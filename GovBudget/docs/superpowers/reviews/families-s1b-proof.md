# Families piece 1 — S1b proof (era Classified Programs rows, Task 9)

Spec: docs/superpowers/specs/2026-10-02-era-procurement-history-design.md §4.2, §9 S1b.
Code: 99ebde61cb1400e457c74460a595146d1dc03bbd. Snapshot: .proofs/s1 (snapshot.json sha256 0ec28966082e304529958e715ce64b9426d357160a7545a460a225751531bee3); scratch database govbudget_proof_s1.

Prediction (parse of the 7 workbooks): 409 rows = 49/91/91/63/70/21/24 (PB2017-PB2023), 50 keys; PB2023's two 3080F rows are BA 03 and BA 04.
A = the post-S1 snapshot, jbooks export-facts, govbudget build, export-site. B = A + s1_reload_era_p1.py --apply, then the same.
A2 = a second run of A's chain on another clone of the snapshot: the control. A = A2 sets the float-noise floor (values equal to 12 significant digits) that A vs B is read against.
Consumer audit: see the Task 9 table in the families piece 1 plan; no published reader takes era-edition 9999999999 rows.
data/research/edition_manifest.json budget_lines counts are load-time records (no gate reads them) and stay at their pre-S1b values.

## Summary (2026-10-03)

**Outcome.** Live Postgres `govbudget` gained exactly the 409 rows the parse predicts. Nothing else changed: the
transactional verifier reported 0 pre-existing rows changed, and live equals the rehearsal on 16 columns in id
order. The live lake was re-exported and equals the rehearsal row for row. The judged site diff A vs B is EQUAL
with 0 changed.

| | before | after |
|---|---|---|
| budget_lines | 159,494 | 159,903 |
| P-1/P-1R | 84,463 | 84,872 |
| P-1 `9999999999` by FY | 2024 35, 2025 21, 2026 29 | + 2017 49, 2018 91, 2019 91, 2020 63, 2021 70, 2022 21, 2023 24 |
| era `9999999999` rows: organization `''` / code `9999999999` / title Classified Programs | 0 | 409 / 409 / 409 |
| era `9999999999` keys (account, budget activity, FY) | 0 | 50 (PB2023 3080F in BA 03 and BA 04) |
| organization-`''` identities (crosswalk.py comment) | 13 | 20 |
| budget_lines max id | 349,612 | 581,201 (the live dry run burns ~58k sequence values; ids are not compared) |
| live lake budget_lines rows / with line_item_code | 159,494 / 84,463 | 159,903 / 84,872 |

**Control and noise (controller ruling, 2026-10-03).** The control A vs A2 (two exports of the s1 snapshot with
this code) read EQUAL and wrote `noise-s1.json`: sha256 `51604a5e3c43ad79b5b962d14ac2f22658afd77d2a224c9950c7f7c4e31ac2a7`,
classes_sha256 `122d9b684dd14b10a12cf0972ce2d679135c0a3af523278e00f67664a73636fc`, 9 reorder classes.
A vs B judged with it read **DIFFERENT, changed 1** (`05-diff-A-B.log`, kept). The one file was
`json/flows/0605502E.json /awards`, where awards 8 and 9 swap places. Both are exactly $1,500,000.0
(W31P4Q19C0008 / W31P4Q17C0103). `export_site._emit_flows_sidecars` orders by `dollars desc limit 12` with no
tie-break, and that query's input rows are identical as multisets in the A, A2 and B warehouses (`05x`). The
DARPA R-1 line reads award tables, never era P-1 rows.

