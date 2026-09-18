"""ROADMAP #8 — the `govbudget refresh` stage graph.

Everything here runs against a FAKE stage runner. The orchestrator's only two
doors to the outside world are refresh._run (fire-and-forget) and
refresh._capture (stdout needed), both module-level for exactly this reason.
No test in this file may start a subprocess, open a socket, touch Postgres,
open the DuckDB lake, or read or write outside tmp_path.
"""
import datetime as dt
import fcntl
import io
import json
import shutil as _shutil
import subprocess
import sys
from pathlib import Path

import pytest

from govbudget import config, refresh

ROOT = Path("/fake/repo")
NOW = dt.datetime(2026, 9, 10, 3, 0, tzinfo=dt.UTC)


def _manifest(tmp_path, entries):
    p = tmp_path / "manifest.jsonl"
    p.write_text("".join(json.dumps(e) + "\n" for e in entries))
    return p


@pytest.fixture
def calls(monkeypatch, tmp_path):
    """Record every stage invocation; run nothing. Preflight forced green.

    MANIFEST_PATH is pointed at a (by default non-existent) tmp file so no run
    test reads the real lake manifest.
    """
    recorded: list[dict] = []

    def fake_run(argv, *, cwd=None, env=None):
        recorded.append({"argv": list(argv), "cwd": str(cwd) if cwd else None,
                         "env": dict(env or {})})
        return 0

    monkeypatch.setattr(refresh, "_run", fake_run)
    monkeypatch.setattr(refresh, "preflight", lambda **kw: [])
    monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "manifest.jsonl")
    return recorded


def _refresh(tmp_path, **kw):
    kw.setdefault("root", ROOT)
    kw.setdefault("now", NOW)
    kw.setdefault("assume_yes", True)
    kw.setdefault("state_path", tmp_path / "refresh" / "last_run.json")
    return refresh.run_refresh(**kw)


def _names(record, status):
    return [s["name"] for s in record["stages"] if s["status"] == status]


def _stub_deploy_script(root):
    """preflight requires scripts/launch/deploy.sh to exist under root."""
    p = root / "scripts" / "launch" / "deploy.sh"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("#!/usr/bin/env bash\n")
    return p


# ── the stage graph ─────────────────────────────────────────────────────────


def test_stage_order_is_the_launch_md_canonical_order():
    assert refresh.STAGE_NAMES == (
        "preflight",
        "sync-archive",
        "sync-subawards",
        "sync-fiscaldata",
        "influence-pull",
        "fixtures",
        "export-facts",
        "build",
        "export-site",
        "site-build",
        "site-verify",
        "deploy",
    )
    i = refresh.STAGE_NAMES.index
    # LAUNCH.md Step 0: export-facts -> build -> export-site. The mart reads the
    # parquet export-facts writes (dbt/models/sources.yml:20-36); inverting
    # these two makes export-site fail on the announcement-source check.
    assert i("export-facts") < i("build") < i("export-site")
    # deploy.sh owns assets-then-pages-then-live-check, so it is one stage, last.
    assert refresh.STAGE_NAMES[-1] == "deploy"


