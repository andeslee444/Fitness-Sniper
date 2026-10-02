<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 8: S1 — V1 no-write diff, transactional re-run, proof and live write

**Spec:** §4.2 bullets 1 and 3 (V1 diffs the parse against Postgres; S1 runs the writer in a
transaction it controls, from a dedicated script, so the tripwire cannot be swallowed), §8 V1, §9 S1 ("V1
clean; V2 green; equality holds; 6,927 keys with exactly one code; S0-vs-post export
diff empty"), §11 risk 2.

**Files:**
- Create: `scripts/era/s1_reload_era_p1.py`
- Create: `tests/jbooks/test_s1_reload_era_p1.py`
- Create: `docs/superpowers/reviews/families-s1-proof.md` (proof note, Step 18)
- Shared writes (after the proof): live Postgres `govbudget` (migration 021; S1 update of
  57,722 era P-1 rows' `line_item_code`), live lake `data/parquet/jbooks/*.parquet`
  (`jbooks export-facts`)

**Interfaces:** Consumes: Task 6 (`parse_p1_rollup`, `write_p1_rows`, `P1Row`, `P1Parse`,
`EraKeyConflict`, migration 021), Task 7 (export_facts column + id order, stg column),
Task 3 (`govbudget proof snapshot`, `$SNAP/env.sh`, `govbudget proof diff`; CONTRACT ISSUE 3),
`config.PG_DSN`. / Produces: `scripts/era/s1_reload_era_p1.py` with `--check`,
`--apply [--dry-run]`, `--dsn`, `--editions` and module functions `main(argv) -> int`,
`check(dsn, editions) -> int`, `apply(dsn, editions, *, dry_run) -> int`,
`compare_edition(...)`, `verify_apply(...)`; live state after this task: every
PB2017–23 P-1 row carries `line_item_code` = its column I code (6,927 era keys, one code
each); the live lake `budget_lines.parquet` carries the column, in id order. Snapshot
`.proofs/s0` (its `pg/` dump is the pristine pre-S1 database).

Measured read-only now (2026-10-02, `postgresql://localhost/govbudget`):
P-1/P-1R rows 84,463 (P-1 67,902 + P-1R 16,561); era P-1 rows per edition
PB2017 6,783 · PB2018 13,377 · PB2019 12,857 · PB2020 8,775 · PB2021 10,050 ·
PB2022 2,979 · PB2023 2,901 = 57,722 (all era keys; 0 rows with NULL budget_activity, so
every upsert hits its existing row); era P-1 rollup documents are ids 189, 261, 271, 282,
292, 302, 312, title `p1_display.xlsx`, file_path
`/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/raw_docs/fy{2017..2023}/dod/p1_display.xlsx`,
sha256 present; `schema_migrations` holds 001–020; the jbooks lake parquets equal a fresh
read of Postgres row for row; `check_reviews_follow_loader` passes. A full rehearsal of
this task's `--apply` on a restore of `budget_lines` + `jbook_documents` produced exactly
the outputs below. Queries (each in a `read only` transaction):

```sql
select exhibit, fiscal_year, count(*), count(distinct (account, organization, budget_activity, pe_bli)),
       sum(case when pe_bli ~ '^\d{4}[A-Z]-[A-Z]+-L' then 1 else 0 end)
  from budget_lines where exhibit in ('P-1','P-1R') group by 1, 2 order by 1, 2;
select count(*) from budget_lines where budget_activity is null;                -- 0
select id, fiscal_year, title, file_path, sha256 is not null from jbook_documents
 where exhibit_family = 'rollup' and title not like 'r1%' and title not like 'p1r%'
   and fiscal_year between 2017 and 2023 order by fiscal_year;                 -- 7 rows
select name from schema_migrations order by 1;                                 -- 001 … 020
```

- [ ] **Step 1: Write the failing script tests**

Create `tests/jbooks/test_s1_reload_era_p1.py`:

```python
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
```

- [ ] **Step 2: Run them to see them fail**

Run: `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_s1_reload_era_p1.py -q`

Expected: collection error `FileNotFoundError: [Errno 2] No such file or directory: '/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/era/s1_reload_era_p1.py'`.

- [ ] **Step 3: Write the script**

Create `scripts/era/s1_reload_era_p1.py`:

```python
"""S1: re-run the PB2017-PB2023 P-1 workbooks through the split loader so
every era P-1 budget_lines row records the budget line code it prints
(budget_lines.line_item_code, migration 021).

Spec: docs/superpowers/specs/2026-10-02-era-procurement-history-design.md
§4.2, §8 V1, §9 S1.

  --check   V1, no write. Parses each era P-1 workbook with parse_p1_rollup
            and diffs every (exhibit, fiscal_year, account, organization,
            budget_activity, pe_bli, amount_type) row against Postgres: the
            key set, amount, title, account title, budget activity title,
            source cells, source sheet and source document; plus the
            workbook's sha256 against jbook_documents. When the
            line_item_code column exists it also counts, per edition, rows
            whose stored code is null / equal to the parse / different.
            Exit 1 on any difference (a stored code that differs counts; a
            null one does not, it is what --apply fills).

  --apply   One transaction under an EXCLUSIVE lock on budget_lines:
            V1 again (refuses on any difference), snapshot every column of
            every P-1/P-1R row, write_p1_rows for each edition, re-read, and
            require: no row removed; every pre-existing column except
            line_item_code identical on every row; line_item_code equal to
            the parse on every era-edition P-1 row and unchanged everywhere
            else; inserted rows exactly the parse rows the table lacked;
            every era key ('{account}-{org}-L{line}') carrying exactly one
            non-null line_item_code. Any failure rolls back (exit 1);
            otherwise commits (or rolls back under --dry-run, exit 0).

The parse runs before any database work, so EraKeyConflict propagates
uncaught (this script never goes through the CLI's per-workbook catch-all).

Usage (from GovBudget/):
  uv run --project . python scripts/era/s1_reload_era_p1.py --check
  uv run --project . python scripts/era/s1_reload_era_p1.py --apply [--dry-run]
DSN: --dsn, else GOVBUDGET_PG_DSN (config.PG_DSN).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

import psycopg

from govbudget import config
from govbudget.jbooks.p1_loader import P1Parse, P1Row, parse_p1_rollup, write_p1_rows

ERA_EDITIONS: tuple[int, ...] = tuple(range(2017, 2024))
ERA_KEY_RE = re.compile(r"^\d{4}[A-Z]-[A-Z]+-L")

# Columns V1 compares on every shared key (the key columns are compared by
# the key-set diff itself).
V1_COLUMNS = (
    "amount_thousands", "title", "account_title", "budget_activity_title",
    "source_cells", "source_sheet", "source_document_id",
)
# Every budget_lines column before migration 021, in table order.
SNAPSHOT_COLUMNS = (
    "id", "exhibit", "fiscal_year", "account", "account_title", "organization",
    "budget_activity", "budget_activity_title", "line_number", "pe_bli",
    "title", "amount_type", "amount_thousands", "source_document_id",
    "source_sheet", "source_cells",
)


def row_key(exhibit, fiscal_year, account, organization, budget_activity,
            pe_bli, amount_type) -> tuple:
    """The budget_lines unique-constraint grain."""
    return (exhibit, fiscal_year, account, organization, budget_activity,
            pe_bli, amount_type)


def parse_key(r: P1Row) -> tuple:
    return row_key(r.exhibit, r.fiscal_year, r.account, r.organization,
                   r.budget_activity, r.pe_bli, r.amount_type)


def parse_values(r: P1Row, source_document_id: int) -> dict:
    return {
        "amount_thousands": r.amount_thousands,
        "title": r.title,
        "account_title": r.account_title,
        "budget_activity_title": r.budget_activity_title,
        "source_cells": list(r.source_cells),
        "source_sheet": r.source_sheet,
        "source_document_id": source_document_id,
    }


def has_line_item_code(con) -> bool:
    return con.execute(
        "select count(*) from information_schema.columns"
        " where table_name = 'budget_lines' and column_name = 'line_item_code'"
    ).fetchone()[0] == 1


def era_p1_documents(con, editions) -> dict[int, tuple[int, Path, str | None]]:
    """{edition: (document id, workbook path, sha256)} for the era P-1
    rollup workbooks — the same rule cli._jbooks_load_rollups applies
    (rollup family, not 'r1…', not 'p1r…'). Exactly one per edition."""
    rows = con.execute(
        "select id, fiscal_year, file_path, sha256 from jbook_documents"
        " where exhibit_family = 'rollup' and status = 'downloaded'"
        "   and title not like 'r1%%' and title not like 'p1r%%'"
        "   and fiscal_year = any(%s)"
        " order by fiscal_year, id",
        (list(editions),),
    ).fetchall()
    by_fy: dict[int, list] = {}
    for doc_id, fy, path, sha in rows:
        by_fy.setdefault(fy, []).append((doc_id, Path(path), sha))
    bad = {fy: len(by_fy.get(fy, [])) for fy in editions if len(by_fy.get(fy, [])) != 1}
    if bad:
        raise SystemExit(
            f"s1: expected exactly one era P-1 rollup document per edition, got {bad}")
    return {fy: by_fy[fy][0] for fy in editions}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_edition(con, parsed: P1Parse, *, fiscal_year: int, doc_id: int,
                    with_codes: bool) -> dict:
    """V1 for one edition: the parse against the stored P-1 rows."""
    parse_by_key: dict[tuple, P1Row] = {}
    dup_keys = 0
    for r in parsed.rows:
        k = parse_key(r)
        if k in parse_by_key:
            dup_keys += 1
        parse_by_key[k] = r
    code_sql = ", line_item_code" if with_codes else ""
    db = {}
    for rec in con.execute(
        "select account, organization, budget_activity, pe_bli, amount_type,"
        " amount_thousands, title, account_title, budget_activity_title,"
        f" source_cells, source_sheet, source_document_id{code_sql}"
        " from budget_lines where exhibit = 'P-1' and fiscal_year = %s",
        (fiscal_year,),
    ).fetchall():
        k = row_key("P-1", fiscal_year, *rec[:5])
        db[k] = dict(zip(V1_COLUMNS, rec[5:12]))
        if with_codes:
            db[k]["line_item_code"] = rec[12]
    missing = sorted(set(parse_by_key) - set(db), key=repr)
    extra = sorted(set(db) - set(parse_by_key), key=repr)
    diffs = []
    codes = Counter()
    for k in sorted(set(parse_by_key) & set(db), key=repr):
        want = parse_values(parse_by_key[k], doc_id)
        for col in V1_COLUMNS:
            if want[col] != db[k][col]:
                diffs.append((k, col, want[col], db[k][col]))
        if with_codes:
            stored = db[k]["line_item_code"]
            if stored is None:
                codes["null"] += 1
            elif stored == parse_by_key[k].line_item_code:
                codes["equal"] += 1
            else:
                codes["differ"] += 1
                diffs.append((k, "line_item_code",
                              parse_by_key[k].line_item_code, stored))
    return {
        "fiscal_year": fiscal_year, "doc_id": doc_id,
        "parse_rows": len(parsed.rows), "db_rows": len(db),
        "dup_keys": dup_keys, "missing": missing, "extra": extra,
        "diffs": diffs, "codes": codes, "with_codes": with_codes,
    }


def report_ok(rep: dict) -> bool:
    return not (rep["dup_keys"] or rep["missing"] or rep["extra"] or rep["diffs"])


def print_report(rep: dict) -> None:
    codes = (
        f"null {rep['codes']['null']}, equal {rep['codes']['equal']},"
        f" differ {rep['codes']['differ']}"
        if rep["with_codes"] else "column absent"
    )
    print(
        f"V1 PB{rep['fiscal_year']} P-1 (doc {rep['doc_id']}): parse"
        f" {rep['parse_rows']} rows | db {rep['db_rows']} | missing in db"
        f" {len(rep['missing'])} | extra in db {len(rep['extra'])} |"
        f" duplicate parse keys {rep['dup_keys']} | column diffs"
        f" {len(rep['diffs'])} | line_item_code: {codes}"
    )
    for k in rep["missing"][:5]:
        print(f"  missing in db: {k}")
    for k in rep["extra"][:5]:
        print(f"  extra in db: {k}")
    for k, col, want, got in rep["diffs"][:10]:
        print(f"  diff {k} {col}: parse={want!r} db={got!r}")


def run_v1(con, docs, parses, *, with_codes: bool) -> bool:
    ok = True
    total = 0
    for fy, (doc_id, path, sha) in docs.items():
        actual = sha256_file(path)
        if sha != actual:
            print(f"V1 PB{fy}: workbook sha256 {actual} != jbook_documents {sha}")
            ok = False
        rep = compare_edition(con, parses[fy], fiscal_year=fy, doc_id=doc_id,
                              with_codes=with_codes)
        print_report(rep)
        ok = ok and report_ok(rep)
        total += rep["parse_rows"]
    print(f"V1: {'CLEAN' if ok else 'DIFFERENCES'} ({len(docs)} editions,"
          f" {total} parsed rows)")
    return ok


def snapshot_rows(con) -> dict[int, tuple]:
    cols = ", ".join(SNAPSHOT_COLUMNS) + ", line_item_code"
    return {
        rec[0]: rec
        for rec in con.execute(
            f"select {cols} from budget_lines where exhibit in ('P-1','P-1R')"
        ).fetchall()
    }


def verify_apply(before: dict[int, tuple], after: dict[int, tuple],
                 parse_by_key: dict[tuple, tuple[P1Row, int]],
                 editions) -> tuple[list[str], dict]:
    """The post-write invariants. Returns (problems, counts)."""
    problems: list[str] = []
    n = len(SNAPSHOT_COLUMNS)
    i_code = n  # line_item_code follows the snapshot columns

    def key_of(rec):
        return row_key(rec[1], rec[2], rec[3], rec[5], rec[6], rec[9], rec[11])

    in_scope = set(editions)
    changed_other = 0
    codes_set = 0
    codes_null_before = 0
    for rid, old in before.items():
        new = after.get(rid)
        if new is None:
            problems.append(f"row id {rid} disappeared")
            continue
        if new[:n] != old[:n]:
            changed_other += 1
            if changed_other <= 10:
                problems.append(f"row id {rid} changed outside line_item_code:"
                                f" {old[:n]!r} -> {new[:n]!r}")
        era_edition_p1 = old[1] == "P-1" and old[2] in in_scope
        if era_edition_p1:
            want = parse_by_key.get(key_of(old))
            if want is None:
                problems.append(f"row id {rid} {key_of(old)} has no parse row")
            elif new[i_code] is None or new[i_code] != want[0].line_item_code:
                problems.append(f"row id {rid} line_item_code {new[i_code]!r}"
                                f" != parse {want[0].line_item_code!r}")
            else:
                codes_set += 1
                if old[i_code] is None:
                    codes_null_before += 1
        elif new[i_code] != old[i_code]:
            problems.append(f"row id {rid} outside the era P-1 editions changed"
                            f" line_item_code {old[i_code]!r} -> {new[i_code]!r}")
    if changed_other > 10:
        problems.append(f"... {changed_other} rows changed outside line_item_code")

    before_keys = {key_of(rec) for rec in before.values()}
    expected_new = {k for k in parse_by_key if k not in before_keys}
    inserted = {rid: rec for rid, rec in after.items() if rid not in before}
    inserted_keys = {key_of(rec) for rec in inserted.values()}
    if inserted_keys != expected_new or len(inserted) != len(expected_new):
        problems.append(
            f"inserted {len(inserted)} row(s), expected {len(expected_new)}:"
            f" unexpected {sorted(inserted_keys - expected_new, key=repr)[:5]},"
            f" absent {sorted(expected_new - inserted_keys, key=repr)[:5]}")
    for rec in inserted.values():
        hit = parse_by_key.get(key_of(rec))
        if hit is None:
            continue
        r, doc_id = hit
        got = (rec[12], rec[10], rec[4], rec[7], list(rec[15] or []), rec[14],
               rec[13], rec[i_code])
        want = (r.amount_thousands, r.title, r.account_title,
                r.budget_activity_title, list(r.source_cells), r.source_sheet,
                doc_id, r.line_item_code)
        if got != want:
            problems.append(f"inserted row {key_of(rec)} {got!r} != parse {want!r}")

    era_codes: dict[tuple, set] = {}
    for rec in after.values():
        if rec[1] == "P-1" and rec[2] in in_scope and ERA_KEY_RE.match(rec[9]):
            era_codes.setdefault((rec[2], rec[9]), set()).add(rec[i_code])
    multi = {k: v for k, v in era_codes.items() if len(v) != 1 or None in v}
    if multi:
        problems.append(f"{len(multi)} era key(s) without exactly one non-null"
                        f" line_item_code: {sorted(multi.items(), key=repr)[:5]}")
    counts = {
        "snapshot": len(before), "after": len(after),
        "changed_other": changed_other, "codes_set": codes_set,
        "codes_null_before": codes_null_before, "inserted": len(inserted),
        "expected_new": len(expected_new), "era_keys": len(era_codes),
        "era_keys_one_code": len(era_codes) - len(multi),
    }
    return problems, counts


def apply(dsn: str, editions, *, dry_run: bool) -> int:
    with psycopg.connect(dsn) as con:
        docs = era_p1_documents(con, editions)
        con.rollback()
    # Parse every edition BEFORE any write: EraKeyConflict propagates here.
    parses = {fy: parse_p1_rollup(path, exhibit="P-1", fiscal_year=fy)
              for fy, (doc_id, path, sha) in docs.items()}
    with psycopg.connect(dsn) as con:
        if not has_line_item_code(con):
            print("apply: budget_lines.line_item_code is missing:"
                  " run `govbudget migrate` (021) first")
            return 2
        con.execute("lock table budget_lines in exclusive mode")
        if not run_v1(con, docs, parses, with_codes=True):
            con.rollback()
            print("apply: V1 not clean, nothing written (ROLLED BACK)")
            return 1
        before = snapshot_rows(con)
        print(f"apply: snapshot {len(before)} P-1/P-1R rows")
        parse_by_key: dict[tuple, tuple[P1Row, int]] = {}
        for fy, (doc_id, path, sha) in docs.items():
            n = write_p1_rows(con, parses[fy].rows, source_document_id=doc_id)
            print(f"apply: PB{fy} wrote {n} rows")
            for r in parses[fy].rows:
                parse_by_key[parse_key(r)] = (r, doc_id)
        after = snapshot_rows(con)
        problems, c = verify_apply(before, after, parse_by_key, editions)
        print(f"apply: pre-existing rows changed outside line_item_code:"
              f" {c['changed_other']}")
        print(f"apply: line_item_code equals the parse on {c['codes_set']}"
              f" pre-existing era-edition P-1 rows (null before:"
              f" {c['codes_null_before']})")
        print(f"apply: rows inserted: {c['inserted']} (expected"
              f" {c['expected_new']}); P-1/P-1R rows now {c['after']}")
        print(f"apply: era keys {c['era_keys']}, with exactly one"
              f" line_item_code: {c['era_keys_one_code']}")
        for p in problems[:20]:
            print(f"  PROBLEM {p}")
        if problems:
            con.rollback()
            print(f"apply: {len(problems)} problem(s): ROLLED BACK")
            return 1
        if dry_run:
            con.rollback()
            print("apply: dry run, every check passed: ROLLED BACK")
            return 0
        con.commit()
        print("apply: COMMITTED")
        return 0


def check(dsn: str, editions) -> int:
    with psycopg.connect(dsn) as con:
        con.read_only = True
        docs = era_p1_documents(con, editions)
        parses = {fy: parse_p1_rollup(path, exhibit="P-1", fiscal_year=fy)
                  for fy, (doc_id, path, sha) in docs.items()}
        ok = run_v1(con, docs, parses, with_codes=has_line_item_code(con))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="V1: parse vs Postgres, no write")
    mode.add_argument("--apply", action="store_true", help="transactional re-run")
    ap.add_argument("--dry-run", action="store_true",
                    help="with --apply: run every check, then roll back")
    ap.add_argument("--dsn", default=None, help="default: GOVBUDGET_PG_DSN")
    ap.add_argument("--editions", type=int, nargs="+", default=list(ERA_EDITIONS),
                    help="PB editions (default 2017-2023)")
    args = ap.parse_args(argv)
    dsn = args.dsn or config.PG_DSN
    if args.check:
        return check(dsn, args.editions)
    return apply(dsn, args.editions, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_s1_reload_era_p1.py -q`

Expected: `11 passed`.

- [ ] **Step 5: Run the jbooks suite and commit**

Run: `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks -q`

Expected: `455 passed, 2 skipped`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/scripts/era/s1_reload_era_p1.py GovBudget/tests/jbooks/test_s1_reload_era_p1.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era): S1 script — V1 no-write loader diff and a transactional re-run that rolls back on any difference (families S1, V1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Steps 6–19 are the proof and the shared write. Run them from
`/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget`
in one shell, in order; stop at the first output that differs from the expected one and
do not run any later step. Set once:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget
set -o pipefail
PROOFS=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
LIVE_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data
LIVE_PG=postgresql://localhost/govbudget
LOGS=$PROOFS/s1-logs
mkdir -p $LOGS
```

- [ ] **Step 6: V1 against the live database (read-only)**

```bash
GOVBUDGET_PG_DSN=$LIVE_PG uv run --project . python scripts/era/s1_reload_era_p1.py --check 2>&1 | tee $LOGS/01-v1-live.log
```

Expected (exit 0; the column does not exist yet):

```
V1 PB2017 P-1 (doc 189): parse 6783 rows | db 6783 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2018 P-1 (doc 261): parse 13377 rows | db 13377 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2019 P-1 (doc 271): parse 12857 rows | db 12857 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2020 P-1 (doc 282): parse 8775 rows | db 8775 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2021 P-1 (doc 292): parse 10050 rows | db 10050 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2022 P-1 (doc 302): parse 2979 rows | db 2979 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2023 P-1 (doc 312): parse 2901 rows | db 2901 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1: CLEAN (7 editions, 57722 parsed rows)
```

- [ ] **Step 7: Snapshot S0**

Check `date +%M` is not 15–20 (the hourly SAM job writes `data/parquet/sam` at :17; the
tool also refuses). Then:

```bash
GOVBUDGET_DATA=$LIVE_DATA GOVBUDGET_PG_DSN=$LIVE_PG uv run --project . python -m govbudget proof snapshot --out $PROOFS/s0 --scratch-db govbudget_proof_s0 2>&1 | tee $LOGS/02-snapshot.log
ls $PROOFS/s0/snapshot.json $PROOFS/s0/env.sh
```

Expected: exit 0; both files listed. `govbudget_proof_s0` now holds a restore of the live
database (schema_migrations 001–020, no `line_item_code`).

- [ ] **Step 8: Export Z — S0 as production sees it (no rebuild)**

```bash
cp -c -R $PROOFS/s0 $PROOFS/s0-Z
( source $PROOFS/s0/env.sh $PROOFS/s0-Z && uv run --project . python -m govbudget export-site ) 2>&1 | tee $LOGS/03-export-Z.log
```

Expected: exit 0; the log ends with `budget PDF receipts: …` and
`export-site: … datasets, … citations, … -> $PROOFS/s0-Z/site`. Z reads the S0 lake in
its heap order through the S0 warehouse (built 2026-09-27 02:45 by the same dbt code:
no `dbt/` commit since 2026-09-26 21:56).

- [ ] **Step 9: Export A — S0 plus migration 021, re-exported and rebuilt under this branch**

```bash
cp -c -R $PROOFS/s0 $PROOFS/s0-A
( source $PROOFS/s0/env.sh $PROOFS/s0-A \
  && uv run --project . python -m govbudget migrate \
  && uv run --project . python -m govbudget jbooks export-facts \
  && uv run --project . python -m govbudget build \
  && uv run --project . python -m govbudget export-site ) 2>&1 | tee $LOGS/04-A.log
```

Expected: exit 0; `migrations applied: ['021_budget_lines_line_item_code.sql']`;
`exported: announcement_link_reviews.parquet, award_adjudications.parquet, budget_line_awards.parquet, budget_lines.parquet, detail_narratives.parquet, details.parquet, documents.parquet, program_family.parquet, program_lineage.parquet`;
dbt ends `Completed successfully`; the `export-site:` summary line.

- [ ] **Step 10: Export B — A plus the S1 re-run**

Z, A and B share one scratch database: every `source $PROOFS/s0/env.sh <run dir>` points
`GOVBUDGET_PG_DSN` at `govbudget_proof_s0`, which Step 9 migrates and this step writes. Run
Steps 8, 9 and 10 in that order. The `migrate` at the head of this chain is idempotent (021
is already recorded after Step 9), so this step no longer depends on Step 9 having
migrated the database; without it, a run of this step without Step 9 would stop at
`s1_reload_era_p1.py --apply` with exit 2 and ``run `govbudget migrate` (021) first``.
To retry this step after a failure before `apply: COMMITTED`, first `rm -rf $PROOFS/s0-B`
(`cp -c -R` into an existing directory nests the copy). Once the apply has committed, the
scratch database holds the S1 codes, so repeating Step 8, 9 or 10 means starting again
from Step 7 with a fresh snapshot; the snapshot tool refuses an existing out dir or
database, so first run `/opt/homebrew/opt/postgresql@17/bin/dropdb govbudget_proof_s0` and
`rm -rf $PROOFS/s0 $PROOFS/s0-Z $PROOFS/s0-A $PROOFS/s0-B`.

```bash
cp -c -R $PROOFS/s0 $PROOFS/s0-B
( source $PROOFS/s0/env.sh $PROOFS/s0-B \
  && uv run --project . python -m govbudget migrate \
  && uv run --project . python scripts/era/s1_reload_era_p1.py --check \
  && uv run --project . python scripts/era/s1_reload_era_p1.py --apply \
  && uv run --project . python -m govbudget jbooks export-facts \
  && uv run --project . python -m govbudget build \
  && uv run --project . python -m govbudget export-site ) 2>&1 | tee $LOGS/05-B.log
```

Expected: exit 0. `migrations applied: none (up to date)` (the CLI prints that text, not
`[]`, for an empty list: `src/govbudget/cli.py:110`). The check prints the seven Step 6 lines, each ending
`line_item_code: null <n>, equal 0, differ 0` with `<n>` the edition's row count (6783,
13377, 12857, 8775, 10050, 2979, 2901), and `V1: CLEAN (7 editions, 57722 parsed rows)`;
the apply prints the same V1 block again (it re-runs V1 under its lock), then:

```
apply: snapshot 84463 P-1/P-1R rows
apply: PB2017 wrote 6783 rows
apply: PB2018 wrote 13377 rows
apply: PB2019 wrote 12857 rows
apply: PB2020 wrote 8775 rows
apply: PB2021 wrote 10050 rows
apply: PB2022 wrote 2979 rows
apply: PB2023 wrote 2901 rows
apply: pre-existing rows changed outside line_item_code: 0
apply: line_item_code equals the parse on 57722 pre-existing era-edition P-1 rows (null before: 57722)
apply: rows inserted: 0 (expected 0); P-1/P-1R rows now 84463
apply: era keys 6927, with exactly one line_item_code: 6927
apply: COMMITTED
```

then the export-facts, dbt and export-site lines as in Step 9.

- [ ] **Step 11: Site diffs — Z = A (order and rebuild are inert), A = B (S1 is inert)**

```bash
uv run --project . python -m govbudget proof diff $PROOFS/s0-Z/site $PROOFS/s0-A/site 2>&1 | tee $LOGS/06-diff-Z-A.log
uv run --project . python -m govbudget proof diff $PROOFS/s0-A/site $PROOFS/s0-B/site 2>&1 | tee $LOGS/07-diff-A-B.log
```

Expected: both logs end `proof diff: EQUAL` (zero changed, zero only-in-A, zero
only-in-B; build stamps masked). If either says `DIFFERENT`: stop. Do not run Steps 13–19;
the report names the files that moved — a consumer depends on lake row order (Z ≠ A) or on
`line_item_code` (A ≠ B), which the spec says cannot happen; take it back to the owner.

- [ ] **Step 12: Lake check — only the column changed**

```bash
uv run --project . python - $PROOFS/s0/parquet/jbooks $PROOFS/s0-A/parquet/jbooks $PROOFS/s0-B/parquet/jbooks <<'EOF' 2>&1 | tee $LOGS/08-lake.log
import sys
from pathlib import Path

import duckdb

S0, A, B = (Path(p) for p in sys.argv[1:4])
OLD = ("exhibit, fiscal_year, account, account_title, organization, budget_activity,"
       " budget_activity_title, pe_bli, title, amount_type, amount_thousands,"
       " source_document_id, source_sheet, source_cells")
ERA = r"regexp_matches(pe_bli, '^\d{4}[A-Z]-[A-Z]+-L')"
con = duckdb.connect()


def q(sql):
    return con.execute(sql).fetchall()


def bl(d):
    return f"read_parquet('{d}/budget_lines.parquet')"


def multiset(rows):
    return sorted(map(repr, rows))


s0, a, b = (q(f"select {OLD} from {bl(d)}") for d in (S0, A, B))
print(f"rows: S0 {len(s0)} | A {len(a)} | B {len(b)}")
print("A == S0 on the 14 S0 columns as a multiset:", multiset(a) == multiset(s0))
print("B == A on the 14 S0 columns, row for row:", b == a)
for name, d in (("A", A), ("B", B)):
    null, coded = q(f"select count(*) filter (where line_item_code is null),"
                    f" count(*) filter (where line_item_code is not null)"
                    f" from {bl(d)} where exhibit = 'P-1' and {ERA}")[0]
    off = q(f"select count(*) from {bl(d)} where exhibit in ('P-1', 'P-1R')"
            f" and not {ERA} and line_item_code is distinct from pe_bli")[0][0]
    r1 = q(f"select count(*) from {bl(d)} where exhibit = 'R-1'"
           f" and line_item_code is not null")[0][0]
    print(f"{name}: era P-1 rows null {null}, coded {coded} | non-era P-1/P-1R"
          f" rows whose code != pe_bli {off} | coded R-1 rows {r1}")
ca, cb = (q(f"select line_item_code from {bl(d)}") for d in (A, B))
print("rows whose line_item_code differs A -> B:", sum(1 for x, y in zip(ca, cb) if x != y))
others = sorted(p.name for p in S0.glob("*.parquet") if p.name != "budget_lines.parquet")
same = all(
    multiset(q(f"select * from read_parquet('{x}/{n}')"))
    == multiset(q(f"select * from read_parquet('{y}/{n}')"))
    for n in others for x, y in ((S0, A), (A, B))
)
print(f"other jbooks parquets equal as multisets, S0 = A = B: {same} ({len(others)} files)")
EOF
```

Expected:

```
rows: S0 159494 | A 159494 | B 159494
A == S0 on the 14 S0 columns as a multiset: True
B == A on the 14 S0 columns, row for row: True
A: era P-1 rows null 57722, coded 0 | non-era P-1/P-1R rows whose code != pe_bli 0 | coded R-1 rows 0
B: era P-1 rows null 0, coded 57722 | non-era P-1/P-1R rows whose code != pe_bli 0 | coded R-1 rows 0
rows whose line_item_code differs A -> B: 57722
other jbooks parquets equal as multisets, S0 = A = B: True (8 files)
```

- [ ] **Step 13: Confirm migrate will apply only 021 to the live database (read-only)**

```bash
uv run --project . python - <<'EOF'
import psycopg
from govbudget.jbooks.db import MIGRATIONS_DIR
with psycopg.connect("postgresql://localhost/govbudget") as con:
    con.read_only = True
    done = {r[0] for r in con.execute("select name from schema_migrations")}
print(sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql") if p.name not in done))
EOF
```

Expected: `['021_budget_lines_line_item_code.sql']`.

- [ ] **Step 14: Live write — migrate, rehearse, apply, re-check (shared Postgres)**

```bash
export GOVBUDGET_DATA=$LIVE_DATA GOVBUDGET_PG_DSN=$LIVE_PG
uv run --project . python -m govbudget migrate 2>&1 | tee $LOGS/09-live-migrate.log
uv run --project . python scripts/era/s1_reload_era_p1.py --apply --dry-run 2>&1 | tee $LOGS/10-live-dry-run.log
uv run --project . python scripts/era/s1_reload_era_p1.py --apply 2>&1 | tee $LOGS/11-live-apply.log
uv run --project . python scripts/era/s1_reload_era_p1.py --check 2>&1 | tee $LOGS/12-live-v1-after.log
```

Expected: `migrations applied: ['021_budget_lines_line_item_code.sql']`; the dry run prints
the Step 10 V1 and apply blocks with the last line `apply: dry run, every check passed: ROLLED BACK`;
the apply prints the same blocks ending `apply: COMMITTED`; the final check prints the
seven V1 lines with `line_item_code: null 0, equal <n>, differ 0` where `<n>` is the
edition's row count (6783, 13377, 12857, 8775, 10050, 2979, 2901) and
`V1: CLEAN (7 editions, 57722 parsed rows)`.

- [ ] **Step 15: Live write — lake export (shared lake)**

```bash
m=$((10#$(date +%M))); if [ $m -ge 15 ] && [ $m -le 20 ]; then echo "SAM write window: wait until :21 and re-run this step"; else uv run --project . python -m govbudget jbooks export-facts 2>&1 | tee $LOGS/13-live-export-facts.log; fi
```

Expected: `exported: announcement_link_reviews.parquet, …, program_lineage.parquet` (the
nine names of Step 9). No live `govbudget build` here: the live warehouse's views select
by name and keep working; Task 13 is the first branch build on the live lake.

- [ ] **Step 16: The live result equals the rehearsal**

```bash
uv run --project . python - $LIVE_PG postgresql://localhost/govbudget_proof_s0 $LIVE_DATA/parquet/jbooks $PROOFS/s0-B/parquet/jbooks <<'EOF' 2>&1 | tee $LOGS/14-live-equals-rehearsal.log
import sys

import duckdb
import psycopg

LIVE_DSN, REHEARSAL_DSN, LIVE_LAKE, REHEARSAL_LAKE = sys.argv[1:5]
COLS = ("id, exhibit, fiscal_year, account, account_title, organization,"
        " budget_activity, budget_activity_title, line_number, pe_bli, title,"
        " amount_type, amount_thousands, source_document_id, source_sheet,"
        " source_cells, line_item_code")


def pg_rows(dsn):
    with psycopg.connect(dsn) as con:
        con.read_only = True
        return con.execute(
            f"select {COLS} from budget_lines where exhibit in ('P-1', 'P-1R')"
            " order by id").fetchall()


live, reh = pg_rows(LIVE_DSN), pg_rows(REHEARSAL_DSN)
print(f"P-1/P-1R rows: live {len(live)} | rehearsal {len(reh)} |"
      f" identical (17 columns, by id): {live == reh}")
con = duckdb.connect()
l, r = (con.execute(f"select * from read_parquet('{p}/budget_lines.parquet')").fetchall()
        for p in (LIVE_LAKE, REHEARSAL_LAKE))
print(f"lake budget_lines: live {len(l)} rows | rehearsal {len(r)} rows |"
      f" identical row for row: {l == r}")
EOF
```

Expected:

```
P-1/P-1R rows: live 84463 | rehearsal 84463 | identical (17 columns, by id): True
lake budget_lines: live 159494 rows | rehearsal 159494 rows | identical row for row: True
```

- [ ] **Step 17: Run the whole test suite once more**

Step 14 exported the live lake and database into this shell; no test may see them:

Run: `unset GOVBUDGET_DATA GOVBUDGET_PG_DSN GOVBUDGET_DUCKDB; GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q`

Expected: `3557 passed, 42 skipped` (measured on a copy of this branch with Tasks 6–8
applied; Tasks 1–5 add their own tests on top, so the requirement is `0 failed`).

- [ ] **Step 18: Write the proof note and commit it**

```bash
NOTE=docs/superpowers/reviews/families-s1-proof.md
{
  echo "# Families piece 1 — S1 proof (procurement history before FY2024, Task 8)"
  echo
  echo "Spec: docs/superpowers/specs/2026-10-02-era-procurement-history-design.md §8 V1, §9 S1."
  echo "Code: $(git rev-parse HEAD). Snapshot: .proofs/s0 (snapshot.json sha256 $(shasum -a 256 $PROOFS/s0/snapshot.json | cut -d' ' -f1)); scratch database govbudget_proof_s0."
  echo
  echo "Z = the S0 snapshot exported as production reads it (S0 warehouse, S0 lake in heap order)."
  echo "A = S0 + migration 021, then jbooks export-facts (id order), govbudget build, export-site."
  echo "B = A + scripts/era/s1_reload_era_p1.py --apply, then the same three steps."
  echo "Live = the shared database and lake after the same migrate/apply/export-facts."
  for f in $LOGS/*.log; do
    echo; echo "## $(basename $f .log)"; echo; echo '```'; tail -n 25 "$f"; echo '```'
  done
} > $NOTE
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/docs/superpowers/reviews/families-s1-proof.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(families): S1 proof — every era P-1 row carries its printed code, site export unchanged (Z = A = B)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget
```

- [ ] **Step 19: Clean up the run clones and the scratch database**

```bash
rm -rf $PROOFS/s0-Z $PROOFS/s0-A $PROOFS/s0-B
/opt/homebrew/opt/postgresql@17/bin/dropdb govbudget_proof_s0
ls $PROOFS/s0/pg/
```

Expected: the `ls` lists the S0 dump (kept: it is the pristine pre-S1 database, cited by
the proof note); `.proofs/s0` stays until the release (Task 23).

---
