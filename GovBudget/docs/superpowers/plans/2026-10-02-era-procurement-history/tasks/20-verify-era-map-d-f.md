<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 20: verify-era-map legs d–f and its place in the verify-phase5 assembly

**Spec:** §8 V4 legs (d) any `budget_lines_decade` row whose fact ID does not recompute with `fact_id_workbook` from
its own row, (e) published map parquet ≠ dbt map, (f) F-15 history sha ≠ the pin at `tests/fixtures/f15/history.sha256`;
V4's assembly clause (`_ASSEMBLY_PHASES`, `_VERDICT_RE` extended to `verify-(?:phase\w+|lineage|era-map):`, docstring
and assembly tests updated); V10; S4. Task 14's module (G4) is canonical; contract issue 5 is withdrawn.

**Files:**
- Modify: `src/govbudget/verify_era_map.py` (Task 14's module: the docstring's legs (d)–(f) paragraph; the
  `from collections import defaultdict` import; two constants and three legs inserted between `leg_c_f15` and
  `run_verify_era_map`; the `else:` branch of `run_verify_era_map`)
- Test: `tests/test_verify_era_map_def.py` (create)
- Modify: `tests/test_verify_era_map.py` (Task 14's: delete `test_legs_d_to_f_fail_until_task_20`; replace
  `test_cli_zero_arguments_runs_every_leg` with `LEG_LINES`, `_publish_export` and two tests)
- Modify: `src/govbudget/verify_phase5.py:31-36` (docstring), `:124-146` (comments, `_ASSEMBLY_PHASES`, `_VERDICT_RE`)
- Test: `tests/test_verify_phase5.py` (append after `:729`)

**Interfaces:**
Consumes: Task 14 (`src/govbudget/verify_era_map.py` as G4 drafts it: `_leg(ok, summary, failures)` returning
`{"ok", "detail": {"summary", "failures"}}`, `_sha256_file`, `LEG_NAMES` (already `"d": "fact ids"`, `"e": "published
map"`, `"f": "f15 history pin"`), `format_report` (reads `detail["summary"]` and `detail["failures"]`),
`run_verify_era_map` with its `if`/`elif` dispatch and `else:` branch, `DEFAULT_SEED_PATH`; `tests/test_verify_era_map.py`
with `Corpus`, the `pinned` fixture and the CLI tests); Task 4 (`tests/fixtures/f15/history.sha256`; today's sha of
`data/site/json/f15_funding_history.json` is `9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800`);
Task 19 (`data/p1_era_line_map.parquet` in the export: `select *` of the mart, its column order); Task 13
(`p1_era_line_map` in the warehouse); `govbudget.export_site.fact_id_workbook` (`export_site.py:74-78`);
`govbudget.jbooks.era_keys.is_era_procurement_key` (`era_keys.py:105`).
Produces: `F15_HISTORY_PIN: Path`; `leg_d_fact_ids(*, site_dir: Path) -> dict`, `leg_e_published_map(*, site_dir:
Path, duckdb_path: Path) -> dict`, `leg_f_history_pin(*, site_dir: Path) -> dict`, each returning
`_leg(ok, summary, failures)`; `run_verify_era_map(..., legs="abcdef")` runs all six legs for real, so the CLI's
`format_report` prints six real leg lines; `_ASSEMBLY_PHASES[-1] == "verify-era-map"`; `_VERDICT_RE` matching
`verify-era-map: PASS|FAIL|BLOCKED`. After this task `verify-phase5`'s assembly FAILs until the S4 export ships the map
(leg e) — by design; V10 runs it at release.

- [ ] **Step 1: Write the failing leg tests**

