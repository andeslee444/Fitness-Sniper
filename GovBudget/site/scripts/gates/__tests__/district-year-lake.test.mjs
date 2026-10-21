/**
 * Unit tests for gate 24 leg (r) — a sampled district-year cell must match the
 * LAKE and the RENDERED page (ROADMAP #6).
 *
 * (The brief called this leg (o); (o) was taken by the hand-adjudication
 * coverage leg that landed first, and (p)/(q) are reserved, so this one is
 * (r).)
 *
 * Why the pure half is exported: the leg's I/O (read sidecars, spawn
 * districtyear-recompute.py, parse out/district/{code}/index.html) cannot run
 * without a 35-minute build, and a leg nobody can fail on demand is a leg
 * nobody trusts. checkDistrictYearSample takes the three inputs as data and a
 * reader function, so every failure mode is provable in milliseconds.
 *
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import {
  checkDistrictYearSample,
  sampleDistrictYearCells,
  DISTRICT_YEAR_PINNED,
} from "../datatruth.mjs";

const SAMPLE = [
  { district: "ZZ-01", fy: 2019, total: 124413254.06, positive: 125501811.59 },
];
const TRUTH = {
  "ZZ-01|2019": {
    award_count: 12,
    total_obligation: 124413254.06,
    positive_obligation: 125501811.59,
  },
};
/** What the built page shows: formatAmount renders this as "$124.4M". No
 *  `gross` key — the "Before deobligations" column is conditional, and most
 *  districts do not render it. */
const rendered = (over = {}) => () => ({ amount: 124400000, cited: true, ...over });
/** ...and the same row WITH the gross cell rendered ("$125.5M"). */
const renderedWithGross = (over = {}, grossOver = {}) => () => ({
  amount: 124400000,
  cited: true,
  gross: { amount: 125500000, cited: true, ...grossOver },
  ...over,
});