def test_every_stage_argv_cwd_and_env_is_pinned_exactly():
    """The orchestrator's whole job is typing these twelve command lines
    correctly, so every one is pinned in full. An argv[0]-only spot check let
    `export-sites` or `jbooks export-fact` ship green."""
    gb = [sys.executable, "-m", "govbudget"]
    site_env = {"NEXT_PUBLIC_SITE_URL": "https://fiscalreceipts.com"}
    expected = {
        "preflight": ([], None, {}),
        "sync-archive": (gb + ["sync-archive"], None, {}),
        "sync-subawards": (gb + ["sync-subawards", "--fy", "2026"], None, {}),
        "sync-fiscaldata": (gb + ["sync-fiscaldata"], None, {}),
        "influence-pull": (
            gb + ["influence", "pull", "--years", "2024,2025,2026"], None, {}),
        "fixtures": (
            [sys.executable, "-m", "pytest", "-q", "tests/influence",
             "tests/jbooks", "tests/oversight", "tests/states"], ROOT, {}),
        "export-facts": (gb + ["jbooks", "export-facts"], None, {}),
        "build": (gb + ["build"], None, {}),
        "export-site": (gb + ["export-site"], None, {}),
        "site-build": (["npm", "run", "build"], ROOT / "site", site_env),
        "site-verify": (["npm", "run", "verify"], ROOT / "site", site_env),
        "deploy": ([str(ROOT / "scripts" / "launch" / "deploy.sh")], None, {}),
    }
    stages = refresh.build_stages(ROOT, NOW)
    assert [s.name for s in stages] == list(refresh.STAGE_NAMES)
    allowed_first = {sys.executable, "npm",
                     str(ROOT / "scripts" / "launch" / "deploy.sh")}
    for s in stages:
        assert (s.argv, s.cwd, s.env) == expected[s.name], s.name
        if s.argv:
            assert s.argv[0] in allowed_first, s.name


def test_deploy_stage_uses_the_absolute_deploy_script():
    stage = {s.name: s for s in refresh.build_stages(ROOT, NOW)}["deploy"]
    assert stage.argv == [str(ROOT / "scripts" / "launch" / "deploy.sh")]
    assert Path(stage.argv[0]).is_absolute()


def test_site_stages_carry_the_production_origin_and_run_in_site():
    stages = {s.name: s for s in refresh.build_stages(ROOT, NOW)}
    for name, script in (("site-build", "build"), ("site-verify", "verify")):
        s = stages[name]
        assert s.argv == ["npm", "run", script]
        assert s.cwd == ROOT / "site"
        assert s.env["NEXT_PUBLIC_SITE_URL"] == "https://fiscalreceipts.com"


def test_subawards_stage_targets_the_current_federal_fiscal_year():
    # 2026-09-10 is still FY2026 (FY N runs Oct 1 N-1 .. Sep 30 N).
    stages = {s.name: s for s in refresh.build_stages(ROOT, NOW)}
    assert stages["sync-subawards"].argv[-2:] == ["--fy", "2026"]
    # 2026-10-01 is FY2027, but config.FY_END clamps it.
    later = {s.name: s for s in refresh.build_stages(
        ROOT, dt.datetime(2026, 10, 1, tzinfo=dt.UTC))}
    assert later["sync-subawards"].argv[-1] == str(config.FY_END)


def test_the_lda_pull_window_tracks_the_clock(tmp_path):
    """The CLI default is a hardcoded `2024,2025,2026`; a loaded quarterly job
    inheriting it would stop covering the current filing year after 2026 and
    say nothing (LDA ingests write no manifest record, so neither drift alarm
    can see it). The stage passes the window explicitly instead."""
    def window(when):
        argv = {s.name: s for s in refresh.build_stages(ROOT, when)}[
            "influence-pull"].argv
        return argv[argv.index("--years") + 1]

    assert window(NOW) == "2024,2025,2026"
    assert window(dt.datetime(2027, 3, 1, tzinfo=dt.UTC)) == "2025,2026,2027"
    assert window(dt.datetime(2031, 12, 31, tzinfo=dt.UTC)) == "2029,2030,2031"


def test_syncs_never_carry_allow_corpus_shrink():
    """The unattended path must be the safe one (Task 20a)."""
    for stage in refresh.build_stages(ROOT, NOW):
        assert "--allow-corpus-shrink" not in stage.argv


def test_fixtures_stage_runs_the_committed_golden_suites_before_anything_derived():
    stages = {s.name: s for s in refresh.build_stages(ROOT, NOW)}
    argv = stages["fixtures"].argv
    assert argv[:3] == [sys.executable, "-m", "pytest"]
    assert set(argv[-4:]) == {
        "tests/influence", "tests/jbooks", "tests/oversight", "tests/states"
    }
    assert stages["fixtures"].cwd == ROOT
    i = refresh.STAGE_NAMES.index
    assert i("sync-fiscaldata") < i("fixtures") < i("export-facts")


