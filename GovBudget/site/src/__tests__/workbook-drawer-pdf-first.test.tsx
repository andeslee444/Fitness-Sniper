/**
 * Integration 2026-09-25, gate 4 — the workbook drawer under the PDF-first
 * receipt.
 *
 * Two reviewed behaviours met in the merge:
 *  - the live branch (f15-family-browser): a workbook fact with a verified
 *    government PDF receipt opens on the PDF page; the original spreadsheet
 *    evidence folds into the collapsed "Spreadsheet downloads & calculation
 *    details" (budget-pdf-receipt.test.tsx pins that).
 *  - this branch (PM-S2 §P1-9): the workbook drawer shows the cited cells in
 *    their neighbourhood — a build-time cell preview with context rows.
 *
 * Merged, the preview sat inside the collapsed details: in the DOM, never on
 * screen, and gate 4 failed "no cell preview rendered" for 000042 (fact
 * 4dc6d6bda019d490) and ATA000 (fact 5b532c52d3ebb4c2). These tests hold
 * both behaviours at once, at the panel level where they meet: the PDF page
 * leads, the preview is VISIBLE under it, there is exactly one preview, and
 * no transient copy renders while the receipt is still resolving.
 *
 * Fixtures are the real rows for fact 5b532c52d3ebb4c2 (FY2026
 * p1_display.xlsx, sheet "Exhibit P-1", cells O839,O840,O841) and its v2 PDF
 * receipt (FY2026_p1.pdf page 122).
 */

import React, { useContext } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { CitationPanelProvider } from "@/components/citation-panel/panel";
import { CitationPanelContext } from "@/components/cite";
import { __resetWorkbookCellsCache, type WorkbookPreview } from "@/lib/workbook-cells";
import {
  fetchBudgetPdfReceipt,
  type BudgetPdfPart,
  type BudgetPdfReceipt,
} from "@/lib/budget-pdf-receipts";
import type { WorkbookCitation } from "@/lib/citations";

vi.mock("@/lib/budget-pdf-receipts", () => ({ fetchBudgetPdfReceipt: vi.fn() }));
vi.mock("@/components/citation-panel/pdf-view", () => ({
  PdfView: ({ citation }: { citation: BudgetPdfPart }) => (
    <div data-testid="rendered-pdf">
      {citation.workbook_cell}:{citation.amount_text}
    </div>
  ),
}));
vi.mock("@/components/asset-config", async (original) => ({
  ...(await original<typeof import("@/components/asset-config")>()),
  AssetConfigProvider: ({ children }: { children: React.ReactNode }) => children,
  useAssetUrl: () => (path: string) => path,
}));

// ── Fixtures ─────────────────────────────────────────────────────────────────

const FID = "5b532c52d3ebb4c2";
const SINGLE_FID = "4dc6d6bda019d490";
const WORKBOOK_URL =
  "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx";
const WORKBOOK_SHA = "4d965906ad91aa8b7d6d5f891a0717ac25ace6c18f3d50df07ebde611774a9c0";

const F35: WorkbookCitation = {
  kind: "workbook",
  amount_text: null,
  amount_thousands: 5565655,
  bottom_pt: null,
  cells: "O839,O840,O841",
  formula: null,
  hosted_pdf_url: null,
  inputs: null,
  official_url: WORKBOOK_URL,
  page_height: null,
  page_number: null,
  page_width: null,
  query_body: null,
  recorded_value: null,
  resolution: null,
  retrieved_at: "2026-06-10T16:08:15.686145-04:00",
  sha256: WORKBOOK_SHA,
  sheet: "Exhibit P-1",
  top_pt: null,
  units: "USD thousands",
  x0: null,
  x1: null,
  xml_path: null,
};

const SINGLE: WorkbookCitation = { ...F35, amount_thousands: 793, cells: "O973" };

const F35_PREVIEW: WorkbookPreview = {
  sheet: "Exhibit P-1",
  col: "O",
  col_header: "FY 2024 Actuals Amount",
  units: "USD thousands",
  total: 5565655,
  rows: [
    { r: 837, code: "B02100", title: "B-21 Raider", note: "C (FY 2025 for FY 2026) (M)", flag: "Non-Add" },
    { r: 838, code: "B02100", title: "B-21 Raider", note: "C (FY 2026 for FY 2027) (M)", flag: "Non-Add" },
    { r: 839, code: "ATA000", title: "F-35", note: "Weapon System Cost", flag: "Add", v: 5493772, cited: true },
    { r: 840, code: "ATA000", title: "F-35", note: "Less: Advance Procurement (PY)", flag: "Add", v: -246702, cited: true },
    { r: 841, code: "ATA000", title: "F-35", note: "Advance Procurement (CY)", flag: "Add", v: 318585, cited: true },
    { r: 842, code: "ATA000", title: "F-35", note: "C (FY 2024 for FY 2025) (M)", flag: "Non-Add", v: 318585 },
    { r: 843, code: "ATA000", title: "F-35", note: "C (FY 2025 for FY 2026) (M)", flag: "Non-Add" },
  ],
};

