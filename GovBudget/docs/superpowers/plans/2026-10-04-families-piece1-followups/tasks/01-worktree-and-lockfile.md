<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). -->

### Task 1: Worktree and lockfile (#205); file #207 and #208; the Q7 and Q4 notes on #194 and piece-1 spec §5.2

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6.8 (#205: one lockfile entry, `npm ci`, the build diff, the two stale comments, "decided 2026-10-02 at plan review: /downloads/"), §3.5 (the two adjacent defects filed here as #207 and #208 and closed by Tasks 13 and 14), §2.2 Q7 (the dated correction on ROADMAP #194 and piece-1 spec §5.2) and Q4 (the dated note that the RDT&E line restates R-1 PEs), §1 (#205 lands first).

**Files:**
- Modify: `site/package-lock.json` (the `node_modules/@emnapi/wasi-threads` entry only; anchor on `"node_modules/@emnapi/wasi-threads": {`, about line 990)
- Modify: `site/scripts/gates/build.mjs` (two comment lines; anchor on `decided in Task 19.` about line 693 and on `Task 19 measures the candidate pages and decides.` about line 849)
- Modify: `docs/superpowers/ROADMAP.md` (#194: a dated correction above its Status line, anchor on `(\`_is_valid_pe_bli\` and the section-header skip in \`load_p1_rollup\`).` about line 4869; #207 and #208 after #206's Status line, anchor on `` `src/govbudget/verify_era_map.py`. Effort: days.`` about line 5042)
- Modify: `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md` (§5.2: a dated correction after the `*Owner decision (2026-10-02, implementation plan review; …)*` paragraph, anchor on `record $5.8B").`)
- Test: `tests/test_roadmap_backlog.py` (append at the end of the file)
- Local only, never committed: `site/node_modules` (reinstalled by `npm ci`), `site/out` (rebuilt twice; `site/.gitignore` line 3 ignores it), `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-npmci/` (build logs and chunk digests; `.proofs/` is ignored by `.gitignore` line 22 and the shared exclude)

Line numbers are hints; anchor on the quoted text.

**Interfaces:**
Consumes: the piece-1 harness, unchanged: `scripts/era/env.sh`, the uv `.venv`, the throwaway cluster on `127.0.0.1:55432`, `dbt/target/manifest.json` (196 test nodes), the `data/site` symlink into the live lake.
Produces:
- `site/package-lock.json` that `npm ci` accepts: `node_modules/@emnapi/wasi-threads` at version `1.2.3`, resolved `https://registry.npmjs.org/@emnapi/wasi-threads/-/wasi-threads-1.2.3.tgz`, integrity `sha512-ELEBe8PsLvvJ6QMr0zLt8ffvOHW/dc1m3CEzNMg7aJUv3bMaoDtw2TXyDAwkYBuroxxuHEwhRTLJSe5sya547g==`. Every later task that runs `npm` runs in a tree `npm ci` installed (1,107 packages; `@emnapi/runtime` is no longer installed).
- ROADMAP backlog entries **#207** (subject phrase `Org-split rows get no decade cells`) and **#208** (subject phrase `looks decade cells up by the bare`), each ending `**Status:** open (2026-10-04).`. Task 13 closes #207, Task 14 closes #208, Task 22 stamps both.
- The #194 correction paragraph above #194's `**Status:** open (2026-10-02).` line. #194's Status line itself is unchanged here: `tests/test_roadmap_backlog.py::test_the_families_piece_1_follow_ups_are_filed_once_and_open` still requires it to end the entry until Task 22 closes #194 and updates that test.
- `FOLLOW_UPS_2026_10_04` and `test_the_follow_ups_adjacent_defects_are_filed_once` in `tests/test_roadmap_backlog.py`. The test pins the filing only (once, an effort word, a source pointer), not the open state, so it survives Task 22's closure.

Measured for this task (2026-10-13, read-only, outside :12–:22):
- **The lockfile.** `npm ci --dry-run --ignore-scripts` on a scratch copy of `site/package.json` + `site/package-lock.json` (npm 11.6.2, node v24.13.0) exits with `npm error code EUSAGE` and `Invalid: lock file's @emnapi/wasi-threads@1.2.2 does not satisfy @emnapi/wasi-threads@1.2.3`. With only the `node_modules/@emnapi/wasi-threads` entry changed to 1.2.3 (version, resolved, integrity — `npm view @emnapi/wasi-threads@1.2.3 dist.integrity dist.tarball` gives the two values above), the dry run prints `added 1107 packages`, and a real `npm ci --ignore-scripts --no-audit --no-fund` in the scratch copy installs 1,107 packages whose `node_modules/.package-lock.json` equals the worktree's present one (1,108 entries) minus exactly `node_modules/@emnapi/runtime`, with no version difference. The other two `wasi-threads` entries (line 6094 `^1.2.1` inside `@tailwindcss/oxide-wasm32-wasi`'s bundle list, line 7046 the nested 1.2.1 copy under `@unrs/resolver-binding-wasm32-wasi`) are untouched. `grep -rl @emnapi site/out/_next/static` on the worktree's 2026-10-04 build prints nothing: the bundle never references `@emnapi`.
- **The worktree** today: branch `followups-2026-10-04`, `532205c9` is an ancestor of HEAD; `site/node_modules` is a real directory (735 entries; `next` 16.2.9, `vitest` 3.2.6); `uv run --project . python -c "import govbudget, duckdb, psycopg, pytest; …"` prints `1.5.3 3.3.4 9.0.3`; the cluster answers `andeslee|17.8`; `dbt/target/manifest.json` has 196 test nodes, the same as the live `site_meta.build_checks.dbt_assertions` (196); `data/site` links to the live export; `site/out/_next/static/chunks` holds 49 files.
- **The stale comments.** `site/scripts/gates/build.mjs:693` ends "… without a ceiling raise, decided in Task 19." and `:849` "…; Task 19 measures the candidate pages and decides." The placement was decided on 2026-10-02 at plan review (piece-1 spec §6.4 note, ROADMAP owner-decision table): the era table is on /downloads/.
- **Q7.** Postgres `budget_lines` (read-only psql): `select fiscal_year, exhibit, count(*), min(id), max(id), string_agg(distinct pe_bli, ',') from budget_lines where account='0390D' and pe_bli ~ '[&#/?%[:space:]]' group by 1,2` → `2024|P-1|10|349016|349025|O&M,RDT&E` and `2025|P-1|6|47733|47738|O&M,RDT&E`. The lake's `data/parquet/jbooks/budget_lines.parquet` holds the same 16 (PB2024 O&M 5, RDT&E 5; PB2025 O&M 3, RDT&E 3). `git log -1 481bba08` → 2026-07-05, "fix(audit): … reject junk P-1 BLIs …"; `scripts/clean_junk_pe_bli.py` deletes FY2026 rows only. The era chains, `fct_decade_series` actuals at each key's own edition: "Chem Demilitarization - O&M" 7 keys, 801,553; "Chem Demilitarization - RDT&E" 7 keys, 5,030,464 (sum 5,832,017, the piece-1 §5.2 figure). PB2026's O&M FY2024 actuals 87,404 and the RDT&E line's four PB2026 columns 1,002,560 / 754,762 / 210,039 / 210,039 are the follow-ups design's §4.1 openpyxl reads of `fy2026/dod/p1_display.xlsx` rows 303–304.
- **#207.** `data/site/json/years_matrix.json`: the seven rows with slugs 20-DCSA, 20-DTRA, 30-DMACT, 30-DTRA, 30-OSD, 500-DHRA and 500-DLA carry only `fy_2024_actuals`, `fy_2025_enacted`, `fy_2026_disc_request`, `fy_2026_total` (and 30-OSD `fy_2026_reconciliation_request`) cells and no decade column. `json/program_details/20-DCSA.json` cites FY2024 actuals 2,135 as fid `128936791c3d0741`. `_acct_key` is at `src/govbudget/export_site.py:17760`.
- **#208.** `json/programs.json` has 1,938 rows, 27 of them with a `slug` different from `pe_bli` (the 10 account-collision codes' 20 slugs such as 1350-WPN / 1350-PANMC, and the 7 org-split slugs above). `site/src/app/agency/[org]/page.tsx` reads `decadeCells.get(p.pe_bli)` at lines 91, 92, 115, 361, 364 and 367.
- `tests/test_roadmap_backlog.py`: 30 passed.

- [ ] **Step 1: Check the workspace the plan runs in**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
git -C .. rev-parse --abbrev-ref HEAD
git -C .. merge-base --is-ancestor 532205c9 HEAD && echo has-owner-answers
env | grep '^GOVBUDGET_' | sort
uv run --project . python -c "import govbudget, duckdb, psycopg, pytest; print(duckdb.__version__, psycopg.__version__, pytest.__version__)"
{ test -d site/node_modules && ! test -L site/node_modules; } && echo node-modules-real
lsof -nP -iTCP:55432 -sTCP:LISTEN >/dev/null || LC_ALL=C "$GOVBUDGET_PG_BIN/pg_ctl" -D "$GOVBUDGET_PROOFS/testpg" -l "$GOVBUDGET_PROOFS/testpg.log" -o "-c listen_addresses=127.0.0.1 -c port=55432 -c unix_socket_directories=''" -w start
"$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_TEST_PG_DSN" -Atc "select current_user, split_part(version(), ' ', 2)"
uv run --project . python -c "import json;n=json.load(open('dbt/target/manifest.json'))['nodes'];print(sum(v.get('resource_type')=='test' for v in n.values()))"
readlink data/site
```

Expected, in order: `followups-2026-10-04`; `has-owner-answers`; the six `GOVBUDGET_*` lines (`GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data`, `GOVBUDGET_DUCKDB=…/data/duckdb/govbudget.duckdb`, `GOVBUDGET_PG_BIN=/opt/homebrew/opt/postgresql@17/bin`, `GOVBUDGET_PG_DSN=postgresql://localhost/govbudget`, `GOVBUDGET_PROOFS=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs`, `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres`); `1.5.3 3.3.4 9.0.3`; `node-modules-real`; (pg_ctl prints `server started` only if the cluster was down); `andeslee|17.8`; `196`; `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site`. If the manifest count is not 196, run piece 1's `dbt parse` step (piece-1 Task 1 Step 7) before going on; never copy another checkout's manifest.

- [ ] **Step 2: Show the lockfile failure (red)**

`--dry-run` never touches `node_modules`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npm ci --dry-run --ignore-scripts 2>&1 | grep -E 'EUSAGE|Invalid:'
```

Expected:
```
npm error code EUSAGE
npm error Invalid: lock file's @emnapi/wasi-threads@1.2.2 does not satisfy @emnapi/wasi-threads@1.2.3
```

- [ ] **Step 3: Build once with today's `node_modules` and keep the chunk digests**

The comparison in Step 6 needs a build of the same code and the same `data/site` before the reinstall. The build writes only `site/out`, `site/public` and the logs below.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
mkdir -p "${GOVBUDGET_PROOFS:?}/fu-npmci"
(cd site && npm run build > "$GOVBUDGET_PROOFS/fu-npmci/build-before.log" 2>&1); echo "build exit=$?"
(cd site/out/_next/static/chunks && find . -type f | LC_ALL=C sort | xargs shasum -a 256) > "$GOVBUDGET_PROOFS/fu-npmci/chunks-before.sha256"
wc -l < "$GOVBUDGET_PROOFS/fu-npmci/chunks-before.sha256"
```

Expected: `build exit=0`, then a file count (49 on the 2026-10-04 build; the number itself is not checked, Step 6 compares the two lists).

- [ ] **Step 4: Fix the one lockfile entry**

In `site/package-lock.json`, replace:

```
    "node_modules/@emnapi/wasi-threads": {
      "version": "1.2.2",
      "resolved": "https://registry.npmjs.org/@emnapi/wasi-threads/-/wasi-threads-1.2.2.tgz",
      "integrity": "sha512-c95qOXkHdydNKhscBTebqEC1CVAZpyqOfVfBzQ1qgzyl3gfeldUjIggDbIZgDKsHLgnsM+igH7TJ/eAasaVuMA==",
```

with:

```
    "node_modules/@emnapi/wasi-threads": {
      "version": "1.2.3",
      "resolved": "https://registry.npmjs.org/@emnapi/wasi-threads/-/wasi-threads-1.2.3.tgz",
      "integrity": "sha512-ELEBe8PsLvvJ6QMr0zLt8ffvOHW/dc1m3CEzNMg7aJUv3bMaoDtw2TXyDAwkYBuroxxuHEwhRTLJSe5sya547g==",
```

Nothing else in the file changes (`git diff --stat -- site/package-lock.json` shows `1 file changed, 3 insertions(+), 3 deletions(-)`).

- [ ] **Step 5: Reinstall with `npm ci` (green)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npm ci --no-audit --no-fund 2>&1 | tail -1
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && node -p "Object.keys(require('./node_modules/.package-lock.json').packages).length + ' ' + require('next/package.json').version + ' ' + require('vitest/package.json').version"
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && { test -e node_modules/@emnapi/runtime && echo runtime-present || echo runtime-gone; } && { test -L node_modules && echo symlink || echo real-dir; }
```

Expected: `added 1107 packages in <t>s` (npm may print a `npm warn deprecated uuid@8.3.2` line before it); `1107 16.2.9 3.2.6`; `runtime-gone`; `real-dir`. Any other count, or EUSAGE again: stop and report the npm output; do not commit.

- [ ] **Step 6: Rebuild on the same `data/site` and compare the bundle**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
(cd site && npm run build > "$GOVBUDGET_PROOFS/fu-npmci/build-after.log" 2>&1); echo "build exit=$?"
(cd site/out/_next/static/chunks && find . -type f | LC_ALL=C sort | xargs shasum -a 256) > "$GOVBUDGET_PROOFS/fu-npmci/chunks-after.sha256"
diff "$GOVBUDGET_PROOFS/fu-npmci/chunks-before.sha256" "$GOVBUDGET_PROOFS/fu-npmci/chunks-after.sha256" && echo chunks-identical
grep -rl '@emnapi' site/out/_next/static || echo no-emnapi-in-bundle
```

Expected: `build exit=0`, `chunks-identical`, `no-emnapi-in-bundle`. Only `out/_next/static/<build id>/` (a random build id each build) may differ, which is why the comparison is over `chunks/`. If any chunk differs, stop: keep both lists and both logs under `.proofs/fu-npmci/`, report the differing names, and do not commit.

- [ ] **Step 7: Re-date the two stale gate comments**

In `site/scripts/gates/build.mjs`, replace:

```
  // renders wherever it fits without a ceiling raise, decided in Task 19.
```

with:

```
  // renders wherever it fits without a ceiling raise; decided 2026-10-02 at
  // plan review: /downloads/.
```

and replace:

```
  // raise; Task 19 measures the candidate pages and decides.
```

with:

```
  // raise; decided 2026-10-02 at plan review: /downloads/.
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && grep -c 'decided in Task 19\|Task 19 measures the candidate pages' site/scripts/gates/build.mjs; grep -c 'decided 2026-10-02 at' site/scripts/gates/build.mjs; node --check site/scripts/gates/build.mjs && echo syntax-ok
```

Expected: `0`, `2`, `syntax-ok`.

- [ ] **Step 8: Commit the build hygiene**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/package-lock.json GovBudget/site/scripts/gates/build.mjs && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(site): npm ci accepts the lockfile (@emnapi/wasi-threads 1.2.3); re-date two gate comments (#205)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `2 files changed, 6 insertions(+), 5 deletions(-)`.

- [ ] **Step 9: Write the failing ledger test**

Append to `tests/test_roadmap_backlog.py`, two blank lines after its last line (`        f"#{num} does not end with its open-status line"` and the closing `    )`):

```python


# Families piece-1 follow-ups (docs/superpowers/specs/2026-10-04-families-piece1-
# followups-design.md §3.5) file two adjacent defects in Task 1 and close them in
# release 1 (Tasks 13, 14, 22), so only the filing is pinned here, never the open
# state. Asserted by subject phrase; each phrase sits on one line of its entry.
FOLLOW_UPS_2026_10_04 = [
    "Org-split rows get no decade cells",
    "looks decade cells up by the bare",
]


@pytest.mark.parametrize("subject", FOLLOW_UPS_2026_10_04)
def test_the_follow_ups_adjacent_defects_are_filed_once(subject):
    hits = [(num, body) for num, body in entries() if subject in body]
    assert len(hits) == 1, f"{subject!r} filed {len(hits)} times, want 1"
    num, body = hits[0]
    assert EFFORT_RE.search(body), f"#{num} has no `Effort: hours|days|weeks`"
    assert POINTER_RE.search(body), f"#{num} names no source path"
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_roadmap_backlog.py -q 2>&1 | tail -3
```

Expected: `2 failed, 30 passed`, the failures `AssertionError: 'Org-split rows get no decade cells' filed 0 times, want 1` and `AssertionError: 'looks decade cells up by the bare' filed 0 times, want 1`.

- [ ] **Step 10: File #207 and #208**

In `docs/superpowers/ROADMAP.md`, replace (the end of #206 and the sweep note's first line):

```
  `src/govbudget/verify_era_map.py`. Effort: days.
  **Status:** open (2026-10-04).

*Status markers (one ledger sweep, 2026-08-24).* Every numbered entry below now
```

with:

```
  `src/govbudget/verify_era_map.py`. Effort: days.
  **Status:** open (2026-10-04).

- **#207 Org-split rows get no decade cells on /years/, and /programs/ shows
  "—" for them.** `_emit_years_matrix` (`src/govbudget/export_site.py`) builds
  a row's decade lookup key with `_acct_key`, which keeps the account, so an
  organization-split code's row looks for `('20', '0300D', 'DCSA')`, while its
  decade grains are stored with no account, `('20', None, 'DCSA')`. Seven rows
  lose every decade cell: 20-DCSA, 20-DTRA, 30-DMACT, 30-DTRA, 30-OSD, 500-DHRA
  and 500-DLA (63 modern points today, 147 era points more once #193 lifts the
  era fence). /programs/ then shows "—" for FY24 and FY26 on 20-DCSA, whose own
  page cites FY2024 actuals 2,135 (fid `128936791c3d0741`). Found by the
  families piece-1 follow-ups design (2026-10-04, §3.5); re-measured read-only
  2026-10-13 in `data/site/json/years_matrix.json` (the seven rows carry only
  their PB2026 cells) and `data/site/json/program_details/20-DCSA.json`. Fix:
  key the account on `is_account_split`, as `export_site.py` already does for
  ROADMAP #45, inside #193's work; the /years/ sidecar-parity gate leg proves
  it. Source: `src/govbudget/export_site.py` (`_acct_key` in
  `_emit_years_matrix`). Effort: hours.
  **Status:** open (2026-10-04).

- **#208 /agency/[org]/ looks decade cells up by the bare `pe_bli`, so its
  split-key rows show "—".** `getProgramDecadeCells` keys the cells by
  `slug ?? pe_bli`, but `site/src/app/agency/[org]/page.tsx` (lines 91, 92,
  115, 361, 364, 367) calls `decadeCells.get(p.pe_bli)`. The 27 rows whose
  page slug is not their `pe_bli` (the ten account-collision codes' twenty
  slugs, e.g. 1350-WPN and 1350-PANMC on /agency/N/, and the seven org-split
  slugs of #207) render "—" for FY24 and sort as empty on FY26. Found by the
  families piece-1 follow-ups design (2026-10-04, §3.5); re-measured
  read-only 2026-10-13 (`data/site/json/programs.json`: 1,938 rows, 27 with a
  slug that differs from `pe_bli`). Fix: look up by `slug ?? pe_bli`, inside
  #193's island work. Source: `site/src/app/agency/[org]/page.tsx`,
  `site/src/lib/data.ts` (`getProgramDecadeCells`). Effort: hours.
  **Status:** open (2026-10-04).

*Status markers (one ledger sweep, 2026-08-24).* Every numbered entry below now
```

- [ ] **Step 11: Add the Q7 correction and the Q4 note to #194**

In `docs/superpowers/ROADMAP.md`, replace:

```
  (`_is_valid_pe_bli` and the section-header skip in `load_p1_rollup`).
  Effort: days.
  **Status:** open (2026-10-02).

- **#195 The JLTV continuation sentence is cited to a book that does not
```

with:

```
  (`_is_valid_pe_bli` and the section-header skip in `load_p1_rollup`).
  Effort: days.
  *Correction (2026-10-04, families piece-1 follow-ups design Q7; nothing
  above reworded).* (a) "None of it reaches `budget_lines`" holds for PB2026
  only. Postgres and the lake still hold the PB2024 and PB2025 rows, 16 in
  all (PB2024 ids 349016–349025, PB2025 ids 47733–47738); they reach
  `fct_budget_lines` and the decade tables, though no page or published
  total. PB2026's 8 rows were deleted on 2026-07-05 by
  `scripts/clean_junk_pe_bli.py` (481bba08). (b) The money no page shows is
  the O&M line's only. "Chem Demilitarization - RDT&E" restates R-1 program
  elements 0708081D + 0708083D to the thousand in every edition (PB2026:
  1,002,560 / 754,762 / 210,039 / 210,039), so its dollars are already on those
  two pages. The O&M line's own figures are $87.4M of FY2024 actuals (87,404
  thousand in PB2026), not $1.09B, and $801.6M of FY2015–FY2021 actuals on its
  era chain (801,553 thousand), not $5.83B; the era RDT&E chain carries the
  other 5,030,464 thousand. Measured read-only 2026-10-04 (follow-ups design
  §4.1) and re-measured 2026-10-13 in Postgres `budget_lines`, the lake's
  `budget_lines.parquet` and `fct_decade_series`.
  *Owner (2026-10-04, follow-ups design Q1, Q4).* The RDT&E line gets no page
  and is recorded as an R-1 restatement; its era chain keeps
  `exclude_route_unsafe`, with this note that the line also restates R-1
  PEs. The O&M line loads under the route-safe key `0390DOM` with a page, and
  its era chain joins that page as owner batch B7
  (`docs/superpowers/specs/2026-10-04-families-piece1-followups-design.md` §4).
  **Status:** open (2026-10-02).

- **#195 The JLTV continuation sentence is cited to a book that does not
```

- [ ] **Step 12: Add the dated correction to piece-1 spec §5.2**

In `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md`, replace:

```
*Owner decision (2026-10-02, implementation plan review; nothing above reworded).*
The owner kept the exclusion with the corrected figure recorded ("Keep excluded,
record $5.8B").

### 5.3 Individual decisions (Claude pre-fills, owner approves)
```

with:

```
*Owner decision (2026-10-02, implementation plan review; nothing above reworded).*
The owner kept the exclusion with the corrected figure recorded ("Keep excluded,
record $5.8B").

*Correction (2026-10-04, families piece-1 follow-ups design Q7 and Q4; nothing above
reworded).* Two statements in the 2026-10-02 correction do not hold. (a) PB2024 and
PB2025 do not drop the lines: Postgres and the lake hold their 16 rows (PB2024 10,
PB2025 6); only PB2026's 8 rows are gone, deleted on 2026-07-05 by
`scripts/clean_junk_pe_bli.py`. (b) Of the $5,832,017 thousand, only the O&M chain's
801,553 thousand (FY2015–FY2021 actuals) is money no page shows. The RDT&E line
restates R-1 program elements 0708081D + 0708083D to the thousand, so its 5,030,464
thousand is already on those two pages. The owner then decided (2026-10-04): the O&M
line gets the route-safe page `0390DOM` and its era chain joins that page as owner
batch B7; the RDT&E line gets no page, is recorded as an R-1 restatement, and its era
chain keeps `exclude_route_unsafe`. See
[2026-10-04-families-piece1-followups-design.md](2026-10-04-families-piece1-followups-design.md)
§2.2 and §4.

### 5.3 Individual decisions (Claude pre-fills, owner approves)
```

- [ ] **Step 13: Run the ledger tests (green)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_roadmap_backlog.py -q 2>&1 | tail -1
grep -c '^- \*\*#20[78] ' docs/superpowers/ROADMAP.md
grep -c 'families piece-1 follow-ups design Q7' docs/superpowers/ROADMAP.md docs/superpowers/specs/2026-10-02-era-procurement-history-design.md
```

Expected: `32 passed`; `2`; `docs/superpowers/ROADMAP.md:1` and `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md:1`. `test_the_families_piece_1_follow_ups_are_filed_once_and_open[Chem Demil O&M and RDT&E lines]` still passes because #194's last line is still its `**Status:** open (2026-10-02).`.

- [ ] **Step 14: Commit the ledger**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/docs/superpowers/ROADMAP.md GovBudget/docs/superpowers/specs/2026-10-02-era-procurement-history-design.md GovBudget/tests/test_roadmap_backlog.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(roadmap): file #207 (org-split decade lookup) and #208 (/agency/ slug lookup); dated Q7/Q4 corrections on #194 and piece-1 spec §5.2" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `3 files changed`. `git status --short -- GovBudget` then shows nothing this task created (`site/node_modules`, `site/out`, `site/public` assets and `.proofs/` are ignored).