Create `tests/test_verify_era_map_def.py`:
```python
"""verify-era-map legs d–f (families piece 1, spec 2026-10-02 §8 V4; Task 20).

(d) every budget_lines_decade row's fact_id recomputes with fact_id_workbook
    from its own row, no fact_id repeats, and every PB2017–PB2023 P-1 row keeps
    its era key as pe_bli (non-vacuous: at least one such row);
(e) the published data/p1_era_line_map.parquet equals the warehouse's
    p1_era_line_map, column names and row multiset;
(f) data/site/json/f15_funding_history.json matches the S0 pin.
Each leg returns Task 14's shape, {"ok", "detail": {"summary", "failures"}},
so format_report and the CLI print it like legs a–c. Every fixture is built
here; nothing reads the shared lake.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb

import govbudget.verify_era_map as vem
from govbudget.export_site import fact_id_workbook
from govbudget.verify_era_map import (
    format_report,
    leg_d_fact_ids,
    leg_e_published_map,
    leg_f_history_pin,
    run_verify_era_map,
)

# The nine columns leg d reads: fact_id, then fact_id_workbook's own argument
# order (document_sha256, exhibit, fiscal_year, account, organization,
# budget_activity, pe_bli, amount_type).
BLD_DDL = (
    "create table t (fact_id varchar, document_sha256 varchar, exhibit varchar,"
    " fiscal_year integer, account varchar, organization varchar,"
    " budget_activity varchar, pe_bli varchar, amount_type varchar)"
)
MODERN = ("sha26", "R-1", 2026, "0400", "DARPA", "01", "0601101E", "fy_2024_actuals")
ERA = ("sha19", "P-1", 2019, "3010F", "AF", "01", "3010F-AF-L1", "fy_2017_base_oco")


def _row(ident, fact_id=None):
    return (fact_id or fact_id_workbook(*ident), *ident)


def _write_decade(site: Path, rows) -> None:
    (site / "data").mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(BLD_DDL)
    if rows:
        con.executemany("insert into t values (?,?,?,?,?,?,?,?,?)", rows)
    con.execute(f"copy t to '{site / 'data' / 'budget_lines_decade.parquet'}' (format parquet)")
    con.close()


def _summary(result: dict) -> str:
    return result["detail"]["summary"]


def _failures(result: dict) -> list[str]:
    return result["detail"]["failures"]


# --- leg d -----------------------------------------------------------------

def test_d_passes_when_every_fact_id_recomputes(tmp_path):
    _write_decade(tmp_path, [_row(MODERN), _row(ERA)])
    result = leg_d_fact_ids(site_dir=tmp_path)
    assert result["ok"] is True, _failures(result)
    assert _summary(result) == (
        "rows=2 era_p1_rows=1 mismatched=0 duplicate_fact_ids=0 era_rows_without_era_key=0")
    assert _failures(result) == []


def test_d_fails_on_a_fact_id_that_does_not_recompute(tmp_path):
    _write_decade(tmp_path, [_row(MODERN), _row(ERA, fact_id="0" * 16)])
    result = leg_d_fact_ids(site_dir=tmp_path)
    assert result["ok"] is False
    assert "mismatched=1" in _summary(result)
    assert _failures(result) == [
        "0000000000000000: does not recompute with fact_id_workbook from its own row"
        " (P-1 FY2019 3010F-AF-L1 fy_2017_base_oco)"]


def test_d_fails_on_an_era_row_re_keyed_to_its_printed_code(tmp_path):
    # The fact id recomputes (it hashes the printed code), but the lake
    # identity was re-keyed: spec §6.1 keeps pe_bli = era key in this dataset.
    printed = ERA[:6] + ("ATA000",) + ERA[7:]
    _write_decade(tmp_path, [_row(MODERN), _row(printed)])
    result = leg_d_fact_ids(site_dir=tmp_path)
    assert result["ok"] is False
    assert "mismatched=0" in _summary(result)
    assert "era_rows_without_era_key=1" in _summary(result)
    assert _failures(result) == [
        f"{fact_id_workbook(*printed)}: P-1 FY2019 row has pe_bli 'ATA000', not an era key"
        " (spec §6.1: the lake identity is never re-keyed)"]


def test_d_fails_on_a_repeated_fact_id(tmp_path):
    _write_decade(tmp_path, [_row(ERA), _row(ERA)])
    result = leg_d_fact_ids(site_dir=tmp_path)
    assert result["ok"] is False
    assert "duplicate_fact_ids=1" in _summary(result)
    assert _failures(result) == [f"{fact_id_workbook(*ERA)}: fact_id repeats on 2 rows"]


def test_d_fails_vacuously_without_an_era_row(tmp_path):
    _write_decade(tmp_path, [_row(MODERN)])
    result = leg_d_fact_ids(site_dir=tmp_path)
    assert result["ok"] is False
    assert "era_p1_rows=0" in _summary(result)
    assert _failures(result) == ["no PB2017–PB2023 P-1 row: the era-key check would pass vacuously"]


def test_d_fails_without_the_parquet(tmp_path):
    result = leg_d_fact_ids(site_dir=tmp_path)
    assert result["ok"] is False
    assert _summary(result) == "budget_lines_decade.parquet missing"
    assert _failures(result) == [f"missing {tmp_path / 'data' / 'budget_lines_decade.parquet'}"]


# --- leg e -----------------------------------------------------------------

MAP_DDL = ("create table p1_era_line_map (edition integer, era_key varchar,"
           " line_item_code varchar, decision varchar)")
MAP_ROWS = [(2017, "3010F-AF-L1", "ATA000", "same_program"),
            (2022, "3010F-AF-L1", "B02100", "same_program")]


def _write_map(site: Path, db: Path, published=MAP_ROWS, mart=True) -> None:
    (site / "data").mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    if mart:
        con.execute(MAP_DDL)
        con.executemany("insert into p1_era_line_map values (?,?,?,?)", MAP_ROWS)
    con.execute(MAP_DDL.replace("p1_era_line_map", "pub"))
    if published:
        con.executemany("insert into pub values (?,?,?,?)", published)
    con.execute(f"copy pub to '{site / 'data' / 'p1_era_line_map.parquet'}' (format parquet)")
    con.execute("drop table pub")
    con.close()


def test_e_passes_when_the_published_map_is_the_warehouse_map(tmp_path):
    db = tmp_path / "wh.duckdb"
    _write_map(tmp_path, db)
    result = leg_e_published_map(site_dir=tmp_path, duckdb_path=db)
    assert result["ok"] is True, _failures(result)
    assert _summary(result) == "mart_rows=2 published_rows=2 only_in_mart=0 only_published=0"


def test_e_fails_when_a_decision_moved_after_the_export(tmp_path):
    db = tmp_path / "wh.duckdb"
    _write_map(tmp_path, db, published=[MAP_ROWS[0], (2022, "3010F-AF-L1", "B02100", "history_only")])
    result = leg_e_published_map(site_dir=tmp_path, duckdb_path=db)
    assert result["ok"] is False
    assert _summary(result) == "mart_rows=2 published_rows=2 only_in_mart=1 only_published=1"
    assert _failures(result) == [
        "1 warehouse row(s) are not in the published parquet: re-export",
        "1 published row(s) are not in the warehouse map: re-export",
    ]


def test_e_fails_on_a_duplicated_published_row(tmp_path):
    db = tmp_path / "wh.duckdb"
    _write_map(tmp_path, db, published=MAP_ROWS + [MAP_ROWS[0]])
    result = leg_e_published_map(site_dir=tmp_path, duckdb_path=db)
    assert result["ok"] is False
    assert _summary(result) == "mart_rows=2 published_rows=3 only_in_mart=0 only_published=1"


def test_e_fails_when_the_columns_differ(tmp_path):
    db = tmp_path / "wh.duckdb"
    _write_map(tmp_path, db)
    pq = tmp_path / "data" / "p1_era_line_map.parquet"
    con = duckdb.connect()
    con.execute(f"copy (select edition, era_key, decision, line_item_code from read_parquet('{pq}'))"
                f" to '{tmp_path / 'reordered.parquet'}' (format parquet)")
    con.close()
    (tmp_path / "reordered.parquet").replace(pq)
    result = leg_e_published_map(site_dir=tmp_path, duckdb_path=db)
    assert result["ok"] is False
    assert _summary(result) == "columns differ"
    assert _failures(result) == [
        "published columns ['edition', 'era_key', 'decision', 'line_item_code'] !="
        " warehouse columns ['edition', 'era_key', 'line_item_code', 'decision']"]


def test_e_fails_on_an_empty_warehouse_map(tmp_path):
    db = tmp_path / "wh.duckdb"
    _write_map(tmp_path, db, published=[])
    con = duckdb.connect(str(db))
    con.execute("delete from p1_era_line_map")
    con.close()
    result = leg_e_published_map(site_dir=tmp_path, duckdb_path=db)
    assert result["ok"] is False
    assert _summary(result) == "mart_rows=0 published_rows=0 only_in_mart=0 only_published=0"
    assert _failures(result) == ["the warehouse p1_era_line_map is empty"]


def test_e_fails_without_the_warehouse_map(tmp_path):
    db = tmp_path / "wh.duckdb"
    _write_map(tmp_path, db, mart=False)
    result = leg_e_published_map(site_dir=tmp_path, duckdb_path=db)
    assert result["ok"] is False
    assert _summary(result) == "p1_era_line_map missing from the warehouse"
    assert _failures(result) == [f"{db}: no table p1_era_line_map"]


def test_e_fails_without_the_warehouse(tmp_path):
    _write_map(tmp_path, tmp_path / "wh.duckdb")
    absent = tmp_path / "absent.duckdb"
    result = leg_e_published_map(site_dir=tmp_path, duckdb_path=absent)
    assert result["ok"] is False
    assert _summary(result) == "warehouse unreadable"
    assert _failures(result)[0].startswith(f"cannot open {absent}: ")
    assert not absent.exists()  # a read-only open never creates the file


def test_e_fails_without_the_published_parquet(tmp_path):
    db = tmp_path / "wh.duckdb"
    duckdb.connect(str(db)).close()
    result = leg_e_published_map(site_dir=tmp_path, duckdb_path=db)
    assert result["ok"] is False
    assert _summary(result) == "p1_era_line_map.parquet missing"
    assert _failures(result) == [f"missing {tmp_path / 'data' / 'p1_era_line_map.parquet'}"]


# --- leg f -----------------------------------------------------------------

HISTORY = b'{"points": []}\n'


def _write_history(site: Path, pin: Path, monkeypatch, *, pin_text, history=HISTORY) -> None:
    (site / "json").mkdir(parents=True, exist_ok=True)
    if history is not None:
        (site / "json" / "f15_funding_history.json").write_bytes(history)
    if pin_text is not None:
        pin.write_text(pin_text)
    monkeypatch.setattr(vem, "F15_HISTORY_PIN", pin)


def test_f_pin_path_is_the_committed_fixture():
    assert vem.F15_HISTORY_PIN.parts[-4:] == ("tests", "fixtures", "f15", "history.sha256")


def test_f_passes_on_a_shasum_style_pin(tmp_path, monkeypatch):
    digest = hashlib.sha256(HISTORY).hexdigest()
    _write_history(tmp_path, tmp_path / "pin", monkeypatch,
                   pin_text=f"{digest}  data/site/json/f15_funding_history.json\n")
    result = leg_f_history_pin(site_dir=tmp_path)
    assert result["ok"] is True, _failures(result)
    assert _summary(result) == f"pinned={digest} actual={digest}"


def test_f_passes_on_a_bare_digest(tmp_path, monkeypatch):
    _write_history(tmp_path, tmp_path / "pin", monkeypatch,
                   pin_text=hashlib.sha256(HISTORY).hexdigest().upper() + "\n")
    assert leg_f_history_pin(site_dir=tmp_path)["ok"] is True


def test_f_fails_when_the_history_changed(tmp_path, monkeypatch):
    digest = hashlib.sha256(HISTORY).hexdigest()
    changed = HISTORY.replace(b"[]", b"[1]")
    actual = hashlib.sha256(changed).hexdigest()
    _write_history(tmp_path, tmp_path / "pin", monkeypatch, pin_text=digest, history=changed)
    result = leg_f_history_pin(site_dir=tmp_path)
    assert result["ok"] is False
    assert _summary(result) == f"pinned={digest} actual={actual}"
    assert _failures(result) == [
        f"f15_funding_history.json hashes to {actual}, the S0 pin says {digest}"
        " (only the S5 correction re-pins it)"]


def test_f_fails_without_the_pin(tmp_path, monkeypatch):
    _write_history(tmp_path, tmp_path / "pin", monkeypatch, pin_text=None)
    result = leg_f_history_pin(site_dir=tmp_path)
    assert result["ok"] is False
    assert _summary(result) == "pin missing"
    assert _failures(result) == [f"missing pin {tmp_path / 'pin'}"]


def test_f_fails_on_an_unreadable_pin(tmp_path, monkeypatch):
    _write_history(tmp_path, tmp_path / "pin", monkeypatch, pin_text="not-a-digest\n")
    result = leg_f_history_pin(site_dir=tmp_path)
    assert result["ok"] is False
    assert _summary(result) == "pin unreadable"
    assert _failures(result) == [f"{tmp_path / 'pin'} does not start with a sha256 hex digest"]


def test_f_fails_without_the_history(tmp_path, monkeypatch):
    _write_history(tmp_path, tmp_path / "pin", monkeypatch, pin_text="0" * 64, history=None)
    result = leg_f_history_pin(site_dir=tmp_path)
    assert result["ok"] is False
    assert _summary(result) == "f15_funding_history.json missing"
    assert _failures(result) == [f"missing {tmp_path / 'json' / 'f15_funding_history.json'}"]


# --- run_verify_era_map and format_report ----------------------------------

def test_run_dispatches_d_e_f(tmp_path, monkeypatch):
    db = tmp_path / "wh.duckdb"
    _write_decade(tmp_path, [_row(MODERN), _row(ERA)])
    _write_map(tmp_path, db)
    _write_history(tmp_path, tmp_path / "pin", monkeypatch,
                   pin_text=hashlib.sha256(HISTORY).hexdigest())
    result = run_verify_era_map(site_dir=tmp_path, duckdb_path=db,
                                seed_path=tmp_path / "seed.csv", legs="def")
    assert list(result["legs"]) == ["d", "e", "f"]
    assert result["verdict"] == "PASS"
    assert all(r["detail"]["summary"] != "not implemented" for r in result["legs"].values())
    (tmp_path / "json" / "f15_funding_history.json").write_bytes(b"{}")
    result = run_verify_era_map(site_dir=tmp_path, duckdb_path=db,
                                seed_path=tmp_path / "seed.csv", legs="def")
    assert result["legs"]["f"]["ok"] is False
    assert result["verdict"] == "FAIL"


def test_format_report_prints_legs_d_to_f(tmp_path, monkeypatch):
    db = tmp_path / "wh.duckdb"
    _write_decade(tmp_path, [_row(MODERN), _row(ERA)])
    _write_map(tmp_path, db)
    _write_history(tmp_path, tmp_path / "pin", monkeypatch, pin_text="0" * 64)
    digest = hashlib.sha256(HISTORY).hexdigest()
    lines = format_report(run_verify_era_map(site_dir=tmp_path, duckdb_path=db,
                                             seed_path=tmp_path / "seed.csv", legs="def"))
    assert lines == [
        "leg d fact ids: rows=2 era_p1_rows=1 mismatched=0 duplicate_fact_ids=0"
        " era_rows_without_era_key=0 → PASS",
        "leg e published map: mart_rows=2 published_rows=2 only_in_mart=0 only_published=0 → PASS",
        f"leg f f15 history pin: pinned={'0' * 64} actual={digest} → FAIL",
        f"  FAIL f15_funding_history.json hashes to {digest}, the S0 pin says {'0' * 64}"
        " (only the S5 correction re-pins it)",
    ]
```

