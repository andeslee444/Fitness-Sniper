# Procurement History Before FY2024 (Families Piece 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each executor reads this README (Global Constraints and Binding Cross-Task Decisions) plus its own file under `tasks/`. `notes.md` keeps the drafting groups' full contract notes and measurements as background.

**Goal:** Publish the PB2017–PB2023 procurement editions (FY2015–21 actuals, enacted, requests) on about 880 procurement program pages, each point cited to its own workbook cell and, where the matcher finds it, its PDF, without changing any existing fact ID.

**Architecture:** Keep the budget line code that era P-1 workbooks print in column I (`line_item_code`, migration 021) and leave the era key (`{account}-{org}-L{line}`) as the row and fact identity. Record one owner-approved decision per code chain in a dbt seed. Build a program-grain decade table beside `fct_decade_series`. Switch the exporter's decade tier to that table, fencing the F-15 page, lineage funding lines and `/years/`. Prove "nothing else changed" with fresh A/B exports on pinned snapshots.

**Tech Stack:** Python 3.12 (uv, psycopg 3, openpyxl, DuckDB 1.5), dbt-duckdb, PostgreSQL 17 (local), Next.js 16 / React 19 / vitest, the site gate registry (`npm run verify`), launchd-free shell steps.

**Spec:** [`docs/superpowers/specs/2026-10-02-era-procurement-history-design.md`](../../specs/2026-10-02-era-procurement-history-design.md) (approved 2026-10-02, with the class rulings R-DEC-ERA-SAME / -EXCLUDE / -HISTORY and the plan-review owner decisions recorded in its dated notes). Parent: [`2026-10-02-platform-families-overview.md`](../../specs/2026-10-02-platform-families-overview.md).

## Global Constraints

- **Worktree.** Git toplevel `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families`, branch `families-2026-10-02`. The project is its `GovBudget/` subdirectory, and all paths in this plan are relative to that. Run commands from `GovBudget/` unless a step says otherwise.
- **Commits.** `--author="Andes Lee <andes.lee444@gmail.com>"`; the message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Commit from the toplevel with explicit pathspecs (`git add GovBudget/<path>`). Never `git stash` (the stack is shared with other sessions). Never push the branch to `origin`; Task 23 publishes.
- **Python:** `uv run --project . <cmd>` from `GovBudget/` (Task 1 runs `uv sync`). **Site:** `npm` in `GovBudget/site`. `node_modules` must be a real directory, never a symlink (Task 1 runs `npm ci`).
- **Environment.** `source scripts/era/env.sh` (Task 1) exports `GOVBUDGET_DATA` and `GOVBUDGET_DUCKDB` (live lake: `/Users/andeslee/Documents/Cursor-Projects/GovBudget/data`), plus `GOVBUDGET_PG_DSN=postgresql://localhost/govbudget`, `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres` (the throwaway test cluster), `GOVBUDGET_PG_BIN` and `GOVBUDGET_PROOFS=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs`. `config.py` ignores `GOVBUDGET_DUCKDB` (it derives the DuckDB path from `GOVBUDGET_DATA`); dbt and `govbudget build` read it, so set both.
- **Tests never touch the real database.** Postgres-backed tests use the throwaway cluster on port 55432 that Task 1 creates.
- **Shared-state writes.** Writes to the shared Postgres/lake happen only in:
  - Tasks 8 and 9: the S1/S1b database writes;
  - Tasks 13, 15 and 16: selective `dbt build --select` of the nodes they add or change, never a full `govbudget build`;
  - Task 21: snapshot clones only;
  - Task 23: the release export, plus a recovery `jbooks export-facts` and selective build only if the lake lost the branch's state.

  Each write is additive and followed by a proof on a snapshot.
