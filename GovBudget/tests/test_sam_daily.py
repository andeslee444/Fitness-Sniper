"""Tests for govbudget.sam_daily — the unattended SAM extract driver.

No network and no lake: the published families and the extract are injected.
The injected extract behaves like `sam_entities.extract_entities` where the
driver can see it: it writes a raw body and a manifest line per stored
answer, stamped a second apart AFTER the tick's decision time (a real batch
takes ~10 s), rebuilds entities.parquet at the end, and raises the real
exception types. The clock is pinned; every stamp a test reads is one it
chose.
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
import pytest

from govbudget import cli, sam_daily
from govbudget.manifest import ManifestRecord, append_record
from govbudget.sam_daily import Outcome, run_daily
from govbudget.sam_entities import (
    DEFAULT_SAM_ENTITY_API_URL,
    DEFAULT_SAM_PUBLIC_ENTITY_URL,
    SamAuthError,
    SamOfflineError,
    SamRateLimitError,
    SamShapeError,
    SamUnavailableError,
)

ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 9, 27, 12, 17, tzinfo=timezone.utc)
KEY = "sekret-key-0123456789"
FAMS = [(f"FAM{i:02d}", f"UEI{i:09d}") for i in range(25)]
H = timedelta(hours=1)
S = timedelta(seconds=1)
RUN = 30 * S          # how long a batch takes: the failed-request stamp time


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SAM_API_KEY", KEY)
    monkeypatch.delenv("SAM_PUBLIC_ENTITY_URL", raising=False)
    monkeypatch.delenv("SAM_ENTITY_API_URL", raising=False)
    report = tmp_path / "preflight.json"
    report.write_text(json.dumps({
        "endpoint": DEFAULT_SAM_ENTITY_API_URL, "status": 200,
        "public_url": DEFAULT_SAM_PUBLIC_ENTITY_URL, "public_url_status": 200,
    }))
    return SimpleNamespace(state_dir=tmp_path / "state", raw=tmp_path / "raw",
                           out=tmp_path / "out", report=report, slept=[])


def fake_extract(*, fail=None, calls=None, rebuild=True):
    """Stores up to `max_requests` missing bodies in the order given. `fail`
    maps (request number, uei) to an exception to raise instead, or None."""
    def extract(families, *, api_key, out_dir, raw_dir, max_requests, endpoint):
        assert api_key == KEY and endpoint == DEFAULT_SAM_ENTITY_API_URL
        if calls is not None:
            calls.append((max_requests, [u for _, u in families]))
        raw_dir.mkdir(parents=True, exist_ok=True)
        n = 0
        try:
            for _, uei in families:
                body = raw_dir / f"{uei}.json"
                if body.exists():
                    continue
                if n >= max_requests:
                    break
                exc = fail(n, uei) if fail else None
                if exc is not None:
                    raise exc
                body.write_text("{}")
                append_record(Path(out_dir) / "manifest.jsonl", ManifestRecord(
                    dataset="sam_entities", fiscal_year=None, file_name=body.name,
                    source_url="https://api.sam.gov/x", sha256="0" * 64, bytes=2,
                    downloaded_at=(extract.now + (n + 1) * S).isoformat()))
                n += 1
        finally:
            if rebuild:
                Path(out_dir).mkdir(parents=True, exist_ok=True)
                (Path(out_dir) / "entities.parquet").write_bytes(b"PAR1")
        return Path(out_dir) / "entities.parquet"
    return extract


def unavailable_on(*ueis):
    return lambda n, uei: (SamUnavailableError(f"SAM did not answer for {uei}",
                                               uei=uei) if uei in ueis else None)


def never(*_a, **_k):
    raise AssertionError("must not be called on this tick")


def tick(env, now, *, extract=None, families=FAMS, families_fn=None,
         notify=None, **kw) -> Outcome:
    if extract is not None and extract is not never:
        extract.now = now
    return run_daily(
        now=now, clock=lambda: now + RUN, sleep=env.slept.append,
        state_dir=env.state_dir, raw_dir=env.raw, out_dir=env.out,
        report_path=env.report, duckdb_path=Path("unused"),
        families_fn=families_fn or (lambda _p, top_n: families),
        extract_fn=extract or never,
        notify=notify if notify is not None else (lambda _t: True), **kw)


def state(env) -> dict:
    return json.loads((env.state_dir / "state.json").read_text())


# ── the quota and the daily batch ───────────────────────────────────────────

def test_a_fresh_install_runs_a_full_batch_and_says_how_many_are_left(env):
    calls = []
    o = tick(env, T0, extract=fake_extract(calls=calls))
    assert (o.status, o.fetched, o.missing, o.exit_code) == ("fetched", 10, 15, 0)
    assert calls[0][0] == 10
    assert o.note == ("Stored 10 SAM answer(s); 15 families left "
                      "(~2 more batch(es), one a day).") and o.notified
    s = state(env)
    assert s["missing"] == 15 and s["retry_pending"] is False
    assert s["retry_until"] == (T0 + 24 * H).isoformat()


def test_the_next_days_tick_sleeps_through_the_last_seconds_instead_of_an_hour(env):
    """The batch's stamps land seconds after its tick, so the tick 24 h later
    is seconds early; without the short sleep every batch slips an hour and
    20 batches take 21 days."""
    tick(env, T0, extract=fake_extract())
    assert tick(env, T0 + 23 * H, families_fn=never).status == "waiting"
    o = tick(env, T0 + 24 * H, extract=fake_extract())
    assert (o.status, o.fetched) == ("fetched", 10)
    assert env.slept == [11.0]                 # last stamp T0+10 s, +1 s margin


def test_a_hand_run_extract_counts_against_the_quota_through_the_manifest(env):
    x = fake_extract()
    x.now = T0 - H
    x(FAMS, api_key=KEY, out_dir=env.out, raw_dir=env.raw, max_requests=4,
      endpoint=DEFAULT_SAM_ENTITY_API_URL)
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.budget) == ("waiting", 6)
    assert f"needed from {(T0 - H + 4 * S + 24 * H).isoformat()}" in o.message


def test_preflight_probes_count_against_the_quota_from_the_shared_ledger(env):
    env.out.mkdir(parents=True)
    (env.out / "preflight_probes.jsonl").write_text("".join(
        json.dumps({"at": (T0 - H + i * S).isoformat(), "url": "u"}) + "\n"
        for i in range(2)))
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.budget) == ("waiting", 8)


def test_the_last_families_run_once_what_is_free_covers_them(env):
    x = fake_extract()
    x.now = T0 - 20 * H
    x(FAMS, api_key=KEY, out_dir=env.out, raw_dir=env.raw, max_requests=7,
      endpoint=DEFAULT_SAM_ENTITY_API_URL)
    env.state_dir.mkdir(parents=True)
    (env.state_dir / "state.json").write_text(json.dumps({"missing": 3}))
    ten = FAMS[:10]                           # 7 stored, 3 missing, 3 free
    o = tick(env, T0, extract=fake_extract(), families=ten)
    assert (o.status, o.fetched, o.budget) == ("complete", 3, 3)


def test_the_fit_rule_waits_until_exactly_enough_are_free(env):
    x = fake_extract()
    x.now = T0 - 20 * H
    x(FAMS, api_key=KEY, out_dir=env.out, raw_dir=env.raw, max_requests=8,
      endpoint=DEFAULT_SAM_ENTITY_API_URL)
    env.state_dir.mkdir(parents=True)
    (env.state_dir / "state.json").write_text(json.dumps({"missing": 3}))
    o = tick(env, T0, families_fn=never, families=FAMS[:11])   # 2 free, 3 needed
    assert (o.status, o.budget) == ("waiting", 2)
    assert f"3 needed from {(T0 - 20 * H + S + 24 * H).isoformat()}" in o.message


# ── retries ─────────────────────────────────────────────────────────────────

def test_a_timeout_mid_batch_retries_the_rest_of_the_window_two_hours_later(env):
    calls = []
    o = tick(env, T0, extract=fake_extract(
        fail=lambda n, u: SamUnavailableError("timeout", uei=u) if n == 3 else None,
        calls=calls))
    assert (o.status, o.fetched, o.failed, o.exit_code) == ("sam_unavailable", 3, 1, 0)
    assert o.note.startswith("SAM did not answer after storing 3:")
    s = state(env)
    assert s["retry_pending"] and s["retry_after"] == (T0 + 2 * H).isoformat()
    assert s["uei_failures"] == {FAMS[3][1]: {
        "batches": 1, "last_batch": (T0 + 24 * H).isoformat()}}
    assert tick(env, T0 + H, families_fn=never).status == "waiting"
    o = tick(env, T0 + 2 * H, extract=fake_extract(calls=calls))
    assert [c[0] for c in calls] == [10, 6]           # 10 - 3 stored - 1 failed
    assert calls[1][1][-1] == FAMS[3][1]              # the one that failed goes last
    assert (o.status, o.fetched) == ("fetched", 6)
    assert tick(env, T0 + 20 * H, families_fn=never).status == "waiting"
    # The retry's own stamps (T0 + 2 h + 1..6 s) set the next full batch:
    # the T0 + 26 h tick sleeps the last 6 s (+1) and runs it.
    assert tick(env, T0 + 25 * H, families_fn=never).status == "waiting"
    o = tick(env, T0 + 26 * H, extract=fake_extract())
    assert env.slept == [7.0]
    # One that failed once now waits behind the 15 that never did.
    assert o.fetched == 10 and not (env.raw / f"{FAMS[3][1]}.json").exists()


def test_a_retry_never_outlives_its_batchs_window(env):
    """Review finding 1: request 2 and the retry's last request both time out.
    The next day's first roll-off must not start a 1-request 'retry' that
    pushes the next full batch back a day."""
    calls = []
    fail_once = {"n": 0}

    def fail(n, uei):
        if n == 1 and fail_once["n"] == 0:
            fail_once["n"] = 1
            return SamUnavailableError("timeout", uei=uei)
        return None
    tick(env, T0, extract=fake_extract(fail=fail, calls=calls))        # 1 stored, 1 failed
    tick(env, T0 + 2 * H, extract=fake_extract(
        fail=lambda n, u: SamUnavailableError("t", uei=u) if n == 7 else None,
        calls=calls))                                                  # 7 stored, 1 failed
    assert state(env)["retry_pending"] is True
    # Just past T0 + 24 h the first batch's 2 requests have rolled off, but
    # the retry window is over: wait for a full 10.
    o = tick(env, T0 + 24 * H + 5 * 60 * S, families_fn=never)
    assert o.status == "waiting" and o.budget == 2
    assert state(env)["retry_pending"] is False
    o = tick(env, T0 + 26 * H + 5 * 60 * S, extract=fake_extract(calls=calls))
    assert (o.status, o.fetched) == ("fetched", 10)


def hourly(env, start, hours, families, extract):
    """Tick every hour like launchd; returns the outcomes that did anything."""
    outs = []
    for h in range(hours):
        o = tick(env, start + h * H, extract=extract, families=families)
        if o.status != "waiting":
            outs.append(o)
    return outs


def test_a_registration_that_always_fails_blocks_nothing_and_ends_stuck(env):
    """It goes behind the rest from its batch's retry on, so the other 11
    are stored on schedule; only once it is the last one, failing in its
    third daily batch, is it `stuck` (exit 1)."""
    twelve, bad = FAMS[:12], FAMS[0][1]
    outs = hourly(env, T0, 4 * 24, twelve, fake_extract(fail=unavailable_on(bad)))
    assert [o.status for o in outs][:2] == ["sam_unavailable", "fetched"]
    assert sum(o.fetched for o in outs) == 11
    assert (outs[-1].status, outs[-1].exit_code) == ("stuck", 1)
    assert bad in outs[-1].message and "owner action" in outs[-1].note
    first_stuck = next(o for o in outs if o.status == "stuck")
    assert f"failed in {3}+ daily batches" in first_stuck.message


def test_a_few_hours_of_outage_is_one_failed_batch_not_stuck(env):
    """Review 2, finding 2: the batch and both 2-hourly retries fail on the
    last family while SAM is down — one batch, so no false 'owner action'."""
    two = FAMS[:2]
    tick(env, T0, extract=fake_extract(), families=FAMS[:1])      # 1 stored
    down = fake_extract(fail=lambda n, u: SamUnavailableError("503", uei=u))
    outs = hourly(env, T0 + 25 * H, 6, two, down)
    assert [o.status for o in outs] == ["sam_unavailable"] * 3
    assert state(env)["uei_failures"][FAMS[1][1]]["batches"] == 1


def test_one_bad_registration_never_starves_another_deferred_one(env):
    """Review 2, finding 1: X always fails, Y failed in three batches during
    an outage. Fewest-failed-batches first means Y is asked before X."""
    x, y = FAMS[0][1], FAMS[1][1]
    env.state_dir.mkdir(parents=True)
    (env.state_dir / "state.json").write_text(json.dumps({"uei_failures": {
        x: {"batches": 9, "last_batch": "2026-09-20T00:00:00+00:00"},
        y: {"batches": 3, "last_batch": "2026-09-21T00:00:00+00:00"}}}))
    calls = []
    o = tick(env, T0, extract=fake_extract(fail=unavailable_on(x), calls=calls),
             families=FAMS[:2])
    assert calls[0][1] == [y, x]
    assert (o.fetched, o.status) == (1, "stuck")      # Y stored; only X is left


def test_a_rate_limit_is_never_retried_inside_its_window(env):
    """SAM counts more than the ledgers do (a failed preflight, a hand run's
    failed request), so its 429 ends the batch."""
    o = tick(env, T0, extract=fake_extract(
        fail=lambda n, u: SamRateLimitError("quota spent") if n == 2 else None))
    assert (o.status, o.failed, o.exit_code) == ("rate_limited", 1, 0)
    assert o.note.startswith("SAM says the day's quota is used up after storing 2")
    s = state(env)
    assert s["retry_after"] == (T0 + 6 * H).isoformat() and not s["retry_pending"]
    o = tick(env, T0 + 6 * H, families_fn=never)
    assert (o.status, o.budget, o.note) == ("waiting", 7, None)
    assert tick(env, T0 + 25 * H, extract=fake_extract()).status == "fetched"


def test_an_exhausted_retry_says_when_the_next_real_batch_is(env):
    """Review 2, findings 1 and 12: once a failed batch's retry has used the
    window, the waiting line must name the next FULL batch, not a retry at a
    roll-off that falls after the retry window has closed."""
    tick(env, T0, extract=fake_extract(
        fail=lambda n, u: SamUnavailableError("t", uei=u) if n == 3 else None))
    tick(env, T0 + 2 * H, extract=fake_extract(
        fail=lambda n, u: SamUnavailableError("t", uei=u) if n == 5 else None))
    o = tick(env, T0 + 12 * H, families_fn=never)
    assert o.status == "waiting" and "retrying" not in o.message
    last = T0 + 2 * H + RUN                         # the retry's failed stamp
    assert f"10 needed from {(last + 24 * H).isoformat()}" in o.message
    assert o.wake_at == last + 24 * H


def test_offline_spends_nothing_stays_quiet_and_retries_next_tick(env):
    o = tick(env, T0, extract=fake_extract(
        fail=lambda n, u: SamOfflineError("no network", uei=u)))
    assert (o.status, o.failed, o.exit_code, o.note) == ("offline", 0, 0, None)
    s = state(env)
    assert not s.get("failed_requests") and "retry_until" not in s  # no batch began
    o = tick(env, T0 + H, extract=fake_extract())
    assert (o.status, o.fetched) == ("fetched", 10)


# ── failures that need a person ─────────────────────────────────────────────

def test_a_refused_key_is_an_owner_action_and_exits_non_zero(env):
    o = tick(env, T0, extract=fake_extract(
        fail=lambda n, u: SamAuthError("SAM rejected the key (403)")))
    assert (o.status, o.exit_code) == ("sam_refused", 1)
    assert o.note.startswith("SAM refused the key (owner action)")
    assert state(env)["retry_after"] == (T0 + 24 * H).isoformat()


def test_an_unparseable_answer_is_a_shape_error_not_a_refusal_and_never_complete(env):
    """Review findings 7 and 14: the body is stored before it is parsed, and
    every later rebuild fails on it — the driver must keep saying so rather
    than report progress and, at the end, 'complete'."""
    twelve = FAMS[:12]

    def stored_then_unparseable(n, uei):
        if n:
            return None
        (env.raw / f"{uei}.json").write_text("{}")    # the real extract stores first
        return SamShapeError("legalBusinessName is empty")
    o = tick(env, T0, families=twelve, extract=fake_extract(fail=stored_then_unparseable))
    assert (o.status, o.exit_code) == ("shape_error", 1)
    assert o.note.startswith("A SAM answer is unusable (owner action)")
    # Next day the rebuild fails (the extract returns None, parquet untouched).
    o = tick(env, T0 + 25 * H, families=twelve, extract=fake_extract(rebuild=False))
    assert (o.status, o.fetched, o.missing, o.exit_code) == ("shape_error", 10, 1, 1)
    assert "sam reparse" in o.message
    (env.raw / f"{twelve[11][1]}.json").write_text("{}")   # a hand run stores the last
    o = tick(env, T0 + 50 * H, families=twelve)
    assert (o.status, o.exit_code) == ("shape_error", 1)
    assert "older than the newest" in o.message


def test_a_missing_key_blocks_offline_without_touching_the_lake_or_quota(env, monkeypatch):
    monkeypatch.delenv("SAM_API_KEY")
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.exit_code) == ("blocked", 1) and "SAM_API_KEY" in o.note
    assert not state(env).get("failed_requests")
    assert tick(env, T0 + H, families_fn=never).note is None      # once a day
    assert "SAM_API_KEY" in tick(env, T0 + 25 * H, families_fn=never).note


def test_an_unreadable_preflight_report_is_blocked_not_a_crash(env):
    env.report.write_text("")
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.exit_code) == ("blocked", 1)
    assert "does not read" in o.message and state(env)["last_status"] == "blocked"


def test_a_corrupt_manifest_is_a_recorded_error_not_a_silent_crash(env):
    env.out.mkdir(parents=True)
    (env.out / "manifest.jsonl").write_text("{torn line\n")
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.exit_code) == ("error", 1) and o.note
    assert state(env)["last_status"] == "error"


def test_a_blocked_tick_keeps_an_earlier_retry_and_backoff_standing(env, monkeypatch):
    tick(env, T0, extract=fake_extract(fail=unavailable_on(FAMS[1][1])))
    before = state(env)
    monkeypatch.delenv("SAM_API_KEY")
    tick(env, T0 + H, families_fn=never)
    after = state(env)
    assert after["retry_pending"] is True
    assert after["retry_after"] == before["retry_after"]


# ── the lake ────────────────────────────────────────────────────────────────

def test_a_write_locked_lake_waits_quietly_then_speaks_once_after_six_hours(env):
    def locked(_p, top_n):
        raise duckdb.IOException('IO Error: Could not set lock on file "x.duckdb": '
                                 "Conflicting lock is held in dbt (PID 4242)")
    outs = [tick(env, T0 + h * H, families_fn=locked) for h in (0, 3, 6, 7)]
    assert [o.note is None for o in outs] == [True, True, False, True]
    assert "PID 4242" in outs[0].message and outs[0].exit_code == 0
    assert tick(env, T0 + 8 * H, extract=fake_extract()).status == "fetched"
    assert state(env)["since"] == {}


def test_a_corrupt_lake_is_an_error_even_though_block_contains_lock(env):
    def corrupt(_p, top_n):
        raise duckdb.IOException("IO Error: Corrupt database file: computed "
                                 "checksum 1 does not match stored checksum 2 "
                                 "in block at location 536576")
    o = tick(env, T0, families_fn=corrupt)
    assert (o.status, o.exit_code) == ("error", 1) and "Corrupt" in o.note


def test_views_naming_a_vanished_path_say_to_rebuild_from_the_main_checkout(env):
    def gone(_p, top_n):
        raise duckdb.IOException('IO Error: No files found that match the '
                                 'pattern "/x/worktrees/y/data/parquet/sam/entities.parquet"')
    o = tick(env, T0, families_fn=gone)
    assert o.status == "error" and "govbudget build` from the main checkout" in o.message


def test_an_empty_family_list_is_an_error_never_complete(env):
    o = tick(env, T0, families=[])
    assert (o.status, o.exit_code) == ("error", 1)


# ── completion, notices, state ──────────────────────────────────────────────

def test_the_last_batch_completes_and_says_so_once(env):
    twelve = FAMS[:12]
    tick(env, T0, extract=fake_extract(), families=twelve)
    o = tick(env, T0 + 25 * H, extract=fake_extract(), families=twelve)
    assert (o.status, o.fetched, o.missing) == ("complete", 2, 0)
    assert o.note.startswith("Every published family's SAM answer is stored")
    o = tick(env, T0 + 50 * H, families=twelve)        # daily re-check
    assert o.status == "complete" and o.note is None


def test_a_notice_nobody_saw_does_not_silence_the_next_tick(env, monkeypatch):
    """Review finding 13: a hand run without --notify (or a failed post) must
    not use up the scheduled job's once-a-day notice."""
    monkeypatch.delenv("SAM_API_KEY")
    o = run_daily(now=T0, state_dir=env.state_dir, raw_dir=env.raw,
                  out_dir=env.out, report_path=env.report,
                  families_fn=never, extract_fn=never)       # no notify
    assert o.note and not o.notified
    assert tick(env, T0 + H, families_fn=never, notify=lambda _t: False).notified is False
    o = tick(env, T0 + 2 * H, families_fn=never)
    assert o.note and o.notified


