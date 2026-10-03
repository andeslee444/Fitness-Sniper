"""V2 (spec 2026-10-02-era-procurement-history-design.md §8): the split
P-1 loader on a PB2021-shaped era workbook.

The header row is copied cell for cell from the real PB2021 P-1 display
workbook (data/raw_docs/fy2021/dod/p1_display.xlsx, sheet 'Exhibit P-1',
row 2, wrapped headers included), truncated after the FY 2019 and FY 2020
Base Enacted columns; the banner row 1 carries 'Total of Displayed Rows'
in column K as the real one does. Rows mirror real era shapes: column I
('Line Item') is the printed budget line code, column F ('Line Number')
the display line the era key is minted from.
"""
from decimal import Decimal

import psycopg
import pytest
from openpyxl import Workbook

from govbudget.jbooks.p1_loader import (
    EraKeyConflict,
    P1Parse,
    P1Row,
    load_p1_rollup,
    parse_p1_rollup,
    write_p1_rows,
)

# data/raw_docs/fy2021/dod/p1_display.xlsx, 'Exhibit P-1', row 2, columns A-Q.
PB2021_ERA_HEADERS = [
    "Account", "Account Title", "Organization", "Budget\nActivity",
    "Budget Activity Title", "Line\nNumber", "BSA",
    "Budget Sub Activity (BSA) Title", "Line Item", "Line Item Title",
    "Cost\nType", "Cost Type Title", "Add/\nNon-Add",
    "FY 2019\n(Base + OCO)\nQuantity", "FY 2019\n(Base + OCO)\nAmount",
    "FY 2020\nBase Enacted\nQuantity", "FY 2020\nBase Enacted\nAmount",
]

APN = ("1506N", "Aircraft Procurement, Navy")
OPAF = ("3080F", "Other Procurement, Air Force")


def _row(acct, org, ba, ba_title, line, code, title, cost_type, add, fy19, fy20):
    return [acct[0], acct[1], org, ba, ba_title, line, "10", "BSA", code, title,
            cost_type, "Cost", add, 0, fy19, 0, fy20]


def make_era_xlsx(tmp_path, rows, name="p1_display.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1"
    ws.append(["", "", "", "", "", "", "", "", "", "", "Total of Displayed Rows"])
    ws.append(PB2021_ERA_HEADERS)
    for r in rows:
        ws.append(r)
    p = tmp_path / name
    wb.save(p)
    return p


# A program line plus its advance-procurement line: the SAME printed code on
# two display lines (live PB2021 shape: 0577 F/A-18E/F lines 1 and 2).
ADVANCE_PROCUREMENT_PAIR = [
    _row(APN, "N", "01", "Combat Aircraft", "1", "0577", "F/A-18E/F (Fighter) Hornet",
         "A", "Add", 1000, 1100),
    _row(APN, "N", "01", "Combat Aircraft", "1", "0577", "F/A-18E/F (Fighter) Hornet",
         "B", "Add", 10, 20),
    _row(APN, "N", "01", "Combat Aircraft", "1", "0577", "F/A-18E/F (Fighter) Hornet",
         "Z", "Non-Add", 999999, 999999),
    _row(APN, "N", "01", "Combat Aircraft", "2", "0577", "F/A-18E/F (Fighter) Hornet",
         "A", "Add", 300, 400),
]
# Classified Programs: blank Line Number, organization '', code 9999999999
# (live PB2021 row 1096).
CLASSIFIED = _row(OPAF, "", "04", "Other Base Maintenance and Support Equip", "",
                  "9999999999", "Classified Programs", "", "Add", 20743417, 21086112)
# Footnote rows: blank Line Number, prose in column A (live PB2022 rows 1156-1157).
FOOTNOTES = [
    [""] + [None] * 16,
    ["*Includes Division A, Title IX and X of the Consolidated Appropriations Act, 2020"]
    + [None] * 16,
]
# Section header: an appropriation label in the line slot (the guard's '&').
SECTION_HEADER = _row(("0390D", "RDT&E, Defense-Wide"), "DW", "", "", "RDT&E",
                      "RDT&E", "RDT&E Total", "A", "Add", 1002560, 754762)


def test_parse_captures_the_printed_code_and_keys_by_line(tmp_path):
    parsed = parse_p1_rollup(
        make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR), exhibit="P-1", fiscal_year=2021)
    assert isinstance(parsed, P1Parse)
    assert parsed.era_line_keying is True
    assert parsed.sheet_title == "Exhibit P-1"
    got = {(r.pe_bli, r.amount_type): r for r in parsed.rows}
    assert sorted(got) == [
        ("1506N-N-L1", "fy_2019_base_oco"), ("1506N-N-L1", "fy_2020_base_enacted"),
        ("1506N-N-L2", "fy_2019_base_oco"), ("1506N-N-L2", "fy_2020_base_enacted"),
    ]
    line1 = got[("1506N-N-L1", "fy_2019_base_oco")]
    assert line1 == P1Row(
        exhibit="P-1", fiscal_year=2021, account="1506N",
        account_title="Aircraft Procurement, Navy", organization="N",
        budget_activity="01", budget_activity_title="Combat Aircraft",
        pe_bli="1506N-N-L1", title="F/A-18E/F (Fighter) Hornet",
        amount_type="fy_2019_base_oco", amount_thousands=Decimal("1010"),
        source_sheet="Exhibit P-1", source_cells=("O3", "O4"),
        line_item_code="0577",
    )
    # the advance-procurement line stays its own era key with its own code
    line2 = got[("1506N-N-L2", "fy_2020_base_enacted")]
    assert line2.line_item_code == "0577"
    assert line2.amount_thousands == Decimal("400")
    assert line2.source_cells == ("Q6",)