- **Scratch proof databases** named `govbudget_proof_<name>` may be created and dropped on `postgresql://localhost` by `govbudget proof snapshot`. Never create, alter or drop any other database.
- **The SAM window.** The hourly SAM launchd job writes `data/parquet/sam` at :17. Do not start any step that reads or writes the live lake during minutes :15–:20 past the hour; steps that guard with margin use :12–:22. This covers snapshots, live `export-site`, live `jbooks export-facts` and live dbt builds. Check `date +%M` first, and start only if the step will finish before the next :15. Exports and dbt runs against a snapshot or its clone are exempt, as is `dbt parse`.
- **Site builds in the worktree** read `GovBudget/data/site` relative to `site/`, and the build needs this worktree's own `dbt/target/manifest.json`. Task 1 creates the `data/site` symlink (excluded by the shared `.git/info/exclude`) and runs `dbt parse`. Tasks 21–23 repoint the `data/*` symlinks at the snapshot or lake they build against.
- **Never** raise a page-weight ceiling or the `/years/` 4 MiB cap. Never trim existing disclosure prose without the owner. Never re-key `pe_bli`: era keys stay the lake and fact identity.
- **Era keys** are selected with `era_keys.is_era_procurement_key(pe_bli)` (or `'^\d{4}[A-Z]-[A-Z]+-L'`), never "every PB2017–23 P-1 row": from Task 9 on, era editions also hold `9999999999` classified rows.
- **Lake hazard until merge.** A `jbooks export-facts` run from the main checkout rewrites `data/parquet/jbooks/budget_lines.parquet` without `line_item_code`, which breaks every branch dbt build. If that happens, re-run `jbooks export-facts` from this branch first (Task 23 Step 1 checks).

## Owner Decisions Already Made (do not re-ask)

