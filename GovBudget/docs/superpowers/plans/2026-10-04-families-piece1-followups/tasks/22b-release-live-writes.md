<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13); brought to README decisions 1–3 and spec §8's abort path at the 2026-10-13 plan review (O-1). -->

### Task 22b: Release 1 — the live writes (Chem Demil, export-facts, the selective dbt build), live = fu-post, and the abort path

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §8 step 2 (in this order, each outside :12–:22: `s194_chem_demil.py --apply` on live Postgres, `jbooks export-facts`, the single selective dbt build; then live equals fu-post, §4.4: "the 0390D rows in the live Postgres must equal fu-post's, and the rebuilt marts must equal fu-post's (`EXCEPT` both ways)"; the post-write state is checked with `lake_parity.py` against fu-post and `era-map check --strict`), §8 step 2's pre-image ("The live `--apply` writes its pre-image to `.proofs/fu-release-s194-pre-image.json`; its rows must equal those of the pre-image the rehearsals wrote, and it is the abort path's input"), §8's abort path (steps 1–4; after the deploy, the owner decides first, then LAUNCH.md's rollback and steps 1–4), §2.3 Q24 (b) (the abort path uses `--revert`), §6.2 "Build order".

**Files:**
- No tracked file changes. **Shared-state writes (this wave's only ones besides Task 22c's export and the abort path's restore):** live Postgres `budget_lines` (Step 3), the live lake `data/parquet/jbooks/*.parquet` (Step 4) and `data/duckdb/govbudget.duckdb` (Step 5). The abort path, only if it runs: the same three, back to their pre-write content (A1, A2), and `data/site` (A3). Local only: the live pre-image `.proofs/fu-release-s194-pre-image.json` (Step 3; kept: it is A1's input), logs under `.proofs/fu-logs/`; the worktree's ignored `dbt/target/` and the A worktree's (A2).

**Interfaces:**
Consumes: Task 7's `s194_chem_demil.py` (README decision 1: exactly one of `--check`, `--dry-run`, `--apply --revert-file F`, `--revert --revert-file F`; default DSN `GOVBUDGET_PG_DSN`, the live database; `--apply` refuses an existing file; `--revert` checks the file's `rows_sha256` and that it was written on this database); Task 21a's `snapshot_pins.py` and `lake_parity.py`, and its `$L/parity-smoke.txt` (the live lake's pre-write row counts, Step 6); Task 21e's rehearsed `.proofs/fu-post`, its build order and its revert file `$L/s194-fu-post-revert.json`; Task 21f's `$L/s194-fu-pre-revert.json` and its rehearsals of A1 (Step 5) and A2 (Step 6, with its `PASS=<n>`); Task 22a's `live-pg-pins-pre.json` and `.proofs/fu-release-pre-site`; Task 21d's `.proofs/fu-pre` (the lake A2's parity compares with; its database is pre-write again after Task 21f Step 5) and the A worktree (`/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a`, the deployed code, for the abort rebuild).
Produces: the live Postgres and lake in fu-post's state; the live pre-image `.proofs/fu-release-s194-pre-image.json`; logs `s194-live-*.log`, `live-pg-pins-dryrun.json`, `live-pg-pins-post*.json`, `live-0390d-after.txt`, `export-facts-live.log`, `dbt-build-live.log`, `dbt-order-live.txt`, `parity-live-fu-post.txt`, `era-check-live.log`, `live-counts-pre-post.txt`.

Every block that touches the live lake or Postgres starts with the SAM guard; on `WAIT`, wait until :23 and re-run that block. Steps 3–5 are writes: run each once, in order, and read its result before the next. No other session may hold the DuckDB file during Step 5 (dbt needs its write lock; a holder makes dbt fail before writing).

**Hazard from Step 3 until Task 22e publishes (design §2.3 Q24):** the main checkout still runs the deployed code. Its `export-site` raises on the B7 map row (`line_item_code` O&M differs from `program_key` 0390DOM, `export_site.py:7355-7362` at 916ae88e) and its `govbudget build` or `jbooks export-facts` would rebuild the map without `decided_on`/B7 or re-stage the parquet. Run nothing from the main checkout in that window, and ask the owner not to. The hourly SAM job only reads the lake.

- [ ] **Step 1: `--check` against the live database (read-only)**

`--check` only reads. The `--dry-run` takes the table lock and spends four id-sequence values, so it waits for the owner's go-ahead (Step 3's first block):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs" && echo "DSN $GOVBUDGET_PG_DSN"
uv run --project . python scripts/era/s194_chem_demil.py --check > "$L/s194-live-check.log" 2>&1; echo "check exit=$?"; tail -1 "$L/s194-live-check.log"
```
Expected: `DSN postgresql://localhost/govbudget`; `check exit=0`, `check: CLEAN, the only differences are #194's (re-key 8, insert 4, delete 8)`. Anything else: stop (nothing is written).

