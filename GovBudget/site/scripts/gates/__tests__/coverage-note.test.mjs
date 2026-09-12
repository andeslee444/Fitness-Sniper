/**
 * Unit tests for gate 21 leg (o) — the coverage note tells the truth about
 * ingestion, on every tier (ROADMAP #14).
 *
 * Three defects this leg exists to catch, each of which has actually
 * shipped:
 *   1. 2026-07-05 — a hardcoded A/N/F set made ~24 defense-wide agency
 *      pages say "not yet ingested" about a book that WAS loaded;
 *   2. 2026-09-10 — the honest wording only existed on the rollup branch,
 *      so 0603115DHA and 0708083D (full tier, no detail at all) asserted a
 *      J-book detail that does not exist;
 *   3. the inverse of (1), which registering a book without extracting it
 *      would have caused: a page saying "the book IS ingested" for an org
 *      with no loaded detail.
 *
 * The corpus is injected (sidecars, programs, ingestedOrgs, pages) so the
 * tests never touch site/out or data/site — and, following
 * split-key-awards.test.mjs, the injected corpus SATISFIES the leg's
 * non-vacuity floor rather than dodging it. Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import { runCoverageNoteLeg } from "../program-skeleton.mjs";

const INGESTED = ["A", "N", "F", "OSD"];

/** Verbatim ServiceBooksNote output (src/components/service-books-note.tsx). */
const UNINGESTED_NOTE = (svc) =>
  `<p data-coverage="service-books" data-section-empty>Detailed justification for this program lives in the ${svc} J-book, which is not yet ingested — see <a href="/methodology/#coverage-service-books">roadmap</a>.</p>`;
const INGESTED_NOTE = (svc) =>
  `<p data-coverage="service-books" data-section-empty>The ${svc} FY2026 J-books are ingested, but this program element carries no R-2/P-40 narrative in them — only its cited R-1/P-1 workbook figures are shown. See <a href="/methodology/#coverage-service-books">roadmap</a>.</p>`;
const FULL_TIER_SENTENCE =
  "<p data-section-empty>The J-book detail for this line carries no separate mission or description narrative — see the justification and line items below for its own prose.</p>";

/** Measured 2026-09-10 from data/site/json/program_details: 1,936 non-decade
 *  pages carry detail and/or a narrative, 73 are workbook-only, 553 decade. */
const DETAIL_PAGES = 1936;

function liveShape() {
  const sidecars = new Map();
  const programs = [];
  const pages = new Map();

  const wb = (org, tier) => ({
    details: [],
    narratives: [],
    budget_lines: [{}],
    ...(tier ? { tier, service_org: org } : {}),
  });

  sidecars.set("R-ING", wb("A", "rollup"));
  pages.set("R-ING", INGESTED_NOTE("Army"));
  sidecars.set("R-UNING", wb("DHA", "rollup"));
  pages.set("R-UNING", UNINGESTED_NOTE("DHA"));
  sidecars.set("F-WBONLY", wb("DHA"));
  programs.push({ pe_bli: "F-WBONLY", slug: "F-WBONLY", org: "DHA" });
  pages.set("F-WBONLY", UNINGESTED_NOTE("DHA"));

  // the negative direction, at the measured population. F-DETAIL1 keeps the
  // full-tier sentence, which is TRUE for a page that has detail — the leg
  // must not flag it.
  for (let i = 0; i < DETAIL_PAGES; i++) {
    const slug = `F-DETAIL${i}`;
    sidecars.set(slug, {
      details: [{}],
      narratives: i % 2 ? [{}] : [],
      budget_lines: [{}],
    });
    programs.push({ pe_bli: slug, slug, org: i % 3 ? "A" : "N" });
    pages.set(slug, i === 1 ? FULL_TIER_SENTENCE : "<p>real prose</p>");
  }

  // a decade page — its own tier, its own wording (leg k)
  sidecars.set("D-ONLY", {
    tier: "decade",
    details: [],
    narratives: [],
    budget_lines: [],
  });
  pages.set("D-ONLY", "<p data-decade-only>history</p>");

  return { sidecars, programs, pages };
}

function run(mutate = () => {}, ingestedOrgs = INGESTED) {
  const corpus = liveShape();
  mutate(corpus);
  const errors = [];
  const notes = [];
  runCoverageNoteLeg({ errors, notes, ingestedOrgs, ...corpus });
  return { errors, notes };
}

describe("leg o — the live shape", () => {
  it("passes and says what it saw", () => {
    const { errors, notes } = run();
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toContain("3 page(s) render the service-books note");
    expect(notes.join(" ")).toContain(`${DETAIL_PAGES} page(s) with detail carry none`);
  });
});

describe("leg o — proof it can fail", () => {
  it("fails when a workbook-only full-tier page asserts a J-book detail (the 0603115DHA bug)", () => {
    const { errors } = run((c) => c.pages.set("F-WBONLY", FULL_TIER_SENTENCE));
    expect(errors.join("\n")).toMatch(/F-WBONLY/);
    expect(errors.join("\n")).toMatch(/no R-2\/P-40 detail/);
  });

  it("fails when a page says 'not yet ingested' about a LOADED book (the 2026-07-05 species)", () => {
    const { errors } = run((c) => c.pages.set("R-ING", UNINGESTED_NOTE("Army")));
    expect(errors.join("\n")).toMatch(/R-ING/);
    expect(errors.join("\n")).toMatch(/loaded set/);
  });

  it("fails when a page says the book IS ingested for an org with no loaded detail", () => {
    const { errors } = run((c) => c.pages.set("R-UNING", INGESTED_NOTE("DHA")));
    expect(errors.join("\n")).toMatch(/R-UNING/);
    // The leg emphasises the direction — "IS in the loaded set" on the
    // 2026-07-05 branch above, "is NOT in the loaded set" here — so this
    // regex carries the emphasis rather than matching either message.
    expect(errors.join("\n")).toMatch(/NOT in the loaded set/);
  });

  it("fails when a page WITH detail renders the coverage note anyway", () => {
    const { errors } = run((c) => c.pages.set("F-DETAIL0", INGESTED_NOTE("Army")));
    expect(errors.join("\n")).toMatch(/F-DETAIL0/);
  });

  it("fails when the note names an org the page does not belong to", () => {
    const { errors } = run((c) => c.pages.set("F-WBONLY", UNINGESTED_NOTE("Navy")));
    expect(errors.join("\n")).toMatch(/F-WBONLY/);
  });

  it("fails loudly when the ingested-org payload is empty — the leg would be reading the wrong set", () => {
    const { errors } = run(() => {}, []);
    expect(errors.join("\n")).toMatch(/ingested_service_orgs/);
  });

  it("fails when the detail-page population collapses — the leg would be vacuous", () => {
    const { errors } = run((c) => {
      for (let i = 500; i < DETAIL_PAGES; i++) c.sidecars.delete(`F-DETAIL${i}`);
    });
    expect(errors.join("\n")).toMatch(/do not lower the floor/);
  });
});
