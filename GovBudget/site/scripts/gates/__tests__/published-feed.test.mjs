import assert from "node:assert/strict";
import { it as test } from "vitest";
import { inspectPublishedFeed, inspectConcentrationDestination, MIN_PUBLISHED_CONCENTRATION_DESTINATIONS } from "../coverage.mjs";
import { withheldFloorClause } from "../concentration-floor.mjs";

// Integration ruling R-INT-2 (2026-09-25): a program page publishes the
// HIGH-confidence concentration figure or withholds it below the floor; the
// all-link figure is never printed. The codex/f15-family-browser cases below
// asserted the all-link receipts on the destination; each is kept, rewritten
// to the ruled receipts (hhi_high_fact_id / program_dollars_high_fact_id),
// and the new cases pin what the retargeted leg adds.

const HHI = "aaaaaaaaaaaaaaaa";
const DOLLARS = "bbbbbbbbbbbbbbbb";
const ALL_HHI = "eeeeeeeeeeeeeeee";
const ALL_DOLLARS = "ffffffffffffffff";
const CARD_HHI = "1111111111111111";
const CARD_DOLLARS = "2222222222222222";
const floor = { awards: 3, families: 2 };

const program = {
  slug: "0592",
  hhi: {
    hhi_all: 10000, hhi_all_fact_id: ALL_HHI, program_dollars_all: 5e9, program_dollars_all_fact_id: ALL_DOLLARS,
    hhi_high: 9048.39, hhi_high_fact_id: HHI, program_dollars_high: 588917585.54, program_dollars_high_fact_id: DOLLARS,
    top_family_high: "BOEING",
  },
};
const withheldProgram = {
  slug: "0593",
  hhi: { ...program.hhi, hhi_high: null, hhi_high_fact_id: null, top_family_high: null },
};
const sharedMember = { slug: "3010-SCN", hhi: null };

const citations = {
  [HHI]: { kind: "derived", units: "Herfindahl-Hirschman Index", recorded_value: "9048.390", formula: "… across fct_budget_to_awards high-confidence links only and obligation > 0 …" },
  [DOLLARS]: { kind: "derived", units: "USD", recorded_value: "588917585.540", formula: "… via fct_budget_to_awards high-confidence links only, across all linked award transactions …" },
  [CARD_HHI]: { kind: "derived", units: "Herfindahl-Hirschman Index", recorded_value: "10000.000", formula: "sum(share_pct * share_pct) over (pe_bli, fiscal_year) … (feed HHI; positive-only shares)" },
  [CARD_DOLLARS]: { kind: "derived", units: "USD", recorded_value: "25351139885.200", formula: "sum(obligations) for high-confidence awards in feed concentration window" },
};
const loadCitation = (id) => citations[id] ?? null;

const card = (url) => ({
  event_type: "concentration_shift", program_url: url, figure_value: 10000, figure_fact_id: CARD_HHI,
  magnitude: { kind: "single", to: { fact_id: CARD_DOLLARS, value: 25351139885.2 } },
});
const concentrated = card("/program/0592/");
const withheldCard = card("/program/0593/");
const ambiguous = card("/program/0145/");
const toShared = card("/program/3010-SCN/");
const other = { event_type: "yoy_swing", program_url: "/program/OTHER/", figure_value: 1 };

const html =
  '<section aria-labelledby="concentration-heading"><div data-concentration-basis="high">' +
  `<span data-amount="true" data-fact-id="${HHI}" data-dataset="fct_program_concentration" data-measure="hhi-high">9048</span>` +
  '<div data-hhi-band="Highly Concentrated" data-hhi-basis="high">Highly Concentrated</div>' +
  `<span data-amount="true" data-fact-id="${DOLLARS}" data-dataset="fct_program_concentration" data-measure="obligations-high">$588.9M</span>` +
  "</div></section>";
const withheldHtml =
  '<section aria-labelledby="concentration-heading"><p data-concentration-withheld="below-floor">' +
  "No concentration index is published for this line. This line's high-confidence links do not clear the floor " +
  `for a published concentration index — ${withheldFloorClause(floor)}.</p></section>`;
const pages = { "0592": html, "0593": withheldHtml, "3010-SCN": "<main>no concentration section</main>" };

