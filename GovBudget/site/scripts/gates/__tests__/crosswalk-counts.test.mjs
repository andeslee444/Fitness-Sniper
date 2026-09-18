/**
 * Proof-it-can-fail for gate 24 leg (p).
 *
 * The claim fixtures are the strings this branch ships; the org mix is the
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
import { crosswalkClaimFindings, orgAttributionFindings } from "../datatruth.mjs";

const DECLARED = {
  "link-universe": 444,
  "bridged-request": 384,
  "high-confidence-links": 240,
  "district-linkable": 200,
  "district-linkable-unbridged": 34,
};
const CORPUS = { "index-rows": 1938, "program-pages": 2562, "detail-pages": 1936 };
/** What site_meta.link_adjudication publishes — READ, never re-derived. */
const PUBLISHED = [12595, 9587, 8474, 768, 60];

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

  it("passes the replacement sentences this branch ships", () => {
    expect(
      orgAttributionFindings(
        [
          { url: "/district/", text: "District data reflects only high-confidence award crosswalk links. A budget line earns one only where the award record says more than an account code: a contract announcement that names the program, or an account plus program-specific tokens." },
          { url: "/methodology/", text: "That covers 200 of 1,938 programs, spread across the service books; the tier is built from announcements naming a program and adjudicator-pinned account matches." },
        ],
        MIX,
      ),
    ).toEqual([]);
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

  it("fails a vacuously-empty org mix rather than passing", () => {
    expect(orgAttributionFindings([{ url: "/district/", text: "anything" }], {}).join(" ")).toContain("no flow sidecars");
  });
});
