import React from "react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { normalizeProgramHHI, parseGaoRatifications, selectRatifiedGaoFindings } from "@/lib/program-evidence";
import { getCitations, getFeed, getGaoCrosswalkStats, getGaoProgramFindings, getPrograms, type CitationsMap, type DerivedCitation, type GaoAssessment, type GaoProgramFindings, type GaoRelatedReport } from "@/lib/data";
import { ProgramConcentration } from "@/components/program-concentration";

afterEach(cleanup);

// Unit cases use fixed independent evidence. A regenerated programs.json may
// legitimately use either supported shape; it must not change which fields a
// malformed-input test mutates. Live-artifact checks remain below.
const HHI_ID = "1111111111111111";
const DOLLARS_ID = "2222222222222222";
const allLinkFormula = "Calculated over high- and medium-confidence links";
const normalizedHhiFormula = "sum(share_pct * share_pct) over (partition by pe_bli) " +
  "where share = family_obligation / sum(family_obligation) " +
  "and obligation > 0 (positive-only shares; negative obligations excluded)";

function derived(value: number, units: string, formula: string): DerivedCitation {
  return {
    kind: "derived", units, formula, recorded_value: String(value), inputs: "[]",
    official_url: null, retrieved_at: null, query_body: null, amount_text: null,
    amount_thousands: null, bottom_pt: null, cells: null, hosted_pdf_url: null,
    page_height: null, page_number: null, page_width: null, resolution: null,
    sha256: null, sheet: null, top_pt: null, x0: null, x1: null, xml_path: null,
  };
}
const citations: CitationsMap = {
  [HHI_ID]: derived(6250, "Herfindahl-Hirschman Index", allLinkFormula),
  [DOLLARS_ID]: derived(1_000_000, "USD", allLinkFormula),
};
const rawHhi = {
  hhi_all: 6250, program_dollars_all: 1_000_000, family_count_all: 2,
  top_family_all: "Example recipient", hhi_all_fact_id: HHI_ID,
  program_dollars_all_fact_id: DOLLARS_ID,
  hhi_high: 10000, program_dollars_high: 100, family_count_high: 1,
  top_family_high: "Another recipient", hhi_high_fact_id: "3333333333333333",
};
const normalizedHhi = {
  hhi: 6250, program_dollars: 1_000_000, family_count: 2,
  top_family: "Example recipient", hhi_fact_id: HHI_ID,
  program_dollars_fact_id: DOLLARS_ID,
};

