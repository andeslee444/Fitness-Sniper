"""The P-1 loader on 0390D's Chem Demilitarization lines (families piece-1
follow-ups design §4.3, #194; owner decisions 2026-10-04: Q1 (a), Q2).

The rows copy data/raw_docs/fy2026/dod/p1_display.xlsx rows 303-304 (read
2026-10-13): O&M 87,404 / 20,745 / 3,243 and RDT&E 1,002,560 / 754,762 /
210,039 in the FY2024 actuals, FY2025 enacted and FY2026 discretionary
request columns. O&M loads under its route-safe key 0390DOM with the printed
code kept in line_item_code; RDT&E restates R-1 program elements 0708081D +
0708083D (live budget_lines ids 1031-1035) and is checked against them, then
left out; any other code a web address cannot carry raises.
"""
import re
from decimal import Decimal

import psycopg
import pytest
from openpyxl import Workbook

from govbudget.jbooks.p1_loader import load_p1_rollup, parse_p1_rollup, verify_r1_restatements
from govbudget.jbooks.route_safe_codes import P1RestatementMismatch, UnsafeBudgetLineCode
from jbooks.test_p1_loader import P1_HEADERS

CHEM_DEMIL_OM = ["0390D", "Chemical Agents and Munitions Destruction, Defense", "A", "01",
                 "Operation and maintenance", "1", "", "", "O&M", "Chem Demilitarization - O&M",
                 "A", "Weapon System Cost", "Add", "", 87404, "", 20745, "", 3243]
CHEM_DEMIL_RDTE = ["0390D", "Chemical Agents and Munitions Destruction, Defense", "A", "02",
                   "Research, Development, Test, and Evaluation", "2", "", "", "RDT&E",
                   "Chem Demilitarization - RDT&E", "A", "Weapon System Cost", "Add",
                   "", 1002560, "", 754762, "", 210039]
REAL_BLI = ["2035A", "Other Procurement, Army", "A", "02", "Comm", "10", "1", "A", "BZ7015",
            "Handheld Manpack", "A", "Weapon System Cost", "Add", "", 114329, "", 98000, "", 105500]
# PB2026 R-1 rows of 0390D in the three columns above
R1_ROWS = [("0708081D", "fy_2024_actuals", 2093), ("0708083D", "fy_2024_actuals", 1000467),
           ("0708083D", "fy_2025_enacted", 754762), ("0708083D", "fy_2026_disc_request", 210039)]


