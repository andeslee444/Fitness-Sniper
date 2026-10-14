<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 21c: Release-1 expected-difference rule files (P1, P2, release state)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §7 P1 (lake changes; re-paired B@fu-pre vs B@fu-post), P2 (code changes; re-paired A@fu-pre vs B@fu-pre), §8 step 4 (the release state against B@fu-post: SAM-registration rules only), §4.7, §5.7, §5.8, §3.2, Q3, Q6.

**Files:**
- Create: `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-code.json` (P2)
- Create: `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-lake.json` (P1)
- Create: `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-fact-moves-lake.json` (P1, read by `scripts/fu/fact_delta.py --expect`)
- Create: `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-release.json` (Task 22c)

**Interfaces:**
Consumes: `govbudget proof diff --expect` rules (`govbudget.proof.load_expectations`): a JSON list of `{path, why, status?, pointer?, change?, required?}`; `path` and `pointer` are globs where only `*` is special (it also crosses `/`); a pointer collapses 16-hex fact IDs to `{fid}` and writes list elements as `/[]`; a list compares as a multiset, so a changed list entry is one `removed` plus one `added`; a rule without `pointer` matches any change in the file; every difference must match a rule and every `required` rule must match at least once. Float noise, build stamps and the control's reorder classes (`--noise-from`) are never differences. Task 21b's `fact_delta.py --expect` object.
Produces: the four files above, read by Task 21f (P2: `expected-diff-code.json`; P1: `expected-diff-lake.json` and `expected-fact-moves-lake.json`) and Task 22c (`expected-diff-release.json`).

Measured for this task (2026-10-13, read-only, the live export of 2026-10-04): `json/budget-pdf-receipts/` holds 256 two-hex v1 shards (`00.json` … `ff.json`) and `v2/` (4,096 files); `manifest.json` `json_sidecars` 36,271; `json/datasets.json` entries carry `bytes, cited, file, name, row_count, scope`, and `p1_era_line_map`'s scope reads "… line_item_code (the budget line code printed on it, the pe_bli a same_program line's era citations carry) …"; `json/search_quick.json` is `{"docs": [...]}` with `{"id": "alias:jassm", "kind": "alias", "title": "JASSM", "url": "/program/0603000D8Z/"}` and `{"id": "alias:c-130j", …, "url": "/program/2012C130J/"}`; `json/site_meta.json` `counts` `{agencies 24, citations 143841, companies 200, companies_with_sam 149, program_pages 2562, programs 1938}`, `build_checks.dbt_assertions` 196, `programs_coverage.universe_total_thousands` 385268393.0 (`universe_billions` 385.3, `coverage_pct` 77.9); `json/era_map_summary.json` `totals.same_program` `{actuals_thousands 727137554.0, chains 918, lines 5853}`, `totals.exclude_route_unsafe` `{5832017.0, chains 2, lines 14}`; `json/programs_excluded.json` is a list of 29; `json/flow_chart.json` is the only top-level `json/` file naming 0390D (`budget.nodes[26].other.members`: `{"k": "A|0390D", "v": 210039}`); `data/fct_budget_trajectory.parquet` holds 0708081D and 0708083D (rollup tier), so it can gain 0390DOM; `json/sam/` 149 files and 150 of 200 `json/entity_details/*.json` mention SAM. All three rule lists load with `load_expectations` (24, 40 and 12 rules; 24, 31 and 0 required).

- [ ] **Step 1: Write the P2 rule list (code changes, A@fu-pre vs B@fu-pre)**

Create `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-code.json`:

```json
[
  {"path": "json/years_matrix.json", "status": ["changed"], "required": true, "why": "#193 (design §3.2-§3.3): the core keeps its name as schema 2 (header, every row with np, the 12 default decade columns, build_id, the shards manifest); P2b (years_shard_proof.py) proves the merged view keeps every A cell and equals the program sidecars"},
  {"path": "json/years_matrix/decade.json", "status": ["only_b"], "required": true, "why": "#193: the lazy shard holding the 18 non-default decade columns (P2b)"},
  {"path": "json/years_matrix/detail.json", "status": ["only_b"], "required": true, "why": "#193: the lazy shard holding the PB2026 amount types, the deltas and the projects (P2b)"},
  {"path": "json/budget-pdf-receipts/0*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/0?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/1*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/1?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/2*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/2?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/3*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/3?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/4*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/4?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/5*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/5?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/6*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/6?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/7*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/7?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/8*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/8?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/9*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/9?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/a*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/a?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/b*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/b?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/c*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/c?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/d*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/d?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/e*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/e?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "json/budget-pdf-receipts/f*.json", "status": ["only_a"], "required": true, "why": "#196 (design §5.7): the 16 unread v1 receipt shards json/budget-pdf-receipts/f?.json leave the export; no rule covers v2/, so any v2 shard that moved fails"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/json_sidecars", "change": ["changed"], "required": true, "why": "#196 and #193: the sidecar count loses the 256 v1 shards and gains the two /years/ shards (36,271 -> 36,017 on the 2026-10-04 export)"},
  {"path": "json/search_quick.json", "status": ["changed"], "pointer": "/docs/[]", "change": ["added", "removed"], "required": true, "why": "#197 (design §5.8): alias:jassm -> /program/0207325F/ and alias:c-130j -> /program/0401132F/, each one removed and one added list entry"},
  {"path": "json/f15_funding_history.json", "status": ["changed"], "pointer": "/programs/[]", "change": ["added", "removed"], "required": true, "why": "#206 T9 (design §5.2, Q17 as amended): F015E0's note gains the gloss [the PB2026 F-15EX AP (F015EX) P-40]; Task 21g's hermetic check proves that note is the only leaf that moved"},
  {"path": "json/datasets.json", "status": ["changed"], "pointer": "/datasets/[]", "change": ["added", "removed"], "required": true, "why": "Q3 scope amendment (design §4.5): the p1_era_line_map entry's scope names program_key (the printed code except 0390DOM for 0390D's O&M line)"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/build_checks/dbt_assertions", "change": ["changed"], "required": true, "why": "W2: the dbt assertion count grows with this wave's tests (A's dbt parse manifest has 196 test nodes, B's more; Task 21d prints both)"}
]
```

Deliberately no rule, so any change there fails P2: `json/citations.json`, `json/cite-shards/*`, `citations/citations.parquet` (design §7: no fid added, removed or changed), every `data/*.parquet`, every `json/program_details/*.json` (no 0390DOM page exists on fu-pre; Task 12's `printed_code`/`exhibit_family` are written for alias keys only), `json/budget-pdf-receipts/v2/*` and the receipts audit, `json/flow_chart.json`, `json/programs.json`, `json/programs_excluded.json`, `json/era_map_summary.json` (the summary is computed from the lake's map, which both exports read), `json/lineage_flow.json`, `json/feed*`, and every other key of `manifest.json` and `json/site_meta.json`. The /years/ content is judged by P2b (`years_shard_proof.py`), the F-15 note by Task 21g's hermetic leaf check.

- [ ] **Step 2: Write the P1 rule list (lake changes, B@fu-pre vs B@fu-post)**

Create `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-lake.json`:

```json
[
  {"path": "data/budget_lines.parquet", "status": ["changed"], "required": true, "why": "#194 (design §4.4, §7 P1): +4 rows, 0390DOM PB2026 (87,404 / 20,745 / 3,243 / 3,243); fact_delta: every A row is in B and B's only new rows carry pe_bli 0390DOM"},
  {"path": "data/budget_lines_decade.parquet", "status": ["changed"], "required": true, "why": "#194 and B7: 0390DOM's PB2024-PB2026 rows and the B7 era rows (era key 0390D-ARMY-L1); fact_delta checks both pe_bli sets"},
  {"path": "data/fct_budget_trajectory.parquet", "status": ["changed"], "why": "#194: the mart carries rollup-tier lines (0708081D and 0708083D are in it today), so it may gain a 0390DOM row; fact_delta allows only that"},
  {"path": "data/p1_era_line_map.parquet", "status": ["changed"], "required": true, "why": "#206 T6 (design §5.1): decided_on is column 14 of 18; B7 (design §4.5): the 7 O&M era rows read same_program, R-DEC-ERA-B7, program_key 0390DOM, B7's date"},
  {"path": "json/era_map_summary.json", "status": ["changed"], "required": true, "why": "B7 (design §4.5): same_program 727,137,554K -> 727,939,107K (918 -> 919 chains), exclude_route_unsafe 5,832,017K -> 5,030,464K (2 -> 1 chain); a R-DEC-ERA-B7 entry"},
  {"path": "json/program_details/0390DOM.json", "status": ["only_b"], "required": true, "why": "#194 (design §4.6, Q5): the new rollup-tier page's sidecar, with printed_code O&M and exhibit_family om"},
  {"path": "json/programs_excluded.json", "status": ["changed"], "pointer": "/[]", "change": ["added"], "required": true, "why": "#194 (design §4.6): 0390DOM is listed as excluded (no_detail); it gets no programs.json, /years/ or search row"},
  {"path": "json/flow_chart.json", "status": ["changed"], "required": true, "why": "Q6 (design §4.7): the 0390DOM FY2026 request (3,243) joins the flow chart: node and edge values, geometry, the Other members' A|0390D 210,039 -> 213,282, the bridge"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "required": true, "why": "#194, B7: new 0390DOM workbook leaves, era leaves, decade_era_map sums and book diffs; fact_delta traces every one to pe_bli 0390DOM"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/recorded_value", "change": ["changed"], "required": true, "why": "design §4.7: the 11 named derived aggregates (expected-fact-moves-lake.json) each move by exactly +3,243; fact_delta checks each fid"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/inputs", "change": ["changed"], "required": true, "why": "design §4.7: the same 11 aggregates each gain the 0390DOM FY2026 total leaf as an input, and drop none"},
  {"path": "json/cite-shards/*.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "required": true, "why": "the cite shards carry the new citations (the same objects as citations.json)"},
  {"path": "json/cite-shards/*.json", "status": ["changed"], "pointer": "/{fid}/recorded_value", "change": ["changed"], "required": true, "why": "the 11 moved aggregates, as in citations.json"},
  {"path": "json/cite-shards/*.json", "status": ["changed"], "pointer": "/{fid}/inputs", "change": ["changed"], "required": true, "why": "the 11 moved aggregates' inputs, as in citations.json"},
  {"path": "citations/citations.parquet", "status": ["changed"], "required": true, "why": "the citation table: the new rows and the 11 moved aggregates (fact_delta compares citations.json fact by fact)"},
  {"path": "json/breakdowns/*.json", "status": ["changed"], "required": true, "why": "the 11 moved aggregates' breakdowns gain the 0390DOM row (fact_delta --diff-report: changed only for a moved fact)"},
  {"path": "json/breakdowns/*.json", "status": ["only_b"], "why": "a breakdown for each new multi-input derived fact (decade_era_map sums, book diffs); fact_delta: only for facts new in B"},
  {"path": "json/workbook-cells/*.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "required": true, "why": "workbook-cell previews for the new 0390DOM and B7 era leaves (all 256 shards exist in A)"},
  {"path": "json/budget-pdf-receipts/v2/*.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "why": "design §7 P1: receipts for the new leaves, only if the matcher places the O&M rows (Task 12 lets it accept the alias)"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/citation_sha256", "change": ["changed"], "required": true, "why": "the audit fingerprints the citation registry it read"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/leaf_count", "change": ["changed"], "required": true, "why": "more workbook leaves"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/receipt_count", "change": ["changed"], "why": "more receipts, only if the matcher places the new leaves"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/complete_receipts", "change": ["changed"], "why": "more complete receipts, only if the matcher places the new leaves"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/books/[]", "change": ["added", "removed"], "why": "the PB2024-PB2026 and era P-1 books' fact and complete counts, where the new leaves land"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/unmatched_cells/[]", "change": ["added"], "why": "new cells the matcher cannot place yet, disclosed per edition"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/citations/workbook", "change": ["changed"], "required": true, "why": "the manifest's citation counts: new workbook leaves"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/citations/derived", "change": ["changed"], "required": true, "why": "the manifest's citation counts: new decade_era_map sums and book diffs"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/datasets/budget_lines", "change": ["changed"], "required": true, "why": "the manifest's dataset counts: budget_lines 8,549 -> 8,553"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/datasets/budget_lines_decade", "change": ["changed"], "required": true, "why": "the manifest's dataset counts: budget_lines_decade"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/datasets/fct_budget_trajectory", "change": ["changed"], "why": "the manifest's dataset counts, if the trajectory mart gains its 0390DOM row"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/json_sidecars", "change": ["changed"], "required": true, "why": "the sidecar count: the 0390DOM program sidecar and the new breakdowns"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/counts/citations", "change": ["changed"], "required": true, "why": "site_meta counts.citations"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/counts/program_pages", "change": ["changed"], "required": true, "why": "site_meta counts.program_pages 2,562 -> 2,563 (/program/0390DOM/)"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/datasets/budget_lines", "change": ["changed"], "required": true, "why": "site_meta datasets.budget_lines 8,549 -> 8,553"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/datasets/budget_lines_decade", "change": ["changed"], "required": true, "why": "site_meta datasets.budget_lines_decade"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/datasets/fct_budget_trajectory", "change": ["changed"], "why": "site_meta datasets.fct_budget_trajectory, if the mart gains its 0390DOM row"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/programs_coverage/universe_total_thousands", "change": ["changed"], "required": true, "why": "design §4.7: the /programs/ universe 385,268,393 -> 385,271,636 ($385.3B and 77.9% unchanged)"},
  {"path": "json/datasets.json", "status": ["changed"], "pointer": "/datasets/[]", "change": ["added", "removed"], "required": true, "why": "the row_count/bytes entries of budget_lines, budget_lines_decade and p1_era_line_map (and fct_budget_trajectory if it moved) are replaced"},
  {"path": "json/datasets.json", "status": ["changed"], "pointer": "/citations/row_count", "change": ["changed"], "required": true, "why": "the citations card's row count"},
  {"path": "json/datasets.json", "status": ["changed"], "pointer": "/citations/kinds/[]", "change": ["added", "removed"], "required": true, "why": "the citations card's per-kind counts (workbook, derived)"}
]
```

