/**
 * Unit tests for gate 24 leg (o) — per-award hand-adjudication coverage
 * (ROADMAP #109).
 *
 * THE DEFECT THESE PIN. /methodology/ opened its "Budget-to-contract links"
 * section with "As of September 2026, every published link was individually
 * hand-adjudicated: each award's contract descriptions were investigated
 * against the program's J-book narratives and project titles, and every
 * proposed program-level link was then challenged by two independent
 * adversarial reviewers — a link is published as high only if neither could
 * refute it." Measured 2026-09-11: 9,587 of the 12,595 links the crosswalk
 * grades high or medium carry an `award_pe_adjudications` row at all (three
 * of the five published methods carry NONE), 8,474 of those adjudications
 * found work that could not be pinned to any one program element, and 60 rows
 * in the whole table record both adversarial lenses (57 on a published link).
 *
 * Nothing could catch it: the sentence held no number, so no number could
 * disagree with it. The leg's answer is that the sentence now holds three
 * derived numbers and may hold no others.
 *
 * Corpora are injected (as link-precision.test.mjs injects its own) so the
 * tests do not depend on a build.
 *
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import { runLinkAdjudicationLeg } from "../datatruth.mjs";

/** site_meta.link_adjudication as export_site._link_adjudication_block
 *  returns it against the live warehouse (read off the block on 2026-09-11,
 *  not typed from the page). */
const LIVE_META = {
  link_adjudication: {
    as_of: "2026-09-01",
    published: 12595,
    adjudicated: 9587,
    unpinned: 8474,
    unpinned_tier: "medium",
    by_method: {
      "account+subagency": { published: 9337, adjudicated: 9173 },
      "account+tokens": { published: 527, adjudicated: 414 },
      "announcement+lexicon": { published: 708, adjudicated: 0 },
      "fpds-ap": { published: 1910, adjudicated: 0 },
      "subaward+lexicon": { published: 113, adjudicated: 0 },
    },
    adjudicated_methods: ["account+subagency", "account+tokens"],
    unadjudicated_methods: ["announcement+lexicon", "fpds-ap", "subaward+lexicon"],
  },
};

/** The passage /methodology/ renders for LIVE_META, as the leg reads it
 *  (node-html-parser text, whitespace normalised). */
const LIVE_PASSAGE =
  "As of 2026-09-01, 9,587 of the 12,595 links the crosswalk grades high or " +
  "medium carry a per-award hand adjudication, each recording which program " +
  "elements, if any, the award's own contract record supports. 8,474 of " +
  "those found work that could not be pinned to any one program element; " +
  "those links publish at medium. The announcement+lexicon, fpds-ap and " +
  "subaward+lexicon paths carry no per-link adjudication — their precision " +
  "is sampled instead (below).";

function run({ siteMeta, passageText, methodologyBuilt }) {
  const errors = [];
  const notes = [];
  runLinkAdjudicationLeg(errors, notes, { siteMeta, passageText, methodologyBuilt });
  return { errors, notes };
}

describe("gate 24 leg o — the live shape", () => {
  it("passes on the corpus this branch ships", () => {
    const { errors, notes } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE,
    });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toMatch(/9,587 of 12,595 links adjudicated/);
    expect(notes.join(" ")).toMatch(/3 unadjudicated path\(s\)/);
  });
});

describe("gate 24 leg o — a figure that drifts from the block", () => {
  it("FAILS when the passage states a coverage number site_meta does not hold", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE.replace("9,587", "12,000"),
    });
    expect(errors.join("\n")).toMatch(/never states adjudicated = 9,587/);
    expect(errors.join("\n")).toMatch(/states "12,000", which is not a figure/);
  });

  it("FAILS when a number is typed back into the prose beside the derived ones", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText:
        LIVE_PASSAGE.replace(
          "per-award hand adjudication,",
          "per-award hand adjudication challenged by 2 adversarial reviewers,",
        ),
    });
    expect(errors.join("\n")).toMatch(/states "2", which is not a figure/);
  });

  it("FAILS when the passage carries no date for the coverage claim", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE.replace("As of 2026-09-01, ", ""),
    });
    expect(errors.join("\n")).toMatch(/does not carry as_of "2026-09-01"/);
  });
});

describe("gate 24 leg o — an unadjudicated evidence path must be named", () => {
  it("FAILS when a path with zero adjudications goes unnamed", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE.replace("fpds-ap and ", ""),
    });
    expect(errors.join("\n")).toMatch(
      /"fpds-ap" publishes links and carries NO adjudication row/,
    );
  });

  it("FAILS when the block leaves an unadjudicated method off its own list", () => {
    const meta = {
      link_adjudication: {
        ...LIVE_META.link_adjudication,
        unadjudicated_methods: ["announcement+lexicon", "subaward+lexicon"],
      },
    };
    const { errors } = run({ siteMeta: meta, passageText: LIVE_PASSAGE });
    expect(errors.join("\n")).toMatch(/fpds-ap carries no adjudication but is missing/);
  });
});

describe("gate 24 leg o — presence is tied to the measurement", () => {
  it("FAILS when the sentence renders with no block behind it (the old claim)", () => {
    const { errors } = run({
      siteMeta: {},
      passageText:
        "As of September 2026, every published link was individually " +
        "hand-adjudicated.",
    });
    expect(errors.join("\n")).toMatch(/renders while site_meta.link_adjudication is empty/);
  });

  it("passes silently on a corpus with no adjudication and no sentence", () => {
    const { errors, notes } = run({ siteMeta: {}, passageText: null });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toMatch(/nothing adjudicated yet/);
  });

  it("FAILS when the block has coverage but the sentence is gone", () => {
    const { errors } = run({ siteMeta: LIVE_META, passageText: null });
    expect(errors.join("\n")).toMatch(/no \[data-link-adjudication\] passage renders/);
  });
});

describe("gate 24 leg o — the block against itself", () => {
  it("FAILS when by_method does not sum to the headline counts", () => {
    const meta = {
      link_adjudication: {
        ...LIVE_META.link_adjudication,
        by_method: {
          ...LIVE_META.link_adjudication.by_method,
          "fpds-ap": { published: 1, adjudicated: 0 },
        },
      },
    };
    const { errors } = run({ siteMeta: meta, passageText: LIVE_PASSAGE });
    expect(errors.join("\n")).toMatch(/published is 12595 but by_method sums to 10686/);
  });

  it("FAILS when more links are adjudicated than exist", () => {
    const meta = {
      link_adjudication: {
        ...LIVE_META.link_adjudication,
        published: 9000,
        by_method: {},
      },
    };
    const { errors } = run({
      siteMeta: meta,
      passageText: LIVE_PASSAGE.replace("12,595", "9,000"),
    });
    expect(errors.join("\n")).toMatch(/is inverted/);
  });
});
