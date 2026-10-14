<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G2 (2026-10-13). -->

### Task 10: Owner batch B7 — the era O&M chain joins 0390DOM (#194; the owner has already answered)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §4.5 (after the alias, `propose` sees code `O&M` continue into PB2024–PB2026 and classes the chain A1; §6.2 sends a class result that differs from a seeded decision to `review.csv`; "Under Q3 the change is batch B7": `review_batch_page` renders it, the owner answers, `era-map ratify --batch B7 --decided-on <date>` writes `same_program`, ruling `R-DEC-ERA-B7`; "What moves": `exclude_route_unsafe` becomes 5,030,464K in 1 chain of 7 lines), §2.2 Q3 and Q4, §2.3 Q25 (the held chain's old class row leaves the seed until the batch is ratified). Owner decision (binding): Q3 was answered in chat on 2026-10-04 as "Join it (Recommended)" (ROADMAP "Follow-ups first", commit 532205c9); `B7.json` records that reply verbatim as `owner_reply`. **No new owner touchpoint:** do not publish the batch page or ask again.

**Files:**
- Create: `data/research/era_map/batches/B7.json`
- Modify (only through the tools): `data/research/era_map/review.csv` (`propose`, then `answer`, then `propose`), `data/research/era_map/chains.csv`, `data/research/era_map/keys.csv`, `data/research/era_map/counts.json` (`propose`), `dbt/seeds/p1_era_code_decisions.csv` (`propose` drops the O&M class row; `ratify` adds the B7 row)
- Modify: `dbt/models/marts/schema.yml` — `p1_era_line_map` → `decision`'s description (anchor on `exclude_route_unsafe (0390D O&M / RDT&E)`, about line 446)
- Local, git-ignored: `tmp/era-review/B7.html` and `tmp/era-review/B7.json` (the render's page and manifest; `GovBudget/.gitignore` ignores `/tmp/`)

**Interfaces:**
Consumes: Task 8 (the alias in `era_map.load_inputs`/`classify`: the era O&M chain classes A1); Task 4a (`propose` holds a chain whose class result differs from its seeded class row: `review.csv` row with `proposed_decision` `same_program` and reason `A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded exclude_route_unsafe (R-DEC-ERA-EXCLUDE, 2026-10-02) — confirm or keep the seeded decision; no silent overturn`, `chains.csv` `left_ruling_reason` `class result differs from the seeded decision`, the old class row removed from the seed); Task 4b (`ratify`'s second success line `era-map ratify: next, ONE build: …`); Task 4c (`render` records `review_sha256` in the manifest; `answer` refuses a `review.csv` changed since render; errors print `review_batch_page: ERROR — …` and exit 2); Task 9 (the map's `decided_on` column carries this row's 2026-10-04 once the map is rebuilt). The live lake is read, never written.
Produces (Tasks 11, 21 and 22 read these):
- The seed row `O&M|0390D||2017-2023`: `decision` `same_program`, `ruling` `R-DEC-ERA-B7`, `decided_on` `2026-10-04`, `decided_by` `owner`, `n_keys` `7`, `keys_sha256` `523cd96c7d9031b4c4a43c45f4b72731a6fa140873c51c52b9a3700d47d595a2`, pins blank, `proposed_rule` `A1`, `modern_title` `Chem Demilitarization - O&M`, `evidence` `continuity=7/7; actuals_k=801553; proposed=same_program: A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded exclude_route_unsafe (R-DEC-ERA-EXCLUDE, 2026-10-02) — confirm or keep the seeded decision; no silent overturn`. The RDT&E row `RDT&E|0390D||2017-2023` stays `exclude_route_unsafe` / R-DEC-ERA-EXCLUDE (Q4).
- `counts.json`: `rulings` SAME 810 / EXCLUDE 46 / HISTORY 271; `owner_batch_chains` 126; `chain_groups.unsafe` 1; `key_classes.UNSAFE` 7; `ruled_actuals_k.R-DEC-ERA-EXCLUDE` "5030464"; `review_rows` 0.
- Rebuilt with the seed (Tasks 21 and 22, never here): `p1_era_line_map` gives the 7 `0390D-ARMY-L1` keys `program_key` `0390DOM`, `same_program`, `R-DEC-ERA-B7`; `fct_program_decade_series` gains 21 `era_line_map` grains under `0390DOM` (PB2017–PB2023 × actuals/enacted/request, 2,333,721 thousand in all).
- **Window of disagreement.** From Step 2's `propose` until Task 22's dbt build, the committed seed differs from the live warehouse's `p1_era_line_map` (still built from the old seed): `era-map check --strict` fails between Step 2 and Step 6 (the chain is undecided), and verify-era-map leg b reports a stale build for `O&M|0390D||2017-2023` from Step 6 until the release rebuilds the map. Run no dbt build in this task (Task 4a's notes: a build between `propose` and `ratify` would fail `assert_p1_era_map_no_undecided`).

Measured for this task (2026-10-13): the whole flow below ran on a scratch tree of HEAD plus Tasks 3, 4a, 4c, 6, 7 and 8, with a copy of `data/research/era_map` and the committed seed, against the live lake read-only (minute 26); every expected line below is that run's output. A copy of the live DuckDB file then built `p1_route_safe_codes p1_era_code_decisions p1_era_line_map fct_program_decade_series` with the B7 seed: `Done. PASS=37 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=37` (`assert_route_safe_codes_valid`, `assert_p1_era_map_no_undecided` and `assert_program_decade_conservation` included); the map gave the 7 O&M keys `program_key` `0390DOM` (`keys_sha_ok` true) and the RDT&E keys `exclude_route_unsafe` with `program_key` NULL; the program table held 21 `era_line_map` grains under `0390DOM`, 2,333,721 thousand in all (PB2017 FY2015 actuals 180,674 … PB2023 FY2023 request 84,612). Task 4b was not on the scratch tree, so its second ratify line is quoted from Task 4b's interface.

- [ ] **Step 1: Preconditions (read-only)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
git status --short -- data/research/era_map dbt/seeds | wc -l
grep -c '^O&M|0390D||2017-2023,O&M,0390D,,2017,2023,exclude_route_unsafe,' dbt/seeds/p1_era_code_decisions.csv
uv run --project . python -m govbudget era-map check | tail -1
```

Expected: `0` (no local changes to the files this task writes); `1` (the seed still holds the 2026-10-02 exclusion); `era-map check: 0 undecided chain(s), 0 stale decision(s)`. Tasks 4, 8 and 9 must be committed: `git log --oneline -25` shows their commits.

- [ ] **Step 2: Propose — the O&M chain goes to review**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -m govbudget era-map propose && git status --short -- data/research/era_map dbt/seeds
uv run --project . python - <<'EOF'
import csv
for r in csv.DictReader(open("data/research/era_map/review.csv", newline="")):
    print(r["chain_id"], r["first_edition"], r["last_edition"], r["proposed_decision"],
          r["keys_sha256"][:12], r["continuity"], r["actuals_k"], "|", r["reason"])
print(sum(1 for r in csv.DictReader(open("dbt/seeds/p1_era_code_decisions.csv", newline=""))
          if r["line_item_code"] == "O&M" and r["account"] == "0390D"))
EOF
uv run --project . python -m govbudget era-map check | tail -2
```

Expected: `era-map propose: 6927 era keys, 1253 chains; rulings SAME=810 EXCLUDE=46 HISTORY=271; 1 chain(s) for review -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/data/research/era_map`; ` M` for `chains.csv`, `counts.json`, `keys.csv`, `review.csv` and `dbt/seeds/p1_era_code_decisions.csv`; then `O&M|0390D| 2017 2023 same_program 523cd96c7d90 7/7 801553 | A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded exclude_route_unsafe (R-DEC-ERA-EXCLUDE, 2026-10-02) — confirm or keep the seeded decision; no silent overturn`; `0` (the class row left the seed, Q25); `  undecided O&M|0390D| editions 2017,2018,2019,2020,2021,2022,2023 (7 key(s))` and `era-map check: 1 undecided chain(s), 0 stale decision(s)`. Any other review row, or a stale decision, means the lake moved: stop, restore with `git checkout -- data/research/era_map dbt/seeds/p1_era_code_decisions.csv` and report it.

- [ ] **Step 3: Render batch B7 (for its manifest; not published)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python scripts/era/review_batch_page.py render --batch 7
python3 -c "import json; m = json.load(open('tmp/era-review/B7.json')); print(m['chain_ids'], m['labels'], m['actuals_k'], m['undecided_before'], len(m['review_sha256']))"
```

Expected: `B7: 1 chain(s), $801.55M of era actuals -> tmp/era-review/B7.html (manifest tmp/era-review/B7.json); 0 undecided after this batch`, then `['O&M|0390D|'] ['O&M|0390D||2017-2023'] 801553 1 64`. The page (`7 era lines · class A1`) is not published and the owner is not asked: Q3 already put this exact chain, its 7 lines and its $801,553K to the owner on 2026-10-04.

- [ ] **Step 4: Write the owner's answers file**

Create `data/research/era_map/batches/B7.json` (`owner_reply` is the owner's reply verbatim; `decided_on` is the date of that reply; the row names the decision explicitly, so the file reads the same whatever proposal the page showed):

```json
{
  "batch": "B7",
  "decided_on": "2026-10-04",
  "owner_reply": "Join it (Recommended)",
  "owner_acknowledgements": {
    "B7 source": "The owner gave this reply in chat on 2026-10-04 to question Q3 of the families piece-1 follow-ups design: join the era O&M chain O&M|0390D| (PB2017-PB2023, 7 lines, $801,553 thousand of FY2015-FY2021 actuals) to /program/0390DOM/ as owner batch B7, reversing the 2026-10-02 exclude_route_unsafe for this chain. ROADMAP records it in commit 532205c9. The question named the chain, its lines and its dollars, so no batch page was shown."
  },
  "rows": {
    "O&M|0390D|": {"decision": "same_program", "note": "owner B7 (design Q3, 2026-10-04): same_program, the era O&M chain joins /program/0390DOM/; supersedes the 2026-10-02 R-DEC-ERA-EXCLUDE row for this chain"}
  }
}
```

- [ ] **Step 5: Apply the answer to `review.csv`**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python scripts/era/review_batch_page.py answer --batch 7 --answers data/research/era_map/batches/B7.json; echo "exit=$?"
```

Expected: `B7: 1 decided, 0 split into 0 ranges, 0 deferred -> data/research/era_map/review.csv; ratify writes 1 seed row(s): era-map ratify --batch B7 --decided-on 2026-10-04`, `exit=0`. `review_batch_page: ERROR — … changed since batch B7 was rendered …` means something rewrote `review.csv` after Step 3: run Step 3 again, then this step.

- [ ] **Step 6: Ratify B7**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -m govbudget era-map ratify --batch B7 --decided-on 2026-10-04; echo "exit=$?"
uv run --project . python - <<'EOF'
import csv
for r in csv.DictReader(open("dbt/seeds/p1_era_code_decisions.csv", newline="")):
    if r["ruling"] == "R-DEC-ERA-B7":
        print(r["decision_id"], r["decision"], repr(r["program_account"]), repr(r["program_org"]),
              r["n_keys"], r["keys_sha256"][:12], r["proposed_rule"], r["decided_on"], r["decided_by"])
        print(r["evidence"])
EOF
uv run --project . python -m govbudget era-map check | tail -1; echo "exit=$?"
```

Expected: `era-map ratify: 1 decision row(s) added as R-DEC-ERA-B7 -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/dbt/seeds/p1_era_code_decisions.csv`, the line Task 4b added as Task 8 amended it, `era-map ratify: next, ONE build: uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select p1_route_safe_codes p1_era_code_decisions p1_era_line_map fct_program_decade_series (a map-only build fails assert_program_decade_conservation)` (do NOT run it here: Tasks 21 and 22 build, with `stg_budget_lines+` in the same selection, README decision 3), `exit=0`; then `O&M|0390D||2017-2023 same_program '' '' 7 523cd96c7d90 A1 2026-10-04 owner` and `continuity=7/7; actuals_k=801553; proposed=same_program: A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded exclude_route_unsafe (R-DEC-ERA-EXCLUDE, 2026-10-02) — confirm or keep the seeded decision; no silent overturn`; `era-map check: 0 undecided chain(s), 0 stale decision(s)`, `exit=0`. On `era-map ratify: REFUSED — …` (exit 1, seed untouched): `keys_sha256 changed since review` means the lake moved — restore with `git checkout -- data/research/era_map dbt/seeds/p1_era_code_decisions.csv` and start again at Step 1.

- [ ] **Step 7: Rewrite the research files with nothing open**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -m govbudget era-map propose && git diff --stat -- data/research/era_map dbt/seeds && git status --short -- data/research/era_map
python3 -c "import json; c = json.load(open('data/research/era_map/counts.json')); print(c['rulings'], c['owner_batch_chains'], c['review_rows'], c['chain_groups']['unsafe'], c['key_classes']['UNSAFE'], c['ruled_actuals_k']['R-DEC-ERA-EXCLUDE'])"
```

Expected: `era-map propose: 6927 era keys, 1253 chains; rulings SAME=810 EXCLUDE=46 HISTORY=271; 0 chain(s) for review -> …/data/research/era_map`; `git diff --stat` lists `chains.csv | 2 +-`, `counts.json | 18 +++++++++---------`, `keys.csv | 14 +++++++-------`, `dbt/seeds/p1_era_code_decisions.csv | 2 +-` (`4 files changed, 18 insertions(+), 18 deletions(-)`: `review.csv` is back to its header line, as committed); `?? data/research/era_map/batches/B7.json`; then `{'R-DEC-ERA-EXCLUDE': 46, 'R-DEC-ERA-HISTORY': 271, 'R-DEC-ERA-SAME': 810} 126 0 1 7 5030464` (`counts.json` is written with sorted keys). The seed's diff is exactly the O&M row (`exclude_route_unsafe … R-DEC-ERA-EXCLUDE` → `same_program … R-DEC-ERA-B7`); `keys.csv` changes only the 7 `0390D-ARMY-L1` rows (class `UNSAFE` → `A1`, `title_jaccard` 1.00, continuity `7/7`); `chains.csv` only the `O&M|0390D|` row.

- [ ] **Step 8: The map's `decision` description names what is still excluded**

In `dbt/models/marts/schema.yml` (`p1_era_line_map` → `decision`, about line 446), replace:

```yaml
        description: "same_program (points join the code's page) · history_only (era-only code: data, no page — R-DEC-FAM-ERAONLY) · exclude_placeholder (FY2017CR/FY2018CR continuing-resolution lines) · exclude_route_unsafe (0390D O&M / RDT&E) · exclude_reused_code (the code meant a different program in this range) · undecided (no seed row covers the key)."
```

with:

```yaml
        description: "same_program (points join the code's page) · history_only (era-only code: data, no page — R-DEC-FAM-ERAONLY) · exclude_placeholder (FY2017CR/FY2018CR continuing-resolution lines) · exclude_route_unsafe (0390D RDT&E, which restates R-1 PEs 0708081D + 0708083D and has no page key; 0390D's O&M chain joined 0390DOM in owner batch B7, 2026-10-04) · exclude_reused_code (the code meant a different program in this range) · undecided (no seed row covers the key)."
```

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && grep -c 'owner batch B7, 2026-10-04' dbt/models/marts/schema.yml && uv run --project . dbt parse --project-dir dbt --profiles-dir dbt > /dev/null && echo parse-ok
```

Expected: `1`, `parse-ok`.

- [ ] **Step 9: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/data/research/era_map/batches/B7.json GovBudget/data/research/era_map/review.csv GovBudget/data/research/era_map/chains.csv GovBudget/data/research/era_map/keys.csv GovBudget/data/research/era_map/counts.json GovBudget/dbt/seeds/p1_era_code_decisions.csv GovBudget/dbt/models/marts/schema.yml && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era-map): owner batch B7 ratified (R-DEC-ERA-B7): the era O&M chain O&M|0390D| joins 0390DOM; RDT&E stays excluded (#194, design Q3/Q4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `6 files changed` (`review.csv` is unchanged against HEAD, so `git add` stages nothing for it). The live warehouse is untouched; Tasks 21 and 22 rebuild the seed, the map and the program table in one invocation that also selects `p1_route_safe_codes`.
