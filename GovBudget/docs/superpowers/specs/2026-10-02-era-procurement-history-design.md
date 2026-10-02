# Procurement History Before FY2024 — Families Piece 1

**Date:** 2026-10-02
**Status:** Draft for owner review. Approving this spec also approves the three class
rulings in §5.2 (R-DEC-ERA-SAME, R-DEC-ERA-EXCLUDE, R-DEC-ERA-HISTORY).
**Parent:** [2026-10-02-platform-families-overview.md](2026-10-02-platform-families-overview.md)
(owner decisions R-DEC-FAM-UNIT, -NAME, -REVIEW, -ERAONLY).
**Depends on:** the PB2017–PB2026 decade lake (Phase 5E), `fct_decade_series`,
`budget_lines_decade`, the v2 PDF receipt pipeline (`program_pdf_receipts.py`), the
F-15 family history (`f15_funding_history.py`).
**Evidence base:** read-only measurements at main `dc801fdb` (2026-10-02), re-checked
adversarially against the raw workbooks, Postgres, DuckDB and the code. Scratch
outputs: `era_map/era_map_proposal.csv`, `designverify/` (session scratchpad).

---

## 1. Goal

Every procurement program page whose budget line code appears in a PB2017–PB2023 P-1
workbook shows those editions' points (FY(N−2) actuals, FY(N−1) enacted, FY(N)
request), each cited to its own workbook cell and, where the PDF matcher can find it,
a highlighted location in the same edition's P-1 PDF. Today every procurement page
outside F-15 starts at PB2024 (FY2022 actuals), while R&D pages reach back to PB2017.

**Success criteria**
- About 800 of the 891 PB2026 procurement program pages gain era points (about 581
  of them all seven editions). The three class rulings alone reach about 731; the
  individual decisions bring the rest. The 892nd page is the classified aggregate,
  which never gains points.
- Every published figure that exists before this piece keeps its fact ID, amount and
  inputs. The only changes to existing citations are the ones listed in §10.
- `json/f15_funding_history.json` is byte-identical through the data changes
  (S0–S4). It changes only in the separate, approved F-15 correction (S5).
- Source-linked coverage stays 100% for budget figures, and no figure that has a
  complete PDF receipt today loses it (overview §7).
- A release gate (`verify-era-map`, in the `verify-phase5` assembly) fails if any
  era line is unmapped, any decision went stale, or any published era figure does
  not recompute from its own workbook row.

## 2. Non-goals

- No pages for the 279 discontinued code chains (R-DEC-FAM-ERAONLY). They live in
  the map and the program table only.
- No family registry, evidence engine, template or new family page (pieces 2–4).
- No re-keying of `pe_bli` in the lake, no published fact ID change.
- No era book diffs and no `/feed/` re-ranking (`assert_book_diff_no_era_procurement.sql`
  stays). No quantities, PB2027, PB2012–16 or service J-book backfill.
- No change to the F-15 page's layout or its six workspaces; no change to lineage
  funding lines; `/years/` changes only if it fits its size cap (§6.2).
- No fix for PB2026's dropped `0390D` Chem Demil `O&M`/`RDT&E` lines (filed
  separately, §11).

## 3. What is true today

- Every PB2017–23 P-1 workbook has the same layout as the modern ones: `Line Number`
  in column F and the budget line code in column I, headed "Line Item" (PB2024+:
  "Budget Line Item"). Column I is filled on all 6,927 era keys.
- `p1_loader.py:116-124` detects era layout, drops the code and keys the row by line
  number; `:152-159` mints `{account}-{org}-L{line}` (`era_keys.py:72-86`);
  `:140-141` skips any row with a blank Line Number.
- Era keys per edition: 969 / 1,029 / 989 / 975 / 1,005 / 993 / 967 = 6,927. Every
  key carries exactly one printed code, one title and one budget activity (0
  exceptions). Postgres and the lake agree.
- Line numbers are not identities: between consecutive editions 63–68% of the
  earlier edition's keys print a different code (67–72% of keys present in both).
- Within an edition 37–51 (code, account) pairs span several lines: mostly
  advance-procurement pairs in one budget activity; 6–14 span budget activities;
  3–4 span organizations.
