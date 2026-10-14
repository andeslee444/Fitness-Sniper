"""scripts/fu/snapshot_pins.py — snapshot and Postgres pins (follow-ups Task 21a)."""
import copy
import json

import psycopg
import pytest

from fu.snapshot_pins import compare_pg_pins, compare_pins, main, pg_table_pins, pins  # scripts/ is on sys.path


def manifest(**over):
    m = {
        "duckdb": {"sha256_at_copy": "a" * 64, "sha256": "b" * 64},
        "parquet": {"jbooks/budget_lines.parquet": {"sha256": "c" * 64, "bytes": 1, "rows": 1},
                    "sam/daily/state.json": {"sha256": "d" * 64, "bytes": 1, "rows": None}},
        "site": {"sha256": "e" * 64, "files": 1, "bytes": 1},
        "raw_docs": {"sha256": "f" * 64, "files": 1, "bytes": 1},
        "manifest_jsonl_sha256": "0" * 64,
        "pg": {"dump_sha256": "1" * 64, "tables": {"budget_lines": {"rows": 2, "md5": "x"}}},
    }
    m.update(over)
    return m


def test_two_snapshots_of_one_state_are_equal_whatever_their_dump_sha_or_sam_files():
    a = manifest()
    b = copy.deepcopy(a)
    b["pg"]["dump_sha256"] = "9" * 64            # pg_dump headers carry a timestamp
    b["duckdb"]["sha256"] = "8" * 64             # after the view rewrite: not a pin
    b["parquet"]["sam/daily/state.json"]["sha256"] = "7" * 64
    assert compare_pins(pins(a), pins(b)) == []


@pytest.mark.parametrize("path, value", [
    (("duckdb", "sha256_at_copy"), "2" * 64),
    (("site", "sha256"), "3" * 64),
    (("raw_docs", "sha256"), "4" * 64),
    (("manifest_jsonl_sha256",), "5" * 64),
    (("parquet", "jbooks/budget_lines.parquet", "sha256"), "6" * 64),
    (("pg", "tables", "budget_lines", "md5"), "y"),
])
def test_any_pin_that_moves_is_reported(path, value):
    b = manifest()
    node = b
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    assert compare_pins(pins(manifest()), pins(b))


def test_a_parquet_file_only_on_one_side_is_reported():
    b = manifest()
    b["parquet"]["jbooks/new.parquet"] = {"sha256": "c" * 64, "bytes": 1, "rows": 1}
    assert compare_pins(pins(manifest()), pins(b)) == ["parquet: only in B: jbooks/new.parquet"]


def test_compare_cli_reads_snapshot_dirs(tmp_path, capsys):
    for name, m in (("a", manifest()), ("b", manifest())):
        (tmp_path / name).mkdir()
        (tmp_path / name / "snapshot.json").write_text(json.dumps(m))
    assert main(["compare", str(tmp_path / "a"), str(tmp_path / "b")]) == 0
    assert capsys.readouterr().out.strip().endswith("snapshot-pins: EQUAL")
    assert main(["compare", str(tmp_path / "a"), str(tmp_path / "missing")]) == 2
    assert "snapshot-pins: ERROR — " in capsys.readouterr().err


def test_pg_pins_track_content_not_row_order_and_honour_drop(pg_dsn):
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("drop table if exists fu_pin_probe")
        con.execute("create table fu_pin_probe (id bigint, code text, amount numeric)")
        con.execute("insert into fu_pin_probe values (1, 'O&M', 87404), (2, 'RDT&E', 1002560)")
    first = pg_table_pins(pg_dsn)
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("delete from fu_pin_probe")
        con.execute("insert into fu_pin_probe values (2, 'RDT&E', 1002560), (1, 'O&M', 87404)")
    assert pg_table_pins(pg_dsn) == first                       # row order is not content
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("update fu_pin_probe set id = 9 where id = 1")
    moved = pg_table_pins(pg_dsn)
    assert compare_pg_pins(first, moved) == (False, [
        f"fu_pin_probe: differs: rows 2 -> 2, md5 {first['fu_pin_probe']['md5']} -> {moved['fu_pin_probe']['md5']}"])
    assert compare_pg_pins(first, moved, ["fu_pin_probe"])[0]
    no_id_before = pg_table_pins(pg_dsn, {"fu_pin_probe": ["id"]})
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("update fu_pin_probe set id = 1 where id = 9")
    assert pg_table_pins(pg_dsn, {"fu_pin_probe": ["id"]}) == no_id_before   # only the id moved
    with pytest.raises(ValueError, match="dropped different columns"):
        compare_pg_pins(first, no_id_before)
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("drop table fu_pin_probe")


def test_pg_cli_writes_and_compares(pg_dsn, tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    assert main(["pg", "--dsn", pg_dsn, "--out", str(a)]) == 0
    assert main(["pg", "--dsn", pg_dsn, "--out", str(b)]) == 0
    assert main(["pg-compare", str(a), str(b)]) == 0
    assert capsys.readouterr().out.strip().endswith("pg-pins: EQUAL")
    assert main(["pg-compare", str(a), str(b), "--changed", "budget_lines"]) == 1
    assert "pg-pins: FAIL (expected to differ: budget_lines)" in capsys.readouterr().out
    assert main(["pg", "--dsn", pg_dsn, "--out", str(a), "--drop", "nosuchtable.id"]) == 2
