/**
 * Unit tests for gate 8 leg (l)'s destination probe (ROADMAP #80; fix round
 * 1, 2026-09-11).
 *
 * Leg (l) reconciles a feed card's single-year HHI band against what the
 * destination program page actually renders. Since the fix that page renders
 * exactly one of two things: a headline band over HIGH-CONFIDENCE links, or
 * an explicit withheld marker saying no index is published. An all-links
 * band is no longer a legitimate destination state at all — if one appears,
 * a template regression put back the basis the site stopped publishing — and
 * two badges, or a badge that does not say which basis it is, make the
 * reconciliation meaningless. These tests pin every one of those, and pass
 * on the contract.
 *
 * Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parse } from "node-html-parser";
import {
  destinationHhiBadge,
  hhiDestinationCensusVerdict,
  MIN_RECONCILABLE_HHI_DESTINATIONS,
} from "../feed.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const page = (inner) => parse(`<html><body><main>${inner}</main></body></html>`, { comment: false });

describe("destinationHhiBadge", () => {
  it("returns the band for one high-basis badge", () => {
    const r = destinationHhiBadge(page('<div data-hhi-band="Competitive" data-hhi-basis="high">Competitive</div>'));
    expect(r).toEqual({ band: "Competitive", basis: "high", withheld: null, error: null });
  });

  it("accepts a withheld destination as a legitimate state", () => {
    const r = destinationHhiBadge(page(
      '<p data-concentration-withheld="below-floor">No concentration index is published for this line.</p>',
    ));
    expect(r).toEqual({ band: null, basis: null, withheld: "below-floor", error: null });
  });

  it("returns band null (no error) when the page has no concentration block", () => {
    expect(destinationHhiBadge(page("<p>no card</p>"))).toEqual({
      band: null, basis: null, withheld: null, error: null,
    });
  });

  it("fails on an all-links band — the basis the site stopped publishing", () => {
    const r = destinationHhiBadge(page('<div data-hhi-band="Highly Concentrated" data-hhi-basis="all">x</div>'));
    expect(r.band).toBeNull();
    expect(r.error).toMatch(/expected "high"/);
  });

  it("fails when two badges are rendered", () => {
    const r = destinationHhiBadge(page(
      '<div data-hhi-band="Competitive" data-hhi-basis="high"></div><div data-hhi-band="Moderately Concentrated" data-hhi-basis="high"></div>',
    ));
    expect(r.band).toBeNull();
    expect(r.error).toMatch(/renders 2 \[data-hhi-band\]/);
  });

  it("fails when the badge does not declare its basis", () => {
    const r = destinationHhiBadge(page('<div data-hhi-band="Competitive">Competitive</div>'));
    expect(r.band).toBeNull();
    expect(r.error).toMatch(/data-hhi-basis/);
  });

  it("fails on an unknown basis token", () => {
    const r = destinationHhiBadge(page('<div data-hhi-band="Competitive" data-hhi-basis="medium"></div>'));
    expect(r.error).toMatch(/expected "high"/);
  });

  it("fails when a page both publishes a band and claims to withhold", () => {
    const r = destinationHhiBadge(page(
      '<div data-hhi-band="Competitive" data-hhi-basis="high"></div>' +
        '<p data-concentration-withheld="below-floor">withheld</p>',
    ));
    expect(r.band).toBeNull();
    expect(r.error).toMatch(/both a \[data-hhi-band\] and/);
  });
});

/**
 * ROADMAP #80 fix round 2 (2026-09-11), finding 5 — ruling R7.
 *
 * Leg (l) counted a withheld destination as "checked" BEFORE it resolved
 * the destination, so a run in which every destination withheld still had
 * checked = 60+, skipped the `checked === 0` vacuity guard, and printed a
 * green "0 silent contradictions" note having reconciled nothing. With 407
 * of 444 mart rows publishing no index, the reconcilable population is
 * small enough that this is a live risk, not a hypothetical.
 *
 * The census verdict below is the whole decision, extracted so it can be
 * driven without a built site: `resolved` (destinations that actually
 * rendered a high band) is what the vacuity guard and the dated
 * do-not-lower floor both read.
 */
