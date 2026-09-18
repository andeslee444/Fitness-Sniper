/**
 * Unit tests for gate 21 leg (n) — a shared BLI code's members own their own
 * awards (ROADMAP #70), name their own appropriation in the title block and
 * publish their own J-book narratives and detail rows (ROADMAP #82), and the
 * leg is not vacuous.
 *
 * The floors are the reason this file exists. The leg's per-page checks are
 * all perfectly satisfied by a corpus in which every member page shows ZERO
 * awards (split_key drift), renders NO appropriation line (a header
 * regression), or publishes NO J-book row (the same drift on the narrative
 * axis) — "nothing to object to" and "the regression" are the same
 * observation without a floor. The leg's first standalone run printed
 * "0 member page(s) carry 0 award row(s)" and PASSED. These tests pin that
 * it cannot do so again, on any of the three axes.
 *
 * Synthetic pe_bli codes are used throughout; the leg reads page HTML through
 * the injected `pageHtml` so no build is needed and the stub check finds
 * nothing on disk.
 *
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import { runSplitKeyAwardsLeg, evidenceBadges } from "../program-skeleton.mjs";

/** Shape of the real corpus, transposed onto synthetic codes: 13 shared
 *  codes — 10 account-split (TA…TJ) and 3 organization-split (TK, TL, TM —
 *  one account 0300D, distinct orgs, like '20'/'30'/'500') — 7 member pages
 *  carrying 86 award rows in total (0145-PANMC 3, 2101-WPN 23, 3010-SCN 5,
 *  3010-OPN 3, 3050-OPN 50, 3215-OPN 1, 4217-OPN 1 — measured 2026-09-04
 *  from budget_line_awards), and 20 account-split member pages (measured
 *  2026-09-05 from programs.json, re-measured 2026-09-11: still 20). */
const LIVE_SHAPE = [
  ["TA", [0, 3]],
  ["TB", [0, 23]],
  ["TC", [5, 3]],
  ["TD", [0, 50]],
  ["TE", [0, 1]],
  ["TF", [0, 1]],
  ["TG", [0, 0]],
  ["TH", [0, 0]],
  ["TI", [0, 0]],
  ["TJ", [0, 0]],
  ["TK", [0, 0]],
  ["TL", [0, 0]],
  ["TM", [0, 0, 0]],
];
const ORG_SPLIT = new Set(["TK", "TL", "TM"]);

/** A member page's title block + WHO card, the way the built page emits them
 *  (h1[data-program-name], span[data-program-account], the answer-who card).
 *  `accountTitle` overrides what the appropriation line SAYS; `omitAccount`
 *  drops the element; `withheld` stamps data-who-withheld; `tier` is the WHO
 *  card's declared tier. */
function memberHtml(
  p,
  { accountTitle = p.account_title, omitAccount = false, withheld = false, tier = "none" } = {},
) {
  const account = omitAccount
    ? ""
    : `<span data-program-account="${p.account}">${accountTitle} · <code>${p.account}</code></span>`;
  return (
    `<html><body><h1 data-program-name="true">${p.title}</h1>` +
    `<div class="flex"><a href="/agency/${p.org}/">${p.org}</a>${account}</div>` +
    `<div data-testid="answer-who"><span data-who-tier="${tier}"` +
    `${withheld ? ' data-who-withheld="shared-code"' : ""}>x</span></div>` +
    `<div data-section="figures"></div></body></html>`
  );
}

