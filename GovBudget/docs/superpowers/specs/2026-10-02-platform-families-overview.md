# Platform Families — Program Overview

**Date:** 2026-10-02
**Status:** Direction approved by the owner (2026-10-02). Option B: weapon-system
families first, then broader program areas so that every program eventually belongs
to one group. Approach: hybrid (the machine proposes members with budget-book
evidence, the owner approves each, one page template). Owner quote: "the F-15 family
is great because it combines all the F-15 related programs together, I would like to
do this for the rest of the programs grouping them into families … Ideally all
programs are linked to the actual excel or PDF in the budget or receipt where
available."
**First piece:** [2026-10-02-era-procurement-history-design.md](2026-10-02-era-procurement-history-design.md)
**Evidence base:** five read-only research passes on 2026-10-01/02 at main `dc801fdb`
(F-15 as shipped, the other session's 12-family attempt, the program inventory and
grouping signals, source-document coverage, the piece-1 design) and one adversarial
re-check of the design's load-bearing claims. Numbers below come from those passes;
the ones the re-check corrected carry the corrected value.

---

## 1. Owner decisions recorded

| Id | Decision (2026-10-02) | Consequence |
|---|---|---|
| R-DEC-FAM-UNIT | A family is a **platform family**, like the F-15: one family per platform, each member tagged with its acquisition program so per-program totals stay visible. GPS = satellites + ground control + receivers; Abrams = tank + upgrades. | GAO's per-program unit (F-15EX and EPAWSS separately) becomes a tag inside a family, not the family. Identity-only machine grouping (MDAP codes) under-groups by design: F-15 comes out as 3 components. |
| R-DEC-FAM-NAME | Reader-facing name **"family"**, route **`/families/<id>/`** for every family. F-15 stays at `/families/f-15/`. | The lineage label "Branching family" on program pages is renamed so "family" means one thing on the site (piece 4). Internal identifiers use `platform_family` to stay distinct from contractor families (`entity_families.py`, `/companies/families/`) and lineage `program_family`. |
| R-DEC-FAM-REVIEW | **Claude pre-fills, the owner approves.** Every era-map decision and every counted family member is proposed with its evidence, sorted by dollars, and approved by the owner in batches. Nothing publishes without the owner's yes. | Seeds record `decided_by=owner` plus a ruling id. Class rulings (one ruling covering many rows) are allowed and are listed in the spec that uses them. |
| R-DEC-FAM-ERAONLY | **Discontinued procurement lines stay data only.** The 279 era-only code chains ($48.3B, e.g. JLTV's pre-FY2021 code, older EELV launch lines) get no program pages. Families may count them as predecessors later. Where a budget book states that a line continues under a new code, that link is recorded now. | Piece 1 records `successor_code` with its citation, e.g. JLTV `5600D15603` → `5731D15610`, from the PB2026 Army Other Procurement BA1 P-40 (p.100): "This budget line D15610 is a continuation of an existing effort where prior year funds through FY 2020 are reflected under the previous budget line D15603." |

Standing decisions that bind every piece: **publish the smaller true number**
(2026-08-07), and **every figure traces to a citation**.

---

## 2. Terms

| Term | Meaning |
|---|---|
| **Family** (reader) / `platform_family` (code) | A reviewed group of budget lines that fund one platform. |
| **Member** | One budget line in a family, identified by code + account (+ organization where a code spans organizations), with a valid edition range, a role and cited evidence. |
| **Role** | `counted` (in the family total), `context` (shown, never summed: shared spares lines, related programs), `project_slice` (one R-2 project inside a shared line; deferred until a pilot decides it). |
| **Program tag** | The acquisition program a member funds (F-15EX, EPAWSS …), so a family can show per-program subtotals. |
| **Program area** | A broader group for lines no platform family fits (basic research, ammunition, other procurement). Piece 10. |
| **Era key** | `{account}-{org}-L{line}`, the identity of one PB2017–23 procurement display line inside one edition. It stays the fact identity forever. |
| **Printed code** | The budget line code printed in the same row of the era workbook (column I, "Line Item"). Today's loader discards it. |
| **Chain** | All era keys across PB2017–23 that print the same code in the same account (and organization, for the five codes that span organizations). One review decision covers a chain or a dated range of it. |
| **Link coverage** | For a set of published figures: the share linked to a source document (workbook cell or PDF), and separately the share with a highlighted PDF location. Defined in §7. |

---

## 3. The pieces

Each piece gets its own spec → plan → implementation → deploy cycle and has its own
pass/fail check. A piece may not lower link coverage (§7).

| # | Piece | Scope | Depends on | What readers see | Pass/fail check |
|---|---|---|---|---|---|
| 1 | **Procurement history before FY2024** | Keep the printed code at load; review every era code chain once; program-grain decade table; old points on program pages; classified era rows loaded (never shown under a program); F015E0 relabel and F-15 classified/MILCON note; link-coverage tool and baseline | — | About 880 procurement program pages (about 800 with PB2026 lines, about 80 history-only) gain the PB2017–23 editions (FY2015–21 actuals), each point linked to its workbook cell and, where the matcher can, its PDF | Fresh A/B export on a pinned snapshot equals the expected-difference list; every existing fact ID unchanged; F-15 history JSON unchanged except the approved S5 changes (relabel, note, two coverage notes); `verify-era-map` in the release assembly |
| 2 | **Family list, F-15 as entry #1** | `platform_families.json` + members CSV; one loader that fails loudly; one generic history builder inside `export_site`; registry-driven receipt formulas and audits; `json/families/index.json`; F-15 rebuilt on it | 1 | Nothing (F-15 output byte-identical) | Golden pin; fresh A/B export against a pinned lake snapshot; 17 existing F-15 tests unchanged |
| 3 | **Member-evidence engine** | Extract MDAP codes, Code B PEs, Other Program Funding, related PEs, P-18 spares allocations, the adjudicated contract-program map, era continuity and approved aliases into one evidence table; group by identity edges, propose one hop beyond; per-family proposal files | 1, 2 | Nothing (research outputs) | Calibrated on F-15: recovers its 8 counted lines and marks shared spares lines as context; byte-identical reruns |
| 4 | **Family page template + F-35** | Standard sections that render only when data exists; per-family editorial slots; member → family backlinks; rename the lineage "Branching family" label; F-35 (10 lines, 4 accounts) as the first new family | 2, 3 (and 1 for F-35's pre-FY2022 procurement, pooled today in `3010F-AF-L1`) | First new family page | Independent recompute of every family total from seeds and lake (not from the builder); page weight; accessibility |
| 5 | **F-15 gaps** | All 30 budget snapshots with request/enacted/actual; GAO, lobbying and contract panels from member data; PDF pages for the 18 narrative passages without one; archived copies of the 62 web sources; the 36 related programs moved in as `context` members | 4 | Yes | Deliberate re-stamp of the F-15 pin, owner sign-off |
| 6 | **Pilots, then about 108 families** | Columbia (rename + account move + shipbuilding receipts), Sentinel (rename + Army radar name clash), GPS (Space Force account moves), Abrams (project slice 330), then batches by budget area starting where coverage is highest | 3, 4 | Yes | Per family: evidence resolves, ratified members only, recompute matches |
| 7 | **Contracts per family** | Review candidate contracts (F-15: $35.7B of FPDS descriptions mentioning F-15, FY2017–26, unreviewed); key by (code, source system); count each contract once across members | 2 | Yes | Sampled precision published; no double counting |
| 8 | **Quantities and unit cost** | Load P-1 quantity columns (row grain); P-40 quantities; unit cost only where weapon-system cost and advance procurement are separable | 2 (readers see it through 4) | Yes (via the template) | Recompute from workbook cells |
| 9 | **PB2027** | Ingest the PB2027 edition (posted 2026-04-03; brings FY2025 actuals); re-check members, renames and `expected_from` editions; remove FY2026 hardcodes | Scheduled between pieces, never in the middle of a piece that pins F-15 | Yes | Re-pin with sign-off |
| 10 | **Program areas** | Partition every program page into exactly one area or family; taxonomy from budget sub-activity titles, lineage families and categories; homes for shared lines and classified | 6 | Yes | Gate: every program page belongs to exactly one group |
| 11 | **Source backfills** | Service J-books before PB2026 (#89); narrative PDF pages (#90); O-1/C-1 exhibits; PB2012–16; era book diffs; the dead v1 receipt files | various | Varies | Link coverage rises |

Order: 1 → 2 → 3 → 4 → (5 ∥ 6). Pieces 7, 8 and 11 run alongside once 2 is done.
Piece 9 lands between pieces. Piece 10 follows 6.

---

## 4. What the F-15 family is missing

Measured on production and the local export (identical bytes) on 2026-10-01. Every
funding-table figure is already sourced: 276/276 matrix figures have a citation and a
complete PDF receipt; 207/207 leaf figures have a workbook cell.

| # | Gap | Evidence | Piece |
|---|---|---|---|
| 1 | **Mislabeled line.** The matrix calls F015E0 "F-15e (legacy line)". | PB2026 AF Aircraft Procurement Vol I, F015EX P-40, p.71: of the eight Lot 1 aircraft funded outside that exhibit in FY2020, two test aircraft were bought with RDT&E funds (PE 0207134F), and "four operationally representative test aircraft and two operational aircraft were purchased with procurement funds (F015E0, Line #3)". F015E0 is an FY2020 line ($1,050,000K requested, $621,100K enacted). | 1 |
| 2 | **No classified-funding or construction note.** | No coverage note mentions classified funding or MILCON. (The nominal-dollar note already exists, `COVERAGE_NOTES[4]`.) | 1 |
| 3 | Who got the money | 6 contracts linked to F-15 lines, none to F015EX. $35.7B of F-15-mentioning FPDS candidates (10,317 transactions; $14.6B FMS-funded), unreviewed. Largest unlinked: FA863418C2701 (F-15QA, $6.99B), FA863423F0048 (EX Lot 5 advance procurement, $3.93B). Subawards $6.46B under 10 primes. | 7 |
| 4 | Quantities and unit cost | F015EX: 24 aircraft FY2024 actual, 18 FY2025 enacted, 21 FY2026 request — in every P-1 workbook, dropped by the loader. | 8 |
| 5 | Request vs enacted vs actual per year | 30 snapshots exported, 12 shown (`family-funding-history.ts:93-99`). | 5 |
| 6 | GAO and lobbying on the family page | 6 GAO assessment entries (F-15EX, EPAWSS, 2023–25), 10 LDA filings; shown on member program pages only. | 5 |
| 7 | Budget-book text without a PDF page | 5 of 23 narrative passages have a page; 16 of 36 related programs have one. | 5, 11 |
| 8 | PB2027 and FY2025 actuals | Edition not ingested; the page's background text already cites the FY27 P-40 as plain text. FY2025/26 are "Partial" because EPAWSS development (0207171F) has no workbook figure for those years. | 9 |
| 9 | History before FY2015 | PE 0207130F (F-15A–D) and PB2012–16 not ingested (open ROADMAP item). | 11 |
| 10 | Unarchived web sources | 62 live links, no archived copy; af.mil returns 403 and saffm times out to automated clients. 11 dollar amounts in "Countries & orders" are plain text, not cited figures. | 5 |
| 11 | Guard/Reserve context | P-1R rows for F01500 exist and are not shown (context only, never counted). | 5 |
| 12 | Shared spares | Initial Spares (000999) names F-15 EPAWSS with no per-system amount. | 5 (context) |

---

## 5. What to consider when building other families

1. **Procurement history before FY2024 is missing everywhere except F-15** — 20,781
   era cells, 93 published. Families built today mix ten years of R&D with three years
   of procurement (the other session's F-35 showed $39.3M in FY2015 next to $11.9B in
   FY2022). Piece 1 fixes this first.
2. **Membership needs evidence, not names.** Strongest signals: J-book MDAP codes
   (R-2 and P-40), P-40 Code B program elements, R-2 Other Program Funding tables,
   the adjudicated contract-program map (`leg1_result.json`). Names mislead: in PB2026
   J-book titles "Sentinel" matches only an Army radar line, never the ICBM;
   "HERCULES" matches the M88 recovery vehicle. Signals conflict: the J-book labels the
   B-21 with MDAP code 437, while contracts carrying 437 describe AH-64E work. Both use
   the one DoD program-code list, so a few J-book assignments are stale (437, 247, 123,
   112), and per-code agreement between J-book title and FPDS description is a cheap
   bad-code detector.
3. **Membership needs dates.** Lines are renamed (HH-60W twice; Columbia was "OHIO
   Replacement"), move accounts (Columbia 1611N/1612N; GPS 3020F → 3021F/3022F) and
   change codes (JLTV D15603 → D15610; GBSD 0605230F → 0605238F). Without a valid
   edition range a line that did not exist yet reads as "missing".
4. **Line structure changed.** Since PB2024 one line folds in advance procurement;
   before that it was a separate line (F-15EX was lines 4 and 5 in PB2021).
   Shipbuilding lines carry full-funding and completion rows that can be negative.
5. **Shared lines are context only.** 144 generic lines ($23.3B FY2026) have no
   per-system amount (Air Force Initial Spares 000999 names 11 systems). Transitive
   grouping over every signal collapses hundreds of lines into one component, so
   grouping stays one hop from an identity core and hub lines never join two families.
6. **Identity is code + account (+ organization).** 10 codes are reused across
   accounts (0145 is F/A-18 in one account and General Purpose Bombs in another) and
   3 across organizations within 0300D (`20`, `30`, `500`).
   In PB2026, P-40 evidence must also carry the P-1 line number or budget activity,
   or Code B edges land on the wrong line (F01500 mixes modifications with
   post-production).
7. **Families span services.** F-35 is 10 lines in 4 accounts; H-60 is 10 lines
   across Army, Navy, Air Force and SOCOM. Contracts must be counted once: per-line
   sums give $626.1B for F-35, per-contract $161.2B.
8. **Classified money cannot be assigned.** $73.9B of FY2026 (19.2% of P-1 + R-1) is
   "Classified Programs". Every family carries an "excludes classified funding" note.
9. **Scale.** About 108 weapon-system families (an upper bound before review) covering
   about 47% of unclassified FY2024 money. Coverage is 69–80% for aircraft, ship and
   missile procurement but 0–16% for other procurement, ammunition and early research,
   which need program areas (piece 10).
10. **PDF highlight coverage varies by service and book.** Detailed R&D figures with a
    highlighted page: Navy 10.8%, Army 33.5%, Defense-Wide 100%. Era shipbuilding
    cost-type rows match the PDF poorly (DDG-51, Columbia, Patriot/LTAMDS: 6 of 9
    yearly points are workbook-only). Pages disclose this instead of hiding it.
11. **Upkeep.** Every new edition (PB2027 next) means re-checking members, renames and
    the era map. A family total's fact ID is derived from its inputs, so a restated
    amount changes the ID. Web sources need archived copies.

---

## 6. What is standard and what varies by family

**Standard (one of each, for every family):**
- One family list: one row per member with code, account, organization, role, program
  tag, valid edition range, predecessor/successor, evidence ids, verdict, who decided
  and when.
- One exporter inside `export_site`: every family figure goes through the same
  citation registry and audits. No second builder.
- One set of counting rules: per year, actuals → enacted → request from one edition;
  never sum base, OCO and total; missing is not zero; a request never fills an actuals
  gap; partial years are labelled; no workbook cell counted twice; every total
  rebuilds from its cited inputs; each contract counted once.
- One evidence ladder per figure: workbook cell → highlighted PDF location → official
  link.
- One page template whose sections render only when data exists: funding table,
  request/enacted/actual, quantities, contracts, GAO, lobbying, budget-book text,
  related lines, scope and caveats.
- One standard caveat list: classified funding, construction and operations not
  included, nominal dollars, foreign buyers' money outside DoD P-1/R-1, CR-adjusted
  measures where they apply.
- One set of release checks that test the output independently of the builder:
  counted members have live evidence; every era line carrying a member's code is
  mapped or explicitly excluded; receipts complete or disclosed; page weight per
  family; F-15 pinned.

**Varies by family:**
- Members, roles, dates, predecessor lines, account moves.
- Internal structure: variants (F-15 has 6), lots, hull classes, sub-families
  (C-130 across 12 lines), program tags.
- Which sections apply: quantities for production programs, foreign orders only where
  there are foreign buyers, project slices only where one line funds several systems.
- Milestones (as many as the history warrants), narrative, scope note, exclusions.
- Images: optional, accurate, captioned honestly.
- Disclosed PDF-highlight completeness (differs by service, budget activity, edition).

---

## 7. Link coverage — "every program linked to its Excel or PDF"

**Definition.** For each published money figure, its best link is one of: (a) a
complete PDF receipt (page + highlighted location), (b) a workbook cell in a
sha-pinned copy of the official workbook, (c) an official URL only, (d) nothing.
Derived figures take the weakest link among their inputs. Two scores, reported per
page and site-wide: **source-linked** = (a)+(b) share, which must stay 100% for budget
figures; **PDF-highlighted** = (a) share, which may not fall for any figure that
already has it.

**Baseline (2026-10-02, local export = production).** 55,749 budget figures on 2,562
program pages: 99.2% (a) or derived only from (a); about 0.8% (b) only; zero (c) or
(d). 42,153 workbook citations, all pointing to a cell in a sha-pinned workbook;
41,772 with complete PDF receipts. 2,437 of 2,562 pages fully PDF-highlighted. All 30
workbooks and 225 PDFs serve from assets.fiscalreceipts.com.

*Note (2026-10-02, piece-1 plan).* The figures above count appearances: the same
fact ID shown twice on a page counts twice. The committed `govbudget link-coverage`
tool scores distinct fact IDs across seven sidecar sections: 45,151 distinct budget
figures (44,747 (a), 404 (b), 0 (c)/(d)), 100.00% source-linked, 99.11%
PDF-highlighted, 2,437 of 2,562 pages fully highlighted. It also reproduces the
55,749 appearance count. Later pieces quote the distinct-figure numbers.

**What is missing is mostly what is not published yet:**

| Gap | Size | Piece |
|---|---|---|
| A. Procurement history PB2017–23 | 20,781 era cells, 93 published (F-15) | 1 |
| B. Shipbuilding and other rows the PDF matcher misses | 381 workbook facts / 471 cells (1611N cost-type rows for Virginia, Columbia, DDG-51, carriers; classified 3080F; PB2021 Space Force blanks) | 6, 11 |
| C. Budget-book page links | 6,764 detail figures and 5,601 narratives without a page (#90); Navy RDT&E BA4–8 at 8 of about 3,380 highlighted | 11 |
| D. Quantities | every procurement edition | 8 |
| E. PB2027 | one edition | 9 |
| F. J-book detail before PB2026 | Defense-Wide PB2017–25 in Postgres (~85% page provenance), not exported; services never fetched (#89, owner go/no-go) | 11 |
| G. PB2012–16 | five editions | 11 |
| H. Contract side | F015EX has 0 linked contracts | 7 |

---

## 8. Program-wide risks

1. **Shared mutable data lake.** Another session running dbt makes proofs
   irreproducible. Every before/after proof runs against a pinned lake snapshot whose
   sha is recorded in the proof note.
2. **Hashed identifiers.** Fact IDs hash surface strings and keys. Internal names
   (`platform_family`, surface strings) are fixed in piece 2 before the first
   non-F-15 family; renaming later changes published fact IDs.
3. **False continuity.** Code reuse and renames are the real hazard; chain decisions
   carry a drift guard (sha of the keys and titles reviewed) and re-review on change.
4. **Review fatigue.** Batches sorted by dollars, largest effects first; class rulings
   for the mechanical cases.
5. **The other session's branch** (`wip/other-session-families-layout-2026-09-29`)
   holds a JS builder, a dynamic `/families/[family]` route and a stripped F-15 page.
   None of it merges; ideas worth keeping (member inclusion model, fail-closed
   accounting rules, program → family backlink, honest art captions) are re-implemented.
   An empty `site/src/app/families/[family]/` directory is left in the main checkout
   and must stay empty until piece 4 decides the route.
6. **PB2027 timing.** It must land between pieces, never during one that pins F-15.
