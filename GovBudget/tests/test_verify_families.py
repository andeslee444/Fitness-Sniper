"""verify-families: the families piece 2 release gate (spec §13; D9, Review Focus 5).

All lake access is stubbed. The suite calls I-REG through module attributes
(reg.open_lake, reg.check_lake, reg.check_citations), so monkeypatch.setattr(reg, …)
reaches every caller.
"""
from __future__ import annotations

import datetime
import json

import duckdb
import pytest

from govbudget import cli, config
from govbudget import platform_families as reg
import govbudget.verify_families as vf
from govbudget.platform_family_history import _json_bytes
from platform_families_helpers import DRAFT_F35, MSAR, FakeLake, add_family, f15_registry, site_tree

LOCK = 'IO Error: Could not set lock on file "/x/govbudget.duckdb": Conflicting lock is held in /usr/bin/python3 (PID 1)'
ANNUAL_F15 = ("sum(budget_lines.amount_thousands) for reviewed F-15 members, PB2026, FY2024 actuals; "
              "one selected scenario column per workbook line")
FID = "0" * 16
CIT = {"kind": "derived", "formula": ANNUAL_F15, "inputs": "[]", "recorded_value": "0"}


@pytest.fixture
def paths(tmp_path):
    paths = f15_registry(tmp_path)
    add_family(paths, DRAFT_F35, sources=[MSAR])
    return paths


@pytest.fixture
def registry(paths):
    return reg.load_registry(paths)


# ---------------------------------------------------------------------------
# Leg a: the registry files (stage 1)
# ---------------------------------------------------------------------------


def test_leg_a_passes_on_the_f15_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "DEFAULT_PATHS", f15_registry(tmp_path))
    out = vf.run_verify_families(site_dir=tmp_path, duckdb_path=tmp_path / "x.duckdb", legs="a")
    assert out == {"legs": {"a": {"ok": True, "failures": [],
                   "summary": "families=1 published=1 member_rows=8 era_lines=31 rulings=1"}}, "verdict": "PASS"}


def test_leg_a_failure_names_the_file_and_blocks_legs_b_and_c(paths, tmp_path, monkeypatch):
    doc = json.loads(paths.json.read_text(encoding="utf-8"))
    doc["schema_version"] = 2
    paths.json.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(reg, "DEFAULT_PATHS", paths)
    monkeypatch.setattr(reg, "open_lake", lambda p: pytest.fail("leg b opened the lake"))
    out = vf.run_verify_families(site_dir=tmp_path, duckdb_path=tmp_path / "x.duckdb", legs="abc")
    a = out["legs"]["a"]
    assert not a["ok"] and a["failures"][0].startswith("platform-families: ") and "platform_families.json" in a["failures"][0]
    for leg in "bc":
        assert out["legs"][leg] == {"ok": False, "summary": "registry unreadable",
                                    "failures": [f"stage 1 failed (leg a): {len(a['failures'])} error(s)"]}
    assert out["verdict"] == "FAIL"


# ---------------------------------------------------------------------------
# Leg b: stage 2 against the lake (read-only)
# ---------------------------------------------------------------------------


