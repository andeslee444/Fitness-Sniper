<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G2 (2026-10-13). -->

### Task 12: The O&M page — printed code, "O&M" badge, the restated RDT&E line, the map scope, and the receipt matcher accepts the alias (#194)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §4.6 (`/program/0390DOM/` is rollup tier, cited to workbook cells only; the sidecar gains `printed_code: "O&M"` and `exhibit_family: "om"` for alias keys only, read from the seed; `deriveExhibitFamily` honours the hint; the header shows the code as printed with the sentence "The P-1 prints this line's code as O&M; its address uses 0390DOM because a web address cannot carry “&”."; under Q1 (a) a second sentence "The P-1's Chem Demilitarization - RDT&E line restates R-1 program elements 0708081D and 0708083D, whose pages carry those dollars.", both PEs code-linked; the badge reads "O&M" while the term beside the code stays "BLI"; no `search_aliases.csv` row, no /years/ row, no `search_quick.json` document; the `program-skeleton.mjs` census comment "2 route-unsafe" is updated), §4.5 "Scope string" (the `p1_era_line_map` scope moves the clause to a `program_key` entry, approved with Q3), §2.3 cross-review (the v2 receipt matcher accepts a citation `pe_bli` that is the route-safe key of the row's printed code; without it every 0390DOM workbook citation stops the export). Owner decisions 2026-10-04: Q2, Q3 (with its scope string), Q5 (the strings and the badge/term pair), Q6 (the $3,243K FY2026 request counts in the /programs/ universe and the flow chart: nothing to change here, the line is a P-1 row of a procurement-title account).

**Files:**
- Modify: `src/govbudget/export_site.py` — the `p1_era_line_map` entry of `_DATASET_SCOPES` and the comment above it (anchor on `# Programs lines S1b loaded under 9999999999 are not in it.`, about lines 1779–1787); a new `_route_safe_page_fields` before `def decade_only_page_pes(` (about line 6986); the rollup sidecar dict (anchor on `"trajectory_fact_ids": _trajectory_fact_ids(pe_bli, traj),\n        }`, about line 13655)
- Modify: `src/govbudget/program_pdf_receipts.py` — a new `program_code_matches` before `def matched_amount(` (about line 141); the code check in `export_program_pdf_receipts` (about lines 350–351)
- Modify: `site/scripts/gates/program-skeleton.mjs` — the `MIN_DECADE_ONLY_PAGES` comment (about lines 3312–3318)
- Modify: `site/src/lib/data.ts` — the end of `interface ProgramDetails` (anchor on `  exhibit_family?: string | null;\n}`, about lines 1551–1558)
- Modify: `site/src/lib/program-tier.ts` — `rollupProgramRow`'s `exhibit_family` (about line 420)
- Modify: `site/src/lib/copy.ts` — `peBliKind` (about lines 75–78); `COPY.program.rollupBadgeTitle` (about line 455)
- Modify: `site/src/components/program-header.tsx` — imports (lines 1–5); the end of `ProgramHeaderProps`; the destructuring at the top of `ProgramHeader`; the PE/BLI label and code (about lines 262–273)
- Modify: `site/src/app/program/[peBli]/page.tsx` — the `copy` import (about line 106); the `<ProgramHeader … />` props (about lines 760–767); `<ProgramWayfinding … />` (about line 794)
- Create: `tests/test_export_route_safe_page.py`
- Create: `site/src/__tests__/program-header-printed-code.test.tsx`
- Test: `tests/test_export_era_line_map.py` (`test_scope_names_both_meanings_of_pe_bli_and_carries_no_money`, about lines 57–64); `tests/test_program_pdf_receipts.py` (the import block; append at the end); `tests/jbooks/test_export_site_5f.py` (a new test before `def test_full_tier_sidecar_shape_unchanged`, about line 356); `site/src/lib/__tests__/program-tier.test.ts` (inside `describe("rollupProgramRow"`); `site/src/lib/__tests__/copy.test.ts` (the import line; append at the end)

