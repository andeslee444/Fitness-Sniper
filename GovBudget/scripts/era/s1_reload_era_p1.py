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
