/**
 * Gate 24 legs (n) and (o) — the decisions wave's new site_meta keys
 * (ruling R-DEC-GATE24, controller 2026-09-26: "bind the new site_meta keys
 * it renders … — no stray-number exemption").
 *
 * The decisions wave moved three things /methodology/ now states as figures:
 *
 *   - #107(b): the account / sub-agency tier was withdrawn from publication
 *     on its 0-of-58 attribution figure. The exporter keeps that figure in
 *     `link_precision.withdrawn` — never in `methods`, which leg n binds to
 *     the published tiers — and the page states it, with the number of links
 *     withdrawn, in a [data-link-precision-withdrawn="<method>"] element.
 *     The unpinned-link clause of the opener changes with it: most unpinned
 *     links no longer publish, so "those links publish at medium" (a claim
 *     about all of them) gives way to `unpinned_published`.
 *   - #110 / R-DEC-110: every link published at high carries a recorded
 *     review, split by record kind (`high.reviewed_high`,
 *     `high.reviewed_by_kind`), in [data-link-review-high].
 *   - R-DEC-110 / R-DEC-110b: the links a recorded rule moved down from high
 *     (`high.demoted_from_high`), by reason, in [data-link-demoted-high].
 *
 * Each direction below was run against the legs BEFORE they bound these keys
 * and failed there (a figure rendered with nothing behind it, a figure
 * typed back in, a figure dropped, a permuted order) — the point of a proof
 * that the binding can fail.
 *
 * Corpora are injected the way link-precision.test.mjs and
 * link-adjudication.test.mjs inject theirs, so nothing here needs a build.
 */

import { describe, it, expect } from "vitest";
import { runLinkPrecisionLeg, runLinkAdjudicationLeg } from "../datatruth.mjs";

// ─────────────────────────────────────────────────────────────────────────
// leg n — link_precision.withdrawn
// ─────────────────────────────────────────────────────────────────────────

function citationsFor(pairs) {
  const out = {};
  pairs.forEach(([method, confidence], i) => {
    out[`f${i}`] = {
      formula:
        `crosswalk link: pe_bli=0604262N matched to award PIID N000${i} via ` +
        `method='${method}', confidence='${confidence}' (dollars live at ` +
        `award grain in fct_award_transactions)`,
    };
  });
  return out;
}

/** The published universe after #107(b): account+subagency still publishes
 *  its two-lens-pinned pairs (at high), so it stays a published method. */
const CITATIONS = citationsFor([
  ["account", "medium"],
  ["account+subagency", "high"],
  ["account+tokens", "medium"],
  ["announcement+lexicon", "high"],
  ["announcement+lexicon", "medium"],
  ["fpds-ap", "medium"],
  ["subaward+lexicon", "medium"],
]);

/** The post-chain shape export_site._link_precision_block projects
 *  (decisions-lane-export-ops.md §4(a)). */
const WITHDRAWN_META = {
  link_precision: {
    rubric: "attribution",
    sample_id: "2026-09-04",
    sampled_at: "2026-09-04",
    methods: {
      "announcement+lexicon": { confirmed: 56, sampled: 60, sample_id: "2026-09-04", judged: "2026-09-04" },
      "fpds-ap": { confirmed: 89, sampled: 114, sample_id: "2026-09-04", judged: "2026-09-04" },
      "subaward+lexicon": { confirmed: 53, sampled: 60, sample_id: "2026-09-04", judged: "2026-09-04" },
    },
    unmeasured: ["account", "account+subagency", "account+tokens"],
    withdrawn: {
      "account+subagency": {
        confirmed: 0,
        sampled: 58,
        sample_id: "2026-09-05",
        judged: "2026-09-11",
        links: 8833,
        demotion_reasons: ["account_subagency_not_pinned"],
      },
    },
  },
};

