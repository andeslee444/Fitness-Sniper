<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 2: Record corrections and filed follow-ups

**Spec:** §6.6 (the `era_keys.py` docstring and ROADMAP #28 correction), §11.8 (five follow-ups filed at S0), §9 S0 ("Docstring and #28 corrections; file the §11 follow-ups"). The spec amendments (CLI name, plan-review corrections, owner decisions) are already in the plan commit; Step 8 only checks them.

**Files:**
- Test: `tests/test_roadmap_backlog.py` (append after line 232, the end of the file)
- Modify: `docs/superpowers/ROADMAP.md` (insert after line 4705, the end of #192; insert after line 5676, the end of #28)
- Modify: `src/govbudget/jbooks/era_keys.py:118-120` (the `is_era_procurement_key` docstring; Step 6 shows lines 115-121)
- Modify: `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md:193`, `:207` (CLI name); insert after `:198` (end of §4.6), after `:249` (end of §5.2), after `:362` (end of §6.4's per-edition-table bullet). Line numbers are those of the file before Step 8; Step 8 anchors every edit on text.

**Interfaces:**
Consumes: Task 1's environment (`source scripts/era/env.sh`; `GOVBUDGET_PG_DSN` for the read-only `tests/jbooks/test_era_keys.py`).
Produces: ROADMAP backlog entries #193 (`/years/` sharding), #194 (0390D Chem Demil lines), #195 (JLTV narrative attribution), #196 (dead v1 receipt files), #197 (`search_aliases.csv` routes), each ending `**Status:** open (2026-10-02).`; `FAMILIES_FOLLOW_UPS` and `test_the_families_piece_1_follow_ups_are_filed_once_and_open` in `tests/test_roadmap_backlog.py`; the #28 correction note; the corrected docstring. (Spec amendments — CLI name, plan-review corrections, owner decisions — are already in the plan commit.) If main files its own #193+ before this branch merges, renumber these at merge (the contiguity test will say so).

Measured for this task (read-only, 2026-10-02):
- `3010F-AF-L1`: `select fiscal_year, count(*), sum(amount_thousands), min(title) from budget_lines where pe_bli='3010F-AF-L1' group by 1` → 2017 7 rows F-35 · 2018 13 · 2019 13 · 2020 9 · 2021 10 (all `F-35`) · 2022 3 · 2023 3 (`B-21 Raider`); 58 rows, 142,566,153 thousand. Column I of each era workbook (`data/raw_docs/fy20NN/dod/p1_display.xlsx`, rows with Account 3010F and Line Number 1): `ATA000` in PB2017–21, `B02100` in PB2022–23. `count(distinct pe_bli)` of era keys = 1,214; `count(distinct (fiscal_year, pe_bli))` = 6,927.
- `json/years_matrix.json` in the live export: 3,178,320 bytes (`ls -l`); cap `_YEARS_MATRIX_MAX_BYTES = 4 * 1024 * 1024` (`export_site.py:17063`).
- 0390D in `p1_display.xlsx` (openpyxl, `Add` rows whose Budget Line Item is `O&M`/`RDT&E`): PB2026 rows 303–304, FY2024 actuals 87,404 + 1,002,560 = 1,089,964; PB2025 FY2023 actuals 1,059,818; PB2024 FY2022 actuals 1,093,252. `_INVALID_PE_BLI_CHARS = set("&/%#")` (`p1_loader.py:21`).
- JLTV: citation `136baeef904dd052` is `jbook_narrative`, pe_bli `5731D15610`, sha `a0b31f94ab70…`, `page_number` null; its body contains the continuation sentence. `jbook_documents` id 346 (`BA 3, 4 & 6`, `downloaded`), id 347 (`BA1 - Tactical & Support Vehicles`, sha `184228d828aa…`, `superseded`); `data/site/pdfs` holds only the a0b31f94 PDF. pypdfium2 text search for "previous budget line D15603": BA1 (251 pages) → page 100 only; BA 3, 4 & 6 (602 pages) → none.
- v1 receipts: `data/site/json/budget-pdf-receipts/` holds 256 `??.json` shards beside `v2/`, 169 non-empty; `budget_pdf_receipts.export_budget_pdf_receipts` (`budget_pdf_receipts.py:393-472`) has no caller in `src/`, `scripts/`, `site/` or `tests/`; the site fetches `/json/budget-pdf-receipts/v2/` only (`site/src/lib/budget-pdf-receipts.ts:35`); `data-seeds/f15_budget_pdf_sources.json` has no reader.
- `data-seeds/search_aliases.csv` line 3 `JASSM,/program/0603000D8Z/`, line 11 `C-130J,/program/2012C130J/`; `dbt/seeds/program_aliases.csv` lines 2-3 carry the #55 corrections (0207325F, 0401132F; commits `c6270fc9`, `1edbfcc0`, 2026-08-27); live `json/search_quick.json` has `alias:jassm` → `/program/0603000D8Z/`, `alias:c-130j` → `/program/2012C130J/`.
- `tests/test_roadmap_backlog.py`: 25 passed; `tests/jbooks/test_era_keys.py`: 8 passed.
- §5.2's "$0 selected actuals" for R-DEC-ERA-EXCLUDE (DuckDB `data/duckdb/govbudget.duckdb`, `read_only=True`). The 2 UNSAFE chains are 14 keys, `0390D-ARMY-L1` "Chem Demilitarization - O&M" and `0390D-ARMY-L2` "Chem Demilitarization - RDT&E" in each of PB2017–PB2023, and carry 5,832,017 thousand of selected actuals: `with k as (select distinct fiscal_year ed, pe_bli, title from stg_budget_lines where exhibit='P-1' and account='0390D' and fiscal_year<=2023 and regexp_matches(pe_bli,'-L[0-9]+$') and title in ('Chem Demilitarization - O&M','Chem Demilitarization - RDT&E')) select count(*), sum(f.amount) from k join fct_decade_series f on f.pe_bli=k.pe_bli and f.edition_year=k.ed and f.amount_type_kind='actuals'` → `(14, 5832017.0)` (the edition's FY(N−2) actuals, the same selection Task 11's `EraKey.actuals_k` uses). The CR placeholders are $0: the same join over era keys whose title contains "continuing resolution" → 45 keys, 45 actuals rows, sum 0.0.
- §6.4's `/coverage/` stamp "85,710 / 20,288" (462 gzip bytes under 20,750) is stale. `curl -s https://fiscalreceipts.com/coverage/` weighed like gate 1's `weigh()` (`site/scripts/gates/build.mjs:889-892`, raw bytes and `zlib.gzipSync(buf, {level: 9})`) → 86,203 raw / 20,458 gzip, which leaves 16,797 raw and 292 gzip bytes under the 103,000 / 20,750 ceiling (`build.mjs:779`, still stamped `measured: "85,710 / 20,288"`). Task 5 re-stamps gate 1 from a fresh S0 build and gets the same numbers.
- §4.6's `keys.csv` evidence list names "cost types", but Task 11's `keys.csv` has no cost-type column. The P-1 loader keeps `Add` rows and sums every cost-type sub-row of a line into one row per (account, organization, budget activity, line) per edition (`src/govbudget/jbooks/p1_loader.py:89-92`, `:128-131`; Task 6 moves this summing into `parse_p1_rollup`), and that row's `source_cells` lists every summed cell, so the cost types stay traceable to their workbook cells.

- [ ] **Step 1: Write the failing ledger test**

Append to `tests/test_roadmap_backlog.py`, two blank lines after line 232 (`    assert rel in ROADMAP.read_text(encoding="utf-8"), f"no backlog entry cites {rel}"`):

```python
# Families piece 1 (docs/superpowers/specs/2026-10-02-era-procurement-history-
# design.md §11.8) files five follow-ups at S0. Asserted by subject phrase, as
# above; each phrase sits on one line of its entry.
FAMILIES_FOLLOW_UPS = [
    "/years/ needs sharding",
    "Chem Demil O&M and RDT&E lines",
    "JLTV continuation sentence",
    "Dead v1 PDF receipt files",
    "still routes JASSM and C-130J",
]


@pytest.mark.parametrize("subject", FAMILIES_FOLLOW_UPS)
def test_the_families_piece_1_follow_ups_are_filed_once_and_open(subject):
    hits = [(num, body) for num, body in entries() if subject in body]
    assert len(hits) == 1, f"{subject!r} filed {len(hits)} times, want 1"
    num, body = hits[0]
    assert EFFORT_RE.search(body), f"#{num} has no `Effort: hours|days|weeks`"
    assert POINTER_RE.search(body), f"#{num} names no source path"
    assert body.rstrip().endswith("**Status:** open (2026-10-02)."), (
        f"#{num} does not end with its open-status line"
    )
```

- [ ] **Step 2: Run it — it fails**

```bash
uv run --project . pytest tests/test_roadmap_backlog.py -q
```

Expected: `5 failed, 25 passed`, each failure `AssertionError: '<subject>' filed 0 times, want 1` (e.g. `'/years/ needs sharding' filed 0 times, want 1`).

- [ ] **Step 3: File #193–#197**

In `docs/superpowers/ROADMAP.md`, insert the five entries between #192's Status line and the sweep note. Before (lines 4703-4707):

```
  `src/govbudget/export_site.py` (the district-sum derived rows),
  `site/scripts/gates/linkgraph.mjs` (leg k). Effort: hours.
  **Status:** open (2026-10-01).

*Status markers (one ledger sweep, 2026-08-24).* Every numbered entry below now
```

After:

```
  `src/govbudget/export_site.py` (the district-sum derived rows),
  `site/scripts/gates/linkgraph.mjs` (leg k). Effort: hours.
  **Status:** open (2026-10-01).

- **#193 /years/ needs sharding before it can carry era procurement or
  PB2027.** `_emit_years_matrix` (`src/govbudget/export_site.py`) raises
  when `json/years_matrix.json` passes `_YEARS_MATRIX_MAX_BYTES`
  (4,194,304 bytes), and that cap is not to be raised. Measured read-only
  2026-10-02 on the live export (built 2026-10-02T01:30Z): 3,178,320 bytes,
  which leaves 1,015,984. The families piece-1 spec estimates the
  PB2017–PB2023 procurement points at about 0.75 MB more (about 3.9–4.0 MB
  in all), which would leave no room for PB2027, so piece 1 fences /years/:
  it keeps its procurement rows from PB2024 on
  (`docs/superpowers/specs/2026-10-02-era-procurement-history-design.md`
  §2, §6.2). Fix: shard the matrix (by exhibit or by edition block, each
  shard fetched lazily by the /years/ island), check the size per shard,
  then lift the era fence. Source: `src/govbudget/export_site.py`
  (`_YEARS_MATRIX_MAX_BYTES`, `_emit_years_matrix`),
  `site/src/app/years/page.tsx`. Effort: days.
  **Status:** open (2026-10-02).

- **#194 The P-1 loader drops 0390D's real Chem Demil O&M and RDT&E lines
  as section headers.** `_is_valid_pe_bli`
  (`src/govbudget/jbooks/p1_loader.py`) rejects a Budget Line Item cell that
  holds any of `& / % #` or whitespace, to skip appropriation labels and to
  keep `/program/[peBli]` routes safe. Account 0390D (Chemical Agents and
  Munitions Destruction) prints two real lines under exactly those codes:
  `O&M` ("Chem Demilitarization - O&M") and `RDT&E` ("Chem Demilitarization
  - RDT&E"), both `Add` rows. Measured read-only 2026-10-02 in
  `data/raw_docs/fy2026/dod/p1_display.xlsx` rows 303–304: FY2024 actuals
  87,404 + 1,002,560 = 1,089,964 thousand (about $1.09B); PB2025 drops
  1,059,818 of FY2023 actuals and PB2024 1,093,252 of FY2022 actuals the
  same way. None of it reaches `budget_lines`, a page or a total. The era
  editions print the same pair; families piece 1 excludes those chains as
  `exclude_route_unsafe` (R-DEC-ERA-EXCLUDE,
  `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md`
  §2, §5.1). Fix: load the two lines under a route-safe key with the
  printed code kept in `line_item_code`, give them pages, and re-measure
  every total that sums 0390D. Source: `src/govbudget/jbooks/p1_loader.py`
  (`_is_valid_pe_bli` and the section-header skip in `load_p1_rollup`).
  Effort: days.
  **Status:** open (2026-10-02).

- **#195 The JLTV continuation sentence is cited to a book that does not
  print it.** Narrative fact `136baeef904dd052` (5731D15610, the
  `LineItem[6]` justification) holds "NOTE: This budget line D15610 is a
  continuation of an existing effort where prior year funds through FY 2020
  are reflected under the previous budget line D15603." Its citation names
  the PB2026 Army OPA "BA 3, 4 & 6 - Other Support Equipment, Initial
  Spares and Agile Portfolio Management" PDF (`jbook_documents` id 346, sha
  `a0b31f94…`) with no page: the narrative came from the
  whole-appropriation master XML attached to that PDF, and none of its 602
  pages prints the sentence. Only the BA1 "Tactical & Support Vehicles"
  book prints it, on PDF p.100 of 251 (id 347, sha `184228d8…`), and that
  book is `superseded` in `jbook_documents`, so it is not hosted. Measured
  read-only 2026-10-02 (`data/site/citations/citations.parquet`,
  `data/site/data/jbook_narratives.parquet`, the two PDFs under
  `data/raw_docs/fy2026/a/`). Families piece 1 records the JLTV successor
  (5600D15603 → 5731D15610) from the BA1 page by document sha, page and XML
  path, and does not display it
  (`docs/superpowers/specs/2026-10-02-era-procurement-history-design.md`
  §5.4). Fix: attribute a master-XML narrative to the book whose pages
  print it (or host BA1 and re-point this fact), and add a check that every
  `jbook_narrative` citation names a document that prints its text. Source:
  `src/govbudget/export_site.py` (the jbook_narrative citation pass).
  Effort: hours.
  **Status:** open (2026-10-02).

- **#196 Dead v1 PDF receipt files still ship and need the owner's sign-off
  to remove.** `export_budget_pdf_receipts` in
  `src/govbudget/budget_pdf_receipts.py:393-472` has no caller: the
  `export-budget-pdf-receipts` command and the `export-site` CLI both run
  `program_pdf_receipts.export_program_pdf_receipts`, which writes
  `json/budget-pdf-receipts/v2/`. The 256 v1 shards the old function wrote,
  `json/budget-pdf-receipts/??.json` (169 of them non-empty, measured
  read-only 2026-10-02 in `data/site`), still sit beside `v2/`, and step 5d2
  of `site/scripts/prepare-assets.mjs` copies the whole directory into the
  build, so they deploy; the site fetches only `v2/`
  (`site/src/lib/budget-pdf-receipts.ts`).
  `data-seeds/f15_budget_pdf_sources.json` has no reader either. Fix, with
  the owner's sign-off because it deletes shipped files: remove the
  function, the v1 shards and the unread seed, and copy only `v2/` in
  `prepare-assets.mjs`. Found by the families piece-1 review. Source:
  `src/govbudget/budget_pdf_receipts.py`,
  `site/scripts/prepare-assets.mjs`. Effort: hours.
  **Status:** open (2026-10-02).

- **#197 `data-seeds/search_aliases.csv` still routes JASSM and C-130J to
  the pages #55 moved them off.** Its line 3 sends a search for "JASSM" to
  `/program/0603000D8Z/` (Joint Munitions Advanced Technology) and line 11
  sends "C-130J" to `/program/2012C130J/` (AC/MC-130J). #55 corrected both
  in `dbt/seeds/program_aliases.csv` on 2026-08-27 (JASSM → 0207325F,
  C-130J → 0401132F; `c6270fc9`, `1edbfcc0`), but nothing ties the two seeds
  together, and `export_site` publishes the search seed as `alias:` entries
  in `json/search_quick.json`: the live export routes `alias:jassm` to
  `/program/0603000D8Z/` and `alias:c-130j` to `/program/2012C130J/`
  (measured read-only 2026-10-02). Fix: route both terms as #55 did, and add
  a check that a term present in both seeds names the same program; the
  families registry (pieces 2–4) is meant to become the one membership
  source. Source: `data-seeds/search_aliases.csv`,
  `dbt/seeds/program_aliases.csv`, `src/govbudget/export_site.py` (the
  search-aliases block). Effort: hours.
  **Status:** open (2026-10-02).

*Status markers (one ledger sweep, 2026-08-24).* Every numbered entry below now
```

Each subject phrase the test looks for sits on one line (the parser joins lines with `\n`).

- [ ] **Step 4: Add the dated correction under #28 (nothing in #28 is reworded)**

Before (lines 5674-5677):

```
    **Status: OPEN** — swept 2026-08-24. Deferred by the entry itself and
    assigned to drawdown Task D5 ("decide before building"), which never
    executed; no commit in the history references #28.
29. **Program-lineage Phase 2 (coverage + depth, from 5I).** The Phase-1 lineage
```

After:

```
    **Status: OPEN** — swept 2026-08-24. Deferred by the entry itself and
    assigned to drawdown Task D5 ("decide before building"), which never
    executed; no commit in the history references #28.

    *Correction (2026-10-02, families piece 1; nothing above is reworded).*
    `3010F-AF-L1` is not a rollup parse artifact. It is Air Force Aircraft
    Procurement line 1: the era loader's key for the P-1 row whose printed
    Line Item (column I) is ATA000 "F-35" in PB2017–PB2021 and B02100 "B-21
    Raider" in PB2022–PB2023 — 58 `budget_lines` rows, $142.566B summed over
    every scenario column (measured read-only 2026-10-02 in Postgres and the
    seven era `data/raw_docs/fy20NN/dod/p1_display.xlsx` workbooks). The
    1,214 `-L<n>` keys are the era loader's line keys
    (`{account}-{org}-L{line}`; 6,927 edition-key pairs): real P-1 lines keyed
    by line number because the loader drops the printed code, not parse
    debris. They must still never become pages, since a line number is no
    program identity across editions; families piece 1
    (`docs/superpowers/specs/2026-10-02-era-procurement-history-design.md`)
    maps them through their printed codes instead. The same claim in
    `src/govbudget/jbooks/era_keys.py` (`is_era_procurement_key`) is
    corrected in the same commit.
29. **Program-lineage Phase 2 (coverage + depth, from 5I).** The Phase-1 lineage
```

- [ ] **Step 5: Run the ledger tests — they pass**

```bash
uv run --project . pytest tests/test_roadmap_backlog.py -q
```

Expected: `30 passed`.

- [ ] **Step 6: Correct the `is_era_procurement_key` docstring**

In `src/govbudget/jbooks/era_keys.py`, before (lines 115-121):

```python
    across editions. A /program/ page is a cross-edition identity claim by
    construction — one URL, one title, a decade of figures under it — so
    these keys must never become pages, however much money they carry
    (1,214 of them in the shipped warehouse; '3010F-AF-L1' alone sums
    $142.6B across PB2017-PB2023 because the era P-1 loader files an
    account's rollup row under its first line number).
    """
```

After:

```python
    across editions. A /program/ page is a cross-edition identity claim by
    construction — one URL, one title, a decade of figures under it — so
    these keys must never become pages, however much money they carry
    (1,214 of them in the shipped warehouse). '3010F-AF-L1' shows why: it
    is Air Force Aircraft Procurement line 1, whose printed Line Item is
    ATA000 (F-35) in PB2017-PB2021 and B02100 (B-21 Raider) in
    PB2022-PB2023 — two programs under one key, 58 rows and $142.566B
    summed over every scenario column (corrected 2026-10-02: this
    docstring used to call the line an account total filed under its
    first line number).
    """
```

(No new test: spec §6.6 is a record correction. The other `3010F-AF-L1` mentions — `export_site.py:6788`, `tests/test_export_site_decade_only.py:15` — state only the true $142.6B sum and stay.)

- [ ] **Step 7: Check the module still imports and its tests pass**

```bash
uv run --project . python -c "from govbudget.jbooks.era_keys import is_era_procurement_key as f; print(f('3010F-AF-L1'), 'rollup' in f.__doc__, 'B02100' in f.__doc__)"
uv run --project . pytest tests/jbooks/test_era_keys.py -q
```

Expected: `True False True`; `8 passed` (its live-warehouse guard only SELECTs from `GOVBUDGET_PG_DSN`).

- [ ] **Step 8: Confirm the spec already carries the CLI name and the plan-review corrections**

The plan commit (`docs(families): implementation plan …`) already applied every spec amendment this piece needs: the
`era-map` CLI name (§4.6, §4.7), eight dated `*Correction (2026-10-02, implementation plan review; nothing above
reworded).*` notes (§4.5, §4.6, §5.2, §6.4, §7, §9, §10, §11) and two `*Owner decision (2026-10-02, …)*` notes
(§5.2: R-DEC-ERA-EXCLUDE kept with the $5.83B figure; §6.4: the era table on `/downloads/`, the "tier pending" badge,
the `/data/` hoist). This task does not edit the spec. Check:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget
grep -n "jbooks era-map" docs/superpowers/specs/2026-10-02-era-procurement-history-design.md || echo none
grep -c '^\*Correction (2026-10-02, implementation plan review; nothing above reworded)\.\*$' docs/superpowers/specs/2026-10-02-era-procurement-history-design.md
grep -c '^\*Owner decision (2026-10-02, implementation plan review; nothing above reworded)\.\*$' docs/superpowers/specs/2026-10-02-era-procurement-history-design.md
```

Expected: `none`, `8`, `2`. If any differs, stop: the plan commit is missing from this branch.

- [ ] **Step 9: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/tests/test_roadmap_backlog.py GovBudget/docs/superpowers/ROADMAP.md GovBudget/src/govbudget/jbooks/era_keys.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(era): correct the 3010F-AF-L1 rollup claim (#28, era_keys); file #193-#197 (families piece 1 S0)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `3 files changed`.
