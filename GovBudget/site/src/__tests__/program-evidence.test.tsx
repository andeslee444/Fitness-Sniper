import React from "react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { normalizeProgramHHI, parseGaoRatifications, selectPublishedGaoFindings, selectRatifiedGaoFindings } from "@/lib/program-evidence";
import { getCitations, getFeed, getGaoCrosswalkStats, getGaoProgramFindings, getPrograms, type CitationsMap, type DerivedCitation, type GaoAssessment, type GaoProgramFindings, type GaoRelatedReport } from "@/lib/data";
import { ProgramConcentration } from "@/components/program-concentration";
import { concentrationHeadline } from "@/lib/concentration-basis";

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

  // Integration 2026-09-25, ruling R-INT-2. The f15-family-browser branch
  // published the all-link figure on these three pages; the merged site
  // keeps ROADMAP #80 (publish the smaller true number): a page headlines
  // the HIGH-confidence figure where it clears the mart's floor, and
  // otherwise states the withholding and prints no figure. The all-link
  // validator stays in front as a fail-closed guard — getPrograms() keeps a
  // block only when normalizeProgramHHI() resolves it against citations.
  // Expected states measured on the 2026-09-25 run-4 export: 0207146F clears
  // the floor (3 high awards, 2 positive families); 0592 and 0102110F each
  // have one high-confidence family, so their high index is withheld.
  it.each([
    ["0207146F", "published"],
    ["0592", "withheld"],
    ["0102110F", "withheld"],
  ] as const)("%s headlines the high-confidence figure or the withheld state (#80), behind the all-link validator", (slug, expected) => {
    const hhi = getPrograms().find(row => row.slug === slug)!.hhi;
    expect(hhi).not.toBeNull();
    // The live branch's validator is still guarding this block.
    expect(normalizeProgramHHI(hhi, getCitations())).not.toBeNull();
    const head = concentrationHeadline(hhi!);
    expect(head.published ? "published" : "withheld").toBe(expected);
    const { container } = render(<ProgramConcentration hhi={hhi} />);
    // #175 (fix round 4): sentence case, per VOICE.md.
    expect(screen.getByRole("heading", { name: "Contractor concentration" })).toBeVisible();
    // The all-link figures never reach the card, on either state.
    expect(container.querySelector(`[data-fact-id="${hhi!.hhi_all_fact_id}"]`)).toBeNull();
    expect(container.querySelector(`[data-fact-id="${hhi!.program_dollars_all_fact_id}"]`)).toBeNull();
    expect(screen.queryByText(/High- and medium-confidence program–award links/)).toBeNull();
    if (head.published) {
      const bands = container.querySelectorAll("[data-hhi-band]");
      expect(bands).toHaveLength(1);
      expect(bands[0]).toHaveAttribute("data-hhi-basis", "high");
      expect(hhi!.hhi_high_fact_id).not.toBeNull();
      expect(hhi!.program_dollars_high_fact_id).not.toBeNull();
      expect(container.querySelector(`[data-fact-id="${hhi!.hhi_high_fact_id}"]`)).not.toBeNull();
      expect(container.querySelector(`[data-fact-id="${hhi!.program_dollars_high_fact_id}"]`)).not.toBeNull();
      expect(container.querySelector("[data-concentration-withheld]")).toBeNull();
    } else {
      expect(hhi!.hhi_high).toBeNull();
      expect(container.querySelector('[data-concentration-withheld="below-floor"]')).not.toBeNull();
      expect(container.querySelector("[data-hhi-band]")).toBeNull();
      expect(container.querySelector("[data-amount]")).toBeNull();
      expect(container.querySelector("[data-fact-id]")).toBeNull();
    }
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
const assessment = (
  product_number: string, common_name = "F-15EX",
  chain: Pick<GaoAssessment, "edition_year" | "inherited_from" | "program_key"> = { edition_year: 2025, inherited_from: null, program_key: "f15ex" },
): GaoAssessment => ({
  product_number, common_name, gao_program: "different long title", assessment_type: "MDAP", description: "Original report wording.",
  pdf_page: 1, pdf_url: "https://www.gao.gov/assets/report.pdf", released: "2025-06-01", report_page: 1,
  report_title: "Weapon Systems Annual Assessment", report_url: "https://www.gao.gov/products/report", service: "Air Force",
  ...chain,
});
// An older WSAA edition chained to the ratified anchor `anchor` (#30).
const olderEdition = (product_number: string, edition_year: number, anchor: string, program_key = "f15ex", common_name = "F-15EX") =>
  assessment(product_number, common_name, { edition_year, inherited_from: anchor, program_key });

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

  // Integration 2026-09-25, ruling R-INT-3: an older edition carries no
  // verdict of its own and passes only when the ratified anchor it is
  // chained to (inherited_from + program_key) passes on the SAME page.
  it("an older edition passes only behind its ratified anchor on the same page", () => {
    const anchor = assessment("GAO-25-107569");
    const chained = olderEdition("GAO-24-106831", 2024, "GAO-25-107569");
    const otherProgram = olderEdition("GAO-23-106059", 2023, "GAO-25-107569", "mh139a", "MH-139A");
    // Fix round 1 (2026-09-25): the B-52 anchor and its older edition share
    // ONE program key, "b52". The first version of this case left the anchor
    // on the default "f15ex" key, so the key mismatch dropped the older
    // edition whatever the anchor's verdict was, and the case proved nothing
    // about the verdict. Now only the anchor's verdict can drop it.
    const b52Anchor = assessment("GAO-25-107569", "B-52", { edition_year: 2025, inherited_from: null, program_key: "b52" });
    const b52Older = olderEdition("GAO-24-106831", 2024, "GAO-25-107569", "b52", "B-52");
    const data: Record<string, GaoProgramFindings> = {
      // anchor ratified here: its own edition chain renders; a row chained
      // to the same product under another program key does not.
      "0207146F": { assessments: [anchor, chained, otherProgram], reports: [] },
      // anchor NOT ratified here ('n'): its chained older edition drops too.
      "0101127F": { assessments: [b52Anchor, b52Older], reports: [] },
      // an older edition alone, its anchor ratified only on ANOTHER page.
      "F015EX": { assessments: [chained], reports: [] },
    };
    // Precondition that keeps this case honest: on 0101127F the older
    // edition's chain (inherited_from + program_key) matches an anchor row,
    // so a rule that accepted ANY inherited_from === null row as the anchor
    // would publish it.
    expect(data["0101127F"].assessments.some(row =>
      row.inherited_from === null &&
      row.product_number === b52Older.inherited_from &&
      row.program_key === b52Older.program_key)).toBe(true);
    const decisions = parseGaoRatifications(header + "GAO-25-107569,F-15EX,0207146F,y\nGAO-25-107569,B-52,0101127F,n");
    const result = selectPublishedGaoFindings(data, decisions);
    expect(Object.keys(result)).toEqual(["0207146F"]);
    expect(result["0207146F"].assessments).toEqual([anchor, chained]);
    // The guard alone would publish the anchor and nothing chained to it.
    expect(selectRatifiedGaoFindings(data, decisions)["0207146F"].assessments).toEqual([anchor]);

    // Counter-case: the SAME fixture, with ONLY the B-52 verdict changed to
    // 'y'. The anchor is ratified now, so its older edition publishes behind
    // it: the verdict alone decided the outcome above.
    const b52Ratified = parseGaoRatifications(header + "GAO-25-107569,F-15EX,0207146F,y\nGAO-25-107569,B-52,0101127F,y");
    const counter = selectPublishedGaoFindings(data, b52Ratified);
    expect(Object.keys(counter)).toEqual(["0207146F", "0101127F"]);
    expect(counter["0101127F"].assessments).toEqual([b52Anchor, b52Older]);
    expect(counter["0207146F"].assessments).toEqual([anchor, chained]);
  });

  it.each(["0207146F", "0102110F"])("publishes the ratified annual assessment for %s and the older editions chained to it", slug => {
    const rows = getGaoProgramFindings(slug)!.assessments;
    const anchors = rows.filter(row => row.inherited_from === null);
    expect(anchors.map(row => row.product_number)).toEqual(["GAO-25-107569"]);
    // Every other row is an older edition of that same anchor's program.
    for (const row of rows.filter(row => row.inherited_from !== null)) {
      expect(row.inherited_from).toBe("GAO-25-107569");
      expect(row.program_key).toBe(anchors[0].program_key);
      expect(row.edition_year).toBeLessThan(anchors[0].edition_year);
    }
    // Measured on the 2026-09-25 run-4 export: the 2024 and 2023 editions.
    expect(rows.map(row => row.product_number)).toEqual(["GAO-25-107569", "GAO-24-106831", "GAO-23-106059"]);
  });

  it("reports stats for actual ratifications and the rendered population, matching the export", () => {
    const decisions = parseGaoRatifications(readFileSync(join(process.cwd(), "../data-seeds/gao_program_xwalk.csv"), "utf8"));
    const findings = JSON.parse(readFileSync(join(process.cwd(), "../data/site/json/gao_program_findings.json"), "utf8"));
    const selected = selectPublishedGaoFindings(findings.by_slug, decisions);
    const stats = getGaoCrosswalkStats()!;
    expect(stats).toMatchObject({
      accepted: decisions.filter(row => row.verdict === "y").length,
      rejected: decisions.filter(row => row.verdict === "n").length,
      adjudicated: decisions.length,
      pages_with_findings: Object.keys(selected).length,
      rendered_items: Object.values(selected).reduce((sum, row) => sum + row.assessments.length + row.reports.length, 0),
      inherited_items: Object.values(selected).reduce((sum, row) => sum + row.assessments.filter(a => a.inherited_from !== null).length, 0),
    });
    // The guard drops nothing the exporter published: the rendered
    // population is the export's own (132 items, 70 inherited, on
    // 2026-09-25's run-4 export).
    expect(stats.rendered_items).toBe(findings.stats.rendered_items);
    expect(stats.inherited_items).toBe(findings.stats.inherited_items);
    expect(stats.pages_with_findings).toBe(findings.stats.pages_with_findings);
  });
});
