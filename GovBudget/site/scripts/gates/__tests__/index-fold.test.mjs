/**
 * Proof-it-can-fail for gate 16's index-fold leg. Every number is the
 * measurement taken on the deployed build 2026-09-10, before the reordering:
 * the first data row inside each page's first data block.
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
});
