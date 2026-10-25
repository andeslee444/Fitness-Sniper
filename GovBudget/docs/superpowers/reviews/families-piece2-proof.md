# Families piece 2 — the registry proof (Task 9b)

Spec: docs/superpowers/specs/2026-10-20-families-piece2-registry-design.md §14, §16.
Code: A = `00b599a6e315f0ee265b9f4993332dc1e7c68879` (`git merge-base main HEAD`, the contract-link fix's
release under D1); its src/, dbt/, data-seeds/, scripts/ and site/ equal the deployed
`9dce8219eca59a4564cc069eccfd342d4cf4d375` (Task 1's `A:` line, re-checked in Task 9a Step 1). B =
`e48ab21b8bed9af4eb1f6f3bd74e905dcd469ec8` [a_sha.txt, b_sha.txt].
Snapshot: `.proofs/fam2` (scratch database govbudget_proof_fam2), taken 2026-10-24T14:29:14.012795+00:00
[snapshot-shas.json], after the link fix's live dbt build: its DuckDB holds `link_line_rulings` and
`link_award_keys` with its five columns (the holdings the controller proved at the snapshot, ledger
`proof-logs/fam2-snapshot.md`). The DuckDB file of fam2, fam2-A and fam2-B still hashes
c9e75aa9fc733b21b2051697180887c78dbd5430b9b06a21785a2d8b242bfd4a, the post-repoint sha `fam2/snapshot.json`
records (re-hashed read-only on 2026-10-25 for this note).

Every bracketed log is under `.proofs/fam2-logs/`; Task 10c copies them into the ledger. Times are EDT unless
they carry `+00:00`.

A@fam2 = the deployed code's export of fam2 (clone `fam2-A`). B@fam2 = the piece-2 code's export of the same
snapshot (`fam2-B`). B2@fam2 = a second export of B's state: the control (`fam2-B2`). fam2-B-eval = a copy of
fam2-B whose DuckDB views read its own parquet, made for `verify-phase5`'s paid eval (R-PF-20; see Re-runs).

## Summary (2026-10-25)

**Result.** On the pinned snapshot fam2, B's export differs from A's in exactly §16's two data rows:
`json/families/index.json` only in B (833 bytes, sha256 3657d3bd36fa8f344cf2c299714dacb11fe227100cd1ff0c3d3d22f6734f1945,
equal to D7's projection: the F-15 alone, with its 8 counted members) and `manifest.json` `/json_sidecars` +1
(36,034 → 36,035). The control reads EQUAL. The F-15 history is byte-identical (the pinned sha256 on A, B and B2),
and no fact is added, removed or changed (143,804 citations on each side). Link coverage prints the same lines on
A and B, PASS with 0 violations on each. Built over each export, `/families/f-15/` and `/methodology/` weigh the same raw bytes on A and B (705,056
and 161,453, also Task 1's `base-weight:`), and each page is identical on A and B once the build ID and the export
stamps are masked; the F-15 page snapshot passes on both builds. Every gate passes on B's export:
verify-era-map, verify-families, verify-phase5b1, verify-phase5e, verify-lineage, `evals check`, `npm run verify`
(27 gates; gate 21's leg (r) green for the first time, K1, beside the link fix's leg (q)), vitest, pytest on 55432
(4,914 passed), W1 at the Task 1 baselines, and `verify-phase5` (whose assembly now includes verify-families). The
`verify-phase5` PASS is its third run, on the eval clone fam2-B-eval under R-PF-20 and R-PF-20a; the first two runs
failed for causes outside B, and `### Re-runs` records both. The owner ratified F-35 batch B1 on 2026-10-25; the
F-35 appears nowhere in the export.

### Snapshot [snapshot-shas.json, snapshot.log]

| Pin | Value |
|---|---|
| created | 2026-10-24T14:29:14.012795+00:00 |
| `duckdb_sha256_at_copy` | ad706b4370321d6106e4006592a02abcc6ab86f5581c8eae0dfbcbe39cd6a179 |
| `parquet_files_minus_sam` / `parquet_minus_sam_sha256` | 107 / ab00a63f0918316e887190a96e15fb7b630e578ff0dc3ac99486eb7275fb0209 |
| `site_sha256` | 682cc2055aff85a5fd280c1ba2d74c92290d6332df139d3293328d8fa7e30e9d |
| `raw_docs_sha256` | 320c7d9106b8422277fd965bdb26b2fcc94a67f71dab49d0a9798704fc7f3f27 |
| `manifest_jsonl_sha256` | bc4e8b141e15088e41915b0eb8392addf2da1e704f476581dbf04e0da8db0e35 |
| `pg_tables` / `pg_tables_sha256` | 18 / 8842437e6c44074b6b391a412a2b85ccc73489460b8fb70cec7a52c3592ba765 |
| `pg_dump_sha256` (not a pin) | cdc7760db152f9b28e16f56e58c595768a69314f471b320f9c71f04d4563bb94 |

snapshot.log: parquet files 112 · site files 36,328 · raw_docs files 1,112; 18 of 37 DuckDB views repointed.

### Exports and diffs [export-fam2-A.log, export-fam2-B.log, export-fam2-B2.log, diff-control.txt, noise-B-B2.json, diff-code.txt, diff-code-report.json, sidecars.txt]

- **Exports** (Task 9a Step 4; A 10:54–11:09, B 11:09–11:23, B2 11:23–11:38), the same line on all three:
  `export-site: 17 datasets, 143804 citations, 224 pdfs, 30 workbooks, 8021 unresolved, 4093 zero-amount`,
  so N = 143,804; each also prints `budget PDF receipts: 64679/65459 complete, 21 government documents`.
- **Control** (B vs B2, `--control --write-noise`): `proof diff: EQUAL`; identical 35,801 · equivalent 360 ·
  reordered 168 (control class) · changed 0 · only in A 0 · only in B 0 [diff-control.txt]. noise-B-B2.json:
  schema 2, verdict EQUAL, 9 classes, classes_sha256 80a4b35abd91198d64772cb7604ee544d1de1f7c4573ef9a30fe426ae6f16979.
- **Code** (A vs B, rules `docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json`, which equal
  §16): `proof diff: PASS`; rule 0 (`json/families/index.json`) matched 1 and rule 1 (`manifest.json`) matched 1;
  no UNEXPECTED and no UNMET line. Counts: identical 35,801 · equivalent 366 · reordered 160 (every reorder in the
  control's 9 classes) · changed 1 (`manifest.json` `/json_sidecars`) · only in A 0 · only in B 1 [diff-code.txt].
- **json_sidecars** A 36,034, B 36,035 (B − A = 1); `families/index.json` is the only json file only in B, and
  none is only in A. The index lists `['f-15']` with 8 members and 1 ruling id, equal to the projection
  [sidecars.txt].

### F-15 bytes and facts [f15-era-identity.txt, fact-stability.txt, link-coverage-A.txt, link-coverage-B.txt, gate-verify-era-map.log]

- **The pin.** `json/f15_funding_history.json` has sha256
  d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f (`tests/fixtures/f15/history.sha256`) on
  fam2-A and fam2-B (Task 9a Step 7; re-hashed read-only on A, B and B2 for this note). verify-era-map leg f on B
  reads pinned = actual [gate-verify-era-map.log].
- **V5.** `tests/test_f15_era_identity.py` on B's code: 4 passed [f15-era-identity.txt].
- **Fact stability.** citations A 143,804, B 143,804: new in B 0, missing 0, changed 0; budget_lines_decade
  56,294 rows on each side, 0 A rows not in B, schema equal; `fact-stability (no F-15 restamp expected): PASS`
  [fact-stability.txt]. Task 9a calls `fact_stability.py`'s two compare functions with an empty leaf map
  (`f15_leaves={}`, `expected_f15=0`), because the CLI's rule S4 expects the F-15's 72 A1 era leaves to re-stamp
  and so reports two identical trees as FAIL; the empty map demands zero missing and zero changed facts.
- **Link coverage**, against `data/research/link_coverage/baseline.json`: A and B print the same five lines, line
  for line, each ending `link-coverage: 0 violation(s)` and `link-coverage: PASS`: 61,678 budget figures on 2,563
  program pages (a 61,016 · b 662 · c 0 · d 0), source-linked 100.00%, PDF-highlighted 98.93%, 2,416 pages fully
  PDF-highlighted, compared against the baseline's 44,747 (a) figures [link-coverage-A.txt, link-coverage-B.txt].
  That is spec §14 item 6's "unchanged". The printed shares are not the baseline file's own (`pdf_highlighted`
  0.991052, from the 2026-10-02 export of 45,151 figures), and need not be, because `compare_to_baseline`
  (`src/govbudget/link_coverage.py:281-309`) checks only that no baseline (a) figure is lost and the absolute
  checks (no (c) or (d) figure, receipts matching citations), never a percentage.

### Page and weight [site-build-B.log, site-build-A.log, site-B/, site-A/, weights.txt, site-verify-B.log, gate21-notes-B.txt]

- **Page snapshot.** `node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check …` printed
  `f15-page-snapshot: PASS — equal to ../tests/fixtures/f15/page_snapshot.json` on B's build and the same PASS
  against the A worktree's fixture on A's build (both builds `build exit=0`).
- **Weights** (level-9 gzip) [weights.txt]:

  | Page | A@fam2 build | B@fam2 build | Task 1 `base-weight:` (A, live export) | Ceiling |
  |---|---|---|---|---|
  | /families/f-15/ | 705,056 / 69,335 | 705,056 / 69,334 | 705,056 / 69,328 | 725,000 / 70,000 |
  | /methodology/ | 161,453 / 45,356 | 161,453 / 45,357 | 161,453 / 45,356 | 162,000 / 45,400 |

  The raw counts are equal on A and B, and equal `base-weight:`, because fam2's rendered date ("October 25, 2026")
  has the length of the one `base-weight:` records ("October 24, 2026"). The gzip counts differ by 1 byte between
  A and B, the build-ID and export-stamp noise the plan measured. /methodology/ keeps 43 gzip bytes under its
  ceiling on B (R-PF-14: A's base build is the reference). No weight entry was re-stamped and no ceiling raised.
- **The two exports' stamps:** `fam2-A built_at 2026-10-25T15:00:57.181724+00:00, renders October 25, 2026` and
  `fam2-B built_at 2026-10-25T15:15:39.206059+00:00, renders October 25, 2026` [weights.txt].
- **Masked comparison** (each tree's own build ID — A `f-k2DorHuuEp0ZovefjII`, B `O4nlIOy_4PNeoolp7pCiM` — every
  `+00:00` timestamp, the date rendered after one, and /methodology/'s "As of <date>"): `F-15 page identical apart
  from the build id and the export stamps` and `/methodology/ identical apart from the build id and the export
  stamps` [weights.txt]. Unmasked, the two F-15 files first differ at byte 354,105 (`cmp` on site-A/f15.html and
  site-B/f15.html).
- **Gate 21 (`program-skeleton`) leg (r) is green** on B's build, K1's first green: `leg r: 1 family index entry
  with history and built page ✓`, beside leg p (`family history sums, 12 annual snapshots, receipts and historical
  coverage checked ✓`) and the link fix's leg (q) (`line rulings: 51 withdrawn pair(s) checked on 2563 program
  page(s), 310 flows file(s), citations.json and 88 cite shard file(s); N0001922F0001 checked off flows/ATA000.json
  and /district/IN-07/`), with no `program-skeleton(r):` error. The full run prints `gate 21 program-skeleton: PASS`
  [site-verify-B.log] but elides the gate's notes past the first unless `VERIFY_NOTES=all`; the three notes come
  from re-running the gate alone on the same build and data links (PASS, 0 errors, 18 notes) [gate21-notes-B.txt].

### Gates [gate-*.log, verify-phase5.log, verify-phase5-runtime.txt, evals.log, site-verify-B.log, vitest-B.log, pytest.txt, w1.txt]

On B@fam2 (`source .proofs/fam2/env.sh .proofs/fam2-B`; the site build over the `data/*` links pointed at
fam2-B), except `verify-phase5`, which ran on fam2-B-eval (R-PF-20):

- **verify-era-map** exit 0, legs a–h PASS: 7 workbooks, 6,927 keys checked; 6,927 keys, 0 undecided, 1,253
  decisions; f15 31 map rows; fact ids 56,294 rows, 17,523 era P-1 rows, 0 mismatched; published map
  6,927 = 6,927; f15 history pin pinned = actual; era minters 17,523; era book diffs 1,044, procurement 0 →
  `verify-era-map: PASS` [gate-verify-era-map.log].
- **verify-families** exit 0: `leg a registry: families=2 published=1 member_rows=27 era_lines=94 rulings=2 → PASS`;
  `leg b lake: families=2 failures=0 undecided=1 stale=0 → PASS` (the one undecided is the F-35's deferred row
  `f-35|R-1:3600F:AF:0207268F|2017-2026`, recorded and never exported [check-f35-ratified.txt]); `leg c export:
  published=1 histories=1 stage3=0 leaks=0 files_scanned=36036 → PASS` (index.json equal to the projection, the
  F-15 artifact's 8 counted ids, no D9 needle) → `verify-families: PASS` [gate-verify-families.log].
- **verify-phase5b1** exit 0: gate 1 citations 50/50, gate 2 integrity PASS, gate 4 narrative provenance 25/25,
  gate 5 PASS, gate 3 non-gating → `verify-phase5b1: PASS` [gate-verify-phase5b1.log].
- **verify-phase5e** exit 0, gates a–e PASS → `verify-phase5e: PASS` [gate-verify-phase5e.log].
- **verify-lineage** exit 0, legs a–j PASS → `verify-lineage: PASS` [gate-verify-lineage.log].
- **evals check** exit 0: `evals check: 43 ok, 0 stale, 5 skipped`, `evals check: PASS`; no expected answer moved,
  so none was refreshed [evals.log].
- **`npm run verify`** exit 0 on Step 2's build (12:02): all 27 gates PASS, `overall: PASS` [site-verify-B.log].
- **vitest** exit 0: 210 files / 2,928 tests passed, and the client-graph config 1 file / 3 tests; among them the
  platform-family mirror (`src/__tests__/platform-family-mirror.test.ts`, 4), gate 21 leg (r)'s
  `family-index.test.mjs` (8), and the link fix's `about-link-line-rulings` (4),
  `methodology-precision-population` (1) and `program-skeleton-line-rulings` (14) [vitest-B.log].
- **verify-phase5** on fam2-B-eval, run 3 (from 13:43, runtime 1596 s): `gate freshness: 43 answers current →
  PASS`; `gate eval: accuracy 47/48, citation 43/43 → PASS` (data/research/eval-runs/eval-20261025T175123Z.json,
  untracked); `gate assembly: PASS`, with verify-phase1, verify-phase2, verify-phase3, verify-phase4,
  verify-phase5a, verify-phase5b1, verify-phase5b3, verify-lineage, verify-era-map and verify-families each
  `PASS`; `verify-phase5: PASS` [verify-phase5.log, verify-phase5-runtime.txt]. Task 10a's timing guard reads the
  1596 s. Runs 1 and 2 are in `### Re-runs`.
- **pytest** on 55432: `4914 passed in 314.51s`, 0 failed, run 12:23–12:28 (outside :15–:22) [pytest.txt].
- **W1** (`uvx --offline ruff check --isolated --select F,E9`): cli 5, export_site 10, verify_phase5 2 (Task 1's
  `W1:` line); program_pdf_receipts, f15_funding_history, verify_era_map and the four new modules
  (platform_families, platform_family_history, platform_family_review, verify_families) `All checks passed!`
  [w1.txt].

### The F-35 (B1)

Batch R-DEC-FAM-F35-B1 was ratified on 2026-10-25 (owner: "yes"). The B1 page showed, from the preview on fam2:
FY2015 8,276.5 … FY2024 13,469.6, FY2015–24 cumulative 116,808.4, FY2025 enacted 12,532.3, FY2026 request 11,467.0
($M), equal to F35 Appendix B1, differences none. Manifest sha256
e434eacf3eda829fa367dc9e2beb1349add37a1923bbf408ca0a6160cb6377df. Amendments: none. The F-35 is `ratified` and
appears nowhere in the export.

The reply is the committed `data/research/platform_families/f-35/batches/B1.json` (`owner_reply` "yes",
`decided_on` 2026-10-25, `rows` empty) and the ruling's `owner_reply` in `data-seeds/platform_families.json`
(R-PF-8); the ledger's `B1:` line records the date, the manifest sha256 and "amendments: none". The ruling records
18 approved rows and 1 deferred, as the page proposed. The figures are the manifest's `preview` (`differences: []`),
rounded half up to $0.1M. The export check is verify-families leg c (`leaks=0`) on B@fam2.

### Re-runs

**Correction (2026-10-25): Task 9b Step 3 (`verify-phase5`) ran three times; run 3 is the result above.** Steps 1,
5 and 6 ran once. Step 2's build ran a second time under R-PF-20a, and Step 4's restore a second time after run 3.
One of Step 3's assembly legs also ran on its own: a standalone `verify-phase5b3` on the same tree after run 2,
13:32:45–13:41:16 (run 2's bullet below), as gate 21 ran on its own over Step 2's build (`### Page and weight`).
Each paid eval left one untracked `data/research/eval-runs/` file in this worktree; none is committed.

- **Run 1 (12:29:03–13:00:14, runtime 1871 s), on fam2-B as the brief wrote it: `verify-phase5: FAIL`.** `gate
  eval: accuracy 18/48, citation 9/14 → FAIL` (eval-20261025T164141Z.json); most questions answered `REFUSE`, and
  q040's recompute read `Permission Error`. Freshness (43 answers current) and the assembly (all 10 legs) passed
  [verify-phase5-clone-sandbox.log, verify-phase5-clone-sandbox-runtime.txt].
  - **The cause was the clone, not B.** The analyst's sandbox (`analyst/sql_tool.py`,
    `_make_sandboxed_connection`) admits only `<duckdb>/../parquet`, and then disables every other file access. A
    `cp -c -R` clone's DuckDB views keep reading the snapshot's parquet (`proof.py`: "The clone's DuckDB views keep
    reading $SNAP/parquet"). So on fam2-B every view over parquet raised a Permission Error, and the agent refused.
  - **The probe** calls the analyst's own factory, read-only [eval-sandbox-probe.txt]:
    `fam2-B PermissionException Permission Error: Cannot access file
    "…/.proofs/fam2/parquet/contracts/*/*.parquet" - file system operations are disabled by configuration`, and
    `fam2 fct_award_transactions rows 41686265`.
  - Piece 2 changed neither the analyst nor the evals: `git diff --stat 00b599a6 e48ab21b --
    GovBudget/src/govbudget/analyst GovBudget/evals` is empty.
- **R-PF-20 (controller): an eval clone, fam2-B-eval.** It is `cp -c -p -R fam2-B`. Its views were repointed from
  fam2/parquet to fam2-B-eval/parquet with the snapshot's own `proof._rewrite_duckdb_views` (`proof.py` is unchanged
  from A to B): 18 of 37 views rewritten [eval-clone-repoint.txt].
  - **No data byte changed.** Its parquet listing equals fam2's, 112 files, by name and byte count (re-listed
    read-only for this note). Only its DuckDB file's view text changed: that file now hashes b9f1f2ea…, while fam2,
    fam2-A and fam2-B still hash c9e75aa9….
  - **The sandbox now reads the warehouse.** On fam2-B-eval it reads 41,686,265 rows of `fct_award_transactions`,
    as fam2 does. Untouched fam2-B is still refused [eval-sandbox-probe-after-repoint.txt].
  - The `data/*` links and the environment pointed at fam2-B-eval; `site/out` stayed Step 2's B@fam2 build.
- **Run 2 (13:06–13:32, runtime 1566 s), on fam2-B-eval: `verify-phase5: FAIL`.** `gate eval: accuracy 47/48,
  citation 43/43 → PASS` (eval-20261025T171335Z.json) and freshness PASS. The assembly failed on verify-phase5b3
  alone. Run 2's log, created 13:06:06 and last written 13:32:12, prints only that leg's verdict,
  `verify-phase5b3: FAIL` [verify-phase5-eval-clone-run2.log, verify-phase5-eval-clone-run2-runtime.txt].
  - **The leg's detail comes from a standalone `verify-phase5b3` run** on the same tree after run 2's log ended:
    13:32:45–13:41:16, the log's creation and last write. Its log names this worktree as repo root, reads
    `build-meta git_head: e48ab21b`, and finds `out/`'s marker at Step 2's build [gate-verify-phase5b3-eval-clone.log].
    Its dossier gate passed. Its site run failed gate 1 only (the other 26 gates PASS), with `out/ is stale: a
    source file is 3567.8s newer than out/.build-meta.json (source_max=2026-10-25T17:01:53.721Z,
    marker=2026-10-25T16:02:25.951Z)`, and it ends `verify-phase5b3: FAIL`.
  - That newer file is `site/public/llms.txt`, newer than Step 2's 12:02:25 build. Step 4 had already run (the
    first implementer, 13:01:53, after run 1), and the controller re-ran Step 3 without first re-running Step 2's
    build, so the order was wrong, not B.
- **R-PF-20a (controller): a re-run starts from Step 3's tree state.** Step 2's build was re-run on fam2-B-eval,
  whose site is a `cp -c -p -R` of fam2-B/site, at 13:42–13:43: build exit 0 [site-build-B-eval.log],
  `f15-page-snapshot: PASS`, and the f-15 page equal to Step 2's with the build ID masked. All three come from the
  ledger; the last two were re-checked read-only for this note, on `site/out`, together with /methodology/, which is
  also equal to Step 2's.
- **Run 3 (from 13:43, runtime 1596 s), on fam2-B-eval: `verify-phase5: PASS`** (the Gates line above). Step 4's
  restore was then re-done: the links point at the main checkout's data, `llms.txt` is restored, and no tracked
  file changed.

Under R-PF-20 and R-PF-20a, run 3 satisfies Step 3. Runs 1 and 2 are kept as recorded here, not hidden.
