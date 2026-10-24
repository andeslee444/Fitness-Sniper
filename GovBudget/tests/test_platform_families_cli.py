"""`govbudget platform-families …` (families piece 2; spec §8.3, §9.2, Review Focus 5).

Task 7a: `check`. Tasks 7b–7d append propose, render, answer, ratify and preview.
The lake is stubbed through module attributes (reg.open_lake, reg.check_lake).
"""
from __future__ import annotations

import datetime
import json
from types import SimpleNamespace

import duckdb
import pytest

from govbudget import cli, config
from govbudget import platform_families as reg
import govbudget.verify_families as vf
from platform_families_helpers import DRAFT_F35, MSAR, FakeLake, add_family, f15_registry

LOCK = 'IO Error: Could not set lock on file "/x/govbudget.duckdb": Conflicting lock is held in /usr/bin/python3 (PID 1)'


def _exit(argv) -> int:
    with pytest.raises(SystemExit) as exit_:
        cli.main(argv)
    return exit_.value.code


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    paths = f15_registry(tmp_path)
    add_family(paths, DRAFT_F35, sources=[MSAR])
    env = SimpleNamespace(paths=paths, tmp_path=tmp_path, report=reg.LakeReport([], [], []), lakes=[])
    monkeypatch.setattr(reg, "DEFAULT_PATHS", paths)
    monkeypatch.setattr(reg, "REVIEW_ROOT", tmp_path / "research")

    def open_lake(path):
        env.lakes.append(FakeLake())
        return env.lakes[-1]

    monkeypatch.setattr(reg, "open_lake", open_lake)
    monkeypatch.setattr(reg, "check_lake", lambda registry, **kw: env.report)
    # Without it, a run at :15-:20 against the default --duckdb would trip the SAM guard.
    monkeypatch.setattr(vf, "_now", lambda: datetime.datetime(2026, 10, 21, 1, 30))
    return env


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def test_check_prints_failures_undecided_and_stale(cli_env, capsys):
    cli_env.report = reg.LakeReport(failures=[], undecided=["f-35: 2026/JSM000 matches the review guard"],
                                    stale=["f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved"])
    code = _exit(["platform-families", "check"])
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert "  undecided f-35: 2026/JSM000 matches the review guard" in out
    assert "  stale f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved" in out
    assert out[-1] == "platform-families check: families=2 failures=0 undecided=1 stale=1"
    assert [lake.closed for lake in cli_env.lakes] == [True]


@pytest.mark.parametrize("which", ["undecided", "stale"])
def test_check_strict_exits_1_on_undecided_or_stale(cli_env, capsys, which):
    cli_env.report = reg.LakeReport(failures=[], undecided=[], stale=[])
    getattr(cli_env.report, which).append("f-35: 2026/JSM000 matches the review guard")
    assert _exit(["platform-families", "check"]) == 0
    assert _exit(["platform-families", "check", "--strict"]) == 1
    assert capsys.readouterr().out.splitlines()[-1].startswith("platform-families check: families=2 failures=0")


def test_check_exits_1_on_a_lake_failure(cli_env, capsys):
    cli_env.report = reg.LakeReport(failures=["f-15: P-1 2026/F01500 title 'F-15X' differs from titles_seen 'F-15'"],
                                    undecided=[], stale=[])
    assert _exit(["platform-families", "check"]) == 1
    out = capsys.readouterr().out.splitlines()
    assert "  FAIL f-15: P-1 2026/F01500 title 'F-15X' differs from titles_seen 'F-15'" in out
    assert out[-1] == "platform-families check: families=2 failures=1 undecided=0 stale=0"


def test_check_exits_1_on_a_stage_1_error_naming_the_file(cli_env, capsys):
    doc = json.loads(cli_env.paths.json.read_text(encoding="utf-8"))
    doc["schema_version"] = 2
    cli_env.paths.json.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    assert _exit(["platform-families", "check"]) == 1
    out = capsys.readouterr().out.splitlines()
    n = len(out) - 1
    assert n >= 1
    assert all(line.startswith("platform-families: ") and "platform_families.json" in line for line in out[:-1])
    assert out[-1] == f"platform-families check: stage 1 failed ({n} error(s))"
    assert cli_env.lakes == []


def test_check_reports_a_duckdb_lock_as_exit_2(cli_env, monkeypatch, capsys):   # Review Focus 5
    def locked(path):
        raise duckdb.IOException(LOCK)
    monkeypatch.setattr(reg, "open_lake", locked)
    assert _exit(["platform-families", "check"]) == 2
    out, err = capsys.readouterr()
    assert err.strip() == f"platform-families check: ERROR — {LOCK}"
    assert "platform-families check: families=" not in out


def test_check_refuses_the_live_lake_across_the_sam_window(cli_env, monkeypatch, capsys):
    live = cli_env.tmp_path / "govbudget.duckdb"
    live.touch()
    monkeypatch.setattr(config, "DUCKDB_PATH", live)
    monkeypatch.setattr(vf, "_now", lambda: datetime.datetime(2026, 10, 21, 1, 17))
    assert _exit(["platform-families", "check"]) == 2
    out, err = capsys.readouterr()
    assert "SAM window" in err
    assert "platform-families check: families=" not in out
    assert cli_env.lakes == []