describe("gate 24 leg r — district-year cells vs the lake and the page", () => {
  it("passes when sidecar, lake and rendered figure agree", () => {
    // SAMPLE's gross exceeds its net, so this district's page renders the
    // gross column too — both figures have to agree.
    const { failures, checked } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: renderedWithGross(),
    });
    expect(failures).toEqual([]);
    expect(checked).toBe(1);
  });

  it("FAILS when the lake holds nothing for a cell the page publishes", () => {
    const { failures } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: {},
      readRendered: rendered(),
    });
    expect(failures[0]).toContain("the lake holds");
  });

  it("FAILS when the sidecar disagrees with the lake", () => {
    const { failures } = checkDistrictYearSample({
      sample: [{ ...SAMPLE[0], total: 999_999_999 }],
      truth: TRUTH,
      readRendered: rendered(),
    });
    expect(failures[0]).toContain("lake=124413254.06");
  });

  it("FAILS when the built page renders no row for a published cell", () => {
    const { failures } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: () => null,
    });
    expect(failures[0]).toContain("renders no [data-district-year");
  });

  it("FAILS when the rendered figure carries no citation", () => {
    const { failures } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: rendered({ cited: false }),
    });
    expect(failures[0]).toContain("without its receipt");
  });

  it("FAILS when the page renders a number the lake does not support", () => {
    const { failures } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: rendered({ amount: 98_700_000 }),
    });
    expect(failures[0]).toContain("the page renders");
  });

  it("FAILS when the rendered text is not a single currency figure", () => {
    const { failures } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: rendered({ amount: null }),
    });
    expect(failures[0]).toContain("not a single parseable currency value");
  });

  // ── fix round 1: the gross cell (Important 4) ────────────────────────────

  it("does not check a gross cell the page does not render", () => {
    // gross == net, so the page legitimately renders no gross column.
    const { failures, checked, grossChecked } = checkDistrictYearSample({
      sample: [{ district: "ZZ-04", fy: 2019, total: 124413254.06, positive: 124413254.06 }],
      truth: {
        "ZZ-04|2019": {
          award_count: 12,
          total_obligation: 124413254.06,
          positive_obligation: 124413254.06,
        },
      },
      readRendered: rendered(),
    });
    expect(failures).toEqual([]);
    expect(checked).toBe(1);
    expect(grossChecked).toBe(0);
  });

  it("checks the gross cell when the page renders one", () => {
    const { failures, checked, grossChecked } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: renderedWithGross(),
    });
    expect(failures).toEqual([]);
    expect(checked).toBe(1);
    expect(grossChecked).toBe(1);
  });

  it("FAILS when the RENDERED gross figure disagrees with the lake", () => {
    // The net cell is right — this is the second published figure per row that
    // had nothing binding it to anything before the fix round.
    const { failures, grossChecked } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: renderedWithGross({}, { amount: 98_700_000 }),
    });
    expect(failures).toHaveLength(1);
    expect(failures[0]).toContain("(gross)");
    expect(failures[0]).toContain("98700000");
    expect(failures[0]).toContain("125501811.59");
    expect(grossChecked).toBe(0);
  });

  it("FAILS when the SIDECAR's gross figure disagrees with the lake", () => {
    const { failures } = checkDistrictYearSample({
      sample: [{ ...SAMPLE[0], positive: 999_999_999 }],
      truth: TRUTH,
      readRendered: renderedWithGross(),
    });
    expect(failures[0]).toContain("(gross): sidecar=999999999");
    expect(failures[0]).toContain("lake=125501811.59");
  });

  it("FAILS when the rendered gross figure carries no citation", () => {
    const { failures } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: renderedWithGross({}, { cited: false }),
    });
    expect(failures[0]).toContain("(gross)");
    expect(failures[0]).toContain("without its receipt");
  });

  it("FAILS when a row whose gross exceeds its net renders no gross cell", () => {
    // The page renders the column for the whole district as soon as ONE year
    // has gross > net, so this row cannot legitimately be missing it.
    const { failures } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: rendered(),
    });
    expect(failures).toHaveLength(1);
    expect(failures[0]).toContain("must render a \"Before deobligations\" cell");
  });

  it("FAILS when a gross cell is rendered with no sidecar value behind it", () => {
    const { district, fy, total } = SAMPLE[0];
    const { failures } = checkDistrictYearSample({
      sample: [{ district, fy, total }],
      truth: TRUTH,
      readRendered: renderedWithGross(),
    });
    expect(failures[0]).toContain("no positive_obligation behind it");
  });

  // ── fix round 1: page rounding at small magnitudes (Minor 6) ─────────────

  it("accepts a sub-$10 cell rounded to integer dollars by the page", () => {
    // formatAmount renders 4.37 as "$4" (compactFormat's integer-dollar branch
    // under $1,000). valuesAgree's 3-significant-digit granularity at this
    // magnitude is 0.005, so the old comparison called this a disagreement.
    // No such cell is published today (the 120 sub-$10 cells are all exactly
    // $0.00, measured 2026-09-11) — this pins the latent flake shut.
    const { failures, checked } = checkDistrictYearSample({
      sample: [{ district: "ZZ-02", fy: 2025, total: 4.37 }],
      truth: {
        "ZZ-02|2025": {
          award_count: 1, total_obligation: 4.37, positive_obligation: 4.37,
        },
      },
      readRendered: () => ({ amount: 4, cited: true }),
    });
    expect(failures).toEqual([]);
    expect(checked).toBe(1);
  });

  it("still FAILS on a sub-$10 cell the page renders wrongly", () => {
    // The relaxation above is the page's own rounding, not a blanket tolerance.
    const { failures } = checkDistrictYearSample({
      sample: [{ district: "ZZ-02", fy: 2025, total: 4.37 }],
      truth: {
        "ZZ-02|2025": {
          award_count: 1, total_obligation: 4.37, positive_obligation: 4.37,
        },
      },
      readRendered: () => ({ amount: 9, cited: true }),
    });
    expect(failures).toHaveLength(1);
    expect(failures[0]).toContain("the page renders 9 where the lake says 4.37");
  });

  it("mirrors the page's sign-then-round on a negative sub-$1,000 cell", () => {
    // compactFormat rounds the ABSOLUTE value and reapplies the sign, so
    // -48.5 renders "-$49" where Math.round(-48.5) would be -48. (-48.5 sits
    // in the under-$1,000 whole-dollar branch; Task 26 renamed this test,
    // which said "sub-$10".)
    const { failures, checked } = checkDistrictYearSample({
      sample: [{ district: "ZZ-03", fy: 2025, total: -48.5 }],
      truth: {
        "ZZ-03|2025": {
          award_count: 1, total_obligation: -48.5, positive_obligation: 0,
        },
      },
      readRendered: () => ({ amount: -49, cited: true }),
    });
    expect(failures).toEqual([]);
    expect(checked).toBe(1);
  });
});

