/**
 * Unit tests for gate 8 leg (l)'s destination probe (ROADMAP #80).
 *
 * The card now publishes two bases; leg (l) reconciles a feed card's
 * single-year HHI band against the ONE band the destination page
 * headlines. Two [data-hhi-band] badges (a template that stamped the
 * second line too) or a badge that does not say which basis it is would
 * make the reconciliation meaningless — these tests pin that the probe
 * fails loudly on both, and passes on the contract.
 *
 * Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import { parse } from "node-html-parser";
import { destinationHhiBadge } from "../feed.mjs";

const page = (inner) => parse(`<html><body><main>${inner}</main></body></html>`, { comment: false });

describe("destinationHhiBadge", () => {
  it("returns the band and basis for one stamped badge", () => {
    const r = destinationHhiBadge(page('<div data-hhi-band="Competitive" data-hhi-basis="high">Competitive</div>'));
    expect(r).toEqual({ band: "Competitive", basis: "high", error: null });
  });
  it("accepts the all-tier basis", () => {
    const r = destinationHhiBadge(page('<div data-hhi-band="Highly Concentrated" data-hhi-basis="all">x</div>'));
    expect(r.basis).toBe("all");
    expect(r.error).toBeNull();
  });
  it("returns band null (no error) when the page has no concentration block", () => {
    expect(destinationHhiBadge(page("<p>no card</p>"))).toEqual({ band: null, basis: null, error: null });
  });
  it("fails when two badges are rendered", () => {
    const r = destinationHhiBadge(page(
      '<div data-hhi-band="Competitive" data-hhi-basis="high"></div><div data-hhi-band="Moderately Concentrated" data-hhi-basis="all"></div>',
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
    expect(r.error).toMatch(/expected "high" or "all"/);
  });
});