**Interfaces:**
Consumes: Task 6 (`route_safe_codes.by_page_key`, `page_key`, `restated_lines`; the seed row's `exhibit_family` `om`); Task 8 (`p1_era_line_map.program_key` = `0390DOM` for the era O&M rows; the decade tier publishes their citations under `0390DOM`); Task 7 + Task 22 (the live rows: PB2024–PB2026 `budget_lines` rows with `pe_bli` `0390DOM`, so the exporter's rollup universe — the PB2026 `budget_lines` keys not in `programs.json` — contains `0390DOM`); Task 10 (B7: the page's era decade points).
Produces (Tasks 21 and 22 measure and check them):
- `export_site._route_safe_page_fields(pe_bli) -> dict`: `{"printed_code", "exhibit_family", "restated_lines"}` for a route-safe page key, `{}` otherwise; the rollup sidecar `json/program_details/0390DOM.json` carries `"printed_code": "O&M"`, `"exhibit_family": "om"`, `"restated_lines": [{"line_item_code": "RDT&E", "title": "Chem Demilitarization - RDT&E", "program_elements": ["0708081D", "0708083D"]}]`; no other sidecar gains a key.
- `datasets.json` → `p1_era_line_map` scope: "… line_item_code (the budget line code printed on it), program_key (the pe_bli a same_program line's era citations carry; the printed code except 0390DOM for 0390D's O&M line, whose "&" cannot appear in a web address) and the dated owner decision …" (P2 in Task 21: a code-change difference).
- `program_pdf_receipts.program_code_matches(cited, row) -> bool` (the citation's `pe_bli` is the row's printed code or that code's page key under the row's account; a missing `pe_bli` matches).
- Site: `ProgramDetails.printed_code?: string`, `ProgramDetails.restated_lines?: RestatedLine[]`, `interface RestatedLine {line_item_code; title; program_elements}`; `rollupProgramRow` prefers `details.exhibit_family`; `peBliKind("om") === "BLI"`; `COPY.program.printedCodeNote(printed, key)`, `COPY.program.restatedLineLead(title)`, `COPY.program.restatedLineTail`; `ProgramHeader` props `printedCode?: string | null`, `restatedLines?: readonly RestatedLine[]`, rendering `[data-printed-code]` (the code element), `[data-printed-code-note]` and `[data-restated-line="<code>"]`; the program page's wayfinding names the printed code and the BLI term.

Measured for this task (2026-10-13):
- No sidecar or `programs.json` row carries `exhibit_family` `om` today (`programs.json`: 1,077 `rdte`, 861 `procurement`; sidecars: 464 decade `rdte`, 89 decade `procurement`, 71 rollup without the key, 1,938 full without it); `copy.ts` `exhibitFamilyLabel("om")` and the header's own `exhibitFamilyLabel` already print "O&M", and `what-it-is.ts` `answerFamilyPlain("om")` prints "operations & maintenance". `peBliKind` and the header's term read `exhibit_family === "procurement"`, so an `om` row would print "PE": this task makes it "BLI".
- `/program/0708081D/` (rollup) and `/program/0708083D/` (full tier, in `programs.json`) exist today (`data/site/json/program_details/0708081D.json`, `…/0708083D.json`).
- `program_pdf_receipts.py:350-351` raises `Source program code differs` when a workbook citation's `pe_bli` is not the cell row's printed code (column I of the P-1); a 0390DOM citation's row prints `O&M`.
- The /data/ page renders the `p1_era_line_map` scope three times (once in the HTML table, twice in the RSC payload). Substituting the amended scope into today's built `site/out/data/index.html` (85,358 / 14,500 by Python `zlib` level 9, gzip container; the gate stamp reads 85,358 / 14,530) gives 85,725 / 14,712: +367 raw, +212 gzip (Step 12's script; the RSC copies' escaping of the quoted "&" is approximated), against 19,642 raw / 1,070 gzip of headroom under 105,000 / 15,600. /downloads/ (no ceiling, the scope only in its RSC payload) grows by about +357 / +128. Task 21 re-measures both on the release build and re-stamps; no ceiling moves.
- `decade_only_page_pes`' census on the live lake: `{'candidates': 3771, 'has_page': 1994, 'era_key': 1214, 'route_unsafe': 2, 'no_positive_grain': 8, 'edition_gap': 0}` → 553 pages; the two route-unsafe keys are 0390D's stale `O&M` and `RDT&E` decade keys.
- On a scratch tree with this task's edits: `tests/test_export_route_safe_page.py` 2 passed, `tests/test_program_pdf_receipts.py` 50 (42 + 8), `tests/test_export_era_line_map.py` 13 (Task 9a's `test_ships_each_decisions_date` included, which runs before this task), `tests/jbooks/test_export_site_5f.py` 13 (12 + 1, Postgres); vitest `src/lib/__tests__/program-tier.test.ts`, `src/lib/__tests__/copy.test.ts`, `src/__tests__/program-header-badge.test.tsx`, `src/__tests__/program-header-printed-code.test.tsx` and `src/__tests__/program-header-account.test.tsx`: 62 passed (5 files); `tsc --noEmit` reported nothing in the edited files.

- [ ] **Step 1: Write the failing Python tests**

Create `tests/test_export_route_safe_page.py`:

```python
"""export_site._route_safe_page_fields (families piece-1 follow-ups design
§4.6, #194; owner Q1 (a), Q2, Q5): the sidecar of a page keyed by a
route-safe page key names the code its P-1 prints, the seed's exhibit
family and the restated R-1 line of its account; every other page gets
nothing."""
from govbudget.export_site import _route_safe_page_fields


def test_the_o_and_m_page_names_its_printed_code_and_the_restated_line():
    assert _route_safe_page_fields("0390DOM") == {
        "printed_code": "O&M",
        "exhibit_family": "om",
        "restated_lines": [{
            "line_item_code": "RDT&E",
            "title": "Chem Demilitarization - RDT&E",
            "program_elements": ["0708081D", "0708083D"],
        }],
    }


def test_every_other_page_gets_nothing():
    for pe in ("0708081D", "0708083D", "O&M", "RDT&E", "F015EX", "0390D"):
        assert _route_safe_page_fields(pe) == {}
```

In `tests/test_export_era_line_map.py` (`test_scope_names_both_meanings_of_pe_bli_and_carries_no_money`), replace:

```python
    assert ("line_item_code (the budget line code printed on it, the pe_bli a same_program"
            " line's era citations carry)") in scope
```

