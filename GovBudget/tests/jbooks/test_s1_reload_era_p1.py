"""scripts/era/s1_reload_era_p1.py (spec 2026-10-02-era-procurement-history-
design.md §8 V1, §9 S1): --check diffs the parse against Postgres without
writing; --apply re-runs the era P-1 workbooks in one transaction and rolls
back on any difference.

The database starts in the state S1 finds in production: every era P-1 row
loaded, migration 021 applied, era line_item_code NULL; plus a modern P-1
row and an era P-1R row whose codes the backfill already set.
"""
import hashlib
import importlib.util
from pathlib import Path

import psycopg
import pytest
from openpyxl import Workbook

from govbudget.jbooks.db import MIGRATIONS_DIR
from govbudget.jbooks.p1_loader import EraKeyConflict, load_p1_rollup

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "s1_reload_era_p1", ROOT / "scripts" / "era" / "s1_reload_era_p1.py")
s1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s1)

# data/raw_docs/fy2021/dod/p1_display.xlsx, 'Exhibit P-1', row 2, columns A-Q.
HEADERS = [
    "Account", "Account Title", "Organization", "Budget\nActivity",
    "Budget Activity Title", "Line\nNumber", "BSA",
    "Budget Sub Activity (BSA) Title", "Line Item", "Line Item Title",
    "Cost\nType", "Cost Type Title", "Add/\nNon-Add",
    "FY 2019\n(Base + OCO)\nQuantity", "FY 2019\n(Base + OCO)\nAmount",
    "FY 2020\nBase Enacted\nQuantity", "FY 2020\nBase Enacted\nAmount",
]


def _row(line, code, title, cost_type, fy19, fy20, ba="01"):
    return ["1506N", "Aircraft Procurement, Navy", "N", ba, "Combat Aircraft",
            line, "10", "BSA", code, title, cost_type, "Cost", "Add",
            0, fy19, 0, fy20]


EDITION_ROWS = {
    2020: [_row("1", "0577", "F/A-18E/F (Fighter) Hornet", "A", 1000, 1100),
           _row("1", "0577", "F/A-18E/F (Fighter) Hornet", "B", 10, 20)],
    2021: [_row("1", "0577", "F/A-18E/F (Fighter) Hornet", "A", 900, 950),
           _row("2", "0577", "F/A-18E/F (Fighter) Hornet", "A", 300, 400)],
}


def _workbook(path: Path, rows) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1"
    ws.append(["", "", "", "", "", "", "", "", "", "", "Total of Displayed Rows"])
    ws.append(HEADERS)
    for r in rows:
        ws.append(r)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def _register(con, fy, title, path):
    sha = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    return con.execute(
        "insert into jbook_documents (org, exhibit_family, fiscal_year, title,"
        " source_url, file_path, sha256, status) values ('DoD', 'rollup', %s,"
        " %s, %s, %s, %s, 'downloaded') returning id",
        (fy, title, f"https://example.test/fy{fy}/{title}", str(path), sha),
    ).fetchone()[0]


@pytest.fixture()
def era_db(pg_dsn, tmp_path):
    """Two era editions loaded, era codes nulled (post-021, pre-S1)."""
    docs = {}
    with psycopg.connect(pg_dsn) as con:
        for fy, rows in EDITION_ROWS.items():
            p = _workbook(tmp_path / f"fy{fy}" / "p1_display.xlsx", rows)
            docs[fy] = (_register(con, fy, "p1_display.xlsx", p), p)
            # the era P-1R and R-1 rollups are not S1's to touch
            _register(con, fy, "p1r_display.xlsx", tmp_path / f"fy{fy}" / "p1r.xlsx")
            _register(con, fy, "r1_display.xlsx", tmp_path / f"fy{fy}" / "r1.xlsx")
        modern = _register(con, 2026, "p1_display.xlsx", tmp_path / "fy2026.xlsx")
    for fy, (doc_id, p) in docs.items():
        load_p1_rollup(pg_dsn, p, exhibit="P-1", fiscal_year=fy, source_document_id=doc_id)
    with psycopg.connect(pg_dsn) as con:
        con.execute("update budget_lines set line_item_code = null where exhibit = 'P-1'")
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " budget_activity, pe_bli, title, amount_type, amount_thousands,"
            " source_document_id, line_item_code) values"
            " ('P-1', 2026, '3010F', 'F', '01', 'F01500', 'F-15', 'fy_2026_total', 7,"
            "  %s, 'F01500'),"
            " ('P-1R', 2021, '2035A', 'ARMY', '02', '9675A00010', 'RAVEN', 'fy_2021_total',"
            "  3, %s, '9675A00010')",
            (modern, docs[2021][0]),
        )
    return docs


def _snapshot(pg_dsn):
    with psycopg.connect(pg_dsn) as con:
        return con.execute(
            "select id, exhibit, fiscal_year, pe_bli, amount_type, amount_thousands,"
            " title, source_cells, line_item_code from budget_lines order by id"
        ).fetchall()


def _run(pg_dsn, *flags):
    return s1.main([*flags, "--dsn", pg_dsn, "--editions", "2020", "2021"])


