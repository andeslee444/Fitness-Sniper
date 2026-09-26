"""R-DEC-AMEND (controller ruling 2026-09-26, under the owner's 2026-09-25
delegation): an LDA amendment supersedes the original report for the same
registrant, client and quarter, so fct_influence counts the amendment INSTEAD
of the original — never both.

Measured read-only 2026-09-26 on data/parquet/influence/lda_filings.parquet:
fct_influence summed every filing, so a quarter with a report and its
amendment was counted twice (RTX's own 2024 Q1 and 2025 Q4 reports, e.g.).

audit_lda_filings grades EVERY lda_filings row (counted or not, and why);
fct_influence sums the counted rows. The unit tests run the committed model's
SQL against a throwaway DuckDB; the last test builds the fixture lake with dbt.

Senate LDA filing_type codes the rule reads (the lake carries no other
amendment field): Q1-Q4 quarterly report (Q1Y… no activity), 1T-4T
termination report (1TY… no activity), 1A-4A amendment (1AY… no activity),
1@-4@ termination amendment, RR registration, RA registration amendment.
"""
import os
import subprocess
from pathlib import Path

import duckdb

from test_dbt_build import make_lake

ROOT = Path(__file__).resolve().parents[1]

FILING_COLS = (
    "filing_uuid, url, client_name, registrant_name, filing_year,"
    " filing_period, filing_type, income_usd, expenses_usd, family_key_guess,"
    " match_method"
)


def _audit_sql() -> str:
    sql = (ROOT / "dbt" / "models" / "audit" / "audit_lda_filings.sql").read_text()
    sql = sql.replace("{{ source('influence', 'lda_filings') }}", "filings")
    assert "{{" not in sql, "unsubstituted macro left in audit_lda_filings.sql"
    return sql


def _resolve(filings):
    """filings: (uuid, registrant, client, year, period, type, income, expenses).
    Returns {uuid: (counted, resolution, latest_determinable)}."""
    con = duckdb.connect()
    defs = ", ".join(f"{c.strip()} varchar" for c in FILING_COLS.split(","))
    con.execute(f"create table filings ({defs})")
    for uuid, reg, client, year, period, ftype, inc, exp in filings:
        con.execute(
            "insert into filings values (?, 'u', ?, ?, ?, ?, ?, ?, ?, 'ACME',"
            " 'exact_family')",
            [uuid, client, reg, year, period, ftype, inc, exp],
        )
    rows = con.execute(
        "select filing_uuid, counted, resolution, latest_determinable"
        " from (" + _audit_sql() + ")"
    ).fetchall()
    con.close()
    # one graded row per filing
    assert len(rows) == len(filings), rows
    return {r[0]: r[1:] for r in rows}


FIRM, CLIENT, Y, Q1 = "OUTSIDE FIRM", "ACME INC", "2024", "first_quarter"


def test_an_amendment_supersedes_the_original_report():
    r = _resolve([
        ("orig", FIRM, CLIENT, Y, Q1, "Q1", "150000", ""),
        ("amend", FIRM, CLIENT, Y, Q1, "1A", "120000", ""),
    ])
    assert r["orig"] == (False, "superseded_by_amendment", True)
    assert r["amend"] == (True, "amendment_counted", True)


def test_the_supersession_is_per_registrant_client_and_quarter():
    r = _resolve([
        ("orig", FIRM, CLIENT, Y, Q1, "Q1", "150000", ""),
        ("amend", FIRM, CLIENT, Y, Q1, "1A", "120000", ""),
        # another quarter, another client, another registrant, another year
        ("q2", FIRM, CLIENT, Y, "second_quarter", "Q2", "90000", ""),
        ("other_client", FIRM, "OTHER CO", Y, Q1, "Q1", "10000", ""),
        ("other_firm", "ANOTHER FIRM", CLIENT, Y, Q1, "Q1", "20000", ""),
        ("other_year", FIRM, CLIENT, "2025", Q1, "Q1", "30000", ""),
    ])
    for uuid in ("q2", "other_client", "other_firm", "other_year"):
        assert r[uuid] == (True, "original", None), (uuid, r[uuid])
    assert r["orig"][0] is False and r["amend"][0] is True


