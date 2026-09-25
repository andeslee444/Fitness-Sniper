/**
 * Unit tests for gate 24 leg (q) — the announcement LLM-alias pass's published
 * scope and its own measured precision (ROADMAP findings log :118-119).
 *
 * THE DEFECT THIS PINS. /methodology/ stated "the 3,840 unmatched records that
 * carry about 88% of the residue by announced value; the 12,811 smaller records
 * carrying the remaining ~12% were not attempted" — four literals typed
 * 2026-09-02, describing a residue whose selection code was never committed.
 * Every gate was green. The leg below recomputes each figure from
 * site_meta.announcement_llm_scope and requires the rendered paragraph to state
 * it, and — symmetrically — requires NO paragraph when no pass is recorded.
 *
 * THE SECOND HALF (2026-09-19). The pass's newest round is measured by its OWN
 * held-out sample, not by the tier-wide study, which was drawn before those
 * links existed. The leg binds that pair in the same slot order as the counts,
 * and fails a paragraph that states a pair the block does not carry — the one
 * way a reader could be handed another population's precision.
 *
 * FIX ROUND 1. Three properties the first version claimed and did not have,
 * each with its own proof-it-can-fail test below: the figures are bound to
 * their own CLAUSES and to their render ORDER (two swapped between clauses
 * used to pass, because both strings were still present); a number the block
 * does not carry FAILS; an absent block fails instead of passing with a note.
 * And one the page did not have: the tier-wide figure's draw predates the
 * links this pass added to the tier, and [data-announcement-draw-gap] must
 * say how many.
 *
 * FULL.records_attempted is deliberately NOT equal to records_residue, so a
 * stale attempted-count is a figure the paragraph genuinely fails to contain.
 *
 * Corpora are injected (like link-precision.test.mjs), so no build is needed.
 * Run via `npm test` (vitest) from site/.
 */
import { describe, it, expect } from "vitest";
import { runAnnouncementScopeLeg } from "../datatruth.mjs";

const FULL = {
  as_of: "2026-09-19",
  records_total: 32852,
  records_deterministic: 4508,
  records_residue: 28344,
  records_attempted: 26900,
  records_remaining: 1444,
  pct_value_attempted: 97.3,
  pct_value_remaining: 2.7,
  links_new_this_pass: 367,
  precision: { sample_id: "2026-09-12", sampled_at: "2026-09-19", drawn: 60,
               sampled: 55, confirmed: 48 },
};

const DONE = { ...FULL, records_attempted: 28344, records_remaining: 0,
               pct_value_attempted: 100, pct_value_remaining: 0 };

const UNMEASURED = { ...FULL, precision: null };

/** The tier-wide block, which carries the draw the announcement tier's own
 *  figure is pinned to — the date the frame clause has to name. */
const TIER = {
  rubric: "attribution",
  methods: {
    "announcement+lexicon": { confirmed: 56, sampled: 60,
                              sample_id: "2026-09-04", judged: "2026-09-04" },
  },
  unmeasured: [],
};

/** The clause inside [data-link-precision] that discloses the frame. */
const gapText =
  "The announcement tier's figure comes from the 2026-09-04 draw, which " +
  "predates 367 of the links now publishing under that tier: the LLM-alias " +
  "pass's most recent round added them, and the round's own held-out sample " +
  "above measures its links instead.";

const meta = (scope, extra = {}) => ({
  announcement_llm_scope: scope, link_precision: TIER, ...extra,
});

const head =
  "Scope of the announcement path: deterministic name matching covered all " +
  "32,852 archived announcement records that join the award lake; 4,508 named " +
  "a program a J-book narrative owns. Of the 28,344 that did not, ";

const measured =
  " Its most recent round carries its own measurement: two independent " +
  "reviewers judged a random draw of 60 of its links, recorded 2026-09-19, " +
  "and confirmed 48 of the 55 that publish — the others no longer publish " +
  "and count in neither direction; those links only, not the path as a whole.";

const fullText = head +
  "26,900 have been through an LLM-assisted alias pass — 97.3% of the residue " +
  "by announced value; the remaining 1,444 records (2.7% of that value) were " +
  "not attempted." + measured;

const doneText = head +
  "28,344 have been through an LLM-assisted alias pass — 100% of the residue " +
  "by announced value; none is left unattempted." + measured;

