"""The unattended driver for the SAM.gov extract — what launchd runs hourly.

ROADMAP #10, SAM-extract half. `sam extract` fetches up to 10 registrations
and stops; this module decides WHEN to call it, so a scheduled job neither
exceeds the key's quota nor loses a day to one transient failure (the
2026-09-27 run stored one registration, then SAM's 60 s read timeout ended
it). `govbudget sam daily` is the command; scripts/launch/sam_daily.sh is the
launchd entry point; docs/superpowers/LAUNCH.md Step 11b installs it.

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

ONE BATCH A DAY. A run starts only when the full quota is free (or the
families still missing fit in what is free), so each day's requests go out
together. The exception is a retry: after SAM fails mid-batch, what is left of
that batch's 24 hours is spent two hours later rather than abandoned, with the
registration that failed moved behind the rest. Registrations are tried in
order of how many batches they have failed in (fewest first, then published
order); one that has failed in DEFER_AFTER batches is `stuck` once nothing
else is left.

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

from govbudget import config
from govbudget import sam_entities as sam
from govbudget.manifest import load_records

DAILY_QUOTA = sam.DEFAULT_MAX_REQUESTS
WINDOW = timedelta(hours=24)
#: How long each outcome waits before the next attempt. A status not listed
#: here retries on the next tick.
BACKOFF = {
    "sam_unavailable": timedelta(hours=2),
    "rate_limited": timedelta(hours=6),
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


def _missing(families, raw_dir: Path) -> list[tuple[str, str]]:
    return [f for f in families if not (raw_dir / f"{f[1]}.json").exists()]


def _parquet_stale(out_dir: Path, raw_dir: Path) -> bool:
    """True when a stored answer is newer than the parquet built from them —
    the rebuild failed (`extract_entities` prints why and returns None; `sam
    reparse` raises it). The fix is the owner's, and nothing is lost: the
    bodies are kept."""
    bodies = list(raw_dir.glob("*.json"))
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
        days = -(-outcome.missing // DAILY_QUOTA) if outcome.missing else 0
        return (f"Stored {outcome.fetched} SAM answer(s); {outcome.missing} "
                f"families left (~{days} more batch(es), one a day).")
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
              extract_fn: Callable | None = None,
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
                 extract_fn=extract_fn or sam.extract_entities, clock=clock)
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
          extract_fn, clock):
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
    need = min(DAILY_QUOTA, known_missing) if known_missing else DAILY_QUOTA
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
    missing = _missing(families, raw_dir)
    if check:
        verdict = (f"a real tick would wait: {wait}" if wait else
                   f"a real tick would fetch {min(budget, len(missing))} now")
        return Outcome("check", f"{len(missing)} of {len(families)} published "
                       f"families missing; {budget} of {DAILY_QUOTA} "
                       f"request(s) free; {verdict}; endpoint "
                       f"{report['endpoint']}", missing=len(missing),
                       budget=budget), key
    if not missing:
        if _parquet_stale(out_dir, raw_dir):
            return Outcome("shape_error", "every answer is stored but "
                           "entities.parquet is older than the newest one: "
                           "run `uv run python -m govbudget sam reparse` to "
                           "see why", missing=0, budget=budget), key
        return Outcome("complete", f"all {len(families)} published families "
                       "have a stored SAM answer", missing=0,
                       budget=budget), key

    # 4. The run. Registrations are tried fewest-failed-batches first, so one
    #    SAM always fails on can starve nothing behind it (a registration
    #    that failed earlier in THIS batch counts as one more). The marker is
    #    saved first so a run killed mid-request is still charged for it.
    batch = (state.get("retry_until") if retrying
             else _iso(now + WINDOW))       # what _record will stamp
    failures = state.setdefault("uei_failures", {})

    def score(f) -> int:
        rec = failures.get(f[1]) or {}
        return rec.get("batches", 0) + (rec.get("last_batch") == batch)
    ordered = sorted(families, key=score)   # stable: published order within
    before = len(missing)
    state["inflight"] = _iso(now)
    persist()
    status, message, failed = "fetched", "", 0
    failed_uei = None
    try:
        extract_fn(ordered, api_key=key, out_dir=out_dir, raw_dir=raw_dir,
                   max_requests=budget, endpoint=report["endpoint"])
    except sam.SamRateLimitError as e:
        status, message, failed = "rate_limited", str(e), 1
    except sam.SamOfflineError as e:
        status, message = "offline", str(e)          # nothing was sent
    except sam.SamUnavailableError as e:
        status, message, failed = "sam_unavailable", str(e), 1
        failed_uei = e.uei
    except sam.SamAuthError as e:
        status, message, failed = "sam_refused", str(e), 1
    except sam.SamShapeError as e:
        status, message, failed = "shape_error", str(e), 1
    except Exception as e:  # recorded and reported, never swallowed
        print(_scrub(traceback.format_exc(), key), file=sys.stderr)
        status, message, failed = "error", f"{type(e).__name__}: {e}", 1
    finally:
        state.pop("inflight", None)
    if failed:
        # Stamped at the END of the run: never earlier than the request.
        state.setdefault("failed_requests", []).append(_iso(max(clock(), now)))
    still = _missing(families, raw_dir)
    fetched = before - len(still)
    stored = {u for _, u in families} - {u for _, u in still}
    for uei in [u for u in failures if u in stored]:
        del failures[uei]
    if failed_uei:
        rec = failures.setdefault(failed_uei, {"batches": 0, "last_batch": None})
        if rec["last_batch"] != batch:      # one count per batch, not per retry
            rec["batches"] += 1
            rec["last_batch"] = batch
        if all((failures.get(u) or {}).get("batches", 0) >= DEFER_AFTER
               for _, u in still):
            status = "stuck"
            message = (f"every family still missing "
                       f"({', '.join(u for _, u in still)}) has failed in "
                       f"{DEFER_AFTER}+ daily batches; SAM did not answer for "
                       f"{failed_uei} this time. The driver keeps trying them, "
                       f"fewest failures first, once a day; check each on "
                       f"https://sam.gov/entity/<UEI>. {message}")
    if status == "fetched" and _parquet_stale(out_dir, raw_dir):
        status, message = "shape_error", (
            "entities.parquet was not rebuilt after this run's answers were "
            "stored: run `uv run python -m govbudget sam reparse` to see why")
    elif status == "fetched":
        if not still:
            status = "complete"
        message = (f"stored {fetched} answer(s) with {budget} request(s) free; "
                   f"{len(still)} of {len(families)} families still missing")
    return Outcome(status, message, fetched=fetched, failed=failed,
                   missing=len(still), budget=budget, ran=True,
                   retry=retrying), key


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
        started = not (s == "offline" and outcome.fetched == 0)
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