def test_leg_b_reports_draft_guard_matches_as_undecided_not_failures(registry, monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(reg, "open_lake", lambda p: FakeLake())
    monkeypatch.setattr(reg, "check_lake", lambda r, **kw: seen.update(kw) or reg.LakeReport(
        failures=[], undecided=["f-35: 2026/JSM000 matches the review guard"], stale=[]))
    leg = vf.run_verify_families(site_dir=tmp_path, duckdb_path=tmp_path / "fam2.duckdb", legs="b", registry=registry)["legs"]["b"]
    assert leg == {"ok": True, "summary": "families=2 failures=0 undecided=1 stale=0", "failures": []}
    assert seen.get("families") is None  # stage 2 for every family, draft included


@pytest.mark.parametrize("report,line", [
    (dict(failures=["f-15: P-1 2026/F01500 title 'F-15X' differs from titles_seen 'F-15'"], undecided=[], stale=[]),
     "f-15: P-1 2026/F01500 title 'F-15X' differs from titles_seen 'F-15'"),
    (dict(failures=[], undecided=[], stale=["f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved"]),
     "stale f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved")])
def test_leg_b_fails_on_a_lake_failure_or_a_stale_row(registry, monkeypatch, tmp_path, report, line):
    lake = FakeLake()
    monkeypatch.setattr(reg, "open_lake", lambda p: lake)
    monkeypatch.setattr(reg, "check_lake", lambda r, **kw: reg.LakeReport(**report))
    out = vf.run_verify_families(site_dir=tmp_path, duckdb_path=tmp_path / "fam2.duckdb", legs="b", registry=registry)
    leg = out["legs"]["b"]
    assert not leg["ok"] and line in leg["failures"]
    assert out["verdict"] == "FAIL" and lake.closed


def test_verify_families_leg_b_lock_is_error_not_fail(registry, paths, tmp_path, monkeypatch, capsys):  # Review Focus 5
    def locked(path):
        raise duckdb.IOException(LOCK)
    monkeypatch.setattr(reg, "open_lake", locked)
    monkeypatch.setattr(vf, "_now", lambda: datetime.datetime(2026, 10, 21, 1, 30))
    with pytest.raises(duckdb.IOException):
        vf.run_verify_families(site_dir=tmp_path, duckdb_path=tmp_path / "x.duckdb", legs="b", registry=registry)
    monkeypatch.setattr(reg, "DEFAULT_PATHS", paths)
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-families", "--legs", "b"])
    out = capsys.readouterr().out.splitlines()
    assert exit_.value.code == 2
    assert out[-1] == f"verify-families: ERROR — {LOCK}"
    assert "verify-families: FAIL" not in out


def test_legs_b_and_c_refuse_the_live_lake_across_the_sam_window(registry, monkeypatch, tmp_path):
    live = tmp_path / "govbudget.duckdb"
    live.touch()
    monkeypatch.setattr(config, "DUCKDB_PATH", live)
    monkeypatch.setattr(vf, "_now", lambda: datetime.datetime(2026, 10, 21, 1, 17))
    monkeypatch.setattr(reg, "open_lake", lambda p: FakeLake())
    monkeypatch.setattr(reg, "check_lake", lambda r, **kw: reg.LakeReport([], [], []))
    with pytest.raises(RuntimeError, match="SAM window"):
        vf.run_verify_families(site_dir=tmp_path, duckdb_path=live, legs="b", registry=registry)
    snap = tmp_path / "fam2.duckdb"   # not the live lake: never guarded
    assert vf.run_verify_families(site_dir=tmp_path, duckdb_path=snap, legs="b", registry=registry)["verdict"] == "PASS"
    clone = tmp_path / "fam2-B" / "duckdb" / "govbudget.duckdb"   # config.DUCKDB_PATH inside a proof snapshot tree (R16)
    clone.parent.mkdir(parents=True)
    clone.touch()
    (tmp_path / "fam2-B" / "snapshot.json").write_text("{}")
    monkeypatch.setattr(config, "DUCKDB_PATH", clone)
    assert vf.run_verify_families(site_dir=tmp_path, duckdb_path=clone, legs="b", registry=registry)["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# Leg c: stage 3, the index projection and the leak scan against the export
# ---------------------------------------------------------------------------


class _Recorder:
    def __init__(self):
        self.calls = []
        self.returns = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return list(self.returns)


@pytest.fixture
def recorder(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(reg, "check_citations", rec)
    return rec


@pytest.fixture
def export_site(tmp_path, registry, recorder, monkeypatch):
    site = site_tree(tmp_path, formulas=[ANNUAL_F15], citations={FID: CIT})
    (site / "json" / "families").mkdir()
    (site / "json" / "families" / "index.json").write_bytes(_json_bytes(reg.index_projection(registry)))
    history = {"family_id": "f-15", "programs": [{"id": m.member_id} for m in registry["f-15"].counted],
               "points": [], "cumulative": {"fact_id": FID}}
    (site / "json" / "f15_funding_history.json").write_text(json.dumps(history) + "\n", encoding="utf-8")
    monkeypatch.setattr(vf, "_program_identity", lambda p: object())
    return site


def test_leg_c_passes_on_the_projection_and_a_matching_history(export_site, registry, recorder, tmp_path):
    leg = vf.run_verify_families(site_dir=export_site, duckdb_path=tmp_path / "fam2.duckdb", legs="c",
                                 registry=registry)["legs"]["c"]
    assert leg == {"ok": True, "failures": [], "summary": "published=1 histories=1 stage3=0 leaks=0 files_scanned=4"
                   " (stage-3 item 6, citation identity, runs only at export)"}
    (family,), kw = recorder.calls[0]
    assert family.platform_family == "f-15" and kw["minted"] == {FID: CIT} and kw["registry"] is registry


def _damage(site, how, recorder):
    index = site / "json" / "families" / "index.json"
    history = site / "json" / "f15_funding_history.json"
    if how == "rm index":
        index.unlink()
    elif how == "index +space":
        index.write_bytes(index.read_bytes() + b" ")
    elif how == "rm history":
        history.unlink()
    elif how == "stage 3":
        recorder.returns = ["f-15 program note receipt mismatch: e7d5bcfb4a30f458"]
    else:
        payload = json.loads(history.read_text(encoding="utf-8"))
        if how == "family_id f-16":
            payload["family_id"] = "f-16"
        else:  # programs reversed
            payload["programs"].reverse()
        history.write_text(json.dumps(payload) + "\n", encoding="utf-8")


@pytest.mark.parametrize("damage,failure", [
    ("rm index", "json/families/index.json is missing"),
    ("index +space", "json/families/index.json differs from index_projection(registry)"),
    ("rm history", "f-15: json/f15_funding_history.json is missing"),
    ("family_id f-16", "f-15: json/f15_funding_history.json family_id is 'f-16', not 'f-15'"),
    ("programs reversed", "f-15: json/f15_funding_history.json programs[].id differ from the counted members in member_order"),
    ("stage 3", "f-15: f-15 program note receipt mismatch: e7d5bcfb4a30f458")])
def test_leg_c_fails_when_the_index_history_or_stage_3_disagrees(export_site, registry, recorder, tmp_path,
                                                                  damage, failure):
    _damage(export_site, damage, recorder)
    out = vf.run_verify_families(site_dir=export_site, duckdb_path=tmp_path / "fam2.duckdb", legs="c",
                                 registry=registry)
    leg = out["legs"]["c"]
    assert not leg["ok"] and failure in leg["failures"]
    assert out["verdict"] == "FAIL"


@pytest.mark.parametrize("plant,failure", [
    (("json/search_quick.json", '{"d":"f35_funding_history"}'), "leak: 'f35_funding_history' of unpublished f-35 in json/search_quick.json"),
    (("json/f35_funding_history.json", "{}"), "leak: json/f35_funding_history.json of unpublished f-35 exists"),
    (("json/breakdowns/x.json", '{"k":"f-35|2017|2015"}'), "leak: 'f-35|' of unpublished f-35 in json/breakdowns/x.json"),
    ("formula: sum(budget_lines.amount_thousands) for reviewed F-35 members, PB2026, FY2024 actuals",
     "leak: 'reviewed F-35 members' of unpublished f-35 in citations/citations.parquet (1 row(s))")])
def test_leak_scan_finds_each_needle_of_an_unpublished_family(tmp_path, registry, plant, failure):
    if isinstance(plant, str):
        site = site_tree(tmp_path, formulas=[ANNUAL_F15, plant.removeprefix("formula: ")])
    else:
        site = site_tree(tmp_path, formulas=[ANNUAL_F15])
        relative, text = plant
        (site / relative).parent.mkdir(parents=True, exist_ok=True)
        (site / relative).write_text(text, encoding="utf-8")
    failures, scanned = vf.scan_leaks(site, registry)
    assert failure in failures
    assert scanned == len(list(site.rglob("*.json")))


def test_leak_scan_control_fails_when_no_formula_names_a_published_family(tmp_path, registry):
    failures, _ = vf.scan_leaks(site_tree(tmp_path), registry)
    assert failures == ["leak scan control: no citations/citations.parquet formula contains 'reviewed F-15 members'"]


# ---------------------------------------------------------------------------
# The CLI
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("verdict,code", [("PASS", 0), ("FAIL", 1)])
def test_cli_prints_legs_then_one_verdict_line(monkeypatch, capsys, verdict, code):
    calls = []
    canned = {"legs": {"a": {"ok": verdict == "PASS", "summary": "families=1 published=1 member_rows=8 era_lines=31 rulings=1",
                             "failures": [] if verdict == "PASS" else ["platform-families: x: y"]}}, "verdict": verdict}
    monkeypatch.setattr(vf, "run_verify_families", lambda **kw: calls.append(kw) or canned)
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-families"])
    out = capsys.readouterr().out.splitlines()
    assert exit_.value.code == code and out[-1] == f"verify-families: {verdict}"
    assert out[0] == f"leg a registry: families=1 published=1 member_rows=8 era_lines=31 rulings=1 → {verdict}"
    assert calls == [{"site_dir": config.SITE_DIR, "duckdb_path": config.DUCKDB_PATH, "legs": "abc"}]


def test_cli_refuses_unknown_legs_with_exit_2(capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-families", "--legs", "az"])
    assert exit_.value.code == 2
    assert capsys.readouterr().out.splitlines()[-1] == "verify-families: ERROR — legs must be letters from abc; got 'az'"
