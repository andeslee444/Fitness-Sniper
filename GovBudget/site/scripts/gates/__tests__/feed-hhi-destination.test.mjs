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
import { parse } from "node-html-parser";
import { destinationHhiBadge } from "../feed.mjs";

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
