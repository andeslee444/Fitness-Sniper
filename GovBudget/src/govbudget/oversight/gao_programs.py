"""GAO Weapon Systems Annual Assessment (WSAA) -> gao_program_assessments.parquet.

The DEPARTMENT tier already exists (``high_risk.py`` — "DOD: 5 high-risk
areas").  This module adds the PROGRAM tier that ROADMAP #30 asks for: GAO's
annual, per-program assessments of DOD's costliest weapon programs, plus the
program-specific GAO reports the same volume lists as related products.

Source (verified live, August 2026)
-----------------------------------
``https://www.gao.gov/assets/gao-25-107569.pdf`` — one PDF per edition (2025:
233 pages).  Two structures are read out of it:

1. **Appendix I: Program Assessments** — a one- or two-page spread per
   program.  The first page of each spread opens with a machine-readable
   banner, then the program-name heading, then GAO's own description::

       Air Force Program Type: MDAP Common Name: Sentinel
       LGM-35A Sentinel
       The Air Force's Sentinel, formerly the Ground Based Strategic
       Deterrent, is intended to replace the Minuteman III ...
       Source: U.S. Air Force. | GAO-25-107569

   Each service section also prints an index table whose assessment-type
   column carries one token per program; that count is the parser's
   cross-check, and a shortfall is reported rather than swallowed.

2. **Related GAO Products** — a bibliography of program-specific and
   portfolio-level GAO reports, each as
   ``Title. GAO-NN-NNNNNN. Washington, D.C.: Month D, YYYY.``

Politeness: exactly ONE HTTP GET per edition, to a static PDF asset under
``/assets/``.  ``gao.gov/robots.txt`` disallows ``/search`` and
``/reports-testimonies``; neither is used.  The PDF is cached under
``data/raw/gao/`` and reused.

Parquet columns (typed at ingestion — backlog #11):
    kind varchar, product_number varchar, report_title varchar,
    report_url varchar, source_product varchar, source_pdf_url varchar,
    released varchar, service varchar, assessment_type varchar,
    program_name varchar, common_name varchar, report_page integer,
    pdf_page integer, description varchar, edition_year integer,
    program_key varchar, predecessor_product varchar,
    predecessor_pdf_page integer

``kind`` is ``assessment`` (Appendix I) or ``related_product``.

Three editions are ingested (2025, 2024, 2023); each assessment carries its
edition and a link to the same program's assessment in the nearest earlier
edition (``link_predecessors``).  Older editions reach a page only through
that link.

NOTE: this module ingests GAO's work.  It does NOT decide which budget line
each item belongs to — that crosswalk is human-ratified in
``data-seeds/gao_program_xwalk.csv`` and measured by ``gao_xwalk.py``, because
attributing a GAO finding to the wrong weapons program is a defamation-shaped
error, not a formatting one.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import duckdb
import httpx

# ── Layouts ─────────────────────────────────────────────────────────────────
#
# GAO re-typesets the volume every year.  Each anchor below is a tuple of
# regexes tried in order — the first that matches a page wins.  When an
# edition drifts, ADD an alternative here; never loosen the one that already
# parses a shipped edition (the 2025 anchors are listed first on purpose).
#
# Measured 2026-09-10 against the cached 233-page 2025 volume: the two
# alternatives below change nothing there.  COMMON_FIRST fires on 0 pages
# TYPE_FIRST does not; PAGENO_BARE fires on 0 pages that carry a banner and
# lack the full footer, and never disagrees with PAGENO_FULL where both match;
# the index-header regex finds the same four pages and the same count, 65.

# GAO's own service labels.  "DOD" is the 2024/2023 volumes' label for a
# program no single service leads (the F-35); the 2025 volume writes the
# same idea as "Joint".  Both are kept verbatim — the label a reader sees
# is GAO's — and _SERVICE_FAMILY below decides what they mean for linking.
_SERVICES = r"Air Force|Army|Navy|Space Force|Marine Corps|Joint|DOD"

# 2025 (verified live): "Air Force Program Type: MDAP Common Name: Sentinel"
_BANNER_TYPE_FIRST_RE = re.compile(
    rf"^[ \t]*(?P<service>{_SERVICES})\s+Program Type:\s*(?P<type>.+?)\s+"
    r"Common Name:\s*(?P<common>.+?)[ \t]*$",
    re.MULTILINE,
)
# The other order the same two labels can be typeset in.
_BANNER_COMMON_FIRST_RE = re.compile(
    rf"^[ \t]*(?P<service>{_SERVICES})\s+Common Name:\s*(?P<common>.+?)\s+"
    r"Program Type:\s*(?P<type>.+?)[ \t]*$",
    re.MULTILINE,
)
# 2024 and 2023 (measured from the cached PDFs 2026-09-12): the same three
# labels, typeset type-first and with the service behind "Lead Component:" —
# "MDAP Lead Component: Air Force Common Name: B-52 CERP".
_BANNER_LEAD_COMPONENT_RE = re.compile(
    rf"^[ \t]*(?P<type>.+?)\s+Lead Component:\s*(?P<service>{_SERVICES})\s+"
    r"Common Name:\s*(?P<common>.+?)[ \t]*$",
    re.MULTILINE,
)
# The footer's kerning breaks inside words on some pages ("U.S. Govern ment"),
# so every literal here tolerates an interior space.
_PAGENO_FULL_RE = re.compile(
    r"Page\s+(\d+)\s+U\.\s?S\.\s+Govern\s*ment\s+Account\s*ability\s+"
    r"Office\s+GAO-\d\d-\d+"
)
# A footer that prints only the product number.
_PAGENO_BARE_RE = re.compile(
    r"Page\s+(\d+)\s+GAO-\d\d-\d+\s+Weapon\s+Systems"
)
# The service index tables' header row; one type token per program follows.
_INDEX_HEADER_RE = re.compile(r"Program name\s+(?:Assessment|Program) type")
# 2024 and 2023 print the same two columns the other way round.  "Program
# name Primary staff" (the GAO-contact table in the 2023 volume) is a
# different table and is deliberately not matched by either anchor.
_INDEX_HEADER_TYPE_FIRST_RE = re.compile(r"Assessment type\s+Program name")
# Headers whose tables print the assessment type once per GROUP rather than
# once per program, so the countable unit is the program row (see
# ``index_table_program_counts``).
_ROW_COUNTED_HEADERS = (_INDEX_HEADER_TYPE_FIRST_RE,)


@dataclass(frozen=True)
class Layout:
    """Per-edition text anchors.  See the block comment above."""

    banners: tuple[re.Pattern, ...]
    pagenos: tuple[re.Pattern, ...]
    index_headers: tuple[re.Pattern, ...]

    @staticmethod
    def _first(patterns: tuple[re.Pattern, ...], text: str):
        for rx in patterns:
            m = rx.search(text)
            if m is not None:
                return m
        return None

    def banner(self, text: str):
        return self._first(self.banners, text)

    def pageno(self, text: str):
        return self._first(self.pagenos, text)

    def index_header(self, text: str):
        return self._first(self.index_headers, text)


DEFAULT_LAYOUT = Layout(
    banners=(
        _BANNER_TYPE_FIRST_RE,
        _BANNER_COMMON_FIRST_RE,
        _BANNER_LEAD_COMPONENT_RE,
    ),
    pagenos=(_PAGENO_FULL_RE, _PAGENO_BARE_RE),
    index_headers=(_INDEX_HEADER_RE, _INDEX_HEADER_TYPE_FIRST_RE),
)

# ── Editions ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Edition:
    product_number: str
    report_title: str
    released: str  # ISO yyyy-mm
    # The current edition's bibliography is the reading list.  An older
    # edition's would add products no person has adjudicated, so it is not
    # re-read (a coverage gap, stated on /methodology/).
    ingest_related: bool = True
    layout: Layout = DEFAULT_LAYOUT

    @property
    def slug(self) -> str:
        return self.product_number.lower()

    @property
    def year(self) -> int:
        return int(self.released[:4])

    @property
    def pdf_url(self) -> str:
        return f"https://www.gao.gov/assets/{self.slug}.pdf"

    @property
    def report_url(self) -> str:
        return f"https://www.gao.gov/products/{self.slug}"


EDITIONS: tuple[Edition, ...] = (
    Edition(
        product_number="GAO-25-107569",
        report_title=(
            "Weapon Systems Annual Assessment: DOD Leaders Should Ensure That "
            "Newer Programs Are Structured for Speed and Innovation"
        ),
        released="2025-06",
    ),
    # Predecessors (ROADMAP #30, "and its predecessors").  Verified live
    # 2026-09-10: the PDFs HEAD 200 application/pdf at 40,333,305 and
    # 24,744,977 bytes; the /products/ pages carry exactly these titles and
    # give publication dates Jun 17, 2024 and Jun 08, 2023.  GAO-24-106831 is
    # additionally marked "[Reissued with revisions on Jul. 18, 2024]" — a
    # revision marker, not part of the title, so it is not carried here.
    Edition(
        product_number="GAO-24-106831",
        report_title=(
            "Weapon Systems Annual Assessment: DOD Is Not Yet Well-Positioned "
            "to Field Systems with Speed"
        ),
        released="2024-06",
        ingest_related=False,
    ),
    Edition(
        product_number="GAO-23-106059",
        report_title=(
            "Weapon Systems Annual Assessment: Programs Are Not Consistently "
            "Implementing Practices That Can Help Accelerate Acquisitions"
        ),
        released="2023-06",
        ingest_related=False,
    ),
)


def current_edition() -> Edition:
    """The newest edition — the only one the crosswalk matches against."""
    return max(EDITIONS, key=lambda e: e.released)

USER_AGENT = (
    "FiscalReceipts/1.0 (+https://fiscalreceipts.com; "
    "contact andes.lee444@gmail.com)"
)

# ── Shared helpers ──────────────────────────────────────────────────────────

_ASSESSMENT_TYPES = (
    "MDAP Increment",
    "MDAP",
    "MTA",
    "Future Major Weapon Acquisition/MTA",
    "Future Major Weapon Acquisition",
)


def _clean(text: str) -> str:
    """Normalize quotes/ligatures and collapse whitespace."""
    text = text.replace("­", "")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    return re.sub(r"\s+", " ", text).strip()


def _key(text: str) -> str:
    """Join key: lowercase alphanumerics only.

    One PDF spells the same thing several ways — "MDAP Incremen t" where the
    kerning broke, "F-22SeE" in an index table against "F-22 SeE" on the
    banner.  Punctuation and spacing carry no meaning across those spellings.
    """
    return re.sub(r"[^a-z0-9]", "", text.lower())


_TYPE_BY_KEY = {_key(t): t for t in _ASSESSMENT_TYPES}

# One anchor per program in a service index table.  The longest type wraps
# across typeset lines with the program NAME between its halves ("Future Major
# Weapon" / name / "Acquisition"), so its first half is the anchor and the
# orphaned "Acquisition/MTA" tail must not count a second time.
_TYPE_ANCHOR_RE = re.compile(
    r"Future Major Weapon|MDAP Increment|MDAP|(?<!Acquisition/)\bMTA\b"
)

# ── Appendix I parsing ──────────────────────────────────────────────────────

_MAX_HEADING_LINES = 3

# The image credit is typeset in the left rail, so on 13 of the 65 spreads it
# lands INSIDE GAO's paragraph — "…prior to making | Source: Raytheon. |
# GAO-25-107569 | a full production decision."  Cutting at it would ship a
# sentence fragment as a verbatim quote, so the credit is excised first and
# the paragraph is cut at a structural marker afterwards.
_CREDIT_RE = re.compile(
    r"Source[s]?\s*(?:\([^)]*\))?\s*:.{0,140}?\|\s*GAO-\d\d-\d+\s*"
)

# Everything that can follow GAO's description paragraph on the spread's first
# page: the performance chart's caption, the software and essentials side
# panels, the leading-practices table, a footnote, an uncredited "Source:".
_DESC_END_RE = re.compile(
    r"Source[s]?\s*(?:\(.*?\))?\s*:"
    r"|Program Performance\b"
    r"|Software Development\b"
    r"|Program Essentials\b"
    r"|Implementation of Leading\b"
    r"|Attainment of Product\b"
    r"|Total quantities\b"
    r"|Estimated\s+(?:\w+\s+){0,5}?Cost and Quantit"
    r"|Current Status\b"
    r"|\ba?GAO-\d\d-\d+"
)

# Nothing that survives the cut may look like a figure caption or a dollar
# amount: a currency token in prose is an uncited figure (site gate 2), and a
# stray caption is proof the cut missed.  Tripping this is a parse defect.
DESC_RESIDUE_RE = re.compile(
    r"[\$€£]"
    r"|\bdollars in (?:millions|billions)\b"
    r"|\bfiscal year \d{4} dollars\b"
)

_MIN_DESCRIPTION_CHARS = 120


def program_key(common_name: str) -> str:
    """The identity that links one program across editions: GAO's own common
    name, normalized the way ``_key`` normalizes every other join."""
    return _key(common_name)


@dataclass
class Assessment:
    kind: str
    product_number: str
    report_title: str
    report_url: str
    source_product: str
    source_pdf_url: str
    released: str
    service: str
    assessment_type: str
    program_name: str
    common_name: str
    report_page: int
    pdf_page: int
    description: str
    # Edition stamp + predecessor link (ROADMAP #30 "and its predecessors").
    edition_year: int
    program_key: str          # program_key(common_name); "" for related products
    predecessor_product: str  # the nearest earlier edition assessing the same program, or ""
    predecessor_pdf_page: int


def index_table_program_counts(
    pages: list[str], layout: Layout = DEFAULT_LAYOUT
) -> int:
    """How many programs the service index tables say Appendix I contains.

    Two typesettings, counted two different ways because the tables say two
    different things:

    * 2025 prints the assessment type once per PROGRAM ("LGM-35A Sentinel
      MDAP").  The tables wrap names and types across typeset lines in two
      different interleavings, so the NAMES are not reliably recoverable from
      them — but one type token per program is, and that count is exact.
    * 2024 and 2023 print the type once per GROUP ("MDAPs", "MTA Programs")
      and one program per row, so the countable unit is the row.  That count
      is an UPPER bound: a program name too long for the column wraps onto a
      row of its own, and so does the tail of a wrapped group label, and text
      extraction cannot tell either from a program.  Measured 2026-09-12 the
      inflation is 7 rows of 75 (2024) and 6 of 69 (2023), so the parser is
      expected to come in at or a little below this number, never above it.

    This number is the parser's expected population.
    """
    total = 0
    for raw in pages:
        if not raw:
            continue
        head = layout.index_header(raw)
        if head is None:
            continue
        block = raw[head.end():]
        block = re.split(r"Source[s]?\s*(?:\(.*?\))?\s*:", block)[0]
        if head.re in _ROW_COUNTED_HEADERS:
            total += sum(1 for line in block.splitlines() if line.strip())
        else:
            total += len(_TYPE_ANCHOR_RE.findall(block))
    return total


def _split_heading(lines: list[str], common_name: str) -> tuple[str, int]:
    """Return (heading, number of lines consumed).

    The heading runs for however many lines it takes for the accumulated text
    to contain the banner's common name — one line for "LGM-35A Sentinel",
    two for "F-15 Eagle Passive Active Warning Survivability System" +
    "(F-15 EPAWSS)".  Reading the name the banner already gave us beats
    guessing where GAO's first sentence starts; an earlier cut guessed, and
    swallowed GAO's opening clause on two programs.
    """
    want = _key(common_name)
    acc = ""
    for n, line in enumerate(lines[:_MAX_HEADING_LINES], start=1):
        acc = f"{acc} {line}".strip()
        if want and want in _key(acc):
            return _clean(acc), n
    return "", 0


def _last_sentence(text: str) -> str:
    """Trim to the last complete sentence.

    The column cut can land mid-clause.  A quote that stops mid-sentence
    reads as GAO trailing off; ending on GAO's own full stop does not change
    what GAO said, and dropping the fragment is the conservative direction.
    """
    text = text.strip()
    at = text.rfind(". ")
    if text.endswith("."):
        return text
    return text[: at + 1].strip() if at > 0 else text


def parse_edition_pages(pages: list[str], edition: Edition) -> list[Assessment]:
    """One Assessment per Appendix I program.  ``pages[i]`` is PDF page i+1."""
    out: list[Assessment] = []
    seen: set[str] = set()
    layout = edition.layout
    for idx, raw in enumerate(pages):
        if not raw:
            continue
        banner = layout.banner(raw)
        pageno = layout.pageno(raw)
        if banner is None or pageno is None:
            continue
        service = banner.group("service").strip()
        atype = _TYPE_BY_KEY.get(_key(banner.group("type")))
        common = _clean(banner.group("common"))
        if atype is None or not common:
            continue
        if _key(common) in seen:
            continue  # continuation page of a two-page spread

        body_lines = [
            ln for ln in raw[banner.end():].splitlines() if ln.strip()
        ]
        heading, used = _split_heading(body_lines, common)
        if not heading:
            continue
        tail = _clean(_CREDIT_RE.sub(" ", " ".join(body_lines[used:])))
        stop = _DESC_END_RE.search(tail)
        description = _last_sentence(tail[: stop.start()] if stop else tail)
        # A heading that wraps onto a second line ("T-AO 205 John Lewis Class
        # Fleet Replenishment Oiler" / "(T-AO 205)") is already satisfied by
        # line one, so its parenthetical tail falls into the paragraph.
        description = re.sub(r"^\([^)]*\)\s*", "", description).strip()
        if len(description) < _MIN_DESCRIPTION_CHARS:
            continue

        seen.add(_key(common))
        out.append(
            Assessment(
                kind="assessment",
                product_number=edition.product_number,
                report_title=edition.report_title,
                report_url=edition.report_url,
                source_product=edition.product_number,
                source_pdf_url=edition.pdf_url,
                released=edition.released,
                service=service,
                assessment_type=atype,
                program_name=heading,
                common_name=common,
                report_page=int(pageno.group(1)),
                pdf_page=idx + 1,
                description=description,
                edition_year=edition.year,
                program_key=program_key(common),
                predecessor_product="",
                predecessor_pdf_page=0,
            )
        )
    return out


# ── Related GAO Products parsing ────────────────────────────────────────────

_RELATED_RE = re.compile(
    r"(?P<title>[A-Z][^.]*?:[^.]*?)\.\s*"
    r"(?P<product>GAO[-/][A-Z0-9-]+)\.\s*"
    r"Washington, D\.C\.:\s*(?P<date>[A-Z][a-z]+ \d{1,2}, \d{4})"
)
_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        "January February March April May June July August September "
        "October November December".split()
    )
}




_RELATED_BODY_X0 = 210.0
_RELATED_ROW_TOL = 3.0
_RUNNING_HEADER_RE = re.compile(r"R?\s*elated\s+GAO\s+P\s*roducts")


def related_column_text(pdf_path: Path) -> str:
    """Text of the Related GAO Products bibliography, left rail removed.

    The appendix is typeset in two columns: a left rail of category labels
    ("Acquisition Policy and Reform") and a right column of citations.  Line
    extraction folds them together word by word, which corrupts the FIRST
    title under every label — and those titles ship verbatim.  Splitting on
    the words' own x-coordinates keeps the citation column intact instead of
    trying to subtract the labels back out afterwards.
    """
    import pdfplumber

    out: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "Washington, D.C.:" not in text:
                continue
            rows: dict[int, list[tuple[float, str]]] = {}
            for w in page.extract_words():
                if w["x0"] < _RELATED_BODY_X0:
                    continue
                key = int(w["top"] / _RELATED_ROW_TOL)
                rows.setdefault(key, []).append((w["x0"], w["text"]))
            for key in sorted(rows):
                line = " ".join(t for _, t in sorted(rows[key]))
                out.append(_RUNNING_HEADER_RE.sub(" ", line))
    return "\n".join(out)


def parse_related_products(text: str, edition: Edition) -> list[Assessment]:
    """One Assessment(kind="related_product") per bibliography entry."""
    blob = _clean(
        re.sub(
            r"Page \d+ GAO-\d\d-\d+ Weapon Systems Annual Assessment",
            " ",
            text,
        )
    )
    out: list[Assessment] = []
    seen: set[str] = set()
    for m in _RELATED_RE.finditer(blob):
        product = m.group("product").strip()
        if product in seen or product == edition.product_number:
            continue
        title = _clean(m.group("title"))
        if ":" not in title or len(title) < 20:
            continue
        month, day, year = re.match(
            r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", m.group("date")
        ).groups()
        seen.add(product)
        out.append(
            Assessment(
                kind="related_product",
                product_number=product,
                report_title=title,
                report_url=f"https://www.gao.gov/products/{product.lower()}",
                source_product=edition.product_number,
                source_pdf_url=edition.pdf_url,
                released=f"{year}-{_MONTHS[month]:02d}-{int(day):02d}",
                service="",
                assessment_type="",
                program_name=title.split(":", 1)[0].strip(),
                common_name="",
                report_page=0,
                pdf_page=0,
                description="",
                edition_year=edition.year,
                program_key="",
                predecessor_product="",
                predecessor_pdf_page=0,
            )
        )
    return out


# ── Predecessor links ───────────────────────────────────────────────────────

# GAO's service label -> the book family it is carried in.  Space Force
# programs were Air Force programs in older editions and are carried in the
# Air Force book either way — the same call ``gao_xwalk.SERVICE_ORGS`` makes
# for the four services it maps.  "Joint" is extra here: SERVICE_ORGS has no
# entry for it (a Joint assessment generates no crosswalk candidate), but a
# Joint program still needs a stable family to chain across editions.
_SERVICE_FAMILY = {
    "Air Force": "F", "Space Force": "F", "Army": "A",
    "Navy": "N", "Marine Corps": "N", "Joint": "J",
    # 2024/2023 write "DOD" where 2025 writes "Joint" — one family, so a
    # joint-lead program (the F-35) chains across the three volumes instead
    # of reading as a rename.
    "DOD": "J",
}


def _family(service: str) -> str:
    return _SERVICE_FAMILY.get(service, service)


def link_predecessors(rows: list[Assessment]) -> list[Assessment]:
    """Stamp ``predecessor_product`` / ``predecessor_pdf_page`` on every
    assessment.

    The predecessor is the SAME program — same ``program_key`` and same
    service family — in the nearest earlier edition that assessed it.
    Nothing fuzzier: a renamed program (GBSD -> Sentinel) breaks its own
    chain, and an older edition's assessment that no chain reaches is linked
    to no page.  A missed link is a coverage gap; a wrong one puts GAO's words
    on the wrong weapon.
    """
    by_year: dict[int, dict[tuple[str, str], Assessment]] = {}
    for a in rows:
        if a.kind == "assessment":
            by_year.setdefault(a.edition_year, {})[
                (a.program_key, _family(a.service))
            ] = a
    years = sorted(by_year)
    out: list[Assessment] = []
    for a in rows:
        if a.kind != "assessment":
            out.append(a)
            continue
        pred = None
        for y in reversed([y for y in years if y < a.edition_year]):
            pred = by_year[y].get((a.program_key, _family(a.service)))
            if pred is not None:
                break
        out.append(replace(
            a,
            predecessor_product=pred.product_number if pred else "",
            predecessor_pdf_page=pred.pdf_page if pred else 0,
        ))
    return out


def predecessor_chain(row: dict, rows: list[dict]) -> list[dict]:
    """Older-edition assessments of ``row``'s program, newest first.

    Works on parquet rows (dicts) so the exporter and the CLI share it.
    """
    index = {
        (r["product_number"], r["program_key"], _family(r["service"])): r
        for r in rows if r["kind"] == "assessment"
    }
    out: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    cur = row
    while cur.get("predecessor_product"):
        key = (
            cur["predecessor_product"], cur["program_key"],
            _family(cur["service"]),
        )
        if key in seen or key not in index:
            break
        seen.add(key)
        cur = index[key]
        out.append(cur)
    return out


def unlinked_older_assessments(
    rows: list[dict], current_product: str
) -> list[dict]:
    """Older-edition assessments no current-edition chain reaches.

    Programs GAO assessed in an earlier volume but not the current one
    (delivered, cancelled, restructured, renamed).  They are linked to NO
    page — by design — and reported so the gap is loud, not silent.
    """
    reached: set[tuple[str, str, str]] = set()
    for r in rows:
        if r["kind"] == "assessment" and r["product_number"] == current_product:
            for p in predecessor_chain(r, rows):
                reached.add(
                    (p["product_number"], p["program_key"], _family(p["service"]))
                )
    return sorted(
        (
            r for r in rows
            if r["kind"] == "assessment"
            and r["product_number"] != current_product
            and (r["product_number"], r["program_key"], _family(r["service"]))
            not in reached
        ),
        key=lambda r: (-int(r["edition_year"]), r["service"], r["common_name"]),
    )


# ── Fetch + build ───────────────────────────────────────────────────────────


def fetch_edition_pdf(
    client: httpx.Client, edition: Edition, *, raw_dir: Path
) -> Path:
    """Download (or reuse) the edition PDF under ``raw_dir``."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / f"{edition.slug}.pdf"
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(
            f"gao-programs: reusing cached {dest.name} "
            f"({dest.stat().st_size:,} bytes)"
        )
        return dest
    r = client.get(edition.pdf_url, follow_redirects=True)
    r.raise_for_status()
    dest.write_bytes(r.content)
    sha = hashlib.sha256(r.content).hexdigest()[:16]
    print(
        f"gao-programs: fetched {edition.pdf_url} "
        f"({len(r.content):,} bytes, sha256:{sha})"
    )
    return dest


def extract_pdf_pages(pdf_path: Path) -> list[str]:
    """Per-page text, via pdfplumber.

    pypdf was tried first and rejected: it emits the two-page spreads out of
    reading order (the image credit lands above the heading on 19 of 65) and
    breaks words across its own line breaks — "Production Is sues", "Making
    C ritical".  A verbatim quote reassembled from broken words is not
    verbatim, so the reader that keeps words intact wins.
    """
    import pdfplumber

    with pdfplumber.open(str(pdf_path)) as pdf:
        return [(page.extract_text() or "") for page in pdf.pages]


_COLUMNS = (
    "kind varchar, product_number varchar, report_title varchar,"
    "report_url varchar, source_product varchar, source_pdf_url varchar,"
    "released varchar, service varchar, assessment_type varchar,"
    "program_name varchar, common_name varchar, report_page integer,"
    "pdf_page integer, description varchar"
    ", edition_year integer, program_key varchar,"
    "predecessor_product varchar, predecessor_pdf_page integer"
)
_FIELDS = (
    "kind", "product_number", "report_title", "report_url", "source_product",
    "source_pdf_url", "released", "service", "assessment_type",
    "program_name", "common_name", "report_page", "pdf_page", "description",
    "edition_year", "program_key", "predecessor_product",
    "predecessor_pdf_page",
)


_MIN_PARSE_SHARE = 0.9


def build_gao_program_assessments(
    client: httpx.Client, *, raw_dir: Path, out_path: Path
) -> Path:
    """Fetch every edition, parse it, link predecessors, write the parquet."""
    rows: list[Assessment] = []
    for edition in EDITIONS:
        pdf = fetch_edition_pdf(client, edition, raw_dir=raw_dir)
        pages = extract_pdf_pages(pdf)
        parsed = parse_edition_pages(pages, edition)
        expected = index_table_program_counts(pages, edition.layout)
        related = (
            parse_related_products(related_column_text(pdf), edition)
            if edition.ingest_related
            else []
        )
        print(
            f"gao-programs: {edition.product_number} -> {len(parsed)}/"
            f"{expected} Appendix I program assessments, "
            f"{len(related)} related products"
            + ("" if edition.ingest_related else " (bibliography not re-read)")
        )
        if expected == 0:
            raise RuntimeError(
                f"gao-programs: {edition.product_number}: no service index "
                "table matched Layout.index_headers — the layout changed; add "
                "an anchor to the edition's Layout rather than shipping an "
                "uncounted edition"
            )
        if not parsed or len(parsed) < _MIN_PARSE_SHARE * expected:
            raise RuntimeError(
                f"gao-programs: {edition.product_number}: parsed {len(parsed)} "
                f"of {expected} indexed programs (< {_MIN_PARSE_SHARE:.0%}) — "
                "the banner or footer anchors drifted; add an alternative to "
                "the edition's Layout rather than shipping a partial edition"
            )
        if len(parsed) != expected:
            print(
                f"  WARNING: {expected - len(parsed)} index row(s) have no "
                "parsed assessment — a wrapped name or group label occupies "
                "its own row in the 2024/2023 tables (see "
                "index_table_program_counts), so read this against the names "
                "before treating it as a miss"
            )
        residue = [a for a in parsed if DESC_RESIDUE_RE.search(a.description)]
        if residue:
            raise RuntimeError(
                "gao-programs: description text carries a figure caption or "
                "currency token for "
                + ", ".join(a.common_name for a in residue[:5])
                + " — the paragraph cut missed, and a dollar figure in prose "
                "is an uncited figure"
            )
        rows.extend(parsed)
        rows.extend(related)

    rows = link_predecessors(rows)
    current = current_edition().product_number
    linked = sum(
        1 for r in rows if r.kind == "assessment" and r.predecessor_product
    )
    older = sum(
        1 for r in rows
        if r.kind == "assessment" and r.product_number != current
    )
    print(
        f"gao-programs: {linked} predecessor link(s) across {len(EDITIONS)} "
        f"editions; {older} older-edition assessment(s) ingested"
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.execute(f"create table _ga ({_COLUMNS})")
        con.executemany(
            "insert into _ga values (" + ",".join(["?"] * len(_FIELDS)) + ")",
            [tuple(asdict(r)[f] for f in _FIELDS) for r in rows],
        )
        con.execute(
            f"copy _ga to '{out_path}' (format parquet, compression zstd)"
        )
    finally:
        con.close()
    print(f"gao-programs: wrote {len(rows)} rows -> {out_path}")
    return out_path
