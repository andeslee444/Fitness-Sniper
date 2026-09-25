import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { FactResolver } from "@/app/fact/fact-resolver";
import { __resetCiteShardCache } from "@/lib/cite-shards";
import type { WorkbookCitation } from "@/lib/data";
import { fetchBudgetPdfReceipt, type BudgetPdfReceipt } from "@/lib/budget-pdf-receipts";

vi.mock("@/lib/budget-pdf-receipts", () => ({ fetchBudgetPdfReceipt: vi.fn() }));
vi.mock("@/components/citation-panel/pdf-view", () => ({ PdfView: () => <div data-testid="highlighted-pdf-view">Verified PDF highlight</div> }));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.clearAllMocks(); __resetCiteShardCache(); window.history.replaceState({}, "", "/"); });

describe("standalone budget receipt", () => {
  it("prioritizes the matching PDF and opens the shared highlighted drawer from the permalink", async () => {
    const fid = "a123456789abcdef";
    const officialUrl = "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/r1_display.xlsx";
    const pdfUrl = "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/FY2026_r1.pdf";
    const citation: WorkbookCitation = { kind: "workbook", official_url: officialUrl, sha256: "b".repeat(64),
      amount_thousands: 50000, sheet: "Exhibit R-1", cells: "W123", units: "USD thousands", retrieved_at: "2026-09-24T12:00:00Z",
      amount_text: null, formula: null, inputs: null, query_body: null, recorded_value: null, bottom_pt: null, hosted_pdf_url: null,
      page_height: null, page_number: null, page_width: null, resolution: null, top_pt: null, x0: null, x1: null, xml_path: null };
    const receipt: BudgetPdfReceipt = { amount_thousands: 50000, matched_amount_thousands: 50000, complete: true, blank_zero_count: 0, unmatched_count: 0,
      parts: [{ official_url: pdfUrl, sha256: "a".repeat(64), hosted_pdf_url: "/pdfs/match.pdf", page_number: 15,
        page_width: 792, page_height: 612, x0: 100, x1: 130, top_pt: 100, bottom_pt: 110,
        units: "USD thousands", amount_text: "50,000", resolution: "unique", amount_thousands: 50000,
        program: "B-21", line: "55", workbook_cell: "W123", workbook_sha256: citation.sha256, workbook_url: officialUrl,
        column_label: "FY2026 Request", edition: 2026, exhibit: "R-1" }] };
    vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(receipt);
    vi.stubGlobal("fetch", vi.fn(async (url: string) => ({ ok: true, json: async () => url === "/config.json" ? { assetBaseUrl: "/assets" }
      : url.includes("/cite-shards/") ? { [fid]: citation } : {} })));
    window.history.replaceState({}, "", `/fact/?id=${fid}`);
    render(<FactResolver />);
    const action = await screen.findByRole("button", { name: "View highlighted line item" });
    expect(screen.queryByRole("button", { name: "View source excerpt" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open government PDF/ })).toHaveAttribute("href", `${pdfUrl}#page=15`);
    expect(screen.getByRole("button", { name: "Download government spreadsheet" })).toHaveAttribute("data-filename", "PB2026_DoD_R-1_Research-Development-Test-Evaluation.xlsx");
    fireEvent.click(action);
    const panelReceipt = await screen.findByTestId("budget-pdf-receipt");
    expect(within(panelReceipt).getByTestId("highlighted-pdf-view")).toBeVisible();
    const visibleDownload = within(panelReceipt).getAllByRole("button", { name: "Download government spreadsheet" }).find(button => !button.closest("details"));
    expect(visibleDownload).toBeVisible();
  });
});
