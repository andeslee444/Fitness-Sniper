"""ROADMAP #133 — the fiscal-year move rule, in dbt staging (2026-09-25).

A USAspending source correction can MOVE a transaction into another fiscal
year's archive. A refreshed archive then carries the transaction's key once
in its new year while the older archive still carries the pre-correction
copy, and `unique_fct_award_transactions_transaction_key` fails. On
2026-09-24 that happened to 81 rows and `scripts/reconcile_award_moves.py`
retired them by hand (report first, then rewrite the parquet).

The owner delegated the rule to dbt (2026-09-25): a key present in more than
one fiscal-year archive keeps its STRICTLY NEWER copy by last_modified_date
only when there are exactly two copies in two DIFFERENT fiscal years — the
same acceptance rule the script applies. Anything else (two copies in one
fiscal year, equal dates, three or more copies, a copy with no parseable
date) is ambiguous: nothing is retired and the build fails, on the unique
test exactly as before and on assert_award_duplicates_unambiguous, which
names each copy and why. The guard is never weakened.

The first two tests build the fixture lake with dbt (the real models, real
tests); the rest run the committed audit model's own SQL against a
throwaway DuckDB, one duplicate shape at a time.
"""
import os
import subprocess
from pathlib import Path

import duckdb
import pytest

from test_dbt_build import CONTRACT_COLS, make_lake, write_parquet

ROOT = Path(__file__).resolve().parents[1]

ASSISTANCE_COLS = (
    "assistance_transaction_unique_key, action_date, federal_action_obligation, "
    "recipient_uei, recipient_name, recipient_parent_uei, recipient_parent_name, "
    "awarding_agency_name, awarding_sub_agency_name, "
    "primary_place_of_performance_state_name, "
    "prime_award_transaction_place_of_performance_cd_current, "
    "usaspending_permalink, assistance_award_unique_key, last_modified_date"
)


def _contract(key, action_date, obligation, modified):
    """One contracts-archive row (CONTRACT_COLS order) for a DoD award."""
    return (
        f"('{key}','{action_date}','{obligation}','UEI9','MOVER INC','PUEI9',"
        f"'MOVER PARENT','DoD','Navy','336411','1510','VA','VA-02',"
        f"'N0002425C9{key[-3:]}','https://www.usaspending.gov/award/CONT_AWD_{key}',"
        f"'CAUK_{key}','NAVSEA HQ','FULL AND OPEN COMPETITION','2',"
        + ("null" if modified is None else f"'{modified}'")
        + ")"
    )


def _assistance(key, action_date, obligation, modified):
    return (
        f"('{key}','{action_date}','{obligation}','UEI8','GRANTEE','PUEI8',"
        f"'GRANTEE PARENT','DoD','Army','VIRGINIA','VA-02',"
        f"'https://www.usaspending.gov/award/ASST_NON_{key}','ASUK_{key}',"
        + ("null" if modified is None else f"'{modified}'")
        + ")"
    )


def _write_contracts(data_dir: Path, fy: int, rows: list[str], part="part"):
    d = data_dir / f"parquet/contracts/fy={fy}"
    d.mkdir(parents=True, exist_ok=True)
    duckdb.sql(
        f"copy (select * from (values {', '.join(rows)}) t({CONTRACT_COLS}))"
        f" to '{d}/{part}.parquet' (format parquet)"
    )


def _write_assistance(data_dir: Path, fy: int, rows: list[str]):
    write_parquet(
        data_dir / f"parquet/assistance/fy={fy}",
        f"select * from (values {', '.join(rows)}) t({ASSISTANCE_COLS})",
    )


def _dbt_build(data_dir: Path) -> tuple[subprocess.CompletedProcess, Path]:
    (data_dir / "duckdb").mkdir(exist_ok=True)
    db = data_dir / "duckdb" / "test.duckdb"
    env = {**os.environ, "GOVBUDGET_DATA": str(data_dir), "GOVBUDGET_DUCKDB": str(db)}
    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    return result, db