Task 8's same-snapshot control had caught this same tie: `.proofs/s1-logs/noise-s0.json`, sha256
`b947523b6a17a766f12a869cd8e7ce5a8b71f32d6645664605f77893209574b9`, classes_sha256
`963c39010e43d9e118b3f468d9711b09723fea6af2253d6ab2cdb2f5b1e5503f`, verdict EQUAL, 10 classes. It is a strict
superset of noise-s1 and adds exactly `json/flows/*.json /awards`. The ruling: noise classes are a property of
the export code, which is unchanged since Task 8's control (only cli.py's proof flags changed), so A vs B is
judged with noise-s0.json. Result (`05-diff-A-B-noise-s0.log`): **EQUAL**. The counts were `identical 35,030 ·
equivalent 373 · reordered 165 (10 control classes) · changed 0 · only in A 0 · only in B 0`. Float noise was
226 files / 3,604 values; the rule is equal to 12 significant digits, or |a−b| ≤ 1e-6 near zero. Derived hashes
were 2 files / 12 values. What this can hide: an ordering change inside a control-observed class (by
construction, tie-break orders with no meaning), and differences below those float tolerances (not money).

**Test fix (controller-approved).** After the live write, `tests/jbooks/test_era_keys.py::
test_era_procurement_keyspace_disjoint_from_modern_and_r1` failed. That test reads the live database, and it
selected "every PB2017–23 P-1 row" as era keys, which the plan's binding rule forbids. It reported `9999999999`
as a collision with modern editions, which carry that code by design. Before: `1 failed`
(`14a-era-keyspace-test-before-fix.txt`). The fix selects era keys with `is_era_procurement_key` and asserts
that the only other era-edition value is `CLASSIFIED_CODE`, which keeps the namespace guard non-vacuous.
After: `1 passed` (`14b-…`). The read-only evidence (`13c-…`): 1,219 era-edition values, of which only
`9999999999` is not an era key; 0 collisions and 0 unanchored under the selector.

**Full suite** (env.sh sourced, per Task 8's ruling; the `test_config` worktree artifact fails only with
`GOVBUDGET_DATA` unset): `3739 passed, 13 skipped`, 0 failed (`15-full-suite.log`). The 13 skips are
environment-gated. Earlier runs, before the test fix, are in `13a-full-suite-env-unset.txt` (2 failed: the
keyspace test and the `test_config` artifact) and `13b-full-suite-env-set.txt` (1 failed: the keyspace test).

**Not changed:** the live DuckDB warehouse (Task 8 and Task 9 have no live dbt build), and
`data/research/edition_manifest.json`.

## 01-v1-live

```
V1 PB2017 P-1 (doc 189): parse 6832 rows | db 6783 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 49 | line_item_code: null 0, equal 6783, differ 0
V1 PB2018 P-1 (doc 261): parse 13468 rows | db 13377 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 91 | line_item_code: null 0, equal 13377, differ 0
V1 PB2019 P-1 (doc 271): parse 12948 rows | db 12857 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 91 | line_item_code: null 0, equal 12857, differ 0
V1 PB2020 P-1 (doc 282): parse 8838 rows | db 8775 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 63 | line_item_code: null 0, equal 8775, differ 0
V1 PB2021 P-1 (doc 292): parse 10120 rows | db 10050 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 70 | line_item_code: null 0, equal 10050, differ 0
V1 PB2022 P-1 (doc 302): parse 3000 rows | db 2979 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 21 | line_item_code: null 0, equal 2979, differ 0
V1 PB2023 P-1 (doc 312): parse 2925 rows | db 2901 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 24 | line_item_code: null 0, equal 2901, differ 0
V1: CLEAN (7 editions, 58131 parsed rows)
```

## 01z-live-before-counts

```
budget_lines rows: 159494
P-1/P-1R rows: 84463
P-1 9999999999 by fiscal_year: [(2024, 35), (2025, 21), (2026, 29)]
organization '' identities (distinct pe_bli, exhibit, fiscal_year): 13
max id: 349612
```

## 02-snapshot