Deliberately no rule, so any change there fails P1: `json/years_matrix.json` and `json/years_matrix/*` (0390DOM gets no /years/ row, design §4.6 as corrected), `json/search_quick.json`, `json/programs.json`, `json/agencies.json`, `json/f15_funding_history.json`, `json/lineage_flow.json`, `json/feed*`, every other `data/*.parquet`, every program sidecar except the new `0390DOM.json` (0708081D's and 0708083D's sidecars do not name 0390D today), and every other key of `manifest.json`, `json/site_meta.json` and the receipts audit. Changes inside the allowed patterns are judged fact by fact by `fact_delta.py` with Step 3's file.

- [ ] **Step 3: Write the P1 fact expectations**

Create `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-fact-moves-lake.json`:

```json
{
  "explained_by_pe_bli": ["0390DOM"],
  "moved": {
    "709cbd08c6b7dfb0": {"why": "/programs/ universe (site_meta.programs_coverage.universe_fact_id): 385,268,393 -> 385,271,636", "delta_thousands": "3243.000"},
    "c216c55e0ddffec1": {"why": "flow chart b:total: 385,268,393 -> 385,271,636", "delta_thousands": "3243.000"},
    "d2f5b699e5123b11": {"why": "flow chart b:c:A (Army): 43,338,494 -> 43,341,737", "delta_thousands": "3243.000"},
    "da3a508dbe8427f4": {"why": "flow chart edge b:c:A->b:other:appropriation: 28,418,219 -> 28,421,462", "delta_thousands": "3243.000"},
    "ce38e79987ed7a92": {"why": "flow chart b:other:appropriation (holds A|0390D): 100,800,917 -> 100,804,160", "delta_thousands": "3243.000"},
    "ac97b301729e8743": {"why": "flow chart edge b:other:appropriation->b:other:budget_activity: 92,318,533 -> 92,321,776", "delta_thousands": "3243.000"},
    "980c6bbee984f264": {"why": "flow chart b:other:budget_activity: 215,533,900 -> 215,537,143", "delta_thousands": "3243.000"},
    "9a77d80916d1cead": {"why": "flow chart edge b:other:budget_activity->b:other:program: 204,111,830 -> 204,115,073", "delta_thousands": "3243.000"},
    "ce27343e3d87e507": {"why": "flow chart b:other:program: 263,982,731 -> 263,985,974", "delta_thousands": "3243.000"},
    "25e51edb9bfa36b3": {"why": "flow chart edge b:other:program->b:bridge:not-crosswalked: 137,809,962 -> 137,813,205", "delta_thousands": "3243.000"},
    "6ca3c62f32d31298": {"why": "flow chart bridge not_yet_crosswalked: 227,538,773 -> 227,542,016 ($227.5B unchanged)", "delta_thousands": "3243.000"}
  },
  "rows": {"data/budget_lines.parquet": ["0390DOM"], "data/budget_lines_decade.parquet": ["0390D-ARMY-L1", "0390DOM"], "data/fct_budget_trajectory.parquet": ["0390DOM"]}
}
```

