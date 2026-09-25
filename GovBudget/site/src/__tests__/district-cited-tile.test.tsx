/**
 * /district/{code}/ — one tile while cited equals linkable TO THE CENT, two
 * the moment they differ (2026-09-25 final integration review, finding #5).
 *
 * THE DEFECT. The page chose between its single-tile state ("every linked
 * dollar carries a USAspending citation") and its two-tile state ("$X of
 * which cited (USAspending)") with an exact float ===. Both totals are float
 * sums of per-program obligations and the exporter's clamp does not round,
 * so 14 districts differed by less than a cent on float noise alone: AL-02
 * shipped cited 4,589,898,661.98 against linkable 4,589,898,661.9800005 and
 * rendered two identical $4.59B tiles — the duplication §P1-6 removed — and
 * every re-export picked a different set (CO-06 flipped the other way).
 * Pre-existing on both parents and in production.
 *
 * Same seams as district-scope-note.test.tsx: the page is an async server
 * component whose data doors are @/lib/data and @/lib/fy-range.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import React from "react";
import type { DistrictDetail } from "@/lib/data";

vi.mock("@/lib/fy-range", () => ({
  getAwardFyRange: () => ({
    fyMin: 2017,
    fyMax: 2026,
    maxPartial: false,
    label: "FY2017–FY2026",
    latestActionDate: "2026-09-04",
  }),
}));

vi.mock("@/components/citation-panel", () => ({
  CitationPanelProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

let detail: DistrictDetail;

vi.mock("@/lib/data", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/data")>()),
  getDistrictIndex: () => ({
    districts: [{ pop_district: "ZZ-01", total_linkable_dollars: detail.total_linkable_dollars }],
    geo_grand_total: 90_000_000_000,
  }),
  getDistrictDetail: () => detail,
}));

afterEach(cleanup);

const SINGLE = "every linked dollar carries a USAspending citation";
const SECOND = "of which cited (USAspending)";

async function tiles(cited: number, linkable: number) {
  detail = {
    pop_district: "ZZ-01",
    pop_state: "ZZ",
    program_count: 0,
    award_count: 1,
    programs: [],
    by_year: [],
    by_year_programs: [],
    total_cited_dollars: cited,
    total_cited_fact_id: null,
    total_linkable_dollars: linkable,
    total_linkable_fact_id: null,
  };
  const Page = (await import("@/app/district/[district]/page")).default;
  const el = await Page({ params: Promise.resolve({ district: "ZZ-01" }) });
  const text = render(el as React.ReactElement).container.textContent!.replace(/\s+/g, " ");
  return { single: text.includes(SINGLE), second: text.includes(SECOND) };
}

describe("/district/{code}/ cited-vs-linkable tiles", () => {
  it("one tile when the totals are exactly equal", async () => {
    expect(await tiles(1_000_000, 1_000_000)).toEqual({ single: true, second: false });
  });

  it("one tile on float noise below a cent — AL-02's shipped pair", async () => {
    expect(await tiles(4_589_898_661.98, 4_589_898_661.9800005)).toEqual({
      single: true,
      second: false,
    });
  });

  it("one tile on noise in either operand — CO-06's shipped pair", async () => {
    expect(await tiles(4_679_796_603.66, 4_679_796_603.660001)).toEqual({
      single: true,
      second: false,
    });
  });

  it("two tiles on a real gap — CA-51's shipped pair ($340,858)", async () => {
    expect(await tiles(85_700_487.26, 86_041_345.82)).toEqual({ single: false, second: true });
  });

  it("two tiles on a one-cent gap: equality is to the cent, not approximate", async () => {
    expect(await tiles(1_000_000.0, 1_000_000.01)).toEqual({ single: false, second: true });
  });
});