- [ ] **Step 2: Bring Task 14's zero-argument tests up to six real legs**

In `tests/test_verify_era_map.py` (Task 14), delete this test and the two blank lines after it (it pinned the
placeholder `else:` branch this task removes):
```python
def test_legs_d_to_f_fail_until_task_20(pinned):
    out = run_verify_era_map(site_dir=pinned.site_dir, duckdb_path=pinned.duckdb_path,
                             seed_path=pinned.seed_path)
    assert list(out["legs"]) == ["a", "b", "c", "d", "e", "f"]
    assert [leg for leg, r in out["legs"].items() if not r["ok"]] == ["d", "e", "f"]
    assert out["verdict"] == "FAIL"


```

Then replace the last test of the file. Before:
```python
def test_cli_zero_arguments_runs_every_leg(pinned, capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-era-map"])
    out = capsys.readouterr().out.splitlines()
    assert exit_.value.code == 1
    assert [line.split(":")[0] for line in out if line.startswith("leg ")] == [
        "leg a workbooks", "leg b decisions", "leg c f15",
        "leg d fact ids", "leg e published map", "leg f f15 history pin"]
    assert out[-1] == "verify-era-map: FAIL"
```
After (the zero-argument run now passes all six legs on a corpus whose export carries the three artifacts legs d–f
read, and fails d–f for their real reasons when it does not):
```python
LEG_LINES = ["leg a workbooks", "leg b decisions", "leg c f15",
             "leg d fact ids", "leg e published map", "leg f f15 history pin"]


def _publish_export(corpus: Corpus, monkeypatch) -> None:
    """The three artifacts legs d–f read, consistent with the corpus: one era
    P-1 row of budget_lines_decade (its fact id from fact_id_workbook), the
    warehouse map exported as data/p1_era_line_map.parquet, and an F-15
    history file with its pin."""
    from govbudget.export_site import fact_id_workbook

    k = corpus.row(2019, "3010F-AF-L30")
    ident = (k["source_document_sha256"], "P-1", 2019, k["account"], k["organization"],
             k["budget_activity"], k["era_key"], "fy_2017_base_oco")
    data = corpus.site_dir / "data"
    data.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute("create table bld (fact_id varchar, document_sha256 varchar, exhibit varchar,"
                " fiscal_year integer, account varchar, organization varchar,"
                " budget_activity varchar, pe_bli varchar, amount_type varchar)")
    con.execute("insert into bld values (?,?,?,?,?,?,?,?,?)", [fact_id_workbook(*ident), *ident])
    con.execute(f"copy bld to '{data / 'budget_lines_decade.parquet'}' (format parquet)")
    con.execute(f"attach '{corpus.duckdb_path}' as wh (read_only)")
    con.execute("copy (select * from wh.p1_era_line_map)"
                f" to '{data / 'p1_era_line_map.parquet'}' (format parquet)")
    con.close()
    history = b'{"points": []}\n'
    (corpus.site_dir / "json").mkdir(exist_ok=True)
    (corpus.site_dir / "json" / "f15_funding_history.json").write_bytes(history)
    pin = corpus.site_dir.parent / "history.sha256"
    pin.write_text(hashlib.sha256(history).hexdigest() + "  data/site/json/f15_funding_history.json\n")
    monkeypatch.setattr(verify_era_map, "F15_HISTORY_PIN", pin)


def test_cli_zero_arguments_runs_every_leg(pinned, capsys, monkeypatch):
    _publish_export(pinned, monkeypatch)
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-era-map"])
    out = capsys.readouterr().out.splitlines()
    legs = [line for line in out if line.startswith("leg ")]
    assert [line.split(":")[0] for line in legs] == LEG_LINES
    assert all(line.endswith("→ PASS") for line in legs), out
    assert exit_.value.code == 0
    assert out[-1] == "verify-era-map: PASS"


def test_cli_zero_arguments_fails_without_the_export(pinned, capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-era-map"])
    out = capsys.readouterr().out.splitlines()
    legs = {line.split(":")[0]: line for line in out if line.startswith("leg ")}
    assert list(legs) == LEG_LINES
    assert all(legs[name].endswith("→ PASS") for name in LEG_LINES[:3])
    assert legs["leg d fact ids"].endswith(": budget_lines_decade.parquet missing → FAIL")
    assert legs["leg e published map"].endswith(": p1_era_line_map.parquet missing → FAIL")
    assert legs["leg f f15 history pin"].endswith(": f15_funding_history.json missing → FAIL")
    assert exit_.value.code == 1
    assert out[-1] == "verify-era-map: FAIL"
```
(`hashlib`, `duckdb`, `pytest`, `cli` and `verify_era_map` are already imported at the top of the file by Task 14.)