```
proof snapshot: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1
  duckdb sha256 79b1bca75dbb47f958ee4271a7d07147c085172fc1fea78206694b70492e6293 (18 of 37 views repointed)
  parquet files 112 · site files 35,520 · raw_docs files 1,112
  postgres govbudget -> govbudget_proof_s1 (18 tables, dump sha256 a8d8aa57c2064be83102fabf5ee74c4e7c18f519f387b132a14f8984d1530cdf)
  source /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1/env.sh [RUN_DIR]
```

## 03-A

```
lineage_flow.json: 62059 bytes (budget 160000) — 52 families, 152 identities, 98 stated + 3 inferred edges, 9 unresolved reference(s)
{"edition": 2017, "exhibit": "P-1", "pages": 168, "facts": 6, "complete": 6}
{"edition": 2017, "exhibit": "R-1", "pages": 85, "facts": 2781, "complete": 2778}
{"edition": 2018, "exhibit": "P-1", "pages": 384, "facts": 9, "complete": 9}
{"edition": 2018, "exhibit": "R-1", "pages": 200, "facts": 3123, "complete": 3120}
{"edition": 2019, "exhibit": "P-1", "pages": 396, "facts": 12, "complete": 12}
{"edition": 2019, "exhibit": "R-1", "pages": 312, "facts": 3195, "complete": 3190}
{"edition": 2020, "exhibit": "P-1", "pages": 264, "facts": 15, "complete": 15}
{"edition": 2020, "exhibit": "R-1", "pages": 190, "facts": 3192, "complete": 3187}
{"edition": 2021, "exhibit": "P-1", "pages": 267, "facts": 18, "complete": 18}
{"edition": 2021, "exhibit": "R-1", "pages": 210, "facts": 3396, "complete": 3313}
{"edition": 2022, "exhibit": "P-1", "pages": 88, "facts": 18, "complete": 18}
{"edition": 2022, "exhibit": "R-1", "pages": 88, "facts": 3318, "complete": 3315}
{"edition": 2023, "exhibit": "P-1", "pages": 79, "facts": 15, "complete": 15}
{"edition": 2023, "exhibit": "R-1", "pages": 83, "facts": 3252, "complete": 3249}
{"edition": 2024, "exhibit": "P-1", "pages": 140, "facts": 2715, "complete": 2646}
{"edition": 2024, "exhibit": "R-1", "pages": 94, "facts": 3225, "complete": 3189}
{"edition": 2025, "exhibit": "P-1", "pages": 178, "facts": 2380, "complete": 2352}
{"edition": 2025, "exhibit": "R-1", "pages": 97, "facts": 2934, "complete": 2844}
{"edition": 2026, "exhibit": "P-1", "pages": 166, "facts": 3163, "complete": 3123}
{"edition": 2026, "exhibit": "P-1R", "pages": 41, "facts": 403, "complete": 391}
{"edition": 2026, "exhibit": "R-1", "pages": 102, "facts": 4983, "complete": 4982}
budget PDF receipts: 46682/47081 complete, 21 government documents; audit -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-A/site/json/budget_pdf_receipts_audit.json
export-site: 16 datasets, 125457 citations, 204 pdfs, 30 workbooks, 8021 unresolved, 4093 zero-amount -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-A/site
export-site: dossiers 50 written, 45 claim(s) dropped across 12 dossier(s)
```

## 03b-A2

