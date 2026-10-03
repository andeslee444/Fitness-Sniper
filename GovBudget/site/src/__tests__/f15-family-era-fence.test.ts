/**
 * Families piece 1 (spec 2026-10-02 §6.2): the /families/f-15/ page keeps
 * showing exactly the decade editions it showed before procurement history
 * reached PB2017 — every R-1 edition, P-1 from PB2024 on. Era P-1 points
 * (about 45 facts on F01500, F15EWS and F015EX) would exceed the page's
 * weight ceiling; F-15 keeps its own reviewed era history in
 * f15_funding_history.json.
 *
 * Hermetic: @/lib/data is mocked, so this runs without data/site.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Citation, DecadePoint, ProgramDetails, ProgramRow } from "@/lib/data";
import { F15_FIRST_P1_DECADE_EDITION, isF15ShownDecadePoint, loadRecord } from "@/lib/f15-family-data";

const state = vi.hoisted(() => ({ details: new Map<string, unknown>() }));

vi.mock("@/lib/data", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/data")>();
  return {
    ...real,
    getPrograms: () => [...state.details.keys()].map((slug) => ({ slug, title: `Program ${slug}` }) as unknown as ProgramRow),
    getProgramDetails: (slug: string) => state.details.get(slug) as ProgramDetails,
    getCitation: (factId: string) => ({
      kind: "workbook", fact_id: factId, units: "USD thousands", amount_thousands: 1,
      sheet: "Exhibit P-1", cells: "Q9", official_url: "https://example.mil/p1.xlsx",
      retrieved_at: "2026-07-01T00:00:00",
    }) as unknown as Citation,
  };
});

const point = (fy: number, edition: number, fid: string, measure: string): DecadePoint => ({ fy, v: 1000 + fy, fid, edition, basis: "toa", measure });

function setDetails(slug: string, exhibit: "P-1" | "R-1", series: ProgramDetails["decade_series"]) {
  state.details.set(slug, {
    budget_lines: [{ exhibit, fy: null, measure: null }],
    summary: { cards: [] },
    narratives: [],
    decade_series: series,
  });
}

beforeEach(() => state.details.clear());

describe("F-15 decade edition fence", () => {
  it("shows P-1 decade points from PB2024 on and every R-1 edition", () => {
    expect(F15_FIRST_P1_DECADE_EDITION).toBe(2024);
    expect(isF15ShownDecadePoint("P-1", { edition: 2023 })).toBe(false);
    expect(isF15ShownDecadePoint("P-1", { edition: 2024 })).toBe(true);
    expect(isF15ShownDecadePoint("R-1", { edition: 2017 })).toBe(true);
  });

  it("drops era P-1 points from a BLI record and keeps its modern points", () => {
    setDetails("F01500", "P-1", {
      actuals: [point(2017, 2019, "a017000000000001", "actuals"), point(2022, 2024, "a022000000000001", "actuals")],
      request: [point(2019, 2019, "b019000000000001", "request"), point(2024, 2024, "b024000000000001", "request")],
    });
    const record = loadRecord("F01500");
    expect(record.facts.map((fact) => [fact.fy, fact.edition, fact.factId])).toEqual([
      [2022, 2024, "a022000000000001"],
      [2024, 2024, "b024000000000001"],
    ]);
  });

  it("keeps every edition of an R-1 record", () => {
    setDetails("0207134F", "R-1", {
      request: [point(2017, 2017, "c017000000000001", "request"), point(2024, 2024, "c024000000000001", "request")],
    });
    expect(loadRecord("0207134F").facts.map((fact) => fact.edition)).toEqual([2017, 2024]);
  });
});
