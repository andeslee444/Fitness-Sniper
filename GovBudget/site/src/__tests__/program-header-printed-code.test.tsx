/**
 * ProgramHeader on a route-safe alias page (#194; families piece-1 follow-ups
 * design §4.6, owner Q1 (a), Q2, Q5). /program/0390DOM/ is the P-1 line the
 * workbook prints as "O&M": the header shows the printed code, names it a
 * BLI under an "O&M" badge, says why the address is 0390DOM, and points to
 * the two R-1 program elements the RDT&E line restates. Every other page
 * keeps its key and renders neither note.
 */
import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import React from "react";

import { ProgramHeader } from "@/components/program-header";
import type { ProgramRow, RestatedLine } from "@/lib/data";

const OM: ProgramRow = {
  award_count: 0,
  exhibit_family: "om",
  fully_reconciled: false,
  reconciled_in_scope: null,
  fy2024_actual_millions: null,
  fy2024_fact_id: null,
  fy2024_xml_path: null,
  hhi: null,
  narrative_count: 0,
  org: "A",
  pe_bli: "0390DOM",
  project_count: 0,
  title: "Chem Demilitarization - O&M",
  trajectory: null,
  trajectory_fact_ids: null,
  slug: "0390DOM",
  account: null,
  account_title: null,
};
const RESTATED: RestatedLine[] = [{
  line_item_code: "RDT&E",
  title: "Chem Demilitarization - RDT&E",
  program_elements: ["0708081D", "0708083D"],
}];

afterEach(cleanup);

describe("ProgramHeader, route-safe alias page", () => {
  it("shows the printed code, the BLI term and the O&M badge", () => {
    const { container } = render(
      <ProgramHeader program={OM} tier="rollup" printedCode="O&M" restatedLines={RESTATED} />,
    );
    expect(container.querySelector("[data-printed-code]")?.textContent).toBe("O&M");
    expect(container.querySelector("[data-glossary-term]")?.textContent).toBe("BLI");
    expect(container.querySelector("[data-glossary-term]")?.getAttribute("data-glossary-term")).toBe("bli");
    expect(container.textContent).toContain("O&M");
    expect(container.querySelector("[data-printed-code-note]")?.textContent).toBe(
      "The P-1 prints this line's code as O&M; its address uses 0390DOM because a web address cannot carry “&”.");
  });

  it("names the restated RDT&E line and links both program elements", () => {
    const { container } = render(
      <ProgramHeader program={OM} tier="rollup" printedCode="O&M" restatedLines={RESTATED} />,
    );
    const note = container.querySelector("[data-restated-line]");
    expect(note?.getAttribute("data-restated-line")).toBe("RDT&E");
    expect(note?.textContent).toBe(
      "The P-1's Chem Demilitarization - RDT&E line restates R-1 program elements 0708081D and 0708083D, whose pages carry those dollars.");
    // next/link drops the trailing slash under vitest; the build writes /program/<pe>/
    expect([...(note?.querySelectorAll("a") ?? [])].map((a) => a.getAttribute("href"))).toEqual([
      expect.stringMatching(/^\/program\/0708081D\/?$/), expect.stringMatching(/^\/program\/0708083D\/?$/)]);
  });

  it("leaves every other page as it was", () => {
    const { container } = render(
      <ProgramHeader program={{ ...OM, pe_bli: "7001SA1000", slug: "7001SA1000", exhibit_family: "procurement" }} tier="rollup" />,
    );
    expect(container.querySelector("code.t-id")?.textContent).toBe("7001SA1000");
    expect(container.querySelector("[data-printed-code]")).toBeNull();
    expect(container.querySelector("[data-printed-code-note]")).toBeNull();
    expect(container.querySelector("[data-restated-line]")).toBeNull();
    expect(container.querySelector("[data-glossary-term]")?.textContent).toBe("BLI");
  });
});
