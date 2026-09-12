import { describe, it, expect } from "vitest";
import { uningestedCoverageOrgsFrom } from "@/lib/data";

/** The shape data/site publishes, transposed onto synthetic slugs (measured
 *  2026-09-10: DHA 14 = 13 rollup + 1 synthesized full-tier, DEFW 4, IG 1;
 *  71 rollup + 2 full-tier workbook-only pages in all). */
function corpus() {
  const sidecars = new Map<string, Record<string, unknown>>();
  const orgBySlug = new Map<string, string>();
  const wb = (org: string, tier?: string) => ({
    details: [],
    narratives: [],
    budget_lines: [{}],
    ...(tier ? { tier, service_org: org } : {}),
  });
  for (let i = 0; i < 13; i++) sidecars.set(`R-DHA-${i}`, wb("DHA", "rollup"));
  for (let i = 0; i < 4; i++) sidecars.set(`R-DEFW-${i}`, wb("DEFW", "rollup"));
  sidecars.set("R-IG-0", wb("IG", "rollup"));
  // ingested rollup pages — the OTHER branch of the note, excluded
  for (let i = 0; i < 25; i++) sidecars.set(`R-N-${i}`, wb("N", "rollup"));
  // the one rollup sidecar with an empty service_org
  sidecars.set("R-EMPTY", wb("", "rollup"));
  // the two synthesized full-tier workbook-only pages (no tier, no service_org)
  sidecars.set("F-DHA", wb("DHA"));
  orgBySlug.set("F-DHA", "DHA");
  sidecars.set("F-A", wb("A")); // org A IS ingested -> excluded
  orgBySlug.set("F-A", "A");
  // a decade sidecar (no workbook line) and a page with real detail
  sidecars.set("D-0", { details: [], narratives: [], budget_lines: [], tier: "decade" });
  sidecars.set("F-DETAIL", { details: [{}], narratives: [{}], budget_lines: [{}] });
  orgBySlug.set("F-DETAIL", "DHA");
  return { sidecars, orgBySlug };
}

const INGESTED = new Set(["A", "N", "F", "OSD"]);

describe("uningestedCoverageOrgsFrom (ROADMAP #14)", () => {
  it("counts exactly the pages that say a book is missing, by org", () => {
    const { sidecars, orgBySlug } = corpus();
    expect(uningestedCoverageOrgsFrom(sidecars, orgBySlug, INGESTED)).toEqual([
      { org: "DHA", pages: 14 },
      { org: "DEFW", pages: 4 },
      { org: "IG", pages: 1 },
    ]);
  });

  it("excludes orgs whose book IS loaded — they render the other branch", () => {
    const { sidecars, orgBySlug } = corpus();
    const got = uningestedCoverageOrgsFrom(sidecars, orgBySlug, INGESTED);
    expect(got.map((o) => o.org)).not.toContain("N");
    expect(got.map((o) => o.org)).not.toContain("A");
  });

  it("counts a synthesized full-tier page under its programs.json org", () => {
    // The 2026-09-10 defect: these sidecars carry no service_org at all, so
    // a service_org-only reading drops them and /methodology/ under-counts
    // the pages that blame a missing book.
    const { sidecars, orgBySlug } = corpus();
    sidecars.delete("F-DHA");
    const got = uningestedCoverageOrgsFrom(sidecars, orgBySlug, INGESTED);
    expect(got.find((o) => o.org === "DHA")?.pages).toBe(13);
  });

  it("ignores decade sidecars and pages that carry detail", () => {
    const { sidecars, orgBySlug } = corpus();
    const before = uningestedCoverageOrgsFrom(sidecars, orgBySlug, INGESTED);
    sidecars.set("D-1", { details: [], narratives: [], budget_lines: [], tier: "decade" });
    sidecars.set("F-DETAIL2", { details: [{}], narratives: [], budget_lines: [{}] });
    orgBySlug.set("F-DETAIL2", "DEFW");
    expect(uningestedCoverageOrgsFrom(sidecars, orgBySlug, INGESTED)).toEqual(before);
  });

  it("returns [] when every org is loaded — the clause must drop cleanly", () => {
    const { sidecars, orgBySlug } = corpus();
    const all = new Set([...INGESTED, "DHA", "DEFW", "IG"]);
    expect(uningestedCoverageOrgsFrom(sidecars, orgBySlug, all)).toEqual([]);
  });
});
