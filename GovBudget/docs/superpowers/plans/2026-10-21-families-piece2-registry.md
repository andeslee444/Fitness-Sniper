# Families Piece 2 (the Family Registry) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-coded F-15 family constants with one reviewed family registry (three `data-seeds/` files, a loader that fails loudly in three stages, one generic history builder inside `export_site`), rebuild the F-15 on it byte for byte, and record the F-35 as an owner-reviewed, unpublished entry #2, with readers seeing no change.

**Architecture:** `platform_families.py` holds the formats, the loader (stage 1 files, stage 2 the lake read-only, stage 3 the citation registry) and the one-off F-15 seed. `platform_family_history.py` is the generic builder plus the export post-pass that also writes `json/families/index.json`. `f15_funding_history.py` becomes a facade derived from the registry, `platform_family_review.py` and the `platform-families` CLI run propose → render (with a draft preview) → answer → ratify, and `verify-families` joins the `verify-phase5` assembly. The proof is piece 1's: A (the deployed code) and B (piece 2) export one pinned snapshot `fam2`, and the diff may hold only §16's two paths.

**Tech Stack:** Python 3.12 (uv; DuckDB 1.5 opened `read_only`, pypdf through `provenance_pages._page_texts`, openpyxl), dbt-duckdb (`dbt parse` only), PostgreSQL 17 (the 55432 test cluster; the scratch databases `govbudget proof snapshot` makes), Next.js 16 / React 19 / vitest 3.2.6 / typescript 5.9.3, the site gate registry (`npm run verify`), `scripts/launch/deploy.sh`.

**Spec:** `docs/superpowers/specs/2026-10-20-families-piece2-registry-design.md`, approved by the owner on 2026-10-21 with "approved, would process with recommendation to approve all" (that message is R-DEC-FAM-F15-SEED's `owner_reply`). Appendix A's tasks are renumbered per D2. Conventions follow `docs/superpowers/plans/2026-10-04-families-piece1-followups/README.md` and `docs/superpowers/plans/2026-10-02-era-procurement-history/README.md`.

## Global Constraints

### Workspace and shell

- **Toplevel** `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families`, branch `piece2-2026-10-20`: main `88538c6a`, then the spec `23dcb83b`, then the contract-link fix (round 1 `be256625`, `391eb1d6`, `b30134c4`; round 2 `5c751627`, `893f9a8b`, `5d567272`, `b6b68d82`, `9acf0c78`, approved by review r2-2; its minors `4504be40`, `f308589c`, `8e23089b`, `b6c9a8d9` for review r2 M-1 to M-4; round 3 `79a81125`, `372a496c`, `9a50e28b` for the owner's R-DEC-LINK-2026-10-21-B, and its review fixes `4e505dc3`, `b47c11b9`, `31b1e47b`; and any later link-fix commit before its release). Under D1 the link fix releases first and `main` fast-forwards to its release commit, which is A. The project is `GovBudget/`; every path in this plan is relative to it unless absolute.
- **Block start:** `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh` (multi-line blocks end that line with `|| exit 1`). Shell state does not persist: re-derive every variable (`P`, `L`, `A`, `FAM2_DUCKDB`, `FAM2_SITE`, …) in every block. Destructive cleanups expand `${VAR:?}`. Commit, toplevel-git and `deploy.sh` blocks are exempt.
- **`env.sh`** exports `GOVBUDGET_DATA`, `GOVBUDGET_DUCKDB`, `GOVBUDGET_PG_DSN=postgresql://localhost/govbudget`, `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres`, `GOVBUDGET_PG_BIN` and `GOVBUDGET_PROOFS=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs`. `config.py` derives the DuckDB path from `GOVBUDGET_DATA`; a snapshot is used through its own `source <snapshot>/env.sh [RUN_DIR]`.
- **SAM window:** the hourly job writes `data/parquet/sam` at :17. Start no step that reads or writes the live lake (read-only included) during :15–:20. Guarded blocks carry, right after the block start, `MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi`; on `WAIT`, re-run the whole block from :23. Release exports run :21–:45 with the SAM mtime check. A snapshot, its clones and `dbt parse` are exempt. The full pytest suite is not exempt. Under `env.sh` it opens the live DuckDB read-only (`tests/test_collision_keys.py:80-83` and `tests/analyst/test_schema_card.py:317-332` read `config.DUCKDB_PATH`) and runs about 10 minutes (the link fix's runbook times its Step P0, which runs it, at ~10 min). So the blocks that run it (Task 1 Step 3, Task 9b Step 6, Task 10a Step 1) start only between :23 and :59 and print the minute pytest ended.
- **Python** runs as `uv run --project . <cmd>` from `GovBudget/`; **site** commands are `npm` in `GovBudget/site`; `site/node_modules` is a real directory from `npm ci`; the worktree needs its own `dbt parse` manifest; site builds read `data/site` through the `data/*` symlinks, and proofs repoint them and put them back.
- **Tests** never touch the real database: pytest that can reach Postgres carries `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres` inline; run one task's pytest at a time; a Postgres-only failure gets one re-run on a quiet cluster.
- **zsh** does not word-split an unquoted parameter: pass lists as arrays (`"${ARGS[@]}"`) and single-quote pathspecs that contain `[` or `*`.
- **Lake parquet `fiscal_year` is VARCHAR:** cast it (`cast(fiscal_year as integer)`) in every query against `budget_lines.parquet`.
- **"Could not set lock on file"** means another process holds the DuckDB file: wait and re-run. Tools report it as a tool error (exit 2), never as FAIL.
- **dbt:** piece 2 runs only `dbt parse` (this worktree and the A worktree); any dbt log check greps `Done\. PASS`.
- **W1 lint** `uvx --offline ruff check --isolated --select F,E9` finds nothing beyond the baselines re-measured 2026-10-21 at `b6c9a8d9` and again at `9a50e28b`, which `31b1e47b` keeps (its review fixes touch only `site/`) (the same at `88538c6a`, `b30134c4` and `9acf0c78`: the link fix moved no count): `cli.py` 5, `export_site.py` 10, `verify_phase5.py` 2, every other touched or new module 0.
- **Module paths:** `era_map`, `era_keys` and `collision_keys` are `govbudget.jbooks.era_map`, `govbudget.jbooks.era_keys` and `govbudget.jbooks.collision_keys`.

### Commits and publishing

- **Commits** use `--author="Andes Lee <andes.lee444@gmail.com>"`, end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and run from the toplevel with explicit pathspecs (`git add GovBudget/<path>`). Never `git stash`.
- **Never** commit or delete any untracked `data/research/eval-runs/eval-*.json` (spec §5.3). Three were there on 2026-10-21: `eval-20261004T203052Z.json`, `eval-20261015T023059Z.json` and `eval-20261016T033053Z.json`. Every `verify-phase5` run with the paid eval adds one, because `verify_phase5.py` writes `config.RESEARCH_DIR/eval-runs/eval-<UTC>.json` and `RESEARCH_DIR` is this checkout's `data/research`. That includes the link fix's release Step R11, Task 9b Step 3 and Task 10a Step 7, all run from this worktree. "Worktree is clean" checks ignore `??`.
- **Never** push the branch to `origin`. Publishing (Task 10c, after the go-ahead) is `git subtree split --prefix=GovBudget` from the toplevel, then merge `govbudget/main` into the split, then push to `govbudget` `main`.
- **Deploy** only `./scripts/launch/deploy.sh` by absolute path from this worktree, never from the main checkout.
- The other session's branch `wip/other-session-families-layout-2026-09-29` is read-only prior art; nothing merges from it.

### Data safety and proof state

- **Piece 2 writes nothing** to the lake, DuckDB, dbt, the parquet tree or Postgres: no dbt seed, model or migration. Stage 2 opens DuckDB with `read_only=True`.
- **Scratch databases** `govbudget_proof_fam2` and `govbudget_proof_fam2_rel` are created and dropped only by `govbudget proof snapshot`, the Task 10c cleanup on a yes, and Task 10a's re-take on the owner's yes (Step 1's stale-proof branch and Step 2's `DIFFERENT` branch). Never create, alter or drop any other database.
- **Never use `/private/tmp`** for durable state: proof state goes under `$GOVBUDGET_PROOFS`, notes in the ledger `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2/` (`progress.md`, `work/`, `proof-logs/`, `b1-preview.md`), transients in the git-ignored `GovBudget/tmp/`.
- **Byte identity** is proven only on the pinned snapshot fam2 (A vs B vs the control B2, timestamps masked), never on the live lake or by an idempotent re-run.
- **fam2 carries the link fix's warehouse objects.** The link fix's live dbt build adds the seed `link_line_rulings` and the model `link_award_keys` (a table, `dbt_project.yml`). Since round 2 (`5d567272`), `export_site._require_link_award_keys` raises `link_award_keys is missing or incomplete …`. It does so when a warehouse has the award lake (`fct_award_transactions`) and district rows, but not that model with the columns `award_piid, recipient_uei, award_unique_key, n_awards, named`. Since M-3 (`8e23089b`), `flow_chart.build_flow_chart` calls the same guard whenever a high link exists. Both A's and B's code carry the guard. So the snapshot (Task 1 Step 5) and its clones `fam2-A`, `fam2-B` and `fam2-B2` (APFS copies of the same DuckDB file) must hold both objects, or every export stops. So must the live lake that Task 10a Step 5 exports from; `fam2-rel` is not a clone but a fresh release-time snapshot of that lake (D15, Task 10a Step 2), on which no export runs. The live DuckDB held neither before the link fix's release (probed read-only 2026-10-21 03:40: `link_award_keys` raised `CatalogException`).

### F-15 freeze

- **The pin:** `json/f15_funding_history.json` sha256 `d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f` (`tests/fixtures/f15/history.sha256`, 139,061 B) never changes.
- **Byte-unchanged on the branch:** `tests/test_f15_funding_history.py` (21 functions, 34 items), `tests/test_f15_era_identity.py` (4), `tests/test_capture_f15_fixtures.py` (5) — 43 collected items in all — plus `tests/fixtures/f15/*`, `tests/test_verify_era_map*.py`, `tests/test_export_era_line_map.py`, `site/scripts/gates/__tests__/f15-page-snapshot.test.mjs`, every F-15 TypeScript file, `src/govbudget/verify_era_map.py`, `scripts/era/capture_f15_fixtures.py` and `scripts/era/review_batch_page.py`; checked with `git diff --quiet <A> -- …`.
- **Frozen fact-ID inputs:** the 31 `family_history` IDs keyed `f-15|…`, the 27 `family_program_history` IDs keyed `{program_id}|…`, the 11 reused `decade` receipts, the dataset token `f15_funding_history`, the formula strings, the reuse allow-list and member order.
- **If stage-3 leaf expansion fires on the F-15:** stop and report; never weaken the check, never change F-15 bytes.
- **Page weight:** never raise a page-weight ceiling. `/families/f-15/` was 705,056 / 69,328 on the `1256ec35` build, against 725,000 / 70,000 (`build.mjs:288`). Task 1 records A's build as `base-weight:`, and piece 2 adds zero bytes to it. Of the page sources, the link fix's release changes only /about/ and /methodology/. Its release step P12 also re-stamps the /methodology/ entry's `measured:` text in `build.mjs`, with the ceiling unchanged. It leaves /methodology/ the tightest page, about 38 gzip bytes under 162,000 / 45,400. These are the link fix's own figures, and its release's P12 re-measures them:
  - round 2 measured 161,455 / 45,362 on the `9acf0c78` build of the pre-release export (fix-report "Round 2 fix 1");
  - round 3 estimated the same 45,362 with the fpds-ap figure its release prints (fix-report §R3-5; 45,361 on its `9a50e28b` build of the pre-release export).

  The /methodology/ source is unchanged through `31b1e47b`. After round 3 (R-DEC-LINK-2026-10-21-B-C1), A's export prints fpds-ap 86/111, the same length as 89/114 and 87/112. Piece 2 changes no page source and no field a page renders, so every page weighs what A's build of the same export weighs. Task 9b Step 5 compares both pages with the build ID and export stamps masked. A gate-1 failure that A's build shares is the link fix's: stop and report.
- **Piece 2 changes** no F-15 TypeScript, page, editorial layer, fact ID, `p1_era_line_map` scope sentence or `verify_era_map.py` code. The scope sentence is "Only a same_program line whose code has a program page, or an F-15 family-history line, has those rows and citations." It sits in the `"p1_era_line_map": (` entry of `export_site.py`: `:1850-1862`, with its comment from `:1829`, at `b6c9a8d9`. It was `:1787-1799` and `:1766` at `88538c6a` and `b30134c4`; round 2's `5d567272` added 61 lines above it and M-3's docstring 2 more. Anchor on the quoted text.

### Names

- New fields and artifacts use `platform_family`, never a bare `family_id`; family ids are `f-15` and `f-35`.
- Frozen for the F-15: `short_name` `F-15`, `history_dataset` `f15_funding_history`, the `member_id` spellings (era org `AF`, `NAVY`) and the `display_title` strings.

### Owner rules

- **Owner rulings** carry `decided_by=owner` and a verbatim, non-empty `owner_reply`. `R-DEC-FAM-F15-SEED`: "approved, would process with recommendation to approve all", `decided_on` 2026-10-21, `seed_basis` true (the only one allowed).
- **Nothing is published** without an owner ruling: only the F-15 seed writes `published` directly, a family leaves `draft` only through `ratify`, and the F-35 (`draft` or `ratified`) appears nowhere in `data/site`.
- **★ Owner touchpoints:** B1's answer (Task 8b), the deploy go-ahead naming "readers see no change" and `SAM_D` (Task 10b), the publish go-ahead (Task 10c), and the cleanup (on a yes only). If Task 10a Step 1 or 2 finds the proof stale, removing proof state for a re-take is also an owner stop (on a yes only).
- **Readers see nothing:** `prepare-assets.mjs` never copies `index.json`, and `upload_r2.sh` sends only `pdfs/`, `data/`, `workbooks/` and `citations/`; live `/json/families/index.json` returns 404.
- **Publish the smaller true number:** an exclusion stores only a cited `size_text`, never summed; F-35 spares is "$766.3M in FY2024", never the inferred ~$6.3B. **Every figure traces to a citation**, and `index.json` carries no amounts.
- **No PB2027 ingestion** during piece 2.
- **#209** stays open, re-deferred to piece 4. ROADMAP entries are never reworded (new Status above, old relabelled `**Status (<date>):**`), and `tests/test_roadmap_backlog.py` changes in the stamp's commit.

### Conventions

- **CLI:** a tool error prints `<tool>: ERROR — <message>` and exits 2; a failed check exits 1; verify CLIs end with `verify-<name>: PASS|FAIL`.
- **Ledger dates:** a finding or owner answer keeps its own date; a re-read figure says "re-measured 2026-10-21"; a stamp, deploy, rollback tag or proof note carries the day its step runs.
- **Line numbers** are hints at `b6c9a8d9` (re-based 2026-10-21 from `b30134c4`). Of the files this plan edits or cites by line, the link fix moved only two:
  - `export_site.py`: +63 past line 830. Round 2's `_require_link_award_keys` and `_named_link_awards_sql`, inserted after `_fetch_program_identity`, added 61; M-3's docstring added 2;
  - `site/scripts/gates/program-skeleton.mjs`: its header, import and leg calls by +2 or +3, and leg (q)'s block at the end of the file (grown again by M-2).

  Round 3 (`79a81125`, `372a496c`, `9a50e28b`) moved only one anchor this plan cites: the end of leg (q)'s block, from `:4476` to `:4481`. `export_site.py` lines 1–4400 are identical at `b6c9a8d9` and `9a50e28b`, because round 3's export edits are comments and docstrings at `:4426` and `:4686` onwards. Every other hint at `b6c9a8d9` holds at `9a50e28b`. Round 3 also touched no test file whose count this plan pins. Its test edits are `tests/test_dbt_link_line_rulings.py`, `tests/test_export_site_line_ruling_precision.py` and three site tests. So every count pinned "at `b6c9a8d9`" holds at `9a50e28b` (checked with `git diff --quiet b6c9a8d9 9a50e28b -- <those files>`).
  Round 3's review fixes (`4e505dc3`, `b47c11b9`, `31b1e47b`) touch only `site/`: /about/, leg (q) and their two tests. They move one anchor this plan cites, the end of leg (q)'s block again, from `:4481` to `:4532`. `git diff --stat 9a50e28b 31b1e47b -- GovBudget/src GovBudget/tests GovBudget/dbt GovBudget/docs/superpowers/ROADMAP.md` is empty, so every other hint and every pinned count holds at `31b1e47b`.
  Anchor on the quoted text.

### Known red windows (expected; nothing else may be red)

- **K1, leg (r).** From Task 7e's commit until Task 10a's release export, `npm run verify` against the live `data/site` fails gate 21 (`program-skeleton`) leg (r), because the A-code export (the link fix's release) has no `json/families/index.json`. Gate 21's leg (q), the link fix's, passes on that export. Gate 24 (`datatruth`) has an unrelated leg r of its own (D8). Run the full site verify only on Task 9b's B@fam2 build and Task 10a's release build.
- **K2, `verify-families` leg c.** From Task 7a's commit until Task 10a's release export, live `verify-families` leg c, and so `verify-phase5`'s assembly, fail with `json/families/index.json is missing`. Run them on the fam2-B clone (Task 9b) until Task 10a Step 7.

### Binding decisions (they override a task's wording)

- **D1. Sequencing with the contract-link fix: ruled `link-fix-first`.** The controller ruled this on 2026-10-21, following the owner's order "yes please do in order and run in parallel when possible" (the link fix first, then piece 2). It is recorded in the ledger `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2/owner-decisions.md`, section "2026-10-21: piece-2 plan D1 (controller)".
  - **The link fix's commits on this branch:**
    - round 1: `be256625` (dbt seed `link_line_rulings.csv` and four dbt tests), `391eb1d6` (export) and `b30134c4` (program-skeleton leg (q) and /about/);
    - round 2: `5c751627` (the 10 F03500 holds, which round 3 withdrew), `893f9a8b` (gate (a)'s recall note), `5d567272` (the dbt model `link_award_keys`, the re-keyed district, feed and concentration marts, and `export_site`'s `_named_link_awards_sql` and `_require_link_award_keys`, plus `flow_chart`'s bridge families), `b6b68d82` and `9acf0c78` (the /methodology/ precision clause, the /about/ collision sentence, and leg (q) on citations and the N0001922F0001 pins);
    - its minors, review r2 M-1 to M-4 (controller rulings, owner-decisions.md):
      - `4504be40`: /about/ prints the collision order at its net $147.0 million;
      - `f308589c`: leg (q) pins N0001922F0001 at IN-07;
      - `8e23089b`: `flow_chart`'s bridge families call `_require_link_award_keys`, or log a drop;
      - `b6c9a8d9`: gate 24 leg r always samples IN-07 FY2022;
    - round 3, under the owner's R-DEC-LINK-2026-10-21-B ("proceed with recommendations") and the controller's -B-C1 (owner-decisions.md, "2026-10-21: owner reply"):
      - `79a81125`: the seed withdraws the 10 held F03500 production-support pairs, so 51 pairs are withdrawn in all;
      - `372a496c`: export_site's comments and docstrings only, recording that fpds-ap goes 87/112 → 86/111;
      - `9a50e28b`: /about/ counts 51 withdrawn links in three species, and leg (q)'s floor rises to 51;
      - its review fixes (reviews r3-1a and r3-1b): `4e505dc3` (/about/ calls the B ruling's 10 links contracts or orders, as FPDS records them), `b47c11b9` (leg (q) names each withdrawn pair's own ruling and holds /about/'s line name to its title) and `31b1e47b` (/about/ dates the correction to the owner rulings);
    - any later link-fix commit before its release (for example, from its release runbook: the /methodology/ weight re-stamp in `build.mjs` (P12), the eval refresh (R8), `llms.txt` (R9) or the ROADMAP stamp (R16)). A is whatever `main` fast-forwards to.
  - **The order.** The link fix releases on its own proof and deploy, and `main` fast-forwards to its release commit. So A = `git merge-base main HEAD` is that commit, and fam2 is taken after its live dbt build (`link_line_rulings` and `link_award_keys` in the live warehouse). Task 1 Step 1 proves this and writes the `D1:` line in `progress.md`.
  - **Not taken:** `joint` (both on one release). It would have needed an owner-approved spec amendment, because §16 would gain the link fix's differences.
- **D2. Renumbering** (spec §18 allows it): spec 2 → 2a (formats, per-row rules) + 2b (cross-row rules); spec 5's stage 2 → 2c, so the seed can refuse a stage-2 failure; spec 3 → 3a (seed) + 3b (facade); spec 7 → 7a–7e; spec 8 → 8a + 8b★; spec 9 → 9a + 9b (proof note in 9b); spec 10 → 10a + 10b★ + 10c★. Task 6 runs before Task 5 (stage 3 calls its grammar) and is placed before it here.
- **D3. Modules:** `platform_families.py` (formats, vocabularies, `RegistryError`, stages 1–3, measurement, writers, the one-off seed); `platform_family_history.py` (builder, post-pass); `platform_family_review.py` (new: propose, preview, render, answer, ratify, the batch page); `verify_families.py` (new: the verify legs, mirroring `verify_era_map.py`). `scripts/era/review_batch_page.py` stays untouched; the new page copies its look.
- **D4. Receipt tails insert `short_name` verbatim, never `re.escape(short_name)`.** `re.escape("F-15")` is `F\-15` (Python 3.12.13), which would break §11's exact string equality; stage-1 rule 3 admits no character that is special outside a character class.
- **D5. A code-keyed member** is an approved `counted` row with a non-empty `titles_seen` (F-15: 0207134F, 0207146F, 0207171F, F01500, F015EX, F15EWS, exactly today's `MODERN_MEMBERS` keys). **The partial-corpus gate:** every code-keyed counted code must be in `fct_decade_series.pe_bli`. `corpus_gate` returns True (build), False (`skip`, the F-15 today) or raises (`raise`) `{short_name} family history requires every counted workbook member: missing {codes}`.
- **D6. All published families build, or none does.** None builds → return None and write nothing (`index.json` included); one skips while another builds → `RegistryError` (piece 4 revisits, spec §17 risk 4).
- **D7. `index_projection(registry)`:** `families` = `registry.published()` in JSON order, each with the keys `history`, `history_dataset`, `members`, `platform_family`, `route`, `ruling_ids`, `short_name`; `members` = approved counted rows in `member_order`, then approved context rows by `member_id`, each `{member_id, page_slug (null when blank), role}`; `ruling_ids` = the sorted distinct union of `published_ruling_id` and the listed rows' `ruling_id`; `_json_bytes` serialization. Only the full export pass writes it (never the facade path or a preview). For the committed F-15 it is 833 bytes, sha256 `3657d3bd36fa8f344cf2c299714dacb11fe227100cd1ff0c3d3d22f6734f1945` (spec §12's example).
- **D8. The site gate leg is gate 21 (`program-skeleton`) leg (r).** The link fix took (q) in `b30134c4`, round 2 extended it in `b6b68d82`, and M-2 extended it again in `f308589c`. At `b6c9a8d9`, `9a50e28b` and `31b1e47b`, gate 21 has no (r) in its header or code. The leg is implemented as `checkFamilyIndex` in `site/scripts/gates/family-history.mjs`. Leg p is unchanged. It fails closed on a missing or empty index (K1).
  - **Gate 24 (`datatruth.mjs`) is a different gate** with its own lettering:
    - its leg q is "announcement LLM-alias pass scope";
    - its leg r is "district by-year cells recomputed from the lake" (ROADMAP #6). Its helper `districtyear-recompute.py` was re-keyed by the link fix's round 2, and M-4 (`b6c9a8d9`) makes the leg always sample `IN-07|2022`.
    Piece 2 touches neither of gate 24's legs.
  - **Telling them apart.** Gate 21's leg (r) errors carry the prefix `program-skeleton(r): `. Its note reads `leg r: <n> family index entr…`, as gate 21's leg p note reads `leg p: …` (leg q's reads `line rulings: …`), and both gates' notes print only on their own `gate <n> <name>:` line. So a log check names the gate (`gate 21 program-skeleton`), never a bare `leg r`.
- **D9. The leak scan** (`verify-families` leg c), for every non-published family: the needles `history_dataset`, `{platform_family}|` and `reviewed {short_name} members` in every `*.json` under `data/site` and in every VARCHAR column of `citations/citations.parquet` (27 columns, 19 VARCHAR, no `dataset` column; re-measured 2026-10-21), plus the file `json/{history_dataset}.json`, plus a control that each published family's formula needle matches at least one row.
- **D10. Batch artifacts:** the page and manifest `tmp/platform-families/<pf>/B<n>.{html,json}` (git-ignored); the owner's answer `data/research/platform_families/<pf>/batches/B<n>.json` (committed); the B1 reference `data/research/platform_families/f-35/reference-b1.json` (committed); the preview scratch `<snapshot dir>-preview-<pf>-B<n>` beside the snapshot (`$GOVBUDGET_PROOFS/fam2-preview-f-35-B1`; `render --preview-out` overrides), never committed and never under `data/site`. **`family_sha256`** = sha256 of `json.dumps({"family": <family object>, "sources": [<cited sources sorted by source_id>]}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, where the cited sources are those named by `src:` refs in the object's `exclusions[].evidence`; sources cited only by review rows are covered by `review_sha256`.
- **D11. Serialization:** `platform_families.json` = `json.dumps(doc, indent=2, ensure_ascii=False) + "\n"`, keys in §7.2 order, families in output order; CSVs through `csv` with `lineterminator="\n"` and `QUOTE_MINIMAL`, members sorted by `member_row_id`, era lines by (`platform_family`, `edition`, `era_key`); every multi-file write is one `era_map._atomic_write_texts` call (`registry_texts` supplies the three registry texts).
- **D12. Lake flags:** `render` and `preview` require `--duckdb` and `--site-dir`; `ratify` and `check` default them to `config.DUCKDB_PATH` and `config.SITE_DIR`; `propose` takes `--duckdb` only (its `--site-dir` belongs to `--seed-shipped`; `doc:` refs are checked in Task 8a Step 3 and by `render`'s preview, stage 2 item 7). Piece 2 runs propose, render and ratify against fam2; Task 10a runs `check --strict` against the live lake.
- **D13. The F-15 seed's owner reply** is the committed file `data/research/platform_families/f-15/owner-reply-R-DEC-FAM-F15-SEED.txt`: exactly `approved, would process with recommendation to approve all` plus one newline; the seed strips exactly one trailing `\n`; `decided_on` is `2026-10-21`.
- **D14.** `short_name` is never used as a regex without D4's guard; no other module builds a regex from registry text.
- **D15. Proof-state names** (all under the `fam2*` glob; none collides with `fu-*`/`fu2*`): the snapshot `.proofs/fam2` (database `govbudget_proof_fam2`); the clones `fam2-A`, `fam2-B`, `fam2-B2`; the logs `fam2-logs/` (noise file `fam2-logs/noise-B-B2.json`); the release snapshot `.proofs/fam2-rel` (database `govbudget_proof_fam2_rel`); the release copies `.proofs/fam2-release-pre-site`, `fam2-release-export.sha256` and `fam2-release-export.built_at`; the preview scratch `fam2-preview-f-35-B1`; the never-created dbt-parse probes `fam2-dbt-parse-{a,b}.duckdb`; the A worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fam2-proof-a` (detached at A); local refs `publish-fam2*`.

### Contract resolutions (assembly, 2026-10-21; they amend the drafting outline)

- **R1. Independent-signal bar.** In piece 2 a `fact:` ref never satisfies the bar: stage 1 cannot tell a member's own narrative from another line's book text without the export. This is narrower than §7.5's "a non-self `fact:`"; nothing relies on it (the F-15 stands on `seed_basis`; every F-35 counted row carries a `doc:` or a tier-G `src:`). Task 10c files the piece-3 follow-up.
- **R2. `LakeReader` additions (Task 2c):** `actuals(keys)` (feeds `headline_actuals_k`; it reproduces every F35 Appendix B1 member figure and 116,808.4) and `program_series(code)` (the `fct_program_decade_series` mart under the edition rule; Task 7c's `compare_reference`). No reader filters editions, so a PB2027 row reaches stage 2 and fails loudly (§9.2 item 1, §17 risk 7).
- **R3. Registry additions beyond the outline (Task 2a unless named):** `ON_PARTIAL_CORPUS`, `RULING_KINDS`, `HEADLINE_MEASURES`, `GUARD_EXHIBITS`, the key-order tuples, `split_refs`, `Member.from_row`, `EraLine.as_row`, `registry_texts`; `INDEPENDENT_TIERS` (2b); `normalize_quote_text`, `LakeReader` as a context manager (2c). `Registry.__getitem__` and `published()` read `families` with no cache, so `dataclasses.replace(registry, families=…)` stays consistent.
- **R4. Stage-2 outcomes.** `LakeReport.raise_if_failed()` raises on failures **and** stale (a drift mismatch blocks the export, `ratify` and the seed). Recorded `deferred` rows are reported `undecided` (§8.3). `check` exits 1 on failures; `--strict` also on undecided or stale. `verify-families` leg b fails on failures or stale.
- **R5. `RegistryError` lines** read `platform-families: <file basename>[:<row id>]: <reason>` (`platform_families.json`, `platform_family_members.csv`, `review.csv`, `rows.csv`, …); stage-3 lines name `family.history_path` instead.
- **R6. The seed.** `--seed-shipped` has `choices=["f-15"]` (argparse refuses any other family, §7.6). The seed's input refusals (any family already present included) raise before the lake opens. The CLI wrapper derives `expected_from` from `f15_funding_history.F15.counted`'s `coverage_expected_from_edition`.
- **R7. Guard coverage.** Stage 2 counts a guard-matching lake row covered by an `approved` or `rejected` row of the family, any role, whose code equals the row's `pe_bli` (code-keyed) or its printed `line_item_code` (era-keyed). The builder never sees `line_item_code` (the frozen source SQL), so an era-keyed guard match on no roster raises "Unreviewed" there even when stage 2 counts it covered: fail-closed, and none exists for the F-15 (31 era-keyed guard lines) or the F-35 (63), all on counted rosters (measured 2026-10-21).
- **R8. Receipts (Task 6):** `default_cell_counts(site_dir, registry, receipts)` (it counts `receipts[fact_id]["complete"]`); `family_formula_tails` order = every published family's annual tail (JSON order), the generic tail once, every published family's cumulative tail (JSON order), which reproduces today's `[annual, generic, cumulative]`.
- **R9. Builder (Tasks 4–5):** `_json_bytes` and `_point_measure` move from `f15_funding_history.py:111-159` into `platform_family_history` (the facade re-exports `_json_bytes`); helpers `program_entries(family)` and `check_headline(family, payload)`, the latter called only by `export_family_histories` (the frozen F-15 tests build one-year cumulatives); the generic `member_row` looks a code up among all approved counted members (no such lake row exists for the era-only F0150P/F015E0; measured).
- **R10. Stage 3:** `check_citations(..., claimed=None)` shares one `claimed` dict across the families of one pass (the export and `verify-families` leg c); after an export, `minted` = every citation the history artifact names (points, cumulative, program cells, the 11 reused decade receipts included). A preview checks formulas against a registry copy in which the previewed family is `published`, for the grammar only.
- **R11. Literal copies (Task 3a):** `tests/test_f15_registry_parity.py` holds the `88538c6a` constants as module globals, `EXPECTED_FROM`, `literal_constants()` and `SHIPPED = literal_constants()`; Task 3b reads `SHIPPED`, Task 6 adds `RECEIPT_TAILS_88538C6A`.
- **R12. `propose` (Task 7b):** the `--family-json` file is `{"family": <§7.2 object without status and published_ruling_id>, "sources": [...]}` (an exclusion's `evidence` may be empty); the family object is checked first as a zero-row draft; prefill rows become `Member`s through `Member.from_row` before measurement, and stage 1 runs once, on the measured rows; the review files and the registry are written in one atomic call.
- **R13. `ratify` (Task 7d)** writes every reviewed row (approved and deferred: 19 rows and 63 era lines for B1) and runs stage 2 for every family (§9.2). The batch ruling's `spec` is `docs/superpowers/specs/2026-10-20-families-piece2-registry-design.md#82-r-dec-fam-f35-b1-one-batch-through-the-batch-page`, the anchor style of R-DEC-FAM-F15-SEED's `#81-…`.
- **R14. Preview (Task 7c):** `PreviewResult` gains `members: dict[code, member_id]`; `CAUSE_LAKE = "lake since 2026-10-19"` is a constant (`reference-b1.json` has no `as_of`).
- **R15. Patch points:** `platform_family_review` and `verify_families` call I-REG and I-HIST through module attributes (`reg.open_lake`, `hist.export_family_histories`, …); `platform_family_history`'s own module-level `open_lake`, `check_lake`, `index_projection` and `build_workbook_previews` are Task 5's.
- **R16. SAM guard scope:** `verify_families.sam_guard` acts only when the DuckDB path is `config.DUCKDB_PATH` and is not inside a proof snapshot tree (its grandparent holds `snapshot.json`), so fam2 and its clones are never guarded (Global Constraints) even when their `env.sh` is sourced.
- **R17. Known limits filed at Task 10c:** re-proposing a `ratified` family is undefined in piece 2 (`ratify` flips the family; only fixtures exercise the re-propose rules), and no piece-2 tool re-measures a published or ratified family's committed lake columns, so a moved F-15 or ratified F-35 line is an owner stop at Task 10a Step 3; `scripts/era/fact_stability.py` cannot read a no-change A/B (Task 9a Step 9 calls its functions instead); `check --strict` cannot exit 0 while a deferred row or a draft exists, so Task 10a reads its categories.

## Review Focus

1. **The owner's B1 answer defers or amends rows** (identity, edition or lake columns; `member_order` gaps; a `--decided-on` unlike the answer): `answer` refuses a non-amendable column (re-run `propose`) and a row not on the page; `ratify` renumbers `member_order` contiguously and refuses the date mismatch. Tests (Task 7d): `test_answer_refuses_identity_edition_or_lake_column_amendments`, `test_answer_refuses_a_row_not_on_the_page`, `test_ratify_renumbers_member_order_after_a_deferral`, `test_ratify_refuses_a_decided_on_unlike_the_answer`.
2. **Hand-written `doc:` quotes that do not survive PDF extraction** (`;` inside `q=`, line breaks, NBSP, non-ASCII hyphens and minus, curly quotes): stage 1 refuses `;` in `q=`; stage 2 matches after NFKC, whitespace-run, dash and quote folding, case-sensitive; a miss names the sha, page and quote. Tests: `test_doc_ref_quote_with_semicolon_is_refused` (Task 2b); `test_doc_ref_quote_matches_across_breaks_nbsp_dashes_and_curly_quotes`, `test_doc_ref_miss_names_sha_page_and_quote` (Task 2c).
3. **Preview figures against B1 at mixed precision** (thousands vs $0.1M, a real `0.0` vs an absent `—`, lake drift vs a wrong row): ROUND_HALF_UP to 0.1 before comparing; zero and absent stay distinct; the cause comes from `fct_program_decade_series` on fam2 — "proposal row" blocks the page, "lake since 2026-10-19" is shown. Tests (Task 7c): `test_preview_compares_at_b1_precision`, `test_preview_keeps_real_zero_distinct_from_absent`, `test_render_blocks_a_proposal_row_difference_and_shows_lake_drift`.
4. **Hand-edited registry files** (a BOM, CRLF, a trailing blank line, a padded field, duplicate JSON keys, an unquoted comma in `scope_note`): one `platform-families: <file>[:<row>]` error each, never a silent normalization. Tests (Task 2a): `test_bom_crlf_and_trailing_blank_line_are_refused_naming_the_file`, `test_duplicate_json_keys_are_refused`, `test_field_whitespace_is_not_stripped`, `test_unquoted_comma_shifts_columns_and_fails_the_header_count`.
5. **The shared lake held by another writer, or a live run crossing :15–:20:** `check`, `verify-families` leg b, `propose` and `ratify` print `<tool>: ERROR — … lock …` (or the SAM refusal) and exit 2, never FAIL or a partial PASS; `propose` and `ratify` write nothing. Tests: `test_open_lake_surfaces_a_duckdb_lock_as_an_exception` (Task 2c); `test_check_reports_a_duckdb_lock_as_exit_2`, `test_verify_families_leg_b_lock_is_error_not_fail`, `test_legs_b_and_c_refuse_the_live_lake_across_the_sam_window` (Task 7a); `test_propose_and_ratify_write_nothing_on_a_lock` (Tasks 7b, 7d).

## File Structure

**Data and seeds**

| File | Responsibility (task) |
|---|---|
| `data-seeds/platform_families.json` | `schema_version`, `rulings[]`, `sources[]`, `families[]` (§7.2): F-15 `published` + `R-DEC-FAM-F15-SEED` (3a); F-35 `draft` + source `msar-pb2027` (8a); F-35 `ratified` + `R-DEC-FAM-F35-B1` on a ratify (8b) |
| `data-seeds/platform_family_members.csv` | The frozen 49-column header (§7.3): F-15 8 rows (3a); +19 F-35 rows on a ratify (8b) |
| `data-seeds/platform_family_era_lines.csv` | The pinned era roster (§7.4): F-15 31 rows (3a); +63 on a ratify (8b) |
| `data/research/platform_families/f-15/owner-reply-R-DEC-FAM-F15-SEED.txt` | D13 (3a) |
| `data/research/platform_families/f-35/prefill/{family.json,rows.csv}`, `reference-b1.json` | The `propose` inputs and Appendix B1 (8a) |
| `data/research/platform_families/f-35/{review.csv,review_era_lines.csv}` | Written by `propose` (8a) |
| `data/research/platform_families/f-35/batches/B1.json` | Written by `answer` (8b) |

**Code**

| File | Responsibility (task) |
|---|---|
| `src/govbudget/platform_families.py` (new) | Paths, vocabularies, types, `RegistryError`, stage 1 and writers (2a, 2b), stage 2 and measurement (2c), the seed (3a), stage 3 and `index_projection` (5) |
| `src/govbudget/platform_family_history.py` (new) | The pure builder and templates (4); `export_family_histories`, `INDEX_PATH` (5) |
| `src/govbudget/platform_family_review.py` (new) | `propose` (7b); `preview`, `compare_reference`, `render` (7c); `answer`, `ratify` (7d) |
| `src/govbudget/verify_families.py` (new) | Legs a–c, `scan_leaks`, `sam_guard`, `format_report` (7a) |
| `src/govbudget/f15_funding_history.py` | Facade: constants from the registry (3b), wrappers (4), `export_f15_funding_history` (5) |
| `src/govbudget/export_site.py:3932-3938` (the `export_f15_funding_history` call after `# Family history is a bounded additive projection`; `:3869-3875` at `b30134c4`) | Calls `export_family_histories(..., registry=load_registry())` (5) |
| `src/govbudget/program_pdf_receipts.py:266-278`, `:458-467` | Registry tails and audit (6) |
| `src/govbudget/cli.py` | `platform-families` (7a parser and `check`; 7b–7d branches), `verify-families` (7a) |
| `src/govbudget/verify_phase5.py:30-42`, `:137-158` | `verify-families` in `_ASSEMBLY_PHASES`, `_VERDICT_RE` (7a) |
| `scripts/export_f15_funding_history.py` | Deleted (5; §10.1) |

**Tests and gates**

| File | Responsibility (task) |
|---|---|
| `tests/platform_family_fixtures.py` (new) | The miniature registry world (2a) and its lake and site (2c) |
| `tests/test_platform_families_loader.py` (new) | Stage 1 (2a, 2b), stage 2 (2c), stage 3 (5) |
| `tests/test_f15_registry_parity.py` (new) | The only literal `88538c6a` copies and the seed's tests (3a); facade parity (3b); tails (6) |
| `tests/test_platform_family_history.py` (new) | The generic builder (4); the post-pass and `index.json` (5) |
| `tests/platform_families_helpers.py` (new) | Shared CLI fixtures (7a–7d) |
| `tests/test_platform_families_cli.py` (new) | `check` (7a), `propose` (7b), `preview`/`render` (7c), `answer`/`ratify` and the round trip (7d) |
| `tests/test_verify_families.py` (new) | Legs a–c and the CLI (7a) |
| `tests/test_budget_pdf_receipts.py`, `tests/test_verify_phase5.py`, `tests/test_roadmap_backlog.py` | New cases (6), the assembly (7a), the stamp (10c) |
| `site/src/__tests__/platform-family-mirror.test.ts`, `site/scripts/gates/__tests__/family-index.test.mjs` (new) | The hermetic mirror and leg (r)'s unit tests (7e) |
| `site/scripts/gates/family-history.mjs`, `program-skeleton.mjs` | `checkFamilyIndex` and leg (r) (7e) |

**Docs and ledger:** `docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json` (9a; spec §14 step 3 names this directory, so the rule files live there while this plan is one file), `…/expected-diff-release.json` (10a), `docs/superpowers/reviews/families-piece2-proof.md` (9b), `docs/superpowers/ROADMAP.md` (10c); the ledger files above.

**Interface labels** used by the tasks: **I-REG** = `govbudget.platform_families` (Tasks 2a, 2b, 2c, 3a, 5); **I-HIST** = `govbudget.platform_family_history` (4, 5); **I-FACADE** = `govbudget.f15_funding_history` (3b, 4, 5); **I-RCPT** = `govbudget.program_pdf_receipts` (6); **I-REV** = `govbudget.platform_family_review` and the `platform-families` CLI (7a–7d); **I-SITE** = `checkFamilyIndex` and leg (r) (7e). Each owning task's **Produces** block is the authority for the exact signatures.

---

### Task 1: Worktree, baselines and the fam2 snapshot

**Spec:** §5.2, §5.3, §14 step 1, Appendix A row 1; D1, D15.

**Files:**
- Create (ledger, outside the repo): `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2/progress.md` and `…/families-piece2/proof-logs/fam2-snapshot.md`.
- Proof state: `$GOVBUDGET_PROOFS/fam2/` (the snapshot tool also creates the scratch database `govbudget_proof_fam2`) and `$GOVBUDGET_PROOFS/fam2-logs/`.
- Local only: `site/out/`, `dbt/target/manifest.json` (re-parsed), and `site/public/llms.txt` (rewritten by the base build, then restored).
- No tracked file changes and no commit.

**Interfaces:**
- Consumes:
  - `govbudget proof snapshot --out DIR --scratch-db NAME`. It prints `proof snapshot: <dir>` and three summary lines and writes `DIR/{duckdb/govbudget.duckdb, parquet/, site/, raw_docs/, manifest.jsonl, pg/govbudget_proof_fam2.dump, snapshot.json, env.sh}`. It refuses :15–:20, an existing directory or database, and a DuckDB writer lock, and removes only a directory it created itself.
  - `node scripts/f15-page-snapshot.mjs <index.html> --check FILE`, run from `site/`. It prints `f15-page-snapshot: PASS — equal to FILE`.
  - The controller's D1 ruling, `link-fix-first` (2026-10-21), in the ledger's `owner-decisions.md`.
- Produces:
  - `$GOVBUDGET_PROOFS/fam2/…`, `fam2-logs/snapshot.log` and `fam2-logs/snapshot-shas.json`.
  - `FAM2_DUCKDB=$GOVBUDGET_PROOFS/fam2/duckdb/govbudget.duckdb` and `FAM2_SITE=$GOVBUDGET_PROOFS/fam2/site`. Tasks 3a, 7c, 8a, 8b and 9a set them again in every block.
  - These `progress.md` lines: `D1:` (Step 1), then `A:`, `dbt-tests:`, `W1:`, `frozen:`, `base-weight:` and `fam2:`. Tasks 8a–10c read them.

**Measured (read-only, at HEAD `b6c9a8d9`; re-measured 2026-10-21):**
- **Live F-15 pin.** The live `data/site/json/f15_funding_history.json` hashes to the pin `d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f` (139,061 B).
- **Production, before the link fix's release.**
  - `https://fiscalreceipts.com/json/f15_funding_history.json` has the same sha.
  - `/json/families/index.json` returns 404, and `/families/f-15/` returns 200.
  - A curl copy of `/families/f-15/` passes `f15-page-snapshot --check ../tests/fixtures/f15/page_snapshot.json`.
  - `/.build-meta.json` `git_head` is `1256ec35e3aadd7410f13eee48f6b2a9e6f5bebe`.
  - After the link fix's release, Step 1 expects that release's code instead (D1).
- **W1 at `88538c6a`, `b30134c4`, `9acf0c78`, `b6c9a8d9` and `9a50e28b`** (`uvx --offline ruff check --isolated --select F,E9`; `9acf0c78` and `b6c9a8d9` measured on a clean `git archive` of each commit, and `9a50e28b` on the clean worktree): `cli.py` 5, `export_site.py` 10, `verify_phase5.py` 2; `program_pdf_receipts.py`, `f15_funding_history.py` and `verify_era_map.py` 0 each.
- **Frozen files** (sha256):

  | File | sha256 |
  |---|---|
  | `tests/test_f15_funding_history.py` (21 tests) | `dc0eb58ae08a0d7430d9c0721a013fad7017297ea1e52a19519bfc5705bde75b` |
  | `tests/test_f15_era_identity.py` (4) | `6b436439726c8327e77e651291be2cfd82ca53a9ee0ff57fc88f5fbde6b2b6d9` |
  | `tests/test_capture_f15_fixtures.py` (5) | `7768e402ce71d3143cd6d37baff35c24d76754a824057bed0a20fc25918e4320` |
  | `site/scripts/gates/__tests__/f15-page-snapshot.test.mjs` | `cee5a7481041ebc27fe53843e766fce0ab87686093c16a32675f85d49bb6040d` |
  | `tests/fixtures/f15/history.json` | `d0de9e8b…8d8f` |
  | `tests/fixtures/f15/page_snapshot.json` | `9288cd2c04a8d8200baf638d6375964c523f2415fb61bb858eb88ee6565fd623` |
- **Worktree.** `site/node_modules` is a real directory. `data/{site,duckdb,parquet,raw,raw_docs}` and `.env` are symlinks into `/Users/andeslee/Documents/Cursor-Projects/GovBudget/`. `dbt/target/manifest.json` is rewritten whenever the link fix's dbt fixture tests run (last at 03:38 today; it lists 206 test nodes and the model `link_award_keys`), so Step 2 parses again.
- **The link fix is committed here and not released.**
  - Round 1 is `be256625`, `391eb1d6` and `b30134c4`: its seed, four dbt tests, `export_site.py`, program-skeleton leg (q), /about/ and their tests.
  - Round 2 is `5c751627`, `893f9a8b`, `5d567272`, `b6b68d82` and `9acf0c78`: the F03500 holds, the dbt model `link_award_keys` and the re-keyed marts, `export_site.py`'s named-award rule and its guard, `flow_chart.py`, /methodology/ and /about/, leg (q) on citations, and their tests.
  - The minors are `4504be40`, `f308589c`, `8e23089b` and `b6c9a8d9`: /about/, leg (q)'s IN-07 pin, `flow_chart.py`'s guard and gate 24 leg r's sample.
  - Round 3 is `79a81125`, `372a496c` and `9a50e28b` (R-DEC-LINK-2026-10-21-B): the 10 F03500 holds become withdrawals, so the seed withdraws 51 pairs; `export_site.py`'s docstrings record fpds-ap 86/111; /about/; leg (q)'s floor rises to 51; and their tests. Its review fixes are `4e505dc3`, `b47c11b9` and `31b1e47b` (`site/` only: /about/'s wording, leg (q)'s messages, and their tests).
  - All of it sits on this branch, while `main` and `git merge-base main HEAD` are still `88538c6a`.
  - Besides the three `??` eval-runs files, the worktree holds only this uncommitted plan. The plan is committed before the link fix's release Step P0 or after its Step R17, never between them: a commit inside that window breaks the runbook's R14 provenance check (runbook, open question 2). Either way it is committed before Task 1 (ledger).
  - The link fix's release adds at least one more `??` file: its Step R11 runs `verify-phase5` with the paid eval from this worktree, and that writes `data/research/eval-runs/eval-<UTC>.json` here (Global Constraints).
  - Under D1 the link fix releases before Task 1 runs.
- **The link fix's warehouse objects are not live yet.** The live DuckDB (written 2026-10-14 21:32) has no `link_line_rulings` and no `link_award_keys`, and `fct_award_transactions` is a view (probed read-only 2026-10-21 03:40). The link fix's release builds both, and Step 1 checks them.
- **Nothing to collide with.** `.proofs/` holds no `fam2*` entry, the local server has no `govbudget_proof_*` database, and there is no `fam2-proof-a` worktree.
- **The F-15 era roster in the live `p1_era_line_map`** has 31 rows over its five decisions.

- [ ] **Step 1: D1 (ruled `link-fix-first`): prove the link fix's release and its live build, then write the `D1:` line**

The controller ruled D1 = `link-fix-first` on 2026-10-21 (ledger `owner-decisions.md`, section "2026-10-21: piece-2 plan D1 (controller)"). This task does not decide D1. It proves the ruling's preconditions, then writes the ruling into `progress.md` before anything is measured.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
LEDGER=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2
grep -c 'D1 = `link-fix-first`' "$LEDGER/owner-decisions.md"
A=$(git merge-base main HEAD); echo "A=$A"
[ "$A" != 88538c6ae40d7565ff69b908970d0cbe85c53250 ] && git merge-base --is-ancestor 88538c6a "$A" && echo "main advanced past 88538c6a"
git merge-base --is-ancestor 31b1e47b "$A" && echo "A holds the link fix through 31b1e47b"
[ "$A" = "$(git rev-parse main)" ] && echo "A is main's tip"
LIVE=$(curl -s https://fiscalreceipts.com/.build-meta.json | python3 -c "import json,sys; print(json.load(sys.stdin)['git_head'])"); echo "live=$LIVE"
git -C .. diff --quiet "$LIVE" "$A" -- GovBudget/src GovBudget/dbt GovBudget/data-seeds GovBudget/scripts GovBudget/site && echo "A's code equals the deployed code"
git -C .. status --porcelain -- GovBudget | grep -v '^??'; echo "(tracked changes above: expect none)"; git -C .. status --porcelain -- GovBudget | grep '^??'
uv run --project . python -c "import duckdb; c=duckdb.connect('$GOVBUDGET_DATA/duckdb/govbudget.duckdb', read_only=True); print('link_line_rulings tables:', c.execute(\"select count(*) from information_schema.tables where table_name = 'link_line_rulings'\").fetchone()[0]); c.execute('select award_piid, recipient_uei, award_unique_key, n_awards, named from link_award_keys limit 0'); print('link_award_keys: the five columns export_site._require_link_award_keys reads')"
```

Expected:
- `1`: the ledger's ruling line. `0` means the ruling changed: stop and ask the controller. This plan assumes `link-fix-first`, and §16's rule list (Task 9a Step 2) holds only piece 2's two paths;
- `A=<sha>`;
- `main advanced past 88538c6a`;
- `A holds the link fix through 31b1e47b` (round 3's last review fix, the link fix's last commit when this plan was committed);
- `A is main's tip`. `main` fast-forwarded onto this branch, so HEAD contains it;
- `live=<sha>`;
- `A's code equals the deployed code`;
- no tracked change;
- `??` only on `data/research/eval-runs/eval-*.json` files: the three of 2026-10-21, plus those the link fix's release added (its R11 eval writes one per run). Leave them all; never commit or delete one;
- `link_line_rulings tables: 1` and `link_award_keys: the five columns export_site._require_link_award_keys reads`. The link fix's seed and model are in the live warehouse, so fam2 will carry them.
  - A `CatalogException` or `BinderException` naming `link_award_keys` means the live build predates round 2. Stop: A's and B's exports would raise on fam2 (Global Constraints, "fam2 carries the link fix's warehouse objects").

Anything else: stop and report. The snapshot must not predate the link fix's live build (D1).

Then write the ruling as the first `progress.md` line:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget || exit 1
LEDGER=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2
A=$(git merge-base main HEAD); LIVE=$(curl -s https://fiscalreceipts.com/.build-meta.json | python3 -c "import json,sys; print(json.load(sys.stdin)['git_head'])")
{ grep -q '^D1: ' "$LEDGER/progress.md" 2>/dev/null && echo "D1 line already written"; } || printf 'D1: link-fix-first (controller 2026-10-21, owner-decisions.md) — A = %s, deployed %s\n' "${A:?}" "${LIVE:?}" >> "$LEDGER/progress.md"
grep -E '^D1: ' "$LEDGER/progress.md"
```

Expected: one line, `D1: link-fix-first (controller 2026-10-21, owner-decisions.md) — A = <40 hex>, deployed <40 hex>`. Its A and deployed sha are the ones printed above.

- [ ] **Step 2: Ready the worktree**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
if [ -d site/node_modules ] && [ ! -L site/node_modules ]; then echo "node_modules is a real directory"; else (cd site && npm ci > /dev/null 2>&1; echo "npm ci exit=$?"); fi
uv sync --frozen > /dev/null 2>&1; echo "uv sync exit=$?"
for d in site duckdb parquet raw raw_docs; do if [ -L "data/$d" ]; then echo "data/$d -> $(readlink "data/$d")"; else echo "STOP: data/$d is not a link"; fi; done; readlink .env
GOVBUDGET_DUCKDB="$GOVBUDGET_PROOFS/fam2-dbt-parse-b.duckdb" uv run --project . dbt parse --project-dir dbt --profiles-dir dbt > /dev/null 2>&1; echo "parse exit=$?"; test ! -e "$GOVBUDGET_PROOFS/fam2-dbt-parse-b.duckdb" && echo no-warehouse-opened
uv run --project . python -c "import json; m=json.load(open('dbt/target/manifest.json')); print('dbt test nodes', sum(1 for n in m['nodes'].values() if n.get('resource_type') == 'test'))"
```

Expected:
- `node_modules is a real directory`, or `npm ci exit=0`;
- `uv sync exit=0`;
- five links to `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/{site,duckdb,parquet,raw,raw_docs}`;
- `.env` reads `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.env` (never print its contents);
- `parse exit=0` and `no-warehouse-opened`;
- `dbt test nodes <n>`. Record `dbt-tests: <n>`. Piece 2 adds no dbt test, so Task 9a's A worktree must print the same `<n>`.

- [ ] **Step 3: Baselines (pin, pytest, W1, frozen files)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -lt 23 ]; then echo "WAIT: start between :23 and :59 (minute $MIN); the full pytest reads the live DuckDB for about 10 minutes"; exit 0; fi
H=$(shasum -a 256 data/site/json/f15_funding_history.json | cut -d' ' -f1); [ -n "$H" ] && [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ] && echo "F-15 history matches the pin" || echo "STOP: F-15 history ${H:-missing} is not the pin"
"$GOVBUDGET_PG_BIN/pg_isready" -h 127.0.0.1 -p 55432 && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q 2>&1 | tail -1; echo "pytest ended at minute $(date +%M)"
for f in cli export_site verify_phase5 program_pdf_receipts f15_funding_history verify_era_map; do printf "%s: " "$f"; uvx --offline ruff check --isolated --select F,E9 "src/govbudget/$f.py" 2>&1 | grep -E '^(Found|All checks)'; done
shasum -a 256 tests/test_f15_funding_history.py tests/test_f15_era_identity.py tests/test_capture_f15_fixtures.py site/scripts/gates/__tests__/f15-page-snapshot.test.mjs tests/fixtures/f15/*
git -C .. diff --quiet 88538c6a HEAD -- GovBudget/tests/test_f15_funding_history.py GovBudget/tests/test_f15_era_identity.py GovBudget/tests/test_capture_f15_fixtures.py GovBudget/tests/fixtures/f15 'GovBudget/tests/test_verify_era_map*.py' GovBudget/tests/test_export_era_line_map.py GovBudget/site/scripts/gates/__tests__/f15-page-snapshot.test.mjs GovBudget/src/govbudget/verify_era_map.py GovBudget/scripts/era/capture_f15_fixtures.py GovBudget/scripts/era/review_batch_page.py && echo "frozen files unchanged since 88538c6a"
```

Expected:
- `F-15 history matches the pin`;
- `127.0.0.1:55432 - accepting connections` and `… passed`, with 0 failed (a Postgres-only failure gets one re-run on a quiet cluster);
- `pytest ended at minute <m>`, with `<m>` outside :15–:22. A run started at :23 or later that ends in :15–:22 crossed the SAM window: re-run the block from :23;
- W1: `cli: Found 5 errors.`, `export_site: Found 10 errors.`, `verify_phase5: Found 2 errors.`, and `All checks passed!` for the other three. The link fix moved no count through `31b1e47b`. If its later commits moved one, record A's count instead: these are the baselines Task 9b holds W1 to;
- the six shas of the Measured table, plus `tests/fixtures/f15/README.md`, `builder_inputs.json.gz` and `history.sha256` (record all nine as `frozen:`);
- `frozen files unchanged since 88538c6a`.

- [ ] **Step 4: Base build at A, and the F-15 page snapshot**

The page snapshot is checked on a base build, before any piece-2 code exists. Port 4173 is not used here.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
mkdir -p "${GOVBUDGET_PROOFS:?}/fam2-logs" && cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > "$GOVBUDGET_PROOFS/fam2-logs/base-site-build.log" 2>&1; echo "build exit=$?"
node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check ../tests/fixtures/f15/page_snapshot.json
node -e 'const fs=require("fs"),z=require("zlib");for(const [l,f] of [["/families/f-15/","out/families/f-15/index.html"],["/methodology/","out/methodology/index.html"]]){const b=fs.readFileSync(f);console.log(l+" "+b.length.toLocaleString("en-US")+" / "+z.gzipSync(b,{level:9}).length.toLocaleString("en-US"))}'
node -e 'const m=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));console.log("export built_at "+m.built_at+", renders "+new Date(m.built_at).toLocaleDateString("en-US",{year:"numeric",month:"long",day:"numeric"}))' ../data/site/json/site_meta.json
cd .. && git checkout -- site/public/llms.txt && git -C .. status --porcelain -- GovBudget | grep -v '^??'; echo "clean check done"
```

Expected:
- `build exit=0`;
- `f15-page-snapshot: PASS — equal to ../tests/fixtures/f15/page_snapshot.json`;
- `/families/f-15/ <raw> / <gzip>`. It was 705,056 / 69,328 on `1256ec35`, and the link fix touches neither the F-15 page nor its sources. Whatever A builds, it must stay under 725,000 / 70,000;
- `/methodology/ <raw> / <gzip>`, under 162,000 / 45,400 (`build.mjs`, the `/methodology/` entry). The link fix's own figures are about 38 gzip bytes of headroom: 161,455 / 45,362 on round 2's pre-release build, the same in round 3's estimate, and re-measured and re-stamped by its release's P12. A's export prints fpds-ap 86/111 after round 3, the same length as 89/114. A page over its ceiling here is A's, not piece 2's: stop and report; never raise a ceiling;
- `export built_at <ISO timestamp>, renders <Month D, YYYY>`. This is the stamp of the live export, A's release export. The footer prints it, and on /methodology/ the page intro prints it too. Measured 2026-10-21 on a build of the pre-release export, the rendered date appears twice on `/families/f-15/` and four times on /methodology/ (HTML and flight payload). Task 9b Step 5 needs it;
- record both pages and the stamp as `base-weight:`;
- no tracked change, then `clean check done`.

- [ ] **Step 5: Take the fam2 snapshot (creates the scratch database only)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"; [ -e "$P/fam2" ] && { echo "STOP: $P/fam2 exists"; exit 1; }
date +%H:%M && uv run --project . python -m govbudget proof snapshot --out "$P/fam2" --scratch-db govbudget_proof_fam2 > "$L/snapshot.log" 2>&1; echo "exit=$?"; cat "$L/snapshot.log"
uv run --project . python - "$P/fam2/snapshot.json" "$L/snapshot-shas.json" <<'PY'
import hashlib, json, sys
m = json.load(open(sys.argv[1]))
digest = lambda v: hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
parquet = {rel: e["sha256"] for rel, e in m["parquet"].items() if not rel.startswith("sam/")}
out = {"created_at": m["created_at"], "duckdb_sha256_at_copy": m["duckdb"]["sha256_at_copy"],
       "parquet_files_minus_sam": len(parquet), "parquet_minus_sam_sha256": digest(parquet),
       "site_sha256": m["site"]["sha256"], "raw_docs_sha256": m["raw_docs"]["sha256"],
       "manifest_jsonl_sha256": m["manifest_jsonl_sha256"], "pg_tables": len(m["pg"]["tables"]),
       "pg_tables_sha256": digest(m["pg"]["tables"]), "pg_dump_sha256": m["pg"]["dump_sha256"],
       "pg_scratch_dsn": m["pg"]["scratch_dsn"]}
open(sys.argv[2], "w").write(json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))
PY
```

Expected:
- `exit=0`, then `proof snapshot: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fam2` and the duckdb, parquet and postgres lines, the last of which reads `postgres govbudget -> govbudget_proof_fam2 …`;
- the JSON with every value filled and `"pg_scratch_dsn": "dbname=govbudget_proof_fam2 host=localhost"`.

On `WAIT`, or on a refusal printed as `proof snapshot: ERROR — …`, wait until :23 and re-run. The tool has already removed a directory it created.

Then prove what fam2 holds:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; FAM2_DUCKDB="$P/fam2/duckdb/govbudget.duckdb"; FAM2_SITE="$P/fam2/site"
H=$(shasum -a 256 "$FAM2_SITE/json/f15_funding_history.json" | cut -d' ' -f1); [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ] && echo "fam2 F-15 history matches the pin"
uv run --project . python -c "import duckdb; c=duckdb.connect('$FAM2_DUCKDB', read_only=True); print('link_line_rulings tables:', c.execute(\"select count(*) from information_schema.tables where table_name = 'link_line_rulings'\").fetchone()[0]); c.execute('select award_piid, recipient_uei, award_unique_key, n_awards, named from link_award_keys limit 0'); print('link_award_keys: the five columns export_site._require_link_award_keys reads'); print('F-15 roster rows:', c.execute(\"select count(*) from p1_era_line_map where decision_id in ('F01500|3010F||2017-2023','F015EX|3010F||2021-2023','F15EWS|3010F||2019-2023','F0150P|3010F||2017-2020','F015E0|3010F||2020-2022')\").fetchone()[0])"
(source "$P/fam2/env.sh" && echo "$GOVBUDGET_DATA | $GOVBUDGET_PG_DSN")
```

Expected:
- `fam2 F-15 history matches the pin`;
- `link_line_rulings tables: 1`;
- `link_award_keys: the five columns export_site._require_link_award_keys reads`. The clones `fam2-A`, `fam2-B` and `fam2-B2` (Task 9a) copy this DuckDB file, so the guard passes in all three exports;
- `F-15 roster rows: 31`;
- `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fam2 | dbname=govbudget_proof_fam2 host=localhost`.

- [ ] **Step 6: Write the ledger (nothing is committed)**

Append to `progress.md`, under the `D1:` line:
- `A: <sha> (git merge-base main HEAD; equals the deployed <live sha> on src, dbt, data-seeds, scripts, site)`;
- `dbt-tests: <n>`;
- `W1: cli <n>, export_site <n>, verify_phase5 <n>, program_pdf_receipts 0, f15_funding_history 0, verify_era_map 0`;
- `frozen: <the nine sha256 lines>`;
- `base-weight: /families/f-15/ <raw> / <gzip>; /methodology/ <raw> / <gzip> at A; export built_at <ISO>, renders <Month D, YYYY>`;
- `fam2: <created_at>; FAM2_DUCKDB=$GOVBUDGET_PROOFS/fam2/duckdb/govbudget.duckdb; FAM2_SITE=$GOVBUDGET_PROOFS/fam2/site; [fam2-logs/snapshot-shas.json]`.

Write `proof-logs/fam2-snapshot.md` with the contents of `snapshot-shas.json` and `snapshot.log`, and the date this step runs.

Expected: `grep -cE '^(D1|A|dbt-tests|W1|frozen|base-weight|fam2): ' progress.md` prints `7`.

---

### Task 2a: Registry formats, vocabularies and per-row stage-1 rules

**Spec:** §6 (names), §7.1–§7.4 (the three files, the frozen 49-column header), §9 intro (one `RegistryError`, its line format), §9.1 rules 1–12, 17, 18, 26, 27, the file-level refusals of Review Focus 4; D10 (`family_hash`), D11 (serialization). Rule 5's ruling link, rule 7's citation checks and rules 13–16 and 19–25 are Task 2b's.

**Files:**
- Create: `src/govbudget/platform_families.py`
- Create: `tests/platform_family_fixtures.py` (the miniature registry every loader test mutates; Task 2c adds its lake)
- Create: `tests/test_platform_families_loader.py`

**Interfaces:**
- Consumes (all in `govbudget.jbooks.era_map`, imported at module level; it pulls in only `collision_keys`, `era_keys` and `route_safe_codes`, measured 2026-10-21):
  - `ERA_ORG_TO_MODERN = {"ARMY": "A", "NAVY": "N", "AF": "F"}` (`era_map.py:100`), for rule 10;
  - `_csv_text(columns, rows) -> str` (`:939`, `DictWriter`, `lineterminator="\n"`, `QUOTE_MINIMAL`) and `_atomic_write_texts(files: Mapping[Path, str]) -> None` (`:949`, writes with `newline=""`), for D11;
  - `read_seed(seed_path) -> list[dict[str, str]]` (`:979`) and `default_seed_path() -> Path` (`:1531`, `config.ROOT / "dbt/seeds/p1_era_code_decisions.csv"`);
  - `config.ROOT`, `config.RESEARCH_DIR` (`config.py:4, 63`).
- Produces (`govbudget.platform_families`; Tasks 2b–2c, 3a, 3b, 4, 5, 6, 7a–7d rely on these names):
  - Paths: `REGISTRY_JSON`, `MEMBERS_CSV`, `ERA_LINES_CSV`, `REVIEW_ROOT`; `@dataclass(frozen=True) class RegistryPaths(json: Path, members: Path, era_lines: Path)`; `DEFAULT_PATHS`.
  - Columns: `MEMBER_COLUMNS` (49), `ERA_LINE_COLUMNS` (7), `REVIEW_COLUMNS`, `PREFILL_COLUMNS` (43).
  - Vocabularies (I-REG table) plus `ON_PARTIAL_CORPUS`, `RULING_KINDS`, `HEADLINE_MEASURES`, `GUARD_EXHIBITS`; `EDITIONS`; `SEED_BASIS_ALLOWED`; `F15_SEED_RULING_ID`; the six regexes; the key-order tuples `TOP_KEYS`, `RULING_KEYS`, `SOURCE_KEYS`, `FAMILY_KEYS` and the nested ones.
  - `class RegistryError(ValueError)` with `errors: list[str]`.
  - Frozen dataclasses `Ruling`, `Source`, `Member` (`from_row`, `title_for`, `as_row`), `EraLine` (`as_row`), `Headline`, `ReviewGuard`, `ProgramNote`, `Family` (`counted`, `code_keyed`, `context`, `route`, `history_path`), `Registry` (`__getitem__`, `published()`, `doc`; both read `families` with no cache, so `dataclasses.replace(registry, families=…)` stays consistent, R3).
  - `split_refs(text: str) -> tuple[str, ...]`.
  - `parse_registry(doc, member_rows, era_rows, *, era_decisions, paths=DEFAULT_PATHS) -> Registry`; `load_registry(paths=DEFAULT_PATHS, *, era_decisions_path=None) -> Registry`.
  - `registry_texts(paths: RegistryPaths, *, doc: dict, members: Sequence[Mapping[str, str]], era_lines: Sequence[Mapping[str, str]]) -> dict[Path, str]` (the three D11 texts; Task 7b writes them with its review files in one atomic call, R12); `write_registry(paths, *, doc, members, era_lines) -> None` = `era_map._atomic_write_texts(registry_texts(...))`; `family_hash(doc, platform_family) -> str`.
  - `tests/platform_family_fixtures.py`: `ON`, `RULING_X1`, `XA`, `XR`, `XC`, `ERA_XA`, `SRC_BYTES`, `SRC_SHA`, `DOC_SHA`, `LINES`, `DRIFT`, `ERA_DECISIONS`, `World`, `tmp_paths(root)`, `write_world(root, world)`.

- [ ] **Step 1: Write the fixture module `tests/platform_family_fixtures.py`**

The world: a published family `x-1` (two counted members and one context member, one era line) and a draft `y-1` with zero rows. Its lines are the ones Task 2c's lake prints, so `DRIFT` is what stage 2 recomputes.

```python
"""A miniature platform-families registry (piece 2, Tasks 2a–2c; spec §7, §9)."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from govbudget.jbooks import era_map
from govbudget.jbooks.era_map import keys_sha256
from govbudget.platform_families import MEMBER_COLUMNS, RegistryPaths, parse_registry, write_registry

ON = "2026-10-21"
RULING_X1 = "R-DEC-FAM-X1-B1"
XA, XR, XC = "P-1:3010F:AF:XA0001", "R-1:3600F:AF:XR0001", "P-1:3010F:AF:XC0001"
ERA_XA = "XA0001|3010F||2023-2023"
SRC_BYTES = b"x-book archived copy\n"            # site/sources/x-book.txt (Task 2c)
SRC_SHA = hashlib.sha256(SRC_BYTES).hexdigest()
DOC_SHA = "d" * 64                               # site/pdfs/<DOC_SHA>.pdf (Task 2c)
# (edition, code or era key, budget activity, filed title): the lines each member binds.
LINES = {
    "XA0001": [(2023, "3010F-AF-L7", "05", "X-1"), (2024, "XA0001", "05", "X-1"),
               (2025, "XA0001", "05", "X-1"), (2026, "XA0001", "05", "X-1")],
    "XR0001": [(2025, "XR0001", "07", "X-1 Dev"), (2026, "XR0001", "07", "X-1 Dev")],
    "XC0001": [(2024, "XC0001", "06", "X-1 Spares"), (2025, "XC0001", "06", "X-1 Spares"),
               (2026, "XC0001", "06", "X-1 Spares")],
}
DRIFT = {code: keys_sha256(lines) for code, lines in LINES.items()}


def ruling(rid: str, pf: str, **kv) -> dict:
    return {"ruling_id": rid, "kind": "batch", "platform_family": pf, "decided_by": "owner",
            "decided_on": ON, "owner_reply": f"yes, ratify {pf}", "spec": "docs/x.md#b1",
            "text": f"Ratifies the {pf} rows.", "seed_basis": False, **kv}


def source(**kv) -> dict:
    return {"source_id": "x-book", "title": "X-1 Selected Acquisition Report", "publisher": "DoD",
            "url": "https://x.test/sar.pdf", "as_of": "2026-04-21", "sha256": SRC_SHA, "bytes": 21,
            "archived": True, "archive_path": "sources/x-book.txt", "tier": "G", "verified_by": [], **kv}


def family(pf: str, *, status: str, ruling_id: str | None = None, **kv) -> dict:
    short = pf.upper()
    fam = {"platform_family": pf, "status": status}
    if ruling_id:
        fam["published_ruling_id"] = ruling_id
    fam.update({
        "short_name": short, "history_dataset": f"{pf.replace('-', '')}_funding_history",
        "on_partial_corpus": "raise",
        "headline": {"measure": "cumulative_actuals", "first_fy": 2015, "last_fy": 2024},
        "scope_note": f"{short} scope.", "coverage_notes": [f"{short} coverage."],
        "review_guard": {"exhibits": ["P-1", "R-1"], "title_substrings": [short]},
        "program_notes": {}, "variants": [{"id": "A"}, {"id": "B", "note": "B is the trainer."}],
        "program_tags": [{"tag": short, "mdap_code": "999"}], "purpose_tags": ["production"],
        "caveat_ids": ["classified", "nominal_dollars"], "exclusions": [], "aliases": [],
        "contract_routes": None, "official_estimates": None, "art": None, **kv})
    return fam


def member(pf: str, member_id: str, frm: int, to: int, **kv) -> dict[str, str]:
    exhibit, account, org, code = member_id.split(":")
    row = dict.fromkeys(MEMBER_COLUMNS, "")
    row.update(member_row_id=f"{pf}|{member_id}|{frm}-{to}", platform_family=pf, member_id=member_id,
               exhibit=exhibit, account=account, organization=org, code=code, verdict="approved",
               appropriation="rdte" if exhibit == "R-1" else "procurement",
               valid_from_edition=str(frm), valid_to_edition=str(to), services_using="USAF",
               paying_org="AF", decided_by="owner",
               ruling_id=f"R-DEC-FAM-{pf.replace('-', '').upper()}-B1", decided_on=ON)
    row.update(kv)
    return row


def decision(decision_id: str, kind: str) -> dict[str, str]:
    code, account, org, editions = decision_id.split("|")
    row = dict.fromkeys(era_map.SEED_COLUMNS, "")
    row.update(decision_id=decision_id, line_item_code=code, account=account, organization=org,
               first_edition=editions[:4], last_edition=editions[5:], decision=kind,
               decided_on=ON, decided_by="owner", ruling="R-DEC-ERA-SAME")
    return row


ERA_DECISIONS = {d: decision(d, k) for d, k in [
    (ERA_XA, "same_program"), ("XA0001|3010F||2017-2022", "exclude_placeholder"),
    ("XB0001|3010F||2023-2023", "same_program"), ("XZ0001|3010F||2023-2023", "same_program"),
    ("20|0300D|DSS|2022-2022", "same_program"),
]}


def _doc() -> dict:
    x1 = family("x-1", status="published", ruling_id=RULING_X1, exclusions=[
        {"exclusion_id": "spares", "kind": "shared_line", "label": "Spares",
         "size_text": "X-1 spares: $1.0M in FY2024", "evidence": ["src:x-book#p2"]}])
    return {"schema_version": 1, "rulings": [ruling(RULING_X1, "x-1")], "sources": [source()],
            "families": [x1, family("y-1", status="draft")]}


def _members() -> list[dict[str, str]]:
    return [
        member("x-1", XA, 2023, 2026, role="counted", budget_activities="05",
               titles_seen="2024: X-1; 2025: X-1; 2026: X-1", display_title="X-1", page_slug="XA0001",
               coverage_expected_from_edition="2023", era_decision_ids=ERA_XA,
               drift_sha256=DRIFT["XA0001"], member_order="1", program_tag="X-1",
               purpose_tag="production", purpose="buy", variant_ids="A", variant_scope="variant",
               evidence=f"era:{ERA_XA};src:x-book#p3"),
        member("x-1", XR, 2025, 2026, role="counted", budget_activities="07",
               titles_seen="2025: X-1 Dev; 2026: X-1 Dev", display_title="X-1 Dev", page_slug="XR0001",
               coverage_expected_from_edition="2025", drift_sha256=DRIFT["XR0001"], member_order="2",
               program_tag="X-1", purpose="develop", variant_ids="A;B", variant_scope="shared",
               scope_note="Shared A/B development.", evidence=f"doc:{DOC_SHA}#p1;q=X-1 development"),
        member("x-1", XC, 2024, 2026, role="context", budget_activities="06",
               titles_seen="2024: X-1 Spares; 2025: X-1 Spares; 2026: X-1 Spares",
               display_title="X-1 Spares", drift_sha256=DRIFT["XC0001"],
               scope_note="A shared spares line; never summed.", evidence="src:x-book#p4"),
    ]


def _era_rows() -> list[dict[str, str]]:
    return [{"platform_family": "x-1", "member_id": XA, "edition": "2023", "era_key": "3010F-AF-L7",
             "budget_activity": "05", "filed_title": "X-1", "decision_id": ERA_XA}]


class World:
    """A fresh deep copy of the registry; a test mutates it, then parses it."""

    def __init__(self):
        self.doc, self.members, self.era_rows = _doc(), _members(), _era_rows()
        self.decisions = copy.deepcopy(ERA_DECISIONS)

    def family(self, pf: str = "x-1") -> dict:
        return next(f for f in self.doc["families"] if f["platform_family"] == pf)

    def member(self, code: str, pf: str = "x-1") -> dict[str, str]:
        return next(m for m in self.members if m["platform_family"] == pf and m["code"] == code)

    def add_family(self, pf: str, *, status: str) -> dict:
        rid = f"R-DEC-FAM-{pf.replace('-', '').upper()}-B1"
        if status != "draft":
            self.doc["rulings"].append(ruling(rid, pf))
        fam = family(pf, status=status, ruling_id=rid if status == "published" else None)
        self.doc["families"].append(fam)
        return fam

    def add_member(self, pf: str, member_id: str, frm: int, to: int, **kv) -> dict[str, str]:
        row = member(pf, member_id, frm, to, **kv)
        self.members.append(row)
        return row

    def parse(self):
        return parse_registry(self.doc, self.members, self.era_rows, era_decisions=self.decisions)


def tmp_paths(root: Path) -> RegistryPaths:
    return RegistryPaths(root / "platform_families.json", root / "platform_family_members.csv",
                         root / "platform_family_era_lines.csv")


def write_world(root: Path, world: World) -> tuple[RegistryPaths, Path]:
    """The world as committed files plus an era seed holding its decisions."""
    paths = tmp_paths(root / "data-seeds")
    write_registry(paths, doc=world.doc, members=world.members, era_lines=world.era_rows)
    seed = root / "p1_era_code_decisions.csv"
    era_map.write_csv(seed, era_map.SEED_COLUMNS, world.decisions.values())
    return paths, seed
```

- [ ] **Step 2: Write the failing tests in `tests/test_platform_families_loader.py`**

Every red case asserts that one line of the raised `RegistryError` starts with `platform-families: <file>:<row id>: ` (or `platform-families: <file>: ` for a file-level fault) and contains the fragment. Rule ids are §9.1's.

```python
"""platform_families loader (families piece 2; spec §7, §9)."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from govbudget.jbooks import era_map
from govbudget.platform_families import (
    CAVEAT_IDS, CONTRACT_LINK_POLICIES, DEFAULT_PATHS, EDITIONS, ERA_LINE_COLUMNS, EXCLUSION_KINDS,
    EXHIBITS, FAMILY_KEYS, F15_SEED_RULING_ID, HISTORY_DATASET_RE, LINK_BASES, MEMBER_COLUMNS,
    MEMBER_ID_RE, PAYING_ORGS, PLATFORM_FAMILY_RE, PREFILL_COLUMNS, PURPOSES, REVIEW_COLUMNS,
    REVIEW_ROOT, ROLES, RULING_ID_RE, SEED_BASIS_ALLOWED, SERVICES, SHORT_NAME_RE, SOURCE_ID_RE,
    SOURCE_TIERS, STATUSES, TOP_KEYS, VARIANT_SCOPES, VERDICTS, EraLine, Headline, RegistryError,
    ReviewGuard, family_hash, load_registry, registry_texts, write_registry)
from platform_family_fixtures import (DOC_SHA, ERA_XA, RULING_X1, World, XA, XC, XR, tmp_paths,
                                      write_world)

J, M, E = "platform_families.json", "platform_family_members.csv", "platform_family_era_lines.csv"
XA_ID = "x-1|P-1:3010F:AF:XA0001|2023-2026"
XR_ID = "x-1|R-1:3600F:AF:XR0001|2025-2026"
XC_ID = "x-1|P-1:3010F:AF:XC0001|2024-2026"
ERA_ID = "x-1|2023|3010F-AF-L7"


def refused(errors, file, row, fragment) -> bool:
    head = f"platform-families: {file}:{row}: " if row else f"platform-families: {file}: "
    return any(line.startswith(head) and fragment in line for line in errors)


def assert_refused(fn, file, row, fragment):
    with pytest.raises(RegistryError) as exc:
        fn()
    assert refused(exc.value.errors, file, row, fragment), "\n".join(exc.value.errors)


def test_constants_are_the_spec_values():
    assert len(MEMBER_COLUMNS) == 49 and len(set(MEMBER_COLUMNS)) == 49
    assert MEMBER_COLUMNS[:3] == ("member_row_id", "platform_family", "member_id")
    assert MEMBER_COLUMNS[44:] == ("allocation_years", "decided_by", "ruling_id", "decided_on", "note")
    assert ERA_LINE_COLUMNS == ("platform_family", "member_id", "edition", "era_key",
                                "budget_activity", "filed_title", "decision_id")
    assert REVIEW_COLUMNS == MEMBER_COLUMNS + ("reason", "headline_actuals_k")
    assert len(PREFILL_COLUMNS) == 43 and PREFILL_COLUMNS[-1] == "reason"
    assert not {"member_row_id", "titles_seen", "budget_activities", "drift_sha256", "decided_by",
                "ruling_id", "decided_on"} & set(PREFILL_COLUMNS)
    assert (ROLES, VERDICTS, EXHIBITS, STATUSES, SOURCE_TIERS) == (
        ("counted", "context", "project_slice", "excluded"), ("approved", "deferred", "rejected"),
        ("P-1", "R-1", "P-1R"), ("draft", "ratified", "published"), ("G", "PG", "C", "X"))
    assert (PURPOSES, VARIANT_SCOPES, LINK_BASES) == (
        ("buy", "upgrade", "develop", "support"), ("variant", "shared"),
        ("book_stated", "era_map", "inferred"))
    assert CONTRACT_LINK_POLICIES == ("production+AP", "modifications_only", "development", "none")
    assert SERVICES == ("USAF", "USN", "USMC", "USA", "USSF", "SOCOM", "DW")
    assert PAYING_ORGS == ("AF", "NAVY", "USMC", "ARMY", "USSF", "SOCOM", "DW")
    assert CAVEAT_IDS == ("classified", "construction", "operating_and_support", "spares",
                          "foreign", "cr_years", "nominal_dollars")
    assert EXCLUSION_KINDS == ("outside_scope", "not_a_budget_line", "shared_line")
    assert list(EDITIONS) == list(range(2017, 2027))
    assert SEED_BASIS_ALLOWED == frozenset({"R-DEC-FAM-F15-SEED"}) and F15_SEED_RULING_ID == "R-DEC-FAM-F15-SEED"
    assert [r.pattern for r in (PLATFORM_FAMILY_RE, SHORT_NAME_RE, HISTORY_DATASET_RE, RULING_ID_RE,
                                SOURCE_ID_RE, MEMBER_ID_RE)] == [
        r"^[a-z0-9]+(-[a-z0-9]+)*$", r"^[A-Za-z0-9][A-Za-z0-9 /-]*$", r"^[a-z0-9]+_funding_history$",
        r"^R-DEC-FAM-[A-Z0-9]+(-[A-Z0-9]+)+$", r"^[a-z0-9][a-z0-9-]*$",
        r"^(P-1|R-1|P-1R):[0-9]{4}[A-Z]+:[A-Z0-9]+:[A-Z0-9]+$"]
    assert TOP_KEYS == ("schema_version", "rulings", "sources", "families")
    assert FAMILY_KEYS[:3] == ("platform_family", "status", "published_ruling_id") and len(FAMILY_KEYS) == 20
    assert DEFAULT_PATHS.json.parts[-2:] == ("data-seeds", "platform_families.json")
    assert DEFAULT_PATHS.members.name == M and DEFAULT_PATHS.era_lines.name == E
    assert REVIEW_ROOT.parts[-3:] == ("data", "research", "platform_families")


def test_minimal_published_family_loads():
    w = World()
    reg = w.parse()
    assert reg.schema_version == 1 and reg.doc == w.doc and reg.doc is not w.doc
    assert [f.platform_family for f in reg.families] == ["x-1", "y-1"]
    assert [f.platform_family for f in reg.published()] == ["x-1"]
    x = reg["x-1"]
    assert [m.member_id for m in x.counted] == [XA, XR]
    assert [m.code for m in x.code_keyed] == ["XA0001", "XR0001"]
    assert [m.member_id for m in x.context] == [XC]
    assert (x.route, x.history_path) == ("/families/x-1/", "json/x1_funding_history.json")
    assert x.headline == Headline("cumulative_actuals", 2015, 2024)
    assert x.review_guard == ReviewGuard(("P-1", "R-1"), ("X-1",))
    assert x.era_lines == (EraLine("x-1", XA, 2023, "3010F-AF-L7", "05", "X-1", ERA_XA),)
    assert reg.rulings[RULING_X1].seed_basis is False and reg.sources["x-book"].tier == "G"
    xa = x.counted[0]
    assert (xa.valid_from_edition, xa.valid_to_edition, xa.member_order) == (2023, 2026, 1)
    assert xa.titles_seen == ((2024, "X-1"), (2025, "X-1"), (2026, "X-1"))
    assert xa.evidence == (f"era:{ERA_XA}", "src:x-book#p3")
    assert x.counted[1].evidence == (f"doc:{DOC_SHA}#p1;q=X-1 development",)
    assert x.counted[1].variant_ids == ("A", "B") and xa.quantity_bearing is None
    with pytest.raises(KeyError):
        reg["z-9"]


def test_draft_family_with_zero_rows_loads():
    y = World().parse()["y-1"]
    assert (y.status, y.published_ruling_id, y.members, y.era_lines, y.counted) == (
        "draft", None, (), (), ())


def test_member_and_era_line_as_row_round_trip():
    w = World()
    x = w.parse()["x-1"]
    assert sorted((m.as_row() for m in x.members), key=lambda r: r["member_row_id"]) == sorted(
        w.members, key=lambda r: r["member_row_id"])
    assert [e.as_row() for e in x.era_lines] == w.era_rows


def test_title_for_reads_titles_seen():
    xa = World().parse()["x-1"].counted[0]
    assert (xa.title_for(2025), xa.title_for(2023)) == ("X-1", None)


def _set(target, **kv):
    return lambda w: target(w).update(kv)


FAM = lambda w: w.family()
YFAM = lambda w: w.family("y-1")
RUL = lambda w: w.doc["rulings"][0]
SRC = lambda w: w.doc["sources"][0]
MXA = lambda w: w.member("XA0001")
MXR = lambda w: w.member("XR0001")
MXC = lambda w: w.member("XC0001")

STAGE1_ROW_RULES = [
    # (case id, mutation, file, row id, fragment)
    ("r1-schema-version", lambda w: w.doc.update(schema_version=2), J, None, "schema_version"),
    ("r1-schema-version-bool", lambda w: w.doc.update(schema_version=True), J, None, "schema_version"),
    ("r1-top-unknown", lambda w: w.doc.update(notes="x"), J, None, "notes"),
    ("r1-family-missing", lambda w: w.family().pop("headline"), J, "x-1", "headline"),
    ("r1-family-unknown", _set(FAM, colour="red"), J, "x-1", "colour"),
    ("r1-ruling-unknown", _set(RUL, extra=1), J, RULING_X1, "extra"),
    ("r1-source-unknown", _set(SRC, extra=1), J, "x-book", "extra"),
    ("r1-nested-unknown", lambda w: w.family()["headline"].update(window=1), J, "x-1", "window"),
    ("r1-type", _set(FAM, coverage_notes="one note"), J, "x-1", "coverage_notes"),
    ("r1-caveat", _set(FAM, caveat_ids=["weather"]), J, "x-1", "weather"),
    ("r1-exclusion-kind", lambda w: w.family()["exclusions"][0].update(kind="guess"), J, "x-1", "guess"),
    ("r1-exclusion-duplicate", lambda w: w.family()["exclusions"].append(
        copy.deepcopy(w.family()["exclusions"][0])), J, "x-1", "exclusion_id"),
    ("r1-on-partial-corpus", _set(FAM, on_partial_corpus="ignore"), J, "x-1", "on_partial_corpus"),
    ("r1-art-generated", _set(FAM, art={"src": "a.png", "alt": "a", "caption": "An X-1",
                                        "generated": True}), J, "x-1", "AI-generated"),
    ("r1-contract-basis", _set(FAM, contract_routes={"program_codes": ["999"],
        "description_pattern": "X-1", "description_exclusions": [], "basis": "vibes"}),
     J, "x-1", "basis"),
    ("r2-regex", _set(FAM, platform_family="X_1"), J, "X_1", "platform_family"),
    ("r2-duplicate", lambda w: w.doc["families"].append(copy.deepcopy(w.family("y-1"))),
     J, "y-1", "duplicate"),
    ("r3-regex", _set(FAM, short_name="X_1"), J, "x-1", "short_name"),
    ("r3-leading-hyphen", _set(FAM, short_name="-X1"), J, "x-1", "short_name"),
    ("r3-duplicate", _set(YFAM, short_name="X-1"), J, "y-1", "short_name"),
    ("r4-regex", _set(FAM, history_dataset="x1_history"), J, "x-1", "history_dataset"),
    ("r4-duplicate", _set(YFAM, history_dataset="x1_funding_history"), J, "y-1", "history_dataset"),
    ("r5-status", _set(FAM, status="public"), J, "x-1", "status"),
    ("r6-decided-by", _set(RUL, decided_by="controller"), J, RULING_X1, "decided_by"),
    ("r6-blank-reply", _set(RUL, owner_reply="  "), J, RULING_X1, "owner_reply"),
    ("r6-bad-date", _set(RUL, decided_on="2026-13-01"), J, RULING_X1, "decided_on"),
    ("r6-non-iso-date", _set(RUL, decided_on="21 Oct 2026"), J, RULING_X1, "decided_on"),
    ("r6-ruling-id", _set(RUL, ruling_id="R-DEC-X1"), J, "R-DEC-X1", "ruling_id"),
    ("r6-duplicate", lambda w: w.doc["rulings"].append(copy.deepcopy(w.doc["rulings"][0])),
     J, RULING_X1, "duplicate"),
    ("r6-kind", _set(RUL, kind="decree"), J, RULING_X1, "kind"),
    ("r6-seed-basis", _set(RUL, seed_basis=True), J, RULING_X1, "seed_basis"),
    ("r7-tier", _set(SRC, tier="Z"), J, "x-book", "tier"),
    ("r7-sha256", _set(SRC, sha256="abc"), J, "x-book", "sha256"),
    ("r7-archive-path", lambda w: w.doc["sources"][0].pop("archive_path"), J, "x-book", "archive_path"),
    ("r7-source-id", _set(SRC, source_id="X Book"), J, "X Book", "source_id"),
    ("r7-as-of", _set(SRC, as_of="April 2026"), J, "x-book", "as_of"),
    ("r7-duplicate", lambda w: w.doc["sources"].append(copy.deepcopy(w.doc["sources"][0])),
     J, "x-book", "duplicate"),
    ("r8-row-keys", lambda w: w.members[0].pop("note"), M, XA_ID, "columns"),
    ("r9-formula", _set(MXA, member_row_id="x-1|XA0001|2023-2026"), M, "x-1|XA0001|2023-2026",
     "member_row_id"),
    ("r9-duplicate", lambda w: w.members.append(dict(w.member("XC0001"))), M, XC_ID, "duplicate"),
    ("r10-regex", _set(MXA, member_id="P-2:3010F:AF:XA0001"), M, XA_ID, "member_id"),
    ("r10-disagrees", _set(MXA, code="XA0002"), M, XA_ID, "code"),
    ("r10-modern-org", _set(MXA, member_id="P-1:3010F:F:XA0001", organization="F",
                            member_row_id="x-1|P-1:3010F:F:XA0001|2023-2026"),
     M, "x-1|P-1:3010F:F:XA0001|2023-2026", "era spelling"),
    ("r11-role", _set(MXA, role="member"), M, XA_ID, "role"),
    ("r11-verdict", _set(MXA, verdict="maybe"), M, XA_ID, "verdict"),
    ("r11-appropriation", _set(MXA, appropriation="procure"), M, XA_ID, "appropriation"),
    ("r11-purpose", _set(MXA, purpose="make"), M, XA_ID, "purpose"),
    ("r11-purpose-blank-with-page", _set(MXA, purpose=""), M, XA_ID, "purpose"),
    ("r11-variant-scope", _set(MXA, variant_scope="both"), M, XA_ID, "variant_scope"),
    ("r11-link-basis", _set(MXA, link_basis="guess"), M, XA_ID, "link_basis"),
    ("r11-contract-link-policy", _set(MXA, contract_link_policy="all"), M, XA_ID,
     "contract_link_policy"),
    ("r11-boolean", _set(MXA, quantity_bearing="yes"), M, XA_ID, "quantity_bearing"),
    ("r11-service", _set(MXA, services_using="USAF;ARMY"), M, XA_ID, "ARMY"),
    ("r11-paying-org", _set(MXA, paying_org="USN"), M, XA_ID, "paying_org"),
    ("r11-p1r-not-context", _set(MXA, exhibit="P-1R", member_id="P-1R:3010F:AF:XA0001",
                                 member_row_id="x-1|P-1R:3010F:AF:XA0001|2023-2026"),
     M, "x-1|P-1R:3010F:AF:XA0001|2023-2026", "P-1R"),
    ("r11-empty-list-item", _set(MXR, variant_ids="A;;B"), M, XR_ID, "variant_ids"),
    ("r11-drift-format", _set(MXA, drift_sha256="XYZ"), M, XA_ID, "drift_sha256"),
    ("r12-before-2017", _set(MXA, valid_from_edition="2016"), M, XA_ID, "valid_from_edition"),
    ("r12-after-2026", _set(MXA, valid_to_edition="2027"), M, XA_ID, "valid_to_edition"),
    ("r12-not-integer", _set(MXA, valid_to_edition="20x6"), M, XA_ID, "valid_to_edition"),
    ("r12-from-after-to", _set(MXA, valid_from_edition="2026", valid_to_edition="2024",
                               member_row_id="x-1|P-1:3010F:AF:XA0001|2026-2024"),
     M, "x-1|P-1:3010F:AF:XA0001|2026-2024", "valid_from_edition"),
    ("r12-coverage-outside", _set(MXA, coverage_expected_from_edition="2022"), M, XA_ID,
     "coverage_expected_from_edition"),
    ("r12-expected-next", _set(MXA, expected_next_edition="2026"), M, XA_ID, "expected_next_edition"),
    ("r12-titles-outside", _set(MXA, titles_seen="2022: X-1; 2024: X-1"), M, XA_ID, "titles_seen"),
    ("r12-titles-order", _set(MXA, titles_seen="2025: X-1; 2024: X-1"), M, XA_ID, "titles_seen"),
    ("r12-titles-format", _set(MXA, titles_seen="X-1"), M, XA_ID, "titles_seen"),
    ("r17-slice-no-project", _set(MXC, role="project_slice", verdict="deferred"), M, XC_ID,
     "project_number"),
    ("r17-project-on-counted", _set(MXA, project_number="675365"), M, XA_ID, "project_number"),
    ("r17-shared-no-scope", _set(MXR, scope_note=""), M, XR_ID, "scope_note"),
    ("r17-context-no-scope", _set(MXC, scope_note=""), M, XC_ID, "scope_note"),
    ("r17-context-coverage", _set(MXC, coverage_expected_from_edition="2024"), M, XC_ID,
     "coverage_expected_from_edition"),
    ("r17-context-order", _set(MXC, member_order="3"), M, XC_ID, "member_order"),
    ("r17-allocation-off-context", _set(MXA, allocation_years="2024"), M, XA_ID, "allocation_years"),
    ("r17-quantity-off-counted", _set(MXC, quantity_bearing="true"), M, XC_ID, "quantity_bearing"),
    ("r18-variant", _set(MXA, variant_ids="C"), M, XA_ID, "variant_ids"),
    ("r18-program-tag", _set(MXA, program_tag="X-2"), M, XA_ID, "program_tag"),
    ("r18-purpose-tag", _set(MXA, purpose_tag="sdd"), M, XA_ID, "purpose_tag"),
    ("r26-empty", lambda w: w.family()["review_guard"].update(title_substrings=[]), J, "x-1",
     "title_substrings"),
    ("r26-lower-case", lambda w: w.family()["review_guard"].update(title_substrings=["x-1"]),
     J, "x-1", "title_substrings"),
    ("r26-exhibits", lambda w: w.family()["review_guard"].update(exhibits=["P-1R"]), J, "x-1",
     "exhibits"),
    ("r27-window", lambda w: w.family()["headline"].update(first_fy=2025), J, "x-1", "headline"),
    ("r27-measure", lambda w: w.family()["headline"].update(measure="total"), J, "x-1", "measure"),
]


@pytest.mark.parametrize("mutate,file,row,fragment",
                         [c[1:] for c in STAGE1_ROW_RULES], ids=[c[0] for c in STAGE1_ROW_RULES])
def test_stage_one_red_case(mutate, file, row, fragment):
    w = World()
    mutate(w)
    assert_refused(w.parse, file, row, fragment)


def test_stage_one_lists_every_error_at_once():
    w = World()
    w.family().update(short_name="X_1")
    w.member("XC0001").update(role="member")
    with pytest.raises(RegistryError) as exc:
        w.parse()
    assert refused(exc.value.errors, J, "x-1", "short_name")
    assert refused(exc.value.errors, M, XC_ID, "role")
    assert str(exc.value) == "\n".join(exc.value.errors)


@pytest.mark.parametrize("fault,fragment", [
    (lambda b: b"\xef\xbb\xbf" + b, "BOM"),
    (lambda b: b.replace(b"\n", b"\r\n"), "carriage return"),
    (lambda b: b + b"\n", "trailing blank line"),
], ids=["bom", "crlf", "trailing-blank-line"])
@pytest.mark.parametrize("which", ["json", "members", "era_lines"])
def test_bom_crlf_and_trailing_blank_line_are_refused_naming_the_file(tmp_path, fault, fragment, which):
    paths, seed = write_world(tmp_path, World())
    target = getattr(paths, which)
    target.write_bytes(fault(target.read_bytes()))
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), target.name, None, fragment)


def test_duplicate_json_keys_are_refused(tmp_path):
    paths, seed = write_world(tmp_path, World())
    text = paths.json.read_text(encoding="utf-8")
    paths.json.write_text(text.replace('"short_name": "X-1",', '"short_name": "X-1",\n      "short_name": "X-1",', 1),
                          encoding="utf-8")
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), J, None, "duplicate key 'short_name'")


def test_field_whitespace_is_not_stripped(tmp_path):
    w = World()
    w.member("XA0001").update(role=" counted")
    paths, seed = write_world(tmp_path, w)
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), M, XA_ID, "' counted'")


def test_unquoted_comma_shifts_columns_and_fails_the_header_count(tmp_path):
    paths, seed = write_world(tmp_path, World())
    text = paths.members.read_text(encoding="utf-8")
    paths.members.write_text(text.replace("A shared spares line; never summed.",
                                          "A shared spares line, never summed."), encoding="utf-8")
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), M, XC_ID,
                   "50 fields, the header has 49")


@pytest.mark.parametrize("which,columns", [("members", MEMBER_COLUMNS), ("era_lines", ERA_LINE_COLUMNS)])
def test_header_other_than_the_frozen_tuple_is_refused(tmp_path, which, columns):
    paths, seed = write_world(tmp_path, World())
    target = getattr(paths, which)
    lines = target.read_text(encoding="utf-8").split("\n")
    lines[0] = ",".join(reversed(columns))
    target.write_text("\n".join(lines), encoding="utf-8")
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), target.name, None, "header")


def test_missing_file_and_non_json_are_refused(tmp_path):
    paths, seed = write_world(tmp_path, World())
    paths.era_lines.unlink()
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), E, None, "missing")
    paths, seed = write_world(tmp_path / "b", World())
    paths.json.write_text("{\n", encoding="utf-8")
    assert_refused(lambda: load_registry(paths, era_decisions_path=seed), J, None, "JSON")


def test_write_registry_serializes_per_d11(tmp_path):
    w = World()
    w.doc["families"][0] = dict(reversed(list(w.family().items())))
    w.family().update(scope_note="X-1 – scope")
    paths = tmp_paths(tmp_path)
    write_registry(paths, doc=w.doc, members=list(reversed(w.members)), era_lines=w.era_rows)
    text = paths.json.read_text(encoding="utf-8")
    doc = json.loads(text)
    assert list(doc) == list(TOP_KEYS)
    assert list(doc["families"][0]) == [k for k in FAMILY_KEYS if k in w.family()]
    assert text.startswith('{\n  "schema_version": 1,\n') and "X-1 – scope" in text
    assert text.endswith("}\n") and not text.endswith("\n\n")
    members = paths.members.read_text(encoding="utf-8").split("\n")
    assert members[0] == ",".join(MEMBER_COLUMNS) and members[-1] == ""
    assert [line.split(",", 1)[0] for line in members[1:-1]] == [XA_ID, XC_ID, XR_ID]
    assert b"\r" not in paths.members.read_bytes() + paths.era_lines.read_bytes()


def test_registry_texts_are_what_write_registry_writes(tmp_path):
    w = World()
    paths = tmp_paths(tmp_path)
    texts = registry_texts(paths, doc=w.doc, members=w.members, era_lines=w.era_rows)
    write_registry(paths, doc=w.doc, members=w.members, era_lines=w.era_rows)
    assert set(texts) == {paths.json, paths.members, paths.era_lines}
    assert all(p.read_text(encoding="utf-8") == t for p, t in texts.items())


def test_write_registry_round_trips_byte_for_byte(tmp_path):
    paths, seed = write_world(tmp_path, World())
    reg = load_registry(paths, era_decisions_path=seed)
    again = tmp_paths(tmp_path / "again")
    write_registry(again, doc=reg.doc, members=[m.as_row() for f in reg.families for m in f.members],
                   era_lines=[e.as_row() for f in reg.families for e in f.era_lines])
    for name in ("json", "members", "era_lines"):
        assert getattr(again, name).read_bytes() == getattr(paths, name).read_bytes()


def test_write_registry_writes_nothing_when_a_replace_fails(tmp_path, monkeypatch):
    paths, _seed = write_world(tmp_path, World())
    before = {p.name: p.read_bytes() for p in paths.json.parent.iterdir()}

    def fail(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(era_map.os, "replace", fail)
    w = World()
    w.family().update(scope_note="changed")
    with pytest.raises(OSError, match="disk full"):
        write_registry(paths, doc=w.doc, members=w.members, era_lines=w.era_rows)
    assert {p.name: p.read_bytes() for p in paths.json.parent.iterdir()} == before


def _d10(fam, sources):
    text = json.dumps({"family": fam, "sources": sources}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_family_hash_is_d10():
    w = World()
    assert family_hash(w.doc, "x-1") == _d10(w.family(), [w.doc["sources"][0]])
    assert family_hash(w.doc, "y-1") == _d10(w.family("y-1"), [])
    shuffled = copy.deepcopy(w.doc)
    shuffled["families"][0] = dict(reversed(list(w.family().items())))
    assert family_hash(shuffled, "x-1") == family_hash(w.doc, "x-1")
    changed = World()
    changed.family()["exclusions"][0]["size_text"] = "X-1 spares: $2.0M in FY2024"
    retiered = World()
    retiered.doc["sources"][0]["tier"] = "PG"
    assert family_hash(changed.doc, "x-1") != family_hash(w.doc, "x-1")
    assert family_hash(retiered.doc, "x-1") != family_hash(w.doc, "x-1")
    uncited = World()
    uncited.doc["sources"].append(dict(w.doc["sources"][0], source_id="uncited"))
    assert family_hash(uncited.doc, "x-1") == family_hash(w.doc, "x-1")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_loader.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'govbudget.platform_families'`.

- [ ] **Step 4: Write the constants, types and paths in `src/govbudget/platform_families.py`**

The module docstring names spec §7 and §9. Module-level imports are only the standard library, `govbudget.config` and `govbudget.jbooks.era_map` (stage 1 runs on every import of the facade, `program_pdf_receipts` and `export_site`); `export_site` and `duckdb` are imported inside the Task 2c functions.

Pinned values (the vocabularies and regexes are the I-REG tables; the rest are spec §7.2/§7.3 key and column orders):

```python
REGISTRY_JSON = config.ROOT / "data-seeds" / "platform_families.json"
MEMBERS_CSV = config.ROOT / "data-seeds" / "platform_family_members.csv"
ERA_LINES_CSV = config.ROOT / "data-seeds" / "platform_family_era_lines.csv"
REVIEW_ROOT = config.RESEARCH_DIR / "platform_families"
MEMBER_COLUMNS = (  # spec §7.3, frozen order
    "member_row_id", "platform_family", "member_id", "exhibit", "account", "organization", "code",
    "role", "verdict", "project_number", "appropriation", "budget_activities", "titles_seen",
    "display_title", "page_slug", "valid_from_edition", "valid_to_edition",
    "coverage_expected_from_edition", "expected_next_edition", "era_decision_ids", "drift_sha256",
    "member_order", "program_tag", "purpose_tag", "purpose", "variant_ids", "variant_scope",
    "scope_note", "services_using", "paying_org", "predecessor_member_id", "successor_member_id",
    "link_basis", "link_evidence", "evidence", "quantity_bearing", "quantity_row", "quantity_notes",
    "jbook_anchor", "contract_link_policy", "msar_account", "msar_funding_source_page",
    "msar_shared_flag", "allocation_source", "allocation_years", "decided_by", "ruling_id",
    "decided_on", "note")
ERA_LINE_COLUMNS = ("platform_family", "member_id", "edition", "era_key", "budget_activity",
                    "filed_title", "decision_id")
REVIEW_COLUMNS = MEMBER_COLUMNS + ("reason", "headline_actuals_k")
PREFILL_COLUMNS = tuple(c for c in MEMBER_COLUMNS if c not in {
    "member_row_id", "titles_seen", "budget_activities", "drift_sha256", "decided_by", "ruling_id",
    "decided_on"}) + ("reason",)
ON_PARTIAL_CORPUS = ("skip", "raise")
RULING_KINDS = ("class", "batch")
HEADLINE_MEASURES = ("cumulative_actuals",)
GUARD_EXHIBITS = ("P-1", "R-1")
EDITIONS = range(2017, 2027)
SEED_BASIS_ALLOWED = frozenset({"R-DEC-FAM-F15-SEED"})
F15_SEED_RULING_ID = "R-DEC-FAM-F15-SEED"
TOP_KEYS = ("schema_version", "rulings", "sources", "families")
RULING_KEYS = ("ruling_id", "kind", "platform_family", "decided_by", "decided_on", "owner_reply",
               "spec", "text", "seed_basis")
SOURCE_KEYS = ("source_id", "title", "publisher", "url", "as_of", "sha256", "bytes", "archived",
               "archive_path", "tier", "verified_by")           # optional: sha256, bytes, archive_path, verified_by
FAMILY_KEYS = ("platform_family", "status", "published_ruling_id", "short_name", "history_dataset",
               "on_partial_corpus", "headline", "scope_note", "coverage_notes", "review_guard",
               "program_notes", "variants", "program_tags", "purpose_tags", "caveat_ids",
               "exclusions", "aliases", "contract_routes", "official_estimates", "art")  # optional: published_ruling_id
HEADLINE_KEYS = ("measure", "first_fy", "last_fy")
GUARD_KEYS = ("exhibits", "title_substrings")
PROGRAM_NOTE_KEYS = ("note", "note_fact_id", "expected_receipt")
RECEIPT_KEYS = ("kind", "page_number", "pe_bli", "sha256")
VARIANT_KEYS = ("id", "note")                                   # note optional
PROGRAM_TAG_KEYS = ("tag", "mdap_code")                         # mdap_code str or null
EXCLUSION_KEYS = ("exclusion_id", "kind", "label", "size_text", "evidence")
CONTRACT_ROUTE_KEYS = ("program_codes", "description_pattern", "description_exclusions", "basis")  # basis: action|award
OFFICIAL_ESTIMATE_KEYS = ("msar_program_number", "msar_source_ids", "gao_program_key", "wsaa_exit_ruling")
ART_KEYS = ("src", "alt", "caption", "generated")              # generated true needs "AI-generated" in caption
```

Plus the I-REG vocabulary tuples `ROLES` … `EXCLUSION_KINDS` and the six regexes (`re.compile`, patterns exactly as Step 2 asserts), and `class RegistryPaths`/`DEFAULT_PATHS = RegistryPaths(REGISTRY_JSON, MEMBERS_CSV, ERA_LINES_CSV)`. Every regex in this module is applied with `.fullmatch` (a bare `$` would accept a trailing newline).

Types (all `@dataclass(frozen=True)` except `RegistryError`):
- `class RegistryError(ValueError)`: `__init__(self, errors: Sequence[str])`; `.errors: list[str]`; `str()` is `"\n".join(errors)`.
- `Ruling(ruling_id, kind, platform_family, decided_by, decided_on, owner_reply, spec, text: str, seed_basis: bool)`.
- `Source(source_id, title, publisher, url, as_of: str, sha256: str | None, bytes: int | None, archived: bool, archive_path: str | None, tier: str, verified_by: tuple[str, ...])`.
- `Member`: one field per `MEMBER_COLUMNS` name, in that order. `valid_from_edition`, `valid_to_edition`, `coverage_expected_from_edition`, `expected_next_edition`, `member_order`: `int | None`. `titles_seen: tuple[tuple[int, str], ...]`. `budget_activities`, `era_decision_ids`, `variant_ids`, `services_using`, `allocation_years`: `tuple[str, ...]` (`;`-split). `evidence`, `link_evidence`: `tuple[str, ...]` (`split_refs`). `quantity_bearing`, `msar_shared_flag`: `bool | None`. Every other column: `str`. Methods: `@classmethod from_row(cls, row: Mapping[str, str]) -> Member` (raises `ValueError` on an unparsable value; used by stage 1 after its checks, by the seed and by `propose`), `title_for(edition: int) -> str | None`, `as_row() -> dict[str, str]` (the exact inverse: `as_row(from_row(r)) == r` for every row stage 1 accepts; `titles_seen` renders `"; ".join(f"{e}: {t}")`, lists `";".join`, `None` as `""`, booleans `"true"`/`"false"`).
- `EraLine(platform_family, member_id: str, edition: int, era_key, budget_activity, filed_title, decision_id: str)` with `as_row() -> dict[str, str]`.
- `Headline(measure: str, first_fy: int, last_fy: int)`; `ReviewGuard(exhibits: tuple[str, ...], title_substrings: tuple[str, ...])`; `ProgramNote(note: str, note_fact_id: str, expected_receipt: Mapping[str, object])`.
- `Family`: one field per `FAMILY_KEYS` name (`published_ruling_id: str | None`; `headline: Headline`; `review_guard: ReviewGuard`; `program_notes: Mapping[str, ProgramNote]` keyed by member_id; lists as tuples; reserved objects `Mapping | None`), then `members: tuple[Member, ...]` (every CSV row of the family, CSV order) and `era_lines: tuple[EraLine, ...]`. Properties: `counted` (approved `counted` rows by `member_order`), `code_keyed` (D5: `counted` rows with a non-empty `titles_seen`, same order), `context` (approved `context` rows by `member_id`), `route` (`f"/families/{platform_family}/"`), `history_path` (`f"json/{history_dataset}.json"`).
- `Registry(schema_version: int, rulings: Mapping[str, Ruling], sources: Mapping[str, Source], families: tuple[Family, ...], doc: dict)`: `rulings`/`sources` keyed by id in JSON order; `doc` is a deep copy of the input; `__getitem__(platform_family) -> Family` raises `KeyError`; `published() -> tuple[Family, ...]` (status `published`, JSON order).

- [ ] **Step 5: Write `split_refs`, `parse_registry` (Task 2a's rules) and `load_registry`**

`split_refs(text: str) -> tuple[str, ...]`: `""` → `()`; split on `;`; a segment that starts with `q=` is re-attached (`prev + ";" + seg`) to the segment before it when that one starts with `doc:` and carries no `;q=` yet, otherwise `ValueError("dangling q=")`; an empty segment raises `ValueError("empty list item")`. It does not validate prefixes (Task 2b's `parse_ref` does).

`parse_registry(doc: dict, member_rows: Sequence[Mapping[str, str]], era_rows: Sequence[Mapping[str, str]], *, era_decisions: Mapping[str, Mapping[str, str]], paths: RegistryPaths = DEFAULT_PATHS) -> Registry`: pure; collects every error, then raises one `RegistryError`. Each line is `f"platform-families: {file}:{row_id}: {reason}"`, or `f"platform-families: {file}: {reason}"` for a file-level fault, where:
- `file` is `paths.json.name`, `paths.members.name` or `paths.era_lines.name`;
- the JSON row id is the entry's `platform_family`, `ruling_id` or `source_id` as written (`families[<i>]`, `rulings[<i>]`, `sources[<i>]` when that key is missing or not a string); the members row id is `member_row_id` as written; the era-lines row id is `f"{platform_family}|{edition}|{era_key}"` as written;
- every reason names the key or column it is about and quotes the offending value with `repr` (Step 2's fragments rely on this).

Task 2a's checks (§9.1 rule numbers; Task 2b adds the rest to the same function):
- **Rule 1.** `TOP_KEYS` exactly; each family, ruling, source and nested object against its key tuple (required = all but the optional ones named in Step 4); JSON types: strings, `bool` (never an int) for `seed_basis`/`archived`/`art.generated`, `int` (never a `bool`) for `schema_version`/`bytes`/`first_fy`/`last_fy`/`page_number`, lists of strings for `coverage_notes`/`purpose_tags`/`caveat_ids`/`aliases`/`verified_by`/`exclusions[].evidence` (an empty list is valid: the F-35's `before-fy2015` and `classified` cite nothing, R12); `caveat_ids` ⊆ `CAVEAT_IDS`; `exclusions[].kind` ∈ `EXCLUSION_KINDS`, `exclusion_id` unique in its family; `on_partial_corpus` ∈ `ON_PARTIAL_CORPUS`; `contract_routes.basis` ∈ (`action`, `award`); `art.generated` true needs `"AI-generated"` in `caption` (the reason quotes `AI-generated`).
- **Rules 2–4.** Regex and uniqueness across families; a duplicate is reported on the second occurrence's row id, its reason containing `duplicate` and the key name.
- **Rule 5 (vocabulary only).** `status` ∈ `STATUSES`.
- **Rule 6.** `decided_by == "owner"`; `owner_reply.strip()` non-empty; `decided_on` matches `^\d{4}-\d{2}-\d{2}$` and `date.fromisoformat` accepts it; `RULING_ID_RE`; unique (`duplicate`); `kind` ∈ `RULING_KINDS`; `seed_basis` true only for an id in `SEED_BASIS_ALLOWED`.
- **Rule 7 (entry checks).** `SOURCE_ID_RE`, unique; `tier` ∈ `SOURCE_TIERS`; `sha256`, when present, `^[0-9a-f]{64}$`; `as_of` ISO as in rule 6; `archived` true needs `archive_path`.
- **Rule 8.** Each member row's keys are exactly `MEMBER_COLUMNS` in order, each era row's `ERA_LINE_COLUMNS` (reason word `columns`).
- **Rule 9.** `member_row_id == f"{platform_family}|{member_id}|{valid_from_edition}-{valid_to_edition}"`; unique.
- **Rule 10.** `MEMBER_ID_RE`; its four parts equal `exhibit`, `account`, `organization`, `code`; `organization` not a value of `era_map.ERA_ORG_TO_MODERN` (reason contains `era spelling`).
- **Rule 11.** Required non-empty: `platform_family`, `member_id`, `exhibit`, `account`, `organization`, `code`, `role`, `verdict`, `appropriation`, `display_title`. Vocabularies: `role`, `verdict`, `exhibit`, `appropriation` always; `purpose`, `variant_scope`, `link_basis`, `contract_link_policy`, `paying_org` when non-blank; every `services_using` item ∈ `SERVICES`. `purpose` blank only when `page_slug` is blank. `P-1R` only with role `context`. `;`-lists reject an empty item. Booleans are blank, `true` or `false`. `drift_sha256` is `^[0-9a-f]{64}$`, required on `approved` rows. `quantity_row` blank or `^[A-Z]$`; `msar_funding_source_page` blank or `^[1-9][0-9]*$`; `jbook_anchor` blank or `^doc:[0-9a-f]{64}#p[1-9][0-9]*;xml=[^;]+;units=(Thousands|Millions)$`; `allocation_years` items `^[0-9]{4}$`. Never strip a field.
- **Rule 12.** `valid_from_edition`/`valid_to_edition` match `^[0-9]{4}$` and lie in `EDITIONS`; from ≤ to; `coverage_expected_from_edition` blank or in [from, to]; `expected_next_edition` blank or > to; `member_order` blank or `^[1-9][0-9]*$`; `titles_seen` blank or `"; "`-joined `"{edition}: {title}"` items (`^([0-9]{4}): (.+)$`), editions strictly ascending and inside [from, to].
- **Rule 17**, **rule 18** (blank `program_tag`/`purpose_tag` allowed; a non-blank one must be in the family's list; every `variant_ids` item must be a `variants[].id`; duplicates inside a family's `variants`, `program_tags` or `purpose_tags` fail too), **rule 26** (`title_substrings` non-empty, every item non-empty and equal to its `.upper()`; `exhibits` a non-empty subset of `GUARD_EXHIBITS`), **rule 27** (`first_fy <= last_fy`, else reason contains `headline`; `measure` ∈ `HEADLINE_MEASURES`), as spec §9.1 words them.

On no error it builds the `Registry`: rows attach to the family named by their `platform_family` (Task 2b reports rows whose family is missing); era rows build `EraLine`s on the same family.

`load_registry(paths: RegistryPaths = DEFAULT_PATHS, *, era_decisions_path: Path | None = None) -> Registry`: reads the three files as bytes and refuses, all at once, file by file (file-level lines, no row id): a missing file (`missing`), a UTF-8 BOM (`BOM`), bytes that are not UTF-8, any `\r` (`carriage return`), an empty file, a file not ending in `\n`, a file ending in `\n\n` (`trailing blank line`); JSON that does not parse (`JSON`); a duplicate key in any JSON object (`object_pairs_hook`; reason `duplicate key '<key>'`); a CSV header other than the frozen tuple (`header`); a CSV row whose field count differs from the header's (row id = the row's first field for members, its `{0}|{2}|{3}` fields for era lines when present, else `line <n>`; reason `<n> fields, the header has <m>`). CSVs are read with `csv.reader` (no `skipinitialspace`). Any file-level fault raises here, before `parse_registry` runs. Era decisions: `era_map.read_seed(era_decisions_path or era_map.default_seed_path())`, keyed by `decision_id`. Then `parse_registry(doc, rows, era_rows, era_decisions=…, paths=paths)`.

- [ ] **Step 6: Write `registry_texts`, `write_registry` and `family_hash`**

`registry_texts(paths: RegistryPaths, *, doc: dict, members: Sequence[Mapping[str, str]], era_lines: Sequence[Mapping[str, str]]) -> dict[Path, str]` (D11) returns `{paths.json: …, paths.members: …, paths.era_lines: …}`: JSON text `json.dumps(canonical, indent=2, ensure_ascii=False) + "\n"`, where `canonical` re-orders every object's keys by its key tuple (Step 4; `program_notes` keys sorted by member_id, families and list items in their given order) and raises `ValueError` on a key no tuple names; members text `era_map._csv_text(MEMBER_COLUMNS, sorted(members, key=lambda r: r["member_row_id"]))`; era-lines text `era_map._csv_text(ERA_LINE_COLUMNS, sorted(era_lines, key=lambda r: (r["platform_family"], r["edition"], r["era_key"])))`. `write_registry(paths, *, doc, members, era_lines) -> None` is `era_map._atomic_write_texts(registry_texts(paths, doc=doc, members=members, era_lines=era_lines))`. Neither validates (callers run `parse_registry` first).

`family_hash(doc: dict, platform_family: str) -> str` (D10): sha256 hex of the UTF-8 bytes of `json.dumps({"family": <the family object>, "sources": [<sources>]}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, where `<sources>` are the `doc["sources"]` entries named by a `src:` ref in the family object's `exclusions[].evidence` (the only refs a family object holds), sorted by `source_id`, each as written.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_loader.py -q`
Expected: `108 passed` (15 single tests, 82 `test_stage_one_red_case`, 9 BOM/CRLF/blank-line, 2 headers).

- [ ] **Step 8: Lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uvx --offline ruff check --isolated --select F,E9 src/govbudget/platform_families.py tests/platform_family_fixtures.py tests/test_platform_families_loader.py`
Expected: `All checks passed!`

- [ ] **Step 9: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_families.py GovBudget/tests/platform_family_fixtures.py GovBudget/tests/test_platform_families_loader.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): registry formats and per-row stage-1 rules (piece 2 task 2a)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2b: Stage-1 cross-row and cross-file rules

**Spec:** §7.5 (typed refs, tiers, the independent-signal bar), §9.1 rules 5 (the ruling link; a `draft` carrying `published_ruling_id`), 7 (citation checks), 13–16, 19–25 (rule 23 as amended 2026-10-20); Review Focus 2 (the `;` in `q=`).

**Files:**
- Modify: `src/govbudget/platform_families.py` (add `parse_ref`, `INDEPENDENT_TIERS`; extend `parse_registry`)
- Test: `tests/test_platform_families_loader.py` (append)

**Interfaces:**
- Consumes: Task 2a's `World`, `parse_registry`, `split_refs`, `load_registry`, `write_world`; `govbudget.jbooks.era_keys._ERA_KEY_RE = re.compile(r"^(\d{4}[A-Z])-([A-Z]+)-L([0-9][0-9A-Za-z-]*)\Z")` (`era_keys.py:73`); `govbudget.jbooks.era_map.ORG_SPLIT_CODES = frozenset({"10", "15", "20", "30", "500"})` (`era_map.py:59`).
- Produces:
  - `parse_ref(ref: str) -> tuple[str, dict]`, raising `ValueError` on a malformed ref. Parts: `era` → `{"decision_id"}`; `fact` → `{"fact_id"}`; `doc` → `{"sha256", "page": int, "quote": str | None}`; `src` → `{"source_id", "page": int | None}`; `ev` → `{"id"}`. Used by Task 2c (stage 2), Task 5 (stage 3) and Task 7b (`propose`).
  - `INDEPENDENT_TIERS = frozenset({"G", "PG"})`.
  - `parse_registry` complete for stage 1.

- [ ] **Step 1: Write the failing tests (append to `tests/test_platform_families_loader.py`)**

Add `parse_ref` and `split_refs` to the `govbudget.platform_families` import and `ruling` to the `platform_family_fixtures` import at the top of the file, then append:

```python
A64 = "a" * 64


def test_parse_ref_reads_every_prefix():
    assert parse_ref("era:F01500|3010F||2017-2023") == ("era", {"decision_id": "F01500|3010F||2017-2023"})
    assert parse_ref("fact:0026c924483c6624") == ("fact", {"fact_id": "0026c924483c6624"})
    assert parse_ref(f"doc:{A64}#p71;q=funded outside this exhibit") == (
        "doc", {"sha256": A64, "page": 71, "quote": "funded outside this exhibit"})
    assert parse_ref(f"doc:{A64}#p3") == ("doc", {"sha256": A64, "page": 3, "quote": None})
    assert parse_ref("src:msar-pb2027#p25") == ("src", {"source_id": "msar-pb2027", "page": 25})
    assert parse_ref("src:msar-pb2027") == ("src", {"source_id": "msar-pb2027", "page": None})
    assert parse_ref("ev:E-17") == ("ev", {"id": "E-17"})


@pytest.mark.parametrize("ref", [
    "", "web:x", "era:F01500", "fact:XYZ", "fact:0026c924483c662", "doc:abc#p1", f"doc:{A64}",
    f"doc:{A64}#p0", f"doc:{A64}#p1;q=", f"doc:{A64}#p1;q=a;b", "src:Msar", "src:msar#p", "ev:"])
def test_parse_ref_refuses_malformed(ref):
    with pytest.raises(ValueError):
        parse_ref(ref)


def test_split_refs_reattaches_quotes():
    assert split_refs(f"era:XA0001|3010F||2023-2023;doc:{A64}#p3;q=Lot 1 aircraft;src:x-book") == (
        "era:XA0001|3010F||2023-2023", f"doc:{A64}#p3;q=Lot 1 aircraft", "src:x-book")
    assert split_refs("") == ()
    with pytest.raises(ValueError):
        split_refs("q=orphan")


def test_doc_ref_quote_with_semicolon_is_refused():
    w = World()
    w.member("XR0001").update(evidence=f"doc:{DOC_SHA}#p1;q=X-1 development; continued")
    assert_refused(w.parse, M, XR_ID, "';'")


def _z1(w, **kv):
    """A ratified family z-1 counting XA0001 in 2024–2026 (the double-count hazard)."""
    w.add_family("z-1", status="ratified")
    return w.add_member("z-1", XA, 2024, 2026, role="counted", member_order="1",
                        titles_seen="2024: X-1; 2025: X-1; 2026: X-1", display_title="X-1",
                        drift_sha256="0" * 64, program_tag="Z-1", evidence="src:x-book#p3", **kv)


def test_one_member_counted_in_two_families_is_refused():
    w = World()
    _z1(w)
    assert_refused(w.parse, M, "z-1|P-1:3010F:AF:XA0001|2024-2026", "x-1")


def test_a_draft_carrying_published_ruling_id_is_refused():
    w = World()
    w.family("y-1")["published_ruling_id"] = RULING_X1
    assert_refused(w.parse, J, "y-1", "published_ruling_id")


def test_load_registry_resolves_era_refs_against_the_committed_era_seed(tmp_path):
    paths, seed = write_world(tmp_path, World())
    assert load_registry(paths, era_decisions_path=seed)["x-1"].counted[0].code == "XA0001"
    assert_refused(lambda: load_registry(paths), M, XA_ID, f"era:{ERA_XA}")   # not in the committed seed


def _c_source(w, **kv):
    entry = dict(w.doc["sources"][0], source_id="c-claim", tier="C", verified_by=[])
    entry.update(kv)
    w.doc["sources"].append(entry)
    w.member("XA0001").update(evidence=f"era:{ERA_XA};src:x-book#p3;src:c-claim")


def _deferred_xa(w):
    w.add_member("x-1", XA, 2026, 2026, role="counted", verdict="deferred")


def _org_split_context(w):
    w.add_member("x-1", "P-1:0300D:DTRA:20", 2024, 2026, role="context", scope_note="Shared.",
                 drift_sha256="0" * 64, evidence="era:20|0300D|DSS|2022-2022")


def _y1_ruling(w) -> str:
    w.doc["rulings"].append(ruling("R-DEC-FAM-Y1-B1", "y-1"))
    return "R-DEC-FAM-Y1-B1"


def _z1_era(w):
    w.add_family("z-1", status="ratified")
    w.add_member("z-1", "P-1:3010F:AF:XZ0001", 2023, 2026, role="counted", member_order="1",
                 display_title="Z", drift_sha256="0" * 64, program_tag="Z-1",
                 era_decision_ids="XZ0001|3010F||2023-2023", evidence="src:x-book#p3")
    w.era_rows.append(dict(w.era_rows[0], platform_family="z-1", member_id="P-1:3010F:AF:XZ0001",
                           decision_id="XZ0001|3010F||2023-2023"))


NOTE = {"note": "A note.", "note_fact_id": "0026c924483c6624",
        "expected_receipt": {"kind": "jbook_narrative", "page_number": 1, "pe_bli": "XA0001", "sha256": A64}}
ERA0 = lambda w: w.era_rows[0]

STAGE1_CROSS_RULES = [
    ("r5-published-no-ruling", lambda w: w.family().pop("published_ruling_id"), J, "x-1",
     "published_ruling_id"),
    ("r5-unknown-ruling", _set(FAM, published_ruling_id="R-DEC-FAM-X1-B9"), J, "x-1", "R-DEC-FAM-X1-B9"),
    ("r5-other-familys-ruling", lambda w: FAM(w).update(published_ruling_id=_y1_ruling(w)), J, "x-1", "y-1"),
    ("r7-x-cited-by-row", _set(SRC, tier="X"), M, XA_ID, "tier X"),
    ("r7-x-cited-by-exclusion", lambda w: (SRC(w).update(tier="X"), MXA(w).update(
        evidence=f"doc:{DOC_SHA}#p1"), MXC(w).update(evidence="")), J, "x-1", "tier X"),
    ("r7-c-unverified", _c_source, M, XA_ID, "verified_by"),
    ("r7-c-verified-by-c", lambda w: _c_source(w, verified_by=["c-claim"]), M, XA_ID, "verified_by"),
    ("r13-overlap", _deferred_xa, M, "x-1|P-1:3010F:AF:XA0001|2026-2026", "overlap"),
    ("r15-shared-code", lambda w: w.add_member(
        "x-1", "R-1:3600F:AF:XA0001", 2025, 2026, role="counted", member_order="3", display_title="X",
        drift_sha256="0" * 64, program_tag="X-1", evidence="src:x-book#p3"),
     M, "x-1|R-1:3600F:AF:XA0001|2025-2026", "code"),
    ("r16-gap", _set(MXR, member_order="3"), M, XR_ID, "member_order"),
    ("r16-on-deferred", lambda w: (_deferred_xa(w), w.members[-1].update(member_order="3")),
     M, "x-1|P-1:3010F:AF:XA0001|2026-2026", "member_order"),
    ("r19-unknown-predecessor", _set(MXR, predecessor_member_id="P-1:3010F:AF:QQ0001",
                                     link_basis="inferred"), M, XR_ID, "predecessor_member_id"),
    ("r19-no-basis", _set(MXR, predecessor_member_id=XA), M, XR_ID, "link_basis"),
    ("r19-book-stated-no-quote", _set(MXR, predecessor_member_id=XA, link_basis="book_stated",
                                      link_evidence="src:x-book#p3"), M, XR_ID, "book_stated"),
    ("r20-malformed", _set(MXA, evidence="web:x"), M, XA_ID, "web:x"),
    ("r20-malformed-exclusion", lambda w: w.family()["exclusions"][0].update(evidence=["web:x"]),
     J, "x-1", "web:x"),
    ("r20-era-unresolved", _set(MXA, evidence="era:XQ0001|3010F||2023-2023;src:x-book#p3"),
     M, XA_ID, "XQ0001"),
    ("r20-era-other-code", _set(MXA, evidence="era:XB0001|3010F||2023-2023;src:x-book#p3"),
     M, XA_ID, "XB0001"),
    ("r20-era-excluded", _set(MXA, evidence="era:XA0001|3010F||2017-2022;src:x-book#p3"),
     M, XA_ID, "exclude_placeholder"),
    ("r20-era-org-split", _org_split_context, M, "x-1|P-1:0300D:DTRA:20|2024-2026", "organization"),
    ("r20-src-unknown", _set(MXA, evidence=f"era:{ERA_XA};src:nope"), M, XA_ID, "nope"),
    ("r20-no-independent-signal", _set(MXA, evidence=f"era:{ERA_XA}"), M, XA_ID, "independent"),
    ("r20-fact-is-not-enough", _set(MXA, evidence=f"era:{ERA_XA};fact:0026c924483c6624"),
     M, XA_ID, "independent"),
    ("r21-unresolved", _set(MXA, era_decision_ids="XQ0001|3010F||2023-2023"), M, XA_ID,
     "era_decision_ids"),
    ("r21-other-code", _set(MXA, era_decision_ids="XB0001|3010F||2023-2023"), M, XA_ID, "XB0001"),
    ("r22-decided-by", _set(MXA, decided_by=""), M, XA_ID, "decided_by"),
    ("r22-unknown-ruling", _set(MXA, ruling_id="R-DEC-FAM-X1-B9"), M, XA_ID, "R-DEC-FAM-X1-B9"),
    ("r22-other-familys-ruling", lambda w: MXA(w).update(ruling_id=_y1_ruling(w)), M, XA_ID, "y-1"),
    ("r22-decided-on", _set(MXA, decided_on="2026-10-20"), M, XA_ID, "decided_on"),
    ("r23-row-without-family", _set(MXC, platform_family="q-1", member_row_id="q-1|P-1:3010F:AF:XC0001|2024-2026"),
     M, "q-1|P-1:3010F:AF:XC0001|2024-2026", "q-1"),
    ("r23-ratified-without-rows", _set(YFAM, status="ratified"), J, "y-1", "no member rows"),
    ("r24-key-not-counted", _set(FAM, program_notes={XC: NOTE}), J, "x-1", "program_notes"),
    ("r24-empty-note", _set(FAM, program_notes={XA: dict(NOTE, note="")}), J, "x-1", "note"),
    ("r24-fact-id", _set(FAM, program_notes={XA: dict(NOTE, note_fact_id="XYZ")}), J, "x-1", "note_fact_id"),
    ("r24-receipt-keys", _set(FAM, program_notes={XA: dict(NOTE, expected_receipt={
        "kind": "jbook_narrative", "page_number": 1, "sha256": A64})}), J, "x-1", "expected_receipt"),
    ("r25-not-counted", _set(ERA0, member_id=XC), E, ERA_ID, "approved counted"),
    ("r25-edition-outside", _set(ERA0, edition="2022"), E, "x-1|2022|3010F-AF-L7", "edition"),
    ("r25-key-regex", _set(ERA0, era_key="3010F-AF-7"), E, "x-1|2023|3010F-AF-7", "era_key"),
    ("r25-key-account", _set(ERA0, era_key="3011F-AF-L7"), E, "x-1|2023|3011F-AF-L7", "account"),
    ("r25-key-org", _set(ERA0, era_key="3010F-NAVY-L7"), E, "x-1|2023|3010F-NAVY-L7", "organization"),
    ("r25-decision", _set(ERA0, decision_id="XB0001|3010F||2023-2023"), E, ERA_ID, "decision_id"),
    ("r25-duplicate", lambda w: w.era_rows.append(dict(w.era_rows[0])), E, ERA_ID, "duplicate"),
    ("r25-two-families", _z1_era, E, "z-1|2023|3010F-AF-L7", "x-1"),
]


@pytest.mark.parametrize("mutate,file,row,fragment",
                         [c[1:] for c in STAGE1_CROSS_RULES], ids=[c[0] for c in STAGE1_CROSS_RULES])
def test_stage_one_cross_red_case(mutate, file, row, fragment):
    w = World()
    mutate(w)
    assert_refused(w.parse, file, row, fragment)


def test_a_c_source_verified_by_a_g_source_may_be_cited():
    w = World()
    _c_source(w, verified_by=["x-book"])
    assert w.parse()["x-1"].counted[0].evidence[-1] == "src:c-claim"


def test_a_seed_basis_ruling_stands_without_an_independent_signal():
    w = World()
    w.doc["rulings"][0].update(ruling_id="R-DEC-FAM-F15-SEED", seed_basis=True)
    w.family()["published_ruling_id"] = "R-DEC-FAM-F15-SEED"
    for row in w.members:
        row["ruling_id"] = "R-DEC-FAM-F15-SEED"
    w.member("XA0001").update(evidence=f"era:{ERA_XA}")
    w.member("XR0001").update(evidence="fact:0026c924483c6624")
    assert [m.code for m in w.parse()["x-1"].counted] == ["XA0001", "XR0001"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_loader.py -q`
Expected: collection error, `ImportError: cannot import name 'parse_ref' from 'govbudget.platform_families'`.

- [ ] **Step 3: Write `parse_ref` and extend `parse_registry` in `src/govbudget/platform_families.py`**

`parse_ref(ref: str) -> tuple[str, dict]`, `ValueError` on anything else. The grammar (spec §7.5; a `q=` may not contain `;`):

```python
_REF_RES = {
    "era": re.compile(r"^era:([^|;]+\|[^|;]+\|[^|;]*\|[0-9]{4}-[0-9]{4})$"),
    "fact": re.compile(r"^fact:([0-9a-f]{16})$"),
    "doc": re.compile(r"^doc:([0-9a-f]{64})#p([1-9][0-9]*)(?:;q=([^;]+))?$"),
    "src": re.compile(r"^src:([a-z0-9][a-z0-9-]*)(?:#p([1-9][0-9]*))?$"),
    "ev": re.compile(r"^ev:(\S+)$"),
}
```

Additions to `parse_registry` (all collected with Task 2a's, same line format):
- **Refs.** Every item of `evidence`, `link_evidence` and each family's `exclusions[].evidence` goes through `parse_ref`; every ref fault below (malformed, unresolved, wrong code, wrong decision, unknown source) quotes the ref with `repr` (rule 20). When the failing item directly follows a `doc:` item that carries `;q=`, the reason says the quote contains `';'` (Review Focus 2). A `split_refs` `ValueError` is reported the same way.
- **Rule 5 (link).** `published` needs `published_ruling_id`, naming a ruling whose `platform_family` is this family (reason names the other family); a `draft` must not carry the key. (`ratified` is not refused; the spec is silent.)
- **Rule 7 (citations).** A `src:` ref (row or exclusion) to a tier-`X` source fails (reason contains `tier X`) when cited by an `approved` row or by an exclusion; a tier-`C` source fails (`verified_by`) unless its `verified_by` names at least one source of tier `G` or `PG`. Exclusion faults go on the family's JSON row id, row faults on the member row.
- **Rule 13.** Two rows of one family with one `member_id` and intersecting [from, to]: reported on the later row by CSV order (`overlap`).
- **Rule 14.** One `member_id` in `approved` `counted` rows of two families with intersecting editions: reported on the later family's row, naming the earlier family.
- **Rule 15.** Two `approved` `counted` rows of one family with different `member_id`s and one `code`: reported on the later row by CSV order (reason names `code`).
- **Rule 16.** The `approved` `counted` rows' `member_order` values are exactly 1..n (n = their count): each such row whose value is outside 1..n or repeats an earlier row's fails; any other row with a `member_order` fails.
- **Rule 19.** `predecessor_member_id`/`successor_member_id`, when set, equal the `member_id` of some row of the same family; either set requires `link_basis`; `book_stated` requires a `doc:` item with a quote in `link_evidence`.
- **Rule 20 (refs).** `era:`: the decision exists in `era_decisions` (else `does not resolve`); its `line_item_code` and `account` equal the member's; its `organization` equals the member's when the code is in `era_map.ORG_SPLIT_CODES` and is blank otherwise; its `decision` is `same_program` or `history_only` (the reason quotes the decision). `src:`: the source exists. **The bar:** every `approved` `counted` row carries a `doc:` ref or a `src:` ref to a source in `INDEPENDENT_TIERS`, unless its ruling's `seed_basis` is true (reason contains `independent`). A `fact:` ref never satisfies the bar at stage 1: whether it is the member's own narrative is unknowable without the export (R1).
- **Rule 21.** Every `era_decision_ids` item exists in `era_decisions` and its `line_item_code` and `account` equal the member's.
- **Rule 22.** On `approved` rows: `decided_by == "owner"`; `ruling_id` exists; that ruling's `platform_family` is the row's (reason names the other family); `decided_on` equals the ruling's.
- **Rule 23.** A row whose `platform_family` is not in the JSON (reason quotes it); a `ratified` or `published` family with no rows (`no member rows`). A `draft` with zero rows passes.
- **Rule 24.** Each `program_notes` key is the `member_id` of an `approved` `counted` row of that family; `note` non-empty; `note_fact_id` `^[0-9a-f]{16}$`; `expected_receipt` keys exactly `RECEIPT_KEYS`.
- **Rule 25.** Each era row: its (`platform_family`, `member_id`) is an `approved` `counted` row whose [from, to] contains `edition` (else `approved counted` / `edition`); `era_key` matches `era_keys._ERA_KEY_RE`; the key's account and organization groups equal the member's `account` and `organization`; `decision_id` ∈ the member's `era_decision_ids`; (family, edition, era_key) unique (`duplicate`); one (edition, era_key) bound by counted members of two families is reported on the later family's row, naming the earlier.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_loader.py -q`
Expected: `172 passed` (108 from Task 2a; 8 single tests, 13 `test_parse_ref_refuses_malformed`, 43 `test_stage_one_cross_red_case`). Task 2a's tests stay green: the world satisfies every cross rule, and each red case asserts its own line is present, not that it is the only one.

- [ ] **Step 5: Lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uvx --offline ruff check --isolated --select F,E9 src/govbudget/platform_families.py tests/test_platform_families_loader.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_families.py GovBudget/tests/test_platform_families_loader.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): stage-1 cross-row rules and the typed-ref grammar (piece 2 task 2b)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2c: Lake stage 2 (read-only) and member measurement

**Spec:** §9.2 items 1–9 (a `draft` gets item 7 and its guard matches as undecided), §7.3 rows 13 and 21 (`titles_seen`, `drift_sha256`), §7.5 (`doc:` and `src:` resolution), §8.3 `check` (`undecided`, `stale`); D5; Review Focus 2 (quote matching) and 5 (a lock is an exception).

**Files:**
- Modify: `src/govbudget/platform_families.py` (append the stage-2 section)
- Modify: `tests/platform_family_fixtures.py` (append `make_lake`, `make_site`)
- Test: `tests/test_platform_families_loader.py` (append)

**Interfaces:**
- Consumes:
  - `govbudget.export_site._stage_parquet_path(duckdb_path, stage: str, filename: str) -> Path | None` (`export_site.py:2637` at `b6c9a8d9`, `:2574` at `b30134c4`), imported inside `open_lake`;
  - `govbudget.jbooks.era_map.keys_sha256(lines: Iterable[tuple[int, str, str | None, str | None]]) -> str` (`era_map.py:205`), `ERA_ORG_TO_MODERN`, `ORG_SPLIT_CODES`;
  - `govbudget.jbooks.collision_keys.classify_shared_keys(rows) -> dict[str, SplitAxis]`;
  - `govbudget.jbooks.era_keys.is_era_procurement_key(pe_bli) -> bool`;
  - `govbudget.jbooks.provenance_pages._page_texts(pdf_path) -> list[str]` (`provenance_pages.py:87`, pypdf; the extractor that places narrative citations);
  - Tasks 2a–2b: `Registry`, `Family`, `Member`, `EraLine`, `Headline`, `ReviewGuard`, `RegistryError`, `parse_ref`, `split_refs`, `INDEPENDENT_TIERS`.
- Produces (Tasks 3a, 5, 7a–7d):
  - `open_lake(duckdb_path: Path) -> LakeReader`;
  - `class LakeReader` (context manager): `code_rows(exhibit: str, account: str, organizations: set[str], code: str) -> list[dict]`, `era_map_rows(code: str, account: str, organization: str | None) -> list[dict]`, `guard_rows(guard: ReviewGuard) -> list[dict]`, `collision_codes() -> frozenset[str]`, `series_codes() -> frozenset[str]`, `actuals(keys: Iterable[tuple[str, int]]) -> dict[tuple[str, int], Decimal]`, `program_series(code: str) -> dict[tuple[int, str], Decimal]` (Task 7c's `compare_reference`, R2), `close() -> None`;
  - `@dataclass(frozen=True) MemberMeasure(titles_seen: tuple[tuple[int, str], ...], budget_activities: tuple[str, ...], editions: tuple[int, ...], drift_sha256: str, era_lines: tuple[EraLine, ...], headline_actuals_k: Decimal | None)`;
  - `measure_member(lake: LakeReader, member: Member, *, headline: Headline) -> MemberMeasure`;
  - `@dataclass LakeReport(failures: list[str], undecided: list[str], stale: list[str])` with `raise_if_failed() -> None` (raises `RegistryError(failures + stale)` when either is non-empty);
  - `check_lake(registry: Registry, *, lake: LakeReader, site_dir: Path, families: Sequence[str] | None = None) -> LakeReport`;
  - `corpus_gate(family: Family, series_codes: frozenset[str]) -> bool`;
  - `resolve_doc_ref(ref: str, *, site_dir: Path) -> str | None`;
  - `normalize_quote_text(text: str) -> str`;
  - in `tests/platform_family_fixtures.py`: `BL_COLS`, `LAKE_ROWS`, `MAP_ROWS`, `PROGRAM_ROWS`, `write_parquet`, `make_lake`, `make_site` (Task 3a reuses `BL_COLS` and `write_parquet`).

Measured for this task (live lake, read-only, 2026-10-21, outside :12–:22):
- `dim_programs` collision keys: 13, `0145, 1350, 20, 2101, 2210, 2292, 30, 3010, 3050, 3215, 3302, 4217, 500`; no F-15 or F-35 member code is one.
- No P-1/R-1 title contains `"; "` or `"|"`, so `titles_seen`'s format holds every title.
- The F-15 review guard matches 73 distinct lines (31 era-keyed, 42 code-keyed), all covered by the eight members. `F01500` also prints under exhibit `P-1R` (3010F, orgs `F` and `AF`); stage 2 reads only `P-1`/`R-1`, as the builder does.
- `actuals` summed over each F-35 member's bound lines (`fy = edition − 2`, FY2015–24, within its editions) reproduces every F35 Appendix B1 member figure and the 116,808.4 $M cumulative.
- A second writer's DuckDB connection makes `duckdb.connect(path, read_only=True)` raise `duckdb.IOException: IO Error: Could not set lock on file …` (probed on a scratch file).

- [ ] **Step 1: Append the lake and site to `tests/platform_family_fixtures.py`**

Layout as in `tests/jbooks/era_map_fixtures.py`: `{root}/duckdb/govbudget.duckdb`, `{root}/parquet/jbooks/{budget_lines,documents}.parquet` (all-varchar, its `BL_COLS` plus `line_item_code`), `{root}/site/`.

Add `from collections.abc import Mapping, Sequence`, `import duckdb` and `from pdf_factory import make_pdf` to the module's imports, then append:

```python
BL_COLS = ("exhibit", "fiscal_year", "account", "account_title", "organization", "budget_activity",
           "budget_activity_title", "pe_bli", "title", "amount_type", "amount_thousands",
           "source_document_id", "source_sheet", "source_cells", "line_item_code")
# (exhibit, edition, account, organization, ba, pe_bli, title, line_item_code, actuals_k)
LAKE_ROWS = [
    ("P-1", 2023, "3010F", "AF", "05", "3010F-AF-L7", "X-1", "XA0001", "100"),
    ("P-1", 2024, "3010F", "F", "05", "XA0001", "X-1", "XA0001", "200"),
    ("P-1", 2025, "3010F", "F", "05", "XA0001", "X-1", "XA0001", "210"),
    ("P-1", 2026, "3010F", "F", "05", "XA0001", "X-1", "XA0001", "220"),
    ("R-1", 2025, "3600F", "F", "07", "XR0001", "X-1 Dev", "", "50"),
    ("R-1", 2026, "3600F", "F", "07", "XR0001", "X-1 Dev", "", "60"),
    ("P-1", 2024, "3010F", "F", "06", "XC0001", "X-1 Spares", "XC0001", "10"),
    ("P-1", 2025, "3010F", "F", "06", "XC0001", "X-1 Spares", "XC0001", "11"),
    ("P-1", 2026, "3010F", "F", "06", "XC0001", "X-1 Spares", "XC0001", "12"),
    ("P-1", 2026, "3010F", "F", "07", "ZZ0001", "Unrelated Line", "ZZ0001", "5"),
]
# (edition, account, organization, ba, era_key, line_item_code, filed_title, program_key, decision, decision_id)
MAP_ROWS = [(2023, "3010F", "AF", "05", "3010F-AF-L7", "XA0001", "X-1", "XA0001", "same_program", ERA_XA)]
PROGRAM_ROWS = [("XA0001", "3010F", "F"), ("XR0001", "3600F", "F"), ("XC0001", "3010F", "F"),
                ("0145", "1506N", "N"), ("0145", "1810N", "N")]      # one collision key, no member's
```

Three functions (every one creates its parent directories):
- `write_parquet(path: Path, cols: Sequence[str], rows: Sequence[Sequence[str]]) -> None`: an all-varchar parquet through an in-memory DuckDB, as `era_map_fixtures._write_parquet` does (Task 3a reuses it).
- `make_lake(root: Path, *, add: Sequence[tuple] = (), drop: set[tuple[int, str]] = frozenset(), retitle: Mapping[tuple[int, str], str] = {}, map_rows: Sequence[tuple] = MAP_ROWS, programs: Sequence[tuple] = PROGRAM_ROWS, series_skip: frozenset[str] = frozenset()) -> Path` writes `LAKE_ROWS + add` minus the `(edition, pe_bli)` pairs in `drop`, with `retitle` replacing a pair's title. Each entry becomes two `budget_lines` rows (amount types `fy_{e-2}_actuals` with its `actuals_k` and `fy_{e-1}_total` with `"0"`; `account_title` `Acct`, `budget_activity_title` `BA`, `source_document_id` `str(e - 2000)`, `source_sheet` `Exhibit P-1`, `source_cells` `O9`), so one line spans two amount columns. It writes `documents.parquet` like `era_map_fixtures.make_lake` (ids `"23"`–`"26"`), and DuckDB tables `fct_decade_series (pe_bli varchar, fy integer, edition_year integer, amount_type_kind varchar, amount double, account varchar, organization varchar)` with one `actuals` row per entry (`fy = e - 2`, null axes) unless its `pe_bli` is in `series_skip`, `fct_program_decade_series (program_key varchar, fy integer, edition_year integer, amount_type_kind varchar, amount_thousands double)` with, per entry, `program_key = line_item_code or pe_bli` and two rows (`actuals`, `fy = e - 2`, its `actuals_k`; `enacted`, `fy = e - 1`, `0`), both at `edition_year = e`, `p1_era_line_map` with the ten `MAP_ROWS` columns (`edition integer`, the rest varchar) and `dim_programs (pe_bli, account, org)` (varchar). Returns the DuckDB path.
- `make_site(root: Path) -> Path` writes `{root}/site/pdfs/{DOC_SHA}.pdf` with `make_pdf(path, [["X-1 development", "continues in FY2026"]])` and `{root}/site/sources/x-book.txt` with `SRC_BYTES`; returns `{root}/site`.

- [ ] **Step 2: Write the failing tests (append to `tests/test_platform_families_loader.py`)**

Merge into the file's import block: `subprocess`, `sys`, `from decimal import Decimal`, `duckdb`, `from openpyxl import Workbook`, `from pdf_factory import make_pdf`; from `govbudget.platform_families` the names `LakeReport, MemberMeasure, check_lake, corpus_gate, measure_member, normalize_quote_text, open_lake, resolve_doc_ref`; from `platform_family_fixtures` the names `DRIFT, MAP_ROWS, PROGRAM_ROWS, SRC_SHA, make_lake, make_site`. Then append:

```python
HEAD = Headline("cumulative_actuals", 2015, 2024)


def _check(tmp_path, w=None, **lake_kw):
    w = w or World()
    db, site = make_lake(tmp_path, **lake_kw), make_site(tmp_path)
    with open_lake(db) as lake:
        return check_lake(w.parse(), lake=lake, site_dir=site)


def test_lake_reader_reads_the_world(tmp_path):
    with open_lake(make_lake(tmp_path)) as lake:
        assert lake.code_rows("P-1", "3010F", {"AF", "F"}, "XA0001") == [
            {"edition": e, "organization": "F", "budget_activity": "05", "title": "X-1"} for e in (2024, 2025, 2026)]
        assert [(r["edition"], r["era_key"], r["decision_id"]) for r in lake.era_map_rows("XA0001", "3010F", None)] == [
            (2023, "3010F-AF-L7", ERA_XA)]
        assert len(lake.guard_rows(ReviewGuard(("P-1", "R-1"), ("X-1",)))) == 9
        assert lake.collision_codes() == frozenset({"0145"})
        assert lake.series_codes() == frozenset({"3010F-AF-L7", "XA0001", "XR0001", "XC0001", "ZZ0001"})
        assert lake.actuals([("XA0001", 2024), ("XA0001", 2017)]) == {("XA0001", 2024): Decimal("200")}


def test_lake_reader_program_series_uses_the_edition_rule(tmp_path):
    with open_lake(make_lake(tmp_path)) as lake:
        series = lake.program_series("XA0001")
        assert (series[(2021, "actuals")], series[(2024, "actuals")]) == (Decimal("100"), Decimal("220"))
        assert series[(2025, "enacted")] == Decimal("0") and (2024, "request") not in series
        assert lake.program_series("QQ0001") == {}


def test_open_lake_opens_duckdb_read_only(tmp_path, monkeypatch):
    db, real, calls = make_lake(tmp_path), duckdb.connect, []
    monkeypatch.setattr(duckdb, "connect", lambda *a, **k: calls.append((a, k)) or real(*a, **k))
    open_lake(db).close()
    assert [k for a, k in calls if a and a[0] == str(db)] == [{"read_only": True}]


def test_open_lake_surfaces_a_duckdb_lock_as_an_exception(tmp_path):
    db = make_lake(tmp_path)
    holder = subprocess.Popen([sys.executable, "-c", "import duckdb, sys, time; c = duckdb.connect(sys.argv[1]);"
                               " print('ready', flush=True); time.sleep(30)", str(db)],
                              stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "ready"
        with pytest.raises(duckdb.IOException, match="Could not set lock"):
            open_lake(db)
    finally:
        holder.kill()


def test_measure_member_measures_each_row(tmp_path):
    x = World().parse()["x-1"]
    with open_lake(make_lake(tmp_path)) as lake:
        xa, xr = (measure_member(lake, m, headline=HEAD) for m in x.counted)
        xc = measure_member(lake, x.context[0], headline=HEAD)
    assert xa == MemberMeasure(((2024, "X-1"), (2025, "X-1"), (2026, "X-1")), ("05",), (2023, 2024, 2025, 2026),
                               DRIFT["XA0001"], x.era_lines, Decimal("730"))
    assert xr == MemberMeasure(((2025, "X-1 Dev"), (2026, "X-1 Dev")), ("07",), (2025, 2026), DRIFT["XR0001"],
                               (), Decimal("110"))
    assert (xc.drift_sha256, xc.headline_actuals_k) == (DRIFT["XC0001"], Decimal("33"))


def test_measure_member_keeps_each_editions_titles(tmp_path):
    xa = World().parse()["x-1"].counted[0]
    with open_lake(make_lake(tmp_path, add=[("P-1", 2025, "3010F", "F", "05", "XA0001", "X-1 Lot 2", "XA0001", "0")],
                             drop={(2026, "XA0001")})) as lake:
        got = measure_member(lake, xa, headline=HEAD)
    assert got.titles_seen == ((2024, "X-1"), (2025, "X-1"), (2025, "X-1 Lot 2"))
    assert got.editions == (2023, 2024, 2025)


def test_check_lake_passes_the_minimal_world(tmp_path):
    assert _check(tmp_path) == LakeReport([], [], [])


def _failures(report, file, row, fragment):
    assert refused(report.failures, file, row, fragment), "\n".join(report.failures)


def test_code_keyed_title_drift_fails(tmp_path):
    _failures(_check(tmp_path, retitle={(2025, "XA0001"): "X-1 Lot"}), M, XA_ID, "'X-1 Lot'")


def test_code_keyed_row_in_an_edition_titles_seen_omits_fails(tmp_path):
    report = _check(tmp_path, add=[("P-1", 2023, "3010F", "F", "05", "XA0001", "X-1", "XA0001", "90")])
    _failures(report, M, XA_ID, "PB2023")


def test_code_keyed_row_outside_the_range_fails(tmp_path):
    report = _check(tmp_path, add=[("P-1", 2022, "3010F", "F", "05", "XA0001", "X-1", "XA0001", "90")])
    _failures(report, M, XA_ID, "PB2022")


def test_a_pb2027_code_keyed_row_fails_loudly(tmp_path):      # no reader filters editions (R2; §17 risk 7)
    report = _check(tmp_path, add=[("P-1", 2027, "3010F", "F", "05", "XA0001", "X-1", "XA0001", "230")])
    _failures(report, M, XA_ID, "PB2027")


def test_drift_sha_mismatch_is_stale_and_blocks(tmp_path):
    w = World()
    w.member("XA0001").update(drift_sha256="0" * 64)
    report = _check(tmp_path, w)
    assert report.failures == [] and refused(report.stale, M, XA_ID, "drift_sha256")
    with pytest.raises(RegistryError):
        report.raise_if_failed()


def test_roster_unlike_the_map_fails(tmp_path):
    w = World()
    w.era_rows.clear()
    _failures(_check(tmp_path, w), E, ERA_ID, "roster")


def test_unmapped_era_line_fails_unless_excluded(tmp_path):
    extra = (2022, "3010F", "AF", "05", "3010F-AF-L9", "XA0001", "X-1", "XA0001", "same_program",
             "XA0001|3010F||2022-2022")
    _failures(_check(tmp_path / "a", map_rows=MAP_ROWS + [extra]), M, XA_ID, "3010F-AF-L9")
    excluded = extra[:8] + ("exclude_placeholder", "XA0001|3010F||2017-2022")
    assert _check(tmp_path / "b", map_rows=MAP_ROWS + [excluded]) == LakeReport([], [], [])


def test_unreviewed_guard_match_fails_with_the_f15_wording(tmp_path):
    report = _check(tmp_path, add=[("P-1", 2026, "3010F", "F", "07", "XD0001", "X-1 Trainer", "XD0001", "1")])
    _failures(report, J, "x-1", "Unreviewed X-1 workbook identity: 2026/XD0001")


def test_guard_match_covered_only_by_a_deferred_row_is_undecided(tmp_path):
    w = World()
    w.add_member("x-1", "P-1:3010F:AF:XD0001", 2026, 2026, role="counted", verdict="deferred",
                 display_title="X-1 Trainer")   # rule 11 requires it
    report = _check(tmp_path, w, add=[("P-1", 2026, "3010F", "F", "07", "XD0001", "X-1 Trainer", "XD0001", "1")])
    assert report.failures == [] and any("XD0001" in line for line in report.undecided)


def test_a_recorded_deferred_row_is_undecided_never_a_failure(tmp_path):      # §8.3, R4
    w = World()
    w.add_member("x-1", "R-1:3600F:AF:XS0001", 2026, 2026, role="project_slice", verdict="deferred",
                 project_number="675365", display_title="X-1 slice")
    report = _check(tmp_path, w)
    assert report.failures == [] and report.stale == []
    assert refused(report.undecided, M, "x-1|R-1:3600F:AF:XS0001|2026-2026", "deferred")


def test_collision_code_fails(tmp_path):
    _failures(_check(tmp_path, programs=PROGRAM_ROWS + [("XA0001", "3011F", "F")]), M, XA_ID, "collision")


def test_doc_ref_missing_file_and_page_out_of_range_fail(tmp_path):
    for i, ref, fragment in [(0, f"doc:{'e' * 64}#p1", "pdfs/"), (1, f"doc:{DOC_SHA}#p2", "out of range")]:
        w = World()
        w.member("XR0001").update(evidence=ref)
        _failures(_check(tmp_path / str(i), w), M, XR_ID, fragment)


def test_doc_ref_miss_names_sha_page_and_quote(tmp_path):
    site = make_site(tmp_path)
    reason = resolve_doc_ref(f"doc:{DOC_SHA}#p1;q=X-2 development", site_dir=site)
    assert DOC_SHA in reason and "p1" in reason and "'X-2 development'" in reason
    assert resolve_doc_ref(f"doc:{DOC_SHA}#p1;q=X-1 development continues", site_dir=site) is None


def test_doc_ref_quote_matches_across_breaks_nbsp_dashes_and_curly_quotes(tmp_path):
    site = make_site(tmp_path)
    make_pdf(site / "pdfs" / f"{'e' * 64}.pdf", [['F-35 "Lightning" II - Block 4', "modernization continues"]])
    quote = "F\u201135 \u201cLightning\u201d II \u2013 Block\u00a04 modernization"   # NB hyphen, curly quotes, en dash, NBSP; the page breaks after "Block 4"
    assert resolve_doc_ref(f"doc:{'e' * 64}#p1;q={quote}", site_dir=site) is None
    assert resolve_doc_ref(f"doc:{'e' * 64}#p1;q=f-35", site_dir=site) is not None    # case-sensitive


def test_normalize_quote_text_folds_and_keeps_case():
    assert normalize_quote_text(" a\u00a0 b\n–− “q” ‘s’ ") == "a b -- \"q\" 's'"
    assert normalize_quote_text("Block") != normalize_quote_text("block")


def test_doc_ref_on_a_workbook_reads_the_sheet(tmp_path):
    site = make_site(tmp_path)
    wb = Workbook()
    wb.active["A1"], wb.active["B2"] = "X-1 line", "Lot 2"
    (site / "workbooks").mkdir()
    wb.save(site / "workbooks" / f"{'b' * 64}.xlsx")
    assert resolve_doc_ref(f"doc:{'b' * 64}#p1;q=X-1 line Lot 2", site_dir=site) is None
    assert "out of range" in resolve_doc_ref(f"doc:{'b' * 64}#p2", site_dir=site)


def test_unarchived_or_changed_source_fails_only_for_a_published_family(tmp_path):
    w = World()
    w.doc["sources"][0].update(archived=False)
    w.doc["sources"][0].pop("archive_path")
    _failures(_check(tmp_path / "a", w), J, "x-book", "not archived")
    w.family().update(status="ratified")
    w.family().pop("published_ruling_id")
    assert _check(tmp_path / "b", w).failures == []
    db, site = make_lake(tmp_path / "c"), make_site(tmp_path / "c")
    (site / "sources" / "x-book.txt").write_bytes(b"another copy\n")
    with open_lake(db) as lake:
        _failures(check_lake(World().parse(), lake=lake, site_dir=site), J, "x-book", SRC_SHA)


def test_partial_corpus_raises_for_raise_and_skips_for_skip(tmp_path):
    message = "X-1 family history requires every counted workbook member: missing XR0001"
    _failures(_check(tmp_path / "a", series_skip=frozenset({"XR0001"})), J, "x-1", message)
    x = World().parse()["x-1"]
    with open_lake(make_lake(tmp_path / "b", series_skip=frozenset({"XR0001"}))) as lake:
        series = lake.series_codes()
    with pytest.raises(RegistryError, match=message):
        corpus_gate(x, series)
    w = World()
    w.family().update(on_partial_corpus="skip")
    assert corpus_gate(w.parse()["x-1"], series) is False
    assert corpus_gate(x, series | {"XR0001"}) is True
    assert _check(tmp_path / "c", w, series_skip=frozenset({"XR0001"})).failures == []


def test_draft_family_gets_only_doc_refs_and_undecided_guard_matches(tmp_path):
    w = World()
    w.family("y-1")["exclusions"] = [{"exclusion_id": "classified", "kind": "outside_scope", "label": "Classified",
                                      "size_text": "Classified funding: unknown", "evidence": [f"doc:{'f' * 64}#p1"]}]
    report = _check(tmp_path, w, add=[("P-1", 2026, "3010F", "F", "01", "YA0001", "Y-1 Aircraft", "YA0001", "1")])
    assert [line for line in report.failures if ":y-1: " in line and "doc:" + "f" * 64 not in line] == []
    _failures(report, J, "y-1", "f" * 64)
    assert refused(report.undecided, J, "y-1", "YA0001")


def test_check_lake_families_argument_limits_the_families(tmp_path):
    db, site = make_lake(tmp_path, add=[("P-1", 2026, "3010F", "F", "01", "YA0001", "Y-1 Aircraft", "YA0001", "1")]), make_site(tmp_path)
    with open_lake(db) as lake:
        assert check_lake(World().parse(), lake=lake, site_dir=site, families=["x-1"]) == LakeReport([], [], [])
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_loader.py -q`
Expected: collection error, `ImportError: cannot import name 'LakeReport' from 'govbudget.platform_families'`.

- [ ] **Step 4: Write the lake reader and `measure_member`**

`open_lake(duckdb_path: Path) -> LakeReader`: one `duckdb.connect(str(duckdb_path), read_only=True)` (it reads the parquet files too); `budget_lines.parquet` and `documents.parquet` resolved with `export_site._stage_parquet_path(duckdb_path, "jbooks", …)`, `FileNotFoundError` naming both probe roots when either is `None`. A `duckdb.IOException` (the lock) propagates untouched: no stage-2 function catches it.

`LakeReader` queries (every `budget_lines` query casts `cast(fiscal_year as integer)` and filters no edition, so a PB2027 row is seen and fails item 1 (R2); the live P-1/R-1 rows are all PB2017–PB2026, re-measured 2026-10-21; results are distinct and sorted):
- `code_rows`: rows with `exhibit`, `account`, `organization in organizations`, `pe_bli = code` → `{edition, organization, budget_activity, title}`, sorted by (edition, budget_activity, title, organization).
- `era_map_rows`: `p1_era_line_map` rows with `line_item_code = code`, `account = account` and, when `organization` is not `None`, `organization = organization` → `{edition, account, organization, budget_activity, era_key, line_item_code, filed_title, program_key, decision, decision_id}`, sorted by (edition, era_key).
- `guard_rows`: rows with `exhibit in guard.exhibits` and `upper(title)` containing any substring → `{edition, exhibit, account, organization, budget_activity, pe_bli, title, line_item_code}`, sorted by (edition, exhibit, pe_bli, account, organization).
- `collision_codes`: `frozenset(classify_shared_keys(select pe_bli, account, org from dim_programs))`.
- `series_codes`: `select distinct pe_bli from fct_decade_series`; `frozenset()` when the table is absent (`duckdb.CatalogException`, today's small-export case).
- `actuals`: for each requested (pe_bli, edition), the sum of `fct_decade_series.amount` where `amount_type_kind = 'actuals'`, `edition_year = edition`, `fy = edition - 2`, as `Decimal(str(v))`; keys with no row are absent.
- `program_series`: `fct_program_decade_series` rows with `program_key = code`, kept only under the edition rule (`actuals` at `edition_year = fy + 2`, `enacted` at `fy + 1`, `request` at `fy`), summed per `(fy, amount_type_kind)` as `Decimal(str(v))` of `amount_thousands`; `{}` when no row matches or the table is absent (`duckdb.CatalogException`). Re-measured 2026-10-21: summed over the 15 F-35 codes it reproduces every Appendix B1 total; `account`/`organization` are NULL for all 15.

`measure_member(lake: LakeReader, member: Member, *, headline: Headline) -> MemberMeasure`:
- code-keyed lines: `lake.code_rows(member.exhibit, member.account, {member.organization, ERA_ORG_TO_MODERN.get(member.organization, member.organization)}, member.code)`;
- era lines: `lake.era_map_rows(member.code, member.account, member.organization if member.code in ORG_SPLIT_CODES else None)` whose `decision_id` ∈ `member.era_decision_ids`, as `EraLine(member.platform_family, member.member_id, …)`, unrestricted by edition;
- `titles_seen`: every distinct (edition, title) of the code-keyed lines inside [from, to], sorted (two titles in one edition stay two entries; stage 1 then refuses them);
- `budget_activities`: sorted distinct BAs of both kinds of line inside [from, to];
- `editions`: sorted editions of both kinds, unrestricted (so a caller sees an out-of-range edition);
- `drift_sha256`: `keys_sha256` over the distinct `(edition, code, ba, title)` code-keyed and `(edition, era_key, ba, title)` era lines inside [from, to];
- `headline_actuals_k`: `sum(lake.actuals(...).values())` over those lines' (pe_bli or era_key, edition) with `headline.first_fy <= edition - 2 <= headline.last_fy`; `None` when no amount is found.

- [ ] **Step 5: Write `resolve_doc_ref`, `normalize_quote_text`, `corpus_gate`, `LakeReport` and `check_lake`**

`normalize_quote_text(text: str) -> str`: `unicodedata.normalize("NFKC", text)`; U+2010–U+2015 and U+2212 → `-`; U+2018, U+2019, U+201A, U+201B → `'`; U+201C, U+201D, U+201E, U+201F → `"`; every whitespace run → one space; strip. Case is kept.

`resolve_doc_ref(ref: str, *, site_dir: Path) -> str | None` (`None` = resolves): `parse_ref`; the file is `site_dir/pdfs/<sha>.pdf`, else `site_dir/workbooks/<sha>.xlsx`, else the reason names both paths; a PDF's pages are `provenance_pages._page_texts`; a workbook's page n is its n-th worksheet (openpyxl `read_only=True, data_only=True`), whose text is every non-empty cell's `str` value in row-major order joined by `" "`; page outside 1..count → reason `doc:<sha>#p<n>: page out of range (1–<count>)`; a quote not in the page's normalized text → reason `doc:<sha>#p<n>: quote not found: <repr(quote)>`. Cache page texts per file path for the life of the process.

`corpus_gate(family: Family, series_codes: frozenset[str]) -> bool` (D5): `missing = sorted({m.code for m in family.code_keyed} - series_codes)`; none → `True`; `on_partial_corpus == "skip"` → `False`; `"raise"` → `RegistryError([f"platform-families: {REGISTRY_JSON.name}:{family.platform_family}: {family.short_name} family history requires every counted workbook member: missing {', '.join(missing)}"])`.

`check_lake(registry, *, lake, site_dir, families=None) -> LakeReport`: families in JSON order (only those named in `families`, via `registry[pf]`); within a family, rows by `member_row_id`, guard lines in `guard_rows` order. Lines use Task 2a's format (file = `REGISTRY_JSON.name`/`MEMBERS_CSV.name`/`ERA_LINES_CSV.name`, since a `Registry` does not carry its paths). Per family:
- **`draft`:** item 7 on its `exclusions[].evidence` `doc:` refs (failures); every guard row → `undecided` on the family's JSON row (`undecided guard match PB<e> <exhibit> <account>/<org> <pe_bli> <title!r>`). Nothing else.
- **`ratified` and `published`:**
  1. Each `approved` `counted` row: a `titles_seen` edition with no code-keyed line (`missing`); a line whose title differs from its edition's entry (reason quotes both titles and `PB<e>`); a line in an edition inside [from, to] that `titles_seen` lacks (`PB<e>`); a line outside [from, to] (`PB<e>`, `outside`).
  2. Every row with a non-blank `drift_sha256` that differs from `measure_member(...).drift_sha256` → `stale` (reason names both hashes and the line count).
  3. Each `approved` `counted` row: its era lines in the registry vs the measured ones, compared as (edition, era_key, budget_activity, filed_title, decision_id); each difference on the era-lines file, row id `{pf}|{edition}|{era_key}`, reason containing `roster`; a measured line whose `program_key` or `line_item_code` differs from the code fails the same way.
  4. Each `approved` `counted` row: every `era_map_rows` line (organization filter as in `measure_member`) that is not one of the family's era lines and whose `decision` does not start with `exclude_` → failure on the member row naming the era key (`unmapped`).
  5. Every guard row must be covered by a row of this family whose `verdict` is `approved` or `rejected`, any role: a code-keyed row (not `is_era_procurement_key`) is covered by a row with equal exhibit and account, organization ∈ {its spelling, its modern spelling}, `code == pe_bli` and the edition in [from, to]; an era-keyed row likewise but with `code == line_item_code`. Covered only by a `deferred` row → `undecided`. Uncovered → failure `Unreviewed {short_name} workbook identity: {edition}/{pe_bli}` on the family's JSON row.
  6. Each `approved` `counted` row's code ∈ `lake.collision_codes()` → failure (`collision`).
  7. Every `doc:` ref in any row's `evidence`, `link_evidence`, `allocation_source` and in `exclusions[].evidence` → `resolve_doc_ref`; a reason becomes a failure on that row (exclusions: the JSON family row).
  8. `published` only: every source named by a `src:` ref of the family (rows or exclusions) must be `archived` (else `not archived`, on the source's JSON row) and `site_dir / archive_path` must exist with sha256 equal to `sha256` (else the reason names the expected `sha256`; an absent `sha256` fails as unverifiable).
  9. `on_partial_corpus == "raise"`: `corpus_gate`'s message as a failure when it would raise.
  10. Every `deferred` row → `undecided` on its members row (`deferred row, recorded and never exported`), never a failure (§8.3; a recorded deferral is undecided, R4).

`LakeReport.raise_if_failed()` raises `RegistryError(self.failures + self.stale)` when either is non-empty; `undecided` never raises (spec §8.2: a deferred B1 never blocks).

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_loader.py -q`
Expected: `199 passed` (172 from Tasks 2a–2b plus 27).

- [ ] **Step 7: Lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uvx --offline ruff check --isolated --select F,E9 src/govbudget/platform_families.py tests/platform_family_fixtures.py tests/test_platform_families_loader.py`
Expected: `All checks passed!`

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_families.py GovBudget/tests/platform_family_fixtures.py GovBudget/tests/test_platform_families_loader.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): read-only lake stage 2 and member measurement (piece 2 task 2c)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3a: The one-off F-15 seed and the F-15 entry

**Spec:** §7.6 (the eight rows, their sourcing, the seed's refusals), §8.1 (the ruling's text and fields), §7.2 F-15 column, §7.4 (31 era rows), §13 (`tests/test_f15_registry_parity.py` holds the only literal `88538c6a` copies), §19 row 27; D13 (the reply file).

**Files:**
- Modify: `src/govbudget/platform_families.py` (append the seed section)
- Create: `tests/test_f15_registry_parity.py`
- Create: `data/research/platform_families/f-15/owner-reply-R-DEC-FAM-F15-SEED.txt`
- Create (written by the seed in Step 7): `data-seeds/platform_families.json`, `data-seeds/platform_family_members.csv`, `data-seeds/platform_family_era_lines.csv`

**Interfaces:**
- Consumes: Tasks 2a–2c (`parse_registry`, `write_registry`, `load_registry`, `Member.from_row`, `open_lake`, `measure_member`, `check_lake`, `RegistryPaths`, `RegistryError`); `govbudget.verify_era_map.F15_HISTORY_PIN` (`verify_era_map.py:390`, the pin file, first token = sha256); `era_map.read_seed`, `era_map.default_seed_path()`; Task 1's fam2 snapshot (`$GOVBUDGET_PROOFS/fam2/duckdb/govbudget.duckdb`, `$GOVBUDGET_PROOFS/fam2/site`).
- Produces:
  - `@dataclass(frozen=True) F15Constants(programs: Sequence[Mapping], modern_members: Mapping[str, tuple[str, str, str]], era_members: Mapping[int, Sequence[tuple[int, str, str]]], era_program_codes: Mapping[int, Mapping[int, str]], program_notes: Mapping[str, Mapping[str, str]], note_receipts: Mapping[str, Mapping[str, object]], scope_note: str, coverage_notes: Sequence[str], expected_from: Mapping[str, int | None])`;
  - `seed_shipped_f15(*, constants: F15Constants, duckdb_path: Path, site_dir: Path, decided_on: str, owner_reply: str, paths: RegistryPaths = DEFAULT_PATHS) -> dict` → `{"members": 8, "era_lines": 31, "rulings": 1}`; it strips exactly one trailing `\n` from `owner_reply` (D13);
  - `F15_SEED_ROWS`, `F15_SEED_RULING_TEXT`, `F15_SEED_SPEC` (module constants, used only by the seed);
  - the committed registry (Tasks 3b, 4, 5, 6, 7e read it);
  - in `tests/test_f15_registry_parity.py` (Tasks 3b and 6 extend it): module-level literal copies `MODERN_MEMBERS`, `ERA_MEMBERS`, `ERA_PROGRAM_CODES`, `PROGRAM_NOTES`, `NOTE_RECEIPTS`, `PROGRAMS`, `SCOPE_NOTE`, `COVERAGE_NOTES` (verbatim `88538c6a:GovBudget/src/govbudget/f15_funding_history.py:19-108`), `EXPECTED_FROM = {"0207134F": 2017, "0207171F": 2017, "0207146F": 2021, "F01500": 2024, "F015EX": 2024, "F15EWS": 2024, "F0150P": None, "F015E0": None}` (`f15_funding_history.py:218-224`), `literal_constants() -> F15Constants`, `SHIPPED = literal_constants()` (the instance Task 3b's parity tests read, R11), `make_f15_world(root, *, drop_map=(), extra_programs=()) -> tuple[Path, Path]`.

Measured for this task (live lake, read-only, 2026-10-21; `tests/fixtures/f15/builder_inputs.json.gz`'s 467 source rows give the same lines, so the hermetic world below measures identically):

| member | titles_seen | budget_activities | lines | drift_sha256 |
|---|---|---|---|---|
| R-1:3600F:AF:0207134F | 2017–2026: `F-15E Squadrons` | `07` | 10 | `3e712698ea139bb2e5353b817fad2dc8d7a6c557fdbc75d147ab515529cbbe9d` |
| R-1:3600F:AF:0207146F | 2021–2026: `F-15EX` | `07` | 6 | `ba44e832838c6dea94864a2b7ba01fb4509cd4b83a16b1b3e394587f2bf4a53c` |
| R-1:3600F:AF:0207171F | 2017–2026: `F-15 EPAWSS` | `05;07` | 11 | `0ac8af1ee02fdc821e1b06fa2553f70b215bcf0b3fc3fd7b115b3750b25b3b68` |
| P-1:3010F:AF:F01500 | 2024–2026: `F-15` | `05;07` | 19 (13 era) | `01771b3d6a955ca8757b53d3648e9e2afd8cff3cade49a7befd6f999f932fdfd` |
| P-1:3010F:AF:F015EX | 2024–2026: `F-15EX` | `01;05;07` | 12 (6 era) | `c9f52488401161fe17ff6751f197c1230c667ff157075d69abd0dee9adb823dc` |
| P-1:3010F:AF:F15EWS | 2024–2026: `F-15 EPAW` | `05` | 8 (5 era) | `a5fc0cd2f4f7e419b7a36a639f32860bfa1862bbb4a84483c87d5a1991684691` |
| P-1:3010F:AF:F0150P | — | `07` | 4 (era) | `a3973b968d31541ba0f3b4048ac1a20c2facc9eda28208be641ae27ea463302a` |
| P-1:3010F:AF:F015E0 | — | `01` | 3 (era) | `3534b19978134f6408e33d2a1865bc3ae60662a1ca49f176fd3232b621ffa946` |

`p1_era_line_map` holds exactly 31 rows for these codes in 3010F, all with `program_key = line_item_code`; `tests/fixtures/f15/history.json` hashes to the pin `d0de9e8b…8d8f` and its `programs[]` equal `PROGRAMS`.

- [ ] **Step 1: Write the owner's reply file (D13)**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && mkdir -p data/research/platform_families/f-15 && printf '%s\n' 'approved, would process with recommendation to approve all' > data/research/platform_families/f-15/owner-reply-R-DEC-FAM-F15-SEED.txt && wc -c < data/research/platform_families/f-15/owner-reply-R-DEC-FAM-F15-SEED.txt`
Expected: `59` (58 characters and one `\n`).

- [ ] **Step 2: Write `tests/test_f15_registry_parity.py`**

The file opens with the literal block, copied byte for byte from `88538c6a`, between two marker comments; then `EXPECTED_FROM`; then the world and the tests.

```python
"""F-15 registry parity and the one-off seed (families piece 2; spec §7.6, §8.1, §13).

The only literal copies of the 88538c6a F-15 constants live here."""
from __future__ import annotations

import csv
import gzip
import json
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import duckdb
import pytest

from govbudget import config
from govbudget.jbooks import era_map
from govbudget.platform_families import (DEFAULT_PATHS, F15_SEED_RULING_TEXT, F15_SEED_SPEC,
                                         F15Constants, RegistryError, load_registry, registry_texts,
                                         seed_shipped_f15)
from platform_family_fixtures import BL_COLS, World, tmp_paths, write_parquet, write_world

# --- literal copies (88538c6a f15_funding_history.py:19-108) ---
# <lines 19–108 of `git show 88538c6a:GovBudget/src/govbudget/f15_funding_history.py`, unchanged>
# --- end literal copies ---
EXPECTED_FROM = {"0207134F": 2017, "0207171F": 2017, "0207146F": 2021, "F01500": 2024,
                 "F015EX": 2024, "F15EWS": 2024, "F0150P": None, "F015E0": None}
REPLY_FILE = config.ROOT / "data/research/platform_families/f-15/owner-reply-R-DEC-FAM-F15-SEED.txt"
REPLY = "approved, would process with recommendation to approve all"
FIXTURES = config.ROOT / "tests" / "fixtures" / "f15"
DECISION_IDS = {"F01500": "F01500|3010F||2017-2023", "F015EX": "F015EX|3010F||2021-2023",
                "F15EWS": "F15EWS|3010F||2019-2023", "F0150P": "F0150P|3010F||2017-2020",
                "F015E0": "F015E0|3010F||2020-2022"}
DRIFT = {   # re-measured 2026-10-21 on the live lake; the hermetic world gives the same
    "0207134F": "3e712698ea139bb2e5353b817fad2dc8d7a6c557fdbc75d147ab515529cbbe9d",
    "0207146F": "ba44e832838c6dea94864a2b7ba01fb4509cd4b83a16b1b3e394587f2bf4a53c",
    "0207171F": "0ac8af1ee02fdc821e1b06fa2553f70b215bcf0b3fc3fd7b115b3750b25b3b68",
    "F01500": "01771b3d6a955ca8757b53d3648e9e2afd8cff3cade49a7befd6f999f932fdfd",
    "F015EX": "c9f52488401161fe17ff6751f197c1230c667ff157075d69abd0dee9adb823dc",
    "F15EWS": "a5fc0cd2f4f7e419b7a36a639f32860bfa1862bbb4a84483c87d5a1991684691",
    "F0150P": "a3973b968d31541ba0f3b4048ac1a20c2facc9eda28208be641ae27ea463302a",
    "F015E0": "3534b19978134f6408e33d2a1865bc3ae60662a1ca49f176fd3232b621ffa946",
}


def literal_constants() -> F15Constants:
    return F15Constants(programs=PROGRAMS, modern_members=MODERN_MEMBERS, era_members=ERA_MEMBERS,
                        era_program_codes=ERA_PROGRAM_CODES, program_notes=PROGRAM_NOTES,
                        note_receipts=NOTE_RECEIPTS, scope_note=SCOPE_NOTE,
                        coverage_notes=COVERAGE_NOTES, expected_from=EXPECTED_FROM)


SHIPPED = literal_constants()
```

`make_f15_world(root: Path, *, drop_map: Sequence[tuple[int, int]] = (), extra_programs: Sequence[tuple[str, str, str]] = ()) -> tuple[Path, Path]` builds a fam2-shaped snapshot from the committed fixtures, with the Task 2c layout (files through `write_parquet`, tables through `duckdb`):
- `budget_lines.parquet` (`BL_COLS`) from `builder_inputs.json.gz` (`gzip` + `json`) `source_rows`: `fiscal_year = str(edition)`, `source_document_id = "1"`, `source_sheet = sheet`, `source_cells = cells`, `amount_thousands = str(...)`, `line_item_code = ERA_PROGRAM_CODES[edition][int(pe_bli.rsplit("L", 1)[1])]` for era keys, else `pe_bli`; `documents.parquet` with one row id `"1"`;
- DuckDB: `fct_decade_series` from `series` (`edition_year = edition`, `amount_type_kind = kind`, null axes); `p1_era_line_map` from the literal `ERA_MEMBERS` × `ERA_PROGRAM_CODES` (31 rows: account `3010F`, organization `AF`, era key `3010F-AF-L<line>`, `program_key` = code, `decision` `history_only` for F0150P/F015E0 else `same_program`, `decision_id = DECISION_IDS[code]`), minus the (edition, line) pairs in `drop_map`; `dim_programs` = the six `MODERN_MEMBERS` codes with their account and org `F`, plus `extra_programs`;
- `site/json/f15_funding_history.json` = the bytes of `tests/fixtures/f15/history.json`.
Returns (DuckDB path, site dir).

The tests:

```python
def seed(tmp_path, *, world_kw=None, paths=None, **kw):
    db, site = make_f15_world(tmp_path / "fam2", **(world_kw or {}))
    args = dict(constants=literal_constants(), duckdb_path=db, site_dir=site,
                decided_on="2026-10-21", owner_reply=REPLY, paths=paths or tmp_paths(tmp_path / "seeds"))
    args.update(kw)
    return seed_shipped_f15(**args), args["paths"]


def test_literal_copies_equal_the_shipped_module():
    from govbudget import f15_funding_history as f15

    assert (f15.MODERN_MEMBERS, f15.ERA_MEMBERS, f15.ERA_PROGRAM_CODES, f15.PROGRAMS, f15.PROGRAM_NOTES,
            f15.NOTE_RECEIPTS, f15.SCOPE_NOTE, f15.COVERAGE_NOTES) == (
        MODERN_MEMBERS, ERA_MEMBERS, ERA_PROGRAM_CODES, PROGRAMS, PROGRAM_NOTES, NOTE_RECEIPTS,
        SCOPE_NOTE, COVERAGE_NOTES)


def test_owner_reply_file_is_the_verbatim_approval():
    assert REPLY_FILE.read_bytes() == (REPLY + "\n").encode("utf-8")


def _x1_registry(tmp_path):
    write_world(tmp_path / "seeds-x", World())
    return tmp_paths(tmp_path / "seeds-x" / "data-seeds")


def _f15_registry(tmp_path):
    seed(tmp_path / "first")
    return tmp_paths(tmp_path / "first" / "seeds")


def _site_one_byte_off(tmp_path):
    db, site = make_f15_world(tmp_path / "fam2-tampered")
    hist = site / "json" / "f15_funding_history.json"
    hist.write_bytes(hist.read_bytes() + b" ")
    return {"duckdb_path": db, "site_dir": site}


SEED_REFUSALS = [
    # (case id, how -> seed() keyword overrides, fragment)
    ("registry-holds-a-family", lambda t: {"paths": _x1_registry(t)}, "registry already holds x-1"),
    ("f15-exists", lambda t: {"paths": _f15_registry(t)}, "f-15 already in platform_families.json"),
    ("site-sha", _site_one_byte_off, "pin"),
    ("programs", lambda t: {"constants": replace(literal_constants(), programs=[
        dict(p, title="F-15 EX") if p["code"] == "F015EX" else p for p in PROGRAMS])}, "programs[4].title"),
    ("scope-note", lambda t: {"constants": replace(literal_constants(), scope_note=SCOPE_NOTE + " ")},
     "scope_note"),
    ("coverage-notes", lambda t: {"constants": replace(literal_constants(), coverage_notes=COVERAGE_NOTES[:-1])},
     "coverage_notes"),
    ("roster", lambda t: {"world_kw": {"drop_map": [(2023, 74)]}}, "roster"),
    ("blank-reply", lambda t: {"owner_reply": " "}, "owner_reply"),
    ("non-iso-date", lambda t: {"decided_on": "21 Oct 2026"}, "decided_on"),
    ("stage-one", lambda t: {"constants": replace(literal_constants(),
                                                  expected_from=dict(EXPECTED_FROM, **{"0207146F": 2016}))},
     "coverage_expected_from_edition"),
    ("stage-two", lambda t: {"world_kw": {"extra_programs": [("F01500", "3011F", "F")]}}, "collision"),
]


@pytest.mark.parametrize("how,fragment", [c[1:] for c in SEED_REFUSALS], ids=[c[0] for c in SEED_REFUSALS])
def test_seed_refusal(tmp_path, how, fragment):
    kw = how(tmp_path)
    paths = kw.get("paths") or tmp_paths(tmp_path / "seeds")
    before = {p: p.read_bytes() for p in (paths.json, paths.members, paths.era_lines) if p.exists()}
    with pytest.raises(RegistryError) as exc:
        seed(tmp_path, **kw)
    assert any(fragment in line for line in exc.value.errors), "\n".join(exc.value.errors)
    assert {p: p.read_bytes() for p in (paths.json, paths.members, paths.era_lines) if p.exists()} == before


def test_seed_lists_every_input_refusal_at_once(tmp_path):
    with pytest.raises(RegistryError) as exc:
        seed(tmp_path, owner_reply="", decided_on="2026-10-32",
             constants=replace(literal_constants(), scope_note="x"))
    text = str(exc.value)
    assert "owner_reply" in text and "decided_on" in text and "scope_note" in text


def test_seed_writes_atomically(tmp_path, monkeypatch):
    def fail(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(era_map.os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        seed(tmp_path)
    assert not (tmp_path / "seeds").exists() or not any((tmp_path / "seeds").iterdir())


def test_seed_writes_the_entry_and_returns_counts(tmp_path):
    counts, paths = seed(tmp_path)
    assert counts == {"members": 8, "era_lines": 31, "rulings": 1}
    reg = load_registry(paths)
    f15 = reg["f-15"]
    assert [f.platform_family for f in reg.published()] == ["f-15"]
    assert (f15.status, f15.published_ruling_id, f15.short_name, f15.history_dataset, f15.on_partial_corpus) == (
        "published", "R-DEC-FAM-F15-SEED", "F-15", "f15_funding_history", "skip")
    assert [m.member_id for m in f15.counted] == [p["id"] for p in PROGRAMS]
    assert [m.code for m in f15.code_keyed] == list(MODERN_MEMBERS)
    assert [m.coverage_expected_from_edition for m in f15.counted] == [EXPECTED_FROM[p["code"]] for p in PROGRAMS]
    assert {m.code: m.drift_sha256 for m in f15.counted} == DRIFT
    assert f15.counted[4].titles_seen == ((2024, "F-15EX"), (2025, "F-15EX"), (2026, "F-15EX"))
    assert len(f15.era_lines) == 31 and len(f15.counted[0].titles_seen) == 10
    assert f15.program_notes["P-1:3010F:AF:F015E0"].note == PROGRAM_NOTES["F015E0"]["note"]
    assert (f15.scope_note, list(f15.coverage_notes)) == (SCOPE_NOTE, COVERAGE_NOTES)
    ruling = reg.rulings["R-DEC-FAM-F15-SEED"]
    assert (ruling.kind, ruling.platform_family, ruling.decided_by, ruling.decided_on, ruling.owner_reply,
            ruling.seed_basis, ruling.spec, ruling.text) == (
        "class", "f-15", "owner", "2026-10-21", REPLY, True, F15_SEED_SPEC, F15_SEED_RULING_TEXT)
    assert F15_SEED_SPEC == ("docs/superpowers/specs/2026-10-20-families-piece2-registry-design.md"
                             "#81-r-dec-fam-f15-seed-class-ruling-pending-owner-approval-with-this-spec")
    assert F15_SEED_RULING_TEXT == (
        "The F-15 family's registry entry records the eight budget lines the shipped F-15 history counts,"
        " as they ship at main 88538c6a. It records: their order, identities and display titles; the"
        " coverage rule (which lines are expected in which editions); the 31-line era roster; the F015E0"
        " note and its receipt; the family's scope and coverage notes. It changes no published figure,"
        " text or fact ID. Its evidence basis is the shipped family history (the F-15 family funding"
        " correction recorded in the ROADMAP on 2026-09-24), the piece-1 era decisions and the page's"
        " record-link narratives. Piece 3 must add an independent signal for each line before any F-15"
        " row changes.")


def test_seed_strips_exactly_one_trailing_newline_from_the_reply(tmp_path):     # D13
    for i, (given, kept) in enumerate([(REPLY_FILE.read_text(encoding="utf-8"), REPLY),
                                       (REPLY + "\n\n", REPLY + "\n")]):
        _counts, paths = seed(tmp_path / str(i), owner_reply=given)
        assert load_registry(paths).rulings["R-DEC-FAM-F15-SEED"].owner_reply == kept


def _f15_slice_texts(committed, out) -> dict[Path, str]:
    """The committed registry cut to the F-15 entry (family f-15, ruling R-DEC-FAM-F15-SEED, the f-15
    member and era-line rows), serialized by registry_texts at `out`'s paths. Tasks 8a and 8b add the
    F-35 beside the entry; the slice never sees it."""
    doc = json.loads(committed.json.read_text(encoding="utf-8"))

    def f15_rows(path):
        with path.open(encoding="utf-8", newline="") as fh:
            return [row for row in csv.DictReader(fh) if row["platform_family"] == "f-15"]

    doc.update(rulings=[r for r in doc["rulings"] if r["ruling_id"] == "R-DEC-FAM-F15-SEED"],
               sources=[],  # the F-15 entry cites no source (§7.6)
               families=[f for f in doc["families"] if f["platform_family"] == "f-15"])
    return registry_texts(out, doc=doc, members=f15_rows(committed.members),
                          era_lines=f15_rows(committed.era_lines))


def test_seed_reproduces_the_committed_f15_entry_byte_for_byte(tmp_path):
    _counts, paths = seed(tmp_path, owner_reply=REPLY_FILE.read_text(encoding="utf-8"))
    for path, text in _f15_slice_texts(DEFAULT_PATHS, paths).items():
        assert path.read_bytes() == text.encode("utf-8"), path.name


def test_committed_registry_loads_with_the_f15_published():
    reg = load_registry()
    f15 = reg["f-15"]
    assert (f15.status, f15.published_ruling_id, len(f15.members), len(f15.era_lines)) == (
        "published", "R-DEC-FAM-F15-SEED", 8, 31)
    assert reg.rulings["R-DEC-FAM-F15-SEED"].platform_family == "f-15"
    assert "f-15" in [f.platform_family for f in reg.published()]
```

The last two tests read only the F-15 slice of the committed files. Task 8a's draft F-35 and its `msar-pb2027` source, and Task 8b's 19 member rows, 63 era lines and `R-DEC-FAM-F35-B1`, leave them green, so Task 8a Step 5, Task 8b Step 4, Task 9b Step 6 and Task 10a Step 1 run them unchanged. Before Task 8a the slice is the whole registry, so at this task the byte-for-byte test compares all three files whole.

- [ ] **Step 3: Check the literal block against `88538c6a`**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && diff <(git show 88538c6a:GovBudget/src/govbudget/f15_funding_history.py | sed -n 19,108p) <(sed -n '/^# --- literal copies (88538c6a f15_funding_history.py:19-108) ---$/,/^# --- end literal copies ---$/p' tests/test_f15_registry_parity.py | sed '1d;$d') && echo IDENTICAL`
Expected: `IDENTICAL`

- [ ] **Step 4: Run the tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_registry_parity.py -q`
Expected: collection error, `ImportError: cannot import name 'F15_SEED_RULING_TEXT' from 'govbudget.platform_families'`.

- [ ] **Step 5: Write the seed in `src/govbudget/platform_families.py`**

Pinned values: `F15_SEED_RULING_TEXT` and `F15_SEED_SPEC` exactly as Step 2 asserts; `F15Constants` as in Interfaces; and the §7.6 values the Python module does not hold:

```python
F15_SEED_ROWS = {  # code: (valid_from, valid_to, era_decision_ids, record-link fact, purpose, variant_ids, variant_scope, program_tag)
    "0207134F": (2017, 2026, (), "0026c924483c6624", "develop", "C;D;E;EX", "shared", "F-15"),
    "0207146F": (2021, 2026, (), "d9982379a24ebac6", "develop", "EX", "variant", "F-15EX"),
    "0207171F": (2017, 2026, (), "b30fae1fd23999e4", "develop", "E;EX", "shared", "EPAWSS"),
    "F01500": (2017, 2026, ("F01500|3010F||2017-2023",), "c9e5c28dfebc879e", "upgrade", "C;D;E", "shared", "F-15"),
    "F015EX": (2021, 2026, ("F015EX|3010F||2021-2023",), "e7d5bcfb4a30f458", "buy", "EX", "variant", "F-15EX"),
    "F15EWS": (2019, 2026, ("F15EWS|3010F||2019-2023",), "b3dbc6ed30814fdf", "upgrade", "E", "variant", "EPAWSS"),
    "F0150P": (2017, 2020, ("F0150P|3010F||2017-2020",), None, "", "", "", "F-15"),
    "F015E0": (2020, 2022, ("F015E0|3010F||2020-2022",), None, "", "", "", "F-15EX"),
}
```

Each page row's `scope_note` is `RECORD_CONFIG[code].scopeNote` copied verbatim from `site/src/lib/f15-family-data.ts:10-15` into a sibling constant `F15_SEED_SCOPE_NOTES: Mapping[str, str]` (six entries; Task 7e's mirror test proves them against the TypeScript); the two history-only rows have none.

`seed_shipped_f15(*, constants: F15Constants, duckdb_path: Path, site_dir: Path, decided_on: str, owner_reply: str, paths: RegistryPaths = DEFAULT_PATHS) -> dict`. Order:
1. **Input refusals, all collected.** First `owner_reply = owner_reply.removesuffix("\n")` (D13: exactly one trailing newline is stripped, so the CLI wrapper passes the reply file's text as read; `test_seed_strips_exactly_one_trailing_newline_from_the_reply`). Then: `paths.json` exists and names any family (`registry already holds <ids>`, and `f-15 already in platform_families.json` when f-15 is one); `paths.members` or `paths.era_lines` exists with a data row; `owner_reply.strip()` empty (`owner_reply`); `decided_on` not `^\d{4}-\d{2}-\d{2}$` or rejected by `date.fromisoformat` (`decided_on`); `site_dir/json/f15_funding_history.json` missing or its sha256 ≠ the first token of `verify_era_map.F15_HISTORY_PIN` (reason names both hashes and the word `pin`); the shipped payload's `programs` vs `constants.programs` index by index, key by key over each dict's keys (`programs[<i>].<key>`, plus a length mismatch); `scope_note` and `coverage_notes` vs the constants (reason names the key). Any step-1 refusal raises here, all of them together, **before the lake opens** (R6; Task 7b's wrapper test proves the one-off refusal reads no lake).
2. **Build** (read only the constants and `F15_SEED_ROWS`): the family object = §7.2's F-15 column — `status` `published`, `published_ruling_id` `R-DEC-FAM-F15-SEED`, `short_name` `F-15`, `history_dataset` `f15_funding_history`, `on_partial_corpus` `skip`, `headline` `{"measure": "cumulative_actuals", "first_fy": 2015, "last_fy": 2024}`, `scope_note`/`coverage_notes` from the constants, `review_guard` `{"exhibits": ["P-1", "R-1"], "title_substrings": ["F-15", "F15"]}`, `program_notes` `{"P-1:3010F:AF:F015E0": {"note": program_notes["F015E0"]["note"], "note_fact_id": "e7d5bcfb4a30f458", "expected_receipt": note_receipts["e7d5bcfb4a30f458"]}}` (built generically from `program_notes` × `note_receipts`, keyed by the program's `id`), `variants` `[{"id": v} for v in ("A", "B", "C", "D", "E", "EX")]`, `program_tags` `[{"tag": "F-15", "mdap_code": None}, {"tag": "F-15EX", "mdap_code": None}, {"tag": "EPAWSS", "mdap_code": None}]`, `purpose_tags` `[]`, `caveat_ids` `["classified", "construction", "nominal_dollars", "cr_years"]`, `exclusions` `[]`, `aliases` `[]`, `contract_routes`/`official_estimates`/`art` `None`. The ruling: `ruling_id` `R-DEC-FAM-F15-SEED`, `kind` `class`, `platform_family` `f-15`, `decided_by` `owner`, `decided_on`, `owner_reply` (after step 1's newline strip, otherwise verbatim), `spec` `F15_SEED_SPEC`, `text` `F15_SEED_RULING_TEXT`, `seed_basis` `True`. `sources` `[]`. One member row per `constants.programs` entry, in that order: `member_id` = the program's `id`, `exhibit`/`account`/`organization`/`code` from it, `role` `counted`, `verdict` `approved`, `appropriation` `procurement` for P-1 and `rdte` for R-1, `display_title` = its `title`, `page_slug` = its `program_slug` or `""`, the valid range, era decisions, purpose, variants, scope and tag from `F15_SEED_ROWS`, `scope_note` from `F15_SEED_SCOPE_NOTES` (blank for the two history-only rows), `coverage_expected_from_edition` = `expected_from[code]` (blank for `None`), `member_order` = position + 1, `services_using` `USAF`, `paying_org` `AF`, `evidence` = the `era:<id>` refs then `fact:<id>` when set, `decided_by` `owner`, `ruling_id` `R-DEC-FAM-F15-SEED`, `decided_on`; every other column blank. Era rows: for each `(edition, [(line, ba, title)])` in `era_members` and its code `era_program_codes[edition][line]`, `(f-15, P-1:3010F:AF:<code>, edition, 3010F-AF-L<line>, ba, title, <the member's one era decision id>)`.
3. **Measure:** `open_lake(duckdb_path)`; per row `measure_member(lake, Member.from_row(row), headline=…)` fills `titles_seen`, `budget_activities` and `drift_sha256`; the measured era lines are compared with step 2's era rows as (member_id, edition, era_key, budget_activity, filed_title, decision_id) sets, each difference a refusal containing `roster`; raise every roster refusal together.
4. **Validate the result:** `parse_registry(doc, rows, era_rows, era_decisions=<era_map.read_seed(era_map.default_seed_path()) by decision_id>, paths=paths)` (its `RegistryError` propagates); then `check_lake(registry, lake=lake, site_dir=site_dir, families=["f-15"]).raise_if_failed()`; close the lake.
5. **Write:** `write_registry(paths, doc=doc, members=rows, era_lines=era_rows)` (one atomic replace of the three files); return `{"members": len(rows), "era_lines": len(era_rows), "rulings": 1}`.

- [ ] **Step 6: Run the seed tests (not yet the two that read the committed files)**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_registry_parity.py -q -k "not reproduces and not committed"`
Expected: `17 passed, 2 deselected`.

- [ ] **Step 7: Run the seed once against fam2**

fam2 is a snapshot, so no SAM guard is needed (exempt). The run checks that the module's constants still equal the literal copies, then seeds.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
FAM2_DUCKDB="$GOVBUDGET_PROOFS/fam2/duckdb/govbudget.duckdb"; FAM2_SITE="$GOVBUDGET_PROOFS/fam2/site"
test -f "$FAM2_DUCKDB" && test -d "$FAM2_SITE" || { echo "fam2 snapshot missing (Task 1)"; exit 1; }
FAM2_DUCKDB="$FAM2_DUCKDB" FAM2_SITE="$FAM2_SITE" uv run --project . python - <<'PY'
import os, sys
from pathlib import Path
sys.path[:0] = ["tests"]
from test_f15_registry_parity import REPLY_FILE, literal_constants
from govbudget import f15_funding_history as f15
from govbudget.platform_families import seed_shipped_f15
c = literal_constants()
assert (f15.PROGRAMS, f15.MODERN_MEMBERS, f15.ERA_MEMBERS, f15.ERA_PROGRAM_CODES, f15.PROGRAM_NOTES,
        f15.NOTE_RECEIPTS, f15.SCOPE_NOTE, f15.COVERAGE_NOTES) == (
    c.programs, c.modern_members, c.era_members, c.era_program_codes, c.program_notes,
    c.note_receipts, c.scope_note, c.coverage_notes)
print(seed_shipped_f15(constants=c, duckdb_path=Path(os.environ["FAM2_DUCKDB"]),
                       site_dir=Path(os.environ["FAM2_SITE"]), decided_on="2026-10-21",
                       owner_reply=REPLY_FILE.read_text(encoding="utf-8")))   # the seed strips the one "\n" (D13)
PY
```

Expected: `{'members': 8, 'era_lines': 31, 'rulings': 1}`. A `RegistryError` lists every refusal; stop and report it (never edit the constants or the files to pass). A `duckdb.IOException` naming a lock: wait and re-run.

- [ ] **Step 8: Inspect what the seed wrote**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && wc -l data-seeds/platform_family_members.csv data-seeds/platform_family_era_lines.csv && cut -d, -f1 data-seeds/platform_family_members.csv && grep -c '^f-15,' data-seeds/platform_family_era_lines.csv && grep -o '[0-9a-f]\{64\}' data-seeds/platform_family_members.csv | sort -u | wc -l && git -C .. status --short GovBudget/data-seeds GovBudget/data/research/platform_families`
Expected:
- line counts `9` and `32`;
- `member_row_id`, then `f-15|P-1:3010F:AF:F01500|2017-2026`, `f-15|P-1:3010F:AF:F0150P|2017-2020`, `f-15|P-1:3010F:AF:F015E0|2020-2022`, `f-15|P-1:3010F:AF:F015EX|2021-2026`, `f-15|P-1:3010F:AF:F15EWS|2019-2026`, `f-15|R-1:3600F:AF:0207134F|2017-2026`, `f-15|R-1:3600F:AF:0207146F|2021-2026`, `f-15|R-1:3600F:AF:0207171F|2017-2026`;
- `31`;
- `8` distinct 64-hex values (the eight `drift_sha256`, equal to the measured table; a different value means fam2's F-15 lines moved: stop and report);
- `?? GovBudget/data-seeds/platform_families.json`, `?? GovBudget/data-seeds/platform_family_era_lines.csv`, `?? GovBudget/data-seeds/platform_family_members.csv`, `?? GovBudget/data/research/platform_families/`.

- [ ] **Step 9: Run the parity and loader tests**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_registry_parity.py tests/test_platform_families_loader.py tests/test_f15_funding_history.py tests/test_f15_era_identity.py tests/test_capture_f15_fixtures.py -q`
Expected: `261 passed` (19 parity, 199 loader, and 43 F-15 items: the 21 functions of `test_f15_funding_history.py` collect as 34, plus 4 and 5; collected 2026-10-21). The last three files are untouched by this task.

- [ ] **Step 10: Lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uvx --offline ruff check --isolated --select F,E9 src/govbudget/platform_families.py tests/test_f15_registry_parity.py`
Expected: `All checks passed!` (the literal block's names are module globals the tests read, so F401/F841 do not fire).

- [ ] **Step 11: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_families.py GovBudget/tests/test_f15_registry_parity.py GovBudget/data-seeds/platform_families.json GovBudget/data-seeds/platform_family_members.csv GovBudget/data-seeds/platform_family_era_lines.csv GovBudget/data/research/platform_families/f-15/owner-reply-R-DEC-FAM-F15-SEED.txt && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): seed the F-15 as registry entry #1 under R-DEC-FAM-F15-SEED (piece 2 task 3a)

Measured on fam2; the seed's tests reproduce the committed entry from the
pinned F-15 fixtures byte for byte.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3b: The facade derives the F-15 constants from the registry

**Spec:** §10.4 (the facade table), §13 (`tests/test_f15_registry_parity.py`), §17 risks 1–2. Line numbers are at
HEAD `b6c9a8d9`.
- Of `src/`, the link fix changed only two files, and this task touches neither:
  - `export_site.py`: precision, flows, the district readers, and the new `_require_link_award_keys` and
    `_named_link_awards_sql` (`:824` and `:858`). None of the family-history call site's lines changed (now
    `:3932-3938`).
  - `flow_chart.py`: the bridge families, which since M-3 (`8e23089b`) call `_require_link_award_keys`.
- `f15_funding_history.py`, `program_pdf_receipts.py`, `cli.py` and `verify_phase5.py` equal `88538c6a` (checked
  2026-10-21 at `b6c9a8d9`).
- Anchor on the quoted names.

**Files:**
- Modify: `src/govbudget/f15_funding_history.py:9-108` (the imports, then the constants block `MODERN_MEMBERS = {` …
  `COVERAGE_NOTES = [ … ]`). The functions at `:111-497` stay today's code in this task.
- Modify: `tests/test_f15_registry_parity.py` (append four tests).

**Interfaces:**
- Consumes (Tasks 2a–2c, 3a):
  - `platform_families.load_registry(paths: RegistryPaths = DEFAULT_PATHS, *, era_decisions_path=None) -> Registry`;
    the module attribute `platform_families.DEFAULT_PATHS`; `RegistryPaths(json, members, era_lines)`;
    `RegistryError(ValueError)` (`.errors: list[str]`, built as `RegistryError(lines)`);
  - `Registry.__getitem__`; `Family.counted`, `Family.code_keyed` (D5, in `member_order`), `Family.era_lines`,
    `Family.program_notes: Mapping[member_id, ProgramNote]`, `Family.scope_note`, `Family.coverage_notes`;
    `Member.titles_seen: tuple[tuple[int, str], ...]`, `Member.member_row_id`, `Member.page_slug: str`;
    `EraLine(platform_family, member_id, edition: int, era_key, budget_activity, filed_title, decision_id)`;
    `ProgramNote(note, note_fact_id, expected_receipt)`;
  - `govbudget.jbooks.era_keys._ERA_KEY_RE` (group 3 is the line);
  - the committed registry files (3a) and the literal copies Task 3a puts in `tests/test_f15_registry_parity.py`.
    Task 3a's module-level `SHIPPED = literal_constants()` (an `F15Constants`: `programs`, `modern_members`,
    `era_members`, `era_program_codes`, `program_notes`, `note_receipts`, `scope_note`, `coverage_notes`,
    `expected_from`; R11).
- Produces (I-FACADE constants; names and types exactly as at `88538c6a`):
  - `F15: Family`, bound at import by `platform_families.load_registry(platform_families.DEFAULT_PATHS)["f-15"]`.
    The facade reads the module attribute at call time, so a test can redirect it;
  - `MODERN_MEMBERS: dict[str, tuple[str, str, str]]`, `ERA_MEMBERS: dict[int, list[tuple[int, str, str]]]`,
    `ERA_PROGRAM_CODES: dict[int, dict[int, str]]`, `PROGRAMS: list[dict]`, `PROGRAM_NOTES: dict[str, dict]`,
    `NOTE_RECEIPTS: dict[str, dict]`, `SCOPE_NOTE: str`, `COVERAGE_NOTES: list[str]`.
  - The function names are unchanged until Task 4.

**Depends on:** 3a.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_f15_registry_parity.py`; merge the imports below into the file's import block, since `pytest` is already imported there and ruff's F811 would flag a re-import)

```python
import importlib
import shutil

import pytest

from govbudget import f15_funding_history as facade
from govbudget import platform_families as pf

FACADE_FIELDS = {
    "MODERN_MEMBERS": "modern_members", "ERA_MEMBERS": "era_members",
    "ERA_PROGRAM_CODES": "era_program_codes", "PROGRAMS": "programs",
    "PROGRAM_NOTES": "program_notes", "NOTE_RECEIPTS": "note_receipts",
    "SCOPE_NOTE": "scope_note", "COVERAGE_NOTES": "coverage_notes",
}


@pytest.mark.parametrize("name,field", sorted(FACADE_FIELDS.items()))
def test_facade_constant_equals_its_88538c6a_literal(name, field):
    assert getattr(facade, name) == getattr(SHIPPED, field)


def test_facade_constants_keep_the_88538c6a_order_and_types():
    assert list(facade.MODERN_MEMBERS) == ["0207134F", "0207146F", "0207171F", "F01500", "F015EX", "F15EWS"]
    assert list(facade.ERA_MEMBERS) == list(range(2017, 2024)) == list(facade.ERA_PROGRAM_CODES)
    for edition, rows in facade.ERA_MEMBERS.items():
        assert [line for line, _, _ in rows] == sorted(line for line, _, _ in rows)
        assert list(facade.ERA_PROGRAM_CODES[edition]) == sorted(facade.ERA_PROGRAM_CODES[edition])
    assert sum(map(len, facade.ERA_MEMBERS.values())) == 31
    assert [p["code"] for p in facade.PROGRAMS] == [
        "0207134F", "0207146F", "0207171F", "F01500", "F015EX", "F15EWS", "F0150P", "F015E0"]
    assert type(facade.COVERAGE_NOTES) is list and len(facade.COVERAGE_NOTES) == 7


def test_registry_coverage_columns_reproduce_the_88538c6a_expected_rule():
    counted = {m.code: m for m in facade.F15.counted}
    assert {code: m.coverage_expected_from_edition for code, m in counted.items()} == dict(SHIPPED.expected_from)
    assert all(m.valid_to_edition == 2026 for m in counted.values() if m.coverage_expected_from_edition is not None)


def test_a_registry_fault_at_import_names_the_file_and_the_row(tmp_path, monkeypatch):
    bad = pf.RegistryPaths(*(tmp_path / p.name for p in (pf.DEFAULT_PATHS.json, pf.DEFAULT_PATHS.members,
                                                          pf.DEFAULT_PATHS.era_lines)))
    for src, dst in zip((pf.DEFAULT_PATHS.json, pf.DEFAULT_PATHS.members, pf.DEFAULT_PATHS.era_lines), bad):
        shutil.copyfile(src, dst)
    row = "f-15|R-1:3600F:AF:0207146F|2021-2026"
    lines = bad.members.read_text(encoding="utf-8").split("\n")
    lines = [l.replace(",counted,approved,", ",counted,maybe,", 1) if l.startswith(row + ",") else l for l in lines]
    bad.members.write_text("\n".join(lines), encoding="utf-8")
    monkeypatch.setattr(pf, "DEFAULT_PATHS", bad)
    try:
        with pytest.raises(pf.RegistryError) as raised:
            importlib.reload(facade)
    finally:
        monkeypatch.undo()
        importlib.reload(facade)
    assert "platform_family_members.csv" in str(raised.value) and row in str(raised.value)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_registry_parity.py -q -k "facade or coverage_columns or registry_fault"`

Expected: `2 failed, 9 passed`. `test_registry_coverage_columns_reproduce_the_88538c6a_expected_rule` fails with
`AttributeError: module 'govbudget.f15_funding_history' has no attribute 'F15'`, and
`test_a_registry_fault_at_import_names_the_file_and_the_row` fails with `DID NOT RAISE`. The parity and order
tests already pass on the literals; they are the guard for Step 3.

- [ ] **Step 3: Replace the constants block in `src/govbudget/f15_funding_history.py:19-108` with derivations from `F15`**

Keep the module docstring and today's imports, and add `from govbudget import platform_families` and `from
govbudget.jbooks.era_keys import _ERA_KEY_RE`. Each name is one derivation over `F15`:

| Name | Derived as |
|---|---|
| `F15` | `platform_families.load_registry(platform_families.DEFAULT_PATHS)["f-15"]` |
| `MODERN_MEMBERS` | `{m.code: (m.exhibit, m.account, title)}` over `F15.code_keyed`, where `title` is the one distinct value in `m.titles_seen`. More than one distinct title raises `RegistryError([f"platform-families: platform_family_members.csv:{m.member_row_id}: the F-15 facade needs one title in titles_seen, found {sorted(titles)}"])` |
| `ERA_MEMBERS` | `{edition: [(line, budget_activity, filed_title), …]}` over `F15.era_lines`, editions ascending, lines ascending **as integers**. `line = int(_ERA_KEY_RE.fullmatch(era_key).group(3))`; the CSV's string order puts `L25` before `L3`, so never keep file order. A non-integer line raises `RegistryError([f"platform-families: platform_family_era_lines.csv:f-15|{edition}|{era_key}: the F-15 facade needs an integer line number"])` |
| `ERA_PROGRAM_CODES` | `{edition: {line: <code of the EraLine's member>}}`, same orders |
| `PROGRAMS` | over `F15.counted` (in `member_order`): `dict(id=m.member_id, code=m.code, title=m.display_title, program_slug=m.page_slug or None, exhibit=m.exhibit, account=m.account, organization=m.organization)`, plus `note`/`note_fact_id` when `m.member_id in F15.program_notes` |
| `PROGRAM_NOTES` | `{member.code: dict(note=pn.note, note_fact_id=pn.note_fact_id)}` over `F15.program_notes` |
| `NOTE_RECEIPTS` | `{pn.note_fact_id: dict(pn.expected_receipt)}` |
| `SCOPE_NOTE` / `COVERAGE_NOTES` | `F15.scope_note` / `list(F15.coverage_notes)` (a list: the parity test compares with a list) |

Replace the long comments with one line naming the source: the registry entry `f-15` in
`data-seeds/platform_families.json` and its two CSVs; `tests/test_f15_registry_parity.py` holds the `88538c6a`
literals.

- [ ] **Step 4: Run the parity tests and every importer of the facade**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_registry_parity.py -q`
Expected: no failures. The 11 items this task added (8 parametrized, plus 3) pass.

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_funding_history.py tests/test_f15_era_identity.py tests/test_capture_f15_fixtures.py -q`
Expected: `43 passed` (34 + 4 + 5, the count at `b30134c4` and at `b6c9a8d9`, re-measured 2026-10-21).

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_verify_era_map.py tests/test_verify_era_map_def.py tests/test_verify_era_map_gh.py tests/test_export_era_line_map.py tests/test_era_fact_stability.py tests/test_budget_pdf_export_workflow.py -q`
Expected: `121 passed` (76 + 13 + 21 + 11; re-measured 2026-10-21 on a clean `git archive` of `b6c9a8d9`, which the link fix left unchanged).

- [ ] **Step 5: Prove the frozen files are byte-unchanged and the lint is at baseline**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && git diff --quiet 88538c6a -- tests/test_f15_funding_history.py tests/test_f15_era_identity.py tests/test_capture_f15_fixtures.py tests/fixtures/f15 scripts/era/capture_f15_fixtures.py && echo UNCHANGED && uvx --offline ruff check --isolated --select F,E9 src/govbudget/f15_funding_history.py`
Expected: `UNCHANGED`, then `All checks passed!`

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/f15_funding_history.py GovBudget/tests/test_f15_registry_parity.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): the F-15 facade derives its constants from the registry (piece 2 Task 3b)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: The generic history builder and the facade wrappers

**Spec:** §10.1 (the function table), §10.2 (standard vs registry), §10.3 (coverage), §10.4 (the wrappers), §11 (the
formula templates), §13 (`tests/test_platform_family_history.py`). Anchors are in `src/govbudget/f15_funding_history.py`
at HEAD: `_json_bytes` :111-112, `check_program_notes` :115-125, `member_row` :128-147, `_point_measure` :150-159,
`build_history` :162-241, `build_program_matrix` :244-344.

**Files:**
- Create: `src/govbudget/platform_family_history.py`.
- Modify: `src/govbudget/f15_funding_history.py`. Lines `:111-344` become wrappers. `_json_bytes` and
  `_point_measure` move to the new module, and the facade re-exports `_json_bytes`. Drop the imports the wrappers no
  longer use (`defaultdict`, `deepcopy`, `InvalidOperation`); `export_f15_funding_history` (`:347-497`) is unchanged
  until Task 5 and keeps working on the wrappers.
- Create: `tests/test_platform_family_history.py`.

**Interfaces:**
- Consumes: I-REG types `Family` (`counted`, `code_keyed`, `members`, `era_lines`, `review_guard`, `headline`,
  `program_notes`, `short_name`, `platform_family`, `history_dataset`, `scope_note`, `coverage_notes`), `Member`
  (`title_for(edition)`, `page_slug`, `role`, `verdict`, editions), `EraLine`, `ReviewGuard(exhibits,
  title_substrings)`, `Headline(measure, first_fy, last_fy)`; `era_map.ERA_ORG_TO_MODERN = {"ARMY": "A", "NAVY": "N",
  "AF": "F"}`; `export_site.fact_id_workbook`, `fact_id_derived`, `_amount_type_meta`, `_decade_measure_token`
  (imported inside the functions, as today: `export_site` is never imported at module level).
- Produces (I-HIST, pure part):
  - `member_row(family: Family, row: Mapping) -> bool`;
  - `build_history(family, source_rows: list[dict], series: list[dict], *, retrieved_at: str, current_fact_ids:
    set[str] | None = None) -> tuple[dict | None, dict, dict, dict]`;
  - `build_program_matrix(family, payload: dict, previews: dict, *, existing_citations: dict, retrieved_at: str) ->
    tuple[dict, dict, dict]`;
  - `check_program_notes(family, programs: list[dict], registry: Mapping[str, dict]) -> None` (`registry` = the
    citations mapping);
  - `expected_members(family, edition: int) -> frozenset[str]`;
  - `ANNUAL_FORMULA`, `CUMULATIVE_FORMULA`, `CELL_FORMULA` (str templates);
    `reuse_formulas(member_id: str, edition: int, fy: int, kind: str, amount_type: str | None) -> list[str]`;
  - helpers (R9): `program_entries(family) -> list[dict]` (the `PROGRAMS` shape, used by the matrix,
    the facade and stage 3) and `check_headline(family, payload: dict) -> None` (called by Task 5's post-pass only);
    `_json_bytes(value) -> bytes` and `_point_measure(kind, measures)` (moved verbatim).
  - I-FACADE functions, each with `family=F15` bound: `member_row(row)`,
    `build_history(source_rows, series, *, retrieved_at, current_fact_ids=None)`,
    `build_program_matrix(payload, previews, *, existing_citations, retrieved_at)`,
    `check_program_notes(programs, registry)`; `PROGRAMS` rebinds to `program_entries(F15)` (the same value).

**Depends on:** 3b.

- [ ] **Step 1: Write the failing tests** (`tests/test_platform_family_history.py`)

Imports: `import pytest`; `from dataclasses import replace`; `from govbudget.export_site import fact_id_derived`; `from
govbudget.platform_families import EraLine, Headline, ReviewGuard, load_registry`; `from
govbudget.platform_family_history import (ANNUAL_FORMULA, CELL_FORMULA, CUMULATIVE_FORMULA, _json_bytes,
build_history, build_program_matrix, check_headline, expected_members, member_row, program_entries,
reuse_formulas)`.

Test scaffolding, defined at the top of the file:
- `F15 = load_registry()["f-15"]`.
- `_member(member_id, title, *, family="f-35", valid=(2017, 2026), titles=None, order=None, role="counted",
  page_slug=None)` is `dataclasses.replace(F15.counted[0], …)`. It sets
  `member_row_id=f"{family}|{member_id}|{first}-{last}"`, `platform_family=family`, the four identity fields split
  from `member_id`, `role`, `verdict="approved"`,
  `titles_seen=tuple((e, title) for e in (titles if titles is not None else range(first, last + 1)))` (a tuple, never
  a generator: `F35` is shared by every test, and `title_for` reads `titles_seen` on every call), `display_title=title`,
  `page_slug=page_slug if page_slug is not None else (code if role == "counted" else "")`, the editions,
  `coverage_expected_from_edition=first if role == "counted" else None`, `member_order=order`,
  `era_decision_ids=()` and `evidence=()`.
- `F35` is `replace(F15, platform_family="f-35", short_name="F-35", history_dataset="f35_funding_history",
  on_partial_corpus="raise", review_guard=ReviewGuard(exhibits=("P-1", "R-1"), title_substrings=("F-35", "F35",
  "JSF", "JOINT STRIKE", "F135", "LIGHTNING")), headline=Headline("cumulative_actuals", 2015, 2024),
  program_notes={}, scope_note="Synthetic F-35-shaped scope note.", coverage_notes=("Synthetic coverage note.",),
  members=…, era_lines=…)`. It is built without stage 1; the builder is pure. Its members follow. In the `titles`
  column, `all` passes `titles=None`, `2024–2026` passes `titles=range(2024, 2027)`, and `none` passes `titles=()`.
  `none` gives an empty `titles_seen`, and that is harmless: `member_row` matches a context row by its code (step 4),
  never by its titles.

  | order | `member_id` | title | valid | `titles` |
  |---|---|---|---|---|
  | 1 | `P-1:3010F:AF:ATA000` | F-35 | 2017–2026 | 2024–2026 |
  | 2 | `P-1:1506N:NAVY:0152` | JSF STOVL | 2017–2026 | 2024–2026 |
  | 3 | `R-1:3600F:AF:0207142F` | F-35 Squadrons | 2017–2026 | all |
  | 4 | `R-1:1319N:NAVY:0604800M` | JSF EMD | 2017–2026 (synthetic; so a PB2026 row is in range) | all |
  | 5 | `R-1:1319N:NAVY:0604810N` | JSF Follow-On Modernization | 2017–2020 | all |
  | — | `P-1:3020F:AF:JSM000` (role `context`) | Joint Strike Missile | 2017–2026 | none |

  It has one era line: `EraLine("f-35", "P-1:3010F:AF:ATA000", 2020, "3010F-AF-L1", "01", "F-35", "ATA000|3010F||2017-2023")`.
- `_row(pe, edition, *, exhibit, account, organization, title, amount_type="fy_2024_actuals", value=10,
  budget_activity="01", cells="J20")` is the shape of `tests/test_f15_funding_history.py::source`. `_point(row, *,
  fy=2024, kind="actuals", n=1, amount=None)` is the shape of its `point`. `_previews(leaves, family)` is that file's
  `matrix` preview builder; it reads the code of an era leaf from `family.era_lines`.

```python
def test_templates_are_the_spec_section_11_text():
    assert ANNUAL_FORMULA == ("sum(budget_lines.amount_thousands) for reviewed {short_name} members, PB{edition}, "
                              "FY{fy} {kind}; one selected scenario column per workbook line")
    assert CUMULATIVE_FORMULA == ("sum(budget_lines.amount_thousands) via annual reviewed {short_name} actuals totals, "
                                  "FY{a}–FY{b}; each fiscal year once, nominal USD thousands; excludes "
                                  "enacted/current-year figures and requests")
    assert CELL_FORMULA == ("sum(budget_lines.amount_thousands) for workbook program {member_id}, PB{edition}, "
                            "FY{fy} {kind}; each selected workbook input once")


def test_reuse_formulas_lists_own_then_edition_then_bare():
    own = ("sum(budget_lines.amount_thousands) for workbook program P-1:3010F:AF:F01500, PB2018, FY2016 actuals; "
           "each selected workbook input once")
    assert reuse_formulas("P-1:3010F:AF:F01500", 2018, 2016, "actuals", "fy_2016_base_oco") == [
        own, "sum(budget_lines.amount_thousands where amount_type=fy_2016_base_oco and edition=2018)",
        "sum(budget_lines.amount_thousands where amount_type=fy_2016_base_oco)"]
    assert reuse_formulas("P-1:3010F:AF:F01500", 2018, 2016, "actuals", None) == [own]


def test_four_accounts_sum_once_into_one_annual_point():
    rows = [_row("ATA000", 2026, exhibit="P-1", account="3010F", organization="F", title="F-35", value=100, cells="J10"),
            _row("0152", 2026, exhibit="P-1", account="1506N", organization="N", title="JSF STOVL", value=20, cells="J11"),
            _row("0207142F", 2026, exhibit="R-1", account="3600F", organization="F", title="F-35 Squadrons", value=3, cells="J12"),
            _row("0604800M", 2026, exhibit="R-1", account="1319N", organization="N", title="JSF EMD", value=4, cells="J13")]
    payload, citations, leaves, _ = build_history(F35, rows, [_point(r) for r in rows], retrieved_at="2026-10-21")
    (point,) = payload["points"]
    assert point["amount_thousands"] == 127 and len(leaves) == 4
    assert {c["program_slug"] for c in point["components"]} == {"ATA000", "0152", "0207142F", "0604800M"}
    assert point["fact_id"] == fact_id_derived("family_history", "f-35|2026|2024", "actuals")
    assert citations[point["fact_id"]]["formula"] == ("sum(budget_lines.amount_thousands) for reviewed F-35 members, "
                                                      "PB2026, FY2024 actuals; one selected scenario column per workbook line")
    assert point["missing_programs"] == [] and point["coverage"] == "covered-records"
    assert payload["family_id"] == "f-35" and payload["scope_note"] == "Synthetic F-35-shaped scope note."
    assert payload["cumulative"]["fact_id"] == fact_id_derived("family_history", "f-35|2024|2024", "cumulative-actuals")


def test_navy_rows_accept_the_era_and_modern_spellings_only():
    row = _row("0604800M", 2026, exhibit="R-1", account="1319N", organization="N", title="JSF EMD")
    assert member_row(F35, row) and member_row(F35, {**row, "organization": "NAVY"})
    with pytest.raises(ValueError, match=r"^F-35 modern member identity drift: 2026/0604800M$"):
        member_row(F35, {**row, "organization": "F"})


def test_a_member_ending_at_pb2020_is_not_missing_afterwards():
    a = _row("0207142F", 2020, exhibit="R-1", account="3600F", organization="F", title="F-35 Squadrons", amount_type="fy_2018_actuals")
    b = _row("0207142F", 2021, exhibit="R-1", account="3600F", organization="F", title="F-35 Squadrons", amount_type="fy_2019_actuals")
    payload, *_ = build_history(F35, [a, b], [_point(a, fy=2018), _point(b, fy=2019)], retrieved_at="2026-10-21")
    missing = {p["edition"]: p["missing_programs"] for p in payload["points"]}
    assert missing == {2020: ["0152", "0604800M", "0604810N", "ATA000"], 2021: ["0152", "0604800M", "ATA000"]}


def test_era_roster_attribution_counts_as_present():
    era = _row("3010F-AF-L1", 2020, exhibit="P-1", account="3010F", organization="AF", title="F-35", amount_type="fy_2018_actuals")
    payload, *_ = build_history(F35, [era], [_point(era, fy=2018)], retrieved_at="2026-10-21")
    (point,) = payload["points"]
    assert point["missing_programs"] == ["0152", "0207142F", "0604800M", "0604810N"]
    assert point["components"][0]["program_slug"] is None and point["components"][0]["dataset"] == "budget_lines_decade"


def test_a_context_row_is_never_summed_and_silences_the_guard():
    ata = _row("ATA000", 2026, exhibit="P-1", account="3010F", organization="F", title="F-35", cells="J10")
    jsm = _row("JSM000", 2026, exhibit="P-1", account="3020F", organization="F", title="Joint Strike Missile", cells="J11")
    assert member_row(F35, jsm) is False
    payload, _, leaves, _ = build_history(F35, [ata, jsm], [_point(ata), _point(jsm)], retrieved_at="2026-10-21")
    assert [c["pe_bli"] for c in payload["points"][0]["components"]] == ["ATA000"] and len(leaves) == 1


def test_an_unreviewed_joint_strike_row_raises():
    row = _row("JSF999", 2026, exhibit="P-1", account="3010F", organization="F", title="JOINT STRIKE SPARES")
    with pytest.raises(ValueError, match=r"^Unreviewed F-35 workbook identity: 2026/JSF999$"):
        member_row(F35, row)


def test_a_code_keyed_row_outside_titles_seen_is_identity_drift():
    row = _row("0604810N", 2021, exhibit="R-1", account="1319N", organization="N", title="JSF Follow-On Modernization")
    with pytest.raises(ValueError, match=r"^F-35 modern member identity drift: 2021/0604810N$"):
        member_row(F35, row)


def test_a_multi_input_cell_mints_the_family_dataset_and_cell_formula():
    first = _row("ATA000", 2026, exhibit="P-1", account="3010F", organization="F", title="F-35", value=100, cells="J10")
    second = {**first, "budget_activity": "05", "amount_thousands": 20, "cells": "J20"}
    payload, _, leaves, _ = build_history(F35, [first, second], [_point(first, n=2, amount=120)], retrieved_at="2026-10-21")
    enriched, additions, _ = build_program_matrix(F35, payload, _previews(leaves, F35), existing_citations={}, retrieved_at="2026-10-21")
    (cell,) = enriched["points"][0]["program_cells"]
    assert cell["dataset"] == "f35_funding_history" and cell["amount_thousands"] == 120
    assert cell["fact_id"] == fact_id_derived("family_program_history", "P-1:3010F:AF:ATA000|2026|2024", "actuals")
    assert additions[cell["fact_id"]]["formula"] == ("sum(budget_lines.amount_thousands) for workbook program "
                                                     "P-1:3010F:AF:ATA000, PB2026, FY2024 actuals; each selected workbook input once")
    assert enriched["programs"] == program_entries(F35)
    assert [p["id"] for p in enriched["programs"]] == [m.member_id for m in F35.counted]


def test_expected_members_reproduces_the_88538c6a_f15_rule():
    for edition in range(2017, 2027):
        today = {"0207134F", "0207171F"} | ({"0207146F"} if edition >= 2021 else set()) \
            | ({"F01500", "F015EX", "F15EWS"} if edition >= 2024 else set())
        assert expected_members(F15, edition) == frozenset(today), edition


def test_check_headline_refuses_a_window_unlike_the_registry():
    assert check_headline(F35, {"cumulative": {"start_fy": 2015, "end_fy": 2024}}) is None
    with pytest.raises(ValueError, match=r"^F-35 cumulative window FY2016–FY2024 differs from the registry headline FY2015–FY2024$"):
        check_headline(F35, {"cumulative": {"start_fy": 2016, "end_fy": 2024}})


def test_the_f15_facade_delegates_to_the_generic_builder():
    from govbudget import f15_funding_history as facade
    row = _row("0207130F", 2026, exhibit="R-1", account="3600F", organization="F", title="F-15 Squadrons")
    with pytest.raises(ValueError, match=r"^Unreviewed F-15 workbook identity: 2026/0207130F$"):
        facade.member_row(row)
    assert facade.PROGRAMS == program_entries(facade.F15) and facade.F15 == F15
    assert facade._json_bytes is _json_bytes
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_family_history.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'govbudget.platform_family_history'`.

- [ ] **Step 3: Create `src/govbudget/platform_family_history.py` with the pure builder**

Module-level imports: `from govbudget.platform_families import EraLine, Family, Member` and
`from govbudget.jbooks.era_map import ERA_ORG_TO_MODERN`. `export_site` is imported inside the functions, as today.

The templates are module constants, exact text (copy from the Step 1 test): `ANNUAL_FORMULA`,
`CUMULATIVE_FORMULA`, `CELL_FORMULA`. Fill them with `str.format`.

**The generic rules.** `build_history` and `build_program_matrix` are today's bodies (`:162-344`) with these
substitutions. Nothing else changes: not the edition offsets, sorts, point ids, default rule, cumulative rule,
breakdown shapes, `_point_measure` or the reuse ranking.

| Today | Generic |
|---|---|
| `member_row(row)` per row | one per-family lookup built once per call (not once per row), then the membership rule below |
| `program_slug=row["pe_bli"] if … in MODERN_MEMBERS` (components and leaf `pe_bli`) | `member.page_slug or None` for a code-keyed row; `None` for an era row |
| `f"f-15\|{edition}\|{fy}"`, `f"f-15\|{min}\|{max}"` | `f"{family.platform_family}\|…"` (same surfaces and metric strings) |
| the three formula literals and the reuse list `:313-320` | the templates; `reuse_formulas(program_id, edition, fy, kind, amount_type)`, passing `None` when the cell's amount types are mixed |
| hardcoded `expected` `:218-223`; `present = {r["pe_bli"]}` | `expected_members(family, edition)`; `present` = the member code of each component (a code-keyed row's code; an era row's roster member's code) |
| `family_id="f-15"`, `SCOPE_NOTE`, `COVERAGE_NOTES` | `family.platform_family`, `family.scope_note`, `list(family.coverage_notes)` |
| `deepcopy(PROGRAMS)`; `programs` keyed by code | `deepcopy(program_entries(family))`, keyed by code |
| `ERA_PROGRAM_CODES[edition].get(int(line))` | the roster member's code for `(edition, era_key)` |
| `row["organization"] in {"F", "AF"}` (`:293`) | `row["organization"] in {member.organization, ERA_ORG_TO_MODERN.get(member.organization, member.organization)}` |
| `dataset = "f15_funding_history"` | `family.history_dataset` |
| every "F-15" in a message | `family.short_name`. For example `Duplicate {short_name} scenario: …` and `{short_name} matrix/annual total mismatch: …`; every other text stays exactly as it is |

The `\|` in this table are Markdown escapes; the code uses a bare `|`.

**`member_row(family, row)`.** The check order is pinned; it reproduces today's F-15 outcomes, and the
`test_f15_funding_history.py` cases depend on the order.
1. If `row["exhibit"] not in {"P-1", "R-1"}`, return False.
2. If `row["pe_bli"]` is the code of an **approved counted** member, this is a code-keyed match. Its identity is
   (exhibit, account, `member.title_for(edition)`), with organization in {era spelling, modern spelling}. A mismatch
   raises `f"{short_name} modern member identity drift: {edition}/{pe}"`, and that includes an edition with no
   `titles_seen` entry. Otherwise return True.
3. If `(edition, pe_bli)` is an era key of the family's roster, this is an era match. Its identity is exactly
   (`"P-1"`, member account, member organization in the era spelling, the line's `budget_activity`, its
   `filed_title`). A mismatch raises `f"{short_name} era member identity drift: {edition}/{pe}"`. Otherwise return
   True.
4. If a row of the family covers the lake row, return False. A covering row has verdict `approved` and a role other
   than `counted`, or verdict `rejected`; it has the same exhibit, account and code, an organization in its two
   spellings, and an edition inside its range.
5. If the exhibit is in `review_guard.exhibits` and any substring is in `(row.get("title") or "").upper()`, raise
   `f"Unreviewed {short_name} workbook identity: {edition}/{pe}"`.
6. Return False.

Step 2 covers era-only counted members too (F0150P, F015E0). A code-keyed lake row for one of them raises identity
drift, where today it would read "Unreviewed" or be dropped. No such row exists in the live lake or in
`tests/fixtures/f15/builder_inputs.json.gz`; measured 2026-10-21, code-keyed rows exist only for the six
`MODERN_MEMBERS` codes, inside their `titles_seen` editions. So no byte moves.

**The other signatures:**
- `expected_members(family, edition) -> frozenset[str]` = `{m.code for m in family.counted if
  m.coverage_expected_from_edition is not None and m.coverage_expected_from_edition <= edition <= m.valid_to_edition}`.
- `program_entries(family) -> list[dict]` is the Task 3b `PROGRAMS` derivation over `family.counted`.
- `check_program_notes(family, programs, registry)` is today's body. Its expected receipts are `{pn.note_fact_id:
  dict(pn.expected_receipt) for pn in family.program_notes.values()}`, and its message is
  `f"{short_name} program note receipt mismatch: {code}/{fid}"`.
- `reuse_formulas(...)` returns `[CELL_FORMULA filled]`, plus the two `where` forms when `amount_type` is not None.
- `check_headline(family, payload)` compares `payload["cumulative"]` `start_fy`/`end_fy` with
  `family.headline.first_fy`/`last_fy`. A mismatch raises `f"{short_name} cumulative window FY{a}–FY{b} differs from
  the registry headline FY{first}–FY{last}"`. It is never called by `build_history`: the frozen F-15 tests build
  one-year cumulatives, for example FY2024 alone in `test_exact_scenario_selection_excludes_disc_reconciliation_and_earlier_request`.

- [ ] **Step 4: Turn the facade's functions into wrappers** (`src/govbudget/f15_funding_history.py:111-344`)

`member_row`, `build_history`, `build_program_matrix` and `check_program_notes` become `def` wrappers with today's
signatures, each calling the generic function with `F15`. Use `def`, not `functools.partial`:
`scripts/era/capture_f15_fixtures.py` imports these names, and its test monkeypatches `build_history`.
Add `PROGRAMS = program_entries(F15)` in place of the Task 3b comprehension, and
`from govbudget.platform_family_history import _json_bytes`.

- [ ] **Step 5: Run the new tests, V5 and every facade importer**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_family_history.py tests/test_f15_registry_parity.py -q`
Expected: no failures; `tests/test_platform_family_history.py` passes 13.

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_funding_history.py tests/test_f15_era_identity.py tests/test_capture_f15_fixtures.py tests/test_verify_era_map.py tests/test_verify_era_map_def.py tests/test_verify_era_map_gh.py tests/test_export_era_line_map.py tests/test_era_fact_stability.py tests/test_budget_pdf_export_workflow.py -q`
Expected: `164 passed`. V5's golden, fresh-state and sensitivity tests are among them; a red V5 means the
generic rules moved a byte.

- [ ] **Step 6: Frozen files and lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && git diff --quiet 88538c6a -- tests/test_f15_funding_history.py tests/test_f15_era_identity.py tests/test_capture_f15_fixtures.py tests/fixtures/f15 scripts/era/capture_f15_fixtures.py && echo UNCHANGED && uvx --offline ruff check --isolated --select F,E9 src/govbudget/f15_funding_history.py src/govbudget/platform_family_history.py`
Expected: `UNCHANGED`, then `All checks passed!`

- [ ] **Step 7: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_family_history.py GovBudget/src/govbudget/f15_funding_history.py GovBudget/tests/test_platform_family_history.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): one generic family-history builder; the F-15 functions become wrappers (piece 2 Task 4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Registry-driven receipt grammar and audit

**Spec:** §11 ("`program_pdf_receipts.additive_budget_formula`", "The receipt audit"), §16
(`budget_pdf_receipts_audit.json` identical), D4. Anchors in `src/govbudget/program_pdf_receipts.py` at HEAD:
`additive_budget_formula` :266-278 (the three literal tails :273-277); the audit block :458-467 inside
`export_program_pdf_receipts`.

**Run order:** after Task 3a, and before Task 5.

**Files:**
- Modify: `src/govbudget/program_pdf_receipts.py:266-278`, `:458-467`.
- Modify: `tests/test_budget_pdf_receipts.py` (append four tests; the existing 16 are untouched).
- Modify: `tests/test_f15_registry_parity.py` (append the tail literal and its test).

**Interfaces:**
- Consumes: `platform_families.load_registry()`, `Registry.published()`, `Family.short_name`,
  `Family.history_path`, the committed registry (3a).
- Produces (I-RCPT):
  - `family_formula_tails(registry: Registry) -> list[str]`;
  - `additive_budget_formula(formula: str, *, registry: Registry | None = None) -> bool`; the one-argument call in
    `attach_additive_receipts` and in `tests/test_export_decade_era_map.py` keeps working;
  - `default_cell_counts(site_dir: Path, registry: Registry, receipts: Mapping[str, dict]) -> tuple[int, int]`. The
    third parameter (R8): `default_complete` counts `receipts[fact_id]["complete"]`, so it cannot be computed from
    the site and the registry alone;
  - `_default_registry() -> Registry`, `functools.lru_cache(maxsize=1)` over `load_registry()`.
  - `export_program_pdf_receipts`' signature is unchanged; `tests/test_budget_pdf_export_workflow.py` pins its
    keyword arguments.

**Depends on:** 3a.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_f15_registry_parity.py`:

```python
# program_pdf_receipts.py:274-276 at 88538c6a, in order.
RECEIPT_TAILS_88538C6A = [
    r" for reviewed F-15 members, PB20\d{2}, FY20\d{2} (?:actuals|enacted|request); one selected scenario column per workbook line",
    r" for workbook program (?:P-1|R-1):[A-Za-z0-9:]+, PB20\d{2}, FY20\d{2} (?:actuals|enacted|request); each selected workbook input once",
    r" via annual reviewed F-15 actuals totals, FY20\d{2}–FY20\d{2}; each fiscal year once, nominal USD thousands; excludes enacted/current-year figures and requests",
]


def test_family_formula_tails_equal_the_88538c6a_strings():
    from govbudget.platform_families import load_registry   # local: Task 6 may land before Task 3b's imports
    from govbudget.program_pdf_receipts import family_formula_tails
    assert family_formula_tails(load_registry()) == RECEIPT_TAILS_88538C6A
```

Append to `tests/test_budget_pdf_receipts.py`, with these imports: `dataclasses.replace`, `hashlib`, `inspect`,
`re`; `from govbudget import program_pdf_receipts`; `from govbudget.program_pdf_receipts import
additive_budget_formula, default_cell_counts, export_program_pdf_receipts, family_formula_tails`; `from
govbudget.platform_families import load_registry`.

```python
def annual(name):
    return (f"sum(budget_lines.amount_thousands) for reviewed {name} members, PB2026, FY2024 actuals;"
            " one selected scenario column per workbook line")


def cumulative(name):
    return (f"sum(budget_lines.amount_thousands) via annual reviewed {name} actuals totals, FY2015–FY2024;"
            " each fiscal year once, nominal USD thousands; excludes enacted/current-year figures and requests")


def with_family(short_name, status="published"):
    registry = load_registry()
    f15 = registry["f-15"]
    other = replace(f15, platform_family="b-52", short_name=short_name, history_dataset="b52_funding_history",
                    status=status, published_ruling_id=f15.published_ruling_id if status == "published" else None)
    return replace(registry, families=(f15, other))


def test_a_second_published_family_widens_the_grammar_and_a_draft_does_not():
    published, draft = with_family("B-52"), with_family("B-52", status="draft")
    for formula in (annual("B-52"), cumulative("B-52")):
        assert additive_budget_formula(formula, registry=published)
        assert not additive_budget_formula(formula, registry=draft)
        assert not additive_budget_formula(formula)                       # committed registry: F-15 alone
    assert additive_budget_formula(annual("F-15")) and additive_budget_formula(annual("F-15"), registry=published)
    tails = family_formula_tails(published)
    assert [t.split(" members")[0] for t in tails[:2]] == [" for reviewed F-15", " for reviewed B-52"]
    assert tails[2].startswith(" for workbook program ") and len(tails) == 5
    assert [t.split(" actuals totals")[0] for t in tails[3:]] == [" via annual reviewed F-15", " via annual reviewed B-52"]


def test_receipt_tails_insert_short_name_verbatim_never_re_escaped():
    assert re.escape("F-15") == "F\\-15"                                   # why D4 exists (Python 3.12)
    assert "F\\-15" not in "".join(family_formula_tails(load_registry()))
    assert "re.escape" not in inspect.getsource(program_pdf_receipts.family_formula_tails)
    assert additive_budget_formula(annual("KC-46 A/B"), registry=with_family("KC-46 A/B"))


def _history(points, defaults):
    return json.dumps({"points": [{"id": i, "program_cells": [{"fact_id": f} for f in cells]} for i, cells in points],
                       "default_point_ids": defaults})


def test_default_cell_counts_sum_over_published_family_artifacts(tmp_path):
    (tmp_path / "json").mkdir()
    (tmp_path / "json/f15_funding_history.json").write_text(_history([("fy2024a", ["a", "b"]), ("fy2025e", ["c"])], ["fy2024a"]))
    (tmp_path / "json/b52_funding_history.json").write_text(_history([("fy2024a", ["d"])], ["fy2024a"]))
    receipts = {"a": {"complete": True}, "b": {"complete": False}, "c": {"complete": True}, "d": {"complete": True}}
    assert default_cell_counts(tmp_path, with_family("B-52"), receipts) == (3, 2)
    assert default_cell_counts(tmp_path, with_family("B-52", status="draft"), receipts) == (2, 1)
    (tmp_path / "json/b52_funding_history.json").unlink()
    assert default_cell_counts(tmp_path, with_family("B-52"), receipts) == (2, 1)


def test_the_receipt_audit_keeps_its_keys_and_order(tmp_path):
    (tmp_path / "json").mkdir()
    (tmp_path / "json/citations.json").write_text("{}")
    (tmp_path / "json/f15_funding_history.json").write_text(_history([("fy2024a", ["a", "b"])], ["fy2024a"]))
    (tmp_path / "manifest.json").write_text("[]")
    report = export_program_pdf_receipts(site_dir=tmp_path, manifest=tmp_path / "manifest.json", cache_dir=tmp_path / "cache")
    assert list(report) == ["schema_version", "full_corpus", "citation_sha256", "source_count", "leaf_count",
                            "receipt_count", "complete_receipts", "books", "default_cells", "default_complete",
                            "unmatched_cells", "shard_prefix_length", "highlight_geometry"]
    assert (report["default_cells"], report["default_complete"]) == (2, 0)
    assert json.loads((tmp_path / "json/budget_pdf_receipts_audit.json").read_text()) == report
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_budget_pdf_receipts.py tests/test_f15_registry_parity.py -q`
Expected: `ImportError: cannot import name 'default_cell_counts'` (or `family_formula_tails`) at collection.

- [ ] **Step 3: Implement I-RCPT in `src/govbudget/program_pdf_receipts.py`**

**`family_formula_tails(registry)`** returns, in this order:
1. the annual tail of every published family, in JSON order;
2. the generic `for workbook program …` tail, once;
3. the cumulative tail of every published family, in JSON order.

With the F-15 alone, that is `RECEIPT_TAILS_88538C6A`, exactly (`[annual, generic, cumulative]`). Build each
family tail by concatenating the `RECEIPT_TAILS_88538C6A` text around `short_name`, inserted **verbatim** (D4).
Stage-1 rule 3 (`^[A-Za-z0-9][A-Za-z0-9 /-]*$`) admits no character that is special in a regex outside a character
class. Do not use `str.format` or an f-string on the regex text: either would consume the `{2}` in `\d{2}`. The
test greps the function's source for `re.escape`, so do not name it in the docstring either.

**`additive_budget_formula(formula, *, registry=None)`.** Today's body, with `tails = family_formula_tails(registry
if registry is not None else _default_registry())`.

**`default_cell_counts(site_dir, registry, receipts)`.**
- For each family in `registry.published()` whose `site_dir / family.history_path` exists, collect the
  `program_cells` of the points whose `id` is in `default_point_ids`. This is today's `:459-462`; a missing artifact
  adds nothing, as today.
- Return `(len(cells), sum(receipts.get(c["fact_id"], {}).get("complete", False) for c in cells))`.

**The audit (`:458-467`).** Replace the `history_path` block with `default_cells, default_complete =
default_cell_counts(site_dir, _default_registry(), receipts)`. Keep the `report` dict literal's key order exactly.
The file is written with `json.dumps(report, indent=2)` and no `sort_keys`, and §16 requires
`budget_pdf_receipts_audit.json` to be byte-identical in the A/B.

- [ ] **Step 4: Run the tests**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_budget_pdf_receipts.py tests/test_f15_registry_parity.py tests/test_export_decade_era_map.py tests/test_budget_pdf_export_workflow.py -q`
Expected: no failures. `tests/test_budget_pdf_receipts.py` passes 20 (16 + 4), `tests/test_export_decade_era_map.py`
24 and `tests/test_budget_pdf_export_workflow.py` 11.

- [ ] **Step 5: The audit and the grammar against fam2, read-only**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - "$GOVBUDGET_PROOFS/fam2/site" <<'EOF'
import json, sys
from pathlib import Path
from govbudget.platform_families import load_registry
from govbudget.program_pdf_receipts import default_cell_counts, family_formula_tails
site = Path(sys.argv[1]); registry = load_registry()
history = json.loads((site / "json/f15_funding_history.json").read_text())
ids = {c["fact_id"] for p in history["points"] if p["id"] in history["default_point_ids"] for c in p["program_cells"]}
receipts = {}
for prefix in {i[:3] for i in ids}:
    receipts.update(json.loads((site / f"json/budget-pdf-receipts/v2/{prefix}.json").read_text()))
audit = json.loads((site / "json/budget_pdf_receipts_audit.json").read_text())
print(default_cell_counts(site, registry, receipts), (audit["default_cells"], audit["default_complete"]), len(family_formula_tails(registry)))
EOF
```

Expected: `(67, 67) (67, 67) 3`. The live export read 67/67 on 2026-10-21 with today's logic.

- [ ] **Step 6: Lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uvx --offline ruff check --isolated --select F,E9 src/govbudget/program_pdf_receipts.py`
Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/program_pdf_receipts.py GovBudget/tests/test_budget_pdf_receipts.py GovBudget/tests/test_f15_registry_parity.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): receipt grammar and audit come from the published registry families (piece 2 Task 6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Export integration: stage 3, the post-pass and `json/families/index.json`

**Spec:** §9.3 (stage 3, items 1–8), §10.1 (the post-pass "keeps today's post-pass exactly"), §12 (`index.json`),
§16 (the expected A/B difference), §17 risks 4–5. Anchors, at `b6c9a8d9`:
- `f15_funding_history.py:347-497` (`export_f15_funding_history`);
- in `export_site.py`, the call site `:3932-3938`: the comment `# Family history is a bounded additive projection over
  the completed`, then `from govbudget.f15_funding_history import export_f15_funding_history` and the call. It comes after
  `manifest.json` is written at `:3926-3930` (`# Update manifest with json_sidecars count`), and its return block is at
  `:3948-3959`. These were `:3869-3875`, `:3863-3867` and `:3885-3896` at `b30134c4`. The link fix added 63 lines above
  them (61 in round 2, 2 in M-3's docstring) and changed none of them;
- `program_pdf_receipts.py:281-318` (`attach_additive_receipts`, the leaf rule).

**Run Task 6 first.** Stage-3 item 4 calls `additive_budget_formula(formula, registry=…)`.

**Files:**
- Modify: `src/govbudget/platform_families.py` (append stage 3: `expand_leaves`, `check_citations`, `index_projection`).
- Modify: `src/govbudget/platform_family_history.py` (module imports, `INDEX_PATH`, `export_family_histories`).
- Modify: `src/govbudget/f15_funding_history.py:347-497`. `export_f15_funding_history` becomes a wrapper. Drop the
  imports it no longer uses (`Counter`, `Decimal`, `json`, `os`, `Path`, `tempfile`, and whichever others ruff
  names).
- Modify: `src/govbudget/export_site.py:3932-3938` (the call site quoted above).
- Delete: `scripts/export_f15_funding_history.py` (§10.1. Nothing calls it: on 2026-10-21, `grep -rn
  export_f15_funding_history src scripts tests site/scripts` hits only this file, the facade, `export_site.py` and
  a comment in the frozen `scripts/era/capture_f15_fixtures.py:63`, which stays).
- Modify: `tests/test_platform_families_loader.py` (stage-3 cases) and `tests/test_platform_family_history.py`
  (post-pass cases).

**Interfaces:**
- Consumes:
  - from Task 4: `build_history`, `build_program_matrix`, `check_program_notes`, `program_entries`, `check_headline`
    and `_json_bytes`;
  - from Task 6: `program_pdf_receipts.additive_budget_formula(formula, *, registry=None)`;
  - from Tasks 2b–2c: `parse_ref(ref) -> (prefix, parts)`, `open_lake(duckdb_path) -> LakeReader`,
    `check_lake(registry, *, lake, site_dir, families=None) -> LakeReport` (`.raise_if_failed()`), and
    `corpus_gate(family, series_codes) -> bool` (False = skip, raise = D5's message);
  - from `export_site`: `_fetch_program_identity(con) -> _ProgramIdentity` (`.accounts(pe_bli)`,
    `.slug(pe_bli, account, account_title, organization=None)`) and `_stage_parquet_path`;
  - `workbook_cells.build_workbook_previews` and `config.SITE_DIR`.
- Produces:
  - I-REG stage 3:
    - `expand_leaves(fact_id: str, citations: Mapping[str, Mapping]) -> list[tuple[str, str, str]]`;
    - `check_citations(family, *, registry: Registry, citations: Mapping[str, Mapping], minted: Mapping[str, Mapping],
      identity, site_dir: Path, claimed: dict[tuple[str, str, str], str] | None = None) -> list[str]`. The keyword
      `claimed` (R10): stage-3 item 7 needs state shared across families. Pass one dict through every family of a
      pass; Task 7a's `verify-families` leg c does the same;
    - `index_projection(registry) -> dict` (D7).
  - I-HIST:
    - `INDEX_PATH = "json/families/index.json"`;
    - `export_family_histories(*, duckdb_path: Path, out_dir: Path, registry: Registry, families: Sequence[str] |
      None = None, preview: bool = False) -> dict | None`. It returns `{"citations": int, "json_files": int,
      "families": {pf: {"annual_points", "source_facts", "added_citations", "cumulative_actuals_thousands"}}}`.
  - I-FACADE: `export_f15_funding_history(*, duckdb_path, out_dir) -> dict | None`, with today's six flat keys.
  - For Task 7c's preview and this task's tests (R15): the module-level names `build_workbook_previews`, `open_lake`, `check_lake` and
    `index_projection` in `platform_family_history`, which the tests monkeypatch.

**Depends on:** 4, 6.

- [ ] **Step 1: Write the failing stage-3 tests** (append to `tests/test_platform_families_loader.py`)

Imports: `hashlib`, `json`, `from dataclasses import replace`, `from govbudget.export_site import
_ProgramIdentity`, `from govbudget.platform_families import check_citations, expand_leaves, index_projection,
load_registry`, `from govbudget.platform_family_history import _json_bytes`.

Scaffolding:
- `F15 = load_registry()["f-15"]`.
- `NARRATIVE = dict(kind="jbook_narrative", page_number=71, pe_bli="F015EX",
  sha256="528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e")`.
- `REFS = ("0026c924483c6624", "d9982379a24ebac6", "b30fae1fd23999e4", "c9e5c28dfebc879e", "b3dbc6ed30814fdf")`.
- `_citations()` = `{"e7d5bcfb4a30f458": dict(NARRATIVE), **{f: dict(kind="jbook_narrative") for f in REFS}}`.
- `_identity(*codes)` = `_ProgramIdentity([(code, account, "Title", "F", True) for each counted F-15 member whose
  code is in codes])`.
- `_site(tmp_path, *codes)` writes `json/program_details/{code}.json` = `{}` for each code.
- `MODERN = ("0207134F", "0207146F", "0207171F", "F01500", "F015EX", "F15EWS")`.
- `ANNUAL = "sum(budget_lines.amount_thousands) for reviewed F-15 members, PB2026, FY2024 actuals; one selected
  scenario column per workbook line"`.
- `_wb(cells, amount, sha="a" * 64, sheet="Exhibit R-1")` = a `kind="workbook"`, `units="USD thousands"` citation.
- `_total(inputs, value, formula=ANNUAL)` = a `kind="derived"` citation with `recorded_value=f"{value:.3f}"` and
  `inputs=json.dumps(inputs)`.
- `_stage3(tmp_path, *, citations=None, minted=None, family=F15, identity_codes=MODERN, claimed=None)` calls
  `check_citations` with `registry=load_registry()` and `site_dir=_site(tmp_path, *identity_codes)`. It is named
  `_stage3`, never `_check`: Task 2c Step 2 already defines the module-level stage-2 helper `_check(tmp_path,
  w=None, **lake_kw)` in this file, and a second `def _check` would rebind it, so all 16 stage-2 tests that call it
  would fail (`TypeError`, or a list compared with a `LakeReport`). ruff's F rules do not flag the redefinition.

```python
def test_stage3_passes_on_the_committed_f15_entry(tmp_path):
    claimed = {}
    assert _stage3(tmp_path, minted={"1" * 16: _wb("J1", 1.0)}, claimed=claimed) == []
    assert claimed == {("a" * 64, "Exhibit R-1", "J1"): "f-15"}


def test_stage3_unresolved_fact_ref_is_named(tmp_path):
    cits = _citations(); del cits["0026c924483c6624"]
    (line,) = _stage3(tmp_path, citations=cits)
    assert line.startswith("platform-families: json/f15_funding_history.json: ")
    assert "fact:0026c924483c6624" in line and "f-15|R-1:3600F:AF:0207134F|2017-2026" in line


def test_stage3_note_receipt_mismatch_keeps_the_f15_message(tmp_path):
    cits = {**_citations(), "e7d5bcfb4a30f458": {**NARRATIVE, "page_number": 70}}
    assert any("F-15 program note receipt mismatch: F015E0/e7d5bcfb4a30f458" in l for l in _stage3(tmp_path, citations=cits))


def test_stage3_page_slug_must_match_the_program_identity(tmp_path):
    lines = _stage3(tmp_path, identity_codes=(*MODERN, "F0150P"))
    assert any("P-1:3010F:AF:F0150P page_slug None differs from the export's program page 'F0150P'" in l for l in lines)
    wrong = replace(F15, members=tuple(replace(m, page_slug="WRONG") if m.code == "0207134F" else m for m in F15.members))
    assert any("R-1:3600F:AF:0207134F page_slug 'WRONG'" in l for l in _stage3(tmp_path, family=wrong))


def test_stage3_minted_formula_must_pass_the_receipt_grammar(tmp_path):
    minted = {"2" * 16: _wb("J1", 1.0), "1" * 16: _total(["2" * 16], 1.0, "sum(budget_lines.amount_thousands) + 1")}
    assert any("1111111111111111 formula fails the receipt grammar" in l for l in _stage3(tmp_path, minted=minted))


def test_stage3_a_total_must_recompute_from_its_inputs(tmp_path):
    minted = {"2" * 16: _wb("J1", 1.0), "3" * 16: _wb("J2", 1.0), "1" * 16: _total(["2" * 16, "3" * 16], 3.0)}
    assert any("F-15 receipt 1111111111111111 does not recompute from its inputs" in l for l in _stage3(tmp_path, minted=minted))


def test_stage3_no_leaf_twice_in_one_total(tmp_path):
    minted = {"2" * 16: _wb("J1,J2", 2.0), "3" * 16: _wb("J2", 1.0), "1" * 16: _total(["2" * 16, "3" * 16], 3.0)}
    assert any("F-15 receipt 1111111111111111 counts leaf" in l and "/Exhibit R-1/J2 twice" in l
               for l in _stage3(tmp_path, minted=minted))


def test_stage3_a_published_fact_is_never_overwritten(tmp_path):
    cits = {**_citations(), "3" * 16: _total([], 0.0, "sum(budget_lines.amount_thousands)")}
    minted = {"3" * 16: _total([], 0.0, "sum(budget_lines.amount_thousands where amount_type=x)")}
    assert any("F-15 citation identity conflicts with published fact 3333333333333333" in l
               for l in _stage3(tmp_path, citations=cits, minted=minted))


def test_stage3_a_leaf_in_two_families_is_refused(tmp_path):
    claimed = {("a" * 64, "Exhibit R-1", "J1"): "b-1"}
    lines = _stage3(tmp_path, minted={"1" * 16: _wb("J1", 1.0)}, claimed=claimed)
    assert any("is counted by b-1 and f-15" in l for l in lines)


def test_expand_leaves_splits_cells_and_recurses_into_derived_inputs():
    cits = {"w1": _wb("J1, J2", 2.0), "w2": _wb("J2", 1.0), "t": _total(["w1", "w2"], 3.0), "c": _total(["t"], 3.0)}
    assert expand_leaves("c", cits) == [("a" * 64, "Exhibit R-1", "J1"), ("a" * 64, "Exhibit R-1", "J2"),
                                        ("a" * 64, "Exhibit R-1", "J2")]
    with pytest.raises(ValueError, match="not an additive workbook receipt"):
        expand_leaves("missing", cits)


def test_index_projection_of_the_committed_registry_is_spec_section_12():
    data = _json_bytes(index_projection(load_registry()))
    assert len(data) == 833
    assert hashlib.sha256(data).hexdigest() == "3657d3bd36fa8f344cf2c299714dacb11fe227100cd1ff0c3d3d22f6734f1945"
    (fam,) = index_projection(load_registry())["families"]
    assert [m["page_slug"] for m in fam["members"]][-2:] == [None, None] and fam["ruling_ids"] == ["R-DEC-FAM-F15-SEED"]


def test_index_projection_lists_published_families_counted_then_context():
    b1 = replace(F15, platform_family="b-1", short_name="B-1", history_dataset="b1_funding_history",
                 published_ruling_id="R-DEC-FAM-B1-PUB", members=(
                     _b1_member("P-1:3010F:AF:B00100", "counted", order=1),
                     _b1_member("P-1:3020F:AF:ZZ0001", "context"), _b1_member("P-1:3020F:AF:AA0001", "context")))
    draft = replace(b1, platform_family="x-1", short_name="X-1", history_dataset="x1_funding_history",
                    status="draft", published_ruling_id=None)
    out = index_projection(replace(load_registry(), families=(F15, b1, draft)))
    assert [f["platform_family"] for f in out["families"]] == ["f-15", "b-1"]
    b = out["families"][1]
    assert [(m["member_id"], m["role"]) for m in b["members"]] == [
        ("P-1:3010F:AF:B00100", "counted"), ("P-1:3020F:AF:AA0001", "context"), ("P-1:3020F:AF:ZZ0001", "context")]
    assert b["ruling_ids"] == ["R-DEC-FAM-B1-B1", "R-DEC-FAM-B1-PUB"]
    assert (b["route"], b["history"]) == ("/families/b-1/", "json/b1_funding_history.json")
```

`_b1_member(member_id, role, order=None)` is `replace(F15.counted[0], …)` with the identity split from
`member_id`, `platform_family="b-1"`, `role`, `verdict="approved"`, `member_order=order`, `page_slug=""` and
`ruling_id="R-DEC-FAM-B1-B1"`.

- [ ] **Step 2: Run the stage-3 tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_loader.py -q -k "stage3 or expand_leaves or index_projection"`
Expected: an `ImportError` naming `check_citations`, `expand_leaves` or `index_projection`.

- [ ] **Step 3: Append stage 3 to `src/govbudget/platform_families.py`**

`check_program_notes`, `program_entries` and `additive_budget_formula` are imported inside `check_citations`.
A module-level import would be circular, because `platform_family_history` imports this module.

**`expand_leaves(fact_id, citations)`:**
- A `workbook` citation gives `[(sha256, sheet, cell.strip()) for cell in cells.split(",") if cell.strip()]`.
- A `derived` citation gives the concatenation, in input order, of its `json.loads(inputs)` expansions. Duplicates
  are kept, so callers can see them.
- A missing fact, another kind, malformed `inputs`, or a cycle raises `ValueError(f"{fact_id}: not an additive
  workbook receipt")`.
- It does not judge formulas; item 4 does that.

**`check_citations(...)`.** Every line is `f"platform-families: {family.history_path}: {reason}"`. `merged =
{**citations, **minted}`. The items:

| §9.3 item | Check | Reason text |
|---|---|---|
| 1 | every `fact:` ref (`parse_ref`) in the `evidence` and `link_evidence` of the family's approved rows is a key of `citations` | `fact:{id} on {member_row_id} does not resolve in json/citations.json` |
| 2 | `check_program_notes(family, program_entries(family), citations)` | the `ValueError` text (keeps `{short_name} program note receipt mismatch: …`) |
| 3 | for each approved counted member, `slug = identity.slug(code, account, account_title, ERA_ORG_TO_MODERN.get(org, org))` when `identity.accounts(code)` is non-empty, else `code`. `account_title` comes from the `accounts()` row whose account equals the member's, else the first row's. `want = slug if (site_dir / "json/program_details" / f"{slug}.json").is_file() else None`. Fail when `(page_slug or None) != want` | `{member_id} page_slug {got!r} differs from the export's program page {want!r}` |
| 4 | every `derived` citation in `minted` passes `additive_budget_formula(formula, registry=registry)` | `{fid} formula fails the receipt grammar: {formula}` |
| 5 | every `derived` citation in `minted` has `Decimal(recorded_value)` equal to the sum of its inputs' values (`amount_thousands` for workbook inputs, `recorded_value` for derived ones, read from `merged`), and `expand_leaves(fid, merged)` has no duplicate | `{short_name} receipt {fid} does not recompute from its inputs` / `{short_name} receipt {fid} counts leaf {sha}/{sheet}/{cell} twice` |
| 6 | for `fid` in `minted` ∩ `citations`, the identity fields are equal. They are today's `:411` tuples: workbook (`kind, units, amount_thousands, sha256, sheet, cells, official_url`), derived (`kind, units, recorded_value, formula, inputs`) | `{short_name} citation identity conflicts with published fact {fid}` |
| 7 | when `claimed` is a dict: every leaf of every `workbook` citation in `minted` is absent from `claimed` or claimed by `family.platform_family`; then each is recorded as claimed by it | `leaf {sha}/{sheet}/{cell} is counted by {other} and {platform_family}` |

**`index_projection(registry)`** (D7) returns `{"families": [...], "schema_version": 1}` over
`registry.published()` in JSON order. Each family is:
- `{history: family.history_path, history_dataset, members, platform_family, route: family.route, ruling_ids,
  short_name}`;
- `members` = the approved counted rows in `member_order`, then the approved `context` rows by `member_id`, each as
  `{member_id, page_slug: page_slug or None, role}`;
- `ruling_ids` = `sorted({published_ruling_id} | {m.ruling_id for m in members listed})`.

- [ ] **Step 4: Run the stage-3 tests**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_loader.py -q`
Expected: no failures; the 12 new tests pass.

- [ ] **Step 5: Commit stage 3**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_families.py GovBudget/tests/test_platform_families_loader.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): registry stage 3 — citations, leaf expansion and the index projection (piece 2 Task 5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Write the failing post-pass tests** (append to `tests/test_platform_family_history.py`)

Imports added: `gzip`, `hashlib`, `json`, `duckdb`; `from pathlib import Path` (for `_v5_export`'s annotation;
`pytest` is already imported, Task 4); `from govbudget import config, platform_family_history`; `from
govbudget.platform_family_history import INDEX_PATH, export_family_histories`; `from govbudget.platform_families
import LakeReport, RegistryError`.

**`_v5_export(root, *, extra_rows=(), extra_series=(), drop_series=()) -> tuple[Path, Path]`** builds a mini export
from `tests/fixtures/f15/builder_inputs.json.gz` and returns `(duckdb_path, out_dir)`.

`root/lake/govbudget.duckdb` holds two tables:
- `fct_decade_series(pe_bli, fy, edition_year, amount_type_kind, amount, amount_type, n_source_rows)`, from
  `series` (`edition` → `edition_year`, `kind` → `amount_type_kind`) plus `extra_series`, minus the rows whose
  `pe_bli` is in `drop_series`;
- `dim_programs(pe_bli, org, exhibit_family, account, account_title, title)`, one row per F-15 code-keyed code, with
  `org` `F` and a non-null `exhibit_family`.

`root/lake/parquet/jbooks/` holds two parquet files, built from `source_rows` plus `extra_rows`:
- `budget_lines.parquet`, with columns `exhibit, fiscal_year (VARCHAR), account, account_title, organization,
  budget_activity, budget_activity_title, pe_bli, title, amount_type, amount_thousands (DOUBLE), source_sheet,
  source_cells, source_document_id`;
- `documents.parquet` (`id, sha256, source_url, downloaded_at`), one document per distinct (`sha256`,
  `official_url`, `retrieved_at`).

`root/site/` holds:
- `manifest.json` = `{"built_at": <fixture retrieved_at>, "citations": {}, "datasets": {"budget_lines_decade": 0},
  "json_sidecars": 0, "schema_version": 1}`;
- `json/citations.json` = the fixture `registry`, plus `NARRATIVE` under `e7d5bcfb4a30f458`, plus a
  `jbook_narrative` stub under each of the five other F-15 `fact:` ids;
- `citations/citations.parquet` with the same fact ids, in the 27 live columns `fact_id, kind, units, amount_text,
  page_number, x0, x1, top_pt, bottom_pt, page_width, page_height, resolution, sheet, cells, amount_thousands,
  sha256, hosted_pdf_url, official_url, xml_path, retrieved_at, formula, inputs, query_body, recorded_value, pe_bli,
  scenario, amount_type`;
- `data/budget_lines.parquet` (`fact_id` = `current_fact_ids`);
- `data/budget_lines_decade.parquet`, empty, in the 16 live columns `fact_id, exhibit, fiscal_year, account,
  account_title, organization, budget_activity, budget_activity_title, pe_bli, title, amount_type,
  amount_thousands, units, document_sha256, source_sheet, source_cells`;
- `json/site_meta.json` = `{"counts": {"citations": 0}, "datasets": {"budget_lines_decade": 0}}`;
- `json/datasets.json` = `{"datasets": [{"name": "budget_lines_decade", "row_count": 0, "bytes": 0}]}`;
- `json/program_details/{code}.json` = `{}` for the six code-keyed codes.

**The `stubbed` fixture** monkeypatches three names on `platform_family_history`:
- `build_workbook_previews` returns the fixture `previews` for F-15 leaves, and a one-row preview built from the
  citation's sheet, cells and amount for a `b-1` leaf (code `B00100`);
- `open_lake` returns an object with `close()`;
- `check_lake` is a spy that records `(families, site_dir)` and returns `LakeReport([], [], [])`.

**`B1`** = `replace(F15, platform_family="b-1", short_name="B-1", history_dataset="b1_funding_history",
program_notes={}, review_guard=ReviewGuard(("P-1", "R-1"), ("B-1B",)), headline=Headline("cumulative_actuals",
2024, 2024), on_partial_corpus="skip", era_lines=(), members=(_member("P-1:3010F:AF:B00100", "B-1B",
family="b-1", valid=(2024, 2026), order=1, page_slug=""),))`. Task 4's `_member` gives it `evidence=()`.
- `B1_ROW` is its one PB2026 `fy_2024_actuals` row: amount 5, cells `J5`, sha `"b" * 64`, official url
  `https://comptroller.war.gov/Portals/45/Documents/defbudget/fy2026/p1_display.xlsx`.
- `B1_SERIES` is the matching `fct_decade_series` row.

`_tree(root) -> dict[str, str]` maps each relative path to its sha256. `_rows(path) -> list[tuple]` is
`duckdb.connect().execute("select * from read_parquet(?) order by fact_id", [str(path)]).fetchall()`. `PIN` is
`tests/fixtures/f15/history.sha256`'s value (`d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f`).

```python
def test_post_pass_on_the_v5_fixture_writes_the_pinned_history_and_the_index(tmp_path, stubbed):
    duckdb_path, out = _v5_export(tmp_path)
    result = export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=load_registry())
    assert hashlib.sha256((out / "json/f15_funding_history.json").read_bytes()).hexdigest() == PIN
    assert hashlib.sha256((out / INDEX_PATH).read_bytes()).hexdigest() == \
        "3657d3bd36fa8f344cf2c299714dacb11fe227100cd1ff0c3d3d22f6734f1945"
    assert result["families"] == {"f-15": {"annual_points": 30, "source_facts": 207, "added_citations": 208,
                                           "cumulative_actuals_thousands": 17043321.0}}
    assert result["citations"] == 177 + 6 + 208
    assert stubbed.check_lake_calls == [(["f-15"], out)]
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["f15_funding_history"] == {"annual_points": 30, "source_facts": 207, "start_fy": 2015, "end_fy": 2026}
    assert result["json_files"] == manifest["json_sidecars"] == len(list((out / "json").rglob("*.json")))


def test_full_pass_differs_from_the_facade_path_only_by_index_and_json_sidecars(tmp_path, stubbed):
    from govbudget import f15_funding_history as facade
    db_a, out_a = _v5_export(tmp_path / "a")
    db_b, out_b = _v5_export(tmp_path / "b")
    flat = facade.export_f15_funding_history(duckdb_path=db_a, out_dir=out_a)
    full = export_family_histories(duckdb_path=db_b, out_dir=out_b, registry=load_registry())
    assert set(flat) == {"annual_points", "source_facts", "added_citations", "citations", "json_files",
                         "cumulative_actuals_thousands"}
    assert full["json_files"] == flat["json_files"] + 1 and full["citations"] == flat["citations"]
    a, b = _tree(out_a), _tree(out_b)
    assert set(b) - set(a) == {INDEX_PATH} and set(a) <= set(b)
    for path in a:
        if path.endswith(".parquet"):
            assert _rows(out_a / path) == _rows(out_b / path), path   # select * … order by fact_id
        elif path != "manifest.json":
            assert a[path] == b[path], path
    ma, mb = (json.loads((o / "manifest.json").read_text()) for o in (out_a, out_b))
    assert mb.pop("json_sidecars") == ma.pop("json_sidecars") + 1 and ma == mb


def test_nothing_is_written_without_a_full_corpus(tmp_path, stubbed):
    duckdb_path, out = _v5_export(tmp_path, drop_series={"0207171F"})
    before = _tree(out)
    assert export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=load_registry()) is None
    assert _tree(out) == before and not (out / "json/families").exists()


def test_a_published_family_skipped_beside_one_that_builds_raises_and_writes_nothing(tmp_path, stubbed):
    duckdb_path, out = _v5_export(tmp_path, extra_rows=[B1_ROW])          # no B1_SERIES: B-1 skips
    before = _tree(out)
    with pytest.raises(RegistryError, match=r"all published families build or none: built \['f-15'\], skipped \['b-1'\]"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=replace(load_registry(), families=(F15, B1)))
    assert _tree(out) == before


def test_two_families_in_one_pass_share_no_leaf_and_leave_f15_bytes_unchanged(tmp_path, stubbed):
    duckdb_path, out = _v5_export(tmp_path, extra_rows=[B1_ROW], extra_series=[B1_SERIES])
    result = export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=replace(load_registry(), families=(F15, B1)))
    assert hashlib.sha256((out / "json/f15_funding_history.json").read_bytes()).hexdigest() == PIN
    assert json.loads((out / "json/b1_funding_history.json").read_text())["family_id"] == "b-1"
    assert [f["platform_family"] for f in json.loads((out / INDEX_PATH).read_text())["families"]] == ["f-15", "b-1"]
    assert set(result["families"]) == {"f-15", "b-1"} and result["families"]["b-1"]["source_facts"] == 1
    assert {"f15_funding_history", "b1_funding_history"} <= set(json.loads((out / "manifest.json").read_text()))


def test_a_leaf_in_two_families_stops_the_pass_before_any_write(tmp_path, stubbed):
    shared = next(m for m in F15.counted if m.code == "0207134F")
    dup = replace(B1, headline=Headline("cumulative_actuals", 2015, 2024),
                  members=(replace(shared, platform_family="b-1", member_order=1),))
    duckdb_path, out = _v5_export(tmp_path)
    before = _tree(out)
    with pytest.raises(RegistryError, match=r"is counted by f-15 and b-1"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=replace(load_registry(), families=(F15, dup)))
    assert _tree(out) == before


def test_the_index_must_list_exactly_the_built_families(tmp_path, stubbed, monkeypatch):
    monkeypatch.setattr(platform_family_history, "index_projection", lambda registry: {"families": [], "schema_version": 1})
    duckdb_path, out = _v5_export(tmp_path)
    before = _tree(out)
    with pytest.raises(RegistryError, match=r"index.json lists \[\] but the pass built \['f-15'\]"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=load_registry())
    assert _tree(out) == before


def test_the_pass_refuses_a_headline_window_unlike_the_registry(tmp_path, stubbed):
    shifted = replace(F15, headline=Headline("cumulative_actuals", 2015, 2023))
    duckdb_path, out = _v5_export(tmp_path)
    with pytest.raises(ValueError, match=r"^F-15 cumulative window FY2015–FY2024 differs from the registry headline FY2015–FY2023$"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=replace(load_registry(), families=(shifted,)))


def test_preview_builds_one_unpublished_family_without_an_index_and_refuses_the_site_dir(tmp_path, stubbed, monkeypatch):
    ratified = replace(B1, status="ratified", published_ruling_id=None)
    registry = replace(load_registry(), families=(F15, ratified))
    duckdb_path, out = _v5_export(tmp_path / "x", extra_rows=[B1_ROW], extra_series=[B1_SERIES])
    export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=registry, families=["b-1"], preview=True)
    assert (out / "json/b1_funding_history.json").is_file()
    assert not (out / INDEX_PATH).exists() and not (out / "json/f15_funding_history.json").exists()
    with pytest.raises(ValueError, match="preview"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=registry, families=["b-1"])
    with pytest.raises(ValueError, match="preview"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=registry, families=["f-15"], preview=True)
    monkeypatch.setattr(config, "SITE_DIR", tmp_path / "x")
    before = _tree(out)
    with pytest.raises(ValueError, match="site dir"):
        export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=registry, families=["b-1"], preview=True)
    assert _tree(out) == before
```

- [ ] **Step 7: Run the post-pass tests to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_family_history.py -q`
Expected: `ImportError: cannot import name 'export_family_histories'` (or `INDEX_PATH`).

- [ ] **Step 8: Implement `export_family_histories` in `src/govbudget/platform_family_history.py`**

Module-level imports, so the tests can monkeypatch them:
- `from govbudget import config`;
- `from govbudget.workbook_cells import build_workbook_previews`;
- `from govbudget.platform_families import RegistryError, check_citations, check_lake, corpus_gate,
  index_projection, open_lake`.

The body is today's `export_f15_funding_history` (`f15_funding_history.py:354-495`), widened in this order. The
order is the plan's decision; every check precedes the first write.

1. **Targets.**
   - `preview=True` needs exactly one id in `families`, whose family is not `published`. `Path(out_dir).resolve()`
     must not be inside `config.SITE_DIR.resolve()`; that raises `ValueError("platform-families: preview refuses an
     out_dir inside the site dir: …")`. Any other preview misuse raises a `ValueError` whose text contains
     "preview".
   - A non-published id without `preview` raises a `ValueError` whose text contains "preview".
   - With `families=None`, the targets are `registry.published()`.
   - With no targets, return None.
2. **Series and identity.** One read-only connection runs today's `fct_decade_series` query (`:363`) and
   `export_site._fetch_program_identity(con)`, then closes. `duckdb.CatalogException` returns None.
3. **Corpus.** Call `corpus_gate(family, frozenset(r["pe_bli"] for r in series))` for each target. If none builds,
   return None. If some build and some skip, raise `RegistryError([f"platform-families: platform_families.json:
   all published families build or none: built {built_ids}, skipped {skipped_ids}"])` (D6).
4. **Stage 2.** Open `lake = open_lake(duckdb_path)`. For each built family, run `check_lake(registry, lake=lake,
   site_dir=out_dir, families=[pf]).raise_if_failed()`. Close the lake in a `finally`.
5. **Sources.** Resolve the staged parquet as at `:373-376`; a miss raises `ValueError("platform family history
   requires the workbook source lake")`. Read the source rows with today's SQL `:379-386`, unchanged:
   `scripts/era/capture_f15_fixtures.py`'s `SOURCE_SQL` mirrors it. Then read the manifest, `current_fact_ids`
   and `json/citations.json` (`running`).
6. **Grammar registry.** It is `registry`. Under `preview` it is a copy where the previewed family's `status` is
   `"published"`, so its formulas pass `additive_budget_formula` (the grammar admits published families only).
7. **Each built family, in JSON order:**
   - `build_history`; a None payload counts as a skip for step 3's rule;
   - `check_headline`;
   - the previews, with today's count check and `{short_name}` text;
   - `build_program_matrix(..., existing_citations=running)`;
   - today's recompute `:424-437`, with `{short_name}` in its messages;
   - `check_citations(family, registry=grammar_registry, citations=running, minted=<this family's additions>,
     identity=identity, site_dir=out_dir, claimed=claimed)`, with one `claimed` dict for the pass. Any line raises
     `RegistryError(lines)`;
   - then queue the citation rows whose fid is not in `running` (and add them to `running`), the decade rows not
     already in `data/budget_lines_decade.parquet`, the absent breakdowns (`:403`) and the previews.
8. **Index (full pass only: `families is None and not preview`).** `index = index_projection(registry)`.
   `[f["platform_family"] for f in index["families"]]` must equal the built ids, in order (stage-3 item 8);
   otherwise raise `RegistryError([f"platform-families: {INDEX_PATH}: index.json lists {listed} but the pass built
   {built}"])`. Stage `INDEX_PATH` = `_json_bytes(index)`. The facade path and previews never write the index.
9. **Stage and replace** exactly as `:438-494`, with one `tempfile.TemporaryDirectory(prefix=".family-history-",
   dir=out_dir)` for all families:
   - one append to each of the citations parquet and the decade parquet;
   - the population check, as `"citation JSON/parquet population mismatch"`;
   - `json/citations.json`, and each `family.history_path` = `_json_bytes(payload)`;
   - the cite shards over the prefixes of every family's additions, the workbook-cells shards over every preview,
     and the breakdowns;
   - in `manifest.json`: the citations counter, `datasets.budget_lines_decade`, `manifest[family.history_dataset] =
     {annual_points, source_facts, start_fy, end_fy}` per family, and `json_sidecars` by today's formula `:476`
     (the new index counts +1);
   - `json/site_meta.json` and `json/datasets.json`;
   - the unchanged replace loop.
10. **Return** `{"citations": citation_count, "json_files": manifest["json_sidecars"], "families": {pf:
    {"annual_points", "source_facts", "added_citations" (this family's new rows), "cumulative_actuals_thousands"}}}`.

- [ ] **Step 9: Rewire the facade, the call site and the retired script**

- `src/govbudget/f15_funding_history.py:347-497`: `export_f15_funding_history(*, duckdb_path, out_dir)` calls
  `export_family_histories(duckdb_path=…, out_dir=…, registry=platform_families.load_registry(platform_families.DEFAULT_PATHS),
  families=["f-15"])`. It returns None for None; otherwise the flat dict `annual_points`, `source_facts`,
  `added_citations` (from `families["f-15"]`), `citations`, `json_files` and `cumulative_actuals_thousands`.
- `src/govbudget/export_site.py:3932-3938` (the call site quoted in the Task 5 header): replace the import and call
  with `from govbudget.platform_families import load_registry`, `from govbudget.platform_family_history import
  export_family_histories` and `family_history = export_family_histories(duckdb_path=duckdb_path, out_dir=out_dir,
  registry=load_registry())`. Keep the comment, reworded to "Family histories (every published registry family) are a
  bounded additive projection…". The return block `:3948-3959` is unchanged.
- From `GovBudget/`: `git rm -q scripts/export_f15_funding_history.py` (it stays staged for Step 13's commit).

- [ ] **Step 10: Run the Task 5 tests, the frozen F-15 tests and the export suites**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_family_history.py tests/test_platform_families_loader.py tests/test_f15_registry_parity.py -q`
Expected: no failures; `tests/test_platform_family_history.py` passes 22 (13 + 9).

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_funding_history.py tests/test_f15_era_identity.py tests/test_capture_f15_fixtures.py tests/test_verify_era_map.py tests/test_verify_era_map_def.py tests/test_verify_era_map_gh.py tests/test_export_era_line_map.py tests/test_era_fact_stability.py tests/test_budget_pdf_export_workflow.py -q`
Expected: `164 passed`.

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_site_pg.py tests/jbooks/test_export_site_5f.py tests/test_collision_slugs.py tests/jbooks/test_export_basis.py -q`
Expected: `144 passed`, the count collected at `b30134c4` and at `b6c9a8d9`. Re-measured 2026-10-21: all 144 pass
on a clean `git archive` of `9acf0c78` and of `b6c9a8d9`, on a quiet 55432 cluster. Their fixture warehouses carry no full F-15 corpus,
so the post-pass returns None and their `json_files` stay as they are. Round 2's `_require_link_award_keys` raises
only where a warehouse has the award lake. None of these four files (or `tests/conftest.py`, `tests/jbooks/`) creates
`fct_award_transactions`, so the guard does not touch them. The link fix gave its award-lake fixtures a
`link_award_keys` view instead (`tests/link_award_keys_fixture.py`).

- [ ] **Step 11: Stage 3 on the real F-15, read-only, against fam2**

The snapshot is exempt from the SAM window. If leaf expansion or any other item fires here, **stop and report to
the controller**. Never weaken the check, and never change F-15 bytes (§9.3).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - "$GOVBUDGET_PROOFS/fam2" <<'EOF'
import json, sys
from pathlib import Path
import duckdb
from govbudget.export_site import _fetch_program_identity
from govbudget.platform_families import check_citations, load_registry
fam2 = Path(sys.argv[1]); site = fam2 / "site"
registry = load_registry(); f15 = registry["f-15"]
citations = json.loads((site / "json/citations.json").read_text())
history = json.loads((site / f15.history_path).read_text())
ids = {history["cumulative"]["fact_id"]} | {p["fact_id"] for p in history["points"]}
ids |= {c["fact_id"] for p in history["points"] for c in p["components"] + p["program_cells"]}
con = duckdb.connect(str(fam2 / "duckdb/govbudget.duckdb"), read_only=True)
identity = _fetch_program_identity(con); con.close()
lines = check_citations(f15, registry=registry, citations=citations, minted={f: citations[f] for f in ids},
                        identity=identity, site_dir=site, claimed={})
print(f"stage-3 f-15 on fam2: {len(lines)} failures over {len(ids)} facts", *lines, sep="\n")
EOF
```

Expected: `stage-3 f-15 on fam2: 0 failures over 276 facts`. The 276 are 207 leaves, 30 annual totals, 1
cumulative and 38 multi-input cells. The same count is pinned in
`tests/test_budget_pdf_receipts.py::test_shipped_f15_evidence_preserves_all_default_and_historical_cells`.
Measured on the live export on 2026-10-21 with an equivalent script: 0 duplicate leaves over the 31 totals and 38
derived cells; all six `fact:` refs resolve; `dim_programs` has rows for the six code-keyed codes and none for
F0150P or F015E0.

- [ ] **Step 12: Lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uvx --offline ruff check --isolated --select F,E9 src/govbudget/platform_families.py src/govbudget/platform_family_history.py src/govbudget/f15_funding_history.py; uvx --offline ruff check --isolated --select F,E9 src/govbudget/export_site.py | tail -1`
Expected: `All checks passed!`, then `Found 10 errors.` (the W1 baseline).

- [ ] **Step 13: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_family_history.py GovBudget/src/govbudget/f15_funding_history.py GovBudget/src/govbudget/export_site.py GovBudget/tests/test_platform_family_history.py && git status --short -- GovBudget/scripts/export_f15_funding_history.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): the export runs every published family through one post-pass and writes json/families/index.json (piece 2 Task 5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7a: `platform-families check`, `verify-families` and the assembly

**Spec:** §8.3 (`check [--strict]`), §9.2 (where stage 2 runs; a draft family's guard matches count as undecided), §12, §13 (the `verify-families` legs, the assembly), §5.3 and [FU §6] (exit codes). D9 (leak needles), D12 (lake flags) and Review Focus 5.

**Files:**
- Create: `src/govbudget/verify_families.py`
- Create: `tests/platform_families_helpers.py`. These are the shared fixtures for Tasks 7a–7d. pytest puts `tests/` on `sys.path`, so they import as `from platform_families_helpers import …`, the way `jbooks.era_map_fixtures` does.
- Create: `tests/test_verify_families.py`
- Create: `tests/test_platform_families_cli.py` (the `check` cases; Tasks 7b–7d append)
- Modify: `src/govbudget/cli.py`. Add `cmd_verify_families` after `cmd_verify_era_map` (:2469-2487). Add `cmd_platform_families` and `_cmd_platform_families` before `def cmd_refresh` (:3163). Add the `verify-families` parser after `vera.set_defaults(func=cmd_verify_era_map)` (:3460). Add the `platform-families` parser after `em.set_defaults(func=cmd_era_map)` (:3625).
- Modify: `src/govbudget/verify_phase5.py`: the docstring's assembly paragraph (:30-42), and the comment, `_ASSEMBLY_PHASES` and `_VERDICT_RE` (:130-158)
- Modify: `tests/test_verify_phase5.py:733-800`

**Measured (read-only, outside :12–:22, re-measured 2026-10-21):**
- `tests/test_verify_phase5.py`: 66 collected, 66 passed; `-k "assembly or verdict"` selects 19. W1 (`--output-format concise`): `cli.py` 5, `verify_phase5.py` 2.
- `data/site` (the `1256ec35`-era export, before the link fix's release): 36,038 `*.json` files (413,434,695 B); none contains `f35_funding_history`, `f-35|` or `reviewed F-35 members`. `citations/citations.parquet`: 143,893 rows, 27 columns, 19 VARCHAR, no `dataset` column; `reviewed F-15 members` appears in 30 rows, `f15_funding_history` and `f-15|` in none.
  - The link fix's release export (A's, live when Step 9 runs under D1) differs in its totals. These are the link fix's own measurements, which its release re-measures:
    - Its release runbook (`/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2/link-fix/release/runbook.md`) measured 79 retired citation facts at round 2 (143,893 → 143,814): the 41 withdrawn links; 3 district receipts, the IN-07 F-35 receipt `44ee093c2bab2ea8` among them; PA-02's 16 district facts; 0549's 3 concentration facts; and 16 feed facts.
    - It also measured the files `flows/0549.json`, `flows/C03200.json` and `districts/PA-02.json` leaving.
    - Round 3 retires the 10 F03500 link facts more (fix-report §R3-4), 89 in all.
  - It changes no budget figure of the F-15 or the F-35, no citations column, and none of the 30 `reviewed F-15 members` rows. It moves only award-link surfaces. Among them are `flows/ATA000.json`, /district/IN-07/ and the `programs.json` concentration figures, including, after round 3, F03500's all-basis concentration.
  - Nothing below pins the file or row totals.
- `site/node_modules`: typescript 5.9.3, vitest 3.2.6; vitest's default include also runs `site/scripts/gates/__tests__/*.test.mjs`.

**Interfaces:**
- **Consumes.**
  - I-REG: `DEFAULT_PATHS`, `RegistryPaths`, `load_registry`, `RegistryError` (`.errors`), `Registry` (`families`, `rulings`, `published()`, `__getitem__`, `doc`), `Family` (`platform_family`, `short_name`, `history_dataset`, `status`, `members`, `era_lines`, `counted`), `open_lake(duckdb_path) -> LakeReader`, `LakeReader.close()`, `check_lake(registry, *, lake, site_dir, families=None) -> LakeReport(failures, undecided, stale)`, `check_citations(family, *, registry, citations, minted, identity, site_dir, claimed=None) -> list[str]` (Task 5, R10) and `index_projection(registry) -> dict`.
  - I-FACADE: `_json_bytes`.
  - `export_site._fetch_program_identity(con) -> _ProgramIdentity`.
  - `proof.SAM_WINDOW_MINUTES` (`range(15, 21)`) and `proof._sam_window_touched(start, end) -> bool`. Import them; never copy them.
- **Produces.**
  - In `verify_families`:
    - `LEGS = ("a", "b", "c")` and `LEG_NAMES = {"a": "registry", "b": "lake", "c": "export"}`;
    - `run_verify_families(*, site_dir: Path, duckdb_path: Path, legs: str = "abc", registry: Registry | None = None) -> dict`, which returns `{"legs": {leg: {"ok": bool, "summary": str, "failures": list[str]}}, "verdict": "PASS" | "FAIL"}`;
    - `format_report(out: dict) -> list[str]`;
    - `scan_leaks(site_dir: Path, registry: Registry) -> tuple[list[str], int]`, which returns the failures and the number of files scanned;
    - `sam_guard(duckdb_path: Path, *, start: datetime, end: datetime | None = None) -> None` and `_now() -> datetime`. Tasks 7b–7d call both.
  - In the CLI: `cmd_platform_families(args)` wraps `_cmd_platform_families(args)`. Tasks 7b–7d add one branch each to the second. Also `cmd_verify_families(args)`.
  - The `platform-families` parser (`dest="pf_action"`) with all six actions and their D12 flags, so Tasks 7b–7d add no parser code.
  - `tests/platform_families_helpers.py`, listed in Step 1.

- [ ] **Step 1: Write the shared fixtures `tests/platform_families_helpers.py`**

These are the exact signatures. The data below is fixed by this plan; the bodies are the implementer's.

```python
def f15_registry(tmp_path: Path) -> reg.RegistryPaths:
    """The committed registry's F-15 entries only: family f-15, ruling R-DEC-FAM-F15-SEED,
    its 8 member rows and its 31 era lines. They are written with reg.write_registry under
    tmp_path/"data-seeds". Counts stay fixed after Tasks 8a/8b add the F-35 to the
    committed files."""

def add_family(paths, family: dict, *, sources=(), members=(), era_lines=(), rulings=()) -> None:
    """Add a family object (plus its sources, member rows, era rows and rulings) to the
    registry at `paths`, through reg.write_registry. Replace-by-id, like ratified_f35: a
    family with the same platform_family is replaced in place (keeping its index in
    families[]), and so is a source with the same source_id, a ruling with the same
    ruling_id, a member row with the same member_row_id and an era row with the same
    (platform_family, edition, era_key). Anything new is appended. cli_env has already
    added DRAFT_F35, so a test that calls add_family for f-35 again replaces that draft
    rather than adding a second f-35, which stage 1 would refuse as a duplicate (rule 2)."""

def add_source(paths, source: dict) -> None:
    """Add one sources[] entry to the registry at `paths`, through reg.write_registry,
    replacing the entry with the same source_id in place (else appending): MSAR | {"bytes": 1}
    replaces cli_env's MSAR instead of duplicating msar-pb2027 (rule 7)."""
def ratified_f35(paths) -> None:
    """Make f-35 ratified at `paths` through reg.write_registry, replacing any f-35 family in
    place (cli_env has added the draft) and adding MSAR to sources only when absent:
    DRAFT_F35 with status "ratified"; ruling R-DEC-FAM-F35-B1 (kind batch, decided_by owner,
    decided_on 2026-10-22, owner_reply "approved", spec "docs/x.md#b1", text "Ratifies the
    f-35 rows.", seed_basis False); one fully measured member row over MEMBER_COLUMNS:
    F35_PREFILL[0] without "reason", plus member_row_id "f-35|P-1:3010F:AF:ATA000|2017-2026",
    platform_family "f-35", MEASURES["P-1:3010F:AF:ATA000"]'s lake columns (titles_seen
    "2024: F-35; 2025: F-35; 2026: F-35", budget_activities "01", drift_sha256 "a"*64) and
    decided_by "owner", ruling_id "R-DEC-FAM-F35-B1", decided_on "2026-10-22"; and that
    measure's one era line (era_line(...).as_row()). reg.load_registry(paths) loads the
    result with no error, so a caller's refusal is the only one raised."""
def write_prefill(tmp_path, rows) -> tuple[Path, Path]:
    """family.json = {"family": DRAFT_F35 minus "status", "sources": [MSAR]} and rows.csv
    under reg.PREFILL_COLUMNS (blank where a row omits a column)."""
def measure(member_id, *, drift, actuals_k=None, titles=(), era_lines=()) -> reg.MemberMeasure:
    """budget_activities=("01",), editions = the titles' editions, headline_actuals_k = Decimal(actuals_k) or None."""
def era_line(member_id, edition, era_key, ba, title, decision_id) -> reg.EraLine:
    """EraLine(platform_family=member's family, member_id, edition, era_key, budget_activity, filed_title, decision_id)."""
class FakeLake:  # program_series(code) -> series.get(code, {}); close() sets .closed
    def __init__(self, series: dict[str, dict[tuple[int, str], Decimal]] | None = None): ...
F15_ORDER = ["R-1:3600F:AF:0207134F", "R-1:3600F:AF:0207146F", "R-1:3600F:AF:0207171F", "P-1:3010F:AF:F01500",
             "P-1:3010F:AF:F015EX", "P-1:3010F:AF:F15EWS", "P-1:3010F:AF:F0150P", "P-1:3010F:AF:F015E0"]  # §7.6
def fake_export(points: list[tuple[int, str, int, str, dict[str, str]]]):
    """Stand-in for platform_family_history.export_family_histories. Each point is
    (fy, kind, edition, total_k, {member_id: cell_k}). The callable records each call's
    kwargs in .calls, then writes out_dir/json/<history_dataset>.json for families[0]:
    family_id, programs [{"id", "code"} per counted member], points (fy, kind, edition,
    amount_thousands, program_cells [{program_id, amount_thousands}]) and cumulative
    (amount_thousands = the sum of the actuals totals). It returns {"json_files": 1}."""
def site_tree(tmp_path, *, formulas=(), citations=None) -> Path:
    """tmp_path/"site" holding manifest.json {"built_at": "2026-10-21T00:00:00Z"},
    json/citations.json (citations or {}), and citations/citations.parquet with VARCHAR
    columns fact_id, kind, formula, inputs, query_body (one row per formula, written with
    DuckDB COPY)."""
```

This is the data (exact values):

```python
MSAR = {"source_id": "msar-pb2027", "title": "DoD MSAR for the FY2027 budget, effective 21 April 2026",
        "publisher": "Department of Defense", "url": "https://www.esd.whs.mil/", "as_of": "2026-04-21",
        "sha256": "063345e4a46f7d58cf89356389fb36986e5a0f8c06c716030ead49932e8dca50", "bytes": 1298631,
        "archived": False, "tier": "G", "verified_by": []}
DRAFT_F35 = {  # §7.2's F-35 column; keys in §7.2 table order
    "platform_family": "f-35", "status": "draft", "short_name": "F-35", "history_dataset": "f35_funding_history",
    "on_partial_corpus": "raise", "headline": {"measure": "cumulative_actuals", "first_fy": 2015, "last_fy": 2024},
    "scope_note": "Draft scope note for the B1 page.", "coverage_notes": [],
    "review_guard": {"exhibits": ["P-1", "R-1"], "title_substrings": ["F-35", "F35", "JSF", "JOINT STRIKE", "F135", "LIGHTNING"]},
    "program_notes": {}, "variants": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
    "program_tags": [{"tag": "F-35", "mdap_code": "198"}],
    "purpose_tags": ["production", "modifications", "sdd", "block4", "usaf_squadrons"],
    "caveat_ids": ["classified", "construction", "operating_and_support", "spares", "foreign", "cr_years", "nominal_dollars"],
    "exclusions": [], "aliases": [], "contract_routes": None, "official_estimates": None, "art": None}
```

`F35_PREFILL` holds four rows. Every column a row does not name is blank.

| member_id | role / verdict | approp. | valid | cov. from | order | tags (program / purpose) | purpose | variants / scope | services / paying | other non-blank |
|---|---|---|---|---|---|---|---|---|---|---|
| `P-1:3010F:AF:ATA000` | counted / approved | procurement | 2017–2026 | 2017 | 1 | F-35 / production | buy | A / variant | USAF / AF | display_title `F-35`, page_slug `ATA000`, era_decision_ids `ATA000\|3010F\|\|2017-2023`, evidence `era:ATA000\|3010F\|\|2017-2023;src:msar-pb2027#p25`, reason `MDAP 198 on the P-40` |
| `R-1:3600F:AF:0604800F` | counted / approved | rdte | 2017–2023 | 2017 | 2 | F-35 / sdd | develop | A;B;C / shared | USAF;USN;USMC / AF | display_title `F-35 EMD`, page_slug `0604800F`, scope_note `Development shared by A, B and C, counted by paying service.`, evidence `src:msar-pb2027`, reason `MSAR funding sources` |
| `P-1:3020F:AF:JSM000` | context / approved | procurement | 2022–2026 | — | — | — | — | — | — | display_title `Joint Strike Missile`, scope_note `A missile the F-35 carries, not the aircraft; never summed.`, evidence `src:msar-pb2027`, reason `review-guard match JOINT STRIKE; not counted` |
| `R-1:3600F:AF:0207268F` | project_slice / deferred | rdte | 2017–2026 | — | — | — | — | — | — | project_number `675365`, display_title `F135 CIP (project 675365)`, evidence `src:msar-pb2027`, reason `waits for the project-slice pilot` |

The exhibit, account, organization and code come from the member_id.

`MEASURES` (keyed by member_id):

| member_id | drift | actuals_k | titles | era_lines |
|---|---|---|---|---|
| ATA000 | `"a"*64` | `"53368300.000"` | `((2024,"F-35"),(2025,"F-35"),(2026,"F-35"))` | `era_line("P-1:3010F:AF:ATA000", 2018, "3010F-AF-L1", "01", "F-35", "ATA000\|3010F\|\|2017-2023")` |
| 0604800F | `"b"*64` | `"1939500.000"` | `((2023,"F-35 EMD"),)` | — |
| JSM000 | `"c"*64` | `"373500.000"` | `((2026,"Joint Strike Missile"),)` | — |
| 0207268F | `"d"*64` | `None` | `((2026,"F-35 Squadrons"),)` | — |

`B1_REF` holds the two counted lines at FY2015 (actuals), FY2025 (enacted) and FY2026 (request), in $M:

```python
B1_REF = {"lines": {"ATA000": {"2015": 4044.7, "2025": 4972.5, "2026": 4086.7},
                    "0604800F": {"2015": 566.9, "2025": None, "2026": None}},
          "totals": {"2015": 4611.6, "2025": 4972.5, "2026": 4086.7},
          "cumulative": 4611.6, "fy2025_enacted": 4972.5, "fy2026_request": 4086.7}
B1_POINTS = [(2015, "actuals", 2017, "4611600.000", {"P-1:3010F:AF:ATA000": "4044700.000", "R-1:3600F:AF:0604800F": "566900.000"}),
             (2025, "enacted", 2026, "4972500.000", {"P-1:3010F:AF:ATA000": "4972500.000"}),
             (2026, "request", 2026, "4086700.000", {"P-1:3010F:AF:ATA000": "4086700.000"})]
B1_MART = {"ATA000": {(2015, "actuals"): Decimal("4044700"), (2025, "enacted"): Decimal("4972500"), (2026, "request"): Decimal("4086700")},
           "0604800F": {(2015, "actuals"): Decimal("566900")}}
```

- [ ] **Step 2: Write the failing `verify_families` tests in `tests/test_verify_families.py`**

All lake access is stubbed. Two fixtures carry the registry: `paths`, which is `f15_registry(tmp_path)` followed by `add_family(paths, DRAFT_F35, sources=[MSAR])`, and `registry`, which is `reg.load_registry(paths)`. Every test below that names `registry` or `paths` takes those fixtures. The suite calls I-REG through module attributes (`reg.open_lake`, `reg.check_lake`, `reg.check_citations`), so `monkeypatch.setattr(reg, …)` reaches every caller.

```python
def test_leg_a_passes_on_the_f15_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "DEFAULT_PATHS", f15_registry(tmp_path))
    out = vf.run_verify_families(site_dir=tmp_path, duckdb_path=tmp_path / "x.duckdb", legs="a")
    assert out == {"legs": {"a": {"ok": True, "failures": [],
                   "summary": "families=1 published=1 member_rows=8 era_lines=31 rulings=1"}}, "verdict": "PASS"}

def test_leg_a_failure_names_the_file_and_blocks_legs_b_and_c(tmp_path, monkeypatch):
    # rewrite the tmp platform_families.json with "schema_version": 2
    out = vf.run_verify_families(site_dir=..., duckdb_path=..., legs="abc")
    a = out["legs"]["a"]
    assert not a["ok"] and a["failures"][0].startswith("platform-families: ") and "platform_families.json" in a["failures"][0]
    for leg in "bc":
        assert out["legs"][leg] == {"ok": False, "summary": "registry unreadable",
                                    "failures": [f"stage 1 failed (leg a): {len(a['failures'])} error(s)"]}
    assert out["verdict"] == "FAIL"

def test_leg_b_reports_draft_guard_matches_as_undecided_not_failures(registry, monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(reg, "open_lake", lambda p: FakeLake())
    monkeypatch.setattr(reg, "check_lake", lambda r, **kw: seen.update(kw) or reg.LakeReport(
        failures=[], undecided=["f-35: 2026/JSM000 matches the review guard"], stale=[]))
    leg = vf.run_verify_families(site_dir=tmp_path, duckdb_path=tmp_path / "fam2.duckdb", legs="b", registry=registry)["legs"]["b"]
    assert leg == {"ok": True, "summary": "families=2 failures=0 undecided=1 stale=0", "failures": []}
    assert seen.get("families") is None  # stage 2 for every family, draft included

@pytest.mark.parametrize("report,line", [
    (dict(failures=["f-15: P-1 2026/F01500 title 'F-15X' differs from titles_seen 'F-15'"], undecided=[], stale=[]),
     "f-15: P-1 2026/F01500 title 'F-15X' differs from titles_seen 'F-15'"),
    (dict(failures=[], undecided=[], stale=["f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved"]),
     "stale f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved")])
def test_leg_b_fails_on_a_lake_failure_or_a_stale_row(...): assert not leg["ok"] and line in leg["failures"]

LOCK = 'IO Error: Could not set lock on file "/x/govbudget.duckdb": Conflicting lock is held in /usr/bin/python3 (PID 1)'

def test_verify_families_leg_b_lock_is_error_not_fail(registry, paths, tmp_path, monkeypatch, capsys):  # Review Focus 5
    def locked(path): raise duckdb.IOException(LOCK)
    monkeypatch.setattr(reg, "open_lake", locked)
    monkeypatch.setattr(vf, "_now", lambda: datetime.datetime(2026, 10, 21, 1, 30))
    with pytest.raises(duckdb.IOException):
        vf.run_verify_families(site_dir=tmp_path, duckdb_path=tmp_path / "x.duckdb", legs="b", registry=registry)
    monkeypatch.setattr(reg, "DEFAULT_PATHS", paths)
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-families", "--legs", "b"])
    out = capsys.readouterr().out.splitlines()
    assert exit_.value.code == 2
    assert out[-1] == f"verify-families: ERROR — {LOCK}"
    assert "verify-families: FAIL" not in out

def test_legs_b_and_c_refuse_the_live_lake_across_the_sam_window(registry, monkeypatch, tmp_path):
    live = tmp_path / "govbudget.duckdb"; live.touch()
    monkeypatch.setattr(config, "DUCKDB_PATH", live)
    monkeypatch.setattr(vf, "_now", lambda: datetime.datetime(2026, 10, 21, 1, 17))
    monkeypatch.setattr(reg, "open_lake", lambda p: FakeLake())
    monkeypatch.setattr(reg, "check_lake", lambda r, **kw: reg.LakeReport([], [], []))
    with pytest.raises(RuntimeError, match="SAM window"):
        vf.run_verify_families(site_dir=tmp_path, duckdb_path=live, legs="b", registry=registry)
    snap = tmp_path / "fam2.duckdb"   # not the live lake: never guarded
    assert vf.run_verify_families(site_dir=tmp_path, duckdb_path=snap, legs="b", registry=registry)["verdict"] == "PASS"
    clone = tmp_path / "fam2-B" / "duckdb" / "govbudget.duckdb"   # config.DUCKDB_PATH inside a proof snapshot tree (R16)
    clone.parent.mkdir(parents=True); clone.touch(); (tmp_path / "fam2-B" / "snapshot.json").write_text("{}")
    monkeypatch.setattr(config, "DUCKDB_PATH", clone)
    assert vf.run_verify_families(site_dir=tmp_path, duckdb_path=clone, legs="b", registry=registry)["verdict"] == "PASS"
```

These are the leg c cases. The fixture `export_site` builds `site_tree(tmp_path, formulas=[ANNUAL_F15], citations={FID: CIT})`.
- `ANNUAL_F15` = `"sum(budget_lines.amount_thousands) for reviewed F-15 members, PB2026, FY2024 actuals; one selected scenario column per workbook line"`.
- `FID` = `"0" * 16`.
- It writes `json/families/index.json` = `_json_bytes(reg.index_projection(registry))`.
- It writes `json/f15_funding_history.json` = `{"family_id": "f-15", "programs": [{"id": m.member_id} for m in registry["f-15"].counted], "points": [], "cumulative": {"fact_id": FID}}`.
- It stubs `reg.check_citations` to a recorder that returns `[]`, and `vf._program_identity` to `lambda p: object()`.

```python
def test_leg_c_passes_on_the_projection_and_a_matching_history(export_site, registry, recorder):
    leg = vf.run_verify_families(site_dir=export_site, duckdb_path=..., legs="c", registry=registry)["legs"]["c"]
    assert leg == {"ok": True, "failures": [], "summary": "published=1 histories=1 stage3=0 leaks=0 files_scanned=4"}
    (family,), kw = recorder.calls[0]
    assert family.platform_family == "f-15" and kw["minted"] == {FID: CIT} and kw["registry"] is registry

@pytest.mark.parametrize("damage,failure", [
    ("rm index", "json/families/index.json is missing"),
    ("index +space", "json/families/index.json differs from index_projection(registry)"),
    ("rm history", "f-15: json/f15_funding_history.json is missing"),
    ("family_id f-16", "f-15: json/f15_funding_history.json family_id is 'f-16', not 'f-15'"),
    ("programs reversed", "f-15: json/f15_funding_history.json programs[].id differ from the counted members in member_order"),
    ("stage 3", "f-15: f-15 program note receipt mismatch: e7d5bcfb4a30f458")])
def test_leg_c_fails_when_the_index_history_or_stage_3_disagrees(...):
    # "stage 3": the check_citations stub returns ["f-15 program note receipt mismatch: e7d5bcfb4a30f458"]
    assert not leg["ok"] and failure in leg["failures"]

@pytest.mark.parametrize("plant,failure", [
    (("json/search_quick.json", '{"d":"f35_funding_history"}'), "leak: 'f35_funding_history' of unpublished f-35 in json/search_quick.json"),
    (("json/f35_funding_history.json", "{}"), "leak: json/f35_funding_history.json of unpublished f-35 exists"),
    (("json/breakdowns/x.json", '{"k":"f-35|2017|2015"}'), "leak: 'f-35|' of unpublished f-35 in json/breakdowns/x.json"),
    ("formula: sum(budget_lines.amount_thousands) for reviewed F-35 members, PB2026, FY2024 actuals",
     "leak: 'reviewed F-35 members' of unpublished f-35 in citations/citations.parquet (1 row(s))")])
def test_leak_scan_finds_each_needle_of_an_unpublished_family(...):
    failures, scanned = vf.scan_leaks(site, registry)
    assert failure in failures

def test_leak_scan_control_fails_when_no_formula_names_a_published_family(tmp_path, registry):
    failures, _ = vf.scan_leaks(site_tree(tmp_path), registry)
    assert failures == ["leak scan control: no citations/citations.parquet formula contains 'reviewed F-15 members'"]

@pytest.mark.parametrize("verdict,code", [("PASS", 0), ("FAIL", 1)])
def test_cli_prints_legs_then_one_verdict_line(monkeypatch, capsys, verdict, code):
    calls = []
    canned = {"legs": {"a": {"ok": verdict == "PASS", "summary": "families=1 published=1 member_rows=8 era_lines=31 rulings=1",
                             "failures": [] if verdict == "PASS" else ["platform-families: x: y"]}}, "verdict": verdict}
    monkeypatch.setattr(vf, "run_verify_families", lambda **kw: calls.append(kw) or canned)
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-families"])
    out = capsys.readouterr().out.splitlines()
    assert exit_.value.code == code and out[-1] == f"verify-families: {verdict}"
    assert out[0] == f"leg a registry: families=1 published=1 member_rows=8 era_lines=31 rulings=1 → {verdict}"
    assert calls == [{"site_dir": config.SITE_DIR, "duckdb_path": config.DUCKDB_PATH, "legs": "abc"}]

def test_cli_refuses_unknown_legs_with_exit_2(capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-families", "--legs", "az"])
    assert exit_.value.code == 2
    assert capsys.readouterr().out.splitlines()[-1] == "verify-families: ERROR — legs must be letters from abc; got 'az'"
```

- [ ] **Step 3: Write the failing `check` tests in `tests/test_platform_families_cli.py` and edit `tests/test_verify_phase5.py`**

The fixture `cli_env` does four things:
- `paths = f15_registry(tmp_path)`, then `add_family(paths, DRAFT_F35, sources=[MSAR])`;
- `monkeypatch.setattr(reg, "DEFAULT_PATHS", paths)` and `monkeypatch.setattr(reg, "REVIEW_ROOT", tmp_path / "research")`;
- `reg.open_lake` → `FakeLake()`;
- `reg.check_lake` → a settable canned `LakeReport`;
- `vf._now` → `datetime.datetime(2026, 10, 21, 1, 30)`. Without it, a run at :15–:20 against the default `--duckdb` would trip the SAM guard and the suite would flake. `test_verify_families_leg_b_lock_is_error_not_fail` pins the same minute.

```python
def test_check_prints_failures_undecided_and_stale(cli_env, capsys):
    cli_env.report = reg.LakeReport(failures=[], undecided=["f-35: 2026/JSM000 matches the review guard"],
                                    stale=["f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved"])
    code = _exit(["platform-families", "check"])
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert "  undecided f-35: 2026/JSM000 matches the review guard" in out
    assert "  stale f-15|P-1:3010F:AF:F01500|2017-2026: drift_sha256 moved" in out
    assert out[-1] == "platform-families check: families=2 failures=0 undecided=1 stale=1"

@pytest.mark.parametrize("which", ["undecided", "stale"])
def test_check_strict_exits_1_on_undecided_or_stale(...): assert _exit(["platform-families", "check", "--strict"]) == 1

def test_check_exits_1_on_a_lake_failure(...):            # failures=["f-15: …"] → "  FAIL f-15: …", exit 1, no --strict
def test_check_exits_1_on_a_stage_1_error_naming_the_file(...):
    # schema_version 2 → every stdout line but the last starts "platform-families: " and names platform_families.json;
    # last line == f"platform-families check: stage 1 failed ({n} error(s))"; exit 1

def test_check_reports_a_duckdb_lock_as_exit_2(cli_env, monkeypatch, capsys):   # Review Focus 5
    def locked(path): raise duckdb.IOException(LOCK)
    monkeypatch.setattr(reg, "open_lake", locked)
    assert _exit(["platform-families", "check"]) == 2
    out, err = capsys.readouterr()
    assert err.strip() == f"platform-families check: ERROR — {LOCK}"
    assert "platform-families check: families=" not in out

def test_check_refuses_the_live_lake_across_the_sam_window(...):
    # config.DUCKDB_PATH = an existing tmp file, vf._now → 01:17, no --duckdb → exit 2, "SAM window" in stderr
```

`_exit(argv)` runs `cli.main(argv)` under `pytest.raises(SystemExit)` and returns the code. `check` always ends in `sys.exit`.

In `tests/test_verify_phase5.py`, replace `test_assembly_phases_end_with_verify_era_map` (:739-744). Its `_ASSEMBLY_PHASES[-1] == "verify-era-map"` turns false once `verify-families` follows:

```python
def test_assembly_phases_end_with_verify_era_map_then_verify_families():
    from govbudget.verify_phase5 import _ASSEMBLY_PHASES

    assert _ASSEMBLY_PHASES[-2:] == ["verify-era-map", "verify-families"]
    assert _ASSEMBLY_PHASES.index("verify-lineage") < _ASSEMBLY_PHASES.index("verify-era-map")
```

After `test_assembly_gate_passes_with_era_map_green` (:792-800), add four tests modelled on the era-map ones:
- `test_verdict_regex_parses_verify_families_pass`, on `"leg c export: published=1 … → PASS\nverify-families: PASS\n"`;
- `test_verdict_regex_parses_verify_families_fail`, on `"  FAIL json/families/index.json is missing\nverify-families: FAIL\n"`;
- `test_assembly_invokes_verify_families_with_no_arguments`, which asserts `["uv", "run", "python", "-m", "govbudget", "verify-families"] in seen`;
- `test_assembly_gate_fails_when_verify_families_fails`, with `_fake_run_factory({"verify-families"})`, `ok is False`, `blocked is False` and the one row's verdict `FAIL`.

- [ ] **Step 4: Run the tests to verify they fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_verify_families.py tests/test_platform_families_cli.py tests/test_verify_phase5.py -q 2>&1 | tail -5
```

Expected:
- the first two files error at collection with `ModuleNotFoundError: No module named 'govbudget.verify_families'`;
- `test_verify_phase5.py` fails exactly the five new or rewritten tests.

- [ ] **Step 5: Implement `src/govbudget/verify_families.py`**

The module docstring is modelled on `verify_era_map.py:1-8`. It names the CLI, the three legs, the last line, the exit codes and the SAM guard.

- `_now() -> datetime.datetime` returns `datetime.datetime.now()`.
- `sam_guard(duckdb_path, *, start, end=None)`:
  - It is a no-op unless `Path(duckdb_path).resolve() == config.DUCKDB_PATH.resolve()` and `Path(duckdb_path).resolve().parents[1] / "snapshot.json"` does not exist: a proof snapshot or its clone is never guarded, even when its `env.sh` makes it `config.DUCKDB_PATH` (R16).
  - Otherwise it raises `RuntimeError(f"refusing at {now:%H:%M} — the live lake was read across the SAM window (the hourly SAM job writes data/parquet/sam at :17); run outside :15-:20")` when `start.minute in proof.SAM_WINDOW_MINUTES` (`end is None`) or when `proof._sam_window_touched(start, end)` holds.
- `_program_identity(duckdb_path) -> export_site._ProgramIdentity` opens DuckDB `read_only=True`, calls `export_site._fetch_program_identity(con)` and closes the connection.
- `leg_a_registry(registry) -> dict`. Its summary is `families={n} published={p} member_rows={m} era_lines={e} rulings={r}`.
- `run_verify_families`:
  - It raises `ValueError(f"legs must be letters from abc; got {legs!r}")` for an empty or unknown `legs`. Legs always run in `a, b, c` order.
  - When `registry` is None, it calls `reg.load_registry(reg.DEFAULT_PATHS)`, reading the attribute at call time.
  - A `RegistryError` makes leg a fail with `e.errors` as its failures. Legs b and c then get the "registry unreadable" result Step 2 pins. A supplied registry passes leg a with the same summary.
  - Before legs b and c, it records `start = _now()` and calls `sam_guard(duckdb_path, start=start)`. After them it calls `sam_guard(duckdb_path, start=start, end=_now())`.
  - Exceptions from `reg.open_lake` and from `_program_identity` (a DuckDB lock) propagate. They never become a leg failure.
- **Leg b.** `lake = reg.open_lake(duckdb_path)`. Then `report = reg.check_lake(registry, lake=lake, site_dir=site_dir)`, with no `families=` keyword, so every family runs. `lake.close()` goes in a `finally`.
  - `ok = not report.failures and not report.stale`. The failures are `report.failures`, then each stale line prefixed `"stale "`.
  - The summary is `families={n} failures={f} undecided={u} stale={s}`. Undecided never fails.
- **Leg c**, against `site_dir`. It collects every failure and never stops early:
  1. `json/families/index.json` must exist, and its bytes must equal `_json_bytes(reg.index_projection(registry))`.
  2. `json/citations.json` must exist. Its absence fails with `json/citations.json is missing`.
  3. For each `registry.published()` family:
     - `json/{history_dataset}.json` exists;
     - `payload["family_id"] == platform_family`;
     - `[p["id"] for p in payload["programs"]] == [m.member_id for m in family.counted]`;
     - `minted` = `{fid: citations[fid]}` for every fact ID the artifact names (`cumulative.fact_id`, `points[].fact_id`, `points[].program_cells[].fact_id`). A fact ID missing from the citations fails with `{pf}: fact {fid} named by json/{hd}.json is not in json/citations.json`.
     - Then `reg.check_citations(family, registry=registry, citations=citations, minted=minted, identity=_program_identity(duckdb_path), site_dir=site_dir, claimed=claimed)`, with one `claimed = {}` for the whole leg (stage-3 item 7 across families, R10). Each returned line is prefixed `f"{pf}: "`.
  4. `scan_leaks(site_dir, registry)`.

  The summary is `published={p} histories={h} stage3={x} leaks={l} files_scanned={n}`. `stage3` counts check_citations lines, `histories` counts the artifacts found and `leaks` counts the scan's failures.
- **`scan_leaks`** checks the non-published families (D9). For each such family the needles are `history_dataset`, `f"{platform_family}|"` and `f"reviewed {short_name} members"`.
  - It reads every `site_dir.rglob("*.json")` file as bytes and tests `needle.encode() in data`.
  - `json/{history_dataset}.json` existing is a failure.
  - The parquet check runs through DuckDB over **every VARCHAR column** of `citations/citations.parquet`, taken from `describe`. D9: the parquet has no `dataset` column. The query is `contains(coalesce(col, ''), ?)`.
  - **The control.** For every published family, `reviewed {short_name} members` must match at least one `formula` row. Otherwise the scan reports itself blind with the Step 2 message. The live export has 30 such rows (re-measured 2026-10-21).
  - It returns `(failures, files_scanned)`. The messages are Step 2's.
- **`format_report`** prints one line per leg, `leg {leg} {LEG_NAMES[leg]}: {summary} → PASS|FAIL`. Under it come the first 25 failures as `  FAIL {failure}`, then `  … and {n} more`, as `verify_era_map.format_report` does.

- [ ] **Step 6: Implement the CLI in `src/govbudget/cli.py`**

**`cmd_verify_families(args)`** follows `cmd_verify_era_map`.
- It calls `verify_families.run_verify_families(site_dir=args.site_dir or config.SITE_DIR, duckdb_path=args.duckdb or config.DUCKDB_PATH, legs=args.legs)` through the module attribute.
- On any `Exception` it prints `verify-families: ERROR — {e}` on stdout and exits 2.
- Otherwise it prints `format_report(out)`, then `verify-families: {verdict}`, and exits `0 if PASS else 1`.
- The parser is `verify-families` with `--legs` (default `"abc"`), `--site-dir` (Path, default None) and `--duckdb` (Path, default None). Its help reads `families piece 2 release gate: registry files, lake (read-only) and export (legs a-c)`.

**`cmd_platform_families(args)`** follows `cmd_proof` (:3182-3197).
- With `tool = f"platform-families {args.pf_action}"`, it calls `_cmd_platform_families(args)` and re-raises `SystemExit`.
- Any other `Exception` prints `f"{tool}: ERROR — {message}"` to stderr and exits 2. `message` is `str(e)`, so a `RegistryError` prints its lines after the prefix.

**The `platform-families` parser** (`dest="pf_action"`, `required=True`). Flags whose default is None are resolved at call time from `config` and `reg`, so the tests' monkeypatches reach them. The CLI always passes `paths=reg.DEFAULT_PATHS`, `review_root=reg.REVIEW_ROOT` and `out_root=platform_family_review.OUT_ROOT`. `platform_family_review` is imported only inside the branches that use it, so the `check` branch runs before Task 7b creates the module.

| action | flags |
|---|---|
| `propose` | `--family`, `--family-json` (Path), `--rows` (Path), `--duckdb`, `--seed-shipped` (choices `["f-15"]`), `--site-dir`, `--decided-on`, `--owner-reply` (Path) |
| `render` | `--family` (req), `--batch` (req), `--duckdb` (Path, req), `--site-dir` (Path, req), `--preview-out` (Path) |
| `answer` | `--family` (req), `--batch` (req), `--answers` (Path, req) |
| `ratify` | `--family` (req), `--batch` (req), `--decided-on` (req), `--duckdb`, `--site-dir` |
| `check` | `--strict`, `--duckdb`, `--site-dir` |
| `preview` | `--family` (req), `--draft`, `--site-dir` (Path, req), `--duckdb` (Path, req), `--out` (Path, req) |

**The `check` branch of `_cmd_platform_families`.** Tasks 7b–7d add the other branches. Until then each one raises `NotImplementedError(f"{args.pf_action} lands in Task 7b/7c/7d")`.
1. `registry = reg.load_registry(reg.DEFAULT_PATHS)`. On a `RegistryError` it prints each of `e.errors`, then `platform-families check: stage 1 failed ({n} error(s))`, and exits 1.
2. `start = verify_families._now()` and `verify_families.sam_guard(duckdb, start=start)`.
3. `lake = reg.open_lake(duckdb)`, then `report = reg.check_lake(registry, lake=lake, site_dir=site_dir)`, closing the lake in a `finally`.
4. `sam_guard(duckdb, start=start, end=_now())`.
5. It prints `  FAIL …`, `  undecided …` and `  stale …`, then `platform-families check: families={n} failures={f} undecided={u} stale={s}`.
6. It exits with `1 if report.failures or (args.strict and (report.undecided or report.stale)) else 0`.

- [ ] **Step 7: Edit `src/govbudget/verify_phase5.py`**

- `_ASSEMBLY_PHASES` (:140-150) gains `"verify-families"` after `"verify-era-map"`.
- `_VERDICT_RE` (:156-158) becomes `re.compile(r"verify-(?:phase\w+|lineage|era-map|families):\s*(PASS|FAIL|BLOCKED)", re.IGNORECASE)`.
- The comment above `_ASSEMBLY_PHASES` (:137-139) and the one above `_VERDICT_RE` (:152-155) each gain one sentence. Here is the first: `verify-families (families piece 2, spec 2026-10-20 §13) joins on the same terms: no arguments, legs a–c (registry files, lake read-only, export plus the leak scan), one final "verify-families: PASS|FAIL" line.`
- The module docstring's item 3 (:30-42) gains `PLUS verify-families (families piece 2: the family registry's stage 1, its stage 2 against the warehouse, and its stage 3, index.json projection and leak scan against the export)` after the verify-era-map clause.

- [ ] **Step 8: Run the tests to verify they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_verify_families.py tests/test_platform_families_cli.py -q 2>&1 | tail -1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_verify_phase5.py -q 2>&1 | tail -1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_verify_phase5.py -q -k "assembly or verdict" 2>&1 | tail -1
```

Expected: `29 passed` (22 + 7), then `70 passed`, then `23 passed, 47 deselected`.

- [ ] **Step 9: Live, read-only: `check` and legs a and b pass; leg c fails closed (Known red window K2)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -m govbudget platform-families check; echo "exit $?"
uv run --project . python -m govbudget verify-families --legs ab; echo "exit $?"
uv run --project . python -m govbudget verify-families --legs c | tail -3; echo "exit ${pipestatus[1]}"
```

Expected:
- `platform-families check: families=1 failures=0 undecided=0 stale=0`, then `exit 0`;
- `leg a registry: families=1 published=1 member_rows=8 era_lines=31 rulings=1 → PASS`, `leg b lake: families=1 failures=0 undecided=0 stale=0 → PASS` and `verify-families: PASS`, then `exit 0`;
- leg c ends `  FAIL json/families/index.json is missing`, then `verify-families: FAIL`, then `exit 1`. That is the only FAIL line, `leaks=0`.

Any other leg-b or leg-c failure is a finding: stop and report it. **K2:** live `verify-families`, and so `verify-phase5`'s assembly, stay red until Task 10a's release export.

- [ ] **Step 10: W1 lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && for f in src/govbudget/verify_families.py src/govbudget/cli.py src/govbudget/verify_phase5.py; do printf "%s: " $f; uvx --offline ruff check --isolated --select F,E9 --output-format concise $f | grep -c '^src/'; done`

Expected: `verify_families.py: 0`, `cli.py: 5`, `verify_phase5.py: 2`.

- [ ] **Step 11: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/verify_families.py GovBudget/src/govbudget/cli.py GovBudget/src/govbudget/verify_phase5.py GovBudget/tests/platform_families_helpers.py GovBudget/tests/test_verify_families.py GovBudget/tests/test_platform_families_cli.py GovBudget/tests/test_verify_phase5.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): platform-families check and verify-families (legs a-c, leak scan) in the release assembly" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7b: `propose` (a draft family plus its review files) and the `--seed-shipped` wrapper

**Spec:** §8.3 (`propose`, `propose --seed-shipped`), §7.2 (`status: draft`), §7.4 (era lines are measured into `review_era_lines.csv`), §7.6 (the seed), §9.1 rule 23 and §19 rows 25 and 27. D11 (serialization) and Review Focus 4 and 5.

**Files:**
- Create: `src/govbudget/platform_family_review.py` (`propose` and its helpers)
- Modify: `src/govbudget/cli.py` (the `propose` branch of `_cmd_platform_families`)
- Modify: `tests/test_platform_families_cli.py` (append)
- Modify: `tests/platform_families_helpers.py`, only if a helper Step 1 of Task 7a fixed needs a fix. Three of this task's tests rely on `add_family` and `add_source` replacing by id (Task 7a Step 1): `test_propose_never_reproposes_reviewed_excluded_or_rejected_rows`, `test_propose_holds_a_lake_change_to_a_ratified_row_for_review` and `test_propose_refuses_a_source_id_that_differs_from_the_shared_list`. If either helper appends instead, `load_registry` refuses a duplicate `f-35` or `msar-pb2027` before `propose`'s own checks run. Fix the helper; never the test. Because the helpers rewrite the registry files, a test that calls one takes its "byte-unchanged" baseline after that call, never from the `proposing` fixture's `before` (Step 1).

**Interfaces:**
- **Consumes.**
  - I-REG: `PREFILL_COLUMNS`, `REVIEW_COLUMNS`, `ERA_LINE_COLUMNS`, `REVIEW_ROOT`, `DEFAULT_PATHS`, `RegistryPaths`, `load_registry`, `parse_registry(doc, members, era_rows, *, era_decisions, paths)`, `registry_texts`, `write_registry`, `RegistryError`, `Member.from_row`, `Member.as_row()`, `Family.headline`, `open_lake`, `measure_member(lake, member, *, headline) -> MemberMeasure`, `seed_shipped_f15(*, constants, duckdb_path, site_dir, decided_on, owner_reply, paths)` and `F15Constants`.
  - `era_map._atomic_write_texts`, `era_map._csv_text`, `era_map.read_seed` and `era_map.default_seed_path`.
  - Task 7a: `verify_families.sam_guard` and `_now`.
  - I-FACADE: `f15_funding_history.{PROGRAMS, MODERN_MEMBERS, ERA_MEMBERS, ERA_PROGRAM_CODES, PROGRAM_NOTES, NOTE_RECEIPTS, SCOPE_NOTE, COVERAGE_NOTES, F15}`.
- **Produces.** In `platform_family_review` (Task 7c consumes the second helper):
  - `OUT_ROOT = config.ROOT / "tmp" / "platform-families"`;
  - `propose(*, platform_family: str, family_json: Path, rows_csv: Path, duckdb_path: Path, paths: RegistryPaths = DEFAULT_PATHS, review_root: Path = REVIEW_ROOT) -> dict`, which returns `{"rows": int, "era_lines": int, "held_for_review": int}`;
  - `review_files(review_root: Path, platform_family: str) -> tuple[Path, Path]`, which returns `(<root>/<pf>/review.csv, <root>/<pf>/review_era_lines.csv)`;
  - `_trial_registry(registry, *, platform_family, rows, era_lines, ruling, paths) -> tuple[dict, list[dict], list[dict], Registry]`, used again by 7c's preview and 7d's ratify;
  - `_era_row(line: EraLine) -> dict[str, str]`;
  - `_era_decisions() -> dict[str, dict[str, str]]`.

  **The `family_json` format** (Task 8a writes it):
  - `{"family": <a §7.2 family object without "status" and without "published_ruling_id">, "sources": [<§7.2 sources[] entries the family cites>]}`;
  - exactly those two keys;
  - UTF-8 with no BOM, and duplicate keys refused.

- [ ] **Step 1: Write the failing `propose` tests (append to `tests/test_platform_families_cli.py`)**

The fixture `proposing` builds on `cli_env`:
- `family_json, rows_csv = write_prefill(tmp_path, F35_PREFILL)`;
- `reg.open_lake` → `FakeLake()`;
- `reg.measure_member` → `lambda lake, member, *, headline: MEASURES[member.member_id]`;
- `db = tmp_path / "fam2.duckdb"`;
- `out_root = tmp_path / "out"`, and `monkeypatch.setattr(review, "OUT_ROOT", out_root)`. The CLI always passes `out_root=review.OUT_ROOT` (Task 7a Step 6), so without this patch a `render`, `answer` or `ratify` run through `cli.main` (Task 7d's lock test and round trip) would read and write the checkout's own `tmp/platform-families/`, where Task 8a puts the owner's B1 page and manifest. Every direct `review.render`, `review.answer` and `review.ratify` call in Tasks 7c–7d passes this same `out_root`;
- `before` = the bytes of the three registry files.

```python
def test_propose_writes_a_draft_family_and_the_review_files(proposing):
    out = review.propose(platform_family="f-35", family_json=fj, rows_csv=rc, duckdb_path=db, paths=paths, review_root=rr)
    assert out == {"rows": 4, "era_lines": 1, "held_for_review": 0}
    registry = reg.load_registry(paths)
    assert registry["f-35"].status == "draft" and registry["f-35"].members == ()
    assert registry.sources["msar-pb2027"].tier == "G"
    rows = _csv(rr / "f-35" / "review.csv")
    assert list(rows[0]) == list(reg.REVIEW_COLUMNS)
    assert [r["member_row_id"] for r in rows] == ["f-35|P-1:3010F:AF:ATA000|2017-2026", "f-35|P-1:3020F:AF:JSM000|2022-2026",
                                                 "f-35|R-1:3600F:AF:0207268F|2017-2026", "f-35|R-1:3600F:AF:0604800F|2017-2023"]
    ata = rows[0]
    assert (ata["titles_seen"], ata["drift_sha256"], ata["headline_actuals_k"]) == ("2024: F-35; 2025: F-35; 2026: F-35", "a" * 64, "53368300.000")
    assert (ata["decided_by"], ata["ruling_id"], ata["decided_on"]) == ("", "", "")
    assert rows[2]["headline_actuals_k"] == ""
    assert _csv(rr / "f-35" / "review_era_lines.csv") == [{"platform_family": "f-35", "member_id": "P-1:3010F:AF:ATA000",
        "edition": "2018", "era_key": "3010F-AF-L1", "budget_activity": "01", "filed_title": "F-35", "decision_id": "ATA000|3010F||2017-2023"}]
    assert paths.members.read_bytes() == before["members"] and paths.era_lines.read_bytes() == before["era_lines"]
```

The other tests, with the assertion each pins:
- `test_propose_refuses_to_overwrite_a_ratified_or_published_family`, parametrized two ways:
  - `"published"` runs `propose` for `f-15` with a family_json written the way `write_prefill` writes it, without `status`: `{"family": {k: v for k, v in DRAFT_F35.items() if k != "status"} | {"platform_family": "f-15", "short_name": "F-15", "history_dataset": "f15_funding_history"}, "sources": [MSAR]}`, so step 1 passes and step 3 refuses;
  - `"ratified"` calls `ratified_f35(paths)` first (a registry that loads cleanly, so step 3's status check is reached).

  It expects `RegistryError` with `"f-15 is published"` / `"f-35 is ratified"` in `str(e)`. The three registry files must be byte-unchanged from their bytes just before `propose` runs (after `ratified_f35`), and `rr/"f-35"` (or `rr/"f-15"`) must not exist.
- `test_propose_replaces_an_earlier_draft_of_the_same_family`. The second run changes `scope_note` to `"Second draft."`. The `families` ids must still be `["f-15", "f-35"]`, the scope note `"Second draft."`, and `review.csv` holds 4 rows.
- `test_propose_never_reproposes_reviewed_excluded_or_rejected_rows`. Beforehand, `add_family` rewrites cli_env's draft in place (replace-by-id) with one member row: JSM000 with `verdict=rejected`. Then `out["rows"] == 3`, and JSM000 is absent from `review.csv`.
- `test_propose_holds_a_lake_change_to_a_ratified_row_for_review`. Beforehand, `add_family` rewrites cli_env's draft in place with ruling `R-DEC-FAM-F35-B1`. The draft carries two approved rows under that ruling: ATA000 with `drift_sha256="0"*64`, and JSM000 carrying exactly the lake columns `MEASURES` gives it (`titles_seen` `2026: Joint Strike Missile`, `budget_activities` `01`, `drift_sha256` `"c"*64`). Then:
  - `out == {"rows": 3, "era_lines": 1, "held_for_review": 1}`;
  - JSM000 is unchanged, so it is not re-proposed;
  - ATA000's `reason` equals `"lake result differs from ratified row f-35|P-1:3010F:AF:ATA000|2017-2026 (drift_sha256) — confirm or keep the ratified row; no silent overturn"`;
  - the members CSV is byte-unchanged from its bytes just before `propose` runs (after `add_family`). The fixture's `before` predates `add_family`'s two member rows, so never compare against it here.
- `test_propose_lists_every_error_at_once_and_writes_nothing`. The prefill puts 0604800F at `member_order` `3` (rule 16) and JSM000 at `purpose` `fly` (rule 11). It expects `len(e.errors) >= 2`, both member_row_ids in `str(e)`, `"review.csv"` in `str(e)`, nothing written and no review directory.
- `test_propose_refuses_a_prefill_header_bom_or_crlf` (Review Focus 4), parametrized as `["header", "bom", "crlf"]`:
  - `header` drops the `reason` column;
  - `bom` prefixes `"\ufeff"` (a UTF-8 BOM);
  - `crlf` rewrites every line ending.

  It expects `RegistryError` with `"rows.csv"` in `str(e)`, and nothing written.
- `test_propose_refuses_a_source_id_that_differs_from_the_shared_list`. Beforehand, `add_source(paths, MSAR | {"bytes": 1})` replaces cli_env's MSAR in place, so the registry loads and step 4's same-id, different-content refusal is the one that fires. It expects `"msar-pb2027"` in `str(e)`, and nothing written: the three registry files equal their bytes just before `propose` runs (after `add_source`, whose `"bytes": 1` the fixture's `before` predates), and `rr/"f-35"` does not exist. It also expects no `duplicate` in `str(e)`: that word is stage 1's rule-7 reason, and step 4's refusal says the content differs.
- `test_propose_and_ratify_write_nothing_on_a_lock`, parametrized as `["propose"]` (Task 7d adds `"ratify"` and its branch). This is Review Focus 5. It takes `proposing` and pytest's `request`, so Task 7d's branch can build its own state on the same fixture.
  - After the state is built, the test patches `reg.open_lake` to raise `duckdb.IOException(LOCK)`.
  - `cli.main(["platform-families", "propose", "--family", "f-35", "--family-json", str(fj), "--rows", str(rc), "--duckdb", str(db)])` exits 2.
  - stderr starts with `platform-families propose: ERROR — ` and contains `Could not set lock on file`.
  - The three registry files are byte-unchanged and `rr/"f-35"` does not exist.
- `test_seed_shipped_wrapper_passes_the_facade_constants`. Here `reg.seed_shipped_f15` is a recorder that raises `reg.RegistryError(["platform-families: platform_families.json: f-15 already in platform_families.json"])`. The command is `propose --seed-shipped f-15 --duckdb D --site-dir S --decided-on 2026-10-21 --owner-reply R`, where R holds `approved, would process with recommendation to approve all\n`. It expects:
  - exit 2;
  - each `F15Constants` field equal to the facade attribute of the same upper-case name;
  - `expected_from == {"0207134F": 2017, "0207171F": 2017, "0207146F": 2021, "F01500": 2024, "F015EX": 2024, "F15EWS": 2024, "F0150P": None, "F015E0": None}`;
  - `decided_on == "2026-10-21"`;
  - `owner_reply` equal to R's text unchanged (the seed strips the one newline, D13);
  - `paths is reg.DEFAULT_PATHS`.
- `test_seed_shipped_wrapper_refuses_once_the_f15_exists`. This uses the real seed. `reg.open_lake` raises `duckdb.IOException(LOCK)`, which proves the one-off refusal comes before any lake read. It expects exit 2, stderr containing `f-15` and `already`, and the three registry files byte-unchanged.
- `test_cli_propose_refuses_mixed_seed_and_family_flags`, parametrized two ways:
  - `["--seed-shipped", "f-15", "--family", "f-35", …]` gives the ERROR line `--seed-shipped takes --duckdb, --site-dir, --decided-on and --owner-reply only`;
  - `["--family", "f-35", "--family-json", fj]` gives `propose needs --family, --family-json and --rows`.

  Both exit 2.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_cli.py -q 2>&1 | tail -3`

Expected: collection fails with `ModuleNotFoundError: No module named 'govbudget.platform_family_review'`.

- [ ] **Step 3: Implement `propose` in `src/govbudget/platform_family_review.py`**

**Imports.** The module imports `from govbudget import config, platform_families as reg, platform_family_history as hist, verify_families as vf` and `from govbudget.jbooks import era_map`. It calls every I-REG and I-HIST function through those module attributes.

**`_trial_registry`.** This is the one place a family under review is made buildable and checkable:
- `doc` = a deep copy of `registry.doc`. The family's `status` is set to `"ratified"`. `ruling` is appended to `rulings`, which stay sorted by `ruling_id`.
- `members`:
  - start from every existing member row (`m.as_row()`);
  - drop the rows of `platform_family` that `rows` replaces by `member_row_id`;
  - add each row of `rows` with `decided_by="owner"`, `ruling_id=ruling["ruling_id"]` and `decided_on=ruling["decided_on"]`, minus `reason` and `headline_actuals_k`;
  - sort by `member_row_id`.
- The era rows are the existing ones plus those of `era_lines` whose `member_id` is an approved counted row of `rows`, sorted by (`platform_family`, `edition`, `era_key`).
- It returns those three plus `reg.parse_registry(doc, members, era_rows, era_decisions=_era_decisions(), paths=paths)`. That call raises `RegistryError` with every stage-1 error.

**`propose`.** Every check runs before the first write, and every error collected is raised as one `RegistryError` whose lines read `platform-families: <file basename>[:<row id>]: <reason>` (R5). Steps 1–5 raise before the lake opens; steps 6–8 raise together after it closes (R12).
1. **Read `family_json`.** The keys must be exactly `{"family", "sources"}`. The file is refused if it has a BOM, or duplicate keys (via `object_pairs_hook`). `family["platform_family"]` must equal `platform_family`. `status` and `published_ruling_id` must be absent.
2. **Read `rows_csv`.** Refuse a BOM, any `\r` and a trailing blank line. The header must equal `reg.PREFILL_COLUMNS`, and field whitespace is kept as read.
3. **Load the registry.** `registry = reg.load_registry(paths)`. An existing family with status `ratified` or `published` refuses (`f"{pf} is {status}; propose writes draft families only"`). An existing draft is replaced in place, keeping its index in `families[]`. A new family is appended.
4. **Merge sources by `source_id`.** A new id is added. An id already present with different content refuses. `sources` stays sorted by `source_id`.
5. **Check the family object as a zero-row draft.** `draft = reg.parse_registry(<doc with the family as status "draft" and the merged sources>, <the existing member rows>, <the existing era rows>, era_decisions=_era_decisions(), paths=paths)` (a draft with zero rows is valid, rule 23). Its errors name `platform_families.json`; `family = draft[pf]` supplies `headline`.
6. **Rows and ids.** Each prefill row gets `member_row_id = f"{pf}|{member_id}|{valid_from}-{valid_to}"`. `existing` = this family's member-CSV rows by `member_row_id`.
   - A prefill row whose existing row is `rejected` or has role `excluded` is dropped.
   - A prefill row whose existing row is `approved` is re-measured in step 7.
   - Each remaining row becomes `reg.Member.from_row(<the row over MEMBER_COLUMNS, lake and ruling columns blank>)`; a `ValueError` becomes an error on `review.csv:<member_row_id>` and that row is not measured.
7. **Measure.** First `start = vf._now()` and `vf.sam_guard(duckdb_path, start=start)`. Then `lake = reg.open_lake(duckdb_path)`. For each `Member`, call `measure = reg.measure_member(lake, member, headline=family.headline)`.
   - The row's `titles_seen`, `budget_activities` and `drift_sha256` come from `dataclasses.replace(member, titles_seen=…, budget_activities=…, drift_sha256=…).as_row()`.
   - `headline_actuals_k = f"{measure.headline_actuals_k:.3f}"`, or blank when that is None.
   - The era lines come from `_era_row` over `measure.era_lines`.
   - An `approved` existing row with the same lake columns is not re-proposed. One whose lake columns differ is kept with `reason` set to `f"lake result differs from ratified row {member_row_id} ({', '.join(changed columns)}) — confirm or keep the ratified row; no silent overturn"`, and counted in `held_for_review`. This follows `era_map._hold_for_review`.
   - `lake.close()` goes in a `finally`. Then `vf.sam_guard(duckdb_path, start=start, end=vf._now())`. A lock exception propagates, with nothing written.
8. **Stage 1 on the measured rows, once.** Call `_trial_registry` with the ruling `{"ruling_id": f"R-DEC-FAM-{FAM}-PROPOSE", "kind": "batch", "platform_family": pf, "decided_by": "owner", "decided_on": "2026-01-01", "owner_reply": "propose trial (never written)", "spec": "", "text": "", "seed_basis": False}` (`{FAM}` is `pf.replace("-", "").upper()`), the measured rows and era lines, and `paths=reg.RegistryPaths(json=paths.json, members=review_csv, era_lines=review_era_lines_csv)`, so errors name the review files. Rule 25 checks the era lines here. Its errors join the list.
9. **Write, in one `era_map._atomic_write_texts` call:** `review.csv` (`REVIEW_COLUMNS`, rows sorted by `member_row_id`, `decided_by`/`ruling_id`/`decided_on` blank) and `review_era_lines.csv` (`ERA_LINE_COLUMNS`, sorted by (`platform_family`, `edition`, `era_key`)), both via `era_map._csv_text`, plus `reg.registry_texts(paths, doc=<doc with the draft family and merged sources>, members=<unchanged>, era_lines=<unchanged>)`. The members and era-lines CSVs are rewritten byte-identical.
10. Return `{"rows": len(review rows), "era_lines": len(review era lines), "held_for_review": n}`.

- [ ] **Step 4: Implement the `propose` branch of `_cmd_platform_families` in `src/govbudget/cli.py`**

- **With `--seed-shipped f-15`:**
  1. Refuse `--family`, `--family-json` and `--rows`. All four of `--duckdb`, `--site-dir`, `--decided-on` and `--owner-reply` are required. Step 1 fixes both messages.
  2. Call `reg.seed_shipped_f15(constants=reg.F15Constants(programs=f15.PROGRAMS, modern_members=f15.MODERN_MEMBERS, era_members=f15.ERA_MEMBERS, era_program_codes=f15.ERA_PROGRAM_CODES, program_notes=f15.PROGRAM_NOTES, note_receipts=f15.NOTE_RECEIPTS, scope_note=f15.SCOPE_NOTE, coverage_notes=f15.COVERAGE_NOTES, expected_from={m.code: m.coverage_expected_from_edition for m in f15.F15.counted}), duckdb_path=args.duckdb, site_dir=args.site_dir, decided_on=args.decided_on, owner_reply=args.owner_reply.read_text(encoding="utf-8"), paths=reg.DEFAULT_PATHS)`. Here `f15` is `govbudget.f15_funding_history`.
  3. Print `platform-families propose: f-15 seeded as R-DEC-FAM-F15-SEED; {members} member row(s), {era_lines} era line(s), {rulings} ruling -> data-seeds/`.
- **Otherwise:**
  1. `--family`, `--family-json` and `--rows` are required.
  2. Call `propose(..., duckdb_path=args.duckdb or config.DUCKDB_PATH, paths=reg.DEFAULT_PATHS, review_root=reg.REVIEW_ROOT)`.
  3. Print `platform-families propose: {pf} draft; {rows} review row(s), {era_lines} era line(s), {held} held for review -> {review_root}/{pf}/`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_cli.py tests/test_verify_families.py -q 2>&1 | tail -1`

Expected: `45 passed` (23 + 22).

- [ ] **Step 6: W1 lint**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && for f in src/govbudget/platform_family_review.py src/govbudget/cli.py; do printf "%s: " $f; uvx --offline ruff check --isolated --select F,E9 --output-format concise $f | grep -c '^src/'; done`

Expected: `platform_family_review.py: 0`, `cli.py: 5`.

- [ ] **Step 7: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_family_review.py GovBudget/src/govbudget/cli.py GovBudget/tests/test_platform_families_cli.py GovBudget/tests/platform_families_helpers.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): platform-families propose writes a draft family and its review files; --seed-shipped wraps the F-15 seed" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7c: `preview`, `compare_reference` and `render` (the batch page)

**Spec:** §8.2 (the page, its order and contents, the preview, "a preview that shows a wrong row blocks the page", "scratch only"), §8.3 (`render` and `preview`), §17 risk 6 and §19 row 26. D10 (artifact paths, `family_sha256`) and Review Focus 3.

**Files:**
- Modify: `src/govbudget/platform_family_review.py`
- Modify: `src/govbudget/cli.py` (the `render` and `preview` branches)
- Modify: `tests/test_platform_families_cli.py` (append)

**Interfaces:**
- **Consumes.**
  - Task 7b's `_trial_registry`, `review_files` and `OUT_ROOT`.
  - I-HIST `export_family_histories(*, duckdb_path, out_dir, registry, families, preview=True) -> dict | None`.
  - I-REG `family_hash(doc, platform_family) -> str`, `open_lake` and `Registry.sources`.
  - `LakeReader.program_series(code: str) -> dict[tuple[int, str], Decimal]`, added by Task 2c (R2). It is `fct_program_decade_series` summed by `program_key = code` under the edition rule: actuals at `edition_year = fy + 2`, enacted at `fy + 1`, request at `fy`.
  - `era_map.BATCH_RE` (`^B[1-9][0-9]*$`) and `era_map._atomic_write_texts`.
- **Produces.**
  - `@dataclass PreviewResult(years: list[dict], cumulative_thousands: Decimal, member_years: dict[tuple[str, int, str], Decimal], out_dir: Path, members: dict[str, str] = field(default_factory=dict))`. Each `years` entry is `{"fy": int, "kind": str, "edition": int, "total_thousands": Decimal}`; `members` maps each counted member's code to its `member_id` (R14), so a reference code the preview never printed still gets its `member_id`.
  - `preview(*, platform_family: str, draft: bool, site_dir: Path, duckdb_path: Path, out: Path, paths: RegistryPaths = DEFAULT_PATHS, review_root: Path = REVIEW_ROOT) -> PreviewResult`.
  - `compare_reference(result: PreviewResult, reference: dict, *, lake) -> list[dict]`. Each difference is `{"fy": int | None, "kind": str, "member_id": str | None, "preview_k": Decimal | None, "reference_m": Decimal | None, "cause": str, "blocks": bool}`.
  - `render(*, platform_family: str, batch: str, duckdb_path: Path, site_dir: Path, review_root: Path = REVIEW_ROOT, out_root: Path = OUT_ROOT, preview_out: Path) -> dict`, which returns `{"page": Path, "manifest": Path, "rows": int, "differences": int}`.
  - `batch_ruling_id(platform_family: str, batch: str) -> str`, for example `R-DEC-FAM-F35-B1`.
  - `CAUSE_PROPOSAL = "proposal row"`, `CAUSE_LAKE = "lake since 2026-10-19"` and `PREVIEW_MARKER = ".platform-families-preview"`.
  - **The manifest** at `out_root/<pf>/B<n>.json`: `{"schema_version": 1, "platform_family", "batch", "rows": [<review.csv rows in page order>], "review_sha256", "review_era_lines_sha256", "family_sha256", "preview": {"years", "cumulative_thousands", "differences"}}`. Decimals are written as strings (thousands `f"{d:.3f}"`, $M `f"{d:.1f}"`, None as `null`). It is serialized `json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"`.
  - **The reference** is read from `review_root/<pf>/reference-<batch lower>.json` (Task 8a writes `reference-b1.json`). Its keys are exactly `lines`, `totals`, `cumulative`, `fy2025_enacted` and `fy2026_request`. A null is an absent value (`—`); `0.0` is a real zero.

- [ ] **Step 1: Write the failing tests (append to `tests/test_platform_families_cli.py`)**

The fixture `rendering` builds on `proposing` and runs `review.propose(...)` once. It also:
- writes `B1_REF` to `rr/"f-35"/"reference-b1.json"`;
- sets `site = site_tree(tmp_path)` and `scratch = tmp_path / "fam2-preview-f-35-B1"`;
- patches `hist.export_family_histories` with `fake_export(B1_POINTS)`;
- patches `reg.open_lake` with `FakeLake(B1_MART)`.

```python
def test_preview_refuses_a_draft_without_the_draft_flag(rendering):
    with pytest.raises(reg.RegistryError, match="--draft"):
        review.preview(platform_family="f-35", draft=False, site_dir=site, duckdb_path=db, out=scratch, paths=paths, review_root=rr)
    assert not scratch.exists()

def test_preview_refuses_out_inside_the_site_dir(rendering, monkeypatch):
    monkeypatch.setattr(config, "SITE_DIR", tmp_path / "live-site")
    with pytest.raises(reg.RegistryError, match="inside config.SITE_DIR"):
        review.preview(..., out=tmp_path / "live-site" / "preview")
    assert not (tmp_path / "live-site").exists()

def test_preview_builds_the_draft_into_a_scratch_clone(rendering):
    before = sorted(p.relative_to(site) for p in site.rglob("*"))
    result = review.preview(platform_family="f-35", draft=True, site_dir=site, duckdb_path=db, out=scratch, paths=paths, review_root=rr)
    assert result.years[0] == {"fy": 2015, "kind": "actuals", "edition": 2017, "total_thousands": Decimal("4611600.000")}
    assert result.cumulative_thousands == Decimal("4611600.000")
    assert result.member_years[("P-1:3010F:AF:ATA000", 2015, "actuals")] == Decimal("4044700.000")
    assert (scratch / review.PREVIEW_MARKER).is_file() and sorted(p.relative_to(site) for p in site.rglob("*")) == before
    (call,) = hist.export_family_histories.calls
    assert call["families"] == ["f-35"] and call["preview"] is True and call["out_dir"] == scratch
    assert call["registry"]["f-35"].status == "ratified"
    assert [m.member_id for m in call["registry"]["f-35"].counted] == ["P-1:3010F:AF:ATA000", "R-1:3600F:AF:0604800F"]

def test_preview_replaces_only_its_own_scratch(rendering):
    scratch.mkdir(); (scratch / "keep.txt").write_text("x")
    with pytest.raises(reg.RegistryError, match="not a preview scratch"):
        review.preview(..., out=scratch)
    shutil.rmtree(scratch); review.preview(..., out=scratch); review.preview(..., out=scratch)  # second run replaces

def test_preview_compares_at_b1_precision(tmp_path):            # Review Focus 3
    ata = "P-1:3010F:AF:ATA000"
    ref = {"lines": {"ATA000": {"2015": 4044.7, "2025": 4972.5, "2026": 4086.7}},
           "totals": {"2015": 4044.7, "2025": 4972.5, "2026": 4086.7}, "cumulative": 4044.7,
           "fy2025_enacted": 4972.5, "fy2026_request": 4086.7}
    def result(k2015):
        years = [(2015, "actuals", 2017, k2015), (2025, "enacted", 2026, "4972500"), (2026, "request", 2026, "4086700")]
        return review.PreviewResult(years=[{"fy": f, "kind": k, "edition": e, "total_thousands": Decimal(t)} for f, k, e, t in years],
                                    cumulative_thousands=Decimal(k2015),
                                    member_years={(ata, f, k): Decimal(t) for f, k, e, t in years}, out_dir=tmp_path)
    lake = FakeLake({"ATA000": {(2015, "actuals"): Decimal("4044700"), (2025, "enacted"): Decimal("4972500"), (2026, "request"): Decimal("4086700")}})
    assert review.compare_reference(result("4044650"), ref, lake=lake) == []       # 4044.65 → 4044.7 only under ROUND_HALF_UP
    diffs = review.compare_reference(result("4044649.999"), ref, lake=lake)
    assert {"fy": 2015, "kind": "actuals", "member_id": ata, "preview_k": Decimal("4044649.999"),
            "reference_m": Decimal("4044.7"), "cause": "proposal row", "blocks": True} in diffs
    assert len(diffs) == 3 and all(d["blocks"] for d in diffs)   # the member, the FY2015 total, the cumulative

def test_preview_keeps_real_zero_distinct_from_absent(tmp_path):  # Review Focus 3
    f40, n10 = "R-1:3600F:AF:0604840F", "R-1:1319N:NAVY:0604810N"
    ref = {"lines": {"0604840F": {"2018": 0.0, "2019": 0.0, "2026": 1182.1}, "0604810N": {"2019": None, "2020": None, "2026": None}},
           "totals": {"2018": 0.0, "2019": 0.0, "2026": 1182.1}, "cumulative": 0.0, "fy2025_enacted": None, "fy2026_request": 1182.1}
    member_years = {(f40, 2019, "actuals"): Decimal("0"), (f40, 2026, "request"): Decimal("1182100"), (n10, 2019, "actuals"): Decimal("0")}
    result = review.PreviewResult(   # years and cumulative agree with ref; 0604840F FY2018 is absent from the preview
        years=[{"fy": 2018, "kind": "actuals", "edition": 2020, "total_thousands": Decimal("0")},
               {"fy": 2019, "kind": "actuals", "edition": 2021, "total_thousands": Decimal("0")},
               {"fy": 2026, "kind": "request", "edition": 2026, "total_thousands": Decimal("1182100")}],
        cumulative_thousands=Decimal("0"), member_years=member_years, out_dir=tmp_path)
    lake = FakeLake({"0604840F": {(2018, "actuals"): Decimal("0"), (2019, "actuals"): Decimal("0"), (2026, "request"): Decimal("1182100")}})
    diffs = {(d["fy"], d["member_id"]): d for d in review.compare_reference(result, ref, lake=lake) if d["member_id"]}
    assert set(diffs) == {(2018, f40), (2019, n10)}
    assert (diffs[(2018, f40)]["preview_k"], diffs[(2018, f40)]["reference_m"]) == (None, Decimal("0.0"))
    assert (diffs[(2019, n10)]["preview_k"], diffs[(2019, n10)]["reference_m"]) == (Decimal("0"), None)
    assert all(d["cause"] == "proposal row" for d in diffs.values())

def test_render_blocks_a_proposal_row_difference_and_shows_lake_drift(rendering, monkeypatch):  # Review Focus 3
    wrong = [(2015, "actuals", 2017, "4611549.999", {"P-1:3010F:AF:ATA000": "4044649.999", "R-1:3600F:AF:0604800F": "566900.000"}), *B1_POINTS[1:]]  # 4044.6 ≠ 4044.7
    monkeypatch.setattr(hist, "export_family_histories", fake_export(wrong))
    with pytest.raises(reg.RegistryError, match="proposal row"):
        review.render(platform_family="f-35", batch="B1", duckdb_path=db, site_dir=site, review_root=rr, out_root=out_root, preview_out=scratch)
    assert not (out_root / "f-35" / "B1.html").exists() and not (out_root / "f-35" / "B1.json").exists()
    drift = [(2015, "actuals", 2017, "4616900.000", {"P-1:3010F:AF:ATA000": "4050000.000", "R-1:3600F:AF:0604800F": "566900.000"}), *B1_POINTS[1:]]
    monkeypatch.setattr(hist, "export_family_histories", fake_export(drift))
    monkeypatch.setattr(reg, "open_lake", lambda p: FakeLake(B1_MART | {"ATA000": B1_MART["ATA000"] | {(2015, "actuals"): Decimal("4050000")}}))
    out = review.render(...)
    assert out["differences"] == 3
    assert "lake since 2026-10-19" in out["page"].read_text()
    member = [d for d in json.loads(out["manifest"].read_text())["preview"]["differences"] if d["member_id"]]
    assert member == [{"fy": 2015, "kind": "actuals", "member_id": "P-1:3010F:AF:ATA000", "preview_k": "4050000.000",
                       "reference_m": "4044.7", "cause": "lake since 2026-10-19", "blocks": False}]
```

- `test_render_writes_no_page_when_the_preview_fails`. The fake export raises `ValueError("Unreviewed F-35 workbook identity: 2026/0604999F")`. `render` raises that same error, and `out_root/"f-35"` holds no `B1.*`.
- `test_render_orders_the_page_and_records_the_manifest`. Let `page = out["page"].read_text(encoding="utf-8")` and `text = html.unescape(page)` (the test module imports `html`; Step 4 escapes every value, so `'` and `&` arrive as `&#x27;` and `&amp;`):
  - `page.index("P-1:3010F:AF:ATA000") < page.index("R-1:3600F:AF:0604800F") < page.index("not counted") < page.index("P-1:3020F:AF:JSM000") < page.index("R-1:3600F:AF:0207268F") < page.index("Exclusions")`.
  - `text` contains `53,368.3`, `1,939.5`, the literal owner quote `yes this is good, except we should break out the sub contractors because it doesn't end with lockheed and pratt & W` (equal to `review.PRIOR_APPROVALS["f-35"][1]`) and `piece 7`.
  - Each evidence ref is shown with its tier, in `text`: `src:msar-pb2027#p25 (G)` and `era:ATA000|3010F||2017-2023 (era decision)`.
  - The manifest keys are exactly the eight listed, and `preview`'s keys are exactly `years`, `cumulative_thousands` and `differences`.
  - `[r["member_row_id"] for r in rows]` is in page order: ATA000, 0604800F, JSM000, 0207268F.
  - `review_sha256 == sha256(review.csv bytes)`, `review_era_lines_sha256 == sha256(review_era_lines.csv bytes)` and `family_sha256 == reg.family_hash(json.loads(paths.json.read_text()), "f-35")`.
  - `preview.years[0] == {"fy": 2015, "kind": "actuals", "edition": 2017, "total_thousands": "4611600.000"}` and `preview.differences == []`.
- `test_compare_reference_refuses_a_reference_whose_named_years_disagree`. `B1_REF | {"fy2025_enacted": 1.0}` raises `ValueError` matching `fy2025_enacted 1.0 differs from totals\[2025\] 4972.5`.
- `test_cli_render_and_preview_require_duckdb_and_site_dir`, parametrized two ways:
  - `["platform-families", "render", "--family", "f-35", "--batch", "B1"]`;
  - `["platform-families", "preview", "--family", "f-35", "--draft", "--out", "x"]`.

  Each raises `SystemExit` with code 2 from argparse.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_cli.py -q 2>&1 | tail -3`

Expected: `10 failed, 25 passed`.
- 10 of the 12 new test items fail with `AttributeError: module 'govbudget.platform_family_review' has no attribute 'preview'` (or `PreviewResult`, `compare_reference`, `render`).
- The two `test_cli_render_and_preview_require_duckdb_and_site_dir` cases already pass. Task 7a Step 6 built the full parser with `--duckdb` and `--site-dir` required for `render` and `preview`, so argparse exits 2 before any branch runs.
- The earlier 23 pass.

- [ ] **Step 3: Implement `preview` and `compare_reference`**

**`preview` refuses, before any write:**
- an `out` for which `out.resolve().is_relative_to(config.SITE_DIR.resolve())` holds (`--out … is inside config.SITE_DIR`);
- a `published` family;
- a `draft` family without `draft` (`{pf} is a draft family; pass --draft to preview its proposed rows (review.csv)`);
- `draft` on a non-draft family;
- an existing `out` without `PREVIEW_MARKER` (`{out} exists and is not a preview scratch`). An existing `out` that has the marker is removed with `shutil.rmtree`.

**Then `preview`:**
1. With `draft`, the registry is `_trial_registry(registry, platform_family=pf, rows=<review.csv rows>, era_lines=<review_era_lines.csv rows>, ruling={…"ruling_id": f"R-DEC-FAM-{FAM}-PREVIEW"…}, paths=<review-file paths>)[3]`. Otherwise it is the loaded registry.
2. Call `vf.sam_guard`.
3. Run `subprocess.run(["cp", "-c", "-R", str(site_dir), str(out)], check=True)` and write the marker.
4. Call `hist.export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=reg_for_build, families=[pf], preview=True)`. A `None` return raises `RegistryError` (`preview built nothing for {pf}`).
5. Read `out/json/{history_dataset}.json`. `years` comes from `points` (`fy`, `kind`, `edition`, `Decimal(str(amount_thousands))`), in file order. `cumulative_thousands` comes from `cumulative.amount_thousands`. `member_years[(cell["program_id"], point["fy"], point["kind"])]` comes from `points[].program_cells[]`. An absent cell stays absent. `members` = `{m.code: m.member_id for m in <the built family>.counted}`.

**`compare_reference`.** The algorithm:

```text
R = max fy in reference["totals"]; kind(fy) = "request" if fy == R else "enacted" if fy == R - 1 else "actuals"
for name, fy in (("fy2025_enacted", 2025), ("fy2026_request", 2026)):   # self-consistency, raise ValueError
    if str(fy) in totals and reference[name] != totals[str(fy)]: raise ValueError(f"reference {name} {reference[name]} differs from totals[{fy}] {totals[str(fy)]}")
m(x) = None if x is None else (Decimal(x) / 1000).quantize(Decimal("0.1"), ROUND_HALF_UP)      # thousands → $M
r(x) = None if x is None else Decimal(str(x)).quantize(Decimal("0.1"))                          # reference $M
code→member_id from result.members, then from result.member_years keys (member_id.rsplit(":", 1)[1]); None only for a code neither names
member level: for every (code, fy) in reference["lines"] ∪ preview member-years:
    p = member_years.get((member_id, fy, kind(fy))); ref = r(lines.get(code, {}).get(str(fy)))
    if (p is None) != (ref is None) or (p is not None and m(p) != ref):
        mart = lake.program_series(code).get((fy, kind(fy)))
        cause = CAUSE_LAKE if (mart is None) == (p is None) and (p is None or m(mart) == m(p)) else CAUSE_PROPOSAL
        emit {fy, kind, member_id (None when no preview cell names the code), preview_k: p, reference_m: ref, cause, blocks: cause == CAUSE_PROPOSAL}
year level (member_id None): every fy of totals vs the years entry of (fy, kind(fy)); cumulative (fy None, kind "cumulative") vs
    result.cumulative_thousands. Cause CAUSE_LAKE iff every member-level difference in that fy (all actuals years for the
    cumulative) has CAUSE_LAKE and there is at least one; otherwise CAUSE_PROPOSAL.
order: member level by (fy, member_id), then year level by fy, then the cumulative
```

- [ ] **Step 4: Implement `render`, `render_page` and `batch_ruling_id`**

**`render` refuses:**
- a batch outside `era_map.BATCH_RE`;
- a family whose status is not `draft`;
- a batch whose `batch_ruling_id` is already in `registry.rulings`;
- a missing `review.csv`.

It uses `reg.load_registry(reg.DEFAULT_PATHS)`, because I-REV gives `render` no `paths` parameter.

**`render` then:**
1. Call `result = preview(platform_family=pf, draft=True, site_dir=site_dir, duckdb_path=duckdb_path, out=preview_out, paths=reg.DEFAULT_PATHS, review_root=review_root)`.
2. Read the reference if it exists. If it does, open `lake = reg.open_lake(duckdb_path)` (closed in a `finally`) and run `differences = compare_reference(result, reference, lake=lake)`. Without a reference there are no differences, and the page says `No reference figures for {batch}.`
3. Any difference with `blocks` raises `RegistryError`. It has one line per blocking difference, `f"platform-families: review.csv: FY{fy} {kind} {member_id or 'total'}: preview {m(p)} vs reference {ref} ($M) — proposal row; fix the prefill, re-run propose, render again"`. Nothing is written.
4. Write `B<n>.html` (`render_page(...)`) and `B<n>.json` (the manifest) under `out_root/<pf>/` in one `era_map._atomic_write_texts` call. `family_sha256 = reg.family_hash(registry.doc, pf)`.

**`render_page(*, family, rows, sources, result, reference, differences, batch) -> str`** returns one self-contained Artifact fragment: `<title>`, the font link, `<style>` and `<main>`, as `scripts/era/review_batch_page.py:render_page` emits (:246-284).
- **The CSS.** It copies that file's `:root` token block and its dark-mode block (`PAGE_CSS`, :58-93). `scripts/` is not importable from `src/`.
- **The header:**
  - "Family review, {short_name}, batch {batch}";
  - the prior approval from `PRIOR_APPROVALS = {"f-35": ("2026-10-19", "yes this is good, except we should break out the sub contractors because it doesn't end with lockheed and pratt & W")}`, quoted verbatim with its date;
  - the commitment from `PIECE_COMMITMENTS = {"f-35": "Subcontractors are broken out as their own layer in piece 7, as you asked on 2026-10-19."}`;
  - the answer instructions: reply `approved`, or name a row and its change (an amendable column, or `defer`); a change to a family field means a new page.
- **The sections, in §8.2 order:**
  1. **Preview figures.** One row per `years` entry: FY, kind, PB edition, preview $M and reference $M (`—` for absent). Then the cumulative row. Each difference is shown with its cause.
  2. **Counted rows**, sorted by `Decimal(headline_actuals_k or 0)` descending, then `member_row_id`.
  3. **"Context rows (not counted)"**, by `member_id`.
  4. **Every other row** (deferred, rejected or excluded), by `member_id`.
  5. **The family's fields**: the §7.2 keys other than the identity keys, then an `Exclusions` table (`exclusion_id`, `kind`, `size_text`, evidence).
- **Each row** shows: `member_id` and `display_title`; role and verdict; `valid_from_edition`–`valid_to_edition`; `program_tag`, `purpose_tag`, `variant_ids` and `variant_scope`; every evidence ref with its tier; `drift_sha256`; FY2015–24 $M with one decimal and thousands separators (`53,368.3`, or `—` when blank); and `reason`.
- **The evidence tier** comes from `ref_tier(ref, sources)`:
  - `doc:` gives `G`;
  - `src:<id>` gives that source's `tier`;
  - `era:` gives `era decision`;
  - `fact:` gives `fact`;
  - `ev:` gives `reserved`.
- Every interpolated value goes through `html.escape`.

- [ ] **Step 5: The `render` and `preview` branches in `src/govbudget/cli.py`**

- **`render`.** `preview_out` defaults to `args.site_dir.resolve().parent.parent / f"{args.site_dir.resolve().parent.name}-preview-{args.family}-{args.batch}"`. For `--site-dir $GOVBUDGET_PROOFS/fam2/site` that is `$GOVBUDGET_PROOFS/fam2-preview-f-35-B1`, D10's path. `--preview-out` overrides it. Then call `render(..., review_root=reg.REVIEW_ROOT, out_root=review.OUT_ROOT)` and print `platform-families render: {pf} {batch}: {rows} row(s), {differences} difference(s) -> {page} (manifest {manifest})`.
- **`preview`.** Call `preview(...)`. Print one line per year, `  FY{fy} {kind} PB{edition} {total_thousands:.3f}`, then `platform-families preview: {pf} cumulative {cumulative_thousands:.3f} thousand -> {out}`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_cli.py tests/test_verify_families.py -q 2>&1 | tail -1`

Expected: `57 passed` (35 + 22).

- [ ] **Step 7: W1 lint, the same two files as Task 7b Step 6**

Expected: `platform_family_review.py: 0`, `cli.py: 5`.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_family_review.py GovBudget/src/govbudget/cli.py GovBudget/tests/test_platform_families_cli.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): platform-families preview and render — the batch page shows the draft's preview beside the reference; a proposal-row difference blocks the page" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7d: `answer` and `ratify`

**Spec:** §8.2 ("The answer"; "If the owner defers B1"), §8.3 (`ratify`), §9.1 rules 16, 22, 23 and 25, and §19 row 25. D10 and Review Focus 1 and 5.

**Files:**
- Modify: `src/govbudget/platform_family_review.py`
- Modify: `src/govbudget/cli.py` (the `answer` and `ratify` branches)
- Modify: `tests/test_platform_families_cli.py` (append; and in the lock test, add `"ratify"` to its parameters and the ratify branch Step 1 describes)

**Interfaces:**
- **Consumes.**
  - Task 7c's manifest, `batch_ruling_id`, `review_files` and `OUT_ROOT`.
  - Task 7b's `_trial_registry` and `_era_row`.
  - I-REG: `family_hash`, `open_lake`, `measure_member`, `check_lake(registry, *, lake, site_dir, families)`, `write_registry` and `RegistryError`.
  - Task 7a: `vf.sam_guard` and `vf._now`.
- **Produces.**
  - `AMENDABLE_COLUMNS = ("role","verdict","program_tag","purpose_tag","purpose","variant_ids","variant_scope","scope_note","services_using","paying_org","predecessor_member_id","successor_member_id","link_basis","link_evidence","evidence","coverage_expected_from_edition","expected_next_edition","note")`;
  - `ANSWER_KEYS = frozenset({"batch", "decided_on", "owner_reply", "rows"})`;
  - `BATCH_RULING_SPEC = "docs/superpowers/specs/2026-10-20-families-piece2-registry-design.md#82-r-dec-fam-f35-b1-one-batch-through-the-batch-page"` (R13; the anchor style of Task 3a's `F15_SEED_SPEC`);
  - `answer(*, platform_family: str, batch: str, answers_path: Path, review_root: Path = REVIEW_ROOT, out_root: Path = OUT_ROOT) -> Path`;
  - `ratify(*, platform_family: str, batch: str, decided_on: str, duckdb_path: Path, site_dir: Path, paths: RegistryPaths = DEFAULT_PATHS, review_root: Path = REVIEW_ROOT, out_root: Path = OUT_ROOT) -> dict`, which returns `{"members": int, "era_lines": int, "ruling_id": str, "status": "ratified"}`;
  - **the answer file** `review_root/<pf>/batches/B<n>.json` = the answer input plus `review_sha256` and `manifest_sha256`, serialized `json.dumps(obj, indent=2, ensure_ascii=False) + "\n"`.

- [ ] **Step 1: Write the failing tests (append to `tests/test_platform_families_cli.py`)**

The fixture `answering` builds on `rendering` and runs `review.render(...)` once, with no differences and with `out_root=out_root` (the `proposing` fixture's, which is also the patched `review.OUT_ROOT`). It also:
- writes `ans = tmp_path / "B1-answers.json"` through `_answers(rows={}, decided_on="2026-10-22", owner_reply="approved")`;
- patches `reg.measure_member` with the `MEASURES` lookup;
- patches `reg.check_lake` with `lambda r, **kw: reg.LakeReport([], [], [])`.

Two module-level helpers check "nothing written" for `ratify`:
- `_snap(paths, rr) -> dict[Path, bytes]` returns the bytes of the three registry files and both review files: `{p: p.read_bytes() for p in (paths.json, paths.members, paths.era_lines, *review.review_files(rr, "f-35"))}`;
- `_assert_unchanged(baseline, paths, rr)` asserts `_snap(paths, rr) == baseline`.

Each ratify-refusal test that checks "nothing written" takes `baseline = _snap(paths, rr)` immediately before the refused `ratify` call: after `review.answer`, and after any file edit the test itself makes. Never compare against the `proposing` fixture's `before`: it predates `propose`, so it holds neither review file and not the draft `propose` writes into `platform_families.json`.

```python
ATA, F00, JSM, SLICE = ("f-35|P-1:3010F:AF:ATA000|2017-2026", "f-35|R-1:3600F:AF:0604800F|2017-2023",
                        "f-35|P-1:3020F:AF:JSM000|2022-2026", "f-35|R-1:3600F:AF:0207268F|2017-2026")

def test_answer_writes_the_batch_file_with_both_shas(answering):
    path = review.answer(platform_family="f-35", batch="B1", answers_path=ans, review_root=rr, out_root=out_root)
    assert path == rr / "f-35" / "batches" / "B1.json"
    got = json.loads(path.read_text())
    assert got == {"batch": "B1", "decided_on": "2026-10-22", "owner_reply": "approved", "rows": {},
                   "review_sha256": _sha(rr / "f-35" / "review.csv"), "manifest_sha256": _sha(out_root / "f-35" / "B1.json")}

@pytest.mark.parametrize("change,needle", [({"extra": 1}, "unknown key"), ({"owner_reply": "  "}, "owner_reply"),
                                           ({"decided_on": "20261022"}, "not an ISO date")])
def test_answer_refuses_unknown_keys_a_blank_reply_or_a_non_iso_date(...):  # RegistryError ⊇ needle; no batches/B1.json

def test_answer_refuses_a_changed_review_csv(...):   # rewrite review.csv with one reason changed → "changed since B1 was rendered"

@pytest.mark.parametrize("column", ["member_id", "valid_from_edition", "drift_sha256", "titles_seen", "member_order"])
def test_answer_refuses_identity_edition_or_lake_column_amendments(answering, column):   # Review Focus 1
    _answers(rows={ATA: {column: "x"}})
    with pytest.raises(reg.RegistryError) as e:
        review.answer(...)
    assert f"{ATA}: {column} is not amendable in an answer" in str(e.value) and "re-run propose" in str(e.value)
    assert not (rr / "f-35" / "batches" / "B1.json").exists()

def test_answer_refuses_a_row_not_on_the_page(answering):               # Review Focus 1
    _answers(rows={"f-35|P-1:3010F:AF:F03500|2017-2026": {"note": "x"}})
    with pytest.raises(reg.RegistryError, match=r"f-35\|P-1:3010F:AF:F03500\|2017-2026 is not on the B1 page"):
        review.answer(...)

def test_ratify_writes_members_era_lines_and_the_batch_ruling(answering):
    _answers(rows={JSM: {"note": "context only"}}); review.answer(...)
    out = review.ratify(platform_family="f-35", batch="B1", decided_on="2026-10-22", duckdb_path=db, site_dir=site,
                        paths=paths, review_root=rr, out_root=out_root)
    assert out == {"members": 4, "era_lines": 1, "ruling_id": "R-DEC-FAM-F35-B1", "status": "ratified"}
    registry = reg.load_registry(paths)
    ruling = registry.rulings["R-DEC-FAM-F35-B1"]
    assert (registry["f-35"].status, ruling.kind, ruling.platform_family, ruling.decided_by, ruling.decided_on,
            ruling.owner_reply, ruling.seed_basis) == ("ratified", "batch", "f-35", "owner", "2026-10-22", "approved", False)
    assert ruling.spec == review.BATCH_RULING_SPEC and ruling.spec.endswith("#82-r-dec-fam-f35-b1-one-batch-through-the-batch-page")
    rows = {r["member_row_id"]: r for r in _csv(paths.members) if r["platform_family"] == "f-35"}
    assert [rows[i]["member_order"] for i in (ATA, F00, JSM, SLICE)] == ["1", "2", "", ""]
    assert {r["ruling_id"] for r in rows.values()} == {"R-DEC-FAM-F35-B1"} and rows[JSM]["note"] == "context only"
    assert rows[SLICE]["verdict"] == "deferred"
    assert [r["member_id"] for r in _csv(paths.era_lines) if r["platform_family"] == "f-35"] == ["P-1:3010F:AF:ATA000"]
    assert [m.member_id for m in registry["f-15"].counted] == F15_ORDER        # F-15 untouched

def test_ratify_renumbers_member_order_after_a_deferral(answering):     # Review Focus 1
    _answers(rows={ATA: {"defer": True}}); review.answer(...)
    out = review.ratify(...)
    rows = {r["member_row_id"]: r for r in _csv(paths.members) if r["platform_family"] == "f-35"}
    assert (rows[ATA]["verdict"], rows[ATA]["member_order"], rows[F00]["member_order"]) == ("deferred", "", "1")
    assert out["era_lines"] == 0

def test_ratify_refuses_a_decided_on_unlike_the_answer(answering):      # Review Focus 1
    review.answer(...)
    baseline = _snap(paths, rr)
    with pytest.raises(reg.RegistryError, match="--decided-on 2026-10-23 differs from the answer's decided_on 2026-10-22"):
        review.ratify(..., decided_on="2026-10-23")
    _assert_unchanged(baseline, paths, rr)
```

- `test_ratify_refuses_a_family_object_changed_since_the_render`. After the answer, set the f-35 `scope_note` in `paths.json` to `"Edited."`, then take `baseline = _snap(paths, rr)`, so the baseline holds the edit. It expects `"family object changed since B1 was rendered"`, and nothing written: `_assert_unchanged(baseline, paths, rr)`.
- `test_ratify_refuses_a_reused_batch`. Ratify once, then again. It expects `"R-DEC-FAM-F35-B1 already exists"`.
- `test_ratify_refuses_a_lake_hash_unlike_the_review_time_drift`. `MEASURES` for 0604800F is changed to drift `"e"*64`. It expects `f"{F00}: drift_sha256 {'e'*64} differs from the review-time {'b'*64}"`.
- `test_ratify_lists_every_refusal_at_once_and_writes_nothing`. It combines the decided_on mismatch with the drift mismatch, and expects both lines in `e.errors`. The three registry files and both review files must be byte-unchanged: `baseline = _snap(paths, rr)` after the answer, and `_assert_unchanged(baseline, paths, rr)` after the refusal.
- `test_propose_and_ratify_write_nothing_on_a_lock` gains the `"ratify"` parameter and its branch (Review Focus 5). Ratify reaches the lake only at Step 4's step 6, after steps 1–5 have read the answer, the manifest and both review files. So the branch first builds that state:
  - `request.getfixturevalue("answering")`. It builds on the `proposing` the test already holds, and renders B1;
  - `review.answer(platform_family="f-35", batch="B1", answers_path=ans, review_root=rr, out_root=out_root)`;
  - then it takes `baseline = _snap(paths, rr)`: the three registry files and both review files (`review.csv`, `review_era_lines.csv`).

  Only then does it patch `reg.open_lake` to raise `duckdb.IOException(LOCK)`. `cli.main(["platform-families", "ratify", "--family", "f-35", "--batch", "B1", "--decided-on", "2026-10-22", "--duckdb", str(db), "--site-dir", str(site)])` exits 2. The CLI passes `out_root=review.OUT_ROOT`, which `proposing` patched to `out_root`, so ratify reads the manifest that `answering`'s render wrote. stderr starts with `platform-families ratify: ERROR — ` and contains `Could not set lock on file`, not `answer B1 first`. Nothing is written: `_assert_unchanged(baseline, paths, rr)`. The propose branch's `rr/"f-35"` check does not apply here, because the `rendering` fixture's `propose` wrote that directory.
- `test_propose_render_answer_ratify_round_trip`. The whole cycle runs through `cli.main`, with the stubs above: `propose`, then `render --family f-35 --batch B1 --duckdb D --site-dir S --preview-out P`, `answer --family f-35 --batch B1 --answers A`, `ratify … --decided-on 2026-10-22 --duckdb D --site-dir S` and `check`. Its `render`, `answer` and `ratify` write and read the page and manifest under `out_root`, the `review.OUT_ROOT` that `proposing` patched, never the checkout's `tmp/platform-families/`. Each exits 0, or returns. The final `load_registry(paths)["f-35"].status == "ratified"`, and `check`'s last line is `platform-families check: families=2 failures=0 undecided=0 stale=0`.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_cli.py -q 2>&1 | tail -3`

Expected: the 20 new cases fail with `AttributeError: module 'govbudget.platform_family_review' has no attribute 'answer'` (or `'ratify'`), and the earlier 35 pass.

- [ ] **Step 3: Implement `answer`**

Every check runs before the write, and the errors are raised together as one `RegistryError`.
1. **The manifest** is `out_root/<pf>/<batch>.json`. A missing one raises `render {batch} first`. Its `platform_family` and `batch` must match.
2. **The review files.** `sha256(review.csv)` must equal `manifest["review_sha256"]`, and `sha256(review_era_lines.csv)` must equal `manifest["review_era_lines_sha256"]`. Otherwise: `{review.csv} changed since {batch} was rendered (sha256 {old[:12]} at render, {new[:12]} now) — render the batch again`.
3. **The answer input.** It must be one JSON object, with duplicate keys refused.
   - Its keys must be ⊆ `ANSWER_KEYS`; a stray one fails with `unknown key(s) [...]`.
   - `batch` must match.
   - `owner_reply` must be non-blank after `strip()`. It is stored verbatim.
   - `decided_on` must match `^\d{4}-\d{2}-\d{2}$` and pass `date.fromisoformat`; otherwise `decided_on {v!r} is not an ISO date`.
   - `rows` must be an object keyed by `member_row_id`. Each id must be one of the manifest rows' (`{id} is not on the {batch} page`).
   - Each value is either exactly `{"defer": true}` or an object whose keys are ⊆ `AMENDABLE_COLUMNS` with string values. Anything else fails with `{id}: {column} is not amendable in an answer; change it in the prefill and re-run propose`.
4. **Write** `review_root/<pf>/batches/<batch>.json` atomically: the input, then `review_sha256` and then `manifest_sha256` (the sha256 of the manifest's bytes).

`answer` does not open the registry. The reused-batch refusal belongs to `ratify`.

- [ ] **Step 4: Implement `ratify`**

Every refusal is collected first, then raised as one `RegistryError`, and nothing is written (#198 style).
1. **Read the files.** The answer file must exist (`answer {batch} first`). The manifest must exist, and its sha256 must equal the answer's `manifest_sha256`. Both review files' shas must equal the manifest's and the answer's.
2. **Check the batch and family.**
   - `ruling_id = batch_ruling_id(pf, batch)`. If it is already in `registry.rulings`, refuse with `{ruling_id} already exists (batch {batch} is ratified)`.
   - The family status must be `draft`.
   - `reg.family_hash(registry.doc, pf)` must equal `manifest["family_sha256"]`; otherwise `the {pf} family object changed since {batch} was rendered — re-run propose and render a new page`.
   - `decided_on` must equal the answer's `decided_on`; otherwise `--decided-on {decided_on} differs from the answer's decided_on {answer_date}`.
3. **Merge.** The rows are the `review.csv` rows the manifest lists.
   - Apply each amendment. `{"defer": true}` sets `verdict="deferred"`.
   - Clear `member_order` on every row that is not approved counted.
   - Renumber the approved counted rows 1..n, ordered by (their `review.csv` `member_order` as an int, or after all numbered ones when it is blank; then `member_row_id`).
   - A members-CSV row with the same `member_row_id` may be replaced only when its `verdict` is `deferred`. Otherwise refuse with `{id} is already ratified`.
4. **The ruling:** `{"ruling_id": ruling_id, "kind": "batch", "platform_family": pf, "decided_by": "owner", "decided_on": decided_on, "owner_reply": answer["owner_reply"], "spec": BATCH_RULING_SPEC, "text": f"The owner ratified batch {batch} of the {pf} family as shown on its batch page (manifest sha256 {manifest_sha256}): {a} approved, {d} deferred, {x} rejected or excluded row(s).", "seed_basis": False}`.
5. **Stage 1.** Call `_trial_registry(registry, platform_family=pf, rows=merged, era_lines=<review_era_lines.csv rows>, ruling=ruling, paths=paths)`. A `RegistryError` contributes its `errors`.
6. **Stage 2.** It runs only if steps 1–5 left the trial registry parseable.
   - `start = vf._now()`, `vf.sam_guard(duckdb_path, start=start)`, then `lake = reg.open_lake(duckdb_path)`.
   - Every row that is approved after the merge is re-measured: `reg.measure_member(lake, member, headline=family.headline).drift_sha256` must equal the row's `drift_sha256` from `review.csv`. Otherwise: `{id}: drift_sha256 {new} differs from the review-time {old}`.
   - `report = reg.check_lake(trial, lake=lake, site_dir=site_dir)`, with no `families=` keyword: stage 2 runs for every family (§9.2, R13). `report.failures` and `report.stale` are appended (R4); `undecided` is not a refusal.
   - `lake.close()` goes in a `finally`, then `vf.sam_guard(duckdb_path, start=start, end=vf._now())`. A lock propagates, with nothing written.
7. **Write.** `reg.write_registry(paths, doc=trial_doc, members=trial_members, era_lines=trial_era_rows)`, as one atomic call. The review files and the answer file stay as they are.
8. Return `{"members": len(merged), "era_lines": <era rows added for pf>, "ruling_id": ruling_id, "status": "ratified"}`.

- [ ] **Step 5: The `answer` and `ratify` branches in `src/govbudget/cli.py`**

- **`answer`** prints `platform-families answer: {pf} {batch} -> {path}; next: platform-families ratify --family {pf} --batch {batch} --decided-on {decided_on}`.
- **`ratify`** calls `ratify(..., duckdb_path=args.duckdb or config.DUCKDB_PATH, site_dir=args.site_dir or config.SITE_DIR, paths=reg.DEFAULT_PATHS, review_root=reg.REVIEW_ROOT, out_root=review.OUT_ROOT)`. It prints `platform-families ratify: {pf} {status} as {ruling_id}; {members} member row(s), {era_lines} era line(s) -> data-seeds/`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_platform_families_cli.py tests/test_verify_families.py tests/test_verify_phase5.py -q 2>&1 | tail -1`

Expected: `147 passed` (55 + 22 + 70).

- [ ] **Step 7: W1 lint, the same two files as Task 7b Step 6**

Expected: `platform_family_review.py: 0`, `cli.py: 5`.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/platform_family_review.py GovBudget/src/govbudget/cli.py GovBudget/tests/test_platform_families_cli.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(families): platform-families answer and ratify — the owner's batch reply becomes the batch ruling; refusals listed at once, nothing written" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7e: The site mirror test and gate leg (r)

**Spec:** §13 "Site side" (the hermetic mirror; one leg that checks each family in `index.json` for its history artifact and built page; leg p, gate 1's weight row and the snapshot tool unchanged), §12 and §3 (no F-15 TypeScript change). D8 and K1.

**Files:**
- Create: `site/src/__tests__/platform-family-mirror.test.ts`
- Create: `site/scripts/gates/__tests__/family-index.test.mjs`
- Modify: `site/scripts/gates/family-history.mjs`. Add `import fs from "node:fs";` and `import path from "node:path";` after its two imports (:1-2), and append `checkFamilyIndex`.
- Modify: `site/scripts/gates/program-skeleton.mjs` (gate 21; line hints at `b6c9a8d9`, with `b30134c4`'s in brackets):
  - **The header comment.** Add an `(r)` paragraph after `(p)`'s (` * (p) /families/f-15/ states the family funding history its export carries:`, `:78-82` [`:76-80`]), which is the last paragraph before ` */`. The link fix's `(q)` paragraph (` * (q) A pair the owner ruled withdrawn …`, `:72-77`) sits before `(p)`, and stays there. The link fix took `(q)` in `b30134c4` (`runLineRulingsLeg`, D8); gate 21 has no `(r)` yet.
  - **The import.** `import { checkFamilyHistory, checkFamilyHistoryAssets } from "./family-history.mjs";` (`:90` [`:87`]) becomes `import { checkFamilyHistory, checkFamilyHistoryAssets, checkFamilyIndex } from "./family-history.mjs";`.
  - **The call.** One call goes after `runLineRulingsLeg({ errors, notes, sidecars });` (`:569` [`:566`]), the last leg call before `return { pass: errors.length === 0, errors, notes };`.
  - **The leg.** `runFamilyIndexLeg` goes at the end of the file, after leg (q)'s block. That block runs from its `// leg q — a pair the owner ruled withdrawn publishes nowhere` banner to `runLineRulingsLeg`'s closing brace: `:4216-4532` at `31b1e47b` (`:4216-4481` at `9a50e28b`, `:4216-4476` at `b6c9a8d9`, `:4213-4348` at `b30134c4`). Round 2, M-2 (`f308589c`), round 3's `9a50e28b`, which raised its floor to 51, and its review fixes `b47c11b9` and `31b1e47b` grew it. Anchor on the end of `export function runLineRulingsLeg({`.

**Interfaces:**
- **Consumes.**
  - Task 3a's `data-seeds/platform_family_members.csv`. The F-15's approved counted rows with a `page_slug`, in `member_order`, are 0207134F, 0207146F, 0207171F, F01500, F015EX and F15EWS.
  - The D7 `json/families/index.json` format: `{"families": [{"history", "history_dataset", "members", "platform_family", "route", "ruling_ids", "short_name"}], "schema_version": 1}`.
  - `parseCsv` from `site/scripts/gates/basis.mjs:3270`. It trims every field.
  - `F15_RECORD_SLUGS` from `@/lib/f15-family`. It does not import `server-only`, while `f15-family-data.ts` does, so the mirror reads that file's source text and never imports it.
  - The `typescript` devDependency (5.9.3).
- **Produces.**
  - I-SITE `export function checkFamilyIndex(dataDir, outDir): string[]`. `dataDir` is the `data/site` root; `outDir` is `site/out`.
  - Leg (r) findings prefixed `program-skeleton(r): `.

- [ ] **Step 1: Write the failing gate unit test `site/scripts/gates/__tests__/family-index.test.mjs`**

The fixture `tree({index, histories, pages})` builds `data/site/json/…` and `out/families/<id>/index.html` under `fs.mkdtempSync(path.join(os.tmpdir(), "family-index-"))` and removes it in `afterEach`.

```js
import { describe, it, expect, afterEach } from "vitest";
import { checkFamilyIndex } from "../family-history.mjs";

const F15 = { history: "json/f15_funding_history.json", history_dataset: "f15_funding_history", members: [],
              platform_family: "f-15", route: "/families/f-15/", ruling_ids: ["R-DEC-FAM-F15-SEED"], short_name: "F-15" };
const F35 = { ...F15, history: "json/f35_funding_history.json", history_dataset: "f35_funding_history",
              platform_family: "f-35", route: "/families/f-35/", ruling_ids: ["R-DEC-FAM-F35-B1"], short_name: "F-35" };

describe("checkFamilyIndex — every listed family has its history and its built page", () => {
  it("passes when each family has both", () => {
    const { data, out } = tree({ index: { families: [F15], schema_version: 1 }, histories: ["f15_funding_history"], pages: ["f-15"] });
    expect(checkFamilyIndex(data, out)).toEqual([]);
  });
  it("fails closed when the index is missing", () => {
    expect(checkFamilyIndex(...tree({})) ).toEqual(["json/families/index.json is missing"]);
  });
  it("fails on an index that is not JSON", () => { /* index text "{" */ expect(f[0]).toMatch(/^json\/families\/index\.json is not JSON: /); });
  it("fails on a schema_version other than 1", () => { /* 2 */ expect(f).toEqual(["json/families/index.json schema_version is 2, not 1"]); });
  it("fails when the index lists no family", () => { expect(f).toEqual(["json/families/index.json lists no family"]); });
  it("names a family whose history artifact is missing", () => { expect(f).toEqual(["f-15: json/f15_funding_history.json is missing"]); });
  it("names a family whose page is not built", () => { expect(f).toEqual(["f-15: families/f-15/index.html is not built"]); });
  it("reads each family's own history path, not a hard-coded F-15 one", () => {
    // index [F15, F35]; only the F-15 has its history and page
    expect(f).toEqual(["f-35: json/f35_funding_history.json is missing", "f-35: families/f-35/index.html is not built"]);
  });
});
```

- [ ] **Step 2: Write the mirror test `site/src/__tests__/platform-family-mirror.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import ts from "typescript";
import { parseCsv } from "../../scripts/gates/basis.mjs";
import { F15_RECORD_SLUGS } from "@/lib/f15-family";

const ROOT = resolve(__dirname, "../../..");   // GovBudget/
type Config = Record<string, { purpose: string; variantIds: string[]; scopeNote: string }>;

/** RECORD_CONFIG read from the source text (it is not exported; the file stays unedited): the
 *  VariableDeclaration named RECORD_CONFIG → ObjectLiteralExpression → PropertyAssignment whose
 *  name is an Identifier or StringLiteral, each value an object literal with purpose (StringLiteral),
 *  scopeNote (StringLiteral) and variantIds (ArrayLiteralExpression of StringLiteral). */
function readRecordConfig(source: string): Config { /* ts.createSourceFile(…, ts.ScriptTarget.Latest, true) + walk */ }

/** One finding per paged member whose purpose / variant_ids (";"-split) / scope_note differ. */
function recordConfigProblems(rows: Record<string, string>[], config: Config): string[] { … }

const rows = parseCsv(readFileSync(resolve(ROOT, "data-seeds/platform_family_members.csv"), "utf8"));
const paged = rows.filter((r) => r.platform_family === "f-15" && r.role === "counted" && r.verdict === "approved" && r.page_slug !== "")
                  .sort((a, b) => Number(a.member_order) - Number(b.member_order));
const config = readRecordConfig(readFileSync(resolve(ROOT, "site/src/lib/f15-family-data.ts"), "utf8"));

describe("the F-15 registry rows mirror the F-15 TypeScript (CLAUDE.md mirror rule; spec §13)", () => {
  it("lists the paged counted members, in member_order, as F15_RECORD_SLUGS", () => {
    expect(paged.map((r) => r.page_slug)).toEqual([...F15_RECORD_SLUGS]);
  });
  it("reads one RECORD_CONFIG entry per record slug from the source", () => {
    expect(Object.keys(config).sort()).toEqual([...F15_RECORD_SLUGS].sort());
    expect(config.F15EWS).toEqual({ purpose: "upgrade", variantIds: ["E"], scopeNote: "The procurement narrative describes EPAWSS installation and related support for F-15E aircraft. This amount is not assigned to F-15EX." });
  });
  it("carries RECORD_CONFIG's purpose, variant ids and scope note on every paged member", () => {
    expect(recordConfigProblems(paged, config)).toEqual([]);
  });
  it("catches a drifted scope note", () => {
    const drifted = paged.map((r) => (r.page_slug === "F15EWS" ? { ...r, scope_note: "Edited." } : r));
    expect(recordConfigProblems(drifted, config)).toEqual(["F15EWS: scope_note differs from RECORD_CONFIG"]);
  });
});
```

`recordConfigProblems` reports each kind of drift with the same shape: `"{slug}: purpose differs from RECORD_CONFIG"`, `"{slug}: variant_ids differ from RECORD_CONFIG"` and `"{slug}: scope_note differs from RECORD_CONFIG"`.

- [ ] **Step 3: Run both to verify their state**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run scripts/gates/__tests__/family-index.test.mjs src/__tests__/platform-family-mirror.test.ts 2>&1 | tail -6`

Expected:
- `family-index.test.mjs` fails, because the module has no export named `checkFamilyIndex`;
- `platform-family-mirror.test.ts` passes 4 of 4. Task 3a's seed already mirrors the TypeScript, and "catches a drifted scope note" is its red control.

- [ ] **Step 4: Implement `checkFamilyIndex(dataDir, outDir)` in `site/scripts/gates/family-history.mjs`**

- It reads `path.join(dataDir, "json/families/index.json")`.
- It returns at once, with the single finding, when the index is missing, is not JSON, has `schema_version !== 1`, or has `families` that is not a non-empty array. The messages are Step 1's.
- Otherwise, for each family in index order:
  - `path.join(dataDir, family.history)` must exist (`${platform_family}: ${history} is missing`);
  - `path.join(outDir, "families", platform_family, "index.html")` must exist (`${platform_family}: families/${platform_family}/index.html is not built`).
- Its JSDoc says: an absent or empty index fails, never skips (D8, K1).

- [ ] **Step 5: Add leg (r) to `site/scripts/gates/program-skeleton.mjs`**

The header paragraph, verbatim, after `(p)`'s:

```text
 * (r) Every family json/families/index.json lists has its history artifact in
 *     data/site/json and a built page at out/families/<id>/index.html, and a
 *     missing or empty index fails rather than skips (families piece 2, spec
 *     2026-10-20 §13; the index lists published families only) — see leg r's
 *     own block at the bottom.
```

`function runFamilyIndexLeg({ errors, notes })` calls `checkFamilyIndex(path.dirname(jsonDir), outDir)`.
- Each finding goes into `errors` with the prefix `program-skeleton(r): `.
- When there is none, it notes `leg r: ${n} family index entr${n === 1 ? "y" : "ies"} with history and built page ✓`, where `n` is read from the index.

Its block comment follows leg p's banner style and names spec §13 and D8. Call it right after `runLineRulingsLeg({ errors, notes, sidecars });`, under a `// ── (r) every family in json/families/index.json has its history and its page ──` banner. Leg p, leg q (the link fix's), gate 1's weight row (`build.mjs:288`) and `scripts/f15-page-snapshot.mjs` are untouched. The leg is gate 21's (r); gate 24 (`datatruth.mjs`) keeps its own, unrelated leg r (district by-year cells, D8).

- [ ] **Step 6: Run the tests to verify they pass, and show leg (r) fails closed on the live export (K1)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && source ../scripts/era/env.sh || exit 1
npx vitest run scripts/gates/__tests__/family-index.test.mjs src/__tests__/platform-family-mirror.test.ts 2>&1 | grep -E "Test Files|Tests "
node -e "import('./scripts/gates/family-history.mjs').then((m) => console.log(JSON.stringify(m.checkFamilyIndex('../data/site', 'out'))))"
npx eslint scripts/gates/family-history.mjs scripts/gates/program-skeleton.mjs scripts/gates/__tests__/family-index.test.mjs src/__tests__/platform-family-mirror.test.ts && echo "eslint clean"
npx tsc --noEmit -p . && echo "tsc clean"
```

Expected:
- `Test Files  2 passed (2)` and `Tests  12 passed (12)`;
- `["json/families/index.json is missing"]`. This is **K1**: `npm run verify` against the live `data/site` stays red on gate 21 leg (r) until Task 10a's export. Run the full verify only on Task 9b's and Task 10a's builds.
- `eslint clean`;
- `tsc clean`.

- [ ] **Step 7: The F-15 freeze holds**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && A=$(git merge-base main HEAD) && git diff --quiet "$A" -- GovBudget/site/scripts/gates/__tests__/f15-page-snapshot.test.mjs GovBudget/site/src/lib/f15-family-data.ts GovBudget/site/src/lib/f15-family.ts GovBudget/site/scripts/f15-page-snapshot.mjs GovBudget/site/scripts/gates/build.mjs && echo "F-15 site files unchanged"`

Expected: `F-15 site files unchanged`.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/src/__tests__/platform-family-mirror.test.ts GovBudget/site/scripts/gates/__tests__/family-index.test.mjs GovBudget/site/scripts/gates/family-history.mjs GovBudget/site/scripts/gates/program-skeleton.mjs && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(site): the F-15 registry rows mirror RECORD_CONFIG; gate 21 leg r checks every family in json/families/index.json (fails closed: K1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8a: The F-35 prefill, `propose` against fam2 and the B1 page

**Spec:** §7.2 (the F-35 column), §7.5, §7.7, §8.2, §8.3 (`propose`, `render`, `preview`), §9.2 (a draft family), §18 (the F-35 `doc:` refs and era-lines count are measured), Appendix A row 8; D10, D12.

**Files:**
- Create:
  - `data/research/platform_families/f-35/prefill/family.json`;
  - `data/research/platform_families/f-35/prefill/rows.csv`;
  - `data/research/platform_families/f-35/reference-b1.json`.
- Generated by `propose`, then committed:
  - `data-seeds/platform_families.json` (the F-35 `draft` and the `msar-pb2027` source);
  - `data/research/platform_families/f-35/review.csv`;
  - `data/research/platform_families/f-35/review_era_lines.csv`.
- Generated by `render`, git-ignored: `tmp/platform-families/f-35/B1.html` and `B1.json`. Preview scratch goes to `$GOVBUDGET_PROOFS/fam2-preview-f-35-B1/` (D10).
- Ledger: `…/families-piece2/b1-preview.md`.

**Interfaces:**
- Consumes:
  - From Task 7b and 7c (I-REV): `platform-families propose --family <id> --family-json <json> --rows <csv> [--duckdb]` and `platform-families render --family <id> --batch B<n> --duckdb <fam2> --site-dir <fam2 site>`.
  - The I-REG names `PREFILL_COLUMNS`, `REVIEW_COLUMNS`, `ERA_LINE_COLUMNS`, `load_registry`, `family_hash(doc, platform_family) -> str` and `resolve_doc_ref(ref, *, site_dir) -> str | None`.
  - `compare_reference(result, reference, *, lake)`, which reads `reference-b1.json`.
  - `FAM2_DUCKDB` and `FAM2_SITE` (Task 1).
- Produces:
  - `reference-b1.json`, shaped `{"lines": {code: {"2015": $M|null, …, "2026": $M|null}}, "totals": {"2015": $M, …, "2026": $M}, "cumulative": 116808.4, "fy2025_enacted": 12532.3, "fy2026_request": 11467.0}`.
  - `prefill/family.json`, shaped `{"family": <the §7.2 F-35 object without status and published_ruling_id>, "sources": [<msar-pb2027>]}`.
  - The committed draft F-35, `review.csv` (19 rows) and `review_era_lines.csv` (63 rows).
  - The B1 page and manifest. Task 8b answers on them.
  - The ledger `b1-preview.md`.

**Measured (live lake, read-only, outside :12–:22, 2026-10-21; piece 2 and the link fix change no budget line, so fam2 reads the same).** The link fix moves only award-link surfaces. Some of them belong to F-35 members: it withdraws the production links on 0592, 0593 and F03500, and the N0001922F0001 Rolls-Royce order leaves `flows/ATA000.json`, /district/IN-07/ and ATA000's `programs.json` concentration. Round 3 (R-DEC-LINK-2026-10-21-B) also withdraws F03500's 10 production-support orders and moves F03500's all-basis concentration (B-C1). The B1 page, the preview, `reference-b1.json` and every registry column below are budget figures and identities only (`contract_routes` stays null; `contract_link_policy` is blank on every prefill row), so none of them moves.
- **Code-keyed lake rows** (`budget_lines.parquet`, `cast(fiscal_year as integer)`):

  | Code | Editions | Title (every edition unless noted) | BA |
  |---|---|---|---|
  | ATA000 | 2024–2026 | F-35 | 01 |
  | F03500 | 2024–2026 | F-35 Modifications | 05 |
  | 0152 | 2024–2026 | JSF STOVL | 01 |
  | 0592 | 2024–2026 | F-35 STOVL Series | 05 |
  | 0147 | 2024–2026 | Joint Strike Fighter CV | 01 |
  | 0593 | 2024–2026 | F-35 CV Series | 05 |
  | 0604800F | 2017–2023 | F-35 - EMD | 05 |
  | 0604800N, 0604800M | 2017–2025 | Joint Strike Fighter (JSF) - EMD | 05 |
  | 0604810N, 0604810M | 2017–2020 | 2017: Joint Strike Fighter Follow On Development - Navy (Marine Corps); 2018–2020: Joint Strike Fighter Follow On Modernization (FoM) - Navy (Marine Corps) | 05 |
  | 0604840F | 2020–2026 | F-35 C2D2 | 07 |
  | 0604840N, 0604840M | 2019–2026 | F-35 C2D2 | 07 |
  | 0207142F | 2017–2026 | F-35 Squadrons | 07 |
  | 000999 | 2024–2026 | Initial Spares/Repair Parts | 3010F 06; 3020F 04 |
  | 0605 | 2024–2026 | Spares and Repair Parts | 06 |
  | JSM000 | 2024–2026 | Joint Strike Missile (3020F) | 02 |
  | 0207268F | 2017–2026 | Aircraft Engine Component Improvement Program | 07 |

  The R-1 rows carry both spellings of the organization (`AF`/`F`, `NAVY`/`N`).
- **`p1_era_line_map`.** The six counted chains hold 63 rows, all `same_program` under `R-DEC-ERA-SAME`, editions 2017–2023, with their titles unchanged. ATA000, 0152 and 0147 have 14 each, and F03500, 0592 and 0593 have 7 each; BA is 01 for production and 05 for modifications. Two context chains also exist: 000999 (8 rows, `R-DEC-ERA-B1`) and 0605 (7).
- **The review guard on the live lake** finds 150 distinct (edition, pe) lines: 87 code-keyed (the 15 members plus JSM000) and 63 era-keyed (exactly the six chains' roster).
- **`fct_program_decade_series`** over the 15 codes on B1's basis reproduces every B1 total and the cumulative at `ROUND_HALF_UP` to 0.1. B1's basis is actuals from PB{fy+2}, with FY2025 enacted and the FY2026 request from PB2026. Totals in thousands:

  | FY | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 |
  |---|---|---|---|---|---|---|
  | Thousands | 8,276,453 | 11,159,349 | 10,767,556 | 12,724,876 | 11,743,209 | 12,187,056 |

  | FY | 2021 | 2022 | 2023 | 2024 | 2025 (enacted) | 2026 (request) |
  |---|---|---|---|---|---|---|
  | Thousands | 12,744,466 | 11,889,941 | 11,845,845 | 13,469,616 | 12,532,299 | 11,466,954 |

  The FY2015–24 cumulative is 116,808,367.
- **Member FY2015–24 dollars** (thousands; the page's sort order): ATA000 53,368,317; 0152 22,654,924; 0147 20,097,427; 0604840F 4,627,447; 0604840M 2,459,683; 0604840N 2,370,205; F03500 2,094,998; 0604800F 1,939,531; 0604800M 1,758,823; 0604800N 1,659,724; 0207142F 1,387,574; 0592 1,328,912; 0593 667,304; 0604810M 199,303; 0604810N 194,195.
- **Pages.** All 19 codes have `data/site/json/program_details/<code>.json`. None is a collision key.
- **Hosted PDFs and pages** (`data/site/pdfs`; pypdf text, one line each):
  - **AF Aircraft Procurement Vol I PB2026,** `528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e`:
    - p.55, `LI ATA000 - F-35`: `Line Item MDAP/MAIS Code: 198` and `Funding for this exhibit contained in PE 0207142F.`;
    - p.175: `ATA000 / F-35 Squadrons [198]`.
  - **APN BA1-4 PB2026,** `e7e130253786cbd906d4367bc622649fc9ad86a38ce3677da47ad33d9c628ca0`:
    - p.51, `LI 0147 - Joint Strike Fighter CV`: `Line Item MDAP/MAIS Code: 198` and `Program Elements for Code B Items: 0204146N`;
    - p.83, `LI 0152 - JSF STOVL`: `Line Item MDAP/MAIS Code: 198`.
  - **AF Missile Procurement PB2026,** `4edf049fb40b58835092f49d2dd60f74cfce4280065b0c6c655f40c7c15ac94d`, p.99: `LI JSM000 - Joint Strike Missile`.
  - **Not hosted:** the APN BA6-7 book (0605's p.47) and the Navy RDT&E BA4–7 book. Those rows rely on the era ref or on `src:msar-pb2027`.

- [ ] **Step 1: Write `reference-b1.json` from Appendix B1, then check it**

Transcribe `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2/research/f35-recommendation.md` Appendix B1, using the rules below. That is the ledger copy; `GovBudget/research/` has no such file. Its lines 510–527 are the B1 header, the 15 counted lines and the "Counted total (15)" row. The rules:
- `lines` holds the 15 counted codes. Each has 12 keys, `"2015"` … `"2026"`, holding $M as JSON numbers with one decimal. `—` becomes `null`, and `0.0` stays `0.0`.
- `totals` holds the same 12 keys from the total row.
- `cumulative` is `116808.4`, `fy2025_enacted` is `12532.3` and `fy2026_request` is `11467.0`.
- The context rows (JSM000, 000999, 0605) are not in the file.
- Write it as `json.dumps(doc, indent=2, ensure_ascii=False) + "\n"`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - data/research/platform_families/f-35/reference-b1.json <<'PY'
import json, sys
from decimal import Decimal
r = json.load(open(sys.argv[1]), parse_float=Decimal)
codes = {"ATA000","F03500","0152","0592","0147","0593","0604800F","0604800N","0604800M","0604810N","0604810M","0604840F","0604840N","0604840M","0207142F"}
fys = [str(y) for y in range(2015, 2027)]
assert sorted(r) == ["cumulative", "fy2025_enacted", "fy2026_request", "lines", "totals"] and set(r["lines"]) == codes
assert all(list(v) == fys for v in r["lines"].values()) and list(r["totals"]) == fys
cells = [x for v in r["lines"].values() for x in v.values()]
print(f"{len(codes)} lines; {len(cells)} cells, {cells.count(None)} null, {sum(1 for x in cells if x == 0)} zero")
print("FY2015-24 totals sum", sum(r["totals"][y] for y in fys[:10]), "cumulative", r["cumulative"])
assert r["fy2025_enacted"] == r["totals"]["2025"] and r["fy2026_request"] == r["totals"]["2026"]
print("line-sum minus total:", " ".join(f"{y} {sum(v[y] for v in r['lines'].values() if v[y] is not None) - r['totals'][y]}" for y in fys))
PY
```

Expected:
```
15 lines; 180 cells, 34 null, 6 zero
FY2015-24 totals sum 116808.4 cumulative 116808.4
line-sum minus total: 2015 -0.1 2016 0.1 2017 0.0 2018 0.0 2019 -0.1 2020 0.1 2021 -0.2 2022 0.0 2023 0.0 2024 0.0 2025 0.0 2026 -0.2
```

The six zeros are 0604840F FY2018–19, 0604840N FY2017–18 and 0604840M FY2017–18. B1's totals round the exact thousands, not the rounded lines. `compare_reference` therefore compares totals with totals and cells with cells, never a line sum with a total.

- [ ] **Step 2: Write `prefill/family.json`**

The object is the §7.2 F-35 column, and `sources` is §7.7's one source. Three things are proposals for the owner to review on the B1 page; piece 4 finalizes them: `scope_note`, `coverage_notes` and the exclusion `label`s. Exactly this content, written with `json.dumps(doc, indent=2, ensure_ascii=False) + "\n"`:

```json
{
  "family": {
    "platform_family": "f-35",
    "short_name": "F-35",
    "history_dataset": "f35_funding_history",
    "on_partial_corpus": "raise",
    "headline": {"measure": "cumulative_actuals", "first_fy": 2015, "last_fy": 2024},
    "scope_note": "Recorded F-35 research, development and procurement budget lines in the imported P-1/R-1 workbooks: the Air Force and Navy aircraft and modification lines, and the F-35 development lines counted by the service that paid. This is a covered-record total, not the program's lifetime cost. Initial spares bought from shared lines, military construction, operating and support, and partner-nation and foreign-buyer money are outside this calculation.",
    "coverage_notes": [
      "Coverage begins with FY2015 actuals in PB2017. Earlier funding, including F-35 development before FY2015, is not represented.",
      "Development lines are counted once, in a development column labelled by the service that paid; they are never divided among the F-35A, F-35B and F-35C.",
      "Historical procurement line numbers change between editions. Each legacy line is matched within its own budget edition through its owner-ratified era decision.",
      "Actuals, current-year figures and requests are separate snapshots. Requests and current-year figures are excluded from the cumulative actuals figure.",
      "Amounts are nominal dollars of total obligational authority (TOA), not contract obligations, cash outlays or inflation-adjusted dollars.",
      "Missing workbook figures are not zero spending. Some current-year columns contain requests adjusted for continuing resolutions rather than final enacted appropriations.",
      "The totals exclude classified funding, military construction, initial spares bought from shared lines, operating and support, and partner-nation and foreign-buyer money."
    ],
    "review_guard": {"exhibits": ["P-1", "R-1"], "title_substrings": ["F-35", "F35", "JSF", "JOINT STRIKE", "F135", "LIGHTNING"]},
    "program_notes": {},
    "variants": [{"id": "A"}, {"id": "B", "note": "F-35B is a Marine Corps jet bought from the Navy's aircraft account"}, {"id": "C", "note": "F-35C includes Marine Corps jets"}],
    "program_tags": [{"tag": "F-35", "mdap_code": "198"}],
    "purpose_tags": ["production", "modifications", "sdd", "block4", "usaf_squadrons"],
    "caveat_ids": ["classified", "construction", "operating_and_support", "spares", "foreign", "cr_years", "nominal_dollars"],
    "exclusions": [
      {"exclusion_id": "initial-spares", "kind": "shared_line", "label": "Initial spares bought from shared lines", "size_text": "F-35 initial spares from shared lines 000999 and 0605: $766.3M in FY2024", "evidence": ["doc:528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e#p175;q=ATA000 / F-35 Squadrons [198]", "src:msar-pb2027"]},
      {"exclusion_id": "milcon", "kind": "outside_scope", "label": "Military construction", "size_text": "Construction: $4,022.7M over the program life, all FY2022 or earlier", "evidence": ["src:msar-pb2027#p92", "src:msar-pb2027#p93"]},
      {"exclusion_id": "operating-support", "kind": "outside_scope", "label": "Operating and support", "size_text": "Operating and support: $1,395.0B TY / $596.4B CY12, through 2083", "evidence": ["src:msar-pb2027#p32"]},
      {"exclusion_id": "partner-share", "kind": "outside_scope", "label": "Partner nations' share of development", "size_text": "Partner nations' share of development: $12.9B over the program life", "evidence": ["src:msar-pb2027#p85", "src:msar-pb2027#p99"]},
      {"exclusion_id": "fms", "kind": "outside_scope", "label": "Foreign buyers' aircraft (FMS)", "size_text": "Foreign buyers' aircraft (FMS): 530 aircraft, $89,475.6M as listed", "evidence": ["src:msar-pb2027#p67", "src:msar-pb2027#p68"]},
      {"exclusion_id": "before-fy2015", "kind": "outside_scope", "label": "Spending before FY2015", "size_text": "Spending before FY2015 is not shown", "evidence": []},
      {"exclusion_id": "classified", "kind": "outside_scope", "label": "Classified funding", "size_text": "Classified funding: unknown", "evidence": []},
      {"exclusion_id": "programming-codes", "kind": "not_a_budget_line", "label": "Programming codes, not budget lines", "size_text": "0204146N and 0204146M are named on the 0147 and 0152 P-40s but exist in no P-1 or R-1 workbook; the ATA000 note's PE 0207142F is a programming code, and the R&D line 0207142F is separate money", "evidence": ["doc:e7e130253786cbd906d4367bc622649fc9ad86a38ce3677da47ad33d9c628ca0#p51;q=Program Elements for Code B Items: 0204146N", "doc:528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e#p55;q=Funding for this exhibit contained in PE 0207142F."]}
    ],
    "aliases": [],
    "contract_routes": null,
    "official_estimates": null,
    "art": null
  },
  "sources": [
    {"source_id": "msar-pb2027", "title": "F-35 Modernized Selected Acquisition Report (MSAR), FY2027 President's Budget", "publisher": "Department of Defense", "url": "https://www.esd.whs.mil/Portals/54/Documents/FOID/Reading%20Room/Selected_Acquisition_Reports/PB_2027_MSARs/F-35_MSAR_FY2027_PB_cleared.pdf", "as_of": "2026-04-21", "sha256": "063345e4a46f7d58cf89356389fb36986e5a0f8c06c716030ead49932e8dca50", "bytes": 1298631, "archived": false, "tier": "G"}
  ]
}
```

The `size_text` strings are §7.7's verbatim. The spares exclusion records only $766.3M FY2024, never the inferred ~$6.3B (publish the smaller true number). The family object carries no `status` and no `published_ruling_id`: `propose` writes `status: draft` (§8.3).

- [ ] **Step 3: Write `prefill/rows.csv` (19 rows, `PREFILL_COLUMNS`)**

Write the header `PREFILL_COLUMNS` in its order, then one row per line of the table below, in table order. Use `csv.DictWriter(lineterminator="\n", quoting=csv.QUOTE_MINIMAL)`.

Fixed on every row:
- `platform_family` = `f-35` and `program_tag` = `F-35`;
- `exhibit`, `account`, `organization` and `code` = the parts of `member_id`;
- `appropriation` = `procurement` for P-1 and `rdte` for R-1;
- `page_slug` = `code` (all 19 have a program page).

Always blank:
- `expected_next_edition`;
- `quantity_bearing`, `quantity_row`, `quantity_notes`;
- `jbook_anchor`, `contract_link_policy`;
- `msar_account`, `msar_funding_source_page`, `msar_shared_flag`;
- `allocation_source`, `allocation_years`;
- `note`.

Each of these is reserved, or barred for the row's role (§7.3, §7.7). Columns a row leaves out of the table are blank too.

**Counted rows** (`role` = `counted`, `verdict` = `approved`, `coverage_expected_from_edition` = `valid_from_edition`, `member_order` = #; `reason` = `owner 2026-10-19: counted member <#> of 15 [F35 §1.1]`):

| # | `member_id` | `display_title` | valid | `era_decision_ids` | `purpose_tag` / `purpose` | `variant_ids` / `variant_scope` / `scope_note` | `services_using` / `paying_org` | `evidence` |
|---|---|---|---|---|---|---|---|---|
| 1 | `P-1:3010F:AF:ATA000` | F-35 | 2017–2026 | `ATA000\|3010F\|\|2017-2023` | production / buy | A / variant / — | USAF / AF | `era:ATA000\|3010F\|\|2017-2023;doc:528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e#p55;q=Line Item MDAP/MAIS Code: 198` |
| 2 | `P-1:3010F:AF:F03500` | F-35 Modifications | 2017–2026 | `F03500\|3010F\|\|2017-2023` | modifications / upgrade | A / variant / — | USAF / AF | `era:F03500\|3010F\|\|2017-2023;src:msar-pb2027#p25` |
| 3 | `P-1:1506N:NAVY:0152` | JSF STOVL | 2017–2026 | `0152\|1506N\|\|2017-2023` | production / buy | B / variant / — | USMC / NAVY | `era:0152\|1506N\|\|2017-2023;doc:e7e130253786cbd906d4367bc622649fc9ad86a38ce3677da47ad33d9c628ca0#p83;q=Line Item MDAP/MAIS Code: 198` |
| 4 | `P-1:1506N:NAVY:0592` | F-35 STOVL Series | 2017–2026 | `0592\|1506N\|\|2017-2023` | modifications / upgrade | B / variant / — | USMC / NAVY | `era:0592\|1506N\|\|2017-2023;src:msar-pb2027#p25` |
| 5 | `P-1:1506N:NAVY:0147` | Joint Strike Fighter CV | 2017–2026 | `0147\|1506N\|\|2017-2023` | production / buy | C / variant / — | USN;USMC / NAVY | `era:0147\|1506N\|\|2017-2023;doc:e7e130253786cbd906d4367bc622649fc9ad86a38ce3677da47ad33d9c628ca0#p51;q=Line Item MDAP/MAIS Code: 198` |
| 6 | `P-1:1506N:NAVY:0593` | F-35 CV Series | 2017–2026 | `0593\|1506N\|\|2017-2023` | modifications / upgrade | C / variant / — | USN;USMC / NAVY | `era:0593\|1506N\|\|2017-2023;src:msar-pb2027#p25` |
| 7 | `R-1:3600F:AF:0604800F` | F-35 EMD | 2017–2023 | — | sdd / develop | A;B;C / shared / S-DEV | USAF;USN;USMC / AF | `src:msar-pb2027` |
| 8 | `R-1:1319N:NAVY:0604800N` | JSF EMD | 2017–2025 | — | sdd / develop | A;B;C / shared / S-DEV | USAF;USN;USMC / NAVY | `src:msar-pb2027` |
| 9 | `R-1:1319N:NAVY:0604800M` | JSF EMD | 2017–2025 | — | sdd / develop | A;B;C / shared / S-DEV | USAF;USN;USMC / USMC | `src:msar-pb2027` |
| 10 | `R-1:1319N:NAVY:0604810N` | JSF Follow-On Modernization | 2017–2020 | — | block4 / develop | A;B;C / shared / S-DEV | USAF;USN;USMC / NAVY | `src:msar-pb2027#p26` |
| 11 | `R-1:1319N:NAVY:0604810M` | JSF Follow-On Modernization | 2017–2020 | — | block4 / develop | A;B;C / shared / S-DEV | USAF;USN;USMC / USMC | `src:msar-pb2027#p26` |
| 12 | `R-1:3600F:AF:0604840F` | F-35 C2D2 | 2020–2026 | — | block4 / develop | A;B;C / shared / S-DEV | USAF;USN;USMC / AF | `src:msar-pb2027` |
| 13 | `R-1:1319N:NAVY:0604840N` | F-35 C2D2 | 2019–2026 | — | block4 / develop | A;B;C / shared / S-DEV | USAF;USN;USMC / NAVY | `src:msar-pb2027` |
| 14 | `R-1:1319N:NAVY:0604840M` | F-35 C2D2 | 2019–2026 | — | block4 / develop | A;B;C / shared / S-DEV | USAF;USN;USMC / USMC | `src:msar-pb2027` |
| 15 | `R-1:3600F:AF:0207142F` | F-35 Squadrons | 2017–2026 | — | usaf_squadrons / develop | A / variant / S-SQ | USAF / AF | `src:msar-pb2027#p27` |

(The `\|` in this table is a Markdown escape; the file holds a bare `|`.)

The links (§7.7, `link_basis` = `inferred`, `link_evidence` = `src:msar-pb2027#p26`):
- row 10 has `successor_member_id` `R-1:1319N:NAVY:0604840N`, and row 13 has `predecessor_member_id` `R-1:1319N:NAVY:0604810N`;
- row 11 has `successor_member_id` `R-1:1319N:NAVY:0604840M`, and row 14 has `predecessor_member_id` `R-1:1319N:NAVY:0604810M`.

The scope notes:
- **S-DEV:** `Development shared by the F-35A, F-35B and F-35C; counted once in the development column by the service that paid, never divided among the variants.`
- **S-SQ** (§7.7, verbatim): `Air Force-only work, counted in the development column by payer, never in the F-35A procurement bucket.`

Row 15 is variant A and Air Force-only, so its `services_using` is `USAF`. §7.7's "the development rows: USAF;USN;USMC" is read as rows 7–14.

**Context and deferred rows.** `member_order` and `coverage_expected_from_edition` are blank, and so are `purpose_tag`, `variant_ids` and `variant_scope`.

| `member_id` | `role` / `verdict` | `display_title` | valid | `purpose` | `services_using` / `paying_org` | `scope_note` | `evidence` | `reason` |
|---|---|---|---|---|---|---|---|---|
| `P-1:3010F:AF:000999` | context / approved | Initial Spares/Repair Parts | 2017–2026 | support | USAF / AF | C-000999 | `era:000999\|3010F\|\|2017-2023;doc:528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e#p175;q=ATA000 / F-35 Squadrons [198]` | `context: shown, never summed [F35 §1.2]` |
| `P-1:1506N:NAVY:0605` | context / approved | Spares and Repair Parts | 2017–2026 | support | USN;USMC / NAVY | C-0605 | `era:0605\|1506N\|\|2017-2023` | `context: shown, never summed [F35 §1.2]` |
| `P-1:3020F:AF:JSM000` | context / approved | Joint Strike Missile | 2024–2026 | buy | USAF / AF | C-JSM000 | `doc:4edf049fb40b58835092f49d2dd60f74cfce4280065b0c6c655f40c7c15ac94d#p99;q=LI JSM000 - Joint Strike Missile` | `context: related line, not counted [F35 §5 Q15]` |
| `R-1:3600F:AF:0207268F` | project_slice / deferred, `project_number` `675365` | F135 Component Improvement Program (project 675365) | 2017–2026 | develop | USAF / AF | D-0207268F | (blank) | `deferred to the project-slice pilot [F35 §1.2, §5 Q15]` |

The context scope notes are §7.7's "substance" column, verbatim:
- **C-000999:** `A shared Air Force spares line. Its P-40/P-18 names "ATA000 / F-35 Squadrons [198]"; the book-stated F-35 amount is FY2024 $446.470M, FY2025 $440.846M, FY2026 $311.759M (Vol I pp.171, 174–175). Never summed.`
- **C-0605:** `A shared Navy spares line. The book states F-35 amounts for 0147 and 0152 (APN BA6-7 p.47). Never summed.`
- **C-JSM000:** `A missile the F-35 carries, not the aircraft. A related line, not counted. It also covers the review guard's "JOINT STRIKE" match.`
- **D-0207268F:** `Project 675365 (F135 Component Improvement Program) inside the shared Air Force engine line 0207268F; it waits for the project-slice pilot.`

Then check the prefill and every hand-written `doc:` ref against fam2, read-only (fam2 is a snapshot, so no SAM guard):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
FAM2_SITE="${GOVBUDGET_PROOFS:?}/fam2/site"
uv run --project . python - data/research/platform_families/f-35/prefill/rows.csv "$FAM2_SITE" <<'PY'
import csv, sys
from collections import Counter
from pathlib import Path
from govbudget.platform_families import PREFILL_COLUMNS, resolve_doc_ref
rows = list(csv.DictReader(open(sys.argv[1], newline="")))
print("header ok:", tuple(rows[0].keys()) == tuple(PREFILL_COLUMNS), "| rows:", len(rows), "|", dict(Counter(r["role"] for r in rows)))
print("member_order:", [r["member_order"] for r in rows if r["role"] == "counted"] == [str(i) for i in range(1, 16)])
A, N, M = ("528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e", "e7e130253786cbd906d4367bc622649fc9ad86a38ce3677da47ad33d9c628ca0", "4edf049fb40b58835092f49d2dd60f74cfce4280065b0c6c655f40c7c15ac94d")
refs = [f"doc:{A}#p55;q=Line Item MDAP/MAIS Code: 198", f"doc:{N}#p83;q=Line Item MDAP/MAIS Code: 198", f"doc:{N}#p51;q=Line Item MDAP/MAIS Code: 198",
        f"doc:{A}#p175;q=ATA000 / F-35 Squadrons [198]", f"doc:{M}#p99;q=LI JSM000 - Joint Strike Missile",
        f"doc:{N}#p51;q=Program Elements for Code B Items: 0204146N", f"doc:{A}#p55;q=Funding for this exhibit contained in PE 0207142F."]
print("doc refs unresolved:", [(r[:24], why) for r in refs if (why := resolve_doc_ref(r, site_dir=Path(sys.argv[2])))])
PY
```

Expected:
```
header ok: True | rows: 19 | {'counted': 15, 'context': 3, 'project_slice': 1}
member_order: True
doc refs unresolved: []
```

An unresolved ref names its reason, a missing file, page or quote. Re-read that page in `$FAM2_SITE/pdfs/<sha>.pdf` and correct the quote. Never drop the ref without a replacement independent signal.

- [ ] **Step 4: `propose` against fam2**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
FAM2_DUCKDB="${GOVBUDGET_PROOFS:?}/fam2/duckdb/govbudget.duckdb"
uv run --project . python -m govbudget platform-families propose --family f-35 --family-json data/research/platform_families/f-35/prefill/family.json --rows data/research/platform_families/f-35/prefill/rows.csv --duckdb "$FAM2_DUCKDB"; echo "exit=$?"
git -C .. status --porcelain -- GovBudget/data-seeds GovBudget/data/research/platform_families; git -C .. diff --quiet -- GovBudget/data-seeds/platform_family_members.csv GovBudget/data-seeds/platform_family_era_lines.csv && echo "members and era-lines CSVs untouched"
```

Expected:
- `platform-families propose: f-35 draft; 19 review row(s), 63 era line(s), 0 held for review -> <REVIEW_ROOT>/f-35/` (Task 7b's format), then `exit=0`;
- ` M GovBudget/data-seeds/platform_families.json` and `?? GovBudget/data/research/platform_families/f-35/`;
- `members and era-lines CSVs untouched`.

On a refusal (`platform-families propose: ERROR — …`, exit 2), nothing is written. Every error is listed: fix the prefill and re-run.

Then check what `propose` wrote:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - <<'PY'
import csv, json
from govbudget.platform_families import REVIEW_COLUMNS, ERA_LINE_COLUMNS, load_registry, family_hash, REGISTRY_JSON
reg = load_registry(); f35 = reg["f-35"]
doc = json.loads(REGISTRY_JSON.read_text()); fo = next(x for x in doc["families"] if x["platform_family"] == "f-35")
print("f-35:", f35.status, "published_ruling_id" in fo, "| member rows", len(f35.members))
src = reg.sources["msar-pb2027"]; print("msar:", src.tier, src.archived, src.sha256[:8], src.bytes)
print("published:", [f.platform_family for f in reg.published()], "| family_sha256", family_hash(doc, "f-35"))
d = "data/research/platform_families/f-35/"
rv = list(csv.DictReader(open(d + "review.csv", newline=""))); el = list(csv.DictReader(open(d + "review_era_lines.csv", newline="")))
print("review.csv:", tuple(rv[0]) == tuple(REVIEW_COLUMNS), len(rv), "| era lines:", tuple(el[0]) == tuple(ERA_LINE_COLUMNS), len(el), sorted({r["decision_id"].split("|")[0] for r in el}))
k = {r["code"]: r["headline_actuals_k"] for r in rv if r["role"] == "counted"}
print("sort dollars:", k["ATA000"], k["0152"], k["0147"], k["0604810N"], "| drift shas:", sum(len(r["drift_sha256"]) == 64 for r in rv if r["role"] == "counted"))
print("0604810N titles_seen:", next(r["titles_seen"] for r in rv if r["code"] == "0604810N"))
PY
```

Expected:
```
f-35: draft False | member rows 0
msar: G False 063345e4 1298631
published: ['f-15'] | family_sha256 <64 hex>
review.csv: True 19 | era lines: True 63 ['0147', '0152', '0592', '0593', 'ATA000', 'F03500']
sort dollars: 53368317.000 22654924.000 20097427.000 194195.000 | drift shas: 15
0604810N titles_seen: 2017: Joint Strike Fighter Follow On Development - Navy; 2018: Joint Strike Fighter Follow On Modernization (FoM) - Navy; 2019: Joint Strike Fighter Follow On Modernization (FoM) - Navy; 2020: Joint Strike Fighter Follow On Modernization (FoM) - Navy
```

`headline_actuals_k` is written `f"{d:.3f}"` (Task 7b), so the sort dollars print `53368317.000 22654924.000 20097427.000 194195.000`; the values are whole thousands (re-measured 2026-10-21). `titles_seen` follows the era-seed format of §7.3.

- [ ] **Step 5: Stage 1 and the facade still load; the F-15 is untouched; the draft is undecided, never failed**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_registry_parity.py tests/test_f15_funding_history.py tests/test_f15_era_identity.py tests/test_capture_f15_fixtures.py tests/test_budget_pdf_receipts.py tests/test_platform_families_loader.py -q 2>&1 | tail -1
uv run --project . python -m govbudget platform-families check --duckdb "$P/fam2/duckdb/govbudget.duckdb" --site-dir "$P/fam2/site" > "$P/fam2-logs/check-f35-draft.txt" 2>&1; echo "check exit=$?"; cat "$P/fam2-logs/check-f35-draft.txt"
```

Expected:
- `… passed`, with 0 failed;
- `check exit=0` (no failure; without `--strict`, undecided entries do not fail);
- `stale` 0;
- every `undecided` entry is an F-35 guard line, and none is an F-15 line. There are 150 on the live-lake measurement: 87 code-keyed and 63 era-keyed. A draft has no member rows, so all its guard matches are undecided (§9.2).

- [ ] **Step 6: Render B1 against fam2 (runs `preview --draft` first)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; B0=$(python3 -c "import json; print(json.load(open('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/manifest.json'))['built_at'])")
uv run --project . python -m govbudget platform-families render --family f-35 --batch B1 --duckdb "$P/fam2/duckdb/govbudget.duckdb" --site-dir "$P/fam2/site"; echo "exit=$?"
ls tmp/platform-families/f-35/B1.html tmp/platform-families/f-35/B1.json; ls -d "$P/fam2-preview-f-35-B1"
[ "$(python3 -c "import json; print(json.load(open('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/manifest.json'))['built_at'])")" = "$B0" ] && [ ! -e /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/f35_funding_history.json ] && echo "live data/site untouched"
grep -c "yes this is good, except we should break out the sub contractors" tmp/platform-families/f-35/B1.html
```

Expected:
- `platform-families render: f-35 B1: 19 row(s), 0 difference(s) -> <page> (manifest <manifest>)` (Task 7c's format), then `exit=0`;
- the two files, then `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fam2-preview-f-35-B1`;
- `live data/site untouched`;
- a count ≥ 1: the header quotes the 2026-10-19 reply.

A preview error, or a difference whose cause is "proposal row", writes no page. In that case, fix the prefill (never the numbers), re-run Steps 3–6 and render again. A difference caused by "lake since 2026-10-19" is shown on the page; none is expected, because the series equals B1 (Measured).

Then check the manifest:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - <<'PY'
import hashlib, json
from govbudget.platform_families import family_hash, REGISTRY_JSON
m = json.load(open("tmp/platform-families/f-35/B1.json"))
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
d = "data/research/platform_families/f-35/"
print(m["schema_version"], m["platform_family"], m["batch"], len(m["rows"]))
print("shas:", m["review_sha256"] == sha(d + "review.csv"), m["review_era_lines_sha256"] == sha(d + "review_era_lines.csv"), m["family_sha256"] == family_hash(json.loads(REGISTRY_JSON.read_text()), "f-35"))
print("order:", [r["code"] for r in m["rows"]])
basis = {(2025, "enacted", 2026), (2026, "request", 2026)} | {(fy, "actuals", fy + 2) for fy in range(2015, 2025)}
pts = {y["fy"]: y["total_thousands"] for y in m["preview"]["years"] if (y["fy"], y["kind"], y["edition"]) in basis}
print("years:", [str(pts[fy]) for fy in sorted(pts)]); print("cumulative:", m["preview"]["cumulative_thousands"], "| differences:", m["preview"]["differences"])
PY
shasum -a 256 tmp/platform-families/f-35/B1.json
```

Expected:
```
1 f-35 B1 19
shas: True True True
order: ['ATA000', '0152', '0147', '0604840F', '0604840M', '0604840N', 'F03500', '0604800F', '0604800M', '0604800N', '0207142F', '0592', '0593', '0604810M', '0604810N', '0605', '000999', 'JSM000', '0207268F']
years: ['8276453.000', '11159349.000', '10767556.000', '12724876.000', '11743209.000', '12187056.000', '12744466.000', '11889941.000', '11845845.000', '13469616.000', '12532299.000', '11466954.000']
cumulative: 116808367.000 | differences: []
```

§8.2 fixes the counted rows' order: by FY2015–24 dollars, largest first, ending with 0604810N at 194.2. It also fixes that the context rows and then the deferred row follow. Within the context rows the order is `member_id` (Task 7c): `P-1:1506N:NAVY:0605`, `P-1:3010F:AF:000999`, `P-1:3020F:AF:JSM000`. The manifest writes thousands as `f"{d:.3f}"` strings; the mart totals are whole thousands (re-measured 2026-10-21). The manifest's sha256 is the value Task 8b quotes.

- [ ] **Step 7: Copy the figures into the ledger**

Write `…/families-piece2/b1-preview.md`, dated the day this step runs. It holds:
- the page path, the manifest path and its sha256;
- `review_sha256`, `review_era_lines_sha256` and `family_sha256`;
- a table with one row per FY: FY2015–FY2024 actuals, FY2025 enacted and FY2026 request. Columns: the preview's thousands; the preview in $M (`ROUND_HALF_UP`, 0.1); B1's $M; match yes or no;
- the cumulative: 116,808,367 thousand, 116,808.4 $M, B1 116,808.4;
- the differences, `none`;
- the counted rows in page order, each with its FY2015–24 thousands.

If B1 is deferred, this file and the page are the only places the figures live (§8.2).

- [ ] **Step 8: Commit the draft F-35**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/data/research/platform_families/f-35/prefill/family.json GovBudget/data/research/platform_families/f-35/prefill/rows.csv GovBudget/data/research/platform_families/f-35/reference-b1.json GovBudget/data/research/platform_families/f-35/review.csv GovBudget/data/research/platform_families/f-35/review_era_lines.csv GovBudget/data-seeds/platform_families.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "data(families): the F-35 as a draft family — prefill, propose against fam2 (19 rows, 63 era lines) and the B1 reference (piece 2 §7.7, §8.2)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: the commit, `6 files changed`.

---

### Task 8b ★: B1, the owner's answer, then `ratify` or the recorded deferral

**Spec:** §8.2 (the answer, the deferral), §8.3 (`answer`, `ratify`, `check`), §9.1 rules 16, 22 and 23, §9.2 item 5, §19 rows 7, 21, 25 and 26.

**Files:**
- Create, on an answer: `data/research/platform_families/f-35/batches/B1.json`, written by `answer`.
- Generated and committed, on a ratify:
  - `data-seeds/platform_families.json` (F-35 `ratified`, ruling `R-DEC-FAM-F35-B1`);
  - `data-seeds/platform_family_members.csv` (+19 rows);
  - `data-seeds/platform_family_era_lines.csv` (+63 rows).
- Ledger: `…/families-piece2/work/b1-answer-input.json` and the `B1:` line in `progress.md`.

**Interfaces:**
- Consumes (I-REV):
  - `platform-families answer --family <id> --batch B<n> --answers <file>`;
  - `platform-families ratify --family <id> --batch B<n> --decided-on DATE [--duckdb] [--site-dir]`;
  - `platform-families check [--strict] [--duckdb] [--site-dir]`;
  - `AMENDABLE_COLUMNS`;
  - the answer input `{batch, decided_on, owner_reply, rows: {member_row_id: {<AMENDABLE_COLUMNS subset>} | {"defer": true}}}`.
- Consumes from Task 8a: the B1 page, the manifest and its sha256.
- Produces B1's outcome. Task 9b Step 7 and Task 10c quote it from `progress.md`:
  - `B1: ratified <decided_on>; manifest sha256 <hex>; amendments: none|<list>; ruling R-DEC-FAM-F35-B1`, or
  - `B1: deferred by the owner <date>: "<reply>"`.

- [ ] **Step 1: ★ Put the B1 page in front of the owner**

Send the page (`tmp/platform-families/f-35/B1.html`) to the owner. Fill `<…>` from `b1-preview.md` and say:

"The F-35 review page (batch R-DEC-FAM-F35-B1) is ready. With the 15 lines you approved on 2026-10-19, the F-35 totals come to $116,808.4M of FY2015–24 recorded actuals: FY2015 $8,276.5M … FY2024 $13,469.6M, with FY2025 enacted at $12,532.3M and the FY2026 request at $11,467.0M. That matches the figures you reviewed, year by year; differences: <none>. The page also lists:
- the edition range, evidence and drift hash of each line;
- 3 related lines that are shown and never added in (000999 and 0605 spares, JSM000);
- the F135 engine-improvement project, held for later;
- the 8 exclusions, each with its cited size.

Subcontractors stay a piece-7 commitment. Your yes marks the F-35 approved, but still not public: its page comes in piece 4. You can also change a row's role, tags, scope note or evidence, hold a row back, or put the whole batch off; piece 2 ships either way. Your reply is recorded word for word."

Wait for an explicit answer. No reply is not an answer. The reply's date is `decided_on`.
- **A change to an identity, edition range, lake-measured column or family field** is not an answer amendment (§8.2, Review Focus 1). Make it in Task 8a Steps 2–3, re-run Task 8a Steps 4–8 (a new page and a new manifest), and ask again.
- **The whole batch put off:** go to Step 5.

- [ ] **Step 2: `answer` (ratify branch)**

Write `…/families-piece2/work/b1-answer-input.json`:
- `{"batch": "B1", "decided_on": "<YYYY-MM-DD of the reply>", "owner_reply": "<the reply, verbatim>", "rows": {}}`;
- `rows` maps each amended `member_row_id` (from `review.csv`) to its `AMENDABLE_COLUMNS` changes, or to `{"defer": true}`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python -m govbudget platform-families answer --family f-35 --batch B1 --answers /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2/work/b1-answer-input.json; echo "exit=$?"
uv run --project . python -c "import json,hashlib; a=json.load(open('data/research/platform_families/f-35/batches/B1.json')); print(a['batch'], a['decided_on'], len(a['rows']), a['manifest_sha256'] == hashlib.sha256(open('tmp/platform-families/f-35/B1.json','rb').read()).hexdigest(), a['review_sha256'] == hashlib.sha256(open('data/research/platform_families/f-35/review.csv','rb').read()).hexdigest())"
```

Expected: `platform-families answer: f-35 B1 -> <REVIEW_ROOT>/f-35/batches/B1.json; next: platform-families ratify --family f-35 --batch B1 --decided-on <decided_on>` (Task 7d's format), `exit=0`, then `B1 <decided_on> <amended row count> True True`. A refusal (exit 2) names the unknown key, row, sha, blank reply or date; fix the input file, never `review.csv`.

- [ ] **Step 3: `ratify` against fam2**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; D=$(uv run --project . python -c "import json; print(json.load(open('data/research/platform_families/f-35/batches/B1.json'))['decided_on'])")
uv run --project . python -m govbudget platform-families ratify --family f-35 --batch B1 --decided-on "${D:?}" --duckdb "$P/fam2/duckdb/govbudget.duckdb" --site-dir "$P/fam2/site"; echo "exit=$?"
uv run --project . python - "$D" <<'PY'
import csv, subprocess, sys
from collections import Counter
from govbudget.platform_families import load_registry, MEMBERS_CSV, ERA_LINES_CSV
reg = load_registry(); f, r = reg["f-35"], reg.rulings["R-DEC-FAM-F35-B1"]
print(f.status, r.kind, r.decided_by, r.decided_on == sys.argv[1])
print(sorted(Counter((m.role, m.verdict) for m in f.members).items()), [m.member_order for m in f.counted] == list(range(1, len(f.counted) + 1)))
print({m.ruling_id for m in f.members}, {m.decided_on for m in f.members} == {sys.argv[1]}, len(f.era_lines))
head = lambda p: [row for row in csv.DictReader(subprocess.run(["git", "show", f"HEAD:GovBudget/{p.relative_to(p.parents[1])}"], capture_output=True, text=True, check=True).stdout.splitlines())]
now = lambda p: list(csv.DictReader(open(p, newline="")))
print("F-15 rows unchanged:", [x for x in now(MEMBERS_CSV) if x["platform_family"] == "f-15"] == head(MEMBERS_CSV), [x for x in now(ERA_LINES_CSV) if x["platform_family"] == "f-15"] == head(ERA_LINES_CSV))
PY
```

Expected, with no deferred or amended counted row:
- `platform-families ratify: f-35 ratified as R-DEC-FAM-F35-B1; 19 member row(s), 63 era line(s) -> data-seeds/` (Task 7d's format; the deferred row 0207268F is written too, R13), then `exit=0`;
- `ratified batch owner True`;
- `[(('context', 'approved'), 3), (('counted', 'approved'), 15), (('project_slice', 'deferred'), 1)] True`;
- `{'R-DEC-FAM-F35-B1'} True 63`;
- `F-15 rows unchanged: True True`.

The answer may have held a row back. Then `member_order` is renumbered 1..n in review order, and the counts drop by that row. Before Task 8b, HEAD's CSVs hold only the F-15 rows.

On a refusal, nothing is written, and every error is listed. Report them to the owner and stop. Two refusals to expect:
- a counted row held back leaves its guard lines uncovered, which stage 2 refuses for a `ratified` family (§9.2 item 5);
- a lake hash that differs from the review-time `drift_sha256`.

- [ ] **Step 4: `check` against fam2, and the registry-reading tests**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"
uv run --project . python -m govbudget platform-families check --duckdb "$P/fam2/duckdb/govbudget.duckdb" --site-dir "$P/fam2/site" > "$P/fam2-logs/check-f35-ratified.txt" 2>&1; echo "check exit=$?"; cat "$P/fam2-logs/check-f35-ratified.txt"
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_registry_parity.py tests/test_f15_funding_history.py tests/test_f15_era_identity.py tests/test_capture_f15_fixtures.py tests/test_budget_pdf_receipts.py tests/test_platform_families_loader.py tests/test_platform_families_cli.py tests/test_verify_families.py -q 2>&1 | tail -1
```

Expected:
- `check exit=0`. The F-35 is reported `ratified` with no failure, and `stale` is 0;
- the only `undecided` entry is the recorded deferred row `f-35|R-1:3600F:AF:0207268F|2017-2026`. No F-15 entry appears;
- `… passed`, with 0 failed.

- [ ] **Step 5: Commit, or record the deferral**

**Ratify branch:**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/data-seeds/platform_families.json GovBudget/data-seeds/platform_family_members.csv GovBudget/data-seeds/platform_family_era_lines.csv GovBudget/data/research/platform_families/f-35/batches/B1.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "data(families): the owner ratifies F-35 batch B1 (R-DEC-FAM-F35-B1) — ratified, never exported (piece 2 §8.2)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `4 files changed`. Then add to `progress.md`:
- `B1: ratified <decided_on>; manifest sha256 <Task 8a Step 6's>; amendments: none|<member_row_id: columns, …>; ruling R-DEC-FAM-F35-B1`.

**Deferral branch** (the owner put B1 off): run no tool.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && git -C .. status --porcelain -- GovBudget/data-seeds GovBudget/data/research/platform_families | grep -v '^??'; uv run --project . python -c "from govbudget.platform_families import load_registry; f=load_registry()['f-35']; print(f.status, len(f.members), len(f.era_lines))"
```

Expected: no status lines, then `draft 0 0`. Nothing about the F-35 reaches the members or era-lines CSVs. Add one line to `progress.md`:
- `B1: deferred by the owner <date>: "<reply verbatim>"`.

---

### Task 9a: Proof — the rule file, the A worktree, the exports and the diffs

**Spec:** §14 steps 2–6, §16, §2 (success criteria), §17 risk 9; D1, D15.

**Files:**
- Create: `docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json`.
- Proof state (D15):
  - `$GOVBUDGET_PROOFS/fam2-A`, `fam2-B` and `fam2-B2` (APFS clones of `fam2`);
  - `fam2-logs/{a_sha.txt, b_sha.txt, export-*.log, diff-control.txt, noise-B-B2.json, diff-code.txt, diff-code-report.json, sidecars.txt, f15-era-identity.txt, fact-stability.txt, link-coverage-A.txt, link-coverage-B.txt}`.
- The A worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fam2-proof-a`, detached at A and kept until Task 10c's cleanup offer.

**Interfaces:**
- Consumes:
  - `govbudget proof diff A B [--control --write-noise FILE | --noise-from FILE] [--expect RULES] [--report FILE]`. Its last line is `proof diff: EQUAL|DIFFERENT`, or `PASS|FAIL` with `--expect`, and each rule prints `rule <i> [<path>] matched <n>: <why>`.
  - The rule-file keys `path, why, status, pointer, change, required`, read by `govbudget.proof.load_expectations`.
  - `scripts/era/fact_stability.py`'s `compare_citations(a, b, f15_leaves, *, expected_f15, noise_classes)` and `compare_decade_rows(a_parquet, b_parquet)`.
  - `govbudget link-coverage --site-dir DIR --baseline FILE`.
  - `index_projection(registry) -> dict` (I-REG) and the facade's `_json_bytes` (I-FACADE).
  - Task 1's A and fam2; Task 8b's outcome.
- Produces: `fam2-A/site`, `fam2-B/site`, `fam2-B2/site`, `noise-B-B2.json`, and `a_sha.txt`/`b_sha.txt`. Task 9b and Task 10a use them.

**Measured (2026-10-21):**
- **`fact_stability.py` as a CLI cannot read a no-change A/B.** Its S4 rule expects every one of the F-15's 72 A1 era leaves to move `pe_bli` null → code and `retrieved_at` space → `T`. On two identical trees it reports those 72 as `changed … f15_restamp` and FAIL; `compare_citations` was run on the live `citations.json` against itself. Step 9 therefore calls its two functions with an empty leaf map (`f15_leaves={}`, `expected_f15=0`), which demands zero missing and zero changed facts.
- **The export CLI prints no `json_files`.** `cmd_export_site`'s summary line omits it, so the +1 is read from `manifest.json` and the json file count (Step 7). Task 5's test pins the return value.

- [ ] **Step 1: Preconditions**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
LEDGER=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2
git -C .. status --porcelain -- GovBudget | grep -v '^??'; echo "(tracked changes above: expect none)"; grep -E '^(D1|A|B1): ' "$LEDGER/progress.md"
A=$(git merge-base main HEAD); grep -q "^A: $A " "$LEDGER/progress.md" && echo "A unchanged since Task 1: $A"
LIVE=$(curl -s https://fiscalreceipts.com/.build-meta.json | python3 -c "import json,sys; print(json.load(sys.stdin)['git_head'])") && git -C .. diff --quiet "$LIVE" "$A" -- GovBudget/src GovBudget/dbt GovBudget/data-seeds GovBudget/scripts GovBudget/site && echo "A's code equals the deployed $LIVE"
git -C .. diff --quiet "$A" HEAD -- GovBudget/tests/test_f15_funding_history.py GovBudget/tests/test_f15_era_identity.py GovBudget/tests/test_capture_f15_fixtures.py GovBudget/tests/fixtures/f15 'GovBudget/tests/test_verify_era_map*.py' GovBudget/tests/test_export_era_line_map.py GovBudget/site/scripts/gates/__tests__/f15-page-snapshot.test.mjs GovBudget/src/govbudget/verify_era_map.py GovBudget/scripts/era/capture_f15_fixtures.py GovBudget/scripts/era/review_batch_page.py 'GovBudget/site/src/lib/f15-*' GovBudget/site/src/app GovBudget/site/src/components && echo "frozen files byte-unchanged on the branch (no page code touched, §3)"
git -C .. diff --stat "$A" HEAD -- GovBudget/dbt GovBudget/migrations | tail -1; echo "(dbt/migrations diff above: expect none)"
```

Expected:
- no tracked change;
- the `D1:`, `A:` and `B1:` lines;
- `A unchanged since Task 1: <sha>`;
- `A's code equals the deployed <sha>`;
- `frozen files byte-unchanged on the branch (no page code touched, §3)`;
- no dbt or migration diff.

If A moved (main advanced again), stop: the proof would mix that commit into the A/B. If the deployed code differs from A, someone deployed after Task 1: stop and read it.

- [ ] **Step 2: Write the rule file (exactly §16) and commit it**

`docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json`:

```json
[
  {"path": "json/families/index.json", "status": ["only_b"], "required": true, "why": "piece 2 §12, §16: the families index (published families only, pointers, no amounts), written by export_family_histories in the same staging pass"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/json_sidecars", "change": ["changed"], "required": true, "why": "piece 2 §16: json_sidecars counts json/families/index.json, exactly +1 (Task 9a Step 7 asserts B - A = 1)"}
]
```

Nothing else may differ (§16 "Must be identical"), so no other rule exists.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python -c "from govbudget.proof import load_expectations; r=load_expectations('docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json'); print(len(r), [x['path'] for x in r], all(x['required'] for x in r))"
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(plan): the piece-2 A/B rule list (§16: index.json only in B; json_sidecars +1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `2 ['json/families/index.json', 'manifest.json'] True`, then the commit (`1 file changed`).

**On a re-take** (Task 10a Step 1 or Step 2 sends you back here), the rule file is already committed. Write it as above, then run this from `GovBudget/`: `git ls-files --error-unmatch docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json > /dev/null && git diff --quiet HEAD -- docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json && echo "rule file committed and unchanged"`. If it prints that line, run the `load_expectations` line alone and expect its same output, with no commit: `git commit` would print `nothing to commit` and exit 1. Otherwise run the block as written.

- [ ] **Step 3: Record A and B; check out A with its own dbt manifest**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"; git merge-base main HEAD > "$L/a_sha.txt"; git rev-parse HEAD > "$L/b_sha.txt"; cat "$L/a_sha.txt" "$L/b_sha.txt"
A=$(cat "$L/a_sha.txt") && cd .. && git worktree add --detach /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fam2-proof-a "${A:?}" && cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fam2-proof-a/GovBudget && uv sync --frozen > /dev/null 2>&1 && source scripts/era/env.sh && GOVBUDGET_DUCKDB="$GOVBUDGET_PROOFS/fam2-dbt-parse-a.duckdb" uv run --project . dbt parse --project-dir dbt --profiles-dir dbt > "$GOVBUDGET_PROOFS/fam2-logs/dbt-parse-a.log" 2>&1; echo "parse exit=$?"; test ! -e "$GOVBUDGET_PROOFS/fam2-dbt-parse-a.duckdb" && echo no-warehouse-opened
uv run --project . python - /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/dbt/target/manifest.json dbt/target/manifest.json <<'PY'
import json, sys
n = [sum(1 for x in json.load(open(p))["nodes"].values() if x.get("resource_type") == "test") for p in sys.argv[1:]]
print(f"dbt test nodes: B {n[0]}, A {n[1]}"); sys.exit(0 if n[0] == n[1] else 1)
PY
echo "count check exit=$?"; git log -1 --format='%h %s'
```

Expected:
- the two shas;
- `Preparing worktree (detached HEAD …)`;
- `parse exit=0` and `no-warehouse-opened`;
- `dbt test nodes: B <n>, A <n>`, equal to Task 1's `dbt-tests:`, then `count check exit=0`;
- A's subject.

The receipt cache speed-up for the exports is optional. To use it, copy `tmp/pdfs/*-program-pages-v1.json` from this worktree into `fam2-proof-a/GovBudget/tmp/pdfs/`, as Task 25b Step 4 of the follow-ups did.

- [ ] **Step 4: Three exports on fam2 (A, B and the control B2)**

Snapshot clones are exempt from the SAM guard. Each export takes about 15 minutes.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"
for d in fam2-A fam2-B fam2-B2; do [ -e "$P/$d" ] && { echo "STOP: $P/$d exists"; exit 1; }; cp -c -R "$P/fam2" "$P/$d"; done
(cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fam2-proof-a/GovBudget && source "$P/fam2/env.sh" "$P/fam2-A" && uv run --project . python -m govbudget export-site) > "$L/export-fam2-A.log" 2>&1; echo "fam2-A exit=$?"; tail -2 "$L/export-fam2-A.log"
for d in fam2-B fam2-B2; do (source "$P/fam2/env.sh" "$P/$d" && uv run --project . python -m govbudget export-site) > "$L/export-$d.log" 2>&1; echo "$d exit=$?"; tail -2 "$L/export-$d.log"; done
```

Expected: three `exit=0`, each followed by its `budget PDF receipts: …` and `export-site: <d> datasets, <N> citations, … -> …/.proofs/<dir>/site` lines. The `<N>` is the same in all three: `index.json` carries no fact. It is A's citation count on fam2, which already lacks the facts the link fix's release retires (79 by its runbook at round 2, plus round 3's 10 F03500 link facts; Task 7a Measured). No check pins that number: the three exports are compared with each other.

What stops the step:
- **A `RegistryError`** (from stage 2 or 3), or "family history requires every counted workbook member": read it; never change the registry to pass it.
- **Stage-3 leaf expansion firing on the F-15:** stop and report (§9.3).
- **`link_award_keys is missing or incomplete …`** (from `_require_link_award_keys`, A's and B's code alike): fam2 predates the link fix's round-2 live build, which Task 1 Steps 1 and 5 should have caught. Stop; never run against such a warehouse.

The link fix's flows rule makes each export about half a minute slower (its fix report: about +15% on the flows query, over 310 programs). An `export-site: WARNING — flows/… names no award` line would appear in A's log and B's alike; the link fix measured none on the live lake.

- [ ] **Step 5: The control, which must read EQUAL**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"
uv run --project . python -m govbudget proof diff "$P/fam2-B/site" "$P/fam2-B2/site" --control --write-noise "$L/noise-B-B2.json" > "$L/diff-control.txt" 2>&1; echo "control exit=$?"; tail -6 "$L/diff-control.txt"; ls "$L/noise-B-B2.json"
```

Expected: `control exit=0`, then `changed 0 · only in A 0 · only in B 0` and any float-noise or reorder lines, then `proof diff: EQUAL`, and the noise file exists. On `DIFFERENT`, stop: no judged diff can be read without it.

- [ ] **Step 6: Code A/B, which must pass the rule file**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"
uv run --project . python -m govbudget proof diff "$P/fam2-A/site" "$P/fam2-B/site" --noise-from "$L/noise-B-B2.json" --expect docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json --report "$L/diff-code-report.json" > "$L/diff-code.txt" 2>&1; echo "exit=$?"; grep -E "changed [0-9]|^  rule |UNEXPECTED|UNMET|^proof diff:" "$L/diff-code.txt"
```

Expected:
```
exit=0
  identical … · changed 1 · only in A 0 · only in B 1
  rule 0 [json/families/index.json] matched 1: piece 2 §12, §16: …
  rule 1 [manifest.json] matched 1: piece 2 §16: …
proof diff: PASS
```

A FAIL names each unexpected path. Stop and explain it; never widen the rule file without an owner-approved spec change (§16).

- [ ] **Step 7: Exactly +1, the index's content, the F-15 pin, and no leak**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"
uv run --project . python - "$P/fam2-A/site" "$P/fam2-B/site" <<'PY' | tee "$L/sidecars.txt"
import json, sys
from pathlib import Path
from govbudget.f15_funding_history import _json_bytes
from govbudget.platform_families import index_projection, load_registry
a, b = map(Path, sys.argv[1:3])
na, nb = (json.loads((s / "manifest.json").read_text())["json_sidecars"] for s in (a, b))
fa, fb = ({str(p.relative_to(s / "json")) for p in (s / "json").rglob("*.json")} for s in (a, b))
print(f"json_sidecars A {na:,} B {nb:,} (B - A = {nb - na}); json files only in B {sorted(fb - fa)}, only in A {sorted(fa - fb)}")
raw = (b / "json/families/index.json").read_bytes(); idx = json.loads(raw)
print("index:", [f["platform_family"] for f in idx["families"]], len(idx["families"][0]["members"]), idx["schema_version"], "| equals the projection:", raw == _json_bytes(index_projection(load_registry())))
PY
for d in fam2-A fam2-B; do H=$(shasum -a 256 "$P/$d/site/json/f15_funding_history.json" | cut -d' ' -f1); [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ] && echo "$d F-15 history matches the pin" || echo "STOP: $d F-15 history $H"; done
ls "$P/fam2-B/site/json/f35_funding_history.json" 2>/dev/null | wc -l; grep -rlF -e 'f35_funding_history' -e 'reviewed F-35 members' -e 'f-35|' "$P/fam2-B/site/json" | wc -l
```

Expected:
```
json_sidecars A <a> B <a+1> (B - A = 1); json files only in B ['families/index.json'], only in A []
index: ['f-15'] 8 1 | equals the projection: True
fam2-A F-15 history matches the pin
fam2-B F-15 history matches the pin
0
0
```

`index.json` lists the F-15 alone with its 8 members, under schema 1. The F-35, `draft` or `ratified`, appears nowhere. `verify-families` leg c (Task 9b) runs the full D9 scan, `citations.parquet` included.

- [ ] **Step 8: V5 on B's code**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_era_identity.py -v 2>&1 | tee "${GOVBUDGET_PROOFS:?}/fam2-logs/f15-era-identity.txt" | tail -6
```

Expected: the 4 tests (pin, golden, fresh state, sensitivity) `PASSED`, then `4 passed`.

- [ ] **Step 9: Fact stability, A vs B (zero missing, moved or changed)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"
uv run --project . python - "$P/fam2-A/site" "$P/fam2-B/site" "$L/noise-B-B2.json" <<'PY' | tee "$L/fact-stability.txt"
import json, sys
from pathlib import Path
sys.path.insert(0, "scripts/era")
from fact_stability import compare_citations, compare_decade_rows
from govbudget.proof import load_noise_classes
a, b, noise = map(Path, sys.argv[1:4])
ca, cb = (json.loads((s / "json/citations.json").read_text()) for s in (a, b))
c = compare_citations(ca, cb, {}, expected_f15=0, noise_classes=load_noise_classes(noise))
d = compare_decade_rows(a / "data/budget_lines_decade.parquet", b / "data/budget_lines_decade.parquet")
print(f"citations: A {c['a_facts']:,}, B {c['b_facts']:,}, new in B {c['new_in_b']}, missing {len(c['missing'])}, changed {len(c['changed'])}")
print(f"budget_lines_decade: A {d['a_rows']:,} rows, B {d['b_rows']:,} rows, A rows not in B {d['lost']}, schema {'equal' if d['schema_equal'] else 'DIFFERS'}")
print(f"equivalent under proof diff's noise rules: {c['noise_equivalent']}; reorder classes trusted: {len(c['reorder_classes_trusted'])}")
print("fact-stability (no F-15 restamp expected):", "PASS" if c["ok"] and d["ok"] and c["new_in_b"] == 0 else "FAIL")
PY
```

Expected:
- `citations: A <N>, B <N>, new in B 0, missing 0, changed 0`, with Step 4's `<N>`;
- `budget_lines_decade: A <r> rows, B <r> rows, A rows not in B 0, schema equal`;
- the noise line;
- `fact-stability (no F-15 restamp expected): PASS`.

- [ ] **Step 10: Link coverage against the committed baseline, A and B alike**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"
for d in A B; do uv run --project . python -m govbudget link-coverage --site-dir "$P/fam2-$d/site" --baseline data/research/link_coverage/baseline.json > "$L/link-coverage-$d.txt" 2>&1; echo "$d exit=$?"; done
diff <(sed "s#$P/fam2-A#SITE#g" "$L/link-coverage-A.txt") <(sed "s#$P/fam2-B#SITE#g" "$L/link-coverage-B.txt") && echo "link coverage identical"; tail -3 "$L/link-coverage-B.txt"
```

Expected: `A exit=0`, `B exit=0`, `link coverage identical`, and B's summary lines. The percentages are the baseline's.

---

### Task 9b: Proof — the gates, the site build, the page snapshot, the weight, and the proof note

**Spec:** §14 steps 7–10, §2 (success criteria), §4 anti-goal 1 (zero added page bytes), §13; D8 and K1 (leg (r) passes here first).

**Files:**
- Create: `docs/superpowers/reviews/families-piece2-proof.md`.
- Proof logs: `fam2-logs/{gate-*.log, verify-phase5.log, verify-phase5-runtime.txt, evals.log, site-build-B.log, site-verify-B.log, vitest-B.log, site-B/, site-build-A.log, site-A/, weights.txt, pytest.txt, w1.txt}`.
- Local only:
  - this worktree's `data/{site,duckdb,parquet}` links, pointed at `fam2-B` and then back;
  - the A worktree's `site/node_modules` and its `data/{site,duckdb,parquet}` links (pointed at `fam2-A`);
  - both `site/out/` trees;
  - `site/public/llms.txt`, restored.

**Interfaces:**
- Consumes:
  - Task 9a's clones, `noise-B-B2.json` and `a_sha.txt`/`b_sha.txt`;
  - `verify-families [--legs abc] [--site-dir] [--duckdb]`, whose last line is `verify-families: PASS|FAIL`;
  - `verify-phase5`, whose assembly now includes `verify-families` (Task 7a);
  - `program-skeleton` leg (r) (Task 7e) — leg (q) is the link fix's;
  - `site/scripts/f15-page-snapshot.mjs`;
  - Task 8b's `B1:` line;
  - after a re-take, Task 10a's `release-pins:` and `release-retake:` lines in `progress.md`.
- Produces:
  - the proof note;
  - `fam2-logs/verify-phase5-runtime.txt`, read by Task 10a's timing guard;
  - the proven site tree `fam2-B/site`, which Task 10a's release-state diff compares against.

**Measured (2026-10-21):**
- **The F-15 page weight.** `/families/f-15/` was 705,056 / 69,328 on the `1256ec35` build, against 725,000 / 70,000 (`build.mjs:288`, the `{ label: "/families/f-15/", …` entry). The proof holds B to A's build (Task 1's `base-weight:`), not to that figure.
- **The /methodology/ page weight.** By the link fix's own figures, /methodology/ has about 38 gzip bytes under its 45,400 ceiling (`build.mjs`, the `{ label: "/methodology/", …` entry):
  - 161,455 / 45,362 on round 2's `9acf0c78` build of the pre-release export;
  - the same 45,362 in round 3's estimate with fpds-ap 86/111 (fix-report §R3-5);
  - its release's P12 re-measures and re-stamps these.

  The page source is unchanged through `31b1e47b`. Gate 1 judges it on B's build (Step 2). Piece 2 changes no page source and no field the page renders. So Step 5 shows that B's /methodology/ equals A's apart from the build ID and the export stamps, and a gate-1 failure on it is A's, not piece 2's.
- **The build ID and the export stamps.** Two builds differ in more than their code:
  - **The build ID.** Next writes a fresh 21-character `site/.next/BUILD_ID` on every build (no `generateBuildId` in `next.config.ts`). Each page carries it once.
  - **The export stamps.** Each export run stamps its own values, so the `fam2-A` and `fam2-B` exports (Task 9a Step 4, separate runs) differ in them:
    - `site_meta.built_at` is `datetime.now(UTC).isoformat()` (`export_site.py`, "ONE timestamp for the run"). The layout footer prints it as `Built <time dateTime={builtAt}>…</time>`, and the /methodology/ page intro prints it again;
    - the citations' `retrieved_at` stamps, which the F-15 page's flight payload carries;
    - /methodology/'s `link_adjudication.measured_on`, which is `built_at[:10]`, printed as "As of <date>".

    Measured 2026-10-21 on a build of the pre-release export:
    - `/families/f-15/` carries 48 `+00:00` export timestamps (the built_at among them) and the rendered date twice;
    - /methodology/ carries the built_at 4 times, the rendered date 4 times and `measured_on` twice.
  - **What this means for the weights.** Raw bytes are equal when the stamps have equal lengths. The ISO stamps always do, but the rendered date may not: "October 9, 2026" is one character shorter than "October 10, 2026". The two exports run minutes apart, so their dates normally match.
  - **What this means for gzip.** Gzip may differ by a few bytes. For example, on `/families/f-15/` the `build.mjs` stamp (705,056 / 69,328, release 2's proof build of 2026-10-15) and a `9a50e28b` build of the live export have equal raw bytes, and their gzip is 69,328 and 69,340.
  - **How Step 5 compares.** It compares each page of the two builds with each build's own ID masked and every export stamp masked.
- **Not edited.** This task does not re-stamp `build.mjs`: piece 2 adds zero bytes.

- [ ] **Step 1: The Python gates on B@fam2**

Snapshot clones are exempt from the SAM guard. The defaults read `config.SITE_DIR` and the DuckDB under the clone's `GOVBUDGET_DATA`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"
for gate in verify-era-map verify-families verify-phase5b1 verify-phase5e verify-lineage; do (source "$P/fam2/env.sh" "$P/fam2-B" && uv run --project . python -m govbudget ${gate}) > "$L/gate-${gate}.log" 2>&1; echo "${gate} exit=$?"; tail -1 "$L/gate-${gate}.log"; done; head -12 "$L/gate-verify-families.log"
(source "$P/fam2/env.sh" "$P/fam2-B" && uv run --project . python -m govbudget evals check) > "$L/evals.log" 2>&1; echo "evals exit=$?"; tail -2 "$L/evals.log"
```

Expected:
- five `exit=0`, ending `verify-era-map: PASS`, `verify-families: PASS`, `verify-phase5b1: PASS`, `verify-phase5e: PASS` and `verify-lineage: PASS`;
- verify-era-map runs legs a–h with unchanged verdicts;
- verify-families' leg lines are a PASS, b PASS and c PASS. Leg b reports a draft F-35's guard matches as undecided, never failed. Leg c finds `index.json` equal to the projection, the F-15 artifact's `family_id` `f-15` with its 8 counted ids in order, and no D9 needle;
- `evals exit=0` and `evals check: PASS`. Piece 2 moves no warehouse figure, so the expected answers are A's.
  - The link fix's marts can move answers in `evals/phase5_questions.yaml` (its `fct_budget_to_awards` count questions and its program-concentration HHI question). Its release refreshes any it moves before it ships (D1).
  - If `evals check` names a stale answer here, run it against `fam2-A` with A's code (`source "$P/fam2/env.sh" "$P/fam2-A"`, from the A worktree). If A reports the same answer, it is the link fix's: stop and report. Never refresh evals in piece 2.

`verify-phase5b1` takes about 17 minutes.

- [ ] **Step 2: Build the site on B@fam2; the page snapshot, `npm run verify` and vitest**

Port 4173 must be free (no other session running verify).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"; BAD=0; for d in site duckdb parquet; do if [ -e "data/$d" ] && [ ! -L "data/$d" ]; then echo "STOP: data/$d is a real directory"; BAD=1; fi; done; [ "$BAD" = 0 ] || exit 1
for d in site duckdb parquet; do ln -sfn "$P/fam2-B/$d" "data/$d"; done; ls -l data | grep -- '->'
cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > "$L/site-build-B.log" 2>&1; echo "build exit=$?"
node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check ../tests/fixtures/f15/page_snapshot.json
NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > "$L/site-verify-B.log" 2>&1; echo "verify exit=$?"; grep -E "program-skeleton|family-history|^overall:" "$L/site-verify-B.log" | tail -4
npm test > "$L/vitest-B.log" 2>&1; echo "vitest exit=$?"; grep -E "Test Files|Tests " "$L/vitest-B.log" | tail -2
mkdir -p "$L/site-B" && cp out/families/f-15/index.html "$L/site-B/f15.html" && cp out/methodology/index.html "$L/site-B/methodology.html" && cp .next/BUILD_ID "$L/site-B/BUILD_ID"
```

Expected:
- `data/{site,duckdb,parquet} -> …/.proofs/fam2-B/…`;
- `build exit=0`;
- `f15-page-snapshot: PASS — equal to ../tests/fixtures/f15/page_snapshot.json`;
- `verify exit=0`, with the program-skeleton and family-history gates `PASS` and `overall: PASS`:
  - Gate 21's leg (r) finds `json/families/index.json` listing `f-15`, `json/f15_funding_history.json` and `out/families/f-15/index.html`, with no `program-skeleton(r):` error. This build is K1's first green.
  - Gate 21's leg (q), the link fix's, passes on the same build, because fam2 follows the link fix's live build (D1) and B's tree carries its seed `dbt/seeds/link_line_rulings.csv`.
  - Gate 24's own leg r (district by-year cells) reads `data/duckdb`, which points at `fam2-B` here.
  - Gate 1 judges /methodology/ at A's weight (Measured; Step 5 compares the two pages);
- `vitest exit=0`, with the platform-family mirror test among the passes. The link fix's site tests (`about-link-line-rulings`, `methodology-precision-population`, `program-skeleton-line-rulings`) are among them.

Any failure is a stop.

- [ ] **Step 3: `verify-phase5` (the assembly with `verify-families`) on B@fam2, timed for Task 10a**

The `data/*` links still point at `fam2-B`, and `site/out` is B's build. The run includes the paid live eval (48 questions), as every release has.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"; T0=$(date +%s)
(source "$P/fam2/env.sh" "$P/fam2-B" && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com uv run --project . python -m govbudget verify-phase5) > "$L/verify-phase5.log" 2>&1; echo "exit=$?"; echo "runtime $(( $(date +%s) - T0 )) s" | tee "$L/verify-phase5-runtime.txt"
grep -E "verify-era-map|verify-families|verify-phase5b1|gate eval|gate assembly|^verify-phase5:" "$L/verify-phase5.log" | tail -8
```

Expected:
- `exit=0`;
- `runtime <s> s`;
- the assembly lines list `verify-era-map` and `verify-families` `PASS`;
- `verify-phase5: PASS`.

Exit 2 (`BLOCKED`) is not a pass: check that the worktree's `.env` link exists (Task 1 Step 2), then re-run.

- [ ] **Step 4: Put the links and `llms.txt` back**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
git checkout -- site/public/llms.txt && for d in site duckdb parquet; do ln -sfn "/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/$d" "data/$d"; done && ls -l data | grep -- '->' && git -C .. status --porcelain -- GovBudget | grep -v '^??'; echo "clean check done"
```

Expected: the five links point at `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/…`; no tracked change; `clean check done`.

- [ ] **Step 5: Build A@fam2 in the A worktree; the F-15 page weighs what A's does and equals it with the build ID and export stamps masked**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"; AW=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fam2-proof-a/GovBudget; A=$(cat "$L/a_sha.txt")
if git -C .. diff --quiet "$A" HEAD -- GovBudget/site/package.json GovBudget/site/package-lock.json; then [ -e "$AW/site/node_modules" ] || cp -c -R site/node_modules "$AW/site/node_modules"; echo "node_modules cloned (lockfile equal)"; else (cd "$AW/site" && npm ci > /dev/null 2>&1; echo "npm ci exit=$?"); fi
for d in site duckdb parquet; do ln -sfn "$P/fam2-A/$d" "$AW/data/$d"; done; ls -l "$AW/data" | grep -- '->'
cd "$AW/site" && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > "$L/site-build-A.log" 2>&1; echo "build exit=$?"
node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check "$AW/tests/fixtures/f15/page_snapshot.json"
mkdir -p "$L/site-A" && cp out/families/f-15/index.html "$L/site-A/f15.html" && cp out/methodology/index.html "$L/site-A/methodology.html" && cp .next/BUILD_ID "$L/site-A/BUILD_ID"
cd "$L" && node -e 'const fs=require("fs"),z=require("zlib");for(const [l,f] of [["/families/f-15/","f15.html"],["/methodology/","methodology.html"]])for(const s of ["site-A","site-B"]){const b=fs.readFileSync(s+"/"+f);console.log(s+" "+l+" "+b.length.toLocaleString("en-US")+" / "+z.gzipSync(b,{level:9}).length.toLocaleString("en-US"))}' | tee weights.txt
for s in A B; do node -e 'const m=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));console.log(process.argv[2]+" built_at "+m.built_at+", renders "+new Date(m.built_at).toLocaleDateString("en-US",{year:"numeric",month:"long",day:"numeric"}))' "$P/fam2-$s/site/json/site_meta.json" "fam2-$s"; done | tee -a weights.txt
M() { sed -E -e "s/$(cat "$1/BUILD_ID")/BUILD_ID/g" -e 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?\+00:00/TS/g' -e 's/(TS(">|\\",\\"children\\":\\"))[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}/\1DATE/g' -e 's/(As of (<!-- -->|\\",\\"))[0-9]{4}-[0-9]{2}-[0-9]{2}/\1DAY/g' "$1/$2"; }
cmp <(M site-A f15.html) <(M site-B f15.html) && echo "F-15 page identical apart from the build id and the export stamps" | tee -a weights.txt
cmp <(M site-A methodology.html) <(M site-B methodology.html) && echo "/methodology/ identical apart from the build id and the export stamps" | tee -a weights.txt
```

`M` masks, in this order:
- the tree's own build ID;
- every `+00:00` ISO-8601 timestamp, which covers the `built_at` and every citation `retrieved_at` an export stamps. The source-dated `retrieved_at` values carry a local offset (`-04:00` on today's F-15 page) and stay compared;
- the date rendered right after a masked timestamp (the `<time>` element's text, in HTML and in the flight payload);
- /methodology/'s "As of <measured_on>".

It was tested 2026-10-21 in zsh and bash on the two pages of a build of the live export, against a copy carrying another build ID, other export stamps and a shorter rendered date: both pages matched. A one-character change elsewhere still differed.

Expected:
- `node_modules cloned (lockfile equal)`. Piece 2 adds no npm dependency; if the lockfile differs, `npm ci exit=0`;
- three links to `fam2-A`;
- `build exit=0`;
- `f15-page-snapshot: PASS — …`;
- `site-A /families/f-15/ <raw> / <gzip>` and `site-B /families/f-15/ <raw> / <gzip>`, under 725,000 / 70,000:
  - The raw counts are equal. This is the hard check.
  - The raw counts also equal Task 1's `base-weight:` (A's build of the live export; 705,056 / 69,328 was the `1256ec35`-era stamp) when fam2's rendered date has the same length as the one `base-weight:` records. Otherwise they differ by exactly twice the length difference, because the page prints the date twice.
  - The gzip counts are equal, or differ by a few bytes of build-ID and export-stamp noise (Measured);
- `site-A /methodology/ <raw> / <gzip>` and `site-B /methodology/ <raw> / <gzip>`, with the raw counts equal, under 162,000 / 45,400. By the link fix's figures that leaves about 38 gzip bytes, and its release's P12 re-measures them. The gzip counts are equal, or differ by a few bytes of noise. The page prints export figures, so compare it with Task 1's `base-weight:` (the live export) for information only;
- `fam2-A built_at <ISO>, renders <date>` and `fam2-B built_at <ISO>, renders <date>`. The two exports ran minutes apart in Task 9a Step 4, so the dates are normally equal. If they differ in length, the A-vs-B raw counts differ by exactly that length difference times the date's occurrences: 2 on `/families/f-15/`, 4 on /methodology/. Then the masked `cmp` lines below decide, and the proof note records both dates;
- `F-15 page identical apart from the build id and the export stamps`;
- `/methodology/ identical apart from the build id and the export stamps`.

A stop means piece 2 moved a page. Stop and report: §4 anti-goal 1. Either of these is a stop:
- a raw difference that the rendered dates do not account for exactly;
- a masked `cmp` difference. Never widen the mask to make it pass. Never re-stamp a weight entry, and never raise a ceiling. The A worktree's links and `out/` are local to it, and its removal at Task 10c's cleanup takes them.

- [ ] **Step 6: pytest on 55432, and W1 at the Task 1 baselines**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -lt 23 ]; then echo "WAIT: start between :23 and :59 (minute $MIN); the full pytest reads the live DuckDB for about 10 minutes"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fam2-logs"
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q > "$L/pytest.txt" 2>&1; tail -1 "$L/pytest.txt"; echo "pytest ended at minute $(date +%M)"
for f in cli export_site verify_phase5 program_pdf_receipts f15_funding_history verify_era_map platform_families platform_family_history platform_family_review verify_families; do printf "%s: " "$f"; uvx --offline ruff check --isolated --select F,E9 "src/govbudget/$f.py" 2>&1 | grep -E '^(Found|All checks)'; done | tee "$L/w1.txt"
```

Expected:
- `… passed`, with 0 failed (a Postgres-only failure gets one re-run on a quiet cluster);
- `pytest ended at minute <m>`, with `<m>` outside :15–:22; otherwise re-run the block from :23;
- W1 equal to Task 1's `W1:` line for the six existing modules (`cli: Found 5 errors.`, `export_site: Found 10 errors.` and `verify_phase5: Found 2 errors.` unless A moved them);
- `All checks passed!` for the other three existing modules and the four new ones.

- [ ] **Step 7: Write the proof note, and commit it**

Write `docs/superpowers/reviews/families-piece2-proof.md`, modelled on `fu-release1-proof.md`. Every bracketed log is under `.proofs/fam2-logs/`, and Task 10c copies them into the ledger.

**Header:**
- spec §14 and §16;
- A = `<a_sha>` (`git merge-base main HEAD`, the link fix's release under D1), whose src/, dbt/, data-seeds/, scripts/ and site/ equal the deployed `<live sha>`;
- B = `<b_sha>` [a_sha.txt, b_sha.txt];
- the snapshot `.proofs/fam2` (database `govbudget_proof_fam2`), taken `<created_at>`, which includes the link fix's live build (`link_line_rulings` and `link_award_keys` present).

**`## Summary (<date this step runs>)`:** one paragraph with the result.

**`### Snapshot`:** the values of `snapshot-shas.json`:
- `duckdb_sha256_at_copy`;
- `parquet_files_minus_sam` and `parquet_minus_sam_sha256`;
- `site_sha256`, `raw_docs_sha256` and `manifest_jsonl_sha256`;
- `pg_tables`, `pg_tables_sha256` and `pg_dump_sha256`.

**`### Exports and diffs`:**
- the three export lines with one `<N>`;
- the control EQUAL [diff-control.txt];
- the code A/B PASS with rules 0 and 1 matched once each [diff-code.txt];
- `json_sidecars` +1 and `families/index.json` the only new json file [sidecars.txt].

**`### F-15 bytes and facts`:**
- the pin on A and B;
- V5 4 passed [f15-era-identity.txt];
- fact stability with 0 missing, 0 changed and 0 new [fact-stability.txt], with one sentence on why the empty leaf map is used (Task 9a Measured);
- link coverage identical [link-coverage-*.txt].

**`### Page and weight`:**
- the snapshot PASS on both builds;
- the A and B weights of `/families/f-15/` and `/methodology/`, the two exports' `built_at` lines, and the two masked-identical lines [weights.txt];
- gate 21 (`program-skeleton`) leg (r) green, beside the link fix's leg (q) [site-verify-B.log].

**`### Gates`:** each verdict line of Steps 1, 3 and 6 [gate-*.log, verify-phase5.log, evals.log, vitest-B.log, pytest.txt, w1.txt].

**`### The F-35 (B1)`** comes from Task 8b's `B1:` line:
- **Ratified:** "Batch R-DEC-FAM-F35-B1 was ratified on <date> (owner: "<reply>"). The B1 page showed, from the preview on fam2: FY2015 8,276.5 … FY2024 13,469.6, FY2015–24 cumulative 116,808.4, FY2025 enacted 12,532.3, FY2026 request 11,467.0 ($M), equal to F35 Appendix B1, differences none. Manifest sha256 <hex>. Amendments: <none|list>. The F-35 is `ratified` and appears nowhere in the export."
- **Deferred:** one line, "The owner deferred F-35 batch B1 on <date>; the F-35 stays a draft." It makes no F-35 claim.

**`### Re-runs`:** a dated correction note for anything re-run; otherwise "none". On a re-take the note is already committed: rewrite the whole file, and this commit carries the corrections.
- Write one dated correction per `release-pins:` and `release-retake:` line in `progress.md`, in ledger order. Each keeps its own date and source: the `DIFFERENT` reason with its kept `pins-fam2-fam2-rel-DIFFERENT-*.txt`, then the re-take with the owner's reply and the items removed. A Step 1 re-take also gives the old B and the commits that moved the export code.
- The section is cumulative. A second re-take keeps the first one's corrections, because they are re-written from the ledger lines, which are never deleted.

Task 10a's re-take branches write nothing into the note themselves.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/docs/superpowers/reviews/families-piece2-proof.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(review): the piece-2 proof — F-15 byte-identical on fam2 (A/B within §16), gates green, B1 <ratified|deferred>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: the commit, `1 file changed`.

Keep everything for Task 10a and the cleanup offer: the A worktree, `.proofs/fam2`, `fam2-A`, `fam2-B`, `fam2-B2`, `fam2-preview-f-35-B1`, `fam2-logs` and `govbudget_proof_fam2`.

---

### Task 10a: Release — preconditions, the live re-measure, the export, the release-state checks and the build

**Spec:** §15 steps 1–5, §12 (`index.json` stays off the live site), §5.2; K1 (closed here).

**Files:**
- Create: `docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-release.json`.
- Modify only if the build changes it: `site/public/llms.txt`.
- Proof state:
  - `.proofs/fam2-rel` (database `govbudget_proof_fam2_rel`);
  - `.proofs/fam2-release-pre-site`;
  - `.proofs/fam2-release-export.sha256` and `.proofs/fam2-release-export.built_at`.
- Transient logs: `tmp/fam2-release-*`.

**Shared-state writes:** one, the release export of the live `data/site` (Step 5). It runs between :21 and :45, by absolute path from this worktree. Nothing touches Postgres, DuckDB, dbt or the parquet tree (§15 step 2).

**Interfaces:**
- Consumes:
  - Task 9a and 9b's `fam2-B/site`, `noise-B-B2.json`, `b_sha.txt` and `verify-phase5-runtime.txt`;
  - `platform-families check --strict` (I-REV; it defaults to the live `config.DUCKDB_PATH` and `config.SITE_DIR`);
  - `scripts/fu/snapshot_pins.py compare SNAP_A SNAP_B`, which prints `snapshot-pins: EQUAL|DIFFERENT` and skips `sam/`;
  - `govbudget proof diff … --expect`.
- Produces, for Task 10b:
  - `SAM_D` and `tmp/fam2-release-counts.json`;
  - the fingerprint;
  - a built and verified `site/out` at HEAD.
- Produces, for Task 9b Step 7 after a re-take: `progress.md` lines `release-pins: DIFFERENT …` (Step 2) and `release-retake: …` (Steps 1 and 2), one per event, each with its own date.

**Measured (2026-10-21, read-only):**
- The live SAM parquet files are unchanged since 2026-10-04 21:17 (`entities.parquet`, `answers.parquet`), so `SAM_D` 0 is expected.
- `launchctl list` holds only `com.fiscalreceipts.sam-daily`.
- The live `/json/families/index.json` returns 404. `upload_r2.sh` sends only `pdfs/`, `data/`, `workbooks/` and `citations/`, and `prepare-assets.mjs` copies `json/f15_funding_history.json` by name, so `index.json` never ships (§12).

- [ ] **Step 1: Preconditions**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -lt 23 ]; then echo "WAIT: start between :23 and :59 (minute $MIN); the full pytest reads the live DuckDB for about 10 minutes"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fam2-logs"; B=$(cat "$L/b_sha.txt"); LEDGER=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2
git -C .. status --porcelain -- GovBudget | grep -v '^??'; echo "(tracked changes above: expect none)"; git -C .. log --oneline -1
git -C .. diff --quiet "${B:?}" HEAD -- GovBudget/src GovBudget/dbt GovBudget/data-seeds GovBudget/scripts GovBudget/migrations && echo "export code at HEAD = the proven B $B"
"$GOVBUDGET_PG_BIN/pg_isready" -h 127.0.0.1 -p 55432 && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q 2>&1 | tail -1; echo "pytest ended at minute $(date +%M)"
launchctl list | grep -i fiscalreceipts
grep -E '^B1: ' "$LEDGER/progress.md"; uv run --project . python -c "from govbudget.platform_families import load_registry; f=load_registry()['f-35']; print('f-35', f.status, len(f.members))"
curl -s https://fiscalreceipts.com/.build-meta.json | grep git_head
```

Expected:
- no tracked change, with HEAD Task 9b's commit;
- `export code at HEAD = the proven B <sha>`;
- `accepting connections` and `… passed`, with 0 failed;
- `pytest ended at minute <m>`, with `<m>` outside :15–:22; otherwise re-run the block from :23;
- one line ending `com.fiscalreceipts.sam-daily`;
- the `B1:` line agreeing with the registry: `ratified …` with `f-35 ratified 19`, or `deferred …` with `f-35 draft 0`;
- the `git_head` that Task 9a Step 1 proved equal to A. Production has not moved since the proof.

What to do on a miss:
- **The export code moved:** the proof is stale, and the re-run is an owner stop, as in Step 2's re-take. Task 9a Step 3 refuses the existing A worktree and Step 4 refuses existing clones. Ask the owner, naming the commits, for a yes to remove `fam2-A`, `fam2-B` and `fam2-B2` and the A worktree, plus `fam2-rel` and `govbudget_proof_fam2_rel` if an earlier pass of Step 2 made them. Use Task 10c Step 5's commands for those items. `fam2` and its database stay, and Step 2 re-checks them. On the yes, first add one line to `progress.md`, dated the day of the answer: `release-retake: <date of the yes> Step 1: owner "<reply>"; removed <items>; old B <the sha in fam2-logs/b_sha.txt, read before the re-run overwrites it>; export code moved by <commits>`. Then re-run Task 9a from Step 1 at the new HEAD, skipping Step 2's commit when the rule file is already committed unchanged (Task 9a Step 2's re-take note; its `load_expectations` check still runs), then Task 9b, then this task from Step 1. Without a yes, release nothing.
- **Another `fiscalreceipts` launchd job:** stop and ask the owner. It could export from the main checkout during this release.

- [ ] **Step 2: The live lake's pins equal fam2's (SAM excepted)**

Start only between :23 and :45. The tool itself refuses :15–:20.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -lt 23 ] || [ "$MIN" -gt 45 ]; then echo "WAIT: start between :23 and :45 (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}"; L="$P/fam2-logs"; [ -e "$P/fam2-rel" ] && { echo "STOP: $P/fam2-rel exists"; exit 1; }
uv run --project . python -m govbudget proof snapshot --out "$P/fam2-rel" --scratch-db govbudget_proof_fam2_rel > "$L/snapshot-fam2-rel.log" 2>&1; echo "snapshot exit=$?"; tail -3 "$L/snapshot-fam2-rel.log"
uv run --project . python scripts/fu/snapshot_pins.py compare "$P/fam2" "$P/fam2-rel" > "$L/pins-fam2-fam2-rel.txt" 2>&1; echo "pins exit=$?"; cat "$L/pins-fam2-fam2-rel.txt"
```

Expected: `snapshot exit=0` with its summary lines, then `pins exit=0` and `snapshot-pins: EQUAL`.

On `DIFFERENT`, the live lake or Postgres moved after fam2; the lines above the verdict name what moved. Stop. Leave the proof note alone for now. Task 9b Step 7 committed it, so an edit here is a tracked change, and the clean checks of Task 9a Step 1, Task 9b Step 4 and this task's Steps 1 and 8 would refuse it on a re-take. The reason reaches the note through the re-take ("On the yes" below). Record it in the ledger instead. First keep the verdict, which a re-take's pass of this step overwrites:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fam2-logs"; K="pins-fam2-fam2-rel-DIFFERENT-$(date -u +%Y%m%dT%H%M%SZ).txt"; cp "$L/pins-fam2-fam2-rel.txt" "$L/$K" && echo "kept $K"
```

Then add one line to `progress.md`: `release-pins: DIFFERENT <date>: <what moved, from the lines above the verdict> [fam2-logs/<the kept file>]`.

Run Step 3 next, before re-taking anything: if it reports a stale entry or a failure, Step 3's owner stop applies and no re-run of Tasks 9a and 9b can pass.

Otherwise the re-take §15 step 1 asks for is also an owner stop. Every artifact it recreates already exists, and each is guarded: Task 1 Step 5 and `proof snapshot` refuse an existing `fam2` or `govbudget_proof_fam2`; Task 9a Step 3's `git worktree add` refuses the existing A worktree; Task 9a Step 4 refuses existing clones; and this step refuses an existing `fam2-rel`. Removing them is the owner's call (Global Constraints, "Scratch databases"; spec §15 step 10).
- **Ask** the owner, naming what moved, for a yes to remove these and re-take:
  - under `$GOVBUDGET_PROOFS`: `fam2`, `fam2-A`, `fam2-B`, `fam2-B2` and `fam2-rel`;
  - the databases `govbudget_proof_fam2` and `govbudget_proof_fam2_rel`;
  - the A worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fam2-proof-a`.

  Keep `fam2-logs`, which the re-run overwrites file by file, and `fam2-preview-f-35-B1`, the B1 page's preview.
- **On the yes,** first add one line to `progress.md`, dated the day of the answer: `release-retake: <date of the yes> Step 2: owner "<reply>"; removed <items>`. Then remove exactly those items. Use Task 10c Step 5's commands for them: the two `dropdb` calls, `git -C .. worktree remove --force` on the A worktree, and `rm -rf` of the five names, run in `"${GOVBUDGET_PROOFS:?}"`. Then re-run Task 1 Step 5; Task 9a from Step 1, skipping Step 2's commit when the rule file is already committed unchanged (Task 9a Step 2's re-take note; its `load_expectations` check still runs); Task 9b; and this task from Step 1. The dated corrections come from the `release-pins:` and `release-retake:` lines (Task 9b Step 7, `### Re-runs`). They go into the proof note's `### Re-runs` section when Task 9b Step 7 rewrites and commits the note, and at no other point. An edit after that commit is a tracked change, and Step 8's clean check and `deploy.sh`'s provenance check would refuse it.
- **Without a yes,** release nothing. The reason stays in the `release-pins:` line and the kept file.

Never release onto a lake the proof did not start from (§15 step 1).

- [ ] **Step 3: `platform-families check --strict` against the live lake**

This re-measures the lake-measured values (`titles_seen`, `budget_activities`, ranges and `drift_sha256`), read-only.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
mkdir -p tmp && uv run --project . python -m govbudget platform-families check --strict > tmp/fam2-release-check.txt 2>&1; echo "exit=$?"; cat tmp/fam2-release-check.txt
```

Expected: no failure line, `stale` 0, and no `f-15` entry in any category. Then, by branch:
- **B1 ratified:** the only `undecided` entry is the recorded deferred row `f-35|R-1:3600F:AF:0207268F|2017-2026`.
- **B1 deferred:** every `undecided` entry is a guard line of the draft F-35 (150 measured).

`--strict` therefore exits 1, on undecided entries alone (R4, R17): the recorded deferred row or the draft's guard lines. That is the expected pass, because §15 step 1 asks for "no stale and no failure"; read the categories, not the exit code.

What else may happen:
- **Exit 2** with `Could not set lock on file`: another process holds the DuckDB file. Wait and re-run.
- **A stale entry, a failure, or an F-15 entry:** the live lake differs from fam2 for a registry family (a moved line or a new guard match). Stop before the export, record the reason in the proof note as a dated correction, and stop for the owner; release nothing until the owner answers. Piece 2 has no tool that re-measures the committed lake columns (`titles_seen`, `budget_activities`, `drift_sha256`) of a published or ratified family. `propose --seed-shipped` refuses an existing `f-15` (R6), `propose` refuses a published or ratified family (R17), and the F-15 freeze forbids editing the rows by hand. Re-taking fam2 alone would only move the stop into the proof: B's export (stage 2 on the F-15) and `verify-families` leg b (every family) refuse the same entries (R4). The re-pin §15 step 1 asks for (re-measure with a recorded reason) needs an owner ruling and a re-measure path. That path is piece-3 work, filed by Task 10c as #<n2>.

- [ ] **Step 4: Write the release-state rule file (SAM registration rules only) and commit it**

The build in Step 8 must follow every commit, because `deploy.sh` requires `.build-meta.json` `git_head` to equal HEAD.

Create `docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-release.json` as a copy of `docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-release.json`:
- keep the same 12 rules, in the same order, with each rule's `path`, `status`, `pointer` and `change` unchanged and no `required` key;
- in every `why`, replace `design §8 step 4` with `piece-2 spec §15 step 4` and `snapshot fu-post` with `snapshot fam2`;
- in the first rule's `why`, replace `(all 200 families had an answer on 2026-10-13, so none is expected)` with `(the SAM parquet has been unchanged since 2026-10-04, so none is expected)`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python - <<'PY'
from govbudget.proof import load_expectations
old = load_expectations("docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-release.json")
new = load_expectations("docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-release.json")
keys = lambda r: {k: v for k, v in r.items() if k != "why"}
print(len(new), sum(keys(a) == keys(b) for a, b in zip(old, new)), sum("piece-2 spec §15 step 4" in r["why"] for r in new), any("fu-post" in r["why"] or "design §8" in r["why"] for r in new))
PY
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-release.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(plan): the piece-2 release-state rule list (SAM registrations only, §15 step 4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `12 12 3 False`, then the commit (`1 file changed`). Three rules carried release 1's `design §8 step 4`.

- [ ] **Step 5: Keep production's export, point the worktree at the main lake, export (SHARED WRITE: data/site)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; [ -e "$P/fam2-release-pre-site" ] || cp -cR /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site "$P/fam2-release-pre-site"; ls "$P/fam2-release-pre-site/manifest.json"; ls "$P/fam2-release-pre-site/json/families" 2>/dev/null | wc -l
for d in site duckdb parquet raw raw_docs; do if [ -e "data/$d" ] && [ ! -L "data/$d" ]; then echo "STOP: data/$d is a real directory"; else ln -sfn "/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/$d" "data/$d"; fi; done; [ -e .env ] || ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/.env .env; ls -l data .env | grep -c -- '->'
```

Expected:
- the manifest path, then `0`. Production's export has no `json/families/`;
- `6`, for five lake links and `.env`. Never print `.env`.

Then start the export only between :21 and :45 (about 15 minutes; the SAM job writes at :17):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && MIN=$(date +%M) && if [ "$MIN" -lt 21 ] || [ "$MIN" -gt 45 ]; then echo "WAIT: start between :21 and :45 (now :$MIN)"; else S0=$(stat -f %m /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet) && GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget export-site > tmp/fam2-release-export.log 2>&1; echo "exit=$?"; S1=$(stat -f %m /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet); [ "$S0" = "$S1" ] && echo "SAM parquet unchanged during the export" || echo "RE-RUN: SAM parquet changed during the export"; tail -2 tmp/fam2-release-export.log; fi
```

Expected: `exit=0`, `SAM parquet unchanged during the export`, and the `budget PDF receipts: …` and `export-site: … <N> citations …` lines, with Task 9a's `<N>`. On `RE-RUN`, export again in the next window.

Record the counts and fingerprint the export:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python - <<'PY'
import json, os
from pathlib import Path
proofs = Path(os.environ["GOVBUDGET_PROOFS"]); live = Path("/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site")
def measure(s):
    meta, man = json.loads((s / "json/site_meta.json").read_text()), json.loads((s / "manifest.json").read_text())
    return {"companies_with_sam": meta["counts"]["companies_with_sam"], "citations": meta["counts"]["citations"],
            "pdf_files": len(list((s / "pdfs").glob("*.pdf"))), "json_sidecars": man["json_sidecars"], "built_at": man["built_at"]}
pre, rel = measure(proofs / "fam2-release-pre-site"), measure(live)
out = {"pre": pre, "release": rel, "SAM_D": rel["companies_with_sam"] - pre["companies_with_sam"], "citations_D": rel["citations"] - pre["citations"],
       "json_sidecars_D": rel["json_sidecars"] - pre["json_sidecars"], "new_pdfs": rel["pdf_files"] - pre["pdf_files"]}
Path("tmp/fam2-release-counts.json").write_text(json.dumps(out, indent=2) + "\n"); (proofs / "fam2-release-export.built_at").write_text(rel["built_at"] + "\n")
print(json.dumps({k: out[k] for k in ("SAM_D", "citations_D", "json_sidecars_D", "new_pdfs")}))
PY
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget && find data/site/data data/site/citations data/site/pdfs data/site/workbooks data/site/manifest.json data/site/json/f15_funding_history.json -type f -print0 | sort -z | xargs -0 shasum -a 256 > .proofs/fam2-release-export.sha256 && wc -l < .proofs/fam2-release-export.sha256 && shasum -a 256 -c --quiet .proofs/fam2-release-export.sha256 && echo "release export fingerprinted"
```

Expected: `{"SAM_D": 0, "citations_D": 0, "json_sidecars_D": 1, "new_pdfs": 0}`, then a line count and `release export fingerprinted`.
- A non-zero `SAM_D` adds that many to `json_sidecars_D` (one `json/sam/*.json` file each). Step 6's rules allow it, and the owner hears the number at Task 10b.
- A non-zero `citations_D` beyond SAM is a stop.

- [ ] **Step 6: Release-state checks: what ships is what was proven**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; S=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site
uv run --project . python -m govbudget proof diff "$P/fam2-B/site" "$S" --noise-from "$P/fam2-logs/noise-B-B2.json" --expect docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-release.json > tmp/fam2-release-vs-proof.txt 2>&1; echo "proof diff exit=$?"; grep -E "changed [0-9]|UNEXPECTED|^proof diff:" tmp/fam2-release-vs-proof.txt
H=$(shasum -a 256 "$S/json/f15_funding_history.json" | cut -d' ' -f1); [ -n "$H" ] && [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ] && echo "F-15 history matches the pin" || echo "STOP: F-15 history ${H:-missing} is not the pin"
python3 -c "import json; print('index:', [f['platform_family'] for f in json.load(open('$S/json/families/index.json'))['families']])"
uv run --project . python -m govbudget link-coverage --site-dir "$S" --baseline data/research/link_coverage/baseline.json > tmp/fam2-release-link-coverage.txt 2>&1; echo "link-coverage exit=$?"
```

Expected:
- `proof diff exit=0`;
- `changed 0 · only in A 0 · only in B 0` when `SAM_D` is 0, or only SAM-rule matches;
- `proof diff: PASS`;
- `F-15 history matches the pin`;
- `index: ['f-15']`;
- `link-coverage exit=0`.

Any failure: take the abort path at the end of this task.

- [ ] **Step 7: The Python release gates on the live state**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
S=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet
for gate in verify-era-map verify-families; do MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN) before ${gate}; re-run this block from :23"; exit 0; fi; S0=$(stat -f %m "$S"); GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python -m govbudget ${gate} > tmp/fam2-release-${gate}.log 2>&1; echo "${gate} exit=$?"; [ "$(stat -f %m "$S")" = "$S0" ] || echo "RE-RUN ${gate}: the SAM parquet changed while it ran"; tail -1 tmp/fam2-release-${gate}.log; done
```

Expected: `verify-era-map exit=0` / `verify-era-map: PASS` and `verify-families exit=0` / `verify-families: PASS`, with no `WAIT` or `RE-RUN` line.

Then `verify-phase5`, timed between two SAM ticks from Task 9b's runtime:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); RT=$(awk '/^runtime / {print $2}' "${GOVBUDGET_PROOFS:?}/fam2-logs/verify-phase5-runtime.txt"); : "${RT:?Task 9b Step 3 first}"
if [ "$RT" -gt 2940 ]; then echo "STOP: verify-phase5 takes about $(( RT / 60 )) minutes; no start fits between two SAM ticks — ask the owner"; exit 1; fi
if [ "$MIN" -lt 23 ] || [ "$MIN" -gt 28 ] || { [ "$RT" -gt 2640 ] && [ "$MIN" -ne 23 ]; }; then echo "WAIT: start between :23 and :28 (:23 exactly when over 44 minutes); minute $MIN, runtime ${RT} s"; exit 0; fi
S=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet; S0=$(stat -f %m "$S"); T0=$(date +%s)
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com uv run --project . python -m govbudget verify-phase5 > tmp/fam2-release-verify-phase5.log 2>&1; echo "exit=$?"; echo "runtime $(( $(date +%s) - T0 )) s, ended at minute $(date +%M)"; [ "$(stat -f %m "$S")" = "$S0" ] && echo "SAM parquet unchanged during verify-phase5" || echo "RE-RUN: the SAM parquet changed during verify-phase5"; grep -E "verify-families|verify-era-map|gate eval|^verify-phase5:" tmp/fam2-release-verify-phase5.log | tail -6
```

Expected:
- `exit=0`;
- the runtime line;
- `SAM parquet unchanged during verify-phase5`;
- `verify-families` and `verify-era-map` `PASS` in the assembly;
- `verify-phase5: PASS`.

`BLOCKED` (exit 2) is not a pass: check the `.env` link. A failure that cannot be cleared means the abort path.

- [ ] **Step 8: llms.txt, then build, test and verify at HEAD, each after the fingerprint check**

Two blocks, as the link fix's runbook Step R10 has. The first reads only `data/site`, `node_modules` and `site/out`, so it runs at any minute: `prepare-assets.mjs` reads `data/site/json` and copies DuckDB-WASM from `node_modules`, and the link fix's runbook (fix pass M-1) verified that the build and vitest read neither `data/duckdb` nor `data/parquet`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
FP() { (cd /Users/andeslee/Documents/Cursor-Projects/GovBudget && shasum -a 256 -c --quiet .proofs/fam2-release-export.sha256) && [ "$(python3 -c "import json; print(json.load(open('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/manifest.json'))['built_at'])")" = "$(cat /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fam2-release-export.built_at)" ] && echo "data/site is the release export" || { echo "STOP: data/site is no longer the release export"; exit 1; }; }
FP; cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com node scripts/prepare-assets.mjs > /dev/null && cd .. && git diff --stat -- site/public/llms.txt; echo "(llms.txt diff above: expect none, citations_D 0)"
FP; cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > ../tmp/fam2-release-site-build.log 2>&1; echo "build exit=$?"; cd ..
FP; cd site && npm test > ../tmp/fam2-release-vitest.log 2>&1; echo "vitest exit=$?"; node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check ../tests/fixtures/f15/page_snapshot.json; cd ..
ls site/out/json/families 2>/dev/null | wc -l
```

Expected:
- three `data/site is the release export` lines;
- no `llms.txt` diff;
- `build exit=0`;
- `vitest exit=0`;
- `f15-page-snapshot: PASS — …`;
- `0`. `out/json/families/` does not exist: `prepare-assets.mjs` never copies `index.json`.

If `citations_D` were non-zero, `llms.txt` would change. Commit exactly that file before the build: `chore(site): llms.txt citation count after the piece-2 release export (<pre> -> <release>)`, with the author and trailer as everywhere.

`npm run verify` reads the live lake through this worktree's `data/duckdb` and `data/parquet` links, which Step 5 pointed at the main lake:
- gate 24 leg r's `site/scripts/gates/districtyear-recompute.py` opens `data/duckdb/govbudget.duckdb` read-only;
- so do the other `*-recompute.py` helpers and `district.mjs`, and several of them read `data/parquet`.

So the second block keeps the SAM rule (Global Constraints), the way the link fix's runbook R10 gates its own release verify. The fingerprint check runs first. Then the minute is read directly before `npm run verify`, which starts only between :23 and :50. The link fix's runbook measured that verify at about 600 s, so a verify started then ends before :12. The SAM mtime check around the verify catches a tick that lands anyway. A `WAIT` or `RE-RUN` repeats only this block, never the build. Snapshot clones are exempt, so Task 9b Step 2's verify on `fam2-B` needs no guard.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
FP() { (cd /Users/andeslee/Documents/Cursor-Projects/GovBudget && shasum -a 256 -c --quiet .proofs/fam2-release-export.sha256) && [ "$(python3 -c "import json; print(json.load(open('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/manifest.json'))['built_at'])")" = "$(cat /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fam2-release-export.built_at)" ] && echo "data/site is the release export" || { echo "STOP: data/site is no longer the release export"; exit 1; }; }
FP
MIN=$(date +%M); if [ "$MIN" -lt 23 ] || [ "$MIN" -gt 50 ]; then echo "WAIT: start npm run verify between :23 and :50 (minute $MIN); it reads the live lake for about 600 s"; exit 0; fi
SAM=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet; S0=$(stat -f %m "$SAM"); T0=$(date +%s)
cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > ../tmp/fam2-release-site-verify.log 2>&1; echo "verify exit=$? ($(( $(date +%s) - T0 )) s, ended at minute $(date +%M))"; grep -E "program-skeleton|^overall:" ../tmp/fam2-release-site-verify.log | tail -2; cd ..
[ "$(stat -f %m "$SAM")" = "$S0" ] && echo "SAM parquet unchanged during npm run verify" || echo "RE-RUN: the SAM parquet changed during npm run verify"
git -C .. status --porcelain -- GovBudget | grep -v '^??'; python3 -c "import json; print(json.load(open('site/out/.build-meta.json'))['git_head'])"; git rev-parse HEAD
```

Expected:
- one `data/site is the release export` line;
- no `WAIT` line. On `WAIT`, re-run this block alone in the window;
- `verify exit=0 (<s> s, ended at minute <m>)`, with `<s>` near 600 and `<m>` before :12 of the next hour; `program-skeleton` `PASS` and `overall: PASS`. Gate 21's leg (r) passes on the live export, which closes K1 (Step 7's live `verify-families` PASS closed K2). Its leg (q), the link fix's, passes beside it, and gate 1 judges /methodology/ at the weight Task 9b Step 5 measured on A and B;
- `SAM parquet unchanged during npm run verify`. On `RE-RUN`, run this block again from :23; nothing it does writes shared state;
- no tracked change;
- the two shas equal.

**Abort path (before the deploy).** Use it on any stop after Step 5's export that does not end in a deploy: a failed check here, a failure in Task 10b before its deploy, or the owner's no. There is no lake state to revert (§15 abort). Restore `data/site` and keep the aborted export aside; nothing is deleted:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
mv data/site "data/site.fam2-release-aborted-$(date -u +%Y%m%dT%H%M%SZ)" && cp -cR .proofs/fam2-release-pre-site data/site && shasum -a 256 data/site/manifest.json .proofs/fam2-release-pre-site/manifest.json
```

Expected: the two hashes are equal. Remove `data/site.fam2-release-aborted-*` only on the owner's word.

---

### Task 10b ★: Release — the deploy and the live checks

**Spec:** §15 steps 6–7, the abort, and §19 rows 8 and 24.

**Files:** none; shell only. Logs go to `tmp/fam2-release-deploy*.log` and `tmp/fam2-release-live-checks.txt`, and the `deploy:` line goes into `progress.md`.

**Interfaces:**
- Consumes:
  - Task 10a's export, fingerprint, `tmp/fam2-release-counts.json` and built `site/out`;
  - `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh` (R2 rollback copy, `pdfs/`, `data/`, `workbooks/` and `citations/`, Vercel, then the live-asset check).
- Produces, for Task 10c: the deployed commit and its R2 rollback tag, as `progress.md` line `deploy: <sha> <date>; rollback tag <tag>`.

- [ ] **Step 1: ★ The owner's go-ahead**

Fill `<…>` from `tmp/fam2-release-counts.json`, Task 9b's proof note and `progress.md`, and say:

"Ready to deploy families piece 2 (the family registry) at `<HEAD short sha>`. Readers see no change from piece 2: the F-15 page, its numbers and its citation IDs are byte-identical to the deployed site's, proven on one frozen snapshot (see `docs/superpowers/reviews/families-piece2-proof.md`). The new `json/families/index.json` stays off the live site and returns 404. SAM registrations shipped since the last deploy: `<SAM_D>` (0 expected); these are the only reader-visible change, on company pages. The F-35: <ratified on <date> as batch R-DEC-FAM-F35-B1, not published | batch B1 deferred; the F-35 stays a draft>. All gates are green (verify-phase5 with verify-families, verify-era-map, link coverage, npm verify). I can also merge without deploying and let this ride with the next release, if you prefer. Deploy now?"

Wait for an explicit yes. No reply is not a yes. A no takes Task 10a's abort path. "Merge without deploying" skips Steps 2–4 and goes to Task 10c, whose merge-only variant (Step 1) makes every stamp line, the commit message and the publish prompt say "merged, not deployed", with no rollback tag.

- [ ] **Step 2: The fingerprint, then the dry run**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L=/Users/andeslee/Documents/Cursor-Projects/GovBudget
(cd "$L" && shasum -a 256 -c --quiet .proofs/fam2-release-export.sha256) || { echo "STOP: data/site is no longer the release export"; exit 1; }
H=$(shasum -a 256 "$L/data/site/json/f15_funding_history.json" | cut -d' ' -f1); [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ] || { echo "STOP: F-15 history is not the pin"; exit 1; }
[ "$(python3 -c "import json; print(json.load(open('$L/data/site/manifest.json'))['built_at'])")" = "$(cat "$L/.proofs/fam2-release-export.built_at")" ] && echo "data/site is the release export"
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh --dry-run > tmp/fam2-release-deploy-dry.log 2>&1; echo "exit=$?"; grep -E "0/3|provenance:|untracked inputs|R2 pdfs|Dry run complete" tmp/fam2-release-deploy-dry.log
```

Expected:
- `data/site is the release export`;
- `exit=0`;
- `0/3  preflight`;
- `provenance:      OK — git_head matches HEAD; no tracked changes; no untracked build inputs`;
- `untracked inputs: none`;
- `R2 pdfs:         <n> binaries to sync`, where `<n>` = `release.pdf_files` in the counts file (unchanged; piece 2 adds no PDF);
- `Dry run complete — nothing was copied, uploaded or deployed.`

Any `STOP` means no deploy: re-run Task 10a Steps 5–8, or take its abort path.

- [ ] **Step 3: Deploy, by absolute path from this worktree**

```bash
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh > /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fam2-release-deploy.log 2>&1; echo "exit=$?"; grep -E "rollback tag|Rollback copy made|Deploy complete" /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fam2-release-deploy.log
```

Expected:
- `exit=0`;
- `rollback tag:    <YYYY-MM-DDTHHMMSSZ>`;
- `Rollback copy made and checked: r2:govbudget-assets/rollback/<tag>/`;
- `Deploy complete: …, live assets verified.`

Record `deploy: <HEAD sha> <date>; rollback tag <tag>` in `progress.md`. A failure after the copy prints the tag again: read it before anything is re-run.

- [ ] **Step 4: Live checks**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
H=$(git rev-parse HEAD); T=tmp/fam2-release-live-f15.html
{ echo "build-meta head: $(curl -s https://fiscalreceipts.com/.build-meta.json | grep -c "\"git_head\": \"${H}\"")"
  echo "/families/f-15/: $(curl -s -o "$T" -w '%{http_code}' https://fiscalreceipts.com/families/f-15/)"
  (cd site && node scripts/f15-page-snapshot.mjs "../$T" --check ../tests/fixtures/f15/page_snapshot.json)
  echo "/json/f15_funding_history.json sha256 $(curl -s https://fiscalreceipts.com/json/f15_funding_history.json | shasum -a 256 | cut -d' ' -f1) (pin $(cat tests/fixtures/f15/history.sha256))"
  echo "/json/families/index.json: $(curl -s -o /dev/null -w '%{http_code}' https://fiscalreceipts.com/json/families/index.json)"
  echo "/json/f35_funding_history.json: $(curl -s -o /dev/null -w '%{http_code}' https://fiscalreceipts.com/json/f35_funding_history.json)"; } | tee tmp/fam2-release-live-checks.txt
```

Expected:
```
build-meta head: 1
/families/f-15/: 200
f15-page-snapshot: PASS — equal to ../tests/fixtures/f15/page_snapshot.json
/json/f15_funding_history.json sha256 d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f (pin d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f)
/json/families/index.json: 404
/json/f35_funding_history.json: 404
```

**Abort (after the deploy).** On any failed line, tell the owner at once and give the rollback tag. The owner decides whether to roll back (§15). On a yes:
1. Follow LAUNCH.md's rollback: Vercel back to the previous deployment, then R2 `data/` and `citations/` from `rollback/<tag>/`, with the commands `deploy.sh` printed.
2. Then run Task 10a's abort block, which restores `data/site` from `.proofs/fam2-release-pre-site`.

There is no lake or Postgres state to revert.

---

### Task 10c ★: The ROADMAP stamp, publish and the cleanup offer

**Spec:** §15 steps 8–10, §3 (#209), §8.2 (the deferral line); D15; the ROADMAP rule "never reword an entry".

**Files:** modify `docs/superpowers/ROADMAP.md` and `tests/test_roadmap_backlog.py`, in one commit. The line numbers below are at `b6c9a8d9`, where the ROADMAP still equals `88538c6a`'s. The link fix's release stamp may add its own ledger row, findings entry and backlog entries above these lines, so anchor on the quoted text, never on a number:
- **The ledger row,** directly above the `| Post-launch |` row (line 248 at `b6c9a8d9`; anchor on `| Post-launch |`). If the link fix's stamp put its row there, piece 2's row goes below it, still directly above `| Post-launch |`.
- **The findings entry,** first under `## Findings log (what we learned; feeds future phases)` (line 284 at `b6c9a8d9`), so above any link-fix entry.
- **#209's Status marker.** The current one, `  **Status:** open (2026-10-14) — for piece 2.`, is at line 5490 at `b6c9a8d9`.
- **New entries** after the last numbered entry (after the link fix's, if its stamp filed any).
- **A clause** at the front of the `**Updated:**` line (line 3), so before any link-fix clause.
- **The backlog test:** one new test appended at the end of the file, plus a subject list if new entries are filed.

**Interfaces:**
- Consumes:
  - the `B1:` and `deploy:` lines in `progress.md` (no `deploy:` line under the merge-only choice; Step 1);
  - Task 9b's proof note;
  - `tmp/fam2-release-counts.json`;
  - remotes `origin` (monorepo) and `govbudget` (fiscalreceipts);
  - `tests/test_roadmap_backlog.py`'s `entries()`, `STATUS_RE` (`\*\*Status:`), `EFFORT_RE`, `POINTER_RE` and `Q23_SUBJECT = "the search seeds disagree on B-21"`.
- Produces: the stamp commit, monorepo `main` and fiscalreceipts `main` advanced, and the cleanup outcome.

**Measured (2026-10-21):**
- **The highest backlog entry is #221** at `b6c9a8d9`, `9a50e28b` and `31b1e47b`, where the ROADMAP still equals `88538c6a`'s.
  - The link fix's report lists four open items for the ROADMAP, so its release stamp will likely file more:
    - the loader's `matched_obligation` re-key, with `scripts/derive_ap_links.py` added by review r2-1's M-4;
    - the withdrawn facts' `/fact/` permalinks;
    - `site_meta.link_adjudication.published`;
    - gate (a)'s recall.
  - Its fifth round-2 item, "the 10 F03500 holds await an owner ruling", was settled by round 3's withdrawal (R-DEC-LINK-2026-10-21-B), so do not expect it.
  - Number from the highest entry at stamp time.
- **#209 today** ends with exactly one plain marker, `  **Status:** open (2026-10-14) — for piece 2.`, and `test_the_aliases_ts_follow_up_is_filed_once_for_piece_2` pins its filing.
- **`govbudget/main` is a merge commit** the monorepo does not hold, so the publish needs the merge recipe again.

- [ ] **Step 1: The ROADMAP stamp**

The values come from `progress.md`, the proof note and the counts file; nothing is re-read from the lake. `<date>` is the day this step runs.

**Merge-only variant.** If the owner chose "merge without deploying" at Task 10b Step 1, there is no `deploy:` line and no rollback tag. Every deploy claim below then takes its merge-only form, so the ROADMAP never records a deploy that did not happen:
- the ledger row's Status cell, and its last cell's `SAM registrations shipped <SAM_D>`, which reads `SAM registrations not shipped (not deployed; <SAM_D> in the release export)`;
- the findings entry's header, (b);
- the `**Updated:**` clause, (e);
- the commit message (Step 3);
- the publish prompt and the report (Steps 4 and 5).

Each form is given where it applies.

(a) **The ledger row,** above `| Post-launch |`:

```markdown
| Families-2 | Platform families piece 2, the family registry: `data-seeds/platform_families.json` + `platform_family_members.csv` + `platform_family_era_lines.csv`, one loader that fails loudly (three stages), one generic history builder inside `export_site` (`platform_family_history.py`; `f15_funding_history.py` a facade), registry-driven receipt grammar and audit, `json/families/index.json` (published families only; never shipped), `platform-families propose/render/answer/ratify/check/preview`, `verify-families` in the verify-phase5 assembly; the F-15 seeded as entry #1 under owner ruling R-DEC-FAM-F15-SEED (2026-10-21) with program tags F-15/F-15EX/EPAWSS; the F-35 as entry #2 (<ratified, R-DEC-FAM-F35-B1 | draft, B1 deferred>) | A/B on one snapshot `.proofs/fam2` (A = <A short sha>, the deployed code; B = <B short sha>): §16 only (`json/families/index.json` only in B, `json_sidecars` +1), F-15 history = pin, fact stability 0 missing/moved/changed, link coverage unchanged, `/families/f-15/` snapshot and weight equal to A's ([proof](reviews/families-piece2-proof.md)) | ✅ DEPLOYED <date> at <short sha> (rollback tag <tag>) | readers see no change; F-15 history d0de9e8b…8d8f unchanged, `/families/f-15/` <raw> / <gzip> of 725,000 / 70,000 (ceilings unchanged); live `/json/families/index.json` 404; citations <N>, unchanged; SAM registrations shipped <SAM_D>; gates: npm verify overall PASS (leg r), verify-phase5 PASS (eval <x>/48) with verify-families and verify-era-map, link-coverage PASS, evals check PASS [fam2-release-*.log] |
```

Under the merge-only choice, the Status cell reads `✅ MERGED <date> at <short sha>, not deployed (owner)`, with no rollback tag. In the last cell, `SAM registrations shipped <SAM_D>` reads `SAM registrations not shipped (not deployed; <SAM_D> in the release export)`.

(b) **The findings entry,** first under `## Findings log`:

```markdown
- **<date>: Families piece 2 (the family registry) deployed.** The F-15 moved
  onto the registry with its bytes intact: on one snapshot (`.proofs/fam2`,
  taken after the contract-link fix's live build) the pre-piece code and the
  piece-2 code exported identically except the two §16 paths, the F-15 history
  kept its pin and every fact ID held [families-piece2-proof.md]. The F-15 entry
  was written once by `propose --seed-shipped f-15` under R-DEC-FAM-F15-SEED
  (owner, 2026-10-21: "approved, would process with recommendation to approve
  all") and stands on `seed_basis` until piece 3 supplies independent signals.
  `scripts/era/fact_stability.py` cannot judge a no-change A/B: its S4 rule
  expects the F-15's 72 A1 era leaves to restamp and reports them as changed
  when they do not, so the proof called its functions with no restamp expected
  (filed as #<n1>). <B1 line>
```

Under the merge-only choice, the header reads `**<date>: Families piece 2 (the family registry) merged, not deployed (owner).**`, and the rest of the entry is unchanged.

`<B1 line>` takes one of two forms:
- **Ratified:** `The F-35 is entry #2, ratified as batch R-DEC-FAM-F35-B1 on <decided_on> and not published: its B1 page showed FY2015–24 recorded actuals $116,808.4M (FY2015 8,276.5 … FY2024 13,469.6; FY2025 enacted 12,532.3; FY2026 request 11,467.0, $M), equal to the owner-reviewed figures, manifest sha256 <hex>, amendments <none|list>.`
- **Deferred:** `F-35 batch B1 was deferred by the owner on <date>; the F-35 stays a draft.` Nothing more about the F-35.

(c) **#209.** Put a new marker directly above its current `**Status:**` line, at the entry's 2-space indentation, then `  *(Earlier marker below.)*`. Restyle only the old line's label; its text stays:

```markdown
  **Status:** open (<date>) — re-deferred to piece 4 by the piece-2 spec §3
  (owner, 2026-10-21): making the registry the alias source now would change
  `search_quick.json` and the search chips, which readers see; piece 2 reserves
  the `aliases` family field.
  *(Earlier marker below.)*
  **Status (2026-10-14):** open (2026-10-14) — for piece 2.
```

(d) **New entries,** numbered from the highest at stamp time: `grep -oE '^- \*\*#[0-9]+' docs/superpowers/ROADMAP.md | tr -dc '0-9\n' | sort -n | tail -1`, plus 1, and so on. The three entries below are always filed (R1, R17). Any other finding in `progress.md`'s `findings:` lines gets an entry in the same format.

```markdown
- **#<n1> `fact_stability.py` reports a no-change A/B as 72 changed facts.**
  `compare_citations` treats every F-15 A1 era leaf (F01500 39, F015EX 18,
  F15EWS 15) as one that must move `pe_bli` null → code and `retrieved_at` to its
  `T` form, the S4 decade-tier switch; on two exports of one code it reports all
  72 as `changed … f15_restamp` and FAIL. The piece-2 proof (Task 9a Step 9)
  called its functions with an empty leaf map instead. Fix: a `--no-f15-restamp`
  mode (or an `--expected-f15 0` that skips the leaf map), with a test on two
  identical trees. Source: `scripts/era/fact_stability.py`. Effort: hours.
  **Status:** open (<date>).
- **#<n2> Re-proposing a ratified family is undefined.** `propose` refuses a
  `ratified` or `published` family and `ratify` flips `draft` to `ratified`, so
  the re-propose rules (reviewed `excluded`/`rejected` rows never re-proposed; a
  lake change to a ratified row held for review) fire only on fixtures in piece 2.
  Piece 3 must define how a ratified or published family's rows are re-measured
  and re-reviewed; until then a moved F-15 or ratified F-35 line stops a release
  for the owner (plan Task 10a Step 3). Source:
  `src/govbudget/platform_family_review.py`. Effort: days.
  **Status:** open (<date>) — for piece 3.
- **#<n3> A non-self `fact:` ref cannot yet satisfy the evidence bar.** Spec §7.5
  counts a `fact:` naming another line's book text as an independent signal, but
  stage 1 cannot tell it from the member's own narrative without the export, so
  piece 2 never lets a `fact:` clear the bar (plan R1). Piece 3's evidence
  engine should add the non-self check at stage 3. Source:
  `src/govbudget/platform_families.py`. Effort: days.
  **Status:** open (<date>) — for piece 3.
```

(e) **The `**Updated:**` line.** Put `<date> (families piece 2 deployed at <short sha>: the family registry, the F-15 on it byte-identical, the F-35 <ratified|draft>; #209 re-deferred to piece 4; #<n1>–#<n3> filed);` directly after `**Updated:** `, and leave the rest of the line unchanged. Under the merge-only choice, `deployed at <short sha>` reads `merged at <short sha>, not deployed (owner)`.

- [ ] **Step 2: The backlog test**

Append this to `tests/test_roadmap_backlog.py`:

```python


# Re-deferred by the piece-2 stamp (Task 10c; spec §3, owner 2026-10-21): #209
# stays open for piece 4, its 2026-10-14 marker relabelled, never reworded.
def test_209_is_re_deferred_to_piece_4_and_stays_open():
    hits = [(num, body) for num, body in entries() if Q23_SUBJECT in body]
    assert len(hits) == 1, f"{Q23_SUBJECT!r} filed {len(hits)} times, want 1"
    num, body = hits[0]
    assert num == 209
    assert "re-deferred to piece 4 by the piece-2 spec §3" in body
    assert "**Status (2026-10-14):** open (2026-10-14) — for piece 2." in body
    assert len(STATUS_RE.findall(body)) == 1


# Filed by the piece-2 stamp (Task 10c), by phrase.
FAMILIES_PIECE_2_FINDINGS = [
    "reports a no-change A/B as 72 changed facts",
    "Re-proposing a ratified family is undefined",
    "A non-self `fact:` ref cannot yet satisfy the evidence bar",
]


@pytest.mark.parametrize("subject", FAMILIES_PIECE_2_FINDINGS)
def test_the_piece_2_findings_are_filed_once_with_effort_and_source(subject):
    hits = [(num, body) for num, body in entries() if subject in body]
    assert len(hits) == 1, f"{subject!r} filed {len(hits)} times, want 1"
    num, body = hits[0]
    assert EFFORT_RE.search(body), f"#{num} has no `Effort: hours|days|weeks`"
    assert POINTER_RE.search(body), f"#{num} names no source path"
    assert body.rstrip().splitlines()[-1].strip().startswith("**Status:** "), f"#{num} does not end with its Status line"
```

Add one phrase to `FAMILIES_PIECE_2_FINDINGS` for each further entry Step 1 (d) filed. Each phrase must sit on one line of its entry.

- [ ] **Step 3: Run the ledger test, then commit the stamp**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_roadmap_backlog.py -q 2>&1 | tail -1`

Expected: `… passed`, 0 failed: the earlier count plus `1 + len(FAMILIES_PIECE_2_FINDINGS)`. A failure names the entry. Fix the stamp (numbering, one plain Status line, the effort word, a source path), never the test.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/docs/superpowers/ROADMAP.md GovBudget/tests/test_roadmap_backlog.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(roadmap): stamp families piece 2 (the family registry; <short sha>, rollback tag <tag>); #209 re-deferred to piece 4" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Under the merge-only choice, the first `-m` reads `docs(roadmap): stamp families piece 2 (the family registry; merged at <short sha>, not deployed); #209 re-deferred to piece 4`.

Expected: the commit, `2 files changed`.

- [ ] **Step 4: ★ The owner's go-ahead to publish, then publish**

Ask: "Deploy verified. Push the branch to monorepo `main` (fast-forward only), fast-forward the main checkout, and publish GovBudget to fiscalreceipts `main`?" Under the merge-only choice, the prompt opens "Not deployed, as you chose; the release export and the gates are verified." instead of "Deploy verified." Wait for an explicit yes. Then:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git fetch origin && git merge-base --is-ancestor origin/main HEAD && echo "fast-forward from origin/main" && git push origin "HEAD:refs/heads/main"
```

Expected: `fast-forward from origin/main` and the push. If the ancestor check prints nothing, stop: `origin/main` moved. Never force.

Run the next block only between :25 and :10 past the hour:

```bash
MIN=$(date +%M) && if [ "$MIN" -ge 10 ] && [ "$MIN" -lt 25 ]; then echo "WAIT: minute $MIN is near the SAM tick"; else cd /Users/andeslee/Documents/Cursor-Projects && git rev-parse --abbrev-ref HEAD && git merge --ff-only origin/main && git log --oneline -1 && git status --porcelain --untracked-files=no; fi
```

Expected: `main`, a fast-forward to the pushed sha, and only the workspace's own modified `CLAUDE.md`. Piece 2 adds no dbt test, so the main checkout needs no new `dbt parse`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git fetch govbudget && git subtree split --prefix=GovBudget -b publish-fam2 && SPLIT=$(git rev-parse publish-fam2) && echo "SPLIT=${SPLIT}" && (git merge-base --is-ancestor govbudget/main "${SPLIT}" && echo "fast-forward" || echo "needs merge")
```

Expected: the split sha and `needs merge`.
- **`fast-forward`:** run `git branch publish-fam2-merge publish-fam2` and skip the next block.
- **A stale `publish-fam2`** (`fatal: branch 'publish-fam2' is not an ancestor …`): inspect it (`git log -1 publish-fam2`), run `git branch -D publish-fam2`, and re-run.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && GT=$(git rev-parse 'govbudget/main^{tree}') && MATCH=$(git log --format=%H HEAD | while read c; do [ "$(git rev-parse "${c}:GovBudget")" = "${GT}" ] && echo "${c}" && break; done) && echo "govbudget/main tree = ${MATCH}:GovBudget" && SPLIT=$(git rev-parse publish-fam2) && MERGE=$(GIT_AUTHOR_NAME="Andes Lee" GIT_AUTHOR_EMAIL="andes.lee444@gmail.com" GIT_COMMITTER_NAME="Andes Lee" GIT_COMMITTER_EMAIL="andes.lee444@gmail.com" git commit-tree "${SPLIT}^{tree}" -p "${SPLIT}" -p govbudget/main -m "Merge families piece 2 (the family registry) into fiscalreceipts" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>") && git merge-base --is-ancestor govbudget/main "${MERGE}" && [ "$(git rev-parse "${MERGE}^{tree}")" = "$(git rev-parse HEAD:GovBudget)" ] && git branch publish-fam2-merge "${MERGE}" && echo "MERGE=${MERGE} ok, parked in refs/heads/publish-fam2-merge"
```

Expected: one monorepo commit whose `GovBudget` tree equals `govbudget/main`'s (the link fix's publish), then `MERGE=<sha> ok, parked …`. If there is no match, stop: fiscalreceipts holds content the monorepo lacks. Never force.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families || exit 1
git rev-parse --verify -q refs/heads/publish-fam2-merge > /dev/null || { echo "STOP: refs/heads/publish-fam2-merge is missing"; exit 1; }
git push govbudget publish-fam2-merge:refs/heads/main && git branch -D publish-fam2 publish-fam2-merge && git fetch govbudget && [ "$(git rev-parse 'govbudget/main^{tree}')" = "$(git rev-parse HEAD:GovBudget)" ] && echo "fiscalreceipts main == monorepo GovBudget"
```

Expected: the push, both branches deleted, and `fiscalreceipts main == monorepo GovBudget`. The push cannot deploy, because `GovBudget/vercel.json` sets `git.deploymentEnabled: false`.

- [ ] **Step 5: Report, and offer the cleanup**

First copy the proof and release logs into the ledger (read-only on `.proofs`):

```bash
LEDGER=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/families-piece2/proof-logs && mkdir -p "$LEDGER/fam2-release" && cp -cR /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fam2-logs "$LEDGER/fam2-logs" && cp -c /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fam2-release-* "$LEDGER/fam2-release/" && ls "$LEDGER" && ls "$LEDGER/fam2-release" | wc -l
```

Expected: `fam2-logs`, `fam2-release` and `fam2-snapshot.md`, then the count of release files copied.

Report to the owner:
- the deployed sha and the rollback tag, or, under the merge-only choice, the merged sha and "not deployed";
- `SAM_D`;
- B1's outcome;
- the publish shas.

Then ask whether to remove the piece-2 proof state. Nothing is removed without a yes. The list:
- under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/`: `fam2`, `fam2-A`, `fam2-B`, `fam2-B2`, `fam2-rel`, `fam2-preview-f-35-B1`, `fam2-logs` (copied above), `fam2-release-pre-site`, `fam2-release-export.sha256` and `fam2-release-export.built_at`;
- the scratch databases `govbudget_proof_fam2` and `govbudget_proof_fam2_rel`;
- the A worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fam2-proof-a`.

On a yes:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && "${GOVBUDGET_PG_BIN:?}/dropdb" govbudget_proof_fam2 && "$GOVBUDGET_PG_BIN/dropdb" govbudget_proof_fam2_rel && git -C .. worktree remove --force /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fam2-proof-a && git -C .. worktree list | grep -c fam2-proof-a; cd "${GOVBUDGET_PROOFS:?}" && rm -rf fam2 fam2-A fam2-B fam2-B2 fam2-rel fam2-preview-f-35-B1 fam2-logs fam2-release-pre-site fam2-release-export.sha256 fam2-release-export.built_at && ls -A "$GOVBUDGET_PROOFS" | grep -c '^fam2'
```

Expected: `0` (the A worktree is gone), then `0` (no `fam2*` entry left). The ledger copies stay.
