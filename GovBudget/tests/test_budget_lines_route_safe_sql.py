"""dbt/tests/assert_budget_lines_route_safe_pe_bli.sql (families piece-1
follow-ups design §4.4, #194): it fails on the pre-write lake's 16 stale
0390D rows and passes once they are re-keyed or gone."""
import duckdb
from dbt_render import render_dbt_sql

TEST = "dbt/tests/assert_budget_lines_route_safe_pe_bli.sql"


def _failures(pe_blis):
    con = duckdb.connect()
    con.execute("create table stg_budget_lines (exhibit varchar, fiscal_year integer,"
                " account varchar, pe_bli varchar)")
    con.executemany("insert into stg_budget_lines values (?, ?, ?, ?)", pe_blis)
    return sorted(con.execute(render_dbt_sql(TEST)).fetchall())


def test_the_pre_write_rows_fail():
    rows = ([("P-1", 2024, "0390D", "O&M")] * 5 + [("P-1", 2024, "0390D", "RDT&E")] * 5
            + [("P-1", 2025, "0390D", "O&M")] * 3 + [("P-1", 2025, "0390D", "RDT&E")] * 3
            + [("P-1", 2019, "0390D", "0390D-ARMY-L1"), ("R-1", 2026, "0390D", "0708083D")])
    assert _failures(rows) == [
        ("route-unsafe pe_bli in budget_lines", "P-1", 2024, "0390D", "O&M", 5),
        ("route-unsafe pe_bli in budget_lines", "P-1", 2024, "0390D", "RDT&E", 5),
        ("route-unsafe pe_bli in budget_lines", "P-1", 2025, "0390D", "O&M", 3),
        ("route-unsafe pe_bli in budget_lines", "P-1", 2025, "0390D", "RDT&E", 3),
    ]


def test_every_unsafe_character_fails():
    for pe in ("A#B", "A/B", "A?B", "A%B", "A B", "A\tB"):
        assert len(_failures([("P-1", 2026, "0300D", pe)])) == 1, pe


def test_the_post_write_lake_passes():
    assert _failures([("P-1", 2024, "0390D", "0390DOM"), ("P-1", 2026, "0390D", "0390DOM"),
                      ("P-1", 2019, "0390D", "0390D-ARMY-L1"), ("P-1", 2017, "0300D", "46-1")]) == []