def _xlsx(tmp_path, *rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1"
    ws.append(["Total of Displayed Rows"])
    ws.append(P1_HEADERS)
    for r in rows or (CHEM_DEMIL_OM, CHEM_DEMIL_RDTE, REAL_BLI):
        ws.append(r)
    p = tmp_path / "p1_display.xlsx"
    wb.save(p)
    return p


def _load_r1(pg_dsn, doc_id, rows=R1_ROWS):
    with psycopg.connect(pg_dsn) as con:
        for pe, at, amt in rows:
            con.execute(
                "insert into budget_lines (exhibit, fiscal_year, account, organization,"
                " budget_activity, pe_bli, title, amount_type, amount_thousands,"
                " source_document_id) values ('R-1', 2026, '0390D', 'A', '02', %s, 'x',"
                " %s, %s, %s)", (pe, at, amt, doc_id))


def _p1_rows(pg_dsn):
    with psycopg.connect(pg_dsn) as con:
        return con.execute(
            "select pe_bli, line_item_code, title, amount_type, amount_thousands"
            " from budget_lines where exhibit = 'P-1' order by pe_bli, amount_type"
        ).fetchall()


def test_the_o_and_m_line_loads_under_its_route_safe_key(pg_dsn, tmp_path, doc_id):
    _load_r1(pg_dsn, doc_id)
    n = load_p1_rollup(pg_dsn, _xlsx(tmp_path), exhibit="P-1", fiscal_year=2026,
                       source_document_id=doc_id)
    assert n == 6       # O&M's three FY columns + the real BLI's three
    rows = _p1_rows(pg_dsn)
    assert [r for r in rows if r[0] == "0390DOM"] == [
        ("0390DOM", "O&M", "Chem Demilitarization - O&M", "fy_2024_actuals", Decimal("87404")),
        ("0390DOM", "O&M", "Chem Demilitarization - O&M", "fy_2025_enacted", Decimal("20745")),
        ("0390DOM", "O&M", "Chem Demilitarization - O&M", "fy_2026_disc_request", Decimal("3243")),
    ]
    assert {r[0] for r in rows} == {"0390DOM", "BZ7015"}   # no 'O&M', no 'RDT&E'


def test_the_rdte_line_is_checked_against_the_r1_and_left_out(pg_dsn, tmp_path, doc_id):
    _load_r1(pg_dsn, doc_id)
    parsed = parse_p1_rollup(_xlsx(tmp_path), exhibit="P-1", fiscal_year=2026)
    assert sorted((r.pe_bli, r.line_item_code, r.amount_type, r.amount_thousands)
                  for r in parsed.restated) == [
        ("RDT&E", "RDT&E", "fy_2024_actuals", Decimal("1002560")),
        ("RDT&E", "RDT&E", "fy_2025_enacted", Decimal("754762")),
        ("RDT&E", "RDT&E", "fy_2026_disc_request", Decimal("210039")),
    ]
    assert all(r.pe_bli != "RDT&E" for r in parsed.rows)
    with psycopg.connect(pg_dsn) as con:
        assert verify_r1_restatements(con, parsed) == 3


def test_a_restatement_that_no_longer_matches_the_r1_refuses(pg_dsn, tmp_path, doc_id):
    _load_r1(pg_dsn, doc_id, [r if r[1] != "fy_2026_disc_request" else (r[0], r[1], 210038)
                              for r in R1_ROWS])
    with pytest.raises(P1RestatementMismatch,
                       match="fy_2026_disc_request = 210039 but R-1 0708081D [+] 0708083D"):
        load_p1_rollup(pg_dsn, _xlsx(tmp_path), exhibit="P-1", fiscal_year=2026,
                       source_document_id=doc_id)
    assert _p1_rows(pg_dsn) == []


def test_a_restatement_whose_r1_is_not_loaded_refuses(pg_dsn, tmp_path, doc_id):
    with pytest.raises(P1RestatementMismatch, match="load the edition's R-1 before its P-1"):
        load_p1_rollup(pg_dsn, _xlsx(tmp_path), exhibit="P-1", fiscal_year=2026,
                       source_document_id=doc_id)
    assert _p1_rows(pg_dsn) == []


def test_a_restatement_printed_under_another_title_refuses(pg_dsn, tmp_path, doc_id):
    _load_r1(pg_dsn, doc_id)
    renamed = CHEM_DEMIL_RDTE[:9] + ["Chem Demil RDT&E"] + CHEM_DEMIL_RDTE[10:]
    with pytest.raises(P1RestatementMismatch, match="not 'Chem Demilitarization - RDT&E'"):
        load_p1_rollup(pg_dsn, _xlsx(tmp_path, CHEM_DEMIL_OM, renamed), exhibit="P-1",
                       fiscal_year=2026, source_document_id=doc_id)


@pytest.mark.parametrize("account, code", [("2035A", "A/B"), ("2035A", "O&M"),
                                           ("0390D", "PROC #2"), ("0390D", "RDT&E/O&M")])
def test_any_other_route_unsafe_code_raises(tmp_path, account, code):
    # A page key belongs to one (account, code): O&M under 2035A has none.
    row = [account] + CHEM_DEMIL_OM[1:8] + [code] + CHEM_DEMIL_OM[9:]
    with pytest.raises(UnsafeBudgetLineCode, match=f"{account} prints {re.escape(repr(code))}"):
        parse_p1_rollup(_xlsx(tmp_path, row), exhibit="P-1", fiscal_year=2026)


def test_a_route_unsafe_non_add_row_is_ignored(tmp_path):
    memo = CHEM_DEMIL_OM[:8] + ["A/B"] + CHEM_DEMIL_OM[9:12] + ["Non-Add"] + CHEM_DEMIL_OM[13:]
    parsed = parse_p1_rollup(_xlsx(tmp_path, REAL_BLI, memo), exhibit="P-1", fiscal_year=2026)
    assert {r.pe_bli for r in parsed.rows} == {"BZ7015"}
    assert parsed.restated == ()
