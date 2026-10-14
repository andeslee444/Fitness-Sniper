<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 21i: Release-1 proof note

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §7 (the proofs and what each fails on), §8 step 8 (the release stamp cites the proof), piece-1's proof-note form (`docs/superpowers/reviews/families-s1-proof.md`).

**Files:**
- Create: `docs/superpowers/reviews/fu-release1-proof.md`

**Interfaces:**
Consumes: the logs Tasks 21d–21h wrote under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs/` (named in brackets in the note) and their commits.
Produces: the proof note Task 22e's ledger row and findings entry cite. Keeps (until Task 22e's cleanup offer) `.proofs/{fu-pre,fu-post,fu-pre-A,fu-pre-B,fu-post-B,fu-post-B2,fu-logs}`, the scratch databases `govbudget_proof_fu_pre` and `govbudget_proof_fu_post`, and the A worktree: Task 22a compares a fresh snapshot with fu-pre's pins, Task 22b compares the live lake with fu-post, compares its live revert file's `before` rows with `s194-fu-post-revert.json` and `s194-fu-pre-revert.json`, and its abort path runs `--revert --revert-file` on the live file, rebuilds with the A worktree and compares the live lake with fu-pre, Task 22c diffs the release export against `fu-post-B/site` with `noise-fu.json`.

- [ ] **Step 1: Write the proof note**

Create `docs/superpowers/reviews/fu-release1-proof.md`, filling every `<…>` from the log named in brackets (all under `.proofs/fu-logs/`); copy numbers, never round them:

```markdown
# Families piece-1 follow-ups — release-1 proof (Task 21)

Spec: docs/superpowers/specs/2026-10-04-families-piece1-followups-design.md §7, §8.
Code: A = `<A sha>` (`git merge-base main HEAD`; its src/, dbt/, data-seeds/ and scripts/ equal the
deployed 916ae88e), B = `<B sha>` [shas.txt]. Snapshots: `.proofs/fu-pre` (scratch database
govbudget_proof_fu_pre) and `.proofs/fu-post` (govbudget_proof_fu_post), taken back to back
<created_at fu-pre> and <created_at fu-post> [snapshot-shas.json].

A@fu-pre = the deployed code's export of the pre-write lake. B@fu-pre = the follow-ups code's export
of the same lake. B@fu-post = the follow-ups code's export of fu-post after the rehearsed writes.
B2@fu-post = a second export of B@fu-post's state: the control.

## Summary (<YYYY-MM-DD>)

**Result.** The two snapshots carry equal pins. On fu-post the Chem Demil write committed once (its
revert file kept). On fu-pre, after its two exports, the same write equalled fu-post's, ids included;
its `--revert` returned every Postgres pin to fu-pre's pre-write pins, and a second `--revert` found
nothing to revert. The abort path's lake rebuild by the deployed code, rehearsed on a clone of
fu-post, equals fu-pre's lake. The single selective dbt build passed (W2). The control reads EQUAL; P2 (code),
P2b (/years/) and P1 (lake) pass their rule lists and their fact-level checks; the F-15 history moves
only in F015E0's note; every Python gate, link coverage and `npm run verify` pass on B@fu-post.

### Snapshots [snapshot-shas.json, pins-fu-pre-fu-post.txt, snapshot-fu-*.log]

| | fu-pre | fu-post |
|---|---|---|
| created | <created_at> | <created_at> |
| DuckDB sha256 at copy | <sha> | <same sha> |
| site / raw_docs digest | <sha> / <sha> | same |
| Postgres | 18 tables; budget_lines 159,903 rows, md5 <md5> | same |
| dump sha256 (not a pin) | <sha> | <sha> |
| duration | <mm:ss> | <mm:ss> |

`snapshot_pins.py compare`: EQUAL. The live lake before the write [prewrite-live.txt]: 159,903
budget_lines rows, 16 route-unsafe (PB2024 O&M 5 / RDT&E 5, PB2025 O&M 3 / RDT&E 3), no 0390DOM, a
17-column map, no p1_route_safe_codes; `era-map check --strict` 0 undecided, 0 stale.

### W1 [w1-pytest.log, w1-vitest.log, w1-ruff.txt]

