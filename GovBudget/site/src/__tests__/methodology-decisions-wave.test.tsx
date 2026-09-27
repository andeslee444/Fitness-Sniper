/**
 * /methodology/ after the owner-delegated decisions wave (rulings of
 * 2026-09-25/26) — the page renders what gate 24 legs (n) and (o) bind, on
 * BOTH shapes of site_meta it can meet, and on whichever the shared export
 * is today:
 *
 *   - the pre-chain shape (chain F2, 2026-09-25: no withdrawn tier, no
 *     recorded-review census) — a FIXTURE derived from today's export by
 *     removing the decisions wave's keys (`preChain`). Until chain G this
 *     was the shared export itself; chain G's export (2026-09-26) is the
 *     post-chain shape, so the pre-chain case can no longer read it live;
 *   - the post-chain shape the decisions wave exports (#107(b): the
 *     account / sub-agency tier withdrawn into link_precision.withdrawn and
 *     `unpinned_published`; #110 / R-DEC-110: `reviewed_high` +
 *     `reviewed_by_kind`; R-DEC-110 / R-DEC-110b: `demoted_from_high`).
 *     Its figures are a FIXTURE (the chain measures the real ones); what is
 *     tested is that every figure the page states is one the gate binds, in
 *     its slot — so a rendered figure without its site_meta source fails.
 *
 * It also pins the prose the wave rewrote, each sentence checked for being
 * true of the shape it renders on (the species lesson: new prose that
 * overstates is the recurring defect).
 */
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { parse } from "node-html-parser";
import type { SiteMeta } from "@/lib/data";
import {
  runLinkAdjudicationLeg,
  runLinkPrecisionLeg,
} from "../../scripts/gates/datatruth.mjs";

let override: ((m: SiteMeta) => SiteMeta) | null = null;
vi.mock("@/lib/data", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/data")>();
  return {
    ...actual,
    getSiteMeta: () =>
      override ? override(structuredClone(actual.getSiteMeta())) : actual.getSiteMeta(),
  };
});

import MethodologyPage from "@/app/methodology/page";

afterEach(() => {
  cleanup();
  override = null;
});

const norm = (s: string) => s.replace(/\s+/g, " ").trim();

function renderPage(fn: ((m: SiteMeta) => SiteMeta) | null) {
  override = fn;
  const { container } = render(<MethodologyPage />);
  const root = parse(container.innerHTML, { comment: false });
  cleanup();
  return root;
}

/** Every crosswalk method the fixture corpus publishes, as citations.json
 *  states them (one row per method × tier is enough for leg n's universe). */
function citationsFor(methods: string[]) {
  const out: Record<string, { formula: string }> = {};
  methods.forEach((m, i) => {
    out[`f${i}`] = {
      formula: `crosswalk link: pe_bli=X matched to award PIID P${i} via method='${m}', confidence='medium'`,
    };
  });
  return out;
}
const PUBLISHED_METHODS = [
  "account",
  "account+subagency",
  "account+tokens",
  "announcement+lexicon",
  "fpds-ap",
  "subaward+lexicon",
];

/** The legs, fed the rendered page's elements through their injected seam. */
function legs(root: ReturnType<typeof parse>, meta: SiteMeta) {
  const errors: string[] = [];
  const notes: string[] = [];
  const text = (sel: string) => {
    const el = root.querySelector(sel);
    return el ? norm(el.text) : undefined;
  };
  const withdrawnTexts: Record<string, string> = {};
  for (const el of root.querySelectorAll("[data-link-precision-withdrawn]")) {
    withdrawnTexts[el.getAttribute("data-link-precision-withdrawn")!] = norm(el.text);
  }
  runLinkPrecisionLeg(errors, notes, {
    siteMeta: meta,
    citations: citationsFor(PUBLISHED_METHODS),
    paragraphText: text("[data-link-precision]"),
    withdrawnTexts,
  });
  runLinkAdjudicationLeg(errors, notes, {
    siteMeta: meta,
    passageText: text("[data-link-adjudication]"),
    highText: text("[data-link-adjudication-high]"),
    reviewText: text("[data-link-review-high]"),
    demotedText: text("[data-link-demoted-high]"),
  });
  return { errors, notes };
}

/** The post-chain shape. Figures are a fixture; the gate binds whatever the
 *  chain measures. */
