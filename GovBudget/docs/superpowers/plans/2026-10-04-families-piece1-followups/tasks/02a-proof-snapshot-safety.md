<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). Task 2 is split into 02a (snapshot safety and the proof CLI convention), 02b (diff corners and the noise file) and 02c (proof scripts and proof notes); run them in that order. -->

### Task 2a: Proof tooling hardening — snapshot safety and the `proof` CLI convention (#199)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6 (the one CLI convention: a tool error prints `<tool>: ERROR — <message>` and exits 2; a failed check exits 1), §6.1 "Snapshot safety" (hermeticity by resolved path, the SAM check over the whole copy, symlink scan and digests before `create database`, drop only the database this call created, `env.sh` quoting, the password refusal) and its "Tests to add" (`.wal`, writer lock, missing entry, after the copy, port 55432, a literal `?host=`). §6.9 lists the #199 items not done (none of them is in this part).

**Files:**
- Modify: `src/govbudget/proof.py` — `snapshot` (whole function, about lines 1433–1532), new helpers inserted before `def _clone(src: Path, dst: Path) -> None:` (about line 1563), `_rewrite_duckdb_views` (anchor on `raise RuntimeError(f"proof snapshot: views still read {old}:`), `_pg_snapshot` (whole function, about lines 1729–1800), `_env_script` (whole function, about lines 1803–1815)
- Modify: `src/govbudget/cli.py` — `cmd_proof` (whole function, about lines 3096–3145)
- Test: `tests/test_proof.py` — the `pg_source` fixture (about line 593), `test_snapshot_refuses_a_local_scratch_db_without_the_proof_prefix` (about line 477), and a new section appended at the end of the file

Line numbers are hints; anchor on the quoted text.

**Interfaces:**
Consumes: Task 1's workspace (the throwaway cluster on 127.0.0.1:55432, `GOVBUDGET_PG_BIN`).
Produces (Task 21 takes its snapshots with this tool):
- `proof.snapshot(out_dir, *, data_dir, pg_dsn, scratch_db) -> dict` — same signature and manifest keys as today (`snapshot.json` `schema_version` stays 1). New refusals: `ValueError("proof snapshot: the source DSN carries a password; …")`; `RuntimeError("proof snapshot: refusing — the copy ran HH:MM:SS-HH:MM:SS, across the SAM window …")`; `RuntimeError("proof snapshot: N view read(s) resolve outside the snapshot …")`; `RuntimeError("proof snapshot: N jbook_documents.file_path row(s) resolve outside the snapshot …")`. A symlink in a pinned tree now raises before any database exists. On any failure after `out_dir` is created, `out_dir` is removed and the scratch database is dropped only if this call created it.
- `proof._drop_scratch_database(pg_dsn: str, scratch_db: str) -> None` (refuses any name but `govbudget_proof_<name>`).
- `proof._sam_window_touched(start: datetime.datetime, end: datetime.datetime) -> bool`, `proof._view_parquet_paths(sql: str) -> list[str]`, `proof._is_under(path: Path, root: Path) -> bool`.
- `<snapshot>/env.sh`: `_proof_dir=<shlex-quoted path>` then `if [ -n "${1:-}" ]; then _proof_dir="$1"; fi`; usage unchanged (`source <snapshot>/env.sh [RUN_DIR]`).
- `govbudget proof snapshot|diff`: exit 0 EQUAL/PASS, 1 DIFFERENT/FAIL, 2 tool error with one stderr line `proof <action>: ERROR — <message>` and no traceback.