pytest <passed> passed, <skipped> skipped, 0 failed; vitest <files> files / <tests> tests; pyflakes
(`uvx --offline ruff check --isolated --select F,E9`) on the <k> touched modules: no finding beyond
A's (cli.py <h>/<a>, export_site.py <h>/<a>).

### Rehearsed writes on fu-post and fu-pre [pg-pins-*.json, s194-post-*.log, s194-pre-*.log, rehearsal-0390d-apply.txt, parity-pg-pre-post.txt, parity-abort-fu-pre.txt]

| Step | Result |
|---|---|
| pins, fu-pre vs fu-post scratch | only jbook_documents differs (each points at its own raw_docs) |
| fu-post `--check` / `--dry-run` | CLEAN / ROLLED BACK, pins unchanged |
| fu-post `--apply --revert-file s194-fu-post-revert.json` (its only write) | COMMITTED; only budget_lines moved: 159,903 → 159,899 rows; 0390DOM PB2024 5 (325,095), PB2025 3 (194,641), PB2026 4 (114,635); O&M ids 47733–47735, 349016–349020 kept; new PB2026 ids <ids>; 0 route-unsafe |
| fu-pre `--dry-run`, then `--apply --revert-file s194-fu-pre-revert.json` (after both fu-pre exports) | COMMITTED; account 0390D's 350 rows equal fu-post's, ids included; the two revert files' `before`, re-keyed, deleted and inserted rows equal |
| fu-pre `--revert --revert-file s194-fu-pre-revert.json` | restored 16 pre-write rows (re-keyed 8 back, re-inserted 8, removed 4); every table's pin equal to fu-pre's before any write, ids included (Q24 (b)) [pg-pins-pre-reverted.json] |
| fu-pre second `--revert` | the database already holds the pre-write rows; nothing to revert |
| abort-path lake rehearsal: the A worktree's `jbooks export-facts` and `dbt build --select p1_era_code_decisions stg_budget_lines+` on a clone of fu-post, `p1_route_safe_codes` dropped | PASS=<n> ERROR=0; `lake-parity: EQUAL` against fu-pre (nine relations and `jbooks/budget_lines.parquet`) |
| `jbooks export-facts` | budget_lines.parquet 159,899 rows [export-facts-fu-post.log] |
| `dbt build --select p1_route_safe_codes p1_era_code_decisions stg_budget_lines+` | PASS=<n> WARN=<w> ERROR=0; map built before the program table, conservation after both [dbt-build-fu-post.log, dbt-order-fu-post.txt] |
| rebuilt warehouse | map 18 columns, decided_on 14th; 0390D map rows: B7 same_program 0390DOM 7, RDT&E exclude_route_unsafe 7; era-map check 0/0; 0 views read the live lake [postbuild-fu-post.txt] |

### Exports [export-*.log]

A@fu-pre <N_pre> citations; B@fu-pre <N_pre>; B@fu-post and B2@fu-post <N_post>. Export times
<mm> / <mm> / <mm> / <mm> minutes. dbt test nodes: A 196, B <n> [dbt-tests.txt].

### Control [control-diff.txt]

B@fu-post vs B2@fu-post: identical <i> · equivalent <e> · reordered <r> · changed 0 · only in A 0 ·
only in B 0; float noise <f> files / <v> values; `proof diff: EQUAL`. noise-fu.json: <k> classes,
classes_sha256 <sha>, file sha256 <sha>.

### P2 — code (A@fu-pre vs B@fu-pre) [p2-diff.txt, p2-fact-delta.json]

`proof diff --expect expected-diff-code.json`: PASS, every rule matched (the 256 v1 receipt shards
only in A; the /years/ core changed and its two shards only in B; the two search aliases; the F015E0
note; the map scope; the dbt count <196> → <n>; json_sidecars <a> → <a − 254>). fact_delta: no fact
added, removed or changed (`citations.json` identical up to noise); budget_lines, budget_lines_decade
and fct_budget_trajectory equal.

### P2b — /years/ (A@fu-pre vs B@fu-pre) [p2b-report.json]

| File | Bytes | Gzip |
|---|---|---|
| json/years_matrix.json (core, schema 2) | <b> | <g> (cap 780,074) |
| json/years_matrix/decade.json | <b> | <g> |
| json/years_matrix/detail.json | <b> | <g> |

