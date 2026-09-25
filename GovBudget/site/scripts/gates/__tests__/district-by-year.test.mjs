/**
 * Unit tests for gate 9 leg (f) — the /district/{code}/ by-year table adds up,
 * and the leg is not vacuous (ROADMAP #6).
 *
 * The floor is why this file exists. "Every by-year row sums to the headline"
 * is PERFECTLY satisfied by a corpus in which no district has a by_year array
 * at all — which is exactly what an export run against a warehouse built before
 * the by-year marts existed produces (_emit_district_sidecars degrades to an
 * empty list by design, so the other sidecar fields still ship). These tests
 * pin that the leg cannot pass on that.
 *
 * Synthetic districts are used so the leg never touches site/out.
 *
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import { runDistrictByYearLeg } from "../district.mjs";

/** The corpus shape measured 2026-09-10 against data/duckdb/govbudget.duckdb,
 *  transposed onto synthetic district codes: 153 districts, 924 by-year rows.
 *  (Chain C run 4, 2026-09-25, published 189 districts and 1,266 rows; the
 *  counts only exercise the logic.) Rows are spread as evenly as the
 *  counts allow — base years each, remainder one extra — so that `districts`
 *  districts carry exactly `rows` rows between them and EVERY district carries
 *  at least one whenever rows >= districts. (A generator that truncates
 *  trailing districts would silently test a different corpus than the one the
 *  floor cases name.) */
function corpus({ districts = 153, rows = 924, breakDistricts = [] } = {}) {
  const broken = new Set(breakDistricts);
  const base = Math.floor(rows / districts);
  const remainder = rows - base * districts;
  const out = [];
  for (let i = 0; i < districts; i++) {
    const nYears = base + (i < remainder ? 1 : 0);
    const by_year = [];
    for (let y = 0; y < nYears; y++) {
      by_year.push({
        fiscal_year: 2017 + y,
        award_count: 3,
        total_obligation: 1_000_000,
        total_fact_id: `f${i}${y}`.padEnd(16, "0"),
        positive_obligation: 1_100_000,
        positive_fact_id: `p${i}${y}`.padEnd(16, "0"),
      });
    }
    const code = `ZZ-${String(i).padStart(3, "0")}`;
    const sum = by_year.reduce((s, r) => s + r.total_obligation, 0);
    out.push({
      pop_district: code,
      total_linkable_dollars: broken.has(code) ? sum + 1_000 : sum,
      by_year,
    });
  }
  return out;
}

function run(sidecars) {
  const errors = [];
  const notes = [];
  runDistrictByYearLeg({ errors, notes, sidecars });
  return { errors, notes };
}

describe("gate 9 leg f — by-year sum vs the page headline", () => {
  it("passes on the 2026-09-10 corpus shape and says what it saw", () => {
    const { errors, notes } = run(corpus());
    expect(errors).toEqual([]);
    expect(notes[0]).toContain("153 district(s)");
    expect(notes[0]).toContain("924 by-year row(s)");
  });

  it("FAILS when one district's years stop adding up to its headline", () => {
    const { errors } = run(corpus({ breakDistricts: ["ZZ-007"] }));
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("ZZ-007");
    expect(errors[0]).toContain("by-year rows sum to");
  });

  it("FAILS when no district carries a by_year array at all", () => {
    const empty = corpus().map((d) => ({ ...d, by_year: [] }));
    const { errors, notes } = run(empty);
    expect(notes).toEqual([]);
    expect(errors.some((e) => e.includes("0 district(s) carry a by-year table"))).toBe(true);
    expect(errors.some((e) => e.includes("do not lower"))).toBe(true);
  });

  it("FAILS just below the district floor and passes at it", () => {
    expect(run(corpus({ districts: 129, rows: 850 })).errors[0]).toContain(
      "129 district(s) carry a by-year table (floor 130",
    );
    expect(run(corpus({ districts: 130, rows: 850 })).errors).toEqual([]);
  });

  it("FAILS when the row count collapses even though every district has one year", () => {
    // 153 districts, one year each: the per-district check is satisfied and the
    // district floor is met, but nine tenths of the table is gone.
    const { errors } = run(corpus({ districts: 153, rows: 153 }));
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("153 by-year row(s) (floor 800");
  });

  it("FAILS on a by-year row with no resolving citation", () => {
    const c = corpus();
    c[3].by_year[0].total_fact_id = null;
    const { errors } = run(c);
    expect(errors.some((e) => e.includes("carries no total_fact_id"))).toBe(true);
  });

  // ── fix round 1 ──────────────────────────────────────────────────────────

  it("reports the TRUE number of broken districts, not the detail cap", () => {
    // The cap used to sit inside the detection condition, so this corpus
    // reported "5 district(s)" (Important 3). Six is deliberately one past it.
    const broken = ["ZZ-001", "ZZ-002", "ZZ-003", "ZZ-004", "ZZ-005", "ZZ-006"];
    const { errors } = run(corpus({ breakDistricts: broken }));
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("6 district(s) whose by-year rows do not sum");
    // Five named, the sixth counted and declared rather than dropped.
    for (const code of broken.slice(0, 5)) expect(errors[0]).toContain(code);
    expect(errors[0]).toContain("(+1 more)");
  });

  it("reports the TRUE number of uncited figures, not the detail cap", () => {
    const c = corpus();
    for (let i = 0; i < 6; i++) c[i].by_year[0].total_fact_id = null;
    const { errors } = run(c);
    const uncitedError = errors.find((e) => e.includes("uncited by-year figure"));
    expect(uncitedError).toContain("6 uncited by-year figure(s)");
    expect(uncitedError).toContain("(+1 more)");
  });

  it("FAILS on a row missing ONLY its positive_fact_id", () => {
    // Minor 9: the gross figure is rendered on every district with a
    // deobligation, so a row cited on the net half only is half-uncited.
    const c = corpus();
    c[3].by_year[0].positive_fact_id = null;
    const { errors } = run(c);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("1 uncited by-year figure(s)");
    expect(errors[0]).toContain("carries no positive_fact_id");
    expect(errors[0]).not.toContain("(+");
  });
});
