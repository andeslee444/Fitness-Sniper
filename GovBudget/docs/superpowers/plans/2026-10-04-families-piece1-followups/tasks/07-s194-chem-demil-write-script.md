<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G2 (2026-10-13). -->

### Task 7: The Chem Demil write script `s194_chem_demil.py` (`--check` / `--dry-run` / `--apply` / `--revert`); retire `clean_junk_pe_bli.py` (#194)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §4.4 (the script's modes, one transaction under `LOCK budget_lines IN EXCLUSIVE MODE`, the three writes under Q1 (a), the post-write checks, roll back on any failure, no migration, the new dbt test `assert_budget_lines_route_safe_pe_bli`), §4.1 (the 16 stale rows), §2.2 Q8 (re-key the 8 O&M rows in place, ids kept, an explicit exception to piece 1's "never re-key `pe_bli`", which was about era keys; delete the 8 RDT&E rows; none of their fact ids is published) and Q9 (retire `scripts/clean_junk_pe_bli.py` with a dated note), §2.3 Q24 (b) as the owner chose it on 2026-10-04: a `--revert` mode that restores the exact pre-write rows, with its own test and rehearsal; release 1's abort path uses it.

**Files:**
- Create: `scripts/era/s194_chem_demil.py`
- Create: `tests/jbooks/test_s194_chem_demil.py`
- Create: `dbt/tests/assert_budget_lines_route_safe_pe_bli.sql`
- Create: `tests/test_budget_lines_route_safe_sql.py`
- Delete: `scripts/clean_junk_pe_bli.py`
- Modify: `docs/superpowers/ROADMAP.md` — the findings-log entry "Reject junk at the loader, not just at the exporter (audit-fix 2026-07-05)" (anchor on its last line, `  masks bad data from the UI is belt; rejecting it at ingest is braces.`, about line 1019)
- Local scratch only (never committed, never the live server): database `s194_rehearsal` on the throwaway cluster 127.0.0.1:55432 and `$GOVBUDGET_PROOFS/fu-s194-rehearsal/` (Step 6, removed at its end)

