"""Deterministic budget-line -> award crosswalk (v1).

Method 1 (account): an award qualifies as a candidate for a budget line when
the line's federal account (e.g. 097-0400) appears in the award's
federal_accounts_funding_this_award list. Method 2 (token overlap): candidate
confidence is raised to 'high' when PE/title tokens overlap the award's
descriptions. Everything lands in budget_line_awards with method + confidence;
nothing is asserted silently. v1 is LLM-free by design (recorded decision).

Award window (#78, 2026-09-05). By default a budget line is matched ONLY
against awards whose FEDERAL fiscal year equals that line's own PB edition
`fiscal_year` -- resolved per line, inside the loop, so a PB2017 line sees
FY2017 awards and a PB2026 line sees FY2026 awards. fy_start/fy_end (always
both, never one) pin a single explicit window for every line instead;
all_years=True removes the window entirely. all_years is the pre-#78 default,
and it is what cross-joined 177 DARPA line-editions against the whole
FY2017-26 lake on 2026-09-04 (+2,214,705 rows, reverted from a parquet
backup), so the CLI plans EVERY run with plan_crosswalk_org() first -- under
whichever window was asked for, --all-years or not -- and refuses to write
above ALL_YEARS_ABORT_ROWS pairs unless --yes.

Determinism (#85, 2026-09-05; re-measured 2026-09-10). Two runs over the same
lake and the same budget_lines write byte-identical mechanical rows. Two
things used to break that. (1) budget_lines can carry several titles under one
(organization, pe_bli, exhibit, fiscal_year, account) key -- three live keys,
HCMC00 and JSE000 on 3010F and SFV000 on 3022F, all org F, all PB2026 -- and
every variant was iterated with the last upsert winning. _load_lines now
returns ONE canonical row per key: the latest document's row (jbook_documents
fiscal_year, then downloaded_at, then id), then the lowest budget_activity,
then the first title; every tiebreak is explicit in CANONICAL_LINE_SQL.
(2) The candidate query aggregated an award's transactions with any_value(),
which DuckDB resolves by scan order: three consecutive identical read-only
runs on 2026-09-10 returned a different transaction_description for 6,226 and
5,957 of the 13,216 awards under 097-0400, a different awarding_sub_agency_name
for 392 and 370, and a different recipient_name for 51 and 55 -- the +/-346
medium / +119 high flip ROADMAP #85 recorded. _fetch_candidates now grades an
award from ALL of its transactions in the window under one rule, "any
transaction of the award carries the attribute":
  * sub-agency: medium when ANY transaction's awarding_sub_agency_name
    contains an alias of the organization (controller ruling 2026-09-05;
    the rationale says "on k of n transaction(s)");
  * token overlap: computed once per canonical line against the UNION of
    the award's distinct transaction descriptions and its base description;
  * recipient_name/uei: the latest transaction's (action_date, then
    contract_transaction_unique_key);
  * matched_obligation: an exact decimal sum (order-independent; the lake's
    097-0400 obligations carry at most two decimals, 0 of 196,043 more).
Tier names, the min_overlap threshold and the upsert guard are unchanged;
only membership became deterministic.

Counting and binding (#86, 2026-09-11). crosswalk_org returns
CrosswalkResult(written, skipped) rather than one number: a candidate row the
upsert guard left alone (the key already carries an evidence-graded link) was
being counted as a link the run wrote. fed_account and the FY bounds are
DuckDB `?` parameters, and an award whose action_date is NULL or not a date is
excluded from an FY window explicitly (see FED_FY_EXPR) instead of by NULL
arithmetic. The upsert guard itself is byte-identical.

Edition selector and window validation (2026-09-24, merged 2026-09-25 from
the award-refresh branch). `fiscal_year` restricts a run to ONE PB edition's
budget lines (the CLI's shared jbooks `--fiscal-year`), so a refresh can plan
and write a single edition instead of every edition the org has loaded. It
narrows WHICH lines run and never widens a line's award window. Every year
argument must be an integer in 1900-2200 and fy_start may not follow fy_end:
a reversed window used to match nothing and write nothing, silently, instead
of stopping.

Ambiguous identities (#170, 2026-09-25). budget_line_awards' unique key
(pe_bli, exhibit, fiscal_year, award_piid) names neither the account nor the
organization, so when two accounts -- or two organizations -- file the same
(pe_bli, exhibit, fiscal_year), the later line's upsert silently replaced the
earlier line's grade on every award both matched: the last account won.
find_ambiguous_identities() names every such identity, and plan_crosswalk_org /
crosswalk_org raise AmbiguousIdentityError on one before any lake scan or
write; the CLI checks every organization it will run before planning the first.
The live branch (81929a6b) aborted the same way; the 2026-09-25 merge dropped it.

Scoped detail tokens (#171, 2026-09-25). A line's tokens are its own title's
plus the project titles of detail rows from ITS OWN book: a document whose
organization (orgs.workbook_org) is the line's organization, whose edition is
the line's fiscal_year, and whose detail row names the line's account or no
account. The merged code added every non-superseded project title filed under
the code to every line of it, so a line reached account+tokens/high on titles
from another organization's book, another edition or another account.
regrade_report() is the dry run's measurement of what the scoping moves.

Update-only re-grade (R-DEC-171, 2026-09-26). The only write path used to be
crosswalk_org's upsert, which also INSERTS every candidate pair not yet stored
(226,020 for DARPA FY2026 under --all-years). apply_regrade() rewrites only
the stored mechanical rows regrade_report() lists in `updates` -- rows the
unscoped rule still reproduces, that the scoping alone re-grades, and that
were stored under the run's own window -- each guarded on still reading as
measured, all in one transaction, never an INSERT. The CLI's --regrade-only
writes only with --expect-updates equal to the count its dry run printed
(82 for DARPA FY2026 --all-years on 2026-09-25: 50 unadjudicated
account+tokens/high -> account/low, 32 adjudicated -> account+subagency/medium).
"""
import csv
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import NamedTuple

