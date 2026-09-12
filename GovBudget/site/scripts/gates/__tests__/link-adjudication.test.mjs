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
 * in the whole table record both adversarial lenses — 57 of them on a link
 * the crosswalk grades high or medium.
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
    measured_on: "2026-09-11",
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
    unadjudicated_methods: ["announcement+lexicon", "fpds-ap", "subaward+lexicon"],
    high: {
      published_high: 768,
      adjudicated_high: 60,
      two_lens_high: 60,
      by_path: {
        account: { high: 3, adjudicated: 3, two_lens: 3 },
        "account+subagency": { high: 23, adjudicated: 23, two_lens: 23 },
        "account+tokens": { high: 34, adjudicated: 34, two_lens: 34 },
        "announcement+lexicon": {
          high: 708,
          adjudicated: 0,
          two_lens: 0,
          with_match_basis: 384,
        },
      },
    },
  },
};

/** The passage /methodology/ renders for LIVE_META, as the leg reads it
 *  (node-html-parser text, whitespace normalised). */
const LIVE_PASSAGE =
  "As of 2026-09-11, 9,587 of the 12,595 links the crosswalk grades high or " +
  "medium carry a per-award hand adjudication — the most recent made on " +
  "2026-09-01 — each recording which program " +
  "elements, if any, the award's own contract record supports. 8,474 of " +
  "those found work that could not be pinned to any one program element; " +
  "those links publish at medium. The announcement+lexicon, fpds-ap and " +
  "subaward+lexicon paths carry no per-link adjudication — their precision " +
  "is sampled instead (below).";

/** The High-tier census /methodology/ renders inside the tier grading. */
const LIVE_HIGH =
  "60 of the 768 links published at high carry a per-award hand " +
  "adjudication, all 60 of them challenged by two independent adversarial " +
  "reviewers; the other 708 rest on the announcement+lexicon path.";

/** LIVE_META's block with the `high` census removed — the shape a warehouse
 *  with no mart produces (_published_high_links returns null). */
function withoutHighCensus() {
  const block = { ...LIVE_META.link_adjudication };
  delete block.high;
  return block;
}

