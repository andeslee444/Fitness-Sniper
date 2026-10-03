"""govbudget.proof — pinned snapshots and the masked export diff (families piece 1, spec §8).

The diff decides whether an A/B export proof passes, so its masking is pinned
here on tiny trees: build stamps (every `built_at`, a `retrieved_at` that is a
UTC instant inside the tree's own build window, `measured_on` on the build day)
are masked; source stamps — workbook download times, SAM retrieval times — are
evidence and never are. Parquet files compare as row multisets. DOUBLE/FLOAT
values and JSON floats equal to 12 significant digits are float noise:
equivalent, counted apart, never changed.
"""
from __future__ import annotations

import datetime
import decimal
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
# The throwaway test cluster (Task 1). With GOVBUDGET_TEST_PG_DSN unset the
# fallback is still that cluster, so a missing env SKIPS instead of creating
# and dropping databases on the real server.
ADMIN_DSN = os.environ.get("GOVBUDGET_TEST_PG_DSN", "postgresql://127.0.0.1:55432/postgres")

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
    assert report["counts"] == {"identical": 5, "equivalent": 0, "reordered": 0,
                                "changed": 0, "only_a": 0, "only_b": 0}
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
    assert report["counts"] == {"identical": 49, "equivalent": 0, "reordered": 0,
                                "changed": 2, "only_a": 1, "only_b": 1}
    assert report["files"]["pdfs/x.pdf"]["kind"] == "bytes"
    assert report["files"]["gone.json"]["status"] == "only_a"
    assert report["files"]["new.json"]["status"] == "only_b"
    assert report["groups"]["json/program_details/*.json"] == {
        "identical": 49, "equivalent": 0, "reordered": 0, "changed": 1,
        "only_a": 0, "only_b": 0}


# ---------------------------------------------------------------------------
# float noise
# ---------------------------------------------------------------------------

# Two identical `select * ... order by all` queries on the live warehouse return
# parallel double sums that differ in the last bits (dim_geography,
# fct_district_totals, fct_program_concentration; pre-flight 2026-10-03).
NOISY = 4589898661.9800005
CLEAN = 4589898661.98
MOVED = 4589898662.98


def test_float_noise_is_equivalent_and_counted_on_its_own(tmp_path):
    # (a) DOUBLE parquet values and JSON floats equal to 12 significant digits
    assert NOISY != CLEAN
    cols = [("state", "varchar"), ("n", "integer"), ("total", "double")]
    _parquet(tmp_path / "a" / "data" / "dim_geography.parquet", cols,
             [("NY", 1, CLEAN), ("CA", 2, 7.5)])
    _parquet(tmp_path / "b" / "data" / "dim_geography.parquet", cols,
             [("CA", 2, 7.5), ("NY", 1, NOISY)])
    _json(tmp_path / "a" / "json" / "geo.json",
          {"total": CLEAN, "rows": [{"state": "NY", "total": CLEAN}, {"state": "CA", "total": 7.5}]})
    _json(tmp_path / "b" / "json" / "geo.json",
          {"total": NOISY, "rows": [{"state": "NY", "total": NOISY}, {"state": "CA", "total": 7.5}]})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert {rel: (e["status"], e["float_noise"]) for rel, e in report["files"].items()} == {
        "data/dim_geography.parquet": ("equivalent", 1),
        "json/geo.json": ("equivalent", 2),
    }
    assert report["counts"]["equivalent"] == 2 and report["counts"]["changed"] == 0
    assert report["float_noise"] == {"files": 2, "values": 3}
    assert proof.is_equal(report)
    assert ("  equivalent (float noise): 2 file(s), 3 value(s) equal to 12 significant digits"
            in proof.format_report(report))


