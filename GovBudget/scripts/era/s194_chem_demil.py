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