/** Build {programs, sidecars, html} from [[pe, [awardsPerMember…]], …].
 *  `page(p, siblings)` returns the HTML for one member (default: correct).
 *
 *  J-book rows (ROADMAP #82, the narrative axis): by default each member
 *  publishes TWO narratives and FIVE details of its OWN — the live shape,
 *  where every one of the 27 member pages has its own PB2026 volume.
 *  `fusedJbook` reproduces the pre-fix corpus instead: every member carries
 *  every member's rows, which is what a bare-pe_bli lookup produces.
 *  `noJbook` empties them, the shape the floor exists to catch.
 *
 *  Mentions: `mentionCodes` names the codes whose members all render ONE
 *  shared lobbying filing (the live shape on 6 of 13 codes). By default that
 *  filing is `pe_literal` — it names the shared code itself, so it is
 *  evidence for every member, and each sidecar declares the "code" basis.
 *  `mentionKind` switches the tier ("multi_token"), `mentionTerm(p)` decides
 *  what each member's row matched, and `declareMentions` controls whether the
 *  sidecar declares any basis at all. */
function corpus(
  shape,
  {
    piidPerMember = false,
    page = (p) => memberHtml(p),
    withheld = () => false,
    fusedJbook = false,
    noJbook = false,
    mentionCodes = new Set(),
    declareMentions = true,
    mentionKind = "pe_literal",
    mentionTerm = (p) => p.pe_bli,
    mentionDeclaration = null,
  } = {},
) {
  const programs = [];
  const sidecars = new Map();
  const html = new Map();
  let piid = 0;
  const jbookFids = (pe, i, kind, n) =>
    Array.from({ length: n }, (_, k) => ({ fact_id: `${kind}-${pe}-${i}-${k}` }));
  for (const [pe, counts] of shape) {
    const members = counts.map((n, i) => ({
      pe_bli: pe,
      slug: `${pe}-M${i}`,
      title: `Program ${pe}-${i}`,
      org: ORG_SPLIT.has(pe) ? `ORG${i}` : "N",
      account: ORG_SPLIT.has(pe) ? "0300D" : `A${i}`,
      account_title: ORG_SPLIT.has(pe) ? "Procurement, Defense-Wide" : `Appropriation ${pe}-${i}`,
      award_count: n,
    }));
    const allIdx = counts.map((_n, i) => i);
    members.forEach((p, i) => {
      const awards = [];
      for (let k = 0; k < counts[i]; k++) {
        awards.push({
          award_piid: piidPerMember ? `PIID-${pe}-${k}` : `PIID-${++piid}`,
          recipient_name: "ACME",
          confidence: "medium",
        });
      }
      const volumes = noJbook ? [] : fusedJbook ? allIdx : [i];
      const side = {
        awards,
        narratives: volumes.flatMap((v) => jbookFids(pe, v, "narr", 2)),
        details: volumes.flatMap((v) => jbookFids(pe, v, "det", 5)),
        summary: { concentration_withheld: withheld(p) },
      };
      if (mentionCodes.has(pe)) {
        side.mentions = [{
          filing_uuid: `uuid-${pe}`,
          client_name: "ACME LOBBYING",
          evidence_kind: mentionKind,
          matched_term: mentionTerm(p),
        }];
        if (declareMentions) {
          side.mentions_shared_code =
            mentionDeclaration ??
            { [mentionKind]: mentionKind === "pe_literal" ? "code" : "title" };
        }
      }
      programs.push(p);
      sidecars.set(p.slug, side);
      html.set(p.slug, page(p, members));
    });
  }
  return { programs, sidecars, html };
}

function run(shape, opts) {
  const { programs, sidecars, html } = corpus(shape, opts);
  const errors = [];
  const notes = [];
  runSplitKeyAwardsLeg({
    errors,
    notes,
    sidecars,
    programs,
    pageHtml: (slug) => html.get(slug) ?? null,
  });
  return { errors, notes };
}

/** Org-split members render no appropriation line (their org discriminates). */
const livePage = (p) => memberHtml(p, { omitAccount: ORG_SPLIT.has(p.pe_bli) });