const PRECISION_PARAGRAPH =
  "Measured precision of the published tiers, from a held-out " +
  "hand-adjudicated sample re-run through a two-reviewer process and " +
  "recorded 2026-09-04. Every figure answers one question — program " +
  "attribution: does this award execute this program element? — not whether " +
  "the linking rule fired. Each sampled link is counted under the tier it " +
  "publishes under today, not the tier it carried when it was drawn; one the " +
  "corpus no longer publishes is counted in neither direction: " +
  "announcement+lexicon 56/60; fpds-ap 89/114; subaward+lexicon 53/60. No " +
  "precision figure is published for the remaining tiers a reader can meet — " +
  "account, account+subagency, account+tokens. Those rest on an " +
  "appropriation-account match, narrowed by a hand adjudication of the award, " +
  "by sub-agency and a pinning two-lens adjudication, or by " +
  "keyword overlap; how often that association names the right program has " +
  "not been independently measured for these tiers.";

/** What /methodology/ renders in [data-link-precision-withdrawn="account+subagency"]. */
const WITHDRAWN_TEXT =
  "A held-out sample of account / sub-agency links, judged on program " +
  "attribution, confirmed 0 of 58 (2026-09-11). The tier was withdrawn on " +
  "that figure (2026-09-25): its 8,833 links that no two-lens hand " +
  "adjudication pinned no longer publish.";

function legN(overrides = {}) {
  const errors = [];
  const notes = [];
  runLinkPrecisionLeg(errors, notes, {
    siteMeta: WITHDRAWN_META,
    citations: CITATIONS,
    paragraphText: PRECISION_PARAGRAPH,
    withdrawnTexts: { "account+subagency": WITHDRAWN_TEXT },
    ...overrides,
  });
  return { errors, notes };
}
const legNErrors = (o) => legN(o).errors.filter((e) => e.startsWith("leg n"));

