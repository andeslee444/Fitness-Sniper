# Families piece 1 follow-ups (#193-#206) — design

**Date:** 2026-10-04
**Status:** Approved 2026-10-04 (owner answers recorded in §2; ROADMAP commits 53dff043, 532205c9); recovered and finalized 2026-10-13
**Parent:** [2026-10-02-era-procurement-history-design.md](2026-10-02-era-procurement-history-design.md)
(families piece 1, deployed 916ae88e) and
[2026-10-02-platform-families-overview.md](2026-10-02-platform-families-overview.md).
**Base:** main `7dccd983` plus `53dff043` and `532205c9` (the two ROADMAP owner-decisions
commits), branch `followups-2026-10-04`.
**Plan:** [2026-10-04-families-piece1-followups](../plans/2026-10-04-families-piece1-followups/README.md),
with the task numbers of Appendix A.
**Evidence base:** four read-only research passes on 2026-10-04. They covered /years/,
Chem Demil, copy and hardening. They read the live lake (DuckDB `read_only`, every
read outside :12–:22), Postgres (read-only psql), `data/site` (built 2026-10-04 15:29,
byte-identical to the S5 proof for `years_matrix.json`), `site/out` and the raw
workbooks. Scratch scripts and outputs were in the session scratchpad `fu-plan/`:
`ym_era_sim.py`, `ym_shard_sizes.py` (output in `shard_sizes.txt`), `r194/`,
`weigh_edits.mjs`, `t7b.mjs`, `t9.mjs`, `narr_volume_census.*` and `npmci/`. Line numbers
are hints; anchor on the quoted text.

> **Note (2026-10-13): the 2026-10-04 measurements may have moved slightly.** Every figure
> in this spec was measured on 2026-10-04. Since then the hourly SAM job has finished (all
> 200 families have a stored SAM answer); otherwise the lake, Postgres and `data/site` are
> as of 2026-10-04. Figures that touch SAM registrations, citation counts, `site_meta`
> counts, `llms.txt` or page weights may therefore differ a little today. Each plan task
> re-measures every figure it quotes, says how it measured it, and reports any difference
> from this spec. The 2026-10-04 scratchpad was lost before 2026-10-13 (macOS clears
> `/private/tmp`), and with it the research scripts named above and the group drafts and
> notes that cross-review remarks cite ("G2 notes, contract issue 5", "G4 notes C-34" and
> so on); a task re-creates any script it needs. This text was recovered verbatim from the
> 2026-10-04 session and finalized on 2026-10-13: §2 records the owner's answers; text that
> assumed an unanswered alternative or the original F015E0 gloss was edited; §4.4 and §8
> gain the `--revert` mode (Q24 (b)); Appendix A carries the final task numbers, and draft
> task numbers in cross-review remarks are replaced by them.

---

## 1. Scope and success criteria

This design clears backlog #193–#206 before piece 2 (family registry). It changes
nothing outside these entries, except for two adjacent defects that the research found
and that block a gate this design adds (§3.5). Those two are filed as #207 and #208
(Task 1) and closed in this wave.

| # | Entry | Disposition | § |
|---|---|---|---|
| #193 | /years/ sharding and era fence | **Do.** Column-tier shards (scheme A), fence lifted, sidecar-parity gate | 3 |
| #194 | 0390D Chem Demil lines | **Do, amended.** The O&M line loads under `0390DOM` with a page, as decided. The RDT&E line restates two R-1 program elements to the thousand, so loading it would double-count: it gets no page and is recorded as an R-1 restatement (Q1 (a)). The era O&M chain joins `0390DOM` as owner batch B7 (Q3) | 4 |
| #195 | JLTV narrative cited to a book that does not print it | **Do, systemic.** 4,231 PB2026 narratives have the same defect. The full re-attribution fix ships as a second release (Q19 (A)), with 111 `opening_only` citations held by a ratchet (Q26) | 5.6 |
| #196 | Dead v1 PDF receipt files | **Do** (owner signed off 2026-10-04). No R2 step is needed | 5.7 |
| #197 | Search aliases for JASSM and C-130J | **Do**, plus a cross-seed membership test | 5.8 |
| #198 | Era-map review tooling | **Do**, except 3 items not worth doing (§6.9) | 6.2 |
| #199 | Proof tooling and notes | **Do**, except 6 items not worth doing (§6.9) | 6.1 |
| #200 | link-coverage fails open | **Do** | 6.5 |
| #201 | F-15 snapshot tooling and note | **Do**, bundled with #206 T9 so the F-15 fixtures are re-pinned once. No trim now: 1,426 gzip bytes are left after T9 | 6.6 |
| #202 | P-1 loader tripwires | **Do**, before #194's load | 6.3 |
| #203 | verify-era-map and era dbt tests | **Do**, except the sheet name in `source_cells` | 6.4 |
| #204 | Era fences rely on optional arguments | **Do**, after §3 removes the /years/ fence | 6.7 |
| #205 | `npm ci` lockfile and stale comments | **Do** first. New worktrees need `npm ci` | 6.8 |
| #206 T4 | /methodology/ gap sentences | **Subsumed by #193.** Lifting the fence makes both sentences true, and a new gate leg backs them (§3.6). No /methodology/ edit is required | 3.6 |
| #206 T6 | `decided_on` on the map | **Do** (owner-decided) | 5.1 |
| #206 T7 | Three definitions of "tier pending" | **Do**, with the exact strings the owner accepted (Q16) | 5.3 |
| #206 T9 | F015E0 note gloss | **Do** (owner-decided), with the gloss as Q17 amended it: "[the PB2026 F-15EX AP (F015EX) P-40]" | 5.2 |
| #206 T11 | Two claims guarded only by string pins | **Do**: verify-era-map legs g and h | 5.4 |
| #207 (new) | Org-split rows get no decade cells on /years/ and "—" on /programs/ (`_acct_key`) | **Do** inside #193. The parity gate cannot pass without it | 3.5 |
| #208 (new) | /agency/[org]/ looks decade cells up by bare `pe_bli` (27 split-key rows show "—") | **Do** inside #193 (Q10) | 3.5 |

**Success criteria**
- **/years/ matches the program pages.** Every row that has a program page shows exactly
  that page's decade points, all PB2017–PB2026 editions included. A new static leg
  checks this as zero mismatches in both directions. Today the default view has 4,995
  cells missing.
- **/years/ size.** On open, /years/ downloads no more than today's 780,074 gzip bytes;
  the measured core is 347,657. Every /years/ file is at most 4 MiB, measured on the
  exact bytes written. The cap is not raised.
- **0390D Chem Demil.** The O&M line's money is on the site under a route-safe key, and
  nothing is counted twice: the account's PB2026 total becomes the P-1's own printed
  total, 213,282K. `budget_lines` holds no `pe_bli` with `& # / ? %` or whitespace, and
  a dbt test enforces it. The write can be undone: `s194_chem_demil.py --revert` restores
  the exact pre-write rows, and a rehearsal proves it (Q24 (b)).
- **`decided_on`.** `p1_era_line_map` publishes `decided_on`, and verify-era-map leg b
  proves that it equals the seed.
- **Facts.** Every fact ID published before this wave keeps its amount and inputs,
  except the derived aggregates that §7's rule lists name.
- **Links.** Budget figures stay 100% source-linked, and no figure loses a complete PDF
  receipt (V9).
- **F-15 history.** `f15_funding_history.json` changes only in the F015E0 `note`.
- **Weight and prose.** No page-weight ceiling and no cap is raised. No disclosure prose
  is trimmed.
- **Hardening.** Each hardening item lands with a test that is red before the fix and
  green after it.

## 2. Owner decisions

### 2.1 Binding (ROADMAP, "Follow-ups first (owner, 2026-10-04)", verbatim)

