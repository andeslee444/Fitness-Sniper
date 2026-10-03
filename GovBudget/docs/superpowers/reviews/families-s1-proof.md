# Families piece 1 — S1 proof (procurement history before FY2024, Task 8)

Spec: docs/superpowers/specs/2026-10-02-era-procurement-history-design.md §8 V1, §9 S1.
Code: 6809d62c72f72642afc2694c3aab5d9e968bef7b. Snapshot: .proofs/s0 (snapshot.json sha256 5d437b225f26d3a49cd1277b31a15df6305adf61327e74d89466dbaaf19248ff); scratch database govbudget_proof_s0.

Z = the S0 snapshot exported as production reads it (S0 warehouse, S0 lake in heap order).
Z2 = a second export of the same S0 snapshot: the control. Z = Z2 sets the float-noise floor (values equal to 12 significant digits) that every diff below is read against.
A = S0 + migration 021, then jbooks export-facts (id order), govbudget build, export-site.
B = A + scripts/era/s1_reload_era_p1.py --apply, then the same three steps.
Live = the shared database and lake after the same migrate/apply/export-facts.

## Summary (2026-10-03)

**Result.** V1 was CLEAN before any write. The scratch rehearsal (B) and the live run each committed one
transaction whose verifier found 0 pre-existing rows changed outside `line_item_code`, 0 rows inserted, and
6,927 / 6,927 era keys each carrying exactly one code. The site export is unchanged by lake row order and rebuild
(Z = A) and by S1 (A = B). The live database and lake equal the rehearsal.

### Live database, before and after (read-only counts: logs `08z-live-before-counts`, `14z-live-after-counts`)

| `postgresql://localhost/govbudget` | Before (06:53) | After (07:01) |
|---|---|---|
| schema_migrations | 20 (max `020_budget_line_awards_superseded_history.sql`) | 21 (max `021_budget_lines_line_item_code.sql`) |
| `budget_lines.line_item_code` | column absent | present |
| budget_lines rows | 159,494 | 159,494 |
| P-1/P-1R rows | 84,463 | 84,463 |
| Era P-1 rows (PB2017–23: 6,783 · 13,377 · 12,857 · 8,775 · 10,050 · 2,979 · 2,901) | 57,722, no code | 57,722, all coded (null 0) |
| Era keys with exactly one non-null code | — | 6,927 / 6,927 |
| Non-era P-1/P-1R rows whose code ≠ pe_bli | — | 0 |
| Coded rows outside P-1/P-1R | — | 0 |
| Live lake `parquet/jbooks/budget_lines.parquet` | 159,494 rows, no column (Sep 26) | 159,494 rows, `line_item_code`, id order; row for row equal to the rehearsal |

### The control and the noise file

- The Z vs Z2 control is in log `11-rejudge-control-Z-Z2` (proof tool at fix round 5, `6809d62c`, run by the
  tool owner): `identical 35,036 · equivalent 369 · reordered 163 (control class) · changed 0 · only in A 0 ·
  only in B 0`; float noise 224 files / 3,635 values; derived hash 2 files / 10 values; `proof diff: EQUAL`.
  It wrote `.proofs/s1-logs/noise-s0.json`: schema 1, verdict EQUAL, 10 reorder classes,
  `classes_sha256 963c39010e43d9e118b3f468d9711b09723fea6af2253d6ab2cdb2f5b1e5503f`, file sha256
  `b947523b6a17a766f12a869cd8e7ce5a8b71f32d6645664605f77893209574b9`. The classes, with `{fid}` standing for a
  16-hex fact ID:
  `citations/citations.parquet /inputs`, `citations/citations.parquet /query_body`,
  `json/breakdowns/*.json /rows`, `json/citations.json /{fid}/inputs`, `json/citations.json /{fid}/query_body`,
  `json/cite-shards/*.json /{fid}/inputs`, `json/cite-shards/*.json /{fid}/query_body`,
  `json/districts/*.json /by_year_programs`, `json/districts/*.json /programs`, `json/flows/*.json /awards`.
  So the noise floor that Z = Z2 sets is float noise (12 significant digits, with an absolute floor near zero),
  derived hashes, and these pure-permutation classes. Adds, removes and substitutions still read "changed".
