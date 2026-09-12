/**
 * Unit tests for gate 21 leg (n) — a shared BLI code's members own their own
 * awards (ROADMAP #70), name their own appropriation in the title block
 * (ROADMAP #82), and the leg is not vacuous.
 *
 * The floors are the reason this file exists. The leg's per-page checks are
 * all perfectly satisfied by a corpus in which every member page shows ZERO
 * awards (split_key drift), or renders NO appropriation line (a header
 * regression) — "nothing to object to" and "the regression" are the same
 * observation without a floor. The leg's first standalone run printed
 * "0 member page(s) carry 0 award row(s)" and PASSED. These tests pin that
 * it cannot do so again, on either axis.
 *
 * Synthetic pe_bli codes are used throughout; the leg reads page HTML through
 * the injected `pageHtml` so no build is needed and the stub check finds
 * nothing on disk.
 *
 * Run via `npm test` (vitest).
 */

import { describe, it, expect } from "vitest";
import { runSplitKeyAwardsLeg } from "../program-skeleton.mjs";

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
 *  `page(p, siblings)` returns the HTML for one member (default: correct). */
function corpus(shape, { piidPerMember = false, page = (p) => memberHtml(p), withheld = () => false } = {}) {
  const programs = [];
  const sidecars = new Map();
  const html = new Map();
  let piid = 0;
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
    members.forEach((p, i) => {
      const awards = [];
      for (let k = 0; k < counts[i]; k++) {
        awards.push({
          award_piid: piidPerMember ? `PIID-${pe}-${k}` : `PIID-${++piid}`,
          recipient_name: "ACME",
          confidence: "medium",
        });
      }
      programs.push(p);
      sidecars.set(p.slug, { awards, summary: { concentration_withheld: withheld(p) } });
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

  it("FAILS just below the shared-code floor and passes at it", () => {
    const nine = LIVE_SHAPE.slice(0, 9);
    expect(run(nine, { page: livePage }).errors[0]).toContain("carries 9 shared BLI code(s) (floor 10");
    // Ten account-split codes = 20 pages: clears both the universe floor
    // and the appropriation-line floor; the award floors are met by the
    // first ten too (7 pages / 86 rows).
    const ten = LIVE_SHAPE.slice(0, 10);
    expect(run(ten, { page: livePage }).errors).toEqual([]);
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