- [ ] **Step 3: Run the tests to see them fail**

Run (two commands: a collection error stops a pytest run, so the files run separately):
```bash
uv run --project . pytest tests/test_verify_era_map_def.py -q
uv run --project . pytest tests/test_verify_era_map.py -q
```
Expected: the first stops at collection, `1 error`, with
`ImportError: cannot import name 'leg_d_fact_ids' from 'govbudget.verify_era_map'`. The second prints
`2 failed, 24 passed`: `test_cli_zero_arguments_runs_every_leg` fails inside `_publish_export` with
`AttributeError: <module 'govbudget.verify_era_map' …> has no attribute 'F15_HISTORY_PIN'`, and
`test_cli_zero_arguments_fails_without_the_export` fails on
`assert legs["leg d fact ids"].endswith(": budget_lines_decade.parquet missing → FAIL")` (the line reads
`leg d fact ids: not implemented → FAIL`).

- [ ] **Step 4: Add legs d–f to `src/govbudget/verify_era_map.py`**

Four edits to Task 14's module.

Edit 1, the module docstring. Before:
```python
  Legs (d)–(f) are added by Task 20 (fact-ID recompute, published parquet vs
  dbt map, F-15 history sha pin). Until then they report FAIL, so the
  zero-argument run cannot pass vacuously.
"""
```
After:
```python
  Leg (d) — fact ids. Every row of the exported budget_lines_decade.parquet
    recomputes its fact_id with export_site.fact_id_workbook from its own
    columns, no fact_id repeats, and every PB2017–PB2023 P-1 row keeps its
    era key as pe_bli (spec §6.1: the lake identity is never re-keyed). At
    least one such row must exist, so the check cannot pass vacuously.

  Leg (e) — published map. The exported data/p1_era_line_map.parquet equals
    the warehouse's p1_era_line_map: the same column names in the same order,
    the same row multiset, and not empty. A warehouse whose map moved after
    the export fails here until the site is re-exported.

  Leg (f) — F-15 history pin. data/site/json/f15_funding_history.json hashes
    to the sha256 committed at S0 in tests/fixtures/f15/history.sha256 (its
    first token, so `shasum -a 256` output reads); only the S5 correction
    re-pins it.
"""
```