# ── execution ───────────────────────────────────────────────────────────────


def test_happy_path_runs_every_monthly_stage_in_order(tmp_path, calls):
    record = _refresh(tmp_path)
    assert record["ok"] is True
    assert _names(record, "ok") == [
        "preflight", "sync-archive", "sync-subawards", "sync-fiscaldata",
        "fixtures", "export-facts", "build", "export-site",
        "site-build", "site-verify", "deploy",
    ]
    assert _names(record, "skipped-cadence") == ["influence-pull"]
    assert len(calls) == 10  # preflight is in-process, not a subprocess


def test_only_the_site_stages_reach_the_runner_with_the_production_origin(
    tmp_path, calls
):
    """Asserted on what reaches `_run`, not on the Stage dataclass: dropping
    `env=stage.env` from the call site would bake the placeholder origin into
    the production build and no dataclass assertion would notice."""
    _refresh(tmp_path)
    site = [c for c in calls if c["argv"][0] == "npm"]
    assert [c["argv"] for c in site] == [["npm", "run", "build"],
                                         ["npm", "run", "verify"]]
    for c in site:
        assert c["env"] == {"NEXT_PUBLIC_SITE_URL": "https://fiscalreceipts.com"}
        assert c["cwd"] == str(ROOT / "site")
    for c in calls:
        if c["argv"][0] != "npm":
            assert c["env"] == {}, c["argv"]


def test_quarterly_flag_adds_the_influence_pull(tmp_path, calls):
    record = _refresh(tmp_path, quarterly=True)
    assert "influence-pull" in _names(record, "ok")
    assert any(
        c["argv"][-4:] == ["influence", "pull", "--years", "2024,2025,2026"]
        for c in calls
    )


def test_dry_run_executes_nothing_and_writes_no_state(tmp_path, calls):
    state = tmp_path / "refresh" / "last_run.json"
    record = _refresh(tmp_path, dry_run=True)
    assert calls == []
    assert not state.exists()
    assert {s["status"] for s in record["stages"]} <= {"dry-run", "skipped-cadence"}


def test_until_stops_after_the_named_stage(tmp_path, calls):
    record = _refresh(tmp_path, until_stage="export-site")
    assert _names(record, "ok")[-1] == "export-site"
    assert not any(c["argv"][0] == "npm" for c in calls)
    assert not any("deploy.sh" in c["argv"][0] for c in calls)


def test_from_resumes_at_the_named_stage(tmp_path, calls):
    record = _refresh(tmp_path, from_stage="build")
    assert [s["name"] for s in record["stages"]] == [
        "build", "export-site", "site-build", "site-verify", "deploy"
    ]
    assert not any("sync-archive" in " ".join(c["argv"]) for c in calls)


def test_unknown_stage_name_names_the_valid_ones(tmp_path, calls):
    with pytest.raises(ValueError) as exc:
        _refresh(tmp_path, from_stage="synk-archive")
    assert "synk-archive" in str(exc.value)
    assert "sync-archive" in str(exc.value)


def test_from_after_until_is_refused(tmp_path, calls):
    with pytest.raises(ValueError):
        _refresh(tmp_path, from_stage="deploy", until_stage="build")


def test_first_failure_aborts_and_later_stages_are_not_run(tmp_path, monkeypatch):
    recorded = []

    def fake_run(argv, *, cwd=None, env=None):
        recorded.append(list(argv))
        # the dbt stage only — `npm run build` also ends in "build"
        return 1 if argv[0] != "npm" and argv[-1] == "build" else 0

    monkeypatch.setattr(refresh, "_run", fake_run)
    monkeypatch.setattr(refresh, "preflight", lambda **kw: [])
    monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "manifest.jsonl")
    state = tmp_path / "refresh" / "last_run.json"
    record = _refresh(tmp_path, state_path=state)

    assert record["ok"] is False
    assert record["failed_stage"] == "build"
    by_name = {s["name"]: s for s in record["stages"]}
    assert by_name["build"]["status"] == "failed"
    assert by_name["build"]["returncode"] == 1
    assert by_name["export-site"]["status"] == "not-run"
    assert by_name["deploy"]["status"] == "not-run"
    assert not any("npm" in a for a in recorded)
    # The alarm file is written EXACTLY when it matters.
    assert json.loads(state.read_text())["failed_stage"] == "build"


