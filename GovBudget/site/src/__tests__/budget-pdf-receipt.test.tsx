import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BudgetPdfReceipt } from "@/components/citation-panel/budget-pdf-receipt";
import { fetchBudgetPdfReceipt, type BudgetPdfPart, type BudgetPdfReceipt as Receipt } from "@/lib/budget-pdf-receipts";
vi.mock("@/lib/budget-pdf-receipts", () => ({ fetchBudgetPdfReceipt: vi.fn() }));
vi.mock("@/components/citation-panel/pdf-view", () => ({ PdfView: ({citation}: {citation: BudgetPdfPart}) => <div data-testid="rendered-pdf">{citation.workbook_cell}:{citation.amount_text}</div> }));
const part: BudgetPdfPart = { amount_thousands: 120044, program: "F-15", line: "43", workbook_cell: "W874", column_label: "FY 2026 Total", edition: 2026, exhibit: "P-1", sha256: "a".repeat(64), hosted_pdf_url: "/pdfs/a.pdf", page_number: 124, page_width: 792, page_height: 612, x0: 700, x1: 730, top_pt: 210, bottom_pt: 220, resolution: "unique", amount_text: "120,044", units: "USD thousands", official_url: "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/FY2026_p1.pdf" };
const receipt: Receipt = {amount_thousands: 125156, matched_amount_thousands: 125156, complete: true, blank_zero_count: 0, unmatched_count: 0, parts: [part, {...part, line: "111", workbook_cell: "W922", amount_thousands: 5112, amount_text: "5,112", page_number: 130}]};
beforeEach(() => vi.mocked(fetchBudgetPdfReceipt).mockReset());
it("leads with exact PDF evidence and switches between contributing numbers", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(receipt);
  render(<BudgetPdfReceipt factId="1234567890abcdef"><p>Original spreadsheet evidence</p></BudgetPdfReceipt>);
  await screen.findByTestId("budget-pdf-receipt");
  expect(screen.getByTestId("pdf-workbook-match")).toHaveTextContent("Matches the published spreadsheet");
  expect(screen.getByText(/2 printed amounts sum to 125,156/)).toBeVisible();
  expect(screen.getByTestId("rendered-pdf")).toHaveTextContent("W874:120,044");
  fireEvent.click(screen.getByRole("button", {name: /Line 111/}));
  expect(screen.getByTestId("rendered-pdf")).toHaveTextContent("W922:5,112");
  expect(screen.getByRole("link", {name: /Open government PDF/})).toHaveAttribute("href", `${part.official_url}#page=130`);
  expect(screen.getByText("Original spreadsheet evidence").closest("details")).not.toHaveAttribute("open");
});
it("labels incomplete matching honestly and never claims a blank zero is printed", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue({...receipt, complete:false, unmatched_count:1, blank_zero_count:1});
  render(<BudgetPdfReceipt factId="1234567890abcdef">Spreadsheet</BudgetPdfReceipt>);
  expect(await screen.findByTestId("pdf-workbook-match")).toHaveTextContent("Partially matched");
  expect(screen.getByText(/zero with no printed number/)).toBeVisible();
  expect(screen.getByRole("status")).toHaveTextContent("do not have a verified PDF amount");
});
it("preserves original receipts when PDF evidence is unavailable", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(null);
  render(<BudgetPdfReceipt factId="1234567890abcdef"><p>Original spreadsheet evidence</p></BudgetPdfReceipt>);
  await waitFor(() => expect(fetchBudgetPdfReceipt).toHaveBeenCalled());
  expect(screen.getByText("Original spreadsheet evidence")).toBeVisible();
  expect(screen.queryByTestId("budget-pdf-receipt")).not.toBeInTheDocument();
});
it("does not show the previous fact's PDF while a new receipt resolves", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValueOnce(receipt).mockReturnValueOnce(new Promise(() => {}));
  const view=render(<BudgetPdfReceipt factId="1234567890abcdef">First</BudgetPdfReceipt>);
  await screen.findByTestId("budget-pdf-receipt");
  view.rerender(<BudgetPdfReceipt factId="abcdef1234567890">Second spreadsheet evidence</BudgetPdfReceipt>);
  expect(screen.queryByTestId("rendered-pdf")).not.toBeInTheDocument();
  expect(screen.getByText("Second spreadsheet evidence")).toBeVisible();
});
it("keeps zero receipts on the spreadsheet without inventing a printed PDF zero", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue({amount_thousands:0, matched_amount_thousands:0, complete:true, blank_zero_count:1, unmatched_count:0, parts:[]});
  render(<BudgetPdfReceipt factId="1234567890abcdef">Zero spreadsheet receipt</BudgetPdfReceipt>);
  expect(await screen.findByRole("status")).toHaveTextContent("no printed number to highlight");
  expect(screen.queryByTestId("rendered-pdf")).not.toBeInTheDocument();
  expect(screen.getByText("Zero spreadsheet receipt")).toBeVisible();
});
