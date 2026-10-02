<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 3: Proof tooling — pinned snapshots and the masked diff

**Spec:** §8 "Proofs run on pinned snapshots, never on the live lake" (snapshot contents, recorded shas, A/B "diffed with build timestamps masked"); §9 S1/S1b/S4 (the diffs those steps run); §10 (expected differences — `retrieved_at` changes on F-15's era leaves must stay visible, so `retrieved_at` is never masked as a key); §11.1 (shared mutable lake).

**Files:**
- Create: `src/govbudget/proof.py`
- Create: `tests/test_proof.py`
- Modify: `src/govbudget/cli.py` — insert `cmd_proof` between `cmd_refresh` (ends at line 2937) and `def main(argv=None)` (line 2940); insert the `proof` subparser between `rfr.set_defaults(func=cmd_refresh)` (line 3336) and `args = p.parse_args(argv)` (line 3338). Anchor on the text, not the numbers: Tasks 5, 12 and 14 add subparsers at the same place.

**Interfaces:**
Consumes: Task 1 (`scripts/era/env.sh`, the 127.0.0.1:55432 cluster, `.proofs/` ignored). Existing: `govbudget.cli.main`, `govbudget.config.{DATA_DIR, PG_DSN}`.
Produces (contract names first):
- `snapshot(out_dir: Path, *, data_dir: Path, pg_dsn: str, scratch_db: str) -> dict` — the manifest: `{schema_version: 1, created_at, out_dir, source: {data_dir, pg_dsn}, env: {GOVBUDGET_DATA, GOVBUDGET_DUCKDB, GOVBUDGET_PG_DSN}, duckdb: {path, sha256_at_copy, sha256, views, views_rewritten}, parquet: {relpath: {sha256, bytes, rows}}, site: {files, bytes, sha256}, raw_docs: {files, bytes, sha256}, manifest_jsonl_sha256, pg: {source_db, scratch_db, scratch_dsn, dump, dump_sha256, pg_dump_version, tables: {name: {rows, md5}}, rewrites: {"jbook_documents.file_path": n}}}`. Writes `<out>/{duckdb/govbudget.duckdb, parquet/, site/, raw_docs/, manifest.jsonl, pg/<db>.dump, snapshot.json, env.sh}` and creates database `scratch_db` on the source server. Refuses before writing anything at minutes :15–:20, on an existing `out_dir` or database, a bad name, an out_dir inside the lake, a missing lake entry, a `.wal`, or a DuckDB writer; refuses after the copy if the clock entered :15–:20 during it (delete `out_dir` and retry).
- `diff_trees(a: Path, b: Path) -> dict` — `{a, b, build_window: {a: [lo, hi] | None, b: ...}, counts: {identical, equivalent, changed, only_a, only_b}, groups: {group: counts}, files: {relpath: {status, kind: json|parquet|bytes, group, detail}}}`; `files` lists every non-identical file. JSON detail: `{changes: [{pattern, change: added|removed|changed|reordered, count, samples: [{pointer, a, b}]}]}`; parquet detail: `{schema_a, schema_b, rows_a, rows_b, only_a, only_b, sample_only_a, sample_only_b}`; bytes detail: `{sha256_a, sha256_b}`.
- `load_expectations(path) -> list[dict]`, `check_expectations(report, rules) -> {ok, unexpected, unmet, matched}`, `format_report(report, verdict=None) -> list[str]`, `is_equal(report) -> bool`; constants `SNAPSHOT_MANIFEST = "snapshot.json"`, `SNAPSHOT_ENV = "env.sh"`, `BUILD_TS = "<build-timestamp>"`, `BUILD_DATE = "<build-date>"`.
- CLI `govbudget proof snapshot --out DIR --scratch-db NAME [--data-dir DIR] [--pg-dsn DSN]`; `govbudget proof diff A B [--expect FILE] [--report FILE]`. `diff` prints one final line: `proof diff: EQUAL` (exit 0) / `proof diff: DIFFERENT` (exit 1) without `--expect`; `proof diff: PASS` (exit 0) / `proof diff: FAIL` (exit 1) with it.
- `--expect` file: a JSON list of rules `{"path": glob, "why": text, "status": [changed|only_a|only_b]?, "pointer": glob?, "change": [added|removed|changed|reordered]?, "required": bool?}`. Only `*` is a wildcard (it also matches `/`); `[]` and `{fid}` are literal. Every difference must match a rule; every `required` rule must match one. A JSON difference is matched per (`pattern`, `change`): `pattern` is the JSON pointer with 16-hex fact-ID keys collapsed to `{fid}` and list elements written `/[]` (e.g. `/{fid}/retrieved_at`, `/decade_series/[]`).
- Run-dir convention for every proof export (Tasks 8, 9, 21): `cp -c -R <snap> <snap>-<run>`; `source <snap>/env.sh <snap>-<run>`; `uv run --project . python -m govbudget export-site` from the code checkout's `GovBudget/`; `uv run --project . python -m govbudget proof diff <snapA>-<run>/site <snapB>-<run>/site [--expect FILE]`. Scratch database names: `govbudget_proof_<snapshot name>`.

What export-site reads (traced for this task; recorded in the module docstring): `$GOVBUDGET_DATA/duckdb/govbudget.duckdb` (tables + 37 views, 18 of which embed `<DATA_DIR>/parquet/...`), `$GOVBUDGET_DATA/parquet/**` (also via `_stage_parquet_path`/`_lake_parquet_dir` beside the DuckDB file), `$GOVBUDGET_DATA/manifest.jsonl` (`config.MANIFEST_PATH`, `export_site.py:1288`), `$GOVBUDGET_DATA/site` (output; existing `pdfs/`, `workbooks/`, `json/` reused or rewritten), Postgres `config.PG_DSN`, raw documents through `jbook_documents.file_path`; repo-relative: `data/research/` (`edition_manifest.json` `:3736`, `dossiers-raw/`, `snapshots/index.json` via `cli.py:2442-2447`, `usaspending_recipient_ids.json` `:18017`), `data-seeds/*`, `dbt/seeds/state_category_map.csv`, `dbt/target/manifest.json` + `site/scripts/verify.mjs` + `evals/phase5_questions.yaml` (`site_meta.build_checks`, `:1383-1418` — differs between checkouts that have or lack `dbt/target`), and the page cache `ROOT/tmp/pdfs` written by `program_pdf_receipts` (`cli.py:2449-2455`). `program_pdf_receipts.source_file` downloads a PDF only when `site/pdfs/<sha>.pdf` is missing.

Measured for this task (read-only unless stated, 2026-10-02):
- Build stamps in the live export (`manifest.json` `built_at` 2026-10-02T01:30:21.066005+00:00): every `retrieved_at` that is UTC with a fractional second — 38,997 citation rows over 9 distinct instants (8 derived tiers plus the state kinds), each tier's own `now()` (`export_site.py:3375, 5753, 7057, 7793, 7960, 9383, 10073, 14873`) — lies in [01:26:11.150859, 01:30:21.066005]; the F-15 builder reuses `built_at` itself (`f15_funding_history.py:348`). `built_at` appears in `manifest.json`, `json/datasets.json`, `json/site_meta.json`; `link_adjudication.measured_on` = `built_at[:10]` in `manifest.json` and `json/site_meta.json`. Source stamps that must stay visible: workbook/jbook `-04:00` stamps (both `T` and space forms), SAM retrieval stamps `2026-10-02T00:17:58+00:00`…`00:18:12+00:00` on 58 derived rows (second precision, about 70 minutes before the run), `dim_entities.sam_retrieved_at`, dossier `collected_at`, `site_meta.source_freshness.*.newest_downloaded_at`. Query: a JSON walk over all 35,248 JSON files in `data/site` for ISO-timestamp strings, and `select kind, count(distinct retrieved_at), min(retrieved_at), max(retrieved_at) from 'data/site/citations/citations.parquet' group by kind`.
- `diff_trees(live data/site, cp -c clone)`: 35,520 identical files in 15.9 s. On a scratch clone with every `2026-10-02T01:` stamp shifted to `2026-10-05T07:` in the 260 JSON files and `citations.parquet` that carry them: 259 files `equivalent`, 28.9 s; the two `measured_on` values the shift missed were reported `changed` (correctly: the build day had moved).
- DuckDB rewrite on a scratch clone of `govbudget.duckdb` + `parquet/`: 18 views rewritten, 0 left naming `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/`, and `dim_programs` 1,936, `stg_budget_lines` 159,494, `fct_program_lobbying` 12,571, `dim_lobbyists` 1,612, `fct_state_per_capita` 6 rows — equal to the live file.
- Lake: `parquet/` 112 files (109 `.parquet`, plus `sam/manifest.jsonl`, `sam/daily/.lock`, `sam/daily/state.json`), `site/` 35,520 files, `raw_docs/` 1,112 files, no symlinks; `cp -c -R data/site` 4.3 s. Postgres `govbudget`: 18 tables, 1,028 MB (largest `budget_line_awards`, 719 MB); one per-table digest (`provenance_pages`, 75,434 rows) takes 0.52 s.
- `tests/test_proof.py` on the prototype: 15 passed after cycle A; `7 failed, 16 passed` at the start of cycle B; 23 passed at the end; mutation checks (no window widening; masking `retrieved_at` as a key) each fail the masking tests.

- [ ] **Step 1: Write the failing diff tests**

Create `tests/test_proof.py`:

```python
"""govbudget.proof — pinned snapshots and the masked export diff (families piece 1, spec §8).

The diff decides whether an A/B export proof passes, so its masking is pinned
here on tiny trees: build stamps (every `built_at`, a `retrieved_at` that is a
UTC instant inside the tree's own build window, `measured_on` on the build day)
are masked; source stamps — workbook download times, SAM retrieval times — are
evidence and never are. Parquet files compare as row multisets.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import duckdb
import psycopg
import pytest

from govbudget import cli, proof

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get("GOVBUDGET_TEST_PG_DSN", "postgresql://localhost/postgres")

BUILT_A = "2026-10-02T01:30:21.066005+00:00"
DERIVED_A = "2026-10-02T01:26:11.150859+00:00"
WHOLE_SECOND_A = "2026-10-02T01:28:00+00:00"   # a now() that landed on .000000
BUILT_B = "2026-10-03T09:12:44.512300+00:00"
DERIVED_B = "2026-10-03T09:08:02.000417+00:00"
WHOLE_SECOND_B = "2026-10-03T09:10:00.500000+00:00"
WORKBOOK_T = "2026-07-03T07:44:16.038674-04:00"
WORKBOOK_SPACE = "2026-07-03 07:44:15.975561-04:00"
SAM = "2026-10-02T00:17:58+00:00"

FID_DERIVED = "aaaaaaaaaaaaaaaa"
FID_WHOLE = "dddddddddddddddd"
FID_WORKBOOK = "bbbbbbbbbbbbbbbb"
FID_SAM = "cccccccccccccccc"


def _json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _parquet(path: Path, columns: list[tuple[str, str]], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.execute("create table t (" + ", ".join(f"{n} {t}" for n, t in columns) + ")")
        if rows:
            con.executemany(
                "insert into t values (" + ", ".join("?" for _ in columns) + ")", rows
            )
        con.execute(f"copy t to '{path}' (format parquet)")
    finally:
        con.close()


def _site(root: Path, *, built: str, derived: str, whole: str,
          workbook: str = WORKBOOK_T, sam: str = SAM) -> Path:
    """A miniature data/site export: the files that carry stamps."""
    _json(root / "manifest.json", {"built_at": built,
                                   "link_adjudication": {"measured_on": built[:10]}})
    _json(root / "json" / "site_meta.json", {"built_at": built, "counts": {"citations": 4}})
    citations = {
        FID_DERIVED: {"kind": "derived", "retrieved_at": derived, "inputs": [FID_WORKBOOK]},
        FID_WHOLE: {"kind": "derived", "retrieved_at": whole, "inputs": [FID_WORKBOOK]},
        FID_WORKBOOK: {"kind": "workbook", "retrieved_at": workbook, "pe_bli": None},
        FID_SAM: {"kind": "derived", "retrieved_at": sam, "inputs": []},
    }
    _json(root / "json" / "citations.json", citations)
    _parquet(
        root / "citations" / "citations.parquet",
        [("fact_id", "varchar"), ("kind", "varchar"), ("retrieved_at", "varchar")],
        [(fid, c["kind"], c["retrieved_at"]) for fid, c in sorted(citations.items())],
    )
    _json(root / "json" / "sam" / "X.json", {"source": {"retrieved_at": sam}})
    return root


def _pair(tmp_path: Path, **b_overrides) -> tuple[Path, Path]:
    a = _site(tmp_path / "a", built=BUILT_A, derived=DERIVED_A, whole=WHOLE_SECOND_A)
    b_kwargs = {"built": BUILT_B, "derived": DERIVED_B, "whole": WHOLE_SECOND_B, **b_overrides}
    b = _site(tmp_path / "b", **b_kwargs)
    return a, b


def _changes(report: dict, rel: str) -> list[tuple[str, str, int]]:
    return [(c["pattern"], c["change"], c["count"])
            for c in report["files"][rel]["detail"]["changes"]]


# ---------------------------------------------------------------------------
# masking
# ---------------------------------------------------------------------------


def test_a_tree_equals_its_copy(tmp_path):
    a = _site(tmp_path / "a", built=BUILT_A, derived=DERIVED_A, whole=WHOLE_SECOND_A)
    b = tmp_path / "b"
    shutil.copytree(a, b)
    report = proof.diff_trees(a, b)
    assert report["counts"] == {"identical": 5, "equivalent": 0, "changed": 0,
                                "only_a": 0, "only_b": 0}
    assert report["files"] == {}
    assert proof.is_equal(report)


def test_two_builds_of_the_same_data_differ_only_in_masked_build_stamps(tmp_path):
    a, b = _pair(tmp_path)
    report = proof.diff_trees(a, b)
    assert report["build_window"]["a"] == [DERIVED_A, BUILT_A]
    assert report["build_window"]["b"] == [DERIVED_B, BUILT_B]
    assert report["counts"]["changed"] == 0, report["files"]
    assert {rel: e["status"] for rel, e in report["files"].items()} == {
        "manifest.json": "equivalent",
        "json/site_meta.json": "equivalent",
        "json/citations.json": "equivalent",
        "citations/citations.parquet": "equivalent",
    }
    assert proof.is_equal(report)


def test_a_source_retrieval_stamp_change_is_reported_not_masked(tmp_path):
    # Spec §10: F-15's era leaves move from the space form to the T form.
    a = _site(tmp_path / "a", built=BUILT_A, derived=DERIVED_A, whole=WHOLE_SECOND_A,
              workbook=WORKBOOK_SPACE)
    b = _site(tmp_path / "b", built=BUILT_B, derived=DERIVED_B, whole=WHOLE_SECOND_B,
              workbook=WORKBOOK_T)
    report = proof.diff_trees(a, b)
    assert _changes(report, "json/citations.json") == [("/{fid}/retrieved_at", "changed", 1)]
    sample = report["files"]["json/citations.json"]["detail"]["changes"][0]["samples"][0]
    assert sample == {"pointer": f"/{FID_WORKBOOK}/retrieved_at",
                      "a": json.dumps(WORKBOOK_SPACE), "b": json.dumps(WORKBOOK_T)}
    pq = report["files"]["citations/citations.parquet"]
    assert (pq["status"], pq["detail"]["only_a"], pq["detail"]["only_b"]) == ("changed", 1, 1)
    assert not proof.is_equal(report)


def test_a_utc_stamp_outside_the_build_window_is_evidence(tmp_path):
    # SAM's retrieval stamp is UTC and recent, but it predates the run.
    a, b = _pair(tmp_path, sam="2026-10-02T00:18:02+00:00")
    report = proof.diff_trees(a, b)
    assert _changes(report, "json/sam/X.json") == [("/source/retrieved_at", "changed", 1)]
    assert _changes(report, "json/citations.json") == [("/{fid}/retrieved_at", "changed", 1)]


def test_measured_on_is_masked_only_on_the_build_day(tmp_path):
    a, b = _pair(tmp_path)
    _json(a / "json" / "other.json", {"measured_on": "2026-09-01"})
    _json(b / "json" / "other.json", {"measured_on": "2026-09-02"})
    report = proof.diff_trees(a, b)
    assert report["files"]["manifest.json"]["status"] == "equivalent"
    assert _changes(report, "json/other.json") == [("/measured_on", "changed", 1)]


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------


def test_parquet_files_compare_as_row_multisets(tmp_path):
    cols = [("x", "integer"), ("y", "varchar")]
    _parquet(tmp_path / "a" / "data" / "t.parquet", cols, [(1, "x"), (2, "y"), (2, "y")])
    _parquet(tmp_path / "b" / "data" / "t.parquet", cols, [(2, "y"), (1, "x"), (2, "y")])
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["files"]["data/t.parquet"]["status"] == "equivalent"

    _parquet(tmp_path / "b" / "data" / "t.parquet", cols, [(2, "y"), (1, "x")])
    d = proof.diff_trees(tmp_path / "a", tmp_path / "b")["files"]["data/t.parquet"]["detail"]
    assert (d["rows_a"], d["rows_b"], d["only_a"], d["only_b"]) == (3, 2, 1, 0)
    assert d["sample_only_a"] == [{"x": 2, "y": "y"}]

    _parquet(tmp_path / "b" / "data" / "t.parquet", [*cols, ("z", "integer")],
             [(1, "x", 0), (2, "y", 0), (2, "y", 0)])
    d = proof.diff_trees(tmp_path / "a", tmp_path / "b")["files"]["data/t.parquet"]["detail"]
    assert d["schema_b"] == [["x", "INTEGER"], ["y", "VARCHAR"], ["z", "INTEGER"]]
    assert d["only_a"] is None and d["only_b"] is None


def test_json_lists_compare_as_multisets_and_scalars_by_type(tmp_path):
    _json(tmp_path / "a" / "p.json", {"series": [{"fy": 2018}, {"fy": 2019}], "v": 1})
    _json(tmp_path / "b" / "p.json", {"series": [{"fy": 2019}, {"fy": 2018}], "v": 1.0})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert _changes(report, "p.json") == [("/series", "reordered", 1), ("/v", "changed", 1)]

    _json(tmp_path / "b" / "p.json",
          {"series": [{"fy": 2017}, {"fy": 2018}, {"fy": 2019}], "v": 1, "w": True})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert _changes(report, "p.json") == [("/series/[]", "added", 1), ("/w", "added", 1)]


def test_other_files_compare_by_bytes_and_big_directories_group(tmp_path):
    for side in ("a", "b"):
        for i in range(50):
            _json(tmp_path / side / "json" / "program_details" / f"P{i:03d}.json", {"i": i})
    (tmp_path / "a" / "pdfs").mkdir()
    (tmp_path / "b" / "pdfs").mkdir()
    (tmp_path / "a" / "pdfs" / "x.pdf").write_bytes(b"%PDF-1 a")
    (tmp_path / "b" / "pdfs" / "x.pdf").write_bytes(b"%PDF-1 b")
    (tmp_path / "a" / "gone.json").write_text("{}")
    (tmp_path / "b" / "new.json").write_text("{}")
    _json(tmp_path / "b" / "json" / "program_details" / "P007.json", {"i": 7, "era": [1]})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["counts"] == {"identical": 49, "equivalent": 0, "changed": 2,
                                "only_a": 1, "only_b": 1}
    assert report["files"]["pdfs/x.pdf"]["kind"] == "bytes"
    assert report["files"]["gone.json"]["status"] == "only_a"
    assert report["files"]["new.json"]["status"] == "only_b"
    assert report["groups"]["json/program_details/*.json"] == {
        "identical": 49, "equivalent": 0, "changed": 1, "only_a": 0, "only_b": 0}


# ---------------------------------------------------------------------------
# --expect
# ---------------------------------------------------------------------------


def _expect_fixture(tmp_path: Path) -> dict:
    _json(tmp_path / "a" / "json" / "program_details" / "P1.json", {"decade_series": [{"fy": 2022}]})
    _json(tmp_path / "b" / "json" / "program_details" / "P1.json",
          {"decade_series": [{"fy": 2015}, {"fy": 2022}]})
    _parquet(tmp_path / "b" / "data" / "new.parquet", [("x", "integer")], [(1,)])
    return proof.diff_trees(tmp_path / "a", tmp_path / "b")


def test_expectations_cover_every_difference_or_fail(tmp_path):
    report = _expect_fixture(tmp_path)
    rules = [
        {"path": "json/program_details/*.json", "pointer": "/decade_series/[]",
         "change": ["added"], "why": "era decade points (spec §10)"},
        {"path": "data/new.parquet", "status": ["only_b"], "why": "new dataset",
         "required": True},
    ]
    verdict = proof.check_expectations(report, rules)
    assert verdict["ok"], verdict
    assert [m["count"] for m in verdict["matched"]] == [1, 1]

    verdict = proof.check_expectations(report, rules[:1])
    assert not verdict["ok"]
    assert verdict["unexpected"] == [{"path": "data/new.parquet", "status": "only_b",
                                      "pattern": None, "change": None, "count": 1}]

    unmet = [*rules, {"path": "json/era_map_summary.json", "why": "summary", "required": True}]
    verdict = proof.check_expectations(report, unmet)
    assert not verdict["ok"]
    assert verdict["unmet"] == [{"rule": 2, "path": "json/era_map_summary.json", "why": "summary"}]


@pytest.mark.parametrize("rule, message", [
    ({"path": "x"}, "non-empty 'why'"),
    ({"path": "x", "why": "w", "colour": "red"}, "unknown keys"),
    ({"path": "x", "why": "w", "status": ["equivalent"]}, "bad 'status'"),
    ({"path": "x", "why": "w", "change": ["moved"]}, "bad 'change'"),
    ({"why": "w"}, "needs a 'path'"),
])
def test_malformed_rules_are_refused(tmp_path, rule, message):
    path = tmp_path / "expect.json"
    path.write_text(json.dumps([rule]))
    with pytest.raises(ValueError, match=message):
        proof.load_expectations(path)


def test_globs_treat_only_the_star_as_special():
    assert proof._glob("/decade_series/[]", "/decade_series/[]")
    assert not proof._glob("/decade_series/[]", "/decade_series/x")
    assert proof._glob("json/*.json", "json/program_details/P1.json")
    assert proof._glob("/{fid}/*", "/{fid}/retrieved_at")
```

- [ ] **Step 2: Run them — they fail**

```bash
uv run --project . pytest tests/test_proof.py -q
```

Expected: collection error `ImportError: cannot import name 'proof' from 'govbudget'`, `1 error`.

- [ ] **Step 3: Implement the diff half of `src/govbudget/proof.py`**

Create `src/govbudget/proof.py`:

```python
"""Pinned proof snapshots, and a masked, parquet-aware diff of two data/site trees.

Families piece 1 (docs/superpowers/specs/2026-10-02-era-procurement-history-design.md
§8, "Proofs run on pinned snapshots, never on the live lake").

What `govbudget export-site` reads — and so what `snapshot()` pins (traced in
export_site.py, cli.py and config.py on 2026-10-02):

  Under GOVBUDGET_DATA (config.DATA_DIR, config.py:29). Every lake constant is
  built from it — SITE_DIR, DUCKDB_PATH, PARQUET_DIR, RAW_DOCS_DIR, RAW_DIR and
  MANIFEST_PATH (config.py:56-67) — so one variable moves them all.
    duckdb/govbudget.duckdb  config.DUCKDB_PATH. dbt materializes most marts as
                             VIEWS whose SQL embeds the ABSOLUTE
                             read_parquet('<DATA_DIR>/parquet/...') path of the
                             lake it was built against (18 of 37 views on
                             2026-10-02). A byte copy alone would still read the
                             live lake, so snapshot() repoints those views at the
                             copy. config ignores GOVBUDGET_DUCKDB; only dbt
                             (dbt/profiles.yml) and `govbudget build`
                             (cli.py cmd_build) read it.
    parquet/                 config.PARQUET_DIR. The exporter also reads staged
                             parquets BESIDE the DuckDB file
                             (export_site._stage_parquet_path/_lake_parquet_dir:
                             <duckdb dir>/../parquet/<stage>/...).
    manifest.jsonl           config.MANIFEST_PATH (site_meta source freshness).
    site/                    config.SITE_DIR, the output tree. Existing pdfs/ and
                             workbooks/ are kept when their sha256 matches;
                             program_pdf_receipts downloads a PDF only when
                             site/pdfs/<sha>.pdf is missing.
    raw_docs/                NOT read through config.RAW_DOCS_DIR: the document
                             loop (export_site.py, "3. Documents") stats and copies
                             jbook_documents.file_path, an ABSOLUTE path stored in
                             Postgres. snapshot() clones raw_docs and points the
                             scratch database's file_path rows at the clone.
  Postgres: config.PG_DSN (GOVBUDGET_PG_DSN).
  Repo-relative, pinned by the commit being run, not by the snapshot:
    data/research/ (config.RESEARCH_DIR = ROOT/data/research, config.py:63),
    data-seeds/, dbt/seeds/state_category_map.csv, the build_checks inputs
    (dbt/target/manifest.json, site/scripts/verify.mjs,
    evals/phase5_questions.yaml), and the program_pdf_receipts page cache
    ROOT/tmp/pdfs (derived from sha-pinned PDFs; a cold cache costs time only).

Running export-site against a snapshot (each export gets its own clone, so a
second export never starts from the first one's output):

    SNAP=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/<name>
    cp -c -R "$SNAP" "$SNAP-A"           # APFS clone: seconds, no extra space
    source "$SNAP/env.sh" "$SNAP-A"      # GOVBUDGET_DATA/_DUCKDB -> $SNAP-A, PG -> scratch db
    uv run --project . python -m govbudget export-site     # from the code checkout's GovBudget/
    uv run --project . python -m govbudget proof diff "$SNAP/site" "$SNAP-A/site"

The clone's DuckDB views keep reading $SNAP/parquet and its documents resolve to
$SNAP/raw_docs; both are read-only and pinned. Never run a snapshot or an export
between :15 and :20 past the hour (the hourly SAM job writes data/parquet/sam
at :17); snapshot() refuses to.

diff_trees() compares two data/site trees: JSON structurally, parquet as row
multisets, everything else by bytes. It masks build timestamps only — values of
`built_at`/`retrieved_at` that are UTC instants inside the tree's own build
window, and `measured_on` equal to the build day — never `retrieved_at` as a
key, because source retrieval stamps are evidence (spec §10 expects specific
`retrieved_at` changes).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SNAPSHOT_MANIFEST = "snapshot.json"
SNAPSHOT_ENV = "env.sh"
DUCKDB_REL = Path("duckdb") / "govbudget.duckdb"
MANIFEST_REL = "manifest.jsonl"
CLONED_DIRS = ("parquet", "site", "raw_docs")
SAM_WINDOW_MINUTES = range(15, 21)
DEFAULT_PG_BIN = Path("/opt/homebrew/opt/postgresql@17/bin")

BUILD_TS = "<build-timestamp>"
BUILD_DATE = "<build-date>"
STAMP_KEYS = frozenset({"built_at", "retrieved_at"})
DATE_KEYS = frozenset({"measured_on"})
STATUSES = ("identical", "equivalent", "changed", "only_a", "only_b")
CHANGES = ("added", "removed", "changed", "reordered")

_UTC_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00")
_UTC_FRACTION_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{1,6}\+00:00")
_FID_RE = re.compile(r"[0-9a-f]{16}")
_SCRATCH_DB_RE = re.compile(r"[a-z][a-z0-9_]{0,62}")
_WINDOW_LOOKBACK = datetime.timedelta(hours=3)
_WINDOW_LOOKAHEAD = datetime.timedelta(hours=1)
_GROUP_MIN_FILES = 50
_SAMPLES_PER_CHANGE = 3
_SAMPLE_ROWS = 5
_MAX_VALUE_CHARS = 300
_IGNORED_NAMES = frozenset({".DS_Store"})
_RULE_KEYS = frozenset({"path", "why", "status", "pointer", "change", "required"})


def _now() -> datetime.datetime:
    """Local wall clock; tests monkeypatch this."""
    return datetime.datetime.now()


# ---------------------------------------------------------------------------
# shared
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _same_bytes(pa: Path, pb: Path) -> bool:
    if pa.stat().st_size != pb.stat().st_size:
        return False
    with open(pa, "rb") as fa, open(pb, "rb") as fb:
        while True:
            ca, cb = fa.read(1 << 20), fb.read(1 << 20)
            if ca != cb:
                return False
            if not ca:
                return True


def _files(root: Path) -> list[str]:
    """Sorted POSIX relpaths of every regular file under root.

    Raises on a symlink: a link inside a pinned tree could point back at the
    live lake."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in [*dirnames, *filenames]:
            if (Path(dirpath) / name).is_symlink():
                raise RuntimeError(f"proof: symlink inside a pinned tree: {Path(dirpath) / name}")
        for name in filenames:
            if name in _IGNORED_NAMES:
                continue
            out.append((Path(dirpath) / name).relative_to(root).as_posix())
    return sorted(out)


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Window:
    lo: datetime.datetime
    hi: datetime.datetime
    day: str


def _build_window(tree: Path) -> _Window | None:
    """The span of the export run that produced `tree`, or None.

    Anchored on manifest.json's `built_at`; widened to every UTC instant with
    a fractional second among citations.parquet's retrieved_at values within
    3 h before / 1 h after it (derived rows carry their tier's own now()).
    Source stamps cannot fall inside: a snapshot pins them before the run
    starts, and SAM's are second-precision."""
    manifest = tree / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        obj = json.loads(manifest.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    anchor_s = obj.get("built_at") if isinstance(obj, dict) else None
    if not isinstance(anchor_s, str) or not _UTC_TS_RE.fullmatch(anchor_s):
        return None
    anchor = datetime.datetime.fromisoformat(anchor_s)
    lo, hi = anchor - _WINDOW_LOOKBACK, anchor + _WINDOW_LOOKAHEAD
    stamps = [anchor]
    cit = tree / "citations" / "citations.parquet"
    if cit.is_file():
        import duckdb

        con = duckdb.connect()
        try:
            cols = {r[0] for r in con.execute(
                "describe select * from read_parquet(?)", [str(cit)]).fetchall()}
            if "retrieved_at" in cols:
                for (v,) in con.execute(
                    "select distinct retrieved_at from read_parquet(?)"
                    " where retrieved_at is not null", [str(cit)],
                ).fetchall():
                    if isinstance(v, str) and _UTC_FRACTION_RE.fullmatch(v):
                        d = datetime.datetime.fromisoformat(v)
                        if lo <= d <= hi:
                            stamps.append(d)
        finally:
            con.close()
    return _Window(min(stamps), max(stamps), anchor_s[:10])


def _is_build_stamp(value, window: _Window | None) -> bool:
    if window is None or not isinstance(value, str) or not _UTC_TS_RE.fullmatch(value):
        return False
    return window.lo <= datetime.datetime.fromisoformat(value) <= window.hi


def _mask(obj, window: _Window | None):
    """Mask build stamps in place; return obj."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in STAMP_KEYS and _is_build_stamp(value, window):
                obj[key] = BUILD_TS
            elif key in DATE_KEYS and window is not None and value == window.day:
                obj[key] = BUILD_DATE
            else:
                _mask(value, window)
    elif isinstance(obj, list):
        for value in obj:
            _mask(value, window)
    return obj


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _escape(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def _json_changes(a, b, pointer: str, out: list) -> None:
    """Append (change, pointer, a, b) for every difference between a and b.

    Dicts recurse by key; lists compare as multisets of canonical JSON (a
    shuffled list is one `reordered` change; an inserted element is one
    `added` at `<list>/[]`); scalars must match in type AND value, so 1 vs
    1.0 or 1 vs true is a change."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            p = f"{pointer}/{_escape(key)}"
            if key not in b:
                out.append(("removed", p, a[key], None))
            elif key not in a:
                out.append(("added", p, None, b[key]))
            else:
                _json_changes(a[key], b[key], p, out)
        return
    if isinstance(a, list) and isinstance(b, list):
        ca, cb = [_canon(x) for x in a], [_canon(x) for x in b]
        if ca == cb:
            return
        ma, mb = Counter(ca), Counter(cb)
        if ma == mb:
            out.append(("reordered", pointer, None, None))
            return
        for s, n in sorted((ma - mb).items()):
            out.extend([("removed", pointer + "/[]", json.loads(s), None)] * n)
        for s, n in sorted((mb - ma).items()):
            out.extend([("added", pointer + "/[]", None, json.loads(s))] * n)
        return
    if type(a) is type(b) and a == b:
        return
    out.append(("changed", pointer, a, b))


def _pattern(pointer: str) -> str:
    return "/".join("{fid}" if _FID_RE.fullmatch(s) else s for s in pointer.split("/"))


def _short(value) -> str | None:
    if value is None:
        return None
    s = _canon(value)
    return s if len(s) <= _MAX_VALUE_CHARS else s[:_MAX_VALUE_CHARS] + "…"


def _json_detail(pa: Path, pb: Path, wa, wb) -> dict | None:
    """None when the two files hold the same JSON value after masking."""
    a = _mask(json.loads(pa.read_text(encoding="utf-8")), wa)
    b = _mask(json.loads(pb.read_text(encoding="utf-8")), wb)
    raw: list = []
    _json_changes(a, b, "", raw)
    if not raw:
        return None
    grouped: dict[tuple[str, str], dict] = {}
    for change, pointer, va, vb in raw:
        key = (_pattern(pointer), change)
        entry = grouped.setdefault(
            key, {"pattern": key[0], "change": change, "count": 0, "samples": []}
        )
        entry["count"] += 1
        if len(entry["samples"]) < _SAMPLES_PER_CHANGE:
            entry["samples"].append({"pointer": pointer, "a": _short(va), "b": _short(vb)})
    return {"changes": [grouped[k] for k in sorted(grouped)]}


def _sql_path(path: Path) -> str:
    return "read_parquet('" + str(path).replace("'", "''") + "')"


def _masked_select(con, path: Path, schema: list, window, tag: str) -> str:
    src = _sql_path(path)
    exprs = []
    for i, (name, typ) in enumerate(schema):
        q = '"' + name.replace('"', '""') + '"'
        if name in STAMP_KEYS and typ == "VARCHAR" and window is not None:
            masked = [
                v for (v,) in con.execute(
                    f"select distinct {q} from {src} where {q} is not null").fetchall()
                if _is_build_stamp(v, window)
            ]
            if masked:
                table = f"mask_{tag}_{i}"
                con.execute(f"create temp table {table} (v varchar)")
                con.executemany(f"insert into {table} values (?)", [(v,) for v in masked])
                exprs.append(
                    f"case when {q} in (select v from {table}) then '{BUILD_TS}'"
                    f" else {q} end as {q}"
                )
                continue
        exprs.append(q)
    return f"select {', '.join(exprs)} from {src}"


def _jsonable_rows(cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [json.loads(json.dumps(dict(zip(cols, row)), default=str)) for row in cursor.fetchall()]


def _parquet_detail(pa: Path, pb: Path, wa, wb) -> dict | None:
    """None when the two files hold the same row multiset after masking."""
    import duckdb

    con = duckdb.connect()
    try:
        schema_a = [[r[0], r[1]] for r in con.execute(f"describe select * from {_sql_path(pa)}").fetchall()]
        schema_b = [[r[0], r[1]] for r in con.execute(f"describe select * from {_sql_path(pb)}").fetchall()]
        rows_a = con.execute(f"select count(*) from {_sql_path(pa)}").fetchone()[0]
        rows_b = con.execute(f"select count(*) from {_sql_path(pb)}").fetchone()[0]
        if schema_a != schema_b:
            return {"schema_a": schema_a, "schema_b": schema_b, "rows_a": rows_a,
                    "rows_b": rows_b, "only_a": None, "only_b": None,
                    "sample_only_a": [], "sample_only_b": []}
        sel_a = _masked_select(con, pa, schema_a, wa, "a")
        sel_b = _masked_select(con, pb, schema_b, wb, "b")
        only_a = con.execute(f"select count(*) from ({sel_a} except all {sel_b})").fetchone()[0]
        only_b = con.execute(f"select count(*) from ({sel_b} except all {sel_a})").fetchone()[0]
        if only_a == 0 and only_b == 0:
            return None
        return {
            "schema_a": schema_a, "schema_b": schema_b, "rows_a": rows_a, "rows_b": rows_b,
            "only_a": only_a, "only_b": only_b,
            "sample_only_a": _jsonable_rows(con.execute(
                f"select * from ({sel_a} except all {sel_b}) limit {_SAMPLE_ROWS}")),
            "sample_only_b": _jsonable_rows(con.execute(
                f"select * from ({sel_b} except all {sel_a}) limit {_SAMPLE_ROWS}")),
        }
    finally:
        con.close()


def _kind(rel: str) -> str:
    if rel.endswith(".json"):
        return "json"
    if rel.endswith(".parquet"):
        return "parquet"
    return "bytes"


def _group(rel: str, dir_counts: Counter) -> str:
    parent, _, name = rel.rpartition("/")
    if parent and dir_counts[parent] >= _GROUP_MIN_FILES:
        return f"{parent}/*{Path(name).suffix}"
    return rel


def diff_trees(a: Path, b: Path) -> dict:
    """Compare two data/site trees; return the report (see module docstring).

    report["counts"] has every status in STATUSES; report["files"] lists each
    file that is not byte-identical; report["groups"] tallies statuses per
    path group (a directory with 50+ files collapses to '<dir>/*<suffix>')."""
    a, b = Path(a), Path(b)
    for root in (a, b):
        if not root.is_dir():
            raise NotADirectoryError(f"proof diff: {root} is not a directory")
    wa, wb = _build_window(a), _build_window(b)
    files_a, files_b = set(_files(a)), set(_files(b))
    every = sorted(files_a | files_b)
    dir_counts = Counter(rel.rpartition("/")[0] for rel in every)
    counts = Counter({s: 0 for s in STATUSES})
    groups: dict[str, Counter] = {}
    files: dict[str, dict] = {}
    for rel in every:
        kind, group = _kind(rel), _group(rel, dir_counts)
        detail = None
        if rel not in files_b:
            status = "only_a"
        elif rel not in files_a:
            status = "only_b"
        elif _same_bytes(a / rel, b / rel):
            status = "identical"
        else:
            if kind == "json":
                try:
                    detail = _json_detail(a / rel, b / rel, wa, wb)
                except ValueError:  # not JSON after all: compare as bytes
                    kind = "bytes"
            elif kind == "parquet":
                detail = _parquet_detail(a / rel, b / rel, wa, wb)
            if kind == "bytes":
                detail = {"sha256_a": _sha256_file(a / rel), "sha256_b": _sha256_file(b / rel)}
            status = "changed" if detail is not None else "equivalent"
        counts[status] += 1
        groups.setdefault(group, Counter({s: 0 for s in STATUSES}))[status] += 1
        if status != "identical":
            files[rel] = {"status": status, "kind": kind, "group": group, "detail": detail}
    return {
        "a": str(a),
        "b": str(b),
        "build_window": {
            side: (None if w is None else [w.lo.isoformat(), w.hi.isoformat()])
            for side, w in (("a", wa), ("b", wb))
        },
        "counts": dict(counts),
        "groups": {g: dict(c) for g, c in sorted(groups.items())},
        "files": files,
    }


def is_equal(report: dict) -> bool:
    c = report["counts"]
    return c["changed"] == 0 and c["only_a"] == 0 and c["only_b"] == 0


# ---------------------------------------------------------------------------
# expectations (--expect)
# ---------------------------------------------------------------------------


def _glob(pattern: str, text: str) -> bool:
    """`*` matches any run of characters (including '/'); nothing else is special."""
    rx = "".join(".*" if c == "*" else re.escape(c) for c in pattern)
    return re.fullmatch(rx, text, re.DOTALL) is not None


def load_expectations(path: Path) -> list[dict]:
    """Read and validate an --expect file: a JSON list of rules.

    Rule keys: path (required glob over the tree-relative path), why
    (required, non-empty: the allowed-change description), status (list of
    'equivalent'-free statuses: changed/only_a/only_b), pointer (glob over a
    JSON change pattern such as '/{fid}/retrieved_at' or '/decade_series/[]'),
    change (list of added/removed/changed/reordered), required (bool: the
    rule must match at least one difference)."""
    rules = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rules, list):
        raise ValueError("proof diff --expect: the file must hold a JSON list of rules")
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f"proof diff --expect: rule {i} is not an object")
        unknown = set(rule) - _RULE_KEYS
        if unknown:
            raise ValueError(f"proof diff --expect: rule {i} has unknown keys {sorted(unknown)}")
        if not isinstance(rule.get("path"), str) or not rule["path"]:
            raise ValueError(f"proof diff --expect: rule {i} needs a 'path' glob")
        if not isinstance(rule.get("why"), str) or not rule["why"].strip():
            raise ValueError(f"proof diff --expect: rule {i} needs a non-empty 'why'")
        if "status" in rule and not set(rule["status"]) <= {"changed", "only_a", "only_b"}:
            raise ValueError(f"proof diff --expect: rule {i} has a bad 'status' {rule['status']}")
        if "change" in rule and not set(rule["change"]) <= set(CHANGES):
            raise ValueError(f"proof diff --expect: rule {i} has a bad 'change' {rule['change']}")
        if "pointer" in rule and not isinstance(rule["pointer"], str):
            raise ValueError(f"proof diff --expect: rule {i} 'pointer' must be a string")
        if "required" in rule and not isinstance(rule["required"], bool):
            raise ValueError(f"proof diff --expect: rule {i} 'required' must be true/false")
    return rules


def _diff_items(report: dict) -> list[dict]:
    items = []
    for rel, entry in sorted(report["files"].items()):
        status = entry["status"]
        if status == "equivalent":
            continue
        if status == "changed" and entry["kind"] == "json":
            for ch in entry["detail"]["changes"]:
                items.append({"path": rel, "status": status, "pattern": ch["pattern"],
                              "change": ch["change"], "count": ch["count"]})
        else:
            items.append({"path": rel, "status": status, "pattern": None,
                          "change": None, "count": 1})
    return items


def _rule_matches(rule: dict, item: dict) -> bool:
    if not _glob(rule["path"], item["path"]):
        return False
    if "status" in rule and item["status"] not in rule["status"]:
        return False
    if "pointer" in rule and (item["pattern"] is None or not _glob(rule["pointer"], item["pattern"])):
        return False
    if "change" in rule and item["change"] not in rule["change"]:
        return False
    return True


def check_expectations(report: dict, rules: list[dict]) -> dict:
    """Every difference must match a rule; every `required` rule must match."""
    matched = [0] * len(rules)
    unexpected = []
    for item in _diff_items(report):
        hit = False
        for i, rule in enumerate(rules):
            if _rule_matches(rule, item):
                matched[i] += item["count"]
                hit = True
        if not hit:
            unexpected.append(item)
    unmet = [{"rule": i, "path": r["path"], "why": r["why"]}
             for i, r in enumerate(rules) if r.get("required") and matched[i] == 0]
    return {
        "ok": not unexpected and not unmet,
        "unexpected": unexpected,
        "unmet": unmet,
        "matched": [{"rule": i, "path": r["path"], "why": r["why"], "count": matched[i]}
                    for i, r in enumerate(rules)],
    }


def format_report(report: dict, verdict: dict | None = None) -> list[str]:
    """Human-readable lines; the last line is the verdict."""
    c = report["counts"]
    lines = [
        f"proof diff: A = {report['a']}",
        f"proof diff: B = {report['b']}",
        f"  build window A {report['build_window']['a']} · B {report['build_window']['b']}",
        f"  identical {c['identical']:,} · equivalent {c['equivalent']:,}"
        f" (build stamps, row order or JSON formatting only) · changed {c['changed']:,}"
        f" · only in A {c['only_a']:,} · only in B {c['only_b']:,}",
    ]
    for group, gc in report["groups"].items():
        if not (gc["changed"] or gc["only_a"] or gc["only_b"]):
            continue
        lines.append(f"  {group}: changed {gc['changed']:,} · only in A {gc['only_a']:,}"
                     f" · only in B {gc['only_b']:,}")
        tally: Counter = Counter()
        for entry in report["files"].values():
            if entry["group"] != group or entry["status"] != "changed":
                continue
            if entry["kind"] == "json":
                for ch in entry["detail"]["changes"]:
                    tally[(ch["pattern"], ch["change"])] += ch["count"]
            elif entry["kind"] == "parquet":
                d = entry["detail"]
                tally[(f"rows {d['rows_a']:,} -> {d['rows_b']:,}; only in A {d['only_a']}"
                       f", only in B {d['only_b']}", "parquet")] += 1
            else:
                tally[("bytes differ", "bytes")] += 1
        for (pattern, change), n in tally.most_common(10):
            lines.append(f"    {change} {pattern} ×{n:,}")
    if verdict is None:
        lines.append("proof diff: EQUAL" if is_equal(report) else "proof diff: DIFFERENT")
        return lines
    for m in verdict["matched"]:
        lines.append(f"  rule {m['rule']} [{m['path']}] matched {m['count']:,}: {m['why']}")
    if verdict["unexpected"]:
        lines.append(f"  UNEXPECTED differences: {len(verdict['unexpected']):,}")
        for item in verdict["unexpected"][:50]:
            lines.append(f"    {item['path']} {item['status']}"
                         f" {item['change'] or ''} {item['pattern'] or ''} ×{item['count']:,}".rstrip())
    for u in verdict["unmet"]:
        lines.append(f"  UNMET required rule {u['rule']} [{u['path']}]: {u['why']}")
    lines.append("proof diff: PASS" if verdict["ok"] else "proof diff: FAIL")
    return lines
```

- [ ] **Step 4: Run the diff tests — they pass**

```bash
uv run --project . pytest tests/test_proof.py -q
```

Expected: `15 passed`.

- [ ] **Step 5: Commit the diff**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/proof.py GovBudget/tests/test_proof.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(proof): masked, parquet-aware diff of two data/site trees (families piece 1, spec §8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `2 files changed`.

- [ ] **Step 6: Write the failing CLI and snapshot tests**

Append to `tests/test_proof.py`, two blank lines after its last line (`    assert proof._glob("/{fid}/*", "/{fid}/retrieved_at")`):

```python
def test_cli_diff_exit_codes_and_report(tmp_path, capsys):
    _expect_fixture(tmp_path)
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", a, b])
    assert exc.value.code == 1
    assert capsys.readouterr().out.splitlines()[-1] == "proof diff: DIFFERENT"

    expect = tmp_path / "expect.json"
    expect.write_text(json.dumps([
        {"path": "json/program_details/*.json", "why": "era points"},
        {"path": "data/*.parquet", "why": "new dataset"},
    ]))
    out = tmp_path / "report.json"
    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", a, b, "--expect", str(expect), "--report", str(out)])
    assert exc.value.code == 0
    assert capsys.readouterr().out.splitlines()[-1] == "proof diff: PASS"
    saved = json.loads(out.read_text())
    assert saved["verdict"]["ok"] is True
    assert saved["report"]["counts"]["only_b"] == 1

    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", a, a])
    assert exc.value.code == 0
    assert capsys.readouterr().out.splitlines()[-1] == "proof diff: EQUAL"


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


def test_config_follows_govbudget_data_except_research(tmp_path):
    """Every lake path export-site uses moves with GOVBUDGET_DATA; RESEARCH_DIR
    stays with the code checkout."""
    code = (
        "import json; from govbudget import config as c; print(json.dumps({k: str(getattr(c, k))"
        " for k in ('DATA_DIR','SITE_DIR','DUCKDB_PATH','PARQUET_DIR','RAW_DOCS_DIR',"
        "'MANIFEST_PATH','RESEARCH_DIR','ROOT')}))"
    )
    env = {**os.environ, "GOVBUDGET_DATA": str(tmp_path)}
    env.pop("GOVBUDGET_DUCKDB", None)
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True,
                         text=True, check=True, cwd=ROOT)
    got = json.loads(out.stdout)
    base = str(tmp_path.resolve())
    assert got["DATA_DIR"] == base
    assert got["SITE_DIR"] == f"{base}/site"
    assert got["DUCKDB_PATH"] == f"{base}/duckdb/govbudget.duckdb"
    assert got["PARQUET_DIR"] == f"{base}/parquet"
    assert got["RAW_DOCS_DIR"] == f"{base}/raw_docs"
    assert got["MANIFEST_PATH"] == f"{base}/manifest.jsonl"
    assert got["RESEARCH_DIR"] == f"{got['ROOT']}/data/research"


def test_snapshot_refuses_inside_the_sam_write_window(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 17))
    with pytest.raises(RuntimeError, match="SAM job writes data/parquet/sam at :17"):
        proof.snapshot(tmp_path / "s", data_dir=tmp_path, pg_dsn="postgresql://x/db",
                       scratch_db="snap")
    assert not (tmp_path / "s").exists()


@pytest.mark.parametrize("scratch, message", [
    ("Bad-Name", "must match"),
    ("db", "cannot be the source database"),
])
def test_snapshot_refuses_bad_scratch_names(tmp_path, monkeypatch, scratch, message):
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    with pytest.raises(ValueError, match=message):
        proof.snapshot(tmp_path / "s", data_dir=tmp_path / "data",
                       pg_dsn="postgresql://x/db", scratch_db=scratch)


def test_snapshot_refuses_an_existing_out_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    (tmp_path / "s").mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        proof.snapshot(tmp_path / "s", data_dir=tmp_path / "data",
                       pg_dsn="postgresql://x/db", scratch_db="snap")


def _lake(data: Path) -> None:
    """A miniature lake: a DuckDB view that embeds its parquet's absolute path."""
    _parquet(data / "parquet" / "jbooks" / "budget_lines.parquet",
             [("pe_bli", "varchar"), ("amount_thousands", "double")], [("ATA000", 1.5)])
    (data / "duckdb").mkdir(parents=True)
    con = duckdb.connect(str(data / "duckdb" / "govbudget.duckdb"))
    try:
        con.execute(
            "create view stg_budget_lines as select * from read_parquet("
            f"'{data.resolve()}/parquet/jbooks/budget_lines.parquet')"
        )
        con.execute("create table fct_decade_series as select 1 as n")
    finally:
        con.close()
    _json(data / "site" / "manifest.json", {"built_at": BUILT_A})
    (data / "raw_docs" / "fy2017" / "dod").mkdir(parents=True)
    (data / "raw_docs" / "fy2017" / "dod" / "p1_display.xlsx").write_bytes(b"xlsx")
    (data / "manifest.jsonl").write_text('{"stage": "fixture"}\n')


def test_view_rewrite_repoints_the_copy_and_leaves_the_source(tmp_path):
    live = tmp_path / "live"
    _lake(live)
    snap = tmp_path / "snap"
    (snap / "duckdb").mkdir(parents=True)
    shutil.copy(live / "duckdb" / "govbudget.duckdb", snap / "duckdb" / "govbudget.duckdb")
    shutil.copytree(live / "parquet", snap / "parquet")
    got = proof._rewrite_duckdb_views(snap / "duckdb" / "govbudget.duckdb",
                                      old_root=live.resolve(), new_root=snap.resolve())
    assert got == {"views": 1, "rewritten": 1}
    shutil.rmtree(live / "parquet")          # the copy must not need the live lake
    con = duckdb.connect(str(snap / "duckdb" / "govbudget.duckdb"), read_only=True)
    try:
        assert con.execute("select pe_bli from stg_budget_lines").fetchall() == [("ATA000",)]
    finally:
        con.close()


@pytest.fixture()
def pg_source():
    """A throwaway source database on the TEST cluster, never the real one."""
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    except psycopg.OperationalError as e:
        pytest.skip(f"Postgres unavailable ({e}); start the test cluster (Task 1)")
    for db in ("proof_src_test", "proof_scratch_test"):
        admin.execute(f"drop database if exists {db}")
    admin.execute("create database proof_src_test")
    dsn = urlunsplit(urlsplit(ADMIN_DSN)._replace(path="/proof_src_test"))
    yield admin, dsn
    for db in ("proof_src_test", "proof_scratch_test"):
        admin.execute(f"drop database if exists {db} with (force)")
    admin.close()


def test_snapshot_pins_lake_and_postgres(tmp_path, monkeypatch, pg_source):
    admin, src_dsn = pg_source
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    live = tmp_path / "live"
    _lake(live)
    doc = f"{live.resolve()}/raw_docs/fy2017/dod/p1_display.xlsx"
    with psycopg.connect(src_dsn) as con:
        con.execute("create table jbook_documents (id serial primary key, file_path text)")
        con.execute("insert into jbook_documents (file_path) values (%s)", (doc,))
        con.execute("create table budget_lines (pe_bli text, amount numeric)")
        con.execute("insert into budget_lines values ('ATA000', 1.5), ('B02100', 2)")
    out = tmp_path / "proofs" / "s0"

    m = proof.snapshot(out, data_dir=live, pg_dsn=src_dsn, scratch_db="proof_scratch_test")

    scratch_dsn = urlunsplit(urlsplit(ADMIN_DSN)._replace(path="/proof_scratch_test"))
    assert m["env"] == {"GOVBUDGET_DATA": str(out),
                        "GOVBUDGET_DUCKDB": f"{out}/duckdb/govbudget.duckdb",
                        "GOVBUDGET_PG_DSN": scratch_dsn}
    assert m["duckdb"]["views"] == 1 and m["duckdb"]["views_rewritten"] == 1
    assert m["parquet"]["jbooks/budget_lines.parquet"]["rows"] == 1
    assert m["site"]["files"] == 1 and m["raw_docs"]["files"] == 1
    assert m["pg"]["tables"]["budget_lines"]["rows"] == 2
    assert m["pg"]["rewrites"] == {"jbook_documents.file_path": 1}
    assert json.loads((out / "snapshot.json").read_text()) == m
    with psycopg.connect(src_dsn) as con:    # the digest is the source's own
        src_md5 = con.execute(
            "select md5(coalesce(string_agg(h, '' order by h), ''))"
            " from (select md5(t::text) as h from public.budget_lines t) s").fetchone()[0]
        assert con.execute("select file_path from jbook_documents").fetchone()[0] == doc
    assert m["pg"]["tables"]["budget_lines"]["md5"] == src_md5
    with psycopg.connect(scratch_dsn) as con:
        assert con.execute("select file_path from jbook_documents").fetchone()[0] == (
            f"{out}/raw_docs/fy2017/dod/p1_display.xlsx")
    with pytest.raises(FileExistsError, match="database proof_scratch_test already exists"):
        proof.snapshot(tmp_path / "proofs" / "s1", data_dir=live, pg_dsn=src_dsn,
                       scratch_db="proof_scratch_test")
    assert not (tmp_path / "proofs" / "s1").exists()
    shutil.rmtree(live / "parquet")
    con = duckdb.connect(str(out / "duckdb" / "govbudget.duckdb"), read_only=True)
    try:
        assert con.execute("select count(*) from stg_budget_lines").fetchone()[0] == 1
    finally:
        con.close()
    env = subprocess.run(
        ["bash", "-c", f'source "{out}/env.sh" "{out}-A" && echo "$GOVBUDGET_DATA|$GOVBUDGET_DUCKDB|$GOVBUDGET_PG_DSN"'],
        capture_output=True, text=True, check=True).stdout.strip()
    assert env == f"{out}-A|{out}-A/duckdb/govbudget.duckdb|{scratch_dsn}"
```

- [ ] **Step 7: Run them — the new ones fail**

```bash
uv run --project . pytest tests/test_proof.py -q
```

Expected: `7 failed, 16 passed`:
`test_cli_diff_exit_codes_and_report` (`assert 2 == 1` — argparse rejects `proof`), the four `test_snapshot_refuses_*` cases (SAM window, two bad names, existing out dir) and `test_snapshot_pins_lake_and_postgres` (`AttributeError: module 'govbudget.proof' has no attribute 'snapshot'`), and `test_view_rewrite_repoints_the_copy_and_leaves_the_source` (`... no attribute '_rewrite_duckdb_views'`). `test_config_follows_govbudget_data_except_research` already passes: it pins the existing `config.py` behaviour the snapshot relies on. If `test_snapshot_pins_lake_and_postgres` shows `SKIPPED` instead, the test cluster is down — restart it (Task 1 Step 5).

- [ ] **Step 8: Implement the snapshot half of `src/govbudget/proof.py`**

Append to `src/govbudget/proof.py`, two blank lines after its last line (the end of `format_report`, `    return lines`):

```python
# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


def snapshot(out_dir: Path, *, data_dir: Path, pg_dsn: str, scratch_db: str) -> dict:
    """Pin everything export-site reads into out_dir; return the manifest.

    Writes out_dir/{duckdb,parquet,site,raw_docs,manifest.jsonl} (APFS clones),
    out_dir/pg/<db>.dump, out_dir/snapshot.json and out_dir/env.sh, and restores
    the dump into a NEW database `scratch_db` on the same server. Refuses if
    out_dir or the scratch database already exists, inside the SAM write window
    (:15-:20), or while a writer holds the DuckDB file.
    """
    out_dir = Path(out_dir).absolute()
    data_dir = Path(data_dir).resolve()
    _check_sam_window("before the copy")
    if out_dir.exists():
        raise FileExistsError(f"proof snapshot: {out_dir} already exists")
    if out_dir == data_dir or data_dir in out_dir.parents:
        raise ValueError(f"proof snapshot: {out_dir} is inside the lake {data_dir}")
    if not _SCRATCH_DB_RE.fullmatch(scratch_db):
        raise ValueError(
            f"proof snapshot: scratch database name {scratch_db!r} must match"
            f" {_SCRATCH_DB_RE.pattern}"
        )
    source_db = urlsplit(pg_dsn).path.lstrip("/")
    if not source_db:
        raise ValueError(f"proof snapshot: {pg_dsn!r} names no database")
    if scratch_db == source_db:
        raise ValueError("proof snapshot: the scratch database cannot be the source database")
    src_duckdb = data_dir / DUCKDB_REL
    for required in (src_duckdb, data_dir / MANIFEST_REL, *(data_dir / d for d in CLONED_DIRS)):
        if not required.exists():
            raise FileNotFoundError(f"proof snapshot: {required} is missing")
    wal = src_duckdb.with_name(src_duckdb.name + ".wal")
    if wal.exists():
        raise RuntimeError(f"proof snapshot: {wal} exists — a DuckDB write is unfinished")
    if _database_exists(pg_dsn, scratch_db):
        raise FileExistsError(
            f"proof snapshot: database {scratch_db} already exists — drop it"
            f" (dropdb) or choose another --scratch-db"
        )

    import duckdb

    # A read-only connection holds DuckDB's shared file lock for the whole
    # copy, so no writer (dbt build) can start mid-clone — and it fails here,
    # before anything is written, if a writer already holds the file.
    try:
        lock = duckdb.connect(str(src_duckdb), read_only=True)
    except duckdb.IOException as e:
        raise RuntimeError(f"proof snapshot: {src_duckdb} is being written ({e}); retry later") from e
    try:
        out_dir.mkdir(parents=True)
        (out_dir / DUCKDB_REL.parent).mkdir()
        _clone(src_duckdb, out_dir / DUCKDB_REL)
        for name in CLONED_DIRS:
            _clone(data_dir / name, out_dir / name)
        _clone(data_dir / MANIFEST_REL, out_dir / MANIFEST_REL)
    finally:
        lock.close()
    _check_sam_window(f"after the copy — delete {out_dir} and retry")

    duckdb_sha_at_copy = _sha256_file(out_dir / DUCKDB_REL)
    views = _rewrite_duckdb_views(out_dir / DUCKDB_REL, old_root=data_dir, new_root=out_dir)
    pg = _pg_snapshot(
        pg_dsn, scratch_db, out_dir / "pg",
        old_raw_docs=data_dir / "raw_docs", new_raw_docs=out_dir / "raw_docs",
        data_dir=data_dir,
    )
    env = {
        "GOVBUDGET_DATA": str(out_dir),
        "GOVBUDGET_DUCKDB": str(out_dir / DUCKDB_REL),
        "GOVBUDGET_PG_DSN": pg["scratch_dsn"],
    }
    manifest = {
        "schema_version": 1,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "out_dir": str(out_dir),
        "source": {"data_dir": str(data_dir), "pg_dsn": pg_dsn},
        "env": env,
        "duckdb": {
            "path": DUCKDB_REL.as_posix(),
            "sha256_at_copy": duckdb_sha_at_copy,
            "sha256": _sha256_file(out_dir / DUCKDB_REL),
            "views": views["views"],
            "views_rewritten": views["rewritten"],
        },
        "parquet": _parquet_digest(out_dir / "parquet"),
        "site": _tree_digest(out_dir / "site"),
        "raw_docs": _tree_digest(out_dir / "raw_docs"),
        "manifest_jsonl_sha256": _sha256_file(out_dir / MANIFEST_REL),
        "pg": pg,
    }
    (out_dir / SNAPSHOT_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / SNAPSHOT_ENV).write_text(_env_script(manifest), encoding="utf-8")
    return manifest


def _check_sam_window(stage: str) -> None:
    now = _now()
    if now.minute in SAM_WINDOW_MINUTES:
        raise RuntimeError(
            f"proof snapshot: refusing at {now:%H:%M} ({stage}) — the hourly SAM"
            " job writes data/parquet/sam at :17; run outside :15-:20"
        )


def _clone(src: Path, dst: Path) -> None:
    """APFS copy-on-write clone (macOS `cp -c`): seconds, no extra space."""
    done = subprocess.run(
        ["cp", "-c", "-R", str(src), str(dst)], capture_output=True, text=True
    )
    if done.returncode != 0:
        raise RuntimeError(
            f"proof snapshot: cp -c -R {src} {dst} failed: {done.stderr.strip()}"
            " (snapshots need APFS clones on one volume)"
        )


def _tree_digest(root: Path) -> dict:
    lines, total = [], 0
    files = _files(root)
    for rel in files:
        size = (root / rel).stat().st_size
        total += size
        lines.append(f"{rel}\t{size}\t{_sha256_file(root / rel)}\n")
    return {
        "files": len(files),
        "bytes": total,
        "sha256": hashlib.sha256("".join(lines).encode("utf-8")).hexdigest(),
    }


def _parquet_digest(root: Path) -> dict:
    import duckdb

    con = duckdb.connect()
    try:
        out = {}
        for rel in _files(root):
            path = root / rel
            rows = None
            if rel.endswith(".parquet"):
                rows = con.execute(
                    "select sum(num_rows) from parquet_file_metadata(?)", [str(path)]
                ).fetchone()[0]
            out[rel] = {
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
                "rows": int(rows) if rows is not None else None,
            }
        return out
    finally:
        con.close()


def _rewrite_duckdb_views(db_path: Path, *, old_root: Path, new_root: Path) -> dict:
    """Repoint every view that embeds old_root at new_root, in the copy only.

    DuckDB binds a view when it is created, so new_root's parquet must
    already exist (snapshot() clones it first). Raises if any view still names
    old_root afterwards."""
    import duckdb

    old, new = str(old_root) + "/", str(new_root) + "/"
    con = duckdb.connect(str(db_path))
    try:
        views = con.execute(
            "select view_name, sql from duckdb_views()"
            " where not internal and database_name = current_database()"
            " order by view_name"
        ).fetchall()
        rewritten = 0
        for name, sql in views:
            if old not in sql:
                continue
            if not sql.startswith("CREATE VIEW "):
                raise RuntimeError(f"proof snapshot: unexpected DDL for view {name}: {sql[:80]!r}")
            con.execute("CREATE OR REPLACE VIEW " + sql[len("CREATE VIEW "):].replace(old, new))
            rewritten += 1
        left = con.execute(
            "select view_name from duckdb_views()"
            " where not internal and database_name = current_database()"
            " and contains(sql, ?)",
            [old],
        ).fetchall()
        if left:
            raise RuntimeError(f"proof snapshot: views still read {old}: {sorted(r[0] for r in left)}")
        con.execute("checkpoint")
    finally:
        con.close()
    return {"views": len(views), "rewritten": rewritten}


def _pg_bin(name: str) -> str:
    env_dir = os.environ.get("GOVBUDGET_PG_BIN")
    if env_dir:
        cand = Path(env_dir) / name
        if cand.is_file():
            return str(cand)
        raise FileNotFoundError(f"proof snapshot: {cand} not found (GOVBUDGET_PG_BIN)")
    found = shutil.which(name)
    if found:
        return found
    cand = DEFAULT_PG_BIN / name
    if cand.is_file():
        return str(cand)
    raise FileNotFoundError(
        f"proof snapshot: {name} not found — set GOVBUDGET_PG_BIN to the Postgres bin directory"
    )


def _with_database(dsn: str, database: str) -> str:
    parts = urlsplit(dsn)
    return urlunsplit(parts._replace(path="/" + database))


def _database_exists(pg_dsn: str, name: str) -> bool:
    import psycopg

    with psycopg.connect(_with_database(pg_dsn, "postgres"), autocommit=True) as admin:
        return admin.execute(
            "select 1 from pg_database where datname = %s", (name,)
        ).fetchone() is not None


def _run(cmd: list[str]) -> str:
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"proof snapshot: {' '.join(cmd[:2])} failed: {done.stderr.strip()}")
    return done.stdout


def _pg_snapshot(
    pg_dsn: str, scratch_db: str, dump_dir: Path, *,
    old_raw_docs: Path, new_raw_docs: Path, data_dir: Path,
) -> dict:
    import psycopg
    from psycopg import sql

    source_db = urlsplit(pg_dsn).path.lstrip("/")
    scratch_dsn = _with_database(pg_dsn, scratch_db)
    dump_dir.mkdir()
    dump = dump_dir / f"{source_db}.dump"
    _run([_pg_bin("pg_dump"), "--format=custom", "--no-owner", "--no-privileges",
          f"--file={dump}", pg_dsn])
    with psycopg.connect(_with_database(pg_dsn, "postgres"), autocommit=True) as admin:
        admin.execute(sql.SQL("create database {}").format(sql.Identifier(scratch_db)))
    _run([_pg_bin("pg_restore"), "--no-owner", "--no-privileges", "--exit-on-error",
          f"--dbname={scratch_dsn}", str(dump)])

    tables: dict[str, dict] = {}
    rewrites: dict[str, int] = {}
    with psycopg.connect(scratch_dsn) as con:
        # Pin the row-to-text rendering so the digests compare across sessions.
        con.execute("set time zone 'UTC'")
        con.execute("set datestyle = 'ISO, YMD'")
        con.execute("set extra_float_digits = 1")
        names = [r[0] for r in con.execute(
            "select table_name from information_schema.tables"
            " where table_schema = 'public' and table_type = 'BASE TABLE'"
            " order by table_name"
        ).fetchall()]
        for name in names:
            rows, digest = con.execute(sql.SQL(
                "select count(*), md5(coalesce(string_agg(h, '' order by h), ''))"
                " from (select md5(t::text) as h from {} t) s"
            ).format(sql.Identifier("public", name))).fetchone()
            tables[name] = {"rows": int(rows), "md5": digest}
        # Digests above describe the dump as taken. Only now repoint the
        # document paths at the cloned raw_docs, so export-site run against
        # this database never opens a live-lake file.
        if con.execute("select to_regclass('public.jbook_documents')").fetchone()[0]:
            old, new = str(old_raw_docs) + "/", str(new_raw_docs) + "/"
            cur = con.execute(
                "update jbook_documents set file_path = %s || substr(file_path, length(%s) + 1)"
                " where left(file_path, length(%s)) = %s",
                (new, old, old, old),
            )
            rewrites["jbook_documents.file_path"] = cur.rowcount
            live = str(data_dir) + "/"
            left = con.execute(
                "select count(*) from jbook_documents where left(file_path, length(%s)) = %s",
                (live, live),
            ).fetchone()[0]
            if left:
                raise RuntimeError(
                    f"proof snapshot: {left} jbook_documents.file_path row(s) still under {live}"
                )
        con.commit()
    return {
        "source_db": source_db,
        "scratch_db": scratch_db,
        "scratch_dsn": scratch_dsn,
        "dump": f"pg/{dump.name}",
        "dump_sha256": _sha256_file(dump),
        "pg_dump_version": _run([_pg_bin("pg_dump"), "--version"]).strip(),
        "tables": tables,
        "rewrites": rewrites,
    }


def _env_script(manifest: dict) -> str:
    env = manifest["env"]
    return (
        f"# Written by `govbudget proof snapshot` at {manifest['created_at']}.\n"
        "# Usage: source env.sh [RUN_DIR]\n"
        "#   no argument: point export-site/dbt/verify-* at this snapshot itself;\n"
        "#   RUN_DIR:     a `cp -c -R` clone of this snapshot to export into.\n"
        f'_proof_dir="${{1:-{env["GOVBUDGET_DATA"]}}}"\n'
        'export GOVBUDGET_DATA="$_proof_dir"\n'
        'export GOVBUDGET_DUCKDB="$_proof_dir/duckdb/govbudget.duckdb"\n'
        f"export GOVBUDGET_PG_DSN={shlex.quote(env['GOVBUDGET_PG_DSN'])}\n"
        "unset _proof_dir\n"
    )
```

- [ ] **Step 9: Add the `proof` CLI**

In `src/govbudget/cli.py`, insert `cmd_proof` before `main`. Before (lines 2936-2942):

```python
    if not record["ok"]:
        sys.exit(1)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="govbudget")
    sub = p.add_subparsers(dest="cmd", required=True)
```

After:

```python
    if not record["ok"]:
        sys.exit(1)


def cmd_proof(args) -> None:
    """Families piece 1: pinned proof snapshots and the masked export diff."""
    import json as _json

    from govbudget import proof

    if args.proof_action == "snapshot":
        m = proof.snapshot(
            args.out, data_dir=args.data_dir, pg_dsn=args.pg_dsn,
            scratch_db=args.scratch_db,
        )
        print(f"proof snapshot: {m['out_dir']}")
        print(f"  duckdb sha256 {m['duckdb']['sha256_at_copy']}"
              f" ({m['duckdb']['views_rewritten']} of {m['duckdb']['views']} views repointed)")
        print(f"  parquet files {len(m['parquet'])} · site files {m['site']['files']:,}"
              f" · raw_docs files {m['raw_docs']['files']:,}")
        print(f"  postgres {m['pg']['source_db']} -> {m['pg']['scratch_db']}"
              f" ({len(m['pg']['tables'])} tables, dump sha256 {m['pg']['dump_sha256']})")
        print(f"  source {m['out_dir']}/{proof.SNAPSHOT_ENV} [RUN_DIR]")
        return
    report = proof.diff_trees(args.a, args.b)
    verdict = None
    if args.expect is not None:
        verdict = proof.check_expectations(report, proof.load_expectations(args.expect))
    if args.report is not None:
        args.report.write_text(
            _json.dumps({"report": report, "verdict": verdict}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    for line in proof.format_report(report, verdict):
        print(line)
    ok = verdict["ok"] if verdict is not None else proof.is_equal(report)
    sys.exit(0 if ok else 1)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="govbudget")
    sub = p.add_subparsers(dest="cmd", required=True)
```

Then insert the parser. Before (lines 3333-3339):

```python
    rfr.add_argument("--yes", action="store_true",
                     help="skip the confirmation prompt. REQUIRED for scheduled "
                          "runs — launchd gives a job no TTY")
    rfr.set_defaults(func=cmd_refresh)

    args = p.parse_args(argv)
    args.func(args)
```

After:

```python
    rfr.add_argument("--yes", action="store_true",
                     help="skip the confirmation prompt. REQUIRED for scheduled "
                          "runs — launchd gives a job no TTY")
    rfr.set_defaults(func=cmd_refresh)

    prf = sub.add_parser(
        "proof",
        help="families piece 1: pin a proof snapshot; diff two data/site trees",
    )
    prf_sub = prf.add_subparsers(dest="proof_action", required=True)
    prf_snap = prf_sub.add_parser(
        "snapshot",
        help="APFS-clone the lake export-site reads + restore Postgres into a scratch db",
    )
    prf_snap.add_argument("--out", type=Path, required=True,
                          help="new directory, e.g. <main GovBudget>/.proofs/s0")
    prf_snap.add_argument("--scratch-db", required=True, dest="scratch_db",
                          help="NEW database on the same server for the restored dump")
    prf_snap.add_argument("--data-dir", type=Path, default=config.DATA_DIR, dest="data_dir")
    prf_snap.add_argument("--pg-dsn", default=config.PG_DSN, dest="pg_dsn")
    prf_snap.set_defaults(func=cmd_proof)
    prf_diff = prf_sub.add_parser(
        "diff",
        help="compare two data/site trees (build stamps masked; parquet as row multisets)",
    )
    prf_diff.add_argument("a", type=Path)
    prf_diff.add_argument("b", type=Path)
    prf_diff.add_argument("--expect", type=Path, default=None,
                          help="JSON list of allowed-difference rules; FAIL on anything else")
    prf_diff.add_argument("--report", type=Path, default=None,
                          help="also write the full JSON report here")
    prf_diff.set_defaults(func=cmd_proof)

    args = p.parse_args(argv)
    args.func(args)
```

- [ ] **Step 10: Run the tests — all pass**

```bash
uv run --project . pytest tests/test_proof.py tests/test_budget_pdf_export_workflow.py tests/test_roadmap_backlog.py -q -rs
uv run --project . python -m govbudget proof --help
```

Expected: `59 passed` (23 in `test_proof.py`, 6 in the unchanged export workflow, 30 in the ledger after Task 2) and no `SKIPPED` line; `--help` lists `{snapshot,diff}`.

- [ ] **Step 11: Smoke-test on the real lake, then remove the smoke snapshot**

This creates a scratch database `govbudget_proof_t3_smoke` on `localhost` (not a write to `govbudget`; the plan header allows `govbudget_proof_<name>` databases) and APFS clones under `.proofs/` (no extra space). The snapshot copy reads the live lake, so the plan header's SAM-window rule applies. Check the clock first — `date +%M` must not be 15–20 (the command refuses itself in that window). It takes a few minutes, mostly `pg_dump` and `pg_restore` of the 1 GB database.

```bash
source scripts/era/env.sh
uv run --project . python -m govbudget proof snapshot --out "$GOVBUDGET_PROOFS/t3-smoke" --scratch-db govbudget_proof_t3_smoke
```

Expected (shas vary; counts as of 2026-10-02 may drift with the lake):

```
proof snapshot: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t3-smoke
  duckdb sha256 <64 hex> (18 of 37 views repointed)
  parquet files 112 · site files 35,520 · raw_docs files 1,112
  postgres govbudget -> govbudget_proof_t3_smoke (18 tables, dump sha256 <64 hex>)
  source /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t3-smoke/env.sh [RUN_DIR]
```

Then verify the snapshot is hermetic and the diff sees the cloned site as equal to live:

```bash
uv run --project . python - <<'EOF'
import json, duckdb, psycopg
snap = "/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t3-smoke"
live = "/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/"
m = json.load(open(f"{snap}/snapshot.json"))
con = duckdb.connect(f"{snap}/duckdb/govbudget.duckdb", read_only=True)
print(con.execute("select count(*) from duckdb_views() where not internal and contains(sql, ?)", [live]).fetchone()[0],
      con.execute("select count(*) from dim_programs").fetchone()[0])
with psycopg.connect(m["env"]["GOVBUDGET_PG_DSN"]) as pg:
    print(m["pg"]["rewrites"], pg.execute(
        "select count(*) from jbook_documents where left(file_path, length(%s)) = %s", (live, live)).fetchone()[0])
EOF
uv run --project . python -m govbudget proof diff "$GOVBUDGET_DATA/site" "$GOVBUDGET_PROOFS/t3-smoke/site"
```

Expected: `0 1936`; `{'jbook_documents.file_path': 254} 0`; the diff prints `identical 35,520 · equivalent 0 (build stamps, row order or JSON formatting only) · changed 0 · only in A 0 · only in B 0` and ends `proof diff: EQUAL` (about 16 s).

Clean up:

```bash
"$GOVBUDGET_PG_BIN/psql" postgresql://localhost/postgres -c 'drop database govbudget_proof_t3_smoke'
rm -rf "$GOVBUDGET_PROOFS/t3-smoke"
```

Expected: `DROP DATABASE`.

- [ ] **Step 12: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/proof.py GovBudget/tests/test_proof.py GovBudget/src/govbudget/cli.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(proof): pinned proof snapshots (views and document paths repointed) + govbudget proof CLI (families piece 1, spec §8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `3 files changed`.
