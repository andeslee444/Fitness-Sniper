<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 21d: Release-1 proof — preconditions, the A worktree, W1, and snapshots fu-pre/fu-post

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §7 "Snapshots" (two snapshots of one live state back to back in one SAM-safe window; their pins equal, else retake both), "Code under test" (A = `git merge-base main HEAD`, proven equal to the deployed 916ae88e in `src/`, `dbt/`, `data-seeds/`, `scripts/`, in a detached worktree with its own `dbt parse` manifest; B = the release HEAD), W1 (pytest, vitest, pyflakes on touched modules: no finding beyond the HEAD baseline, `cli.py` 5, `export_site.py` 10), §2.3 Q24.

**Files:**
- No tracked file changes. Local only (ignored): `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/{fu-pre,fu-post,fu-logs}/`, the detached worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a`, the worktree's `dbt/target/` (rewritten by `dbt parse`). Shared Postgres: creates the scratch databases `govbudget_proof_fu_pre` and `govbudget_proof_fu_post` only (through `govbudget proof snapshot`).

Shell state does not persist between blocks: every block re-derives `P="$GOVBUDGET_PROOFS"` and `L="$P/fu-logs"`, and the A and B shas are written to `$L/shas.txt` (line 1 A, line 2 B, line 3 the deployed sha that A was proven equal to) in Step 3 and read back where used.

**Interfaces:**
Consumes:
- Tasks 1–20 committed on this branch, in particular: Task 6's `dbt/seeds/p1_route_safe_codes.csv` (one row: account `0390D`, line_item_code `O&M`, page_key `0390DOM`); Task 7's `scripts/era/s194_chem_demil.py` (`--check` / `--dry-run` / `--apply --revert-file` / `--revert --revert-file`, README decision 1) and the removal of `scripts/clean_junk_pe_bli.py`; Task 9's `decided_on` in `dbt/models/marts/p1_era_line_map.sql`; Task 10's B7 row in `dbt/seeds/p1_era_code_decisions.csv` (ruling `R-DEC-ERA-B7`); Task 13's `split_years_matrix`, `merge_years_matrix`, `_YEARS_MATRIX_MAX_BYTES`, `_YEARS_MATRIX_CORE_GZIP_MAX`.
- Task 2's hardened `govbudget proof snapshot --out DIR --scratch-db govbudget_proof_<name>` (writes `DIR/{duckdb/govbudget.duckdb, parquet/, site/, raw_docs/, manifest.jsonl, pg/<db>.dump, snapshot.json, env.sh}`; refuses during the SAM window, while a DuckDB writer holds the lake, or when `DIR` or the database exists; on a failure after `create database` it drops only the database it created).
- Task 21a's `scripts/fu/snapshot_pins.py compare`.
- `govbudget era-map check --strict` (piece-1 Task 12): `era-map check: <u> undecided chain(s), <s> stale decision(s)`.
Also consumes the red window Tasks 20a and 20c declare (G3 notes C1): exactly four tests fail between Task 20 and this proof's re-pin.
Produces (kept until Task 22e's cleanup offer):
- `.proofs/fu-pre` (scratch database `govbudget_proof_fu_pre`: the pre-write reference; its database is written only by Task 21f Steps 4–5, the `--apply`/`--revert` rehearsal after both fu-pre exports (README decision 2), which must leave every Postgres pin as Task 21e Step 1 took it) and `.proofs/fu-post` (scratch database `govbudget_proof_fu_post`, where Task 21e runs the write the release must reach);
- `.proofs/fu-logs/shas.txt` (A sha, B sha, deployed sha), `snapshot-fu-pre.log`, `snapshot-fu-post.log`, `snapshot-times.txt`, `snapshot-shas.json`, `pins-fu-pre-fu-post.txt`, `dbt-tests.txt`, `w1-*.log`, `prewrite-live.txt`;
- the A worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a` (detached at A, its own `.venv` and `dbt/target/manifest.json`, `tmp/pdfs` cache), used by Task 21f's A export and Task 22b's abort path.

Measured for this task (2026-10-13, read-only, outside :12–:22): `git merge-base main HEAD` is `7dccd983` (local `main`), and `git diff --stat 916ae88e 7dccd983 -- GovBudget/src GovBudget/dbt GovBudget/data-seeds GovBudget/scripts GovBudget/site` prints nothing (7dccd983 only stamps the ROADMAP); `dbt/target/manifest.json` has 196 test nodes; `uvx --offline ruff check --isolated --select F,E9 src/govbudget/cli.py src/govbudget/export_site.py` reports 15 findings (cli.py 5, export_site.py 10; ruff 0.16.10 from the uv cache); live Postgres `budget_lines` has 159,903 rows, 16 with a `pe_bli` matching `[&#/?%[:space:]]` (PB2024 ids 349016–349025, PB2025 ids 47733–47738) and none equal to `0390DOM`; the live `p1_era_line_map` has 17 columns and no `decided_on`; there is no `p1_route_safe_codes` relation; the database is 1,047 MB with 18 public base tables; `.proofs/` holds only `testpg` and `testpg.log`; the worktree's `tmp/pdfs` holds the 21 `*-program-pages-v1.json` caches.

