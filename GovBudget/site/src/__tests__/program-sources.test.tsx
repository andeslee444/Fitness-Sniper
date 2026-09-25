import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { Citation, JbookPdfCitation, WorkbookCitation } from "@/lib/data";
import { fetchBudgetPdfReceipt, type BudgetPdfReceipt } from "@/lib/budget-pdf-receipts";
import { budgetPdfSourceDocuments, programSourceEntries } from "@/lib/source-document";
import { ProgramSources } from "@/components/program-sources";
import { SourceDocumentLinks } from "@/components/source-document-links";
import { CitationPanelContext } from "@/components/cite";

vi.mock("@/lib/budget-pdf-receipts", () => ({ fetchBudgetPdfReceipt: vi.fn() }));
vi.mock("@/lib/reader-events", () => ({ trackReaderEvent: vi.fn() }));
const fid = "a123456789abcdef";
const pdfUrl = "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/FY2026_r1.pdf";
const workbook = {
  kind: "workbook", official_url: "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/r1_display.xlsx",
  sha256: "b".repeat(64), sheet: "Exhibit R-1", cells: "W123", amount_thousands: 50000, page_number: null,
} as WorkbookCitation;
const detail = {
  kind: "jbook_pdf", official_url: "https://example.mil/detailed-justification.pdf", hosted_pdf_url: "/pdfs/detail.pdf",
  sha256: "c".repeat(64), page_number: 12, resolution: "unique", amount_text: "48.200", units: "USD millions",
  x0: 100, x1: 130, top_pt: 100, bottom_pt: 110, page_width: 792, page_height: 612,
} as JbookPdfCitation;
const receipt: BudgetPdfReceipt = {
  amount_thousands: 50000, matched_amount_thousands: 50000, complete: true, blank_zero_count: 0, unmatched_count: 0,
  parts: [{ official_url: pdfUrl, sha256: "a".repeat(64), hosted_pdf_url: "/pdfs/match.pdf", page_number: 15,
    page_width: 792, page_height: 612, x0: 100, x1: 130, top_pt: 100, bottom_pt: 110,
    units: "USD thousands", amount_text: "50,000", resolution: "unique", amount_thousands: 50000,
    program: "B-21", line: "55", workbook_cell: "W123", column_label: "FY2026 Request", edition: 2026, exhibit: "R-1" }],
};
beforeEach(() => { vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(null); });
afterEach(() => { cleanup(); vi.clearAllMocks(); vi.unstubAllGlobals(); });

describe("sitewide source standard", () => {
  it("leads a non-F15 workbook receipt with highlighted PDF access and keeps download visible", async () => {
    vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(receipt);
    const openPanel = vi.fn();
    const view = render(<CitationPanelContext.Provider value={{ openPanel }}><SourceDocumentLinks citation={workbook} factId={fid} /></CitationPanelContext.Provider>);
    const highlighted = await screen.findByRole("button", { name: "View highlighted line item" });
    fireEvent.click(highlighted);
    expect(openPanel).toHaveBeenCalledWith(fid);
    const pdf = screen.getByRole("link", { name: /Open government PDF/ });
    expect(pdf).toHaveAttribute("href", `${pdfUrl}#page=15`);
    const download = screen.getByRole("button", { name: "Download government spreadsheet" });
    expect(download).toBeVisible();
    expect(download).toHaveAttribute("data-filename", "PB2026_DoD_R-1_Research-Development-Test-Evaluation.xlsx");
    expect(view.container.querySelectorAll('[data-testid="official-source"]')[0]).toBe(pdf);
  });

  it("does not keep a previous fact's PDF while a different fact resolves", async () => {
    vi.mocked(fetchBudgetPdfReceipt).mockResolvedValueOnce(receipt).mockReturnValueOnce(new Promise(() => {}));
    const view = render(<SourceDocumentLinks citation={workbook} factId={fid} />);
    await screen.findByRole("link", { name: /Open government PDF/ });
    view.rerender(<SourceDocumentLinks citation={workbook} factId="d123456789abcdef" />);
    expect(screen.queryByRole("link", { name: /Open government PDF/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download government spreadsheet" })).toBeVisible();
  });

  it("offers a matching PDF without claiming an unverified highlight", async () => {
    vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue({ ...receipt, parts: [], complete: false, unmatched_count: 1,
      source_documents: [{ official_url: pdfUrl, sha256: "a".repeat(64), edition: 2026, exhibit: "R-1" }] });
    render(<SourceDocumentLinks citation={workbook} factId={fid} />);
    expect(await screen.findByRole("link", { name: /Open government PDF/ })).toHaveAttribute("href", pdfUrl);
    expect(screen.getByText(/exact printed amount has not been verified/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "View highlighted line item" })).not.toBeInTheDocument();
  });

  it("keeps workbook and detail sources together without asserting their amounts match", async () => {
    const entries = programSourceEntries({ [fid]: workbook, d123456789abcdef: detail });
    render(<ProgramSources entries={entries} program="0604015F" />);
    expect(screen.getByRole("button", { name: "Download government spreadsheet" })).toBeVisible();
    expect(screen.getByRole("link", { name: /Open government PDF · page 12/ })).toHaveAttribute("href", `${detail.official_url}#page=12`);
    expect(screen.getByText(/different accounting basis/)).toBeVisible();
    await waitFor(() => expect(fetchBudgetPdfReceipt).toHaveBeenCalledWith(fid));
    expect(fetchBudgetPdfReceipt).toHaveBeenCalledTimes(1);
    expect(within(screen.getByTestId("program-detail-sources")).queryByRole("button", { name: /Download/ })).not.toBeInTheDocument();
  });

  it("deduplicates original documents and prefers a located numeric receipt", () => {
    const unresolved = { ...detail, resolution: "unresolved", page_number: null } as Citation;
    const entries = programSourceEntries({ first: unresolved, second: detail, anotherYear: { ...workbook, cells: "T123" }, [fid]: workbook });
    expect(entries).toHaveLength(2);
    expect(entries[0].factId).toBe("second");
  });

  it("describes reserve component locations without claiming a printed line identifier", () => {
    const documents = budgetPdfSourceDocuments({ ...receipt, parts: [{ ...receipt.parts[0], line: "", row_label: "National Guard", exhibit: "P-1R" }] });
    expect(documents[0].locators[0]).toContain("National Guard");
    expect(documents[0].locators[0]).not.toContain("Line");
  });

  it("waits until primary sources approach the viewport before fetching PDF metadata", async () => {
    let onIntersection: IntersectionObserverCallback = () => {};
    const disconnect = vi.fn();
    vi.stubGlobal("IntersectionObserver", class {
      constructor(callback: IntersectionObserverCallback) { onIntersection = callback; }
      observe = vi.fn(); disconnect = disconnect;
    });
    render(<ProgramSources entries={[{ factId: fid, citation: workbook }]} />);
    expect(fetchBudgetPdfReceipt).not.toHaveBeenCalled();
    await act(async () => onIntersection([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver));
    expect(fetchBudgetPdfReceipt).toHaveBeenCalledWith(fid);
    expect(disconnect).toHaveBeenCalled();
  });
});