import duckdb
import psycopg

from govbudget import config
from govbudget.jbooks.orgs import workbook_org

# Sub-agency alias seed: data-seeds/org_subagency_aliases.csv, columns
# organization,alias. Replaces a hardcoded DARPA-only clause (#75) — every
# organization's medium-tier sub-agency match now comes from this file.
# Anchored to config.ROOT like every other seed path in cli.py, so this module
# has one path anchor and it is not this file's own depth in the tree (#86).
_ALIASES_CSV = config.ROOT / "data-seeds" / "org_subagency_aliases.csv"


class CrosswalkResult(NamedTuple):
    """What one crosswalk_org run did to budget_line_awards (#86).

    written  rows inserted, or updated because the stored row was mechanical
    skipped  candidate rows the upsert guard left alone — the key already
             holds an evidence-graded row (fpds-ap, announcement+lexicon,
             subaward+lexicon) that a mechanical re-run must never rewrite
    """

    written: int
    skipped: int


def _load_subagency_aliases() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    with open(_ALIASES_CSV, newline="") as f:
        for row in csv.DictReader(f):
            organization = (row.get("organization") or "").strip()
            alias = (row.get("alias") or "").strip()
            # 2026-09-04 (#75 fix round 1, finding 5): an empty alias makes
            # `"" in sub_agency` true for EVERY award (empty string is a
            # substring of everything in Python), silently promoting the
            # whole organization's low-tier matches to medium. An empty
            # organization is equally unusable (it can never be looked up
            # by crosswalk_org's own `organization` argument). Fail loudly
            # at load time rather than let either slip through as a no-op
            # alias that quietly inflates confidence.
            if not organization:
                raise ValueError(
                    f"{_ALIASES_CSV}: row with empty organization"
                    f" (alias={row.get('alias')!r})"
                )
            if not alias:
                raise ValueError(
                    f"{_ALIASES_CSV}: empty alias for organization"
                    f" {organization!r} — an empty alias would match every"
                    " award's sub-agency and silently promote the whole"
                    " organization to medium confidence"
                )
            out.setdefault(organization, []).append(alias.lower())
    return out


# Trailing letter on budget accounts is the service designator and maps to
# the treasury agency prefix USAspending uses (verified in the award lake:
# 0400D->097-0400, 1319N->017-1319, 2040A->021-2040, 3600F->057-3600).
AGENCY_BY_LETTER = {"D": "097", "N": "017", "A": "021", "F": "057"}

STOPWORDS = {
    "the", "and", "for", "of", "to", "in", "a", "support", "services", "service",
    "program", "research", "development", "defense", "system", "systems",
    "technology", "technologies", "advanced", "based", "high", "performance",
    "management", "information", "operational", "tactical", "small",
}


def _tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    return {
        t for t in re.split(r"[^a-z0-9]+", text.lower())
        if len(t) > 3 and t not in STOPWORDS
    }


# 2026-09-05 (#78): every crosswalk run is PLANNED first (count of (line,
# award) candidate pairs, nothing written) and refused above this many pairs
# unless the operator passes --yes -- the default per-line window included,
# not just --all-years (controller ruling 2026-09-11). Calibration, read-only
# 2026-09-05: the whole budget_line_awards table holds 164,345 rows, and the
# unbounded 2026-09-04 DARPA run this guard exists to stop planned 177
# line-editions x 13,216 distinct 097-0400 PIIDs = 2,339,232 pairs. DARPA
# plans 761,029 pairs even under the default window, so a full DARPA re-run
# needs --yes either way; that is deliberate -- the operator reads the plan
# before a six-figure write.
ALL_YEARS_ABORT_ROWS = 500_000

# Federal fiscal year of a USAspending action_date string (Oct 1 - Sep 30):
# an Oct-Dec date belongs to the NEXT FY, not the calendar year the string
# starts with (#75a). Built on try_cast(... as date) so a value that is not a
# date has no fiscal year AT ALL (#86): the earlier substr arithmetic read a
# year-only '2024' as FY2024 and a month-13 '2024-13-01' as FY2025 (13 >= 10
# rolled the year over), and excluded NULL/'' only by three-valued-logic
# accident. A NULL fiscal year matches no BETWEEN, so such a row is excluded
# under any window and kept under none -- the behaviour the explicit window
# has had since #75a, now stated rather than inherited. The lake's action_date
# is VARCHAR in every partition (10-char ISO, 0 NULL, 0 unparseable across
# 39,765,730 rows on 2026-09-10), so this moves no live link. Callers that
# need the expression use this constant rather than restating it.
FED_FY_EXPR = (
    "(year(try_cast(action_date as date))"
    " + case when month(try_cast(action_date as date)) >= 10 then 1 else 0 end)"
)


def _validate_window(
    fy_start: int | None, fy_end: int | None, all_years: bool,
    fiscal_year: int | None = None,
) -> None:
    """Loud failure for the window shapes that used to be silently
    reinterpreted: one bound alone (pre-#78 it was dropped, i.e. the run went
    unbounded), all_years stacked on an explicit window (contradictory), a
    reversed window (it matched nothing and wrote nothing, silently), and a
    year that is not an integer in 1900-2200 (`fiscal_year` — the edition
    selector — included). Runs before any database is opened."""
    for name, year in (("fy_start", fy_start), ("fy_end", fy_end),
                       ("fiscal_year", fiscal_year)):
        if year is not None and (
            isinstance(year, bool) or not isinstance(year, int)
            or not 1900 <= year <= 2200
        ):
            raise ValueError(
                f"{name} must be an integer fiscal year between 1900 and 2200"
                f" (got {year!r})"
            )
    if (fy_start is None) != (fy_end is None):
        raise ValueError(
            "fy_start and fy_end must be given together"
            f" (got fy_start={fy_start!r}, fy_end={fy_end!r})"
        )
    if fy_start is not None and fy_start > fy_end:
        raise ValueError(
            f"fy_start {fy_start} is after fy_end {fy_end}; the window would"
            " match no award"
        )
    if all_years and fy_start is not None:
        raise ValueError(
            "all_years cannot be combined with an explicit fy_start/fy_end window"
        )


