"""Tests for govbudget.sam_daily — the unattended SAM extract driver.

No network and no lake. The published families are injected, and every
request goes through the REAL `sam_batch.fetch_batch` to tests/sam_fake's
FakeSam over httpx.MockTransport, so URLs, stored bodies, manifest lines (the
quota ledger) and answers are the real ones. The clock is pinned: a batch's
bodies are stamped RUN after the tick's decision time, as a real batch lands
seconds after its tick.
"""
from __future__ import annotations

import json
import plistlib
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import duckdb
import httpx
import pytest

from govbudget import cli, sam_batch, sam_daily
from govbudget.manifest import ManifestRecord, append_record
from govbudget.sam_daily import Outcome, run_daily
from govbudget.sam_entities import (
    DEFAULT_SAM_ENTITY_API_URL,
    DEFAULT_SAM_PUBLIC_ENTITY_URL,
)
from sam_fake import FakeSam

ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 9, 28, 13, 29, tzinfo=timezone.utc)
KEY = "sekret-key-0123456789"
CONTROL = sam_batch.CONTROL_UEI
H = timedelta(hours=1)
S = timedelta(seconds=1)
RUN = 30 * S


def fams(n, start=0):
    return [(f"FAM{i:03d}", f"UEI{i:09d}") for i in range(start, start + n)]


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SAM_API_KEY", KEY)
    monkeypatch.delenv("SAM_PUBLIC_ENTITY_URL", raising=False)
    monkeypatch.delenv("SAM_ENTITY_API_URL", raising=False)
    monkeypatch.setattr("govbudget.sam_entities._REQUEST_FLOOR_S", 0)
    report = tmp_path / "preflight.json"
    report.write_text(json.dumps({
        "endpoint": DEFAULT_SAM_ENTITY_API_URL, "status": 200,
        "public_url": DEFAULT_SAM_PUBLIC_ENTITY_URL, "public_url_status": 200,
    }))
    return SimpleNamespace(state_dir=tmp_path / "state", raw=tmp_path / "raw",
                           out=tmp_path / "out", report=report, slept=[])


def never(*_a, **_k):
    raise AssertionError("must not be called on this tick")


def tick(env, now, *, sam=None, families=None, families_fn=None,
         notify=None, **kw) -> Outcome:
    client = httpx.Client(transport=httpx.MockTransport(sam or FakeSam()))
    return run_daily(
        now=now, clock=lambda: now + RUN, sleep=env.slept.append,
        state_dir=env.state_dir, raw_dir=env.raw, out_dir=env.out,
        report_path=env.report, duckdb_path=Path("unused"),
        families_fn=families_fn or (lambda _p, top_n: families or fams(25)),
        client=client, fetch_fn=None if sam is not None else never,
        notify=notify if notify is not None else (lambda _t: True), **kw)


def state(env) -> dict:
    return json.loads((env.state_dir / "state.json").read_text())


def answers(env):
    return {r[0]: r[1] for r in duckdb.sql(
        f"select sam_uei, kind from '{env.out}/answers.parquet'").fetchall()}


def hand_run(env, when, n, start=0):
    """A hand-run `sam extract`: empty single bodies with manifest lines."""
    env.raw.mkdir(parents=True, exist_ok=True)
    for _, u in fams(n, start):
        (env.raw / f"{u}.json").write_text(json.dumps(
            {"entityData": [], "totalRecords": 0}))
        append_record(env.out / "manifest.jsonl", ManifestRecord(
            "sam_entities", None, f"{u}.json", "u", "0" * 64, 2, when.isoformat()))


def set_state(env, **kw):
    env.state_dir.mkdir(parents=True, exist_ok=True)
    (env.state_dir / "state.json").write_text(json.dumps(kw))


# ── batching, and proving it ────────────────────────────────────────────────

def test_the_first_batch_carries_the_control_and_proves_the_mode(env):
    sam = FakeSam()
    o = tick(env, T0, sam=sam)
    assert (o.status, o.fetched, o.missing, o.exit_code) == ("complete", 25, 0, 0)
    assert len(sam.requests) == 3                  # 9 + control, then 10, then 6
    assert sam.asked(0)[-1] == CONTROL and len(sam.asked(0)) == 10
    assert CONTROL not in sam.asked(1) and len(sam.asked(1)) == 10
    s = state(env)
    assert s["mode"] == "batch+integrity" and s["mode_verified"] is True
    assert "proven" in o.message
    assert all("integrityInformation" in q["includeSections"] for q in sam.requests)


