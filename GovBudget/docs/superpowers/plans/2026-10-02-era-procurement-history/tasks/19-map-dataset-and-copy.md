<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 19: Map dataset registration, era summary JSON and its table, methodology sentence

**Spec:** §4.4 (dataset registration, uncited ledger, `json/era_map_summary.json`); §6.2 `/methodology/` fence; §6.4
(copy: methodology sentence at equal length, per-edition table, datatruth leg, `corpus.ts` comment); §7 (an undecided
era key is never exported); V7 (era completeness reported per edition); V8 (datatruth: map dataset card, Explorer
entry, era summary table; page weight, no ceiling raised); S4. The owner decision and contract issues 2, 4 and 6 above
apply: the table's page and its counts-only content depart from §4.4/§6.4/§10; the owner approved both at plan review
(Step 19) and the plan commit already holds the dated spec corrections and the ROADMAP sentence (Step 20 only checks).
This task edits neither the spec nor the ROADMAP.

**Files:**
- Create: `site/scripts/computed-style-snapshot.mjs`
- Create: `site/src/app/data/data.module.css`
- Modify: `site/src/app/data/page.tsx:1-14` (imports), `:143-152` (table), `:173-231` (rows)
- Modify: `site/src/app/methodology/page.tsx:1767-1775` (the PB2024-boundary sentence, Part A), `:1025-1028` (the
  pending-ledger clause, Part C Step 22, after the owner's yes)
- Modify: `site/src/lib/corpus.ts:187-196` (comment only)
- Modify: `site/scripts/gates/build.mjs:372` (`/data/` stamp + note), `:647` (`/methodology/` stamp + note)
- Test: `site/src/__tests__/data-inventory-hoist.test.ts`, `site/src/__tests__/methodology-era-sentence.test.ts`
- Modify: `src/govbudget/export_site.py:1753-1758` (scope), after `:2186` (new constants and two functions), `:2584-2590` (wiring)
- Modify: `src/govbudget/cli.py:2471-2480` (`_export_budget_pdf_evidence`)
- Test: `tests/test_export_era_line_map.py`, `tests/test_era_map_summary.py`, `tests/test_budget_pdf_export_workflow.py` (append), `tests/jbooks/test_export_site_pg.py` (append)
- Modify: `site/src/lib/dataset-names.ts:18-35`, `site/src/components/explorer.tsx:163-165`, `site/src/lib/data.ts:29-30` and after `:764`, `site/src/app/downloads/page.tsx:3`, `:73`, `:143-144`, `site/src/components/download-cards.tsx` (imports, props, the card grid: the era table renders inside it)
- Create: `site/src/lib/era-map.ts`, `site/src/components/era-map-table.tsx`, `site/scripts/gates/eramap-recompute.py`
- Modify: `site/scripts/gates/datatruth.mjs:213-214` (header), `:776-779` (wiring), end of file (leg s)
- Test: `site/src/__tests__/methodology-pending-ledger.test.ts`, `site/src/__tests__/duckdb-helpers.test.ts:119-149`, `site/src/__tests__/explorer-era-map-preset.test.ts`, `tests/test_explorer_era_map_preset.py`, `site/src/__tests__/era-map-table.test.tsx`, `site/scripts/gates/__tests__/era-map-leg.test.mjs`

Line numbers cited in this task are hints (anchor on the quoted text; line numbers are approximate): earlier tasks shift them.

**Interfaces:**
Consumes: Task 1 (worktree `uv sync`, `site/node_modules` via `npm ci`, Playwright chromium, the `data/site` link of
contract issue 6, `GOVBUDGET_TEST_PG_DSN` cluster); Task 5 (`/methodology/` stamp re-measured at S0); Task 10
(`govbudget.jbooks.era_map.DECISIONS`); Task 13 (`p1_era_line_map` in the warehouse); Task 15 (no undecided row, for
Step 17's real-data check); Task 17 (era leaves cited with `pe_bli = line_item_code`, which the scope sentence states).
Produces: `_DATASET_SCOPES["p1_era_line_map"]`; `ERA_MAP_DATASET = "p1_era_line_map"`,
`ERA_MAP_SUMMARY_FILE = "era_map_summary.json"`, `ERA_MAP_EDITIONS = tuple(range(2017, 2024))`;
`_export_p1_era_line_map(con, data_dir: Path) -> int | None`; `write_era_map_summary(*, site_dir: Path, duckdb_path:
Path) -> dict | None` (all in `export_site.py`); `data/p1_era_line_map.parquet` and `json/era_map_summary.json`
(schema below) in every `export-site` CLI run; `DATASET_NAMES` gains `"p1_era_line_map"`; `cannedQueriesFor
("p1_era_line_map")`; `site/src/lib/era-map.ts` (`ERA_DECISIONS`, `ERA_EXCLUDED`, `ERA_MAP_COLUMNS`, `eraMapCells`,
types `EraMapSummary`, `EraMapEdition`, `EraMapTally`); `getEraMapSummary(): EraMapSummary | null` in
`site/src/lib/data.ts`; `<EraMapTable summary>` rendered on `/downloads/` by `<DownloadCards eraMap>` as the
`sm:col-span-2` grid item directly after the `[data-dataset-card="p1_era_line_map"]` card (`section#era-map`,
`[data-era-map]`, `tr[data-era-edition]`, `[data-era-cell] [data-era-value]`; spec §6.4 owner decision: "directly under
the `p1_era_line_map` download card"); every download card carries `data-dataset-card="<name>"`; gate 24 leg (s) `runEraMapLeg(errors, notes, injected?)`
exported from `site/scripts/gates/datatruth.mjs`; `site/scripts/gates/eramap-recompute.py`;
`site/scripts/computed-style-snapshot.mjs` (`--route/--selector/--out/--port`, `--diff A B`). Handoff to Task 21 in
contract issue 6.

`json/era_map_summary.json` schema (schema_version 1):
`{"schema_version": 1, "actuals_basis": str, "receipts_basis": str, "editions": [{"edition": int, "fy_actuals": int,
"lines": int, "by_decision": {<each of DECISIONS>: {"chains": int, "lines": int, "actuals_thousands": float}},
"receipts": {"facts": int, "complete": int}}] (exactly 2017..2023, in order), "by_ruling": [{"ruling": str,
"decision": str, "chains": int, "lines": int, "actuals_thousands": float}] (sorted by ruling, decision),
"totals": {<decision>: {"chains", "lines", "actuals_thousands"}}}`. A chain is one `decision_id`; per edition it counts
the decision rows covering at least one of that edition's lines.

#### Part A — make room on `/data/`, swap the methodology sentence (builds against today's data)

Part A must land before Part C: once `DATASET_NAMES` names `p1_era_line_map`, the site no longer builds against the
pre-S4 export.

- [ ] **Step 1: Check the build preconditions**

Run (from the worktree `GovBudget/`):
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
test -f data/site/json/datasets.json && test -f dbt/target/manifest.json && test -f data-seeds/gao_program_xwalk.csv && test ! -L site/node_modules && test -d site/node_modules/next && test -d site/node_modules/playwright && echo ready
python3 -c "import json;print(len(json.load(open('data/site/json/datasets.json'))['datasets']))"
```
Expected: `ready`, then `16`. If either fails, Task 1's setup (contract issue 6) is missing; stop. Two traps,
reproduced 2026-10-02 on a scratch copy: `node_modules` must be a real directory (Turbopack fails a symlinked one with
`Symlink [project]/node_modules is invalid, it points out of the filesystem root`); `dbt/target/manifest.json` must
exist in THIS checkout (`site/src/lib/data.ts:650`; without it every loader throws and the build stops at
`Page "/district/[district]" is missing "generateStaticParams()"`). It is written by Tasks 13/16's `govbudget build`
run from this worktree; never copy another checkout's (#173: /methodology/ prints its dbt-assertion count).

- [ ] **Step 2: Create the computed-style snapshot tool**

Create `site/scripts/computed-style-snapshot.mjs`:
```js
#!/usr/bin/env node
/**
 * computed-style-snapshot.mjs — proof that a utility-class hoist changes no
 * computed style (families piece 1, Task 19; /coverage/ did the same check by
 * hand for coverage.module.css, see that file's header).
 *
 * Serves out/ (serve-static.mjs), opens one route and records, for every
 * element under one selector, its bounding box and every standard computed
 * property (custom properties skipped), in eight states — 390×844 and
 * 1440×900, light and dark, screen and print — plus the first body row's
 * :hover state at 1440×900 light screen.
 *
 *   node scripts/computed-style-snapshot.mjs --route /data/ \
 *     --selector "#dataset-inventory table" --out /abs/before.json [--port 4191]
 *   node scripts/computed-style-snapshot.mjs --diff /abs/before.json /abs/after.json
 *
 * --diff prints up to 50 differences and "computed-style diff: N difference(s)",
 * exiting 1 when N > 0.
 */
import fs from "fs";
import { chromium } from "playwright";
import { startServer } from "./serve-static.mjs";

const VIEWPORTS = [{ width: 390, height: 844 }, { width: 1440, height: 900 }];
const SCHEMES = ["light", "dark"];
const MEDIA = ["screen", "print"];

function arg(name) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : undefined;
}

/** Runs in the page. Self-contained: Playwright serialises its source. */
function collect(selector) {
  const root = document.querySelector(selector);
  if (!root) throw new Error(`no element matches ${selector}`);
  return [root, ...root.querySelectorAll("*")].map((el) => {
    const cs = getComputedStyle(el);
    const props = {};
    for (let i = 0; i < cs.length; i++) {
      const p = cs[i];
      if (!p.startsWith("--")) props[p] = cs.getPropertyValue(p);
    }
    const r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      box: [r.x, r.y, r.width, r.height].map((v) => Math.round(v * 100) / 100),
      props,
    };
  });
}

async function snapshot(route, selector, port) {
  const server = await startServer(port);
  const browser = await chromium.launch();
  const out = {};
  try {
    for (const viewport of VIEWPORTS) {
      for (const colorScheme of SCHEMES) {
        for (const media of MEDIA) {
          const page = await browser.newPage({ viewport });
          await page.emulateMedia({ colorScheme, media });
          await page.goto(`${server.url}${route}`, { waitUntil: "load" });
          const key = `${viewport.width}x${viewport.height}/${colorScheme}/${media}`;
          out[key] = await page.evaluate(collect, selector);
          if (viewport.width === 1440 && colorScheme === "light" && media === "screen") {
            await page.locator(`${selector} tbody tr`).first().hover();
            await page.waitForTimeout(1000);
            out[`${key}/hover`] = await page.evaluate(collect, `${selector} tbody tr`);
          }
          await page.close();
        }
      }
    }
  } finally {
    await browser.close();
    await server.close();
  }
  return out;
}

function diff(a, b) {
  const A = JSON.parse(fs.readFileSync(a, "utf8"));
  const B = JSON.parse(fs.readFileSync(b, "utf8"));
  const lines = [];
  for (const key of new Set([...Object.keys(A), ...Object.keys(B)])) {
    const x = A[key];
    const y = B[key];
    if (!x || !y) {
      lines.push(`${key}: present in one snapshot only`);
      continue;
    }
    if (x.length !== y.length) {
      lines.push(`${key}: ${x.length} elements vs ${y.length}`);
      continue;
    }
    x.forEach((e, i) => {
      const f = y[i];
      if (e.tag !== f.tag) lines.push(`${key} #${i}: <${e.tag}> vs <${f.tag}>`);
      if (e.box.join() !== f.box.join()) lines.push(`${key} #${i} <${e.tag}> box ${e.box} -> ${f.box}`);
      for (const p of new Set([...Object.keys(e.props), ...Object.keys(f.props)])) {
        if (e.props[p] !== f.props[p]) {
          lines.push(`${key} #${i} <${e.tag}> ${p}: ${e.props[p]} -> ${f.props[p]}`);
        }
      }
    });
  }
  return lines;
}

if (process.argv.includes("--diff")) {
  const i = process.argv.indexOf("--diff");
  const lines = diff(process.argv[i + 1], process.argv[i + 2]);
  for (const l of lines.slice(0, 50)) console.log(l);
  console.log(`computed-style diff: ${lines.length} difference(s)`);
  process.exit(lines.length === 0 ? 0 : 1);
} else {
  const route = arg("--route");
  const selector = arg("--selector");
  const outPath = arg("--out");
  const port = Number(arg("--port") ?? 4191);
  if (!route || !selector || !outPath) {
    console.error("usage: --route /path/ --selector CSS --out /abs/file.json [--port N] | --diff A B");
    process.exit(2);
  }
  const snap = await snapshot(route, selector, port);
  fs.writeFileSync(outPath, JSON.stringify(snap));
  const n = Object.values(snap).reduce((s, els) => s + els.length, 0);
  console.log(`computed-style snapshot: ${Object.keys(snap).length} states, ${n} elements -> ${outPath}`);
}
```

- [ ] **Step 3: Baseline build, snapshot and weights (before any page change)**

Run:
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
mkdir -p /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t19-data-hoist
cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build
node scripts/computed-style-snapshot.mjs --route /data/ --selector "#dataset-inventory table" \
  --out /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t19-data-hoist/before.json --port 4191
node -e 'const fs=require("fs"),z=require("zlib");for(const f of ["data","methodology"]){const b=fs.readFileSync(`out/${f}/index.html`);console.log(f,b.length,z.gzipSync(b,{level:9}).length)}' \
  | tee /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t19-data-hoist/weights-before.txt
cd .. && git checkout -- site/public/llms.txt
```
The build runs at the production origin, the origin Task 5 measured its `/methodology/` stamp at, so every stamp
Step 11 writes compares like with like (a build without `NEXT_PUBLIC_SITE_URL` bakes in
`https://govbudget-placeholder.example`; measured 2026-10-02, both pages then weigh 220 raw / 30 to 35 gzip more).
Expected:
the build succeeds (about 20 minutes, almost all of it `generate-og.mjs`);
`computed-style snapshot: 9 states, 1362 elements -> …/before.json` (16 inventory rows); weights
`data 101696 15555` and `methodology 161166 45269` (a production-origin scratch build of this commit on 2026-10-02's
data: raw equals production exactly, gzip may move by up to ~10 bytes with the per-build ID). With the production
origin the regenerated `site/public/llms.txt` equals the committed one; the checkout is a guard in case the export
moved.

- [ ] **Step 4: Write the failing pins for the hoist and the sentence**

Create `site/src/__tests__/data-inventory-hoist.test.ts`:
```ts
/**
 * /data/ inventory rows carry no per-row utility strings (families piece 1,
 * Task 19). They live in src/app/data/data.module.css, selected by the hooks
 * already on each cell, because the page ships each row twice (HTML + RSC)
 * and p1_era_line_map's row did not fit the 42 gzip bytes the page had left.
 * A string put back on a row is weight put back on every row.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "data", "page.tsx");
const CSS = path.resolve(__dirname, "..", "app", "data", "data.module.css");

const HOISTED = [
  "block sm:table-row border-b border-border last:border-0 hover:bg-muted/30 transition-colors py-3 sm:py-0",
  "t-id block sm:table-cell px-4 py-0 sm:py-2 sm:whitespace-nowrap",
  "inline sm:table-cell px-4 py-0 sm:py-2 text-left sm:text-right tabular-nums text-xs sm:text-sm text-muted-foreground",
  "inline sm:table-cell pr-4 sm:px-4 py-0 sm:py-2 text-left sm:text-right tabular-nums text-xs sm:text-sm text-muted-foreground whitespace-nowrap",
  "inline sm:table-cell px-4 py-0 sm:py-2 text-xs",
  "block sm:table-cell px-4 pt-1 sm:py-2 text-muted-foreground sm:max-w-sm",
];

describe("/data/ inventory rows: utilities hoisted into data.module.css", () => {
  const src = fs.readFileSync(PAGE, "utf8");

  it.each(HOISTED)("page.tsx no longer carries %s", (cls) => {
    expect(src).not.toContain(`"${cls}"`);
  });

  it("the inventory table takes the module class", () => {
    expect(src).toContain('import styles from "./data.module.css";');
    expect(src).toContain("className={`min-w-full text-sm ${styles.inv}`}");
  });

  it("the name cell keeps t-id for the type spec", () => {
    expect(src).toContain('<td role="cell" className="t-id">');
  });

  it("the module styles every cell the rows used to style inline", () => {
    const css = fs.readFileSync(CSS, "utf8");
    for (const sel of [
      ".inv > tbody > tr {",
      ".inv > tbody > tr:last-child {",
      ".inv > tbody > tr:hover {",
      ".inv > tbody > tr > td:first-child {",
      ".inv > tbody > tr > td:nth-child(2),",
      ".inv > tbody > tr > td:nth-child(3) {",
      '.inv [data-primary-value="citation"] {',
      '.inv [data-primary-value="scope"] {',
      "@media (width >= 40rem) {",
    ]) {
      expect(css).toContain(sel);
    }
  });
});
```

Create `site/src/__tests__/methodology-era-sentence.test.ts`:
```ts
/**
 * /methodology/'s "Two honest gaps" paragraph, first gap (families piece 1,
 * spec 2026-10-02 §6.4). The sentence said cross-edition procurement
 * comparisons stop at the PB2024 boundary. Era procurement lines now join a
 * program only through a dated, reviewed decision on the code each P-1
 * printed, and the rest stay data only, so the sentence states that gap, at
 * the replaced sentence's exact rendered byte length: /methodology/ sits near
 * its gate-1 ceiling and only the link markup is new. It must still read as
 * a gap (it opens "Two honest gaps remain"), not as a new capability.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "methodology", "page.tsx");

/** The replaced sentence as rendered (312 UTF-8 bytes). */
const OLD_SENTENCE =
  "First, cross-edition procurement comparisons stop at the PB2024 boundary: PB2017–PB2023 procurement lines are keyed within their own edition (the underlying account/line identity is unstable across those years), so book diffs for the era editions cover RDT&E only — a wrong lineage would be worse than a gap.";

/** Rendered text of the JSX between two markers: {" "} is a space, tags drop,
 *  whitespace collapses, &amp; is &. */
function visible(start: string, end: string): string {
  const src = fs.readFileSync(PAGE, "utf8");
  const a = src.indexOf(start);
  const b = src.indexOf(end, a + start.length);
  expect(a, `marker not found: ${start}`).toBeGreaterThan(-1);
  expect(b, `marker not found: ${end}`).toBeGreaterThan(a);
  return src
    .slice(a, b)
    .replaceAll('{" "}', " ")
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .replaceAll("&amp;", "&")
    .trim();
}

describe("/methodology/ era procurement sentence", () => {
  const sentence = visible("Two honest gaps remain. First,", "Second, program elements").replace(
    /^Two honest gaps remain\. /,
    "",
  );

  it("states the gap: era procurement joins a program only by a reviewed decision on the printed code", () => {
    expect(sentence).toContain(
      "PB2017–PB2023 procurement lines join a program only by a dated, reviewed decision on the code their P-1 printed, never by title",
    );
    expect(sentence).toContain("(renames too; published in p1_era_line_map)");
    expect(sentence).toContain("the rest stay data only");
  });

  it("keeps the two statements that stay true", () => {
    expect(sentence).toContain("book diffs for the era editions still cover RDT&E only");
    expect(visible("Second, program elements", "</p>")).toContain(
      "never fuzzy-matches renamed programs across editions",
    );
  });

  it("no longer says comparisons stop at the PB2024 boundary", () => {
    expect(sentence).not.toContain("PB2024 boundary");
  });

  it("is exactly as long as the sentence it replaced", () => {
    expect(Buffer.byteLength(OLD_SENTENCE)).toBe(312);
    expect(Buffer.byteLength(sentence)).toBe(312);
  });

  it("links the map dataset the way the page's other dataset link does", () => {
    const src = fs.readFileSync(PAGE, "utf8");
    expect(src).toContain('<a href="/data/" className="underline hover:text-foreground">p1_era_line_map</a>);');
  });
});
```

Run:
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/data-inventory-hoist.test.ts src/__tests__/methodology-era-sentence.test.ts
```
Expected: FAIL, `Tests  13 failed | 1 passed (14)`. The hoist file fails all 9 cases (the six `page.tsx no longer
carries …`, the module class, `t-id` alone on the name cell, and the CSS case with `ENOENT: no such file or directory …
data.module.css`); the sentence file fails 4 of 5 ("states the gap", "keeps the two statements" on `still cover`, "no
longer says", "links"). Only the length case passes: the old sentence is also 312 bytes.

- [ ] **Step 5: Create `site/src/app/data/data.module.css`**

```css
/* ── The /data/ dataset inventory's row and cell styling, hoisted (gate 1) ──
   Families piece 1 (spec 2026-10-02 §4.4, Task 19) adds a seventeenth
   dataset, p1_era_line_map, to a page that had 42 gzip bytes of headroom
   (live 2026-10-01: 101,696 / 15,558 against 105,000 / 15,600). One more
   row costs more than that, and the ceiling is not raised. Every inventory
   row carried the same utility strings on the <tr> and all five cells, and
   the page ships each row twice (HTML and the RSC payload). Hoisting them
   here, the move coverage.module.css made for /coverage/, weighed −19,948
   raw / −2,038 gzip on production-origin builds against 2026-10-02's data
   (101,696 / 15,555 -> 81,748 / 13,517) with no rendered character changed.

   Each rule names the utility list it replaces and declares what that list
   compiles to (Tailwind 4, the site's built stylesheet), so every computed
   style is unchanged: scripts/computed-style-snapshot.mjs compares every
   element of the table at 390×844 and 1440×900, light and dark, screen and
   print, and the row :hover state. Cells are selected by the hooks already
   on them (data attributes) or by column position; the name cell keeps
   `t-id` for the type spec. Unlayered rules beat the utilities layer, and
   nothing else styles these cells, so these rules win exactly where the
   utilities did. */

/* <tr>: block sm:table-row border-b border-border last:border-0
   hover:bg-muted/30 transition-colors py-3 sm:py-0 */
.inv > tbody > tr {
  display: block;
  border-bottom-style: solid;
  border-bottom-width: 1px;
  border-color: var(--border);
  padding-block: calc(var(--spacing) * 3);
  transition-property: color, background-color, border-color, outline-color,
    text-decoration-color, fill, stroke, --tw-gradient-from, --tw-gradient-via,
    --tw-gradient-to;
  transition-timing-function: var(--tw-ease, var(--ease-standard));
  transition-duration: var(--tw-duration, var(--motion-fast));
}
.inv > tbody > tr:last-child {
  border-style: solid;
  border-width: 0;
}
@media (hover: hover) {
  .inv > tbody > tr:hover {
    background-color: var(--muted);
  }
  @supports (color: color-mix(in lab, red, red)) {
    .inv > tbody > tr:hover {
      background-color: color-mix(in oklab, var(--muted) 30%, transparent);
    }
  }
}

/* name <td> (keeps t-id): block sm:table-cell px-4 py-0 sm:py-2
   sm:whitespace-nowrap */
.inv > tbody > tr > td:first-child {
  display: block;
  padding-inline: calc(var(--spacing) * 4);
  padding-block: calc(var(--spacing) * 0);
}

/* rows <td>: inline sm:table-cell px-4 py-0 sm:py-2 text-left sm:text-right
   tabular-nums text-xs sm:text-sm text-muted-foreground
   size <td>: the same with pr-4 sm:px-4 in place of px-4, plus
   whitespace-nowrap */
.inv > tbody > tr > td:nth-child(2),
.inv > tbody > tr > td:nth-child(3) {
  display: inline;
  padding-block: calc(var(--spacing) * 0);
  text-align: left;
  --tw-numeric-spacing: tabular-nums;
  font-variant-numeric: var(--tw-ordinal,) var(--tw-slashed-zero,)
    var(--tw-numeric-figure,) var(--tw-numeric-spacing,)
    var(--tw-numeric-fraction,);
  font-size: var(--text-xs);
  line-height: var(--tw-leading, var(--text-xs--line-height));
  color: var(--muted-foreground);
}
.inv > tbody > tr > td:nth-child(2) {
  padding-inline: calc(var(--spacing) * 4);
}
.inv > tbody > tr > td:nth-child(3) {
  padding-right: calc(var(--spacing) * 4);
  white-space: nowrap;
}

/* citation <td>: inline sm:table-cell px-4 py-0 sm:py-2 text-xs */
.inv [data-primary-value="citation"] {
  display: inline;
  padding-inline: calc(var(--spacing) * 4);
  padding-block: calc(var(--spacing) * 0);
  font-size: var(--text-xs);
  line-height: var(--tw-leading, var(--text-xs--line-height));
}

/* scope <td>: block sm:table-cell px-4 pt-1 sm:py-2 text-muted-foreground
   sm:max-w-sm */
.inv [data-primary-value="scope"] {
  display: block;
  padding-inline: calc(var(--spacing) * 4);
  padding-top: calc(var(--spacing) * 1);
  color: var(--muted-foreground);
}

/* The `sm:` halves, on the same selectors as the rules they override. */
@media (width >= 40rem) {
  .inv > tbody > tr {
    display: table-row;
    padding-block: calc(var(--spacing) * 0);
  }
  .inv > tbody > tr > td:first-child {
    display: table-cell;
    padding-block: calc(var(--spacing) * 2);
    white-space: nowrap;
  }
  .inv > tbody > tr > td:nth-child(2),
  .inv > tbody > tr > td:nth-child(3) {
    display: table-cell;
    padding-block: calc(var(--spacing) * 2);
    text-align: right;
    font-size: var(--text-sm);
    line-height: var(--tw-leading, var(--text-sm--line-height));
  }
  .inv > tbody > tr > td:nth-child(3) {
    padding-inline: calc(var(--spacing) * 4);
  }
  .inv [data-primary-value="citation"] {
    display: table-cell;
    padding-block: calc(var(--spacing) * 2);
  }
  .inv [data-primary-value="scope"] {
    display: table-cell;
    padding-block: calc(var(--spacing) * 2);
    max-width: var(--container-sm);
  }
}
```

- [ ] **Step 6: Use the module in `site/src/app/data/page.tsx`**

Imports, before (`:12-14`):
```tsx
// Universal module (NOT lib/duckdb, which is "use client" — its runtime
// exports become client references in a server component).
import { DATASET_NAMES, type DatasetName } from "@/lib/dataset-names";
```
After:
```tsx
// Universal module (NOT lib/duckdb, which is "use client" — its runtime
// exports become client references in a server component).
import { DATASET_NAMES, type DatasetName } from "@/lib/dataset-names";

import styles from "./data.module.css";
```

Table, before (`:150-152`):
```tsx
            the header semantics are untouched. */}
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="min-w-full text-sm">
```
After:
```tsx
            the header semantics are untouched.
            FAMILIES PIECE 1 (Task 19): the rows' and cells' utility strings
            live in data.module.css (`.inv`), selected by the hooks below.
            They used to ride on every row twice (HTML + RSC payload); the
            hoist paid for p1_era_line_map's row on a page with 42 gzip bytes
            left. src/__tests__/data-inventory-hoist.test.ts pins it. */}
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className={`min-w-full text-sm ${styles.inv}`}>
```

Rows, before (`:176-228`, from `<tr` to the scope `</td>`):
```tsx
                  <tr
                    key={ds.name}
                    data-dataset-card={ds.name}
                    role="row"
                    className="block sm:table-row border-b border-border last:border-0 hover:bg-muted/30 transition-colors py-3 sm:py-0"
                  >
                    <td role="cell" className="t-id block sm:table-cell px-4 py-0 sm:py-2 sm:whitespace-nowrap">
                      {ds.name}
                    </td>
                    {/* [data-dataset-rowcount] wraps the NUMERALS ONLY — gate
                        24 leg b parses its text as an integer against the
                        shipped parquet, so the mobile "rows" word rides
                        outside it. */}
                    <td
                      role="cell"
                      className="inline sm:table-cell px-4 py-0 sm:py-2 text-left sm:text-right tabular-nums text-xs sm:text-sm text-muted-foreground"
                    >
                      <span data-dataset-rowcount>
                        {ds.row_count.toLocaleString("en-US")}
                      </span>
                      <span className="sm:hidden"> rows</span>
                    </td>
                    <td role="cell" className="inline sm:table-cell pr-4 sm:px-4 py-0 sm:py-2 text-left sm:text-right tabular-nums text-xs sm:text-sm text-muted-foreground whitespace-nowrap">
                      <span className="sm:hidden" aria-hidden="true">
                        ·{" "}
                      </span>
                      {formatBytes(ds.bytes)}
                    </td>
                    {/* data-primary-value marks the two columns that were
                        entirely off-canvas at 390px before the card treatment
                        (backlog #31) — gate 3's mobile leg measures both. */}
                    <td
                      role="cell"
                      data-primary-value="citation"
                      className="inline sm:table-cell px-4 py-0 sm:py-2 text-xs"
                    >
