/**
 * Proof-it-can-fail for gate 16's index-fold leg.
 *
 * PRE_FIX is the measurement taken on the deployed build 2026-09-10, before
 * the reordering: the first data row inside each page's first data block.
 * Eight of those ten were below the fold; the helper has to say so.
 *
 * POST_FIX is the same ten cells re-measured on this branch (`next dev`,
 * Playwright, 2026-09-18) after Task 21d moved each caveat under its data
 * AND its fix round moved `/lineage/`'s own chart caption under its diagram
 * (`chart-figure.tsx` `captionPlacement="last"`). It is the live number the
 * gate should reproduce, kept here so the fixture is not frozen at a state
 * the site no longer has — `/lineage/` at 390 was 1,377 on the deployed
 * build, 1,049 after 21d, and 781 now.
 */
import { describe, it, expect } from "vitest";
import { indexFoldFindings } from "../answerfold.mjs";

const PRE_FIX = [
  { url: "/companies/", width: 1440, height: 900, top: 750 },
  { url: "/companies/", width: 390, height: 844, top: 843 },
  { url: "/district/", width: 1440, height: 900, top: 969 },
  { url: "/district/", width: 390, height: 844, top: 1214 },
  { url: "/years/", width: 1440, height: 900, top: 1106 },
  { url: "/years/", width: 390, height: 844, top: 865 },
  { url: "/lineage/", width: 1440, height: 900, top: 1189 },
  { url: "/lineage/", width: 390, height: 844, top: 1377 },
  { url: "/coverage/", width: 1440, height: 900, top: 1275 },
  { url: "/coverage/", width: 390, height: 844, top: 1494 },
];

/**
 * Re-measured on this branch 2026-09-18 with `next dev` and Playwright, the
 * same probe gate 16 runs. Headroom against each viewport, tightest first:
 * /lineage/ 390 = 63px, /district/ 390 = 97px, /years/ 1440 = 161px.
 */
const POST_FIX = [
  { url: "/companies/", width: 1440, height: 900, top: 590 },
  { url: "/companies/", width: 390, height: 844, top: 582 },
  { url: "/district/", width: 1440, height: 900, top: 431 },
  { url: "/district/", width: 390, height: 844, top: 747 },
  { url: "/years/", width: 1440, height: 900, top: 739 },
  { url: "/years/", width: 390, height: 844, top: 662 },
  { url: "/lineage/", width: 1440, height: 900, top: 561 },
  { url: "/lineage/", width: 390, height: 844, top: 781 },
  { url: "/coverage/", width: 1440, height: 900, top: 431 },
  { url: "/coverage/", width: 390, height: 844, top: 422 },
];

describe("indexFoldFindings", () => {
  it("reproduces the shipped defect on eight of the ten measurements", () => {
    const found = indexFoldFindings(PRE_FIX);
    // /companies/ passes at both widths — 750 of 900, and 843 of 844.
    expect(found).toHaveLength(8);
    expect(found.some((f) => f.includes("/companies/"))).toBe(false);
    expect(found.join(" ")).toContain("/coverage/ at 390x844");
    expect(found.join(" ")).toContain("1494");
    expect(found.join(" ")).toContain("650px below the fold");
  });

  it("passes once the first data row is inside the viewport", () => {
    expect(
      indexFoldFindings([
        { url: "/coverage/", width: 1440, height: 900, top: 420 },
        { url: "/coverage/", width: 390, height: 844, top: 500 },
      ]),
    ).toEqual([]);
  });

  it("fails a page whose data block was not found at all, rather than skipping it", () => {
    expect(indexFoldFindings([{ url: "/years/", width: 390, height: 844, top: null }])[0]).toContain("no [data-first-data]");
  });

  it("fails an empty measurement set", () => {
    expect(indexFoldFindings([])[0]).toContain("measured nothing");
  });

  it("finds nothing in the ten tops measured on this branch", () => {
    expect(indexFoldFindings(POST_FIX)).toEqual([]);
  });

  it("holds /lineage/ at 390 to the caption move that bought it — 781 of 844", () => {
    const lineage390 = POST_FIX.find(
      (r) => r.url === "/lineage/" && r.width === 390,
    );
    expect(lineage390.top).toBe(781);
    // 63px of headroom. The chart caption above the diagram was 260px of it
    // and the legend a further 108px; only the caption moved, and putting it
    // back is a 1,041px top — a finding, not a near miss.
    expect(indexFoldFindings([{ ...lineage390, top: 781 + 260 }])).toHaveLength(1);
    expect(indexFoldFindings([{ ...lineage390, top: 843 }])).toEqual([]);
    expect(indexFoldFindings([{ ...lineage390, top: 844 }])).toHaveLength(1);
  });
});