def test_ten_requests_answer_about_a_hundred_families_a_day(env):
    o = tick(env, T0, sam=FakeSam(), families=fams(192))
    assert (o.status, o.fetched, o.missing) == ("fetched", 99, 93)
    assert o.note == "Stored 99 SAM answer(s); 93 families left (~1 more day(s))."


def test_sam_ignoring_the_batch_syntax_walks_down_to_single_requests(env):
    """Without the control in the answer nothing is marked absent, and the
    ladder reaches a mode SAM honours within the same tick."""
    sam = FakeSam(honour_batches=False)
    o = tick(env, T0, sam=sam, families=fams(12))
    s = state(env)
    assert (s["mode"], s["mode_verified"]) == ("single+integrity", True)
    assert "dropped" in o.message and o.fetched == 8     # 2 probes + 8 singles
    assert set(answers(env).values()) == {"registered"}  # no false absences


def test_integrity_refused_drops_to_plain_batches(env):
    o = tick(env, T0, sam=FakeSam(honour_integrity=False), families=fams(30))
    s = state(env)
    assert (s["mode"], s["mode_verified"]) == ("batch", True)
    assert o.fetched == 30 and o.failed == 1              # the refused probe
    assert len(s["failed_requests"]) == 1


def test_the_next_days_tick_sleeps_through_the_last_seconds(env):
    tick(env, T0, sam=FakeSam(), families=fams(250))
    o = tick(env, T0 + 23 * H, families_fn=never, families=fams(250))
    assert o.status == "waiting"
    o = tick(env, T0 + 24 * H, sam=FakeSam(), families=fams(250))
    assert env.slept == [31.0] and o.fetched == 100


# ── the three queries ───────────────────────────────────────────────────────

def test_the_three_queries_settle_every_kind_of_answer(env):
    f = fams(5)
    kinds = {f[0][1]: "opted_out", f[1][1]: "id_only", f[2][1]: "inactive",
             f[3][1]: "none"}
    sam = FakeSam(kinds, default_hides_expired=True)
    o = tick(env, T0, sam=sam, families=f)
    assert o.status == "complete"
    stages = [("id_assigned" if q.get("samRegistered") == "No" else
               "expired" if q.get("registrationStatus") == "E" else "registered")
              for q in sam.requests]
    assert stages == ["registered", "id_assigned", "expired"]
    assert answers(env) == {f[0][1]: "opted_out", f[1][1]: "id_assigned",
                            f[2][1]: "registered", f[3][1]: "not_public",
                            f[4][1]: "registered", CONTROL: "registered"}
    rows = duckdb.sql(f"select sam_uei from '{env.out}/entities.parquet'").fetchall()
    assert f[1][1] not in {r[0] for r in rows}    # never "Registration Active"


def test_the_first_days_empty_answers_are_asked_again_with_integrity(env):
    """RTX, Humana and BAE came back empty to a plain query, which cannot tell
    an opted-out entity from none, so they are asked again."""
    f = fams(3)
    hand_run(env, T0 - 30 * H, 3)
    o = tick(env, T0, sam=FakeSam({f[0][1]: "opted_out"}), families=f)
    assert o.fetched == 3 and answers(env)[f[0][1]] == "opted_out"


def test_a_page_too_small_for_duplicates_asks_the_rest_alone(env):
    f = fams(10)
    sam = FakeSam({u: "dup" for _, u in f[:6]})
    set_state(env, mode="batch+integrity", mode_verified=True)
    o = tick(env, T0, sam=sam, families=f)
    assert o.status == "complete"
    assert [len(sam.asked(i)) for i in range(len(sam.requests))] == [10, 1, 1, 1, 1, 1]


# ── quota ───────────────────────────────────────────────────────────────────

def test_a_hand_run_extract_counts_against_the_quota(env):
    hand_run(env, T0 - H, 4, start=100)
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.budget) == ("waiting", 6)