def _previous_ok_record(tmp_path):
    """A last_run.json from a previous, successful run."""
    state = tmp_path / "refresh" / "last_run.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"ok": True, "failed_stage": None}) + "\n")
    return state


def _raising_runner(monkeypatch, tmp_path, exc):
    def boom(argv, *, cwd=None, env=None):
        raise exc

    monkeypatch.setattr(refresh, "_run", boom)
    monkeypatch.setattr(refresh, "preflight", lambda **kw: [])
    monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "manifest.jsonl")


def test_an_exec_level_failure_overwrites_the_previous_runs_ok(
    tmp_path, monkeypatch
):
    """A missing binary raises out of subprocess.run rather than returning a
    non-zero code. Without a finally the record is never rewritten and
    last_run.json keeps the PREVIOUS run's `"ok": true` — the one file the
    operator is told to read would be lying."""
    state = _previous_ok_record(tmp_path)
    _raising_runner(monkeypatch, tmp_path,
                    FileNotFoundError(2, "No such file or directory: 'uv'"))
    with pytest.raises(FileNotFoundError):
        _refresh(tmp_path, state_path=state)
    rec = json.loads(state.read_text())
    assert rec["ok"] is False
    assert rec["failed_stage"] == "sync-archive"
    assert "FileNotFoundError" in rec["error"]
    assert "uv" in rec["error"]
    assert rec["ended_at"]


def test_a_ctrl_c_overwrites_the_previous_runs_ok(tmp_path, monkeypatch):
    state = _previous_ok_record(tmp_path)
    _raising_runner(monkeypatch, tmp_path, KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        _refresh(tmp_path, state_path=state)
    rec = json.loads(state.read_text())
    assert rec["ok"] is False
    assert rec["failed_stage"] == "sync-archive"
    assert "KeyboardInterrupt" in rec["error"]


def test_a_clean_run_records_no_error(tmp_path, calls):
    assert _refresh(tmp_path)["error"] is None


def test_preflight_failure_aborts_before_any_stage(tmp_path, monkeypatch):
    recorded = []
    monkeypatch.setattr(
        refresh, "_run",
        lambda argv, **kw: (recorded.append(list(argv)), 0)[1],
    )
    monkeypatch.setattr(
        refresh, "preflight",
        lambda **kw: ["postgres: cannot connect to postgresql://localhost/govbudget"],
    )
    monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "manifest.jsonl")
    record = _refresh(tmp_path)
    assert record["ok"] is False
    assert record["failed_stage"] == "preflight"
    assert "postgres" in record["stages"][0]["detail"]
    assert recorded == []


def test_no_tty_without_yes_refuses_to_start(tmp_path, calls, monkeypatch):
    # io.StringIO().isatty() is False — deterministic under any capture mode.
    monkeypatch.setattr(refresh.sys, "stdin", io.StringIO())
    with pytest.raises(refresh.RefreshAborted) as exc:
        _refresh(tmp_path, assume_yes=False)
    assert "--yes" in str(exc.value)
    assert calls == []


def test_a_second_instance_refuses_to_start_while_the_lock_is_held(
    tmp_path, calls
):
    """The monthly and quarterly launchd labels are different labels, so
    launchd's same-label suppression does not keep them apart; an overrunning
    monthly joined by the quarterly would write the same parquet partitions."""
    state = tmp_path / "refresh" / "last_run.json"
    lock_path = state.parent / ".lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    held = lock_path.open("w")
    fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(refresh.RefreshAborted) as exc:
            _refresh(tmp_path, state_path=state)
    finally:
        held.close()
    assert str(lock_path) in str(exc.value)
    assert calls == []
    # The RUNNING instance's record must not be clobbered by the refusal.
    assert not state.exists()