def test_a_fresh_unreconciled_lake_builds_and_retires_exactly_the_moved_copies(tmp_path):
    """The 2026-09-24 shape, before anyone ran the reconcile script: a
    refreshed FY2026 contracts archive carries MOVED001 and MOVED002 again,
    source-corrected (newer last_modified_date, new obligation), while the
    FY2025 and FY2024 archives still carry the old copies; the assistance
    side has one such move from FY2024 to FY2025. The build must succeed,
    keep only the refreshed copies, and list every retired copy in
    audit_award_fy_moves — and nothing else."""
    make_lake(tmp_path)
    _write_contracts(tmp_path, 2024, [
        _contract("MOVED002", "2024-06-01", "500", "2025-01-01 00:00:00+00"),
        _contract("STAYS024", "2024-06-02", "11", "2025-01-01 00:00:00+00"),
    ])
    _write_contracts(tmp_path, 2025, [
        _contract("MOVED001", "2025-03-01", "100", "2025-04-01 09:00:00+00"),
        _contract("STAYS025", "2025-03-02", "13", "2025-04-01 00:00:00+00"),
    ])
    _write_contracts(tmp_path, 2026, [
        _contract("MOVED001", "2025-10-02", "120", "2026-08-02 00:00:00+00"),
        _contract("MOVED002", "2025-10-03", "450", "2026-08-02 00:00:00+00"),
        _contract("STAYS026", "2025-10-04", "17", "2026-08-02 00:00:00+00"),
    ])
    _write_assistance(tmp_path, 2024, [
        _assistance("AMOVED01", "2024-02-01", "700", "2024-03-01 00:00:00+00"),
    ])
    _write_assistance(tmp_path, 2025, [
        _assistance("AMOVED01", "2024-10-05", "650", "2026-08-01 12:00:00.5+00"),
    ])

    result, db = _dbt_build(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    # The retired count is printed by the build itself (a WARN-severity
    # singular test returns one row per retired copy).
    assert "warn_award_fy_moves_retired" in result.stdout
    assert "Got 3 results" in result.stdout, result.stdout

    con = duckdb.connect(str(db), read_only=True)
    try:
        kept = con.sql(
            "select transaction_key, award_type, fiscal_year, obligation"
            " from fct_award_transactions"
            " where transaction_key in ('MOVED001','MOVED002','AMOVED01')"
            " order by transaction_key"
        ).fetchall()
        assert kept == [
            ("AMOVED01", "assistance", 2025, 650.0),
            ("MOVED001", "contract", 2026, 120.0),
            ("MOVED002", "contract", 2026, 450.0),
        ], kept
        # Nothing that was not a proven move is touched: 4 original fixture
        # rows + 3 STAYS + the 3 surviving refreshed copies.
        assert con.sql("select count(*) from fct_award_transactions").fetchone()[0] == 10

        moves = con.sql(
            "select award_type, transaction_key, kept_fiscal_year,"
            " kept_last_modified_date, retired_fiscal_year,"
            " retired_last_modified_date,"
            " regexp_extract(kept_file, 'fy=[0-9]+/[^/]+$'),"
            " regexp_extract(retired_file, 'fy=[0-9]+/[^/]+$')"
            " from audit_award_fy_moves order by transaction_key"
        ).fetchall()
        assert moves == [
            ("assistance", "AMOVED01", 2025, "2026-08-01 12:00:00.5+00", 2024,
             "2024-03-01 00:00:00+00", "fy=2025/part.parquet", "fy=2024/part.parquet"),
            ("contract", "MOVED001", 2026, "2026-08-02 00:00:00+00", 2025,
             "2025-04-01 09:00:00+00", "fy=2026/part.parquet", "fy=2025/part.parquet"),
            ("contract", "MOVED002", 2026, "2026-08-02 00:00:00+00", 2024,
             "2025-01-01 00:00:00+00", "fy=2026/part.parquet", "fy=2024/part.parquet"),
        ], moves

        # The flowdown staging reads the same contracts archive directly; a
        # retired copy must not reach it either (its conservation assertion,
        # assert_flow_competed_classes_sum, ran green in the build above).
        flow_2025 = con.sql(
            "select sum(obligation) from stg_flow_contracts where fiscal_year = 2025"
        ).fetchone()[0]
        assert flow_2025 == 13.0, flow_2025
    finally:
        con.close()


def test_an_ambiguous_duplicate_fails_the_build_loudly(tmp_path):
    """Every shape the rule refuses, at once. Nothing may be retired, the
    unique guard must fail exactly as it did before the rule existed, and
    assert_award_duplicates_unambiguous must name all nine copies."""
    make_lake(tmp_path)
    _write_contracts(tmp_path, 2024, [
        _contract("THREE001", "2024-01-01", "1", "2024-02-01 00:00:00+00"),
    ])
    _write_contracts(tmp_path, 2025, [
        # two copies in ONE fiscal year (two part files)
        _contract("SAMEFY01", "2025-01-01", "5", "2025-02-01 00:00:00+00"),
        # equal source revision time in two fiscal years
        _contract("TIEDATE1", "2025-01-02", "6", "2026-01-01 00:00:00+00"),
        # three copies
        _contract("THREE001", "2025-01-03", "2", "2025-02-01 00:00:00+00"),
        # one copy with no source revision time at all
        _contract("NODATE01", "2025-01-04", "7", None),
    ])
    _write_contracts(tmp_path, 2025, [
        _contract("SAMEFY01", "2025-01-05", "8", "2026-02-01 00:00:00+00"),
    ], part="part-2")
    _write_contracts(tmp_path, 2026, [
        _contract("TIEDATE1", "2025-10-01", "9", "2026-01-01 00:00:00+00"),
        _contract("THREE001", "2025-10-02", "3", "2026-08-02 00:00:00+00"),
        _contract("NODATE01", "2025-10-03", "4", "2026-08-02 00:00:00+00"),
    ])

    result, db = _dbt_build(tmp_path)
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    assert "FAIL 4 unique_fct_award_transactions_transaction_key" in out, out
    assert "FAIL 9 assert_award_duplicates_unambiguous" in out, out

    con = duckdb.connect(str(db), read_only=True)
    try:
        # the audit model built; it retired nothing
        assert con.sql("select count(*) from audit_award_fy_moves").fetchone()[0] == 0
        reasons = con.sql(
            "select transaction_key, count(*), min(ambiguity)"
            " from audit_award_duplicate_copies group by 1 order by 1"
        ).fetchall()
        assert reasons == [
            ("NODATE01", 2, "a copy has no parseable last_modified_date"),
            ("SAMEFY01", 2, "both copies sit in one fiscal year"),
            ("THREE001", 3, "more than two copies"),
            ("TIEDATE1", 2, "both copies carry the same last_modified_date"),
        ], reasons
    finally:
        con.close()


# ── the committed audit model's own SQL, one shape at a time ─────────────────

def _audit_sql() -> str:
    """dbt/models/audit/audit_award_duplicate_copies.sql with its config()
    and source() macros replaced by plain tables — the SQL dbt builds, not a
    restatement of it."""
    sql = (ROOT / "dbt" / "models" / "audit" / "audit_award_duplicate_copies.sql").read_text()
    sql = sql.replace("{{ config(materialized='table') }}", "")
    sql = sql.replace("{{ source('lake', 'contracts') }}", "contracts")
    sql = sql.replace("{{ source('lake', 'assistance') }}", "assistance")
    assert "{{" not in sql, "unsubstituted macro left in audit_award_duplicate_copies.sql"
    return sql


def _classify(copies: list[tuple]) -> list[tuple]:
    """copies: (key, fy, last_modified_date, filename) contract rows."""
    con = duckdb.connect()
    con.execute(
        "create table contracts (contract_transaction_unique_key varchar,"
        " fy varchar, last_modified_date varchar, filename varchar)"
    )
    con.execute(
        "create table assistance (assistance_transaction_unique_key varchar,"
        " fy varchar, last_modified_date varchar, filename varchar)"
    )
    if copies:
        con.executemany("insert into contracts values (?,?,?,?)", copies)
    con.execute("insert into contracts values ('LONE', '2026', '2026-01-01', 'f')")
    rows = con.execute(
        "select transaction_key, fiscal_year, resolution, ambiguity from ("
        + _audit_sql() + ") order by transaction_key, fiscal_year"
    ).fetchall()
    con.close()
    return rows


def test_the_newer_copy_is_kept_whichever_year_it_sits_in():
    # the refreshed copy need not be the later fiscal year: the rule is the
    # source revision time, as in reconcile_award_moves.py
    assert _classify([
        ("K", "2025", "2026-08-02 00:00:00+00", "a"),
        ("K", "2026", "2025-01-01 00:00:00+00", "b"),
    ]) == [("K", 2025, "keep", None), ("K", 2026, "retire", None)]


def test_a_key_seen_once_is_not_in_the_audit():
    assert _classify([]) == []


@pytest.mark.parametrize("copies, reason", [
    ([("K", "2025", "2025-01-01", "a"), ("K", "2025", "2026-01-01", "b")],
     "both copies sit in one fiscal year"),
    ([("K", "2025", "2026-01-01 00:00:00+00", "a"),
      ("K", "2026", "2026-01-01 00:00:00+00", "b")],
     "both copies carry the same last_modified_date"),
    ([("K", "2024", "2024-01-01", "a"), ("K", "2025", "2025-01-01", "b"),
      ("K", "2026", "2026-01-01", "c")],
     "more than two copies"),
    ([("K", "2025", None, "a"), ("K", "2026", "2026-01-01", "b")],
     "a copy has no parseable last_modified_date"),
    ([("K", "2025", "not a date", "a"), ("K", "2026", "2026-01-01", "b")],
     "a copy has no parseable last_modified_date"),
])
def test_every_other_duplicate_is_ambiguous_and_nothing_is_retired(copies, reason):
    rows = _classify(copies)
    assert {r[2] for r in rows} == {"ambiguous"}, rows
    assert {r[3] for r in rows} == {reason}, rows
    assert len(rows) == len(copies)
