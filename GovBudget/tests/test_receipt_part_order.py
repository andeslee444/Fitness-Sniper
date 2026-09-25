"""A multi-part PDF receipt lists its parts in ONE order on every export.

Final integration review finding #3 (2026-09-25): 26 receipts in the
integration export listed the same parts as production in a different order,
with no code change behind it. /program/F015EX/'s reconciliation chip
(cf802c75afa0f505) opened on P-1 line 44 in production and on line 7 in the
integration build. The drawer opens on parts[0], so the order is what a reader
sees first.

The cause was upstream of the receipt. program_pdf_receipts.
attach_additive_receipts concatenates its inputs' parts in the order the
summed citation lists its `inputs`. Those came from the FY2026 budget_lines
query, whose only sort keys were (exhibit, pe_bli, amount_type). F015EX's
three reconciliation lines (BA-01, BA-05 and BA-07) tie on all three, and
Postgres returned tied rows in heap order, which moves whenever a row is
rewritten. export_site._load_budget_line_rows now sorts on a TOTAL key: the
three original keys, then organization, appropriation account and budget
activity, then the row id. Within one organization and account, ascending
budget activity is the order the P-1 prints a program's lines in.

These tests insert the rows in production's churned order, BA-05, BA-07,
BA-01. Without an explicit tiebreak Postgres returns them in that heap order,
so each test fails on the unsorted query. The end-to-end test follows the
order from the query through the summed citation's `inputs` to the receipt's
parts.
"""
from __future__ import annotations

import json

import psycopg
import pytest

from govbudget.export_site import _build_fy26_split_index, _load_budget_line_rows
from govbudget.program_pdf_receipts import attach_additive_receipts

_PE = "F015EX"
_TYPE = "fy_2026_reconciliation_request"
# (budget_activity, source cells, amount $K) — PB2026 P-1, account 3010F.
_LINES = {
    "01": (["U847"], 2480818),          # line 7
    "05": (["U875"], 286700),           # line 44
    "07": (["U923", "U932"], 246876),   # lines 112 + 134
}
_CHURNED = ("05", "07", "01")   # production's order (81929a6b), heap order here
_DEFINED = ["01", "05", "07"]   # ascending budget activity: the P-1's order


def _seed(con) -> None:
    doc = con.execute(
        "insert into jbook_documents (org, exhibit_family, fiscal_year, title,"
        " source_url, sha256, status) values ('DOD','rollup',2026,"
        " 'p1_display.xlsx','https://example.test/p1_display.xlsx',%s,"
        " 'downloaded') returning id",
        ("e" * 64,),
    ).fetchone()[0]
    for ba in _CHURNED:
        cells, amount = _LINES[ba]
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account,"
            " account_title, organization, budget_activity,"
            " budget_activity_title, pe_bli, title, amount_type,"
            " amount_thousands, source_document_id, source_sheet, source_cells)"
            " values ('P-1',2026,'3010F','Aircraft Procurement, Air Force','F',"
            " %s,'Activity',%s,'F-15EX',%s,%s,%s,'Exhibit P-1',%s)",
            (ba, _PE, _TYPE, amount, doc, cells),
        )


@pytest.fixture()
def f015ex_rows(pg_dsn):
    """The loader's rows for the seeded code, inside a rolled-back
    transaction so the session database is left as it was found."""
    with psycopg.connect(pg_dsn) as con:
        try:
            _seed(con)
            rows, _excluded, _null = _load_budget_line_rows(con)
            yield [r for r in rows if r[8] == _PE]
        finally:
            con.rollback()


def test_tied_budget_lines_come_out_in_the_printed_order(f015ex_rows):
    """(exhibit, pe_bli, amount_type) tie for all three rows; the loader's
    tiebreak (organization, account, budget activity, id) decides, never
    the heap."""
    assert [r[6] for r in f015ex_rows] == _DEFINED
    assert [r[15] for r in f015ex_rows] == ["U847", "U875", "U923,U932"]


def test_the_receipt_opens_on_the_first_printed_line_whatever_the_heap(f015ex_rows):
    """End to end: the query order is the summed citation's `inputs` order
    is the receipt's part order. The lead part is line 7 (U847). Production's
    headline receipt for the same page (4a9ae7cc78dcf0ba) already opens
    there, so the page's two receipts now agree."""
    fid = {r[6]: r[0] for r in f015ex_rows}
    _split, cit_rows = _build_fy26_split_index(bl_rows=f015ex_rows)
    summed = [r for r in cit_rows if _TYPE in (r[20] or "")]
    assert len(summed) == 1
    total_fid, inputs = summed[0][0], json.loads(summed[0][21])
    assert inputs == [fid[ba] for ba in _DEFINED]

    citations = {total_fid: {
        "kind": "derived", "units": "USD thousands", "formula": summed[0][20],
        "inputs": summed[0][21], "recorded_value": summed[0][23],
    }}
    receipts = {
        fid[ba]: {
            "amount_thousands": float(amount), "matched_amount_thousands": float(amount),
            "complete": True, "blank_zero_count": 0, "unmatched_count": 0,
            "parts": [{"workbook_cell": c, "amount_thousands": float(amount) / len(cells)}
                      for c in cells],
            "source_documents": [],
        }
        for ba, (cells, amount) in _LINES.items()
    }
    attach_additive_receipts(citations, receipts)
    parts = [p["workbook_cell"] for p in receipts[total_fid]["parts"]]
    assert parts == ["U847", "U875", "U923", "U932"]
