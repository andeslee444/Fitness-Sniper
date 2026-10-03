"""Migration 021 (spec docs/superpowers/specs/2026-10-02-era-procurement-
history-design.md §4.1): budget_lines.line_item_code, the budget line code
printed in the source P-1/P-1R row.

The backfill copies pe_bli onto every P-1/P-1R row whose pe_bli is not an
era key: modern P-1 and every P-1R row already key by the printed code. Era
P-1 rows ('{account}-{org}-L{line}') stay NULL until the S1 re-run
(scripts/era/s1_reload_era_p1.py --apply); R-1 rows stay NULL (a program
element, not a budget line code).

The migration's SQL is re-executed inside a rolled-back transaction after
dropping the column the session fixture already added (the pattern of
tests/test_migration_019_recipient_basis.py).
"""
import psycopg
import pytest

from govbudget.jbooks.db import MIGRATIONS_DIR

SQL_PATH = MIGRATIONS_DIR / "021_budget_lines_line_item_code.sql"
COMMENT = (
    'Budget line code printed in the source P-1/P-1R row (era "Line Item",'
    ' modern "Budget Line Item"); source-stated, never mapped'
)

# (exhibit, fiscal_year, account, organization, budget_activity, pe_bli),
# and the line_item_code the backfill must leave on the row.
ROWS = [
    (("P-1", 2026, "3010F", "F", "01", "F01500"), "F01500"),
    (("P-1", 2026, "3080F", "", "04", "9999999999"), "9999999999"),
    (("P-1", 2021, "1506N", "N", "01", "1506N-N-L1"), None),
    (("P-1", 2017, "0300D", "WHS", "01", "0300D-WHS-L46-1"), None),
    (("P-1R", 2021, "2035A", "ARMY", "02", "9675A00010"), "9675A00010"),
    (("P-1R", 2024, "2035A", "A", "02", "BZ7015"), "BZ7015"),
    (("R-1", 2026, "0400", "DARPA", "01", "0601101E"), None),
]


@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def test_021_adds_a_commented_text_column(con):
    assert con.execute(
        "select data_type from information_schema.columns"
        " where table_name = 'budget_lines' and column_name = 'line_item_code'"
    ).fetchall() == [("text",)]
    assert con.execute(
        "select col_description('budget_lines'::regclass, attnum)"
        " from pg_attribute where attrelid = 'budget_lines'::regclass"
        " and attname = 'line_item_code'"
    ).fetchone()[0] == COMMENT


def test_021_backfills_the_printed_code_everywhere_but_era_keys(con):
    con.execute("alter table budget_lines drop column line_item_code")
    doc_id = con.execute(
        "insert into jbook_documents (org, exhibit_family, fiscal_year, title,"
        " source_url, status) values ('DoD', 'rollup', 2026, 'm021.xlsx',"
        " 'https://example.test/m021.xlsx', 'downloaded') returning id"
    ).fetchone()[0]
    for (exhibit, fy, account, org, ba, pe_bli), _ in ROWS:
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account,"
            " organization, budget_activity, pe_bli, amount_type,"
            " amount_thousands, source_document_id)"
            " values (%s, %s, %s, %s, %s, %s, 'fy_2020_total', 1, %s)",
            (exhibit, fy, account, org, ba, pe_bli, doc_id),
        )
    con.execute(SQL_PATH.read_text())
    got = dict(con.execute(
        "select pe_bli, line_item_code from budget_lines").fetchall())
    assert got == {key[5]: code for key, code in ROWS}