- `fct_decade_series` (grain `pe_bli, fy, edition_year`, selection partitioned by
  `pe_bli, account, organization, edition_year, scenario`) has 59,179 rows, 20,781 of
  them era grains. Only F-15's 93 era cells are published, through its hand map.
- The era loader drops the Classified Programs rows (blank Line Number, code
  `9999999999`): 7 per edition, 8 in PB2023, 50 in total, $19.1–23.1B of FY(N−2)
  actuals per edition. Both decade paths already exclude `9999999999`
  (`fct_decade_series.sql:187`, `export_site.py` `_build_decade_citation_rows`).
- `budget_lines.line_number` is NULL on all 67,902 P-1 and 16,561 P-1R rows.
- `era_keys.py:118-120` and ROADMAP #28 call `3010F-AF-L1` a rollup artifact. It is
  F-35 (ATA000) in PB2017–21 and B-21 (B02100) in PB2022–23: 58 rows, $142.566B
  summed over every scenario column.
- `fact_id_workbook` (`export_site.py:74`) hashes `pe_bli`; `fact_id_derived`
  (`:85`) hashes a surface string and key.

## 4. Data model

### 4.1 Postgres — `migrations/021_budget_lines_line_item_code.sql`

```sql
alter table budget_lines add column line_item_code text;
comment on column budget_lines.line_item_code is
  'Budget line code printed in the source P-1/P-1R row (era "Line Item", modern "Budget Line Item"); source-stated, never mapped';
update budget_lines set line_item_code = pe_bli
 where exhibit in ('P-1','P-1R') and pe_bli !~ '^\d{4}[A-Z]-[A-Z]+-L';
```

Modern P-1 rows and all P-1R rows already key by the printed code, so the backfill is
exact. Era P-1 rows are filled by re-running `load_p1_rollup` for PB2017–23 (S1). The
upsert key (`p1_loader.py:200`) does not change, so amounts and fact IDs cannot move.

### 4.2 Loader

- Era mode keeps column I as `line_item_code` instead of discarding it.
- Tripwire: collect the codes, titles and budget activities per era key; raise if any
  has more than one value (0 today).
- S1b, a separate commit: a row with a blank Line Number whose Line Item is
  `9999999999` loads as `pe_bli='9999999999'`, as in modern editions. Footnote rows,
  which also have a blank Line Number, stay skipped.
- `jbooks/export_facts.py` adds `line_item_code` to the budget_lines export;
  `stg_budget_lines` passes it through. Consumers select columns by name, so the extra
  column is inert (S1 proves this with an empty export diff).

### 4.3 dbt seed — `dbt/seeds/p1_era_code_decisions.csv` (the reviewed artifact)

Grain: (`line_item_code`, `account`, `organization`, `first_edition`,
`last_edition`); ranges never overlap. `organization` is blank unless the code spans
organizations within an edition — today codes `10`, `15`, `20`, `30` and `500`.
All columns are varchar in `dbt_project.yml` (the `program_aliases` pattern).
About 1,250–1,300 rows.

| Column | Meaning |
|---|---|
| `decision_id` | `{code}|{account}|{org}|{first}-{last}` |
| `line_item_code`, `account`, `organization` | Chain identity |
| `first_edition`, `last_edition` | 2017–2023 |
| `decision` | `same_program` · `history_only` · `exclude_placeholder` · `exclude_route_unsafe` · `exclude_reused_code` |
| `program_account`, `program_org` | Only for the 13 PB2026 collision codes; pins the page the points join |
| `successor_code`, `successor_account`, `successor_evidence` | Only where a budget book states the continuation; evidence is a citation (document sha + locator + quoted sentence) |
| `n_keys`, `keys_sha256` | sha256 of the sorted `edition|era_key|budget_activity|filed_title` lines reviewed — the drift guard |
| `titles_seen`, `modern_title`, `proposed_rule`, `evidence` | Review context: titles by edition, class (§5.1), title similarity, continuity checks passed/total, selected actuals |
| `decided_on`, `decided_by`, `ruling` | ISO date; `owner` (or `class` for a class-ruled row); `R-DEC-ERA-*` id |
| `note` | Free text |

