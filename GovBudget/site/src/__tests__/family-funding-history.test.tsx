import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within, waitFor } from "@testing-library/react";
import { FamilyFundingHistory } from "@/components/family-funding-history";
import { CitationPanelContext } from "@/components/cite";
import { getF15FundingHistory, getF15FundingHistorySource } from "@/lib/family-funding-history-data";
import { FAMILY_HISTORY_URL, familyHistoryInputRows, familyHistorySeries } from "@/lib/family-funding-history";
import { getCitations } from "@/lib/data";
import F15FamilyPage from "@/app/families/f-15/page";

vi.mock("@/components/f15-model", () => ({ F15Model: () => <div /> }));
const source = getF15FundingHistorySource();
beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (url: RequestInfo | URL) => {
    if (url === FAMILY_HISTORY_URL) return { ok: true, json: async () => source };
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

  it("embeds annual receipts and only the latest source rows without fetching on mount", () => {
    const { history, citations } = getF15FundingHistory();
    expect(history.points).toHaveLength(12);
    expect(history.points.slice(0, -1).every(point => point.components === undefined && point.component_count > 0)).toBe(true);
    expect(history.points.at(-1)?.components).toHaveLength(8);
    expect(Object.keys(citations)).toHaveLength(21);
    render(<FamilyFundingHistory history={history} shortName="F-15" />);
    expect(screen.getByTestId("family-ledger").querySelectorAll("[data-history-input]")).toHaveLength(8);
    expect(fetch).not.toHaveBeenCalled();
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

  it("loads older rows on selection while retaining cited totals and caches later year switches", async () => {
    const { history } = getF15FundingHistory();
    render(<FamilyFundingHistory history={history} shortName="F-15" />);
    const chart = screen.getByRole("group", { name: "Funding by fiscal year" });
    expect(within(chart).getAllByRole("button")).toHaveLength(12);
    const oldYear = source.points.find(p => p.fy === 2015 && p.kind === "actuals")!;
    fireEvent.click(within(chart).getByRole("button", { name: /^FY2015 / }));
    expect(within(chart).getByRole("button", { name: /^FY2015 / })).toHaveAttribute("aria-pressed", "true");
    const ledger = screen.getByTestId("family-ledger");
    expect(ledger).toHaveTextContent("FY2015");
    expect(ledger).toHaveTextContent("Loading FY2015 source rows");
    expect(ledger.querySelectorAll("[data-history-input]")).toHaveLength(0);
    expect(screen.getByTestId("family-receipt").querySelector('[data-history-selected="fy2015a"] [data-amount]')).toHaveAttribute("data-fact-id", oldYear.fact_id);
    await waitFor(() => expect(ledger.querySelectorAll("[data-history-input]")).toHaveLength(oldYear.components.length));
    expect(fetch).toHaveBeenCalledExactlyOnceWith(FAMILY_HISTORY_URL);
    expect(ledger.querySelectorAll("[data-history-input]")).toHaveLength(oldYear.components.length);
    for (const row of oldYear.components) {
      const el = ledger.querySelector(`[data-history-input="${row.fact_id}"]`)!;
      expect(el.querySelector("[data-amount]")).toHaveAttribute("data-fact-id", row.fact_id);
      expect(el.querySelector("a[target='_blank']")).toHaveAttribute("href", row.official_url);
    }
    fireEvent.click(within(chart).getByRole("button", { name: /^FY2026 / }));
    expect(ledger.querySelector("[data-history-missing]")).toHaveTextContent("0207171F");
    expect(ledger.querySelector("[data-history-missing]")).toHaveTextContent("Missing coverage is not zero funding");
    fireEvent.click(within(chart).getByRole("button", { name: /^FY2016 / }));
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(ledger.querySelectorAll("[data-history-input]")).toHaveLength(source.points.find(p => p.id === "fy2016a")!.components.length);
  });

  it("shows retry on failure without a false zero and loads the selected year after retry", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("offline"));
    const { history } = getF15FundingHistory();
    render(<FamilyFundingHistory history={history} shortName="F-15" />);
    fireEvent.click(screen.getByRole("button", { name: /^FY2015 / }));
    expect(await screen.findByRole("alert")).toHaveTextContent("FY2015 source rows could not be loaded");
    const total = screen.getByTestId("family-receipt").querySelector('[data-history-selected="fy2015a"] [data-amount]')!;
    expect(total).toHaveTextContent("$771.1M");
    fireEvent.click(screen.getByRole("button", { name: "Retry loading source rows" }));
    await waitFor(() => expect(screen.getByTestId("family-ledger").querySelectorAll("[data-history-input]")).toHaveLength(5));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("does not replace a newer selection when an earlier request finishes", async () => {
    let finish!: (value: Response) => void;
    vi.mocked(fetch).mockImplementationOnce(() => new Promise<Response>(resolve => { finish = resolve; }));
    const { history } = getF15FundingHistory();
    render(<FamilyFundingHistory history={history} shortName="F-15" />);
    fireEvent.click(screen.getByRole("button", { name: /^FY2015 / }));
    fireEvent.click(screen.getByRole("button", { name: /^FY2016 / }));
    const ledger = screen.getByTestId("family-ledger");
    expect(ledger).toHaveTextContent("Loading FY2016 source rows");
    expect(fetch).toHaveBeenCalledTimes(1);
    await act(async () => { finish({ ok: true, json: async () => source } as Response); });
    expect(ledger.querySelector("summary")).toHaveTextContent("FY2016");
    expect([...ledger.querySelectorAll("[data-history-input]")].map(row => row.getAttribute("data-history-input"))).toEqual(source.points.find(p => p.id === "fy2016a")!.components.map(row => row.fact_id));
  });

  it("rejects a stale or altered source sidecar instead of changing published totals", () => {
    const { history } = getF15FundingHistory();
    expect(Object.keys(familyHistoryInputRows(source, history))).toHaveLength(12);
    const stale = structuredClone(source);
    stale.points.find(p => p.id === "fy2015a")!.fact_id = "a".repeat(16);
    expect(() => familyHistoryInputRows(stale, history)).toThrow("does not match");
    const changed = structuredClone(source);
    changed.points.find(p => p.id === "fy2015a")!.components[0].amount_thousands += 1;
    expect(() => familyHistoryInputRows(changed, history)).toThrow("disagree with total");
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
