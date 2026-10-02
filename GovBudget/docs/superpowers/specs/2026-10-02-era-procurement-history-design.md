# Procurement History Before FY2024 — Families Piece 1

**Date:** 2026-10-02 (revised the same day after an independent review against the code)
**Status:** Draft for owner review. Approving this spec also approves the three class
rulings in §5.2 (R-DEC-ERA-SAME, R-DEC-ERA-EXCLUDE, R-DEC-ERA-HISTORY).
**Parent:** [2026-10-02-platform-families-overview.md](2026-10-02-platform-families-overview.md)
(owner decisions R-DEC-FAM-UNIT, -NAME, -REVIEW, -ERAONLY).
**Depends on:** the PB2017–PB2026 decade lake (Phase 5E), `fct_decade_series`,
`budget_lines_decade`, the v2 PDF receipt pipeline (`program_pdf_receipts.py`), the
F-15 family history (`f15_funding_history.py`).
**Evidence base:** read-only measurements at main `dc801fdb` (2026-10-02), re-checked
adversarially against the raw workbooks, Postgres, DuckDB and the code, then reviewed
for feasibility against the exporter, the gates and the source books. Scratch outputs
live in the session scratchpad (`era_map/`, `designverify/`, `specreview/`).

---

## 1. Goal

Every procurement program page whose budget line code is printed in a PB2017–PB2023 P-1
workbook shows those editions' points (FY(N−2) actuals, FY(N−1) enacted, FY(N)
request), each cited to its own workbook cell and, where the PDF matcher can find it,
a highlighted location in the same edition's P-1 PDF. Today every procurement page
outside F-15 starts at PB2024 (FY2022 actuals), while R&D pages reach back to PB2017.

