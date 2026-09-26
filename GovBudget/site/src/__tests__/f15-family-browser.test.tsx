import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { CitationPanelContext } from "@/components/cite";
import { CitationPanelProvider } from "@/components/citation-panel/panel";
import { F15FamilyBrowser } from "@/components/f15-family-browser";
import { getF15FamilyData } from "@/lib/f15-family-data";
import { getRecordFact, type F15FamilyPayload, type VariantId } from "@/lib/f15-family";
import { parseFamilyView, readSavedFactIds, serializeFamilyView, type FamilyView } from "@/lib/f15-browser-state";
import { gzipSync } from "node:zlib";
import { trackReaderEvent } from "@/lib/reader-events";

vi.mock("@/lib/reader-events", () => ({ trackReaderEvent: vi.fn() }));

vi.mock("@/components/f15-model", () => ({
  F15Model: ({ variant, compareVariant, topic, onTopicChange }: { variant: string; compareVariant: string | null; topic: string; onTopicChange: (topic: string) => void }) => (
    <div data-testid="family-model" data-variant={variant} data-compare={compareVariant ?? ""} data-topic={topic}>
      <button onClick={() => onTopicChange("cockpit")}>Inspect cockpit on model</button>
    </div>
  ),
}));

const family = getF15FamilyData();
const openPanel = vi.fn();
const writeText = vi.fn<(...args: string[]) => Promise<void>>();
const scrollTo = vi.fn();
const STORAGE_KEY = "fiscal-receipts:f15-research:v1";

beforeEach(() => {
  window.history.replaceState({}, "", "/family/f-15/");
  localStorage.clear();
  openPanel.mockReset();
  vi.mocked(trackReaderEvent).mockReset();
  writeText.mockReset().mockResolvedValue(undefined);
  scrollTo.mockReset();
  Object.defineProperty(window, "scrollTo", { configurable: true, value: scrollTo });
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: vi.fn() });
});

afterEach(async () => {
  cleanup();
  await act(async () => { await new Promise<void>((resolve) => requestAnimationFrame(() => resolve())); });
  vi.restoreAllMocks();
});

async function mount(search = "", payload: F15FamilyPayload = family) {
  window.history.replaceState({}, "", `/family/f-15/${search}`);
  const result = render(<CitationPanelContext.Provider value={{ openPanel, hasCitation: (id) => Boolean(payload.citations[id]) }}><F15FamilyBrowser family={payload} /></CitationPanelContext.Provider>);
  await act(async () => { await new Promise<void>((resolve) => requestAnimationFrame(() => resolve())); });
  return result;
}

function variants() { return within(screen.getByRole("group", { name: "Aircraft variant" })); }
function chooseVariant(id: VariantId) {
  const previousSection = within(screen.getByRole("navigation", { name: "F-15 family sections" })).getByRole("link", { current: "page" }).textContent!;
  if (previousSection !== "Aircraft") navigate("Aircraft");
  const variant = family.variants.find((item) => item.id === id)!;
  fireEvent.click(variants().getByRole("button", { name: `${variant.name} ${variant.nickname}` }));
  expect(variants().getByRole("button", { name: `${variant.name} ${variant.nickname}` })).toHaveAttribute("aria-pressed", "true");
  if (previousSection !== "Aircraft") navigate(previousSection);
}
function funding() { return within(screen.getByRole("region", { name: "Budget & receipts." })); }
function recordSelector() { return screen.getByRole("combobox", { name: "Funding record" }); }
function budgetRecords() { return within(recordSelector()); }
function chooseRecord(slug: string) { fireEvent.change(recordSelector(), { target: { value: slug } }); }
function fiscalYears() { return within(screen.getByRole("group", { name: "Fiscal year" })); }
function selectYear(fy: number) { fireEvent.click(fiscalYears().getByRole("button", { name: new RegExp(`^Select FY${fy},`) })); }
function selectedRecord() { return screen.getByRole("article", { name: "Selected funding record" }); }
function query() { return new URLSearchParams(window.location.search); }
function navigate(label: string) { fireEvent.click(within(screen.getByRole("navigation", { name: "F-15 family sections" })).getByRole("link", { name: label })); }
function openResearchTray() { fireEvent.click(screen.getByRole("link", { name: /^Research tray/ })); }