function postChain(m: SiteMeta): SiteMeta {
  const lp = m.link_precision!;
  delete lp.methods!["account+subagency"];
  lp.unmeasured = ["account", "account+subagency", "account+tokens"];
  lp.sample_id = "2026-09-04";
  lp.sampled_at = "2026-09-04";
  lp.withdrawn = {
    "account+subagency": {
      confirmed: 0,
      sampled: 58,
      sample_id: "2026-09-05",
      judged: "2026-09-11",
      links: 8833,
      demotion_reasons: ["account_subagency_not_pinned"],
    },
  };
  const la = m.link_adjudication!;
  la.unpinned_tier = null;
  la.unpinned_published = 86;
  la.unpinned_published_tier = "medium";
  const h = la.high!;
  h.published_high = 1105;
  h.adjudicated_high = 60;
  h.two_lens_high = 60;
  h.reviewed_high = 1105;
  h.review_as_of = null;
  h.reviewed_by_kind = { adjudication: 60, verdict_pair: 418, survivor_list: 627 };
  h.by_path = {
    account: { high: 3, adjudicated: 3, two_lens: 3, reviewed: 3 },
    "account+subagency": { high: 22, adjudicated: 22, two_lens: 22, reviewed: 22 },
    "account+tokens": { high: 34, adjudicated: 34, two_lens: 34, reviewed: 34 },
    "announcement+lexicon": {
      high: 1046, adjudicated: 1, two_lens: 1, with_match_basis: 700, reviewed: 1046,
    },
  };
  h.demoted_from_high = {
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
  };
  return m;
}

/** The pre-chain shape (chain F2's export), rebuilt from today's by removing
 *  what the decisions wave added: the withdrawn tier goes back into
 *  `methods` and out of `unmeasured`, the unpinned links publish at one tier
 *  again, and the high tier carries no recorded-review census. */
function preChain(m: SiteMeta): SiteMeta {
  const lp = m.link_precision!;
  const w = lp.withdrawn?.["account+subagency"];
  if (w) {
    lp.methods = {
      ...lp.methods,
      "account+subagency": {
        confirmed: w.confirmed,
        sampled: w.sampled,
        sample_id: w.sample_id,
        judged: w.judged,
      },
    };
  }
  delete lp.withdrawn;
  lp.unmeasured = (lp.unmeasured ?? []).filter((t) => t !== "account+subagency");
  const la = m.link_adjudication!;
  la.unpinned_tier = "medium";
  delete la.unpinned_published;
  delete la.unpinned_published_tier;
  const h = la.high!;
  delete h.reviewed_high;
  delete h.review_as_of;
  delete h.reviewed_by_kind;
  delete h.demoted_from_high;
  for (const path of Object.values(h.by_path ?? {})) {
    delete path.reviewed;
    delete path.reviewed_by_kind;
    delete path.announcement_reviewed;
    delete path.announcement_upheld;
  }
  return m;
}

