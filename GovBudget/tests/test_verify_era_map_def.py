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
