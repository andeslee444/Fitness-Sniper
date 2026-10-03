/**
 * The /downloads/ era-map table (families piece 1, spec 2026-10-02 §6.4,
 * Task 19). It renders counts from json/era_map_summary.json: lines, printed
 * codes per decision, and receipt completeness, never a dollar figure (a
 * rendered $ needs a Cite state these sums do not have). DownloadCards renders
 * it inside the card grid as the full-width item directly after the
 * p1_era_line_map card (spec §6.4 owner decision), so these cases render the
 * cards. The leg (s) cases bind the rendered cards to the gate: what they
 * render, the leg accepts, and a summary the page disagrees with, the leg
 * rejects.
 *
 * Task 19 fix round 1: (1) the cells count printed codes (distinct
 * line_item_code), never decisions, so the fixture's codes are smaller than
 * its chains; (2) the summary never crosses into the client DownloadCards:
 * the server page renders <EraMapTable> and passes the element, which the
 * boundary cases pin; (3) the p1_era_line_map card spans both columns with
 * the table; (4) card names are level-2 headings and the table's is an h3.
 */
import React from "react";
import fs from "fs";
import path from "path";
import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { parse } from "node-html-parser";
import { EraMapTable } from "@/components/era-map-table";
import { DownloadCards, type DownloadDataset } from "@/components/download-cards";
import { ERA_DECISIONS, type EraMapEdition, type EraMapSummary } from "@/lib/era-map";
import { runEraMapLeg } from "../../scripts/gates/datatruth.mjs";

const SRC = path.resolve(__dirname, "..");

function edition(
  ed: number,
  chains: number[],
  codes: number[],
  excludedCodes: number,
  facts: number,
  complete: number,
): EraMapEdition {
  const lines = chains.map((c) => (c === 0 ? 0 : c + 1));
  const by_decision = Object.fromEntries(
    ERA_DECISIONS.map((d, i) => [
      d,
      { chains: chains[i], codes: codes[i], lines: lines[i], actuals_thousands: chains[i] ? 1000 * chains[i] + 7 : 0 },
    ]),
  ) as EraMapEdition["by_decision"];
  return {
    edition: ed,
    fy_actuals: ed - 2,
    lines: lines.reduce((a, b) => a + b, 0),
    by_decision,
    excluded_codes: excludedCodes,
    receipts: { facts, complete },
  };
}

const SUMMARY: EraMapSummary = {
  schema_version: 1,
  actuals_basis: "test",
  receipts_basis: "test",
  editions: [
    edition(2017, [690, 230, 45, 2, 2], [628, 229, 1, 2, 2], 3, 2214, 2107),
    edition(2018, [745, 240, 44, 0, 0], [664, 238, 1, 0, 0], 1, 2349, 2231),
    edition(2019, [768, 189, 32, 0, 0], [675, 189, 1, 0, 0], 1, 2262, 2160),
    edition(2020, [790, 160, 25, 0, 0], [700, 160, 1, 0, 0], 1, 2231, 2140),
    edition(2021, [812, 170, 0, 0, 1], [720, 170, 0, 0, 1], 1, 2298, 2210),
    edition(2022, [820, 150, 0, 0, 0], [730, 150, 0, 0, 0], 0, 2272, 2180),
    edition(2023, [815, 135, 0, 0, 0], [729, 135, 0, 0, 0], 0, 2212, 2120),
  ],
  by_ruling: [],
  totals: Object.fromEntries(
    ERA_DECISIONS.map((d) => [d, { chains: 0, codes: 0, lines: 0, actuals_thousands: 0 }]),
  ) as EraMapSummary["totals"],
};

