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
 * 3. FAMILY FOLD (2026-09-12, the lead-figure rule): every out/families/<id>/
 *    page, at both viewports — [data-testid="family-receipt"] is fully inside
 *    the first screen AND above the family's tab bar ([data-testid="family-nav"]);
 *    the ledger starts inside the first screen; the receipt carries exactly
 *    one [data-amount] whose data-fact-id equals its own data-lead-fact-id
 *    (or, in the absent case, none and a [data-absence] with the doctrine
 *    sentence); and the lead is VIEW-INDEPENDENT — after switching the funding
 *    workspace to another record, data-lead-fact-id is unchanged while the
 *    funding sheet's own statement follows the selection. Nine critics: "the
 *    program page buries the money"; the rule that surfaces it is
 *    src/lib/family-lead.ts, and this leg is where it is held on the fold.
 *
 * Export: runAnswerfoldGate({ baseUrl }) → { pass, errors, notes }
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
            errors.push(`${where}: [data-testid="family-receipt"] missing — the family page has no lead figure (src/lib/family-lead.ts decides it; the page must render it)`);
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
            const leadFid = await receipt.getAttribute("data-lead-fact-id");
            const amounts = receipt.locator('[data-testid="family-receipt-figure"] [data-amount]');
            const n = await amounts.count();
            if (n !== 1) errors.push(`${where}: family-receipt-figure holds ${n} [data-amount] (exactly one)`);
            else {
              const fid = await amounts.first().getAttribute("data-fact-id");
              const uncited = await amounts.first().getAttribute("data-uncited");
              if (fid !== leadFid) errors.push(`${where}: receipt figure fact-id ${fid} ≠ data-lead-fact-id ${leadFid}`);
              if (uncited != null) errors.push(`${where}: the lead figure is data-uncited — a family lead must be a state-A card`);
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
                const after = await receipt.getAttribute("data-lead-fact-id");
                if (after !== leadFid) errors.push(`${where}: data-lead-fact-id changed from ${leadFid} to ${after} after selecting another record — the lead follows the rule, never the view`);
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