describe("/methodology/ renders what gate 24 legs n and o bind", () => {
  it("on today's export: no leg n / leg o finding, and each new element renders exactly when its key is present", () => {
    // The identity override hands back (a clone of) exactly what the page read.
    let seen: SiteMeta | null = null;
    const root = renderPage((m) => (seen = m));
    const meta = seen! as SiteMeta;
    const { errors } = legs(root, meta);
    expect(errors).toEqual([]);
    // Bound to the export, whichever shape it is: an element the page
    // renders without its site_meta source, or a source it drops, fails.
    const has = (sel: string) => root.querySelector(sel) !== null;
    const withdrawn = Object.keys(meta.link_precision?.withdrawn ?? {});
    expect(has("[data-link-precision-withdrawn]")).toBe(withdrawn.length > 0);
    expect(has("[data-link-review-high]")).toBe(
      typeof meta.link_adjudication?.high?.reviewed_high === "number",
    );
    expect(has("[data-link-demoted-high]")).toBe(
      (meta.link_adjudication?.high?.demoted_from_high?.links ?? 0) > 0,
    );
  }, 30_000);

  it("on the pre-chain shape: no leg n / leg o finding, and nothing the new keys would render", () => {
    let seen: SiteMeta | null = null;
    const root = renderPage((m) => (seen = preChain(m)));
    const { errors } = legs(root, seen!);
    expect(errors).toEqual([]);
    // Nothing the new keys would render appears without them.
    expect(root.querySelector("[data-link-precision-withdrawn]") === null).toBe(true);
    expect(root.querySelector("[data-link-review-high]") === null).toBe(true);
    expect(root.querySelector("[data-link-demoted-high]") === null).toBe(true);
    expect(norm(root.querySelector("[data-link-adjudication]")!.text)).toMatch(
      /program element; those links publish at medium\./,
    );
  }, 30_000);

  it("on the post-chain shape: every new figure renders, and binds", () => {
    let seen: SiteMeta | null = null;
    const root = renderPage((m) => (seen = postChain(m)));
    const { errors, notes } = legs(root, seen!);
    expect(errors).toEqual([]);
    expect(notes.join(" ")).toMatch(/withdrawn tier\(s\) stated/);

    const withdrawn = norm(root.querySelector('[data-link-precision-withdrawn="account+subagency"]')!.text);
    expect(withdrawn).toBe(
      "A held-out sample of account / sub-agency links, judged on program " +
        "attribution, confirmed 0 of 58 (2026-09-11). On that figure the tier " +
        "was withdrawn (decided 2026-09-25): its 8,833 links " +
        "that no two-lens hand adjudication pinned no longer publish.",
    );
    expect(norm(root.querySelector("[data-link-adjudication]")!.text)).toContain(
      "8,475 of those found work that could not be pinned to any one program " +
        "element; 86 of them still publish, at medium, and the rest no longer publish.",
    );
    const review = norm(root.querySelector("[data-link-review-high]")!.text);
    expect(review).toMatch(/^All 1,105 carry a recorded review/);
    expect(review).toBe(
      "All 1,105 carry a recorded review, counted once under the strongest: 60 " +
        "a two-lens hand adjudication, 418 a per-proposal verdict pair and 627 " +
        "only a survivor-list entry, which records survival of the adversarial " +
        "pass, not its verdict.",
    );
    expect(norm(root.querySelector("[data-link-demoted-high]")!.text)).toBe(
      "91 more were demoted from high: 63 unadjudicated keyword matches, 5 " +
        "refuted in review, 12 rejected by a reviewer and 11 refuted by the " +
        "precision study.",
    );
    // The rule-fired history sentence waits on the tier NOT being withdrawn.
    const precision = norm(root.querySelector("[data-link-precision]")!.text);
    expect(precision).not.toMatch(/first sample \(2026-09-04\) asked only/);
    expect(precision).toContain(
      "by sub-agency and a pinning two-lens adjudication",
    );
    expect(precision).not.toMatch(/account\+subagency \d/);
  }, 30_000);

  it("a reason the page has no words for prints its code, never vanishes", () => {
    let seen: SiteMeta | null = null;
    const root = renderPage((m) => {
      const x = postChain(m);
      const d = x.link_adjudication!.high!.demoted_from_high!;
      d.links = 92;
      d.by_reason = { ...d.by_reason, some_future_reason: 1 };
      d.by_path["announcement+lexicon"] = { ...d.by_path["announcement+lexicon"], some_future_reason: 1 };
      return (seen = x);
    });
    expect(norm(root.querySelector("[data-link-demoted-high]")!.text)).toContain(
      "1 demoted as some_future_reason",
    );
    expect(legs(root, seen!).errors).toEqual([]);
  }, 30_000);
});