def test_a_float_change_beyond_12_significant_digits_is_a_change(tmp_path):
    # (b) 4589898661.98 -> 4589898662.98 moves the 10th significant digit
    cols = [("state", "varchar"), ("n", "integer"), ("total", "double")]
    _parquet(tmp_path / "a" / "data" / "t.parquet", cols, [("NY", 1, CLEAN), ("CA", 2, 7.5)])
    _parquet(tmp_path / "b" / "data" / "t.parquet", cols, [("NY", 1, MOVED), ("CA", 2, 7.5)])
    _json(tmp_path / "a" / "p.json", {"total": CLEAN, "rows": [{"total": CLEAN}]})
    _json(tmp_path / "b" / "p.json", {"total": MOVED, "rows": [{"total": MOVED}]})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    pq = report["files"]["data/t.parquet"]
    assert (pq["status"], pq["float_noise"], pq["detail"]["only_a"], pq["detail"]["only_b"]) == (
        "changed", 0, 1, 1)
    assert pq["detail"]["sample_only_b"] == [{"state": "NY", "n": 1, "total": MOVED}]
    assert _changes(report, "p.json") == [
        ("/rows/[]", "added", 1), ("/rows/[]", "removed", 1), ("/total", "changed", 1)]
    assert report["float_noise"] == {"files": 0, "values": 0}
    assert not proof.is_equal(report)


@pytest.mark.parametrize("typ, va, vb", [
    ("bigint", 100_000_000_000_000, 100_000_000_000_001),
    ("decimal(38,10)", decimal.Decimal("4589898661.98"), decimal.Decimal("4589898661.9800000001")),
    ("varchar", "ABC-123", "ABC-124"),
])
def test_integers_decimals_and_strings_stay_exact(tmp_path, typ, va, vb):
    # (c) only DOUBLE/FLOAT columns (and, since ruling 1, a VARCHAR column
    # whose value is strict numeric text — covered separately below) get a
    # tolerant comparison: an integer, a decimal, or a plain non-numeric
    # string stays exact, even beside a double that differs only by noise
    cols = [("state", "varchar"), ("v", typ), ("total", "double")]
    _parquet(tmp_path / "a" / "data" / "t.parquet", cols, [("NY", va, CLEAN)])
    _parquet(tmp_path / "b" / "data" / "t.parquet", cols, [("NY", vb, NOISY)])
    pq = proof.diff_trees(tmp_path / "a", tmp_path / "b")["files"]["data/t.parquet"]
    assert (pq["status"], pq["detail"]["only_a"], pq["detail"]["only_b"]) == ("changed", 1, 1)


def test_json_integers_and_strings_stay_exact(tmp_path):
    # (c) for JSON: ints always compare exactly; a plain non-numeric string
    # stays exact too — only the float is noise
    _json(tmp_path / "a" / "p.json", {"n": 100_000_000_000_000, "s": "ABC-123", "x": CLEAN})
    _json(tmp_path / "b" / "p.json", {"n": 100_000_000_000_001, "s": "ABC-124", "x": NOISY})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert _changes(report, "p.json") == [("/n", "changed", 1), ("/s", "changed", 1)]
    assert report["files"]["p.json"]["float_noise"] == 1


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


@pytest.mark.parametrize("scratch, dsn, message", [
    ("Bad-Name", "postgresql://x/db", "must match"),
    # scratch must itself carry the required prefix (Fix round 1, Finding 1:
    # the prefix rule is now unconditional) to reach the self-conflict check
    # this case targets, so the source db is named with the prefix too.
    ("govbudget_proof_same", "postgresql://x/govbudget_proof_same",
     "cannot be the source database"),
])
def test_snapshot_refuses_bad_scratch_names(tmp_path, monkeypatch, scratch, dsn, message):
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    with pytest.raises(ValueError, match=message):
        proof.snapshot(tmp_path / "s", data_dir=tmp_path / "data",
                       pg_dsn=dsn, scratch_db=scratch)


def test_snapshot_refuses_an_existing_out_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    (tmp_path / "s").mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        proof.snapshot(tmp_path / "s", data_dir=tmp_path / "data",
                       pg_dsn="postgresql://x/db", scratch_db="snap")