describe("concentration evidence selection", () => {
  it("retains the all-link amount and its own citations even when the high-only sample differs", () => {
    const result = normalizeProgramHHI(rawHhi, citations)!;
    expect(result).toEqual({ ...normalizedHhi, link_scope: "high-and-medium" });
    expect(result.hhi_fact_id).not.toBe(rawHhi.hhi_high_fact_id);
  });

  it("keeps a cited all-link series when high-only evidence is absent", () => {
    const result = normalizeProgramHHI({ ...rawHhi, hhi_high: null, program_dollars_high: null }, citations);
    expect(result).toEqual({ ...normalizedHhi, link_scope: "high-and-medium" });
  });

  describe.each([
    ["dual-series", rawHhi, "_all"],
    ["normalized", normalizedHhi, ""],
  ] as const)("%s source validation", (_shape, row, suffix) => {
    it("preserves cited 10,000-point HHI sums with only machine-precision roundoff", () => {
      const roundoff = 10000.000000000004;
      const roundoffCitations = { ...citations, [HHI_ID]: derived(10000, "Herfindahl-Hirschman Index", allLinkFormula) };
      expect(normalizeProgramHHI({ ...row, [`hhi${suffix}`]: roundoff }, roundoffCitations)?.hhi).toBe(roundoff);
      expect(normalizeProgramHHI({ ...row, [`hhi${suffix}`]: 10000.0001 }, roundoffCitations)).toBeNull();
    });

    it.each([
      ["missing HHI citation", HHI_ID, null],
      ["missing obligation citation", DOLLARS_ID, null],
      ["wrong HHI value", HHI_ID, { recorded_value: "1" }],
      ["wrong obligation value", DOLLARS_ID, { recorded_value: "1" }],
      ["wrong HHI units", HHI_ID, { units: "USD" }],
      ["wrong obligation units", DOLLARS_ID, { units: "Herfindahl-Hirschman Index" }],
      ["high-only HHI scope", HHI_ID, { formula: "high-confidence links only" }],
      ["high-only obligation scope", DOLLARS_ID, { formula: "high-confidence links only" }],
      ["missing HHI formula", HHI_ID, { formula: null }],
      ["missing obligation formula", DOLLARS_ID, { formula: null }],
      ["unknown HHI formula", HHI_ID, { formula: "unverified population" }],
      ["nonfinite recorded HHI", HHI_ID, { recorded_value: "NaN" }],
    ])("rejects %s", (_reason, id, changes) => {
      const changed = { ...citations };
      if (changes === null) delete changed[id as string];
      else changed[id as string] = { ...changed[id as string], ...changes } as DerivedCitation;
      expect(normalizeProgramHHI(row, changed)).toBeNull();
    });

    it.each([
      ["hhi", null], ["hhi", NaN], ["hhi", 10001],
      ["program_dollars", Infinity], ["family_count", 0],
      ["family_count", 1.5], ["top_family", " "],
    ])("rejects malformed %s value %s", (field, value) => {
      expect(normalizeProgramHHI({ ...row, [`${field}${suffix}`]: value }, citations)).toBeNull();
    });

    it("rejects unsupported declared scope rather than inventing a disclosure", () => {
      expect(normalizeProgramHHI({ ...row, link_scope: "high-only" }, citations)).toBeNull();
    });
  });

  it("preserves evidence scope when normalizing an already normalized result", () => {
    const normalized = normalizeProgramHHI(rawHhi, citations)!;
    expect(normalizeProgramHHI(normalized, citations)).toEqual(normalized);
    expect(normalized.link_scope).toBe("high-and-medium");
  });

  it("recognizes established normalized receipts only with their all-link obligation evidence", () => {
    const legacyCitations = { ...citations, [HHI_ID]: derived(6250, "Herfindahl-Hirschman Index", normalizedHhiFormula) };
    expect(normalizeProgramHHI(normalizedHhi, legacyCitations)).toEqual({ ...normalizedHhi, link_scope: "high-and-medium" });
    // The older one-series formula cannot establish which of two new series
    // was selected; that contract still requires explicit scope on both facts.
    expect(normalizeProgramHHI(rawHhi, legacyCitations)).toBeNull();
    expect(normalizeProgramHHI(normalizedHhi, {
      ...legacyCitations, [DOLLARS_ID]: derived(1_000_000, "USD", "high-confidence links only"),
    })).toBeNull();
  });

  it.each(["0592", "0207146F", "0102110F"])("restores %s with traceable figures and an explicit scope", slug => {
    const hhi = getPrograms().find(row => row.slug === slug)!.hhi;
    expect(hhi).not.toBeNull();
    const { container } = render(<ProgramConcentration hhi={hhi} />);
    expect(screen.getByRole("heading", { name: "Contractor Concentration" })).toBeVisible();
    expect(screen.getByText(/High- and medium-confidence program–award links/)).toBeVisible();
    expect(container.querySelector(`[data-fact-id="${hhi!.hhi_fact_id}"]`)).not.toBeNull();
    expect(container.querySelector(`[data-fact-id="${hhi!.program_dollars_fact_id}"]`)).not.toBeNull();
  });

  it("gives every published concentration feed destination a cited concentration card", () => {
    const bySlug = new Map(getPrograms().map(row => [row.slug, row]));
    const cards = getFeed().cards.filter(row => row.event_type === "concentration_shift");
    expect(cards.length).toBeGreaterThanOrEqual(60);
    for (const card of cards) {
      const slug = card.program_url?.match(/^\/program\/([^/]+)\/$/)?.[1];
      expect(bySlug.get(slug ?? "")?.hhi, card.program_url ?? "missing program URL").toBeTruthy();
    }
  });
});