- History, kept for the record: `03c0-diff-Z-Z2-no-control` is the first plain (no `--control`) diff,
  DIFFERENT, 166 files. `03c-diff-Z-Z2` is the same control under fix round 4 (`be1f8748`), EQUAL with 230
  per-fact-ID classes. Under those per-fact-ID classes the judged diffs read DIFFERENT
  (`06-…-before-fid-generalisation`: 28 changed; `07-…-before-fid-generalisation`: 38 changed). Every one of
  those changes was a pure permutation of derived `inputs` or usaspending `award_ids` on a fact ID the control
  had not happened to reorder. Fix round 5 generalised fact-ID segments to `{fid}`.

### Step 11 re-judge (fix round 5, `--noise-from noise-s0.json`)

- Z vs A (`06-diff-Z-A`): `identical 35,038 · equivalent 373 · reordered 157 (control class) · changed 0 · only in
  A 0 · only in B 0`; float noise 221 files / 3,650 values; derived hash 2 files / 12 values; 10 classes;
  **`proof diff: EQUAL`**.
- A vs B (`07-diff-A-B`): `identical 35,037 · equivalent 373 · reordered 158 (control class) · changed 0 · only in
  A 0 · only in B 0`; float noise 227 files / 3,588 values; derived hash 2 files / 10 values; 9 classes;
  **`proof diff: EQUAL`**.
- The tool owner's independent runs (`11-rejudge-Z-A`, `11-rejudge-A-B`) give the same counts.

### Rehearsal on the scratch database (B; full log `05-B`, its tail below shows only export-site)

The `--check` reported each edition `null <n>, equal 0, differ 0` and `V1: CLEAN (7 editions, 57722 parsed rows)`.
Then `--apply`: `snapshot 84463 P-1/P-1R rows`; the seven `wrote` lines; `pre-existing rows changed outside
line_item_code: 0`; `line_item_code equals the parse on 57722 pre-existing era-edition P-1 rows (null before:
57722)`; `rows inserted: 0 (expected 0); P-1/P-1R rows now 84463`; `era keys 6927, with exactly one
line_item_code: 6927`; `COMMITTED`. dbt in A and in B: `Done. PASS=204 WARN=2 ERROR=0 SKIP=0 NO-OP=0 TOTAL=206`
(the two pre-existing warn tests: `warn_subaward_amount_exceeds_50b` 3, `warn_lda_amendment_latest_undetermined` 7).
Lake check (`08-lake`): only `line_item_code` changed, on the 57,722 era P-1 rows.

### Full suite (Step 17) and the coordinator's ruling

Ruling (coordinator, 2026-10-03): run the full suite with `scripts/era/env.sh` sourced in the same command
(`GOVBUDGET_DATA` set, as every plan command does) plus the inline test DSN. The `test_config` symlink test fails
only when `GOVBUDGET_DATA` is unset in this worktree (no `data/raw` here, so `RAW_DIR` names a worktree path).
Result: **`3736 passed, 13 skipped`, 0 failed** (log `15-full-suite`). The brief's literal command (variables
unset) gave `1 failed, 3728 passed, 20 skipped`, the one failure being
`tests/test_config.py::test_lake_dirs_are_symlink_resolved`. Neither that test nor `config.py` changes on this
branch.

### Evidence location

`.proofs/s1-logs/` (every log below in full, the JSON diff reports, `noise-s0.json`) and `.proofs/s0` (its `pg/`
holds `govbudget.dump`, sha256 `eee56251da084cf7c10370c1b0f66d8a31ed4e5e69b7d8070cbfa62c33dfc0a0`, the
pristine pre-S1 database) stay until the release (Task 23). The run clones Z, Z2, A, B and the scratch
database are removed in Step 19.

Each section below is the last 25 lines of one log.

## 01-v1-live

```
V1 PB2017 P-1 (doc 189): parse 6783 rows | db 6783 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2018 P-1 (doc 261): parse 13377 rows | db 13377 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2019 P-1 (doc 271): parse 12857 rows | db 12857 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2020 P-1 (doc 282): parse 8775 rows | db 8775 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2021 P-1 (doc 292): parse 10050 rows | db 10050 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2022 P-1 (doc 302): parse 2979 rows | db 2979 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1 PB2023 P-1 (doc 312): parse 2901 rows | db 2901 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: column absent
V1: CLEAN (7 editions, 57722 parsed rows)
```

## 02-snapshot