function run({ siteMeta, passageText, highText, methodologyBuilt }) {
  const errors = [];
  const notes = [];
  runLinkAdjudicationLeg(errors, notes, {
    siteMeta,
    passageText,
    highText: highText === undefined ? LIVE_HIGH : highText,
    methodologyBuilt,
  });
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
          "per-award hand adjudication —",
          "per-award hand adjudication challenged by 2 adversarial reviewers —",
        ),
    });
    expect(errors.join("\n")).toMatch(/states "2", which is not a figure/);
  });

  it("FAILS when the passage carries no date for the coverage claim", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE.replace("As of 2026-09-11, ", ""),
    });
    expect(errors.join("\n")).toMatch(/does not carry measured_on "2026-09-11"/);
  });

  it("FAILS when the last adjudication's date goes unstated", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE.replace(
        " — the most recent made on 2026-09-01 — each",
        ", each",
      ),
    });
    expect(errors.join("\n")).toMatch(/does not carry as_of "2026-09-01"/);
  });

  // C1, the Critical this fix round exists for: the passage used to open
  // "As of {as_of}" over counts taken at export time, and this leg REQUIRED
  // it. On 2026-09-01 the corpus held 9,864 published links; the other 2,731
  // were created 2026-09-04, which is why they carry no adjudication. The
  // ratio 9,587 of 12,595 never held on that date.
  it("FAILS when the census is dated by the last adjudication instead of the run", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText:
        "As of 2026-09-01, 9,587 of the 12,595 links the crosswalk grades " +
        "high or medium carry a per-award hand adjudication — measured " +
        "2026-09-11 — each recording which program elements, if any, the " +
        "award's own contract record supports. 8,474 of those found work " +
        "that could not be pinned to any one program element; those links " +
        "publish at medium. The announcement+lexicon, fpds-ap and " +
        "subaward+lexicon paths carry no per-link adjudication — their " +
        "precision is sampled instead (below).",
    });
    expect(errors.join("\n")).toMatch(
      /dates itself 2026-09-01 \(the last adjudication\) before 2026-09-11/,
    );
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
    const { errors, notes } = run({
      siteMeta: {},
      passageText: null,
      highText: null,
    });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toMatch(/nothing adjudicated yet/);
  });

  it("FAILS when the block has coverage but the sentence is gone", () => {
    const { errors } = run({ siteMeta: LIVE_META, passageText: null, highText: null });
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

describe("gate 24 leg o — non-vacuity (fix round 1, M4)", () => {
  // leg n carries MIN_PUBLISHED_LINK_METHODS for exactly this shape. With
  // by_method = {} and self-consistent headline counts, the per-method sum
  // check, the unadjudicated-path naming and the completeness check all skip
  // silently, and a passage that names NO unadjudicated path reads as a
  // corpus with none.
  it("FAILS when by_method names fewer paths than the dated floor", () => {
    const meta = {
      link_adjudication: {
        ...LIVE_META.link_adjudication,
        by_method: {
          "account+subagency": { published: 12595, adjudicated: 9587 },
        },
        unadjudicated_methods: [],
      },
    };
    const { errors } = run({
      siteMeta: meta,
      passageText: LIVE_PASSAGE.replace(
        " The announcement+lexicon, fpds-ap and subaward+lexicon paths carry " +
          "no per-link adjudication — their precision is sampled instead (below).",
        "",
      ),
    });
    expect(errors.join("\n")).toMatch(/by_method names 1 path\(s\)/);
    expect(errors.join("\n")).toMatch(/do not lower the floor/);
  });

  it("FAILS on an empty by_method even when every other direction passes", () => {
    const meta = {
      link_adjudication: {
        ...LIVE_META.link_adjudication,
        by_method: {},
        unadjudicated_methods: [],
      },
    };
    const { errors } = run({
      siteMeta: meta,
      passageText: LIVE_PASSAGE.replace(
        " The announcement+lexicon, fpds-ap and subaward+lexicon paths carry " +
          "no per-link adjudication — their precision is sampled instead (below).",
        "",
      ),
    });
    expect(errors.filter((e) => /by_method names 0 path/.test(e))).toHaveLength(1);
  });

  it("passes at the floor itself", () => {
    const four = Object.fromEntries(
      Object.entries(LIVE_META.link_adjudication.by_method).filter(
        ([m]) => m !== "subaward+lexicon",
      ),
    );
    const meta = {
      link_adjudication: {
        ...LIVE_META.link_adjudication,
        published: 12482,
        by_method: four,
        unadjudicated_methods: ["announcement+lexicon", "fpds-ap"],
      },
    };
    const { errors } = run({
      siteMeta: meta,
      passageText: LIVE_PASSAGE.replace("12,595", "12,482")
        .replace("announcement+lexicon, fpds-ap and subaward+lexicon paths", "announcement+lexicon and fpds-ap paths"),
    });
    expect(errors.join("\n")).not.toMatch(/by_method names/);
  });
});

describe("gate 24 leg o — the High tier's own census (R-6c-4)", () => {
  it("FAILS when the High passage states a count the high block does not hold", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE,
      highText: LIVE_HIGH.replace("60 of the 768", "881 of the 881"),
    });
    expect(errors.join("\n")).toMatch(/never states published_high = 768/);
    expect(errors.join("\n")).toMatch(/states "881", which is not a figure/);
  });

  // The species this whole sub-block exists for: the 768 that publish at high
  // are the MART's, and Postgres' coalesce(adjudicated_confidence,
  // confidence) says 881 because dbt demotes 113 unadjudicated
  // account+tokens rows nothing in Postgres records.
  it("FAILS when the tier's grading claims two lenses over the whole tier", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE,
      highText:
        "768 of the 768 links published at high carry a per-award hand " +
        "adjudication, all 60 of them challenged by two independent " +
        "adversarial reviewers.",
    });
    expect(errors.join("\n")).toMatch(
      /"announcement\+lexicon" publishes 708 link\(s\) at HIGH with no per-award adjudication/,
    );
  });

  it("FAILS when the unreviewed remainder's evidence path goes unnamed", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE,
      highText: LIVE_HIGH.replace(
        "; the other 708 rest on the announcement+lexicon path",
        "",
      ),
    });
    expect(errors.join("\n")).toMatch(
      /"announcement\+lexicon" publishes 708 link\(s\) at HIGH/,
    );
  });

  it("FAILS when the high census renders with no high block behind it", () => {
    const { errors } = run({
      siteMeta: { link_adjudication: withoutHighCensus() },
      passageText: LIVE_PASSAGE,
    });
    expect(errors.join("\n")).toMatch(
      /renders while site_meta.link_adjudication carries no `high` census/,
    );
  });

  it("FAILS when the high block has a census and the grading states none", () => {
    const { errors } = run({
      siteMeta: LIVE_META,
      passageText: LIVE_PASSAGE,
      highText: null,
    });
    expect(errors.join("\n")).toMatch(
      /no \[data-link-adjudication-high\] passage renders/,
    );
  });

  it("passes when the mart is absent and neither census renders", () => {
    const { errors, notes } = run({
      siteMeta: { link_adjudication: withoutHighCensus() },
      passageText: LIVE_PASSAGE,
      highText: null,
    });
    expect(errors).toEqual([]);
    expect(notes.join(" ")).not.toMatch(/published at high/);
  });

  it("FAILS when by_path does not sum to the high headline counts", () => {
    const meta = {
      link_adjudication: {
        ...LIVE_META.link_adjudication,
        high: {
          ...LIVE_META.link_adjudication.high,
          by_path: {
            ...LIVE_META.link_adjudication.high.by_path,
            "announcement+lexicon": { high: 1, adjudicated: 0, two_lens: 0 },
          },
        },
      },
    };
    const { errors } = run({ siteMeta: meta, passageText: LIVE_PASSAGE });
    expect(errors.join("\n")).toMatch(/published_high is 768 but by_path sums to 61/);
  });

  it("FAILS when more links survived two lenses than were adjudicated", () => {
    const meta = {
      link_adjudication: {
        ...LIVE_META.link_adjudication,
        high: {
          published_high: 768,
          adjudicated_high: 60,
          two_lens_high: 768,
          by_path: {},
        },
      },
    };
    const { errors } = run({
      siteMeta: meta,
      passageText: LIVE_PASSAGE,
      highText: LIVE_HIGH.replace("all 60 of them", "all 768 of them"),
    });
    expect(errors.join("\n")).toMatch(/site_meta.link_adjudication.high is inverted/);
  });
});

describe("gate 24 leg o — a block that predates measured_on", () => {
  // The page's guard requires `measured_on`, so a pre-fix-round artifact
  // renders NO passage while the block still carries coverage. Without this
  // branch the leg reports "the block has coverage and nothing renders",
  // which sends the reader looking at the page instead of the export.
  it("names the stale artifact rather than blaming the page", () => {
    const block = { ...LIVE_META.link_adjudication };
    delete block.measured_on;
    const { errors } = run({
      siteMeta: { link_adjudication: block },
      passageText: null,
      highText: null,
    });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(/no `measured_on`/);
    expect(errors[0]).toMatch(/Re-run export-site; do not re-date the counts by `as_of`/);
  });
});
