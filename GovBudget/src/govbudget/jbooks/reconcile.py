from decimal import Decimal

import psycopg

TOLERANCE_M = Decimal("0.001")

def scenario_map(fiscal_year: int) -> dict[str, list[str]]:
    """XML scenario -> candidate R-1/P-1 amount_type slugs for one PB edition.

    Gate B passes if ANY candidate matches within tolerance (PB books split
    base/OOC/total differently per org, and the display-workbook column
    headers vary by edition). Scenario names are edition-relative: for
    edition year N, PriorYear=FY(N-2) actuals, CurrentYear=FY(N-1),
    BudgetYearOne=FY(N) total request, BudgetYearOneBase=FY(N) base/disc.

    Header-variant candidates are empirical, from the editions on disk
    (Phase 5E Task 4 live-run evidence):
      - PB2026: 'FY 2025 Total'/'FY 2025 Enacted', 'FY 2026 Total'/'FY 2026
        Disc Request' — the original slugs, kept first in original order.
      - PB2024: 'FY 2023 Total Enacted', 'FY 2023 Less Supplementals
        Enacted', 'FY 2024 Request'. (The supplementals-only column is
        intentionally NOT a CurrentYear candidate.)
      - PB2025: 'FY 2024 PB Request with CR Amounts*' (R-1) / '... with CR
        Adjustments Amount*' (P-1) — FY2024 ran under a continuing
        resolution when PB2025 published — plus 'FY 2025 Request'.
      - PB2017–PB2023 (Task 4 round 2, live workbook evidence): prior-year
        actuals labelled 'FY N-2 (Base & OCO)'/'(Base + OCO)' (2017–2021,
        2023) or 'FY N-2 Actual*' (2022, singular); current-year enacted
        labelled 'Total Enacted (Base+Emerg+OCO)' (2021), 'Enactment*'
        (2023), or the FY2017/FY2018 CR-mess 'Total PB Requests with CR Adj
        Base + OCO [+ SAA / + Emergency]' (2018/2019); budget-year request
        split Base / OCO / 'Total (Base + OCO)' (2017–2021).
    Candidate slugs that don't exist in an edition's budget_lines never
    match, so each edition only ever reconciles against its own headers.
    """
    py, cy, by = fiscal_year - 2, fiscal_year - 1, fiscal_year
    return {
        "PriorYear": [f"fy_{py}_actuals", f"fy_{py}_base_oco", f"fy_{py}_actual"],
        "CurrentYear": [
            f"fy_{cy}_total", f"fy_{cy}_enacted", f"fy_{cy}_total_enacted",
            f"fy_{cy}_less_supplementals_enacted",
            f"fy_{cy}_pb_request_with_cr_amounts",
            f"fy_{cy}_pb_request_with_cr_adjustments",
            f"fy_{cy}_enactment",
            f"fy_{cy}_total_enacted_base_emerg_oco",
            f"fy_{cy}_total_pb_requests_with_cr_adj_base_oco",
            f"fy_{cy}_total_pb_requests_with_cr_adj_base_oco_saa",
            f"fy_{cy}_total_pb_requests_with_cr_adj_base_oco_emergency",
        ],
        "BudgetYearOne": [
            f"fy_{by}_total", f"fy_{by}_disc_request", f"fy_{by}_request",
            f"fy_{by}_total_base_oco",
        ],
        "BudgetYearOneBase": [
            f"fy_{by}_disc_request", f"fy_{by}_total", f"fy_{by}_request",
            f"fy_{by}_base",
        ],
    }

# Extracted but intentionally not reconciled: no R-1 display analog.
# Marts and the accuracy gate treat these as not-served-by-design,
# distinct from pending-review.
DESIGN_EXCLUDED_SCENARIOS = frozenset({"AllPriorYears", "BudgetYearOneOOC"})


