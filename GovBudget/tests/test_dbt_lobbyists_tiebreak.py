"""dim_lobbyists must pick the SAME covered_position on every build.

Chain F2 (2026-09-25) rebuilt the warehouse twice from one lake and 14
lobbyist fact ids changed between the two builds. The exporter mints a
lobbyist's fact id from the disclosing filing — the lowest filing_uuid whose
covered_position equals the mart's (export_site._export_dim_lobbyists) — and
the mart chose covered_position with first_value() ordered by (disclosed
first, filing_appearances desc) and nothing after that. Two positions tied on
both keys came back in whatever order the sort emitted them, so the disclosing
filing, and with it the /fact/ link, could change between deploys with the
lake unchanged.

The order is now total (covered_position itself breaks the tie). These tests
run the committed model's own SQL against a throwaway DuckDB with the tied
rows inserted in both orders, several times, and require one answer.
"""
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _model_sql() -> str:
    sql = (ROOT / "dbt" / "models" / "marts" / "dim_lobbyists.sql").read_text()
    sql = sql.replace("{{ source('influence', 'lda_lobbyists') }}", "lda_lobbyists")
    assert "{{" not in sql, "unsubstituted macro left in dim_lobbyists.sql"
    return sql


def _pick(rows: list[tuple]) -> tuple:
    con = duckdb.connect(config={"threads": 4})
    try:
        con.execute(
            "create table lda_lobbyists"
            " (filing_uuid varchar, name varchar, covered_position varchar)"
        )
        con.executemany("insert into lda_lobbyists values (?, ?, ?)", rows)
        return con.execute(
            "select covered_position, filings_count, revolving_door from ("
            + _model_sql() + ") where name = 'PAT DOE'"
        ).fetchone()
    finally:
        con.close()


CASES = {
    # two disclosed positions, one filing each: the tie the old order left open
    "two disclosed, tied": (
        [("f1", "PAT DOE", "Legislative Assistant, Sen. X"),
         ("f2", "PAT DOE", "Chief of Staff, Rep. Y")],
        ("Chief of Staff, Rep. Y", 2, True),
    ),
    # the undisclosed spellings tie too: '' and NULL are both "not disclosed"
    "empty vs null, tied": (
        [("f1", "PAT DOE", None), ("f2", "PAT DOE", "")],
        ("", 2, False),
    ),
    "N/A vs empty, tied": (
        [("f1", "PAT DOE", "N/A"), ("f2", "PAT DOE", "")],
        ("", 2, False),
    ),
    # the existing preferences are unchanged: more appearances wins…
    "more appearances wins": (
        [("f1", "PAT DOE", "Aide, Sen. Z"), ("f2", "PAT DOE", "Aide, Sen. Z"),
         ("f3", "PAT DOE", "Chief of Staff, Rep. Y")],
        ("Aide, Sen. Z", 3, True),
    ),
    # …and a disclosed position beats a more frequent undisclosed one
    "disclosed beats frequent empty": (
        [("f1", "PAT DOE", ""), ("f2", "PAT DOE", ""), ("f3", "PAT DOE", ""),
         ("f4", "PAT DOE", "Aide, Sen. Z")],
        ("Aide, Sen. Z", 4, True),
    ),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_covered_position_is_the_same_whatever_order_the_rows_arrive_in(case):
    rows, expected = CASES[case]
    seen = set()
    for _ in range(5):
        seen.add(_pick(rows))
        seen.add(_pick(list(reversed(rows))))
    assert seen == {expected}, (case, seen)
