# Families piece-1 follow-ups — release-1 proof (Task 21)

Spec: docs/superpowers/specs/2026-10-04-families-piece1-followups-design.md §7, §8.
Code: A = `7dccd98320fea0735299f6639a1a758b28f688ca` (`git merge-base main HEAD`; its src/, dbt/, data-seeds/,
scripts/ and site/ equal the deployed `916ae88eee04f1e2445040933f83a3e279c04209`, production's `/.build-meta.json`
`git_head` when Task 21d Step 3 ran), B = `abb1c7102af63466b948120ba01bcc686881c25d` [shas.txt, lines 1–3].
Snapshots: `.proofs/fu-pre` (scratch database govbudget_proof_fu_pre) and `.proofs/fu-post`
(govbudget_proof_fu_post), taken back to back 2026-10-14T12:23:57.212362+00:00 and
2026-10-14T12:24:39.459562+00:00 [snapshot-shas.json].

B was `2569f5bdbe9ea3148d8d8fd09486260b2d8a9846` when Task 21d first ran [superseded-21f-run1/shas.txt]. Task 21f2
moved it to `abb1c710`: `21bebdfb` changed one line of `src/govbudget/export_site.py` and `abb1c710` only plan
files, and 21f2 re-recorded B and re-ran the exports from it (see "Two stops and their fixes"). The site build
that `npm run verify` and the page weights measured is `abff1e97`'s site code over B@fu-post's export
(`build-meta git_head: abff1e97` [site-verify.log, gate 1]). From B to `b31244ac` only site/ and tests/ moved
(`fe0bee9e`, `abff1e97`, `b31244ac`), so HEAD's export code is B's.

Every bracketed log is under `.proofs/fu-logs/`; Task 22e Step 12 copies them to the ledger's `proof-logs/`.
Times are EDT unless they carry `+00:00`.

A@fu-pre = the deployed code's export of the pre-write lake. B@fu-pre = the follow-ups code's export
of the same lake. B@fu-post = the follow-ups code's export of fu-post after the rehearsed writes.
B2@fu-post = a second export of B@fu-post's state: the control.

## Summary (2026-10-14)

**Result.** The two snapshots carry equal pins. On fu-post the Chem Demil write committed once (its
revert file kept). On fu-pre, after its first pair of exports, the same write equalled fu-post's, ids included;
its `--revert` returned every Postgres pin to fu-pre's pre-write pins, and a second `--revert` found
nothing to revert. The abort path's lake rebuild by the deployed code, rehearsed on a clone of
fu-post, equals fu-pre's lake. The single selective dbt build passed (W2). The control reads EQUAL; P2 (code),
P2b (/years/) and P1 (lake) pass their rule lists and their fact-level checks; the F-15 history moves
only in F015E0's note; every Python gate, link coverage and `npm run verify` pass on B@fu-post.

The proof stopped twice on the way, and each stop was fixed at its cause, then re-run: P1 first failed on two
tied awards that swapped places in one flows file (Task 21f, fixed by Task 21f2), and `npm run verify` first
failed gate 23 leg f2 on /program/0390DOM/ (Task 21h, fixed by Task 21h2). No rule was widened beyond one
optional code rule, and no noise class was added.

### Snapshots [snapshot-shas.json, pins-fu-pre-fu-post.txt, snapshot-fu-*.log, snapshot-times.txt]