with:

```python
    # #194 (owner Q3, 2026-10-04): the printed code and the pe_bli era
    # citations carry part only for 0390D's O&M line (program key 0390DOM).
    assert ("line_item_code (the budget line code printed on it), program_key (the pe_bli"
            " a same_program line's era citations carry; the printed code except 0390DOM"
            " for 0390D's O&M line, whose \"&\" cannot appear in a web address)") in scope
```

In `tests/test_program_pdf_receipts.py` (the import block), replace:

```python
from govbudget.program_pdf_receipts import (
    attach_additive_receipts,
    metadata_for_row,
    source_identity,
)
```

with:

```python
from govbudget.program_pdf_receipts import (
    attach_additive_receipts,
    metadata_for_row,
    program_code_matches,
    source_identity,
)
```

Append at the end of `tests/test_program_pdf_receipts.py`:

```python


@pytest.mark.parametrize(("cited", "account", "code", "matches"), [
    ("F015EX", "3010F", "F015EX", True),
    (None, "3010F", "F015EX", True),
    ("", "3010F", "F015EX", True),
    ("F015E0", "3010F", "F015EX", False),
    # #194: a 0390DOM citation names the row that prints O&M under 0390D
    ("0390DOM", "0390D", "O&M", True),
    ("O&M", "0390D", "O&M", True),
    ("0390DOM", "2035A", "O&M", False),
    ("0390DOM", "0390D", "RDT&E", False),
])
def test_a_citation_names_the_printed_code_or_its_route_safe_key(cited, account, code, matches):
    assert program_code_matches(cited, {"account": account, "code": code}) is matches
```

In `tests/jbooks/test_export_site_5f.py` (a new test before `test_full_tier_sidecar_shape_unchanged`), replace:

```python
def test_full_tier_sidecar_shape_unchanged(pg_dsn, tmp_path):
```

with:

```python
def test_route_safe_alias_sidecar_names_its_printed_code(pg_dsn, tmp_path):
    """#194 (design §4.6, owner Q5): the rollup sidecar of 0390DOM, a P-1
    line printed as 'O&M', carries printed_code, the seed's exhibit_family
    and the restated RDT&E line; an ordinary rollup sidecar carries none."""
    doc_id, sha = _seed_jbook_doc(pg_dsn, pdf_path=FIXTURE_PDF)
    _seed_budget_line(pg_dsn, doc_id, sha)
    _seed_rollup_budget_line(pg_dsn, doc_id)
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, account_title,"
            " organization, budget_activity, budget_activity_title, pe_bli, title,"
            " amount_type, amount_thousands, source_document_id, source_sheet,"
            " source_cells, line_item_code) values ('P-1', 2026, '0390D',"
            " 'Chemical Agents and Munitions Destruction, Defense', 'A', '01',"
            " 'Operation and maintenance', '0390DOM', 'Chem Demilitarization - O&M',"
            " 'fy_2024_actuals', 87404, %s, 'Exhibit P-1', ARRAY['O303'], 'O&M')",
            (doc_id,))
    build_provenance_pages(pg_dsn)
    site = _export(pg_dsn, tmp_path, extend_duckdb=_rollup_marts)
    om = json.loads((site / "json" / "program_details" / "0390DOM.json").read_text())
    assert om["tier"] == "rollup"
    assert (om["printed_code"], om["exhibit_family"]) == ("O&M", "om")
    assert om["restated_lines"] == [{
        "line_item_code": "RDT&E", "title": "Chem Demilitarization - RDT&E",
        "program_elements": ["0708081D", "0708083D"]}]
    other = json.loads((site / "json" / "program_details" / f"{_PE}.json").read_text())
    assert not {"printed_code", "restated_lines", "exhibit_family"} & set(other)


def test_full_tier_sidecar_shape_unchanged(pg_dsn, tmp_path):
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_export_route_safe_page.py tests/test_export_era_line_map.py tests/test_program_pdf_receipts.py tests/jbooks/test_export_site_5f.py -q 2>&1 | tail -5
```