**Success criteria**
- About 880 procurement program pages gain era points: about 800 of the 891 pages with
  PB2026 lines (about 581 of them all seven editions), plus about 80 of the 89
  history-only procurement pages (ROADMAP #28, e.g. A01000, A-10). The three class
  rulings alone reach most of them; the individual decisions bring the rest. The
  classified aggregate page never gains points. Exact counts are measured at S4 and
  recorded in the ROADMAP.
- Every published figure that exists before this piece keeps its fact ID, amount and
  inputs. The only changes to existing citations are those listed in §10.
- `json/f15_funding_history.json` is byte-identical through the data changes
  (S0–S4). It changes only in the separate F-15 correction (S5), whose exact changes
  the owner approves.
- Budget figures stay 100% source-linked, and no figure that has a complete PDF
  receipt today loses it (overview §7), measured by a committed tool.
- A release gate (`verify-era-map`, in the `verify-phase5` assembly) fails if any era
  line is undecided, any decision went stale, or any published era figure does not
  recompute from its own workbook row.

## 2. Non-goals

- No pages for discontinued code chains (R-DEC-FAM-ERAONLY). They live in the map and
  the program table only.
- No family registry, evidence engine, template or new family page (pieces 2–4).
- No re-keying of `pe_bli` in the lake; no published fact ID changes.
- No era book diffs, no `/feed/` re-ranking (`assert_book_diff_no_era_procurement.sql`
  stays). No quantities, PB2027, PB2012–16 or service J-book backfill.
- No change to the F-15 page's layout or workspaces, to lineage funding lines, or to
  `/years/` (§6.2). `/years/` keeps its procurement rows from PB2024 on; carrying era
  procurement there needs the matrix sharded first (filed, §11).
- No fix for PB2026's dropped `0390D` Chem Demil `O&M`/`RDT&E` lines (filed, §11).

## 3. What is true today

- Every PB2017–23 P-1 workbook has `Line Number` in column F and the budget line code
  in column I, headed "Line Item" (PB2024+: "Budget Line Item"). Column I is filled on
  all 6,927 era keys.
- `p1_loader.py:116-124` detects era layout, drops the code and keys the row by line
  number; `:152-159` mints `{account}-{org}-L{line}` (`era_keys.py:72-86`);
  `:140-141` skips any row with a blank Line Number. `load_p1_rollup` parses and
  writes in one call: it opens its own connection (~:187) and commits on exit; its
  `ON CONFLICT` updates only amount, title, source document, sheet and cells. The CLI
  caller (`cli.py:145-180`) catches every exception per workbook and prints FAILED.
- Era keys per edition: 969 / 1,029 / 989 / 975 / 1,005 / 993 / 967 = 6,927. Every
  key carries exactly one printed code, one title and one budget activity. Postgres
  and the lake agree. Each key is one or more `budget_lines` rows, one per amount
  column (2,901–13,377 era P-1 rows per edition).
- Line numbers are not identities: between consecutive editions 63–68% of the earlier
  edition's keys print a different code (67–72% of keys present in both).
- Within an edition 37–51 (code, account) pairs span several lines: mostly
  advance-procurement pairs in one budget activity; 6–14 span budget activities; 3–4
  span organizations.
- `fct_decade_series` is unique on (`pe_bli, account, organization, fy, edition_year`),
  with account/organization non-null only for the 13 PB2026 collision codes (10
  reused across accounts; `20`, `30`, `500` reused across organizations in 0300D). It
  has 59,179 rows, 20,781 of them era grains; only F-15's 93 era cells are published,
  through its own hand map.
- The era loader drops the Classified Programs rows (blank Line Number, code
  `9999999999`): 50 workbook rows (7 per edition, 8 in PB2023), $19.1–23.1B of
  FY(N−2) actuals per edition. Both decade paths already exclude `9999999999`.
- `budget_lines.line_number` is NULL on all 67,902 P-1 and 16,561 P-1R rows.
- `era_keys.py:118-120` and ROADMAP #28 call `3010F-AF-L1` a rollup artifact. It is
  F-35 (ATA000) in PB2017–21 and B-21 (B02100) in PB2022–23: 58 rows, $142.566B summed
  over every scenario column.
- `fact_id_workbook` (`export_site.py:74`) hashes `pe_bli`; `fact_id_derived` (`:85`)
  hashes a surface string and key.
- The exporter's decade tier builds `decade_grains` (a positional 9-tuple) and
  `decade_series_by_pe` entries `{fy, v, fid, edition, basis, measure}`, which are
  serialized into every program sidecar and also feed lineage funding lines
  (~:10739) and `/years/` (~:17279). Page scope is PB2026 lines plus the decade-only
  pages (`scope_pes`, ~:3059). The production `export-site` CLI always runs
  `program_pdf_receipts` after the export (`cli.py:2449-2455`).

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
exact. Era P-1 rows are filled by the S1 re-run.

### 4.2 Loader

- Split `load_p1_rollup` into a pure `parse_p1_rollup(xlsx, edition)` that returns the
  rows it would write, and a writer that takes a caller-owned connection. V1 diffs the
  parse against Postgres; S1 runs the writer inside a transaction it controls.
- Era mode keeps column I as `line_item_code`. `line_item_code` is added to both the
  `INSERT` column list and the `ON CONFLICT DO UPDATE SET` list (every era row already
  exists, so only the update branch runs on the re-run). The upsert key does not
  change, so amounts and fact IDs cannot move.
- Tripwire: if any era key has more than one code, title or budget activity, the parse
  raises. S1 runs from a dedicated script, not through the CLI's catch-all, so the
  tripwire cannot be swallowed.
- S1b, a separate commit: a row with a blank Line Number whose Line Item is
  `9999999999` loads as `pe_bli='9999999999'`, as in modern editions. Footnote rows,
  which also have a blank Line Number, stay skipped.
- `jbooks/export_facts.py` adds `line_item_code` to the budget_lines export;
  `stg_budget_lines` passes it through. Consumers select columns by name, so the extra
  column is inert (S1 proves this with an empty export diff).

### 4.3 dbt seed — `dbt/seeds/p1_era_code_decisions.csv` (the reviewed artifact)

Grain: (`line_item_code`, `account`, `organization`, `first_edition`,
`last_edition`); ranges never overlap. `organization` is blank unless the code spans
organizations within an edition (today `10`, `15`, `20`, `30`, `500`). All columns are
varchar in `dbt_project.yml` (the `program_aliases` pattern).

| Column | Meaning |
|---|---|
| `decision_id` | `{code}|{account}|{org}|{first}-{last}` |
| `line_item_code`, `account`, `organization` | Chain identity |
| `first_edition`, `last_edition` | 2017–2023 |
| `decision` | `same_program` · `history_only` · `exclude_placeholder` · `exclude_route_unsafe` · `exclude_reused_code` |
| `program_account`, `program_org` | Set for every chain on one of the 13 PB2026 collision codes: the PB2026 account/organization whose page the points join. Blank otherwise |
| `successor_code`, `successor_account`, `successor_evidence` | Only where a budget book states the continuation (§5.4). `successor_code` is the P-1 code as printed in PB2024–26 |
| `n_keys`, `keys_sha256` | sha256 of the sorted `edition|era_key|budget_activity|filed_title` lines reviewed — the drift guard |
| `titles_seen`, `modern_title`, `proposed_rule`, `evidence` | Review context: titles by edition, class (§5.1), title similarity, continuity checks passed/total, selected actuals |
| `decided_on`, `decided_by`, `ruling` | ISO date; `owner`; the `R-DEC-ERA-*` id (a class ruling or a review batch) |
| `note` | Free text |

There is no verdict column: a row exists only once something is decided.

### 4.4 dbt model — `p1_era_line_map` (table, published)

One row per era key (6,927). Key: (`edition`, `account`, `organization`,
`budget_activity`, `era_key`). Columns: `line_item_code`, `filed_title`,
`program_key`, `program_account`, `program_org`, `decision` (`undecided` when no seed
row covers the key), `decision_id`, `ruling`, `keys_sha_ok`, `successor_code`,
`source_document_sha256`, `source_cells`.

Published as `data/site/data/p1_era_line_map.parquet`. Shipping it requires: a
`_DATASET_SCOPES` row-grain sentence (the exporter refuses a parquet without one); the
name added to `site/src/lib/dataset-names.ts` (the `/data/` page throws if
`datasets.json` and `DATASET_NAMES` disagree); a `/data/` card and a canned Explorer
query in `components/explorer.tsx` (gate 24, datatruth legs a–c). It goes on the
uncited ledger: its rows are decisions, not money.

A small `json/era_map_summary.json` (chains and dollars by decision and ruling,
receipt completeness per edition) is exported for the site to render (§6.4).

### 4.5 dbt model — `fct_program_decade_series` (table)

- The same CTEs as `fct_decade_series`. Era rows enter only when `decision in
  ('same_program','history_only')`.
- **`program_key` is always the bare printed code.** Grain: (`program_key`,
  `account`, `organization`, `fy`, `edition_year`), with account/organization
  non-null only for the 13 PB2026 collision codes — exactly today's uniqueness key.
  For an era row on a collision code, `account`/`organization` are the pinned
  `program_account`/`program_org`, not the row's own era values. The page split comes
  only from account/organization; no suffixed key exists anywhere.
- **Same aggregation as today.** Era lines that share a code are summed across budget
  activities and line numbers exactly as modern lines that share a code already are.
- `row_fact_id` still hashes the source row's own `pe_bli` (the era key).
- Extra columns: `map_basis` ∈ {`native`, `era_line_map`, `era_history_only`},
  `source_keys` (the era keys summed).
- **Parity:** every `map_basis='native'` row — all editions, including the 22,008
  PB2017–23 R-1 grains — equals `fct_decade_series` row for row. The book-diff join
  and the derived-ID mirror (`export_site.py` ~:15015) depend on it.
- `fct_decade_series` is not touched. F-15's builder, verify-phase5e and
  `fct_book_diff` keep reading it.

### 4.6 Research outputs (git-tracked, regenerated by `jbooks era-map propose`)

`data/research/era_map/keys.csv` (6,927 rows of row-level evidence: workbook sha,
row number, columns F/I/J, cost types, title similarity, continuity, $),
`chains.csv`, `review.csv` (only chains needing an individual decision, sorted by
dollars), `counts.json` (the exact class and chain counts the rulings cover).

### 4.7 Code layout

- `src/govbudget/jbooks/era_map.py`: `propose`, `ratify`, `check`; title
  normalization; class evaluation; successor search; `ERA_ORG_TO_MODERN`.
- `src/govbudget/verify_era_map.py` and the `verify-era-map` CLI (§8, V4).
- `src/govbudget/link_coverage.py` and `govbudget link-coverage --site-dir <dir>
  [--baseline <file>]` (§8, V9).
- CLI: `jbooks era-map propose|ratify|check`.

## 5. Classification and review

### 5.1 Classes (per era key; reproducible from `propose`)

Title normalization: casefold; collapse whitespace and punctuation; strip the
suffixes `(MYP)`, `(MIP)`, `(SPACE)`, `(MULTIYEAR)`, `(AP)`, `(AP-CY)`. For the five
organization-spanning codes, "exists in PB2024–26" compares (code, account,
organization).

Rules are evaluated in this order; the first that matches wins:

| Order | Class | Rule |
|---|---|---|
| 1 | CR | `FY2017CR` / `FY2018CR` continuing-resolution placeholder lines |
| 2 | UNSAFE | `0390D` `O&M` / `RDT&E` (not route-safe codes) |
| 3 | R3 | The code spans accounts within an era edition — only when (code, account) exists in PB2024–26 and the code is not a PB2026 collision code |
| 4 | A1 | (code, account) exists in PB2024–26 and the normalized title equals a modern title |
| 5 | A2 | Renamed: title Jaccard ≥ 0.5 and at least 2/3 of overlapping-year amount checks within 2× |
| 6 | R1 | Title drift beyond A2 |
| 7 | R2 | The code exists in PB2024–26 only under another account (or organization) |
| 8 | H | The code is absent from PB2024–26 |

Research-pass key counts (CR and UNSAFE counted inside H): A1 5,487 ($681.72B) · A2 65
· R1 161 · R2 113 · R3 64 · H 1,037 ($54.10B), of $783.76B era actuals (FY2015–21,
nominal, excluding classified). `propose` recomputes them under the order above and
writes `counts.json`.

### 5.2 Class rulings (approved with this spec)

Rulings are rules; they cover whatever chains meet them when `propose` runs. Chains
are keyed by (code, account), split by organization for the five
organization-spanning codes (1,253 chains in the research pass).

| Ruling | Covers | Decision | Research-pass size |
|---|---|---|---|
| **R-DEC-ERA-EXCLUDE** (takes precedence) | CR placeholder chains; `0390D` `O&M`/`RDT&E` chains | `exclude_placeholder`, `exclude_route_unsafe` | 45 + 2 chains, $0 selected actuals |
| **R-DEC-ERA-SAME** | Chains whose every key is A1. For a collision code, `program_account`/`program_org` = the chain's own account/organization; a chain whose account/organization has no PB2026 page (e.g. `20`-DSS, `30`-DODEA, `500`-DCMA) leaves the ruling for individual review | `same_program` | about 813 chains, about 83% of era actual dollars ($651.54B on the unsplit count) |
| **R-DEC-ERA-HISTORY** | Era-only chains with no title drift after normalization | `history_only` — data only, no page (R-DEC-FAM-ERAONLY) | about 271 chains |

Class-ruled rows are recorded `decided_by=owner` with the ruling id. The two F-15
era-only chains (F0150P, F015E0) fall under R-DEC-ERA-HISTORY.

### 5.3 Individual decisions (Claude pre-fills, owner approves)

About 120–125 chains: those containing R1/R2/R3 keys (95), A2 chains without R keys
(19), era-only chains whose normalized title drifts (8), and class-ruled chains that
left their ruling (collision orgs without a page). Each `review.csv` row shows the
titles by edition, the modern title, the accounts, the continuity checks, the dollars
and a pre-filled `proposed_decision` with its reason:

- R2/R3 (account moves, e.g. Space Force 3020F/3021F → 3022F, Columbia 1045 in
  1611N/1612N) → `same_program`, with `program_account` set for collision codes.
- An organization rename (e.g. `20`: DSS → DCSA) → `same_program` with `program_org`.
- R1 (renames, e.g. LX(R) → LPD Flight II, OHIO Replacement → COLUMBIA, UH-1N
  Replacement → MH-139A) → `same_program` when continuity holds, or a range split.
- A code reused for a different program (e.g. `50` in 0300D: "Indian Financing Act"
  → "DTRA Cyber Activities") → range split, earlier range `exclude_reused_code`.
- Drifting era-only chains → `history_only` or `exclude_reused_code`.

Review happens in batches of about 25, largest dollars first. Each batch is shown as
a private page the owner can open on a phone and is approved or amended in chat.
`ratify` writes the batch with `decided_by=owner`, `decided_on` and
`ruling=R-DEC-ERA-B<n>`. `check` lists undecided chains and stale `keys_sha256`.

### 5.4 Stated successors (R-DEC-FAM-ERAONLY)

`propose` searches the J-book XML on disk for each era-only code: first the literal
code, then the code without a 4-digit account prefix (Army codes print as
`5600D15603` in the P-1 but `D15603` in the books); it records which form matched.
Only PB2026 service books are on disk (PB2024–25 have none), so service codes are
searched in PB2026 only. A `successor_code` is recorded only where the text says the
line continues under another code; a mention alone is not enough.

Known case: JLTV. Era code `5600D15603` (2035A) → `successor_code=5731D15610`,
`successor_account=2035A`. Evidence: PB2026 Army Other Procurement BA1 P-40,
justification for line 5731D15610, PDF p.100 of "Other Procurement - BA1 - Tactical &
Support Vehicles.pdf" (sha `184228d8…`): "NOTE: This budget line D15610 is a
continuation of an existing effort where prior year funds through FY 2020 are
reflected under the previous budget line D15603." That PDF is not hosted, so the
evidence is recorded as document sha + page + XML path, and successors are recorded,
not displayed, in this piece. A dbt test checks that every successor exists in
PB2024–26 under its account.

F015E0 has no successor: its source says its aircraft were funded *outside* the
F015EX exhibit, which is not a continuation. Its corrected label is §6.5's job.

## 6. Export and site

### 6.1 Decade tier (`export_site.py`, `_build_decade_citation_rows`)

- Read `fct_program_decade_series`. If it is missing while `fct_decade_series` exists,
  the exporter raises (no silent fallback); the exporter test fixtures that build only
  `fct_decade_series` are updated.
- Source rows are matched to grains through the map: by (`program_key`, pinned
  account/organization, edition, amount_type), never by the era row's own
  account/organization, so a pinned chain (e.g. DSS → DCSA) neither raises the
  source-count guard nor drops silently. Modern rows are matched as today.
- **Era leaf identity.** `w_fid` is computed from the source row's own `pe_bli` (its
  era key), so every existing era fact ID (F-15's 72 A1 leaves) is reproduced, not
  re-minted. `budget_lines_decade` rows keep `pe_bli` = era key; the dataset schema
  does not change (readers join `p1_era_line_map` for the program key).
- **Citation `pe_bli`** for an era leaf is the bare printed code (`line_item_code`),
  so `program_pdf_receipts` re-checks every era cell against column I. In citations
  `pe_bli` means "the code printed at the cited cell"; in `budget_lines_decade` it
  means the lake row identity. Both meanings are documented in the dataset scopes.
- **Era sums of several lines** (advance-procurement pairs, cross-budget-activity
  lines) get a new surface: `fact_id_derived("decade_era_map",
  f"{program_key}|{account}|{organization}|{edition}", amount_type)` (blank
  account/organization for non-collision codes) with formula `sum(budget_lines.amount_thousands
  where era_line_map='{program_key}'[ and account=…][ and organization=…] and
  amount_type={at} and edition={edition})`. It passes `additive_budget_formula`'s
  grammar and is not on F-15's reuse list, so F-15's 27 legacy multi-input cells keep
  their own receipts. Inputs on this surface are sorted by fact ID so the receipt is
  byte-stable; existing surfaces keep their order.
- Points go only to pages in today's page scope (PB2026 lines plus decade-only
  pages). `history_only` rows stay in the program table and the map.