> before piece 2, clear the piece-1 follow-ups #193–#206, with these owner decisions:
> shard `/years/` and lift its era fence so it shows PB2017–PB2023 procurement (#193);
> load the two 0390D Chem Demil lines under route-safe codes with pages (#194); remove
> the unread v1 PDF receipt files from the deploy (#196); add the gloss "This exhibit
> [the PB2026 F-15EX (F015EX) P-40] does not include …" to the F015E0 note (#206 T9);
> and publish each era decision's date in `p1_era_line_map` as a `decided_on` column
> (#206 T6).

The owner's answers to this design were added to the same paragraph later on 2026-10-04
(commit 532205c9). Verbatim:

> *Owner, later 2026-10-04, after the follow-ups design found the RDT&E Chem Demil line
> restates R-1 PEs 0708081D + 0708083D to the thousand:* the RDT&E line gets no page and
> is recorded as an R-1 restatement (only the O&M line gets a page, `0390DOM`); the era
> O&M chain joins that page as owner batch B7; #195 gets the full re-attribution fix as a
> second release; the F015E0 gloss names the exhibit exactly, "[the PB2026 F-15EX AP
> (F015EX) P-40]". The design's other recommendations stand (its Q2, Q4–Q16, Q18,
> Q20–Q23, Q25, Q26), and the Chem Demil write gets a `--revert` mode (Q24 (b)).

These answers supersede two clauses of the first paragraph: only the O&M line gets a page,
and the gloss is the amended string, not "[the PB2026 F-15EX (F015EX) P-40]". The owner
gave Q3's answer in chat on 2026-10-04 as "Join it (Recommended)"; batch B7's answers file
records it as `owner_reply` (§4.5). Q15's totals-chart change was put to the owner, who did
not object; release 1's ROADMAP stamp records it (§8 step 8).

Earlier rulings that still bind:
- R-DEC-ERA-SAME, R-DEC-ERA-HISTORY and R-DEC-ERA-EXCLUDE, together with batches B1–B6.
- Publish the smaller true number (2026-08-07).
- The era table on /downloads/ shows counts only.

### 2.2 Questions and the owner's answers (research findings the first 2026-10-04 decisions predate)

The owner answered every question in §2.2 and §2.3 on 2026-10-04 (§2.1). "Recommendation
accepted" means the answer is the Recommendation column as written. The Task(s) column gives
the final task numbers of Appendix A. It replaces the draft "Blocks" codes (CD-1…, Y-1…,
N-1… and so on), which named tasks in the lost 2026-10-04 drafts.

| Q | Question | Recommendation | Answer (owner, 2026-10-04) | Task(s) |
|---|---|---|---|---|
| Q1 | **RDT&E line.** "Chem Demilitarization - RDT&E" equals R-1 PEs 0708081D + 0708083D. All 65 same-slug (edition, amount type) pairs PB2017–PB2025 match, as do PB2025's FY2024 CR column and PB2026's four columns (1,002,560 / 754,762 / 210,039 / 210,039). That money is already on those two pages. (a) No page: record the line as an R-1 restatement and point readers to the two PEs. (b) Give it a page, fenced out of every R-1+P-1 sum. (c) Give it a page summed like any other line. | **(a).** (b) fulfils the 2026-10-04 wording but needs at least five fence points of the kind #204 shows fail open. (c) double-counts $210.0M of FY2026 request, $754.8M of FY2025 enacted and $1.00B of FY2024 actuals, which breaks the 2026-08-07 rule. | **(a).** No page; the line is recorded as an R-1 restatement of 0708081D + 0708083D (`P1_R1_RESTATEMENTS`, §4.3). | 6, 7, 8, 12 |
| Q2 | Approve the keys `0390DOM` (and `0390DRDTE` only under Q1(b))? The printed code stays in `line_item_code`. | **Yes.** The keys are alphanumeric: they pass the llms.txt regex `/program/[A-Z0-9]+/` and the receipts grammar `[A-Za-z0-9:]+`, and they collide with nothing. | Recommendation accepted: `0390DOM` only. There is no `0390DRDTE`, because Q1 is (a). | 6 |
| Q3 | **Era O&M chain** (`O&M\|0390D\|\|2017-2023`, 7 lines, $801,553K FY2015–21 actuals). Join it to `0390DOM` as batch B7, reversing the 2026-10-02 exclusion for this chain? | **Yes, B7.** The page now exists and the reason "route-unsafe" stops being true once the alias exists. This also needs one scope amendment string (§4.5). | **Yes**, batch B7. Given in chat as "Join it (Recommended)"; B7's answers file records it as `owner_reply`, with `decided_on` 2026-10-04 (§4.5). | 8, 10 |
| Q4 | **Era RDT&E chain** ($5,030,464K). Keep `exclude_route_unsafe`? | **Keep it, with a dated note** that the line also restates R-1 PEs. Under Q1(a) the code has no route-safe key, so the reason stays literally true and the published vocabulary does not change. | Recommendation accepted. | 1, 8 |
| Q5 | O&M page copy: show the printed code "O&M" plus one sentence on why the address differs, and an "O&M" badge instead of the derived "Procurement"/"BLI" badge? Strings in §4.6. | **Approve.** | Recommendation accepted, including the "O&M" badge beside the "BLI" term (§4.6). | 12 |
| Q6 | Count the $3,243K FY2026 O&M request in the /programs/ "FY2026 procurement and RDT&E request" universe and in the flow chart? | **Count it.** 0390D is a procurement-title account and the P-1 prints the line. $385.3B, 77.9% and $227.5B do not change. | Recommendation accepted. | 12 |
| Q7 | Dated correction notes on ROADMAP #194 and spec §5.2. (a) 16 PB2024–25 rows are in Postgres and the lake; only PB2026's 8 rows were deleted, on 2026-07-05, by `scripts/clean_junk_pe_bli.py`. (b) The missing money is the O&M line only: $87.4M of FY2024 actuals, not $1.09B, and $801.6M for FY2015–21, not $5.83B. | **Approve.** | Recommendation accepted. | 1 |
| Q8 | Re-key the 8 O&M rows in place (ids kept) as an explicit exception to piece 1's "never re-key `pe_bli`", which was written about era keys? Under Q1(a), delete the 8 RDT&E rows. None of their fact IDs is published. | **Approve.** | Recommendation accepted. | 7 |
| Q9 | Retire `scripts/clean_junk_pe_bli.py`? It treated real lines as junk. | **Retire it**, with a dated note. | Recommendation accepted. | 7 |
| Q10 | /years/ scheme A. The core keeps the name `json/years_matrix.json` (schema 2), with lazy `decade.json` and `detail.json`. Fold in the org-split key fix and the /agency/ slug lookup? | **Yes to all.** | Recommendation accepted. | 13, 14 |
| Q11 | Size rules. Keep the 4 MiB cap per file, measured on the exact compact bytes written (today the guard checks 2,900,904 B while 3,178,320 B ships). Add a new budget: core gzip ≤ 780,074. | **Yes.** This tightens, never raises, and readers never download more on open than before. | Recommendation accepted. | 13, 15 |
| Q12 | Revert the /years/ tooltip for gaps before PB2024 to "Not in the PB20XX edition"? | **Yes.** All 1,032 remaining default-view P-1 gaps are true absences under the decision identity: 985 codes not printed, 41 joined to the sibling account's row, and 6 reused-code exclusions. | Recommendation accepted. | 14 |
| Q13 | Replace the 69-byte clause "the trajectory workbook simply has no row for that program and column" with "the edition workbook simply holds no line for that program and column" (also 69 B)? | **Yes.** For decade columns the source is the edition workbook, not the trajectory workbook. | Recommendation accepted. | 15 |
| Q14 | New /years/ edition legend sentence: "Before PB2024, a procurement row shows only lines a reviewed decision joined to it." This is client-side and costs no weight. | **Approve.** | Recommendation accepted. | 14 |
| Q15 | Totals chart: accept that the balanced panel grows from 524 to 1,056 programs and that FY2024A→FY2026R moves from +9.3% to −2.5%? | **Accept it.** The caption already states the panel's size and share, and every number in it is a visible sum. Record the change in the ROADMAP stamp. | Recommendation accepted: the owner was told and did not object. Release 1's ROADMAP stamp records the change (§8 step 8). | 22 |
| Q16 | T7: approve the six /methodology/ strings and two /about/ strings in §5.3? | **Approve.** | Recommendation accepted. | 19 |
| Q17 | T9: keep the decided gloss, or name the exhibit "[the PB2026 F-15EX AP (F015EX) P-40]" (+3 B)? Page 71 prints "F015EX / F-15EX AP" (P-1 line #7). A second F015EX P-40, "F-15EX" (line 44, Vol II), also exists. | **Amend to "F-15EX AP".** "The F-15EX P-40" would lead a reader to the line-44 exhibit. | **Amended:** the gloss is exactly "[the PB2026 F-15EX AP (F015EX) P-40]". | 20 |
| Q18 | T6: publish `decided_on` only, not `decided_by` (always "owner", and a test already enforces that), using the §5.1 description that a class ruling's date is the day the rule was approved with the spec? | **Yes.** | Recommendation accepted: `decided_on` only. | 9 |
| Q19 | #195. (A) Re-point about 4,200 narrative citations to the volume that prints them, host up to 20 superseded PB2026 volumes (162,040,168 B on R2), keep fact IDs, and let a citation's sha256 differ from the sha hashed into its fact ID. (B) A scoped JLTV fix plus a ratchet. | **(A), as a second release.** (B) leaves thousands of citations pointing at a book that does not print the passage. | **(A)**, as release 2. | 23, 24, 25, 26 |
| Q20 | #200: 440 detail cards show a value cited by XML path with no fact ID. Keep them outside V9 and report them as a separate count? | **Yes.** Counting them as (c) or (d) would fail the absolute check for cards that are cited. | Recommendation accepted. | 5 |
| Q21 | #201: add an `aria-label` on the F015E0 row header, so that "Note below" leaves every cell's row name? | **Yes**, in the same sign-off as Q17. | Recommendation accepted. | 20 |
| Q22 | Close the items in §6.9 with a dated reason in their Status lines? | **Yes.** | Recommendation accepted. | 22 |
| Q23 | #197: extend the seed check to `site/src/lib/aliases.ts`? It maps B-21 to 0604015F under different chip semantics. | **No.** File it for the families registry (piece 2), which becomes the single source. | Recommendation accepted: filed for piece 2 in release 1's stamp (§8 step 8). | 22 |

### 2.3 Cross-review additions (2026-10-04; questions the drafts raised)

| Q | Question | Recommendation | Answer (owner, 2026-10-04) | Task(s) |
|---|---|---|---|---|
| Q24 | **No rollback for the live Postgres write.** The abort path (§8 step 3) restores `data/site` only. If the release stops after `s194_chem_demil.py --apply` commits, the live lake keeps the wave's rows while the main checkout runs piece-1 code, whose `export-site` refuses the alias row and whose `govbudget build` would rebuild the map without `decided_on`/B7 (G5 notes, contract issue 7). (a) Accept: the release task (Task 22) stops and reports; the owner decides. (b) Add a `--revert` mode to `s194_chem_demil.py` that restores the 16 rows from the fu-pre dump, with its own rehearsal. | **(b) if the owner wants an unattended abort path; otherwise (a).** | **(b).** `--revert` restores the exact pre-write rows, from the pre-image `--apply` records (which must equal fu-pre's rows), with its own test and rehearsal; release 1's abort path uses it (§4.4, §7, §8). | 7, 21, 22 |
| Q25 | **The #198 guard drops a re-ruled chain's seed row.** When `propose` sends a class result that differs from the seed to review (§6.2), it also removes the old class row from the seed, so B7 can be rendered and ratified; until the owner ratifies, `era-map check --strict` and verify-era-map leg b fail (undecided keys). This is fail-closed but not in §4.5/§6.2's wording (G4 notes C-35b). Approve? | **Approve**, together with B7. | Recommendation accepted. | 4, 10 |
| Q26 | **#195 measured against §5.6** (release 2): the paged rule fails 339 of 6,078 paged PB2026 citations, not 4; Task 23 relocates 228 and keeps 111 as `opening_only`, which Task 24 ratchets (`OPENING_ONLY_CEILING = 111`) instead of failing. Fallback B is not drafted (its figures do not match the measurement). Accept the ratchet? | **Accept**, with the 111 named in release 2's stamp. | Recommendation accepted; release 2's stamp names the 111. | 24, 26 |

Other cross-review corrections, recorded where they apply: §4.6 (0390DOM gets no /years/ row and no search document; the restated-line search alias is dropped); §5.1 (`decided_on` is column 14 of 18); §5.7 (nine unused imports, AST-checked); §6.3 (the tripwire keys on the full upsert key, `amount_type` included; the stale comment is `:183-186`); §6.4 (ten regex sites); §6.8 (decided 2026-10-02); §7 (P1/P2 re-paired; Postgres pins by table md5; W1 pyflakes via `uvx`); §8 (`.proofs/fu-release-pre-site`); Appendix A (the S0 ledger, the map-alias task, two superseded drafts). Design §4.2's seed gains an `exhibit_family` column (§4.6 reads it "from the seed"); `P1_R1_RESTATEMENTS` lives in `jbooks/route_safe_codes.py` as a mapping the loader and exporter share; the loader loads each edition's R-1 first (`cli._jbooks_load_rollups` gains an ORDER BY) and compares PB2025's CR column under `R1_AMOUNT_TYPE_EQUIVALENTS` (G2 notes, contract issues 1–4). The v2 receipt matcher (`program_pdf_receipts`) accepts a citation `pe_bli` that is the route-safe key of the row's printed code (Task 12), without which every 0390DOM workbook citation stops the export.

## 3. /years/ shards and the fence lift (#193, #206 T4, #207, #208)

### 3.1 Measured today
**The file.** `json/years_matrix.json` is 3,178,320 B on disk and 780,074 B at gzip-9. It holds:
- 1,938 rows in 25 orgs;
- 30 decade columns, 12 of them shown by default;
- 7 amount types;
- 2,623 project rows.

**The fence.** It is `export_site.py:17745-17747`, which drops `era_grain_fids` from
`decade_grains`.

**A read-only simulation without the fence** (`ym_era_sim.py`: each row joined to its
own sidecar's `decade_series`, with era fids taken from `budget_lines_decade` and
`decade_era_map`):
- 14,985 cells are added on 795 P-1 rows: 14,082 workbook leaves and 903 era-map sums.
- 4,995 of them are in the default view, which reproduces final-review T4 exactly.
- No column appears or changes its measure, and there are 0 mismatches with existing
  cells.
- As one file it would be 3,984,416 B on disk, leaving 209,888 B. PB2027 adds a block
  of about 296 KB, which would exceed the cap.

### 3.2 Scheme A: split by column tier
| File | Holds | With era: bytes / gzip |
|---|---|---|
| `json/years_matrix.json` (core, `schema_version: 2`) | the header, every row (`pe_bli, title, slug?, family_id?, np`), and the cells of the 12 `decade_default_columns` | 1,201,028 / 347,657 |
| `json/years_matrix/decade.json` (lazy) | the other 18 decade columns | 1,510,541 / 434,338 |
| `json/years_matrix/detail.json` (lazy) | the PB2026 amount types, Δ and %Δ, and projects | 1,355,038 / 286,102 |

Sizes come from `ym_shard_sizes.py` on the simulated era payload. The largest file uses
36% of the cap. The core grows by about one column per edition, so PB2027 fits.

Alternatives, all measured:
- **By exhibit:** `r1` 625,614 + `p1` 389,765 gzip, both loaded on open.
- **By edition block:** 999,023 gzip on open, because the defaults FY2015A–21A live in
  the history block.
- **By row range:** about 1.0 MB on open, and the per-file cap stops guarding growth.

None of these defers anything, so all three are rejected.

Keeping the core's file name leaves these readers and copy unchanged:
- the build-time readers: `getProgramDecadeCells` reads `fy2024a` and `fy2026r`, both
  default columns, and `getDecadeEditions` reads the header;
- the /coverage/ derivation sentence that names `years_matrix.json`
  (`coverage-map.ts:455`; /coverage/ has 295 gzip bytes left);
- `verify_live_assets.mjs`;
- the linkgraph target.

### 3.3 Exporter (`src/govbudget/export_site.py`)
- **Build v1 first.** `_emit_years_matrix` still builds today's v1 payload in memory,
  now without the era filter. Its `era_grain_fids` parameter is deleted (§6.7).
- **Split.** A pure function `split_years_matrix(payload) -> dict[str, dict]` returns
  `{"years_matrix.json": core, "years_matrix/decade.json": …, "years_matrix/detail.json": …}`.
  A pure function `merge_years_matrix(core, decade, detail) -> dict` is its inverse, and
  pytest checks `merge(split(p)) == p` (ignoring `schema_version`, `build_id`, `shards`
  and `np`) on a fixture and on the live payload.
- **Shard rows** are keyed by `slug ?? pe_bli`. That key is unique, because split rows
  carry slugs.
- **Build id.** Every file carries `build_id`, the sha256 of the canonical v1 payload.
  It is a content hash, never `built_at`, so that byte-identity proofs keep working. The
  core's `shards` manifest lists each shard's path, columns, bytes and sha256.
- **Writer.** A new `_write_json_compact(path, obj) -> int` writes
  `separators=(",", ":"), sort_keys=True` to a temporary file. It raises when the
  encoded length is above `_YEARS_MATRIX_MAX_BYTES` (unchanged, 4 MiB), and otherwise
  does `os.replace`. The guard therefore measures exactly the bytes that ship. The core
  also has to satisfy `gzip -9 ≤ 780,074` (`_YEARS_MATRIX_CORE_GZIP_MAX`, Q11).
- **No stale shards.** `json/years_matrix/` is rewritten whole, and
  `prepare-assets.mjs` 5d mirrors the directory (`copyDir` removes it, then copies), so
  a stale shard cannot ship.

### 3.4 Island (`site/src/components/years-matrix.tsx`)
- **Fetch order.** The island fetches the core on mount. It fetches `decade.json` the
  first time a picker chip turns on a non-default decade column, and `detail.json` the
  first time a detail column is shown or a row is expanded. The expand caret reads `np`
  from the core.
- **Loading.** A column is added only after its shard resolves. Until then its chip
  shows a loading state and the table sets `aria-busy`. A "—" must never stand in for an
  unloaded cell, because "—" means "absent from the book".
- **Build-id mismatch.** If a deploy lands between the two fetches, the island refetches
  the core once. If the ids still differ, it shows a per-column error and nothing else.
- **Gate marker.** The table carries `data-shards="core[ decade][ detail]"` for the
  gates.
- **CSV.** CSV export covers the visible columns, all of which are loaded by
  construction.
- **Totals chart.** `YearsTotalsChart` uses the default columns only, so it needs only
  the core.
- **Fence code removed:** `PROCUREMENT_GRID_FIRST_EDITION` (`:1587`), the
  `procurementBeforeGrid` branch (`:1633-1644`) and the `isPeCode` import.

### 3.5 Two adjacent defects folded in (filed as #207 and #208 in Task 1, closed here)
**Org-split decade lookup (#207).**
- `_acct_key` (`export_site.py:17760-17761`) looks rows up with the key
  `('20','0300D','DCSA')`, while the grains are stored under `('20', None, 'DCSA')`
  (`:17878`).
- Seven rows lose every decade cell: 20-DCSA, 20-DTRA, 30-DMACT, 30-DTRA, 30-OSD,
  500-DHRA and 500-DLA. That is 63 modern points and, after the lift, 147 era points.
- /programs/ shows "—" for FY24 and FY26 on /program/20-DCSA/, while that page cites
  FY2024 2,135 (fid `128936791c3d0741`).
- **Fix:** gate the account on `is_account_split`, the pattern already used at `:6072`
  (ROADMAP #45). The same mismatch probably also removes `fy_2025_total` and Δ from these
  rows; the proof measures this.

**/agency/[org]/ lookup (#208).**
- `agency/[org]/page.tsx:91, :115, :361-367` call `decadeCells.get(p.pe_bli)`.
  `getProgramDecadeCells` keys by `slug ?? pe_bli`, so 27 split-key rows render "—"
  (e.g. /program/1350/ on /agency/N/).
- **Fix:** look up by `slug ?? pe_bli`.

### 3.6 Gates and tests
**`site/scripts/gates/yearsmatrix.mjs`.**
- **Static legs (a, b, d, e, f, g, i)** run on the merged view through one shared
  loader, `loadYearsMatrix(dir)`.
- **Leg g** resolves an era cell's source rows through
  `data/site/data/p1_era_line_map.parquet` (also in `yearsmatrix-recompute.py`). The
  conditions:
  - the key's `fiscal_year` equals the stated edition;
  - `program_key` equals the row's `pe_bli` and the decision is `same_program`;
  - a split row's pins match its slug;
  - the workbook sha is among the rows, and the row count equals the inputs.

  A dry run passed 14,985 of 14,985.
- **Non-vacuity:** sample at least one era leaf and at least one `decade_era_map` cell
  per PB2017–PB2023 edition.
- **New leg j, sidecar parity.** For every row with a sidecar and every decade column, a
  cell is present if and only if the sidecar has a point with the same (kind, edition,
  fy), with equal value and fid. Today it fails on 4,995 default-view cells plus the 7
  org-split rows; it must read 0.

  This leg is T4's "absent means absent" check. It also backs
  `/methodology/` `#coverage-years-matrix` and the `#coverage-editions` gap sentence,
  which leaves T4 subsumed.
- **G8:** every file is at most 4 MiB on disk, and the core gzip is at most 780,074.
- **Live legs c, e-UI and i3** wait on the `data-shards` marker instead of the
  `waitForTimeout` calls at `:1147-1160`, `:1384` and `:1590-1592`.
- **New live leg:** on load, the only `/json/years_matrix*` request is the core.

**Other gates and probes.**
- `linkgraph.mjs` `MIN_STATIC_FETCH_TARGETS` rises from 4 to 6, re-measured. That is a
  floor, so it tightens.
- `__tests__/fetch-targets.test.mjs:133` changes to match.
- `verify_live_assets.mjs:812` probes all three files, and `LAUNCH.md:642` changes to
  match.

**Tests that change in the same commit series.**
- `TestEraFence` is inverted into a test that era cells render.
- `TestSizeBudget` checks each file.
- The `test_export_site_pg.py:2160` spy expects `{lineage}` only.
- `test_program_member_enrichment.py:383` now reads projects from `detail.json`.
- `test_launch_deploy_landing.py:155`.
- `years-matrix.test.tsx`: 4 fetch mocks, plus the tooltip and legend pins at `:727`
  and `:735-779`.

**Spec.** §6.2 gets a dated amendment: /years/ is no longer fenced. Lineage and the
F-15 browser stay fenced.

### 3.7 What readers see, and copy
- **/years/ procurement rows** show PB2017–PB2023 cells wherever their program page
  does. The page description "a decade of edition-honest actuals (FY2015–FY2024)"
  (`years/page.tsx:32`) becomes accurate with no edit.
- **Tooltip:** "Not in the PB20XX edition" for every gap (Q12). The /methodology/
  `#coverage-editions` sentence ("…with a 'not in the PB20XX edition' note…") is then
  true again, with no edit.
- **Edition legend:** "Procurement rows here start at PB2024; any PB2017–PB2023 history
  is on the program page." becomes the Q14 sentence. It renders client-side, so it costs
  no page weight.
- **/methodology/ `#coverage-years-matrix`:** the equal-length clause swap in Q13
  (69 B → 69 B, no `'` or `&`, so the escaped HTML length is the same).
- **Totals chart:** the panel grows from 524 to 1,056 rows and the direction flips
  (Q15). This is recorded, not hidden.
- **/methodology/ byte budget.** Stamp 161,353 / 45,336 against 162,000 / 45,400, so
  647 raw and 64 gzip bytes are left (node zlib reads 45,338, which leaves 62). Each
  sentence appears twice in the HTML (SSR and RSC). Re-measure after this whole wave:
  - Q13: 0 raw, a few bytes of gzip.
  - T7 (§5.3): −13 gzip, +16 raw.
  - the dbt count 196 → 19x: same digit count.

  The wave fits, with T7's gzip saving (Q16 accepted). If a build shows it does not, Q13
  is dropped, not the ceiling raised.
- **/years/ HTML** (37,362 / 7,668 against 45,000 / 9,000) moves only by chunk hashes.
  Re-measure the island's JS chunk anyway.

## 4. 0390D Chem Demil lines (#194)

### 4.1 Measured today
**PB2026 P-1** (`fy2026/dod/p1_display.xlsx`, rows 303–304, openpyxl):
- O&M: 87,404 / 20,745 / 3,243 / 3,243.
- RDT&E: 1,002,560 / 754,762 / 210,039 / 210,039.

**Where the skip fires.** `parse_p1_rollup`'s `_is_valid_pe_bli` skip fires only on
these lines. It catches 2 rows in each of PB2024, PB2025 and PB2026, and 0 in the other
17 workbooks (`r194/skipped.py`). No real section label was ever caught.

**Postgres** still holds 16 such rows:
- PB2024: 10 rows, ids 349016–349025.
- PB2025: 6 rows, ids 47733–47738.
- PB2026's 8 rows were deleted on 2026-07-05 by `scripts/clean_junk_pe_bli.py`
  (481bba088).

**Lake vs site.** The 16 rows reach `fct_budget_lines`, plus 12 grains in each decade
table and 2 book diffs, but they are published nowhere.

**RDT&E restatement.** The RDT&E line equals R-1 PEs 0708081D + 0708083D in every
column (Q1). 0390D is the only account that appears in both exhibits.

### 4.2 Route-safe key
- **Seed.** A new seed, `dbt/seeds/p1_route_safe_codes.csv`, with columns `account,
  line_item_code, page_key, decided_on, decided_by, note`, plus `exhibit_family`
  (cross-review, §2.3). Its single row is 0390D's `O&M` line: `page_key` `0390DOM`,
  `exhibit_family` `om`, `decided_on` 2026-10-04 (the date of Q2's answer), `decided_by`
  `owner`. There is no `0390DRDTE` row: under Q1 (a) the RDT&E line gets no key and is
  handled by the restatement rule (§4.3).
- **Python access.** Python reads the seed through `jbooks/route_safe_codes.py`
  (`load_route_safe_codes()`, plus `page_key(account, code)`).
- **dbt test** `assert_route_safe_codes_valid`:
  - `page_key` is unique;
  - it matches `^[A-Z0-9]+$`;
  - it collides with no other `pe_bli` in `budget_lines` or `budget_line_details`.

### 4.3 Loader (`src/govbudget/jbooks/p1_loader.py`)
**Modern rows.**
- An alias row gets `pe_bli = page_key` and `line_item_code` = the printed code.
- Per Q1 (a), a named rule `P1_R1_RESTATEMENTS`, keyed by (`0390D`, `RDT&E`), skips the
  RDT&E line with its own counter. It is a mapping in `jbooks/route_safe_codes.py` that the
  loader and the exporter share (cross-review, §2.3). It first checks that the line equals the loaded R-1 0390D
  sum for that edition and amount type. It raises `P1RestatementMismatch` if the two
  differ, or if the R-1 is absent.
- Any other route-unsafe code on an Add row raises `UnsafeBudgetLineCode` and is no
  longer skipped silently.

**Tests.**
- `test_p1_loader_skips_appropriation_section_header_rows`
  (`tests/jbooks/test_p1_loader.py:311`) encodes the real 0390D values as "section
  totals". It is rewritten, as a dated correction, to assert the alias load, the
  restatement skip and the raise.

**Prerequisite.** This lands after §6.3's tripwires.

### 4.4 Database write and its proof
**Script:** `scripts/era/s194_chem_demil.py`, following the S1 script, with modes
`--check`, `--dry-run`, `--apply` and `--revert` (Q24 (b)).

**`--check`** parses PB2024–26 and diffs the result against Postgres. The only allowed
differences are the 16 stale keys and the missing PB2026 rows.

**`--apply`** runs one transaction under `LOCK budget_lines IN EXCLUSIVE MODE`. Per
Q1 (a) it does three things:
1. `UPDATE pe_bli='0390DOM'` on the 8 O&M rows, keeping their ids and therefore the
   lake's row order.
2. `DELETE` the 8 RDT&E rows.
3. `write_p1_rows` for PB2026's 4 O&M rows.

Before the first write it saves a **pre-image**: every column of every row in its scope
(account 0390D's P-1 rows in PB2024–PB2026, ids included; §4.1 counted 16, all stale). It
writes the pre-image to the file `--pre-image` names, through a temporary file and
`os.replace`, together with the database name and the rows' sha256, and it stops before
any write if that fails.

It then verifies:
- no other row changed in any column;
- the alias rows equal the parse;
- no `pe_bli` matching `[&#/?%[:space:]]` remains.

On any failure it rolls back.

**`--revert --pre-image <file>`** (Q24 (b)) restores the exact pre-write rows. In one
transaction under the same lock it:
1. checks the file's sha256 and that the database it names is the target;
2. refuses unless the in-scope rows are exactly the state `--apply` writes (re-derived
   from the parse, as `--check` does); if they already equal the pre-image it reports
   "already reverted" and exits 0;
3. deletes the in-scope rows whose id is not in the pre-image (PB2026's 4 O&M inserts),
   re-inserts the deleted RDT&E rows with their own ids and columns, and restores every
   column of the re-keyed O&M rows;
4. verifies that the in-scope rows equal the pre-image in every column (`EXCEPT` both
   ways) and that no other row changed.

On any failure it rolls back. It writes Postgres only; the lake steps that must follow a
live revert are in §8's abort path.

**Tests** (pytest on the 55432 test cluster): `--apply` then `--revert` on a fixture
database leaves every `budget_lines` row equal to the pre-apply rows; a second `--revert`
changes nothing; `--revert` refuses a changed in-scope row, a pre-image whose sha256 does
not match, and a pre-image taken from another database.

**No migration.** `migrate` tracks by file name, so data does not belong in a migration.

**Follow-on steps:**
- `jbooks export-facts`.
- One `dbt build --select stg_budget_lines+` that includes the §5.1 map changes, so the
  marts are rebuilt once.
- A new dbt test, `assert_budget_lines_route_safe_pe_bli`.

**Proof.** The writes are rehearsed on snapshot `fu-post` before the live write, and the
proof is P1 in §7. After the live write, the 0390D rows in the live Postgres must equal
`fu-post`'s, and the rebuilt marts must equal `fu-post`'s (`EXCEPT` both ways). The revert
is rehearsed on snapshot `fu-pre` (§7): `--apply`, then `--revert`, after which every
Postgres pin equals fu-pre's at-copy pins.

### 4.5 Era chains (Q3, Q4)
**Why the change must go to review.** After the re-key, `era-map propose` would see code
`O&M` continuing into PB2024–26 and class the chain A1, so R-DEC-ERA-SAME would apply.
That would silently overturn an owner ruling. §6.2 therefore makes `propose` send any
chain whose class result differs from a seeded owner or class decision to `review.csv`.

**Q3 (owner: yes) makes the change batch B7.**
- `review_batch_page` renders the B7 page, which records the question the owner
  answered.
- The owner has already answered: "Join it (Recommended)", in chat on 2026-10-04. B7's
  answers file (`data/research/era_map/batches/B7.json`) records that verbatim as
  `owner_reply`, with `decided_on` 2026-10-04.
- `era-map ratify --batch B7 --decided-on 2026-10-04` writes the seed row:
  `same_program`, ruling `R-DEC-ERA-B7`, `decided_on` 2026-10-04.

**Where the alias applies:**
- `p1_era_line_map.sql`: `program_key = coalesce(alias.page_key, line_item_code)`.
- `era_map.load_inputs` and `classify`: a code with an alias is route-safe.
- `UNSAFE` narrows to exactly the unaliased (`0390D`, `RDT&E`) pair, and any other
  unsafe code raises.

**What moves:**
- `era_map_summary` `same_program` becomes 727,939,107K (919 chains).
- `exclude_route_unsafe` becomes 5,030,464K (1 chain, 7 lines).
- The /downloads/ table counts move, and datatruth leg (s) re-checks them.
- The O&M page gains up to 21 era points (measured in P1).

**Scope string.** The `p1_era_line_map` scope (`export_site.py:1781`) says
`line_item_code` is "the pe_bli a same_program line's era citations carry". That is
false for the 7 `0390DOM` rows. The amendment, approved with Q3, moves the clause:

> … line_item_code (the budget line code printed on it), program_key (the pe_bli a
> same_program line's era citations carry; the printed code except 0390DOM for 0390D's
> O&M line, whose "&" cannot appear in a web address) …

**Q4** (recommendation accepted). The RDT&E chain keeps `exclude_route_unsafe`. ROADMAP
#194 and piece-1 spec §5.2 get a dated note that the line also restates the R-1 PEs
(Task 1 files it with Q7's notes).

### 4.6 Pages
**Tier.** `/program/0390DOM/` is rollup tier. No R-2 or P-40 exists, and no Chemical
Agents and Munitions Destruction book is registered, so it is cited to workbook cells
only.

**Where it appears:**
- the sitemap (measured: 4,349 → 4,350);
- `programs_excluded.json` (`no_detail`).

It is not added to `programs.json`, because P-1 has no `fy_2025_total`, or to
`agencies.json`. *Cross-review correction (2026-10-04):* it therefore gets no /years/
row and no `search_quick.json` program document either: both iterate exactly
`programs.json`'s 1,938 rows (measured on the S5 export; the rollup page 0708081D is in
neither). The earlier "/years/ (about 0.8–0.9 KB of the core)" and "`search_quick.json`"
bullets are withdrawn.

**Presentation (Q5).**
- The sidecar gains `printed_code: "O&M"` and `exhibit_family: "om"` for alias keys
  only. The exporter reads both from the seed.
- `program-tier.ts` `deriveExhibitFamily` honours the hint. `copy.ts` already has the
  `om` token.
- The header shows the code as printed.
- Proposed sentence: "The P-1 prints this line's code as O&M; its address uses 0390DOM
  because a web address cannot carry “&”."
- Per Q1 (a) a second sentence points to the restated line: "The
  P-1's Chem Demilitarization - RDT&E line restates R-1 program elements 0708081D and
  0708083D, whose pages carry those dollars." Both links are code-linked.
  *Cross-review:* the search alias is dropped — `search_aliases.csv` requires a `jbook:`
  or `lda:` source ref and a target in `dim_programs`, and none of 0390DOM, 0708081D,
  0708083D qualifies (G2 notes, contract issue 5). The badge reads "O&M" while the term
  beside the code stays "BLI" (it is a P-1 line); the Q5 answer accepts both.
- The `program-skeleton.mjs` census comment ("2 route-unsafe") is updated.

### 4.7 Totals that move (PB2026, USD thousands; site_meta, flow_chart, budget_lines sums)
| Figure | Today | After (Q1 (a), chosen) | Q1 (c), naive (rejected; for comparison) |
|---|---|---|---|
| /programs/ universe (1,714 `fy_2026_total` rows) | 385,268,393 ($385.3B) | 385,271,636 ($385.3B) | 385,481,675 ($385.5B) |
| Flow chart Army node | 43,338,494 | 43,341,737 | 43,551,776 |
| Flow chart A\|0390D | 210,039 | 213,282 | 423,321 |
| Bridge, not yet crosswalked | 227,538,773 ($227.5B) | 227,542,016 ($227.5B) | 227,752,055 ($227.8B) |
| Coverage line | 77.9% | 77.9% | 77.9% |
| 0390D account, FY24A / FY25E / FY26R | 1,002,560 / 754,762 / 210,039 | 1,089,964 / 775,507 / 213,282 (= the P-1's own total) | 2,092,524 / 1,530,269 / 423,321 |

Under Q1 (a) no rendered headline changes, and each derived aggregate keeps its fact-ID
key while its value and inputs change. P1's rule list names each of these.

## 5. decided_on and the other copy, metadata and data fixes

### 5.1 T6: `decided_on`
**Model.** `dbt/models/marts/p1_era_line_map.sql`:
- the decisions CTE (`:108-121`) adds `cast(decided_on as date) as decided_on`;
- `bound` carries it through;
- the final select places it right after `b.ruling`, which is column 14 of 18
  (cross-review: "column 18" counted the total, not the position).

**Schema.** `schema.yml` gets `not_null` and this description: "the date the owner
approved the ruling the decision is recorded under: for R-DEC-ERA-SAME/HISTORY/EXCLUDE
the spec's approval date (2026-10-02), applied by rule rather than row by row; for
R-DEC-ERA-B<n> the date the owner answered the batch, as its answers file records it."
*Finalized 2026-10-13:* the draft ended "the batch's ratify date". `ratify --decided-on`
takes the date from the batch's answers file (`review_batch_page.py`), and B7's answer
(2026-10-04) precedes its ratify, so the description names the answer date.

**Live dates.** Per ruling: 1,128 seed rows dated 2026-10-02, 121 dated 2026-10-03 (B1–B5)
and 4 dated 2026-10-04 (B6). Joined to map keys that is 6,212 / 701 / 14, with no
undecided keys.

**verify-era-map.** `MAP_COLUMNS` (`:88-93`) gains `decided_on`, and leg b's map-vs-seed
tuple (`:308-313`) compares it. This is what proves the published date.

**Tests that pin 17 columns:**
- `test_p1_era_line_map_sql.py:149-157`;
- `test_export_era_line_map.py:21-38`;
- `test_explorer_era_map_preset.py:20-52`;
- `test_verify_era_map.py`, plus a new case where the seed date differs from the map
  date, which must fail as a stale build.

**Export.** The export (`select *`) and leg e (dynamic columns) need no change.

**Measured effect.**
- The parquet grows from 105,305 B to 106,128 B, and /data/ shows "104 KB" instead of
  "103 KB", the same length.
- The dbt count goes from 196 to 197.
- The three "dated decision" claims become true with no copy edit: `export_site.py:1786`,
  `era-map-table.tsx:43` and `methodology/page.tsx:1782`.

**Spec.** §4.4 gets a dated amendment.

**Prerequisite.** This lands with §6.4's regex change, so the map is rebuilt once,
together with §4.4/§4.5.

**Q18** (answered): `decided_on` only; `decided_by` is not published.

### 5.2 T9: F015E0 gloss (with #201)
**Code.**
- `f15_funding_history.py:59`: the note begins "This exhibit [the PB2026 F-15EX AP
  (F015EX) P-40] does not include …": the gloss exactly as Q17 amended it.
- `NOTE_RECEIPTS['e7d5bcfb4a30f458']` gains `pe_bli='F015EX'`, and
  `check_program_notes` checks it.

**New test.** Strip the note's `[…]` glosses with `re.sub(r'\s*\[[^\]]*\]', '', note)`.
The result must equal the verbatim source sentence, and the first gloss must name the
receipt's `pe_bli`.

**Pins that change:**
- `F015E0_NOTE` (`tests/test_f15_funding_history.py:287-292`);
- `NOTE` (`site/src/__tests__/family-funding-history-note.test.tsx:12`).

**Re-pin** (per `tests/fixtures/f15/README.md`):
1. Compute the expected sha hermetically: run `build_history` and `build_program_matrix`
   on `builder_inputs.json.gz`. The only leaf difference allowed is
   `programs[F015E0].note`.
2. On P2's B clone, run `capture_f15_fixtures.py --expect-sha256 <hermetic sha>`. This
   uses the tool after §6.6 has hardened it.
3. Run `f15-page-snapshot`. The note prose is skipped today, so the snapshot changes only
   through #201's new prose capture, re-pinned in the same step.

**Weight** on /families/f-15/: +68 raw / +36 gzip, giving 703,495 / 68,574 against
725,000 / 70,000 (measured by substitution, `t9.mjs`, before Q17 was answered: +68 raw is
the original gloss's 34 B in two rendered copies; the amended gloss is 37 B, about +74
raw, and Task 20 re-measures both figures). The receipt's own verbatim paragraph, the
third occurrence, must not change.

### 5.3 T7: one definition of "tier pending" (strings approved with Q16)
**/methodology/:**
1. Body `:1023-1025`: "figure is from a dataset for which row-level citation linkage is
   not yet complete." → "a figure from a dataset without row-level citations."
2. `:1026-1028`: "defined — and gate-enforced — for" → "defined, and gate-enforced, for".
   Delete `copy-allowlist.json:38-43` in the same commit, because the copy gate fails on
   stale entries.
3. FAQ `:71`: "reserved for datasets without citations (currently p1_era_line_map)." → "a
   dataset without row-level citations (currently p1_era_line_map)." That is 98 B, which
   fits the 102 B pin.
4. FAQ `:56`: "Every rendered number carries a citation to the exact source document,
   page, or API endpoint." → "Every rendered dollar figure carries a citation state; a
   cited one links to the exact source document, page, or API endpoint."
5. `:1013`: "Every rendered figure is in one of three states." → "Every rendered dollar
   figure is in one of three states."
6. FAQ `:71`: "Figures in one of three states:" → "Dollar figures in one of three
   states:".

**/about/ `:169-174`:**
- "Every rendered number" → "Every rendered dollar figure".
- "(dataset where row-level linkage is a work in progress). No number is displayed" →
  "(a dataset without row-level citations). No dollar figure is displayed".

Gate 2 (`render-static.mjs:5-14`) enforces dollar figures, which is what the narrowed
claims now say.

**Test.** Extend `methodology-pending-ledger.test.ts` to check:
- the shared phrase appears in the body, the FAQ and /about/;
- "work in progress", "not yet complete", "reserved for datasets" and "Every rendered
  number" no longer appear.

**Measured** by substitution on the built HTML: /methodology/ −13 gzip / +16 raw, /about/
−13 gzip. Re-measure on the release build.

### 5.4 T11: verify-era-map legs g and h (`src/govbudget/verify_era_map.py`)
**Wiring.** `LEGS` changes from "abcdef" to "abcdefgh", with the matching `cli.py:3349`
default, help text and docstring.

**Leg g, era minters.** It checks every era row in `budget_lines_decade`:
- **same_program rows:** decision `same_program`, a page exists for `program_key`
  (`program_key-<account|org>` for collision codes), and the citation's `pe_bli` equals
  `program_key`. It is `program_key` rather than `line_item_code`, so the alias in §4.5
  stays honest.
- **F-15 rows:** an `ERA_MEMBERS × ERA_PROGRAM_CODES` row whose citation `pe_bli` is null.
- **Workbook citations:** the set of workbook citations under `ERA_P1_WORKBOOK_SHA256`
  equals the set of era decade fact IDs.

Live: 17,502 = 17,481 + 21.

**Leg h, era book diffs.** Resolve each sidecar `book_diff` fid recursively to its
`budget_lines_decade` leaves. It fails if `from_edition ≤ 2023` and any leaf is a P-1 or
P-1R row. Live: 1,044 R-1 era diffs, 0 procurement.

**Tests.** Planted failures, each of which must fail its leg:
- an excluded-line row;
- a history_only row not on the roster;
- a same_program row with no page;
- a P-1 diff from PB2023.

### 5.5 T4
Subsumed. See §3.6 leg j and §3.7. Record the closure in #206's Status line, citing #193.

### 5.6 #195: narrative attribution (second release; Q19 (A))
**Scale.** The defect is systemic. `narr_volume_census.py` ran a 771-second pypdf text
pass over 48 PB2026 PDFs. Of the 5,601 pageless PB2026 narratives:
- 3,504 are printed only in a superseded sibling volume;
- 727 are printed in a different hosted volume;
- 1,367 are printed in no PDF in the corpus (1,342 of those come from the Navy RDTEN
  BA1–3 master XML);
- 3 are printed in their own volume.

Some paged citations point at the wrong exhibit. For example, `033016199ca94aa7` is
cited to Vol I p.71, but its closing words are only on Vol II p.215.

**Cause.** `service_fetch.dedup_service_master_dups` keeps the volume with the lowest
title per master XML. The rest are marked `superseded`.

**Design A (the owner's choice, Q19):**
1. `provenance_pages.build_narrative_provenance` (`:489-575`) searches the volume group
   that shares the master XML, superseded volumes included. It stores
   `printed_document_sha256`, a new column added by the next numbered migration.
2. Export pass 4h (`export_site.py:3455-3489`) takes `sha256`, `hosted_pdf_url`,
   `official_url#page=N` and the page from the printing volume. `fact_id_narrative`
   still hashes the attached volume, so lineage and verify-lineage do not change.
3. Export step 3 (`:3053-3078`) also copies every superseded PDF that a citation now
   names. `deploy.sh` already syncs `data/site/pdfs` to R2: at most 20 PDFs, 162 MB.
4. A full-population check, `verify-jbook-narratives`, run as a leg in
   `verify-phase5b1`, with its own text pass:
   - A paged citation's opening must be on its page, and its last 12 words on pages
     page..page+2.
   - A pageless citation's opening must appear in no volume of its group.
   - The run reports the honest unresolved count, about 1,370.
   - A paged citation whose opening is on its page but whose last 12 words are not is
     kept as `opening_only`. The leg ratchets their count at
     `OPENING_ONLY_CEILING = 111` instead of failing (Q26: 339 of 6,078 paged PB2026
     citations fail the paged rule, and Task 23 relocates 228 of them).

**Weight.** The heaviest program page is `/program/0601102A/`, with 22,519 raw and 5,397
gzip bytes of headroom. It gains about 13.2 KB raw, because each paged record is about
122 B longer and it carries 108 records. Measure before committing. If it does not fit,
stop and ask the owner; never raise the ceiling.

**File separately:**
- whether the 8,021 unresolved detail amounts are the same species;
- acquiring the missing Navy RDTEN books.

**Fallback B** (not chosen: the owner chose A, and Q26 found B's figures do not match the
measurement). Host BA1, override the JLTV fact, and run the check in ratchet mode
(≤ 4,231 in another volume plus 4 on the wrong page). File the systemic fix.

### 5.7 #196: v1 receipt files
**Delete:**
- `export_budget_pdf_receipts` (`budget_pdf_receipts.py:393-472`);
- `load_sources` (`:349-382`) and `tight_glyph_geometry` (`:91-116`), which only it uses;
- the imports that become unused: `hashlib`, `json`, `shutil`, `defaultdict`,
  `c_double`, `openpyxl`, `pdfium`, `pdfplumber` and `Path` (nine, checked with an AST
  scan: the project installs no `ruff`);
- `data-seeds/f15_budget_pdf_sources.json`. It has no reader, and its 20 shas are a
  subset of `budget_pdf_sources.json`'s.

**Export.** `export_program_pdf_receipts` removes top-level
`json/budget-pdf-receipts/[0-9a-f]{2}.json` files and leaves `v2/` alone. It has a pytest.

**Site build.**
- `prepare-assets.mjs:223-227` removes the destination parent, then copies only `v2/`.
- A new `build.mjs` leg checks that `out/json/budget-pdf-receipts` holds exactly `v2/`,
  with 4,096 `[0-9a-f]{3}.json` files.

**Measured effect.** 256 files (419,075 B) leave the deploy. `manifest.json_sidecars`
moves from 36,271 to 36,015 (+2 for the /years/ shards); nothing renders it.

**No R2 step.** `json/` ships only through Vercel: `upload_r2.sh` syncs pdfs, data,
workbooks and citations, and deploy.sh runs `vercel --prod --archive=tgz` from
`site/out`. Earlier deployments, including rollbacks, keep the files, and nothing
fetches them.

### 5.8 #197: search aliases
`data-seeds/search_aliases.csv`:
- Line 3: JASSM → `/program/0207325F/`, ref `jbook:0207325F:ProgramElement[182]/Project[0]`.
- Line 11: C-130J → `/program/0401132F/`, ref `jbook:0401132F:ProgramElement[252]`.

Both carry the #55 note (2026-08-27).

**New test** beside `tests/test_dossiers_research.py:546-583`: every search term whose
alphanumeric key matches a `program_aliases` alias must target a `pe_bli` in that alias's
target set. It checks membership, not equality, because 10 aliases have several targets.
Today it fails on exactly JASSM and C-130J.

**Effect.** Two URLs change in `search_quick.json`. Dossier matching for the two terms
shifts on its next run.

## 6. Hardening (grouped; each item gets a test that is red at HEAD)

**One CLI convention for the tools this wave touches:** `proof`, `link-coverage`,
`verify-era-map` and `review_batch_page`. A tool error prints `<tool>: ERROR — <message>`
and exits 2. A failed check still exits 1. `deploy.sh` and the plan steps test only for
a nonzero exit.

### 6.1 Proof tooling (#199): before any proof in §7
**Snapshot safety.**
- **Hermeticity by resolved path.** Every `read_parquet` path in a rewritten view, and
  every `jbook_documents.file_path`, must resolve under the new root. Today a symlinked
  worktree spelling passes.
- **SAM window.** The check covers the whole copy interval, not only the end minute.
- **Order.** The symlink scan and digests run before `create database`. On any later
  failure, the tool drops only the `govbudget_proof_*` database it created itself.
- **`env.sh`.** The default path is written as a `shlex.quote`d `_proof_dir` and is then
  overridden by `"$1"`. Today `/tmp/a}b`, `/tmp/a$HOME` and `/tmp/a"b` break.
- **Credentials.** The tool refuses a DSN that carries a password.

**Tests to add:**
- the refusals on `.wal`, the writer lock, a missing entry, and after the copy;
- a port-55432 assertion;
- a literal `?host=`.

**Numeric corners.**
- JSON-in-string `parse_float` keeps non-finite values as text (`1e400` ≠ `1e500`).
- `NOISE_FILE_SCHEMA` → 2. The marker goes inside the hashed classes, the file records
  tree digests, and a DIFFERENT control deletes a stale noise file. This invalidates the
  old `.proofs` noise files, so §7's controls run fresh.
- `--noise-from` help mentions `{fid}`.

**Proof scripts.**
- `fact_stability.py` uses a public proof API and type-strict equality.
- The `s4_report` docstring names `decade_absent`.

**Proof notes.** Dated correction notes on `families-s1-proof.md` (the 1e-6 absolute and
1e-12 relative tolerances) and `families-s1b-proof.md` (the code commit was e25945b7,
whose source is identical).

### 6.2 Era-map review tooling (#198): before B7 and T6
**propose.**
- **Rule 4(b).** Extract `_org_grain_clashes` from ratify (`:1595-1613`) and also run it
  in `propose`, so clashing class-ruled chains go to review. The red case is the DISA
  and TJS A1 chains on code `15` in PB2021.
- **No silent overturns.** A class result that differs from a seeded decision goes to
  review (§4.5). The old class row leaves the seed, so B7 can be rendered and ratified;
  until it is, `era-map check --strict` and verify-era-map leg b fail on the undecided
  keys (fail-closed; Q25).
- **UNSAFE** narrows to unaliased (`0390D`, `RDT&E`), and any other unsafe code raises.
- **Atomic writes.** Compute all five outputs, then write each one through a temporary
  file and `os.replace`.
- **`--decided-on`** defaults to `CLASS_RULINGS_DECIDED_ON`.
- **Successor search** prefers the literal form across files.
- **Escaping.** Escape `"` in evidence quotes.
- **Imports.** Move `EraKeyConflict` into `era_keys`.

**ratify.**
- It reads `chains.csv` only when a row names a successor.
- It collects every error per row.
- Add tests for its untested branches.

**Review page.**
- The manifest records `review.csv`'s sha256, and `answer` refuses if the file changed.
- A blank-proposal collision row names its missing pins.
- Bad JSON, `int()` errors and a missing manifest raise `ReviewError` (exit 2).
- Pluralize "era line(s)".
- Reword the own-account reason.

**Build order.** Write it into ratify's success message: one invocation of
`dbt build --select p1_era_code_decisions p1_era_line_map fct_program_decade_series`.
Prove in scratch that a map-only build fails conservation and the single invocation
passes.

**Acceptance:** a scratch `propose` against the live lake reproduces the seed byte for
byte, before the #194 write.

### 6.3 P-1 loader tripwires (#202): before §4.3
- After `sums`, raise `P1KeyConflict(ValueError)` when two groups share an upsert key
  (account, organization, budget activity, pe_bli, **amount_type** — the real
  `budget_lines` upsert key; exhibit and fiscal year are fixed per parse). Measured across
  all 20 workbooks: 0 such collisions. *Cross-review:* the four-part key without
  `amount_type` has 1 live collision (PB2026 `3022F`/`F`/`03`/`SFV000`, two titles on
  disjoint amount columns, nothing lost) and would refuse the PB2026 P-1 workbook and the
  §4.4 re-parse (G4 notes C-34).
- Test a real modern P-1 shape (Budget Line Item plus Add/Non-Add) for `line_item_code ==
  pe_bli`.
- Add the classified-title tripwire test.
- Fix the comment at `p1_loader.py:183-186` ("key matches the DB unique constraint
  grain"; `:195-198` is the accurate S1b comment) and the S1b date at `crosswalk.py:424`.

### 6.4 Era dbt tests and verify-era-map (#203): lands with §5.1
- `assert_p1_era_map_collision_pinned` requires both pins.
- Replace the loose regex `^[0-9]{4}[A-Z]-[A-Z]+-L` with the full one at every site
  (cross-review: ten literal copies — eight dbt files, the exporter's parity check at
  `export_site.py:7252` and one test — not five). Live counts are identical:
  57,722 = 57,722.
- In `era_keys._ERA_KEY_RE`, change `$` to `\Z`. Today `'0300D-DEFW-L1\n'` matches.
- Plant the four unplanted legs: complete × 2, P-1R triple count, and account collision.
- Tests for leg a's classified filter and its failure branches.
- A bad `--legs` value exits 2.
- `ensure_lake_columns` unlinks its temporary file on failure.

### 6.5 Link coverage (#200)
- It fails when the baseline recorded `receipts_match_citations` True and the report has
  None.
- With `--baseline` and `--write-baseline`, it compares first and refuses the same path
  for both.
- A summary card with a value and neither a fid nor an `xml_path` counts as (d). Live
  there are 0 such cards. The 440 cards with an `xml_path` are reported as their own
  count (Q20).
- `json.loads` TypeError and ValueError count as (d).

### 6.6 F-15 tooling (#201): with §5.2
**Direct-run guard.** Use `fs.realpathSync` in:
- `f15-page-snapshot.mjs`;
- `generate-feeds.mjs:203`;
- `run-mobile-leg.mjs:104`;
- `serve-static.mjs:236`;
- `gates/basis.mjs:3385`.

**Snapshot capture.** The snapshot captures the coverage paragraph, the total-row header,
the Partial badges, the matrix note and the notes list. The capture tool rebuilds from
the gzip round-tripped fixture and writes its three files atomically after the check.

**family-history gate.**
- The note ref's href must be `#history-note-<code>`.
- The receipt must have a page, a 64-hex sha and `#page=` in both URLs.

**Other fixes.**
- Add the `aria-label` from Q21.
- `verify.mjs` prints "+N more notes", and `VERIFY_NOTES=all` prints them all.

### 6.7 Fences (#204): after §3
`era_grain_fids` becomes a required keyword-only argument on `_emit_lineage`,
`_emit_json_sidecars` and `_write_all_sidecars`. `_emit_years_matrix` no longer takes
it.
- An `inspect.signature` test asserts that it has no default.
- About 6 test callers are updated.
- Add an invariant assertion at the `build_lineage_flow` call (`export_site.py:13440`):
  no chosen amount fid is in `era_grain_fids`.

### 6.8 Build hygiene (#205): first
- In `site/package-lock.json`, edit only `node_modules/@emnapi/wasi-threads` from 1.2.2
  to 1.2.3 (version, resolved and integrity).
- Proven in scratch: `npm ci` now passes, and it installs today's tree minus
  `@emnapi/runtime`, which the bundle never references.
- Rebuild `site/out` on the same `data/site` and diff `out/_next/static`.
- Re-date the comments at `build.mjs:693` and `:849` to "decided 2026-10-02 at plan
  review: /downloads/" (cross-review: the /downloads/ placement was decided 2026-10-02,
  piece-1 spec §6.4 and ROADMAP line 28; G4 notes C-31).

### 6.9 Not worth doing (close with a dated reason, Q22)
**#198:**
- The successor search for 133 digits-only chains ($20,293,971K, history_only, so no
  page changes; digits look like numbers in prose).
- The dict field in the frozen `Chain` (never hashed).

**#199:**
- `measured_on` masked at any depth.
- Dotted numeric text.
- Two noisy lenient columns (fails safe).
- The 16-hex `{fid}` rule (no live segments).
- A repeatable `--noise-from`.
- Rules 5–8, 17, 33 and 35 (build these when piece 2's proof needs them).

**#203:** a sheet name in `source_cells`. Every era row comes from "Exhibit P-1", and the
change would alter a published dataset.

**#201:** trimming /families/f-15/ now, since 1,426 gzip bytes are left after T9. The
lazy narratives (about 10.7 KB gzip of RSC data) are kept for piece 2.

**#205:** a `package.json` overrides pin, unless the one-entry fix breaks again.

## 7. Verification

| Id | Check | Fails on |
|---|---|---|
| W1 | pytest, vitest, and pyflakes on touched modules (`uvx --offline ruff check --isolated --select F,E9`: the project installs no ruff; no finding beyond the HEAD baseline — `cli.py` 5, `export_site.py` 10) | any red |
| W2 | dbt (one selective build): `assert_budget_lines_route_safe_pe_bli`, `assert_route_safe_codes_valid`, `p1_era_line_map.decided_on not_null`, the hardened era tests, `assert_program_decade_conservation` | any failure |
| W3 | `verify-era-map` legs a–h (b compares `decided_on`) | any FAIL |
| W4 | `npm run verify`, including: yearsmatrix legs a–j and the per-file and core budgets, the new live leg, linkgraph floor 6, program-skeleton, datatruth (s), family-history, copy (allowlist entry removed), build (v2-only leg, page weights re-stamped and never raised) | any FAIL |
| W5 | `verify-phase5b1` (plus the narrative leg in the second release), `verify-phase5e`, `verify-lineage`, `verify-phase5`, `evals check` | any FAIL or BLOCKED |
| W6 | V9 `link-coverage` against the committed baseline | budget figures below 100% linked; a complete receipt lost |

**Proofs run on pinned snapshots** (piece 1 Task 21 pattern, using the hardened tooling of §6.1).

**Snapshots.** Take two snapshots of one live state back to back in one SAM-safe window:
- `fu-pre`, with scratch database `govbudget_proof_fu_pre`;
- `fu-post`, with scratch database `govbudget_proof_fu_post`.

Their at-copy DuckDB, Postgres-dump and parquet-manifest shas must be equal; if they
differ, retake both. *Cross-review:* two `pg_dump --format=custom` archives of one
unchanged database differ (the header records its creation time), so the Postgres pin is
each table's row count and row md5 on the restored dump (`scripts/fu/snapshot_pins.py`,
Task 21), with the DuckDB at-copy sha, every parquet file's sha (minus `sam/`) and the
site and raw_docs tree digests. The lake writes are rehearsed on `fu-post` itself, because its
views point at its own parquet, while clones' views point at the parent:
1. `s194_chem_demil.py --apply` against the scratch database, keeping its pre-image file
   with the proof;
2. `jbooks export-facts`;
3. the B7 ratify, on the committed seed;
4. the single selective dbt build.

**The revert is rehearsed on `fu-pre`** (Q24 (b)), after the A@fu-pre and B@fu-pre
exports, so it disturbs no export and leaves `fu-post` as written:
1. `s194_chem_demil.py --apply` against `govbudget_proof_fu_pre`. Its in-scope rows must
   equal fu-post's, ids included (a second rehearsal of the write), and its pre-image rows
   must equal those of the pre-image the fu-post rehearsal wrote.
2. `s194_chem_demil.py --revert` with that pre-image. Every Postgres pin must then equal
   fu-pre's at-copy pins.
3. A second `--revert` reports "already reverted" and changes nothing.

*Clarified 2026-10-13 (plan review; nothing above reworded):* "fu-pre's at-copy pins"
are the pins of fu-pre's restored scratch database taken before any write (plan Task 21e
Step 1). `snapshot.json`'s `pg.tables` is computed before the snapshot rewrites
`jbook_documents.file_path` to the snapshot's own `raw_docs`, so it differs from any
restored copy on that table alone and cannot be the reference. fu-post, fu-pre and the
live database each run one `--dry-run` before their `--apply` (a dry run spends four
id-sequence values and rolls back), so the three writes insert the same four ids and
"ids included" holds. The abort path's lake half (§8 abort steps 2–3) is rehearsed too,
on a clone of fu-post against fu-pre's reverted database (plan Task 21f Step 6).

**Code under test:**
- **A** is the parent of the wave's first export-affecting commit, in a detached worktree
  with its own `dbt parse` manifest (Task 21 takes `git merge-base main HEAD` and
  proves its `src/`, `dbt/`, `data-seeds/` and `scripts/` equal the deployed 916ae88e).
- **B** is the release HEAD.

*Cross-review re-pairing (2026-10-04, G5 notes contract issue 1):* A cannot export
fu-post — the deployed exporter raises when a `same_program` map row's `line_item_code`
differs from its `program_key` (`export_site.py:7355-7362`), which B7 plus the 0390DOM
alias make true for the 7 O&M era rows. So **P2 (code) = A@fu-pre vs B@fu-pre** and
**P1 (lake) = B@fu-pre vs B@fu-post**; B must therefore export the pre-write warehouse
(17-column map, no `p1_route_safe_codes` table, the 16 stale rows still present), which
it does: the exporter reads the route-safe seed from the CSV and copies the map with
`select *`. The rule files keep the names below; their contents follow the new pairs (the
0390DOM sidecar's `printed_code`/`exhibit_family` land in P1, the Q3 scope string in P2).
The text below is the original pairing, kept for the record.

**Exports.** Four clones and exports: A@fu-pre, B@fu-pre, B@fu-post, and a control
B2@fu-post (originally: A@fu-pre, A@fu-post, B@fu-post, B2@fu-post). Then run
`proof diff B B2 --control --write-noise` (it must read EQUAL), followed by the two
judged diffs below with `--noise-from`.

**P1, lake changes: A@fu-pre vs A@fu-post** (re-paired: B@fu-pre vs B@fu-post), rules in
`docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-lake.json`.
With Q1 (a) and Q3 (B7) the expected differences are:
- **New page:** `data/budget_lines.parquet` (+4 rows, `0390DOM` PB2026);
  `data/budget_lines_decade.parquet` (+0390DOM rows for PB2024–25 and the B7 era rows);
  `program_details/0390DOM.json` (only in B).
- **The map:** `data/p1_era_line_map.parquet` (`decided_on` added as column 14 of 18;
  7 O&M rows' `decision`, `ruling`, `program_key`, `decided_on`); `json/era_map_summary.json`.
- **Citations:** `json/citations.json` and the cite shards gain the new workbook, era
  leaf and `decade_era_map` fids (pointer `/{fid}`, added). The named derived aggregates
  change value and inputs: the universe fact, the flow-chart TOTAL, Army and A|0390D,
  and the bridge's not_yet_crosswalked figure. `citations.parquet` changes to match.
- **Other changed files:**
  - `json/programs_excluded.json`: +1 entry (cross-review: no /years/ row and no
    `search_quick.json` document for 0390DOM, §4.6 as corrected; both files stay
    identical in P1);
  - `json/flow_chart.json`: nodes, edges, bridge;
  - `json/site_meta.json`: counts and `programs_coverage`;
  - `datasets.json`: rows and bytes of `budget_lines`, `budget_lines_decade` and
    `p1_era_line_map`;
  - `manifest.json`: counts;
  - workbook-cell shards and breakdowns;
  - the v2 receipt shards and the audit, only if the matcher finds the O&M rows.
- **Then** run `fact_stability.py`: every A fact is unchanged except the named
  aggregates. Every other path must be identical, equivalent or a control-class reorder.

**P2, code changes: A@fu-post vs B@fu-post** (re-paired: A@fu-pre vs B@fu-pre), rules in `expected-diff-code.json`. The
expected differences are:
- **/years/:** `json/years_matrix.json` changed (schema 2 core); `json/years_matrix/decade.json`
  and `detail.json` only in B.
- **#196:** `json/budget-pdf-receipts/??.json` only in A (256 files);
  `manifest.json /json_sidecars`.
- **#197:** `json/search_quick.json`, two alias URLs.
- **Chem Demil pages:** `program_details/0390DOM.json`, `printed_code` and
  `exhibit_family` added (re-paired: these land in P1, where the page first exists).
- **T9:** `json/f15_funding_history.json`, `/programs/{i}/note` for F015E0 only.
- **Scope string:** `datasets.json`, the `p1_era_line_map` scope (Q3's amendment, §4.5).
- **dbt count:** `json/site_meta.json /build_checks/dbt_assertions`.

`citations.json` must be identical: no fid is added, removed or changed.

**P2b, the /years/ shard proof** (`scripts/fu/years_shard_proof.py`).
1. Merge B's three files.
2. Check `build_id` equality.
3. Check that every A cell is present in B, unchanged.
4. Check that B equals the sidecars: leg j's rule, with 0 mismatches.
5. Check that non-decade cells are identical except on the 7 org-split rows. Report what
   moved on those rows.
6. Report the counts:
   - era cells added (expected 14,985; 0390DOM has no /years/ row, §4.6 as corrected);
   - org-split cells (63 modern + 147 era);
   - every file's bytes and gzip against the caps.

**P3, F-15:** the §5.2 re-pin from B@fu-post (hermetic sha = captured sha), then
`test_f15_era_identity` and `f15-page-snapshot --check`.

**Site-side differences** (not in the data A/B; checked by W4 and reviewed in the build
diff):
- /years/ island and legend;
- /programs/ FY24 and FY26 on the 7 org-split rows;
- /agency/ on the 27 split-key rows;
- `/program/0390DOM/` header and badge;
- /methodology/ (T7, Q13, dbt count);
- /about/ (T7);
- /families/f-15/ (gloss, aria-label);
- /data/ "104 KB";
- llms.txt citation count;
- sitemap 4,349 → 4,350.

## 8. Release

**Release 1** (proofs Task 21, release Task 22) covers §3, §4, §5.1–§5.5, §5.7, §5.8 and
§6. **Release 2** (proof Task 25, release Task 26) covers §5.6, with its own A/B on a fresh
snapshot and its own rule list: narrative citation records, cite shards, program-page
citation records, `pdfs/` and the link-coverage baseline. Its deploy uploads the
superseded volumes the citations now name to R2 through `deploy.sh` (at most 20 PDFs,
162,040,168 B; §5.6), and the owner's go-ahead names that upload and the re-measured
weight of the heaviest program page; its stamp names the 111 `opening_only` citations
(Q26).

Both releases reuse piece 1 Task 23 as amended after the final review (RR-1…RR-6,
INT-1…INT-5). The steps:

1. **Preconditions.** The worktree is clean. pytest is green on the 55432 cluster. The
   live lake still carries the PRE-write state the proof started from (a fresh snapshot
   carries fu-pre's pins, SAM files excepted; Task 22). *Cross-review:* the original
   text here required the post-write state (`0390DOM` rows, `decided_on`, B7) before step
   2's writes, which cannot hold; the post-write state is checked after step 2
   (`lake_parity.py` against fu-post, `era-map check --strict`).
2. **Live writes**, in this order, each outside :12–:22:
   - `s194_chem_demil.py --apply` on live Postgres;
   - `jbooks export-facts`;
   - the single selective dbt build.

   The live `--apply` writes its pre-image to `.proofs/fu-release-s194-pre-image.json`;
   its rows must equal those of the pre-image the rehearsals wrote, and it is the abort
   path's input. Then check that live equals `fu-post` (§4.4). These are this wave's only
   shared-state writes besides the export and the abort path below. Add them, and the
   abort path's writes, to the plan README's shared-write list.
3. **Export.** Keep `.proofs/fu-release-pre-site` (G5: an `fu-` prefix keeps piece 1's
   `tmp/release-*` files out of this release). Export between :21 and :45 with the SAM
   mtime check. Record the counts (`SAM_D` from `companies_with_sam`; the wave's citation
   delta is the remainder) and fingerprint `data/site/{data,citations,manifest.json}`.
   The abort path below restores `.proofs/fu-release-pre-site`.
4. **Release-state checks.**
   - **New:** `proof diff` of B@fu-post/site against the release `data/site`, with the
     noise file. The only expected differences are SAM-registration rules: `json/sam`,
     `entity_details`, the SAM citations and `site_meta` counts. This makes "what ships
     is what was proven" mechanical.
   - The F-15 history matches the new pin.
   - W6 passes.
   - Postgres records 0 worktree paths.
5. **Gates and the site.** W3 and W5. The `llms.txt` commit is built with
   `NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com` (RR-1). Then the build, W4 and
   vitest, after the fingerprint check that opens each of these steps.
6. **Deploy.** `verify-phase5`, then the `deploy.sh --dry-run`. The owner's go-ahead
   names:
   - the moved totals (§4.7);
   - the totals-chart flip (Q15);
   - `SAM_D`.

   Then the fingerprint check and `./scripts/launch/deploy.sh`, by absolute path, from
   this worktree, never from the main checkout, which holds another session's
   uncommitted files.
7. **Live checks, added for this wave:**
   - `/json/years_matrix/decade.json` and `detail.json` return 200 and carry the core's
     `build_id`;
   - `/json/budget-pdf-receipts/00.json` returns 404 while a `v2/` shard returns 200;
   - `/program/0390DOM/` returns 200;
   - the sitemap has 4,350 URLs;
   - `alias:jassm` and `alias:c-130j` URLs are right in `search_quick.json`;
   - a /years/ page load fetches only the core.
8. **ROADMAP stamp.**
   - A ledger row and findings entry.
   - Status lines on #193–#206: CLOSED, or PARTIAL with the §6.9 reasons. Never reword an
     entry.
   - The new entries closed.
   - Q15: the /years/ totals chart's balanced panel grew from 524 to 1,056 programs and
     FY2024A→FY2026R moved from +9.3% to −2.5%; the owner was told on 2026-10-04 and did
     not object.
   - Q23, filed for piece 2: `site/src/lib/aliases.ts` maps B-21 to 0604015F under
     different chip semantics; the family registry becomes the single source.
   - Q4's and Q7's dated notes are already filed (Task 1); the stamp leaves them as
     written.
   - The dated spec amendments (piece-1 spec §4.4 `decided_on`, §5.2 Chem Demil, §6.2
     /years/ fence lifted).
   - #10's SAM count.
9. **Publish.** Fast-forward monorepo `main` and the main checkout. Run
   `git subtree split --prefix=GovBudget` from the toplevel and merge `govbudget/main`
   into the split. Push to `govbudget` main. Never push a worktree branch to `origin`.
10. **Report and cleanup offer.** List the `.proofs/fu-*` directories, the scratch
    databases `govbudget_proof_fu_pre` and `govbudget_proof_fu_post`, and the A worktree.
    Remove them only on a yes.

**Abort path (release 1; Q24 (b)).** If release 1 stops after release step 2's `--apply`
has committed, the live lake must not stay in the wave's state while the main checkout runs
piece-1 code (Q24). Each step runs outside :12–:22:
1. `s194_chem_demil.py --revert --pre-image .proofs/fu-release-s194-pre-image.json`
   restores live Postgres's pre-write rows (§4.4).
2. From the A worktree (piece-1 code, proven equal to the deployed 916ae88e, §7), run
   `jbooks export-facts` and the selective dbt build, so the lake is rebuilt with
   piece-1's seeds and models (no B7 row, no route-safe seed, no `decided_on`). A relation
   that B's build created and A's project does not define is dropped.
3. `lake_parity.py` against fu-pre must pass, SAM files excepted.
4. If release step 3 (the export) has run, restore `data/site` from
   `.proofs/fu-release-pre-site`, keeping the aborted export aside, as piece 1 Task 23 does.

If the stop comes after release step 6's deploy, the owner decides first. On a yes, roll the site
back by LAUNCH.md's rollback procedure (Vercel to the previous deployment, then R2 `data/`
and `citations/` from the rollback copy `deploy.sh` tagged), then run abort steps 1–4.

---

## Appendix A — task outline (final task numbers, 2026-10-13)

The plan (`docs/superpowers/plans/2026-10-04-families-piece1-followups/`) uses exactly these
numbers. A group may split a task too big for one reviewer gate into lettered parts (21a,
21b, …); a dependency on a split task means all of its parts. The plan group (G1–G6) says
which drafter writes the task. "Depends on" is derived from the 2026-10-04 table, with the
old numbers mapped to these (1–7 unchanged; 6b → 8; 8 → 9; 9 → 10; 10 → 11; 11 → 12;
12–19 → 13–20; 20 → 21; 21 → 22; 22 → 23; 23 → 24; 24 → 25 and 26) and one addition (¹).

| # | Task | Spec § | Plan group | Depends on |
|---|---|---|---|---|
| 1 | Worktree and lockfile (#205); also files new ledger entries #207 (org-split rows) and #208 (/agency/ lookup), and the Q7 dated corrections on #194 and piece-1 spec §5.2 (with Q4's note) | 6.8, 3.5, 2.2 (Q4, Q7) | G4 | — |
| 2 | Proof tooling hardening (#199) | 6.1 | G4 | 1 |
| 3 | P-1 loader tripwires (#202) | 6.3 | G4 | 1 |
| 4 | Era-map guards (#198) | 6.2 | G4 | 1 |
| 5 | link-coverage fails closed (#200) | 6.5 | G4 | 1 |
| 6 | Route-safe seed and loader alias + R-1 restatement rule (#194) | 4.2, 4.3 | G2 | 3 |
| 7 | Chem Demil write script `s194_chem_demil.py` (`--check`/`--dry-run`/`--apply`/`--revert`) + retire `clean_junk_pe_bli.py` (#194, Q8, Q9, Q24 (b)) | 4.4 | G2 | 6 |
| 8 | Map alias: `p1_era_line_map.program_key` from the route-safe seed, `era_map` alias/classify, UNSAFE narrowed to (0390D, RDT&E) | 4.5, 6.2 | G2 | 4, 6 |
| 9 | Map code changes: `decided_on` column, strict era-key regex, both collision pins, leg b (#206 T6, #203) | 5.1, 6.4 | G3 | 4, 6, 8 ¹ |
| 10 | Owner batch B7 (era O&M chain → `0390DOM`; owner already answered) | 4.5 | G2 | 8, 9 |
| 11 | verify-era-map legs g (era minters) and h (era book diffs) (#206 T11) | 5.4 | G3 | 9 |
| 12 | O&M page presentation (`printed_code`, badge, scope amendment, receipt matcher accepts the alias) (#194, Q5, Q6) | 4.5, 4.6, 2.3 | G2 | 6 |
| 13 | /years/ exporter: split, compact writer, budgets, fence lift, org-split fix (#193, #207) | 3.3, 3.5 | G1 | 2 |
| 14 | /years/ island: lazy shards, tooltip revert, legend, /agency/ slug lookup (#193, #208, Q12–Q14) | 3.4, 3.5, 3.7 | G1 | 13 |
| 15 | /years/ gates: merged-view legs, leg g via the map, parity leg, live probes, methodology clause swap Q13, spec §6.2 amendment (#193, #206 T4) | 3.6, 3.7, 5.5 | G1 | 13, 14 |
| 16 | Required `era_grain_fids` + `build_lineage_flow` invariant (#204) | 6.7 | G4 | 13 |
| 17 | v1 receipt removal (#196) | 5.7 | G3 | 1 |
| 18 | Search aliases JASSM/C-130J + cross-seed test (#197) | 5.8 | G3 | 1 |
| 19 | T7 tier-pending copy (Q16) | 5.3 | G3 | 1 |
| 20 | F-15 tooling and the F015E0 gloss (amended string) + aria-label (#201, #206 T9, Q17, Q21) | 5.2, 6.6 | G3 | 1 |
| 21 | Release-1 proofs: snapshots fu-pre/fu-post, rehearsed Chem Demil write AND its `--revert`, B7/map/program-table builds on the snapshot, A/B/B2 exports + noise, P1/P2/P2b/P3, F-15 re-pin, weights, proof note (split into 21a…) | 7, 4.4 | G5 | 2, 5, 7, 10, 11, 12, 15–20 |
| 22 | ★ Release 1: live writes (`s194 --apply`, B7 builds in order map → program table → map), export, gates, deploy, live checks, ROADMAP stamp (incl. Q15), publish; abort path uses `--revert` (split into 22a…) | 8 | G5 | 21 |
| 23 | #195 provenance across the master-XML volume group (migration, export, hosting of superseded volumes) | 5.6 | G6 | 22 |
| 24 | #195 printed-in check (verify-phase5b1 narrative leg, the 111 `opening_only` ratchet, Q26) | 5.6 | G6 | 23 |
| 25 | Release-2 proof | 7, 8 | G6 | 24 |
| 26 | ★ Release 2 (deploy with R2 upload of the new volumes, live checks, stamp, publish; owner go-aheads) | 8 | G6 | 25 |

¹ Added 2026-10-13: Tasks 8 and 9 both edit `dbt/models/marts/p1_era_line_map.sql`, and the
final numbering puts the alias first.

★ marks an owner go-ahead still to come. Every design question was answered on 2026-10-04
(§2), B7's included: Task 10 records that answer and does not ask again.

Task 22's title gives the B7 build order as the controller wrote it (map → program table →
map). §6.2 sets the rule that order must meet (a map-only build fails conservation; Task 4
proves in scratch which build passes), and Task 21 rehearses on the snapshot exactly the
sequence Task 22 runs on the live lake.

*Drafts (2026-10-04):* the group drafts were lost with the scratchpad. Two cross-review
rulings carry over: the P2b tool (`scripts/fu/years_shard_proof.py`) and the F-15 re-pin
belong to Task 21 only, so Tasks 15 and 20 do not create them.

The research's order still holds: T6 and the map code first, then #194's write and B7, then
/years/, so that the /years/ proof measures final content. Tasks 3, 4, 5, 17, 18, 19 and 20
are independent of one another.
