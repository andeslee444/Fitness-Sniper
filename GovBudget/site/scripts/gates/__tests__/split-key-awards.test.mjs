/**
 * Unit tests for gate 21 leg (n) — a shared BLI code's members own their own
 * awards (ROADMAP #70), name their own appropriation in the title block and
 * publish their own J-book narratives and detail rows (ROADMAP #82), publish
 * no lobbying evidence and say so (ruling R-INT-9, 2026-09-25), and the leg
 * is not vacuous.
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
import {
  runSplitKeyAwardsLeg,
  evidenceBadges,
  SHARED_CODE_LOBBYING_EMPTY,
} from "../program-skeleton.mjs";

/** The live empty state (production c2ac0b90, site/src/app/program/[peBli]/
 *  page.tsx), copied here by hand ON PURPOSE: the gate pins its own copy, and
 *  the first test below checks the two agree, so neither can drift alone. */
const LIVE_SHARED_EMPTY =
  "This code is shared by more than one budget line. No lobbying matches are assigned to this specific account or organization.";
/** The ordinary empty state — what a page that does NOT share its code says. */
const ORDINARY_EMPTY =
  "No Senate LDA lobbying filing in the tracked data mentions this program element by code or alias.";

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

/** A member page's title block + WHO card + Lobbying Mentions section, the
 *  way the built page emits them (h1[data-program-name],
 *  span[data-program-account], the answer-who card, and
 *  section[data-section="lobbying"] with its [data-section-empty] line).
 *  `accountTitle` overrides what the appropriation line SAYS; `omitAccount`
 *  drops the element; `withheld` stamps data-who-withheld; `tier` is the WHO
 *  card's declared tier; `whoName` renders a [data-who-name]. The lobbying
 *  section renders `mentionRows` [data-filing-mention] rows when > 0,
 *  otherwise the empty state `lobbyEmpty` (default: the live shared-code
 *  sentence); `omitLobby` drops the section. */
