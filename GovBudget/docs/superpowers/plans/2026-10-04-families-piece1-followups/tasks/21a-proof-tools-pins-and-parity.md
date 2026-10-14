<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 21a: Release-1 proof tools — snapshot pins and lake parity

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §7 "Snapshots" (the cross-review Postgres pin: each table's row count and row md5, not the dump sha), §4.4 "Proof" (after the live write, the 0390D rows and the rebuilt marts must equal fu-post's, `EXCEPT` both ways), §8 step 1 (a fresh snapshot carries fu-pre's pins, SAM files excepted) and step 2 (`lake_parity.py` against fu-post), §2.3 Q24 (b) (the `--revert` rehearsal needs a before/after pin), §6 (one CLI convention: a tool error prints `<tool>: ERROR — <message>` and exits 2).

**Files:**
- Create: `scripts/fu/snapshot_pins.py`, `tests/test_fu_snapshot_pins.py`
- Create: `scripts/fu/lake_parity.py`, `tests/test_fu_lake_parity.py`

`scripts/fu/` is a new directory with no `__init__.py`, like `scripts/era/`: `tests/conftest.py:23` puts `scripts/` on `sys.path`, so the tests import `fu.snapshot_pins` and `fu.lake_parity` as a namespace package.

**Interfaces:**
Consumes:
- `govbudget proof snapshot`'s `snapshot.json` keys, as written today by `src/govbudget/proof.py` `snapshot()` and kept by Task 2: `duckdb.sha256_at_copy`, `parquet` (`{path relative to parquet/: {"sha256", "bytes", "rows"}}`), `site.sha256`, `raw_docs.sha256`, `manifest_jsonl_sha256`, `pg.tables` (`{table: {"rows", "md5"}}`, computed by `_pg_snapshot` with `set time zone 'UTC'`, `set datestyle = 'ISO, YMD'`, `set extra_float_digits = 1` and `md5(coalesce(string_agg(md5(t::text), '' order by …), ''))` before the `jbook_documents.file_path` rewrite).
- The root `tests/conftest.py` fixture `pg_dsn` (a migrated scratch database on the throwaway cluster `GOVBUDGET_TEST_PG_DSN`).
Produces:
- `scripts/fu/snapshot_pins.py`: `SAM_PREFIX = "sam/"`; `pins(manifest: dict) -> dict`; `compare_pins(a: dict, b: dict) -> list[str]`; `load_snapshot(path: Path) -> dict` (a snapshot directory or its `snapshot.json`); `pg_table_pins(dsn: str, drop: dict[str, list[str]] | None = None) -> dict[str, {"rows": int, "md5": str, "drop": list[str]}]`; `compare_pg_pins(a, b, changed: list[str] | None = None) -> tuple[bool, list[str]]`; CLI `compare SNAP_A SNAP_B` (last line `snapshot-pins: EQUAL|DIFFERENT`), `pg --dsn DSN --out FILE [--drop TABLE.COLUMN ...]` (`pg-pins: <n> tables, <rows> rows -> FILE`), `pg-compare A.json B.json [--changed TABLE ...]` (`pg-pins: EQUAL|DIFFERENT`, or with `--changed` `pg-pins: PASS|FAIL (expected to differ: …)`); exit 0/1, tool error exit 2.
- `scripts/fu/lake_parity.py`: `run(a_root, b_root, *, relations: list[str], parquet: list[str], work: Path, pg: tuple[dsn_a, dsn_b, table, where] | None) -> dict`; `compare_relation`, `compare_parquet`, `compare_pg`; CLI `--a ROOT --b ROOT [--relation NAME ...] [--parquet REL ...] [--pg-a DSN --pg-b DSN --pg-table budget_lines --pg-where SQL] --work DIR [--report FILE]`, one line per check, last line `lake-parity: EQUAL|DIFFERENT`; exit 0/1, tool error exit 2. A lake root is a directory holding `duckdb/govbudget.duckdb` and `parquet/` (the live `GOVBUDGET_DATA`, or a snapshot directory).
- Used by Task 21d (fu-pre vs fu-post pins), Task 21e (fu-pre's pre-write pins), Task 21f (the fu-pre `--revert` rehearsal pins and the abort rehearsal's parity), Task 22a (fu-rel vs fu-pre; live pins before the write), Task 22b (live vs fu-post parity; the abort path's live vs fu-pre parity).

Measured for this task (2026-10-13, read-only, outside :12–:22): both tools were prototyped in `.superpowers/sdd/2026-10-04-piece1-followups/work/G5/` with exactly the code below and passed the tests below (11 + 6) against the throwaway cluster. `lake_parity.py` run read-only on the live lake against a second root whose `duckdb/` and `parquet/` are symlinks to the same lake read `EQUAL` in 1.5 s: `stg_budget_lines` 159,903 rows, `fct_budget_lines` 159,903, `fct_decade_series` 59,179, `fct_book_diff` 18,412, `p1_era_code_decisions` 1,253, `p1_era_line_map` 6,927, `fct_program_decade_series` 57,886, `fct_budget_trajectory` 1,988, `parquet/jbooks/budget_lines.parquet` 159,903. The DOUBLE columns in those relations are `amount_thousands` (`stg_budget_lines`, `fct_budget_lines`), `amount`/`amount_thousands` (`fct_decade_series`, `fct_program_decade_series`) and `from_value`/`to_value`/`delta` (`fct_book_diff`): sums and differences of Postgres `numeric` USD-thousand amounts, which is why the tool compares DOUBLE columns rounded to 3 decimals. DuckDB 1.5.3 sums `[0.1, 0.2, 0.3]` to `0.6000000000000001` and `[0.3, 0.2, 0.1]` to `0.6`, which the test below uses. A read-only DuckDB connection can `COPY … TO` a file outside the database (checked on a scratch database). Postgres `budget_lines` has no timestamp column (`\d budget_lines`: `id … line_item_code`), so two databases that took the same write differ at most in the ids of inserted rows.

- [ ] **Step 1: Write the failing snapshot-pin tests**

Create `tests/test_fu_snapshot_pins.py`:

```python
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
```

- [ ] **Step 2: Write the failing lake-parity tests**

Create `tests/test_fu_lake_parity.py`:

```python
"""scripts/fu/lake_parity.py — two lakes hold the same rows (follow-ups Task 21a)."""
import os
from urllib.parse import urlsplit, urlunsplit

import duckdb
import psycopg
import pytest

from fu.lake_parity import compare_pg, main, run  # scripts/ is on sys.path

ADMIN_DSN = os.environ.get("GOVBUDGET_TEST_PG_DSN", "postgresql://localhost/postgres")


def lake(root, rows, *, amounts=(0.1, 0.2, 0.3), schema="(code varchar, amount double)"):
    (root / "duckdb").mkdir(parents=True)
    (root / "parquet" / "jbooks").mkdir(parents=True)
    src = root / "parquet" / "jbooks" / "x.parquet"
    con = duckdb.connect()
    con.execute(f"create table t {schema}")
    con.executemany("insert into t values (?, ?)", rows)
    con.execute(f"copy t to '{src}' (format parquet)")
    con.close()
    con = duckdb.connect(str(root / "duckdb" / "govbudget.duckdb"))
    con.execute(f"create view v as select * from read_parquet('{src}')")
    con.execute("create table m as select sum(x) as total from (select unnest(?::double[]) as x)", [list(amounts)])
    con.close()
    return root


def test_equal_lakes_read_their_own_parquet_and_ignore_float_last_bits(tmp_path):
    a = lake(tmp_path / "a", [("O&M", 87404.0), ("0390DOM", 3243.0)])
    b = lake(tmp_path / "b", [("0390DOM", 3243.0), ("O&M", 87404.0)], amounts=(0.3, 0.2, 0.1))  # 0.6000000000000001 vs 0.6
    report = run(a, b, relations=["v", "m"], parquet=["jbooks/x.parquet"], work=tmp_path / "w")
    assert report["ok"], report
    assert report["relations"]["v"]["rows_a"] == 2


def test_a_moved_row_is_found_both_ways(tmp_path):
    a = lake(tmp_path / "a", [("O&M", 87404.0), ("RDT&E", 1002560.0)])
    b = lake(tmp_path / "b", [("0390DOM", 87404.0), ("RDT&E", 1002560.0)])
    report = run(a, b, relations=["v"], parquet=["jbooks/x.parquet"], work=tmp_path / "w")
    assert not report["ok"]
    assert (report["relations"]["v"]["a_not_b"], report["relations"]["v"]["b_not_a"]) == (1, 1)
    assert report["parquet"]["jbooks/x.parquet"]["samples_b_not_a"] == [{"code": "0390DOM", "amount": "87404.0"}]


def test_a_duplicate_row_is_a_difference(tmp_path):
    a = lake(tmp_path / "a", [("O&M", 1.0)])
    b = lake(tmp_path / "b", [("O&M", 1.0), ("O&M", 1.0)])
    assert run(a, b, relations=["v"], parquet=[], work=tmp_path / "w")["relations"]["v"]["b_not_a"] == 1


def test_a_schema_change_is_a_difference(tmp_path):
    a = lake(tmp_path / "a", [("O&M", 1.0)])
    b = lake(tmp_path / "b", [("O&M", 1)], schema="(code varchar, amount bigint)")
    assert run(a, b, relations=["v"], parquet=[], work=tmp_path / "w")["relations"]["v"]["schema_equal"] is False


def test_cli_verdicts_and_tool_errors(tmp_path, capsys):
    a = lake(tmp_path / "a", [("O&M", 1.0)])
    b = lake(tmp_path / "b", [("O&M", 1.0)])
    assert main(["--a", str(a), "--b", str(b), "--relation", "v", "--work", str(tmp_path / "w")]) == 0
    assert capsys.readouterr().out.strip().endswith("lake-parity: EQUAL")
    c = lake(tmp_path / "c", [("O&M", 2.0)])
    assert main(["--a", str(a), "--b", str(c), "--relation", "v", "--work", str(tmp_path / "w2")]) == 1
    assert capsys.readouterr().out.strip().endswith("lake-parity: DIFFERENT")
    assert main(["--a", str(a), "--b", str(b), "--relation", "nosuch", "--work", str(tmp_path / "w3")]) == 2
    assert "lake-parity: ERROR — " in capsys.readouterr().err
    assert main(["--a", str(a), "--b", str(a), "--relation", "v", "--work", str(tmp_path / "w4")]) == 2


@pytest.fixture
def two_dbs():
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    except psycopg.OperationalError as e:
        pytest.skip(f"Postgres unavailable ({e})")
    names = ["govbudget_test_fu_parity_a", "govbudget_test_fu_parity_b"]
    dsns = []
    for name in names:
        admin.execute(f"drop database if exists {name}")
        admin.execute(f"create database {name}")
        dsn = urlunsplit(urlsplit(ADMIN_DSN)._replace(path="/" + name))
        with psycopg.connect(dsn, autocommit=True) as con:
            con.execute("create table budget_lines (id bigint primary key, account text, pe_bli text,"
                        " fiscal_year integer, amount_thousands numeric)")
        dsns.append(dsn)
    yield dsns
    for name in names:
        admin.execute(f"drop database if exists {name}")
    admin.close()


def test_postgres_rows_compare_without_ids(two_dbs):
    a, b = two_dbs
    with psycopg.connect(a, autocommit=True) as con:
        con.execute("insert into budget_lines values (47733, '0390D', '0390DOM', 2025, 84612),"
                    " (581202, '0390D', '0390DOM', 2026, 3243), (1, '3010F', 'F015EX', 2026, 1)")
    with psycopg.connect(b, autocommit=True) as con:
        con.execute("insert into budget_lines values (47733, '0390D', '0390DOM', 2025, 84612),"
                    " (581206, '0390D', '0390DOM', 2026, 3243), (1, '3010F', 'F015EX', 2026, 2)")
    report = compare_pg(a, b, "budget_lines", "account = '0390D'")
    assert report["ok"] and report["ids_equal"] is False
    assert (report["ids_a"], report["ids_b"]) == ([47733, 581202], [47733, 581206])
    with psycopg.connect(b, autocommit=True) as con:
        con.execute("update budget_lines set amount_thousands = 3244 where id = 581206")
    report = compare_pg(a, b, "budget_lines", "account = '0390D'")
    assert not report["ok"] and (report["a_not_b"], report["b_not_a"]) == (1, 1)
```

- [ ] **Step 3: Run both files to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_fu_snapshot_pins.py tests/test_fu_lake_parity.py -q`
Expected: two collection errors, each `ModuleNotFoundError: No module named 'fu'`.

- [ ] **Step 4: Implement `scripts/fu/snapshot_pins.py`**

```python
#!/usr/bin/env python3
"""Pins of a pinned proof snapshot and of a Postgres database (families piece-1
follow-ups, Task 21a; design §7 "Snapshots", §4.4, §8 step 1, Q24 (b)).

`govbudget proof snapshot` writes snapshot.json. Two snapshots of one unchanged
lake must carry the same pins, but not the same dump sha256: pg_dump
--format=custom records its creation time in the archive header. So the
Postgres pin is each table's row count and row md5 (snapshot.json
`pg.tables`, computed on the restored dump before the document paths are
repointed). The other pins:

  duckdb_sha256_at_copy  the DuckDB file's sha256 right after the copy;
  parquet                every parquet/ file's sha256, except under sam/ (the
                         hourly SAM job rewrites sam/daily/state.json every
                         hour; the follow-ups never read sam/);
  site, raw_docs         the two tree digests;
  manifest_jsonl_sha256  the lake manifest.

Subcommands:

  compare SNAP_A SNAP_B
      Every pin equal? Last line `snapshot-pins: EQUAL|DIFFERENT`.
  pg --dsn DSN --out FILE [--drop TABLE.COLUMN ...]
      Row count and row md5 of every public base table, with the query and
      session settings `govbudget proof snapshot` uses. --drop leaves a
      column out of that table's row text (the md5 is then over the row's
      jsonb minus those keys, and the pin records which keys were dropped).
  pg-compare A.json B.json [--changed TABLE ...]
      Without --changed: `pg-pins: EQUAL|DIFFERENT`. With --changed: PASS
      when exactly the named tables differ and every other table is equal,
      else FAIL. Pins taken with different --drop lists never compare.

Exit 0 on EQUAL/PASS, 1 on DIFFERENT/FAIL, 2 on a tool error, printed as
`<subcommand>: ERROR — <message>` (design §6 CLI convention).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SAM_PREFIX = "sam/"
SNAPSHOT_MANIFEST = "snapshot.json"


def pins(manifest: dict) -> dict:
    """The comparable pins of one snapshot.json."""
    return {
        "duckdb_sha256_at_copy": manifest["duckdb"]["sha256_at_copy"],
        "parquet": {rel: entry["sha256"] for rel, entry in sorted(manifest["parquet"].items())
                    if not rel.startswith(SAM_PREFIX)},
        "site_sha256": manifest["site"]["sha256"],
        "raw_docs_sha256": manifest["raw_docs"]["sha256"],
        "manifest_jsonl_sha256": manifest["manifest_jsonl_sha256"],
        "pg_tables": {name: [entry["rows"], entry["md5"]]
                      for name, entry in sorted(manifest["pg"]["tables"].items())},
    }


def compare_pins(a: dict, b: dict) -> list[str]:
    """Human-readable differences between two pins() results; [] when equal."""
    out: list[str] = []
    for key in ("duckdb_sha256_at_copy", "site_sha256", "raw_docs_sha256", "manifest_jsonl_sha256"):
        if a[key] != b[key]:
            out.append(f"{key}: {a[key]} != {b[key]}")
    for name in ("parquet", "pg_tables"):
        only_a = sorted(set(a[name]) - set(b[name]))
        only_b = sorted(set(b[name]) - set(a[name]))
        changed = sorted(k for k in set(a[name]) & set(b[name]) if a[name][k] != b[name][k])
        out += [f"{name}: only in A: {k}" for k in only_a]
        out += [f"{name}: only in B: {k}" for k in only_b]
        out += [f"{name}: differs: {k}: {a[name][k]} != {b[name][k]}" for k in changed]
    return out


def load_snapshot(path: Path) -> dict:
    path = Path(path)
    if path.is_dir():
        path = path / SNAPSHOT_MANIFEST
    return json.loads(path.read_text(encoding="utf-8"))


def pg_table_pins(dsn: str, drop: dict[str, list[str]] | None = None) -> dict:
    """{table: {"rows", "md5", "drop"}} for every public base table.

    The query and session settings are `govbudget proof snapshot`'s
    (proof._pg_snapshot), so a pin taken here on a database equals the pin
    the snapshot took on its restored dump of that database."""
    import psycopg
    from psycopg import sql

    drop = drop or {}
    out: dict[str, dict] = {}
    with psycopg.connect(dsn) as con:
        con.execute("set time zone 'UTC'")
        con.execute("set datestyle = 'ISO, YMD'")
        con.execute("set extra_float_digits = 1")
        names = [r[0] for r in con.execute(
            "select table_name from information_schema.tables"
            " where table_schema = 'public' and table_type = 'BASE TABLE'"
            " order by table_name"
        ).fetchall()]
        unknown = sorted(set(drop) - set(names))
        if unknown:
            raise ValueError(f"--drop names tables that do not exist: {unknown}")
        for name in names:
            keys = sorted(drop.get(name, []))
            if keys:
                row_text = sql.SQL("(to_jsonb(t) - {}::text[])::text").format(sql.Literal(keys))
            else:
                row_text = sql.SQL("t::text")
            rows, digest = con.execute(sql.SQL(
                "select count(*), md5(coalesce(string_agg(h, '' order by h), ''))"
                " from (select md5({}) as h from {} t) s"
            ).format(row_text, sql.Identifier("public", name))).fetchone()
            out[name] = {"rows": int(rows), "md5": digest, "drop": keys}
        con.rollback()
    return out


def compare_pg_pins(a: dict, b: dict, changed: list[str] | None = None) -> tuple[bool, list[str]]:
    """(ok, lines). Without `changed`: ok when every table is equal. With it:
    ok when exactly those tables differ and every other one is equal."""
    lines: list[str] = []
    for name in sorted(set(a) | set(b)):
        if name not in a or name not in b:
            lines.append(f"{name}: only in {'A' if name in a else 'B'}")
            continue
        if a[name]["drop"] != b[name]["drop"]:
            raise ValueError(f"{name}: pins dropped different columns ({a[name]['drop']} vs {b[name]['drop']})")
        if (a[name]["rows"], a[name]["md5"]) != (b[name]["rows"], b[name]["md5"]):
            lines.append(f"{name}: differs: rows {a[name]['rows']} -> {b[name]['rows']}, "
                         f"md5 {a[name]['md5']} -> {b[name]['md5']}")
    differing = sorted(line.split(":", 1)[0] for line in lines)
    if changed is None:
        return not lines, lines
    want = sorted(set(changed))
    return differing == want, lines


def _parse_drop(values: list[str]) -> dict[str, list[str]]:
    drop: dict[str, list[str]] = {}
    for item in values or []:
        table, sep, column = item.partition(".")
        if not sep or not table or not column:
            raise ValueError(f"--drop takes TABLE.COLUMN, not {item!r}")
        drop.setdefault(table, []).append(column)
    return drop


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Snapshot and Postgres pins for the follow-ups proofs")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare", help="compare two snapshots' pins")
    c.add_argument("a", type=Path)
    c.add_argument("b", type=Path)
    g = sub.add_parser("pg", help="pin every public table of a Postgres database")
    g.add_argument("--dsn", required=True)
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--drop", action="append", default=[], metavar="TABLE.COLUMN")
    k = sub.add_parser("pg-compare", help="compare two pg pin files")
    k.add_argument("a", type=Path)
    k.add_argument("b", type=Path)
    k.add_argument("--changed", action="append", default=None, metavar="TABLE")
    args = p.parse_args(argv)
    label = {"compare": "snapshot-pins", "pg": "pg-pins", "pg-compare": "pg-pins"}[args.cmd]
    try:
        if args.cmd == "compare":
            diffs = compare_pins(pins(load_snapshot(args.a)), pins(load_snapshot(args.b)))
            for line in diffs:
                print(f"  {line}")
            print(f"snapshot-pins: {'EQUAL' if not diffs else 'DIFFERENT'}")
            return 0 if not diffs else 1
        if args.cmd == "pg":
            result = pg_table_pins(args.dsn, _parse_drop(args.drop))
            args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print(f"pg-pins: {len(result)} tables, {sum(t['rows'] for t in result.values()):,} rows -> {args.out}")
            return 0
        a = json.loads(args.a.read_text(encoding="utf-8"))
        b = json.loads(args.b.read_text(encoding="utf-8"))
        ok, lines = compare_pg_pins(a, b, args.changed)
        for line in lines:
            print(f"  {line}")
        if args.changed is None:
            print(f"pg-pins: {'EQUAL' if ok else 'DIFFERENT'}")
        else:
            print(f"pg-pins: {'PASS' if ok else 'FAIL'} (expected to differ: {', '.join(sorted(set(args.changed)))})")
        return 0 if ok else 1
    except Exception as e:  # noqa: BLE001 — a tool error is exit 2, never a FAIL
        print(f"{label}: ERROR — {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `scripts/fu/lake_parity.py`**

```python
#!/usr/bin/env python3
"""Lake parity: two lakes (and two Postgres databases) hold the same rows
(families piece-1 follow-ups, Task 21a; design §4.4 "Proof", §8 steps 1-2, Q24 (b)).

After the live writes, the live lake must equal the rehearsal on snapshot
fu-post: "the 0390D rows in the live Postgres must equal fu-post's, and the
rebuilt marts must equal fu-post's (EXCEPT both ways)". The abort path uses the
same check against fu-pre after a revert.

A lake is a root with duckdb/govbudget.duckdb and parquet/ (the live
GOVBUDGET_DATA, or a `govbudget proof snapshot` directory). For each
--relation, each side's DuckDB is opened read-only and the relation is copied
to a parquet file under --work; the two copies are compared as row multisets
(EXCEPT ALL, both ways) after a schema check (names and types, in order). Each
--parquet file (relative to parquet/) is compared the same way. DOUBLE and
FLOAT columns compare rounded to 3 decimals: in the relations this proof names
every such column is a sum or difference of USD-thousand amounts that Postgres
stores with at most 3 decimals, so float error (well under 1e-6) cannot cross a
rounding boundary, while two parallel sums of one input may differ in the last
bit.

With --pg-a/--pg-b, the rows of --pg-table matching --pg-where are compared as
multisets over every column except `id`; ids are reported, not judged (a
sequence value spent by a rolled-back or reverted run moves an inserted row's id
and nothing else).

Last line `lake-parity: EQUAL|DIFFERENT`; exit 0/1; a tool error prints
`lake-parity: ERROR — <message>` and exits 2.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DUCKDB_REL = Path("duckdb") / "govbudget.duckdb"
FLOAT_TYPES = frozenset({"DOUBLE", "FLOAT", "REAL"})
SAMPLE_ROWS = 3


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _canonical_select(con, source_sql: str) -> tuple[list[tuple[str, str]], str]:
    schema = [(r[0], r[1]) for r in con.execute(f"describe select * from {source_sql}").fetchall()]
    cols = [f"round({_quote(n)}, 3) as {_quote(n)}" if t in FLOAT_TYPES else _quote(n) for n, t in schema]
    return schema, f"select {', '.join(cols)} from {source_sql}"


def _export(root: Path, source_sql: str, out: Path, *, relation: bool) -> list[tuple[str, str]]:
    import duckdb

    out.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(root / DUCKDB_REL), read_only=True) if relation else duckdb.connect()
    try:
        schema, select = _canonical_select(con, source_sql)
        con.execute(f"copy ({select}) to '{out.as_posix()}' (format parquet)")
    finally:
        con.close()
    return schema


def _compare_files(pa: Path, pb: Path) -> dict:
    import duckdb

    con = duckdb.connect()
    try:
        a, b = f"read_parquet('{pa.as_posix()}')", f"read_parquet('{pb.as_posix()}')"
        rows_a = con.execute(f"select count(*) from {a}").fetchone()[0]
        rows_b = con.execute(f"select count(*) from {b}").fetchone()[0]
        cur = con.execute(f"select * from {a} except all select * from {b}")
        cols = [d[0] for d in cur.description]
        a_not_b = cur.fetchall()
        b_not_a = con.execute(f"select * from {b} except all select * from {a}").fetchall()
    finally:
        con.close()
    return {"rows_a": rows_a, "rows_b": rows_b, "a_not_b": len(a_not_b), "b_not_a": len(b_not_a),
            "samples_a_not_b": [dict(zip(cols, map(str, r))) for r in a_not_b[:SAMPLE_ROWS]],
            "samples_b_not_a": [dict(zip(cols, map(str, r))) for r in b_not_a[:SAMPLE_ROWS]]}


def compare_relation(a_root: Path, b_root: Path, name: str, work: Path) -> dict:
    sa = _export(a_root, _quote(name), work / "a" / f"{name}.parquet", relation=True)
    sb = _export(b_root, _quote(name), work / "b" / f"{name}.parquet", relation=True)
    if sa != sb:
        return {"ok": False, "schema_equal": False, "schema_a": sa, "schema_b": sb}
    result = _compare_files(work / "a" / f"{name}.parquet", work / "b" / f"{name}.parquet")
    return {"ok": result["a_not_b"] == 0 and result["b_not_a"] == 0, "schema_equal": True, **result}


def compare_parquet(a_root: Path, b_root: Path, rel: str, work: Path) -> dict:
    stem = rel.replace("/", "__")
    pa, pb = a_root / "parquet" / rel, b_root / "parquet" / rel
    for path in (pa, pb):
        if not path.is_file():
            raise FileNotFoundError(f"{path} is missing")
    sa = _export(a_root, f"read_parquet('{pa.as_posix()}')", work / "a" / f"{stem}", relation=False)
    sb = _export(b_root, f"read_parquet('{pb.as_posix()}')", work / "b" / f"{stem}", relation=False)
    if sa != sb:
        return {"ok": False, "schema_equal": False, "schema_a": sa, "schema_b": sb}
    result = _compare_files(work / "a" / stem, work / "b" / stem)
    return {"ok": result["a_not_b"] == 0 and result["b_not_a"] == 0, "schema_equal": True, **result}


def _pg_rows(dsn: str, table: str, where: str) -> tuple[list[str], list[tuple], list[int]]:
    import psycopg
    from psycopg import sql

    with psycopg.connect(dsn) as con:
        cur = con.execute(sql.SQL("select * from {} where " + where + " order by id").format(
            sql.Identifier("public", table)))
        cols = [d.name for d in cur.description]
        rows = cur.fetchall()
        con.rollback()
    i = cols.index("id")
    return ([c for c in cols if c != "id"],
            sorted(tuple(map(str, r[:i] + r[i + 1:])) for r in rows),
            [r[i] for r in rows])


def compare_pg(dsn_a: str, dsn_b: str, table: str, where: str) -> dict:
    cols_a, rows_a, ids_a = _pg_rows(dsn_a, table, where)
    cols_b, rows_b, ids_b = _pg_rows(dsn_b, table, where)
    if cols_a != cols_b:
        return {"ok": False, "columns_equal": False, "columns_a": cols_a, "columns_b": cols_b}
    from collections import Counter

    ca, cb = Counter(rows_a), Counter(rows_b)
    a_not_b, b_not_a = sorted((ca - cb).elements()), sorted((cb - ca).elements())
    return {"ok": not a_not_b and not b_not_a, "columns_equal": True, "rows_a": len(rows_a),
            "rows_b": len(rows_b), "a_not_b": len(a_not_b), "b_not_a": len(b_not_a),
            "ids_equal": ids_a == ids_b, "ids_a": ids_a, "ids_b": ids_b,
            "samples_a_not_b": [dict(zip(cols_a, r)) for r in a_not_b[:SAMPLE_ROWS]],
            "samples_b_not_a": [dict(zip(cols_b, r)) for r in b_not_a[:SAMPLE_ROWS]]}


def run(a_root: Path, b_root: Path, *, relations: list[str], parquet: list[str], work: Path,
        pg: tuple[str, str, str, str] | None = None) -> dict:
    a_root, b_root, work = Path(a_root).resolve(), Path(b_root).resolve(), Path(work)
    if a_root == b_root:
        raise ValueError("--a and --b are the same lake")
    out = {"relations": {}, "parquet": {}, "pg": None}
    for name in relations:
        out["relations"][name] = compare_relation(a_root, b_root, name, work)
    for rel in parquet:
        out["parquet"][rel] = compare_parquet(a_root, b_root, rel, work)
    if pg is not None:
        out["pg"] = compare_pg(*pg)
    checks = list(out["relations"].values()) + list(out["parquet"].values()) + ([out["pg"]] if out["pg"] else [])
    out["ok"] = bool(checks) and all(c["ok"] for c in checks)
    return out


def _line(label: str, r: dict) -> str:
    if not r.get("schema_equal", r.get("columns_equal", True)):
        return f"{label}: SCHEMA DIFFERS"
    text = (f"{label}: A {r['rows_a']:,} rows, B {r['rows_b']:,} rows, "
            f"A not in B {r['a_not_b']:,}, B not in A {r['b_not_a']:,}")
    if "ids_equal" in r:
        text += f", ids {'equal' if r['ids_equal'] else 'differ'}"
    return text + (" — equal" if r["ok"] else " — DIFFERENT")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Row-multiset parity of two lakes (and two Postgres databases)")
    p.add_argument("--a", type=Path, required=True, help="lake root A (duckdb/govbudget.duckdb, parquet/)")
    p.add_argument("--b", type=Path, required=True, help="lake root B")
    p.add_argument("--relation", action="append", default=[], help="a DuckDB table or view, repeatable")
    p.add_argument("--parquet", action="append", default=[], help="a file under parquet/, repeatable")
    p.add_argument("--pg-a", default=None)
    p.add_argument("--pg-b", default=None)
    p.add_argument("--pg-table", default="budget_lines")
    p.add_argument("--pg-where", default=None, help="SQL predicate selecting the rows to compare")
    p.add_argument("--work", type=Path, required=True, help="scratch directory for the copies")
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        pg = None
        if args.pg_a or args.pg_b or args.pg_where:
            if not (args.pg_a and args.pg_b and args.pg_where):
                raise ValueError("--pg-a, --pg-b and --pg-where go together")
            pg = (args.pg_a, args.pg_b, args.pg_table, args.pg_where)
        report = run(args.a, args.b, relations=args.relation, parquet=args.parquet, work=args.work, pg=pg)
    except Exception as e:  # noqa: BLE001 — a tool error is exit 2, never a verdict
        print(f"lake-parity: ERROR — {e}", file=sys.stderr)
        return 2
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    for name, r in report["relations"].items():
        print(_line(f"relation {name}", r))
    for rel, r in report["parquet"].items():
        print(_line(f"parquet {rel}", r))
    if report["pg"] is not None:
        print(_line(f"postgres {args.pg_table} where {args.pg_where}", report["pg"]))
    for section in ("relations", "parquet"):
        for name, r in report[section].items():
            for sample in r.get("samples_a_not_b", []) + r.get("samples_b_not_a", []):
                print(f"  {name}: {sample}")
    if report["pg"]:
        for sample in report["pg"].get("samples_a_not_b", []) + report["pg"].get("samples_b_not_a", []):
            print(f"  postgres: {sample}")
    print(f"lake-parity: {'EQUAL' if report['ok'] else 'DIFFERENT'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_fu_snapshot_pins.py tests/test_fu_lake_parity.py -q && uvx --offline ruff check --isolated --select F,E9 scripts/fu/snapshot_pins.py scripts/fu/lake_parity.py tests/test_fu_snapshot_pins.py tests/test_fu_lake_parity.py`
Expected: `17 passed`, then `All checks passed!`.

- [ ] **Step 7: Smoke-test lake parity on the live lake, read-only**

This reads the live lake, so it carries the SAM guard (on `WAIT`, wait until :23 and re-run the block). It writes only under `.proofs/fu-logs/`, and records the pre-write counts the later tasks compare with.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs" && mkdir -p "$L/liveroot-twin" && ln -sfn "$GOVBUDGET_DATA/duckdb" "$L/liveroot-twin/duckdb" && ln -sfn "$GOVBUDGET_DATA/parquet" "$L/liveroot-twin/parquet"
uv run --project . python scripts/fu/lake_parity.py --a "$GOVBUDGET_DATA" --b "$L/liveroot-twin" --relation stg_budget_lines --relation fct_budget_lines --relation fct_decade_series --relation fct_book_diff --relation p1_era_code_decisions --relation p1_era_line_map --relation fct_program_decade_series --relation fct_budget_trajectory --parquet jbooks/budget_lines.parquet --work "$L/parity-smoke" > "$L/parity-smoke.txt" 2>&1; echo "exit=$?"; cat "$L/parity-smoke.txt"; rm -rf "${L:?}/parity-smoke" "${L:?}/liveroot-twin"
```
Expected: `exit=0`, nine lines ending `— equal`, with the row counts measured above (159,903 / 159,903 / 59,179 / 18,412 / 1,253 / 6,927 / 57,886 / 1,988 / 159,903, unless an earlier task of this wave legitimately moved one — none of Tasks 1–20 writes the live lake), and `lake-parity: EQUAL`. Keep `parity-smoke.txt`: Task 22b compares the post-write counts with it.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/scripts/fu/snapshot_pins.py GovBudget/scripts/fu/lake_parity.py GovBudget/tests/test_fu_snapshot_pins.py GovBudget/tests/test_fu_lake_parity.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(fu): release-1 proof tools — snapshot and Postgres pins, lake parity (design §7, §4.4, §8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `4 files changed`.
