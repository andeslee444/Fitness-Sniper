/**
 * f15-page-snapshot.mjs — the normalized /families/f-15/ snapshot that proves
 * the F-15 page does not change while era procurement history lands
 * (spec 2026-10-02-era-procurement-history-design.md §6.2, §9 S0).
 *
 * Fixture HTML only — no build. The markup mirrors
 * src/components/family-funding-history.tsx (section[data-family-history],
 * th[data-history-column], td[data-history-annual], tr[data-history-program],
 * td[data-history-cell] with data-history-inputs, data-history-missing) and a
 * Flight payload string the way Next serializes record facts.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { describe, it, expect } from "vitest";
import { snapshotF15Page, firstDifference } from "../../f15-page-snapshot.mjs";

const BASELINE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../tests/fixtures/f15/page_snapshot.json");
// f15_funding_history.py PROGRAMS, in row order.
const PROGRAM_IDS = [
  "R-1:3600F:AF:0207134F", "R-1:3600F:AF:0207146F", "R-1:3600F:AF:0207171F",
  "P-1:3010F:AF:F01500", "P-1:3010F:AF:F015EX", "P-1:3010F:AF:F15EWS",
  "P-1:3010F:AF:F0150P", "P-1:3010F:AF:F015E0",
];

const A = "a0231f5a75a7ad52";
const B = "28f53c8d681494cc";
const C = "cce72b42a96bfcb7";
const T = "e2a8baadbe15c1e5";
const R = "3bd9c921b2397209";

const PAGE = `<!DOCTYPE html><html><body>
<div data-entity="family:f-15"></div>
<section class="x__overview" data-family-history="f-15">
  <span data-fact-id="${T}" data-dataset="f15_funding_history" data-entity="family:f-15" style="flex-grow:0.6682583630407969">$771.1M</span>
  <table><thead><tr><th>Program / budget line</th>
    <th scope="col" data-history-column="fy2015a">FY2015</th><th scope="col" data-history-column="fy2016a">FY2016</th></tr></thead>
  <tbody>
    <tr><th scope="row">F-15 family total</th>
      <td data-history-annual="fy2015a"><span data-fact-id="${T}" data-dataset="f15_funding_history">$771.1M</span></td>
      <td data-history-annual="fy2016a"><span data-fact-id="${A}" data-dataset="f15_funding_history">$984.6M</span><span>Partial</span></td></tr>
    <tr data-history-program="P-1:3010F:AF:F01500"><th scope="row"><span class="x__programCode">BLI<!-- --> <!-- -->F01500</span><a href="/program/F01500/">F-15</a><span class="x__rowMeta">Procurement</span></th>
      <td data-history-cell="fy2015a" data-history-inputs="${R}"><span data-fact-id="${R}" data-dataset="budget_lines_decade">$498.3M</span></td>
      <td data-history-cell="fy2016a" data-history-inputs="${B},${C}"><span data-fact-id="${A}" data-dataset="f15_funding_history">$596.9M</span></td></tr>
    <tr data-history-program="P-1:3010F:AF:F015E0"><th scope="row"><span>BLI F015E0</span><span>F-15e (legacy line)</span><span>Procurement · Historical code</span></th>
      <td data-history-cell="fy2015a"><span data-history-missing="F015E0">Missing</span></td>
      <td data-history-cell="fy2016a"><span>—</span></td></tr>
  </tbody></table>
</section>
<script>self.__next_f.push([1,"{\\"factId\\":\\"${B}\\",\\"entity\\":\\"family:f-15\\"}"])</script>
</body></html>`;

describe("snapshotF15Page", () => {
  it("reduces the page to fact ids, datasets, entity count and the matrix", () => {
    const snap = snapshotF15Page(PAGE);
    expect(snap.schema).toBe(1);
    expect(snap.page).toBe("/families/f-15/");
    expect(snap.data_fact_id_elements).toBe(5);
    expect(snap.data_fact_ids).toEqual([R, A, T].sort());
    expect(snap.data_dataset_counts).toEqual({ budget_lines_decade: 1, f15_funding_history: 4 });
    expect(snap.family_f15_occurrences).toBe(3);
    // B and C appear only in data-history-inputs / the Flight payload; the
    // style fraction "0.6682583630407969" is not a fact id.
    expect(snap.page_fact_ids).toEqual([A, B, C, R, T].sort());
    expect(snap.page_fact_id_occurrences).toBe(9);
    expect(snap.matrix.columns).toEqual(["fy2015a", "fy2016a"]);
    expect(snap.matrix.annual).toEqual([
      { column: "fy2015a", fact_id: T, dataset: "f15_funding_history", text: "$771.1M", inputs: [], missing: null },
      { column: "fy2016a", fact_id: A, dataset: "f15_funding_history", text: "$984.6M", inputs: [], missing: null },
    ]);
    expect(snap.matrix.rows).toEqual([
      {
        program_id: "P-1:3010F:AF:F01500",
        label: ["BLI F01500", "F-15", "Procurement"],
        cells: [
          { column: "fy2015a", fact_id: R, dataset: "budget_lines_decade", text: "$498.3M", inputs: [R], missing: null },
          { column: "fy2016a", fact_id: A, dataset: "f15_funding_history", text: "$596.9M", inputs: [B, C], missing: null },
        ],
      },
      {
        program_id: "P-1:3010F:AF:F015E0",
        label: ["BLI F015E0", "F-15e (legacy line)", "Procurement · Historical code"],
        cells: [
          { column: "fy2015a", fact_id: null, dataset: null, text: "Missing", inputs: [], missing: "F015E0" },
          { column: "fy2016a", fact_id: null, dataset: null, text: "—", inputs: [], missing: null },
        ],
      },
    ]);
  });

  it("sees a fact that leaks only into the Flight payload", () => {
    const leaked = PAGE.replace("</body>", `<script>self.__next_f.push([1,"{\\"factId\\":\\"0123456789abcdef\\"}"])</script></body>`);
    const diff = firstDifference(snapshotF15Page(PAGE), snapshotF15Page(leaked));
    expect(diff).toMatch(/^\$\.page_fact_id_occurrences: 9 != 10$/);
  });

  it("refuses a page without the F-15 funding section", () => {
    expect(() => snapshotF15Page("<html><body></body></html>")).toThrow(/no section\[data-family-history="f-15"\]/);
  });
});

describe("firstDifference", () => {
  it("is null for equal snapshots and names the first differing path otherwise", () => {
    const snap = snapshotF15Page(PAGE);
    expect(firstDifference(snap, JSON.parse(JSON.stringify(snap)))).toBeNull();
    const relabeled = snapshotF15Page(PAGE.replace("F-15e (legacy line)", "F-15e (FY2020 F-15EX Lot 1 aircraft)"));
    expect(firstDifference(snap, relabeled)).toBe(
      '$.matrix.rows[1].label[1]: "F-15e (legacy line)" != "F-15e (FY2020 F-15EX Lot 1 aircraft)"');
  });
});

describe("committed S0 baseline (tests/fixtures/f15/page_snapshot.json)", () => {
  it("is present and well-formed", () => {
    expect(fs.existsSync(BASELINE), `missing ${BASELINE}: capture it from a fresh build (Task 4)`).toBe(true);
    const snap = JSON.parse(fs.readFileSync(BASELINE, "utf8"));
    expect(snap.schema).toBe(1);
    expect(snap.page).toBe("/families/f-15/");
    expect(snap.matrix.rows.map((row) => row.program_id)).toEqual(PROGRAM_IDS);
    expect(snap.matrix.columns).toHaveLength(12);
    expect(snap.matrix.annual.map((cell) => cell.column)).toEqual(snap.matrix.columns);
    for (const row of snap.matrix.rows) expect(row.cells.map((cell) => cell.column)).toEqual(snap.matrix.columns);
    expect(snap.data_fact_ids.length).toBeGreaterThan(0);
    for (const id of snap.page_fact_ids) expect(id).toMatch(/^[0-9a-f]{16}$/);
    expect(snap.data_fact_ids.filter((id) => !snap.page_fact_ids.includes(id))).toEqual([]);
  });
});