describe("/methodology/ prose the decisions wave rewrote", () => {
  it("#134: the header says Built <date>, never a data date", () => {
    const root = renderPage(null);
    const header = norm(root.querySelector("p.text-sm")!.text);
    expect(header).toMatch(/^Built [A-Z][a-z]+ \d{1,2}, \d{4}\.$/);
    expect(norm(root.text)).not.toMatch(/generated [A-Z][a-z]+ \d|[Dd]ata as of/);
  }, 30_000);

  it("#107(b)/#110: Medium names its kinds without ranking them", () => {
    const root = renderPage(null);
    const t = norm(root.text);
    expect(t).toContain("Medium: weaker evidence, of more than one kind.");
    expect(t).not.toContain("most such links are account-based");
    expect(t).not.toContain("usually under the same sub-agency");
  }, 30_000);

  it("#110: the announcement rule states what keeps a link high, and the reason for the rest", () => {
    const t = norm(renderPage(null).text);
    expect(t).toContain(
      "One stays at high only while a recorded review upholds it and no recorded " +
        "rejection or refutation applies; otherwise medium, with the reason recorded.",
    );
    expect(t).not.toMatch(/only links surviving both publish — at high/);
  }, 30_000);

  it("§2 lobbying: no year bound, the #176 numeric-code rule, the amendment rule", () => {
    const t = norm(renderPage(null).text);
    expect(t).not.toContain("filings for 2025 and prior years");
    expect(t).toContain(
      "an all-digit one only beside a budget-line label; none of the 1,631 " +
        "bare-number matches counted before this rule had one",
    );
    expect(t).not.toContain("qualifying only when the exact PE/BLI code appears");
    // Final review finding #5: the rule is R-DEC-AMEND's, which is scoped to
    // fct_influence — the yearly DOLLARS. fct_program_lobbying has no
    // `counted` filter, so the mention count in this same paragraph still
    // counts an amended quarter's original AND its amendment (801 of the
    // 12,571 rows came from 68 uncounted filings on the chain-G lake). An
    // unscoped "An amendment replaces its original" sat in that paragraph and
    // read as a rule for the mentions too.
    expect(t).toContain(
      "In those yearly figures an amendment replaces its original instead of " +
        "adding to it (a correction decided 2026-09-26); where a quarter’s " +
        "amendments disagree, the smallest counts (our copy keeps no posting date).",
    );
    expect(t).toContain(
      "(our copy keeps no posting date). Program mentions still count superseded reports.",
    );
    expect(t).not.toMatch(/(?:^|[.;] )An amendment replaces its original/);
  }, 30_000);

  /**
   * Decisions wave fix round 4 (review finding: the page stated the RULING
   * dates as the dates the changes took effect — "withdrawn … (2026-09-25)",
   * "Since 2026-09-26", "before 2026-09-26" — while the live site kept doing
   * the old thing until chain G's deploy, whose date no one knows yet). A
   * decision is dated as a decision ("decided <date>"), a measurement by its
   * export, and nothing says when the site changed. Checked on both shapes.
   */
  it("no sentence dates when the site changed; decisions are dated as decisions", () => {
    for (const fn of [null, postChain]) {
      const t = norm(renderPage(fn).text);
      expect(t).not.toMatch(/\b(?:[Ss]ince|[Uu]ntil|[Bb]efore|[Aa]fter) \d{4}-\d{2}-\d{2}/);
      expect(t).not.toMatch(/withdrawn on that figure \(\d{4}-\d{2}-\d{2}\)/);
      expect(t).not.toMatch(/moved up a band \(\d{4}-\d{2}-\d{2}/);
      // No internal ledger id reaches a reader (the ROADMAP defines R-INT-1..9
      // in its findings log, but the page has no reason to print either kind).
      expect(t).not.toMatch(/\bR-(?:DEC|INT)-/);
    }
    const bands = renderPage(null)
      .querySelectorAll("[data-historical-figures] tbody tr")
      .map((tr) => tr.querySelectorAll("td").map((td) => norm(td.text)))
      .find((cells) => cells[0] === "HHI bands");
    expect(bands?.[3]).toBe(
      "On the 2026-09-25 export these bands put 3 feed cards and 4 badges one " +
        "band higher; “Competitive” is now Unconcentrated.",
    );
  }, 30_000);

  it("#130: the warehouse's code-level rows are named, per row, on /downloads/", () => {
    const t = norm(renderPage(null).text);
    expect(t).toContain(
      "In the warehouse a shared code is one row, labelled scope = 'code'; " +
        "/downloads/ says of each whether it is one program's figure.",
    );
  }, 30_000);

  it("the corrections table ends with the bands' correction; the lobbying ones are stated in §2", () => {
    const root = renderPage(null);
    const rows = root
      .querySelectorAll("[data-historical-figures] tbody tr")
      .map((tr) => norm(tr.querySelectorAll("td")[0].text));
    expect(rows.slice(-2)).toEqual(["Concentration (HHI) wording", "HHI bands"]);
    // #176 and R-DEC-AMEND are labelled corrections where the figure is
    // described (§2), which the table's introduction now says.
    const t = norm(root.text);
    expect(t).toContain(
      "Corrections issued since are appended to the same table, newest last, or " +
        "stated where the figure is described.",
    );
  }, 30_000);
});
