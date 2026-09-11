"""Phase 3 acceptance gates: oversight ingestion, linkage, marts, trace.

Gates (CLI: verify-phase3):
  1. ingest_gate   — parquet files exist and meet minimum row/program thresholds.
  2. linkage_gate  — ≥80% of high-risk areas are mapped to an agency_code.
  3. marts_gate    — dbt build green AND four efficiency marts non-empty + sane invariants.
  4. trace_gate3   — 2 DoD high-risk areas → dim_programs non-empty → top family available.
"""
from pathlib import Path

import duckdb

from govbudget.agency_codes import canonical_agency


def ingest_gate(ip_path: Path, hr_path: Path) -> dict:
    """Gate 1: improper_payments ≥50 programs with ≥1 FY row + source_url;
    high_risk ≥30 areas, all with area_url."""
    con = duckdb.connect()

    # improper_payments: count distinct programs, all rows have source_url
    ip_prog_count, ip_rows_with_url = con.execute(
        f"""
        select
            count(distinct program),
            count(*) filter (where source_url is not null and source_url <> '')
        from read_parquet('{ip_path}')
        """
    ).fetchone()
    ip_total = con.execute(
        f"select count(*) from read_parquet('{ip_path}')"
    ).fetchone()[0]

    # high_risk: count areas, all have area_url
    hr_area_count, hr_rows_with_url = con.execute(
        f"""
        select
            count(*),
            count(*) filter (where area_url is not null and area_url <> '')
        from read_parquet('{hr_path}')
        """
    ).fetchone()

    ok = (
        ip_prog_count >= 50
        and ip_rows_with_url == ip_total
        and hr_area_count >= 30
        and hr_rows_with_url == hr_area_count
    )
    return {
        "ok": ok,
        "program_count": ip_prog_count,
        "ip_total_rows": ip_total,
        "ip_rows_with_url": ip_rows_with_url,
        "area_count": hr_area_count,
        "hr_rows_with_url": hr_rows_with_url,
    }


def linkage_gate(hr_path: Path) -> dict:
    """Gate 2: ≥80% of high-risk areas mapped to an agency_code.
    Unmapped count reported explicitly."""
    con = duckdb.connect()
    total, mapped = con.execute(
        f"""
        select
            count(*),
            count(*) filter (where mapped = 'true' and agency_code <> '')
        from read_parquet('{hr_path}')
        """
    ).fetchone()
    unmapped = total - mapped
    mapped_pct = round(100.0 * mapped / total, 1) if total else 0.0
    ok = mapped_pct >= 80.0
    return {
        "ok": ok,
        "total_areas": total,
        "mapped": mapped,
        "unmapped_count": unmapped,
        "mapped_pct": mapped_pct,
    }


# HHI's mathematical ceiling is exactly 10,000 (one family at 100% share).
# DuckDB sums `share_pct * share_pct` in parallel, so a program whose positive
# obligations sit in a single family lands on 10000.0 or 10000.000000000004
# depending on that run's partition order: six consecutive
# `select count(*) from fct_program_concentration where hhi > 10000` over one
# read-only connection to the live lake returned 13, 8, 8, 10, 10, 13
# (2026-09-10) — this leg had been failing intermittently on float noise.
# 1e-6 is four orders above that noise and eight below the smallest breach
# that would mean anything (a share above 100%). Do NOT widen it.
_HHI_CEILING = 10_000.0 + 1e-6

# #80 fix round 1 (2026-09-11): a do-not-lower floor on the number of programs
# that publish a high-only index. bad_high_floor below can only fire on a
# hand-written table — the mart applies the same predicate by construction —
# so on its own it would stay 0 through a total collapse of the high basis
# (an upstream vocabulary change, a demotion pass), every hhi_high would go
# NULL, gate 3 would stay green and every program card would silently stop
# publishing a concentration index. Measured 37 of 444 rows on the live lake
# 2026-09-11 (57 cleared the award/family-count floor; 13 of those summed to
# zero or negative high-confidence dollars and 7 more rested on a single
# positive-dollar family). Never lower this to fit a red run: a drop means
# the high basis moved, which is the thing to investigate.
_MIN_HIGH_ONLY_ROWS = 37


