/**
 * entity-label-margins — the narrow-label census (ROADMAP #10 A; Task 29S).
 *
 * /methodology/ typed "15 of the 200 families we publish carry a label that
 * beat its runner-up by under 15%". The FY2026 refresh of 2026-09-06 moved
 * the argmaxes and the top-200 membership, and chain C run 3's recompute
 * found 14 — the literal had rotted to false while every figure around it
 * stayed cited. The page now renders a census computed by ONE helper that
 * gate 24 leg l computes too, from its own inputs, and matches verbatim.
 *
 * Fixtures only: the shipped seed and the lake move under other tasks.
 */
import fs from "fs";
import path from "path";
import { describe, it, expect } from "vitest";
import {
  NEAR_TIE_MARGIN,
  isNearTie,
  labelMarginCensus,
  labelCensusSentence,
  labelCensusFindings,
} from "../entity-label-margins.mjs";

/** What familylabel-recompute.py hands leg l: published families + margins. */
const RECOMPUTED = [
  { family_key: "LOCKHEED MARTIN", margin: 1.0 },
  { family_key: "ROCKWELL COLLINS AUSTRALIA", margin: 0.031 },
  { family_key: "HIG CAPITAL MANAGEMENT", margin: 0.022 },
  { family_key: "WICO", margin: 0.18 }, // seeded, but no longer a near-tie
  { family_key: "TRANSDIGM GROUP", margin: 0.024 }, // a near-tie nobody seeded
];
/** The seed's family_key column — one row names a family no longer published. */
const SEED_KEYS = [
  "ROCKWELL COLLINS AUSTRALIA",
  "HIG CAPITAL MANAGEMENT",
  "WICO",
  "SERCO GROUP",
];
/** What the page reads: entities_top.json rows, `label` where the seed resolved. */
const ENTITIES_TOP = [
  { family_key: "LOCKHEED MARTIN", display_name: "LOCKHEED MARTIN CORP" },
  {
    family_key: "ROCKWELL COLLINS AUSTRALIA",
    display_name: "ROCKWELL COLLINS AUSTRALIA PTY LIMITED",
    label: "RTX (Raytheon Company registrations)",
  },
  {
    family_key: "HIG CAPITAL MANAGEMENT",
    display_name: "HIG CAPITAL MANAGEMENT, INC.",
    label: "HIG Capital Management, Inc.",
  },
  {
    family_key: "WICO",
    display_name: "WICO LIMITED",
    label: "General Dynamics Ordnance & Tactical Systems",
  },
  { family_key: "TRANSDIGM GROUP", display_name: "TRANSDIGM GROUP INCORPORATED" },
];
const labelledKeys = (rows: typeof ENTITIES_TOP) =>
  rows.filter((r) => r.label).map((r) => r.family_key);

describe("isNearTie — the one threshold", () => {
  it("is 15%, strictly below", () => {
    expect(NEAR_TIE_MARGIN).toBe(0.15);
    expect(isNearTie({ family_key: "X", margin: 0.031 })).toBe(true);
    expect(isNearTie({ family_key: "X", margin: 0.1499 })).toBe(true);
    expect(isNearTie({ family_key: "X", margin: 0.15 })).toBe(false);
    expect(isNearTie({ family_key: "X", margin: 1 })).toBe(false);
  });

  it("a family without a measured margin is not a near-tie", () => {
    expect(isNearTie({ family_key: "X" })).toBe(false);
    expect(isNearTie({ family_key: "X", margin: Number.NaN })).toBe(false);
  });
});

describe("labelMarginCensus", () => {
  it("counts leg l's inputs: the recompute's families and the seed", () => {
    expect(labelMarginCensus(RECOMPUTED, SEED_KEYS)).toEqual({
      published: 5,
      closeMargin: 3,
      curated: 3, // SERCO GROUP is seeded but not published: it curates nothing
      thresholdPct: 15,
    });
  });

  it("counts the page's inputs: entities_top.json and its seed labels — no margins, so no closeMargin", () => {
    expect(labelMarginCensus(ENTITIES_TOP, labelledKeys(ENTITIES_TOP))).toEqual({
      published: 5,
      closeMargin: null,
      curated: 3,
      thresholdPct: 15,
    });
  });

  it("the page and the gate agree on every figure the sentence prints when their inputs agree", () => {
    const page = labelMarginCensus(ENTITIES_TOP, labelledKeys(ENTITIES_TOP));
    const gate = labelMarginCensus(RECOMPUTED, SEED_KEYS);
    expect(labelCensusSentence(page)).toBe(labelCensusSentence(gate));
  });

  it("a label the exporter dropped makes the two disagree — the drift leg l exists to catch", () => {
    const dropped = ENTITIES_TOP.map((r) =>
      r.family_key === "WICO" ? { ...r, label: undefined } : r,
    );
    const page = labelMarginCensus(dropped, labelledKeys(dropped));
    const gate = labelMarginCensus(RECOMPUTED, SEED_KEYS);
    expect(page.curated).toBe(2);
    expect(labelCensusSentence(page)).not.toBe(labelCensusSentence(gate));
  });

  it("refuses a half-measured family list rather than count part of it", () => {
    expect(() =>
      labelMarginCensus([...RECOMPUTED, { family_key: "UNMEASURED" }], SEED_KEYS),
    ).toThrow(/margin/);
  });
});

