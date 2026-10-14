<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 22c: Release 1 — the release export, its counts and fingerprint, and the release-state checks

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §8 step 3 (export between :21 and :45 with the SAM mtime check; record the counts — `SAM_D` from `companies_with_sam`, the wave's citation delta the remainder; fingerprint `data/site/{data,citations,manifest.json}`; the abort path restores the pre-release copy), step 4 (`proof diff` of B@fu-post/site against the release `data/site` with the noise file — only SAM-registration rules; the F-15 history matches the new pin; W6; Postgres records 0 worktree paths), step 5 (W3 and W5). Piece-1 Task 23 Steps 3–5 (INT-1, RR-2, RR-3) are the model.

**Files:**
- Modify (only if `evals check` finds stale answers explained by this release): `evals/phase5_questions.yaml`
- **Shared-state write:** the live `data/site` (the export). Local only: `tmp/fu-release-counts.json` (the worktree's ignored `tmp/`), `.proofs/fu-release-export.sha256`, `.proofs/fu-release-export.built_at`, logs under `.proofs/fu-logs/`.

**Interfaces:**
Consumes: Task 22b's live state; Task 22a's `.proofs/fu-release-pre-site` and `release-pre-counts.json`; Task 21f's `fu-post-B/site`, `noise-fu.json` and `p1-fact-delta.json` (`citations.new_in_b` = WAVE_D); Task 21c's `expected-diff-release.json`; Task 21g's F-15 pin `tests/fixtures/f15/history.sha256`; Task 5's `govbudget link-coverage --site-dir DIR --baseline FILE`; `verify-era-map`, `verify-phase5b1`, `verify-phase5e`, `verify-lineage`, `evals check|refresh`.
Produces: the release export in the main lake's `data/site`; `tmp/fu-release-counts.json` (`pre`, `release`, `SAM_D`, `WAVE_D`) for Tasks 22d–22e; the fingerprint `.proofs/fu-release-export.sha256` + `.built_at`, and **the fingerprint check** (defined in Step 2) that opens Task 22d's build, dry run and deploy steps.

Measured for this task (2026-10-13): production's export is 143,841 citations with 149 SAM registrations; the lake holds 164 SAM entities; piece 1's release export took 13–17 minutes including the receipt pass; `verify-phase5b1` takes about 4.5 minutes; `jbook_documents` rows whose `file_path` holds `/.claude/worktrees/` (LAUNCH.md rule of 2026-09-12): 0 on 2026-10-04.

- [ ] **Step 1: Export (SHARED LAKE WRITE: `data/site`)**

Start only between :21 and :45 (the SAM job writes `data/parquet/sam` at :17, and the export reads it):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -lt 21 ] || [ "$MIN" -gt 45 ]; then echo "WAIT: start between :21 and :45 (minute $MIN)"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs" && S=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet
S0=$(stat -f %m "$S") && GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget export-site > "$L/export-release.log" 2>&1; echo "exit=$?"; S1=$(stat -f %m "$S"); [ "$S0" = "$S1" ] && echo "SAM parquet unchanged during the export" || echo "RE-RUN: SAM parquet changed during the export"; tail -2 "$L/export-release.log"
```
Expected: `exit=0`, `SAM parquet unchanged during the export`, the `budget PDF receipts: …` and `export-site: … <N> citations …` lines. On `RE-RUN`, export again in the next window. A failure: the abort path (Task 22b; A3 too).

- [ ] **Step 2: Record what ships — and reconcile it with the proof**

Every export reads the SAM parquet live, so the release also carries the SAM.gov registrations stored since production's export (piece-1 INT-1/RR-3). Each published registration carries exactly one derived citation, so `SAM_D` is the `companies_with_sam` delta and the rest of the citation delta must be the wave's own, which P1 measured:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && mkdir -p tmp
uv run --project . python - "$P" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
def measure(site):
    meta = json.loads((site / "json" / "site_meta.json").read_text())
    return {"built_at": json.loads((site / "manifest.json").read_text())["built_at"],
            "citations": meta["counts"]["citations"], "companies_with_sam": meta["counts"]["companies_with_sam"],
            "sam_files": len(list((site / "json" / "sam").glob("*.json"))),
            "dbt_assertions": meta["build_checks"]["dbt_assertions"]}
pre = measure(p / "fu-release-pre-site")
rel = measure(Path("/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site"))
post_b = measure(p / "fu-post-B" / "site")
wave = json.loads((p / "fu-logs" / "p1-fact-delta.json").read_text())["citations"]["new_in_b"]
sam_d = rel["companies_with_sam"] - pre["companies_with_sam"]
out = {"pre": pre, "release": rel, "fu_post_B": post_b, "SAM_D": sam_d,
       "WAVE_D": rel["citations"] - pre["citations"] - sam_d, "WAVE_D_proof": wave}
Path("tmp/fu-release-counts.json").write_text(json.dumps(out, indent=2) + "\n")
(p / "fu-release-export.built_at").write_text(rel["built_at"] + "\n")
print(json.dumps(out, indent=2))
assert out["WAVE_D"] == wave, "the release's citation delta is not P1's plus the SAM registrations"
assert rel["dbt_assertions"] == post_b["dbt_assertions"]
assert (rel["citations"] - post_b["citations"]) == (rel["companies_with_sam"] - post_b["companies_with_sam"])
print("reconciled: release = production + WAVE_D + SAM_D; release - B@fu-post = SAM registrations only")
PY
```
Expected: `pre` is production's export (`built_at` 2026-10-04T19:25:35.216512+00:00, 143,841, 149, 149, 196); `release` has a newer `built_at`, `companies_with_sam` and `sam_files` equal (164 if every stored entity publishes), `dbt_assertions` B's count (Task 21d Step 5); `WAVE_D` equal to `WAVE_D_proof`; the last line `reconciled: …`. An assertion error: stop and read the numbers (an export from other code, or a lake that moved after Task 22b) — then the abort path.

Then fingerprint the release export (the fixed-name objects `upload_r2.sh` overwrites, plus the manifest whose `built_at` changes on every export):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget && find data/site/data data/site/citations data/site/manifest.json -type f -print0 | sort -z | xargs -0 shasum -a 256 > .proofs/fu-release-export.sha256 && wc -l < .proofs/fu-release-export.sha256 && shasum -a 256 -c --quiet .proofs/fu-release-export.sha256 && echo "release export fingerprinted"
```
Expected: a line count and `release export fingerprinted`.

**The fingerprint check.** Task 22d runs this block before the build, before the dry run and before the deploy (other worktrees link this same `data/site`, and a re-export by any of them would put other code's `data/` and `citations/` under this release's pages; piece-1 RR-2, INT-4). It reads only `data/site` and `.proofs`:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
LIVE=/Users/andeslee/Documents/Cursor-Projects/GovBudget
(cd "$LIVE" && shasum -a 256 -c --quiet .proofs/fu-release-export.sha256) || { echo "STOP: data/site is no longer the release export (fingerprint mismatch)"; exit 1; }
H=$(shasum -a 256 "$LIVE/data/site/json/f15_funding_history.json" | cut -d' ' -f1); { [ -n "$H" ] && [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ]; } || { echo "STOP: F-15 history does not match the pin (got ${H:-nothing})"; exit 1; }
for f in json/years_matrix.json json/years_matrix/decade.json json/years_matrix/detail.json json/program_details/0390DOM.json data/p1_era_line_map.parquet; do [ -s "$LIVE/data/site/$f" ] || { echo "STOP: $f is missing from data/site"; exit 1; }; done
[ -z "$(ls "$LIVE/data/site/json/budget-pdf-receipts" | grep -v '^v2$')" ] || { echo "STOP: v1 receipt files are back in data/site"; exit 1; }
B=$(uv run --project . python -c "import json; print(json.load(open('$LIVE/data/site/manifest.json'))['built_at'])"); [ "$B" = "$(cat "$LIVE/.proofs/fu-release-export.built_at")" ] || { echo "STOP: manifest built_at ($B) is not the release export's"; exit 1; }
echo "data/site is the release export: built_at $B"
```
Expected: `data/site is the release export: built_at <the built_at Step 2 recorded>`. Any `STOP`: do not go on; on a fingerprint mismatch `shasum -c` names the differing files just above it. Re-run Step 1 (then everything after it) or take the abort path.

- [ ] **Step 3: Release-state checks — what ships is what was proven**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}" && L="$P/fu-logs" && D=docs/superpowers/plans/2026-10-04-families-piece1-followups && LIVE=/Users/andeslee/Documents/Cursor-Projects/GovBudget
uv run --project . python -m govbudget proof diff "$P/fu-post-B/site" "$LIVE/data/site" --noise-from "$L/noise-fu.json" --expect "$D/expected-diff-release.json" --report "$L/release-state-report.json" > "$L/release-state.txt" 2>&1; echo "proof diff exit=$?"; tail -16 "$L/release-state.txt"
H=$(shasum -a 256 "$LIVE/data/site/json/f15_funding_history.json" | cut -d' ' -f1); [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ] && echo "F-15 history matches the pin $H"
uv run --project . python -m govbudget link-coverage --site-dir "$LIVE/data/site" --baseline data/research/link_coverage/baseline.json > "$L/link-coverage-release.txt" 2>&1; echo "link-coverage exit=$?"; tail -3 "$L/link-coverage-release.txt"
"$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_PG_DSN" -At -c "select count(*) from jbook_documents where file_path like '%/.claude/worktrees/%';"
```
Expected: `proof diff exit=0` with `changed`/`only in` counts covered by the SAM rules only (all 0 when no SAM answer landed after fu-post) and last line `proof diff: PASS` (a late SAM registration also moves `data/dim_entities.parquet` and its citation's `formula`/`retrieved_at`, which no rule excuses, so it stops the release for the owner: fail-closed by design, and none is expected since the SAM job finished on 2026-10-13); `F-15 history matches the pin <H>` (Task 21g's); `link-coverage exit=0` ending `link-coverage: PASS` (W6: budget figures 100% source-linked, no figure lost a complete receipt); `0`. Any failure: the abort path.

- [ ] **Step 4: W3 and W5 on the live state**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs" && S=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet
for gate in verify-era-map verify-phase5b1 verify-phase5e verify-lineage; do MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN) before ${gate}: wait until :23 and re-run this block"; exit 0; fi; S0=$(stat -f %m "$S"); GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget ${gate} > "$L/release-${gate}.log" 2>&1; echo "${gate} exit=$?"; [ "$(stat -f %m "$S")" = "$S0" ] || echo "RE-RUN ${gate}: the SAM parquet changed while it ran"; tail -1 "$L/release-${gate}.log"; done
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN) before evals check: wait until :23 and re-run this block"; exit 0; fi
S0=$(stat -f %m "$S"); GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget evals check > "$L/release-evals.log" 2>&1; echo "evals exit=$?"; [ "$(stat -f %m "$S")" = "$S0" ] || echo "RE-RUN evals check: the SAM parquet changed while it ran"; tail -3 "$L/release-evals.log"
```
The guard sits inside the loop, before each gate, because the four gates and `evals check` together run longer than the gap between two SAM ticks (`verify-phase5b1` alone about 4.5 minutes; the SAM job has fired off schedule after a wake, `logs/sam-daily.out.log` 2026-10-13 22:23 and 23:24 UTC); each gate also checks that `data/parquet/sam/entities.parquet` did not change under it. Expected: no `WAIT` and no `RE-RUN` line; each gate `exit=0` with `verify-era-map: PASS` (legs a–h), `verify-phase5b1: PASS`, `verify-phase5e: PASS`, `verify-lineage: PASS`; `evals exit=0`, `evals check: <n> ok, 0 stale, <k> skipped` and `evals check: PASS`. On `WAIT`, re-run the whole block from :23 (every gate is read-only and repeatable); on `RE-RUN <gate>`, re-run the block. A gate that fails and cannot be cleared: the abort path. If `evals check` lists STALE answers, read each `expected=… live=…`; only when every one is explained by this release (the 0390DOM rows, the B7 map rows, the SAM registrations) refresh and re-check — otherwise stop:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs"
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python -m govbudget evals refresh && GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget evals check > "$L/release-evals.log" 2>&1; echo "evals exit=$?"; tail -3 "$L/release-evals.log"; git -C .. status --porcelain -- GovBudget/evals
```
Expected: `evals check: PASS` and ` M GovBudget/evals/phase5_questions.yaml`. Then commit exactly that file:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/evals/phase5_questions.yaml && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(evals): refresh answers moved by the follow-ups release-1 export" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `1 file changed`.