- [ ] **Step 1: The wave's code is in place and the worktree is clean**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
git -C .. status --porcelain -- GovBudget | grep -v '^??'; echo "(tracked changes above: expect none)"
uv run --project . python - <<'PY'
import csv
from pathlib import Path
rows = list(csv.DictReader(open("dbt/seeds/p1_route_safe_codes.csv", newline="")))
print("route-safe seed:", [(r["account"], r["line_item_code"], r["page_key"]) for r in rows])
seed = list(csv.DictReader(open("dbt/seeds/p1_era_code_decisions.csv", newline="")))
print("B7 seed rows:", sum(1 for r in seed if "R-DEC-ERA-B7" in r.values()), "of", len(seed))
print("s194 present:", Path("scripts/era/s194_chem_demil.py").is_file(),
      "| clean_junk_pe_bli retired:", not Path("scripts/clean_junk_pe_bli.py").exists())
print("map model has decided_on:", "decided_on" in Path("dbt/models/marts/p1_era_line_map.sql").read_text())
from govbudget import export_site as e
print("years split/merge:", callable(e.split_years_matrix), callable(e.merge_years_matrix),
      e._YEARS_MATRIX_MAX_BYTES, e._YEARS_MATRIX_CORE_GZIP_MAX)
PY
uv run --project . python scripts/era/s194_chem_demil.py --help | grep -c -- '--revert'
```
Expected: no tracked change; `route-safe seed: [('0390D', 'O&M', '0390DOM')]`; `B7 seed rows: 1 of <n>` (the O&M chain's one row; `<n>` is the seed's row count, 1,253 if Task 10's propose replaced the chain's R-DEC-ERA-EXCLUDE row as design Q25 says); `s194 present: True | clean_junk_pe_bli retired: True`; `map model has decided_on: True`; `years split/merge: True True 4194304 780074`; then `1` (or more). Anything else: the task that owns it is not done; stop.

- [ ] **Step 2: The live lake is still in the pre-write state (read-only)**

The proof starts from the live state the release will write (design §8 step 1). This reads the live lake and Postgres, so it carries the SAM guard:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs" && mkdir -p "$L"
"$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_PG_DSN" -At -F' | ' -c "select count(*) from budget_lines;" -c "select count(*) from budget_lines where pe_bli ~ '[&#/?%[:space:]]';" -c "select count(*) from budget_lines where pe_bli = '0390DOM';" -c "select fiscal_year, pe_bli, line_item_code, count(*), sum(amount_thousands) from budget_lines where account = '0390D' and exhibit = 'P-1' and fiscal_year >= 2024 group by 1, 2, 3 order by 1, 2, 3;" > "$L/prewrite-live.txt" 2>&1
uv run --project . python -c "import duckdb,os; c=duckdb.connect(os.environ['GOVBUDGET_DUCKDB'], read_only=True); cols=[r[0] for r in c.execute('describe p1_era_line_map').fetchall()]; print('map columns', len(cols), 'decided_on' in cols); print('route-safe relation', c.execute(\"select count(*) from duckdb_tables() where table_name = 'p1_route_safe_codes'\").fetchone()[0])" >> "$L/prewrite-live.txt" 2>&1
uv run --project . python -m govbudget era-map check --strict > "$L/prewrite-era-check.log" 2>&1; echo "era-map check exit=$?" >> "$L/prewrite-live.txt"; tail -1 "$L/prewrite-era-check.log" >> "$L/prewrite-live.txt"
cat "$L/prewrite-live.txt"
```
Expected:
```
159903
16
0
2024 | O&M | O&M | 5 | 325095
2024 | RDT&E | RDT&E | 5 | 3979637
2025 | FY2024CR | FY2024CR | 1 | -32026
2025 | O&M | O&M | 3 | 194641
2025 | RDT&E | RDT&E | 3 | 2732528
map columns 17 False
route-safe relation 0
era-map check exit=0
era-map check: 0 undecided chain(s), 0 stale decision(s)
```
The committed seed already carries B7 (Step 1), and `era-map check` hashes the lake's era keys against it, which the write does not touch. If Postgres already holds `0390DOM` rows or the map has `decided_on`, the live lake is not in the pre-write state: stop and report (someone ran a live write early; the proof below would prove the wrong transition).

