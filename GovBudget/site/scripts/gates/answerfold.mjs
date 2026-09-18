/**
 * gate — answerfold_gate (Phase 5C, G6)
 *
 * Goal 5 contract: program pages answer three questions ABOVE THE FOLD —
 * what is this / what changed / who gets the money.
 *
 * Checks (live, Playwright):
 * 1. Sample 10 program slugs from out/program/: the first 5 (sorted) plus 5
 *    crosswalked programs that have a flows sidecar (data/site/json/flows).
 * 2. For each sampled page, at BOTH 1440×900 and 390×844, all three
 *    [data-testid^="answer-"] elements (answer-what / answer-changed /
 *    answer-who) must be present, visible, and fully inside the initial
 *    viewport: boundingBox().y + height < viewport.height (no scrolling).
 *
 * 3. INDEX-FOLD LEG (ROADMAP.md:1606-1610, round-3 judging: "the explanatory
 *    prose demoted below the data it qualifies on five index pages"). At the
 *    same two viewports, on each of INDEX_FOLD_PAGES, the first data ROW
 *    inside that page's [data-first-data] block must start inside the initial
 *    viewport. The assertion is position, not prose length: a byte budget on
 *    caveat text is a style opinion, while "a reader sees data without
 *    scrolling" is the thing the judging actually asked for.
 *
 * FLOOR (2026-09-18, DO NOT LOWER): the two viewports are 1440x900 and
 * 390x844 and the test is `top < height` at both. It is never relaxed into a
 * per-page allowance or a taller notional viewport — a page that regresses
 * moves a block below its data, the way these five did.
 *
 * Export: runAnswerfoldGate({ baseUrl }) → { pass, errors, notes },
 *         INDEX_FOLD_PAGES, indexFoldFindings(rows)
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, "..", "..");
const outProgramDir = path.resolve(siteRoot, "out", "program");
const flowsDir = path.resolve(siteRoot, "..", "data", "site", "json", "flows");

const VIEWPORTS = [
  { width: 1440, height: 900 },
  { width: 390, height: 844 },
];

const TESTIDS = ["answer-what", "answer-changed", "answer-who"];

/**
 * Sample 10 program slugs: first 5 sorted from out/program/ plus the first 5
 * flow-sidecar slugs (sorted) that have built pages and aren't already in
 * the first set.
 */
function sampleSlugs() {
  const built = fs
    .readdirSync(outProgramDir, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name)
    .sort();
  const first5 = built.slice(0, 5);

  let flowSlugs = [];
  if (fs.existsSync(flowsDir)) {
    flowSlugs = fs
      .readdirSync(flowsDir)
      .filter((f) => f.endsWith(".json"))
      .map((f) => f.replace(".json", ""))
      .sort();
  }
  const builtSet = new Set(built);
  const flow5 = flowSlugs
    .filter((s) => builtSet.has(s) && !first5.includes(s))
    .slice(0, 5);

  return [...first5, ...flow5];
}

/**
 * The five index pages whose explanatory prose outran their data. Chosen by
 * measurement (2026-09-10): these five put their first data row 750-1,494px
 * down the page at 1440x900/390x844, against a first row well inside the fold
 * on every other index page.
 */
export const INDEX_FOLD_PAGES = [
  "/companies/",
  "/district/",
  "/years/",
  "/lineage/",
  "/coverage/",
];

/** Inside [data-first-data], the element that IS the first row of data. */
const FIRST_DATA_IN = "tbody tr, [data-lineage-edge]";

/**
 * The same thing, scoped, so the measurement can WAIT for it. /years/ is a
 * client island that fetches its grid, so at `load` its block holds a loading
 * placeholder and no row; measuring then would read a near-empty wrapper and
 * pass vacuously. The wait is best-effort — a page that never renders a row
 * still falls through to the block itself, and a missing block is still a
 * failure below.
 */
const FIRST_DATA_WAIT = FIRST_DATA_IN.split(",")
  .map((sel) => `[data-first-data] ${sel.trim()}`)
  .join(", ");

/**
 * Round-3 judging leftover (ROADMAP.md:1606-1610): "the explanatory prose
 * demoted below the data it qualifies on five index pages". The durable
 * assertion is not a prose budget — it is that the page's first data ROW is
 * inside the initial viewport at both widths, the same measurement this gate
 * already makes for the three program-page answers. `top` is null when the
 * page declares no [data-first-data]; that is a failure, never a skip.
 */