def _line_window(
    edition_fy: int, fy_start: int | None, fy_end: int | None, all_years: bool,
) -> tuple[int | None, int | None]:
    """Inclusive federal-FY bounds for ONE budget line.

    Precedence: an explicit fy_start/fy_end window > all_years (no bounds,
    (None, None)) > the line's own PB edition fiscal_year (the #78 default).
    """
    if fy_start is not None:
        return fy_start, fy_end
    if all_years:
        return None, None
    return int(edition_fy), int(edition_fy)


def _window_label(lo: int | None, hi: int | None) -> str:
    """Audit label for one line's window. Nothing parses it, but the
    no-bounds wording is byte-identical to the rows already in
    budget_line_awards so that population stays self-describing."""
    if lo is None:
        return "all loaded award years"
    if lo == hi:
        return f"award FY{lo}"
    return f"award FY{lo}-{hi}"


def run_window_label(
    fy_start: int | None, fy_end: int | None, all_years: bool,
) -> str:
    """Run-level label for the CLI's summary lines. Distinct from
    _window_label because the #78 default has no single FY for a whole run --
    every line gets its own."""
    if fy_start is not None:
        return _window_label(fy_start, fy_end)
    if all_years:
        return "all loaded award years"
    return "each line's own edition FY"


def _fed_account(account: str | None, treasury_agency: str) -> str:
    """Map service-letter suffix to treasury agency prefix.
    e.g. "1319N" -> agency "017", numeric "1319" -> fed_account "017-1319".
    Letterless accounts fall back to the caller-supplied treasury_agency."""
    if account and account[-1:].isalpha():
        numeric, letter = account[:-1], account[-1].upper()
    else:
        numeric, letter = account, None
    agency = AGENCY_BY_LETTER.get(letter, treasury_agency)
    return f"{agency}-{numeric}"


def _candidate_where(
    fed_account: str, fy_start: int | None, fy_end: int | None,
) -> tuple[str, list]:
    """The candidate predicate AND its bound parameters, shared by the planner
    and the write path so a plan can never count rows the run would not upsert.
    fy_start/fy_end here are ONE LINE's resolved bounds (see _line_window), not
    the CLI flags.

    Returns (sql, params). fed_account and the FY bounds are DuckDB `?`
    parameters (#86); they used to be f-string-interpolated, so an account code
    carrying a quote was a ParserException rather than a value that matches
    nothing. award_glob stays interpolated at the two call sites: it is an
    operator-supplied path, not data. DuckDB binds `?` in TEXTUAL order, so a
    caller whose SELECT list carries its own placeholder (the obligation `case`
    in _fetch_candidates) passes that parameter FIRST.

    LIKE metacharacters in fed_account are NOT escaped: the account domain is
    digits plus one optional service letter (see AGENCY_BY_LETTER), so no live
    code carries `_` or `%`. Binding fixes the quoting hole, not the wildcard
    one; escaping is a separate change if that domain ever widens.
    """
    where = (
        "federal_accounts_funding_this_award like ?"
        " and award_id_piid is not null and award_id_piid <> ''"
    )
    params: list = [f"%{fed_account}%"]
    if fy_start is not None:
        # An action_date that is NULL or not a date has no fiscal year, so a
        # window excludes it EXPLICITLY (#86) instead of relying on NULL
        # arithmetic -- and the year-only / month-13 strings the old substr
        # expression folded into a fiscal year go with it. See FED_FY_EXPR.
        where += (
            " and try_cast(action_date as date) is not null"
            f" and {FED_FY_EXPR} between ? and ?"
        )
        params += [fy_start, fy_end]
    return where, params


# One canonical budget line per (pe_bli, exhibit, fiscal_year, account) key
# within the organization (#85). DISTINCT ON keeps the FIRST row under the
# ORDER BY, so every tiebreak is written out: the latest document (edition FY,
# then when it was downloaded, then id), then the lowest budget activity, then
# the first title. Postgres orders DESC with NULLS FIRST by default, hence the
# explicit NULLS LAST on the nullable legs. budget_lines.source_document_id is
# NOT NULL (migration 005), so the join drops nothing. When two rows tie on
# every leg they are identical in all five selected columns, so which one
# DISTINCT ON keeps cannot change the result.
#
# The second and third parameters are the optional edition selector
# (`fiscal_year`): both NULL keeps every edition.
CANONICAL_LINE_SQL = """
select distinct on (b.pe_bli, b.exhibit, b.fiscal_year, b.account)
       b.pe_bli, b.exhibit, b.fiscal_year, b.account, b.title
from budget_lines b
join jbook_documents d on d.id = b.source_document_id
where b.organization = %s
  and (%s::int is null or b.fiscal_year = %s)
order by b.pe_bli, b.exhibit, b.fiscal_year, b.account,
         d.fiscal_year desc, d.downloaded_at desc nulls last, d.id desc,
         b.budget_activity asc nulls last, b.title asc nulls last
"""


def _load_lines(
    dsn: str, organization: str, fiscal_year: int | None = None,
) -> list[tuple]:
    """Exactly one (pe_bli, exhibit, fiscal_year, account, title) row per key
    for the org -- the canonical title (CANONICAL_LINE_SQL) -- sorted in Python
    by (account, fiscal_year, pe_bli, exhibit) so lines sharing a
    (fed_account, window) sit together for the single-entry memo and the
    iteration order is fixed. plan_crosswalk_org iterates the same list, so a
    multi-title key is planned once, not once per variant. Live counts
    2026-09-10: DARPA 177 -> 177 (no variants), org F 1,739 -> 1,736.
    `fiscal_year` keeps only that PB edition's lines (None: every edition)."""
    with psycopg.connect(dsn) as pg:
        rows = pg.execute(
            CANONICAL_LINE_SQL, (organization, fiscal_year, fiscal_year),
        ).fetchall()
    return sorted(rows, key=lambda r: (r[3] or "", r[2], r[0] or "", r[1] or ""))