There is no verdict column: a row exists only once something is decided.

### 4.4 dbt model — `p1_era_line_map` (table, published)

One row per era key (6,927). Key: (`edition`, `account`, `organization`,
`budget_activity`, `era_key`). Columns: `line_item_code`, `filed_title`,
`program_key`, `decision` (`undecided` when no seed row covers the key),
`decision_id`, `keys_sha_ok`, `successor_code`, `source_document_sha256`,
`source_cells`. Published as `data/site/data/p1_era_line_map.parquet` and registered
in `datasets.json` and `/downloads/`.

### 4.5 dbt model — `fct_program_decade_series` (table)

- The same CTEs as `fct_decade_series`, with `program_key = coalesce(map.program_key,
  pe_bli)`. Era rows enter only when `decision in ('same_program','history_only')`.
- **Same grain and aggregation as today.** Grain (`program_key, fy, edition_year`),
  selection partitioned by (`program_key, account, organization, edition_year,
  scenario`). Era lines that share a code are summed across budget activities exactly
  as modern lines that share a code already are. A test proves parity: for PB2024–26
  the new table equals `fct_decade_series` row for row.
- `row_fact_id` still hashes the source row's own `pe_bli` (the era key).
- The account/org split stays pinned to the PB2026 anchor (`collision_slots`), so an
  era account move never creates a new split.
- Extra columns: `map_basis` ∈ {`native`, `era_line_map`, `era_history_only`},
  `source_keys`.
- `fct_decade_series` is not touched. F-15's builder, verify-phase5e and the book-diff
  joins keep reading it.

### 4.6 Research outputs (git-tracked, regenerated by `jbooks era-map propose`)

`data/research/era_map/keys.csv` (6,927 rows of row-level evidence: workbook sha,
row number, columns F/I/J, cost types, title similarity, continuity, $),
`chains.csv` (1,243 chains), `review.csv` (only the chains needing an individual
decision, sorted by dollars).

### 4.7 Code layout

- `src/govbudget/jbooks/era_map.py`: `propose`, `ratify`, `check`; title
  normalization; `ERA_ORG_TO_MODERN`.
- CLI: `jbooks era-map propose|ratify|check`, and `verify-era-map` (§8).

## 5. Classification and review

### 5.1 Classes (per era key; reproducible from `propose`)

Title normalization: casefold; collapse whitespace and punctuation; strip the
suffixes `(MYP)`, `(MIP)`, `(SPACE)`, `(MULTIYEAR)`, `(AP)`, `(AP-CY)`.

| Class | Rule |
|---|---|
| A1 | (code, account) exists in PB2024–26 and the normalized title equals a modern title |
| A2 | Renamed: title Jaccard ≥ 0.5 and at least 2/3 of overlapping-year amount checks within 2× |
| R1 | Title drift beyond A2 |
| R2 | The code exists in PB2024–26 only under another account |
| R3 | The code spans accounts within an era edition — only when (code, account) exists in PB2024–26 and the code is not a PB2026 collision code |
| H | The code is absent from PB2024–26 |
| CR | `FY2017CR` / `FY2018CR` continuing-resolution placeholder lines |
| UNSAFE | `0390D` `O&M` / `RDT&E` (codes that are not route-safe) |

Key counts: A1 5,487 ($681.72B) · A2 65 · R1 161 · R2 113 · R3 64 · H 1,037
($54.10B), of $783.76B era actuals (FY2015–21, nominal, excluding classified).

### 5.2 Class rulings (approved with this spec)

| Ruling | Covers | Decision |
|---|---|---|
| **R-DEC-ERA-SAME** | 803 chains whose every key is A1 | `same_program` — 83.1% of era actual dollars ($651.54B) |
| **R-DEC-ERA-EXCLUDE** | 45 CR placeholder chains ($0 selected actuals) and the 2 `0390D` `O&M`/`RDT&E` chains | `exclude_placeholder`, `exclude_route_unsafe` |
| **R-DEC-ERA-HISTORY** | 271 era-only chains with no title drift after normalization | `history_only` — data only, no page (R-DEC-FAM-ERAONLY) |

