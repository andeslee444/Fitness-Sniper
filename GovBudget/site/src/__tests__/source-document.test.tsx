import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { citationSourceDocuments, citationSourceSlice, officialDocumentUrl } from "@/lib/source-document";
import { F15ProgramSources } from "@/components/family-entry";
import { SourceDocumentLinks } from "@/components/source-document-links";
import { getF15FamilyData } from "@/lib/f15-family-data";
import { getRecordFact } from "@/lib/f15-family";
import { trackReaderEvent } from "@/lib/reader-events";
import { resolveCitationFromShards } from "@/lib/cite-shards";

vi.mock("@/lib/reader-events", () => ({ trackReaderEvent: vi.fn() }));
vi.mock("@/lib/cite-shards", () => ({ resolveCitationFromShards: vi.fn() }));
afterEach(cleanup);
const family = getF15FamilyData();

describe("exact source document actions", () => {
  it("slices only the selected total and its inputs and labels the missing-TOA narrative fallback", () => {
    const slice = citationSourceSlice("4a9ae7cc78dcf0ba", family.citations);
    expect(Object.keys(slice)).toEqual(["4a9ae7cc78dcf0ba", "03407158217dec76", "5768200ce4fbc494", "819f32a0ad3fb66e"]);
    render(<F15ProgramSources programSlug="0207171F" />);
    expect(screen.getByText(/does not supply the missing FY2026 TOA figure/)).toBeVisible();
    expect(screen.getByRole("link", { name: /Open government PDF/ })).toHaveAttribute("href", family.citations[family.records.find(row => row.slug === "0207171F")!.narratives[0].factId].official_url);
  });
  it("resolves government workbooks for all six F-15 records without inventing derived source rows", () => {
    for (const record of family.records) {
      const fact = getRecordFact(record, 2026) ?? getRecordFact(record, 2024)!;
      const documents = citationSourceDocuments(family.citations[fact.factId], family.citations);
      expect(documents).toHaveLength(1);
      expect(documents[0].url).toMatch(/^https:\/\/comptroller\.war\.gov\/.+\.xlsx$/);
      expect(documents[0].locators.length).toBeGreaterThan(0);
      expect(documents[0].label).toBe("Open government spreadsheet");
    }
    const total = family.citations["4a9ae7cc78dcf0ba"];
    expect(total.official_url).toBeNull();
    expect(citationSourceDocuments(total, family.citations)[0].locators).toEqual(["Exhibit P-1 · W847", "Exhibit P-1 · W875", "Exhibit P-1 · W923,W932"]);
  });

  it("uses a recorded PDF page while leaving unresolved pages and spreadsheet URLs untouched", () => {
    expect(officialDocumentUrl({ official_url: "https://example.mil/book.pdf#page=2&zoom=150", page_number: 71 })).toBe("https://example.mil/book.pdf#page=71&zoom=150");
    expect(officialDocumentUrl({ official_url: "https://example.mil/book.pdf", page_number: null })).toBe("https://example.mil/book.pdf");
    expect(officialDocumentUrl({ official_url: "https://example.gov/book.xlsx", page_number: 71 })).toBe("https://example.gov/book.xlsx");
    expect(officialDocumentUrl({ official_url: "javascript:alert(1)", page_number: null })).toBeNull();
  });

  it("does not mislabel a mirror as a government host or loop through derived inputs", () => {
    const source = { ...family.citations["44f9ccc1f1518032"], official_url: "https://gov.example.com/saved.xlsx" };
    expect(citationSourceDocuments(source)[0].label).toBe("Open source spreadsheet");
    const root = family.citations["4a9ae7cc78dcf0ba"];
    if (root.kind !== "derived") throw new Error("Expected derived F-15EX total");
    const cycle = { ...root, inputs: '["4a9ae7cc78dcf0ba"]' };
    expect(citationSourceDocuments(cycle, { "4a9ae7cc78dcf0ba": cycle })).toEqual([]);
  });

  it("resolves missing inputs for a standalone total and retains honest failure state", async () => {
    vi.mocked(resolveCitationFromShards).mockImplementation(async id => family.citations[id] ?? null);
    const view = render(<SourceDocumentLinks citation={family.citations["4a9ae7cc78dcf0ba"]} resolveInputs />);
    expect(await screen.findByRole("link", { name: /Open government spreadsheet/ })).toHaveAttribute("href", "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx");
    view.unmount();
    vi.mocked(resolveCitationFromShards).mockResolvedValue(null);
    render(<SourceDocumentLinks citation={family.citations["4a9ae7cc78dcf0ba"]} resolveInputs />);
    expect(await screen.findByText(/Some source locations could not be loaded/)).toBeVisible();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("makes derived input documents prominent and measures the official action once", () => {
    render(<SourceDocumentLinks citation={family.citations["4a9ae7cc78dcf0ba"]} citations={family.citations} factId="4a9ae7cc78dcf0ba" program="F015EX" surface="citation-panel" />);
    const link = screen.getByRole("link", { name: /Open government spreadsheet/ });
    expect(link).toHaveAttribute("href", "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx");
    expect(screen.getByText(/The link opens the whole spreadsheet/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Copy sheet and cell locations" })).toBeVisible();
    fireEvent.click(link);
    expect(trackReaderEvent).toHaveBeenCalledWith("official_source_opened", { program: "F015EX", factId: "4a9ae7cc78dcf0ba", surface: "citation-panel" });
  });
});