def test_an_amendment_of_an_amendment_counts_once():
    # several amendments that report the same amounts: whichever is latest,
    # the quarter's figure is that amount, counted once
    r = _resolve([
        ("orig", FIRM, CLIENT, Y, Q1, "Q1", "", "3350000"),
        ("a1", FIRM, CLIENT, Y, Q1, "1A", "", "3350000"),
        ("a2", FIRM, CLIENT, Y, Q1, "1A", "", "3350000"),
    ])
    assert r["orig"] == (False, "superseded_by_amendment", True)
    counted = [u for u in ("a1", "a2") if r[u][0]]
    assert counted == ["a1"], r   # deterministic: lowest filing_uuid
    assert r["a2"] == (False, "amendment_superseded", True)


def test_disagreeing_amendments_count_the_smallest_and_say_the_latest_is_unknown():
    """The lake carries no posting date (influence/lda.py keeps none), so when
    a quarter's amendments disagree the latest cannot be named. The rule then
    counts the smallest amended figure — never more than the latest amendment
    reports — and flags the quarter (latest_determinable = false)."""
    r = _resolve([
        ("orig", FIRM, CLIENT, Y, Q1, "Q1", "", "2710000"),
        ("a_big", FIRM, CLIENT, Y, Q1, "1A", "", "2830000"),
        ("a_mid", FIRM, CLIENT, Y, Q1, "1A", "", "2390000"),
        ("a_small", FIRM, CLIENT, Y, Q1, "1A", "", "1600000"),
    ])
    assert r["orig"] == (False, "superseded_by_amendment", False)
    assert r["a_small"] == (True, "amendment_counted", False)
    assert r["a_big"] == (False, "amendment_superseded", False)
    assert r["a_mid"] == (False, "amendment_superseded", False)


def test_an_empty_amended_amount_is_smaller_than_a_reported_one():
    # an outside firm's empty income is "under $5,000" — the smaller figure
    r = _resolve([
        ("orig", FIRM, CLIENT, Y, Q1, "Q1", "", ""),
        ("a_amount", FIRM, CLIENT, Y, Q1, "1A", "20000", ""),
        ("a_empty", FIRM, CLIENT, Y, Q1, "1A", "", ""),
    ])
    assert r["a_empty"] == (True, "amendment_counted", False)
    assert r["a_amount"] == (False, "amendment_superseded", False)


def test_termination_and_no_activity_amendments_supersede_too():
    r = _resolve([
        # 3@ = termination amendment of the 3T termination report
        ("t", FIRM, CLIENT, Y, "third_quarter", "3T", "40000", ""),
        ("t_amend", FIRM, CLIENT, Y, "third_quarter", "3@", "50000", ""),
        # 2AY = amendment (no activity) of the Q2 report
        ("q2", FIRM, CLIENT, Y, "second_quarter", "Q2", "", "10000"),
        ("q2_amend", FIRM, CLIENT, Y, "second_quarter", "2AY", "", ""),
    ])
    assert r["t"][:2] == (False, "superseded_by_amendment")
    assert r["t_amend"][:2] == (True, "amendment_counted")
    assert r["q2"][:2] == (False, "superseded_by_amendment")
    assert r["q2_amend"][:2] == (True, "amendment_counted")


def test_an_amendment_with_no_original_in_the_lake_counts():
    r = _resolve([("amend", FIRM, CLIENT, Y, Q1, "1A", "30000", "")])
    assert r["amend"] == (True, "amendment_counted", True)