function recountOf(summary: EraMapSummary) {
  return {
    present: true,
    editions: Object.fromEntries(
      summary.editions.map((e) => [
        String(e.edition),
        {
          lines: e.lines,
          excluded_codes: e.excluded_codes,
          by_decision: Object.fromEntries(
            Object.entries(e.by_decision)
              .filter(([, t]) => t.lines > 0)
              .map(([d, t]) => [d, { chains: t.chains, codes: t.codes, lines: t.lines }]),
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
/** What the /downloads/ page does: render the table on the server and hand
 *  DownloadCards the element. */
const cards = (eraMap: EraMapSummary | null) =>
  renderToStaticMarkup(
    <DownloadCards
      builtAt="2026-10-02T01:30:21.066005+00:00"
      inventory={INVENTORY}
      citationsIndex={{ row_count: 125409, scope: "The citation index." }}
      uncitedDatasets={["p1_era_line_map"]}
      eraMapTable={eraMap ? <EraMapTable summary={eraMap} /> : null}
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
    expect(cell(2017, "receipts")).toBe("2,107 of 2,214");
    expect(cell(2018, "lines")).toBe("1,032");
    expect(root.querySelector("#era-map")!.toString()).not.toContain("$");
  });

  it("counts printed codes, not decisions", () => {
    expect(cell(2017, "same_program")).toBe("628 codes");
    expect(cell(2017, "history_only")).toBe("229 codes");
    // 49 exclude decisions, 3 distinct printed codes among them
    expect(cell(2017, "excluded")).toBe("3 codes");
    expect(cell(2018, "excluded")).toBe("1 code");
    const table = root.querySelector("#era-map")!.toString();
    for (const decisions of ["690 codes", "49 codes", "44 codes"]) expect(table).not.toContain(decisions);
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

  it("spans the p1_era_line_map card across both columns too, so the grid leaves no empty cell", () => {
    expect(root.querySelector('[data-dataset-card="p1_era_line_map"]')!.classList.contains("sm:col-span-2")).toBe(true);
    expect(root.querySelector('[data-dataset-card="budget_lines"]')!.classList.contains("sm:col-span-2")).toBe(false);
    const bare = parse(cards(null));
    expect(bare.querySelector('[data-dataset-card="p1_era_line_map"]')!.classList.contains("sm:col-span-2")).toBe(false);
  });

  it("nests the table's heading under the card's: cards are level 2, the table h3", () => {
    expect(root.querySelectorAll("h1, h2")).toHaveLength(0);
    const names = root.querySelectorAll('[data-dataset-card] [role="heading"]');
    expect(names.map((h) => [h.text.trim(), h.getAttribute("aria-level")])).toEqual([
      ["budget_lines", "2"],
      ["p1_era_line_map", "2"],
      ["dim_programs", "2"],
      ["citations", "2"],
    ]);
    const after = root.querySelectorAll('[role="heading"]').at(-1)!;
    expect([after.text.trim(), after.getAttribute("aria-level")]).toEqual(["Additional assets (not in table above)", "2"]);
    expect(root.querySelector("#era-map h3#era-map-heading")?.text.trim()).toBe("Procurement lines before PB2024");
    expect(root.querySelector("#era-map")!.getAttribute("aria-labelledby")).toBe("era-map-heading");
  });

  it("keeps table semantics on the display:block mobile rows, as /data/ does", () => {
    const rows = root.querySelectorAll("tr[data-era-edition]");
    expect(rows.every((r) => r.getAttribute("role") === "row")).toBe(true);
    expect(rows.every((r) => r.querySelector("th")?.getAttribute("role") === "rowheader")).toBe(true);
    const cells = root.querySelectorAll("td[data-era-cell]");
    expect(cells).toHaveLength(35);
    expect(cells.every((c) => c.getAttribute("role") === "cell")).toBe(true);
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

/**
 * The client boundary (Task 19 fix round 1). DownloadCards is "use client":
 * every prop it receives is serialised into /downloads/' RSC payload. Handed
 * the summary, it shipped all 45 actuals_thousands sums (R-DEC-ERA-SAME's
 * 651,579,549 among them) in a script no rendered-text gate reads. The page
 * now renders <EraMapTable> on the server and passes the element, so only the
 * rendered cells cross. These cases fail if the summary can cross again.
 */
describe("era map: nothing uncited crosses into the client DownloadCards", () => {
  const read = (rel: string) => fs.readFileSync(path.join(SRC, rel), "utf8");
  const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");

  it("EraMapTable stays a server component (a client one would serialise its summary prop)", () => {
    const src = code(read("components/era-map-table.tsx"));
    expect(src).not.toMatch(/["']use client["']/);
    expect(src).not.toMatch(/\buse(State|Effect|Context|Memo|Ref|AssetUrl)\b/);
  });

  it("DownloadCards takes a rendered table, never the summary", () => {
    const src = code(read("components/download-cards.tsx"));
    expect(src).toMatch(/^["']use client["']/);
    expect(src).toContain("eraMapTable?: React.ReactNode;");
    for (const banned of ["EraMapSummary", "@/lib/era-map", "@/components/era-map-table", "eraMap?:", "actuals_thousands"]) {
      expect(src).not.toContain(banned);
    }
  });

  it("the /downloads/ page renders the table itself and passes only the element", () => {
    const src = code(read("app/downloads/page.tsx"));
    expect(src).not.toMatch(/["']use client["']/);
    expect(src).toContain("const eraMapTable = eraMap ? <EraMapTable summary={eraMap} /> : null;");
    expect(src).toContain("eraMapTable={eraMapTable}");
    expect(src).not.toMatch(/\beraMap=\{/);
  });

  it("the summary file itself never ships: public/ and the R2 sync carry no json/era_map_summary.json", () => {
    const prepare = fs.readFileSync(path.join(SRC, "..", "scripts", "prepare-assets.mjs"), "utf8");
    expect(prepare).not.toContain("era_map_summary");
    const r2 = fs.readFileSync(path.join(SRC, "..", "..", "scripts", "launch", "upload_r2.sh"), "utf8");
    const folders = r2.match(/^declare -a FOLDERS=\(([^)]*)\)/m)?.[1].replaceAll('"', "").trim().split(/\s+/);
    expect(folders).toEqual(["pdfs", "data", "workbooks", "citations"]);
  });

  it("what crosses (the rendered table) carries no dollar sum", () => {
    const crossing = renderToStaticMarkup(<EraMapTable summary={SUMMARY} />);
    expect(crossing).not.toContain("actuals_thousands");
    for (const e of SUMMARY.editions) {
      for (const t of Object.values(e.by_decision)) {
        if (t.actuals_thousands) expect(crossing).not.toContain(String(t.actuals_thousands));
      }
    }
  });
});
