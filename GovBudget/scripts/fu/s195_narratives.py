#!/usr/bin/env python3
"""#195: point each narrative provenance row at the volume that prints it.

Families piece-1 follow-ups, design §5.6 (Design A), Q19 (A), Q26; Task 23c.
The relocation itself is govbudget.jbooks.provenance_pages
.plan_narrative_relocations (every edition's narrative rows); this script is
the transactional write around it: the release-2 shared write (Task 26) and
its rehearsal on a proof snapshot (Task 25).

  --digest     Read only, seconds: prints the state digest (below).
  --check      Read only. Plans the relocation; prints its counts, every volume
               a changed row will cite, and the state digest. --plan-json FILE
               also writes the plan (and the digest) as JSON. Works before
               migration 022 (printed_document_sha256 then reads as null).
  --apply      One transaction holding an EXCLUSIVE lock on provenance_pages:
               refuses unless migration 022 is applied and --pre-image does
               not exist yet; refuses when the state digest differs from
               --expect-pre-digest; plans; writes --pre-image (every column of
               every narrative provenance row) and fsyncs it BEFORE any
               update; updates the planned rows (the relocation columns and
               built_at, nothing else); re-reads and requires every planned
               row to equal its plan and every other row to equal the pre-image
               in every column; prints the post-write digest. Any failure rolls
               back (exit 1); --dry-run rolls back after the checks (exit 0).
               A pre-image written before a rollback (a failed post-write
               check, --dry-run) stays on disk: it is the state the rollback
               kept, so a later --apply needs a new path.
  --revert     One transaction holding the same lock: restores, from
               --pre-image, every row whose relocation columns or built_at
               differ; requires every row to equal the pre-image in every
               column and the digest to equal the pre-image's; exit 1 and roll
               back otherwise. Idempotent.

The state digest is md5 over every narrative provenance row (every column but
built_at), every jbook_documents row (every column but file_path and
downloaded_at: a proof snapshot's scratch copy repoints file_path) and every
detail_narratives row (its body as md5). Equal digests on the live database and
on a proof snapshot's scratch copy mean the relocation writes the same rows.

Every mode's first line, once connected, names the database it reads or
writes, on stderr (so stdout's `state digest:` line stays the one a caller
cuts): `s195 --<mode>: database '<current_database()>' on host <host>:<port>`.

Exit 2, before any write: a usage error (--dry-run or --expect-pre-digest
without --apply, --plan-json without --check, an --expect-pre-digest that is
not a 32-hex md5 - an empty one is refused, never ignored); an empty --dsn (or
GOVBUDGET_PG_DSN), refused before any connection; a --pre-image for --revert
that is missing or is not a well-formed schema-1 pre-image (`s195: ...`, no
traceback); a provenance_pages whose columns (information_schema, this
schema) are not PAGE_COLUMNS in table order, checked under the lock by
--apply and --revert before anything is written.

Usage (from GovBudget/):
  uv run --project . python scripts/fu/s195_narratives.py --digest
  uv run --project . python scripts/fu/s195_narratives.py --check [--plan-json FILE]
  uv run --project . python scripts/fu/s195_narratives.py --apply --pre-image FILE [--expect-pre-digest HEX] [--dry-run]
  uv run --project . python scripts/fu/s195_narratives.py --revert --pre-image FILE
DSN: --dsn when given (an empty one is refused, never replaced), else
GOVBUDGET_PG_DSN (config.PG_DSN).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from decimal import Decimal
from pathlib import Path

import psycopg

from govbudget import config
from govbudget.jbooks.provenance_pages import (
    RELOCATION_COLUMNS,
    plan_narrative_relocations,
    same_location,
)

PRE_IMAGE_SCHEMA = 1
PRE_IMAGE_FIELDS = ("schema", "pre_digest", "taken_at", "columns", "rows")
# Every provenance_pages column, in table order (migrations 003, 004 and 022):
# the pre-image is taken in these columns and --revert writes them back.
PAGE_COLUMNS = (
    "id", "document_sha256", "pe_bli", "project_number", "scenario",
    "amount_millions", "amount_text", "page_number", "x0", "x1", "top_pt",
    "bottom_pt", "page_width", "page_height", "resolution", "candidate_pages",
    "built_at", "target_kind", "narrative_kind", "xml_path",
    "printed_document_sha256",
)
_DIGEST_RE = re.compile(r"[0-9a-f]{32}")


class Precondition(ValueError):
    """A state the script will not work from (exit 2, `s195: <reason>`)."""


def announce(con, mode: str) -> str:
    """Print a mode's first line (stderr): the database the connection
    reached and where. Returns current_database()."""
    db = con.execute("select current_database()").fetchone()[0]
    print(f"s195 {mode}: database {db!r} on host {con.info.host}:{con.info.port}",
          file=sys.stderr)
    return db


def has_printed_column(con) -> bool:
    return con.execute(
        "select 1 from information_schema.columns where table_schema = current_schema()"
        " and table_name = 'provenance_pages' and column_name = 'printed_document_sha256'"
    ).fetchone() is not None


def state_digest(con) -> str:
    printed = "coalesce(p.printed_document_sha256, '~')" if has_printed_column(con) else "'~'"
    return con.execute(f"""
        select md5(coalesce(string_agg(t, E'\\n' order by t), '')) from (
          select 'p|' || concat_ws('|', p.id, p.document_sha256, p.pe_bli,
                 coalesce(p.project_number, '~'), p.narrative_kind, p.xml_path,
                 p.amount_text, coalesce(p.page_number::text, '~'),
                 coalesce(p.x0::text, '~'), coalesce(p.x1::text, '~'),
                 coalesce(p.top_pt::text, '~'), coalesce(p.bottom_pt::text, '~'),
                 coalesce(p.page_width::text, '~'), coalesce(p.page_height::text, '~'),
                 p.resolution, p.candidate_pages, {printed}) as t
            from provenance_pages p where p.target_kind = 'narrative'
          union all
          select 'd|' || concat_ws('|', id, org, exhibit_family, fiscal_year, title,
                 source_url, coalesce(sha256, '~'), coalesce(bytes::text, '~'), status)
            from jbook_documents
          union all
          select 'n|' || concat_ws('|', id, document_id, pe_bli,
                 coalesce(project_number, '~'), kind, coalesce(xml_path, '~'),
                 md5(body), superseded)
            from detail_narratives
        ) s
    """).fetchone()[0]


def _columns(con) -> list[str]:
    return [r[0] for r in con.execute(
        "select column_name from information_schema.columns"
        " where table_schema = current_schema() and table_name = 'provenance_pages'"
        " order by ordinal_position").fetchall()]


def check_columns(con) -> list[str]:
    """provenance_pages must have exactly PAGE_COLUMNS, in table order: the
    pre-image is taken and restored in those columns."""
    columns = _columns(con)
    if columns != list(PAGE_COLUMNS):
        raise Precondition(f"provenance_pages columns {columns} are not PAGE_COLUMNS"
                           f" {list(PAGE_COLUMNS)}; nothing written")
    return columns


def _narrative_rows(con, columns: list[str]) -> dict[int, dict]:
    cols = ", ".join(columns)
    return {r[0]: dict(zip(columns, r)) for r in con.execute(
        f"select {cols} from provenance_pages where target_kind = 'narrative' order by id"
    ).fetchall()}


def _to_json(value):
    if isinstance(value, Decimal):
        return {"numeric": str(value)}
    if isinstance(value, datetime.datetime):
        return {"timestamptz": value.isoformat()}
    return value


def _from_json(value):
    if isinstance(value, dict) and "numeric" in value:
        return Decimal(value["numeric"])
    if isinstance(value, dict) and "timestamptz" in value:
        ts = datetime.datetime.fromisoformat(value["timestamptz"])
        if ts.tzinfo is None:
            raise ValueError(f"timestamptz {value['timestamptz']!r} has no offset")
        return ts
    return value


def write_pre_image(path: Path, *, pre_digest: str, columns: list[str],
                    rows: dict[int, dict]) -> None:
    """Write the pre-image atomically and durably: a temp file, flushed and
    fsynced, renamed over `path`, then the directory fsynced so the rename
    survives a crash. On any failure neither the temp file nor a half-made
    `path` is left behind (--apply refused an existing `path`)."""
    doc = {"schema": PRE_IMAGE_SCHEMA, "pre_digest": pre_digest,
           "taken_at": datetime.datetime.now(datetime.UTC).isoformat(),
           "columns": columns,
           "rows": [[_to_json(r[c]) for c in columns] for _, r in sorted(rows.items())]}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    replaced = False
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        replaced = True
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        for leftover in (tmp, path) if replaced else (tmp,):
            try:
                leftover.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_value(v) -> bool:
    """A pre-image cell: a JSON scalar, or a tagged numeric / timestamptz."""
    if isinstance(v, dict):
        return len(v) == 1 and next(iter(v)) in ("numeric", "timestamptz") and isinstance(
            next(iter(v.values())), str)
    return v is None or isinstance(v, (str, int, float))


def malformed(doc) -> str | None:
    """Why `doc` is not a well-formed schema-PRE_IMAGE_SCHEMA pre-image, or
    None. --revert asks this before it connects, so a truncated or hand-made
    file is a usage error (exit 2), never a traceback or a partial restore."""
    if not isinstance(doc, dict):
        return f"a JSON {type(doc).__name__}, not an object"
    missing = [f for f in PRE_IMAGE_FIELDS if f not in doc]
    if missing:
        return f"no {', '.join(missing)}"
    if doc["schema"] != PRE_IMAGE_SCHEMA:
        return f"schema {doc['schema']!r}"
    if not (isinstance(doc["pre_digest"], str) and _DIGEST_RE.fullmatch(doc["pre_digest"])):
        return "`pre_digest` is not a 32-hex md5"
    if not isinstance(doc["taken_at"], str):
        return "`taken_at` is not a string"
    cols = doc["columns"]
    if not (isinstance(cols, list) and all(isinstance(c, str) for c in cols)
            and len(set(cols)) == len(cols) and cols[:1] == ["id"]
            and {*RELOCATION_COLUMNS, "built_at"} <= set(cols)):
        return "`columns` is not a provenance_pages column list"
    rows = doc["rows"]
    if not isinstance(rows, list) or not all(
            isinstance(r, list) and len(r) == len(cols) and _is_int(r[0])
            and all(_is_value(v) for v in r) for r in rows):
        return f"`rows` is not a list of {len(cols)}-column rows keyed by an integer id"
    if len({r[0] for r in rows}) != len(rows):
        return "`rows` repeats an id"
    return None


def read_pre_image(path: Path) -> dict:
    """The pre-image at `path`, its rows as {id: {column: value}}. Raises
    Precondition (exit 2) for a missing, unreadable or malformed file."""
    path = Path(path)
    if not path.is_file():
        raise Precondition(f"{path} does not exist; nothing written")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise Precondition(f"{path} could not be read ({exc}); nothing written") from None
    except ValueError as exc:               # not UTF-8, or not JSON (a truncated file)
        doc, why = None, f"not JSON: {exc}"
    else:
        why = malformed(doc)
    if why is None:
        cols = doc["columns"]
        try:
            doc["rows"] = {r[0]: dict(zip(cols, (_from_json(v) for v in r)))
                           for r in doc["rows"]}
        except (ArithmeticError, ValueError) as exc:
            why = f"a value does not convert: {exc}"
    if why:
        raise Precondition(f"{path} is not a schema-{PRE_IMAGE_SCHEMA} s195 pre-image"
                           f" ({why}); nothing written")
    return doc


def _update(con, pid: int, values: dict) -> None:
    cols = list(values)
    con.execute(f"update provenance_pages set {', '.join(f'{c} = %s' for c in cols)}"
                " where id = %s", [values[c] for c in cols] + [pid])


def _print_plan(plan: dict) -> None:
    c = plan["counts"]
    print(f"rows {c['rows']}: kept {c['kept']}, located {c['located']}, relocated"
          f" {c['relocated']}, opening_only {c['opening_only']}, unresolved {c['unresolved']}")
    for sha, v in sorted(plan["printed_volumes"].items(), key=lambda kv: kv[1]["title"]):
        print(f"  cites {v['status']:10} {sha} {v['rows']:5} row(s)  {v['title']}")


def check(dsn: str, *, plan_json: Path | None) -> int:
    with psycopg.connect(dsn) as con:
        con.execute("set transaction read only")
        announce(con, "--check")
        printed_column = has_printed_column(con)
        if not printed_column:
            print("s195: migration 022 not applied; printed_document_sha256 reads as null")
        digest = state_digest(con)
        plan = plan_narrative_relocations(con, printed_column=printed_column)
    _print_plan(plan)
    print(f"state digest: {digest}")
    if plan_json is not None:
        plan_json.write_text(json.dumps({**plan, "state_digest": digest},
                                        default=str, indent=1) + "\n")
        print(f"plan: {plan_json}")
    return 0


def apply(dsn: str, *, pre_image: Path, expect_pre_digest: str | None,
          dry_run: bool) -> int:
    if pre_image.exists():
        print(f"s195: {pre_image} already exists; refusing to overwrite a pre-image",
              file=sys.stderr)
        return 1
    with psycopg.connect(dsn) as con:
        announce(con, "--apply --dry-run" if dry_run else "--apply")
        con.execute("lock table provenance_pages in exclusive mode")
        if not has_printed_column(con):
            con.rollback()
            print("s195: migration 022 is not applied"
                  " (provenance_pages.printed_document_sha256 is missing)", file=sys.stderr)
            return 1
        columns = check_columns(con)
        pre = state_digest(con)
        print(f"pre-write digest: {pre}")
        if expect_pre_digest is not None and pre != expect_pre_digest:
            con.rollback()
            print(f"s195: pre-write digest {pre} != expected {expect_pre_digest};"
                  " nothing written", file=sys.stderr)
            return 1
        before = _narrative_rows(con, columns)
        plan = plan_narrative_relocations(con)
        _print_plan(plan)
        try:
            write_pre_image(pre_image, pre_digest=pre, columns=columns, rows=before)
        except OSError as exc:
            con.rollback()
            print(f"s195: could not write {pre_image} ({exc}); rolled back, nothing written",
                  file=sys.stderr)
            return 1
        print(f"pre-image: {pre_image} ({len(before)} rows)")
        planned = {ch["id"]: ch["after"] for ch in plan["changes"]}
        now = datetime.datetime.now(datetime.UTC)
        for pid, after in planned.items():
            _update(con, pid, {**after, "built_at": now})
        after_rows = _narrative_rows(con, columns)
        problems = []
        if set(after_rows) != set(before):
            problems.append("the narrative row ids changed")
        for pid, row in after_rows.items():
            if pid not in before:
                continue
            if pid in planned:
                if not same_location(row, planned[pid]):
                    problems.append(f"row {pid}: not the planned location")
                bad = [c for c in columns if c not in RELOCATION_COLUMNS
                       and c != "built_at" and row[c] != before[pid][c]]
            else:
                bad = [c for c in columns if row[c] != before[pid][c]]
            if bad:
                problems.append(f"row {pid}: {bad} changed")
        if problems:
            print("s195: post-write check failed; rolling back", file=sys.stderr)
            for problem in problems[:20]:
                print(f"  {problem}", file=sys.stderr)
            con.rollback()
            return 1
        post = state_digest(con)
        print(f"updated {len(planned)} row(s); post-write digest: {post}")
        if dry_run:
            con.rollback()
            print("dry run: rolled back")
            return 0
        con.commit()
    print("committed")
    return 0


def revert(dsn: str, *, pre_image: Path) -> int:
    doc = read_pre_image(pre_image)
    saved = doc["rows"]
    restore_cols = [*RELOCATION_COLUMNS, "built_at"]
    with psycopg.connect(dsn) as con:
        announce(con, "--revert")
        con.execute("lock table provenance_pages in exclusive mode")
        columns = check_columns(con)
        if columns != doc["columns"]:
            con.rollback()
            print(f"s195: provenance_pages columns {columns} != pre-image {doc['columns']}",
                  file=sys.stderr)
            return 1
        current = _narrative_rows(con, columns)
        if set(current) != set(saved):
            con.rollback()
            print("s195: the narrative row ids differ from the pre-image", file=sys.stderr)
            return 1
        restored = 0
        for pid, row in sorted(saved.items()):
            if any(current[pid][c] != row[c] for c in restore_cols):
                _update(con, pid, {c: row[c] for c in restore_cols})
                restored += 1
        now_rows = _narrative_rows(con, columns)
        bad = [pid for pid, row in now_rows.items()
               if any(row[c] != saved[pid][c] for c in columns)]
        digest = state_digest(con)
        if bad or digest != doc["pre_digest"]:
            print(f"s195: revert check failed ({len(bad)} row(s) differ; digest {digest},"
                  f" pre-image {doc['pre_digest']}); rolling back", file=sys.stderr)
            con.rollback()
            return 1
        con.commit()
    print(f"reverted {restored} row(s); digest {digest} equals the pre-image's")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--digest", action="store_true", help="read-only state digest")
    mode.add_argument("--check", action="store_true", help="read-only plan")
    mode.add_argument("--apply", action="store_true", help="transactional relocation")
    mode.add_argument("--revert", action="store_true", help="restore the pre-image")
    ap.add_argument("--pre-image", type=Path, default=None, dest="pre_image")
    ap.add_argument("--expect-pre-digest", default=None, dest="expect_pre_digest")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run")
    ap.add_argument("--plan-json", type=Path, default=None, dest="plan_json")
    ap.add_argument("--dsn", default=None,
                    help="default: GOVBUDGET_PG_DSN; an empty --dsn is refused, never replaced")
    args = ap.parse_args(argv)
    if (args.apply or args.revert) and args.pre_image is None:
        ap.error("--apply and --revert need --pre-image FILE")
    if not args.apply and (args.dry_run or args.expect_pre_digest is not None):
        ap.error("--dry-run and --expect-pre-digest go with --apply")
    if not args.check and args.plan_json is not None:
        ap.error("--plan-json goes with --check")
    if args.expect_pre_digest is not None and not _DIGEST_RE.fullmatch(args.expect_pre_digest):
        ap.error(f"--expect-pre-digest {args.expect_pre_digest!r} is not a 32-hex md5"
                 " (an empty one is refused, never ignored)")
    # An empty --dsn (an unset "$DSN") must not fall back to GOVBUDGET_PG_DSN,
    # the live database once scripts/era/env.sh is sourced.
    dsn = config.PG_DSN if args.dsn is None else args.dsn
    if not dsn.strip():
        ap.print_usage(sys.stderr)
        print("s195: --dsn is empty; nothing connected" if args.dsn is not None
              else "s195: GOVBUDGET_PG_DSN is empty; nothing connected", file=sys.stderr)
        return 2
    try:
        if args.digest:
            with psycopg.connect(dsn) as con:
                con.execute("set transaction read only")
                announce(con, "--digest")
                print(f"state digest: {state_digest(con)}")
            return 0
        if args.check:
            return check(dsn, plan_json=args.plan_json)
        if args.apply:
            return apply(dsn, pre_image=args.pre_image,
                         expect_pre_digest=args.expect_pre_digest, dry_run=args.dry_run)
        return revert(dsn, pre_image=args.pre_image)
    except Precondition as exc:
        print(f"s195: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