describe("labelCensusSentence", () => {
  it("renders the census, and nothing typed", () => {
    expect(
      labelCensusSentence({ published: 200, closeMargin: 14, curated: 17, thresholdPct: 15 }),
    ).toBe(
      "Among the 200 families we publish, a label that won its argmax by " +
        "under 15% fails the build without a reviewed one from a curated seed; " +
        "17 carry one, each company page still showing its registered name.",
    );
  });

  it("scopes the rule to the families it counts — leg l recomputes only the published set", () => {
    // Task 29 fix round 1: the sentence opened "A label that beat its
    // runner-up by under 15% fails the build…" with no scope, while leg l
    // measures only the top 200 and /companies/families/ renders member
    // labels below that cut (L3 TECHNOLOGIES, rank 201, a 3.1% near-tie with
    // no seed row). The rule clause must name the set it is enforced on.
    const s = labelCensusSentence({ published: 200, closeMargin: 14, curated: 17, thresholdPct: 15 });
    const rule = s.slice(0, s.indexOf(";"));
    expect(rule.startsWith("Among the 200 families we publish, a label that won")).toBe(true);
    expect(rule).toContain("under 15% fails the build");
  });

  it("groups thousands the way the site prints counts", () => {
    expect(
      labelCensusSentence({ published: 1200, closeMargin: null, curated: 1050, thresholdPct: 15 }),
    ).toMatch(/^Among the 1,200 families we publish, .*; 1,050 carry one,/);
  });
});

describe("labelCensusFindings — leg l's binding of the rendered sentence", () => {
  const census = labelMarginCensus(RECOMPUTED, SEED_KEYS);
  const page = (sentence: string) =>
    `The tier grades the grouping, never the name. A family’s label is the\n` +
    `registered parent name of its largest member, chosen by an argmax over ` +
    `obligations. ${sentence} No SAM.gov registration record ships yet.`;

  it("passes on the sentence the helper renders, whatever the whitespace around it", () => {
    expect(labelCensusFindings(page(labelCensusSentence(census)), census)).toEqual([]);
  });

  it("FAILS on the typed literal the page shipped before (proof it can fail)", () => {
    const before =
      "chosen by an argmax over obligations: 15 of the 200 families we publish " +
      "carry a label that beat its runner-up by under 15%. Those carry a " +
      "reviewed label from a curated seed instead";
    const findings = labelCensusFindings(before, census);
    expect(findings).toHaveLength(1);
    expect(findings[0]).toMatch(/missing or reworded/);
  });

  it("FAILS when the page states another count than the census computes", () => {
    const stale = labelCensusSentence({ ...census, curated: 11 });
    const findings = labelCensusFindings(page(stale), census);
    expect(findings).toHaveLength(1);
    expect(findings[0]).toContain('states "Among the 5 families we publish,');
    expect(findings[0]).toContain("; 11 carry one,");
    expect(findings[0]).toContain("; 3 carry one,");
  });

  it("FAILS when the page states another threshold than the gate enforces", () => {
    const loosened = labelCensusSentence({ ...census, thresholdPct: 10 });
    const findings = labelCensusFindings(page(loosened), census);
    expect(findings).toHaveLength(1);
    expect(findings[0]).toContain("under 10%");
  });

  it("FAILS when the published denominator drifts", () => {
    const findings = labelCensusFindings(
      page(labelCensusSentence({ ...census, published: 200 })),
      census,
    );
    expect(findings).toHaveLength(1);
  });
});

describe("one helper, two importers", () => {
  const site = path.resolve(__dirname, "..", "..", "..");
  const read = (p: string) => fs.readFileSync(path.join(site, p), "utf8");

  it("/methodology/ renders the helper's sentence and types no census of its own", () => {
    const src = read("src/app/methodology/page.tsx");
    expect(src).toMatch(/from "@\/lib\/entity-label-margins\.mjs"/);
    expect(src).toContain("labelCensusSentence(");
    expect(src).not.toMatch(/\d+ of the \d+\s+families we publish/);
    expect(src).not.toMatch(/Among the \d+\s+families we publish/);
  });

  it("gate 24 leg l takes its threshold, census and sentence check from the helper", () => {
    const src = read("scripts/gates/datatruth.mjs");
    expect(src).toMatch(/from "\.\.\/\.\.\/src\/lib\/entity-label-margins\.mjs"/);
    expect(src).toContain("labelMarginCensus(");
    expect(src).toContain("labelCensusFindings(");
    expect(src).not.toMatch(/const NEAR_TIE_MARGIN\s*=/);
  });
});