```
and (`:222-228`)
```tsx
                    <td
                      role="cell"
                      data-primary-value="scope"
                      className="block sm:table-cell px-4 pt-1 sm:py-2 text-muted-foreground sm:max-w-sm"
                    >
                      {ds.scope}
                    </td>
```
After (the badge `<span>`s between them are unchanged):
```tsx
                  <tr
                    key={ds.name}
                    data-dataset-card={ds.name}
                    role="row"
                  >
                    <td role="cell" className="t-id">
                      {ds.name}
                    </td>
                    {/* [data-dataset-rowcount] wraps the NUMERALS ONLY — gate
                        24 leg b parses its text as an integer against the
                        shipped parquet, so the mobile "rows" word rides
                        outside it. */}
                    <td role="cell">
                      <span data-dataset-rowcount>
                        {ds.row_count.toLocaleString("en-US")}
                      </span>
                      <span className="sm:hidden"> rows</span>
                    </td>
                    <td role="cell">
                      <span className="sm:hidden" aria-hidden="true">
                        ·{" "}
                      </span>
                      {formatBytes(ds.bytes)}
                    </td>
                    {/* data-primary-value marks the two columns that were
                        entirely off-canvas at 390px before the card treatment
                        (backlog #31) — gate 3's mobile leg measures both. */}
                    <td role="cell" data-primary-value="citation">
```
and
```tsx
                    <td role="cell" data-primary-value="scope">
                      {ds.scope}
                    </td>
```

- [ ] **Step 7: Swap the methodology sentence**

In `site/src/app/methodology/page.tsx`, before (`:1767-1775`):
```tsx
                <p className="mt-2">
                  Two honest gaps remain. First, cross-edition{" "}
                  <em>procurement</em>{" "}
                  comparisons stop at the PB2024 boundary:
                  PB2017–PB2023 procurement lines are keyed within their own
                  edition (the underlying account/line identity is unstable
                  across those years), so book diffs for the era editions cover
                  RDT&amp;E only — a wrong lineage would be worse than a gap.
                  Second, program elements absent from an edition render as gaps
```
After:
```tsx
                <p className="mt-2">
                  {/* Families piece 1 (spec 2026-10-02 §6.4): this sentence
                      said cross-edition procurement comparisons stopped at the
                      PB2024 boundary. Era procurement lines now join a program
                      only through a dated, reviewed decision on the code each
                      P-1 printed (published in p1_era_line_map); the rest stay
                      data only. The sentence states that gap instead, at the
                      old one's exact rendered length (312 bytes):
                      /methodology/ sits near its gate-1 ceiling and only the
                      link markup is new.
                      src/__tests__/methodology-era-sentence.test.ts pins it. */}
                  Two honest gaps remain. First, PB2017–PB2023{" "}
                  <em>procurement</em>{" "}
                  lines join a program only by a dated, reviewed decision on
                  the code their P-1 printed, never by title (renames too;
                  published in{" "}
                  <a href="/data/" className="underline hover:text-foreground">p1_era_line_map</a>);
                  the rest stay data only, and book diffs for the era editions
                  still cover RDT&amp;E only — a wrong lineage would be worse
                  than a gap.
                  Second, program elements absent from an edition render as gaps