def test_the_lock_is_released_when_a_run_ends(tmp_path, calls):
    _refresh(tmp_path)
    _refresh(tmp_path)   # a second run after the first finished is fine
    assert (tmp_path / "refresh" / ".lock").exists()


def test_preflight_skips_deploy_credentials_when_deploy_is_not_planned(
    tmp_path, monkeypatch
):
    seen = {}
    monkeypatch.setattr(refresh, "_run", lambda argv, **kw: 0)
    monkeypatch.setattr(refresh, "preflight", lambda **kw: (seen.update(kw), [])[1])
    monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "manifest.jsonl")
    _refresh(tmp_path, until_stage="export-site")
    assert seen["require_deploy"] is False
    seen.clear()
    _refresh(tmp_path)
    assert seen["require_deploy"] is True


# ── preflight itself ────────────────────────────────────────────────────────


@pytest.fixture
def local_checks_green(monkeypatch, tmp_path):
    monkeypatch.setattr(refresh, "_check_disk", lambda: None)
    monkeypatch.setattr(refresh, "_check_postgres", lambda: None)
    monkeypatch.setattr(refresh, "_check_duckdb", lambda: None)
    monkeypatch.setattr(_shutil, "which", lambda name: f"/usr/bin/{name}")
    (tmp_path / "logs").mkdir(exist_ok=True)


def test_preflight_reports_a_missing_rclone_remote(tmp_path, monkeypatch, local_checks_green):
    _stub_deploy_script(tmp_path)
    monkeypatch.setattr(
        refresh, "_capture",
        lambda argv: (0, "gdrive:\n") if argv[0] == "rclone" else (0, "andes\n"),
    )
    failures = refresh.preflight(root=tmp_path, require_deploy=True)
    assert len(failures) == 1
    assert "rclone" in failures[0] and "r2" in failures[0]


def test_preflight_reports_a_missing_deploy_script(tmp_path, monkeypatch, local_checks_green):
    monkeypatch.setattr(refresh, "_capture", lambda argv: (0, "r2:\n"))
    failures = refresh.preflight(root=tmp_path, require_deploy=True)
    assert len(failures) == 1
    assert "deploy.sh" in failures[0]


def test_preflight_reports_a_logged_out_vercel(tmp_path, monkeypatch, local_checks_green):
    _stub_deploy_script(tmp_path)
    monkeypatch.setattr(
        refresh, "_capture",
        lambda argv: (0, "r2:\n") if argv[0] == "rclone" else (1, "Error: not authenticated"),
    )
    failures = refresh.preflight(root=tmp_path, require_deploy=True)
    assert len(failures) == 1
    assert "vercel" in failures[0]


def test_preflight_green_when_everything_answers(tmp_path, monkeypatch, local_checks_green):
    _stub_deploy_script(tmp_path)
    monkeypatch.setattr(
        refresh, "_capture",
        lambda argv: (0, "r2:\n") if argv[0] == "rclone" else (0, "andes\n"),
    )
    assert refresh.preflight(root=tmp_path, require_deploy=True) == []


def test_preflight_reports_every_failure_at_once(tmp_path, monkeypatch):
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(refresh, "_check_disk", lambda: (_ for _ in ()).throw(
        RuntimeError("2.1 GB free")))
    monkeypatch.setattr(refresh, "_check_postgres", lambda: (_ for _ in ()).throw(
        RuntimeError("connection refused")))
    monkeypatch.setattr(refresh, "_check_duckdb", lambda: None)
    failures = refresh.preflight(root=tmp_path, require_deploy=False)
    assert len(failures) == 2
    assert failures[0].startswith("disk:") and failures[1].startswith("postgres:")


