import React, { useContext } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Cite, CitationPanelContext } from "@/components/cite";
import { CitationPanelProvider } from "@/components/citation-panel/panel";
import { resolveCitationFromShards } from "@/lib/cite-shards";
import type { Citation, CitationsMap, DerivedCitation } from "@/lib/data";
import { trackReaderEvent } from "@/lib/reader-events";

vi.mock("@/lib/cite-shards", () => ({ resolveCitationFromShards: vi.fn() }));
vi.mock("@/lib/reader-events", () => ({ trackReaderEvent: vi.fn() }));

const TOTAL_ID = "4a9ae7cc78dcf0ba";
const INPUT_ID = "03407158217dec76";
const TOTAL: DerivedCitation = {
  kind: "derived",
  formula: "sum(cited inputs)",
  inputs: JSON.stringify([INPUT_ID]),
  recorded_value: "3014394",
  units: "USD thousands",
  official_url: null,
  retrieved_at: null,
  query_body: null,
  amount_text: null,
  amount_thousands: null,
  bottom_pt: null,
  cells: null,
  hosted_pdf_url: null,
  page_height: null,
  page_number: null,
  page_width: null,
  resolution: null,
  sha256: null,
  sheet: null,
  top_pt: null,
  x0: null,
  x1: null,
  xml_path: null,
};
const INPUT: DerivedCitation = {
  ...TOTAL,
  formula: "source input",
  inputs: "[]",
  recorded_value: "2480818",
};
const CITATIONS: CitationsMap = { [TOTAL_ID]: TOTAL, [INPUT_ID]: INPUT };

function Openers({ showChart = true }: { showChart?: boolean }) {
  const { openPanel } = useContext(CitationPanelContext);
  return (
    <>
      {showChart && (
        <Cite
          value={3014394}
          units="USD thousands"
          dataset="budget_lines"
          factId={TOTAL_ID}
          chip={false}
          fy={2026}
          measure="request"
          basis="toa"
          entity="F015EX"
        />
      )}
      <button onClick={() => openPanel(TOTAL_ID)}>Open budget receipt</button>
    </>
  );
}

function mount(citations = CITATIONS, showChart = true) {
  return render(
    <CitationPanelProvider citations={citations}>
      <Openers showChart={showChart} />
    </CitationPanelProvider>,
  );
}

async function openFrom(kind: "chart" | "receipt") {
  const opener = screen.getByRole("button", {
    name: kind === "chart" ? "$3.01B — click to view citation" : "Open budget receipt",
  });
  opener.focus();
  expect(opener).toHaveFocus();
  if (kind === "chart") fireEvent.keyDown(opener, { key: "Enter" });
  else fireEvent.click(opener);
  const dialog = await screen.findByRole("dialog", { name: "Citation details" });
  await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
  return opener;
}

async function closeWith(method: "Escape" | "close") {
  if (method === "Escape") fireEvent.keyDown(document.activeElement!, { key: "Escape" });
  else fireEvent.click(screen.getByRole("button", { name: "Close citation panel" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  // Radix restores focus in its deferred onCloseAutoFocus callback.
  await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });
}

beforeEach(() => {
  vi.mocked(trackReaderEvent).mockReset();
  window.history.replaceState({}, "", "/");
  vi.mocked(resolveCitationFromShards).mockReset();
  vi.stubGlobal("fetch", vi.fn(async (url: string) => ({
    ok: url === "/config.json",
    status: url === "/config.json" ? 200 : 404,
    json: async () => ({ assetBaseUrl: "/assets" }),
  })));
});

afterEach(async () => {
  cleanup();
  await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("citation panel returns focus to its outside opener", () => {
  it("tracks one receipt open and only successful citation copies", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    mount({ ...CITATIONS, [TOTAL_ID]: { ...TOTAL, official_url: "https://comptroller.defense.gov/receipt" } });
    await openFrom("chart");
    expect(vi.mocked(trackReaderEvent).mock.calls.filter(([event]) => event === "receipt_opened")).toHaveLength(1);
    expect(trackReaderEvent).toHaveBeenCalledWith("receipt_opened", expect.objectContaining({ program: "F015EX", factId: TOTAL_ID, fiscalYear: 2026, measure: "request" }));
    fireEvent.click(screen.getByTestId("official-source"));
    expect(vi.mocked(trackReaderEvent).mock.calls.filter(([event]) => event === "official_source_opened")).toHaveLength(1);
    expect(trackReaderEvent).toHaveBeenCalledWith("official_source_opened", expect.objectContaining({ program: "F015EX" }));
    fireEvent.click(screen.getByTestId("copy-footnote"));
    await waitFor(() => expect(trackReaderEvent).toHaveBeenCalledWith("citation_copied", expect.objectContaining({ program: "F015EX", factId: TOTAL_ID, format: "chicago" })));
    writeText.mockRejectedValueOnce(new Error("blocked"));
    fireEvent.click(screen.getByTestId("copy-footnote"));
    await screen.findByText("Copy failed");
    expect(vi.mocked(trackReaderEvent).mock.calls.filter(([event]) => event === "citation_copied")).toHaveLength(1);
  });
  it.each([
    ["chart", "Escape"],
    ["chart", "close"],
    ["receipt", "Escape"],
    ["receipt", "close"],
  ] as const)("returns to the %s control after %s", async (kind, method) => {
    mount();
    const opener = await openFrom(kind);
    await closeWith(method);
    expect(opener).toHaveFocus();
  });

  it.each(["Escape", "close"] as const)("preserves the opener through input drilldown and Back before %s", async (method) => {
    mount();
    const opener = await openFrom("chart");
    const input = screen.getByTestId("derived-input-chip");
    input.focus();
    fireEvent.click(input);
    expect(await screen.findByText("source input")).toBeInTheDocument();
    const back = screen.getByRole("button", { name: "Back to previous citation" });
    back.focus();
    fireEvent.click(back);
    expect(await screen.findByText("sum(cited inputs)")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back to previous citation" })).not.toBeInTheDocument();
    await closeWith(method);
    expect(opener).toHaveFocus();
  });

  it("captures a fresh opener on a later opening", async () => {
    mount();
    const first = await openFrom("chart");
    await closeWith("Escape");
    expect(first).toHaveFocus();
    const second = await openFrom("receipt");
    await closeWith("close");
    expect(second).toHaveFocus();
  });

  it("restores focus when closed during loading and ignores the late result", async () => {
    let resolve!: (citation: Citation | null) => void;
    vi.mocked(resolveCitationFromShards).mockReturnValue(new Promise((done) => { resolve = done; }));
    mount({});
    const opener = await openFrom("receipt");
    expect(screen.getByText(/loading citation/i)).toBeInTheDocument();
    await closeWith("Escape");
    expect(opener).toHaveFocus();
    await act(async () => { resolve(TOTAL); });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("does not try to focus an opener removed while the dialog was open", async () => {
    const view = mount();
    const opener = await openFrom("chart");
    const focus = vi.spyOn(opener, "focus");
    view.rerender(
      <CitationPanelProvider citations={CITATIONS}>
        <Openers showChart={false} />
      </CitationPanelProvider>,
    );
    expect(opener.isConnected).toBe(false);
    await closeWith("close");
    expect(focus).not.toHaveBeenCalled();
  });
});