def test_the_key_never_reaches_the_message_note_state_or_stderr(env, capsys):
    o = tick(env, T0, extract=fake_extract(
        fail=lambda n, u: RuntimeError(f"boom api_key={KEY}")))
    assert o.status == "error"
    blobs = [o.message, o.note, (env.state_dir / "state.json").read_text(),
             capsys.readouterr().err]
    assert all(KEY not in b for b in blobs) and "api_key=…" in o.message


def test_a_run_killed_mid_request_is_charged_for_it(env):
    env.state_dir.mkdir(parents=True)
    (env.state_dir / "state.json").write_text(json.dumps(
        {"inflight": (T0 - H).isoformat()}))
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.budget) == ("waiting", 9)
    assert state(env)["failed_requests"] == [(T0 - H + 12 * 60 * S).isoformat()]


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
    o = tick(env, T0, check=True, notify=posted.append)
    assert o.status == "check" and "would fetch 10 now" in o.message
    assert not env.state_dir.exists() and posted == [] and o.note is None
    tick(env, T0, extract=fake_extract())
    before = (env.state_dir / "state.json").read_text()
    o = tick(env, T0 + H, check=True, notify=posted.append)
    assert "would wait" in o.message and "15 of 25" in o.message
    assert (env.state_dir / "state.json").read_text() == before and posted == []