const SINGLE_PREVIEW: WorkbookPreview = {
  sheet: "Exhibit P-1",
  col: "O",
  col_header: "FY 2024 Actuals Amount",
  units: "USD thousands",
  total: 793,
  rows: [
    { r: 971, code: "SDB002", title: "SMALL DIAMETER BOMB II", note: "Weapon System Cost", flag: "Add", v: 291553 },
    { r: 972, code: "SIAW24", title: "Stand-In Attack Weapon (SIAW)", note: "Weapon System Cost", flag: "Add", v: 41947 },
    { r: 973, code: "000042", title: "Industrial Preparedness/Pol Prevention", note: "Weapon System Cost", flag: "Add", v: 793, cited: true },
    { r: 974, code: "000999", title: "Initial Spares/Repair Parts", note: "Weapon System Cost", flag: "Add", v: 1200 },
  ],
};

function part(cell: string, amount: number, text: string): BudgetPdfPart {
  return {
    amount_thousands: amount,
    amount_text: text,
    program: "F-35",
    line: "22",
    row_label: "Weapon System Cost",
    workbook_cell: cell,
    workbook_sha256: WORKBOOK_SHA,
    workbook_sheet: "Exhibit P-1",
    workbook_url: WORKBOOK_URL,
    column_label: "FY 2024 Actuals Amount",
    pdf_column_label: "FY 2024 Actuals",
    edition: 2026,
    exhibit: "P-1",
    sha256: "fce4c9296280bdb355d05199b49a1d009afc6b615409ba4dba19f358a0da835f",
    hosted_pdf_url: "/pdfs/fce4c929.pdf",
    page_number: 122,
    page_width: 792,
    page_height: 612,
    x0: 360,
    x1: 380,
    top_pt: 450,
    bottom_pt: 460,
    resolution: "unique",
    units: "USD thousands",
    official_url:
      "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/FY2026_p1.pdf",
  };
}

const F35_RECEIPT: BudgetPdfReceipt = {
  amount_thousands: 5565655,
  matched_amount_thousands: 5565655,
  complete: true,
  blank_zero_count: 0,
  unmatched_count: 0,
  parts: [
    part("O839", 5493772, "5,493,772"),
    part("O840", -246702, "-246,702"),
    part("O841", 318585, "318,585"),
  ],
};

const SINGLE_RECEIPT: BudgetPdfReceipt = {
  amount_thousands: 793,
  matched_amount_thousands: 793,
  complete: true,
  blank_zero_count: 0,
  unmatched_count: 0,
  parts: [{ ...part("O973", 793, "793"), program: "Industrial Preparedness/Pol Prevention", line: "24", page_number: 138 }],
};

// ── Harness ──────────────────────────────────────────────────────────────────

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: () => Promise.resolve(body) };
}

