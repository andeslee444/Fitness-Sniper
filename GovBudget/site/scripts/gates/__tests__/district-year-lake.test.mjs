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
import { checkDistrictYearSample } from "../datatruth.mjs";

const SAMPLE = [{ district: "ZZ-01", fy: 2019, total: 124413254.06 }];
const TRUTH = {
  "ZZ-01|2019": {
    award_count: 12,
    total_obligation: 124413254.06,
    positive_obligation: 125501811.59,
  },
};
/** What the built page shows: formatAmount renders this as "$124.4M". */
const rendered = (over = {}) => () => ({ amount: 124400000, cited: true, ...over });

describe("gate 24 leg r — district-year cells vs the lake and the page", () => {
  it("passes when sidecar, lake and rendered figure agree", () => {
    const { failures, checked } = checkDistrictYearSample({
      sample: SAMPLE,
      truth: TRUTH,
      readRendered: rendered(),
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
});