- [ ] **Step 2: Owner go-ahead for the live writes**

Tell the owner: "The follow-ups release-1 proof passed (docs/superpowers/reviews/fu-release1-proof.md) and the live database is in the state the proof started from. The read-only --check found exactly #194's differences. On your yes, I first run a dry run on the live database: it takes the write's table lock, runs every check, rolls back, and leaves one trace, four spent id-sequence values (the rehearsals spent them too, so the write draws the ids they drew). Then I write the live Postgres (re-key the 8 Chem Demil O&M rows to 0390DOM, delete the 8 RDT&E rows, insert PB2026's 4 O&M rows), re-stage the jbooks parquet and rebuild the era map and program table. Until the release is published, please run nothing from the main checkout. The write keeps a pre-image (.proofs/fu-release-s194-pre-image.json). If anything fails before the deploy, I restore the database from it with the rehearsed --revert, rebuild the lake with the deployed code and drop the one table the new build adds (p1_route_safe_codes), as the design's abort path says; after the deploy, rolling back is your call. Go ahead?" Wait for an explicit yes. Nothing in this task has touched the live database before that yes except Step 1's read-only `--check`.

- [ ] **Step 3: The Chem Demil write on live Postgres (SHARED POSTGRES WRITE)**

First, right after the owner's yes, the dry run and its pin comparison (it rolls back; its only trace is four spent id-sequence values, as Task 21e Step 2 spent on fu-post and Task 21f Step 4 on fu-pre, so the `--apply` below draws the ids the rehearsals drew):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && F="$P/fu-release-s194-pre-image.json"
[ ! -e "$F" ] || { echo "STOP: $F exists: an earlier live --apply wrote it; read it and the live 0390D rows before anything else"; exit 1; }
uv run --project . python scripts/era/s194_chem_demil.py --dry-run > "$L/s194-live-dryrun.log" 2>&1; echo "dry-run exit=$?"; tail -2 "$L/s194-live-dryrun.log"
uv run --project . python scripts/fu/snapshot_pins.py pg --dsn "$GOVBUDGET_PG_DSN" --out "$L/live-pg-pins-dryrun.json" && uv run --project . python scripts/fu/snapshot_pins.py pg-compare "$L/live-pg-pins-pre.json" "$L/live-pg-pins-dryrun.json"
```
Expected: `dry-run exit=0`, `apply: re-keyed 8, deleted 8, inserted 4; untouched rows 159887 (digest equal); route-unsafe pe_bli left 0` and `apply: dry run, every check passed: ROLLED BACK`; `pg-pins: EQUAL`. Anything else: stop and report to the owner (nothing is written; the dry run rolled back). Run the dry run once: a second one spends four more sequence values, and the PB2026 ids then differ from the rehearsals' (reported, not a failure; README decision 2).

Then the write:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && F="$P/fu-release-s194-pre-image.json"
[ ! -e "$F" ] || { echo "STOP: $F exists: an earlier live --apply wrote it; read it and the live 0390D rows before anything else"; exit 1; }
uv run --project . python scripts/era/s194_chem_demil.py --apply --revert-file "$F" > "$L/s194-live-apply.log" 2>&1; echo "apply exit=$?"; tail -2 "$L/s194-live-apply.log"
uv run --project . python scripts/fu/snapshot_pins.py pg --dsn "$GOVBUDGET_PG_DSN" --out "$L/live-pg-pins-post.json" && uv run --project . python scripts/fu/snapshot_pins.py pg-compare "$L/live-pg-pins-pre.json" "$L/live-pg-pins-post.json" --changed budget_lines
"$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_PG_DSN" -At -F' | ' -c "select count(*) from budget_lines;" -c "select count(*) from budget_lines where pe_bli ~ '[&#/?%[:space:]]';" -c "select fiscal_year, pe_bli, line_item_code, count(*), sum(amount_thousands) from budget_lines where account = '0390D' and exhibit = 'P-1' and fiscal_year >= 2024 group by 1, 2, 3 order by 1, 2, 3;" -c "select string_agg(id::text, ',' order by id) from budget_lines where pe_bli = '0390DOM' and fiscal_year in (2024, 2025);" -c "select string_agg(id::text, ',' order by id) from budget_lines where pe_bli = '0390DOM' and fiscal_year = 2026;" | tee "$L/live-0390d-after.txt"
uv run --project . python -c "import json,sys; f,post,pre=(json.load(open(x)) for x in sys.argv[1:]); print('live pre-image:', f['database'], len(f['before']), 'before rows | before = fu-post rehearsal:', f['before'] == post['before'], '| before = fu-pre rehearsal:', f['before'] == pre['before'], '| inserted = fu-post:', f['inserted'] == post['inserted'])" "$F" "$L/s194-fu-post-revert.json" "$L/s194-fu-pre-revert.json"
```
Expected: `apply exit=0`, the `apply: re-keyed 8, deleted 8, inserted 4; untouched rows 159887 (digest equal); route-unsafe pe_bli left 0` line and `apply: COMMITTED (revert file /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-release-s194-pre-image.json)`; `budget_lines: differs: rows 159903 -> 159899, …` and `pg-pins: PASS (expected to differ: budget_lines)`; then exactly Task 21e Step 3's result: `159899`, `0`, `2024 | 0390DOM | O&M | 5 | 325095`, `2025 | 0390DOM | O&M | 3 | 194641`, `2025 | FY2024CR | FY2024CR | 1 | -32026`, `2026 | 0390DOM | O&M | 4 | 114635`, `47733,47734,47735,349016,349017,349018,349019,349020`, and the four PB2026 ids Task 21e Step 3 printed; last, `live pre-image: govbudget 16 before rows | before = fu-post rehearsal: True | before = fu-pre rehearsal: True | inserted = fu-post: True` (spec §8 step 2: the live pre-image's rows equal the rehearsals'). If the apply printed `ROLLED BACK`, nothing was written and no file exists: stop and read its log. If it committed but either `before` check is `False`, or any other check here differs, take the abort path (A1 restores exactly the rows this file recorded). `inserted = fu-post: False` with both `before` checks `True` and the PB2026 ids alone different means another transaction spent live sequence values after Task 22a: report it to the owner; it is not a failure (README decision 2).

