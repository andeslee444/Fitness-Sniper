<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 1: Workspace and test harness

**Spec:** Global constraints (Python via `uv run --project .`, site via `npm`, Postgres tests on a throwaway cluster, real-data reads through `GOVBUDGET_DATA`/`GOVBUDGET_PG_DSN`); §8 "Proofs run on pinned snapshots" (where snapshots live); §9 S0 (workspace for every later step, including the S0 site builds of Tasks 4 and 5: this checkout's own dbt manifest per ROADMAP #173, and the `data/site` link).

**Files:**
- Create: `scripts/era/env.sh`
- Modify: `.gitignore` (append after line 19, `/tmp/`)
- Local only, never committed: `.venv` (uv), `site/node_modules` (npm), the cluster at `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/testpg`, one line appended to the shared `/Users/andeslee/Documents/Cursor-Projects/.git/info/exclude`, this checkout's dbt parse output (`dbt/target/`, `dbt/logs/`, `dbt/.user.yml`; ignored by `.gitignore` lines 7, 9, 10), the symlink `data/site -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site` (ignored by the shared exclude's `GovBudget/data/site`, line 26)
- Test (existing, unchanged): `tests/jbooks/test_p1_loader.py`, `tests/test_roadmap_backlog.py`

**Interfaces:**
Consumes: nothing.
Produces:
- `scripts/era/env.sh` (sourced, bash or zsh, from the worktree's `GovBudget/`): exports `GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data`, `GOVBUDGET_DUCKDB=$GOVBUDGET_DATA/duckdb/govbudget.duckdb`, `GOVBUDGET_PG_DSN=postgresql://localhost/govbudget`, `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres`, `GOVBUDGET_PG_BIN=/opt/homebrew/opt/postgresql@17/bin` (unless already set), `GOVBUDGET_PROOFS=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs`. Every later task's shell starts with `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh`.
- A running throwaway Postgres 17 cluster on `127.0.0.1:55432` (data dir `.proofs/testpg`, log `.proofs/testpg.log`, superuser = the OS user, trust auth, locale C).
- `.proofs/` ignored in the worktree (`GovBudget/.gitignore`) and, until this branch merges, in the main checkout (shared `info/exclude`).
- `dbt/target/manifest.json` written by THIS checkout's own `dbt parse` (163 test nodes, the same set as main's manifest and the live `site_meta.build_checks.dbt_assertions`). `site/src/lib/data.ts:649-671` (`dbtAssertionCount`, ROADMAP #173, called from `getSiteMeta` at `:627`) throws during a production site build when the checkout has no manifest, and `site/src/__tests__/dbt-assertion-count.test.ts:62-71` reads it in `npm run test`, so Tasks 4 (Step 14) and 5 build only after this exists. Never copy another checkout's manifest: #173 exists because /methodology/ printed another checkout's count. Tasks 13, 15, 16 and 21 rewrite it through `govbudget build`.
- The symlink `data/site -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site`. The site build reads `site/../data/site` unconditionally (`site/scripts/prepare-assets.mjs:17-19`, `site/src/lib/data.ts:36-39`), and the worktree's `data/` is a real directory that holds only the tracked `manifest.jsonl` and `research/`. Tasks 4 (Step 13) and 5 (Step 12) only check the link and `test -f dbt/target/manifest.json`; a task that needs a snapshot's site re-points the link itself.

Measured for this task (2026-10-02): `uv sync --dry-run` → "Resolved 84 packages", "Would install 83 packages" (lock pins duckdb 1.5.3, psycopg 3.3.4, pytest 9.0.3); the worktree `.venv` exists but has no packages (`import govbudget` fails). `site/node_modules` is absent; the lockfile has 1,259 entries, `next` 16.2.9, `vitest` 3.2.6 (main checkout). Postgres binaries: only `/opt/homebrew/opt/postgresql@17/bin` (server 17.8), none on `PATH`. `pg_ctl start` without `LC_ALL=C` dies with "FATAL: postmaster became multithreaded during startup" (reproduced on a scratch cluster); with it, the cluster starts and `tests/jbooks/test_p1_loader.py` gives `12 passed`. `tests/test_roadmap_backlog.py` gives `25 passed`. `.gitignore` has 19 lines and no `.proofs` rule; `git check-ignore` matches nothing for `GovBudget/.proofs/x` in either checkout; the shared `info/exclude` has 31 lines. Port 55432 is free (`lsof -nP -iTCP:55432 -sTCP:LISTEN` prints nothing). The worktree has no `dbt/target/` and no `data/site`; `git check-ignore -v data/site` already prints `/Users/andeslee/Documents/Cursor-Projects/.git/info/exclude:26:GovBudget/data/site	data/site` (`.gitignore`'s `data/site/` is a directory pattern and would not match a symlink). `dbt parse` (dbt-core 1.11.11, dbt-duckdb 1.10.1, the `uv.lock` pins) run on a scratch copy of this worktree's `dbt/` with `GOVBUDGET_DUCKDB` on a scratch path: 2.4 s, full parse, `MissingArgumentsPropertyInGenericTestDeprecation: 22 occurrences`, writes `target/{manifest.json, partial_parse.msgpack, perf_info.json, semantic_manifest.json}`, `logs/dbt.log` and `.user.yml`, and does NOT create the DuckDB file. Its manifest has 163 test nodes, the identical set of node ids to main's `dbt/target/manifest.json` (163, dbt 1.11.11, generated 2026-10-02T00:10:09Z); live `data/site/json/site_meta.json` `build_checks` = `{'dbt_assertions': 163, 'eval_questions': 48, 'eval_threshold': 44, 'npm_gates': 27}`.

- [ ] **Step 1: Install the Python environment**

Run (from `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget`):

```bash
uv sync
uv run --project . python -c "import govbudget, duckdb, psycopg, pytest; print(duckdb.__version__, psycopg.__version__, pytest.__version__)"
```

Expected: `uv sync` prints `Resolved 84 packages`, then `Installed 83 packages` (or `Audited 83 packages` if already synced); the check prints `1.5.3 3.3.4 9.0.3`.

- [ ] **Step 2: Install the site's node_modules (real, not a symlink)**

```bash
cd site && npm ci && node -p "require('next/package.json').version + ' ' + require('vitest/package.json').version" && test -x node_modules/.bin/next && cd ..
```

Expected: npm ends with `added <N> packages, and audited <M> packages in <t>s` (N close to the lockfile's 1,259 entries; optional platform packages vary), then `16.2.9 3.2.6`.

- [ ] **Step 3: Write the env helper**

Create `scripts/era/env.sh`:

```sh
# Families piece 1 (era procurement history): the shell environment every task
# in the plan starts from. SOURCE it (bash or zsh) from the worktree's
# GovBudget/ directory:
#
#     source scripts/era/env.sh
#
# Points reads at the LIVE lake and the live Postgres (the plan writes to them
# only in its named tasks) and points tests at the throwaway cluster on
# 127.0.0.1:55432 — never at the real server. For a pinned proof snapshot,
# source <snapshot>/env.sh [RUN_DIR] instead (written by `govbudget proof
# snapshot`). config.py builds every lake path from GOVBUDGET_DATA and ignores
# GOVBUDGET_DUCKDB; dbt and `govbudget build` read GOVBUDGET_DUCKDB, so both
# are set, consistently.
_era_common="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
if [ -z "$_era_common" ]; then
  echo "scripts/era/env.sh: source me from inside the GovBudget checkout" >&2
  return 1
fi
_era_main="$(dirname "$_era_common")/GovBudget"   # the main checkout owns the lake
export GOVBUDGET_DATA="$_era_main/data"
export GOVBUDGET_DUCKDB="$GOVBUDGET_DATA/duckdb/govbudget.duckdb"
export GOVBUDGET_PG_DSN="postgresql://localhost/govbudget"
export GOVBUDGET_TEST_PG_DSN="postgresql://127.0.0.1:55432/postgres"
export GOVBUDGET_PG_BIN="${GOVBUDGET_PG_BIN:-/opt/homebrew/opt/postgresql@17/bin}"
export GOVBUDGET_PROOFS="$_era_main/.proofs"
unset _era_common _era_main
```

Run:

```bash
source scripts/era/env.sh && env | grep '^GOVBUDGET_' | sort && test -f "$GOVBUDGET_DUCKDB" && echo lake-ok
```

Expected (exactly these six lines, then `lake-ok`):

```
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data
GOVBUDGET_DUCKDB=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb
GOVBUDGET_PG_BIN=/opt/homebrew/opt/postgresql@17/bin
GOVBUDGET_PG_DSN=postgresql://localhost/govbudget
GOVBUDGET_PROOFS=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres
lake-ok
```

- [ ] **Step 4: Ignore `.proofs/` in both checkouts**

Edit `.gitignore` — after the last line (line 19), append:

Before (lines 16-19):
```
# PDF page caches (config.ROOT/"tmp"/"pdfs", program_pdf_receipts.py) —
# derived, ~0.5 GB, files up to ~52 MB; must never reach the fiscalreceipts
# subtree publish.  Anchored: only GovBudget/tmp/, not every dir named tmp.
/tmp/
```
After (lines 16-22):
```
# PDF page caches (config.ROOT/"tmp"/"pdfs", program_pdf_receipts.py) —
# derived, ~0.5 GB, files up to ~52 MB; must never reach the fiscalreceipts
# subtree publish.  Anchored: only GovBudget/tmp/, not every dir named tmp.
/tmp/
# Proof snapshots and the throwaway test Postgres cluster (families piece 1,
# scripts/era/env.sh): APFS clones of the lake; never committed or published.
/.proofs/
```

The snapshots live in the MAIN checkout (`/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs`), whose `.gitignore` gets this rule only when the branch merges, so also add it to the shared exclude file (idempotent):

```bash
EXCL="$(git rev-parse --path-format=absolute --git-common-dir)/info/exclude"
grep -qxF 'GovBudget/.proofs/' "$EXCL" || printf 'GovBudget/.proofs/\n' >> "$EXCL"
mkdir -p "$GOVBUDGET_PROOFS"
git -C /Users/andeslee/Documents/Cursor-Projects check-ignore -v GovBudget/.proofs/testpg
git -C /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families check-ignore -v GovBudget/.proofs/testpg
```

Expected: `.git/info/exclude:32:GovBudget/.proofs/	GovBudget/.proofs/testpg` (the exclude path may print absolute), then `GovBudget/.gitignore:22:/.proofs/	GovBudget/.proofs/testpg`.

- [ ] **Step 5: Create and start the throwaway test cluster**

```bash
lsof -nP -iTCP:55432 -sTCP:LISTEN || echo port-free
LC_ALL=C "$GOVBUDGET_PG_BIN/initdb" -D "$GOVBUDGET_PROOFS/testpg" --locale=C -E UTF8 --auth=trust
LC_ALL=C "$GOVBUDGET_PG_BIN/pg_ctl" -D "$GOVBUDGET_PROOFS/testpg" -l "$GOVBUDGET_PROOFS/testpg.log" \
  -o "-c listen_addresses=127.0.0.1 -c port=55432 -c unix_socket_directories=''" -w start
"$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_TEST_PG_DSN" -Atc "select current_user, split_part(version(), ' ', 2)"
```

Expected: `port-free`; initdb ends with `Success. You can now start the database server using:`; pg_ctl prints `waiting for server to start.... done` and `server started`; psql prints `andeslee|17.8`. `LC_ALL=C` is required on `pg_ctl` too — without it the log says `FATAL:  postmaster became multithreaded during startup`.

After a reboot, restart with the same `LC_ALL=C ... pg_ctl ... -w start` line. Stop it (at the end of the plan) with `"$GOVBUDGET_PG_BIN/pg_ctl" -D "$GOVBUDGET_PROOFS/testpg" stop`.

- [ ] **Step 6: Prove the harness — the loader tests run against the throwaway cluster, not skipped**

```bash
uv run --project . pytest tests/jbooks/test_p1_loader.py -q -rs
uv run --project . pytest tests/test_roadmap_backlog.py -q
"$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_TEST_PG_DSN" -Atc "select datname from pg_database where datname like 'govbudget_test%'"
```

Expected: `12 passed` with no `SKIPPED` line (a skip means the cluster is down: redo Step 5); `25 passed`; `govbudget_test` (the jbooks fixture database now exists on 127.0.0.1:55432, so the fixtures ran against the throwaway cluster).

- [ ] **Step 7: Write this checkout's own dbt manifest and link `data/site` (both needed by every site build in the worktree)**

A production site build throws without `dbt/target/manifest.json` (`site/src/lib/data.ts:649-671`, ROADMAP #173), and the worktree has none until dbt runs here. `dbt parse` writes it from this checkout's own models and tests. It builds nothing and opens no warehouse; `GOVBUDGET_DUCKDB` points at a scratch path anyway, so even a dbt change of behaviour could not touch the lake. Never copy another checkout's manifest instead: that is the bug #173 fixed.

```bash
source scripts/era/env.sh
GOVBUDGET_DUCKDB="$GOVBUDGET_PROOFS/dbt-parse.duckdb" uv run --project . dbt parse --project-dir dbt --profiles-dir dbt
test ! -e "$GOVBUDGET_PROOFS/dbt-parse.duckdb" && echo no-warehouse-opened
uv run --project . python -c "import json;n=json.load(open('dbt/target/manifest.json'))['nodes'];print(sum(v.get('resource_type')=='test' for v in n.values()))"
```

Expected: dbt logs `Registered adapter: duckdb=1.10.1`, `Unable to do partial parsing because saved manifest not found. Starting full parse.`, a `MissingArgumentsPropertyInGenericTestDeprecation: 22 occurrences` summary (pre-existing, harmless) and `Performance info: dbt/target/perf_info.json`, exit 0, in about 3 s; then `no-warehouse-opened`; then `163` — the same count as main's manifest and as the live `site_meta.build_checks.dbt_assertions`. Any other number means this checkout's `dbt/` differs from main's: stop and diff `dbt/` against main before going on.

Then link the live export where the site build looks for it (idempotent; a link that is already there, even one a later task re-pointed at a snapshot, is left alone):

```bash
{ [ -L data/site ] || [ -e data/site ]; } || ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site data/site
EXCL="$(git rev-parse --path-format=absolute --git-common-dir)/info/exclude"
git check-ignore -q data/site || printf 'GovBudget/data/site\n' >> "$EXCL"
readlink data/site
git check-ignore -q data/site && echo data-site-ignored
test -f data/site/json/site_meta.json && test -f dbt/target/manifest.json && echo site-build-inputs-ok
git status --short -- dbt data
```

Expected: `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site`, `data-site-ignored`, `site-build-inputs-ok`, and no `git status` output (`dbt/target/`, `dbt/logs/`, `dbt/.user.yml` are in `.gitignore`; the shared exclude already lists `GovBudget/data/site` at line 26, so the append never runs today).

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/.gitignore GovBudget/scripts/era/env.sh && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(era): env helper and ignored .proofs/ for families piece 1 (Task 1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `2 files changed`. `git status --short -- GovBudget` is empty afterwards (`.venv`, `site/node_modules`, `.proofs`, `dbt/target/`, `dbt/logs/`, `dbt/.user.yml` and the `data/site` link are all ignored).