def test_preflight_probes_count_against_the_quota_from_the_shared_ledger(env):
    env.out.mkdir(parents=True)
    (env.out / "preflight_probes.jsonl").write_text("".join(
        json.dumps({"at": (T0 - H + i * S).isoformat(), "url": "u"}) + "\n"
        for i in range(2)))
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.budget) == ("waiting", 8)


def test_the_last_families_start_once_the_requests_they_need_are_free(env):
    hand_run(env, T0 - 20 * H, 9, start=100)                  # 1 request free
    set_state(env, missing=4, mode="batch+integrity", mode_verified=True)
    o = tick(env, T0, sam=FakeSam(), families=fams(4))        # 4 need 1 request
    assert (o.status, o.fetched, o.budget) == ("complete", 4, 1)


# ── retries and failures ────────────────────────────────────────────────────

def test_a_batch_timeout_retries_in_two_hours_with_half_size_batches(env):
    sam = FakeSam(fail=lambda n, q: httpx.ReadTimeout("t") if n == 1 else None)
    o = tick(env, T0, sam=sam, families=fams(40))
    assert (o.status, o.fetched, o.failed, o.exit_code) == ("sam_unavailable", 9, 1, 0)
    s = state(env)
    assert s["retry_pending"] and s["retry_after"] == (T0 + 2 * H).isoformat()
    assert len(s["batch_timeouts"]) == 10
    assert tick(env, T0 + H, families_fn=never, families=fams(40)).status == "waiting"
    sam2 = FakeSam()
    o = tick(env, T0 + 2 * H, sam=sam2, families=fams(40))
    # The 21 untouched families first; the timed-out ten behind them, halved.
    assert [len(sam2.asked(i)) for i in range(len(sam2.requests))] == [10, 10, 5, 5, 1]
    assert o.fetched == 31 and state(env)["batch_timeouts"] == {}


def test_a_registration_that_always_times_out_alone_ends_stuck(env):
    f = fams(3)
    bad = f[0][1]
    set_state(env, mode="single", mode_verified=True)
    outs = []
    for h in range(4 * 24):
        sam = FakeSam(fail=lambda n, q: httpx.ReadTimeout("t")
                      if q["ueiSAM"] == bad else None)
        o = tick(env, T0 + h * H, sam=sam, families=f)
        if o.status != "waiting":
            outs.append(o)
    assert sum(o.fetched for o in outs) == 2
    assert (outs[-1].status, outs[-1].exit_code) == ("stuck", 1)
    assert bad in outs[-1].message and "owner action" in outs[-1].note


def test_a_rate_limit_ends_the_batch_and_waits_out_the_window(env):
    sam = FakeSam(fail=lambda n, q: httpx.Response(429, text="OVER_RATE_LIMIT")
                  if n == 2 else None)
    o = tick(env, T0, sam=sam, families=fams(40))
    assert (o.status, o.fetched, o.failed, o.exit_code) == ("rate_limited", 19, 1, 0)
    assert state(env)["retry_after"] == (T0 + 24 * H).isoformat()
    assert tick(env, T0 + 6 * H, families_fn=never, families=fams(40)).status == "waiting"
    assert tick(env, T0 + 24 * H, sam=FakeSam(), families=fams(40)).fetched == 21


def test_offline_spends_nothing_and_retries_next_tick(env):
    o = tick(env, T0, sam=FakeSam(fail=lambda n, q: httpx.ConnectError("x")))
    assert (o.status, o.failed, o.note) == ("offline", 0, None)
    assert not state(env).get("failed_requests")
    assert tick(env, T0 + H, sam=FakeSam()).status == "complete"


def test_a_refused_key_is_an_owner_action(env):
    o = tick(env, T0, sam=FakeSam(fail=lambda n, q: httpx.Response(
        403, text="API_KEY_INVALID")))
    assert (o.status, o.exit_code) == ("sam_refused", 1)
    assert state(env)["retry_after"] == (T0 + 24 * H).isoformat()


def test_an_answer_that_will_not_parse_is_stored_and_reported_never_complete(env):
    f = fams(3)
    o = tick(env, T0, sam=FakeSam({f[1][1]: "noname"}), families=f)
    assert (o.status, o.exit_code) == ("shape_error", 1)
    assert "parquet rebuild failed" in o.message
    assert len(list((env.raw / "batches").glob("*.json"))) == 1
    o = tick(env, T0 + 25 * H, families=f)            # nothing owed; parquet stale
    assert o.status == "shape_error" and "older than the newest" in o.message


