/**
 * /district/{code}/ — the partial-year footnote, and the lede's honesty about
 * display rounding (ROADMAP #6, fix round 1: Critical 2 and Minor 5).
 *
 * THE DEFECT. The footnote was gated on `partialFy !== null` — i.e. on
 * site_meta.award_fy_range.max_partial, which is SITEWIDE and true on every
 * district page — rather than on this table containing that year. Only 67 of
 * 153 districts had an FY2026 row when that was measured (2026-09-11; 110 of
 * 189 on the 2026-09-25 run-4 export); on the others the page asserted
 * "FY2026 … is a part-year total" about a figure that is not in the table.
 * The first two tests pin both directions of that gate. Task 26 added the two
 * after them, which pin what the footnote may SAY: where this corpus's data
 * for the year ends — never that the year "is still open", a claim about the
 * calendar that turns false on Oct 1 while max_partial stays true.
 *
 * The page is an async server component; @/lib/data and @/lib/fy-range are the
 * only data doors it opens, so mocking those two renders the real markup. The
 * citation panel is stubbed to a passthrough: <Cite> needs no provider (it has
 * a default context) and the real provider fetches /config.json, which jsdom
 * cannot resolve.
 */

import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import type { DistrictDetail, DistrictYear } from "@/lib/data";

const PARTIAL_FY = 2026;
/** site_meta.award_fy_range.latest_action_date — null on an export without one. */
let latestActionDate: string | null = "2026-09-04";

vi.mock("@/lib/fy-range", () => ({
  getAwardFyRange: () => ({
    fyMin: 2017,
    fyMax: PARTIAL_FY,
    maxPartial: true,
    label: `FY2017–FY${PARTIAL_FY}`,
    latestActionDate,
  }),
}));

vi.mock("@/components/citation-panel", () => ({
  CitationPanelProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

/** The detail the page is handed. `years` are the fiscal years the table holds. */
let detail: DistrictDetail;

vi.mock("@/lib/data", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/data")>()),
  getDistrictIndex: () => ({
    districts: [{ pop_district: "ZZ-01", total_linkable_dollars: 3_000_000 }],
    geo_grand_total: 30_000_000,
  }),
  getDistrictDetail: () => detail,
}));

function year(fy: number): DistrictYear {
  return {
    fiscal_year: fy,
    award_count: 2,
    total_obligation: 1_000_000,
    total_fact_id: `t${fy}`.padEnd(16, "0"),
    positive_obligation: 1_000_000,
    positive_fact_id: `p${fy}`.padEnd(16, "0"),
  };
}

async function renderDistrict(years: number[]) {
  const by_year = years.map(year);
  detail = {
    pop_district: "ZZ-01",
    pop_state: "ZZ",
    program_count: 0,
    award_count: 5,
    programs: [],
    by_year,
    by_year_programs: [],
    total_cited_dollars: by_year.length * 1_000_000,
    total_cited_fact_id: null,
    total_linkable_dollars: by_year.length * 1_000_000,
    total_linkable_fact_id: null,
  };
  const Page = (await import("@/app/district/[district]/page")).default;
  const el = await Page({ params: Promise.resolve({ district: "ZZ-01" }) });
  const { container } = render(el as React.ReactElement);
  return container.textContent!.replace(/\s+/g, " ");
}

describe("/district/{code}/ partial-year footnote", () => {
  it("renders the footnote when the table reaches the partial year", async () => {
    latestActionDate = "2026-09-04";
    const text = await renderDistrict([2024, 2025, PARTIAL_FY]);
    expect(text).toContain("part-year total");
    // ...and the row itself is labelled, which is the claim the note explains.
    expect(text).toContain("partial year");
  });

  /**
   * Task 26. The footnote said "FY2026 is still open — it does not close
   * until September 30": a claim about the CALENDAR, false from 2026-10-01,
   * while its predicate (max_partial, a claim about the DATA) stays true for
   * this corpus — and the deploy was due after that date. It now says where
   * the corpus's data for that year ends, which is true on every date.
   */
  it("says where the data ends, never that the year is still open", async () => {
    latestActionDate = "2026-09-04";
    const text = await renderDistrict([2024, 2025, PARTIAL_FY]);
    expect(text).toContain(
      `FY${PARTIAL_FY} runs only through 2026-09-04 in this corpus`,
    );
    expect(text).not.toMatch(/still open|does not close|September 30/);
  });

  it("states the part-year without a date when the export carries none", async () => {
    latestActionDate = null;
    const text = await renderDistrict([2024, 2025, PARTIAL_FY]);
    expect(text).toContain(`FY${PARTIAL_FY} is a part-year total in this corpus`);
    expect(text).not.toMatch(/still open|does not close|September 30/);
    latestActionDate = "2026-09-04";
  });

  it("renders NO footnote when the table ends before the partial year", async () => {
    const text = await renderDistrict([2017, 2018, 2019]);
    // The table is there — this is not a vacuous pass.
    expect(text).toContain("Obligations by fiscal year");
    expect(text).toContain("FY2019");
    expect(text).not.toContain(`FY${PARTIAL_FY} runs only through`);
    expect(text).not.toContain("part-year total");
    expect(text).not.toContain("partial year");
  });

  it("the lede does not claim the displayed years add up exactly", async () => {
    const text = await renderDistrict([2017, 2018, 2019]);
    expect(text).toContain("The years add up to that total");
    expect(text).toContain("rounded for display");
    // Minor 5: the figures are 3-significant-digit compact USD, so a reader
    // adding what is on screen will not land on the displayed headline.
    expect(text).not.toContain("add up to that total exactly");
  });
});
