import React from "react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { normalizeProgramHHI, parseGaoRatifications, selectRatifiedGaoFindings } from "@/lib/program-evidence";
import { getCitations, getFeed, getGaoCrosswalkStats, getGaoProgramFindings, getPrograms, type CitationsMap, type GaoAssessment, type GaoProgramFindings, type GaoRelatedReport } from "@/lib/data";
import { ProgramConcentration } from "@/components/program-concentration";

afterEach(cleanup);

const citations = getCitations();
const rawPrograms = JSON.parse(readFileSync(join(process.cwd(), "../data/site/json/programs.json"), "utf8"));
const rawHhi = rawPrograms.find((row: { slug: string }) => row.slug === "0207146F").hhi;

describe("concentration evidence selection", () => {
  it("retains the all-link amount and its own citations even when the high-only sample differs", () => {
    const result = normalizeProgramHHI({ ...rawHhi, hhi_high: 10000, program_dollars_high: 1 }, citations)!;
    expect(result.hhi).toBe(rawHhi.hhi_all);
    expect(result.program_dollars).toBe(rawHhi.program_dollars_all);
    expect(result.hhi_fact_id).toBe(rawHhi.hhi_all_fact_id);
    expect(result.program_dollars_fact_id).toBe(rawHhi.program_dollars_all_fact_id);
    expect(result.hhi_fact_id).not.toBe(rawHhi.hhi_high_fact_id);
    expect(result.link_scope).toBe("high-and-medium");
  });

  it("keeps a cited all-link series when high-only evidence is absent", () => {
    const row = rawPrograms.find((row: { slug: string }) => row.slug === "0102110F");
    expect(row.hhi.hhi_high).toBeNull();
    expect(normalizeProgramHHI(row.hhi, citations)?.hhi).toBe(10000);
  });

  it("preserves cited 10,000-point HHI sums with only machine-precision roundoff", () => {
    const row = rawPrograms.find((row: { slug: string }) => row.slug === "0101316F");
    expect(normalizeProgramHHI(row.hhi, citations)?.hhi).toBe(row.hhi.hhi_all);
    expect(normalizeProgramHHI({ ...row.hhi, hhi_all: 10000.0001 }, citations)).toBeNull();
  });

  it.each([
    ["missing citation", {}],
    ["wrong value", { recorded_value: "1" }],
    ["wrong units", { units: "USD" }],
    ["wrong link scope", { formula: "high-confidence links only" }],
    ["missing formula", { formula: null }],
  ])("rejects %s", (_, changes) => {
    const id = rawHhi.hhi_all_fact_id;
    const changed = Object.keys(changes).length ? { ...citations, [id]: { ...citations[id], ...changes } } : {};
    expect(normalizeProgramHHI(rawHhi, changed as CitationsMap)).toBeNull();
  });

  it.each([
    { hhi_all: null }, { hhi_all: NaN }, { hhi_all: 10001 },
    { program_dollars_all: Infinity }, { family_count_all: 0 },
    { family_count_all: 1.5 }, { top_family_all: " " },
  ])("rejects malformed source values: %j", changes => {
    expect(normalizeProgramHHI({ ...rawHhi, ...changes }, citations)).toBeNull();
  });

  it("also supports the established normalized data contract", () => {
    const normalized = normalizeProgramHHI(rawHhi, citations)!;
    expect(normalizeProgramHHI(normalized, citations)).toMatchObject({
      hhi: rawHhi.hhi_all, hhi_fact_id: rawHhi.hhi_all_fact_id,
      program_dollars: rawHhi.program_dollars_all,
    });
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