function memberHtml(
  p,
  {
    accountTitle = p.account_title,
    omitAccount = false,
    withheld = false,
    tier = "none",
    whoName = false,
    mentionRows = 0,
    lobbyEmpty = LIVE_SHARED_EMPTY,
    omitLobby = false,
  } = {},
) {
  const account = omitAccount
    ? ""
    : `<span data-program-account="${p.account}">${accountTitle} · <code>${p.account}</code></span>`;
  const lobby = omitLobby
    ? ""
    : `<section id="program-lobbying" data-section="lobbying">` +
      (mentionRows > 0
        ? `<div data-sort-table="program-mentions">` +
          Array.from(
            { length: mentionRows },
            (_, k) => `<div data-filing-mention="" data-evidence-kind="pe_literal">row ${k}</div>`,
          ).join("") +
          `</div>`
        : `<div class="mb-8"><h2>Lobbying Mentions</h2>` +
          `<p data-section-empty="true" class="text-xs">${lobbyEmpty}</p></div>`) +
      `</section>`;
  return (
    `<html><body><h1 data-program-name="true">${p.title}</h1>` +
    `<div class="flex"><a href="/agency/${p.org}/">${p.org}</a>${account}</div>` +
    `<div data-testid="answer-who"><span data-who-tier="${tier}"` +
    `${withheld ? ' data-who-withheld="shared-code"' : ""}>x` +
    `${whoName ? '<span data-who-name="">ACME CORP</span>' : ""}</span></div>` +
    `<div data-section="figures"></div>${lobby}</body></html>`
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
 *  Lobbying (R-INT-9): by default NO member carries lobbying evidence — the
 *  shape the ruled exporter ships. The options below rebuild the shape the
 *  RETIRED #82 exporter shipped, so the tests can prove the leg refuses it:
 *  `mentionCodes` names the codes whose members each carry ONE lobbying row
 *  from the same filing (the pre-R-INT-9 export carried rows on 6 of 13
 *  codes); by default it is `pe_literal` and each sidecar declares the #82
 *  "code" basis. `mentionKind` switches the tier, `mentionTerm(p)` decides
 *  what each member's row matched, `declareMentions` controls whether the
 *  sidecar declares any basis, and `mentionDeclaration` overrides it.
 *  `lobbiedBy(p)` / `namedPrimes(p)` put a lobbied_by block / named primes
 *  in a member's summary. */
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
    lobbiedBy = () => false,
    namedPrimes = () => false,
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
        summary: {
          concentration_withheld: withheld(p),
          named_primes: namedPrimes(p)
            ? [{ name: "ACME CORP", family_key: "ACME CORP", fact_id: "f", public_id: "p" }]
            : [],
          lobbied_by: lobbiedBy(p)
            ? {
                families: [
                  { name: "ACME CORP", family_key: "ACME CORP", filings: 3, evidence_kind: "pe_literal", slug: null },
                ],
                shown: 1,
                more: 0,
                filings: 3,
              }
            : null,
        },
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
    //
    // Since R-INT-9 the J-book tier is refused on EVERY member (check 8(b):
    // named primes are withheld on a shared code), so this page now draws
    // two findings — check 7's, which is what this test pins, and 8(b)'s.
    const page = (p) =>
      p.slug === "TC-M0"
        ? memberHtml(p, { tier: "jbook" })
        : memberHtml(p, { omitAccount: ORG_SPLIT.has(p.pe_bli), withheld: p.pe_bli === "TC" });
    const { errors } = run(LIVE_SHAPE, { page, withheld: (p) => p.pe_bli === "TC" });
    expect(errors).toHaveLength(2);
    expect(errors[0]).toContain('/program/TC-M0/ sidecar says concentration_withheld=true');
    expect(errors[0]).toContain('declares tier "jbook"');
    expect(errors[1]).toContain('/program/TC-M0/ answers WHO GETS IT on the "jbook" tier');
  });

  it("FAILS when the withheld marker migrates onto a stronger tier", () => {
    // The other half of the tier clause: the payload IS withheld and the
    // marker IS rendered, but on a tier whose own sentence names companies
    // or dollars. Without the tier clause both halves of check 7 are
    // satisfied and the page passes while saying two contradictory things.
    // (R-INT-9 adds check 8(b)'s own finding: no member answers on the
    // lobbying tier at all.)
    const page = (p) =>
      p.slug === "TC-M0"
        ? memberHtml(p, { tier: "lobbying", withheld: true })
        : memberHtml(p, { omitAccount: ORG_SPLIT.has(p.pe_bli), withheld: p.pe_bli === "TC" });
    const { errors } = run(LIVE_SHAPE, { page, withheld: (p) => p.pe_bli === "TC" });
    expect(errors).toHaveLength(2);
    expect(errors[0]).toContain('declares tier "lobbying"');
    expect(errors[1]).toContain('/program/TC-M0/ answers WHO GETS IT on the "lobbying" tier');
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
});

// ═══════════════════════════════════════════════════════════════════════════
// check 8(b) — ruling R-INT-9 (2026-09-25): no lobbying evidence on a member
// ═══════════════════════════════════════════════════════════════════════════
//
// These were the #82 mention-axis tests (2026-09-18), which ALLOWED a
// declared pe_literal row on every member and a title-basis row on the member
// whose title carried its terms. R-INT-9 retired that rule: on '20'/'30'/'500'
// every pe_literal row matched a bill or public-law number, a date or part of
// a larger figure, and the merged build told readers of 7 member pages that
// companies "named this program in Senate lobbying filings" while this leg
// passed (verify 27/27 at 5c670cb6) because the exporter DECLARED the basis.
// Each old case is kept on its old fixture and rewritten to the ruled
// behaviour — a declaration excuses nothing — and the cases below it prove the
// new assertions can fail.

/** Findings about one member page. */
const about = (errors, slug) => errors.filter((e) => e.includes(`/program/${slug}/`));

