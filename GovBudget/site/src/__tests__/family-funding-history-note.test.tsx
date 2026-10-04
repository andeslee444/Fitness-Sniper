import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { parse } from "node-html-parser";
import { FamilyFundingHistory } from "@/components/family-funding-history";
import { CitationPanelContext } from "@/components/cite";
import { validateFamilyHistoryMatrix, type FamilyFundingHistoryData, type FamilyFundingHistoryView, type FamilyFundingProgram } from "@/lib/family-funding-history";
import { checkFamilyHistoryNotes } from "../../scripts/gates/family-history.mjs";

// Spec §6.5 (S5): the strings the owner signed off, on a hermetic one-year history.
const NOTE = "This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four operationally representative test aircraft and two operational aircraft were purchased with procurement funds (F015E0, Line #3 [line 3 of the PB2020–21 P-1 (line 4 in PB2022)])).";
const NOTE_FID = "e7d5bcfb4a30f458";
const ANNUAL = "a".repeat(16);
const CELL = "b".repeat(16);
const noted: FamilyFundingProgram = { id: "P-1:3010F:AF:F015E0", code: "F015E0", title: "F-15e (FY2020 F-15EX Lot 1 aircraft)", program_slug: null, exhibit: "P-1", account: "3010F", organization: "AF", note: NOTE, note_fact_id: NOTE_FID };
const plain: FamilyFundingProgram = { id: "P-1:3010F:AF:F01500", code: "F01500", title: "F-15", program_slug: "F01500", exhibit: "P-1", account: "3010F", organization: "AF" };
const citations = { [NOTE_FID]: { kind: "jbook_narrative", page_number: 71 } };

function view(programs: FamilyFundingProgram[] = [noted, plain]): FamilyFundingHistoryView {
  return {
    schema_version: 1, family_id: "f-15", units: "USD thousands", basis: "toa", start_fy: 2020, end_fy: 2020,
    scope_note: "Scope.", coverage_notes: ["Coverage."], default_point_ids: ["fy2020a"], programs,
    cumulative: { start_fy: 2020, end_fy: 2020, kind: "actuals", measure: "actuals", amount_thousands: 621100, fact_id: ANNUAL, point_ids: ["fy2020a"], scope_note: "Sum." },
    points: [{
      id: "fy2020a", fy: 2020, edition: 2022, kind: "actuals", measure: "actuals", measure_label: "Recorded actuals",
      amount_thousands: 621100, fact_id: ANNUAL, coverage: "covered-records", missing_programs: [], component_count: 1,
      program_cells: [{ program_id: noted.id, amount_thousands: 621100, fact_id: CELL, measure: "actuals", dataset: "budget_lines_decade", input_fact_ids: [CELL] }],
    }],
  };
}

afterEach(() => cleanup());

describe("F-15 budget-line notes (spec §6.5)", () => {
  it("quotes the F015E0 sentence once, as cited source text, beside its narrative receipt", () => {
    Element.prototype.scrollIntoView = vi.fn();
    const openPanel = vi.fn();
    render(<CitationPanelContext.Provider value={{ openPanel }}><FamilyFundingHistory history={view()} shortName="F-15" /></CitationPanelContext.Provider>);
    const notes = document.querySelectorAll("[data-history-note]");
    expect(notes).toHaveLength(1);
    expect(notes[0]).toHaveAttribute("id", "history-note-F015E0");
    const quote = notes[0].querySelector(`[data-source-text="narrative"][data-cite-fact-id="${NOTE_FID}"]`);
    expect(quote?.textContent).toBe(`“${NOTE}”`);
    expect(notes[0].querySelector("[data-amount]")).toBeNull();
    fireEvent.click(notes[0].querySelector(`[data-narrative-chip][data-fact-id="${NOTE_FID}"]`)!);
    expect(openPanel).toHaveBeenCalledWith(NOTE_FID);
    expect(document.querySelector('[data-history-program="P-1:3010F:AF:F015E0"] [data-history-note-ref="F015E0"]')).toHaveAttribute("href", "#history-note-F015E0");
    expect(document.querySelector('[data-history-program="P-1:3010F:AF:F01500"] [data-history-note-ref]')).toBeNull();
    expect(screen.getByRole("rowheader", { name: /F-15e \(FY2020 F-15EX Lot 1 aircraft\)/ })).toBeInTheDocument();
  });

  it("renders no note list when no program carries a note", () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(<FamilyFundingHistory history={view([plain])} shortName="F-15" />);
    expect(document.querySelector("[data-history-note]")).toBeNull();
    expect(screen.queryByRole("list", { name: "Budget-line notes" })).toBeNull();
  });

  it("release gate accepts the rendered note and rejects each kind of drift", () => {
    const html = renderToStaticMarkup(<FamilyFundingHistory history={view()} shortName="F-15" />);
    expect(checkFamilyHistoryNotes(parse(html), view(), citations)).toEqual([]);
    expect(checkFamilyHistoryNotes(parse(html.replace("Lot 1 which", "Lot 1, which")), view(), citations)).toContain("program F015E0 rendered note differs from its export");
    expect(checkFamilyHistoryNotes(parse(html), view(), { [NOTE_FID]: { kind: "workbook" } })).toContain("program F015E0 note lacks a narrative receipt");
    const noChip = parse(html);
    noChip.querySelector("[data-narrative-chip]")!.remove();
    expect(checkFamilyHistoryNotes(noChip, view(), citations)).toContain("program F015E0 note is not rendered with its source chip");
    const noRef = parse(html);
    noRef.querySelector("[data-history-note-ref]")!.remove();
    expect(checkFamilyHistoryNotes(noRef, view(), citations)).toContain("program F015E0 row does not point to its note");
    expect(checkFamilyHistoryNotes(parse(renderToStaticMarkup(<FamilyFundingHistory history={view([plain])} shortName="F-15" />)), view(), citations)).toContain("family notes: 0 rendered for 1 noted program(s)");
  });

  it("the loader rejects a note without its receipt id", () => {
    const data = {
      ...view(),
      points: view().points.map(point => ({ ...point, components: [{ fact_id: CELL, program_id: noted.id, amount_thousands: 621100 }] })),
    } as unknown as FamilyFundingHistoryData;
    expect(() => validateFamilyHistoryMatrix(data)).not.toThrow();
    const broken = structuredClone(data);
    delete broken.programs[0].note_fact_id;
    expect(() => validateFamilyHistoryMatrix(broken)).toThrow("Invalid family program note: F015E0");
  });
});