def test_a_missing_key_blocks_offline_without_touching_the_lake(env, monkeypatch):
    monkeypatch.delenv("SAM_API_KEY")
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.exit_code) == ("blocked", 1) and "SAM_API_KEY" in o.note
    assert tick(env, T0 + H, families_fn=never).note is None      # once a day
    assert "SAM_API_KEY" in tick(env, T0 + 25 * H, families_fn=never).note


def test_an_unreadable_preflight_report_is_blocked_not_a_crash(env):
    env.report.write_text("")
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.exit_code) == ("blocked", 1) and "does not read" in o.message


def test_a_corrupt_manifest_is_a_recorded_error(env):
    env.out.mkdir(parents=True)
    (env.out / "manifest.jsonl").write_text("{torn line\n")
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.exit_code) == ("error", 1) and o.note
    assert state(env)["last_status"] == "error"


def test_a_blocked_tick_keeps_an_earlier_retry_and_backoff(env, monkeypatch):
    tick(env, T0, sam=FakeSam(fail=lambda n, q: httpx.ReadTimeout("t") if n == 1 else None),
         families=fams(40))
    before = state(env)
    monkeypatch.delenv("SAM_API_KEY")
    tick(env, T0 + H, families_fn=never)
    after = state(env)
    assert after["retry_pending"] is True and after["retry_after"] == before["retry_after"]


# ── the lake ────────────────────────────────────────────────────────────────

def test_a_write_locked_lake_waits_quietly_then_speaks_once(env):
    def locked(_p, top_n):
        raise duckdb.IOException('IO Error: Could not set lock on file "x.duckdb": '
                                 "Conflicting lock is held in dbt (PID 4242)")
    outs = [tick(env, T0 + h * H, families_fn=locked) for h in (0, 3, 6, 7)]
    assert [o.note is None for o in outs] == [True, True, False, True]
    assert "PID 4242" in outs[0].message and outs[0].exit_code == 0
    assert tick(env, T0 + 8 * H, sam=FakeSam()).status == "complete"


def test_a_corrupt_lake_is_an_error_even_though_block_contains_lock(env):
    def corrupt(_p, top_n):
        raise duckdb.IOException("IO Error: Corrupt database file: computed "
                                 "checksum 1 does not match stored checksum 2 "
                                 "in block at location 536576")
    o = tick(env, T0, families_fn=corrupt)
    assert (o.status, o.exit_code) == ("error", 1) and "Corrupt" in o.note


def test_views_naming_a_vanished_path_say_to_rebuild_from_main(env):
    def gone(_p, top_n):
        raise duckdb.IOException('IO Error: No files found that match the '
                                 'pattern "/x/worktrees/y/data/parquet/sam/entities.parquet"')
    o = tick(env, T0, families_fn=gone)
    assert o.status == "error" and "govbudget build` from the main checkout" in o.message


def test_an_empty_family_list_is_an_error_never_complete(env):
    o = tick(env, T0, families_fn=lambda _p, top_n: [])
    assert (o.status, o.exit_code) == ("error", 1)


# ── completion, notices, state ──────────────────────────────────────────────

def test_completion_is_said_once(env):
    o = tick(env, T0, sam=FakeSam())
    assert o.status == "complete" and o.note.startswith("Every published family")
    o = tick(env, T0 + 25 * H)                         # daily re-check, pre-network
    assert o.status == "complete" and o.note is None


def test_a_notice_nobody_saw_does_not_silence_the_next_tick(env, monkeypatch):
    monkeypatch.delenv("SAM_API_KEY")
    o = run_daily(now=T0, state_dir=env.state_dir, raw_dir=env.raw,
                  out_dir=env.out, report_path=env.report,
                  families_fn=never, fetch_fn=never)       # no notify
    assert o.note and not o.notified
    assert tick(env, T0 + H, families_fn=never, notify=lambda _t: False).notified is False
    o = tick(env, T0 + 2 * H, families_fn=never)
    assert o.note and o.notified