describe("leg n — check 8(b): a shared-code member publishes no lobbying evidence (R-INT-9)", () => {
  it("pins the live empty-state sentence, verbatim", () => {
    expect(SHARED_CODE_LOBBYING_EMPTY).toBe(LIVE_SHARED_EMPTY);
  });

  it("passes on the corpus the R-INT-9 exporter ships and says what it saw", () => {
    const { errors, notes } = run(LIVE_SHAPE, { page: livePage });
    expect(errors).toEqual([]);
    expect(notes[0]).toContain("R-INT-9: no member publishes a lobbying mention");
    expect(notes[0]).toContain("27 of 27 member page(s) state the withholding verbatim");
  });

  it("FAILS a pe_literal mention on both members even though the sidecar declares {pe_literal: \"code\"}", () => {
    // Was: "allows a pe_literal mention on both members — the filing names
    // the CODE" (errors []). The live '20': 22 rows of "H.R. 20" on 20-DCSA
    // and 20-DTRA, each sidecar declaring {pe_literal: "code"}.
    const { errors } = run(LIVE_SHAPE, {
      page: livePage,
      mentionCodes: new Set(["TA", "TB", "TK", "TL", "TM"]),
    });
    const members = ["TA-M0", "TA-M1", "TB-M0", "TB-M1", "TK-M0", "TK-M1", "TL-M0", "TL-M1", "TM-M0", "TM-M1", "TM-M2"];
    for (const slug of members) {
      const mine = about(errors, slug);
      const row = mine.find((e) => e.includes("publishes 1 lobbying mention row(s)"));
      expect(row, slug).toBeDefined();
      expect(row).toContain('1 pe_literal (badged "PE/BLI code cited directly")');
      expect(row).toContain("whatever basis its sidecar declares");
      expect(mine.some((e) => e.includes('declares mentions_shared_code {"pe_literal":"code"}'))).toBe(true);
    }
    expect(errors).toHaveLength(2 * members.length);
  });

  it("FAILS an undeclared mention on both members too", () => {
    const { errors } = run(LIVE_SHAPE, {
      page: livePage,
      mentionCodes: new Set(["TA"]),
      declareMentions: false,
    });
    expect(errors).toHaveLength(2);
    expect(about(errors, "TA-M0")[0]).toContain("publishes 1 lobbying mention row(s) on shared code TA");
    expect(about(errors, "TA-M1")[0]).toContain("publishes 1 lobbying mention row(s) on shared code TA");
    expect(errors.some((e) => e.includes("mentions_shared_code"))).toBe(false);
  });

  // The live 0145 (fix round 1, 2026-09-18): a multi_token row matched
  // `General|Purpose`, the title of ONE member ("General Purpose Bombs"). #82
  // published it on that member and refused it on the other; R-INT-9 refuses
  // it on both — the mart row is keyed on the bare code either way.
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

  it("FAILS the 0145 shape on BOTH members — a title match no longer earns the row a page", () => {
    // Was: failed only TA-M0 and left TA-M1 ("the member whose title DOES
    // carry them keeps its row") uncomplained-about.
    const { errors } = runBuilt(shape0145());
    for (const slug of ["TA-M0", "TA-M1"]) {
      expect(
        about(errors, slug).some((e) => e.includes("publishes 1 lobbying mention row(s) on shared code TA")),
        slug,
      ).toBe(true);
    }
  });

  it("FAILS the 2292 shape — identical member titles make the row true of neither page", () => {
    // Was: "passes on the 2292 shape". The live 2292 carried 18 rows on each
    // member; production renders none.
    const built = shape0145();
    built.programs.find((p) => p.slug === "TA-M0").title = "General Purpose Bombs";
    const { errors } = runBuilt(built);
    expect(about(errors, "TA-M0").some((e) => e.includes("lobbying mention row(s)"))).toBe(true);
    expect(about(errors, "TA-M1").some((e) => e.includes("lobbying mention row(s)"))).toBe(true);
  });

  // ── the quoted badge is the one the PAGE shows, per tier ────────────────
  // Kept from #82: a finding quotes the badge the reader saw, read out of
  // src/lib/evidence.ts (the table the row itself calls), never a hand-copy.
  it("quotes multi_token's OWN badge on a multi_token row", () => {
    const { errors } = runBuilt(shape0145());
    const row = about(errors, "TA-M0").find((e) => e.includes("lobbying mention row(s)"));
    expect(row).toContain('1 multi_token (badged "matched 2+ title words")');
    expect(row).not.toContain("matched a known alias");
  });

  it("quotes ALIAS's badge on an alias row, not multi_token's", () => {
    const { errors } = runBuilt(
      shape0145({ mentionKind: "alias", mentionTerm: () => "Super Hornet" }),
    );
    const row = about(errors, "TA-M1").find((e) => e.includes("lobbying mention row(s)"));
    expect(row).toContain('1 alias (badged "matched a known alias")');
    expect(row).not.toContain("2+ title words");
  });

  it("reads the badge table out of src/lib/evidence.ts, and says so if it cannot", () => {
    const table = evidenceBadges();
    expect(table.multi_token.label).toBe("matched 2+ title words");
    expect(table.alias.label).toBe("matched a known alias");
    // #176 (fix round 2026-09-26): the badge names both code kinds and the
    // title the all-digit rule; the reader still extracts both arms.
    expect(table.pe_literal.label).toBe("PE/BLI code cited directly");
    expect(table.pe_literal.title).toMatch(/all-digit codes need a budget-line label/);
    for (const kind of ["multi_token", "alias", "pe_literal"]) {
      expect(table[kind].title.length).toBeGreaterThan(20);
    }
    // A module that no longer carries the table must fail loudly rather than
    // hand the leg a stale hand-copy.
    expect(() => evidenceBadges("/no/such/evidence.ts")).toThrow(/evidence/i);
  });

  it("FAILS any mentions_shared_code declaration — the retired exporter's signature — even with no rows", () => {
    // Was: "FAILS a wrong declaration" (multi_token declared "code"). Every
    // declaration is now the finding, right or wrong.
    const { programs, sidecars, html } = corpus(LIVE_SHAPE, { page: livePage });
    sidecars.get("TK-M0").mentions_shared_code = { pe_literal: "code" };
    const { errors } = runBuilt({ programs, sidecars, html });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("/program/TK-M0/ sidecar declares mentions_shared_code");
    expect(errors[0]).toContain("the retired #82 per-row basis");
  });

  it("FAILS a row whose tier the declaration does not name, once per member", () => {
    const { errors } = runBuilt(shape0145({ mentionDeclaration: { pe_literal: "code" } }));
    expect(errors.filter((e) => e.includes("publishes 1 lobbying mention row(s)"))).toHaveLength(2);
    expect(errors.filter((e) => e.includes("declares mentions_shared_code"))).toHaveLength(2);
  });

  it("FAILS a mention that only ONE member renders", () => {
    // Was: "never objects to a mention that only ONE member renders" — the
    // #82 title-basis outcome (0145-PANMC's 5 rows, 1350-PANMC's 2).
    const { programs, sidecars, html } = corpus(LIVE_SHAPE, {
      page: livePage,
      mentionCodes: new Set(["TA"]),
    });
    sidecars.get("TA-M1").mentions = [];
    delete sidecars.get("TA-M1").mentions_shared_code;
    delete sidecars.get("TA-M0").mentions_shared_code;
    const { errors } = runBuilt({ programs, sidecars, html });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("/program/TA-M0/ publishes 1 lobbying mention row(s)");
  });

  // ── the WHO answer: payload and page ────────────────────────────────────
  it("FAILS a lobbied_by block in a member's payload (the 30-OSD shape)", () => {
    const { errors } = run(LIVE_SHAPE, { page: livePage, lobbiedBy: (p) => p.slug === "TM-M0" });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("/program/TM-M0/ sidecar carries summary.lobbied_by (ACME CORP)");
    expect(errors[0]).toContain("R-INT-9 withholds the lobbying WHO answer");
  });

  it("FAILS a page that answers on the lobbying tier and names a company, even with a clean payload", () => {
    const page = (p) =>
      p.slug === "TK-M1" ? memberHtml(p, { omitAccount: true, tier: "lobbying", whoName: true }) : livePage(p);
    const { errors } = run(LIVE_SHAPE, { page });
    expect(errors).toHaveLength(2);
    expect(errors[0]).toContain('/program/TK-M1/ answers WHO GETS IT on the "lobbying" tier');
    expect(errors[1]).toContain("/program/TK-M1/ renders 1 [data-who-name]");
  });

  it("FAILS named primes in the payload and the J-book tier on the page", () => {
    const { errors: payload } = run(LIVE_SHAPE, { page: livePage, namedPrimes: (p) => p.slug === "TC-M0" });
    expect(payload).toHaveLength(1);
    expect(payload[0]).toContain("/program/TC-M0/ sidecar carries 1 summary.named_primes entry (ACME CORP)");
    const page = (p) => (p.slug === "TC-M0" ? memberHtml(p, { tier: "jbook" }) : livePage(p));
    const { errors: rendered } = run(LIVE_SHAPE, { page });
    expect(rendered).toHaveLength(1);
    expect(rendered[0]).toContain('/program/TC-M0/ answers WHO GETS IT on the "jbook" tier');
  });

  it("allows the award tier and the honest absence on a member", () => {
    const page = (p) => memberHtml(p, { omitAccount: ORG_SPLIT.has(p.pe_bli), tier: p.pe_bli === "TD" ? "award" : "none" });
    expect(run(LIVE_SHAPE, { page }).errors).toEqual([]);
  });

  // ── the positive assertion: the page SAYS it withholds ──────────────────
  it("FAILS rendered mention rows even when the payload is clean", () => {
    const page = (p) => (p.slug === "TL-M0" ? memberHtml(p, { omitAccount: true, mentionRows: 25 }) : livePage(p));
    const { errors } = run(LIVE_SHAPE, { page });
    expect(errors).toHaveLength(2);
    expect(errors[0]).toContain("/program/TL-M0/ renders 25 lobbying mention row(s) ([data-filing-mention])");
    expect(errors[1]).toContain('/program/TL-M0/ Lobbying Mentions reads "(no empty state)"');
  });

  it("FAILS a member that falls back to the ordinary empty state", () => {
    const page = (p) => (p.slug === "TB-M0" ? memberHtml(p, { lobbyEmpty: ORDINARY_EMPTY }) : livePage(p));
    const { errors } = run(LIVE_SHAPE, { page });
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain(`/program/TB-M0/ Lobbying Mentions reads "${ORDINARY_EMPTY}"`);
    expect(errors[0]).toContain(`verbatim: "${LIVE_SHARED_EMPTY}"`);
  });

  it("FAILS a member whose empty state is reworded, and one with no lobbying section", () => {
    const reworded = LIVE_SHARED_EMPTY.replace("specific account or organization", "program");
    const page = (p) =>
      p.slug === "TE-M0"
        ? memberHtml(p, { lobbyEmpty: reworded })
        : p.slug === "TE-M1"
          ? memberHtml(p, { omitLobby: true })
          : livePage(p);
    const { errors } = run(LIVE_SHAPE, { page });
    expect(errors).toHaveLength(2);
    expect(errors[0]).toContain("/program/TE-M0/ Lobbying Mentions reads");
    expect(errors[1]).toContain('/program/TE-M1/ renders no Lobbying Mentions section');
  });

  it("does not reach a page that shares no code — the ordinary page keeps its own evidence", () => {
    // TZ has one program: its mention, lobbying tier and ordinary empty state
    // are outside this leg (leg j holds its WHO card to the lobbying template).
    const shape = [...LIVE_SHAPE, ["TZ", [0]]];
    const { programs, sidecars, html } = corpus(shape, {
      page: (p) =>
        p.pe_bli === "TZ"
          ? memberHtml(p, { tier: "lobbying", whoName: true, mentionRows: 3 })
          : livePage(p),
      mentionCodes: new Set(["TZ"]),
      lobbiedBy: (p) => p.pe_bli === "TZ",
      namedPrimes: (p) => p.pe_bli === "TZ",
    });
    const { errors, notes } = runBuilt({ programs, sidecars, html });
    expect(errors).toEqual([]);
    expect(notes[0]).toContain("27 of 27 member page(s)");
  });

  // ── proof it can fail: the build R-INT-9 was ruled against ──────────────
  it("FAILS the corpus the pre-R-INT-9 exporter shipped (integration build 42eed1e4), on every page it got wrong", () => {
    // Transposed from the measured build: title-basis rows on one member of
    // 0145 (TA, 5) and 1350 (TB, 2) and on both members of 2292 (TD, 18
    // each); declared pe_literal rows on every member of 20 (TK, 22), 500
    // (TL, 3) and 30 (TM, 26 — the page caps the list at 25); lobbied_by and
    // the lobbying tier on all 7 of those org-split members. That build
    // passed this leg; the old check 8 read the declarations as licences.
    const rowsOf = { "TA-M1": 5, "TB-M1": 2, "TD-M0": 18, "TD-M1": 18 };
    for (const pe of ["TK", "TL", "TM"]) {
      const n = { TK: 22, TL: 3, TM: 26 }[pe];
      for (let i = 0; i < (pe === "TM" ? 3 : 2); i++) rowsOf[`${pe}-M${i}`] = n;
    }
    const orgSplitLobbied = (p) => ORG_SPLIT.has(p.pe_bli);
    const { programs, sidecars, html } = corpus(LIVE_SHAPE, {
      page: (p) =>
        rowsOf[p.slug]
          ? memberHtml(p, {
              omitAccount: ORG_SPLIT.has(p.pe_bli),
              tier: orgSplitLobbied(p) ? "lobbying" : "none",
              whoName: orgSplitLobbied(p),
              mentionRows: Math.min(rowsOf[p.slug], 25),
            })
          : livePage(p),
      lobbiedBy: orgSplitLobbied,
    });
    for (const [slug, n] of Object.entries(rowsOf)) {
      const d = sidecars.get(slug);
      const kind = ORG_SPLIT.has(slug.slice(0, 2)) ? "pe_literal" : "multi_token";
      d.mentions = Array.from({ length: n }, (_, k) => ({
        filing_uuid: `uuid-${slug}-${k}`, client_name: "ACME CORP", evidence_kind: kind, matched_term: "x",
      }));
      d.mentions_shared_code = { [kind]: kind === "pe_literal" ? "code" : "title" };
    }
    const { errors } = runBuilt({ programs, sidecars, html });
    const wrong = Object.keys(rowsOf).sort();
    expect(wrong).toHaveLength(11);
    const flagged = new Set(
      errors.map((e) => /\/program\/([A-Z]{2}-M\d)\//.exec(e)?.[1]).filter(Boolean),
    );
    expect([...flagged].sort()).toEqual(wrong);
    for (const slug of wrong) {
      const mine = about(errors, slug);
      expect(mine.some((e) => e.includes(`publishes ${rowsOf[slug]} lobbying mention row(s)`)), slug).toBe(true);
      expect(mine.some((e) => e.includes("renders") && e.includes("[data-filing-mention]")), slug).toBe(true);
      expect(mine.some((e) => e.includes("Lobbying Mentions reads")), slug).toBe(true);
      const lobbied = ORG_SPLIT.has(slug.slice(0, 2));
      expect(mine.some((e) => e.includes("summary.lobbied_by")), slug).toBe(lobbied);
      expect(mine.some((e) => e.includes('on the "lobbying" tier')), slug).toBe(lobbied);
    }
    expect(errors.filter((e) => e.includes('on the "lobbying" tier'))).toHaveLength(7);
    // …and the corpus R-INT-9 ships in its place passes (first test above).
  });
});