- [ ] **Step 3: Record A and B, and prove A is the deployed code**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs" && cd .. || exit 1
A_SHA=$(git merge-base main HEAD) && B_SHA=$(git rev-parse HEAD) && git log -1 --format='A: %h %s' "$A_SHA" && git log -1 --format='B: %h %s' "$B_SHA"
LIVE=$(curl -s https://fiscalreceipts.com/.build-meta.json | python3 -c "import json,sys; print(json.load(sys.stdin)['git_head'])") || { echo "STOP: could not read the deployed git_head from /.build-meta.json"; exit 1; }
echo "deployed: $LIVE" && git diff --quiet "$LIVE" "$A_SHA" -- GovBudget/src GovBudget/dbt GovBudget/data-seeds GovBudget/scripts GovBudget/site && echo "A's src/ dbt/ data-seeds/ scripts/ site/ equal the deployed $(git rev-parse --short=8 "$LIVE")" && printf '%s\n%s\n%s\n' "$A_SHA" "$B_SHA" "$LIVE" > "$L/shas.txt" && cat "$L/shas.txt"
```
Expected: `A: 7dccd983 docs(roadmap): stamp the families piece 1 deploy (916ae88e, rollback tag 2026-10-04T210918Z)` (or a later `main` commit if `main` moved; the equality line is what matters), `B: <short sha> <Task 21c's subject>`, `deployed: 916ae88eee04f1e2445040933f83a3e279c04209` (production's `/.build-meta.json` `git_head`, read as Task 25b Step 1 reads it, never typed), `A's src/ dbt/ data-seeds/ scripts/ site/ equal the deployed 916ae88e` (README decision 4 names `site/` too), and the three shas (`shas.txt`: line 1 A, line 2 B, line 3 the deployed sha). If the equality line is missing, `main` holds code production does not run, or production was redeployed from code this branch does not hold (`git diff` cannot resolve the sha): stop and report (A must be the deployed code).

- [ ] **Step 4: Check out A in a detached worktree with its own dbt manifest**

