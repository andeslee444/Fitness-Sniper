// @vitest-environment node
/**
 * Unit tests for gate 3's layout-spine leg (gates/spine.mjs) — the reading-
 * measure half, (s2). ROADMAP #42 residue, 2026-09-10.
 *
 * The project runs vitest under jsdom; this file overrides to node, because
 * jsdom has no layout and (s2) is a LAYOUT property — characters per rendered
 * line. So the tests drive the same headless Chromium the leg uses: render a
 * fixture with setContent(), then call the leg's OWN in-page measurer and its
 * OWN trip predicate. Nothing here re-implements the measurement.
 * (measureSpineInPage is serialized into the page by Playwright and closes
 * over nothing, so the module transform that loads it leaves its body alone.)
 *
 * globals.css is injected raw: the browser drops @import / @theme /
 * @custom-variant as unknown at-rules, while :root's custom properties and
 * the unlayered .spine rules survive — so the assertion runs against the
 * rules that ship, not a copy of them.
 *
 * What these pin, measured on the live 2026-09-04 build at 1440 before the
 * fix: /glossary/'s 21 <dd> definitions ran 121-134 characters per line and
 * /coverage/'s corpus-count <li> 132, with gate 3 green — <dd> matched no
 * selector, and the leg skipped every list-style:none item on the theory
 * that the marker separates prose from cards. The container test does that.
 *
 * Proof it can fail: the first test renders the fixture WITHOUT the
 * stylesheet and requires the leg to trip on all four blocks. Narrow the
 * selector back to "p, li, figcaption", or reinstate the list-style skip,
 * and it goes red before any page does.
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { chromium } from "playwright";
import {
  MAX_CPL,
  MIN_PROSE_CHARS,
  SPINE_WIDTHS,
  measureSpineInPage,
  proseOverMeasure,
} from "../spine.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const globalsCss = fs.readFileSync(
  path.resolve(__dirname, "..", "..", "..", "src", "app", "globals.css"),
  "utf8",
);

/** 3 x 152 = 456 characters: past MIN_PROSE_CHARS, and long enough to wrap at
 *  every width these tests render. */
const SENTENCES =
  "The reconciliation badge states the result of comparing a summary exhibit total against the sum of its detail rows for the same fiscal year and edition; ".repeat(
    3,
  );

/** The four shapes under test, each with a distinct first word so the leg's
 *  44-character `text` sample says which block tripped. BOXITEM is
 *  /coverage/'s shape (bordered, px-4 rows); BAREITEM is the dossier's (no
 *  border, no padding). The box-sizing reset stands in for Tailwind's
 *  preflight, which the raw @import cannot load — without it the .spine box
 *  measures 1312px instead of the 1280px the site renders. */
function fixture({ withCss, boxAttr = "", bareAttr = "" }) {
  return `<!doctype html><html><head>
<style>${withCss ? globalsCss : ""}</style>
<style>*,*::before,*::after{box-sizing:border-box}
body{margin:0;font:16px/1.75 "Avenir Next","Segoe UI",sans-serif}</style>
</head><body>
<header><a href="/">Fiscal Receipts</a></header>
<main id="main-content"><div class="spine">
<h1>Fixture</h1>
<p>PARAGRAPH ${SENTENCES}</p>
<dl><div><dt>Reconciliation</dt><dd class="mt-1">DEFINITION ${SENTENCES}</dd></div></dl>
<ul ${boxAttr} style="list-style:none;margin:0;padding:0;border:1px solid #ccc"><li style="padding:0.75rem 1rem">BOXITEM ${SENTENCES}</li></ul>
<ul ${bareAttr} style="list-style:none;margin:0;padding:0"><li>BAREITEM ${SENTENCES}</li></ul>
</div></main></body></html>`;
}

let browser;
beforeAll(async () => {
  browser = await chromium.launch({ headless: true });
});
afterAll(async () => {
  await browser?.close();
});

