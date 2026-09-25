import assert from "node:assert/strict";
import { it as test } from "vitest";
import { inspectPublishedFeed } from "../coverage.mjs";

const program = { slug: "0592", hhi: { hhi_all_fact_id: "aaaaaaaaaaaaaaaa", program_dollars_all_fact_id: "bbbbbbbbbbbbbbbb" } };
const concentrated = { event_type: "concentration_shift", program_url: "/program/0592/", figure_value: 10000 };
const ambiguous = { ...concentrated, program_url: "/program/0145/" };
const other = { event_type: "yoy_swing", program_url: "/program/OTHER/", figure_value: 1 };
const html = '<section aria-labelledby="concentration-heading"><span data-hhi-band="Highly Concentrated"></span><button data-fact-id="aaaaaaaaaaaaaaaa"></button><button data-fact-id="bbbbbbbbbbbbbbbb"></button></section>';
const sourceFeed = { cards: [concentrated, ambiguous, other], total: 3 };
function inspect(cards = [concentrated, other], page = html) {
  return inspectPublishedFeed({ sourceFeed, publishedFeed: { cards, total: cards.length }, programs: [program], loadProgramHtml: () => page });
}

test("counts the shipped feed while independently excluding ambiguous destinations", () => {
  assert.deepEqual(inspect(), { count: 2, errors: [] });
});

test("rejects a published ambiguous code even when its concentration number looks valid", () => {
  assert.ok(inspect([concentrated, ambiguous, other]).errors.some(error => error.includes("no canonical destination")));
});

test("requires the destination's own two receipt IDs and the rendered concentration band", () => {
  for (const page of [null, html.replace("data-hhi-band", "data-other"), html.replace("aaaaaaaaaaaaaaaa", "cccccccccccccccc"), html.replace("bbbbbbbbbbbbbbbb", "dddddddddddddddd")]) {
    assert.ok(inspect(undefined, page).errors.some(error => error.includes("no canonical destination")));
  }
});

test("cannot silently remove supported cards or unrelated event types", () => {
  assert.ok(inspect([other]).errors.length);
  assert.ok(inspect([concentrated]).errors.length);
});

test("rejects changed amounts and altered card order", () => {
  assert.ok(inspect([{ ...concentrated, figure_value: 1 }, other]).errors.length);
  assert.ok(inspect([other, concentrated]).errors.length);
});

test("fails closed when shipped cards are absent or its total is false", () => {
  assert.ok(inspectPublishedFeed({ sourceFeed, publishedFeed: {}, programs: [program], loadProgramHtml: () => html }).errors.length);
  assert.ok(inspectPublishedFeed({ sourceFeed, publishedFeed: { cards: [concentrated, other], total: 3 }, programs: [program], loadProgramHtml: () => html }).errors.some(error => error.includes("total")));
});