# Resolution memory (#9): a failure re-flagged by a later extraction run with
# the same expected/actual a person already accepted is inserted pre-accepted,
# with a resolution naming the ROOT human decision. Carried rows are recognised
# by this prefix — `review list` reports them apart from open items, and the
# re-reconcile prune re-derives them (the root row is the audit trail, not the
# carried copies).
CARRIED_PREFIX = "carried from #"


def carried_resolution(prior_id: int, prior_resolution: str | None) -> str:
    """Resolution text for a queue row pre-accepted from a prior triage.

    Points at the root human acceptance: when the prior row is itself a
    carried copy its text is reused verbatim, so chains never grow and the
    id always names a row a person accepted.
    """
    reason = (prior_resolution or "").strip()
    if reason.startswith(CARRIED_PREFIX):
        return reason
    return f"{CARRIED_PREFIX}{prior_id}" + (f": {reason}" if reason else "")


def reconcile_document(dsn: str, *, document_id: int, extraction_run_id: int) -> dict:
    """Run Gates A and B for one document's live details. Returns counters."""
    counts = {"passed": 0, "failed": 0, "queued": 0, "carried": 0}
    with psycopg.connect(dsn) as con:
        org, family, fy = con.execute(
            "select org, exhibit_family, fiscal_year from jbook_documents where id=%s",
            (document_id,),
        ).fetchone()
        # Re-reconciling replaces this document's verdicts: drop prior checks
        # and their UNRESOLVED queue items, plus machine-carried acceptances
        # (re-derived from their root by _tally below). Human-accepted rows
        # keep their audit trail.
        con.execute(
            """
            delete from review_queue rq using reconciliation_checks c, extraction_runs r
            where rq.check_id = c.id and c.extraction_run_id = r.id
              and r.document_id = %s
              and (rq.status = 'open' or rq.resolution like %s)
            """,
            (document_id, CARRIED_PREFIX + "%"),
        )
        con.execute(
            """
            delete from reconciliation_checks c using extraction_runs r
            where c.extraction_run_id = r.id and r.document_id = %s
              and not exists (select 1 from review_queue rq where rq.check_id = c.id)
            """,
            (document_id,),
        )
        from govbudget.jbooks.orgs import CONSOLIDATED_ORGS, workbook_org

        org = workbook_org(org)
        # Consolidated Defense-Wide volumes (PB2018–PB2023) span many workbook
        # orgs: their Gate B candidates are computed per organization instead
        # of pinned to the document org.
        consolidated = org in CONSOLIDATED_ORGS
        exhibit = {"rdte": "R-1", "procurement": "P-1"}.get(family)
        # ---------- Gate A: project rows sum to the PE-level amount ----------
        gate_a_rows = con.execute(
            """
            with pe as (
              select pe_bli, scenario, amount_millions from budget_line_details
              where document_id=%s and not superseded and project_number is null
            ), proj as (
              select pe_bli, scenario, sum(amount_millions) total, count(*) n
              from budget_line_details
              where document_id=%s and not superseded and project_number is not null
              group by pe_bli, scenario
            )
            select pe.pe_bli, pe.scenario, pe.amount_millions, proj.total
            from pe join proj using (pe_bli, scenario)
            """,
            (document_id, document_id),
        ).fetchall()
        for pe_bli, scenario, pe_amount, proj_total in gate_a_rows:
            ok = abs(pe_amount - proj_total) <= TOLERANCE_M
            check_id = _record(con, extraction_run_id, "A", pe_bli, scenario,
                               pe_amount, proj_total, ok,
                               f"sum(projects)={proj_total} vs PE={pe_amount}")
            _tally(con, counts, check_id, ok, document_id=document_id)
            if not ok:
                _unreconcile(con, document_id, pe_bli, scenario)

        # ---------- Gate B: PE-level amount matches R-1 control rows ----------
        # Split-funded PEs have one R-1 row per budget activity: sum them.
        # `account` disambiguates procurement P-1 line numbers that collide
        # within an org (Navy FY2026: line 2210 under 1507N vs 1810N); it is
        # NULL for R-1/RDT&E and legacy era-namespaced rows, where the prior
        # cross-account behavior is kept.
        pe_rows = con.execute(
            "select pe_bli, scenario, amount_millions, account from budget_line_details "
            "where document_id=%s and not superseded and project_number is null",
            (document_id,),
        ).fetchall()
        # Some books omit a PE-level funding element for a scenario while the
        # project list carries it explicitly (absent = zero at PE level, e.g.
        # OSD PB2026 0605755D8Z PriorYear; DW PB2022 0303430V PriorYear/
        # CurrentYear). Neither gate would ever see those facts: reconcile the
        # project-level sum as the PE amount so they get a verdict too.
        pe_seen = {(p, s) for p, s, _, _ in pe_rows}
        proj_only_rows = [
            r for r in con.execute(
                "select pe_bli, scenario, sum(amount_millions), min(account) "
                "from budget_line_details "
                "where document_id=%s and not superseded "
                "and project_number is not null "
                "group by pe_bli, scenario",
                (document_id,),
            ).fetchall()
            if (r[0], r[1]) not in pe_seen
        ]
        edition_map = scenario_map(fy)
        total_type = f"fy_{fy}_total"
        recon_type = f"fy_{fy}_reconciliation_request"
        for pe_bli, scenario, amount_m, account, basis in (
            [(*r, "") for r in pe_rows]
            + [(*r, " [PE funding absent: sum(projects) basis]")
               for r in proj_only_rows]
        ):
            candidates = edition_map.get(scenario)
            if not candidates:
                continue
            fetch_types = list(candidates) + [total_type, recon_type]
            # Procurement P-1 line numbers are unique only within an account:
            # scope the control lookup by account when the detail carries one
            # (NULL for R-1/RDT&E and era rows, where cross-account sum stands).
            acct_clause = " and account=%s" if account is not None else ""
            acct_param = (account,) if account is not None else ()
            if consolidated:
                rows = con.execute(
                    "select amount_type, organization, sum(amount_thousands) "
                    "from budget_lines "
                    "where pe_bli=%s and amount_type = any(%s) "
                    "and exhibit=%s and fiscal_year=%s" + acct_clause + " "
                    "group by amount_type, organization",
                    (pe_bli, fetch_types, exhibit, fy) + acct_param,
                ).fetchall()
            else:
                rows = [
                    (t, org, v) for t, v in con.execute(
                        "select amount_type, sum(amount_thousands) from budget_lines "
                        "where pe_bli=%s and amount_type = any(%s) "
                        "and exhibit=%s and organization=%s and fiscal_year=%s"
                        + acct_clause + " "
                        "group by amount_type",
                        (pe_bli, fetch_types, exhibit, org, fy) + acct_param,
                    ).fetchall()
                ]
            control_orgs = sorted({o for _, o, _ in rows})
            by_type_org = {(t, o): v for t, o, v in rows}
            present = [
                (t, by_type_org[(t, o)] / Decimal(1000))  # R-1 $K -> $M
                for t in candidates
                for o in control_orgs
                if by_type_org.get((t, o)) is not None
            ]
            if scenario in ("BudgetYearOne", "BudgetYearOneBase"):
                for o in control_orgs:
                    total = by_type_org.get((total_type, o))
                    recon = by_type_org.get((recon_type, o))
                    if total is not None and recon is not None:
                        present.append((
                            f"fy_{fy}_total_minus_recon",
                            (total - recon) / Decimal(1000),
                        ))
            match = next(
                ((t, v) for t, v in present if abs(v - amount_m) <= TOLERANCE_M), None
            )
            if match:
                matched_type, expected = match
                ok = True
                detail = f"{exhibit} {matched_type}={expected}M vs XML {scenario}={amount_m}M"
            elif present:
                matched_type, expected = present[0]
                ok = False
                detail = f"{exhibit} {matched_type}={expected}M vs XML {scenario}={amount_m}M"
            elif amount_m == 0:
                # The R-1 display omits empty cells; an absent control row is
                # semantically zero. Only an explicit zero may match it.
                expected = None
                ok = True
                detail = f"absent {exhibit} cell == XML {scenario}=0.000 (zero-absent rule)"
            else:
                expected = None
                ok = False
                detail = f"no R-1 row for {pe_bli} ({exhibit}/{org}/fy{fy}) in {candidates}"
            check_id = _record(con, extraction_run_id, "B", pe_bli, scenario,
                               expected, amount_m, ok, detail + basis)
            _tally(con, counts, check_id, ok, document_id=document_id)
            if ok:
                con.execute(
                    "update budget_line_details set reconciled=true "
                    "where document_id=%s and pe_bli=%s and scenario=%s and not superseded "
                    "and not exists (select 1 from reconciliation_checks c "
                    "  where c.extraction_run_id=%s and c.pe_bli=%s and c.scenario=%s "
                    "  and not c.passed)",
                    (document_id, pe_bli, scenario, extraction_run_id, pe_bli, scenario),
                )
            else:
                _unreconcile(con, document_id, pe_bli, scenario)
    return counts


