<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 20c: /families/f-15/ names the noted row without its link; the gate checks the note's link and receipt; the snapshot reads the prose (#201, Q21, #206 T9)

Third part of Task 20 (after 20a and 20b).

**Spec:** design §6.6 (#201: "Snapshot capture. The snapshot captures the coverage paragraph, the total-row header, the
Partial badges, the matrix note and the notes list"; "family-history gate. The note ref's href must be
`#history-note-<code>`. The receipt must have a page, a 64-hex sha and `#page=` in both URLs"; "Add the `aria-label`
from Q21"); §2.2 Q21 (owner: an `aria-label` on the F015E0 row header so that "Note below" leaves every cell's row
name — approved with Q17 on 2026-10-04); §5.2 (the site pin `NOTE` in
`site/src/__tests__/family-funding-history-note.test.tsx:12` changes; weight on /families/f-15/ measured by
substitution; "the receipt's own verbatim paragraph, the third occurrence, must not change"; the snapshot "changes
only through #201's new prose capture, re-pinned in the same step" — Task 21 P3); §6.9 (no trim of /families/f-15/
now); §7 P3, W4 (gate 21 / family-history, build page weights).

**Files:**
- Modify: `site/src/components/family-funding-history.tsx` (import :8; `rowName` before the component :17; the row
  header :85; the matrix note :106)
- Modify: `site/scripts/gates/family-history.mjs` (`checkFamilyHistoryNotes`: after the receipt-kind check :142-145;
  the note-ref check :153)
- Replace: `site/scripts/f15-page-snapshot.mjs` (whole file; schema 2)
- Replace: `site/scripts/gates/__tests__/f15-page-snapshot.test.mjs` (whole file)
- Modify: `site/src/__tests__/family-funding-history-note.test.tsx` (constants :11-13; `citations` :18; two tests)

Line numbers are hints measured at `532205c9` (anchor on the quoted text).

**Interfaces:**
Consumes: Task 20a's note string and `NOTE_RECEIPTS` (the site test mirrors them); Task 20b's
`site/scripts/direct-run.mjs` (`isDirectRun`), which the new snapshot file imports; `FamilyFundingProgram`
(`site/src/lib/family-funding-history.ts`); the program-skeleton gate's call
`checkFamilyHistory(parse(html), history, citations, slice)` with `citations` = `data/site/json/citations.json` (whose
`e7d5bcfb4a30f458` record carries `page_number` 71, `sha256` 528d1441…, `hosted_pdf_url` and `official_url` both ending
`#page=71`, read 2026-10-13).
Produces: the noted row header's `aria-label`, `rowName(program)` = `"<PE|BLI> <code> <title> <Development|Procurement>[ ·
Historical code]"`, for F015E0 `BLI F015E0 F-15e (FY2020 F-15EX Lot 1 aircraft) Procurement · Historical code` (Task 22's
stamp quotes it as Q21's string); `p[data-history-matrix-note]` (a selector hook; the matrix note has only a hashed
CSS-module class); family-history gate errors `program <code> note link does not target #history-note-<code>`,
`program <code> note receipt lacks its page, sha256 or #page= links`, `program <code> row header's accessible name
must name the line, not its "Note below" link`; snapshot schema 2: adds `prose` (`coverage`, `matrix_note`, `notes[]`
with `code`, `id`, `fact_id`, `quote`), `matrix.total_header`, `matrix.annual[].partial`, `matrix.rows[].aria_label`.
For Task 21 (P3): after the release build against B@fu-post, `node scripts/f15-page-snapshot.mjs
out/families/f-15/index.html --out ../tests/fixtures/f15/page_snapshot.json` writes the schema-2 baseline, and
`--check` against it must pass; /families/f-15/ page weight is re-stamped (`build.mjs` `PAGE_WEIGHT_BUDGET`, stamp
`703,427 / 68,538` against `725,000 / 70,000`).