| | fu-pre | fu-post |
|---|---|---|
| created | 2026-10-14T12:23:57.212362+00:00 | 2026-10-14T12:24:39.459562+00:00 |
| DuckDB sha256 at copy | c3f7286a84074aef7633082d07fc8e148907db93e38959a7096d9271f9d1e2fa | c3f7286a84074aef7633082d07fc8e148907db93e38959a7096d9271f9d1e2fa |
| site / raw_docs digest | af669905e16d112d1acc10d2882aaa1715c606380e59048c1527e98e8cdce2fc / 320c7d9106b8422277fd965bdb26b2fcc94a67f71dab49d0a9798704fc7f3f27 | same |
| manifest.jsonl sha256 | bc4e8b141e15088e41915b0eb8392addf2da1e704f476581dbf04e0da8db0e35 | same |
| files [snapshot-fu-*.log] | parquet 112 · site 36,545 · raw_docs 1,112; 18 of 37 DuckDB views repointed | same |
| Postgres | 18 tables; budget_lines 159,903 rows, md5 2d31b701446430d82b4ee0b4ca9ad2f0 | same |
| dump sha256 (not a pin) | d589780d9cf3fe45c81ff8c1de6376baf7212030cf206e4072526c8cac8fc5f6 | 611c52a1e159f95c5f6f969d2d6af7f58d301d9ddc2b32cdb87023bdf01c1205 |
| duration [snapshot-times.txt] | 00:42 (fu-post start 08:23:57 − fu-pre start 08:23:15) | 00:42 (fu-post end 08:24:39 − fu-post start 08:23:57) |

`snapshot_pins.py compare`: EQUAL. The live lake before the write [prewrite-live.txt]: 159,903
budget_lines rows, 16 route-unsafe (PB2024 O&M 5 / RDT&E 5, PB2025 O&M 3 / RDT&E 3), no 0390DOM, a
17-column map, no p1_route_safe_codes; `era-map check --strict` 0 undecided, 0 stale [prewrite-era-check.log].

### W1 [w1-pytest.log, w1-vitest.log, w1-ruff.txt, w1-pytest-after-repin.log, site-vitest.log]

Task 21d Step 6 ran W1 before the snapshots, on B = `2569f5bd`: pytest 4,429 passed, 3 failed; vitest 205 files /
2,881 tests, 1 failed [superseded-21f-run1/w1-pytest.log, superseded-21f-run1/w1-vitest.log]. Because src/ moved,
Task 21f2 re-ran it on B = `abb1c710` (22a's "Only src/ moved" path), after the snapshots, inside the declared
F-15 window: pytest 4,431 passed, 0 skipped, 3 failed; vitest 205 files / 2,881 tests, 1 failed. The 3 + 1 are
exactly the window's four (the three `tests/test_f15_era_identity.py` goldens and the vitest
"committed baseline … is present, well-formed and of this schema"), and nothing else failed
[w1-pytest.log, w1-vitest.log]. The 2 more passing tests are `21bebdfb`'s flows-order tests.

Green after the re-pins: the full pytest suite 4,434 passed, 0 skipped, 0 failed after Task 21g's F-15 re-pin
(`fe0bee9e`) [w1-pytest-after-repin.log]; vitest 205 files / 2,891 tests, 0 failed (and the client-graph config
1 file / 3 tests) after Task 21h2's page-snapshot re-pin (`b31244ac`) [site-vitest.log]. The 10 tests beyond W1's
2,881 are `abff1e97`'s label and gate-leg tests. pyflakes (`uvx --offline ruff check --isolated --select F,E9`)
on the 23 touched modules: no finding beyond A's (cli.py 5/5, export_site.py 10/10, verify_phase5.py 2/2,
budget_pdf_receipts.py 1/1, the other 19 modules 0/0) [w1-ruff.txt].

### Rehearsed writes on fu-post and fu-pre [pg-pins-*.json, s194-post-*.log, s194-pre-*.log, rehearsal-0390d-apply.txt, parity-pg-pre-post.txt, parity-abort-fu-pre.txt, abort-rehearsal-*.log]