# #170: every organization that files one of the run's identities, with the
# accounts it files it under. `run` is the (pe_bli, exhibit, fiscal_year)
# identities the given organizations would plan (the same edition selector as
# CANONICAL_LINE_SQL); the outer query lists every filer of those identities
# -- the run's own organizations, and any other organization the CLI could
# run (non-null, non-empty; the '' lines are never run by default). One row
# per distinct (identity, organization, account): budget_lines.account is NOT
# NULL (migration 001) and every row has a source document (migration 005), so
# these are exactly the canonical line keys _load_lines returns.
AMBIGUITY_SQL = """
with run as (
  select distinct pe_bli, exhibit, fiscal_year from budget_lines
  where organization = any(%(orgs)s)
    and (%(fy)s::int is null or fiscal_year = %(fy)s)
)
select distinct b.pe_bli, b.exhibit, b.fiscal_year, b.organization, b.account
from budget_lines b
join run r on r.pe_bli = b.pe_bli and r.exhibit = b.exhibit
          and r.fiscal_year = b.fiscal_year
where b.organization = any(%(orgs)s)
   or (b.organization is not null and b.organization <> '')
order by 1, 2, 3, 4, 5
"""


#: How an empty organization code prints in a refusal (13 live identities).
EMPTY_ORG = "''"


@dataclass(frozen=True)
class AmbiguousIdentity:
    """One (pe_bli, exhibit, fiscal_year) that more than one (organization,
    account) files -- budget_line_awards' key cannot tell their links apart."""

    pe_bli: str
    exhibit: str
    fiscal_year: int
    filers: tuple[tuple[str, str], ...]   # sorted (organization, account)

    @property
    def kind(self) -> str:
        """'organizations' when two or more organizations file it, else
        'accounts' (one organization, two or more accounts)."""
        return "organizations" if len({o for o, _ in self.filers}) > 1 else "accounts"

    def describe(self) -> str:
        who = "; ".join(f"{org or EMPTY_ORG} {account}" for org, account in self.filers)
        return f"({self.pe_bli}, {self.exhibit}, FY{self.fiscal_year}): {who}"


class AmbiguousIdentityError(ValueError):
    """Raised before any lake scan or write when a run's identities are
    ambiguous (#170). `identities` lists every one, not just the first."""

    def __init__(self, identities: list[AmbiguousIdentity]):
        self.identities = identities
        super().__init__(
            f"{len(identities)} (pe_bli, exhibit, fiscal_year) identit"
            f"{'y is' if len(identities) == 1 else 'ies are'} filed under more"
            " than one account or organization; budget_line_awards' key names"
            " neither, so the last line written would silently replace the"
            " others' links. Crosswalk refused: "
            + " | ".join(a.describe() for a in identities)
        )


def find_ambiguous_identities(
    dsn: str, organizations, fiscal_year: int | None = None,
) -> list[AmbiguousIdentity]:
    """Every identity the given organizations would plan that two or more
    accounts of one organization, or two or more organizations, file (#170).
    Read-only. `fiscal_year` is the edition selector, as in _load_lines."""
    orgs = sorted(set(organizations))
    with psycopg.connect(dsn) as pg:
        pg.read_only = True
        rows = pg.execute(AMBIGUITY_SQL, {"orgs": orgs, "fy": fiscal_year}).fetchall()
    filers: dict[tuple[str, str, int], set[tuple[str, str]]] = {}
    for pe_bli, exhibit, fy, org, account in rows:
        filers.setdefault((pe_bli, exhibit, int(fy)), set()).add((org, account))
    return [
        AmbiguousIdentity(pe, ex, fy, tuple(sorted(who)))
        for (pe, ex, fy), who in sorted(filers.items())
        if len(who) > 1
    ]


def _refuse_ambiguous(dsn: str, organization: str, fiscal_year: int | None) -> None:
    found = find_ambiguous_identities(dsn, [organization], fiscal_year)
    if found:
        raise AmbiguousIdentityError(found)


# #171: the project titles a line's tokens may draw on. Organization and
# edition come from the detail row's DOCUMENT (jbook_documents.org, mapped to
# the workbook code by orgs.workbook_org -- PB2017-PB2019 filenames spell the
# agency out -- and jbook_documents.fiscal_year); account is the detail row's
# own (NULL for R-1/RDT&E rows, which carry no appropriation). The filter to
# the run's codes only bounds the read.
DETAIL_TITLES_SQL = """
select d.pe_bli, j.org, j.fiscal_year, d.account, d.project_title
from budget_line_details d
join jbook_documents j on j.id = d.document_id
where not d.superseded and d.pe_bli = any(%s)
order by d.pe_bli, j.org, j.fiscal_year, d.account nulls first, d.project_title
"""

#: The three legs, in the order the dry run applies them cumulatively to name
#: the first one that drops a line's overlap below min_overlap.
SCOPE_LEGS = ("organization", "edition", "account")


@dataclass(frozen=True)
class DetailTitle:
    workbook_org: str
    edition: int
    account: str | None
    tokens: frozenset[str]


def _load_detail_titles(dsn: str, pe_blis) -> dict[str, list[DetailTitle]]:
    """pe_bli -> the tokenised project titles of its non-superseded detail
    rows, each with the book (organization, edition) and account it is from."""
    codes = sorted({p for p in pe_blis if p})
    if not codes:
        return {}
    with psycopg.connect(dsn) as pg:
        pg.read_only = True
        rows = pg.execute(DETAIL_TITLES_SQL, (codes,)).fetchall()
    out: dict[str, list[DetailTitle]] = {}
    for pe_bli, doc_org, edition, account, title in rows:
        tokens = _tokens(title)
        if tokens:
            out.setdefault(pe_bli, []).append(DetailTitle(
                workbook_org(doc_org or ""), int(edition), account,
                frozenset(tokens)))
    return out