describe("leg n — non-vacuity floors", () => {
  it("passes on the corpus this branch publishes and says what it saw", () => {
    const { errors, notes } = run(LIVE_SHAPE, { page: livePage });
    expect(errors).toEqual([]);
    expect(notes[0]).toContain("13 shared BLI code(s) checked");
    expect(notes[0]).toContain("7 member page(s) carry 86 award row(s)");
    expect(notes[0]).toContain("20 account-split member page(s) name their own appropriation");
  });

  it("FAILS when every member page shows zero awards", () => {
    const zeroed = LIVE_SHAPE.map(([pe, counts]) => [pe, counts.map(() => 0)]);
    const { errors, notes } = run(zeroed, { page: livePage });
    expect(notes).toEqual([]);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("only 0 shared-code member page(s) carry 0 award row(s)");
    expect(errors[0]).toContain("do not lower it to fit the build");
  });

  it("FAILS when one key's links stop reaching their page", () => {
    const partial = LIVE_SHAPE.map(([pe, counts]) =>
      pe === "TD" ? [pe, counts.map(() => 0)] : [pe, counts],
    );
    const { errors } = run(partial, { page: livePage });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("6 shared-code member page(s) carry 36 award row(s)");
  });

  it("still reports the real defects it was written for", () => {
    const { errors } = run(LIVE_SHAPE, { page: livePage, piidPerMember: true });
    const fused = errors.filter((e) => e.includes("is listed on BOTH"));
    expect(fused.length).toBeGreaterThan(0);
    expect(fused[0]).toContain("their money is never combined");
  });

  it("FAILS when programs.json carries no shared codes at all", () => {
    const { errors, notes } = run([["TA", [3]]], { page: livePage });
    expect(notes).toEqual([]);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("carries 0 shared BLI code(s) (floor 10");
    expect(errors[0]).toContain("do not lower the floor");
  });

  it("FAILS just below the shared-code floor, and passes once every floor is met (11 codes)", () => {
    const nine = LIVE_SHAPE.slice(0, 9);
    expect(run(nine, { page: livePage }).errors[0]).toContain("carries 9 shared BLI code(s) (floor 10");
    // Eleven codes = the ten account-split ones (20 title-block pages,
    // clearing the appropriation-line floor of 16) plus one org-split pair,
    // for 22 member pages publishing their own J-book rows — exactly check
    // 8's floor. The award floors are met by the first ten alone (7 pages /
    // 86 rows). Ten codes alone would clear every floor but check 8's, which
    // is measured on the whole 27-member population.
    const eleven = LIVE_SHAPE.slice(0, 11);
    expect(run(eleven, { page: livePage }).errors).toEqual([]);
  });
});

