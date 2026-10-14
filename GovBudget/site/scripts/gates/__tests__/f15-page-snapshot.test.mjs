/**
 * f15-page-snapshot.mjs — the normalized /families/f-15/ snapshot that proves
 * the F-15 page does not change while era procurement history lands
 * (spec 2026-10-02-era-procurement-history-design.md §6.2, §9 S0).
 *
 * Fixture HTML only — no build. The markup mirrors
 * src/components/family-funding-history.tsx (section[data-family-history],
 * p[data-history-coverage], th[data-history-column], th#history-row-total,
 * td[data-history-annual] with its Partial badge, tr[data-history-program]
 * whose noted row header carries an aria-label, td[data-history-cell] with
 * data-history-inputs, data-history-missing, p[data-history-matrix-note] and
 * li[data-history-note]) and a Flight payload string the way Next
 * serializes record facts. Schema 2 (ROADMAP #201) adds the prose around the
 * matrix, which schema 1 skipped.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { describe, it, expect } from "vitest";
import { SNAPSHOT_SCHEMA, snapshotF15Page, firstDifference } from "../../f15-page-snapshot.mjs";

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
const N = "e7d5bcfb4a30f458";
const ROW_NAME = "BLI F015E0 F-15e (FY2020 F-15EX Lot 1 aircraft) Procurement · Historical code";

const PAGE = `<!DOCTYPE html><html><body>
<div data-entity="family:f-15"></div>
<section class="x__overview" data-family-history="f-15">
  <span data-fact-id="${T}" data-dataset="f15_funding_history" data-entity="family:f-15" style="flex-grow:0.6682583630407969">$771.1M</span>
  <p class="x__coverage" data-history-coverage="">Coverage starts in FY<!-- -->2015<!-- -->; earlier funding is not included.</p>
  <table><thead><tr><th>Program / budget line</th>
    <th scope="col" data-history-column="fy2015a">FY2015</th><th scope="col" data-history-column="fy2016a">FY2016</th></tr></thead>
  <tbody>
    <tr><th scope="row" id="history-row-total">F-15 family total<span class="x__rowMeta">Covered programs</span></th>
      <td data-history-annual="fy2015a"><span data-fact-id="${T}" data-dataset="f15_funding_history">$771.1M</span></td>
      <td data-history-annual="fy2016a"><span data-fact-id="${A}" data-dataset="f15_funding_history">$984.6M</span><span>Partial</span></td></tr>
    <tr data-history-program="P-1:3010F:AF:F01500"><th scope="row"><span class="x__programCode">BLI<!-- --> <!-- -->F01500</span><a href="/program/F01500/">F-15</a><span class="x__rowMeta">Procurement</span></th>
      <td data-history-cell="fy2015a" data-history-inputs="${R}"><span data-fact-id="${R}" data-dataset="budget_lines_decade">$498.3M</span></td>
      <td data-history-cell="fy2016a" data-history-inputs="${B},${C}"><span data-fact-id="${A}" data-dataset="f15_funding_history">$596.9M</span></td></tr>
    <tr data-history-program="P-1:3010F:AF:F015E0"><th scope="row" aria-label="${ROW_NAME}"><span>BLI F015E0</span><span>F-15e (FY2020 F-15EX Lot 1 aircraft)</span><span>Procurement · Historical code</span><a href="#history-note-F015E0" data-history-note-ref="F015E0">Note below</a></th>
      <td data-history-cell="fy2015a"><span data-history-missing="F015E0">Missing</span></td>
      <td data-history-cell="fy2016a"><span>—</span></td></tr>
  </tbody></table>
  <p class="x__matrixNote" data-history-matrix-note="">Historical F0150P and F015E0 remain separate.</p>
  <ul aria-label="Budget-line notes"><li id="history-note-F015E0" data-history-note="F015E0"><span>BLI F015E0</span><span data-source-text="narrative" data-cite-fact-id="${N}">“This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include
    the eight aircraft.”</span><button data-narrative-chip="" data-fact-id="${N}">Source</button></li></ul>
</section>
<script>self.__next_f.push([1,"{\\"factId\\":\\"${B}\\",\\"entity\\":\\"family:f-15\\"}"])</script>
</body></html>`;

describe("snapshotF15Page", () => {
  it("reduces the page to fact ids, datasets, entity count and the matrix", () => {
    const snap = snapshotF15Page(PAGE);
    expect(snap.schema).toBe(2);
    expect(snap.page).toBe("/families/f-15/");
    expect(snap.data_fact_id_elements).toBe(6);
    expect(snap.data_fact_ids).toEqual([R, A, T, N].sort());
    expect(snap.data_dataset_counts).toEqual({ budget_lines_decade: 1, f15_funding_history: 4 });
    expect(snap.family_f15_occurrences).toBe(3);
    // B and C appear only in data-history-inputs / the Flight payload; the
    // style fraction "0.6682583630407969" is not a fact id.
    expect(snap.page_fact_ids).toEqual([A, B, C, R, T, N].sort());
    expect(snap.page_fact_id_occurrences).toBe(11);
    expect(snap.matrix.columns).toEqual(["fy2015a", "fy2016a"]);
    expect(snap.matrix.total_header).toEqual(["F-15 family total", "Covered programs"]);
    expect(snap.matrix.annual).toEqual([
      { column: "fy2015a", fact_id: T, dataset: "f15_funding_history", text: "$771.1M", inputs: [], missing: null, partial: false },
      { column: "fy2016a", fact_id: A, dataset: "f15_funding_history", text: "$984.6M", inputs: [], missing: null, partial: true },
    ]);
    expect(snap.matrix.rows).toEqual([
      {
        program_id: "P-1:3010F:AF:F01500",
        label: ["BLI F01500", "F-15", "Procurement"],
        aria_label: null,
        cells: [
          { column: "fy2015a", fact_id: R, dataset: "budget_lines_decade", text: "$498.3M", inputs: [R], missing: null },
          { column: "fy2016a", fact_id: A, dataset: "f15_funding_history", text: "$596.9M", inputs: [B, C], missing: null },
        ],
      },
      {
        program_id: "P-1:3010F:AF:F015E0",
        label: ["BLI F015E0", "F-15e (FY2020 F-15EX Lot 1 aircraft)", "Procurement · Historical code", "Note below"],
        aria_label: ROW_NAME,
        cells: [
          { column: "fy2015a", fact_id: null, dataset: null, text: "Missing", inputs: [], missing: "F015E0" },
          { column: "fy2016a", fact_id: null, dataset: null, text: "—", inputs: [], missing: null },
        ],
      },
    ]);
  });

  it("captures the prose around the matrix (ROADMAP #201)", () => {
    expect(snapshotF15Page(PAGE).prose).toEqual({
      coverage: "Coverage starts in FY2015; earlier funding is not included.",
      matrix_note: "Historical F0150P and F015E0 remain separate.",
      notes: [{
        code: "F015E0", id: "history-note-F015E0", fact_id: N,
        quote: "“This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include the eight aircraft.”",
      }],
    });
  });

  it("sees a reworded note, coverage limit or Partial badge", () => {
    const snap = snapshotF15Page(PAGE);
    expect(firstDifference(snap, snapshotF15Page(PAGE.replace(" AP (F015EX)", " (F015EX)")))).toBe(
      '$.prose.notes[0].quote: "“This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include the eight aircraft.”"'
      + ' != "“This exhibit [the PB2026 F-15EX (F015EX) P-40] does not include the eight aircraft.”"');
    expect(firstDifference(snap, snapshotF15Page(PAGE.replace("earlier funding is not included", "earlier funding is included"))))
      .toMatch(/^\$\.prose\.coverage: /);
    expect(firstDifference(snap, snapshotF15Page(PAGE.replace("<span>Partial</span>", ""))))
      .toBe("$.matrix.annual[1].partial: true != false");
    expect(firstDifference(snap, snapshotF15Page(PAGE.replace(` aria-label="${ROW_NAME}"`, ""))))
      .toBe(`$.matrix.rows[1].aria_label: ${JSON.stringify(ROW_NAME)} != null`);
  });

  it("sees a fact that leaks only into the Flight payload", () => {
    const leaked = PAGE.replace("</body>", `<script>self.__next_f.push([1,"{\\"factId\\":\\"0123456789abcdef\\"}"])</script></body>`);
    const diff = firstDifference(snapshotF15Page(PAGE), snapshotF15Page(leaked));
    expect(diff).toMatch(/^\$\.page_fact_id_occurrences: 11 != 12$/);
  });

  it("refuses a page without the F-15 funding section or its prose hooks", () => {
    expect(() => snapshotF15Page("<html><body></body></html>")).toThrow(/no section\[data-family-history="f-15"\]/);
    expect(() => snapshotF15Page(PAGE.replace(' data-history-matrix-note=""', ""))).toThrow(/no matrix note \[data-history-matrix-note\]/);
  });
});

describe("firstDifference", () => {
  it("is null for equal snapshots and names the first differing path otherwise", () => {
    const snap = snapshotF15Page(PAGE);
    expect(firstDifference(snap, JSON.parse(JSON.stringify(snap)))).toBeNull();
    const relabeled = snapshotF15Page(PAGE.replace("<span>F-15e (FY2020 F-15EX Lot 1 aircraft)</span>", "<span>F-15e (legacy line)</span>"));
    expect(firstDifference(snap, relabeled)).toBe(
      '$.matrix.rows[1].label[1]: "F-15e (FY2020 F-15EX Lot 1 aircraft)" != "F-15e (legacy line)"');
  });
});

describe("committed baseline (tests/fixtures/f15/page_snapshot.json)", () => {
  it("is present, well-formed and of this schema", () => {
    expect(fs.existsSync(BASELINE), `missing ${BASELINE}: capture it from a fresh build (tests/fixtures/f15/README.md)`).toBe(true);
    const snap = JSON.parse(fs.readFileSync(BASELINE, "utf8"));
    expect(snap.schema).toBe(SNAPSHOT_SCHEMA);
    expect(snap.page).toBe("/families/f-15/");
    expect(snap.matrix.rows.map((row) => row.program_id)).toEqual(PROGRAM_IDS);
    expect(snap.matrix.columns).toHaveLength(12);
    expect(snap.matrix.annual.map((cell) => cell.column)).toEqual(snap.matrix.columns);
    for (const row of snap.matrix.rows) expect(row.cells.map((cell) => cell.column)).toEqual(snap.matrix.columns);
    expect(snap.data_fact_ids.length).toBeGreaterThan(0);
    for (const id of snap.page_fact_ids) expect(id).toMatch(/^[0-9a-f]{16}$/);
    expect(snap.data_fact_ids.filter((id) => !snap.page_fact_ids.includes(id))).toEqual([]);
    expect(snap.prose.notes.map((note) => note.code)).toEqual(["F015E0"]);
  });
});