**Red until Task 21 re-pins (by design):** `site/scripts/gates/__tests__/f15-page-snapshot.test.mjs` › "committed
baseline (tests/fixtures/f15/page_snapshot.json) › is present, well-formed and of this schema": the committed
baseline is schema 1 until Task 21h Step 3 (P3.4) rewrites it. With 20a's three Python goldens these are the only four
tests that may fail between this task and Task 21.

Verified now (read-only, 2026-10-13, the worktree's `site/out/families/f-15/index.html` built 2026-10-04, run through a
scratch copy of the schema-2 tool with the hook injected): `prose.coverage` = "Coverage starts in FY2015; earlier funding is
not included. Newer enacted funding and requests are shown separately."; `matrix.total_header` = ["F-15 family total",
"Covered programs"]; `annual[].partial` true only for the last two columns; one note, `F015E0`, `history-note-F015E0`,
fact `e7d5bcfb4a30f458`; the F015E0 row label carries "Note below" as its fourth element and has no `aria-label` today.

- [ ] **Step 1: Write the failing tests**

In `site/src/__tests__/family-funding-history-note.test.tsx` (:11-13), replace:

```tsx
// Spec §6.5 (S5): the strings the owner signed off, on a hermetic one-year history.
const NOTE = "This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four operationally representative test aircraft and two operational aircraft were purchased with procurement funds (F015E0, Line #3 [line 3 of the PB2020–21 P-1 (line 4 in PB2022)])).";
const NOTE_FID = "e7d5bcfb4a30f458";
```

with:

```tsx
// Spec §6.5 (S5): the strings the owner signed off, on a hermetic one-year
// history; the first gloss is the owner's 2026-10-04 amendment (#206 T9, Q17).
const NOTE = "This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four operationally representative test aircraft and two operational aircraft were purchased with procurement funds (F015E0, Line #3 [line 3 of the PB2020–21 P-1 (line 4 in PB2022)])).";
const NOTE_FID = "e7d5bcfb4a30f458";
const NOTE_SHA = "528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e";
// Owner Q21 (#201): the noted row's accessible name, without its "Note below" link.
const ROW_NAME = "BLI F015E0 F-15e (FY2020 F-15EX Lot 1 aircraft) Procurement · Historical code";
```

In `site/src/__tests__/family-funding-history-note.test.tsx` (:18), replace:

```tsx
const citations = { [NOTE_FID]: { kind: "jbook_narrative", page_number: 71 } };
```

with:

```tsx
const citations = { [NOTE_FID]: {
  kind: "jbook_narrative", page_number: 71, sha256: NOTE_SHA,
  hosted_pdf_url: `/pdfs/${NOTE_SHA}.pdf#page=71`,
  official_url: "https://www.saffm.hq.af.mil/Portals/84/documents/FY26/FY26%20Air%20Force%20Aircraft%20Procurement%20Vol%20I.pdf#page=71",
} };
```

In `site/src/__tests__/family-funding-history-note.test.tsx` (:50-51), replace:

```tsx
    expect(screen.getByRole("rowheader", { name: /F-15e \(FY2020 F-15EX Lot 1 aircraft\)/ })).toBeInTheDocument();
  });
```

with:

```tsx
    expect(screen.getByRole("rowheader", { name: /F-15e \(FY2020 F-15EX Lot 1 aircraft\)/ })).toBeInTheDocument();
  });

  it("names the noted row without its \"Note below\" link (#201, owner Q21)", () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(<FamilyFundingHistory history={view()} shortName="F-15" />);
    const header = screen.getByRole("rowheader", { name: ROW_NAME });
    expect(header).toHaveAttribute("aria-label", ROW_NAME);
    expect(header.querySelector("[data-history-note-ref]")).toHaveTextContent("Note below");
    // every cell of the row names this header, so no cell's row name carries the link
    expect(document.querySelector('[data-history-program="P-1:3010F:AF:F015E0"] td')).toHaveAttribute(
      "headers", expect.stringContaining(header.id));
    // a row without a note keeps the name its content gives it
    expect(document.querySelector('[data-history-program="P-1:3010F:AF:F01500"] th')).not.toHaveAttribute("aria-label");
    expect(document.querySelector("[data-history-matrix-note]")).toHaveTextContent("Historical F0150P and F015E0 remain separate.");
  });
