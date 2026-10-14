/**
 * Unit tests for gate 23 (basis.mjs) helpers — value normalization,
 * 3-significant-digit agreement, FY-label token extraction, the golden
 * footnote field-manifest parser, and leg (f)'s chip classification (#48).
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import {
  normalizeAmount,
  valuesAgree,
  fyTokensFromLabel,
  validateGoldenFootnote,
  chipExhibitClaim,
  isBasisChipClassName,
  feedSectionIsTruncated,
  citationLeafSheets,
  omPageChipProblems,
} from "../basis.mjs";
import { parse } from "node-html-parser";

const goldensDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "goldens",
  "footnotes",
);

// ── normalizeAmount ──────────────────────────────────────────────────────────

describe("normalizeAmount", () => {
  it("parses $/B/M/K suffixed figures to dollars", () => {
    expect(normalizeAmount("$5.25B")).toBe(5.25e9);
    expect(normalizeAmount("$286.5M")).toBe(286.5e6);
    expect(normalizeAmount("$318.6K")).toBe(318.6e3);
    expect(normalizeAmount("$3.66T")).toBe(3.66e12);
  });

  it("parses comma-grouped plain dollars", () => {
    expect(normalizeAmount("$5,247.07")).toBeCloseTo(5247.07, 6);
    expect(normalizeAmount("$4,972,514")).toBe(4972514);
  });

  it("tolerates surrounding whitespace", () => {
    expect(normalizeAmount("  $4.09B ")).toBe(4.09e9);
  });

  it("returns null for absences, prose, and non-currency text", () => {
    expect(normalizeAmount("—")).toBeNull();
    expect(normalizeAmount("–")).toBeNull();
    expect(normalizeAmount("")).toBeNull();
    expect(normalizeAmount("FY24 Actuals")).toBeNull();
    expect(normalizeAmount("$5.25B requested")).toBeNull(); // not a lone figure
    expect(normalizeAmount(null)).toBeNull();
  });
});

// ── valuesAgree ──────────────────────────────────────────────────────────────

describe("valuesAgree (3-significant-digit tolerance)", () => {
  it("a rendered rounding of the exact value agrees ($5.25B ~ $5,247.07M)", () => {
    expect(valuesAgree(5.25e9, 5247.07e6)).toBe(true);
  });

  it("the P0-1 collision values do NOT agree ($5.25B vs $5.57B)", () => {
    expect(valuesAgree(5.25e9, 5.57e9)).toBe(false);
  });

  it("the P0-1 FY26 collision values do NOT agree ($4.09B vs $3.56B)", () => {
    expect(valuesAgree(4.09e9, 3.56e9)).toBe(false);
  });

  it("units normalize: $4,972,514 thousand-scale display ~ $4.97B", () => {
    // decade cell renders $4.97B; title carries $4,972,514 (USD thousands)
    expect(valuesAgree(4.97e9, 4972514e3)).toBe(true);
  });

  it("identical and zero values agree; null never agrees", () => {
    expect(valuesAgree(5e9, 5e9)).toBe(true);
    expect(valuesAgree(0, 0)).toBe(true);
    expect(valuesAgree(null, 5e9)).toBe(false);
    expect(valuesAgree(5e9, null)).toBe(false);
  });
});

// ── fyTokensFromLabel ────────────────────────────────────────────────────────

describe("fyTokensFromLabel", () => {
  it("extracts a single 2-digit FY", () => {
    expect(fyTokensFromLabel("FY24 Actuals")).toEqual({ years: [2024], change: false });
    expect(fyTokensFromLabel("FY25 Total")).toEqual({ years: [2025], change: false });
  });

  it("extracts 4-digit FYs", () => {
    expect(fyTokensFromLabel("FY2026 Request")).toEqual({ years: [2026], change: false });
  });

  it("extracts change-card endpoint pairs", () => {
    expect(fyTokensFromLabel("FY25→26 Change")).toEqual({
      years: [2025, 2026],
      change: true,
    });
  });

  it("returns empty for labels without FY tokens", () => {
    expect(fyTokensFromLabel("All Prior Years")).toEqual({ years: [], change: false });
  });
});

// ── validateGoldenFootnote (golden parser) ───────────────────────────────────

function loadGolden(tier) {
  const fixture = JSON.parse(
    fs.readFileSync(path.join(goldensDir, `${tier}.input.json`), "utf8"),
  );
  const golden = fs.readFileSync(path.join(goldensDir, `${tier}.txt`), "utf8").trim();
  return { fixture, golden };
}

describe("validateGoldenFootnote", () => {
  it.each(["pdf", "workbook", "derived"])(
    "the committed %s golden satisfies its own field manifest",
    (tier) => {
      const { fixture, golden } = loadGolden(tier);
      expect(validateGoldenFootnote(fixture, golden)).toEqual([]);
    },
  );

  it("flags the CURRENT (pre-fix) pdf-tier footnote as incomplete (P0-3)", () => {
    const { fixture } = loadGolden("pdf");
    // Verbatim current production output (spec §P0-3 "Actual output").
    const current =
      "F-35: 5,247.070 — FY26 Air Force Aircraft Procurement Vol I.pdf, p.55; " +
      "sha256:528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e; " +
      "retrieved 2026-07-05; https://fiscalreceipts.com/program/ATA000/";
    const missing = validateGoldenFootnote(fixture, current);
    // The exact hazards P0-3 names: no unit, no FY, no row name, no document
    // title (filename only), no fact permalink.
    expect(missing.join("; ")).toMatch(/value with unit/);
    expect(missing.join("; ")).toMatch(/fiscal year/i);
    expect(missing.join("; ")).toMatch(/row\/field name/);
    expect(missing.join("; ")).toMatch(/fact permalink/);
  });

  it("flags a footnote missing the sha256 (pdf tier)", () => {
    const { fixture, golden } = loadGolden("pdf");
    const tampered = golden.replace(/SHA-256 [0-9a-f]{8}…/, "");
    expect(validateGoldenFootnote(fixture, tampered).join("; ")).toMatch(/sha256/);
  });

  it("flags a workbook footnote missing sheet/cells locator", () => {
    const { fixture, golden } = loadGolden("workbook");
    const noSheet = golden.replace("sheet Exhibit P-1, ", "").replace("Exhibit P-1", "");
    expect(validateGoldenFootnote(fixture, noSheet).join("; ")).toMatch(/sheet locator/);
    const noCells = golden.replace("cells O839,O840,O841", "");
    expect(validateGoldenFootnote(fixture, noCells).join("; ")).toMatch(/cells locator/);
  });

  it("flags a derived footnote missing formula or input permalinks", () => {
    const { fixture, golden } = loadGolden("derived");
    const noFormula = golden.replace(fixture.formula, "");
    expect(validateGoldenFootnote(fixture, noFormula).join("; ")).toMatch(
      /derivation formula/,
    );
    const noInput = golden.replace("https://fiscalreceipts.com/fact/666be822", "");
    expect(validateGoldenFootnote(fixture, noInput).join("; ")).toMatch(
      /input fact permalink/,
    );
  });

  it("flags a footnote missing the retrieved date", () => {
    const { fixture, golden } = loadGolden("workbook");
    const tampered = golden.replace(/retrieved \d{4}-\d{2}-\d{2}/i, "retrieved");
    expect(validateGoldenFootnote(fixture, tampered).join("; ")).toMatch(
      /retrieved date/,
    );
  });
});

// ── chipExhibitClaim / isBasisChipClassName — leg (f) (#48) ─────────────────

describe("chipExhibitClaim", () => {
  it("reads an RDT&E chip", () => {
    expect(chipExhibitClaim("R-1 TOA · PB2026")).toBe("rdte");
  });

  it("reads a procurement chip", () => {
    expect(chipExhibitClaim("P-1 TOA · PB2026")).toBe("procurement");
  });

  it("reads the combined both-exhibits chip as mixed, not procurement", () => {
    // The leading substring is literally "P-1" for both forms — the "/"
    // check must run BEFORE the "P-1 " (space) check, or every mixed chip
    // misreads as a procurement claim.
    expect(chipExhibitClaim("P-1/R-1 TOA · PB2026")).toBe("mixed");
  });

  it("returns null for a non-TOA chip (no opinion)", () => {
    expect(chipExhibitClaim("J-book detail · PB2026")).toBeNull();
  });

  it("returns null for empty/absent text", () => {
    expect(chipExhibitClaim("")).toBeNull();
    expect(chipExhibitClaim(null)).toBeNull();
    expect(chipExhibitClaim(undefined)).toBeNull();
  });
});

describe("isBasisChipClassName", () => {
  // The exact className cite.tsx renders the chip with (Cite's basisChip and
  // CiteChips' chipText spans — verified identical at both call sites).
  const CHIP_CLASS =
    "ml-1 inline-block whitespace-nowrap rounded border border-border bg-muted px-1 py-0.5 align-middle font-sans text-xs font-normal leading-none text-muted-foreground no-underline";

  it("matches the chip's real rendered class string", () => {
    expect(isBasisChipClassName(CHIP_CLASS)).toBe(true);
  });

  it("does not match the fact-id chip's class (.cite-id-chip, a named class — no overlapping tokens)", () => {
    expect(isBasisChipClassName("cite-id-chip")).toBe(false);
  });

  it("does not match an unrelated span missing the distinguishing tokens", () => {
    expect(isBasisChipClassName("text-xs text-muted-foreground")).toBe(false);
  });

  it("handles missing/empty class attributes", () => {
    expect(isBasisChipClassName(null)).toBe(false);
    expect(isBasisChipClassName(undefined)).toBe(false);
    expect(isBasisChipClassName("")).toBe(false);
  });
});

// ── leg g4's truncation excuse (Task 26) ─────────────────────────────────────

describe("feedSectionIsTruncated — leg g4 excuses a missing card only by its OWN section's note", () => {
  const note = (type) =>
    `<p data-feed-truncation-note="" data-feed-event-type="${type}" data-feed-shown="75" data-feed-total="99">Showing the 75 largest…</p>`;

  it("reads the yoy_swing note chain C run 4's /feed/ renders", () => {
    const root = parse(`<main>${note("yoy_swing")}${note("concentration_shift")}</main>`);
    expect(feedSectionIsTruncated(root, "yoy_swing")).toBe(true);
  });

  it("a truncated concentration_shift section excuses nothing on yoy_swing — proof it can fail", () => {
    const root = parse(`<main>${note("concentration_shift")}</main>`);
    expect(feedSectionIsTruncated(root, "yoy_swing")).toBe(false);
    expect(feedSectionIsTruncated(root, "concentration_shift")).toBe(true);
  });

  it("no note at all excuses nothing", () => {
    expect(feedSectionIsTruncated(parse("<main><p>cards</p></main>"), "yoy_swing")).toBe(false);
  });
});

// ── leg f4: an "om" page's chip names its figure's own sheet (#194) ─────────
//
// /program/0390DOM/ (Chem Demil O&M, exhibit_family "om") is printed on the
// PB2026 P-1: its TOA chips read "P-1 TOA" because every figure on the page
// cites sheet "Exhibit P-1" (Task 21h2). The markup and citation records
// below are the B@fu-post build's own (fact ids, cells and the derived
// change's inputs as shipped in out/json/cite-shards), trimmed to the
// fields the leg reads.

describe("omPageChipProblems — leg f4", () => {
  const CHIP_CLASS =
    "ml-1 inline-block whitespace-nowrap rounded border border-border bg-muted px-1 py-0.5 align-middle font-sans text-xs font-normal leading-none text-muted-foreground no-underline";
  const figure = (fid, text) =>
    `<span data-amount="true" data-fact-id="${fid}" data-basis="toa" class="cite-figure">${text}</span>` +
    `<span data-receipts-chip="true" class="cite-id-chip">#${fid.slice(0, 8)}</span>`;
  const chip = (text) => `<span class="${CHIP_CLASS}">${text}</span>`;
  // answer-changed: a chip={false} Cite, then CiteChips after the value
  // cluster; the figures grid: Cite's own chip right after its figure.
  const PAGE =
    `<div data-testid="answer-changed"><span class="whitespace-nowrap">` +
    `${figure("7e51d0fb2dbbd071", "-$17.5M")}<span> (-84.4%)</span></span> ` +
    `<span class="inline-flex items-center whitespace-nowrap">${chip("P-1 TOA · PB2026")}</span></div>` +
    `<div data-section="figures">` +
    `<span>${figure("9a66c1d170413c20", "$87.4M")}${chip("P-1 TOA · PB2026")}</span>` +
    `<span>${figure("28d7620d29b4ccd6", "$20.7M")}${chip("P-1 TOA · PB2026")}</span>` +
    `<span>${figure("86eb97e8aabd38f4", "$3.24M")}${chip("P-1 TOA · PB2026")}</span>` +
    `<span>${figure("7e51d0fb2dbbd071", "-$17.5M")}${chip("P-1 TOA · PB2026")}</span></div>`;
  const P1 = (cells) => ({ kind: "workbook", sheet: "Exhibit P-1", cells, inputs: null });
  const CITATIONS = {
    "9a66c1d170413c20": P1("O303"),
    "28d7620d29b4ccd6": P1("Q303"),
    "86eb97e8aabd38f4": P1("W303"),
    // the shards carry a derived record's inputs as a JSON string
    "7e51d0fb2dbbd071": {
      kind: "derived",
      sheet: null,
      inputs: '["86eb97e8aabd38f4", "28d7620d29b4ccd6"]',
    },
  };
  const loaderFor = (records) => (fid) => records[fid] ?? null;
  const check = (html, records = CITATIONS) =>
    omPageChipProblems(parse(`<main>${html}</main>`), loaderFor(records), "program/0390DOM/index.html");

  it("passes the real page: five P-1 chips, each on a figure citing Exhibit P-1", () => {
    const r = check(PAGE);
    expect(r.problems).toEqual([]);
    expect(r.resolved).toBe(5);
  });

  it("reads a derived figure through its inputs", () => {
    expect(citationLeafSheets("7e51d0fb2dbbd071", loaderFor(CITATIONS))).toEqual([
      "Exhibit P-1",
      "Exhibit P-1",
    ]);
  });

  it("PLANT: an om line whose figure cites another sheet fails — the P-1 claim is not proven", () => {
    const r = check(PAGE, { ...CITATIONS, "86eb97e8aabd38f4": { ...P1("W303"), sheet: "Exhibit O-1" } });
    // the FY2026 card's own chip, and both change chips (an input of the change)
    expect(r.problems).toHaveLength(3);
    expect(r.problems[0]).toContain('"P-1 TOA · PB2026"');
    expect(r.problems.join("\n")).toContain("Exhibit O-1");
  });

  it("PLANT: a derived figure with one input on the R-1 fails", () => {
    const r = check(PAGE, { ...CITATIONS, "28d7620d29b4ccd6": { kind: "workbook", sheet: "Exhibit R-1", inputs: null } });
    expect(r.problems.some((p) => p.includes("7e51d0fb2dbbd071"))).toBe(true);
  });

  it("PLANT: a fact id the cite-shards do not hold, or a chip with no cited figure before it, fails closed", () => {
    const missing = { ...CITATIONS };
    delete missing["9a66c1d170413c20"];
    expect(check(PAGE, missing).problems).toHaveLength(1);
    expect(check(chip("P-1 TOA · PB2026")).problems).toHaveLength(1);
    const uncited = `<span data-amount="true" data-basis="toa">$1.0M</span>${chip("P-1 TOA · PB2026")}`;
    expect(check(uncited).problems).toHaveLength(1);
  });

  it("leaves the both-exhibits chip to leg f2 and a non-TOA chip alone", () => {
    const r = check(`${figure("9a66c1d170413c20", "$87.4M")}${chip("P-1/R-1 TOA · PB2026")}${chip("J-book detail · PB2026")}`);
    expect(r).toEqual({ resolved: 0, problems: [] });
  });
});
