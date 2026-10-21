# Families Piece 2: the family registry, with the F-15 as entry #1 and the F-35 as entry #2 (design)

**Date:** 2026-10-20
**Status:** APPROVED by the owner 2026-10-21: "approved, would process with recommendation to approve all" (approves the three Pending owner decisions below; R-DEC-FAM-F15-SEED owner_reply = that quote, decided_on 2026-10-21). Was: Draft for owner approval. Revised 2026-10-20 with the controller's answers to the
builder-check review (§7.6, §8.2, §8.3, §9.1 rule 23), with the knock-on edits in §14, §15
and Appendix A. Exactly what approving this spec
decides is listed under **Pending owner decisions** below. The F-35 entry needs its own
owner answer, batch `R-DEC-FAM-F35-B1` (§8.2).
**Parent:** [2026-10-02-platform-families-overview.md](2026-10-02-platform-families-overview.md),
§3 piece 2, §6 and §8. The owner decisions are R-DEC-FAM-UNIT, -NAME, -REVIEW and -ERAONLY.
**Builds on:** piece 1, [2026-10-02-era-procurement-history-design.md](2026-10-02-era-procurement-history-design.md)
(deployed 916ae88e), and its follow-ups,
[2026-10-04-families-piece1-followups-design.md](2026-10-04-families-piece1-followups-design.md)
(release 1 deployed e362c0a7; release 2 deployed 1256ec35).
**Base:** main `88538c6a`, the live code. Worktree `families`, branch `piece2-2026-10-20`.
**Evidence base:** read-only. No code, lake, Postgres or export was written for this spec.
- Two design maps, both at `88538c6a`: `.superpowers/sdd/families-piece2/design/map-f15.md` and `map-prior-art.md`.
- The F-35 research the owner reviewed: `research/f35-recommendation.md` and `f35-supply-chain-recommendation.md`.
- The owner decisions file, `owner-decisions.md`.
- My own reading of `src/govbudget/f15_funding_history.py`, `program_pdf_receipts.py`, `verify_era_map.py`, `export_site.py:3860-3895`, `cli.py:2500-2580`, the F-15 tests, `site/scripts/prepare-assets.mjs`, `site/scripts/gates/build.mjs:288`, the era seed and the ROADMAP. All read at `88538c6a`.

Line numbers are hints; anchor on the quoted text.

**Summary for the owner (plain language)**

- Today the F-15 page adds up every F-15 budget line into one total, and every number links back to the budget page it came from.
- The list of which lines count as "F-15" is typed into the program by hand. Doing the next aircraft the same way would mean a second hand-built copy, which is how the earlier attempt went wrong.
- Piece 2 replaces that with one shared list and one shared calculator. For each aircraft family, the list says which budget lines belong to it, for which budget years, why, and when you approved them.
- The F-15 moves onto the new list first. Its page must come out exactly the same, character for character. We prove it by running the old and the new version on the same frozen copy of the data and comparing the two results.
- **What readers see: nothing.** No new page and no changed number.
- The F-35 goes on the list as a draft: the 15 lines you approved on 2026-10-19, the shared lines that are shown but never added in, and the costs the total leaves out.
- You get one review page for the F-35. Next to the lines, it shows what the F-35 totals come to with those lines, year by year and for FY2015–24, so you approve with the result in front of you. If those totals reveal a wrong line, the page is fixed before it reaches you.
- Your yes marks the F-35 as approved but still not public. The F-35 page itself comes in piece 4. If you put the review off, nothing about the F-35 is saved as approved, and piece 2 still ships.
- Approving this spec decides three things, listed next.

**Pending owner decisions.** Approving this spec approves exactly these three things. Each
one stays pending owner approval until the approval message arrives.
*(2026-10-21: all three approved by the owner with the spec — see Status.)*
1. **The F-15 seed ruling, `R-DEC-FAM-F15-SEED` (§8.1).** The F-15's entry in the new list records its eight budget lines exactly as they ship today, and changes nothing readers see. Your approval message is recorded word for word as the ruling's `owner_reply`, dated the day you send it.
2. **The F-15 program tags (§7.6): F-15, F-15EX and EPAWSS.** They are labels inside the one F-15 family, following your own R-DEC-FAM-UNIT example. Nothing shows them in piece 2.
3. **Moving ROADMAP #209 to piece 4 (§3).** #209 makes the family list the single source of program aliases (your follow-ups Q23 choice). Doing it now would change the search results readers see.

Approving the spec also accepts the design calls listed in §19, unless your reply overrules
one. It does **not** decide:
- the F-35 batch `R-DEC-FAM-F35-B1`, which gets its own answer on its review page (§8.2);
- the deploy go-ahead (§15 step 6).

**Citation tags used below**

| Tag | Source |
|---|---|
| [OV] | the overview spec |
| [P1] | the piece-1 spec |
| [FU] | the follow-ups spec, plus its plan README `docs/superpowers/plans/2026-10-04-families-piece1-followups/README.md` |
| [MAP-F15] | `design/map-f15.md` |
| [MAP-ART] | `design/map-prior-art.md` |
| [F35] | `research/f35-recommendation.md` |
| [F35-SUP] | `research/f35-supply-chain-recommendation.md` |
| [OD] | `owner-decisions.md` |
| [CODE] | my own reading at `88538c6a` |

The `research/`, `design/` and `owner-decisions.md` paths are under `.superpowers/sdd/families-piece2/`
in the worktree root.

**Labels.** Every choice in this spec is one of three kinds, and each is labelled:
- **Owner:** the owner decided it. The decision is cited.
- **Design call:** my call, open to the owner. §19 lists every design call in one place.
- **Design call (controller, 2026-10-20):** settled by the controller on 2026-10-20, in answer to the builder-check review. It is open to the owner like any design call (§19 rows 25–27).

---

## 0. In one page (plain language)

The F-15 page groups every F-15 budget line into one family and cites every number. The
owner wants the same for every other weapon system [OV, owner quote]. The first new
family will be the F-35 (piece 4). That page must answer:
- what the F-35 costs, and whether the cost is growing;
- who gets paid, subcontractors included;
- how many jets are bought, and how much each costs;
- whether the program is on track;
- what the family total leaves out.

Piece 2 builds the ground those pages stand on. It does three things:
1. **A family list.** The list is a set of files that names, for each family, every budget line it counts, with dates, a reason and the owner's approval.
2. **One machine.** One machine turns that list into the cited funding history, inside the same exporter and the same citation checks every other figure goes through.
3. **The F-15 on the new machine.** The F-15 is rebuilt on the list and the machine, and must come out identical to the byte.

The F-35 goes into the list as entry #2, first as a draft. It has the 15 budget lines the
owner approved on 2026-10-19, the shared lines that are shown but never added in, and the
things the total leaves out. The owner ratifies it as one batch, on a page that also shows
what the F-35 totals come to with those lines. It is **not published**: no reader sees
the F-35 until piece 4.

**What readers see after piece 2: nothing new.** The F-15 page, its numbers and its
citation IDs do not change. The proof is the method piece 1 used: a frozen copy of the
data is exported by the old code and by the new code, and the two exports are compared.

---

## 1. Intent and why

### 1.1 The owner's words

- **Direction, 2026-10-02** [OV status line]: "the F-15 family is great because it combines all the F-15 related programs together, I would like to do this for the rest of the programs grouping them into families … Ideally all programs are linked to the actual excel or PDF in the budget or receipt where available."
- **F-35 members and cut, 2026-10-19** [OD]: "yes this is good, except we should break out the sub contractors because it doesn't end with lockheed and pratt & W". This approved:
  - the variant cut: A/B/C, each with its modifications, plus development as one column labelled by the paying service;
  - the 15 counted lines;
  - subcontractors as their own layer.
- **Evidence rule, 2026-10-19** [OD]: "only govt reported or trusted source verified".
- **Partner governments, 2026-10-20** [OD]: "yes it counts". Partner governments' official published figures count as government-reported. They are shown verbatim, labelled, and never added.

### 1.2 Why piece 2 exists

The overview lists piece 2's scope [OV §3, piece 2 row]: "`platform_families.json` + members CSV; one loader that fails loudly; one
generic history builder inside `export_site`; registry-driven receipt formulas and
audits; `json/families/index.json`; F-15 rebuilt on it". Its pass/fail is "golden pin; fresh A/B export against a pinned lake
snapshot; 17 existing F-15 tests unchanged". Readers see "Nothing (F-15 output
byte-identical)".

Today the F-15 is the only family, and it is hand-coded.
- **Python.** Its members, era roster, titles, notes and coverage rules are constants in `src/govbudget/f15_funding_history.py` [MAP-F15 §1.1].
- **The site.** The six modern codes are listed eight separate times across Python and TypeScript [MAP-F15 §3].

A second hand-coded family would mean a second builder. That is exactly what made the other
session's attempt fail [MAP-ART §1.2]. Piece 2 replaces the constants with one reviewed
list and one builder, before anything new is published. The internal names and fact-ID
spellings are fixed now, because changing them later would change published fact IDs [OV §8.2].

### 1.3 What the later pieces need from piece 2

The F-35 research lists the per-member and per-family fields that pieces 4, 7 and 8, and
the MSAR/GAO ingestion, attach to [F35 §4]. Piece 2 freezes the full column set now, so
those pieces attach data without changing the list's shape (§7). The supply-chain research
adds evidence tiers and a partner-government tier (§7.5) [F35-SUP §0, §3; OD 2026-10-20].

---

## 2. Goals

1. **One family list** in `data-seeds/`:
   - `platform_families.json`, with family-level fields, rulings and sources;
   - `platform_family_members.csv`, with one row per member identity × edition range × role;
   - `platform_family_era_lines.csv`, the pinned era roster.

   Every field and its consumer are in §7.
2. **One loader** that validates the files in three stages. It collects every error and then raises once (§9).
3. **One generic history builder**, `src/govbudget/platform_family_history.py`. It is called only from `export_site.export_site()`, at the spot where the F-15 builder is called today (§10).
   - `src/govbudget/f15_funding_history.py` becomes a facade. It keeps every name that tests and tools import today, and derives each one from the list.
4. **Registry-driven receipt formulas and audits** (§11):
   - the formula text and the PDF-receipt grammar come from each published family's `short_name`;
   - the receipt audit loops over published families;
   - the verify legs read the list.
5. **`json/families/index.json`** is written into the export. It holds pointers only, no amounts, and lists published families only (§12).
6. **F-15 rebuilt on the list**, byte-identical (§14):
   - `json/f15_funding_history.json` still hashes to the pin `d0de9e8b…8d8f` [MAP-F15 header];
   - every F-15 fact ID is unchanged;
   - the page's normalized snapshot is unchanged.
7. **F-35 recorded as entry #2**: 15 counted members, 3 context rows, 1 deferred project slice, the era roster and the family-level exclusions.
   - `propose` writes it as a `draft` family object, with its rows under review in `review.csv` (§8.3).
   - The owner ratifies it as batch `R-DEC-FAM-F35-B1`, on a batch page that shows its preview figures (§8.2). It then has status `ratified`. It is never exported (§7.7).
8. **New gates:**
   - a `verify-families` CLI in the release assembly;
   - a `platform-families check` command;
   - loader tests;
   - a Python↔TypeScript mirror test;
   - one site gate leg (§13).

**Success criteria**

- **F-15 pin.** `tests/fixtures/f15/history.sha256` still matches a fresh export.
- **Tests.**
  - The V5 tests in `tests/test_f15_era_identity.py` (golden, fresh state, sensitivity) pass unchanged.
  - All 21 test functions in `tests/test_f15_funding_history.py` pass unchanged. These are the overview's 17 plus the 4 that piece 1 added [MAP-F15 §2].
  - The 5 tests in `tests/test_capture_f15_fixtures.py` pass unchanged.
  - Each of these files and `tests/fixtures/f15/` are byte-unchanged on the branch.
- **A/B diff.** The fresh A/B export on one pinned snapshot differs only as §16 lists:
  - `json/families/index.json` is added;
  - `manifest.json` `json_sidecars` rises by 1.
- **Fact stability.** `fact_stability.py` reports zero moved facts.
- **Page.** `site/scripts/f15-page-snapshot.mjs --check` passes against `tests/fixtures/f15/page_snapshot.json`, and the `/families/f-15/` page weight is unchanged.
- **Gates.** `verify-era-map` legs a–h pass with unchanged verdicts, and `verify-families` passes.
- **No leak.** No unpublished family appears anywhere in `data/site`.

---

## 3. Non-goals

- **No new visible page and no visible change.** The `/families/[family]/` route waits for piece 4 [OV §8.5]. The empty `site/src/app/families/[family]/` directory stays empty.
- **No contracts, quantities, MSAR or GAO ingestion.**
  - Contracts are piece 7.
  - Quantities and unit cost are piece 8.
  - Official estimates and "on track" are the MSAR/GAO ingestion, which comes later.

  Their fields are reserved and vocabulary-checked, never populated from new ingestion (§7.3).
- **No evidence engine.** Piece 3 extracts MDAP codes, Code B PEs, Other Program Funding tables and P-18 allocations. Piece 2's `propose` takes two prefilled inputs, a family JSON object and a rows CSV (§8.3).
- **No change to the F-15 page, its TypeScript, its editorial layer or its fact IDs.**
  - The site keeps reading `json/f15_funding_history.json` with `family_id === "f-15"`.
  - The eight TypeScript copies of the six modern codes stay as they are. A mirror test (§13) ties them to the list, and piece 4 or piece 5 points them at it.
