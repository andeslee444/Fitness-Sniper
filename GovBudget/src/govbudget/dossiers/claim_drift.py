"""Dossier claims that contradict their own citation (ruling R-DEC-DOSSIERDRIFT).

RULING (controller, 2026-09-26): before deploy, a published dossier claim
whose stated figure disagrees with its cited fact's CURRENT value — any fact
kind — (beyond the rounding the sentence itself shows: "about 389" vs
1,284.7 fails), or whose concentration word contradicts the band of the
cited HHI under the 2023 bands, is WITHHELD (not rewritten) by the exporter,
logged by name, and the dossier gate fails any published claim that still
contradicts its fact.

WHY THIS PARSES THE SENTENCE. The ruling prefers comparing against the value
the fact carried when the claim was authored. The raw archives
(data/research/dossiers-raw/*.json) do not record it: a claim is exactly
{"text", "citation": {"fact_id"} | {"url"}} (batch.DOSSIER_SCHEMA, measured
2026-09-26 over all 68 dossier archives; the directory's 69th file is
batch_meta.json), so the fallback applies — the figure the sentence states
is held to the fact's current value.

ONE function, `claim_contradictions`, is used by BOTH the exporter
(export_site._emit_dossier_sidecars — withholds) and the gate
(dossiers/gate.py — fails anything still published), so the two cannot
disagree about what a contradiction is.

THE SIX CHECKS
  stated_figure — on any fact whose citation row carries a current numeric
    value (`fact_current_value`, round 2 — round 1 read recorded_value
    only): a derived fact's `recorded_value`; else a workbook cell's
    `amount_thousands`; else a J-book PDF glyph's `amount_text`, parsed as
    the receipt exporter parses a printed amount
    (budget_pdf_receipts.amount). The value is read in the row's own
    `units` exactly as the site's citation card converts it
    (format.ts usdEquivalence: USD thousands x 1e3, USD millions x 1e6) —
    a row whose units are not a dollar scale (or HHI) is not checked.
    Dollar facts are held to every "$X [thousand|million|billion|trillion]"
    the sentence states; HHI facts (units "Herfindahl-Hirschman Index") to
    the number that follows an HHI anchor ("HHI", "Herfindahl-Hirschman
    Index", "concentration score"). ANY stated figure agreeing keeps the
    claim (a sentence routinely states the prior year beside the cited one
    — the convention _claim_value_still_matches already measured); a claim
    with no parseable figure has nothing to contradict. "Agreeing" = within
    half a unit of the last significant digit the sentence prints: "$4.68
    billion" is +/- $5M, "about 389" +/- 0.5, "about 1,300" +/- 50. "More
    than / over / above / at least" and "under / below / less than / up to"
    make the figure a bound instead. The sign is ignored (prose states a
    decrease as a magnitude).
  fiscal_year (round 3) — a figure that agrees with the cited value must
    not be given another fiscal year than the cited column's
    (`fiscal_year_contradicted`). The column's year: a workbook cell's
    amount_type ("fy_2025_enacted"), a J-book glyph's scenario read as the
    exporter labels detail columns (export_site._scenario_meta under the
    PB2026 fence: PriorYear FY2024, CurrentYear FY2025, BudgetYearOne[Base]
    FY2026; AllPriorYears is no year). The sentence's: "FY2026" / "FY 2026"
    / "FY26" / "fiscal year 2026", or "current / prior / budget year"
    relative to the J-book's edition, bound to a figure by a leading frame
    ("For FY2026, ... $X"), a label earlier in its clause, a trailing
    "in / for / during [the] <label>" or its own parenthesis. The claim is
    withheld when EVERY agreeing figure carries a year that is not the
    column's. Measured on /program/1203154SF/ what_it_is[3]: "For FY2026,
    ... about $243.3 million (its Current Year amount)" cites an FY 2025
    glyph (the row's FY 2026 Total is 1.916).
  concentration_band — a band word (unconcentrated / low concentration;
    moderately concentrated; highly concentrated), unless negated, must be
    the 2023 band (govbudget.hhi_band, the mirror of site/src/lib/
    hhi-band.mjs) of the cited HHI: the fact's own value when it is an HHI
    fact, else the HHI of the concentration row that minted the cited
    dollars fact. A negated word ("not highly concentrated") must NOT be it.
  top_family — a "top / leading / largest recipient family" (or "top
    recipient") claim must name, by family key or display name, the family
    the cited concentration fact's row records (top_family_all for the
    all-links fids, top_family_high for the high-only fids). A fact that
    records no family is not checked.
  recipient_list (round 2) — a sentence that names the recipients of the
    program's awards ("recipients ... include A, B and C", "awards went to
    A and B", "A is a recipient linked to this budget line") must name only
    recipients THE PAGE lists: every named recipient must be among the
    page's linked-award recipient families (`PageRecipients`, read from the
    same fct_budget_to_awards rows the page's Related awards table lists,
    split-key-scoped like export_site._awards_for). A name matches when,
    normalized (`_name_tokens`: case, punctuation, "the"/"and" and legal
    forms dropped), it equals or extends — or is extended by — a linked
    award's recipient_name, family key or family display name, or when
    entity_xwalk files that name under a family the page links (a
    subsidiary named by its own registration). This check reads the page,
    not the cited fact: the claim's citation cannot vouch for names the
    page's award records do not carry.
  lobbying_mention (R-DEC-DOSSIERLDA, final-review ruling 2026-09-27) — a
    LOBBYING claim (it cites an lda_filing fact, or its text says "lobby…" /
    "LDA") must name only lobbying filers THE PAGE's lobbying mentions list.
    A filer is any Senate LDA client, registrant or verified family name in
    audit_lda_filings — the whole filing universe (`FilerUniverse`), so a
    filer whose every mention of this program the #176 rematch removed is
    still recognised — read as a capitalized run of the sentence (the longest
    name wins; a one-word name shorter than three letters, all digits or as
    generic as "Aerospace" never counts). The page lists a filer when its
    fct_program_lobbying rows (the program_details `mentions` rows: client,
    family and, through audit_lda_filings, registrant) carry that name, one
    extending it or extended by it, or the filer's verified family
    (`PageLobbying`); a shared code's member page lists none (R-INT-9).
    Measured on /program/2004/ players[1] ("Additional FedEx Corporation
    filings in 2024 …", CVN-81, which lists no mention after the rematch) and
    /program/1045/ players[5] ("A FedEx Corporation filing matched the term
    '1045' …", a page listing General Dynamics and Huntington Ingalls only).

FAIL CLOSED (round 2). `concentration_fact_index`,
`linked_recipient_index` and `lobbying_mention_index` RAISE
ClaimDriftIndexError when a duckdb_path was
supplied and the read fails; only duckdb_path=None means "no mart, leg not
run". An empty index silently skipped the family leg, and one chain-G
contradiction (0603467E "The top recipient family ... is Raytheon") is
caught by that leg alone.

LIMITS (R-DEC-GATE-LIMIT applies: a regex cannot parse all English). Other
units (percent, counts) are not parsed; a figure written in words ("two
billion") is not read; the fiscal-year leg reads only a year the sentence
binds to the figure as above (a bare "the 2025 enacted level" is not a
label, a year followed by a capitalized word — "the FY2016 SSNs" — is a
name's, a range or list of years names no one year, and a "current year" on
a workbook cell is not read: its row records the column's year but not the
book's edition), and a derived fact records a formula, not a column, so it
is not checked for its year; a recipient list is read only in the three shapes
above, and a list item is everything between commas (or "and") up to the
end of the sentence — a clause trailing the last name ("... and Leidos for
engineering support") is read as part of that name, which then fails to
match: the direction that withholds. The lobbying leg reads a filer only by
a name the LDA data records (a nickname such as "GD" is not read), only in a
sentence that cites an LDA filing or says "lobby…" / "LDA", and a filer name
that is also an award recipient's is held to the lobbying list only there.
Adversarial prose review remains the backstop.
"""
from __future__ import annotations

