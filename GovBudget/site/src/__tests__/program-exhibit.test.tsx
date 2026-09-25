import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ProgramExhibit } from "@/components/program-exhibit";
import { CitationPanelContext } from "@/components/cite";
import { PROGRAM_EXHIBITS, validateExhibitNarratives } from "@/lib/program-exhibits";
import type { ProgramDetails } from "@/lib/data";
import { getCitations } from "@/lib/data";
import { trackReaderEvent } from "@/lib/reader-events";

vi.mock("next/script", () => ({ default: () => null }));
vi.mock("@/lib/reader-events", () => ({ trackReaderEvent: vi.fn() }));
const writeText = vi.fn<(...args: string[]) => Promise<void>>();
beforeEach(() => {
  writeText.mockReset().mockResolvedValue(undefined);
  vi.mocked(trackReaderEvent).mockReset();
  window.history.replaceState({}, "", "/program/2013/");
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
});
afterEach(cleanup);
const details = (slug: string): ProgramDetails => JSON.parse(readFileSync(resolve(process.cwd(), "../data/site/json/program_details", `${slug}.json`), "utf8"));

function mount(slug = "2013") {
  const d = details(slug), openPanel = vi.fn();
  const view = render(<CitationPanelContext.Provider value={{ openPanel, hasCitation: () => true }}>
    <ProgramExhibit config={PROGRAM_EXHIBITS[slug]} cards={d.summary.cards} exhibitFamily={slug === "2013" || slug === "ATA000" ? "procurement" : "rdte"}
      narratives={d.narratives} citations={getCitations()}
      reconciliationKeys={d.summary.reconciliation.map(r => `${r.fy}|${r.measure}`)}/>
  </CitationPanelContext.Provider>);
  return { ...view, d, openPanel };
}