def test_parse_skips_classified_footnote_and_section_header_rows(tmp_path):
    """Blank-Line-Number rows (the Classified Programs line, footnotes) and
    the section-header label are skipped. S1b (Task 9) changes the first."""
    rows = ADVANCE_PROCUREMENT_PAIR[:1] + [CLASSIFIED, SECTION_HEADER] + FOOTNOTES
    parsed = parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)
    assert {r.pe_bli for r in parsed.rows} == {"1506N-N-L1"}
    assert parsed.skipped_invalid == 1  # the 'RDT&E' label row


@pytest.mark.parametrize("field, value", [
    ("code", "0578"),
    ("title", "F/A-18E/F (Fighter) Hornet (AP-CY)"),
    ("ba", "02"),
])
def test_parse_raises_when_an_era_key_prints_two_values(tmp_path, field, value):
    second = dict(code="0577", title="F/A-18E/F (Fighter) Hornet", ba="01")
    second[field] = value
    rows = [
        ADVANCE_PROCUREMENT_PAIR[0],
        _row(APN, "N", second["ba"], "Combat Aircraft", "1", second["code"],
             second["title"], "B", "Add", 10, 20),
    ]
    with pytest.raises(EraKeyConflict, match="1506N-N-L1"):
        parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)


def test_tripwire_ignores_non_add_rows(tmp_path):
    rows = [
        ADVANCE_PROCUREMENT_PAIR[0],
        _row(APN, "N", "01", "Combat Aircraft", "1", "0578", "Other",
             "Z", "Non-Add", 1, 1),
    ]
    parsed = parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)
    assert {r.line_item_code for r in parsed.rows} == {"0577"}


def test_parse_is_pure(tmp_path, monkeypatch):
    def no_db(*a, **k):
        raise AssertionError("parse_p1_rollup must not open a database connection")
    monkeypatch.setattr(psycopg, "connect", no_db)
    parsed = parse_p1_rollup(
        make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR), exhibit="P-1", fiscal_year=2021)
    assert len(parsed.rows) == 4


def test_modern_and_p1r_rows_carry_pe_bli_as_code(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1R"
    ws.append(["Account", "Account Title", "Organization", "Budget\nActivity",
               "Budget Activity Title", "BSA", "Budget Sub Activity (BSA) Title",
               "Line Item", "Line Item Title", "Cost\nType", "Cost Type Title",
               "FY 2018\nQuantity", "FY 2018\nAmount", "Classification"])
    ws.append(["0300D", "Procurement, Defense-Wide", "DEFW", "01", "Major Equipment",
               "1", "Major Equipment", "23", "Vehicles", "A", "Weapon System Cost",
               "", 21000, "U"])
    p = tmp_path / "p1r_display.xlsx"
    wb.save(p)
    parsed = parse_p1_rollup(p, exhibit="P-1R", fiscal_year=2017)
    assert parsed.era_line_keying is False
    assert [(r.pe_bli, r.line_item_code) for r in parsed.rows] == [("23", "23")]


def test_write_p1_rows_never_commits(pg_dsn, tmp_path, doc_id):
    parsed = parse_p1_rollup(
        make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR), exhibit="P-1", fiscal_year=2021)
    con = psycopg.connect(pg_dsn)
    try:
        n = write_p1_rows(con, parsed.rows, source_document_id=doc_id)
        assert n == 4
        inside = con.execute("select count(*) from budget_lines").fetchone()[0]
        assert inside == 4
        con.rollback()
    finally:
        con.close()
    with psycopg.connect(pg_dsn) as other:
        assert other.execute("select count(*) from budget_lines").fetchone()[0] == 0


def test_load_writes_line_item_code(pg_dsn, tmp_path, doc_id):
    n = load_p1_rollup(pg_dsn, make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR),
                       exhibit="P-1", fiscal_year=2021, source_document_id=doc_id)
    assert n == 4
    with psycopg.connect(pg_dsn) as con:
        rows = con.execute(
            "select pe_bli, line_item_code, count(*) from budget_lines"
            " group by 1, 2 order by 1"
        ).fetchall()
    assert rows == [("1506N-N-L1", "0577", 2), ("1506N-N-L2", "0577", 2)]


def test_update_branch_sets_line_item_code_on_an_existing_row(pg_dsn, tmp_path, doc_id):
    xlsx = make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR)
    load_p1_rollup(pg_dsn, xlsx, exhibit="P-1", fiscal_year=2021, source_document_id=doc_id)
    with psycopg.connect(pg_dsn) as con:
        con.execute("update budget_lines set line_item_code = null")
        ids_before = con.execute("select id from budget_lines order by id").fetchall()
    load_p1_rollup(pg_dsn, xlsx, exhibit="P-1", fiscal_year=2021, source_document_id=doc_id)
    with psycopg.connect(pg_dsn) as con:
        ids_after = con.execute("select id from budget_lines order by id").fetchall()
        codes = con.execute(
            "select distinct line_item_code from budget_lines").fetchall()
    assert ids_after == ids_before  # updated in place, nothing inserted
    assert codes == [("0577",)]
