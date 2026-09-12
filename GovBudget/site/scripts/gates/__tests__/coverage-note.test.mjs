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
/** The OTHER withdrawn full-tier empty state — the Justification section's.
 *  Both literals in WITHDRAWN_FULL_TIER_SENTENCES are exercised below; a
 *  literal no test ever trips is a literal that can rot silently. */
const WITHDRAWN_JUSTIFICATION_SENTENCE =
  "<p data-section-empty>No accomplishments or planned-program narratives in this line's J-book detail — some exhibits carry figures without per-project prose.</p>";

/** Re-measured 2026-09-12 from data/site/json/program_details (2,562 sidecars):
 *  1,936 non-decade pages carry detail and/or a narrative, 73 are workbook-only,
 *  553 decade — unchanged from the 2026-09-10 reading. Matches the leg's own
 *  MIN_DETAIL_PAGES_CHECKED note. */
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

  // Check 4 in isolation. The 0603115DHA test above REPLACES the note with the
  // withdrawn sentence, so the leg stops at check 1 ("renders no note") and
  // check 4 never runs — it had no proof-it-can-fail test at all. Here the page
  // keeps an otherwise-correct note and ALSO carries a withdrawn sentence, so
  // checks 1/2/3 all pass and the only error that can appear is check 4's.
  it.each([
    ["the Description empty state", FULL_TIER_SENTENCE,
     "The J-book detail for this line carries no separate mission"],
    ["the Justification empty state", WITHDRAWN_JUSTIFICATION_SENTENCE,
     "some exhibits carry figures without per-project prose"],
  ])(
    "fails when a correctly-noted page ALSO carries %s",
    (_label, withdrawnHtml, literal) => {
      const { errors, notes } = run((c) =>
        c.pages.set("F-WBONLY", UNINGESTED_NOTE("DHA") + withdrawnHtml),
      );
      const own = errors.filter((e) => e.startsWith("program-skeleton(o)"));
      expect(own).toHaveLength(1); // exactly one — checks 1/2/3 are satisfied
      expect(own[0]).toContain("F-WBONLY");
      expect(own[0]).toContain(literal);
      expect(own[0]).toContain("claims a detail record behind the page");
      // and the summary must not report the run as clean (minor 3)
      expect(notes.join(" ")).not.toContain("✓");
      expect(notes.join(" ")).toContain("1 withdrawn sentence(s)");
    },
  );

  it("keeps the ✓ off the summary only when check 4 is the sole failure", () => {
    // the control for the assertion above: an untouched run DOES print ✓
    expect(run().notes.join(" ")).toContain("✓");
  });

  it("fails when the detail-page population collapses — the leg would be vacuous", () => {
    const { errors } = run((c) => {
      for (let i = 500; i < DETAIL_PAGES; i++) c.sidecars.delete(`F-DETAIL${i}`);
    });
    expect(errors.join("\n")).toMatch(/do not lower the floor/);
  });
});
