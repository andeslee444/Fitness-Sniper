/**
 * Gate 24 leg (s) — the era-map table on /downloads/ (families piece 1,
 * Task 19). The page must render exactly json/era_map_summary.json, directly
 * after the p1_era_line_map download card, and the summary must agree with
 * the shipped p1_era_line_map (recounted from the parquet) and with the
 * receipts audit. Every input is injected, so nothing here needs a build or
 * the lake. src/__tests__/era-map-table.test.tsx binds the real components to
 * the same leg.
 */
import { describe, it, expect } from "vitest";
import { runEraMapLeg } from "../datatruth.mjs";

const DECISIONS = ["same_program", "history_only", "exclude_placeholder", "exclude_route_unsafe", "exclude_reused_code"];
const EDITIONS = [2017, 2018, 2019, 2020, 2021, 2022, 2023];

function edition(ed) {
  const chains = [2, 1, 1, 0, 0];
  const by_decision = Object.fromEntries(DECISIONS.map((d, i) => [d, { chains: chains[i], lines: chains[i], actuals_thousands: 0 }]));
  return { edition: ed, fy_actuals: ed - 2, lines: 4, by_decision, receipts: { facts: 1234, complete: 1200 } };
}
const summary = () => ({ schema_version: 1, editions: EDITIONS.map(edition), by_ruling: [], totals: {} });
const recountOf = (s) => ({
  present: true,
  editions: Object.fromEntries(s.editions.map((e) => [String(e.edition), {
    lines: e.lines,
    by_decision: Object.fromEntries(Object.entries(e.by_decision).filter(([, t]) => t.lines > 0).map(([d, t]) => [d, { chains: t.chains, lines: t.lines }])),
  }])),
});
const auditOf = (s) => ({ books: s.editions.map((e) => ({ edition: e.edition, exhibit: "P-1", facts: e.receipts.facts, complete: e.receipts.complete })) });

/** The markup DownloadCards renders, by hand: the card grid with the era
 *  table's section directly after the p1_era_line_map card (with `misplaced`,
 *  after the grid instead). */
function htmlOf(s, { drop, misplaced } = {}) {
  const rows = s.editions.filter((e) => e.edition !== drop).map((e) =>
    `<tr data-era-edition="${e.edition}"><th scope="row">PB${e.edition}</th>` +
    [["lines", "4"], ["same_program", "2 codes"], ["history_only", "1 code"], ["excluded", "1 code"], ["receipts", "1,200 of 1,234"]]
      .map(([k, v]) => `<td data-era-cell="${k}"><span class="t-label">x</span><span data-era-value>${v}</span></td>`).join("") +
    "</tr>").join("");
  const table = `<section id="era-map" class="sm:col-span-2"><table data-era-map><tbody>${rows}</tbody></table></section>`;
  const card = (name) => `<div data-dataset-card="${name}"><span>${name}</span></div>`;
  return `<main><div class="grid gap-4 sm:grid-cols-2">${card("budget_lines")}${card("p1_era_line_map")}` +
    `${misplaced ? "" : table}${card("citations")}</div>${misplaced ? table : ""}</main>`;
}

function run(over = {}) {
  const s = over.summary ?? summary();
  const errors = [];
  const notes = [];
  runEraMapLeg(errors, notes, {
    recount: over.recount ?? recountOf(s),
    summary: s,
    audit: over.audit ?? auditOf(s),
    html: "html" in over ? over.html : htmlOf(s),
  });
  return { errors, notes };
}

describe("gate 24 leg (s)", () => {
  it("passes when page, summary, map and audit agree", () => {
    const { errors, notes } = run();
    expect(errors).toEqual([]);
    expect(notes).toHaveLength(1);
  });

  it("fails when the map parquet is not shipped", () => {
    expect(run({ recount: { present: false } }).errors[0]).toMatch(/p1_era_line_map\.parquet is not shipped/);
  });

  it("fails when the summary is missing", () => {
    const errors = [];
    runEraMapLeg(errors, [], { recount: recountOf(summary()), summary: null, audit: auditOf(summary()), html: htmlOf(summary()) });
    expect(errors[0]).toMatch(/era_map_summary\.json is missing/);
  });

  it("fails when the summary does not cover exactly PB2017–PB2023", () => {
    const s = summary();
    s.editions.pop();
    expect(run({ summary: s, html: htmlOf(s) }).errors[0]).toMatch(/covers editions \[2017,2018,2019,2020,2021,2022\]/);
  });

  it("fails when the summary disagrees with the shipped map", () => {
    const s = summary();
    const recount = recountOf(s);
    recount.editions["2019"].by_decision.history_only.chains = 2;
    expect(run({ summary: s, recount }).errors).toEqual([
      "leg s: PB2019 history_only summary says 1 chains / 1 lines, the shipped map holds 2 / 1",
    ]);
  });

  it("fails when receipts disagree with the audit", () => {
    const s = summary();
    const audit = auditOf(s);
    audit.books[3].complete = 1199;
    expect(run({ summary: s, audit }).errors).toEqual([
      "leg s: PB2020 receipts say 1200 of 1234, the receipts audit has 1199 of 1234",
    ]);
  });

  it("fails when /downloads/ is not built", () => {
    expect(run({ html: null }).errors).toEqual(["leg s: /downloads/ not built — run npm run build"]);
  });

  it("fails when the page drops an edition's row", () => {
    const s = summary();
    expect(run({ summary: s, html: htmlOf(s, { drop: 2022 }) }).errors[0]).toMatch(/renders rows for \[2017,2018,2019,2020,2021,2023\]/);
  });

  it("fails when a rendered cell differs from the summary", () => {
    const s = summary();
    s.editions[6].by_decision.same_program = { chains: 3, lines: 3, actuals_thousands: 0 };
    s.editions[6].lines = 5;
    const errors = run({ summary: s, html: htmlOf(s) }).errors;
    expect(errors).toContain('leg s (/downloads/): PB2023 same_program renders "2 codes", era_map_summary.json says "3 codes"');
    expect(errors).toContain('leg s (/downloads/): PB2023 lines renders "4", era_map_summary.json says "5"');
  });

  it("fails when the table is not directly under the p1_era_line_map card", () => {
    const s = summary();
    expect(run({ summary: s, html: htmlOf(s, { misplaced: true }) }).errors).toEqual([
      "leg s (/downloads/): the era table is not the element directly after the p1_era_line_map card",
    ]);
  });
});
