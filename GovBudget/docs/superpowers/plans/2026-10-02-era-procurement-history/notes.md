# Drafting notes — families piece 1

Background for executors: each drafting group's contract notes, resolved issues and read-only measurements (2026-10-02), verbatim. Where a note and the README's *Binding Cross-Task Decisions* differ, the README wins; where a note proposed a spec correction or owner decision, it is already recorded in the spec's dated notes.


## G1a — Tasks 1–3

PLAN HEADER (G1a owns these global-constraint clarifications; the assembler copies them into the plan header's "Global constraints", replacing the contract's bullets on shared writes and on the SAM window):

- **Writes to the shared Postgres/lake** happen ONLY in Tasks 8, 9 (S1/S1b DB writes), 13/16 (`govbudget build` adds tables), 15 (the build that loads the ratified seed and rebuilds `p1_era_line_map` to close S2), 21 (snapshot builds) and 23 (release export). Each is additive and followed by an export diff on a snapshot.
- **Scratch proof databases are allowed.** Databases named `govbudget_proof_<name>` may be created and dropped on the shared server (`postgresql://localhost`) by `govbudget proof snapshot --scratch-db govbudget_proof_<name>` (Task 3 Step 11's smoke run, Tasks 8, 9 and 21) and dropped with `"$GOVBUDGET_PG_BIN/psql" postgresql://localhost/postgres -c 'drop database govbudget_proof_<name>'` when their snapshot is deleted. They are not writes to `govbudget`: a snapshot only reads `govbudget` (`pg_dump`), restores into its own scratch database, and rewrites `jbook_documents.file_path` in that scratch copy only. Never create, alter or drop any other database on the shared server.
- **SAM window.** The hourly SAM launchd job writes `data/parquet/sam` at :17. No step that reads or writes the LIVE lake (`/Users/andeslee/Documents/Cursor-Projects/GovBudget/data`) may overlap minutes :15–:20 past the hour. That covers snapshot copies (`govbudget proof snapshot`), a live `export-site`, a live `jbooks export-facts` and live dbt builds (`govbudget build` with `GOVBUDGET_DATA`/`GOVBUDGET_DUCKDB` on the live lake). Check `date +%M` first and start such a step only when it will finish before the next :15. Exports and dbt builds run against a snapshot or its run-dir clone are exempt: after Task 3's view rewrite they read only pinned files. Task 1's `dbt parse` reads no lake and opens no warehouse, so it is exempt too.

CONTRACT ISSUE (G1a-1) — a byte copy of the DuckDB file is not a pinned snapshot. dbt materializes most marts as views, and 18 of the 37 views in `data/duckdb/govbudget.duckdb` embed the absolute path `read_parquet('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/...')` of the lake they were built against (measured read-only 2026-10-02: `select view_name, sql from duckdb_views() where not internal`). Spec §8's "staged parquets are looked up beside the DuckDB file" covers the exporter's own `_stage_parquet_path`/`_lake_parquet_dir` reads (`export_site.py:2347-2367`, `:9815-9831`), not these views. Smallest fix, in Task 3: `proof snapshot` clones `data/parquet` first, then rewrites every such view in the COPY with `CREATE OR REPLACE VIEW` to read the clone (verified on a scratch clone: 18 rewritten, 0 left naming the live lake, row counts equal). No consumer changes.

CONTRACT ISSUE (G1a-2) — the exporter does not read raw documents through `config.RAW_DOCS_DIR`. Its document loop (`export_site.py:2829-2855`) stats and copies `jbook_documents.file_path`, an absolute path stored in Postgres; all 254 rows point into the live `data/raw_docs/` (234 `downloaded`, 20 `superseded`). Smallest fix, in Task 3: the snapshot clones `raw_docs` and rewrites `file_path` in the SCRATCH database only, after computing the manifest's table digests (so digests describe the dump as taken and compare across snapshots).

CONTRACT ISSUE (G1a-3) — `config.py` ignores `GOVBUDGET_DUCKDB`. `DUCKDB_PATH` is always `$GOVBUDGET_DATA/duckdb/govbudget.duckdb` (`config.py:58`); only dbt (`dbt/profiles.yml:6`) and `govbudget build` (`cli.py:2012-2013`) read `GOVBUDGET_DUCKDB`. Every env file in this plan sets both, consistently. `RESEARCH_DIR` is `ROOT/data/research` (`config.py:63`), i.e. the code checkout's committed files, not the snapshot; the worktree's copies of the four research inputs the exporter reads equal main's today (checked with `git ls-files -s` and `diff`). The contract's "the worktree has no data/ directory" is not quite true: the worktree has the tracked `data/manifest.jsonl` and `data/research/`.

CONTRACT ISSUE (G1a-4) — `SITE_DIR` is `$GOVBUDGET_DATA/site`, so two exports cannot share one data dir without the second starting from the first one's output (which spec §8 forbids). Task 3's snapshot writes `<snap>/env.sh [RUN_DIR]`: each export runs in its own `cp -c -R` clone of the snapshot (seconds, no extra space); the clone's DuckDB views keep reading `<snap>/parquet` and its documents resolve to `<snap>/raw_docs`, both read-only.

CONTRACT ISSUE (G1a-5) — the contract assigns no task to take the S0 snapshot. Task 3 builds the tool and smoke-tests it on real data, then deletes the smoke snapshot and its scratch database. The consumer (Task 8) should take `.proofs/s0` immediately before S1's database write and the post-S1 snapshot immediately after, inside one `:20`–`:15` stretch: the hourly SAM job rewrites `data/parquet/sam`, which `dim_entities` reads through a view, so a snapshot taken hours earlier would show SAM drift as export differences. Task 3's smoke step (Step 11) creates and then drops a scratch database on the shared server, never touching `govbudget`; the PLAN HEADER above allows that explicitly ("Scratch proof databases are allowed"), so Step 11 stays.

CONTRACT ISSUE (G1a-6) — names this group adds beyond the contract (all additive): `proof.load_expectations(path) -> list[dict]`, `proof.check_expectations(report, rules) -> dict`, `proof.format_report(report, verdict=None) -> list[str]`, `proof.is_equal(report) -> bool`; CLI flags `proof diff --report FILE`, `proof snapshot --data-dir DIR --pg-dsn DSN` (default `config.DATA_DIR`, `config.PG_DSN`); snapshot files `<snap>/snapshot.json` and `<snap>/env.sh`; `scripts/era/env.sh` also exports `GOVBUDGET_DUCKDB`, `GOVBUDGET_PG_BIN` and `GOVBUDGET_PROOFS`.

CONTRACT ISSUE (G1a-7) — two facts in spec §11.8 measured differently: the 0390D `O&M`/`RDT&E` lines are dropped by PB2024 and PB2025 too, not only PB2026 (#194 records all three); the JLTV BA1 book IS registered (`jbook_documents` id 347) but as `superseded`, which is why it is not hosted (#195 says so).


## G1b — Task 4

CONTRACT ISSUE (1) — the site build cannot be pointed at data with `GOVBUDGET_DATA`. It reads `site/../data/site` unconditionally (`site/scripts/prepare-assets.mjs:17-19`, `site/src/lib/data.ts:36-39`, `site/src/lib/family-funding-history-data.ts:8`). The worktree's `GovBudget/data/` is a real directory holding only the tracked `manifest.jsonl` and `research/` (the contract's "the worktree has no data/ directory" is not quite true), so every site build in the worktree (Tasks 4, 18, 21, 23) needs `GovBudget/data/site` to exist. Smallest fix: a symlink `GovBudget/data/site -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site` (or a snapshot's site copy), excluded through the shared `info/exclude` because `.gitignore`'s `data/site/` directory pattern does not match a symlink (the shared `/Users/andeslee/Documents/Cursor-Projects/.git/info/exclude` already lists `GovBudget/data/site`, line 26). Task 4 Step 13 creates the link idempotently; Task 1 may create it first.

CONTRACT ISSUE (2) — the contract names `tests/fixtures/f15/history.sha256` but not its format. Task 4 defines it as exactly 64 lowercase hex characters followed by one newline (no file name). Task 20's leg f must read it with `Path(...).read_text().strip()`.

CONTRACT ISSUE (3) — the contract fixes the surface string `"decade_era_map"` but not the fact-ID key or formula text. Task 4's V5 fresh-state test encodes spec §6.1 verbatim: `fact_id_derived("decade_era_map", f"{program_key}|{account}|{organization}|{edition}", amount_type)` with blank account/organization for a non-collision code (so `"F01500|||2018"`), formula `sum(budget_lines.amount_thousands where era_line_map='{program_key}' and amount_type={at} and edition={edition})`, inputs sorted by fact ID. Task 17 must mint byte-identical text; if it introduces a helper, it should switch this test to import it in the same commit.

CONTRACT ISSUE (4), an addition: `site/scripts/f15-page-snapshot.mjs` also takes `--check FILE` (exit 1 and the first differing path), so Tasks 18 and 21 can compare a build against the S0 baseline with one command.


## G1c — Task 5

CONTRACT ISSUE: (additive, nothing renamed) Task 5 defines public names beyond the contract's two
functions, because the CLI and the S6 check need them: `baseline_from_report(report: dict) -> dict`,
`absolute_violations(report: dict) -> list[str]`, and the constants `BASELINE_SCHEMA_VERSION = 1`,
`CLASSES = ("a", "b", "c", "d")`, `SECTIONS` and `DEFINITION`. Each `report["pages"][slug]` also
carries a `not_a` map ({fid: class} for the page's figures that are not (a)). Smallest fix: add these
to the contract's link-coverage block. Task 23 only needs the CLI.

CONTRACT ISSUE: how figures are counted. The overview's "55,749 budget figures" counts appearances
in five sidecar sections, so the same fact ID shown twice on one page (a summary card repeating a
budget line) is counted twice. The tool scores **distinct fact IDs** and reads seven sections. The
two extra sections are `fy26_split.disc` and `fy26_split.lines`: 1,642 appearances that the research
pass left out, 3 of them (b). Measured on the live export: 45,151 distinct figures (44,747 a,
404 b, 0 c, 0 d), 100.00% source-linked, 99.11% PDF-highlighted, and 2,437 of 2,562 pages fully
PDF-highlighted. The per-section appearance counts in the report reproduce the research numbers
exactly: 55,749 appearances, 55,328 of them (a), plus 42,153 workbook citations, 41,772 of them (a).
Smallest fix: Task 23 and the ROADMAP stamp quote the tool's distinct-figure numbers.

CONTRACT ISSUE: spec §6.4 quotes `/coverage/` at "85,710 / 20,288 against 103,000 / 20,750". That
is the stale `measured` stamp. Production (curl + zlib level 9, 2026-10-02) and the 2026-10-02
deploy build's gate 1 both weigh it at **86,203 / 20,458**. That leaves 292 gzip bytes of
headroom, not 462. Smallest fix: Task 19 sizes the era summary table against the stamp Task 5
re-measures and decides which page it renders on. Task 2 adds the dated correction note under
spec §6.4. Task 5 does not edit the spec.

CONTRACT ISSUE: the contract says the worktree has no data/ directory. It does have one, holding the
tracked `data/research/` and `data/manifest.jsonl`, and the site build reads
`GovBudget/data/site` relative to `site/`. Task 5's build needs `data/site` to be a symlink into the
main lake (the worktree convention in `config._lake_path`). Task 1 creates that link. Step 12
checks it and re-creates it, idempotently, only if it is missing.


## G2 — Tasks 6–9

<!-- G2 draft: Tasks 6, 7, 8, 9 (spec §4.1, §4.2, V1, V2, S1, S1b). Measured read-only 2026-10-02 against main dc801fdb data. -->

**CONTRACT ISSUE 1 — migration 021 moves into Task 6.** Task 6's loader names
`line_item_code` in its `INSERT` and `ON CONFLICT ... SET` lists (contract), and every
jbooks test database is built by `migrate` (`tests/jbooks/conftest.py:24-26`). With the
migration in Task 7, every loader test fails at Task 6's commit (`psycopg.errors.UndefinedColumn`).
Smallest fix: Task 6 creates `migrations/021_budget_lines_line_item_code.sql` (spec §4.1
verbatim) and `tests/jbooks/test_migration_021.py` as its first commit; Task 7 keeps
`export_facts` and `stg_budget_lines`.

**CONTRACT ISSUE 2 — Task 7 touches two more things than the contract lists.**
(a) `tests/test_dbt_build.py:make_lake` writes the fixture lake's `budget_lines.parquet`
without `line_item_code`; once `stg_budget_lines` selects the column, every dbt fixture
build (`tests/test_dbt_build.py`, and the four `test_dbt_*.py` files that import
`make_lake`) fails with `Binder Error: Referenced column "line_item_code" not found`
(reproduced). The fixture gains the column. (b) The `budget_lines` export gains
`order by id`. Measured read-only: the live lake file equals an unordered read of
Postgres row for row (heap order), and heap order is not id order (a sequential scan
returns id 45751 first).
Migration 021 rewrites 26,741 modern P-1/P-1R tuples and S1 rewrites 57,722 era P-1
tuples, so without an `ORDER BY` the lake file would reorder under unchanged data and the
S1 proof would compare two arbitrary orders. `order by id` permutes the file once
(159,494 rows) and never again; Task 8's Z-vs-A export diff proves the site does not
depend on that order.

**CONTRACT ISSUE 3 — how a snapshot is exported is not in the contract.** Tasks 8–9 use
Task 3's tool with the interface its prototype (session scratch `plan/scratch/G1a/part1_proof.py`,
`part2_proof.py`) defines: `govbudget proof snapshot --out DIR --scratch-db NAME` reads `GOVBUDGET_DATA` /
`GOVBUDGET_PG_DSN`, writes `DIR/{duckdb,parquet,site,raw_docs,manifest.jsonl,snapshot.json,env.sh,pg/}`,
repoints the DuckDB views at `DIR/parquet` and the scratch database's
`jbook_documents.file_path` at `DIR/raw_docs`; `source DIR/env.sh RUN_DIR` points
`GOVBUDGET_DATA`/`GOVBUDGET_DUCKDB` at a `cp -c -R` clone and `GOVBUDGET_PG_DSN` at the
scratch database; `govbudget proof diff A B` ends with `proof diff: EQUAL` or
`proof diff: DIFFERENT`. If Task 3 lands a different interface, only the proof steps of
Tasks 8–9 change. (Independent confirmation of why the view repointing matters: the live
`stg_budget_lines` view is `... FROM read_parquet('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/jbooks/budget_lines.parquet')`
— dbt bakes the absolute lake path in at build time.)

**CONTRACT ISSUE 4 — names this group adds.** `p1_loader.CLASSIFIED_CODE = "9999999999"`
(Task 9); proof notes `docs/superpowers/reviews/families-s1-proof.md` (Task 8) and
`docs/superpowers/reviews/families-s1b-proof.md` (Task 9). The S1 script also takes
`--dry-run`, `--dsn` and `--editions` (needed by its tests and the live rehearsal).

**Hazards for later tasks (not fixes).** (1) From Task 9 on, Postgres and the lake hold
409 era-edition P-1 rows with `pe_bli = '9999999999'` (organization `''`). Tasks 10–14
must select era keys with `era_keys.is_era_procurement_key(pe_bli)` (or the
`'^\d{4}[A-Z]-[A-Z]+-L'` pattern), never "every PB2017–23 P-1 row"; `parse_p1_rollup`'s
output for an era workbook now includes those rows too (verify-era-map leg a must filter
them to keep its 6,927). (2) Until the branch merges, a `jbooks export-facts` run from the
main checkout rewrites `data/parquet/jbooks/budget_lines.parquet` without
`line_item_code` (and in heap order); every branch `govbudget build` after that fails on
`stg_budget_lines`. Re-run `jbooks export-facts` from the branch first.

---


## G3 — Tasks 10–12

<!-- G3 draft: Tasks 10, 11, 12 (spec §4.3, §4.6, §5). All code below was run end to end in a
scratch copy of the worktree (95 tests green) and propose was run against a scratch copy of
the live lake carrying the column-I codes S1 will load; every expected number is from that run.
Fixer pass 2026-10-02: CONTRACT ISSUES 4, 9 and 10 below; ratify refuses part-decided chains and a
second organization on one page; propose pre-fills history_only for those chains (re-run on the
scratch lake: only review.csv changed, 3 rows). -->

FIXER NOTES (review issues for G3, both verified against the draft code before fixing):
- Task 12, part-decided chains: confirmed. `propose` builds `open_chains` without every chain that
  has an owner row, so a chain ratified for only some of its editions never returns to review.csv
  and `check` keeps listing it. Fixed in `ratify` (CONTRACT ISSUE 9a), with a new refusal case. The
  Task 11 test that wrote a part-chain owner row by hand now writes a whole-chain row.
- Tasks 11–12, codes spanning organizations: confirmed on the scratch lake. PB2018 prints `10` for
  TJS (`0300D-TJS-L43`, A1, class-ruled SAME, page 10 is TJS's) and DPAA (`0300D-DPAA-L22`, R2,
  pre-filled `same_program`). PB2021–23 print `15` for DISA (A1, SAME) and TJS (R2, pre-filled
  `same_program`). The same defect shows up on a collision code: `500|0300D|DCMA` (R2, PB2017–22)
  was pre-filled `same_program` pinned to `0300D/DLA` because both titles read "Major Equipment".
  DLA's own chain is class-ruled SAME over the same editions, so the pre-fill would have put DCMA's
  $21,056K on page 500-DLA. Fixed in `_prefill` and `ratify` (CONTRACT ISSUE 9b). The collision-code
  case also needs CONTRACT ISSUE 4's history_only pin relaxed (below).
- Spec gaps from the review: none touch Tasks 10–12 code. Two touch their records, which Task 2
  writes: the §7 "Code spanning organizations" row should name the rule in CONTRACT ISSUE 9b, and
  §4.6 `keys.csv` has no cost-type column (see "Minor spec deviation" below). CONTRACT ISSUE 6
  (EXCLUDE is $5,832,017K, not $0) already goes to Task 2 and the Task 15 B1 message.

CONTRACT ISSUE 1 (records carry no amounts for A2). Spec §5.1's A2 rule needs "at least 2/3 of
overlapping-year amount checks within 2×", which compares edition N's FY(N−1) enacted with edition
N+1's FY(N−1) actuals, across the era sum and the PB2024–26 grain. The contract's `EraKey` carries
only `actuals_k` and `ModernLine` carries no amount, so `classify_keys(era, modern, ...)` cannot
evaluate A2. Smallest fix, used below: `EraKey.actuals_k` is `Decimal | None` (an absent
`fct_decade_series` grain is `None`, not 0) plus a trailing field `enacted_k: Decimal | None = None`;
`ModernLine` gains trailing `actuals_k: Decimal | None = None, enacted_k: Decimal | None = None`.
Positional construction with the contract's fields still works.

CONTRACT ISSUE 2 (`ratify` cannot check the lake). The task requires ratify to verify
`keys_sha256` unchanged against the current lake, but the contract signature has no lake path.
Fix: `ratify(*, review_csv, seed_path, batch, decided_on, duckdb_path)`; the CLI passes
`config.DUCKDB_PATH`.

CONTRACT ISSUE 3 (review.csv columns). Three columns are added to the given list: `first_edition`,
`last_edition` (an owner range split duplicates a row and edits the range, spec §5.3) and
`keys_sha256` (the review-time drift guard ratify compares). Order:
`chain_id, first_edition, last_edition, titles_by_edition, modern_title, accounts, continuity,
actuals_k, proposed_decision, reason, program_account, program_org, successor_code, keys_sha256,
decision, note`. ratify reads `chains.csv` beside the review file for the book-stated successor
account and evidence.

CONTRACT ISSUE 4 (collision pinning shape — binding for Tasks 13 and 16). For every chain on one of
the 13 PB2026 collision codes decided `same_program` or `history_only`, the seed sets BOTH
`program_account` and `program_org` to the identity of the PB2026 page (`dim_programs` account +
org: `('1611N','N')` for `3010` in SCN, `('0300D','DTRA')` for `20`-DTRA) or, for `history_only`
with no page, of the PB2024–26 P-1 line (`('0300D','DODEA')`) or of the chain itself (its own
account + organization after `ERA_ORG_TO_MODERN`, e.g. `('0300D','DCMA')` for `500`-DCMA, which no
PB2024–26 line prints; ratify accepts either). G4's `collision_pinned` test already accepts any
set pin on a history_only row, so no Task 13 change is needed. Exclude decisions and every
non-collision code leave both blank. Blank seed cells load as NULL (measured with `dbt seed`).
Task 16 must map the pin to `fct_decade_series`' key shape: account kept only for the 10
account-collision codes, organization kept only for `20`/`30`/`500`. Task 13's `collision_pinned`
test: collision code and decision in (`same_program`,`history_only`) ⇒ both non-null.

CONTRACT ISSUE 5 (chain identity and drift guard in SQL — binding for Task 13). A key belongs to
the seed row with the same `line_item_code` and `account`, edition in `[first_edition,
last_edition]`, and `organization` equal to the key's organization when the seed's is non-null;
the seed's organization is null exactly when the code is not in `ORG_SPLIT_CODES`.
`keys_sha256` = sha256 hex of the UTF-8 join with `'\n'` (no trailing newline) of the sorted lines
`{edition}|{era_key}|{budget_activity}|{filed_title}` (empty string for a null), i.e. in DuckDB
`sha256(string_agg(line, chr(10) order by line))`.

CONTRACT ISSUE 6 (spec record, not a code change). Spec §5.2 lists R-DEC-ERA-EXCLUDE at "$0
selected actuals". Measured: the 45 CR chains carry $0, but the 2 UNSAFE chains (`0390D` `O&M`,
`RDT&E`, 14 keys, Chem Demil) carry $5,832,017K of FY(N−2) actuals. They have no page either way
(route-unsafe), so excluding them changes nothing displayed, but the approval text understated
them. Record it with Task 2's corrections and show it to the owner with the first review batch
(Task 15).

CONTRACT ISSUE 7 (research-pass deltas, all from the spec's own rule). The research pass compared
(code, account) for the org-split codes; §5.1 compares (code, account, organization). Exactly 20
keys move, all on org-split codes, so: A1-only chains 811 (not 813: `20|0300D|DSS` and
`500|0300D|DCMA` become R2), A2-without-R 18 (not 19: `10|0300D|DPAA` becomes R2), R-containing 98
(not 95). Key classes A1 5,477 / A2 64 / R1 152 / R2 133 / R3 64 / H 978 + CR 45 + UNSAFE 14
(research: 5,487 / 65 / 161 / 113 / 64 / 1,037). R-DEC-ERA-SAME covers 810 chains
($651,579,549K), one A1-only collision chain leaves it (`30|0300D|DODEA`, no PB2026 page), and 125
chains go to review. The spec's "20-DSS, 500-DCMA leave the ruling" examples are reviewed as R2
instead, which has the same outcome.

CONTRACT ISSUE 8 (CLI edit anchors). `cmd_era_map` is inserted immediately before
`def cmd_refresh(args) -> None:` and its parser immediately after `ev.set_defaults(func=cmd_evals)`.
Tasks 3, 5 and 14 also add CLI commands and should use other anchors.

CONTRACT ISSUE 9 (two ratify rules; binding for Task 13's dbt guard and Task 15's batches; the
§7 row "Code spanning organizations" should name 9b, recorded by Task 2).
(a) Whole chains only. `ratify` refuses a batch unless every chain it touches is fully decided:
the chain's seed rows plus its batch rows cover every edition in which it holds keys. Error:
`<chain_id>: editions <e1, e2, ...> left undecided — split the whole chain or defer it`. `propose`
re-proposes only chains with no owner row, so a part-decided chain could never return to
review.csv and Task 15 could never reach 0 undecided. Task 15's range splits must therefore cover
the whole chain in one batch, or the chain stays blank (deferred) for a later batch.
(b) One organization per page grain and edition. A same_program row's page grain is
`(code)` for a code that is not a PB2026 collision code, and `(code, program_account, program_org)`
for a collision code (spec §4.5). `ratify` refuses a same_program row of an org-split chain
(seed `organization` set) when a same_program row of ANOTHER organization, already in the seed
(class-ruled or owner) or in the same batch, has the same page grain and both rows cover keys
in a common edition. Error: `<decision_id>: same_program collides with <decision_id> — page
<page> would sum <org> and <org> in PB<e>, ...; decide history_only for the organization whose
page it is not`. Live cases: `10` (page TJS; DPAA in PB2018), `15` (page DISA; TJS in
PB2021–23), and on a collision code `500` (DCMA pre-filled onto page 500-DLA over PB2017–22).
`20|0300D|DSS` → page 20-DCSA is unaffected: no edition has keys from both DSS and DCSA, so it is
an organization rename. Matching dbt guard (Task 13, G4): among `p1_era_line_map` keys whose
decision is `same_program` and whose seed row has a non-null `organization`, fail any
(`edition`, `line_item_code`, `program_account`, `program_org`) group with more than one distinct
`organization` (pins are NULL on non-collision codes, so the group is the bare code there).
Keys of non-org-split codes are out of scope on purpose: they come from codes that span accounts
(R3), which aggregate like modern lines sharing a code (§4.5).
(c) Pre-fill. `propose` pre-fills `history_only` for an org-split chain whose code points at
another organization's page in an edition where that organization also holds keys. The page is
the code's single page for a non-collision code (owned by the organizations that print the code
in PB2024–26; the owner's own chain never matches). For a collision code it is the page the
pre-fill picked by title. Reason:
`<classes>: code also printed by <org> in PB<e>, ...; page <code> is <org>'s` (collision code:
`page <code>-<org> (title match) is <org>'s`). Pins are blank on a non-collision code and the
chain's own identity on a collision code (CONTRACT ISSUE 4).

CONTRACT ISSUE 10 (what the fixes change in the live outputs; for Task 15). Re-running propose on
the scratch lake changes only `data/research/era_map/review.csv` (new sha in Task 11 Step 8). Three
rows change: `10|0300D|DPAA`, `15|0300D|TJS` and `500|0300D|DCMA`, each now pre-filled
`history_only` (see Task 11 Step 9). Review pre-fills are now 108 `same_program`, 12
`history_only` and 5 blank (before: 111 / 9 / 5). `counts.json`, `chains.csv`, `keys.csv` and the
seed are byte-identical, and every count in Tasks 11–12 is unchanged.

Minor spec deviation (Task 2 records it as a dated correction to §4.6): `keys.csv` has no workbook
cost-type column. The lake already sums cost-type rows per key, and `source_cells` lists every
summed cell.


## G4 — Tasks 13, 14, 16

<!-- G4 draft: Tasks 13, 14, 16 (spec §4.4, §4.5, V3, V4 legs a–c). Every code block below was run
     read-only on 2026-10-02: the SQL against an in-memory copy of the live lake (with
     line_item_code taken from the research scan) and inside a scratch copy of the dbt project
     (fixture lake: PASS=242; real-lake selection with a fully decided simulated seed:
     PASS=50 WARN=0); the pytest files against the contract's era_map / parse_p1_rollup shapes.
     Fixer pass (2026-10-02): org_split's second leg (Task 13), map_basis in the program grain
     (Task 16, G4-4), SAM-window guards on both live builds; test_p1_era_line_map_sql.py 40 passed,
     test_program_decade_series_sql.py 21 passed. -->

CONTRACT ISSUE (G4-1, keys_sha256 rendering). The contract gives only the signature of
`era_map.keys_sha256`; `p1_era_line_map` must recompute the same hash in SQL. Smallest fix —
Task 10 implements exactly: render each `(edition, era_key, ba, filed_title)` as
`f"{edition}|{era_key}|{ba or ''}|{filed_title or ''}"`, sort the rendered strings (Python `str`
order, which equals DuckDB's default VARCHAR order — so `…-L10|…` sorts before `…-L1|…`), join
with `"\n"` (no trailing newline), return `hashlib.sha256(text.encode("utf-8")).hexdigest()`.
Each seed row's `keys_sha256` and `n_keys` cover exactly the keys that row binds: printed code +
account (+ organization when set) + edition in `first_edition..last_edition` (a range split
hashes each range separately). Task 13's `test_keys_sha_sql_agrees_with_era_map_keys_sha256`
fails if the two sides disagree.

CONTRACT ISSUE (G4-2, fixture lake columns). `tests/test_dbt_build.py`'s `make_lake` writes
`budget_lines.parquet` without `line_item_code`, `source_sheet`, `source_cells`. Task 7's
`stg_budget_lines` change (selects `line_item_code`) and Task 13's `p1_era_line_map` (reads the
lake's `source_cells`) both break `dbt build` on that fixture, which backs
`tests/test_dbt_build.py` and the four `tests/test_dbt_*.py` files that import `make_lake`.
Smallest fix — Task 13 Step 10 adds an idempotent `ensure_lake_columns` helper to `make_lake`
that appends any of the three that are missing as NULL varchar. Task 7 should keep
`test_dbt_build.py` green on its own (it can call the same helper); Step 10 leaves a column Task 7
already wrote alone.

CONTRACT ISSUE (G4-3, how Tasks 13/16 write the live DuckDB). The global constraints let 13/16
"govbudget build" to add tables. A full `govbudget build` rebuilds every mart from whatever the
shared lake holds at that minute. These tasks run the same `dbt build` (same project, profiles and
env as `cmd_build`, `cli.py:2007-2020`) limited with `--select` to the nodes they add
(`stg_budget_lines` view refresh + seed + `p1_era_line_map`; then `fct_program_decade_series`).
Swap in `uv run --project . python -m govbudget build` if the orchestrator wants the full rebuild;
the expected test lines are the same.

CONTRACT ISSUE (G4-4, the program table's grain). The contract gives `fct_program_decade_series`
the grain `(program_key, account, organization, fy, edition_year)`. That key keeps account and
organization NULL on every non-collision code, so a `history_only` chain and a `same_program`
chain that print the same code in the same edition would sum into one row, and that row is the
page's: history-only dollars on the page. Measured on the research classes (read-only,
2026-10-02): `10` in PB2018 (DPAA beside TJS), `15` in PB2021–PB2023 (TJS Cyber beside DISA), and
codes printed under two accounts in one edition such as `0182` (PB2017–PB2022: MH-60R under 1506N
beside Air Expendable Countermeasures under 1508N), whenever review decides one side
`history_only`. Smallest fix, used below: `map_basis` is part of the grouping key from `detail`
through the slug pick to the lake check, so the grain is `(program_key, account, organization,
fy, edition_year, map_basis)`, and the five-column key stays unique among the `native` and
`era_line_map` rows that pages read (`assert_program_decade_grain_unique.sql` checks both).
`map_basis = 'mixed'` can no longer occur. Task 17 (G5) works unchanged: it joins native rows on
`map_basis = 'native'` and skips `era_history_only` grains (G5 CONTRACT ISSUE 2 asked for this
fix). Task 2 should record dated spec corrections: §4.5's five-column grain becomes "unique per
map_basis, and unique on the five columns among the native and era_line_map rows pages read";
§7 row "Code spanning organizations" should name the rule
`assert_p1_era_map_org_split.sql` enforces: at most one organization per edition is
`same_program` on a code that is not a PB2026 collision code (today `10` and `15`).

CONTRACT NOTES (names this group fixes for later tasks):
- `fct_program_decade_series` columns, in order: `program_key, fy, edition_year,
  amount_type_kind, amount, amount_thousands, scenario, amount_type, account, organization,
  n_source_rows, source_fact_id, map_basis, source_keys`. There is no `pe_bli` column (Task 17
  selects `program_key`). `map_basis ∈ {native, era_line_map, era_history_only}` and is part of
  the grain (G4-4); `source_keys` is the sorted comma-joined era keys (NULL for native).
- Tasks 13 and 16 add 18 and 15 dbt test nodes. /methodology/'s "dbt data-model assertions"
  count and `site_meta.build_checks.dbt_assertions` are derived from `dbt/target/manifest.json`
  at build time and move from 163 (main checkout's manifest, measured 2026-10-02) to 196. No
  pinned number changes. Task 15's swap of the warn test for the error test is net zero. The
  release's site-side change list (spec §10) should name this move.
- `p1_era_line_map.source_cells` = the column-I cells of the key's workbook rows, comma-joined in
  row order (`'I35,I36'`); `source_document_sha256` = the era P-1 workbook sha (Task 19's
  `_DATASET_SCOPES` sentence should say so).
- `warn_p1_era_map_undecided.sql` returns undecided **or stale** (`keys_sha_ok = false`) keys.
  Task 15's `assert_p1_era_map_no_undecided.sql` should keep that predicate at error severity.
- `verify_era_map` reports legs d–f as FAIL ("added by families piece 1 Task 20") until Task 20
  replaces the `else` branch in `run_verify_era_map`. `LEG_NAMES` already names d–f. Task 20
  must update `test_legs_d_to_f_fail_until_task_20` and `test_cli_zero_arguments_runs_every_leg`.
- S3's "exporter unchanged → empty export diff" holds by construction at Task 16: nothing in
  `src/` reads `fct_program_decade_series` until Task 17 (Task 16 Step 11 greps it). Task 21's
  A/B on the post-S3 snapshot is the export proof.
- New shared test helper `tests/dbt_render.py` (`render_dbt_sql(rel_path, sources=None)`); later
  tasks may reuse it.


## G5 — Tasks 17–18

<!-- G5 draft: Tasks 17 and 18 (spec §6.1, §6.2). Every code edit below was applied
to a scratch copy of the worktree at 10fb4585 and its tests were run there; the
Postgres-backed exporter tests were collected but not run (no throwaway cluster
existed while drafting — Task 1 creates it). -->

> **CONTRACT ISSUE 1 — the program table's read contract (Task 16 / G4).** Task 17
> reads exactly these `fct_program_decade_series` columns: `program_key, fy,
> edition_year, amount_type_kind, amount, amount_type, n_source_rows,
> source_fact_id, account, organization, map_basis` (`source_keys` is not read).
> It needs: (a) `map_basis` values spelled exactly `native`, `era_line_map`,
> `era_history_only` (any other value raises); (b) on era rows, `account` /
> `organization` follow `fct_decade_series`' axis convention — the pinned
> `program_account` only for the 10 account-collision codes, the pinned
> `program_org` only for the 3 organization-collision codes `20`/`30`/`500`,
> never both (Task 17 raises if an era grain carries both); (c) a single-source
> era grain's `source_fact_id` is `fact_id_workbook` over the source row's OWN
> `(sha256, 'P-1', edition, account, organization, budget_activity, era_key,
> amount_type)` — not the pinned values (Task 17 compares it and raises on a
> mismatch); (d) `fct_decade_series` stays a base table with its
> `organization` column (Task 17 orders native grains by its `rowid`).
> `p1_era_line_map` (Task 13) is read as `edition` (castable to integer),
> `account, organization, budget_activity, era_key, line_item_code,
> program_key, program_account, program_org, decision`; on every
> `same_program` row `program_key` must equal `line_item_code` (spec §4.5 —
> Task 17 raises otherwise); blank or NULL pins are both accepted.

> **CONTRACT ISSUE 2 — a history-only chain can share a grain with a
> same_program chain (Task 16 / G4; Task 15 / G7).** The grain
> `(program_key, account, organization, fy, edition_year)` keeps
> account/organization NULL on every non-collision code, so a `history_only`
> chain and a `same_program` chain that print the SAME code in the SAME edition
> under different organizations (or accounts) land on one key. Measured in the
> research pass (`scratchpad/era_map/era_map_proposal.csv`, codes 10 and 15 in
> 0300D): PB2018 code `10` has `0300D-DPAA-L22` (class A2, "Major Equipment,
> DPAA") beside `0300D-TJS-L43` (A1, the PB2026 page `10` is TJS); PB2021–23
> code `15` has `0300D-TJS-L50/51/53` (R1, "Major Equipment - TJS Cyber", no
> PB2024–26 line) beside `0300D-DISA-L12/13` (A1, "Joint Forces Headquarters -
> DODIN", the decade-only page `15`). If either TJS-Cyber or DPAA is decided
> `history_only`, a fused grain would carry another organization's dollars;
> Task 17 matches only `same_program` map rows, so its source-count guard then
> raises "mart/lake drift" instead of publishing it. **Smallest fix:** Task 16
> adds `map_basis` to the grain-uniqueness test
> (`assert_program_decade_grain_unique` on `(program_key, account,
> organization, fy, edition_year, map_basis)`) and groups era rows by
> `map_basis`, so history-only rows never sum into an `era_line_map` grain;
> native rows stay unique on the five-column key (parity is unaffected:
> measured, no PB2017–23 printed P-1 code equals any R-1 PE in any edition).
> Tasks 17–18 below work unchanged with that fix (they skip
> `era_history_only` grains).

> **CONTRACT ISSUE 3 — WITHDRAWN (plan review, 2026-10-02).** This draft first
> asked Task 19 to extend `_DATASET_SCOPES["budget_lines_decade"]`
> (`export_site.py:1753-1758`) so that spec §6.1's two meanings of `pe_bli`
> are "documented in the dataset scopes". That is unnecessary: Task 19's new
> `_DATASET_SCOPES["p1_era_line_map"]` sentence already names both ("era_key
> (its pe_bli in budget_lines_decade), line_item_code (the budget line code
> printed on it, the pe_bli its era citations carry)"), and Task 19's
> `test_scope_names_both_meanings_of_pe_bli_and_carries_no_money` pins it.
> The `budget_lines_decade` scope stays byte-identical, so there is no extra
> `/data/` weight and no `datasets.json` description change. Tasks 17–18 do
> not touch `_DATASET_SCOPES`.

**Base and line numbers.** All `file:line` references are at base commit
`10fb4585` (worktree branch `families-2026-10-02`). Task 17 adds 244 lines to
`src/govbudget/export_site.py` (18,464 → 18,708): 238 before base line 10,601
(every Task 18 site from base 10,601 to 17,173 moves down by 238) and 6 at base
17,702. Task 18 cites both its post-Task-17 lines and the base lines. Every
edit is an exact-text replacement whose "old" text occurs exactly once in the
file, so it applies by search even if earlier tasks moved lines.

**Consumer audit (everything that reads `decade_grains`, `decade_series_by_pe`,
`decade_bl_rows` or `decade_side_meta`).** The spec fences three surfaces; these
are all the others, and none needs a new fence:

| Consumer | Reads | Effect of era grains | Action |
|---|---|---|---|
| `_build_summary_blocks` (`export_site.py:8001-8010`) | grains with `d_edition == _SUMMARY_EDITION` (2026, `:7368`) | none — era grains are PB2017–23 | none |
| program sidecars (`:12998-12999`, `:13095-13096`, `:13183`) | `decade_series_by_pe` | era points added — the feature (§10) | none |
| decade-only page filter (`:12752-12757`) | truthiness of `decade_series_by_pe[pe]` | none — measured 553 of 553 candidates already carry a cited native point, so no page appears or disappears | none |
| `_decade_absent_block` (`:7563`, called `:13189`) | the sidecar's own series | `first_edition`, `edition_count`, `fy_min` move earlier on the ~80 decade-only procurement pages (§10); `last_edition`/`renumber` unchanged (era editions precede PB2024) | none (expected) |
| `build_lineage_flow` (`lineage/flow.py:286`, called `:12880`) | only `fy == AMOUNT_FY` (2026, `flow.py:87`) request points | none — era points are FY ≤ 2023 | none (not in the spec's list; verified safe) |
| `_emit_breakdowns` (`:17627`) | `decade_bl_rows`, `decade_side_meta` | new breakdowns for `decade_era_map` sums (§10); era rows must link to the page | Task 17 Edit 17.14 |
| decade-only title / org / exhibit indexes (`:12773-12786`) | `decade_bl_rows` keyed by the row's own `pe_bli` | none — era rows key on era keys, never a decade-only page | none |
| `_rva_gap_rows` / book-diff join (`:14979-15047`, `:7212-7260`) | `fct_decade_series` / native grains only | none — era grains never enter `grain_fid_by_key` (Edit 17.11) | none |
| site: `isZeroContentDetails` (`program-tier.ts:492`), sitemap count (`gates/build.mjs:1051`) | sidecar series values | none — measured 0 zero-content program sidecars of 2,562, so no page becomes indexable | none |
| site: `/programs/`, `/agency/` (`getProgramDecadeCells`, `data.ts:3954`) | `years_matrix.json` | none once /years/ is fenced | Task 18 |
| site: `family-entry.tsx:32,44,64` | `getF15FamilyData().records` | none once `loadRecord` is fenced | Task 18 |
| site: `fact-resolver.ts:171`, program page, sparkline, `program-skeleton` leg k | sidecar series | era points resolve and render — the feature; leg k recomputes `decade_absent` from the same series | none |
| site: `briefing-specs.json`, `gates/basis.mjs` leg h2 | edition-2026 fids / summary cards | none | none |

**Measurements (read-only, 2026-10-02, live data at
`/Users/andeslee/Documents/Cursor-Projects/GovBudget/data`).**
- `json/years_matrix.json` is 3,178,320 B (cap 4,194,304), sha256
  `3c766600c633ea3c9bd2890862ef8f591e652b1d5e2dd0d4e227053840f2213c`
  (`ls -la` + `shasum -a 256`).
- Lineage: 50 families carry 604 `funding_line` entries across
  `json/program_details/*.json` (python: collect `lineage.family.funding_line` per
  `family_id`). Exactly one lineage family member is a PB2026 P-1 code that is
  printed in a PB2017–23 P-1 column I: `837170` (lake
  `program_family.parquet` ∩ PB2026 P-1 `pe_bli` ∩ era column-I codes from the
  research `rows.pkl`). That is the funding line the lineage fence protects.
- PB2017–23 printed P-1 codes equal to any R-1 `pe_bli` in any edition: 0
  (same sources). An era grain therefore never shares a key with a native R-1
  grain.
- `decade_only_page_pes`: 553 pages from 3,771 candidates; all 553 have a
  `tier: "decade"` sidecar today.
- Zero-content program sidecars (`isZeroContentDetails` re-implemented in
  python over `json/program_details/*.json`): 0 of 2,562.
- Order: on the live warehouse,
  `select … from fct_decade_series` (the base read) returns the same 59,179
  rows in the same order as a program table shuffled with `order by random()`
  and re-read through Task 17's `rowid` join (exact-equality check, 5.8 s).
- Base decade tier on the live warehouse with scope = PB2026 lake `pe_bli` ∪
  decade-only pages (2,546): 38,762 `budget_lines_decade` rows, 57,566 citation
  rows (395 derived decade sums, 18,409 book-diff facts), 38,354 grains, 0 era
  keys. Task 17's switched tier, run on a scratch warehouse whose program table
  is the native part of `fct_decade_series` in random order, reproduced all four
  outputs exactly (`native identical: True`).


## G6 — Tasks 19–20

## G6 contract notes (Tasks 19–20)

Live weights below were measured read-only on 2026-10-02 with gate 1's own `weigh()` (zlib level 9) on the live pages
(`curl -s -H 'Accept-Encoding: identity' https://fiscalreceipts.com/<page>/`): `/data/` 101,696 / 15,558 against
105,000 / 15,600 (42 gzip bytes left); `/coverage/` 86,203 / 20,458 against 103,000 / 20,750 (292 left);
`/methodology/` 161,166 / 45,270 against 162,000 / 45,400 (130 left); `/downloads/` 101,020 / 16,358 (no entry in
`PAGE_WEIGHT_BUDGET`). Build measurements come from production-origin builds
(`NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com`, the origin Task 5's stamps were measured at) of a scratch copy of
this worktree's `site/` against 2026-10-02's `data/site` (scratch: `scratchpad/plan/scratch/G6/fix/`). The baseline
build reproduced production's raw bytes exactly (`/data/` 101,696, `/methodology/` 161,166; gzip within 3 bytes, the
per-build ID).

**OWNER DECISION — MADE 2026-10-02 at plan review (all three points approved as proposed below; Task 19 Steps 19–20
record it) — where the per-edition era table renders, and that it shows counts only.** Spec §6.4 says: render it on `/coverage/` if it fits, otherwise on the `/data/` map card; §4.4 and
§6.4 say "chains and dollars by decision". Measured with the table component as Part C builds it (7 editions, counts
only, HTML + its RSC copy; +28,550 raw on any page): `/coverage/` 86,203 / 20,460 → 114,753 / 22,853 (+2,393 gzip
against 292 left; raw over 103,000 too); `/data/`, after Part A's hoist and before the dataset's own inventory row,
81,748 / 13,517 → 110,298 / 17,164 (+3,647 gzip against 2,083 left; raw over 105,000 too). An earlier stripped-down
simulation (one module class, no mobile labels) still needed +1,331 on `/coverage/` and +1,797 on `/data/`. Neither
page takes it without a raised ceiling or trimmed disclosure, which the plan may not do without the owner. Dollars
cannot render either: every rendered `$` token must sit in a `[data-amount]` with a Cite state (gate 2 render-static
(a)/(b)/(c)); these per-decision sums have no citation (history-only and excluded lines are never minted), and a
state-C span would have to name an uncited-ledger dataset holding the figure (`p1_era_line_map` holds no amounts).
**Proposal:** render the table on `/downloads/`, directly under the `p1_era_line_map` download card (no ceiling, no new
route, sitemap unchanged; +2,354 gzip there, 101,020 / 16,358 → 129,570 / 18,712), counts only (lines, codes per
decision, PDF-receipt completeness), with the dollars machine-readable in `json/era_map_summary.json`. A third point
rides with it (the reviewer's §4.4 observation): `p1_era_line_map` on the uncited ledger gives `/data/` its first
"tier pending" badge (all 16 datasets are "cited" today) and makes the `/methodology/` clause "every published dataset
carries a citation tier (the pending ledger is empty)" false; the proposal keeps the badge and rewrites that clause at
equal length (measured: same raw bytes, 60 gzip left), a second `/methodology/` change beyond spec §6.2's one. Task 19
Step 19 sends the owner these numbers and waits for an explicit yes; Step 20 then adds dated correction notes to spec
§6.4 and §10 and records the decision in the ROADMAP "Platform families" paragraph. If the owner declines, Part C
stops (Step 19 says how). Datatruth leg (s) reads `/downloads/`.

**CONTRACT ISSUE 2 — registering the dataset on `/data/` does not fit either, without a no-disclosure-change hoist.**
`p1_era_line_map` gets an inventory row and an Explorer option automatically (datasets.json drives `/data/`). One row
costs +223 gzip (empty scope) to +529 (259-char scope) against 42 left. **Smallest fix (in Task 19 Part A):** move the
inventory rows' repeated utility strings into `src/app/data/data.module.css`, the move `coverage.module.css` made for
`/coverage/` (−904 gzip there). Proved on production-origin builds of a scratch copy (2026-10-02, Steps 3 and 10 below,
verbatim): **0 computed-style differences** over 1,362 elements in 9 states (390/1440, light/dark, screen/print, row
hover); `/data/` 101,696 / 15,555 → 81,748 / 13,517 (−19,948 raw / −2,038 gzip); an earlier run of the same check with
one declaration removed from the CSS reported 258 differences. This hoist is needed whatever the owner decides about
the era table: it pays for the dataset's row.

**CONTRACT ISSUE 3 — withdrawn into the owner decision above** (the table renders counts; the dollars stay in
`json/era_map_summary.json`). Rendering them later needs derived citations over cited inputs.

**CONTRACT ISSUE 4 — the summary is written after the receipts step.** Receipt completeness comes from
`json/budget_pdf_receipts_audit.json`, which `cli._export_budget_pdf_evidence` writes after `export_site()` returns.
So `json/era_map_summary.json` is written by a new public `write_era_map_summary(*, site_dir: Path, duckdb_path:
Path) -> dict | None` (in `export_site.py`), called from `cli._export_budget_pdf_evidence` (both `export-site` and
`export-budget-pdf-receipts`). Fixture exports through the low-level `export_site()` write no summary.

**CONTRACT ISSUE 5 — withdrawn.** Task 14's `verify_era_map.py` (G4) is canonical: legs are the public
`leg_a_workbooks` / `leg_b_decisions` / `leg_c_f15`, each returning `_leg(ok, summary, failures)`, and
`run_verify_era_map` dispatches with `if`/`elif` and an `else` that FAILs d–f. Task 20 writes `leg_d_fact_ids`,
`leg_e_published_map` and `leg_f_history_pin` in that shape and replaces the `else` branch.

**CONTRACT ISSUE 6 — site builds in the worktree need `data/site`.** `site/src/lib/data.ts:38` and
`site/scripts/prepare-assets.mjs:18` read `GovBudget/data/site` relative to the site (no env override). Task 1 must
create `GovBudget/data/site -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site` in the worktree (read-only
use; the build scripts write only under `site/`, checked in `prepare-assets.mjs`, `generate-og.mjs`,
`generate-feeds.mjs`, `write-build-meta.mjs`), `site/node_modules` must be a real directory (`npm ci`, or
`cp -cR` from the main checkout), never a symlink, and `dbt/target/manifest.json` must be this worktree's own (Tasks
13/16 write it with `govbudget build`). After Task 19 Part C, the site builds only against an export that ships `p1_era_line_map`
(`data/page.tsx:36-54` throws when `DATASET_NAMES` names an unshipped parquet), so Task 21's S4 snapshot is the first
build of Part C. **Handoff to Task 21:** run `npm run verify` on that build (gate 24 legs a–c, s; gate 1 page weight);
re-measure the `/data/` `measured` stamp there (expected ≈ Part A's stamp + 400 to 650 gzip for the new row); the S4
diff's site side has the era table on `/downloads/`, not `/coverage/` (the owner decision of Task 19 Step 19).

**Interfaces assumed from other groups.** G4/Task 13: `p1_era_line_map` (DuckDB `main`) has the spec §4.4 columns,
including `edition` (integer), `account`, `organization`, `budget_activity`, `era_key`, `line_item_code`,
`filed_title`, `program_key`, `decision` (`'undecided'` when no seed row covers the key), `decision_id`, `ruling`;
`fct_program_decade_series` has `map_basis`. G3/Task 10: `govbudget.jbooks.era_map.DECISIONS`. G1b/Task 4:
`tests/fixtures/f15/history.sha256` starts with the 64-hex sha256 of `data/site/json/f15_funding_history.json`
(`shasum -a 256` output satisfies this). G4/Task 14: `src/govbudget/verify_era_map.py` exactly as G4 drafts it
(`from collections import defaultdict`, `_leg`, `_sha256_file`, `LEG_NAMES`, `format_report`, and the `else:` branch
of `run_verify_era_map` that Task 20 replaces) and `tests/test_verify_era_map.py` with
`test_legs_d_to_f_fail_until_task_20` and `test_cli_zero_arguments_runs_every_leg`. G5/Task 17: a fixture warehouse that gives `fct_program_decade_series` rows
with `map_basis <> 'native'` must also create `p1_era_line_map` (the exporter raises otherwise, by design).

---


## G7 — Tasks 15, 21–23

<!-- G7 draft: Tasks 15, 21, 22, 23. Drafted 2026-10-02 against worktree 10fb4585 (= main dc801fdb + the spec commits); revised the same day against the G1a/G1b/G3/G4/G6 drafts (fixer pass). -->

CONTRACT ISSUE 1 — WITHDRAWN (review.csv shape). G3's schema wins: Task 15 reads and writes exactly
`era_map.REVIEW_COLUMNS` (`chain_id, first_edition, last_edition, titles_by_edition, modern_title, accounts,
continuity, actuals_k, proposed_decision, reason, program_account, program_org, successor_code, keys_sha256,
decision, note`, G3 CONTRACT ISSUE 3), keyed by `chain_id`, and reads `n_keys`, `classes`, `successor_account`,
`successor_evidence` from `chains.csv` beside it. Its end-to-end test runs Task 12's `ratify` on what it writes.

CONTRACT ISSUE 2 — WITHDRAWN (keys.csv columns). A range split duplicates the chain's review row, changes only
`first_edition`/`last_edition` and keeps the chain's `keys_sha256`; ratify compares that with the whole chain
and hashes each range from the lake itself. Task 15 no longer reads keys.csv.

CONTRACT ISSUE 3 — REPLACED (ratify semantics, as G3 Task 12 builds them). `govbudget era-map ratify --batch
B<n> --decided-on DATE` (both required; `config.DUCKDB_PATH`, so `source scripts/era/env.sh` first) writes
every decided review.csv row as `ruling = R-DEC-ERA-B<n>`, `decided_by = owner`, and refuses (writes nothing)
on any row that overlaps an existing seed row. So after each batch Task 15 runs `govbudget era-map propose`,
which rewrites review.csv with only the chains no seed row covers (deferred chains come back blank) and
keeps the owner rows verbatim.

CONTRACT ISSUE 4 — WITHDRAWN (proof tool I/O). Tasks 21–22 use Task 3's layout and run convention: the
snapshot directory itself is the `GOVBUDGET_DATA` root (`<snap>/{duckdb,parquet,site,raw_docs,manifest.jsonl,
pg/,snapshot.json,env.sh}`, views and `jbook_documents.file_path` repointed by Task 3), each export runs in
its own `cp -c -R <snap> <run>` clone under `source <snap>/env.sh <run>`, and both `--expect` files are
Task 3's JSON list of rules. No snapshot is rebuilt (V3 runs `dbt test` on the pinned state).

CONTRACT ISSUE 5 — WITHDRAWN (F-15 fixture capture). Task 22 uses Task 4's CLIs as built:
`scripts/era/capture_f15_fixtures.py --site-dir DIR --duckdb PATH --out-dir DIR --expect-sha256 HEX` and
`site/scripts/f15-page-snapshot.mjs <index.html> [--out FILE | --check FILE]`, and Task 4's pin format
(`history.sha256` = 64 lowercase hex + LF). Cross-group note: G1b's `tests/fixtures/f15/README.md` re-pin
recipe still names `.proofs/s5/data/{site,duckdb,parquet}`; under Task 3's layout it is
`.proofs/s5/{site,duckdb,parquet}`, as Task 22 uses.

CONTRACT ISSUE 6 (A-side commit — Task 17/G5 ↔ Task 21). Verified against the drafts: only Tasks 17, 18 and
19 commit `src/govbudget/export_site.py`, Task 17's subject starts `feat(export): decade tier reads
fct_program_decade_series`, and no task 17–20 commits `dbt/`. Task 21 still checks both at run time.

CONTRACT ISSUE 7 (link-coverage exit code). Verified: Task 5's CLI exits 1 on any baseline violation
(last line `link-coverage: FAIL`), 0 otherwise.

CONTRACT ISSUE 8 (site data dirs in the worktree). The site build and gates read the repo-relative
`data/site`, `data/duckdb/govbudget.duckdb` and `dbt/target/manifest.json` (site/src/lib/data.ts:35-38 and
:649-671; site/scripts/gates/*-recompute.py). Tasks 21–23 point `GovBudget/data/{site,duckdb,parquet,raw,raw_docs}`
at the right lake with symlinks (excluded by the shared `.git/info/exclude`, lines 23–27) and rely on
`dbt/target/manifest.json` written by this worktree's own dbt runs (Task 1 Step 7's `dbt parse`, Tasks
13/15/16 builds, Task 21 Step 11 and Task 23 Step 1 `dbt test`).

CONTRACT ISSUE 9 (write list and the SAM window). Task 15 closes S2 with a selective live rebuild
(`dbt build --select p1_era_code_decisions p1_era_line_map`), so the global constraint's write list should
read "Tasks 8, 9 (S1/S1b DB writes), 13/15/16 (selective `dbt build` of the nodes they add or change; never a
full `govbudget build`), 21 (snapshot clones only) and 23 (release export; Step 1's recovery
`jbooks export-facts` + selective `dbt build` only if the lake lost the branch's state)". The ":15–:20" rule
covers every live-lake read or write that a SAM write could disturb, dbt builds included (Tasks 15 and 23
guard :12–:22 for margin); exports into pinned snapshot clones are exempt. Scratch `govbudget_proof_*`
databases on the shared server (created by `proof snapshot`) are allowed.

---