| Date | Decision | Where recorded |
|---|---|---|
| 2026-10-02 | Platform families; reader name "family" at `/families/<id>/`; Claude pre-fills, owner approves; era-only lines stay data with stated successors (R-DEC-FAM-*) | overview §1, ROADMAP |
| 2026-10-02 | Spec approved with R-DEC-ERA-SAME / -EXCLUDE / -HISTORY | spec status, ROADMAP |
| 2026-10-02 | R-DEC-ERA-EXCLUDE kept with its corrected figure: the two `0390D` Chem Demil lines carry $5.83B and have no page in any edition (#194) | spec §5.2 note, ROADMAP |
| 2026-10-02 | The per-edition era table renders on `/downloads/`, counts only; dollars stay in `json/era_map_summary.json` | spec §6.4 note, ROADMAP |
| 2026-10-02 | `p1_era_line_map` shows "tier pending" on `/data/`; the `/methodology/` pending-ledger clause is rewritten at equal length; the `/data/` inventory CSS hoist pays for the row | spec §6.4 note, ROADMAP |

**Still needs the owner during execution:** Task 15, the individual review batches (about 125 chains, about 25 per batch); Task 22, the exact F-15 strings; Task 23, a go before the production deploy.

## Binding Cross-Task Decisions

These came out of drafting and cross-review. They override the spec's wording where they differ, and each is noted in the spec or in `notes.md`.

1. **Proof layout (Task 3).** `govbudget proof snapshot --out DIR --scratch-db NAME` writes `DIR/{duckdb/govbudget.duckdb, parquet/, site/, raw_docs/, manifest.jsonl, pg/, snapshot.json, env.sh}`. The snapshot directory itself is the `GOVBUDGET_DATA` root. The copy's 18 DuckDB views and `jbook_documents.file_path` (in the scratch database only) are repointed at the copy. Each export runs in its own `cp -c -R DIR RUN` clone under `source DIR/env.sh RUN`. `govbudget proof diff A B [--expect RULES.json] [--report FILE]` takes rules as a JSON list of `{path, why, status?, pointer?, change?, required?}`; its last line is `proof diff: PASS|FAIL`, or `EQUAL|DIFFERENT` when there is no `--expect`.
2. **Migration 021 lands in Task 6** with the loader, since loader tests build their database through `migrate`. Task 7 adds `line_item_code` to `export_facts` (with `order by id`) and to `stg_budget_lines`, plus the dbt fixture column.
3. **`review.csv` schema (Task 11)** is `era_map.REVIEW_COLUMNS`, in this order: `chain_id, first_edition, last_edition, titles_by_edition, modern_title, accounts, continuity, actuals_k, proposed_decision, reason, program_account, program_org, successor_code, keys_sha256, decision, note`. `ratify(*, review_csv, seed_path, batch, decided_on, duckdb_path)`. CLI: `govbudget era-map ratify --batch B<n> --decided-on DATE`.
4. **Two ratify rules.**
   - (a) Whole chains only: a batch must decide every edition of every chain it touches.
   - (b) On an organization-spanning code, at most one organization per page grain and edition is `same_program`. `propose` pre-fills `history_only` for the other organization, and `assert_p1_era_map_org_split` enforces the same rule in dbt.
5. **Collision pins (Task 11 → 13, 16).** For a chain on one of the 13 PB2026 collision codes decided `same_program` or `history_only`, the seed sets both `program_account` and `program_org`. The program table maps them to `fct_decade_series`' axis shape: account only for the 10 account-collision codes, organization only for `20`/`30`/`500`.
6. **`keys_sha256`** is the sha256 hex of `"\n".join(sorted(f"{edition}|{era_key}|{ba or ''}|{filed_title or ''}"))` in UTF-8, identical in Python (`era_map.keys_sha256`) and SQL (`sha256(string_agg(line, chr(10) order by line))`).
7. **Program table grain (Task 16).**
   - Grain: (`program_key, account, organization, fy, edition_year, map_basis`), unique on the first five columns among `native` and `era_line_map` rows.
   - Columns, in order: `program_key, fy, edition_year, amount_type_kind, amount, amount_thousands, scenario, amount_type, account, organization, n_source_rows, source_fact_id, map_basis, source_keys`.
   - There is no `pe_bli` column, and `map_basis` is one of `native`, `era_line_map`, `era_history_only`.
8. **`decade_era_map` (Tasks 4, 17).**
   - Key: `fact_id_derived("decade_era_map", f"{program_key}|{account}|{organization}|{edition}", amount_type)`, with account and organization blank when not set.
   - Formula: `sum(budget_lines.amount_thousands where era_line_map='{program_key}'[ and account=…][ and organization=…] and amount_type={at} and edition={edition})`.
   - Inputs are sorted by fact ID.
9. **`verify_era_map` (Task 14 → 20).**
   - Legs are public `leg_a_workbooks`, `leg_b_decisions`, `leg_c_f15`, `leg_d_fact_ids`, `leg_e_published_map` and `leg_f_history_pin`, each returning `_leg(ok, summary, failures)`.
   - `run_verify_era_map` dispatches with `if`/`elif`; Task 20 replaces the `else` branch that fails d–f.
   - The F-15 pin `tests/fixtures/f15/history.sha256` is 64 lowercase hex characters plus a newline.
10. **Link coverage counts distinct fact IDs.** Live baseline: 45,151 distinct figures (44,747 (a), 404 (b)), 100.00% source-linked, 99.11% PDF-highlighted, 2,437 of 2,562 pages fully highlighted. The overview's 55,749 counts appearances, and the tool reproduces that number too. Task 23 and the ROADMAP quote the distinct-figure numbers.
11. **Research-pass deltas under the spec's own rules (Task 11).** R-DEC-ERA-SAME covers 810 chains ($651.58B); 125 chains go to review; `30|0300D|DODEA` leaves the ruling. `20|0300D|DSS` and `500|0300D|DCMA` are reviewed as R2, which gives the same outcome as the spec's examples.
12. **The era table is on `/downloads/`, counts only (owner decision).** Datatruth leg (s) checks it against `json/era_map_summary.json`. That file is written by `write_era_map_summary(*, site_dir, duckdb_path)`, called after the receipts step in `cli._export_budget_pdf_evidence`.
13. **The dbt assertion count** on `/methodology/` and in `site_meta.build_checks.dbt_assertions` moves from 163 to 196 as Tasks 13 and 16 add tests. It is an expected difference, not a fence breach.

## Tasks

Steps S0–S6 follow spec §9. Owner touchpoints are marked ★.

| # | Task | Spec step | File |
|---|---|---|---|
| 1 | Workspace and test harness | S0 | [tasks/01-workspace-and-test-harness.md](tasks/01-workspace-and-test-harness.md) |
| 2 | Record corrections and filed follow-ups (#193–#197) | S0 | [tasks/02-record-corrections-and-filed-follow-ups.md](tasks/02-record-corrections-and-filed-follow-ups.md) |
| 3 | Proof tooling: pinned snapshots and the masked diff | S0 | [tasks/03-proof-tooling.md](tasks/03-proof-tooling.md) |
| 4 | F-15 hermetic fixtures, sha pin, golden test, page snapshot (V5) | S0 | [tasks/04-f15-fixtures.md](tasks/04-f15-fixtures.md) |
| 5 | Link-coverage tool and baseline; re-measured page-weight stamps (V9) | S0 | [tasks/05-link-coverage.md](tasks/05-link-coverage.md) |
| 6 | Loader split, printed-code capture, tripwire, migration 021 (V2) | S1 | [tasks/06-loader-split.md](tasks/06-loader-split.md) |
| 7 | `line_item_code` through `export_facts` and `stg_budget_lines` | S1 | [tasks/07-export-facts-and-staging.md](tasks/07-export-facts-and-staging.md) |
| 8 | S1: no-write diff (V1), transactional re-run, proof, live write | S1 | [tasks/08-s1-reload.md](tasks/08-s1-reload.md) |
| 9 | S1b: era Classified Programs rows | S1b | [tasks/09-s1b-classified-rows.md](tasks/09-s1b-classified-rows.md) |
| 10 | `era_map` pure functions: normalize, classify, chains, rulings | S2 | [tasks/10-era-map-functions.md](tasks/10-era-map-functions.md) |
| 11 | `propose`: research outputs, class rulings to seed, successors | S2 | [tasks/11-propose.md](tasks/11-propose.md) |
| 12 | `ratify`, `check`, seed config, CLI | S2 | [tasks/12-ratify-check-cli.md](tasks/12-ratify-check-cli.md) |
| 13 | dbt `p1_era_line_map` and its tests (V3) | S2 | [tasks/13-dbt-era-line-map.md](tasks/13-dbt-era-line-map.md) |
| 14 | `verify-era-map` legs a–c and CLI (V4) | S2 | [tasks/14-verify-era-map-a-c.md](tasks/14-verify-era-map-a-c.md) |
| 15 ★ | Owner review batches → ratify → close S2 | S2 | [tasks/15-owner-review-batches.md](tasks/15-owner-review-batches.md) |
| 16 | dbt `fct_program_decade_series` and its tests (V3) | S3 | [tasks/16-dbt-program-decade-series.md](tasks/16-dbt-program-decade-series.md) |
| 17 | Exporter decade-tier switch | S4 | [tasks/17-exporter-decade-tier.md](tasks/17-exporter-decade-tier.md) |
| 18 | Fences: lineage, `/years/`, the F-15 browser | S4 | [tasks/18-fences.md](tasks/18-fences.md) |
| 19 | Map dataset registration, era summary and `/downloads/` table, methodology | S4 | [tasks/19-map-dataset-and-copy.md](tasks/19-map-dataset-and-copy.md) |
| 20 | `verify-era-map` legs d–f and the `verify-phase5` assembly | S4 | [tasks/20-verify-era-map-d-f.md](tasks/20-verify-era-map-d-f.md) |
| 21 | S4 proof: pre-S4 vs S4 export on one post-S3 snapshot (V5–V8) | S4 | [tasks/21-s4-proof.md](tasks/21-s4-proof.md) |
| 22 ★ | F-15 corrections | S5 | [tasks/22-f15-corrections.md](tasks/22-f15-corrections.md) |
| 23 ★ | Release: gates, deploy, ROADMAP stamp, publish | S6 | [tasks/23-release.md](tasks/23-release.md) |

**Order.**
- Tasks 1 → 2 → 3 → 4 → 5 (S0).
- Then 6 → 7 → 8 → 9 (S1, S1b).
- Then 10 → 11 → 12 → 13 → 14 → 15 (S2). Task 15 is the critical path: no chain may be undecided before Task 17.
- Then 16 (S3), 17 → 18 → 19 → 20 → 21 (S4), 22 (S5) and 23 (S6).
- Tasks 10–14 do not depend on Task 9 and may start once Task 8 has loaded `line_item_code` into the lake.