def test_check_is_clean_and_counts_the_null_codes(pg_dsn, era_db, capsys):
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--check") == 0
    out = capsys.readouterr().out
    assert "V1 PB2020 P-1" in out and "V1 PB2021 P-1" in out
    assert "line_item_code: null 4, equal 0, differ 0" in out
    assert "V1: CLEAN (2 editions, 6 parsed rows)" in out
    assert _snapshot(pg_dsn) == before


@pytest.mark.parametrize("tamper, expect", [
    ("update budget_lines set amount_thousands = amount_thousands + 1"
     " where pe_bli = '1506N-N-L2' and amount_type = 'fy_2019_base_oco'",
     "amount_thousands"),
    ("update budget_lines set title = 'Hornet' where pe_bli = '1506N-N-L1'"
     " and fiscal_year = 2020 and amount_type = 'fy_2019_base_oco'", "title"),
    ("delete from budget_lines where pe_bli = '1506N-N-L2'"
     " and amount_type = 'fy_2020_base_enacted'", "missing in db: "),
    ("update jbook_documents set sha256 = 'stale' where fiscal_year = 2021"
     " and title = 'p1_display.xlsx'", "workbook sha256"),
])
def test_check_fails_on_any_difference(pg_dsn, era_db, capsys, tamper, expect):
    with psycopg.connect(pg_dsn) as con:
        con.execute(tamper)
    assert _run(pg_dsn, "--check") == 1
    out = capsys.readouterr().out
    assert expect in out
    assert "V1: DIFFERENCES" in out


def test_apply_fills_every_era_code_and_commits(pg_dsn, era_db, capsys):
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply") == 0
    out = capsys.readouterr().out
    assert "apply: snapshot 8 P-1/P-1R rows" in out
    assert "apply: pre-existing rows changed outside line_item_code: 0" in out
    assert ("apply: line_item_code equals the parse on 6 pre-existing"
            " era-edition P-1 rows (null before: 6)") in out
    assert "apply: rows inserted: 0 (expected 0); P-1/P-1R rows now 8" in out
    assert "apply: era keys 3, with exactly one line_item_code: 3" in out
    assert "apply: COMMITTED" in out
    after = _snapshot(pg_dsn)
    assert [r[:8] for r in after] == [r[:8] for r in before]
    assert {(r[3], r[8]) for r in after} == {
        ("1506N-N-L1", "0577"), ("1506N-N-L2", "0577"),
        ("F01500", "F01500"), ("9675A00010", "9675A00010"),
    }
    # idempotent: a second run finds every code already equal
    assert _run(pg_dsn, "--check") == 0
    assert "line_item_code: null 0, equal 4, differ 0" in capsys.readouterr().out


def test_apply_dry_run_rolls_back(pg_dsn, era_db, capsys):
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply", "--dry-run") == 0
    assert "apply: dry run, every check passed: ROLLED BACK" in capsys.readouterr().out
    assert _snapshot(pg_dsn) == before


def test_apply_refuses_when_v1_differs(pg_dsn, era_db, capsys):
    with psycopg.connect(pg_dsn) as con:
        con.execute("update budget_lines set source_cells = '{X9}'"
                    " where pe_bli = '1506N-N-L1' and fiscal_year = 2021")
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply") == 1
    assert "apply: V1 not clean, nothing written (ROLLED BACK)" in capsys.readouterr().out
    assert _snapshot(pg_dsn) == before


def test_apply_rolls_back_when_a_write_touches_another_column(
    pg_dsn, era_db, capsys, monkeypatch,
):
    real = s1.write_p1_rows

    def stray(con, rows, *, source_document_id):
        n = real(con, rows, source_document_id=source_document_id)
        con.execute("update budget_lines set title = 'moved' where pe_bli = 'F01500'")
        return n

    monkeypatch.setattr(s1, "write_p1_rows", stray)
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply") == 1
    out = capsys.readouterr().out
    assert "apply: pre-existing rows changed outside line_item_code: 1" in out
    assert "problem(s): ROLLED BACK" in out
    assert _snapshot(pg_dsn) == before


def test_apply_needs_migration_021(pg_dsn, era_db, capsys):
    with psycopg.connect(pg_dsn) as con:
        con.execute("alter table budget_lines drop column line_item_code")
    try:
        assert _run(pg_dsn, "--apply") == 2
        assert "run `govbudget migrate` (021) first" in capsys.readouterr().out
    finally:
        with psycopg.connect(pg_dsn) as con:
            con.execute(
                (MIGRATIONS_DIR / "021_budget_lines_line_item_code.sql").read_text())


def test_the_tripwire_propagates_before_any_write(pg_dsn, era_db, tmp_path):
    doc_id, path = era_db[2021]
    _workbook(path, EDITION_ROWS[2021] + [
        _row("2", "0578", "F/A-18E/F (Fighter) Hornet", "B", 1, 1)])
    with psycopg.connect(pg_dsn) as con:
        con.execute("update jbook_documents set sha256 = %s where id = %s",
                    (hashlib.sha256(path.read_bytes()).hexdigest(), doc_id))
    before = _snapshot(pg_dsn)
    with pytest.raises(EraKeyConflict, match="1506N-N-L2"):
        _run(pg_dsn, "--apply")
    assert _snapshot(pg_dsn) == before
