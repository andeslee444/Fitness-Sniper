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
"""
import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import duckdb
import psycopg

# Sub-agency alias seed: data-seeds/org_subagency_aliases.csv, columns
# organization,alias. Replaces a hardcoded DARPA-only clause (#75) — every
# organization's medium-tier sub-agency match now comes from this file.
# crosswalk.py -> jbooks -> govbudget -> src -> GovBudget (parents[3]).
_ALIASES_CSV = Path(__file__).resolve().parents[3] / "data-seeds" / "org_subagency_aliases.csv"


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
# starts with (#75a). A NULL or unparseable action_date yields NULL, which no
# BETWEEN matches, so such a row is excluded under any window and kept under
# none -- the behaviour the explicit window has had since #75a.
FED_FY_EXPR = (
    "(try_cast(substr(action_date,1,4) as integer)"
    " + case when try_cast(substr(action_date,6,2) as integer)"
    " >= 10 then 1 else 0 end)"
)


def _validate_window(
    fy_start: int | None, fy_end: int | None, all_years: bool,
) -> None:
    """Loud failure for the two window shapes that used to be silently
    reinterpreted: one bound alone (pre-#78 it was dropped, i.e. the run went
    unbounded) and all_years stacked on an explicit window (contradictory)."""
    if (fy_start is None) != (fy_end is None):
        raise ValueError(
            "fy_start and fy_end must be given together"
            f" (got fy_start={fy_start!r}, fy_end={fy_end!r})"
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
) -> str:
    """The candidate predicate, shared by the planner and the write path so a
    plan can never count rows the run would not upsert. fy_start/fy_end here
    are ONE LINE's resolved bounds (see _line_window), not the CLI flags."""
    where = (
        f"federal_accounts_funding_this_award like '%{fed_account}%'"
        " and award_id_piid is not null and award_id_piid <> ''"
    )
    if fy_start is not None:
        where += f" and {FED_FY_EXPR} between {fy_start} and {fy_end}"
    return where


# One canonical budget line per (pe_bli, exhibit, fiscal_year, account) key
# within the organization (#85). DISTINCT ON keeps the FIRST row under the
# ORDER BY, so every tiebreak is written out: the latest document (edition FY,
# then when it was downloaded, then id), then the lowest budget activity, then
# the first title. Postgres orders DESC with NULLS FIRST by default, hence the
# explicit NULLS LAST on the nullable legs. budget_lines.source_document_id is
# NOT NULL (migration 005), so the join drops nothing. When two rows tie on
# every leg they are identical in all five selected columns, so which one
# DISTINCT ON keeps cannot change the result.
CANONICAL_LINE_SQL = """
select distinct on (b.pe_bli, b.exhibit, b.fiscal_year, b.account)
       b.pe_bli, b.exhibit, b.fiscal_year, b.account, b.title
from budget_lines b
join jbook_documents d on d.id = b.source_document_id
where b.organization = %s
order by b.pe_bli, b.exhibit, b.fiscal_year, b.account,
         d.fiscal_year desc, d.downloaded_at desc nulls last, d.id desc,
         b.budget_activity asc nulls last, b.title asc nulls last
"""