Measured for this task (2026-10-13, read-only):
- `uv run --project . pytest tests/test_proof.py -q` → `131 passed` (the pg tests ran on the 55432 cluster; `test_snapshot_refuses_a_local_scratch_db_without_the_proof_prefix` is 3 of them, one per DSN).
- The live DuckDB has 37 views; 18 call `read_parquet`, and every path literal they name is under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/` (e.g. `read_parquet('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/contracts/*/*.parquet', (hive_partitioning = …`). The regex `read_parquet\(\s*(\[[^\]]*\]|'(?:[^']|'')*')` matches the first argument of all 18. Postgres `jbook_documents`: 254 rows, every `file_path` under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/raw_docs/`.
- `psycopg.conninfo.conninfo_to_dict("postgresql://remote.example.invalid/govbudget?host=127.0.0.1&port=55432")` → `{'dbname': 'govbudget', 'host': '127.0.0.1', 'port': '55432'}`, and `_with_database` of it keeps that host and port; `conninfo_to_dict("postgresql://u:s3cret@127.0.0.1:55432/postgres")` carries `'password': 's3cret'`.
- A second process holding a read-write `duckdb.connect` makes `duckdb.connect(path, read_only=True)` raise `_duckdb.IOException: IO Error: Could not set lock on file …` and leaves no `.wal`.
- Today's `env.sh` line `_proof_dir="${1:-<path>}"` under `/bin/bash` 3.2.57: `/tmp/a}b` becomes `/tmp/ab}`, `/tmp/a$HOME` expands `$HOME`, `/tmp/a"b` and `/tmp/a b'c` end in a syntax error and an empty `GOVBUDGET_DATA`. The quoted form below gives the literal path for all four, and `RUN_DIR` when one is passed.

- [ ] **Step 1: Write the failing tests**

In `tests/test_proof.py`, add the port assertion to the `pg_source` fixture. Replace:

```python
@pytest.fixture()
def pg_source():
    """A throwaway source database on the TEST cluster, never the real one."""
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True)
```

with:

```python
@pytest.fixture()
def pg_source():
    """A throwaway source database on the TEST cluster, never the real one."""
    assert str(psycopg.conninfo.conninfo_to_dict(ADMIN_DSN).get("port")) == "55432", (
        f"GOVBUDGET_TEST_PG_DSN={ADMIN_DSN!r} is not the throwaway cluster on port 55432")
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True)
```

Change the CLI half of the prefix test to the new exit convention. Replace:

```python
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
```

with:

```python
def test_snapshot_refuses_a_local_scratch_db_without_the_proof_prefix(
    tmp_path, monkeypatch, capsys, dsn,
):
    # README: on the local server only govbudget_proof_<name> may be created;
    # both the function and the CLI (cmd_proof) refuse before touching anything.
    # The CLI reports a tool error on one line and exits 2 (follow-ups #199).
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    with pytest.raises(ValueError, match="must be named govbudget_proof_<name>"):
        proof.snapshot(tmp_path / "s", data_dir=tmp_path / "data", pg_dsn=dsn,
                       scratch_db="snap")
    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "snapshot", "--out", str(tmp_path / "s"), "--scratch-db", "snap",
                  "--data-dir", str(tmp_path / "data"), "--pg-dsn", dsn])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert err.startswith("proof snapshot: ERROR — a scratch database must be named"
                          " govbudget_proof_<name>")
    assert "Traceback" not in err
    assert not (tmp_path / "s").exists()
```

Append at the end of `tests/test_proof.py`:

```python


# ---------------------------------------------------------------------------
# Families piece-1 follow-ups, ROADMAP #199 (spec 2026-10-04 §6.1): snapshot
# safety and the one CLI convention (tool error -> exit 2, one line)
# ---------------------------------------------------------------------------

_SRC = "postgresql://127.0.0.1:55432/proof_src_test"
_SCRATCH = "govbudget_proof_scratch_test"


def _scratch_db_exists(admin) -> bool:
    return admin.execute(
        "select 1 from pg_database where datname = %s", (_SCRATCH,)).fetchone() is not None


def test_snapshot_refuses_a_dsn_with_a_password(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    dsn = "postgresql://andeslee:s3cret@127.0.0.1:55432/postgres"
    with pytest.raises(ValueError, match="carries a password"):
        proof.snapshot(tmp_path / "s", data_dir=tmp_path / "data", pg_dsn=dsn, scratch_db=_SCRATCH)
    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "snapshot", "--out", str(tmp_path / "s"), "--scratch-db", _SCRATCH,
                  "--data-dir", str(tmp_path / "data"), "--pg-dsn", dsn])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert err.startswith("proof snapshot: ERROR — the source DSN carries a password")
    assert "s3cret" not in err
    assert not (tmp_path / "s").exists()


