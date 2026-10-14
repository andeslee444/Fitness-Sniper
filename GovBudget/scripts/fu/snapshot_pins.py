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