describe("leg n — the title block names the member's own appropriation (ROADMAP #82)", () => {
  it("FAILS when a member page wears its sibling's appropriation", () => {
    // The #56 fusion shape relocated into the header: 3010-OPN's page
    // saying "Shipbuilding and Conversion, Navy".
    const page = (p, siblings) =>
      p.slug === "TC-M1"
        ? memberHtml(p, { accountTitle: siblings[0].account_title })
        : livePage(p);
    const { errors } = run(LIVE_SHAPE, { page });
    expect(errors).toHaveLength(2);
    expect(errors[0]).toContain("/program/TC-M1/ title block reads");
    expect(errors[0]).toContain('expected its own appropriation "Appropriation TC-1"');
    expect(errors[1]).toContain("names its sibling's appropriation");
  });

  it("FAILS when an account-split member renders no appropriation line", () => {
    const page = (p) => (p.slug === "TA-M0" ? memberHtml(p, { omitAccount: true }) : livePage(p));
    const { errors } = run(LIVE_SHAPE, { page });
    expect(errors.some((e) => e.includes("/program/TA-M0/ renders 0 [data-program-account]"))).toBe(true);
  });

  it("FAILS when an organization-split member renders one", () => {
    const page = (p) => (p.slug === "TK-M0" ? memberHtml(p) : livePage(p));
    const { errors } = run(LIVE_SHAPE, { page });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("/program/TK-M0/ is an organization-split member");
    expect(errors[0]).toContain("discriminates nothing");
  });

  it("FAILS below the appropriation-line floor even when every rendered line is correct", () => {
    // Five account-split members go dark: 15 checkable pages, floor 16.
    const dark = new Set(["TG-M0", "TG-M1", "TH-M0", "TH-M1", "TI-M0"]);
    const page = (p) => (dark.has(p.slug) ? memberHtml(p, { omitAccount: true }) : livePage(p));
    const { errors } = run(LIVE_SHAPE, { page });
    const floor = errors.filter((e) => e.includes("account-split member page(s) rendered a checkable title block"));
    expect(floor).toHaveLength(1);
    expect(floor[0]).toContain("only 15 account-split member page(s)");
    expect(floor[0]).toContain("floor 16, measured 2026-09-05 at 20");
  });

  it("FAILS when the disambiguation stub renders an appropriation line", () => {
    // The stub is a chooser BETWEEN accounts; naming one of them in its own
    // title block would answer the question it exists to ask.
    const { programs, sidecars, html } = corpus(LIVE_SHAPE, { page: livePage });
    html.set(
      "TA",
      '<html><body><span data-program-account="A0">Appropriation TA-0</span></body></html>',
    );
    const errors = [];
    runSplitKeyAwardsLeg({ errors, notes: [], sidecars, programs, pageHtml: (s) => html.get(s) ?? null });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("the /program/TA/ disambiguation stub renders [data-program-account]");
  });

  it("FAILS when a member has a sidecar but no built page", () => {
    const { programs, sidecars, html } = corpus(LIVE_SHAPE, { page: livePage });
    html.delete("TB-M1");
    const errors = [];
    runSplitKeyAwardsLeg({ errors, notes: [], sidecars, programs, pageHtml: (s) => html.get(s) ?? null });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("/program/TB-M1/ has a sidecar but no built page");
  });
});

describe("leg n — a withheld concentration figure is said, not hidden (ROADMAP #82)", () => {
  it("passes when payload and page agree (both members of TC withheld)", () => {
    const withheld = (p) => p.pe_bli === "TC";
    const page = (p) => memberHtml(p, { omitAccount: ORG_SPLIT.has(p.pe_bli), withheld: p.pe_bli === "TC" });
    expect(run(LIVE_SHAPE, { page, withheld }).errors).toEqual([]);
  });

  it("FAILS when the sidecar says withheld but the none-tier card does not", () => {
    const { errors } = run(LIVE_SHAPE, { page: livePage, withheld: (p) => p.slug === "TC-M0" });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("/program/TC-M0/ sidecar says concentration_withheld=true");
  });

  it("FAILS when the card says withheld but the sidecar does not", () => {
    const page = (p) => memberHtml(p, { omitAccount: ORG_SPLIT.has(p.pe_bli), withheld: p.slug === "TC-M1" });
    const { errors } = run(LIVE_SHAPE, { page });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("/program/TC-M1/ renders [data-who-withheld] but its sidecar");
  });

  it("FAILS when a stronger tier answers on a withheld member", () => {
    // The brief planned to SCOPE check 7 to the "none" tier, on the reading
    // that a stronger tier may legitimately answer instead. It cannot: a
    // withheld member carries linked awards by construction, and every
    // stronger tier's closing sentence ("in high-confidence matched awards"
    // needs the block this page does not have; "not yet crosswalked to
    // award data"; "No contract award is linked to this line") is either
    // impossible or false above that member's own Related Awards table. The
    // exporter's per-member awards guard (#80 fix round 1, made per member
    // by #82) is what keeps it so — and this check is what notices if that
    // guard is ever dropped.
    const page = (p) =>
      p.slug === "TC-M0"
        ? memberHtml(p, { tier: "jbook" })
        : memberHtml(p, { omitAccount: ORG_SPLIT.has(p.pe_bli), withheld: p.pe_bli === "TC" });
    const { errors } = run(LIVE_SHAPE, { page, withheld: (p) => p.pe_bli === "TC" });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain('/program/TC-M0/ sidecar says concentration_withheld=true');
    expect(errors[0]).toContain('declares tier "jbook"');
  });

  it("FAILS when the withheld marker migrates onto a stronger tier", () => {
    // The other half of the tier clause: the payload IS withheld and the
    // marker IS rendered, but on a tier whose own sentence names companies
    // or dollars. Without the tier clause both halves of check 7 are
    // satisfied and the page passes while saying two contradictory things.
    const page = (p) =>
      p.slug === "TC-M0"
        ? memberHtml(p, { tier: "lobbying", withheld: true })
        : memberHtml(p, { omitAccount: ORG_SPLIT.has(p.pe_bli), withheld: p.pe_bli === "TC" });
    const { errors } = run(LIVE_SHAPE, { page, withheld: (p) => p.pe_bli === "TC" });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain('declares tier "lobbying"');
  });
});

