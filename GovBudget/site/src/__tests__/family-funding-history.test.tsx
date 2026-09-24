import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { FamilyFundingHistory } from "@/components/family-funding-history";
import { CitationPanelContext } from "@/components/cite";
import { getF15FundingHistory } from "@/lib/family-funding-history-data";
import { familyHistorySeries } from "@/lib/family-funding-history";
import F15FamilyPage from "@/app/families/f-15/page";

vi.mock("@/components/f15-model", () => ({ F15Model: () => <div /> }));
afterEach(cleanup);

describe("F-15 family funding history", () => {
  it("sums each actuals year exactly once and excludes later enacted/request amounts", () => {
    const { history, citations } = getF15FundingHistory();
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

  it("leads with cited family actuals and explicitly bounded historical coverage", () => {
    const { history } = getF15FundingHistory();
    const openPanel = vi.fn();
    render(<CitationPanelContext.Provider value={{ openPanel }}><FamilyFundingHistory history={history} shortName="F-15" /></CitationPanelContext.Provider>);
    const receipt = screen.getByTestId("family-receipt");
    expect(receipt).toHaveTextContent("F-15 family funding");
    expect(receipt).toHaveTextContent("Recorded actuals · FY2015–2024");
    expect(receipt).toHaveTextContent("earlier funding is not included");
    expect(receipt).not.toHaveTextContent("Largest cited");
    const amount = receipt.querySelector('[data-testid="family-receipt-figure"] [data-amount]')!;
    expect(amount).toHaveAttribute("data-fact-id", history.cumulative.fact_id);
    expect(amount).toHaveAttribute("data-entity", "family:f-15");
    fireEvent.click(amount);
    expect(openPanel).toHaveBeenCalledWith(history.cumulative.fact_id, expect.objectContaining({ measure: "actuals" }));
  });

  it("switches the year total and every source row together, preserving direct government links", () => {
    const { history } = getF15FundingHistory();
    render(<FamilyFundingHistory history={history} shortName="F-15" />);
    const chart = screen.getByRole("group", { name: "Funding by fiscal year" });
    expect(within(chart).getAllByRole("button")).toHaveLength(12);
    const oldYear = history.points.find(p => p.fy === 2015)!;
    fireEvent.click(within(chart).getByRole("button", { name: /^FY2015 / }));
    expect(within(chart).getByRole("button", { name: /^FY2015 / })).toHaveAttribute("aria-pressed", "true");
    const ledger = screen.getByTestId("family-ledger");
    expect(ledger).toHaveTextContent("FY2015");
    expect(ledger.querySelectorAll("[data-history-input]")).toHaveLength(oldYear.components.length);
    for (const row of oldYear.components) {
      const el = ledger.querySelector(`[data-history-input="${row.fact_id}"]`)!;
      expect(el.querySelector("[data-amount]")).toHaveAttribute("data-fact-id", row.fact_id);
      expect(el.querySelector("a[target='_blank']")).toHaveAttribute("href", row.official_url);
    }
    fireEvent.click(within(chart).getByRole("button", { name: /^FY2026 / }));
    expect(ledger.querySelector("[data-history-missing]")).toHaveTextContent("0207171F");
    expect(ledger.querySelector("[data-history-missing]")).toHaveTextContent("Missing coverage is not zero funding");
  });

  it("keeps family history independent of the selected aircraft and funding record", async () => {
    window.history.replaceState({}, "", "/families/f-15/");
    Object.defineProperty(window, "scrollTo", { configurable: true, value: vi.fn() });
    render(F15FamilyPage());
    await act(async () => { await new Promise<void>(resolve => requestAnimationFrame(() => resolve())); });
    const total = screen.getByTestId("family-receipt").getAttribute("data-family-cumulative");
    fireEvent.click(within(screen.getByTestId("family-nav")).getByRole("link", { name: "Budget & receipts" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Funding record" }), { target: { value: "0207146F" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Selected aircraft" }), { target: { value: "E" } });
    expect(screen.getByTestId("family-receipt")).toHaveAttribute("data-family-cumulative", total);
    expect(screen.getByRole("group", { name: "Funding by fiscal year" }).querySelectorAll("[data-history-year]")).toHaveLength(12);
  });
});