def _line_tokens(
    title: str | None, details: list[DetailTitle], organization: str,
    fiscal_year: int, account: str | None, legs=SCOPE_LEGS,
) -> set[str]:
    """A line's tokens: its own title's, plus the project titles `legs`
    admits. The default (every leg) is the rule; the dry run passes fewer
    legs to find which one dropped a line."""
    tokens = _tokens(title)
    for d in details:
        if "organization" in legs and d.workbook_org != organization:
            continue
        if "edition" in legs and d.edition != int(fiscal_year):
            continue
        if "account" in legs and d.account is not None and d.account != account:
            continue
        tokens |= d.tokens
    return tokens


@dataclass(frozen=True)
class LinePlan:
    """What crosswalk_org would do for ONE budget line: the federal account
    and award-FY window it resolves to, and how many (line, award) pairs that
    window yields. Counting only -- plan_crosswalk_org writes nothing."""

    pe_bli: str
    exhibit: str
    fiscal_year: int
    account: str | None
    fed_account: str
    fy_lo: int | None
    fy_hi: int | None
    candidates: int


def plan_crosswalk_org(
    dsn: str, *, organization: str, treasury_agency: str, award_glob: str,
    fy_start: int | None = None,
    fy_end: int | None = None,
    all_years: bool = False,
    fiscal_year: int | None = None,
) -> list[LinePlan]:
    """Count the (line, award) pairs crosswalk_org WOULD upsert -- one
    LinePlan per budget line -- without writing anything (#78: --dry-run, and
    the projected-row abort).

    Same lines, same account mapping, same per-line window, same predicate:
    the planner and the write path share _load_lines / _fed_account /
    _line_window / _candidate_where, and the write path's `group by
    award_id_piid` returns exactly one row per distinct PIID, so
    `count(distinct award_id_piid)` here cannot drift from it.
    `fiscal_year` plans only that PB edition's lines, as crosswalk_org writes.
    """
    _validate_window(fy_start, fy_end, all_years, fiscal_year)
    _refuse_ambiguous(dsn, organization, fiscal_year)
    lines = _load_lines(dsn, organization, fiscal_year)
    con = duckdb.connect()
    out: list[LinePlan] = []
    # Same single-entry memo as crosswalk_org, for the same reason.
    memo_key: tuple[str, int | None, int | None] | None = None
    memo_n = 0
    try:
        for pe_bli, exhibit, fy, account, _title in lines:
            fed_account = _fed_account(account, treasury_agency)
            lo, hi = _line_window(fy, fy_start, fy_end, all_years)
            key = (fed_account, lo, hi)
            if key != memo_key:
                where, where_params = _candidate_where(fed_account, lo, hi)
                memo_n = con.execute(
                    "select count(distinct award_id_piid)"
                    f" from read_parquet('{award_glob}', union_by_name=true)"
                    f" where {where}",
                    where_params,
                ).fetchone()[0]
                memo_key = key
            out.append(LinePlan(
                pe_bli, exhibit, int(fy), account, fed_account, lo, hi, int(memo_n),
            ))
    finally:
        con.close()
    return out


# Ordering key that picks ONE transaction of an award deterministically: the
# latest action_date, ties broken by the transaction's own unique key. Both
# columns are VARCHAR in the lake ('YYYY-MM-DD' sorts as text); coalesce keeps
# a NULL from making the whole key NULL. arg_max ignores rows whose ARGUMENT
# is NULL, i.e. it falls back to the latest transaction that has a value.
LATEST_TX_KEY = (
    "coalesce(action_date, '') || '|' || coalesce(contract_transaction_unique_key, '')"
)


@dataclass(frozen=True)
class AwardCandidate:
    """One award under a (fed_account, window), summarised over ALL of its
    transactions in that window -- nothing here depends on scan order."""

    piid: str
    recipient_name: str | None          # latest transaction's
    recipient_uei: str | None           # latest transaction's
    matched_obligation: Decimal | None  # exact sum for this account only
    descriptions: tuple[str, ...]       # distinct, sorted, non-null: transaction + base
    sub_agencies: tuple[str | None, ...]  # one entry per transaction (DuckDB list keeps NULLs)


def _fetch_candidates(
    con: duckdb.DuckDBPyConnection, award_glob: str, fed_account: str,
    where: str, where_params: list,
) -> list[AwardCandidate]:
    """The only lake query in the write path. Every aggregate is
    order-independent (list / arg_max / decimal sum) -- no any_value() anywhere,
    which is what #85 was. Rows come back ordered by PIID so upsert order, and
    therefore bigserial ids on a fresh table, are fixed too. `where` /
    `where_params` are _candidate_where(fed_account, lo, hi) -- the same
    predicate plan_crosswalk_org counts, so a plan still cannot drift from the
    run. fed_account is BOUND, not interpolated (#86); DuckDB binds `?` in
    textual order, so the obligation `case`'s parameter goes first and the
    where clause's follow."""
    rows = con.execute(
        f"""
        select award_id_piid,
               arg_max(recipient_name, {LATEST_TX_KEY}),
               arg_max(recipient_uei, {LATEST_TX_KEY}),
               sum(case when federal_accounts_funding_this_award = ?
                        then try_cast(federal_action_obligation as decimal(20,2)) end),
               list(distinct transaction_description order by transaction_description),
               list(distinct prime_award_base_transaction_description
                    order by prime_award_base_transaction_description),
               list(awarding_sub_agency_name order by awarding_sub_agency_name)
        from read_parquet('{award_glob}', union_by_name=true)
        where {where}
        group by award_id_piid
        order by award_id_piid
        """,
        [fed_account, *where_params],
    ).fetchall()
    out: list[AwardCandidate] = []
    for piid, rname, ruei, obligation, tx_descs, base_descs, subs in rows:
        descriptions = tuple(sorted(
            {d for d in (tx_descs or []) + (base_descs or []) if d}
        ))
        out.append(AwardCandidate(
            piid=piid, recipient_name=rname, recipient_uei=ruei,
            matched_obligation=obligation, descriptions=descriptions,
            sub_agencies=tuple(subs or []),
        ))
    return out


