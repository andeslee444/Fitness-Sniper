/**
 * Proof-it-can-fail for gate 24 leg (p).
 *
 * The claim fixtures are the strings this branch shipped on 2026-09-18 (chain C
 * run 4, 2026-09-25, rendered the counts 536 / 461 / 353 / 314 where these
 * say 444 / 384 / 240 / 200 — the fixtures only exercise the logic); the org
 * mix is the
 * shipped flow sidecars' own header.org tally, recomputed from
 * data/site/json/flows on 2026-09-18 (92 N, 59 F, 22 A, 14 DARPA, 6 MDA,
 * 4 OSD, 2 SOCOM, 1 DISA — 200 in total, unchanged from the brief's
 * 2026-09-10 measurement).
 *
 * The negative fixtures matter more than the positive ones here: (p2) is a
 * sweep over rendered text, where adjacent elements concatenate without a
 * space, and a matcher that reads a glued run as one sentence reports four
 * unrelated figures per page. The last two cases in the first block are the
 * exact glue shapes the 2026-09-12 build produces.
 */
import { describe, it, expect } from "vitest";
import {
  crosswalkClaimFindings,
  orgAttributionFindings,
  publishedLinkFigures,
} from "../datatruth.mjs";

const DECLARED = {
  "link-universe": 444,
  "bridged-request": 384,
  "high-confidence-links": 240,
  "district-linkable": 200,
  "district-linkable-unbridged": 34,
};
const CORPUS = { "index-rows": 1938, "program-pages": 2562, "detail-pages": 1936 };
/** The leaf fields of site_meta.link_adjudication that the swept pages render
 *  — READ, never re-derived. 8,474 (`unpinned`) and every `by_method.*` figure
 *  are deliberately NOT here: the block holds them, no page states them as a
 *  ratio, and admitting them was a free pass for any rotted literal that
 *  happened to equal one. */
const PUBLISHED = [12595, 9587, 768, 60];

