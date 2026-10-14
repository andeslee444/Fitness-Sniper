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
