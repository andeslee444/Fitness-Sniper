"""Resolve J-book facts to PDF page + word bbox.

Per DOCUMENT (not per fact): one pypdf text pass over all pages (~12 ms/page)
caches page texts; candidate pages are those whose text contains the pe_bli
anchor AND a word-boundary regex match of a formatted amount string; ONE
pdfplumber handle (opened lazily) extracts words only on candidate pages
(~60 ms/page) until one yields the exact word → bbox.

Phase 5F (§2b) adds NARRATIVE provenance (target_kind='narrative'): each
narrative paragraph is located by its opening text (first ~12 words,
whitespace-normalized — narrative_opening is BINDING, shared with the
verify-phase5b1 narrative re-derivation leg). Candidate pages are those whose
normalized text contains the opening; tie-breaking narrows by pe_bli presence,
then the same source-exhibit/project rules as amounts. The bbox is the FIRST
LINE of the passage (pdfplumber word span). Resolution vocabulary and honesty
rules are identical to amounts; unresolvable openings store an 'unresolved'
row with NO page — locations are never faked.

Deterministic tie-breaking (several candidate pages): detail facts have one
true source exhibit — R-2A for project-level RDT&E facts, R-2 for PE-level
RDT&E facts, P-40 for procurement line items. Candidates are narrowed to
pages whose 'Exhibit <type>' header matches that source exhibit, then (for
project facts) to pages containing the project number as a standalone token.
Each narrowing step is skipped if it would eliminate every candidate.

Resolution honesty: 'unique' (page uniquely determined — either a single
candidate, or tie-breaking narrowed several candidates to exactly one AND the
word match confirmed on that page), 'ambiguous_first' (several pages remain
even after tie-breaking; the first preferred page with a word match wins),
'zero_amount' (amount == 0 — '0.000' floods pages, a page highlight would be
arbitrary; NO page citation, the xml_path citation remains), 'unresolved' (no
page). candidate_pages always records the RAW text-match count (pre
tie-breaking), so 'unique' rows with candidate_pages > 1 are disambiguated
ones — never fabricated certainty. Identity includes the amount (live data
has same-key facts with different amounts).
Cached: already-built (sha, pe_bli, project, scenario, amount) keys are skipped.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from decimal import Decimal
from itertools import groupby
from pathlib import Path

import psycopg

from govbudget.jbooks.era_keys import era_key_anchor
from govbudget.jbooks.citation_units import pdf_page_currency_units


def fact_anchor(pe_bli: str | None) -> str | None:
    """Page-text anchor for a fact's pe_bli.

    Era procurement keys ('0300D-CBDP-L70', Finding D) never appear verbatim
    on a page — the anchor is their P-1 line number ('70'), matching the
    pre-re-key resolution behavior exactly. Everything else anchors on the
    pe_bli itself.
    """
    return era_key_anchor(pe_bli) or pe_bli


def amount_strings(amount: Decimal) -> list[str]:
    """Candidate page renderings for a millions amount.

    Millions forms FIRST (comma then bare, 3-decimal J-book style) — the
    defense-wide comptroller books render dollars in millions ('280.494'), and
    trying them first keeps their resolution byte-identical. The thousands
    integer forms are APPENDED because the Navy comptroller renders R-2/P-40
    dollar figures in THOUSANDS with comma grouping ('280,494' for 280.494M,
    '16,000' for 16.000M). J-book amounts are whole thousands, so amount*1000
    is an integer rendering. Additive: a thousands form only matches when the
    millions form found no page, so defense-wide behavior is unchanged.
    """
    out: list[str] = []
    for s in (f"{amount:,.3f}", f"{amount:.3f}"):  # millions: comma, then bare
        if s not in out:
            out.append(s)
    thousands = amount * 1000
    for s in (f"{thousands:,.0f}", f"{thousands:.0f}"):  # thousands: comma, bare
        if s not in out:
            out.append(s)
    return out


def _page_texts(pdf_path: Path) -> list[str]:
    from pypdf import PdfReader

    return [p.extract_text() or "" for p in PdfReader(str(pdf_path)).pages]


def _amount_pattern(target: str) -> re.Pattern:
    # word-boundary for numerics: '280.494' must not match inside '1,280.494'
    return re.compile(rf"(?<![\d,.]){re.escape(target)}(?![\d])")


# 'Exhibit R-2A' etc. page headers. Longer variants BEFORE their prefixes
# (R-2A before R-2, R-4A before R-4, P-40A before P-40) so alternation
# never truncates a match.
_EXHIBIT_MARKER_RE = re.compile(
    r"Exhibit\s+(R-2A|R-2|R-1|R-3|R-4A|R-4|P-40A|P-40|P-1|P-5|P-3A|P-21|P-10)\b"
)


def _page_exhibit(text: str) -> str | None:
    """First 'Exhibit <type>' marker on the page, or None (TOC/index pages)."""
    m = _EXHIBIT_MARKER_RE.search(text)
    return m.group(1) if m else None


def _source_exhibit(exhibit_family: str | None,
                    project_number: str | None) -> str | None:
    """The one exhibit type a detail fact is extracted from.

    RDT&E project rows live on R-2A (RDT&E Project Justification) pages;
    PE-level rows on R-2 (RDT&E Budget Item Justification) pages; procurement
    line items on P-40 (Budget Line Item Justification) pages. Unknown
    families get no exhibit preference.
    """
    if exhibit_family == "rdte":
        return "R-2A" if project_number else "R-2"
    if exhibit_family == "procurement":
        return "P-40"
    return None


def _project_pattern(project_number: str) -> re.Pattern:
    # standalone token: project 'RD' must not match inside 'BOARD' or 'RD1'
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(project_number)}(?![A-Za-z0-9])"
    )


def _preferred_candidates(page_texts: list[str], candidates: list[int], *,
                          project_number: str | None,
                          exhibit_family: str | None) -> list[int]:
    """Narrow candidates by source-exhibit header, then project number.

    Each narrowing step only applies if it keeps ≥1 candidate — the fallback
    is always the previous (wider) set, never an empty one. Returned list
    preserves page order, so 'first' stays deterministic.
    """
    result = list(candidates)
    source = _source_exhibit(exhibit_family, project_number)
    if source is not None:
        narrowed = [i for i in result if _page_exhibit(page_texts[i]) == source]
        if narrowed:
            result = narrowed
    if project_number:
        pat = _project_pattern(project_number)
        narrowed = [i for i in result if pat.search(page_texts[i])]
        if narrowed:
            result = narrowed
    return result


_UNRESOLVED = {
    "page_number": None, "x0": None, "x1": None, "top_pt": None,
    "bottom_pt": None, "page_width": None, "page_height": None,
}


def _resolve_fact(page_texts: list[str], plumber, *, pe_bli: str,
                  amount: Decimal, project_number: str | None = None,
                  exhibit_family: str | None = None) -> dict:
    """Resolve one fact against pre-extracted texts + an open pdfplumber handle.

    `plumber` is a zero-arg callable returning the (lazily opened, cached)
    pdfplumber.PDF — so documents whose facts all miss never pay the open cost.
    """
    if not amount.is_finite():
        return {**_UNRESOLVED, "resolution": "unresolved",
                "candidate_pages": 0, "amount_text": str(amount)}
    targets = amount_strings(amount)
    if amount == 0:
        return {**_UNRESOLVED, "resolution": "zero_amount",
                "candidate_pages": 0, "amount_text": targets[0]}
    patterns = [_amount_pattern(t) for t in targets]
    candidates = [
        i for i, text in enumerate(page_texts)
        if pe_bli in text and any(p.search(text) for p in patterns)
    ]
    if not candidates:
        return {**_UNRESOLVED, "resolution": "unresolved",
                "candidate_pages": 0, "amount_text": targets[0]}
    preferred = _preferred_candidates(
        page_texts, candidates,
        project_number=project_number, exhibit_family=exhibit_family,
    )
    # Preferred pages first; remaining raw candidates keep the word-match
    # fallback exhaustive (a text-layer match can still fail word extraction).
    ordered = preferred + [i for i in candidates if i not in preferred]
    pdf = plumber()
    millions_targets = {f"{amount:,.3f}", f"{amount:.3f}"}
    # Do not let an early year/activity numeral (2027 or 2) beat a later
    # exact monetary glyph (2.027 or 0.002). Search canonical glyphs across
    # candidate pages first; only proven thousand-unit pages permit fallback.
    groups = ([target for target in targets if target in millions_targets],
              [target for target in targets if target not in millions_targets])
    for scaled, group in enumerate(groups):
        for idx in ordered:
            units = pdf_page_currency_units(page_texts[idx])
            if scaled and units != "USD thousands":
                continue
            if not scaled and units == "USD thousands":
                continue
            page = pdf.pages[idx]
            words = page.extract_words()
            word = next((w for target in group for w in words if w["text"] == target), None)
            if word is not None:
                # 'unique' ONLY when the page is uniquely determined: a single raw
                # candidate, or tie-breaking narrowed to exactly this one page AND
                # the word match confirmed here (not on a fallback page).
                uniquely = len(candidates) == 1 or (
                    len(preferred) == 1 and idx == preferred[0]
                )
                return {
                    "page_number": idx + 1,         # 1-based for #page=N anchors
                    "x0": float(word["x0"]), "x1": float(word["x1"]),
                    "top_pt": float(word["top"]), "bottom_pt": float(word["bottom"]),
                    "page_width": float(page.width), "page_height": float(page.height),
                    "resolution": "unique" if uniquely else "ambiguous_first",
                    "candidate_pages": len(candidates),
                    "amount_text": word["text"],
                }
    return {**_UNRESOLVED, "resolution": "unresolved",
            "candidate_pages": len(candidates), "amount_text": targets[0]}


def find_fact_page(pdf_path: Path, *, pe_bli: str, amount: Decimal,
                   project_number: str | None = None,
                   exhibit_family: str | None = None) -> dict:
    """Single-fact public entry point (tests; ad-hoc use)."""
    import pdfplumber

    texts = _page_texts(pdf_path)
    pdf_handle = None

    def plumber():
        nonlocal pdf_handle
        if pdf_handle is None:
            pdf_handle = pdfplumber.open(pdf_path)
        return pdf_handle

    try:
        return _resolve_fact(texts, plumber, pe_bli=fact_anchor(pe_bli),
                             amount=amount, project_number=project_number,
                             exhibit_family=exhibit_family)
    finally:
        if pdf_handle is not None:
            pdf_handle.close()


def build_provenance_pages(dsn: str, *, fiscal_year: int | None = None) -> int:
    """Resolve every non-superseded detail fact lacking a provenance_pages row.

    fiscal_year scopes the run to one PB edition's documents (Phase 5E
    per-edition backfill); None keeps the historical whole-corpus behavior.
    Grouped by document: each PDF's text is extracted ONCE for all its facts.
    Returns rows actually inserted (cursor rowcount — ON CONFLICT suppressions
    don't count). Missing document files raise loudly.
    """
    import pdfplumber

    inserted = 0
    with psycopg.connect(dsn) as con:
        rows = con.execute(
            """
            select j.sha256, j.file_path, d.pe_bli, d.project_number, d.scenario,
                   d.amount_millions, j.exhibit_family
            from budget_line_details d
            join jbook_documents j on j.id = d.document_id
            where not d.superseded and j.sha256 is not null
              and (%(fy)s::int is null or j.fiscal_year = %(fy)s)
              and not exists (
                select 1 from provenance_pages p
                where p.target_kind = 'amount'
                  and p.document_sha256 = j.sha256 and p.pe_bli = d.pe_bli
                  and p.scenario = d.scenario
                  and p.project_number is not distinct from d.project_number
                  and p.amount_millions = d.amount_millions
              )
            order by j.sha256
            """,
            {"fy": fiscal_year},
        ).fetchall()
        for sha, doc_group in groupby(rows, key=lambda r: r[0]):
            facts = list(doc_group)
            pdf_path = Path(facts[0][1])
            if not pdf_path.exists():
                raise FileNotFoundError(f"document {sha} missing on disk: {pdf_path}")
            texts = _page_texts(pdf_path)
            pdf_handle = None

            def plumber(path=pdf_path):
                nonlocal pdf_handle
                if pdf_handle is None:
                    pdf_handle = pdfplumber.open(path)
                return pdf_handle

            try:
                for (_, _, pe_bli, project_number, scenario, amount,
                     exhibit_family) in facts:
                    hit = _resolve_fact(texts, plumber,
                                        pe_bli=fact_anchor(pe_bli),
                                        amount=Decimal(amount),
                                        project_number=project_number,
                                        exhibit_family=exhibit_family)
                    cur = con.execute(
                        """
                        insert into provenance_pages
                          (target_kind, document_sha256, pe_bli, project_number,
                           scenario, amount_millions, amount_text, page_number,
                           x0, x1, top_pt, bottom_pt, page_width, page_height,
                           resolution, candidate_pages)
                        values ('amount',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        on conflict (document_sha256, pe_bli, project_number,
                                     scenario, amount_millions)
                          where target_kind = 'amount' do nothing
                        """,
                        (sha, pe_bli, project_number, scenario, amount,
                         hit["amount_text"], hit["page_number"], hit["x0"],
                         hit["x1"], hit["top_pt"], hit["bottom_pt"],
                         hit["page_width"], hit["page_height"],
                         hit["resolution"], hit["candidate_pages"]),
                    )
                    inserted += cur.rowcount
            finally:
                if pdf_handle is not None:
                    pdf_handle.close()
        con.commit()
    return inserted


# ---------------------------------------------------------------------------
# Narrative paragraph provenance (Phase 5F §2b)
# ---------------------------------------------------------------------------

_WS_RE = re.compile(r"\s+")

# BINDING: the opening-word count shared by the builder and the
# verify-phase5b1 narrative re-derivation leg. Changing it invalidates every
# stored narrative row (amount_text holds the searched opening).
NARRATIVE_OPENING_WORDS = 12


def normalize_ws(text: str) -> str:
    """Collapse all whitespace runs to single spaces and strip the ends."""
    return _WS_RE.sub(" ", text).strip()


def narrative_opening(body: str, n_words: int = NARRATIVE_OPENING_WORDS) -> str:
    """A narrative's distinctive opening: first n_words, whitespace-normalized.

    BINDING for the verify-phase5b1 narrative leg — the gate recomputes this
    from the exported body and must land on the same searched string.
    """
    return " ".join(body.split()[:n_words])


def _find_word_span(words: list[dict], snippet: str) -> list[int] | None:
    """Indices of the consecutive pdfplumber words spelling `snippet`.

    Words are joined with single spaces; the match must start AND end on word
    boundaries (a passage opening appearing only inside a longer word is not
    a location). Returns None when the page's words never spell the snippet.
    """
    texts = [w["text"] for w in words]
    joined = " ".join(texts)
    starts: list[int] = []
    off = 0
    for t in texts:
        starts.append(off)
        off += len(t) + 1
    pos = joined.find(snippet)
    while pos != -1:
        end = pos + len(snippet)
        if (pos == 0 or joined[pos - 1] == " ") and (
            end == len(joined) or joined[end] == " "
        ):
            return [
                i for i, s in enumerate(starts)
                if s < end and s + len(texts[i]) > pos
            ]
        pos = joined.find(snippet, pos + 1)
    return None


def _first_line_bbox(words: list[dict], span: list[int]) -> dict:
    """Bbox of the passage START: the matched words on the passage's first
    rendered line (top within 3 pt of the first matched word)."""
    w0 = words[span[0]]
    line_top = float(w0["top"])
    line = [words[i] for i in span if abs(float(words[i]["top"]) - line_top) <= 3.0]
    return {
        "x0": float(w0["x0"]),
        "x1": max(float(w["x1"]) for w in line),
        "top_pt": min(float(w["top"]) for w in line),
        "bottom_pt": max(float(w["bottom"]) for w in line),
    }


def _resolve_narrative(page_texts: list[str], norm_texts: list[str], plumber, *,
                       snippet: str, pe_bli: str,
                       project_number: str | None = None,
                       exhibit_family: str | None = None,
                       words_cache: dict | None = None) -> dict:
    """Resolve one narrative opening against pre-extracted (raw + normalized)
    page texts and an open pdfplumber handle.

    Same honesty vocabulary as _resolve_fact: 'unique' only when the page is
    uniquely determined (single raw candidate, or tie-breaking narrowed to
    exactly the confirming page); 'ambiguous_first' otherwise; 'unresolved'
    when the opening is never found — NO page, never a fake location.
    candidate_pages records the RAW pre-tie-breaking count.
    """
    if not snippet:
        return {**_UNRESOLVED, "resolution": "unresolved",
                "candidate_pages": 0, "search_text": snippet}
    candidates = [i for i, t in enumerate(norm_texts) if snippet in t]
    if not candidates:
        return {**_UNRESOLVED, "resolution": "unresolved",
                "candidate_pages": 0, "search_text": snippet}
    # Tie-break 1: pages carrying the fact's PE anchor (skip if it would
    # eliminate every candidate — same fallback rule as _preferred_candidates).
    preferred = list(candidates)
    narrowed = [i for i in preferred if pe_bli in norm_texts[i]]
    if narrowed:
        preferred = narrowed
    # Tie-breaks 2+3: source exhibit header, then project token (shared with
    # the amount resolver).
    preferred = _preferred_candidates(
        page_texts, preferred,
        project_number=project_number, exhibit_family=exhibit_family,
    )
    ordered = preferred + [i for i in candidates if i not in preferred]
    for idx in ordered:
        if words_cache is not None and idx in words_cache:
            words, page_width, page_height = words_cache[idx]
        else:
            page = plumber().pages[idx]
            words = page.extract_words()
            page_width, page_height = float(page.width), float(page.height)
            if words_cache is not None:
                words_cache[idx] = (words, page_width, page_height)
        span = _find_word_span(words, snippet)
        if span:
            uniquely = len(candidates) == 1 or (
                len(preferred) == 1 and idx == preferred[0]
            )
            return {
                "page_number": idx + 1,         # 1-based for #page=N anchors
                **_first_line_bbox(words, span),
                "page_width": page_width, "page_height": page_height,
                "resolution": "unique" if uniquely else "ambiguous_first",
                "candidate_pages": len(candidates),
                "search_text": snippet,
            }
    return {**_UNRESOLVED, "resolution": "unresolved",
            "candidate_pages": len(candidates), "search_text": snippet}


def find_narrative_page(pdf_path: Path, *, pe_bli: str, body: str,
                        project_number: str | None = None,
                        exhibit_family: str | None = None) -> dict:
    """Single-narrative public entry point (tests; ad-hoc use)."""
    import pdfplumber

    texts = _page_texts(pdf_path)
    norm_texts = [normalize_ws(t) for t in texts]
    pdf_handle = None

    def plumber():
        nonlocal pdf_handle
        if pdf_handle is None:
            pdf_handle = pdfplumber.open(pdf_path)
        return pdf_handle

    try:
        return _resolve_narrative(
            texts, norm_texts, plumber,
            snippet=narrative_opening(body), pe_bli=fact_anchor(pe_bli),
            project_number=project_number, exhibit_family=exhibit_family,
        )
    finally:
        if pdf_handle is not None:
            pdf_handle.close()


# ---------------------------------------------------------------------------
# #195 — the volume that PRINTS a narrative (families piece-1 follow-ups,
# design §5.6, Task 23a)
# ---------------------------------------------------------------------------
#
# service_fetch.dedup_service_master_dups keeps one volume per embedded master
# XML and marks the rest superseded; every narrative of the master is attached
# to the kept volume, which prints only its own budget activities. Until #195
# a narrative was searched in that volume alone, by its opening only: 4,157 of
# the 5,601 PB2026 narratives it could not place, and 339 placed ones sat on a
# page that prints the opening but not the paragraph (measured 2026-10-13).
# A narrative is now placed on the first page, in book-set order, that prints
# its opening, its closing within three pages and its PE/BLI anchor.

# BINDING, like NARRATIVE_OPENING_WORDS: the closing-word count shared by the
# relocation below and verify-jbook-narratives (Task 24). Changing it changes
# which stored narrative rows count as printed where they are cited.
NARRATIVE_CLOSING_WORDS = 12
# BINDING: a paragraph may run over a page break, so its closing words may sit
# on the opening's page or on either of the next two.
NARRATIVE_CLOSING_SPAN_PAGES = 3


def narrative_closing(body: str, n_words: int = NARRATIVE_CLOSING_WORDS) -> str:
    """A narrative's closing: its last n_words, whitespace-normalized."""
    return " ".join(body.split()[-n_words:])


def narrative_printed_at(norm_texts: list[str], page_idx: int,
                         opening: str, closing: str) -> bool:
    """True when page page_idx prints the opening and the closing follows on
    that page or the next NARRATIVE_CLOSING_SPAN_PAGES - 1 pages (the window's
    normalized texts joined by one space). BINDING for verify-jbook-narratives'
    paged rule."""
    if not opening or not closing or not 0 <= page_idx < len(norm_texts):
        return False
    if opening not in norm_texts[page_idx]:
        return False
    window = " ".join(norm_texts[page_idx:page_idx + NARRATIVE_CLOSING_SPAN_PAGES])
    return closing in window


def narrative_located_at(norm_texts: list[str], page_idx: int, opening: str,
                         closing: str, anchor: str | None) -> bool:
    """narrative_printed_at, and the opening's page also prints the fact's
    PE/BLI anchor (fact_anchor). The bar for giving a narrative a NEW location:
    an opening and closing alone recur under other program elements (#195's
    033016199ca94aa7 is the case), so a location must also name the program.
    BINDING for verify-jbook-narratives' pageless rule."""
    return (bool(anchor)
            and narrative_printed_at(norm_texts, page_idx, opening, closing)
            and anchor in norm_texts[page_idx])


@dataclass(frozen=True)
class Volume:
    """One PDF of a narrative's book set (#195)."""
    document_id: int
    sha256: str
    file_path: str
    status: str
    title: str


_BOOK_SET_SQL = """
    select o.id, o.sha256, o.file_path, o.status, o.title
    from jbook_documents d
    join jbook_documents o
      on o.fiscal_year = d.fiscal_year and o.org = d.org
     and o.exhibit_family = d.exhibit_family
    where d.id = %s
      and o.sha256 is not null and o.file_path is not null
      and lower(o.file_path) like '%%.pdf'
      and o.status in ('downloaded', 'superseded')
    order by (o.id <> d.id), (o.status <> 'downloaded'), o.title, o.id
"""


def book_set(con, document_id: int) -> list[Volume]:
    """The attached volume first, then every other PDF volume of the same PB
    edition, organization and exhibit family, downloaded before superseded,
    then by title and id.

    Not only the volumes sharing one master-XML sha: two volumes can embed
    regenerated copies of the same master (Army RDT&E Vol 1, docs 344 and 351,
    hold the same 1,189 narratives under masters with different bytes), and
    each prints the other's budget activities.
    """
    return [Volume(*row) for row in con.execute(_BOOK_SET_SQL, (document_id,)).fetchall()]


def _page_texts_job(path: str) -> list[str]:
    return _page_texts(Path(path))


def page_texts_parallel(paths: list[str], *,
                        workers: int | None = None) -> dict[str, list[str]]:
    """pypdf page texts for several PDFs, one worker process per PDF (pypdf is
    pure Python, so processes, not threads). Keyed by the path as given; the
    texts equal _page_texts' for each path."""
    from concurrent.futures import ProcessPoolExecutor

    unique = sorted(set(paths))
    if not unique:
        return {}
    workers = workers or min(8, os.cpu_count() or 1, len(unique))
    if workers <= 1:
        return {p: _page_texts_job(p) for p in unique}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return dict(zip(unique, pool.map(_page_texts_job, unique)))


def resolve_printed_narrative(volumes: list[Volume], texts: dict, plumber_for, *,
                              opening: str, closing: str, pe_bli: str,
                              project_number: str | None,
                              exhibit_family: str | None,
                              words_cache: dict) -> dict | None:
    """The first volume, in book-set order, with a page where the narrative is
    located (narrative_located_at), resolved to that page's first-line bbox.

    texts maps sha256 -> (raw page texts, normalized page texts); plumber_for
    maps sha256 -> an open pdfplumber handle; words_cache is keyed by
    (sha256, page index); pe_bli is the fact anchor. Within a volume the
    existing tie-breaks narrow the located pages (source exhibit, then project
    token) and the honesty vocabulary is unchanged: 'unique' only when one page
    locates it or the tie-breaks narrowed to exactly the page the words
    confirm. candidate_pages is the RAW count of pages in that volume carrying
    the opening, as for every narrative row. Returns None when no volume
    locates the narrative or no word span confirms it.
    """
    for vol in volumes:
        raw, norm = texts[vol.sha256]
        located = [i for i in range(len(norm))
                   if narrative_located_at(norm, i, opening, closing, pe_bli)]
        if not located:
            continue
        preferred = _preferred_candidates(raw, located, project_number=project_number,
                                          exhibit_family=exhibit_family)
        ordered = preferred + [i for i in located if i not in preferred]
        for idx in ordered:
            key = (vol.sha256, idx)
            if key not in words_cache:
                page = plumber_for(vol.sha256).pages[idx]
                words_cache[key] = (page.extract_words(), float(page.width),
                                    float(page.height))
            words, page_width, page_height = words_cache[key]
            span = _find_word_span(words, opening)
            if span:
                uniquely = len(located) == 1 or (
                    len(preferred) == 1 and idx == preferred[0])
                return {
                    "page_number": idx + 1,
                    **_first_line_bbox(words, span),
                    "page_width": page_width, "page_height": page_height,
                    "resolution": "unique" if uniquely else "ambiguous_first",
                    "candidate_pages": sum(1 for t in norm if opening in t),
                    "search_text": opening,
                    "printed_sha256": vol.sha256,
                }
    return None


# The columns a relocation writes, in provenance_pages order. Everything else
# on a narrative row (its identity, amount_text = the searched opening, the
# amount columns) is never written by it.
RELOCATION_COLUMNS = ("page_number", "x0", "x1", "top_pt", "bottom_pt",
                      "page_width", "page_height", "resolution",
                      "candidate_pages", "printed_document_sha256")
_GEOMETRY = ("x0", "x1", "top_pt", "bottom_pt", "page_width", "page_height")

_RELOCATION_ROWS_SQL = """
    select p.id, j.id, j.sha256, n.pe_bli, n.project_number, n.kind,
           n.xml_path, n.body, j.exhibit_family,
           p.page_number, p.x0, p.x1, p.top_pt, p.bottom_pt, p.page_width,
           p.page_height, p.resolution, p.candidate_pages,
           {printed} as printed_document_sha256
    from detail_narratives n
    join jbook_documents j on j.id = n.document_id
    join provenance_pages p
      on p.target_kind = 'narrative' and p.document_sha256 = j.sha256
     and p.pe_bli = n.pe_bli and p.narrative_kind = n.kind
     and p.xml_path = n.xml_path
    where not n.superseded and j.sha256 is not null
      and (%(fy)s::int[] is null or j.fiscal_year = any(%(fy)s::int[]))
    order by p.id
"""


def _stored_location(row) -> dict:
    return dict(zip(RELOCATION_COLUMNS, row[9:19]))


def _as_stored(hit: dict, attached_sha: str) -> dict:
    """A resolve_printed_narrative hit in provenance_pages' column shape."""
    printed = hit["printed_sha256"]
    return {
        "page_number": hit["page_number"], "x0": hit["x0"], "x1": hit["x1"],
        "top_pt": hit["top_pt"], "bottom_pt": hit["bottom_pt"],
        "page_width": hit["page_width"], "page_height": hit["page_height"],
        "resolution": hit["resolution"], "candidate_pages": hit["candidate_pages"],
        "printed_document_sha256": None if printed == attached_sha else printed,
    }


def same_location(a: dict, b: dict) -> bool:
    """Equal relocation columns; the box within 1e-6 pt (numeric vs float)."""
    for col in RELOCATION_COLUMNS:
        x, y = a[col], b[col]
        if col in _GEOMETRY:
            if (x is None) != (y is None) or (
                    x is not None and abs(float(x) - float(y)) > 1e-6):
                return False
        elif x != y:
            return False
    return True


def plan_narrative_relocations(con, *, fiscal_years: list[int] | None = None,
                               texts_for=None, printed_column: bool = True,
                               log=print) -> dict:
    """Which narrative provenance rows are not located where the narrative is
    printed, and where they belong (#195). Reads only.

    Scope: every narrative provenance row of a non-superseded narrative, in
    the given PB editions (all editions when fiscal_years is None).

    A row is KEPT when its stored page prints the narrative
    (narrative_printed_at on the stored volume: printed_document_sha256, or the
    attached document when that is null). Every other row - unresolved, or
    paged where only the opening is printed - is re-resolved across the
    attached document's book set with resolve_printed_narrative. A hit that
    differs from the stored location is a change: 'located' (was pageless) or
    'relocated' (was paged). A paged row with no hit keeps its page and counts
    'opening_only'; an unresolved row with no hit stays 'unresolved'.

    texts_for(paths) -> {path: raw page texts}, default page_texts_parallel.
    printed_column=False reads printed_document_sha256 as null: a read-only
    plan of a database that migration 022 has not reached yet.
    """
    import pdfplumber

    texts_for = texts_for or page_texts_parallel
    sql = _RELOCATION_ROWS_SQL.format(
        printed="p.printed_document_sha256" if printed_column else "null::text")
    rows = con.execute(sql, {"fy": fiscal_years}).fetchall()
    sets: dict[int, list[Volume]] = {}
    for row in rows:
        if row[1] not in sets:
            sets[row[1]] = book_set(con, row[1])
    paths = {v.sha256: v.file_path for vols in sets.values() for v in vols}
    for sha, path in paths.items():
        if not Path(path).exists():
            raise FileNotFoundError(f"document {sha} missing on disk: {path}")
    raw_by_path = texts_for(sorted(paths.values()))
    texts = {sha: (raw_by_path[p], [normalize_ws(t) for t in raw_by_path[p]])
             for sha, p in paths.items()}
    handles: dict[str, object] = {}

    def plumber_for(sha):
        if sha not in handles:
            handles[sha] = pdfplumber.open(paths[sha])
        return handles[sha]

    words_cache: dict = {}
    changes: list[dict] = []
    counts = {"rows": len(rows), "kept": 0, "located": 0, "relocated": 0,
              "opening_only": 0, "unresolved": 0}
    printed: dict[str, dict] = {}
    try:
        for row in rows:
            (pid, doc_id, sha, pe_bli, project_number, kind, xml_path, body,
             exhibit_family) = row[:9]
            stored = _stored_location(row)
            opening, closing = narrative_opening(body), narrative_closing(body)
            stored_sha = stored["printed_document_sha256"] or sha
            paged = (stored["page_number"] is not None
                     and stored["resolution"] in ("unique", "ambiguous_first"))
            if paged and stored_sha in texts and narrative_printed_at(
                    texts[stored_sha][1], stored["page_number"] - 1, opening, closing):
                counts["kept"] += 1
                continue
            hit = resolve_printed_narrative(
                sets[doc_id], texts, plumber_for, opening=opening, closing=closing,
                pe_bli=fact_anchor(pe_bli), project_number=project_number,
                exhibit_family=exhibit_family, words_cache=words_cache)
            if hit is None:
                counts["opening_only" if paged else "unresolved"] += 1
                continue
            after = _as_stored(hit, sha)
            if same_location(stored, after):
                counts["kept"] += 1
                continue
            change_kind = "relocated" if paged else "located"
            counts[change_kind] += 1
            changes.append({"id": pid, "fact_key": [sha, pe_bli, kind, xml_path],
                            "kind": change_kind, "before": stored, "after": after})
            vol = next(v for v in sets[doc_id] if v.sha256 == hit["printed_sha256"])
            entry = printed.setdefault(vol.sha256, {"title": vol.title,
                                                    "status": vol.status, "rows": 0})
            entry["rows"] += 1
    finally:
        for handle in handles.values():
            handle.close()
    scope = "all editions" if fiscal_years is None else f"PB{fiscal_years}"
    log(f"narrative relocation ({scope}): {counts}")
    return {"changes": changes, "counts": counts, "printed_volumes": printed}


def build_narrative_provenance(
    dsn: str, *, fiscal_year: int | None = None, keys=None
) -> int:
    """Resolve every non-superseded narrative lacking a narrative provenance row.

    Identity is (document_sha256, pe_bli, narrative_kind, xml_path) — the same
    key fact_id_narrative hashes. Grouped by document; each volume's text is
    extracted once per run (page_texts_parallel) and word boxes are cached per
    (volume, page). Returns rows actually inserted. Missing document files
    raise loudly.

    fiscal_year scopes the run to one PB edition's documents (Phase 5G
    per-service backfill — mirrors build_provenance_pages); None keeps the
    historical whole-corpus behavior.

    keys (#29(b), 2026-08-27) narrows to an explicit set of identity tuples
    (document_sha256, pe_bli, narrative_kind, xml_path). The multi-edition
    lineage layer needs a page anchor for a few dozen PB2017–PB2025 narratives
    — the ones a stated edge cites — out of ~18k in those editions; resolving
    all of them costs hours of pdfplumber for pages nothing links to. Scoping
    changes only WHICH rows are attempted, never how one is resolved, so a
    scoped row is identical to the row a whole-edition run would write.

    #195 (families piece-1 follow-ups, Task 23a): a narrative is located on
    the first page of its document's book set (book_set: the attached volume
    first) where narrative_located_at holds, and printed_document_sha256 names
    that volume when it is not the attached one. Only when no volume locates it
    does the pre-#195 rule decide (its opening alone, in the attached volume),
    so the rows plan_narrative_relocations would write are the rows this
    builder writes.
    """
    import pdfplumber

    inserted = 0
    texts: dict[str, tuple[list[str], list[str]]] = {}
    paths: dict[str, str] = {}
    handles: dict[str, object] = {}

    def plumber_for(sha):
        if sha not in handles:
            handles[sha] = pdfplumber.open(paths[sha])
        return handles[sha]

    with psycopg.connect(dsn) as con:
        rows = con.execute(
            """
            select j.sha256, j.file_path, n.pe_bli, n.project_number, n.kind,
                   n.xml_path, n.body, j.exhibit_family, j.id
            from detail_narratives n
            join jbook_documents j on j.id = n.document_id
            where not n.superseded and j.sha256 is not null
              and (%(fy)s::int is null or j.fiscal_year = %(fy)s)
              and not exists (
                select 1 from provenance_pages p
                where p.target_kind = 'narrative'
                  and p.document_sha256 = j.sha256 and p.pe_bli = n.pe_bli
                  and p.narrative_kind = n.kind and p.xml_path = n.xml_path
              )
            order by j.sha256
            """,
            {"fy": fiscal_year},
        ).fetchall()
        if keys is not None:
            wanted = {tuple(k) for k in keys}
            # row is (sha256, file_path, pe_bli, project_number, kind, xml_path, …)
            rows = [r for r in rows if (r[0], r[2], r[4], r[5]) in wanted]
        try:
            for sha, doc_group in groupby(rows, key=lambda r: r[0]):
                narratives = list(doc_group)
                pdf_path = Path(narratives[0][1])
                if not pdf_path.exists():
                    raise FileNotFoundError(f"document {sha} missing on disk: {pdf_path}")
                volumes = book_set(con, narratives[0][8])
                todo = [v for v in volumes if v.sha256 not in texts]
                for vol in todo:
                    if not Path(vol.file_path).exists():
                        raise FileNotFoundError(
                            f"document {vol.sha256} missing on disk: {vol.file_path}")
                raw_by_path = page_texts_parallel([v.file_path for v in todo])
                for vol in todo:
                    raw = raw_by_path[vol.file_path]
                    texts[vol.sha256] = (raw, [normalize_ws(t) for t in raw])
                    paths[vol.sha256] = vol.file_path
                words_cache: dict = {}      # (sha256, page index) -> words: book set
                attached_words: dict = {}   # page index -> words: the opening-only rule
                for (_, _, pe_bli, project_number, kind, xml_path, body,
                     exhibit_family, _doc_id) in narratives:
                    opening = narrative_opening(body)
                    hit = resolve_printed_narrative(
                        volumes, texts, plumber_for,
                        opening=opening, closing=narrative_closing(body),
                        pe_bli=fact_anchor(pe_bli), project_number=project_number,
                        exhibit_family=exhibit_family, words_cache=words_cache,
                    )
                    if hit is None:
                        hit = _resolve_narrative(
                            texts[sha][0], texts[sha][1], lambda: plumber_for(sha),
                            snippet=opening, pe_bli=fact_anchor(pe_bli),
                            project_number=project_number,
                            exhibit_family=exhibit_family,
                            words_cache=attached_words,
                        )
                    printed = hit.get("printed_sha256")
                    cur = con.execute(
                        """
                        insert into provenance_pages
                          (target_kind, document_sha256, pe_bli, project_number,
                           narrative_kind, xml_path, amount_text, page_number,
                           x0, x1, top_pt, bottom_pt, page_width, page_height,
                           resolution, candidate_pages, printed_document_sha256)
                        values ('narrative',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                %s,%s,%s)
                        on conflict (document_sha256, pe_bli, narrative_kind,
                                     xml_path)
                          where target_kind = 'narrative' do nothing
                        """,
                        (sha, pe_bli, project_number, kind, xml_path,
                         hit["search_text"], hit["page_number"], hit["x0"],
                         hit["x1"], hit["top_pt"], hit["bottom_pt"],
                         hit["page_width"], hit["page_height"],
                         hit["resolution"], hit["candidate_pages"],
                         None if printed in (None, sha) else printed),
                    )
                    inserted += cur.rowcount
        finally:
            for handle in handles.values():
                handle.close()
        con.commit()
    return inserted