```
lineage_flow.json: 62059 bytes (budget 160000) — 52 families, 152 identities, 98 stated + 3 inferred edges, 9 unresolved reference(s)
{"edition": 2017, "exhibit": "P-1", "pages": 168, "facts": 6, "complete": 6}
{"edition": 2017, "exhibit": "R-1", "pages": 85, "facts": 2781, "complete": 2778}
{"edition": 2018, "exhibit": "P-1", "pages": 384, "facts": 9, "complete": 9}
{"edition": 2018, "exhibit": "R-1", "pages": 200, "facts": 3123, "complete": 3120}
{"edition": 2019, "exhibit": "P-1", "pages": 396, "facts": 12, "complete": 12}
{"edition": 2019, "exhibit": "R-1", "pages": 312, "facts": 3195, "complete": 3190}
{"edition": 2020, "exhibit": "P-1", "pages": 264, "facts": 15, "complete": 15}
{"edition": 2020, "exhibit": "R-1", "pages": 190, "facts": 3192, "complete": 3187}
{"edition": 2021, "exhibit": "P-1", "pages": 267, "facts": 18, "complete": 18}
{"edition": 2021, "exhibit": "R-1", "pages": 210, "facts": 3396, "complete": 3313}
{"edition": 2022, "exhibit": "P-1", "pages": 88, "facts": 18, "complete": 18}
{"edition": 2022, "exhibit": "R-1", "pages": 88, "facts": 3318, "complete": 3315}
{"edition": 2023, "exhibit": "P-1", "pages": 79, "facts": 15, "complete": 15}
{"edition": 2023, "exhibit": "R-1", "pages": 83, "facts": 3252, "complete": 3249}
{"edition": 2024, "exhibit": "P-1", "pages": 140, "facts": 2715, "complete": 2646}
{"edition": 2024, "exhibit": "R-1", "pages": 94, "facts": 3225, "complete": 3189}
{"edition": 2025, "exhibit": "P-1", "pages": 178, "facts": 2380, "complete": 2352}
{"edition": 2025, "exhibit": "R-1", "pages": 97, "facts": 2934, "complete": 2844}
{"edition": 2026, "exhibit": "P-1", "pages": 166, "facts": 3163, "complete": 3123}
{"edition": 2026, "exhibit": "P-1R", "pages": 41, "facts": 403, "complete": 391}
{"edition": 2026, "exhibit": "R-1", "pages": 102, "facts": 4983, "complete": 4982}
budget PDF receipts: 46682/47081 complete, 21 government documents; audit -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-A2/site/json/budget_pdf_receipts_audit.json
export-site: 16 datasets, 125457 citations, 204 pdfs, 30 workbooks, 8021 unresolved, 4093 zero-amount -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-A2/site
export-site: dossiers 50 written, 45 claim(s) dropped across 12 dossier(s)
```

## 03c-diff-A-A2

```
proof diff: A = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-A/site
proof diff: B = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-A2/site
  build window A ['2026-10-03T11:37:55.949896+00:00', '2026-10-03T11:41:32.582323+00:00'] · B ['2026-10-03T11:55:50.835450+00:00', '2026-10-03T11:59:46.427193+00:00']
  identical 35,033 · equivalent 372 (build stamps, row order, JSON formatting, float/numeric-text noise or a derived hash only) · reordered 163 (control class) · changed 0 · only in A 0 · only in B 0
  equivalent (float noise): 225 file(s), 3,577 value(s) equal to 12 significant digits
  equivalent (derived hash): 2 file(s), 11 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 163 file(s) across 9 class(es)
    [citations/citations.parquet] /inputs ×49
    [citations/citations.parquet] /query_body ×61
    [json/breakdowns/*.json] /rows ×39
    [json/citations.json] /{fid}/inputs ×49
    [json/citations.json] /{fid}/query_body ×61
    [json/cite-shards/*.json] /{fid}/inputs ×49
    [json/cite-shards/*.json] /{fid}/query_body ×61
    [json/districts/*.json] /by_year_programs ×33
    [json/districts/*.json] /programs ×6
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 39 · only in A 0 · only in B 0
  json/citations.json: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/cite-shards/*.json: changed 0 · reordered 88 · only in A 0 · only in B 0
  json/districts/*.json: changed 0 · reordered 34 · only in A 0 · only in B 0
proof diff: EQUAL
```

## 04-B