```
proof snapshot: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0
  duckdb sha256 79b1bca75dbb47f958ee4271a7d07147c085172fc1fea78206694b70492e6293 (18 of 37 views repointed)
  parquet files 112 · site files 35,520 · raw_docs files 1,112
  postgres govbudget -> govbudget_proof_s0 (18 tables, dump sha256 eee56251da084cf7c10370c1b0f66d8a31ed4e5e69b7d8070cbfa62c33dfc0a0)
  source /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0/env.sh [RUN_DIR]
```

## 03-export-Z

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
budget PDF receipts: 46682/47081 complete, 21 government documents; audit -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z/site/json/budget_pdf_receipts_audit.json
export-site: 16 datasets, 125457 citations, 204 pdfs, 30 workbooks, 8021 unresolved, 4093 zero-amount -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z/site
export-site: dossiers 50 written, 45 claim(s) dropped across 12 dossier(s)
```

## 03b-export-Z2

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
budget PDF receipts: 46682/47081 complete, 21 government documents; audit -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z2/site/json/budget_pdf_receipts_audit.json
export-site: 16 datasets, 125457 citations, 204 pdfs, 30 workbooks, 8021 unresolved, 4093 zero-amount -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z2/site
export-site: dossiers 50 written, 45 claim(s) dropped across 12 dossier(s)
```

## 03c-diff-Z-Z2

```
proof diff: A = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z/site
proof diff: B = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z2/site
  build window A ['2026-10-03T08:24:45.224218+00:00', '2026-10-03T08:27:50.295062+00:00'] · B ['2026-10-03T08:39:07.778267+00:00', '2026-10-03T08:42:11.417517+00:00']
  identical 35,036 · equivalent 369 (build stamps, row order, JSON formatting, float/numeric-text noise or a derived hash only) · reordered 163 (control class) · changed 0 · only in A 0 · only in B 0
  equivalent (float noise): 224 file(s), 3,635 value(s) equal to 12 significant digits
  equivalent (derived hash): 2 file(s), 10 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 163 file(s) across 230 class(es)
    [citations/citations.parquet] /inputs ×42
    [citations/citations.parquet] /query_body ×70
    [json/breakdowns/*.json] /rows ×36
    [json/citations.json] /071b51045d67f20e/inputs ×1
    [json/citations.json] /08f2a77a71a04fac/query_body ×1
    [json/citations.json] /09266f9e3fe6bb68/inputs ×1
    [json/citations.json] /0dbb5d7b633dbe35/query_body ×1
    [json/citations.json] /1191456e4add9e40/query_body ×1
    [json/citations.json] /11e49f1f7770ab8a/query_body ×1
    [json/citations.json] /133a80339086aa8d/query_body ×1
    +220 more (see --report)
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 36 · only in A 0 · only in B 0
  json/citations.json: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/cite-shards/*.json: changed 0 · reordered 90 · only in A 0 · only in B 0
  json/districts/*.json: changed 0 · reordered 34 · only in A 0 · only in B 0
  json/flows/*.json: changed 0 · reordered 1 · only in A 0 · only in B 0
proof diff: EQUAL
```

## 03c0-diff-Z-Z2-no-control

```
  citations/citations.parquet: changed 1 · only in A 0 · only in B 0
    parquet rows 125,457 -> 125,457; only in A 113, only in B 113 ×1
  json/breakdowns/*.json: changed 36 · only in A 0 · only in B 0
    reordered /rows ×36
  json/budget_pdf_receipts_audit.json: changed 1 · only in A 0 · only in B 0
    changed /citation_sha256 ×1
  json/citations.json: changed 1 · only in A 0 · only in B 0
    changed /{fid}/query_body ×70
    changed /{fid}/inputs ×42
    changed /{fid}/recorded_value ×1
  json/cite-shards/*.json: changed 90 · only in A 0 · only in B 0
    changed /{fid}/query_body ×70
    changed /{fid}/inputs ×42
    changed /{fid}/recorded_value ×1
  json/datasets.json: changed 1 · only in A 0 · only in B 0
    added /datasets/[] ×9
    removed /datasets/[] ×9
  json/districts/*.json: changed 35 · only in A 0 · only in B 0
    reordered /by_year_programs ×33
    reordered /programs ×5
    added /by_year_programs/[] ×1
    removed /by_year_programs/[] ×1
  json/flows/*.json: changed 1 · only in A 0 · only in B 0
    reordered /awards ×1
proof diff: DIFFERENT
```