def test_snapshot_refuses_an_out_dir_inside_the_lake_through_a_symlink(tmp_path, monkeypatch):
    # Fix round 1, Finding 2: in the real worktree, GovBudget/data/site is a
    # symlink into the live lake (Task 1). Path.absolute() does not follow
    # it, so a textually-outside out_dir could still land inside the lake
    # once the symlink resolves — the containment check must resolve both
    # sides, not just data_dir.
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    live = tmp_path / "live"
    live.mkdir()
    worktree_data = tmp_path / "worktree" / "data"
    worktree_data.parent.mkdir()
    worktree_data.symlink_to(live, target_is_directory=True)
    out_dir = worktree_data / "site" / "x"   # resolves into live/site/x
    with pytest.raises(ValueError, match="is inside the lake"):
        proof.snapshot(out_dir, data_dir=live, pg_dsn="postgresql://x/db",
                       scratch_db="govbudget_proof_snap")
    assert not (live / "site").exists()


@pytest.mark.parametrize("dsn", [
    "postgresql://localhost/govbudget",
    "postgresql://127.0.0.1:55432/postgres",
    "postgresql:///govbudget",
])
def test_snapshot_refuses_a_local_scratch_db_without_the_proof_prefix(tmp_path, monkeypatch, dsn):
    # README: on the local server only govbudget_proof_<name> may be created;
    # both the function and the CLI (cmd_proof) refuse before touching anything.
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    with pytest.raises(ValueError, match="must be named govbudget_proof_<name>"):
        proof.snapshot(tmp_path / "s", data_dir=tmp_path / "data", pg_dsn=dsn,
                       scratch_db="snap")
    with pytest.raises(ValueError, match="must be named govbudget_proof_<name>"):
        cli.main(["proof", "snapshot", "--out", str(tmp_path / "s"), "--scratch-db", "snap",
                  "--data-dir", str(tmp_path / "data"), "--pg-dsn", dsn])
    assert not (tmp_path / "s").exists()


def test_snapshot_refuses_a_non_prefixed_scratch_db_even_on_a_remote_looking_host(
    tmp_path, monkeypatch,
):
    # Fix round 1, Finding 1: the old check only required the prefix when the
    # DSN's netloc looked local, which a libpq query parameter (?host=...)
    # can silently contradict (verified: a DSN whose netloc names a remote
    # host can still connect to 127.0.0.1 via such a parameter). The rule is
    # now unconditional, so a DSN that merely LOOKS remote is refused too,
    # before any connection is attempted.
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    with pytest.raises(ValueError, match="must be named govbudget_proof_<name>"):
        proof.snapshot(tmp_path / "s", data_dir=tmp_path / "data",
                       pg_dsn="postgresql://remote.example.invalid/govbudget",
                       scratch_db="snap")
    assert not (tmp_path / "s").exists()


def test_with_database_overrides_a_query_parameter_dbname():
    # Fix round 1, Finding 1: a bare urlsplit/urlunsplit path swap does not
    # survive a `?dbname=...` query parameter (libpq lets the query param
    # win), so _with_database must use psycopg.conninfo.make_conninfo, which
    # overrides the dbname regardless of where it came from.
    dsn = "postgresql://127.0.0.1:55432/postgres?dbname=template1"
    scratch_dsn = proof._with_database(dsn, "govbudget_proof_x")
    assert psycopg.conninfo.conninfo_to_dict(scratch_dsn)["dbname"] == "govbudget_proof_x"


def test_resolve_dbname_follows_a_query_parameter_override():
    # Fix round 1, Finding 1: the source database must be read from the
    # resolved conninfo, not urlsplit(pg_dsn).path, which a query parameter
    # can silently contradict.
    assert proof._resolve_dbname(
        "postgresql://127.0.0.1:55432/postgres?dbname=template1") == "template1"
    with pytest.raises(ValueError, match="names no database"):
        proof._resolve_dbname("postgresql://host:5432/")


class _FakeCursor:
    def __init__(self, value):
        self._value = value

    def fetchone(self):
        return (self._value,)


class _FakeConnection:
    """Enough of a psycopg Connection for _assert_current_database: a single
    .execute(...).fetchone() round trip, no real database needed."""

    def __init__(self, value):
        self._value = value

    def execute(self, *_args, **_kwargs):
        return _FakeCursor(self._value)