```
lineage_flow.json: 62059 bytes (budget 160000) — 52 families, 152 identities, 98 stated + 3 inferred edges, 9 unresolved reference(s)
{"edition": 2017, "exhibit": "P-1", "pages": 168, "facts": 6, "complete": 6}
{"edition": 2017, "exhibit": "R-1", "pages": 85, "facts": 2781, "complete": 2778}
{"edition": 2018, "exhibit": "P-1", "pages": 384, "facts": 9, "complete": 9}
{"edition": 2018, "exhibit": "R-1", "pages": 200, "facts": 3123, "complete": 3120}
{"edition": 2019, "exhibit": "P-1", "pages": 396, "facts": 12, "complete": 12}
{"edition": 2019, "exhibit": "R-1", "pages": 312, "facts": 3195, "complete": 3190}
{"edition": 2020, "exhibit": "P-1", "pages": 264, "facts": 15, "complete": 15}
{"edition": 2020, "exhibit": "R-1", "pages": 190, "facts": 3192, "complete": 3187}
{"edition": 2021, "exhibit": "P-1", "pages": 267, "facts": 18, "complete": 18}
{"edition": 2021, "exhibit": "R-1", "pages": 210, "facts": 3396, "complete": 3313}
{"edition": 2022, "exhibit": "P-1", "pages": 88, "facts": 18, "complete": 18}
{"edition": 2022, "exhibit": "R-1", "pages": 88, "facts": 3318, "complete": 3315}
{"edition": 2023, "exhibit": "P-1", "pages": 79, "facts": 15, "complete": 15}
{"edition": 2023, "exhibit": "R-1", "pages": 83, "facts": 3252, "complete": 3249}
{"edition": 2024, "exhibit": "P-1", "pages": 140, "facts": 2715, "complete": 2646}
{"edition": 2024, "exhibit": "R-1", "pages": 94, "facts": 3225, "complete": 3189}
{"edition": 2025, "exhibit": "P-1", "pages": 178, "facts": 2380, "complete": 2352}
{"edition": 2025, "exhibit": "R-1", "pages": 97, "facts": 2934, "complete": 2844}
{"edition": 2026, "exhibit": "P-1", "pages": 166, "facts": 3163, "complete": 3123}
{"edition": 2026, "exhibit": "P-1R", "pages": 41, "facts": 403, "complete": 391}
{"edition": 2026, "exhibit": "R-1", "pages": 102, "facts": 4983, "complete": 4982}
budget PDF receipts: 46682/47081 complete, 21 government documents; audit -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-B/site/json/budget_pdf_receipts_audit.json
export-site: 16 datasets, 125457 citations, 204 pdfs, 30 workbooks, 8021 unresolved, 4093 zero-amount -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-B/site
export-site: dossiers 50 written, 45 claim(s) dropped across 12 dossier(s)
```

## 05-diff-A-B-noise-s0

```
proof diff: A = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-A/site
proof diff: B = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-B/site
  build window A ['2026-10-03T11:37:55.949896+00:00', '2026-10-03T11:41:32.582323+00:00'] · B ['2026-10-03T12:18:52.337043+00:00', '2026-10-03T12:22:27.987991+00:00']
  identical 35,030 · equivalent 373 (build stamps, row order, JSON formatting, float/numeric-text noise or a derived hash only) · reordered 165 (control class) · changed 0 · only in A 0 · only in B 0
  equivalent (float noise): 226 file(s), 3,604 value(s) equal to 12 significant digits
  equivalent (derived hash): 2 file(s), 12 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 165 file(s) across 10 class(es)
    [citations/citations.parquet] /inputs ×47
    [citations/citations.parquet] /query_body ×60
    [json/breakdowns/*.json] /rows ×41
    [json/citations.json] /{fid}/inputs ×47
    [json/citations.json] /{fid}/query_body ×60
    [json/cite-shards/*.json] /{fid}/inputs ×47
    [json/cite-shards/*.json] /{fid}/query_body ×60
    [json/districts/*.json] /by_year_programs ×31
    [json/districts/*.json] /programs ×6
    [json/flows/*.json] /awards ×1
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 41 · only in A 0 · only in B 0
  json/citations.json: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/cite-shards/*.json: changed 0 · reordered 89 · only in A 0 · only in B 0
  json/districts/*.json: changed 0 · reordered 32 · only in A 0 · only in B 0
  json/flows/*.json: changed 0 · reordered 1 · only in A 0 · only in B 0
proof diff: EQUAL
```