```

In `site/src/__tests__/family-funding-history-note.test.tsx` (:71-72), replace:

```tsx
    expect(checkFamilyHistoryNotes(parse(renderToStaticMarkup(<FamilyFundingHistory history={view([plain])} shortName="F-15" />)), view(), citations)).toContain("family notes: 0 rendered for 1 noted program(s)");
  });
```

with:

```tsx
    expect(checkFamilyHistoryNotes(parse(renderToStaticMarkup(<FamilyFundingHistory history={view([plain])} shortName="F-15" />)), view(), citations)).toContain("family notes: 0 rendered for 1 noted program(s)");
  });

  it("release gate checks the note link's target, the receipt's page and sha, and the row name (#201)", () => {
    const html = renderToStaticMarkup(<FamilyFundingHistory history={view()} shortName="F-15" />);
    const elsewhere = parse(html);
    elsewhere.querySelector("[data-history-note-ref]")!.setAttribute("href", "#history-note-F01500");
    expect(checkFamilyHistoryNotes(elsewhere, view(), citations)).toEqual(["program F015E0 note link does not target #history-note-F015E0"]);
    const receipt = citations[NOTE_FID];
    for (const broken of [{ ...receipt, page_number: null }, { ...receipt, sha256: "abc" },
      { ...receipt, hosted_pdf_url: `/pdfs/${NOTE_SHA}.pdf` }, { ...receipt, official_url: receipt.official_url.replace("#page=71", "#page=7") }]) {
      expect(checkFamilyHistoryNotes(parse(html), view(), { [NOTE_FID]: broken })).toEqual(["program F015E0 note receipt lacks its page, sha256 or #page= links"]);
    }
    const unnamed = parse(html);
    unnamed.querySelector('[data-history-program="P-1:3010F:AF:F015E0"] th')!.removeAttribute("aria-label");
    expect(checkFamilyHistoryNotes(unnamed, view(), citations)).toEqual(["program F015E0 row header's accessible name must name the line, not its \"Note below\" link"]);
  });
```

Replace the whole of `site/scripts/gates/__tests__/f15-page-snapshot.test.mjs` with:

```js
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run src/__tests__/family-funding-history-note.test.tsx scripts/gates/__tests__/f15-page-snapshot.test.mjs`
Expected: failures in both files — "names the noted row without its \"Note below\" link" (no element with that
accessible name), "release gate checks the note link's target, the receipt's page and sha, and the row name" (the
gate returns `[]`), and the snapshot tests that expect schema 2 (`expected 1 to be 2`, missing `prose`).

- [ ] **Step 3: Implement**

In `site/src/components/family-funding-history.tsx` (:8), replace:

```tsx
import { familyHistorySeries, type FamilyFundingHistoryView, type FamilyFundingPointSummary } from "@/lib/family-funding-history";
```

with:

```tsx
import { familyHistorySeries, type FamilyFundingHistoryView, type FamilyFundingPointSummary, type FamilyFundingProgram } from "@/lib/family-funding-history";
```

In `site/src/components/family-funding-history.tsx` (:17), replace:

```tsx
/** Family scope is independent of the aircraft variant or individual record below. */
```

with:

```tsx
/** A noted row's accessible name: what its header shows, without the "Note
 *  below" link. Every cell names its row header (headers=…), so the link text
 *  was read as part of each of the row's cells (ROADMAP #201, owner Q21). */
function rowName(program: FamilyFundingProgram): string {
  return `${program.exhibit === "R-1" ? "PE" : "BLI"} ${program.code} ${program.title} ${program.exhibit === "R-1" ? "Development" : "Procurement"}${program.program_slug ? "" : " · Historical code"}`;
}