Edit 2, the imports. Before:
```python
from collections import defaultdict
```
After:
```python
from collections import Counter, defaultdict
```

Edit 3, the three legs, between `leg_c_f15` and `run_verify_era_map`. Before:
```python
    return _leg(not failures,
                f"expected={len(expected)} map_rows={len(actual)} failures={len(failures)}",
                failures)


def run_verify_era_map(
```
After:
```python
    return _leg(not failures,
                f"expected={len(expected)} map_rows={len(actual)} failures={len(failures)}",
                failures)


# --- Legs d–f (Task 20): the published export against its own inputs -------

#: The F-15 history pin committed at S0 (Task 4). Its first whitespace-
#: separated token is the sha256 hex digest of
#: data/site/json/f15_funding_history.json (`shasum -a 256` output reads).
#: Resolved from this file, not config.ROOT, so a test can swap it.
F15_HISTORY_PIN = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "f15" / "history.sha256"

#: The last edition whose P-1 rows carry era keys as pe_bli (spec §3).
_ERA_P1_LAST_EDITION = 2023


def leg_d_fact_ids(*, site_dir: Path) -> dict:
    """Leg (d): budget_lines_decade's fact ids recompute; era rows keep era keys."""
    import duckdb

    from govbudget.export_site import fact_id_workbook
    from govbudget.jbooks.era_keys import is_era_procurement_key

    pq = Path(site_dir) / "data" / "budget_lines_decade.parquet"
    if not pq.is_file():
        return _leg(False, "budget_lines_decade.parquet missing", [f"missing {pq}"])
    con = duckdb.connect()
    try:
        rows = con.execute(
            "select fact_id, document_sha256, exhibit, fiscal_year, account,"
            " organization, budget_activity, pe_bli, amount_type"
            " from read_parquet(?)", [str(pq)]).fetchall()
    finally:
        con.close()
    failures: list[str] = []
    mismatched = 0
    for fid, sha, exhibit, fy, account, org, ba, pe_bli, amount_type in rows:
        if fact_id_workbook(sha, exhibit, fy, account, org, ba, pe_bli, amount_type) != fid:
            mismatched += 1
            failures.append(f"{fid}: does not recompute with fact_id_workbook from its own row"
                            f" ({exhibit} FY{fy} {pe_bli} {amount_type})")
    counts = Counter(r[0] for r in rows)
    for fid, n in sorted(counts.items()):
        if n > 1:
            failures.append(f"{fid}: fact_id repeats on {n} rows")
    era = [r for r in rows
           if r[2] == "P-1" and r[3] is not None and int(r[3]) <= _ERA_P1_LAST_EDITION]
    re_keyed = [r for r in era if not is_era_procurement_key(r[7])]
    for r in re_keyed:
        failures.append(f"{r[0]}: P-1 FY{r[3]} row has pe_bli {r[7]!r}, not an era key"
                        " (spec §6.1: the lake identity is never re-keyed)")
    if not era:
        failures.append("no PB2017–PB2023 P-1 row: the era-key check would pass vacuously")
    return _leg(not failures,
                f"rows={len(rows)} era_p1_rows={len(era)} mismatched={mismatched}"
                f" duplicate_fact_ids={len(rows) - len(counts)}"
                f" era_rows_without_era_key={len(re_keyed)}", failures)


def leg_e_published_map(*, site_dir: Path, duckdb_path: Path) -> dict:
    """Leg (e): the published p1_era_line_map.parquet is the warehouse's map."""
    import duckdb

    pq = Path(site_dir) / "data" / "p1_era_line_map.parquet"
    if not pq.is_file():
        return _leg(False, "p1_era_line_map.parquet missing", [f"missing {pq}"])
    src = str(pq)
    try:
        con = duckdb.connect(str(duckdb_path), read_only=True)
    except duckdb.Error as e:
        return _leg(False, "warehouse unreadable", [f"cannot open {duckdb_path}: {e}"])
    try:
        try:
            mart_cols = [d[0] for d in con.execute(
                "select * from p1_era_line_map limit 0").description]
        except duckdb.CatalogException:
            return _leg(False, "p1_era_line_map missing from the warehouse",
                        [f"{duckdb_path}: no table p1_era_line_map"])
        pub_cols = [d[0] for d in con.execute(
            "select * from read_parquet(?) limit 0", [src]).description]
        if pub_cols != mart_cols:
            return _leg(False, "columns differ",
                        [f"published columns {pub_cols} != warehouse columns {mart_cols}"])
        mart_rows = con.execute("select count(*) from p1_era_line_map").fetchone()[0]
        pub_rows = con.execute("select count(*) from read_parquet(?)", [src]).fetchone()[0]
        only_mart = con.execute(
            "select count(*) from (select * from p1_era_line_map"
            " except all select * from read_parquet(?))", [src]).fetchone()[0]
        only_pub = con.execute(
            "select count(*) from (select * from read_parquet(?)"
            " except all select * from p1_era_line_map)", [src]).fetchone()[0]
    finally:
        con.close()
    failures: list[str] = []
    if mart_rows == 0:
        failures.append("the warehouse p1_era_line_map is empty")
    if only_mart:
        failures.append(f"{only_mart} warehouse row(s) are not in the published parquet: re-export")
    if only_pub:
        failures.append(f"{only_pub} published row(s) are not in the warehouse map: re-export")
    return _leg(not failures,
                f"mart_rows={mart_rows} published_rows={pub_rows}"
                f" only_in_mart={only_mart} only_published={only_pub}", failures)


def leg_f_history_pin(*, site_dir: Path) -> dict:
    """Leg (f): f15_funding_history.json is byte-identical to the S0 pin."""
    history = Path(site_dir) / "json" / "f15_funding_history.json"
    if not history.is_file():
        return _leg(False, "f15_funding_history.json missing", [f"missing {history}"])
    if not F15_HISTORY_PIN.is_file():
        return _leg(False, "pin missing", [f"missing pin {F15_HISTORY_PIN}"])
    tokens = F15_HISTORY_PIN.read_text().split()
    pin = tokens[0].lower() if tokens else ""
    if not re.fullmatch(r"[0-9a-f]{64}", pin):
        return _leg(False, "pin unreadable",
                    [f"{F15_HISTORY_PIN} does not start with a sha256 hex digest"])
    actual = _sha256_file(history)
    failures = [] if actual == pin else [
        f"{history.name} hashes to {actual}, the S0 pin says {pin}"
        " (only the S5 correction re-pins it)"]
    return _leg(not failures, f"pinned={pin} actual={actual}", failures)


def run_verify_era_map(
```