def test_a_probe_that_hangs_becomes_a_named_preflight_failure(
    tmp_path, monkeypatch, local_checks_green
):
    """launchd starts no second instance of a label whose previous instance is
    still alive, so one wedged `vercel whoami` would stop the monthly refresh
    forever with nothing in the record."""
    _stub_deploy_script(tmp_path)

    def hang(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw.get("timeout"))

    monkeypatch.setattr(refresh.subprocess, "run", hang)
    failures = refresh.preflight(root=tmp_path, require_deploy=True)
    assert len(failures) == 2
    assert "rclone" in failures[0] and "timed out" in failures[0]
    assert "vercel" in failures[1] and "timed out" in failures[1]


def test_every_preflight_probe_carries_a_timeout(monkeypatch):
    seen = {}

    class _Proc:
        returncode = 0
        stdout = "r2:\n"
        stderr = ""

    def spy(argv, **kw):
        seen[argv[0]] = kw.get("timeout")
        return _Proc()

    monkeypatch.setattr(refresh.subprocess, "run", spy)
    assert refresh._capture(["rclone", "listremotes"]) == (0, "r2:\n")
    assert seen["rclone"] == refresh.PROBE_TIMEOUT_SECONDS == 60


def test_a_stage_is_run_with_no_timeout_at_all(monkeypatch):
    """dbt and the site build run 30+ minutes; a per-stage timeout would kill
    a healthy run. The consequence is documented in LAUNCH.md Step 11."""
    seen = {}

    class _Proc:
        returncode = 0

    def spy(argv, **kw):
        seen.update(kw)
        return _Proc()

    monkeypatch.setattr(refresh.subprocess, "run", spy)
    assert refresh._run(["npm", "run", "build"]) == 0
    assert "timeout" not in seen


def test_a_missing_lake_is_a_preflight_failure_and_creates_no_database(
    tmp_path, monkeypatch
):
    """duckdb.connect CREATES an empty database at a path that does not
    exist, so a misconfigured GOVBUDGET_DUCKDB/GOVBUDGET_DATA would pass the
    write-lock check green and leave an empty lake behind."""
    missing = tmp_path / "nowhere" / "govbudget.duckdb"
    monkeypatch.setattr(config, "DUCKDB_PATH", missing)
    with pytest.raises(FileNotFoundError) as exc:
        refresh._check_duckdb()
    assert str(missing) in str(exc.value)
    assert not missing.exists()


def test_preflight_calls_a_missing_lake_missing_not_locked(
    tmp_path, monkeypatch
):
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(refresh, "_check_disk", lambda: None)
    monkeypatch.setattr(refresh, "_check_postgres", lambda: None)
    monkeypatch.setattr(config, "DUCKDB_PATH", tmp_path / "nope.duckdb")
    failures = refresh.preflight(root=tmp_path, require_deploy=False)
    assert len(failures) == 1
    assert "no lake" in failures[0]
    assert "holding it" not in failures[0]


def test_preflight_names_a_missing_logs_directory(
    tmp_path, monkeypatch, local_checks_green
):
    """launchd opens StandardOutPath BEFORE exec and does not create missing
    parents, so the job cannot create logs/ for itself."""
    (tmp_path / "logs").rmdir()
    failures = refresh.preflight(root=tmp_path, require_deploy=False)
    assert len(failures) == 1
    assert "logs" in failures[0] and "mkdir -p" in failures[0]


# ── drift report ────────────────────────────────────────────────────────────


def test_drift_report_flags_a_stale_monthly_dataset(tmp_path):
    old = (NOW - dt.timedelta(days=200)).isoformat()
    fresh = (NOW - dt.timedelta(days=3)).isoformat()
    p = _manifest(tmp_path, [
        {"dataset": "contracts", "downloaded_at": old, "file_name": "c.zip"},
        {"dataset": "assistance", "downloaded_at": fresh, "file_name": "a.zip"},
    ])
    report = refresh.drift_report(p, NOW)
    assert report["datasets"]["contracts"]["age_days"] == 200
    assert report["datasets"]["assistance"]["age_days"] == 3
    assert len(report["alarms"]) == 1
    assert "contracts" in report["alarms"][0]
    assert "monthly" in report["alarms"][0]