describe("gate 24 leg n — link_precision.withdrawn (R-DEC-GATE24)", () => {
  it("passes on the post-chain shape with the withdrawn figure stated in its own element", () => {
    const { errors, notes } = legN();
    expect(errors).toEqual([]);
    expect(notes.some((n) => /withdrawn/.test(n))).toBe(true);
  });

  it("FAILS when a withdrawn tier's figure renders nowhere", () => {
    const errs = legNErrors({ withdrawnTexts: {} });
    expect(errs).toHaveLength(1);
    expect(errs[0]).toMatch(/withdrawn.*account\+subagency.*no \[data-link-precision-withdrawn/);
  });

  it("FAILS when the element renders with no withdrawn figure behind it", () => {
    const meta = structuredClone(WITHDRAWN_META);
    delete meta.link_precision.withdrawn;
    const errs = legNErrors({ siteMeta: meta });
    expect(errs.some((e) => /renders while site_meta\.link_precision\.withdrawn carries no/.test(e))).toBe(true);
  });

  it("FAILS when the element states a figure the block does not hold (0 of 60, the pre-merge figure)", () => {
    const errs = legNErrors({
      withdrawnTexts: { "account+subagency": WITHDRAWN_TEXT.replace("0 of 58", "0 of 60") },
    });
    expect(errs.some((e) => /"60"/.test(e))).toBe(true);
  });

  it("FAILS when a number is typed back in beside the derived ones", () => {
    const errs = legNErrors({
      withdrawnTexts: {
        "account+subagency": WITHDRAWN_TEXT.replace(
          "no longer publish.",
          "no longer publish; 22 still do.",
        ),
      },
    });
    expect(errs.some((e) => /states "22"/.test(e))).toBe(true);
  });

  it("FAILS when the figures sit in the wrong slots (links where the sample was)", () => {
    const errs = legNErrors({
      withdrawnTexts: {
        "account+subagency": WITHDRAWN_TEXT.replace("0 of 58", "0 of 8,833").replace("its 8,833", "its 58"),
      },
    });
    expect(errs.some((e) => /in the order/.test(e))).toBe(true);
  });

  it("FAILS when the withdrawn links go unstated (the size of the withdrawal is the point)", () => {
    const errs = legNErrors({
      withdrawnTexts: {
        "account+subagency": WITHDRAWN_TEXT.replace("its 8,833 links", "its links"),
      },
    });
    expect(errs.some((e) => /links = 8,833/.test(e))).toBe(true);
  });

  it("FAILS when the judged date goes unstated", () => {
    const errs = legNErrors({
      withdrawnTexts: { "account+subagency": WITHDRAWN_TEXT.replace(" (2026-09-11)", "") },
    });
    expect(errs.some((e) => /2026-09-11/.test(e))).toBe(true);
  });

  it("FAILS when the element never says which question the figure answered", () => {
    const errs = legNErrors({
      withdrawnTexts: {
        "account+subagency": WITHDRAWN_TEXT.replace("judged on program attribution, ", ""),
      },
    });
    expect(errs.some((e) => /program attribution/.test(e))).toBe(true);
  });

  it("FAILS when a withdrawn figure is also printed as a published tier's precision", () => {
    const errs = legNErrors({
      paragraphText: PRECISION_PARAGRAPH.replace(
        "subaward+lexicon 53/60.",
        "subaward+lexicon 53/60; account+subagency 0/58.",
      ),
    });
    expect(errs.some((e) => /account\+subagency/.test(e))).toBe(true);
  });

  it("FAILS on a self-contradicting withdrawn block (more confirmed than sampled)", () => {
    const meta = structuredClone(WITHDRAWN_META);
    meta.link_precision.withdrawn["account+subagency"].confirmed = 59;
    const errs = legNErrors({
      siteMeta: meta,
      withdrawnTexts: { "account+subagency": WITHDRAWN_TEXT.replace("0 of 58", "59 of 58") },
    });
    expect(errs.some((e) => /inverted|cannot exceed/.test(e))).toBe(true);
  });

  it("the pre-decisions shape (no withdrawn key, no element) is unaffected", () => {
    const meta = structuredClone(WITHDRAWN_META);
    delete meta.link_precision.withdrawn;
    expect(legNErrors({ siteMeta: meta, withdrawnTexts: {} })).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────────────────────
// leg o — unpinned_published, reviewed_high + reviewed_by_kind,
// demoted_from_high
// ─────────────────────────────────────────────────────────────────────────

/** The post-chain shape (decisions-lane-export-ops.md §4, fix round §3;
 *  figures are a fixture, not a measurement — the chain measures them). */
const ADJ_META = {
  link_adjudication: {
    measured_on: "2026-09-27",
    as_of: "2026-09-01",
    published: 12866,
    adjudicated: 9538,
    unpinned: 8475,
    unpinned_tier: null,
    unpinned_published: 86,
    unpinned_published_tier: "medium",
    by_method: {
      "account+subagency": { published: 9368, adjudicated: 9172 },
      "account+tokens": { published: 445, adjudicated: 364 },
      "announcement+lexicon": { published: 1075, adjudicated: 2 },
      "fpds-ap": { published: 1865, adjudicated: 0 },
      "subaward+lexicon": { published: 113, adjudicated: 0 },
    },
    unadjudicated_methods: ["fpds-ap", "subaward+lexicon"],
    high: {
      published_high: 1105,
      adjudicated_high: 60,
      two_lens_high: 60,
      reviewed_high: 1105,
      review_as_of: null,
      reviewed_by_kind: { adjudication: 60, verdict_pair: 418, survivor_list: 627 },
      demoted_from_high: {
        links: 91,
        by_reason: {
          account_tokens_unadjudicated: 63,
          announcement_review_refuted: 5,
          announcement_reviewer_rejected: 12,
          precision_sample_refuted: 11,
        },
        by_path: {
          "account+tokens": { account_tokens_unadjudicated: 63 },
          "announcement+lexicon": {
            announcement_review_refuted: 5,
            announcement_reviewer_rejected: 12,
            precision_sample_refuted: 11,
          },
        },
      },
      by_path: {
        account: { high: 3, adjudicated: 3, two_lens: 3, reviewed: 3,
          reviewed_by_kind: { adjudication: 3, verdict_pair: 0, survivor_list: 0 } },
        "account+subagency": { high: 22, adjudicated: 22, two_lens: 22, reviewed: 22,
          reviewed_by_kind: { adjudication: 22, verdict_pair: 0, survivor_list: 0 } },
        "account+tokens": { high: 34, adjudicated: 34, two_lens: 34, reviewed: 34,
          reviewed_by_kind: { adjudication: 34, verdict_pair: 0, survivor_list: 0 } },
        "announcement+lexicon": {
          high: 1046, adjudicated: 1, two_lens: 1, with_match_basis: 700, reviewed: 1046,
          announcement_reviewed: 1045, announcement_upheld: 1045,
          reviewed_by_kind: { adjudication: 1, verdict_pair: 418, survivor_list: 627 },
        },
      },
    },
  },
};

const OPENER =
  "As of 2026-09-27, 9,538 of the 12,866 links the crosswalk grades high or " +
  "medium carry a per-award hand adjudication — the most recent made on " +
  "2026-09-01 — recording which program elements, if any, the award's own " +
  "contract record supports. 8,475 of those found work that could not be " +
  "pinned to any one program element; 86 of them still publish, at medium, " +
  "and the rest no longer publish. The fpds-ap and subaward+lexicon paths " +
  "carry no per-link adjudication — their precision is sampled instead (below).";
const HIGH =
  "60 of the 1,105 links published at high carry a per-award hand " +
  "adjudication, all 60 challenged by two independent adversarial reviewers; " +
  "the other 1,045 rest on the announcement+lexicon path.";
const REVIEW =
  "All 1,105 carry a recorded review, counted once under the strongest: 60 " +
  "a two-lens hand adjudication, 418 a per-proposal verdict pair and 627 " +
  "only a survivor-list entry, which records survival of the adversarial " +
  "pass, not its verdict.";
const DEMOTED =
  "91 more were demoted from high: 63 unadjudicated keyword matches, 5 " +
  "refuted in review, 12 rejected by a reviewer and 11 refuted by the " +
  "precision study.";

function legO(overrides = {}) {
  const errors = [];
  const notes = [];
  runLinkAdjudicationLeg(errors, notes, {
    siteMeta: ADJ_META,
    passageText: OPENER,
    highText: HIGH,
    reviewText: REVIEW,
    demotedText: DEMOTED,
    ...overrides,
  });
  return { errors, notes };
}
const legOErrors = (o) => legO(o).errors.filter((e) => e.startsWith("leg o"));
const withMeta = (fn) => {
  const meta = structuredClone(ADJ_META);
  fn(meta.link_adjudication);
  return meta;
};

describe("gate 24 leg o — unpinned_published (#107(b))", () => {
  it("passes on the post-chain shape", () => {
    expect(legO().errors).toEqual([]);
  });

  it("FAILS when the old 'those links publish at medium' survives beside a block where most no longer publish", () => {
    const errs = legOErrors({
      passageText: OPENER.replace(
        "; 86 of them still publish, at medium, and the rest no longer publish.",
        "; those links publish at medium.",
      ),
    });
    expect(errs.some((e) => /those links publish at/.test(e))).toBe(true);
  });

  it("FAILS when the count that still publishes goes unstated", () => {
    const errs = legOErrors({
      passageText: OPENER.replace("; 86 of them still publish, at medium, and the rest no longer publish", ""),
    });
    expect(errs.some((e) => /unpinned_published = 86/.test(e))).toBe(true);
  });

  it("FAILS when the rest's withdrawal goes unsaid", () => {
    const errs = legOErrors({
      passageText: OPENER.replace(", and the rest no longer publish", ""),
    });
    expect(errs.some((e) => /no longer publish/.test(e))).toBe(true);
  });

  it("FAILS when unpinned_published moves into another slot", () => {
    const errs = legOErrors({
      passageText: OPENER.replace("8,475 of those", "86 of those").replace("; 86 of them", "; 8,475 of them"),
    });
    expect(errs.some((e) => /in the order/.test(e))).toBe(true);
  });

  it("FAILS on a block claiming more unpinned links publish than exist", () => {
    const errs = legOErrors({
      siteMeta: withMeta((b) => { b.unpinned_published = 9000; }),
      passageText: OPENER.replace("86 of them", "9,000 of them"),
    });
    expect(errs.some((e) => /inverted|cannot exceed/.test(e))).toBe(true);
  });

  it("an export where every unpinned link still publishes keeps the old clause", () => {
    const meta = withMeta((b) => {
      b.unpinned_published = 8475;
      b.unpinned_tier = "medium";
    });
    const text = OPENER.replace(
      "; 86 of them still publish, at medium, and the rest no longer publish.",
      "; those links publish at medium.",
    );
    expect(legOErrors({ siteMeta: meta, passageText: text })).toEqual([]);
  });

  it("zero still publishing: the passage must say none does", () => {
    const meta = withMeta((b) => { b.unpinned_published = 0; b.unpinned_published_tier = null; });
    const ok = OPENER.replace("; 86 of them still publish, at medium, and the rest no longer publish", "; none of them still publishes");
    expect(legOErrors({ siteMeta: meta, passageText: ok })).toEqual([]);
    const bad = OPENER.replace("; 86 of them still publish, at medium, and the rest no longer publish", "");
    expect(legOErrors({ siteMeta: meta, passageText: bad }).some((e) => /none of them still publishes/.test(e))).toBe(true);
  });
});

describe("gate 24 leg o — reviewed_high and its record-kind split (#110, R-DEC-110)", () => {
  it("FAILS when the census carries the split and no [data-link-review-high] renders", () => {
    const errs = legOErrors({ reviewText: undefined });
    expect(errs.some((e) => /no \[data-link-review-high\] passage renders/.test(e))).toBe(true);
  });

  it("FAILS when the passage renders with no split behind it", () => {
    const meta = withMeta((b) => {
      delete b.high.reviewed_high;
      delete b.high.reviewed_by_kind;
    });
    const errs = legOErrors({ siteMeta: meta });
    expect(errs.some((e) => /\[data-link-review-high\] renders while/.test(e))).toBe(true);
  });

  it("FAILS when reviewed_high is exported without the record-kind split (R-DEC-110 discloses it)", () => {
    const meta = withMeta((b) => { delete b.high.reviewed_by_kind; });
    const errs = legOErrors({ siteMeta: meta, reviewText: undefined });
    expect(errs.some((e) => /reviewed_by_kind/.test(e))).toBe(true);
  });

  it("FAILS when a kind's count is typed instead of derived", () => {
    const errs = legOErrors({ reviewText: REVIEW.replace("418 a per-proposal", "425 a per-proposal") });
    expect(errs.some((e) => /"425"/.test(e))).toBe(true);
  });

  it("FAILS when two kinds trade places (the granularity is the disclosure)", () => {
    const errs = legOErrors({
      reviewText: REVIEW.replace("418 a per-proposal", "627 a per-proposal").replace(
        "627 only a survivor-list entry",
        "418 only a survivor-list entry",
      ),
    });
    expect(errs.some((e) => /in the order/.test(e))).toBe(true);
  });

  it("FAILS when the passage stops naming a record kind", () => {
    const errs = legOErrors({ reviewText: REVIEW.replace("survivor-list entry", "list entry") });
    expect(errs.some((e) => /survivor-list/.test(e))).toBe(true);
  });

  it("FAILS when it says 'All' over a census where not every high link is reviewed", () => {
    const meta = withMeta((b) => {
      b.high.reviewed_high = 1100;
      b.high.reviewed_by_kind = { adjudication: 60, verdict_pair: 418, survivor_list: 622 };
      b.high.by_path["announcement+lexicon"].reviewed = 1041;
      b.high.by_path["announcement+lexicon"].reviewed_by_kind = { adjudication: 1, verdict_pair: 418, survivor_list: 622 };
    });
    const text = REVIEW.replace("All 1,105", "All 1,100").replace("627 only", "622 only");
    const errs = legOErrors({ siteMeta: meta, reviewText: text });
    expect(errs.some((e) => /"All"/.test(e))).toBe(true);
    const honest = REVIEW.replace("All 1,105", "1,100 of them").replace("627 only", "622 only");
    expect(legOErrors({ siteMeta: meta, reviewText: honest })).toEqual([]);
  });

  it("FAILS on a split that does not sum to reviewed_high", () => {
    const meta = withMeta((b) => { b.high.reviewed_by_kind.survivor_list = 600; });
    const errs = legOErrors({ siteMeta: meta, reviewText: REVIEW.replace("627 only", "600 only") });
    expect(errs.some((e) => /sums to/.test(e))).toBe(true);
  });

  it("FAILS when more links are reviewed than publish at high", () => {
    const meta = withMeta((b) => { b.high.reviewed_high = 1200; });
    const errs = legOErrors({ siteMeta: meta, reviewText: REVIEW.replace("All 1,105", "1,200 of them") });
    expect(errs.some((e) => /reviewed_high/.test(e) && /published_high/.test(e))).toBe(true);
  });
});

describe("gate 24 leg o — demoted_from_high (R-DEC-110, R-DEC-110b)", () => {
  it("FAILS when the census carries demotions and no [data-link-demoted-high] renders", () => {
    const errs = legOErrors({ demotedText: undefined });
    expect(errs.some((e) => /no \[data-link-demoted-high\] passage renders/.test(e))).toBe(true);
  });

  it("FAILS when the passage renders with no demotion behind it", () => {
    const meta = withMeta((b) => { delete b.high.demoted_from_high; });
    const errs = legOErrors({ siteMeta: meta });
    expect(errs.some((e) => /\[data-link-demoted-high\] renders while/.test(e))).toBe(true);
  });

  it("FAILS when a reason's count is dropped", () => {
    const errs = legOErrors({
      demotedText: DEMOTED.replace(", 12 rejected by a reviewer", ""),
    });
    expect(errs.some((e) => /in the order/.test(e))).toBe(true);
  });

  it("FAILS when the total is typed instead of derived (the stage-1 projection's 18)", () => {
    const errs = legOErrors({ demotedText: DEMOTED.replace("91 more were", "18 more were") });
    expect(errs.some((e) => /"18"/.test(e))).toBe(true);
  });

  it("FAILS on a block whose by_path does not sum to by_reason", () => {
    const meta = withMeta((b) => { b.high.demoted_from_high.by_path["announcement+lexicon"].precision_sample_refuted = 10; });
    const errs = legOErrors({ siteMeta: meta });
    expect(errs.some((e) => /by_path/.test(e) && /precision_sample_refuted/.test(e))).toBe(true);
  });

  it("FAILS on a block where a reason counts more pairs than were demoted", () => {
    const meta = withMeta((b) => { b.high.demoted_from_high.links = 50; });
    const errs = legOErrors({ siteMeta: meta, demotedText: DEMOTED.replace("91 more", "50 more") });
    expect(errs.some((e) => /exceeds|cannot exceed/.test(e))).toBe(true);
  });

  it("an empty demotion census renders nothing, and that passes", () => {
    const meta = withMeta((b) => {
      b.high.demoted_from_high = { links: 0, by_reason: {}, by_path: {} };
    });
    expect(legOErrors({ siteMeta: meta, demotedText: undefined })).toEqual([]);
  });
});

describe("gate 24 leg o — the pre-decisions shape is unaffected", () => {
  it("a block without any of the new keys binds exactly as before", () => {
    const meta = withMeta((b) => {
      delete b.unpinned_published;
      delete b.unpinned_published_tier;
      b.unpinned_tier = "medium";
      delete b.high.reviewed_high;
      delete b.high.review_as_of;
      delete b.high.reviewed_by_kind;
      delete b.high.demoted_from_high;
    });
    const text = OPENER.replace(
      "; 86 of them still publish, at medium, and the rest no longer publish.",
      "; those links publish at medium.",
    );
    expect(
      legOErrors({ siteMeta: meta, passageText: text, reviewText: undefined, demotedText: undefined }),
    ).toEqual([]);
  });
});