/** Family scope is independent of the aircraft variant or individual record below. */
```

In `site/src/components/family-funding-history.tsx` (:85), replace:

```tsx
              <th scope="row" id={`history-row-${index}`} className={styles.matrixProgram}>
```

with:

```tsx
              <th scope="row" id={`history-row-${index}`} className={styles.matrixProgram} aria-label={program.note ? rowName(program) : undefined}>
```

In `site/src/components/family-funding-history.tsx` (:106), replace:

```tsx
      <p className={styles.matrixNote}>Rows follow
```

with:

```tsx
      <p className={styles.matrixNote} data-history-matrix-note="">Rows follow
```

In `site/scripts/gates/family-history.mjs` (:142-145), replace:

```js
    if (!program.note || citations[program.note_fact_id]?.kind !== "jbook_narrative") {
      errors.push(`program ${program.code} note lacks a narrative receipt`);
      continue;
    }
```

with:

```js
    if (!program.note || citations[program.note_fact_id]?.kind !== "jbook_narrative") {
      errors.push(`program ${program.code} note lacks a narrative receipt`);
      continue;
    }
    // ROADMAP #201: the receipt must open the printed page — a page number, the
    // document's 64-hex sha256, and `#page=N` on both the hosted and the
    // official link — not merely be of the right kind.
    const receipt = citations[program.note_fact_id];
    const page = receipt.page_number;
    if (!(Number.isInteger(page) && page > 0) || !/^[0-9a-f]{64}$/.test(receipt.sha256 ?? "")
        || ![receipt.hosted_pdf_url, receipt.official_url].every(url => typeof url === "string" && url.endsWith(`#page=${page}`))) {
      errors.push(`program ${program.code} note receipt lacks its page, sha256 or #page= links`);
    }
```

In `site/scripts/gates/family-history.mjs` (:153), replace:

```js
    if (!root.querySelector(`[data-history-program="${program.id}"] [data-history-note-ref="${program.code}"]`)) errors.push(`program ${program.code} row does not point to its note`);
```

with:

```js
    const ref = root.querySelector(`[data-history-program="${program.id}"] [data-history-note-ref="${program.code}"]`);
    if (!ref) errors.push(`program ${program.code} row does not point to its note`);
    else if (ref.getAttribute("href") !== `#history-note-${program.code}`) errors.push(`program ${program.code} note link does not target #history-note-${program.code}`);
    // Owner Q21: each cell names this header, so its name must not carry the link.
    const name = root.querySelector(`[data-history-program="${program.id}"] th[scope="row"]`)?.getAttribute("aria-label") ?? "";
    if (!name.includes(program.code) || !name.includes(program.title) || name.includes("Note below")) {
      errors.push(`program ${program.code} row header's accessible name must name the line, not its "Note below" link`);
    }
```

Replace the whole of `site/scripts/f15-page-snapshot.mjs` with:

```js
#!/usr/bin/env node
/**
 * f15-page-snapshot.mjs — normalized snapshot of the built /families/f-15/ page.
 *
 * Spec 2026-10-02-era-procurement-history-design.md §6.2: the F-15 page must
 * not change while procurement history before FY2024 lands (S0–S4). A raw
 * HTML diff is useless for that proof — chunk names, CSS-module hashes and
 * the build id change with any code change anywhere — so this reduces the
 * page to what a reader and a citation check can see:
 *
 *   - every element carrying data-fact-id (count + distinct ids),
 *   - data-dataset counts,
 *   - occurrences of the family entity string "family:f-15",
 *   - every 16-hex fact-id token anywhere in the HTML, including the RSC
 *     (Flight) payload — the F-15 browser's records ship there, so an era
 *     fact leaking into loadRecord shows up here even when it is not in the
 *     initially rendered DOM,
 *   - the funding matrix: columns, the annual total row (with each year's
 *     Partial badge), and each program row's label, accessible name and
 *     cells (fact id, display text, inputs, missing marker),
 *   - the prose around it (schema 2, ROADMAP #201): the coverage paragraph,
 *     the total row's header, the matrix note and the budget-line notes list
 *     (code, anchor, receipt, quoted text) — schema 1 skipped all of these,
 *     so a reworded note or coverage limit passed the identity proof.
 *
 * Usage (from GovBudget/site):
 *   node scripts/f15-page-snapshot.mjs out/families/f-15/index.html
 *   node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --out ../tests/fixtures/f15/page_snapshot.json
 *   node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check ../tests/fixtures/f15/page_snapshot.json
 *
 * --check exits 1 and names the first differing path when the snapshot of
 * the page differs from the committed baseline.
 */

