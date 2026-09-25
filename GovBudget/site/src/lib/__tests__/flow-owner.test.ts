/**
 * Task 26 (Critical, coverage.ts:89): which program page draws each flows
 * sidecar, and what a page with no view may truthfully say about why.
 *
 * THE DEFECT THIS PINS. flows/{pe_bli}.json is keyed by the BARE code, and
 * the page for a member of a shared code ('0145-APN') is addressed by its
 * slug — so five member pages that list high-confidence awards rendered "this
 * program's awards haven't been crosswalked at high confidence", while
 * /district/ pages linked those same members as high-confidence. And /coverage/
 * printed the sidecar count (314) as "programs [that] have a follow-the-dollar
 * view", four more than drew one.
 *
 * The member-grain district mart says whose links a shared sidecar holds: on
 * the run-4 export every shared code with a sidecar (0145, 2292, 3010, 3215)
 * has district rows under exactly ONE member's split_key, and that member's
 * own high-confidence links are every award the sidecar draws. So that member
 * draws it — and a code whose district rows name two members, or no member
 * (an organization split carries split_key === pe_bli), is owned by nobody.
 */
import { describe, it, expect } from "vitest";
import {
  flowAbsenceReason,
  flowSidecarOwners,
} from "@/lib/flow-owner";

const programs = [
  { slug: "0603114N", pe_bli: "0603114N" },
  { slug: "0145-APN", pe_bli: "0145" },
  { slug: "0145-PANMC", pe_bli: "0145" },
  { slug: "3215-WPN", pe_bli: "3215" },
  { slug: "3215-OPN", pe_bli: "3215" },
  { slug: "20-DCSA", pe_bli: "20" },
  { slug: "20-DTRA", pe_bli: "20" },
];

describe("flowSidecarOwners", () => {
  it("an ordinary code's sidecar is drawn by the page of the same name", () => {
    const owners = flowSidecarOwners({
      sidecars: ["0603114N"],
      programs,
      districtMemberKeys: new Map([["0603114N", new Set(["0603114N"])]]),
    });
    expect([...owners]).toEqual([["0603114N", "0603114N"]]);
  });

  it("a shared code's sidecar is drawn by the one member the district mart files it under", () => {
    const owners = flowSidecarOwners({
      sidecars: ["0145"],
      programs,
      districtMemberKeys: new Map([["0145", new Set(["0145-APN"])]]),
    });
    expect(owners.get("0145")).toBe("0145-APN");
    // ...and never by the sibling, whose own links name no place of performance.
    expect([...owners.values()]).not.toContain("0145-PANMC");
  });

  it("no page draws a shared sidecar whose district rows span two members", () => {
    const owners = flowSidecarOwners({
      sidecars: ["3215"],
      programs,
      districtMemberKeys: new Map([["3215", new Set(["3215-WPN", "3215-OPN"])]]),
    });
    expect(owners.has("3215")).toBe(false);
  });

  it("no page draws an organization-split code's sidecar (its rows name no member)", () => {
    const owners = flowSidecarOwners({
      sidecars: ["20"],
      programs,
      districtMemberKeys: new Map([["20", new Set(["20"])]]),
    });
    expect(owners.has("20")).toBe(false);
  });

  it("no page draws a sidecar with no programs.json row or no district rows", () => {
    const owners = flowSidecarOwners({
      sidecars: ["9999", "0145"],
      programs,
      districtMemberKeys: new Map(),
    });
    expect(owners.size).toBe(0);
  });
});

describe("flowAbsenceReason", () => {
  it("a page with no high-confidence link says its awards were not crosswalked at high", () => {
    expect(flowAbsenceReason([])).toBe("no-high-link");
    expect(flowAbsenceReason([{ confidence: "medium" }])).toBe("no-high-link");
  });

  it("a page WITH high-confidence links never says they were not crosswalked", () => {
    expect(
      flowAbsenceReason([{ confidence: "medium" }, { confidence: "high" }]),
    ).toBe("no-place-of-performance");
  });
});