describe("leg n — each member publishes its OWN J-book (ROADMAP #82, narrative axis)", () => {
  it("passes on the corpus this branch publishes and says what it saw", () => {
    const { errors, notes } = run(LIVE_SHAPE, { page: livePage });
    expect(errors).toEqual([]);
    expect(notes[0]).toContain("27 member page(s) publish their own J-book rows");
    expect(notes[0]).toContain("no narrative or detail fact id on two members");
  });

  it("FAILS on the pre-fix corpus, where both members publish both volumes", () => {
    // Measured 2026-09-12 before the fix: all 13 shared codes published
    // identical narratives and identical details on every member, so
    // /program/3010-SCN/ rendered the OPN program's mission prose and money
    // under the LPD Flight II heading with every citation resolving.
    const { errors } = run(LIVE_SHAPE, { page: livePage, fusedJbook: true });
    const narr = errors.filter((e) => e.includes("J-book narrative"));
    const det = errors.filter((e) => e.includes("J-book detail"));
    expect(narr.length).toBeGreaterThan(0);
    expect(det.length).toBeGreaterThan(0);
    expect(narr[0]).toContain("is published on BOTH /program/");
    expect(narr[0]).toContain("documented in different J-book volumes");
  });

  it("FAILS when ONE narrative crosses to the sibling", () => {
    const { programs, sidecars, html } = corpus(LIVE_SHAPE, { page: livePage });
    // TC-M1 (the '3010-OPN' analogue) publishes one of TC-M0's narratives.
    sidecars.get("TC-M1").narratives.push({ fact_id: "narr-TC-0-0" });
    const errors = [];
    runSplitKeyAwardsLeg({
      errors, notes: [], sidecars, programs, pageHtml: (s) => html.get(s) ?? null,
    });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("J-book narrative narr-TC-0-0");
    expect(errors[0]).toContain("/program/TC-M0/ and /program/TC-M1/");
  });

  it("FAILS when every member page publishes no J-book row at all", () => {
    // The no-duplicate assertion above is satisfied perfectly by silence,
    // and silence is exactly what split_key drift between the J-book indexes
    // and the sidecar writer produces.
    const { errors, notes } = run(LIVE_SHAPE, { page: livePage, noJbook: true });
    expect(notes).toEqual([]);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("only 0 shared-code member page(s) publish a J-book");
    expect(errors[0]).toContain("floor 22, measured 2026-09-12 at 27");
    expect(errors[0]).toContain("do not lower the floor");
  });

  it("FAILS just below the J-book floor and passes at it", () => {
    const dark = new Set(["TG-M0", "TG-M1", "TH-M0", "TH-M1", "TI-M0", "TI-M1"]);
    const { programs, sidecars, html } = corpus(LIVE_SHAPE, { page: livePage });
    for (const slug of dark) {
      sidecars.get(slug).narratives = [];
      sidecars.get(slug).details = [];
    }
    const errors = [];
    runSplitKeyAwardsLeg({
      errors, notes: [], sidecars, programs, pageHtml: (s) => html.get(s) ?? null,
    });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("only 21 shared-code member page(s) publish a J-book");
    // one page back above the floor and the leg is clean again
    sidecars.get("TI-M1").details = [{ fact_id: "det-TI-1-0" }];
    const errors2 = [];
    runSplitKeyAwardsLeg({
      errors: errors2, notes: [], sidecars, programs, pageHtml: (s) => html.get(s) ?? null,
    });
    expect(errors2).toEqual([]);
  });

  it("allows a pe_literal mention on both members — the filing names the CODE", () => {
    // A `pe_literal` filing's activity description contains the budget-line
    // code itself, which names the LINE and nothing finer, so on a shared
    // code it is evidence for every member. That is a rule, and the sidecar
    // states it per row ({pe_literal: "code"}).
    const { errors } = run(LIVE_SHAPE, {
      page: livePage,
      mentionCodes: new Set(["TA", "TB", "TK", "TL", "TM"]),
    });
    expect(errors).toEqual([]);
  });

  it("FAILS when a mention is repeated with no declaration", () => {
    const { errors } = run(LIVE_SHAPE, {
      page: livePage,
      mentionCodes: new Set(["TA"]),
      declareMentions: false,
    });
    // one per member for the undeclared payload, plus the cross-member repeat
    expect(
      errors.some((e) => e.includes("declares no per-row mentions_shared_code basis")),
    ).toBe(true);
    expect(
      errors.some(
        (e) =>
          e.includes("appears on TA-M0, TA-M1") &&
          e.includes("declare no mentions_shared_code basis for pe_literal"),
      ),
    ).toBe(true);
  });

  // ── the mention half's own defect (fix round 1, 2026-09-18) ──────────────
  // The live 0145: the mart is keyed on the BARE code, so a multi_token row
  // that qualified by matching ONE member's title tokens arrives at both
  // members. /program/0145-APN/ "F/A-18E/F (Fighter) Hornet" rendered 5 rows
  // matched `General|Purpose` — the SIBLING's title ("General Purpose
  // Bombs") — each badged "matched 2+ distinct, non-generic words from this
  // program's title". Check 8 used to exempt exactly those rows.
  const shape0145 = (opts = {}) => {
    const built = corpus(LIVE_SHAPE, {
      page: livePage,
      mentionCodes: new Set(["TA"]),
      mentionKind: "multi_token",
      mentionTerm: () => "General|Purpose",
      ...opts,
    });
    built.programs.find((p) => p.slug === "TA-M0").title = "F/A-18E/F (Fighter) Hornet";
    built.programs.find((p) => p.slug === "TA-M1").title = "General Purpose Bombs";
    return built;
  };
  const runBuilt = ({ programs, sidecars, html }) => {
    const errors = [];
    const notes = [];
    runSplitKeyAwardsLeg({
      errors, notes, sidecars, programs, pageHtml: (s) => html.get(s) ?? null,
    });
    return { errors, notes };
  };

  it("FAILS on the 0145 shape — a multi_token row on the member whose title lacks the terms", () => {
    const { errors } = runBuilt(shape0145());
    const offending = errors.filter((e) => e.includes("TA-M0"));
    expect(offending).toHaveLength(1);
    expect(offending[0]).toContain("General|Purpose");
    expect(offending[0]).toContain("F/A-18E/F (Fighter) Hornet");
    expect(offending[0]).toContain("does not carry General, Purpose");
    // the member whose title DOES carry them keeps its row, uncomplained-about
    expect(errors.some((e) => e.includes("TA-M1"))).toBe(false);
  });

  it("passes on the 2292 shape — identical member titles, so the row is true on both", () => {
    const built = shape0145();
    built.programs.find((p) => p.slug === "TA-M0").title = "General Purpose Bombs";
    const { errors, notes } = runBuilt(built);
    expect(errors).toEqual([]);
    expect(notes[0]).toContain("2 title-basis row(s) carry every matched term");
  });

  // ── the quoted badge is the one the PAGE shows, per tier ────────────────
  //
  // The message hardcoded multi_token's wording ("2+ distinct, non-generic
  // words from this program's title") for EVERY non-pe_literal tier, so an
  // alias failure told the reader to go look for a badge that page does not
  // render — and the sentence it quoted is evidenceKindLongExplanation's,
  // which no mention row renders at all. Both halves are now read out of
  // src/lib/evidence.ts, the table the row itself calls.
  it("quotes multi_token's OWN badge on a multi_token failure", () => {
    const { errors } = runBuilt(shape0145());
    const offending = errors.filter((e) => e.includes("TA-M0"));
    expect(offending[0]).toContain('the badge "matched 2+ title words"');
    expect(offending[0]).toContain("2+ distinct title words found together");
    expect(offending[0]).not.toContain("matched a known alias");
  });

  it("quotes ALIAS's badge on an alias failure, not multi_token's", () => {
    const { errors } = runBuilt(
      shape0145({ mentionKind: "alias", mentionTerm: () => "Super Hornet" }),
    );
    const offending = errors.filter(
      (e) => e.includes("TA-M1") && e.includes("alias lobbying mention"),
    );
    expect(offending).toHaveLength(1);
    expect(offending[0]).toContain('the badge "matched a known alias"');
    expect(offending[0]).toContain("curated, verified alias");
    expect(offending[0]).not.toContain("2+ distinct");
    expect(offending[0]).not.toContain("words from");
  });

  it("reads the badge table out of src/lib/evidence.ts, and says so if it cannot", () => {
    const table = evidenceBadges();
    expect(table.multi_token.label).toBe("matched 2+ title words");
    expect(table.alias.label).toBe("matched a known alias");
    expect(table.pe_literal.label).toBe("PE code cited directly");
    for (const kind of ["multi_token", "alias", "pe_literal"]) {
      expect(table[kind].title.length).toBeGreaterThan(20);
    }
    // A module that no longer carries the table must fail loudly rather than
    // hand the leg a stale hand-copy.
    expect(() => evidenceBadges("/no/such/evidence.ts")).toThrow(/evidence/i);
  });

  it("FAILS a wrong declaration: a multi_token row declared on the pe_literal basis", () => {
    // The gate reads the declaration and never trusts it. Declaring "code"
    // for a multi_token row is the retired blanket rule restated per tier.
    const { errors } = runBuilt(
      shape0145({ mentionDeclaration: { multi_token: "code" } }),
    );
    expect(
      errors.some((e) => e.includes('declares mentions_shared_code multi_token="code"')),
    ).toBe(true);
  });

  it("FAILS a row whose evidence tier the sidecar declares no basis for", () => {
    const { errors } = runBuilt(
      shape0145({ mentionDeclaration: { pe_literal: "code" } }),
    );
    // twice over: once per page, and once for the repeat across both members
    expect(
      errors.filter(
        (e) =>
          e.includes("publishes a multi_token lobbying mention") &&
          e.includes("declares no basis for"),
      ),
    ).toHaveLength(2);
    expect(
      errors.some((e) =>
        e.includes("multi_token lobbying mention uuid-TA|ACME LOBBYING|General|Purpose appears on TA-M0, TA-M1"),
      ),
    ).toBe(true);
  });

  it("never objects to a mention that only ONE member renders", () => {
    const { programs, sidecars, html } = corpus(LIVE_SHAPE, {
      page: livePage,
      mentionCodes: new Set(["TA"]),
    });
    sidecars.get("TA-M1").mentions = [];
    delete sidecars.get("TA-M1").mentions_shared_code;
    const errors = [];
    runSplitKeyAwardsLeg({
      errors, notes: [], sidecars, programs, pageHtml: (s) => html.get(s) ?? null,
    });
    expect(errors).toEqual([]);
  });
});