describe("crosswalkClaimFindings", () => {
  it("accepts the two shipped ratios, because both are declared", () => {
    expect(
      crosswalkClaimFindings(
        [
          { url: "/flow/", text: "Budget→contractor links are drawn for 384 of 444 crosswalked PEs — 63.4% of the FY2026 request is not yet crosswalked." },
          { url: "/district/", text: "200 of 1,938 program elements have a follow-the-dollar view." },
        ],
        DECLARED,
        CORPUS,
      ),
    ).toEqual([]);
  });

  it("rejects a crosswalk claim whose numbers are declared nowhere", () => {
    const found = crosswalkClaimFindings(
      [{ url: "/district/", text: "17 of 1,741 programs currently crosswalkable." }],
      DECLARED,
      CORPUS,
    );
    expect(found).toHaveLength(2);           // 17 and 1,741
    expect(found.join(" ")).toContain("/district/");
    expect(found.join(" ")).toContain("declared");
  });

  it("fails when NO crosswalk claim is found at all (a broken scan)", () => {
    const found = crosswalkClaimFindings([{ url: "/flow/", text: "Two rivers, deliberately kept apart." }], DECLARED, CORPUS);
    expect(found.join(" ")).toContain("not one crosswalk claim");
  });

  it("fails a sweep that falls below the dated do-not-lower floor", () => {
    const found = crosswalkClaimFindings(
      [{ url: "/flow/", text: "Budget→contractor links are drawn for 384 of 444 crosswalked PEs." }],
      DECLARED,
      CORPUS,
      PUBLISHED,
      6,
    );
    expect(found.join(" ")).toContain("do-not-lower floor of 6");
    expect(found.join(" ")).toContain("do not");
  });

  it("lets fiscal years and percentages through", () => {
    expect(
      crosswalkClaimFindings(
        [{ url: "/flow/", text: "The FY2026 crosswalk bridges 384 of 444 PEs; 63.4% is not bridged." }],
        DECLARED,
        CORPUS,
      ),
    ).toEqual([]);
  });

  it("admits a figure the derived link blocks already publish, and only then", () => {
    const sentence =
      "As of 2026-09-12, 9,587 of the 12,595 links the crosswalk grades high or medium carry a per-award hand adjudication.";
    expect(crosswalkClaimFindings([{ url: "/methodology/", text: sentence }], DECLARED, CORPUS, PUBLISHED)).toEqual([]);
    // Without the block, the same true sentence reads as two undeclared
    // denominators — which is why (p2) READS site_meta rather than re-deriving.
    expect(crosswalkClaimFindings([{ url: "/methodology/", text: sentence }], DECLARED, CORPUS)).toHaveLength(2);
  });

  it("admits the complement /district/ computes from two declared counts", () => {
    expect(
      crosswalkClaimFindings(
        [
          {
            url: "/district/",
            text: "District data reflects only high-confidence award crosswalk links. 1,738 of 1,938 program elements have no district-level linkage.",
          },
        ],
        DECLARED,
        CORPUS,
      ),
    ).toEqual([]);
  });

  it("does not read a ratio out of a glued run that has no crosswalk word beside it", () => {
    // /methodology/, 2026-09-12: the dossier ratio sits one glued sentence
    // away from the crosswalk paragraph. It is a true number about a
    // different thing, and (p2) must not demand it be declared here.
    const found = crosswalkClaimFindings(
      [
        { url: "/flow/", text: "Budget→contractor links are drawn for 384 of 444 crosswalked PEs." },
        {
          url: "/methodology/",
          text: "Pages outside it say so in place of the flow: we could not defend the link, not that no money moved.Research dossiers — 50 of 1,938 programsDossiers exist for 50 of 1,938 programs, selected by ranking FY2026 requested dollars.",
        },
      ],
      DECLARED,
      CORPUS,
    );
    expect(found).toEqual([]);
  });

  it("never invents a number out of a glued digit run", () => {
    // /coverage/ renders "Program pages" and "1,936 of 2,562 program pages"
    // as adjacent elements, so the text reads "…Program pages1,936 of
    // 2,562…". A \b-only matcher finds the boundary between the comma and
    // the "9" and reports "936 of 2,562" — a figure the page never states
    // and no registry can declare. The lookbehind refuses it; the glued
    // number is skipped rather than invented (leg k2's rule: a glue may cost
    // a finding, never fabricate one).
    const found = crosswalkClaimFindings(
      [
        { url: "/flow/", text: "Budget→contractor links are drawn for 384 of 444 crosswalked PEs." },
        { url: "/coverage/", text: "The budget→award crosswalk is a limit.Program pages1,936 of 2,562 program pages carry detail-grade J-book justification." },
      ],
      DECLARED,
      CORPUS,
    );
    expect(found).toEqual([]);
    expect(found.join(" ")).not.toContain("936 of");
  });
});