const firstWord = (p) => p.text.split(" ")[0];

async function measure(html) {
  const page = await browser.newPage({
    viewport: { width: SPINE_WIDTHS[0], height: 1000 },
  });
  try {
    await page.setContent(html);
    await page.evaluate(() => document.fonts.ready).catch(() => {});
    const m = await page.evaluate(measureSpineInPage, {
      minProseChars: MIN_PROSE_CHARS,
    });
    return {
      m,
      byBlock: new Map(m.prose.map((p) => [firstWord(p), p])),
      over: proseOverMeasure(m.prose),
    };
  } finally {
    await page.close();
  }
}

describe("spine leg (s2) — constants", () => {
  it("holds the WCAG 1.4.8 number, the 120-character floor and the 1440 width", () => {
    expect(MAX_CPL).toBe(80);
    expect(MIN_PROSE_CHARS).toBe(120);
    expect(SPINE_WIDTHS[0]).toBe(1440);
  });
});

describe("spine leg (s2) — proof it can fail", () => {
  it("measures <dd> and marker-less <li>, and trips on both when nothing caps them", async () => {
    const { m, byBlock, over } = await measure(fixture({ withCss: false }));
    // Non-vacuity: all four blocks resolved a measure (>= 2 lines each).
    expect([...byBlock.keys()].sort()).toEqual([
      "BAREITEM",
      "BOXITEM",
      "DEFINITION",
      "PARAGRAPH",
    ]);
    expect(m.proseSkipped).toBe(0);
    // Uncapped in a 1,440px document, every one of them runs far past 80.
    expect(over.map(firstWord).sort()).toEqual([
      "BAREITEM",
      "BOXITEM",
      "DEFINITION",
      "PARAGRAPH",
    ]);
    for (const p of over) expect(p.cpl).toBeGreaterThan(MAX_CPL);
    // Worst first — the leg's error message samples the top three.
    expect(over[0].cpl).toBeGreaterThanOrEqual(over[over.length - 1].cpl);
  });
});

describe("spine leg (s2) — globals.css caps what the leg measures", () => {
  it("caps <p>, <dd> and both declared list shapes at the measure", async () => {
    const { byBlock, over } = await measure(
      fixture({
        withCss: true,
        boxAttr: 'data-measure="prose-box"',
        bareAttr: 'data-measure="prose"',
      }),
    );
    expect(over).toEqual([]);
    for (const key of ["PARAGRAPH", "DEFINITION", "BOXITEM", "BAREITEM"]) {
      const p = byBlock.get(key);
      expect(p, key).toBeTruthy();
      // Capped, and not vacuously so: a 54ch cap lands near 70 rendered
      // characters. Under 55 would mean the fixture, not the rule, changed.
      expect(p.cpl, key).toBeLessThanOrEqual(MAX_CPL);
      expect(p.cpl, key).toBeGreaterThanOrEqual(55);
      expect(p.lines, key).toBeGreaterThanOrEqual(2);
    }
  });

  it("leaves an undeclared marker-less list visible to the leg (the drift guard)", async () => {
    const { byBlock, over } = await measure(fixture({ withCss: true }));
    // <dd> needs no declaration; a marker-less list does — and without one
    // the leg reports it rather than the stylesheet quietly leaving it wide.
    expect(byBlock.get("DEFINITION").cpl).toBeLessThanOrEqual(MAX_CPL);
    expect(over.map(firstWord).sort()).toEqual(["BAREITEM", "BOXITEM"]);
  });

  it('the [data-measure="full"] opt-out is CSS-only — the leg still measures and still holds 80', async () => {
    const { byBlock, over } = await measure(
      fixture({
        withCss: true,
        boxAttr: 'data-measure="full"',
        bareAttr: 'data-measure="full"',
      }),
    );
    expect(byBlock.has("BAREITEM")).toBe(true);
    expect(over.map(firstWord).sort()).toEqual(["BAREITEM", "BOXITEM"]);
  });
});
