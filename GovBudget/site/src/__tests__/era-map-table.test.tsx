/**
 * The /downloads/ era-map table (families piece 1, spec 2026-10-02 §6.4,
 * Task 19). It renders counts from json/era_map_summary.json: lines, chains
 * ("codes") per decision, and receipt completeness, never a dollar figure (a
 * rendered $ needs a Cite state these sums do not have). DownloadCards renders
 * it inside the card grid as the full-width item directly after the
 * p1_era_line_map card (spec §6.4 owner decision), so these cases render the
 * cards. The last two bind the rendered cards to gate 24 leg (s): what they
 * render, the leg accepts, and a summary the page disagrees with, the leg
 * rejects.
 */
import React from "react";
import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { parse } from "node-html-parser";
import { EraMapTable } from "@/components/era-map-table";
import { DownloadCards, type DownloadDataset } from "@/components/download-cards";
import { ERA_DECISIONS, type EraMapEdition, type EraMapSummary } from "@/lib/era-map";
import { runEraMapLeg } from "../../scripts/gates/datatruth.mjs";

function edition(ed: number, chains: number[], facts: number, complete: number): EraMapEdition {
  const lines = chains.map((c) => (c === 0 ? 0 : c + 1));
  const by_decision = Object.fromEntries(
    ERA_DECISIONS.map((d, i) => [d, { chains: chains[i], lines: lines[i], actuals_thousands: 1000 * chains[i] }]),
  ) as EraMapEdition["by_decision"];
  return { edition: ed, fy_actuals: ed - 2, lines: lines.reduce((a, b) => a + b, 0), by_decision, receipts: { facts, complete } };
}

const SUMMARY: EraMapSummary = {
  schema_version: 1,
  actuals_basis: "test",
  receipts_basis: "test",
  editions: [
    edition(2017, [690, 230, 45, 2, 2], 2214, 2107),
    edition(2018, [745, 240, 44, 0, 0], 2349, 2231),
    edition(2019, [768, 189, 32, 0, 0], 2262, 2160),
    edition(2020, [790, 160, 25, 0, 0], 2231, 2140),
    edition(2021, [812, 170, 0, 0, 1], 2298, 2210),
    edition(2022, [820, 150, 0, 0, 0], 2272, 2180),
    edition(2023, [815, 135, 0, 0, 0], 2212, 2120),
  ],
  by_ruling: [],
  totals: Object.fromEntries(ERA_DECISIONS.map((d) => [d, { chains: 0, lines: 0, actuals_thousands: 0 }])) as EraMapSummary["totals"],
};

function recountOf(summary: EraMapSummary) {
  return {
    present: true,
    editions: Object.fromEntries(
      summary.editions.map((e) => [
        String(e.edition),
        {
          lines: e.lines,
          by_decision: Object.fromEntries(
            Object.entries(e.by_decision)
              .filter(([, t]) => t.lines > 0)
              .map(([d, t]) => [d, { chains: t.chains, lines: t.lines }]),
          ),
        },
      ]),
    ),
  };
}

const auditOf = (summary: EraMapSummary) => ({
  books: summary.editions.map((e) => ({ edition: e.edition, exhibit: "P-1", facts: e.receipts.facts, complete: e.receipts.complete })),
});

const INVENTORY: DownloadDataset[] = [
  { name: "budget_lines", row_count: 159903, scope: "One row per budget line.", cited: true },
  { name: "p1_era_line_map", row_count: 6927, scope: "One row per PB2017–PB2023 P-1 display line.", cited: false },
  { name: "dim_programs", row_count: 1936, scope: "One row per program.", cited: true },
];
const cards = (eraMap: EraMapSummary | null) =>
  renderToStaticMarkup(
    <DownloadCards
      builtAt="2026-10-02T01:30:21.066005+00:00"
      inventory={INVENTORY}
      citationsIndex={{ row_count: 125409, scope: "The citation index." }}
      uncitedDatasets={["p1_era_line_map"]}
      eraMap={eraMap}
    />,
  );

const html = cards(SUMMARY);
const root = parse(html);
const cell = (ed: number, key: string) =>
  root.querySelector(`tr[data-era-edition="${ed}"] [data-era-cell="${key}"] [data-era-value]`)?.text;

describe("EraMapTable", () => {
  it("renders one row per edition, in edition order", () => {
    expect(root.querySelectorAll("[data-era-map]")).toHaveLength(1);
    expect(root.querySelectorAll("tr[data-era-edition]").map((r) => r.getAttribute("data-era-edition"))).toEqual(
      ["2017", "2018", "2019", "2020", "2021", "2022", "2023"],
    );
  });

  it("renders the counts, never a dollar figure", () => {
    expect(cell(2017, "lines")).toBe("974");
    expect(cell(2017, "same_program")).toBe("690 codes");
    expect(cell(2017, "history_only")).toBe("230 codes");
    expect(cell(2017, "excluded")).toBe("49 codes");
    expect(cell(2017, "receipts")).toBe("2,107 of 2,214");
    expect(cell(2018, "lines")).toBe("1,032");
    expect(root.querySelector("#era-map")!.toString()).not.toContain("$");
  });

  it("says code, not codes, for one", () => {
    expect(cell(2021, "excluded")).toBe("1 code");
  });

  it("renders directly after the p1_era_line_map card, full width in the card grid", () => {
    const card = root.querySelector('[data-dataset-card="p1_era_line_map"]');
    const next = card?.nextElementSibling;
    expect(next?.getAttribute("id")).toBe("era-map");
    expect(next?.classList.contains("sm:col-span-2")).toBe(true);
    expect(next?.parentNode).toBe(card?.parentNode);
    const alone = parse(renderToStaticMarkup(<EraMapTable summary={SUMMARY} />));
    expect(alone.querySelector("#era-map")?.classList.contains("sm:col-span-2")).toBe(true);
  });

  it("renders no table when the export shipped no summary", () => {
    const bare = parse(cards(null));
    expect(bare.querySelectorAll("[data-era-map]")).toHaveLength(0);
    expect(bare.querySelectorAll("[data-dataset-card]")).toHaveLength(4);
  });

  it("is what gate 24 leg (s) accepts", () => {
    const errors: string[] = [];
    const notes: string[] = [];
    runEraMapLeg(errors, notes, { recount: recountOf(SUMMARY), summary: SUMMARY, audit: auditOf(SUMMARY), html });
    expect(errors).toEqual([]);
    expect(notes.join("\n")).toMatch(/leg s: \/downloads\/ renders all 7 era editions/);
  });

  it("fails gate 24 leg (s) when the summary moves and the page does not", () => {
    const moved = structuredClone(SUMMARY);
    moved.editions[0].receipts.complete = 2108;
    const errors: string[] = [];
    runEraMapLeg(errors, [], { recount: recountOf(moved), summary: moved, audit: auditOf(moved), html });
    expect(errors).toEqual([
      'leg s (/downloads/): PB2017 receipts renders "2,107 of 2,214", era_map_summary.json says "2,108 of 2,214"',
    ]);
  });
});