/**
 * Review r2 M-4 (R-DEC-LINK-2026-10-21 R4). Leg q pins IN-07's F-35 ROWS off
 * the shipped district page, not IN-07's totals. If fct_district_totals_by_year
 * alone regressed to the PIID-only join, IN-07 FY2022 would carry the
 * Rolls-Royce order sharing N0001922F0001 again ($162,388,806.00 instead of
 * $15,219,278.19, measured read-only 2026-10-21) and only a stride that
 * happened to land on that cell would see it. The cell is therefore always
 * sampled, beside the deterministic stride.
 */
describe("gate 24 leg r — the IN-07 FY2022 cell is always sampled (review r2 M-4)", () => {
  const cellsOf = (n, extra = []) => [
    ...Array.from({ length: n }, (_, i) => ({
      district: `ZZ-${String(i).padStart(2, "0")}`, fy: 2020, total: i, positive: i,
    })),
    ...extra,
  ];
  const IN07 = { district: "IN-07", fy: 2022, total: 15219278.19, positive: 15219278.19 };
  const key = (c) => `${c.district}|${c.fy}`;

  it("pins IN-07|2022", () => {
    expect(DISTRICT_YEAR_PINNED).toContain("IN-07|2022");
  });

  it("adds the pinned cell to the unchanged stride sample", () => {
    const cells = cellsOf(36, [IN07]);
    const { sample, missingPins } = sampleDistrictYearCells(cells);
    expect(missingPins).toEqual([]);
    // the stride is the leg's own: floor(37 / 12) = 3, cells 0, 3, ..., 33
    expect(sample.slice(0, 12).map(key)).toEqual(
      Array.from({ length: 12 }, (_, i) => key(cells[i * 3])),
    );
    expect(sample.map(key)).toContain("IN-07|2022");
    expect(sample).toHaveLength(13);
  });

  it("never samples the pinned cell twice", () => {
    // 12 cells: stride 1 lands on every cell, IN-07|2022 among them
    const cells = cellsOf(11, [IN07]);
    const { sample } = sampleDistrictYearCells(cells);
    expect(sample.filter((c) => key(c) === "IN-07|2022")).toHaveLength(1);
    expect(sample).toHaveLength(12);
  });

  it("reports a pinned cell the sidecars no longer publish", () => {
    const { sample, missingPins } = sampleDistrictYearCells(cellsOf(40));
    expect(missingPins).toEqual(["IN-07|2022"]);
    expect(sample).toHaveLength(12);
  });

  it("catches the totals regressed to the PIID-only join on IN-07 FY2022", () => {
    const regressed = { ...IN07, total: 162388806.0, positive: 173136574.12 };
    const { sample } = sampleDistrictYearCells(cellsOf(36, [regressed]));
    const truth = Object.fromEntries(
      sample.map((c) => [key(c), {
        award_count: 1, total_obligation: c.total, positive_obligation: c.positive,
      }]),
    );
    // the helper restates the named-award rule: 4 awards, $15,219,278.19
    truth["IN-07|2022"] = {
      award_count: 4, total_obligation: 15219278.19, positive_obligation: 15219278.19,
    };
    const { failures } = checkDistrictYearSample({
      sample, truth, readRendered: () => null,
    });
    expect(failures.join("\n")).toMatch(/IN-07\|2022: sidecar=162388806 lake=15219278\.19/);
  });
});