## 05-diff-A-B

```
proof diff: A = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-A/site
proof diff: B = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s1-B/site
  build window A ['2026-10-03T11:37:55.949896+00:00', '2026-10-03T11:41:32.582323+00:00'] · B ['2026-10-03T12:18:52.337043+00:00', '2026-10-03T12:22:27.987991+00:00']
  identical 35,030 · equivalent 373 (build stamps, row order, JSON formatting, float/numeric-text noise or a derived hash only) · reordered 164 (control class) · changed 1 · only in A 0 · only in B 0
  equivalent (float noise): 226 file(s), 3,604 value(s) equal to 12 significant digits
  equivalent (derived hash): 2 file(s), 12 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 164 file(s) across 9 class(es)
    [citations/citations.parquet] /inputs ×47
    [citations/citations.parquet] /query_body ×60
    [json/breakdowns/*.json] /rows ×41
    [json/citations.json] /{fid}/inputs ×47
    [json/citations.json] /{fid}/query_body ×60
    [json/cite-shards/*.json] /{fid}/inputs ×47
    [json/cite-shards/*.json] /{fid}/query_body ×60
    [json/districts/*.json] /by_year_programs ×31
    [json/districts/*.json] /programs ×6
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 41 · only in A 0 · only in B 0
  json/citations.json: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/cite-shards/*.json: changed 0 · reordered 89 · only in A 0 · only in B 0
  json/districts/*.json: changed 0 · reordered 32 · only in A 0 · only in B 0
  json/flows/*.json: changed 1 · reordered 0 · only in A 0 · only in B 0
    reordered /awards ×1
proof diff: DIFFERENT
```

## 05x-flows-0605502E-investigation

```
s1-A: 42 grouped award rows for 0605502E; fct_budget_to_awards rows 69
s1-A2: 42 grouped award rows for 0605502E; fct_budget_to_awards rows 69
s1-B: 42 grouped award rows for 0605502E; fct_budget_to_awards rows 69
grouped rows identical as multisets (dollars rounded to cents): A=A2 True | A=B True
rows at $1,500,000.00 (the tie):
   ('W31P4Q17C0103', 'M8KCZYW54M17', 'CA', 'CA-36', 'INFERLINK', 1500000.0)
   ('W31P4Q19C0008', 'SHJDT5DCTLG9', 'IN', 'IN-08', 'MAGNOLIA OPTICAL TECHNOLOGIES', 1500000.0)
top 14 by dollars desc, piid asc (A):
   W31P4Q18C0067 MA-05 4610107.0
   W31P4Q17C0168 CA-51 3379909.15
   W31P4Q17C0154 MA-05 2371877.31
   W31P4Q17C0121 MA-05 1997115.0
   W31P4Q17C0127 NM-01 1748449.0
   W31P4Q18C0083 CA-32 1699976.0
   W31P4Q17C0050 MA-05 1534927.0
   W31P4Q18C0007 OH-11 1506698.0
   W31P4Q17C0103 CA-36 1500000.0
   W31P4Q19C0008 IN-08 1500000.0
   W31P4Q18C0056 OR-01 1499997.0
   W31P4Q18C0055 VA-10 1499977.0
   W31P4Q19C0079 CA-36 1499947.0
   W31P4Q19C0067 CA-15 1499933.0
```

## 06-lake

```
rows: A 159494 | B 159903 | added 409
B starts with A, row for row (15 columns): True
every added row is P-1 / pe_bli 9999999999 / organization '' / title Classified Programs / line_item_code 9999999999: True
added per edition: [('2017', 49), ('2018', 91), ('2019', 91), ('2020', 63), ('2021', 70), ('2022', 21), ('2023', 24)]
other jbooks parquets equal as multisets, A = B: True (8 files)
```

