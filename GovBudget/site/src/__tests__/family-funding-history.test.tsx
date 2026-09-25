import React from "react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within, waitFor } from "@testing-library/react";
import { FamilyFundingHistory } from "@/components/family-funding-history";
import { CitationPanelProvider } from "@/components/citation-panel/panel";
import { CitationPanelContext } from "@/components/cite";
import { getF15FundingHistory, getF15FundingHistorySource } from "@/lib/family-funding-history-data";
import { FAMILY_HISTORY_URL, familyHistoryInputRows, familyHistorySeries, validateFamilyHistoryMatrix } from "@/lib/family-funding-history";
import { getCitations } from "@/lib/data";
import F15FamilyPage from "@/app/families/f-15/page";

vi.mock("@/components/f15-model", () => ({ F15Model: () => <div /> }));
vi.mock("@/components/citation-panel/pdf-view", () => ({ PdfView: () => <div data-testid="pdf-preview" /> }));
const source = getF15FundingHistorySource();
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  vi.stubGlobal("fetch", vi.fn(async (url: RequestInfo | URL) => {
    if (String(url).startsWith("/json/")) return { ok: true, json: async () => JSON.parse(readFileSync(join(process.cwd(), "../data/site", String(url)), "utf8")) };
    if (url === "/config.json") return { ok: true, json: async () => ({ assetBaseUrl: "/assets" }) };
    throw new Error(`Unexpected fetch in history test: ${String(url)}`);
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("F-15 family funding history", () => {
  it("sums each actuals year exactly once and excludes later enacted/request amounts", () => {
    const history = source;
    const citations = getCitations();
    const series = familyHistorySeries(history);
    expect(series.map(p => p.fy)).toEqual(Array.from({ length: 12 }, (_, i) => 2015 + i));
    const actuals = series.filter(p => p.kind === "actuals");
    expect(history.cumulative.point_ids).toEqual(actuals.map(p => p.id));
    expect(history.cumulative.amount_thousands).toBe(actuals.reduce((n, p) => n + p.amount_thousands, 0));
    expect(actuals.at(-1)?.fy).toBe(2024);
    expect(series.at(-1)?.amount_thousands).toBe(3_705_620);
    expect(series.at(-1)?.missing_programs.join(" ")).toContain("0207171F");
    for (const point of series) {
      expect(point.amount_thousands).toBe(point.components.reduce((n, row) => n + row.amount_thousands, 0));
      expect(new Set(point.components.map(r => r.fact_id)).size).toBe(point.components.length);
      expect(citations[point.fact_id].kind).toBe("derived");
      for (const row of point.components) {
        expect(citations[row.fact_id].kind).toBe("workbook");
        expect(row.official_url).toMatch(/^https:\/\/[^/]+\.(?:mil|gov)\//);
      }
    }
    // Older procurement must survive the edition-specific line-number identities.
    expect(series[0].components.some(row => row.pe_bli.startsWith("3010F-"))).toBe(true);
  });

  it("renders the complete matrix immediately with chronological year columns and stable program rows", () => {
    const { history } = getF15FundingHistory();
    render(<FamilyFundingHistory history={history} shortName="F-15" />);
    const table = screen.getByRole("table", { name: "Programs across the years" });
    expect(table.closest("details")).toBeNull();
    expect([...table.querySelectorAll("[data-history-column]")].map(el => el.textContent?.match(/FY(\d+)/)?.[1])).toEqual(Array.from({ length: 12 }, (_, i) => String(2015 + i)));
    expect(table.querySelectorAll("[data-history-program]")).toHaveLength(8);
    expect(table.querySelectorAll("[data-history-cell] [data-amount]")).toHaveLength(67);
    expect(table.querySelectorAll("[data-history-annual] [data-amount]")).toHaveLength(12);
    expect(fetch).not.toHaveBeenCalled();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    for (const row of table.querySelectorAll("[data-history-program]")) expect(row.querySelectorAll("td")).toHaveLength(12);
  });

  it("opens each exact program/year receipt and partitions all 83 workbook inputs once", () => {
    const { history } = getF15FundingHistory();
    const openPanel = vi.fn();
    render(<CitationPanelContext.Provider value={{ openPanel }}><FamilyFundingHistory history={history} shortName="F-15" /></CitationPanelContext.Provider>);
    const table = screen.getByRole("table");
    for (const point of familyHistorySeries(source)) {
      const shownInputs: string[] = [];
      for (const cell of point.program_cells) {
        const el = table.querySelector(`[data-history-program="${cell.program_id}"] [data-history-cell="${point.id}"]`)!;
        shownInputs.push(...el.getAttribute("data-history-inputs")!.split(","));
        const amount = el.querySelector("[data-amount]")!;
        expect(amount).toHaveAttribute("data-fact-id", cell.fact_id);
        expect(amount).toHaveAttribute("data-measure", cell.measure);
        expect(amount).toHaveAttribute("data-fy", String(point.fy));
        fireEvent.click(amount);
        expect(openPanel).toHaveBeenLastCalledWith(cell.fact_id, expect.objectContaining({ fy: point.fy, value: cell.amount_thousands, entity: cell.program_id }));
      }
      expect(shownInputs.sort()).toEqual(point.components.map(row => row.fact_id).sort());
    }
    fireEvent.click(within(screen.getByRole("group", { name: "Funding by fiscal year" })).getByRole("button", { name: /^FY2015 / }));
    expect(table.querySelector('[data-history-column="fy2015a"]')).toHaveAttribute("data-selected", "true");
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
    expect(table.querySelectorAll("[data-history-cell] [data-amount]")).toHaveLength(67);
  });

  it("keeps legacy codes separate, real zeros clickable, and missing funding explicit", () => {
    const { history } = getF15FundingHistory();
    render(<FamilyFundingHistory history={history} shortName="F-15" />);
    const table = screen.getByRole("table");
    const legacy = table.querySelector('[data-history-program="P-1:3010F:AF:F015E0"] [data-history-cell="fy2020a"] [data-amount]')!;
    expect(legacy).toHaveTextContent("$621.1M");
    expect(table.querySelectorAll("[data-history-missing]")).toHaveLength(2);
    for (const point of familyHistorySeries(source)) for (const cell of point.program_cells.filter(cell => cell.amount_thousands === 0)) {
      const amount = table.querySelector(`[data-history-program="${cell.program_id}"] [data-history-cell="${point.id}"] [data-amount]`)!;
      expect(amount).toHaveTextContent("$0");
      expect(amount).toHaveAttribute("role", "button");
    }
    expect(table.querySelector('[data-history-program="R-1:3600F:AF:0207171F"] [data-history-cell="fy2026r"]')).toHaveTextContent("Missing");
  });

  it("opens historical source documents on demand, drills into each input, and restores keyboard focus", async () => {
    const { history, citations } = getF15FundingHistory();
    const point = familyHistorySeries(source).find(point => point.program_cells.some(cell => cell.input_fact_ids.length > 1 && !citations[cell.fact_id]))!;
    const cell = point.program_cells.find(cell => cell.input_fact_ids.length > 1 && !citations[cell.fact_id])!;
    const program = source.programs.find(program => program.id === cell.program_id)!;
    render(<CitationPanelProvider citations={citations} figurePrograms={{ [program.id]: { name: program.title, code: program.code } }}><FamilyFundingHistory history={history} shortName="F-15" /></CitationPanelProvider>);
    const opener = screen.getByRole("table").querySelector(`[data-history-program="${program.id}"] [data-history-cell="${point.id}"] [data-amount]`) as HTMLElement;
    opener.focus();
    fireEvent.keyDown(opener, { key: "Enter" });
    const dialog = await screen.findByRole("dialog", { name: "Citation details" });
    await within(dialog).findByTestId("budget-pdf-receipt");
    fireEvent.click(within(dialog).getByText("Spreadsheet downloads & calculation details"));
    expect(await within(dialog).findByTestId("derived-card")).toBeInTheDocument();
    expect(dialog).toHaveTextContent(program.code);
    expect(within(dialog).getByTestId("receipt-figure-context")).toHaveTextContent(`FY${point.fy}`);
    const docs = await within(dialog).findByTestId("source-documents");
    const inputs = point.components.filter(input => cell.input_fact_ids.includes(input.fact_id));
    await waitFor(() => { for (const input of inputs) {
      expect(docs.querySelector(`a[href="${input.official_url}"]`)).not.toBeNull();
      for (const locator of input.cells.split(",")) expect(docs).toHaveTextContent(locator);
    } });
    const breakdown = await within(dialog).findByTestId("breakdown-table");
    for (const input of inputs) expect(breakdown.querySelector(`[data-fact-id="${input.fact_id}"]`)).not.toBeNull();
    fireEvent.click(breakdown.querySelector(`[data-fact-id="${inputs[0].fact_id}"]`)!);
    await waitFor(() => expect(within(dialog).getByTestId("source-documents")).toHaveTextContent(inputs[0].cells));
    fireEvent.click(within(dialog).getByRole("button", { name: "Back to previous citation" }));
    await waitFor(() => expect(within(dialog).getByTestId("receipt-figure-context")).toHaveTextContent(`FY${point.fy}`));
    fireEvent.keyDown(document.activeElement!, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(opener).toHaveFocus());
    expect(fetch).not.toHaveBeenCalledWith(FAMILY_HISTORY_URL, expect.anything());
  });

  it("rejects regrouped, duplicated, or stale source cells", () => {
    const { history } = getF15FundingHistory();
    expect(Object.keys(familyHistoryInputRows(source, history))).toHaveLength(12);
    const altered = structuredClone(source);
    altered.points[0].program_cells[0].program_id = "P-1:3010F:AF:F015EX";
    expect(() => validateFamilyHistoryMatrix(altered)).toThrow();
    const duplicated = structuredClone(source);
    duplicated.points[0].program_cells.push(duplicated.points[0].program_cells[0]);
    expect(() => validateFamilyHistoryMatrix(duplicated)).toThrow();
    const stale = structuredClone(source);
    stale.points.find(point => point.id === "fy2015a")!.program_cells[0].fact_id = "a".repeat(16);
    expect(() => familyHistoryInputRows(stale, history)).toThrow("cells do not match");
  });

  it("keeps family history independent of the selected aircraft and funding record", async () => {
    window.history.replaceState({}, "", "/families/f-15/");
    Object.defineProperty(window, "scrollTo", { configurable: true, value: vi.fn() });
    render(F15FamilyPage());
    await act(async () => { await new Promise<void>(resolve => requestAnimationFrame(() => resolve())); });
    const total = screen.getByTestId("family-receipt").getAttribute("data-family-cumulative");
    fireEvent.click(within(screen.getByTestId("family-nav")).getByRole("link", { name: "Budget & receipts" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Funding record" }), { target: { value: "0207146F" } });
    fireEvent.click(within(screen.getByTestId("family-nav")).getByRole("link", { name: "Aircraft" }));
    fireEvent.click(within(screen.getByRole("group", { name: "Aircraft variant" })).getByRole("button", { name: "F-15E Strike Eagle" }));
    fireEvent.click(within(screen.getByTestId("family-nav")).getByRole("link", { name: "Budget & receipts" }));
    expect(screen.getByTestId("family-receipt")).toHaveAttribute("data-family-cumulative", total);
    expect(screen.getByRole("group", { name: "Funding by fiscal year" }).querySelectorAll("[data-history-year]")).toHaveLength(12);
  });
});