describe("F-15 browser uses actual family data", () => {
  it("copies a complete funding answer and records only completed copies", async () => {
    await mount("#funding");
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    await waitFor(() => expect(trackReaderEvent).toHaveBeenCalledWith("answer_copied", expect.objectContaining({ factId: "4a9ae7cc78dcf0ba", fiscalYear: 2026, measure: "request" })));
    const text = writeText.mock.calls[0][0];
    expect(text).toContain("FY2026 request");
    expect(text).toContain("Total obligation authority (TOA) · PB2026");
    const url = new URL(text.split("Selected view: ")[1]);
    expect(url.searchParams.get("record")).toBe("F015EX");
    expect(url.searchParams.get("variant")).toBe("EX");
    expect(url.hash).toBe("#funding");
    expect(vi.mocked(trackReaderEvent).mock.calls.filter(([event]) => event === "answer_copied")).toHaveLength(1);
    writeText.mockRejectedValueOnce(new Error("blocked"));
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    expect(await screen.findByRole("textbox", { name: "Copy this text" })).toHaveValue(text);
    expect(vi.mocked(trackReaderEvent).mock.calls.filter(([event]) => event === "answer_copied")).toHaveLength(1);
  });

  it("tracks selection and one save but not duplicate saves", async () => {
    await mount("#funding");
    selectYear(2025);
    expect(trackReaderEvent).toHaveBeenCalledWith("funding_selected", expect.objectContaining({ fiscalYear: 2025, measure: "enacted" }));
    fireEvent.click(screen.getByRole("button", { name: "Save receipt" }));
    fireEvent.click(screen.getByRole("button", { name: "Saved to research" }));
    expect(vi.mocked(trackReaderEvent).mock.calls.filter(([event]) => event === "receipt_saved")).toHaveLength(1);
  });
  it("starts on EX procurement with a cited multi-activity total and passes full receipt context", async () => {
    await mount("#funding");
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-variant", "EX");
    const article = selectedRecord();
    const headline = article.querySelector('[data-amount][data-fact-id="4a9ae7cc78dcf0ba"]');
    expect(headline).toHaveTextContent("$3.01B");
    expect(headline).toHaveAttribute("data-basis", "toa");
    expect(headline).toHaveAttribute("data-fy", "2026");
    expect(headline).toHaveAttribute("data-measure", "request");
    expect(headline).toHaveAttribute("data-entity", "F015EX");
    expect(within(article).getByText("New aircraft, in-service modifications, support equipment and facilities.")).toBeVisible();
    const fullScope = within(article).getByText(/broader than the price of new aircraft/);
    expect(fullScope).not.toBeVisible();
    fireEvent.click(within(article).getByText("Source data"));
    expect(fullScope).toBeVisible();
    fireEvent.click(within(article).getByText("Source data"));
    fireEvent.click(screen.getByRole("button", { name: "Open budget receipt" }));
    expect(openPanel).toHaveBeenCalledWith("4a9ae7cc78dcf0ba", expect.objectContaining({ value: 3_014_394, units: "USD thousands", fy: 2026, measure: "request", basis: "toa", entity: "F015EX", edition: 2026 }));
    navigate("Aircraft");
    expect(screen.getByRole("button", { name: "Sound off" })).toHaveAttribute("aria-pressed", "false");
  });

  it("backs the request-change headline with its exact receipt and avoids increase claims for historical or missing years", async () => {
    await mount("#funding");
    const record = family.records.find((item) => item.slug === "F015EX")!;
    const change = record.change!;
    const headline = within(selectedRecord()).getByRole("heading", { name: /more than FY2025 enacted$/ });
    const delta = headline.querySelector("[data-amount]");
    expect(delta).toHaveAttribute("data-fact-id", change.factId);
    expect(delta).toHaveAttribute("data-fy", "2026");
    expect(delta).toHaveAttribute("data-basis", "toa");
    expect(delta).toHaveTextContent("$1.21B");
    expect(within(selectedRecord()).getByText("FY2026 request compared with FY2025 enacted funding.")).toBeInTheDocument();
    fireEvent.click(within(headline).getByRole("button", { name: /click to view citation/ }));
    expect(openPanel).toHaveBeenLastCalledWith(change.factId, expect.objectContaining({ value: change.amountThousands, units: "USD thousands", fy: 2026, measure: change.measure, basis: "toa", entity: "F015EX", edition: 2026 }));

    selectYear(2025);
    expect(within(selectedRecord()).getByRole("heading", { level: 3, name: "FY2025 enacted funding" })).toBeVisible();
    expect(within(selectedRecord()).queryByRole("heading", { name: /more than|change from/ })).toBeNull();
    expect(selectedRecord().querySelector(`[data-amount][data-fact-id="${change.factId}"]`)).toBeNull();
    chooseRecord("0207171F");
    expect(within(selectedRecord()).getByRole("heading", { level: 3, name: "No matching TOA figure for FY2025." })).toBeVisible();
    expect(within(selectedRecord()).queryByRole("heading", { name: /more than|change from/ })).toBeNull();
    expect(selectedRecord().querySelector('[data-amount][data-fy="2025"]')).toBeNull();
  });

  it("explains chart statuses as budget authority, approval and proposals rather than cash payments", async () => {
    await mount("#funding");
    const explanation = funding().getByText("Actuals report past budget authority. Enacted funding is approved; requests are proposals.");
    expect(explanation).toBeVisible();
    expect(explanation).not.toHaveTextContent(/cash|spent|payments/i);
    expect(funding().getByText("Funding authority, not payments or aircraft unit prices.")).toBeInTheDocument();
  });

  it("shows one exact EX comparison and opens its receipt without selecting a different year", async () => {
    await mount("#funding");
    const record = family.records.find((item) => item.slug === "F015EX")!;
    const change = record.change!;
    const from = getRecordFact(record, 2025)!;
    const to = getRecordFact(record, 2026)!;
    expect(change.amountThousands).toBe(to.amountThousands - from.amountThousands);
    expect(change.fromFactId).toBe(from.factId);
    expect(change.toFactId).toBe(to.factId);
    const yearGroup = screen.getByRole("group", { name: "Fiscal year" });
    const targetButton = within(yearGroup).getByRole("button", { name: /^Select FY2026,/ });
    const comparisonHeading = within(selectedRecord()).getByRole("heading", { name: /more than FY2025 enacted$/ });
    const delta = within(comparisonHeading).getByRole("button", { name: "$1.21B — click to view citation" });
    expect(delta).toBeVisible();
    expect(selectedRecord().querySelectorAll(`[data-amount][data-fact-id="${change.factId}"]`)).toHaveLength(1);
    expect(yearGroup).not.toContainElement(delta);
    expect(delta.closest('button[aria-label^="Select FY"]')).toBeNull();
    expect(delta).toHaveAttribute("data-fact-id", change.factId);
    expect(delta).toHaveAttribute("data-fy", "2026");
    expect(delta).toHaveAttribute("data-measure", "change");
    expect(delta).toHaveAttribute("data-basis", "toa");

    expect(delta).toHaveAttribute("title", "$1,205,922 (USD thousands)");
    const sourceButton = within(yearGroup).getByRole("button", { name: /^Select FY2025,/ });
    expect(sourceButton).toHaveAttribute("data-chart-fact-id", change.fromFactId);
    expect(sourceButton.parentElement).toHaveAttribute("data-comparison-from", "true");
    expect(targetButton).toHaveAttribute("data-chart-fact-id", change.toFactId);
    expect(targetButton.parentElement).toHaveAttribute("data-comparison-year", "true");
    expect(funding().getByText("FY2026 request compared with FY2025 enacted funding.")).toBeInTheDocument();

    fireEvent.click(delta);
    expect(openPanel).toHaveBeenLastCalledWith(change.factId, { value: 1_205_922, units: "USD thousands", fy: 2026, measure: "change", basis: "toa", entity: "F015EX", edition: 2026, display: null });
    expect(targetButton).toHaveAttribute("aria-pressed", "true");
    expect(query().get("fy") ?? "2026").toBe("2026");

    selectYear(2025);
    expect(yearGroup.querySelector(`[data-amount][data-fact-id="${change.factId}"]`)).toBeNull();
    expect(selectedRecord().querySelector(`[data-amount][data-fact-id="${change.factId}"]`)).toBeNull();
    expect(yearGroup.querySelector('[data-comparison-year="true"]')).toBeNull();
    selectYear(2026);
    expect(funding().getByRole("button", { name: "$1.21B — click to view citation" })).toBeVisible();
    expect(selectedRecord().querySelectorAll(`[data-amount][data-fact-id="${change.factId}"]`)).toHaveLength(1);
    chooseRecord("0207171F");
    expect(funding().getByRole("heading", { name: "No matching TOA figure for FY2026." })).toBeVisible();
    expect(selectedRecord().querySelector(`[data-amount][data-fact-id="${change.factId}"]`)).toBeNull();
    expect(funding().queryByRole("heading", { name: /more than|change from/ })).toBeNull();
  });

  it("keeps a small canonical change visible with the same complete source context", async () => {
    await mount("?variant=E&purpose=upgrade&record=F15EWS&fy=2026#funding");
    const record = family.records.find((item) => item.slug === "F15EWS")!;
    const change = record.change!;
    expect(change.factId).toBe("619c9271f416aa12");
    expect(change.amountThousands).toBe(25_265);
    expect(change.amountThousands).toBe(getRecordFact(record, 2026)!.amountThousands - getRecordFact(record, 2025)!.amountThousands);
    const yearGroup = screen.getByRole("group", { name: "Fiscal year" });
    expect(yearGroup.querySelector(`[data-amount][data-fact-id="${change.factId}"]`)).toBeNull();
    expect(within(yearGroup).queryByText(/more than/)).toBeNull();
    const comparisonHeading = within(selectedRecord()).getByRole("heading", { name: /more than FY2025 enacted$/ });
    const citation = within(comparisonHeading).getByRole("button", { name: /click to view citation/ });
    expect(citation).toBeVisible();
    expect(selectedRecord().querySelectorAll(`[data-amount][data-fact-id="${change.factId}"]`)).toHaveLength(1);
    expect(citation).toHaveAttribute("data-fact-id", change.factId);
    expect(citation).toHaveAttribute("data-measure", "change");
    expect(funding().getByText("FY2026 request compared with FY2025 enacted funding.")).toBeInTheDocument();
    fireEvent.click(citation);
    expect(openPanel).toHaveBeenLastCalledWith("619c9271f416aa12", { value: 25_265, units: "USD thousands", fy: 2026, measure: "change", basis: "toa", entity: "F15EWS", edition: 2026, display: null });
  });

  it("identifies a nonadjacent comparison's exact endpoints without attributing it to the intervening year", async () => {
    const payload = structuredClone(family);
    const record = payload.records.find((item) => item.slug === "F015EX")!;
    const change = record.change!;
    // Synthetic coverage keeps the same reconciled values, but moves the
    // comparison's enacted source to FY2023. FY2024 lies between the endpoints.
    const originalFrom = record.facts.find((fact) => fact.factId === change.fromFactId)!;
    record.facts = record.facts.filter((fact) => fact.fy !== 2023 && fact.factId !== originalFrom.factId);
    record.facts.push({ ...originalFrom, fy: 2023 });
    record.preferredFactIds[2023] = originalFrom.factId;
    delete record.preferredFactIds[2025];
    await mount("?fy=2026#funding", payload);
    const yearGroup = screen.getByRole("group", { name: "Fiscal year" });
    expect(yearGroup.querySelector(`[data-amount][data-fact-id="${change.factId}"]`)).toBeNull();
    const sourceYear = fiscalYears().getByRole("button", { name: /^Select FY2023,/ });
    expect(sourceYear).toHaveAttribute("data-chart-fact-id", originalFrom.factId);
    expect(sourceYear.parentElement).toHaveAttribute("data-comparison-from", "true");
    expect(fiscalYears().getByRole("button", { name: /^Select FY2024,/ }).parentElement).toHaveAttribute("data-comparison-year", "false");
    expect(funding().getByText("FY2026 request compared with FY2023 enacted funding.")).toBeInTheDocument();
    const comparisonHeading = within(selectedRecord()).getByRole("heading", { name: /more than FY2023 enacted$/ });
    const citation = within(comparisonHeading).getByRole("button", { name: "$1.21B — click to view citation" });
    expect(citation).toHaveAttribute("data-fact-id", change.factId);
    expect(selectedRecord().querySelectorAll(`[data-amount][data-fact-id="${change.factId}"]`)).toHaveLength(1);
    fireEvent.click(citation);
    expect(openPanel).toHaveBeenLastCalledWith(change.factId, { value: 1_205_922, units: "USD thousands", fy: 2026, measure: "change", basis: "toa", entity: "F015EX", edition: 2026, display: null });
  });

  it("opens the exact three additive source inputs with complete fiscal context", async () => {
    await mount("#funding");
    const included = screen.getByRole("region", { name: "Included in this total" });
    const expected = [
      ["Combat aircraft", "03407158217dec76", 2_480_818, "F015EX/F/3010F/01/fy_2026_total"],
      ["Aircraft modifications", "5768200ce4fbc494", 286_700, "F015EX/F/3010F/05/fy_2026_total"],
      ["Support & facilities", "819f32a0ad3fb66e", 246_876, "F015EX/F/3010F/07/fy_2026_total"],
    ] as const;
    expect(within(included).getAllByRole("listitem")).toHaveLength(3);
    expect(Array.from(included.querySelectorAll("[data-amount]")).map((figure) => figure.getAttribute("data-fact-id"))).toEqual(expected.map(([, factId]) => factId));
    for (const [label, factId, amount, entity] of expected) {
      const row = within(included).getByText(label).closest("li")!;
      const figure = within(row).getByRole("button", { name: /click to view citation/ });
      expect(figure).toBeVisible();
      expect(figure).toHaveAttribute("data-fact-id", factId);
      expect(figure).toHaveAttribute("data-fy", "2026");
      expect(figure).toHaveAttribute("data-measure", "request");
      fireEvent.click(figure);
      expect(openPanel).toHaveBeenLastCalledWith(factId, expect.objectContaining({ value: amount, units: "USD thousands", entity, fy: 2026, measure: "request", basis: "toa", edition: 2026 }));
    }
    expect(openPanel).toHaveBeenCalledTimes(3);
    expect(included.querySelector('[data-fact-id="4a9ae7cc78dcf0ba"]')).toBeNull();
    expect(included.querySelector('[data-measure="reconciliation-request"]')).toBeNull();
  });

  it("updates included inputs for the selected year and hides them for a direct or missing total", async () => {
    await mount("#funding");
    selectYear(2024);
    const historical = screen.getByRole("region", { name: "Included in this total" });
    expect(Array.from(historical.querySelectorAll("[data-amount]")).map((figure) => figure.getAttribute("data-fact-id"))).toEqual(["c05ad3ce0481b0ef", "97884d9ae98e9e06"]);
    expect(historical.querySelector('[data-fy="2026"]')).toBeNull();
    expect(historical.querySelectorAll('[data-fy="2024"][data-measure="actuals"][data-amount]')).toHaveLength(2);
    selectYear(2025);
    expect(screen.queryByRole("region", { name: "Included in this total" })).toBeNull();
    expect(selectedRecord().querySelector('[data-amount][data-fact-id="92835a9645aa3793"]')).not.toBeNull();
    selectYear(2026);
    expect(within(screen.getByRole("region", { name: "Included in this total" })).getAllByRole("listitem")).toHaveLength(3);
    chooseRecord("0207171F");
    expect(screen.queryByRole("region", { name: "Included in this total" })).toBeNull();
    selectYear(2025);
    const missingYear = fiscalYears().getByRole("button", { name: "Select FY2025, no figure in this collection" });
    expect(missingYear).toHaveAttribute("aria-pressed", "true");
    expect(missingYear).not.toHaveAttribute("data-chart-fact-id");
    expect(missingYear.querySelector("[data-status]")).toBeNull();
    expect(funding().getByRole("heading", { name: "No matching TOA figure for FY2025." })).toBeVisible();
    expect(funding().queryByRole("button", { name: "Open budget receipt" })).toBeNull();
    expect(selectedRecord().querySelector('[data-amount][data-fy="2025"]')).toBeNull();
  });

  it("keeps the receipt total tied to its parent fact and separate from the additive inputs across fiscal years", async () => {
    await mount("#funding");
    const record = family.records.find((item) => item.slug === "F015EX")!;
    const expected = [
      { fy: 2026, label: "Total requested", heading: "FY2026 request — source rows", factId: "4a9ae7cc78dcf0ba", value: 3_014_394, measure: "request", inputIds: ["03407158217dec76", "5768200ce4fbc494", "819f32a0ad3fb66e"] },
      { fy: 2024, label: "Reported total", heading: "FY2024 actuals — source rows", factId: "84b823fc2c6e3b8a", value: 2_739_061, measure: "actuals", inputIds: ["c05ad3ce0481b0ef", "97884d9ae98e9e06"] },
      { fy: 2025, label: "Total enacted", heading: "FY2025 enacted — source record", factId: "92835a9645aa3793", value: 1_808_472, measure: "enacted", inputIds: [] },
    ];
    for (const { fy, label, heading, factId, value, measure, inputIds } of expected) {
      selectYear(fy);
      const selectedFact = getRecordFact(record, fy)!;
      expect(selectedFact.factId).toBe(factId);
      expect(selectedFact.amountThousands).toBe(value);
      const sourceTrail = screen.getByRole("region", { name: "Budget source trail" });
      expect(within(sourceTrail).getByRole("heading", { level: 3, name: heading })).toBeVisible();
      const totalRow = within(sourceTrail).getByText(label).parentElement!;
      const total = within(totalRow).getByRole("button", { name: /click to view citation/ });
      expect(total).toBeVisible();
      expect(total).toHaveAttribute("data-fact-id", factId);
      expect(total).toHaveAttribute("data-fy", String(fy));
      expect(total).toHaveAttribute("data-basis", "toa");
      expect(total).toHaveAttribute("data-measure", measure);
      expect(total).toHaveAttribute("data-entity", "F015EX");
      expect(total).toHaveAttribute("data-dataset", selectedFact.dataset);
      expect(total).toHaveAttribute("title", `$${value.toLocaleString("en-US")} (USD thousands)`);
      expect(totalRow.querySelectorAll(`[data-amount][data-fact-id="${factId}"]`)).toHaveLength(1);
      const inputs = within(sourceTrail).queryByRole("region", { name: "Included in this total" });
      if (inputIds.length) {
        expect(inputs).not.toContainElement(total);
        expect(Array.from(inputs!.querySelectorAll("[data-amount]")).map((item) => item.getAttribute("data-fact-id"))).toEqual(inputIds);
      } else {
        expect(inputs).toBeNull();
      }
      // The selected parent and its additive inputs remain separate, regardless
      // of historical chart values or the comparison displayed alongside them.
      expect(totalRow.querySelectorAll("[data-amount]")).toHaveLength(1);
      expect(inputs?.querySelectorAll("[data-amount]").length ?? 0).toBe(inputIds.length);
      fireEvent.click(total);
      expect(openPanel).toHaveBeenLastCalledWith(factId, { value, units: "USD thousands", fy, measure, basis: "toa", entity: "F015EX", edition: 2026, display: null });
      for (const other of expected.filter((item) => item.fy !== fy)) {
        expect(totalRow.querySelector(`[data-amount][data-fact-id="${other.factId}"]`)).toBeNull();
        expect(inputs?.querySelector(`[data-amount][data-fact-id="${other.factId}"]`) ?? null).toBeNull();
        expect(within(sourceTrail).queryByText(other.label)).toBeNull();
      }
    }
    expect(openPanel).toHaveBeenCalledTimes(3);
  });

  it("does not retain a receipt total for missing funding or an aircraft without a mapped record", async () => {
    await mount("#funding");
    expect(funding().getByText("Total requested")).toBeVisible();
    chooseRecord("0207171F");
    for (const fy of [2026, 2025]) {
      selectYear(fy);
      expect(funding().getByRole("heading", { name: `No matching TOA figure for FY${fy}.` })).toBeVisible();
      expect(funding().queryByRole("region", { name: "Budget source trail" })).toBeNull();
      expect(funding().queryByText(/^(Total requested|Total enacted|Reported total)$/)).toBeNull();
    }
    for (const variant of ["A", "B"] as const) {
      chooseVariant(variant);
      expect(screen.getByTestId("family-model")).toHaveAttribute("data-variant", variant);
      expect(screen.queryByRole("article", { name: "Selected funding record" })).toBeNull();
      expect(funding().queryByRole("region", { name: "Budget source trail" })).toBeNull();
      expect(funding().queryByText(/^(Total requested|Total enacted|Reported total)$/)).toBeNull();
      expect(document.querySelectorAll('[data-workspace-section="funding"] [data-amount]')).toHaveLength(0);
    }
  });

  it("uses one amount control per FY2026 row to open the canonical workbook citation with exact input context", async () => {
    await mount("#funding");
    const sourceTrail = screen.getByRole("region", { name: "Budget source trail" });
    const included = within(sourceTrail).getByRole("region", { name: "Included in this total" });
    const officialUrl = "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx";
    const expected = [
      ["Combat aircraft", "03407158217dec76", "W847", 2_480_818, "F015EX/F/3010F/01/fy_2026_total"],
      ["Aircraft modifications", "5768200ce4fbc494", "W875", 286_700, "F015EX/F/3010F/05/fy_2026_total"],
      ["Support & facilities", "819f32a0ad3fb66e", "W923,W932", 246_876, "F015EX/F/3010F/07/fy_2026_total"],
    ] as const;
    expect(funding().getByRole("link", { name: "Official document" })).not.toBeVisible();
    fireEvent.click(funding().getByText("Source data"));
    expect(funding().getByRole("link", { name: "Official document" })).toBeVisible();
    expect(funding().getByRole("link", { name: "Official document" })).toHaveAttribute("href", officialUrl);
    fireEvent.click(funding().getByText("Source data"));
    expect(within(included).getAllByRole("button")).toHaveLength(3);

    for (const [label, factId, cells, value, entity] of expected) {
      const citation = family.citations[factId];
      expect(citation.kind).toBe("workbook");
      expect(citation.cells).toBe(cells);
      expect(citation.sheet).toBe("Exhibit P-1");
      expect(citation.official_url).toBe(officialUrl);
      const row = within(included).getByText(label).closest("li")!;
      const amount = within(row).getByRole("button", { name: /click to view citation/ });
      expect(within(row).getAllByRole("button")).toEqual([amount]);
      expect(amount).toBeVisible();
      expect(amount).toHaveAttribute("data-fact-id", factId);
      expect(amount).toHaveAttribute("title", `$${value.toLocaleString("en-US")} (USD thousands)`);
      fireEvent.click(amount);
      expect(openPanel).toHaveBeenLastCalledWith(factId, { value, units: "USD thousands", fy: 2026, measure: "request", basis: "toa", entity, edition: 2026, display: null });
    }
    expect(openPanel).toHaveBeenCalledTimes(3);
  });

  it("switches the sole row citations to FY2024 sources and removes input controls for the FY2025 direct total", async () => {
    await mount("#funding");
    selectYear(2024);
    const included = screen.getByRole("region", { name: "Included in this total" });
    const expected = [
      ["c05ad3ce0481b0ef", "O847,O848,O849", 2_659_261, "F015EX/F/3010F/01/fy_2024_actuals"],
      ["97884d9ae98e9e06", "O875", 79_800, "F015EX/F/3010F/05/fy_2024_actuals"],
    ] as const;
    const amounts = within(included).getAllByRole("button");
    expect(amounts).toHaveLength(2);
    expected.forEach(([factId, cells, value, entity], index) => {
      expect(family.citations[factId].cells).toBe(cells);
      expect(amounts[index]).toHaveAccessibleName(/click to view citation/);
      expect(amounts[index]).toHaveAttribute("data-fact-id", factId);
      expect(amounts[index]).toHaveAttribute("data-fy", "2024");
      expect(amounts[index]).toHaveAttribute("data-measure", "actuals");
      fireEvent.click(amounts[index]);
      expect(openPanel).toHaveBeenLastCalledWith(factId, { value, units: "USD thousands", fy: 2024, measure: "actuals", basis: "toa", entity, edition: 2026, display: null });
    });
    expect(included.querySelector('[data-fy="2026"]')).toBeNull();

    selectYear(2025);
    const sourceTrail = screen.getByRole("region", { name: "Budget source trail" });
    expect(within(sourceTrail).queryByRole("region", { name: "Included in this total" })).toBeNull();
    expect(sourceTrail.querySelector('[data-fact-id="c05ad3ce0481b0ef"], [data-fact-id="97884d9ae98e9e06"]')).toBeNull();
    fireEvent.click(within(sourceTrail).getByRole("button", { name: "Open budget receipt" }));
    expect(openPanel).toHaveBeenLastCalledWith("92835a9645aa3793", { value: 1_808_472, units: "USD thousands", fy: 2025, measure: "enacted", basis: "toa", entity: "F015EX", edition: 2026 });
  });

  it.each([
    { fy: 2026, factId: "03407158217dec76", cells: ["W847"], amount: "2,480,818", measure: "request" },
    { fy: 2024, factId: "c05ad3ce0481b0ef", cells: ["O847", "O848", "O849"], amount: "2,659,261", measure: "actuals" },
    { fy: 2025, factId: "92835a9645aa3793", cells: ["Q847", "Q848"], amount: "1,808,472", measure: "enacted" },
  ])("opens and copies the real FY$fy workbook receipt with canonical cells and declared fiscal status", async ({ fy, factId, cells, amount, measure }) => {
    const payload = structuredClone(family);
    const input = payload.records.find((record) => record.slug === "F015EX")!.componentRows.find((row) => row.factId === factId)!;
    if (input) input.source.locator = "Narrative row description is not a canonical workbook cell";
    const citation = payload.citations[factId];
    if (citation.kind !== "workbook") throw new Error("Expected canonical workbook fixture");
    expect(citation.cells?.split(",")).toEqual(cells);
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => ({
      ok: String(url) === "/config.json",
      status: String(url) === "/config.json" ? 200 : 404,
      json: async () => ({ assetBaseUrl: "/assets" }),
    } as Response));
    window.history.replaceState({}, "", `/family/f-15/?fy=${fy}#funding`);
    render(<CitationPanelProvider citations={payload.citations}><F15FamilyBrowser family={payload} /></CitationPanelProvider>);
    await act(async () => { await new Promise<void>((resolve) => requestAnimationFrame(() => resolve())); });
    const sourceTrail = screen.getByRole("region", { name: "Budget source trail" });
    const included = within(sourceTrail).queryByRole("region", { name: "Included in this total" });
    const opener = within(included ?? sourceTrail).getAllByRole("button").find((button) => button.getAttribute("data-fact-id") === factId)!;
    if (included) expect(within(opener.closest("li")!).getAllByRole("button")).toEqual([opener]);
    else expect(within(sourceTrail).getByText("Total enacted").parentElement!.querySelectorAll(`[role="button"][data-fact-id="${factId}"]`)).toHaveLength(1);
    act(() => opener.focus());
    fireEvent.keyDown(opener, { key: "Enter" });
    const dialog = await screen.findByRole("dialog", { name: "Citation details" });
    expect(within(dialog).getByTestId("workbook-amount")).toHaveTextContent(`${amount} USD thousands`);
    expect(within(dialog).getByTestId("workbook-amount-basis")).toHaveTextContent(`FY${fy} · ${measure} · P-1 TOA · PB2026`);
    expect(within(dialog).getAllByTestId("cell-ref").map((cell) => cell.getAttribute("data-cell"))).toEqual(cells);
    expect(within(dialog).getByText("Exhibit P-1")).toBeVisible();
    expect(within(dialog).getByRole("link", { name: /^Government original\s*\(opens in new tab\)$/ })).toHaveAttribute("href", citation.official_url);
    expect(within(dialog).getByRole("button", { name: "Download government spreadsheet" })).toHaveAttribute("data-filename", "PB2026_DoD_P-1_Procurement.xlsx");
    expect(within(dialog).getByTestId("panel-fact-permalink")).toHaveAttribute("href", `/fact/${factId.slice(0, 8)}`);
    fireEvent.click(within(dialog).getByRole("button", { name: "Copy this citation as a formatted footnote" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const footnote = writeText.mock.calls[0][0];
    expect(footnote).toContain(`FY${fy} ${measure} Total Obligation Authority (P-1)`);
    expect(footnote).toContain(`$${amount} thousand`);
    expect(footnote).toContain("FY2026 Department of Defense Budget: Procurement Programs (P-1)");
    expect(footnote).toContain(`sheet Exhibit P-1, cells ${cells.join(",")}`);
    expect(footnote).toContain(`https://fiscalreceipts.com/fact/${factId.slice(0, 8)}`);
    fireEvent.click(within(dialog).getByRole("button", { name: "Close citation panel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(opener).toHaveFocus());
  });

  it("switches to historical A without carrying over EX figures or a zero budget", async () => {
    await mount("#funding");
    chooseVariant("A");
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-variant", "A");
    expect(funding().getByText(/F-15A: an earlier chapter of the Eagle/)).toBeVisible();
    expect(funding().getByText(/No separately identified F-15A budget record/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Open budget receipt" })).toBeNull();
    expect(document.querySelectorAll('[data-workspace-section="funding"] [data-amount]')).toHaveLength(0);
    expect(query().get("variant")).toBe("A");
    expect(query().get("record")).toBe("");
    navigate("Aircraft");
    expect(screen.getByTestId("family-model")).toBeVisible();
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-variant", "A");
    expect(document.querySelector('[data-family-topic="airframe"]')).not.toHaveTextContent("not mapped");
    expect(document.querySelector('[data-family-topic="airframe"] p')?.textContent?.length).toBeGreaterThan(100);
  });

  it.each(["A", "B"] as const)("can share an unmapped F-15%s view and return to EX funding from the aircraft buttons", async (id) => {
    await mount("#funding");
    chooseVariant(id);
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-variant", id);
    expect(screen.getByRole("button", { name: "Share view" })).toBeVisible();
    expect(screen.queryByRole("combobox", { name: "Selected aircraft" })).toBeNull();
    expect(funding().queryAllByRole("combobox")).toEqual([]);
    expect(funding().queryByRole("combobox", { name: "Funding record" })).toBeNull();
    expect(funding().queryByRole("button", { name: "Open budget receipt" })).toBeNull();
    expect(document.querySelectorAll('[data-workspace-section="funding"] [data-amount]')).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Share view" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const shared = new URL(writeText.mock.calls[0][0]);
    expect(shared.hash).toBe("#funding");
    expect(shared.searchParams.get("variant")).toBe(id);
    expect(shared.searchParams.get("record")).toBe("");

    chooseVariant("EX");
    expect(window.location.hash).toBe("#funding");
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-variant", "EX");
    navigate("Aircraft");
    expect(variants().getAllByRole("button").map((button) => button.getAttribute("aria-label"))).toEqual(family.variants.map((variant) => `${variant.name} ${variant.nickname}`));
    navigate("Budget & receipts");
    expect(recordSelector()).toHaveValue("F015EX");
    expect(query().get("variant")).toBe("EX");
    expect(query().get("record")).toBe("F015EX");
    fireEvent.click(funding().getByRole("button", { name: "Open budget receipt" }));
    expect(openPanel).toHaveBeenLastCalledWith("4a9ae7cc78dcf0ba", expect.objectContaining({ value: 3_014_394, fy: 2026, entity: "F015EX", measure: "request", basis: "toa" }));
  });

  it("switches a legacy variant directly to an available budget record", async () => {
    await mount("#funding");
    chooseVariant("C");
    expect(query().get("purpose")).toBe("develop");
    expect(selectedRecord()).toHaveTextContent("0207134F");
    navigate("Aircraft");
    expect(document.querySelector('[data-family-topic="airframe"]')).not.toHaveTextContent("not mapped");
  });

  it("restores a variant-only link with useful funding and follows the selected topic's exact record", async () => {
    await mount("?variant=C#funding");
    expect(selectedRecord()).toHaveTextContent("PE 0207134F");
    chooseVariant("E");
    navigate("Aircraft");
    fireEvent.click(screen.getByRole("button", { name: /03\s*Electronic systems/ }));
    navigate("Budget & receipts");
    chooseRecord("F15EWS");
    chooseVariant("EX");
    navigate("Aircraft");
    fireEvent.click(screen.getByText("Budget connection"));
    fireEvent.click(screen.getByRole("link", { name: "Follow its funding record" }));
    expect(query().get("record")).toBe("0207171F");
    expect(selectedRecord()).toHaveTextContent("PE 0207171F");
  });

  it("changes budget record, fiscal year and model topic together with the shareable URL", async () => {
    await mount("#funding");
    chooseRecord("0207146F");
    expect(query().get("purpose")).toBe("develop");
    expect(query().get("record")).toBe("0207146F");
    expect(selectedRecord().querySelector('[data-fact-id="a1e559f43a1650d7"]')).not.toBeNull();
    selectYear(2024);
    expect(query().get("fy")).toBe("2024");
    expect(selectedRecord().querySelector('[data-fact-id="14806401bc7e4a7f"]')).not.toBeNull();
    navigate("Aircraft");
    fireEvent.click(screen.getByRole("button", { name: "Inspect cockpit on model" }));
    expect(query().get("topic")).toBe("cockpit");
    expect(query().get("record")).toBe("0207134F");
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-topic", "cockpit");
    fireEvent.click(screen.getByText("Budget connection"));
    fireEvent.click(screen.getByRole("button", { name: "Read source passage" }));
    expect(openPanel).toHaveBeenLastCalledWith("0026c924483c6624");
    navigate("Budget & receipts");
    expect(selectedRecord().querySelector('[data-fact-id="e58bcd5e7566188d"]')).not.toBeNull();
  });


  it("shows every linked budget record together and uses one year control for the amount and its receipt", async () => {
    await mount("#funding");
    expect(budgetRecords().getAllByRole("option").map((option) => option.getAttribute("value"))).toEqual(["F015EX", "0207146F", "0207134F", "0207171F"]);
    expect(recordSelector()).toHaveValue("F015EX");
    expect(within(budgetRecords().getByRole("group", { name: "Aircraft procurement" })).getByRole("option", { name: "Aircraft & support" })).toHaveValue("F015EX");
    const development = within(budgetRecords().getByRole("group", { name: "Research & development" }));
    expect(development.getAllByRole("option").map((option) => option.textContent)).toEqual(["F-15EX development", "Fleet software", "Electronic protection"]);
    expect(budgetRecords().queryByRole("group", { name: "Modification procurement" })).toBeNull();
    expect(funding().getAllByRole("combobox")).toEqual([recordSelector()]);
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-variant", "EX");
    expect(funding().queryByRole("combobox", { name: "Fiscal year" })).toBeNull();
    expect(funding().queryByRole("button", { name: /^(Develop|Buy|Upgrade)$/ })).toBeNull();
    expect(funding().getAllByRole("group", { name: "Fiscal year" })).toHaveLength(1);

    selectYear(2024);
    const selectedYear = fiscalYears().getByRole("button", { name: /^Select FY2024,/ });
    expect(selectedYear).toHaveAttribute("aria-pressed", "true");
    const record = family.records.find((item) => item.slug === "F015EX")!;
    const fact = getRecordFact(record, 2024)!;
    expect(selectedYear).toHaveAttribute("data-chart-fact-id", fact.factId);
    const headline = selectedRecord().querySelector(`[data-amount][data-fact-id="${fact.factId}"]`);
    expect(headline).toHaveAttribute("data-fy", "2024");
    expect(headline).toHaveAttribute("data-measure", fact.measure);
    fireEvent.click(funding().getByRole("button", { name: "Open budget receipt" }));
    expect(openPanel).toHaveBeenLastCalledWith(fact.factId, expect.objectContaining({ fy: 2024, measure: fact.measure, value: fact.amountThousands, entity: "F015EX" }));
    fireEvent.click(funding().getByText("Source data"));
    const annualTable = funding().getByRole("table", { name: /Cited fiscal figures/ });
    expect(annualTable.querySelector(`[data-fact-id="${fact.factId}"]`)).not.toBeNull();
    expect(query().get("fy")).toBe("2024");
  });

  it("marks only the cited comparison years and keeps the funding statement before its annual context", async () => {
    await mount("#funding");
    const yearGroup = screen.getByRole("group", { name: "Fiscal year" });
    const comparisonYears = () => Array.from(yearGroup.querySelectorAll('[data-comparison-year="true"]')).map((column) => column.querySelector('button[aria-label^="Select FY"]')!.getAttribute("aria-label")!.match(/^Select FY(\d{4}),/)![1]);
    expect(comparisonYears()).toEqual(["2025", "2026"]);
    const from = fiscalYears().getByRole("button", { name: /^Select FY2025,/ }).parentElement!;
    const to = fiscalYears().getByRole("button", { name: /^Select FY2026,/ }).parentElement!;
    expect(from).toHaveAttribute("data-comparison-from", "true");
    expect(to).toHaveAttribute("data-comparison-from", "false");
    const amountHeading = within(selectedRecord()).getByRole("heading", { name: "FY2026 budget request" });
    expect(amountHeading.compareDocumentPosition(yearGroup) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    selectYear(2024);
    expect(comparisonYears()).toEqual([]);
    expect(yearGroup.querySelector('[data-comparison-from="true"]')).toBeNull();
  });

  it("keeps the cited comparison pair when a later unreported year is also in the chart", async () => {
    const extendedCoverage: F15FamilyPayload = { ...family, years: [...family.years, 2027] };
    await mount("?variant=EX&purpose=buy&record=F015EX&fy=2026#funding", extendedCoverage);
    const yearGroup = screen.getByRole("group", { name: "Fiscal year" });
    const from = fiscalYears().getByRole("button", { name: /^Select FY2025,/ }).parentElement!;
    const to = fiscalYears().getByRole("button", { name: /^Select FY2026,/ }).parentElement!;
    const later = fiscalYears().getByRole("button", { name: "Select FY2027, no figure in this collection" }).parentElement!;
    expect(from).toHaveAttribute("data-comparison-year", "true");
    expect(from).toHaveAttribute("data-comparison-from", "true");
    expect(to).toHaveAttribute("data-comparison-year", "true");
    expect(to).toHaveAttribute("data-comparison-from", "false");
    expect(later).toHaveAttribute("data-comparison-year", "false");
    expect(later).toHaveAttribute("data-comparison-from", "false");
    expect(yearGroup.querySelectorAll('[data-comparison-year="true"]')).toHaveLength(2);
    const record = extendedCoverage.records.find((item) => item.slug === "F015EX")!;
    const comparison = record.change!;
    expect(from.querySelector("[data-chart-fact-id]")).toHaveAttribute("data-chart-fact-id", comparison.fromFactId);
    expect(to.querySelector("[data-chart-fact-id]")).toHaveAttribute("data-chart-fact-id", comparison.toFactId);
    expect(selectedRecord().querySelector(`[data-amount][data-fact-id="${comparison.factId}"]`)).toBeVisible();
  });

  it.each([
    ["F015EX", "billions", 1_000_000],
    ["0207146F", "millions", 1_000],
  ] as const)("plots every annual amount for %s against the same zero-based %s scale", async (slug, units, unitThousands) => {
    await mount("#funding");
    chooseRecord(slug);
    const record = family.records.find((item) => item.slug === slug)!;
    const years = screen.getByRole("group", { name: "Fiscal year" });
    const plot = years.closest("figure")!;
    expect(plot).toHaveTextContent(`USD ${units}`);
    const ticks = Array.from(plot.querySelectorAll<HTMLElement>('[style*="--tick-position"]'));
    const zero = ticks.find((tick) => Number(tick.textContent) === 0)!;
    expect(zero).toBeDefined();
    expect(Number(zero.style.getPropertyValue("--tick-position"))).toBe(1);
    const labeledTick = ticks.find((tick) => Number(tick.textContent) > 0)!;
    const axisCeiling = Number(labeledTick.textContent) * unitThousands /
      (1 - Number(labeledTick.style.getPropertyValue("--tick-position")));
    expect(axisCeiling).toBeGreaterThan(0);
    const buttons = within(years).getAllByRole("button");
    const plottedFacts = buttons.flatMap((button) => {
      const factId = button.getAttribute("data-chart-fact-id");
      return factId ? [record.facts.find((item) => item.factId === factId)!] : [];
    });
    expect(plottedFacts.length).toBeGreaterThan(1);
    for (const button of buttons) {
      const factId = button.getAttribute("data-chart-fact-id");
      const bar = button.querySelector<HTMLElement>("[data-status]");
      if (!factId) {
        expect(bar).toBeNull();
        continue;
      }
      const fact = record.facts.find((item) => item.factId === factId)!;
      expect(bar).not.toBeNull();
      const height = parseFloat(bar!.style.height);
      expect(height).toBeGreaterThanOrEqual(0);
      expect(height).toBeLessThanOrEqual(100);
      // Reading the axis and bar independently catches per-year scaling or a
      // nonzero baseline that would exaggerate differences between years.
      expect(height / 100 * axisCeiling).toBeCloseTo(Math.abs(fact.amountThousands), 5);
      expect(bar).toHaveAttribute("data-status", fact.measure);
    }
  });

  it("traces the selected program and year to the official workbook and exact receipt, with reachable funding definitions", async () => {
    await mount("#funding");
    const procurement = family.records.find((item) => item.slug === "F015EX")!;
    const sourceUrls = [...new Set(procurement.componentRows.filter((row) => row.fy === 2026).map((row) => row.source.officialUrl).filter(Boolean))];
    expect(sourceUrls).toHaveLength(1);
    let sourceTrail = screen.getByRole("region", { name: "Budget source trail" });
    expect(within(sourceTrail).getByRole("link", { name: "Budget line F015EX" })).toHaveAttribute("href", "/program/F015EX");
    expect(within(sourceTrail).getByRole("heading", { name: "FY2026 budget request" })).toBeVisible();
    expect(sourceTrail).toHaveTextContent("Total obligation authority · Source edition: President’s Budget 2026.");
    expect(funding().getByRole("link", { name: "Official document" })).not.toBeVisible();
    const calculation = funding().getByText("FY2026 request · Calculated from cited source rows");
    expect(calculation).not.toBeVisible();
    fireEvent.click(funding().getByText("Source data"));
    expect(calculation).toBeVisible();
    expect(funding().getByRole("link", { name: "Official document" })).toBeVisible();
    expect(funding().getByRole("link", { name: "Official document" })).toHaveAttribute("href", sourceUrls[0]);
    fireEvent.click(funding().getByText("Source data"));
    fireEvent.click(funding().getByRole("button", { name: "Open budget receipt" }));
    expect(openPanel).toHaveBeenLastCalledWith("4a9ae7cc78dcf0ba", expect.objectContaining({ entity: "F015EX", fy: 2026, measure: "request", value: 3_014_394 }));

    chooseRecord("0207146F");
    selectYear(2024);
    const development = family.records.find((item) => item.slug === "0207146F")!;
    const fact = getRecordFact(development, 2024)!;
    sourceTrail = screen.getByRole("region", { name: "Budget source trail" });
    expect(within(sourceTrail).getByRole("link", { name: "Program element 0207146F" })).toHaveAttribute("href", "/program/0207146F");
    expect(within(sourceTrail).getByRole("heading", { name: "FY2024 reported actuals" })).toBeVisible();
    expect(sourceTrail).toHaveTextContent("Total obligation authority · Source edition: President’s Budget 2026.");
    expect(funding().getByRole("link", { name: "Official document" })).not.toBeVisible();
    fireEvent.click(funding().getByRole("button", { name: "Open budget receipt" }));
    expect(openPanel).toHaveBeenLastCalledWith("14806401bc7e4a7f", expect.objectContaining({ entity: "0207146F", fy: 2024, measure: fact.measure, value: fact.amountThousands }));

    const definitions = funding().getByText(/Research & development funds design, software and testing/);
    expect(definitions).not.toBeVisible();
    fireEvent.click(funding().getByText("Source data"));
    expect(definitions).toBeVisible();
    expect(funding().getByRole("link", { name: "Official document" })).toBeVisible();
    expect(funding().getByRole("link", { name: "Official document" })).toHaveAttribute("href", fact.source.officialUrl);
    expect(funding().getByText("FY2024 actuals · Traced to its source location")).toBeVisible();
    expect(definitions).toHaveTextContent("Procurement funds aircraft, equipment and modifications to the existing fleet.");
    expect(definitions).toHaveTextContent("shared records do not allocate a cost to each variant");
    const trail = within(funding().getByRole("navigation", { name: "Evidence trail" }));
    fireEvent.click(trail.getByRole("button", { name: `Source #${fact.publicId}` }));
    expect(openPanel).toHaveBeenLastCalledWith(fact.factId, expect.objectContaining({ entity: "0207146F", fy: 2024, measure: fact.measure, value: fact.amountThousands }));
    fireEvent.click(funding().getByRole("button", { name: "Inspect source context" }));
    expect(funding().getByRole("heading", { name: fact.source.title })).toBeVisible();
    expect(funding().getByRole("button", { name: "Hide source context" })).toHaveAttribute("aria-expanded", "true");
  });

  it("keeps missing EPAWSS coverage distinct from zero and opens its older year with the matching source", async () => {
    await mount("#funding");
    chooseRecord("0207171F");
    expect(query().get("record")).toBe("0207171F");
    expect(fiscalYears().getByRole("button", { name: "Select FY2026, no figure in this collection" })).toHaveAttribute("aria-pressed", "true");
    expect(within(selectedRecord()).getByRole("heading", { name: "No matching TOA figure for FY2026." })).toBeVisible();
    expect(funding().queryByRole("button", { name: "Open budget receipt" })).toBeNull();
    expect(selectedRecord().querySelector('[data-amount][data-fy="2026"]')).toBeNull();
    selectYear(2024);
    const record = family.records.find((item) => item.slug === "0207171F")!;
    const fact = getRecordFact(record, 2024)!;
    expect(within(selectedRecord()).queryByText(/No matching TOA figure/)).toBeNull();
    expect(selectedRecord().querySelector(`[data-amount][data-fact-id="${fact.factId}"]`)).toHaveAttribute("data-fy", "2024");
    fireEvent.click(funding().getByRole("button", { name: "Open budget receipt" }));
    expect(openPanel).toHaveBeenLastCalledWith(fact.factId, expect.objectContaining({ fy: 2024, value: fact.amountThousands, entity: "0207171F" }));
    selectYear(2026);
    expect(within(selectedRecord()).getByRole("heading", { name: "No matching TOA figure for FY2026." })).toBeVisible();
    expect(selectedRecord().querySelector('[data-amount][data-fy="2026"]')).toBeNull();
    expect(funding().queryByRole("button", { name: "Open budget receipt" })).toBeNull();
    expect(funding().queryByRole("region", { name: "Budget source trail" })).toBeNull();
    const absentYear = fiscalYears().getByRole("button", { name: "Select FY2026, no figure in this collection" });
    expect(absentYear).toHaveAttribute("aria-pressed", "true");
    expect(absentYear).not.toHaveAttribute("data-chart-fact-id");
    expect(absentYear.querySelector("[data-status]")).toBeNull();
  });

  it("switches between development and modification records without hiding either category", async () => {
    await mount("?variant=E&purpose=develop&record=0207134F&fy=2026#funding");
    const expectedRecords = [
      ["Fleet software", "0207134F", "develop"],
      ["Electronic protection", "0207171F", "develop"],
      ["Aircraft modifications", "F01500", "upgrade"],
      ["F-15E protection kits", "F15EWS", "upgrade"],
    ];
    expect(budgetRecords().getAllByRole("option")).toHaveLength(expectedRecords.length);
    for (const [label, slug, purpose] of expectedRecords) {
      chooseRecord(slug);
      expect(query().get("record")).toBe(slug);
      expect(query().get("purpose")).toBe(purpose);
      expect(selectedRecord()).toHaveTextContent(slug);
      expect(budgetRecords().getAllByRole("option")).toHaveLength(expectedRecords.length);
      expect(recordSelector()).toHaveValue(slug);
      expect(budgetRecords().getByRole("option", { name: label })).toHaveProperty("selected", true);
    }
    expect(selectedRecord().querySelector('[data-amount][data-fact-id="7e2ce3f9955ed215"]')).not.toBeNull();
    expect(within(budgetRecords().getByRole("group", { name: "Modification procurement" })).getAllByRole("option").map((option) => option.getAttribute("value"))).toEqual(["F01500", "F15EWS"]);
    expect(within(budgetRecords().getByRole("group", { name: "Research & development" })).getAllByRole("option").map((option) => option.getAttribute("value"))).toEqual(["0207134F", "0207171F"]);
  });

  it("sanitizes invalid URL choices and shares the resolved compatible record", async () => {
    await mount("?variant=bad&purpose=anything&fy=9999&topic=invalid&compare=EX&record=F15EWS#funding");
    expect(fiscalYears().getByRole("button", { name: /^Select FY2026,/ })).toHaveAttribute("aria-pressed", "true");
    expect(selectedRecord()).toHaveTextContent("BLI F015EX");
    fireEvent.click(screen.getByRole("button", { name: "Share view" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const shared = new URL(writeText.mock.calls[0][0]);
    expect(shared.searchParams.get("record")).toBe("F015EX");
    expect(shared.searchParams.get("variant")).toBe("EX");
    expect(shared.searchParams.get("purpose")).toBe("buy");
    expect(shared.searchParams.get("fy")).toBe("2026");
    expect(shared.searchParams.has("compare")).toBe(false);
    expect(shared.hash).toBe("#funding");
    navigate("Aircraft");
    expect(screen.getByTestId("family-model")).toBeVisible();
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-variant", "EX");
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-topic", "airframe");
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-compare", "");
  });

  it("exposes F-15E EPAWSS procurement only for E, with its own cited figure", async () => {
    await mount("?variant=E&purpose=upgrade&fy=2026&record=F15EWS#funding");
    expect(selectedRecord()).toHaveTextContent("BLI F15EWS");
    expect(selectedRecord().querySelector('[data-fact-id="7e2ce3f9955ed215"]')).not.toBeNull();
    chooseVariant("EX");
    expect(query().get("purpose")).toBe("develop");
    expect(selectedRecord()).toHaveTextContent("PE 0207146F");
    expect(document.querySelectorAll("#funding [data-fact-id='7e2ce3f9955ed215']")).toHaveLength(0);
  });

  it("keeps shared records identified in comparisons and sends both variants to the aligned model", async () => {
    await mount("?variant=C&purpose=develop&fy=2026&record=0207134F&compare=D#compare");
    const comparison = screen.getByRole("region", { name: "Compare aircraft" });
    expect(within(comparison).getAllByText("PE 0207134F · Shared across variants")).toHaveLength(2);
    expect(within(comparison).getByText(/same funding, counted once/)).toBeVisible();
    expect(comparison.querySelectorAll('[data-fact-id="44f9ccc1f1518032"][data-amount]')).toHaveLength(2);
    expect(comparison).not.toHaveTextContent("Combined total");
    fireEvent.click(screen.getByRole("link", { name: "Inspect the aligned models" }));
    expect(screen.getByRole("region", { name: "Aircraft inspection" })).toBeVisible();
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-variant", "C");
    expect(screen.getByTestId("family-model")).toHaveAttribute("data-compare", "D");
  });

  it("makes keyboard variant navigation change the selection and focus", async () => {
    await mount("#funding");
    navigate("Aircraft");
    const ex = variants().getByRole("button", { name: "F-15EX Eagle II" });
    fireEvent.keyDown(ex, { key: "Home" });
    expect(variants().getByRole("button", { name: "F-15A Eagle" })).toHaveFocus();
    expect(query().get("variant")).toBe("A");
    fireEvent.keyDown(variants().getByRole("button", { name: "F-15A Eagle" }), { key: "ArrowRight" });
    expect(variants().getByRole("button", { name: "F-15B Eagle" })).toHaveFocus();
    expect(query().get("variant")).toBe("B");
  });
});

describe("F-15 research tray preserves provenance", () => {
  it("saves and restores receipts, copies full fiscal context, and removes the saved item", async () => {
    await mount("#funding");
    fireEvent.click(screen.getByRole("button", { name: "Save receipt" }));
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)!)).toEqual(["4a9ae7cc78dcf0ba"]);
    openResearchTray();
    expect(window.location.hash).toBe("#research");
    fireEvent.click(screen.getByRole("button", { name: "Copy all citations" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const copied = writeText.mock.calls[0][0];
    expect(copied).toContain("F015EX");
    expect(copied).toContain("FY2026");
    expect(copied).toMatch(/request/i);
    expect(copied).toMatch(/TOA|total obligation authority/i);
    expect(copied).toContain("PB2026");
    expect(copied).toContain("https://fiscalreceipts.com/fact/4a9ae7cc");
    expect(copied).toContain("https://fiscalreceipts.com/fact/03407158");
    cleanup();
    await mount("#research");
    expect(screen.getByRole("button", { name: "Remove saved receipt 4a9ae7cc" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Remove saved receipt 4a9ae7cc" }));
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)!)).toEqual([]);
    expect(screen.getByRole("button", { name: "Copy all citations" })).toBeDisabled();
  });

  it("falls back to copyable text when the clipboard is blocked", async () => {
    writeText.mockRejectedValue(new Error("Clipboard unavailable"));
    await mount();
    fireEvent.click(screen.getByRole("button", { name: "Share view" }));
    const fallback = await screen.findByRole("textbox", { name: "Copy this text" });
    expect((fallback as HTMLTextAreaElement).value).toContain("variant=EX");
    expect(fallback).toHaveAttribute("readonly");
    expect(screen.getByRole("status", { name: "Research feedback" })).toHaveTextContent("Copy access is unavailable");
  });

  it("discards unrecognized saved fact IDs rather than rendering arbitrary stored content", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(["untrusted", "4a9ae7cc78dcf0ba", "4a9ae7cc78dcf0ba", 123]));
    await mount("#research");
    expect(screen.getAllByRole("button", { name: "Remove saved receipt 4a9ae7cc" })).toHaveLength(1);
    expect(document.querySelector('[data-workspace-section="research"]')).not.toHaveTextContent("untrusted");
  });
});

describe("F-15 focused workspace navigation", () => {
  it("keeps one persistent Research tray link in all six workspaces and preserves its focus on activation", async () => {
    await mount();
    const navigation = within(screen.getByRole("navigation", { name: "F-15 family sections" }));
    const links = navigation.getAllByRole("link");
    expect(links).toHaveLength(6);
    const research = navigation.getByRole("link", { name: "Research tray" });
    expect(links[5]).toBe(research);
    expect(research).toHaveAttribute("href", "#research");

    for (const label of ["Aircraft", "Budget & receipts", "Countries & orders", "Family history", "Compare aircraft"]) {
      navigate(label);
      expect(navigation.getByRole("link", { name: "Research tray" })).toBe(research);
      expect(screen.getAllByRole("link", { name: "Research tray" })).toEqual([research]);
      expect(research).toBeVisible();
      expect(research).not.toHaveAttribute("aria-current");
      research.focus();
      fireEvent.click(research);
      expect(window.location.hash).toBe("#research");
      expect(navigation.getByRole("link", { name: "Research tray" })).toBe(research);
      expect(research).toHaveAttribute("aria-current", "page");
      expect(research).toHaveFocus();
      expect(screen.getByRole("button", { name: "Copy all citations" })).toBeVisible();
    }
  }, 20_000); // walks all six workspaces (~3.3 s alone); the 5 s default flaked under full-suite load three times on 2026-09-25/26

  it("lets modified workspace links keep their browser behavior without changing the current view", async () => {
    await mount("?variant=EX&purpose=buy&record=F015EX#inspect");
    const navigation = within(screen.getByRole("navigation", { name: "F-15 family sections" }));
    const pushState = vi.spyOn(window.history, "pushState");
    const location = window.location.href;
    for (const modifier of ["metaKey", "ctrlKey", "shiftKey", "altKey"]) {
      let intercepted = true;
      document.addEventListener("click", (event) => {
        intercepted = event.defaultPrevented;
        event.preventDefault(); // Keep jsdom from performing the browser's default link navigation.
      }, { once: true });
      fireEvent.click(navigation.getByRole("link", { name: "Budget & receipts" }), { [modifier]: true });
      expect(intercepted).toBe(false);
      expect(window.location.href).toBe(location);
      expect(navigation.getByRole("link", { name: "Aircraft" })).toHaveAttribute("aria-current", "page");
    }
    expect(pushState).not.toHaveBeenCalled();
    await act(async () => { await new Promise<void>((resolve) => requestAnimationFrame(() => resolve())); });
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("follows workspace links inside the aircraft content while preserving the selected funding record", async () => {
    await mount("?variant=E&purpose=upgrade&record=F15EWS&fy=2024#inspect");
    fireEvent.click(screen.getByRole("link", { name: /Next, follow the public money/ }));
    expect(window.location.hash).toBe("#funding");
    expect(query().get("variant")).toBe("E");
    expect(query().get("record")).toBe("F15EWS");
    expect(query().get("fy")).toBe("2024");
    expect(selectedRecord()).toHaveTextContent("F15EWS");
    await waitFor(() => expect(scrollTo).toHaveBeenCalledExactlyOnceWith({ top: 0, behavior: "auto" }));
    scrollTo.mockClear();
    navigate("Family history");
    expect(window.location.hash).toBe("#history");
    await waitFor(() => expect(scrollTo).toHaveBeenCalledExactlyOnceWith({ top: 0, behavior: "auto" }));
    expect(query().get("record")).toBe("F15EWS");
    expect(query().get("fy")).toBe("2024");
  });

  it("keeps keyboard focus visible when next-chapter and Inspect aircraft links hide their origin", async () => {
    await mount("?variant=E&purpose=upgrade&record=F15EWS&fy=2024#inspect");
    const navigation = within(screen.getByRole("navigation", { name: "F-15 family sections" }));
    const nextChapter = screen.getByRole("link", { name: /Next, follow the public money/ });
    nextChapter.focus();
    fireEvent.click(nextChapter, { detail: 0 });
    await waitFor(() => expect(navigation.getByRole("link", { name: "Budget & receipts" })).toHaveFocus());
    expect(nextChapter).not.toBeVisible();

    const inspectAircraft = within(selectedRecord()).getByRole("link", { name: /Inspect aircraft/ });
    inspectAircraft.focus();
    fireEvent.click(inspectAircraft, { detail: 0 });
    await waitFor(() => expect(navigation.getByRole("link", { name: "Aircraft" })).toHaveFocus());
    expect(inspectAircraft).not.toBeVisible();
    expect(screen.getByRole("group", { name: "Aircraft variant" })).toBeVisible();
    expect(query().get("record")).toBe("F15EWS");
    expect(query().get("fy")).toBe("2024");
  });

  it("opens one workspace at a time, shares its location, and restores the receipt after browser back", async () => {
    await mount();
    const navigation = within(screen.getByRole("navigation", { name: "F-15 family sections" }));
    expect(navigation.getByRole("link", { name: "Aircraft" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("region", { name: "Aircraft inspection" })).toBeVisible();
    expect(screen.queryByRole("article", { name: "Selected funding record" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Copy all citations" })).toBeNull();
    expect(screen.getByRole("group", { name: "Aircraft variant" })).toBeVisible();
    expect(variants().getByRole("button", { name: "F-15EX Eagle II" })).toHaveAttribute("aria-pressed", "true");
    navigate("Budget & receipts");
    expect(window.location.hash).toBe("#funding");
    expect(navigation.getByRole("link", { name: "Budget & receipts" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("combobox", { name: "Selected aircraft" })).toBeNull();
    expect(screen.queryByRole("group", { name: "Aircraft variant" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Aircraft inspection" })).toBeNull();
    chooseRecord("0207146F");
    selectYear(2024);
    navigate("Family history");
    expect(window.location.hash).toBe("#history");
    expect(screen.getByRole("region", { name: "Five moments in the Eagle’s evolution." })).toBeVisible();
    expect(screen.queryByRole("article", { name: "Selected funding record" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Share view" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const shared = new URL(writeText.mock.calls[0][0]);
    expect(shared.hash).toBe("#history");
    expect(shared.searchParams.get("record")).toBe("0207146F");
    expect(shared.searchParams.get("fy")).toBe("2024");

    act(() => window.history.back());
    await waitFor(() => expect(navigation.getByRole("link", { name: "Budget & receipts" })).toHaveAttribute("aria-current", "page"));
    expect(window.location.hash).toBe("#funding");
    expect(fiscalYears().getByRole("button", { name: /^Select FY2024,/ })).toHaveAttribute("aria-pressed", "true");
    expect(selectedRecord().querySelector('[data-amount][data-fact-id="14806401bc7e4a7f"]')).not.toBeNull();
    expect(screen.queryByRole("region", { name: "Five moments in the Eagle’s evolution." })).toBeNull();

    cleanup();
    await mount(`${shared.search}${shared.hash}`);
    expect(screen.getByRole("region", { name: "Five moments in the Eagle’s evolution." })).toBeVisible();
    navigate("Budget & receipts");
    expect(selectedRecord().querySelector('[data-amount][data-fact-id="14806401bc7e4a7f"]')).not.toBeNull();
  });

  it("falls back to aircraft inspection for an unknown workspace without exposing hidden controls", async () => {
    await mount("?variant=E#unknown-workspace");
    expect(screen.getByRole("region", { name: "Aircraft inspection" })).toBeVisible();
    expect(variants().getByRole("button", { name: "F-15E Strike Eagle" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("combobox", { name: "Funding record" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Copy all citations" })).toBeNull();
    openResearchTray();
    expect(window.location.hash).toBe("#research");
    expect(screen.getByRole("button", { name: "Copy all citations" })).toBeDisabled();
    expect(screen.queryByRole("region", { name: "Aircraft inspection" })).toBeNull();
  });
});

describe("F-15 initial payload", () => {
  it("keeps the family payload under 500 kB raw and 60 kB compressed", () => {
    const bytes = new TextEncoder().encode(JSON.stringify(family)).byteLength;
    const compressed = gzipSync(JSON.stringify(family)).byteLength;
    expect(bytes).toBeLessThan(500_000);
    expect(compressed).toBeLessThan(60_000);
  });
});

describe("F-15 share and storage boundaries", () => {
  it("round-trips every valid view field without losing a comparison or source record", () => {
    const view: FamilyView = { variant: "E", purpose: "upgrade", record: "F15EWS", fy: 2024, compare: "EX", topic: "sensors" };
    expect(parseFamilyView(`?${serializeFamilyView(view)}`, family.years)).toEqual(view);
    expect(serializeFamilyView({ ...view, compare: "E" })).not.toContain("compare=");
  });

  it("rejects arbitrary URL values, unsupported years and self-comparisons", () => {
    const parsed = parseFamilyView("?variant=E&compare=E&purpose=__proto__&record=https://example.com/&fy=NaN&topic=constructor", family.years);
    expect(parsed).toEqual({ variant: "E", compare: null, purpose: "buy", record: "F015EX", fy: 2026, topic: "airframe" });
    expect(parseFamilyView("?variant=EX&fy=-1", family.years).fy).toBe(2026);
  });

  it("caps known receipt IDs, removes duplicates and rejects malformed or object-shaped storage", () => {
    const ids = [...new Set(family.records.flatMap((record) => record.facts.map((fact) => fact.factId)))];
    const allowed = new Set(ids);
    expect(readSavedFactIds(null, allowed)).toEqual([]);
    expect(readSavedFactIds("{bad-json", allowed)).toEqual([]);
    expect(readSavedFactIds(JSON.stringify({ fact: ids[0] }), allowed)).toEqual([]);
    expect(readSavedFactIds(JSON.stringify([ids[0], ids[0], "unknown", false, ids[1]]), allowed)).toEqual(ids.slice(0, 2));
    expect(readSavedFactIds(JSON.stringify(ids), allowed)).toEqual(ids.slice(0, 12));
  });
});
