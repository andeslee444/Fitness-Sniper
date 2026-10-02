<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 22: F-15 corrections (S5)

**Spec:** §6.5 (label, cited note, coverage notes, re-pins, exact-diff check), §9 S5 ("the owner signs off the exact strings; re-pins; the diff equals the approved changes"), §8 V4(f), V5.
**Files:**
- Modify: `src/govbudget/f15_funding_history.py` — `PROGRAMS` (:51–65, F015E0 row :63), `COVERAGE_NOTES` (:72–79; index 2 is :75, the variant-allocation note), new `PROGRAM_NOTES`/`NOTE_RECEIPTS` before `PROGRAMS`, new `check_program_notes` after `_json_bytes` (:82–83), call after `registry = json.loads(registry_path.read_text())` (:352)
- Modify: `tests/test_f15_funding_history.py` — imports (:7–13) and three new tests at the end
- Modify: `site/src/lib/family-funding-history.ts` — `FamilyFundingProgram` (:21–30), `validateFamilyHistoryMatrix` (:138)
- Modify: `site/src/components/family-funding-history.tsx` — imports (:5), `noted` (:22), program row header (:83–87), note list after the `matrixNote` paragraph (:103)
- Modify: `site/src/components/family-funding-history.module.css` — append after :82
- Modify: `site/scripts/gates/family-history.mjs` — call at the end of `checkFamilyHistory` (:121–127) and new export `checkFamilyHistoryNotes`
- Create: `site/src/__tests__/family-funding-history-note.test.tsx`
- Create: `docs/superpowers/plans/2026-10-02-era-procurement-history-expected-diff-s5.json`
- Modify (re-pins): `tests/fixtures/f15/history.json`, `tests/fixtures/f15/history.sha256`, `tests/fixtures/f15/builder_inputs.json.gz`, `tests/fixtures/f15/page_snapshot.json`
- Modify: `site/scripts/gates/build.mjs` — the `/families/f-15/` `PAGE_WEIGHT_BUDGET` entry (:254) `measured` stamp and its comment
- Modify: `docs/superpowers/ROADMAP.md` — the "F-15 family funding correction (2026-09-24)" paragraph under "## Current priorities" (lines 32–40 today)