## 04-A

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
budget PDF receipts: 46682/47081 complete, 21 government documents; audit -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-A/site/json/budget_pdf_receipts_audit.json
export-site: 16 datasets, 125457 citations, 204 pdfs, 30 workbooks, 8021 unresolved, 4093 zero-amount -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-A/site
export-site: dossiers 50 written, 45 claim(s) dropped across 12 dossier(s)
```

## 05-B

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
budget PDF receipts: 46682/47081 complete, 21 government documents; audit -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-B/site/json/budget_pdf_receipts_audit.json
export-site: 16 datasets, 125457 citations, 204 pdfs, 30 workbooks, 8021 unresolved, 4093 zero-amount -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-B/site
export-site: dossiers 50 written, 45 claim(s) dropped across 12 dossier(s)
```

## 06-diff-Z-A-before-fid-generalisation

```
  reordered (control class): 130 file(s) across 168 class(es)
    [citations/citations.parquet] /inputs ×46
    [citations/citations.parquet] /query_body ×65
    [json/breakdowns/*.json] /rows ×35
    [json/citations.json] /071b51045d67f20e/inputs ×1
    [json/citations.json] /09266f9e3fe6bb68/inputs ×1
    [json/citations.json] /0dbb5d7b633dbe35/query_body ×1
    [json/citations.json] /1191456e4add9e40/query_body ×1
    [json/citations.json] /11e49f1f7770ab8a/query_body ×1
    [json/citations.json] /133a80339086aa8d/query_body ×1
    [json/citations.json] /193d225abe9cca95/inputs ×1
    +158 more (see --report)
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 35 · only in A 0 · only in B 0
  json/budget_pdf_receipts_audit.json: changed 1 · reordered 0 · only in A 0 · only in B 0
    changed /citation_sha256 ×1
  json/citations.json: changed 1 · reordered 0 · only in A 0 · only in B 0
    changed /{fid}/query_body ×22
    changed /{fid}/inputs ×8
  json/cite-shards/*.json: changed 26 · reordered 62 · only in A 0 · only in B 0
    changed /{fid}/query_body ×22
    changed /{fid}/inputs ×8
  json/districts/*.json: changed 0 · reordered 31 · only in A 0 · only in B 0
  json/flows/*.json: changed 0 · reordered 1 · only in A 0 · only in B 0
proof diff: DIFFERENT
```

## 06-diff-Z-A

```
proof diff: A = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z/site
proof diff: B = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-A/site
  build window A ['2026-10-03T08:24:45.224218+00:00', '2026-10-03T08:27:50.295062+00:00'] · B ['2026-10-03T10:12:53.218055+00:00', '2026-10-03T10:15:55.141772+00:00']
  identical 35,038 · equivalent 373 (build stamps, row order, JSON formatting, float/numeric-text noise or a derived hash only) · reordered 157 (control class) · changed 0 · only in A 0 · only in B 0
  equivalent (float noise): 221 file(s), 3,650 value(s) equal to 12 significant digits
  equivalent (derived hash): 2 file(s), 12 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 157 file(s) across 10 class(es)
    [citations/citations.parquet] /inputs ×46
    [citations/citations.parquet] /query_body ×65
    [json/breakdowns/*.json] /rows ×35
    [json/citations.json] /{fid}/inputs ×46
    [json/citations.json] /{fid}/query_body ×65
    [json/cite-shards/*.json] /{fid}/inputs ×46
    [json/cite-shards/*.json] /{fid}/query_body ×65
    [json/districts/*.json] /by_year_programs ×31
    [json/districts/*.json] /programs ×9
    [json/flows/*.json] /awards ×1
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 35 · only in A 0 · only in B 0
  json/citations.json: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/cite-shards/*.json: changed 0 · reordered 88 · only in A 0 · only in B 0
  json/districts/*.json: changed 0 · reordered 31 · only in A 0 · only in B 0
  json/flows/*.json: changed 0 · reordered 1 · only in A 0 · only in B 0
proof diff: EQUAL
```

## 07-diff-A-B-before-fid-generalisation