def test_assert_current_database_refuses_on_mismatch():
    # Fix round 1, Finding 1: the final defense-in-depth check before any
    # destructive Postgres operation — refuse rather than touch the wrong
    # database if the connection did not land where expected.
    proof._assert_current_database(_FakeConnection("govbudget_proof_x"), "govbudget_proof_x")
    with pytest.raises(RuntimeError, match="connected to database 'govbudget'"):
        proof._assert_current_database(_FakeConnection("govbudget"), "govbudget_proof_x")


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
    for db in ("proof_src_test", "govbudget_proof_scratch_test"):
        admin.execute(f"drop database if exists {db}")
    admin.execute("create database proof_src_test")
    dsn = urlunsplit(urlsplit(ADMIN_DSN)._replace(path="/proof_src_test"))
    yield admin, dsn
    for db in ("proof_src_test", "govbudget_proof_scratch_test"):
        admin.execute(f"drop database if exists {db} with (force)")
    admin.close()


def test_a_query_dbname_override_is_resolved_and_the_scratch_dsn_still_targets_scratch(
    pg_source,
):
    # Fix round 1, Finding 1, run against the throwaway cluster only: a DSN
    # whose query parameter secretly retargets the connection to "postgres"
    # even though its path names proof_src_test — the exact libpq override
    # this fix addresses. _resolve_dbname must follow the override (not the
    # path), and the scratch DSN _with_database builds must still land on
    # the scratch database, not on whatever the query named.
    admin, src_dsn = pg_source
    sep = "&" if "?" in src_dsn else "?"
    overridden = f"{src_dsn}{sep}dbname=postgres"
    assert proof._resolve_dbname(overridden) == "postgres"
    with psycopg.connect(overridden) as con:
        assert con.execute("select current_database()").fetchone()[0] == "postgres"

    scratch_dsn = proof._with_database(overridden, "govbudget_proof_scratch_test")
    assert psycopg.conninfo.conninfo_to_dict(scratch_dsn)["dbname"] == "govbudget_proof_scratch_test"
    admin.execute("create database govbudget_proof_scratch_test")
    with psycopg.connect(scratch_dsn) as con:
        assert con.execute("select current_database()").fetchone()[0] == (
            "govbudget_proof_scratch_test")


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

    m = proof.snapshot(out, data_dir=live, pg_dsn=src_dsn, scratch_db="govbudget_proof_scratch_test")

    # _with_database now builds the scratch DSN with psycopg.conninfo.make_conninfo
    # (Fix round 1, Finding 1), which returns a keyword/value conninfo string,
    # not a URI — so the expected value is resolved semantically (the right
    # dbname, on the same host/port as ADMIN_DSN), not hand-rolled as a URI.
    scratch_dsn = m["pg"]["scratch_dsn"]
    resolved = psycopg.conninfo.conninfo_to_dict(scratch_dsn)
    admin_resolved = psycopg.conninfo.conninfo_to_dict(ADMIN_DSN)
    assert resolved["dbname"] == "govbudget_proof_scratch_test"
    assert resolved.get("host") == admin_resolved.get("host")
    assert str(resolved.get("port")) == str(admin_resolved.get("port"))
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
    with pytest.raises(FileExistsError, match="database govbudget_proof_scratch_test already exists"):
        proof.snapshot(tmp_path / "proofs" / "s1", data_dir=live, pg_dsn=src_dsn,
                       scratch_db="govbudget_proof_scratch_test")
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


# ---------------------------------------------------------------------------
# Fix round 3: numeric-text, JSON-in-string, derived hashes, reorder classes
# ---------------------------------------------------------------------------


def test_numeric_text_noise_vs_a_real_numeric_text_change(tmp_path):
    # ruling 1: a string leaf that is a strict numeral on both sides
    # compares as a number under the SAME 12-sig-digit rule as the real
    # CLEAN/NOISY float-noise pair; MOVED genuinely differs.
    _json(tmp_path / "a" / "p.json", {"recorded_value": str(CLEAN)})
    _json(tmp_path / "b" / "p.json", {"recorded_value": str(NOISY)})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["files"]["p.json"]["status"] == "equivalent"
    assert report["float_noise"] == {"files": 1, "values": 1}

    _json(tmp_path / "b" / "p.json", {"recorded_value": str(MOVED)})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert _changes(report, "p.json") == [("/recorded_value", "changed", 1)]
    assert report["float_noise"] == {"files": 0, "values": 0}