Edit 4, the dispatch in `run_verify_era_map`. Before:
```python
        elif leg == "c":
            results[leg] = leg_c_f15(map_rows=map_rows)
        else:
            results[leg] = _leg(False, "not implemented",
                                [f"leg {leg} is added by families piece 1 Task 20"])
```
After:
```python
        elif leg == "c":
            results[leg] = leg_c_f15(map_rows=map_rows)
        elif leg == "d":
            results[leg] = leg_d_fact_ids(site_dir=Path(site_dir))
        elif leg == "e":
            results[leg] = leg_e_published_map(site_dir=Path(site_dir),
                                               duckdb_path=Path(duckdb_path))
        else:  # f
            results[leg] = leg_f_history_pin(site_dir=Path(site_dir))
```
Legs d–f do not use the map rows the dispatcher reads for a–c, so an unreadable map still FAILs only a–c (and leg e on
its own terms); `format_report` prints them unchanged because each returns `_leg(...)`.

- [ ] **Step 5: Run the leg tests**

Run:
```bash
uv run --project . pytest tests/test_verify_era_map_def.py tests/test_verify_era_map.py -q
```
Expected: `49 passed` — 23 in `tests/test_verify_era_map_def.py` (6 for d, 8 for e, 7 for f, the dispatch case, the
`format_report` case) and 26 in Task 14's file (its 26, less the deleted placeholder test, plus the second
zero-argument test).