**Interfaces:**
Consumes: `.proofs/s4-B`, `.proofs/s4/env.sh` and `govbudget_proof_s4` (Task 21; Task 3's snapshot layout: a run dir holds `site/`, `duckdb/govbudget.duckdb`, `parquet/`); `scripts/export_f15_funding_history.py` (exists, :1–12); `govbudget proof diff A B --expect RULES.json` (Task 3); Task 4's `scripts/era/capture_f15_fixtures.py --site-dir DIR --duckdb PATH --out-dir DIR --expect-sha256 HEX` (writes `history.sha256` as 64 hex + newline) and `site/scripts/f15-page-snapshot.mjs <index.html> --out FILE`; `tests/test_f15_era_identity.py` (Task 4); `govbudget verify-era-map` leg f (Task 20); `NarrativeSourceChip` (`site/src/components/narrative-chip.tsx`); narrative fact `e7d5bcfb4a30f458`.
Produces: `f15_funding_history.PROGRAM_NOTES: dict[str, dict]`, `NOTE_RECEIPTS: dict[str, dict]`, `check_program_notes(programs, registry) -> None` (raises `ValueError("F-15 program note receipt mismatch: …")`); payload `programs[]` entries may carry `note: str` and `note_fact_id: str` (both or neither); TS `FamilyFundingProgram.note?: string`, `note_fact_id?: string`; gate export `checkFamilyHistoryNotes(root, history, citations) -> string[]`; DOM hooks `[data-history-note="<code>"]`, `[data-history-note-ref="<code>"]`; new pins.

Verified now (read-only): `e7d5bcfb4a30f458` is in `data/site/json/cite-shards/e7.json` as `kind: jbook_narrative`, `page_number: 71`, `pe_bli: F015EX`, `sha256: 528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e` (PB2026 AF Aircraft Procurement Vol I). Page 71 of that PDF prints, verbatim: "Funding for this exhibit is contained in PE 0207146F. This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four operationally representative test aircraft and two operational aircraft were purchased with procurement funds (F015E0, Line #3))." `ERA_PROGRAM_CODES` (`f15_funding_history.py:46-48`) places F015E0 at line 3 in PB2020 and PB2021, line 4 in PB2022. Today's history: 30 annual points, 207 source facts, 8 programs, 67 default cells, cumulative 17,043,321 thousand, sha256 `9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800`. F-15 page ceiling `725,000 / 70,000`, stamp `701,316 / 67,757` (`build.mjs:254`). The gate already forbids any `$` figure outside a cited amount on this section (`family-history.mjs:121-125`); none of the new strings carries one.

- [ ] **Step 1: Owner sign-off on the exact strings (before any code)**

Send the owner, in chat, exactly:

> F-15 corrections for families piece 1 (spec §6.5). Please approve or amend these exact strings:
> 1. F015E0 row label: `F-15e (legacy line)` → `F-15e (FY2020 F-15EX Lot 1 aircraft)`
> 2. F015E0 note, quoted from the PB2026 F-15EX P-40 (AF Aircraft Procurement Vol I, PDF p.71) and cited to that page's receipt, with my gloss in brackets: “This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four operationally representative test aircraft and two operational aircraft were purchased with procurement funds (F015E0, Line #3 [line 3 of the PB2020–21 P-1 (line 4 in PB2022)])).” — shown in a note list under the matrix; the F015E0 row gets a “Note below” link to it.
> 3. Coverage note 3, amended: “Historical procurement line numbers change between editions. Each legacy line is matched within its own budget edition, without asserting a modern-program or aircraft-variant allocation, except where a budget book states one (F015E0).”
> 4. New last coverage note: “The totals exclude classified funding and military construction.”

Wait for the owner's reply. If any string is amended, use the amended text everywhere the steps below write it (Python `PROGRAM_NOTES`/`COVERAGE_NOTES`, both test files, the Step 14 check). Record the reply and its date for Step 20.

- [ ] **Step 2: Write the failing Python tests**

In `tests/test_f15_funding_history.py`, replace the import block (:7–13):

```python
from govbudget.f15_funding_history import (
    ERA_MEMBERS,
    ERA_PROGRAM_CODES,
    build_history,
    build_program_matrix,
    member_row,
)
```
with:

```python
from govbudget.f15_funding_history import (
    ERA_MEMBERS,
    ERA_PROGRAM_CODES,
    PROGRAMS,
    build_history,
    build_program_matrix,
    check_program_notes,
    member_row,
)
```
and append at the end of the file:

```python


# Spec §6.5 (S5): the strings the owner signed off.
F015E0_LABEL = "F-15e (FY2020 F-15EX Lot 1 aircraft)"
F015E0_NOTE = (
    "This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in "
    "FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four operationally "
    "representative test aircraft and two operational aircraft were purchased with procurement funds "
    "(F015E0, Line #3 [line 3 of the PB2020–21 P-1 (line 4 in PB2022)]))."
)
NARRATIVE = dict(kind="jbook_narrative", page_number=71, pe_bli="F015EX",
                 sha256="528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e")


def test_f015e0_row_is_retitled_and_carries_its_cited_lot1_note():
    row = source("3010F-AF-L4", 2022, amount_type="fy_2020_actuals", value=621100, exhibit="P-1", account="3010F", organization="AF", budget_activity="01", title="F-15e", cells="J10")
    payload, _, leaves, _ = build([row], [point(row, fy=2020)])
    enriched, _, _ = matrix(payload, leaves)
    programs = {p["code"]: p for p in enriched["programs"]}
    assert programs["F015E0"]["title"] == F015E0_LABEL
    assert programs["F015E0"]["note"] == F015E0_NOTE
    assert programs["F015E0"]["note_fact_id"] == "e7d5bcfb4a30f458"
    assert [code for code, p in programs.items() if "note" in p or "note_fact_id" in p] == ["F015E0"]
    assert programs["F0150P"]["title"] == "F-15 (legacy support line)"


def test_coverage_notes_state_the_exclusions_and_the_f015e0_allocation():
    row = source()
    payload, *_ = build([row], [point(row)])
    notes = payload["coverage_notes"]
    assert notes[2] == ("Historical procurement line numbers change between editions. Each legacy line is matched "
                        "within its own budget edition, without asserting a modern-program or aircraft-variant "
                        "allocation, except where a budget book states one (F015E0).")
    assert notes[-1] == "The totals exclude classified funding and military construction."
    assert len(notes) == 7


def test_a_program_note_ships_only_with_its_reviewed_narrative_receipt():
    check_program_notes(PROGRAMS, {"e7d5bcfb4a30f458": dict(NARRATIVE)})
    for registry in ({}, {"e7d5bcfb4a30f458": {**NARRATIVE, "page_number": 70}},
                     {"e7d5bcfb4a30f458": {**NARRATIVE, "kind": "workbook"}},
                     {"e7d5bcfb4a30f458": {**NARRATIVE, "sha256": "f" * 64}}):
        with pytest.raises(ValueError, match="program note receipt mismatch"):
            check_program_notes(PROGRAMS, registry)
    unreviewed = [{**PROGRAMS[0], "note": "x", "note_fact_id": "0123456789abcdef"}]
    with pytest.raises(ValueError, match="program note receipt mismatch"):
        check_program_notes(unreviewed, {"0123456789abcdef": dict(NARRATIVE)})
    with pytest.raises(ValueError, match="program note receipt mismatch"):
        check_program_notes([{**PROGRAMS[0], "note": "x"}], {})
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uv run --project . pytest tests/test_f15_funding_history.py -q`
Expected: collection error `ImportError: cannot import name 'check_program_notes' from 'govbudget.f15_funding_history'`.

- [ ] **Step 4: Implement the Python change**

In `src/govbudget/f15_funding_history.py`, replace the head of `PROGRAMS` (:51–55):

```python
PROGRAMS = [
    dict(id=f"{exhibit}:{account}:AF:{code}", code=code, title=title,
         program_slug=code if code in MODERN_MEMBERS else None,
         exhibit=exhibit, account=account, organization="AF")
    for code, exhibit, account, title in [
```
with:

```python
# A program note quotes the one budget-book sentence that states what a line
# bought, cited to that sentence's narrative receipt (spec §6.5; the owner
# signed off the exact strings, recorded in the ROADMAP). F015E0: PB2026 AF
# Aircraft Procurement Vol I, F015EX P-40 description, PDF p.71, the only page
# that prints it. The quote is verbatim; the [bracketed] gloss is ours, read
# from ERA_PROGRAM_CODES (F015E0 is line 3 in PB2020–21, line 4 in PB2022).
PROGRAM_NOTES = {
    "F015E0": dict(
        note=("This exhibit does not include the eight aircraft in Lot 1 which were funded outside this "
              "exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four "
              "operationally representative test aircraft and two operational aircraft were purchased with "
              "procurement funds (F015E0, Line #3 [line 3 of the PB2020–21 P-1 (line 4 in PB2022)]))."),
        note_fact_id="e7d5bcfb4a30f458",
    ),
}
# What each note_fact_id must resolve to in the exported registry: the
# jbook_narrative receipt for that paragraph, in that exact PDF.
NOTE_RECEIPTS = {
    "e7d5bcfb4a30f458": dict(kind="jbook_narrative", page_number=71,
                             sha256="528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e"),
}
PROGRAMS = [
    dict(id=f"{exhibit}:{account}:AF:{code}", code=code, title=title,
         program_slug=code if code in MODERN_MEMBERS else None,
         exhibit=exhibit, account=account, organization="AF",
         **PROGRAM_NOTES.get(code, {}))
    for code, exhibit, account, title in [
```
Replace the F015E0 row (:63):

```python
        ("F015E0", "P-1", "3010F", "F-15e (legacy line)"),
```
with:

```python
        ("F015E0", "P-1", "3010F", "F-15e (FY2020 F-15EX Lot 1 aircraft)"),
```
Replace `COVERAGE_NOTES[2]` (:75):

```python
    "Historical procurement line numbers change between editions. Each legacy line is matched within its own budget edition, without asserting a modern-program or aircraft-variant allocation.",
```
with:

```python
    "Historical procurement line numbers change between editions. Each legacy line is matched within its own budget edition, without asserting a modern-program or aircraft-variant allocation, except where a budget book states one (F015E0).",
```
Replace the end of `COVERAGE_NOTES` (:78–79):

```python
    "Missing workbook figures are not zero spending. Some current-year columns contain requests adjusted for continuing resolutions rather than final enacted appropriations.",
]
```
with:

```python
    "Missing workbook figures are not zero spending. Some current-year columns contain requests adjusted for continuing resolutions rather than final enacted appropriations.",
    "The totals exclude classified funding and military construction.",
]
```
After `_json_bytes` (:82–83):

```python
def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
```
add:

```python


def check_program_notes(programs, registry) -> None:
    """A program note ships only with the reviewed narrative receipt it quotes."""
    for program in programs:
        if "note" not in program and "note_fact_id" not in program:
            continue
        fid = program.get("note_fact_id")
        expected = NOTE_RECEIPTS.get(fid)
        citation = registry.get(fid) if fid else None
        if (not program.get("note") or expected is None or citation is None
                or any(citation.get(key) != value for key, value in expected.items())):
            raise ValueError(f"F-15 program note receipt mismatch: {program['code']}/{fid}")
```
In `export_f15_funding_history`, replace (:351–352 before this task's insertions):

```python
        registry_path = json_dir / "citations.json"
        registry = json.loads(registry_path.read_text())
```
with:

```python
        registry_path = json_dir / "citations.json"
        registry = json.loads(registry_path.read_text())
        check_program_notes(PROGRAMS, registry)
```

- [ ] **Step 5: Run the Python tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uv run --project . pytest tests/test_f15_funding_history.py -q`
Expected: `33 passed` (30 existing + 3 new).

- [ ] **Step 6: Write the failing site tests**

Create `site/src/__tests__/family-funding-history-note.test.tsx`:

```tsx
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { parse } from "node-html-parser";
import { FamilyFundingHistory } from "@/components/family-funding-history";
import { CitationPanelContext } from "@/components/cite";
import { validateFamilyHistoryMatrix, type FamilyFundingHistoryData, type FamilyFundingHistoryView, type FamilyFundingProgram } from "@/lib/family-funding-history";
import { checkFamilyHistoryNotes } from "../../scripts/gates/family-history.mjs";

// Spec §6.5 (S5): the strings the owner signed off, on a hermetic one-year history.
const NOTE = "This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four operationally representative test aircraft and two operational aircraft were purchased with procurement funds (F015E0, Line #3 [line 3 of the PB2020–21 P-1 (line 4 in PB2022)])).";
const NOTE_FID = "e7d5bcfb4a30f458";
const ANNUAL = "a".repeat(16);
const CELL = "b".repeat(16);
const noted: FamilyFundingProgram = { id: "P-1:3010F:AF:F015E0", code: "F015E0", title: "F-15e (FY2020 F-15EX Lot 1 aircraft)", program_slug: null, exhibit: "P-1", account: "3010F", organization: "AF", note: NOTE, note_fact_id: NOTE_FID };
const plain: FamilyFundingProgram = { id: "P-1:3010F:AF:F01500", code: "F01500", title: "F-15", program_slug: "F01500", exhibit: "P-1", account: "3010F", organization: "AF" };
const citations = { [NOTE_FID]: { kind: "jbook_narrative", page_number: 71 } };

function view(programs: FamilyFundingProgram[] = [noted, plain]): FamilyFundingHistoryView {
  return {
    schema_version: 1, family_id: "f-15", units: "USD thousands", basis: "toa", start_fy: 2020, end_fy: 2020,
    scope_note: "Scope.", coverage_notes: ["Coverage."], default_point_ids: ["fy2020a"], programs,
    cumulative: { start_fy: 2020, end_fy: 2020, kind: "actuals", measure: "actuals", amount_thousands: 621100, fact_id: ANNUAL, point_ids: ["fy2020a"], scope_note: "Sum." },
    points: [{
      id: "fy2020a", fy: 2020, edition: 2022, kind: "actuals", measure: "actuals", measure_label: "Recorded actuals",
      amount_thousands: 621100, fact_id: ANNUAL, coverage: "covered-records", missing_programs: [], component_count: 1,
      program_cells: [{ program_id: noted.id, amount_thousands: 621100, fact_id: CELL, measure: "actuals", dataset: "budget_lines_decade", input_fact_ids: [CELL] }],
    }],
  };
}

afterEach(() => cleanup());

describe("F-15 budget-line notes (spec §6.5)", () => {
  it("quotes the F015E0 sentence once, as cited source text, beside its narrative receipt", () => {
    Element.prototype.scrollIntoView = vi.fn();
    const openPanel = vi.fn();
    render(<CitationPanelContext.Provider value={{ openPanel }}><FamilyFundingHistory history={view()} shortName="F-15" /></CitationPanelContext.Provider>);
    const notes = document.querySelectorAll("[data-history-note]");
    expect(notes).toHaveLength(1);
    expect(notes[0]).toHaveAttribute("id", "history-note-F015E0");
    const quote = notes[0].querySelector(`[data-source-text="narrative"][data-cite-fact-id="${NOTE_FID}"]`);
    expect(quote?.textContent).toBe(`“${NOTE}”`);
    expect(notes[0].querySelector("[data-amount]")).toBeNull();
    fireEvent.click(notes[0].querySelector(`[data-narrative-chip][data-fact-id="${NOTE_FID}"]`)!);
    expect(openPanel).toHaveBeenCalledWith(NOTE_FID);
    expect(document.querySelector('[data-history-program="P-1:3010F:AF:F015E0"] [data-history-note-ref="F015E0"]')).toHaveAttribute("href", "#history-note-F015E0");
    expect(document.querySelector('[data-history-program="P-1:3010F:AF:F01500"] [data-history-note-ref]')).toBeNull();
    expect(screen.getByRole("rowheader", { name: /F-15e \(FY2020 F-15EX Lot 1 aircraft\)/ })).toBeInTheDocument();
  });

  it("renders no note list when no program carries a note", () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(<FamilyFundingHistory history={view([plain])} shortName="F-15" />);
    expect(document.querySelector("[data-history-note]")).toBeNull();
    expect(screen.queryByRole("list", { name: "Budget-line notes" })).toBeNull();
  });

  it("release gate accepts the rendered note and rejects each kind of drift", () => {
    const html = renderToStaticMarkup(<FamilyFundingHistory history={view()} shortName="F-15" />);
    expect(checkFamilyHistoryNotes(parse(html), view(), citations)).toEqual([]);
    expect(checkFamilyHistoryNotes(parse(html.replace("Lot 1 which", "Lot 1, which")), view(), citations)).toContain("program F015E0 rendered note differs from its export");
    expect(checkFamilyHistoryNotes(parse(html), view(), { [NOTE_FID]: { kind: "workbook" } })).toContain("program F015E0 note lacks a narrative receipt");
    const noChip = parse(html);
    noChip.querySelector("[data-narrative-chip]")!.remove();
    expect(checkFamilyHistoryNotes(noChip, view(), citations)).toContain("program F015E0 note is not rendered with its source chip");
    const noRef = parse(html);
    noRef.querySelector("[data-history-note-ref]")!.remove();
    expect(checkFamilyHistoryNotes(noRef, view(), citations)).toContain("program F015E0 row does not point to its note");
    expect(checkFamilyHistoryNotes(parse(renderToStaticMarkup(<FamilyFundingHistory history={view([plain])} shortName="F-15" />)), view(), citations)).toContain("family notes: 0 rendered for 1 noted program(s)");
  });

  it("the loader rejects a note without its receipt id", () => {
    const data = {
      ...view(),
      points: view().points.map(point => ({ ...point, components: [{ fact_id: CELL, program_id: noted.id, amount_thousands: 621100 }] })),
    } as unknown as FamilyFundingHistoryData;
    expect(() => validateFamilyHistoryMatrix(data)).not.toThrow();
    const broken = structuredClone(data);
    delete broken.programs[0].note_fact_id;
    expect(() => validateFamilyHistoryMatrix(broken)).toThrow("Invalid family program note: F015E0");
  });
});
```

- [ ] **Step 7: Run it to verify it fails**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run src/__tests__/family-funding-history-note.test.tsx`
Expected: `Tests  3 failed | 1 passed (4)` — "quotes the F015E0 sentence…" fails `expected … to have a length of 1 but got +0`, the gate test fails `TypeError: (0 , checkFamilyHistoryNotes) is not a function`, the loader test fails `expected [Function] to throw an error`; only "renders no note list…" passes. (Measured on a copy of this site tree.)

- [ ] **Step 8: Implement the type, the loader guard, the row and the note list**

`site/src/lib/family-funding-history.ts`, replace (:27–30):

```ts
  account: string;
  organization: string;
}

export interface FamilyFundingCell {
```
with:

```ts
  account: string;
  organization: string;
  /** A budget book's own sentence about this line, quoted verbatim ([brackets] gloss it); always paired with note_fact_id. */
  note?: string;
  /** The jbook_narrative receipt for `note`: the page that prints the sentence. */
  note_fact_id?: string;
}

export interface FamilyFundingCell {
```
and after (:138):

```ts
  if (programs.size !== history.programs.length) throw new Error("Duplicate family program identity");
```
insert:

```ts
  for (const program of history.programs) {
    const hasNote = program.note !== undefined, hasReceipt = program.note_fact_id !== undefined;
    if (hasNote !== hasReceipt || (hasNote && (!program.note!.trim() || !/^[0-9a-f]{16}$/.test(program.note_fact_id!)))) {
      throw new Error(`Invalid family program note: ${program.code}`);
    }
  }
```

`site/src/components/family-funding-history.tsx`: after `import { Cite } from "@/components/cite";` (:5) add

```tsx
import { NarrativeSourceChip } from "@/components/narrative-chip";
```
replace (:22–23)

```tsx
  const total = history.cumulative;
  const tableRef = useRef<HTMLDivElement>(null);
```
with

```tsx
  const total = history.cumulative;
  const noted = history.programs.filter(program => program.note);
  const tableRef = useRef<HTMLDivElement>(null);
```
replace (:86–87)

```tsx
                <span className={styles.rowMeta}>{program.exhibit === "R-1" ? "Development" : "Procurement"}{!program.program_slug ? " · Historical code" : ""}</span>
              </th>
```
with

```tsx
                <span className={styles.rowMeta}>{program.exhibit === "R-1" ? "Development" : "Procurement"}{!program.program_slug ? " · Historical code" : ""}</span>
                {program.note && <a className={styles.noteRef} href={`#history-note-${program.code}`} data-history-note-ref={program.code}>Note below</a>}
              </th>
```
and after the `matrixNote` paragraph (:103)

```tsx
      <p className={styles.matrixNote}>Rows follow the government’s PE or budget-line code across editions. Historical F0150P and F015E0 remain separate. Missing EPAWSS development figures in FY2025–2026 are excluded from those totals.</p>
```
insert

```tsx
      {noted.length > 0 && <ul className={styles.programNotes} aria-label="Budget-line notes">
        {noted.map(program => <li key={program.id} id={`history-note-${program.code}`} data-history-note={program.code}>
          <span className={styles.programCode}>{program.exhibit === "R-1" ? "PE" : "BLI"} {program.code}</span>
          <span className={styles.noteQuote} data-source-text="narrative" data-cite-fact-id={program.note_fact_id}>“{program.note}”</span>
          {program.note_fact_id && <NarrativeSourceChip factId={program.note_fact_id} />}
        </li>)}
      </ul>}
```
The quote carries `data-source-text="narrative"` (a classified kind, `site/scripts/gates/source-text-kinds.mjs`) and the citation anchor render-static (a0) requires (`data-cite-fact-id`, `render-static.mjs:621-653`); it holds no `[data-amount]`. The full note sits under the matrix rather than in the sticky 164–232px row header, which would turn the row into a column of text on a phone.

`site/src/components/family-funding-history.module.css`, append after :82:

```css
.noteRef{display:inline-block;margin-top:4px;font:var(--type-ui);color:var(--ink);text-underline-offset:3px}
.noteRef:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.programNotes{list-style:none;margin:10px 0 0;padding:0;max-width:110ch;font:var(--type-ui);line-height:1.5;color:var(--muted-ink)}
.programNotes li+li{margin-top:8px}
.programNotes .programCode{display:inline;margin:0 6px 0 0}
.noteQuote{color:var(--ink)}
```

`site/scripts/gates/family-history.mjs`, replace the end of `checkFamilyHistory` (:121–127):

```js
  const clone = root.querySelector("[data-family-history]")?.clone();
  if (clone) {
    for (const a of clone.querySelectorAll("[data-amount]")) a.remove();
    check(!/\$[\d,]+(\.\d+)?\s*[TBMK]?\b/.test(clone.text), "family history has currency outside a cited figure");
  }
  return errors;
}
```
with:

```js
  const clone = root.querySelector("[data-family-history]")?.clone();
  if (clone) {
    for (const a of clone.querySelectorAll("[data-amount]")) a.remove();
    check(!/\$[\d,]+(\.\d+)?\s*[TBMK]?\b/.test(clone.text), "family history has currency outside a cited figure");
  }
  errors.push(...checkFamilyHistoryNotes(root, history, citations));
  return errors;
}

