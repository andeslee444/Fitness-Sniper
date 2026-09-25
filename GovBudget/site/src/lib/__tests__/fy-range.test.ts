import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * §P1-6: one derived period, one wording. The site used to state the
 * USAspending aggregate period three ways — "FY2017–FY2025" on /companies/
 * (a year short of the data), "across the full USAspending dataset" on a
 * company page, and nothing at all on /district/, where a $3.66T figure sat
 * in a card with no period.
 *
 * Hermetic: the real sidecars must not be read — getSiteMeta is mocked.
 * awardFyRangeLabel mirrors award_fy_range_label() in export_site.py.
 */

const state = {
  meta: {} as Record<string, unknown>,
};

vi.mock("@/lib/data", () => ({
  getSiteMeta: () => state.meta,
}));

const { awardFyRangeLabel, getAwardFyRange } = await import("@/lib/fy-range");

beforeEach(() => {
  state.meta = {
    award_fy_range: {
      fy_min: 2017,
      fy_max: 2026,
      label: "FY2017–FY2026",
      latest_action_date: "2026-04-23",
      max_partial: true,
    },
  };
});

describe("awardFyRangeLabel", () => {
  it("renders the canonical shape", () => {
    expect(awardFyRangeLabel(2017, 2026)).toBe("FY2017–FY2026");
  });

  it("collapses a single-year range", () => {
    expect(awardFyRangeLabel(2025, 2025)).toBe("FY2025");
  });

  it("uses an en dash, never a hyphen", () => {
    expect(awardFyRangeLabel(2017, 2026)).not.toContain("-");
    expect(awardFyRangeLabel(2017, 2026)).toContain("–");
  });

  it("throws on an inverted range rather than rendering it backwards", () => {
    expect(() => awardFyRangeLabel(2026, 2017)).toThrow(/inverted/i);
  });

  it("throws on non-integer fiscal years", () => {
    expect(() => awardFyRangeLabel(2017.5, 2026)).toThrow(/non-integer/i);
  });
});

describe("getAwardFyRange", () => {
  it("reads the exporter-derived range", () => {
    const r = getAwardFyRange();
    expect(r).not.toBeNull();
    expect(r!.label).toBe("FY2017–FY2026");
    expect(r!.fyMin).toBe(2017);
    expect(r!.fyMax).toBe(2026);
    expect(r!.maxPartial).toBe(true);
  });

  it("names the partial final year in the title, with the data's own last date", () => {
    // Task 26: "it does not close until September 30" was a claim about the
    // CALENDAR, false from 2026-10-01 while max_partial (a claim about the
    // DATA) stays true for this corpus. The title now says where the data ends.
    const r = getAwardFyRange()!;
    expect(r.title).toMatch(/FY2026 is a partial year — data through 2026-04-23\./);
    expect(r.title).not.toMatch(/September 30|does not close|still open/);
    expect(r.latestActionDate).toBe("2026-04-23");
  });

  it("states the partial year without a date when the export carries none", () => {
    state.meta = {
      award_fy_range: {
        fy_min: 2017,
        fy_max: 2026,
        label: "FY2017–FY2026",
        latest_action_date: null,
        max_partial: true,
      },
    };
    const r = getAwardFyRange()!;
    expect(r.title).toMatch(/FY2026 is a partial year\.$/);
    expect(r.latestActionDate).toBeNull();
  });

  it("omits the partial-year sentence when the final year has closed", () => {
    state.meta = {
      award_fy_range: {
        fy_min: 2017,
        fy_max: 2025,
        label: "FY2017–FY2025",
        latest_action_date: "2025-09-30",
        max_partial: false,
      },
    };
    const r = getAwardFyRange()!;
    expect(r.title).toBe(
      "USAspending award obligations across fiscal years 2017 through 2025.",
    );
    expect(r.title).not.toMatch(/partial/);
  });

  it("returns null when the export carries no range (degenerate export)", () => {
    state.meta = {};
    expect(getAwardFyRange()).toBeNull();
    state.meta = { award_fy_range: null };
    expect(getAwardFyRange()).toBeNull();
  });

  it("THROWS when the exporter's label and this module's have drifted apart", () => {
    // The whole point of "one wording": a Python change that is not mirrored
    // here must fail the build, not ship two vocabularies.
    state.meta = {
      award_fy_range: {
        fy_min: 2017,
        fy_max: 2026,
        label: "FY2017-FY2026", // hyphen, not en dash
        latest_action_date: "2026-04-23",
        max_partial: true,
      },
    };
    expect(() => getAwardFyRange()).toThrow(/drifted apart/i);
  });
});
