<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the README's Contract Notes, section G6, hold this group's contract notes. -->

### Task 25c: Release-2 proof — gates on B, the `--revert` rehearsal, the site build and weights, the proof note

**Spec:** §7 (W3–W6 on the proven state), §5.6 (the full-population check; the heaviest program page measured, never a raised ceiling), §2.3 Q24 (b) for release 2 (the revert has its own rehearsal), §8 (release 2's go-ahead names the re-measured weight of the heaviest program page). Depends on Task 25b.
**Files:**
- Modify: `site/scripts/gates/build.mjs` — the `/program/*/ (heaviest)` entry of `PAGE_WEIGHT_BUDGET` (line 860–864 today: four comment lines and the entry; anchor on `{ label: "/program/*/ (heaviest)"`)
- Modify: `docs/superpowers/ROADMAP.md` — a new first entry under `## Findings log (what we learned; feeds future phases)` (line 270 today)
- Modify, only if Step 1 measures fewer `opening_only` or `opening_seen` citations than the ceilings: `src/govbudget/verify_jbook_narratives.py` (`OPENING_ONLY_CEILING = 111`, `PAGELESS_OPENING_SEEN_CEILING = 77`, and `test_the_ceilings_are_the_measured_counts` in `tests/jbooks/test_verify_jbook_narratives.py`), lowered to the measured counts, never raised

**Interfaces:**
Consumes: Task 25b's `.proofs/fu2*` clones, scratch database and `fu2-logs/` records; `govbudget verify-jbook-narratives` (Task 24), `verify-phase5b1` (gate 5), `verify-lineage`, `verify-phase5e`, `verify-era-map`; `govbudget link-coverage --site-dir DIR --baseline FILE` and the baseline Task 22 left committed in `data/research/link_coverage/baseline.json`; `tests/fixtures/f15/history.sha256` as Task 21 re-pinned it (#206 T9); `scripts/fu/s195_narratives.py --revert`.
Produces: the proven site tree `.proofs/fu2-Bpost/site` (Task 26a diffs the release export against it), the re-stamped page-weight entry, the proof note. Task 26 reads `fu2-logs/digest-pre.txt`, `digest-mid.txt`, `digest-post.txt` and `noise-fu2.json`.

**Measured now:** Task 23c Step 7 estimated `/program/0601102A/` at 1,171,692 raw / 147,566 gzip after the relocation (from 1,157,481 / 145,454 on the 916ae88e build), inside 1,180,000 / 151,000; the build below is the measurement. Gate 1's stamp-drift leg reads only the gzip headroom (`build.mjs` "ANNOTATION-DRIFT LEG"): the stamped 5,397 left against about 3,434 real is under 2x, so the stale stamp would not fail verify — the entry is re-stamped because the page moved, as piece 1 Task 21 did.

- [ ] **Step 1: The printed-in check on both B exports**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
for d in fu2-Bpost fu2-B; do (source "$P/fu2/env.sh" "$P/$d" && uv run --project . python -m govbudget verify-jbook-narratives --site-dir "$GOVBUDGET_DATA/site" --pg-dsn "$GOVBUDGET_PG_DSN") > "$P/fu2-logs/vjn-$d.txt" 2>&1; echo "$d exit=$?"; head -1 "$P/fu2-logs/vjn-$d.txt"; tail -1 "$P/fu2-logs/vjn-$d.txt"; done
```
Expected:

```
fu2-Bpost exit=0
narrative citations 11717: paged 10273 (printed 10162, opening_only 111 of at most 111); pageless 1444 (opening printed without its closing 77 of at most 77, opening printed nowhere 1367)
verify-jbook-narratives: PASS
fu2-B exit=1
narrative citations 11717: paged 6096 (printed 5757, opening_only 339 of at most 111); pageless 5621 (opening printed without its closing 77 of at most 77, opening printed nowhere 1367)
verify-jbook-narratives: FAIL
```
(The check reads the book sets from the scratch database, which Task 25b Step 6 changed only in `provenance_pages`; the book sets live in `jbook_documents`. The same gate is red on the export before the relocation and green after it — the design's "red before, green after" for this item.) The ceilings are met exactly. If B shows fewer `opening_only` or `opening_seen` citations, lower the two constants and the pinning test to the new counts and commit them on their own (`fix(verify): ratchet the #195 ceilings to the release-2 proof's counts`) before Task 26 — a ratchet only tightens; more than the ceilings fails the step, and the owner decides.

- [ ] **Step 2: Python gates on B (W3, W5)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
for gate in verify-phase5b1 verify-lineage verify-phase5e verify-era-map; do (source "$P/fu2/env.sh" "$P/fu2-Bpost" && uv run --project . python -m govbudget ${gate}) > "$P/fu2-logs/${gate}.log" 2>&1; echo "${gate} exit=$?"; tail -1 "$P/fu2-logs/${gate}.log"; done; grep -A1 '^gate 5 narrative printed-in' "$P/fu2-logs/verify-phase5b1.log"
```
Expected: four `exit=0` with `verify-phase5b1: PASS`, `verify-lineage: PASS`, `verify-phase5e: PASS`, `verify-era-map: PASS`; then `gate 5 narrative printed-in: → PASS` and the Step 1 count line, indented. verify-lineage passes unchanged because fact IDs still hash the attached document (§5.6 point 2); its leg (g) reads the rail's fact ID and sentence, and the rail pages now equal the citations' (Task 23b).

- [ ] **Step 3: F-15 pin and link coverage (W6)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
H=$(shasum -a 256 "$P/fu2-Bpost/site/json/f15_funding_history.json" | cut -d' ' -f1); if [ -n "$H" ] && [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ]; then echo "F-15 history matches the pin"; else echo "F-15 history DOES NOT match the pin (got ${H:-nothing}) — stop"; fi
uv run --project . python -m govbudget link-coverage --site-dir "$P/fu2-Bpost/site" --baseline data/research/link_coverage/baseline.json > "$P/fu2-logs/link-coverage.txt" 2>&1; echo "link-coverage exit=$?"; tail -4 "$P/fu2-logs/link-coverage.txt"
```
Expected: `F-15 history matches the pin` (the F015E0 note receipt `e7d5bcfb4a30f458` did not move, Task 25b Step 10); `link-coverage exit=0` with release 1's source-linked and PDF-highlighted percentages unchanged — narrative rows are not budget figures (`link_coverage.py` docstring), so #195 cannot move them.

- [ ] **Step 4: Rehearse the abort path's `--revert` on the scratch database**

Task 26a's abort path restores the live rows with this command (Q24 (b), applied to release 2). On the scratch database it must restore every relocated row exactly and the pre-write digest D1, and leave the 19 lineage-evidence rows, which piece-1-era code already cites correctly (Task 25b Step 6: none names another volume).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
(source "$P/fu2/env.sh" && uv run --project . python scripts/fu/s195_narratives.py --revert --pre-image "$P/fu2-logs/rehearsal-s195-pre-image.json" && uv run --project . python scripts/fu/s195_narratives.py --digest && "$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_PG_DSN" -Atc "select count(*), count(printed_document_sha256) from provenance_pages where target_kind = 'narrative' and id > $(cat "$P/fu2-logs/max-id-before.txt")") > "$P/fu2-logs/scratch-revert.log" 2>&1; echo "exit=$?"; cat "$P/fu2-logs/scratch-revert.log"; echo "D1=$(cat "$P/fu2-logs/digest-mid.txt")"
```
Expected: `exit=0`; `reverted 4386 row(s); digest <D1> equals the pre-image's`; `state digest: <D1>` (the same value as the `D1=` line); `19|0`. Then re-apply, so the scratch database again matches the exported state Task 26a compares with (the second apply is a fresh pre-image of the same D1 state; it must print the same D2):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
(source "$P/fu2/env.sh" && uv run --project . python scripts/fu/s195_narratives.py --apply --pre-image "$P/fu2-logs/rehearsal-s195-pre-image-2.json" --expect-pre-digest "$(cat "$P/fu2-logs/digest-mid.txt")") > "$P/fu2-logs/scratch-s195-reapply.log" 2>&1; echo "exit=$?"; grep -o 'post-write digest: [0-9a-f]*' "$P/fu2-logs/scratch-s195-reapply.log"; echo "D2=$(cat "$P/fu2-logs/digest-post.txt")"
```
Expected: `exit=0` and `post-write digest: <D2>` equal to the `D2=` line: the relocation is deterministic, which is what lets Task 26a hold the live write to D2.

- [ ] **Step 5: Build and verify the site on B; weigh the program pages**

Point the worktree's data links at B (refusing a real directory), build, verify, weigh, then point them back. Port 4173 must be free (no other session running verify).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs; BAD=0; for d in site duckdb parquet; do if [ -e "data/$d" ] && [ ! -L "data/$d" ]; then echo "STOP: data/$d is a real directory"; BAD=1; fi; done; [ "$BAD" = 0 ] && for d in site duckdb parquet; do ln -sfn "$P/fu2-Bpost/$d" "data/$d"; done; ls -l data | grep -- '->'
cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > "$P/fu2-logs/site-build.log" 2>&1; echo "build exit=$?"; NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > "$P/fu2-logs/site-verify.log" 2>&1; echo "verify exit=$?"; grep -E "^overall:|program/\*/ \(heaviest\)" "$P/fu2-logs/site-verify.log" | tail -4
node -e 'const fs=require("fs"),z=require("zlib");let w=null;for(const s of fs.readdirSync("out/program")){const p=`out/program/${s}/index.html`;if(!fs.existsSync(p))continue;const n=fs.statSync(p).size;if(!w||n>w.n)w={s,n,p}}const b=fs.readFileSync(w.p);console.log(w.s+" "+b.length.toLocaleString("en-US")+" / "+z.gzipSync(b,{level:9}).length.toLocaleString("en-US"))'
```
Expected: three symlinks `data/{site,duckdb,parquet} -> …/.proofs/fu2-Bpost/…`; `build exit=0`; `verify exit=0`, `overall: PASS` (every gate, the clickthrough PDF panel among them: the superseded volumes are in `data/site/pdfs`, which `serve-static.mjs` serves); then the heaviest program page, `0601102A <raw> / <gzip>`, about `1,171,692 / 147,566` (Task 23c Step 7's estimate; release 1's own changes to that page move it a little). Over `1,180,000` raw or `151,000` gzip: stop and take it to the owner — never raise a ceiling (spec §5.6). If verify fails only with a page-weight stamp-drift message, re-stamp below and re-run verify; any other failure: stop.

In `site/scripts/gates/build.mjs`, the entry today reads (if Task 21 re-stamped it, its comment lines stand as Task 21 left them and are kept verbatim the same way):

```js
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 1,111,532 / 142,888 -> 1,157,926 / 145,603. CEILINGS UNCHANGED;
  // 22,074 raw / 5,397 gzip left.
  { label: "/program/*/ (heaviest)", dir: "program", maxRaw: 1_180_000, maxGzip: 151_000, measured: "1,157,926 / 145,603 (/program/0601102A/)" },
```

Replace it with the same four comment lines, four new ones and the new `measured` string (today's date, B's short sha from `fu2-logs/b_sha.txt`, the printed numbers; the headroom is the ceiling minus the measurement):

```js
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 1,111,532 / 142,888 -> 1,157,926 / 145,603. CEILINGS UNCHANGED;
  // 22,074 raw / 5,397 gzip left.
  // RE-MEASURED <YYYY-MM-DD> (Task 25c, the release-2 proof build of <B short
  // sha>: #195 gives the page's narrative citations their printing pages;
  // gate 1's weigh(), zlib level 9): <previous measured> -> <raw> / <gzip>.
  // CEILINGS UNCHANGED; <1,180,000 − raw> raw / <151,000 − gzip> gzip left.
  { label: "/program/*/ (heaviest)", dir: "program", maxRaw: 1_180_000, maxGzip: 151_000, measured: "<raw> / <gzip> (/program/0601102A/)" },
```
(`<previous measured>` is the entry's `measured` numbers as they stood, `1,157,926 / 145,603` unless Task 21 re-stamped it.) Then check the entry and restore the links:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && node --input-type=module -e 'import("./scripts/gates/build.mjs").then(({checkPageWeight})=>{const r=checkPageWeight();console.log(r.errors.filter(e=>/program\/\*/.test(e)).length)})' && cd .. && git checkout -- site/public/llms.txt && for d in site duckdb parquet; do ln -sfn "/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/$d" "data/$d"; done && git -C .. status --porcelain -- GovBudget | grep -v '^??'; echo "links restored"
```
Expected: `0`; then only ` M GovBudget/site/scripts/gates/build.mjs`; `links restored`. (The build rewrote `llms.txt` from B's export; Task 26a commits the release's own.)

- [ ] **Step 6: Record the proof in the ROADMAP**

Insert as the first entry under `## Findings log (what we learned; feeds future phases)` in `docs/superpowers/ROADMAP.md`, filling every `<…>` from the files named in brackets (under `.proofs/fu2-logs/`):

```markdown
- **<YYYY-MM-DD>: Families piece-1 follow-ups, release-2 proof (#195) — the
  narrative relocation on one snapshot.** Snapshot `.proofs/fu2`
  (`govbudget proof snapshot`, <created_at>; DuckDB <duckdb_sha256_at_copy> at copy;
  site <site_sha256>; raw_docs <raw_docs_sha256>; Postgres dump <pg_dump_sha256>
  restored as `govbudget_proof_fu2`) [snapshot-shas.json]. Migration 022 on the
  scratch database left its state digest at the live value <D0> [digest-pre.txt].
  P2: the code at `<A short sha>` (release 1, proved equal to the deployed
  <live short sha>) and at `<B short sha>` exported the migrated database
  identically (`proof diff: EQUAL`) [diff-p2.txt]. The rehearsed writes, in the
  release's order: `jbooks narrative-provenance --lineage-evidence` built the 19
  lineage-evidence narrative rows that never had one (all in their own volume),
  digest <D1>; `scripts/fu/s195_narratives.py --apply` relocated 4,386 rows
  (located 4,158, relocated 228; kept 5,776; opening_only 111; unresolved
  1,444), digest <D2> [scratch-s195-apply.log]. P1 passed the release-2 rule
  list (`expected-diff-r2-narratives.json`) [diff-p1.txt]; field by field, 4,177
  narrative citations gained a page and 228 moved, none changed outside the
  location fields, 20 superseded PB2026 volumes (162,040,168 B) became hosted,
  the F015E0 note receipt stayed on Vol I p.71, the JLTV continuation sentence
  (#195's case) now cites the BA1 book p.100 and the F-15EX example
  033016199ca94aa7 Vol II p.215 [relocation-report.json]. verify-jbook-narratives:
  FAIL before (339 opening-only, 4,177 pageless narratives a volume locates),
  PASS after (10,162 printed, 111 opening-only, 1,444 pageless: 77 whose opening
  alone is printed, 1,367 printed nowhere) [vjn-*.txt]; verify-phase5b1 (gate 5
  included), verify-lineage, verify-phase5e, verify-era-map PASS; the F-15 history
  matches its pin; link coverage unchanged. `--revert` restored 4,386 rows and
  digest <D1> on the scratch database and left the 19 new rows; a second apply
  reproduced <D2> [scratch-revert.log, scratch-s195-reapply.log]. Site build of
  <B short sha> on the proven export: `npm run verify` overall PASS;
  `/program/0601102A/` <raw> / <gzip> against 1,180,000 / 151,000 (ceilings
  unchanged).
```

- [ ] **Step 7: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/scripts/gates/build.mjs GovBudget/docs/superpowers/ROADMAP.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(roadmap): release-2 proof (#195) — P2 equal, P1 within the rule list, the relocation and its revert rehearsed; /program/*/ re-measured, ceilings unchanged" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: the commit (`2 files changed`). Keep the A worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fu2-proof-a` (README: A worktrees are removed on the owner's yes only; Task 26b Step 8 offers it), and keep `.proofs/fu2`, `fu2-A`, `fu2-B`, `fu2-Bpost`, `fu2-B2post`, `fu2-logs` and the `govbudget_proof_fu2` database: Task 26a diffs the release export against `fu2-Bpost/site`, reads the digests and the noise file, and Task 26b asks the owner before removing any of them.