def test_the_key_never_reaches_the_message_note_state_or_stderr(env, capsys):
    def boom(*_a, **_k):
        raise RuntimeError(f"boom api_key={KEY}")
    o = run_daily(now=T0, clock=lambda: T0, state_dir=env.state_dir,
                  raw_dir=env.raw, out_dir=env.out, report_path=env.report,
                  families_fn=lambda _p, top_n: fams(3), fetch_fn=boom,
                  notify=lambda _t: True)
    assert o.status == "error"
    blobs = [o.message, o.note, (env.state_dir / "state.json").read_text(),
             capsys.readouterr().err]
    assert all(KEY not in b for b in blobs) and "api_key=…" in o.message


def test_a_run_killed_mid_request_is_charged_for_it(env):
    set_state(env, inflight=(T0 - H).isoformat())
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.budget) == ("waiting", 9)


def test_a_second_instance_refuses_while_the_lock_is_held(env):
    held = sam_daily._acquire_lock(env.state_dir / ".lock")
    try:
        o = tick(env, T0, families_fn=never)
    finally:
        held.close()
    assert (o.status, o.note) == ("already_running", None)
    assert not (env.state_dir / "state.json").exists()


def test_check_reads_the_lake_but_locks_spends_writes_and_notifies_nothing(env):
    posted = []
    o = tick(env, T0, check=True, notify=posted.append, families=fams(25))
    assert o.status == "check" and "mode batch+integrity (unproven)" in o.message
    assert "ask about 25" in o.message
    assert not env.state_dir.exists() and posted == [] and o.note is None


def test_a_corrupt_state_file_is_kept_aside_reported_and_backs_off_a_day(env):
    env.state_dir.mkdir(parents=True)
    (env.state_dir / "state.json").write_text("{not json")
    assert "back off 24 hours" in tick(env, T0, check=True).message
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.exit_code) == ("corrupt_state", 1) and o.notified
    aside = env.state_dir / "state.json.corrupt-20260928T132900Z"
    assert aside.read_text() == "{not json" and aside.name in o.message
    assert tick(env, T0 + 23 * H, families_fn=never).status == "waiting"
    assert tick(env, T0 + 25 * H, sam=FakeSam()).status == "complete"


def test_the_state_lives_beside_the_manifest_so_every_checkout_shares_it(env):
    run_daily(now=T0, clock=lambda: T0 + RUN, raw_dir=env.raw, out_dir=env.out,
              report_path=env.report, families_fn=lambda _p, top_n: fams(3),
              client=httpx.Client(transport=httpx.MockTransport(FakeSam())),
              notify=lambda _t: True)
    assert (env.out / "daily" / "state.json").exists()
    assert (env.out / "daily" / ".lock").exists()


# ── the CLI, the notification and the launchd files ─────────────────────────

@pytest.mark.parametrize("flags", [[], ["--notify"]])
def test_cmd_sam_daily_prints_one_line_and_exits_by_status(monkeypatch, capsys, flags):
    seen = {}

    def fake_run(**kw):
        seen.update(kw)
        return Outcome("blocked", "no key", at="2026-09-28T13:29:00+00:00",
                       note="SAM daily is blocked (owner action): no key")
    monkeypatch.setattr(sam_daily, "run_daily", fake_run)
    with pytest.raises(SystemExit) as exc:
        cli.main(["sam", "daily", *flags])
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "sam daily 2026-09-28T13:29:00+00:00: blocked — no key" in out
    assert "notice (not posted)" in out
    assert (seen["notify"] is sam_daily.notify_macos) == ("--notify" in flags)


def test_notify_macos_passes_the_text_as_argv_and_never_raises(monkeypatch):
    seen = {}

    def fake_run(args, **kw):
        seen["args"] = args
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(sam_daily.subprocess, "run", fake_run)
    body = 'He said "done" & left \\ early'
    assert sam_daily.notify_macos(body) is True
    assert seen["args"][-1] == body and all(body not in a for a in seen["args"][:-1])

    def missing(*_a, **_k):
        raise FileNotFoundError("osascript")
    monkeypatch.setattr(sam_daily.subprocess, "run", missing)
    assert sam_daily.notify_macos(body) is False


