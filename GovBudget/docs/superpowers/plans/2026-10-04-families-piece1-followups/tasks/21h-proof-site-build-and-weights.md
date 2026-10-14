<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 21h: Release-1 proof — site build on B@fu-post, the F-15 page snapshot, `npm run verify`, page weights, sitemap

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §5.2 "Re-pin" step 3 (`f15-page-snapshot`, re-pinned in the same step as #201's new prose capture), §3.7 (/years/, /methodology/ and the island chunk re-measured after the whole wave), §4.6 (the 0390DOM page; sitemap 4,349 → 4,350), §5.7 (only `v2/` ships), §7 "Site-side differences", W4 (every gate, page weights re-stamped and never raised), §1 "Weight and prose".

**Files:**
- Modify (re-pinned by `site/scripts/f15-page-snapshot.mjs --out`, schema 1 → 2): `tests/fixtures/f15/page_snapshot.json`
- Modify: `site/scripts/gates/build.mjs` — the `PAGE_WEIGHT_BUDGET` entries of the pages this wave changed, only where the build measures a value other than the entry's `measured` stamp (anchor on each entry's `{ label: "<page>", …` line): `/methodology/`, `/families/f-15/`, `/data/`, `/years/`, `/programs/`, `/agency/*/ (heaviest)`. For each, a `RE-MEASURED` comment goes directly above the entry and only `measured` changes; the ceilings never change.
- Local only: the worktree's `data/{site,duckdb,parquet}` links (pointed at B@fu-post, then back), `site/out/`, `site/public/llms.txt` (rewritten by the build, then restored).

**Interfaces:**
Consumes: Task 21f's `.proofs/fu-post-B`; Task 20c's `site/scripts/f15-page-snapshot.mjs <index.html> [--out FILE | --check FILE]` (`f15-page-snapshot: PASS — equal to FILE`; snapshot schema 2 adds `prose` (`coverage`, `matrix_note`, `notes[]` with `code`, `id`, `fact_id`, `quote`), `matrix.total_header`, `matrix.annual[].partial`, `matrix.rows[].aria_label`) and the F015E0 row `aria-label` (Q21); Tasks 12–15, 17–19's site changes; `site/scripts/gates/build.mjs` `PAGE_WEIGHT_BUDGET` (exported) and gate 1's `weigh()` (zlib level 9, not exported) and `checkPageWeight()` (exported).
Produces: the re-pinned page snapshot; the re-stamped weight entries; logs `$L/site-build.log`, `site-verify.log`, `site-vitest.log`, `weights.txt`, `sitemap-b.txt`, `0390dom-page.txt`, `years-chunks.txt`, `f15-snapshot-diff.txt`.