def test_registrations_and_unamended_reports_are_untouched():
    """Out of the ruling's scope, and counted exactly as before: a
    registration (RR) and its amendment (RA) are not quarterly reports (no
    amount in the lake), and two ORIGINAL reports for one quarter with no
    amendment are not an amendment chain."""
    r = _resolve([
        ("rr", FIRM, CLIENT, Y, Q1, "RR", "", ""),
        ("ra", FIRM, CLIENT, Y, Q1, "RA", "", ""),
        ("dup1", FIRM, CLIENT, Y, "fourth_quarter", "Q4", "10000", ""),
        ("dup2", FIRM, CLIENT, Y, "fourth_quarter", "Q4", "10000", ""),
        ("t", FIRM, CLIENT, Y, "third_quarter", "3T", "40000", ""),
        ("q", FIRM, CLIENT, Y, "third_quarter", "Q3", "40000", ""),
    ])
    assert r["rr"] == (True, "registration", None)
    assert r["ra"] == (True, "registration", None)
    for uuid in ("dup1", "dup2", "t", "q"):
        assert r[uuid] == (True, "original", None), (uuid, r[uuid])


def test_every_counted_quarter_counts_exactly_one_filing_when_amended():
    r = _resolve([
        ("o1", FIRM, CLIENT, Y, Q1, "Q1", "1", ""),
        ("o2", FIRM, CLIENT, Y, Q1, "1T", "2", ""),
        ("a1", FIRM, CLIENT, Y, Q1, "1A", "3", ""),
        ("a2", FIRM, CLIENT, Y, Q1, "1@", "4", ""),
    ])
    assert sum(1 for v in r.values() if v[0]) == 1


# ── the fixture lake, built with dbt ────────────────────────────────────────

def test_fct_influence_counts_the_amendment_instead_of_the_original(tmp_path):
    make_lake(tmp_path)
    # the fixture's two filings, plus an amendment of uuid-lda-001's quarter
    # (2024 Q1, OUTSIDE FIRM LLC for ACME PARENT INC): 150,000 → 120,000
    influence = tmp_path / "parquet/influence"
    duckdb.sql(
        "copy (select * from (values"
        " ('uuid-lda-001','https://lda.gov/filings/public/filing/uuid-lda-001/print/',"
        "  'ACME PARENT INC','OUTSIDE FIRM LLC','2024','first_quarter','Q1','150000','',"
        "  'ACME PARENT','exact_family'),"
        " ('uuid-lda-002','https://lda.gov/filings/public/filing/uuid-lda-002/print/',"
        "  'ACME PARENT INC','ACME PARENT INC','2024','second_quarter','Q2','','50000',"
        "  'ACME PARENT','exact_family'),"
        " ('uuid-lda-003','https://lda.gov/filings/public/filing/uuid-lda-003/print/',"
        "  'ACME PARENT INC','OUTSIDE FIRM LLC','2024','first_quarter','1A','120000','',"
        "  'ACME PARENT','exact_family'))"
        f" t({FILING_COLS})) to '{influence}/lda_filings.parquet' (format parquet)"
    )
    (tmp_path / "duckdb").mkdir()
    db = tmp_path / "duckdb" / "test.duckdb"
    env = {**os.environ, "GOVBUDGET_DATA": str(tmp_path), "GOVBUDGET_DUCKDB": str(db)}
    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--project-dir", "dbt", "--profiles-dir",
         "dbt", "--select", "+fct_influence", "audit_lda_filings",
         "warn_lda_amendment_latest_undetermined"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    con = duckdb.connect(str(db), read_only=True)
    try:
        assert con.sql(
            "select filings_count, lobbying_income_usd, lobbying_expense_usd,"
            " lobbying_total_usd from fct_influence"
            " where family_key = 'ACME PARENT' and filing_year = '2024'"
        ).fetchone() == (2, 120000.0, 50000.0, 170000.0)
        assert dict(con.sql(
            "select filing_uuid, resolution from audit_lda_filings"
        ).fetchall()) == {
            "uuid-lda-001": "superseded_by_amendment",
            "uuid-lda-002": "original",
            "uuid-lda-003": "amendment_counted",
        }
    finally:
        con.close()
