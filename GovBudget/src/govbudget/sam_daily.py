"""The unattended driver for the SAM.gov extract — what launchd runs hourly.

ROADMAP #10, SAM-extract half. This module decides WHEN to ask SAM and how
much, so a scheduled job neither exceeds the key's quota nor loses a day to
one transient failure (the 2026-09-27 run stored one registration, then SAM's
60 s read timeout ended it). WHAT it asks — batched requests, three queries
per UEI, a ladder of request shapes proven by a control UEI — is
`sam_batch`'s; each tick loops over `sam_batch.fetch_batch` until the
budget is spent or nothing is owed. `govbudget sam daily` is the command;
scripts/launch/sam_daily.sh is the launchd entry point;
docs/superpowers/LAUNCH.md Step 11b installs it.

THE QUOTA RULE. https://open.gsa.gov/api/entity-api/ publishes 10 requests a
day for a key with no SAM.gov role and does not say when the day resets (read
2026-09-27). The limiter is rolling: at most DAILY_QUOTA requests in any
trailing 24 hours. That also holds any UTC day to DAILY_QUOTA, and any US
Eastern day but the 25-hour one in November. Requests are counted from three
ledgers, all in the shared lake beside the extract's output:
`downloaded_at` in data/parquet/sam/manifest.jsonl (every stored answer, at
its real time), data/parquet/sam/preflight_probes.jsonl (every `sam
preflight` request, stamped once it was answered or failed), and this
driver's own `failed_requests` (a request that stored nothing, stamped when
the run ends, or — for a run killed mid-request — INFLIGHT_MAX after it
began). None of them sees a failed request of a hand-run `sam extract`;
SAM's 429 is the backstop for that, and it stops a run without losing a
stored body.

ONE BATCH A DAY. A run starts only when the requests the families still owed
need are free (all 10 until the last day), so each day's requests go out
together. The exception is a retry: after SAM fails mid-batch, what is left of
that batch's 24 hours is spent two hours later rather than abandoned. A batch
that timed out is asked again at half its size, down to one UEI a request;
families are tried in order of how often they have failed (fewest first,
then published order), and one that has failed alone in DEFER_AFTER daily
batches is `stuck` once nothing else is owed. A proof of an unproven request
shape never carries a family that has timed out, and two unanswered proofs
in a row step the shape down.

HOURLY TICKS. launchd runs this every hour. A tick that decides to wait
exits without opening the DuckDB lake — unless the wait ends within
SLEEP_MAX, when it sleeps and runs, so the daily batch does not slip an hour
each day behind the ticks.
"""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import duckdb

import httpx

from govbudget import config
from govbudget import sam_batch
from govbudget import sam_entities as sam
from govbudget.manifest import load_records

DAILY_QUOTA = sam.DEFAULT_MAX_REQUESTS
WINDOW = timedelta(hours=24)
#: How long each outcome waits before the next attempt. A status not listed
#: here retries on the next tick.
BACKOFF = {
    "sam_unavailable": timedelta(hours=2),
    # SAM counted more than the ledgers did (a failed preflight, a hand
    # run's failed request): only a full window is sure to clear what it saw.
    "rate_limited": timedelta(hours=24),
    "error": timedelta(hours=6),
    "sam_refused": timedelta(hours=24),
    "shape_error": timedelta(hours=24),
    "stuck": timedelta(hours=24),
    "corrupt_state": timedelta(hours=24),
    "complete": timedelta(hours=24),
}
#: A wait that ends this soon is slept through, not left to the next tick.
SLEEP_MAX = timedelta(minutes=5)
#: A run killed mid-request is charged one request this long after it began:
#: 10 requests x (1 s floor + 60 s timeout), rounded up.
INFLIGHT_MAX = timedelta(minutes=12)
#: Batches (not requests: a few hours' outage is one batch) a registration
#: must fail in before, with nothing else left, the driver calls it stuck.
DEFER_AFTER = 3
#: Statuses that say nothing until they have lasted QUIET_FOR.
QUIET = frozenset({"lake_busy", "offline"})
QUIET_FOR = timedelta(hours=6)
NOTIFY_EVERY = timedelta(hours=24)
HISTORY_KEEP = 90
#: Statuses that exit non-zero: each needs a person, not another tick.
FAILING = frozenset({"blocked", "sam_refused", "shape_error", "stuck",
                     "corrupt_state", "error"})