describe("program exhibits and financial provenance", () => {
  it("counts a repeated 3D topic event only when the selection changes", () => {
    const { container } = mount();
    fireEvent.click(screen.getByRole("button", { name: "Explore in 3D" }));
    const scene = container.querySelector("fiscal-scene")!;
    fireEvent(scene, new CustomEvent("topic-select", { detail: { topic: "construction" } }));
    fireEvent(scene, new CustomEvent("topic-select", { detail: { topic: "shipyard" } }));
    fireEvent(scene, new CustomEvent("topic-select", { detail: { topic: "shipyard" } }));
    expect(vi.mocked(trackReaderEvent).mock.calls.filter(([event]) => event === "brief_selected")).toHaveLength(1);
  });
  it.each(["change", "2024", "fy9999"])("ignores unavailable shared funding year %s", async (year) => {
    window.history.replaceState({}, "", `/program/2013/#exhibit?topic=construction&year=${year}`);
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: vi.fn() });
    mount();
    await act(async () => { await new Promise<void>(resolve => requestAnimationFrame(() => resolve())); });
    expect(screen.getByLabelText("Program funding")).toHaveValue("fy2026");
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Copy answer" })); });
    expect(writeText.mock.calls[0][0]).toContain("year=fy2026");
  });
  it.each(["2013", "0602668D8Z"])("copies the selected %s funding fact with its exact narrative passage", async (slug) => {
    const { d } = mount(slug);
    fireEvent.change(screen.getByLabelText("Program funding"), { target: { value: "fy2024" } });
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    await waitFor(() => expect(trackReaderEvent).toHaveBeenCalledWith("answer_copied", expect.objectContaining({ program: slug, fiscalYear: 2024, measure: "actuals" })));
    const text = writeText.mock.calls[0][0];
    const topic = PROGRAM_EXHIBITS[slug].topics[0];
    expect(text).toContain(d.summary.cards.find(c => c.key === "fy2024")!.fid);
    expect(text).toContain(topic.factId);
    expect(text).toContain(topic.evidenceContains);
    expect(text).toContain("year=fy2024");
    expect(text).toContain("topic=" + topic.id);
    expect(text).toContain("does not describe each selected funding year");
    expect(screen.getByRole("status")).toHaveTextContent("Answer copied");
    expect(vi.mocked(trackReaderEvent).mock.calls.filter(([event]) => event === "answer_copied")).toHaveLength(1);
  });
  it("exposes selectable text without recording a completed copy when clipboard fails", async () => {
    mount();
    writeText.mockRejectedValueOnce(new Error("blocked"));
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    const fallback = await screen.findByRole("textbox", { name: "Text to copy" });
    expect(fallback).toHaveValue(writeText.mock.calls[0][0]);
    expect(vi.mocked(trackReaderEvent).mock.calls.some(([event]) => event === "answer_copied")).toBe(false);
  });
  it("withholds answer copying when its narrative anchor no longer matches", () => {
    const d = details("2013");
    render(<ProgramExhibit config={PROGRAM_EXHIBITS["2013"]} cards={d.summary.cards} exhibitFamily="procurement" reconciliationKeys={[]} narratives={d.narratives.map(item => ({ ...item, body: "Unrelated source passage." }))} citations={getCitations()} />);
    expect(screen.getByRole("button", { name: "Copy answer" })).toBeDisabled();
  });
  it("grounds every curated topic in its own program's current narrative", () => {
    for (const config of Object.values(PROGRAM_EXHIBITS)) {
      expect(() => validateExhibitNarratives(config, details(config.slug).narratives)).not.toThrow();
    }
    expect(() => validateExhibitNarratives(PROGRAM_EXHIBITS.ATA000, details("0604840F").narratives)).toThrow(/missing or changed/);
  });
  it("opens the selected topic's actual source passage", () => {
    const { openPanel } = mount();
    fireEvent.click(screen.getByRole("tab", { name: /Shipyard capacity/ }));
    fireEvent.click(screen.getByRole("button", { name: /Read the source passage/ }));
    expect(openPanel).toHaveBeenCalledWith("ab7edeece9637c51");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("shipbuilder productivity");
  });
  it("switches financial facts and keeps the year, measure, and accounting basis", () => {
    const { container, d } = mount("0604840F");
    fireEvent.change(screen.getByLabelText("Program funding"), { target: { value: "fy2024" } });
    const amount = container.querySelector("[data-amount]")!;
    expect(amount.getAttribute("data-fact-id")).toBe(d.summary.cards.find(c => c.key === "fy2024")!.fid);
    expect(amount.getAttribute("data-fy")).toBe("2024");
    expect(amount.getAttribute("data-measure")).toBe("actuals");
    expect(amount.getAttribute("data-basis")).toBe("toa");
    expect(container.textContent).toContain("R-1 TOA");
  });
  it("supports keyboard topic selection without requiring 3D", () => {
    mount("0602668D8Z");
    const first = screen.getByRole("tab", { name: /Research foundations/ });
    fireEvent.keyDown(first, { key: "ArrowRight" });
    const next = screen.getByRole("tab", { name: /Dependable networks/ });
    expect(next).toHaveAttribute("aria-selected", "true");
    expect(next).toHaveFocus();
    expect(screen.getByRole("tabpanel")).toHaveTextContent("conceptual");
  });
  it("loads 3D only on request and recovers to the poster if WebGL fails", () => {
    const { container } = mount();
    expect(container.querySelector("fiscal-scene")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Explore in 3D" }));
    const scene = container.querySelector("fiscal-scene")!;
    expect(scene).toHaveAttribute("src", "/exhibits/virginia.glb");
    fireEvent(scene, new CustomEvent("scene-error"));
    expect(container.querySelector("fiscal-scene")).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent("unavailable");
    expect(screen.getByRole("button", { name: /Read the source passage/ })).toBeEnabled();
  });
  it("keeps the two F-35 funding routes separate", () => {
    mount("ATA000");
    expect(screen.getByRole("link", { name: "Aircraft procurement" })).toHaveAttribute("aria-current", "page");
    const destination = new URL(screen.getByRole("link", { name: "Capability development" }).getAttribute("href")!, "https://fiscalreceipts.com");
    expect(destination.pathname.replace(/\/$/, "")).toBe("/program/0604840F");
    expect(destination.hash).toBe("#exhibit");
  });
});