import html
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from govbudget.hhi_band import hhi_band_key

HHI_UNITS = "Herfindahl-Hirschman Index"


class ClaimDriftIndexError(RuntimeError):
    """A mart the claim-drift legs were told to read could not be read.

    Raised (never swallowed into an empty index) whenever a duckdb_path was
    supplied: an empty index would skip the family / recipient legs without
    a word, and the gate would pass claims those legs alone can fail."""


#: dollars per unit of a fact's `units` — format.ts usdEquivalence's scales
_FACT_DOLLAR_SCALE = {
    "USD": 1.0,
    "USD thousands": 1e3,
    "USD millions": 1e6,
    "USD billions": 1e9,
}

_WORD_SCALE = {
    "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12,
    "k": 1e3, "m": 1e6, "b": 1e9,
}

_NUM = r"\d[\d,]*(?:\.\d+)?"

_DOLLAR_RE = re.compile(
    r"\$\s?(?P<num>" + _NUM + r")\b"
    r"(?:\s*(?P<scale>thousand|million|billion|trillion|[kmb](?![a-z])))?",
    re.IGNORECASE,
)

_HHI_ANCHOR = (
    r"(?:\bHHI\b|Herfindahl[\s-]*Hirschman(?:\s+Index)?"
    r"|\bconcentration\s+(?:score|index)\b)"
)
# The first number after an anchor, across at most 40 characters of words and
# brackets (no digit, full stop, semicolon or dollar sign in between) — never
# a count of families/awards or a percentage.
_HHI_FIGURE_RE = re.compile(
    _HHI_ANCHOR + r"[^.;$\d]{0,40}?(?<![\w$])(?P<num>" + _NUM + r")\b"
    r"(?!\s*(?:%|percent|recipient|famil|award|contract|compan|firm|vendor))",
    re.IGNORECASE,
)

_LOWER_BOUND_RE = re.compile(
    r"\b(?:more than|over|above|at least|exceeding|in excess of)\s*$", re.IGNORECASE)
_UPPER_BOUND_RE = re.compile(
    r"\b(?:less than|under|below|up to|no more than)\s*$", re.IGNORECASE)

_BAND_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("unconcentrated", re.compile(
        r"\bunconcentrated\b|\blow(?:ly)?[\s-]+concentrat\w*", re.IGNORECASE)),
    ("moderate", re.compile(
        r"\bmoderate(?:ly)?[\s-]+concentrat\w*", re.IGNORECASE)),
    ("concentrated", re.compile(
        r"\b(?:high(?:ly)?|heavily)[\s-]+concentrat\w*", re.IGNORECASE)),
)
_NEGATION_RE = re.compile(
    r"\b(?:not|never|no longer|isn't|wasn't|aren't|rather than|instead of)"
    r"\s+(?:\w+\s+)?$",
    re.IGNORECASE,
)

_TOP_FAMILY_RE = re.compile(
    r"\b(?:top|leading|largest|biggest|dominant)\s+(?:\w+\s+){0,2}?"
    r"(?:recipient|contractor|vendor)\s+famil(?:y|ies)\b"
    r"|\b(?:top|leading|largest|biggest|dominant)\s+famil(?:y|ies)\b"
    r"|\b(?:top|leading|largest|biggest|dominant)\s+recipient\b",
    re.IGNORECASE,
)


def _parse_num(raw: str) -> tuple[float, float] | None:
    """(value, half a unit of the last significant digit printed)."""
    s = raw.rstrip(",").replace(",", "")
    try:
        value = float(s)
    except ValueError:
        return None
    if "." in s:
        return value, 0.5 * 10 ** -len(s.split(".", 1)[1])
    stripped = s.rstrip("0")
    zeros = len(s) - len(stripped) if stripped else 0
    return value, 0.5 * 10 ** zeros


def _bound(text: str, start: int) -> str:
    before = text[max(0, start - 24):start]
    if _LOWER_BOUND_RE.search(before):
        return "lower"
    if _UPPER_BOUND_RE.search(before):
        return "upper"
    return "nominal"


def _agrees(stated: float, tol: float, bound: str, actual: float) -> bool:
    target = abs(actual)
    tol = tol + 1e-9 * max(target, 1.0)
    if bound == "lower":
        return target >= stated - tol
    if bound == "upper":
        return target <= stated + tol
    return abs(stated - target) <= tol


def _dollar_figure_spans(text: str) -> list[tuple[int, int, float, float, str]]:
    """[(start, end, dollars, tolerance in dollars, bound)] per "$X [scale]"."""
    out = []
    for m in _DOLLAR_RE.finditer(text):
        parsed = _parse_num(m.group("num"))
        if parsed is None:
            continue
        value, half = parsed
        scale = _WORD_SCALE.get((m.group("scale") or "").lower(), 1.0)
        out.append((m.start(), m.end(), value * scale, half * scale,
                    _bound(text, m.start())))
    return out


def stated_dollar_figures(text: str) -> list[tuple[float, float, str]]:
    """[(dollars, tolerance in dollars, bound)] for every "$X [scale]"."""
    return [(v, t, b) for _s, _e, v, t, b in _dollar_figure_spans(text)]


def stated_hhi_figures(text: str) -> list[tuple[float, float, str]]:
    """[(index points, tolerance, bound)] for each number an HHI anchor states."""
    out = []
    seen: set[int] = set()
    for m in _HHI_FIGURE_RE.finditer(text):
        if m.start("num") in seen:
            continue
        seen.add(m.start("num"))
        parsed = _parse_num(m.group("num"))
        if parsed is None:
            continue
        value, half = parsed
        out.append((value, half, _bound(text, m.start("num"))))
    return out


def stated_band_words(text: str) -> list[tuple[str, bool]]:
    """[(band key, negated)] for each concentration word the sentence uses."""
    out = []
    for key, pat in _BAND_PATTERNS:
        for m in pat.finditer(text):
            negated = bool(_NEGATION_RE.search(text[max(0, m.start() - 30):m.start()]))
            out.append((key, negated))
    return out


def names_top_family(text: str) -> bool:
    return bool(_TOP_FAMILY_RE.search(text))