`export-site` reads the code checkout's `dbt/target/manifest.json` for `site_meta.build_checks.dbt_assertions`; `dbt parse` writes it from A's own `dbt/` without opening a warehouse (piece-1 Task 21 Step 13's method):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs" && A_SHA=$(sed -n 1p "$L/shas.txt") && : "${A_SHA:?run Step 3 first}"
cd .. && git worktree add --detach /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a "$A_SHA" || exit 1
mkdir -p /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a/GovBudget/tmp/pdfs && cp -c /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/pdfs/*-program-pages-v1.json /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a/GovBudget/tmp/pdfs/
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a/GovBudget && uv sync --frozen > "$L/uv-sync-a.log" 2>&1; echo "uv sync exit=$?"
source scripts/era/env.sh && GOVBUDGET_DUCKDB="$GOVBUDGET_PROOFS/dbt-parse-a.duckdb" uv run --project . dbt parse --project-dir dbt --profiles-dir dbt > "$L/dbt-parse-a.log" 2>&1; echo "parse exit=$?"; test ! -e "$GOVBUDGET_PROOFS/dbt-parse-a.duckdb" && echo no-warehouse-opened
ls tmp/pdfs | wc -l; git log -1 --format='%h %s'
```
Expected: `Preparing worktree (detached HEAD <A short sha>)`, `uv sync exit=0`, `parse exit=0`, `no-warehouse-opened`, `21`, and A's subject. No stash anywhere.

- [ ] **Step 5: B's dbt manifest, and both test-node counts**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs"
GOVBUDGET_DUCKDB="$GOVBUDGET_PROOFS/dbt-parse-b.duckdb" uv run --project . dbt parse --project-dir dbt --profiles-dir dbt > "$L/dbt-parse-b.log" 2>&1; echo "parse exit=$?"; test ! -e "$GOVBUDGET_PROOFS/dbt-parse-b.duckdb" && echo no-warehouse-opened
uv run --project . python - /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a/GovBudget/dbt/target/manifest.json dbt/target/manifest.json <<'PY' | tee "$L/dbt-tests.txt"
import json, sys
names = ("assert_budget_lines_route_safe_pe_bli", "assert_route_safe_codes_valid")
for side, path in zip("AB", sys.argv[1:]):
    nodes = json.load(open(path))["nodes"].values()
    tests = [n for n in nodes if n.get("resource_type") == "test"]
    print(f"{side}: {len(tests)} dbt test nodes;", {name: any(n["name"] == name for n in tests) for name in names},
          "decided_on not_null:", any(n["name"] == "not_null_p1_era_line_map_decided_on" for n in tests))
PY
```
Expected: `parse exit=0`, `no-warehouse-opened`, `A: 196 dbt test nodes; {…: False, …: False} decided_on not_null: False`, and `B: <n> dbt test nodes; {'assert_budget_lines_route_safe_pe_bli': True, 'assert_route_safe_codes_valid': True} decided_on not_null: True` with `<n>` above 196. `<n>` is the count B's exports publish as `site_meta.build_checks.dbt_assertions` (P2's rule) and /methodology/ prints.

- [ ] **Step 6: W1 — pytest, vitest and pyflakes on the touched modules**

pytest runs on the throwaway cluster; the full suite takes minutes:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs"
"$GOVBUDGET_PG_BIN/pg_isready" -h 127.0.0.1 -p 55432
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q > "$L/w1-pytest.log" 2>&1; echo "pytest exit=$?"; tail -1 "$L/w1-pytest.log"
(cd site && npm test > "$L/w1-vitest.log" 2>&1); echo "vitest exit=$?"; grep -E "Test Files|Tests " "$L/w1-vitest.log" | tail -2
A_SHA=$(sed -n 1p "$L/shas.txt") && A_ROOT=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a/GovBudget
git -C .. diff --name-only --diff-filter=AM "$A_SHA" HEAD -- 'GovBudget/src/*.py' 'GovBudget/scripts/*.py' | sed 's#^GovBudget/##' > "$L/w1-touched.txt"; wc -l < "$L/w1-touched.txt"
while read -r f; do h=$(uvx --offline ruff check --isolated --select F,E9 --output-format concise "$f" 2>/dev/null | grep -c "^$f:"); if [ -f "$A_ROOT/$f" ]; then a=$(cd "$A_ROOT" && uvx --offline ruff check --isolated --select F,E9 --output-format concise "$f" 2>/dev/null | grep -c "^$f:"); else a=0; fi; echo "$f HEAD $h base $a"; done < "$L/w1-touched.txt" > "$L/w1-ruff.txt"; cat "$L/w1-ruff.txt"; awk '{ if ($3 > $5) bad = 1 } END { print (bad ? "W1 pyflakes: FAIL" : "W1 pyflakes: PASS") }' "$L/w1-ruff.txt"
```
Expected: `127.0.0.1:55432 - accepting connections`; `pytest exit=1` with the last line `3 failed, <n> passed …`, and `vitest exit=1` with `Tests  1 failed | <m> passed` — exactly the four tests Tasks 20a and 20c leave red by design until this proof re-pins the F-15 fixtures (`tests/test_f15_era_identity.py::test_golden_rebuild_from_fixtures_is_byte_identical`, `::test_fresh_state_with_decade_era_map_receipts_keeps_every_byte`, `::test_allowed_formula_competitor_changes_exactly_one_cell`, and `site/scripts/gates/__tests__/f15-page-snapshot.test.mjs` › "committed baseline (tests/fixtures/f15/page_snapshot.json) › is present, well-formed and of this schema"); check with `grep -E '^FAILED' "$L/w1-pytest.log"` and `grep -E 'FAIL|✗|×' "$L/w1-vitest.log"` that no other test failed (any other failure is fixed in the task that introduced it before the snapshots are taken); Task 21g turns the three Python goldens green, Task 21h the vitest one; the number of touched modules; one `<file> HEAD <h> base <a>` line per module, `src/govbudget/cli.py HEAD 5 base 5` and `src/govbudget/export_site.py HEAD 10 base 10` if both were touched (fewer is fine), every new file `base 0` with `HEAD 0`; last line `W1 pyflakes: PASS`. A failure here is fixed in the task that introduced it before the snapshots are taken.

- [ ] **Step 7: Take snapshots fu-pre and fu-post back to back (shared Postgres: creates two scratch databases)**

Both copies must see one live state (design §7). Start only between :23 and :40, so both finish before the next SAM window (each snapshot clones the lake in seconds, then dumps and restores the 1 GB database; the tool refuses on its own at :15–:20). On `WAIT`, re-run the block later.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -lt 23 ] || [ "$MIN" -gt 40 ]; then echo "WAIT: start between :23 and :40 (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
for n in fu-pre fu-post; do if [ -e "$P/$n" ]; then echo "STOP: $P/$n exists"; exit 1; fi; done
echo "fu-pre start $(date +%Y-%m-%dT%H:%M:%S)" | tee "$L/snapshot-times.txt"
uv run --project . python -m govbudget proof snapshot --out "$P/fu-pre" --scratch-db govbudget_proof_fu_pre > "$L/snapshot-fu-pre.log" 2>&1; echo "fu-pre exit=$?" | tee -a "$L/snapshot-times.txt"
echo "fu-post start $(date +%Y-%m-%dT%H:%M:%S)" | tee -a "$L/snapshot-times.txt"
uv run --project . python -m govbudget proof snapshot --out "$P/fu-post" --scratch-db govbudget_proof_fu_post > "$L/snapshot-fu-post.log" 2>&1; echo "fu-post exit=$?" | tee -a "$L/snapshot-times.txt"
echo "fu-post end $(date +%Y-%m-%dT%H:%M:%S)" | tee -a "$L/snapshot-times.txt"; tail -5 "$L/snapshot-fu-pre.log" "$L/snapshot-fu-post.log"
```
Expected: `fu-pre exit=0` and `fu-post exit=0`, each log ending with the snapshot summary (`proof snapshot: …/.proofs/fu-pre`, the DuckDB sha and views repointed, file counts, `postgres govbudget -> govbudget_proof_fu_pre (18 tables, …)`, `source …/env.sh [RUN_DIR]`; likewise for fu-post), and the three timestamps, kept with the two exit lines in `$L/snapshot-times.txt` (the proof note's durations: fu-pre = `fu-post start` − `fu-pre start`, fu-post = `fu-post end` − `fu-post start`; a retake rewrites the file). If either refuses (SAM window, a DuckDB writer, an existing database), discard both and retake them together in a later window (a refused snapshot leaves no database it did not create; Task 2):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"
for n in fu_pre fu_post; do "$GOVBUDGET_PG_BIN/psql" postgresql://localhost/postgres -At -c "select datname from pg_database where datname = 'govbudget_proof_$n'" | grep -q . && "$GOVBUDGET_PG_BIN/dropdb" "govbudget_proof_$n"; done
rm -rf "${P:?}/fu-pre" "${P:?}/fu-post"; ls "$P"
```
Expected: `ls` lists neither `fu-pre` nor `fu-post`. Then re-run the snapshot block.

- [ ] **Step 8: The two snapshots carry the same pins**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
uv run --project . python scripts/fu/snapshot_pins.py compare "$P/fu-pre" "$P/fu-post" > "$L/pins-fu-pre-fu-post.txt" 2>&1; echo "exit=$?"; cat "$L/pins-fu-pre-fu-post.txt"
uv run --project . python - "$P" > "$L/snapshot-shas.json" <<'PY'
import json, sys
out = {}
for name in ("fu-pre", "fu-post"):
    m = json.load(open(f"{sys.argv[1]}/{name}/snapshot.json"))
    out[name] = {"created_at": m["created_at"], "duckdb_sha256_at_copy": m["duckdb"]["sha256_at_copy"],
                 "duckdb_sha256": m["duckdb"]["sha256"], "views_rewritten": m["duckdb"]["views_rewritten"],
                 "site_sha256": m["site"]["sha256"], "raw_docs_sha256": m["raw_docs"]["sha256"],
                 "manifest_jsonl_sha256": m["manifest_jsonl_sha256"], "pg_dump_sha256": m["pg"]["dump_sha256"],
                 "pg_tables": len(m["pg"]["tables"]), "budget_lines": m["pg"]["tables"]["budget_lines"],
                 "scratch_dsn": m["pg"]["scratch_dsn"]}
print(json.dumps(out, indent=1))
PY
cat "$L/snapshot-shas.json"
```
Expected: `exit=0`, `snapshot-pins: EQUAL`; the JSON with equal `duckdb_sha256_at_copy`, `site_sha256`, `raw_docs_sha256` and `manifest_jsonl_sha256` on both sides, `pg_tables` 18, `budget_lines` `{"rows": 159903, "md5": <same on both>}`, different `pg_dump_sha256` (the archive header records its creation time; that is why it is not a pin), and `scratch_dsn` `dbname=govbudget_proof_fu_pre host=localhost` / `dbname=govbudget_proof_fu_post host=localhost`. On `snapshot-pins: DIFFERENT` the lake moved between the copies (the lines above the verdict name what): discard both with Step 7's discard block and retake them.

From here on, never write `.proofs/fu-pre`, and write its database only in Task 21f Steps 4–5 (the `--apply`/`--revert` rehearsal, run after both fu-pre exports; README decision 2), which must leave every Postgres pin as Task 21e Step 1 took it: fu-pre is the pre-write reference and the clone source of Task 21f's A and B exports.