| Step | Result |
|---|---|
| pins, fu-pre vs fu-post scratch | only jbook_documents differs (each points at its own raw_docs): rows 254 / 254, md5 f9f014eb5b90d96f1fb089fcae76598c / 5170fc17e20d23dd8fa28ee939c40c95 [pg-pins-pre-scratch.json, pg-pins-post-0.json] |
| fu-post `--check` / `--dry-run` | CLEAN, the only differences #194's (re-key 8, insert 4, delete 8) / ROLLED BACK; pins unchanged [s194-post-check.log, s194-post-dryrun.log, pg-pins-post-dryrun.json] |
| fu-post `--apply --revert-file s194-fu-post-revert.json` (its only write) | COMMITTED; re-keyed 8, deleted 8, inserted 4, untouched rows 159,887 (digest equal); only budget_lines moved: 159,903 → 159,899 rows [pg-pins-post-1.json]; 0390DOM PB2024 5 (325,095), PB2025 3 (194,641), PB2026 4 (114,635); O&M ids 47733–47735, 349016–349020 kept; new PB2026 ids 581323–581326; 0 route-unsafe [s194-post-apply.log, rehearsal-0390d-apply.txt] |
| fu-pre `--dry-run`, then `--apply --revert-file s194-fu-pre-revert.json` (after its first pair of exports) | COMMITTED, the same counts; account 0390D's 350 rows equal fu-post's, ids included (`ids equal — equal`, `lake-parity: EQUAL`) [s194-pre-dryrun.log, s194-pre-apply.log, parity-pg-pre-post.txt]; the two revert files' `before` (16 rows), `rekeyed`, `deleted_ids` and `inserted` equal, as are `untouched_digest`, `columns`, `editions` and `schema`; only `database`, `written_at` and `rows_sha256` differ [s194-fu-post-revert.json, s194-fu-pre-revert.json] |
| fu-pre `--revert --revert-file s194-fu-pre-revert.json` | restored 16 pre-write rows (re-keyed 8 back, re-inserted 8, removed 4); every table's pin equal to fu-pre's before any write, ids included (Q24 (b)) [s194-pre-revert.log, pg-pins-pre-reverted.json = pg-pins-pre-scratch.json]; `--check` afterwards CLEAN with #194's differences only [s194-pre-check-after-revert.log] |
| fu-pre second `--revert` | the database already holds the pre-write rows; nothing to revert [s194-pre-revert-2.log] |
| abort-path lake rehearsal: the A worktree's `jbooks export-facts` and `dbt build --select p1_era_code_decisions stg_budget_lines+` on `.proofs/fu-abort`, a clone of fu-post, against fu-pre's reverted database, `p1_route_safe_codes` dropped | export-facts on `GOVBUDGET_DATA=…/.proofs/fu-abort` and `dbname=govbudget_proof_fu_pre` [abort-rehearsal-export-facts.log]; A's project (196 data tests, 4 seeds) `Done. PASS=156 WARN=0 ERROR=0` [abort-rehearsal-dbt.log]; `lake-parity: EQUAL` against fu-pre on nine checks: eight relations (stg_budget_lines and fct_budget_lines 159,903; fct_decade_series 59,179; fct_book_diff 18,412; p1_era_code_decisions 1,253; p1_era_line_map 6,927; fct_program_decade_series 57,886; fct_budget_trajectory 1,988) and `jbooks/budget_lines.parquet` 159,903 [parity-abort-fu-pre.txt]; fu-post's jbooks parquet unchanged by the clone's export-facts [fu-post-jbooks-sha-after-21f-step6.txt = fu-post-jbooks-parquet-sha-after-export.txt]. The drop's own line (route-safe relation left 0) is in Task 21f's report, not in a log file |
| `jbooks export-facts` (fu-post) | budget_lines.parquet 159,899 rows: 0390DOM O&M 2024 5, 2025 3, 2026 4 [export-facts-fu-post.log, export-facts-fu-post-check.txt] |
| `dbt build --select p1_route_safe_codes p1_era_code_decisions stg_budget_lines+` | 199 data tests, 5 seeds; `Done. PASS=160 WARN=0 ERROR=0`; map built before the program table, conservation after both [dbt-build-fu-post.log, dbt-order-fu-post.txt] |
| rebuilt warehouse | map 18 columns, decided_on 14th; 0390D map rows: B7 same_program 0390DOM 7 (R-DEC-ERA-B7, 2026-10-04), RDT&E exclude_route_unsafe 7, history_only PROC 7 and exclude_placeholder 2 (both 2026-10-02); 0390DOM decade series 30 rows, 21 of them era_line_map grains totalling 2,333,721 thousand; 0 views read the live lake [postbuild-fu-post.txt, postbuild-fu-post-decade-0390DOM.txt]; era-map check 0/0 [era-check-fu-post.log] |

