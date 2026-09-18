"""`govbudget refresh` — the unattended end-to-end refresh orchestrator.

ROADMAP #8. Before this module the refresh drill was a page of LAUNCH.md and a
human who remembered the order; the award corpus was last ingested 2026-06-11
and nothing said so on any page until the freshness block shipped 2026-09-01.

DESIGN, and why it is this boring:

  * Every stage is a SUBPROCESS of the commands an operator would type, not an
    in-process call. `cmd_build` ends in `sys.exit(rc)` (cli.py:1799-1812) and
    several other commands exit non-zero on partial failure, so importing and
    calling them would either kill the orchestrator mid-run or require each one
    to be refactored. A subprocess boundary also means the orchestrator cannot
    accidentally hold the DuckDB lock while dbt wants it.

  * The ONLY two doors to the outside world are `_run` and `_capture`, both
    module-level, so the whole graph is testable with no network, no Postgres
    and no lake (tests/test_refresh.py).

  * Stage order is LAUNCH.md Step 0's canonical order, not a paraphrase:
    export-facts -> build -> export-site. The mart reads the parquet
    export-facts writes (jbooks/export_facts.py:80-101 ->
    dbt/models/sources.yml:20-36); LAUNCH.md Step 0 records what inverting them
    costs — "the mart and Postgres disagree and `export_site` fails loudly on
    the announcement-source check" (LAUNCH.md:163-164), i.e. ~35 wasted minutes.

  * A non-zero exit from any stage is fatal for the run. That matters most for
    `sync-archive`, which iterates FY by FY and CONTINUES past a failed FY,
    exiting 1 only at the end (`cmd_sync_archive`, cli.py:51-54): the
    orchestrator stops there and the operator reads the printed
    `PartitionShrinkError` / traceback to learn WHICH FY refused.

  * The orchestrator does NOT run the link loaders (jbooks crosswalk,
    scripts/derive_ap_links.py, scripts/load_announcement_links.py). Those
    rebuild budget_line_awards under a shared key whose run order decides which
    evidence each key carries. A data refresh is not a link rebuild; LAUNCH.md
    Step 0 stays the operator procedure for that.

  * The syncs run WITHOUT --allow-corpus-shrink. The path that runs while
    nobody is watching must be the safe one; that is what the Task 20a guards
    are for.

  * WHAT THE `fixtures` STAGE ACTUALLY IS. The ROADMAP entry words the drift
    alarm as "golden fixtures break = schema drift detected". The golden
    fixtures are COMMITTED FILES (tests/fixtures/...), so those suites test
    THIS REPO'S PARSERS against bytes that never change — a changed upstream
    cannot break them. The stage is still worth its minutes (a parser
    regression caught here does not propagate into a 35-minute derived
    rebuild), but it is not an upstream-shape alarm and must not be described
    as one. What does fire on a changed upstream, already shipped:
    convert._check_columns -> MissingColumnsError when a required column
    disappears (convert.py:95-107); fiscaldata.fetch_all_pages -> ValueError on
    a missing meta.total-pages (fiscaldata.py:26-30); convert
    .PartitionShrinkError on a truncated archive (convert.py:12-30).
    BLIND SPOT, named: a NEWLY ADDED upstream column is detected by nothing.
    The suites build their Postgres state in throwaway databases
    (govbudget_test in tests/jbooks/conftest.py, govbudget_test_root in
    tests/conftest.py) — with ONE exception that is not hermetic:
    tests/jbooks/test_era_keys.py opens a connection to the real
    `config.PG_DSN` warehouse that it uses only for SELECTs (its
    keyspace-collision guard; `psycopg.connect(config.PG_DSN)` at
    test_era_keys.py:84 sets no read-only mode), and skips when that database
    is unavailable. Only reads, but not "never touches".

  * The drift record has two halves that ARE true: drift_report ages every
    manifest dataset against the cadence its SOURCE publishes on, and the
    stall check alarms when a sync stage exits 0 without advancing its
    dataset's newest downloaded_at (the sync-subawards skip). Both land in
    data/refresh/last_run.json.

  * This module installs NO scheduler. scripts/launch/*.plist.template plus
    LAUNCH.md Step 11 are for the owner to load by hand.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SITE_URL = "https://fiscalreceipts.com"

# How long a preflight PROBE may take before it counts as hung. The probes are
# `rclone listremotes` and `vercel whoami`; both touch the network, both answer
# in under a second when healthy. Generous, but finite: launchd starts no
# second instance of a StartCalendarInterval label whose previous instance is
# still alive, so one wedged probe would stop the monthly refresh forever with
# nothing in the run record. STAGES deliberately get no timeout at all (dbt and
# the site build run 30+ minutes) — LAUNCH.md Step 11 says so and says what it
# costs.
PROBE_TIMEOUT_SECONDS = 60

# Returned by `_capture` for a probe that never answered. 124 is the
# conventional shell timeout code, so a reader who greps for it finds the
# meaning without this file.
PROBE_TIMEOUT_RC = 124

# Cadence -> the age at which a dataset is stale enough to name in the alarm.
# Generous on purpose: the alarm is for "nobody has run this in a season", not
# for "the run slipped by a week". Deliberately NOT shared with gate 24 leg m's
# CADENCE_DAYS (site/scripts/gates/datatruth.mjs:3705): that gate owns its own
# word->days map so it is checking a page against a manifest rather than one
# mirror against another. This table is an operator alarm, not a published claim.
_CADENCE_MAX_AGE_DAYS: dict[str, int] = {
    "monthly": 45,
    "quarterly": 135,
    "annual": 400,
    "biennial": 800,
}

STAGE_NAMES: tuple[str, ...] = (
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

# Which manifest datasets a sync stage is supposed to advance. Used by the
# stall check: exit 0 without advancing means the stage SKIPPED, not refreshed.
_STAGE_DATASETS: dict[str, tuple[str, ...]] = {
    "sync-archive": ("contracts", "assistance"),
    "sync-subawards": ("subawards",),
    "sync-fiscaldata": ("mts_outlays",),
}


class RefreshAborted(RuntimeError):
    pass


@dataclass(frozen=True)
class Stage:
    name: str
    argv: list[str]
    cwd: Path | None = None
    cadence: str = "monthly"
    env: dict[str, str] = field(default_factory=dict)


# ── the two doors to the outside world ──────────────────────────────────────


def _run(argv: list[str], *, cwd: Path | None = None, env: dict | None = None) -> int:
    """Run a stage, streaming its output. Returns the exit code.

    NO TIMEOUT, on purpose: `dbt build` and `npm run build` routinely run 30+
    minutes and a full `sync-archive` sweep runs hours, so any number small
    enough to catch a wedged stage is small enough to kill a healthy one. The
    cost is stated in LAUNCH.md Step 11 — a stage that hangs holds its launchd
    slot, and launchd then skips every later occurrence of that label until the
    machine is rebooted or the job is killed by hand.
    """
    print(f"+ {' '.join(argv)}" + (f"   (cwd={cwd})" if cwd else ""))
    return subprocess.run(
        argv, cwd=str(cwd) if cwd else None, env={**os.environ, **(env or {})}
    ).returncode


def _capture(argv: list[str], *, timeout: int = PROBE_TIMEOUT_SECONDS) -> tuple[int, str]:
    """Run a short PROBE and return (returncode, stdout+stderr).

    A probe that does not answer within `timeout` returns `PROBE_TIMEOUT_RC`
    and a message saying so, which preflight renders as an ordinary failure
    naming the probe — a hung `vercel whoami` must fail the preflight, not the
    schedule (see PROBE_TIMEOUT_SECONDS).
    """
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return PROBE_TIMEOUT_RC, f"timed out after {timeout}s with no answer"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# ── the stage graph ─────────────────────────────────────────────────────────


def _federal_fiscal_year(now: dt.datetime) -> int:
    """FY N runs Oct 1 (N-1) .. Sep 30 (N)."""
    return now.year + 1 if now.month >= 10 else now.year


def _lda_years(now: dt.datetime) -> str:
    """The LDA filing years a quarterly pull covers: this CALENDAR year and the
    two before it.

    Senate LDA filings are filed per calendar year and amended for months
    afterwards, so the current year plus two is the window that keeps a
    scheduled pull picking up late and amended filings. Computed from the
    clock rather than inherited from `cli.py`'s `--years 2024,2025,2026`
    default, which a loaded quarterly job would keep using after 2026 — and
    silently: LDA ingests write no `data/manifest.jsonl` record, so neither the
    cadence alarm nor the stall check can see the corpus going stale.
    """
    return ",".join(str(now.year - back) for back in (2, 1, 0))


def build_stages(root: Path, now: dt.datetime) -> list[Stage]:
    from govbudget import config

    py = sys.executable
    gb = [py, "-m", "govbudget"]
    subaward_fy = min(_federal_fiscal_year(now), config.FY_END)
    site_env = {"NEXT_PUBLIC_SITE_URL": SITE_URL}

    return [
        Stage("preflight", []),
        Stage("sync-archive", gb + ["sync-archive"]),
        # NOTE: cmd_sync_subawards returns early when the manifest already holds
        # this dataset+FY (cli.py:67-69), so after the first successful pull for
        # a given FY this stage prints "skipped" every month. That is existing
        # behavior, deliberately not changed here — when a partial-FY subaward
        # file may be replaced is its own decision. The stall check below turns
        # the silence into an alarm so nobody reads "skipped" as "refreshed".
        Stage("sync-subawards", gb + ["sync-subawards", "--fy", str(subaward_fy)]),
        Stage("sync-fiscaldata", gb + ["sync-fiscaldata"]),
        Stage("influence-pull",
              gb + ["influence", "pull", "--years", _lda_years(now)],
              cadence="quarterly"),
        # Parser-regression gate, NOT an upstream-shape alarm — see the module
        # docstring. Runs after the pulls and before anything derived, so a
        # broken parser stops the run instead of propagating into the mart, the
        # site and the CDN.
        Stage("fixtures", [py, "-m", "pytest", "-q",
                           "tests/influence", "tests/jbooks",
                           "tests/oversight", "tests/states"], cwd=root),
        Stage("export-facts", gb + ["jbooks", "export-facts"]),
        Stage("build", gb + ["build"]),
        Stage("export-site", gb + ["export-site"]),
        Stage("site-build", ["npm", "run", "build"], cwd=root / "site", env=site_env),
        Stage("site-verify", ["npm", "run", "verify"], cwd=root / "site", env=site_env),
        # The ONLY deploy path, by absolute path: R2 assets first, then Vercel,
        # then the live-asset check (scripts/launch/deploy.sh).
        Stage("deploy", [str(root / "scripts" / "launch" / "deploy.sh")]),
    ]


def _slice(stages: list[Stage], from_stage: str | None, until_stage: str | None) -> list[Stage]:
    for name in (from_stage, until_stage):
        if name is not None and name not in STAGE_NAMES:
            raise ValueError(
                f"unknown stage {name!r}. Valid stages, in order: "
                + ", ".join(STAGE_NAMES)
            )
    lo = STAGE_NAMES.index(from_stage) if from_stage else 0
    hi = STAGE_NAMES.index(until_stage) if until_stage else len(STAGE_NAMES) - 1
    if lo > hi:
        raise ValueError(f"--from {from_stage} comes after --until {until_stage}")
    return [s for s in stages if lo <= STAGE_NAMES.index(s.name) <= hi]


# ── preflight ───────────────────────────────────────────────────────────────
# Each check is its own module-level function so a test can neutralize one
# without stubbing the whole of preflight().


def _check_disk() -> None:
    from govbudget import config
    from govbudget.download import ensure_free_space

    ensure_free_space(config.RAW_DIR, config.MIN_FREE_GB)


def _check_postgres() -> None:
    import psycopg

    from govbudget import config

    with psycopg.connect(config.PG_DSN, connect_timeout=5) as con:
        con.execute("select 1")


def _check_duckdb() -> None:
    """Assert the lake EXISTS, then open it read-WRITE and close it again.

    The existence check has to come first, and is not a nicety:
    `duckdb.connect(path)` CREATES an empty database at a path that does not
    exist, so a misconfigured `GOVBUDGET_DUCKDB` / `GOVBUDGET_DATA` would pass
    the write-lock check green and leave an empty warehouse behind for the
    build to fail against half an hour later.

    Read-only would not answer the second question: what breaks an unattended
    run is another process (a dbt build, an open DuckDB CLI, a DBeaver
    session) holding the single-writer lock. This takes and releases exactly
    the lock `govbudget build` needs a few minutes later, so a failure here is
    the same failure, five stages earlier and with a name on it.
    """
    import duckdb

    from govbudget import config

    path = Path(config.DUCKDB_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"no lake at {path} — GOVBUDGET_DUCKDB / GOVBUDGET_DATA points "
            "somewhere with no warehouse (connecting would CREATE an empty "
            "database there)"
        )
    con = duckdb.connect(str(path))
    con.close()


def preflight(*, root: Path, require_deploy: bool = True) -> list[str]:
    """Return human-readable failures; an empty list is green.

    Never raises for a check failure — the caller records every failure in
    last_run.json, so the operator sees all of them at once instead of fixing
    them one run at a time.
    """
    from govbudget import config

    failures: list[str] = []

    try:
        _check_disk()
    except Exception as exc:
        failures.append(f"disk: {exc}")

    try:
        _check_postgres()
    except Exception as exc:
        failures.append(
            f"postgres: cannot connect to {config.PG_DSN} "
            f"({type(exc).__name__}: {exc})"
        )

    try:
        _check_duckdb()
    except FileNotFoundError as exc:
        # Distinct from the lock failure below: nothing is holding a lake that
        # is not there, and saying so would send the operator hunting a process.
        failures.append(f"duckdb: {exc}")
    except Exception as exc:
        failures.append(
            f"duckdb: cannot take the write lock on {config.DUCKDB_PATH} — "
            f"another process is holding it ({type(exc).__name__}: {exc})"
        )

    # launchd opens StandardOutPath/StandardErrorPath BEFORE exec and does not
    # create missing parents, so a scheduled job cannot create its own log
    # directory — `logs/` is gitignored, so a fresh clone has none.
    if not (root / "logs").is_dir():
        failures.append(
            f"logs: {root}/logs does not exist, and launchd opens the job's log "
            f"files before exec — run `mkdir -p {root}/logs` "
            "(docs/superpowers/LAUNCH.md Step 11)"
        )

    if not require_deploy:
        return failures

    if shutil.which("rclone") is None:
        failures.append("rclone: not on PATH (brew install rclone)")
    else:
        rc, out = _capture(["rclone", "listremotes"])
        if rc != 0:
            failures.append(f"rclone: `rclone listremotes` exited {rc}: {out.strip()}")
        elif "r2:" not in out:
            failures.append(
                "rclone: no remote named 'r2' is configured "
                f"(listremotes: {out.strip() or 'none'}). See "
                "docs/superpowers/LAUNCH.md Step 4a"
            )

    if shutil.which("vercel") is None:
        failures.append("vercel: CLI not on PATH (npm i -g vercel)")
    else:
        rc, out = _capture(["vercel", "whoami"])
        if rc != 0:
            failures.append(
                f"vercel: not logged in (`vercel whoami` exited {rc}: "
                f"{out.strip()}). Run `vercel login`."
            )

    if not (root / "scripts" / "launch" / "deploy.sh").is_file():
        failures.append(f"deploy: {root}/scripts/launch/deploy.sh is missing")

    return failures


# ── drift report ────────────────────────────────────────────────────────────


def drift_report(manifest_path: Path, now: dt.datetime) -> dict:
    """Age every ingested dataset against the cadence its SOURCE publishes on.

    The cadence table is export_site._DECLARED_CADENCE — the same table the
    /methodology/ freshness sentence renders from. TWO consumers, one table;
    gate 24 leg m is deliberately NOT one of them (it owns its own word->days
    map so it checks a rendered page against data/manifest.jsonl rather than one
    mirror against another — datatruth.mjs:3705). export_site raises on a
    manifest dataset with no entry here, which is what keeps the table complete.

    A dataset whose declared cadence is None makes no claim, so it can never be
    stale: "no claim" is a decision, not an omission — the comment block above
    `_DECLARED_CADENCE` says so and the `None` entries are deliberate.

    UNPARSEABLE LINES ARE COUNTED, never merely skipped. gate 24 leg m reads
    the same `data/manifest.jsonl` and returns a hard error on one
    ("refusing to guess ingest ages", datatruth.mjs); this operator alarm is
    deliberately laxer than the published-page gate — a partial final line is
    ordinary crash residue and must not stop a refresh — but it may not be
    silent, because a dropped line makes a dataset vanish from the report and
    the stall check would then describe a record that exists as absent.
    """
    from govbudget.export_site import _DECLARED_CADENCE

    newest: dict[str, str] = {}
    unparseable = 0
    if manifest_path.exists():
        for line in manifest_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                unparseable += 1
                continue
            ds, at = rec.get("dataset"), rec.get("downloaded_at")
            if not ds or not at:
                unparseable += 1
                continue
            if ds not in newest or at > newest[ds]:
                newest[ds] = at

    datasets: dict[str, dict] = {}
    alarms: list[str] = []
    for ds, at in sorted(newest.items()):
        try:
            when = dt.datetime.fromisoformat(at)
        except ValueError:
            unparseable += 1
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.UTC)
        age = (now - when).days
        cadence = _DECLARED_CADENCE.get(ds)
        datasets[ds] = {
            "newest_downloaded_at": at,
            "age_days": age,
            "declared_cadence": cadence,
        }
        limit = _CADENCE_MAX_AGE_DAYS.get(cadence or "")
        if limit is not None and age > limit:
            alarms.append(
                f"{ds}: newest ingest is {age} days old against a declared "
                f"{cadence} cadence (alarm above {limit} days)"
            )

    if unparseable:
        alarms.insert(0, (
            f"{unparseable} unparseable manifest line(s) in {manifest_path} "
            "were ignored — a dataset they carried may be missing from this "
            "report entirely (gate 24 leg m treats one such line as fatal)"
        ))

    return {
        "datasets": datasets,
        "alarms": alarms,
        "unparseable_lines": unparseable,
    }


# ── the run ─────────────────────────────────────────────────────────────────


def _write_state(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def _confirm(planned: list[Stage]) -> None:
    if not sys.stdin.isatty():
        raise RefreshAborted(
            "no TTY to confirm on and --yes was not passed. A scheduled run "
            "must pass --yes explicitly: launchd hands a job no controlling "
            "terminal, so a refresh blocked on input() would hang forever "
            "without ever running or reporting, holding its launchd slot — and "
            "launchd starts no second instance of a label whose previous "
            "instance is still alive. See scripts/launch/refresh.sh."
        )
    print("\nStages to run:")
    for s in planned:
        print(f"  {s.name}")
    if input("\nProceed? type 'yes': ").strip().lower() != "yes":
        raise RefreshAborted("aborted at the confirmation prompt")


def _stall_alarms(record: dict, after: dict) -> list[str]:
    """A sync stage that exited 0 without advancing its dataset SKIPPED it.

    The concrete case this exists for: cmd_sync_subawards returns early once
    the manifest holds its dataset+FY (cli.py:67-69), so a monthly run reports
    a green sync-subawards forever. Green must not read as refreshed.
    """
    # An unparseable line drops its dataset from the report, so "no record at
    # all" would be a false statement about a record that exists but could not
    # be read. Say which of the two it is.
    unreadable = after.get("unparseable_lines", 0)
    caveat = (
        f" (or a record that is there and unreadable — {unreadable} "
        "unparseable manifest line(s) were ignored)" if unreadable else ""
    )
    alarms: list[str] = []
    for entry in record["stages"]:
        if entry["status"] != "ok":
            continue
        for ds in _STAGE_DATASETS.get(entry["name"], ()):
            if ds not in after["datasets"]:
                alarms.append(
                    f"{entry['name']}: exited 0 but {ds} has no record in "
                    f"data/manifest.jsonl at all{caveat}"
                )
            elif not record["ingest_advanced"][ds]:
                stamp = after["datasets"][ds]["newest_downloaded_at"]
                alarms.append(
                    f"{entry['name']}: exited 0 but {ds} did not advance in "
                    f"data/manifest.jsonl (newest ingest still {stamp}) — the "
                    "stage skipped, it did not refresh"
                )
    return alarms


def _acquire_single_instance_lock(lock_path: Path):
    """Exclusive, non-blocking `flock` on `data/refresh/.lock`.

    The monthly and quarterly jobs carry DIFFERENT launchd labels, so launchd's
    same-label suppression does not keep them apart: the quarterly (6th 03:00)
    can join a monthly (5th 03:00) still downloading archives, and both would
    write the same parquet partitions and append the same manifest. The second
    instance refuses immediately rather than waiting — a refresh that starts
    hours late is not the run the schedule asked for.

    Returns the open file handle; closing it releases the lock. The kernel also
    releases it if the process dies, so a crashed run leaves no stale lock.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("w")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise RefreshAborted(
            f"another refresh already holds {lock_path} — refusing to start a "
            "second instance against the same lake. Wait for it to finish "
            "(`tail -f logs/refresh-*.log`); the lock clears on its own when "
            "that process exits."
        ) from None
    handle.write(f"{os.getpid()}\n")
    handle.flush()
    return handle


