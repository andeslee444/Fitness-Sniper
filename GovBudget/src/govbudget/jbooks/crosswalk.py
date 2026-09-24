"""Deterministic budget-line -> award crosswalk (v1).

Method 1 (account): an award qualifies as a candidate for a budget line when
the line's federal account (e.g. 097-0400) appears in the award's
federal_accounts_funding_this_award list. Method 2 (token overlap): candidate
confidence is raised to 'high' when PE/title tokens overlap the award's
descriptions. Everything lands in budget_line_awards with method + confidence;
nothing is asserted silently. v1 is LLM-free by design (recorded decision).

v1 links are account+evidence-scoped; FY attribution is explicit via
a paired fy_start/fy_end override, or each budget edition's own FY by default.
"""
import csv
from dataclasses import dataclass
import re

import duckdb
import psycopg

from govbudget import config

# Sub-agency alias seed: data-seeds/org_subagency_aliases.csv, columns
# organization,alias. Replaces a hardcoded DARPA-only clause (#75) — every
# organization's medium-tier sub-agency match now comes from this file.
_ALIASES_CSV = config.ROOT / "data-seeds" / "org_subagency_aliases.csv"


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


# Count every candidate, including protected rows: the cap is a conservative
# bound on the entire run, not an estimate of how many existing rows can change.
DEFAULT_MAX_ROWS = 100_000


@dataclass(frozen=True)
class CrosswalkPlan:
    organization: str
    rows: tuple[tuple, ...]

    @property
    def projected_rows(self) -> int:
        return len(self.rows)


def validate_crosswalk_window(
    fy_start: int | None, fy_end: int | None,
    fiscal_year: int | None = None, max_rows: int = DEFAULT_MAX_ROWS,
) -> None:
    if (fy_start is None) != (fy_end is None):
        raise ValueError("--fy-start and --fy-end must be supplied together")
    for year in (fy_start, fy_end, fiscal_year):
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)
                                 or not 1900 <= year <= 2200):
            raise ValueError("Fiscal years must be integers between 1900 and 2200")
    if fy_start is not None and fy_start > fy_end:
        raise ValueError("--fy-start must not be after --fy-end")
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows < 1:
        raise ValueError("--max-rows must be a positive integer")