def _award_tokens(cand: AwardCandidate) -> set[str]:
    return set().union(*(_tokens(d) for d in cand.descriptions))


def _grade(
    pe_tokens: set[str], cand: AwardCandidate, org_aliases: list[str],
    min_overlap: int, fed_account: str,
    award_tokens: set[str] | None = None,
) -> tuple[str, str, int, str]:
    """The tier rule, pure. Returns (confidence, method, score, rationale
    core); the caller appends the window label. Precedence is unchanged:
    token overlap -> high, else any-transaction sub-agency -> medium, else
    account only -> low.

    Sub-agency semantics (controller ruling 2026-09-05, the pre-existing rule
    made explicit): an award carries the organization's sub-agency when ANY of
    its transactions in the window was awarded under it -- not the dominant
    one, not the latest one, not whichever one was scanned first.

    `award_tokens`, when given, is _award_tokens(cand) computed once by a
    caller that grades one award under several token sets (regrade_report).
    """
    if award_tokens is None:
        award_tokens = _award_tokens(cand)
    hits = pe_tokens & award_tokens
    overlap = len(hits)
    sub_hits = [
        s for s in cand.sub_agencies
        if s and any(a in s.lower() for a in org_aliases)
    ]
    if overlap >= min_overlap:
        return (
            "high", "account+tokens", overlap,
            f"account {fed_account}; token overlap {overlap}"
            f" ({', '.join(sorted(hits))}) across {len(cand.descriptions)}"
            " distinct description(s)",
        )
    if sub_hits:
        names = " / ".join(sorted(set(sub_hits)))
        return (
            "medium", "account+subagency", overlap,
            f"account {fed_account}; sub-agency {names} on {len(sub_hits)} of"
            f" {len(cand.sub_agencies)} transaction(s)",
        )
    return ("low", "account", overlap, f"account {fed_account} only")


def crosswalk_org(
    dsn: str, *, organization: str, treasury_agency: str, award_glob: str,
    min_overlap: int = 2,
    fy_start: int | None = None,
    fy_end: int | None = None,
    all_years: bool = False,
    fiscal_year: int | None = None,
) -> CrosswalkResult:
    """Crosswalk all of one organization's budget lines against the award lake.

    Window: fy_start/fy_end (both) pin an explicit federal-FY window on
    action_date; all_years=True matches every loaded award year; otherwise
    each line matches only awards in its own edition fiscal_year (#78).
    `fiscal_year` (the edition selector) runs only that PB edition's lines;
    it never widens a line's award window.

    Deterministic (#85): one canonical title per key (_load_lines) and every
    award graded from all of its transactions in the window
    (_fetch_candidates + _grade). Two runs over the same inputs write the
    same rows.

    Returns CrosswalkResult(written, skipped): the number of (pe_bli, award)
    links this run inserted or updated, and the number the upsert guard left
    alone because the key already carries an evidence-graded row (#86 — the
    old single count included those skips and called them links). The two
    together are the number of upsert statements issued, i.e. what
    plan_crosswalk_org projects.
    """
    _validate_window(fy_start, fy_end, all_years, fiscal_year)
    # #170: refused before any lake scan or write.
    _refuse_ambiguous(dsn, organization, fiscal_year)
    lines = _load_lines(dsn, organization, fiscal_year)
    # #171: project titles, each tagged with the book and account it is from.
    details = _load_detail_titles(dsn, {line[0] for line in lines})

    aliases = _load_subagency_aliases()
    org_aliases = aliases.get(organization, [organization.lower()])

    con = duckdb.connect()
    written = 0
    skipped = 0
    # Single-entry memo: lines are sorted by (account, fiscal_year), so every
    # line sharing the previous line's (fed_account, window) reuses its fetch.
    # DARPA: 10 lake scans instead of 177. One result set in memory at a time.
    memo_key: tuple[str, int | None, int | None] | None = None
    memo_rows: list[AwardCandidate] = []
    try:
        for pe_bli, exhibit, fy, account, line_title in lines:
            fed_account = _fed_account(account, treasury_agency)
            lo, hi = _line_window(fy, fy_start, fy_end, all_years)
            key = (fed_account, lo, hi)
            if key != memo_key:
                where, where_params = _candidate_where(fed_account, lo, hi)
                memo_rows = _fetch_candidates(
                    con, award_glob, fed_account, where, where_params,
                )
                memo_key = key
            # Computed ONCE per canonical line (#85): one title per key, and
            # only the project titles of the line's own book and account (#171).
            pe_tokens = _line_tokens(
                line_title, details.get(pe_bli, []), organization, fy, account)
            window_note = "; " + _window_label(lo, hi)

            with psycopg.connect(dsn) as pg:
                for cand in memo_rows:
                    confidence, method, score, why = _grade(
                        pe_tokens, cand, org_aliases, min_overlap, fed_account,
                    )
                    rationale = f"{why}{window_note}"
                    cur = pg.execute(
                        """
                        insert into budget_line_awards
                          (pe_bli, exhibit, fiscal_year, organization, award_piid,
                           recipient_name, recipient_uei, matched_obligation,
                           method, confidence, score, rationale)
                        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        on conflict (pe_bli, exhibit, fiscal_year, award_piid)
                        do update set confidence=excluded.confidence,
                                      method=excluded.method,
                                      score=excluded.score,
                                      rationale=excluded.rationale,
                                      matched_obligation=excluded.matched_obligation
                        where budget_line_awards.method in
                              ('account', 'account+subagency', 'account+tokens')
                        """,
                        (pe_bli, exhibit, fy, organization, cand.piid,
                         cand.recipient_name, cand.recipient_uei,
                         cand.matched_obligation, method, confidence, score,
                         rationale),
                    )
                    # Postgres' INSERT tag counts rows inserted OR updated; a
                    # conflict whose `do update ... where` rejected the row (an
                    # evidence-graded stored row) counts 0. That is the guard
                    # skip the old `upserts += 1` mis-counted as a link (#86).
                    if cur.rowcount == 1:
                        written += 1
                    else:
                        skipped += 1
    finally:
        con.close()
    return CrosswalkResult(written=written, skipped=skipped)