def _names(text: str, name: str | None) -> bool:
    if not name or len(name) < 3:
        return False
    return bool(re.search(
        r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", text, re.IGNORECASE))


def _numeric(value) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _printed_amount(text) -> float | None:
    """A J-book glyph's value, parsed exactly as the receipt exporter parses a
    printed amount (budget_pdf_receipts.amount: "1,234.5", "(1,234)" -> the
    magnitude); None for anything that is not a number."""
    if not isinstance(text, str):
        return None
    from govbudget.budget_pdf_receipts import amount

    return amount(text.strip())


def fact_current_value(fact: Mapping | None):
    """(field, raw value, value as a float) of the citation row's CURRENT
    numeric value, or None when the row carries none.

    One value per row, in this order: recorded_value (derived facts and the
    LDA rows that carry one), amount_thousands (workbook cells), amount_text
    (J-book PDF glyphs, parsed as the receipt exporter parses them). The
    float is in the row's own `units`; fact_comparison_value scales it."""
    if not fact:
        return None
    for field_name, parse in (
        ("recorded_value", _numeric),
        ("amount_thousands", _numeric),
        ("amount_text", _printed_amount),
    ):
        raw = fact.get(field_name)
        if raw is None:
            continue
        value = parse(raw)
        if value is not None:
            return field_name, raw, value
    return None


def fact_comparison_value(fact: Mapping | None) -> tuple[str, float] | None:
    """("dollars", $) or ("hhi", points) for the fact's current value, read in
    its own units (USD thousands x 1e3, USD millions x 1e6 — the site's
    usdEquivalence); None when there is no value or the units are neither a
    dollar scale nor the HHI."""
    current = fact_current_value(fact)
    if current is None:
        return None
    units = fact.get("units") or ""
    scale = _FACT_DOLLAR_SCALE.get(units)
    if scale is not None:
        return "dollars", current[2] * scale
    if units == HHI_UNITS:
        return "hhi", current[2]
    return None


def cited_value(fact: Mapping | None):
    """The raw current value the checks compared with (for logs and the
    sidecar's withheld_claims), or None."""
    current = fact_current_value(fact)
    return current[1] if current else None


# ---------------------------------------------------------------------------
# Fiscal-year labels (round 3)
# ---------------------------------------------------------------------------

#: "FY2026" / "FY 2026" / "FY26", "fiscal year 2026" / "Fiscal year (FY) 2026",
#: and the book-relative "current year" / "prior year" / "budget year" (the
#: J-book's own column names). "year-over-year", "prior years" and "all
#: prior year(s)" are not labels.
_FY_LABEL_RE = re.compile(
    r"(?<![\w-])(?:"
    r"FY\s?'?(?P<fy>\d{4}|\d{2})(?!\w)"
    r"|fiscal\s+(?:year\s+)?(?:\(FY\)\s+)?(?P<fiscal>(?:19|20)\d{2})(?!\d)"
    r"|(?P<rel>current|prior|budget)[\s-]+year(?![\w-])"
    r")",
    re.IGNORECASE,
)
#: years back from the edition each book-relative column is (the exporter's
#: _scenario_meta: PriorYear = N-2, CurrentYear = N-1, BudgetYearOne = N)
_RELATIVE_OFFSET = {"prior": 2, "current": 1, "budget": 0}
#: "FY2024-2026", "FY2023-FY2027", "FY24–27", "FY 2020 to 2024": a range,
#: no single year (the second label of "FY2023-FY2027" is not matched at all:
#: _FY_LABEL_RE never starts right after a hyphen)
_RANGE_TAIL_RE = re.compile(
    r"\s*(?:[-–—/]|to\b|through\b)\s*(?:FY\s?)?'?\d{2,4}\b", re.IGNORECASE)
#: two labels joined as a range or a list ("FY2023-FY2027", "FY 2020 to FY
#: 2024", "FY2024 and FY2025"): neither names the one year of a figure
_PAIR_GAP_RE = re.compile(r"\s*(?:[-–—/,&]|to|through|and|or)\s*", re.IGNORECASE)
#: a period label is followed by punctuation, a lower-case word or the end —
#: never a capitalized word, which makes the year a name's ("the FY2016
#: SSNs", "the FY26 National Defense Authorization Act")
_LABEL_TAIL_OK_RE = re.compile(r"\s*$|\s*[^\w\s]|\s+[a-z]")
#: "... $X [requested|enacted|funded|spent ...] in / for / during [the] <label>"
_TRAIL_RE = re.compile(
    r"\s*,?\s*(?:(?:was|were|is|are)\s+)?(?:actually\s+)?"
    r"(?:(?:requested|enacted|appropriated|budgeted|funded|spent|provided|planned"
    r"|programmed|obligated|recorded)\s+)?"
    r"(?:in|for|during)\s+(?:the\s+)?(?:coming\s+|upcoming\s+)?",
    re.IGNORECASE,
)
#: a label chained to the one before it ("current year (FY2025)", "the FY2026
#: budget year")
_CHAIN_RE = re.compile(r"\s*\(?\s*")
_CLAUSE_BREAK_RE = re.compile(r"[,;:—–]|\s-\s|\.\s")
_SENTENCE_BREAK_RE = re.compile(r"(?<![A-Z])\.\s+(?=[A-Z])")
_OPEN_PAREN_RE = re.compile(r"\s*\(")


def _column_meta():
    """The exporter's own column labellers and its edition fence — ONE
    definition of what year a workbook amount_type or a J-book scenario is."""
    from govbudget.export_site import _SUMMARY_EDITION, _amount_type_meta, _scenario_meta

    return _SUMMARY_EDITION, _amount_type_meta, _scenario_meta


def fact_fiscal_year(fact: Mapping | None) -> int | None:
    """The fiscal year of the column a cited fact was read from, or None.

    A workbook cell records it in its amount_type ("fy_2025_enacted" ->
    2025), read by export_site._amount_type_meta. A J-book glyph records only
    its scenario — no column year of its own — so the year is derived the
    way the exporter labels detail columns: export_site._scenario_meta(
    scenario, _SUMMARY_EDITION), the PB2026 fence every jbook_pdf citation
    is minted under (CurrentYear -> FY2025). AllPriorYears is no single year;
    a derived fact records a formula, not a column: both None."""
    if not fact:
        return None
    edition, amount_type_meta, scenario_meta = _column_meta()
    if fact.get("amount_type"):
        return amount_type_meta(fact["amount_type"], edition)[0]
    if fact.get("scenario"):
        return scenario_meta(fact["scenario"], edition)[0]
    return None


def _relative_edition(fact: Mapping) -> int | None:
    """The edition a "current / prior / budget year" in the sentence is
    relative to: known for a J-book glyph (the PB2026 fence), not for a
    workbook cell, whose citation row records its column's year but not
    the book it was read from — so there the relative words are not read."""
    if fact.get("scenario") and not fact.get("amount_type"):
        return _column_meta()[0]
    return None


def fiscal_year_labels(text: str, edition: int | None) -> list[tuple[int, int, int | None]]:
    """[(start, end, year)] for each fiscal-year label that names ONE year of
    a period; a book-relative label's year is None when `edition` is."""
    raw: list[tuple[int, int, int | None]] = []
    for m in _FY_LABEL_RE.finditer(text):
        if not _LABEL_TAIL_OK_RE.match(text, m.end()):
            continue
        rel = m.group("rel")
        if rel:
            if re.search(r"\ball[\s-]+$", text[max(0, m.start() - 5):m.start()], re.I):
                continue
            year = None if edition is None else edition - _RELATIVE_OFFSET[rel.lower()]
        else:
            digits = m.group("fy") or m.group("fiscal")
            year = int(digits) if len(digits) == 4 else 2000 + int(digits)
        raw.append((m.start(), m.end(), year))
    drop: set[int] = set()
    for i, (_s, e, _y) in enumerate(raw):
        if _RANGE_TAIL_RE.match(text, e):
            drop.add(i)
        if i + 1 < len(raw) and _PAIR_GAP_RE.fullmatch(text[e:raw[i + 1][0]]):
            drop |= {i, i + 1}
    return [r for i, r in enumerate(raw) if i not in drop]


def _figure_groups(text: str) -> list[dict]:
    """Dollar figures, each with the parenthesis right after it and the
    figures inside that parenthesis ("$2,346,905 thousand (about $2.3
    billion)", "$243.3 million (its Current Year amount)") — one stated
    amount, one set of labels."""
    figs = _dollar_figure_spans(text)
    groups: list[dict] = []
    i = 0
    while i < len(figs):
        start, end = figs[i][0], figs[i][1]
        members = [figs[i]]
        paren = None
        j = i + 1
        m = _OPEN_PAREN_RE.match(text, end)
        if m:
            close = text.find(")", m.end())
            if close != -1:
                paren = (m.end(), close)
                while j < len(figs) and figs[j][0] < close:
                    members.append(figs[j])
                    j += 1
                end = close + 1
        groups.append({"start": start, "end": end, "figures": members, "paren": paren})
        i = j
    return groups


def _group_years(text: str, groups: list[dict], labels) -> list[set]:
    """The years the sentence binds to each figure group:
      - a label inside the group's own parenthesis;
      - a trailing "in / for / during [the] <label>" (after an optional
        "requested", "enacted", "funded", "spent" ...), and any label chained
        right after it ("the current year (FY2025)", "the FY2026 budget
        year") — such a label is the group's, never the next group's;
      - the nearest other label before the group and after the previous
        group: a sentence's opening frame ("For FY2026, ... $X", "In FY2024
        the program recorded $X") binds the first group across commas; a
        later label binds only inside its clause (no comma, semicolon, colon
        or dash between it and the figure)."""
    at = {s: (s, e, y) for s, e, y in labels}
    consumed: set[int] = set()
    years: list[set] = [set() for _ in groups]
    for gi, g in enumerate(groups):
        if g["paren"]:
            for s, _e, y in labels:
                if g["paren"][0] <= s < g["paren"][1]:
                    consumed.add(s)
                    years[gi].add(y)
        m = _TRAIL_RE.match(text, g["end"])
        pos = m.end() if m else -1
        while pos in at:
            s, e, y = at[pos]
            consumed.add(s)
            years[gi].add(y)
            c = _CHAIN_RE.match(text, e)
            pos = c.end() if c and c.end() > e else -1
    for gi, g in enumerate(groups):
        lo = groups[gi - 1]["end"] if gi else 0
        for s, e, y in reversed(labels):
            if s < lo or e > g["start"] or s in consumed:
                continue
            gap = text[e:g["start"]]
            if gi == 0:
                if not _SENTENCE_BREAK_RE.search(gap):
                    years[gi].add(y)
            elif not _CLAUSE_BREAK_RE.search(gap):
                years[gi].add(y)
            break
    return years


def fiscal_year_contradicted(text: str, fact: Mapping | None) -> bool:
    """True when the sentence gives the cited value a fiscal year its column
    is not: every stated figure that agrees with the cited value carries a
    year (explicit, or book-relative on a J-book glyph) other than the
    column's. One agreeing figure that carries no year, or only the
    column's, keeps the claim (the stated_figure leg's "any agreeing figure"
    convention); a figure that does not agree with the value is the
    stated_figure leg's, not this one's. Facts with no column year are not
    checked (fact_fiscal_year)."""
    if not fact:
        return False
    fy = fact_fiscal_year(fact)
    current = fact_comparison_value(fact)
    if fy is None or current is None or current[0] != "dollars":
        return False
    labels = fiscal_year_labels(text, _relative_edition(fact))
    if not labels:
        return False
    groups = _figure_groups(text)
    agreeing = [
        ys for g, ys in zip(groups, _group_years(text, groups, labels))
        if any(_agrees(v, t, b, current[1]) for _s, _e, v, t, b in g["figures"])
    ]
    return bool(agreeing) and all(
        any(y is not None and y != fy for y in ys) for ys in agreeing)


def fact_column_index(citations_parquet: str | Path | None) -> dict[str, dict]:
    """{fact_id: {"scenario", "amount_type"}} for every citation row that
    records a column, read-only from citations.parquet — the same 27-column
    rows export-site builds `citation_facts` from (indexes 25 and 26), which
    citations.json does not carry. The gate reads the fiscal-year leg's input
    here.

    None -> {} (the leg does not run). A supplied path that cannot be read
    RAISES ClaimDriftIndexError (fail closed, as the mart reads do)."""
    if citations_parquet is None:
        return {}
    import duckdb

    path = Path(citations_parquet)
    what = "citations.parquet's scenario / amount_type columns"
    if not path.is_file():
        raise _read_error(what, path, FileNotFoundError(f"no file at {path}"))
    con = duckdb.connect()
    try:
        rows = con.execute(
            "select fact_id, scenario, amount_type from read_parquet(?)"
            " where scenario is not null or amount_type is not null",
            [str(path)],
        ).fetchall()
    except Exception as exc:
        raise _read_error(what, path, exc) from exc
    finally:
        con.close()
    return {fid: {"scenario": sc, "amount_type": at} for fid, sc, at in rows}


# ---------------------------------------------------------------------------
# Recipient lists
# ---------------------------------------------------------------------------

_LEGAL_FORMS = frozenset({
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LLC",
    "LLP", "LP", "LTD", "LIMITED", "PLC",
})
_NAME_FILLER = frozenset({"THE", "AND"})
# a one-word name this generic never matches by extension ("University")
_GENERIC_TOKENS = frozenset({
    "UNIVERSITY", "GENERAL", "NATIONAL", "AMERICAN", "UNITED", "INTERNATIONAL",
    "SYSTEMS", "TECHNOLOGIES", "TECHNOLOGY", "SERVICES", "SOLUTIONS", "GROUP",
    "INSTITUTE", "DEFENSE", "RESEARCH", "LABORATORY", "LABORATORIES", "HOLDINGS",
})

_LIST_TRIGGERS: tuple[re.Pattern[str], ...] = (
    # "Recorded recipients of awards linked to the program include A, B ..."
    re.compile(
        r"\brecipients?\b[^.;:]{0,120}?\binclud(?:e|es|ed|ing)\b\s*:?\s*(?P<names>.+)",
        re.IGNORECASE | re.DOTALL),
    # "Other large awards went to A and B" / "the largest award ... went to A"
    re.compile(
        r"\bawards?\b[^;]{0,120}?\bwent\s+to\b\s*(?P<names>.+)",
        re.IGNORECASE | re.DOTALL),
)
# "A is a recipient linked to this budget line through contract records."
_SINGLE_TRIGGER = re.compile(
    r"^\s*(?P<names>[^;:]{2,200}?)\s+(?:is|are)\s+(?:a|an|the|one\s+of\s+the)\s+"
    r"recipients?\s+(?:linked|tied|connected)\b",
    re.IGNORECASE | re.DOTALL,
)
_CLAUSE_END_RE = re.compile(
    r";|\s[—–]\s|\s--\s|,?\s+among\s+others\b|,?\s+and\s+others\b"
    r"|,?\s+according\s+to\b|,\s*(?:which|who|each|all\s+of\s+which)\b",
    re.IGNORECASE,
)
_ABBREVIATION_TAIL_RE = re.compile(
    r"(?:\b(?:inc|corp|co|ltd|jr|sr|st|no)|\b[a-z])$", re.IGNORECASE)


def _name_tokens(name: str | None) -> tuple[str, ...]:
    """A recipient name, normalized for comparison: upper case, "&" as a
    word, periods and apostrophes removed ("L.L.C." -> LLC), punctuation as
    spaces, and "the", "and" and legal forms (Inc, Corp, LLC, ...) dropped."""
    if not name:
        return ()
    s = html.unescape(str(name)).upper().replace("&", " AND ")
    s = re.sub(r"[.'’]", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return tuple(t for t in s.split() if t not in _LEGAL_FORMS and t not in _NAME_FILLER)


def _extends(longer: tuple[str, ...], shorter: tuple[str, ...]) -> bool:
    """True when `longer` begins with the whole of `shorter` (word-aligned) —
    a subsidiary or longer registration of a family ("NORTHROP GRUMMAN
    SYSTEMS" extends "NORTHROP GRUMMAN"). A one-word generic prefix
    ("UNIVERSITY") or one under four letters never counts."""
    if not shorter or len(shorter) >= len(longer) or longer[:len(shorter)] != shorter:
        return False
    if len(" ".join(shorter)) < 4:
        return False
    return not (len(shorter) == 1 and shorter[0] in _GENERIC_TOKENS)


def _sentence_head(s: str) -> str:
    """`s` up to the end of its sentence: the first ". " followed by a capital
    whose preceding word is not an abbreviation (Inc., Corp., a middle
    initial)."""
    for m in re.finditer(r"\.\s+(?=[A-Z])", s):
        if not _ABBREVIATION_TAIL_RE.search(s[:m.start()]):
            return s[:m.start()]
    return s


def _strip_sentence_end(s: str) -> str:
    """Drop trailing punctuation and the sentence's own full stop — but not
    the period of an abbreviation that ends the name ("INDYNE, INC.")."""
    while True:
        s2 = s.strip().rstrip(",;:").strip()
        if s2.endswith(".") and not _ABBREVIATION_TAIL_RE.search(s2[:-1]):
            s2 = s2[:-1]
        if s2 == s:
            return s
        s = s2


def _legal_form_prefix(seg: str) -> tuple[str, str]:
    """("LLC", "Boeing") for "LLC and Boeing": the legal-form words a comma
    split off the name before them, and whatever follows."""
    words = seg.split()
    i = 0
    while i < len(words) and re.sub(r"[.,]", "", words[i]).upper() in _LEGAL_FORMS:
        i += 1
    return " ".join(words[:i]), " ".join(words[i:])


def _list_items(names_text: str) -> list[tuple[str, list[str]]]:
    """[(item as printed, its " and "-parts)] for one list of names."""
    s = re.sub(r"\s*\([^)]*\)", "", names_text)
    s = _sentence_head(s)
    s = _CLAUSE_END_RE.split(s, maxsplit=1)[0]
    s = _strip_sentence_end(re.sub(r"\s+", " ", s))
    merged: list[str] = []
    for seg in s.split(","):
        seg = seg.strip()
        legal, rest = _legal_form_prefix(seg)
        if legal and merged:
            merged[-1] = f"{merged[-1]}, {legal}"  # "CACI TECHNOLOGIES, LLC"
            seg = rest
        seg = re.sub(r"^(?:and|or)\s+", "", seg.strip(), flags=re.IGNORECASE).strip()
        if _name_tokens(seg):
            merged.append(seg)
    items: list[tuple[str, list[str]]] = []
    for item in merged:
        item = _strip_sentence_end(item)
        parts = [p.strip() for p in re.split(r"\s+and\s+", item) if _name_tokens(p)]
        items.append((item, parts if len(parts) > 1 else []))
    return items


def _recipient_items(text: str) -> list[tuple[str, list[str]]]:
    items: list[tuple[str, list[str]]] = []
    for pat in _LIST_TRIGGERS:
        for m in pat.finditer(text):
            items.extend(_list_items(m.group("names")))
    m = _SINGLE_TRIGGER.search(text)
    if m:
        items.extend(_list_items(m.group("names")))
    seen: set[str] = set()
    out = []
    for item in items:
        if item[0] not in seen:
            seen.add(item[0])
            out.append(item)
    return out


def named_recipients(text: str) -> list[str]:
    """The recipients a recipient-list sentence names, as printed: each list
    item, or an item's " and "-parts when it has them ("SYSTEM HIGH
    CORPORATION and CACI TECHNOLOGIES, LLC")."""
    out: list[str] = []
    for whole, parts in _recipient_items(text):
        out.extend(parts or [whole])
    return out


@dataclass(frozen=True)
class PageRecipients:
    """The recipients one program page lists: its Related awards links'
    recipient names, their families and the families' display names."""

    names: frozenset[tuple[str, ...]]
    families: frozenset[str]
    family_by_name: Mapping[str, frozenset[str]] = field(default_factory=dict)

    @classmethod
    def from_links(
        cls,
        links: Iterable[tuple[str | None, str | None, str | None]],
        family_by_name: Mapping[str, frozenset[str]] | None = None,
    ) -> PageRecipients:
        """links: (recipient_name, family_key, family display_name) per award."""
        names: set[tuple[str, ...]] = set()
        families: set[str] = set()
        for recipient_name, family_key, display_name in links:
            for n in (recipient_name, family_key, display_name):
                toks = _name_tokens(n)
                if toks:
                    names.add(toks)
            if family_key:
                families.add(family_key)
        return cls(frozenset(names), frozenset(families), family_by_name or {})

    def lists(self, name: str, *, by_extension: bool = True) -> bool:
        """True when the page's links carry `name`: the same normalized name,
        one extending it or extended by it (by_extension), or a name
        entity_xwalk files under a family the page links."""
        toks = _name_tokens(name)
        if not toks:
            return True
        if toks in self.names:
            return True
        if by_extension and any(_extends(toks, n) or _extends(n, toks) for n in self.names):
            return True
        return bool(self.family_by_name.get(" ".join(toks), frozenset()) & self.families)

    def item_unlisted(self, whole: str, parts: list[str]) -> list[str]:
        """The names of one list item the page does not list. An item joined
        by "and" is either its parts ("SYSTEM HIGH and CACI") or one name that
        contains "and" ("Test & Evaluation Services and Technologies") — the
        latter only on an exact match, never by extension, so "SYSTEM HIGH
        CORPORATION and CACI" cannot pass on SYSTEM HIGH alone."""
        if not parts:
            return [] if self.lists(whole) else [whole]
        missing = [p for p in parts if not self.lists(p)]
        if not missing or self.lists(whole, by_extension=False):
            return []
        return [whole] if len(missing) == len(parts) else missing


class RecipientIndex:
    """Page slug -> PageRecipients, with the entity_xwalk name -> family index
    every page shares. A page with no links lists no recipients (an empty,
    still-checking PageRecipients), never None."""

    def __init__(
        self,
        links_by_page: Mapping[str, list[tuple[str | None, str | None, str | None]]],
        family_by_name: Mapping[str, frozenset[str]],
    ):
        self._links = links_by_page
        self._family_by_name = family_by_name
        self._pages: dict[str, PageRecipients] = {}

    def for_page(self, page: str) -> PageRecipients:
        if page not in self._pages:
            self._pages[page] = PageRecipients.from_links(
                self._links.get(page, []), self._family_by_name)
        return self._pages[page]


def unlinked_recipients(text: str, page: PageRecipients) -> list[str]:
    """Every recipient the sentence names that the page's links do not."""
    out: list[str] = []
    for whole, parts in _recipient_items(text):
        out.extend(page.item_unlisted(whole, parts))
    return out


# ---------------------------------------------------------------------------
# Lobbying mentions (R-DEC-DOSSIERLDA)
# ---------------------------------------------------------------------------

#: the words that make a sentence a lobbying claim when it cites no LDA filing
_LOBBYING_WORDS_RE = re.compile(
    r"\blobb(?:y|ied|ies|ying|yists?)\b|\bLDA\b", re.IGNORECASE)
#: a one-word filer name this generic is never read as a name in prose
#: ("Aerospace lobbying rose ..."); the recipient leg's list plus the LDA
#: universe's own generic one-word client
_FILER_GENERIC_TOKENS = _GENERIC_TOKENS | frozenset({"AEROSPACE"})
_WORD_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.'’]*[A-Za-z0-9])?|&")
_POSSESSIVE_RE = re.compile(r"['’]s$", re.IGNORECASE)
#: legal-form words right after a matched name are printed with it
#: ("FedEx Corporation"); they are not part of the normalized name
_LEGAL_TAIL_RE = re.compile(
    r"(?:,?\s+(?:" + "|".join(sorted(_LEGAL_FORMS)) + r")\b)+", re.IGNORECASE)


def _word_tokens(text) -> tuple[list[tuple[str, int, int]], str]:
    """([(token, start, end)] per word, the unescaped text the offsets are
    in): each word normalized as `_name_tokens` normalizes a name (upper
    case, periods and apostrophes removed, "the" / "and" / "&" and legal
    forms dropped), and a possessive "'s" dropped ("FedEx's" -> FEDEX)."""
    s = html.unescape(str(text or ""))
    out: list[tuple[str, int, int]] = []
    for m in _WORD_RE.finditer(s):
        word = _POSSESSIVE_RE.sub("", m.group(0))
        tok = re.sub(r"[.'’]", "", word).upper()
        if not tok or tok == "&" or tok in _LEGAL_FORMS or tok in _NAME_FILLER:
            continue
        out.append((tok, m.start(), m.end()))
    return out, s


def _filer_tokens(name) -> tuple[str, ...]:
    """A filer name, normalized for comparison (see _word_tokens)."""
    return tuple(t for t, _s, _e in _word_tokens(name)[0])


def _nameable(toks: tuple[str, ...]) -> bool:
    """False for a one-word name too short, numeric or generic to be read as
    a name in prose, and for any name made of digits alone."""
    if not toks or all(t.isdigit() for t in toks):
        return False
    if len(toks) == 1:
        t = toks[0]
        return len(t) >= 3 and t not in _FILER_GENERIC_TOKENS
    return True


@dataclass(frozen=True)
class FilerUniverse:
    """Every Senate LDA filer name the lake records — each filing's client,
    registrant and verified family — normalized, with the verified families
    each name belongs to (empty for an outside registrant, which files for
    many clients and belongs to none of them)."""

    families: Mapping[tuple[str, ...], frozenset[str]]
    max_len: int = 0

    @classmethod
    def from_filings(
        cls, filings: Iterable[tuple[str | None, str | None, str | None]],
    ) -> FilerUniverse:
        """filings: (client_name, registrant_name, verified family_key or
        None) per filing. A registrant takes the client's family only when it
        IS the client (a self-filer: FEDEX CORPORATION for itself)."""
        fams: dict[tuple[str, ...], set[str]] = {}
        for client, registrant, family in filings:
            ct, rt, ft = _filer_tokens(client), _filer_tokens(registrant), _filer_tokens(family)
            for toks, of_family in ((ct, True), (rt, rt == ct), (ft, True)):
                if not toks:
                    continue
                entry = fams.setdefault(toks, set())
                if family and of_family:
                    entry.add(family)
        return cls({k: frozenset(v) for k, v in fams.items()},
                   max((len(k) for k in fams), default=0))


def named_lobbying_filers(text: str, universe: FilerUniverse) -> list[str]:
    """The LDA filers the sentence names, as printed: each longest run of
    words that is a filer name in `universe` and starts with a capital or a
    digit (a name, not a common word), with any legal form printed after it
    ("General Dynamics Corporation"). Non-overlapping, in sentence order."""
    toks, s = _word_tokens(text)
    out: list[str] = []
    i = 0
    while i < len(toks):
        hit = 0
        for k in range(min(universe.max_len, len(toks) - i), 0, -1):
            cand = tuple(t for t, _s, _e in toks[i:i + k])
            if cand in universe.families and _nameable(cand):
                hit = k
                break
        first = s[toks[i][1]] if hit else ""
        if hit and (first.isupper() or first.isdigit()):
            start, end = toks[i][1], toks[i + hit - 1][2]
            tail = _LEGAL_TAIL_RE.match(s, end)
            out.append(s[start:tail.end() if tail else end])
            i += hit
        else:
            i += 1
    return out


@dataclass(frozen=True)
class PageLobbying:
    """The lobbying filers one program page lists: its mention rows' client
    names, family keys and registrant names, and their families."""

    names: frozenset[tuple[str, ...]]
    families: frozenset[str]
    universe: FilerUniverse

    @classmethod
    def from_mentions(
        cls,
        mentions: Iterable[tuple[str | None, str | None, str | None]],
        universe: FilerUniverse,
    ) -> PageLobbying:
        """mentions: (client_name, family_key, registrant_name) per row."""
        names: set[tuple[str, ...]] = set()
        families: set[str] = set()
        for client, family, registrant in mentions:
            for n in (client, family, registrant):
                toks = _filer_tokens(n)
                if toks:
                    names.add(toks)
            if family:
                families.add(family)
        return cls(frozenset(names), frozenset(families), universe)

    def lists(self, name: str) -> bool:
        """True when a mention row on the page carries `name`: the same
        normalized name, one extending it or extended by it, or a row of the
        name's verified family."""
        toks = _filer_tokens(name)
        if not toks or toks in self.names:
            return True
        if any(_extends(toks, n) or _extends(n, toks) for n in self.names):
            return True
        return bool(self.universe.families.get(toks, frozenset()) & self.families)


class LobbyingIndex:
    """Page slug -> PageLobbying over one shared FilerUniverse. A page with no
    mention lists no filer (an empty, still-checking PageLobbying)."""

    def __init__(
        self,
        mentions_by_page: Mapping[str, list[tuple[str | None, str | None, str | None]]],
        universe: FilerUniverse,
    ):
        self._mentions = mentions_by_page
        self.universe = universe
        self._pages: dict[str, PageLobbying] = {}

    def for_page(self, page: str) -> PageLobbying:
        if page not in self._pages:
            self._pages[page] = PageLobbying.from_mentions(
                self._mentions.get(page, []), self.universe)
        return self._pages[page]


def is_lobbying_claim(text: str, fact: Mapping | None) -> bool:
    """A claim about lobbying: it cites an lda_filing fact, or it says so."""
    return (fact or {}).get("kind") == "lda_filing" or bool(_LOBBYING_WORDS_RE.search(text))


def unlisted_lobbying_filers(
    text: str, fact: Mapping | None, page: PageLobbying | None,
) -> list[str]:
    """Every LDA filer a lobbying claim names that the page's lobbying
    mentions do not list; [] for a claim that is not about lobbying or when
    no index was read."""
    if page is None or not is_lobbying_claim(text, fact):
        return []
    out: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for name in named_lobbying_filers(text, page.universe):
        toks = _filer_tokens(name)
        if toks not in seen and not page.lists(name):
            seen.add(toks)
            out.append(name)
    return out


def claim_contradictions(
    text: str,
    fact: Mapping | None,
    concentration: Mapping | None = None,
    recipients: PageRecipients | None = None,
    lobbying: PageLobbying | None = None,
) -> list[str]:
    """Why `text` contradicts its cited fact, in check order; [] when it does not.

    fact: the cited citation row ({"kind", "units", "recorded_value",
        "amount_thousands", "amount_text", "scenario", "amount_type", ...})
        or None. scenario / amount_type (the column) feed the fiscal-year
        leg; a row without them is not checked for its year. kind
        "lda_filing" makes the claim a lobbying claim.
    concentration: {"family_key", "display_name", "hhi"} of the
        fct_program_concentration row that minted the cited fact
        (concentration_fact_index), or None when the fact is not one.
    recipients: the page's linked-award recipients (RecipientIndex.for_page),
        or None when no mart was read (the recipient leg does not run).
    lobbying: the page's lobbying mentions (LobbyingIndex.for_page), or None
        when no mart was read (the lobbying leg does not run).
    """
    reasons: list[str] = []
    fact = fact or {}
    units = fact.get("units")

    # stated_figure
    current = fact_comparison_value(fact)
    if current is not None:
        kind, actual = current
        figures = stated_dollar_figures(text) if kind == "dollars" else stated_hhi_figures(text)
        if figures and not any(_agrees(v, t, b, actual) for v, t, b in figures):
            reasons.append("stated_figure")

    # fiscal_year (round 3)
    if fiscal_year_contradicted(text, fact):
        reasons.append("fiscal_year")

    # concentration_band
    hhi = (
        _numeric(fact.get("recorded_value")) if units == HHI_UNITS
        else _numeric((concentration or {}).get("hhi"))
    )
    if hhi is not None:
        band = hhi_band_key(hhi)
        for key, negated in stated_band_words(text):
            if (key == band) == negated:
                reasons.append("concentration_band")
                break

    # top_family
    if concentration and concentration.get("family_key") and names_top_family(text):
        if not (_names(text, concentration.get("family_key"))
                or _names(text, concentration.get("display_name"))):
            reasons.append("top_family")

    # recipient_list
    if recipients is not None and unlinked_recipients(text, recipients):
        reasons.append("recipient_list")

    # lobbying_mention (R-DEC-DOSSIERLDA)
    if unlisted_lobbying_filers(text, fact, lobbying):
        reasons.append("lobbying_mention")

    return reasons


def _read_error(what: str, duckdb_path, exc: Exception) -> ClaimDriftIndexError:
    detail = " ".join(str(exc).split())[:240]
    return ClaimDriftIndexError(
        f"{what} could not be read from {duckdb_path} ({type(exc).__name__}:"
        f" {detail}) — the R-DEC-DOSSIERDRIFT legs that need it cannot run,"
        " and an unreadable mart is never an empty one"
    )


def concentration_fact_index(duckdb_path: str | Path | None) -> dict[str, dict]:
    """{fact_id: {"family_key", "display_name", "hhi"}} for every concentration
    fact fct_program_concentration can mint, read-only.

    The derived fids are fact_id_derived("concentration", pe_bli, metric) —
    "hhi"/"program_dollars" for the all-links basis (top_family_all, hhi_all)
    and "hhi_high"/"program_dollars_high" for the high-only basis
    (top_family_high, hhi_high), exactly as export_site mints them. A basis
    with no family is omitted (it records none). The display name comes from
    dim_entities.

    duckdb_path=None -> {} (no mart: the family leg does not run; the figure
    and band legs, which need only the citation row, still do). A supplied
    path that cannot be read — missing file, missing mart or column, a lock
    — RAISES ClaimDriftIndexError (fail closed, round 2).
    """
    if duckdb_path is None:
        return {}
    import duckdb

    from govbudget.export_site import fact_id_derived

    try:
        con = duckdb.connect(str(duckdb_path), read_only=True)
    except Exception as exc:
        raise _read_error("the concentration mart", duckdb_path, exc) from exc
    try:
        try:
            rows = con.execute(
                "select pe_bli, hhi_all, top_family_all, hhi_high, top_family_high"
                " from fct_program_concentration"
            ).fetchall()
        except Exception as exc:
            raise _read_error("fct_program_concentration", duckdb_path, exc) from exc
        try:
            names = dict(con.execute(
                "select family_key, min(display_name)"
                " from dim_entities group by family_key"
            ).fetchall())
        except Exception as exc:
            raise _read_error("dim_entities", duckdb_path, exc) from exc
    finally:
        con.close()
    out: dict[str, dict] = {}
    for pe_bli, hhi_all, fam_all, hhi_high, fam_high in rows:
        for metrics, hhi, fam in (
            (("hhi", "program_dollars"), hhi_all, fam_all),
            (("hhi_high", "program_dollars_high"), hhi_high, fam_high),
        ):
            if not fam:
                continue
            entry = {"family_key": fam, "display_name": names.get(fam), "hhi": hhi}
            for metric in metrics:
                out[fact_id_derived("concentration", pe_bli, metric)] = entry
    return out


#: The page's Related awards rows (export_site._AWARD_LINKS_SQL's
#: fct_budget_to_awards, every published link) with each link's family by the
#: concentration mart's own rule (fct_program_concentration.sql: entity_xwalk
#: on recipient_uei, else the UEI, else the upper-cased name) and the family's
#: dim_entities display name.
_RECIPIENT_LINKS_SQL = """
with fam as (
    select l.pe_bli, l.account, l.organization, l.recipient_name,
           coalesce(x.family_key, l.recipient_uei, upper(l.recipient_name)) as family_key
    from fct_budget_to_awards l
    left join entity_xwalk x on x.recipient_uei = l.recipient_uei
)
select distinct f.pe_bli, f.account, f.organization, f.recipient_name,
       f.family_key, e.display_name
from fam f
left join (
    select family_key, min(display_name) as display_name
    from dim_entities group by family_key
) e on e.family_key = f.family_key
"""


def linked_recipient_index(duckdb_path: str | Path | None) -> RecipientIndex | None:
    """Every program page's linked-award recipients, read-only, keyed by PAGE.

    Links are filed exactly as export_site._awards_for files them: by
    `ident.split_key(pe_bli, account, organization)`, so a shared code's two
    members are two pages with two link sets (ROADMAP #82), and a link under a
    key no member page reads lists on no page. The shared name -> family index
    is entity_xwalk's recipient_name and parent_name plus dim_entities'
    display_name, each normalized (`_name_tokens`).

    duckdb_path=None -> None (the recipient leg does not run). A supplied path
    that cannot be read RAISES ClaimDriftIndexError (fail closed).
    """
    if duckdb_path is None:
        return None
    import duckdb

    from govbudget.export_site import _fetch_program_identity

    try:
        con = duckdb.connect(str(duckdb_path), read_only=True)
    except Exception as exc:
        raise _read_error("the linked-award marts", duckdb_path, exc) from exc
    try:
        try:
            ident = _fetch_program_identity(con)
        except Exception as exc:
            raise _read_error("dim_programs", duckdb_path, exc) from exc
        try:
            link_rows = con.execute(_RECIPIENT_LINKS_SQL).fetchall()
        except Exception as exc:
            raise _read_error(
                "fct_budget_to_awards / entity_xwalk / dim_entities (the linked"
                " awards' recipient families)", duckdb_path, exc) from exc
        try:
            xwalk_rows = con.execute(
                "select recipient_name, parent_name, family_key from entity_xwalk"
                " where family_key is not null"
                " union all"
                " select display_name, null, family_key from dim_entities"
                " where family_key is not null"
            ).fetchall()
        except Exception as exc:
            raise _read_error("entity_xwalk / dim_entities", duckdb_path, exc) from exc
    finally:
        con.close()

    page_by_key: dict[tuple, str] = {}
    for pe_bli in ident.split_pe_blis:
        for account, account_title, organization, _has_detail in ident.accounts(pe_bli):
            page_by_key[ident.split_key(pe_bli, account, organization)] = ident.slug(
                pe_bli, account, account_title, organization)

    links_by_page: dict[str, list[tuple]] = {}
    for pe_bli, account, organization, recipient_name, family_key, display_name in link_rows:
        if ident.is_split(pe_bli):
            page = page_by_key.get(ident.split_key(pe_bli, account, organization))
            if page is None:
                continue  # filed under a key no member page reads (#70)
        else:
            page = pe_bli
        links_by_page.setdefault(page, []).append((recipient_name, family_key, display_name))

    family_by_name: dict[str, set[str]] = {}
    for recipient_name, parent_name, family_key in xwalk_rows:
        for n in (recipient_name, parent_name):
            toks = _name_tokens(n)
            if toks:
                family_by_name.setdefault(" ".join(toks), set()).add(family_key)
    return RecipientIndex(
        links_by_page, {k: frozenset(v) for k, v in family_by_name.items()})


#: Each program-mention row with its filing's registrant: the program page's
#: `mentions` rows (export_site reads client_name / family_key from the same
#: fct_program_lobbying rows) and the registrant audit_lda_filings records for
#: the filing.
_LOBBYING_MENTIONS_SQL = """
select m.pe_bli, m.client_name, m.family_key, f.registrant_name
from fct_program_lobbying m
left join audit_lda_filings f on f.filing_uuid = m.filing_uuid
"""
#: The filer universe: every filing in the lake (audit_lda_filings is EVERY
#: Senate LDA filing, counted or not) with its family when the match is
#: verified — fct_program_lobbying's own gate (match_method set and not
#: 'none'; an unverified guess is only the queried family name) — plus the
#: mart's client / family pairs.
_LOBBYING_UNIVERSE_SQL = """
select client_name, registrant_name,
       case when match_method is not null and match_method <> 'none'
            then family_key_guess end as family_key
from audit_lda_filings
union all
select client_name, null, family_key from fct_program_lobbying
"""


def lobbying_mention_index(duckdb_path: str | Path | None) -> LobbyingIndex | None:
    """Every program page's lobbying mentions, read-only, keyed by PAGE, over
    the universe of every LDA filer name (R-DEC-DOSSIERLDA).

    A mention row is filed on its bare code's page, exactly as the exporter
    publishes the program page's `mentions`: an ordinary program's page is
    its pe_bli, and a shared (split) code's rows are on NO member page —
    R-INT-9 withholds them from every member, since nothing in a filing says
    which member it describes.

    duckdb_path=None -> None (the lobbying leg does not run). A supplied path
    that cannot be read RAISES ClaimDriftIndexError (fail closed).
    """
    if duckdb_path is None:
        return None
    import duckdb

    from govbudget.export_site import _fetch_program_identity

    try:
        con = duckdb.connect(str(duckdb_path), read_only=True)
    except Exception as exc:
        raise _read_error("the lobbying marts", duckdb_path, exc) from exc
    try:
        try:
            ident = _fetch_program_identity(con)
        except Exception as exc:
            raise _read_error("dim_programs", duckdb_path, exc) from exc
        try:
            mention_rows = con.execute(_LOBBYING_MENTIONS_SQL).fetchall()
            universe_rows = con.execute(_LOBBYING_UNIVERSE_SQL).fetchall()
        except Exception as exc:
            raise _read_error(
                "fct_program_lobbying / audit_lda_filings (the pages' lobbying"
                " mentions, their registrants and every LDA filer name)",
                duckdb_path, exc) from exc
    finally:
        con.close()

    mentions_by_page: dict[str, list[tuple]] = {}
    for pe_bli, client_name, family_key, registrant_name in mention_rows:
        if not pe_bli or ident.is_split(pe_bli):
            continue  # R-INT-9: a shared code's rows are on no member page
        mentions_by_page.setdefault(pe_bli, []).append(
            (client_name, family_key, registrant_name))
    return LobbyingIndex(mentions_by_page, FilerUniverse.from_filings(universe_rows))