```
Rendered, the new first gap reads: "First, PB2017–PB2023 *procurement* lines join a program only by a dated, reviewed
decision on the code their P-1 printed, never by title (renames too; published in p1_era_line_map); the rest stay data
only, and book diffs for the era editions still cover RDT&E only — a wrong lineage would be worse than a gap." It names
two limits (the lines without a same-program decision stay data only; era book diffs are still RDT&E only), so it
reads as the gap the paragraph announces, and it carries the spec §6.4 content: era procurement history through
reviewed decisions on the printed code, renames as decisions, the map dataset linked. Both sentences are 312 rendered
bytes (measured with the test's own normalization). Weighed on production-origin builds against 2026-10-02's data
(Steps 3 and 10): +188 raw / +61 gzip (161,166 / 45,269 → 161,354 / 45,330 against 162,000 / 45,400; 70 gzip
bytes left).

- [ ] **Step 8: Correct the `corpus.ts` comment (comment only; the visible string stays true)**

In `site/src/lib/corpus.ts`, before (`:192-196`):
```ts
      // whose history is CITED (a positive fct_decade_series grain). The
      // rest are era P-1 display line numbers, which are workbook rows
      // rather than program identities, and reserve-component P-1R rows,
      // whose money is already inside the P-1 line. The sentence names the
      // two universes it unions instead of claiming all of them.
```
After:
```ts
      // whose history is CITED (a positive fct_decade_series grain). The
      // rest are era P-1 display line numbers, which are workbook rows
      // rather than program identities, and reserve-component P-1R rows,
      // whose money is already inside the P-1 line. Families piece 1
      // (2026-10-02) keeps that: an era line still gets no page of its own;
      // its figures reach an existing page only through a reviewed decision
      // on the code it printed (p1_era_line_map), so this count and the
      // sentence below do not change. The sentence names the two universes
      // it unions instead of claiming all of them.
```

- [ ] **Step 9: Run the pins**

Run:
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/data-inventory-hoist.test.ts src/__tests__/methodology-era-sentence.test.ts
```
Expected: `Test Files  2 passed (2)`, `Tests  14 passed (14)`.

- [ ] **Step 10: Rebuild, prove no computed style moved, weigh**

Run:
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npx next build && node scripts/write-build-meta.mjs
node scripts/computed-style-snapshot.mjs --route /data/ --selector "#dataset-inventory table" \
  --out /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t19-data-hoist/after.json --port 4191
node scripts/computed-style-snapshot.mjs --diff \
  /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t19-data-hoist/before.json \
  /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t19-data-hoist/after.json
node -e 'const fs=require("fs"),z=require("zlib");for(const f of ["data","methodology"]){const b=fs.readFileSync(`out/${f}/index.html`);console.log(f,b.length,z.gzipSync(b,{level:9}).length)}' \
  | tee /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t19-data-hoist/weights-after.txt
grep -c 'First, PB2017–PB2023<!-- --> <em>procurement</em> <!-- -->lines join a program only by a dated, reviewed decision' out/methodology/index.html
grep -c 'published in<!-- --> <a href="/data/" class="underline hover:text-foreground">p1_era_line_map</a>); the rest stay data only' out/methodology/index.html
grep -c 'block sm:table-row border-b' out/data/index.html
cd .. && git checkout -- site/public/llms.txt
```
`npx next build` (about a minute) is enough here: Part A changes no input of the prebuild steps, whose outputs from Step
3 are still in `public/`. It must run at the same production origin as Step 3. Expected (the production-origin scratch
run of these exact edits on 2026-10-02): `computed-style diff: 0 difference(s)` (exit 0); `data 81748 13517` (−19,948
raw / −2,038 gzip against Step 3, 23,252 raw / 2,083 gzip under 105,000 / 15,600); `methodology 161354 45330` (+188
raw / +61 gzip against Step 3, under 162,000 / 45,400 with 646 raw / 70 gzip bytes left). Gzip may differ by up to
~10 bytes (the per-build ID); raw must match. The two `grep -c` on methodology print `1`; the one on `/data/` prints
`0`.

- [ ] **Step 11: Re-stamp the two measured pages in `site/scripts/gates/build.mjs`**

Both stamps come from Step 10's production-origin build, the origin Task 5 measured at, so neither mixes origins.
Below, the expected numbers from the 2026-10-02 scratch run are filled in. If Step 10 printed different numbers, use
Step 10's (raw and gzip from its `data` / `methodology` lines, comma-grouped) and recompute the "left" figures against
the unchanged ceilings; replace `2026-10-02` with the date you build.

Edit 1, `/data/`. Before (`:369-372`, the end of the 2026-09-26 comment and the entry):
```js
  // The drift leg fired at 7.0x (+245 gzip: the final review's fct_influence
  // and dim_geography descriptions, R-DEC-LDATOTAL). 41 gzip bytes left: any
  // further text here needs a trim first, never a raise.
  { label: "/data/", file: "data/index.html", maxRaw: 105_000, maxGzip: 15_600, measured: "101,707 / 15,559" },
```
After:
```js
  // The drift leg fired at 7.0x (+245 gzip: the final review's fct_influence
  // and dim_geography descriptions, R-DEC-LDATOTAL). 41 gzip bytes left: any
  // further text here needs a trim first, never a raise.
  // FAMILIES PIECE 1 (2026-10-02, Task 19 Part A): the inventory rows'
  // utility strings moved into src/app/data/data.module.css (the
  // coverage.module.css move). p1_era_line_map adds a 17th inventory row and
  // Explorer option, and one row weighs more than the 42 gzip bytes this
  // page had left (live 2026-10-01: 101,696 / 15,558). Production-origin
  // builds against 2026-10-02's data: 101,696 / 15,555 -> 81,748 / 13,517
  // (-19,948 raw / -2,038 gzip); scripts/computed-style-snapshot.mjs found 0
  // computed-style differences (390/1440, light/dark, screen/print, row
  // hover). The new row (simulated +381 to +605 gzip by scope length) ships
  // with the map; Task 21's S4 build re-measures it. The per-edition era
  // table does not render here: as built it weighed +3,647 gzip on this page
  // even after the hoist. CEILINGS UNCHANGED. RE-MEASURED 2026-10-02 (Task 19
  // Part A build, before the map ships; gate 1's own weigh()): 81,748 /
  // 13,517; 23,252 raw / 2,083 gzip left.
  { label: "/data/", file: "data/index.html", maxRaw: 105_000, maxGzip: 15_600, measured: "81,748 / 13,517" },
```

Edit 2, `/methodology/` (`:641-647` before Task 5; Task 5 Step 15's edit 1 left it as below). Before (Task 5's
after-text; its `<git_head>` and `<built_at>` hold the values Task 5 wrote, and if Task 5 stamped other build numbers
than `161,166 / 45,270`, its lines carry those; match them as they stand in the file):
```js
  // RE-MEASURED 2026-10-02 (families piece 1 S0, build of <git_head>, built
  // <built_at>, on the 2026-10-02T01:30:21Z export of 125,409 citations;
  // gate 1's own weigh()): 160,836 / 45,147 -> 161,166 / 45,270. CEILINGS
  // UNCHANGED; 834 raw / 130 gzip left (the old stamp claimed 253).
  // Production served 161,166 / 45,270 the same day. Piece 1 replaces one
  // sentence here at equal length and adds a link (spec §6.4); its era table
  // renders wherever it fits without a ceiling raise, decided in Task 19.
  { label: "/methodology/", file: "methodology/index.html", maxRaw: 162_000, maxGzip: 45_400, measured: "161,166 / 45,270" },
```
After (Task 5's seven comment lines unchanged, six new comment lines, the new `measured` string):
```js
  // RE-MEASURED 2026-10-02 (families piece 1 S0, build of <git_head>, built
  // <built_at>, on the 2026-10-02T01:30:21Z export of 125,409 citations;
  // gate 1's own weigh()): 160,836 / 45,147 -> 161,166 / 45,270. CEILINGS
  // UNCHANGED; 834 raw / 130 gzip left (the old stamp claimed 253).
  // Production served 161,166 / 45,270 the same day. Piece 1 replaces one
  // sentence here at equal length and adds a link (spec §6.4); its era table
  // renders wherever it fits without a ceiling raise, decided in Task 19.
  // FAMILIES PIECE 1 (2026-10-02, Task 19 Part A): the "PB2024 boundary"
  // sentence became the era-procurement gap sentence at its exact rendered
  // length (312 bytes); only its p1_era_line_map link is new. RE-MEASURED
  // 2026-10-02 (production-origin build; gate 1's own weigh()): 161,166 /
  // 45,269 -> 161,354 / 45,330 (+188 raw / +61 gzip). CEILINGS UNCHANGED;
  // 646 raw / 70 gzip left. The era table does not render here.
  { label: "/methodology/", file: "methodology/index.html", maxRaw: 162_000, maxGzip: 45_400, measured: "161,354 / 45,330" },