Total: 1,121 of 1,243 chains. The two F-15 era-only chains (F0150P, F015E0) fall
under R-DEC-ERA-HISTORY; F015E0 also gets a stated successor (§5.4).

### 5.3 Individual decisions (Claude pre-fills, owner approves)

About 122 chains: 95 containing R1/R2/R3 keys, 19 A2-only chains, 8 era-only chains
whose normalized title drifts — plus range or organization splits where a chain needs
one. Each row in `review.csv` shows the titles by edition, the modern title, the
accounts, the continuity checks, the dollars and a pre-filled `proposed_decision` with
its reason:

- R2/R3 (account moves, e.g. Space Force 3020F/3021F → 3022F, Columbia 1045 in
  1611N/1612N) → `same_program`, with `program_account` set when the code is a PB2026
  collision code.
- R1 (renames, e.g. LX(R) → LPD Flight II, OHIO Replacement → COLUMBIA, UH-1N
  Replacement → MH-139A) → `same_program` when continuity holds, or a range split.
- A code reused for a different program (e.g. `50` in 0300D: "Indian Financing Act"
  → "DTRA Cyber Activities") → range split, earlier range `exclude_reused_code`.
- Drifting era-only chains → `history_only` or `exclude_reused_code`.

Review happens in batches of about 25, largest dollars first. Each batch is shown as
a readable page (a private artifact the owner can open on a phone) and approved or
amended in chat. `ratify` writes the batch with `decided_by=owner`, `decided_on` and
`ruling=R-DEC-ERA-B<n>`. `check` lists undecided chains and stale `keys_sha256`.

### 5.4 Stated successors (R-DEC-FAM-ERAONLY)

