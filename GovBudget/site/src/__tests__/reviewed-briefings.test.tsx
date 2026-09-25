import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import specs from "@/lib/briefing-specs.json";
import type { ProgramDetails } from "@/lib/data";
import { getCitations } from "@/lib/data";
import { CitationPanelContext } from "@/components/cite";

const load = (slug: string): ProgramDetails => JSON.parse(readFileSync(resolve(process.cwd(), "../data/site/json/program_details", `${slug}.json`), "utf8"));
vi.mock("@/lib/data", () => ({
  getProgramDetails: (slug: string) => load(slug),
  getCitations: vi.fn(() => Object.fromEntries(specs.flatMap(s => Object.keys(s.sourceChecks)).map(fid => [fid, JSON.parse(readFileSync(resolve(process.cwd(), "../data/site/json/cite-shards", `${fid.slice(0, 2)}.json`), "utf8"))[fid]]))),
}));
import { getReviewedBriefings } from "@/lib/reviewed-briefings";
import { ReviewedBriefings } from "@/components/reviewed-briefings";

describe("dated source-backed briefings", () => {
  it.each([
    ["f371727c075ecac9", "amount_thousands", 1],
    ["f371727c075ecac9", "sheet", "Wrong sheet"],
    ["f371727c075ecac9", "cells", "A1"],
    ["03407158217dec76", "amount_thousands", 1],
    ["da8fcf0561c0e6e8", "page_number", 1],
  ])("blocks changed %s %s even while fact IDs and summaries match", (factId, key, value) => {
    const citations = getCitations();
    vi.mocked(getCitations).mockReturnValueOnce({ ...citations, [factId]: { ...citations[factId], [key]: value } });
    expect(() => getReviewedBriefings()).toThrow(/Briefing needs source review/);
  });
  it("allows a refreshed retrieval timestamp without changing the reviewed evidence", () => {
    const citations = getCitations();
    const factId = "f371727c075ecac9";
    vi.mocked(getCitations).mockReturnValueOnce({ ...citations, [factId]: { ...citations[factId], retrieved_at: "2026-09-23T00:00:00Z" } });
    expect(() => getReviewedBriefings()).not.toThrow();
  });
  it("binds the frozen before/after context and exact narrative to current exported evidence", () => {
    const briefings = getReviewedBriefings();
    expect(briefings).toHaveLength(3);
    for (const briefing of briefings) {
      expect(briefing.figures.map(f => f.fy)).toEqual([2025, 2026]);
      expect(briefing.figures[1].measure).toBe("request");
      expect(briefing.figures.every(f => f.basis === "toa")).toBe(true);
    }
    expect(briefings[2].figures[0].measure).toBe("total");
  });
  it("renders all six amounts through receipts and states scope limits", () => {
    const openPanel = vi.fn();
    const { container, getAllByRole } = render(<CitationPanelContext.Provider value={{ openPanel }}><ReviewedBriefings /></CitationPanelContext.Provider>);
    expect(container.querySelectorAll("[data-amount][data-fact-id]")).toHaveLength(6);
    expect(container.textContent).toContain("does not explain the full P-1 change");
    expect(container.textContent).toContain("not an achieved outcome");
    const buttons = getAllByRole("button", { name: "Read source passage", hidden: true });
    expect(buttons).toHaveLength(3);
    for (const [index, button] of buttons.entries()) {
      fireEvent.click(button);
      expect(openPanel).toHaveBeenLastCalledWith(specs[index].narrativeFactId);
    }
    expect(container.querySelectorAll('[data-source-text][data-cite-fact-id]')).toHaveLength(3);
    expect(container.textContent).toContain("Assistant source review; not human sign-off");
  });
});