describe("orgAttributionFindings", () => {
  const MIX = { N: 92, F: 59, A: 22, DARPA: 14, MDA: 6, OSD: 4, SOCOM: 2, DISA: 1 };

  it("catches the shipped /district/ prose attributing linkage to DARPA", () => {
    const found = orgAttributionFindings(
      [
        { url: "/district/", text: "200 of 1,938 programs currently crosswalkable (DARPA budget-to-award crosswalk covers DARPA and related programs)." },
        { url: "/district/CO-05/", text: "DARPA's account structure does that, while the services book many programs under one account." },
      ],
      MIX,
    );
    expect(found).toHaveLength(2);
    expect(found[0]).toContain("DARPA");
    expect(found[0]).toContain("14 of 200");
  });

  it("catches /methodology/'s own version of the same sentence", () => {
    const found = orgAttributionFindings(
      [{ url: "/methodology/", text: "Today that covers 200 of 1,938 programs, concentrated in DARPA lines whose account structure makes matching reliable." }],
      MIX,
    );
    expect(found).toHaveLength(1);
    expect(found[0]).toContain("14 of 200");
  });

  it("passes prose that names the mechanism instead of an organization", () => {
    expect(
      orgAttributionFindings(
        [{ url: "/district/", text: "A link is published only where a contract announcement names the program, or an account plus program-specific tokens does." }],
        MIX,
      ),
    ).toEqual([]);
  });

  it("passes the replacement sentences this branch shipped on 2026-09-18", () => {
    expect(
      orgAttributionFindings(
        [
          { url: "/district/", text: "District data reflects only high-confidence award crosswalk links. A budget line earns one only where the award record says more than an account code: a contract announcement that names the program, or an account plus program-specific tokens." },
          // Chain-D fix round 1 trimmed the §4 summary clause off the end of
          // this sentence (it restated the §4 reference the same sentence
          // makes); the fixture follows the shipped wording, and the assertion
          // is unchanged. The reason the leg stays silent is unchanged too,
          // and it is not the one this comment gave before fix round 2: the
          // shipped sentence names no organization, and it carries no
          // crosswalk cue either, so (p3) skips it at CROSSWALK_CUE
          // (datatruth.mjs) before any org is considered — as it did with the
          // clause as well. The cued mechanism sentence is exercised by the
          // /district/ entry above it and by "passes prose that names the
          // mechanism instead of an organization".
          { url: "/methodology/", text: "That covers 200 of 1,938 programs, spread across the service books." },
        ],
        MIX,
      ),
    ).toEqual([]);
  });

  it("passes the sentences the Task 26 fix wave ships on /district/ and /district/{code}/", () => {
    // site/src/app/district/page.tsx and [district]/page.tsx at db7ea6b8:
    // the mechanism is named without enumerating its paths.
    expect(
      orgAttributionFindings(
        [
          { url: "/district/", text: "District data reflects only high-confidence award crosswalk links. A budget line earns one only where more than an account code ties the award to it; methodology §4 says what does." },
          { url: "/district/AL-02/", text: "This page counts only links the crosswalk grades high, where more than an account code ties the award to the program; methodology §4 says what does." },
        ],
        MIX,
      ),
    ).toEqual([]);
  });

  it("recommends that wording, not the retired two-path enumeration, when it fires", () => {
    const found = orgAttributionFindings(
      [{ url: "/district/", text: "High-confidence crosswalk links are concentrated in DARPA lines." }],
      MIX,
    );
    expect(found).toHaveLength(1);
    expect(found[0]).toMatch(/only where more than an account code ties the award to it/);
    expect(found[0]).not.toMatch(/names the program, or account plus program tokens/);
  });

  it("still names an organization that really does hold the majority", () => {
    // Not a false negative: if the sidecars were 92% DARPA, the sentence the
    // branch deleted would have been true, and the leg must say so by
    // passing it rather than by having no opinion.
    expect(
      orgAttributionFindings(
        [{ url: "/district/", text: "The crosswalk covers DARPA and related programs." }],
        { DARPA: 180, N: 20 },
      ),
    ).toEqual([]);
  });

  it("still matches an org name that ends in a non-word character", () => {
    // `\b` after the `)` of "OSD (R&E)" can only match before a word
    // character, so the anchored form went permanently silent on such a name
    // instead of reporting it. Two shapes: a parenthesised name (the comment
    // above the matcher names this one) and one ending in a stop.
    const mix = { "OSD (R&E)": 14, "R&E.": 6, N: 180 };
    const found = orgAttributionFindings(
      [
        { url: "/district/", text: "The crosswalk is concentrated in OSD (R&E) lines whose account structure makes matching reliable." },
        { url: "/methodology/", text: "Crosswalk coverage is concentrated in lines booked under R&E. That account structure makes matching reliable." },
      ],
      mix,
    );
    expect(found).toHaveLength(2);
    expect(found[0]).toContain("OSD (R&E)");
    expect(found[0]).toContain("14 of 200");
    expect(found[1]).toContain("R&E.");
    expect(found[1]).toContain("6 of 200");
  });

  it("fails a vacuously-empty org mix rather than passing", () => {
    expect(orgAttributionFindings([{ url: "/district/", text: "anything" }], {}).join(" ")).toContain("no flow sidecars");
  });
});