def test_a_corrupt_state_file_is_kept_aside_reported_and_backs_off_a_day(env):
    env.state_dir.mkdir(parents=True)
    (env.state_dir / "state.json").write_text("{not json")
    o = tick(env, T0, check=True)
    assert o.status == "check" and "back off 24 hours" in o.message
    o = tick(env, T0, families_fn=never)
    assert (o.status, o.exit_code) == ("corrupt_state", 1) and o.notified
    aside = env.state_dir / "state.json.corrupt-20260927T121700Z"
    assert aside.read_text() == "{not json" and aside.name in o.message
    assert tick(env, T0 + 23 * H, families_fn=never).status == "waiting"
    assert tick(env, T0 + 25 * H, extract=fake_extract()).status == "fetched"


def test_the_state_lives_beside_the_manifest_so_every_checkout_shares_it(env):
    x = fake_extract()
    x.now = T0
    run_daily(now=T0, clock=lambda: T0 + RUN, raw_dir=env.raw, out_dir=env.out,
              report_path=env.report, families_fn=lambda _p, top_n: FAMS,
              extract_fn=x, notify=lambda _t: True)
    assert (env.out / "daily" / "state.json").exists()
    assert (env.out / "daily" / ".lock").exists()


# ── the CLI, the notification and the launchd files ─────────────────────────

@pytest.mark.parametrize("flags,exit_code", [([], 1), (["--notify"], 1)])
def test_cmd_sam_daily_prints_one_line_and_exits_by_status(monkeypatch, capsys,
                                                           flags, exit_code):
    seen = {}

    def fake_run(**kw):
        seen.update(kw)
        return Outcome("blocked", "no key", at="2026-09-27T12:17:00+00:00",
                       note="SAM daily is blocked (owner action): no key")
    monkeypatch.setattr(sam_daily, "run_daily", fake_run)
    with pytest.raises(SystemExit) as exc:
        cli.main(["sam", "daily", *flags])
    assert exc.value.code == exit_code
    out = capsys.readouterr().out
    assert "sam daily 2026-09-27T12:17:00+00:00: blocked — no key" in out
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
    assert seen["args"][-1] == body and seen["args"][0] == "osascript"
    assert all(body not in a for a in seen["args"][:-1])      # never in the source

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
    assert plist["StandardOutPath"] == f"{tmp_path}/logs/sam-daily.out.log"
    assert plist["StandardErrorPath"] == f"{tmp_path}/logs/sam-daily.err.log"
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
