import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { citationSourceDocuments, citationSourceSlice, officialDocumentUrl, resolveSourceCitationInputs, SOURCE_INPUT_LIMIT, workbookDownloadName } from "@/lib/source-document";
import { F15ProgramSources } from "@/components/family-entry";
import { SourceDocumentLinks } from "@/components/source-document-links";
import { getF15FamilyData } from "@/lib/f15-family-data";
import { getRecordFact } from "@/lib/f15-family";
import { trackReaderEvent } from "@/lib/reader-events";
import { resolveCitationFromShards } from "@/lib/cite-shards";
import { getF15FundingHistorySource } from "@/lib/family-funding-history-data";
import { getCitations } from "@/lib/data";

vi.mock("@/lib/reader-events", () => ({ trackReaderEvent: vi.fn() }));
vi.mock("@/lib/cite-shards", () => ({ resolveCitationFromShards: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const family = getF15FamilyData();

describe("exact source document actions", () => {
  it("names complete workbooks by their own budget edition and exhibit", () => {
    const sha = "4d965906ad91aa8b7d6d5f891a0717ac25ace6c18f3d50df07ebde611774a9c0";
    expect(workbookDownloadName("https://comptroller.war.gov/Portals/45/Documents/defbudget/fy2017/p1_display.xlsx", sha)).toBe("PB2017_DoD_P-1_Procurement.xlsx");
    expect(workbookDownloadName("https://comptroller.defense.gov/Portals/45/Documents/defbudget/FY2026/r1_display.xlsx", sha)).toBe("PB2026_DoD_R-1_Research-Development-Test-Evaluation.xlsx");
    expect(workbookDownloadName("https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1r_display.xlsx", sha)).toBe("PB2026_DoD_P-1R_Procurement.xlsx");
    expect(workbookDownloadName("https://example.com/fy2026/p1_display.xlsx", sha)).toBe("p1_display_4d965906.xlsx");
    expect(workbookDownloadName(null, sha)).toBe("Budget-spreadsheet_4d965906.xlsx");
    const history = getF15FundingHistorySource();
    const citations = getCitations();
    const docs = citationSourceDocuments(citations[history.cumulative.fact_id], citations);
    expect(new Set(docs.map(doc => doc.workbook?.filename)).size).toBe(20);
  });
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
      expect(documents[0].label).toBe("Download government spreadsheet");
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
    expect(citationSourceDocuments(source)[0].label).toBe("Download source spreadsheet");
    const root = family.citations["4a9ae7cc78dcf0ba"];
    if (root.kind !== "derived") throw new Error("Expected derived F-15EX total");
    const cycle = { ...root, inputs: '["4a9ae7cc78dcf0ba"]' };
    expect(citationSourceDocuments(cycle, { "4a9ae7cc78dcf0ba": cycle })).toEqual([]);
  });

  it("resolves missing inputs for a standalone total and retains honest failure state", async () => {
    vi.mocked(resolveCitationFromShards).mockImplementation(async id => family.citations[id] ?? null);
    const view = render(<SourceDocumentLinks citation={family.citations["4a9ae7cc78dcf0ba"]} resolveInputs />);
    expect(await screen.findByRole("button", { name: /Download government spreadsheet/ })).toHaveAttribute("data-filename", "PB2026_DoD_P-1_Procurement.xlsx");
    view.unmount();
    vi.mocked(resolveCitationFromShards).mockResolvedValue(null);
    render(<SourceDocumentLinks citation={family.citations["4a9ae7cc78dcf0ba"]} resolveInputs />);
    expect(await screen.findByText(/Some source locations could not be loaded/)).toBeVisible();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("makes derived input documents prominent and measures the official action once", () => {
    render(<SourceDocumentLinks citation={family.citations["4a9ae7cc78dcf0ba"]} citations={family.citations} factId="4a9ae7cc78dcf0ba" program="F015EX" surface="citation-panel" />);
    const link = screen.getByRole("link", { name: /Government original/ });
    expect(link).toHaveAttribute("href", "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx");
    expect(screen.getByText(/Complete workbook · unchanged saved copy/)).toBeVisible();
    expect(screen.getByRole("button", { name: /Download government spreadsheet/ })).toHaveAttribute("data-filename", "PB2026_DoD_P-1_Procurement.xlsx");
    expect(screen.getByRole("button", { name: "Copy sheet and cell locations" })).toBeVisible();
    fireEvent.click(link);
    expect(trackReaderEvent).toHaveBeenCalledWith("official_source_opened", { program: "F015EX", factId: "4a9ae7cc78dcf0ba", surface: "citation-panel" });
  });

  it("resolves the complete multi-year receipt without a false missing-source warning", async () => {
    const history = getF15FundingHistorySource();
    const citations = getCitations();
    const total = citations[history.cumulative.fact_id];
    const fetchCitation = vi.fn().mockResolvedValue(null);
    const closure = await resolveSourceCitationInputs(total, id => citations[id], fetchCitation);
    expect(Object.keys(closure.values).length).toBeGreaterThan(32);
    expect(closure.incomplete).toBe(false);
    expect(fetchCitation).not.toHaveBeenCalled();
    vi.mocked(resolveCitationFromShards).mockClear();
    let view!: ReturnType<typeof render>;
    await act(async () => { view = render(<SourceDocumentLinks citation={total} citations={citations} resolveInputs />); });
    const summary = screen.getByText("View 20 government spreadsheets");
    expect(summary.closest("details")).not.toHaveAttribute("open");
    for (const link of screen.getAllByRole("button", { name: /Download government spreadsheet/ })) expect(link).not.toBeVisible();
    fireEvent.click(summary);
    await waitFor(() => expect(summary.closest("details")).toHaveAttribute("open"));
    expect(screen.getAllByRole("button", { name: /Download government spreadsheet/ })).toHaveLength(20);
    expect(view.container.querySelectorAll('[data-testid="official-source"]')).toHaveLength(20);
    expect(screen.queryByText(/Some source locations could not be loaded/)).toBeNull();
    expect(resolveCitationFromShards).not.toHaveBeenCalled();
  });

  it("loads the same cumulative chain from standalone shards without truncating at 32", async () => {
    const history = getF15FundingHistorySource();
    const citations = getCitations();
    const fetchCitation = vi.fn(async (id: string) => citations[id] ?? null);
    const closure = await resolveSourceCitationInputs(citations[history.cumulative.fact_id], () => undefined, fetchCitation);
    expect(closure.incomplete).toBe(false);
    expect(fetchCitation.mock.calls.length).toBeGreaterThan(32);
    expect(new Set(fetchCitation.mock.calls.map(([id]) => id)).size).toBe(fetchCitation.mock.calls.length);
    expect(citationSourceDocuments(citations[history.cumulative.fact_id], closure.values)).toHaveLength(20);
  });

  it("still bounds oversized graphs and reports genuine missing sources", async () => {
    const root = family.citations["4a9ae7cc78dcf0ba"];
    if (root.kind !== "derived") throw new Error("Expected derived fixture");
    const ids = Array.from({ length: SOURCE_INPUT_LIMIT + 1 }, (_, n) => n.toString(16).padStart(16, "0"));
    const fetchCitation = vi.fn(async () => family.citations["44f9ccc1f1518032"]);
    const limited = await resolveSourceCitationInputs({ ...root, inputs: JSON.stringify(ids) }, () => undefined, fetchCitation);
    expect(limited.incomplete).toBe(true);
    expect(Object.keys(limited.values)).toHaveLength(SOURCE_INPUT_LIMIT);
    expect(fetchCitation).toHaveBeenCalledTimes(SOURCE_INPUT_LIMIT);
    const missing = await resolveSourceCitationInputs(root, () => undefined, async () => null);
    expect(missing.incomplete).toBe(true);
    expect(missing.values).toEqual({});
    const cycle = { ...root, inputs: '["4a9ae7cc78dcf0ba"]' };
    const cyclic = await resolveSourceCitationInputs(cycle, () => cycle, fetchCitation);
    expect(cyclic.incomplete).toBe(false);
    expect(Object.keys(cyclic.values)).toEqual(["4a9ae7cc78dcf0ba"]);
  });
});