- Breakdown rows set `pe_bli` to the page slug (`breakdown-table.tsx` links every
  breakdown `pe_bli` to `/program/`; an era key would be a dead link).
- **Era marker without new fields.** The decade tier records the fact IDs of the
  grains it adds through the map in an out-of-band set passed to the fenced emitters
  (§6.2). The marker is never serialized: `decade_grains` and the sidecar
  `decade_series` entries keep their exact shape, and native entries stay
  byte-identical.

### 6.2 Fences — surfaces that must not change in this piece

| Surface | Why it would change | Fence | Proof |
|---|---|---|---|
| `/families/f-15/` | `f15-family-data.ts:107` copies every `decade_series` point; it would gain about 45 era facts (F01500 21, F15EWS 15, F015EX 9) and exceed its page-weight ceiling | `loadRecord` keeps only the editions it showed before (R-1 all; P-1 PB2024–26) | Normalized page snapshot equal to the S0 baseline |
| Lineage funding lines | A lineage family would gain era points (e.g. 837170's FY2018–20 requests) whose labels do not match their fact `pe_bli`; verify-lineage leg d fails | `_emit_lineage` skips grains in the era set | verify-lineage passes; funding lines byte-identical |
| `/years/` | Built from `decade_grains`; era points would add about 0.75 MB (≈3.9–4.0 MB against a 4,194,304 B cap that must not be raised, leaving no room for PB2027) and fail years-matrix leg g (its source rows' `pe_bli` is the era key) | `_emit_years_matrix` skips grains in the era set | `years_matrix.json` byte-identical; years-matrix gate unchanged |
| `/methodology/` | Live weight is 161,166 / 45,270 gzip against 162,000 / 45,400 (about 130 B gzip of headroom; the build stamp still says 45,147) | One sentence replaced at equal length plus a link (§6.4); everything else goes elsewhere | Build gate passes with the re-measured stamp and no raised ceiling |

### 6.3 Receipts

The `export-site` CLI reruns `program_pdf_receipts` over the full corpus, so receipts
are part of every export proof (S4). The PB2017–23 P-1 PDFs are already in
`budget_pdf_sources.json` and hosted. Era shipbuilding cost-type rows (14–19 N/L/E rows
per edition through `cost_row_match`) are expected to be workbook-only until the
matcher is extended; this is disclosed per edition, not hidden.

### 6.4 Copy

- `/methodology/` (`page.tsx` near line 1770, "comparisons stop at the PB2024
  boundary"): that sentence is replaced at equal byte length by one saying procurement
  history now reaches PB2017 through reviewed decisions on the printed budget code,
  with a link to the map dataset. Two statements stay true: era book diffs cover R&D
  only, and the site never fuzzy-matches renamed programs (renames are dated owner
  decisions on the printed code, published in `p1_era_line_map`).
- The per-edition table (chains and dollars by decision, receipt completeness) is
  rendered from `json/era_map_summary.json` on `/coverage/` (85,710 / 20,288 against
  103,000 / 20,750) if it fits that ceiling, otherwise on the `/data/` map card. A
  datatruth leg checks the rendered figures against the JSON. No ceiling is raised
  and no existing disclosure is trimmed without the owner's sign-off.
- `corpus.ts` changes a comment only; its visible string stays true.

### 6.5 F-15 corrections (S5, a deliberate re-stamp)

Source: PB2026 AF Aircraft Procurement Vol I, F015EX P-40 description, PDF p.71 (the
only page that prints it): "This exhibit does not include the eight aircraft in Lot 1
which were funded outside this exhibit in FY 2020 (two test aircraft were purchased
with RDT&E funds (PE 0207134F); four operationally representative test aircraft and
two operational aircraft were purchased with procurement funds (F015E0, Line #3))."

- **Label.** F015E0's matrix title "F-15e (legacy line)" becomes "F-15e (FY2020 F-15EX
  Lot 1 aircraft)": the filed title stays the row name, and only what the P-40 states
  is added.
- **Note.** The F015E0 program entry gains `note` and `note_fact_id`: the full
  parenthetical above, with "Line #3" glossed as "line 3 of the PB2020–21 P-1 (line 4
  in PB2022)", cited to the existing narrative fact `e7d5bcfb4a30f458` (p.71). That
  receipt highlights the paragraph's first line; the note quotes the sentence so the
  reader can find it on the page. This needs a payload field, the TS type
  (`FamilyFundingProgram`) and the row rendering in `family-funding-history.tsx`.
- **Coverage notes.** Add: the totals exclude classified funding and military
  construction. Amend `COVERAGE_NOTES[2]` (legacy lines carry no variant allocation)
  with "except where a budget book states one (F015E0)".
- **Re-pins.** The V4(f) history sha, the V5 golden fixtures and the S0 normalized
  F-15 page snapshot are re-captured; F-15 page weight is re-measured.
- **Check.** The diff of `f15_funding_history.json` and the page equals exactly: the
  retitle, the new note fields, and the two coverage-note changes.

### 6.6 Record corrections

- `era_keys.py:118-120`: the docstring says rollup; correct it (F-35, then B-21).
- ROADMAP #28: a dated correction note under the entry (entries are never reworded).

## 7. Error handling

| Case | Behavior |
|---|---|
| An era key prints more than one code, title or budget activity | The parse raises (0 today); S1's script lets it propagate |
| Several era lines share one code in an edition | Summed under the program key, exactly as `fct_decade_series` sums modern lines; `decade_era_map` formula |
| A line number reused across editions | Irrelevant: decisions key on the printed code; era keys are per edition |
| A code reused for a different program | Range split; the earlier range is `exclude_reused_code` |
| Rename | `same_program` with a dated owner decision; receipts show the filed title |
| Account or organization move | A non-collision code keeps one page summing its accounts, as modern pages do. A collision code's chain always carries `program_account`/`program_org`; a dbt test rejects an unpinned collision chain |
| Code spanning organizations (10, 15, 20, 30, 500) | Decided per organization; a dbt test fails if an un-split decision covers keys from more than one organization in one edition |
| An era key with no decision | `undecided`; never exported. The dbt test is warn-severity while S2 batches are in review and flips to error in the commit that closes S2; `verify-era-map` leg b is strict from S4 |
| Keys or titles changed after review | `keys_sha256` mismatch fails `era-map check` and `verify-era-map`; re-review required |
| Classified `9999999999` | Loaded (S1b), never mapped, never a page point |
| P-1R rows | Context only, never counted; map cross-check (1,645 of 1,650 era P-1R triples; 5 known PB2017 Army exceptions allow-listed) |
| An F-15 member missing from an era edition | F-15's existing `partial` / `missing_programs` logic, unchanged |
| The program table missing at export | Raise |
| Mart/lake drift during export | The existing guard raises |

## 8. Verification

| Id | Check | Where | Fails on |
|---|---|---|---|
| V1 | **No-write loader diff** | S1 script, using `parse_p1_rollup` | The parse of PB2017–23 differs from Postgres in any amount, title, cell or key |
| V2 | Loader unit tests | `tests/jbooks/test_p1_loader_era.py`, fixture workbook | Code not captured; advance-procurement pair mishandled; classified row; footnote row; section header; tripwire not raised; `line_item_code` missing from the update branch |
| V3 | dbt tests | `assert_p1_era_map_{grain_unique,complete,no_undecided,one_code,decisions_no_overlap,org_split,collision_pinned,successor_resolves,p1r_crosscheck}.sql`; `assert_program_decade_{native_equals_line,conservation,grain_unique}.sql` | Coverage ≠ 6,927; undecided rows (§7 severity rule); unpinned collision chain; a successor absent from PB2024–26; P-1R cross-check outside the allow-list; any native row (all editions) ≠ `fct_decade_series`; Σ program grain ≠ Σ mapped line grain per edition and kind; grain not unique on (`program_key, account, organization, fy, edition_year`) |
| V4 | **`verify-era-map`** | `src/govbudget/verify_era_map.py`; CLI with zero-argument defaults (`config.SITE_DIR`, DuckDB path, seed path) printing one final `verify-era-map: PASS|FAIL` line; added to `_ASSEMBLY_PHASES` in S4 with `_VERDICT_RE` extended to `verify-(?:phase\w+|lineage|era-map):`, docstring and assembly tests updated | (a) re-read of the 7 era P-1 workbooks in `data/site/workbooks`: key set ≠ 6,927, printed code ≠ `line_item_code`, title ≠ reviewed; (b) undecided or stale decisions; (c) the map's F-15 rows ≠ `ERA_MEMBERS` joined to `ERA_PROGRAM_CODES` (31 rows); (d) any `budget_lines_decade` row whose fact ID does not recompute with `fact_id_workbook` from its own row; (e) published map parquet ≠ dbt map; (f) F-15 history sha ≠ the pin committed at `tests/fixtures/f15/history.sha256` |
| V5 | **F-15 identity** | `tests/test_f15_era_identity.py`, on hermetic fixtures committed at S0 under `tests/fixtures/f15/` (history JSON or sha, the 207 component previews, the registry subset `build_program_matrix` reads); fails, never skips, if they are missing | (1) `build_program_matrix` on a fresh-state registry (F-15's own receipts removed) with injected `decade_era_map` receipts ≠ golden bytes. (2) Sensitivity: injecting a competitor with an allowed formula and identical inputs and amount **does** change exactly that cell's fact ID — proving the formula allow-list is what protects F-15 |
| V6 | **Fact stability** | S4 proof script | Any S0 fact ID missing, or with a different amount or inputs, outside §10 |
| V7 | Receipts | `program_pdf_receipts` audit, at S4 | F-15 default ≠ 67/67; any complete receipt turns incomplete; era completeness not reported per edition |
| V8 | Site gates | `npm run verify` | program-skeleton (including leg k's recomputed `decade_absent` for decade-only pages), linkgraph, datatruth (map dataset card, Explorer entry, era summary table), years-matrix (unchanged), page weight (F-15 unchanged; `/methodology/` stamp re-measured at S0, no ceiling raised), sitemap unchanged |
| V9 | Link coverage | `govbudget link-coverage --site-dir`: per page and site-wide shares of (a) complete PDF receipt, (b) workbook cell, (c) official URL only, (d) nothing; derived figures take their weakest input. Baseline committed at S0 (`data/research/link_coverage/baseline.json`); hard check at S6 | Budget figures < 100% source-linked; any figure loses a complete PDF receipt |
| V10 | Release | `verify-phase5`, `verify-phase5b1`, `verify-phase5e` (recomputes `budget_lines_decade` amounts from the lake), `verify-lineage`, `verify-era-map`, deploy live check | Any FAIL |

**Proofs run on pinned snapshots, never on the live lake.** A snapshot is: a copy of
the DuckDB file inside a copy of the whole `data/parquet` tree (staged parquets are
looked up beside the DuckDB file), a `pg_dump` of the Postgres database restored into
a scratch database, and a copy of `data/site`, with `GOVBUDGET_DATA`,
`GOVBUDGET_DUCKDB` and `GOVBUDGET_PG_DSN` pointed at the copies. Each proof note
records the snapshot's shas. S1 and S1b compare the S0 snapshot against the post-step
state under the same code. S4's A/B exports the pre-S4 code and the S4 code, both
through the `export-site` CLI, against one post-S3 snapshot, diffed with build
timestamps masked. An idempotent re-run on a copy of `data/site` is not proof (it
hides fresh-state effects, and the F-15 call already re-serializes `datasets.json`).

## 9. Rollout (each step verifiable on its own)

| Step | Change | Verified by |
|---|---|---|
| **S0** Baseline | Snapshot S0. Hermetic F-15 fixtures and sha pin; normalized F-15 page snapshot from a fresh build at the base commit (never `site/out`). `link-coverage` tool and committed baseline. Re-measure the `/methodology/` and `/coverage/` weight stamps. Docstring and #28 corrections; file the §11 follow-ups | Pytest green; no `data/site` change |
| **S1** Loader | Loader split; V1; V2; migration 021 with the modern backfill; capture, tripwire, update-branch column; export_facts and stg columns; dedicated script re-runs PB2017–23 inside a transaction, compares every existing column of all 84,463 P-1/P-1R rows, and rolls back on any difference | V1 clean; V2 green; equality holds; 6,927 keys with exactly one code; S0-vs-post export diff empty |
| **S1b** Classified era rows | Load the 50 blank-line `9999999999` workbook rows | Lake gains exactly the `budget_lines` rows V1's parse predicts (one per amount column); export diff empty |
| **S2** Map | `era-map propose` (writes `counts.json`); class rulings applied; successor search; batches reviewed and ratified; `p1_era_line_map` and its dbt tests; `verify-era-map` legs a–c; the closing commit flips `no_undecided` to error | dbt tests pass with no undecided rows; the map's F-15 rows equal `ERA_MEMBERS` × `ERA_PROGRAM_CODES` |
| **S3** Program table | `fct_program_decade_series` and its tests | Native parity (all editions); conservation; exporter unchanged → empty export diff |
| **S4** Era points | Decade tier switch (§6.1), fences (§6.2), map dataset registration, era summary JSON and its rendering, methodology sentence, `verify-era-map` legs d–f and its assembly entry | V3–V8 and `verify-phase5e`; the A/B diff equals §10; measured page gain recorded |
| **S5** F-15 corrections | §6.5; the owner signs off the exact strings; re-pins | The diff equals the approved changes |
| **S6** Release | V9 hard check, V10; one deploy via `./scripts/launch/deploy.sh` | All green; live check passes |

S2's individual review is the critical path: S4 cannot start until no chain is
undecided. The class-ruled chains are ready as soon as this spec is approved.

## 10. Expected differences (what the S4 A/B diff must equal)

- `program_details/<slug>.json`: new era decade points for about 880 procurement
  pages. For the about 80 decade-only procurement pages, the `decade_absent` block
  (first edition, edition count, FY span) and its rendered note change accordingly.
- `citations.json`, cite shards, `citations.parquet`: new era leaf and
  `decade_era_map` entries. F-15's 72 A1 era-leaf entries are now minted by the decade
  tier: their `pe_bli` changes from null to F01500 / F015EX / F15EWS and their
  `retrieved_at` from the space form to the `T` form (seven edition timestamps). Every
  other field is equal. F-15's reported `added_citations` falls by 72. These 72 rows
  move position in `citations.parquet` and `budget_lines_decade.parquet`.
- `budget_lines_decade.parquet`: new era rows (schema unchanged); its `datasets.json`
  row_count and bytes change.
- New `p1_era_line_map.parquet` with its `datasets.json` entry; new
  `json/era_map_summary.json`.
- New `json/breakdowns/<fid>.json` for each `decade_era_map` sum with two or more
  inputs; workbook-cell previews for the new era leaves.
- `json/budget-pdf-receipts/v2/*` shards and `json/budget_pdf_receipts_audit.json`
  (new receipts; per-book counts).
- `json/site_meta.json` (`counts.citations`, `datasets.budget_lines_decade`) and the
  manifest's sidecar and dataset counts.
- Site side (not part of the data A/B): the committed `site/public/llms.txt` citation
  count; the `/coverage/` or `/data/` era table; the methodology sentence.
- Unchanged: `f15_funding_history.json` and its 69 breakdowns, `/families/f-15/`,
  lineage funding lines, `years_matrix.json`, book diffs, `/feed/`, `sitemap.xml` (no
  page is zero-content today, so none becomes indexable).

## 11. Risks and filed follow-ups

1. **Shared mutable lake and Postgres.** Every proof runs on a pinned snapshot; the
   hourly SAM job and other sessions cannot touch it.
2. **The S1 database write** uses today's loader on old editions. V1 must be clean
   first; the re-run is transactional and rolls back on any difference.
3. **Duplicate receipts.** Era sums for F-15 lines exist twice (program-page receipt
   and F-15 cell receipt, same inputs and amount), deliberately, for byte identity.
   Unifying them is a later re-stamp.
4. **Size.** About 15–16k new era points and 16–21k leaf citations against 125,409
   today; `citations.json` (83.9 MB) grows. Per-point cost on program pages is about
   2.2 KB raw / 0.22 KB gzip; procurement pages stay under 40% of their ceiling. Page
   weight and build time are re-measured, never assumed.
5. **Receipt completeness.** Era shipbuilding rows will be mostly workbook-only.
   Disclosed per edition.
6. **False continuity.** Mitigated by owner review of every non-mechanical chain, the
   drift guard and the published map.
7. **Review stall.** About 120–125 decisions in batches of 25, largest dollars first.
8. **File as ROADMAP items at S0:**
   - `/years/` needs sharding (or an exhibit split) before it can carry era
     procurement and PB2027 under its 4 MiB cap.
   - PB2026 drops the real `0390D` Chem Demil `O&M`/`RDT&E` lines ($1.09B FY2024
     actuals) as section headers.
   - Narrative fact `136baeef904dd052` (the JLTV continuation sentence) is attributed
     to the OPA BA 3, 4 & 6 book with no page; the sentence is printed only in the
     BA1 book (p.100), which is neither registered nor hosted.
   - Dead v1 receipt files (`budget_pdf_receipts.py:393-472`, 256 shipped shards)
     need owner sign-off to remove.
   - `search_aliases.csv` still holds two routes #55 corrected.