def test_drift_report_is_silent_when_everything_is_fresh(tmp_path):
    fresh = (NOW - dt.timedelta(days=3)).isoformat()
    p = _manifest(tmp_path, [
        {"dataset": d, "downloaded_at": fresh, "file_name": "x"}
        for d in ("contracts", "assistance", "subawards")
    ])
    assert refresh.drift_report(p, NOW)["alarms"] == []


def test_drift_report_makes_no_claim_for_a_none_cadence(tmp_path):
    """mts_outlays declares None in _DECLARED_CADENCE — no claim, no alarm."""
    old = (NOW - dt.timedelta(days=900)).isoformat()
    p = _manifest(tmp_path, [
        {"dataset": "mts_outlays", "downloaded_at": old, "file_name": "m.parquet"},
    ])
    report = refresh.drift_report(p, NOW)
    assert report["datasets"]["mts_outlays"]["declared_cadence"] is None
    assert report["alarms"] == []


def test_drift_report_is_attached_to_the_run_record(tmp_path, calls, monkeypatch):
    fresh = (NOW - dt.timedelta(days=3)).isoformat()
    p = _manifest(tmp_path, [
        {"dataset": "contracts", "downloaded_at": fresh, "file_name": "c.zip"},
    ])
    monkeypatch.setattr(config, "MANIFEST_PATH", p)
    record = _refresh(tmp_path)
    assert record["drift"]["datasets"]["contracts"]["age_days"] == 3


def test_drift_report_counts_unparseable_manifest_lines(tmp_path):
    """gate 24 leg m treats one unparseable line in the SAME file as fatal
    ("refusing to guess ingest ages"); the operator alarm may be quieter than
    the published-page gate, but it may not be silent."""
    fresh = (NOW - dt.timedelta(days=3)).isoformat()
    p = tmp_path / "manifest.jsonl"
    p.write_text(
        json.dumps({"dataset": "contracts", "downloaded_at": fresh}) + "\n"
        # a crash between write and flush leaves a partial final line
        + '{"dataset": "assistance", "downloa\n'
        + json.dumps({"dataset": "subawards", "downloaded_at": "not-a-date"})
        + "\n"
    )
    report = refresh.drift_report(p, NOW)
    assert report["unparseable_lines"] == 2
    assert [a for a in report["alarms"]
            if a.startswith("2 unparseable manifest line(s)")]
    assert report["datasets"]["contracts"]["age_days"] == 3
    assert "subawards" not in report["datasets"]


def test_a_clean_manifest_counts_zero_unparseable_lines_and_says_nothing(
    tmp_path,
):
    fresh = (NOW - dt.timedelta(days=3)).isoformat()
    p = _manifest(tmp_path, [
        {"dataset": "contracts", "downloaded_at": fresh, "file_name": "c.zip"},
    ])
    report = refresh.drift_report(p, NOW)
    assert report["unparseable_lines"] == 0
    assert report["alarms"] == []


def test_an_unparseable_line_is_printed_once_as_a_drift_alarm(
    tmp_path, calls, monkeypatch, capsys
):
    fresh = (NOW - dt.timedelta(days=3)).isoformat()
    p = tmp_path / "manifest.jsonl"
    p.write_text(
        json.dumps({"dataset": "contracts", "downloaded_at": fresh}) + "\n"
        + "{not json at all\n"
    )
    monkeypatch.setattr(config, "MANIFEST_PATH", p)
    record = _refresh(tmp_path)
    err = capsys.readouterr().err
    assert err.count("DRIFT ALARM: 1 unparseable manifest line(s)") == 1
    assert record["drift"]["unparseable_lines"] == 1


# ── the stall check: green must not read as refreshed ───────────────────────


STALE_FOUR = ("assistance", "contracts", "mts_outlays", "subawards")