describe("publishedLinkFigures", () => {
  /** The 2026-09-18 artifact, trimmed to the fields that matter here. */
  const META = {
    link_adjudication: {
      published: 12595,
      adjudicated: 9587,
      unpinned: 8474,
      by_method: {
        "account+subagency": { adjudicated: 9173, published: 9337 },
        "announcement+lexicon": { adjudicated: 0, published: 708 },
        "fpds-ap": { adjudicated: 0, published: 1910 },
      },
      high: {
        published_high: 768,
        two_lens_high: 60,
        adjudicated_high: 60,
        by_path: {
          "account+tokens": { adjudicated: 34, high: 34, two_lens: 34 },
          "announcement+lexicon": { adjudicated: 0, high: 708, two_lens: 0, with_match_basis: 384 },
        },
      },
    },
    link_precision: {
      methods: {
        "announcement+lexicon": { confirmed: 51, sampled: 54, judged: "2026-09-04" },
        "fpds-ap": { confirmed: 94, sampled: 120, judged: "2026-09-04" },
      },
    },
  };

  it("admits the leaf fields the swept passages actually render", () => {
    const got = publishedLinkFigures(META);
    // "9,587 of the 12,595 links", "60 of the 768 links published at high",
    // and the four precision ratios — every one of them text on /methodology/.
    for (const n of [12595, 9587, 768, 60, 51, 54, 94, 120]) {
      expect(got).toContain(n);
    }
  });

  it("admits adjudicated_high in its own right, not through two_lens_high", () => {
    // §4 renders `{adjudicated_high} of the {published_high} links published at
    // high` (methodology/page.tsx:311 -> :844); two_lens_high is the trailing
    // "all 60 challenged by two…" clause. They are both 60 on today's
    // artifact, so admitting only one would pass by coincidence until the day
    // adjudication pins a link two lenses have not both seen.
    const meta = {
      ...META,
      link_adjudication: {
        ...META.link_adjudication,
        high: { ...META.link_adjudication.high, adjudicated_high: 61 },
      },
    };
    const got = publishedLinkFigures(meta);
    expect(got).toContain(61);
    expect(got).toContain(60);
  });

  /**
   * THE DEFECT THIS CLOSES. The shipped version walked both blocks and pushed
   * every finite number it found — 22 distinct integers on the 2026-09-18
   * artifact — so `unpinned`, every `by_method.*` counter and every
   * `high.by_path.*` counter became a free pass for any crosswalk ratio that
   * happened to collide with one. None of them is stated as an `N of M` ratio
   * on any swept page.
   *
   * `by_method.*.published` outlived the first cut of the enumeration on the
   * reasoning that §4 carries a per-method tier table. It does not: `by_method`
   * has exactly one reader in site/src, the type declaration at lib/data.ts:265,
   * and 9,337 / 1,910 / 708 / 527 / 113 appear nowhere in the built pages. The
   * live hazard was 1,910, which sits 28 away from the rendered corpus
   * denominator 1,938 — a rotted "200 of 1,910 programs" would have been waved
   * through by the leg that exists to catch it.
   */
  it("does NOT admit a number the block holds but no passage renders", () => {
    const got = publishedLinkFigures(META);
    for (const n of [8474, 9173, 34, 9337, 1910, 708]) {
      expect(got).not.toContain(n);
    }
  });

  it("lets a claim through on a leaf, and reports the same claim on a non-leaf", () => {
    const leaf = "9,587 of the 12,595 links the crosswalk grades high or medium carry an adjudication.";
    expect(
      crosswalkClaimFindings([{ url: "/methodology/", text: leaf }], DECLARED, CORPUS, publishedLinkFigures(META)),
    ).toEqual([]);
    // `unpinned` (8,474) and `by_method["account+subagency"].adjudicated`
    // (9,173) are both in the block and both admitted by the old walk.
    const nonLeaf = "8,474 of the 9,173 links the crosswalk grades medium sit unpinned.";
    expect(
      crosswalkClaimFindings([{ url: "/methodology/", text: nonLeaf }], DECLARED, CORPUS, publishedLinkFigures(META)),
    ).toHaveLength(2);
  });

  it("reports a claim that collides with a by_method figure no page renders", () => {
    // The shape the free pass would have hidden: 1,910 is
    // by_method["fpds-ap"].published, 28 away from the corpus denominator the
    // page really states (1,938), and this sentence is a crosswalk claim.
    const rotted = "Follow-the-dollar flows cover 200 of the 1,910 programs in the index.";
    const found = crosswalkClaimFindings(
      [{ url: "/program/000042/", text: rotted }],
      DECLARED,
      CORPUS,
      publishedLinkFigures(META),
    );
    expect(found).toHaveLength(1);
    expect(found[0]).toContain("1,910");
  });

  it("returns nothing for a site_meta with no link blocks at all", () => {
    expect(publishedLinkFigures({})).toEqual([]);
    expect(publishedLinkFigures(undefined)).toEqual([]);
  });
});