def plan_crosswalk_org(
    dsn: str, *, organization: str, treasury_agency: str, award_glob: str,
    min_overlap: int = 2, fy_start: int | None = None,
    fy_end: int | None = None, fiscal_year: int | None = None,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> CrosswalkPlan:
    """Build a read-only, capped plan before opening any write transaction.

    No FY override means that each budget edition sees only award actions in
    its own federal FY. --fiscal-year restricts budget editions; the paired
    FY override deliberately selects a different award-action window.
    """
    validate_crosswalk_window(fy_start, fy_end, fiscal_year, max_rows)
    if isinstance(min_overlap, bool) or not isinstance(min_overlap, int) or min_overlap < 1:
        raise ValueError("min_overlap must be a positive integer")
    with psycopg.connect(dsn) as pg:
        lines = pg.execute(
            # Preserve the historical canonical-title rule (#85): latest
            # source edition/download, then lowest activity and title.
            "select distinct on (b.pe_bli,b.exhibit,b.fiscal_year,b.account)"
            " b.pe_bli,b.exhibit,b.fiscal_year,b.account,b.title"
            " from budget_lines b join jbook_documents d on d.id=b.source_document_id"
            " where b.organization=%s and (%s::int is null or b.fiscal_year=%s)"
            " order by b.pe_bli,b.exhibit,b.fiscal_year,b.account,"
            " d.fiscal_year desc,d.downloaded_at desc nulls last,d.id desc,"
            " b.budget_activity asc nulls last,b.title asc nulls last",
            (organization, fiscal_year, fiscal_year),
        ).fetchall()
        detail_rows = pg.execute(
            "select d.pe_bli, j.fiscal_year, d.account, d.project_title"
            " from budget_line_details d join jbook_documents j on j.id=d.document_id"
            " where not d.superseded and j.org=%s"
            " and (%s::int is null or j.fiscal_year=%s)",
            (organization, fiscal_year, fiscal_year),
        ).fetchall()

    # Canonical title selection yields one classification per identity.
    # The current table key cannot represent two accounts for the same line.
    # Reject that ambiguity instead of choosing whichever account came last.
    line_tokens: dict[tuple, set[str]] = {}
    accounts: dict[tuple, str] = {}
    for pe_bli, exhibit, fy, account, title in lines:
        identity = (pe_bli, exhibit, fy)
        if not account:
            raise ValueError(f"Missing account for {identity!r}")
        if identity in accounts and accounts[identity] != account:
            raise ValueError(f"Ambiguous accounts for {identity!r}; crosswalk aborted")
        accounts[identity] = account
        line_tokens.setdefault(identity, set()).update(_tokens(title))
    for pe_bli, fy, account, project_title in detail_rows:
        for identity, tokens in line_tokens.items():
            if identity[0] == pe_bli and identity[2] == fy and (
                account is None or account == accounts[identity]
            ):
                tokens.update(_tokens(project_title))

    if not line_tokens:
        return CrosswalkPlan(organization, ())

    aliases = _load_subagency_aliases()
    org_aliases = aliases.get(organization, [organization.lower()])
    planned: list[tuple] = []
    with duckdb.connect() as con:
        con.read_parquet(award_glob, union_by_name=True).create_view("award_input")
        con.execute("""
            create temp view awards as
            select *,
              list_transform(regexp_split_to_array(
                coalesce(federal_accounts_funding_this_award, ''), '[;,]'),
                x -> trim(x)) as account_codes,
              year(try_cast(action_date as date)) +
                case when month(try_cast(action_date as date)) >= 10 then 1 else 0 end
                as action_fy
            from award_input
            where award_id_piid is not null and award_id_piid <> ''
        """)
        # One account/window query can serve many lines. Counts are checked
        # before materializing assignments and before any Postgres write.
        windows: dict[tuple, list[tuple]] = {}
        for identity in sorted(line_tokens):
            account = accounts[identity]
            if account[-1:].isalpha():
                numeric, letter = account[:-1], account[-1].upper()
            else:
                numeric, letter = account, None
            agency = AGENCY_BY_LETTER.get(letter, treasury_agency)
            fed_account = f"{agency}-{numeric}"
            start, end = (identity[2], identity[2]) if fy_start is None else (fy_start, fy_end)
            windows.setdefault((fed_account, start, end), []).append(identity)
        projected = 0
        for (fed_account, start, end), identities in sorted(windows.items()):
            count = con.execute(
                "select count(distinct award_id_piid) from awards"
                " where list_contains(account_codes, ?) and action_fy between ? and ?",
                (fed_account, start, end),
            ).fetchone()[0]
            projected += count * len(identities)
            if projected > max_rows:
                raise ValueError(
                    f"Projected crosswalk rows {projected:,} exceed --max-rows {max_rows:,};"
                    " no links written. Narrow --fiscal-year or the award FY window."
                )
        for (fed_account, start, end), identities in sorted(windows.items()):
            rows = con.execute(
                """
                select award_id_piid,
                  first(struct_pack(name := recipient_name, uei := recipient_uei)
                    order by try_cast(action_date as date) desc nulls last,
                    coalesce(contract_transaction_unique_key, '') desc,
                    coalesce(recipient_name, ''), coalesce(recipient_uei, '')),
                  case when bool_and(account_codes = [?]) then
                    sum(try_cast(federal_action_obligation as decimal(38,6))) end,
                  list(distinct transaction_description order by transaction_description),
                  list(distinct prime_award_base_transaction_description
                    order by prime_award_base_transaction_description),
                  list(awarding_sub_agency_name order by awarding_sub_agency_name)
                from awards
                where list_contains(account_codes, ?) and action_fy between ? and ?
                group by award_id_piid order by award_id_piid
                """,
                (fed_account, fed_account, start, end),
            ).fetchall()
            for identity in identities:
                for piid, recipient, obligation, descriptions, base_descriptions, agencies in rows:
                    award_tokens = set().union(*(
                        _tokens(d) for d in descriptions + base_descriptions
                    ))
                    overlap = len(line_tokens[identity] & award_tokens)
                    matching_agencies = [s for s in agencies if s and any(
                        a in s.lower() for a in org_aliases
                    )]
                    scope = f"; award action FY{start}" + (f"–FY{end}" if end != start else "")
                    if overlap >= min_overlap:
                        confidence, method = "high", "account+tokens"
                        rationale = f"account {fed_account}; token overlap {overlap}{scope}"
                    elif matching_agencies:
                        confidence, method = "medium", "account+subagency"
                        rationale = (f"account {fed_account}; sub-agency {'; '.join(sorted(set(matching_agencies)))}"
                                     f" on {len(matching_agencies)} of {len(agencies)} transaction(s){scope}")
                    else:
                        confidence, method = "low", "account"
                        rationale = f"account {fed_account} only{scope}"
                    planned.append((*identity, organization, piid, recipient["name"],
                                    recipient["uei"], obligation, method, confidence,
                                    overlap, rationale))
    return CrosswalkPlan(organization, tuple(sorted(planned, key=lambda r: r[:5])))


def apply_crosswalk_plans(
    dsn: str, plans: list[CrosswalkPlan], *, max_rows: int = DEFAULT_MAX_ROWS,
) -> int:
    """Apply a fully preflighted run atomically; count only actual writes.

    Every evidence/human method remains protected even if inserted between
    planning and application. A later failure rolls back every organization.
    """
    validate_crosswalk_window(None, None, max_rows=max_rows)
    projected = sum(p.projected_rows for p in plans)
    if projected > max_rows:
        raise ValueError(f"Projected crosswalk rows {projected:,} exceed --max-rows {max_rows:,}; no links written")
    keys = [(*r[:3], r[4]) for p in plans for r in p.rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate crosswalk identities across plans; no links written")
    changed = 0
    with psycopg.connect(dsn) as pg:
        for plan in plans:
            for row in plan.rows:
                result = pg.execute(
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
                                  recipient_name=excluded.recipient_name,
                                  recipient_uei=excluded.recipient_uei,
                                  matched_obligation=excluded.matched_obligation
                    where budget_line_awards.method in
                          ('account', 'account+subagency', 'account+tokens')
                      and budget_line_awards.organization=excluded.organization
                    """, row,
                )
                changed += result.rowcount
    return changed


def crosswalk_org(
    dsn: str, *, organization: str, treasury_agency: str, award_glob: str,
    min_overlap: int = 2, fy_start: int | None = None,
    fy_end: int | None = None, fiscal_year: int | None = None,
    max_rows: int = DEFAULT_MAX_ROWS, dry_run: bool = False,
) -> int:
    """Return candidate count for dry runs, or the actual guarded write count."""
    plan = plan_crosswalk_org(
        dsn, organization=organization, treasury_agency=treasury_agency,
        award_glob=award_glob, min_overlap=min_overlap, fy_start=fy_start,
        fy_end=fy_end, fiscal_year=fiscal_year, max_rows=max_rows,
    )
    if dry_run:
        return plan.projected_rows
    return apply_crosswalk_plans(dsn, [plan], max_rows=max_rows)