- [ ] **Step 6: Run legs d and f on the live export (read-only), and show leg e fails until the map ships**

Run:
```bash
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python -m govbudget verify-era-map --legs df; echo "exit $?"
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python -m govbudget verify-era-map --legs e; echo "exit $?"
```
Expected (measured 2026-10-02 on the live export with these legs: F-15's 93 era cells are its only PB2017–PB2023 P-1
rows):
```
leg d fact ids: rows=38855 era_p1_rows=93 mismatched=0 duplicate_fact_ids=0 era_rows_without_era_key=0 → PASS
leg f f15 history pin: pinned=9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800 actual=9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800 → PASS
verify-era-map: PASS
exit 0
leg e published map: p1_era_line_map.parquet missing → FAIL
  FAIL missing /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/data/p1_era_line_map.parquet
verify-era-map: FAIL
exit 1
```
The live export predates the map; Task 21 proves leg e on the S4 snapshot and Task 23 on the release export.

- [ ] **Step 7: Commit the legs**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/verify_era_map.py GovBudget/tests/test_verify_era_map_def.py GovBudget/tests/test_verify_era_map.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(verify): verify-era-map legs d-f: decade fact ids recompute, published map equals the warehouse, F-15 history pinned (families piece 1, Task 20a)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 8: Write the failing assembly tests**

Append to `tests/test_verify_phase5.py` after `test_assembly_gate_passes_with_lineage_green` (after `:729`):
```python


# ---------------------------------------------------------------------------
# Tests: assembly era-map leg (families piece 1, spec 2026-10-02 V4/V10).
# verify-era-map is invoked exactly like verify-lineage: subprocess with no
# arguments, verdict parsed from its one final line.
# ---------------------------------------------------------------------------


def test_assembly_phases_end_with_verify_era_map():
    from govbudget.verify_phase5 import _ASSEMBLY_PHASES

    assert "verify-era-map" in _ASSEMBLY_PHASES
    assert _ASSEMBLY_PHASES[-1] == "verify-era-map"
    assert _ASSEMBLY_PHASES.index("verify-lineage") < _ASSEMBLY_PHASES.index("verify-era-map")


def test_verdict_regex_parses_verify_era_map_pass():
    m = _VERDICT_RE.search(
        "leg f f15 history pin: pinned=9f70c770 actual=9f70c770 → PASS\nverify-era-map: PASS\n")
    assert m is not None
    assert m.group(1).upper() == "PASS"


def test_verdict_regex_parses_verify_era_map_fail():
    """PROOF-IT-CAN-FAIL (regex arm): a verify-era-map FAIL verdict is parsed,
    not missed (a miss would fall back to returncode inference)."""
    m = _VERDICT_RE.search(
        "leg e published map: p1_era_line_map.parquet missing → FAIL\n"
        "  FAIL missing data/site/data/p1_era_line_map.parquet\nverify-era-map: FAIL\n")
    assert m is not None
    assert m.group(1).upper() == "FAIL"


def test_assembly_invokes_verify_era_map_with_no_arguments(monkeypatch):
    import govbudget.verify_phase5 as vp5

    seen = []

    def _run(cmd, **kwargs):  # noqa: ANN001
        seen.append(cmd)
        return SimpleNamespace(stdout=f"{cmd[-1]}: PASS\n", stderr="", returncode=0)

    monkeypatch.setattr(vp5.subprocess, "run", _run)
    assembly_gate(repo_root=Path("/nonexistent-not-used"))
    assert ["uv", "run", "python", "-m", "govbudget", "verify-era-map"] in seen


def test_assembly_gate_fails_when_era_map_fails(monkeypatch):
    """PROOF-IT-CAN-FAIL (assembly arm): every other phase PASSes but
    verify-era-map FAILs → the assembly is a hard FAIL."""
    import govbudget.verify_phase5 as vp5

    monkeypatch.setattr(vp5.subprocess, "run", _fake_run_factory({"verify-era-map"}))
    result = assembly_gate(repo_root=Path("/nonexistent-not-used"))
    assert result["ok"] is False
    assert result["blocked"] is False
    rows = [r for r in result["results"] if r["phase"] == "verify-era-map"]
    assert len(rows) == 1
    assert rows[0]["verdict"] == "FAIL"


def test_assembly_gate_passes_with_era_map_green(monkeypatch):
    import govbudget.verify_phase5 as vp5

    monkeypatch.setattr(vp5.subprocess, "run", _fake_run_factory(set()))
    result = assembly_gate(repo_root=Path("/nonexistent-not-used"))
    assert result["ok"] is True
    row = next(r for r in result["results"] if r["phase"] == "verify-era-map")
    assert row["verdict"] == "PASS"
```