const header = "product_number,gao_program,slug,verdict,notes\r\n";
const assessment = (product_number: string, common_name = "F-15EX"): GaoAssessment => ({
  product_number, common_name, gao_program: "different long title", assessment_type: "MDAP", description: "Original report wording.",
  pdf_page: 1, pdf_url: "https://www.gao.gov/assets/report.pdf", released: "2025-06-01", report_page: 1,
  report_title: "Weapon Systems Annual Assessment", report_url: "https://www.gao.gov/products/report", service: "Air Force",
});

describe("GAO ratification boundary", () => {
  it("reads quoted commas, escaped quotes, CRLF, and duplicate identical decisions", () => {
    const row = 'GAO-25-107569,"F-15EX, ""Eagle II""",0207146F,y,"two\nlines"\r\n';
    expect(parseGaoRatifications(header + row + row)).toEqual([{ product_number: "GAO-25-107569", gao_program: 'F-15EX, "Eagle II"', slug: "0207146F", verdict: "y" }]);
  });

  it.each([
    "product_number,slug,verdict\nX,Y,y",
    header + "X,Y,Z,maybe",
    header + "X,Y,Z,y\nX,Y,Z,n",
    header + 'X,"Y,Z,y',
  ])("fails closed for malformed or conflicting adjudication seeds", csv => {
    expect(() => parseGaoRatifications(csv)).toThrow();
  });

  it("requires exact report, GAO program name, and canonical slug; never inherits a prior edition", () => {
    const accepted = assessment("GAO-25-107569");
    const report: GaoRelatedReport = { gao_program: "F-15EX", product_number: "GAO-25-RELATED", released: "2025-01-01", report_title: "Related work", report_url: "https://www.gao.gov/products/related" };
    const data: Record<string, GaoProgramFindings> = {
      "0207146F": { assessments: [accepted, assessment("GAO-24-106831"), assessment("GAO-25-107569", "Another program")], reports: [report, { ...report, gao_program: "Another program" }] },
      "F015EX": { assessments: [accepted], reports: [report] },
    };
    const decisions = parseGaoRatifications(header + "GAO-25-107569,F-15EX,0207146F,y\nGAO-24-106831,F-15EX,0207146F,n\nGAO-25-RELATED,F-15EX,0207146F,y");
    const result = selectRatifiedGaoFindings(data, decisions);
    expect(Object.keys(result)).toEqual(["0207146F"]);
    expect(result["0207146F"]).toEqual({ assessments: [accepted], reports: [report] });
    expect(result["0207146F"].assessments[0]).toBe(accepted);
  });

  it.each(["0207146F", "0102110F"])("publishes only the ratified annual assessment for %s", slug => {
    expect(getGaoProgramFindings(slug)?.assessments.map(row => row.product_number)).toEqual(["GAO-25-107569"]);
  });

  it("reports stats for actual ratifications and the rendered population", () => {
    const decisions = parseGaoRatifications(readFileSync(join(process.cwd(), "../data-seeds/gao_program_xwalk.csv"), "utf8"));
    const findings = JSON.parse(readFileSync(join(process.cwd(), "../data/site/json/gao_program_findings.json"), "utf8"));
    const selected = selectRatifiedGaoFindings(findings.by_slug, decisions);
    expect(getGaoCrosswalkStats()).toMatchObject({
      accepted: decisions.filter(row => row.verdict === "y").length,
      rejected: decisions.filter(row => row.verdict === "n").length,
      adjudicated: decisions.length,
      pages_with_findings: Object.keys(selected).length,
      rendered_items: Object.values(selected).reduce((sum, row) => sum + row.assessments.length + row.reports.length, 0),
    });
  });
});
