import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * Canonical corpus statement — PM-review Sprint 2, spec §P1-5.
 *
 * Hermetic: the real data sidecars must not be read. Each test drives
 * getCorpus through a mocked @/lib/data.
 */

const state = {
  /**
   * Backlog #35: the detail tier is the sidecars that hold J-book detail rows
   * (= dim_programs), not programs.json's length. The mock keeps them
   * DIFFERENT on purpose — 1,739 vs 1,741, exactly the shipped gap — so a
   * regression back to the index count fails here rather than on the page.
   */
  detailGrade: 1739,
  programs: 1741,
  programPages: 1993,
  meta: {
    counts: { agencies: 23, citations: 1, companies: 200, programs: 1741, program_pages: 1993 },
    corpus_scope:
      "excludes personnel, O&M, and R-1/P-1 lines that lack R-2/P-40 project detail",
  } as Record<string, unknown>,
  flows: 200,
  flowsOutsideBridge: 34,
  bridge: { universePeCount: 444, crosswalkedPeCount: 384, highConfidencePeCount: 240 },
};

vi.mock("@/lib/data", () => ({
  getPrograms: () => new Array(state.programs).fill({}),
  getDetailGradeCount: () => state.detailGrade,
  getProgramPagesCount: () => state.programPages,
  getSiteMeta: () => state.meta,
  getFlowsCount: () => state.flows,
  getFlowsOutsideBridgeCount: () => state.flowsOutsideBridge,
  getFlowChartMeta: () => ({ bridge: state.bridge }),
}));

import {
  getCorpus,
  corpusStatement,
  getCrosswalkCounts,
  crosswalkValue,
  CROSSWALK_COUNT_IDS,
} from "@/lib/corpus";
import { getFlowChartMeta } from "@/lib/data";

const SCOPE =
  "excludes personnel, O&M, and R-1/P-1 lines that lack R-2/P-40 project detail";

function reset() {
  state.detailGrade = 1739;
  state.programs = 1741;
  state.programPages = 1993;
  state.meta = {
    counts: { agencies: 23, citations: 1, companies: 200, programs: 1741, program_pages: 1993 },
    corpus_scope: SCOPE,
  };
  state.flows = 200;
  state.flowsOutsideBridge = 34;
  state.bridge = { universePeCount: 444, crosswalkedPeCount: 384, highConfidencePeCount: 240 };
}

beforeEach(reset);

describe("corpusStatement", () => {
  it("states both universes with thousands separators and the scope tail", () => {
    expect(corpusStatement(1993, 1741, SCOPE)).toBe(
      "1,993 browsable program pages; 1,741 of them carry detail-grade R-2/P-40 J-book data — " +
        SCOPE +
        ".",
    );
  });

  it("matches the datatruth gate's leg-d regex (gate and component share the shape)", () => {
    // Keep in sync with scripts/gates/datatruth.mjs CORPUS_RE.
    const CORPUS_RE =
      /([\d,]+)\s+browsable program pages;\s*([\d,]+)\s+of them carry detail-grade/i;
    const m = corpusStatement(1993, 1741, SCOPE).match(CORPUS_RE);
    expect(m).not.toBeNull();
    expect(m![1]).toBe("1,993");
    expect(m![2]).toBe("1,741");
  });
});

describe("getCorpus", () => {
  it("derives both numbers from build data, never a literal", () => {
    state.programPages = 2100;
    state.detailGrade = 1800;
    state.meta = { counts: { program_pages: 2100 }, corpus_scope: SCOPE };
    const c = getCorpus();
    expect(c.programPages).toBe(2100);
    expect(c.detailPages).toBe(1800);
    expect(c.statement).toContain("2,100 browsable program pages");
    expect(c.statement).toContain("1,800 of them carry detail-grade");
  });

  it("uses the build's scope wording verbatim (shared with the §P0-5 hero)", () => {
    expect(getCorpus().scope).toBe(SCOPE);
    expect(getCorpus().statement.endsWith(SCOPE + ".")).toBe(true);
  });

  it("throws when site_meta's declared page count disagrees with the sidecars", () => {
    state.meta = { counts: { program_pages: 1900 }, corpus_scope: SCOPE };
    expect(() => getCorpus()).toThrow(/program_pages=1900 but 1993/);
  });

  it("tolerates a pre-Sprint-2 export with no declared page count", () => {
    state.meta = { counts: {}, corpus_scope: SCOPE };
    expect(getCorpus().programPages).toBe(1993);
  });

  it("throws when the detail tier is not a subset of the page universe", () => {
    state.detailGrade = 2000;
    state.meta = { counts: {}, corpus_scope: SCOPE };
    expect(() => getCorpus()).toThrow(/exceeds total program pages/);
  });

  it("throws on a degenerate (empty) corpus rather than rendering '0 pages'", () => {
    state.programPages = 0;
    state.meta = { counts: {}, corpus_scope: SCOPE };
    expect(() => getCorpus()).toThrow(/degenerate corpus/);
  });

  it("throws when the export predates corpus_scope rather than inventing wording", () => {
    state.meta = { counts: { program_pages: 1993 } };
    expect(() => getCorpus()).toThrow(/no corpus_scope/);
  });
});

