/**
 * /district/{code}/ — two members of one shared budget-line code, each in its
 * own row (Task 27, 2026-09-19).
 *
 * THE DEFECT THIS PINS. fct_district_programs used to be grained on
 * (state, district, pe_bli), so the day both members of a shared code earned
 * high-confidence links in one district their dollars summed into a single
 * card under whichever title sorted first — ROADMAP #56's fusion shape. The
 * mart now carries the member's appropriation account and the sidecar row
 * carries its `split_key`, so the page renders one row per member. Two things
 * on this page assumed one row per pe_bli and had to move with it: the React
 * key, and the mono code rendered beside the title — which would otherwise
 * print "0145" twice and leave the reader no way to tell the two rows apart.
 *
 * Same seams as district-by-year-partial-fy.test.tsx: the page is an async
 * server component whose only data doors are @/lib/data and @/lib/fy-range.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import type { DistrictDetail, DistrictProgram } from "@/lib/data";

vi.mock("@/lib/fy-range", () => ({
  getAwardFyRange: () => ({
    fyMin: 2017,
    fyMax: 2026,
    maxPartial: false,
    label: "FY2017–FY2026",
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
    districts: [{ pop_district: "ZZ-01", total_linkable_dollars: 9_000_000 }],
    geo_grand_total: 90_000_000,
  }),
  getDistrictDetail: () => detail,
  collectCitations: () => ({}),
}));

function program(over: Partial<DistrictProgram>): DistrictProgram {
  return {
    account: null,
    award_count: 1,
    fact_id: null,
    organization: "N",
    pe_bli: "0145",
    program_url: "/program/0145/",
    recipient_count: 1,
    shared_award_count: 1,
    split_key: "0145",
    title: "A Program",
    total_obligation: 1_000_000,
    transaction_count: 1,
    ...over,
  };
}

/** The live shape of '0145' after the 2026-09-19 wave-4 load. */
const MEMBERS: DistrictProgram[] = [
  program({
    account: "1506N",
    split_key: "0145-APN",
    program_url: "/program/0145-APN/",
    title: "F/A-18E/F (Fighter) Hornet",
    total_obligation: 8_000_000,
  }),
  program({
    account: "1508N",
    split_key: "0145-PANMC",
    program_url: "/program/0145-PANMC/",
    title: "General Purpose Bombs",
    total_obligation: 2_000_000,
  }),
  program({
    pe_bli: "0601101E",
    split_key: "0601101E",
    program_url: "/program/0601101E/",
    title: "Defense Research Sciences",
    organization: "DARPA",
    total_obligation: 500_000,
  }),
];

async function renderDistrict(programs: DistrictProgram[]) {
  detail = {
    pop_district: "ZZ-01",
    pop_state: "ZZ",
    program_count: programs.length,
    award_count: 3,
    programs,
    by_year: [],
    by_year_programs: [],
    total_cited_dollars: 0,
    total_cited_fact_id: null,
    total_linkable_dollars: 10_500_000,
    total_linkable_fact_id: null,
  };
  const Page = (await import("@/app/district/[district]/page")).default;
  const el = await Page({ params: Promise.resolve({ district: "ZZ-01" }) });
  return render(el as React.ReactElement).container;
}

describe("/district/{code}/ shared-code members", () => {
  let errors: string[];
  let spy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    errors = [];
    spy = vi
      .spyOn(console, "error")
      .mockImplementation((...args: unknown[]) => void errors.push(String(args[0])));
  });
  afterEach(() => spy.mockRestore());

  it("gives each member its own row, labelled by its own split key", async () => {
    const container = await renderDistrict(MEMBERS);
    const rows = Array.from(
      container.querySelectorAll('table[data-sort-table="district-programs"] tbody tr')
    );
    expect(rows).toHaveLength(3);

    const codes = rows.map((r) => r.querySelector("span.font-mono")?.textContent);
    // NOT ["0145", "0145", …] — two rows printing one code name neither member.
    expect(codes).toEqual(["0145-APN", "0145-PANMC", "0601101E"]);

    // next/link normalises the sidecar's trailing slash away in this
    // environment; the slash itself is the exporter's contract, pinned in
    // tests/test_collision_slugs.py, not the page's.
    const hrefs = rows.map((r) => r.querySelector("a")?.getAttribute("href"));
    expect(hrefs).toEqual([
      "/program/0145-APN",
      "/program/0145-PANMC",
      "/program/0601101E",
    ]);
  });

  it("keys the rows uniquely, so React does not collapse or warn", async () => {
    await renderDistrict(MEMBERS);
    expect(
      errors.filter((e) => e.includes("same key") || e.includes("unique"))
    ).toEqual([]);
  });

  it("an ordinary district row is unchanged: bare code, bare link", async () => {
    const container = await renderDistrict([MEMBERS[2]]);
    const row = container.querySelector(
      'table[data-sort-table="district-programs"] tbody tr'
    )!;
    expect(row.querySelector("span.font-mono")?.textContent).toBe("0601101E");
    expect(row.querySelector("a")?.getAttribute("href")).toBe("/program/0601101E");
  });
});