const sourceFeed = { cards: [concentrated, withheldCard, ambiguous, toShared, other], total: 5 };
function inspect(cards = [concentrated, withheldCard, other], page = null, extra = {}) {
  return inspectPublishedFeed({
    sourceFeed,
    publishedFeed: { cards, total: cards.length },
    programs: [program, withheldProgram, sharedMember],
    loadProgramHtml: (slug) => (slug === "0592" && page !== null ? page : pages[slug] ?? null),
    loadCitation,
    floor,
    minPublishedDestinations: 1,
    ...extra,
  });
}
const destination = (overrides = {}) =>
  inspectConcentrationDestination({ program, html, loadCitation, floor, ...overrides });

test("counts the shipped feed while independently excluding ambiguous destinations", () => {
  const result = inspect();
  assert.deepEqual(result.errors, []);
  assert.equal(result.count, 3);
  assert.equal(result.census.published.cards, 1);
  assert.equal(result.census.belowFloor.cards, 1);
});

test("rejects a published ambiguous code even when its concentration number looks valid", () => {
  assert.ok(inspect([concentrated, withheldCard, ambiguous, other]).errors.some((e) => e.includes("no canonical destination")));
});

test("a page that withholds its block (shared code, #70/#82) may carry no feed card", () => {
  const errors = inspect([concentrated, withheldCard, toShared, other]).errors;
  assert.ok(errors.some((e) => e.includes("/program/3010-SCN/") && e.includes("a page that withholds has no feed card")));
});

test("requires the destination's own two high-confidence receipt IDs and the rendered band", () => {
  for (const page of [
    "",
    html.replace('data-hhi-band="Highly Concentrated"', "data-other"),
    html.replace(`data-fact-id="${HHI}"`, 'data-fact-id="cccccccccccccccc"'),
    html.replace(`data-fact-id="${DOLLARS}"`, 'data-fact-id="dddddddddddddddd"'),
  ]) {
    assert.ok(inspect(undefined, page).errors.some((e) => e.includes("no canonical destination")), page);
  }
});

test("R-INT-2: a destination displaying the all-link receipts is not canonical", () => {
  const allLink = html.replace(HHI, ALL_HHI).replace(DOLLARS, ALL_DOLLARS);
  assert.ok(destination({ html: allLink }).problems.some((p) => p.includes("all-link receipt")));
  const extra = html.replace("</div></section>", `<span data-fact-id="${ALL_HHI}"></span></div></section>`);
  assert.ok(destination({ html: extra }).problems.some((p) => p.includes(ALL_HHI)));
  assert.ok(destination({ html: html.replace('data-hhi-basis="high"', 'data-hhi-basis="all"') }).problems.length);
});

test("the published figure is the payload's: band, basis, stamps, display and one band only", () => {
  assert.deepEqual(destination().problems, []);
  assert.equal(destination().state, "published");
  assert.ok(destination({ html: html.replace('data-hhi-band="Highly Concentrated"', 'data-hhi-band="Competitive"') }).problems.length);
  assert.ok(destination({ html: html.replace('data-hhi-basis="high"', "") }).problems.length);
  assert.ok(destination({ html: html.replace('data-measure="hhi-high"', 'data-measure="hhi"') }).problems.length);
  assert.ok(destination({ html: html.replace('data-measure="obligations-high"', 'data-measure="obligations"') }).problems.length);
  assert.ok(destination({ html: html.replace(">9048<", ">5984<") }).problems.length);
  assert.ok(destination({ html: html.replace("</div></section>", '<div data-hhi-band="Highly Concentrated" data-hhi-basis="high"></div></div></section>') }).problems.length);
  assert.ok(destination({ html: html + html }).problems.some((p) => p.includes("sections")));
  assert.ok(destination({ html: html.replace("</div></section>", '<p data-concentration-withheld="below-floor"></p></div></section>') }).problems.length);
});

test("the published figure's receipts resolve to the payload's values, scoped high-confidence", () => {
  const withCitations = (patch) => destination({ loadCitation: (id) => (patch[id] !== undefined ? patch[id] : citations[id] ?? null) });
  assert.ok(withCitations({ [HHI]: null }).problems.some((p) => p.includes(HHI)));
  assert.ok(withCitations({ [HHI]: { ...citations[HHI], recorded_value: "5983.772" } }).problems.length);
  assert.ok(withCitations({ [DOLLARS]: { ...citations[DOLLARS], units: "Herfindahl-Hirschman Index" } }).problems.length);
  assert.ok(withCitations({ [DOLLARS]: { ...citations[DOLLARS], formula: "… high- and medium-confidence links …" } }).problems.some((p) => p.includes("scoped")));
  assert.ok(withCitations({ [HHI]: { ...citations[HHI], kind: "workbook" } }).problems.length);
});