beforeEach(() => {
  __resetWorkbookCellsCache();
  vi.mocked(fetchBudgetPdfReceipt).mockReset();
  // Only the workbook-cells shards are served; the PDF receipt comes from the
  // mocked fetchBudgetPdfReceipt, so each test orders the two lookups itself.
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const u = String(url);
      if (u === "/json/workbook-cells/5b.json" || u === "/json/workbook-cells/4d.json") {
        return jsonResponse({ [FID]: F35_PREVIEW, [SINGLE_FID]: SINGLE_PREVIEW });
      }
      return { ok: false, status: 404, json: () => Promise.resolve({}) };
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function Trigger({ factId }: { factId: string }) {
  const { openPanel } = useContext(CitationPanelContext);
  return <button onClick={() => openPanel(factId)}>Open receipt</button>;
}

async function openDrawer(factId: string, citation: WorkbookCitation) {
  render(
    <CitationPanelProvider citations={{ [factId]: citation } as never}>
      <Trigger factId={factId} />
    </CitationPanelProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Open receipt" }));
  return await screen.findByTestId("citation-panel");
}

function follows(a: Element, b: Element): boolean {
  return Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("workbook drawer × PDF-first receipt (integration 2026-09-25, gate 4)", () => {
  it("multi-cell fact: opens on the PDF page AND shows its cell preview in the open under it", async () => {
    vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(F35_RECEIPT);
    const panel = await openDrawer(FID, F35);

    const receipt = await within(panel).findByTestId("budget-pdf-receipt");
    const preview = await within(panel).findByTestId("workbook-preview");

    // The PDF page leads (the live branch's standard)…
    const pdf = within(receipt).getByTestId("rendered-pdf");
    expect(pdf).toHaveTextContent("O839:5,493,772");
    expect(follows(pdf, preview)).toBe(true);

    // …and the §P1-9 preview is on screen, not folded into the details.
    expect(preview).toBeVisible();
    expect(preview.closest("details")).toBeNull();
    expect(receipt.contains(preview)).toBe(true);
    expect(panel.querySelectorAll('[data-testid="workbook-preview"]')).toHaveLength(1);

    const cited = [...preview.querySelectorAll('[data-testid="workbook-preview-row"][data-cited="true"]')]
      .map((row) => row.getAttribute("data-row"));
    expect(cited).toEqual(["839", "840", "841"]);
    expect(preview.querySelectorAll('[data-testid="workbook-preview-row"]').length).toBeGreaterThan(cited.length);

    // The rest of the spreadsheet evidence still folds (live-branch behaviour
    // kept): amount, document, locator, arithmetic, download.
    const amount = within(panel).getByTestId("workbook-amount");
    expect(amount.closest("details")).not.toHaveAttribute("open");
    await waitFor(() => expect(within(panel).getByTestId("workbook-arithmetic")).toBeInTheDocument());
    expect(within(panel).getByTestId("workbook-arithmetic").closest("details")).not.toHaveAttribute("open");
    expect(within(panel).queryByTestId("workbook-preview-unavailable")).toBeNull();
  });

  it("single-cell fact: the preview is on screen with its context rows, and no arithmetic line", async () => {
    vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(SINGLE_RECEIPT);
    const panel = await openDrawer(SINGLE_FID, SINGLE);

    await within(panel).findByTestId("budget-pdf-receipt");
    const preview = await within(panel).findByTestId("workbook-preview");
    expect(preview).toBeVisible();
    expect(panel.querySelectorAll('[data-testid="workbook-preview"]')).toHaveLength(1);
    const rows = preview.querySelectorAll('[data-testid="workbook-preview-row"]');
    expect([...rows].filter((r) => r.getAttribute("data-cited") === "true").map((r) => r.getAttribute("data-row"))).toEqual(["973"]);
    expect(rows.length).toBeGreaterThan(1);
    expect(within(panel).queryByTestId("workbook-arithmetic")).toBeNull();
  });

  it("never renders a transient preview while the receipt resolves, even when the preview shard lands first", async () => {
    let settle: (r: BudgetPdfReceipt | null) => void = () => {};
    vi.mocked(fetchBudgetPdfReceipt).mockReturnValue(
      new Promise((done) => {
        settle = done;
      }),
    );
    const panel = await openDrawer(FID, F35);

    // The preview shard resolves; the receipt has not.
    await waitFor(() => expect(fetch).toHaveBeenCalledWith("/json/workbook-cells/5b.json"));
    await act(async () => {
      await new Promise((done) => setTimeout(done, 0));
    });
    // The spreadsheet evidence is in the open while resolving (live
    // behaviour) — but no preview that the receipt would then fold away.
    expect(within(panel).getByTestId("workbook-amount")).toBeVisible();
    expect(within(panel).queryByTestId("workbook-preview")).toBeNull();

    await act(async () => settle(F35_RECEIPT));
    const preview = await within(panel).findByTestId("workbook-preview");
    expect(preview).toBeVisible();
    expect(panel.querySelectorAll('[data-testid="workbook-preview"]')).toHaveLength(1);
  });

  it("no PDF receipt: the card shows its own preview in the open, exactly as before the merge", async () => {
    vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(null);
    const panel = await openDrawer(FID, F35);

    const preview = await within(panel).findByTestId("workbook-preview");
    expect(preview).toBeVisible();
    expect(within(panel).queryByTestId("budget-pdf-receipt")).toBeNull();
    expect(within(panel).queryByTestId("receipt-beside")).toBeNull();
    expect(panel.querySelectorAll('[data-testid="workbook-preview"]')).toHaveLength(1);
    // Card order kept: amount → … → preview.
    expect(follows(within(panel).getByTestId("workbook-amount"), preview)).toBe(true);
  });

  it("no verified printed amount: the spreadsheet evidence stays in the open with its own preview", async () => {
    vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue({
      ...F35_RECEIPT,
      complete: false,
      unmatched_count: 3,
      parts: [],
    });
    const panel = await openDrawer(FID, F35);

    await within(panel).findByText(/exact printed amount has not been verified/);
    const preview = await within(panel).findByTestId("workbook-preview");
    expect(preview).toBeVisible();
    expect(within(panel).queryByTestId("receipt-beside")).toBeNull();
    expect(panel.querySelectorAll('[data-testid="workbook-preview"]')).toHaveLength(1);
  });

  it("an unreachable preview shard is said plainly under the PDF page, never a blank", async () => {
    vi.mocked(fetchBudgetPdfReceipt).mockResolvedValue(F35_RECEIPT);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 404, json: () => Promise.resolve({}) })),
    );
    const panel = await openDrawer(FID, F35);

    const note = await within(panel).findByTestId("workbook-preview-unavailable");
    expect(note).toBeVisible();
    expect(within(panel).getByTestId("receipt-beside").contains(note)).toBe(true);
    expect(panel.querySelectorAll('[data-testid="workbook-preview-unavailable"]')).toHaveLength(1);
    expect(within(panel).queryByTestId("workbook-preview")).toBeNull();
  });
});