def test_a_sync_that_exits_zero_without_advancing_the_manifest_alarms(
    tmp_path, calls, monkeypatch
):
    """cmd_sync_subawards returns early once its FY is in the manifest
    (cli.py:67-69). The run is green; the dataset did not move."""
    stale = (NOW - dt.timedelta(days=5)).isoformat()
    p = _manifest(tmp_path, [
        {"dataset": d, "downloaded_at": stale, "file_name": "x"} for d in STALE_FOUR
    ])
    monkeypatch.setattr(config, "MANIFEST_PATH", p)
    record = _refresh(tmp_path)

    assert record["ok"] is True
    assert record["ingest_advanced"] == {d: False for d in STALE_FOUR}
    joined = " | ".join(record["drift"]["alarms"])
    for stage in ("sync-archive", "sync-subawards", "sync-fiscaldata"):
        assert stage in joined
    assert "did not advance" in joined


def test_an_advancing_sync_raises_no_stall_alarm(tmp_path, monkeypatch):
    stale = (NOW - dt.timedelta(days=5)).isoformat()
    p = _manifest(tmp_path, [
        {"dataset": d, "downloaded_at": stale, "file_name": "x"} for d in STALE_FOUR
    ])
    monkeypatch.setattr(config, "MANIFEST_PATH", p)

    def fake_run(argv, *, cwd=None, env=None):
        cmd = argv[3] if len(argv) > 3 else ""
        with p.open("a") as f:
            for ds in refresh._STAGE_DATASETS.get(cmd, ()):
                f.write(json.dumps({
                    "dataset": ds, "downloaded_at": NOW.isoformat(),
                    "file_name": "new",
                }) + "\n")
        return 0

    monkeypatch.setattr(refresh, "_run", fake_run)
    monkeypatch.setattr(refresh, "preflight", lambda **kw: [])
    record = _refresh(tmp_path)
    assert record["ingest_advanced"] == {d: True for d in STALE_FOUR}
    assert record["drift"]["alarms"] == []


def test_a_stall_alarm_does_not_claim_no_record_when_a_line_was_unreadable(
    tmp_path, calls, monkeypatch
):
    """A dataset whose newest line is malformed disappears from the report, and
    the unqualified "has no record ... at all" message would then be false."""
    p = tmp_path / "manifest.jsonl"
    p.write_text("{\"dataset\": \"subawards\", truncated\n")
    monkeypatch.setattr(config, "MANIFEST_PATH", p)
    record = _refresh(tmp_path)
    joined = " | ".join(record["drift"]["alarms"])
    assert "sync-subawards" in joined
    assert "unparseable" in joined


def test_a_dry_run_raises_no_stall_alarms(tmp_path, calls, monkeypatch):
    stale = (NOW - dt.timedelta(days=5)).isoformat()
    p = _manifest(tmp_path, [
        {"dataset": d, "downloaded_at": stale, "file_name": "x"} for d in STALE_FOUR
    ])
    monkeypatch.setattr(config, "MANIFEST_PATH", p)
    record = _refresh(tmp_path, dry_run=True)
    assert record["drift"]["alarms"] == []


# ── CLI surface ─────────────────────────────────────────────────────────────


def test_cli_refresh_passes_every_flag_through(monkeypatch):
    from govbudget import cli

    seen = {}
    monkeypatch.setattr(
        refresh, "run_refresh",
        lambda **kw: (seen.update(kw), {"ok": True})[1],
    )
    cli.main([
        "refresh", "--dry-run", "--yes", "--quarterly",
        "--from", "build", "--until", "site-verify",
    ])
    assert seen == {
        "dry_run": True, "assume_yes": True, "quarterly": True,
        "from_stage": "build", "until_stage": "site-verify",
    }


def test_cli_refresh_rejects_an_unknown_stage(monkeypatch):
    from govbudget import cli

    monkeypatch.setattr(refresh, "run_refresh", lambda **kw: {"ok": True})
    with pytest.raises(SystemExit) as exc:
        cli.main(["refresh", "--from", "synk-archive"])
    assert exc.value.code == 2