const unmeasuredText = head +
  "26,900 have been through an LLM-assisted alias pass — 97.3% of the residue " +
  "by announced value; the remaining 1,444 records (2.7% of that value) were " +
  "not attempted. Its most recent round has not yet been measured on a " +
  "held-out sample of its own.";

describe("gate 24 leg q — announcement LLM-pass scope", () => {
  it("passes when every rendered figure matches site_meta", () => {
    const errors = [], notes = [];
    runAnnouncementScopeLeg(errors, notes, {
      siteMeta: meta(FULL), drawGapText: gapText, paragraphText: fullText,
    });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toContain("leg q");
  });

  it("passes on a completed pass that claims nothing is left", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(DONE), drawGapText: gapText, paragraphText: doneText,
    });
    expect(errors).toEqual([]);
  });

  it("FAILS when the page keeps a stale record count", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText,
      // the 2026-09-02 literal, left behind after a fuller pass
      paragraphText: fullText.replace("26,900 have been", "3,840 have been"),
    });
    expect(errors.join(" ")).toMatch(/26,900/);
  });

  it("FAILS when the page keeps a stale percentage", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText,
      paragraphText: fullText.replace("97.3% of the residue", "88% of the residue"),
    });
    expect(errors.join(" ")).toMatch(/97\.3%/);
  });

  it("FAILS when a partial pass does not say what was not attempted", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText,
      paragraphText: fullText
        .replace("the remaining 1,444 records (2.7% of that value) were not " +
                 "attempted.",
                 "the remaining 1,444 records (2.7% of that value) are queued."),
    });
    expect(errors.join(" ")).toMatch(/1,444/);
  });

  it("FAILS when a completed pass still says records were not attempted", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(DONE), drawGapText: gapText,
      paragraphText: doneText.replace("none is left unattempted.",
        "the remaining records were not attempted."),
    });
    expect(errors.join(" ")).toMatch(/not attempted/i);
  });

  it("FAILS when the paragraph renders and site_meta carries no pass", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta({}), paragraphText: fullText,
    });
    expect(errors.join(" ")).toMatch(/renders anyway, from nothing/);
  });

  it("FAILS on an empty block rather than passing with a note", () => {
    // Fix round 1, minor 4. A pass IS recorded (since 2026-09-19), so the only
    // way here is a stale export or a database restored without
    // announcement_llm_scope — and the page has silently dropped the
    // disclosure. The dated-floor idiom of leg p2 / leg p3 / leg r.
    const errors = [], notes = [];
    runAnnouncementScopeLeg(errors, notes, {
      siteMeta: {}, paragraphText: null,
    });
    expect(errors.join(" ")).toMatch(/carries no pass.*2026-09-19/s);
    expect(notes).toEqual([]);
  });

  it("FAILS when site_meta carries a pass and the paragraph is missing", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText, paragraphText: null,
    });
    expect(errors.join(" ")).toMatch(/\[data-announcement-scope\]/);
  });

  it("FAILS when /methodology/ is not built, like leg n does", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText, paragraphText: null,
      methodologyBuilt: false,
    });
    expect(errors.join(" ")).toMatch(/not built/);
  });

  // ── the pass's own precision pair ────────────────────────────────────────

  it("FAILS when the rendered pair is not the measured one", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText,
      // the tier-wide figure, which was sampled before these links existed
      paragraphText: fullText.replace("48 of the 55", "56 of the 60"),
    });
    expect(errors.join(" ")).toMatch(/48 of the 55/);
  });

  it("FAILS when the rendered judged date is not the measured one", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText,
      paragraphText: fullText.replace("recorded 2026-09-19", "recorded 2026-09-04"),
    });
    expect(errors.join(" ")).toMatch(/2026-09-19/);
  });

  it("passes when no sample has measured the newest round and the page says so", () => {
    const errors = [], notes = [];
    runAnnouncementScopeLeg(errors, notes, {
      siteMeta: meta(UNMEASURED), drawGapText: gapText, paragraphText: unmeasuredText,
    });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toMatch(/not measured/);
  });

  it("FAILS when no sample has measured the newest round and the page states a pair anyway", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(UNMEASURED), drawGapText: gapText, paragraphText: fullText,
    });
    expect(errors.join(" ")).toMatch(/no held-out sample|not yet measured/i);
  });

  it("FAILS when a measured round is described as unmeasured", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText, paragraphText: unmeasuredText,
    });
    expect(errors.join(" ")).toMatch(/not yet measured/i);
  });

  it("FAILS on a half-written precision block rather than skipping the pair", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta({ ...FULL, precision: { sample_id: "2026-09-12", sampled: 55 } }),
      drawGapText: gapText,
      paragraphText: fullText,
    });
    expect(errors.join(" ")).toMatch(/precision/i);
  });

  // ── fix round 1: slots, order, strays, and the frame ────────────────────

  it("FAILS when two figures are swapped between their clauses", () => {
    // PROOF IT CAN FAIL. Both strings are still in the paragraph — the old
    // `includes()` sweep passed this exactly, and the page published "26,900
    // … 2.7% of the residue by announced value … 1,444 records (97.3% of that
    // value)".
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText,
      paragraphText: fullText
        .replace("97.3% of the residue", "2.7% of the residue")
        .replace("(2.7% of that value)", "(97.3% of that value)"),
    });
    expect(errors.join(" ")).toMatch(/97\.3%/);
  });

  it("FAILS when records_deterministic and records_attempted change places", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText,
      paragraphText: fullText
        .replace("4,508 named a program", "26,900 named a program")
        .replace("26,900 have been through", "4,508 have been through"),
    });
    expect(errors.join(" ")).toMatch(/records_attempted|records_deterministic/);
  });

  it("FAILS on a number the block does not carry", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText,
      paragraphText: fullText.replace(
        "not attempted.",
        "not attempted, and 156 chunks are still queued.",
      ),
    });
    expect(errors.join(" ")).toMatch(/156/);
  });

  it("FAILS when the draw size is not the one the sample holds", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: gapText,
      paragraphText: fullText.replace("draw of 60 of its links",
                                      "draw of 55 of its links"),
    });
    expect(errors.join(" ")).toMatch(/precision\.drawn/);
  });

  it("FAILS when the tier's draw predates links and nothing says so", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), drawGapText: null, paragraphText: fullText,
    });
    expect(errors.join(" ")).toMatch(/data-announcement-draw-gap/);
    // No link_adjudication block to size the tier: no share is printed.
    expect(errors.join(" ")).toMatch(/part of which the draw could not reach/);
  });

  it("…and prints the unreached share from site_meta, never a typed one", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL, {
        link_adjudication: {
          by_method: { "announcement+lexicon": { published: 1075, adjudicated: 2 } },
        },
      }),
      drawGapText: null,
      paragraphText: fullText,
    });
    // chain C run 4 (2026-09-25): 367 of 1,075 → 34%.
    expect(errors.join(" ")).toMatch(
      /34% of which \(367 of the tier's 1,075 published links, link_adjudication\.by_method\) the draw could not reach/,
    );
    expect(errors.join(" ")).not.toMatch(/a third/);
  });

  it("FAILS when the frame clause states a count site_meta does not carry", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), paragraphText: fullText,
      drawGapText: gapText.replace("predates 367 of the links",
                                   "predates 708 of the links"),
    });
    expect(errors.join(" ")).toMatch(/367/);
  });

  it("FAILS when the frame clause names another draw than the pinned one", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta(FULL), paragraphText: fullText,
      drawGapText: gapText.replace("2026-09-04 draw", "2026-09-12 draw"),
    });
    expect(errors.join(" ")).toMatch(/2026-09-04 draw/);
  });

  it("passes with no frame clause when this pass added no tier link", () => {
    const errors = [], notes = [];
    runAnnouncementScopeLeg(errors, notes, {
      siteMeta: meta({ ...FULL, links_new_this_pass: 0 }),
      paragraphText: fullText, drawGapText: null,
    });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).not.toMatch(/draw-gap/);
  });

  it("FAILS when a frame clause renders and site_meta carries no such count", () => {
    const errors = [];
    runAnnouncementScopeLeg(errors, [], {
      siteMeta: meta({ ...FULL, links_new_this_pass: null }),
      paragraphText: fullText, drawGapText: gapText,
    });
    expect(errors.join(" ")).toMatch(/links_new_this_pass/);
  });
});