describe("hhiDestinationCensusVerdict", () => {
  const census = (over = {}) => ({
    cards: 75,
    resolved: MIN_RECONCILABLE_HHI_DESTINATIONS,
    agree: 10,
    disclosedDivergence: MIN_RECONCILABLE_HHI_DESTINATIONS - 10,
    withheldDestination: 75 - MIN_RECONCILABLE_HHI_DESTINATIONS,
    ...over,
  });

  it("passes at the floor and reports the whole census", () => {
    const v = hhiDestinationCensusVerdict(census());
    expect(v.error).toBeNull();
    expect(v.note).toContain(`${MIN_RECONCILABLE_HHI_DESTINATIONS}`);
    expect(v.note).toContain("publishes no pooled index");
    expect(v.note).toContain("0 silent contradictions");
  });

  it("fails one destination below the floor — proof the floor is load-bearing", () => {
    const v = hhiDestinationCensusVerdict(
      census({
        resolved: MIN_RECONCILABLE_HHI_DESTINATIONS - 1,
        disclosedDivergence: MIN_RECONCILABLE_HHI_DESTINATIONS - 11,
        withheldDestination: 75 - (MIN_RECONCILABLE_HHI_DESTINATIONS - 1),
      }),
    );
    expect(v.note).toBeNull();
    expect(v.error).toMatch(/feed leg l/);
    expect(v.error).toMatch(/floor/);
    expect(v.error).toMatch(/2026-09-11/);
  });

  it("fails when every destination withholds — the vacuity guard now sees it", () => {
    const v = hhiDestinationCensusVerdict(
      census({ resolved: 0, agree: 0, disclosedDivergence: 0, withheldDestination: 75 }),
    );
    expect(v.note).toBeNull();
    expect(v.error).toMatch(/vacuous/);
    expect(v.error).toMatch(/withheld/);
  });

  // Every probe above derives its fixtures FROM the constant, so they stay
  // green at any value — lowering the floor to 5 to clear a red build would
  // have cost nothing (#80 fix round 3, 2026-09-11, finding 3). This one
  // fails on a LOWER value, and pins the dated note that says why.
  it("the floor is a positive, dated, do-not-lower number", () => {
    expect(Number.isInteger(MIN_RECONCILABLE_HHI_DESTINATIONS)).toBe(true);
    expect(MIN_RECONCILABLE_HHI_DESTINATIONS).toBeGreaterThan(0);
    // MEASURED 2026-09-11: 21 of the top-75 concentration_shift CARDS reach a
    // pe_bli that clears the high-only floor (chain C run 4, 2026-09-25: 45).
    // Never lower it; raising it is the dated decision backlog #144 owns.
    expect(MIN_RECONCILABLE_HHI_DESTINATIONS).toBeGreaterThanOrEqual(21);

    // The "never lower" rule lives in feed.mjs's doc comment, so read the
    // source the way the strip test reads page.tsx: a silent edit that keeps
    // the number and deletes the rule fails here too.
    const src = fs.readFileSync(path.resolve(__dirname, "..", "feed.mjs"), "utf8");
    const decl = src.indexOf("export const MIN_RECONCILABLE_HHI_DESTINATIONS");
    expect(decl).toBeGreaterThan(-1);
    expect(src.slice(decl)).toMatch(
      new RegExp(`^export const MIN_RECONCILABLE_HHI_DESTINATIONS = ${MIN_RECONCILABLE_HHI_DESTINATIONS};`),
    );
    const note = src.slice(src.lastIndexOf("/**", decl), decl);
    expect(note).toMatch(/NEVER LOWER/i);
    expect(note).toMatch(/\b20\d\d-\d\d-\d\d\b/);
  });
});