build_id <sha> on all three; 1,938 rows; leg j 0 mismatches; every A cell unchanged. Added decade cells:
14,985 era (4,995 in the default view; 147 on the seven org-split rows) and 63 modern (all on the
org-split rows). Org-split rows' non-decade cells added: <list>. Totals chart (Q15): panel 524 → 1,063
of 1,938 programs; FY2024A→FY2026R +9.34% → −2.61%; FY2015A→FY2026R +108.17% → +103.71%. The design's
1,056 omitted the seven org-split rows.

### P1 — lake (B@fu-pre vs B@fu-post) [p1-diff.txt, p1-fact-delta.json, p1-content.txt]

`proof diff --expect expected-diff-lake.json`: PASS. fact_delta: <WAVE_D> new facts (<w> workbook,
<d> derived), every one traced to pe_bli 0390DOM; the eleven named aggregates moved by exactly
+3,243 (universe 385,268,393 → 385,271,636; Army 43,338,494 → 43,341,737; bridge 227,538,773 →
227,542,016; …), nothing else moved; budget_lines +4 (0390DOM), budget_lines_decade +<m> 0390DOM and
+<e> 0390D-ARMY-L1, fct_budget_trajectory <+0 or +1>; breakdowns changed 11, new <k>. The 0390DOM
sidecar: printed_code O&M, exhibit_family om, <n> decade points, <e> before PB2024. Era summary:
same_program 727,939,107K (919 chains, 5,860 lines), exclude_route_unsafe 5,030,464K (1 chain, 7
lines), R-DEC-ERA-B7 801,553K. Flow A|0390D 213,282; coverage 77.9% and $385.3B unchanged;
program pages 2,563.

### P3 — F-15 [p3-hermetic.txt, p3-capture.json, f15-snapshot-diff.txt]

Hermetic history sha256 <H>: the only leaf that moved is programs[F015E0].note, which now opens
"This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include". B@fu-pre and B@fu-post ship
exactly <H>; captured and pinned from B@fu-post (source_rows 467, series 195, previews 207). Page
snapshot: no pre-wave value moved; F015E0 label <same | old → new>; new captures <list>; re-pinned.

### Gates on B@fu-post [gate-*.log, link-coverage-fu-post-B.txt, site-verify.log, site-vitest.log]

verify-era-map (legs a–h), verify-phase5e, verify-lineage, verify-phase5b1: PASS. link-coverage:
PASS against data/research/link_coverage/baseline.json (<pct>% source-linked; <x> detail cards cited
by XML path, counted apart, Q20). `npm run verify` overall PASS (<g> gates); vitest PASS. Sitemap
4,350 (live 4,349 + /program/0390DOM/) [sitemap-b.txt].

### Page weights [weights.txt]

| Page | Stamp before | Measured | Ceiling |
|---|---|---|---|
| /methodology/ | 161,353 / 45,336 | <raw> / <gzip> | 162,000 / 45,400 |
| /families/f-15/ | 703,427 / 68,538 | <raw> / <gzip> | 725,000 / 70,000 |
| /data/ | 85,358 / 14,530 | <raw> / <gzip> | 105,000 / 15,600 |
| /years/ | 37,362 / 7,668 | <raw> / <gzip> | 45,000 / 9,000 |
| /programs/ | 2,968,731 / 310,063 | <raw> / <gzip> | 3,150,000 / 330,000 |
| /agency/*/ (heaviest) | 1,755,341 / 120,583 | <raw> / <gzip> (<page>) | 2,060,000 / 137,000 |

No ceiling raised. /years/ scripts: <k> chunks, <raw> / <gzip> gzip (pre-wave 15, 890,636 / 271,283)
[years-chunks.txt].

## What the release still has to show (Task 22)

A fresh snapshot of the live lake carries fu-pre's pins; the live write, export-facts and dbt build
leave the live lake equal to fu-post (`lake_parity.py`); the release export equals B@fu-post except
for SAM registrations stored after fu-post; W3–W6 pass on the live state; the live checks after the
deploy.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/docs/superpowers/reviews/fu-release1-proof.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(review): follow-ups release-1 proof — rehearsed write and revert, P1/P2/P2b/P3, gates on B@fu-post" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `1 file changed`.