```
  equivalent (derived hash): 1 file(s), 9 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 121 file(s) across 155 class(es)
    [citations/citations.parquet] /inputs ×46
    [citations/citations.parquet] /query_body ×67
    [json/breakdowns/*.json] /rows ×35
    [json/citations.json] /071b51045d67f20e/inputs ×1
    [json/citations.json] /09266f9e3fe6bb68/inputs ×1
    [json/citations.json] /0dbb5d7b633dbe35/query_body ×1
    [json/citations.json] /1191456e4add9e40/query_body ×1
    [json/citations.json] /133a80339086aa8d/query_body ×1
    [json/citations.json] /193d225abe9cca95/inputs ×1
    [json/citations.json] /227abd03fe02f490/inputs ×1
    +145 more (see --report)
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 35 · only in A 0 · only in B 0
  json/budget_pdf_receipts_audit.json: changed 1 · reordered 0 · only in A 0 · only in B 0
    changed /citation_sha256 ×1
  json/citations.json: changed 1 · reordered 0 · only in A 0 · only in B 0
    changed /{fid}/query_body ×26
    changed /{fid}/inputs ×12
  json/cite-shards/*.json: changed 36 · reordered 57 · only in A 0 · only in B 0
    changed /{fid}/query_body ×26
    changed /{fid}/inputs ×12
  json/districts/*.json: changed 0 · reordered 28 · only in A 0 · only in B 0
proof diff: DIFFERENT
```

## 07-diff-A-B

```
proof diff: A = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-A/site
proof diff: B = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-B/site
  build window A ['2026-10-03T10:12:53.218055+00:00', '2026-10-03T10:15:55.141772+00:00'] · B ['2026-10-03T10:30:45.371750+00:00', '2026-10-03T10:33:47.521936+00:00']
  identical 35,037 · equivalent 373 (build stamps, row order, JSON formatting, float/numeric-text noise or a derived hash only) · reordered 158 (control class) · changed 0 · only in A 0 · only in B 0
  equivalent (float noise): 227 file(s), 3,588 value(s) equal to 12 significant digits
  equivalent (derived hash): 2 file(s), 10 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 158 file(s) across 9 class(es)
    [citations/citations.parquet] /inputs ×46
    [citations/citations.parquet] /query_body ×67
    [json/breakdowns/*.json] /rows ×35
    [json/citations.json] /{fid}/inputs ×46
    [json/citations.json] /{fid}/query_body ×67
    [json/cite-shards/*.json] /{fid}/inputs ×46
    [json/cite-shards/*.json] /{fid}/query_body ×67
    [json/districts/*.json] /by_year_programs ×26
    [json/districts/*.json] /programs ×9
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 35 · only in A 0 · only in B 0
  json/citations.json: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/cite-shards/*.json: changed 0 · reordered 93 · only in A 0 · only in B 0
  json/districts/*.json: changed 0 · reordered 28 · only in A 0 · only in B 0
proof diff: EQUAL
```

## 08-lake

```
rows: S0 159494 | A 159494 | B 159494
A == S0 on the 14 S0 columns as a multiset: True
B == A on the 14 S0 columns, row for row: True
A: era P-1 rows null 57722, coded 0 | non-era P-1/P-1R rows whose code != pe_bli 0 | coded R-1 rows 0
B: era P-1 rows null 0, coded 57722 | non-era P-1/P-1R rows whose code != pe_bli 0 | coded R-1 rows 0
rows whose line_item_code differs A -> B: 57722
other jbooks parquets equal as multisets, S0 = A = B: True (8 files)
```

## 08z-live-before-counts

```
dsn postgresql://localhost/govbudget | line_item_code column: False
schema_migrations: (20, '020_budget_line_awards_superseded_history.sql')
budget_lines total: 159494
  P-1 FY2017: rows 6783 keys 969 era-key rows 6783
  P-1 FY2018: rows 13377 keys 1029 era-key rows 13377
  P-1 FY2019: rows 12857 keys 989 era-key rows 12857
  P-1 FY2020: rows 8775 keys 975 era-key rows 8775
  P-1 FY2021: rows 10050 keys 1005 era-key rows 10050
  P-1 FY2022: rows 2979 keys 993 era-key rows 2979
  P-1 FY2023: rows 2901 keys 967 era-key rows 2901
  P-1 FY2024: rows 4585 keys 917 era-key rows 0
  P-1 FY2025: rows 2432 keys 940 era-key rows 0
  P-1 FY2026: rows 3163 keys 910 era-key rows 0
  P-1R FY2017: rows 3080 keys 280 era-key rows 0
  P-1R FY2018: rows 3055 keys 235 era-key rows 0
  P-1R FY2019: rows 3289 keys 253 era-key rows 0
  P-1R FY2020: rows 2169 keys 241 era-key rows 0
  P-1R FY2021: rows 2300 keys 230 era-key rows 0
  P-1R FY2022: rows 651 keys 217 era-key rows 0
  P-1R FY2023: rows 582 keys 194 era-key rows 0
  P-1R FY2024: rows 582 keys 194 era-key rows 0
  P-1R FY2025: rows 450 keys 199 era-key rows 0
  P-1R FY2026: rows 403 keys 175 era-key rows 0
P-1/P-1R rows: 84463
```