- [ ] **Step 4: `jbooks export-facts` on the live lake (SHARED LAKE WRITE)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs" && echo "GOVBUDGET_DATA=$GOVBUDGET_DATA"
uv run --project . python -m govbudget jbooks export-facts > "$L/export-facts-live.log" 2>&1; echo "export-facts exit=$?"
uv run --project . python -c "import duckdb,sys; c=duckdb.connect(); p=sys.argv[1]; print(c.execute(f\"select count(*) from read_parquet('{p}')\").fetchone()[0], c.execute(f\"select pe_bli, line_item_code, cast(fiscal_year as integer), count(*) from read_parquet('{p}') where account = '0390D' and exhibit = 'P-1' and cast(fiscal_year as integer) >= 2024 group by all order by all\").fetchall())" "$GOVBUDGET_DATA/parquet/jbooks/budget_lines.parquet"
```
Expected: `GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data`, `export-facts exit=0`, then `159899 [('0390DOM', 'O&M', 2024, 5), ('0390DOM', 'O&M', 2025, 3), ('0390DOM', 'O&M', 2026, 4), ('FY2024CR', 'FY2024CR', 2025, 1)]` — Task 21e Step 4's line, from the same query (`fiscal_year` is VARCHAR in this parquet, so the query casts it in the select and the `where`). A failure: take the abort path.

- [ ] **Step 5: The single selective dbt build on the live lake (SHARED LAKE WRITE)**

The same invocation Task 21e Step 5 rehearsed (map, then program table, then the tests that read both):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs" && echo "GOVBUDGET_DUCKDB=$GOVBUDGET_DUCKDB"
uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select p1_route_safe_codes p1_era_code_decisions stg_budget_lines+ > "$L/dbt-build-live.log" 2>&1; echo "dbt build exit=$?"; grep -E 'Done\. PASS' "$L/dbt-build-live.log"
uv run --project . python - dbt/target/run_results.json <<'PY' | tee "$L/dbt-order-live.txt"
import json, sys
results = {r["unique_id"].split(".")[-1] if r["unique_id"].startswith("model.") else r["unique_id"].split(".")[2]: r
           for r in json.load(open(sys.argv[1]))["results"]}
def span(name):
    t = {x["name"]: x for x in results[name]["timing"]}["execute"]
    return t["started_at"], t["completed_at"]
m, p, c = span("p1_era_line_map"), span("fct_program_decade_series"), span("assert_program_decade_conservation")
print("map built before the program table started:", m[1] <= p[0])
print("conservation ran after the program table:", p[1] <= c[0])
print("statuses:", {k: results[k]["status"] for k in ("p1_era_line_map", "fct_program_decade_series", "assert_program_decade_conservation")})
PY
```
Expected: `GOVBUDGET_DUCKDB=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb`; `dbt build exit=0`; the grep's dbt Done line, `Done. PASS=<n> WARN=<w> ERROR=0 SKIP=0 …`, with the same `<n>` as Task 21e Step 5 (the grep, not `tail -1`: dbt prints its deprecation summary after the Done line); the two order lines `True` and statuses `success`/`success`/`pass`. The order check reads `dbt/target/run_results.json` in this block, right after this block's own dbt build, with no pytest run in between: a pytest run (`test_dbt_build`) rewrites the worktree's `dbt/target/` (Task 21d), and the check would then read another build's results. If Task 21e needed the two extra builds of its Step 5, run them now the same way (`--select fct_program_decade_series`, then `--select p1_era_line_map`, each with this block's guard). A dbt failure that is not that case: take the abort path (a lock error means another session holds the DuckDB file: wait for it, then re-run this step; nothing was written).

- [ ] **Step 6: The live lake equals fu-post**

Read-only on both lakes. This step's comparison, like A2's below, compares the lakes' content with `lake_parity.py`, never their files' sha256s: `jbooks export-facts` rewrites `budget_line_awards`, `detail_narratives`, `details` and `documents` with identical rows but different bytes (Task 21e's Step 4 run found it on fu-post, 2026-10-14), so a sha comparison would report differences that are not there.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && POST_DSN=$(. "$P/fu-post/env.sh" && echo "$GOVBUDGET_PG_DSN")
rm -rf "${L:?}/parity-live-fu-post"
uv run --project . python scripts/fu/lake_parity.py --a "$GOVBUDGET_DATA" --b "$P/fu-post" --relation stg_budget_lines --relation fct_budget_lines --relation fct_decade_series --relation fct_book_diff --relation p1_route_safe_codes --relation p1_era_code_decisions --relation p1_era_line_map --relation fct_program_decade_series --relation fct_budget_trajectory --parquet jbooks/budget_lines.parquet --pg-a "$GOVBUDGET_PG_DSN" --pg-b "$POST_DSN" --pg-where "account = '0390D'" --work "$L/parity-live-fu-post" --report "$L/parity-live-fu-post.json" > "$L/parity-live-fu-post.txt" 2>&1; echo "exit=$?"; cat "$L/parity-live-fu-post.txt"
uv run --project . python -m govbudget era-map check --strict > "$L/era-check-live.log" 2>&1; echo "era-map check exit=$?"; tail -1 "$L/era-check-live.log"
uv run --project . python - "$L/parity-smoke.txt" "$L/parity-live-fu-post.txt" <<'PY' | tee "$L/live-counts-pre-post.txt"
"""The live lake's row counts before the write (Task 21a Step 7's parity-smoke.txt,
column A) against after it (this step's parity, column A = live)."""
import re, sys
def counts(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"(?:relation|parquet) (\S+): A ([\d,]+) rows", line)
        if m:
            out[m.group(1)] = int(m.group(2).replace(",", ""))
    return out
pre, post = counts(sys.argv[1]), counts(sys.argv[2])
MOVE = {"stg_budget_lines": -4, "fct_budget_lines": -4, "jbooks/budget_lines.parquet": -4}
SAME = {"p1_era_code_decisions", "p1_era_line_map"}
bad = [name for name in sorted(set(MOVE) | SAME) if name not in pre]
for name in sorted(set(pre) | set(post)):
    if name not in post:
        bad.append(name)
        print(f"{name}: MISSING after the write")
        continue
    if name not in pre:
        print(f"{name}: new, {post[name]:,} row(s)")
        continue
    d = post[name] - pre[name]
    if name in MOVE:
        verdict = "ok" if d == MOVE[name] else f"FAIL (expected {MOVE[name]:+d})"
    elif name in SAME:
        verdict = "ok" if d == 0 else "FAIL (expected unchanged)"
    else:
        verdict = "reported (equal to fu-post above)"
    if verdict.startswith("FAIL"):
        bad.append(name)
    print(f"{name}: {pre[name]:,} -> {post[name]:,} ({d:+d}) {verdict}")
print("pre/post counts:", "FAIL" if bad else "PASS")
PY
```
Expected: `exit=0`; one `— equal` line per relation (`stg_budget_lines` and `fct_budget_lines` 159,899 rows; the others as Task 21e's rebuilt fu-post; `p1_era_line_map` 6,927), `parquet jbooks/budget_lines.parquet: A 159,899 rows, B 159,899 rows, … — equal`, `postgres budget_lines where account = '0390D': A 350 rows, B 350 rows, A not in B 0, B not in A 0, ids equal — equal` (fu-post and live each ran one `--dry-run` then one `--apply`, README decision 2; if Step 3 reported `inserted = fu-post: False`, this line reads `ids differ — equal` for the same four PB2026 ids: report it, it is not a failure), `lake-parity: EQUAL`; then `era-map check exit=0`, `era-map check: 0 undecided chain(s), 0 stale decision(s)`. `DIFFERENT`: the release did not reach the proven state; take the abort path. Last, the live counts against the pre-write ones Task 21a Step 7 kept in `$L/parity-smoke.txt`: `stg_budget_lines: 159,903 -> 159,899 (-4) ok`, the same for `fct_budget_lines` and `jbooks/budget_lines.parquet` (−8 RDT&E, +4 PB2026 O&M; Task 21e Step 3); `p1_era_code_decisions: 1,253 -> 1,253 (+0) ok` and `p1_era_line_map: 6,927 -> 6,927 (+0) ok` (B7 replaces one seed row and moves no map row); `p1_route_safe_codes: new, 1 row(s)`; `fct_program_decade_series`, `fct_decade_series`, `fct_book_diff` and `fct_budget_trajectory` each `<pre> -> <post> (<delta>) reported (equal to fu-post above)` — no task measured their post-write counts, and `fct_program_decade_series` moves by design (B7's 21 era grains under 0390DOM, decision 6), so they are recorded for the stamp, not asserted; their equality with fu-post is the parity above; last line `pre/post counts: PASS`. `FAIL` with `lake-parity: EQUAL` above means the live lake moved between Task 21a Step 7 and the proof's snapshots: stop and report to the owner before Task 22c.

The live writes are done. Task 22c exports.

**Abort path (SHARED-STATE RESTORE; authorised by design §2.3 Q24 (b) and §8's abort path).** Use it when any step from Step 3 on, or any check in Tasks 22c–22d before the deploy, fails and cannot be cleared, or the owner says no before the deploy. It returns the database and the lake to the pre-write state the deployed code expects, and `data/site` to production's export. Stop and report to the owner after it; never deploy from a state it left. Run the parts in order, each with the SAM guard. **After Task 22d Step 6's deploy** a failure is the owner's call first (spec §8): on the owner's yes, roll the site back by LAUNCH.md's rollback procedure — Vercel to the previous deployment, then R2 `data/` and `citations/` from the rollback tag Task 22d Step 6 recorded (`rclone copy --checksum r2:govbudget-assets/rollback/<tag>/data/ r2:govbudget-assets/data/`, the same for `citations/`, as `deploy.sh` printed them) — then run A1, A2 and A3 below, in order, each with its SAM guard. Until the owner answers, run nothing from the main checkout (the hazard above still holds).

A1 — the database, with the rehearsed `--revert` (Task 21f Step 5) and the live pre-image Step 3 wrote:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && F="$P/fu-release-s194-pre-image.json"
[ -f "$F" ] || { echo "SKIP A1: $F does not exist, so Step 3 never committed"; exit 0; }
uv run --project . python scripts/era/s194_chem_demil.py --revert --revert-file "$F" > "$L/s194-live-revert.log" 2>&1; echo "revert exit=$?"; tail -1 "$L/s194-live-revert.log"
uv run --project . python scripts/fu/snapshot_pins.py pg --dsn "$GOVBUDGET_PG_DSN" --out "$L/live-pg-pins-reverted.json" && uv run --project . python scripts/fu/snapshot_pins.py pg-compare "$L/live-pg-pins-pre.json" "$L/live-pg-pins-reverted.json"
```
Expected: `revert exit=0`, `revert: restored 16 pre-write row(s) (re-keyed 8 back, re-inserted 8, removed 4); COMMITTED`, `pg-pins: EQUAL` (every table as Task 22a pinned it, ids included). `SKIP A1: …`: go on with A2 only if Step 4 or 5 ran. `revert: the database moved since --apply (<n> problem(s)); nothing written` or `revert: … sha256 does not match its contents; nothing written` (exit 1): nothing was written; stop and report to the owner with the log — something changed the rows or the file after Step 3, and the revert must not be forced.

A2 — the lake, re-staged from the restored database and rebuilt by the deployed code (the A worktree's `jbooks export-facts` and dbt project; spec §8 abort step 2, rehearsed in Task 21f Step 6), then the one relation B's build created that A's project does not define, `p1_route_safe_codes`, dropped:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs" && echo "GOVBUDGET_DATA=$GOVBUDGET_DATA | GOVBUDGET_DUCKDB=$GOVBUDGET_DUCKDB | code $(git log -1 --format=%h)"
uv run --project . python -m govbudget jbooks export-facts > "$L/export-facts-live-revert.log" 2>&1; echo "export-facts (deployed code) exit=$?"
uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select p1_era_code_decisions stg_budget_lines+ > "$L/dbt-build-live-revert.log" 2>&1; echo "dbt build (deployed code) exit=$?"; grep -E 'Done\. PASS' "$L/dbt-build-live-revert.log"
uv run --project . python -c "import duckdb,os; c=duckdb.connect(os.environ['GOVBUDGET_DUCKDB']); c.execute('drop table if exists main.p1_route_safe_codes'); print('route-safe relation left:', c.execute(\"select count(*) from duckdb_tables() where table_name = 'p1_route_safe_codes'\").fetchone()[0]); c.close()"
```
Expected: `GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data | GOVBUDGET_DUCKDB=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb | code <A short sha>`; `export-facts (deployed code) exit=0`; `dbt build (deployed code) exit=0` and the grep's dbt Done line, `Done. PASS=<n> … ERROR=0 …`, with the `<n>` of Task 21f Step 6's rehearsal; `route-safe relation left: 0`. Then prove the lake is back:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && PRE_DSN=$(. "$P/fu-pre/env.sh" && echo "$GOVBUDGET_PG_DSN") && rm -rf "${L:?}/parity-live-fu-pre"
uv run --project . python scripts/fu/lake_parity.py --a "$GOVBUDGET_DATA" --b "$P/fu-pre" --relation stg_budget_lines --relation fct_budget_lines --relation fct_decade_series --relation fct_book_diff --relation p1_era_code_decisions --relation p1_era_line_map --relation fct_program_decade_series --relation fct_budget_trajectory --parquet jbooks/budget_lines.parquet --pg-a "$GOVBUDGET_PG_DSN" --pg-b "$PRE_DSN" --pg-where "account = '0390D'" --work "$L/parity-live-fu-pre" > "$L/parity-live-fu-pre.txt" 2>&1; echo "exit=$?"; tail -1 "$L/parity-live-fu-pre.txt"
```
Expected: `exit=0`, `lake-parity: EQUAL` (Postgres ids equal too: A1 restored every pre-write row with its own id and removed the four inserted ones).

A3 — `data/site`, only if Task 22c's export ran (piece-1 Task 23's abort path; nothing is deleted):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
mv data/site data/site.release-aborted-$(date -u +%Y%m%dT%H%M%SZ) && cp -cR .proofs/fu-release-pre-site data/site && shasum -a 256 data/site/manifest.json .proofs/fu-release-pre-site/manifest.json
```
Expected: the two hashes are equal. `data/site` stays a real directory at the same path, so the other worktrees' links still resolve. Remove `data/site.release-aborted-*` only on the owner's word.