import fs from "fs";
import path from "path";
import { parse } from "node-html-parser";
import { isDirectRun } from "./direct-run.mjs";

export const SNAPSHOT_SCHEMA = 2;

// A fact id is 16 lowercase hex characters. Decimal fractions in inline
// styles ("0.6682583630407969") are excluded by the "." look-behind.
const FACT_TOKEN_RE = /(?<![0-9A-Za-z.])[0-9a-f]{16}(?![0-9A-Za-z])/g;

const attr = (el, name) => el?.getAttribute(name) ?? null;
const squash = (text) => String(text ?? "").replace(/\s+/g, " ").trim();

function sortedCounts(values) {
  const counts = {};
  for (const value of values) counts[value] = (counts[value] ?? 0) + 1;
  return Object.fromEntries(Object.entries(counts).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
}

function cellOf(td, columnAttr) {
  const figure = td.querySelector("[data-fact-id]");
  const inputs = attr(td, "data-history-inputs");
  return {
    column: attr(td, columnAttr),
    fact_id: attr(figure, "data-fact-id"),
    dataset: attr(figure, "data-dataset"),
    text: figure ? figure.text.trim() : td.text.trim(),
    inputs: inputs ? inputs.split(",") : [],
    missing: attr(td.querySelector("[data-history-missing]"), "data-history-missing"),
  };
}

/** Reduce a built /families/f-15/ HTML document to its normalized snapshot. */
export function snapshotF15Page(html) {
  const root = parse(html);
  const section = root.querySelector('section[data-family-history="f-15"]');
  if (!section) throw new Error('f15-page-snapshot: no section[data-family-history="f-15"] in the page');
  const factElements = root.querySelectorAll("[data-fact-id]");
  const tokens = html.match(FACT_TOKEN_RE) ?? [];
  const rows = section.querySelectorAll("tr[data-history-program]").map((tr) => {
    const th = tr.querySelector("th");
    return {
      program_id: attr(tr, "data-history-program"),
      label: th.childNodes.filter((node) => node.nodeType === 1).map((node) => node.text.trim()),
      aria_label: attr(th, "aria-label"),
      cells: tr.querySelectorAll("td[data-history-cell]").map((td) => cellOf(td, "data-history-cell")),
    };
  });
  if (rows.length === 0) throw new Error("f15-page-snapshot: the funding matrix has no program rows");
  const coverage = section.querySelector("[data-history-coverage]");
  const totalHeader = section.querySelector("th#history-row-total");
  const matrixNote = section.querySelector("[data-history-matrix-note]");
  for (const [name, el] of [["coverage paragraph [data-history-coverage]", coverage],
    ["total-row header th#history-row-total", totalHeader], ["matrix note [data-history-matrix-note]", matrixNote]]) {
    if (!el) throw new Error(`f15-page-snapshot: no ${name} in the funding section`);
  }
  return {
    schema: SNAPSHOT_SCHEMA,
    page: "/families/f-15/",
    data_fact_id_elements: factElements.length,
    data_fact_ids: [...new Set(factElements.map((el) => attr(el, "data-fact-id")))].sort(),
    data_dataset_counts: sortedCounts(root.querySelectorAll("[data-dataset]").map((el) => attr(el, "data-dataset"))),
    family_f15_occurrences: html.split("family:f-15").length - 1,
    page_fact_id_occurrences: tokens.length,
    page_fact_ids: [...new Set(tokens)].sort(),
    prose: {
      coverage: squash(coverage.text),
      matrix_note: squash(matrixNote.text),
      notes: section.querySelectorAll("li[data-history-note]").map((li) => ({
        code: attr(li, "data-history-note"),
        id: attr(li, "id"),
        fact_id: attr(li.querySelector("[data-cite-fact-id]"), "data-cite-fact-id"),
        quote: squash(li.querySelector('[data-source-text="narrative"]')?.text),
      })),
    },
    matrix: {
      columns: section.querySelectorAll("th[data-history-column]").map((th) => attr(th, "data-history-column")),
      total_header: totalHeader.childNodes.map((node) => squash(node.text)).filter(Boolean),
      annual: section.querySelectorAll("td[data-history-annual]").map((td) => ({
        ...cellOf(td, "data-history-annual"),
        partial: td.childNodes.some((node) => node.nodeType === 1 && node.text.trim() === "Partial"),
      })),
      rows,
    },
  };
}

/** First path at which two JSON values differ, or null when they are equal. */
export function firstDifference(a, b, at = "$") {
  if (Object.is(a, b)) return null;
  if (typeof a !== typeof b || a === null || b === null || typeof a !== "object" || Array.isArray(a) !== Array.isArray(b)) {
    return `${at}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`;
  }
  const keys = Array.isArray(a)
    ? [...Array(Math.max(a.length, b.length)).keys()]
    : [...new Set([...Object.keys(a), ...Object.keys(b)])].sort();
  for (const key of keys) {
    const found = firstDifference(a[key], b[key], Array.isArray(a) ? `${at}[${key}]` : `${at}.${key}`);
    if (found) return found;
  }
  return null;
}

function main(argv) {
  const [input, flag, target] = argv;
  if (!input || (flag && !["--out", "--check"].includes(flag)) || (flag && !target)) {
    console.error("usage: node scripts/f15-page-snapshot.mjs <index.html> [--out FILE | --check FILE]");
    return 2;
  }
  const snapshot = snapshotF15Page(fs.readFileSync(input, "utf8"));
  const text = JSON.stringify(snapshot, null, 2) + "\n";
  if (flag === "--out") {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, text);
    console.log(`f15-page-snapshot: wrote ${target} (${snapshot.data_fact_id_elements} data-fact-id elements, ${snapshot.page_fact_ids.length} distinct page fact ids, ${snapshot.matrix.rows.length} matrix rows, ${snapshot.prose.notes.length} note(s))`);
    return 0;
  }
  if (flag === "--check") {
    const diff = firstDifference(JSON.parse(fs.readFileSync(target, "utf8")), snapshot);
    if (diff) {
      console.error(`f15-page-snapshot: FAIL — differs from ${target} at ${diff}`);
      return 1;
    }
    console.log(`f15-page-snapshot: PASS — equal to ${target}`);
    return 0;
  }
  process.stdout.write(text);
  return 0;
}

