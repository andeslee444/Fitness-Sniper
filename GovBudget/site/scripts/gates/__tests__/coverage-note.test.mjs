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
 *      with no loaded detail;
 *   4. 2026-09-12 (Task 17c, ROADMAP #111) — "not yet ingested" presupposes a
 *      book exists. No FY2026 RDT&E or procurement justification book was
 *      published for the DoD IG at all, none is published for DEFW's
 *      reconciliation / undistributed / roll-up rows, and the DHA book WAS
 *      downloaded and carries no jb-2009 payload. site_meta.org_absences
 *      records each case; a page whose org is in it must state that rule on
 *      BOTH surfaces (the note and the justification section) and must not
 *      say "not yet ingested" anywhere — the phrase also renders in the
 *      WHAT-IT-IS card tail and in <meta name="description">.
 *
 * The corpus is injected (sidecars, programs, ingestedOrgs, pages) so the
 * tests never touch site/out or data/site — and, following
 * split-key-awards.test.mjs, the injected corpus SATISFIES the leg's
 * non-vacuity floor rather than dodging it. Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import { ABSENCE_MARKERS, runCoverageNoteLeg } from "../program-skeleton.mjs";

const INGESTED = ["A", "N", "F", "OSD"];

/** site_meta.org_absences, one entry per rule — the live FY2026 shape
 *  (export_site._org_absences over data/research/edition_manifest.json). */
const ABSENCES = {
  DHA: {
    rule: "book-carries-no-embedded-xml",
    checked_on: "2026-09-12",
    checked_url: "https://comptroller.war.gov/…/00-DHP_Vols_I_and_II_PB26.pdf",
  },
  DEFW: {
    rule: "summary-line-only",
    checked_on: "2026-09-12",
    checked_url: "https://comptroller.war.gov/Budget-Materials/",
  },
  IG: {
    rule: "no-justification-book-published",
    checked_on: "2026-09-12",
    checked_url: "https://comptroller.war.gov/Budget-Materials/",
  },
};

/** Verbatim ServiceBooksNote output (src/components/service-books-note.tsx). */
const UNINGESTED_NOTE = (svc) =>
  `<p data-coverage="service-books" data-section-empty>Detailed justification for this program lives in the ${svc} J-book, which is not yet ingested — see <a href="/methodology/#coverage-service-books">roadmap</a>.</p>`;
const INGESTED_NOTE = (svc) =>
  `<p data-coverage="service-books" data-section-empty>The ${svc} FY2026 J-books are ingested, but this program element carries no R-2/P-40 narrative in them — only its cited R-1/P-1 workbook figures are shown. See <a href="/methodology/#coverage-service-books">roadmap</a>.</p>`;

/** Verbatim orgAbsenceWording output (src/lib/program-tier.ts), per rule.
 *  program-tier.test.ts pins that those sentences contain the markers this
 *  leg matches, so a reworded sentence is a red unit test as well as a red
 *  build. */
const ABSENCE_TEXT = {
  "no-justification-book-published": (svc) => [
    `No FY2026 RDT&E or procurement justification book was published for ${svc} (justification index checked 2026-09-12), so this corpus carries no detailed justification for this program.`,
    `No FY2026 RDT&E or procurement justification book was published for ${svc}, so there are no accomplishments or planned-program narratives to show — see the description note above.`,
  ],
  "summary-line-only": (svc) => [
    `No ${svc}-specific FY2026 justification book is published (justification index checked 2026-09-12) — its workbook rows are reconciliation, undistributed and roll-up summary lines — so this corpus carries no detailed justification for this program.`,
    `No ${svc}-specific FY2026 justification book is published, so there are no accomplishments or planned-program narratives to show — see the description note above.`,
  ],
  "book-carries-no-embedded-xml": (svc) => [
    `The ${svc} FY2026 justification book was downloaded, but its PDF carries no embedded data payload (checked 2026-09-12), so no R-2/P-40 detail could be extracted from it.`,
    `The ${svc} FY2026 justification book was downloaded, but its PDF carries no embedded data payload, so no accomplishments or planned-program narratives could be extracted from it — see the description note above.`,
  ],
};
const ABSENCE_NOTE = (rule, svc) =>
  `<p data-coverage="service-books" data-section-empty>${ABSENCE_TEXT[rule](svc)[0]} See <a href="/methodology/#coverage-service-books">roadmap</a>.</p>`;
/** The justification SECTION, which the leg reads separately — the second
 *  render site of the same decision. */
const JUST_SECTION = (inner) =>
  `<section data-section="justification"><p data-section-empty>${inner}</p></section>`;
const ABSENCE_JUST = (rule, svc) => JUST_SECTION(ABSENCE_TEXT[rule](svc)[1]);
const UNINGESTED_JUST = (svc) =>
  JUST_SECTION(
    `Accomplishments and planned-program narratives live in the ${svc} J-book, which is not yet ingested — see the description note above for the roadmap.`,
  );
const INGESTED_JUST = (svc) =>
  JUST_SECTION(
    `The ${svc} FY2026 J-book is ingested, but this program element carries no matching R-2/P-40 accomplishments or planned-program narrative — see the description note above.`,
  );
/** The whole absence page, both surfaces — what a correct build emits. */
const ABSENCE_PAGE = (rule, svc) =>
  ABSENCE_NOTE(rule, svc) + ABSENCE_JUST(rule, svc);
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

  // A loaded book (Army), and the org's own note.
  sidecars.set("R-ING", wb("A", "rollup"));
  pages.set("R-ING", INGESTED_NOTE("Army") + INGESTED_JUST("Army"));
  // The three recorded absences, one per rule — the live FY2026 shape: DHA's
  // book was downloaded and carries no payload, DEFW publishes none for its
  // summary rows, IG published none at all.
  sidecars.set("R-DHA", wb("DHA", "rollup"));
  pages.set("R-DHA", ABSENCE_PAGE("book-carries-no-embedded-xml", "DHA"));
  sidecars.set("R-DEFW", wb("DEFW", "rollup"));
  pages.set("R-DEFW", ABSENCE_PAGE("summary-line-only", "DEFW"));
  sidecars.set("R-IG", wb("IG", "rollup"));
  pages.set("R-IG", ABSENCE_PAGE("no-justification-book-published", "IG"));
  // The workbook-only FULL-tier page (0603115DHA's shape): no tier key, no
  // service_org, org from programs.json — and an absence, like the real one.
  sidecars.set("F-WBONLY", wb("DHA"));
  programs.push({ pe_bli: "F-WBONLY", slug: "F-WBONLY", org: "DHA" });
  pages.set("F-WBONLY", ABSENCE_PAGE("book-carries-no-embedded-xml", "DHA"));
  // An org with neither a loaded book nor a recorded absence — the ONLY state
  // "not yet ingested" is true of, kept live so both directions of check 3
  // still have a page to read.
  sidecars.set("R-UNPROBED", wb("ZZZ", "rollup"));
  pages.set("R-UNPROBED", UNINGESTED_NOTE("ZZZ") + UNINGESTED_JUST("ZZZ"));
  // 9999999999's shape: a rollup sidecar with an EMPTY service_org, which has
  // no org to probe and reads "the service J-book".
  sidecars.set("R-NOORG", wb("", "rollup"));
  pages.set("R-NOORG", UNINGESTED_NOTE("service") + UNINGESTED_JUST("service"));

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

function run(mutate = () => {}, ingestedOrgs = INGESTED, absences = ABSENCES) {
  const corpus = liveShape();
  const injected = { ingestedOrgs, absences };
  mutate(corpus, injected);
  const errors = [];
  const notes = [];
  runCoverageNoteLeg({ errors, notes, ...injected, ...corpus });
  return { errors, notes };
}

describe("leg o — the live shape", () => {
  it("passes and says what it saw", () => {
    const { errors, notes } = run();
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toContain("7 page(s) render the service-books note");
    // the three branches, counted
    expect(notes.join(" ")).toContain(
      "(1 on a loaded book, 4 on a recorded absence, 2 still \"not yet ingested\")",
    );
    expect(notes.join(" ")).toContain("3 recorded absence(s)");
    // and the breakdown chain C reads, per org and rule
    expect(notes.join(" ")).toContain("DEFW summary-line-only 1");
    expect(notes.join(" ")).toContain("DHA book-carries-no-embedded-xml 2");
    expect(notes.join(" ")).toContain("IG no-justification-book-published 1");
    expect(notes.join(" ")).toContain("unprobed: ZZZ 1");
    expect(notes.join(" ")).toContain("1 with no org code");
    expect(notes.join(" ")).toContain(`${DETAIL_PAGES} page(s) with detail carry none`);
  });
});

describe("the markers legs (c) and (o) share", () => {
  it("each rule's note opens with its marker, so leg (c) accepts the third wording", () => {
    // leg (c) samples 8 rollup pages — head 4 + tail 4 of the sorted slugs —
    // and the tail is RECONCIL1 / RECONCIL2 / UNDISTRIB, all DEFW absence
    // pages. It accepts a note that carries ANY marker in this map; leg (o)
    // decides WHICH one is right. One map, two legs: a rule dropped from it
    // breaks both, visibly, here.
    for (const [rule, marker] of Object.entries(ABSENCE_MARKERS)) {
      expect(ABSENCE_TEXT[rule]("DEFW")[0]).toContain(marker("DEFW"));
      expect(ABSENCE_TEXT[rule]("DEFW")[1]).toContain(marker("DEFW"));
    }
    expect(Object.keys(ABSENCE_MARKERS).sort()).toEqual(
      Object.keys(ABSENCE_TEXT).sort(),
    );
  });
});

describe("leg o — proof it can fail", () => {
  it("fails when a workbook-only full-tier page asserts a J-book detail (the 0603115DHA bug)", () => {
    // the note is REPLACED by the withdrawn sentence — the leg stops at
    // check 1 ("renders no note") before the absence branch is reached.
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
    // R-UNPROBED: no loaded book, no recorded absence — the branch this
    // direction of check 3 still guards.
    const { errors } = run((c) => c.pages.set("R-UNPROBED", INGESTED_NOTE("ZZZ")));
    expect(errors.join("\n")).toMatch(/R-UNPROBED/);
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
    const { errors } = run((c) =>
      c.pages.set("R-UNPROBED", UNINGESTED_NOTE("Navy") + UNINGESTED_JUST("Navy")),
    );
    expect(errors.join("\n")).toMatch(/R-UNPROBED/);
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
        c.pages.set(
          "F-WBONLY",
          ABSENCE_PAGE("book-carries-no-embedded-xml", "DHA") + withdrawnHtml,
        ),
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

  // ── check 6, the Task 17c branch ────────────────────────────────────────
  it("fails when an absence page still says 'not yet ingested' elsewhere on the page", () => {
    // BOTH prose surfaces are correct; the phrase survives in the page's
    // <meta name="description"> — exactly the half-fix the note-only audit of
    // 2026-09-12 would have shipped (the WHAT-IT-IS card tail is the other).
    const { errors } = run((c) =>
      c.pages.set(
        "R-IG",
        '<meta name="description" content="Workbook-tier line: the detailed service J-book is not yet ingested." />' +
          ABSENCE_PAGE("no-justification-book-published", "IG"),
      ),
    );
    const own = errors.filter((e) => e.startsWith("program-skeleton(o)"));
    expect(own).toHaveLength(1);
    expect(own[0]).toContain("R-IG");
    expect(own[0]).toContain("not yet ingested");
    expect(own[0]).toContain("presupposes a book exists");
  });

  it("fails when an absence page keeps the generic 'not yet ingested' note", () => {
    // The pre-17c page, unchanged: IG published no book at all, so this note
    // names one that does not exist.
    const { errors } = run((c) =>
      c.pages.set("R-IG", UNINGESTED_NOTE("IG") + UNINGESTED_JUST("IG")),
    );
    const own = errors.filter((e) => e.startsWith("program-skeleton(o)"));
    expect(own.join("\n")).toMatch(/R-IG/);
    expect(own.join("\n")).toMatch(/has a recorded absence \(no-justification-book-published\)/);
    expect(own.join("\n")).toMatch(/not yet ingested/);
  });

  it("fails when the justification twin was fixed and the description note was not", () => {
    // The mirror of the case below, and the only one that isolates the note
    // check: no banned phrase anywhere and a correct justification section, so
    // the sole error can be the note's. (Without this, disabling the note
    // check leaves every other absence test green — the other errors carry the
    // same slug and rule name.)
    const { errors } = run((c) =>
      c.pages.set(
        "R-DEFW",
        INGESTED_NOTE("DEFW") + ABSENCE_JUST("summary-line-only", "DEFW"),
      ),
    );
    const own = errors.filter((e) => e.startsWith("program-skeleton(o)"));
    expect(own).toHaveLength(1);
    expect(own[0]).toContain("R-DEFW");
    expect(own[0]).toContain("its coverage note does not state it");
  });

  it("fails when the description note was fixed and the justification twin was not", () => {
    // The two-render-site defect in isolation: no banned phrase anywhere, so
    // the ONLY error that can appear is the justification section's.
    const { errors } = run((c) =>
      c.pages.set(
        "R-DEFW",
        ABSENCE_NOTE("summary-line-only", "DEFW") + INGESTED_JUST("DEFW"),
      ),
    );
    const own = errors.filter((e) => e.startsWith("program-skeleton(o)"));
    expect(own).toHaveLength(1);
    expect(own[0]).toContain("R-DEFW");
    expect(own[0]).toContain("not in its justification section");
  });

  it("fails when a page states another org's absence rule", () => {
    // DEFW's page rendering DHA's sentence: fluent, cited-looking, and about
    // a book that is not this org's.
    const { errors } = run((c) =>
      c.pages.set("R-DEFW", ABSENCE_PAGE("book-carries-no-embedded-xml", "DEFW")),
    );
    const own = errors.filter((e) => e.startsWith("program-skeleton(o)"));
    expect(own.join("\n")).toMatch(/R-DEFW/);
    expect(own.join("\n")).toMatch(/summary-line-only/);
  });

  it("fails loudly when the org_absences payload is missing — 19 pages would relapse", () => {
    const { errors } = run(() => {}, INGESTED, null);
    expect(errors.join("\n")).toMatch(/org_absences is absent or not an object/);
    expect(errors.join("\n")).toMatch(/presupposes a book exists/);
  });

  it("fails when an org is recorded as absent AND as loaded", () => {
    const { errors } = run(() => {}, [...INGESTED, "DHA"]);
    expect(errors.join("\n")).toMatch(/"DHA" is in BOTH/);
  });

  it("fails when the payload names a rule the leg has no sentence for", () => {
    const { errors } = run(() => {}, INGESTED, {
      ...ABSENCES,
      IG: { ...ABSENCES.IG, rule: "book-is-classified" },
    });
    expect(errors.join("\n")).toMatch(/carries rule "book-is-classified"/);
  });

  it("fails when the detail-page population collapses — the leg would be vacuous", () => {
    const { errors } = run((c) => {
      for (let i = 500; i < DETAIL_PAGES; i++) c.sidecars.delete(`F-DETAIL${i}`);
    });
    expect(errors.join("\n")).toMatch(/do not lower the floor/);
  });
});