def test_json_in_string_reorder_needs_a_matching_noise_class(tmp_path):
    # ruling 2 (parse-and-recurse) + ruling 4 (reorder trust is gated).
    a_body = json.dumps({"award_ids": ["A", "B", "C"]})
    b_body = json.dumps({"award_ids": ["C", "B", "A"]})
    _json(tmp_path / "a" / "p.json", {"query_body": a_body})
    _json(tmp_path / "b" / "p.json", {"query_body": b_body})

    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert _changes(report, "p.json") == [("/query_body", "changed", 1)]
    assert not proof.is_equal(report)

    report = proof.diff_trees(tmp_path / "a", tmp_path / "b", control=True)
    assert report["files"]["p.json"]["status"] == "reordered"
    assert report["reorder_classes"] == [{"path": "p.json", "pointer": "/query_body", "count": 1}]
    assert proof.is_equal(report)

    report = proof.diff_trees(
        tmp_path / "a", tmp_path / "b",
        noise_classes=[{"path": "p.json", "pointer": "/query_body", "count": 1}],
    )
    assert report["files"]["p.json"]["status"] == "reordered"
    assert proof.is_equal(report)

    # A reorder at a class NOT in the noise file stays "changed".
    report = proof.diff_trees(
        tmp_path / "a", tmp_path / "b",
        noise_classes=[{"path": "p.json", "pointer": "/some_other_field"}],
    )
    assert _changes(report, "p.json") == [("/query_body", "changed", 1)]
    assert not proof.is_equal(report)


def test_parquet_varchar_json_reorder_is_changed_without_control_and_reordered_with_it(tmp_path):
    # ruling 2 ("in JSON files AND in parquet VARCHAR cells") + ruling 4.
    cols = [("fact_id", "varchar"), ("inputs", "varchar"), ("recorded_value", "varchar")]
    _parquet(tmp_path / "a" / "data" / "c.parquet", cols,
             [("f1", json.dumps(["x", "y", "z"]), str(CLEAN))])
    _parquet(tmp_path / "b" / "data" / "c.parquet", cols,
             [("f1", json.dumps(["z", "y", "x"]), str(NOISY))])

    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    pq = report["files"]["data/c.parquet"]
    assert (pq["status"], pq["detail"]["only_a"], pq["detail"]["only_b"]) == ("changed", 1, 1)

    report = proof.diff_trees(tmp_path / "a", tmp_path / "b", control=True)
    assert report["files"]["data/c.parquet"]["status"] == "reordered"
    assert report["reorder_classes"] == [
        {"path": "data/c.parquet", "pointer": "/inputs", "count": 1}
    ]

    report = proof.diff_trees(
        tmp_path / "a", tmp_path / "b",
        noise_classes=[{"path": "data/c.parquet", "pointer": "/inputs"}],
    )
    assert report["files"]["data/c.parquet"]["status"] == "reordered"


def test_derived_hash_is_equivalent_only_when_the_referent_is(tmp_path):
    # ruling 3: json/datasets.json's per-entry `bytes` is a derived hash of
    # data/<file> — equivalent only while that file compares equivalent.
    cols = [("x", "integer"), ("total", "double")]
    _parquet(tmp_path / "a" / "data" / "fct_x.parquet", cols, [(1, CLEAN)])
    _parquet(tmp_path / "b" / "data" / "fct_x.parquet", cols, [(1, NOISY)])
    entry = {"file": "fct_x.parquet", "name": "fct_x", "row_count": 1, "scope": "s"}
    _json(tmp_path / "a" / "json" / "datasets.json", {"datasets": [{**entry, "bytes": 100}]})
    _json(tmp_path / "b" / "json" / "datasets.json", {"datasets": [{**entry, "bytes": 142}]})

    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["files"]["data/fct_x.parquet"]["status"] == "equivalent"
    assert report["files"]["json/datasets.json"]["status"] == "equivalent"
    assert report["derived_hash"] == {"files": 1, "values": 1}
    assert proof.is_equal(report)

    # The referent now genuinely changes too: the hash difference stays.
    _parquet(tmp_path / "b" / "data" / "fct_x.parquet", cols, [(1, MOVED)])
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["files"]["data/fct_x.parquet"]["status"] == "changed"
    assert report["files"]["json/datasets.json"]["status"] == "changed"
    changes = _changes(report, "json/datasets.json")
    assert sorted(ch[1] for ch in changes) == ["added", "removed"]
    assert all(ch[0] == "/datasets/[]" for ch in changes)
    assert report["derived_hash"] == {"files": 0, "values": 0}


