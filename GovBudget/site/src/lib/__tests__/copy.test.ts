import { describe, it, expect } from "vitest";
import { count, countWord, callout, stamp, eyebrow, metaTitle, exhibitTitle, identityLine, emptyState, COPY, SHORTCUTS, fundingNote } from "@/lib/copy";
describe("copy smoke", () => {
  it("formats", () => {
    expect(count(1938, "defense budget line")).toBe("1,938 defense budget lines");
    expect(count(1, "record")).toBe("1 record");
    expect(countWord(3)).toBe("three"); expect(countWord(24)).toBe("24");
    expect(callout(9)).toBe("10"); expect(stamp(1, "Sea")).toBe("01 / Sea");
    expect(eyebrow("Field guide", "Air")).toBe("Field guide / Air");
    const row = { pe_bli: "2013", title: "Virginia Class Submarine", org: "N", exhibit_family: "procurement" };
    expect(exhibitTitle(row)).toBe("Navy procurement, BLI 2013");
    expect(identityLine(row)).toBe("Navy · BLI 2013 · Procurement");
    expect(metaTitle(row)).toBe("Virginia Class Submarine (BLI 2013) · Navy");
    const long = { ...row, title: "Space Based Infrared System (SBIRS) High Ground Segment Modernization Program" };
    expect(metaTitle(long).length).toBeLessThanOrEqual(60); expect(metaTitle(long)).toMatch(/…\) · Navy$|… \(BLI 2013\) · Navy$/);
    expect(fundingNote("toa", "rdte", 2026, 2026)).toBe("The figure is this line's TOA figure for FY2026, read from the R-1 of PB2026.");
    expect(COPY.program.empty.lineItemsDecade("BLI 2013")).toBe("No FY2026 line items for this program element. The FY2026 R-1 and P-1 workbooks carry no row for BLI 2013. Missing coverage is not zero spending.");
    expect(COPY.home.h1({ programs: 1938, companies: 200, agencies: 24 })).toBe("1,938 defense budget lines, each with its source.");
    expect(SHORTCUTS.map((s) => s.label)).toEqual(["Overview", "Budget & history", "Program detail", "Contracts & influence", "Oversight", "Sources"]);
    expect(COPY.program.empty.trajectory("BLI 2013")).toBe("No FY2024–FY2026 series for this line. The FY2026 R-1 and P-1 workbooks carry no row for BLI 2013. Missing coverage is not zero spending.");
  });
});