- **No dbt seed, no dbt model, no Postgres migration, no lake write.** The files live in `data-seeds/`, so the pinned snapshot never changes (§7.1).
- **No change to the `p1_era_line_map` dataset scope sentence** "… or an F-15 family-history line" (`export_site.py:1766-1797`; its test is `tests/test_export_era_line_map.py:100-140`) [MAP-F15 §1.2]. Piece 4 generalizes it when a second family publishes.
- **ROADMAP #209 (aliases) is re-deferred to piece 4.**
  - **Design call; pending owner approval** (Pending owner decisions, item 3). The owner chose, in follow-ups Q23 (2026-10-04), to make the families registry the single source of program aliases [FU §2.2 Q23; ROADMAP #209].
  - Making it the source now would change `search_quick.json` and the search chips, which readers see. That breaks piece 2's "readers see nothing".
  - Piece 2 reserves the `aliases` family field (§7.2) and leaves #209 open, with a dated Status line.
- **No PB2027.** It must land between pieces, never during one that pins the F-15 [OV §8.6].

---

## 4. Anti-goals (things piece 2 must never do)

1. **Anything that changes the F-15 page or its fact IDs.** That includes:
   - the 31 `family_history` IDs keyed `f-15|…`;
   - the 27 own `family_program_history` cell IDs keyed `{program_id}|…`;
   - the 11 reused `decade` cell receipts;
   - the dataset token `f15_funding_history`;
   - the formula strings;
   - member order;
   - the page payload, which has 672 gzip bytes of headroom (`build.mjs:288`, measured 705,056 / 69,328 against 725,000 / 70,000). The ROADMAP quotes 658 bytes from an earlier measurement; either way piece 2 adds zero [MAP-F15 §4.2; CODE].
2. **A second builder, or any family figure that skips `export_site`'s registry and audits.** The other session wrote:
   - a JS builder in the site layer;
   - its own citation registry and 256 shards, with non-`fact_id_derived` IDs;
   - a gate that compared its builder only with itself [MAP-ART §1.2 #2, #3].

   In piece 2, every family figure is minted with `export_site.fact_id_derived`, written to the one `citations.parquet`, `citations.json` and cite-shard set, and passed through `program_pdf_receipts` and link coverage.
3. **Members without evidence or without the owner's approval.** Two things the other session did:
   - It counted 10 F-35 lines and missed the 5 finished R&D lines ($5,751.6M FY2015–24), which produces the false jump from $39.3M to $2.27B [F35 §1.5; MAP-ART §1.2 #4].
   - Its "evidence" was each member's own page narrative.

   In piece 2, a counted row needs an independent government signal (§7.5) and an owner ruling.
4. **The other session's other mistakes** [MAP-ART §1.2]. Each one, with the rule here that prevents it:

   | # | The mistake | The rule here |
   |---|---|---|
   | 1 | Stripped F-15 sections | The F-15 output is byte-identical and the page snapshot is checked |
   | 5 | Development assigned to variants | `variant_scope=shared` plus `paying_org`, per the owner's cut [OD] |
   | 6 | Uncited specs and unarchived web sources | No editorial specs in piece 2. Every `src:` carries a tier, and a published family's sources must be archived |
   | 7 | Members silently dropped by a "majority measure" rule | An incompatible measure raises |
   | 8 | A cumulative that resets on any gap | The F-15's contiguous-or-raise rule stays |
   | 9 | Members keyed by page slug alone | Identity is exhibit + account + organization + code |
   | 10 | No dates | Every row has an edition range |
   | 11 | Build-order coupling to site files | The builder reads lake inputs inside the export |

---

## 5. Constraints

### 5.1 Owner decisions that bind piece 2

| Decision | What it means here |
|---|---|
| **R-DEC-FAM-UNIT** (2026-10-02): one family per platform; each member tagged with its acquisition program [OV §1] | `program_tag` per member; per-program subtotals become possible without splitting a family |
| **R-DEC-FAM-NAME** (2026-10-02): reader name "family", route `/families/<id>/`; internal identifiers `platform_family` [OV §1] | The route is derived from the id, not stored. The new code names are in §6 |
| **R-DEC-FAM-REVIEW** (2026-10-02): Claude pre-fills, the owner approves, in batches sorted by dollars; nothing publishes without the owner's yes; class rulings are listed in the spec that uses them [OV §1] | Every approved row carries `decided_by=owner` and a ruling. The F-15's class ruling is in §8.1. The F-35 batch page is sorted by FY2015–24 dollars (§8.2) |
| **R-DEC-FAM-ERAONLY** (2026-10-02): discontinued procurement lines stay data only; families may count them as predecessors [OV §1] | F0150P and F015E0 stay counted F-15 members with no page |
| **R-DEC-ERA-SAME / -HISTORY** and batches B1–B7 [P1 §5.2; FU §2] | `era:` evidence and `era_decision_ids` resolve against `dbt/seeds/p1_era_code_decisions.csv`. No new era rulings are needed for the F-15 or the F-35, because all their chains are decided [MAP-ART §2.1; F35 §5 Q1] |
| **Publish the smaller true number** (2026-08-07) | An exclusion carries only a cited size. The F-35 spares exclusion records $766.3M for FY2024 [F35 §1.2, V-CON M1], not the inferred ~$6.3B, which still needs a direct MSAR read [F35 §1.2] |
| **Every figure traces to a citation** | The index carries no amounts. Exclusion sizes are stored as cited text and never published in piece 2 |
| **F-35 cut and 15 members** (2026-10-19) [OD] | The F-35 entry's member set, purpose tags and `paying_org` follow [F35 §1.1, §2.1] |
| **Subcontractors broken out** (2026-10-19) [OD] | A piece-7 constraint. Piece 2 reserves `contract_routes` and blocks nothing; supplier rows belong to piece 7's own seed (§7.2, design call) |
| **Evidence rule** (2026-10-19) and **partner governments count** (2026-10-20) [OD] | The source tier vocabulary is `G` / `PG` / `C` / `X`, enforced by the loader (§7.5) |

### 5.2 Proof and data-safety constraints (inherited from piece 1)

- **Byte identity is proven on a pinned snapshot, never on the live lake.** The A export runs the pre-piece code and the B export runs the piece-2 code, both against one snapshot, diffed with build timestamps masked. A control B2 measures noise [P1 §8; FU §7]. An idempotent re-run on a copy of `data/site` is not proof [P1 §8].
- **The SAM window.** The hourly SAM job writes `data/parquet/sam` at :17 [FU README, Global Constraints].
  - Start no step that reads or writes the live lake during :15–:20. Guarded blocks use :12–:22.
  - Release exports run between :21 and :45, with the SAM mtime check.
  - Exports against a snapshot are exempt.
- **Shared mutable lake.** Another session running dbt makes live proofs irreproducible [OV §8.1].
  - Piece 2 writes nothing to the lake or Postgres.
  - The loader's lake stage reads DuckDB `read_only`.
- **Tests** use the 55432 throwaway cluster. Run one task's pytest steps at a time [FU README].

### 5.3 Worktree and release conventions (from the piece-1 plans)

- **Location.** The project is `GovBudget/` inside the worktree `families`. Branch from main `88538c6a`.
- **Command blocks.**
  - Every block starts with `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh`.
  - The SAM guard line follows wherever the block touches the live lake.
  - Python runs as `uv run --project .`.
- **Site setup.**
  - `site/node_modules` is a real directory, from `npm ci`.
  - The worktree needs its own `dbt parse` manifest.
  - Site builds read `data/site` through the `data/*` symlinks; proofs repoint them and put them back.
- **Commits** use `--author="Andes Lee <andes.lee444@gmail.com>"`.
- **Untracked files.** The untracked `data/research/eval-runs/*.json` files are not this wave's. Never commit or delete them.
- **Deploy** only by absolute path from this worktree, never from the main checkout.
- **Publish.**
  - Run `git subtree split --prefix=GovBudget` from the toplevel, then merge `govbudget/main` into the split.
  - Push to `govbudget` main.
  - Never push a worktree branch to `origin`.
- **Tool errors** print `<tool>: ERROR — <message>` and exit 2. A failed check exits 1 [FU §6].
- **Off-limits.** The other session's branch `wip/other-session-families-layout-2026-09-29` is read-only prior art. Nothing merges from it [OV §8.5].

---

## 6. Names

These names are frozen in piece 2. The reasons are in [MAP-ART §3] and [OV §8.2].

| Thing | Name |
|---|---|
| Field on every new row and artifact | `platform_family`. Never a bare `family_id`: lineage already uses `programs[].family_id` (an integer), and the contractor families use `family_key` |
| Family ids | `f-15`, `f-35`. They match `^[a-z0-9]+(-[a-z0-9]+)*$` |
| Files | `data-seeds/platform_families.json`, `data-seeds/platform_family_members.csv`, `data-seeds/platform_family_era_lines.csv` |
| Python | `src/govbudget/platform_families.py` (loader, vocabularies, `RegistryError`, the one-off F-15 seed mode of §7.6); `src/govbudget/platform_family_history.py` (the builder); `f15_funding_history.py` stays as the facade |
| CLI | `govbudget platform-families propose \| render \| answer \| ratify \| check \| preview`, with `propose --seed-shipped f-15` as the seed mode's wrapper; `govbudget verify-families` |
| Review directory | `data/research/platform_families/<platform_family>/` (`review.csv`, `review_era_lines.csv`, `batches/B<n>.json`) |
| Rulings | Class rulings are `R-DEC-FAM-<FAM>-<NAME>`. Batches are `R-DEC-FAM-<FAM>-B<n>`. `<FAM>` is the id without hyphens, upper-case (`F15`, `F35`) |
| Fact-ID surfaces | Unchanged: `family_history` and `family_program_history`. They are already the F-15's, and they do not collide with the contractor `family_year` |
| History payload field | `family_id` stays inside `json/<history_dataset>.json` (schema 1, pinned). New artifacts use `platform_family` |

---

## 7. The registry formats

### 7.1 Where the files live, and why not dbt

- **Location.** `data-seeds/` is read by Python only, like `gao_program_xwalk.csv` and `entity_family_events.csv`.
- **Why not dbt.** A dbt seed adds a lake table. That would change the pinned snapshot and put `dbt build` on the release path [MAP-ART §4.1].
- **Lake checks.** The checks that need SQL against the lake run read-only from Python, as `era_map.check` already does.
- **CSV conventions**, as in the era seed:
  - the exact header is enforced;
  - every field is a string;
  - rows are sorted by their id;
  - writes go through `era_map._atomic_write_texts`.
- **Repository vs site.** The files are tracked in git, so they reach the public fiscalreceipts repository with everything else. A `draft` or `ratified` family is in the repository and never in the export.

### 7.2 `data-seeds/platform_families.json`

Unknown keys are rejected at every level. In the tables below, "Consumer" names the piece
that reads the field, and every field is validated by piece 2's loader whether or not
piece 2 uses it.

**Top level**

| Key | Type | Meaning | Consumer |
|---|---|---|---|
| `schema_version` | int, `1` | — | loader |
| `rulings` | list | Every ruling any row or family cites (below) | loader, ratify, the F-15 seed, index |
| `sources` | list | Every non-budget-book source an evidence ref or exclusion cites (below) | loader; pieces 3, 4, 7 |
| `families` | list, in output order | Family objects (below) | all |

**`rulings[]`**

| Key | Meaning |
|---|---|
| `ruling_id` | `^R-DEC-FAM-[A-Z0-9]+(-[A-Z0-9]+)+$`, unique |
| `kind` | `class` or `batch` |
| `platform_family` | the family the ruling covers |
| `decided_by` | `owner` (the only allowed value) |
| `decided_on` | ISO date of the owner's answer (for a class ruling, the date the spec was approved, as in [FU §5.1]) |
| `owner_reply` | the owner's message, verbatim, non-empty |
| `spec` | repo path + anchor of the spec that defines it |
| `text` | what the ruling decides, one paragraph |
| `seed_basis` | bool. `true` lets counted rows under this ruling stand without an independent evidence ref (§7.5). This spec grants it to `R-DEC-FAM-F15-SEED` only; the loader keeps that allow-list in code |

**`sources[]`**

| Key | Meaning |
|---|---|
| `source_id` | `^[a-z0-9][a-z0-9-]*$`, unique |
| `title`, `publisher`, `url`, `as_of` | as printed; `as_of` is an ISO date |
| `sha256`, `bytes` | of the exact file read, when known |
| `archived` | bool: a sha-pinned copy is in the site's file store |
| `archive_path` | required when `archived` is true |
| `tier` | `G` (reported by the US government), `PG` (a partner government's official publication, which counts as government-reported [OD 2026-10-20]), `C` (a company or other claim), `X` (press or secondary; never usable) |
| `verified_by` | a list of `source_id`s with tier `G`/`PG`. It is required for a `C` source before anything may cite it (the evidence rule [OD 2026-10-19]) |

**`families[]`**

| Key | F-15 value | F-35 value | Meaning | Consumer |
|---|---|---|---|---|
| `platform_family` | `f-15` | `f-35` | **Frozen.** It is inside the `family_history` fact-ID keys and the route | builder (fact IDs), index, piece 4 route |
| `status` | `published` | `draft` until B1 is ratified, then `ratified` | `draft`: written by `propose` with the full family object; its rows are under review in `review.csv`; it may have zero member rows, and it may not be published (§9.1 rules 5 and 23). `ratified`: owner-ratified, validated, never exported. `published`: built and exported. **Design call (controller, 2026-10-20)** for `draft` (§8.3) | loader, builder, index |
| `published_ruling_id` | `R-DEC-FAM-F15-SEED` | — | Required for `published`; absent on a `draft`. A family moves to `published` only from `ratified`, and only by an owner ruling (piece 4 for F-35). The F-15 is the exception: its seed writes it `published` directly (§7.6) | loader |
| `short_name` | `F-15` | `F-35` | **Frozen for F-15.** It is inside published formula text, the receipt grammar and error messages | builder, `program_pdf_receipts` |
| `history_dataset` | `f15_funding_history` | `f35_funding_history` | **Frozen for F-15.** Three things derive from it: the multi-input cell dataset token, the artifact path `json/{history_dataset}.json`, and the manifest key. Must match `^[a-z0-9]+_funding_history$` and be unique. **Design call:** one field, three derived uses, so no free path can drift | builder, index, audit |
| `on_partial_corpus` | `skip` | `raise` | What happens when the series lacks a counted code-keyed member. `skip` is the F-15's legacy "return None" for small fixture exports [MAP-F15 §4.2 #14]; new families raise. **Design call** | builder |
| `headline` | `{"measure": "cumulative_actuals", "first_fy": 2015, "last_fy": 2024}` | same window [F35 §1.4] | The builder checks that the derived cumulative window equals this. A mismatch raises, so PB2027 forces a deliberate re-stamp | builder, piece 4 |
| `scope_note` | verbatim `SCOPE_NOTE` | proposed on the B1 page (piece 4 finalizes) | Byte-bearing for F-15 | builder |
| `coverage_notes` | the 7 `COVERAGE_NOTES`, verbatim, in order | proposed | Byte-bearing for F-15 | builder |
| `review_guard` | `{"exhibits": ["P-1","R-1"], "title_substrings": ["F-15","F15"]}` | `{"exhibits": ["P-1","R-1"], "title_substrings": ["F-35","F35","JSF","JOINT STRIKE","F135","LIGHTNING"]}` | Every lake row of these exhibits, in **any** account, whose upper-cased title contains a substring must be covered by a row of this family. Otherwise it is "Unreviewed". F-15's value reproduces `member_row` exactly: a substring test on `title.upper()` with no account filter [CODE `f15_funding_history.py:138-143`]. F-35's substrings are the research's workbook search terms, which find exactly the 15 members plus JSM000 [F35 §1.3 item 1] | builder, loader stage 2 |
| `program_notes` | `{"P-1:3010F:AF:F015E0": {"note": <verbatim>, "note_fact_id": "e7d5bcfb4a30f458", "expected_receipt": {"kind": "jbook_narrative", "page_number": 71, "pe_bli": "F015EX", "sha256": "528d1441…bc01e"}}}` | `{}` | Owner-signed member notes with their exact receipt [CODE l.61-77] | builder (`check_program_notes`) |
| `variants` | `[{"id":"A"},{"id":"B"},{"id":"C"},{"id":"D"},{"id":"E"},{"id":"EX"}]` | `[{"id":"A"},{"id":"B","note":"F-35B is a Marine Corps jet bought from the Navy's aircraft account"},{"id":"C","note":"F-35C includes Marine Corps jets"}]` [F35 §2.2 pt 3] | Vocabulary for `variant_ids` | loader; piece 4 cut and variant cards |
| `program_tags` | proposed (§7.6) | `[{"tag":"F-35","mdap_code":"198"}]` [F35 §1.1] | Vocabulary for `program_tag` | pieces 3, 4, 7 |
| `purpose_tags` | `[]` | `["production","modifications","sdd","block4","usaf_squadrons"]` [F35 §1.1, §4.1] | Vocabulary for `purpose_tag` | piece 4 toggles |
| `caveat_ids` | `["classified","construction","nominal_dollars","cr_years"]` (read off `COVERAGE_NOTES`) | `["classified","construction","operating_and_support","spares","foreign","cr_years","nominal_dollars"]` [F35 §4.2] | The standard caveat list [OV §6]. The vocabulary is exactly these seven | piece 4 |
| `exclusions` | `[]` | §7.7 | `[{exclusion_id, kind: outside_scope\|not_a_budget_line\|shared_line, label, size_text, evidence: [ref]}]`. `size_text` is cited text, never summed | piece 4 "what is not counted" |
| `aliases` | `[]` | `[]` | Reserved for #209 (piece 4) | piece 4 |
| `contract_routes` | `null` | `null` | Reserved: `{program_codes, description_pattern, description_exclusions, basis: action\|award}`. F-35 values are proposed in [F35 §4.2] (code `198`; excludes F-350, Joint Strike Missile, bare "lightning"). The basis is the owner's piece-7 call | piece 7 |
| `official_estimates` | `null` | `null` | Reserved: `{msar_program_number, msar_source_ids, gao_program_key, wsaa_exit_ruling}` (F-35: `198`, `f35` [F35 §4.2]) | MSAR/GAO ingestion |
| `art` | `null` | `null` | Reserved: `{src, alt, caption, generated}`. `generated: true` requires a caption containing "AI-generated" [MAP-ART §1.1] | piece 4 |

**Not stored (design call; standard in code instead):**
- the route (`/families/{platform_family}/`, by R-DEC-FAM-NAME);
- `schema_version`, `units` and `basis` of the history payload;
- the cumulative scope note ("Sum of covered annual recorded actuals only …", generic text);
- formula templates, the edition rule, measure rules, the reuse allow-list and sort orders (§10.2).

Storing any of these per family would let one family drift from the standard.

**Supplier layers stay out of the registry (design call).** These are facts about companies, not budget-line membership:
- the "named by the US government" identity rows;
- the subcontractor panels;
- the work locations;
- partner claims.

Piece 7 keeps them in its own seed, keyed by `platform_family` [F35-SUP §3.1, §5]. Piece 2 only fixes the tier vocabulary they will use.

### 7.3 `data-seeds/platform_family_members.csv`

Column order is frozen exactly as listed. Blank means empty. The "Piece 2 uses" column says
whether the builder reads the field (**B**), the loader checks it beyond its vocabulary
(**L**), or the field is reserved, vocabulary-checked and otherwise unread (**R**).

| # | Column | Meaning / vocabulary | Piece 2 | Consumer later | Source of the field |
|---|---|---|---|---|---|
| 1 | `member_row_id` | `{platform_family}\|{member_id}\|{valid_from_edition}-{valid_to_edition}` | L | all | era seed `decision_id` style [MAP-ART §4.3] |
| 2 | `platform_family` | must exist in the JSON | B | all | F35 §4.1 `family_id` |
| 3 | `member_id` | `{exhibit}:{account}:{ORG}:{code}`, where ORG is the **era spelling** (`AF`, `NAVY`, `ARMY`; a defense-wide agency code as printed). **Frozen:** it is the F-15 `program_id` inside 27 cell fact IDs, the page entity and `data-history-program` [MAP-F15 §4.2 #2]. Regex `^(P-1\|R-1\|P-1R):[0-9]{4}[A-Z]+:[A-Z0-9]+:[A-Z0-9]+$` (the receipt grammar's `[A-Za-z0-9:]+` must still hold) | B | all | — |
| 4–7 | `exhibit`, `account`, `organization`, `code` | must agree with `member_id`; `organization` uses the era spelling; `P-1R` only with role `context` | B | all | F35 §4.1 identity |
| 8 | `role` | `counted` (in the total), `context` (shown, never summed), `project_slice` (one R-2 project in a shared line), `excluded` (reviewed, not a member; it keeps a review-guard match from raising and from being re-proposed) | B | all | OV §2; MAP-ART §4.3 |
| 9 | `verdict` | `approved`, `deferred`, `rejected`. Only `approved` rows reach the builder; `deferred` rows are recorded and never exported | B | all | F35 §4.1 |
| 10 | `project_number` | required iff `project_slice` | L | piece 6 pilot | MAP-ART §1.1 |
| 11 | `appropriation` | `procurement` or `rdte` | L | piece 7 account cut; MSAR recompute | F35 §4.1 |
| 12 | `budget_activities` | `;`-list of the BA codes the member's lines print in | L | piece 7 (production vs modification lines, defect D1); piece 8 | F35 §4.1 |
| 13 | `titles_seen` | Exact filed titles of the member's **code-keyed** lake rows by edition: `2024: F-15; 2025: F-15; 2026: F-15` (era-seed format). Era rows' titles live in the era-lines file. The builder checks each code-keyed row's title against its edition's entry | B | piece 9 re-check | — |
| 14 | `display_title` | The exported program title. Byte-bearing for F-15 (`F-15 (legacy support line)`, `F-15e (FY2020 F-15EX Lot 1 aircraft)`) | B | piece 4 | — |
| 15 | `page_slug` | The program page slug, blank if the member has no page. Checked at stage 3 against the export's program identity (`_ProgramIdentity`, collision slugs like `0145-APN`) | B | piece 4 backlinks | MAP-ART §2.6 |
| 16, 17 | `valid_from_edition`, `valid_to_edition` | PB years, integers within the ingested editions (2017–2026), from ≤ to | B | all | F35 §4.1 |
| 18 | `coverage_expected_from_edition` | The first edition from which absence is reported in `missing_programs`. Blank means never. F-15's legacy values are kept as data (§10.3) | B | piece 4, piece 9 | MAP-F15 §4.2 #10 |
| 19 | `expected_next_edition` | e.g. `2027`; tells "not yet" from "missing" | R | piece 9 | F35 §4.1 |
| 20 | `era_decision_ids` | `;`-list of era-seed `decision_id`s covering the member's PB2017–23 rows | L | piece 1 linkage; piece 8 | F35 §4.1 `era_chain_id` |
| 21 | `drift_sha256` | `era_map.keys_sha256` over the **distinct** P-1/R-1 lake lines the row binds within its editions (one per line, not one per amount column): code-keyed lines as `(edition, code, ba, title)` and era lines as `(edition, era_key, ba, title)` | L | piece 9 | F35 §4.1 `drift_sha` |
| 22 | `member_order` | Integer output order within the family (matrix rows, `programs[]`, browser record order). Contiguous 1..n over approved counted rows; blank otherwise. Never sort by code or dollars [MAP-F15 §4.2 #6] | B | piece 4 | — |
| 23 | `program_tag` | from the family's `program_tags` | L | pieces 3, 4, 7 | R-DEC-FAM-UNIT |
| 24 | `purpose_tag` | from the family's `purpose_tags` | L | piece 4 | F35 §4.1 |
| 25 | `purpose` | `buy`, `upgrade`, `develop`, `support`; blank only when `page_slug` is blank | L | piece 4 template; F-15 mirror | F35 §4.1 |
| 26–28 | `variant_ids`, `variant_scope`, `scope_note` | `;`-list from the family's `variants`; `variant` or `shared`; `scope_note` is required on `shared` rows and on every `context` row | L | piece 4 cut | F35 §4.1; MAP-ART §1.1 |
| 29, 30 | `services_using`, `paying_org` | `;`-list from `USAF`, `USN`, `USMC`, `USA`, `USSF`, `SOCOM`, `DW`; one of `AF`, `NAVY`, `USMC`, `ARMY`, `USSF`, `SOCOM`, `DW`. `paying_org` is who paid, not who benefits [F35 §2.2] | L | piece 4 development-by-payer column | F35 §4.1 |
| 31–34 | `predecessor_member_id`, `successor_member_id`, `link_basis`, `link_evidence` | resolve to rows of the same family; `link_basis` is `book_stated`, `era_map` or `inferred`; `book_stated` needs a `doc:` ref with `q=` | L | history series; piece 9 | F35 §4.1 |
| 35 | `evidence` | `;`-list of typed refs (§7.5) | L | release checks | F35 §4.1 `evidence_ids` |
| 36–38 | `quantity_bearing`, `quantity_row`, `quantity_notes` | `true`/`false`; cost-type letter; text. Allowed only on counted rows | R | piece 8 | F35 §4.1 |
| 39 | `jbook_anchor` | `doc:<sha256>#p<page>;xml=<path>;units=<Thousands\|Millions>` | R | piece 8; receipts | F35 §4.1 |
| 40 | `contract_link_policy` | `production+AP`, `modifications_only`, `development`, `none` | R | piece 7 (stops D1 recurring [F35 §3.1]) | F35 §4.1 |
| 41–43 | `msar_account`, `msar_funding_source_page`, `msar_shared_flag` | account; page; `true`/`false` | R | MSAR recompute gate | F35 §4.1 |
| 44, 45 | `allocation_source`, `allocation_years` | Context rows only: a `doc:` ref to a book-stated per-system amount; a FY list | R | piece 4/5 "context with a book-stated amount" | F35 §1.2, §4.1 |
| 46–48 | `decided_by`, `ruling_id`, `decided_on` | `owner`; a ruling in the JSON whose `platform_family` matches; that ruling's `decided_on` | L | release checks | R-DEC-FAM-REVIEW |
| 49 | `note` | free text, never published | — | — | — |

- **Not a column:** `gao_xwalk_status`. It is derived from `data-seeds/gao_program_xwalk.csv` by `page_slug`, so there is one source [MAP-ART §4.3].
- **Design call:** the full header, reserved columns included, is frozen now [MAP-ART §5 #7], so pieces 4, 7 and 8 attach without a header change.

### 7.4 `data-seeds/platform_family_era_lines.csv`

One row per era key that an approved counted member binds:
`platform_family, member_id, edition, era_key, budget_activity, filed_title, decision_id`,
sorted by (`platform_family`, `edition`, `era_key`).

- **Why it exists (design call).** The builder must stay hermetic. The V5 fixture rebuilds the F-15 with no lake, so the roster cannot be derived from `p1_era_line_map` at build time [MAP-F15 §4.2 #12; MAP-ART §2.3].
  - This file is a **pinned copy** of the map's rows for the member's decisions. It works the way `ERA_MEMBERS` × `ERA_PROGRAM_CODES` do today.
  - Only tools write the rows, never by hand. `propose` measures a family's era lines into `review_era_lines.csv` beside `review.csv`, and `ratify` moves those of the ratified counted rows into this file. Rule 25 (§9.1) accepts an era row only for an approved counted row, so nothing reaches this file before `ratify`. The F-15's rows are written by its seed (§7.6).
  - Stage 2 and `verify-era-map` leg c prove the rows equal to the map at every export and every release.
- **F-15.** 31 rows, exactly today's roster, written by `propose --seed-shipped f-15`. Example rows: `f-15,P-1:3010F:AF:F01500,2018,3010F-AF-L23,05,F-15,F01500|3010F||2017-2023` and `…,2018,3010F-AF-L80,07,F-15,F0150P|3010F||2017-2020` [CODE l.30-50].
- **F-35.** The rows of its six procurement chains (ATA000, F03500, 0152, 0592, 0147, 0593), whose decisions are all `R-DEC-ERA-SAME` [CODE era seed]. `propose` measures the count.

### 7.5 Evidence references and tiers

| Prefix | Resolves to | Checked at | Independent membership signal? |
|---|---|---|---|
| `era:<decision_id>` | A row of `dbt/seeds/p1_era_code_decisions.csv`. Its code and account must equal the member's; its organization must equal the member's for `ORG_SPLIT_CODES`, and be blank otherwise. Its decision must be `same_program` or `history_only` | stage 1 | No. It proves chain identity, not family membership |
| `fact:<16 hex>` | a citation in the export's `json/citations.json` | stage 3 | No when the fact is the member's own narrative (the other session's mistake [MAP-ART §1.2 #4]); yes when it is another line's book text naming this member |
| `doc:<sha256>#p<page>[;q=<verbatim>]` | A sha-pinned PDF or XLSX in `data/site/{pdfs,workbooks}`. The page must be in range, and the quote must be found on the page | stage 2 | Yes (budget book, tier G) |
| `src:<source_id>[#p<page>]` | A `sources[]` entry. A published family's source must be `archived`. Tier `X` is refused. Tier `C` needs `verified_by` | stage 1, plus archive presence at stage 2 for published families | Yes, if tier is `G` or `PG` |
| `ev:<id>` | reserved for piece 3's evidence table | — | — |

**The bar a proposal must clear (loader rule).** Every approved counted row carries at least
one independent signal: a `doc:`, a `src:` with tier G/PG, or a non-self `fact:`. The one
exception is a row whose ruling has `seed_basis: true`, which this spec grants only to the
F-15 seed (§8.1).

**Owner:** the evidence rule [OD 2026-10-19] and the partner-government tier [OD 2026-10-20].
**Design call:**
- the `PG` label;
- the `seed_basis` exception;
- the requirement that a draft or ratified (unpublished) family may cite unarchived sources, while a published one may not. The F-35's MSAR was hashed in a browser and never saved [F35 §3.3; research `verify-gao_sar.md:5`].

### 7.6 Entry #1: the F-15 (status `published`, ruling `R-DEC-FAM-F15-SEED`)

These eight rows reproduce the shipped builder. Columns not shown are blank, or carry the values this table implies.

| `member_order` | `member_id` | `display_title` | `page_slug` | valid | `coverage_expected_from_edition` | `era_decision_ids` | `purpose` / `variant_ids` / `variant_scope` | `program_tag` (proposed) |
|---|---|---|---|---|---|---|---|---|
| 1 | `R-1:3600F:AF:0207134F` | F-15E Squadrons | 0207134F | 2017–2026 | 2017 | — | develop / C;D;E;EX / shared | F-15 |
| 2 | `R-1:3600F:AF:0207146F` | F-15EX | 0207146F | 2021–2026 | 2021 | — | develop / EX / variant | F-15EX |
| 3 | `R-1:3600F:AF:0207171F` | F-15 EPAWSS | 0207171F | 2017–2026 | 2017 | — | develop / E;EX / shared | EPAWSS |
| 4 | `P-1:3010F:AF:F01500` | F-15 | F01500 | 2017–2026 | 2024 | `F01500\|3010F\|\|2017-2023` | upgrade / C;D;E / shared | F-15 |
| 5 | `P-1:3010F:AF:F015EX` | F-15EX | F015EX | 2021–2026 | 2024 | `F015EX\|3010F\|\|2021-2023` | buy / EX / variant | F-15EX |
| 6 | `P-1:3010F:AF:F15EWS` | F-15 EPAW | F15EWS | 2019–2026 | 2024 | `F15EWS\|3010F\|\|2019-2023` | upgrade / E / variant | EPAWSS |
| 7 | `P-1:3010F:AF:F0150P` | F-15 (legacy support line) | — | 2017–2020 | never | `F0150P\|3010F\|\|2017-2020` (history_only) | blank | F-15 |
| 8 | `P-1:3010F:AF:F015E0` | F-15e (FY2020 F-15EX Lot 1 aircraft) | — | 2020–2022 | never | `F015E0\|3010F\|\|2020-2022` (history_only) | blank | F-15EX |

**How the entry is written: design call (controller, 2026-10-20).** A one-off seed mode,
`propose --seed-shipped f-15`, writes it. The mode is part of the registry module
(`platform_families.py`) and is built in task 3, so it does not wait for task 7's full CLI.
Task 7 later wraps it as a `propose` option (§8.3).
- **What it reads.** Today's constants in `f15_funding_history.py`: `PROGRAMS`, `MODERN_MEMBERS`, `ERA_MEMBERS`, `ERA_PROGRAM_CODES`, `PROGRAM_NOTES`, `NOTE_RECEIPTS`, `SCOPE_NOTE`, `COVERAGE_NOTES` and the hardcoded expected set.
  - It runs once, before the facade (§10.4) replaces those constants.
  - The values the Python module does not hold are written from this section's table: `purpose`, variants and row scope notes (from `RECORD_CONFIG`), the record-link `fact:` refs and the program tags. The vitest mirror (§13) proves the first three against the TypeScript.
- **What it writes.**
  - The F-15 family object, with `status: published` and `published_ruling_id=R-DEC-FAM-F15-SEED`. The F-15 is the only family written `published` directly; it is never a draft.
  - The ruling `R-DEC-FAM-F15-SEED` (§8.1), with the owner's verbatim approval of this spec as `owner_reply` and its date as `decided_on` (pending; recorded when given).
  - The 8 member rows. Each carries `decided_by=owner`, `ruling_id=R-DEC-FAM-F15-SEED` and the ruling's `decided_on`.
  - The 31 era-lines rows. The era-lines file has no ruling column (§7.4), so these rows stand under the ruling through their member row (rule 25 accepts an era row only for an approved counted row).
- **Lake-measured values** (`titles_seen`, `budget_activities`, valid ranges, `drift_sha256`) are measured against the pinned proof snapshot fam2 (§14 step 1), for the proof. The release re-measures them against the live lake as a precondition (§15 step 1).
- **Its own refusals.** It lists every error at once, writes nothing on a refusal, and writes atomically. It refuses:
  - any family other than `f-15`;
  - an F-15 family already in `platform_families.json` (the mode is one-off);
  - a value that differs from the shipped output. The shipped output is fam2's `json/f15_funding_history.json`, whose sha must first equal the pin `tests/fixtures/f15/history.sha256`. The values compared are `programs[]` in order (ids, codes, titles, slugs, notes and note fact IDs), `scope_note` and `coverage_notes`;
  - an era roster that differs from fam2's `p1_era_line_map` (stage 2 item 3);
  - a blank owner reply or a non-ISO date (stage 1 rule 6);
  - any stage-1 failure, or any stage-2 failure against fam2, on the result.
- **Its own tests** live in `tests/test_f15_registry_parity.py` (§13). They feed the mode that file's literal `88538c6a` copies, so they keep passing after the facade lands.

How each column is sourced:

- **Order, identities and titles:** copied from `PROGRAMS` and `MODERN_MEMBERS` [CODE l.19-26, 78-93].
- **`coverage_expected_from_edition`:** copied from the hardcoded expected set [CODE l.218-224]:
  - 0207134F and 0207171F are always expected;
  - 0207146F from PB2021;
  - F01500, F015EX and F15EWS from PB2024;
  - F0150P and F015E0 never.
- **`purpose`, variants and scope notes:** copied from `RECORD_CONFIG` in `site/src/lib/f15-family-data.ts:9-16`. The two history-only rows have no site record, so they are left blank [MAP-ART §4.3].
- **Valid ranges:** taken from [MAP-ART §4.3]. The seed mode measures them against fam2, and stage 2 enforces them.
- **`titles_seen`:** the single constant title per code-keyed member, measured by the seed mode against fam2.
- **Evidence:**
  - the era refs above;
  - the record-link narratives in `f15-family-data.ts` (0207134F `fact:0026c924483c6624`, F01500 `fact:c9e5c28dfebc879e`, 0207171F `fact:b30fae1fd23999e4`);
  - the three that [MAP-ART §4.3] lists (0207146F `fact:d9982379a24ebac6`, F015EX `fact:e7d5bcfb4a30f458`, F15EWS `fact:b3dbc6ed30814fdf`). The implementer re-reads these from the TypeScript.

  These refs are not independent signals. That is why the F-15 stands on `seed_basis` until piece 3's calibration supplies independent ones [OV §3, piece 3: "recovers its 8 counted lines"].
- **`program_tag`:** **pending owner approval with this spec** (Pending owner decisions, item 2). It applies R-DEC-FAM-UNIT's own example: "F-15EX and EPAWSS separately" become tags inside the family [OV §1].
  - The tag vocabulary is `[{"tag":"F-15","mdap_code":null},{"tag":"F-15EX","mdap_code":null},{"tag":"EPAWSS","mdap_code":null}]`.
  - MDAP codes are left to piece 3.
  - No output reads tags in piece 2.

The family fields are in §7.2 and the era-lines rows in §7.4. `paying_org` is `AF` and
`services_using` is `USAF` on every row.

### 7.7 Entry #2: the F-35 (status `draft` until batch `R-DEC-FAM-F35-B1` is ratified, then `ratified`; never exported in piece 2)

`propose` writes the F-35 family object as a `draft` and these rows into `review.csv`
(§8.3). They reach `platform_family_members.csv` only through `ratify`.

**Counted members (15 lines in 4 accounts)** [F35 §1.1; FY2015–24 actuals in $M from F35 Appendix B1].
The order is the research's §1.1 order, which is also the cut's order. **Design call:** F-35
order is unpublished, so piece 4 may reorder before publishing.

| `member_order` | `member_id` | Title [F35 §1.1] | valid [F35 §1.1] | FY15–24 $M | `purpose_tag` / `purpose` | variants / scope | `paying_org` | `era_decision_ids` | Independent evidence [F35 §1.1] |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `P-1:3010F:AF:ATA000` | F-35 | 2017–2026 | 53,368.3 | production / buy | A / variant | AF | `ATA000\|3010F\|\|2017-2023` | P-40 names program "F-35, 198" (`doc:` AF Aircraft Procurement Vol I, PB2026) [V-CON M1] |
| 2 | `P-1:3010F:AF:F03500` | F-35 Modifications | 2017–2026 | 2,095.0 | modifications / upgrade | A / variant | AF | `F03500\|3010F\|\|2017-2023` | MSAR funding sources p.25 (`src:msar-pb2027#p25`) |
| 3 | `P-1:1506N:NAVY:0152` | JSF STOVL | 2017–2026 | 22,654.9 | production / buy | B / variant | NAVY | `0152\|1506N\|\|2017-2023` | MDAP 198 on the P-40 |
| 4 | `P-1:1506N:NAVY:0592` | F-35 STOVL Series | 2017–2026 | 1,328.9 | modifications / upgrade | B / variant | NAVY | `0592\|1506N\|\|2017-2023` | MSAR p.25 |
| 5 | `P-1:1506N:NAVY:0147` | Joint Strike Fighter CV | 2017–2026 | 20,097.4 | production / buy | C / variant | NAVY | `0147\|1506N\|\|2017-2023` | MDAP 198 |
| 6 | `P-1:1506N:NAVY:0593` | F-35 CV Series | 2017–2026 | 667.3 | modifications / upgrade | C / variant | NAVY | `0593\|1506N\|\|2017-2023` | MSAR p.25 |
| 7 | `R-1:3600F:AF:0604800F` | F-35 EMD | 2017–2023 | 1,939.5 | sdd / develop | A;B;C / shared | AF | — | MSAR funding sources |
| 8 | `R-1:1319N:NAVY:0604800N` | JSF EMD | 2017–2025 | 1,659.7 | sdd / develop | A;B;C / shared | NAVY | — | MSAR funding sources |
| 9 | `R-1:1319N:NAVY:0604800M` | JSF EMD | 2017–2025 | 1,758.8 | sdd / develop | A;B;C / shared | USMC | — | MSAR funding sources |
| 10 | `R-1:1319N:NAVY:0604810N` | JSF Follow-On Modernization | 2017–2020 | 194.2 | block4 / develop | A;B;C / shared | NAVY | — | MSAR p.26 [V-GAO missed-1] |
| 11 | `R-1:1319N:NAVY:0604810M` | JSF Follow-On Modernization | 2017–2020 | 199.3 | block4 / develop | A;B;C / shared | USMC | — | MSAR p.26 |
| 12 | `R-1:3600F:AF:0604840F` | F-35 C2D2 | 2020–2026 | 4,627.4 | block4 / develop | A;B;C / shared | AF | — | MSAR |
| 13 | `R-1:1319N:NAVY:0604840N` | F-35 C2D2 | 2019–2026 | 2,370.2 | block4 / develop | A;B;C / shared | NAVY | — | MSAR |
| 14 | `R-1:1319N:NAVY:0604840M` | F-35 C2D2 | 2019–2026 | 2,459.7 | block4 / develop | A;B;C / shared | USMC | — | MSAR |
| 15 | `R-1:3600F:AF:0207142F` | F-35 Squadrons | 2017–2026 | 1,387.6 | usaf_squadrons / develop | A / variant (scope note: Air Force-only work, counted in the development column by payer, never in the F-35A procurement bucket) [F35 §5 Q15] | AF | — | MSAR projects 675346, 675349, 676011 [F35 §1.1] |

The counted total over FY2015–24 is **$116,808.4M** [F35 §1.4, B1].

- **Predecessors.** `0604810N → 0604840N` and `0604810M → 0604840M`, with `link_basis=inferred` [F35 §1.1 #10, §5 Q1].
- **Services using.** ATA000 and F03500: USAF. 0152 and 0592: USMC. 0147 and 0593: USN;USMC. The development rows: USAF;USN;USMC [F35 §4.1].
- **Coverage.** `coverage_expected_from_edition` equals `valid_from_edition` on every F-35 row. That is honest under the attribution rule (§10.3), and it is a **design call**.
- **Reserved columns** stay blank. Pieces 7 and 8 fill them from [F35 §4.1] (for example ATA000 `quantity_bearing=true`, `quantity_row=A`, `contract_link_policy=production+AP`).

The member_id organization is normalized to the era spelling `NAVY`. [F35 §4.1] writes "Navy" [MAP-ART §4.3].

**Context rows (shown later, never summed)** [F35 §1.2]

| `member_id` | Title | Role | `scope_note` (the substance) | Evidence |
|---|---|---|---|---|
| `P-1:3010F:AF:000999` | Initial Spares/Repair Parts | context | A shared Air Force spares line. Its P-40/P-18 names "ATA000 / F-35 Squadrons [198]"; the book-stated F-35 amount is FY2024 $446.470M, FY2025 $440.846M, FY2026 $311.759M (Vol I pp.171, 174–175). Never summed | `era:000999\|3010F\|\|2017-2023`, `doc:` Vol I p.175 |
| `P-1:1506N:NAVY:0605` | Spares and Repair Parts | context | A shared Navy spares line. The book states F-35 amounts for 0147 and 0152 (APN BA6-7 p.47). Never summed | `era:0605\|1506N\|\|2017-2023`, `doc:` APN BA6-7 p.47 |
| `P-1:3020F:AF:JSM000` | Joint Strike Missile | context | A missile the F-35 carries, not the aircraft. A related line, not counted. It also covers the review guard's "JOINT STRIKE" match | `doc:` PB2026 P-1 |

- `allocation_source` and `allocation_years` are filled on 000999 and 0605 only if the owner approves the "context with a book-stated amount" class in piece 4 [F35 §5 Q4]. In piece 2 they stay blank, and the amounts live only in `scope_note` text, which is never exported.

**Deferred**

- `R-1:3600F:AF:0207268F`: role `project_slice`, `project_number=675365` (F135 CIP), `verdict=deferred`. It waits for the project-slice pilot [F35 §1.2, §5 Q15].

**Not in B1 (design call).** About ten lines name the F-35 in their text without an amount
(0705, 0570, 0720, …) [F35 §1.2]. Their titles do not match the guard, so piece 3 proposes
them.

**Family-level `exclusions`** [F35 §1.4]. Each has a cited `size_text`; none is ever summed.

| `exclusion_id` | `kind` | `size_text` (cited) |
|---|---|---|
| `initial-spares` | shared_line | "F-35 initial spares from shared lines 000999 and 0605: $766.3M in FY2024" [V-CON M1]. The ~$6.3B FY2015–24 inference is **not** recorded until the MSAR column is read (smaller true number) |
| `milcon` | outside_scope | "Construction: $4,022.7M over the program life, all FY2022 or earlier" (MSAR pp.92–93) |
| `operating-support` | outside_scope | "Operating and support: $1,395.0B TY / $596.4B CY12, through 2083" (MSAR p.32). Never added to acquisition; never "$1.93T" [F35 §3.3 rule 2] |
| `partner-share` | outside_scope | "Partner nations' share of development: $12.9B over the program life" (MSAR pp.85, 99) |
| `fms` | outside_scope | "Foreign buyers' aircraft (FMS): 530 aircraft, $89,475.6M as listed" (MSAR pp.67–68) |
| `before-fy2015` | outside_scope | "Spending before FY2015 is not shown" |
| `classified` | outside_scope | "Classified funding: unknown" [OV §5.8] |
| `programming-codes` | not_a_budget_line | "0204146N and 0204146M are named on the 0147 and 0152 P-40s but exist in no P-1 or R-1 workbook; the ATA000 note's PE 0207142F is a programming code, and the R&D line 0207142F is separate money" [F35 §1.1] |

**Sources added for the F-35.**
- `msar-pb2027`:
  - "DoD MSAR for the FY2027 budget, effective 21 April 2026";
  - `sha256 063345e4a46f7d58cf89356389fb36986e5a0f8c06c716030ead49932e8dca50`, 1,298,631 bytes, 122 pages;
  - `tier G`, `archived false` [research `f35-gao-sar-official.md:103`; `verify-gao_sar.md:16`].
- The J-book PDFs are cited by `doc:` and need no source entry.
- The F-35 family fields not shown here are the F-35 column of §7.2.

**Subcontractors.** The owner's 2026-10-19 "break out the sub contractors" is recorded in
the B1 page header as a piece-7 commitment. No registry field is needed for it (§7.2).

---

## 8. Owner ratification

### 8.1 `R-DEC-FAM-F15-SEED` (class ruling; pending owner approval with this spec)

**Text.**
> The F-15 family's registry entry records the eight budget lines the shipped F-15
> history counts, as they ship at main 88538c6a. It records:
> - their order, identities and display titles;
> - the coverage rule (which lines are expected in which editions);
> - the 31-line era roster;
> - the F015E0 note and its receipt;
> - the family's scope and coverage notes.
>
> It changes no published figure, text or fact ID. Its evidence basis is the shipped
> family history (the F-15 family funding correction recorded in the ROADMAP on
> 2026-09-24), the piece-1 era decisions and the page's record-link narratives. Piece 3
> must add an independent signal for each line before any F-15 row changes.

**Fields.**
- `kind=class`, `platform_family=f-15`, `seed_basis=true`.
- `decided_on` is the date the owner approves this spec: 2026-10-21.
- `owner_reply` is the owner's verbatim approval of this spec: "approved, would process with recommendation to approve all" (2026-10-21). **Design call (controller, 2026-10-20).**
- `spec` is this file's §8.1.
- The seed mode (§7.6) writes the ruling, and every F-15 member row cites it.
- The proposed program tags (§7.6) are part of this approval.

### 8.2 `R-DEC-FAM-F35-B1` (one batch, through the batch page)

**Design call: why a new batch answer, not a re-use of the 2026-10-19 reply.** The
2026-10-19 reply approved the 15 lines and the cut [OD]. The registry rows carry things
that reply never saw:
- edition ranges;
- evidence refs;
- drift hashes, which must be computed at review time;
- the inferred predecessor links;
- the three context rows, the deferred slice, the exclusions and the other family fields;
- the preview figures those rows produce.

So B1 is rendered and answered like an era batch. Its header quotes the 2026-10-19 reply
as the prior approval of the member set. The owner's answer to the page is the
`owner_reply`. It is expected to be a confirmation, and it costs one round trip.

**The page.** `platform-families render --family f-35 --batch B1` writes a private page
plus a JSON manifest. The manifest holds exactly the rows shown, the sha256 of `review.csv`
and of `review_era_lines.csv`, and the sha256 of the draft family object together with the
`sources[]` entries it cites. `ratify` refuses if that family hash no longer matches
(§8.3). The pattern is `scripts/era/review_batch_page.py` [MAP-ART §2.2].
- **Order:**
  1. the preview figures (below);
  2. the counted rows, sorted by FY2015–24 actuals, largest first (ATA000 53,368.3 … 0604810N 194.2), per R-DEC-FAM-REVIEW;
  3. then the context rows, with whole-line amounts labelled "not counted";
  4. then the deferred row;
  5. then the draft family object's fields (the F-35 column of §7.2) and the exclusions.
- **Contents of each row:**
  - the identity;
  - the role;
  - the edition range;
  - the tags;
  - the evidence refs, each with its tier;
  - the `drift_sha256`;
  - the FY2015–24 dollars and the reason.

**The preview: design call (controller, 2026-10-20).** `render` runs
`platform-families preview --family f-35 --draft` against fam2 before it writes the page.
B1 is not yet ratified at that point. The owner then approves the rows with their
consequences visible.
- **`--draft` is explicit.** It makes the preview read the draft family object and the proposed rows in `review.csv` (with `review_era_lines.csv`). Without the flag, `preview` never reads a draft, and it never falls back to one silently.
- **The figures on the page:**
  - the per-year counted totals and the FY2015–24 cumulative, in thousands;
  - beside them, [F35 Appendix B1]: FY2015 8,276.5 … FY2024 13,469.6, cumulative 116,808.4, FY2025 enacted 12,532.3, FY2026 request 11,467.0 ($M);
  - each difference, with its member-year cause.
- **A preview that shows a wrong row blocks the page.** A preview error, or a difference whose cause is a row of the proposal, means no page is written. Fix the proposal first, re-run `propose`, and render again.
  - A difference with any other cause (for example lake drift since 2026-10-19) is shown on the page with that cause.
  - Rows are never adjusted to match.
- **Scratch only.** The preview's output directory is never written to `data/site` and never committed. Its figures appear on the batch page and in the branch ledger (`.superpowers/sdd/families-piece2/`).
- The preview proves that the proposed rows, their era roster and the generic builder agree with the owner-reviewed numbers, before the owner answers.

**The answer.** `answer` takes
`{batch, decided_on, owner_reply (verbatim, required), rows: {member_row_id: amendment | {"defer": true}}}`
and writes `data/research/platform_families/f-35/batches/B1.json`. It refuses:
- unknown keys;
- a changed `review.csv` (by sha);
- a blank `owner_reply`;
- a non-ISO date.

An answer amends rows only. A change to a family field is made by re-running `propose` and
rendering a new page, because `ratify` refuses a family object that differs from the one
the page showed.

**If the owner defers B1: design call (controller, 2026-10-20).**
- The F-35 family object stays in `platform_families.json` as a `draft` with zero member rows, which stage 1 accepts (§9.1 rule 23). Its rows stay in `review.csv`.
- Nothing about the F-35 is written to `platform_family_members.csv` or `platform_family_era_lines.csv`.
- The preview figures appear only on the B1 page and in the branch ledger. They never appear in the proof note's release claims (§14 step 8). The ROADMAP stamp carries one line saying B1 was deferred, and nothing more about the F-35 (§15 step 8).
- Piece 2 can still release, because nothing published depends on the F-35. Stage 2 reports a draft family's guard matches as undecided, never as failures (§9.2).

### 8.3 Tools (`govbudget platform-families …`)

| Command | What it does |
|---|---|
| `propose --family <id> --family-json <json> --rows <csv>` | **Design call (controller, 2026-10-20).** Takes two prefilled inputs. The family JSON is the full family object (`review_guard`, `variants`, `program_tags`, `purpose_tags`, `caveat_ids`, `exclusions`, `headline`, `scope_note`, `coverage_notes`), plus the `sources[]` entries it cites. The rows CSV carries role, tags, evidence refs and the reason per row. For the F-35 both are written from [F35 §1.1–§1.4, §4.2]; piece 3 generates later prefills. `propose` writes the family object into `platform_families.json` with `status: draft`, adding its sources to the top-level `sources[]`. It refuses to overwrite a `ratified` or `published` family. It writes the proposed rows into `review.csv` and their era lines into `review_era_lines.csv`; nothing reaches the members or era-lines CSVs before `ratify`. It fills every lake-derived column from the warehouse, read-only and outside :12–:22: `titles_seen`, `budget_activities`, `drift_sha256`, era lines from `p1_era_line_map`, and FY dollars for sorting. Reviewed `excluded`/`rejected` rows are never re-proposed. A lake result that differs from a ratified row goes back to review; it is never silently overturned (`era_map._hold_for_review` pattern) |
| `propose --seed-shipped f-15 --duckdb <fam2> --site-dir <fam2 site> --decided-on DATE --owner-reply <file>` | The one-off F-15 seed, with its own refusals and tests (§7.6). Task 3 builds it in the registry module; task 7 wraps it here. **Design call (controller, 2026-10-20)** |
| `render --family <id> --batch B<n>` | Runs `preview --draft` against fam2, then writes the batch page and its manifest. A preview that shows a wrong row writes no page (§8.2) |
| `answer` | §8.2 |
| `ratify --family <id> --batch B<n> --decided-on DATE` | **Design call (controller, 2026-10-20).** Writes the ratified rows into `platform_family_members.csv`, and their era lines into `platform_family_era_lines.csv`, as `decided_by=owner`, `ruling_id=R-DEC-FAM-<FAM>-B<n>`. It flips the family's `status` from `draft` to `ratified`. It records the ruling in the JSON: `R-DEC-FAM-<FAM>-B<n>`, `kind=batch`, `decided_by=owner`, `decided_on`, and the verbatim `owner_reply` from the answer. It runs the stage-1 loader on the merged result, then stage 2 against the warehouse. It refuses, listing every error at once and writing nothing (#198 style), on: a reused batch; a family object (with its cited sources) whose hash differs from the batch manifest's, that is, a family object changed since the page was rendered; a lake hash that differs from the review-time `drift_sha256`; any stage-1 or stage-2 failure (§9). Writes are atomic |
| `check [--strict]` | Stage 1, plus stage 2 for every family. It reports `undecided` (guard matches no row covers, and `deferred` rows) and `stale` (rows whose hash moved). `--strict` exits 1 on either |
| `preview --family <id> [--draft] --site-dir <snapshot site> --duckdb <snapshot> --out <dir>` | Runs the generic builder for a non-published family into a scratch directory. It refuses any `--out` inside `config.SITE_DIR`. **Design call (controller, 2026-10-20):** `--draft` reads the draft family object, `review.csv` and `review_era_lines.csv`; without it, `preview` refuses a `draft` family rather than read it silently. `render` runs it for every batch page (§8.2) |

The CLI conventions (exit 0/1/2, `<tool>: ERROR — …`) follow [FU §6].

---

## 9. The loader (`platform_families.load_registry`): fails loudly

The loader collects every error in a stage and then raises one `RegistryError` listing all
of them. Each line reads `platform-families: <file>[:<row id>]: <reason>`. A later stage
does not run if an earlier one failed.

### 9.1 Stage 1: files only (no lake, no export)

This stage runs on every import of the facade, in `program_pdf_receipts`, in `export_site`,
and in every CLI. The V5 tests therefore still run on fixtures with no lake. It fails on
each of these:

1. **JSON format.** The JSON does not parse; `schema_version` ≠ 1; a required key is missing; or an unknown key appears at any level (families, rulings, sources, nested objects).
2. **`platform_family`.** It fails `^[a-z0-9]+(-[a-z0-9]+)*$` or is duplicated.
3. **`short_name`.** It is duplicated or outside `^[A-Za-z0-9][A-Za-z0-9 /-]*$`.
4. **`history_dataset`.** It fails `^[a-z0-9]+_funding_history$` or is duplicated.
5. **`status`.** It is outside the vocabulary; `published` lacks `published_ruling_id`; that ruling is missing or belongs to another family; or a `draft` family carries a `published_ruling_id` (rule 23).
6. **Rulings.**
   - `decided_by` ≠ `owner`;
   - `owner_reply` is blank;
   - `decided_on` is not an ISO date;
   - a `ruling_id` is duplicated or fails its regex;
   - `seed_basis: true` appears on a ruling outside the code allow-list, which holds `R-DEC-FAM-F15-SEED` only.
7. **Sources.**
   - `tier` is outside `G`/`PG`/`C`/`X`;
   - a `sha256` is not 64 hex;
   - an `X` source is cited by any approved row or exclusion;
   - a `C` source is cited without `verified_by` naming a `G`/`PG` source;
   - `archived` is true without an `archive_path`.
8. **CSV headers.** The members or era-lines header is not exactly the frozen tuple, in order.
9. **`member_row_id`.** It does not equal its formula, or is duplicated.
10. **`member_id`.**
    - It fails its regex, or disagrees with `exhibit`/`account`/`organization`/`code`.
    - The organization is a modern spelling (`F`, `N`, `A`) where an era spelling exists. The inverse of `era_map.ERA_ORG_TO_MODERN` decides this.
11. **Vocabularies.** An enumerated column is outside its vocabulary. This covers role, verdict, exhibit, appropriation, purpose, variant_scope, link_basis, contract_link_policy, booleans and service codes. Also: `P-1R` used with a role other than `context`.
12. **Editions.**
    - an edition is not an integer, or lies outside 2017–2026;
    - from > to;
    - `coverage_expected_from_edition` is outside [from, to];
    - `expected_next_edition` ≤ to.
13. **Overlaps within a family.** Two rows of one family share a `member_id` and overlapping editions.
14. **Counted twice.** One `member_id` is approved as `counted` in two families with overlapping editions. This is the double-count hazard. The `family_program_history` key carries no family id, so two families would share receipts [MAP-ART §2.4].
15. **Shared codes.** Two approved counted members of one family share a `code`. The `missing_programs` list holds codes [CODE l.226].
16. **`member_order`.** It is not contiguous 1..n over approved counted rows, or it is set on any other row.
17. **Role rules.**
    - `project_slice` without `project_number`, or `project_number` on any other role;
    - a `shared` or `context` row without `scope_note`;
    - a context row with `coverage_expected_from_edition` or `member_order`;
    - allocation fields on a non-context row;
    - quantity fields on a non-counted row.
18. **Tags and variants.** `variant_ids`, `program_tag` or `purpose_tag` is not in the family's lists.
19. **Links.**
    - a predecessor or successor that is not a row of the same family;
    - a link without `link_basis`;
    - `book_stated` without a `doc:` ref carrying `q=`.
20. **Evidence refs.**
    - A ref is malformed.
    - An `era:` ref does not resolve, or resolves to another code, account or organization, or to a decision other than `same_program`/`history_only`.
    - A `src:` ref is unknown.
    - An approved counted row has no independent signal (§7.5) and its ruling lacks `seed_basis`.
21. **`era_decision_ids`.** One does not resolve, or does not belong to the member's code and account.
22. **Ruling references.**
    - An approved row lacks `decided_by=owner`;
    - its `ruling_id` is not in `rulings`;
    - the ruling covers another family;
    - the row's `decided_on` differs from the ruling's.
23. **Families without rows, rows without families.** A family appears in the CSV but not the JSON, or a `ratified` or `published` family appears in the JSON with no rows.
    - **Design call (controller, 2026-10-20).** The no-rows rule applies to `ratified` and `published` families only.
    - A `draft` family with zero member rows is valid: its rows are in `review.csv` until `ratify` (§8.3).
    - A `draft` family may not be published. It carries no `published_ruling_id` (rule 5), the builder never builds it, and only `ratify` moves a family out of `draft`.
24. **`program_notes`.**
    - a key is not an approved counted member of that family;
    - a note is empty;
    - a `note_fact_id` is not 16 hex;
    - the `expected_receipt` keys are not exactly `kind`, `page_number`, `pe_bli`, `sha256`.
25. **Era-lines rows.**
    - the member is not an approved counted row of that family;
    - the edition is outside the member's range;
    - the `era_key` fails the strict `era_keys._ERA_KEY_RE` [FU §6.4];
    - the account or organization inside the key disagrees with the member;
    - the `decision_id` is not in the member's `era_decision_ids`;
    - a (family, edition, era_key) pair is duplicated;
    - one era key is bound by counted members of two families.
26. **`review_guard`.** Its substrings are empty or not upper-case, or its exhibits are not a subset of {P-1, R-1}.
27. **`headline`.** first_fy > last_fy, or the measure is not `cumulative_actuals`.

### 9.2 Stage 2: lake (read-only)

**Where it runs:**
- inside the export, for each `published` family, after that family's partial-corpus gate decides to build;
- in `platform-families check`, `ratify` and `verify-families` leg b, for every family.
- **A `draft` family** has no member rows (rule 23), so stage 2 checks only its family object's `doc:` refs (item 7). It reports the family's review-guard matches as undecided, never as failures, so a deferred B1 never fails `verify-families` or blocks the release (§8.2). This follows from the §8.3 design call (controller, 2026-10-20).

**It fails on:**
1. **Code-keyed rows.** An approved counted member's code-keyed P-1/R-1 rows are missing from an edition its `titles_seen` lists, or a row's title differs from that edition's entry. It also fails on any code-keyed row in an edition outside the member's range.
   - The F-15 builder accepts out-of-range rows today. On today's lake there are none, so bytes do not change.
   - This fails loudly at PB2027 until piece 9 re-checks the members [OV §3, piece 9]. **Design call.**
2. **Drift.** `drift_sha256` does not recompute.
3. **Roster parity.** The era-lines rows of a member are not exactly the `p1_era_line_map` rows whose `decision_id` is in the member's `era_decision_ids`, with `program_key = line_item_code = code`. This generalizes `verify-era-map` leg c.
4. **Unmapped era lines.** A `p1_era_line_map` row prints an approved counted member's code in its account (plus organization, for `ORG_SPLIT_CODES`) and is neither in the era-lines file nor under an `exclude_*` decision. This is "every era line carrying a member's code is mapped or explicitly excluded" [OV §6].
5. **Review guard.** A guard-matching P-1/R-1 lake row is not covered by an `approved` or `rejected` row of that family.
   - In the export, the message is `Unreviewed {short_name} workbook identity: {edition}/{pe}`, the F-15's text today.
   - In `check`, a row covered only by a `deferred` row is reported as undecided.
6. **Collision codes.** An approved counted member's code is a collision code. `collision_keys.classify_shared_keys` names them: 10 codes are reused across accounts and 3 across organizations [OV §5.6].
   - The builder's series SQL ignores the collision `account`/`organization` columns, so such a member would mix accounts [MAP-F15 §4.2 #22].
   - **Design call:** refuse it now, and extend the series key when a family needs one. The F-15 hits none.
7. **`doc:` refs.** A file is missing by sha, a page is out of range, or a quote is not found on its page.
8. **`src:` refs** of a `published` family point at sources that are not archived, or whose `archive_path` sha differs.
9. **Partial corpus.** A family with `on_partial_corpus=raise` meets a series that lacks one of its counted code-keyed members.

### 9.3 Stage 3: the citation registry (inside the export, after the main citations and before any write)

It fails on:
1. **`fact:` refs.** One does not resolve in `json/citations.json`.
2. **Program notes.** A `program_notes[].expected_receipt` does not match. This is `check_program_notes`, with its message `"{short_name} program note receipt mismatch: …"`.
3. **`page_slug`.** It does not equal the export's program identity for (exhibit, account, organization alias, code), or it is blank while that member has a program page.
4. **Formula grammar.** A minted family receipt formula fails the registry-driven `additive_budget_formula` (§11).
5. **Recompute.** A total does not recompute from its leaves:
   - every annual, cumulative and cell total must equal the sum of its workbook amounts (exists today [CODE l.425-437]);
   - **new:** recursive expansion of every derived receipt down to `(sha256, sheet, cell)` leaves, with no leaf appearing twice in one total. The rule is `program_pdf_receipts.attach_additive_receipts`, applied before writing [MAP-ART §1.1].
6. **Overwrites.** A published fact would be overwritten with different identity fields (exists today [CODE l.404-414]).
7. **Leaf in two families.** One workbook leaf fact enters the totals of two families.
8. **Index projection.** The `json/families/index.json` projection does not equal the registry's published families (§12).

**If leaf expansion (5) fires on the F-15** at proof time, stop and report it. Never weaken
the check, and never change F-15 bytes to pass it.

---

## 10. The generic history builder

### 10.1 Shape and call position

**Module `src/govbudget/platform_family_history.py`**

| Function | What it does |
|---|---|
| `member_row(family, row)` | membership test for one lake row |
| `build_history(family, source_rows, series, *, retrieved_at, current_fact_ids=None)` | returns `(payload, citations, workbook_rows, breakdowns)` |
| `build_program_matrix(family, payload, previews, *, existing_citations, retrieved_at)` | the program-by-year matrix |
| `check_program_notes(family, programs, registry)` | note receipt check |
| `export_family_histories(*, duckdb_path, out_dir, registry)` | the post-pass |

**`export_family_histories` keeps today's post-pass exactly** [CODE l.347-497]:
- It runs **once**, from `export_site.py` where `export_f15_funding_history` is called today (l.3869-3875). That is after `export_site` has written `citations.parquet`, `citations.json`, the cite shards, workbook-cells, breakdowns and `manifest.json`, so the matrix still sees the full registry and reuses the 11 `decade` receipts [MAP-F15 §4.2 #3, #4].
- It processes published families in JSON order, in **one** staging directory, with one atomic replace.
- It keeps the same rules:
  - append only missing citations;
  - never overwrite an existing breakdown;
  - the same serializers (`_json_bytes`: compact, sorted, with a trailing newline);
  - re-copy the parquet with DuckDB zstd;
  - recount `json_sidecars` the same way [MAP-F15 §4.2 #15–#16].
- When no published family builds (small fixture exports), it returns `None` and writes nothing. That includes `index.json`. The `export_site` return counts stay as today.
- It calls the stage-2 and stage-3 loader checks of §9 for each family it builds.

**Design call:**
- One module, called from `export_site`, is the "builder inside `export_site`" of [OV §6]. The F-15 builder already lives in its own module, and moving 500 lines into the 18,000-line exporter would not add an audit.
- Retire `scripts/export_f15_funding_history.py`. It is a second entry point that writes family artifacts outside the CLI's receipt step. Nothing calls it [CODE grep]; only a historical plan task names it.

### 10.2 Standard (code) vs registry (data)

| Rule | Where it lives | F-15 value preserved |
|---|---|---|
| Edition rule: actuals FY+2, enacted FY+1, request FY; one scenario per (key, edition, kind); lake/mart count and value equality; workbook provenance required; duplicate leaf raises | code | yes [CODE l.181-197] |
| Measures: `_amount_type_meta`, `_decade_measure_token`, `_point_measure`. These are imported from `export_site`, never copied [MAP-F15 §4.2 #18] | code | yes |
| Component sort `(exhibit, pe_bli, ba or "", fact_id)`; cumulative inputs `(fy, edition, kind)`; cell inputs sorted; points `(fy, edition, kind)` [MAP-F15 §4.2 #7] | code | yes |
| Point id `fy{fy}{a\|e\|r}`; default point rule (actuals over enacted over request) | code | yes |
| Cumulative over contiguous actuals years, or raise | code | yes |
| Component `dataset`: `budget_lines` iff the fact is in this export's `data/budget_lines.parquet`, else `budget_lines_decade` | code | yes |
| Component `program_slug` and leaf citation `pe_bli`: the member's `page_slug`, **for code-keyed rows only**. Era rows get `None` even when the member has a page [MAP-F15 §4.2 #8]. **Frozen for schema-1 histories.** Piece 4 may add a schema-2 option for new families | code | yes |
| Matrix breakdown row `pe_bli`: the program's `page_slug` (or `None`) | code | yes |
| Fact-ID surfaces and keys: `fact_id_derived("family_history", f"{platform_family}\|{edition}\|{fy}", kind)`; `(… f"{platform_family}\|{first}\|{last}", "cumulative-actuals")`; `fact_id_derived("family_program_history", f"{member_id}\|{edition}\|{fy}", kind)` | code template, registry values | yes: `f-15`, `P-1:3010F:AF:F01500`, … |
| Formula templates (three, §11) with `{short_name}` / `{member_id}` | code template, registry values | yes |
| Reuse allow-list: own formula, then `…where amount_type={at} and edition={e})`, then `…where amount_type={at})`; lower index wins; `decade_era_map` never on it | code | yes [CODE l.313-334] |
| Multi-input cell `dataset` | registry `history_dataset` | `f15_funding_history` |
| Payload `family_id`, `scope_note`, `coverage_notes`; artifact path; manifest key | registry | yes |
| `programs[]` order, `id`, `code`, `title`, `program_slug`, `exhibit`, `account`, `organization`, `note`, `note_fact_id` | registry rows by `member_order` | yes |
| Era identity: era key from the era-lines file; exact (exhibit P-1, account, organization = member's era spelling, BA, title) | registry | yes |
| Code-keyed identity: (exhibit, account, `titles_seen[edition]`); organization ∈ {era spelling, its modern spelling} | registry plus `era_map.ERA_ORG_TO_MODERN` | yes (`{F, AF}`) |
| Title guard | registry `review_guard` | yes |
| Expected members per edition | registry `coverage_expected_from_edition` and `valid_to_edition` | yes (§10.3) |
| Partial-corpus gating | registry `on_partial_corpus` | `skip`, so it is identical |
| Error messages | code templates with `{short_name}` | yes. Every substring the tests match reads the same, because the F-15's `short_name` is `F-15`: "identity drift", "Unreviewed", "Duplicate F-15 scenario/workbook/matrix input", "missing year", "provenance missing", "matrix/annual total mismatch", "program note receipt mismatch" [MAP-F15 §2] |

### 10.3 The coverage rule becomes data (and stays byte-identical)

**Today** [CODE l.218-226]:
- `present` is the set of component `pe_bli`. Era components carry era keys, so they never count as present.
- `expected` is hardcoded per edition.

**Generic rule (design call).** A member is *present* in a point when at least one component
belongs to it: a code-keyed row with its code, or an era row its roster binds. It is
*expected* when `coverage_expected_from_edition ≤ edition ≤ valid_to_edition`.
`missing_programs` is the sorted codes of expected members that are not present.

**Why the F-15 bytes cannot change:**
- Era rows exist only in PB2017–23.
- The only F-15 members with era rows are F01500, F015EX, F15EWS, F0150P and F015E0.
- The first three are expected only from PB2024, and the last two never.

So attribution never adds a present member in an edition where it is expected. The upper
bound `valid_to_edition` removes nothing either: every expected F-15 member runs to 2026,
and the two that end earlier are never expected. A parity test proves the expected set per
edition against today's literal (§13).

**Why the generic rule matters for the F-35.** The F-35 can set `coverage_expected_from_edition`
to its true `valid_from_edition`. A procurement member absent from an era edition is then
disclosed, not hidden. Under today's rule it could not be.

### 10.4 The facade (`src/govbudget/f15_funding_history.py`)

At import, the facade loads the registry (stage 1) and binds `F15 = registry["f-15"]`. It
then exports the same names, derived from the registry:

| Name | Derived as |
|---|---|
| `MODERN_MEMBERS` | `{code: (exhibit, account, title)}` for counted members with code-keyed rows, in `member_order`. The title is the unique `titles_seen` value; the derivation asserts it is unique |
| `ERA_MEMBERS` | `{edition: [(line, ba, title), …]}`, editions ascending, lines ascending, from the era-lines file |
| `ERA_PROGRAM_CODES` | `{edition: {line: code}}`, from the era-lines file |
| `PROGRAMS` | in `member_order`, each `dict(id, code, title, program_slug, exhibit, account, organization, [note, note_fact_id])` |
| `PROGRAM_NOTES`, `NOTE_RECEIPTS` | keyed as today, by code and by fact id |
| `SCOPE_NOTE`, `COVERAGE_NOTES` | from the family's fields |
| `_json_bytes` | unchanged |
| `member_row(row)` | the generic function with `family=F15` bound |
| `build_history(source_rows, series, *, retrieved_at, current_fact_ids=None)` | the same, with `family=F15` bound |
| `build_program_matrix(payload, previews, *, existing_citations, retrieved_at)` | the same, with `family=F15` bound |
| `check_program_notes(programs, registry)` | the same, with `family=F15` bound |
| `export_f15_funding_history(*, duckdb_path, out_dir)` | `export_family_histories` restricted to `f-15`, with today's return keys |

**What runs unchanged on the facade:**
- `tests/test_f15_funding_history.py` (21), `tests/test_f15_era_identity.py` (4) and `tests/test_capture_f15_fixtures.py` (5);
- `scripts/era/capture_f15_fixtures.py`;
- `verify_era_map` legs c and g, which import `ERA_MEMBERS` and `ERA_PROGRAM_CODES`;
- `tests/test_verify_era_map*.py`, `tests/test_export_era_line_map.py`;
- `scripts/era/s4_report.py`, `fact_stability.py`, `scripts/fu/fact_delta.py` [MAP-F15 §5].

---

## 11. Receipt formulas and audits become registry-driven

**Formula templates (standard, code).** Each is filled from the registry. The F-15 strings
are unchanged [CODE l.215, 234, 312]:
- Annual: `sum(budget_lines.amount_thousands) for reviewed {short_name} members, PB{edition}, FY{fy} {kind}; one selected scenario column per workbook line`
- Cumulative: `sum(budget_lines.amount_thousands) via annual reviewed {short_name} actuals totals, FY{a}–FY{b}; each fiscal year once, nominal USD thousands; excludes enacted/current-year figures and requests`
- Cell: `sum(budget_lines.amount_thousands) for workbook program {member_id}, PB{edition}, FY{fy} {kind}; each selected workbook input once`

All three keep the `sum(budget_lines` prefix, so verify-phase5b1 Rule 4c still recomputes
them [MAP-F15 §1.2].

**`program_pdf_receipts.additive_budget_formula`.**
- Today it carries three literal tails, two of them naming "F-15" [CODE `program_pdf_receipts.py:266-277`].
- In piece 2 it builds them from the registry's **published** families:
  - per family, the annual and cumulative tails with `re.escape(short_name)`;
  - once, the generic `for workbook program (?:P-1|R-1):[A-Za-z0-9:]+, …` tail.
- **Design call:** published families only, so a draft family can never widen the grammar.
- With the F-15 as the only published family, the generated list equals today's three strings, in today's order. A test asserts exact string equality.

**The receipt audit.**
- Today the audit reads `json/f15_funding_history.json` to count `default_cells` and `default_complete`. The live value is 67/67 [MAP-F15 §1.2].
- In piece 2 it loops over published families' history artifacts and sums the counts.
- **Design call:** while the F-15 is the only published family, the report keeps exactly today's keys and values. Piece 4 adds a per-family block when a second family publishes.
- The audit's `citation_sha256` covers `citations.json`, which does not change, so `budget_pdf_receipts_audit.json` is identical in the A/B (§16).

**The verify legs.**
- `verify-era-map` legs c, f and g keep their code, names and verdicts. Legs c and g import the facade constants, which are now derived from the registry; leg f keeps the F-15 pin path.
- The generic checks go into `verify-families` (§13). **Design call:** this re-points the legs at the registry without editing a passing gate.

**Fact IDs.** No F-15 fact ID changes, because:
- the surfaces, keys, `platform_family`, `member_id` spellings, formula strings and allow-list are byte-equal;
- the minting order is unchanged: the builder still runs after the decade tier, so the 72 A1 era leaves keep `pe_bli` = printed code [MAP-F15 §4.2 #3].

V5's sensitivity test still shows that the allow-list is what protects the cells.

---

## 12. `json/families/index.json`

**Content** (`_json_bytes` serialization; no amounts, so link coverage and the receipt
audit are untouched):

```json
{"families":[{"history":"json/f15_funding_history.json","history_dataset":"f15_funding_history",
  "members":[{"member_id":"R-1:3600F:AF:0207134F","page_slug":"0207134F","role":"counted"}, … 8 rows in member_order],
  "platform_family":"f-15","route":"/families/f-15/","ruling_ids":["R-DEC-FAM-F15-SEED"],
  "short_name":"F-15"}],"schema_version":1}
```

**Rules**
- It lists `published` families only, in JSON order. Members appear in `member_order`, then context rows by `member_id`. The F-35 (`draft` or `ratified`) appears nowhere in the export.
- `members[]` lets piece 4 answer "which families is this program in" by identity, not by slug [MAP-ART §1.1, backlink].
- It is written by `export_family_histories` in the same staging pass, so `manifest.json` `json_sidecars` counts it. The CLI's `_refresh_json_sidecars` recounts it the same way [CODE `cli.py:2556-2580`].
- **It stays unpublished on the live site (design call).** `prepare-assets.mjs` copies `json/` files selectively and gets no new copy step. `deploy.sh` (through `upload_r2.sh`) uploads `pdfs/`, `data/`, `workbooks/` and `citations/` to R2, never `json/` [CODE `upload_r2.sh:27-30`].
  - So the file exists in `data/site` for gates and for piece 4's build-time route, and returns 404 on fiscalreceipts.com.
  - That keeps "readers see nothing" literal.
  - Piece 4 decides whether to ship it. Its route can read it from `data/site` at build time, so it may never need to.

---

## 13. Gates and tests

**Existing, unchanged** (the files themselves are byte-unchanged):
- `tests/test_f15_funding_history.py` (21 functions);
- `tests/test_f15_era_identity.py` (4: pin, golden, fresh state, sensitivity);
- `tests/test_capture_f15_fixtures.py` (5);
- `tests/fixtures/f15/*`;
- `tests/test_verify_era_map*.py`, `tests/test_export_era_line_map.py`;
- `site/scripts/gates/__tests__/f15-page-snapshot.test.mjs`;
- the F-15 vitest suites [MAP-F15 §2].

**New Python tests**

| Test | What it covers |
|---|---|
| `tests/test_platform_families_loader.py` | One red case per stage-1 failure in §9.1 (27 items; parametrized), plus a green case for a `draft` family with zero rows and a red case for a `draft` carrying `published_ruling_id` (rules 5 and 23). Stage-2 cases on a small DuckDB fixture: title drift, out-of-range edition, drift sha, roster ≠ map, unmapped era line, unreviewed guard match, collision code, missing `doc:`, and a `draft` family's guard matches reported as undecided, not failed. Stage-3 cases on a small registry dict: unresolved `fact:`, note receipt mismatch, slug mismatch, bad formula, leaf twice, index mismatch |
| `tests/test_f15_registry_parity.py` | The derived `MODERN_MEMBERS`, `ERA_MEMBERS`, `ERA_PROGRAM_CODES`, `PROGRAMS`, `PROGRAM_NOTES`, `NOTE_RECEIPTS`, `SCOPE_NOTE` and `COVERAGE_NOTES` equal literal copies taken from `88538c6a`. Those copies are kept **only** in this test, so the facade has one source and the test has the frozen reference [MAP-ART §6]. Also checked: the expected-member set per edition 2017–2026 equals today's rule, and the generated receipt tails equal today's three literal strings. The F-15 seed mode's own tests (§7.6) live here too: one red case per refusal, nothing written on a refusal, and a seed run on the literal copies that reproduces the committed F-15 entry |
| `tests/test_platform_family_history.py` | The generic builder on synthetic F-35-shaped rows. It covers four accounts (3010F, 1506N, 3600F, 1319N); NAVY/USMC R-1 rows with org `N`; a member ending at PB2020 that is not reported missing after; era-roster attribution counting as present; a context row (JSM000) that is never summed and silences the guard; an unreviewed "JOINT STRIKE" row that raises `Unreviewed F-35 workbook identity`; two families in one pass with no shared leaf; `on_partial_corpus=raise` raising; and `index.json` content |
| `tests/test_platform_families_cli.py` | propose → render → answer → ratify round trip on fixtures: refusals listed at once, nothing written on refusal, atomic writes, and the batch manifest sha checks. Also: `propose` writing a `draft` family object and refusing to overwrite a `ratified` or `published` one; `render` writing no page when `preview --draft` fails; `ratify` flipping `draft` to `ratified`, recording the ruling, and refusing a family object changed since the render; `preview` refusing a `draft` family without `--draft`, and refusing `--out` under the site dir |
| `tests/test_budget_pdf_receipts*.py` | One new case: a second published family's `short_name` is accepted by the grammar, and a draft family's is not |

**New CLI `verify-families`** (zero-argument defaults; last line `verify-families: PASS|FAIL`)

| Leg | Checks |
|---|---|
| (a) | Registry files load (stage 1) |
| (b) | Stage 2 for every family against the warehouse (read-only; the SAM guard applies). A `draft` family's guard matches are reported, never failed (§9.2) |
| (c) | Stage 3 for published families against `data/site`. `index.json` equals the projection. Each history artifact exists, its `family_id` equals `platform_family`, and its `programs[].id` equals the counted member ids in order. No unpublished family's `history_dataset`, artifact or `f-35\|` key appears anywhere in `data/site` |

It is added to `_ASSEMBLY_PHASES` in `verify_phase5.py`, and `_VERDICT_RE` becomes
`verify-(?:phase\w+|lineage|era-map|families):`, with the docstring and assembly tests
updated. This is the pattern piece 1 S4 used for `verify-era-map` [P1 §8 V4].

**Site side** (no page change)

- **Mirror test (vitest; hermetic: it reads `../data-seeds/platform_family_members.csv`).** The F-15's approved counted members with a `page_slug`, in `member_order`, must equal `F15_RECORD_SLUGS`. Their `purpose`, `variant_ids` and `scope_note` must equal `RECORD_CONFIG` in `f15-family-data.ts` [CODE]. This is CLAUDE.md's Python↔TypeScript mirror rule.
- **One leg added to `site/scripts/gates/family-history.mjs`.** Every family in `data/site/json/families/index.json` must have:
  - its history artifact in `data/site/json/`;
  - a built page at `out/families/<id>/index.html`.

  Today this holds for the F-15 alone.
- **Unchanged:** leg p, gate 1's weight row (`build.mjs:288`) and the manual snapshot tool. Piece 4 generalizes leg p when a second page exists.

---

## 14. The proof (byte identity on a pinned snapshot)

This uses the piece-1 Task 21 pattern with the #199-hardened tooling [FU §6.1, §7]. Piece 2
writes nothing to the lake or Postgres, so **one** snapshot suffices.

1. **Snapshot.** `govbudget proof snapshot --out .proofs/fam2 --scratch-db govbudget_proof_fam2`, taken in a SAM-safe window. The proof note records its shas: DuckDB at copy, the parquet manifest minus `sam/`, the site and raw_docs digests, and the Postgres table pins.
   - It is taken in task 1, before any registry value is measured. The F-15 seed (§7.6) and the F-35 `propose` and preview (§8.2) all measure against it.
   - Piece 2 writes nothing to the lake, so taking it early changes nothing the proof compares.
2. **Code.**
   - **A** is `git merge-base main HEAD` (`88538c6a`), in a detached worktree with its own `dbt parse`. It must be proven equal to the deployed code on `src/`, `dbt/`, `data-seeds/`, `scripts/` and `site/`.
   - **B** is the release HEAD.
3. **Exports.** Four clones and exports: A@fam2, B@fam2 and a control B2@fam2, each through the `export-site` CLI, which also runs `program_pdf_receipts`.
   - `proof diff B B2 --control --write-noise` must read EQUAL.
   - Then `proof diff A B --noise-from …` runs with the rules in `docs/superpowers/plans/2026-10-20-families-piece2/expected-diff-code.json`, which equal §16.
4. **F-15 bytes.**
   - The sha256 of B's `json/f15_funding_history.json` must equal `tests/fixtures/f15/history.sha256`. That file carries no build timestamp, so the comparison is byte-level, not structural [MAP-F15 §4.2 #15–#17].
   - Then run `test_f15_era_identity` on B's code.
5. **Facts.** `fact_stability.py` A vs B: zero facts missing, moved or changed.
6. **Links.** `govbudget link-coverage` against the committed baseline: unchanged.
7. **Page.**
   - Build the site from B@fam2 (the `data/*` links repointed, then restored).
   - `node site/scripts/f15-page-snapshot.mjs --check` against `tests/fixtures/f15/page_snapshot.json` must pass.
   - Gate 1's `/families/f-15/` weight must be unchanged, byte for byte, against an A@fam2 build.
8. **F-35 (no preview run here).** The preview ran inside `render`, against fam2, before the owner answered B1 (§8.2). The proof records B1's outcome. **Design call (controller, 2026-10-20).**
   - **B1 ratified:** the proof note quotes the figures the B1 page showed, with the batch manifest's sha256 and any amendments the answer made.
   - **B1 deferred:** the proof note says so in one line and makes no F-35 claim. The figures stay on the B1 page and in the branch ledger (§8.2).
9. **Gates.**
   - `verify-era-map` a–h;
   - `verify-families` a–c;
   - `verify-phase5b1`, `verify-phase5e`, `verify-lineage`, `verify-phase5` (assembly, now including `verify-families`);
   - `evals check`;
   - `npm run verify` and vitest on the B@fam2 build;
   - pytest on 55432;
   - W1 lint at the HEAD baselines [FU README].
10. **Proof note.** `docs/superpowers/reviews/families-piece2-proof.md`, with dated correction notes if anything is re-run.

Of the deferred #199 rules, build only those this rule list needs ("Rules 5–8, 17, 33 and
35 … when piece 2's proof needs them" [FU §6.9]). With two expected paths, none is
expected to be needed.

---

## 15. The release

The piece-1 follow-ups release steps apply [FU §8], without the live writes.

1. **Preconditions.**
   - The worktree is clean (the untracked `??` eval-runs files are ignored).
   - pytest is green on 55432.
   - The live lake's pins equal fam2's, SAM files excepted. If they do not, re-take the snapshot and re-run §14.
   - **The F-15's lake-measured values are re-measured against the live lake.** **Design call (controller, 2026-10-20).**
     - `platform-families check` re-measures `titles_seen`, `budget_activities`, valid ranges and `drift_sha256` (stage 2), read-only, in a SAM-safe window. This is the same pattern as `era_map.check` re-checking the era seed.
     - If live differs from fam2, stop before the export. Re-pin with a recorded reason: re-take the snapshot, re-measure, record the reason in the proof note, and re-run §14. Never silently.
   - B1 is ratified or explicitly deferred (§8.2).
2. **No live writes.** Nothing touches Postgres, DuckDB, dbt or the parquet tree.
3. **Export.**
   - Keep `.proofs/fam2-release-pre-site`.
   - Export the live `data/site` between :21 and :45, with the SAM mtime check.
   - Record `SAM_D` and fingerprint `data/site/{data,citations,manifest.json}`.
4. **Release-state checks.**
   - `proof diff` of B@fam2's site against the release `data/site`, with the noise file. Only SAM-registration rules may differ.
   - The F-15 sha equals the pin.
   - Link coverage passes.
5. **Gates and site.**
   - `verify-era-map`, `verify-families`, `verify-phase5`.
   - Build with `NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com`.
   - `npm run verify` and vitest, each after the fingerprint check.
6. **Deploy.** The owner's go-ahead names:
   - that readers see no change from piece 2;
   - `SAM_D`, the SAM registrations since the last deploy, which do change reader-visible company pages.

   Then run the fingerprint check, `deploy.sh --dry-run`, and `./scripts/launch/deploy.sh` by absolute path from this worktree.

   **Design call:** deploy rather than merge-only, so that live equals main and the ROADMAP stamp names a deployed commit with a rollback tag, as every families release has. If the owner prefers, the deploy can ride with the next release. The export and the merge still happen.
7. **Live checks.**
   - `/families/f-15/` returns 200, and its normalized snapshot equals the proof's.
   - `/json/f15_funding_history.json` hashes to the pin.
   - `/json/families/index.json` returns 404.
8. **ROADMAP stamp.**
   - A ledger row and a findings entry.
   - #209's Status line: "re-deferred to piece 4 by the piece-2 spec §3". Never reword the entry.
   - B1's state. If B1 was ratified, the F-35 preview figures as the B1 page showed them. If it was deferred, one line saying so, and nothing more about the F-35 (§8.2).
   - New entries for any finding.
   - `tests/test_roadmap_backlog.py` changes in the same commit as the stamp [FU README].
9. **Publish.** Fast-forward monorepo `main`, run the subtree split, merge `govbudget/main` into the split, and push to `govbudget` main.
10. **Cleanup offer.** Offer to remove `.proofs/fam2*`, the database `govbudget_proof_fam2` and the A worktree. Remove them only on a yes.

**Abort.**
- Before the deploy: restore `data/site` from `.proofs/fam2-release-pre-site`. There is no lake state to revert.
- After the deploy: the owner decides first. On a yes, follow LAUNCH.md's rollback (Vercel to the previous deployment, then R2 from `deploy.sh`'s rollback tag).

---

## 16. Expected differences (what the A/B diff must equal)

**Data A/B (A@fam2 vs B@fam2)**
- `json/families/index.json`: `only_b`, required.
- `manifest.json` `/json_sidecars`: changed, exactly +1.
- The `export_site` return value `json_files` is +1. It is not a file.

**Must be identical:**
- `json/f15_funding_history.json` (byte-level, by sha) and its 69 breakdowns;
- `json/citations.json`, the cite shards and `citations/citations.parquet` (no fact ID added, removed or changed);
- `data/*.parquet`, `json/datasets.json`, `json/site_meta.json`;
- `json/budget_pdf_receipts_audit.json` and the v2 receipt shards;
- workbook-cell shards, `json/era_map_summary.json` and every program sidecar.

**Site side:**
- No reader-visible difference.
- The new vitest mirror test and the gate leg are code, not output.

---

## 17. Risks

1. **Facade drift.** If the facade's constants were hand-kept, two sources would return. They are derived, and the parity test holds the only literal copies.
2. **Import-time loading.** A bad registry file now fails every importer of the facade: verify-era-map, the capture script, the export. That is the intended "fails loudly". The error names the file and row.
3. **Formula-competitor sensitivity.** The allow-list decides the F-15 cell IDs. The generated allow-list is code, identical, and V5 keeps proving it.
4. **Single-pass serialization with several families.** With one family, the bytes equal today's. A second family adds artifacts but never rewrites the F-15's. Piece 4 must re-prove this.
5. **The new leaf-expansion check could fire on the F-15.** Stop and report it (§9.3).
6. **The F-35 preview may not match the research.** The batch page reports each member-year cause. Possible causes are the roster, a collision code (§9.2 item 6) or lake drift since 2026-10-19. A mismatch that shows a wrong row blocks rendering the B1 page until the proposal is fixed; any other cause is shown on the page (§8.2).
7. **Stricter code-keyed edition checks** fail at PB2027. That is intended. PB2027 must not land during this piece [OV §8.6].
8. **Name collision.** A new program-keyed field named `family_id` would collide with lineage. Use `platform_family` everywhere new.
9. **Shared lake during the proof.** It is mitigated by the snapshot. The release export is checked against the proof with the noise file.

---

## 18. What is left to the builder (the implementer decides; no owner input needed)

- **Code shapes.** Internal dataclass shapes, helper names beyond those fixed in §6 and §10, and caching of the loaded registry.
- **Messages.** The exact wording of new error messages. Only the stage prefix and the F-15 substrings in §10.2 are fixed.
- **Test files.** Test file names and how parametrized cases are grouped.
- **The batch page.** Its look, reusing `review_batch_page.py`, and how `propose` computes sort dollars. The sort must be FY2015–24 actuals from the warehouse.
- **Values measured against fam2:**
  - the F-15 `titles_seen`, `budget_activities`, valid ranges and `drift_sha256`, by `propose --seed-shipped f-15` (§7.6);
  - the F-35 era-lines count, by `propose`;
  - the F-35 exact `doc:` page refs, found in the hosted corpus. Where a page is not hosted (the Navy R&D BA4–7 book [F35 App. C]), the row relies on the `src:msar-pb2027` ref.
- **`verify-families` legs.** Whether leg (b) splits into sub-legs.
- **The plan.** Task boundaries and parallel lanes. A suggested outline follows in Appendix A.

---

## 19. Decisions: whose call each one is

| # | Decision | Whose |
|---|---|---|
| 1 | Family per platform; program tags; the route; `platform_family` naming; batch review sorted by dollars; ERA-only lines countable | **Owner** (R-DEC-FAM-UNIT, -NAME, -REVIEW, -ERAONLY, 2026-10-02) |
| 2 | F-35 = 15 counted lines; variant cut plus a development-by-payer column; subcontractors broken out | **Owner** [OD 2026-10-19] |
| 3 | Evidence rule; partner governments count as government-reported | **Owner** [OD 2026-10-19, 2026-10-20] |
| 4 | Publish the smaller true number; every figure cited | **Owner** (2026-08-07; standing) |
| 5 | The registry is the alias source (#209) | **Owner** (follow-ups Q23); **design call:** its timing moves to piece 4 (§3). Pending owner approval with this spec |
| 6 | Approve `R-DEC-FAM-F15-SEED` and the F-15 program tags | **Owner**, with this spec. Pending; the approval message becomes the ruling's `owner_reply` |
| 7 | Ratify F-35 batch B1 | **Owner**, on the batch page |
| 8 | Deploy go-ahead (`SAM_D`) | **Owner** |
| 9 | Files in `data-seeds/`, three files, frozen full header | Design call |
| 10 | The era-lines file as a pinned, tool-written copy of the map (`propose` measures it; `ratify` or the F-15 seed writes it) | Design call |
| 11 | `history_dataset` drives the path, the token and the manifest key | Design call |
| 12 | `on_partial_corpus` (F-15 `skip`, new families `raise`) | Design call |
| 13 | The coverage rule by member attribution, plus `valid_to` | Design call |
| 14 | Standard rules in code; family text in data (§10.2) | Design call |
| 15 | One module called from `export_site`; retire the standalone refresh script | Design call |
| 16 | Receipt grammar from published families only; audit keys unchanged while the F-15 is alone | Design call |
| 17 | verify-era-map legs untouched; a new `verify-families` in the assembly | Design call |
| 18 | `index.json` lists published families only and stays off the live site | Design call |
| 19 | The source tier `PG`; the `seed_basis` exception (F-15 only); unarchived sources allowed only while unpublished | Design call |
| 20 | Refuse collision codes and out-of-range code-keyed rows | Design call |
| 21 | A fresh B1 answer, quoting the 2026-10-19 reply | Design call |
| 22 | F-35 order, coverage values, 0207142F's scope wording; the ten text-only lines left to piece 3 | Design call (F-35 is unpublished, so piece 4 can revise) |
| 23 | Supplier layers in piece 7's own seed, not the registry | Design call |
| 24 | Deploy rather than merge-only | Design call, at the owner's preference |
| 25 | A family under review is a `draft` family object in `platform_families.json`; `propose` takes a family JSON and a rows CSV; rule 23's no-rows check covers `ratified` and `published` only, and a draft may not be published; `ratify` flips `draft` to `ratified`, records the batch ruling, and refuses a family object changed since the render (§7.2, §8.3, §9.1) | Design call (controller, 2026-10-20) |
| 26 | The F-35 preview runs inside `render`, before B1 is answered, from the draft (`--draft`, never silently); a wrong row blocks the page; a deferred B1 keeps the figures to the batch page and the branch ledger (§8.2, §14 step 8, §15) | Design call (controller, 2026-10-20) |
| 27 | The F-15 entry is written by the one-off `propose --seed-shipped f-15`, built in task 3 with its own refusals and tests; lake-measured values come from fam2 and are re-measured against the live lake before the release (§7.6, §15 step 1) | Design call (controller, 2026-10-20) |

---

## Appendix A: suggested task outline (the plan may split or renumber)

| # | Task | § | Depends on | Parallel with |
|---|---|---|---|---|
| 1 | Worktree: base `88538c6a`, `npm ci`, `dbt parse`. Baseline: F-15 sha = pin; snapshot `--check` at base. Take the fam2 snapshot (§14 step 1), which the F-15 seed and the F-35 proposal measure against | 5.3, 14 | — | — |
| 2 | Formats, vocabularies and loader stage 1, with every §9.1 red case (rule 23 as amended) | 7, 9.1 | 1 | — |
| 3 | The F-15 entry: build `propose --seed-shipped f-15` in the registry module, with its refusals and tests; run it once against fam2 with the owner's verbatim approval of this spec, before the facade replaces the constants (the JSON family, 8 member rows, 31 era lines, `R-DEC-FAM-F15-SEED`). Then the facade derivation; the parity test; the 21 + 4 + 5 tests green and byte-unchanged | 7.6, 8.1, 10.4 | 2 | 6 |
| 4 | The generic builder and facade wrappers; V5 green; synthetic F-35-shaped tests | 10 | 3 | 6, 7 |
| 5 | Stages 2 and 3 inside the export; the call site; `index.json`; `json_sidecars` | 9.2, 9.3, 12 | 4 | 7 |
| 6 | `program_pdf_receipts`: registry-driven tails and audit loop, with tests | 11 | 2 | 3, 4, 7 |
| 7 | The CLI: `propose` (family JSON plus rows CSV; it also wraps task 3's seed mode), `render` (runs `preview --draft`), `answer`, `ratify` (the status flip and the family-object hash check), `check`, `preview`; `verify-families` plus the assembly; the vitest mirror; the gate leg | 8.3, 13 | 2 (3 for the seed wrapper, 4 for `preview`) | 4, 5, 6 |
| 8 | The F-35: the family JSON and rows prefill; `propose` against fam2 (a `draft` family object, `review.csv`, `review_era_lines.csv`); render B1, which runs `preview --draft` and puts its figures on the page (a wrong row blocks the page: fix the proposal first); ★ owner answer; then `ratify`, or record the deferral | 7.7, 8.2 | 7 | 5, 6 |
| 9 | The proof (§14). Step 8 records B1's outcome; it runs no preview | 14 | 5, 6, 7 (8 for step 8's line) | — |
| 10 | ★ The release | 15 | 9 | — |

★ marks an owner action.