def _record(con, run_id, gate, pe_bli, scenario, expected, actual, ok, detail) -> int:
    return con.execute(
        "insert into reconciliation_checks (extraction_run_id, gate, pe_bli, scenario,"
        " expected, actual, passed, detail) values (%s,%s,%s,%s,%s,%s,%s,%s) returning id",
        (run_id, gate, pe_bli, scenario, expected, actual, ok, detail),
    ).fetchone()[0]


def _tally(con, counts, check_id, ok, *, document_id):
    """Count the verdict and queue a failure — pre-accepted when a person
    already accepted these exact numbers on this document (#9).
    Invariant: counts["failed"] == counts["queued"] + counts["carried"]."""
    if ok:
        counts["passed"] += 1
        return
    counts["failed"] += 1
    prior = _prior_acceptance(con, document_id=document_id, check_id=check_id)
    if prior is None:
        con.execute("insert into review_queue (check_id) values (%s)", (check_id,))
        counts["queued"] += 1
        return
    prior_id, prior_resolution = prior
    con.execute(
        "insert into review_queue (check_id, status, resolution, resolved_at)"
        " values (%s, 'accepted', %s, now())",
        (check_id, carried_resolution(prior_id, prior_resolution)),
    )
    counts["carried"] += 1


def _prior_acceptance(con, *, document_id, check_id):
    """The accepted queue row for the same document / gate / pe_bli / scenario
    with the same expected and actual as check `check_id` (root human
    decisions ordered before carried copies; newest first); None when nobody
    has triaged these numbers before. `detail` is deliberately not compared:
    within one document it is a function of the key plus the two numbers, and
    its slug half can be renamed by scenario_map() without the mismatch
    changing."""
    return con.execute(
        """
        select rq.id, rq.resolution
        from reconciliation_checks n
        join reconciliation_checks p
          on p.gate = n.gate and p.pe_bli = n.pe_bli and p.scenario = n.scenario
         and p.expected is not distinct from n.expected
         and p.actual is not distinct from n.actual
         and p.id <> n.id
        join extraction_runs r on r.id = p.extraction_run_id
        join review_queue rq on rq.check_id = p.id
        where n.id = %s and r.document_id = %s and rq.status = 'accepted'
        order by (coalesce(rq.resolution, '') like %s), rq.id desc
        limit 1
        """,
        (check_id, document_id, CARRIED_PREFIX + "%"),
    ).fetchone()


def _unreconcile(con, document_id, pe_bli, scenario):
    con.execute(
        "update budget_line_details set reconciled=false "
        "where document_id=%s and pe_bli=%s and scenario=%s and not superseded",
        (document_id, pe_bli, scenario),
    )