## 09-live-migrate

```
migrations applied: ['021_budget_lines_line_item_code.sql']
```

## 10-live-dry-run

```
V1 PB2017 P-1 (doc 189): parse 6783 rows | db 6783 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 6783, equal 0, differ 0
V1 PB2018 P-1 (doc 261): parse 13377 rows | db 13377 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 13377, equal 0, differ 0
V1 PB2019 P-1 (doc 271): parse 12857 rows | db 12857 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 12857, equal 0, differ 0
V1 PB2020 P-1 (doc 282): parse 8775 rows | db 8775 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 8775, equal 0, differ 0
V1 PB2021 P-1 (doc 292): parse 10050 rows | db 10050 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 10050, equal 0, differ 0
V1 PB2022 P-1 (doc 302): parse 2979 rows | db 2979 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 2979, equal 0, differ 0
V1 PB2023 P-1 (doc 312): parse 2901 rows | db 2901 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 2901, equal 0, differ 0
V1: CLEAN (7 editions, 57722 parsed rows)
apply: snapshot 84463 P-1/P-1R rows
apply: PB2017 wrote 6783 rows
apply: PB2018 wrote 13377 rows
apply: PB2019 wrote 12857 rows
apply: PB2020 wrote 8775 rows
apply: PB2021 wrote 10050 rows
apply: PB2022 wrote 2979 rows
apply: PB2023 wrote 2901 rows
apply: pre-existing rows changed outside line_item_code: 0
apply: line_item_code equals the parse on 57722 pre-existing era-edition P-1 rows (null before: 57722)
apply: rows inserted: 0 (expected 0); P-1/P-1R rows now 84463
apply: era keys 6927, with exactly one line_item_code: 6927
apply: dry run, every check passed: ROLLED BACK
```

## 11-live-apply

```
V1 PB2017 P-1 (doc 189): parse 6783 rows | db 6783 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 6783, equal 0, differ 0
V1 PB2018 P-1 (doc 261): parse 13377 rows | db 13377 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 13377, equal 0, differ 0
V1 PB2019 P-1 (doc 271): parse 12857 rows | db 12857 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 12857, equal 0, differ 0
V1 PB2020 P-1 (doc 282): parse 8775 rows | db 8775 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 8775, equal 0, differ 0
V1 PB2021 P-1 (doc 292): parse 10050 rows | db 10050 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 10050, equal 0, differ 0
V1 PB2022 P-1 (doc 302): parse 2979 rows | db 2979 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 2979, equal 0, differ 0
V1 PB2023 P-1 (doc 312): parse 2901 rows | db 2901 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 2901, equal 0, differ 0
V1: CLEAN (7 editions, 57722 parsed rows)
apply: snapshot 84463 P-1/P-1R rows
apply: PB2017 wrote 6783 rows
apply: PB2018 wrote 13377 rows
apply: PB2019 wrote 12857 rows
apply: PB2020 wrote 8775 rows
apply: PB2021 wrote 10050 rows
apply: PB2022 wrote 2979 rows
apply: PB2023 wrote 2901 rows
apply: pre-existing rows changed outside line_item_code: 0
apply: line_item_code equals the parse on 57722 pre-existing era-edition P-1 rows (null before: 57722)
apply: rows inserted: 0 (expected 0); P-1/P-1R rows now 84463
apply: era keys 6927, with exactly one line_item_code: 6927
apply: COMMITTED
```

## 11-rejudge-A-B