The fu-pre write and revert ran after Task 21f's first pair of fu-pre exports (fu-pre-B ended 09:14:56
[superseded-21f-run1/export-times.txt]; the fu-pre revert file was written 2026-10-14T13:15:17+00:00
[s194-fu-pre-revert.json]). Task 21f2's re-exports of A@fu-pre and B@fu-pre (10:11:23–10:34:16 [export-times.txt])
read the reverted database, whose every pin equals the pre-write pin [pg-pins-pre-reverted.json]; the fu-pre
lake itself is never written, because each export runs in its own clone.

### Exports [export-*.log, export-times.txt, dbt-tests.txt]

A@fu-pre 143,856 citations; B@fu-pre 143,856; B@fu-post and B2@fu-post 143,893. Export times
11:33 / 11:20 / 12:44 / 13:20 (mm:ss; each export's last start/end pair in export-times.txt, Task 21f2's
re-run). dbt test nodes: A 196, B 199 [dbt-tests.txt].

### Control [control-diff.txt, noise-fu.json]

B@fu-post vs B2@fu-post: identical 35,771 · equivalent 376 · reordered 164 · changed 0 · only in A 0 ·
only in B 0; float noise 234 files / 3,596 values; derived hash 2 files / 9 values; `proof diff: EQUAL`.
noise-fu.json (schema 2, verdict EQUAL, written fresh after `rm -f`): 9 classes, classes_sha256
121b8c3c51421d077500e144831e86164df7b380dbede0c804ee5b934fbc08c2, file sha256 (of noise-fu.json itself)
ddf3a3f074b56fb9e384165716079a2a2a604de2b5a23d0d9292f23f82b0aa07. The classes: `citations/citations.parquet`
`/inputs` and `/query_body`; `json/breakdowns/*.json /rows`; `json/citations.json` and `json/cite-shards/*.json`
`/{fid}/inputs` and `/{fid}/query_body`; `json/districts/*.json /by_year_programs` and `/programs`. Unlike piece 1's
noise file, `json/flows/*.json /awards` is not a class: the flows order is now total, so P1 and Task 22c
judge flows files strictly.

### P2 — code (A@fu-pre vs B@fu-pre) [p2-diff.txt, p2-diff-report.json, p2-fact-delta.json, p2-flows-check.txt, p2-datasets-entry.txt]

`proof diff --expect expected-diff-code.json`: PASS, every one of the 25 rules matched (the 256 v1 receipt shards
only in A; the /years/ core changed and its two shards only in B; the two search aliases; the F015E0
note; the map scope; the dbt count 196 → 199; json_sidecars 36,286 → 36,032; rule 24, `json/flows/*.json`
`/awards` reordered, 1 file). Counts: identical 35,767 · equivalent 371 · reordered 159 · changed 7 · only in A 256 ·
only in B 2. The replaced `/datasets/[]` entry is `p1_era_line_map.parquet`, and its only differing key is
`scope` (the Q3 amendment); nine other entries differ only in `bytes` [p2-datasets-entry.txt]. The flows file
is `0605502E.json`: the same twelve awards, the $1,500,000.00 pair at places 9 and 10 swapped
[p2-flows-check.txt]. fact_delta: no fact added, removed or changed (`citations.json` identical up to noise,
119 noise-equivalent fields); budget_lines (8,549), budget_lines_decade (56,264) and fct_budget_trajectory (1,988)
equal.

### P2b — /years/ (A@fu-pre vs B@fu-pre) [p2b-report.json, p2b.txt]

| File | Bytes | Gzip |
|---|---|---|
| json/years_matrix.json (core, schema 2) | 1,100,823 | 344,303 (cap 780,074) |
| json/years_matrix/decade.json | 1,390,739 | 433,932 |
| json/years_matrix/detail.json | 1,231,643 | 284,230 |