## 07-live-dry-run

```
V1 PB2017 P-1 (doc 189): parse 6832 rows | db 6783 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 49 | line_item_code: null 0, equal 6783, differ 0
V1 PB2018 P-1 (doc 261): parse 13468 rows | db 13377 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 91 | line_item_code: null 0, equal 13377, differ 0
V1 PB2019 P-1 (doc 271): parse 12948 rows | db 12857 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 91 | line_item_code: null 0, equal 12857, differ 0
V1 PB2020 P-1 (doc 282): parse 8838 rows | db 8775 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 63 | line_item_code: null 0, equal 8775, differ 0
V1 PB2021 P-1 (doc 292): parse 10120 rows | db 10050 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 70 | line_item_code: null 0, equal 10050, differ 0
V1 PB2022 P-1 (doc 302): parse 3000 rows | db 2979 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 21 | line_item_code: null 0, equal 2979, differ 0
V1 PB2023 P-1 (doc 312): parse 2925 rows | db 2901 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 24 | line_item_code: null 0, equal 2901, differ 0
V1: CLEAN (7 editions, 58131 parsed rows)
apply: snapshot 84463 P-1/P-1R rows
apply: PB2017 wrote 6832 rows
apply: PB2018 wrote 13468 rows
apply: PB2019 wrote 12948 rows
apply: PB2020 wrote 8838 rows
apply: PB2021 wrote 10120 rows
apply: PB2022 wrote 3000 rows
apply: PB2023 wrote 2925 rows
apply: pre-existing rows changed outside line_item_code: 0
apply: line_item_code equals the parse on 57722 pre-existing era-edition P-1 rows (null before: 0)
apply: rows inserted: 409 (expected 409); P-1/P-1R rows now 84872
apply: era keys 6927, with exactly one line_item_code: 6927
apply: dry run, every check passed: ROLLED BACK
```

## 08-live-apply

```
V1 PB2017 P-1 (doc 189): parse 6832 rows | db 6783 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 49 | line_item_code: null 0, equal 6783, differ 0
V1 PB2018 P-1 (doc 261): parse 13468 rows | db 13377 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 91 | line_item_code: null 0, equal 13377, differ 0
V1 PB2019 P-1 (doc 271): parse 12948 rows | db 12857 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 91 | line_item_code: null 0, equal 12857, differ 0
V1 PB2020 P-1 (doc 282): parse 8838 rows | db 8775 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 63 | line_item_code: null 0, equal 8775, differ 0
V1 PB2021 P-1 (doc 292): parse 10120 rows | db 10050 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 70 | line_item_code: null 0, equal 10050, differ 0
V1 PB2022 P-1 (doc 302): parse 3000 rows | db 2979 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 21 | line_item_code: null 0, equal 2979, differ 0
V1 PB2023 P-1 (doc 312): parse 2925 rows | db 2901 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 24 | line_item_code: null 0, equal 2901, differ 0
V1: CLEAN (7 editions, 58131 parsed rows)
apply: snapshot 84463 P-1/P-1R rows
apply: PB2017 wrote 6832 rows
apply: PB2018 wrote 13468 rows
apply: PB2019 wrote 12948 rows
apply: PB2020 wrote 8838 rows
apply: PB2021 wrote 10120 rows
apply: PB2022 wrote 3000 rows
apply: PB2023 wrote 2925 rows
apply: pre-existing rows changed outside line_item_code: 0
apply: line_item_code equals the parse on 57722 pre-existing era-edition P-1 rows (null before: 0)
apply: rows inserted: 409 (expected 409); P-1/P-1R rows now 84872
apply: era keys 6927, with exactly one line_item_code: 6927
apply: COMMITTED
```

## 09-live-v1-after

