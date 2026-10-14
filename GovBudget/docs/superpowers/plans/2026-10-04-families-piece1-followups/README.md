# Families Piece 1 Follow-ups (#193–#208) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each executor reads this README (Global Constraints, Binding Cross-Task Decisions, and the Contract Notes of its own group) plus its own file under `tasks/`. Where a task file and a Binding Cross-Task Decision disagree, the decision wins, and the Open Items list names the task text that has to change.

**Goal:** Clear the piece-1 follow-ups #193–#206, plus the two adjacent defects #207 and #208, before piece 2. This happens in two releases, and no published fact ID changes except the derived aggregates the proof's rule lists name.
- **Release 1** ships five changes. /years/ shows PB2017–PB2023 procurement from a sharded payload. The 0390D Chem Demil O&M line gets the page `/program/0390DOM/`, through a write that `--revert` can undo. `p1_era_line_map` publishes `decided_on`. The era-map, proof, loader and link-coverage tools are hardened. The copy, alias and F-15 fixes land.
- **Release 2** re-points the narrative citations to the volume that prints them (#195).

**Architecture:**

*Release 1 (Tasks 1–22):*
- **Hardening first.** The hardening tasks land first (#205, #199, #202, #198, #200), each with a test.
- **One route-safe seed.** A seed (`dbt/seeds/p1_route_safe_codes.csv`, read in Python only through `jbooks/route_safe_codes.py`) gives the P-1 code `O&M` of account 0390D the page key `0390DOM`. The loader, the era map and the exporter all use that seed. The RDT&E line restates R-1 PEs 0708081D + 0708083D, so it is checked against them and loaded nowhere (Q1 (a)).
- **The Chem Demil write.** `scripts/era/s194_chem_demil.py` re-keys 8 rows, deletes 8 and inserts 4 in one locked transaction. It writes a revert file before COMMIT. Owner batch B7 joins the era O&M chain to the page.
- **/years/.** The core keeps its name, `json/years_matrix.json`, at schema 2: the header, every row and the 12 default decade columns. Two lazy shards, `json/years_matrix/decade.json` and `detail.json`, carry the rest. A compact writer measures its own bytes, the era fence is lifted, and a sidecar-parity leg proves every cell equals its program page.
- **Proof.** Everything is proven on pinned snapshots fu-pre/fu-post: P2 (code) = A@fu-pre vs B@fu-pre, P1 (lake) = B@fu-pre vs B@fu-post, P2b (/years/ shards) and P3 (F-15). After that come the live writes, one selective dbt build and the deploy.

*Release 2 (Tasks 23–26):*
- **Relocation.** Each narrative citation is matched to the volume of its edition's book set that prints it (migration 022, `provenance_pages.printed_document_sha256`). The relocation is written once by `scripts/fu/s195_narratives.py` (pre-image, `--revert`).
- **Export.** The export cites and hosts the printing volume (at most 20 superseded PB2026 volumes on R2), and every fact ID stays the same.
- **Check.** verify-phase5b1 gains the printed-in check, with the owner-approved `opening_only` ratchet of 111.

**Tech Stack:** Python 3.12 (uv; psycopg 3, openpyxl, pypdf, pdfplumber/pypdfium2, DuckDB 1.5), dbt-duckdb, PostgreSQL 17 (local server plus the throwaway test cluster on 127.0.0.1:55432), Next.js 16 / React 19 / vitest, the site gate registry (`npm run verify`), `scripts/launch/deploy.sh` (R2, then Vercel, then live checks), launchd-free shell steps.

**Spec:** [`docs/superpowers/specs/2026-10-04-families-piece1-followups-design.md`](../../specs/2026-10-04-families-piece1-followups-design.md) (approved 2026-10-04; owner answers in its §2, ROADMAP commits 53dff043 and 532205c9; recovered verbatim and finalized 2026-10-13; Appendix A fixes the task numbers used here). Parents: piece 1's [`2026-10-02-era-procurement-history-design.md`](../../specs/2026-10-02-era-procurement-history-design.md) and plan [`2026-10-02-era-procurement-history/`](../2026-10-02-era-procurement-history/README.md) (format model; its Task 21 and Task 23 as amended 2026-10-04 are the proof and release models).

## Global Constraints

### Workspace

- **Worktree.** The git toplevel is `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families`, on branch `followups-2026-10-04` (main `7dccd983` plus `53dff043` and `532205c9`). The project is its `GovBudget/` subdirectory, and every path in this plan is relative to it. Run commands from `GovBudget/` unless a step says otherwise.
- **Commits.**
  - Use `--author="Andes Lee <andes.lee444@gmail.com>"`, and end the message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - Commit from the toplevel with explicit pathspecs (`git add GovBudget/<path>`).
  - Never `git stash`: the stack is shared with other sessions.
  - Never push the branch to `origin`. Only Tasks 22e and 26b publish, each after the owner's go-ahead. They fast-forward monorepo `main` and the main checkout, then run `git subtree split --prefix=GovBudget` from the toplevel, merge `govbudget/main` into the split and push to `govbudget` `main`.
  - The untracked `GovBudget/data/research/eval-runs/eval-20261004T203052Z.json` is not this wave's file: never commit or delete it. The "worktree is clean" checks (Tasks 21d, 22a) ignore untracked `??` files.
- **Python** runs as `uv run --project . <cmd>` from `GovBudget/`. **Site** commands are `npm` in `GovBudget/site`. `site/node_modules` must be a real directory, never a symlink; Task 1's lockfile fix makes `npm ci` pass again. W1's lint is `uvx --offline ruff check --isolated --select F,E9` (the project installs no ruff), and it must find nothing beyond the HEAD baselines: `cli.py` 5, `export_site.py` 10, `verify_phase5b1.py` 2, `verify_phase5.py` 2, `budget_pdf_receipts.py` 1 (re-measured 2026-10-13), every other touched module 0.
- **Environment.** `source scripts/era/env.sh` exports:
  - `GOVBUDGET_DATA` and `GOVBUDGET_DUCKDB` (the live lake under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data`);
  - `GOVBUDGET_PG_DSN=postgresql://localhost/govbudget`;
  - `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres`;
  - `GOVBUDGET_PG_BIN`;
  - `GOVBUDGET_PROOFS=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs` (git-ignored).

  `config.py` ignores `GOVBUDGET_DUCKDB` and derives the DuckDB path from `GOVBUDGET_DATA`. dbt and `govbudget build` read `GOVBUDGET_DUCKDB`, so set both. A snapshot is used through its own `source <snapshot>/env.sh [RUN_DIR]`.
- **Shell state does not persist between tool calls.**
  - **Block start.** Each command block, and each inline `Run:` command, starts with `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh`. Multi-line blocks end that line with `|| exit 1`.
  - **Re-derive values.** Any value a step "sets once" is set again inside every block that uses it: `P`, `L`, `PRE_DSN`, `POST_DSN`, `SNAP`, `D1`, and the git refs of Tasks 21d, 22 and 26.
  - **Test DSN.** Every pytest call that can reach Postgres carries `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres` inline.
  - **Destructive cleanups** expand variables as `${VAR:?}`.
  - **Exempt blocks.** Commit blocks are exempt. So are blocks that source a snapshot's or the A worktree's own `env.sh`, and the toplevel git and `deploy.sh` blocks, which use absolute paths and only variables they set themselves.
- **Tests never touch the real database.**
  - Postgres-backed tests use the throwaway cluster on 127.0.0.1:55432. Its scratch databases (`govbudget_test`, Task 7's `s194_rehearsal`) are fine.
  - Every session in this worktree shares that one cluster. Run one task's pytest steps at a time. A Postgres-only failure gets one re-run on a quiet cluster before it counts as red (G4-11).

### Known red windows (expected, and nothing else may be red)

- **F-15 window (G3-C1).** From Task 20a/20c until Tasks 21g/21h re-pin, exactly four tests fail:
  - `tests/test_f15_era_identity.py::{test_golden_rebuild_from_fixtures_is_byte_identical, test_fresh_state_with_decade_era_map_receipts_keeps_every_byte, test_allowed_formula_competitor_changes_exactly_one_cell}`;
  - the vitest "committed baseline … is present, well-formed and of this schema".
- **Gate 20 window (G1-2).** From Task 15 on, `npm run verify` fails gate 20 on a pre-split (schema 1) `years_matrix.json`. The live `data/site` holds one until Task 22c's export. Run the full verify only on Task 21h's B@fu-post build and Task 22d's release build. Site builds between Tasks 14 and 22 still work, because merge, the island and `prepare-assets.mjs` tolerate a schema-1 core.
- **Seed-ahead-of-warehouse window (Task 10 → Task 22b).**
  - `era-map check --strict` fails between Task 10's `propose` and its `ratify`.
  - From the ratify on, verify-era-map leg b reports `O&M|0390D||2017-2023` as a stale build.
  - `assert_budget_lines_route_safe_pe_bli` fails on the live lake until Task 22b's write and build. The 16 stale rows are in `data/parquet/jbooks/budget_lines.parquet` today.
  - No live dbt build happens in this window. Task 10 must not run one, because a build between `propose` and `ratify` fails `assert_p1_era_map_no_undecided` and the `decided_on` `not_null`: fail-closed, as Q25 accepts (G3-C8).

### Shared state

**Shared-state writes** happen only in the places listed below. Each runs outside :12–:22, from this worktree by absolute path, and only after a proof on a snapshot has rehearsed it.

| Task | Write | Abort / undo |
|---|---|---|
| 7 | None live. The rehearsal uses `s194_rehearsal` on the 55432 cluster and `$GOVBUDGET_PROOFS/fu-s194-rehearsal/`, both removed at the end of Step 6. | — |
| 10 | None live. It commits the B7 seed row and the research files. `tmp/era-review/B7.{html,json}` is git-ignored. No dbt build. | — |
| 21d–21h | Scratch only. Snapshots `fu-pre` and `fu-post` (databases `govbudget_proof_fu_pre`, `govbudget_proof_fu_post`) and their clones. On fu-post (Task 21e): `s194_chem_demil.py --dry-run`, then `--apply --revert-file`, `jbooks export-facts` and the single selective dbt build. On fu-pre, after its two exports (Task 21f Steps 4–5): the `--dry-run`/`--apply`/`--revert`/`--revert` rehearsal (decision 2). On `.proofs/fu-abort`, a clone of fu-post (Task 21f Step 6, removed there): abort step A2 rehearsed. | — |
| 22a | Snapshot `fu-rel` (`govbudget_proof_fu_rel`). The copy of production's export at `.proofs/fu-release-pre-site`. | — |
| 22b ★ | Live Postgres: `s194_chem_demil.py --dry-run`, then `--apply --revert-file "$GOVBUDGET_PROOFS/fu-release-s194-pre-image.json"`. Live lake: `jbooks export-facts`, then one `dbt build --select p1_route_safe_codes p1_era_code_decisions stg_budget_lines+`. | A1: `s194_chem_demil.py --revert --revert-file <same file>`. A2: from the A worktree (`.claude/worktrees/families-fu-a`, the deployed code), `jbooks export-facts` and `dbt build --select p1_era_code_decisions stg_budget_lines+`, then `drop table main.p1_route_safe_codes` (spec §8 abort step 2), then `lake_parity.py` against fu-pre. A3: restore `data/site` from `.proofs/fu-release-pre-site`. After a deploy: the owner first, then LAUNCH.md's rollback, then A1–A3 (Tasks 22b, 22d). |
| 22c | The release export of the live `data/site`, between :21 and :45, with the SAM mtime check, fingerprinted. | A3 |
| 22d ★ | `deploy.sh`: R2 `pdfs`, `data`, `workbooks`, `citations`, then Vercel. The `site/public/llms.txt` commit. | LAUNCH.md rollback, owner first, then Task 22b's A1–A3 |
| 22e ★ | The main checkout: `git merge --ff-only origin/main` and `dbt parse` (Step 8), after the publish go-ahead. The ROADMAP stamp commit. | Minute guard :25–:10; on a refused fast-forward, stop and report |
| 25b, 25c | Scratch only. Snapshot `fu2` (`govbudget_proof_fu2`). On it: `migrate` (022), `jbooks narrative-provenance --lineage-evidence`, `s195_narratives.py --apply` and `--revert`. Clones `fu2-*`. | — |
| 26a ★ | After the owner's go-ahead (Step 2b), live Postgres: `migrate` (022), `jbooks narrative-provenance --lineage-evidence` (19 inserts), `s195_narratives.py --apply --pre-image "$GOVBUDGET_PROOFS/fu2-release-s195-pre-image.json"`. The release export of `data/site`. No lake parquet, DuckDB table or dbt model changes in release 2. | `s195_narratives.py --revert --pre-image <same file>`. Restore `data/site` from `.proofs/fu2-release-pre-site`. |
| 26b ★ | `deploy.sh` with the R2 upload of the superseded volumes (at most 20 PDFs, 162,040,168 B). After the publish go-ahead (Step 7): the main checkout's `git merge --ff-only origin/main`. | LAUNCH.md rollback, owner first, then Task 26a's abort path; the fast-forward: minute guard :25–:10, stop on a refusal |

- **Scratch proof databases.** They are named `govbudget_proof_<name>`: here `fu_pre`, `fu_post`, `fu_rel` and `fu2`. Only `govbudget proof snapshot` creates them on `postgresql://localhost`. That tool refuses any other name and any DSN that carries a password, and on failure drops only the database it created. Never create, alter or drop any other database on the local server.
- **The SAM window.** The hourly SAM launchd job writes `data/parquet/sam` at :17.
  - **What it covers.** Start no step that reads or writes the live lake during minutes :15–:20 past the hour. That includes read-only steps: DuckDB `read_only`, parquet reads, `verify-*` runs on the live warehouse, snapshots, live `export-site`, live `jbooks export-facts` and live dbt builds. Steps that guard with margin use :12–:22. Check `date +%M` first, and start only if the step will finish before the next :15.
  - **The guard line.** Such blocks carry `MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi` right after their `cd … && source scripts/era/env.sh` line. If a block prints `WAIT: …`, wait until :23 and re-run the whole block.
  - **Release exports** run between :21 and :45 with the SAM mtime check.
  - **Exempt.** Exports and dbt runs against a snapshot or its clone, and `dbt parse`.
  - **SAM state today.** The job has finished: `state.json` says all 200 published families have a stored SAM answer. The lake holds 164 SAM entities against 149 published, so release 1's export carries about 15 new registrations (`SAM_D`) that the proof exports also read (G5-6).
- **Site builds in the worktree** read `GovBudget/data/site` through the `data/*` symlinks, which the shared `.git/info/exclude` excludes. The build also needs this worktree's own `dbt/target/manifest.json` (Task 1 runs `dbt parse`). Tasks 21h, 22 and 26 repoint the links at the snapshot or lake they build against, and put them back.

### Product rules

- **Ceilings and prose.**
  - Never raise a page-weight ceiling, the /years/ 4 MiB per-file cap (`_YEARS_MATRIX_MAX_BYTES`) or the new core budget (`_YEARS_MATRIX_CORE_GZIP_MAX = 780,074` gzip bytes; it tightens).
  - Never trim existing disclosure prose without the owner.
  - If /methodology/ does not fit, drop Q13's clause swap; never raise the ceiling (spec §3.7).
  - If `/program/0601102A/` does not fit in release 2, stop and ask the owner (spec §5.6).
  - A ratchet may hold only a count the owner approved. `OPENING_ONLY_CEILING = 111` is approved (Q26); `PAGELESS_OPENING_SEEN_CEILING = 77` needs the owner's yes at Task 24 Step 0, before any of Task 24 is written.
- **Never re-key `pe_bli`.** Era keys stay the lake and fact identity. The one exception is Q8: `s194_chem_demil.py` re-keys the 8 modern 0390D O&M rows to `0390DOM` in place, keeping their ids.
- **Era keys.**
  - Select them with `era_keys.is_era_procurement_key(pe_bli)` in Python, or the full regex `'^[0-9]{4}[A-Z]-[A-Z]+-L[0-9][0-9A-Za-z-]*$'` in SQL.
  - Never use the prefix-only `^[0-9]{4}[A-Z]-[A-Z]+-L`: Task 9b replaces it at its ten sites. `tests/test_era_key_regex_sites.py` lists every site, so add a new site there.
  - Never select "every PB2017–23 P-1 row": era editions also hold `9999999999` classified rows.
  - After Task 9b, `_ERA_KEY_RE` ends in `\Z`, not `$`.
- **Lake and code hazards.**
  - (a) From Task 22b Step 3 until Task 22e publishes, the main checkout runs piece-1 code. Its `export-site` raises on the B7 map row, and its `govbudget build` would rebuild the map without `decided_on` and B7. Run nothing from the main checkout in that window, keep the window short, and otherwise take the abort path.
  - (b) The same holds from Task 26a Step 3 until Task 26b publishes: an old-code export would cite the attached book, not the printing volume.
  - (c) Every other worktree whose `data/*` links point at the live lake rewrites the shared `data/site` if it runs `export-site`. The release tasks therefore fingerprint their export and re-check it before deploying (piece-1 INT-4).
  - (d) Deploy only from this worktree, by absolute path. The main checkout holds another session's uncommitted files.
- **Never `/private/tmp`.** macOS cleared `/private/tmp` between 2026-10-04 and 2026-10-13, and with it the first design scratch and drafts. Keep:
  - proof state and proof logs under `$GOVBUDGET_PROOFS`: release 1's `fu-*` and `fu-logs/`, release 2's `fu2*` and `fu2-logs/`;
  - controller notes, review notes and drafting scratch in the worktree's ledger, `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/2026-10-04-piece1-followups/` (`progress.md`, `work/`);
  - transient files a task names under the git-ignored `GovBudget/tmp/` (release 2 writes its release logs there).

  Before any cleanup of proof state, Tasks 22e Step 12 and 26b Step 8 copy `fu-logs/`, `fu2-logs/`, the live pre-images and release 2's `tmp/fu2-release-*` into the ledger's `proof-logs/`, so the proof notes' bracketed log names stay readable.

  `mktemp` is used only for a step's own throwaway demo that the step removes (Task 20b Step 1).

### Ledger conventions

- **Dates in ledger text (G4-8).** A finding or owner answer keeps its own date, 2026-10-04. A figure re-read for this plan says "re-measured 2026-10-13". A Status stamp, deploy, rollback tag or proof note carries the day its step runs.
- **ROADMAP Status stamps (G5-13).**
  - Never reword an entry. Add the new marker above, then `*(Earlier marker below.)*`, and relabel the old line `**Status (<its date>):**`, as #191 does.
  - `tests/test_roadmap_backlog.py` changes in the same commit as the stamp.
  - #198 closes PARTIAL. It names the items that neither §6.2 nor §6.9 covers: "titles containing ' | ' read as drift", and the three test gaps "None in a present key, a multi-page collision chain, per-edition R3" (G4-4, G5-11). The two other gaps #198 lists ("a mere mention is not a successor", "the lake is opened read-only") are pinned by Task 4a's `tests/jbooks/test_era_map_198_gaps.py`. Task 22e Step 6 tells the owner the four stay open and offers to close them with a dated reason instead.

## Owner Decisions Already Made (do not re-ask)

| Date | Decision | Where recorded |
|---|---|---|
| 2026-10-04 | Before piece 2, clear #193–#206. Shard `/years/` and lift its era fence so it shows PB2017–PB2023 procurement (#193). | ROADMAP "Follow-ups first (owner, 2026-10-04)" (commit 53dff043); spec §2.1 |
| 2026-10-04 | Load the 0390D Chem Demil lines under route-safe codes with pages (#194). *Superseded later that day:* only the O&M line gets a page (`0390DOM`). | same; amended by 532205c9 |
| 2026-10-04 | Remove the unread v1 PDF receipt files from the deploy (#196). | same (53dff043) |
| 2026-10-04 | Publish each era decision's date in `p1_era_line_map` as `decided_on` (#206 T6); `decided_on` only, not `decided_by` (Q18). | same; spec §5.1, Q18 |
| 2026-10-04 | F015E0 gloss (#206 T9). *Amended later that day* to exactly "[the PB2026 F-15EX AP (F015EX) P-40]" (Q17). | ROADMAP (53dff043, amended by 532205c9); spec §5.2, Q17 |
| 2026-10-04, later | **Q1 (a):** the RDT&E line gets no page. It is recorded as an R-1 restatement of 0708081D + 0708083D (`P1_R1_RESTATEMENTS`). | ROADMAP (532205c9); spec §2.2 Q1, §4.3 |
| 2026-10-04, later | **Q2:** the key is `0390DOM` only. There is no `0390DRDTE`. | spec Q2 |
| 2026-10-04, later | **Q3:** the era O&M chain joins `0390DOM` as owner batch B7. The answer was given in chat as "Join it (Recommended)", with `decided_on` 2026-10-04. | ROADMAP (532205c9); spec §2.1, §4.5; `data/research/era_map/batches/B7.json` `owner_reply` (Task 10) |
| 2026-10-04, later | **Q19 (A):** #195 gets the full re-attribution fix as a second release. **Q26:** the 111 `opening_only` citations are held by a ratchet, named in release 2's stamp. | ROADMAP (532205c9); spec §5.6, Q19, Q26 |
| 2026-10-04, later | **Q24 (b):** `s194_chem_demil.py --revert` restores the exact pre-write rows, with its own test and rehearsal; release 1's abort path uses it. | ROADMAP (532205c9); spec §4.4, §8 |
| 2026-10-04, later | **Q15:** the /years/ totals chart's balanced panel grows (524 → 1,056 programs as told) and FY2024A→FY2026R flips (+9.3% → about −2.5%). The owner was told and did not object; release 1's stamp records it, with the measured figures (decision 10). | spec Q15, §8 step 8 |
| 2026-10-04, later | Every other recommendation stands: Q4 (the RDT&E era chain keeps `exclude_route_unsafe`, with a dated note), Q5–Q14, Q16, Q18, Q20–Q23 and Q25 (a re-ruled chain's seed row leaves the seed until the owner ratifies; fail-closed). | ROADMAP (532205c9); spec §2.2–§2.3 |
| 2026-10-02 / earlier | Still binding: R-DEC-ERA-SAME / -HISTORY / -EXCLUDE with batches B1–B6. Publish the smaller true number (2026-08-07). The era table on /downloads/ shows counts only. `p1_era_line_map` reads "tier pending" on /data/. | piece-1 spec and README; ROADMAP |

**Still needs the owner during execution (★):**
- **Task 22b Step 2:** a go-ahead before the live Postgres write. The plan adds this one (G5-7); §8 has none here.
- **Task 22d Step 5:** the deploy go-ahead. It names the moved totals (§4.7), Q15 (told 524 → 1,056 and +9.3% → about −2.5%; the measured figures from `p2b-report.json`, 1,063 and −2.61% in the 2026-10-13 simulation) and `SAM_D`.
- **After a release-1 deploy, on any failure:** the owner decides whether to roll back; on a yes, LAUNCH.md's rollback, then Task 22b's abort path A1–A3 (Tasks 22b, 22d; spec §8).
- **Task 22e Step 6:** the go-ahead to publish. It also tells the owner that #198 stays PARTIAL on four items and that Q23 is filed for piece 2.
- **Task 24 Step 0:** the second ratchet `PAGELESS_OPENING_SEEN_CEILING = 77` (G6-2), before any file of Task 24 is written. On a no, Tasks 23a–26b are amended to the owner's rule first.
- **Task 26a Step 2b:** a go-ahead before release 2's live Postgres writes (migration 022, the 19 lineage-evidence rows, the 4,386-row relocation), naming what its abort path cannot undo.
- **Task 26b Steps 3 and 7:** the deploy go-ahead (the R2 upload of the superseded volumes, the re-measured weight of `/program/0601102A/`, the 111 and the 77), then the publish go-ahead.
- **On a yes only:** cleanup of `.proofs/fu-*` and `.proofs/fu2*`, the scratch databases and the A worktrees `families-fu-a` and `fu2-proof-a` (Tasks 22e and 26b, each after copying its logs into the worktree ledger), and removal of an aborted `data/site.*` copy.

## Binding Cross-Task Decisions

These came out of the 2026-10-13 drafting and the notes of the six drafting groups. They override a task file's wording where the two differ. Open Items lists the task text that must follow them.

### Release-1 writes and builds

1. **The s194 CLI is Task 7's.**
   - **Modes.** `scripts/era/s194_chem_demil.py` takes exactly one of `--check`, `--dry-run`, `--apply`, `--revert`. `--dry-run` is its own mode: it runs `--apply`'s transaction and checks, rolls back, and needs no file. `--apply` requires `--revert-file PATH` and refuses an existing file. `--revert` requires `--revert-file PATH`, the file `--apply` wrote. `--dsn` defaults to `config.PG_DSN`; `--editions` defaults to 2024 2025 2026.
   - **Exit codes.** 0; 1 for a difference, a refusal or a rollback; 2 for usage.
   - **The revert file is the spec's pre-image.** Spec §4.4 and §8 call it the pre-image (`--pre-image`). It holds:
     - `database`;
     - `before` (the 16 pre-write rows, every column);
     - `rekeyed`, `deleted_ids` and `inserted`;
     - `untouched_digest`;
     - `rows_sha256`, the sha256 of the record's other fields as canonical JSON (spec §4.4's "the rows' sha256").

     It is written atomically inside the transaction, before COMMIT. Before it opens the database, `--revert` refuses a file whose `rows_sha256` does not match its contents, or whose `before` rows are not #194's (a re-keyed alias row or a deleted restatement, `out_of_scope`); spec §4.4's three refusal tests (a changed in-scope row, a mismatched sha256, another database) are Task 7's. Release 1's live file is `$GOVBUDGET_PROOFS/fu-release-s194-pre-image.json` (spec §8 step 2).
   - **Printed lines to match.** These are the ones Task 7's Interfaces list:
     - `check: CLEAN, the only differences are #194's (re-key 8, insert 4, delete 8)`;
     - `apply: re-keyed 8, deleted 8, inserted 4; untouched rows <n> (digest equal); route-unsafe pe_bli left 0`;
     - `apply: COMMITTED (revert file <path>)`;
     - `revert: restored 16 pre-write row(s) (re-keyed 8 back, re-inserted 8, removed 4); COMMITTED`;
     - `revert: the database already holds the pre-write rows; nothing to revert`;
     - `revert: the database moved since --apply (<n> problem(s)); nothing written`;
     - `revert: <file> sha256 does not match its contents; nothing written`;
     - `revert: <file> names <n> row(s) outside #194's scope; nothing written`;
     - `s194: REFUSED — <ExceptionName>: <message>`.
   - **Superseded forms.** The forms `--apply --dry-run`, `--apply` without a file, `--revert --pre-dsn DSN` and `revert: COMMITTED` do not exist. Tasks 21d, 21e, 21f, 21i, 22a, 22b and 22e were drafted against them (G5-1) and were brought to this decision at the 2026-10-13 review (O-1).
2. **Where the write and its revert are rehearsed (spec §4.4, §7).** Every sequence below is one `--dry-run` (it spends four id-sequence values and rolls back), then one `--apply`, so all three writes draw the same four PB2026 ids.
   - **fu-post (Task 21e Steps 2–3).** It gets exactly one `--apply`, with its revert file kept as `$GOVBUDGET_PROOFS/fu-logs/s194-fu-post-revert.json`. Then come `jbooks export-facts` and decision 3's build, all before Task 21f's B@fu-post exports.
   - **fu-pre (Task 21f Steps 4–5).** The revert is rehearsed on fu-pre after Task 21f has exported A@fu-pre and B@fu-pre:
     1. `--dry-run`, then `--apply --revert-file …/s194-fu-pre-revert.json` on `govbudget_proof_fu_pre`. Account 0390D's rows must equal fu-post's, ids included (`lake_parity.py` with only `--pg-a/--pg-b`: `ids equal — equal`), and the two revert files' `before`, `rekeyed`, `deleted_ids` and `inserted` must be equal.
     2. `--revert`. Every Postgres pin must then equal fu-pre's pins taken before any write. That reference is Task 21e Step 1's `pg-pins-pre-scratch.json`: `snapshot.json`'s `pg.tables` predates the snapshot's `jbook_documents.file_path` rewrite, so it differs on `jbook_documents` alone and cannot serve; spec §7's "fu-pre's at-copy pins" means this pin of fu-pre's restored copy.
     3. A second `--revert` must print `revert: the database already holds the pre-write rows; nothing to revert`.
   - **The abort path's lake half (Task 21f Step 6).** On `.proofs/fu-abort`, a clone of the post-write fu-post, the A worktree's `jbooks export-facts` and `dbt build --select p1_era_code_decisions stg_budget_lines+` run against fu-pre's reverted database, `p1_route_safe_codes` is dropped, and `lake_parity.py` must read EQUAL against fu-pre.
   - **Live (Task 22b).** The live `--apply`'s file is `$GOVBUDGET_PROOFS/fu-release-s194-pre-image.json`; its `before` rows must equal both rehearsal files' (spec §8 step 2). After the write, live's 0390D rows are compared with fu-post's, ids included. If the four inserted PB2026 ids alone differ, because some other rolled-back transaction advanced the live sequence after Task 22a, report it; it is not a failure.
   - **Superseded.** G5's draft (apply → revert → apply on fu-post, with fu-pre's database as the revert source and `id` left out of every later comparison) is superseded; the task files no longer carry it (O-1, fixed 2026-10-13).
3. **One dbt build after the write and B7.**
   - **The build.** Tasks 21e and 22b run exactly one invocation: `dbt build --project-dir dbt --profiles-dir dbt --select p1_route_safe_codes p1_era_code_decisions stg_budget_lines+`. The two seeds are parents that `stg_budget_lines+` does not select, so they are named. dbt builds `p1_era_line_map`, then `fct_program_decade_series`, then the multi-parent tests, `assert_program_decade_conservation` after both. Task 21e checks that order in `dbt/target/run_results.json`.
   - **Appendix A's order.** That one invocation meets Appendix A's "map → program table → map" (G4-2, G5-5). The explicit three-build order is the fallback only if the order check fails. A map-only build fails conservation (Task 4b Step 6).
   - **The abort rebuild (spec §8 abort step 2)** runs from the A worktree with the deployed code: its `jbooks export-facts`, then its project's `dbt build --select p1_era_code_decisions stg_budget_lines+`. Then the one relation B's build created that A's project does not define, `p1_route_safe_codes`, is dropped (`drop table if exists main.p1_route_safe_codes`), as the spec says. Task 21f Step 6 rehearses all of it (G5-8).
4. **B exports the pre-write warehouse (G5-2; spec §7 re-pairing).**
   - **The pairs.** P2 (code) = A@fu-pre vs B@fu-pre. P1 (lake) = B@fu-pre vs B@fu-post.
   - **The rule.** No task may make `export-site` require `decided_on`, the `p1_route_safe_codes` table or alias rows. The exporter reads the route-safe seed from the CSV and copies the map with `select *`. Task 21f Step 3 stops if B@fu-pre raises.
   - **A.** A is `git merge-base main HEAD` (7dccd983), proven equal to the deployed 916ae88e on `src/`, `dbt/`, `data-seeds/`, `scripts/` and `site/`. It sits in the detached worktree `.claude/worktrees/families-fu-a` with its own `dbt parse` manifest.

### The 0390DOM page and B7

5. **The route-safe seed and `0390DOM`'s reach (spec §4.2, §4.6 as corrected).**
   - **The seed.** `dbt/seeds/p1_route_safe_codes.csv` has the columns `account,line_item_code,page_key,exhibit_family,decided_on,decided_by,note` and one row: `0390D,O&M,0390DOM,om,2026-10-04,owner,…`.
   - **The page.** `/program/0390DOM/` is rollup tier and cited to workbook cells only. It is in the sitemap (4,349 → 4,350) and in `programs_excluded.json` (`no_detail`).
   - **Where it is not.** It is not in `programs.json`, `agencies.json`, /years/ or `search_quick.json`, and has no search alias. The /years/ row universe stays 1,938.
   - **When the page exists.** It exists only after Task 22's write and export. Until then the era O&M grains are outside the decade tier's page scope and mint nothing.
   - **Header text.** The header shows "O&M" with the BLI term and the O&M badge. The `<title>` lockup keeps `BLI 0390DOM`, because copy gate leg 38 needs `[A-Z0-9-]+` (G2-6).
6. **B7 (spec §4.5).**
   - **The seed row** is `O&M|0390D||2017-2023`: `same_program`, `R-DEC-ERA-B7`, `decided_on` 2026-10-04 (the answer's date, not the ratify date; spec §5.1), `decided_by` `owner`, `n_keys` 7, pins blank.
   - **`propose`** first sends the chain to `review.csv` with the reason `A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded exclude_route_unsafe (R-DEC-ERA-EXCLUDE, 2026-10-02) — confirm or keep the seeded decision; no silent overturn`, and drops the old class row (Q25).
   - **The RDT&E chain** keeps `exclude_route_unsafe` (Q4).
   - **After the build**, `p1_era_line_map` gives the 7 `0390D-ARMY-L1` keys `program_key` `0390DOM`, and `fct_program_decade_series` gains 21 `era_line_map` grains under `0390DOM` (2,333,721 thousand).
7. **`decided_on` (spec §5.1).**
   - **The column.** It is column 14 of 18 of `p1_era_line_map`, right after `ruling`. It carries `not_null` and is published by `select *`. verify-era-map leg b compares it with the seed.
   - **Legs a–c.** They read the map only from a warehouse built with Task 9a's model (fu-post or later). On a 17-column map they report "p1_era_line_map unreadable". Legs d–h read only the export.
8. **The dbt assertion count moves 196 → 199.** The three new tests are Task 9a's `not_null_p1_era_line_map_decided_on`, Task 6's `assert_route_safe_codes_valid` and Task 7's `assert_budget_lines_route_safe_pe_bli`. Task 21d's `dbt parse` counts them. The digit count on /methodology/ is unchanged, and the move is an expected P2 difference (`site_meta /build_checks/dbt_assertions`).

### /years/

9. **The /years/ files (spec §3.3–§3.6).**
   - **Pure functions.** `split_years_matrix(payload) -> {"years_matrix.json", "years_matrix/decade.json", "years_matrix/detail.json"}` and its inverse `merge_years_matrix(core, *shards)`. Shard rows are keyed by `slug ?? pe_bli`.
   - **Shared fields.** Every file is `schema_version` 2 and carries one `build_id`, the sha256 of the canonical v1 payload. The core's `shards` lists `{name, path, columns, bytes, sha256}`.
   - **Sizes.** The writer is compact (`_write_json_compact`) and measures its own bytes against the 4 MiB cap. The core budget is 780,074 gzip bytes, measured with Python `gzip.compress(…, 9, mtime=0)`, which equals `gzip -9 -n`. Gate 20 shells out to `gzip -9 -n`, so the exporter and the gate enforce the same number. Gate 1's page weights still use node zlib (G1-4).
   - **The island** marks the table `data-shards="core[ decade][ detail]"` and requests shards from the core's load callback, the chip handler and the caret handler, never from an effect (G1-1).
   - **The live check.** On load, the only `/json/years_matrix*` request is the core.
10. **Q15's numbers.** The owner was told 524 → 1,056 programs and +9.3% → about −2.5%. With Task 13's organization-split fix, the simulated panel is 1,063 and −2.61%; first→last moves +108.17% → +103.71% (G1 interfaces, G5-4). Task 22d's go-ahead and Task 22e's stamp name both the told figures and the measured ones, read from the proof's `p2b-report.json` (`panel.a`/`panel.b`: `programs`, `fy2024a_to_fy2026r_pct`, `first_to_last_pct`), never typed from this note.
11. **The org-split fix (#207) and leg j's red number.**
    - **The fix.** `_acct_key` is gated on `is_account_split`, so the seven organization-split rows also gain `fy_2025_total`, `fy2526_change` and `fy2526_pct_change` (G1-6).
    - **Leg j today.** It finds 15,048 missing cells on 795 rows: the 14,985 era cells plus 63 modern org-split cells. The 147 era cells of those seven rows are already inside the 14,985, so P2b reports them and never adds the two counts (G1-5).

### Proof and release mechanics

12. **P1 moves eleven aggregates (G5-3).** Each moves by exactly +3,243, the 0390DOM PB2026 FY2026 total. Task 21c's `expected-fact-moves-lake.json` names all eleven fids:
    - the /programs/ universe fact;
    - the flow chart's TOTAL and Army nodes;
    - the bridge's `not_yet_crosswalked` figure;
    - seven flow nodes and edges on the path Army → Other appropriation → Other budget activity → Other program → the bridge.

    A|0390D has no fact of its own: it sits inside "Other (56)".
13. **Proof tooling (Task 2).**
    - **Snapshots.** The layout is piece 1's: `DIR/{duckdb/govbudget.duckdb, parquet/, site/, raw_docs/, manifest.jsonl, pg/<db>.dump, snapshot.json, env.sh}`. Each export runs in its own `cp -c -R DIR RUN` clone under `source DIR/env.sh RUN`. Tool errors print `proof <action>: ERROR — …` and exit 2.
    - **Noise files** are schema 2, so piece-1 noise files are refused and the controls run fresh. Writing one digests both trees (about 2.3 GB each). A DIFFERENT control deletes a stale noise file at that path.
    - **Postgres pins.** Two `pg_dump` archives of one unchanged database differ, so the pin is each table's row count and row md5 (`scripts/fu/snapshot_pins.py`). It sits with the DuckDB at-copy sha, every parquet sha minus `sam/`, and the site and raw_docs tree digests.
14. **Write-script flag names differ between the two releases, on purpose.** s194 says `--revert-file`; s195 says `--pre-image` (the spec's word). Both are tested as drafted, and each release task quotes its own script's flag. Do not unify them mid-plan.
15. **Proof-state names.**
    - **Release 1.** `.proofs/fu-pre`, `fu-post`, `fu-rel`, `fu-logs/`, `fu-release-pre-site`, `fu-release-export*` and `fu-release-s194-pre-image.json`; databases `govbudget_proof_fu_pre`, `_fu_post` and `_fu_rel`; the A worktree `families-fu-a`; local refs `publish-fu1*`.
    - **Release 2.** `.proofs/fu2`, `fu2-A`, `fu2-B`, `fu2-Bpost`, `fu2-B2post`, `fu2-logs/`, `fu2-release-pre-site`, `fu2-release-export*` and `fu2-release-s195-pre-image.json`; the database `govbudget_proof_fu2`; the A worktree `fu2-proof-a`; refs `publish-fu2*`.

    The two sets never collide.
16. **Release 2 starts from release 1 published.** Release 1 is deployed and published before Task 23a: origin `main`, the main checkout and fiscalreceipts `main` all hold it.
    - #195's migration is `022`. If another migration lands first, rename it everywhere it is named.
    - Release 1 writes none of `provenance_pages`, `jbook_documents` or `detail_narratives`.
    - The release-2 pairing uses one snapshot written in sequence: exports before the writes, then after. P2 (A vs B before the writes) has no rule list and must read EQUAL (G6-8).
17. **The backlog-test handoff.**
    - **Task 22e** rewrites `tests/test_roadmap_backlog.py::test_the_families_piece_1_follow_ups_are_filed_once_and_open` with `FAMILIES_FOLLOW_UPS_STILL_OPEN = {"JLTV continuation sentence"}` (#195 stays open with its 2026-10-02 marker).
    - **Task 26b** empties that set, checks #195's CLOSED stamp, and adds a test for its own new entries: G6-3's lineage-evidence entry, filed and closed, and G6-11's duplicate narratives, filed. Task 26b numbers them from the highest entry number at that time.
    - **Task 1's** `test_the_follow_ups_adjacent_defects_are_filed_once` pins only the filing of #207/#208 and survives their closure.
18. **One CLI convention** for `proof`, `link-coverage`, `verify-era-map` and `review_batch_page`. A tool error prints `<tool>: ERROR — <message>` and exits 2; a failed check exits 1. verify-era-map's default legs become a–h (Task 11). `verify_phase5`'s `_VERDICT_RE` does not parse `ERROR`, so it records that outcome as FAIL by exit code, which is the wanted result (G3-C9).

## Contract Notes

Folded in 2026-10-13 from the six drafting groups' notes (`tasks/notes-G1.md` … `notes-G6.md`, now removed). A task file that points at `tasks/notes-G<n>.md` or `notes-G4.md` means the matching group below.

Task files cite these items as:
- "G<n> notes, contract issue k", which is **G<n>-k** here;
- "G3 notes C<k>", which is **G3-C<k>**;
- "G3 notes item k", which is G3's interface item **G3-Ik**;
- "G6-k", which is **G6-k**.

Each group's measurements were taken on 2026-10-13, read-only (live Postgres in read-only transactions, DuckDB `read_only` outside :12–:22, `data/site` and `site/out` as of 2026-10-04), or on scratch trees under `.superpowers/sdd/2026-10-04-piece1-followups/work/<group>/`. Every task's code blocks were applied in task order to a scratch copy, and the quoted red/green outputs are those runs'.

### G1: /years/ (Tasks 13, 14, 15)

**Interfaces assumed from other groups.**
- **Task 1.** It files #207 and #208, which Tasks 13–15 cite.
- **Tasks 8, 9 and 12** edit `export_site.py` before Task 13, but none of them touches the blocks Task 13 quotes:
  - the import block;
  - the `_YEARS_MATRIX_MAX_BYTES` comment;
  - `_YEARS_DEFAULT_COLUMNS`;
  - `_emit_years_matrix`;
  - the step-17 call;
  - `_leak_surfaces`.

  Task 13 Step 5 greps before adding `import os` or `import gzip`.
- **Task 9b** keeps `era_keys.is_era_procurement_key` (it changes only `$` → `\Z`). `yearsmatrix-recompute.py` uses it.
- **Leg g and the map.** Gate 20's legs g and j see only /years/ rows, so the B7 era rows and the alias never reach them. Leg g reads `p1_era_line_map.parquet` columns `edition, era_key, program_key, program_account, program_org, decision` and ignores `decided_on`.
- **Task 16 consumes Task 13.**
  - `_emit_years_matrix` loses `era_grain_fids`, and `_write_all_sidecars` stops passing it to that call.
  - `test_era_grain_fids_reach_the_fenced_emitters` is renamed `test_era_grain_fids_reach_the_lineage_emitter_only` and asserts `{"lineage": sentinel, "years_matrix": "not passed"}`.
  - Task 13 rewords two docstring paragraphs (`_build_decade_citation_rows`' `era_grain_fids` entry, `_write_all_sidecars`' second paragraph). Task 16 anchors on neither.
- **Task 17** edits `prepare-assets.mjs` step 5d2. Task 14 edits step 5d. Either order works.
- **Task 19 and Task 15** edit different /methodology/ sentences: Task 19 at `:1013-1028` and the FAQ, Task 15 at `:1722-1723`. They share the page's gzip budget. Q13 measured 0 raw / −6 gzip; T7 measured +16 / −13. Task 21h re-stamps on the real build.
- **Task 21.**
  - A@fu-pre exports one `years_matrix.json`, while the B exports have three files.
  - P2's rules: `json/years_matrix.json` changed; `decade.json` and `detail.json` exist only in B; `manifest.json /json_sidecars` +2.
  - P2b may merge with `merge_years_matrix` or call the gate's node helpers (`loadYearsMatrix`, `runSidecarParityLeg`).
  - Gate 20, with legs j and k, runs on the B build in W4.
- **Task 22.**
  - Live check: `node -e "import('./scripts/gates/yearsmatrix.mjs').then(async (m) => console.log(await m.probeYearsOpeningFetches('https://fiscalreceipts.com')))"` prints `problem: null`.
  - `verify_live_assets.mjs` assertion 8, run by `deploy.sh` step 4, requires both shards to return 200 with the core's `build_id`.
  - The stamp closes #193, #207 and #208, records #206 T4 as subsumed by #193 (leg j), and records Q15.
  - Task 15 Step 8 already writes the piece-1 spec §6.2 amendment. The stamp cites it and adds none (G1-11).

**Contract issues.**
- **G1-1.** Shards load from events, not effects: `react-hooks/set-state-in-effect` is a lint error. The core's load callback, the chip handler and the caret handler call the module-level `requestShards`.
- **G1-2.** Pre-split tolerance; see Known red windows. `mergeYearsMatrix`/`merge_years_matrix` treat a schema-1 row's own `projects` as the default. The island requests only the shards the core lists. `prepare-assets.mjs` copies `years_matrix/` only when the core's `schema_version >= 2`. Gate 20 does not tolerate a schema-1 core.
- **G1-3.** Sizes were re-measured on the compact writer. The simulated era-lifted split is 1,100,823 B / 344,303 gzip (core), 1,390,739 / 433,932 (decade) and 1,231,643 / 284,230 (detail). Today's fenced payload splits to 855,969 / 263,763, 900,935 / 278,811 and 1,231,643 / 284,232.
- **G1-4.** The gzip measure is decision 9's: Python and `gzip -9 -n` both give 780,074 B for the deployed file, while node's zlib 1.3.1 gives 754,311.
- **G1-5.** Leg j's red number is decision 11's.
- **G1-6.** The org-split fix moves more than decade cells; see decision 11. P2b reports what moved on those rows.
- **G1-7.** Leg g's era rule, made concrete:
  - An era leaf is a `workbook` citation on sheet `Exhibit P-1` in a PB2017–PB2023 column.
  - An era-map sum is a `derived` citation whose formula names `era_line_map=`.
  - "A split row's pins match its slug" means `(program_account, program_org)` equals `programs.json`'s `(account, org)` for that slug.
  - A dry run over all 14,985 era cells passed 14,985. On the simulated split every static leg passes: a 47/47, b 47, f and g 64/64, i 45,316 of 46,524 checked, j 46,524 cells on 1,938 rows equal, d 53,072 fids.
- **G1-8.** The live-leg waits. The design's `:1147-1160` is the i3 reveal, which waited on the header, not on a timeout; Task 15 adds an `aria-busy` wait there. The two real timeouts become waits on `data-shards` or the Δ header. The filter leg's `waitForTimeout(300)` is unrelated and stays.
- **G1-9 (not changed; follow-up candidate).** The 27 `/agency/` split-key rows keep `href="/program/<pe_bli>/"`, the shared-code page, and React `key={p.pe_bli}`, which is duplicated for the ten account-split pairs on `/agency/N/`. Neither ships a wrong figure.
- **G1-10 (not changed).** `site/scripts/capture-5d-visuals.mjs`, a manual Phase 5D tool, reads Δ cells from the core. They now live in `detail.json`. The tool has been stale since 5E hid the Δ column.
- **G1-11.** The §6.2 amendment is written by Task 15 Step 8 and cited by Task 22.
- **G1-12.** `getProgramDecadeCells` reads `fy2024a` and `fy2026r`. Both are default columns by construction, so it needs no change.

### G2: Chem Demil, the map alias and B7 (Tasks 6, 7, 8, 10, 12)

Order inside the group is 6 → 7 → 8 → 10 → 12. Task 12 needs 6 and 8, and its page exists only after Task 22's write.

**Interfaces assumed from other groups.**
- **Task 3.** It adds `class P1KeyConflict(ValueError)` before `_slug` in `p1_loader.py`. Its tripwire block sits between the `EraKeyConflict` raise and `if skipped_invalid:`. Task 6 replaces the log only from `if skipped_invalid:` down, and its new loader tests live in `tests/jbooks/test_p1_loader_route_safe.py`, which imports `P1_HEADERS` from `jbooks.test_p1_loader`. Task 7 reports `P1KeyConflict`, `UnsafeBudgetLineCode` and `P1RestatementMismatch` as `s194: REFUSED — <name>: <message>`, exit 1.
- **Task 4a.**
  - `p1_loader.py` imports `from govbudget.jbooks.era_keys import EraKeyConflict, era_procurement_key`.
  - `era_map.py`'s import block ends with `from govbudget.jbooks.era_keys import EraKeyConflict, is_era_procurement_key`; Task 8 anchors there.
  - `era_map` must not import `p1_loader`. `route_safe_codes` imports only the standard library.
  - `_hold_for_review` produces decision 6's review row. Task 8's `test_propose_sends_a_re_ruled_chain_to_review_not_into_the_seed` pins that reason string and needs Task 4a.
- **Task 4b.** Its ratify success line is quoted in Task 10. That selection lacked `p1_route_safe_codes`, which `p1_era_line_map` references after Task 8; Task 8 now adds the seed to the line and to 4b's test pin, and Task 10 quotes the amended line (O-3, fixed 2026-10-13).
- **Task 4c.** `render` writes `review_sha256` into `tmp/era-review/B<n>.json`, and `answer` refuses a changed `review.csv`. Tool errors print `review_batch_page: ERROR — …` and exit 2. A one-key chain reads "1 era line".
- **Task 1** files the Q7 and Q4 notes, so Task 10 edits neither the ROADMAP nor the spec. Task 7 adds one dated correction to a different ROADMAP paragraph (the findings-log entry "Reject junk at the loader…"), for Q9.
- **Task 9.** It runs after Task 8 on the same files. Task 8 changes only `p1_era_line_map.sql`'s header paragraph, the `program_key` select line and an appended `left join {{ ref('p1_route_safe_codes') }} rs`, so 9b's script still finds exactly its 2 prefix-only sites. Task 8 also changes `_lake`'s signature in `tests/test_p1_era_line_map_sql.py` to `_lake(lake=None, seed=None, docs=None, route_safe=None)` and edits the `program_key` descriptions in `schema.yml`. Every 9a/9b/9c block matched on the scratch tree.
- **Task 11.** Leg g expects the 7 O&M era rows to cite `pe_bli` `0390DOM` and finds `json/program_details/0390DOM.json`. That holds only after Task 22.
- **Tasks 13 and 14.** `programs.json` is unchanged by G2.
- **Task 17** edits `program_pdf_receipts.py` at `def export_program_pdf_receipts(` and its output block. Task 12 adds `program_code_matches` before `def matched_amount(` and changes only the code check at `:350-351`.
- **Tasks 21 and 22.**
  - The build is decision 3's. A copy of the live DuckDB with the B7 seed built `p1_route_safe_codes p1_era_code_decisions p1_era_line_map fct_program_decade_series` → `PASS=37 … TOTAL=37`, with 21 `era_line_map` grains under `0390DOM`.
  - P1 expectations: `data/budget_lines.parquet` gains 4 rows net (+4 PB2026 `0390DOM`, −8 RDT&E, 8 re-keyed with the same ids). `program_details/0390DOM.json`, with `printed_code`, `exhibit_family` and `restated_lines`, lands in P1. The `datasets.json` scope change lands in P2.
  - `assert_budget_lines_route_safe_pe_bli` fails on any lake that still holds the 16 stale rows.

**Contract issues.**
- **G2-1.** `--revert`'s source is a revert file that `--apply` writes inside its own transaction before COMMIT. It holds every column of the 16 rows, the ids re-keyed, inserted and deleted, and an md5 digest of every other row. That makes it the same table at the same instant, with no `pg_restore`, and `--revert` refuses a database that moved. The id sequence keeps its 4-id advance. This is decision 1.
- **G2-2.** `--dry-run` is its own mode.
- **G2-3.** §4.3's "own counter" is `P1Parse.restated` (the rows themselves, so `verify_r1_restatements` can compare amounts). `P1Parse.skipped_invalid` and `_is_valid_pe_bli` are removed.
- **G2-4.** "Equals the loaded R-1 0390D sum" is checked as the sum of the two named PEs, 0708081D + 0708083D, in the same account, plus the printed title. Today both equal the account sum.
- **G2-5.** `route_safe_codes.P1_R1_RESTATEMENTS` carries the title and the PEs. The exporter writes them to the alias page's sidecar as `restated_lines`.
- **G2-6.** The printed code shows in the header and the wayfinding identity. The `<title>` keeps `BLI 0390DOM`. The WHAT-IT-IS card says "operations & maintenance". The TOA chips read the generic "P-1/R-1 TOA", because `basis.normalizeExhibitFamily` maps only `rdte`/`procurement`. A "P-1 TOA" chip would need an `om` → `procurement` mapping, which is not drafted; do it only if the owner asks.
- **G2-7.** §4.2's "collides with no other `pe_bli`" reads `stg_budget_lines` and `stg_budget_details`.
- **G2-8.** The dbt count is decision 8's.
- **G2-9.** Applying 04b's blocks with G2's harness left 4 of its own ratify tests red. G4's harness applied 04b cleanly (4 red → 39 green). It was the harness: Step 2's "In `ratify`, replace:" named no file. Step 2 now names `src/govbudget/jbooks/era_map.py`, and the 2026-10-13 chain review re-applied every 04b block on a scratch tree, each matching exactly once at its turn (O-7, settled).
- **G2-10.** The amended `p1_era_line_map` scope adds about +367 raw / +212 gzip to /data/ (three renderings), inside its 1,070 gzip headroom. Task 21h re-stamps.

**Shared state.** None live; see the shared-write table.

### G3: metadata, copy and F-15 (Tasks 9a–9c, 11, 17, 18, 19, 20a–20c)

Order: 9a → 9b → 9c → 11, then 20a → 20b → 20c (20c imports 20b's `site/scripts/direct-run.mjs`). Tasks 17, 18 and 19 are independent of the rest and of each other.

**Interfaces assumed (G3-I1 … G3-I8).**
- **I1.** Task 1's workspace.
- **I2.** Task 4a moves `EraKeyConflict` into `era_keys.py`. Task 9b changes only the `_ERA_KEY_RE` line and the comment above it; if code sits between them, anchor on the `_ERA_KEY_RE` line alone.
- **I3.** Task 8 leaves untouched:
  - the `-- keys_sha_ok is the drift guard` line;
  - the `decisions` CTE's `ruling` lines;
  - the `bound` CTE;
  - the final select;
  - `schema.yml`'s `ruling` description and `- name: keys_sha_ok`.

  Task 9b's script refuses unless the SQL holds exactly 2 prefix-only sites. Task 9a's live proof loads any `ref()`'d seed CSV generically, and with the O&M chain still excluded before Task 10, both of its `except all` counts are 0.
- **I4.** Task 9a's dated figures (6,212 / 701 / 14) are pre-B7. After B7, leg g expects the 7 O&M keys to cite `0390DOM` and resolves an unpinned code straight to `program_details/<program_key>.json`.
- **I5.** Task 12 changes the `p1_era_line_map` scope string and its pin in `tests/test_export_era_line_map.py` (`:62-63`). Task 9a edits that file only at `MAP_DDL`/`ROWS`/`INSERT`.
- **I6.** Task 15 and Task 19 edit different /methodology/ sentences; Task 21h re-stamps once.
- **I7.** Task 21:
  - **P3 re-pin** with Task 20a's hardened `capture_f15_fixtures.py --site-dir … --duckdb … --out-dir tests/fixtures/f15 --expect-sha256 <sha>`. The hermetic sha on today's fixtures is `d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f`; only `programs[7].note` differs, 139,024 → 139,061 bytes. Then the schema-2 page snapshot. Add a dated T9 line to `tests/fixtures/f15/README.md`.
  - **verify-era-map** legs a–c run only on fu-post (decision 7).
  - **Rules from this group.** P1: `p1_era_line_map.parquet` gains `decided_on`. P2:
    - `json/budget-pdf-receipts/??.json` only in A (256 files, 419,075 B);
    - `json_sidecars` 36,271 → 36,015 before Task 13's +2;
    - two alias URLs in `search_quick.json` (`alias:jassm` → `/program/0207325F/`, `alias:c-130j` → `/program/0401132F/`);
    - `f15_funding_history.json /programs/7/note` only;
    - `dbt_assertions`.
  - **Weights.** /methodology/ +16 raw / −13 gzip. /families/f-15/ +194 / +67 → 703,621 / 68,605 against 725,000 / 70,000. /about/ −13 gzip.
- **I8.** Task 22's stamp quotes:
  - Q16's strings (Task 19);
  - the F015E0 note (Task 20a);
  - Q21's accessible name `BLI F015E0 F-15e (FY2020 F-15EX Lot 1 aircraft) Procurement · Historical code` (Task 20c);
  - #197's two routes;
  - #196's 256 files / 419,075 B;
  - the closures of #203, #206 T6/T7/T9/T11, #201 (with §6.9's reasons), #196 and #197.

  Live checks: `/json/budget-pdf-receipts/00.json` returns 404 while a `v2/` shard returns 200, and `search_quick.json` carries the two aliases.

**Contract issues.**
- **G3-C1.** The F-15 red window; see Known red windows. The re-pin needs a B@fu-post build, so it cannot move into Task 20.
- **G3-C2.** §5.7's span for `tight_glyph_geometry` is AST 91–115 (line 116 is blank). Task 17's deletion script pins 91–115 and refuses any other span.
- **G3-C3.** Leg g resolves a pinned code through `programs.json`'s (`pe_bli`, `account`, `org`) → `slug` (for example `0145` → `0145-APN`, `0145-PANMC`), not `program_key-<account|org>`. Live, all 17,481 same_program rows resolve, 185 of them on collision codes.
- **G3-C4.** Q21's string is defined by Task 20c as the header's visible text minus the link.
- **G3-C5.** Task 20c adds `data-history-matrix-note=""` (+27 raw, inside the +194).
- **G3-C6.** T9's weight is +194 raw / +67 gzip, which leaves 1,395 gzip bytes.
- **G3-C7.** Non-vacuity: leg g fails with no era row, and leg h with no era book diff. Live: 17,502 rows and 1,044 diffs.
- **G3-C8.** `not_null` on `decided_on` fails during the Q25 window beside `assert_p1_era_map_no_undecided`. This is fail-closed, and no live build happens then.
- **G3-C9.** verify_phase5 records an ERROR as FAIL by exit code (decision 18).
- **G3-C10 (not changed).** `scripts/era/s1_reload_era_p1.py` (`^\d{4}[A-Z]-[A-Z]+-L`) and `scripts/era/fact_stability.py` (`^\d{4}[A-Z]-[A-Z]+-L\d+$`, used only for F-15 codes) are outside §6.4's ten sites. Task 2c leaves the regex alone.
- **G3-C11.** Leg f's "only the S5 correction re-pins it" (`verify_era_map.py:49`, `:480`) is stale after T9's re-pin. Task 11 now rewords the docstring and the failure line ("the committed pin says … (only an owner-approved correction re-pins it)") and re-pins `tests/test_verify_era_map_def.py`, before Task 21's B (O-4, fixed 2026-10-13).
- **G3-C12.** Q18 is answered: Task 9a publishes `decided_on` only.

### G4: worktree and hardening (Tasks 1, 2a–2c, 3, 4a–4c, 5, 16)

Order: 1 first; 2a → 2b → 2c; 4a → 4b → 4c. Tasks 3, 4 and 5 are independent, and 16 runs after 13. The dry run applied every G4 block with `work/g4/tools/apply.py` in the order 3, 5, 2a, 2b, 2c, 4a, 4b, 4c, a simulated Task 13, 16, 1. The scratch suite ran 4,186 tests, and its failures were only Task 13's own `TestEraFence` (inverted by Task 13) and tests that read the absent `data/`.

**Interfaces assumed from other groups.**
- **Task 13** is as G1 describes. Task 16 anchors only on the three `era_grain_fids: frozenset[str] = frozenset(),` signature lines and the `lineage_flow_payload = build_lineage_flow(` call. It asserts `"era_grain_fids" not in inspect.signature(es._emit_years_matrix).parameters`. Its Step 1 `-k "required or years_matrix_no_longer or lineage_flow"` does not select G1's renamed test.
- **Task 6** builds on Task 3's `p1_loader.py`: `P1KeyConflict` before `_slug`, the rewritten grouping comment (`# Grouping key: (account, account_title, organization, ba, ba_title, bli,`), and the tripwire block (`# ROADMAP #202: the grouping key holds three titles`). The tripwire runs on `sums`, so an alias row and a skipped restatement never reach it twice.
- **Task 7's** `--check` reports a `P1KeyConflict` as a refusal, not a traceback. Today there are 0 cases.
- **Task 8** owns the UNSAFE narrowing (G4-1). It anchors on Task 4a's import block and `propose` as Task 4a leaves it: the `_hold_for_review` call after the enrichment loop, and the `outputs = {…}` block before `return counts`.
- **Task 10** relies on Task 4a's no-silent-overturn path (decision 6). `chains.csv` reads `left_ruling_reason` `class result differs from the seeded decision`. `answer` must run before anything rewrites `review.csv`.
- **Task 9b's** new tests raise the counts in Task 4b Step 6 (`TOTAL=20` / `TOTAL=35` are HEAD's). The verdicts do not change.
- **Task 11** owns verify-era-map's half of the CLI convention.
- **Task 21** uses:
  - Task 2a's `proof snapshot`. It refuses a password DSN, any copy minute in :15–:20, a symlink in a pinned tree, and a view or `jbook_documents.file_path` resolving outside the snapshot. On failure it removes `out_dir` (only if this call created it) and drops only its own database.
  - Task 2b's noise files (decision 13).
  - Task 2c's type-strict `fact_stability.py`.
  - Task 5's `link-coverage`, which prints a second stdout line `link-coverage: <n> summary card(s) cited by XML path only, outside V9 (Q20)`. With `--write-baseline` it writes only on 0 violations, and never to the `--baseline` path.
- **Task 22.**
  - (a) It closes #194, #207 and #208, and updates `test_the_families_piece_1_follow_ups_are_filed_once_and_open`, which requires #194 to end with `**Status:** open (2026-10-02).` (decision 17).
  - (b) The B7 build is decision 3's.
  - (c) The Q22 Status lines. #198 is PARTIAL and names what neither §6.2 nor §6.9 covers (see Ledger conventions). #199 is CLOSED with §6.9's reasons; its plaintext-DSN item is covered by the password refusal (G4-4).

**Contract issues.**
- **G4-1.** UNSAFE narrowing is Task 8's, not Task 4's. Task 4a leaves `CLASS_ORDER`, `_ROUTE_UNSAFE_CHARS`, `is_route_safe_code`, `_Context.classify` and `class_ruling` untouched.
- **G4-2.** The B7 build order is decision 3. Measured on a clone of the live lake: map-only gives `FAIL 21 assert_program_decade_conservation` and `PASS=19 … ERROR=1 … TOTAL=20`; the single invocation gives `PASS=35 … TOTAL=35`.
- **G4-3.** Not every hardening item can be red at HEAD. Test gaps are green there:
  - the `.wal`, writer-lock, missing-entry and `?host=` refusals, and the port-55432 assertion (2a);
  - the modern P-1 code shape and the disjoint-columns case (3);
  - ratify's untested branches (4b);
  - the successor-block escaping (4c);
  - the derived figure with an uncited input (5).

  Each task says which of its tests pass at HEAD and why. #205 has no permanent test (`npm ci --dry-run` needs the registry), so Task 1 shows red and green with commands.
- **G4-4.** #198 is PARTIAL (see Ledger conventions). #199's "snapshot.json and env.sh keep the scratch DSN in plaintext" is handled by the password refusal, not by removing the DSN.
- **G4-5.** Noise-file tree digests are recorded as `a_tree_sha256` and `b_tree_sha256` (`proof._tree_digest(tree)["sha256"]`). `load_noise_classes` treats them as provenance and does not re-digest on `--noise-from`.
- **G4-6.** `link-coverage --write-baseline` never records a report with violations (`baseline NOT written …`).
- **G4-7.** `proof snapshot` removes `out_dir` only when this call created it.
- **G4-8.** The date convention; see Ledger conventions. The drafts already follow it, so Task 1 Steps 10–12 and Task 2c Step 6 need no substitution.
- **G4-9.** The untracked eval-run file; see Commits.
- **G4-10.** Line hints. §6.3's accurate S1b comment is at `p1_loader.py:198-201`, and the stale one at `:183-186`. §6.7's "13 call sites" are today 3 production calls and 3 test calls, of which 2 rely on the default: `tests/jbooks/test_export_lineage.py::_emit` and `tests/test_program_member_enrichment.py:140`.
- **G4-11.** One test cluster serves many sessions; see Tests never touch the real database.

**Shared state.** None live. Local writes:
- `site/node_modules` and `site/out` (Task 1, git-ignored);
- `.proofs/fu-npmci/` (kept);
- `.proofs/fu-t4a-propose/` and `.proofs/fu-t4b-buildorder/` (removed in their steps);
- pytest on 55432.

### G5: release-1 proof and release (Tasks 21a–21i, 22a–22e)

**Interfaces checked against drafted task files (✓) or assumed (◇), with today's reconciliation.**
- **✓ Task 2a.** `snapshot.json` keys are unchanged: `schema_version` 1, `duckdb.sha256_at_copy`, `parquet{rel: {sha256, bytes, rows}}`, `site.sha256`, `raw_docs.sha256`, `manifest_jsonl_sha256`, `pg.tables{name: {rows, md5}}` (taken before the `file_path` rewrite), and `pg.scratch_dsn` `dbname=… host=localhost`.
- **✓ Task 2b.** Noise file schema 2, written only by an EQUAL `--control --write-noise`.
- **✓ Task 2c.** `compare_citations(a, b, f15_leaves, *, expected_f15, noise_classes) -> dict` (keys `missing`, `changed[{fact_id, field, a, b}]`, `noise_equivalent`, `reorder_classes_trusted`), type-strict. Also `govbudget.proof.load_noise_classes(path)`.
- **✓ Task 4b; ✓ Task 5; ✓ Task 6.** As above.
- **✓ Task 7.** G5 assumed `--revert --pre-dsn`. Decision 1 reconciles G5-1 with Task 7, and Tasks 21d–22e now use Task 7's CLI (O-1, fixed 2026-10-13).
- **◇ Task 8.** Assumed that export-site still runs on a warehouse built before the write (decision 4).
- **✓ Task 9a.** `decided_on` is column 14 of 18.
- **◇ Task 10.** One committed B7 row and no live build. Its `decided_on` is 2026-10-04 (decision 6).
- **◇ Task 11.** Legs a–h.
- **◇ Task 12.** The 0390DOM sidecar carries `printed_code: "O&M"` and `exhibit_family: "om"`. The page prints "… its address uses 0390DOM because a web address cannot carry “&”." and links `/program/0708081D/` and `/program/0708083D/`. The Q3 scope amendment is in `_DATASET_SCOPES`.
- **✓ Task 13** (decision 9); **◇ Tasks 14/15** (the `data-shards` marker, `verify_live_assets.mjs` probing the three /years/ files, gate legs a–j/k); **✓ Task 17** (`remove_v1_receipt_shards`, `json_sidecars` −256, `out/json/budget-pdf-receipts` holds only `v2/`); **◇ Tasks 18, 19**.
- **✓ Task 20a** (the F015E0 note opens "This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include"; the sha in G3-I7); **✓ Task 20c** (snapshot schema 2 adds `prose`, `matrix.total_header`, `matrix.annual[].partial`, `matrix.rows[].aria_label`).
- **◇ Tasks 1 and 9.** Task 1 files #207/#208 and the Q7/Q4 notes; Task 9a writes the piece-1 spec §4.4 `decided_on` amendment. Task 22e Step 1 only checks that they exist.

**Contract issues.**
- **G5-1.** `--revert`'s source. Superseded by decisions 1 and 2.
- **G5-2.** B exports the pre-write warehouse (decision 4).
- **G5-3.** Eleven moved aggregates (decision 12).
- **G5-4.** Q15's numbers (decision 10).
- **G5-5.** The dbt selection (decision 3).
- **G5-6.** SAM state.
  - All four proof exports read the same SAM parquet, so P1 and P2 see no SAM change. The roughly 15 new registrations appear only in release vs production (`SAM_D`), and `expected-diff-release.json` needs none.
  - In P2, `json_sidecars` moves `<a> → <a − 254>`, where `<a>` = 36,271 plus the new SAM receipt files.
  - If the job stores more between Tasks 21 and 22, they show up as rule matches.
- **G5-7.** An extra owner go-ahead comes before the live Postgres write (Task 22b Step 2).
- **G5-8.** The abort path covers the lake too (decision 3). A2 runs the deployed code's export-facts and build, drops `p1_route_safe_codes` (spec §8), and proves live = fu-pre with `lake_parity.py`; Task 21f Step 6 rehearses it on a clone of fu-post.
- **G5-9.** A third scratch database: `govbudget proof snapshot --out .proofs/fu-rel --scratch-db govbudget_proof_fu_rel`. Task 22a also proves that the live database's pins (`snapshot_pins.py pg`) equal the snapshot's.
- **G5-10.** The backlog-test handoff (decision 17).
- **G5-11.** #198 is PARTIAL.
- **G5-12.** Leg f's wording cannot be fixed in Task 21: it would change `src/` after the proof's B, and Task 22a checks that HEAD's export code equals B. Task 11 fixes it (O-4).
- **G5-13.** The Status stamp convention; see Ledger conventions.

### G6: #195 and release 2 (Tasks 23a–23c, 24, 25a–25c, 26a–26b)

Order: 23a → 23b → 23c → 24 → 25a → 25b → 25c → 26a → 26b, all after release 1 is deployed and published.

**Validation.** Every block of 23a, 23b, 23c, 24 and 25a was applied to a scratch copy and run against a private Postgres 17 cluster. The ten affected test files pass (273 tests), and pyflakes stays at the HEAD baselines. The scratch suite gave 4,033 passed; its 55 failures and 2 collection errors are the same on an unmodified copy, because they come from files the copy lacks.

`s195_narratives.py --check` ran read-only against live Postgres (about 12 minutes) and reproduced the prototype's plan. The CLI's spawn workers are safe under `python -m govbudget`.

**Interfaces assumed from other groups.**
- **Task 1.** The environment is as above. Task 26b numbers its new ROADMAP entries from the highest number then.
- **Task 2.** `snapshot.json` keys `created_at`, `duckdb.sha256_at_copy`, `duckdb.sha256`, `duckdb.views_rewritten`, `site.sha256`, `raw_docs.sha256`, `manifest_jsonl_sha256`, `pg.dump_sha256`, `pg.scratch_dsn`. The snapshot's `env.sh` sets `GOVBUDGET_PG_DSN=dbname=govbudget_proof_fu2 host=localhost`. Rule files load with `govbudget.proof.load_expectations` (keys `path, why, status, pointer, change, required`).
- **Task 5.** `link-coverage` exits 0 on a pass, and release 1 leaves `data/research/link_coverage/baseline.json` valid for its export.
- **Task 7.** The flag names (decision 14).
- **Task 16.** Task 23b inserts its own helper directly above `def _emit_lineage(`, as Task 16 does; whichever lands second sits between, and the anchor stays unique. Task 23b also adds one call directly above `    # ROADMAP #29(c) — the /lineage/ identity diagram payload. Built from the`. It touches neither `_emit_lineage`'s signature nor its call.
- **Tasks 20/21.** `tests/fixtures/f15/history.sha256` is release 1's pin. Release 2 leaves `json/f15_funding_history.json` byte-identical; the F015E0 note receipt `e7d5bcfb4a30f458` does not move.
- **Task 21.** G6 adds `scripts/fu/s195_narratives.py` and `scripts/fu/narrative_relocation_report.py` and imports nothing from G5's files.
- **Task 22** (decision 16). Release 1's export is the live `data/site`, and `govbudget/main` is release 1's merge commit.

**Contract issues.**
- **G6-1. The volume group is the book set.** Grouping by identical master-XML sha gives 8 groups holding the 20 superseded volumes. But Army RDT&E Vol 1 BA1 (doc 344) and BA2 (doc 351) embed two regenerations of one master. The plan therefore searches the edition's book set, `provenance_pages.book_set`: same `fiscal_year`, `org` and `exhibit_family`, downloaded or superseded, attached volume first. Design §5.6's 3,504 + 727 split is reproduced in kind: 2,996 + 440 in superseded volumes, and 721 in hosted ones.
- **G6-2. Pageless rule and the second ratchet.** 1,444 citations stay pageless:
  - 1,367 whose opening no volume prints (1,342 of them from the Navy RDTEN BA1–3 master XML);
  - 77 whose opening a volume prints without the closing words within three pages.

  Gate 5 fails a pageless citation only when a volume page LOCATES it, and ratchets the 77 as `PAGELESS_OPENING_SEEN_CEILING = 77`. Task 24 Step 0 asks the owner before any of Task 24 is written (O-5).
- **G6-3. 19 lineage-evidence narratives have no provenance row, and one has a stale `unresolved` row** (`906bcdda2a0660d1`, PB2019). The plan does two things:
  - It relocates every edition's narrative rows: 11,698 rows, not PB2026's 11,679.
  - It runs `jbooks narrative-provenance --lineage-evidence` as release 2's first live write (19 inserts).

  The 19 rows are filed and closed as a new backlog entry in Task 26b.
- **G6-4. A new location needs the PE/BLI anchor on the opening's page** (`narrative_located_at`). That gives exactly Q26's 228 relocated / 111 `opening_only`. Without the anchor the split is 230 / 109.
- **G6-5. Lineage rail pages.** 22 of the 92 evidence narratives move. Task 23b sets `lineage.rail.*.evidence.page` from the exported citation. Today all 184 rail entries agree, so P2 stays EQUAL; P1 carries one rule for it.
- **G6-6. R2 sampling.** `verify_live_assets.mjs` assertion 1 probes only the 5 newest cited PDFs. Task 26b Step 4 probes all 20 new volumes by `--sha`. A permanent assertion over every narrative-cited PDF is not drafted; it is a follow-up candidate.
- **G6-7. verify-phase5b1 now reads Postgres and the raw PDFs.** It needs about 1,026 s single-threaded; `page_texts_parallel` uses up to 8 processes. Task 24 adds a LAUNCH.md note, and verify-phase5 inherits the cost.
- **G6-8. Release-2 pairing** (decision 16). The release-state diff (Task 26a Step 5) has no rule list either: Task 26a Step 1 checks the SAM parquet against the snapshot.
- **G6-9. Weight.** `/program/0601102A/` moves 1,157,481 / 145,454 → 1,171,692 / 147,566 (+14,211 raw, +2,112 gzip), which leaves 8,308 raw and 3,434 gzip under 1,180,000 / 151,000. 725 program pages change. Task 25c re-stamps.
- **G6-10.** Q26's "Task 28 … Task 30" are the 2026-10-04 draft numbers of Tasks 23 and 24.
- **G6-11. Duplicate narratives (filed, not fixed).** Docs 344 and 351 are both kept, so 1,207 PB2026 narrative pairs share (pe_bli, kind, body). Task 26b files it.

## Open Items for the Review Pass

The drafts carried these known gaps. The 2026-10-13 review pass (three lenses: owner-decision fidelity, the cross-task chain applied on scratch copies, grounding and safety) closed O-1 to O-7 in the task files; each line says where. O-8 stays a list of candidates.

- **O-1 (fixed): Tasks 21d, 21e, 21f, 21i, 22a, 22b, 22e follow decisions 1 and 2.** 21e runs `--dry-run` and one `--apply --revert-file "$L/s194-fu-post-revert.json"` on fu-post (Steps 2–3; its old revert/re-apply steps are gone, and its steps are renumbered 1–6). 21f Steps 4–5 rehearse `--dry-run`, `--apply`, `--revert` and a second `--revert` on fu-pre after both fu-pre exports, and Step 6 rehearses the abort path's lake half (its later steps are renumbered 7–14). 21d and 21i describe fu-pre as written only by that rehearsal. 22a takes no id-free pin. 22b runs `--dry-run`, then `--apply --revert-file "$GOVBUDGET_PROOFS/fu-release-s194-pre-image.json"`, checks that file's `before` rows against both rehearsals', compares live with fu-post ids included, and its abort A1 is `--revert --revert-file <that file>`. 22e's findings entry states the sequence that ran.
- **O-2 (fixed): Task 26a Step 2b** asks the owner before release 2's live Postgres writes and names what the abort path cannot undo (migration 022's column and the 19 lineage-evidence rows).
- **O-3 (fixed): Task 8** adds `p1_route_safe_codes` to `era-map ratify`'s "ONE build" line in `cli.py` and to Task 4b's test pin; Task 10 quotes the amended line.
- **O-4 (fixed): Task 11** rewords leg f's docstring and failure line and re-pins `tests/test_verify_era_map_def.py`.
- **O-5 (fixed): Task 24 Step 0 ★** asks the owner about `PAGELESS_OPENING_SEEN_CEILING = 77` before any of Task 24 is written; on a no, Tasks 23a–26b are amended to the owner's rule first.
- **O-6 (fixed):** 04b and the first lines of 23a–26b point at this README's Contract Notes.
- **O-7 (fixed):** 04b Step 2 names `src/govbudget/jbooks/era_map.py`; the chain review re-applied 04b (G2-9).
- **O-8 (follow-up candidates, not in this wave):** file them in the release-1 or release-2 stamp, or leave them:
  - G1-9 (`/agency/` split-key href and key);
  - G1-10 (`capture-5d-visuals.mjs`);
  - G2-6 ("P-1 TOA" chips for `om`);
  - G3-C10 (two other era-key spellings);
  - G6-6 (a permanent R2 assertion over every narrative-cited PDF);
  - §5.6's "file separately" items (the 8,021 unresolved detail amounts; the missing Navy RDTEN books).

  Q23 (`site/src/lib/aliases.ts`) is filed for piece 2 by Task 22e Step 3 (f), with a filing test in Step 4.

## Tasks

The task numbers are spec Appendix A's. A split task has lettered parts, and a dependency on a split task means all of its parts. ★ marks an owner touchpoint. B7 (Task 10) was answered on 2026-10-04 and is not asked again.

| # | File | Title | Group | Depends on | ★ |
|---|---|---|---|---|---|
| 1 | [tasks/01-worktree-and-lockfile.md](tasks/01-worktree-and-lockfile.md) | Worktree and lockfile (#205); file #207 and #208; the Q7 and Q4 notes on #194 and piece-1 spec §5.2 | G4 | — | |
| 2a | [tasks/02a-proof-snapshot-safety.md](tasks/02a-proof-snapshot-safety.md) | Proof tooling hardening — snapshot safety and the `proof` CLI convention (#199) | G4 | 1 | |
| 2b | [tasks/02b-proof-diff-noise-file.md](tasks/02b-proof-diff-noise-file.md) | Proof tooling hardening — numeric corners and the schema-2 noise file (#199) | G4 | 2a | |
| 2c | [tasks/02c-proof-scripts-and-notes.md](tasks/02c-proof-scripts-and-notes.md) | Proof tooling hardening — proof scripts and the two proof notes (#199) | G4 | 2b | |
| 3 | [tasks/03-p1-loader-tripwires.md](tasks/03-p1-loader-tripwires.md) | P-1 loader tripwires (#202) | G4 | 1 | |
| 4a | [tasks/04a-era-map-propose-guards.md](tasks/04a-era-map-propose-guards.md) | Era-map guards — `propose`, the successor search, atomic writes (#198) | G4 | 1 | |
| 4b | [tasks/04b-era-map-ratify-and-build-order.md](tasks/04b-era-map-ratify-and-build-order.md) | Era-map guards — `ratify`, and the one build after a decision change (#198) | G4 | 4a | |
| 4c | [tasks/04c-review-batch-page.md](tasks/04c-review-batch-page.md) | Era-map guards — the owner review page (#198) | G4 | 4b | |
| 5 | [tasks/05-link-coverage-fails-closed.md](tasks/05-link-coverage-fails-closed.md) | link-coverage fails closed (#200) | G4 | 1 | |
| 6 | [tasks/06-route-safe-seed-and-loader.md](tasks/06-route-safe-seed-and-loader.md) | Route-safe seed, loader alias and the R-1 restatement rule (#194) | G2 | 3, 4a | |
| 7 | [tasks/07-s194-chem-demil-write-script.md](tasks/07-s194-chem-demil-write-script.md) | The Chem Demil write script `s194_chem_demil.py` (`--check` / `--dry-run` / `--apply` / `--revert`); retire `clean_junk_pe_bli.py` (#194) | G2 | 3, 6 | |
| 8 | [tasks/08-map-alias.md](tasks/08-map-alias.md) | Map alias — `p1_era_line_map.program_key` from the route-safe seed, `era_map` load/classify alias, UNSAFE narrowed to (0390D, RDT&E) (#194) | G2 | 4a, 6 | |
| 9a | [tasks/09a-map-decided-on.md](tasks/09a-map-decided-on.md) | `decided_on` on `p1_era_line_map`, proved by verify-era-map leg b (#206 T6) | G3 | 4, 6, 8 | |
| 9b | [tasks/09b-era-regex-and-collision-pins.md](tasks/09b-era-regex-and-collision-pins.md) | One full era-key regex at every site, both collision pins, the unplanted era legs (#203) | G3 | 9a | |
| 9c | [tasks/09c-verify-era-map-cli-and-leg-tests.md](tasks/09c-verify-era-map-cli-and-leg-tests.md) | verify-era-map exits 2 on a bad `--legs`; leg a and leg b failure branches tested (#203) | G3 | 9b | |
| 10 | [tasks/10-owner-batch-b7.md](tasks/10-owner-batch-b7.md) | Owner batch B7 — the era O&M chain joins 0390DOM (#194; the owner has already answered) | G2 | 4, 8, 9 | |
| 11 | [tasks/11-verify-era-map-legs-g-h.md](tasks/11-verify-era-map-legs-g-h.md) | verify-era-map legs g (era minters) and h (era book diffs) (#206 T11) | G3 | 9 | |
| 12 | [tasks/12-om-page-presentation.md](tasks/12-om-page-presentation.md) | The O&M page — printed code, "O&M" badge, the restated RDT&E line, the map scope, and the receipt matcher accepts the alias (#194) | G2 | 6, 8 (page appears after 22) | |
| 13 | [tasks/13-years-exporter-split.md](tasks/13-years-exporter-split.md) | /years/ exporter — a core and two lazy shards, a compact writer measured on its own bytes, the era fence lifted, organization-split rows fixed (#193, #207) | G1 | 1, 2 | |
| 14 | [tasks/14-years-island-lazy-shards.md](tasks/14-years-island-lazy-shards.md) | /years/ island — the core on open, each shard when a reader asks, the gap tooltip and edition legend restated, /agency/ looks decade cells up by slug (#193, #208, Q12–Q14) | G1 | 13 | |
| 15 | [tasks/15-years-gates.md](tasks/15-years-gates.md) | /years/ gates — the merged-view loader and size budgets, leg g through the era map, leg j sidecar parity, leg k lazy opening, the live probe, the Q13 clause swap, the spec §6.2 amendment (#193, #206 T4) | G1 | 13, 14 | |
| 16 | [tasks/16-required-era-grain-fids.md](tasks/16-required-era-grain-fids.md) | Required `era_grain_fids` and the `build_lineage_flow` invariant (#204) | G4 | 13 | |
| 17 | [tasks/17-v1-receipt-removal.md](tasks/17-v1-receipt-removal.md) | Remove the v1 PDF receipt writer, its unread seed and its 256 shards; ship only v2/ (#196) | G3 | 1 | |
| 18 | [tasks/18-search-aliases.md](tasks/18-search-aliases.md) | Search aliases JASSM and C-130J route as #55 did; a cross-seed membership test (#197) | G3 | 1 | |
| 19 | [tasks/19-tier-pending-copy.md](tasks/19-tier-pending-copy.md) | One definition of "citation tier pending"; claims narrowed to dollar figures (#206 T7, Q16) | G3 | 1 | |
| 20a | [tasks/20a-f015e0-gloss-and-capture-tool.md](tasks/20a-f015e0-gloss-and-capture-tool.md) | The F015E0 gloss names its exhibit; the F-15 capture tool round-trips and writes atomically (#206 T9, #201) | G3 | 1 | |
| 20b | [tasks/20b-direct-run-and-verify-notes.md](tasks/20b-direct-run-and-verify-notes.md) | Site scripts' direct-run guards compare real paths; `npm run verify` shows every note on request (#201) | G3 | 20a | |
| 20c | [tasks/20c-f15-page-name-gate-snapshot.md](tasks/20c-f15-page-name-gate-snapshot.md) | /families/f-15/ names the noted row without its link; the gate checks the note's link and receipt; the snapshot reads the prose (#201, Q21, #206 T9) | G3 | 20b | |
| 21a | [tasks/21a-proof-tools-pins-and-parity.md](tasks/21a-proof-tools-pins-and-parity.md) | Release-1 proof tools — snapshot pins and lake parity | G5 | 2 | |
| 21b | [tasks/21b-proof-tools-fact-delta-and-years.md](tasks/21b-proof-tools-fact-delta-and-years.md) | Release-1 proof tools — fact delta and the /years/ shard proof (P2b) | G5 | 2, 13, 21a | |
| 21c | [tasks/21c-proof-rule-files.md](tasks/21c-proof-rule-files.md) | Release-1 expected-difference rule files (P1, P2, release state) | G5 | 21b | |
| 21d | [tasks/21d-proof-preconditions-and-snapshots.md](tasks/21d-proof-preconditions-and-snapshots.md) | Release-1 proof — preconditions, the A worktree, W1, and snapshots fu-pre/fu-post | G5 | 1–20, 21a–21c | |
| 21e | [tasks/21e-proof-rehearsed-writes.md](tasks/21e-proof-rehearsed-writes.md) | Release-1 proof — the Chem Demil write (one `--apply`, revert file kept), export-facts and the selective dbt build on fu-post | G5 | 21d | |
| 21f | [tasks/21f-proof-exports-and-diffs.md](tasks/21f-proof-exports-and-diffs.md) | Release-1 proof — the four exports, the write-and-revert rehearsal on fu-pre, the abort-path rehearsal, the control, P2 (code), P2b (/years/) and P1 (lake) | G5 | 21e | |
| 21g | [tasks/21g-proof-f15-repin-and-gates.md](tasks/21g-proof-f15-repin-and-gates.md) | Release-1 proof — P3 F-15 history re-pin, and the Python gates and V9 on B@fu-post | G5 | 21f | |
| 21h | [tasks/21h-proof-site-build-and-weights.md](tasks/21h-proof-site-build-and-weights.md) | Release-1 proof — site build on B@fu-post, the F-15 page snapshot, `npm run verify`, page weights, sitemap | G5 | 21g | |
| 21i | [tasks/21i-proof-note.md](tasks/21i-proof-note.md) | Release-1 proof note | G5 | 21h | |
| 22a | [tasks/22a-release-preconditions.md](tasks/22a-release-preconditions.md) | Release 1 — preconditions: the live lake still equals fu-pre | G5 | 21 | |
| 22b | [tasks/22b-release-live-writes.md](tasks/22b-release-live-writes.md) | Release 1 — the live writes (Chem Demil with its pre-image, export-facts, the selective dbt build), live = fu-post, and the abort path (before and after a deploy) | G5 | 22a | ★ go-ahead before the live Postgres write (Step 2) |
| 22c | [tasks/22c-release-export-and-checks.md](tasks/22c-release-export-and-checks.md) | Release 1 — the release export, its counts and fingerprint, and the release-state checks | G5 | 22b | |
| 22d | [tasks/22d-release-deploy.md](tasks/22d-release-deploy.md) | Release 1 — `llms.txt`, build, W4, verify-phase5, the owner's go-ahead, deploy, live checks | G5 | 22c | ★ deploy go-ahead (Step 5: §4.7 totals, Q15 told/measured, `SAM_D`) |
| 22e | [tasks/22e-release-stamp-and-publish.md](tasks/22e-release-stamp-and-publish.md) | Release 1 — ROADMAP stamp (Q15, Q23 filed for piece 2), publish, report and cleanup offer | G5 | 22d | ★ publish go-ahead (Step 6); cleanup only on a yes |
| 23a | [tasks/23a-narrative-book-set-relocation.md](tasks/23a-narrative-book-set-relocation.md) | #195 — migration 022 and the book-set relocation in `provenance_pages` | G6 | 22 | |
| 23b | [tasks/23b-export-cites-printing-volume.md](tasks/23b-export-cites-printing-volume.md) | #195 — the export cites, and hosts, the volume that prints each narrative | G6 | 23a | |
| 23c | [tasks/23c-s195-write-script.md](tasks/23c-s195-write-script.md) | #195 — the write script `s195_narratives.py` (`--digest` / `--check` / `--apply` / `--dry-run` / `--revert`) and the read-only measurement | G6 | 23b | |
| 24 | [tasks/24-verify-jbook-narratives.md](tasks/24-verify-jbook-narratives.md) | #195 — `verify-jbook-narratives`, the printed-in check (verify-phase5b1 gate 5) | G6 | 23 | ★ the second ratchet, 77 (Step 0, before anything is written) |
| 25a | [tasks/25a-release2-proof-tools.md](tasks/25a-release2-proof-tools.md) | Release-2 proof tools — the relocation report and the P1 rule list | G6 | 24 | |
| 25b | [tasks/25b-release2-proof-run.md](tasks/25b-release2-proof-run.md) | Release-2 proof — one snapshot, the rehearsed writes, four exports, P2 and P1 | G6 | 25a | |
| 25c | [tasks/25c-release2-proof-gates.md](tasks/25c-release2-proof-gates.md) | Release-2 proof — gates on B, the `--revert` rehearsal, the site build and weights, the proof note | G6 | 25b | |
| 26a | [tasks/26a-release2-writes-export-gates.md](tasks/26a-release2-writes-export-gates.md) | ★ Release 2 (#195) — the owner's go-ahead, live writes, export, release-state checks, gates, build | G6 | 25 | ★ go-ahead before the live writes (Step 2b) |
| 26b | [tasks/26b-release2-deploy-stamp-publish.md](tasks/26b-release2-deploy-stamp-publish.md) | ★ Release 2 (#195) — dry run, the owner's go-ahead, deploy with the R2 upload, live checks, ROADMAP stamp, publish | G6 | 26a | ★ deploy go-ahead (Step 3: R2 upload, heaviest page, 111 and 77); ★ publish go-ahead (Step 7) |

**Order.**
- **Task 1 first.**
- **Hardening.** Then 2a → 2b → 2c, 4a → 4b → 4c, and 3 and 5. Tasks 3, 4 and 5 are independent of one another.
- **Chem Demil and the map.**
  - 6 runs after 3 and 4a, then 7.
  - 8 runs after 4a and 6, then 9a → 9b → 9c.
  - 10 runs after 4b, 4c, 8 and 9, then 11.
  - 12 runs after 6 and 8.

  The research order holds: the map code and T6 first, then #194's write and B7, then /years/, so the /years/ proof measures final content.
- **/years/.** 13 → 14 → 15, and 16 after 13.
- **Independent after Task 1:** 17, 18, 19 and 20a → 20b → 20c. The F-15 red window opens at 20a.
- **Proof tools.** 21a → 21b → 21c may run once 2 (and, for 21b, 13) has landed.
- **The proof.** 21d → 21e → 21f → 21g → 21h → 21i, once Tasks 1–20 are committed.
- **Release 1.** 22a → 22b → 22c → 22d → 22e.
- **Release 2.** 23a → 23b → 23c → 24 → 25a → 25b → 25c → 26a → 26b, only after release 1 is deployed and published.
