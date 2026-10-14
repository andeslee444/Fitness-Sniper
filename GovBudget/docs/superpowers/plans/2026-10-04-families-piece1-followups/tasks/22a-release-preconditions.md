<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 22a: Release 1 — preconditions: the live lake still equals fu-pre

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §8 step 1 (the worktree is clean; pytest is green on the 55432 cluster; the live lake still carries the PRE-write state the proof started from — a fresh snapshot carries fu-pre's pins, SAM files excepted), step 3 (keep `.proofs/fu-release-pre-site`), §2.3 Q24 (b) (the abort path needs a pre-write pin of the live database). Piece-1 Task 23 (as amended 2026-10-04: RR-1…RR-6, INT-1…INT-5) is the model.

**Files:**
- No tracked file changes. Shared Postgres: creates the scratch database `govbudget_proof_fu_rel` only (through `govbudget proof snapshot`). Local only: `.proofs/fu-rel/`, `.proofs/fu-release-pre-site/` (an APFS copy of the live `data/site`), logs under `.proofs/fu-logs/`.

**Interfaces:**
Consumes: Task 21d's `.proofs/fu-pre` and `$L/shas.txt` (line 2 = B, the code the proof exported with); Task 21a's `snapshot_pins.py compare|pg|pg-compare`; `govbudget proof snapshot`.
Produces: `$L/pins-fu-pre-fu-rel.txt` (EQUAL); `$L/live-pg-pins-pre.json` (the live database's pins before the write, ids included: Task 22b compares after the write, and the abort path compares after a `--revert`); `.proofs/fu-release-pre-site` (production's export, the abort path's restore source and the base of Task 22c's counts); `$L/release-pre-counts.json`.

Measured for this task (2026-10-13, read-only): the live export (`data/site/manifest.json` `built_at` 2026-10-04T19:25:35.216512+00:00) carries 143,841 citations, `companies_with_sam` 149 (149 files in `json/sam/`), `build_checks.dbt_assertions` 196; production `/.build-meta.json` `git_head` 916ae88eee04f1e2445040933f83a3e279c04209; the hourly SAM job's state reads "all 200 published families have a stored SAM answer" and the lake's `parquet/sam/entities.parquet` holds 164 rows (written 2026-10-04 21:17), so the next export publishes about 15 more registrations than production; `parquet/sam/daily/state.json` is rewritten every hour (which is why the pins skip `sam/`); the worktree's `data/{site,duckdb,parquet,raw,raw_docs}` and `.env` are symlinks into the main checkout.

- [ ] **Step 1: The worktree is clean, the code is the proven B, and the tests pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs" && B_SHA=$(sed -n 2p "$L/shas.txt") && : "${B_SHA:?Task 21d Step 3 first}"
git -C .. status --porcelain -- GovBudget | grep -v '^??'; echo "(tracked changes above: expect none)"; git -C .. log --oneline -1
git -C .. diff --quiet "$B_SHA" HEAD -- GovBudget/src GovBudget/dbt GovBudget/data-seeds GovBudget/migrations GovBudget/scripts/era && echo "export code at HEAD = the proven B $B_SHA"
"$GOVBUDGET_PG_BIN/pg_isready" -h 127.0.0.1 -p 55432; GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q 2>&1 | tail -1
launchctl list | grep -i fiscalreceipts
```
Expected: no tracked change; HEAD is Task 21i's commit; `export code at HEAD = the proven B <sha>` (only `tests/`, `site/` and `docs/` moved since the proof's exports); `127.0.0.1:55432 - accepting connections`; pytest `… passed …` with 0 failed; one `launchctl` line ending `com.fiscalreceipts.sam-daily` and no other `fiscalreceipts` job (a loaded `refresh` job would run `govbudget build` or `export-site` from the main checkout during Task 22b's hazard window: stop and ask the owner to unload it first). If the export code moved after B, the proof is stale. Which part re-runs depends on what moved; list it with `git -C .. diff --stat "$B_SHA" HEAD -- GovBudget/src GovBudget/dbt GovBudget/data-seeds GovBudget/migrations GovBudget/scripts/era`:
- **`dbt/`, `data-seeds/`, `migrations/` or `scripts/era/` moved:** fu-post's written state (Task 21e's s194 write, `jbooks export-facts` and dbt build) and fu-pre's rehearsal were made by superseded code. Discard the proof state and restart at Task 21d Step 7 (fresh snapshots), then run 21d Step 8 through 21i. First: remove the four export clones (`rm -rf "${P:?}/fu-pre-A" "${P:?}/fu-pre-B" "${P:?}/fu-post-B" "${P:?}/fu-post-B2"`), run Task 21d Step 7's discard block (it drops `govbudget_proof_fu_pre` and `govbudget_proof_fu_post` and removes `.proofs/fu-pre` and `fu-post`), rename `$L/s194-fu-post-revert.json` and `$L/s194-fu-pre-revert.json` to `….superseded` (`--apply` refuses an existing revert file), and re-run Task 21d Step 3 (it records the new HEAD as B in `shas.txt`) and Step 5 (B's dbt manifest from the changed `dbt/`); Step 6's W1 too if `src/` or `scripts/era/` moved.
- **Only `src/` moved** (and not the modules the writes ran: `src/govbudget/jbooks/{p1_loader,route_safe_codes,export_facts}.py` and `config.py`, which `s194_chem_demil.py` and `jbooks export-facts` load; a change there counts as the case above): the snapshots, fu-post's written state and the rehearsals of Task 21f Steps 4–6 still hold (they ran `scripts/era/`, `dbt/`, those modules and the A worktree, none of which moved). Re-run Task 21d Step 3 (the new B in `shas.txt`), remove the four export clones as above, re-clone them with Task 21f Step 1, re-run Step 2 (A's export into its fresh clone; the same `<N_pre>` as before) and restart from Step 3; skip Steps 4–6 (a second Step 4 would spend new id-sequence values on fu-pre, and its revert file already exists), then Steps 7–14, then 21g–21i.

Either way, return here only after Task 21i's note is re-committed.

- [ ] **Step 2: A fresh snapshot carries fu-pre's pins (shared Postgres: creates `govbudget_proof_fu_rel`)**

Start only between :23 and :45 (the tool also refuses at :15–:20):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -lt 23 ] || [ "$MIN" -gt 45 ]; then echo "WAIT: start between :23 and :45 (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"; if [ -e "$P/fu-rel" ]; then echo "STOP: $P/fu-rel exists"; exit 1; fi
uv run --project . python -m govbudget proof snapshot --out "$P/fu-rel" --scratch-db govbudget_proof_fu_rel > "$L/snapshot-fu-rel.log" 2>&1; echo "snapshot exit=$?"; tail -3 "$L/snapshot-fu-rel.log"
uv run --project . python scripts/fu/snapshot_pins.py compare "$P/fu-pre" "$P/fu-rel" > "$L/pins-fu-pre-fu-rel.txt" 2>&1; echo "pins exit=$?"; cat "$L/pins-fu-pre-fu-rel.txt"
```
Expected: `snapshot exit=0` with the summary lines; `pins exit=0`, `snapshot-pins: EQUAL`. On `DIFFERENT` the live lake moved after the proof (the lines above the verdict name what: a re-export of `data/site`, a dbt build, a Postgres write): stop and report to the owner. The proof (Task 21d from Step 2) must be re-taken on the new state; never release onto a lake the proof did not start from. A refusal: remove `.proofs/fu-rel` (and `dropdb govbudget_proof_fu_rel` if it exists) and re-run in a later window.

- [ ] **Step 3: Pin the live database before the write**

The same query and settings as the snapshot's pins (Task 21a), on the live database itself (read-only). They must equal the pins `govbudget proof snapshot` took on `fu-rel`'s restored dump, which ties the abort path's pin to the proof's:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
uv run --project . python scripts/fu/snapshot_pins.py pg --dsn "$GOVBUDGET_PG_DSN" --out "$L/live-pg-pins-pre.json"
uv run --project . python -c "import json,sys; m=json.load(open(sys.argv[1])); json.dump({t: {'rows': v['rows'], 'md5': v['md5'], 'drop': []} for t, v in m['pg']['tables'].items()}, open(sys.argv[2], 'w'), indent=1, sort_keys=True)" "$P/fu-rel/snapshot.json" "$L/fu-rel-pg-pins.json"
uv run --project . python scripts/fu/snapshot_pins.py pg-compare "$L/fu-rel-pg-pins.json" "$L/live-pg-pins-pre.json"
```
Expected: one `pg-pins: 18 tables, <rows> rows -> …` line and `pg-pins: EQUAL`. On `DIFFERENT`, a Postgres write landed after Step 2: stop and re-run Step 2. (No id-free pin is taken: every comparison of live with fu-post includes ids, README decision 2.)

- [ ] **Step 4: Keep production's export, and record its counts**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs"
[ -e "$P/fu-release-pre-site" ] || cp -cR /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site "$P/fu-release-pre-site"
uv run --project . python - "$P/fu-release-pre-site" "$L/release-pre-counts.json" <<'PY'
import json, sys
from pathlib import Path
site = Path(sys.argv[1])
meta = json.loads((site / "json" / "site_meta.json").read_text())
out = {"built_at": json.loads((site / "manifest.json").read_text())["built_at"],
       "citations": meta["counts"]["citations"], "companies_with_sam": meta["counts"]["companies_with_sam"],
       "sam_files": len(list((site / "json" / "sam").glob("*.json"))),
       "dbt_assertions": meta["build_checks"]["dbt_assertions"]}
Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out))
PY
curl -s https://fiscalreceipts.com/.build-meta.json | grep git_head
```
Expected: `{"built_at": "2026-10-04T19:25:35.216512+00:00", "citations": 143841, "companies_with_sam": 149, "sam_files": 149, "dbt_assertions": 196}` and `"git_head": "916ae88eee04f1e2445040933f83a3e279c04209"`. Anything else means `fu-release-pre-site` is not production's export (or production moved): stop and read before going on. The copy is kept: if `.proofs/fu-release-pre-site` already existed from an earlier attempt, the block keeps the older copy — check that its `built_at` is still production's.

- [ ] **Step 5: The worktree reads the main lake and the main `.env`**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
for d in site duckdb parquet raw raw_docs; do if [ -e "data/$d" ] && [ ! -L "data/$d" ]; then echo "STOP: data/$d is a real directory"; else ln -sfn "/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/$d" "data/$d"; fi; done; [ -e .env ] || ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/.env .env; ls -l data .env | grep -- '->'; git -C .. status --porcelain -- GovBudget/data GovBudget/.env
```
Expected: six symlinks into `/Users/andeslee/Documents/Cursor-Projects/GovBudget/` and no status output. Never print `.env`'s contents.