def test_snapshot_refuses_when_the_copy_spans_the_sam_window(tmp_path, monkeypatch):
    # #199: the after-copy check looked only at the end minute. A copy that
    # starts at :14 and ends at :21 crossed the :17 SAM write.
    live = tmp_path / "live"
    _lake(live)
    times = iter([datetime.datetime(2026, 10, 2, 9, 14, 30),   # the before-copy check
                  datetime.datetime(2026, 10, 2, 9, 14, 40),   # the copy starts
                  datetime.datetime(2026, 10, 2, 9, 21, 5)])   # the copy ends
    monkeypatch.setattr(proof, "_now", lambda: next(times))
    monkeypatch.setattr(proof, "_database_exists", lambda dsn, name: False)

    def no_postgres(*_args, **_kwargs):
        raise AssertionError("the copy spanned :17 — snapshot must stop before Postgres")

    monkeypatch.setattr(proof, "_pg_snapshot", no_postgres)
    out = tmp_path / "proofs" / "s0"
    with pytest.raises(RuntimeError, match="the copy ran 09:14:40-09:21:05, across the SAM window"):
        proof.snapshot(out, data_dir=live, pg_dsn=_SRC, scratch_db=_SCRATCH)
    assert not out.exists()


@pytest.mark.parametrize("start, end, touched", [
    ((9, 5, 0), (9, 14, 59), False),
    ((9, 14, 59), (9, 15, 0), True),
    ((9, 20, 59), (9, 21, 1), True),
    ((9, 21, 0), (10, 14, 0), False),
    ((9, 21, 0), (10, 21, 0), True),       # an hour or longer always spans :17
])
def test_sam_window_touched_reads_every_minute_of_the_interval(start, end, touched):
    day = datetime.datetime(2026, 10, 2)
    a = day.replace(hour=start[0], minute=start[1], second=start[2])
    b = day.replace(hour=end[0], minute=end[1], second=end[2])
    assert proof._sam_window_touched(a, b) is touched