Expected: `2 errors` during collection — `ImportError: cannot import name '_route_safe_page_fields' from 'govbudget.export_site'` and `ImportError: cannot import name 'program_code_matches' from 'govbudget.program_pdf_receipts'`. Without those two files:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_export_era_line_map.py tests/jbooks/test_export_site_5f.py -q 2>&1 | grep -E '^FAILED|passed|failed'
```

Expected: `2 failed`: `test_scope_names_both_meanings_of_pe_bli_and_carries_no_money` (the old clause) and `test_route_safe_alias_sidecar_names_its_printed_code` (`KeyError: 'printed_code'`).

- [ ] **Step 3: The exporter writes the alias page's fields and the amended scope**

In `src/govbudget/export_site.py` (`_DATASET_SCOPES`, about lines 1779–1787), replace:

```python
    # Final review T5: the map holds era keys only, so the 50 era Classified
    # Programs lines S1b loaded under 9999999999 are not in it.
    "p1_era_line_map": (
        "One row per era-keyed PB2017–PB2023 P-1 display line (the Classified"
        " Programs lines, loaded under 9999999999, are not in the map):"
        " era_key (its pe_bli in budget_lines_decade), line_item_code (the"
        " budget line code printed on it, the pe_bli a same_program line's era"
        " citations carry) and the dated owner decision that joins it to a"
        " program page or to history only, or excludes it. Only a same_program"
```

with:

```python
    # Final review T5: the map holds era keys only, so the 50 era Classified
    # Programs lines S1b loaded under 9999999999 are not in it.
    # #194 (owner Q3, 2026-10-04): line_item_code is the code printed on the
    # line and program_key the pe_bli its era citations carry; they differ
    # only for 0390D's O&M line, whose program key is its route-safe page key
    # 0390DOM (dbt/seeds/p1_route_safe_codes.csv), so the scope names both.
    "p1_era_line_map": (
        "One row per era-keyed PB2017–PB2023 P-1 display line (the Classified"
        " Programs lines, loaded under 9999999999, are not in the map):"
        " era_key (its pe_bli in budget_lines_decade), line_item_code (the"
        " budget line code printed on it), program_key (the pe_bli a"
        " same_program line's era citations carry; the printed code except"
        " 0390DOM for 0390D's O&M line, whose \"&\" cannot appear in a web"
        " address) and the dated owner decision that joins it to a"
        " program page or to history only, or excludes it. Only a same_program"
```

and (insert before `decade_only_page_pes`) replace:

```python
def decade_only_page_pes(duckdb_path) -> tuple[list[str], dict[str, int]]:
```

with:

```python
def _route_safe_page_fields(pe_bli: str) -> dict:
    """#194 (families piece-1 follow-ups design §4.6; owner Q1 (a), Q2, Q5).

    The extra sidecar fields of a page keyed by a route-safe page key
    (dbt/seeds/p1_route_safe_codes.csv): the code the P-1 prints, the
    exhibit family the seed row gives, and the P-1 lines of the same account
    that restate R-1 program elements (route_safe_codes.P1_R1_RESTATEMENTS),
    which the page names because they get no page of their own. {} for
    every other page."""
    from govbudget.jbooks.route_safe_codes import by_page_key, restated_lines

    alias = by_page_key().get(pe_bli)
    if alias is None:
        return {}
    fields = {"printed_code": alias.line_item_code, "exhibit_family": alias.exhibit_family}
    restated = restated_lines(alias.account)
    if restated:
        fields["restated_lines"] = restated
    return fields


def decade_only_page_pes(duckdb_path) -> tuple[list[str], dict[str, int]]:
```

and (the rollup-tier sidecar dict in `_write_all_sidecars`, about line 13655) replace:

```python
            "trajectory_fact_ids": _trajectory_fact_ids(pe_bli, traj),
        }
```

with:

```python
            "trajectory_fact_ids": _trajectory_fact_ids(pe_bli, traj),
        }
        # #194: /program/0390DOM/ names the code its P-1 prints (O&M).
        obj.update(_route_safe_page_fields(pe_bli))
```

- [ ] **Step 4: The receipt matcher accepts the page key**

In `src/govbudget/program_pdf_receipts.py` (insert before `matched_amount`, about line 141), replace:

```python
def matched_amount(page: dict, y: float, column: dict, value: float) -> dict | None:
```

with:

```python
def program_code_matches(cited, row: dict) -> bool:
    """A workbook citation's pe_bli names the row's printed code, or that
    code's route-safe page key under the row's account (#194:
    dbt/seeds/p1_route_safe_codes.csv, 0390D 'O&M' -> 0390DOM). A citation
    without a pe_bli matches any row."""
    if not cited:
        return True
    from govbudget.jbooks.route_safe_codes import page_key

    cited = str(cited)
    return cited == row["code"] or cited == page_key(row["account"], row["code"])


def matched_amount(page: dict, y: float, column: dict, value: float) -> dict | None:
```

and (in `export_program_pdf_receipts`, about lines 350–351) replace:

```python
                    if citation.get("pe_bli") and str(citation["pe_bli"]) != row["code"]:
                        raise ValueError(f"Source program code differs: {fact}/{cell}")
```

with:

```python
                    if not program_code_matches(citation.get("pe_bli"), row):
                        raise ValueError(f"Source program code differs: {fact}/{cell}")
```

- [ ] **Step 5: Run the Python tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_export_route_safe_page.py tests/test_export_era_line_map.py tests/test_program_pdf_receipts.py tests/jbooks/test_export_site_5f.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/program_pdf_receipts.py | tail -1
```

Expected: `78 passed` (2 + 13 + 50 + 13); `All checks passed!`.

- [ ] **Step 6: Write the failing site tests**

Create `site/src/__tests__/program-header-printed-code.test.tsx`:

```tsx
/**
 * ProgramHeader on a route-safe alias page (#194; families piece-1 follow-ups
 * design §4.6, owner Q1 (a), Q2, Q5). /program/0390DOM/ is the P-1 line the
 * workbook prints as "O&M": the header shows the printed code, names it a
 * BLI under an "O&M" badge, says why the address is 0390DOM, and points to
 * the two R-1 program elements the RDT&E line restates. Every other page
 * keeps its key and renders neither note.
 */
import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import React from "react";

import { ProgramHeader } from "@/components/program-header";
import type { ProgramRow, RestatedLine } from "@/lib/data";

const OM: ProgramRow = {
  award_count: 0,
  exhibit_family: "om",
  fully_reconciled: false,
  reconciled_in_scope: null,
  fy2024_actual_millions: null,
  fy2024_fact_id: null,
  fy2024_xml_path: null,
  hhi: null,
  narrative_count: 0,
  org: "A",
  pe_bli: "0390DOM",
  project_count: 0,
  title: "Chem Demilitarization - O&M",
  trajectory: null,
  trajectory_fact_ids: null,
  slug: "0390DOM",
  account: null,
  account_title: null,
};
const RESTATED: RestatedLine[] = [{
  line_item_code: "RDT&E",
  title: "Chem Demilitarization - RDT&E",
  program_elements: ["0708081D", "0708083D"],
}];

afterEach(cleanup);

describe("ProgramHeader, route-safe alias page", () => {
  it("shows the printed code, the BLI term and the O&M badge", () => {
    const { container } = render(
      <ProgramHeader program={OM} tier="rollup" printedCode="O&M" restatedLines={RESTATED} />,
    );
    expect(container.querySelector("[data-printed-code]")?.textContent).toBe("O&M");
    expect(container.querySelector("[data-glossary-term]")?.textContent).toBe("BLI");
    expect(container.querySelector("[data-glossary-term]")?.getAttribute("data-glossary-term")).toBe("bli");
    expect(container.textContent).toContain("O&M");
    expect(container.querySelector("[data-printed-code-note]")?.textContent).toBe(
      "The P-1 prints this line's code as O&M; its address uses 0390DOM because a web address cannot carry “&”.");
  });

  it("names the restated RDT&E line and links both program elements", () => {
    const { container } = render(
      <ProgramHeader program={OM} tier="rollup" printedCode="O&M" restatedLines={RESTATED} />,
    );
    const note = container.querySelector("[data-restated-line]");
    expect(note?.getAttribute("data-restated-line")).toBe("RDT&E");
    expect(note?.textContent).toBe(
      "The P-1's Chem Demilitarization - RDT&E line restates R-1 program elements 0708081D and 0708083D, whose pages carry those dollars.");
    // next/link drops the trailing slash under vitest; the build writes /program/<pe>/
    expect([...(note?.querySelectorAll("a") ?? [])].map((a) => a.getAttribute("href"))).toEqual([
      expect.stringMatching(/^\/program\/0708081D\/?$/), expect.stringMatching(/^\/program\/0708083D\/?$/)]);
  });

  it("leaves every other page as it was", () => {
    const { container } = render(
      <ProgramHeader program={{ ...OM, pe_bli: "7001SA1000", slug: "7001SA1000", exhibit_family: "procurement" }} tier="rollup" />,
    );
    expect(container.querySelector("code.t-id")?.textContent).toBe("7001SA1000");
    expect(container.querySelector("[data-printed-code]")).toBeNull();
    expect(container.querySelector("[data-printed-code-note]")).toBeNull();
    expect(container.querySelector("[data-restated-line]")).toBeNull();
    expect(container.querySelector("[data-glossary-term]")?.textContent).toBe("BLI");
  });
});
```

In `site/src/lib/__tests__/program-tier.test.ts` (inside `describe("rollupProgramRow"`), replace:

```ts
  it("falls back to the PE code when the sidecar has no title", () => {
```

with:

```ts
  it("prefers the sidecar's own exhibit_family on a route-safe alias page (#194)", () => {
    // /program/0390DOM/: P-1 rows would derive "procurement"; its seed row
    // says "om", and the badge reads "O&M".
    const p1 = rollupDetails().budget_lines.map((bl) => ({ ...bl, exhibit: "P-1" }));
    expect(rollupProgramRow("0390DOM", rollupDetails({ budget_lines: p1 })).exhibit_family)
      .toBe("procurement");
    expect(rollupProgramRow("0390DOM", rollupDetails({ budget_lines: p1, exhibit_family: "om" }))
      .exhibit_family).toBe("om");
  });

  it("falls back to the PE code when the sidecar has no title", () => {
```

In `site/src/lib/__tests__/copy.test.ts` (line 2), replace:

```ts
import { count, countWord, callout, stamp, eyebrow, metaTitle, exhibitTitle, identityLine, emptyState, COPY, SHORTCUTS, fundingNote } from "@/lib/copy";
```

with:

```ts
import { count, countWord, callout, stamp, eyebrow, metaTitle, exhibitTitle, identityLine, emptyState, COPY, SHORTCUTS, fundingNote, peBliKind, documentForBasis } from "@/lib/copy";
```

Append at the end of `site/src/lib/__tests__/copy.test.ts`:

```ts

describe("#194 route-safe alias page copy (owner Q5)", () => {
  it("names an om line a BLI read from the P-1, with an O&M badge", () => {
    expect(peBliKind("om")).toBe("BLI");
    expect(peBliKind("procurement")).toBe("BLI");
    expect(peBliKind("rdte")).toBe("PE");
    expect(documentForBasis("toa", "om")).toBe("P-1");
    const row = { pe_bli: "0390DOM", title: "Chem Demilitarization - O&M", org: "A", exhibit_family: "om" };
    expect(identityLine(row)).toBe("Army · BLI 0390DOM · O&M");
    expect(metaTitle(row)).toBe("Chem Demilitarization - O&M (BLI 0390DOM) · Army");
  });

  it("says why the address is not the printed code, and names the restated line", () => {
    expect(COPY.program.printedCodeNote("O&M", "0390DOM")).toBe(
      "The P-1 prints this line's code as O&M; its address uses 0390DOM because a web address cannot carry “&”.");
    expect(COPY.program.restatedLineLead("Chem Demilitarization - RDT&E")).toBe(
      "The P-1's Chem Demilitarization - RDT&E line restates R-1 program elements ");
    expect(COPY.program.restatedLineTail).toBe(", whose pages carry those dollars.");
  });
});
```

- [ ] **Step 7: Run them to see them fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run src/lib/__tests__/program-tier.test.ts src/lib/__tests__/copy.test.ts src/__tests__/program-header-badge.test.tsx src/__tests__/program-header-printed-code.test.tsx src/__tests__/program-header-account.test.tsx 2>&1 | tail -6
```

Expected: `Test Files  3 failed | 2 passed (5)`, 5 tests failed: `program-header-printed-code.test.tsx` 2 of 3 (`expected undefined to be 'O&M'`: no `[data-printed-code]`; `expected undefined to be 'RDT&E'`: no `[data-restated-line]`; the third, every other page unchanged, passes), `program-tier.test.ts` 1 (`expected 'procurement' to be 'om'`), and `copy.test.ts` 2 (`expected 'PE' to be 'BLI'`; `TypeError: COPY.program.printedCodeNote is not a function`).

- [ ] **Step 8: Types, the tier helper and the copy**

In `site/src/lib/data.ts` (the end of `interface ProgramDetails`), replace:

```ts
  /**
   * ROADMAP #28 (decade tier only): R-1 vs P-1 majority across the page's
   * OWN older-edition workbook rows. The rollup tier derives this from
   * `budget_lines` (deriveExhibitFamily); a decade page's budget_lines array
   * is empty by construction, so the exporter computes it and ships it.
   */
  exhibit_family?: string | null;
}
```

with:

```ts
  /**
   * ROADMAP #28 (decade tier): R-1 vs P-1 majority across the page's OWN
   * older-edition workbook rows. The rollup tier derives this from
   * `budget_lines` (deriveExhibitFamily); a decade page's budget_lines array
   * is empty by construction, so the exporter computes it and ships it.
   * #194: a rollup page keyed by a route-safe page key carries its seed
   * row's family too ("om" on /program/0390DOM/), and rollupProgramRow
   * prefers it to the derived one.
   */
  exhibit_family?: string | null;
  /**
   * #194 (owner Q2, Q5): present only on a page keyed by a route-safe page
   * key (dbt/seeds/p1_route_safe_codes.csv): the budget line code the P-1
   * prints ("O&M" on /program/0390DOM/), which a web address cannot carry.
   * The header shows it in place of the key.
   */
  printed_code?: string;
  /**
   * #194 (owner Q1 (a)): on that page, the P-1 lines of the same account
   * that restate R-1 program elements and so get no page of their own
   * (route_safe_codes.P1_R1_RESTATEMENTS).
   */
  restated_lines?: RestatedLine[];
}

/** A P-1 line that prints the same dollars as R-1 program elements (#194). */
export interface RestatedLine {
  line_item_code: string;
  title: string;
  program_elements: string[];
}
```

In `site/src/lib/program-tier.ts` (`rollupProgramRow`, about line 420), replace:

```ts
    org: details.service_org || "DoD",
    exhibit_family: deriveExhibitFamily(details.budget_lines),
```

with:

```ts
    org: details.service_org || "DoD",
    // #194: a route-safe alias page names its own family (its seed row's
    // "om" for /program/0390DOM/, whose P-1 rows would derive "procurement").
    exhibit_family: details.exhibit_family ?? deriveExhibitFamily(details.budget_lines),
```

In `site/src/lib/copy.ts` (about lines 75–78), replace:

```ts
/** Procurement lines are BLIs; everything else is a program element. */
export function peBliKind(exhibitFamily: string | null): PeBliKind {
  return (exhibitFamily ?? "").toLowerCase() === "procurement" ? "BLI" : "PE";
}
```

with:

```ts
/**
 * Procurement lines are BLIs; everything else is a program element. #194:
 * the one "om" page (/program/0390DOM/) is a P-1 line too, so its code is a
 * BLI while its badge reads "O&M".
 */
export function peBliKind(exhibitFamily: string | null): PeBliKind {
  const family = (exhibitFamily ?? "").toLowerCase();
  return family === "procurement" || family === "om" ? "BLI" : "PE";
}
```

and (`COPY.program`, about line 455) replace:

```ts
    rollupBadgeTitle: "Summary figures from the R-1/P-1 workbooks: this line carries no R-2/P-40 J-book detail. The Purpose note states why.",