```
proof diff: A = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-A/site
proof diff: B = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-B/site
  build window A ['2026-10-03T10:12:53.218055+00:00', '2026-10-03T10:15:55.141772+00:00'] · B ['2026-10-03T10:30:45.371750+00:00', '2026-10-03T10:33:47.521936+00:00']
  identical 35,037 · equivalent 373 (build stamps, row order, JSON formatting, float/numeric-text noise or a derived hash only) · reordered 158 (control class) · changed 0 · only in A 0 · only in B 0
  equivalent (float noise): 227 file(s), 3,588 value(s) equal to 12 significant digits
  equivalent (derived hash): 2 file(s), 10 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 158 file(s) across 9 class(es)
    [citations/citations.parquet] /inputs ×46
    [citations/citations.parquet] /query_body ×67
    [json/breakdowns/*.json] /rows ×35
    [json/citations.json] /{fid}/inputs ×46
    [json/citations.json] /{fid}/query_body ×67
    [json/cite-shards/*.json] /{fid}/inputs ×46
    [json/cite-shards/*.json] /{fid}/query_body ×67
    [json/districts/*.json] /by_year_programs ×26
    [json/districts/*.json] /programs ×9
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 35 · only in A 0 · only in B 0
  json/citations.json: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/cite-shards/*.json: changed 0 · reordered 93 · only in A 0 · only in B 0
  json/districts/*.json: changed 0 · reordered 28 · only in A 0 · only in B 0
proof diff: EQUAL
```

## 11-rejudge-Z-A

```
proof diff: A = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z/site
proof diff: B = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-A/site
  build window A ['2026-10-03T08:24:45.224218+00:00', '2026-10-03T08:27:50.295062+00:00'] · B ['2026-10-03T10:12:53.218055+00:00', '2026-10-03T10:15:55.141772+00:00']
  identical 35,038 · equivalent 373 (build stamps, row order, JSON formatting, float/numeric-text noise or a derived hash only) · reordered 157 (control class) · changed 0 · only in A 0 · only in B 0
  equivalent (float noise): 221 file(s), 3,650 value(s) equal to 12 significant digits
  equivalent (derived hash): 2 file(s), 12 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 157 file(s) across 10 class(es)
    [citations/citations.parquet] /inputs ×46
    [citations/citations.parquet] /query_body ×65
    [json/breakdowns/*.json] /rows ×35
    [json/citations.json] /{fid}/inputs ×46
    [json/citations.json] /{fid}/query_body ×65
    [json/cite-shards/*.json] /{fid}/inputs ×46
    [json/cite-shards/*.json] /{fid}/query_body ×65
    [json/districts/*.json] /by_year_programs ×31
    [json/districts/*.json] /programs ×9
    [json/flows/*.json] /awards ×1
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 35 · only in A 0 · only in B 0
  json/citations.json: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/cite-shards/*.json: changed 0 · reordered 88 · only in A 0 · only in B 0
  json/districts/*.json: changed 0 · reordered 31 · only in A 0 · only in B 0
  json/flows/*.json: changed 0 · reordered 1 · only in A 0 · only in B 0
proof diff: EQUAL
```

## 11-rejudge-control-Z-Z2

```
proof diff: A = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z/site
proof diff: B = /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s0-Z2/site
  build window A ['2026-10-03T08:24:45.224218+00:00', '2026-10-03T08:27:50.295062+00:00'] · B ['2026-10-03T08:39:07.778267+00:00', '2026-10-03T08:42:11.417517+00:00']
  identical 35,036 · equivalent 369 (build stamps, row order, JSON formatting, float/numeric-text noise or a derived hash only) · reordered 163 (control class) · changed 0 · only in A 0 · only in B 0
  equivalent (float noise): 224 file(s), 3,635 value(s) equal to 12 significant digits
  equivalent (derived hash): 2 file(s), 10 value(s) — a content hash or byte count of a file that compared equivalent
  reordered (control class): 163 file(s) across 10 class(es)
    [citations/citations.parquet] /inputs ×42
    [citations/citations.parquet] /query_body ×70
    [json/breakdowns/*.json] /rows ×36
    [json/citations.json] /{fid}/inputs ×42
    [json/citations.json] /{fid}/query_body ×70
    [json/cite-shards/*.json] /{fid}/inputs ×42
    [json/cite-shards/*.json] /{fid}/query_body ×70
    [json/districts/*.json] /by_year_programs ×33
    [json/districts/*.json] /programs ×5
    [json/flows/*.json] /awards ×1
  citations/citations.parquet: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/breakdowns/*.json: changed 0 · reordered 36 · only in A 0 · only in B 0
  json/citations.json: changed 0 · reordered 1 · only in A 0 · only in B 0
  json/cite-shards/*.json: changed 0 · reordered 90 · only in A 0 · only in B 0
  json/districts/*.json: changed 0 · reordered 34 · only in A 0 · only in B 0
  json/flows/*.json: changed 0 · reordered 1 · only in A 0 · only in B 0
proof diff: EQUAL
```

