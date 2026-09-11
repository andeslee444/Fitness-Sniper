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
"""
import csv
import re
from dataclasses import dataclass
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


def _load_lines(dsn: str, organization: str) -> list[tuple]:
    """Every distinct budget line of one organization, sorted in Python by
    (account, fiscal_year, pe_bli, exhibit) so lines sharing a (fed_account,
    window) sit together -- that is what makes crosswalk_org's single-entry
    memo effective (DARPA: 10 lake scans instead of 177). Sorted in Python,
    not SQL, so NULL titles/accounts order predictably instead of by
    collation."""
    with psycopg.connect(dsn) as pg:
        rows = pg.execute(
            "select distinct pe_bli, exhibit, fiscal_year, account, title"
            " from budget_lines where organization=%s",
            (organization,),
        ).fetchall()
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
    memo_rows: list[tuple] = []
    try:
        for pe_bli, exhibit, fy, account, line_title in lines:
            fed_account = _fed_account(account, treasury_agency)
            lo, hi = _line_window(fy, fy_start, fy_end, all_years)
            key = (fed_account, lo, hi)
            if key != memo_key:
                memo_rows = con.execute(
                    f"""
                    select award_id_piid,
                           any_value(recipient_name),
                           any_value(recipient_uei),
                           sum(case when federal_accounts_funding_this_award = '{fed_account}'
                                    then try_cast(federal_action_obligation as double) end),
                           any_value(transaction_description),
                           any_value(prime_award_base_transaction_description),
                           any_value(awarding_sub_agency_name)
                    from read_parquet('{award_glob}', union_by_name=true)
                    where {_candidate_where(fed_account, lo, hi)}
                    group by award_id_piid
                    """
                ).fetchall()
                memo_key = key
            pe_tokens = _tokens(line_title) | title_tokens.get(pe_bli, set())
            window_note = "; " + _window_label(lo, hi)

            with psycopg.connect(dsn) as pg:
                for piid, rname, ruei, obligation, desc1, desc2, sub_agency in memo_rows:
                    award_tokens = _tokens(desc1) | _tokens(desc2)
                    overlap = len(pe_tokens & award_tokens)
                    org_in_subagency = any(
                        a in (sub_agency or "").lower() for a in org_aliases
                    )
                    if overlap >= min_overlap:
                        confidence, method = "high", "account+tokens"
                        rationale = f"account {fed_account}; token overlap {overlap}{window_note}"
                    elif org_in_subagency:
                        confidence, method = "medium", "account+subagency"
                        rationale = f"account {fed_account}; sub-agency {sub_agency}{window_note}"
                    else:
                        confidence, method = "low", "account"
                        rationale = f"account {fed_account} only{window_note}"
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
                        (pe_bli, exhibit, fy, organization, piid, rname, ruei,
                         obligation, method, confidence, overlap, rationale),
                    )
                    upserts += 1
    finally:
        con.close()
    return upserts
