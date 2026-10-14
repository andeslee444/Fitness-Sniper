<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13); Steps 4–6 added at the 2026-10-13 plan review (README decision 2, O-1). -->

### Task 21f: Release-1 proof — the four exports, the write-and-revert rehearsal on fu-pre, the abort-path rehearsal, the control, P2 (code), P2b (/years/) and P1 (lake)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §7 "Exports" (A@fu-pre, B@fu-pre, B@fu-post and the control B2@fu-post; `proof diff B B2 --control --write-noise` must read EQUAL; the judged diffs use `--noise-from`; "The revert is rehearsed on `fu-pre`" after the A@fu-pre and B@fu-pre exports: `--apply`, rows equal to fu-post's ids included, `--revert`, every Postgres pin back, a second `--revert` reports nothing to revert), §8's abort path steps 2–3 (rehearsed here on a clone of fu-post), the cross-review re-pairing (P2 code = A@fu-pre vs B@fu-pre; P1 lake = B@fu-pre vs B@fu-post; B exports the pre-write warehouse), P1, P2 (`citations.json` identical), P2b, §1 success criteria, §4.6, §4.7, §5.7, §5.8.

**Files:**
- No tracked file changes. Local only: the clones `.proofs/{fu-pre-A,fu-pre-B,fu-post-B,fu-post-B2}`, the throwaway clone `.proofs/fu-abort` (Step 6 creates and removes it) and logs under `.proofs/fu-logs/`. Scratch Postgres: Steps 4–5 write `govbudget_proof_fu_pre` (one `--apply`, then its `--revert`) after both fu-pre exports have run, and leave every one of its pins as Task 21e Step 1 took them; Step 6 reads it.

**Interfaces:**
Consumes: Task 21d's `.proofs/fu-pre`, the A worktree and `$L/shas.txt`; Task 21e's rehearsed `.proofs/fu-post`, its revert file `$L/s194-fu-post-revert.json` and fu-pre's pre-write pins `$L/pg-pins-pre-scratch.json`; Task 7's `s194_chem_demil.py --dry-run | --apply --revert-file F | --revert --revert-file F | --check` (README decision 1); Task 21a's `snapshot_pins.py` and `lake_parity.py`; Task 21c's four rule files; Task 21b's `fact_delta.py` and `years_shard_proof.py`; Task 2's `govbudget proof diff A B [--control --write-noise FILE | --noise-from FILE] [--expect RULES] [--report FILE]` (last line `proof diff: EQUAL|DIFFERENT`, or `PASS|FAIL` with `--expect`; noise file schema 2, written only for an EQUAL control); the run-dir convention `cp -c -R <snap> <run>` + `. <snap>/env.sh <run>`.
Produces (kept for Tasks 21g–22e): `$L/export-times.txt` (each export's start and end, for Task 21i), `$L/s194-fu-pre-revert.json` (the fu-pre rehearsal's revert file; Task 22b Step 3 compares the live file's `before` rows with it), `parity-pg-pre-post.txt`, `pg-pins-pre-reverted.json`, `parity-abort-fu-pre.txt` (the abort path's lake half, rehearsed); the four exports' `site/` trees; `$L/noise-fu.json` (the control's reorder classes; Task 22c's release-state diff reads it); `$L/p2-diff.txt`, `p2-diff-report.json`, `p2-fact-delta.json`, `p2b-report.json`, `p1-diff.txt`, `p1-diff-report.json`, `p1-fact-delta.json` (its `citations.new_in_b` is WAVE_D, the wave's citation delta Task 22c reconciles), `p1-content.txt`.

Measured for this task (2026-10-13, read-only, the live export of 2026-10-04 that the snapshots copy as `site/`): 143,841 citations; `json/budget-pdf-receipts/` 256 v1 shards and `v2/` 4,096; `json/program_details/` 2,562 sidecars, none named `0390DOM`; piece 1's four exports ran 13–17 minutes each (piece-1 Task 23 timing note); the fact_delta and P2b expectations below are Task 21b's measurements, the P1 content values Task 21c's. Live Postgres (read-only): account 0390D holds 354 `budget_lines` rows (217 P-1, 137 R-1), 350 after #194's write; `budget_lines_id_seq` `last_value` 581,318.