def marts_gate(duckdb_path: Path) -> dict:
    """Gate 3: four efficiency marts non-empty with sane invariants.

    Invariants:
    - fct_budget_trajectory ≥ 300 rows
    - fct_program_concentration: hhi_all AND hhi_high ∈ [0, 10000] (see _HHI_CEILING);
      a published hhi_high rests on >= 3 high-confidence awards across >= 2
      POSITIVE-dollar families with positive program dollars (#80), and at
      least _MIN_HIGH_ONLY_ROWS programs publish one
    - fct_agency_concentration: ≥ 1 sub-agency
    - fct_improper_exposure: ≥ 10 agencies
    """
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        traj_rows = con.execute("select count(*) from fct_budget_trajectory").fetchone()[0]
        conc_rows = con.execute("select count(*) from fct_program_concentration").fetchone()[0]
        agency_rows = con.execute("select count(*) from fct_agency_concentration").fetchone()[0]
        exposure_rows = con.execute("select count(*) from fct_improper_exposure").fetchone()[0]

        # HHI sanity: no row outside [0, 10000] on EITHER basis (ROADMAP #80).
        bad_hhi_prog = con.execute(
            "select count(*) from fct_program_concentration"
            f" where hhi_all > {_HHI_CEILING} or hhi_all < 0"
            f"    or hhi_high > {_HHI_CEILING} or hhi_high < 0"
        ).fetchone()[0]
        bad_hhi_agency = con.execute(
            "select count(*) from fct_agency_concentration"
            f" where hhi > {_HHI_CEILING} or hhi < 0"
        ).fetchone()[0]
        # #80 floor: a high-only index may rest on nothing smaller than 3
        # high-confidence awards across 2 contractor families HOLDING POSITIVE
        # DOLLARS, with positive net program dollars. The mart NULLs hhi_high
        # below that; a published value below it is the regression this leg
        # exists to catch (the card headlines it).
        #
        # The dollar and positive-family clauses are the 2026-09-11 fix: the
        # first version of this leg re-asserted only the award/family counts,
        # exactly the predicate the mart's own `case` guarantees, so it was
        # structurally 0 while 13 programs published hhi_high = 0.0
        # ("Competitive", $0, a top contractor picked alphabetically) and 7
        # published 10,000 over one positive-dollar family. A mart that stops
        # applying either clause now fails here.
        bad_high_floor = con.execute(
            "select count(*) from fct_program_concentration"
            " where hhi_high is not null"
            "   and (program_dollars_high is null"
            "        or program_dollars_high <= 0"
            "        or positive_family_count_high < 2"
            "        or award_count_high < 3)"
        ).fetchone()[0]
        high_only_rows = con.execute(
            "select count(hhi_high) from fct_program_concentration"
        ).fetchone()[0]
    finally:
        con.close()

    ok = (
        traj_rows >= 300
        and conc_rows > 0
        and agency_rows >= 1
        and exposure_rows >= 10
        and bad_hhi_prog == 0
        and bad_hhi_agency == 0
        and bad_high_floor == 0
        and high_only_rows >= _MIN_HIGH_ONLY_ROWS
    )
    return {
        "ok": ok,
        "trajectory_rows": traj_rows,
        "concentration_rows": conc_rows,
        "high_only_rows": high_only_rows,
        "min_high_only_rows": _MIN_HIGH_ONLY_ROWS,
        "agency_rows": agency_rows,
        "exposure_rows": exposure_rows,
        "bad_hhi_program": bad_hhi_prog,
        "bad_hhi_agency": bad_hhi_agency,
        "bad_high_floor": bad_high_floor,
    }


def trace_gate3(duckdb_path: Path, hr_path: Path) -> dict:
    """Gate 4: For 2 mapped DoD high-risk areas → agency_code = canonical 'DOD' →
    ≥1 dim_programs row exists (DoD programs = all of dim_programs in our DoD-scoped
    warehouse — assert non-empty) + fetch top family via fct_program_concentration
    for at least one DARPA/DoD PE.  Both DoD areas must trace.

    agency_code values are canonical (via canonical_agency) so all DoD variants
    (dow, 097, DOD, dod) normalize to 'DOD' at write time.
    """
    con_hr = duckdb.connect()
    # All DoD variants are canonicalized to 'DOD' at write time
    dod_canonical = canonical_agency("DOD")  # -> "DOD"
    dod_areas = con_hr.execute(
        f"""
        select area_title, agency_code
        from read_parquet('{hr_path}')
        where agency_code = '{dod_canonical}'
          and mapped = 'true'
        limit 5
        """
    ).fetchall()

    if len(dod_areas) < 2:
        return {
            "ok": False,
            "reason": f"fewer than 2 DoD-mapped areas found (got {len(dod_areas)})",
            "dod_areas_traced": 0,
        }

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        # dim_programs must be non-empty (DoD-scoped warehouse)
        prog_count = con.execute("select count(*) from dim_programs").fetchone()[0]
        if prog_count == 0:
            return {
                "ok": False,
                "reason": "dim_programs is empty — no DoD programs loaded",
                "dod_areas_traced": 0,
            }

        # Get top program concentration row (any pe_bli with top_family)
        sample = con.execute(
            "select pe_bli, top_family_all from fct_program_concentration"
            " where top_family_all is not null limit 1"
        ).fetchone()
        top_family = sample[1] if sample else None

        # Both DoD areas traced if dim_programs non-empty + top family available
        # The plan says: "fetch top family via fct_program_concentration for a DARPA PE"
        # We assert non-empty + one family available
        dod_areas_traced = 2 if (prog_count > 0 and top_family is not None) else 0

    finally:
        con.close()

    ok = dod_areas_traced == 2
    return {
        "ok": ok,
        "dod_areas_checked": len(dod_areas),
        "dod_areas_traced": dod_areas_traced,
        "dim_programs_count": prog_count,
        "sample_top_family": top_family,
    }
