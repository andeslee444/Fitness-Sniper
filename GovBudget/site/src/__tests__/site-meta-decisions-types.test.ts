/**
 * The SiteMeta types carry every site_meta key the decisions wave's exporter
 * adds (src/govbudget/export_site.py, 2026-09-25/26) — so the /methodology/
 * writer can render them without a cast, and tsc fails the day a shape
 * drifts from these literals.
 *
 * The literals are the exporter's docstring shapes. Their figures are
 * ILLUSTRATIVE — shapes, not measurements (the chain measures them):
 *   - link_precision.withdrawn (#107(b)) — a tier dbt graded OUT of
 *     publication keeps its measured figure here, never in `methods`;
 *   - link_adjudication.unpinned_published / unpinned_published_tier
 *     (#107(b)) — how many unpinned links the MART still publishes, and at
 *     which one tier;
 *   - link_adjudication.high.reviewed_high / review_as_of / reviewed_by_kind
 *     and by_path reviewed / announcement_reviewed / announcement_upheld /
 *     reviewed_by_kind (#110, R-DEC-110) — recorded review coverage of the
 *     High tier, split by record kind;
 *   - link_adjudication.high.demoted_from_high (R-DEC-110) — the links a rule
 *     demoted from high, counted by reason.
 *
 * `tsc --noEmit -p .` compiles this file (object literals get excess-property
 * checks), and the runtime assertions pin the arithmetic the exporter
 * promises: reviewed_by_kind sums to reviewed_high, per path and overall.
 */
import { describe, it, expect } from "vitest";
import type { SiteMeta } from "@/lib/data";

type LinkPrecision = NonNullable<SiteMeta["link_precision"]>;
type LinkAdjudication = NonNullable<SiteMeta["link_adjudication"]>;

const precision: LinkPrecision = {
  rubric: "attribution",
  sample_id: "2026-09-04",
  sampled_at: "2026-09-04",
  methods: {
    "announcement+lexicon": { confirmed: 56, sampled: 60, sample_id: "2026-09-04", judged: "2026-09-04" },
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
};

const adjudication: LinkAdjudication = {
  measured_on: "2026-09-26",
  as_of: "2026-09-11",
  published: 12595,
  adjudicated: 9272,
  unpinned: 8475,
  unpinned_tier: null,
  unpinned_published: 86,
  unpinned_published_tier: "medium",
  by_method: { "announcement+lexicon": { published: 1074, adjudicated: 1 } },
  unadjudicated_methods: [],
  high: {
    published_high: 484,
    adjudicated_high: 60,
    two_lens_high: 60,
    reviewed_high: 484,
    review_as_of: null,
    reviewed_by_kind: { adjudication: 60, verdict_pair: 300, survivor_list: 124 },
    by_path: {
      "announcement+lexicon": {
        high: 425,
        adjudicated: 1,
        two_lens: 1,
        with_match_basis: 300,
        reviewed: 425,
        announcement_reviewed: 424,
        announcement_upheld: 424,
        reviewed_by_kind: { adjudication: 1, verdict_pair: 300, survivor_list: 124 },
      },
      "fpds-ap": {
        high: 59,
        adjudicated: 59,
        two_lens: 59,
        reviewed: 59,
        reviewed_by_kind: { adjudication: 59, verdict_pair: 0, survivor_list: 0 },
      },
    },
    demoted_from_high: {
      links: 649,
      by_reason: { announcement_review_unrecorded: 638, announcement_review_refuted: 11 },
      by_path: {
        "announcement+lexicon": { announcement_review_unrecorded: 638, announcement_review_refuted: 11 },
      },
    },
  },
};

describe("SiteMeta carries the decisions wave's site_meta keys", () => {
  it("types link_precision.withdrawn beside methods, never inside it", () => {
    expect(Object.keys(precision.withdrawn ?? {})).toEqual(["account+subagency"]);
    expect(precision.methods?.["account+subagency"]).toBeUndefined();
  });

  it("types the unpinned links the mart still publishes", () => {
    expect(adjudication.unpinned_published).toBeLessThanOrEqual(adjudication.unpinned ?? 0);
    expect(adjudication.unpinned_published_tier).toBe("medium");
  });

  it("types the High tier's review coverage, whose kinds sum to reviewed_high", () => {
    const high = adjudication.high!;
    const sum = (k: Record<string, number>) => Object.values(k).reduce((a, b) => a + b, 0);
    expect(sum(high.reviewed_by_kind!)).toBe(high.reviewed_high);
    for (const path of Object.values(high.by_path!)) {
      if (path.reviewed_by_kind) expect(sum(path.reviewed_by_kind)).toBe(path.reviewed);
    }
  });

  it("types the demotions from high, by reason and by path", () => {
    const d = adjudication.high!.demoted_from_high!;
    expect(Object.values(d.by_reason).reduce((a, b) => a + b, 0)).toBeGreaterThanOrEqual(d.links);
    expect(Object.keys(d.by_path)).toEqual(["announcement+lexicon"]);
  });
});