```
Run:
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && node --input-type=module -e 'import("./scripts/gates/build.mjs").then(({checkPageWeight})=>{const r=checkPageWeight();console.log(r.errors.filter(e=>/\/(data|methodology)\//.test(e)).length)})'
```
Expected: `0` (no ceiling or stamp-drift error for either page). Verified on the production-origin scratch build
(Task 5's stamps applied first): with both pages re-stamped it prints `0`; with the pre-Task-5 `/methodology/` stamp
(`160,836 / 45,147`) the drift leg reports `45,330 (70 left, 3.6x less than recorded)`. Task 5's own stamp
(130 claimed, 70 real) stays under the drift leg's 2x trigger, so this re-stamp is record-keeping, not a gate fix.

- [ ] **Step 12: Commit Part A**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/site/scripts/computed-style-snapshot.mjs GovBudget/site/src/app/data/data.module.css GovBudget/site/src/app/data/page.tsx GovBudget/site/src/app/methodology/page.tsx GovBudget/site/src/lib/corpus.ts GovBudget/site/scripts/gates/build.mjs GovBudget/site/src/__tests__/data-inventory-hoist.test.ts GovBudget/site/src/__tests__/methodology-era-sentence.test.ts && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(site): room for the era map on /data/ (inventory hoist) and the era sentence on /methodology/ (families piece 1, Task 19a)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

#### Part B — the exporter: the map parquet and the era summary

- [ ] **Step 13: Write the failing exporter tests**

Create `tests/test_export_era_line_map.py`:
```python
"""p1_era_line_map ships as an uncited dataset (families piece 1, spec
2026-10-02 §4.4, §7; Task 19).

The map's rows are decisions, not money: it goes on the uncited ledger, its
scope sentence names both meanings of pe_bli the spec keeps apart (§6.1), an
undecided era line never ships, and era points can never ship without the map
that put them there.
"""
from __future__ import annotations

import duckdb
import pytest

from govbudget.export_site import (
    _CITED_DATASETS,
    _DATASET_SCOPES,
    ERA_MAP_DATASET,
    _export_p1_era_line_map,
)

MAP_DDL = (
    "create table p1_era_line_map ("
    " edition integer, account varchar, organization varchar,"
    " budget_activity varchar, era_key varchar, line_item_code varchar,"
    " filed_title varchar, program_key varchar, program_account varchar,"
    " program_org varchar, decision varchar, decision_id varchar,"
    " ruling varchar, keys_sha_ok boolean, successor_code varchar,"
    " source_document_sha256 varchar, source_cells varchar)"
)
ROWS = [
    (2018, "3010F", "AF", "01", "3010F-AF-L2", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME", True, None, "sha18", "J9"),
    (2017, "3010F", "AF", "01", "3010F-AF-L1", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME", True, None, "sha17", "J8"),
    (2017, "3010F", "AF", "05", "3010F-AF-L9", "F0150P", "LEGACY LINE", "F0150P", None, None,
     "history_only", "F0150P|3010F||2017-2017", "R-DEC-ERA-HISTORY", True, None, "sha17", "J20"),
    (2017, "0300D", "OSD", "01", "0300D-OSD-L50", "50", "INDIAN FINANCING ACT", None, None, None,
     "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B1", True, None, "sha17", "J60"),
    (2017, "2035A", "A", "01", "2035A-A-L3", "FY2017CR", "CR ADJUSTMENT", None, None, None,
     "exclude_placeholder", "FY2017CR|2035A||2017-2017", "R-DEC-ERA-EXCLUDE", True, None, "sha17", "J70"),
]
INSERT = "insert into p1_era_line_map values (" + ",".join("?" * 17) + ")"


def _con_with_map(rows=ROWS):
    con = duckdb.connect()
    con.execute(MAP_DDL)
    con.executemany(INSERT, rows)
    return con


def test_scope_is_registered_after_budget_lines_decade():
    names = list(_DATASET_SCOPES)
    assert ERA_MAP_DATASET == "p1_era_line_map"
    assert names.index("p1_era_line_map") == names.index("budget_lines_decade") + 1


def test_scope_names_both_meanings_of_pe_bli_and_carries_no_money():
    scope = _DATASET_SCOPES["p1_era_line_map"]
    assert scope.startswith("One row per PB2017–PB2023 P-1 display line")
    assert "era_key (its pe_bli in budget_lines_decade)" in scope
    assert "line_item_code (the budget line code printed on it, the pe_bli its era citations carry)" in scope
    assert scope.endswith("Every row is a decision; none carries an amount.")


def test_the_map_stays_on_the_uncited_ledger():
    assert "p1_era_line_map" not in _CITED_DATASETS


def test_exports_every_row_in_key_order(tmp_path):
    con = _con_with_map()
    assert _export_p1_era_line_map(con, tmp_path) == 5
    keys = duckdb.connect().execute(
        "select edition, era_key from read_parquet(?)",
        [str(tmp_path / "p1_era_line_map.parquet")],
    ).fetchall()
    assert keys == [
        (2017, "0300D-OSD-L50"), (2017, "2035A-A-L3"), (2017, "3010F-AF-L1"),
        (2017, "3010F-AF-L9"), (2018, "3010F-AF-L2"),
    ]


def test_refuses_an_undecided_line(tmp_path):
    undecided = list(ROWS[0])
    undecided[10] = "undecided"
    con = _con_with_map([tuple(undecided)])
    with pytest.raises(RuntimeError, match="undecided"):
        _export_p1_era_line_map(con, tmp_path)
    assert not (tmp_path / "p1_era_line_map.parquet").exists()


def test_refuses_era_points_without_the_map(tmp_path):
    con = duckdb.connect()
    con.execute("create table fct_program_decade_series (program_key varchar, map_basis varchar)")
    con.execute("insert into fct_program_decade_series values ('ATA000', 'era_line_map'), ('0601101E', 'native')")
    with pytest.raises(RuntimeError, match="era point"):
        _export_p1_era_line_map(con, tmp_path)


def test_no_map_and_no_era_points_ships_nothing_and_removes_a_stale_file(tmp_path):
    (tmp_path / "p1_era_line_map.parquet").write_bytes(b"stale")
    con = duckdb.connect()
    con.execute("create table fct_program_decade_series (program_key varchar, map_basis varchar)")
    con.execute("insert into fct_program_decade_series values ('0601101E', 'native')")
    assert _export_p1_era_line_map(con, tmp_path) is None
    assert not (tmp_path / "p1_era_line_map.parquet").exists()


def test_a_fixture_program_table_without_map_basis_is_not_an_error(tmp_path):
    con = duckdb.connect()
    con.execute("create table fct_program_decade_series (program_key varchar)")
    assert _export_p1_era_line_map(con, tmp_path) is None
```

Create `tests/test_era_map_summary.py`:
```python
"""json/era_map_summary.json (families piece 1, spec 2026-10-02 §4.4, §6.4,
V7; Task 19): the era map counted per edition by decision, by ruling, and the
receipt completeness of each edition's cited P-1 cells, read from the receipts
audit of the SAME citations.json."""
from __future__ import annotations

import hashlib
import json

import duckdb
import pytest

from govbudget.export_site import write_era_map_summary

MAP_COLUMNS = "edition integer, era_key varchar, decision varchar, decision_id varchar, ruling varchar"
MAP_ROWS = [
    (2018, "3010F-AF-L2", "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME"),
    (2017, "3010F-AF-L1", "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME"),
    (2017, "3010F-AF-L9", "history_only", "F0150P|3010F||2017-2017", "R-DEC-ERA-HISTORY"),
    (2017, "0300D-OSD-L50", "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B1"),
    (2017, "2035A-A-L3", "exclude_placeholder", "FY2017CR|2035A||2017-2017", "R-DEC-ERA-EXCLUDE"),
]
CITATIONS = b'{"x": 1}'


def _site(tmp_path, *, rows=MAP_ROWS, full_corpus=True, citation_sha=None):
    site = tmp_path / "site"
    (site / "data").mkdir(parents=True)
    (site / "json").mkdir()
    con = duckdb.connect()
    con.execute(f"create table m ({MAP_COLUMNS})")
    con.executemany("insert into m values (?,?,?,?,?)", rows)
    con.execute(f"copy m to '{site / 'data' / 'p1_era_line_map.parquet'}' (format parquet)")
    con.close()
    (site / "json" / "citations.json").write_bytes(CITATIONS)
    (site / "json" / "budget_pdf_receipts_audit.json").write_text(json.dumps({
        "full_corpus": full_corpus,
        "citation_sha256": citation_sha or hashlib.sha256(CITATIONS).hexdigest(),
        "books": [
            {"edition": 2017, "exhibit": "P-1", "pages": 9, "facts": 6, "complete": 5},
            {"edition": 2017, "exhibit": "R-1", "pages": 9, "facts": 100, "complete": 100},
        ],
    }))
    db = tmp_path / "wh.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table fct_decade_series (pe_bli varchar, fy integer, edition_year integer,"
                " amount_type_kind varchar, amount_thousands double)")
    con.executemany("insert into fct_decade_series values (?,?,?,?,?)", [
        ("3010F-AF-L1", 2015, 2017, "actuals", 1000.0),
        ("3010F-AF-L1", 2016, 2017, "enacted", 999.0),
        ("3010F-AF-L2", 2016, 2018, "actuals", 2000.0),
        ("3010F-AF-L9", 2015, 2017, "actuals", 300.0),
        ("0300D-OSD-L50", 2015, 2017, "actuals", 50.0),
    ])
    con.close()
    return site, db


def _tally(chains, lines, actuals):
    return {"chains": chains, "lines": lines, "actuals_thousands": actuals}


ZERO = _tally(0, 0, 0.0)


def test_counts_every_edition_by_decision_and_ruling(tmp_path):
    site, db = _site(tmp_path)
    summary = write_era_map_summary(site_dir=site, duckdb_path=db)
    assert json.loads((site / "json" / "era_map_summary.json").read_text()) == summary
    assert summary["schema_version"] == 1
    assert [e["edition"] for e in summary["editions"]] == list(range(2017, 2024))
    assert summary["editions"][0] == {
        "edition": 2017, "fy_actuals": 2015, "lines": 4,
        "by_decision": {
            "same_program": _tally(1, 1, 1000.0),
            "history_only": _tally(1, 1, 300.0),
            "exclude_placeholder": _tally(1, 1, 0.0),
            "exclude_route_unsafe": ZERO,
            "exclude_reused_code": _tally(1, 1, 50.0),
        },
        "receipts": {"facts": 6, "complete": 5},
    }
    e2018 = summary["editions"][1]
    assert e2018["lines"] == 1
    assert e2018["by_decision"]["same_program"] == _tally(1, 1, 2000.0)
    assert e2018["receipts"] == {"facts": 0, "complete": 0}
    assert all(e["lines"] == 0 for e in summary["editions"][2:])
    assert summary["by_ruling"] == [
        {"ruling": "R-DEC-ERA-B1", "decision": "exclude_reused_code", **_tally(1, 1, 50.0)},
        {"ruling": "R-DEC-ERA-EXCLUDE", "decision": "exclude_placeholder", **_tally(1, 1, 0.0)},
        {"ruling": "R-DEC-ERA-HISTORY", "decision": "history_only", **_tally(1, 1, 300.0)},
        {"ruling": "R-DEC-ERA-SAME", "decision": "same_program", **_tally(1, 2, 3000.0)},
    ]
    assert summary["totals"]["same_program"] == _tally(1, 2, 3000.0)
    assert summary["totals"]["exclude_route_unsafe"] == ZERO


def test_refuses_a_stale_audit(tmp_path):
    site, db = _site(tmp_path, citation_sha="0" * 64)
    with pytest.raises(ValueError, match="not a full-corpus run"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_refuses_a_partial_audit(tmp_path):
    site, db = _site(tmp_path, full_corpus=False)
    with pytest.raises(ValueError, match="not a full-corpus run"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_refuses_an_undecided_line(tmp_path):
    rows = MAP_ROWS + [(2019, "3010F-AF-L4", "undecided", None, None)]
    site, db = _site(tmp_path, rows=rows)
    with pytest.raises(ValueError, match="never published"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_refuses_an_edition_outside_the_era(tmp_path):
    rows = MAP_ROWS + [(2024, "3010F-AF-L4", "same_program", "X|3010F||2024-2024", "R-DEC-ERA-SAME")]
    site, db = _site(tmp_path, rows=rows)
    with pytest.raises(ValueError, match="outside PB2017–PB2023"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_no_map_writes_nothing_and_removes_a_stale_summary(tmp_path):
    site = tmp_path / "site"
    (site / "json").mkdir(parents=True)
    (site / "json" / "era_map_summary.json").write_text("{}")
    assert write_era_map_summary(site_dir=site, duckdb_path=tmp_path / "absent.duckdb") is None
    assert not (site / "json" / "era_map_summary.json").exists()
```

Append to `tests/test_budget_pdf_export_workflow.py`:
```python
def test_full_export_cli_writes_the_era_summary_after_the_receipts(monkeypatch, tmp_path):
    """Families piece 1 (Task 19): era_map_summary.json reads the receipts audit,
    so it is written after the receipts step, from the same site and warehouse."""
    configure_paths(monkeypatch, tmp_path)
    events = []
    monkeypatch.setattr(site_export, "export_site", lambda *a, **k: events.append("artifacts") or BASE_SUMMARY)

    def receipts(**kwargs):
        events.append("pdf-evidence")
        return RECEIPT_SUMMARY

    def summary(**kwargs):
        events.append("era-summary")
        assert kwargs == {"site_dir": tmp_path / "site", "duckdb_path": tmp_path / "warehouse.duckdb"}
        return {"editions": [{}] * 7}

    monkeypatch.setattr(receipt_export, "export_program_pdf_receipts", receipts)
    monkeypatch.setattr(site_export, "write_era_map_summary", summary)
    cli.main(["export-site"])
    assert events == ["artifacts", "pdf-evidence", "era-summary"]


def test_evidence_only_refresh_rewrites_the_era_summary(monkeypatch, tmp_path, capsys):
    configure_paths(monkeypatch, tmp_path)
    events = []
    monkeypatch.setattr(receipt_export, "export_program_pdf_receipts", lambda **k: events.append("pdf-evidence") or RECEIPT_SUMMARY)
    monkeypatch.setattr(site_export, "write_era_map_summary", lambda **k: events.append("era-summary") or {"editions": [{}] * 7})
    cli.main(["export-budget-pdf-receipts"])
    assert events == ["pdf-evidence", "era-summary"]
    assert "era map summary: 7 editions" in capsys.readouterr().out


def test_the_era_summary_recounts_the_manifest_json_sidecars(monkeypatch, tmp_path):
    """The F-15 builder sets manifest.json json_sidecars (its rglob count of
    json/**/*.json) before the receipts step writes json/era_map_summary.json,
    so the receipts step recounts after the summary (Task 19, pre-flight)."""
    configure_paths(monkeypatch, tmp_path)
    json_dir = tmp_path / "site" / "json"
    json_dir.mkdir(parents=True)
    (json_dir / "citations.json").write_text("{}")
    manifest = tmp_path / "site" / "manifest.json"
    manifest.write_text('{"built_at":"b","json_sidecars":1}\n')
    monkeypatch.setattr(receipt_export, "export_program_pdf_receipts", lambda **k: RECEIPT_SUMMARY)

    def summary(**kwargs):
        (kwargs["site_dir"] / "json" / "era_map_summary.json").write_text("{}")
        return {"editions": [{}] * 7}

    monkeypatch.setattr(site_export, "write_era_map_summary", summary)
    cli.main(["export-budget-pdf-receipts"])
    assert manifest.read_text() == '{"built_at":"b","json_sidecars":2}\n'
    cli.main(["export-budget-pdf-receipts"])          # already right: bytes untouched
    assert manifest.read_text() == '{"built_at":"b","json_sidecars":2}\n'


def test_no_era_summary_leaves_the_manifest_alone(monkeypatch, tmp_path):
    configure_paths(monkeypatch, tmp_path)
    json_dir = tmp_path / "site" / "json"
    json_dir.mkdir(parents=True)
    (json_dir / "a.json").write_text("{}")
    (json_dir / "b.json").write_text("{}")
    manifest = tmp_path / "site" / "manifest.json"
    manifest.write_text('{\n  "json_sidecars": 1\n}')
    monkeypatch.setattr(receipt_export, "export_program_pdf_receipts", lambda **k: RECEIPT_SUMMARY)
    monkeypatch.setattr(site_export, "write_era_map_summary", lambda **k: None)
    cli.main(["export-budget-pdf-receipts"])
    assert manifest.read_text() == '{\n  "json_sidecars": 1\n}'
```

Append to `tests/jbooks/test_export_site_pg.py`:
```python
# ---------------------------------------------------------------------------
# Families piece 1 (Task 19): p1_era_line_map ships as an uncited dataset
# ---------------------------------------------------------------------------

_ERA_MAP_DDL = (
    "create table p1_era_line_map ("
    " edition integer, account varchar, organization varchar,"
    " budget_activity varchar, era_key varchar, line_item_code varchar,"
    " filed_title varchar, program_key varchar, program_account varchar,"
    " program_org varchar, decision varchar, decision_id varchar,"
    " ruling varchar, keys_sha_ok boolean, successor_code varchar,"
    " source_document_sha256 varchar, source_cells varchar)"
)


def _add_era_map(db_path: Path, first: str, second: str) -> None:
    con = duckdb.connect(str(db_path))
    try:
        con.execute(_ERA_MAP_DDL)
        con.execute(
            "insert into p1_era_line_map values"
            " (2017, '3010F', 'AF', '04', '3010F-AF-L1', 'ATA000', 'F-35', 'ATA000', null, null,"
            "  ?, 'ATA000|3010F||2017-2021', 'R-DEC-ERA-SAME', true, null, 'sha17', 'J7'),"
            " (2019, '3010F', 'AF', '05', '3010F-AF-L9', 'F0150P', 'LEGACY LINE', 'F0150P', null, null,"
            "  ?, 'F0150P|3010F||2019-2019', 'R-DEC-ERA-HISTORY', true, null, 'sha19', 'J30')",
            [first, second],
        )
    finally:
        con.close()


def test_export_site_ships_p1_era_line_map_uncited(pg_dsn, tmp_path):
    from govbudget.jbooks.provenance_pages import build_provenance_pages

    doc_id, sha = _seed_jbook_doc(pg_dsn, pdf_path=FIXTURE_PDF)
    _seed_budget_line(pg_dsn, doc_id, sha)
    build_provenance_pages(pg_dsn)
    db = tmp_path / "wh.duckdb"
    _make_test_duckdb(db)
    _add_era_map(db, "same_program", "history_only")

    site = tmp_path / "site"
    export_site(pg_dsn, db, out_dir=site, pdf_base_url="/pdfs")

    pq = site / "data" / "p1_era_line_map.parquet"
    assert pq.exists()
    rows = duckdb.connect().execute(
        "select edition, era_key, decision from read_parquet(?)", [str(pq)]).fetchall()
    assert rows == [(2017, "3010F-AF-L1", "same_program"), (2019, "3010F-AF-L9", "history_only")]
    man = json.loads((site / "manifest.json").read_text())
    assert man["datasets"]["p1_era_line_map"] == 2
    assert "p1_era_line_map" in man["uncited_datasets"]
    inventory = json.loads((site / "json" / "datasets.json").read_text())["datasets"]
    entry = next(d for d in inventory if d["name"] == "p1_era_line_map")
    assert entry["cited"] is False
    assert entry["row_count"] == 2
    assert entry["scope"].startswith("One row per PB2017–PB2023 P-1 display line")


def test_export_site_refuses_an_undecided_era_line(pg_dsn, tmp_path):
    _seed_jbook_doc(pg_dsn, pdf_path=FIXTURE_PDF)
    db = tmp_path / "wh.duckdb"
    _make_test_duckdb(db)
    _add_era_map(db, "same_program", "undecided")
    with pytest.raises(RuntimeError, match="undecided"):
        export_site(pg_dsn, db, out_dir=tmp_path / "site", pdf_base_url="/pdfs")
```

Run (one file per invocation: a collection error stops the whole session):
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_export_era_line_map.py -q
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_era_map_summary.py -q
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_budget_pdf_export_workflow.py -q
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_site_pg.py -q -k "era_line"
```
Expected: FAIL. The first errors at collection: `ImportError: cannot import name 'ERA_MAP_DATASET' from
'govbudget.export_site'`; the second: `ImportError: cannot import name 'write_era_map_summary' from
'govbudget.export_site'`; the third: `4 failed, 6 passed`, all four new tests with `AttributeError: <module
'govbudget.export_site' …> has no attribute 'write_era_map_summary'`; the PG pair: `2 failed` (`assert pq.exists()`,
and `Failed: DID NOT RAISE <class 'RuntimeError'>`).

- [ ] **Step 14: Implement the exporter additions in `src/govbudget/export_site.py`**

Scope entry. Before (`:1753-1759`):
```python
    "budget_lines_decade": (
        "The decade sibling of budget_lines: one row per (President's Budget"
        " edition × program element × amount type) figure across all ten"
        " editions PB2017–PB2026, each cited to its own edition's workbook"
        " cell. Editions are parallel publications, never reconciled."
    ),
    "jbook_details": (
```
After:
```python
    "budget_lines_decade": (
        "The decade sibling of budget_lines: one row per (President's Budget"
        " edition × program element × amount type) figure across all ten"
        " editions PB2017–PB2026, each cited to its own edition's workbook"
        " cell. Editions are parallel publications, never reconciled."
    ),
    # Families piece 1 (spec 2026-10-02 §4.4): the reviewed era code
    # decisions. Uncited by construction (no amounts), so it stays off
    # _CITED_DATASETS. It names both meanings of pe_bli §6.1 keeps apart: the
    # era key budget_lines_decade rows carry, and the printed code an era
    # citation carries. /data/ renders it three times under a 15,600 gzip
    # ceiling that data.module.css made room for (Task 19).
    "p1_era_line_map": (
        "One row per PB2017–PB2023 P-1 display line: era_key (its pe_bli in"
        " budget_lines_decade), line_item_code (the budget line code printed"
        " on it, the pe_bli its era citations carry) and the dated owner"
        " decision that joins it to a program page or to history only, or"
        " excludes it. Every row is a decision; none carries an amount."
    ),
    "jbook_details": (
```

New constants and functions, inserted after `_build_dataset_manifest` (after `:2186`, before the
`#: Final-review finding #10 (2026-09-27)` comment block):
```python
#: Families piece 1 (spec 2026-10-02 §4.4, §6.4): the era-map dataset, the
#: summary the site renders from it, and the P-1 editions it covers.
ERA_MAP_DATASET = "p1_era_line_map"
ERA_MAP_SUMMARY_FILE = "era_map_summary.json"
ERA_MAP_EDITIONS = tuple(range(2017, 2024))


def _export_p1_era_line_map(con, data_dir: Path) -> int | None:
    """Ship the reviewed era code decisions as data/p1_era_line_map.parquet.

    Families piece 1 (spec 2026-10-02 §4.4, §7). `con` is the export's
    read-only warehouse connection. Returns the row count written, or None
    when the warehouse has no p1_era_line_map (a fixture warehouse, or one
    built before the map existed); then a stale parquet left in `data_dir` by
    an earlier export is removed, never re-shipped.

    Raises RuntimeError when the map holds an `undecided` row (§7: an era key
    with no decision is never exported; dbt's assert_p1_era_map_no_undecided
    is the build-time twin), and when the map is missing while
    fct_program_decade_series carries era points (map_basis other than
    'native'): era points never ship without the decisions behind them.
    """
    dest = Path(data_dir) / f"{ERA_MAP_DATASET}.parquet"
    tables = {r[0] for r in con.execute(
        "select table_name from information_schema.tables"
        " where table_schema = 'main'").fetchall()}
    if ERA_MAP_DATASET not in tables:
        if "fct_program_decade_series" in tables:
            cols = {r[0] for r in con.execute(
                "select column_name from information_schema.columns"
                " where table_schema = 'main'"
                " and table_name = 'fct_program_decade_series'").fetchall()}
            if "map_basis" in cols:
                era_points = con.execute(
                    "select count(*) from fct_program_decade_series"
                    " where map_basis <> 'native'").fetchone()[0]
                if era_points:
                    raise RuntimeError(
                        f"export-site: fct_program_decade_series carries {era_points}"
                        " era point(s) but the warehouse has no p1_era_line_map; era"
                        " points cannot ship without the decisions that put them"
                        " there (run govbudget build)")
        dest.unlink(missing_ok=True)
        return None
    undecided = con.execute(
        f"select count(*) from {ERA_MAP_DATASET} where decision = 'undecided'"
    ).fetchone()[0]
    if undecided:
        raise RuntimeError(
            f"export-site: p1_era_line_map holds {undecided} undecided era line(s);"
            " an era key with no decision is never exported (spec §7). Run"
            " `govbudget era-map check`.")
    dest_str = str(dest).replace("'", "''")
    con.execute(
        f"COPY (select * from {ERA_MAP_DATASET}"
        " order by edition, account, organization, budget_activity, era_key)"
        f" TO '{dest_str}' (format parquet, compression zstd)")
    return int(con.execute(
        f"select count(*) from read_parquet('{dest_str}')").fetchone()[0])


def write_era_map_summary(*, site_dir: Path, duckdb_path: Path) -> dict | None:
    """json/era_map_summary.json: the shipped era map, counted (spec §4.4, §6.4, V7).

    Per PB2017–PB2023 edition: the P-1 lines the map holds; per decision, the
    chains (distinct decision_id with a line in that edition), lines and their
    FY N−2 actuals (fct_decade_series kind 'actuals', USD thousands); and the
    edition's P-1 receipt completeness from json/budget_pdf_receipts_audit.json.
    Across editions, the same tallies by (ruling, decision) and by decision.

    Runs AFTER export_program_pdf_receipts (cli._export_budget_pdf_evidence):
    the audit must be a full-corpus run over THIS citations.json (its
    citation_sha256), or this raises ValueError rather than publish another
    run's completeness. Returns None, and removes a stale summary, when the
    export shipped no data/p1_era_line_map.parquet. Raises ValueError on a
    decision outside DECISIONS (an `undecided` row) or an edition outside
    2017–2023.
    """
    import duckdb as _duckdb

    from govbudget.jbooks.era_map import DECISIONS

    site_dir = Path(site_dir)
    out_path = site_dir / "json" / ERA_MAP_SUMMARY_FILE
    parquet = site_dir / "data" / f"{ERA_MAP_DATASET}.parquet"
    if not parquet.is_file():
        out_path.unlink(missing_ok=True)
        return None
    audit = json.loads((site_dir / "json" / "budget_pdf_receipts_audit.json").read_text())
    citations_sha = hashlib.sha256(
        (site_dir / "json" / "citations.json").read_bytes()).hexdigest()
    if not audit.get("full_corpus") or audit.get("citation_sha256") != citations_sha:
        raise ValueError(
            "era_map_summary: budget_pdf_receipts_audit.json is not a full-corpus run"
            " over this citations.json; run `govbudget export-budget-pdf-receipts` first")
    con = _duckdb.connect(str(duckdb_path), read_only=True)
    try:
        rows = con.execute(
            "with a as ("
            "  select pe_bli, edition_year, sum(amount_thousands) as actuals"
            "  from fct_decade_series"
            "  where amount_type_kind = 'actuals' and fy = edition_year - 2"
            "  group by pe_bli, edition_year)"
            " select m.edition, m.era_key, m.decision, m.decision_id, m.ruling,"
            "        coalesce(a.actuals, 0)"
            " from read_parquet(?) m"
            " left join a on a.pe_bli = m.era_key and a.edition_year = m.edition"
            " order by m.edition, m.era_key",
            [str(parquet)],
        ).fetchall()
    finally:
        con.close()

    def tally() -> dict:
        return {"chains": set(), "lines": 0, "actuals": Decimal(0)}

    per_edition = {ed: {d: tally() for d in DECISIONS} for ed in ERA_MAP_EDITIONS}
    totals = {d: tally() for d in DECISIONS}
    by_ruling: dict[tuple[str, str], dict] = {}
    for edition, era_key, decision, decision_id, ruling, actuals in rows:
        edition = int(edition)
        if edition not in per_edition:
            raise ValueError(
                f"era_map_summary: {era_key} sits in PB{edition}, outside PB2017–PB2023")
        if decision not in DECISIONS:
            raise ValueError(
                f"era_map_summary: {era_key} (PB{edition}) carries decision"
                f" {decision!r}; an undecided era line is never published")
        amount = Decimal(str(actuals))
        for t in (per_edition[edition][decision], totals[decision],
                  by_ruling.setdefault((ruling or "", decision), tally())):
            t["chains"].add(decision_id)
            t["lines"] += 1
            t["actuals"] += amount

    def counted(t: dict) -> dict:
        return {"chains": len(t["chains"]), "lines": t["lines"],
                "actuals_thousands": float(t["actuals"])}

    books = {(b.get("edition"), b.get("exhibit")): b for b in audit.get("books", [])}
    editions = []
    for ed in ERA_MAP_EDITIONS:
        book = books.get((ed, "P-1"), {})
        editions.append({
            "edition": ed,
            "fy_actuals": ed - 2,
            "lines": sum(t["lines"] for t in per_edition[ed].values()),
            "by_decision": {d: counted(per_edition[ed][d]) for d in DECISIONS},
            "receipts": {"facts": int(book.get("facts", 0)),
                         "complete": int(book.get("complete", 0))},
        })
    summary = {
        "schema_version": 1,
        "actuals_basis": ("FY N-2 actuals as printed in the PB N P-1"
                          " (fct_decade_series amount_type_kind 'actuals'),"
                          " USD thousands, nominal"),
        "receipts_basis": ("budget_pdf_receipts_audit.json books[edition, P-1]:"
                           " the edition's cited P-1 workbook facts and how many"
                           " carry a complete PDF receipt"),
        "editions": editions,
        "by_ruling": [{"ruling": r, "decision": d, **counted(t)}
                      for (r, d), t in sorted(by_ruling.items())],
        "totals": {d: counted(totals[d]) for d in DECISIONS},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, summary)
    return summary
```

Wiring in `export_site()`. Before (`:2584-2590`):
```python
        # dim_lobbyists — enriched typed export (see _export_dim_lobbyists)
        lobbyist_rows = _export_dim_lobbyists(
            con=con, duckdb_path=duckdb_path, data_dir=data_dir
        )
        dataset_counts["dim_lobbyists"] = len(lobbyist_rows)
    finally:
        con.close()
```
After:
```python
        # dim_lobbyists — enriched typed export (see _export_dim_lobbyists)
        lobbyist_rows = _export_dim_lobbyists(
            con=con, duckdb_path=duckdb_path, data_dir=data_dir
        )
        dataset_counts["dim_lobbyists"] = len(lobbyist_rows)

        # p1_era_line_map — the reviewed era code decisions (families piece
        # 1). Uncited: _CITED_DATASETS leaves it on the ledger below.
        era_map_rows = _export_p1_era_line_map(con, data_dir)
        if era_map_rows is not None:
            dataset_counts[ERA_MAP_DATASET] = era_map_rows
    finally:
        con.close()
```

- [ ] **Step 15: Write the summary from the receipts step in `src/govbudget/cli.py`**

Before (`:2471-2480`):
```python
def _export_budget_pdf_evidence(*, site_dir: Path, manifest: Path, cache_dir: Path) -> dict:
    from govbudget.program_pdf_receipts import export_program_pdf_receipts

    report = export_program_pdf_receipts(site_dir=site_dir, manifest=manifest, cache_dir=cache_dir)
    print(
        f"budget PDF receipts: {report['complete_receipts']}/{report['receipt_count']} complete,"
        f" {report['source_count']} government documents;"
        f" audit -> {site_dir / 'json' / 'budget_pdf_receipts_audit.json'}"
    )
    return report
```
After:
```python
def _export_budget_pdf_evidence(*, site_dir: Path, manifest: Path, cache_dir: Path) -> dict:
    from govbudget.export_site import write_era_map_summary
    from govbudget.program_pdf_receipts import export_program_pdf_receipts

    report = export_program_pdf_receipts(site_dir=site_dir, manifest=manifest, cache_dir=cache_dir)
    print(
        f"budget PDF receipts: {report['complete_receipts']}/{report['receipt_count']} complete,"
        f" {report['source_count']} government documents;"
        f" audit -> {site_dir / 'json' / 'budget_pdf_receipts_audit.json'}"
    )
    # Families piece 1 (spec §6.4, V7): the era summary reports each era
    # edition's receipt completeness from the audit just written, so it is
    # refreshed here, after every receipts run; None when no era map shipped.
    era = write_era_map_summary(site_dir=site_dir, duckdb_path=config.DUCKDB_PATH)
    if era is not None:
        print(f"era map summary: {len(era['editions'])} editions"
              f" -> {site_dir / 'json' / 'era_map_summary.json'}")
        # The F-15 family-history builder counted json/**/*.json for
        # manifest.json's json_sidecars before this file existed.
        _refresh_json_sidecars(site_dir)
    return report


def _refresh_json_sidecars(site_dir: Path) -> int | None:
    """Recount manifest.json's json_sidecars after a late JSON sidecar.

    export_site's F-15 family-history builder sets json_sidecars to the number
    of json/**/*.json files (f15_funding_history.py, `json_dir.rglob("*.json")`)
    before the receipts step runs, so json/era_map_summary.json, written above
    on an export's first run, would be left out. Same count and the same
    serialization as that builder (sorted keys, compact, trailing newline); the
    file is rewritten only when the number changed. Returns the count, or None
    when the site has no manifest.json.
    """
    import json

    path = site_dir / "manifest.json"
    if not path.is_file():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    count = len(list((site_dir / "json").rglob("*.json")))
    if manifest.get("json_sidecars") != count:
        manifest["json_sidecars"] = count
        path.write_bytes((json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode())
    return count
```

`--site-dir` must belong to the same `GOVBUDGET_DATA`/`GOVBUDGET_DUCKDB` environment as the
warehouse `config.DUCKDB_PATH` names (source the snapshot's `env.sh` first when the site is
a proof clone): the summary takes its actuals from that warehouse.

- [ ] **Step 16: Run the exporter tests and their neighbours**

Run:
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_export_era_line_map.py tests/test_era_map_summary.py tests/test_budget_pdf_export_workflow.py tests/test_export_site_datasets_manifest.py tests/test_export_site_private_duckdb.py -q
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_site_pg.py -q
```
Expected: all pass, including the 8 new tests in `test_export_era_line_map.py`, the 6 in `test_era_map_summary.py`, the
4 new workflow tests (two for the summary's order, two for the `json_sidecars` recount) and the 2 new PG tests; the manifest file's grain-sentence, em-dash and serial-comma checks now
also cover the new scope.

- [ ] **Step 17: Real-data check, read-only (needs Tasks 13 and 15 in the shared warehouse)**

Run (writes only under `.proofs/`; the warehouse is opened read-only):
This step opens the live lake (README SAM window, read-only included): if a block prints `WAIT: SAM window …`, nothing ran — wait until :23 and re-run that block.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t19-era-summary
rm -rf "$P" && mkdir -p "$P/site/data" "$P/site/json"
ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/citations.json "$P/site/json/citations.json"
ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/budget_pdf_receipts_audit.json "$P/site/json/budget_pdf_receipts_audit.json"
uv run --project . python - <<'EOF'
import duckdb
from pathlib import Path
from govbudget.export_site import _export_p1_era_line_map, write_era_map_summary
P = Path("/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/t19-era-summary/site")
db = Path("/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb")
con = duckdb.connect(str(db), read_only=True)
print("rows", _export_p1_era_line_map(con, P / "data"))
con.close()
s = write_era_map_summary(site_dir=P, duckdb_path=db)
for e in s["editions"]:
    print(e["edition"], e["lines"], round(sum(t["actuals_thousands"] for t in e["by_decision"].values())), e["receipts"])
EOF
```
Expected:
```
rows 6927
2017 969 84973261 {'facts': 6, 'complete': 6}
2018 1029 99430079 {'facts': 9, 'complete': 9}
2019 989 104763979 {'facts': 12, 'complete': 12}
2020 975 126277051 {'facts': 15, 'complete': 15}
2021 1005 126295890 {'facts': 18, 'complete': 18}
2022 993 121099071 {'facts': 18, 'complete': 18}
2023 967 120917488 {'facts': 15, 'complete': 15}
```
(Lines and FY N−2 actuals per edition measured 2026-10-02 from `stg_budget_lines` era keys joined to
`fct_decade_series` kind 'actuals', fy = edition − 2; 6,927 keys, $783,756,819K. Receipts are today's audit, F-15's 93
era cells; Task 21's S4 export changes them.) A `RuntimeError … undecided` here means Task 15 has not closed S2.

- [ ] **Step 18: Commit Part B**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/export_site.py GovBudget/src/govbudget/cli.py GovBudget/tests/test_export_era_line_map.py GovBudget/tests/test_era_map_summary.py GovBudget/tests/test_budget_pdf_export_workflow.py GovBudget/tests/jbooks/test_export_site_pg.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(export): ship p1_era_line_map (uncited) and json/era_map_summary.json (families piece 1, Task 19b)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

#### Part C — the owner's decision, then the site: dataset registration, Explorer presets, the era table, gate 24 leg (s)

Part C departs from the approved spec three times (the table's page; counts instead of dollars; a second
`/methodology/` clause, because the uncited `p1_era_line_map` makes "the pending ledger is empty" false). Steps 19–20
confirm that the owner decided all three at plan review and that the plan commit recorded it; nothing is written to the
spec or the ROADMAP here.

- [ ] **Step 19: Owner decision — already made (2026-10-02)**

The owner decided all three points at plan review on 2026-10-02 ("/downloads/, counts only"; "Yes, badge + sentence";
see spec §6.4's `*Owner decision (2026-10-02, …)*` note and the ROADMAP "Platform families" paragraph, both written
in the plan commit): the per-edition table renders on `/downloads/` under the `p1_era_line_map` card, counts only,
with the dollars in `json/era_map_summary.json`; `/data/` shows the "tier pending" badge for `p1_era_line_map`; the
`/methodology/` pending-ledger clause is replaced at equal length. Proceed with Part C as written. Do not ask again.

- [ ] **Step 20: Nothing to record**

The spec notes (§6.4, §10) and the ROADMAP sentence were written in the plan commit. Check they are present:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
grep -c "renders on\|\`/downloads/\`, directly under the" docs/superpowers/specs/2026-10-02-era-procurement-history-design.md
grep -c "Owner decisions at plan review (2026-10-02)" docs/superpowers/ROADMAP.md
```

Expected: a count of at least `1` for each. No commit in this step.

- [ ] **Step 21: Write the failing site tests**

In `site/src/__tests__/duckdb-helpers.test.ts`, before (`:119-125`):
```ts
  it("contains exactly 16 datasets", () => {
    expect(DATASET_NAMES).toHaveLength(16);
  });

  it("registers budget_lines_decade — shipped since 5E, unqueryable until §P1-5", () => {
    expect(DATASET_NAMES).toContain("budget_lines_decade");
  });
```
After:
```ts
  it("contains exactly 17 datasets", () => {
    expect(DATASET_NAMES).toHaveLength(17);
  });

  it("registers budget_lines_decade — shipped since 5E, unqueryable until §P1-5", () => {
    expect(DATASET_NAMES).toContain("budget_lines_decade");
  });

  it("registers p1_era_line_map — the era code decisions (families piece 1)", () => {
    expect(DATASET_NAMES).toContain("p1_era_line_map");
  });
```
and in the same file's `expected` list (`:128-145`), after `"jbook_narratives",` add `"p1_era_line_map",`.

Create `site/src/__tests__/explorer-era-map-preset.test.ts`:
```ts
/**
 * /data/ Explorer presets for p1_era_line_map (families piece 1, Task 19).
 * The map carries decisions, not money: the presets count chains (distinct
 * decision_id) and lines, and list the owner review batches by ruling id.
 * tests/test_explorer_era_map_preset.py runs both against a fixture parquet.
 */
import { describe, it, expect } from "vitest";
import { cannedQueriesFor } from "@/components/explorer";

describe("Explorer — p1_era_line_map presets", () => {
  const presets = cannedQueriesFor("p1_era_line_map");
  const sql = (label: string): string =>
    presets.find((q) => q.label === label)!.sql.replace(/\s+/g, " ");

  it("offers the two presets, in order", () => {
    expect(presets.map((q) => q.label)).toEqual([
      "Decisions by edition",
      "Lines decided in owner review batches",
    ]);
  });

  it("counts chains as distinct decisions and lines as rows, per edition and decision", () => {
    expect(sql("Decisions by edition")).toMatch(/COUNT\(DISTINCT decision_id\) AS chains/);
    expect(sql("Decisions by edition")).toMatch(/COUNT\(\*\) AS lines/);
    expect(sql("Decisions by edition")).toMatch(/GROUP BY edition, decision ORDER BY edition, decision/);
  });

  it("selects the owner review batches by their ruling id", () => {
    expect(sql("Lines decided in owner review batches")).toContain("WHERE ruling LIKE 'R-DEC-ERA-B%'");
  });

  it("reads the map parquet and no amount column", () => {
    for (const q of presets) {
      expect(q.sql).toContain("FROM 'p1_era_line_map.parquet'");
      expect(q.sql).not.toMatch(/amount/i);
    }
  });
});
```

Create `tests/test_explorer_era_map_preset.py`:
```python
"""The /data/ Explorer's p1_era_line_map presets, run for real (families piece 1, Task 19).

The SQL lives in site/src/components/explorer.tsx and runs in the reader's
browser on DuckDB-WASM. This lifts it out of the component and runs it with
DuckDB on a fixture parquet shaped like the shipped map (spec §4.4 columns),
so it needs no export. The shape is pinned in
site/src/__tests__/explorer-era-map-preset.test.ts.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPLORER = ROOT / "site" / "src" / "components" / "explorer.tsx"
CASE = 'case "p1_era_line_map":'
MAP_DDL = (
    "create table m ("
    " edition integer, account varchar, organization varchar,"
    " budget_activity varchar, era_key varchar, line_item_code varchar,"
    " filed_title varchar, program_key varchar, program_account varchar,"
    " program_org varchar, decision varchar, decision_id varchar,"
    " ruling varchar, keys_sha_ok boolean, successor_code varchar,"
    " source_document_sha256 varchar, source_cells varchar)"
)
ROWS = [
    (2017, "3010F", "AF", "01", "3010F-AF-L1", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2021", "R-DEC-ERA-SAME", True, None, "sha17", "J8"),
    (2017, "3010F", "AF", "01", "3010F-AF-L2", "ATA000", "F-35 AP", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2021", "R-DEC-ERA-SAME", True, None, "sha17", "J9"),
    (2017, "1611N", "N", "02", "1611N-N-L4", "1045", "OHIO REPLACEMENT", "1045", "1611N", None,
     "same_program", "1045|1611N||2017-2020", "R-DEC-ERA-B1", True, None, "sha17", "J30"),
    (2018, "1611N", "N", "02", "1611N-N-L4", "1045", "OHIO REPLACEMENT", "1045", "1611N", None,
     "same_program", "1045|1611N||2017-2020", "R-DEC-ERA-B1", True, None, "sha18", "J31"),
    (2018, "0300D", "OSD", "01", "0300D-OSD-L50", "50", "INDIAN FINANCING ACT", None, None, None,
     "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B2", True, None, "sha18", "J60"),
]


def _presets() -> dict[str, str]:
    src = EXPLORER.read_text(encoding="utf-8")
    start = src.index(CASE)
    block = src[start:src.index("case ", start + len(CASE))]
    return {m.group(1): m.group(2).strip()
            for m in re.finditer(r'label: "([^"]+)",\s*sql: t\(`(.*?)`\)', block, re.S)}


@pytest.fixture()
def run(tmp_path):
    pq = tmp_path / "p1_era_line_map.parquet"
    con = duckdb.connect()
    con.execute(MAP_DDL)
    con.executemany("insert into m values (" + ",".join("?" * 17) + ")", ROWS)
    con.execute(f"copy m to '{pq.as_posix()}' (format parquet)")

    def _run(label: str):
        # The browser registers each dataset under its file name; here the
        # quoted name resolves against the fixture file instead.
        sql = _presets()[label].replace("'p1_era_line_map.parquet'", f"'{pq.as_posix()}'")
        cur = con.execute(sql)
        return [d[0] for d in cur.description], cur.fetchall()

    yield _run
    con.close()


def test_the_two_presets_exist_in_order():
    assert list(_presets()) == ["Decisions by edition", "Lines decided in owner review batches"]


def test_decisions_by_edition_counts_chains_and_lines(run):
    cols, rows = run("Decisions by edition")
    assert cols == ["edition", "decision", "chains", "lines"]
    assert rows == [
        (2017, "same_program", 2, 3),
        (2018, "exclude_reused_code", 1, 1),
        (2018, "same_program", 1, 1),
    ]


def test_owner_batches_list_only_batch_rulings(run):
    cols, rows = run("Lines decided in owner review batches")
    assert cols == ["edition", "era_key", "line_item_code", "filed_title", "program_key", "decision", "ruling"]
    assert [(r[0], r[1], r[6]) for r in rows] == [
        (2017, "1611N-N-L4", "R-DEC-ERA-B1"),
        (2018, "1611N-N-L4", "R-DEC-ERA-B1"),
        (2018, "0300D-OSD-L50", "R-DEC-ERA-B2"),
    ]
```

Create `site/src/__tests__/era-map-table.test.tsx`:
```tsx
/**
 * The /downloads/ era-map table (families piece 1, spec 2026-10-02 §6.4,
 * Task 19). It renders counts from json/era_map_summary.json: lines, chains
 * ("codes") per decision, and receipt completeness, never a dollar figure (a
 * rendered $ needs a Cite state these sums do not have). DownloadCards renders
 * it inside the card grid as the full-width item directly after the
 * p1_era_line_map card (spec §6.4 owner decision), so these cases render the
 * cards. The last two bind the rendered cards to gate 24 leg (s): what they
 * render, the leg accepts, and a summary the page disagrees with, the leg
 * rejects.
 */
import React from "react";
import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { parse } from "node-html-parser";
import { EraMapTable } from "@/components/era-map-table";
import { DownloadCards, type DownloadDataset } from "@/components/download-cards";
import { ERA_DECISIONS, type EraMapEdition, type EraMapSummary } from "@/lib/era-map";
import { runEraMapLeg } from "../../scripts/gates/datatruth.mjs";

function edition(ed: number, chains: number[], facts: number, complete: number): EraMapEdition {
  const lines = chains.map((c) => (c === 0 ? 0 : c + 1));
  const by_decision = Object.fromEntries(
    ERA_DECISIONS.map((d, i) => [d, { chains: chains[i], lines: lines[i], actuals_thousands: 1000 * chains[i] }]),
  ) as EraMapEdition["by_decision"];
  return { edition: ed, fy_actuals: ed - 2, lines: lines.reduce((a, b) => a + b, 0), by_decision, receipts: { facts, complete } };
}

const SUMMARY: EraMapSummary = {
  schema_version: 1,
  actuals_basis: "test",
  receipts_basis: "test",
  editions: [
    edition(2017, [690, 230, 45, 2, 2], 2214, 2107),
    edition(2018, [745, 240, 44, 0, 0], 2349, 2231),
    edition(2019, [768, 189, 32, 0, 0], 2262, 2160),
    edition(2020, [790, 160, 25, 0, 0], 2231, 2140),
    edition(2021, [812, 170, 0, 0, 1], 2298, 2210),
    edition(2022, [820, 150, 0, 0, 0], 2272, 2180),
    edition(2023, [815, 135, 0, 0, 0], 2212, 2120),
  ],
  by_ruling: [],
  totals: Object.fromEntries(ERA_DECISIONS.map((d) => [d, { chains: 0, lines: 0, actuals_thousands: 0 }])) as EraMapSummary["totals"],
};

function recountOf(summary: EraMapSummary) {
  return {
    present: true,
    editions: Object.fromEntries(
      summary.editions.map((e) => [
        String(e.edition),
        {
          lines: e.lines,
          by_decision: Object.fromEntries(
            Object.entries(e.by_decision)
              .filter(([, t]) => t.lines > 0)
              .map(([d, t]) => [d, { chains: t.chains, lines: t.lines }]),
          ),
        },
      ]),
    ),
  };
}

const auditOf = (summary: EraMapSummary) => ({
  books: summary.editions.map((e) => ({ edition: e.edition, exhibit: "P-1", facts: e.receipts.facts, complete: e.receipts.complete })),
});

const INVENTORY: DownloadDataset[] = [
  { name: "budget_lines", row_count: 159903, scope: "One row per budget line.", cited: true },
  { name: "p1_era_line_map", row_count: 6927, scope: "One row per PB2017–PB2023 P-1 display line.", cited: false },
  { name: "dim_programs", row_count: 1936, scope: "One row per program.", cited: true },
];
const cards = (eraMap: EraMapSummary | null) =>
  renderToStaticMarkup(
    <DownloadCards
      builtAt="2026-10-02T01:30:21.066005+00:00"
      inventory={INVENTORY}
      citationsIndex={{ row_count: 125409, scope: "The citation index." }}
      uncitedDatasets={["p1_era_line_map"]}
      eraMap={eraMap}
    />,
  );

const html = cards(SUMMARY);
const root = parse(html);
const cell = (ed: number, key: string) =>
  root.querySelector(`tr[data-era-edition="${ed}"] [data-era-cell="${key}"] [data-era-value]`)?.text;

describe("EraMapTable", () => {
  it("renders one row per edition, in edition order", () => {
    expect(root.querySelectorAll("[data-era-map]")).toHaveLength(1);
    expect(root.querySelectorAll("tr[data-era-edition]").map((r) => r.getAttribute("data-era-edition"))).toEqual(
      ["2017", "2018", "2019", "2020", "2021", "2022", "2023"],
    );
  });

  it("renders the counts, never a dollar figure", () => {
    expect(cell(2017, "lines")).toBe("974");
    expect(cell(2017, "same_program")).toBe("690 codes");
    expect(cell(2017, "history_only")).toBe("230 codes");
    expect(cell(2017, "excluded")).toBe("49 codes");
    expect(cell(2017, "receipts")).toBe("2,107 of 2,214");
    expect(cell(2018, "lines")).toBe("1,032");
    expect(root.querySelector("#era-map")!.toString()).not.toContain("$");
  });

  it("says code, not codes, for one", () => {
    expect(cell(2021, "excluded")).toBe("1 code");
  });

  it("renders directly after the p1_era_line_map card, full width in the card grid", () => {
    const card = root.querySelector('[data-dataset-card="p1_era_line_map"]');
    const next = card?.nextElementSibling;
    expect(next?.getAttribute("id")).toBe("era-map");
    expect(next?.classList.contains("sm:col-span-2")).toBe(true);
    expect(next?.parentNode).toBe(card?.parentNode);
    const alone = parse(renderToStaticMarkup(<EraMapTable summary={SUMMARY} />));
    expect(alone.querySelector("#era-map")?.classList.contains("sm:col-span-2")).toBe(true);
  });

  it("renders no table when the export shipped no summary", () => {
    const bare = parse(cards(null));
    expect(bare.querySelectorAll("[data-era-map]")).toHaveLength(0);
    expect(bare.querySelectorAll("[data-dataset-card]")).toHaveLength(4);
  });

  it("is what gate 24 leg (s) accepts", () => {
    const errors: string[] = [];
    const notes: string[] = [];
    runEraMapLeg(errors, notes, { recount: recountOf(SUMMARY), summary: SUMMARY, audit: auditOf(SUMMARY), html });
    expect(errors).toEqual([]);
    expect(notes.join("\n")).toMatch(/leg s: \/downloads\/ renders all 7 era editions/);
  });

  it("fails gate 24 leg (s) when the summary moves and the page does not", () => {
    const moved = structuredClone(SUMMARY);
    moved.editions[0].receipts.complete = 2108;
    const errors: string[] = [];
    runEraMapLeg(errors, [], { recount: recountOf(moved), summary: moved, audit: auditOf(moved), html });
    expect(errors).toEqual([
      'leg s (/downloads/): PB2017 receipts renders "2,107 of 2,214", era_map_summary.json says "2,108 of 2,214"',
    ]);
  });
});
```

Create `site/scripts/gates/__tests__/era-map-leg.test.mjs`:
```js
/**
 * Gate 24 leg (s) — the era-map table on /downloads/ (families piece 1,
 * Task 19). The page must render exactly json/era_map_summary.json, directly
 * after the p1_era_line_map download card, and the summary must agree with
 * the shipped p1_era_line_map (recounted from the parquet) and with the
 * receipts audit. Every input is injected, so nothing here needs a build or
 * the lake. src/__tests__/era-map-table.test.tsx binds the real components to
 * the same leg.
 */
import { describe, it, expect } from "vitest";
import { runEraMapLeg } from "../datatruth.mjs";

const DECISIONS = ["same_program", "history_only", "exclude_placeholder", "exclude_route_unsafe", "exclude_reused_code"];
const EDITIONS = [2017, 2018, 2019, 2020, 2021, 2022, 2023];

function edition(ed) {
  const chains = [2, 1, 1, 0, 0];
  const by_decision = Object.fromEntries(DECISIONS.map((d, i) => [d, { chains: chains[i], lines: chains[i], actuals_thousands: 0 }]));
  return { edition: ed, fy_actuals: ed - 2, lines: 4, by_decision, receipts: { facts: 1234, complete: 1200 } };
}
const summary = () => ({ schema_version: 1, editions: EDITIONS.map(edition), by_ruling: [], totals: {} });
const recountOf = (s) => ({
  present: true,
  editions: Object.fromEntries(s.editions.map((e) => [String(e.edition), {
    lines: e.lines,
    by_decision: Object.fromEntries(Object.entries(e.by_decision).filter(([, t]) => t.lines > 0).map(([d, t]) => [d, { chains: t.chains, lines: t.lines }])),
  }])),
});
const auditOf = (s) => ({ books: s.editions.map((e) => ({ edition: e.edition, exhibit: "P-1", facts: e.receipts.facts, complete: e.receipts.complete })) });

/** The markup DownloadCards renders, by hand: the card grid with the era
 *  table's section directly after the p1_era_line_map card (with `misplaced`,
 *  after the grid instead). */
function htmlOf(s, { drop, misplaced } = {}) {
  const rows = s.editions.filter((e) => e.edition !== drop).map((e) =>
    `<tr data-era-edition="${e.edition}"><th scope="row">PB${e.edition}</th>` +
    [["lines", "4"], ["same_program", "2 codes"], ["history_only", "1 code"], ["excluded", "1 code"], ["receipts", "1,200 of 1,234"]]
      .map(([k, v]) => `<td data-era-cell="${k}"><span class="t-label">x</span><span data-era-value>${v}</span></td>`).join("") +
    "</tr>").join("");
  const table = `<section id="era-map" class="sm:col-span-2"><table data-era-map><tbody>${rows}</tbody></table></section>`;
  const card = (name) => `<div data-dataset-card="${name}"><span>${name}</span></div>`;
  return `<main><div class="grid gap-4 sm:grid-cols-2">${card("budget_lines")}${card("p1_era_line_map")}` +
    `${misplaced ? "" : table}${card("citations")}</div>${misplaced ? table : ""}</main>`;
}

function run(over = {}) {
  const s = over.summary ?? summary();
  const errors = [];
  const notes = [];
  runEraMapLeg(errors, notes, {
    recount: over.recount ?? recountOf(s),
    summary: s,
    audit: over.audit ?? auditOf(s),
    html: "html" in over ? over.html : htmlOf(s),
  });
  return { errors, notes };
}

describe("gate 24 leg (s)", () => {
  it("passes when page, summary, map and audit agree", () => {
    const { errors, notes } = run();
    expect(errors).toEqual([]);
    expect(notes).toHaveLength(1);
  });

  it("fails when the map parquet is not shipped", () => {
    expect(run({ recount: { present: false } }).errors[0]).toMatch(/p1_era_line_map\.parquet is not shipped/);
  });

  it("fails when the summary is missing", () => {
    const errors = [];
    runEraMapLeg(errors, [], { recount: recountOf(summary()), summary: null, audit: auditOf(summary()), html: htmlOf(summary()) });
    expect(errors[0]).toMatch(/era_map_summary\.json is missing/);
  });

  it("fails when the summary does not cover exactly PB2017–PB2023", () => {
    const s = summary();
    s.editions.pop();
    expect(run({ summary: s, html: htmlOf(s) }).errors[0]).toMatch(/covers editions \[2017,2018,2019,2020,2021,2022\]/);
  });

  it("fails when the summary disagrees with the shipped map", () => {
    const s = summary();
    const recount = recountOf(s);
    recount.editions["2019"].by_decision.history_only.chains = 2;
    expect(run({ summary: s, recount }).errors).toEqual([
      "leg s: PB2019 history_only summary says 1 chains / 1 lines, the shipped map holds 2 / 1",
    ]);
  });

  it("fails when receipts disagree with the audit", () => {
    const s = summary();
    const audit = auditOf(s);
    audit.books[3].complete = 1199;
    expect(run({ summary: s, audit }).errors).toEqual([
      "leg s: PB2020 receipts say 1200 of 1234, the receipts audit has 1199 of 1234",
    ]);
  });

  it("fails when /downloads/ is not built", () => {
    expect(run({ html: null }).errors).toEqual(["leg s: /downloads/ not built — run npm run build"]);
  });

  it("fails when the page drops an edition's row", () => {
    const s = summary();
    expect(run({ summary: s, html: htmlOf(s, { drop: 2022 }) }).errors[0]).toMatch(/renders rows for \[2017,2018,2019,2020,2021,2023\]/);
  });

  it("fails when a rendered cell differs from the summary", () => {
    const s = summary();
    s.editions[6].by_decision.same_program = { chains: 3, lines: 3, actuals_thousands: 0 };
    s.editions[6].lines = 5;
    const errors = run({ summary: s, html: htmlOf(s) }).errors;
    expect(errors).toContain('leg s (/downloads/): PB2023 same_program renders "2 codes", era_map_summary.json says "3 codes"');
    expect(errors).toContain('leg s (/downloads/): PB2023 lines renders "4", era_map_summary.json says "5"');
  });

  it("fails when the table is not directly under the p1_era_line_map card", () => {
    const s = summary();
    expect(run({ summary: s, html: htmlOf(s, { misplaced: true }) }).errors).toEqual([
      "leg s (/downloads/): the era table is not the element directly after the p1_era_line_map card",
    ]);
  });
});
```

Create `site/src/__tests__/methodology-pending-ledger.test.ts` (the third point of Step 19):
```ts
/**
 * /methodology/'s citation-tier paragraph names the pending ledger's one
 * dataset (families piece 1, Task 19; the owner's decision of Step 19).
 * p1_era_line_map ships on the uncited ledger (spec §4.4: its rows are
 * decisions, not money), so its /data/ row shows "tier pending" and "the
 * pending ledger is empty" stops being true when it ships. The clause is
 * replaced at its exact rendered length: /methodology/ sits near its gate-1
 * ceiling.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "methodology", "page.tsx");
const OLD = "every published dataset carries a citation tier (the pending ledger is empty)";
const NEW = "only p1_era_line_map is on the pending ledger, as it holds no amounts to cite";

/** The citation-tier definition as rendered: tags drop, whitespace collapses. */
function rendered(): string {
  const src = fs.readFileSync(PAGE, "utf8");
  const a = src.indexOf("<strong>Citation tier pending</strong>");
  expect(a, "citation-tier definition not found").toBeGreaterThan(-1);
  const b = src.indexOf("</p>", a);
  return src.slice(a, b).replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
}

describe("/methodology/ pending-ledger clause", () => {
  it("names p1_era_line_map as the pending ledger's only dataset", () => {
    expect(rendered()).toContain(`As of this build ${NEW}; the state remains defined`);
  });

  it("no longer says the ledger is empty", () => {
    expect(rendered()).not.toContain("the pending ledger is empty");
  });

  it("keeps the clause's rendered length", () => {
    expect(Buffer.byteLength(NEW)).toBe(Buffer.byteLength(OLD));
    expect(Buffer.byteLength(NEW)).toBe(77);
  });
});
```

Run:
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/duckdb-helpers.test.ts src/__tests__/explorer-era-map-preset.test.ts src/__tests__/era-map-table.test.tsx scripts/gates/__tests__/era-map-leg.test.mjs src/__tests__/methodology-pending-ledger.test.ts
cd .. && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_explorer_era_map_preset.py -q
```
Expected: FAIL. `duckdb-helpers`: 3 failures (`expected [ 'budget_lines', …(15) ] to have a length of 17 but got 16`,
and twice `… to include 'p1_era_line_map'`); the preset test: 3 failures, the first `expected [ 'Preview (first 50
rows)' ] to deeply equal [ 'Decisions by edition', …(1) ]` (the default branch answers); `era-map-table.test.tsx`:
`Error: Failed to resolve import "@/components/era-map-table" from "src/__tests__/era-map-table.test.tsx". Does the
file exist?`; `era-map-leg.test.mjs`: all 10 cases with `TypeError: (0 , runEraMapLeg) is not a function`;
`methodology-pending-ledger.test.ts`: `2 failed | 1 passed` ("names p1_era_line_map …" and "no longer says the ledger
is empty"; the length case passes, both clauses are 77 bytes); pytest:
`ValueError: substring not found` from `src.index(CASE)`.

- [ ] **Step 22: Register the dataset name, and name it on the pending ledger in `/methodology/`**

In `site/src/lib/dataset-names.ts`, before (`:32-35`):
```ts
  "jbook_details",
  "jbook_narratives",
] as const;
```
After:
```ts
  "jbook_details",
  "jbook_narratives",
  "p1_era_line_map",
] as const;
```

Registering the map puts it on the uncited ledger, so the `/methodology/` clause that calls that ledger empty changes
in the same step, at equal length (Step 19, point 3). In `site/src/app/methodology/page.tsx`, before (`:1025-1028`):
```tsx
                  complete. As of this build every published dataset carries a
                  citation tier (the pending ledger is empty); the state remains
                  defined — and gate-enforced — for future datasets that ship
                  before their citations do.
```
After:
```tsx
                  complete. As of this build only p1_era_line_map is on the
                  pending ledger, as it holds no amounts to cite; the state
                  remains defined — and gate-enforced — for future datasets that
                  ship before their citations do.
```
Weighed on a production-origin scratch build with Part A applied (2026-10-02): `/methodology/` 161,354 / 45,340, the
same raw bytes as Part A's stamp and gzip within build-ID noise (60 gzip bytes left under 45,400). Task 21's S4 build
re-measures the stamp.

- [ ] **Step 23: Add the Explorer presets**

In `site/src/components/explorer.tsx`, before (`:160-165`):
```tsx
ORDER BY pb_edition
          `),
        },
      ];

    case "fct_influence":
```
After:
```tsx
ORDER BY pb_edition
          `),
        },
      ];

    case "p1_era_line_map":
      // Families piece 1 (spec 2026-10-02 §4.4). One row per PB2017–PB2023
      // P-1 display line and the dated decision that joins it to a program,
      // keeps it as history, or excludes it. No amounts: the figures live in
      // budget_lines_decade under the same era_key. A chain is one decision
      // (decision_id); owner review batches carry ruling R-DEC-ERA-B<n>.
      return [
        {
          label: "Decisions by edition",
          sql: t(`
SELECT edition, decision,
       COUNT(DISTINCT decision_id) AS chains,
       COUNT(*) AS lines
FROM 'p1_era_line_map.parquet'
GROUP BY edition, decision
ORDER BY edition, decision
          `),
        },
        {
          label: "Lines decided in owner review batches",
          sql: t(`
SELECT edition, era_key, line_item_code, filed_title,
       program_key, decision, ruling
FROM 'p1_era_line_map.parquet'
WHERE ruling LIKE 'R-DEC-ERA-B%'
ORDER BY line_item_code, edition, era_key
LIMIT 50
          `),
        },
      ];

    case "fct_influence":
```

- [ ] **Step 24: Create `site/src/lib/era-map.ts`**

```ts
/**
 * The era-map summary's shape and its one rendering rule (families piece 1,
 * spec 2026-10-02 §4.4, §6.4). UNIVERSAL (no server-only import), so the
 * component and its tests share it. Gate 24 leg (s) formats the same cells
 * with its OWN code, never this module, so a change here has to agree with
 * the gate to pass.
 *
 * Counts only. Dollars stay in json/era_map_summary.json: a rendered $ must
 * carry a Cite state (gate 2), and these per-decision sums have none.
 */
import { formatCount } from "./format";

export const ERA_DECISIONS = [
  "same_program",
  "history_only",
  "exclude_placeholder",
  "exclude_route_unsafe",
  "exclude_reused_code",
] as const;
export type EraDecision = (typeof ERA_DECISIONS)[number];

/** The decisions the "Excluded" column sums. */
export const ERA_EXCLUDED: readonly EraDecision[] = [
  "exclude_placeholder",
  "exclude_route_unsafe",
  "exclude_reused_code",
];

export interface EraMapTally {
  chains: number;
  lines: number;
  actuals_thousands: number;
}

export interface EraMapEdition {
  edition: number;
  fy_actuals: number;
  lines: number;
  by_decision: Record<EraDecision, EraMapTally>;
  receipts: { facts: number; complete: number };
}

export interface EraMapRulingTally extends EraMapTally {
  ruling: string;
  decision: EraDecision;
}

export interface EraMapSummary {
  schema_version: 1;
  actuals_basis: string;
  receipts_basis: string;
  editions: EraMapEdition[];
  by_ruling: EraMapRulingTally[];
  totals: Record<EraDecision, EraMapTally>;
}

export const ERA_MAP_COLUMNS = [
  { key: "lines", label: "Lines" },
  { key: "same_program", label: "Same program" },
  { key: "history_only", label: "History only" },
  { key: "excluded", label: "Excluded" },
  { key: "receipts", label: "PDF receipts" },
] as const;
export type EraMapColumn = (typeof ERA_MAP_COLUMNS)[number]["key"];

const codes = (n: number): string => `${formatCount(n)} ${n === 1 ? "code" : "codes"}`;

/** One edition's cells, in column order. */
export function eraMapCells(e: EraMapEdition): { key: EraMapColumn; label: string; value: string }[] {
  const chains = (d: EraDecision): number => e.by_decision[d]?.chains ?? 0;
  const values: Record<EraMapColumn, string> = {
    lines: formatCount(e.lines),
    same_program: codes(chains("same_program")),
    history_only: codes(chains("history_only")),
    excluded: codes(ERA_EXCLUDED.reduce((sum, d) => sum + chains(d), 0)),
    receipts: `${formatCount(e.receipts.complete)} of ${formatCount(e.receipts.facts)}`,
  };
  return ERA_MAP_COLUMNS.map((c) => ({ key: c.key, label: c.label, value: values[c.key] }));
}
```

- [ ] **Step 25: Add the loader to `site/src/lib/data.ts`**

Imports, before (`:29-30`):
```ts
import type { LineageBlock } from "./lineage";
import type { LineageFlowPayload } from "./lineage-flow";
```
After:
```ts
import type { LineageBlock } from "./lineage";
import type { LineageFlowPayload } from "./lineage-flow";
import type { EraMapSummary } from "./era-map";
```
After `getDatasetManifest` (after `:764`), insert:
```ts

// ── era_map_summary.json (families piece 1, spec 2026-10-02 §6.4) ────────────

/**
 * The era-map decision counts /downloads/ renders under the p1_era_line_map
 * card. Null when the export shipped no map (an export from before families
 * piece 1): the page then renders no table, and gate 24 leg (s) fails,
 * because the map dataset and this summary ship together.
 */
export function getEraMapSummary(): EraMapSummary | null {
  if (!existsSync(join(jsonDir(), "era_map_summary.json"))) return null;
  const s = readJson<EraMapSummary>("era_map_summary.json");
  if (s.schema_version !== 1) {
    throw new Error(
      `[govbudget/data] era_map_summary.json has schema_version=${s.schema_version}, expected 1. ` +
        `Re-run "uv run python -m govbudget export-site" to regenerate sidecars.`,
    );
  }
  return s;
}
```

- [ ] **Step 26: Create `site/src/components/era-map-table.tsx`**

```tsx
/**
 * The era-map decision table on /downloads/ (families piece 1, spec
 * 2026-10-02 §6.4), directly under the p1_era_line_map download card:
 * DownloadCards renders it inside its card grid as the item right after that
 * card, spanning both columns from `sm` up (`sm:col-span-2`); gate 24 leg (s)
 * checks that position.
 *
 * Placed here by the owner's decision (spec §6.4 correction): as built it
 * weighed +2,393 gzip on /coverage/ (292 left) and +3,647 on /data/ (2,083
 * left after the inventory hoist), and no ceiling is raised; /downloads/
 * carries no page-weight ceiling (+2,354 gzip here, measured with the table
 * below the card grid; gate 1 has no /downloads/ entry, so no step re-weighs
 * it). Counts only: dollars stay in
 * json/era_map_summary.json (see lib/era-map). Below `sm` each row becomes a
 * card (the /data/ treatment) with its field labels; the gate hooks
 * ([data-era-edition], [data-era-cell], [data-era-value]) are what gate 24
 * leg (s) reads.
 */
import { ERA_MAP_COLUMNS, eraMapCells, type EraMapSummary } from "@/lib/era-map";

export function EraMapTable({ summary }: { summary: EraMapSummary }) {
  return (
    <section id="era-map" aria-labelledby="era-map-heading" className="sm:col-span-2">
      <h2 id="era-map-heading" className="mb-3">
        Procurement lines before PB2024
      </h2>
      <p className="mb-4 max-w-2xl text-sm leading-7 text-muted-foreground">
        Each PB2017–PB2023 P-1 line reaches a program page only through a dated
        decision on the budget line code it printed, published in the
        p1_era_line_map dataset above. For each edition the table counts the
        lines, the codes each decision covers and the era figures cited on the
        site that carry a complete PDF receipt.
      </p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table data-era-map className="min-w-full text-sm">
          <caption className="sr-only">
            Era P-1 lines, codes per decision and complete PDF receipts, by
            President&apos;s Budget edition.
          </caption>
          <thead className="hidden sm:table-header-group">
            <tr className="border-b border-border bg-muted/50">
              <th scope="col" className="px-4 py-2 text-left font-semibold text-muted-foreground">
                Edition
              </th>
              {ERA_MAP_COLUMNS.map((c) => (
                <th key={c.key} scope="col" className="px-4 py-2 text-right font-semibold text-muted-foreground">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {summary.editions.map((e) => (
              <tr
                key={e.edition}
                data-era-edition={e.edition}
                className="block border-b border-border py-3 last:border-0 sm:table-row sm:py-0"
              >
                <th scope="row" className="block px-4 text-left font-medium text-foreground sm:table-cell sm:py-2">
                  {`PB${e.edition}`}
                </th>
                {eraMapCells(e).map((c) => (
                  <td
                    key={c.key}
                    data-era-cell={c.key}
                    className="block px-4 pt-1 tabular-nums text-muted-foreground sm:table-cell sm:py-2 sm:text-right"
                  >
                    <span className="t-label mb-0.5 block sm:hidden">{c.label}</span>
                    <span data-era-value>{c.value}</span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 27: Render it in the download-card grid, directly after the `p1_era_line_map` card**

Spec §6.4's owner decision puts the table "directly under the `p1_era_line_map` download card", so it renders inside
`DownloadCards`' grid as the full-width item that follows that card (pre-flight ruling 2026-10-03), not below the
whole grid. `EraMapTable` is pure (no hooks, no server-only import), so the client component can render it; the page
passes the summary in.

In `site/src/components/download-cards.tsx`, imports, before:
```tsx
import React from "react";
import { useAssetUrl, useAssetConfigResolved } from "@/components/asset-config";
```
After:
```tsx
import React from "react";
import { useAssetUrl, useAssetConfigResolved } from "@/components/asset-config";
import { EraMapTable } from "@/components/era-map-table";
import type { EraMapSummary } from "@/lib/era-map";

/** The dataset whose card the era-map table follows (families piece 1). */
const ERA_MAP_DATASET = "p1_era_line_map";
```
Props, before:
```tsx
  workbookCount,
  uncitedDatasets = [],
}: {
```
After:
```tsx
  workbookCount,
  uncitedDatasets = [],
  eraMap = null,
}: {
```
Before:
```tsx
  uncitedDatasets?: string[];
}) {
```
After:
```tsx
  uncitedDatasets?: string[];
  /**
   * json/era_map_summary.json (lib/data getEraMapSummary; families piece 1).
   * When present, the era-map table renders as the full-width grid item
   * directly after the p1_era_line_map card (spec §6.4 owner decision).
   */
  eraMap?: EraMapSummary | null;
}) {
```
The card grid, before:
```tsx
        {DATASETS.map((ds) => (
          <div
            key={ds.name}
            {...(degraded ? { "aria-disabled": true } : {})}
```
After:
```tsx
        {DATASETS.map((ds) => (
          <React.Fragment key={ds.name}>
          <div
            data-dataset-card={ds.name}
            {...(degraded ? { "aria-disabled": true } : {})}
```
Before:
```tsx
              {ds.name}.parquet
            </a>
          </div>
        ))}
      </div>
```
After:
```tsx
              {ds.name}.parquet
            </a>
          </div>
          {ds.name === ERA_MAP_DATASET && eraMap && <EraMapTable summary={eraMap} />}
          </React.Fragment>
        ))}
      </div>
```

In `site/src/app/downloads/page.tsx` (the component import stays out of the page), `:3`, before:
```tsx
import { citationsIndexOf, getDatasetManifest, getSiteMeta } from "@/lib/data";
```
After:
```tsx
import { citationsIndexOf, getDatasetManifest, getEraMapSummary, getSiteMeta } from "@/lib/data";
```
Before (`:73`):
```tsx
  const manifest = getDatasetManifest();
```
After:
```tsx
  const manifest = getDatasetManifest();
  // Families piece 1: the era-map decision table renders in the card grid,
  // directly after the p1_era_line_map card (owner decision, spec §6.4
  // correction: /coverage/ and /data/ had no room).
  const eraMap = getEraMapSummary();
```
Before (`:143-144`):
```tsx
            uncitedDatasets={meta.uncited_datasets ?? []}
          />
```
After:
```tsx
            uncitedDatasets={meta.uncited_datasets ?? []}
            eraMap={eraMap}
          />
```

- [ ] **Step 28: Create the gate's independent recount, `site/scripts/gates/eramap-recompute.py`**

```python
#!/usr/bin/env python3
"""eramap-recompute.py — gate 24 leg (s) truth helper (families piece 1).

Recounts, from data/site/data/p1_era_line_map.parquet itself (never from
era_map_summary.json, the artifact under test), each era edition's line count
and, per decision, its chains (distinct decision_id) and lines.

Output (stdout, JSON):
  {"present": true, "editions": {"2017": {"lines": 969,
     "by_decision": {"same_program": {"chains": 690, "lines": 701}, ...}}, ...}}
  {"present": false} when the parquet is not shipped.
"""

import json
import sys
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[3]
PARQUET = REPO / "data" / "site" / "data" / "p1_era_line_map.parquet"


def main() -> int:
    if not PARQUET.is_file():
        print(json.dumps({"present": False}))
        return 0
    con = duckdb.connect()
    try:
        rows = con.execute(
            "select edition, decision, count(*), count(distinct decision_id)"
            " from read_parquet(?) group by edition, decision"
            " order by edition, decision",
            [PARQUET.as_posix()],
        ).fetchall()
    finally:
        con.close()
    editions: dict[str, dict] = {}
    for edition, decision, lines, chains in rows:
        e = editions.setdefault(str(edition), {"lines": 0, "by_decision": {}})
        e["lines"] += int(lines)
        e["by_decision"][decision] = {"chains": int(chains), "lines": int(lines)}
    print(json.dumps({"present": True, "editions": editions}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 29: Add leg (s) to `site/scripts/gates/datatruth.mjs`**

Header, before (`:211-214`):
```js
 *      any sampled cell has no rows in the lake. (The brief called this leg
 *      (o); that letter was taken by the hand-adjudication leg above and
 *      (p)/(q) are reserved, so the by-year leg is (r).)
 *
```
After:
```js
 *      any sampled cell has no rows in the lake. (The brief called this leg
 *      (o); that letter was taken by the hand-adjudication leg above and
 *      (p)/(q) are reserved, so the by-year leg is (r).)
 *  (s) ERA-MAP DECISIONS (families piece 1, spec 2026-10-02 §6.4). /downloads/
 *      renders, directly under the p1_era_line_map card (the card's next
 *      element in the card grid), one row per PB2017–PB2023
 *      edition: its P-1 lines, the chains ("codes") each decision covers and
 *      how many cited era cells carry a complete PDF receipt. This leg
 *      requires the rendered cells to equal json/era_map_summary.json, the
 *      summary's lines and chains to equal an independent recount of the
 *      shipped parquet (eramap-recompute.py), and its receipt figures to
 *      equal the receipts audit's P-1 book for that edition. The map shipping
 *      without the summary, or not shipping at all, is a stale export and
 *      fails. See leg s's own block at the bottom.
 *
```
Wiring, before (`:776-779`):
```js
  // ── leg r: district by-year cells vs the lake (ROADMAP #6) ────────────────
  runDistrictYearLeg(errors, notes);

  return { pass: errors.length === 0, errors, notes };
```
After:
```js
  // ── leg r: district by-year cells vs the lake (ROADMAP #6) ────────────────
  runDistrictYearLeg(errors, notes);

  // ── leg s: era-map decisions on /downloads/ (families piece 1) ────────────
  runEraMapLeg(errors, notes);

  return { pass: errors.length === 0, errors, notes };
```
Append at the end of the file:
```js

// ═══════════════════════════════════════════════════════════════════════════
// leg s — era-map decisions on /downloads/ (families piece 1, spec §6.4)
// ═══════════════════════════════════════════════════════════════════════════

/** The P-1 editions the era map covers (spec 2026-10-02 §4.4). */
const ERA_EDITIONS = [2017, 2018, 2019, 2020, 2021, 2022, 2023];
/** The decisions the rendered "Excluded" column sums (spec §4.3). */
const ERA_EXCLUDED = ["exclude_placeholder", "exclude_route_unsafe", "exclude_reused_code"];
/** Where the table renders: /coverage/ and /data/ had no room under their ceilings. */
const ERA_PAGE = "/downloads/";

function readJsonOrNull(p) {
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

/** Independent recount of the shipped map (eramap-recompute.py, DuckDB). */
function recomputeEraMap() {
  const script = path.join(__dirname, "eramap-recompute.py");
  const res = spawnSync("uv", ["run", "python", script], {
    cwd: repoRoot,
    encoding: "utf8",
    timeout: 120000,
    maxBuffer: 8 * 1024 * 1024,
  });
  if (res.status !== 0) {
    throw new Error(
      `eramap-recompute.py failed (status ${res.status}): ${(res.stderr || "").slice(-800)}`,
    );
  }
  return JSON.parse(res.stdout);
}

/** This leg's own rendering of one edition's cells, written apart from
 *  src/lib/era-map.ts on purpose: a change there has to agree with this. */
function eraExpectedCells(e) {
  const g = (n) => Number(n).toLocaleString("en-US");
  const codes = (n) => `${g(n)} ${n === 1 ? "code" : "codes"}`;
  const chains = (d) => e.by_decision?.[d]?.chains ?? 0;
  return {
    lines: g(e.lines),
    same_program: codes(chains("same_program")),
    history_only: codes(chains("history_only")),
    excluded: codes(ERA_EXCLUDED.reduce((s, d) => s + chains(d), 0)),
    receipts: `${g(e.receipts?.complete ?? 0)} of ${g(e.receipts?.facts ?? 0)}`,
  };
}

/**
 * Leg (s). Injectable like legs m/n/o: `injected` = {recount, summary, audit,
 * html} replaces the recount subprocess, the two JSON files and the built
 * page (scripts/gates/__tests__/era-map-leg.test.mjs,
 * src/__tests__/era-map-table.test.tsx).
 */
export function runEraMapLeg(errors, notes, injected) {
  const before = errors.length;
  let recount;
  try {
    recount = injected ? injected.recount : recomputeEraMap();
  } catch (e) {
    errors.push(`leg s: ${e.message}`);
    return;
  }
  const summary = injected
    ? injected.summary
    : readJsonOrNull(path.join(jsonDir, "era_map_summary.json"));
  const audit = injected
    ? injected.audit
    : readJsonOrNull(path.join(jsonDir, "budget_pdf_receipts_audit.json"));
  const htmlPath = htmlFor(ERA_PAGE);
  const html = injected
    ? injected.html
    : fs.existsSync(htmlPath)
      ? fs.readFileSync(htmlPath, "utf8")
      : null;

  if (!recount?.present) {
    errors.push(
      "leg s: data/site/data/p1_era_line_map.parquet is not shipped — families piece 1 " +
        "publishes the era map with every export, so this is a stale export",
    );
    return;
  }
  if (!summary) {
    errors.push(
      "leg s: data/site/json/era_map_summary.json is missing while p1_era_line_map.parquet " +
        "ships — the export's receipts step writes it (cli._export_budget_pdf_evidence)",
    );
    return;
  }
  const editions = summary.editions ?? [];
  const eds = editions.map((e) => e.edition);
  if (JSON.stringify(eds) !== JSON.stringify(ERA_EDITIONS)) {
    errors.push(
      `leg s: era_map_summary.json covers editions ${JSON.stringify(eds)}, expected ${JSON.stringify(ERA_EDITIONS)}`,
    );
  }

  // (s1) the summary agrees with the shipped map, recounted from the parquet
  for (const e of editions) {
    const t = recount.editions?.[String(e.edition)] ?? { lines: 0, by_decision: {} };
    if (t.lines !== e.lines) {
      errors.push(`leg s: PB${e.edition} summary says ${e.lines} lines, the shipped map holds ${t.lines}`);
    }
    const decisions = new Set([...Object.keys(t.by_decision ?? {}), ...Object.keys(e.by_decision ?? {})]);
    for (const d of decisions) {
      const want = t.by_decision?.[d] ?? { chains: 0, lines: 0 };
      const got = e.by_decision?.[d] ?? { chains: 0, lines: 0 };
      if (want.chains !== got.chains || want.lines !== got.lines) {
        errors.push(
          `leg s: PB${e.edition} ${d} summary says ${got.chains} chains / ${got.lines} lines, ` +
            `the shipped map holds ${want.chains} / ${want.lines}`,
        );
      }
    }
  }

  // (s2) receipt completeness agrees with the receipts audit's P-1 books
  if (!audit) {
    errors.push("leg s: data/site/json/budget_pdf_receipts_audit.json is missing — receipt completeness is unverifiable");
  }
  const books = new Map(
    (audit?.books ?? []).filter((b) => b.exhibit === "P-1").map((b) => [b.edition, b]),
  );
  for (const e of editions) {
    const b = books.get(e.edition) ?? { facts: 0, complete: 0 };
    if (e.receipts?.facts !== b.facts || e.receipts?.complete !== b.complete) {
      errors.push(
        `leg s: PB${e.edition} receipts say ${e.receipts?.complete} of ${e.receipts?.facts}, ` +
          `the receipts audit has ${b.complete} of ${b.facts}`,
      );
    }
  }

  // (s3) the page renders exactly the summary
  if (!html) {
    errors.push(`leg s: ${ERA_PAGE} not built — run npm run build`);
    return;
  }
  const root = parse(html, { comment: false });
  for (const el of root.querySelectorAll("script, style, noscript, template")) el.remove();
  const tables = root.querySelectorAll("[data-era-map]");
  if (tables.length !== 1) {
    errors.push(`leg s (${ERA_PAGE}): ${tables.length} [data-era-map] tables rendered, expected exactly 1`);
    return;
  }
  // (s4) where it renders: directly under the p1_era_line_map download card
  // (spec §6.4 owner decision), i.e. the card's next element is the table's
  // section, a full-width item of the same card grid.
  const card = root.querySelector('[data-dataset-card="p1_era_line_map"]');
  const next = card ? card.nextElementSibling : null;
  if (!card) {
    errors.push(`leg s (${ERA_PAGE}): no p1_era_line_map download card ([data-dataset-card="p1_era_line_map"])`);
  } else if (next?.getAttribute("id") !== "era-map" || next.querySelectorAll("[data-era-map]").length !== 1) {
    errors.push(`leg s (${ERA_PAGE}): the era table is not the element directly after the p1_era_line_map card`);
  }
  const rows = tables[0].querySelectorAll("tr[data-era-edition]");
  const rendered = rows.map((r) => Number(r.getAttribute("data-era-edition")));
  if (JSON.stringify(rendered) !== JSON.stringify(eds)) {
    errors.push(
      `leg s (${ERA_PAGE}): renders rows for ${JSON.stringify(rendered)}, era_map_summary.json has ${JSON.stringify(eds)}`,
    );
  }
  for (const e of editions) {
    const row = rows.find((r) => r.getAttribute("data-era-edition") === String(e.edition));
    if (!row) continue;
    for (const [cell, want] of Object.entries(eraExpectedCells(e))) {
      const el = row.querySelector(`[data-era-cell="${cell}"] [data-era-value]`);
      const got = el ? norm(el.text) : null;
      if (got !== want) {
        errors.push(
          `leg s (${ERA_PAGE}): PB${e.edition} ${cell} renders ${JSON.stringify(got)}, ` +
            `era_map_summary.json says ${JSON.stringify(want)}`,
        );
      }
    }
  }
  if (errors.length === before) {
    notes.push(
      `leg s: ${ERA_PAGE} renders all ${rows.length} era editions exactly as era_map_summary.json, ` +
        "which agrees with the shipped p1_era_line_map and the receipts audit ✓",
    );
  }
}
```

- [ ] **Step 30: Run the site and Python tests, lint and typecheck**

Run:
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && npx vitest run src/__tests__/duckdb-helpers.test.ts src/__tests__/explorer-era-map-preset.test.ts src/__tests__/era-map-table.test.tsx scripts/gates/__tests__/era-map-leg.test.mjs scripts/gates/__tests__/source-cadence.test.mjs src/__tests__/explorer-influence-preset.test.ts src/__tests__/methodology-pending-ledger.test.ts src/__tests__/methodology-era-sentence.test.ts
npx eslint src/lib/era-map.ts src/components/era-map-table.tsx src/components/download-cards.tsx src/app/downloads/page.tsx src/app/data/page.tsx src/app/methodology/page.tsx src/lib/data.ts src/lib/dataset-names.ts src/components/explorer.tsx scripts/gates/datatruth.mjs scripts/computed-style-snapshot.mjs
npx tsc --noEmit -p .
cd .. && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_explorer_era_map_preset.py tests/test_explorer_influence_preset.py -q
```
Expected: vitest `Test Files  8 passed (8)`, `Tests  75 passed (75)` (duckdb-helpers 23, explorer-era-map-preset 4,
era-map-table 7, era-map-leg 10, source-cadence 17, explorer-influence-preset 6, methodology-pending-ledger 3, and Part
A's methodology-era-sentence 5, which must still pass beside the second clause); eslint prints nothing (exit 0);
`tsc` exits 0; pytest `3 passed` for the new file (the influence preset file passes or skips as before, it needs the
shipped `fct_influence.parquet`). The site is not rebuilt here: against today's export the `/data/` registry check
throws (`registered but not shipped: p1_era_line_map`) by design; Task 21's S4 snapshot is the first build (contract
issue 6).

- [ ] **Step 31: Commit Part C**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/site/src/lib/dataset-names.ts GovBudget/site/src/components/explorer.tsx GovBudget/site/src/lib/era-map.ts GovBudget/site/src/lib/data.ts GovBudget/site/src/components/era-map-table.tsx GovBudget/site/src/components/download-cards.tsx GovBudget/site/src/app/downloads/page.tsx GovBudget/site/src/app/methodology/page.tsx GovBudget/site/src/__tests__/methodology-pending-ledger.test.ts GovBudget/site/scripts/gates/eramap-recompute.py GovBudget/site/scripts/gates/datatruth.mjs GovBudget/site/src/__tests__/duckdb-helpers.test.ts GovBudget/site/src/__tests__/explorer-era-map-preset.test.ts GovBudget/site/src/__tests__/era-map-table.test.tsx GovBudget/site/scripts/gates/__tests__/era-map-leg.test.mjs GovBudget/tests/test_explorer_era_map_preset.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(site): register p1_era_line_map (named on the pending ledger in /methodology/), Explorer presets, /downloads/ era table and gate 24 leg (s) (families piece 1, Task 19c)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