def test_the_plist_template_ticks_hourly_and_points_at_the_wrapper(tmp_path):
    template = ROOT / "scripts/launch/com.fiscalreceipts.sam-daily.plist.template"
    text = template.read_text().replace("__REPO_ROOT__", str(tmp_path))
    plist = plistlib.loads(text.encode())
    assert plist["Label"] == "com.fiscalreceipts.sam-daily"
    assert plist["ProgramArguments"] == [f"{tmp_path}/scripts/launch/sam_daily.sh"]
    assert plist["StartCalendarInterval"] == {"Minute": 17}
    assert plist["RunAtLoad"] is True and plist["WorkingDirectory"] == str(tmp_path)
    if shutil.which("plutil"):
        out = tmp_path / "t.plist"
        out.write_text(text)
        assert subprocess.run(["plutil", "-lint", str(out)],
                              capture_output=True).returncode == 0


def test_the_wrapper_is_executable_forwards_to_sam_daily_and_installs_nothing():
    wrapper = ROOT / "scripts/launch/sam_daily.sh"
    text = wrapper.read_text()
    assert wrapper.stat().st_mode & 0o111
    assert 'uv run --no-sync python -m govbudget sam daily --notify "$@"' in text
    code = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    assert not any("launchctl" in ln or "LaunchAgents" in ln for ln in code)


# ── review round 3 (2026-09-27) ─────────────────────────────────────────────

def test_a_family_that_always_times_out_cannot_block_the_proof(env):
    """Unproven, the first proof carried it and timed out; the next proof
    leaves timed-out families out, succeeds, and the extract moves on."""
    f = fams(30)
    poison = f[0][1]

    def sam():
        return FakeSam(fail=lambda n, q: httpx.ReadTimeout("t")
                       if poison in q["ueiSAM"] else None)
    o = tick(env, T0, sam=sam(), families=f)
    assert o.status == "sam_unavailable" and not state(env).get("mode_verified")
    o = tick(env, T0 + 2 * H, sam=sam(), families=f)
    s = state(env)
    assert s["mode_verified"] is True and s["mode"] == "batch+integrity"
    assert o.fetched == 19 and answers(env).get(poison) is None


def test_sam_failing_the_integrity_shape_with_5xx_steps_down_after_two_proofs(env):
    def sam():
        return FakeSam(fail=lambda n, q: httpx.Response(503, text="down")
                       if "integrityInformation" in q.get("includeSections", "") else None)
    tick(env, T0, sam=sam(), families=fams(20))
    assert state(env).get("proof_failures") == 1
    o = tick(env, T0 + 2 * H, sam=sam(), families=fams(20))
    assert state(env)["mode"] == "batch" and "did not answer its proof twice" in o.message
    o = tick(env, T0 + 4 * H, sam=sam(), families=fams(20))
    assert state(env)["mode_verified"] is True and o.status == "complete"


def test_a_duplicate_on_the_proof_page_keeps_the_batch_mode(env):
    f = fams(12)
    o = tick(env, T0, sam=FakeSam({u: "dup" for _, u in f[:6]}), families=f)
    s = state(env)
    assert (s["mode"], s["mode_verified"]) == ("batch+integrity", True)
    assert o.status == "complete"


def test_an_unreadable_answer_is_charged_once_named_and_the_rest_go_on(env):
    f = fams(30)
    bad = FakeSam(fail=lambda n, q: httpx.Response(200, json={
        "totalRecords": 1, "entityData": [{"entityRegistration": None}]})
        if n == 1 else None)
    o = tick(env, T0, sam=bad, families=f)
    assert (o.status, o.exit_code) == ("shape_error", 1)
    assert "do not read" in o.message and "batches/" in o.message
    assert o.fetched == 20                              # 10 unreadable, 20 answered
    lines = (env.out / "manifest.jsonl").read_text().splitlines()
    assert len(lines) == 4 and not state(env).get("failed_requests")
    o = tick(env, T0 + 25 * H, families=f)              # never re-asked
    assert o.status == "shape_error"


def test_offline_after_a_request_was_sent_keeps_the_retry_open(env):
    sam = FakeSam(fail=lambda n, q: httpx.ConnectError("x") if n == 1 else None)
    o = tick(env, T0, sam=sam, families=fams(40))
    assert (o.status, o.fetched) == ("offline", 9)
    assert state(env)["retry_pending"] is True
    o = tick(env, T0 + H, sam=FakeSam(), families=fams(40))
    assert o.fetched == 31
