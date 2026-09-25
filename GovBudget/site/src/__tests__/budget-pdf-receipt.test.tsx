import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BudgetPdfReceipt, BesideEvidenceContext } from "@/components/citation-panel/budget-pdf-receipt";
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
it("keeps the corresponding named workbook download visible beside the PDF", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue({ ...receipt, parts: [{ ...part, workbook_sha256: "b".repeat(64), workbook_url: "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx" }] });
  render(<BudgetPdfReceipt factId="1234567890abcdef">Calculation details</BudgetPdfReceipt>);
  const download = await screen.findByRole("button", { name: "Download government spreadsheet" });
  expect(download).toBeVisible();
  expect(download.closest("details")).toBeNull();
  expect(download).toHaveAttribute("data-filename", "PB2026_DoD_P-1_Procurement.xlsx");
});
it("links the matching budget book even when no exact printed amount was verified", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue({ ...receipt, complete: false, unmatched_count: 1, parts: [], source_documents: [{ official_url: part.official_url!, sha256: part.sha256, edition: 2026, exhibit: "P-1" }] });
  render(<BudgetPdfReceipt factId="1234567890abcdef">Spreadsheet receipt</BudgetPdfReceipt>);
  expect(await screen.findByRole("link", { name: /Open government PDF/ })).toHaveAttribute("href", part.official_url);
  expect(screen.getByRole("status")).toHaveTextContent("exact printed amount has not been verified");
  expect(screen.queryByTestId("rendered-pdf")).not.toBeInTheDocument();
});
it("links a continued row to its source heading and labels reserve components without an invented line number", async () => {
  const reserve = { ...part, program: "Reserve Aircraft", exhibit: "P-1R", line: "", row_label: "Reserve", identity_page_number: 123 };
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue({ ...receipt, parts: [reserve, { ...reserve, row_label: "National Guard", workbook_cell: "W125", identity_page_number: 124 }] });
  render(<BudgetPdfReceipt factId="1234567890abcdef">Spreadsheet evidence</BudgetPdfReceipt>);
  const heading = await screen.findByRole("link", { name: /Program heading · government PDF page 123/ });
  expect(heading).toHaveAttribute("href", `${part.official_url}#page=123`);
  expect(screen.getByRole("link", { name: /Open government PDF · page 124/ })).toHaveAttribute("href", `${part.official_url}#page=124`);
  const choices = screen.getByRole("group", { name: "Contributing PDF amounts" });
  expect(choices).not.toHaveTextContent("Line");
  fireEvent.click(screen.getByRole("button", { name: /National Guard/ }));
  expect(screen.queryByRole("link", { name: /Program heading/ })).not.toBeInTheDocument();
});

// Integration 2026-09-25 (gate 4): `beside` evidence — the panel hands a
// workbook fact's §P1-9 cell preview here so it stays on screen under the PDF
// page while the rest of the spreadsheet evidence folds into the details.
function Placement() { return <span data-testid="placement">{React.useContext(BesideEvidenceContext)}</span>; }
it("keeps `beside` evidence in the open under the PDF page while the children fold into the details", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(receipt);
  render(<BudgetPdfReceipt factId="1234567890abcdef" beside={<p>Cell preview</p>}><p>Original spreadsheet evidence</p><Placement /></BudgetPdfReceipt>);
  await screen.findByTestId("budget-pdf-receipt");
  const beside = screen.getByText("Cell preview");
  expect(beside).toBeVisible();
  expect(beside.closest("details")).toBeNull();
  expect(screen.getByTestId("rendered-pdf").compareDocumentPosition(beside) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByText("Original spreadsheet evidence").closest("details")).not.toHaveAttribute("open");
  expect(screen.getByTestId("placement")).toHaveTextContent("beside");
});
it("places nothing beside while the receipt resolves, and leaves the children their own copy when none exists", async () => {
  let settle: (r: Receipt | null) => void = () => {};
  vi.mocked(fetchBudgetPdfReceipt).mockReturnValue(new Promise(done => { settle = done; }));
  render(<BudgetPdfReceipt factId="1234567890abcdef" beside={<p>Cell preview</p>}><p>Spreadsheet evidence</p><Placement /></BudgetPdfReceipt>);
  expect(screen.getByTestId("placement")).toHaveTextContent("pending");
  expect(screen.getByText("Spreadsheet evidence")).toBeVisible();
  expect(screen.queryByText("Cell preview")).not.toBeInTheDocument();
  await act(async () => settle(null));
  expect(screen.getByTestId("placement")).toHaveTextContent("inline");
  expect(screen.queryByText("Cell preview")).not.toBeInTheDocument();
});
it("leaves the children their own copy when no exact printed amount was verified", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue({ ...receipt, complete: false, unmatched_count: 1, parts: [] });
  render(<BudgetPdfReceipt factId="1234567890abcdef" beside={<p>Cell preview</p>}><Placement /></BudgetPdfReceipt>);
  expect(await screen.findByRole("status")).toHaveTextContent("exact printed amount has not been verified");
  expect(screen.getByTestId("placement")).toHaveTextContent("inline");
  expect(screen.queryByTestId("receipt-beside")).not.toBeInTheDocument();
});
it("settles a failed lookup as no receipt instead of waiting forever", async () => {
  // ...Once: this file's beforeEach returns the mock, which vitest also calls as an afterEach teardown.
  vi.mocked(fetchBudgetPdfReceipt).mockRejectedValueOnce(new Error("offline"));
  render(<BudgetPdfReceipt factId="1234567890abcdef" beside={<p>Cell preview</p>}><p>Spreadsheet evidence</p><Placement /></BudgetPdfReceipt>);
  await waitFor(() => expect(screen.getByTestId("placement")).toHaveTextContent("inline"));
  expect(screen.getByText("Spreadsheet evidence")).toBeVisible();
});
it("without `beside`, the children keep their own copy in every state", async () => {
  vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(receipt);
  render(<BudgetPdfReceipt factId="1234567890abcdef"><Placement /></BudgetPdfReceipt>);
  expect(screen.getByTestId("placement")).toHaveTextContent("inline");
  await screen.findByTestId("budget-pdf-receipt");
  expect(screen.getByTestId("placement")).toHaveTextContent("inline");
  expect(screen.queryByTestId("receipt-beside")).not.toBeInTheDocument();
});
