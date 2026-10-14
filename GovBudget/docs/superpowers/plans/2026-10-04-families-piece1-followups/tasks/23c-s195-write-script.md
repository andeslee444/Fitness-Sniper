<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the README's Contract Notes, section G6, hold this group's contract notes. -->

### Task 23c: #195 — the write script `s195_narratives.py` (`--digest` / `--check` / `--apply` / `--dry-run` / `--revert`) and the read-only measurement

**Spec:** §5.6 (Design A; "Measure before committing" for the heaviest program page), §2.3 Q24 (b) applied to release 2 (the live write gets a `--revert` that restores the exact pre-write rows, with its own test and rehearsal; Task 25 rehearses it, Task 26's abort path uses it), §8 (release 2). Modelled on Task 7's `scripts/era/s194_chem_demil.py` (pre-image file, `--revert --pre-image FILE`) and piece 1's `scripts/era/s1_reload_era_p1.py` (one transaction under a table lock, re-read and verify, roll back on any difference). Depends on Task 23b.
**Files:**
- Create: `scripts/fu/s195_narratives.py`
- Create: `tests/jbooks/test_s195_narratives.py`

**Interfaces:**
Consumes: Task 23a's `provenance_pages.{plan_narrative_relocations, RELOCATION_COLUMNS, same_location}` and migration 022; `tests/jbooks/narrative_volumes.py`; `config.PG_DSN`; `scripts/` on `sys.path` in tests (`tests/conftest.py:23`), as `from era.fact_stability import …` already uses it.
Produces: `scripts/fu/s195_narratives.py` — `has_printed_column(con) -> bool`, `state_digest(con) -> str` (32-hex md5), `write_pre_image(path, *, pre_digest, columns, rows)`, `read_pre_image(path) -> dict`, `check(dsn, *, plan_json) -> int`, `apply(dsn, *, pre_image, expect_pre_digest, dry_run) -> int`, `revert(dsn, *, pre_image) -> int`, `main(argv=None) -> int`; CLI `--digest`, `--check [--plan-json FILE]`, `--apply --pre-image FILE [--expect-pre-digest HEX] [--dry-run]`, `--revert --pre-image FILE`, `[--dsn DSN]` (exit 2 on a usage error); output lines `state digest: <hex>` (digest), `rows <n>: kept <k>, located <l>, relocated <r>, opening_only <o>, unresolved <u>`, one `  cites <status> <sha256> <rows> row(s)  <title>` line per volume a changed row will cite, `state digest: <hex>` and `plan: <path>` (check), `pre-write digest: <hex>`, `pre-image: <path> (<n> rows)`, `updated <n> row(s); post-write digest: <hex>`, `committed` / `dry run: rolled back` (apply), `reverted <n> row(s); digest <hex> equals the pre-image's` (revert); pre-image JSON `{"schema": 1, "pre_digest", "taken_at", "columns", "rows"}` (numerics as `{"numeric": "<text>"}`, timestamps as `{"timestamptz": "<iso>"}`). Tasks 25 and 26 run it; Task 26's abort path runs `--revert`.

**Measured now:** see Step 6 (the read-only plan of the live database, 2026-10-13) and Step 7 (the page-weight estimate).

- [ ] **Step 1: Write the failing tests**

Create `tests/jbooks/test_s195_narratives.py`:

```python
"""scripts/fu/s195_narratives.py — the #195 write, its pre-image and its
revert (families piece-1 follow-ups, Task 23c), on the synthetic book set."""
import json

import psycopg
import pytest

from fu.s195_narratives import main, state_digest  # scripts/ is on sys.path via conftest
from jbooks.narrative_volumes import seed_book_set, seed_pre_195_rows

STATE = ("select id, pe_bli, page_number, x0, resolution, candidate_pages,"
         " printed_document_sha256, built_at from provenance_pages order by id")


def _state(dsn):
    with psycopg.connect(dsn) as con:
        return con.execute(STATE).fetchall()


def _digest(dsn):
    with psycopg.connect(dsn) as con:
        return state_digest(con)


@pytest.fixture()
def book(pg_dsn, tmp_path):
    seeded = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, seeded)
    return seeded


def test_check_reads_only_and_reports_the_plan(pg_dsn, book, tmp_path, capsys):
    before, digest = _state(pg_dsn), _digest(pg_dsn)
    plan_json = tmp_path / "plan.json"
    assert main(["--check", "--plan-json", str(plan_json), "--dsn", pg_dsn]) == 0
    out = capsys.readouterr().out
    assert "rows 6: kept 1, located 1, relocated 1, opening_only 1, unresolved 2" in out
    assert f"cites superseded {book['sha']['BA2']}     1 row(s)  Book BA2" in out
    assert f"state digest: {digest}" in out
    plan = json.loads(plan_json.read_text())
    assert plan["state_digest"] == digest and len(plan["changes"]) == 2
    assert _state(pg_dsn) == before


def test_apply_writes_the_pre_image_then_moves_only_the_planned_rows(pg_dsn, book, tmp_path, capsys):
    pre, before = _digest(pg_dsn), _state(pg_dsn)
    image = tmp_path / "pre.json"
    assert main(["--apply", "--pre-image", str(image), "--expect-pre-digest", pre,
                 "--dsn", pg_dsn]) == 0
    out = capsys.readouterr().out
    doc = json.loads(image.read_text())
    assert doc["pre_digest"] == pre and len(doc["rows"]) == 6
    after = {r[1]: r for r in _state(pg_dsn)}
    assert (after["0605001TST"][2], after["0605001TST"][6]) == (2, book["sha"]["BA2"])
    assert (after["0605002TST"][2], after["0605002TST"][6]) == (1, book["sha"]["BA3"])
    assert sum(1 for r in before if after[r[1]] != r) == 2
    post = _digest(pg_dsn)
    assert post != pre and f"post-write digest: {post}" in out and "committed" in out


def test_apply_refuses_another_pre_state_and_writes_nothing(pg_dsn, book, tmp_path, capsys):
    before, image = _state(pg_dsn), tmp_path / "pre.json"
    assert main(["--apply", "--pre-image", str(image), "--expect-pre-digest", "0" * 32,
                 "--dsn", pg_dsn]) == 1
    assert "nothing written" in capsys.readouterr().err
    assert not image.exists() and _state(pg_dsn) == before


def test_apply_never_overwrites_a_pre_image(pg_dsn, book, tmp_path):
    before, image = _state(pg_dsn), tmp_path / "pre.json"
    image.write_text("{}")
    assert main(["--apply", "--pre-image", str(image), "--dsn", pg_dsn]) == 1
    assert image.read_text() == "{}" and _state(pg_dsn) == before


def test_dry_run_checks_then_rolls_back(pg_dsn, book, tmp_path, capsys):
    before = _state(pg_dsn)
    assert main(["--apply", "--dry-run", "--pre-image", str(tmp_path / "pre.json"),
                 "--dsn", pg_dsn]) == 0
    assert "dry run: rolled back" in capsys.readouterr().out
    assert _state(pg_dsn) == before


def test_revert_restores_every_row_and_the_pre_digest(pg_dsn, book, tmp_path, capsys):
    pre, before, image = _digest(pg_dsn), _state(pg_dsn), tmp_path / "pre.json"
    assert main(["--apply", "--pre-image", str(image), "--dsn", pg_dsn]) == 0
    assert _state(pg_dsn) != before
    assert main(["--revert", "--pre-image", str(image), "--dsn", pg_dsn]) == 0
    assert "reverted 2 row(s)" in capsys.readouterr().out
    assert _state(pg_dsn) == before and _digest(pg_dsn) == pre
    assert main(["--revert", "--pre-image", str(image), "--dsn", pg_dsn]) == 0
    assert "reverted 0 row(s)" in capsys.readouterr().out


def test_the_digest_ignores_file_paths_and_build_times(pg_dsn, book):
    digest = _digest(pg_dsn)
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("update jbook_documents set file_path = '/elsewhere/' || id || '.pdf'")
        con.execute("update provenance_pages set built_at = now() - interval '1 day'")
    assert _digest(pg_dsn) == digest
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("update provenance_pages set candidate_pages = candidate_pages + 1"
                    " where pe_bli = '0605004TST'")
    assert _digest(pg_dsn) != digest


def test_digest_mode_prints_the_state_digest(pg_dsn, book, capsys):
    assert main(["--digest", "--dsn", pg_dsn]) == 0
    assert capsys.readouterr().out == f"state digest: {_digest(pg_dsn)}\n"


def test_usage_errors_exit_2(pg_dsn):
    with pytest.raises(SystemExit) as exc:
        main(["--apply", "--dsn", pg_dsn])
    assert exc.value.code == 2
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_s195_narratives.py -q 2>&1 | tail -3`
Expected: one collection error, `ModuleNotFoundError: No module named 'fu.s195_narratives'` (Task 21 created `scripts/fu/`; on a tree without it the message names `'fu'`).

- [ ] **Step 3: Write the script**

Create `scripts/fu/s195_narratives.py`:

```python
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

Usage (from GovBudget/):
  uv run --project . python scripts/fu/s195_narratives.py --digest
  uv run --project . python scripts/fu/s195_narratives.py --check [--plan-json FILE]
  uv run --project . python scripts/fu/s195_narratives.py --apply --pre-image FILE [--expect-pre-digest HEX] [--dry-run]
  uv run --project . python scripts/fu/s195_narratives.py --revert --pre-image FILE
DSN: --dsn, else GOVBUDGET_PG_DSN (config.PG_DSN). Exit 2 on a usage error.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
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


def has_printed_column(con) -> bool:
    return con.execute(
        "select 1 from information_schema.columns where table_name = 'provenance_pages'"
        " and column_name = 'printed_document_sha256'"
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
        " where table_name = 'provenance_pages' order by ordinal_position").fetchall()]


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
        return datetime.datetime.fromisoformat(value["timestamptz"])
    return value


def write_pre_image(path: Path, *, pre_digest: str, columns: list[str],
                    rows: dict[int, dict]) -> None:
    """Write the pre-image atomically and durably (temp file, fsync, rename)."""
    doc = {"schema": PRE_IMAGE_SCHEMA, "pre_digest": pre_digest,
           "taken_at": datetime.datetime.now(datetime.UTC).isoformat(),
           "columns": columns,
           "rows": [[_to_json(r[c]) for c in columns] for _, r in sorted(rows.items())]}
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def read_pre_image(path: Path) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema") != PRE_IMAGE_SCHEMA:
        raise ValueError(f"{path}: pre-image schema {doc.get('schema')!r},"
                         f" expected {PRE_IMAGE_SCHEMA}")
    cols = doc["columns"]
    doc["rows"] = {r[0]: dict(zip(cols, (_from_json(v) for v in r))) for r in doc["rows"]}
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
        con.execute("lock table provenance_pages in exclusive mode")
        if not has_printed_column(con):
            print("s195: migration 022 is not applied"
                  " (provenance_pages.printed_document_sha256 is missing)", file=sys.stderr)
            return 1
        pre = state_digest(con)
        print(f"pre-write digest: {pre}")
        if expect_pre_digest and pre != expect_pre_digest:
            print(f"s195: pre-write digest {pre} != expected {expect_pre_digest};"
                  " nothing written", file=sys.stderr)
            return 1
        columns = _columns(con)
        before = _narrative_rows(con, columns)
        plan = plan_narrative_relocations(con)
        _print_plan(plan)
        write_pre_image(pre_image, pre_digest=pre, columns=columns, rows=before)
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
        con.execute("lock table provenance_pages in exclusive mode")
        columns = _columns(con)
        if columns != doc["columns"]:
            print(f"s195: provenance_pages columns {columns} != pre-image {doc['columns']}",
                  file=sys.stderr)
            return 1
        current = _narrative_rows(con, columns)
        if set(current) != set(saved):
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
    ap.add_argument("--dsn", default=None, help="default: GOVBUDGET_PG_DSN")
    args = ap.parse_args(argv)
    dsn = args.dsn or config.PG_DSN
    if (args.apply or args.revert) and args.pre_image is None:
        ap.error("--apply and --revert need --pre-image FILE")
    if args.digest:
        with psycopg.connect(dsn) as con:
            con.execute("set transaction read only")
            print(f"state digest: {state_digest(con)}")
        return 0
    if args.check:
        return check(dsn, plan_json=args.plan_json)
    if args.apply:
        return apply(dsn, pre_image=args.pre_image,
                     expect_pre_digest=args.expect_pre_digest, dry_run=args.dry_run)
    return revert(dsn, pre_image=args.pre_image)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_s195_narratives.py tests/jbooks/test_narrative_book_set.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 scripts/fu/s195_narratives.py tests/jbooks/test_s195_narratives.py
```
Expected: `18 passed` (9 here, 9 in Task 23a's file; checked 2026-10-13 on a scratch copy of the tree with Tasks 23a and 23b applied, against a private Postgres 17 cluster), then `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/scripts/fu/s195_narratives.py GovBudget/tests/jbooks/test_s195_narratives.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(fu): s195_narratives.py — the #195 relocation as one locked transaction with a pre-image, a digest and --revert" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Measure the relocation on the live database (read-only)**

`--check` opens a read-only transaction and reads Postgres and `data/raw_docs` only (no lake parquet, no DuckDB), so the SAM job cannot race it; live Postgres has no migration 022 yet, so the column reads as null. It takes about ten minutes (the text pass on up to 8 processes, then pdfplumber word boxes for every changed row).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
mkdir -p tmp && uv run --project . python scripts/fu/s195_narratives.py --check --plan-json tmp/fu2-check-live.json --dsn postgresql://localhost/govbudget > tmp/fu2-check-live.txt 2>&1; echo "exit=$?"; cat tmp/fu2-check-live.txt; grep -c '^  cites superseded' tmp/fu2-check-live.txt
uv run --project . python - <<'PY'
import json
from govbudget.export_site import fact_id_narrative
plan = json.load(open("tmp/fu2-check-live.json"))
by = {fact_id_narrative(*c["fact_key"]): c for c in plan["changes"]}
for fid in ("136baeef904dd052", "033016199ca94aa7", "e7d5bcfb4a30f458", "906bcdda2a0660d1"):
    c = by.get(fid)
    print(fid, "unchanged" if c is None else (c["kind"], c["before"]["page_number"], c["after"]["page_number"], (c["after"]["printed_document_sha256"] or "attached")[:8]))
PY
```
Expected (measured 2026-10-13 on this code, `set transaction read only`):

```
s195: migration 022 not applied; printed_document_sha256 reads as null
narrative relocation (all editions): {'rows': 11698, 'kept': 5757, 'located': 4158, 'relocated': 228, 'opening_only': 111, 'unresolved': 1444}
rows 11698: kept 5757, located 4158, relocated 228, opening_only 111, unresolved 1444
  cites superseded 5e58beb4acd111178f7c9a91ef56ad1da48a292486b43691c0d69fb9434d1a22    71 row(s)  APN_BA5_Book.pdf
  cites superseded 02bf40bcb41af9dbf721a70e2036f98873fba36ab51309d12c093f576d2c67c6    10 row(s)  APN_BA6-7_Book.pdf
  cites superseded 8ef7d90e37f4efeaf2d01840ead847afe1953b6591ec3c63cac218fa95e93c39    79 row(s)  FY26 Air Force Aircraft Procurement Vol II.pdf
  cites downloaded d8a0989f58379ca30b280db42fdbfae719be403db40826a494b10493c2ae6a20     1 row(s)  FY26 Air Force Other Procurement.pdf
  cites downloaded 360a1a8121eb6af19dbb7761b1f99282ee658890a1498a174433f646a0460289    16 row(s)  FY26 Air Force Research and Development Test and Evaluation Vol I.pdf
  cites superseded ac95a8c7ae07b7285a61b027909ce81764a7664edfb365751b0fa696e3951c6c   383 row(s)  FY26 Air Force Research and Development Test and Evaluation Vol II.pdf
  cites superseded 460f97a4763b110f6fc39c859bbeab877744f2442245041a816d323dc516a920   392 row(s)  FY26 Air Force Research and Development Test and Evaluation Vol III.pdf
  cites superseded 779ba7275e50f911c72eb09c0cf5ad2d82ff08be2e9e039e9dfb847ab50843b1   362 row(s)  FY26 Air Force Research and Development Test and Evaluation Vol IV.pdf
  cites downloaded f9a429fbde274901bac9a87f67f7cf7e88c20dd3142bcdeee2a16989e7662117     1 row(s)  FY26 Space Force Procurement.pdf
  cites downloaded 40f1f67d002529317127e3c1c55c44f84f682e7a65ef5f08aa04b3698e71129c     6 row(s)  FY26 Space Force Research and Development Test and Evaluation.pdf
  cites downloaded 118754f3fec7e2ca0f5a2fa64837ad7b98e595aa59365740b0534f9f6d6af509     2 row(s)  OPN_BA1_Book.pdf
  cites superseded 0c2f35d11bd0f4b292e35e00dbfdd09645751ec34b1b853ce640543c0dd0308b    94 row(s)  OPN_BA2_Book.pdf
  cites superseded 9e45a8b11d7f4da7787e0ed7c0a34b5e879b8eb3d66d138238ec1a7dbe9812cd    21 row(s)  OPN_BA3_Book.pdf
  cites superseded 0ab15e0f4100123d146330dd96a0b25a138cdcd396ea4d3a9fff20f7034a808a    23 row(s)  OPN_BA4_Book.pdf
  cites superseded 689e594c7f1b3ee7f49297977ec98b469e2b3722ff4e57b9aaa6c86033e4010f    44 row(s)  OPN_BA5-8_Book.pdf
  cites superseded 184228d828aab1d64819d05f7cd66f24de5e7e28fbeccacf89db50fa15078195    32 row(s)  Other Procurement - BA1 - Tactical & Support Vehicles.pdf
  cites superseded 5bbb799c7f0d78e05c5890169b206f454d4c559f0377244950aa78e136176727   154 row(s)  Other Procurement - BA2 - Communications & Electronics.pdf
  cites downloaded ad24f80769cf6b8e43e26ce1fcc211e2d418bfac31481670e99e068aefbbac22   178 row(s)  RDTE - Vol 1 - Budget Activity 1.pdf
  cites downloaded 24765a252aac2cf5c610eff7fbab4f7d8cf2495f72ba34f7f6d58db936887e6b   544 row(s)  RDTE - Vol 1 - Budget Activity 2.pdf
  cites superseded fdd78d0414e718f3449fcb2175b668ab0f207f78b241de6c2e4c35c3cb102ce9   878 row(s)  RDTE - Vol 1 - Budget Activity 3.pdf
  cites downloaded e5a5bc266a0211c7735917f5e748e657bc21c30294e81593d153a6644ac2cf3e     4 row(s)  RDTE - Vol 2 - Budget Activity 4A.pdf
  cites superseded 8adb79d442b2abda22e0409e4c6969fb483e0689c0e521b318f4364a43ed8e9d   155 row(s)  RDTE - Vol 2 - Budget Activity 4B.pdf
  cites downloaded 7715f4f4490b3e562e4ce1a37c5740f2da4e77f9fa310b4d8a042855a5c41a4a     1 row(s)  RDTE - Vol 3 - Budget Activity 5A.pdf
  cites superseded f22924a93da07c95f4b6e676b6be8d15e41fbc6463c9120cd7b44fccd5c9b16e   132 row(s)  RDTE - Vol 3 - Budget Activity 5B.pdf
  cites superseded 28fa17decbc3927d0bf0f651e7c3ff1fa44308e76ccef2eb6296626f68a2ff24   169 row(s)  RDTE - Vol 3 - Budget Activity 5C.pdf
  cites superseded 045f4ff5332aeb8767b158cc363283d68548fa9515c1cd525b852bd7890f5e4e   224 row(s)  RDTE - Vol 3 - Budget Activity 5D.pdf
  cites downloaded db242ab71c71efb647b702d25c309d7e3f6c2d8efb8bbdff89d46dae760f9e85     1 row(s)  RDTE - Vol 4 - Budget Activity 6.pdf
  cites superseded 1d202f5878beb86205248896e27ffebd6bdfc5a9305d5e7dfc02bde5cd7c16a9   190 row(s)  RDTE - Vol 4 - Budget Activity 7.pdf
  cites superseded 8e1d3bd8612abd2af93bdd9ac8e401442cacba29aaa106b6955caba423413bbd    11 row(s)  RDTE - Vol 4 - Budget Activity 8.pdf
  cites superseded eee17df0d20f79679ec2db119d757258093e7d67e9549cf5a874f99f02df8797    55 row(s)  RDTE - Vol 4 - Budget Activity 9.pdf
  cites downloaded 4ac2a56535d4540dcb2a04203ed11c0448438b8f16c50660fbf2a742817df816    15 row(s)  RDTEN_BA1-3_Book.pdf
  cites downloaded 4e026530e6d634fb383a081ba8c7c3d56c79c1116859b8db2b645e13fffaeb10     2 row(s)  RDTE_CYBERCOM_PB_2026.pdf
  cites downloaded 1623a79d35fd922ba6c87e8e8cbe12f0e960accdef00395d00efff0dfb35b559     1 row(s)  RDTE_DAs_Vol_3B_of_5_OSD_FY19PB-RDTE_Exhibits_BA4-7.pdf
  cites downloaded 266f6fb8a9ddec05641598f0cdd655681d90e2326a784d193d95b62f8d3d5046     1 row(s)  RDTE_DHRA_PB_2026.pdf
  cites downloaded 546a420feb8c273b650dd0c23d6ea503ef935123d6da3da31760ded40ae154ac     1 row(s)  RDTE_OSD_PB_2026.pdf
  cites downloaded cc4d6c5a3896c1ece2b49446140b7ab4e12c3347424fa8558ebff053ecb4e3ee   132 row(s)  RDTE_Vol1_DARPA_MasterJustificationBook_PB_2026.pdf
  cites downloaded 4aa740b7e97bc2cc93e9cacbfcd6c93b1f9b7ae0ba0765a550db7ab8f56a12f2     1 row(s)  RDTE_Vol2_MDA_RDTE_PB26_Justification_Book.pdf
state digest: 3e61258310ef4ce9a7fae630daf8eb62
plan: tmp/fu2-check-live.json
```
then `20` (every superseded PB2026 volume is cited at least once), then

```
136baeef904dd052 ('located', None, 100, '184228d8')
033016199ca94aa7 ('relocated', 71, 215, '8ef7d90e')
e7d5bcfb4a30f458 unchanged
906bcdda2a0660d1 ('located', None, 185, '1623a79d')
```
— the JLTV sentence of #195 moves to the BA1 "Tactical & Support Vehicles" book (doc 347) page 100, as #195 says; design §5.6's F-15EX example moves to AF Aircraft Procurement Vol II page 215; the F015E0 note receipt (`NOTE_RECEIPTS`, page 71 of `528d1441…`) stays, so `f15_funding_history.json` cannot change; the PB2019 lineage-evidence narrative is located. The 11,698 rows are the 11,679 PB2026 rows plus the 19 other-edition rows of non-superseded narratives; the 19 lineage-evidence citations with **no** row (contract issue G6-3) are not in any plan: Task 25b Step 6 and Task 26a Step 3 build them first with `jbooks narrative-provenance --lineage-evidence`. The digest was `3e61258310ef4ce9a7fae630daf8eb62` on 2026-10-13; release 1 writes none of the three tables it covers (provenance_pages' narrative rows, jbook_documents, detail_narratives), so expect the same value; record what it prints, since Task 25's snapshot must carry it. Any count that differs: the live state moved after 2026-10-13 — read why before Task 25, and carry the measured counts (and, if `opening_only` is not 111, the owner's word on the ceiling, Q26) into Tasks 24 and 25.

- [ ] **Step 7: Estimate the heaviest program page before any write (read-only)**

Spec §5.6: the heaviest program page, `/program/0601102A/`, gains about 13.2 KB raw; measure before writing anything. The estimate substitutes each changed narrative citation record into the built pages' RSC payload (the records sit there as JSON inside a JS string, keys sorted, as `JSON.stringify` writes them) and weighs the pages the way gate 1's `weigh()` does (raw bytes, gzip level 9). It needs a build in `site/out` (release 1's, Task 22); Task 25 measures the real build.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - tmp/fu2-check-live.json /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/citations.json tmp/fu2-weigh-records.json postgresql://localhost/govbudget <<'PY'
"""Weight estimate, part 1: the citation records the relocation gives each
exported narrative (what pass 4h would write), from a --check plan."""
import json, sys
import psycopg
from govbudget.export_site import fact_id_narrative

plan_path, citations_path, out_path, dsn = sys.argv[1:5]
plan = json.load(open(plan_path))
cites = json.load(open(citations_path))
with psycopg.connect(dsn) as con:
    con.execute("set transaction read only")
    docs = {r[0]: (r[1], r[2]) for r in con.execute(
        "select distinct on (sha256) sha256, source_url, downloaded_at from jbook_documents"
        " where sha256 is not null order by sha256, id").fetchall()}
records, skipped = {}, 0
for ch in plan["changes"]:
    fid = fact_id_narrative(*ch["fact_key"])
    if fid not in cites:
        skipped += 1
        continue
    a = ch["after"]
    sha = a["printed_document_sha256"] or ch["fact_key"][0]
    url, dl = docs[sha]
    page = int(a["page_number"])
    rec = dict(cites[fid])
    rec.update(sha256=sha, page_number=page, resolution=a["resolution"],
               x0=float(a["x0"]), x1=float(a["x1"]), top_pt=float(a["top_pt"]),
               bottom_pt=float(a["bottom_pt"]), page_width=float(a["page_width"]),
               page_height=float(a["page_height"]),
               hosted_pdf_url=f"/pdfs/{sha}.pdf#page={page}",
               official_url=f"{url}#page={page}", retrieved_at=dl.isoformat())
    records[fid] = {"old": cites[fid], "new": rec}
json.dump(records, open(out_path, "w"))
print(f"records: {len(records)} exported citations change; {skipped} planned rows are not exported")
PY
cat > tmp/fu2-weigh.mjs <<'JS'
// Weight estimate, part 2: substitute each changed narrative citation record
// in every built program page's RSC payload and weigh the result the way
// gate 1's weigh() does (raw bytes; gzip level 9).
import fs from "fs";
import zlib from "zlib";
const [recordsPath, outDir] = process.argv.slice(2);
const records = JSON.parse(fs.readFileSync(recordsPath, "utf8"));
// Next's RSC payload writes &, < and > as \u0026, \u003c and \u003e.
const embed = (rec) => JSON.stringify(JSON.stringify(rec)).slice(1, -1)
  .replace(/&/g, "\\u0026").replace(/</g, "\\u003c").replace(/>/g, "\\u003e");
const fidRe = /\\"([0-9a-f]{16})\\":\{\\"amount_text\\"/g;
const rows = [];
for (const slug of fs.readdirSync(`${outDir}/program`)) {
  const p = `${outDir}/program/${slug}/index.html`;
  if (!fs.existsSync(p)) continue;
  const original = fs.readFileSync(p, "utf8");
  let html = original;
  const gzipBefore = zlib.gzipSync(Buffer.from(original), { level: 9 }).length;
  const fids = new Set([...html.matchAll(fidRe)].map((m) => m[1]).filter((f) => records[f]));
  if (fids.size === 0) continue;
  const before = Buffer.byteLength(html);
  let missing = 0;
  for (const fid of fids) {
    const oldText = embed(records[fid].old);
    // Checked against the page as built: two citations with the same record
    // text (one narrative's sections share pe_bli and xml_path) are both
    // replaced by the first split/join.
    if (!original.includes(oldText)) { missing++; continue; }
    html = html.split(oldText).join(embed(records[fid].new));
  }
  const buf = Buffer.from(html);
  rows.push({ slug, records: fids.size, missing, raw_before: before, raw: buf.length,
              gzip_before: gzipBefore, gzip: zlib.gzipSync(buf, { level: 9 }).length });
}
rows.sort((a, b) => b.raw - a.raw);
for (const r of rows.slice(0, 5)) console.log(JSON.stringify(r));
const heaviestGzip = rows.reduce((m, r) => (r.gzip > m.gzip ? r : m), rows[0]);
console.log("heaviest gzip:", JSON.stringify(heaviestGzip));
console.log(`pages changed: ${rows.length}; records not found verbatim: ${rows.reduce((s, r) => s + r.missing, 0)}`);
JS
node tmp/fu2-weigh.mjs tmp/fu2-weigh-records.json site/out
```
Expected (2026-10-13, on the 916ae88e build in this worktree's `site/out`; release 1's build moves the before-weights a little):

```
{"slug":"0601102A","records":102,"missing":0,"raw_before":1157481,"raw":1171692,"gzip_before":145454,"gzip":147566}
{"slug":"0601153N","records":10,"missing":0,"raw_before":880991,"raw":881062,"gzip_before":102300,"gzip":102357}
{"slug":"0602146A","records":66,"missing":0,"raw_before":871533,"raw":880785,"gzip_before":108827,"gzip":110181}
{"slug":"0603462A","records":114,"missing":0,"raw_before":778890,"raw":794830,"gzip_before":99161,"gzip":101521}
{"slug":"0602145A","records":49,"missing":0,"raw_before":774118,"raw":781006,"gzip_before":100169,"gzip":101219}
heaviest gzip: {"slug":"0601102A","records":102,"missing":0,"raw_before":1157481,"raw":1171692,"gzip_before":145454,"gzip":147566}
pages changed: 725; records not found verbatim: 0
```
On 2026-10-13 that left `/program/0601102A/` at 1,171,692 raw / 147,566 gzip (+14,211 / +2,112; 8,308 raw and 3,434 gzip bytes under the ceilings), and 725 program pages change. The heaviest page after the substitution must sit inside `/program/*/ (heaviest)`'s ceilings, 1,180,000 raw and 151,000 gzip (`site/scripts/gates/build.mjs`, unchanged). If it does not, stop and ask the owner (spec §5.6): never raise a ceiling. Nothing is committed in this step; the numbers go into Task 25's proof note.