build_id 42b97884f48985f6616db45c2b71af169cf4e16058b14c1817d479ce49f9d74c on all three; 1,938 rows; leg j 0
mismatches; every A cell unchanged. Added decade cells: 14,985 era (4,995 in the default view; 147 on the seven
org-split rows) and 63 modern (all on the org-split rows; 35 in the default view). Org-split rows' non-decade
cells added: none (`{}`). Decision 11 expected the seven rows also to gain `fy_2025_total`, `fy2526_change` and
`fy2526_pct_change`; they gain none, because the trajectory mart has no `fy2025_total` for 0300D, so both deltas
are NULL too (Task 21f's finding; re-read for this note from fu-pre-B's `data/fct_budget_trajectory.parquet`:
0300D 63 rows, 0 with `fy2025_total`). The decade half of #207 does land. Totals chart (Q15): panel 524 → 1,063
of 1,938 programs; FY2024A→FY2026R +9.34% → −2.61%; first→last +108.17% → +103.71%. The design's 1,056 omitted
the seven org-split rows (decision 10).

### P1 — lake (B@fu-pre vs B@fu-post) [p1-diff.txt, p1-fact-delta.json, p1-fact-delta.txt, p1-content.txt, p1-trajectory-0390DOM.txt, p1-flows-check.txt]

`proof diff --expect expected-diff-lake.json`: PASS, with no UNEXPECTED and no UNMET line. Counts: identical
35,689 · equivalent 355 · reordered 136 · changed 126 · only in A 0 · only in B 5. No `json/flows` group at all:
312 flows files on each side with no header, award-set or order difference [p1-flows-check.txt].

fact_delta: 37 new facts (31 workbook, 6 derived), every one traced to pe_bli 0390DOM; the eleven named
aggregates moved by exactly +3,243 and each gained input `86eb97e8aabd38f4`, the 0390DOM PB2026 FY2026 total;
nothing else moved. The eleven, with their roles from `expected-fact-moves-lake.json`:

| fid | Aggregate | A → B (thousands) |
|---|---|---|
| 709cbd08c6b7dfb0 | /programs/ universe | 385,268,393 → 385,271,636 |
| c216c55e0ddffec1 | flow chart TOTAL | 385,268,393 → 385,271,636 |
| d2f5b699e5123b11 | flow chart Army | 43,338,494 → 43,341,737 |
| da3a508dbe8427f4 | edge Army → Other appropriation | 28,418,219 → 28,421,462 |
| ce38e79987ed7a92 | Other appropriation (holds A\|0390D) | 100,800,917 → 100,804,160 |
| ac97b301729e8743 | edge Other appropriation → Other budget activity | 92,318,533 → 92,321,776 |
| 980c6bbee984f264 | Other budget activity | 215,533,900 → 215,537,143 |
| 9a77d80916d1cead | edge Other budget activity → Other program | 204,111,830 → 204,115,073 |
| ce27343e3d87e507 | Other program | 263,982,731 → 263,985,974 |
| 25e51edb9bfa36b3 | edge Other program → the bridge | 137,809,962 → 137,813,205 |
| 6ca3c62f32d31298 | bridge `not_yet_crosswalked` | 227,538,773 → 227,542,016 |

Rows: budget_lines +4 (8,549 → 8,553, all 0390DOM), budget_lines_decade +9 0390DOM and +21 0390D-ARMY-L1
(56,264 → 56,294), fct_budget_trajectory +1 (1,988 → 1,989, 0390DOM); breakdowns changed 11, new 4.

**The 0390DOM row in fct_budget_trajectory.** The mart gains one row: pe_bli 0390DOM, organization A, account
0390D (Chemical Agents and Munitions Destruction, Defense), fy2024_actuals 87404, fy2026_total 3243
[p1-trajectory-0390DOM.txt]. Its other three columns, fy2025_total, fy2526_change and fy2526_pct_change, are NULL
(the log prints only the row's non-null columns; re-read for this note from fu-post-B's
`data/fct_budget_trajectory.parquet`). The row ships in the Explorer's `data/fct_budget_trajectory.parquet`;
lake rule 2 allows it (the mart already carries the rollup-tier lines 0708081D and 0708083D). 0390DOM is still
in neither search_quick nor the /years/ core [p1-content.txt].

