/**
 * Task 26 (the final review's Critical): a member of a shared budget-line code
 * draws the flows sidecar it owns.
 *
 * On the run-4 export /program/0145-APN/ listed five high-confidence awards
 * and /district/MO-01/ linked it as a high-confidence program, yet its
 * follow-the-dollar section said its awards "haven't been crosswalked at high
 * confidence": the sidecar is flows/0145.json, named for the bare code, and
 * getFlowData looked for flows/0145-APN.json. It now asks lib/data which
 * sidecar the page draws (the one member the district mart files the code's
 * rows under — lib/flow-owner).
 *
 * The sidecar's HEADER is the bare code's: the exporter keys title, org and
 * the FY2026 total by pe_bli alone, so on a shared code it carries whichever
 * member was read last — flows/0145.json says "General Purpose Bombs",
 * $30,915K, the SIBLING's row, over the F/A-18's five awards. A member page
 * therefore draws its own programs.json row into the header, which is what
 * the exporter's header equals on every one of the 310 ordinary codes.
 */
import { describe, it, expect, vi } from "vitest";
import type { DistrictDetail, FlowSidecar, ProgramRow } from "@/lib/data";

const SIDECAR: FlowSidecar = {
  header: {
    pe_bli: "0145",
    title: "General Purpose Bombs",
    org: "N",
    fy2026_total: 30915,
  },
  awards: [
    {
      confidence: "high",
      district: "MO-01",
      dollars: 5_693_202_530,
      family_slug: "boeing",
      piid: "N0001918C1046",
      recipient_name: "THE BOEING COMPANY",
    },
  ],
};

const MO01: Pick<DistrictDetail, "programs"> = {
  programs: [
    {
      account: "1506N",
      award_count: 5,
      fact_id: "member-fid",
      organization: "N",
      pe_bli: "0145",
      program_url: "/program/0145-APN/",
      recipient_count: 1,
      shared_award_count: 1,
      split_key: "0145-APN",
      title: "F/A-18E/F (Fighter) Hornet",
      total_obligation: 9_000_000,
      transaction_count: 40,
    },
  ],
};

vi.mock("@/lib/data", () => ({
  getFlowSidecarForPage: (slug: string) => (slug === "0145-APN" ? "0145" : null),
  getFlow: (name: string) => (name === "0145" ? SIDECAR : null),
  getDistrictDetail: () => MO01,
  getEntityTopMap: () => new Map(),
}));

import { getFlowData } from "@/components/follow-the-dollar";

function row(over: Partial<ProgramRow>): ProgramRow {
  return {
    slug: "0145-APN",
    pe_bli: "0145",
    title: "F/A-18E/F (Fighter) Hornet",
    org: "N",
    trajectory: {
      n_org_components: 1,
      fy2024_actuals: 41329,
      fy2025_total: null,
      fy2026_total: 50607,
      fy2526_change: null,
      fy2526_pct_change: null,
    },
    ...over,
  } as ProgramRow;
}

describe("getFlowData — the member of a shared code", () => {
  it("draws the bare code's sidecar the member owns", () => {
    const data = getFlowData(row({}));
    expect(data).not.toBeNull();
    expect(data!.flow.awards.map((a) => a.piid)).toEqual(["N0001918C1046"]);
  });

  it("heads the view with the member's own title, org and FY2026 total — never the sibling's", () => {
    const { header } = getFlowData(row({}))!.flow;
    expect(header.title).toBe("F/A-18E/F (Fighter) Hornet");
    expect(header.fy2026_total).toBe(50607);
    expect(header.org).toBe("N");
    // The code the award record carries is still the bare one.
    expect(header.pe_bli).toBe("0145");
  });

  it("cites the member's own district row (split_key), not a bare-code one", () => {
    const rows = getFlowData(row({}))!.districtRows;
    expect(rows).toHaveLength(1);
    expect(rows[0].factId).toBe("member-fid");
    expect(rows[0].totalObligation).toBe(9_000_000);
  });

  it("draws nothing for the sibling, whose page owns no sidecar", () => {
    expect(
      getFlowData(row({ slug: "0145-PANMC", title: "General Purpose Bombs" })),
    ).toBeNull();
  });
});