describe("getCrosswalkCounts", () => {
  it("declares every crosswalk count the site publishes, each with what one unit is", () => {
    const rows = getCrosswalkCounts();
    expect(rows.map((r) => r.id)).toEqual([...CROSSWALK_COUNT_IDS]);
    const byId = Object.fromEntries(rows.map((r) => [r.id, r.value]));
    expect(byId["link-universe"]).toBe(444);
    expect(byId["bridged-request"]).toBe(384);
    expect(byId["high-confidence-links"]).toBe(240);
    expect(byId["district-linkable"]).toBe(200);
    expect(byId["district-linkable-unbridged"]).toBe(34);
    for (const r of rows) expect(r.counts.length).toBeGreaterThan(30);
  });

  it("recomputes on every call — a mutated fixture must be seen", () => {
    expect(getCrosswalkCounts().find((r) => r.id === "district-linkable")!.value).toBe(200);
    state.flows = 201;
    expect(getCrosswalkCounts().find((r) => r.id === "district-linkable")!.value).toBe(201);
  });

  it("throws when the bridged count exceeds the universe it is drawn from", () => {
    state.bridge = { universePeCount: 380, crosswalkedPeCount: 384, highConfidencePeCount: 240 };
    expect(() => getCrosswalkCounts()).toThrow(/bridged-request/);
  });

  it("throws when the high-confidence tier exceeds the bridged set", () => {
    state.bridge = { universePeCount: 444, crosswalkedPeCount: 240, highConfidencePeCount: 384 };
    expect(() => getCrosswalkCounts()).toThrow(/high-confidence-links/);
  });

  it("does NOT compare district-linkable with high-confidence-links", () => {
    // 34 sidecar programs carry no FY2026 request dollars, so the district
    // tier is not a subset of the bridged high tier (240). A gate that
    // asserted it would be asserting a coincidence.
    state.flows = 300;
    expect(() => getCrosswalkCounts()).not.toThrow();
  });

  it("throws when district-linkable exceeds the whole link universe", () => {
    state.flows = 500;
    expect(() => getCrosswalkCounts()).toThrow(/district-linkable/);
  });
});

describe("crosswalkValue", () => {
  it("is the one way a page reads a crosswalk count", () => {
    expect(crosswalkValue("high-confidence-links")).toBe(240);
    expect(crosswalkValue("district-linkable")).toBe(200);
  });

  /**
   * THE DIVERGENCE THIS CLOSES. /methodology/ rendered
   * `flowMeta.bridge.highConfidencePeCount` straight off the meta while
   * /coverage/ rendered the same figure out of the registry — two reads of one
   * number, which is the shape the crosswalk-count registry exists to remove.
   * The page now goes through the registry, and this pins that the registry's
   * `high-confidence-links` row IS that field: re-point the row at any other
   * source and the page silently starts rendering a different digit than it
   * did, which fails here instead.
   */
  it("keeps high-confidence-links bound to the bridge band /methodology/ used to read", () => {
    state.bridge = { universePeCount: 444, crosswalkedPeCount: 384, highConfidencePeCount: 191 };
    expect(crosswalkValue("high-confidence-links")).toBe(191);
    expect(crosswalkValue("high-confidence-links")).toBe(
      getFlowChartMeta().bridge.highConfidencePeCount,
    );
  });

  it("throws on an id the registry does not publish, rather than rendering a blank", () => {
    expect(() => crosswalkValue("no-such-count")).toThrow();
  });
});