/**
 * A program note is a budget book's own sentence (spec §6.5): it renders once,
 * quoted verbatim as cited source text, beside the narrative receipt that
 * prints it, and its matrix row points to it.
 */
export function checkFamilyHistoryNotes(root, history, citations) {
  const errors = [];
  const squash = text => String(text ?? "").replace(/\s+/g, " ").trim();
  const noted = history.programs.filter(program => program.note !== undefined || program.note_fact_id !== undefined);
  const rendered = root.querySelectorAll("[data-history-note]");
  if (rendered.length !== noted.length) errors.push(`family notes: ${rendered.length} rendered for ${noted.length} noted program(s)`);
  for (const program of noted) {
    if (!program.note || citations[program.note_fact_id]?.kind !== "jbook_narrative") {
      errors.push(`program ${program.code} note lacks a narrative receipt`);
      continue;
    }
    const el = root.querySelector(`[data-history-note="${program.code}"]`);
    const quote = el?.querySelector(`[data-source-text="narrative"][data-cite-fact-id="${program.note_fact_id}"]`);
    if (!el || !quote || !el.querySelector(`[data-narrative-chip][data-fact-id="${program.note_fact_id}"]`)) {
      errors.push(`program ${program.code} note is not rendered with its source chip`);
      continue;
    }
    if (squash(quote.text) !== squash(`“${program.note}”`)) errors.push(`program ${program.code} rendered note differs from its export`);
    if (!root.querySelector(`[data-history-program="${program.id}"] [data-history-note-ref="${program.code}"]`)) errors.push(`program ${program.code} row does not point to its note`);
  }
  return errors;
}
```
`checkFamilyHistory` is what program-skeleton leg (p) runs on the built `/families/f-15/` (`program-skeleton.mjs:4178-4196`), so the note is gated on every build.

- [ ] **Step 9: Run the site tests and lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run src/__tests__/family-funding-history-note.test.tsx && npx eslint src/components/family-funding-history.tsx src/lib/family-funding-history.ts src/__tests__/family-funding-history-note.test.tsx scripts/gates/family-history.mjs`
Expected: `Tests  4 passed (4)`; eslint prints nothing. (Prototyped 2026-10-02 on a copy of this exact site tree: 4/4 pass, eslint clean, `tsc --noEmit` reports nothing in the touched files, and the existing `family-funding-history.test.tsx` + `-gate.test.tsx` stay green on today's data, which carries no note.)

This step runs while the worktree's `data/site` still links to the main lake, which does not ship `p1_era_line_map` until the release, and Task 19 Part C made `site/src/app/data/page.tsx` throw at module level on such an export. No test here imports that page:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && grep -rlE "(from|import\()\s*[\"'][^\"']*app/data/page" src scripts || echo "no test imports the /data/ page"
```
Expected: `no test imports the /data/ page` (measured 2026-10-02 on the base tree: no file under `src/` or `scripts/` imports it; Task 19's new tests do not either). If a file is listed, first point `data/{site,duckdb,parquet}` at `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s4-B/{site,duckdb,parquet}` (Task 21 Step 21's `ln -sfn` loop), run the vitest command, and restore the links (Task 21 Step 21's restore block).

- [ ] **Step 10: Commit the code**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/f15_funding_history.py GovBudget/tests/test_f15_funding_history.py GovBudget/site/src/lib/family-funding-history.ts GovBudget/site/src/components/family-funding-history.tsx GovBudget/site/src/components/family-funding-history.module.css GovBudget/site/scripts/gates/family-history.mjs GovBudget/site/src/__tests__/family-funding-history-note.test.tsx && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(f15): F015E0 is the FY2020 F-15EX Lot 1 line — cited note, coverage exclusions (spec §6.5, owner sign-off)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
(The pins are still S0's; Steps 11–18 re-pin before anything is built from this code for release.)

- [ ] **Step 11: Write the S5 expected-diff rule list**

Task 3's `--expect` format (a JSON list of rules; Task 21 Step 7 explains it). S5 may change exactly one file, and must change it. Create `docs/superpowers/plans/2026-10-02-era-procurement-history-expected-diff-s5.json`:

```json
[
  {"path": "json/f15_funding_history.json", "status": ["changed"], "required": true,
   "why": "§6.5 (S5): the F015E0 retitle, its note and note_fact_id, and the two coverage-note changes — Step 14 proves the change is exactly these"}
]
```
Anything else that differs FAILS the diff — citations, cite shards, breakdowns, workbook cells, the manifest, `site_meta.json`. Re-running the F-15 builder on an export it already wrote rewrites `json/datasets.json` with byte differences but an equal JSON value, which the diff counts as `equivalent`, not as a difference (measured read-only 2026-10-02: the builder re-run on an APFS clone of the live export changed only `datasets.json`'s bytes; `proof diff` reported `identical 35,519 · equivalent 1 · changed 0`).

- [ ] **Step 12: Produce the S5 history on a clone of the S4 export**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && cp -c -R "$P/s4-B" "$P/s5" && (source "$P/s4/env.sh" "$P/s5" && echo "$GOVBUDGET_DATA" && uv run --project . python scripts/export_f15_funding_history.py --duckdb "$P/s5/duckdb/govbudget.duckdb" --out-dir "$P/s5/site")
```
Expected: `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s5`, then one JSON line with `"added_citations": 0`, `"annual_points": 30`, `"citations": <N_B>` (Task 21 Step 15), `"cumulative_actuals_thousands": 17043321.0`, `"source_facts": 207` (the totals do not move). The clone's DuckDB views keep reading `.proofs/s4/parquet` (pinned).

- [ ] **Step 13: Diff S4 against S5 at file level**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && uv run --project . python -m govbudget proof diff "$P/s4-B/site" "$P/s5/site" --expect docs/superpowers/plans/2026-10-02-era-procurement-history-expected-diff-s5.json --report "$P/s4-logs/s5-diff-report.json" > "$P/s4-logs/s5-diff.txt" 2>&1; echo "exit=$?"; tail -6 "$P/s4-logs/s5-diff.txt"
```
Expected: `exit=0`; the counts line ends `changed 1 · only in A 0 · only in B 0` (`equivalent` 0 or 1, see Step 11); `rule 0 [json/f15_funding_history.json] matched <k>: …`; last line `proof diff: PASS`.

- [ ] **Step 14: Check the history diff equals exactly the approved changes**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && uv run --project . python - "$P/s4-B/site/json/f15_funding_history.json" "$P/s5/site/json/f15_funding_history.json" <<'PY'
import json, sys
a, b = (json.load(open(path)) for path in sys.argv[1:3])
LABEL = "F-15e (FY2020 F-15EX Lot 1 aircraft)"
NOTE = ("This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 "
        "(two test aircraft were purchased with RDT&E funds (PE 0207134F); four operationally representative test "
        "aircraft and two operational aircraft were purchased with procurement funds (F015E0, Line #3 "
        "[line 3 of the PB2020–21 P-1 (line 4 in PB2022)])).")
OLD2 = ("Historical procurement line numbers change between editions. Each legacy line is matched within its own "
        "budget edition, without asserting a modern-program or aircraft-variant allocation.")
NEW2 = OLD2[:-1] + ", except where a budget book states one (F015E0)."
ADDED = "The totals exclude classified funding and military construction."
expected = json.loads(json.dumps(a))
(f015e0,) = [p for p in expected["programs"] if p["code"] == "F015E0"]
assert f015e0["title"] == "F-15e (legacy line)" and "note" not in f015e0
f015e0.update(title=LABEL, note=NOTE, note_fact_id="e7d5bcfb4a30f458")
assert expected["coverage_notes"][2] == OLD2 and len(expected["coverage_notes"]) == 6
expected["coverage_notes"][2] = NEW2
expected["coverage_notes"].append(ADDED)
assert expected == b, "S5 diff is not exactly the approved changes"
print("S5 diff: exactly the retitle, the two note fields and the two coverage-note changes")
PY
```
Expected: `S5 diff: exactly the retitle, the two note fields and the two coverage-note changes`.

- [ ] **Step 15: Re-pin V4(f) and V5 from the S5 state**

Task 4's capture script refuses unless the shipped history's sha256 equals `--expect-sha256`, so pass the digest of the history Step 14 just approved; it writes `history.sha256` in Task 4's format (64 lowercase hex characters and a newline):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && SHA=$(shasum -a 256 "$P/s5/site/json/f15_funding_history.json" | cut -d' ' -f1) && echo "S5 history sha256 $SHA" && uv run --project . python scripts/era/capture_f15_fixtures.py --site-dir "$P/s5/site" --duckdb "$P/s5/duckdb/govbudget.duckdb" --out-dir tests/fixtures/f15 --expect-sha256 "$SHA" && test "$(cat tests/fixtures/f15/history.sha256)" = "$SHA" && echo "pin = S5 history" && git diff --stat -- tests/fixtures/f15 && uv run --project . pytest tests/test_f15_era_identity.py tests/test_f15_funding_history.py -q && (source "$P/s4/env.sh" "$P/s5" && uv run --project . python -m govbudget verify-era-map --legs f) > "$P/s4-logs/s5-verify-era-map-f.log" 2>&1; echo "verify exit=$?"; tail -1 "$P/s4-logs/s5-verify-era-map-f.log"
```
Expected: `S5 history sha256 <64 hex>` (not `9f70c770…`); the capture's JSON line with `"history_sha256": "<the same hex>"`, `"source_rows": 467`, `"series": 195`, `"previews": 207`, `"current_fact_ids": 20`; `pin = S5 history`; the diff stat lists `history.json`, `history.sha256`, `builder_inputs.json.gz`; all tests pass; `verify exit=0` and `verify-era-map: PASS`. A capture refusal (`capture_f15_fixtures: …`) writes nothing: stop and read its message.

- [ ] **Step 16: Build the site on the S5 export, re-snapshot the F-15 page, run the gates**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && for d in site duckdb parquet; do ln -sfn "$P/s5/$d" "data/$d"; done && ls -l data | grep -- '->' && ls dbt/target/manifest.json && cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > "$P/s4-logs/s5-site-build.log" 2>&1; echo "build exit=$?"; node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --out ../tests/fixtures/f15/page_snapshot.json && cd .. && git diff -- tests/fixtures/f15/page_snapshot.json | head -80
```
Expected: three symlinks into `.proofs/s5`; `build exit=0`; `f15-page-snapshot: wrote ../tests/fixtures/f15/page_snapshot.json (<e> data-fact-id elements, <d> distinct page fact ids, 8 matrix rows)`. Read the snapshot diff: it must show only (1) the F015E0 row title `F-15e (FY2020 F-15EX Lot 1 aircraft)`, (2) that row's `Note below` link, (3) the new `Budget-line notes` list with the quoted sentence and its `source` chip for `e7d5bcfb4a30f458`, (4) coverage note 3's new ending and the new last coverage note. Anything else: stop and explain before Step 17.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && npm test > "$P/s4-logs/s5-vitest.log" 2>&1; echo "vitest exit=$?"; tail -4 "$P/s4-logs/s5-vitest.log"; NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > "$P/s4-logs/s5-site-verify.log" 2>&1; echo "verify exit=$?"; grep -E "program-skeleton|page weight|^overall:" "$P/s4-logs/s5-site-verify.log" | tail -12
```
Expected: `vitest exit=0` (`npm test` runs both vitest configs; the real-data F-15 suites now read the S5 history: 8 program rows, 67 cells, the gate test runs `checkFamilyHistoryNotes` on one note; every suite that reads `data/site` sees an export that ships `p1_era_line_map`); `verify exit=0`, leg p's `family history sums … checked ✓`, `overall: PASS`.

- [ ] **Step 17: Re-measure the F-15 page weight and re-stamp it**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && node -e 'const fs=require("fs"),z=require("zlib");const b=fs.readFileSync("out/families/f-15/index.html");console.log(b.length.toLocaleString("en-US")+" / "+z.gzipSync(b,{level:9}).length.toLocaleString("en-US"))'
```
Expected: `<raw> / <gzip>` within `725,000 / 70,000` (2,243 gzip of headroom was measured on 2026-09-25; the change adds one short row link, ~460 characters of note and ~100 of coverage text, each also carried once in the RSC payload). If gzip exceeds 70,000: stop and take it to the owner (never raise the ceiling, never trim existing disclosures without the owner). In `site/scripts/gates/build.mjs` replace the entry line (:254)

```js
  { label: "/families/f-15/", file: "families/f-15/index.html", maxRaw: 725_000, maxGzip: 70_000, measured: "701,316 / 67,757" },
```
with (filling the printed numbers and the short HEAD sha the build used):

```js
  // RE-MEASURED <YYYY-MM-DD> (families piece 1, S5: the F015E0 label, its
  // cited Lot 1 note and two coverage notes; build of <short sha> plus the
  // S5 working tree on the S5 proof export, this file's own weigh() —
  // zlib level 9): 701,316 / 67,757 -> <raw> / <gzip>. CEILINGS UNCHANGED;
  // <725,000 − raw> raw / <70,000 − gzip> gzip left.
  { label: "/families/f-15/", file: "families/f-15/index.html", maxRaw: 725_000, maxGzip: 70_000, measured: "<raw> / <gzip>" },
```

- [ ] **Step 18: Restore the data links**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && git checkout -- site/public/llms.txt && for d in site duckdb parquet; do ln -sfn "/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/$d" "data/$d"; done && git -C .. status --porcelain -- GovBudget | grep -v '^??'
```
Expected: only the re-pins and `build.mjs` are listed as modified (`tests/fixtures/f15/*`, `site/scripts/gates/build.mjs`), plus the S5 expected-diff file as untracked (`??`, filtered here).

- [ ] **Step 19: Record the sign-off in the ROADMAP**

In `docs/superpowers/ROADMAP.md`, at the end of the "F-15 family funding correction (2026-09-24)" paragraph (it ends `…recorded in the [family history record](plans/2026-09-24-f15-funding-history.md).`), append:

```markdown
**F015E0 correction (<YYYY-MM-DD>, families piece 1 S5):** the owner signed off
(<owner's reply, verbatim>) relabeling F015E0 "F-15e (FY2020 F-15EX Lot 1
aircraft)" and quoting the PB2026 F-15EX P-40 sentence (AF Aircraft Procurement
Vol I, p.71, receipt `e7d5bcfb4a30f458`) that says its procurement funds bought
four operationally representative test aircraft and two operational aircraft of
Lot 1 in FY2020; the coverage notes now say the totals exclude classified
funding and military construction and that F015E0 is the one legacy line with a
stated allocation. Totals unchanged; the history's sha256 is re-pinned
(`tests/fixtures/f15/history.sha256`).
```

- [ ] **Step 20: Commit the re-pins**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/tests/fixtures/f15/history.json GovBudget/tests/fixtures/f15/history.sha256 GovBudget/tests/fixtures/f15/builder_inputs.json.gz GovBudget/tests/fixtures/f15/page_snapshot.json GovBudget/site/scripts/gates/build.mjs GovBudget/docs/superpowers/plans/2026-10-02-era-procurement-history-expected-diff-s5.json GovBudget/docs/superpowers/ROADMAP.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(f15): re-pin history sha, V5 fixtures and page snapshot for the S5 correction; re-measure /families/f-15/" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