Run:
```bash
uv run --project . pytest tests/test_verify_phase5.py -q -k "era_map"
```
Expected: FAIL, `6 failed, 60 deselected` — `test_assembly_phases_end_with_verify_era_map` (`assert 'verify-era-map' in
['verify-phase1', …]`), both regex tests (`assert None is not None`: the old regex matches only `phase\w+|lineage`), the
no-arguments test (`assert ['uv', 'run', 'python', '-m', 'govbudget', 'verify-era-map'] in [...]`), the FAIL arm
(`assert True is False`: nothing ran the era-map gate) and the green arm (`StopIteration`).

- [ ] **Step 9: Wire `verify-era-map` into the assembly in `src/govbudget/verify_phase5.py`**

Docstring, before (`:31-36`):
```python
  3. assembly_gate — subprocess-invokes verify-phase{1,2,3,4,5a,5b1,5b3} (NOT
     5b2 — 5b3 runs the same npm suite) PLUS verify-lineage (the program-
     lineage honesty legs a–e; its leg d audits the built export, so a
     missing built artifact FAILs the leg — same treatment as the other
     build-dependent phase gates). Parses each full output with the verdict
     regex; BLOCKED propagates. Prints a result table.
```
After:
```python
  3. assembly_gate — subprocess-invokes verify-phase{1,2,3,4,5a,5b1,5b3} (NOT
     5b2 — 5b3 runs the same npm suite) PLUS verify-lineage (the program-
     lineage honesty legs a–e; its leg d audits the built export, so a
     missing built artifact FAILs the leg — same treatment as the other
     build-dependent phase gates) PLUS verify-era-map (families piece 1,
     legs a–f: the era P-1 workbooks re-read against the map, no undecided
     or stale decision, F-15's era rows, every budget_lines_decade fact ID
     recomputed from its own row, the published map equal to the
     warehouse's, the F-15 history sha pinned; legs d–f audit the export,
     so a missing artifact FAILs). Parses each full output with the verdict
     regex; BLOCKED propagates. Prints a result table.
```
Phases and regex, before (`:124-146`):
```python
# Sub-phases to check in assembly gate (NOT 5b2 — 5b3 runs same npm suite).
# verify-lineage (the 24th gate — program-lineage honesty legs a–e) is part of
# the automated assembly, not a manual-only CLI a release could skip. Its leg
# (d) audits the BUILT export artifact, so a missing/stale build FAILs the
# leg (and thus this assembly) — consistent with how the other build-dependent
# phase gates already behave (they FAIL on missing artifacts, never skip).
_ASSEMBLY_PHASES = [
    "verify-phase1",
    "verify-phase2",
    "verify-phase3",
    "verify-phase4",
    "verify-phase5a",
    "verify-phase5b1",
    "verify-phase5b3",
    "verify-lineage",
]

# Verdict token regex: parse full output for verdict line. Matches both the
# verify-phaseN family and verify-lineage (whose CLI prints
# "verify-lineage: PASS|FAIL" in the same verdict-line format).
_VERDICT_RE = re.compile(
    r"verify-(?:phase\w+|lineage):\s*(PASS|FAIL|BLOCKED)", re.IGNORECASE
)
```
After:
```python
# Sub-phases to check in assembly gate (NOT 5b2 — 5b3 runs same npm suite).
# verify-lineage (the 24th gate — program-lineage honesty legs a–e) is part of
# the automated assembly, not a manual-only CLI a release could skip. Its leg
# (d) audits the BUILT export artifact, so a missing/stale build FAILs the
# leg (and thus this assembly) — consistent with how the other build-dependent
# phase gates already behave (they FAIL on missing artifacts, never skip).
# verify-era-map (families piece 1, spec 2026-10-02 V4/V10) joins on the same
# terms: invoked with no arguments (its CLI defaults to config.SITE_DIR, the
# warehouse and the repo seed), one final "verify-era-map: PASS|FAIL" line.
_ASSEMBLY_PHASES = [
    "verify-phase1",
    "verify-phase2",
    "verify-phase3",
    "verify-phase4",
    "verify-phase5a",
    "verify-phase5b1",
    "verify-phase5b3",
    "verify-lineage",
    "verify-era-map",
]

# Verdict token regex: parse full output for verdict line. Matches the
# verify-phaseN family, verify-lineage and verify-era-map (whose CLIs print
# "verify-lineage: PASS|FAIL" / "verify-era-map: PASS|FAIL" in the same
# verdict-line format).
_VERDICT_RE = re.compile(
    r"verify-(?:phase\w+|lineage|era-map):\s*(PASS|FAIL|BLOCKED)", re.IGNORECASE
)
```

- [ ] **Step 10: Run the assembly tests**

Run:
```bash
uv run --project . pytest tests/test_verify_phase5.py tests/test_verify_phase5_provider_block.py -q
```
Expected: `96 passed` (66 in `tests/test_verify_phase5.py`, including the 6 new `era_map` tests and the existing
lineage-arm and regex tests, whose fake runner now also prints `verify-era-map: PASS`/`FAIL` for the extended regex to
parse; 30 in `tests/test_verify_phase5_provider_block.py`). Checked 2026-10-02 on a scratch copy of this worktree's
`src/` and `tests/` with Steps 8–9 applied.

- [ ] **Step 11: Commit the assembly wiring**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/verify_phase5.py GovBudget/tests/test_verify_phase5.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(verify): verify-era-map joins the verify-phase5 assembly (families piece 1, Task 20b)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