- [ ] **Step 1: Clone the snapshots for the four exports**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"
for n in fu-pre-A fu-pre-B fu-post-B fu-post-B2; do if [ -e "$P/$n" ]; then echo "STOP: $P/$n exists"; exit 1; fi; done
cp -c -R "$P/fu-pre" "$P/fu-pre-A" && cp -c -R "$P/fu-pre" "$P/fu-pre-B" && cp -c -R "$P/fu-post" "$P/fu-post-B" && cp -c -R "$P/fu-post" "$P/fu-post-B2" || exit 1
for pair in fu-pre:fu-pre-A fu-pre:fu-pre-B fu-post:fu-post-B fu-post:fu-post-B2; do s=${pair%%:*}; r=${pair##*:}; (. "$P/$s/env.sh" "$P/$r" && echo "$r: $GOVBUDGET_DATA | $GOVBUDGET_PG_DSN"); done
```
Expected (seconds; APFS clones share blocks):
```
fu-pre-A: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-pre-A | dbname=govbudget_proof_fu_pre host=localhost
fu-pre-B: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-pre-B | dbname=govbudget_proof_fu_pre host=localhost
fu-post-B: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-post-B | dbname=govbudget_proof_fu_post host=localhost
fu-post-B2: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-post-B2 | dbname=govbudget_proof_fu_post host=localhost
```
The clones' DuckDB views read their parent's `parquet/` (`fu-pre` or `fu-post`); exports only read the scratch databases. Always pass the run dir to the snapshot's `env.sh`.

- [ ] **Step 2: Export A@fu-pre (the deployed code)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
echo "fu-pre-A start $(date +%Y-%m-%dT%H:%M:%S)" >> "$L/export-times.txt"
(. "$P/fu-pre/env.sh" "$P/fu-pre-A" && uv run --project . python -m govbudget export-site) > "$L/export-pre-A.log" 2>&1; rc=$?; echo "fu-pre-A end $(date +%Y-%m-%dT%H:%M:%S) exit=$rc" >> "$L/export-times.txt"; echo "exit=$rc"; tail -2 "$L/export-pre-A.log"
```
Expected: `exit=0`; `budget PDF receipts: <c>/<n> complete, … audit -> …/.proofs/fu-pre-A/site/json/budget_pdf_receipts_audit.json` and `export-site: <d> datasets, <N_pre> citations, … -> …/.proofs/fu-pre-A/site`. `<N_pre>` is 143,841 plus one per SAM.gov registration the hourly job stored after the 2026-10-04 export (the lake held 164 SAM entities on 2026-10-13 against 149 published; each published registration carries one derived citation).

- [ ] **Step 3: Export B@fu-pre (the follow-ups code on the pre-write warehouse)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
echo "fu-pre-B start $(date +%Y-%m-%dT%H:%M:%S)" >> "$L/export-times.txt"
(. "$P/fu-pre/env.sh" "$P/fu-pre-B" && uv run --project . python -m govbudget export-site) > "$L/export-pre-B.log" 2>&1; rc=$?; echo "fu-pre-B end $(date +%Y-%m-%dT%H:%M:%S) exit=$rc" >> "$L/export-times.txt"; echo "exit=$rc"; tail -2 "$L/export-pre-B.log"
```
Expected: `exit=0` and the same two lines for `fu-pre-B`, with the same `<N_pre>` (P2: no fact moves). B must export the pre-write warehouse — 17-column map, no `p1_route_safe_codes` table, the 16 route-unsafe rows still in the lake (design §7 re-pairing). If it raises instead, a task of this wave made the exporter depend on the write (G5 notes, contract issue 2): stop and report.

- [ ] **Step 4: Rehearse the write on fu-pre (scratch Postgres write; README decision 2)**

Both fu-pre exports have run (Steps 2–3), so writing fu-pre's database now disturbs no export. The sequence is the one fu-post (Task 21e Steps 2–3) and live (Task 22b Step 3, after the owner's go-ahead) run: one `--dry-run`, then one `--apply` with its revert file.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && PRE_DSN=$(. "$P/fu-pre/env.sh" && echo "$GOVBUDGET_PG_DSN") && POST_DSN=$(. "$P/fu-post/env.sh" && echo "$GOVBUDGET_PG_DSN")
for f in export-pre-A.log export-pre-B.log; do grep -q '^export-site: ' "$L/$f" || { echo "STOP: $L/$f has no export-site line: run Steps 2 and 3 first"; exit 1; }; done
[ ! -e "$L/s194-fu-pre-revert.json" ] || { echo "STOP: $L/s194-fu-pre-revert.json exists: an earlier rehearsal ran; read it, and Step 5's log, before going on"; exit 1; }
uv run --project . python scripts/era/s194_chem_demil.py --dry-run --dsn "$PRE_DSN" > "$L/s194-pre-dryrun.log" 2>&1; echo "dry-run exit=$?"; tail -1 "$L/s194-pre-dryrun.log"
uv run --project . python scripts/era/s194_chem_demil.py --apply --revert-file "$L/s194-fu-pre-revert.json" --dsn "$PRE_DSN" > "$L/s194-pre-apply.log" 2>&1; echo "apply exit=$?"; tail -1 "$L/s194-pre-apply.log"
rm -rf "${L:?}/parity-pg-pre-post"
uv run --project . python scripts/fu/lake_parity.py --a "$P/fu-pre" --b "$P/fu-post" --pg-a "$PRE_DSN" --pg-b "$POST_DSN" --pg-where "account = '0390D'" --work "$L/parity-pg-pre-post" > "$L/parity-pg-pre-post.txt" 2>&1; echo "parity exit=$?"; cat "$L/parity-pg-pre-post.txt"
uv run --project . python -c "import json,sys; a,b=(json.load(open(p)) for p in sys.argv[1:]); print('revert files:', a['database'], 'vs', b['database'], '| before equal:', a['before'] == b['before'], '| re-keyed equal:', a['rekeyed'] == b['rekeyed'], '| deleted equal:', a['deleted_ids'] == b['deleted_ids'], '| inserted equal:', a['inserted'] == b['inserted'])" "$L/s194-fu-pre-revert.json" "$L/s194-fu-post-revert.json"
```
Expected: `dry-run exit=0`, `apply: dry run, every check passed: ROLLED BACK`; `apply exit=0`, `apply: COMMITTED (revert file /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs/s194-fu-pre-revert.json)`; `parity exit=0`, `postgres budget_lines where account = '0390D': A 350 rows, B 350 rows, A not in B 0, B not in A 0, ids equal — equal` and `lake-parity: EQUAL` (the second write of the rehearsal equals the first, ids included: both snapshots were restored from one state and each ran one dry run first); `revert files: govbudget_proof_fu_pre vs govbudget_proof_fu_post | before equal: True | re-keyed equal: True | deleted equal: True | inserted equal: True`. `ids differ` or any `False`: stop and explain it before Step 5 (something else wrote one of the scratch databases, or the write is not deterministic); the release relies on all three writes being one.

- [ ] **Step 5: Rehearse `--revert` on fu-pre (Q24 (b)) — every Postgres pin comes back**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && PRE_DSN=$(. "$P/fu-pre/env.sh" && echo "$GOVBUDGET_PG_DSN")
uv run --project . python scripts/era/s194_chem_demil.py --revert --revert-file "$L/s194-fu-pre-revert.json" --dsn "$PRE_DSN" > "$L/s194-pre-revert.log" 2>&1; echo "revert exit=$?"; tail -1 "$L/s194-pre-revert.log"
uv run --project . python scripts/fu/snapshot_pins.py pg --dsn "$PRE_DSN" --out "$L/pg-pins-pre-reverted.json" && uv run --project . python scripts/fu/snapshot_pins.py pg-compare "$L/pg-pins-pre-scratch.json" "$L/pg-pins-pre-reverted.json"
uv run --project . python scripts/era/s194_chem_demil.py --revert --revert-file "$L/s194-fu-pre-revert.json" --dsn "$PRE_DSN" > "$L/s194-pre-revert-2.log" 2>&1; echo "second revert exit=$?"; tail -1 "$L/s194-pre-revert-2.log"
uv run --project . python scripts/era/s194_chem_demil.py --check --dsn "$PRE_DSN" > "$L/s194-pre-check-after-revert.log" 2>&1; echo "check exit=$?"; tail -1 "$L/s194-pre-check-after-revert.log"
```
Expected: `revert exit=0`, `revert: restored 16 pre-write row(s) (re-keyed 8 back, re-inserted 8, removed 4); COMMITTED`; `pg-pins: 18 tables, <rows> rows -> …` and `pg-pins: EQUAL` — every table of fu-pre's database, `budget_lines` with its ids, equals Task 21e Step 1's pin of it before any write (the pin taken after the snapshot's `jbook_documents.file_path` rewrite: `snapshot.json`'s at-copy `pg.tables` predates that rewrite and would differ on `jbook_documents` alone); `second revert exit=0`, `revert: the database already holds the pre-write rows; nothing to revert`; `check exit=0`, `check: CLEAN, the only differences are #194's (re-key 8, insert 4, delete 8)` (fu-pre is the pre-write reference again). This is abort step A1 of Task 22b, rehearsed. A `pg-pins: DIFFERENT`: the revert is not exact — stop; the release has no tested way back until Task 7 is fixed and Steps 4–5 re-run on fresh snapshots (Task 21d Step 7).

- [ ] **Step 6: Rehearse the abort path's lake half (§8 abort steps 2–3) on a clone of fu-post**

Task 22b's A2 rebuilds the live lake with the deployed code after A1 restored the database. Here the same commands run on `.proofs/fu-abort`, a clone of the post-write fu-post (B's 18-column map, the B7 seed, the `p1_route_safe_codes` table), against fu-pre's reverted database, and the result must equal fu-pre's lake:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && A_ROOT=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a/GovBudget
[ ! -e "$P/fu-abort" ] || { echo "STOP: $P/fu-abort exists"; exit 1; }
cp -c -R "$P/fu-post" "$P/fu-abort" || exit 1
(cd "$A_ROOT" && . "$P/fu-pre/env.sh" "$P/fu-abort" && echo "GOVBUDGET_DATA=$GOVBUDGET_DATA | $GOVBUDGET_PG_DSN" && uv run --project . python -m govbudget jbooks export-facts) > "$L/abort-rehearsal-export-facts.log" 2>&1; echo "export-facts (deployed code) exit=$?"; head -1 "$L/abort-rehearsal-export-facts.log"
(cd "$A_ROOT" && . "$P/fu-pre/env.sh" "$P/fu-abort" && uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select p1_era_code_decisions stg_budget_lines+) > "$L/abort-rehearsal-dbt.log" 2>&1; echo "dbt build (deployed code) exit=$?"; grep -E 'Done\. PASS' "$L/abort-rehearsal-dbt.log"
uv run --project . python -c "import duckdb,sys; c=duckdb.connect(sys.argv[1]); c.execute('drop table if exists main.p1_route_safe_codes'); print('route-safe relation left:', c.execute(\"select count(*) from duckdb_tables() where table_name = 'p1_route_safe_codes'\").fetchone()[0]); c.close()" "$P/fu-abort/duckdb/govbudget.duckdb"
rm -rf "${L:?}/parity-abort-fu-pre"
uv run --project . python scripts/fu/lake_parity.py --a "$P/fu-abort" --b "$P/fu-pre" --relation stg_budget_lines --relation fct_budget_lines --relation fct_decade_series --relation fct_book_diff --relation p1_era_code_decisions --relation p1_era_line_map --relation fct_program_decade_series --relation fct_budget_trajectory --parquet jbooks/budget_lines.parquet --work "$L/parity-abort-fu-pre" > "$L/parity-abort-fu-pre.txt" 2>&1; echo "parity exit=$?"; cat "$L/parity-abort-fu-pre.txt"
rm -rf "${P:?}/fu-abort" "${L:?}/parity-abort-fu-pre"; ls -d "$P/fu-abort" 2>/dev/null | wc -l
```
Expected: `GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-abort | dbname=govbudget_proof_fu_pre host=localhost`, `export-facts (deployed code) exit=0`; `dbt build (deployed code) exit=0` and the grep's dbt Done line, `Done. PASS=<n> … ERROR=0 …` (A's project: no B7 row, no route-safe seed, no `decided_on`; the grep, not `tail -1`, because dbt prints its deprecation summary after the Done line, Task 21e Step 5); `route-safe relation left: 0` (spec §8 abort step 2: a relation B's build created and A's project does not define is dropped); `parity exit=0`, nine `— equal` lines at Task 21a Step 7's counts (`stg_budget_lines` and `fct_budget_lines` 159,903; `p1_era_line_map` 6,927; `parquet jbooks/budget_lines.parquet` 159,903), `lake-parity: EQUAL`; then `0` (the clone is gone). Record `<n>`: Task 22b's A2 must print the same. `DIFFERENT` or a failed build: the abort path does not restore the lake — stop and fix it (Task 22b's A2 text) before the release.

- [ ] **Step 7: Export B@fu-post and the control B2@fu-post**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
for r in fu-post-B fu-post-B2; do echo "$r start $(date +%Y-%m-%dT%H:%M:%S)" >> "$L/export-times.txt"; (. "$P/fu-post/env.sh" "$P/$r" && uv run --project . python -m govbudget export-site) > "$L/export-$r.log" 2>&1; rc=$?; echo "$r end $(date +%Y-%m-%dT%H:%M:%S) exit=$rc" >> "$L/export-times.txt"; echo "$r exit=$rc"; tail -1 "$L/export-$r.log"; done
cat "$L/export-times.txt"
```
Expected: `fu-post-B exit=0`, `fu-post-B2 exit=0`, each `export-site: <d> datasets, <N_post> citations, …` with the same `<N_post>`, above `<N_pre>`; then `export-times.txt`, one `<run> start <time>` and one `<run> end <time> exit=<rc>` line per export run (Steps 2, 3 and this one append to it; after a re-run, the proof note takes each export's last pair).

- [ ] **Step 8: The control — B@fu-post against B2@fu-post**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
uv run --project . python -m govbudget proof diff "$P/fu-post-B/site" "$P/fu-post-B2/site" --control --write-noise "$L/noise-fu.json" > "$L/control-diff.txt" 2>&1; echo "exit=$?"; tail -8 "$L/control-diff.txt"; ls -l "$L/noise-fu.json"
```
Expected: `exit=0`; the counts line with `changed 0 · only in A 0 · only in B 0`; the `equivalent (float noise)` line (non-zero is normal: the marts' parallel double sums) and, if any, `reordered (control class)`; last line `proof diff: EQUAL`; `noise-fu.json` exists. On `DIFFERENT`, `--write-noise` writes nothing and no judged diff below can be read: stop and report.

- [ ] **Step 9: P2 — code changes, A@fu-pre against B@fu-pre**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && D=docs/superpowers/plans/2026-10-04-families-piece1-followups
uv run --project . python -m govbudget proof diff "$P/fu-pre-A/site" "$P/fu-pre-B/site" --noise-from "$L/noise-fu.json" --expect "$D/expected-diff-code.json" --report "$L/p2-diff-report.json" > "$L/p2-diff.txt" 2>&1; echo "exit=$?"; tail -40 "$L/p2-diff.txt"
ls "$P/fu-pre-B/site/json/budget-pdf-receipts"; ls "$P/fu-pre-B/site/json/budget-pdf-receipts/v2" | wc -l
uv run --project . python -c "import json,sys; d=json.load(open(sys.argv[1])); print({x['id']: x['url'] for x in d['docs'] if x['id'] in ('alias:jassm', 'alias:c-130j')})" "$P/fu-pre-B/site/json/search_quick.json"
uv run --project . python -c "import json,sys; a,b=(json.load(open(f'{p}/manifest.json'))['json_sidecars'] for p in sys.argv[1:]); print('json_sidecars', a, '->', b)" "$P/fu-pre-A/site" "$P/fu-pre-B/site"
```
Expected: `exit=0`; one `rule <i> [<path>] matched <count>` line per rule — `json/years_matrix.json` above 0 (it counts the core's changed JSON patterns), the two shards 1 each, each of the 16 v1 receipt rules 16 (256 in all), `/json_sidecars` 1, `/docs/[]` 4 (two removed, two added), `/programs/[]` 2, `/datasets/[]` 2, `/build_checks/dbt_assertions` 1 — no `UNEXPECTED differences`, no `UNMET required rule`, last line `proof diff: PASS`; then `v2`, `4096`; `{'alias:jassm': '/program/0207325F/', 'alias:c-130j': '/program/0401132F/'}`; `json_sidecars <a> -> <a − 254>` (−256 v1 shards, +2 /years/ shards; `<a>` is the 2026-10-04 export's 36,271 plus one per SAM receipt file `json/sam/<UEI>.json` the lake's newer answers add). A reorder outside `noise-fu.json`'s classes reads `changed` and fails like any real difference: investigate it, never add it to a rule list or the noise file.

- [ ] **Step 10: P2 facts — no fact moves, none appears**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
uv run --project . python scripts/fu/fact_delta.py --a "$P/fu-pre-A/site" --b "$P/fu-pre-B/site" --noise-from "$L/noise-fu.json" --report "$L/p2-fact-delta.json"; echo "exit=$?"
```
Expected: `citations: A <N_pre>, B <N_pre>, new in B 0 {}, moved 0, noise-equivalent fields <k>`, the three dataset lines with `A rows not in B 0` and `{}`, `fact-delta: PASS`, `exit=0` — design §7: in P2 `citations.json` is identical; no fid is added, removed or changed.

- [ ] **Step 11: P2b — the /years/ shards against the v1 matrix and the program sidecars**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
uv run --project . python scripts/fu/years_shard_proof.py --a "$P/fu-pre-A/site" --b "$P/fu-pre-B/site" --expect-era-added 14985 --expect-modern-added 63 --report "$L/p2b-report.json"; echo "exit=$?"
```
Expected: three size lines (`years_matrix.json`, `years_matrix/decade.json`, `years_matrix/detail.json`, each at most 4,194,304 bytes; the core at most 780,074 gzip — Task 13's and Task 21b's simulation of this export reads 1,100,823 / 344,303, 1,390,739 / 433,932 and 1,231,643 / 284,230, a few bytes more on the core and the detail shard for the org-split rows' amount-type cells); `build_id <64 hex>; rows A 1,938, B 1,938; leg j mismatches 0`; `decade cells added: era 14,985, modern 63, era_default 4,995, modern_default 35, era_org_split 147, modern_org_split 63`; the org-split rows' non-decade additions (the amount-type and delta cells `_acct_key` used to lose, e.g. `fy_2025_total`, `fy2526_change`, on 20-DCSA, 20-DTRA, 30-DMACT, 30-DTRA, 30-OSD, 500-DHRA, 500-DLA — whatever the program pages publish); `totals-chart panel A: 524 of 1,938 programs; FY2024A->FY2026R 9.34%; first->last 108.17%` and `totals-chart panel B: 1,063 of 1,938 programs; FY2024A->FY2026R -2.61%; first->last 103.71%`; `years-shard-proof: PASS`; `exit=0`. These are the numbers Task 22d's go-ahead names for Q15.

- [ ] **Step 12: P1 — lake changes, B@fu-pre against B@fu-post**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && D=docs/superpowers/plans/2026-10-04-families-piece1-followups
uv run --project . python -m govbudget proof diff "$P/fu-pre-B/site" "$P/fu-post-B/site" --noise-from "$L/noise-fu.json" --expect "$D/expected-diff-lake.json" --report "$L/p1-diff-report.json" > "$L/p1-diff.txt" 2>&1; echo "exit=$?"; tail -60 "$L/p1-diff.txt"
```
Expected: `exit=0`; a `rule <i> … matched <count>` line per rule, every required rule above 0 — the `/{fid}/recorded_value` and `/{fid}/inputs` rules of `json/citations.json` 11 each (the cite-shard rules 11 each too), `json/program_details/0390DOM.json` 1, `json/programs_excluded.json` `/[]` 1; no `UNEXPECTED differences`, no `UNMET required rule`; last line `proof diff: PASS`. A FAIL names each unexpected path or unmet rule: stop and explain it; never widen the rules without the owner.

- [ ] **Step 13: P1 facts — every new fact traces to 0390DOM, eleven aggregates move by exactly +3,243**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && D=docs/superpowers/plans/2026-10-04-families-piece1-followups
uv run --project . python scripts/fu/fact_delta.py --a "$P/fu-pre-B/site" --b "$P/fu-post-B/site" --expect "$D/expected-fact-moves-lake.json" --noise-from "$L/noise-fu.json" --diff-report "$L/p1-diff-report.json" --report "$L/p1-fact-delta.json"; echo "exit=$?"
```
Expected: `citations: A <N_pre>, B <N_post>, new in B <WAVE_D> {"derived": <d>, "workbook": <w>}, moved 11, …` with `<WAVE_D>` = `<N_post>` − `<N_pre>`; eleven `moved <fid>: <a> -> <b> (+3243.000, inputs +1)` lines, among them `709cbd08c6b7dfb0: 385268393.000 -> 385271636.000`, `d2f5b699e5123b11: 43338494.000 -> 43341737.000` and `6ca3c62f32d31298: 227538773.000 -> 227542016.000`; `data/budget_lines.parquet: A 8,549 rows, B 8,553, A rows not in B 0, B-only rows by pe_bli {"0390DOM": 4}`; `data/budget_lines_decade.parquet: …, B-only rows by pe_bli {"0390D-ARMY-L1": <e>, "0390DOM": <m>}`; `data/fct_budget_trajectory.parquet: …` with `{}` or `{"0390DOM": 1}`; `breakdowns: changed 11 (moved facts), only in B <k> (new facts)`; `fact-delta: PASS`; `exit=0`. Record `<WAVE_D>`: Task 22c checks the release's citation delta against it.

- [ ] **Step 14: P1 content — the 0390DOM page, the map, the summary and the totals**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
uv run --project . python - "$P/fu-post-B/site" <<'PY' | tee "$L/p1-content.txt"
import json, sys
import duckdb
site = sys.argv[1]
side = json.load(open(f"{site}/json/program_details/0390DOM.json"))
points = [p for pts in (side.get("decade_series") or {}).values() for p in pts]
print("0390DOM sidecar:", side.get("printed_code"), side.get("exhibit_family"), "| decade points", len(points),
      "| era points", sum(p["edition"] <= 2023 for p in points), "| editions", sorted({p["edition"] for p in points}))
s = json.load(open(f"{site}/json/era_map_summary.json"))
for k in ("same_program", "exclude_route_unsafe"):
    t = s["totals"][k]
    print(f"era summary {k}:", t["actuals_thousands"], t["chains"], t["lines"])
print("era summary B7:", [r for r in s["by_ruling"] if r["ruling"] == "R-DEC-ERA-B7"])
meta = json.load(open(f"{site}/json/site_meta.json"))
pc = meta["programs_coverage"]
print("universe:", pc["universe_total_thousands"], pc["universe_billions"], pc["coverage_pct"], "| program_pages", meta["counts"]["program_pages"])
flow = json.load(open(f"{site}/json/flow_chart.json"))["budget"]
print("flow A|0390D:", [m["v"] for n in flow["nodes"] if "other" in n for m in n["other"]["members"] if m["k"] == "A|0390D"],
      "| bridge not yet crosswalked:", flow["bridge"]["not_yet_crosswalked"])
print("programs_excluded 0390DOM:", [e for e in json.load(open(f"{site}/json/programs_excluded.json")) if e["pe_bli"] == "0390DOM"])
print("0390DOM in search_quick:", any("0390DOM" in json.dumps(d) for d in json.load(open(f"{site}/json/search_quick.json"))["docs"]),
      "| in years core:", "0390DOM" in open(f"{site}/json/years_matrix.json").read())
con = duckdb.connect()
print("budget_lines 0390DOM:", con.execute(f"select amount_type, amount_thousands from read_parquet('{site}/data/budget_lines.parquet') where pe_bli = '0390DOM' order by amount_type").fetchall())
cols = [r[0] for r in con.execute(f"describe select * from read_parquet('{site}/data/p1_era_line_map.parquet')").fetchall()]
print("published map:", len(cols), "columns, decided_on at", cols.index("decided_on") + 1)
PY
```
Expected:
```
0390DOM sidecar: O&M om | decade points <n> | era points <e> | editions [...]
era summary same_program: 727939107.0 919 5860
era summary exclude_route_unsafe: 5030464.0 1 7
era summary B7: [{'actuals_thousands': 801553.0, 'chains': 1, 'codes': 1, 'decision': 'same_program', 'lines': 7, 'ruling': 'R-DEC-ERA-B7'}]
universe: 385271636.0 385.3 77.9 | program_pages 2563
flow A|0390D: [213282] | bridge not yet crosswalked: 227542016
programs_excluded 0390DOM: [{'amount_thousands': <a>, 'pe_bli': '0390DOM', 'reason': 'no_detail', 'title': <the P-1 line title>}]
0390DOM in search_quick: False | in years core: False
budget_lines 0390DOM: [('fy_2024_actuals', 87404.0), ('fy_2025_enacted', 20745.0), ('fy_2026_disc_request', 3243.0), ('fy_2026_total', 3243.0)]
published map: 18 columns, decided_on at 14
```
with `<e>` at most 21 (design §4.5: "up to 21 era points") and the editions running from PB2017 to PB2026; record `<n>` and `<e>` for the proof note and the go-ahead. (`<a>` and the title are what the exporter lists for an excluded page: the PB2026 amount and the P-1's printed title, "Chem Demilitarization - O&M" in #194.) A value that differs from the design's figure is a finding: stop and explain it before Task 21g.