def test_snapshot_refuses_an_unfinished_duckdb_write(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    live = tmp_path / "live"
    _lake(live)
    (live / "duckdb" / "govbudget.duckdb.wal").write_bytes(b"wal")
    with pytest.raises(RuntimeError, match="a DuckDB write is unfinished"):
        proof.snapshot(tmp_path / "s", data_dir=live, pg_dsn=_SRC, scratch_db=_SCRATCH)
    assert not (tmp_path / "s").exists()


def test_snapshot_refuses_while_a_writer_holds_the_duckdb_file(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    monkeypatch.setattr(proof, "_database_exists", lambda dsn, name: False)
    live = tmp_path / "live"
    _lake(live)
    writer = subprocess.Popen(
        [sys.executable, "-c",
         "import duckdb, sys, time; c = duckdb.connect(sys.argv[1]);"
         " print('locked', flush=True); time.sleep(60)",
         str(live / "duckdb" / "govbudget.duckdb")],
        stdout=subprocess.PIPE, text=True)
    try:
        assert writer.stdout.readline().strip() == "locked"
        with pytest.raises(RuntimeError, match="is being written"):
            proof.snapshot(tmp_path / "s", data_dir=live, pg_dsn=_SRC, scratch_db=_SCRATCH)
    finally:
        writer.kill()
        writer.wait()
    assert not (tmp_path / "s").exists()


def test_snapshot_refuses_a_missing_lake_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    live = tmp_path / "live"
    _lake(live)
    shutil.rmtree(live / "raw_docs")
    with pytest.raises(FileNotFoundError, match="raw_docs is missing"):
        proof.snapshot(tmp_path / "s", data_dir=live, pg_dsn=_SRC, scratch_db=_SCRATCH)
    assert not (tmp_path / "s").exists()


def test_with_database_keeps_a_literal_host_query_parameter():
    # libpq lets ?host= retarget a URI. The scratch DSN must keep that
    # override, so `create database` lands on the server the dump came from.
    dsn = "postgresql://remote.example.invalid/govbudget?host=127.0.0.1&port=55432"
    got = psycopg.conninfo.conninfo_to_dict(proof._with_database(dsn, "govbudget_proof_x"))
    assert (got["host"], str(got["port"]), got["dbname"]) == (
        "127.0.0.1", "55432", "govbudget_proof_x")


def test_view_rewrite_refuses_a_symlinked_spelling_of_the_lake(tmp_path):
    # #199: a view that names the lake through a symlink (a worktree's
    # data/ links) is not rewritten by the string replace and still read the
    # live parquet; hermeticity is now checked on the RESOLVED path.
    live = tmp_path / "live"
    _lake(live)
    alias = tmp_path / "worktree-data"
    alias.symlink_to(live, target_is_directory=True)
    con = duckdb.connect(str(live / "duckdb" / "govbudget.duckdb"))
    try:
        con.execute("create view stg_alias as select * from read_parquet("
                    f"'{alias}/parquet/jbooks/budget_lines.parquet')")
    finally:
        con.close()
    snap = tmp_path / "snap"
    (snap / "duckdb").mkdir(parents=True)
    shutil.copy(live / "duckdb" / "govbudget.duckdb", snap / "duckdb" / "govbudget.duckdb")
    shutil.copytree(live / "parquet", snap / "parquet")
    with pytest.raises(RuntimeError,
                       match=r"1 view read\(s\) resolve outside the snapshot .*stg_alias"):
        proof._rewrite_duckdb_views(snap / "duckdb" / "govbudget.duckdb",
                                    old_root=live.resolve(), new_root=snap.resolve())


def test_view_parquet_paths_reads_strings_lists_and_escaped_quotes():
    sql = ("CREATE VIEW v AS SELECT * FROM read_parquet('/a/b.parquet') UNION ALL"
           " SELECT * FROM read_parquet(['/c/d.parquet', '/e/it''s.parquet'],"
           " (hive_partitioning = CAST('t' AS BOOLEAN)))")
    assert proof._view_parquet_paths(sql) == ["/a/b.parquet", "/c/d.parquet", "/e/it's.parquet"]


@pytest.mark.parametrize("weird", ["/tmp/a}b", "/tmp/a$HOME", '/tmp/a"b', "/tmp/a b'c"])
def test_env_sh_keeps_any_snapshot_path_literal(tmp_path, weird):
    script = tmp_path / "env.sh"
    script.write_text(proof._env_script({
        "created_at": "2026-10-13T00:00:00+00:00",
        "env": {"GOVBUDGET_DATA": weird, "GOVBUDGET_DUCKDB": f"{weird}/duckdb/govbudget.duckdb",
                "GOVBUDGET_PG_DSN": "host=127.0.0.1 port=55432 dbname=govbudget_proof_x"}}))

    def sourced(*args: str) -> str:
        return subprocess.run(
            ["bash", "-c", 'source "$0" "$@"; printf "%s|%s" "$GOVBUDGET_DATA" "$GOVBUDGET_DUCKDB"',
             str(script), *args], capture_output=True, text=True, check=True).stdout

    assert sourced() == f"{weird}|{weird}/duckdb/govbudget.duckdb"
    assert sourced("/runs/x") == "/runs/x|/runs/x/duckdb/govbudget.duckdb"


def test_a_symlink_in_a_pinned_tree_refuses_before_any_database_exists(
    tmp_path, monkeypatch, pg_source,
):
    admin, src_dsn = pg_source
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    live = tmp_path / "live"
    _lake(live)
    (live / "site" / "linked").symlink_to(live / "parquet", target_is_directory=True)
    out = tmp_path / "proofs" / "s0"
    with pytest.raises(RuntimeError, match="symlink inside a pinned tree"):
        proof.snapshot(out, data_dir=live, pg_dsn=src_dsn, scratch_db=_SCRATCH)
    assert not _scratch_db_exists(admin)
    assert not out.exists()


def test_a_failure_after_create_database_drops_only_that_database(
    tmp_path, monkeypatch, pg_source,
):
    admin, src_dsn = pg_source
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    live = tmp_path / "live"
    _lake(live)

    def injected(dsn, expected):
        raise RuntimeError("proof snapshot: injected failure after create database")

    monkeypatch.setattr(proof, "_assert_connected_to", injected)
    out = tmp_path / "proofs" / "s0"
    with pytest.raises(RuntimeError, match="injected failure"):
        proof.snapshot(out, data_dir=live, pg_dsn=src_dsn, scratch_db=_SCRATCH)
    names = {r[0] for r in admin.execute("select datname from pg_database").fetchall()}
    assert _SCRATCH not in names
    assert "proof_src_test" in names           # the source is never touched
    assert not out.exists()


def test_a_document_path_through_a_symlink_refuses_and_cleans_up(
    tmp_path, monkeypatch, pg_source,
):
    admin, src_dsn = pg_source
    monkeypatch.setattr(proof, "_now", lambda: datetime.datetime(2026, 10, 2, 9, 5))
    live = tmp_path / "live"
    _lake(live)
    alias = tmp_path / "worktree-data"
    alias.symlink_to(live, target_is_directory=True)
    with psycopg.connect(src_dsn) as con:
        con.execute("create table jbook_documents (id serial primary key, file_path text)")
        con.execute("insert into jbook_documents (file_path) values (%s), (%s)",
                    (f"{live.resolve()}/raw_docs/fy2017/dod/p1_display.xlsx",
                     f"{alias}/raw_docs/fy2017/dod/p1_display.xlsx"))
    out = tmp_path / "proofs" / "s0"
    with pytest.raises(RuntimeError, match="1 jbook_documents.file_path row.s. resolve outside"):
        proof.snapshot(out, data_dir=live, pg_dsn=src_dsn, scratch_db=_SCRATCH)
    assert not _scratch_db_exists(admin)
    assert not out.exists()


def test_cli_tool_errors_exit_2_with_one_line(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", str(tmp_path / "nope"), str(tmp_path)])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert err.startswith(f"proof diff: ERROR — {tmp_path / 'nope'} is not a directory")
    assert "Traceback" not in err
```

- [ ] **Step 2: Run them — they fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_proof.py -q 2>&1 | tail -3
```

Expected: `20 failed, 132 passed` (152 tests: 131 + 21 new). The failures: the 3 prefix-test cases (the CLI raised `ValueError`, not `SystemExit`), the password test (`FileNotFoundError` instead of the refusal), the SAM-span test (`AssertionError: the copy spanned :17 …`), the 5 `_sam_window_touched` cases and `test_view_parquet_paths_…` (`AttributeError: module 'govbudget.proof' has no attribute …`), the view-symlink test (`DID NOT RAISE`), the 4 `env.sh` cases (`AssertionError` on the no-argument line), the 3 Postgres-backed tests (the database still exists, or `DID NOT RAISE`), and the CLI tool-error test (`NotADirectoryError` escapes). The `.wal`, writer-lock, missing-entry and `?host=` tests pass already: they pin refusals that had no test (#199).

- [ ] **Step 3: Add the helpers**

In `src/govbudget/proof.py`, insert immediately before `def _clone(src: Path, dst: Path) -> None:`:

```python
def _sam_window_touched(start: datetime.datetime, end: datetime.datetime) -> bool:
    """True when any wall-clock minute from start to end (inclusive) is a SAM
    write minute (:15-:20), or the span is an hour or longer. ROADMAP #199:
    the after-copy check used to read the end minute only, so a copy from
    :14 to :21 passed."""
    if end < start:
        start, end = end, start
    if end - start >= datetime.timedelta(hours=1):
        return True
    minute = start.replace(second=0, microsecond=0)
    while minute <= end:
        if minute.minute in SAM_WINDOW_MINUTES:
            return True
        minute += datetime.timedelta(minutes=1)
    return False


def _check_sam_interval(start: datetime.datetime, end: datetime.datetime, stage: str) -> None:
    if _sam_window_touched(start, end):
        raise RuntimeError(
            f"proof snapshot: refusing — {stage} ran {start:%H:%M:%S}-{end:%H:%M:%S},"
            " across the SAM window (the hourly SAM job writes data/parquet/sam at :17);"
            " run outside :15-:20"
        )


def _refuse_password(pg_dsn: str) -> None:
    """snapshot.json and env.sh record the scratch DSN in plaintext, so a
    source DSN that carries a password is refused before anything is
    written (ROADMAP #199). The message never repeats the password."""
    import psycopg

    if psycopg.conninfo.conninfo_to_dict(pg_dsn).get("password"):
        raise ValueError(
            "proof snapshot: the source DSN carries a password; snapshot.json and env.sh"
            " would record it in plaintext. Use ~/.pgpass or PGPASSWORD instead"
        )


def _is_under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


_READ_PARQUET_ARG_RE = re.compile(r"read_parquet\(\s*(\[[^\]]*\]|'(?:[^']|'')*')")
_SQL_STRING_RE = re.compile(r"'((?:[^']|'')*)'")


def _view_parquet_paths(sql: str) -> list[str]:
    """Every path literal a view's read_parquet(...) calls name — a string
    or a list of strings — with SQL '' unescaped."""
    out: list[str] = []
    for m in _READ_PARQUET_ARG_RE.finditer(sql):
        out.extend(s.replace("''", "'") for s in _SQL_STRING_RE.findall(m.group(1)))
    return out


def _drop_scratch_database(pg_dsn: str, scratch_db: str) -> None:
    """Drop the scratch database a failed snapshot() created itself
    (ROADMAP #199). Refuses any name but govbudget_proof_<name>."""
    import psycopg
    from psycopg import sql

    _check_scratch_name(scratch_db)
    with psycopg.connect(_with_database(pg_dsn, "postgres"), autocommit=True) as admin:
        admin.execute(sql.SQL("drop database if exists {} with (force)").format(
            sql.Identifier(scratch_db)))


```

- [ ] **Step 4: Reorder `snapshot` and clean up after a failure**

In `src/govbudget/proof.py`, replace the whole function `snapshot` — from `def snapshot(out_dir: Path, *, data_dir: Path, pg_dsn: str, scratch_db: str) -> dict:` through its last line `    return manifest` (the line before `def _check_sam_window(stage: str) -> None:`) — with:

```python
def snapshot(out_dir: Path, *, data_dir: Path, pg_dsn: str, scratch_db: str) -> dict:
    """Pin everything export-site reads into out_dir; return the manifest.

    Writes out_dir/{duckdb,parquet,site,raw_docs,manifest.jsonl} (APFS clones),
    out_dir/pg/<db>.dump, out_dir/snapshot.json and out_dir/env.sh, and restores
    the dump into a NEW database `scratch_db` on the same server. Refuses if
    out_dir or the scratch database already exists, out_dir resolves inside
    the lake (symlinks followed — a worktree's data/site is a symlink into
    the live lake), the SAM write window (:15-:20) holds the start or any
    minute of the copy, a writer holds the DuckDB file, the DSN carries a
    password, or scratch_db is not named govbudget_proof_<name>.

    Order (ROADMAP #199): the copy; then the symlink scan and the digests of
    every pinned tree; then the view rewrite and its hermeticity check (every
    read_parquet path must RESOLVE under out_dir); only then `create
    database`, whose jbook_documents.file_path rows must also resolve under
    out_dir. On any failure after out_dir is created, out_dir is removed, and
    the scratch database is dropped if, and only if, this call created it.
    """
    # .resolve(), not .absolute(): a worktree's data/site is a symlink into
    # the live lake (Task 1), and .absolute() does not follow it — an
    # unresolved out_dir could sit textually outside data_dir while actually
    # landing inside it once the symlink is followed (2026-10 review finding).
    out_dir = Path(out_dir).resolve()
    data_dir = Path(data_dir).resolve()
    _check_sam_window("before the copy")
    _refuse_password(pg_dsn)
    if out_dir.exists():
        raise FileExistsError(f"proof snapshot: {out_dir} already exists")
    if out_dir == data_dir or data_dir in out_dir.parents:
        raise ValueError(f"proof snapshot: {out_dir} is inside the lake {data_dir}")
    if not _SCRATCH_DB_RE.fullmatch(scratch_db):
        raise ValueError(
            f"proof snapshot: scratch database name {scratch_db!r} must match"
            f" {_SCRATCH_DB_RE.pattern}"
        )
    _check_scratch_name(scratch_db)
    source_db = _resolve_dbname(pg_dsn)
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
    created = {"out_dir": False, "db": False}
    try:
        copy_started = _now()
        try:
            out_dir.mkdir(parents=True)
            created["out_dir"] = True
            (out_dir / DUCKDB_REL.parent).mkdir()
            _clone(src_duckdb, out_dir / DUCKDB_REL)
            for name in CLONED_DIRS:
                _clone(data_dir / name, out_dir / name)
            _clone(data_dir / MANIFEST_REL, out_dir / MANIFEST_REL)
        finally:
            lock.close()
        _check_sam_interval(copy_started, _now(), "the copy")

        # Every pinned tree is scanned (_files raises on a symlink) and
        # digested BEFORE any database exists (ROADMAP #199).
        duckdb_sha_at_copy = _sha256_file(out_dir / DUCKDB_REL)
        parquet = _parquet_digest(out_dir / "parquet")
        site = _tree_digest(out_dir / "site")
        raw_docs = _tree_digest(out_dir / "raw_docs")
        manifest_jsonl_sha256 = _sha256_file(out_dir / MANIFEST_REL)
        views = _rewrite_duckdb_views(out_dir / DUCKDB_REL, old_root=data_dir, new_root=out_dir)
        pg = _pg_snapshot(
            pg_dsn, scratch_db, out_dir / "pg",
            old_raw_docs=data_dir / "raw_docs", new_raw_docs=out_dir / "raw_docs",
            new_root=out_dir, created=created,
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
            "parquet": parquet,
            "site": site,
            "raw_docs": raw_docs,
            "manifest_jsonl_sha256": manifest_jsonl_sha256,
            "pg": pg,
        }
        (out_dir / SNAPSHOT_MANIFEST).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (out_dir / SNAPSHOT_ENV).write_text(_env_script(manifest), encoding="utf-8")
        return manifest
    except BaseException:
        if created["db"]:
            _drop_scratch_database(pg_dsn, scratch_db)
        if created["out_dir"]:
            shutil.rmtree(out_dir, ignore_errors=True)
        raise
```

- [ ] **Step 5: Check the views by resolved path**

In `_rewrite_duckdb_views`, replace:

```python
        if left:
            raise RuntimeError(f"proof snapshot: views still read {old}: {sorted(r[0] for r in left)}")
        con.execute("checkpoint")
```

with:

```python
        if left:
            raise RuntimeError(f"proof snapshot: views still read {old}: {sorted(r[0] for r in left)}")
        # Hermeticity by RESOLVED path (ROADMAP #199): a view that spells the
        # lake through a symlink passes the string test above and would still
        # read the live parquet.
        root = Path(new_root).resolve()
        outside = [
            f"{name}: {path}"
            for name, sql_text in con.execute(
                "select view_name, sql from duckdb_views()"
                " where not internal and database_name = current_database()"
                " order by view_name"
            ).fetchall()
            for path in _view_parquet_paths(sql_text)
            if not _is_under(Path(path).resolve(), root)
        ]
        if outside:
            raise RuntimeError(
                f"proof snapshot: {len(outside)} view read(s) resolve outside the snapshot"
                f" {root}: {outside[:5]}"
            )
        con.execute("checkpoint")
```

- [ ] **Step 6: Record the created database and check document paths by resolved path**

Replace the whole function `_pg_snapshot` — from `def _pg_snapshot(` through its closing `    }` (the line before `def _env_script(manifest: dict) -> str:`) — with:

```python
def _pg_snapshot(
    pg_dsn: str, scratch_db: str, dump_dir: Path, *,
    old_raw_docs: Path, new_raw_docs: Path, new_root: Path, created: dict,
) -> dict:
    import psycopg
    from psycopg import sql

    source_db = _resolve_dbname(pg_dsn)
    scratch_dsn = _with_database(pg_dsn, scratch_db)
    dump_dir.mkdir()
    dump = dump_dir / f"{source_db}.dump"
    _run([_pg_bin("pg_dump"), "--format=custom", "--no-owner", "--no-privileges",
          f"--file={dump}", pg_dsn])
    with psycopg.connect(_with_database(pg_dsn, "postgres"), autocommit=True) as admin:
        admin.execute(sql.SQL("create database {}").format(sql.Identifier(scratch_db)))
    # snapshot() drops it after any later failure — and only because this
    # call made it (ROADMAP #199).
    created["db"] = True
    # Defense in depth before the destructive pg_restore: a libpq override
    # buried in pg_dsn could otherwise make scratch_dsn resolve somewhere
    # other than the database just created (2026-10 review finding).
    _assert_connected_to(scratch_dsn, scratch_db)
    _run([_pg_bin("pg_restore"), "--no-owner", "--no-privileges", "--exit-on-error",
          f"--dbname={scratch_dsn}", str(dump)])

    tables: dict[str, dict] = {}
    rewrites: dict[str, int] = {}
    with psycopg.connect(scratch_dsn) as con:
        _assert_current_database(con, scratch_db)
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
            # Hermeticity by RESOLVED path (ROADMAP #199): a symlinked
            # spelling of the live lake passes a prefix test.
            root = Path(new_root).resolve()
            outside = sorted(
                fp for (fp,) in con.execute(
                    "select distinct file_path from jbook_documents where file_path is not null"
                ).fetchall()
                if not _is_under(Path(fp).resolve(), root)
            )
            if outside:
                raise RuntimeError(
                    f"proof snapshot: {len(outside)} jbook_documents.file_path row(s) resolve"
                    f" outside the snapshot {root} (e.g. {outside[0]})"
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
```

- [ ] **Step 7: Quote the default path in `env.sh`**

Replace the whole function `_env_script` with:

```python
def _env_script(manifest: dict) -> str:
    """The snapshot's env.sh. The default path is a shlex-quoted assignment,
    overridden by "$1" when a RUN_DIR is passed (ROADMAP #199: the old
    "${1:-<path>}" broke on '}', '$' and '"' in the path)."""
    env = manifest["env"]
    return (
        f"# Written by `govbudget proof snapshot` at {manifest['created_at']}.\n"
        "# Usage: source env.sh [RUN_DIR]\n"
        "#   no argument: point export-site/dbt/verify-* at this snapshot itself;\n"
        "#   RUN_DIR:     a `cp -c -R` clone of this snapshot to export into.\n"
        f"_proof_dir={shlex.quote(env['GOVBUDGET_DATA'])}\n"
        'if [ -n "${1:-}" ]; then _proof_dir="$1"; fi\n'
        'export GOVBUDGET_DATA="$_proof_dir"\n'
        'export GOVBUDGET_DUCKDB="$_proof_dir/duckdb/govbudget.duckdb"\n'
        f"export GOVBUDGET_PG_DSN={shlex.quote(env['GOVBUDGET_PG_DSN'])}\n"
        "unset _proof_dir\n"
    )
```

- [ ] **Step 8: One exit convention for `govbudget proof`**

In `src/govbudget/cli.py`, replace the whole function `cmd_proof` — from `def cmd_proof(args) -> None:` through its last line `    sys.exit(0 if ok else 1)` (the line before `def main(argv=None) -> None:`) — with:

```python
def cmd_proof(args) -> None:
    """Families piece 1: pinned proof snapshots and the masked export diff.

    Exit codes (one convention for the follow-ups' tools, ROADMAP #199):
    0 EQUAL/PASS, 1 DIFFERENT/FAIL, 2 a tool error — one stderr line
    `proof <action>: ERROR — <message>`, never a traceback."""
    tool = f"proof {args.proof_action}"
    try:
        _cmd_proof(args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — every tool error exits 2, without a traceback
        message = str(e)
        if message.startswith(f"{tool}: "):
            message = message[len(tool) + 2:]
        print(f"{tool}: ERROR — {message}", file=sys.stderr)
        sys.exit(2)


def _cmd_proof(args) -> None:
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
    if args.write_noise is not None and not args.control:
        raise ValueError("--write-noise requires --control")
    noise_classes = None
    if args.noise_from is not None:
        noise_classes = proof.load_noise_classes(args.noise_from)
    report = proof.diff_trees(args.a, args.b, control=args.control, noise_classes=noise_classes)
    if args.write_noise is not None:
        # Only an EQUAL control vouches for its reorder classes (Fix round 4);
        # a DIFFERENT one writes nothing and fails below as usual.
        try:
            proof.write_noise_file(args.write_noise, report)
        except ValueError as e:
            print(e, file=sys.stderr)
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
```

- [ ] **Step 9: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_proof.py tests/test_era_fact_stability.py tests/test_era_s4_report.py -q 2>&1 | tail -1
"$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_TEST_PG_DSN" -Atc "select count(*) from pg_database where datname like 'govbudget_proof_%'"
uvx --offline ruff check --isolated --select F,E9 src/govbudget/proof.py | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/cli.py | grep '^Found'
```

Expected: `176 passed` (152 + 17 + 7); `0` (no scratch database is left on the test cluster); `All checks passed!` for `proof.py`; `Found 5 errors.` for `cli.py`, its HEAD baseline (measured 2026-10-13; spec §7 W1), so nothing new.

- [ ] **Step 10: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/proof.py GovBudget/src/govbudget/cli.py GovBudget/tests/test_proof.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(proof): snapshot checks hermeticity by resolved path, the whole copy against the SAM window, trees before create database; cleans up after itself; quoted env.sh; tool errors exit 2 (#199)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `3 files changed`.