`propose` searches the PB2024–26 J-book XML for every era-only code. Only 6 of the
searchable era-only codes appear at all (`5600D15603`, `5840A05133`, `F0150P`,
`F015E0`, `V022A0`, `COVID19`). A `successor_code` is recorded only where the text
states the continuation, with the sentence as evidence. Known cases: JLTV
`5600D15603` → `D15610` (PB2026 R-2), F015E0 → F015EX (PB2026 AF Aircraft
Procurement Vol I P-40: Lot 1 aircraft "were purchased with procurement funds
(F015E0, Line #3)"). Successors are recorded, not displayed, in this piece.

## 6. Export and site

### 6.1 Decade tier (`export_site.py`, `_build_decade_citation_rows`)

- Read `fct_program_decade_series` instead of `fct_decade_series`; key the source
  rows by (`program_key`, edition, amount_type) through the map. Modern rows are
  unchanged.
- **Era leaf identity.** `w_fid` is computed from the source row's own `pe_bli` (its
  era key), so every existing era fact ID (F-15's 72 A1 leaves) is reproduced, not
  re-minted. `budget_lines_decade` rows keep `pe_bli` = era key; the dataset schema
  does not change (readers join `p1_era_line_map` for the program key).
- **Citation `pe_bli`** for an era leaf is the bare printed code (`line_item_code`),
  never `program_key`, so `program_pdf_receipts` re-checks every era cell against
  column I. (In citations `pe_bli` means "the code printed at the cited cell"; in
  `budget_lines_decade` it means the lake row identity. Both meanings are documented
  in the dataset descriptions.)
- **Era sums of several lines** (advance-procurement pairs, cross-budget-activity
  lines) get a new surface: `fact_id_derived("decade_era_map", f"{program_key}|{edition}",
  amount_type)` with formula `sum(budget_lines.amount_thousands where
  era_line_map='{program_key}' and amount_type={at} and edition={edition})`. It passes
  `additive_budget_formula`'s grammar and is not on F-15's reuse list, so F-15's 27
  legacy multi-input cells keep their own receipts. Inputs on this new surface are
  sorted by fact ID so the receipt is byte-stable; existing surfaces keep their order.
- Only `program_key`s that have a program page get points. `history_only` rows stay
  in the program table and the map; they are not exported to any page.
- Breakdown rows set `pe_bli` to the page slug (`breakdown-table.tsx` links every
  breakdown `pe_bli` to `/program/`; an era key would be a dead link).
- Hazards the plan must test: suffixed collision `program_key`s must never reach the
  citation `pe_bli` or a `fact_id_workbook` call; the derived-ID mirror near
  `export_site.py:15017`; the parquet row-order moves listed in §10.

### 6.2 Fences — surfaces that must not change in this piece

| Surface | Why it would change | Fence | Proof |
|---|---|---|---|
| `/families/f-15/` | `f15-family-data.ts:107` copies every `decade_series` point; it would gain about 45 era facts (F01500 21, F15EWS 15, F015EX 9) and exceed its page-weight ceiling | `loadRecord` keeps only the editions it showed before (R-1 all; P-1 PB2024–26) | Normalized page snapshot equal to the S0 baseline |
| Lineage funding lines | A lineage family would gain era points (e.g. 837170's FY2018–20 requests) whose labels do not match their fact `pe_bli`; verify-lineage legs d/i6 fail | Funding lines read only `map_basis = native` points | verify-lineage passes unchanged |
| `/years/` matrix | `years_matrix.json` is 3,178,320 B against a 4,194,304 B cap the code says must never be raised | Measure at S4. If era points would breach the cap, `/years/` keeps native rows only and the gap is filed; otherwise it gains era points as an expected difference | Cap respected; recompute gate passes |
| `/methodology/` | The copy rewrite (§6.4) must fit 253 B gzip of headroom (`gates/build.mjs:647`) | Rewrite byte-neutral, trimming elsewhere on the page | Build gate passes without a raised ceiling |

Expected, not fenced: P-1 program pages that had no positive content may become
indexable once they have era points; the sitemap gate derives this.

### 6.3 Receipts

Run `program_pdf_receipts` over the full corpus. The PB2017–23 P-1 PDFs are already
in `budget_pdf_sources.json` and hosted. Publish era receipt completeness per edition.
Era shipbuilding cost-type rows (14–19 N/L/E rows per edition through
`cost_row_match`) are expected to be workbook-only until the matcher is extended;
this is disclosed on the methodology page, not hidden.

### 6.4 Copy

- `/methodology/` (`page.tsx` near line 1770, "comparisons stop at the PB2024
  boundary") is rewritten to say procurement history now reaches PB2017 through
  reviewed printed-code decisions. It keeps two statements true: era book diffs still
  cover R&D only, and the site never fuzzy-matches renamed programs — renames are
  reviewed decisions on the printed code, each dated and published in
  `p1_era_line_map`.
- Map figures (class-ruled, individual, excluded, $) are rendered from the export, not
  typed, and checked by a datatruth leg.
- `corpus.ts` changes a comment only; its visible string stays true.

### 6.5 F-15 corrections (S5, a deliberate re-stamp)

- F015E0's matrix label "F-15e (legacy line)" becomes a label that states only what
  the book says, e.g. "F-15EX (FY2020 line, filed as “F-15e”)", with a scope note
  quoting the PB2026 P-40 sentence and its citation. The coverage note that legacy
  lines carry no variant allocation gains the exception "except where a budget book
  states one (F015E0)".
- A coverage note: the totals exclude classified funding and military construction.
- The F-15 golden pin is re-captured after this commit; the diff must be exactly
  these strings (plus any count of notes the payload records).

### 6.6 Record corrections

- `era_keys.py:118-120`: the docstring says rollup; correct it (F-35 then B-21).
- ROADMAP #28: a dated correction note under the entry (entries are never reworded).

## 7. Error handling

| Case | Behavior |
|---|---|
| An era key prints more than one code, title or budget activity | Loader raises (0 today) |
| Several era lines share one code in an edition | Summed under the program key, exactly as `fct_decade_series` sums modern lines; new `decade_era_map` formula |
| A line number reused across editions | Irrelevant: decisions key on the printed code; era keys are per edition |
| A code reused for a different program | Range split; the earlier range is `exclude_reused_code` |
| Rename | `same_program` with a dated owner decision; receipts show the filed title |
| Account move | A non-collision code keeps one page summing its accounts, as modern pages do; a collision code must set `program_account` (dbt test rejects an unpinned split) |
| Code spanning organizations (10, 15, 20, 30, 500) | Decided per organization; a dbt test fails if an un-split decision covers keys from more than one organization in one edition |
| An era key with no decision | `undecided`; never exported; `verify-era-map` fails strict before the exporter change ships |
| Keys or titles changed after review | `keys_sha256` mismatch fails `era-map check` and `verify-era-map`; re-review required |
| Classified `9999999999` | Loaded (S1b), never mapped, never a page point |
| CR placeholders, route-unsafe codes | Class-ruled exclusions |
| P-1R rows | Context only, never counted; map cross-check (1,645 of 1,650 era P-1R triples; 5 known PB2017 Army exceptions allow-listed) |
| A member of F-15 missing from an era edition | F-15's existing `partial` / `missing_programs` logic, unchanged |
| Mart/lake drift during export | The existing guard raises |

## 8. Verification

| Id | Check | Where | Fails on |
|---|---|---|---|
| V1 | **No-write loader diff** before any DB write | S1 script | Today's loader, parsing PB2017–23 in memory, differs from Postgres in any amount, title, cell or key |
| V2 | Loader unit tests | `tests/jbooks/test_p1_loader_era.py` with a fixture workbook | Code not captured; advance-procurement pair mishandled; classified row; section header; multi-code tripwire not raised |
| V3 | dbt tests | `assert_p1_era_map_{grain_unique,complete,no_undecided,one_code,decisions_no_overlap,org_split}.sql`, `assert_program_decade_{native_equals_line,conservation,grain_unique,collision_pinned}.sql` | Coverage ≠ 6,927; undecided rows (strict before S5); PB2024–26 program rows ≠ `fct_decade_series`; Σ program grain ≠ Σ mapped line grain per edition and kind; a split outside the PB2026 anchor |
| V4 | **`verify-era-map`** CLI, added to `_ASSEMBLY_PHASES` in `verify_phase5.py` with `_VERDICT_RE` extended | `src/govbudget/verify_era_map.py` | (a) re-read of the 7 era P-1 workbooks among `data/site/workbooks`: key set ≠ 6,927, printed code ≠ `line_item_code`, title ≠ reviewed; (b) undecided or stale decisions; (c) the map's F-15-code rows ≠ `ERA_MEMBERS` (31 rows: same codes, budget activities and titles); (d) any `budget_lines_decade` row whose fact ID does not recompute with `fact_id_workbook` from its own row; (e) published map parquet ≠ dbt map; (f) F-15 history sha ≠ pin |
| V5 | **F-15 identity** | `tests/test_f15_era_identity.py` | `build_program_matrix` on a fresh-state registry (F-15's receipts removed) with injected era-map receipts ≠ golden bytes; a negative test with an allowed-formula competitor does **not** change the bytes (proves the guard is live) |
| V6 | **Fact stability** | S4 proof script | Any S0 fact ID missing, or with a different amount or inputs, outside §10 |
| V7 | Receipts | `program_pdf_receipts` audit | F-15 default ≠ 67/67; any complete receipt turns incomplete; era completeness not reported per edition |
| V8 | Site gates | `npm run verify` | program-skeleton, years-matrix, linkgraph, page weight (ceilings re-derived only with measured numbers; F-15 and methodology unchanged), sitemap |
| V9 | Link coverage | baseline captured at S0 | Source-linked share < 100% for budget figures; a figure loses a complete PDF receipt |
| V10 | Release | `verify-phase5`, `verify-phase5b1`, `verify-lineage`, deploy live check | Any FAIL |

**The proof of "nothing else changed" is a fresh A/B export**: old code and new code
exported against the same pinned lake snapshot into two scratch folders, diffed with
build timestamps masked. An idempotent re-run on a copy of `data/site` is not proof
(it hides fresh-state effects, and the F-15 call already re-serializes
`datasets.json`).

## 9. Rollout (each step verifiable on its own)

| Step | Change | Verified by |
|---|---|---|
| **S0** Baseline | Pin a lake snapshot (duckdb file, `parquet/jbooks`, `data/site`; record shas). Golden F-15 fixtures; normalized F-15 page snapshot from a fresh build at the base commit (never `site/out`). Link-coverage baseline. Docstring and #28 corrections | Pytest green; no `data/site` change |
| **S1** Loader | V1 first. Migration 021 with the modern backfill; loader capture and tripwire; export_facts and stg columns; re-run `load_p1_rollup` for PB2017–23 only, inside a transaction with a pre/post snapshot of every existing column | All 84,463 P-1/P-1R rows equal on every existing column; 6,927 keys with exactly one code; fresh export diff empty |
| **S1b** Classified era rows | Load the 50 blank-line `9999999999` rows | Lake +50 rows; export diff empty |
| **S2** Map | `era-map propose`; class rulings applied; individual batches reviewed and ratified; `p1_era_line_map`; V3 map tests; V4 legs a–c | dbt tests pass including no-undecided; the map's F-15 rows equal `ERA_MEMBERS` |
| **S3** Program table | `fct_program_decade_series` and its tests | Native equality; conservation; exporter unchanged → empty export diff |
| **S4** Era points | Decade tier changes (§6.1), fences (§6.2), map dataset, methodology copy, gates re-derived | V5, V6, V8; fresh A/B diff equals §10; measured page gain ≈ 800 |
| **S5** F-15 corrections | §6.5; the owner signs off the exact strings; re-pin | Diff equals the approved strings |
| **S6** Receipts and release | Full-corpus receipts, per-edition audit, V7, V9, `verify-era-map` in the assembly; one deploy via `./scripts/launch/deploy.sh` | V10 green; live check passes |

S2's individual review is the critical path: S4 cannot ship until no chain is
undecided. The class-ruled chains are ready as soon as this spec is approved.

## 10. Expected differences (what the S4 A/B diff must equal)

- `program_details/<slug>.json` for about 800 procurement pages: new era decade
  points. Pages that flip from zero-content to indexable: sitemap entries.
- `citations.json`, cite shards, `citations.parquet`: new era leaf and
  `decade_era_map` entries. F-15's 72 A1 era-leaf entries are now minted by the decade
  tier: their `pe_bli` changes from null to F01500 / F015EX / F15EWS and their
  `retrieved_at` from the space form to the `T` form (seven edition timestamps). Every
  other field is equal. F-15's reported `added_citations` falls by 72. These 72 rows
  move position in `citations.parquet` and `budget_lines_decade.parquet`.
- `budget_lines_decade.parquet`: new era rows (schema unchanged).
- New `p1_era_line_map.parquet`; `datasets.json` and `/downloads/` list it; the
  manifest counts change accordingly.
- Workbook-cell previews for the new era leaves.
- `/years/` either unchanged (fenced) or gains era points, decided by measurement.
- Unchanged: `f15_funding_history.json`, its 69 breakdowns, `/families/f-15/`,
  lineage funding lines, book diffs, `/feed/`.

## 11. Risks and filed follow-ups

1. **Shared mutable lake.** All proofs run on the S0 snapshot; each proof note records
   its lake sha.
2. **The S1 database write** uses today's loader on old editions. V1 must be clean
   first; the re-run is transactional and aborts on any change to an existing column.
3. **Duplicate receipts.** Era sums for F-15 lines exist twice (program-page receipt
   and F-15 cell receipt, same inputs and amount), deliberately, for byte identity.
   Unifying them is a later re-stamp.
4. **Size.** About 15–16k new era points and 16–21k leaf citations against 125,409
   today; `citations.json` is 83.9 MB and grows. Page weight and build time are
   re-measured, never assumed. Per-point cost on program pages is about 2.2 KB raw /
   0.22 KB gzip; P-1 pages stay under 40% of their ceiling.
5. **Receipt completeness.** Era shipbuilding rows will be mostly workbook-only.
   Disclosed per edition.
6. **False continuity.** Mitigated by owner review of every non-mechanical chain, the
   drift guard and the published map.
7. **Review stall.** About 122 decisions in batches of 25, largest dollars first.
8. File as ROADMAP items: PB2026 drops the real `0390D` Chem Demil `O&M`/`RDT&E`
   lines ($1.09B FY2024 actuals) as section headers; dead v1 receipt files
   (`budget_pdf_receipts.py:393-472`, 256 shipped shards) need owner sign-off to
   remove; `search_aliases.csv` still holds two routes #55 corrected.