Each `delta_thousands` is the 0390DOM PB2026 FY2026 total (P-1 `fy2026/dod/p1_display.xlsx` row 303, 3,243); each `why` names the value today (`json/citations.json` `recorded_value`) and after.

- [ ] **Step 4: Write the release-state rule list (B@fu-post vs the release export)**

Create `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-release.json`:

```json
[
  {"path": "json/sam/*.json", "status": ["only_b", "changed"], "why": "design §8 step 4: a SAM.gov registration the hourly job stored after snapshot fu-post (all 200 families had an answer on 2026-10-13, so none is expected)"},
  {"path": "json/entity_details/*.json", "status": ["changed"], "why": "design §8 step 4: a company page's SAM registration block, as above"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "why": "design §8 step 4: one derived citation per newly published SAM registration"},
  {"path": "json/cite-shards/*.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "why": "the cite shards carry those citations"},
  {"path": "citations/citations.parquet", "status": ["changed"], "why": "the citation table, as above"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/counts/citations", "change": ["changed"], "why": "site_meta counts.citations, as above"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/counts/companies_with_sam", "change": ["changed"], "why": "site_meta counts.companies_with_sam, as above"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/citations/derived", "change": ["changed"], "why": "the manifest's derived citation count, as above"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/json_sidecars", "change": ["changed"], "why": "a new json/sam receipt file, as above"},
  {"path": "json/datasets.json", "status": ["changed"], "pointer": "/citations/row_count", "change": ["changed"], "why": "the citations card's row count, as above"},
  {"path": "json/datasets.json", "status": ["changed"], "pointer": "/citations/kinds/[]", "change": ["added", "removed"], "why": "the citations card's derived count, as above"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/citation_sha256", "change": ["changed"], "why": "the audit fingerprints the citation registry, as above"}
]
```

No rule is required: on 2026-10-13 the hourly SAM job reported "all 200 published families have a stored SAM answer" (`data/parquet/sam/daily/state.json`), so the release export normally equals B@fu-post (`proof diff` then reads `PASS` with every rule at 0). Anything else that differs fails the release (design §8 step 4: "what ships is what was proven").

- [ ] **Step 5: Validate the four files**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && D=docs/superpowers/plans/2026-10-04-families-piece1-followups && uv run --project . python - "$D" <<'PY'
import json, re, sys
from pathlib import Path
from govbudget.proof import load_expectations
d = Path(sys.argv[1])
for name in ("expected-diff-code.json", "expected-diff-lake.json", "expected-diff-release.json"):
    rules = load_expectations(d / name)
    print(name, len(rules), "rules,", sum(1 for r in rules if r.get("required")), "required")
moves = json.loads((d / "expected-fact-moves-lake.json").read_text())
assert set(moves) == {"explained_by_pe_bli", "moved", "rows"}
assert len(moves["moved"]) == 11 and all(re.fullmatch(r"[0-9a-f]{16}", f) for f in moves["moved"])
assert {m["delta_thousands"] for m in moves["moved"].values()} == {"3243.000"}
print("expected-fact-moves-lake.json", len(moves["moved"]), "moved aggregates,", sorted(moves["rows"]))
PY
```
Expected:
```
expected-diff-code.json 24 rules, 24 required
expected-diff-lake.json 40 rules, 31 required
expected-diff-release.json 12 rules, 0 required
expected-fact-moves-lake.json 11 moved aggregates, ['data/budget_lines.parquet', 'data/budget_lines_decade.parquet', 'data/fct_budget_trajectory.parquet']
```

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-code.json GovBudget/docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-lake.json GovBudget/docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-fact-moves-lake.json GovBudget/docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-release.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(plan): release-1 expected differences — P2 code, P1 lake (+ the eleven moved aggregates), release state" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `4 files changed`.