def test_derived_hash_audit_sha_is_equivalent_only_when_citations_is(tmp_path):
    # ruling 3: json/budget_pdf_receipts_audit.json's /citation_sha256 is a
    # derived hash of json/citations.json.
    _json(tmp_path / "a" / "json" / "citations.json", {"fid1": {"kind": "derived", "v": CLEAN}})
    _json(tmp_path / "b" / "json" / "citations.json", {"fid1": {"kind": "derived", "v": NOISY}})
    _json(tmp_path / "a" / "json" / "budget_pdf_receipts_audit.json",
          {"citation_sha256": "aaa...old"})
    _json(tmp_path / "b" / "json" / "budget_pdf_receipts_audit.json",
          {"citation_sha256": "bbb...new"})

    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["files"]["json/citations.json"]["status"] == "equivalent"
    assert report["files"]["json/budget_pdf_receipts_audit.json"]["status"] == "equivalent"
    assert report["derived_hash"] == {"files": 1, "values": 1}

    _json(tmp_path / "b" / "json" / "citations.json", {"fid1": {"kind": "derived", "v": MOVED}})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["files"]["json/citations.json"]["status"] == "changed"
    assert report["files"]["json/budget_pdf_receipts_audit.json"]["status"] == "changed"
    assert _changes(report, "json/budget_pdf_receipts_audit.json") == [
        ("/citation_sha256", "changed", 1)
    ]
    assert report["derived_hash"] == {"files": 0, "values": 0}


def test_control_fails_on_a_real_value_change(tmp_path):
    # ruling 4: --control trusts the /rows reorder but still fails overall
    # because /v is a genuine change.
    _json(tmp_path / "a" / "p.json", {"v": 1, "rows": [1, 2, 3]})
    _json(tmp_path / "b" / "p.json", {"v": 2, "rows": [3, 2, 1]})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b", control=True)
    assert not proof.is_equal(report)
    assert report["files"]["p.json"]["status"] == "changed"
    assert _changes(report, "p.json") == [("/v", "changed", 1)]
    assert report["reorder_classes"] == [{"path": "p.json", "pointer": "/rows", "count": 1}]


def test_write_noise_output_is_deterministic(tmp_path):
    _json(tmp_path / "a" / "p.json", {"rows": [1, 2, 3], "other": [4, 5, 6]})
    _json(tmp_path / "b" / "p.json", {"rows": [3, 2, 1], "other": [6, 5, 4]})
    r1 = proof.diff_trees(tmp_path / "a", tmp_path / "b", control=True)
    r2 = proof.diff_trees(tmp_path / "a", tmp_path / "b", control=True)
    assert r1["reorder_classes"] == r2["reorder_classes"] == [
        {"path": "p.json", "pointer": "/other", "count": 1},
        {"path": "p.json", "pointer": "/rows", "count": 1},
    ]