```

with:

```ts
    rollupBadgeTitle: "Summary figures from the R-1/P-1 workbooks: this line carries no R-2/P-40 J-book detail. The Purpose note states why.",
    /** #194, owner Q5: a route-safe alias page says why its address is not the printed code. */
    printedCodeNote: (printed: string, key: string) =>
      `The P-1 prints this line's code as ${printed}; its address uses ${key} because a web address cannot carry “${(/[&#/?%\s]/.exec(printed) ?? [""])[0]}”.`,
    /** #194, owner Q1 (a): the restated P-1 line, around its code-linked program elements. */
    restatedLineLead: (title: string) => `The P-1's ${title} line restates R-1 program elements `,
    restatedLineTail: ", whose pages carry those dollars.",
```

- [ ] **Step 9: The header and the page**

In `site/src/components/program-header.tsx` (lines 1–5), replace:

```tsx
import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import type { HeroCategory, ProgramRow } from "@/lib/data";
import { serviceOrgName } from "@/lib/program-tier";
```

with:

```tsx
import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { COPY, peBliKind } from "@/lib/copy";
import type { HeroCategory, ProgramRow, RestatedLine } from "@/lib/data";
import { serviceOrgName } from "@/lib/program-tier";
```

and (the end of `ProgramHeaderProps`) replace:

```tsx
  accountSplit?: boolean;
}
```

with:

```tsx
  accountSplit?: boolean;
  /**
   * #194 (owner Q2, Q5): the code the P-1 prints when this page's key is its
   * route-safe page key (the sidecar's printed_code: "O&M" on
   * /program/0390DOM/). The header shows it in place of the key and says why
   * the address differs. Absent on every other page.
   */
  printedCode?: string | null;
  /** #194 (owner Q1 (a)): the sidecar's restated_lines, named under the code. */
  restatedLines?: readonly RestatedLine[];
}
```

and replace:

```tsx
  tier = "full",
  accountSplit = false,
}: ProgramHeaderProps) {
  const { title, org, exhibit_family, reconciled_in_scope, pe_bli, account, account_title } =
    program;
```

with:

```tsx
  tier = "full",
  accountSplit = false,
  printedCode = null,
  restatedLines = [],
}: ProgramHeaderProps) {
  const { title, org, exhibit_family, reconciled_in_scope, pe_bli, account, account_title } =
    program;
  const kind = peBliKind(exhibit_family);
```

and (the PE/BLI label and the code, about lines 262–273) replace:

```tsx
        <Link
          href={`/glossary/#${exhibit_family === "procurement" ? "bli" : "pe"}`}
          data-glossary-term={exhibit_family === "procurement" ? "bli" : "pe"}
          className="text-xs text-muted-foreground underline decoration-dotted underline-offset-2 hover:text-foreground"
        >
          {exhibit_family === "procurement" ? "BLI" : "PE"}
        </Link>
        <code className="t-id bg-muted px-1.5 py-0.5 rounded">
          {pe_bli}
        </code>
      </div>
```

with:

```tsx
        <Link
          href={`/glossary/#${kind.toLowerCase()}`}
          data-glossary-term={kind.toLowerCase()}
          className="text-xs text-muted-foreground underline decoration-dotted underline-offset-2 hover:text-foreground"
        >
          {kind}
        </Link>
        <code className="t-id bg-muted px-1.5 py-0.5 rounded" data-printed-code={printedCode ? "" : undefined}>
          {printedCode ?? pe_bli}
        </code>
      </div>
      {printedCode && (
        <p className={styles.account} data-printed-code-note>
          {COPY.program.printedCodeNote(printedCode, pe_bli)}
        </p>
      )}
      {printedCode && restatedLines.map((line) => (
        <p key={line.line_item_code} className={styles.account} data-restated-line={line.line_item_code}>
          {COPY.program.restatedLineLead(line.title)}
          {line.program_elements.map((pe, i) => (
            <span key={pe}>
              {i === 0 ? "" : i === line.program_elements.length - 1 ? " and " : ", "}
              <Link href={`/program/${pe}/`} className="text-primary hover:underline"><code>{pe}</code></Link>
            </span>
          ))}
          {COPY.program.restatedLineTail}
        </p>
      ))}
```

In `site/src/app/program/[peBli]/page.tsx` (about line 106), replace:

```tsx
import { metaTitle } from "@/lib/copy";
```

with:

```tsx
import { metaTitle, peBliKind } from "@/lib/copy";
```

and (the `<ProgramHeader … />` props, about lines 760–767) replace:

```tsx
          orgHasPage={getAgencies().some((a) => a.org === program.org)}
          tier={tier}
          accountSplit={accountSplit}
        />
```

with:

```tsx
          orgHasPage={getAgencies().some((a) => a.org === program.org)}
          tier={tier}
          accountSplit={accountSplit}
          printedCode={details.printed_code ?? null}
          restatedLines={details.restated_lines ?? []}
        />
```

and (about line 794) replace:

```tsx
      <ProgramWayfinding code={program.pe_bli} isProcurement={program.exhibit_family === "procurement"} />
```

with:

```tsx
      <ProgramWayfinding code={details.printed_code ?? program.pe_bli} isProcurement={peBliKind(program.exhibit_family) === "BLI"} />
```

- [ ] **Step 10: The census comment in `program-skeleton.mjs`**

In `site/scripts/gates/program-skeleton.mjs` (the `MIN_DECADE_ONLY_PAGES` comment, about lines 3312–3318; the floor does not move), replace:

```js
/** Non-vacuity floor: the shipped corpus holds exactly 553 decade-only pages
 *  (measured 2026-08-31 from fct_decade_series — keys with a positive grain,
 *  no PB2026 page, not an era procurement key, route-safe: 3,771 candidates
 *  − 1,994 that already have a page − 1,214 era keys − 8 all-zero − 2
 *  route-unsafe). A drop means either the predicate broke or the corpus
 *  changed — RE-MEASURE and re-derive this number, never lower it to
 *  whatever the build produced. */
```

with:

```js
/** Non-vacuity floor: the shipped corpus holds exactly 553 decade-only pages
 *  (measured 2026-08-31 from fct_decade_series — keys with a positive grain,
 *  no PB2026 page, not an era procurement key, route-safe: 3,771 candidates
 *  − 1,994 that already have a page − 1,214 era keys − 8 all-zero − 2
 *  route-unsafe). A drop means either the predicate broke or the corpus
 *  changed — RE-MEASURE and re-derive this number, never lower it to
 *  whatever the build produced.
 *  #194 (families piece-1 follow-ups): the 2 route-unsafe keys were 0390D's
 *  stale PB2024–PB2025 'O&M' and 'RDT&E' rows (re-measured 2026-10-13 with
 *  export_site.decade_only_page_pes: the same census). The Chem Demil write
 *  re-keys O&M to 0390DOM, which has a PB2026 page, and deletes RDT&E, so the
 *  census becomes 3,770 − 1,995 − 1,214 − 8 − 0 = 553; the release proof
 *  re-measures it. */
```

- [ ] **Step 11: Run the site tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run src/lib/__tests__/program-tier.test.ts src/lib/__tests__/copy.test.ts src/__tests__/program-header-badge.test.tsx src/__tests__/program-header-printed-code.test.tsx src/__tests__/program-header-account.test.tsx 2>&1 | tail -4
npx tsc --noEmit -p tsconfig.json 2>&1 | grep -E 'program-header|lib/copy|lib/data|program-tier|program/\\[peBli\\]/page|printed-code' ; echo "tsc lines in edited files: done"
```

Expected: `Test Files  5 passed (5)`, `Tests  62 passed (62)`; the `grep` prints nothing before `tsc lines in edited files: done` (`tsc` may print errors elsewhere that HEAD already has; none in these files).

- [ ] **Step 12: Weigh the scope string on today's /data/ page (read-only)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && python3 - <<'EOF'
import zlib
def gz(b):
    c = zlib.compressobj(9, zlib.DEFLATED, 31); return len(c.compress(b) + c.flush())
b = open("site/out/data/index.html", encoding="utf-8").read()
old_html = "line_item_code (the budget line code printed on it, the pe_bli a same_program line&#x27;s era citations carry)"
new_html = ("line_item_code (the budget line code printed on it), program_key (the pe_bli a same_program line&#x27;s"
            " era citations carry; the printed code except 0390DOM for 0390D&#x27;s O&amp;M line, whose"
            " &quot;&amp;&quot; cannot appear in a web address)")
old_rsc = old_html.replace("&#x27;", "'")
new_rsc = ("line_item_code (the budget line code printed on it), program_key (the pe_bli a same_program line's"
           " era citations carry; the printed code except 0390DOM for 0390D's O&M line, whose"
           ' \\"\\u0026\\" cannot appear in a web address)')
print(b.count(old_html), b.count(old_rsc))
n = b.replace(old_html, new_html).replace(old_rsc, new_rsc)
print(len(b.encode()), gz(b.encode()), "->", len(n.encode()), gz(n.encode()))
EOF
```

Expected (with Task 1's build of today's `data/site` in `site/out`): `1 2`, then `85358 14500 -> 85725 14712` (+367 raw, +212 gzip; zlib's gzip container reads 30 bytes under the gate's 14,530). Under the ceiling 105,000 / 15,600 by about 19,275 raw and 858 gzip; Task 21 re-measures on the release build and re-stamps `build.mjs`. If `site/out` is older than Task 1's build, the absolute numbers differ and only the deltas count.

- [ ] **Step 13: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/export_site.py GovBudget/src/govbudget/program_pdf_receipts.py GovBudget/site/scripts/gates/program-skeleton.mjs GovBudget/site/src/lib/data.ts GovBudget/site/src/lib/program-tier.ts GovBudget/site/src/lib/copy.ts GovBudget/site/src/components/program-header.tsx GovBudget/site/src/app/program/[peBli]/page.tsx GovBudget/tests/test_export_route_safe_page.py GovBudget/site/src/__tests__/program-header-printed-code.test.tsx GovBudget/tests/test_export_era_line_map.py GovBudget/tests/test_program_pdf_receipts.py GovBudget/tests/jbooks/test_export_site_5f.py GovBudget/site/src/lib/__tests__/program-tier.test.ts GovBudget/site/src/lib/__tests__/copy.test.ts && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(program): /program/0390DOM/ shows the printed code O&M with an O&M badge and BLI term, says why the address differs and names the restated RDT&E line; map scope names program_key; receipts accept the alias (#194)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `15 files changed`. The page exists only after Task 22's write and export; Task 21's proof builds it on the `fu-post` snapshot and checks the header, the two links and the sitemap (4,349 → 4,350).