export function indexFoldFindings(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return ["index-fold: measured nothing — the leg cannot vacuously pass"];
  }
  const found = [];
  for (const r of rows) {
    const at = `${r.url} at ${r.width}x${r.height}`;
    if (r.top === null || r.top === undefined) {
      found.push(`index-fold: ${at}: no [data-first-data] element — the page must declare the block this leg measures`);
      continue;
    }
    if (r.top >= r.height) {
      found.push(
        `index-fold: ${at}: the first data row starts at ${Math.round(r.top)}px, ` +
          `${Math.round(r.top - r.height)}px below the fold — the caveat above it has to move under it`,
      );
    }
  }
  return found;
}

export async function runAnswerfoldGate({ baseUrl }) {
  const errors = [];
  const notes = [];

  if (!fs.existsSync(outProgramDir)) {
    errors.push("answerfold_gate: out/program/ not found — build the site first");
    return { pass: false, errors, notes };
  }

  const slugs = sampleSlugs();
  if (slugs.length < 10) {
    notes.push(`only ${slugs.length} sample slugs available (expected 10)`);
  }
  notes.push(`sampled slugs: ${slugs.join(", ")}`);

  const browser = await chromium.launch({ headless: true });

  try {
    for (const vp of VIEWPORTS) {
      const vpLabel = `${vp.width}x${vp.height}`;
      const context = await browser.newContext({ viewport: vp });
      const page = await context.newPage();
      let okCount = 0;

      for (const slug of slugs) {
        try {
          await page.goto(`${baseUrl}/program/${slug}/`, {
            waitUntil: "load",
            timeout: 30000,
          });
          // The strip is SSR'd — wait for the first testid to exist.
          await page.waitForSelector('[data-testid="answer-what"]', {
            timeout: 10000,
          });

          let pageOk = true;
          for (const tid of TESTIDS) {
            const el = page.locator(`[data-testid="${tid}"]`).first();
            const count = await el.count();
            if (count === 0) {
              errors.push(`${vpLabel} program/${slug}: [data-testid="${tid}"] missing`);
              pageOk = false;
              continue;
            }
            const box = await el.boundingBox();
            if (!box) {
              errors.push(`${vpLabel} program/${slug}: [data-testid="${tid}"] not visible (no bounding box)`);
              pageOk = false;
              continue;
            }
            const bottom = box.y + box.height;
            if (bottom >= vp.height) {
              errors.push(
                `${vpLabel} program/${slug}: [data-testid="${tid}"] below the fold — bottom=${bottom.toFixed(0)}px >= viewport ${vp.height}px`
              );
              pageOk = false;
            }
          }
          if (pageOk) okCount++;
        } catch (e) {
          errors.push(`${vpLabel} program/${slug}: ${e.message.split("\n")[0]}`);
        }
      }

      notes.push(`${vpLabel}: ${okCount}/${slugs.length} pages have all three answers above the fold`);

      // ── index-fold leg (see the header doc) ──────────────────────────────
      const foldRows = [];
      for (const url of INDEX_FOLD_PAGES) {
        try {
          await page.goto(`${baseUrl}${url}`, { waitUntil: "load", timeout: 30000 });
          await page
            .waitForSelector(FIRST_DATA_WAIT, { timeout: 15000 })
            .catch(() => {});
          const top = await page.evaluate((sel) => {
            const block = document.querySelector("[data-first-data]");
            if (!block) return null;
            const el = block.querySelector(sel) ?? block;
            return el.getBoundingClientRect().top;
          }, FIRST_DATA_IN);
          foldRows.push({ url, width: vp.width, height: vp.height, top });
        } catch (e) {
          errors.push(`${vpLabel} ${url}: ${e.message.split("\n")[0]}`);
        }
      }
      errors.push(...indexFoldFindings(foldRows));
      notes.push(
        `${vpLabel} index-fold: ` +
          foldRows.map((r) => `${r.url} ${r.top === null ? "MISSING" : Math.round(r.top)}`).join(", "),
      );

      await context.close();
    }
  } finally {
    await browser.close();
  }

  return { pass: errors.length === 0, errors, notes };
}
