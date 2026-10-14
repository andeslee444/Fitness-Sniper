<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13); brought to README decisions 1 and 2 at the 2026-10-13 plan review (O-1). -->

### Task 21e: Release-1 proof — the Chem Demil write, export-facts and the selective dbt build on fu-post

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §7 "Snapshots" (the lake writes are rehearsed on fu-post itself — its views read its own parquet, while clones' views read the parent: 1. `s194_chem_demil.py --apply` against the scratch database, keeping its pre-image file with the proof, 2. `jbooks export-facts`, 3. the B7 ratify on the committed seed, 4. the single selective dbt build; the revert is rehearsed on fu-pre, after its exports, in Task 21f Steps 4–5), §4.4 (the write and what it must leave), §4.5 (B7 and the map), §5.1 (`decided_on`), §6.2 "Build order", §2.3 Q24 (b), W2.

**Files:**
- No tracked file changes. Writes only the snapshot `.proofs/fu-post` (its `parquet/jbooks/*.parquet` and `duckdb/govbudget.duckdb`), its scratch database `govbudget_proof_fu_post`, logs under `.proofs/fu-logs/` (among them the revert file `s194-fu-post-revert.json`, kept), and the worktree's ignored `dbt/target/`. Reads `govbudget_proof_fu_pre` for Step 1's pins only; Task 21f Steps 4–5 are the only steps that write it.

**Interfaces:**
Consumes:
- Task 7's `scripts/era/s194_chem_demil.py` (README decision 1): exactly one of `--check`, `--dry-run`, `--apply`, `--revert`; `--apply` and `--revert` require `--revert-file PATH` (`--apply` refuses an existing file); `--dsn DSN` (default `GOVBUDGET_PG_DSN`); exit 0 / 1 (a difference, a refusal, a rollback) / 2 (usage). Lines matched here: `check: CLEAN, the only differences are #194's (re-key 8, insert 4, delete 8)`; `apply: re-keyed 8, deleted 8, inserted 4; untouched rows <n> (digest equal); route-unsafe pe_bli left 0`; `apply: dry run, every check passed: ROLLED BACK`; `apply: COMMITTED (revert file <path>)`.
- Task 6's seed `p1_route_safe_codes` and its test `assert_route_safe_codes_valid`; Task 7's `assert_budget_lines_route_safe_pe_bli`; Task 8's `p1_era_line_map.program_key` from the seed; Task 9a's `decided_on` as column 14 of 18; Task 10's B7 seed row; Task 4b's build order: one invocation that holds the seeds, the map and the program table (README decision 3).
- Task 21a's `scripts/fu/snapshot_pins.py pg|pg-compare`; Task 21d's `.proofs/fu-pre`, `.proofs/fu-post`.
Produces: `.proofs/fu-post` in the post-write state the release must reach (Postgres, `parquet/jbooks/`, the rebuilt DuckDB marts), which Task 21f clones for B@fu-post and B2@fu-post and Task 22b's `lake_parity.py` compares the live lake with; the revert file `$L/s194-fu-post-revert.json`, whose `before` rows Task 21f Step 4 and Task 22b Step 3 compare with theirs; `$L/pg-pins-pre-scratch.json`, fu-pre's scratch database pinned before any write, which Task 21f Step 5's revert must reproduce; logs `pg-pins-*.json`, `s194-post-*.log`, `rehearsal-0390d-apply.txt`, `export-facts-fu-post.log`, `dbt-build-fu-post.log`, `dbt-order-fu-post.txt`, `postbuild-fu-post.txt`.

Measured for this task (2026-10-13, read-only, live Postgres and lake; fu-post starts as their copy): the 0390D P-1 rows from PB2024 on are `2024 | O&M | O&M | 5 | 325095`, `2024 | RDT&E | RDT&E | 5 | 3979637`, `2025 | FY2024CR | FY2024CR | 1 | -32026`, `2025 | O&M | O&M | 3 | 194641`, `2025 | RDT&E | RDT&E | 3 | 2732528`; the O&M ids are 47733–47735 (PB2025) and 349016–349020 (PB2024); PB2026's P-1 row 303 is 87,404 / 20,745 / 3,243 / 3,243 (FY2024 actuals, FY2025 enacted, FY2026 discretionary request, FY2026 total; design §4.1), so the PB2026 insert sums to 114,635 and the table goes from 159,903 rows to 159,899 (−8 RDT&E, +4 O&M); account 0390D holds 354 `budget_lines` rows in all (217 P-1, 137 R-1), 350 after the write; `budget_lines_id_seq` reads `last_value` 581,318 (`max(id)` 581,201), so a dry run (which spends four sequence values and rolls back) followed by the apply gives the four PB2026 rows ids 581,323–581,326 on a copy restored from that state. The lake's `parquet/jbooks/budget_lines.parquet` has no `id` column (`export_facts.py` selects `exhibit … line_item_code` ordered by id), so the inserted rows' ids never reach the lake. `stg_budget_lines+` is 19 models (`stg_budget_lines` and its 18 descendants: 15 views and 4 tables, `fct_book_diff`, `fct_decade_series`, `fct_program_decade_series`, `p1_era_line_map`; counted from the manifest's `child_map`) and 135 tests in today's manifest; `p1_era_line_map`'s parents are `stg_budget_lines`, `p1_era_code_decisions` and the `jbook_budget_lines`/`jbook_documents` sources, `fct_program_decade_series`'s are the map, `stg_budget_lines` and `jbook_documents`, and `assert_program_decade_conservation` reads `fct_decade_series`, `fct_program_decade_series` and the map. Seeds are not descendants of `stg_budget_lines`, so the selection names them explicitly. dbt's sources read `{{ env_var('GOVBUDGET_DATA') }}/parquet/...`, so a build under `source .proofs/fu-post/env.sh` rebuilds fu-post's views on fu-post's own parquet.

Every block derives `P`, `L`, and the two scratch DSNs from the snapshots' own `env.sh` (`dbname=govbudget_proof_fu_pre host=localhost`, `dbname=govbudget_proof_fu_post host=localhost`). Nothing here reads or writes the live lake, so no block needs the SAM guard.

- [ ] **Step 1: Pin both scratch databases before any write**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
PRE_DSN=$(. "$P/fu-pre/env.sh" && echo "$GOVBUDGET_PG_DSN") && POST_DSN=$(. "$P/fu-post/env.sh" && echo "$GOVBUDGET_PG_DSN") && echo "pre: $PRE_DSN | post: $POST_DSN"
uv run --project . python scripts/fu/snapshot_pins.py pg --dsn "$PRE_DSN" --out "$L/pg-pins-pre-scratch.json"
uv run --project . python scripts/fu/snapshot_pins.py pg --dsn "$POST_DSN" --out "$L/pg-pins-post-0.json"
uv run --project . python scripts/fu/snapshot_pins.py pg-compare "$L/pg-pins-pre-scratch.json" "$L/pg-pins-post-0.json" --changed jbook_documents
```
Expected: `pre: dbname=govbudget_proof_fu_pre host=localhost | post: dbname=govbudget_proof_fu_post host=localhost`; two `pg-pins: 18 tables, <rows> rows -> …` lines with the same `<rows>`; then one `jbook_documents: differs: …` line and `pg-pins: PASS (expected to differ: jbook_documents)` — each scratch database points `jbook_documents.file_path` at its own `raw_docs` clone, and every other table is equal. `pg-pins-pre-scratch.json` is fu-pre's pin after that rewrite and before any write: the reference Task 21f Step 5's `--revert` must reproduce (`snapshot.json`'s `pg.tables` predates the rewrite, so it differs on `jbook_documents` and cannot serve).

- [ ] **Step 2: `--check` and a dry run on fu-post**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && POST_DSN=$(. "$P/fu-post/env.sh" && echo "$GOVBUDGET_PG_DSN")
uv run --project . python scripts/era/s194_chem_demil.py --check --dsn "$POST_DSN" > "$L/s194-post-check.log" 2>&1; echo "check exit=$?"; tail -1 "$L/s194-post-check.log"
uv run --project . python scripts/era/s194_chem_demil.py --dry-run --dsn "$POST_DSN" > "$L/s194-post-dryrun.log" 2>&1; echo "dry-run exit=$?"; tail -2 "$L/s194-post-dryrun.log"
uv run --project . python scripts/fu/snapshot_pins.py pg --dsn "$POST_DSN" --out "$L/pg-pins-post-dryrun.json" && uv run --project . python scripts/fu/snapshot_pins.py pg-compare "$L/pg-pins-post-0.json" "$L/pg-pins-post-dryrun.json"
```
Expected: `check exit=0`, `check: CLEAN, the only differences are #194's (re-key 8, insert 4, delete 8)`; `dry-run exit=0`, `apply: re-keyed 8, deleted 8, inserted 4; untouched rows 159887 (digest equal); route-unsafe pe_bli left 0` and `apply: dry run, every check passed: ROLLED BACK`; `pg-pins: EQUAL` (the dry run left nothing but four spent sequence values, which no pin reads). The dry run is part of the rehearsed sequence: Task 21f Step 4 on fu-pre and Task 22b Step 1 on live each run one before their `--apply`, so the three inserts draw the same ids.

- [ ] **Step 3: Apply on fu-post (scratch Postgres write), keeping the revert file**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && POST_DSN=$(. "$P/fu-post/env.sh" && echo "$GOVBUDGET_PG_DSN")
[ ! -e "$L/s194-fu-post-revert.json" ] || { echo "STOP: $L/s194-fu-post-revert.json exists (an earlier apply on fu-post): retake the snapshots (Task 21d Step 7)"; exit 1; }
uv run --project . python scripts/era/s194_chem_demil.py --apply --revert-file "$L/s194-fu-post-revert.json" --dsn "$POST_DSN" > "$L/s194-post-apply.log" 2>&1; echo "apply exit=$?"; tail -2 "$L/s194-post-apply.log"
uv run --project . python scripts/fu/snapshot_pins.py pg --dsn "$POST_DSN" --out "$L/pg-pins-post-1.json"
uv run --project . python scripts/fu/snapshot_pins.py pg-compare "$L/pg-pins-post-0.json" "$L/pg-pins-post-1.json" --changed budget_lines
"$GOVBUDGET_PG_BIN/psql" "$POST_DSN" -At -F' | ' -c "select count(*) from budget_lines;" -c "select count(*) from budget_lines where pe_bli ~ '[&#/?%[:space:]]';" -c "select fiscal_year, pe_bli, line_item_code, count(*), sum(amount_thousands) from budget_lines where account = '0390D' and exhibit = 'P-1' and fiscal_year >= 2024 group by 1, 2, 3 order by 1, 2, 3;" -c "select string_agg(id::text, ',' order by id) from budget_lines where pe_bli = '0390DOM' and fiscal_year in (2024, 2025);" -c "select fiscal_year, amount_type, amount_thousands from budget_lines where pe_bli = '0390DOM' and fiscal_year = 2026 order by amount_type;" -c "select string_agg(id::text, ',' order by id) from budget_lines where pe_bli = '0390DOM' and fiscal_year = 2026;" | tee "$L/rehearsal-0390d-apply.txt"
uv run --project . python -c "import json,sys; r=json.load(open(sys.argv[1])); print('revert file:', r['database'], len(r['before']), 'before rows,', len(r['rekeyed']), 're-keyed,', len(r['deleted_ids']), 'deleted,', len(r['inserted']), 'inserted')" "$L/s194-fu-post-revert.json"
```
Expected: `apply exit=0`, the `apply: re-keyed 8, deleted 8, inserted 4; …` line and `apply: COMMITTED (revert file /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs/s194-fu-post-revert.json)`; one `pg-pins:` line; `budget_lines: differs: rows 159903 -> 159899, …` and `pg-pins: PASS (expected to differ: budget_lines)`; then
```
159899
0
2024 | 0390DOM | O&M | 5 | 325095
2025 | 0390DOM | O&M | 3 | 194641
2025 | FY2024CR | FY2024CR | 1 | -32026
2026 | 0390DOM | O&M | 4 | 114635
47733,47734,47735,349016,349017,349018,349019,349020
2026 | fy_2024_actuals | 87404
2026 | fy_2025_enacted | 20745
2026 | fy_2026_disc_request | 3243
2026 | fy_2026_total | 3243
<id1>,<id2>,<id3>,<id4>
revert file: govbudget_proof_fu_post 16 before rows, 8 re-keyed, 8 deleted, 4 inserted
```
(the O&M rows keep their ids, the RDT&E rows are gone under Q1 (a), PB2026 gains the P-1's own four O&M figures, and no route-unsafe `pe_bli` is left; the four PB2026 ids are consecutive, 581323,581324,581325,581326 if fu-post's sequence was restored at 581,318 as measured). Any other result: stop and take it to Task 7's owner; the release must not repeat it. This is fu-post's only `--apply`: the revert is rehearsed on fu-pre (Task 21f Steps 4–5), so fu-post keeps the state the release must reach.

- [ ] **Step 4: `jbooks export-facts` on fu-post (writes fu-post's own parquet)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
(. "$P/fu-post/env.sh" && echo "GOVBUDGET_DATA=$GOVBUDGET_DATA" && uv run --project . python -m govbudget jbooks export-facts) > "$L/export-facts-fu-post.log" 2>&1; echo "export-facts exit=$?"; head -1 "$L/export-facts-fu-post.log"
uv run --project . python -c "import duckdb,sys; c=duckdb.connect(); p=sys.argv[1]; print(c.execute(f\"select count(*) from read_parquet('{p}')\").fetchone()[0], c.execute(f\"select pe_bli, line_item_code, fiscal_year, count(*) from read_parquet('{p}') where account = '0390D' and exhibit = 'P-1' and fiscal_year >= 2024 group by all order by all\").fetchall())" "$P/fu-post/parquet/jbooks/budget_lines.parquet"
```
Expected: `export-facts exit=0`, `GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-post`; then `159899 [('0390DOM', 'O&M', 2024, 5), ('0390DOM', 'O&M', 2025, 3), ('0390DOM', 'O&M', 2026, 4), ('FY2024CR', 'FY2024CR', 2025, 1)]`.

- [ ] **Step 5: The single selective dbt build on fu-post (map, then program table, then the tests that read both)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
(. "$P/fu-post/env.sh" && uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select p1_route_safe_codes p1_era_code_decisions stg_budget_lines+) > "$L/dbt-build-fu-post.log" 2>&1; echo "dbt build exit=$?"; grep -E "assert_budget_lines_route_safe_pe_bli|assert_route_safe_codes_valid|not_null_p1_era_line_map_decided_on|assert_program_decade_conservation|assert_p1_era_map_no_undecided" "$L/dbt-build-fu-post.log"; tail -1 "$L/dbt-build-fu-post.log"
uv run --project . python - dbt/target/run_results.json <<'PY' | tee "$L/dbt-order-fu-post.txt"
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
Expected: `dbt build exit=0`; the grep shows `PASS` (or `OK created …` for the seed) for each named test; last line `Done. PASS=<n> WARN=<w> ERROR=0 SKIP=0 …` (`<w>` only from `warn_*` tests); then `map built before the program table started: True`, `conservation ran after the program table: True`, and statuses `success`/`success`/`pass`. This is the build order Task 4 wrote into ratify's message, in one invocation: map, then program table, then the map's cross-table tests (#198's "map, then program table, then map"). If, and only if, the build fails on `assert_program_decade_conservation` alone with the conservation test started before the program table finished, finish the clean order with two more builds and record it for Task 22b:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
(. "$P/fu-post/env.sh" && uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select fct_program_decade_series && uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select p1_era_line_map) > "$L/dbt-build-fu-post-order.log" 2>&1; echo "exit=$?"; grep -E "^.*Done\. PASS" "$L/dbt-build-fu-post-order.log"
```
Expected: `exit=0` and two `Done. PASS=… ERROR=0 …` lines. Any other dbt failure: stop and report (W2 failed on the rehearsed state).

- [ ] **Step 6: The rebuilt fu-post warehouse**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
uv run --project . python - "$P/fu-post/duckdb/govbudget.duckdb" "$GOVBUDGET_DATA/" <<'PY' | tee "$L/postbuild-fu-post.txt"
import duckdb, sys
con = duckdb.connect(sys.argv[1], read_only=True)
cols = [r[0] for r in con.execute("describe p1_era_line_map").fetchall()]
print("map columns:", len(cols), "| decided_on at", cols.index("decided_on") + 1, "| after", cols[cols.index("decided_on") - 1])
for row in con.execute("select decision, ruling, program_key, cast(decided_on as varchar), count(*) from p1_era_line_map"
                       " where account = '0390D' group by all order by all").fetchall():
    print("0390D map:", row)
print("map rows by decided_on:", con.execute("select cast(decided_on as varchar), count(*) from p1_era_line_map group by 1 order by 1").fetchall())
print("route-safe seed:", con.execute("select * from p1_route_safe_codes").fetchall())
print("stg 0390DOM rows:", con.execute("select fiscal_year, count(*) from stg_budget_lines where pe_bli = '0390DOM' group by 1 order by 1").fetchall())
print("decade series 0390DOM rows:", con.execute("select count(*) from fct_program_decade_series where program_key = '0390DOM'").fetchone()[0])
print("views reading the live lake:", con.execute("select count(*) from duckdb_views() where not internal and contains(sql, ?)", [sys.argv[2]]).fetchone()[0])
PY
(. "$P/fu-post/env.sh" && uv run --project . python -m govbudget era-map check --strict) > "$L/era-check-fu-post.log" 2>&1; echo "era-map check exit=$?"; tail -1 "$L/era-check-fu-post.log"
```
Expected: `map columns: 18 | decided_on at 14 | after ruling`; the 0390D map rows `('exclude_placeholder', 'R-DEC-ERA-EXCLUDE', None, '2026-10-02', 2)`, `('exclude_route_unsafe', 'R-DEC-ERA-EXCLUDE', None, '2026-10-02', 7)` (the RDT&E chain keeps its exclusion, Q4), `('history_only', 'R-DEC-ERA-HISTORY', 'PROC', '2026-10-02', 7)` and `('same_program', 'R-DEC-ERA-B7', '0390DOM', '2026-10-04', 7)` (B7's `decided_on` is the day the owner answered, README decision 6); `map rows by decided_on: [('2026-10-02', 6205), ('2026-10-03', 701), ('2026-10-04', 21)]` (design §5.1 measured 6,212 / 701 / 14; the 7 O&M keys move from 2026-10-02 to B7's 2026-10-04, beside B6's 14; 6,927 in all); `route-safe seed` the one `0390D`/`O&M`/`0390DOM` row; `stg 0390DOM rows: [(2024, 5), (2025, 3), (2026, 4)]`; a positive decade-series count; `views reading the live lake: 0`; `era-map check exit=0` and `era-map check: 0 undecided chain(s), 0 stale decision(s)`.

From here on, fu-post is the rehearsed post-write state: do not write it again. Its `snapshot.json` still describes the copy as taken (the pins Task 21d compared), not this state.