## 12-live-v1-after

```
V1 PB2017 P-1 (doc 189): parse 6783 rows | db 6783 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 0, equal 6783, differ 0
V1 PB2018 P-1 (doc 261): parse 13377 rows | db 13377 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 0, equal 13377, differ 0
V1 PB2019 P-1 (doc 271): parse 12857 rows | db 12857 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 0, equal 12857, differ 0
V1 PB2020 P-1 (doc 282): parse 8775 rows | db 8775 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 0, equal 8775, differ 0
V1 PB2021 P-1 (doc 292): parse 10050 rows | db 10050 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 0, equal 10050, differ 0
V1 PB2022 P-1 (doc 302): parse 2979 rows | db 2979 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 0, equal 2979, differ 0
V1 PB2023 P-1 (doc 312): parse 2901 rows | db 2901 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | line_item_code: null 0, equal 2901, differ 0
V1: CLEAN (7 editions, 57722 parsed rows)
```

## 13-live-export-facts

```
exported: announcement_link_reviews.parquet, award_adjudications.parquet, budget_line_awards.parquet, budget_lines.parquet, detail_narratives.parquet, details.parquet, documents.parquet, program_family.parquet, program_lineage.parquet
```

## 14-live-equals-rehearsal

```
P-1/P-1R rows: live 84463 | rehearsal 84463 | identical (17 columns, by id): True
lake budget_lines: live 159494 rows | rehearsal 159494 rows | identical row for row: True
```

## 14z-live-after-counts

```
  P-1 FY2017: rows 6783 keys 969 era-key rows 6783
  P-1 FY2018: rows 13377 keys 1029 era-key rows 13377
  P-1 FY2019: rows 12857 keys 989 era-key rows 12857
  P-1 FY2020: rows 8775 keys 975 era-key rows 8775
  P-1 FY2021: rows 10050 keys 1005 era-key rows 10050
  P-1 FY2022: rows 2979 keys 993 era-key rows 2979
  P-1 FY2023: rows 2901 keys 967 era-key rows 2901
  P-1 FY2024: rows 4585 keys 917 era-key rows 0
  P-1 FY2025: rows 2432 keys 940 era-key rows 0
  P-1 FY2026: rows 3163 keys 910 era-key rows 0
  P-1R FY2017: rows 3080 keys 280 era-key rows 0
  P-1R FY2018: rows 3055 keys 235 era-key rows 0
  P-1R FY2019: rows 3289 keys 253 era-key rows 0
  P-1R FY2020: rows 2169 keys 241 era-key rows 0
  P-1R FY2021: rows 2300 keys 230 era-key rows 0
  P-1R FY2022: rows 651 keys 217 era-key rows 0
  P-1R FY2023: rows 582 keys 194 era-key rows 0
  P-1R FY2024: rows 582 keys 194 era-key rows 0
  P-1R FY2025: rows 450 keys 199 era-key rows 0
  P-1R FY2026: rows 403 keys 175 era-key rows 0
P-1/P-1R rows: 84463
era P-1 rows null/coded: (0, 57722)
era keys / with exactly one non-null code: (6927, 6927)
non-era P-1/P-1R code != pe_bli: 0
coded rows outside P-1/P-1R: 0
```

## 15-full-suite

```
# Step 17 (coordinator ruling 2026-10-03): full suite with scripts/era/env.sh sourced (GOVBUDGET_DATA/DUCKDB/PG_DSN set) + GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres, 07:06:30-07:09:33
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
3736 passed, 13 skipped in 180.61s (0:03:00)
# earlier run with GOVBUDGET_DATA/PG_DSN/DUCKDB unset (brief's literal command), 07:01:29-07:04:30: 1 failed, 3728 passed, 20 skipped — tests/test_config.py::test_lake_dirs_are_symlink_resolved (RAW_DIR names a worktree view: the worktree has no data/raw)
```