```
V1 PB2017 P-1 (doc 189): parse 6832 rows | db 6832 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 0 | line_item_code: null 0, equal 6832, differ 0
V1 PB2018 P-1 (doc 261): parse 13468 rows | db 13468 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 0 | line_item_code: null 0, equal 13468, differ 0
V1 PB2019 P-1 (doc 271): parse 12948 rows | db 12948 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 0 | line_item_code: null 0, equal 12948, differ 0
V1 PB2020 P-1 (doc 282): parse 8838 rows | db 8838 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 0 | line_item_code: null 0, equal 8838, differ 0
V1 PB2021 P-1 (doc 292): parse 10120 rows | db 10120 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 0 | line_item_code: null 0, equal 10120, differ 0
V1 PB2022 P-1 (doc 302): parse 3000 rows | db 3000 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 0 | line_item_code: null 0, equal 3000, differ 0
V1 PB2023 P-1 (doc 312): parse 2925 rows | db 2925 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 0 | line_item_code: null 0, equal 2925, differ 0
V1: CLEAN (7 editions, 58131 parsed rows)
```

## 10-live-export-facts

```
exported: announcement_link_reviews.parquet, award_adjudications.parquet, budget_line_awards.parquet, budget_lines.parquet, detail_narratives.parquet, details.parquet, documents.parquet, program_family.parquet, program_lineage.parquet
```

## 11-live-equals-rehearsal

```
P-1/P-1R rows: live 84872 | rehearsal 84872 | identical (16 columns, in id order): True
lake budget_lines: live 159903 rows | rehearsal 159903 rows | identical row for row: True
```

## 11z-live-after-counts

```
budget_lines rows: 159903
P-1/P-1R rows: 84872
P-1 9999999999 by fiscal_year: [(2017, 49), (2018, 91), (2019, 91), (2020, 63), (2021, 70), (2022, 21), (2023, 24), (2024, 35), (2025, 21), (2026, 29)]
era 9999999999 rows: organization '' / line_item_code 9999999999 / title Classified Programs: (409, 409, 409, 409)
era 9999999999 keys (account, budget_activity, fiscal_year): 50
max id: 581201
live lake budget_lines rows / with line_item_code: (159903, 84872)
```

## 12-crosswalk-empty-org-identities

```
20
```

## 13c-era-keyspace-under-constraint-selector

```
era-edition procurement pe_bli values: 1219 | non-era-key values among them: ['9999999999']
collisions, every era-edition row (the test today): ['9999999999']
collisions, is_era_procurement_key selector: []
unanchored, is_era_procurement_key selector: []
```

## 15-full-suite

```
........                                                                 [100%]
=========================== short test summary info ============================
SKIPPED [1] tests/jbooks/test_xml_parser.py:54: full DARPA xml not on this machine
SKIPPED [1] tests/test_dossiers_research.py:521: live duckdb not present
SKIPPED [1] tests/test_dossiers_research.py:565: live duckdb not present
SKIPPED [1] tests/test_dossiers_research.py:604: live duckdb not present
SKIPPED [1] tests/test_dossiers_research.py:612: live duckdb not present
SKIPPED [1] tests/test_export_entity_families.py:247: no live warehouse
SKIPPED [3] tests/test_load_announcement_links_recipient.py:613: the archived announcements are not on this machine
SKIPPED [1] tests/test_subaward_outlier_sanity.py:188: Subaward parquet lake not present — skipping real-data checks
SKIPPED [1] tests/test_subaward_outlier_sanity.py:205: Subaward parquet lake not present — skipping real-data checks
SKIPPED [1] tests/test_subaward_outlier_sanity.py:235: Subaward parquet lake not present — skipping real-data checks
SKIPPED [1] tests/test_subaward_outlier_sanity.py:252: Subaward parquet lake not present — skipping real-data checks
3739 passed, 13 skipped in 183.32s (0:03:03)
```