Measured for this task (2026-10-13, on the worktree's `site/out` built 2026-10-04 at 916ae88e): the weight table below, run on that build, prints every entry; the six entries this task may re-stamp read today `/methodology/` stamp 161,353 / 45,336 (that build: 161,353 / 45,338; ceiling 162,000 / 45,400), `/families/f-15/` 703,427 / 68,538 (ceiling 725,000 / 70,000), `/data/` 85,358 / 14,530 (ceiling 105,000 / 15,600), `/years/` 37,362 / 7,668 (ceiling 45,000 / 9,000), `/programs/` 2,968,731 / 310,063 (ceiling 3,150,000 / 330,000), `/agency/*/ (heaviest)` 1,755,341 / 120,583 on /agency/N/ (ceiling 2,060,000 / 137,000). Two other entries have little headroom and can move with the SAM registrations this export also carries: `/companies/families/` (222 gzip left) and `/company/*/ (heaviest)` (/company/boeing/, 324 left). On that build `/years/` loads 15 script chunks, 890,636 raw / 271,283 gzip (Step 6's measurement). The live sitemap has 4,349 `<loc>` lines and no `/program/0390DOM/`; live `/program/0390DOM/` answers 404. `tests/fixtures/f15/page_snapshot.json` keys: `schema, page, data_fact_id_elements, data_fact_ids, data_dataset_counts, family_f15_occurrences, page_fact_id_occurrences, page_fact_ids, matrix` (`matrix.rows[]` by `program_id`; the F015E0 row's `label` is `["BLI F015E0", "F-15e (FY2020 F-15EX Lot 1 aircraft)", "Procurement · Historical code", "Note below"]`). The design measured T9's weight on /families/f-15/ as +68 raw / +36 gzip by substitution; with the amended gloss, the `aria-label` and the matrix-note hook, Task 20c measured +194 raw / +67 gzip (703,621 / 68,605, 1,395 gzip left; G3 notes C6); Task 19 measured /methodology/'s T7 strings at +16 raw / −13 gzip, and Task 15's Q13 swap at 0 raw. The F-15 page snapshot is schema 1 today; Task 20c's tool writes schema 2, and its vitest "committed baseline … of this schema" stays red until Step 3 re-pins it.

- [ ] **Step 1: Point the worktree's lake links at B@fu-post**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; BAD=0; for d in site duckdb parquet; do if [ -e "data/$d" ] && [ ! -L "data/$d" ]; then echo "STOP: data/$d is a real directory"; BAD=1; fi; done; [ "$BAD" = 0 ] && for d in site duckdb parquet; do ln -sfn "$P/fu-post-B/$d" "data/$d"; done; ls -l data | grep -- '->'
```
Expected: `data/{site,duckdb,parquet} -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-post-B/{site,duckdb,parquet}` and the unchanged `raw` and `raw_docs` links.

- [ ] **Step 2: Build the site on B@fu-post (production origin)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs" && cd site
NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > "$L/site-build.log" 2>&1; echo "build exit=$?"
ls out/json/years_matrix.json out/json/years_matrix/decade.json out/json/years_matrix/detail.json; ls out/json/budget-pdf-receipts; ls out/json/budget-pdf-receipts/v2 | wc -l
F=$(uv run --project .. python -c "import duckdb; print(duckdb.connect().execute(\"select fact_id from read_parquet('../data/site/data/budget_lines.parquet') where pe_bli = '0390DOM' and amount_type = 'fy_2026_total'\").fetchone()[0])")
H=out/program/0390DOM/index.html; { echo "fy2026 total fid $F: $(grep -c "data-fact-id=\"$F\"" "$H")"; echo "address sentence: $(grep -c 'its address uses 0390DOM' "$H")"; echo "printed code O&amp;M: $(grep -c 'O&amp;M' "$H")"; echo "restated R-1 links: $(grep -o 'href="/program/070808[13]D/"' "$H" | sort -u | tr '\n' ' ')"; } | tee "$L/0390dom-page.txt"
grep -o '<loc>[^<]*</loc>' out/sitemap.xml | sort > "$L/sitemap-b.txt"; curl -s https://fiscalreceipts.com/sitemap.xml | grep -o '<loc>[^<]*</loc>' | sort > "$L/sitemap-live.txt"; wc -l < "$L/sitemap-b.txt"; diff "$L/sitemap-live.txt" "$L/sitemap-b.txt"
```
Expected: `build exit=0`; the three /years/ files; `v2` alone (Task 17); `4096`; `fy2026 total fid <16 hex>: <n ≥ 1>`, `address sentence: <n ≥ 1>` (Q5's "… its address uses 0390DOM because a web address cannot carry “&”."), `printed code O&amp;M: <n ≥ 1>`, `restated R-1 links: href="/program/0708081D/" href="/program/0708083D/"`; `4350`; and a diff of exactly one added line, `> <loc>https://fiscalreceipts.com/program/0390DOM/</loc>` (if production was redeployed after 916ae88e, compare against that deploy's URL list instead).

- [ ] **Step 3: P3.4 — the F-15 page snapshot: only the gloss, the aria-label and the new captures**

The committed snapshot is the pre-wave page. Every value it holds must hold on the new page, except the F015E0 row's label (where the `aria-label` work, Q21, may change what the row header reads); the new page may add the captures Task 20's tool now takes:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs" && cd site
node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --out "$L/page_snapshot.new.json"; echo "snapshot exit=$?"
uv run --project .. python - ../tests/fixtures/f15/page_snapshot.json "$L/page_snapshot.new.json" <<'PY' | tee "$L/f15-snapshot-diff.txt"
import json, sys
old, new = (json.load(open(p)) for p in sys.argv[1:3])
F015E0 = "P-1:3010F:AF:F015E0"
problems = []
def held(a, b, at):
    """Every value `a` holds is in `b` unchanged; `b` may hold more keys."""
    if isinstance(a, dict):
        if not isinstance(b, dict):
            problems.append(at); return
        for k, v in a.items():
            if k not in b:
                problems.append((*at, k))
            else:
                held(v, b[k], (*at, k))
    elif isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            problems.append(at); return
        for i, (x, y) in enumerate(zip(a, b)):
            held(x, y, (*at, i))
    elif a != b:
        problems.append(at)
held({k: v for k, v in old.items() if k not in ("matrix", "schema")}, new, ())
held({k: v for k, v in old["matrix"].items() if k != "rows"}, new["matrix"], ("matrix",))
rows = {r["program_id"]: r for r in new["matrix"]["rows"]}
label = None
for r in old["matrix"]["rows"]:
    if r["program_id"] not in rows:
        problems.append(("matrix", "rows", r["program_id"])); continue
    skip = {"label"} if r["program_id"] == F015E0 else set()
    held({k: v for k, v in r.items() if k not in skip}, rows[r["program_id"]], ("matrix", "rows", r["program_id"]))
    if skip:
        label = (r["label"], rows[r["program_id"]]["label"])
print("old values the new page changed or lost:", problems)
print("F015E0 row label, old -> new:", label)
print("schema:", old.get("schema"), "->", new.get("schema"))
print("captures only the new snapshot has:", sorted(set(new) - set(old)))
print("F015E0 aria_label:", rows.get(F015E0, {}).get("aria_label"))
note = json.dumps(new)
print("gloss captured:", "[the PB2026 F-15EX AP (F015EX) P-40]" in note)
PY
```
Expected: `snapshot exit=0`; `old values the new page changed or lost: []` (every schema-1 value holds on the new page; Task 20c's schema 2 only adds `prose`, `matrix.total_header`, `matrix.annual[].partial` and `matrix.rows[].aria_label`); the F015E0 label pair (equal, or differing only as Task 20c's header change defines); `schema: 1 -> 2`; `captures only the new snapshot has: ['prose']`; `F015E0 aria_label: BLI F015E0 F-15e (FY2020 F-15EX Lot 1 aircraft) Procurement · Historical code` (Q21's accessible name, Task 20c); `gloss captured: True` (the `prose.notes[].quote` capture reads the note). Any entry in the first list: stop — the F-15 page moved outside the approved gloss and accessibility fix. Then re-pin and check:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --out ../tests/fixtures/f15/page_snapshot.json && node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check ../tests/fixtures/f15/page_snapshot.json
```
Expected: `f15-page-snapshot: PASS — equal to ../tests/fixtures/f15/page_snapshot.json`.

- [ ] **Step 4: Page weights — measure every entry, re-stamp the pages this wave changed**

The table is gate 1's measurement (`weigh()`: the file's bytes and `zlib.gzipSync(…, {level: 9})`; a templated directory's heaviest `index.html` by raw size):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs" && cd site
node --input-type=module -e '
import fs from "fs"; import path from "path"; import zlib from "zlib";
const { PAGE_WEIGHT_BUDGET } = await import("./scripts/gates/build.mjs");
const out = "out";
const weigh = (p) => { const b = fs.readFileSync(p); return { raw: b.length, gzip: zlib.gzipSync(b, { level: 9 }).length }; };
const target = (e) => { if (e.file) return path.join(out, e.file); let w = null; for (const s of fs.readdirSync(path.join(out, e.dir))) { const p = path.join(out, e.dir, s, "index.html"); try { const st = fs.statSync(p); if (st.isFile() && (!w || st.size > w.size)) w = { size: st.size, p }; } catch {} } return w.p; };
const fmt = (n) => n.toLocaleString("en-US");
for (const e of PAGE_WEIGHT_BUDGET) {
  const t = target(e); const { raw, gzip } = weigh(t);
  const m = /^\s*([\d,]+)\s*\/\s*([\d,]+)/.exec(e.measured ?? ""); const stamp = m ? `${m[1]} / ${m[2]}` : e.measured;
  const moved = m ? (Number(m[1].replace(/,/g, "")) !== raw || Number(m[2].replace(/,/g, "")) !== gzip) : true;
  const over = raw > e.maxRaw || gzip > e.maxGzip;
  console.log(`${e.label} | stamp ${stamp} | now ${fmt(raw)} / ${fmt(gzip)} [${path.relative(out, t)}] | left ${fmt(e.maxRaw - raw)} / ${fmt(e.maxGzip - gzip)}${moved ? " | MOVED" : ""}${over ? " | OVER CEILING" : ""}`);
}' | tee "$L/weights.txt"
```
Expected: one line per entry (18 today), none ending `OVER CEILING`. An `OVER CEILING` line is a stop: take it to the owner (a trim, never a raise; design §1). If it is `/company/*/ (heaviest)` or `/companies/families/`, say that the SAM registrations stored since 2026-10-04 ship with this export too.

For each of `/methodology/`, `/families/f-15/`, `/data/`, `/years/`, `/programs/` and `/agency/*/ (heaviest)` whose line says `MOVED`, edit its entry in `site/scripts/gates/build.mjs`: keep every comment line above it verbatim, add these comment lines directly above the `{ label: … }` line, and change only the `measured` string (the old stamp, today's date, the B short sha from `$L/shas.txt` line 2, the new pair, and the ceiling minus the new pair). Today `/methodology/`'s entry reads:

```js
  // program page" at the sentence's same 312 bytes; build of ea1c4071 on the
  // S5 proof export with datasets.json's two fixed scopes; gate 1's weigh(),
  // zlib level 9): 161,353 / 45,339 -> 161,353 / 45,336. CEILINGS UNCHANGED;
  // 647 raw / 64 gzip left.
  { label: "/methodology/", file: "methodology/index.html", maxRaw: 162_000, maxGzip: 45_400, measured: "161,353 / 45,336" },
```
and becomes (an earlier task of this wave may have re-stamped it already: then its own last comment and `measured` string are what you keep and replace):

```js
  // program page" at the sentence's same 312 bytes; build of ea1c4071 on the
  // S5 proof export with datasets.json's two fixed scopes; gate 1's weigh(),
  // zlib level 9): 161,353 / 45,339 -> 161,353 / 45,336. CEILINGS UNCHANGED;
  // 647 raw / 64 gzip left.
  // RE-MEASURED <YYYY-MM-DD> (Task 21h, the follow-ups release-1 proof build of
  // <B short sha> on B@fu-post: T7, Q13 and the dbt assertion count; gate 1's
  // weigh(), zlib level 9): 161,353 / 45,336 -> <raw> / <gzip>. CEILINGS
  // UNCHANGED; <162,000 − raw> raw / <45,400 − gzip> gzip left.
  { label: "/methodology/", file: "methodology/index.html", maxRaw: 162_000, maxGzip: 45_400, measured: "<raw> / <gzip>" },
```
The other five take the same four comment lines with their own reason — `/families/f-15/`: "the F015E0 gloss and row aria-label (#206 T9, Q17, Q21)"; `/data/`: "the p1_era_line_map decided_on column (#206 T6) and its amended scope (Q3)"; `/years/`: "the sharded island and the Q14 legend (#193)"; `/programs/`: "the seven org-split rows' FY24/FY26 cells (#207)"; `/agency/*/ (heaviest)`: "the slug lookup for split-key rows (#208)" — and their own ceilings (725,000 / 70,000; 105,000 / 15,600; 45,000 / 9,000; 3,150,000 / 330,000; 2,060,000 / 137,000). `/agency/*/ (heaviest)`'s `measured` keeps its page in parentheses: `"<raw> / <gzip> (/agency/<org>/)"`. Do not touch any other entry unless gate 1's drift leg fires on it in Step 5 (then re-stamp it the same way, naming "per-build drift" as the reason). Then:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && node --input-type=module -e 'import("./scripts/gates/build.mjs").then(({checkPageWeight}) => { const r = checkPageWeight(); console.log(r.errors.length); for (const e of r.errors) console.log(e); })' && git -C ../.. diff --stat -- GovBudget/site/scripts/gates/build.mjs
```
Expected: `0`, and the diff stat of the entries you re-stamped. Then prove no ceiling moved — every changed entry line differs from its old self only in `measured`:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git diff -U0 -- GovBudget/site/scripts/gates/build.mjs | grep -E '^[-+] +\{ label:' | sed -E 's/^[-+]//; s/measured: "[^"]*"//' | sort | uniq -u | wc -l
```
Expected: `0`.

- [ ] **Step 5: `npm run verify` and vitest on the B@fu-post build**

Port 4173 must be free (no other session running verify):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs" && cd site
NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > "$L/site-verify.log" 2>&1; echo "verify exit=$?"; grep -E "^gate |^  gate |^overall:" "$L/site-verify.log" | tail -40
npm test > "$L/site-vitest.log" 2>&1; echo "vitest exit=$?"; grep -E "Test Files|Tests " "$L/site-vitest.log" | tail -2
```
Expected: `verify exit=0`, every gate `PASS` — among them the years-matrix gate with legs a–j, the per-file and core budgets and the live leg that sees only the core fetched on load (Task 15), linkgraph with its floor of 6 static fetch targets, program-skeleton, datatruth (leg s recounts the era table: B7 moves its counts), family-history, copy (the T7 allowlist entry removed), build (the v2-only leg, page weights) — last line `overall: PASS`; `vitest exit=0` (Task 20c's committed-baseline test passes on the schema-2 snapshot Step 3 wrote). If verify fails only with a page-weight drift message (recorded headroom more than twice the real one, no ceiling error), re-stamp that entry as Step 4 says and re-run this step; any other failure is a stop.

- [ ] **Step 6: The /years/ island chunk, for the record (design §3.7)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && L=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs && node -e 'const fs=require("fs"),z=require("zlib");const h=fs.readFileSync("out/years/index.html","utf8");const c=[...new Set([...h.matchAll(/\/_next\/static\/chunks\/[^"\x27 ]+\.js/g)].map(m=>m[0]))];let r=0,g=0;for(const p of c){const b=fs.readFileSync("out"+p);r+=b.length;g+=z.gzipSync(b,{level:9}).length}console.log(`/years/ scripts: ${c.length} chunks, ${r.toLocaleString("en-US")} raw / ${g.toLocaleString("en-US")} gzip`)' | tee "$L/years-chunks.txt"
```
Expected: one line `/years/ scripts: <k> chunks, <raw> raw / <gzip> gzip` (no ceiling applies; the proof note records it beside the HTML weight and the pre-wave 15 chunks, 890,636 / 271,283).

- [ ] **Step 7: Commit the page snapshot and the weight stamps**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/tests/fixtures/f15/page_snapshot.json GovBudget/site/scripts/gates/build.mjs && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(site): re-pin the F-15 page snapshot and re-measure the pages the follow-ups release 1 changed, on the proof build of B@fu-post; ceilings unchanged" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: the commit (`2 files changed`, or `1 file changed` if no weight entry moved).

- [ ] **Step 8: Put the links and `llms.txt` back**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
git checkout -- site/public/llms.txt && for d in site duckdb parquet; do ln -sfn "/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/$d" "data/$d"; done && ls -l data | grep -- '->' && git -C .. status --porcelain -- GovBudget | grep -v '^??'; echo "clean check done"
```
Expected: the five links point at `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/…`, no tracked change, `clean check done` (the release commits its own `llms.txt` in Task 22d).
