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
 * 3. INDEX-FOLD LEG (ROADMAP.md "## PM-review Sprint 3 — round-3 visual
 *    judging", the third panel's "what stays open": "the explanatory
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
 * 4. FAMILY FOLD (2026-09-12, the lead-figure rule): every out/families/<id>/
 *    page, at both viewports — [data-testid="family-receipt"] is fully inside
 *    the first screen AND above the family's tab bar ([data-testid="family-nav"]);
 *    the ledger starts inside the first screen; the receipt carries exactly
 *    one [data-amount] whose data-fact-id equals its own data-family-cumulative
 *    (or, in the absent case, none and a [data-absence] with the doctrine
 *    sentence); and the lead is VIEW-INDEPENDENT — after switching the funding
 *    workspace to another record, data-family-cumulative is unchanged while the
 *    funding sheet's own statement follows the selection. Nine critics: "the
 *    program page buries the money"; the rule that surfaces it is
 *    src/lib/family-funding-history.ts, and this leg is where it is held on the fold.
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

/**
 * Inside [data-first-data], the element that IS the first row of data. Kept
 * as an array (not a comma-joined string parsed back apart) so the scoped
 * wait below is derived without splitting a selector on `,` — a selector
 * with its own comma inside `[]`/`""` would silently break that split.
 */
const FIRST_DATA_ROW_SELECTORS = ["tbody tr", "[data-lineage-edge]"];
const FIRST_DATA_IN = FIRST_DATA_ROW_SELECTORS.join(", ");

/**
 * The same thing, scoped, so the measurement can WAIT for it. /years/ is a
 * client island that fetches its grid, so at `load` its block holds a loading
 * placeholder and no row; measuring then would read a near-empty wrapper and
 * pass vacuously. The wait is best-effort — a page that never renders a row
 * still falls through to the block itself, and a missing block is still a
 * failure below (kind: "block-only"), never a silent pass.
 */
const FIRST_DATA_WAIT = FIRST_DATA_ROW_SELECTORS.map(
  (sel) => `[data-first-data] ${sel}`,
).join(", ");

/**
 * Round-3 judging leftover (ROADMAP.md "## PM-review Sprint 3 — round-3
 * visual judging"): "the explanatory prose
 * demoted below the data it qualifies on five index pages". The durable
 * assertion is not a prose budget — it is that the page's first data ROW is
 * inside the initial viewport at both widths, the same measurement this gate
 * already makes for the three program-page answers.
 *
 * Fix round 2, item 1 (review finding): `top` alone let this leg pass
 * vacuously. Each row now carries a `kind` — "row" (a real first-data-row
 * element was found), "block-only" (the [data-first-data] wrapper was
 * measured because the row selector never appeared — a `waitForSelector`
 * timeout falling through silently), or "none" (no [data-first-data] block
 * at all) — mirroring the program legs' own idiom (:~179-183 above, a null
 * `boundingBox()` is an error, never a skip). `kind` defaults to "row" when
 * absent so every pre-existing fixture (no `kind` field) keeps behaving
 * exactly as it always did. `rectWidth`/`rectHeight` (the measured element's
 * OWN box, not the viewport) catch the other silent pass: a `display:none`
 * row's `getBoundingClientRect()` is all zeros, so `top === 0` used to read
 * as "comfortably above the fold" instead of "not actually rendered".
 * `top` is null for "none"; that is a failure, never a skip.
 */
export function indexFoldFindings(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return ["index-fold: measured nothing — the leg cannot vacuously pass"];
  }
  const found = [];
  for (const r of rows) {
    const at = `${r.url} at ${r.width}x${r.height}`;
    const kind = r.kind ?? "row";
    if (kind === "none" || r.top === null || r.top === undefined) {
      found.push(`index-fold: ${at}: no [data-first-data] element — the page must declare the block this leg measures`);
      continue;
    }
    if (kind === "block-only") {
      found.push(
        `index-fold: ${at}: kind=block-only — [data-first-data] never produced a data row ` +
          `(${FIRST_DATA_IN}); only the wrapper was measured, which is a failure, not a pass`,
      );
      continue;
    }
    if (r.rectWidth === 0 || r.rectHeight === 0) {
      found.push(
        `index-fold: ${at}: kind=row, zero-area (width=${r.rectWidth}, height=${r.rectHeight}) — ` +
          `the first data row has no rendered area (hidden or display:none), so its top is not meaningful`,
      );
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
          // Discriminated result — see indexFoldFindings' doc comment. A
          // `waitForSelector` timeout above falls through silently, so this
          // must say WHAT it measured (a real row, only the wrapper, or
          // nothing) rather than hand back a bare `top` that reads as fine
          // either way.
          const measured = await page.evaluate((sel) => {
            const block = document.querySelector("[data-first-data]");
            if (!block) {
              return { kind: "none", top: null, rectWidth: 0, rectHeight: 0 };
            }
            const el = block.querySelector(sel);
            if (!el) {
              const rect = block.getBoundingClientRect();
              return {
                kind: "block-only",
                top: rect.top,
                rectWidth: rect.width,
                rectHeight: rect.height,
              };
            }
            const rect = el.getBoundingClientRect();
            return {
              kind: "row",
              top: rect.top,
              rectWidth: rect.width,
              rectHeight: rect.height,
            };
          }, FIRST_DATA_IN);
          foldRows.push({
            url,
            width: vp.width,
            height: vp.height,
            top: measured.top,
            kind: measured.kind,
            rectWidth: measured.rectWidth,
            rectHeight: measured.rectHeight,
          });
        } catch (e) {
          errors.push(`${vpLabel} ${url}: ${e.message.split("\n")[0]}`);
        }
      }
      errors.push(...indexFoldFindings(foldRows));
      notes.push(
        `${vpLabel} index-fold: ` +
          foldRows
            .map((r) => {
              if (r.kind === "none") return `${r.url} MISSING`;
              if (r.kind === "block-only") return `${r.url} BLOCK-ONLY(${Math.round(r.top)})`;
              return `${r.url} ${Math.round(r.top)}`;
            })
            .join(", "),
      );

      await context.close();
    }

    // ── Family fold ───────────────────────────────────────────────────────
    const familiesDir = path.resolve(siteRoot, "out", "families");
    const families = fs.existsSync(familiesDir)
      ? fs.readdirSync(familiesDir, { withFileTypes: true }).filter((e) => e.isDirectory() && fs.existsSync(path.join(familiesDir, e.name, "index.html"))).map((e) => e.name).sort()
      : [];
    for (const vp of VIEWPORTS) {
      const vpLabel = `${vp.width}x${vp.height}`;
      const context = await browser.newContext({ viewport: vp });
      const page = await context.newPage();
      for (const fam of families) {
        const where = `${vpLabel} families/${fam}`;
        try {
          await page.goto(`${baseUrl}/families/${fam}/`, { waitUntil: "load", timeout: 30000 });
          const receipt = page.locator('[data-testid="family-receipt"]').first();
          if ((await receipt.count()) === 0) {
            errors.push(`${where}: [data-testid="family-receipt"] missing — the family page has no lead figure (src/lib/family-funding-history.ts decides it; the page must render it)`);
            continue;
          }
          const box = await receipt.boundingBox();
          if (!box) { errors.push(`${where}: family-receipt not visible`); continue; }
          if (box.y < 0 || box.y + box.height >= vp.height) errors.push(`${where}: family-receipt not inside the first screen (top=${box.y.toFixed(0)}, bottom=${(box.y + box.height).toFixed(0)}, viewport ${vp.height})`);
          const nav = page.locator('[data-testid="family-nav"]').first();
          if ((await nav.count()) > 0) {
            const nb = await nav.boundingBox();
            if (nb && box.y + box.height > nb.y + 1) errors.push(`${where}: family-receipt (bottom=${(box.y + box.height).toFixed(0)}) is below the tab bar (top=${nb.y.toFixed(0)}) — the money must come before the chrome`);
          }
          const ledger = page.locator('[data-testid="family-ledger"]').first();
          const absent = await receipt.getAttribute("data-lead-absent");
          if (absent == null) {
            if ((await ledger.count()) === 0) errors.push(`${where}: [data-testid="family-ledger"] missing`);
            else {
              const lb = await ledger.boundingBox();
              if (lb && lb.y >= vp.height) errors.push(`${where}: family-ledger starts below the first screen (top=${lb.y.toFixed(0)})`);
            }
            const leadFid = await receipt.getAttribute("data-family-cumulative");
            const amounts = receipt.locator('[data-testid="family-receipt-figure"] [data-amount]');
            const n = await amounts.count();
            if (n !== 1) errors.push(`${where}: family-receipt-figure holds ${n} [data-amount] (exactly one)`);
            else {
              const fid = await amounts.first().getAttribute("data-fact-id");
              const uncited = await amounts.first().getAttribute("data-uncited");
              if (fid !== leadFid) errors.push(`${where}: receipt figure fact-id ${fid} ≠ data-family-cumulative ${leadFid}`);
              if (uncited != null) errors.push(`${where}: the lead figure is data-uncited — a family total must have a derived receipt`);
            }
            // view-independence: switch the funding record; the lead must not move
            const fundingTab = page.locator('[data-testid="family-nav"] a[href="#funding"]').first();
            const select = page.locator("#family-funding-record").first();
            if ((await fundingTab.count()) > 0 && (await select.count()) > 0) {
              await fundingTab.click();
              await page.waitForTimeout(300);
              const options = await select.locator("option").count();
              if (options > 1) {
                await select.selectOption({ index: 1 });
                await page.waitForTimeout(300);
                const after = await receipt.getAttribute("data-family-cumulative");
                if (after !== leadFid) errors.push(`${where}: data-family-cumulative changed from ${leadFid} to ${after} after selecting another record — the family total is independent of the selected record`);
              }
            }
          } else {
            if ((await receipt.locator("[data-amount]").count()) !== 0) errors.push(`${where}: absent lead renders a [data-amount]`);
            const absText = await receipt.locator("[data-absence]").first().textContent().catch(() => "");
            if (!/Missing coverage is not zero spending/.test(absText ?? "")) errors.push(`${where}: absent lead lacks the doctrine sentence`);
          }
        } catch (e) {
          errors.push(`${where}: ${e.message.split("\n")[0]}`);
        }
      }
      await context.close();
    }
    if (families.length) notes.push(`family fold: ${families.length} famil${families.length === 1 ? "y" : "ies"} checked at both viewports${errors.some((e) => /families\//.test(e)) ? "" : " ✓"}`);
  } finally {
    await browser.close();
  }

  return { pass: errors.length === 0, errors, notes };
}