def _load_lines(dsn: str, organization: str) -> list[tuple]:
    """Exactly one (pe_bli, exhibit, fiscal_year, account, title) row per key
    for the org -- the canonical title (CANONICAL_LINE_SQL) -- sorted in Python
    by (account, fiscal_year, pe_bli, exhibit) so lines sharing a
    (fed_account, window) sit together for the single-entry memo and the
    iteration order is fixed. plan_crosswalk_org iterates the same list, so a
    multi-title key is planned once, not once per variant. Live counts
    2026-09-10: DARPA 177 -> 177 (no variants), org F 1,739 -> 1,736."""
    with psycopg.connect(dsn) as pg:
        rows = pg.execute(CANONICAL_LINE_SQL, (organization,)).fetchall()
    return sorted(rows, key=lambda r: (r[3] or "", r[2], r[0] or "", r[1] or ""))


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
) -> list[LinePlan]:
    """Count the (line, award) pairs crosswalk_org WOULD upsert -- one
    LinePlan per budget line -- without writing anything (#78: --dry-run, and
    the projected-row abort).

    Same lines, same account mapping, same per-line window, same predicate:
    the planner and the write path share _load_lines / _fed_account /
    _line_window / _candidate_where, and the write path's `group by
    award_id_piid` returns exactly one row per distinct PIID, so
    `count(distinct award_id_piid)` here cannot drift from it.
    """
    _validate_window(fy_start, fy_end, all_years)
    lines = _load_lines(dsn, organization)
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
                memo_n = con.execute(
                    "select count(distinct award_id_piid)"
                    f" from read_parquet('{award_glob}', union_by_name=true)"
                    f" where {_candidate_where(fed_account, lo, hi)}"
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
    con: duckdb.DuckDBPyConnection, award_glob: str, fed_account: str, where: str,
) -> list[AwardCandidate]:
    """The only lake query in the write path. Every aggregate is
    order-independent (list / arg_max / decimal sum) -- no any_value() anywhere,
    which is what #85 was. Rows come back ordered by PIID so upsert order, and
    therefore bigserial ids on a fresh table, are fixed too. `where` is
    _candidate_where(fed_account, lo, hi) -- the same predicate
    plan_crosswalk_org counts, so a plan still cannot drift from the run."""
    rows = con.execute(
        f"""
        select award_id_piid,
               arg_max(recipient_name, {LATEST_TX_KEY}),
               arg_max(recipient_uei, {LATEST_TX_KEY}),
               sum(case when federal_accounts_funding_this_award = '{fed_account}'
                        then try_cast(federal_action_obligation as decimal(20,2)) end),
               list(distinct transaction_description order by transaction_description),
               list(distinct prime_award_base_transaction_description
                    order by prime_award_base_transaction_description),
               list(awarding_sub_agency_name order by awarding_sub_agency_name)
        from read_parquet('{award_glob}', union_by_name=true)
        where {where}
        group by award_id_piid
        order by award_id_piid
        """
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


def _grade(
    pe_tokens: set[str], cand: AwardCandidate, org_aliases: list[str],
    min_overlap: int, fed_account: str,
) -> tuple[str, str, int, str]:
    """The tier rule, pure. Returns (confidence, method, score, rationale
    core); the caller appends the window label. Precedence is unchanged:
    token overlap -> high, else any-transaction sub-agency -> medium, else
    account only -> low.

    Sub-agency semantics (controller ruling 2026-09-05, the pre-existing rule
    made explicit): an award carries the organization's sub-agency when ANY of
    its transactions in the window was awarded under it -- not the dominant
    one, not the latest one, not whichever one was scanned first.
    """
    award_tokens: set[str] = set().union(*(_tokens(d) for d in cand.descriptions))
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
) -> int:
    """Crosswalk all of one organization's budget lines against the award lake.

    Window: fy_start/fy_end (both) pin an explicit federal-FY window on
    action_date; all_years=True matches every loaded award year; otherwise
    each line matches only awards in its own edition fiscal_year (#78).

    Deterministic (#85): one canonical title per key (_load_lines) and every
    award graded from all of its transactions in the window
    (_fetch_candidates + _grade). Two runs over the same inputs write the
    same rows.

    Returns the number of (pe_bli, award) upsert statements issued (rows whose
    existing method is evidence-graded are guarded and left untouched but
    still counted — #86 minor 2, unchanged here).
    """
    _validate_window(fy_start, fy_end, all_years)
    lines = _load_lines(dsn, organization)
    with psycopg.connect(dsn) as pg:
        detail_rows = pg.execute(
            "select pe_bli, project_title from budget_line_details"
            " where not superseded",
        ).fetchall()

    title_tokens: dict[str, set[str]] = {}
    for pe_bli, proj_title in detail_rows:
        if pe_bli:
            title_tokens.setdefault(pe_bli, set()).update(_tokens(proj_title))

    aliases = _load_subagency_aliases()
    org_aliases = aliases.get(organization, [organization.lower()])

    con = duckdb.connect()
    upserts = 0
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
                memo_rows = _fetch_candidates(
                    con, award_glob, fed_account, _candidate_where(fed_account, lo, hi),
                )
                memo_key = key
            # Computed ONCE per canonical line (#85): one title per key.
            pe_tokens = _tokens(line_title) | title_tokens.get(pe_bli, set())
            window_note = "; " + _window_label(lo, hi)

            with psycopg.connect(dsn) as pg:
                for cand in memo_rows:
                    confidence, method, score, why = _grade(
                        pe_tokens, cand, org_aliases, min_overlap, fed_account,
                    )
                    rationale = f"{why}{window_note}"
                    pg.execute(
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
                    upserts += 1
    finally:
        con.close()
    return upserts