def test_control_and_noise_from_are_mutually_exclusive(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    with pytest.raises(ValueError, match="mutually exclusive"):
        proof.diff_trees(tmp_path / "a", tmp_path / "b", control=True, noise_classes=[])


def test_load_noise_classes_validates_shape(tmp_path):
    path = tmp_path / "noise.json"
    path.write_text(json.dumps([{"path": "x"}]))
    with pytest.raises(ValueError, match="needs a string"):
        proof.load_noise_classes(path)
    path.write_text(json.dumps({"not": "a list"}))
    with pytest.raises(ValueError, match="JSON list"):
        proof.load_noise_classes(path)


def test_cli_control_write_noise_and_noise_from_round_trip(tmp_path, capsys):
    a, b = tmp_path / "a", tmp_path / "b"
    _json(a / "p.json", {"rows": [1, 2, 3]})
    _json(b / "p.json", {"rows": [3, 2, 1]})
    noise_file = tmp_path / "noise.json"

    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", str(a), str(b), "--control", "--write-noise", str(noise_file)])
    assert exc.value.code == 0
    assert capsys.readouterr().out.splitlines()[-1] == "proof diff: EQUAL"
    assert json.loads(noise_file.read_text()) == [
        {"path": "p.json", "pointer": "/rows", "count": 1}
    ]

    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", str(a), str(b)])
    assert exc.value.code == 1
    assert capsys.readouterr().out.splitlines()[-1] == "proof diff: DIFFERENT"

    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", str(a), str(b), "--noise-from", str(noise_file)])
    assert exc.value.code == 0
    assert capsys.readouterr().out.splitlines()[-1] == "proof diff: EQUAL"

    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", str(a), str(b), "--write-noise", str(tmp_path / "x.json")])
    assert exc.value.code == 2

    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", str(a), str(b), "--control", "--noise-from", str(noise_file)])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# Fix round 3b: an absolute floor for float/numeric-text noise near zero
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("x, y, close", [
    (-7.450580596923828e-09, 0.0, True),    # AZ-05's real residue: -2**-27 vs 0.0
    (0.0, 0.000002, False),                 # 2e-6 > the 1e-6 floor: a real change
    (1e-7, -1e-7, True),                    # 2e-7 absolute gap, both near zero
    (1e-6, 0.0, True),                      # exactly at the floor
    (CLEAN, NOISY, True),                   # unaffected: still equal by the
    (CLEAN, MOVED, False),                  # existing 12-significant-digit rule
])
def test_float_close_has_an_absolute_floor_near_zero(x, y, close):
    assert proof._float_close(x, y) is close


def test_near_zero_float_in_a_json_list_element_is_noise(tmp_path):
    # The real AZ-05 shape: an element differs ONLY in one near-zero float,
    # everything else (including the pe_bli-style string) identical.
    entry = {"award_count": 1, "fiscal_year": 2025, "pe_bli": "0604874C",
             "positive_obligation": 122223512.03999999, "recipient_count": 1,
             "transaction_count": 4}
    _json(tmp_path / "a" / "p.json",
          {"by_year_programs": [{**entry, "total_obligation": -7.450580596923828e-09}]})
    _json(tmp_path / "b" / "p.json",
          {"by_year_programs": [{**entry, "total_obligation": 0.0}]})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["files"]["p.json"]["status"] == "equivalent"
    assert report["float_noise"]["values"] >= 1
    assert proof.is_equal(report)

    # A genuine 2e-6 change in the same position is still "changed".
    _json(tmp_path / "b" / "p.json",
          {"by_year_programs": [{**entry, "total_obligation": 0.000002}]})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["files"]["p.json"]["status"] == "changed"
    assert not proof.is_equal(report)


@pytest.mark.parametrize("typ, va, vb", [
    ("bigint", 1, 2),
    ("decimal(10,6)", decimal.Decimal("0.000001"), decimal.Decimal("0.000003")),
    ("varchar", "ABC", "ABD"),
])
def test_absolute_floor_does_not_affect_integers_decimals_or_strings(tmp_path, typ, va, vb):
    # The floor applies only where the float rule already applies (DOUBLE/
    # FLOAT and numeric text); an integer, decimal or plain string a mere
    # 1e-6 (or less) apart by VALUE is still an exact, reported change.
    cols = [("state", "varchar"), ("v", typ)]
    _parquet(tmp_path / "a" / "data" / "t.parquet", cols, [("NY", va)])
    _parquet(tmp_path / "b" / "data" / "t.parquet", cols, [("NY", vb)])
    pq = proof.diff_trees(tmp_path / "a", tmp_path / "b")["files"]["data/t.parquet"]
    assert (pq["status"], pq["detail"]["only_a"], pq["detail"]["only_b"]) == ("changed", 1, 1)