test("a below-floor destination is canonical only when it says so, with the true floor, and prints nothing", () => {
  const ok = destination({ program: withheldProgram, html: withheldHtml });
  assert.deepEqual(ok, { state: "below-floor", problems: [] });
  // The SWC fold that shipped on build 42eed1e4.
  const mangled = withheldHtml.replace("at least 3 awards across 2 contractor families", "at least 32 contractor families");
  assert.ok(destination({ program: withheldProgram, html: mangled }).problems.some((p) => p.includes("misstates the floor")));
  assert.ok(destination({ program: withheldProgram, html: withheldHtml.replace("below-floor", "shared-code") }).problems.length);
  assert.ok(destination({ program: withheldProgram, html: withheldHtml.replace("</p>", `</p><span data-amount="true" data-fact-id="${ALL_HHI}">10000</span>`) }).problems.length);
  assert.ok(destination({ program: withheldProgram, html: withheldHtml.replace("</p>", '</p><div data-hhi-band="Competitive" data-hhi-basis="high"></div>') }).problems.length);
  // The payload and the page must agree on the state, both ways.
  assert.ok(destination({ program: withheldProgram, html }).problems.length);
  assert.ok(destination({ html: withheldHtml }).problems.length);
});

test("each card's own figure and matched dollars resolve to its receipts", () => {
  const bent = { ...concentrated, figure_value: 9000 };
  assert.ok(inspect([bent, withheldCard, other]).errors.some((e) => e.includes("does not match its receipt")));
  const noIds = { ...concentrated, figure_fact_id: null };
  assert.ok(inspect([noIds, withheldCard, other]).errors.some((e) => e.includes("receipt ids")));
  const mediumDollars = inspectPublishedFeed({
    sourceFeed, publishedFeed: { cards: [concentrated], total: 1 }, programs: [program], floor, minPublishedDestinations: 1,
    loadProgramHtml: () => html,
    loadCitation: (id) => (id === CARD_DOLLARS ? { ...citations[CARD_DOLLARS], formula: "sum(obligations) for high- and medium-confidence awards" } : loadCitation(id)),
  });
  assert.ok(mediumDollars.errors.some((e) => e.includes("not scoped to high-confidence")));
});

test("cannot silently remove supported cards or unrelated event types", () => {
  assert.ok(inspect([other]).errors.length);
  assert.ok(inspect([concentrated, withheldCard]).errors.length);
  assert.ok(inspect([concentrated, other]).errors.some((e) => e.includes("differ")));
});

test("rejects changed amounts and altered card order", () => {
  assert.ok(inspect([{ ...concentrated, figure_value: 1 }, withheldCard, other]).errors.length);
  assert.ok(inspect([{ ...concentrated, headline: "altered" }, withheldCard, other]).errors.some((e) => e.includes("differ")));
  assert.ok(inspect([other, withheldCard, concentrated]).errors.length);
});

test("fails closed when shipped cards are absent or its total is false", () => {
  assert.ok(inspectPublishedFeed({ sourceFeed, publishedFeed: {}, programs: [program], loadProgramHtml: () => html, loadCitation, floor }).errors.length);
  const falseTotal = inspectPublishedFeed({
    sourceFeed, publishedFeed: { cards: [concentrated, withheldCard, other], total: 4 },
    programs: [program, withheldProgram, sharedMember], loadProgramHtml: (slug) => pages[slug] ?? null,
    loadCitation, floor, minPublishedDestinations: 1,
  });
  assert.ok(falseTotal.errors.some((e) => e.includes("total")));
});

test("the floor on publishing destinations: a corpus where every destination withholds fails", () => {
  assert.ok(MIN_PUBLISHED_CONCENTRATION_DESTINATIONS >= 48);
  const allWithheld = inspectPublishedFeed({
    sourceFeed: { cards: [withheldCard, other], total: 2 }, publishedFeed: { cards: [withheldCard, other], total: 2 },
    programs: [withheldProgram], loadProgramHtml: (slug) => pages[slug] ?? null, loadCitation, floor,
  });
  assert.ok(allWithheld.errors.some((e) => e.includes("the leg would be checking no figure at all")));
  // The production default applies when a caller passes no floor.
  assert.ok(inspect().errors.length === 0);
  assert.ok(inspect(undefined, null, { minPublishedDestinations: undefined }).errors.some((e) => e.includes(`floor ${MIN_PUBLISHED_CONCENTRATION_DESTINATIONS}`)));
});