def run_refresh(
    *,
    dry_run: bool = False,
    from_stage: str | None = None,
    until_stage: str | None = None,
    quarterly: bool = False,
    assume_yes: bool = False,
    root: Path | None = None,
    now: dt.datetime | None = None,
    state_path: Path | None = None,
) -> dict:
    """Run the refresh stage graph. Returns (and persists) the run record."""
    from govbudget import config

    root = Path(root) if root is not None else config.ROOT
    now = now or dt.datetime.now(dt.UTC)
    state_path = state_path or (config.DATA_DIR / "refresh" / "last_run.json")

    # Taken BEFORE the run record exists, on purpose: a refused second instance
    # must not overwrite the record of the run that is still going.
    lock = _acquire_single_instance_lock(state_path.parent / ".lock")
    try:
        planned = _slice(build_stages(root, now), from_stage, until_stage)
        if not assume_yes and not dry_run:
            _confirm(planned)

        require_deploy = any(s.name == "deploy" for s in planned)
        before = drift_report(config.MANIFEST_PATH, now)
        record: dict = {
            "started_at": now.isoformat(),
            "root": str(root),
            "dry_run": dry_run,
            "quarterly": quarterly,
            "from_stage": from_stage,
            "until_stage": until_stage,
            "ok": True,
            "failed_stage": None,
            "error": None,
            "stages": [],
            "drift": {"datasets": {}, "alarms": [], "unparseable_lines": 0},
            "ingest_advanced": {},
        }

        # EVERYTHING from here is inside a finally that writes the record. An
        # exec-level failure (`FileNotFoundError` from a binary that is not on
        # launchd's minimal PATH) or a Ctrl-C escapes `_run` instead of
        # returning a code, and without this the record would never be
        # rewritten — leaving `data/refresh/last_run.json`, the one file the
        # operator is told to read, holding the PREVIOUS run's `"ok": true`.
        current: str | None = None
        try:
            aborted = False
            for stage in planned:
                current = stage.name
                entry: dict = {"name": stage.name, "status": "not-run",
                               "returncode": None, "detail": "", "seconds": None}
                record["stages"].append(entry)

                if aborted:
                    continue
                if stage.cadence == "quarterly" and not quarterly:
                    entry["status"] = "skipped-cadence"
                    entry["detail"] = "quarterly stage; re-run with --quarterly"
                    continue
                if dry_run:
                    entry["status"] = "dry-run"
                    entry["detail"] = " ".join(stage.argv) or "(in-process)"
                    print(f"+ {entry['detail']}"
                          + (f"   (cwd={stage.cwd})" if stage.cwd else ""))
                    continue

                began = dt.datetime.now(dt.UTC)
                if stage.name == "preflight":
                    failures = preflight(root=root, require_deploy=require_deploy)
                    rc = 1 if failures else 0
                    entry["detail"] = "; ".join(failures)
                    for f in failures:
                        print(f"PREFLIGHT FAIL: {f}", file=sys.stderr)
                else:
                    rc = _run(stage.argv, cwd=stage.cwd, env=stage.env)
                entry["returncode"] = rc
                entry["seconds"] = round(
                    (dt.datetime.now(dt.UTC) - began).total_seconds(), 1)
                entry["status"] = "ok" if rc == 0 else "failed"
                if rc != 0:
                    record["ok"] = False
                    record["failed_stage"] = stage.name
                    aborted = True
                    print(
                        f"\nrefresh: stage {stage.name} failed (exit {rc}). "
                        f"Nothing after it ran. Resume with "
                        f"`python -m govbudget refresh --from {stage.name} --yes` "
                        "(note: --from skips preflight).",
                        file=sys.stderr,
                    )

            after = drift_report(config.MANIFEST_PATH, now)
            record["drift"] = after
            record["ingest_advanced"] = {
                ds: after["datasets"][ds]["newest_downloaded_at"]
                != before["datasets"].get(ds, {}).get("newest_downloaded_at")
                for ds in after["datasets"]
            }
            if not dry_run:
                after["alarms"].extend(_stall_alarms(record, after))
        except BaseException as exc:   # KeyboardInterrupt included, deliberately
            record["ok"] = False
            record["error"] = f"{type(exc).__name__}: {exc}"
            if record["failed_stage"] is None:
                record["failed_stage"] = current
            print(
                f"\nrefresh: {record['error']}"
                + (f" (during stage {current})" if current else ""),
                file=sys.stderr,
            )
            raise
        finally:
            record["ended_at"] = dt.datetime.now(dt.UTC).isoformat()
            # R-20b-6: an alarm is REPORT-ONLY. It never clears record["ok"] and
            # never changes the exit code — a cadence alarm on data the upstream
            # has not republished must not fail a scheduled run. The operator
            # reads data/refresh/last_run.json (and logs/refresh-*.err.log).
            for alarm in record["drift"]["alarms"]:
                print(f"DRIFT ALARM: {alarm}", file=sys.stderr)
            if not dry_run:
                _write_state(state_path, record)
                print(f"refresh: run record -> {state_path}")
    finally:
        lock.close()
    return record
