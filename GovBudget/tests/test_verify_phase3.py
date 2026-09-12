"""TDD tests for verify_phase3 gates.

Each gate is tested in isolation with minimal fixture data.
"""
import re
from pathlib import Path

import duckdb
import pytest

from govbudget import verify_phase3
from govbudget.verify_phase3 import (
    _MIN_HIGH_ONLY_ROWS,
    ingest_gate,
    linkage_gate,
    marts_gate,
    trace_gate3,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def write_parquet(path: Path, sql: str, cols: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    duckdb.sql(
        f"copy (select * from (values {sql}) t({cols}))"
        f" to '{path}' (format parquet)"
    )


def make_oversight_fixtures(
    tmp_path: Path,
    *,
    n_programs: int = 55,
    n_areas: int = 35,
    mapped_count: int = 30,
) -> tuple[Path, Path]:
    """Write minimal improper_payments and high_risk parquet fixtures.

    Mirrors the typed ingestion schema (backlog #11): fiscal_year INTEGER,
    rate/amount columns DOUBLE, mapped BOOLEAN.
    """
    ip_path = tmp_path / "improper_payments.parquet"
    hr_path = tmp_path / "high_risk.parquet"

    # Build n_programs unique programs, each with ≥1 FY row
    ip_rows = []
    for i in range(n_programs):
        ip_rows.append(
            f"('Program{i}','Agency{i % 5}','ag{i % 5}',2023,"
            f"5.0,1000000.0,0.0,20000000.0,'https://paymentaccuracy.gov/program/p{i}')"
        )
    ip_sql = ",".join(ip_rows)
    write_parquet(
        ip_path, ip_sql,
        "program, agency_name, agency_code, fiscal_year, rate_pct, derived_improper_amount_usd, unknown_rate_pct, outlays_usd, source_url",
    )

    # Build n_areas high-risk areas; mapped_count have agency_code, rest don't
    hr_rows = []
    for i in range(n_areas):
        if i < mapped_count:
            code = f"AGENCY{i % 5}"
            mapped = "true"
        else:
            code = ""
            mapped = "false"
        hr_rows.append(
            f"('Area{i}','https://gao.gov/area{i}','{code}',{mapped},"
            f"'notes','https://www.gao.gov/high-risk-list')"
        )
    hr_sql = ",".join(hr_rows)
    write_parquet(
        hr_path, hr_sql,
        "area_title, area_url, agency_code, mapped, notes, source_url",
    )

    return ip_path, hr_path


def make_duckdb_with_marts(tmp_path: Path, *, n_high_only: int = 40) -> Path:
    """Build a minimal DuckDB with the four efficiency marts populated.

    `n_high_only` is how many concentration rows publish an hhi_high. The
    default clears verify_phase3._MIN_HIGH_ONLY_ROWS; pass fewer to exercise
    the #80 collapse floor.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db_path))

    # fct_budget_trajectory: ≥300 rows required
    rows = [
        f"('PE{i:04d}','ORG{i % 10}',{i * 100.0},{i * 110.0},{i * 120.0},"
        f"{i * 10.0},{9.09})"
        for i in range(1, 401)
    ]
    con.execute(
        "create table fct_budget_trajectory as select * from (values "
        + ",".join(rows)
        + ") t(pe_bli, organization, fy2024_actuals, fy2025_total, fy2026_total,"
        "  fy2526_change, fy2526_pct_change)"
    )

    # fct_program_concentration: valid HHI rows, both bases (ROADMAP #80).
    # The first n_high_only rows clear the high-only floor (>=3 high awards
    # across >=2 POSITIVE-dollar families, positive high dollars); then one
    # row with high links below the floor (hhi_high NULL, dollars published)
    # and one with no high links at all (counts 0, high dollars NULL).
    conc_rows = [
        f"('06011{i:02d}E', 2500.0, 'ACME CORP', 3, 4, 1000000.0,"
        f" 2500.0, 'ACME CORP', 3, 3, 4, 1000000.0)"
        for i in range(n_high_only)
    ]
    conc_rows += [
        "('0601901E', 5000.0, 'MEGA CORP', 2, 3, 2000000.0, NULL, NULL, 1, 1, 2, 500000.0)",
        "('0601902E', 10000.0,'SOLO CORP', 1, 1, 500000.0, NULL, NULL, 0, 0, 0, NULL)",
    ]
    con.execute(
        "create table fct_program_concentration as select * from (values "
        + ",".join(conc_rows)
        + ") t(pe_bli, hhi_all, top_family_all, family_count_all, award_count_all,"
        "     program_dollars_all, hhi_high, top_family_high, family_count_high,"
        "     positive_family_count_high, award_count_high, program_dollars_high)"
    )

    # fct_agency_concentration: ≥10 sub-agencies required
    agency_rows = [
        f"('Agency{i}', {1000.0 + i * 100}, {i * 50000.0}, {3 + i})"
        for i in range(1, 15)
    ]
    con.execute(
        "create table fct_agency_concentration as select * from (values "
        + ",".join(agency_rows)
        + ") t(awarding_sub_agency_name, hhi, total_obligation, family_count)"
    )

    # fct_improper_exposure: ≥10 agencies required
    exposure_rows = [
        f"('ag{i}', {2 + i}, {i * 1e9}, {5.0 + i * 0.5}, 2023)"
        for i in range(1, 15)
    ]
    con.execute(
        "create table fct_improper_exposure as select * from (values "
        + ",".join(exposure_rows)
        + ") t(agency_code, program_count, derived_improper_amount_usd, weighted_rate_pct, latest_fiscal_year)"
    )

    # dim_programs: some DoD programs
    con.execute(
        """
        create table dim_programs as select * from (values
          ('0601100E', 'DARPA', 'rdte', 3, 280.0, true, 'Defense Research'),
          ('0601101E', 'DARPA', 'rdte', 2, 140.0, true, 'Applied Research'),
          ('0601901E', 'ARMY', 'rdte', 5, 500.0, true, 'Army Research')
        ) t(pe_bli, org, exhibit_family, project_count, fy2024_actual_millions,
            fully_reconciled, title)
        """
    )

    con.close()
    return db_path


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class TestIngestGate:
    def test_pass(self, tmp_path):
        ip_path, hr_path = make_oversight_fixtures(tmp_path)
        result = ingest_gate(ip_path, hr_path)
        assert result["ok"] is True
        assert result["program_count"] >= 50
        assert result["area_count"] >= 30

    def test_fail_too_few_programs(self, tmp_path):
        ip_path, hr_path = make_oversight_fixtures(tmp_path, n_programs=40)
        result = ingest_gate(ip_path, hr_path)
        assert result["ok"] is False

    def test_fail_too_few_areas(self, tmp_path):
        ip_path, hr_path = make_oversight_fixtures(tmp_path, n_areas=25)
        result = ingest_gate(ip_path, hr_path)
        assert result["ok"] is False


class TestLinkageGate:
    def test_pass(self, tmp_path):
        _, hr_path = make_oversight_fixtures(
            tmp_path, n_areas=35, mapped_count=30
        )  # 30/35 ≈ 85.7% > 80%
        result = linkage_gate(hr_path)
        assert result["ok"] is True
        assert result["mapped_pct"] >= 80.0
        assert "unmapped_count" in result

    def test_fail_low_mapped(self, tmp_path):
        _, hr_path = make_oversight_fixtures(
            tmp_path, n_areas=35, mapped_count=20
        )  # 20/35 ≈ 57.1% < 80%
        result = linkage_gate(hr_path)
        assert result["ok"] is False
        assert result["unmapped_count"] == 15


class TestMartsGate:
    def test_pass(self, tmp_path):
        db_path = make_duckdb_with_marts(tmp_path)
        result = marts_gate(db_path)
        assert result["ok"] is True, result

    def test_fail_empty_trajectory(self, tmp_path):
        db_path = tmp_path / "t.duckdb"
        con = duckdb.connect(str(db_path))
        con.execute("create table fct_budget_trajectory (pe_bli varchar)")
        con.execute(
            """
            create table fct_program_concentration as select * from (values
              ('0601101E', 2500.0, 'ACME', 1, 1, 1e6, NULL, NULL, 0, 0, 0, NULL)
            ) t(pe_bli, hhi_all, top_family_all, family_count_all, award_count_all, program_dollars_all,
                hhi_high, top_family_high, family_count_high, positive_family_count_high,
                award_count_high, program_dollars_high)
            """
        )
        con.execute(
            "create table fct_agency_concentration (awarding_sub_agency_name varchar,"
            " hhi double, total_obligation double, family_count integer)"
        )
        con.execute(
            "create table fct_improper_exposure (agency_code varchar,"
            " program_count integer, derived_improper_amount_usd double,"
            " weighted_rate_pct double, latest_fiscal_year integer)"
        )
        con.close()
        result = marts_gate(db_path)
        assert result["ok"] is False

    def test_fail_invalid_hhi(self, tmp_path):
        """HHI > 10000 should fail."""
        db_path = tmp_path / "t.duckdb"
        con = duckdb.connect(str(db_path))
        # Minimal trajectory rows
        rows = [f"('PE{i}','ORG',{i},{i},{i},{0},{0})" for i in range(1, 310)]
        con.execute(
            "create table fct_budget_trajectory as select * from (values "
            + ",".join(rows)
            + ") t(pe_bli,organization,fy2024_actuals,fy2025_total,fy2026_total,"
            "fy2526_change,fy2526_pct_change)"
        )
        con.execute(
            """
            create table fct_program_concentration as select * from (values
              ('0601101E', 99999.0, 'ACME', 1, 1, 1e6, NULL, NULL, 0, 0, 0, NULL)
            ) t(pe_bli, hhi_all, top_family_all, family_count_all, award_count_all, program_dollars_all,
                hhi_high, top_family_high, family_count_high, positive_family_count_high,
                award_count_high, program_dollars_high)
            """
        )
        con.execute(
            "create table fct_agency_concentration (awarding_sub_agency_name varchar,"
            " hhi double, total_obligation double, family_count integer)"
        )
        con.execute(
            "create table fct_improper_exposure (agency_code varchar,"
            " program_count integer, derived_improper_amount_usd double,"
            " weighted_rate_pct double, latest_fiscal_year integer)"
        )
        con.close()
        result = marts_gate(db_path)
        assert result["ok"] is False

    def test_fail_high_only_index_below_floor(self, tmp_path):
        """ROADMAP #80: a published hhi_high resting on < 3 high-confidence
        awards or < 2 families is the regression this leg exists to catch."""
        db_path = self._marts_db(
            tmp_path,
            "('0601101E', 2500.0, 'ACME', 3, 4, 1e6, 2500.0, 'ACME', 1, 1, 2, 1e6)",
        )
        result = marts_gate(db_path)
        assert result["ok"] is False, result
        assert result["bad_high_floor"] == 1

    def test_fail_high_only_index_over_nonpositive_dollars(self, tmp_path):
        """#80 fix round 1: the counts alone are the predicate the mart
        already applies, so the leg has to assert something the mart cannot
        satisfy by construction. 13 programs shipped hhi_high = 0.0 over $0
        of high-confidence obligations and one over -$2.3M; each headlined
        "Competitive" on the card with a top contractor chosen alphabetically.
        """
        zero = self._marts_db(
            tmp_path / "zero",
            "('0601101E', 2500.0, 'ACME', 4, 4, 1e6, 0.0, 'ACME', 4, 2, 4, 0.0)",
        )
        result = marts_gate(zero)
        assert result["bad_high_floor"] == 1
        assert result["ok"] is False, result

        negative = self._marts_db(
            tmp_path / "neg",
            "('0601101E', 2500.0, 'ACME', 7, 17, 1e6, 0.0, 'ACME', 7, 2, 17, -2328281.28)",
        )
        assert marts_gate(negative)["bad_high_floor"] == 1

    def test_fail_high_only_index_on_one_positive_family(self, tmp_path):
        """#80 fix round 1: family_count_high counts LINKED families, so a
        family holding zero positive dollars satisfied the old 2-family
        floor — 7 programs published 10,000 (one family holds 100% of the
        positive dollars) next to a card reading "2-4 contractor families".
        """
        db_path = self._marts_db(
            tmp_path,
            "('0603882C', 10000.0, 'BOEING', 2, 4, 7.45e9, 10000.0, 'BOEING', 2, 1, 4, 7.45e9)",
        )
        result = marts_gate(db_path)
        assert result["bad_high_floor"] == 1
        assert result["ok"] is False, result

    def test_fail_when_the_high_basis_collapses(self, tmp_path):
        """#80 fix round 1: bad_high_floor is structurally 0 against any mart
        built by fct_program_concentration.sql, so a high basis that stopped
        matching entirely would leave gate 3 green while every card silently
        lost its index. high_only_rows carries a dated do-not-lower floor."""
        collapsed = make_duckdb_with_marts(tmp_path / "collapsed", n_high_only=0)
        result = marts_gate(collapsed)
        assert result["high_only_rows"] == 0
        assert result["bad_high_floor"] == 0, "nothing else may be what fails"
        assert result["bad_hhi_program"] == 0
        assert result["ok"] is False, result

        healthy = make_duckdb_with_marts(tmp_path / "healthy")
        healthy_result = marts_gate(healthy)
        assert healthy_result["high_only_rows"] >= healthy_result["min_high_only_rows"]
        assert healthy_result["ok"] is True, healthy_result

    def test_float_noise_at_the_ceiling_is_not_a_breach(self, tmp_path):
        """ROADMAP #80 / 2026-09-10: DuckDB's parallel `sum(share*share)` puts a
        single-positive-family program on 10000.0 or 10000.000000000004 run to
        run (13/8/8/10/10/13 breaches in six consecutive counts over the live
        lake). The ceiling absorbs that and nothing larger."""
        ok_db = self._marts_db(
            tmp_path / "ok",
            "('0601101E', 10000.000000000004, 'ACME', 2, 3, 1e6,"
            " 10000.000000000004, 'ACME', 2, 2, 3, 1e6)",
        )
        assert marts_gate(ok_db)["bad_hhi_program"] == 0
        assert marts_gate(ok_db)["ok"] is True

        bad_db = self._marts_db(
            tmp_path / "bad",
            "('0601101E', 10000.01, 'ACME', 2, 3, 1e6, NULL, NULL, 0, 0, 0, NULL)",
        )
        result = marts_gate(bad_db)
        assert result["bad_hhi_program"] == 1
        assert result["ok"] is False

    @staticmethod
    def _marts_db(tmp_path, conc_row: str, *, n_clean: int = 40):
        """A marts warehouse that passes every leg except what conc_row breaks.

        `n_clean` floor-clearing rows sit alongside conc_row so the #80
        collapse floor (_MIN_HIGH_ONLY_ROWS) is not what fails the gate —
        each of these tests must fail for exactly the reason it names.
        """
        tmp_path.mkdir(parents=True, exist_ok=True)
        db_path = tmp_path / "t.duckdb"
        con = duckdb.connect(str(db_path))
        rows = [f"('PE{i}','ORG',{i},{i},{i},{0},{0})" for i in range(1, 310)]
        con.execute(
            "create table fct_budget_trajectory as select * from (values "
            + ",".join(rows)
            + ") t(pe_bli,organization,fy2024_actuals,fy2025_total,fy2026_total,"
            "fy2526_change,fy2526_pct_change)"
        )
        clean = [
            f"('CLEAN{i:03d}', 2500.0, 'ACME', 3, 4, 1e6, 2500.0, 'ACME', 3, 3, 4, 1e6)"
            for i in range(n_clean)
        ]
        con.execute(
            "create table fct_program_concentration as select * from (values "
            + ",".join([conc_row, *clean])
            + ") t(pe_bli, hhi_all, top_family_all, family_count_all, award_count_all,"
            "     program_dollars_all, hhi_high, top_family_high, family_count_high,"
            "     positive_family_count_high, award_count_high, program_dollars_high)"
        )
        agency_rows = [f"('Agency{i}', {1000.0 + i * 100}, {i * 50000.0}, {3 + i})" for i in range(1, 15)]
        con.execute(
            "create table fct_agency_concentration as select * from (values "
            + ",".join(agency_rows)
            + ") t(awarding_sub_agency_name, hhi, total_obligation, family_count)"
        )
        exposure_rows = [f"('ag{i}', {2 + i}, {i * 1e9}, {5.0 + i * 0.5}, 2023)" for i in range(1, 15)]
        con.execute(
            "create table fct_improper_exposure as select * from (values "
            + ",".join(exposure_rows)
            + ") t(agency_code, program_count, derived_improper_amount_usd, weighted_rate_pct, latest_fiscal_year)"
        )
        con.close()
        return db_path


class TestTraceGate3:
    def test_pass(self, tmp_path):
        """Two DoD high-risk areas with DoD programs present → PASS."""
        db_path = make_duckdb_with_marts(tmp_path)
        _, hr_path = make_oversight_fixtures(tmp_path)

        # Add DOD-mapped areas to the fixture (mapped is BOOLEAN)
        hr_path.unlink(missing_ok=True)
        write_parquet(
            hr_path,
            "('DOD Weapon Systems','https://gao.gov/area1','DOD',true,'dod notes','https://www.gao.gov/high-risk-list'),"
            "('DOD Financial Mgmt','https://gao.gov/area2','DOD',true,'dod notes','https://www.gao.gov/high-risk-list'),"
            "('Other HHS','https://gao.gov/area3','HHS',true,'hhs notes','https://www.gao.gov/high-risk-list')",
            "area_title, area_url, agency_code, mapped, notes, source_url",
        )
        result = trace_gate3(db_path, hr_path)
        assert result["ok"] is True, result
        assert result["dod_areas_traced"] == 2

    def test_fail_no_programs(self, tmp_path):
        """DB has dim_programs empty → should fail trace."""
        db_path = tmp_path / "t.duckdb"
        con = duckdb.connect(str(db_path))
        con.execute(
            "create table dim_programs (pe_bli varchar, org varchar,"
            " exhibit_family varchar, project_count integer,"
            " fy2024_actual_millions double, fully_reconciled boolean, title varchar)"
        )
        con.execute(
            "create table fct_program_concentration "
            "(pe_bli varchar, hhi_all double, top_family_all varchar, family_count_all integer,"
            " award_count_all integer, program_dollars_all double, hhi_high double,"
            " top_family_high varchar, family_count_high integer,"
            " positive_family_count_high integer, award_count_high integer,"
            " program_dollars_high double)"
        )
        con.close()
        hr_path = tmp_path / "hr.parquet"
        write_parquet(
            hr_path,
            "('DOD Weapon Systems','https://gao.gov/area1','DOD',true,'dod notes','https://www.gao.gov/high-risk-list')",
            "area_title, area_url, agency_code, mapped, notes, source_url",
        )
        result = trace_gate3(db_path, hr_path)
        assert result["ok"] is False


class TestHighOnlyRowsFloor:
    """_MIN_HIGH_ONLY_ROWS is a floor: it may be raised, never lowered.

    Every marts_gate probe above builds its fixture from the constant
    (`_marts_db(n_clean=40)` exists so the floor is never what fails those
    tests), so lowering it to fit a red run would leave this suite green —
    the gap #80 fix round 3 (2026-09-11, finding 3) found in the site's twin
    floor, MIN_RECONCILABLE_HHI_DESTINATIONS. These two fail on a LOWER value
    and on a deleted rule.
    """

    def test_the_floor_may_only_be_raised(self):
        # MEASURED 2026-09-11 on the live lake: 37 of 444 programs publish an
        # hhi_high under the post-#80 floor. Raise this when a build measures
        # more; a number that moves down to fit a run is not a floor.
        assert _MIN_HIGH_ONLY_ROWS >= 37

    def test_the_do_not_lower_rule_is_stated_and_dated_beside_the_constant(self):
        src = Path(verify_phase3.__file__).read_text(encoding="utf-8")
        decl = src.index("_MIN_HIGH_ONLY_ROWS = ")
        assert src[decl:].startswith(f"_MIN_HIGH_ONLY_ROWS = {_MIN_HIGH_ONLY_ROWS}\n")
        # the comment block immediately above the constant
        note = src[:decl].rsplit("\n\n", 1)[-1]
        assert re.search(r"never lower", note, re.I), note
        assert re.search(r"\b20\d\d-\d\d-\d\d\b", note), note