if (isDirectRun(import.meta.url)) {
  process.exit(main(process.argv.slice(2)));
}
```

- [ ] **Step 4: Run the tests**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run src/__tests__/family-funding-history-note.test.tsx scripts/gates/__tests__/f15-page-snapshot.test.mjs scripts/__tests__/direct-run.test.mjs`
Expected: exactly one failure, the committed-baseline test (`expected 1 to be 2`), red by design until Task 21 P3
(overlay: `Tests  1 failed | 12 passed (13)` for the first two files).

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -c "family-funding-history" || true`
Expected: `0`.

- [ ] **Step 5: Weigh /families/f-15/ by substitution**

Applies the gloss (to the two note occurrences, SSR text and RSC props, never the receipt's own paragraph), the
`aria-label` and the hook to the current build in memory; gzip level 9 as gate 1 does.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site || exit 1
node --input-type=module - out/families/f-15/index.html <<'EOF'
// /families/f-15/ weight by substitution: the T9 gloss (SSR text + RSC props, never
// the receipt's own paragraph), the Q21 aria-label, the snapshot's matrix-note hook.
import fs from "fs"; import zlib from "zlib";
const file = process.argv[2];
const before = fs.readFileSync(file, "utf8");
const OLD = "This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (two test aircraft were purchased with RDT&amp;E";
const OLD_RSC = "This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (two test aircraft were purchased with RDT\\u0026E";
let after = before;
const count = (s, x) => s.split(x).length - 1;
console.log("ssr occurrences", count(before, OLD), "rsc(\\u0026) occurrences", count(before, OLD_RSC), "plain-& occurrences", count(before, OLD.replace("&amp;", "&")));
// Only occurrences that continue into the gloss-bearing note (…Line #3 [line 3 …) are the note; the receipt paragraph ends "Line #3))".
const GL = " [the PB2026 F-15EX AP (F015EX) P-40]";
let n = 0;
after = after.replace(/This exhibit( does not include the eight aircraft in Lot 1[^"<]*?Line #3 \[line 3)/g, (m, rest) => { n++; return "This exhibit" + GL + rest; });
console.log("gloss inserted", n);
const TH = '<th scope="row" id="history-row-7"';
const LABEL = ' aria-label="BLI F015E0 F-15e (FY2020 F-15EX Lot 1 aircraft) Procurement · Historical code"';
console.log("F015E0 th", count(after, TH));
after = after.replace(TH, TH + LABEL);
const MN = '<p class="family-funding-history-module__vnWGSG__matrixNote"';
console.log("matrix note p", count(after, MN));
after = after.replace(MN, MN + ' data-history-matrix-note=""');
const w = (s) => ({ raw: Buffer.byteLength(s), gzip: zlib.gzipSync(Buffer.from(s), { level: 9 }).length });
const b = w(before), a = w(after);
console.log(`/families/f-15/: ${b.raw} / ${b.gzip} -> ${a.raw} / ${a.gzip} (raw +${a.raw - b.raw}, gzip +${a.gzip - b.gzip}); ceiling 725,000 / 70,000`);
EOF
```
Expected (measured 2026-10-13 on the build of 2026-10-04):