#: The methods the mechanical crosswalk writes -- the ones its upsert guard
#: lets it rewrite (the literal list in crosswalk_org's `where` clause).
MECHANICAL_METHODS = ("account", "account+subagency", "account+tokens")


@dataclass(frozen=True)
class RegradeReport:
    """What the scoped detail tokens (#171) change on the rows the mechanical
    crosswalk already stored for one organization's lines. Nothing written.

    stored_mechanical  stored mechanical rows on the run's line keys
    reproduced         of those, the ones the UNSCOPED rule (the merged
                       code's) still grades exactly as stored -- only these
                       are compared, so a change below is the scoping's alone
    drifted            stored rows the unscoped rule already grades
                       differently (the lake moved since they were written)
    not_candidate      stored rows whose award is not a candidate today
    new_pairs          candidate pairs a real run would insert (not stored)
    transitions        (stored method, stored confidence, adjudication,
                       scoped method, scoped confidence) -> rows, for every
                       reproduced row the scoped rule grades differently;
                       adjudication is 'unadjudicated' or 'adjudicated <its
                       adjudicated_confidence>' (award_pe_adjudications)
    lost_leg           (adjudication, leg) -> rows, for every account+tokens
                       row that falls below min_overlap: the first leg of
                       SCOPE_LEGS, applied cumulatively, that drops it
    updates            the transitions as RegradeUpdate rows apply_regrade
                       may write (R-DEC-171) -- only rows whose stored
                       rationale records THIS run's window, since a row
                       stored under another window was graded against
                       another candidate set
    window_mismatch    transition rows left out of `updates` for that reason
    mismatch_windows   the window each of those rows' stored rationale
                       records -> rows ('unrecorded' when none parses), so
                       the operator is told which window re-grades them
    """

    organization: str
    stored_mechanical: int
    reproduced: int
    drifted: int
    not_candidate: int
    new_pairs: int
    transitions: dict
    lost_leg: dict
    updates: tuple = ()
    window_mismatch: int = 0
    mismatch_windows: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RegradeUpdate:
    """One stored mechanical row the scoped detail tokens re-grade (#171).
    `was_*` is the row as measured; apply_regrade writes only while the row
    still reads exactly that."""

    key: tuple                  # (pe_bli, exhibit, fiscal_year, award_piid)
    was_method: str
    was_confidence: str
    was_rationale: str
    bucket: str                 # 'unadjudicated' | 'adjudicated <confidence>'
    method: str
    confidence: str
    score: int
    rationale: str              # the grade's rationale + the window label


#: The labels _window_label writes, as they end a stored rationale segment.
_STORED_WINDOW = re.compile(
    r"; (all loaded award years|award FY\d{4}(?:-\d{4})?)(?=;|$)")


def _stored_window(rationale: str | None) -> str:
    """The window a stored rationale records (its last window label), or
    'unrecorded' when none parses."""
    found = _STORED_WINDOW.findall(rationale or "")
    return found[-1] if found else "unrecorded"


def _stored_under(rationale: str | None, window_label: str) -> bool:
    """True when a stored rationale records `window_label` as its window --
    crosswalk_org appends '; <label>' to every rationale it writes."""
    return bool(rationale) and re.search(
        rf"; {re.escape(window_label)}(;|$)", rationale) is not None