The 0390DOM sidecar: printed_code O&M, exhibit_family om, 30 decade points, 21 of them era points (before
PB2024), editions 2017–2026. Its budget_lines: fy_2024_actuals 87,404 · fy_2025_enacted 20,745 ·
fy_2026_disc_request 3,243 · fy_2026_total 3,243. programs_excluded lists 0390DOM (no_detail, 3,243 thousand,
"Chem Demilitarization - O&M"). Era summary: same_program 727,939,107K (919 chains, 5,860 lines),
exclude_route_unsafe 5,030,464K (1 chain, 7 lines), R-DEC-ERA-B7 801,553K (1 chain, 7 lines). Flow A|0390D
213,282; bridge not yet crosswalked 227,542,016; coverage 77.9% and $385.3B unchanged; program pages 2,563;
the published map 18 columns, decided_on at 14 [p1-content.txt].

### P3 — F-15 [p3-hermetic.txt, p3-capture.json, f15-snapshot-diff.txt]

Hermetic history sha256 d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f: the only leaf that
moved is programs[F015E0].note (`('programs', 7, 'note')`), which now opens "This exhibit [the PB2026 F-15EX AP
(F015EX) P-40] does not include". B@fu-post ships exactly that sha (verify-era-map leg f, pinned = actual
[gate-verify-era-map.log]), and B@fu-pre ships the same file (P1 shows no `json/f15_funding_history.json`
difference [p1-diff.txt]). Captured and pinned from B@fu-post (source_rows 467, series 195, previews 207,
registry 177, current fact ids 20, 139,061 bytes) [p3-capture.json], committed as `fe0bee9e`. Page snapshot: no
pre-wave value moved; F015E0 label unchanged ("BLI F015E0 · F-15e (FY2020 F-15EX Lot 1 aircraft) · Procurement ·
Historical code · Note below"); schema 1 → 2; new captures `['prose']`; gloss captured [f15-snapshot-diff.txt];
re-pinned in `b31244ac`, and its vitest (7 tests) passes [site-vitest.log].

### Gates on B@fu-post [gate-*.log, link-coverage-fu-post-B.txt, site-verify.log, site-vitest.log, gate23-basis-direct.log, 0390dom-page.txt]

verify-era-map (legs a–h; leg d 56,294 rows, 17,523 era P-1 rows, 0 mismatched; leg h 1,044 era book diffs),
verify-phase5e (gates a–e), verify-lineage (legs a–j), verify-phase5b1 (gates 1, 2, 4; gate 3 non-gating with
`p1_era_line_map` deferred): PASS [gate-verify-era-map.log, gate-verify-phase5e.log, gate-verify-lineage.log,
gate-verify-phase5b1.log]. link-coverage: PASS against data/research/link_coverage/baseline.json (61,678 budget
figures on 2,563 program pages; 100.00% source-linked, 98.93% PDF-highlighted; 0 violations; 440 summary cards
cited by XML path only, counted apart, Q20) [link-coverage-fu-post-B.txt]. `npm run verify` overall PASS (27
gates; gate 23's legs f1–f4 green) [site-verify.log, gate23-basis-direct.log]; vitest PASS [site-vitest.log].
Sitemap 4,350 `<loc>` entries (live 4,349 + /program/0390DOM/, the only addition) [sitemap-b.txt,
sitemap-live.txt]. The 0390DOM page carries the FY2026 total fid `86eb97e8aabd38f4`, the address sentence, the
printed code O&amp;M and links to /program/0708081D/ and /program/0708083D/ [0390dom-page.txt].

### Page weights [weights.txt]

| Page | Stamp before | Measured | Ceiling |
|---|---|---|---|
| /methodology/ | 161,353 / 45,336 | 161,373 / 45,323 | 162,000 / 45,400 |
| /families/f-15/ | 703,427 / 68,538 | 703,623 / 68,615 | 725,000 / 70,000 |
| /data/ | 85,358 / 14,530 | 85,747 / 14,745 | 105,000 / 15,600 |
| /years/ | 37,362 / 7,668 | 37,364 / 7,671 | 45,000 / 9,000 |
| /programs/ | 2,968,731 / 310,063 | 2,973,786 / 310,710 | 3,150,000 / 330,000 |
| /agency/*/ (heaviest) | 1,755,341 / 120,583 | 1,765,372 / 121,549 (/agency/N/) | 2,060,000 / 137,000 |

Each ceiling is the measured value plus the "left" weights.txt prints, and equals `build.mjs`'s `maxRaw` /
`maxGzip`. /methodology/ fits with 627 raw / 77 gzip left, so Q13's clause swap stays. No ceiling raised:
weights.txt lists 18 entries, none over its ceiling, and no `maxRaw` or `maxGzip` in
`site/scripts/gates/build.mjs` changed since A; `b31244ac` re-stamped only the six `measured` values above.
/years/ scripts: 15 chunks, 893,556 / 272,011 gzip [years-chunks.txt] (pre-wave, the plan's figure: 15,
890,636 / 271,283).

## Two stops and their fixes

### Task 21f → 21f2: tied awards in a flows file [superseded-21f-run1/p1-diff.txt, p2-flows-check.txt, p1-flows-check.txt, p2-diff.txt]

- **Why 21f stopped.** Run 1's P1 (B@fu-pre vs B@fu-post) read `UNEXPECTED differences: 1`,
  `json/flows/0605502E.json changed reordered /awards ×1`, `proof diff: FAIL`
  [superseded-21f-run1/p1-diff.txt]. Both sides held the same twelve awards. Two of them tie at $1,500,000.00,
  W31P4Q19C0008 (IN-08) and W31P4Q17C0103 (CA-36) [p2-flows-check.txt], and the flows top-12 query ordered only
  by `dollars desc`, so the rebuilt fu-post lake handed DuckDB the tied rows in another order. The control
  cannot see such a flip, because it exports one state twice, and no noise class covers it. The same flip
  would have hit Task 22c's release-state diff after the live rebuild.
- **The fix** (`21bebdfb`): `order by dollars desc, piid, recipient_uei, pop_state, pop_district, family_key`,
  the query's group-by columns, so the order is total. `tests/test_export_site_flow_awards_order.py` failed
  before the fix (2 failed) and passes after it (2 passed). The tiebreak acts on exactly equal `dollars` only.
- **One optional P2 code rule, rule 24** (`abb1c710`): `json/flows/*.json` `/awards` reordered, "no award is
  added or removed". A (no tiebreaker) and B can order tied awards differently. In P2 it matched 1 file
  [p2-diff.txt], and only exactly tied awards reordered [p2-flows-check.txt]: 312 flows files on each side, no
  header difference, no award added or removed, one file whose order differs (0605502E, places 9 and 10, the
  $1,500,000.00 pair), and no adjacent awards in B within a cent of each other without being equal;
  `flows-check: SET-EQUAL`. Nothing was added to the lake or release rule files or to any noise file.
- **The re-run, by 22a's "Only `src/` moved" path.** `git diff 2569f5bd abb1c710` over src/, dbt/, data-seeds/,
  migrations/, scripts/ and site/ is one line of `src/govbudget/export_site.py`. Task 21d Step 3 re-recorded B
  [shas.txt] and Step 6 re-ran W1. The four export clones were re-made, and Task 21f Steps 2–3 and 7–14 ran
  again from the new B. Steps 4–6 were not repeated: the fu-pre write and revert and the abort rehearsal do not
  depend on the export code, and a second Step 4 would spend new id-sequence values. Run 1's logs are kept in
  `superseded-21f-run1/`, and its informational P1 results as `*.after-p1-fail.*`.
- **The re-run matched run 1 everywhere outside flows.** N_pre 143,856 and N_post 143,893 both times
  [superseded-21f-run1/export-*.log, export-*.log]. Both controls read EQUAL with the same nine classes
  (run 1: identical 35,782 · reordered 153; run 2: identical 35,771 · reordered 164)
  [superseded-21f-run1/control-diff.txt, control-diff.txt]. P2b's output is byte-identical
  [superseded-21f-run1/p2b.txt, p2b.txt]. P1 now passes, and its flows check finds no difference
  [p1-diff.txt, p1-flows-check.txt].

### Task 21h → 21h2: the 0390DOM TOA chips [site-verify.blocked-run.log, gate23-basis-direct.log, site-verify.log, weights.blocked-run.txt, weights.txt]

- **Why 21h stopped.** On the first B@fu-post build (site code `fe0bee9e`), `npm run verify` read overall FAIL:
  26 gates PASS and gate 23 (basis) FAIL on leg f2 alone. Five chips on `program/0390DOM/index.html` rendered
  "P-1/R-1 TOA · PB2026" with no `[data-reconciliation]` or `[data-basis-declared]` ancestor
  [site-verify.blocked-run.log]. The sidecar's exhibit_family is `om` [p1-content.txt], which the site's
  `normalizeExhibitFamily` did not know, so the chips fell back to the both-exhibits form, although every figure
  on the page cites the PB2026 P-1.
- **The fix** (`abff1e97`, site/ only): `om` maps to the P-1 family, so the chips read "P-1 TOA · PB2026". That is
  the narrower true basis (the smaller true claim), and the gate was not loosened. follow-the-dollar's
  appropriation label now compares the raw token, so it renders exactly as before, and the header badge still
  reads O&M. This supersedes contract note G2-6, which expected the generic chip.
- **Its gate guard, gate 23 leg f4.** On every page whose sidecar is `om`, each single-exhibit TOA chip must sit
  on a cited figure whose citation sheet is that exhibit's. The leg fails closed on a chip without a figure, a
  fact id the shipped cite shards lack, a leaf citation without a sheet, and an om page that resolves 0 chips. On
  the fixed build: leg f1 8,551 single-exhibit chips agree (272 on rows absent from programs.json skipped); f2 no
  unexplained "P-1/R-1" chip on any program page; f3 8,823 chips resolved; f4 5 single-exhibit chips on 1 om page
  each sit on a figure citing the sheet they name [gate23-basis-direct.log].
- **The re-run of Task 21h, in full, on the fixed code:** build git_head `abff1e97` [site-verify.log, gate 1];
  sitemap 4,350 with /program/0390DOM/ the only addition [sitemap-b.txt, sitemap-live.txt]; the F-15 page snapshot
  schema 1 → 2 with no old value lost [f15-snapshot-diff.txt]; `npm run verify` overall PASS on all 27 gates
  [site-verify.log]; vitest 2,891 / 2,891 [site-vitest.log]; the weights re-measured and re-stamped from this build
  [weights.txt]. The blocked run's logs are kept as `*.blocked-run.*`. Against them, raw bytes are equal on all
  18 entries, and gzip moved by 1–3 bytes on 15 of them (the HTML references new chunk hashes, as Task 21h2's
  report explains); /programs/, /methodology/ and /district/*/ are byte-identical [weights.blocked-run.txt,
  weights.txt].

## For Task 22d's go-ahead

Tell the owner, with these numbers:

1. A tie at the 12th place on a flows page now publishes a fixed award (lowest piid, then uei, state, district,
   family). A and B publish the same award set on all 312 flows pages; against production only 0605502E's order
   changes [p2-flows-check.txt].
2. /program/0390DOM/'s TOA chips read "P-1 TOA · PB2026", not the "P-1/R-1 TOA" that contract note G2-6 expected
   (Task 21h2).
3. `fct_budget_trajectory` gains one 0390DOM row (fy2024_actuals 87404, fy2026_total 3243), shipped in the
   Explorer's `data/fct_budget_trajectory.parquet` [p1-trajectory-0390DOM.txt].
4. The seven org-split rows gain decade cells only (147 era, 63 modern); `fy_2025_total`, `fy2526_change` and
   `fy2526_pct_change` stay empty [p2b-report.json].
5. Q15: told 524 → 1,056 programs and +9.3% → about −2.5% (decision 10); measured 524 → 1,063, +9.34% → −2.61%,
   first→last +108.17% → +103.71% [p2b-report.json].

## What the release still has to show (Task 22)

A fresh snapshot of the live lake carries fu-pre's pins; the live write, export-facts and dbt build
leave the live lake equal to fu-post (`lake_parity.py`); the release export equals B@fu-post except
for SAM registrations stored after fu-post; W3–W6 pass on the live state; the live checks after the
deploy.