```
ssr occurrences 1 rsc(\u0026) occurrences 2 plain-& occurrences 0
gloss inserted 2
F015E0 th 1
matrix note p 1
/families/f-15/: 703427 / 68538 -> 703621 / 68605 (raw +194, gzip +67); ceiling 725,000 / 70,000
```
1,395 gzip bytes stay free (the design's +68 / +36 measured the unamended gloss alone). If the build was redone by an
earlier task, the deltas must still be +194 / +67 within a few gzip bytes; a ceiling is never raised.

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/src/components/family-funding-history.tsx GovBudget/site/scripts/gates/family-history.mjs GovBudget/site/scripts/f15-page-snapshot.mjs GovBudget/site/scripts/gates/__tests__/f15-page-snapshot.test.mjs GovBudget/site/src/__tests__/family-funding-history-note.test.tsx && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(f15): the noted row's name leaves out its link; gate the note link, receipt and name; snapshot the prose (#201, Q21)" -m "aria-label on the noted row header (BLI F015E0 F-15e (FY2020 F-15EX Lot 1 aircraft) Procurement · Historical code). family-history: href #history-note-<code>, receipt page + 64-hex sha + #page= on both URLs. Snapshot schema 2 adds the coverage paragraph, total-row header, Partial badges, matrix note and notes; Task 21 P3 re-pins page_snapshot.json. +194 raw / +67 gzip by substitution." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
