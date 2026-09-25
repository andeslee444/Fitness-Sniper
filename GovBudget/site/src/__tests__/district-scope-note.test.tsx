/**
 * Task 26 (final review): what the /district/ pages say a published link
 * rests on.
 *
 * Both templates said a link is published only where "a contract announcement
 * that names the program, or an account plus program-specific tokens" says so.
 * The pages count only high-confidence links, and on the run-4 export that
 * disjunction left out 25 of the 1,133 high links (adjudicator-pinned account
 * and account+subagency matches), while "names the program" claimed more than
 * /methodology/ §4 does for an announcement link whose match basis went
 * unrecorded. They now state their own scope — high-confidence links, where
 * more than an account code ties the award to the program — and point at §4
 * for what that evidence is, rather than enumerating paths a tier change would
 * falsify.
 *
 * And the index's complement ("N of M program elements have no …") is the
 * pages drawing no follow-the-dollar view, which is what programs.json rows −
 * district-linkable counts; "no district-level linkage" was 3 fewer.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import type { DistrictDetail, DistrictIndex } from "@/lib/data";

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

const INDEX: DistrictIndex = {
  districts: [
    {
      pop_district: "ZZ-01",
      pop_state: "ZZ",
      program_count: 1,
      award_count: 1,
      total_cited_dollars: 1_000_000,
      total_cited_fact_id: null,
      total_linkable_dollars: 1_000_000,
      total_linkable_fact_id: null,
    },
  ],
  geo_grand_total: 90_000_000,
  geo_grand_total_dataset: "dim_geography",
  geo_grand_total_fact_id: null,
  total_districts: 1,
};

const DETAIL: DistrictDetail = {
  pop_district: "ZZ-01",
  pop_state: "ZZ",
  program_count: 0,
  award_count: 1,
  programs: [],
  by_year: [],
  by_year_programs: [],
  total_cited_dollars: 1_000_000,
  total_cited_fact_id: null,
  total_linkable_dollars: 1_000_000,
  total_linkable_fact_id: null,
};

vi.mock("@/lib/data", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/data")>()),
  getDistrictIndex: () => INDEX,
  getDistrictDetail: () => DETAIL,
  getProgramsCount: () => 1938,
}));

vi.mock("@/lib/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/corpus")>()),
  crosswalkValue: () => 314,
}));

vi.mock("@/lib/og", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/og")>()),
  coreOgImages: () => [],
}));

const text = (el: Element) => el.textContent!.replace(/\s+/g, " ");

async function scopeNote(which: "index" | "detail"): Promise<string> {
  const el =
    which === "index"
      ? (await import("@/app/district/page")).default()
      : await (await import("@/app/district/[district]/page")).default({
          params: Promise.resolve({ district: "ZZ-01" }),
        });
  const { container } = render(el as React.ReactElement);
  return text(container);
}

describe.each(["index", "detail"] as const)("/district/ %s scope note", (which) => {
  it("scopes the mechanism to high-confidence links and points at §4 for the evidence", async () => {
    const t = await scopeNote(which);
    expect(t).toMatch(/more than an account code ties the award to (it|the program)/);
    expect(t).toContain("methodology §4 says what does");
  });

  it("never enumerates the tier as announcement-names-the-program or account-plus-tokens", async () => {
    const t = await scopeNote(which);
    expect(t).not.toMatch(/announcement that names the program/);
    expect(t).not.toMatch(/account plus program-specific tokens/);
  });
});

describe("/district/ index complement", () => {
  it("counts the program elements with no follow-the-dollar view", async () => {
    const t = await scopeNote("index");
    expect(t).toContain("1,624 of 1,938 program elements have no follow-the-dollar view");
    expect(t).not.toContain("district-level linkage");
  });
});