def regrade_report(
    dsn: str, *, organization: str, treasury_agency: str, award_glob: str,
    min_overlap: int = 2,
    fy_start: int | None = None,
    fy_end: int | None = None,
    all_years: bool = False,
    fiscal_year: int | None = None,
) -> RegradeReport:
    """Grade every stored mechanical row of the organization's lines twice
    -- under the unscoped detail tokens the merged code used and under the
    scoped rule crosswalk_org now applies -- and count what moves (#171).
    Read-only: Postgres through read-only connections, the award lake
    through the same candidate query crosswalk_org runs."""
    _validate_window(fy_start, fy_end, all_years, fiscal_year)
    _refuse_ambiguous(dsn, organization, fiscal_year)
    lines = _load_lines(dsn, organization, fiscal_year)
    details = _load_detail_titles(dsn, {line[0] for line in lines})
    line_keys = {(pe, ex, int(fy)) for pe, ex, fy, _a, _t in lines}
    codes = sorted({k[0] for k in line_keys})
    stored: dict[tuple, tuple[str, str]] = {}
    adjudicated: dict[tuple[str, str], str] = {}
    if codes:
        with psycopg.connect(dsn) as pg:
            pg.read_only = True
            for pe, ex, fy, piid, method, conf, why in pg.execute(
                "select pe_bli, exhibit, fiscal_year, award_piid, method,"
                " confidence, rationale from budget_line_awards"
                " where pe_bli = any(%s) and method = any(%s)",
                (codes, list(MECHANICAL_METHODS)),
            ).fetchall():
                if (pe, ex, int(fy)) in line_keys:
                    stored[(pe, ex, int(fy), piid)] = (method, conf, why)
            for piid, pe, conf in pg.execute(
                "select award_piid, pe_bli, adjudicated_confidence"
                " from award_pe_adjudications where pe_bli = any(%s)", (codes,),
            ).fetchall():
                adjudicated[(piid, pe)] = conf

    org_aliases = _load_subagency_aliases().get(organization, [organization.lower()])
    transitions: dict[tuple, int] = {}
    lost_leg: dict[tuple[str, str], int] = {}
    updates: list[RegradeUpdate] = []
    window_mismatch = 0
    mismatch_windows: dict[str, int] = {}
    seen: set[tuple] = set()
    reproduced = drifted = new_pairs = 0
    con = duckdb.connect()
    memo_key: tuple[str, int | None, int | None] | None = None
    memo: list[tuple[AwardCandidate, set[str]]] = []
    try:
        for pe_bli, exhibit, fy, account, line_title in lines:
            fed_account = _fed_account(account, treasury_agency)
            lo, hi = _line_window(fy, fy_start, fy_end, all_years)
            if (fed_account, lo, hi) != memo_key:
                where, where_params = _candidate_where(fed_account, lo, hi)
                memo = [(c, _award_tokens(c)) for c in _fetch_candidates(
                    con, award_glob, fed_account, where, where_params)]
                memo_key = (fed_account, lo, hi)
            mine = details.get(pe_bli, [])
            # cumulative scopes: none (the merged code), +organization,
            # +edition, +account (the rule)
            scoped = [
                _line_tokens(line_title, mine, organization, fy, account,
                             legs=SCOPE_LEGS[:i])
                for i in range(len(SCOPE_LEGS) + 1)
            ]
            for cand, award_tokens in memo:
                key = (pe_bli, exhibit, int(fy), cand.piid)
                if key not in stored:
                    new_pairs += 1
                    continue
                seen.add(key)
                before = _grade(scoped[0], cand, org_aliases, min_overlap,
                                fed_account, award_tokens)
                if (before[1], before[0]) != stored[key][:2]:
                    drifted += 1
                    continue
                reproduced += 1
                after = _grade(scoped[-1], cand, org_aliases, min_overlap,
                               fed_account, award_tokens)
                if after[:2] == before[:2]:
                    continue
                adj = adjudicated.get((cand.piid, pe_bli))
                bucket = f"adjudicated {adj}" if adj else "unadjudicated"
                t = (before[1], before[0], bucket, after[1], after[0])
                transitions[t] = transitions.get(t, 0) + 1
                window_label = _window_label(lo, hi)
                if _stored_under(stored[key][2], window_label):
                    updates.append(RegradeUpdate(
                        key=key, was_method=before[1], was_confidence=before[0],
                        was_rationale=stored[key][2], bucket=bucket,
                        method=after[1], confidence=after[0], score=after[2],
                        rationale=f"{after[3]}; {window_label}"))
                else:
                    window_mismatch += 1
                    stored_window = _stored_window(stored[key][2])
                    mismatch_windows[stored_window] = (
                        mismatch_windows.get(stored_window, 0) + 1)
                if before[1] == "account+tokens":
                    for leg, tokens in zip(SCOPE_LEGS, scoped[1:]):
                        if len(tokens & award_tokens) < min_overlap:
                            lost_leg[(bucket, leg)] = lost_leg.get((bucket, leg), 0) + 1
                            break
    finally:
        con.close()
    return RegradeReport(
        organization=organization,
        stored_mechanical=len(stored),
        reproduced=reproduced,
        drifted=drifted,
        not_candidate=len(set(stored) - seen),
        new_pairs=new_pairs,
        transitions=dict(sorted(transitions.items())),
        lost_leg=dict(sorted(lost_leg.items())),
        updates=tuple(sorted(updates, key=lambda u: u.key)),
        window_mismatch=window_mismatch,
        mismatch_windows=dict(sorted(mismatch_windows.items())),
    )


#: R-DEC-171's only write: an UPDATE of one stored mechanical row, guarded on
#: the row still reading exactly what regrade_report measured. There is no
#: INSERT anywhere on this path.
REGRADE_UPDATE_SQL = """
update budget_line_awards
   set method = %(method)s, confidence = %(confidence)s, score = %(score)s,
       rationale = %(rationale)s
 where pe_bli = %(pe_bli)s and exhibit = %(exhibit)s
   and fiscal_year = %(fiscal_year)s and award_piid = %(award_piid)s
   and method = %(was_method)s and confidence = %(was_confidence)s
   and rationale = %(was_rationale)s
   and method in ('account', 'account+subagency', 'account+tokens')
"""


class RegradeConflictError(RuntimeError):
    """A row changed between regrade_report and apply_regrade; nothing was
    written (the whole re-grade rolls back)."""


def apply_regrade(dsn: str, report: RegradeReport, *, today=None) -> int:
    """Write `report.updates` in place -- UPDATE only, never INSERT
    (R-DEC-171) -- in one transaction, and return the rows re-graded.

    Each row is rewritten only while it still reads exactly as measured
    (method, confidence and rationale); any row that does not raises
    RegradeConflictError and rolls every update back. The new rationale keeps
    the window label and records the re-grade and the grade it replaced, so
    the move is auditable in the row itself."""
    from datetime import date

    stamp = f"{(today or date.today()):%Y-%m-%d}"
    with psycopg.connect(dsn) as pg:
        with pg.transaction():
            for u in report.updates:
                pe_bli, exhibit, fiscal_year, award_piid = u.key
                cur = pg.execute(REGRADE_UPDATE_SQL, {
                    "method": u.method, "confidence": u.confidence,
                    "score": u.score,
                    "rationale": (f"{u.rationale}; re-graded {stamp} under the"
                                  f" line's own book's detail tokens (#171),"
                                  f" was {u.was_method}/{u.was_confidence}"),
                    "pe_bli": pe_bli, "exhibit": exhibit,
                    "fiscal_year": fiscal_year, "award_piid": award_piid,
                    "was_method": u.was_method,
                    "was_confidence": u.was_confidence,
                    "was_rationale": u.was_rationale,
                })
                if cur.rowcount != 1:
                    raise RegradeConflictError(
                        f"{award_piid}/{pe_bli} ({exhibit}, FY{fiscal_year}) no"
                        f" longer reads {u.was_method}/{u.was_confidence} as"
                        " measured; nothing re-graded -- re-run the dry run")
    return len(report.updates)