**Interfaces:**
Consumes: Task 6 (`parse_p1_rollup`, `verify_r1_restatements`, `write_p1_rows`, `P1Row`, `P1Parse`; `route_safe_codes.P1_R1_RESTATEMENTS`, `load_route_safe_codes`, `P1RestatementMismatch`, `UnsafeBudgetLineCode`; the committed seed); Task 3 (`P1KeyConflict`); Task 1's throwaway cluster.
Produces (Tasks 21 and 22 run it; nothing else writes the 0390D rows):
- `scripts/era/s194_chem_demil.py`, exactly one mode of `--check`, `--dry-run`, `--apply`, `--revert`; options `--revert-file PATH` (required by `--apply`, which refuses an existing file, and by `--revert`), `--dsn` (default `config.PG_DSN`), `--editions` (default 2024 2025 2026). Exit 0 / 1 (a difference, a refusal, a rollback) / 2 (usage: a missing or existing revert file). Module API: `EDITIONS`, `ROW_COLUMNS` (the 17 `budget_lines` columns in table order), `REVERT_SCHEMA = 1`, `p1_documents(con, editions)`, `plan_edition(con, parsed, *, fiscal_year, doc_id) -> dict` (`rekey: [(id, page_key)]`, `delete: [id]`, `insert: [P1Row]`, `other: [str]`), `run_check(con, docs, parses) -> (bool, plans)`, `check(dsn, editions) -> int`, `apply(dsn, editions, *, dry_run, revert_file) -> int`, `revert(dsn, revert_file) -> int`, `record_sha256(record) -> str` (sha256 of the revert record's canonical JSON without its `rows_sha256` field), `out_of_scope(record) -> [str]` (the `before` rows #194 never writes), `untouched_digest(con, excluded_ids) -> [count, md5]`, `main(argv) -> int`.
- Printed lines the release tasks match: `check PB<yyyy> P-1 (doc <id>): parse <n> | db <n> | re-key <n> | insert <n> | delete <n> | restated rows checked against the R-1 <n> | other differences <n>`; `check: CLEAN, the only differences are #194's (re-key 8, insert 4, delete 8)` / `check: CLEAN, nothing left to write` / `check: DIFFERENCES`; `apply: re-keyed 8, deleted 8, inserted 4; untouched rows <n> (digest equal); route-unsafe pe_bli left 0`; `apply: COMMITTED (revert file <path>)` / `apply: dry run, every check passed: ROLLED BACK` / `apply: nothing to write (#194 is already applied)`; `revert: restored 16 pre-write row(s) (re-keyed 8 back, re-inserted 8, removed 4); COMMITTED` / `revert: the database already holds the pre-write rows; nothing to revert` / `revert: the database moved since --apply (<n> problem(s)); nothing written` / `revert: <file> sha256 does not match its contents; nothing written` / `revert: <file> names <n> row(s) outside #194's scope; nothing written`; `s194: REFUSED — <ExceptionName>: <message>`.
- The revert file (JSON, written atomically before COMMIT): `schema`, `database` (`current_database()`; `--revert` refuses any other database), `written_at`, `editions`, `columns`, `before` (the 16 pre-write rows, every column, amounts as decimal strings), `rekeyed` (`{"<id>": "0390DOM"}`), `deleted_ids`, `inserted` (the 4 new rows as written), `untouched_digest` (`[row count, md5]` of every other row), `rows_sha256` (`record_sha256` of all of the above; spec §4.4's "the rows' sha256"). `--revert` checks `rows_sha256` and `out_of_scope` before it opens the database (spec §4.4 step 1). After `--revert`, Postgres is pre-write row for row (ids included; the id sequence keeps its advance); the lake follows only after `jbooks export-facts` and a selective dbt build (release task's abort path).
- dbt singular test `assert_budget_lines_route_safe_pe_bli` (fails on the live lake until Task 22's `--apply` plus `jbooks export-facts`: the 16 stale rows are in `data/parquet/jbooks/budget_lines.parquet` today).

Measured for this task (2026-10-13, read-only on live Postgres; the rehearsal on a `pg_dump -t budget_lines -t jbook_documents` copy restored into the throwaway cluster):
- `budget_lines`: 159,903 rows, `max(id)` 581,201, `md5(string_agg(b::text, E'\n' order by id))` = `4174ef8314daf8a822289c951e834b78`. P-1 0390D rows of PB2024–PB2026: PB2024 10 (ids 349016–349025), PB2025 7 (the 6 stale plus `FY2024CR` id 47739, "Adj to Match Continuing Resolution", a route-safe line the script never touches), PB2026 0. The P-1 rollup documents are ids 76 (PB2024), 152 (PB2025), 1 (PB2026).
- A scratch run of this script's `--check` on the live database (with Tasks 3, 4a and 6 applied to a scratch tree):

```
check PB2024 P-1 (doc 76): parse 4580 | db 4585 | re-key 5 | insert 0 | delete 5 | restated rows checked against the R-1 5 | other differences 0
check PB2025 P-1 (doc 152): parse 2429 | db 2432 | re-key 3 | insert 0 | delete 3 | restated rows checked against the R-1 3 | other differences 0
check PB2026 P-1 (doc 1): parse 3167 | db 3163 | re-key 0 | insert 4 | delete 0 | restated rows checked against the R-1 4 | other differences 0
check: CLEAN, the only differences are #194's (re-key 8, insert 4, delete 8)
```

  Each stale O&M row equals its parse twin in every column but `pe_bli` (amount, title, account title, budget activity title, source cells, sheet, document, `line_item_code`), which is what lets the re-key keep the row's id.
- On the restored copy: `--dry-run` printed `apply: re-keyed 8, deleted 8, inserted 4; untouched rows 159887 (digest equal); route-unsafe pe_bli left 0` then `ROLLED BACK`; `--apply` the same line then `COMMITTED`, after which the copy's 0390DOM ids were 47733–47735, 349016–349020 and four new ids, no route-unsafe `pe_bli` remained and `--check` printed `check: CLEAN, nothing left to write`; `--revert` printed `revert: restored 16 pre-write row(s) (re-keyed 8 back, re-inserted 8, removed 4); COMMITTED` and the table hashed to `159903 4174ef8314daf8a822289c951e834b78` again; a second `--revert` printed `nothing to revert`.
- The `rows_sha256` and scope refusals were added at the 2026-10-13 plan review (spec §4.4: "checks the file's sha256"; its tests refuse "a changed in-scope row, a pre-image whose sha256 does not match, and a pre-image taken from another database"). The script and tests below, applied to a scratch tree of HEAD plus Tasks 1–7 (`.superpowers/sdd/2026-10-04-piece1-followups/work/fixpass/`), gave `21 passed` on the 55432 cluster and `All checks passed!` from ruff.
- `scripts/clean_junk_pe_bli.py` is referenced by nothing but its own docstring and ROADMAP line 1017 (`grep -rn clean_junk_pe_bli src tests scripts site/scripts site/src dbt docs/superpowers/ROADMAP.md docs/superpowers/LAUNCH.md`). It deleted PB2026's 8 rows on 2026-07-05 (481bba088).

- [ ] **Step 1: Write the failing tests**

Create `tests/jbooks/test_s194_chem_demil.py`:

```python
"""scripts/era/s194_chem_demil.py (families piece-1 follow-ups design §4.4,
#194; owner Q1 (a), Q2, Q8, Q24 (b)).

The database starts in production's pre-write shape: PB2024 and PB2025 hold
0390D's two Chem Demilitarization lines under the printed codes 'O&M' and
'RDT&E' (the stale keys the 2026-07-05 guard never cleaned), PB2026 holds
neither (that cleanup deleted them), and each edition's R-1 carries 0708081D
and 0708083D, which the RDT&E line restates. The values are the live ones
(budget_lines ids 349016-349025, 47733-47738, 1031-1036; PB2026 P-1 rows
303-304), two amount columns per edition.
"""
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path

import psycopg
import pytest
from openpyxl import Workbook

from govbudget.jbooks.p1_loader import parse_p1_rollup, write_p1_rows

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "s194_chem_demil", ROOT / "scripts" / "era" / "s194_chem_demil.py")
s194 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s194)

ID_HEADERS = ["Account", "Account Title", "Organization", "Budget Activity",
              "Budget Activity Title", "Line Number", "BSA", "Budget SubActivity (BSA) Title",
              "Budget Line Item", "Budget Line Item (BLI) Title", "Cost Type",
              "Cost Type Title", "Add/Non-Add"]
# edition -> the two FY amount headers its P-1 prints (PB2025's CR column
# keeps its footnote '*', as the real workbook does)
FY_HEADERS = {
    2024: ("FY 2022 Actuals", "FY 2024 Request"),
    2025: ("FY 2023 Actuals", "FY 2024 PB Request with CR Adjustments"),
    2026: ("FY 2024 Actuals", "FY 2026 Total"),
}
# edition -> (ordinary BLI, O&M, RDT&E) amounts in the two columns
P1_VALUES = {
    2024: ((100, 200), (66587, 89284), (1026665, 1002560)),
    2025: ((110, 210), (84612, 89284), (975206, 1002560)),
    2026: ((120, 220), (87404, 3243), (1002560, 210039)),
}
# edition -> [(pe, amount_type, amount)] of the R-1 0390D rows
R1_ROWS = {
    2024: [("0708081D", "fy_2022_actuals", 6120), ("0708081D", "fy_2024_request", 2093),
           ("0708083D", "fy_2022_actuals", 1020545), ("0708083D", "fy_2024_request", 1000467)],
    2025: [("0708081D", "fy_2023_actuals", 3464),
           ("0708081D", "fy_2024_pb_request_with_cr_amounts", 2093),
           ("0708083D", "fy_2023_actuals", 971742),
           ("0708083D", "fy_2024_pb_request_with_cr_amounts", 1000467)],
    2026: [("0708081D", "fy_2024_actuals", 2093), ("0708083D", "fy_2024_actuals", 1000467),
           ("0708083D", "fy_2026_total", 210039)],
}
CHEM = ("0390D", "Chemical Agents and Munitions Destruction, Defense", "A")


def _workbook(path: Path, fy: int) -> Path:
    a, b = FY_HEADERS[fy]
    star = "*" if fy == 2025 else ""
    ordinary, om, rdte = P1_VALUES[fy]
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1"
    ws.append(["Total of Displayed Rows"])
    ws.append(ID_HEADERS + [f"{a} Quantity", f"{a} Amount", f"{b} Quantity", f"{b} Amount{star}"])
    ws.append(["0300D", "Procurement, Defense-Wide", "CBDP", "03", "Chem/Bio Defense", "120",
               "1", "CBDP", "7001SA1000", "CB Situational Awareness", "A", "Weapon System Cost",
               "Add", "", ordinary[0], "", ordinary[1]])
    ws.append([*CHEM, "01", "Operation and maintenance", "1", "", "", "O&M",
               "Chem Demilitarization - O&M", "A", "Weapon System Cost", "Add", "", om[0], "", om[1]])
    ws.append([*CHEM, "02", "Research, Development, Test, and Evaluation", "2", "", "", "RDT&E",
               "Chem Demilitarization - RDT&E", "A", "Weapon System Cost", "Add",
               "", rdte[0], "", rdte[1]])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def _register(con, fy, title, path=None):
    sha = hashlib.sha256(path.read_bytes()).hexdigest() if path else None
    return con.execute(
        "insert into jbook_documents (org, exhibit_family, fiscal_year, title, source_url,"
        " file_path, sha256, status) values ('DoD', 'rollup', %s, %s, %s, %s, %s,"
        " 'downloaded') returning id",
        (fy, title, f"https://example.test/fy{fy}/{title}", str(path or f"/x/{fy}/{title}"),
         sha)).fetchone()[0]


@pytest.fixture()
def prod(pg_dsn, tmp_path):
    """Production's pre-write state; returns {edition: (doc_id, workbook)}."""
    docs = {}
    with psycopg.connect(pg_dsn) as con:
        for fy in (2024, 2025, 2026):
            p = _workbook(tmp_path / f"fy{fy}" / "p1_display.xlsx", fy)
            docs[fy] = (_register(con, fy, "p1_display.xlsx", p), p)
            r1_doc = _register(con, fy, "r1_display.xlsx")
            for pe, at, amt in R1_ROWS[fy]:
                con.execute(
                    "insert into budget_lines (exhibit, fiscal_year, account, account_title,"
                    " organization, budget_activity, pe_bli, title, amount_type,"
                    " amount_thousands, source_document_id, source_sheet, source_cells)"
                    " values ('R-1', %s, '0390D', %s, 'A', '02', %s, 'x', %s, %s, %s,"
                    " 'Exhibit R-1', '{J9}')", (fy, CHEM[1], pe, at, amt, r1_doc))
        for fy, (doc_id, p) in docs.items():
            parsed = parse_p1_rollup(p, exhibit="P-1", fiscal_year=fy)
            rows = [r for r in parsed.rows if r.pe_bli != "0390DOM"]
            if fy != 2026:  # the stale keys; PB2026's were deleted on 2026-07-05
                rows += [dataclasses.replace(r, pe_bli="O&M")
                         for r in parsed.rows if r.pe_bli == "0390DOM"]
                rows += list(parsed.restated)
            write_p1_rows(con, rows, source_document_id=doc_id)
    return docs


def _snapshot(pg_dsn):
    with psycopg.connect(pg_dsn) as con:
        return con.execute(
            f"select {', '.join(s194.ROW_COLUMNS)} from budget_lines order by id").fetchall()


def _run(pg_dsn, *args):
    return s194.main([*map(str, args), "--dsn", pg_dsn])


def test_check_sorts_every_difference_into_194s_three_kinds(pg_dsn, prod, capsys):
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--check") == 0
    out = capsys.readouterr().out
    assert ("check PB2024 P-1 (doc %d): parse 4 | db 6 | re-key 2 | insert 0 | delete 2 |"
            " restated rows checked against the R-1 2 | other differences 0" % prod[2024][0]) in out
    assert "check PB2025 P-1 (doc %d): parse 4 | db 6 | re-key 2 | insert 0 | delete 2" % (
        prod[2025][0]) in out
    assert "check PB2026 P-1 (doc %d): parse 4 | db 2 | re-key 0 | insert 2 | delete 0" % (
        prod[2026][0]) in out
    assert "check: CLEAN, the only differences are #194's (re-key 4, insert 2, delete 4)" in out
    assert _snapshot(pg_dsn) == before


@pytest.mark.parametrize("tamper, expect", [
    ("update budget_lines set amount_thousands = 101 where pe_bli = '7001SA1000'"
     " and fiscal_year = 2024 and amount_type = 'fy_2022_actuals'", "diff ("),
    ("update budget_lines set title = 'Chem Demil O&M' where pe_bli = 'O&M'"
     " and fiscal_year = 2025 and amount_type = 'fy_2023_actuals'", "stale ("),
    ("insert into budget_lines (exhibit, fiscal_year, account, organization, budget_activity,"
     " pe_bli, title, amount_type, amount_thousands, source_document_id)"
     " select 'P-1', 2024, '0300D', 'CBDP', '03', 'A/B', 'x', 'fy_2022_actuals', 1, id"
     " from jbook_documents where fiscal_year = 2024 and title = 'p1_display.xlsx'",
     "extra in db: ('0300D', 'CBDP', '03', 'A/B', 'fy_2022_actuals')"),
])
def test_check_fails_on_any_other_difference(pg_dsn, prod, capsys, tamper, expect):
    with psycopg.connect(pg_dsn) as con:
        con.execute(tamper)
    assert _run(pg_dsn, "--check") == 1
    out = capsys.readouterr().out
    assert expect in out and "check: DIFFERENCES" in out


def test_apply_writes_exactly_194_and_records_the_pre_write_rows(pg_dsn, prod, tmp_path, capsys):
    before = {r[0]: r for r in _snapshot(pg_dsn)}
    stale = {i: r for i, r in before.items() if r[9] in ("O&M", "RDT&E")}
    revert_file = tmp_path / "revert.json"
    assert _run(pg_dsn, "--apply", "--revert-file", revert_file) == 0
    out = capsys.readouterr().out
    assert ("apply: re-keyed 4, deleted 4, inserted 2; untouched rows %d (digest equal);"
            " route-unsafe pe_bli left 0" % (len(before) - 8)) in out
    assert f"apply: COMMITTED (revert file {revert_file})" in out
    after = {r[0]: r for r in _snapshot(pg_dsn)}
    for i, r in stale.items():
        if r[9] == "O&M":       # re-keyed in place: same id, only pe_bli moves
            assert after[i] == r[:9] + ("0390DOM",) + r[10:]
        else:                   # the restatement is gone
            assert i not in after
    new = [r for i, r in after.items() if i not in before]
    assert sorted((r[2], r[9], r[11], r[12], r[16]) for r in new) == [
        (2026, "0390DOM", "fy_2024_actuals", 87404, "O&M"),
        (2026, "0390DOM", "fy_2026_total", 3243, "O&M")]
    assert {i: r for i, r in after.items() if i in before and i not in stale} == {
        i: r for i, r in before.items() if i not in stale}
    rec = json.loads(revert_file.read_text())
    assert rec["database"] == pg_dsn.rsplit("/", 1)[1]
    assert sorted(r[0] for r in rec["before"]) == sorted(stale)
    assert (len(rec["rekeyed"]), len(rec["deleted_ids"]), len(rec["inserted"])) == (4, 4, 2)
    assert rec["rows_sha256"] == s194.record_sha256(rec)
    assert _run(pg_dsn, "--check") == 0
    assert "check: CLEAN, nothing left to write" in capsys.readouterr().out


def test_a_second_apply_writes_nothing(pg_dsn, prod, tmp_path, capsys):
    assert _run(pg_dsn, "--apply", "--revert-file", tmp_path / "one.json") == 0
    snap = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply", "--revert-file", tmp_path / "two.json") == 0
    assert "apply: nothing to write (#194 is already applied)" in capsys.readouterr().out
    assert _snapshot(pg_dsn) == snap and not (tmp_path / "two.json").exists()


def test_dry_run_changes_nothing(pg_dsn, prod, capsys):
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--dry-run") == 0
    assert "apply: dry run, every check passed: ROLLED BACK" in capsys.readouterr().out
    assert _snapshot(pg_dsn) == before


def test_apply_needs_a_new_revert_file(pg_dsn, prod, tmp_path, capsys):
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply") == 2
    taken = tmp_path / "taken.json"
    taken.write_text("{}")
    assert _run(pg_dsn, "--apply", "--revert-file", taken) == 2
    out = capsys.readouterr().out
    assert "--revert-file is required" in out and "refusing to overwrite a revert file" in out
    assert _snapshot(pg_dsn) == before


def test_apply_refuses_when_the_check_is_not_clean(pg_dsn, prod, tmp_path, capsys):
    with psycopg.connect(pg_dsn) as con:
        con.execute("update budget_lines set amount_thousands = 101 where pe_bli = '7001SA1000'"
                    " and fiscal_year = 2026 and amount_type = 'fy_2024_actuals'")
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply", "--revert-file", tmp_path / "r.json") == 1
    assert "apply: check not clean, nothing written (ROLLED BACK)" in capsys.readouterr().out
    assert _snapshot(pg_dsn) == before and not (tmp_path / "r.json").exists()


def test_apply_rolls_back_when_a_write_touches_another_row(
        pg_dsn, prod, tmp_path, capsys, monkeypatch):
    real = s194.write_p1_rows

    def stray(con, rows, *, source_document_id):
        n = real(con, rows, source_document_id=source_document_id)
        con.execute("update budget_lines set title = 'moved' where pe_bli = '7001SA1000'")
        return n

    monkeypatch.setattr(s194, "write_p1_rows", stray)
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply", "--revert-file", tmp_path / "r.json") == 1
    out = capsys.readouterr().out
    assert "PROBLEM rows the writes did not target changed" in out
    assert "problem(s): ROLLED BACK" in out
    assert _snapshot(pg_dsn) == before and not (tmp_path / "r.json").exists()


def test_a_drifted_restatement_stops_before_any_write(pg_dsn, prod, tmp_path, capsys):
    with psycopg.connect(pg_dsn) as con:
        con.execute("update budget_lines set amount_thousands = 1000466 where pe_bli = '0708083D'"
                    " and amount_type = 'fy_2024_pb_request_with_cr_amounts'")
    before = _snapshot(pg_dsn)
    for args in (["--check"], ["--apply", "--revert-file", tmp_path / "r.json"]):
        assert _run(pg_dsn, *args) == 1
        out = capsys.readouterr().out
        assert "s194: REFUSED — P1RestatementMismatch: PB2025 P-1 0390D 'RDT&E'" in out
        # the R-1 side is the sum of both program elements: 2,093 + 1,000,466
        assert "fy_2024_pb_request_with_cr_amounts = 1002559" in out
    assert _snapshot(pg_dsn) == before and not (tmp_path / "r.json").exists()


def test_a_workbook_the_loader_refuses_stops_before_any_write(pg_dsn, prod, tmp_path, capsys):
    """An unknown route-unsafe code (Task 6's UnsafeBudgetLineCode) refuses the
    whole run; so would a P1KeyConflict (Task 3)."""
    doc_id, path = prod[2025]
    _workbook(path, 2025)
    from openpyxl import load_workbook
    wb = load_workbook(path)
    ws = wb["Exhibit P-1"]
    ws.append(["0300D", "Procurement, Defense-Wide", "CBDP", "03", "Chem/Bio Defense", "121",
               "1", "CBDP", "A/B", "Stray", "A", "Weapon System Cost", "Add", "", 1, "", 2])
    wb.save(path)
    with psycopg.connect(pg_dsn) as con:
        con.execute("update jbook_documents set sha256 = %s where id = %s",
                    (hashlib.sha256(path.read_bytes()).hexdigest(), doc_id))
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply", "--revert-file", tmp_path / "r.json") == 1
    assert "s194: REFUSED — UnsafeBudgetLineCode: p1_display.xlsx (P-1 PB2025) row 6: 0300D prints 'A/B'" in (
        capsys.readouterr().out)
    assert _snapshot(pg_dsn) == before and not (tmp_path / "r.json").exists()


def test_revert_restores_the_exact_pre_write_rows(pg_dsn, prod, tmp_path, capsys):
    before = _snapshot(pg_dsn)
    revert_file = tmp_path / "revert.json"
    assert _run(pg_dsn, "--apply", "--revert-file", revert_file) == 0
    assert _run(pg_dsn, "--revert", "--revert-file", revert_file) == 0
    out = capsys.readouterr().out
    assert ("revert: restored 8 pre-write row(s) (re-keyed 4 back, re-inserted 4,"
            " removed 2); COMMITTED") in out
    assert _snapshot(pg_dsn) == before
    assert _run(pg_dsn, "--revert", "--revert-file", revert_file) == 0
    assert ("revert: the database already holds the pre-write rows; nothing to revert"
            in capsys.readouterr().out)
    assert _snapshot(pg_dsn) == before


def test_revert_refuses_a_database_that_moved(pg_dsn, prod, tmp_path, capsys):
    revert_file = tmp_path / "revert.json"
    assert _run(pg_dsn, "--apply", "--revert-file", revert_file) == 0
    with psycopg.connect(pg_dsn) as con:
        con.execute("update budget_lines set title = 'moved' where pe_bli = '7001SA1000'"
                    " and fiscal_year = 2024 and amount_type = 'fy_2022_actuals'")
    moved = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--revert", "--revert-file", revert_file) == 1
    out = capsys.readouterr().out
    assert "PROBLEM rows --apply did not touch changed since" in out
    assert "revert: the database moved since --apply (1 problem(s)); nothing written" in out
    assert _snapshot(pg_dsn) == moved


def test_revert_refuses_another_database(pg_dsn, prod, tmp_path, capsys):
    revert_file = tmp_path / "revert.json"
    assert _run(pg_dsn, "--apply", "--revert-file", revert_file) == 0
    rec = json.loads(revert_file.read_text())
    rec["database"] = "govbudget"
    rec["rows_sha256"] = s194.record_sha256(rec)   # a genuine file of another database
    revert_file.write_text(json.dumps(rec))
    applied = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--revert", "--revert-file", revert_file) == 1
    assert "was written on database 'govbudget'" in capsys.readouterr().out
    assert _snapshot(pg_dsn) == applied


def test_revert_refuses_an_edited_revert_file(pg_dsn, prod, tmp_path, capsys):
    revert_file = tmp_path / "revert.json"
    assert _run(pg_dsn, "--apply", "--revert-file", revert_file) == 0
    rec = json.loads(revert_file.read_text())
    rec["before"][0][s194.ROW_COLUMNS.index("amount_thousands")] = "999999999"
    revert_file.write_text(json.dumps(rec))
    applied = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--revert", "--revert-file", revert_file) == 1
    assert (f"revert: {revert_file} sha256 does not match its contents; nothing written"
            in capsys.readouterr().out)
    assert _snapshot(pg_dsn) == applied


def test_revert_refuses_a_changed_in_scope_row(pg_dsn, prod, tmp_path, capsys):
    revert_file = tmp_path / "revert.json"
    assert _run(pg_dsn, "--apply", "--revert-file", revert_file) == 0
    with psycopg.connect(pg_dsn) as con:
        rid = con.execute("select id from budget_lines where pe_bli = '0390DOM'"
                          " and fiscal_year = 2024 and amount_type = 'fy_2022_actuals'").fetchone()[0]
        con.execute("update budget_lines set amount_thousands = 1 where id = %s", (rid,))
    moved = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--revert", "--revert-file", revert_file) == 1
    out = capsys.readouterr().out
    assert f"PROBLEM re-keyed row {rid} is not as --apply wrote it" in out
    assert "revert: the database moved since --apply (1 problem(s)); nothing written" in out
    assert _snapshot(pg_dsn) == moved


def test_revert_refuses_a_file_naming_rows_outside_194s_scope(pg_dsn, prod, tmp_path, capsys):
    revert_file = tmp_path / "revert.json"
    assert _run(pg_dsn, "--apply", "--revert-file", revert_file) == 0
    rec = json.loads(revert_file.read_text())
    gone = next(r for r in rec["before"] if r[0] in rec["deleted_ids"])
    gone[s194.ROW_COLUMNS.index("pe_bli")] = "7001SA1000"
    rec["rows_sha256"] = s194.record_sha256(rec)   # consistent, but not #194's rows
    revert_file.write_text(json.dumps(rec))
    applied = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--revert", "--revert-file", revert_file) == 1
    out = capsys.readouterr().out
    assert (f"PROBLEM row {gone[0]} ('0390D', '7001SA1000') is neither re-keyed to its"
            " page key nor a restatement") in out
    assert f"revert: {revert_file} names 1 row(s) outside #194's scope; nothing written" in out
    assert _snapshot(pg_dsn) == applied
```

Create `tests/test_budget_lines_route_safe_sql.py`:

```python
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
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_s194_chem_demil.py tests/test_budget_lines_route_safe_sql.py -q 2>&1 | tail -6
```

Expected: `1 error` during collection of `tests/jbooks/test_s194_chem_demil.py` (`FileNotFoundError: [Errno 2] No such file or directory: '…/scripts/era/s194_chem_demil.py'`), so pytest stops. Then:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_budget_lines_route_safe_sql.py -q 2>&1 | tail -2
```

Expected: `3 failed` (`FileNotFoundError: … dbt/tests/assert_budget_lines_route_safe_pe_bli.sql`).

- [ ] **Step 3: Write the script and the dbt test**

Create `scripts/era/s194_chem_demil.py`:

```python
"""#194: put 0390D's Chem Demilitarization O&M line on the site under its
route-safe key, and take out the RDT&E line the R-1 already carries.

Families piece-1 follow-ups design §4.4 (owner decisions 2026-10-04: Q1 (a),
Q2, Q8, Q24 (b)). Postgres holds 16 rows the old loader guard missed before
it existed: PB2024 ids 349016-349025 and PB2025 ids 47733-47738, keyed by the
printed codes 'O&M' and 'RDT&E', which a web address cannot carry. PB2026's
8 were deleted on 2026-07-05 by the retired scripts/clean_junk_pe_bli.py.
This script, the only writer:

  * re-keys every stale alias row in place (pe_bli 'O&M' -> '0390DOM', ids
    kept, so `jbooks export-facts` keeps the lake's row order);
  * deletes every stale restatement row (pe_bli 'RDT&E': R-1 0708081D +
    0708083D carry those dollars, P1_R1_RESTATEMENTS);
  * inserts the alias rows the table lacks (PB2026's four O&M rows).

Modes (exactly one):

  --check     No write. Parses the PB2024-PB2026 P-1 workbooks with the
              loader (parse_p1_rollup, route-safe seed applied), verifies the
              restated line against the loaded R-1 (verify_r1_restatements),
              and diffs every P-1 row of those editions against Postgres. The
              only differences allowed are the ones above: a stale alias row
              whose re-keyed twin equals the parse in every column, a stale
              restatement row, and a parse alias row the table lacks. Exit 0
              when that holds (including when nothing is left to do), 1 on
              any other difference.
  --dry-run   --apply's transaction and every check, then ROLLED BACK.
  --apply     One transaction under LOCK budget_lines IN EXCLUSIVE MODE: the
              check again (refuses on any other difference), the writes, then
              require that every row the writes did not touch is unchanged
              (row count and an md5 over every column), that every alias row
              of the editions equals the parse, and that no pe_bli holds
              '&#/?%' or whitespace. Before COMMIT it writes --revert-file:
              the exact pre-write rows (every column), the ids it re-keyed,
              inserted and deleted, and the digest of the untouched rows.
              Any failure rolls back (exit 1) and leaves no revert file.
  --revert    Restores the exact pre-write rows from --revert-file, in one
              transaction under the same lock, only if the database still is
              the one --apply wrote (same database name, every written row as
              written, untouched rows unchanged); exits 0 without writing
              when the database already holds the pre-write rows; refuses
              (exit 1) on anything else, and before any read of the
              database it refuses a file whose sha256 (`rows_sha256`, over
              the file's other fields) no longer matches, or whose rows are
              not #194's (a re-keyed alias row or a deleted restatement).
              Afterwards Postgres is pre-write; the lake follows with
              `jbooks export-facts` and a selective dbt build (the release
              task's abort path).

Exit 2: a usage or precondition error (a missing or existing revert file).
A workbook the loader refuses (P1KeyConflict, UnsafeBudgetLineCode) or a
restated line that no longer equals its R-1 (P1RestatementMismatch) prints
`s194: REFUSED — <error>` and exits 1, before any write.

Usage (from GovBudget/):
  uv run --project . python scripts/era/s194_chem_demil.py --check
  uv run --project . python scripts/era/s194_chem_demil.py --dry-run
  uv run --project . python scripts/era/s194_chem_demil.py --apply --revert-file FILE
  uv run --project . python scripts/era/s194_chem_demil.py --revert --revert-file FILE
DSN: --dsn, else GOVBUDGET_PG_DSN (config.PG_DSN).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import psycopg

from govbudget import config
from govbudget.jbooks.p1_loader import (
    P1KeyConflict,
    P1Parse,
    P1Row,
    parse_p1_rollup,
    verify_r1_restatements,
    write_p1_rows,
)
from govbudget.jbooks.route_safe_codes import (
    P1_R1_RESTATEMENTS,
    P1RestatementMismatch,
    UnsafeBudgetLineCode,
    load_route_safe_codes,
)

EDITIONS: tuple[int, ...] = (2024, 2025, 2026)
REVERT_SCHEMA = 1
# Every budget_lines column, in table order (migration 021 added the last).
ROW_COLUMNS = (
    "id", "exhibit", "fiscal_year", "account", "account_title", "organization",
    "budget_activity", "budget_activity_title", "line_number", "pe_bli",
    "title", "amount_type", "amount_thousands", "source_document_id",
    "source_sheet", "source_cells", "line_item_code",
)
# The columns a parse sets and the comparison covers (key columns aside).
VALUE_COLUMNS = (
    "amount_thousands", "title", "account_title", "budget_activity_title",
    "source_cells", "source_sheet", "source_document_id", "line_item_code",
)
UNSAFE_PE_BLI_SQL = "select count(*) from budget_lines where pe_bli ~ '[&#/?%%[:space:]]'"
_ROWS_SQL = f"select {', '.join(ROW_COLUMNS)} from budget_lines"


def p1_documents(con, editions) -> dict[int, tuple[int, Path, str | None]]:
    """{edition: (document id, workbook path, sha256)}: the P-1 rollup
    workbooks, by cli._jbooks_load_rollups' rule. Exactly one per edition."""
    rows = con.execute(
        "select id, fiscal_year, file_path, sha256 from jbook_documents"
        " where exhibit_family = 'rollup' and status = 'downloaded'"
        "   and title not like 'r1%%' and title not like 'p1r%%'"
        "   and fiscal_year = any(%s) order by fiscal_year, id",
        (list(editions),),
    ).fetchall()
    by_fy: dict[int, list] = {}
    for doc_id, fy, path, sha in rows:
        by_fy.setdefault(fy, []).append((doc_id, Path(path), sha))
    bad = {fy: len(by_fy.get(fy, [])) for fy in editions if len(by_fy.get(fy, [])) != 1}
    if bad:
        raise SystemExit(f"s194: expected one P-1 rollup document per edition, got {bad}")
    return {fy: by_fy[fy][0] for fy in editions}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _key(account, organization, budget_activity, pe_bli, amount_type) -> tuple:
    return (account, organization, budget_activity, pe_bli, amount_type)


def _parse_values(r: P1Row, doc_id: int) -> tuple:
    return (r.amount_thousands, r.title, r.account_title, r.budget_activity_title,
            list(r.source_cells), r.source_sheet, doc_id, r.line_item_code)


def plan_edition(con, parsed: P1Parse, *, fiscal_year: int, doc_id: int) -> dict:
    """Compare one edition's parse with its stored P-1 rows and sort every
    difference into re-key / delete / insert / other."""
    codes = load_route_safe_codes()
    alias_by_code = {pair: c.page_key for pair, c in codes.items()}
    parse = {_key(r.account, r.organization, r.budget_activity, r.pe_bli, r.amount_type): r
             for r in parsed.rows}
    db = {}
    for rec in con.execute(
        "select id, account, organization, budget_activity, pe_bli, amount_type,"
        " amount_thousands, title, account_title, budget_activity_title,"
        " source_cells, source_sheet, source_document_id, line_item_code"
        " from budget_lines where exhibit = 'P-1' and fiscal_year = %s",
        (fiscal_year,),
    ).fetchall():
        db[_key(*rec[1:6])] = (rec[0], tuple(rec[6:]))
    rekey, delete, other = [], [], []
    covered = set()
    for k in sorted(set(db) - set(parse), key=repr):
        rid, values = db[k]
        account, org, ba, pe, at = k
        if (account, pe) in P1_R1_RESTATEMENTS:
            delete.append(rid)
        elif (account, pe) in alias_by_code:
            twin = _key(account, org, ba, alias_by_code[(account, pe)], at)
            want = parse.get(twin)
            if want is None or db.get(twin) is not None:
                other.append(f"stale {k}: no parse row {twin} to re-key to")
            elif values != _parse_values(want, doc_id):
                other.append(f"stale {k}: {values!r} != parse {_parse_values(want, doc_id)!r}")
            else:
                rekey.append((rid, twin[3]))
                covered.add(twin)
        else:
            other.append(f"extra in db: {k}")
    page_keys = set(alias_by_code.values())
    insert = []
    for k in sorted(set(parse) - set(db) - covered, key=repr):
        if k[3] in page_keys:
            insert.append(parse[k])
        else:
            other.append(f"missing in db: {k}")
    for k in sorted(set(parse) & set(db), key=repr):
        want = _parse_values(parse[k], doc_id)
        if db[k][1] != want:
            other.append(f"diff {k}: db {db[k][1]!r} != parse {want!r}")
    return {"fiscal_year": fiscal_year, "doc_id": doc_id, "parse_rows": len(parsed.rows),
            "db_rows": len(db), "rekey": rekey, "delete": delete, "insert": insert,
            "other": other}


def run_check(con, docs, parses) -> tuple[bool, dict[int, dict]]:
    ok = True
    plans = {}
    totals = {"rekey": 0, "insert": 0, "delete": 0}
    for fy, (doc_id, path, sha) in docs.items():
        actual = sha256_file(path)
        if sha != actual:
            print(f"check PB{fy}: workbook sha256 {actual} != jbook_documents {sha}")
            ok = False
        n = verify_r1_restatements(con, parses[fy])
        plan = plan_edition(con, parses[fy], fiscal_year=fy, doc_id=doc_id)
        plans[fy] = plan
        for t in totals:
            totals[t] += len(plan[t])
        print(f"check PB{fy} P-1 (doc {doc_id}): parse {plan['parse_rows']} | db"
              f" {plan['db_rows']} | re-key {len(plan['rekey'])} | insert"
              f" {len(plan['insert'])} | delete {len(plan['delete'])} | restated rows"
              f" checked against the R-1 {n} | other differences {len(plan['other'])}")
        for line in plan["other"][:10]:
            print(f"  {line}")
        ok = ok and not plan["other"]
    if not ok:
        print("check: DIFFERENCES")
    elif not any(totals.values()):
        print("check: CLEAN, nothing left to write")
    else:
        print(f"check: CLEAN, the only differences are #194's (re-key {totals['rekey']},"
              f" insert {totals['insert']}, delete {totals['delete']})")
    return ok, plans


def _parse_all(docs) -> dict[int, P1Parse]:
    return {fy: parse_p1_rollup(path, exhibit="P-1", fiscal_year=fy)
            for fy, (doc_id, path, sha) in docs.items()}


def check(dsn: str, editions) -> int:
    with psycopg.connect(dsn) as con:
        con.read_only = True
        docs = p1_documents(con, editions)
        ok, _ = run_check(con, docs, _parse_all(docs))
    return 0 if ok else 1


def _jsonable(rec) -> list:
    return [str(v) if isinstance(v, Decimal) else v for v in rec]


def _rows_by_id(con, ids) -> dict[int, list]:
    return {r[0]: _jsonable(r) for r in con.execute(
        _ROWS_SQL + " where id = any(%s) order by id", (list(ids),)).fetchall()}


def untouched_digest(con, excluded_ids) -> list:
    """[row count, md5 over every column of every row] outside excluded_ids."""
    n, md5 = con.execute(
        "select count(*), md5(coalesce(string_agg(b::text, E'\\n' order by b.id), ''))"
        " from budget_lines b where b.id <> all(%s)", (list(excluded_ids),)).fetchone()
    return [n, md5]


def record_sha256(record: dict) -> str:
    """sha256 of a revert file's record without its own `rows_sha256` field,
    as canonical JSON (sorted keys, no whitespace). --apply stores it;
    --revert recomputes it before anything else (design §4.4)."""
    body = {k: v for k, v in record.items() if k != "rows_sha256"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def out_of_scope(record: dict) -> list[str]:
    """The `before` rows a revert file would restore that #194 never writes.
    Each must be a P-1 row --apply either re-keyed (its printed code is a
    route-safe seed alias, re-keyed to that page key) or deleted (a
    P1_R1_RESTATEMENTS line), and the re-keyed and deleted ids must be
    exactly the `before` rows."""
    alias = {pair: c.page_key for pair, c in load_route_safe_codes().items()}
    col = {c: i for i, c in enumerate(ROW_COLUMNS)}
    rekeyed = {int(k): v for k, v in record["rekeyed"].items()}
    deleted = set(record["deleted_ids"])
    out = []
    for row in record["before"]:
        rid, pair = row[0], (row[col["account"]], row[col["pe_bli"]])
        ok = row[col["exhibit"]] == "P-1" and (
            (rid in rekeyed and alias.get(pair) == rekeyed[rid])
            or (rid in deleted and pair in P1_R1_RESTATEMENTS))
        if not ok:
            out.append(f"row {rid} {pair} is neither re-keyed to its page key"
                       " nor a restatement")
    if set(rekeyed) | deleted != {row[0] for row in record["before"]}:
        out.append("the re-keyed and deleted ids are not the `before` rows")
    return out


def _write_json_atomic(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def apply(dsn: str, editions, *, dry_run: bool, revert_file: Path | None) -> int:
    if not dry_run:
        if revert_file is None:
            print("apply: --revert-file is required (it records the pre-write rows)")
            return 2
        if revert_file.exists():
            print(f"apply: {revert_file} exists; refusing to overwrite a revert file")
            return 2
    with psycopg.connect(dsn) as con:
        docs = p1_documents(con, editions)
        con.rollback()
    parses = _parse_all(docs)               # UnsafeBudgetLineCode propagates here
    with psycopg.connect(dsn) as con:
        con.execute("lock table budget_lines in exclusive mode")
        ok, plans = run_check(con, docs, parses)
        if not ok:
            con.rollback()
            print("apply: check not clean, nothing written (ROLLED BACK)")
            return 1
        rekey = [x for p in plans.values() for x in p["rekey"]]
        delete = [x for p in plans.values() for x in p["delete"]]
        n_insert = sum(len(p["insert"]) for p in plans.values())
        if not (rekey or delete or n_insert):
            con.rollback()
            print("apply: nothing to write (#194 is already applied)")
            return 0
        targets = [rid for rid, _ in rekey] + delete
        before = _rows_by_id(con, targets)
        digest = untouched_digest(con, targets)
        max_id = con.execute("select coalesce(max(id), 0) from budget_lines").fetchone()[0]
        problems = []
        for rid, new_key in rekey:
            n = con.execute("update budget_lines set pe_bli = %s where id = %s",
                            (new_key, rid)).rowcount
            if n != 1:
                problems.append(f"re-keying row {rid} touched {n} rows")
        n_deleted = con.execute("delete from budget_lines where id = any(%s)",
                                (delete,)).rowcount
        n_inserted = 0
        for fy, plan in plans.items():
            n_inserted += write_p1_rows(con, plan["insert"], source_document_id=plan["doc_id"])
        inserted_ids = [r[0] for r in con.execute(
            "select id from budget_lines where id > %s order by id", (max_id,)).fetchall()]
        if n_deleted != len(delete):
            problems.append(f"deleted {n_deleted} row(s), expected {len(delete)}")
        if len(inserted_ids) != n_insert or n_inserted != n_insert:
            problems.append(f"{len(inserted_ids)} new row(s), expected {n_insert}")
        after_digest = untouched_digest(con, [rid for rid, _ in rekey] + inserted_ids)
        if after_digest != digest:
            problems.append(f"rows the writes did not target changed: {digest} -> {after_digest}")
        for fy, (doc_id, path, sha) in docs.items():
            replan = plan_edition(con, parses[fy], fiscal_year=fy, doc_id=doc_id)
            left = len(replan["rekey"]) + len(replan["insert"]) + len(replan["delete"])
            if left or replan["other"]:
                problems.append(f"PB{fy}: after the writes the parse and the table still"
                                f" differ ({left} #194 row(s), {replan['other'][:3]})")
        unsafe = con.execute(UNSAFE_PE_BLI_SQL).fetchone()[0]
        if unsafe:
            problems.append(f"{unsafe} budget_lines row(s) still carry a route-unsafe pe_bli")
        print(f"apply: re-keyed {len(rekey)}, deleted {n_deleted}, inserted {n_inserted};"
              f" untouched rows {digest[0]} (digest {'equal' if after_digest == digest else 'CHANGED'});"
              f" route-unsafe pe_bli left {unsafe}")
        for p in problems:
            print(f"  PROBLEM {p}")
        if problems:
            con.rollback()
            print(f"apply: {len(problems)} problem(s): ROLLED BACK")
            return 1
        if dry_run:
            con.rollback()
            print("apply: dry run, every check passed: ROLLED BACK")
            return 0
        record = {
            "schema": REVERT_SCHEMA,
            "database": con.execute("select current_database()").fetchone()[0],
            "written_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
            "editions": list(editions),
            "columns": list(ROW_COLUMNS),
            "before": [before[i] for i in sorted(before)],
            "rekeyed": {str(rid): key for rid, key in rekey},
            "deleted_ids": sorted(delete),
            "inserted": [r for _, r in sorted(_rows_by_id(con, inserted_ids).items())],
            "untouched_digest": digest,
        }
        record["rows_sha256"] = record_sha256(record)
        try:
            _write_json_atomic(revert_file, record)
        except OSError as exc:
            con.rollback()
            print(f"apply: could not write {revert_file} ({exc}): ROLLED BACK")
            return 1
        con.commit()
        print(f"apply: COMMITTED (revert file {revert_file})")
        return 0


def revert(dsn: str, revert_file: Path) -> int:
    if not revert_file.is_file():
        print(f"revert: {revert_file} does not exist")
        return 2
    rec = json.loads(revert_file.read_text(encoding="utf-8"))
    if rec.get("schema") != REVERT_SCHEMA or rec.get("columns") != list(ROW_COLUMNS):
        print(f"revert: {revert_file} is not a schema-{REVERT_SCHEMA} s194 revert file")
        return 2
    if rec.get("rows_sha256") != record_sha256(rec):
        print(f"revert: {revert_file} sha256 does not match its contents; nothing written")
        return 1
    scope = out_of_scope(rec)
    if scope:
        for p in scope[:10]:
            print(f"  PROBLEM {p}")
        print(f"revert: {revert_file} names {len(scope)} row(s) outside #194's scope;"
              " nothing written")
        return 1
    before = {row[0]: row for row in rec["before"]}
    inserted = {row[0]: row for row in rec["inserted"]}
    rekeyed = {int(k): v for k, v in rec["rekeyed"].items()}
    deleted = rec["deleted_ids"]
    with psycopg.connect(dsn) as con:
        db = con.execute("select current_database()").fetchone()[0]
        if db != rec["database"]:
            print(f"revert: {revert_file} was written on database {rec['database']!r},"
                  f" this is {db!r}; nothing written")
            return 1
        con.execute("lock table budget_lines in exclusive mode")
        now = _rows_by_id(con, list(before) + list(inserted))
        pre_write = (all(now.get(i) == row for i, row in before.items())
                     and not any(i in now for i in inserted))
        if pre_write:
            con.rollback()
            print("revert: the database already holds the pre-write rows; nothing to revert")
            return 0
        problems = []
        for rid, key in rekeyed.items():
            want = list(before[rid])
            want[ROW_COLUMNS.index("pe_bli")] = key
            if now.get(rid) != want:
                problems.append(f"re-keyed row {rid} is not as --apply wrote it")
        for rid, row in inserted.items():
            if now.get(rid) != row:
                problems.append(f"inserted row {rid} is not as --apply wrote it")
        for rid in deleted:
            if rid in now:
                problems.append(f"deleted row {rid} is back")
        digest = untouched_digest(con, list(rekeyed) + list(inserted))
        if digest != rec["untouched_digest"]:
            problems.append(f"rows --apply did not touch changed since: {rec['untouched_digest']}"
                            f" -> {digest}")
        if problems:
            con.rollback()
            for p in problems[:10]:
                print(f"  PROBLEM {p}")
            print(f"revert: the database moved since --apply ({len(problems)} problem(s));"
                  " nothing written")
            return 1
        con.execute("delete from budget_lines where id = any(%s)", (list(inserted),))
        for rid in rekeyed:
            con.execute("update budget_lines set pe_bli = %s where id = %s",
                        (before[rid][ROW_COLUMNS.index("pe_bli")], rid))
        cols = ", ".join(ROW_COLUMNS)
        for rid in deleted:
            con.execute(f"insert into budget_lines ({cols}) values"
                        f" ({', '.join(['%s'] * len(ROW_COLUMNS))})", before[rid])
        restored = _rows_by_id(con, list(before))
        after = untouched_digest(con, list(before))
        bad = [i for i, row in before.items() if restored.get(i) != row]
        if bad or after != rec["untouched_digest"]:
            con.rollback()
            print(f"revert: rows {bad[:5]} differ after the restore, or untouched rows"
                  f" moved ({after}); ROLLED BACK")
            return 1
        con.commit()
        print(f"revert: restored {len(before)} pre-write row(s) (re-keyed {len(rekeyed)} back,"
              f" re-inserted {len(deleted)}, removed {len(inserted)}); COMMITTED")
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="diff the parse against Postgres")
    mode.add_argument("--dry-run", action="store_true", help="--apply, then roll back")
    mode.add_argument("--apply", action="store_true", help="the transactional write")
    mode.add_argument("--revert", action="store_true", help="restore the pre-write rows")
    ap.add_argument("--revert-file", type=Path, default=None,
                    help="--apply writes it; --revert reads it")
    ap.add_argument("--dsn", default=None, help="default: GOVBUDGET_PG_DSN")
    ap.add_argument("--editions", type=int, nargs="+", default=list(EDITIONS))
    args = ap.parse_args(argv)
    dsn = args.dsn or config.PG_DSN
    try:
        if args.check:
            return check(dsn, args.editions)
        if args.revert:
            if args.revert_file is None:
                print("revert: --revert-file is required")
                return 2
            return revert(dsn, args.revert_file)
        return apply(dsn, args.editions, dry_run=args.dry_run, revert_file=args.revert_file)
    except (P1KeyConflict, P1RestatementMismatch, UnsafeBudgetLineCode) as exc:
        print(f"s194: REFUSED — {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

Create `dbt/tests/assert_budget_lines_route_safe_pe_bli.sql`:

```sql
-- No budget_lines row is keyed by a code a web address cannot carry
-- (families piece-1 follow-ups design §4.4, #194). A program page is a static
-- route keyed by pe_bli, so '&', '#', '/', '?', '%' or whitespace in one is a
-- page that cannot exist or a total that counts an unpublished line. Until
-- the #194 write (scripts/era/s194_chem_demil.py --apply) 16 PB2024-PB2025
-- rows held 0390D's printed codes 'O&M' and 'RDT&E'; the loader now keys O&M
-- by its route-safe page key (dbt/seeds/p1_route_safe_codes.csv) and keeps
-- the RDT&E restatement out, and raises on any other such code.
select
    'route-unsafe pe_bli in budget_lines' as failure,
    exhibit,
    fiscal_year,
    account,
    pe_bli,
    count(*) as n_rows
from {{ ref('stg_budget_lines') }}
where regexp_matches(pe_bli, '[&#/?%[:space:]]')
group by exhibit, fiscal_year, account, pe_bli
```

- [ ] **Step 4: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_s194_chem_demil.py tests/test_budget_lines_route_safe_sql.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 scripts/era/s194_chem_demil.py | tail -1
```

Expected: `21 passed` (18 + 3); `All checks passed!`.

- [ ] **Step 5: `--check` on the live database (read-only)**

`--check` opens a read-only transaction and writes nothing; it reads the PB2024–PB2026 workbooks from `data/raw_docs`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python scripts/era/s194_chem_demil.py --check; echo "exit=$?"
```

Expected: the four `check …` lines quoted under "Measured" above, then `exit=0`. Any `other differences` above 0, a `DIFFERENCES` verdict or a `REFUSED` line means Postgres or a workbook moved since 2026-10-13: stop and report it (Task 22 runs this same check first).

- [ ] **Step 6: Rehearse every mode on a copy of the live tables (throwaway cluster only)**

The dump is a read of the live server; every write goes to database `s194_rehearsal` on 127.0.0.1:55432, which this step creates and drops. The live `govbudget` database is never written.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
PGB="$GOVBUDGET_PG_BIN"; R=postgresql://127.0.0.1:55432/s194_rehearsal; D="${GOVBUDGET_PROOFS:?}/fu-s194-rehearsal"
mkdir -p "$D" && rm -f "$D/revert.json"
"$PGB/psql" postgresql://127.0.0.1:55432/postgres -X -q -c "drop database if exists s194_rehearsal" -c "create database s194_rehearsal"
"$PGB/pg_dump" "$GOVBUDGET_PG_DSN" -t budget_lines -t jbook_documents --no-owner --no-privileges -Fc -f "$D/bl_docs.dump"
"$PGB/pg_restore" --no-owner -d "$R" "$D/bl_docs.dump"
BEFORE=$("$PGB/psql" "$R" -X -A -t -c "select count(*) || ' ' || md5(string_agg(b::text, E'\n' order by id)) from budget_lines b"); echo "before: $BEFORE"
uv run --project . python scripts/era/s194_chem_demil.py --dry-run --dsn "$R" | tail -2
uv run --project . python scripts/era/s194_chem_demil.py --apply --revert-file "$D/revert.json" --dsn "$R" | tail -2
uv run --project . python scripts/era/s194_chem_demil.py --check --dsn "$R" | tail -1
"$PGB/psql" "$R" -X -A -t -c "select count(*) from budget_lines where pe_bli ~ '[&#/?%[:space:]]'"
uv run --project . python scripts/era/s194_chem_demil.py --revert --revert-file "$D/revert.json" --dsn "$R"
AFTER=$("$PGB/psql" "$R" -X -A -t -c "select count(*) || ' ' || md5(string_agg(b::text, E'\n' order by id)) from budget_lines b"); echo "after revert: $AFTER"; [ "$BEFORE" = "$AFTER" ] && echo "REVERT EXACT"
uv run --project . python scripts/era/s194_chem_demil.py --revert --revert-file "$D/revert.json" --dsn "$R"
"$PGB/psql" postgresql://127.0.0.1:55432/postgres -X -q -c "drop database s194_rehearsal" && rm -rf "${D:?}"
```

Expected, in order: `before: 159903 4174ef8314daf8a822289c951e834b78` (today's live table; another count or hash only means `budget_lines` moved since 2026-10-13, and the rest of the step must still hold); `apply: re-keyed 8, deleted 8, inserted 4; untouched rows 159887 (digest equal); route-unsafe pe_bli left 0` and `apply: dry run, every check passed: ROLLED BACK`; the same `apply:` line and `apply: COMMITTED (revert file …/fu-s194-rehearsal/revert.json)`; `check: CLEAN, nothing left to write`; `0`; `revert: restored 16 pre-write row(s) (re-keyed 8 back, re-inserted 8, removed 4); COMMITTED`; `after revert: ` with the same text as `before:`, then `REVERT EXACT`; `revert: the database already holds the pre-write rows; nothing to revert`. A missing `REVERT EXACT` is a defect in `--revert`: stop before any later task relies on it.

- [ ] **Step 7: Retire `clean_junk_pe_bli.py` with a dated note**

It treated 0390D's two real lines as junk (design Q9). Delete it:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git rm -q GovBudget/scripts/clean_junk_pe_bli.py && git status --short -- GovBudget/scripts/clean_junk_pe_bli.py
```

Expected: `D  GovBudget/scripts/clean_junk_pe_bli.py`.

In `docs/superpowers/ROADMAP.md` (the findings-log entry "Reject junk at the loader, not just at the exporter", about line 1019), replace:

```markdown
  masks bad data from the UI is belt; rejecting it at ingest is braces.
```

with:

```markdown
  masks bad data from the UI is belt; rejecting it at ingest is braces.
  *Correction (owner, 2026-10-04, #194 design Q9; nothing above reworded):* the
  two "labels" were 0390D's real Chem Demilitarization O&M and RDT&E lines, the
  only rows the guard ever caught (two in each PB2024–PB2026 P-1), and the
  cleanup deleted PB2026's 8 real rows. The guard and `scripts/clean_junk_pe_bli.py`
  are retired: the loader keys O&M by its owner-approved route-safe key `0390DOM`,
  checks the RDT&E line against the R-1 program elements it restates (0708081D +
  0708083D) and leaves it out, and raises on any other route-unsafe code;
  `scripts/era/s194_chem_demil.py` is the one writer of the stored rows.
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && test ! -e scripts/clean_junk_pe_bli.py || echo STILL_THERE
grep -rn clean_junk_pe_bli src tests scripts site/scripts site/src dbt | grep -v '^scripts/era/s194_chem_demil.py' ; grep -c 'are retired: the loader keys O&M' docs/superpowers/ROADMAP.md
```

Expected: no `STILL_THERE`; the grep prints nothing; `1`.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/scripts/era/s194_chem_demil.py GovBudget/tests/jbooks/test_s194_chem_demil.py GovBudget/dbt/tests/assert_budget_lines_route_safe_pe_bli.sql GovBudget/tests/test_budget_lines_route_safe_sql.py GovBudget/docs/superpowers/ROADMAP.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era): s194_chem_demil.py re-keys the 0390D O&M rows to 0390DOM, drops the RDT&E restatement, inserts PB2026 O&M; --check/--dry-run/--apply/--revert; retire clean_junk_pe_bli.py (#194)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `6 files changed` (the deletion staged in Step 7 included). Nothing here writes the live database: Task 21e runs `--apply` once on the `fu-post` scratch database, Task 21f rehearses `--apply` then `--revert` on `fu-pre` (README decision 2), and Task 22b runs `--apply` on live Postgres, with `--revert` as its abort path.