NOTIFY_TITLE = "Fiscal Receipts · SAM daily"


@dataclass
class Outcome:
    status: str
    message: str
    fetched: int = 0
    failed: int = 0
    missing: int | None = None
    budget: int | None = None
    #: True once the extract was called, i.e. requests may have been spent.
    ran: bool = False
    #: True when this run was the retry of a failed batch.
    retry: bool = False
    #: When a `waiting` outcome could next go.
    wake_at: datetime | None = None
    #: Days of quota the families still owed need, at the mode's pace.
    days_left: int | None = None
    #: Requests this tick sent to SAM (answered or not).
    sent: int = 0
    at: str = ""
    note: str | None = None
    notified: bool = False

    @property
    def exit_code(self) -> int:
        return 1 if self.status in FAILING else 0


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _parse_or_none(value) -> datetime | None:
    try:
        return _parse(value)
    except (TypeError, ValueError, AttributeError):
        return None


def load_state(path: Path, now: datetime) -> dict:
    """The driver's state, or a fresh one.

    A file that no longer parses is moved aside under a new timestamped name
    (never overwritten, never deleted) and the returned state carries
    `_corrupt`, which `run_daily` turns into a `corrupt_state` outcome: a
    notice, exit 1 and a full day's backoff, because the failed-request
    stamps the file held are gone and only a day's wait guarantees they have
    rolled off.
    """
    if not path.exists():
        return {}
    try:
        state = json.loads(path.read_text())
        if isinstance(state, dict):
            return state
    except (OSError, ValueError):
        pass
    aside = path.with_name(
        f"{path.name}.corrupt-{now.strftime('%Y%m%dT%H%M%SZ')}")
    path.replace(aside)
    return {"_corrupt": aside.name}


def _peek_state(path: Path) -> dict:
    """`load_state` for --check: reads, never moves or writes anything."""
    if not path.exists():
        return {}
    try:
        state = json.loads(path.read_text())
        if isinstance(state, dict):
            return state
    except (OSError, ValueError):
        pass
    return {"_corrupt": path.name}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def requests_in_window(now: datetime, manifest_path: Path, state: dict,
                       probes_path: Path | None = None) -> list[datetime]:
    """Every request of the trailing 24 hours that a ledger records, oldest
    first. A stamp later than `now` (a clock that moved backwards) counts
    too: erring high is the safe direction for a quota."""
    stamps = [
        _parse(rec.downloaded_at) for rec in load_records(manifest_path)
        if rec.dataset == "sam_entities" and rec.downloaded_at
    ]
    stamps += [t for t in map(_parse_or_none, state.get("failed_requests", []))
               if t is not None]
    if probes_path is not None and probes_path.exists():
        for line in probes_path.read_text().splitlines():
            if line.strip():
                stamps.append(_parse(json.loads(line)["at"]))
    return sorted(t for t in stamps if t > now - WINDOW)


