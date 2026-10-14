"""dbt/tests/assert_route_safe_codes_valid.sql on a hand-built lake (families
piece-1 follow-ups design §4.2, #194): the committed seed passes on the
post-write shape (the 0390DOM alias rows print O&M under 0390D), and every
defect the test exists for fails it."""
import csv

import duckdb
import pytest
from dbt_render import ROOT, render_dbt_sql

from govbudget.jbooks.route_safe_codes import SEED_COLUMNS

TEST = "dbt/tests/assert_route_safe_codes_valid.sql"
SEED = ROOT / "dbt" / "seeds" / "p1_route_safe_codes.csv"

# (exhibit, fiscal_year, account, pe_bli, line_item_code)
LINES = [
    ("P-1", 2026, "0390D", "0390DOM", "O&M"),
    ("P-1", 2024, "0390D", "0390DOM", "O&M"),
    ("P-1", 2019, "0390D", "0390D-ARMY-L1", "O&M"),
    ("R-1", 2026, "0390D", "0708083D", None),
    ("P-1", 2026, "0300D", "7001SA1000", "7001SA1000"),
]
DETAILS = [("0708083D",), ("7001SA1000",)]


def _committed_seed() -> list[dict]:
    with open(SEED, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _failures(lines=LINES, details=DETAILS, seed=None) -> list[tuple]:
    con = duckdb.connect()
    con.execute("create table stg_budget_lines (exhibit varchar, fiscal_year integer,"
                " account varchar, pe_bli varchar, line_item_code varchar)")
    con.executemany("insert into stg_budget_lines values (?, ?, ?, ?, ?)", lines)
    con.execute("create table stg_budget_details (pe_bli varchar)")
    con.executemany("insert into stg_budget_details values (?)", details)
    con.execute("create table p1_route_safe_codes ("
                + ", ".join(f"{c} varchar" for c in SEED_COLUMNS) + ")")
    for row in (_committed_seed() if seed is None else seed):
        con.execute(f"insert into p1_route_safe_codes values ({', '.join('?' * len(SEED_COLUMNS))})",
                    [row[c] for c in SEED_COLUMNS])
    return con.execute(render_dbt_sql(TEST)).fetchall()


def test_the_committed_seed_passes_on_the_post_write_lake():
    assert _failures() == []


def _row(**changes):
    row = dict(_committed_seed()[0])
    row.update(changes)
    return row


OTHER_CODE = "page_key is the pe_bli of a budget_lines row of another code"


@pytest.mark.parametrize("lines, details, seed, failures", [
    # the second row names another code, so the alias rows fail it as well
    (LINES, DETAILS, [_row(), _row(line_item_code="A/B")],
     {"page_key repeats in the seed", OTHER_CODE}),
    (LINES, DETAILS, [_row(page_key="0390D-OM")], {"page_key is not [A-Z0-9]+"}),
    (LINES + [("P-1", 2026, "0300D", "0390DOM", "0390DOM")], DETAILS, None, {OTHER_CODE}),
    (LINES + [("P-1", 2025, "0390D", "0390DOM", "RDT&E")], DETAILS, None, {OTHER_CODE}),
    (LINES, DETAILS + [("0390DOM",)], None, {"page_key is the pe_bli of a J-book detail row"}),
])
def test_each_defect_fails(lines, details, seed, failures):
    assert {r[0] for r in _failures(lines, details, seed)} == failures