def _acquire_lock(lock_path: Path):
    """Non-blocking exclusive `flock`, the `refresh._acquire_single_instance_lock`
    pattern: launchd never starts a second copy of one label, but a hand-run
    `sam daily` beside a scheduled one would otherwise count the same free
    quota twice. Returns the handle (closing it releases the lock) or None."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = os.fdopen(os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644), "r+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(f"{os.getpid()}\n")
    handle.flush()
    return handle


def _parquet_stale(out_dir: Path, raw_dir: Path) -> bool:
    """True when a stored answer is newer than the parquet built from them —
    the rebuild failed (`extract_entities` prints why and returns None; `sam
    reparse` raises it). The fix is the owner's, and nothing is lost: the
    bodies are kept."""
    bodies = (list(raw_dir.glob("*.json"))
              + list((raw_dir / sam_batch.BATCH_DIR).glob("*.json")))
    if not bodies:
        return False
    parquet = out_dir / "entities.parquet"
    if not parquet.exists():
        return True
    return parquet.stat().st_mtime < max(b.stat().st_mtime for b in bodies)


def _scrub(text: str, key: str | None) -> str:
    key = key or os.environ.get("SAM_API_KEY")
    return text.replace(key, "…") if key else text


def notification_for(outcome: Outcome, state: dict, now: datetime) -> str | None:
    """The one line a person is shown for this outcome, or None to stay quiet.

    Progress speaks once per batch. `complete` speaks once until something
    goes missing again. A QUIET status (a busy lake, no network) speaks once,
    and only after it has lasted QUIET_FOR. Any other failure speaks at most
    once per NOTIFY_EVERY for the same status, however many ticks repeat it.
    """
    s = outcome.status
    if s in ("waiting", "already_running", "check"):
        return None
    if s == "fetched":
        return (f"Stored {outcome.fetched} SAM answer(s); {outcome.missing} "
                f"families left (~{outcome.days_left or 1} more day(s)).")
    if s == "complete":
        if state.get("complete_notified"):
            return None
        return ("Every published family's SAM answer is stored. It reaches "
                "the site at the next export and deploy.")
    if s in QUIET:
        since = _parse_or_none(state.get("since", {}).get(s))
        if (since is None or now - since < QUIET_FOR
                or s in state.get("episode_notified", [])):
            return None
        hours = int(QUIET_FOR.total_seconds() // 3600)
        return {
            "lake_busy": "Another process has held the DuckDB lake's write "
                         f"lock for over {hours} hours; the SAM run waits.",
            "offline": f"SAM has been unreachable for over {hours} hours "
                       "(no network?); nothing was spent.",
        }[s]
    last = _parse_or_none(state.get("notified", {}).get(s))
    if last is not None and now - last < NOTIFY_EVERY:
        return None
    lead = {
        "sam_unavailable": "SAM did not answer",
        "rate_limited": "SAM says the day's quota is used up",
        "blocked": "SAM daily is blocked (owner action)",
        "sam_refused": "SAM refused the key (owner action)",
        "shape_error": "A SAM answer is unusable (owner action)",
        "stuck": "SAM keeps failing on the last registrations (owner action)",
        "corrupt_state": "SAM daily's state file was damaged (check it)",
        "error": "SAM daily failed",
    }.get(s, s)
    stored = f" after storing {outcome.fetched}" if outcome.fetched else ""
    return f"{lead}{stored}: {outcome.message.splitlines()[0][:180]}"


def notify_macos(body: str, *, title: str = NOTIFY_TITLE) -> bool:
    """Post a macOS notification; never raise. The text travels as argv, not
    spliced into AppleScript source, so no message can break the quoting."""
    try:
        r = subprocess.run(
            ["osascript", "-e", "on run argv",
             "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
             "-e", "end run", title, body],
            capture_output=True, timeout=15, check=False)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class _CorruptState(Exception):
    pass


def run_daily(*, now: datetime | None = None, state_dir: Path | None = None,
              raw_dir: Path | None = None, out_dir: Path | None = None,
              report_path: Path | None = None, duckdb_path: Path | None = None,
              top_n: int = 200, check: bool = False,
              families_fn: Callable | None = None,
              fetch_fn: Callable | None = None,
              client=None,
              notify: Callable[[str], bool] | None = None,
              clock: Callable[[], datetime] | None = None,
              sleep: Callable[[float], None] = time.sleep) -> Outcome:
    """One tick. Returns the outcome, with the notification text in `note`.

    `notify` posts it (the launchd wrapper passes `--notify`); a note is
    remembered as said only when `notify` delivered it, so a hand run without
    `--notify` never silences the scheduled job. `check=True` runs every
    check and reads the lake, then says what a real tick would do — no lock,
    no request, no write, no notification. `clock` and `sleep` are the
    tests' seams; `now` is the decision time.
    """
    clock = clock or (lambda: datetime.now(timezone.utc))
    now = now or clock()
    out_dir = Path(out_dir or config.PARQUET_DIR / "sam")
    # Beside the manifest, inside the shared lake: every checkout (a worktree
    # included) spends the same key's quota, so all share one lock and one
    # failed-request ledger.
    state_dir = Path(state_dir or out_dir / "daily")
    raw_dir = Path(raw_dir or config.RAW_DIR / "sam")
    report_path = Path(report_path or
                       config.RESEARCH_DIR / "sam_entities" / "preflight.json")
    paths = dict(raw_dir=raw_dir, out_dir=out_dir, report_path=report_path,
                 probes_path=out_dir / sam.PREFLIGHT_PROBES,
                 duckdb_path=duckdb_path or config.DUCKDB_PATH,
                 manifest_path=out_dir / "manifest.jsonl", top_n=top_n,
                 families_fn=families_fn or sam.dominant_parent_ueis,
                 fetch_fn=fetch_fn or sam_batch.fetch_batch, client=client,
                 clock=clock)
    state_path = state_dir / "state.json"

    lock = None
    if not check:
        lock = _acquire_lock(state_dir / ".lock")
        if lock is None:
            return Outcome("already_running", "another `sam daily` holds the "
                           "lock", at=_iso(now))
    try:
        state = _peek_state(state_path) if check else load_state(state_path, now)

        def persist() -> None:
            if not check:
                save_state(state_path, state)

        key = None
        try:
            if "_corrupt" in state:
                # Its failed-request stamps are gone; only a day's wait
                # guarantees they have rolled off.
                aside = state.pop("_corrupt")
                raise _CorruptState(
                    "state.json does not parse; a real tick would keep it "
                    "aside and back off 24 hours" if check else
                    f"state.json did not parse; kept it as {aside}. The "
                    "requests it recorded are unknown, so backing off 24 "
                    "hours")
            outcome, key = _tick(now, state, check=check, persist=persist,
                                 **paths)
            wait = (outcome.wake_at - now) if outcome.wake_at else None
            if (not check and outcome.status == "waiting" and wait is not None
                    and timedelta(0) < wait <= SLEEP_MAX):
                sleep(wait.total_seconds() + 1)
                now = max(clock(), outcome.wake_at + timedelta(seconds=1))
                outcome, key = _tick(now, state, check=check,
                                     persist=persist, **paths)
        except _CorruptState as e:
            outcome = Outcome("check" if check else "corrupt_state", str(e))
        except Exception as e:  # recorded and reported, never swallowed
            print(_scrub(traceback.format_exc(), key), file=sys.stderr)
            outcome = Outcome("error", f"{type(e).__name__}: {e}")
            state.pop("inflight", None)
        outcome.message = _scrub(outcome.message, key)
        outcome.at = _iso(now)
        if not check:
            outcome.note = notification_for(outcome, state, now)
            if outcome.note and notify is not None:
                outcome.notified = bool(notify(outcome.note))
            _record(state, outcome, now)
            persist()
        return outcome
    finally:
        if lock is not None:
            lock.close()


def _tick(now, state, *, check, persist, raw_dir, out_dir, report_path,
          probes_path, duckdb_path, manifest_path, top_n, families_fn,
          fetch_fn, client, clock):
    """The decision and, when it says go, the run. Returns (Outcome, key)."""
    # 0. A run killed mid-request (launchd's SIGTERM at logout or shutdown)
    #    left its marker: charge the request that was in flight.
    inflight = _parse_or_none(state.pop("inflight", None))
    if inflight is not None:
        state.setdefault("failed_requests", []).append(
            _iso(inflight + INFLIGHT_MAX))
        print("sam daily: the previous run was killed mid-batch; charged one "
              "request to the quota for it")

    # 1. Offline and free: the credential and the stored preflight report.
    #    Checked every tick, so a broken .env surfaces within the hour.
    try:
        key = sam.require_api_key()
        report = sam.require_preflight(report_path)
    except (sam.SamAuthError, sam.SamShapeError) as e:
        return Outcome("blocked", str(e)), None
    except (ValueError, OSError) as e:      # an unreadable preflight report
        return Outcome("blocked", f"the preflight report does not read: "
                       f"{type(e).__name__}: {e}"), None

    # 2. The rolling quota, the retry window and any backoff — still without
    #    opening the lake.
    used = requests_in_window(now, manifest_path, state, probes_path)
    budget = max(DAILY_QUOTA - len(used), 0)
    known_missing = state.get("missing")
    per_request = (sam_batch.BATCH_SIZE if (state.get("mode") or
                   sam_batch.MODES[0]).startswith("batch") else 1)
    need = (min(DAILY_QUOTA, -(-known_missing // per_request))
            if known_missing else DAILY_QUOTA)
    retry_until = _parse_or_none(state.get("retry_until"))
    retrying = bool(state.get("retry_pending")) and bool(
        retry_until and now < retry_until)
    if state.get("retry_pending") and not retrying:
        state["retry_pending"] = False      # its batch's 24 hours are over
    retry_after = _parse_or_none(state.get("retry_after"))
    wait, wake_at = None, None
    if retry_after and now < retry_after:
        wait, wake_at = (f"backing off until {_iso(retry_after)} (after "
                         f"{state.get('last_status')})"), retry_after
    elif retrying and budget == 0 and used[0] + WINDOW < retry_until:
        wake_at = used[0] + WINDOW
        wait = (f"retrying the failed batch once a request rolls off at "
                f"{_iso(wake_at)}")
    elif budget < need and not (retrying and budget > 0):
        # (A retry whose next free request would come after its batch's 24
        # hours is over is no retry: the batch rule decides.)
        # `need` are free once the oldest len(used) - (QUOTA - need) stamps
        # have rolled off; the last of those sets the time.
        wake_at = used[len(used) - (DAILY_QUOTA - need) - 1] + WINDOW
        wait = (f"{budget} of {DAILY_QUOTA} request(s) free in the trailing "
                f"24 h; {need} needed from {_iso(wake_at)}")
    if wait and not check:
        return Outcome("waiting", wait, budget=budget, missing=known_missing,
                       wake_at=wake_at), key

    # 3. The published families — the first read of the shared lake.
    try:
        families = families_fn(duckdb_path, top_n=top_n)
    except duckdb.IOException as e:
        first = str(e).splitlines()[0]
        low = first.lower()
        if "could not set lock" in low or "conflicting lock" in low:
            return Outcome("lake_busy", f"the lake is write-locked: {first}",
                           budget=budget), key
        if "no files found that match the pattern" in low:
            first += (" — the lake's views name a path that is gone; run "
                      "`uv run python -m govbudget build` from the main "
                      "checkout")
        print(_scrub(traceback.format_exc(), key), file=sys.stderr)
        return Outcome("error", f"reading the published families failed: "
                       f"{first}", budget=budget), key
    if not families:
        return Outcome("error", "the lake returned no published families — "
                       "refusing to call that complete", budget=budget), key
    mode = state.get("mode") or sam_batch.MODES[0]
    answers = sam_batch.resolve_answers(
        raw_dir, out_dir, integrity=mode.endswith("+integrity"))
    missing = sam_batch.pending(families, answers)
    if check:
        verdict = (f"a real tick would wait: {wait}" if wait else
                   f"a real tick would ask about {len(missing)} "
                   f"famil(ies) with up to {budget} request(s) now")
        return Outcome("check", f"{len(missing)} of {len(families)} published "
                       f"families owed an answer; {budget} of {DAILY_QUOTA} "
                       f"request(s) free; mode {mode}"
                       f"{'' if state.get('mode_verified') else ' (unproven)'}; "
                       f"{verdict}; endpoint {report['endpoint']}",
                       missing=len(missing), budget=budget), key
    if not missing and _unreadable(families, answers):
        return Outcome("shape_error", "stored answer(s) do not read: "
                       f"{'; '.join(_unreadable(families, answers)[:3])} — fix "
                       "the reader, then `uv run python -m govbudget sam "
                       "reparse`", missing=0, budget=budget), key
    if not missing:
        if _parquet_stale(out_dir, raw_dir):
            return Outcome("shape_error", "every answer is stored but "
                           "entities.parquet is older than the newest one: "
                           "run `uv run python -m govbudget sam reparse` to "
                           "see why", missing=0, budget=budget), key
        return Outcome("complete", f"all {len(families)} published families "
                       "have a stored SAM answer", missing=0,
                       budget=budget), key

    # 4. The run: batched requests, one query stage at a time, until the
    #    budget is spent or nothing is owed. Registrations are tried
    #    fewest-failed-batches first, so one SAM always fails on can starve
    #    nothing behind it. A marker is saved before EACH request so a run
    #    killed mid-request is still charged for it.
    batch_id = (state.get("retry_until") if retrying
                else _iso(now + WINDOW))       # what _record will stamp
    failures = state.setdefault("uei_failures", {})
    timeouts = state.setdefault("batch_timeouts", {})

    def score(f) -> int:
        rec = failures.get(f[1]) or {}
        return (rec.get("batches", 0) + (rec.get("last_batch") == batch_id)
                + timeouts.get(f[1], 0))
    ordered = sorted(families, key=score)   # stable: published order within
    before = _settled(families, answers)
    spent = failed = 0
    ueis, control = [], None
    notes: list[str] = []
    status, message, failed_uei = "fetched", "", None
    client = client or httpx.Client(
        headers={"User-Agent": sam._USER_AGENT}, timeout=60,
        follow_redirects=True)
    try:
        while spent < budget:
            mode = state.get("mode") or sam_batch.MODES[0]
            verified = bool(state.get("mode_verified")) or mode == "single"
            answers = sam_batch.resolve_answers(
                raw_dir, out_dir, integrity=mode.endswith("+integrity"))
            owed = sam_batch.pending(ordered, answers)
            if not owed:
                break
            ueis, stage, control = _next_request(
                owed, answers, mode=mode, verified=verified, timeouts=timeouts)
            state["inflight"] = _iso(max(clock(), now))
            persist()
            try:
                result = fetch_fn(client, api_key=key, endpoint=report["endpoint"],
                                  ueis=ueis, stage=stage, mode=mode,
                                  raw_dir=raw_dir, out_dir=out_dir,
                                  control=control, clock=clock)
            except sam_batch.SamQueryRejectedError as e:
                if verified:
                    raise                       # a real shape_error, below
                spent += 1                      # a probe SAM refused: next rung
                failed += 1
                _stamp_failed(state, clock, now)
                notes.append(_advance_mode(state, mode, f"SAM refused it: {e}"))
                continue
            except sam_batch.SamStoredBodyError as e:
                # Paid for, stored and on the ledger (its manifest line), so
                # never stamped again; its UEIs are `unreadable`, not re-asked.
                # The other families carry on; the status says so at the end.
                spent += 1
                notes.append(f"unreadable answer {e.file}")
                continue
            finally:
                state.pop("inflight", None)
            spent += 1
            for u in result.found:
                timeouts.pop(u, None)
            if control is None and not verified:
                state["mode"], state["mode_verified"] = mode, True  # a 200 proves a single mode
                notes.append(f"mode {mode} proven")
            elif control is not None:
                if result.honoured:
                    state["mode"], state["mode_verified"] = mode, True
                    state.pop("proof_failures", None)
                    notes.append(f"mode {mode} proven: SAM answered the "
                                 "bracketed request")
                elif result.honoured is False:
                    notes.append(_advance_mode(
                        state, mode, "a complete page held none of the UEIs "
                        "asked, so SAM did not honour the batch"))
                else:
                    notes.append(f"mode {mode} not yet proven (a full page)")
    except sam.SamRateLimitError as e:
        status, message, failed, spent = "rate_limited", str(e), failed + 1, spent + 1
    except sam.SamOfflineError as e:
        status, message = "offline", str(e)          # nothing was sent
    except sam.SamUnavailableError as e:
        status, message, failed, spent = "sam_unavailable", str(e), failed + 1, spent + 1
        if control is not None:
            # A proof SAM did not answer: twice in a row and the shape itself
            # is suspect (SAM may 5xx what it will not honour), so step down.
            state["proof_failures"] = state.get("proof_failures", 0) + 1
            if state["proof_failures"] >= 2:
                state.pop("proof_failures", None)
                notes.append(_advance_mode(
                    state, state.get("mode") or sam_batch.MODES[0],
                    "SAM did not answer its proof twice"))
        if e.uei and control is None:
            failed_uei = e.uei                   # a single request: that UEI
        for u in ueis:                           # a batch: halve its size next time
            if u != control and len(ueis) > 1:
                timeouts[u] = timeouts.get(u, 0) + 1
    except sam.SamAuthError as e:
        status, message, failed, spent = "sam_refused", str(e), failed + 1, spent + 1
    except sam.SamShapeError as e:
        status, message, failed, spent = "shape_error", str(e), failed + 1, spent + 1
    except Exception as e:  # recorded and reported, never swallowed
        print(_scrub(traceback.format_exc(), key), file=sys.stderr)
        status, message, failed, spent = ("error", f"{type(e).__name__}: {e}",
                                          failed + 1, spent + 1)
    finally:
        state.pop("inflight", None)
    if status not in ("fetched", "offline"):
        # The request that raised: stamped at the END of the run, never
        # earlier than the request. (A 400 during mode probing was stamped
        # where it happened.)
        _stamp_failed(state, clock, now)
    try:
        sam_batch.rebuild(raw_dir, out_dir, integrity=(
            state.get("mode") or sam_batch.MODES[0]).endswith("+integrity"))
    except Exception as e:  # the answers are stored; only the parquet is late
        print(_scrub(traceback.format_exc(), key), file=sys.stderr)
        if status == "fetched":
            status = "shape_error"
            message = (f"the answers are stored but the parquet rebuild "
                       f"failed ({type(e).__name__}: {e}); run `uv run python "
                       "-m govbudget sam reparse` to see why")
    mode = state.get("mode") or sam_batch.MODES[0]
    answers = sam_batch.resolve_answers(raw_dir, out_dir,
                                        integrity=mode.endswith("+integrity"))
    still = sam_batch.pending(families, answers)
    fetched = _settled(families, answers) - before
    answered = {u for _, u in families} - {u for _, u in still}
    for uei in [u for u in failures if u in answered]:
        del failures[uei]
    for uei in [u for u in timeouts if u in answered]:
        del timeouts[uei]
    if failed_uei:
        rec = failures.setdefault(failed_uei, {"batches": 0, "last_batch": None})
        if rec["last_batch"] != batch_id:   # one count per batch, not per retry
            rec["batches"] += 1
            rec["last_batch"] = batch_id
        if still and all((failures.get(u) or {}).get("batches", 0) >= DEFER_AFTER
                         for _, u in still):
            status = "stuck"
            message = (f"every family still owed an answer "
                       f"({', '.join(u for _, u in still)}) has failed in "
                       f"{DEFER_AFTER}+ daily batches; SAM did not answer for "
                       f"{failed_uei} this time. The driver keeps trying them, "
                       f"fewest failures first, once a day. {message}")
    unreadable = _unreadable(families, answers)
    if status == "fetched" and _parquet_stale(out_dir, raw_dir):
        status, message = "shape_error", (
            "entities.parquet was not rebuilt after this run's answers were "
            "stored: run `uv run python -m govbudget sam reparse` to see why")
    elif status == "fetched" and unreadable:
        status, message = "shape_error", (
            f"{len(unreadable)} stored answer(s) do not read — fix the reader, "
            f"then `uv run python -m govbudget sam reparse`: "
            f"{'; '.join(unreadable[:3])}")
    elif status == "fetched":
        if not still:
            status = "complete"
        kinds = _kind_counts(answers, families)
        message = (f"answered {fetched} famil(ies) in {spent} request(s) "
                   f"({kinds}); {len(still)} of {len(families)} still owed")
    if notes:
        message = f"{message} [{'; '.join(notes)}]"
    per_day = DAILY_QUOTA * (sam_batch.BATCH_SIZE if mode.startswith("batch")
                             else 1)
    return Outcome(status, message, fetched=fetched, failed=failed,
                   missing=len(still), budget=budget, ran=True, sent=spent,
                   retry=retrying, days_left=-(-len(still) // per_day)), key


def _next_request(owed, answers, *, mode, verified, timeouts):
    """(ueis, stage, control) for the next request: the earliest query stage
    anything is owed, its families in order, as many as the mode, the
    control's slot and each family's timeout history allow. A family a page
    left unresolved, or one that timed out 3+ times in batches, goes alone."""
    batch = mode.startswith("batch")
    control = sam_batch.CONTROL_UEI if (batch and not verified) else None
    stages = ("registered",) if control else sam_batch.STAGES
    for stage in stages:
        todo = [u for _, u in owed if sam_batch.next_stage(u, answers) == stage
                and u != control
                # a proof never carries a family that has timed out: if the
                # proof fails, it must be the shape, not that family
                and not (control and timeouts.get(u))]
        if todo:
            break
    else:
        # Unproven batch mode and no family fit to prove it with: prove it
        # with the control and CONTROL_PAIR (fetch_batch adds the pair), a
        # real bracketed request, before anything else rides on it.
        return [], "registered", control

    def cap(u) -> int:
        if not batch or (answers.get(u) or {}).get("unresolved"):
            return 1
        return max(1, sam_batch.BATCH_SIZE >> timeouts.get(u, 0))
    slot = 1 if control else 0                  # the control rides along
    chosen: list[str] = []
    for u in todo:
        if len(chosen) + 1 + slot > max(min(cap(x) for x in chosen + [u]), 1 + slot):
            break
        chosen.append(u)
    return chosen, stage, control


_SETTLED = frozenset({"registered", "id_assigned", "opted_out", "not_public"})


def _settled(families, answers) -> int:
    """Families with an answer that reads (not pending, not unreadable)."""
    return sum(1 for _, u in families
               if (answers.get(u) or {}).get("kind") in _SETTLED)


def _unreadable(families, answers) -> list[str]:
    return [(answers.get(u) or {}).get("why", u) for _, u in families
            if (answers.get(u) or {}).get("kind") == "unreadable"]


def _advance_mode(state: dict, mode: str, why: str) -> str:
    modes = sam_batch.MODES
    nxt = modes[min(modes.index(mode) + 1, len(modes) - 1)]
    state["mode"], state["mode_verified"] = nxt, nxt == "single"
    return f"mode {mode} dropped ({why}); now {nxt}"


def _stamp_failed(state: dict, clock, now: datetime) -> None:
    state.setdefault("failed_requests", []).append(_iso(max(clock(), now)))


def _kind_counts(answers: dict, families) -> str:
    counts: dict[str, int] = {}
    for _, u in families:
        k = (answers.get(u) or {}).get("kind", "pending")
        if k != "pending":
            counts[k] = counts.get(k, 0) + 1
    return ", ".join(f"{k} {n}" for k, n in sorted(counts.items())) or "none yet"


def _record(state: dict, outcome: Outcome, now: datetime) -> None:
    """Fold one tick into the state (`_tick` keeps `failed_requests`,
    `uei_failures` and `retry_pending`'s expiry itself)."""
    s = outcome.status
    state["last_tick_at"] = _iso(now)
    if s in ("waiting", "already_running"):
        return
    state["last_status"] = s
    state["last_message"] = outcome.message
    if outcome.missing is not None:
        state["missing"] = outcome.missing
    backoff = BACKOFF.get(s)
    if backoff:
        state["retry_after"] = _iso(now + backoff)
    elif outcome.ran:
        state["retry_after"] = None
    # else: a tick that never reached SAM (blocked, lake_busy) leaves any
    # standing backoff alone.
    if outcome.ran:
        # A failure mid-batch leaves quota worth a retry, for that batch's
        # 24 hours; a clean batch, a completed extract or a refusal ends it.
        # An `offline` run that stored nothing sent nothing: it starts no
        # batch, so it neither opens a retry window nor closes one.
        started = not (s == "offline" and outcome.sent == 0)
        if started and not outcome.retry:
            state["retry_until"] = _iso(now + WINDOW)
        if started or outcome.retry:
            state["retry_pending"] = s in ("sam_unavailable", "error", "offline")
    elif s == "complete":
        state["retry_pending"] = False
    # QUIET statuses: when the episode began, and whether it has spoken.
    since = state.setdefault("since", {})
    for q in [q for q in since if q != s]:
        del since[q]
    if s in QUIET:
        since.setdefault(s, _iso(now))
    state["episode_notified"] = [q for q in state.get("episode_notified", [])
                                 if q == s]
    if s == "complete":
        state["complete_notified"] = (outcome.notified
                                      or state.get("complete_notified", False))
    elif outcome.missing:
        state["complete_notified"] = False
    if outcome.notified:
        state.setdefault("notified", {})[s] = _iso(now)
        if s in QUIET:
            state["episode_notified"] = [s]
    cutoff = now - 2 * WINDOW
    state["failed_requests"] = [
        t for t in state.get("failed_requests", [])
        if (p := _parse_or_none(t)) is not None and p > cutoff]
    if s not in QUIET:
        history = state.setdefault("history", [])
        history.append({"at": _iso(now), "status": s, "fetched": outcome.fetched,
                        "failed": outcome.failed, "missing": outcome.missing,
                        "budget": outcome.budget})
        del history[:-HISTORY_KEEP]
