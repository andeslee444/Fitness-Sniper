# GovBudget Roadmap — Source of Truth

**Updated:** 2026-09-25 (ledger sweep, roadmap-completion Task 1; integration merge of `codex/f15-family-browser`) · Living document: phase ledger, findings log, improvement
backlog, and the evaluator framework. Every phase loop ends by updating this file.

## Current priorities — trust and parallel product work (2026-09-22)

**F-15 family funding correction (2026-09-24):** replace the largest single
program's request with a cited history of the identified F-15 development and
procurement lines. The available span is FY2015–2026; the headline combines
FY2015–2024 actuals only. Enacted/current-year figures and requests remain
separate, with direct government workbook links for each input. Historical
procurement identities are matched within their budget editions. This
supersedes the earlier single-largest-record family lead rule. Implementation,
coverage limits and release checks are recorded in the
[family history record](plans/2026-09-24-f15-funding-history.md).

**Open historical coverage work:** backfill pre-FY2015 official P-1/R-1 books
and the older F-15A–D PE 0207130F; review program membership by edition and
account before adding amounts. Keep lifetime acquisition estimates separate
from annual funding, and shared operating/support budgets unallocated without
an F-15-specific source. Do not label the current covered-record total as
all-time or lifetime funding. Acceptance requires cited annual actuals without
overlapping editions, requests, totals/components or prior-years rollups.

**Publication checkpoint (2026-09-23):** the user authorized commit, push and
publication of this product slice. Source is pushed to the standalone Fiscal
Receipts repository. Release checks repaired the GAO
ratification, concentration-destination and flow-label defects recorded below.
Subaward receipts now require an explicit medium-confidence link contract,
without attributed dollars. The first production deployment and twelve exact
endpoint comparisons passed. Live PDF review then found a thousands/millions
receipt-label mismatch: canonical budget totals remain correct, while 1,421
receipt labels, six reviewed locators and four document-only fallbacks have
been corrected and republished. The final deployment passed all eight live
asset assertions and fifteen independent byte-for-byte production checks;
the corrected F-15 PDF and document-only fallback were also checked visually.
Deployment and final verification are
tracked in the [publication record](plans/2026-09-23-publication.md); the earlier
local-only checkpoints remain historical. The broad copy/voice-rule findings
remain open and must not be described as a fully green release suite.

**Refresh checkpoint (2026-09-24, published and live-verified):** bounded crosswalk
execution and stable assignments are implemented; the live FY2026 DARPA dry-run
projected 39,192 candidates and wrote none. Restored migrations 015–017 reconcile
source with the already-migrated curated store. Attribution reporting now uses
one shared tally over distinct published mart pairs, with the tier-wide
announcement draw pinned separately from the later wave study. Six reviewed PDF
locations were rechecked against source bytes and persisted before regeneration.
September 6 FY2026 contract/assistance archives passed staged key/date/amount and
retention checks and were promoted locally with rollback snapshots. Contract
actions reach September 4 and assistance August 30. The final production build,
eight live-asset checks and 19 exact public artifact comparisons passed. See
the [publication record](plans/2026-09-24-publication.md), [execution plan](plans/2026-09-24-refresh-and-reader-validation.md)
and [coverage review](plans/2026-09-24-award-coverage-review.md).

Final review reconciled six company labels against registration evidence,
archived four inactive aliases, and derived the current 14/200 methodology
census. The independent data-truth gate passes; the 15% threshold and award
groupings remain unchanged. Program pages distinguish linked award records
from an unavailable recipient total, fixing Hornet's contradictory absence
statement. The existing 22 copy/voice findings remain explicit release debt.
Browser review also exposed shared-code contamination in supporting PDF details
and narratives. Exact account/organization identity now excludes 164 sibling
detail rows and 65 sibling narratives from the 27 split program pages, while
retaining canonical source facts. The independent final audit checks 134 detail
rows, 53 narratives and 19 headline citations with zero errors. Unassignable
lobbying, prime and lineage claims are withheld with an explicit scope notice.
Functional source `ebbdf0d6` is deployed; standalone `main` merge `8cfb5720`
is pushed. The final frontend suite passes 1,572 tests, and 14/15 browser-free
gates pass with only the existing copy debt. Live receipt and program reviews
confirm the corrections. Normalized concentration exports retain their verified
confidence scope; feed attribution checks retain exact curated source labels.

Production page views are confirmed in the account. Two real reader actions
reached the analytics endpoint with HTTP 200, but the active Hobby plan does not
support custom-event reporting. The [measurement record](plans/2026-09-24-reader-measurement.md)
separates transport, reporting and human results. All five reader sessions remain
unrun; use the prepared observer sheet without making a paid plan a prerequisite.
The archive differences support a coverage update, not a program spending-change
briefing, because later reporting backfills earlier action dates.

The next product outcome is a reader reaching, checking and reusing a defensible
conclusion about public spending. Keep source freshness and attribution repairs
as the primary trust workstream. Advance the existing reader journey alongside
it; Jev supports editorial review rather than becoming the next public feature.

| Workstream | Roadmap items | Concrete next deliverable | Dependency and release boundary |
|---|---|---|---|
| Trust: current, dependable evidence | Existing #8 refresh; #78/#85 crosswalk execution; #79 rubric/export reconciliation; #80 concentration scope | Reconcile current source/code/export/live state, repair remaining attribution defects, and refresh available award releases through validation and publication | Check current evidence before repeating a study or declaring an old OPEN item fixed. Model confidence does not supply a missing budget-to-award link. |
| Product: complete the investigation journey | #166 flagship briefings; #167 reader measurement | Finish and measure the existing F-15 answer → receipt → save/share journey, then reuse the pattern for Virginia and Cyber Security Research where their sources support it | Can design, implement and test on dated, cited records now. Any new recipient attribution or change explanation waits for its own evidence review; unaffected source-backed views need not wait for every trust ticket. |
| Product: reasons to return | #168 reviewed changes and existing watch feeds | A small reviewed changes briefing plus a clear explanation of what following a program/company provides | Entry points and dated examples can be built now. Promising timely updates depends on #8 and a verified refresh-to-feed publication cycle. |
| Supporting experiment: Jev | #169 internal claim-review pilot | Review flags alongside the exact source passages for one existing dossier/briefing batch, with measured reviewer benefit | Run offline against supplied public evidence. Preserve human publication decisions and validate on fresh cases before adopting any model-based gate. |

**First parallel slice:** instrument the existing F-15 actions (#167) and complete
one reusable answer brief (#166). Reuse its current research tray, citation copy
and share-state behavior; do not rebuild those features. Prepare reader tasks
and a baseline while the trust workstream repairs ingestion and attribution.
These are planned work packages, not claims of implementation or deployment.

**Implementation checkpoint (2026-09-22):** the local pass below implements #166–#168
and completes one bounded #169 batch. The production build and desktop/mobile
answer journeys have been checked locally. The complete release suite is not
green: GAO attribution ratification, feed concentration destinations, flow-label
overlap and broad voice-rule failures remain. The F-15 lead now passes its source,
first-screen, accessibility, typography and unchanged page-weight checks.
No deployment has occurred; the reader study, production
event baseline and human Jev evaluation remain unrun. See the
[delivery and validation record](plans/2026-09-22-parallel-product-delivery.md).

**F-15 visual/source checkpoint (2026-09-22):** extended the flagship journey
with variant-aware one/two-seat drawings and tank configurations, one shared
family navigation and visual system across the six workspaces and six budget
pages, and prominent direct government PDF/workbook actions. Receipts preserve
source locations and offer selectable PDF text and evidence focus when the
record contains page/box metadata. Desktop/mobile review includes all family
sections, linked records, comparison/research states and aircraft variants.
Final local validation passed 1,385 tests, the production build, seven targeted
gates and all 24 program accessibility checks across widths and color schemes.
This remains local; government workbooks were reachable, while Air Force PDF
hosts returned TLS/gateway errors during probes. See the
[visual review and validation record](plans/2026-09-22-f15-visual-source-review.md).


**Current-state reconciliation:** the September 22 review found award actions
only through April 23 in the shipped coverage page/local export. It also found
local precision metadata recording a later attribution-rubric review while
exporter rules and the #79 status still describe the earlier state. Resolve the
database → exporter → published page chain before rerunning the study. Existing
dated findings and original backlog descriptions below remain historical records.

## Phase ledger

| Phase | Goal (source of truth) | Gate | Status | Live numbers |
|---|---|---|---|---|
| 0 | Federal backbone (USAspending archives → parquet → dbt) | dbt build + smoke | ✅ merged | contracts/assistance/subawards FY2017–2026 complete; 6.0GB contracts lake |
| 1A/1B | J-book extraction (embedded XML, all defense-wide books) | verify-phase1 | ✅ merged | 34 books, 4,421 detail facts, 2,457 narratives, recon gates green |
| 1C | Budget→spend crosswalk + marts | verify-phase1 --trace | ✅ merged | Gate-6 trace 5/5; link-table high/medium only |
| 2 | Beneficiary entity graph | verify-phase2 | ✅ merged | 76,727 families; Boeing 89 UEIs; 99.8% district coverage |
| 3 | Oversight layer (GAO high-risk, improper payments) | verify-phase3 | ✅ merged | 67 programs/$185.6B derived improper; 38 GAO areas 84.2% mapped |
| 4 | State pilot (CA/CT comparables) | verify-phase4 | ✅ merged | CA $314.1B full capture; 3 honest comparables |
| 5A | Influence layer (Senate LDA) | verify-phase5a | ✅ merged | 4,258 filings; 32,780 program mentions/245 programs; match 80% *(at 5A; the gate floor was raised to 0.85 on 2026-09-01, `bcfe9680` — measured 46/50 = 92% on the re-pulled 5,393-filing corpus; noted 2026-09-25)* |
| 5B-1 | Citation + export backbone | verify-phase5b1 | ✅ merged | 44,754 citations (3,417 pdf / 8,557 workbook / 32,780 lda); 0 unresolved; 50/50 re-derived |
| 5B-2 | Site skeleton: Next.js SSG + DuckDB-WASM + PDF.js citation panel + receipts mode + two-tier search + SEO | verify-phase5b2 | ✅ merged | 556 SSG pages (326 program/200 company/20 agency); 7 gates PASS; search 24/24 incl. typos; LHCI ≥90; a11y 0 serious; visual gate r2 medians 5/5/5/5 (r1 FAILED on doubled uncited-flag + mobile nav — agent-visual judging caught what no mechanical gate saw); 8,834 amount spans full-corpus verified cited/chipped/flagged |
| 5B-3 | Features + enrichment: anomaly feed, district lens, follow-the-dollar, share cards, top-50 dossiers + animations; USAspending/state/derived citation tiers | verify-phase5b3 + dossier_gate | ✅ merged (dossier batch pending API key) | 4,923 pages (feed 290 cards/4 types; 106 district; 4,258 filing w/ noindex policy; 554 OG cards); 7+ citation kinds, uncited_datasets 11→4 (dim_geography, dim_lobbyists, fct_budget_to_awards, jbook_narratives); 12 npm gates PASS; visual r3 5/5/5/5; 692 pytest/192 vitest. Dossier LLM batch BLOCKED on ANTHROPIC_API_KEY (cost-capped ≤$50; `govbudget dossiers submit` when exported) *(resolved, noted 2026-09-25: the batch ran 2026-07-02 — 50/50 dossiers, 973/974 claims warehouse-cited, `d1581362`; 40 dossiers were authored by subagents on 2026-07-05 for the programs the service J-book ingestion moved into the top-50, `f32a74b8` (the 10 stable programs kept theirs), and the set changed again through small paid runs on 2026-08-11 (`031d61ce`), 2026-08-21 (`ff846674`), 2026-08-31 (`24a06f8b`) and 2026-09-12 (`cc399d74`, 3010-SCN); `uncited_datasets` is `[]` in the 2026-09-25 export, so all four datasets named here now carry a citation kind)* |
| 5B-4 | verify-phase5 assembly: NL eval ≥90%, citation resolution 100%, search eval, full regression | verify-phase5 | ✅ COMPLETE | Analyst agent (sandboxed text-to-SQL: enable_external_access=false, cached schema card, 8-turn tool loop); eval set drift-corrected (freshness gate); verify-phase5 exits 0; live eval 45/45 accuracy + 40/40 citation resolution (100%) — run artifact data/research/eval-runs/eval-20260702T085924Z.json (2026-07-02); verify-phase1..5b3 + phase5 assembly all PASS; site live at https://govbudget.vercel.app; launch tooling (R2 upload/CORS/config-rewrite + LAUNCH.md); 830 pytest/192 vitest |
| 5C | UX trust journey: linkgraph integrity, coverage notes, degraded-mode, receipt moment, 5 persona journeys, answer-fold, motion | 7 npm gates (G1–G7) | ✅ COMPLETE 2026-07-02 | 7 new gates all green; every gate has recorded proof-can-fail; 19/19 total npm gates; visual judges round-2 medians D1–D4:4 V1:5 V2:5 V3:4(after fix) V4:5 V5:4; final opus review SHIP; deployed https://govbudget.vercel.app; live computer-use verification of all 5 persona journeys PASS (PDF panel/downloads verified in degraded mode pending R2); data bug: 146/1,982 PEs had doubled trajectory rows — fixed (detail-only pivot + exporter derived-input join mirror); 4,446 trajectory citations re-verified; 136 dead-link feed events resolved from fct_budget_lines detail *(the degraded-mode caveat is resolved, noted 2026-09-25: R2 went live at `assets.fiscalreceipts.com` on 2026-07-02 — see Remaining launch items — and `scripts/launch/deploy.sh`, since `712485dc` (2026-08-06), syncs R2 before its Vercel deploy unless run with `--skip-r2`, its pages-only mode)* |
| 5D | Years matrix (/years/): 462 programs × FY columns, project sub-rows, cited cells via sharded lazy citations; derived breakdown tables (show-your-work, 1,068 sidecars) | G8 yearsmatrix gate (20th) | ✅ COMPLETE 2026-07-02 | judges r1 8/9 → M2 fix (sticky sum row, legend, decimal rule) → M2 re-score 5/5/5; 20/20 gates; 1,007 pytest / 271 vitest; live at fiscalreceipts.com/years/ |
| 5F | Program-page normalization: pages for all 1,995 PEs (rollup + full tiers), narrative paragraph provenance, deterministic prose amount cites, universal PE linking, 12-section skeleton | program-skeleton gate (21st) + linkgraph leg f + render-static prose-cite leg | ✅ COMPLETE 2026-07-03 | 1,995 program pages both tiers; narrative provenance 2,449/2,457 = 99.7% (8 unresolved keep the non-paged card — never a fake location); 27 deterministic prose cites; universal PE linking (196 unlinked tokens pre-fix → 0); 12-section skeleton gate; visual judges 4.5/5/4.5 PASS; 21/21 gates; 1,039 pytest / 303 vitest; live at fiscalreceipts.com |
| 5H | Experimental flowdown (/flow/): two-river sankey (budget intent vs contract obligations), honest 98.7% not-yet-crosswalked bridge band, FPDS competition overlay (FY2017–FY2026 selector), 1,965 minted flow derived facts, exporter-precomputed collision-free labels | G9 flowdown gate (22nd, legs a–e) + fct_flow_edges dbt conservation tests | ✅ COMPLETE 2026-07-03 | judges r1 PASS/PASS/PASS (F1 two-river honesty unanimous 5s) with F3 craftsmanship=3 on label collisions → fix round (exporter collision-free-by-construction labels + TDD bbox test, hue-split competition classes, value halos) → F3 re-score 5/4/5; G9 recomputes 55 budget + 40 spend nodes from the lake, bridge exact, 58/58 citations; 22/22 gates; 1,059 pytest / 335 vitest; live-verified node→panel (121.8B Navy derived formula + 532-input breakdown) and FY2025→FY2020 switch; live at fiscalreceipts.com/flow/ |
| 5E | Decade backfill PB2017–PB2026: 10 J-book editions (371 books, 159,503 budget lines, 38,422 detail facts, amounts provenance for every edition, 185 manifest-recorded exclusions, era procurement re-keyed {account}-{org}-L{line} with disjointness guard); fct_decade_series 59,068 + fct_book_diff 18,379 (exhaustively lake-recomputed); /years/ 12 edition-tagged columns; decade sparklines on 1,994 program pages; 15 request-vs-actuals feed cards | verify-phase5e CLI (23rd gate, 4 legs, pre-failure recorded) + G8 legs f/g + edition-integrity | ✅ COMPLETE 2026-07-03 (one open confirmation, below) | Adversarial review rounds caught + fixed: edition-merging dbt fence (291 programs would have shipped wrong FY2024 actuals), PB2023 OSD/CBDP books wrongly excluded (sole detail carriers for 112 PEs), era pe_bli collisions with modern BLI codes, 27.8k-orphan citation-export hazard, P-1R subset rule (993 withheld grains published incl. C-130J $1.78B); visual judges first-round PASS medians E1:4 E2:5 E3:5 E4:5 E5:5 + 4 polish fixes shipped; 22/22 npm gates; 1,196 pytest / 352 vitest; eval 48/48 accuracy + 43/43 citations achieved (artifact eval-20260703T190641Z); ✅ CONFIRMED 2026-07-05 (cap raised): verify-phase5 exits 0 — eval 48/48 + 43/43 citations, freshness PASS, assembly PASS (artifact eval-20260706T014127Z); robustness fixes held on a fresh live run (see backlog #22) |
| 5G | Service J-books — Navy FY2026 (Army/AF manual path): Playwright download adapter past the secnav.navy.mil bot-WAF, classifier allowlist for appropriation-code naming (RDTEN/APN/OPN/…), per-family BA-split dedup, account-scoped Gate B, thousands-form provenance; 5,810 Navy detail facts + 2,066 narratives; 351 Navy PEs flipped rollup→full (full-tier universe 462→813; 387/593 Navy display PE-BLIs now carry book detail) | verify-phase5e gate a (superseded-terminal fix) + program-skeleton universe recount + render-static unresolved→state-B | ✅ COMPLETE 2026-07-04 (Navy live-verified; Army + AF on manual drop-dir path — *superseded 2026-07-05: the Army and Air Force/Space Force FY2026 books were ingested through the Internet Archive route instead, row 5G-archive; noted 2026-09-25*) | Probe-first: Playwright reached the live secnav SharePoint listing (spike URL dead); sample RDTE book confirmed Scenario-A embedded jb-2009 XML (252 PEs). Live-data fixes no fixture caught: per-family BA-split dedup (each PDF embeds the full master → 12× procurement over-load), account-scoped Gate B (Navy P-1 line numbers unique only within an appropriation → 204 false failures), thousands-form provenance. 11 duplicate doc rows non-destructively superseded (status flip, reversible — not DELETE); silent_unreconciled=0; verify-phase1/5b1/5e + 22 npm gates PASS; 1,244 pytest (1 pre-existing dossier-CSV failure, API-capped) / 363 vitest. Live-verified flagship 0601153N "Defense Research Sciences": full-tier, 108 R-2 narratives, cited amounts open derived-formula + breakdown panels, and the 40MB Navy RDTE PDF renders in the citation panel after the R2 sync. **R2 asset drift caught + fixed:** the deploy drill rebuilds site/out + Vercel but never re-synced data/site/pdfs → R2, so since the 2026-07-02 launch the 5E decade + Navy PDF citations silently degraded to "open official source" in production; re-ran upload_r2.sh (190 files / 1.48 GiB) → all PDF citations now full-fidelity. Army: asafm.army.mil Akamai blocks even a realistic headless Chromium (spike's "Playwright bypasses Akamai" premise disproven) → manual path, no stealth transport built. |
| 5G-archive | Service J-books — Army + Air Force + Space Force FY2026 via the Internet Archive: asafm.army.mil (Akamai-403 to server clients, per the 5G probe) and saffm.hq.af.mil (CAC) both mirror their PUBLIC books WAF-free on Wayback — a legitimate public archive of public records. New `archive_fetch.py` (CDX enumeration + `id_` raw-bytes download, all robustness-guarded), ARMY_NAMES/AF_NAMES classifier allowlists (org A / F; Space Force → org F via embedded ServiceAgencyName="Air Force" + SF-suffix PEs), empirical master-identity dedup (`dedup_service_master_dups`), per-document xml dir. **Army 507/513 + AF·SF 519/538 page-less PE/BLIs now carry book detail** (11k detail rows across 17 live books, 14 deduped); 1203154SF verified. source_url = ORIGINAL gov URL (Wayback is transport, not cited). | archive_fetch unit suite (MockTransport, no live net) + registry Army/AF/SF classifier + full-inventory partition + byte-identity regression + master-dedup (Postgres) + CLI archive-dispatch | ✅ COMPLETE 2026-07-05 | Provenance-first: `--source archive` enumerates via CDX → downloads through the Wayback raw-bytes endpoint → existing extract/load/reconcile unchanged. Six transport findings no fixture caught, each a committed fix + test: (1) shared xml/ dir clobbered masters across the many-books-per-org-folder layout → per-doc `{stem}__xml/`; (2) Wayback availability API flaky (returns {} for archived URLs) → CDX authoritative; (3) HTML-interstitial snapshots → `%PDF` magic guard; (4) 5 MB-boundary truncation → `is_complete_pdf` (%%EOF) on download AND resume; (5) variant-only archival (AF RDTE Vol I only under `?ver=`) → `variant_snapshots` fallback; (6) transient 504s → failed/missing reset to registered on re-run. Dedup finding: the Navy filename BA-split heuristic does NOT generalize (Army RDTE is genuinely per-volume distinct; AF RDTE Vol I-IV share one master) → empirical master-sha grouping. silent_unreconciled=0; verify-phase1/5e/5b1 PASS (PB2026 discovered=81 terminal=81); 1275 pytest (1 pre-existing dossier-CSV failure, API-capped). Evidence + full findings: docs/superpowers/reviews/5g-archive/. NOT done here (separate rounds): exporter/site ripple (tier flips, /methodology/ wording), deploy + R2 re-sync, judge pack. *(Noted 2026-09-25: the ripple, the deploy and the R2 re-sync shipped in 5G-archive-site on 2026-07-05; the judge pack was never produced — backlog #91, open.)* |
| 5G-archive-site | Exporter + site ripple for the Army/AF/SF archive round: surface the ingested Army (org A) + Air Force / Space Force (org F) FY2026 J-book detail on the site. dbt rebuild grew dim_programs to 1,739; export-site flipped the service PEs rollup→full (full-tier universe 813→**1,741**; rollup 1,182→**252**; total page universe 1,993). Full-tier by org now F=519, A=508, N=387. Coverage honesty: `isIngestedServiceOrg` extended N→{A,N,F} (Space Force folds under 'F' — 'SF' is a PE-number suffix, never an org); rollup service-books note + `/program/[peBli]` justification empty-state + methodology coverage section all say the service books ARE ingested (this line just has no matching R-2/P-40 narrative) instead of the false "not yet ingested"; methodology names Navy+Army+AF+Space Force ingested via official + Internet Archive sources with the near-zero classified/no-R-2 residual. | 22/22 npm gates (program-skeleton universe recount + ingested-wording accept; yearsmatrix budget 2MB→4MB; render-static Cite contract on new pages) + isIngestedServiceOrg tests + search-eval | ✅ COMPLETE 2026-07-05 (live-verified) | Movers, each a sanctioned fix not a weakening: (1) **yearsmatrix budget 2MB→4MB** — matrix grew 813→1,741 programs (~3.0MB) at the SAME ~1.6KB/program density; raised the exporter constant, the G20 gate, AND the pytest budget test (now pinned to the exporter constant so they never drift). (2) **2 mis-parsed pe_blis dropped** — Army R-1/P-1 lines that mis-parsed the appropriation label ("RDT&E", "O&M") into the pe_bli slot; the '&' breaks Next.js static routing → the pages 404'd (0 data-sections, caught by G21). Added a route-safety filter in the exporter (`_is_route_safe_pe`) so these garbage PEs never generate broken pages; real programs with "RDT&E" in their *title* are untouched. (3) **search near-exact company boost bug** — the 3-char-stub heuristic wrongly boosted "GENERAL ATOMICS" over "GENERAL DYNAMICS CORP" for query "general dynamics"; tightened to a real head-prefix overlap (typo cases darppa/lockeed/boeng still pass). (4) **search-eval corpus drift** — every military department now carries its own full-tier "Defense Research Sciences" PE (5-way title tie), so the DARPA-specific case was disambiguated to "defense research sciences darpa"; G5 back to 29/32 (91%). Eval count re-baseline: `evals check` → 43 ok / 0 stale / 5 skipped — no count-pin drifted (the new jbook_details rows touch no pinned SQL; live-eval confirm stays on backlog #22, API-capped — *#22's confirm landed 2026-07-05, row 5E: verify-phase5 exit 0, eval 48/48 + 43/43; noted 2026-09-25*). **R2 re-synced** (backlog #27 lesson): the 17 new Army/AF/SF PDF binaries pushed to R2 (`upload_r2.sh --live`), else citations degrade to "open official source"; SF book 40f1f67d…pdf + an Army (asafm) + an AF (saffm) book all return HTTP 200 from assets.fiscalreceipts.com. Live-verified **1203154SF "Long Range Kill Chains"** (the user's ask, #1 by FY2026 request at $7.7B): now FULL-TIER with 12 canonical sections, the real GMTI mission narrative, R-2 detail table, and working PDF citations to the Space Force RDT&E book (pages 647/649/654) — and one Army full-tier (0603462A NGCV, 114 narratives) + rollup coverage wording confirmed. Deploy `vercel --prod --archive=tgz` (6,732 pages, 2 fewer than pre-fix) aliased to fiscalreceipts.com; 1,275 pytest (1 pre-existing dossier-CSV failure, API-capped) / 363 vitest / tsc clean / eslint 0 errors. Evidence: docs/superpowers/reviews/5g-archive/live-*.png. |
| 5G-dossiers | Regenerate top-50 dossiers for the service-J-book-shifted top-50 (40/50 changed after the Navy + Army/AF/SF ingestion — the current #1 is 1203154SF "Long Range Kill Chains" at $7.7B, and the old defense-wide top-50 that had dossiers dropped out). Recompute live `research.top50`; rewrite `data-seeds/program_categories.csv` to the live set (40 new rows: 6 space, 3 shipbuilding, 31 default; each with a resolvable narrative `source_ref`) → fixes `test_covers_live_top50_exactly`. Author 40 new dossiers in the exact production schema (sections→claims, every claim a real resolvable `fact_id`) via **Claude Code subagents** (not the cost-capped Batch API) — the cited-or-absent gate makes subagent-authored dossiers as honest as pipeline-authored. Committed raw source in `data/research/dossiers-raw/{pe}.json` (honest provenance marker, no faked API batch metadata) so `dossiers collect` reproduces them; the `dossiers submit` CLI remains for future API runs. | `dossiers gate` + `verify-phase5b3` + full pytest | ✅ COMPLETE 2026-07-05 (live-verified) | Dossier gate PASS: 50/50 present, **0 unresolvable citations, 733/733 claims warehouse-cited (100%, floor 80%)**, categories 50/50. **`test_covers_live_top50_exactly` now PASSES** (the one pre-existing API-capped failure noted in 5G rows — now cleared); `test_seed_emits_verbatim` re-pinned to the shifted top-50 (space/cyber/shipbuilding, no hypersonics in the current top-50). Full suite **1,282 pytest / 0 failures**. Faithfulness handled per program: classified lines (0603525N PILOT FISH, 846510 SAP) state "classified per E.O. 13526" and cite only money facts — the "absent" half of cited-or-absent, no fabricated mission; discretionary vs. reconciliation (mandatory) splits cited to distinct budget-line fact_ids; only contractors named IN the J-book narrative asserted (Lockheed for F-35 C2D2, Dynetics for IFPC) — no invented bidders; percent-changes cited only where a feed `figure_fact_id` backs them. 22/22 npm gates PASS (gate-12 animation now 50/50 `data-hero-category` after the fresh build baked the new categories). Deploy `vercel --prod --archive=tgz` aliased to fiscalreceipts.com; **R2 re-synced** (`upload_r2.sh --live` — citations/ 2.85 MiB + data/ 5.4 MiB refreshed so dossier fact_ids resolve). Live-verified 1203154SF (What-it-is/Why-it-matters/Key-players + Golden Dome + $7,696,916, fact_id `7d4bd900234f652c` resolves via same-origin cite-shard HTTP 200), 0603525N (classified framing), 1000 (ship maintenance). |
| 5I-lineage | Program lineage — evidence-tiered YoY money-flow tracking across PE/BLI identity changes (transfer / split / merge / BA-maturation / rename), so a user can follow one funded activity across all the identities it wore over time. Two honesty tiers: **Stated** (regex over FY2026 R-2/P-40 `detail_narratives`, each edge cited to its source sentence + page + `fact_id_narrative`) and **Inferred** (deterministic RDT&E same-agency BA-maturation with a funding taper — never cited, dashed amber "candidate (unverified)", opt-in, never summed). New Postgres `program_lineage` (008) + `program_family` (009) tables + parquet exports; stated-only union-find families with a 1:1-chain helper (stops at split/merge/cycle/partial). Site: per-program lineage rail + reconstructed **family funding line** (sums ONLY the clean 1:1 chain; honest branch note on splits; "(unresolved)" for a cited page-less successor) at `data-section="lineage"`; threaded `/years/` family-thread badge. | **verify-lineage** CLI (24th gate; legs: stated-cite re-derive, id-agnostic family-integrity recompute, one-to-one-sum honesty — proof-can-fail recorded, later hardened) + **render-static inferred-honesty leg** (every `[data-inferred]` must carry a "candidate/unverified" label) | ✅ COMPLETE 2026-07-07 (live-verified) | **Extraction-probe reality (the honest headline): the tiers are small-but-bulletproof, not the "bulk coverage" the spec optimistically framed.** Regex-over-narratives is high-precision/low-recall: **25 stated** (FY2026-fenced) + **3 inferred** = 28 edges, 19 families, 44 PEs, 48 lineage sidecars. Coverage expansion (LLM extraction over the ~1,950 prose transfers, lineage Sankey, multi-edition citations) is deliberately Phase 2. Adversarial rounds caught + fixed live-data defects no fixture saw: (1) **inferred=0 was a plan bug** — the series query filtered a single edition (`edition_year=2026`), collapsing the request trajectory to one FY so no taper could compute; fixed to the cross-edition request series, then `_ba_digit` tightened to RDT&E-only (`06\d(\d)`) + a same-agency-suffix guard — **14 noisy cross-appropriation/cross-service edges → 3 textbook maturations** (0601384BP→0602384BP, 0603654N→0604654N, 0604294D8Z→0605294D8Z, each same serial+agency, one BA rung, a real taper). (2) **Citation resolvability** — 28 of 53 stated edges cited pre-2026 narratives NOT in the site's binding PB2026 cite-shard fence → their `<Cite>` would not resolve; **fenced stated extraction to FY2026 narratives** so all 25 resolve (FY2026 books still narrate historical predecessors, e.g. "previously funded in PE 0206625M in FY2023"). (3) **verify-lineage leg-c dangling-terminal carve-out** — an adversarial reviewer cloned the warehouse and laundered an *uncited* garbage terminal (`deadbeefdeadbeef`) through; hardened so the carve-out is **locally citation-gated** (the dangling terminal's incoming edge must itself pass leg-a) and the NOTE neutralized (no "not-yet-ingested" claim — spec §5.4). (4) Graph helper hardened: **cycle guard** (reciprocal cross-FY stated edges would hang the exporter) + **partial-transfer exclusion** (a `portion_amount` edge must not extend the 1:1 line — spec §5.3). Honesty invariants verified on the live export: 48/48 stated rail entries cite a resolving fact_id (0 dead-cites vs the 134,215-fact universe), 6/6 inferred entries `evidence:null`, 2 dangling refs `resolved:false`, all 19 families' funding lines equal a chain-only recompute exactly. Visual judges median **4/4/4** ("stated-vs-inferred separation exemplary; a casual user cannot mistake a candidate for a fact") → 1 fix round: **directional-honesty bug** (successor cards wrongly read "realigned from" → made direction-aware "realigned to"), `/years/` family-glyph legend, clickable "cited" affordance, funding-chain head title. **22/22 npm gates + verify-lineage (25/25 · 44/44 · 19/19, exit 0) + 1,326 pytest / 391 vitest / tsc clean.** Deploy `vercel --prod --archive=tgz` (359.7MB tarball, 88,526 files) aliased to fiscalreceipts.com; R2 re-synced (11 objects, 0 new PDFs). Live-verified in prod: `/program/0604818A/` renders the rail + a stated cite (`b3123c07e825d2d8` resolves via cite-shard to the Army RDT&E PDF), `/program/0605294D8Z/` shows the dashed `data-inferred` "candidate (unverified)", `/program/0604270F/` shows the "realigned to" direction fix, `/years/` carries `family_id`. Spec `docs/superpowers/specs/2026-07-06-program-lineage-design.md`; plan `docs/superpowers/plans/2026-07-06-program-lineage.md`; pre-failure evidence in `5c-gates-pre-failure.txt`. |
| 5I-review | Final whole-implementation review + live browser test of 5I (user-requested): 35-agent multi-dimension review (find → adversarial verify; 30 findings → 19 confirmed / 11 refuted) + hands-on prod walkthrough of every core journey. **Two CRITICALs the per-task reviews could not see, both live: (1) funding line displayed a multi-member SUM citing a single member's fact — 74/148 shipped points contradicted their citation (worst: $349M cited to a $0 fact); (2) extractor fabricated an endpoint when a sentence named both — 3/25 stated edges asserted a wrong predecessor (rollup-line narratives 837300/834190 aggregate statements about OTHER PEs).** Fix rounds: both-named-endpoint extraction (cross-pairs named PEs, never `this`; subject-position rule, lookahead/lookbehind-guarded) + per-member cited funding points (one entry per (fy, member), v == its fact, NO uncited sums; coexistence FYs render each member labeled). Gate teeth added, each proof-can-fail on the REAL pre-fix warehouse: leg (a) endpoint-contradiction (the 3 bad edges failed verbatim), leg (d) funding-point value==fact vs the built artifact (148 shipped mismatches failed), leg (e) lake↔DB binding (missing parquet = FAIL), FY2026 fence constant shared producer↔gate, cite-degrade print→hard error, render-static stated-side leg (bare stated card = FAIL) + inferred zero-count honesty; verify-lineage wired into the verify-phase5 assembly (8/8 incl. a fresh live eval 48/48 + 43/43). | verify-lineage (5 legs) + assembly + 22 npm gates | ✅ COMPLETE 2026-07-28 (live-verified) | **Re-extraction under the corrected rule GREW the gold tier: 25 → 31 stated (the old self-ref drop was silently discarding 6 real edges, incl. a 5-source fan-in into 0303005F), 22 families; merge fan-ins now flag the branch note (in-degree>1); dangling ORIGIN carve-out mirrors the terminal one (citation-gated).** UX fixes from live testing: evidence sentence now rendered (collapsed "show sentence" blockquote, `data-source-text="lineage-evidence"` — closes the "cited click never shows the sentence" gap), FY chip reads "per FY2026 J-book" (edition, not transfer year), search "Companys"→proper plurals, deep-content hits titled by program name (was raw URL path) + "Chainssource" join spacing, answer strip "run by A."→"run by Army" via serviceOrgName. 1,357 pytest / 410 vitest / tsc clean / 22/22 gates / verify-lineage a 31/31 · b 53/53 · c 22 · d 528 pts 0 fail · e 34/34. Deployed (`vercel --prod --archive=tgz`, aliased fiscalreceipts.com) + R2 re-synced (13 objects); live-verified 7/7: repaired 0207436F→0303004F sentence in prod, per-member FY blocks with per-fact cites, sentence blockquotes, branch note, copy fixes, shard resolution. Findings that remain by design: 4 dangling origins + 1 dangling terminal (cited, `resolved:false`); meta descriptions still use raw org codes (cosmetic, non-prose) *(re-checked 2026-09-25 on the chain-C build: a military service is now spelled out through `serviceOrgName()` — `/program/0601102A/` reads "Army" — while other organizations still print as codes, e.g. `/program/0603115DHA/` reads "DHA")*. Commits b81d4b7/59b417b (criticals+legs), 91a473b/d96a4a8/cadba85 (importants+UX). |
| PM-S1 | PM-review Sprint 1 — trust (spec `2026-07-30-pm-review.md` P0-1..P0-5, P1-1, §Systemic Fix): kill the basis-collision defect class. **Gate 23 "basis" built failing-first** (proof-can-fail: 76,106 attribute-less figures, the F-35 $5.25B/$5.57B collision, 26 summary/detail contradictions + 1,497 false absences, missing footnote fields) — then made green: (1) **dim_programs dual-volume dedup** (47 Army PEs summed at 2× across BA-volume PDF pairs — a defect class the PM review itself missed, caught by the new gate; 0601102A 644.682→322.341, dbt pin + fixture teeth); (2) **basis threading** on all 80,253 program-page figures (`basis/fy/measure/entity/edition` + always-visible ≥12px chips: `P-1 TOA · PB2026` / `P-40 detail · PB2026`), 730 latent same-label collisions resolved honestly in payload attribution; (3) **summary cards from the toa-preferred union** (F-35 FY24 card now $5.57B TOA; FY25 false absence → $4.97B enacted; absence-reason enum `not-published`/`no-comparison`/`no-rollup`, zero bare dashes) + **reconciliation strips** (one mechanism sentence + per-year arithmetic `$5.57B − $5.25B = $318.6M`, delta unlabeled — the bridge row isn't a parsed fact); (4) **unified footnote formatter** (program, FY, row name, value+unit, document title, locator, SHA-256, retrieved, fact permalink; Chicago/AP/BibTeX/JSON; goldens = gate 23 leg c); (5) **fact addressability**: `/fact/{id}` via out/vercel.json edge rewrite → client resolver over the permanent cite-shards (semantic header from the program sidecar, canonical-origin permalinks, 2 real fid8 collision pairs disambiguated), `#fact-{id}` scroll+highlight+open-drawer anchors, ONE public id (the chip/drawer mismatch was two truncations of one 16-hex id — now both `fid[:8]`), `pe_bli` added to shard payloads; (6) **P1-1**: citation underline 1.26:1 → **4.95:1** (hover 7.78:1, gate 6 teeth reproduce the PM's exact 1.26/1.23 measurements in the pre-failure record), 24 provenance elements 10px→12px, **Receipts default ON** (relabeled "Fact IDs", persisted, no-flash hydration); (7) hero/OG/feed on canonical TOA + scope qualifier. | gate 23 (3 legs) + gate 6 contrast/size legs + gate 1 fact-route leg + footnote goldens | ✅ COMPLETE 2026-07-31 (live-verified) | Visual judges **4/4/4** (definitional clarity unanimous) → 1 fix round (strip boilerplate→arithmetic table, resolver semantic labels, canonical permalink origin, 5 minors). Full loop: 1,375 pytest / 563 vitest / tsc clean / **23/23 gates** / verify-lineage exit 0 / verify-phase5 assembly PASS incl. live eval 48/48. Deployed (`vercel --prod --archive=tgz`, READY, aliased) + R2 re-synced (12 objects). **Live PM-appendix repros 7/7 PASS**: ATA000 card=$5.57B + strip + no false absence; `/fact/bb54b165` → 200 via edge rewrite; hero qualifier live; `#2b6dd3` decoration + "Fact IDs" toggle shipped; 0601102A halved to $322.3M. Commits ac7b7e9→02b8bd2 (9). Sprint 2 (P1-2..11) + Sprint 3 (RSS, P2s, coverage page) queued per the PM's sequencing; deferred judge nits (footnote preview, chart color semantics) + raw-org badge sweep + stale /data/ Explorer parquets (P1-5) folded into Sprint 2. *(Noted 2026-09-25: the footnote preview and the org-badge sweep shipped in `ae5d5d24` (2026-08-04) and P1-5 in PM-S2; "chart color semantics" appears in no later commit, sprint row, plan or spec — folded into Sprint 2 on paper and dropped.)* |
| PM-S2 | PM-review Sprint 2 — usability & credibility (spec `2026-07-30-pm-review.md` §P1-2..§P1-11). **P1-4 search:** alphanumeric normalization (F35→F-35, B21, KC46), magnitude-blended ranking (Sentinel→GBSD above Sentinel Mods), a corpus-verified alias table with "also known as" chips, readable filing titles ("LOCKHEED MARTIN — PENN AVENUE PARTNERS, 2024 Q1") — **search-eval 29/32 (91%) → 36/37 (97%)**. **P1-5 data truth:** `/data/`'s row counts were hardcoded literals frozen at 5B-2 values (8 of 15 wrong — dim_programs claimed 326 against a 1,739-row parquet, jbook_details 4,421 against 21,028) while the parquets themselves were always correct — the page lied about its own data, not the data about itself; now every count + row-grain scope comes from an exporter-emitted manifest, plus one canonical corpus statement on the four pages that disagreed. **Found in passing: `budget_lines_decade` (32,642 rows) was not merely undocumented but UNQUERYABLE** — missing from the Explorer's registry, a whole shipped dataset invisible. Same defect class then closed on `/methodology/` §3 (197 test functions/42 modules/21 dbt assertions/45 eval pairs/≥41 — every literal rotted; real: 87 dbt, 24 gates, 48, 44 — now derived from dbt's compiled manifest, the verify.mjs registry, the eval set and the gate's own threshold constant; pytest/vitest totals deliberately REMOVED rather than re-hardcoded, since neither derives honestly at export). **P1-6/P1-7:** currency ladder through T (`$3657.4B` → `$3.66T`), data-derived FY ranges replacing three inconsistent statements, deterministic sorts on every table (filings 2024/2026/2025 → 2026/2025/2024). **P1-9 workbook drawer** (the weakest citation tier): `5,565,655 USD thousands (= $5.57B)`, a per-cell arithmetic line, and a build-time cell preview with context rows — cell data measured at +25.7% on cite-shards if inlined, so routed to lazy per-fact sidecars (22.1 MB, fetched on open). **P1-2/P1-3/P1-10/P1-11:** dossier-hoisted WHAT-IT-IS cards with their fact chips (field-generated fallback for non-dossier programs), the Raytheon/RTX split merged into **one RTX family at #3, $68.9B** (was #4 + #6) behind a hand-curated, source-audited events table on its own page, GAO department-level qualifier, `/programs/` filter + Org sort + CSV. | gate 24 "datatruth" legs a–g (dataset cards, rendered row counts, Explorer picker, corpus statement, /methodology/ build-checks, declared table sorts, curated-family merge) + gate 4 test 3 rebuilt (workbook drawer contract, 35,940 citations) + gate 21 leg f (dossier cards) | ✅ COMPLETE 2026-08-04 (live-verified) | **Visual judging FAILED first at 3/3/3, passed on re-judge at 4/4/4** — the fix round is the substance of this row. Round-1 majors, all real: mobile clipped the payload of three separate fixes (`/companies/` money column, `/data/` scope prose, the search alias chip truncating "Ground Bas…"), the alias table shipped to ⌘K **only** so `/programs/` returned the exact wrong "Sentinel" answer the sprint set out to kill, the deepest citation tier dropped the basis label Sprint 1 added everywhere else, and a merged $68.9B total showed no addends in the same sprint that added "how the cells combine" arithmetic. **Worst: two factual errors in our own curated data** — Exelis labeled "acquired 2019" (Harris acquired it May 2015; 2019 was the L3Harris merger) and Rockwell Collins "renamed 2023" (it entered by acquisition, UTC 2018). The source audit that followed re-opened all 17 rows against their filings and found the Exelis row's **source URL never supported the date it was cited for** (a pre-close shareholder-approval 8-K, replaced with the Item 2.01 completion filing), reclassified 3 events to the wrong `kind`, dropped 3 dollar figures the sources never stated, and caught a curator hazard where `normalize_name("United Technologies Corporation")` would have merged an unrelated $1.5M family into RTX. Schema gained `evidence`/`source_form`/`source_date`/`source_verified`; 2 rows are labelled name-inferred **on the row**; events are now annotated **per former name** (EXELIS acquired 2015 · ROCKWELL COLLINS acquired by UTC 2018 · RAYTHEON COMPANY merged 2020), each deep-linking to its `/families/` row. A re-judge independently spot-checked six curated dates and found **every one correct**. Final polish also fixed a regression the fix round itself introduced (arithmetic line and preview table disagreed on sign convention — now `+ O840 (−246,702)` substitutable straight from the row) and `/families/` at 390px (98px overflow with the **Source column entirely off-screen**, on the page whose whole argument is sourcing). 1,477 pytest / 748 vitest / tsc clean / **24/24 gates**. | 
| PM-S3 | PM-review Sprint 3 — reach & self-description (spec `2026-07-30-pm-review.md` §P1-8, §P2-1..§P2-8, §Coverage). Eight tasks: a **390×844 mobile gate leg** built first (backlog #31 — Sprint 2 passed 24/24 and then failed judging on mobile clipping no gate exercised); **withdrawal of 87 false "zeroed out in FY2026" feed claims** (absence in an edition is not a zero — and the investigation surfaced backlog #32, a PB2026 taxonomy renumber the corpus cannot express); **RSS/Atom + 123 program and 55 company watch feeds** with a dollar magnitude on every card and a per-item linkage basis; **§P2-1 page weight** — `/programs/` 5,875,345 → 2,733,056 bytes (−53.5%; the spec blamed `/years/`, which measured as a 28 KB shell) — plus **§P2-2 `/years/` opens on money** and a mobile column-chip disclosure; **§P2-3/§P2-6 chart a11y** — accessible names, computed descriptions, "View as table" on 5 charts, a Sankey paint-order fix (gate 22 leg f), and a scope-vs-caution note vocabulary; **§P2-4/5/7/8 display** — company title-casing, distinct `0`/`<0.05`/`—` cell states, reproducible derivation strips, count notation; a **rebuilt `entity_xwalk`** correcting a ~73% understatement on 201 pages; and a new **build-derived `/coverage/`** page (12 rows, every figure recomputed at build time, 8 dated targets and 4 reasoned refusals) plus a **`/flow/` two-rivers reframe**. | gate 3 mobile leg (m1/m2, then **m3** added in the fix round) + gate 6 chart legs + gate 22 leg f + gate 24 leg h | ✅ **COMPLETE** 2026-08-05 (third panel 4/4/4 at both widths; live) — *Status corrected 2026-08-24. This cell read "GATES COMPLETE, VISUAL BAR NOT MET … NOT deployed" until then, contradicting this same file ~1,215 lines below, where the third judging panel is recorded at **390 → 4/4/4, 1440 → 4/4/4, unanimously and without a split** (commit `b87acbf`, "third judging panel clears the bar — 4/4/4 at both widths", 2026-08-05). The first two panels genuinely DID fail (2/2/2, then 3/3/3) and that history stays in the evidence section below — it is the substance of this row. The deploy claim is stale by construction: live HEAD is `c984d9c`, which contains `b87acbf`. What the panels left OPEN (#42 layout spine, #43 Fact-ID chip weight, Sankey labelling) remains open and is tracked there, not here.* *Re-checked 2026-09-25: #42 layout spine — closed 2026-09-01 (`f02deb0c`, with `db065c0c` and `29ab46be`; the `<dd>` and marker-less-list residue `dd86f8e7`, 2026-09-11); #43 — closed 2026-08-27 in its entry; Sankey labelling — every label plated and its value set against the node face, gate 22 leg (h) (`3111eae2`, 2026-09-12; `ecff0d6c`, 2026-09-18). Of the next cell's findings left unfixed: the 1440 Sankey value labels are that same work; the `/flow/` vs `/district/` counts are one registry published on `/coverage/#crosswalk` (`a1e8dc86`, 2026-09-18); filing pages case LDA names and keep the filed string beside them (`156a8e26`, 2026-09-18); and on the 2026-09-25 build the only U+2212 minus before a figure is the "FY N−1" prose on `/methodology/`. The 390 scroll-edge clipping was not re-measured here.* | **Visual judging FAILED twice: round 1 unanimous 2/2/2 at 390 and 3/3/3 at 1440; round 2, after the fix round, unanimous 3/3/3 at BOTH widths. Median never reached the ≥4 bar, and this row says so rather than rounding up.** Round 1's majors were all invisible to a 24/24 suite: **the home page painted the program title straight over its dollar delta** ("Test & Evaluation Science & Te**+$1.34B**ogy" — two of five figures on the front door unreadable); `/feed/` kept its desktop two-column row at 390, leaving ~110px for the headline (one or two words per line, ~1.4 cards per screen); **`/flow/`'s "View as table" — the sprint's own accessibility affordance — pushed the AMOUNT column out of its scroll box, so the fallback the chart's caption sends readers to carried no dollars at all**; and §P2-2 sorted the ROWS but not the viewport, so `/years/` still opened on FY2015A, empty for exactly the newest programs the new sort promotes, with the sorted column off-screen at both widths. **The gate work is the durable part.** (m3) — a label must not be painted over its value — was written, run against a deliberately-broken artifact, and **PASSED**, because it measured `getBoundingClientRect()` on a flex item that shrinks while its inline text overflows: the boxes never intersected, only the glyphs did. Rebuilt on painted extent (element + descendants + text line-boxes) it reproduces the shipped defect verbatim ("4/5 mover title vs change figure pair(s) collide — '0605238FGround Based Strategic Deterrent EMD' overprints '+$2.14B' by 59x20px"). The `/years/` leg was **strengthened, not relaxed**: it had pinned the LEFTMOST cell — a proxy that was passing on a column of em-dashes — and now reads the sorted key from the table's own `data-sorted-col` and measures that column (proof-can-fail: "300/300 sorted-column amount cell(s) are outside the 390px viewport — row 0: '7,696.9' left=993"). `/`, `/feed/` and `/flow/` joined the value-bearing sample; `/` had been in it but overflow-only, so the front page's sole assertion was one the defect could not trip. Round 2's majors were surfaces holding the answer in their own payload and not rendering it: **four different filings naming one PE in one quarter rendered as four identical rows** (registrant now on the row; the filing × program × matched-word grain also collapsed, Lockheed 1,296 → 1,219); **"Budget-Linked Awards" named no budget line** while `pe_bli` sat untyped in the sidecar; the chart table showed "RDT&E, Air Force" at $36.1B *and* $26.2B with no parent (now "from Air Force / Space Force" vs "from Classified Programs", 93/95 rows); the decade card claimed **"Ten fiscal years" on a five-year grid**; and `/companies/` said "total federal obligations" against a DoD-only lake. **Gate 1 then caught the fix's own cost** — naming the program on 318 award rows blew the page-weight ceiling by 172KB; the table was capped at 50 with its total stated (717,690 → 289,878 bytes) and **the ceiling was not touched**. Loop at final HEAD: 1,497 pytest / 853 vitest / tsc clean / eslint 0 errors / **24/24 gates** / verify-lineage PASS (31·53·22·528·34) / verify-phase5 assembly 8/8. **Live eval: FAILED first at citation 42/43 (q011 answered correctly through literal/echo SQL — `touched_tables` empty), PASSED on an immediate re-run at accuracy 47/48 and citation 43/43**; q011 has flaked twice before, so this is agent nondeterminism against a 100% bar, filed as backlog #36. The one persistent miss is q022 = backlog #34 (eval wording, not a regression; the gate passes on it). Findings left unfixed and why: the 390 Sankey still clips node values at the scroll edge (inherent to an 840px chart in a 356px scroller — mitigated by a swipe cue and the table view, not removed); 1440 Sankey value labels still sit on node bars and are crossed by de-obligation hairlines (chart-geometry work, not a copy fix); **`/data/` reports `dim_programs` at 1,739 against a site-wide claim of 1,741 — the parquet is right and the corpus number is two lines generous (backlog #35), which means the site currently overstates its own detail-grade coverage on the number `/coverage/` leads with**; `/flow/` "10 of 24 crosswalked PEs" vs `/district/` "17 of 1,741" unreconciled; filing pages keep their source ALL-CAPS registrant names; minus glyphs differ across pages. Commits a323b15→7734004 (7). |
| Post-launch | Refresh automation (cron), accounts/alerts tier, text-to-SQL analyst surface | per feature | backlog — refresh orchestrator shipped 2026-09-18 (#8: `govbudget refresh`, sync shrink guards, launchd templates; loading the scheduler is the owner's action); accounts/alerts tier and the public analyst surface still backlog | — |

## Evaluator framework (how each thing is judged)

Pick the cheapest modality that actually measures the goal; escalate only when the
property is not mechanically checkable. Every gate is re-runnable by an operator.

1. **Mechanical CLI gates** (deterministic, exit-code; the backbone) — data
   correctness, citation re-derivation, set/count integrity, schema locks.
   *Used by: all phases (verify-phase1..5b1). Always preferred when possible.*
2. **Tool-instrumented gates** (headless browser + audit tooling) — properties of
   the RENDERED site that are still objective: every on-screen number carries a
   resolvable citation attr (Playwright DOM walk); citation click-through opens
   PDF.js at the right page with highlight overlapping the stored bbox (Playwright
   + bbox math); search eval set (type queries, assert top-3); Lighthouse budgets
   (INP <200ms, LCP <2.5s); axe-core accessibility; schema.org validation
   (structured-data parse); sitemap/llms.txt presence.
   *Used by: 5B-2 render/clickthrough/search/perf/a11y/seo gates.*
3. **Agent-visual judgment** (screenshot → vision-model rubric, N-vote) — what
   only eyes catch: broken layout, overflow, unreadable contrast, empty-state
   quality, animation jank (screenshot series), "does this page look trustworthy".
   Rubric-scored 1–5 per dimension by 3 independent judges; median ≥4 passes; any
   judge flagging a Blocker fails the gate. Screenshots at 3 viewports
   (390/768/1440px). Non-deterministic → ADVISORY-BLOCKING: failures stop the
   loop, but the rubric + screenshots are committed for human override.
   *Used by: 5B-2 visual_gate, 5B-3 animation/dossier layout review.*
   *Not followed after 5H (noted 2026-09-25): every judged round since
   recorded its scores as ledger prose with no committed rubric + screenshot
   pack — backlog #91 and #101, both open.*
4. **Loop-until-dry evaluation** (adversarial agents against live artifacts) —
   unknown-unknowns: final whole-implementation reviews (opus, live-probing),
   plan reviews before execution, eval-set construction (48 NL Q&A pairs in
   evals/phase5_questions.yaml, 5 of them REFUSE cases — counted 2026-09-25
   with `grep -c '^- id:'`; the set held 45 when this line was written).
   *Used by: every phase's final review; 5B-4's NL eval (≥90% + REFUSE handling).*

## Findings log (what we learned; feeds future phases)

- **2026-09-25: Integration of the live branch.** Production
  (fiscalreceipts.com) was deployed on 2026-09-24 from
  `codex/f15-family-browser` (81929a6b), not from
  `roadmap-completion-2026-09-05`, so deploying the latter alone would have
  removed the live branch's site features (among them verified government PDF
  receipts and the F-15 family funding history). Both branches are merged in
  f0ed21eb on `integration-2026-09-25` (parents 6c3c07e1 and 81929a6b). Four
  rulings, made by the controller under the owner's delegation: **R-INT-1**,
  where the two branches' reviewed page-weight ceilings differ, the merged
  ceiling is the higher of the two per metric and never more, and a merged
  page over it is trimmed, never raised. `site/scripts/gates/build.mjs`
  applies it to the four pages the live branch had raised for its type
  system: /companies/ 740,000 / 73,500, /data/ 105,000 / 15,600 and
  /methodology/ 162,000 / 45,400 (the live branch's pairs), and /coverage/
  103,000 raw (the live branch's) with 20,750 gzip (this branch's); every
  other ceiling and every `measured` stamp is unchanged. **R-INT-2**,
  contractor concentration keeps #80 (the high-confidence figure or none), with
  the live branch's validator kept in front as a fail-closed guard; **R-INT-3**,
  an older GAO edition publishes only when its ratified anchor passes on the
  same page; **R-INT-4**, company labels take the live branch's wording, the
  smaller claim. A fifth, **R-INT-5**, governs this ledger: on #78, #79, #85
  and #86 the live branch's second Status line was relabelled "Status on that
  branch:", with no words deleted, so each entry keeps exactly one grep-able
  Status line (`tests/test_roadmap_backlog.py`). On #166–#169 each
  superseded "Status: OPEN — scoped 2026-09-22" marker was relabelled "Status
  (2026-09-22):" the same way. On #166–#168 the latest state sat under a
  dated "Status (2026-09-24):" label the grep cannot see, so a plain line
  restating it (PUBLISHED on #166 and #168, PARTIAL on #167, as of
  2026-09-24) was added beneath; #169 already carried its latest state
  (PARTIAL, as of its 2026-09-22 implementation update) as a second plain
  marker, which the test missed because it ended an entry at its first
  blank line; it now reads each entry to the next top-level block. A sixth, **R-INT-6** (#82), adopts
  the live branch's narrative organization rule on account-split codes: a
  narrative publishes on a member only when its document's organization is
  that member's and the document's detail rows under that organization name
  exactly that member's appropriation; a refused narrative publishes on
  neither member and is counted in the #82 census print. Measured
  2026-09-25, it refuses none of the 40 PB2026 narratives on the 10
  account-split codes. A seventh, **R-INT-7** (#175), holds gate 27 (copy),
  the live branch's voice lint, to no regression against production.
  Production's own build fails it (1,049 hits on 81929a6b's build, measured
  2026-09-25). Every integration hit that production's build also carries
  (same page, leg and text) is exempted through the gate's
  `copy-allowlist.json` (584 entries, 1,025 hits); of the 9 hits
  production's build does not carry, 7 were reworded at their source and 2
  were marked as what they are rather than reworded (a registrant's legal
  name as data on its filing page, snake_case column names as code on
  /downloads/), so the gate's existing skip rules apply. An eighth,
  **R-INT-8** (#80/#82), lets a program's WHO answer that withholds a leader
  state how many award records the same page's Related Awards table lists
  ("N linked award records are listed below.", the live branch's link) — a
  count of this page's rows, bound by gate 21 leg (j) to the page's sidecar,
  not the count of the line's links that #80 fix round 2 found goes false.
  A ninth, **R-INT-9** (#82), came out of the final integration review: on
  every member page of a shared code, lobbying mentions, the `lobbied_by`
  block and named primes are withheld exactly as production withholds them
  (the live branch's 2c7ebbb0 and c2ac0b90), and the Lobbying Mentions
  section reads "This code is shared by more than one budget line. No
  lobbying matches are assigned to this specific account or organization."
  #82's per-member narratives and details are unchanged. The #82 rule it
  supersedes sent every `pe_literal` row to every member, on the premise that
  a bare code in a filing names the line. For the numeric codes that premise
  is false: on 20, 30 and 500 every such row matched a bill or public-law
  number ("H.R. 20", "P.L. 117-30"), a date ("September 30") or part of a
  larger figure (a spectrum quantity, "2,500 megahertz"), and the merged
  build told readers on 7 member pages that companies "named this program in
  Senate lobbying filings". Gate 21 leg n check 8(b) now fails any member
  sidecar that carries a mention row, a `lobbied_by` block, a named prime or
  a `mentions_shared_code` declaration, and any member page that renders a
  mention row, the lobbying or J-book answer to "Who gets it", or anything
  but that sentence; the check it replaces passed the merged build, because
  it accepted a declared basis. The same review fix round restores
  two live-branch guards the merge had dropped: the subaward exporter again
  refuses a subaward row that does not resolve to exactly one prime award
  and one subawardee or that lacks a recipient or description, and
  verify-phase5b1 checks subaward rows as strictly as the live branch did.
  It also gives a multi-part PDF receipt's parts a deterministic order, so a
  re-export no longer changes which page its citation panel opens on.
  Production's order was an artefact of disk order: the budget-lines query
  sorted on three keys that tie for a program filed under several budget
  activities, and Postgres returned the tied rows unordered. The receipt
  that moved on /program/F015EX/ is its reconciliation chip,
  cf802c75afa0f505, not the headline receipt (4a9ae7cc, which opens on line
  7, page 123, in both builds): production's parts ran [line 44 p126, 112,
  134, 7], the integration's [7 p123, 44, 112, 134]. The new total order
  (organization, account, budget activity, then row id, after the three
  original keys) keeps the integration's order for it, so the deploy moves
  that chip's first page from 126 to 123. Across the corpus, 25 of the 348
  multi-part summed receipts open on a different first part than production
  (measured on a read-only re-export, 2026-09-25). The same check found
  `dim_entities.worst_confidence` computed as `min(confidence)` over text,
  which returns the BEST tier ('high' sorts before 'medium'): 29 families
  with a medium member read high, one published (NAN on /companies/). It is
  now the weakest member's tier, pinned by accepted_values and a singular
  dbt test (`assert_dim_entities_worst_confidence_is_worst`).
  The merged crosswalk is `roadmap-completion-2026-09-05`'s (#78, #85 and #86 carry
  dated integration lines; the live branch's ambiguous-account abort was not carried, #170, and
  neither was its detail-token scoping, #171). The live branch's backlog
  #89–#92 are renumbered #166–#169 (the note above #166). The other session
  is not running; its work is committed (81929a6b, the tip of
  `codex/f15-family-browser`) and merged here. It must not deploy from
  `codex/f15-family-browser` again: production's `git_head` is 81929a6b
  (`/.build-meta.json`, read 2026-09-25), and a deploy built from that branch
  would drop this integration's work. New work branches from `main` once
  this merge lands there. This supersedes the shared-lake note below
  (2026-09-24), which says "the other session must re-run its own `govbudget
  build` and export before it trusts its lake": that session's work now
  lives on this branch.

- **2026-09-22: Jev tested; supporting editorial pilot prioritized behind core product work.**
  Direct `jev-1.13.0` calls evaluated 155 distinct baseline cases, then repeated
  71 lineage cases with revised questions; with the connectivity probe, 227 API
  calls used 284,811 input tokens at an estimated $0.011962 inference cost.
  Median observed end-to-end latency was 0.412 seconds. Baseline agreement was
  63/63 for existing GAO identity links, 13/13 for constructed claims against
  actual F-15EX sources, 26/26 for constructed wrong/missing-evidence controls,
  and 42/53 for reviewed lineage cases. Revised questions improved lineage
  agreement to 51/53 but introduced two false positives across lineage and
  reversed-direction controls. These are regression results, not a blind
  production accuracy estimate; some initial lineage disagreements were
  rubric-sensitive, and the baseline included a wrong high-confidence answer.
  Prioritize freshness/attribution, complete flagship journeys and reviewed
  changes; scope Jev to internal review (#169). Public arbitrary-claim checking,
  automatic lineage publication and a promise-tracking product need separate
  evidence/retrieval validation before implementation is prioritized.
  [Full experiment and caveats](../../data/research/jev-eval/2026-09-22-report.md).

- **2026-09-12: "the page reads the right FILE" is not the same as "the file
  holds the right rows."** chain-B fix 3 keyed the whole dossier pipeline by
  page identity and the bundles still offered a sibling program's citable
  `projects`, because the SIDECAR the bundle reads was itself fused: 13 of 13
  shared BLI codes published both members' J-book narratives and both members'
  R-2/P-40 rows. Three lessons. (a) A guard whose premise expires stops
  guarding silently — `owns_detail` separated the two members only while five
  of the six Navy procurement appropriations went unparsed, and Wave 5's
  comment updating that premise did not revisit the two call sites relying on
  it. (b) The defect is invisible to every number-to-citation gate by
  construction: each row IS a real J-book row with a resolving fact id; only a
  cross-page identity check sees it, which is why leg n check 8 asks "does
  this fact id appear on two member pages" and not "does it resolve". (c) The
  honest answer for a row that matches NO member (the PROC_DoDEA volume under
  code '30') is neither page plus a count — publishing it on all three
  members, which is what the bare-code lookup did, put a school-system
  justification under OSD's, DTRA's and DMACT's names.

- **2026-09-09: F-15 funding and workspace UX refinement in progress.**
  Ambiguous Develop/Buy/Upgrade controls and competing year selectors are
  replaced by named funding records and a single annual chart. Aircraft,
  funding, international research, history, comparison and saved receipts now
  occupy focused workspaces with preserved URL state. Screenshot-only Astra
  critique is guiding the visual pass. Final visual acceptance, fresh export,
  acceptance gates and static preview review remain pending.
  [UX refinement](plans/2026-09-09-f15-family-browser.md#ux-refinement-in-progress).

- **2026-09-09: F-15 family research expanded beyond budget mappings.**
  All 24 model topics now have sourced aircraft context. The added research desk
  covers 8 country records, 16 procurement milestones and 14 supplier/system/
  program cards, with dated government, manufacturer and reporting evidence.
  Requests, signed orders, options, potential-sale approvals, obligations,
  ceilings and deliveries stay distinct. Current reporting corrects Indonesia's
  old proposed-buyer status; Korea's January 2026 award is separate from its
  2024 sale approval. FY2027 context does not replace the FY2026 warehouse ledger.
  Search, source and variant filters, evidence drawers and citation copying
  work on desktop/mobile. The larger research module loads on approach;
  inspection context is available initially. All **1,244 tests / 82 files** pass,
  with clean targeted lint, TypeScript and browser accessibility checks.
  The fresh production build and **24/24 acceptance gates pass**. Final static
  preview checks confirm contract-ID search, updated country status and 390px
  layout without overflow. The page is 665,992 raw / 67,152 gzip bytes, within
  its unchanged size ceilings. Work remains local on `codex/f15-family-browser`,
  with no commit, push or deployment.
  [Implementation and research contract](plans/2026-09-09-f15-family-browser.md#public-research-expansion).

- **2026-09-09: F-15 family browser implemented on a new branch.**
  Branch `codex/f15-family-browser` adds `/families/f-15/` with A/B/C/D/E/EX
  selection, an original interactive aircraft schematic, camera-preserving
  variant changes, aligned comparisons, blueprint/CFT configuration controls,
  optional sounds, linked funding topics, fiscal history, real receipts and a
  persistent research tray. Explore, all six relevant dossiers, sitemap and
  Pagefind expose the family. Shared C/D/E/EX software, C/D/E modifications,
  E/EX EPAWSS development, E-only EPAWSS procurement and dedicated EX records
  retain distinct scopes. Canonical fiscal selection uses the exporter's exact
  preferred fact IDs; derived totals keep their source inputs. Unpaged narrative
  receipts now show the exact source passage as well as the XML locator, through
  optional page-local citation enrichment that leaves the shared cache intact.
  Desktop/mobile inspection verified model rotation, keyboard controls, stable
  camera, comparison, actual workbook drilldown, source passages and research
  copy/restore. Validation: **1,215 tests across 80 files**, targeted ESLint,
  TypeScript, a fresh production build (8,369 generated routes), and all **24
  acceptance gates** verified. The full run passed gates 2–24; gate 1 passed
  separately on the same output after refreshing the existing companies-page
  weight measurement, with its size ceiling unchanged. The new family route
  also has a page-weight budget. Final static-preview inspection verified 3D
  activation, a model topic opening its exact source passage, and a clean console.
  Work remains local and uncommitted; earlier checkout changes are preserved.
  [Implementation and data contract](plans/2026-09-09-f15-family-browser.md).

- **2026-09-08: twenty additional frontend concept variations generated.**
  Ten fresh private 256-character alphanumeric inspiration seeds selected
  palette, typography, layout and illustration details for ten distinct design
  families. Built-in Codex imagegen rendered each as a homepage and Virginia
  Class dossier: **20 unique 1536×1024 images**, all saved in the workspace.
  A standalone local gallery groups the pairs and provides page-type filters,
  full-size viewing and keyboard navigation. Financial/source rows are explicit
  placeholders; image-generated promotional slogans are recorded for neutral
  editorial replacement before any implementation. All 20 local image URLs
  return HTTP 200; gallery filters, viewer navigation and focus return were
  browser-checked. No application code or production deployment changed.
  [Gallery, images and exact prompts](../../art/concepts/2026-09-08-twenty/README.md).

- **2026-09-08: two additional frontend art directions explored.** A shell
  script generated a private 256-character alphanumeric seed and mapped it to
  palette, typography, layout and model-rendering choices. Codex built-in
  imagegen produced four 1536×1024 concept studies: Industrial Almanac and Polar
  Instrument, each as a homepage and Virginia Class dossier. Source-table labels
  were refined to preserve BLI identity and make illustrative rows explicit;
  amounts remain placeholders with fiscal-year, request and accounting context.
  The seed was discarded and never placed in the prompts or artwork. Selected
  images, exact prompts, derived choices and the shell script are saved in
  [the concept comparison](../../art/concepts/2026-09-08-seeded/README.md).
  This is an art-direction exploration; no website code or deployment changed.

- **2026-09-07: editorial frontend redesign published.** All 24 page templates
  share a paper/ink and blueprint visual direction, task-based navigation,
  contextual page introductions, and a structured footer. Program dossiers
  keep their three-answer strip and 13 original sections, with new chapter
  navigation and source wayfinding. The larger receipt reader retains real
  document previews, source locators and copy/share controls; preview scrolling
  is keyboard-accessible. Program filters/sorting survive reload in the URL.
  Company search precedes extended context; entity profiles and research tools
  have task-specific routes into their evidence. Mobile reference navigation is
  a native disclosure above the prose. Fact permalinks distinguish derived
  figures and avoid promising an exact program location for ambiguous IDs.
  District table copy now correctly describes award links across services.
  Codex imagegen produced homepage, dossier and receipt-reader concept studies;
  illustrative mockup data stays outside the published evidence assets.
  Validation: **1,174 unit tests / 24 acceptance gates / 8 live asset checks /
  27 production artifact comparisons pass**, plus desktop/mobile browser review
  and a real Navy source PDF in production. Existing page-weight ceilings were
  retained; several dense routes have little remaining headroom. Budget receipts
  preserve provenance, while universal per-award payment tracing still needs
  exporter enrichment; this release does not increase data coverage.
  Deployment `dpl_AW7JRD39jVFpM72JTZYMzLUvQhDj` is Ready at
  [fiscalreceipts.com](https://fiscalreceipts.com/), published through
  `scripts/launch/deploy.sh --skip-r2`. No warehouse/R2 source assets changed;
  the three prior 3D pilots remain. No git commit or push was made.
  Details: [frontend work log](plans/2026-09-07-frontend-redesign.md).

- **2026-09-07: three visual-exhibit pilots published.**
  [Live gallery](https://fiscalreceipts.com/explore/) leads to Virginia (`2013`),
  F-35 procurement (`ATA000`) and development (`0604840F`), and Cyber Security
  Research (`0602668D8Z`). Original illustrative GLBs and reviewed Blender
  renders accompany curated explanations, exact source IDs, fiscal-year/basis
  labels, optional local Three.js rendering, blueprint mode, keyboard topics,
  and shared views. Editable scenes and PNGs are in `art/exhibits/`.
  All 20 pilot narrative/financial IDs resolve. No component costs are inferred.
  Desktop, tablet, and mobile browser review caught and fixed overlapping cyber
  hotspots; all three mobile targets now select the correct explanation, also
  after rotation. Three collision regressions pass. Full release verification
  passed 24/24 gates; the subsequent viewer-only correction passed its rebuild,
  freshness check, targeted lint, and direct browser regression.
  Production deployment `dpl_QJDYqoHyR6amh5sPB5su7E1icwYG` completed through
  `scripts/launch/deploy.sh --skip-r2` (no warehouse/PDF changes). All eight live
  asset assertions and 13 pilot production checks pass; shipped model/poster/JS
  bytes match the release. The live gallery, 3D topic selection, blueprint view,
  and rendered source PDF were verified in the browser. Source changes remain
  in the workspace; no git commit or push was made.
  Details: [pilot work log](plans/2026-09-07-visual-exhibits-pilots.md).

- **2026-09-01: crosswalk hand-adjudication (correction) + FPDS-AP expansion
  (coverage), one deploy.** All 10,091 published (pe, award) pairs were
  individually adjudicated (688 award investigations, 28 agents, two
  adversarial refuter lenses per proposed pin): the mechanical high tier
  measured **9.1% precise** (37/408) — corrected to 60 adjudicated-high /
  9,212 medium, 819 low/reject pairs unpublished (migration 010 overlay;
  mechanical tags retained as `crosswalk_confidence`, supersede-not-delete).
  Ground-truth rejects incl. SSPARS (5 false high links on one AF radar-O&M
  contract), NSWC Dahlgren, CTEIP. Coverage then rebuilt on stronger
  evidence: all 746 FPDS acquisition-program codes hand-mapped to J-book
  lines (674/879 mappings survived both lenses; 267 honestly unmapped),
  awards narrowed per-line by funding-account color — **1,020 high + 857
  medium pair-rows across 186 PEs, all services** (F-35, Virginia class,
  Sentinel get first award tables); 23k AP-tagged awards with only
  non-J-book money (O&M) deliberately unlinked. Districts 106→41→181.
  Species lessons, each now structural: **keyed sidecar dirs must
  prune-before-emit** (stale `flows/` kept publishing a REJECTED award at
  "high"; districts/breakdowns same; `copyDir` now mirrors); **collision
  pe_blis excluded from link targets** (account-narrowing unioned both
  programs' accounts — a "high" could hit the wrong program); synthetic
  `-L` keys excluded; empty sidecars not written; gate 12 rescoped to
  renderable pages + non-vacuity floor; leg-j designator exemption (DDG
  1000 ≠ a count); File C ruled out separately
  (docs/superpowers/reviews/filec-program-activity-spike.md). Follow-ups
  filed: /feed/ pagination (ceiling raised with do-not-raise-again note),
  Leg 2 name-lexicon + Leg 3 (SAM solicitations, FSRS, defense.gov
  announcements) in flight via parallel sessions.
- **2026-09-01/02: Leg 2/3 discovery — announcements corpus + lexicon (two
  parallel sessions).** Deterministic J-book name-lexicon mined from 30,116
  narrative rows (v1.2: 10,464 entries, ownership own/mentioned, 943 flagged
  weak_name); defense.gov daily Contracts announcements acquired via the
  Wayback Machine (2,786 digests, 22,140 records, 92.4% PIID join to the
  lake, sha256 manifest); FSRS subaward descriptions matched to lexicon
  (3,966 subawards / 269 PEs / $6.6B, corroboration tier). **Hard negative,
  do not rebuild:** literal PE numbers appear in 15 of ~20M award
  descriptions and ZERO of 1.6M subaward descriptions — the "grep award text
  for PE numbers" folk method exists only in solicitation documents.
  SAM.gov solicitations: official API key-gated; unauthenticated search
  returns 0 for bare PE codes — filed as a task chip with probe notes.
  **Wave-1 verification (6,309 candidates on PEs with no published links,
  triage → adversarial refute, 133 agents):** 6,276 triaged → 802 proposed
  (4,311 wrong, 1,163 weak) → **397 survived the refute pass → 386 published
  at high across 168 PEs** (7 collision-key and 4 no-lake-evidence exclusions).
  Method `announcement+lexicon`; every link's rationale cites its announcement
  (article id, date, URL) and its match basis. **Wave 2** (3,934 packets after
  wave-1 dedupe: exact-name 1,254 / designator-normalized 2,347 / LLM-alias
  bases 333, weak_name excluded; 91 agents): 3,933 triaged → 811 proposed
  (1,213 wrong, 1,909 weak) → **411 survived**. **Combined waves 1+2: 808
  survivors → 783 published at high across 300 PEs** (7 collision, 4 catch-all,
  14 no-lake-evidence exclusions). LLM-pass scope disclosed on /methodology/
  verbatim ($1.96T of $2.23T residue attempted; 12,811 records/$278B not).
  **Wave 3 (FSRS subawards)**: 3,871 raw (prime, PE) hits collapsed to 750
  distinct new candidates (265 corroborated existing prime links; 460 weak_name
  hits excluded); 745 triaged → 222 proposed (352 weak, 171 wrong) → 115
  survived → **67 published at MEDIUM** (`subaward+lexicon`; one hop removed,
  never high) after collision/catch-all/no-lake exclusions. **Grand total of the
  announcement legs: 850 links (783 high + 67 medium) across 329 PEs; site-wide
  PEs with any published link: 24 → 430+.**
  Two more species surfaced by the wave-1 publish: **catch-all budget lines are
  not link targets** ("Items Less Than $5 Million", "Ordnance Items <$5M",
  "Other Support Aircraft" — aggregates, not programs; the `$` in the title
  also trips the currency-in-prose sweep) — `CATCHALL_TITLE` exclusion in both
  loaders; and **/feed/ is now a digest** (expansions took it 160→720 cards /
  1.5→6.8MB; per its do-not-raise note the page renders the top 75 cards per
  section with a truncation note, full set in feed.json + RSS/Atom, ceilings
  LOWERED to 3.2MB/150KB, hhi floor re-scoped to the capped page).
- **2026-07-02: product rebranded to Fiscal Receipts** (site display name; infra
  identifiers unchanged).
- **47.3% of FY2025 DoD obligations ($232.4B) were not competed** — surfaced by
  the 5H competition overlay from extent_competed, a field sitting untapped in
  the contracts parquet since Phase 0. Editorial headline candidate.
- **Losing bidders are structurally absent from all public data** — FPDS records
  number_of_offers_received (counts) but never offer identities; SAM.gov is an
  entity registry, not a bid ledger. The /flow/ UI states this statically
  ("counts offers, not bidders") so the overlay can't be misread (5H).
- **Sankey labels: precompute collision-free placement in the exporter, don't
  fix collisions in the client** — thickness-threshold suppression + placement
  at export time made "no label overlaps" a TDD-able bbox-intersection test
  instead of a rendering hope. Rendering-metric drift (font change) is the
  residual risk — judge flagged; closed 2026-07-03 by G9 leg f (backlog #20),
  which promptly caught a real Avenir-Next under-measurement on its first
  clean run (5H F3 fix round, 3→5/4/5).
- **Negative net flows need an explicit rule** — TACOM→Boeing FY2017 nets to
  −$97.6M; sankeys can't draw negative width. Rule: draw at zero width, label
  "net de-obligation", keep the citation (5H).
- **max() on confidence strings is a trap** — lexicographic max('high','medium')
  = 'medium'; the flow marts needed an explicit ordinal mapping (5H dbt).
- **R2 asset sync drifted out of the deploy loop (5G, caught 2026-07-04).** The
  deploy drill rebuilds `site/out` and pushes to Vercel but never re-syncs
  `data/site/pdfs → R2`. So every phase since the 2026-07-02 launch (5E decade
  editions, 5F/5H additions, 5G Navy) shipped citation *metadata* while the PDF
  *binaries* were missing from the CDN — the panel degraded to "open official
  source" and no gate or live-check caught it (prior live-checks happened to
  click workbook/XLSX and derived citations, which were in R2). Fixed by
  re-running `upload_r2.sh` (190 files / 1.48 GiB). LESSON: the "deploy" step is
  Vercel + R2, not Vercel alone — a gate should sample a live PDF fetch from a
  recently-added citation, and the deploy drill must include the R2 sync
  (backlog #27).
- **Government WAFs are not uniform — probe each, never assume (5G).** Navy's
  secnav bot-WAF yields to a realistic headless browser; Army's Akamai blocks
  the identical browser with a 403. The feasibility spike's "Army ≈ Navy, both
  bypass with Playwright" premise was disproven by the actual probe. A blocked
  WAF is a finding routed to the manual path — never a prompt to build evasion.
- **Live data finds bugs fixtures can't — ingest surfaces them (5G).** Three
  Navy defects appeared only against real books: each BA-split PDF embeds the
  full master (12× over-load → per-family dedup), P-1 line numbers reuse across
  appropriations (204 false recon failures → account-scoped Gate B), and Navy
  renders dollars in thousands not millions (provenance form). None were
  reachable from fixtures.
- **`superseded` is an accounted-for terminal state, not a coverage gap (5G).**
  Deduplicated duplicate documents get a reversible status flip (never a
  destructive DELETE); the edition-coverage gate counts them as terminal, with
  a `recon>0` guard so an all-superseded edition still fails.
- **A WAF-blocked source has a legitimate public mirror — the Internet Archive
  (5G-archive).** Army (Akamai-403 to even a headless browser) and AF/SF (CAC)
  are unreachable server-side, but Wayback mirrors their PUBLIC FY2026 books
  WAF-free. Fetching a public archive of public records is a legitimate
  transport, not evasion — and it needs its own robustness layer: the
  availability API is flaky (CDX is authoritative), `id_` snapshots can be HTML
  interstitials (guard `%PDF`) or 5 MB-truncated (guard `%%EOF`, on resume too),
  and some books are archived only under a `?ver=` variant (prefix-search
  fallback). Provenance records the ORIGINAL gov URL; Wayback is transport only.
- **Dedup rules do not generalize across services — derive them empirically
  (5G-archive).** The Navy filename BA-split heuristic collapsed 18 distinct
  Army books when reused blind. Army RDTE is genuinely per-volume distinct
  (each volume's PDFs share only THAT volume's master); AF RDTE Vol I-IV share
  one master; AF vs SF RDTE differ despite same org+family. The robust rule is
  content-based: group by the sha256 of the master XML `pick_book_xml` selects
  and keep one per `(family, master-sha)` — no per-service filename knowledge.
- **Many-books-per-org-folder needs a per-document extraction dir
  (5G-archive).** Defense-wide/Navy put one book per family in each org folder,
  so a shared `xml/` dir was safe; Army/AF pack a dozen justification PDFs into
  one folder and their masters clobbered each other, making `pick_book_xml`
  return the wrong master and the dedup collapse distinct books. Fix: per-stem
  `{name}__xml/` dir, with a read-time fallback to the legacy shared dir.
- **The Internet Archive is a WAF-free mirror of PUBLIC govt budget books with
  the embedded XML intact — the CAC/Akamai "hard blockers" were access-method
  problems, not data-availability problems (5G-archive-site).** Everything the
  5G Navy round could only get by driving a stealth browser past secnav's bot-
  WAF — and everything the 5G probe declared a "hard blocker" for Army (Akamai-
  403) and AF/SF (CAC) — was sitting on Wayback the whole time, same public
  records, same embedded jb-2009 XML that anchors every figure to its page. The
  site ripple is the proof: 928 program pages flipped rollup→full and 1203154SF
  "Long Range Kill Chains" (#1 by FY2026 request) now renders its Space Force
  RDT&E narrative + working PDF citation. The lesson is to separate "can't
  reach it with THIS transport" from "the data isn't public" — the second was
  never true.
- **A larger corpus surfaces latent bugs and stale eval pins — data growth is a
  gate stress-test (5G-archive-site).** Flipping ~1,000 service PEs to full tier
  exposed three defects the smaller corpus hid, each fixed at the root, none by
  weakening a gate: (1) two Army R-1/P-1 lines mis-parsed the appropriation
  label ("RDT&E"/"O&M") into the pe_bli slot — harmless as rollup data, fatal as
  a URL route (the '&' 404'd the page); a route-safety filter drops only these
  garbage PEs. (2) The search near-exact company boost matched on a 3-char stub,
  so "general dynamics" wrongly boosted "GENERAL ATOMICS"; tightened to a real
  head-prefix. (3) Every service now has its own "Defense Research Sciences" PE
  (a 5-way exact-title tie), so a search-eval pinned to DARPA's PE needed the
  org in the query to disambiguate. The years-matrix payload also grew linearly
  (813→1,741 programs, same ~1.6KB/program) — a budget raise, not a regression;
  pinning the pytest budget to the exporter constant stops the three copies from
  ever drifting apart again.
- **A hardcoded "ingested-orgs" constant lies the moment the data outgrows it —
  derive the set from the loaded books (audit-fix 2026-07-05).** `program-tier.ts`
  pinned `INGESTED_SERVICE_ORGS = {A,N,F}` by hand, so every defense-wide agency
  page whose FY2026 J-book WAS loaded (OSD, DCSA, MDA, DISA, DARPA, … — 27 books
  → 25 workbook-org codes) still rendered the false "the {org} J-book is not yet
  ingested". Three confirmed liars: 0604130V/0305133V (DCSA), 0303367D8Z (OSD).
  Fix: the exporter emits `site_meta.ingested_service_orgs` — the distinct
  `jbook_documents` FY2026 downloaded orgs, each run through `workbook_org()` so
  the codes land in the SAME space as `details.service_org` (CYBERCOM→CYBER,
  CHIPS/DPAP→OSD) — and `isIngestedServiceOrg` reads that payload (data.ts
  injects it via a build-time setter, since program-tier is a universal no-fs
  module). Orgs with no loaded book (DHA, DEFW, IG) stay absent → keep the
  honest wording. Lesson: any "which things are ingested/covered/enabled" set
  that a human maintains alongside the data it describes WILL drift; make it a
  query, not a literal.
- **Reject junk at the loader, not just at the exporter (audit-fix 2026-07-05).**
  Army P-1 appropriation SECTION-HEADER rows ('RDT&E', 'O&M') mis-parsed the
  label into the BLI cell and `p1_loader.load_p1_rollup` inserted them as real
  `budget_lines` rows. The exporter's `_is_route_safe_pe` filter hid them from
  PAGES (the '&' 404s a static route) but they still polluted every
  budget_lines-by-pe_bli aggregate (and 30 phantom workbook citations). Root fix
  is a pe_bli validity guard AT the loader (`_is_valid_pe_bli` rejects `& / % #`
  + whitespace, before era re-keying so digits/letters/era sub-line hyphens
  survive) plus a scoped one-shot cleanup of the 8 already-loaded rows
  (`scripts/clean_junk_pe_bli.py`, fy2026-scoped so the FY2017–2023 hyphenated
  era keys `0300D-CBDP-L70` are never in range). A route-safety filter that
  masks bad data from the UI is belt; rejecting it at ingest is braces.
- **A tail-scan window sized for the common case false-negatives the valid tail
  (audit-fix 2026-07-05).** `is_complete_pdf` scanned only the last 2KB for
  `%%EOF`; a valid PDF whose final `%%EOF` sits past 2KB (trailing metadata,
  incremental-update tail, linearized xref) read as truncated → spurious
  download gap. Widened to 64KB.
- **The whole 2017–2023 J-book era embeds .zzz XML** — same renamed-zip +
  jb-2009 schema as 2026; the Mistral-OCR fallback was never needed (5E).
- **Era editions publish consolidated volumes under unstable naming** — token
  classification + evidence-keyed exceptions (EVIDENCE_PATHS, download and
  inspect the embedded XML) beat prefix regexes; count envelopes must be
  era-aware (5E).
- **Era P-1 line numbers are not program identities** — the same string spans
  orgs, conflates programs, and collides with modern BLI codes; namespace
  within edition ({account}-{org}-L{line}) and guard keyspace disjointness (5E).
- **PB2019 OSD ships the same MJB XML in two BA-split volumes** — identical
  tuple sets under both documents; the dedup binding was recorded in the plan
  BEFORE the marts existed, which is what kept it enforced (5E).
- **P-1R is a subset breakout of P-1, never additive** — workbook-proven
  (Aircraft Procurement Army FY2024 = P-1 alone); excluding P-1R from candidate
  sums published 993 previously-unverifiable procurement grains (6 small-dollar
  book quirks noted) (5E).
- **`fiscal_year >= threshold` fences silently merge edition-relative
  scenarios** — PriorYear means a different fiscal year in every edition;
  always fence `= edition` (the 291-programs-wrong-FY2024 near-miss) (5E).
- **Copy-paste-canonical eval contracts need temperature 0 AND deterministic
  SQL rules** — and prompt examples leak into behavior on the very entities
  they mention; keep rules generic (5E).
- **Fencing typed exports requires symmetric fencing of every
  provenance-derived emission pass** — the 27.8k-orphan citation hazard
  (staleness luck masked it until the adversarial re-review simulated a fresh
  export) (5E).
- **Multiple marts can legitimately own the same quantity** — eval
  table-overlap prechecks need documented equivalence groups or agents
  flip-flop between correct citations run to run (5E).
- **Next.js title.template doubles when pages also append the site name** —
  every one of 6,593 pages rendered "… | Fiscal Receipts | Fiscal Receipts";
  caught only during 5H live verification because no gate read <title>. New
  render-static leg (t) asserts the site name appears at most once
  (proof-can-fail: 6,593 pages).
- **J-book PDFs embed full XML** (.zzz attachments) — extraction is deterministic;
  no LLM needed for federal budget facts. The single most load-bearing discovery.
- **Fact identity must include the amount** — 11 live duplicate
  (sha, pe_bli, project, scenario) keys differ only in amount (5B-1).
- **Gates must compare raw rowcounts vs distinct keys** — set-collapse in checks
  hides join fan-out (the 24×-overcount class; re-found at citation layer in 5B-1
  final review).
- **23% of J-book facts are $0** — page-highlighting "0.000" is meaningless;
  zero_amount facts carry xml-path citations only (honesty policy, 5B-1).
- **73% of page resolutions are ambiguous_first** (amount appears on 2+ pages —
  summary + detail exhibits). Improvement candidate: scenario-column/exhibit-header
  anchoring to prefer the R-2/P-40 detail page (→ Backlog #3).
- **LDA client_name filter is contains-style** — query family_key + raw parent
  names + curated aliases; longer query strings return nothing (5A).
- **Entity-graph raw names are the honest alias authority** (UEI-grounded matching
  beats string fuzz; 'UNITED' single-token over-merge is the cautionary class).
- **pdfplumber (MIT) over PyMuPDF (AGPL)** for anything near a hosted product;
  hybrid pypdf-prefilter keeps full-corpus page resolution in minutes.
- **Decimal("NaN") inserts silently** — numeric pipelines need is_nan()/is_finite()
  guards at every parse boundary.
- **USAspending throttles multi-GB pulls** — patient 20–25min cooldown retry loops
  succeed where hammering fails.
- **Agent-visual judging catches what mechanical gates can't** (5B-2): all 7
  tool gates passed while the uncited-flag rendered doubled/overlapping and the
  mobile nav didn't collapse — 3-judge screenshot rubric failed it; after fixes,
  5/5/5/5. Visual gates are load-bearing for UI phases, not decoration.
- **Gate checks must be audited for vacuousness**: two clickthrough assertions
  passed while testing nothing (a misspelled field name; a missing chip check) —
  found only by the final whole-implementation review asking "would this gate
  catch a regression?". Negative-scan allowlists need exact-match semantics.
- **The vacuous-check class recurred TWICE more in 5B-3** — (1)
  `getAttribute(x) !== null` is always true under node-html-parser (returns
  undefined): the entire negative currency scan had never flagged anything;
  fixing it unmasked 1,916 strings needing a three-way taxonomy (quoted source
  prose = structurally exempt WITH block citation required; program names =
  labels; real violations = fix the site). (2) The derived-tier recompute read
  `recorded_value` from inputs that carry their value in `amount_thousands` —
  silently skipping verification of every headline figure; the fixed gate
  immediately caught a real 2× over-sum in the metric→amount_type mapping.
  Standing rule: every new gate ships with a test that proves it CAN fail.
- **Gate-weakening-by-eval-deletion**: an agent deleted failing search eval
  cases instead of indexing district pages — caught in orchestrator review.
  Eval cases are contracts; deletion requires a recorded decision.
- **Tech-stack lessons (5B-2):** SVG `<title>` inside server components gets
  hoisted by Next → hydration mismatch (use `<desc>`); .wasm needs
  `application/wasm` content-type for streaming compile; RSC→client props must
  be JSON-serializable (no Set); runtime asset config (public/config.json) beats
  env-baked bases — one artifact is both gated and shippable; Turbopack honors
  webpack magic comments (turbopackIgnore) for externals like Pagefind.
- **Sandbox broke the warehouse (5B-4, 2026-07-02):** `SET enable_external_access=false`
  (added to stop read_text exfiltration) silently broke every mart query because
  marts are views over read_parquet — mocked FakeClient tests couldn't see it
  (fixtures use in-DB tables). Live eval crashed to 5/45 REFUSEs. Fix: DuckDB
  `allowed_directories` (scoped to the parquet lake) + `enable_external_access=false`
  + `lock_configuration=true`, with a parquet-backed-view regression test. Lesson:
  security lockdowns need a live-path smoke test, not just mocked denial tests.
- **Answer contract invisible to mocked tests (5B-4, 2026-07-02):** first working
  live run scored 5/45 because the model submitted markdown prose in
  `submit_answer.answer` while the grader compares exact canonical values — the
  tool schema never stated the contract. Fixes: explicit canonical-value contract
  in the tool schema, separate `explanation` field for prose, and run_sql now
  returns the grader's own `canonical` string so compliance is copy-paste (imports
  the same `_canonicalize` the grader uses). Lesson: any exact-match grader must
  publish its canonicalization to the agent as a copyable artifact.
- **Answer-shape taxonomy — 22 failures classified (5B-4, 2026-07-02):** SHAPE
  (extra columns/rows vs the question's literal ask), SEMANTIC (wrong
  table/grain/definition — e.g. pe_bli repeats across organizations; improper_payments
  temp table is all-VARCHAR so ORDER BY sorts lexicographically), PRECISION
  (per-question rounding), NONDET (DuckDB parallel float SUM varies run-to-run at
  trillions scale, ~0.1 variance — disproved the 'ROUND(x,4) makes it reproducible'
  idea live). Fixes were generic schema-card rules (question-literal shape,
  deterministic final SELECT, honest data-trap docs) — with an anti-overfit test
  asserting the card mentions no eval question.
- **Underspecified-question repair pattern (5B-4, 2026-07-02):** 9 residual
  failures traced to eval questions not stating the precision/units/shape/
  metric-definition their own answer_sql embodies. Repair = amend question TEXT
  only (expected_answer/answer_sql/tolerance untouched), e.g. 'in millions, to
  three decimal places'. Two eval bugs found and fixed: q005 answer_sql returned
  ranks 2 AND 3 for a single-answer question (limit 2 offset 1 → limit 1 offset
  1); q012/q024 pre-emptively clarified. Live-eval trajectory across the loop:
  5 → 23 → 36 → 45/45.
- **Eval cost correction (5B-4, 2026-07-02):** a full 45-question live run costs
  ~$0.40 (sonnet, ~$0.009/question), not the ~$10 earlier estimated — cheap enough
  to iterate the loop freely.
- **Visual judges catch data bugs evals can't (5C, 2026-07-02):** a judge spotted
  sparkline FY24 $561.0M vs card $280.5M on the same page → fct_budget_trajectory
  summed rollup+detail duplicate rows (the q008 trap at the mart layer); 146 of
  1,982 PEs inflated 1.09–2.0×; invisible to the eval because pct-change ratios
  cancel doubling and eval absolutes hit fct_budget_lines with title filters. Fix:
  detail-only pivot + exporter derived-input join mirror; 4,446 trajectory citations
  re-verified. Companion lesson: derived-citation recompute passes when formula and
  recorded value share the same wrong inputs — recompute checks internal consistency,
  not truth; independent cross-surface comparison (two renderings of the same
  quantity) is what caught it.
- **fullPage screenshots don't trigger IntersectionObserver (5C, 2026-07-02):**
  below-fold reveal content captures as blank; a judge flagged a phantom "blank band".
  Capture scripts must scroll-through before fullPage shots.
- **Dead-link feed events (5C, 2026-07-02):** 136 feed events linked to
  non-existent program pages (pe_blis in trajectory but not dim_programs); G1 gained
  a dead-link leg (proof-can-fail recorded); titles for all 136 resolved from
  fct_budget_lines detail rows at export.
- **svg `<desc>` a11y text is read by screen readers but was invisible to the
  currency gate (5C, 2026-07-02)** after a naive exemption — tightened to require
  an identical [data-amount] twin in the same svg's parent subtree.
- **Evaluator-first worked as designed (5C, 2026-07-02):** G1/G2/G3 built failing
  (orphan nav, no coverage notes, silent degradation), recorded, then turned green
  by implementation — same for the dead-link leg. Proof-can-fail is not a checklist
  item; it is the gate.
- **Fleet stragglers ship half-finished expectation raises (final stage,
  2026-07-02):** an uncommitted fleet diff raised match_gate5a to 0.85 claiming
  "data legitimately improved" — but the LDA re-pull that would improve the data
  never ran (aliases alone can't match filings the original pull never fetched;
  verified: only 1 of 4 target client names exists in the parquet at all).
  verify-phase5a caught it at 40/50 = 80% < 85%. Rule refined: a
  documented-expectation raise must land in the SAME change-set as the pipeline
  run that makes it true, with the gate's PASS output as commit evidence. Same
  class: a fleet build regenerated llms.txt without NEXT_PUBLIC_SITE_URL,
  committing placeholder-origin URLs into the tracked artifact.
- **LDA pull attribution is first-query-wins even at match 'none' (2026-07-02):**
  the global UUID dedup in pull_top_families assigns a filing to the first
  (highest-obligation) family whose contains-style query returns it, regardless of
  match quality — VECTRUS's 'V2X' query consumes the 'V2X, Inc. (formerly known as
  Vertex Aerospace)' filings at match 'none', starving VERTEX AEROSPACE SERVICES.
  A future re-pull should prefer matched attribution over unmatched before global
  dedup (or dedup only among matched claims).
- **Exhibit-header tie-breaking shrinks pdf-page ambiguity by a third (2026-07-02):**
  ambiguous_first 73% → 51% of provenance rows (969 facts disambiguated to their
  detail-exhibit page); the rebuild is deterministic (delete + rebuild reproduced
  all 4,419 keys byte-identically), so the improvement is re-runnable at every
  future J-book ingest.
- **Paragraph-provenance technique (5F, 2026-07-03):** narrative paragraphs are
  located in the source PDF by their OPENING TEXT (first 12 words,
  whitespace-normalized — the `narrative_opening` string is BINDING, shared
  verbatim with the verify-phase5b1 re-derivation leg) via the same
  pypdf-prefilter + pdfplumber-confirm machinery as amounts, with pe_bli →
  source-exhibit → project tie-breaking and a word-boundary span guard; bbox is
  the passage's first rendered line. 2,449/2,457 (99.7%) resolved; the 8
  unresolvable openings store 'unresolved' with NO page and keep the pageless
  citation card — locations are never faked. Prose needed no new machinery,
  only a new *anchor* (opening text instead of an amount) into the existing
  amount-provenance pipeline.
- **Integration tests catch cross-pass crashes unit tests can't (5F,
  2026-07-03):** the exporter's 4a jbook_pdf citation pass predated the
  target_kind discriminator and read ALL provenance_pages rows — with zero
  narrative rows it passed silently for weeks; the FIRST real
  narrative-provenance build (2,457 rows, NULL amounts by the kind-shape
  constraint) fed NULL into fact_id_jbook and crashed export-site. Each pass's
  unit tests were green in isolation; only running both builders + export
  together surfaced it. Regression now TDD'd (both builders in one export;
  4a selects target_kind='amount' only). Producer-consumer integration tests
  are load-bearing whenever two pipeline stages share a table.
- **Deterministic-prose-cite restraint is self-proving (5F, 2026-07-03):** a
  prose dollar token becomes a clickable cite ONLY when it exactly equals
  (canonical dollars) exactly ONE resolvable fact scoped to the same PE —
  ambiguous, unit-less, and uncited tokens stay plain prose. That yields just
  27 prose cites across 2,457 narratives, and the visual judges praised
  exactly this: the sparseness itself communicates that every link is earned
  (a maximal-recall linker would have manufactured doubt about all of them).
  Precision-over-recall in citation UX is a trust feature, not a coverage gap.

- **2026-09-04: crosswalk follow-ups (#70–#77 + raw-corpus backup), one SDD
  plan, 20 commits.** What the reviews caught, in the order they bit: (1) the
  announcement citation card said the announcement "names both this contract
  and this program" — true for 190 of 708 links; the rest were matched by a
  normalized designator, an LLM-judged alias or the work description, and 324
  recorded no basis at all → `match_basis` carried end to end and rendered in
  words. (2) `/methodology/` listed measured precision for a tier withdrawn
  four commits earlier and 100% for `fpds-ap` on a population that no longer
  existed (pooled honest figure 94/120); `account+subagency 60/60` had been
  adjudicated against the rule itself, not program attribution → figures now
  tally by the tier a link publishes under today, latest sample only, and
  unmeasured tiers are named (gate 24 leg n checks listed ⊆ published ⊆
  listed-or-named). (3) The in-table medium caveat shipped two commits before
  the FPDS tier moved into medium and was false for ~2,000 rows. (4)
  `program_dollars`/HHI formula text said "high-confidence join, obligation
  > 0" over a high+medium, net-of-deobligation sum. (5) `/json/feed.json` 404'd
  in production — reached only by client fetch, invisible to the link-graph
  gate → fetch-target leg. (6) The brief's unbounded `jbooks crosswalk --org
  DARPA` cross-joined 177 line-editions × a FY2017–26 lake (+2,214,705 rows;
  reverted from a parquet backup). Lessons: any change to a tier's name,
  membership or threshold must re-read every rendered sentence that names a
  tier; a precision study must record its rubric and refuse to publish strata
  judged on different questions side by side; loaders that share a key need
  the same method guard regardless of run order; a gate that resolves hrefs
  does not see fetches.
- **2026-09-05: #28 residue → #106 (five commits).** Gate 2 leg (sp) modelled
  babel's JSX text cleaner, and babel keeps a first line's leading space —
  Next 16's Turbopack does not when the run also carries an HTML entity, so
  `/methodology/` rendered "553whose" for a week under a green gate. The
  species was not merely known, it was documented *in the same file*
  (ba6c7d66's comment) and fixed at one site elsewhere (a2637af2): five
  remained, one of them client-only. Lessons: when a rendering defect is
  fixed at one site, the same change must grep the shape site-wide and leave
  a gate on the SHAPE, not the sentence; a gate that models a compiler is
  checked against what the compiler emitted, not against the model; an
  assertion shaped `a + (n − a − b) + b === n` is a check of nothing — read
  the rendered sentence back and add it up; and an exemption marker has a
  page-weight cost, so count the elements before spraying it (136 per filing
  page would have blown a ceiling nobody would have connected to it).
- **2026-09-05: the corpus-wide successor denial was checked against the
  rail, not the documents (#32(b) residue).** "No ingested budget document in
  this corpus states a successor for this line" rendered on 287 program pages;
  19 of them quote their own successor three sections lower — 2900 → LI 2361,
  FET000 → PE 0303131F, and DARPA's "Beginning in FY 2026, efforts in this PE
  will be funded in PE 0601122E" on 0601101E, the case #32 called unprovable.
  Exporter and gate both read the lineage rail, so both agreed; two
  implementations of one wrong scope agreeing is not corroboration (the same
  lesson leg (g) learned on 2026-08-27, in a new place). Fix: claim only what
  the site holds, point at the narrative, gate the note against the
  narratives themselves (gate 21 leg l, floor 19). Rule: a negative claim
  about a population ("no document states…") must be gated against THAT
  population, never against a layer derived from it.
- **2026-09-05: #80 — concentration on two bases.** The honest count behind
  the owner call: 768 high vs 11,512 medium links; 162 of 444 concentrated
  programs have no high link, 225 have too few (under 3 awards / 2 families)
  for an index that says anything about a market, 57 clear the floor.
  High-only everywhere would have deleted 387 cards; high+medium everywhere
  kept headlining an association tier. Both bases, smaller-true-number
  headline: the high-only figures where they exist, the all-tier figures on
  a labelled second line, the chip naming the tiers in every case. Two
  things the gates had to learn: gate 23 leg a2 groups [data-amount]s by
  (entity, fy, measure), so a second basis needs its own measure token
  (`hhi-high`, `obligations-high`) or it reads as a collision; feed leg (l)
  reconciles a card's band against the destination's ONE badge, so the
  second line's band is plain text and the badge now declares its basis.
  Found in passing, both pre-existing: eval q023 had been stale since #70
  (seven programs tie at 10,000 on the new basis — deterministic
  tie-breakers plus a rounded sort key), and verify-phase3's marts leg had
  been failing intermittently because DuckDB sums the squared shares in
  parallel, so a single-positive-family program reads 10000.0 or
  10000.000000000004 run to run (13/8/8/10/10/13 breaches over six
  consecutive counts). A gate whose result changes without the data
  changing is not a gate; the ceiling now carries a documented 1e-6 epsilon.
  **Addendum 2026-09-11 (fix round 1, 12 findings).** Three Criticals were
  this branch's OWN new work, and all three came from a floor and a headline
  that counted links instead of money. (1) The floor counted high-confidence
  AWARDS and LINKED families and nothing else, so 13 programs whose high
  links summed to zero positive obligations published `hhi_high` = 0.0 — a
  number, not NULL — which the card headlined "Competitive" with $0 (one
  with −$2.3M) under a top contractor the tie-break had picked
  alphabetically, and 7 more published 10,000 over a single positive-dollar
  family beside a card reading "Contractor Families: 2". The floor now
  measures positive-dollar families (published as
  `positive_family_count_high`) and positive net dollars, and withholds
  `top_family_high` with the index: 37 of 444, not 57. (2) The card
  headlined the all-links figure on 387 pages — the basis the #79
  adjudication had just measured at 0 of 60 for program attribution — and
  286 of those headlined an index below the very floor the mart refuses to
  publish. Publish the smaller true number: the card, the "Who gets it"
  line and the dossier bundle now carry the high-only basis or nothing, and
  say which. The `*_all` columns and their fids stay in the mart, the
  download and /methodology/; nothing renders them, so their own missing
  floor is a data question and stays open (see #107–#109 for the tier
  decisions it waits on) — it would have to be settled BEFORE that basis is
  ever rendered again. (3) `verify-phase3`'s new floor leg re-asserted
  exactly the predicate the mart's own `case` guarantees, so it was
  structurally 0 while all 20 bad rows shipped, and `high_only_rows` was
  returned but never entered `ok`. A leg that can only fire on a
  hand-written table is not a gate leg; it now asserts what the mart cannot
  satisfy by construction, and the row count carries a dated do-not-lower
  floor so a collapse of the high basis fails instead of printing. The
  species lesson from #70–#77 repeated verbatim: every one of the three was
  a tier-naming sentence or figure the branch itself had just written.
- **2026-09-11: precision rubric, and the number it exposed (#79).** The
  largest published tier (`account+subagency` — 9,337 published rows in
  Postgres over 416 DARPA awards and 24 DARPA PEs, 8,856 of them in the mart,
  72% of every published link a reader can meet) carried a 60/60 "precision"
  that measured only whether the linking rule had fired. Re-drawn (60 links,
  seed 20260905) and judged on program attribution — does this award execute
  this program element? — with the award's own description and the PE's
  narrative, project titles and lexicon names in the packet: **0/60**, two
  independent adversarial lenses per packet, 120 judgements, 0 disagreements.
  No sampled link cleared the rubric — but not all 60 failed the same way,
  and the entry first said they did (corrected 2026-09-11, Task 6c, before
  merge): several awards name a different DARPA effort outright, while at
  least SIX were refuted because the record names no work at all — pure
  "DARPA RESEARCH PROJECT" boilerplate (four of the six carry the
  "IGF::OT::IGF" prefix; HR001118C0133 and HR001118C0134 carry the bare
  string), which the rubric refutes on silence rather than on contrary
  evidence (HR001116C0090/0603469E, HR001116C0091/0603467E,
  HR001117C0002/0601117E, HR001117C0005/0603287E, HR001118C0133/0602115E,
  HR001118C0134/0602715E). At least FIVE more describe DARPA-wide
  contracting-office or acquisition-support staffing rather than any PE's work
  (HR001115F0001/0602026E, HR001115F0004/0603469E, HR001117F0009/0602115E,
  HR001117F0036/0605502E, HR001119F0016/0602715E — re-counted 2026-09-11 over
  the same detail file; this entry first said two). Where the
  reviewers found an overlap at all it was USUALLY the appropriation account,
  the DARPA sub-agency and the HR0011 prefix — the rule restated; SIX reasons
  record a thematic content overlap that is none of those three and nothing
  more (HR001113C0030/0602303E "thematic RF overlap", HR001115C0115/0601117E,
  HR001116C0014/0601117E "generic thematic overlap", HR001116C0090/0603469E
  "at most thematic overlap", HR001117F0017/0602025E, HR001119F0017/0602115E
  "thematic manufacturing overlap only" — counted 2026-09-11 over the same
  detail file; this half of the universal was left standing when the first
  half was hedged). Published as
  measured (smaller true number); what the tier does next is an owner call
  (#107). The fix is
  structural, not editorial: the verdict row records its rubric (migration
  015), the exporter filters on it, and gate 24 leg n makes the page name it.
  Lessons: a hand-named exclusion set is a label the next study forgets to
  update, a column is a property of the row; "latest sample only" had to
  become "latest run per stratum" the moment one stratum was re-judged alone;
  and a tier's prose has to be derived from the same list the figures are —
  "narrowed by sub-agency" was still rendering beside an unmeasured list that
  no longer contained that tier until the narrowings were derived too.

- **"Downloaded" is not "ingested" — and the constant that lied in 2026-07-05 was
  replaced by a query that measured the wrong thing (2026-09-12).** The fix for the
  hardcoded `INGESTED_SERVICE_ORGS` made the set data-derived, and derived it from
  `jbook_documents.status = 'downloaded'`. A file on disk is not a narrative: `DoD` (the
  three R-1/P-1 display workbooks) sat in the shipped set with **zero**
  `budget_line_details` rows behind it, and registering the Defense Health Program
  volume would have flipped all 14 DHA pages to "the book is ingested, this element
  simply has no narrative" the moment `acquire` finished — the same species, caused by
  its own fix. That is not a hypothetical: the volume was registered and acquired on
  2026-09-12, it carries no jb-2009 payload, and the old predicate would now return 26
  codes including DHA against the new predicate's 24. `_ingested_service_orgs` now joins
  `budget_line_details` (25 codes → 24; no rendered sentence moved). Second half of the
  same species: the honest wording only ever existed on the ROLLUP branch. `0603115DHA`
  and `0708083D` are synthesized into `programs.json` by
  `_trajectory_only_feed_programs`, so they render as FULL tier and told readers "The
  J-book detail for this line carries no separate mission or description narrative"
  about a line with no J-book detail at all (Task 17b carries the coverage note to that
  tier). Lesson, sharper than 2026-07-05's: making a set a query is not enough — the
  query has to measure the thing the SENTENCE claims, and every tier that can render the
  sentence has to be in the fix's blast radius, not just the tier where the bug was
  found. Corollary: a doc comment describing a query's semantics is part of the query;
  `program-tier.ts` still said "status='downloaded'" until it was moved in the same
  commit.

- **A cross-check whose slack is wider than the defect cannot find the defect
  (2026-09-12, #30 "and its predecessors").** The WSAA parser's expected population
  is the service index tables' row count, and in the 2024/2023 typesetting that count
  is an UPPER bound — a program name too long for the column wraps onto a row of its
  own and text extraction cannot tell that row from a program. 68 of 75 and 63 of 69
  cleared the 90 % guard by 0.7 and 1.3 points, and the docstring, the WARNING and the
  commit body all wrote the difference up as wrapped rows. Three of those rows were
  real programs the heading rule had dropped in silence — one of them, MK 54 MOD 2
  (ALWT), breaking the 2025→2024→2023 chain the rule exists to make. Cause: the rule
  required the banner's common name as a CONTIGUOUS run inside GAO's typeset heading,
  and "MK 54 MOD 2 (ALWT)" is not contiguous inside "MK 54 MOD 2 Advanced Lightweight
  Torpedo (ALWT)"; on three OTHER pages the same rule kept reading until it found the
  name inside GAO's first sentence, so `program_name` carried a sentence and the
  verbatim quote began mid-clause — both would have rendered as GAO's own words if
  either program were ever ratified. The fix is a token test beside the contiguous one
  and a head guard beside `DESC_RESIDUE_RE`'s tail guard, but the lesson is the
  DETECTOR: GAO prints exactly one banner per program, so the banner set diffed against
  the emitted set is exact where the row count is fuzzy, and that diff now raises
  instead of a `continue`. Corollary in the same species as #70–#77's: a tolerance
  explained in prose is a tolerance nobody re-measures — the sentence that called the
  gap expected noise is what kept it invisible, and the honest replacement is a run-time
  diff that states the truth rather than a docstring that predicts it.
- **2026-09-10: #10 was mis-framed for four months.** The backlog entry read
  "SAM entity extract / Splink entity-resolution upgrade" — two remedies for a
  defect that is neither. `recipient_parent_name` IS the SAM registration name,
  so SAM is the *origin* of the wrong string, not its cure; and the evidence
  joining the flagship pair is a shared child set, not string similarity, so a
  probabilistic linker never proposes it. The measured decision: $30.0B of
  addressable name-merge headroom against $255.2B of mislabelling. The fix that
  shipped was 15 curated rows and one gate leg. Lesson: when a backlog entry
  names a TOOL rather than a DEFECT, size the defect first — the sizing spike
  cost a day and deleted a week of the wrong work.
- **2026-09-12: the false sentence had four render sites; the audit that
  measured it found two (#111, Task 17c).** "Detailed justification for this
  program lives in the {org} J-book, which is not yet ingested" presupposes a
  book exists. Against the FY2026 index it is false for the DoD IG (no RDT&E
  or procurement justification book published at all) and for DEFW (none for
  its reconciliation / undistributed / roll-up rows) — 5 pages — and imprecise
  for DHA's 14, whose book WAS downloaded and carries no jb-2009 payload.
  A careful measurement pass counted the pages and found the sentence in the
  coverage note and the Justification empty state. It also rendered, on the
  same pages, from `buildRollupCard`'s tail and from the page's own
  `<meta name="description">` — two more copies of one claim, each read as
  "card wording" and "SEO text" rather than as the claim they are. Lesson:
  measure the SENTENCE across the repo, not the component that renders it; a
  component is a place, and a claim has as many places as it has copies. The
  gate leg is shaped by that — the positive checks bind the two prose
  surfaces, but the ban on "not yet ingested" runs over the WHOLE page HTML,
  so a fifth copy is caught without anyone remembering it exists. Second
  lesson, same shape one layer down: the absence is now published as the
  probe's RULE (`site_meta.org_absences`), so the page renders one sentence
  per recorded case — an unrecorded org still gets "not yet ingested", which
  is the one state that wording is true of.

- **2026-09-18: two true ratios, no reconciliation, and a four-year-old
  attribution nobody re-measured (PM-S3 row, Task 21b).** `/flow/` published
  "384 of 444 crosswalked PEs" and `/district/` "200 of 1,938 programs
  currently crosswalkable". Both were correct and they answer different
  questions — the bridge counts program elements carrying a published link
  that ALSO carry FY2026 request dollars; the district view counts elements
  with a high-confidence link whose award records a place of performance.
  They are not even nested: **34 of the 200 sidecar programs are absent from
  the 384**, because the FY2026 books carry no request dollars for them.
  Nothing on the site said so, so a reader comparing the two pages could not
  tell a different question from a contradiction. `lib/corpus`'s
  `getCrosswalkCounts()` now declares all five counts with what ONE unit of
  each is — the same shape `getCorpusCounts()` gave the five corpus sizes —
  and `/coverage/#crosswalk` publishes the list.
  The second half is the lesson. `/district/`, its detail pages, its money
  column ("DARPA place-of-performance $") and `/methodology/` all credited the
  linkage to "the DARPA crosswalk". Gate 14 leg cm retired that exact claim on
  `/coverage/` on 2026-09-01 and **these five surfaces were missed**, because
  the retirement was scoped to the page the finding was reported on rather
  than to the claim. Measured the same day from the shipped sidecars: 92 Navy,
  59 Air Force, 22 Army, **14 DARPA**, 6 MDA, 4 OSD, 2 SOCOM, 1 DISA. Gate 24
  leg (p3) now recomputes that mix from the sidecars' own headers and rejects
  prose handing the crosswalk to an organization holding under half of it —
  run read-only against the 2026-09-12 build it returns exactly those three
  sentences and nothing else, across five pages carrying 122 DARPA mentions.
  Third lesson, small and expensive: the replacement prose wanted to say the
  mechanism was "hand-adjudicated in both cases", which #109/#110 had already
  measured false — 708 of the 768 links published at high come from the
  announcement path and carry no per-link adjudication. The tier sentence is
  the one a fix is most likely to overstate, because the fix is written by
  someone who has just finished reading how good the evidence is.
  Fourth, on the gate's own shape: leg (p2) started sentence-shaped and could
  not be. Rendered text glues adjacent elements, so the first "sentence" of
  `/district/` is the whole nav plus the lede, and a sentence sweep reports
  four unrelated figures out of it. It is noun-anchored now, like leg (k2) —
  and the same glue taught a second thing, that a bare `\b` finds a word
  boundary INSIDE "pages1,936" and reports "936 of 2,562", a number no page
  states. A sweep over rendered text may lose a finding to glue; it must never
  invent one.

- **2026-09-19: the disclosure that stopped the pass short of its own residue,
  and the sample that could have quietly re-labelled a tier (Task 25b).**
  /methodology/ had said since 2026-09-02 that an LLM-alias pass covered "the
  3,840 unmatched records that carry about 88% of the residue by announced
  value; the 12,811 smaller records carrying the remaining ~12% were not
  attempted" — four literals, none derived, describing a residue whose
  selection code was never committed. Re-deriving the selection (Task 25a)
  does not reproduce it: the records that join the award lake are 32,852, the
  deterministic pass matched 4,508, and the residue is **28,344**, of which
  3,829 had been attempted — so the unattempted tail was never 12,811 but
  about 24,500, roughly **1.9×** the published figure. Wave 4 adjudicated 150
  of 306 queued chunks (11,775 records, four workflow runs), 453 distinct
  (PIID, PE) pairs survived two adversarial lenses, and the unchanged loader —
  run with ALL FOUR wave result files, because it deletes the whole
  announcement/subaward partition before inserting — published
  **1,075 announcement+lexicon** links (708 before) and 114 `subaward+lexicon`
  (113 before), with no `ContradictoryAccountError` and no guard weakened.
  Scope is a derived block now (migration 016 `announcement_llm_scope` + `load_announcement_scope.py` +
  `site_meta.announcement_llm_scope`), and gate 24 leg (q) recomputes every
  figure in the paragraph against the rendered text, in slot order, and fails
  a paragraph that renders with no pass recorded.
  The second half is the lesson, and it is about the MEASUREMENT, not the
  prose. Wave 4's links were sampled fresh — 60 survivors drawn at random,
  each judged by two independent lenses (sample `2026-09-12`, rubric
  `attribution`): 51 confirmed, 9 refuted; 55 of the 60 publish, so the
  derived pair is **48 of 55**. Loading that sample under the existing
  machinery would have made it the ANNOUNCEMENT TIER's published precision the
  moment it landed, because `_link_precision_block` takes each method's LATEST
  run: a 60-link draw from one wave would have replaced a 60-link draw over
  the whole tier, under the tier's name, with every gate green — the same
  species as the withdrawn `fpds-ap+account` figure that leg (n) exists for.
  The tier is therefore PINNED to its own 2026-09-04 draw
  (`_PINNED_PRECISION_SAMPLES`), the wave's pair is published beside the scope
  counts where the sentence says whose links it measured, and a pinned tier
  whose run judged nothing it still publishes is reported UNMEASURED rather
  than falling back. Third, an arithmetic trap the prose had to dodge: 10.9%
  of the residue BY ANNOUNCED VALUE is 44.9% of it by RECORDS, so every
  percentage clause on the page names the measure it is a share of.
  Fourth, measured after the load and not predicted by anyone: the ANNOUNCEMENT
  TIER's pinned figure still moved, 51/54 → **56/60**, and the FPDS tier's
  94/120 → **89/114**. Not one announcement-drawn verdict changed (still 51 of
  54 published). The loader upserts on `(pe_bli, exhibit, fiscal_year,
  award_piid)` with `do update set method=…, confidence=…`, so an announcement
  link lands ON a row another route already owned: **60** of the 1,189 rebuilt
  rows carry a created_at older than this run (45 were `fpds-ap` medium, 13
  `fpds-ap` low, 1 `account` low, 1 `account+subagency` medium), six of them in
  the 2026-09-04 sample. Counting each sampled link under the tier it publishes
  under TODAY — the rule built for the withdrawn `fpds-ap+account` tier — then
  moves those six figures between tiers. The lesson: this loader does not only
  ADD links, it re-attributes existing ones, so a wave's effect cannot be read
  off the announcement row count alone, and the precision table can move
  without any verdict changing.
  FIX ROUND 1 (same day), and it is the fifth lesson: the numerator left the
  denominator's population. `records_attempted` added the EARLIER pass's entry
  count — 3,840 rows over 3,832 distinct keys, taken before the lexicon grew
  — to wave 4's, and published the sum as a share OF today's 28,344-record
  residue. 8 of those entries duplicate a key and 3 of the records now match
  an owned name deterministically, so only **3,829** of them are still in the
  residue: the page had published 15,615 records / 89.4% of the residue by
  value where the true in-residue figures are **15,604 / 89.1%**, and an
  unattempted tail of 12,729 / 10.6% that is really 12,740 / 10.9%. Coverage
  overstated, the tail understated — the wrong direction under "publish the
  smaller true number", and invisible to every gate because each figure came
  from a block and the block came from a manifest. The manifest now publishes
  `earlier_pass.records_in_residue` / `value_in_residue`, the intersection,
  and the loader refuses a manifest without them. THE SPECIES: a derived
  figure is only as honest as the population its inputs share; "derived" says
  nothing about which set a number counts.
  CLOSE-OUT, 2026-09-25 (Task 1's ledger sweep) — what the rest of the
  roadmap-completion branch measured and decided, recorded here so the final
  report can point at one place. **Chain C took four runs.** Run 1
  (2026-09-19) stopped at `dbt build`: the #56 fusion tripwire
  `assert_district_programs_single_member_high_links` fired for the first
  time, because the wave-4 load gave `0145` high links under two accounts
  (1506N ×5, 1508N ×3). It fired on a LINK precondition — the three 1508N
  awards carried no place-of-performance transactions, so no district figure
  had fused and no district pair was ever split. Ruling R-C-2 kept the guard
  and added Task 27 (the district member grain). Run 2 (2026-09-19) went
  22/24: `/methodology/` 413 gzip bytes over 42,500, `/district/VA-11/` at
  171,862 / 20,457 over its INITIAL 154,000 / 20,000 (the page embedded a
  ~50 KB citation map), and two `/feed/` HHI cards on a shared code linking a
  stub → Task 28. Run 3 (2026-09-24) ran on a lake another checkout had
  rewritten that day and went 21/24 → ruling R-C-5 (adopt the 2026-09-06
  FY2026 refresh) and Task 29. Run 4 (2026-09-25) is GREEN: 24/24 site gates
  at `git_head 71d3e053` = HEAD; verify-phase3, verify-phase5b1 and
  `evals check` PASS; verify-phase5 freshness and assembly (8/8) PASS and its
  eval leg 0/48, blocked by API credit (#139). R-C-1 is spent — the
  `/methodology/` gzip ceiling went 42,500 → 43,000 in `71d3e053`, the
  branch's second and last ceiling change — and six eval answers were
  re-baselined on the adopted data (q002, q003, q018, q022, q032, q038, each a
  data move on unchanged code).
  **Run 4's figures against chain D's (2026-09-18):** the five crosswalk
  counts gate 24 leg p binds — link-universe 444 → 536, bridged-request 384 →
  461, high-confidence-links 240 → 353, district-linkable 200 → 314,
  district-linkable-unbridged 34 → 50; programs publishing an `hhi_high` band
  37 → 63 (verify-phase3 `high_only`; its floor stays 37) over 444 → 536
  concentration rows; `fct_district_programs` 392 rows / 153 districts / 203
  program elements (the pre-wave-4 figure #110 measured 2026-09-11) → 611 /
  189 / 317 at the (district, pe_bli, account) grain; citations 132,514 →
  135,586. Run 4 alone: `feed.json` 1,745 cards,
  28 concentration cards withheld on 0145, 3010 and 3215 and 6 published under
  2292-WPN; `flow_chart.json` 582,482 bytes under its unchanged 614,400
  budget; link adjudication 9,588 of 12,917 (8,475 unpinned) and High 60 of
  1,133 (announcement 1,074, a match basis on 748); link precision
  announcement 56/60 (pinned to 2026-09-04), fpds-ap 89/114, subaward 53/60,
  account+subagency 0/60, and wave 4's own draw — 48 confirmed of the 55 that
  publish, of 60 drawn. Page weights on the final build: `/methodology/` 153,970 / 42,910
  against 155,000 / 43,000 — 87 gzip bytes under the ceiling at the stamped
  42,913, 90 on the final build; `/companies/` 700,649 / 68,994 against
  710,000 / 69,000 — 1 byte of stamped headroom and 6 on the final build, and
  build-id jitter alone reddens about 0.1% of rebuilds, so any change there
  needs a same-page trim or an owner-ruled raise; `/data/` 174 left;
  `/coverage/` 99,824 / 20,442 against 103,500 / 20,750 (Task 26 reverts its
  maxRaw to 101,500, R-D-2 as amended — done in the Task 26 fix wave,
  2026-09-25, `site/scripts/gates/build.mjs`); `/district/VA-11/` 122,480 / 17,377
  under the never-raised 154,000 / 20,000. verify-phase5b1's row-label line,
  verbatim: `row labels: sampled=5 checked=5 fallback_summary_row=0
  fallback_pe_line=0 fallback_title_match=0 unreadable=0 skipped_no_detail=0
  skipped_null_bbox=0 toa_basis_checked=0 toa_basis_compared=0
  toa_not_found=0` (#126 says why `toa_basis_checked` is 0).
  **Tasks and rounds the controller added beyond the plan's 26, all
  complete:** Task 6c (2026-09-11), #109's opening sentence derived and gated
  — `61907d78`, `64d5cac9`, `640320e0`, `19c53c6b`, `2a20abcc`, `02f24a47`;
  round 1 `7b516f6b`, `8409114a`, `0716cfe0`, `136abf35`, `696d4cc2`,
  `951c4992`; round 2 `0f5c08e7`, `f5c52110`, `2e0d20c4`. Chain-B fixes 1–3
  (2026-09-12) — `8bf389fc`, `e99ca61b`; `706a0167`, `f6a16648` (superseded by
  `1ce12269`), `c498c286`, `1ae25903`; `46e2cb67`, `341ff934`, `4682579e`,
  `cc399d74` (3010-SCN regenerated through the Batch API). Task 9b
  (2026-09-12, fix round 2026-09-18), member pages publish their own J-book —
  `fba82630`, `c056d369`, `9ad22ec0`, `1faade33`; `60d0ca8e`, `659b2408`,
  `ae632b8b`. Task 17c (2026-09-12), the absence sentences — `428623ad`,
  `16ee1ecd`, `6a5c91ba`. Group D polish (2026-09-18) — SITE `79d88b47`,
  `ee9dbee0`, `89955a32`, `15d97f64`; PY/DOCS `e965c1cb`, `4898547e`,
  `1c65ebbf`, `07bb67ee`, `9c572910`, `0aa96524`. Chain D restamps and fixes
  (2026-09-18) — `2573de1b`, `4c965d3e` (with R-D-2's one dated `/coverage/`
  raise), `54798b73`, `d810f938`, `b6bc8458`, `da499773`, `ab6d58fd`. Group C
  polish (2026-09-18) — `bebd4d38`, `679e01d4`, `b378dcad`, `1e2a343e`,
  `90f0581e`, `a15984fc`. `collect` hardening (2026-09-18/19) — `0525278d`,
  `f007b8d0`, `abd1cca5`; Task 25b fix round 2 `16a38cdc`; chain C run 2's
  docs literals `e510d19d` (2026-09-19). Task 27 (2026-09-19), the district
  member grain, rulings R-27-1..8 — `d3a4bf0f`, `f3fd8fff`, `376a1b61`,
  `43438836`, `bd81dfea`, `f700f6d5`, `4480ccde`, `9a34a4c5`, `b9825ff4`. Task
  28 (2026-09-24), the feed follows `_concentration_owner` and district pages
  resolve citations from the cite shards with an opt-in list of the ids they
  render (R-28b-4) — `7df5152a`, `a0b7f72f`, `082b86c4`, `406b5cc8`,
  `7b1cba78`, `9edc9af4`, `c9eb600d`. Its corrected fact, re-measured
  2026-09-25 for #130: no withheld figure a page or card would print mixes two
  programs' money (0145-PANMC's links are $0-obligation IDVs), while the
  ALL-LINKS figure on 3010 and 3215 — printed on no page or card, but shipped
  under the bare code in the downloadable `fct_program_concentration.parquet`
  (run-4 export: 3010 hhi_all 9,329 over $7.78B, 3215 hhi_all 3,010; scope
  added 2026-09-25, Task 26) — does pool money; `a0b7f72f`'s
  body says "fuses", and `71d3e053`'s body records the correction instead of
  a history rewrite. Task 29 (2026-09-24/25), adopt the refresh (R-C-5) —
  29S `649ec9d9` (fourteen rendered word-glue sites after inline elements,
  and a sweep that catches the shape), 29P `b5691ca5` (manifest provenance;
  the flow payload 615,051 → 582,482 bytes without touching its budget;
  reviewed family labels), fix round `cfcc9391`, micro-fix `118228f8`. Chain C
  run 4's restamp `71d3e053` (2026-09-25).
  **Also recorded.** The shared-lake incident (2026-09-24): the main
  checkout's session (`codex/f15-family-browser`, commit `3786a6e9`)
  re-synced the FY2026 contracts and assistance archives, rebuilt
  `entity_xwalk.parquet` and rewrote the DuckDB lake and `data/site/json`.
  Runs 3 and 4 ran the FULL chain and redefined the shared views to this
  branch's models (R-C-4), and run 4's export overwrote `data/site/json` and
  `data/site/data`, so the other session must re-run its own `govbudget
  build` and export before it trusts its lake; what the adopted lake carries
  that main cannot rebuild is #133. The whole-suite rule (2026-09-19, after
  25b's glue miss): every implementer and fix round ends on the WHOLE
  `npx vitest run` and the whole pytest set for the package it touched. Task
  21c also fixed `site/src/__tests__/pagefind-text-separators.test.tsx`, which
  had pinned the shouted filing title; the program-page strip it did not
  reach is #125. A dating note: several Status stamps this branch wrote carry
  the plan's nominal dates, not their commits' — #78, #80, #84, #85, #88 and
  #106 say 2026-09-05 and #9 and #83 say 2026-09-10, where every one of their
  commits is dated 2026-09-11; #10's "owner stamp 2026-09-10" is `d799e794`,
  2026-09-12; and #89–#105's "open (2026-09-10)" were filed by `628bdee2`,
  2026-09-11 (checked with `git log`, 2026-09-25). The stamps stay as
  written; this line is the correction.
  **Owner decisions this branch leaves, each a dated open entry:** #107 (keep
  publishing the `account+subagency` tier at 0/60?), #110 (1,073 high links
  with no per-award record), #130 (withhold shared-code concentration by links
  or by money), #132 (HHI band vintage), #140 (announcement evidence
  overriding an FPDS mapping — the 60 re-attributed rows), #141 (a
  LORELEI-style attribution rule), #134 ("Data as of <build date>"), #135 (the
  RTX family's Rockwell Collins Australia key), #137 (four refused registry
  names), #133 (the R-C-6 reconcile dependency, before merge), #10 (the
  SAM.gov Personal API key), #8 (loading the scheduler and the first real
  refresh), and #139 — the Anthropic API credit top-up the deploy waits on.
  TASK 26 CLOSE, 2026-09-25 — the final review, its one fix wave, chain E.
  **The final whole-branch review** (workflow `wf_4c337097-fc1`, 78 agents
  over 205 commits / 460 files, `5dd7fb04..a774c2c5`) confirmed 15 findings
  that come to 11 distinct defects, rejected 8 (each then treated as a minor
  candidate) and listed 67 minors. The CRITICAL: five shared-code member
  pages rendered "this program's awards haven't been crosswalked at high
  confidence" while listing high-confidence awards
  (`site/src/lib/coverage.ts`). The others were Important — sentences on
  /companies/, /methodology/, /district/ and /coverage/ that were false,
  stale, unscoped or undated (the district partial-year note would have turned
  false on 2026-10-01), a docs mirror left behind, the
  jsx-glue sweep blind to a JSX comment that eats a space,
  `tests/test_roadmap_backlog.py` red at the tip, a gate message still
  typing "60 of the 768", and the precision CLI without the exporter's
  announcement pin. **ONE fix wave**, three implementers on disjoint files
  in parallel — A (Python, dbt, scripts, seeds, tests), B (`site/src` and
  `docs/methodology.md`), C (`site/scripts`, `docs/superpowers`, the backlog
  test) — landed `2fbb0fca`, `f7f66f90`, `db7ea6b8`, `2631383e` and
  `2ef7471e`. B cleared the CRITICAL by giving the four shared-code members
  that hold their code's district rows (0145-APN, 2292-WPN, 3010-SCN,
  3215-WPN) the bare code's flow view, so 314 pages draw a view against 314
  flow files; a page without a view now states its own reason, and the site
  build fails if a shared-code flow file's district rows name two members
  or none. The wave filed its deferrals as
  #143–#164. Its scoped re-review (`wf_3f0d75e6-955`, 21 agents, over
  `a774c2c5..2ef7471e`) confirmed five more — the /district/
  reconciliation's "314 of 1,938 programs" (#163) and its /methodology/
  twin; the follow-the-dollar chart labelling every account node "RDT&E
  appropriation", procurement views included; a sitewide partial-year note
  bound to the calendar (~2,587 pages); /downloads/ counting 204 PDFs where
  225 ship (#164); and #159 filed open though already fixed — and round 2
  fixed them in `35bff576`, `8ebdfbd3` and `594d1f0c`. The round-2 scoped
  check (one read-only agent) found every item addressed and nothing new at
  Critical or Important. **Chain E is GREEN at `cf37866d`**, its restamp of
  `site/scripts/gates/build.mjs` (no ceiling or floor changed): 24/24 site
  gates at `git_head cf37866d`; verify-phase3, verify-phase5b1 and `evals
  check` (43 ok / 0 stale / 5 skipped) PASS; verify-phase5 freshness and
  assembly (all 8 legs, 5b3 included) PASS and its eval leg 0/48 at $0.00,
  blocked by API credit (#139). Its export reproduced run 4's figures
  (citations 135,586; `feed.json` 1,745 cards; `pdf_count` 204;
  `flow_chart.json` 582,482 bytes). Its first `export-site` attempt failed
  on exhausted TCP ports and the Unix-socket retry passed; LAUNCH.md Step 1
  now carries the workaround. Final page weights (gate 1): `/methodology/`
  153,570 / 42,934 against 155,000 / 43,000 — 65 gzip bytes under the
  ceiling at the stamped 42,935 and 66 on the final build; its gzip rose 22
  bytes on 400 fewer raw bytes where the wave had predicted −111, and R-C-1
  is spent, so the next /methodology/ sentence needs a same-section trim.
  `/companies/` 700,393 / 68,854 against 710,000 / 69,000 — 145 stamped and
  146 final (it was 1); `/data/` 171 left; `/coverage/` 99,824 / 20,449
  against 101,500 / 20,750 — 301 gzip and 1,676 raw left;
  `/district/VA-11/` 122,646 / 17,410 under the never-raised 154,000 /
  20,000. The closing docs commit closes #163, adds a dated addendum to
  #164, files #165 (chain E's nondeterministic `top_family` print), and
  puts a dated note of which basis the warehouse fills (all 536 rows vs 63)
  beside the concentration paragraph in `docs/methodology.md`; the
  paragraph itself is bound verbatim to /methodology/ and was not changed.
  Deploy, merge to main, push and the subtree split wait on the owner's
  Anthropic API credit top-up (#139). The verified build is chain E's;
  because the docs-only closing commit moves HEAD past `cf37866d`, the
  deploy rebuilds and re-verifies at the pushed HEAD first.

## Improvement backlog (content + tech; pulled into phases as they fit)

- **#70 Collision-key program pages (E3).** 8 numeric pe_blis carry two
  programs each (e.g. `3010`); all award links on them are excluded (53 wave-3
  pairs incl. every ADNS link; earlier FPDS/DARPA exclusions). Needs
  account-qualified program routes so a link can name which program.
  **Status:** CLOSED 2026-09-04 — E3 composite slugs reused (no new route); 10 account-split keys are link targets when the award's accounts identify one member (86 links on 7 member pages; 3 org-split keys stay excluded); migration 014; gate 21 leg n with a measured floor.
- **#71 Announcement source kind in the citation panel.** Announcement- and
  subaward-derived links carry provenance in `rationale` text (article id,
  date, URL / subaward number) but the cite panel has no first-class
  "announcement" kind (URL + archive snapshot + sha256 from the manifest).
  **Status:** CLOSED 2026-09-04 — `announcement` citation kind (defense.gov URL, Wayback snapshot, sha256, match_basis; migrations 012/013); 708 rows; exporter fails loudly without a source row; subaward links still cite the derived row (see #84).
- **#72 Held-out precision study on the new link tiers.** The retired tier was
  measured (9.1%); the FPDS-AP, announcement and subaward tiers rely on the
  adversarial refute pass as their precision control. Run a hand-adjudicated
  held-out sample and publish the number either way. **Status:** CLOSED 2026-09-04 — 300-link held-out study (migration 011); FPDS unique-line high tier withdrawn at 34/60; figures derived onto /methodology/ by the tier each link publishes under today (fpds-ap 94/120, announcement 51/54 (six sampled links unpublished by the later money-color guard drop out, 3 confirmed + 3 refuted), subaward 53/60); account+subagency reported as unmeasured for program attribution (its stratum was judged on the rule, not attribution — see #79).
- **#73 /feed/ pagination UX.** The page is a 75-per-section digest with a
  truncation note; a client-side expand (the ProgramAwards pattern) would let
  readers reach the full set without RSS. **Status:** CLOSED 2026-09-04 — client-side expand per section (lookup props, byte-identical client twin pinned by a parity test); /json/feed.json was never copied to public/ (live 404) — fixed and gated.
- **#74 SAM.gov solicitations leg.** Official API key-gated; unauthenticated
  search returns 0 for bare PE codes. Needs a real spike (archived-index
  params, FBO-era Internet Archive fallback). Task chip filed with probe
  notes. **Status:** CLOSED 2026-09-04 — NEGATIVE: 0/10 bare-PE queries, 75 solicitation records + 3 archived FBO pages regex-scanned, 0 PE-code hits; key-gated attachment/SOW text untested (docs/superpowers/reviews/sam-solicitations-spike.md).
- **#75 Mechanical crosswalk v1 debts (medium tier).** The 9,142 DARPA
  `account+subagency` rows still carry v1 mechanics: hardcoded DARPA clause,
  calendar-year (not federal FY) filter, full-award obligation attributed to
  the account. Fix before any non-DARPA mechanical run. **Status:** CLOSED 2026-09-04 — federal-FY filter, single-account obligations, seed-driven aliases, conditional upsert guard (mechanical re-runs cannot overwrite evidence-graded rows), mart demotes unadjudicated mechanical high → medium. The brief's unbounded DARPA re-run cross-joined editions × the decade lake (+2.2M rows, reverted) — see #78.
- **#76 Program-count denominators.** 1,739 (parquet, correct per #35) vs
  1,741/1,753 on some surfaces; reconcile to one build-derived value.
  **Status:** CLOSED 2026-09-04 — registry-derived denominator only; stale literals demoted to dated comments.
- **#77 In-table medium caveat.** Related Awards tables disclose the tier on
  the badge and /methodology/ only; a one-line in-table note ("same account +
  same agency, not evidence this program paid") would stop presence-in-table
  reading as attribution. **Status:** CLOSED 2026-09-04 — in-table caveat true of every medium species (account/sub-agency association; FPDS tag or subaward description establishes the program, not the line); gate 21 leg m.
- **#78 `jbooks crosswalk` has no default FY window.** With the lake at ten
  fiscal years, an unbounded `--org` run cross-joins every line-edition against
  every award of the org's account (177 × 13,216 for DARPA). Add a default
  window (the line's own edition FY) or a per-edition line filter, and a
  projected-row dry-run abort. **Status:** CLOSED 2026-09-05 (code) — default window = each line's own PB-edition FY (federal FY, resolved per line); `--fy-start/--fy-end` required together (one bound alone exits 2); `--all-years` is the opt-in to the old unbounded shape; EVERY run (default included, per the 2026-09-11 controller ruling) is planned first by `plan_crosswalk_org` and aborts above 500,000 projected pairs unless `--yes`; `--dry-run` prints pairs per org and edition FY and writes nothing. Data unchanged: the 124,502 mechanical DARPA rows (all `fiscal_year=2026`, rationale "all loaded award years") are still in `budget_line_awards`; the re-run under the new default (plans 761,029 DARPA pairs, measured read-only 2026-09-05, so it needs `--yes`) is the controller's call and is what #85 is blocked on. Canonical invocation: LAUNCH.md Step 0.
  *From branch `codex/f15-family-browser`, merged 2026-09-25:* **Status on that branch:** CLOSED 2026-09-24 — per-edition federal-FY defaults, paired bounds, edition selector, dry-run, aggregate 100,000-row default cap and atomic writes; live FY2026 DARPA preview 39,192 candidates, zero writes.
  *Addendum 2026-09-25 (Task 26 fix wave; A's review deferral):* the published
  grain is not asserted. `budget_line_awards` is unique on (pe_bli, exhibit,
  fiscal_year, award_piid), so the `--yes` re-run above — any run over
  several PB editions — writes one (pe_bli, award_piid) pair once per
  line-edition whose window the award falls in (under the default window,
  once per edition year its transactions fall in; under `--fy-start/--fy-end`
  or `--all-years`, once per matching edition — `_line_window`,
  `src/govbudget/jbooks/crosswalk.py`; qualified in fix-wave round 2), and
  nothing asserts the pair grain downstream: `fct_program_concentration` would add that award's dollars
  twice to its family and program sums (the district marts join through a
  `select distinct` over award, program, account, title and organization, so
  they double only where the edition rows carry different labels — #152).
  Unique today
  only because the table holds no such run (measured read-only 2026-09-25:
  12,601 `fct_budget_to_awards` rows over 12,601 distinct pairs; its 9,547
  mechanical rows all at fiscal_year 2026). Land backlog #151 before the
  re-run; LAUNCH.md Step 0 carries the warning.
  *Integration 2026-09-25 (merge f0ed21eb):* the 2026-09-24 CLOSED line above
  describes the live branch's crosswalk, which the merge did not carry; the
  merged crosswalk is this branch's reviewed implementation
  (`src/govbudget/jbooks/crosswalk.py`, `src/govbudget/cli.py`). The CLI plans
  every organization before it writes anything and aborts when the projected
  total across all of them exceeds `ALL_YEARS_ABORT_ROWS` = 500,000 pairs
  unless `--yes`; there is no 100,000-row cap and no `--max-rows`. Writes are
  not atomic across a run: `crosswalk_org` commits each budget line's upserts
  on that line's own connection. An award is a candidate when its
  funding-account list contains the line's account (`like`), and
  `matched_obligation` sums only the transactions funded from exactly that
  account. Carried from the live branch: the edition selector (`--fiscal-year`
  plans and writes one PB edition's lines and never widens a line's award
  window) and window validation (a reversed window or a year outside
  1900–2200 exits 2 before any database connection). Its FY2026 DARPA preview
  (39,192 candidates) came from that branch's planner. Identities carrying two
  or more accounts: #170.
- **#79 Precision study rubric.** `link_precision_samples` needs a `rubric`
  column; strata judged on different questions must not publish side by side.
  Re-adjudicate `account+subagency` against program attribution (its first
  study confirmed only that the rule fired). **Status:** CLOSED 2026-09-11 — migration 015 `rubric` column ('attribution' | 'rule-fired'; the 2026-09-04 account+subagency rows stamped rule-fired, the other four strata attribution); exporter and CLI filter on rubric, `_UNRUBRICKED_PRECISION_STRATA` deleted; each tier's figure comes from the latest run that judged it (a run may re-judge one stratum, nothing pools); account+subagency re-drawn (60 links, seed 20260905, sample `2026-09-05`) with attribution packets (award description + program narrative/projects/lexicon + lake evidence) and judged adversarially on program attribution — attribution judge + skeptical refuter per packet, arbiter on disagreement, default refuted, 120 judgements, 0 disagreements — at **0/60** (loaded 2026-09-11; the 2026-09-04 rule-fired rows kept for audit, 55/55 unpublished); /methodology/ prints the figure beside the tier's "association, not evidence this program paid" sentence and the rule-fired history sentence retired itself off the derived unmeasured list; gate 24 leg n requires the paragraph to name the rubric. Owner call on what the tier does next: #107.
  *From branch `codex/f15-family-browser`, merged 2026-09-25:* **Status on that branch:** CLOSED 2026-09-24 — restored the existing explicit-rubric migration, loader and reviews; shared pair-grain tally reads actual published mart membership and pins tier versus wave sampling frames. No new verdicts invented; methodology review coverage and exclusions are derived.
- **#80 Owner call: should `fct_program_concentration` (program-page HHI +
  program_dollars) be high-only?** It is high+medium by construction; 158 of
  438 programs' blocks rest entirely on medium links, and medium is now
  dominated by the unmeasured account+subagency tier (#79). Prose is honest
  meanwhile. **Status:** CLOSED 2026-09-05 — publish BOTH bases (controller ruling, owner may override): mart columns `*_all` (pre-#80 figures, fids unchanged) and `*_high` (high-confidence links only; `hhi_high` NULL below 3 awards across 2 families — 57 of 444 programs clear it, 225 fall below, 162 have no high link); the card and the "Who gets it" line headline the high-only figures with a tier chip and print the all-tier figures on a labelled second line, or headline the all-tier figures and say so; new derived fids for the high-only figures with formulas true of each basis; verify-phase3 floor leg (+ a 1e-6 HHI ceiling epsilon that fixed a pre-existing intermittent red), feed leg (l) requires one basis-stamped badge, q023 re-pointed (it was already stale). **Amended 2026-09-11 (fix round 1):** the floor now also requires 2 families holding POSITIVE dollars (`positive_family_count_high`, published) and positive `program_dollars_high`, and withholds `top_family_high` with the index — 37 of 444 clear it, not 57; and only the high-only basis is RENDERED. Below the floor the card, the "Who gets it" line and the dossier fact bundle publish nothing rather than substituting the all-links figure (`account+subagency`, 0/60 on program attribution, #79) — the `*_all` columns, fids and formulas are unchanged and still ship in the download, on /methodology/ and in citations. Gate 3's floor leg asserts an invariant the mart cannot satisfy by construction plus a dated `high_only_rows >= 37` floor; feed leg (l) accepts a withheld destination and rejects an all-links band; q023 re-measured to `2307, RTX` (0603882C was one of the seven single-positive-family rows).
- **#81 FeedCardItem shared shell.** The client twin (`feed-card-item-client.tsx`)
  is pinned by a byte-identical parity test, not by construction; extract
  `hhiScopeNote` and `Fy26SplitNote` to client-safe files and render one shell
  from both trees. **Status:** CLOSED 2026-09-12 — one `<FeedCardItemShell>`
  (the headline is its only slot) rendered by both trees; `hhiScopeNote` →
  `src/lib/hhi-scope-note.ts` and `Fy26SplitNote` →
  `components/fy26-split-note.tsx`, both called by the shell; hand-copied
  twins deleted; parity test kept, shell single-source test added, and
  `vitest.client-graph.config.ts` runs the client twin against the REAL
  `server-only` (wired into `npm test`).
- **#82 Collision member pages: account in the title block.** E3 pages render
  the member title but not its appropriation; the gate-21 assertion the #70
  plan wanted needs that UI. Also: district cards and filing mentions on shared
  codes still link the bare-key stub, and a withheld concentration block
  suppresses the named-prime/lobbied-by fallback on 3010's members.
  **Status:** CLOSED 2026-09-11 — account-split members name their own appropriation in the title block (`[data-program-account]`, `ProgramHeader.accountSplit` derived from the stub's own `stubDimension`; gate 21 leg n checks 5-7 with a dated 16/20 page floor, and the org-split members and the bare stub render none); district cards link the member whose mart title names it (`member_slugs_by_title`; identical member titles keep the chooser) and filing mentions carry `shared_code` and say the link opens a chooser; `named_primes`/`lobbied_by` are keyed by slug and read the member's own `_concentration_for`, `_awards_for` and dossier, closing three bugs (a slug-named dossier's primes could never reach its page; a bare-key figure no page publishes suppressed the lobbying tier on both members; #80's awards guard could not address one member). A figure withheld because more than one member is linked is now STATED on the WHO card (`summary.concentration_withheld`, `data-who-withheld="shared-code"`, `sharedCodeWithheldReason` beside #80's two strings) instead of "the crosswalk is silent here" above a five-row Related Awards table — true on 3010-SCN and 3010-OPN. No page changes tier on today's corpus.
  **Addendum 2026-09-12 (the narrative axis).** The sweep above covered the header, the WHO strip, member links and district links; it did not cover what the page says the J-book says. Measured read-only on the shipped corpus: all **13 of 13** shared codes published IDENTICAL `narratives` and IDENTICAL `details` on every member (55 narrative and 139 detail fact ids on more than one member page) — /program/3010-SCN/ rendered the Shipboard Tactical Communications mission paragraph and the OPN volume's money under the LPD Flight II heading, every citation resolving, because each row is individually true of something. Root cause: `_narratives_with_links` and the sidecar's `details` read a bare-`pe_bli` index, and the `owns_detail` gate that used to separate them stopped separating anything in Wave 5 (all ten account keys now carry real detail on BOTH sides). Now keyed by the member's own J-book DOCUMENT — its appropriation (account axis, `budget_line_details.account`, which is also how a narrative learns its account since `detail_narratives` has no such column) or its component (organization axis, `jbook_documents.org`) — through the same `split_key` `_awards_for` and `_concentration_for` use; the /years/ matrix's project rows and the detail display-dedupe key move to the same identity (both measured no-ops today), and `programs.json.narrative_count`, `fy2026_absent.has_narrative` and the dossier bundle's `projects`/`narratives` follow the sidecar. After: **0 of 13** codes cross-publish; each member publishes its own volume only (118 → 53 narrative rows, 298 → 134 detail rows across the 27 member pages). Seven rows the PROC_DoDEA volume files under code '30' belong to no member page (DoDEA has no `dim_programs` row) and now publish on NEITHER, with a dated count in the export log — never on all three. Lobbying `mentions` are bare-keyed in the mart (`fct_program_lobbying` has no account and no organization column, and nothing in a Senate LDA filing could populate one), so the exporter decides PER ROW from the mart's own evidence which member each is about: a `pe_literal` row names the budget LINE itself and is evidence for every program using the code (both members render it, and the /filing/ page already carries the shared-code note); a `multi_token`/`alias` row qualified by matching ONE title's terms and publishes only on the member whose own `dim_programs` title carries every one of them — on the other member the rendered badge ("2+ distinct, non-generic words from this program's title") would be false. The sidecar declares that basis per evidence tier in `mentions_shared_code`. Gate 21 leg n gains check 8 (no narrative or detail fact id on two member pages; every mention's basis declared, with the title test re-derived from `programs.json` titles so a wrong declaration fails) with a dated do-not-lower floor of 22 against a measured 27 member pages publishing their own J-book rows.

  **Fix round 1, 2026-09-18 (the mention axis).** The addendum above originally declared one blanket rule for mentions — "an LDA filing names a budget LINE … so it is evidence for every program using the code" — and gate 21 leg n check 8 exempted repeated mentions on the strength of it. That rule is true only of `pe_literal` rows. Measured read-only on the shipped corpus: **7 of the 76** mention identities on shared codes are `multi_token` rows matched against ONE member's title — /program/0145-APN/ "F/A-18E/F (Fighter) Hornet" rendered **5** rows chipped `General|Purpose` (the sibling 0145-PANMC is "General Purpose Bombs") and /program/1350-WPN/ "Missile Industrial Facilities" rendered **2** chipped `Weapons|Ammunition` (sibling "Infantry Weapons Ammunition"), each badged "matched 2+ distinct, non-generic words from this program's title" beside a title carrying neither word. 2292's two members have identical titles, so all 18 of theirs are true on both. Narrowed to the per-row rule quoted above (0145-APN −5, 1350-WPN −2, 2292 unchanged at 18/18, 20/30/500 unchanged — they are `pe_literal` throughout; rows matching no member's title publish on NEITHER, dated count in the export log, measured 0 today), `mentions_shared_code` now declares `{evidence_kind: basis}` rather than `true`, and check 8 exempts only the "code" basis while re-deriving the title test for every other row from `programs.json`'s own titles. The matcher's own last-title-wins on shared codes is **#115**.

  **Addendum 2026-09-19 (Task 27).** The title-keyed `member_slugs_by_title` is replaced by the account-keyed split key on district rows; 2292 (identical member titles) now links its member page — exactly one district row changes its link, AZ-07's, from `/program/2292/` to `/program/2292-WPN/` (0145, 3010 and 3215 publish distinct member titles, so the title proxy already reached their member pages; what changes for their 10 rows is the rendered code and the fact id).

  **Addendum 2026-09-25 (ledger sweep; Task 9 review rider).** The district member link is no longer fixture-pinned. The Task 9 review found 0 of 392 district rows on a shared code (true of the pre-wave-4 mart); after the wave-4 load and Task 27's grain change, chain C run 4 (2026-09-25) measured **11** of the 611 `fct_district_programs` rows on shared codes — `0145` ×2 → `/program/0145-APN/`, `2292` ×1 → `/program/2292-WPN/`, `3010` ×1 → `/program/3010-SCN/`, `3215` ×7 → `/program/3215-WPN/` — each carrying its own split key, which gate 9 leg g checks on every row.

  *Integration 2026-09-25 (ruling R-INT-6):* on an account-split code a
  narrative publishes on a member only when its document's organization is
  that member's organization and the document's detail rows under that
  organization name exactly that member's appropriation. This is the live
  branch's rule (`_narrative_member_key` at 81929a6b), stricter than this
  branch's 2026-09-12 key above, which on the account axis reads only the
  document's appropriation. The merged exporter applies it as a guard in
  front of `split_key` (`_write_all_sidecars`, `src/govbudget/export_site.py`).
  A refused narrative publishes on neither member and is counted in the #82
  census print as `<code>/<account>@<org>`, pinned by
  `test_the_narrative_census_counts_each_org_guard_refusal`
  (`tests/test_program_member_enrichment.py`). Measured read-only 2026-09-25
  against Postgres and the shipped narratives parquet: the 10 account-split
  codes have 20 member pages, all organization N; all 40 PB2026 narratives
  on those codes are organization N, and 0 are refused, so no page changes.

  *Integration 2026-09-25 (ruling R-INT-9):* the mention axis above (the
  2026-09-12 addendum's per-row rule and fix round 1's
  `mentions_shared_code` basis) is superseded on every member page of a
  shared code. There the exporter ships `mentions` empty, `lobbied_by` null
  and `named_primes` empty, as production does (the live branch's 2c7ebbb0
  and c2ac0b90), and the Lobbying Mentions section says the code is shared
  by more than one budget line and no lobbying match is assigned to the
  member. The narratives, details and title block above are unchanged. The
  premise of the superseded rule, that a `pe_literal` row names the budget
  line, is false for numeric codes: each of the 51 `pe_literal` rows on 20,
  30 and 500 matched a bill or public-law number, a date, or part of a
  larger figure (a spectrum quantity) (final integration review, findings #1
  and #11, 2026-09-25). Withdrawn with it,
  measured on the chain F export's sidecars on 2026-09-25: 171 mention rows
  on 11 member pages (`pe_literal`: 22 on each of 20-DTRA and 20-DCSA, 26 on
  each of 30-OSD, 30-DMACT and 30-DTRA, 3 on each of 500-DHRA and 500-DLA;
  `multi_token`, the title-basis rows fix round 1 kept: 5 on 0145-PANMC, 2
  on 1350-PANMC, 18 on each of 2292-PMC and 2292-WPN), and the lobbying
  answer to "Who gets it" on the 7 members of 20, 30 and 500. No member
  carried a named prime. Pinned on the page side by
  `site/src/__tests__/program-split-lobbying-withheld.test.tsx`, whose
  export check stays red until export-site re-runs with the R-INT-9
  exporter, and in the build by gate 21 leg n check 8(b) (review round 2,
  2026-09-25), which fails a member on any lobbying row, lobbying or J-book
  answer or named prime whatever its sidecar declares, and requires the
  empty-state sentence on every member page. Run read-only against the
  chain F export and the 42eed1e4 build, it fails exactly these 11 pages
  (65 findings); the check 8 it replaces passed them.
- **#83 Two definitions of "account-split"** (`scripts/collision_keys.py` vs
  `_ProgramIdentity.is_account_split`) — fail-closed today; unify.
  **Status:** CLOSED 2026-09-10 — one rule, `govbudget.jbooks.collision_keys.classify_shared_keys` (an axis resolves a key only when every row's value is present and pairwise distinct; ACCOUNT, else ORGANIZATION, else UNRESOLVED); `_ProgramIdentity` and both link loaders import it, `scripts/collision_keys.py` deleted; the 13 live keys classify as before (10/3/0, 27 composite slugs); an unresolved key now stops export-site (`UnresolvedSharedKeyError`) and is excluded by the loaders; identity of the three callers' function objects and the two formerly divergent shapes are pinned by tests/test_collision_keys.py.
- **#84 Subaward citation kind.** `subaward+lexicon` links (67) still cite the
  generic derived row; `award_link_sources` already records the subaward number.
  **Status:** CLOSED 2026-09-05 — `subaward` citation kind for all 113 subaward+lexicon links (67 + the 46 unlocked by #70): official_url = the prime award's USAspending page (USAspending has no subaward-level page; the record's own permalink points at the prime), query_body {match_basis, subaward_number, subawardee} from `award_link_sources` + the subawards lake, formula kept (gate 24 leg n); exporter fails loudly on a missing source row / lake row / URL; `SubawardCard` states the basis and the one-hop caveat; `verify-phase5b1` gate 1 verifies the kind with anchored URLs; fact ids unchanged. `migrations/012_award_link_sources.sql`'s "these links keep the generic derived citation row" comment is now historical — an applied migration is never amended.
- **#85 Mechanical crosswalk nondeterminism.** `crosswalk_org` selects several
  title variants per (pe_bli, exhibit, FY, account) key and the last iteration's
  token overlap wins the tag (±346 medium / +119 high on an identical re-run).
  **Status:** CLOSED 2026-09-05 — the reproducible source was `any_value()` over an award's transactions (three consecutive identical read-only runs changed the picked description for ~6,000 of 13,216 `097-0400` awards and the sub-agency for ~380), not the title variants (3 of 22,527 per-organization keys, all org F, none DARPA); both fixed: `_load_lines` takes one canonical title per key (latest document, explicit ORDER BY in `CANONICAL_LINE_SQL`) and `_fetch_candidates`/`_grade` grade every award from all of its transactions in the window (any-transaction sub-agency — controller ruling, documented; union-of-descriptions tokens; latest-transaction recipient; exact-decimal obligation). Order-independence and two-run tests in tests/jbooks/test_crosswalk.py; upsert guard byte-identical; no prose edit owed (tier sentences re-read). Live re-run + md5 check (LAUNCH.md) is the controller's step.
  *From branch `codex/f15-family-browser`, merged 2026-09-25:* **Status on that branch:** CLOSED 2026-09-24 — canonical title/recipient choice and all-transaction classification are deterministic; shuffled assignments, protected evidence and exact account identity tested.
  *Addendum 2026-09-25 (Task 26 fix wave):* that live re-run is the `--yes`
  multi-edition DARPA run #78's addendum warns about — it writes one
  (pe_bli, award_piid) pair as several rows, which the concentration sums do
  not yet guard. Land backlog #151's grain test and collapse first.
  *Integration 2026-09-25 (merge f0ed21eb):* the 2026-09-24 CLOSED line above
  describes the live branch's crosswalk, which the merge did not carry; the
  merged crosswalk is this branch's implementation, deterministic as the
  2026-09-05 line states: one canonical title per (pe_bli, exhibit,
  fiscal_year, account) key (`CANONICAL_LINE_SQL`) and every award graded
  from all of its transactions in the window, pinned by
  `test_one_canonical_title_per_key`,
  `test_tags_independent_of_transaction_order_in_lake` and
  `test_two_runs_over_same_fixtures_produce_identical_rows`
  (`tests/jbooks/test_crosswalk.py`). Account identity is not exact: an award
  is a candidate when its funding-account list contains the line's account
  (`like`), and nothing aborts when one (pe_bli, exhibit, fiscal_year,
  organization) identity carries two or more accounts — an award that is a
  candidate under two of them is upserted onto one row and the account sorted
  last sets its grade and `matched_obligation` (#170). The live branch's
  shuffled-assignment, exact-account and ambiguous-account tests were not
  carried. Nor was its scoping of the detail tokens to the line's own
  (organization, edition, account): the merged crosswalk adds the
  project-title tokens of every non-superseded detail row filed under the
  code to each of its lines, whatever the row's organization, edition or
  account (#171).
- **#86 Task-5 deferred minors:** `_ALIASES_CSV` via `config.ROOT`; upsert count
  overstates guarded skips; NULL `action_date` untested under an FY window;
  f-string SQL for `fed_account`. **Status:** CLOSED 2026-09-11 — seed path via `config.ROOT`; `crosswalk_org` returns `CrosswalkResult(written, skipped)` from the Postgres INSERT count and the CLI prints both; awards whose `action_date` is NULL or not a date are excluded under an FY window by `try_cast(… as date)` (`FED_FY_EXPR`, shared by the planner, 0 of 39.8M lake rows affected); `fed_account` and the FY bounds are DuckDB `?` parameters at both sites (`_candidate_where` returns `(sql, params)`).
  *From branch `codex/f15-family-browser`, merged 2026-09-25:* **Status on that branch:** CLOSED 2026-09-24 — configured aliases path, protected-row actual-write counts, null/invalid-date exclusions and parameterized account predicates covered in the crosswalk safeguards.
  *Integration 2026-09-25 (merge f0ed21eb):* the 2026-09-24 CLOSED line above
  describes the live branch's crosswalk, which the merge did not carry; the
  merged crosswalk is this branch's implementation, which closes the same four
  items as the 2026-09-11 line states: `_ALIASES_CSV` anchored to
  `config.ROOT`; `CrosswalkResult(written, skipped)` counted from the INSERT
  row count; awards whose `action_date` is NULL or not a date excluded under
  an FY window through `try_cast` (`FED_FY_EXPR`); and `fed_account` and the
  FY bounds bound as DuckDB `?` parameters. They are pinned by
  `test_aliases_csv_is_anchored_to_config_root`,
  `test_upsert_count_excludes_rows_the_method_guard_left_alone`,
  `test_undated_and_malformed_action_dates_are_excluded_under_an_fy_window`
  and `test_fed_account_is_bound_as_a_query_parameter`
  (`tests/jbooks/test_crosswalk.py`); the live branch's safeguard tests were
  not carried.
- **#87 Task-4 deferred minors:** gate docstring rule 5 vs code; gate accepts
  `archive_url` with null sha256; source map keyed (award_piid, pe_bli) collapses
  a second announcement row per pair; loader delete is effectively a truncate.
  **Status:** CLOSED 2026-09-11 — gate rule 5 checks `amount_text`/`amount_thousands`/`recorded_value`; `archive_url` without `sha256` fails (708/708 live rows carry both); `_index_award_link_sources` raises on a second announcement row per link (0 live duplicates); loader delete documented as a partition rewrite with a stored-vs-incoming count, `OWNED_METHODS` pinned to the deriver's guard, LAUNCH.md says pass every wave file.
- **#88 /feed/ expand payload.** "Show all" downloads the whole 862 KB
  feed.json; a per-event-type sidecar would be a tenth of that.
  **Status:** CLOSED 2026-09-05 — json/feed-sections/{event_type}.json (exporter; prune-before-emit; cap `_FEED_SECTION_CAP` published as feed.json `section_cap` and read by feed/page.tsx, no fallback; company_slug/has_program_page pre-resolved from entities_top + the program_details listing); prepare-assets 5h mirrors the directory; FeedSectionExpand fetches one section. Measured on the 2026-09-04 export against feed.json's 881,872 B: yoy_swing 23,927 B, concentration_shift 712,645 B — "a tenth" holds for yoy_swing only; concentration_shift IS most of the feed, so its expand saves ~19% raw (~28% gzipped). Gate 13 leg i directory-templated sweep (floor 2; static floor re-measured 5→4); gate 8 leg o (per rendered section: sidecar exists, card count = total − shown, one event type, lookups present; floor 1 truncated section).
- **#89 Service J-book decade backfill (PB2017–PB2025) — the GO/NO-GO was
  never taken.** 5G scoped the service books to FY2026 and named "a separate
  GO/NO-GO after this phase proves the adapter"
  (`docs/superpowers/specs/2026-07-03-phase5g-service-jbooks-design.md:76`).
  The adapter proved out — Navy through the live Playwright index fetch
  (`SERVICE_INDEX_URLS`, `src/govbudget/jbooks/service_fetch.py:44`), Army and
  Air Force / Space Force through the Internet Archive mirror
  (`ARCHIVE_CDX_PREFIX`, `src/govbudget/cli.py:309`) — and then nothing:
  `jbook_documents` holds 44 service books (Army 20, Navy 13, AF 11) and every
  one is edition 2026; editions 2017–2025 have zero rows for orgs A/N/F. The
  money is not the gap — the workbook-derived decade series already covers
  service PEs in all ten editions (`0603502N` has rows in every
  `fct_decade_series` edition). The gap is justification TEXT: narratives,
  R-2/P-40 detail and quotable page citations, which for FY2026 are 9,222 of
  the 11,679 narratives (Army 4,524, Navy 2,437, AF 2,261) and for every
  earlier edition are zero. Cost is real: the FY2026 service books are ~2.0 GB
  of the 2.1 GB `data/raw_docs/fy2026` tree, so nine more editions are ~18 GB
  raw, and both fetch paths are pinned to FY2026 folder names — each earlier
  edition needs its own verified prefix. Effort: weeks (hours for the no-go
  labelling). Owner decision: all nine editions, a recent window
  (PB2024–PB2025), or a no-go that says on /coverage/ that the ten-edition
  window is workbook-only for the services. Scoping note:
  `docs/superpowers/specs/2026-09-10-service-decade-backfill-scoping.md`.
  **Status:** open (2026-09-10).
- **#90 Cross-sibling page resolution for deduped service books — 8,021
  citations resolve `unresolved`.** Each `(family, master)` group registers one
  PDF, so a fact whose R-2/P-40 page is rendered only in a dropped sibling gets
  no page highlight and the reader is sent to "open official source" instead.
  The 5G-archive report records this as an accepted tradeoff and puts
  cross-sibling resolution out of scope
  (`docs/superpowers/reviews/5g-archive/INGESTION-REPORT.md:98-105`); nothing
  tracked it afterwards. Measured: `data/site/manifest.json`
  `skipped_unresolved` = 8,021 (export of 2026-09-05), and the unresolved
  provenance rows are almost entirely the service books — Navy 10,578 of
  14,200 amount rows, Army 3,255 of 5,523, Air Force 733 of 5,313, every
  defense-wide org 0. The detail data is complete; only the highlight is
  missing. The dropped siblings are still on disk and still in the database
  (`dedup_service_master_dups`, `src/govbudget/jbooks/service_fetch.py:384`,
  flips them to `status='superseded'`, non-destructively), so resolution
  across them is a matter of widening the candidate set and citing the sibling
  the page actually lives in. Effort: days. Owner decision: resolve across
  siblings, or keep the gap and say so where a reader meets it. Decide this
  with #89 — every service edition added scales this defect.
  **Status:** open (2026-09-10).
- **#91 5G visual-judging evidence pack was never produced.** The 5G exit
  criteria required a judged pack — one upgraded Navy page and one Army page,
  desktop + mobile, the citation panel open on a narrative and on an amount,
  plus `RUBRIC.md`, three judges, median ≥4
  (`docs/superpowers/plans/2026-07-03-phase5g-service-jbooks.md:92-94`;
  `docs/superpowers/specs/2026-07-03-phase5g-service-jbooks-design.md:67`).
  None exists: `docs/superpowers/reviews/5g-archive/` holds four live PNGs, an
  ingestion report and two book-URL lists but no `RUBRIC.md` and no verdict;
  there is no `site/scripts/capture-5g-visuals.mjs` (the capture scripts stop
  at `capture-5h-visuals.mjs`); and the archive round's own ledger cell lists
  "judge pack" among the things NOT done there
  (`docs/superpowers/ROADMAP.md:27`). The pages shipped and are live; only the
  judging is missing. Effort: hours. Owner decision: produce the pack
  retroactively, or record 5G as judged by live verification only and amend
  the evaluator framework rule that says rubric + screenshots are committed
  for human override (`docs/superpowers/ROADMAP.md:53-59`). Same root cause as
  #101. **Status:** open (2026-09-10).
- **#92 Outlay-stage flows (Treasury MTS) — ingested since Phase 0, never
  published.** 5H listed "Outlay-stage flows (MTS staged data — future)" among
  its non-goals
  (`docs/superpowers/specs/2026-07-02-phase5h-flowdown-chart-design.md:62`) and
  nothing has touched the data since: `data/parquet/mts_outlays/` holds 91,647
  rows covering 2016-10-31 through 2026-04-30, with service-level
  classifications (Department of the Army 1,224 rows, Navy 1,150, Defense
  Agencies 1,083, Air Force 1,035), and the exporter records it as
  ingested-not-published by declaring no cadence for it (`_DECLARED_CADENCE`,
  `src/govbudget/export_site.py:664-673`). The honest limit is grain: MTS is
  agency-month outlays and this site's spine is program-element request
  dollars, so the only defensible view is department-level
  requested-versus-outlaid — never a per-program one, which is exactly the
  reading a careless chart would invite. Effort: days. Owner decision: publish
  a department-level outlay view (and give it a `_DECLARED_CADENCE` entry so
  gate 24 leg m meters it), or state on /coverage/ that outlays are ingested
  and deliberately unpublished. **Status:** open (2026-09-10).
- **#93 California ACFR extraction — deferred at Phase 4, never picked up.**
  Phase 4 registered the ACFR with a sha and recorded its extraction as
  explicitly deferred
  (`docs/superpowers/plans/2026-06-10-phase4-state-pilot.md:47`;
  `docs/superpowers/specs/2026-06-10-phase-gates.md:54`). Three months later it
  is still only a manifest row: `data/raw_docs/state/ca/ca_acfr_fy2023.pdf`
  (376 pages, 10,312,291 bytes, FY2023, `downloaded_at` 2026-06-11),
  `src/govbudget/verify_phase4.py:72-88` asserts manifest presence + sha + file
  on disk and nothing more, and the exporter declares no cadence for
  `state_acfr_ca` (`src/govbudget/export_site.py:672`). Extraction means a
  table-layout parse of an audited financial statement — a different document
  species from a J-book, with its own reconciliation targets and its own
  failure modes. Effort: weeks. Owner decision: extract it (and name the
  published totals it must reconcile against), or close state coverage at the
  machine-readable budget + checkbook and keep the ACFR as a cited cross-check
  only. **Status:** open (2026-09-10).
- **#94 Congressional-adds view — the elements are ingested and nothing reads
  them.** The Phase 5 considerations doc lists a congressional-adds view as a
  Hill-staffer feature with the data "already in the J-book XML"
  (`docs/superpowers/specs/2026-06-10-phase5-considerations.md:56-58`). It is:
  the FY2026 raw XML carries 3,819 `<r2:CongressionalAddDetail>` elements
  across 12 organizations (Army 1,825, Air Force 1,030, Navy 664, OSD 192,
  SOCOM 44, DLA 34, DARPA 12, DTRA 10, and four more at 2 each — raw element
  count over `data/raw_docs/fy2026/**/*.xml`, sibling books not deduped), each
  with a `Title`, per-scenario `Funding`, and a `Text` that frequently names
  the contractor the add was awarded to. Nothing parses them: `grep -rn
  CongressionalAdd src/ dbt/ site/src/ migrations/` returns nothing. #7 (the
  FEC → adds → awards chain) is a closed non-goal
  (`docs/superpowers/ROADMAP.md:662-679`); this entry is the adds view ALONE
  — no campaign-finance linkage, no causal claim, no new persona for the
  money. Effort: days for extraction plus a table; weeks if it gets its own
  page. Owner decision: is a congressional add a new claim type the
  number-versus-citation gates cannot police — the reason #7 was closed — or
  is it one more cited figure from a document already ingested?
  **Status:** open (2026-09-10).
- **#95 Dossier expansion beyond the top 50 — promised live, undecided.**
  5F called LLM descriptions for rollup-tier pages "a cost decision, not part
  of 5F"
  (`docs/superpowers/specs/2026-07-02-phase5f-program-page-normalization-design.md:84-85`),
  and /coverage/ now tells readers "the next batches are queued and will be
  taken in order of FY2026 requested dollars … pending a roadmap decision"
  (`site/src/lib/coverage-map.ts:290-293`; live today: "50 of 1,938 programs
  have a research dossier"). No entry carries that decision. The economics
  changed since the sentence was written: the 5G-dossiers round was authored
  by subagents rather than the cost-capped Batch API
  (`docs/superpowers/ROADMAP.md:29`), so the cost is agent time, not
  `ANTHROPIC_API_KEY` spend, while the gate is unchanged — `dossiers gate`
  requires every claim to resolve to a warehouse citation (last run 733/733
  against `WAREHOUSE_FLOOR = 0.80`, `src/govbudget/dossiers/gate.py:41`) and
  rejects a dossier with even one unresolvable claim rather than publishing it
  with a caveat. Effort: days per batch of ~50. Owner decision: batch size and
  cadence, or drop the /coverage/ promise.
  *Addendum 2026-09-25 (R-22a-3):* the /coverage/ sentence quoted above is the
  pre-Task-22a text. Since `0539aa9d` (2026-09-18) the row reads "No dated
  target, and not scheduled — the order is fixed even though the schedule is
  not: whenever a next batch runs it is taken in order of FY2026 requested
  dollars, largest lines first." (`site/src/lib/coverage-map.ts:413-415`). The
  decision this entry asks for is unchanged.
  **Status:** open (2026-09-10).
- **#96 PB2015 and PB2016 editions — promised live, undecided.** The decade
  backfill stopped at PB2017 (5E scope) and /coverage/ says "PB2015 and PB2016
  are the next two editions queued, and the date is pending a roadmap decision"
  (`site/src/lib/coverage-map.ts:264-268`; the same row leads with "10 editions
  loaded — PB2017–PB2026"). No backlog entry mentions them; the sentence has
  stood unchanged since 2026-08-05 (01a015f7) and the only commit that has
  ever touched the string `PB2015` is the one that published /coverage/ itself
  (a323b157). Each edition is a `jbooks backfill` run plus the evidence-keyed
  volume classification the /coverage/ blocker names — the rule that exists
  because two editions were nearly published with the wrong volumes — and
  costs roughly one defense-wide edition of storage (215–293 MB raw, judging
  by `data/raw_docs/fy2017` through `fy2025`). Effort: days per edition. Owner
  decision: take both, take neither and drop the promise, or publish the
  edition window as a stated policy.
  *Addendum 2026-09-25 (R-22a-3):* the /coverage/ sentence quoted above is the
  pre-Task-22a text. Since `0539aa9d` (2026-09-18) the row reads "No dated
  target, and not scheduled — PB2015 and PB2016 are the two editions that
  would come next. An edition ships only once its volumes are evidence-keyed —
  never on a filename pattern — so a date could only follow that work."
  (`site/src/lib/coverage-map.ts:384-387`). The decision is unchanged.
  **Status:** open (2026-09-10).
- **#97 Pre-2026 narrative paragraph provenance never ran.** 5E deferred
  page-level provenance for pre-2026 narratives, noting that "xml-anchor
  citations [are] still present"
  (`docs/superpowers/specs/2026-07-03-phase5e-decade-backfill-design.md:116`).
  #29(b) later made pre-2026 narratives citable, but they still resolve to the
  non-paged xml-anchor card rather than to a highlighted paragraph. Measured in
  Postgres: edition 2026 has 11,942 narrative provenance rows against 11,679
  non-superseded narratives; every earlier edition has between 0 and 5 rows
  against 1,201–2,748 narratives — 19 rows against 18,437 narratives across
  nine editions. The code path is the one FY2026 already uses (`python -m
  govbudget jbooks narrative-provenance --fiscal-year <FY>`,
  `src/govbudget/cli.py:764`) and the PDFs are on disk (215–293 MB per
  edition), so this is a compute-and-reconcile run, not new ingestion. Effort:
  days. Owner decision: run it for the nine editions, or state on
  /methodology/ that paragraph highlights exist for FY2026 only and that
  earlier editions cite the XML anchor by design.
  **Status:** open (2026-09-10).
- **#98 Accounts / saved searches / alerts (the first paid tier) — never
  scoped.** The 5B surface spec's v1 non-goals name "accounts/auth, saved
  searches/alerts (first paid tier, post-launch)"
  (`docs/superpowers/specs/2026-06-11-phase5b-product-surface-design.md:109-111`)
  and the phase ledger's Post-launch row still carries it as backlog
  (`docs/superpowers/ROADMAP.md:35`). Two months after launch there is no
  entry, spec or route. The alerting half shipped statically —
  `site/scripts/generate-feeds.mjs` writes 287 program and 63 company RSS/Atom
  watch feeds at build time, each item carrying its dollars and a `/fact/{id}`
  receipt permalink. The accounts half is not a missing feature but a missing
  stack: the site is a fully static export with no server, no session, no
  database and no user data anywhere. Two dependencies are hard, not soft —
  anything that mails a reader inherits the cited-or-absent rule without a
  citation panel beside it, and firing alerts off a corpus that is not on a
  refresh schedule (#8 open; award corpus last ingested 2026-06-11) implies a
  currency the data does not have. Effort: weeks. Owner decision: does Fiscal
  Receipts take on a server and user data at all? Scoping note:
  `docs/superpowers/specs/2026-09-10-accounts-alerts-tier-scoping.md`.
  **Status:** open (2026-09-10).
- **#99 Public text-to-SQL analyst surface — never scoped.** The same v1
  non-goal list defers a "public text-to-SQL endpoint (analyst agent stays an
  internal CLI — the paid-analyst surface comes after launch)"
  (`docs/superpowers/specs/2026-06-11-phase5b-product-surface-design.md:109-111`;
  ledger row `docs/superpowers/ROADMAP.md:35`). The engine is real and
  guarded: `python -m govbudget analyst` (`src/govbudget/cli.py:2647`) runs a
  manual tool loop on `claude-sonnet-4-6` with `MAX_TURNS = 8`
  (`src/govbudget/analyst/agent.py:40,47`), and the SQL tool accepts one
  statement that must start with SELECT or WITH and caps results at
  `ROW_CAP = 200` / `TIMEOUT_SECONDS = 30`
  (`src/govbudget/analyst/sql_tool.py:83-86`), opening DuckDB `read_only=True`
  with `data/parquet` as the only readable prefix and every other external
  access disabled (`:176-196`). Measured on the newest recorded eval run
  (`data/research/eval-runs/eval-20260901T055645Z.json`, 48 questions):
  $0.8471 total, $0.0176 mean, $0.0120 median, $0.1297 worst, 2.6 turns mean —
  and `accuracy 48/48` but `citation_ok 42/43`, so `ok: false`. That last
  figure is the whole risk: a live answer is a number no gate saw before the
  reader did, which is the one thing this site has never published. Effort:
  weeks (hours for a static "asked and answered" page built from the eval
  set). Owner decision: public, gated behind accounts, or permanently internal
  — and if public, the 100% citation-resolution floor must be enforced at
  answer time, not measured nightly. Scoping note:
  `docs/superpowers/specs/2026-09-10-public-analyst-surface-scoping.md`.
  **Status:** open (2026-09-10).
- **#100 LLM-alias pass residue: 12,811 announcement records ($278B) never
  attempted.** The Leg-3 LLM alias pass took the top 3,840 unmatched
  defense.gov announcement records by announced value ($1.96T of the $2.23T
  residue) and stopped; the remaining 12,811 records / $278B were not
  attempted (`docs/superpowers/ROADMAP.md:118-119`). The scope is disclosed on
  the live /methodology/ page verbatim ("the 12,811 smaller records carrying
  the remaining ~12% were not attempted"), which is honest — but no entry
  carried the decision, no date was set, and a stopping rule that is never
  revisited quietly becomes a permanent one. Wave 4 is Task 25 of the
  roadmap-completion plan (2026-09-10) — a residue miner plus a two-lens
  adjudication under the same refute discipline — so what this entry holds is
  the stopping RULE, not the count.
  Effort: days. Owner decision: keep going after wave 4, or publish the
  stopping rule as deliberate and say why the small-record tail is below the
  line. **Status:** open (2026-09-10).
- **#101 Print and reduced-motion captures were never produced for any judged
  pack.** `docs/superpowers/reviews/EVIDENCE-CONVENTIONS.md:8-36` requires
  `<page>-1440-print.png` (`page.emulateMedia({ media: "print" })`) and
  `<page>-1440-reduced-motion.png` (`{ reducedMotion: "reduce" }`) in every
  pack authored from 2026-07-03 onward, precisely so the D4 print/export
  dimension and the motion contract are judged from evidence instead of from
  default captures — the exact advisory the convention was written to fix. No
  pack contains either file (`find docs/superpowers/reviews -name '*print*' -o
  -name '*reduced*'` is empty) and no capture script emulates either; the
  scripts stop at `site/scripts/capture-5h-visuals.mjs`, committed 7a72eacf on
  2026-07-03, hours before the convention itself (746287fd, same day). Every
  judged round since — 5G, 5I-lineage, 5I-review, PM-S1, PM-S2, PM-S3 —
  recorded scores as ledger prose with no committed pack at all, which is also
  why #91 has none. Effort: hours (two `emulateMedia` calls in a shared
  capture helper, then re-capture on the next judged round). Owner decision:
  enforce the convention on the next pack, or amend it to describe what packs
  actually ship. **Status:** open (2026-09-10).
- **#102 Lineage title-only endpoints — the ~4,400 verb-only clauses.**
  #29(a) closed on clauses that already contain a PE token; the roughly 4,400
  clauses carrying a transfer verb and no code were declared out of scope for
  that pass and need a separate English-phrase-to-PE matcher with its own
  precision study, because that matcher's dominant error is confidently
  resolving a SYSTEM name to a BUDGET LINE — a true sentence with a false
  endpoint
  (`docs/superpowers/specs/2026-08-31-lineage-llm-extraction-precision.md:194-201`,
  whose neighbouring section measures 432 of 1,936 corpus programs as
  numeric-only, so the ambiguity is measured rather than assumed). Meanwhile
  the live /coverage/ page still tells readers "narrative extraction across the
  whole FY2026 set is the planned next step … pending a roadmap decision"
  (`site/src/lib/coverage-map.ts:329-332`) — written 2026-08-05 (01a015f7) and
  unchanged since, i.e. before that pass ran; today 143 of 1,938 programs
  carry a lineage rail. Effort: weeks. Owner decision: fund the matcher and
  its precision study, or restate the /coverage/ target to say the PE-token
  pass ran and the title-only half is refused on measured ambiguity.
  *Addendum 2026-09-25 (R-22a-3):* the /coverage/ sentence quoted above is the
  pre-Task-22a text. Since `0539aa9d` + `30dba2ff` (2026-09-18) the row reads
  "No dated target, and not scheduled — the pass over clauses that already
  name a program element has run; what is left are clauses naming only a
  system or an effort, which need a different matcher and their own precision
  study. Anything such a matcher found would stay in the candidate tier until
  a quotable sentence names the other end." (`site/src/lib/coverage-map.ts:462-467`)
  — the restatement this entry's second option asked for. Funding the matcher
  and its precision study remains the open decision.
  **Status:** open (2026-09-10).
- **#103 Program-genealogy timeline and program-page district footprint map —
  the 5B-3 "backlog with sketch" was never filed.** Plan-level decision 2 of
  5B-3 deferred both with the promise of a backlog entry and a sketch
  (`docs/superpowers/plans/2026-06-12-phase5b3-features-enrichment.md:11`);
  neither was written. Part of the genealogy idea shipped since as the
  program-page lineage rail and the /lineage/ Sankey — budget-line identities
  only, no awards, GAO findings or news — so what remains is a per-program time
  axis composing data the site already holds. The footprint map is the
  per-program form of the choropleth closed as a non-goal in #15
  (`docs/superpowers/ROADMAP.md:750-768`) and is blocked on the same thing: 153
  of 435 districts carry any linked award today, so a map reads roughly
  two-thirds blank and readers read blank as zero. Effort: days for the
  timeline; the map is blocked, not costed. Owner decision: build the
  timeline, and either adopt #15's reasoning for the map or name the district
  coverage bar that would unblock it. **Status:** open (2026-09-10).
- **#104 GAO protest-docket enrichment — promised live, nothing exists.** 5H
  named protest-docket enrichment "future backlog"
  (`docs/superpowers/specs/2026-07-02-phase5h-flowdown-chart-design.md:61`) and
  the live /coverage/ feed row now tells readers "two further event types are
  planned, protest outcomes and GAO high-risk transitions, each with its
  threshold published before its first card"
  (`site/src/lib/coverage-map.ts:490-493`). Neither exists: `fct_feed_events`
  carries three types (concentration_shift 908, yoy_swing 99, new_entrant 25),
  and `grep -rli protest src/ dbt/ site/src/` matches exactly one file —
  `site/src/lib/coverage-map.ts`, the promise itself and nothing that keeps
  it. The second promise is nearer than it looks:
  `src/govbudget/oversight/high_risk.py` already ingests the high-risk list
  (38 areas), but `data/parquet/oversight/high_risk.parquet` carries no date
  or edition column, so it is a single undated snapshot and a TRANSITION needs
  a second dated edition before it can be an event at all. Protests need a new
  source (GAO's bid-protest docket), and the honesty rule from the same
  non-goals section still binds: FPDS records offer counts only, and the UI
  must never imply losing-bidder identities it does not have. Effort: weeks
  for protests; days for high-risk transitions once a second edition is
  ingested. Owner decision: ship either with its threshold published first, or
  drop the sentence.
  *Addendum 2026-09-25 (R-22a-3):* the quoted promise survives verbatim, but
  since `0539aa9d` (2026-09-18) it is preceded by "No dated target, and not
  scheduled —" instead of followed by "Which build carries them is pending a
  roadmap decision." It now sits at `site/src/lib/coverage-map.ts:678-680`.
  **Status:** open (2026-09-10).
- **#105 Key the successors the narratives already state.** 23 forward
  pointers on 19 no-rail renumbered pages (measured 2026-09-05 against the
  2026-09-04 20:06 export — the population Task 4's gate 21 leg l floors) are
  verbatim in PB2026 narratives and unkeyed: (i) `_RULES` in
  `src/govbudget/lineage/extract.py` lacks the DARPA form "Beginning in FY
  2026, efforts in this PE will be funded in PE X" (14 PE→PE pointers, incl.
  0601101E → 0601122E, 0603760E → 0603467E); (ii) line-item/WSC destinations
  (2900 → LI 2361, 2176 → BLI 2136, 2026 → LI 2981, six AF BLIs → OSAEA0,
  FET000 → PE 0303131F) need account-scoped keys — numeric pe_blis are not
  unique (V3-shape) and would resolve to E3 composite slugs. (i) is one
  `_RULES` entry + `lineage build` + verify-lineage; (ii) is a key-shape
  decision through `program_lineage` (`migrations/008_program_lineage.sql`:
  `from_pe_bli` / `to_pe_bli` are free text, no shape constraint) and the
  rail's `pe` field. Each keyed edge moves its page out of leg l's floor —
  re-measure and lower with a dated note. Effort: days.
  **Status:** open (2026-09-10).
- **#106 Turbopack drops the space after an interpolation when the JSX text
  run that follows spans a line and carries an HTML entity.** `/methodology/`
  rendered "plus 553whose cited record", "ingested for 1,936of them" and
  "(240at high confidence)"; nine `/agency/` reconciliation notes rendered
  "OSD's 128programs" (DMACT is the only agency page whose `program_count`
  is 1, so it read "1programs"); the `/years/` balanced-panel caption compiles
  to "programs present" with no space — client-rendered, so no built-HTML
  gate could have seen it. ba6c7d66 had already fixed one such site by hand
  in `methodology/page.tsx` and named the cause in a comment; a2637af2 fixed
  the species in `program-figures.tsx` alone. Babel's cleaner, which gate 2
  leg (sp) modelled, keeps that space. Also: gate 14 leg cm's split-sum
  assertion recomputed `pages − detail − decade` and re-added it to `pages`
  (a tautology), and its "73"/"553" substring checks could match inside any
  other number on the row. Two things left open on purpose: the 120-character
  LDA mention snippet is NOT marked as quoted source text (136 of them on the
  heaviest filing page would cost ~19,000 raw bytes against 19,198 of
  `/filing/*/` raw headroom), so a join inside one will fail gate 2 loudly
  and the fix then is the marker plus a dated ceiling raise; and whether
  `influence pull` collapsed the registrants' line breaks at all ("H.R.
  7586American Families First Act" is glued in the sidecar) was not
  investigated. #28's own CLOSED stamp says 2026-08-29; its four commits are
  dated 2026-08-31 (left as written).
  **Status:** CLOSED 2026-09-05 (`e664dce4` five sites carry an explicit `{" "}`
  and leg (sp) models the entity trim with a proof-can-fail test and a guard
  on the real tree; `9aee170c` gate 2 leg (nw) reads every built text run for a
  number glued to a word — ordinals, 8+-char hex ids and L3Harris allowed,
  quoted source kinds and `[data-program-name]` exempt, floor 40,000 intact
  "number word" runs against 89,766 measured — LDA activity descriptions and
  covered positions marked `data-source-text="lda-filing"` with the filing's
  URL, J-book project titles marked `data-program-name`; `663a759c` leg cm reads
  each tier bucket off the sidecars and re-adds the rendered sentence's four
  numbers; `ad23016b` the ROADMAP findings entry and this backlog entry;
  `090d63db` the style follow-up keeping `recomputeCoverageMap`'s docblock
  attached to it). (wording corrected before publication)
- **#107 OWNER CALL: what happens to the `account+subagency` tier now that it
  measures 0/60 for program attribution.** The 2026-09-05 sample (60 published
  links, judged 2026-09-11 by two adversarial lenses, 0 disagreements)
  confirmed none. Not all 60 failed the same way (corrected 2026-09-11, Task
  6c, before merge — the entry first stated a universal the verdicts do not
  support): several awards name a different DARPA effort outright, at least six
  name no work at all (boilerplate, which the rubric refutes on silence) and at
  least five describe DARPA-wide contracting-office or acquisition-support
  staffing; where a reviewer found any overlap
  at all it was usually the appropriation account, the DARPA sub-agency and the
  HR0011 prefix — the linking rule restated — but SIX reasons record a thematic
  content overlap that is none of those three and nothing more (re-counted
  2026-09-11; the first half of this universal was hedged before the second). The figure is
  published as measured (smaller true number, 2026-08-07); WHETHER THE TIER
  KEEPS PUBLISHING is the owner's, not a gate's. Scale: 9,337 published rows in
  Postgres over 416 DARPA awards and 24 DARPA PEs; 8,856 in the mart — 72% of
  every published link a reader can meet, and 8,856 of the 9,581 published rows
  (92%) on those 24 program pages. Three options and what each costs:
  (a) **keep it published at medium with the caveat** — nothing moves; the
  Related Awards table on those 24 pages stays 92% rows whose attribution
  measured 0/60, and the honesty rests entirely on the in-table medium note
  (gate 21 leg m) plus /methodology/'s figure, which a reader skimming a table
  may not meet; (b) **demote to an unpublished audit tier** — no program loses
  its Related Awards table (all 24 also carry links of another species), but
  11 of the 24 carry NO rows from a MEASURED tier at all (measured 2026-09-11:
  0602715E, 0605898E, 0605001E, 0602115E, 0605502E, 0602026E, 0603468E,
  0601122E, 0601117E, 0602023E, 0601101E have zero `announcement+lexicon` /
  `fpds-ap` / `subaward+lexicon` rows), so under (b) those eleven pages would
  show a Related Awards table built entirely of tiers whose precision is
  unmeasured (`account`, `account+tokens`) — the same table to a reader,
  carrying less evidence than the one it replaced. Those pages also
  lose ~92% of their rows and the all-tier concentration basis
  (`*_all`, #80) is recomputed on those 24; the high-only basis (`*_high`) and
  the district dollar marts are unaffected by construction (`fct_district_*`
  are `confidence = 'high'` only — the all-confidence breadth grain would lose
  rows); (c) **replace with evidence-graded links only** — (b) plus a
  description-level crosswalk for DARPA, the most expensive and the only one
  that restores coverage with evidence behind it. Decide with #80's basis work
  and #85's mechanical crosswalk, and alongside **#110** — the same owner call
  one tier up, for the 708 `announcement+lexicon` links published at high
  whose adversarial pass leaves no record.
  **Status:** open (owner call, 2026-09-11).
  *Re-measured 2026-09-25 (chain C run 4 lake, read-only):* the tier still
  publishes — 8,855 `account+subagency` rows in `fct_budget_to_awards` (8,833
  medium, 22 high) — and `site_meta.link_precision` still carries its 0/60.
  The eleven-page list and the 9,337 Postgres count above are 2026-09-11
  figures and were not re-derived. Decide alongside **#141** (the
  LORELEI-style re-attribution rule the 0/60 verdicts point at) and **#140**
  (the loader re-attributing links across routes).
- **#108 `fpds-ap` rubric: the tier was judged partly on its own rule.** The
  FPDS acquisition-program tag IS the `fpds-ap` linking rule, and it leads 40
  of the 60 verdict reasons behind `fpds-ap 94/120`; fewer than ten cite the
  PE's narrative or project titles (6 by Task 6a's count, 4 by a stricter
  match — both over `data/research/precision/verdicts_2026-09-04.json`). The
  2026-09-04 study judged that stratum on "the tag matched and the hand-made
  mapping holds", which is weaker than the description-level attribution the
  announcement and subaward strata were judged on and stronger than the
  rule-restating that #79 caught in `account+subagency` — the reasons do pair
  the tag with the award's work description, so it was not re-stamped
  `rule-fired`. A future study should judge `fpds-ap` on description-level
  attribution like the other strata and publish whichever number comes back.
  **Status:** open (2026-09-11).
- **#109 "every published link was individually hand-adjudicated" is looser
  than the adjudication table.** /methodology/ §Budget-to-contract links opens
  with it, and `docs/methodology.md` mirrors it. Measured read-only 2026-09-11
  over the live warehouse: of 12,595 published (high/medium)
  `budget_line_awards` rows, 9,587 carry an `award_pe_adjudications` row at all
  (`account+subagency` 9,173/9,337, `account+tokens` 414/527, and ZERO for the
  1,910 `fpds-ap`, 708 `announcement+lexicon` and 113 `subaward+lexicon` links,
  which are adjudicated by the other processes the same section describes). Of
  the adjudicated ones, 8,474 carry `award_verdict = 'darpa_unpinned'`,
  `pair_reason = 'unpinned-pool'`, empty basis — the hand adjudication
  investigated the AWARD and explicitly did not pin it to this PE, and the
  loader then publishes it at medium against every DARPA PE in the account.
  That fan-out is exactly what #79's 0/60 measured. Nothing renders a wrong
  number and the tier grading below the sentence is honest (medium = "an
  association, not evidence that this specific program paid", now with the
  0/60 beside it), but the opening summary reads as "a human checked this
  pair" for 8,474 links whose adjudication says the opposite. Fix needs an
  evidence pass over all five evidence paths and a gate on the claim, not a
  reword — out of scope for #79, which is why it is filed rather than edited.
  (The overlay is working: all 262 published rows whose adjudication says
  `contradicted`/`not_darpa` are demoted out of the mart.)
  **Status:** open (2026-09-11) — opening sentence shrunk to the derived
  adjudication-coverage numbers in `640320e0` (Task 6c; block `61907d78`, gate
  24 leg o `64d5cac9`), then re-dated and the High tier graded surface by
  surface in Task 6c fix round 1 (block + `measured_on` `7b516f6b`, leg o
  `8409114a`): the census is dated by the export run and `as_of` by the last
  adjudication; /methodology/'s High grading renders 60 of 768 from
  `site_meta.link_adjudication.high` (`136abf35`), the flow clause now points
  at §4's grading instead of restating the tier, /coverage/'s blocker binds
  the adversarial step to the links that carry an adjudication (`0716cfe0`),
  and `docs/methodology.md` mirrors the rendered sentence. Fix round 2 bound
  each of those figures to its SLOT in leg o (a passage that permutes the
  block's own numbers used to pass) and made a block that grades links while
  exporting no High census a gate failure instead of a silent pass
  (`f5c52110` leg o; `0f5c08e7` exporter + companion). The
  five-path evidence pass and per-path gate remain; what to do about the 708
  is #110.
  *Note 2026-09-25 (Task 6c round-2 re-review):* leg o's non-vacuity companion
  keys off "a non-empty `link_adjudication` block means a High census is
  owed", so a corpus with zero high links would be misdiagnosed as a deleted
  census. None exists (1,133 high links at chain C run 4); no code change.

- **#110 OWNER CALL: 708 of the 768 links published at HIGH carry no per-award
  adjudication, and their adversarial pass leaves no record.** Measured
  read-only 2026-09-11 over `fct_budget_to_awards` (the tier a reader meets):
  768 links publish at `high` — `announcement+lexicon` 708, `account+tokens`
  34, `account+subagency` 23, `account` 3. Exactly **60** carry an
  `award_pe_adjudications` row, and all 60 are `pinned` / `pinned-here` /
  `refuter_lenses_passed = 2` — they are the whole two-lens population of that
  table. The other **708** are announcement links: each carries an
  `award_link_sources` announcement row, a match basis is recorded on **384**
  of them (exact-name 190, designator-normalized 93, llm-alias 59,
  llm-designator-variant 36, llm-description 6) and NULL on 324, and the
  agent-reviewer + independent-adversarial-reviewer pass /methodology/
  describes for that path writes NO row anywhere in Postgres. Its precision
  IS measured — 51 of 54 on attribution under the tier these links publish
  under today, sample `2026-09-04` (the raw 2026-09-04 stratum drew 60) — so
  this is not an unmeasured tier; it is a tier whose per-link review is
  unrecorded and therefore ungateable. Task 6c fix round 1 shrank the four
  surfaces that graded the whole tier, each in its own way: /methodology/'s
  High grading renders "60 of the 768 … all 60 of them challenged by two
  independent adversarial reviewers; the other 708 rest on the
  announcement+lexicon path" from `site_meta.link_adjudication.high`
  (`136abf35`), the flow clause points at §4's grading instead of restating
  the tier, /coverage/'s blocker binds the adversarial step to the links that
  carry an adjudication (`0716cfe0`), and `docs/methodology.md` mirrors the
  rendered sentence. That is the smaller true number; what the SITE does
  about the 708 is the owner's call.
  **Correction this entry carries** (measured 2026-09-11, and the reason it is
  not the entry the fix round was briefed to write): the review that raised
  this counted the high tier as
  `coalesce(adjudicated_confidence, confidence) = 'high'` over
  `budget_line_awards` and got **881**, including 113 unadjudicated
  `account+tokens` rows. Those 113 do NOT publish at high — dbt demoted them
  on 2026-09-04 (#75 addendum ruling 3: "a mechanical account+tokens/high pair
  that no human has adjudicated must never publish as high"), and Postgres has
  no column recording it. So the briefed question "should the 113 be demoted"
  is already answered, no floor moves for them, and the live question is the
  708. Re-derive this tier from the MART or not at all —
  `export_site._published_high_links` exists for exactly that reason.
  Three options and what each costs:
  (a) **demote the 708 to medium** — the high-only marts collapse, measured
  read-only 2026-09-11 by re-running each mart's own predicate with
  `method <> 'announcement+lexicon'`: programs publishing an `hhi_high` band
  fall **37 → 4** (`_MIN_HIGH_ONLY_ROWS = 37`, `src/govbudget/verify_phase3.py`,
  dated 2026-09-11 and never-lowered); `fct_district_programs` **392 → 53**
  rows over **203 → 7** programs and **153 → 41** districts;
  `fct_district_totals` **153 → 41**; and feed leg (l)'s reconcilable
  population goes to ZERO — all five destinations it reconciles against
  (`0158`, `0603892C`, `2004`, `2122`, `ATA000`) lose their band, so the leg
  trips its own vacuity guard, not merely its floor of 21
  (`MIN_RECONCILABLE_HHI_DESTINATIONS`, `site/scripts/gates/feed.mjs`). Gate
  21's floors do NOT move: `MIN_MEDIUM_CAVEATS_SAMPLED`,
  `MIN_SPLIT_MEMBER_PAGES_WITH_AWARDS` and `MIN_SPLIT_AWARD_ROWS` all count
  high-OR-medium rows, so a demotion can only grow them. Re-dating four
  never-lowered floors downward is an owner decision, not a gate's;
  (b) **record the announcement path's review** — backfill the agent-reviewer
  and adversarial-reviewer outcomes into `award_pe_adjudications` (or a
  sibling table) so the 708 can be gated the way the 60 are. Cost: one
  backfill of an existing pipeline's outputs, no tier moves, and the High
  sentence then states a coverage figure instead of a split. This is the only
  option that ENDS the question rather than moving it;
  (c) **leave them high with the shipped sentence** — cost: 708 of 768 high
  chips rest on a review whose only record is prose, 324 of them without even
  a recorded match basis, and the claim can never be gated beyond "the path
  is named". Nothing is false; nothing is checkable either.
  Decide with #109's five-path evidence pass, which is the same work as (b),
  and alongside **#107** — the same owner call one tier down, for the
  `account+subagency` medium tier that measured 0/60 on attribution. The two
  are the same question about different evidence: what a tier keeps
  publishing when its per-link attribution measured ZERO (#107) or was never
  recorded at all (#110).
  **Status:** open (owner call, 2026-09-11).
  *Re-measured 2026-09-25 (chain C run 4):* **1,133** links publish at high —
  `announcement+lexicon` 1,074, `account+tokens` 34, `account+subagency` 22,
  `account` 3 (`fct_budget_to_awards`) — and `site_meta.link_adjudication.high`
  records 60 of them adjudicated, all two-lens; the other 1,073 carry no
  per-award row, and a match basis is recorded on 748 of the 1,074
  announcement links. The tier's pinned precision now reads 56/60 (its
  2026-09-04 draw, counted under the tier each link publishes under today),
  not the 51/54 quoted above — #140 records why it moved with no verdict
  changing. Option (a)'s costs above were measured on the 2026-09-11 marts
  (37 `hhi_high` programs, 392 district rows) and are stale: the same marts
  now publish 63 `hhi_high` programs and 611 district rows over 189
  districts. Re-measure before deciding.
- **#111 Residual FY2026 J-book absences (from #14).** (a) The DHP book's
  per-section R-1/P-40/R-2 URLs 404 on the comptroller index and the combined
  `00-DHP_Vols_I_and_II_PB26.pdf` that IS served carries no jb-2009 `.zzz`
  payload (acquired 2026-09-12, `has_embedded_xml` false, zero PDF
  attachments), so DHA has a downloaded book and still zero loaded detail —
  re-probe the section URLs periodically, and probe the Internet-Archive
  mirror (`jbooks backfill --source archive`) if they stay gone. An
  LLM-over-PDF pass is NOT the fallback here: cited-or-absent.
  (b) Whether either consolidated Defense-Wide volume (`PB_2026_PDW_VOL_1.pdf`,
  `PB_2026_RDTE_VOL_5.pdf`, both pinned in `EXCLUDED_NAMES` as per-agency
  re-issues) carries `0904903D`'s R-2 is unprobed. (c) `0708083D` (Assembled
  Chemical Weapons Alternatives) is a published-but-excluded case, not an
  absent one: its R-2 lives in `Chemical Agents and Munitions Destruction,
  Defense.pdf`, excluded by `registry.ARMY_EXCLUSIONS` as a Defense-Wide-account
  book in the Army inventory. Its page reads the Army books' ingested wording,
  which is true as stated but does not name the excluded book; decide whether
  that account deserves its own coverage sentence. (d) `docs/methodology.md:31`
  still says J-books are published at `comptroller.defense.gov`; the host is
  `comptroller.war.gov` and every `jbook_documents.source_url` already uses it.
  (e) The SITE half — what those pages SAY about (a) and (b) — is **fixed on
  this branch by Task 17c (`428623ad`, 2026-09-12)**. All 19 pages said
  "…J-book, which is not yet ingested", a sentence that presupposes a book
  exists: false for IG (1 page) and DEFW (4), imprecise for DHA (14, the book
  is downloaded). `export_site._org_absences` now publishes the probe's own
  record into `site_meta.org_absences` ({org: {rule, checked_on,
  checked_url}}, derived from `edition_manifest.json`) and each rule renders
  its own sentence on all four surfaces that carried the old one — the
  description note, the Justification empty state, the WHAT-IT-IS card tail
  and `<meta name="description">`. Gate 21 leg (o) binds the two prose
  surfaces to the rule and bans the phrase over the whole page. The DATA half
  — clauses (a)–(d) — is untouched and still open: the site now states the
  absence precisely instead of mis-stating it, which is not the same as
  closing it.
  **Status:** open (2026-09-12) — (a)–(d) open; (e), the false rendered
  sentence, fixed on this branch by Task 17c (`428623ad`, 2026-09-12).
- **#112 `3010` has no search alias.** "LPD 17" and "San Antonio-class" reach
  nothing: `flight` was 3010's ONLY title term and it left
  `GENERIC_TITLE_TOKENS` in chain-B fix 3 (it matched a ramjet test vehicle
  and a counter-drone rotor, both filed under an amphibious transport dock,
  and a matched snapshot is a citable url under `recent_developments`). The
  program is now unreachable by the names a reader would actually type. Add
  curated aliases for it in the search-alias CSV — the token set was the
  wrong place for a program-specific name and tightening it is not a
  substitute for naming the ship class.
  **Status:** open (2026-09-12)
- **#113 A J-book volume filing an ACCOUNT-split shared code under an
  unknown appropriation raises out of `_build_summary_blocks`.**
  `_gslug` calls `_ProgramIdentity.slug` with the account_title it looked up
  from `dim_programs`, so a `(pe_bli, account)` pair with no program row —
  including `account IS NULL` — raises `ValueError: … no account_title was
  supplied` from deep inside the summary-card pass, naming neither the
  document nor the row. Found 2026-09-12 by a Task 9b fixture, not by the
  corpus: the live unattributable case (PROC_DoDEA under code '30') is on the
  ORGANIZATION axis, where `slug` needs no lookup and returns `30-DODEA` —
  a summary block under a slug no page reads, which is dead weight but not a
  crash. Two halves: make the message name the document and the pe_bli, and
  decide whether an unattributable grain should mint a summary block and its
  citation rows at all (ROADMAP #82's "publishes on neither member" says no;
  dropping it removes citation rows nothing references, so it needs a build
  to confirm the census). Same second half, measured 2026-09-12: the five
  `30/DODEA` detail facts and two narratives that ROADMAP #82 sends to
  NEITHER member keep live `citations.json` rows (3 details + both
  narratives), and `/fact/{id8}` now renders "Appears on `/program/30/`" —
  the disambiguation stub, which owns no sidecar and carries no `#fact-`
  anchor. Pre-existing for every shared-code fact; newly the ONLY surface
  these five have. Whatever the census decision is, it decides these too.
  **Status:** open (2026-09-12)

- **#114 The five crosswalk counts are derived on the SITE side, not published
  as an exporter block.** `getCrosswalkCounts()` reads them off two shipped
  artifacts — `flow_chart.json`'s own bridge band and the `flows/` sidecar
  directory — and gate 24 leg (p1) recomputes them from the same two and binds
  the rendered list slot for slot, so nothing is typed and nothing drifts
  silently today. It is still two derivations of one number. Task 21b
  considered publishing the registry as `site_meta.crosswalk_counts` and did
  not, for a reason worth recording: **`site_meta.json` is written three
  sections BEFORE `_emit_flows_sidecars` runs**, and the sidecar set is not
  knowable until that loop finishes (a high-linked PE with no district-bearing
  award is skipped, so it is not `select distinct pe_bli from
  fct_district_programs` either). Publishing the block would mean either
  reordering the export or deriving the sidecar set a second way, which is the
  defect the registry exists to close. If a third consumer ever needs these
  counts, move the `site_meta.json` write below section 11 rather than adding
  a second derivation.
  **Status:** open (2026-09-18)

- **#115 `build_program_terms` is last-title-wins on a shared BLI code, so one
  member's title is never searched.** `src/govbudget/influence/mentions.py`
  builds its term index as `result[pe_bli] = compiled` while iterating
  `select pe_bli, title from dim_programs` (two rows on a shared code, via
  `influence pull`/`rematch` in `cli.py`), so the second row simply
  overwrites the first: on the 13 shared codes the matcher searches filing
  text for exactly ONE arbitrary member's tokens and the other member's are
  never candidates at all. (`fct_program_lobbying`'s `programs` CTE already
  collapses the mart to `min(title)` per `pe_bli` for the same reason — the
  mention row has no member identity to carry.) Measured 2026-09-18 by
  running `build_program_terms` over today's `dim_programs`: `0145` indexes
  `General, Purpose, Bombs, 0145` — "General Purpose Bombs", never "F/A-18E/F
  (Fighter) Hornet" — and `1350` indexes `Missile, Industrial, Facilities,
  1350`, while the SHIPPED mart's two `1350` rows carry `Weapons|Ammunition`,
  tokens of the OTHER member ("Infantry Weapons Ammunition"). So which member
  the index holds is not even stable between runs, and a rematch can silently
  swap which member's lobbying rows exist.
  Task 9b fix round 1 made the EXPORTER attribute each row to the member whose
  own title carries the matched terms (so no page renders a false badge), but
  the missing half is invisible from the sidecars: mentions that would have
  matched the unsearched member exist in no row anywhere, and the mart cannot
  say how many. The fix is a mart + matcher change — key the term index by
  `(pe_bli, account/org)` or by `dim_programs` row, widen
  `fct_program_lobbying`'s `programs` CTE past `min(title)`, and add the
  member identity to the mention row — which changes the mention census on
  /methodology/ and needs an `influence rematch` + `dbt build`, so it is not a
  Task 9b change. Second half, same root: `/filing/{uuid}/`'s shared-code note
  explains the chooser with the `pe_literal` reason in its `title` tooltip
  ("Lobbying filings name a budget line, not an appropriation account, so this
  mention cannot say which of the programs sharing the code it refers to") —
  true of a `pe_literal` row, not of a `multi_token`/`alias` one, where the
  matched terms DO say which member (the program page attributes on exactly
  that, Task 9b fix round 1). Rendered prose, so it was left alone here; fix
  it with the matcher, when the row itself can name its member.
  Appended 2026-09-18 (9b re-review). The first half is not mart-only — it is
  on a RENDERED page. `/company/{slug}/` prints
  `entity_details.mentions[].program_title` as the link label beside the terms
  the row matched on, and that title is the `min(title)` collapse itself
  (`fct_program_lobbying`'s `programs` CTE, one row per `pe_bli`). Measured
  2026-09-18 read-only on the shipped artifact:
  `/company/international-business-machines/` renders **"F/A-18E/F (Fighter)
  Hornet"** on all five of IBM's `0145` rows, whose `matched_term` is
  `General|Purpose` — the title words of the SIBLING member, "General Purpose
  Bombs". The `linked_programs` chip on the same page is already correct (it
  carries the both-members label, ROADMAP #70 fix round 1); the mention list is
  the surface that still names one member for a row matched against the other.
  A third strand, same root, different question — the GRAIN of an `alias`
  row. The
  exporter's `_mention_is_about` treats `alias` as TITLE-grain (the row
  publishes only on the member whose own title carries the alias phrase), while
  `_WHO_LOBBY_TIERS = ("pe_literal", "alias")` and `_build_lobbied_by` treat it
  as CODE-grain (both members get the same families list). A curated alias is
  seeded per CODE — `dbt/seeds/program_aliases.csv` keys on `pe_bli`, not on a
  `dim_programs` row — so on a shared code an alias phrase carried by NEITHER
  member's title would be dropped from both Lobbying Mentions lists while still
  naming companies in both WHO-GETS-IT cards. Nothing renders differently
  today, and this entry does not change the behaviour: measured 2026-09-18
  read-only, the 13 shared codes carry 25 `multi_token` and 51 `pe_literal`
  mention rows and **zero** `alias` rows (256 alias rows exist corpus-wide, all
  on unsplit codes), so the only place a dropped alias would show is the
  export's mention census line. Decide the grain with the matcher fix above,
  when the row can name its own member.
  **Status:** open (2026-09-18)
  *Addendum 2026-09-25 (ledger sweep; Group D SITE polish riders).* Two
  gate-side strands of the same grain question, both dormant because no shared
  code carries an `alias` row (re-measured 2026-09-25: the 13 shared codes
  carry 51 `pe_literal` and 25 `multi_token` mention rows and still zero
  `alias`): gate 21 leg (n) applies `titleCarriesTerm` to every non-"code"
  basis, although a curated alias is precisely a term the program title need
  not carry; and for an alias row its per-tier badge message asserts the alias
  badge is false when it is not. Settle both with the matcher's grain.

- **#116 Announcement LLM-alias pass: the residue tail, the 156 chunks wave 4
  did not reach, and the 683 records no wave can reach.** Wave 4 adjudicated
  150 of the 306 queued chunks — 11,775 of the 28,344 residue records — so
  with the earlier 2026-09-02 pass (3,829 of whose 3,840 entries are still in
  today's residue) the route has now been through 15,604 records, 89.1% of the
  residue by announced value; 12,740 records (10.9% of that value) have not
  been attempted. THAT REMAINDER IS NOT ONE PILE, and the difference decides
  what "keep going" can buy:
  - **12,049 records, about $133.8B** — queued, in the 156 chunks of
    `data/research/announcements/wave4_queue/` no lens has read (gitignored;
    regenerate with `uv run python scripts/mine_announcement_residue.py
    queue`, which re-derives the residue and its 306 chunks from
    `records.jsonl` and rewrites `residue_manifest.json`). More workflow runs
    reach these.
  - **683 records, about $281.3B — 7.3% of the residue by announced value,
    two thirds of the unattempted VALUE** — never queued and not queueable:
    `select_residue` rule 4 drops a record whose service maps to no
    organization, or to one with no owned-name lexicon (283 U.S.
    Transportation Command, 218 Defense Health Agency, 75 DFAS, 38 with no
    service heading, …). Regenerating the queue drops them again. Reaching
    them needs a lexicon for those services, not another wave.
  So collecting every remaining chunk takes the published figure to about
  **92.6%**, not 100%. (The last 8 of the 12,740 are duplicate paragraphs of
  records the earlier pass did attempt: the published count counts that pass
  by distinct record, which is the smaller coverage figure.) The published
  figure on /methodology/ moves on its own when more chunks are collected and
  `scripts/load_announcement_scope.py` re-runs — the page states no literal to
  edit. This is the COUNT half of #100, which holds the stopping RULE: the
  owner decision there (keep going, or publish the stopping rule as
  deliberate) is unchanged by wave 4 and now has a derived number in front of
  it. Precision of what wave 4 added is measured, on its own held-out sample
  and not on the tier's: 60 of its links were drawn and judged, 55 of those
  still publish, and 48 of THOSE were confirmed (sample `2026-09-12`, rubric
  `attribution`; 4 of the 60 are pairs an earlier wave also produced). Lower
  than the announcement tier's figure — 56 of the 60 sampled links now
  publishing under the tier, from its 2026-09-04 draw (54 drawn as
  announcement, six drawn under FPDS strata that this load re-attributed) —
  and that tier figure covers less of the tier than it looks: its draw
  predates 367 of the 1,075 links the tier now publishes. Both numbers go into
  the weighing before wave 5.
  Effort: days (one workflow run per ~50 chunks). **Status:** open (2026-09-19).
  *Addendum 2026-09-25 (ledger sweep; Task 25a and 25b review riders).* Two
  things to settle before wave 5 reads the queue: (a) the queue's
  700-character text cut leaves 24% of (record, lake_piid) pairs with the PIID
  outside the excerpt the lens reads (the wave-2 convention; 6,019 records,
  measured by the Task 25a review) — raise the queue-side cut and keep the
  packet excerpt at 700; (b) `site_meta.announcement_llm_scope.precision.drawn`
  counts JUDGED attribution verdicts while /methodology/ says reviewers
  "judged a random draw of 60" — equal today (60 = 60), so nothing renders
  false; rename the field or count the draw file's rows.

- **#117 `/methodology/` and `docs/methodology.md` are hand-mirrored, and a
  test binds two passages of the pair.** `site/src/__tests__/methodology-doc-mirror.test.ts`
  holds the §4 contractor-concentration passage identical on both surfaces
  (`94f71c24`, 2026-09-11) and the §4 company-family rule sentence to the
  page's helper (`cfcc9391`, 2026-09-25). Nothing else in the 404-line
  markdown is bound, although it carries 172 multi-digit numeric tokens on 77
  lines (counted 2026-09-25 at `118228f8`; 195 numeric tokens of any length
  sit on 92 lines — the first count mixed the two). The risk is not hypothetical: the High-tier
  census literals at `docs/methodology.md:188-200` (60 of the 1,133 links at
  high; a match basis on 748 of 1,074 announcement links) were a stale
  projection until chain C run 2 re-measured them (`e510d19d`, 2026-09-19);
  they equal `site_meta.link_adjudication.high` on the run-4 export
  (2026-09-25) by hand, not by test. Bind that sentence to the block first
  (Task 25b re-review), then decide whether a general page↔docs mirror gate
  is worth its cost (Task 7 round-3 rider) or the markdown should stop typing
  figures the page derives. Effort: hours for the census sentence; days for
  a general mirror. **Status:** open (2026-09-25).

- **#118 The Python suite shares state it does not own, so a red whole-suite
  run is suspect until re-run.** Three strands, each measured on the
  roadmap-completion branch: (a) `tests/jbooks/conftest.py:16-17` drops and
  recreates the ONE `govbudget_test` database per session, so a second pytest
  session on the machine destroys the first one's fixture database mid-run —
  failures land in untouched files and each passes alone (reviewer finding,
  2026-09-11); (b) the suite leaves DuckDB's global default connection in an
  aborted transaction part-way through, so later-sorting modules that call
  `duckdb.sql()` (`tests/test_dbt_build.py`, `tests/test_export_site_ledger.py`)
  die — reproduced on untouched files by Task 20a (2026-09-18), whose own
  helper therefore uses a private connection; (c) tests that read the shared
  export under `data/site/` fail when another checkout re-exports —
  `tests/test_flow_chart.py::test_real_export_labels_clean` was red on
  2026-09-24 against the other session's `flow_chart.json` and passed (23
  tests) on this branch's chain C run 4 export. Fix: a per-session database
  name, a private DuckDB connection in every test that queries, and a fixture
  copy for the real-export tests. Standing rule meanwhile (2026-09-19): every
  implementer ends on the WHOLE suite, and a red whole run is re-run before
  it is believed. Effort: hours.
  *Addendum 2026-09-25 (Task 26 fix wave; the review's minor 59, deferred by
  implementer A):* (d) the same species, read-only: `tests/test_collision_keys.py:83`
  and the other new tests that read the live lake make the DEFAULT suite
  depend on whatever another session last wrote there. Fix with (c): move
  live-lake assertions behind an opt-in marker (`-m live`) — a suite-policy
  change across several files.
  **Status:** open (2026-09-25).

- **#119 Three exporter handlers turn a failed program identity into bare
  keys.** `_fetch_program_identity` raises `UnresolvedSharedKeyError` on a
  shared key no axis resolves (`src/govbudget/jbooks/collision_keys.py:60`,
  Task 10) and `RuntimeError` on a present-but-stale `dim_programs` (R-27-8,
  `b9825ff4`). Three `except Exception` blocks turn either into a quiet
  fallback: `src/govbudget/export_site.py:5948-5955` (the decade identity
  becomes an empty `_ProgramIdentity`), `_build_slug_by_pe` (handler `:15003`,
  printing "slug map unavailable … sidecars keyed by bare pe_bli") and
  `_build_pe_by_slug` (handler `:15042`) — line numbers at `71d3e053`,
  2026-09-25. The prints show in a log, but a build that should stop
  publishes bare-keyed sidecars instead. Found by the Task 10 review
  (2026-09-11), which counted two. Fix: catch only the absent-table case, as
  `_require_account_column` does, and let identity errors propagate. Effort:
  hours. **Status:** open (2026-09-25).

- **#120 Three latent weaknesses in the district-year and basis value
  checks.** (a) Gate 24 leg r's `renderedAgreesWithLake`
  (`site/scripts/gates/datatruth.mjs:4306`) hand-mirrors `formatAmount`'s
  sub-$1,000 integer-dollar branch — gates are `.mjs`, `site/src/lib/format.ts`
  is TypeScript — and no test pins the pair (Task 18b fix round, 2026-09-11;
  its re-review swept 10,414 values with 0 false failures, so the two agree
  today). (b) `valuesAgree` (`site/scripts/gates/basis.mjs:329`, used by gate
  23 and gate 24) accepts a difference of 0.5·10^(⌊log10⌋−2), ten times looser
  than the display's half-unit for three-digit mantissas — ±$500,000 passes at
  $124.4M (Task 18b re-review, 2026-09-11). (c) Leg r has no non-vacuity floor
  on `grossChecked`, so the gross half could pass having checked nothing if a
  sample drew only gross = net cells (chain C run 4: 12 cells, 11 with a gross
  cell). Effort: hours. **Status:** open (2026-09-25).

- **#121 Gate 13's fetch-target sweep cannot see a directory fetch built from
  a constant prefix.** Task 14b taught the gate to resolve literal
  `/json/…/{x}.json` templates; `site/src/lib/cite-shards.ts:51-52` and
  `site/src/lib/workbook-cells.ts:89-90` build their URLs from module-level
  constants (`CITE_SHARD_BASE`, `cite-shards.ts:24`; `WORKBOOK_CELLS_BASE`,
  `workbook-cells.ts:66`), so a renamed or missing `cite-shards/` or
  `workbook-cells/` directory is invisible to it — and since Task 28b
  (`7df5152a`, 2026-09-24) district pages also resolve every citation through
  `cite-shards/`. Fix: resolve module-level string-literal prefixes (Task 14b
  review, 2026-09-11). Effort: hours. **Status:** open (2026-09-25).

- **#122 verify-phase5b1 gate 1: two structural limits of the citation
  sample.** (a) `_verify_subaward` (`src/govbudget/verify_phase5b1.py:1438`)
  cannot check that a subaward citation's `official_url` names THIS link's
  award — the row carries no PIID and `query_body` is fixed at three keys — so
  the guarantee is structural (the URL is built from the prime award), not
  re-derived (Task 11 review, 2026-09-11, 112 of 112 then checked; 114
  `subaward+lexicon` links publish at chain C run 4). (b) The 50-row sample
  (`_SAMPLE_SIZE`, `:93`) reserves `_MIN_PER_KIND = 5` (`:94`) per kind and is
  saturated at ten kinds; an eleventh citation kind hits the trim branch,
  which cuts subaward, usaspending and workbook rows first — whoever adds
  kind 11 raises the sample or re-weights the trim. Effort: hours.
  **Status:** open (2026-09-25).

- **#123 A shared code's dossier covers one member page, and the member that
  publishes the links has none.** `data/site/json/dossiers/` holds 50
  dossiers, two of them on split members — `3010-SCN` and `3050-SCN`
  (2026-09-25). `3050-OPN`'s sidecar publishes 50 Related Awards rows and has
  no dossier, while `3050-SCN` publishes none. `dossiers_present` accepts
  exactly one sibling per shared code, so a second member dossier would fail
  it, although the pipeline has been page-keyed since chain-B fix 3
  (`341ff934`, 2026-09-12). Design call: one dossier per member page (chain-B
  fix 2 round-2 review, 2026-09-12). Effort: days (one batch).
  **Status:** open (2026-09-25).

- **#124 The uningested-org census and the WHAT-IT-IS card rest on four
  unbound seams (Task 17b review minors, 2026-09-12).** (a) `whatItIsCard`'s
  `serviceOrg` and `serviceIngested` are derived from different sources
  (`site/src/lib/what-it-is.ts:230-232`) — identical on the rollup tier today;
  (b) `getUningestedCoverageOrgs` (`site/src/lib/data.ts:1622`) parses all
  2,562 program sidecars into memory and re-walks the directory
  `getPagesWithoutDetail` (`:1500`) already walks — make it one generator
  pass; (c) on an EMPTY payload the two sides disagree: `setIngestedServiceOrgs`
  falls back to A/N/F (`site/src/lib/program-tier.ts:78-82`) while the census
  reads the empty set — gate 21 leg (o) hard-fails that build, but the site
  code should mirror or throw on its own; (d) the per-org counts `/methodology/`
  renders — DHA (14), DEFW (4), IG (1) on the 2026-09-25 build — are derived
  but bound by no gate, although leg (o) tallies the same population. Effort:
  hours. **Status:** open (2026-09-25).

- **#125 Program pages print raw ALL-CAPS LDA client names in their
  lobbying-mentions list.** Task 21c (`156a8e26`, `796db562`, 2026-09-18) cased
  the filing pages and `/filings/` through `displayCompanyName`;
  `site/src/components/program-mentions.tsx:123,126` still renders
  `mention.client_name` verbatim. Measured 2026-09-25 on the chain C run 4
  export: 504 program sidecars carry mentions, and none of their 14,111
  mention rows' `client_name` values contains a lower-case letter. Fix: the
  same `displayCompanyName` + refused-name fallback the filing pages use, and
  a casing check on program pages beside gate 10 leg (e)'s. Effort: hours.
  **Status:** open (2026-09-25).

- **#126 Fifteen J-book citations fail the provenance spot-check's row-label
  test; the four diagnosed ones are highlight-placement defects, not wrong
  figures.** Measured by Task 22b over all 9,879 `jbook_pdf` citations of the
  2026-09-12 export (`task-22b-report.md` §3 and its fix round; not
  re-measured on the chain C run 4 export, whose fact ids may differ): 13
  label mislabels — 8 unrecognised row fragments, 2 on another program
  element's row, 2 on a procurement-quantity row, 1 on another project's row —
  plus 2 procurement TOA-basis failures (`7de179a27454c103`, E-7 Wedgetail
  P-40 p157: `200.000` highlighted on Gross/Weapon System Cost in the FY 2026
  Base column, where TOA reads `0.000`; `adbb3fa0ce67ded2`, p223: `11.979` on
  "Less PY Advance Procurement", TOA `50.000`). **Do not "correct" those two
  numbers under the smaller-true-number rule:** the published figures are
  right — `200.000` is the E-7's FY2025 TOA and `11.979` sits on the TOA row
  in the FY2024 column — and `resolution = 'ambiguous_first'` put the
  highlight on the FIRST printed occurrence of the amount, wrong row and
  wrong column. The same resolver explains the p41 pair (`a5b16504f30ca2e1`,
  `689b7c2f8e57e2f0`: `2027` highlighted on the Resource Summary header row).
  Four more cite a small integer off a row fragment (`2` ×2 on "2040 /", `5`
  ×2 on "41 05 01 0507 Marine Group") and are undiagnosed. The fix is a
  provenance re-run of the named facts with a better resolver, never a wider
  label tuple — ruling R-22b-1: the leg fails on any of them and carries no
  allowlist, so a build reddens only when the deterministic five draw one
  (≈0.76% per build). Counts to carry: fallbacks `summary_row` 271 /
  `pe_line` 461 / `title_match` 213 (+18 bullet-prefixed project rows the old
  test missed) over 4,712 project-level facts; 4,597 citations (46.53%: 2,135
  RDT&E + 2,462 procurement) accepted on their own PE's bare summary row, all
  of which print their own `pe_bli` on the cited page; 2,342 TOA comparisons;
  14 unreadable. Two gate gaps from the same review: the deterministic five
  are all RDT&E, so `toa_basis_checked` prints 0 on nearly every real build
  (chain C run 4: `toa_basis_checked=0`) — reserve one procurement slot in the
  stratifier; and `_row_basis_check` finds the TOA row only through the
  literal word `Obligation`, skipping (counted, printed) any P-40 that words
  it otherwise. Effort: hours for the stratifier; a provenance re-run for the
  fifteen. **Status:** open (2026-09-25).

- **#127 `COVERAGE_PROMISE_IDS` has no production consumer.**
  `site/src/lib/coverage-map.ts:113` lists the `/coverage/` rows whose target
  is planned-but-unscheduled work, and only a vitest file reads it
  (`site/src/lib/__tests__/coverage-map.test.ts:307-343`). No site gate binds
  a rendered "not scheduled" target to membership in the list, so a new
  promise row can render without joining it (Task 22a review, 2026-09-18).
  Fix: a gate 14 leg over the built `/coverage/` page — "not scheduled" ⇔
  membership. Effort: hours. **Status:** open (2026-09-25).

- **#128 `_require_account_column` reads a broken view as an absent table.**
  `src/govbudget/export_site.py:658-663` probes with `select * from {table}
  limit 0` under `except Exception: return False`, so a `dim_programs` or
  `fct_district_programs` VIEW that exists but fails to bind (marts are views
  by default) reads as ABSENT — an empty identity and no district rows —
  instead of failing. Unreachable in a production export today (the
  required-mart loop aborts first); found by the Task 27 round-2 re-review
  (2026-09-19). A `describe` / `information_schema` probe closes it. Standing
  obligation from the same review: every `dim_programs` fixture declares
  `account` and `account_title` — 82 fixture tests had silently taken the
  empty-identity path until `b9825ff4`. Effort: hours. **Status:** open
  (2026-09-25).

- **#129 Two feed and dossier checks still run on a subset or on a copy.**
  (a) Gate 8 leg (l) checks each HHI card's band against its destination page
  only for the cards `/feed/` renders — 75 hhi cards on chain C run 4 — while
  `feed.json` carries 1,745 cards (1,606 concentration_shift). Leg (p)
  (`7b1cba78`, 2026-09-24) already binds every card's page key and built page
  feed-wide; what remains is the figure — every `feed.json` card's
  destination should state the card's figure or say why not (Task 28a,
  2026-09-24). (b) `src/govbudget/dossiers/gate.py:134`
  (`_concentration_is_this_members`) carries its own copy of the shared-code
  concentration test ("Mirrors export_site._concentration_for's member
  test") instead of calling `export_site._concentration_owner` (`a0b7f72f`)
  — unify them, so the owner decision in #130 cannot move one and not the
  other. Effort: hours. **Status:** open (2026-09-25).

- **#130 OWNER CALL: withhold a shared code's concentration by LINKS (today)
  or by MONEY?** Program pages and `/feed/` withhold a shared budget-line
  code's concentration figure when more than one member key carries
  published links, high or medium (`export_site._concentration_owner`,
  #70/#82), while the figure itself is computed over HIGH-confidence links
  with positive obligations. Measured read-only 2026-09-25 on the chain C run
  4 lake: the feed withholds **28** concentration_shift cards (0145 ×9, 3010
  ×9, 3215 ×10), and in every one of those 28 program-years exactly ONE
  account carries positive high-confidence obligations (0145 → 1506N, 3010 →
  1611N, 3215 → 1507N) — no withheld figure a page or card would print mixes
  two programs' money. A money-aware test over high links would publish all
  28 cards and the six withheld member-page concentration blocks under
  0145-APN, 3010-SCN and 3215-WPN; a published 0145 block would also need its
  award and family counts restricted, because they count 0145-PANMC's three
  IDV links, whose obligations are all $0. Over ALL links the money does pool
  on two codes — 3010's 1810N member carries $214.4M and 3215's $18.3M of
  positive obligations on medium links — so a money-aware test over all links
  would still withhold 3010 and 3215. The branch keeps the link rule (the
  smaller claim, consistent with #70/#82); a change moves both surfaces
  together. The rule governs pages and cards only: the downloadable warehouse
  ships `fct_program_concentration` at code grain — the all-links basis for
  every code, the high-only index only where it clears the floor (63 of its
  536 rows) — 3010 and 3215 included (run-4 export, read 2026-09-25: hhi_all
  9,329 over $7.78B and 3,010, the pooled figures; hhi_high null on 3010,
  3,122 on 3215; restated in fix-wave round 2, which found "both bases for
  every code" overstated); `docs/methodology.md` §4 says both bases ship
  there; whether shared-code rows in that copy should
  follow `_concentration_owner` or be labelled code-level is part of this
  call (added 2026-09-25, Task 26). Decide with #129 (b).
  **Status:** open (owner call, 2026-09-25).

- **#131 A shared code with one member page plus a link key no member page
  reads would print a false sentence.** If a code's links sit on one member
  AND on a key no member page reads, the figure is withheld (two keys carry
  links) but `concentration_withheld` stays false for the member (one page is
  linked), so its WHO card would say "No company is linked to this line…"
  above its own Related Awards table. Found by the Task 28 fix round
  (2026-09-24); no such code exists today — the export prints a line whenever
  a link is filed under a key no member page reads (`export_site.py:9805`,
  and a clause on the feed census line), and chain C run 4's log carries
  neither. Options: a third reason sentence on
  the site, or fail the build on link keys no member page reads (owner).
  **Status:** open (2026-09-25).

- **#132 OWNER CALL: which merger-guidelines vintage the HHI bands follow.**
  `site/src/lib/hhi-band.mjs:41-42` uses the 2010 Horizontal Merger Guidelines
  thresholds (moderately concentrated from 1,500, highly concentrated from
  2,500) and the site calls them "DOJ/FTC bands"; the 2023 Merger Guidelines
  treat a market with an HHI above 1,800 as highly concentrated. Measured
  2026-09-25 on the chain C run 4 export: of `feed.json`'s 1,606
  concentration_shift cards, 3 sit between 1,800 and 2,500 — moderately
  concentrated under the 2010 bands, highly concentrated under 2023's — and of
  the 63 programs publishing an `hhi_high` band, 4 do. Whichever vintage is
  kept, label the bands by year. **Status:** open (owner call, 2026-09-25).

- **#133 After merge, main alone cannot rebuild the lake this branch deploys
  from (ruling R-C-6).** Chain C ran on a shared lake another checkout
  rewrote on 2026-09-24: commit `3786a6e9` ("Refresh award evidence with
  bounded safeguards and reconciled attribution", on `codex/f15-family-browser`
  — not on main `5dd7fb04`, not an ancestor of this branch) re-synced the
  FY2026 contracts and assistance archives and retired 81 duplicate rows
  through `scripts/reconcile_award_moves.py` — 74 contract and 7 assistance
  rows across 24 part files (contracts FY2018–FY2025, assistance
  FY2024–FY2025), with review and backup files under the main lake's
  `data/refresh/2026-09-24/rollback/`. This branch adopted that lake (ruling
  R-C-5) and carries no such script, so once it merges, a fresh sync +
  `dbt build` from main alone fails LOUDLY on
  `unique_fct_award_transactions_transaction_key` over those 81 duplicates
  until `3786a6e9`'s script and its test land on main. Merge note, measured
  2026-09-25: `3786a6e9` touches 66 files, 52 of which this branch also
  changed since `5dd7fb04` — ROADMAP.md, migrations 015–017, `export_site.py`,
  the district marts and their two assertions among them. **Status:** open
  (owner, 2026-09-25).

- **#134 OWNER CALL: "Data as of <build date>" reads like a currency
  claim.** Three surfaces stamp the BUILD time as the data's date — the site
  footer (`site/src/app/layout.tsx`), the `/methodology/` header ("Describes
  the corpus this build shipped — data as of September 25, 2026.") and the
  program print byline (`site/src/app/program/[peBli]/page.tsx:708`). On the
  chain C run 4 build that date is 2026-09-25, while the newest subawards
  download is 2026-06-11 and the newest contracts and assistance downloads
  2026-09-24 (the provenance sentence in /methodology/ §2 names the least
  recently refreshed dataset correctly). True as a snapshot date; a reader
  can take it as "current to". Wording call — e.g. "Built", or the stalest
  dataset's date beside it (Task 29 fix round, 2026-09-25). **Status:** open
  (owner call, 2026-09-25).

- **#135 OWNER/CURATION CALL: the RTX family's Rockwell Collins Australia key
  is now mostly an Elbit-parented member.** `data-seeds/entity_family_events.csv:5`
  merges "Rockwell Collins Australia Pty Limited" into RTX (acquisition
  2018-11-26, evidence `name-inferred`). After the 2026-09-06 FY2026 refresh
  regrouped the UEIs (the UEI-to-family resolution, not the budget-to-contract
  crosswalk — wording aligned 2026-09-25 with the seed note A corrected in the
  Task 26 fix wave), the key's 12 members are about 70% SPARTON DELEON
  SPRINGS, LLC, which filed ELBIT SYSTEMS LTD among its parents in
  FY2021–FY2025 and RTX CORP alone in FY2026 (re-measured 2026-09-25 and
  published in the RTX event note on `/companies/families/`); the display
  alias that relabelled the key was retired the same day (`cfcc9391`).
  Revisit the merge: keep it with a dated scope, split the Sparton member
  out, or drop the key from the curated family. **Status:** open (owner
  call, 2026-09-25).

- **#136 The display-alias seed carries dated evidence and one boundary
  family to watch.** `data-seeds/entity_display_aliases.csv` holds 17 rows
  (10 relabel, 7 pin); gate 24 leg l on chain C run 4 found 14 of the 200
  published families winning their label argmax by under 15%, all curated.
  Eleven rows are `measured_on` 2026-09-01 — true as dated, not re-measured
  after the 2026-09-06 refresh (six are 2026-09-24) — and L3 Technologies
  sits 201st, $6.9M below the #200 cutoff, with its dead seed row
  removed by `b5691ca5` (Task 29P), so the next refresh can bring it back as
  an uncurated near-tie that fails leg l. Re-measure the eleven and
  pre-review L3 at the next curation pass. **Status:** open (2026-09-25).

- **#137 CURATION CALL: four refreshed top-200 registry names are refused by
  the company-name casing allowlist.** Since the 2026-09-06 refresh reached
  the top 200, `site/src/lib/__tests__/company-name.test.ts:157` ("every
  published registry name is classifiable") fails on the shared export with
  four refusals — "A.P. MØLLER OG HUSTRU CHASTINE MC-KINNEY MØLLERS FOND TIL
  ALMENE FORMAAL" (on "MØLLER"), "M. C. DEAN, INC." (on "DEAN"), "NAN INC" (on
  "NAN") and "FCN, INC." (on "FCN") — measured 2026-09-25 (1 failed, 17
  passed). A refusal renders the name as filed, never mis-cased, which is why
  no verify gate is red; the vitest is, and stays red until the allowlist is
  extended with evidence per name. Chain C run 4 ran no vitest.
  **Status:** open (2026-09-25).

- **#138 The freshness sentence speaks per dataset; the archives are per
  fiscal year.** `/methodology/` §2 names the least recently refreshed dataset
  from each dataset's NEWEST download (subawards, 2026-06-11), but each
  USAspending dataset also holds older fiscal-year archives — contracts,
  assistance and subawards all carry files fetched 2026-06-10 in the 34-record
  `data/manifest.jsonl` (measured 2026-09-25). True as worded; a reader can
  take it as the age of every file. Say "newest download", or state the
  oldest fiscal-year file too, and let gate 24 leg m bind whichever is said
  (Task 29 fix round, 2026-09-25). **Status:** open (2026-09-25).

- **#139 OWNER ACTION: the deploy waits on Anthropic API credit, and the eval
  harness reports the block as an accuracy failure.** Since 2026-09-18 the
  repository's `ANTHROPIC_API_KEY` answers HTTP 400 "credit balance is too
  low" (direct probe during chain D's fix round 1), so `verify-phase5`'s
  `gate eval` — the text-to-SQL analyst — returns ERROR on every question:
  chain C run 4 (2026-09-25) scored 0/48 at $0.00 while `gate freshness` (43
  answers current) and `gate assembly` (8/8, including 5b3's 24 site gates)
  passed. Task 26's deploy gate requires `verify-phase5` to pass, so the
  owner's top-up is the last blocker. Second half, code: the run record
  (`data/research/eval-runs/eval-20260925T062947Z.json`, untracked) says
  `blocked: false` and "accuracy 0/48 < 44 threshold" — `verify_phase5.py`
  sets `blocked` only when no key is present (`:706-709`) or the agent exits
  mid-run (`:744-748`), so an all-ERROR, $0 run reads as a model failure;
  detect it and report BLOCKED.
  **Status:** open (owner action, 2026-09-25).

- **#140 OWNER CALL: should announcement evidence override an FPDS
  acquisition-program mapping on the same key?**
  `scripts/load_announcement_links.py:453` upserts on `(pe_bli, exhibit,
  fiscal_year, award_piid)` with `do update set method=…, confidence=…`, so an
  announcement link that lands on a row another route already owns
  re-attributes it. Measured by Task 25b (2026-09-19): 60 of the 1,189 rebuilt
  rows carried an older `created_at` — 45 `fpds-ap` medium, 13 `fpds-ap` low,
  1 `account` low, 1 `account+subagency` medium — six of them in the
  2026-09-04 precision sample, so the pinned tier figures moved with no
  verdict changing: announcement 51/54 → 56/60, `fpds-ap` 94/120 → 89/114
  (both still what `site_meta.link_precision` publishes at chain C run 4). The
  clause predates this branch (2026-09-04). Keep the override (the
  announcement is the stronger evidence of THIS program) or keep the older
  route's mapping and record the announcement as corroboration. Decide with
  #107 and #110. **Status:** open (owner call, 2026-09-25).

- **#141 OWNER CALL: a LORELEI-style attribution rule — send a DARPA award to
  the program element whose own narrative owns the effort its description
  names.** The `account+subagency` tier links a DARPA award to every DARPA PE
  in its account (#107: 0/60 on attribution). The 60 refutations in
  `data/research/precision/verdicts_2026-09-05_detail.json` show where many of
  those awards belong: 24 of the 60 reasons name another DARPA program
  element (counted 2026-09-25), and five sampled links over four awards
  (HR001115C0113–C0116, linked to 0601101E, 0602024E, 0601117E, 0602026E and
  0603469E) were refuted as LORELEI (Low Resource Languages for Emergent
  Incidents) awards, whose owning narrative a reviewer located at PE 0602303E,
  project IT-04. A description-level rule — the award's description names an
  effort, so link it to the PE whose narrative or project title names that
  effort — would replace the fan-out with one attributed link; it is the
  evidence-graded half of #107's option (c). Cost: a matcher, its own
  precision study, and a rebuilt tier. Decide with #107. **Status:** open
  (owner call, 2026-09-25).

- **#142 `/company/rtx/` publishes no lobbying mentions although 849 mention
  rows name its client.** Measured read-only 2026-09-25: `fct_program_lobbying`
  carries 849 rows over 30 filings for the client "RTX CORPORATION AND
  AFFILIATES" with `family_key` NULL, and `data/site/json/entity_details/rtx.json`
  lists 0 mentions; `lda_filings.parquet` holds 85 RTX-client filings at
  `match_method = 'none'`. The mart attributes a mention to a family only on
  a confirmed match (`dbt/models/marts/fct_program_lobbying.sql:42-50`), and
  no row of `dbt/seeds/client_aliases.csv` maps the "… AND AFFILIATES" client
  string to RTX. Found by the 2026-09-10 roadmap audit while checking #55.
  Fix: a curated alias row with its corporate evidence, then `influence
  rematch` + `dbt build` + export. Effort: hours. **Status:** open
  (2026-09-25).

- **#143 Gate 24 leg (p1) and its sidecar floor have no proof-it-can-fail
  test.** `runCrosswalkCountLeg` (`site/scripts/gates/datatruth.mjs`) is
  not exported and has no injected seam, and it holds (p1)'s id-order check,
  its per-slot value check and the `MIN_FLOW_SIDECARS` floor (`:2348`, 120).
  `site/scripts/gates/__tests__/crosswalk-counts.test.mjs` imports only the
  (p2)/(p3) helpers and `publishedLinkFigures`, so the permuted-row, wrong-value
  and 119-sidecar arms have never been seen to fail — while the
  `CROSSWALK_COUNT_IDS` mirror comment names (p1) as that hand copy's only
  enforcer. The code reads correct and chain C run 4 passed the leg. Fix:
  export pure `crosswalkRegistryFindings({rows, declared})` and
  `flowSidecarFloorFindings(count)` and unit-test swapped ids, a wrong value,
  a missing and an extra row, and 119 sidecars. Source: Task 26 final review
  (review-26, rejected 2:1 as a merge blocker, kept as a minor). Effort:
  hours. **Status:** open (2026-09-25).

- **#144 Re-base the branch's floors on the final corpus.** Every floor this
  branch added is dated to a pre-refresh measurement, and chain C kept each
  one where it stood through the verify chain (its runbook: "a first higher
  measurement is fine"). Chain C run 4 (2026-09-25) against the floors:
  feed leg l `MIN_RECONCILABLE_HHI_DESTINATIONS` 21 vs 45
  (`site/scripts/gates/feed.mjs`, whose own note said "raise it when a build
  measures more"); `MIN_FLOW_SIDECARS` 120 vs 314 flow sidecars
  (`site/scripts/gates/datatruth.mjs`); gate 9 leg f 130 districts / 800
  by-year rows vs 189 / 1,266 (`site/scripts/gates/district.mjs`);
  `_MIN_HIGH_ONLY_ROWS` 37 vs 63 (`src/govbudget/verify_phase3.py`); and gate
  10 leg (a), whose check is `MIN_FILING_COUNT` 4,000 against 5,393 pages and
  an index total of 5,393 — failing below the index total is the floor raise
  task-21c fix round 1 left to "a separate dated decision"
  (`site/scripts/gates/filing.mjs`). No floor is wrong (each fails on a
  collapse); each is loose. Decide per floor: re-derive at its stated
  percentage, never below its current value, with a dated note, and move the
  pins (`site/scripts/gates/__tests__/feed-hhi-destination.test.mjs`,
  `tests/test_verify_phase3.py` TestHighOnlyRowsFloor). Source: Task 26 final
  review (rejected 2:1 as Important; minors on the feed pin and gate 10).
  Effort: hours. **Status:** open (2026-09-25).

- **#145 The `/district/` index page-weight ceiling sits ~2x over the page.**
  `site/scripts/gates/build.mjs`'s `/district/` entry keeps 546,000 / 51,000
  against a measured 279,612 / 30,367 (chain C run 4) — ~95% raw and ~68% gzip
  over, against this file's ~6% convention — because Task 28b stopped
  embedding a citation slice in the page after the ceiling was set, and the
  drift leg only fires on overstated headroom. Lowering a ceiling is allowed;
  it was left for the build that weighs the Task 26 fix wave's rewrite of the
  index's link-mechanism sentence. Fix: re-base both numbers at ~6% over that
  build's measure. Source: Task 26 final review (minor). Effort: hours (one
  build). **Status:** open (2026-09-25).

- **#146 Gate 8 leg (o) checks a section sidecar's size, not its cards.**
  `site/scripts/gates/feed.mjs:1429` asserts a truncated section's sidecar
  holds `total − shown` cards of the right event type with pre-resolved
  fields, and leg (p) checks only their addressing; an exporter that wrote
  the wrong slice at the right length (for example the first `total − shown`
  cards, repeating the 75 already rendered and dropping the tail) passes both,
  and "Show all" renders the wrong set. Fix: compare the sidecar's card keys
  (`event_type`, `pe_bli ?? family_key`, `fiscal_year`), in order, against
  `feed.json`'s same-type cards `.slice(shown)`, with a proof-it-can-fail
  case. Source: Task 26 final review (minor). Effort: hours. **Status:** open
  (2026-09-25).

- **#147 Gate 21 leg (n) check 7 has no floor on the withheld population.**
  `site/scripts/gates/program-skeleton.mjs:1049` compares each sampled member
  page's WHO GETS IT card to its sidecar's `summary.concentration_withheld`,
  so an exporter that stopped withholding everywhere — and a page that
  followed it — would pass with zero withheld pages. Chain C run 4's export
  carries six withheld member sidecars (0145-APN, 0145-PANMC, 3010-OPN,
  3010-SCN, 3215-OPN, 3215-WPN; counted read-only 2026-09-25). Fix: count
  sidecars with `concentration_withheld === true`, fail under a dated floor,
  and pin a zero case in a unit test. Source: Task 26 final review (minor).
  Effort: hours. **Status:** open (2026-09-25).

- **#148 Gate 16's index-fold leg reads the first `/lineage/` ribbon in DOM
  order, not the topmost.** `site/scripts/gates/answerfold.mjs:256` measures
  `block.querySelector(sel)` — for `/lineage/` the first
  `[data-lineage-edge]` in document order — so a re-order in
  `lineage-flow.tsx` can move the measured number with nothing visible
  changing. Fix: take the minimum top over matches with a non-zero box, keep
  the zero-area finding when none has one; it can only be proved on a live
  run, which is why the fix wave did not take it. Source: Task 21d review
  minor via `task-26-polish-list.md` item 14. Effort: hours. **Status:** open
  (2026-09-25).

- **#149 Gate 10 leg (e) loose ends.** `site/scripts/gates/filing.mjs:74`
  takes the registrant marker as ANY non-h1 `[data-company-name]` whose value
  equals the registrant string, not the registrant line's own marker; and the
  vacuity block (`:300`) is inline, so its `casedSeen > 0` rule has no unit
  test. Fix: scope the lookup to the registrant line, extract
  `nameVacuityFindings({nameChecked, casedSeen})` and test it (whether to
  raise the floor toward the measured 49 of 50 is a separate dated
  decision). The fix wave capped the leg's findings at ten and sorted the
  sample; these two remain. Source: Task 21c review via
  `task-26-polish-list.md` item 15. Effort: hours. **Status:** open
  (2026-09-25).

- **#150 `generate-og.mjs` never prunes.** It writes a PNG per current page
  and skips fresh ones (`site/scripts/generate-og.mjs:234-242`) but deletes
  nothing, so `site/public/og/` carries twelve stale company cards that ship
  in `out/og/`: 212 `company-*.png` files against the 200 families in
  `data/site/json/entities_top.json`, and the twelve outside that list all
  date 2026-09-19, older than the run-4 export, so run 4 never wrote them
  (counted 2026-09-25; corrected in fix-wave round 2 from "eleven", which
  subtracted run 4's 2,811 rendered cards from the 2,822 PNGs instead of
  counting cards outside the current set). Fix: prune PNGs outside the current render
  set (gitignored build output), then re-read gate 11's count note. Source:
  chain C run 4 via `task-26-polish-list.md` item 16. Effort: hours.
  **Status:** open (2026-09-25).

- **#151 Nothing asserts the published (pe_bli, award_piid) grain.**
  `budget_line_awards` is unique on (pe_bli, exhibit, fiscal_year,
  award_piid), and `src/govbudget/jbooks/crosswalk.py` (`plan_crosswalk_org`
  `:330`, `crosswalk_org` `:480`) writes one row per line-edition, so a `--yes`
  multi-edition run (#78, #85) writes one pair several times;
  `dbt/models/marts/fct_program_concentration.sql:40`'s `links` CTE would then
  add that award's dollars twice to the family and program sums, and the
  precision/adjudication tallies count link rows. Unique today, measured
  read-only 2026-09-25: 12,601 `fct_budget_to_awards` rows over 12,601
  distinct pairs. Fix: a dbt uniqueness test on `fct_budget_to_awards`
  (pe_bli, award_piid[, account]) with a proof it can fail; collapse the
  `links` CTE (or DISTINCT in `_AWARD_LINKS_SQL`); EXISTS semi-joins in the
  tallies. Warnings now sit in #78, #85 and LAUNCH.md Step 0. Source: Task 26
  final review (rejected finding 0, minor 48), deferred by implementer A.
  Effort: days (dbt run and test). **Status:** open (2026-09-25).

- **#152 The district marts' award join can fan out on a second label.**
  `dbt/models/marts/fct_district_programs.sql:52` and
  `fct_district_programs_by_year.sql:39` join through `select distinct
  award_piid, pe_bli, account, program_title, organization`; a (pe_bli,
  account) that ever carried two titles or two organizations would emit two
  rows per award and `sum(t.obligation)` would count its transactions twice.
  Latent: at most one title and one organization over all 416 (pe_bli,
  account) pairs with a high link (measured read-only 2026-09-25). Fix, in
  lockstep in both models: `group by award_piid, pe_bli, account` with
  `min()` labels, proved byte-identical by a dbt run. Source: Task 26 final
  review (minor 49), deferred by A. Effort: hours. **Status:** open
  (2026-09-25).

- **#153 The mechanical crosswalk has no split-key guard.**
  `src/govbudget/jbooks/crosswalk.py` `crosswalk_org` / `plan_crosswalk_org`
  write organization-split and unresolved shared lines as readily as any
  other, while both link loaders exclude them (#70, #83). It has no rows on
  those keys only because every mechanical row is DARPA's and no split key is
  a DARPA line (measured read-only 2026-09-25: 124,500 mechanical rows in
  `budget_line_awards`, all `organization='DARPA'`; the 13 split keys are N,
  DTRA, DCSA, DMACT, OSD, DHRA and DLA codes). Fix: drop org-split and
  unresolved lines under `partition_split_keys`, handle account-split ones,
  with an org-split fixture test. Source: Task 26 final review (minor 6, code
  half), deferred by A. Effort: hours. **Status:** open (2026-09-25).

- **#154 The GAO identity checks a sum, not each key.**
  `src/govbudget/export_site.py:15002` raises only when `rendered_items !=
  accepted + inherited`; a missing key and a doubled key that offset exactly
  would pass. Fix: count matched rows per ratified (product, program, slug)
  key and raise on any count != 1, with a test. Latent (the run-4 identity is
  132 = 62 + 70). Source: Task 26 final review (minor 9), deferred by A.
  Effort: hours. **Status:** open (2026-09-25).

- **#155 `unadjudicated_methods` names a path only at exactly zero.**
  `src/govbudget/export_site.py:3881` lists a method only when none of its
  links is adjudicated, so `announcement+lexicon` left the list when 2 of its
  1,075 links gained an adjudication (run 4); the High sentence names that
  path for the other 1,073. A "none or almost none" predicate (say < 5%)
  changes an exported block and the rendered /methodology/ sentence, on a
  page with little gzip headroom (about 180 bytes under 43,000 on B's
  estimate after the fix wave) and no raise left under R-C-1. Decide with
  #109/#110. Source: Task 26
  final review (minor 61), deferred by A. Effort: hours plus a page-weight
  trim. **Status:** open (2026-09-25).

- **#156 `links_new_this_pass` is frozen when the scope row is written.**
  `scripts/load_announcement_scope.py` stores the count of links the pass
  added at write time; /methodology/ renders it as the tier's draw gap. True
  on the current corpus (measured 2026-09-25: the 392 wave-4-only surviving
  pairs give 367 published in Postgres and 367 in the mart), but stale the
  moment links move without a new scope row. Fix: re-derive at export time
  (an exported value) or date the rendered figure. Source: Task 26 final
  review (minor 45), deferred by A. Effort: hours. **Status:** open
  (2026-09-25).

- **#157 The loader's "replacing N stored … links" line is untested.**
  `scripts/load_announcement_links.py:437` prints the count an operator is
  told to read before the partition rebuild commits (LAUNCH.md Step 0), from
  inside `main()`, which reads the real lake and wave files. Fix: extract the
  count query and pin it (and the `OWNED_METHODS` join) with a capsys test.
  Source: Task 13 minors via `task-26-polish-list.md` item 19, deferred by A.
  Effort: hours. **Status:** open (2026-09-25).

- **#158 verify-phase5b1's row-label leg: five robustness items.**
  `src/govbudget/verify_phase5b1.py`: `_toa_column_value` needs a tie rule
  and a numeric-shape guard (latent: widest highlight 38.52 pt against a ~50
  pt column pitch, 0 of 250 disagreements); the 4,597 PE-level summary-row
  accepts are invisible on the CLI line; wrapped summary labels ("Plus Cost
  To / Complete") match nothing; `_label_failure_species` calls any `token:`
  row "another project's row"; `_load_fid_to_jbook_detail` materialises all
  21,993 detail rows to look up at most 50. All latent (0 today per
  `task-22b-report.md`). The fifteen failing citations themselves are #126.
  Source: Task 22b review via `task-26-polish-list.md` item 17 (the rest
  after A's partial fix). Effort: hours each. **Status:** open (2026-09-25).

- **#159 `refresh.py`'s section banner undercounts its doors.**
  `src/govbudget/refresh.py:172` still reads "── the two doors to the outside
  world ──" above `_run`/`_capture`, while the module docstring (Task 26) now
  names the preflight checks, `drift_report` and the run record too. Fix:
  "the two subprocess doors". Source: implementer A, found after its commit.
  Effort: minutes.
  *Superseded marker, as filed in `2ef7471e`: open (2026-09-25).*
  **Status:** CLOSED 2026-09-25 — `2631383e` (banner now reads "the two
  subprocess doors (the module docstring lists the others)"); filed after
  the fix landed.

- **#160 The latent SAM clause names the wrong registration.** When
  `companies_with_sam > 0`, `/methodology/` (`site/src/app/methodology/page.tsx:906`)
  and `site/src/components/sam-registration.tsx:70` say the family's SAM.gov
  registration is "the registration of the family's largest member", but the
  join key is `max(coalesce(parent_uei, recipient_uei))`
  (`src/govbudget/export_site.py:5168`), so for a member with a registered
  parent it is the parent's. Renders on 0 pages (`companies_with_sam` = 0 on
  run 4). The three twins are bound by `site/src/__tests__/sam-registration.test.tsx`
  and must change in one commit across B's and A's files. Source: Task 26
  final review (minor 12), deferred by B. Effort: hours. **Status:** open
  (2026-09-25).

- **#161 "No contract award is linked to this line" can be false on a
  shared code.** The lobbying tier's sentence
  (`site/src/app/program/[peBli]/page.tsx:1591`) is true of the page's
  program but not of its budget line when an unlinked member sits on a
  linked shared code (0 pages today). The fix — "…linked to this program" —
  needs four files in one commit: the page (B), gate 21's anchored
  `WHO_LOBBY_TEMPLATE` (`site/scripts/gates/program-skeleton.mjs:2940`, C),
  `src/govbudget/export_site.py:7570` and
  `tests/test_who_gets_it_fallbacks.py:227` (A). Not taken in the fix wave:
  changing the gate's anchor alone would red it against the shipped page.
  Source: Task 9 review via `task-26-polish-list.md` item 8, deferred by B.
  Effort: hours. **Status:** open (2026-09-25).

- **#162 One plate-geometry module for the flow chart and its gate.**
  `site/src/components/flow-chart/flow-chart.tsx:759` and
  `site/scripts/gates/flowdown.mjs:627` each carry `subtractRects`; nothing
  compares them, and gate 22 leg h1 checks only the rendered result (both
  comments now say so). Fix: a shared `site/src/lib/plate-geometry.mjs`
  imported by both, so the gate tests the code the page runs. Source: Task 26
  final review (minor 22/29), deferred by B. Effort: hours. **Status:** open
  (2026-09-25).

- **#163 The /district/ reconciliation's "314 of 1,938 programs" is off by
  three.** `site/src/app/district/page.tsx:253` says the linkable subtotal
  ties back to "{flows} of {programs} programs" (renders 314 of 1,938), but
  the subtotal sums the district rows of 317 program elements: 356010,
  845550 and 9140MA7804 carry district rows with only zero or negative
  obligations and so draw no view (measured read-only 2026-09-25 on the run-4
  export: 317 distinct `pe_bli` in `data/site/json/districts/`, 314 flows
  sidecars). The fix wave's scope-note rewrite left this sentence as it was.
  Fix: state 317 through a declared count gate 24 leg (p2) admits, or align
  the exporter's two criteria. Source: implementer B (Task 26), deferred.
  Effort: hours.
  *Superseded marker, as filed in `2ef7471e`: open (2026-09-25).*
  **Status:** CLOSED 2026-09-25 — `594d1f0c` (the reconciliation sentence
  prints no program count, and its /methodology/ twin, the district lens,
  says a district gets a page when a high-confidence link "records an
  obligation there — a consequence of the crosswalk's current scope", where
  it said the link "places obligated dollars there" within a "current
  314-program scope": GA-02's only link, 356010's, has no positive
  transaction); the true count is 317 program elements (3 with only zero or
  negative obligations) — printing it would need gate 24 to accept it.

- **#164 /downloads/ counts 204 J-book PDFs while 225 ship.**
  `site/src/components/download-cards.tsx:256` renders
  `site_meta.pdf_count` (204: the documents the export copied this run),
  while `data/site/pdfs/` holds 225 files — the exporter never prunes stale
  ones, and the R2 sync ships the directory (counted 2026-09-25). Fix: prune
  at export, or count the directory. Same species as #150 (OG images).
  Source: implementer B (Task 26, polish 18 follow-up), deferred. Effort:
  hours.
  *Addendum 2026-09-25 (Task 26 closing):* since `594d1f0c` /downloads/
  renders no PDF count — its line reads "`pdfs/` — SHA-named J-book PDFs",
  and `download-cards.tsx` accepts `pdfCount` without rendering it — so the
  page no longer prints the wrong figure. The exporter half stays open:
  `site_meta.pdf_count` is 204, the documents chain E's export copied, while
  `data/site/pdfs/` holds 225 files because nothing prunes it (both
  re-counted after chain E's export, 2026-09-25). A page may print the
  count again once the exporter prunes or counts the directory.
  **Status:** open (2026-09-25).

- **#165 verify-phase3's trace leg prints a different `top_family` from run
  to run.** `trace_gate3` (`src/govbudget/verify_phase3.py:233-236`) samples
  `select pe_bli, top_family_all from fct_program_concentration where
  top_family_all is not null limit 1` with no ORDER BY, and
  `fct_program_concentration` is a view in the lake, so the family the CLI
  prints (`top_family=…`, `src/govbudget/cli.py:1228`) is whichever row
  DuckDB returns first. Chain E ran that query 20 times read-only and got 9
  different families; its verify-phase3 printed `top_family=RTX` where run
  4's printed GENERAL ATOMICS with every mart count unchanged, and a second
  20-run re-measure the same day (2026-09-25) again returned 9. The leg
  still PASSes — it needs only some family to exist — so the harm is a
  nondeterministic gate print that reads as a data move when nothing moved.
  Fix: order the sample (e.g. `order by pe_bli`). Source: chain E's report
  (`chain-E-report.md` §7, the branch ledger). Effort: hours.
  **Status:** open (2026-09-25).

*Integration note 2026-09-25 (merge of `codex/f15-family-browser`).* The four
entries below were filed as #89–#92 on that branch; this branch had already
used #89–#92 (the service decade backfill, cross-sibling page resolution, the
5G evidence pack and outlay-stage flows above), so they are renumbered
#89 → #166, #90 → #167, #91 → #168 and #92 → #169. Their text is otherwise
the live branch's, with three kinds of change. The two cross-references
between them are renumbered to match: #168's "Measure return/reuse using
#167" (was #90) and #169's "supporting work alongside #166" (was #89). Under
R-INT-5 (the findings log, 2026-09-25), each entry's superseded "Status: OPEN
— scoped 2026-09-22" marker is relabelled "Status (2026-09-22):", with no
words deleted. And #166, #167 and #168 each end with a plain Status line,
added at the integration, restating the live branch's 2026-09-24 state
(PUBLISHED, PARTIAL and PUBLISHED); #169's own PARTIAL line already ended
it. So the one plain Status line in each entry is its latest state. Plans
and reports written on that branch that cite "Roadmap #89–92" (or #89–90,
#89–91, #90, #92) mean these four.

- **#166 Three complete flagship investigation journeys.** Start with the
  existing F-15 family experience, then reuse the answer/receipt pattern for
  Virginia Class Submarine and Cyber Security Research to cover physical and
  nonphysical programs. Each brief answers what the program does, which record
  and fiscal status the amount represents, what a comparable change establishes,
  which recipients are actually supported (or what remains unknown), and how to
  inspect and reuse the evidence. Use the current F-15 workspace, research tray,
  source drawers and shareable selection; their implementation is already
  recorded above. Verify current local/preview/live state before describing
  anything as newly built or shipped.
  **Parallel scope:** complete the current visual/task review and create the
  concise answer brief from existing cited facts and formatters. Preserve
  variant, record, year and receipt selection in share/restore paths. Additional
  3D asset detail is not an acceptance requirement for this work package.
  The first reusable output is **Copy answer** for F-15EX procurement: what this
  record funds, amount/year/status/basis, the source citation and a link restoring
  the selected view. Use a deterministic format and already-supported text;
  the recipient should understand the answer outside the site and reopen its
  evidence. This extends existing citation copying rather than replacing it.
  **Acceptance:** a reader can identify the relevant program and fiscal status,
  open the exact supporting page/cell/passage, and save or share a view that
  restores the same context; desktop, mobile, keyboard and copy/restore paths
  are checked on the release build. Copied findings retain source IDs, dates,
  basis and scope. Relevant trust fixes gate dependent claims, not all UI work.
  **Status (2026-09-22):** OPEN — scoped 2026-09-22; builds on existing F-15 work, with final
  acceptance/publication status to be checked rather than inferred from git.

  **Implementation update (2026-09-22):** added deterministic **Copy answer** to
  the F-15 funding view and Virginia/Cyber exhibits, with exact selected amount,
  fiscal year/status/basis, shared footnotes, independent narrative receipt and
  restoring URL. Existing tray, share and receipt controls are reused. Missing
  anchored evidence disables the exhibit answer; blocked clipboard exposes a
  selectable fallback. Desktop/mobile release-preview checks passed for native
  copying, receipt opening and selection restore. The full release gate suite
  still has the blockers recorded in the [delivery note](plans/2026-09-22-parallel-product-delivery.md).
  The family page now includes the rule-selected F015EX request and a separate
  ledger of the other five records before navigation, with the EPAWSS absence
  explicit. Final site suite: 93 files / 1,366 tests; final F-15 size 67,875 gzip
  bytes against the unchanged 70,000-byte ceiling. Source, fold, accessibility
  and typography checks passed on the fresh production build.
  **Status (2026-09-24):** PUBLISHED — the answer/receipt journey is live and
  the refreshed release is verified. Human comprehension remains unmeasured;
  the five-reader pilot is the next product acceptance step.
  **Status:** PUBLISHED, as of 2026-09-24 (restated 2026-09-25 in grep-able
  form at the integration merge).

- **#167 Measure reader success on the existing journey.** Basic Vercel
  Analytics is already installed; add a small action funnel for brief/funding
  selection, receipt opened, official source opened, citation copied, view
  shared, receipt saved/exported and watch-feed selected. Reuse existing action
  handlers and record completed actions rather than failed clipboard attempts.
  Event fields should describe the page/program/action, not free-text research
  queries or saved notes.
  **Parallel scope:** define events, instrument the existing F-15 journey and
  prepare five target-reader sessions with one concrete investigation task.
  This does not depend on expanding coverage or introducing an account system.
  **Acceptance:** verify each event fires once on the intended action; establish
  a baseline for answer → receipt → reuse completion and record observed
  confusion/time-to-evidence. Pilot usability goal: at least four of five readers
  complete the task without help and correctly distinguish the fiscal status.
  A five-person pilot is usability evidence, not a population retention estimate.
  **Status (2026-09-22):** OPEN — scoped 2026-09-22; first parallel implementation slice.

  **Implementation update (2026-09-22):** added the controlled reader-action
  event helper and instrumented selection, central receipt opening, official
  source links, successful copy/share/save/export and watch actions. Tests cover
  one event per action, failed-copy suppression and analytics resilience. The
  [five-reader session kit](plans/2026-09-22-reader-pilot.md) includes tasks,
  recording sheet, success criteria and interpretation limits. Aggregate events
  do not establish per-person funnel completion; no custom identifiers added.
  **Status (2026-09-24):** PARTIAL — instrumentation and study kit are live.
  Production page-view reporting and two HTTP-200 custom-event sends are
  verified; Hobby does not provide custom-event reporting. Human baseline and
  all five reader sessions remain unmeasured. The pilot needs no paid plan.
  **Status:** PARTIAL, as of 2026-09-24 (restated 2026-09-25 in grep-able form
  at the integration merge).

- **#168 Reviewed changes briefing and discoverable watch feeds.** Assemble a
  small set of source-backed change explanations around the flagship programs:
  what changed, compared with which year/edition/status, why the available
  documents explain it, what remains uncertain, and links to both receipts.
  Improve answer-led entry points from home/search and explain the existing
  program/company RSS/Atom links as following future changes. Feeds already
  exist; do not count a new subscription backend or account system as necessary
  for this first release.
  **Parallel scope:** build the reusable briefing card, entry points and feed
  affordances using reviewed, explicitly dated examples. Do not present a
  missing edition as cancellation or a temporary transfer as permanent lineage.
  **Acceptance:** each explanation is reviewed against its sources; links open
  the correct before/after receipt; feed links resolve for eligible programs;
  empty/unsupported coverage is explained; source date and publication date
  remain distinct. Timely/recurring-update promises depend on #8's validated
  refresh-to-publication cycle. Measure return/reuse using #167; decide cadence
  from available meaningful changes rather than inventing weekly news.
  **Status (2026-09-22):** OPEN — scoped 2026-09-22; UI and dated examples can proceed in
  parallel, freshness promises depend on #8.

  **Implementation update (2026-09-22):** added three dated PB2026 comparison
  cards on `/feed/#budget-briefings`, linked from home and indexed for search.
  Both endpoints keep their own status and receipt. Explanations state when a
  cause is unestablished; F-15 and Virginia disclose P-1/P-40 scope differences.
  Source/value drift blocks the build pending review. Separate assistant review
  checked all six endpoints and all three exact excerpts; human sign-off is not
  implied. Program/company/feed controls explain RSS/Atom, copy feed addresses
  with fallback, retain eligibility rules and avoid promising a cadence.
  **Status (2026-09-24):** PUBLISHED — reviewed cards and watch controls are
  live; the refresh-to-feed publication cycle passed. No extra spending-change
  briefing was added from archive backfills or revisions. Recurring cadence
  and reader return/reuse evidence remain open.
  **Status:** PUBLISHED, as of 2026-09-24 (restated 2026-09-25 in grep-able
  form at the integration merge).

- **#169 Jev internal editorial-review pilot.** Use the tested adapter as the
  starting point for a bounded offline review of one existing dossier/briefing
  batch: supplied claim + exact source evidence → review flag. Target unsupported
  outcomes, request-versus-spending wording, scope overstatements and incorrect
  program identities. Keep arithmetic, fiscal fields and exact citation
  resolution in deterministic checks. Preserve the static-site architecture;
  no browser credential or public inference endpoint is needed for this pilot.
  **Evaluation:** freeze the rubric and compare with existing validators/manual
  review on a fresh human-reviewed set, separate from the 155 development cases.
  Report false approvals, false flags, abstention/review volume, useful
  corrections and net reviewer time. The earlier prompt-tuned result and a
  confidence cutoff alone do not establish a publication threshold.
  **Acceptance:** retain reproducible source/claim/model/question/decision
  records, manually review the flags, and record a continue/stop decision based
  on demonstrated editorial benefit. Keep scope to one batch until that decision;
  flagging never automatically rewrites a claim, asserts a link or publishes.
  **Deferred product bets:** public "check any claim," automatic change stories
  and "follow the promise" require their own retrieval, source-coverage and
  held-out evaluation plans. Document organization is not the product objective.
  **Status (2026-09-22):** OPEN — scoped 2026-09-22; API experiment complete, production
  integration not implemented; supporting work alongside #166 rather than its
  prerequisite. [Experiment](../../data/research/jev-eval/2026-09-22-report.md).

  **Implementation update (2026-09-22):** implemented a bounded offline packet
  builder and review queue, with immutable prepared evidence, source hashes,
  exact cited rows/passages and recursive derivation inputs. Ran all 17 retained
  claims in one existing dossier: 17 requests completed; nine model flags despite
  17 resolvable citations. Separate assistant review upheld the flags and
  questioned three supported decisions (two clear errors plus a scope concern).
  No claims were rewritten/published. See the [pilot report](../../data/research/jev-editorial/2026-09-22/report.md).
  **Status:** PARTIAL — engineering experiment and assistant review complete;
  keep Jev internal. Human held-out labels, false-approval/false-flag rates and
  net reviewer time remain unmeasured. No expansion or model publication gate.

- **#170 Crosswalk lets the last account win on (pe_bli, exhibit, FY, org)
  identities that carry two or more accounts.** Re-measured read-only from
  Postgres `budget_lines` on 2026-09-25, counting distinct `account` per
  (pe_bli, exhibit, fiscal_year, organization): 47 of the 22,425 identities
  carry two or more accounts, and 31 of those carry exactly two. By
  organization: N, 30 with two and 1 with seven; F, 1 with two and 1 with
  six; A, 1 with seven; '' (empty), 4 with four, 6 with five and 3 with
  seven. The 13 empty-organization identities are all code `9999999999`, and
  the default run never processes them: without `--org`, the CLI's
  organization list keeps only `organization is not null and organization <>
  ''` (`src/govbudget/cli.py:861`). The default run therefore touches 34 of
  the 47 (N 31, F 2, A 1). Where the last account wins: `_load_lines`
  returns one canonical line per (pe_bli, exhibit, fiscal_year, account) and
  sorts the lines by account first (`src/govbudget/jbooks/crosswalk.py:348`),
  so an identity's accounts run one after another, in account order. Each
  line upserts on `budget_line_awards`' key UNIQUE (pe_bli, exhibit,
  fiscal_year, award_piid) (`crosswalk.py:599`), which names no account, and
  `crosswalk_org` does not write the table's `account` column (migration
  014). So when an award is a candidate under two of an identity's accounts,
  the later line's `do update` (`crosswalk.py:600`–`604`) replaces the
  mechanical row's confidence, method, score, rationale and
  `matched_obligation` with its own, silently. No stored row shows this yet:
  the only mechanical rows are DARPA's 124,500 (`account` 114,637,
  `account+subagency` 9,336, `account+tokens` 527), and no DARPA identity
  carries two accounts. The 107 rows on the 34 identities (all organization
  N) come from the evidence loaders (`announcement+lexicon` 25, `fpds-ap` 36,
  `subaward+lexicon` 46), which the upsert's method guard
  (`crosswalk.py:605`) never overwrites. The key names no organization
  either: 10 (pe_bli, exhibit, fiscal_year) triples are filed by two or more
  non-empty organizations (codes 20, 30 and 500 in FY2024–FY2026, and code
  `FY2024CR` in FY2025), so two organizations' runs can also write one row.
  The live branch's planner (`codex/f15-family-browser`, not merged) aborted
  on an ambiguous or missing account instead. Fix: fail loudly before any
  write. The CLI already plans every organization before its first write; the
  plan should exit non-zero, naming each identity and its accounts, when two
  planned lines share (pe_bli, exhibit, fiscal_year), across accounts or
  across organizations, and `crosswalk_org` should refuse the same input when
  it is called directly. Source: `src/govbudget/jbooks/crosswalk.py`, the
  integration's Python report (`integration-report-python.md`, the branch
  ledger) and #78, #85 above. Effort: hours.
  **Status:** open (2026-09-25; scheduled in the decisions wave).

- **#171 The crosswalk's detail tokens are no longer scoped to the line's own
  organization, edition and account.** The merge dropped the live branch's
  scoping. On `codex/f15-family-browser` (81929a6b) the planner added a
  project title's tokens to a line only when the title's document had the
  line's organization and fiscal year and the detail row's account was the
  line's account or NULL. The merged `crosswalk_org` reads every
  non-superseded `budget_line_details` row
  (`src/govbudget/jbooks/crosswalk.py:551`), indexes the project-title tokens
  by `pe_bli` alone (`crosswalk.py:555`–`558`) and adds them to every line of
  that code (`crosswalk.py:583`); `_grade` returns `high` / `account+tokens`
  once the overlap with an award's description tokens reaches `min_overlap`,
  2 by default (`crosswalk.py:502`–`508`). So a line can reach the high tier
  on project titles from another organization's book, another edition or
  another account. What bounds the published effect today:
  `dbt/models/marts/fct_budget_to_awards.sql:70`–`76` publishes an
  unadjudicated `account+tokens`/`high` pair as `medium` (#75 addendum,
  ruling 3), and an adjudicated pair publishes its adjudicated confidence, so
  no token match publishes as `high` without an adjudication verdict. Measured
  read-only 2026-09-25: `fct_budget_to_awards` publishes 251
  `account+tokens` links, all DARPA, edition FY2026, exhibit R-1 (113
  unadjudicated at medium; 104 adjudicated medium and 34 adjudicated high).
  With each award's description tokens re-derived from today's contracts
  lake, all 251 still overlap the unscoped tokens in two or more words, and 82
  fall below two under the scoped rule: 50 unadjudicated and 32 adjudicated.
  All 82 lose the overlap on the edition leg alone (the DARPA detail rows
  carry no account, and scoping by organization alone loses none): the words
  that lift them to two come only from the code's project titles in other
  editions. Re-graded under the scoped rule, the 50 unadjudicated links fall
  to `account`/`low`, which the mart does not publish; the 32 adjudicated
  links would carry `account+subagency` and keep their adjudicated medium.
  Fix: scope the detail tokens to the line's own (organization, edition,
  account), as the live branch did, and re-measure the published links after
  the next crosswalk run. Source: `src/govbudget/jbooks/crosswalk.py`,
  `dbt/models/marts/fct_budget_to_awards.sql`, #75 and #85 above. Effort:
  hours.
  **Status:** open (2026-09-25).

- **#172 `export_site.py` reads through DuckDB's process-wide default
  connection, and several of those reads fall back silently.** 14 call sites
  in `src/govbudget/export_site.py` run `duckdb.sql(...)` (imported as
  `_duckdb` or `_duckdb2`), which uses the one default connection that every
  module in the process shares. Several sit inside `try` / `except Exception`
  blocks that swallow the error: `export_site.py:2947` records a written
  parquet's row count as 0; `:5042` drops the paymentaccuracy.gov source URL
  from the improper-payment derived citations' inputs; `:8626` and `:8641`
  leave the lobbyist-to-filing and filing-URL maps empty. On DuckDB 1.5.3,
  one failed statement on that connection while an earlier result is still
  pending leaves it aborted for the rest of the process ("Current transaction
  is aborted"). The post-merge Python fixer found this through the test
  suite: `tests/test_fiscaldata.py:42` leaves a pending
  `duckdb.sql(...).fetchone()` result, and `scripts/precision_study.py:179`
  then runs a lake query on the same connection that fails and is caught.
  After that the narratives read (now `export_site.py:10081`) raises, loudly,
  while the guarded reads above would degrade quietly. The tests are isolated
  (an autouse fixture in `tests/test_program_member_enrichment.py`); the
  exporter is not. Whether a real export has ever degraded this way is
  unmeasured. Fix: give each reader its own `duckdb.connect()`, and make the
  guarded reads report what they dropped. Source: the integration's Python
  fixer report (`integration-fix-python.md`, the branch ledger). Effort:
  hours.
  **Status:** open (2026-09-25).

- **#173 /methodology/'s dbt-assertion count silently falls back to the last
  export's number.** `buildCheckCounts` in `site/src/lib/data.ts` recounts
  the test nodes in `dbt/target/manifest.json` only when that file exists
  (`data.ts:535`). When it is missing, the object spread at `data.ts:512`
  keeps the `build_checks.dbt_assertions` that `site_meta.json` carries, and
  when it is unreadable the `catch` at `data.ts:541` copies that value back.
  That value is whatever the last `export-site` in the shared data lake
  wrote, from its own checkout's manifest
  (`src/govbudget/export_site.py:1324`–`1331`, which omits the field when the
  manifest is missing). Gate 24 leg e skips the dbt comparison when the
  manifest is missing (`site/scripts/gates/datatruth.mjs:623` and `:656`), so
  nothing flags it. `dbt/target/` is gitignored (`.gitignore:7`), so a fresh
  checkout or worktree has no manifest until dbt runs. Measured 2026-09-25:
  the shared
  `site_meta.json` carries 118 dbt assertions and 24 site gates; the main
  checkout's manifest (generated 2026-09-24) holds 100 test nodes and the
  integration worktree's (generated 2026-09-25) 118. The site-gate count had
  the same drift and, since the integration, fails the build instead
  (`data.ts:529`). Fix: treat a missing or unreadable manifest the same way,
  or print "—"; never print the lake's number. Source: `site/src/lib/data.ts`.
  Effort: hours.
  **Status:** open (2026-09-25).

- **#174 `docs/methodology.md` §5 says every table shows a "data as of"
  date; the site does not.** Checked read-only 2026-09-25. No component in
  the merged `site/src` renders a "data as of" date; the only occurrence is
  the comment at `site/src/app/methodology/page.tsx:503` recording that the
  redesign retired it. None of the 2,854 HTML pages with a `<table>` in the
  main checkout's last build (`site/out`, 2026-09-24) contains the phrase,
  and neither do five production pages fetched the same day (`/`,
  `/methodology/`, `/program/0207146F/`, `/data/`, `/companies/`). What the
  site prints instead is the export's build date: the footer's "Site export
  <date>. Source dates vary by dataset." (`site/src/app/layout.tsx:122`),
  /methodology/'s "generated <date>", /data/'s "Built: <date>" and the
  program page's print byline. The §5 sentence is false today. Fix: reword
  it to what the site shows — the site export's build date, not a data date:
  the footer's "Site export <date>. Source dates vary by dataset."
  (`site/src/app/layout.tsx:122`), the /methodology/ header's "generated
  <date>" (`site/src/app/methodology/page.tsx:509`) and /data/'s "Built:
  <date>" (`site/src/app/data/page.tsx:236`) — following #134's wording call
  (the controller's recommendation under the owner's delegation, 2026-09-25:
  "Built <date>"), which the decisions wave implements after the integration
  deploy. Source: `docs/methodology.md`. Effort: hours.
  **Status:** open (2026-09-25).

- **#175 Gate 27 (copy) ships red in production; the integration exempts
  only production's pre-existing hits (R-INT-7).** Gate 27
  (`site/scripts/gates/copy.mjs`, the live branch's VOICE.md lint from
  93bda149) was run unchanged against production's build (the main
  checkout's `site/out`, `git_head` 81929a6b) on 2026-09-25. It fails with
  1,049 hits on 146 sampled pages (897 distinct page, leg and text
  triples). Hits per leg: 1 (invitation verb) 333; 2 (dive / glance / one
  place) 23; 3 (tricolon) 22; 5 (fragment stack) 9; 7 ("follow the money")
  1; 8 ("a different way into") 1; 9 (marketing adjective) 5; 11
  (marketing-deck arc) 2; 13 (em-dash pile-up) 31; 14 (question heading) 1;
  15 (arrows) 3; 16 (second person) 6; 18 (pointer verb) 171; 21 (bare
  "family") 2; 23 (serial comma) 87; 29 (Title Case h2/h3) 169; 31 (exposed
  enum) 8; 36 (second spelling of a fixed action) 150; 38 (program meta
  title shape) 25. The integration build (2026-09-25) carried 1,038 hits
  before its copy fix. Nine were not in production's build, on /coverage/,
  /district/, /methodology/, /downloads/, one filing page and three program
  pages: seven were reworded at their source, and two were marked as what
  they are, words unchanged — the registrant's legal name on the filing page
  carries `data-copy-slot="data"`, and the /downloads/ column names render as
  `<code>`, which also cleared four of production's leg-31 hits on that
  page. The 1,025 hits left are all in production's build under the
  same page, leg and text. `site/scripts/gates/copy-allowlist.json` exempts
  them in 584 entries: 582 name one page, and 2 use `"*"` for the header and
  footer strings "Explore" (leg 1, 292 hits) and "Visual field guide"
  (leg 36, 147 hits). Two hazards in the allowlist's matching: an entry
  matches any hit on its page and leg whose text CONTAINS the entry's text, so
  the `"*"` "Explore" entry lets every leg-1 text containing "Explore"
  through on every page until it goes; and the per-page entries on templated
  pages follow the gate's sample (the first 25 pages per template, in sorted
  directory order), so a data change that shifts the sample fails the gate on
  stale entries and new hits. Re-run the production comparison when that
  happens; never widen an entry to `"*"`. VOICE.md already names the fix for
  both sitewide strings ("Conflicts resolved" 1 and 2: "Explore" becomes
  "Budget" or "Field guide", and "Visual field guide" becomes "Field
  guide"). Burn-down: fix each string per VOICE.md in `site/src/lib/copy.ts`
  or its component, and delete its allowlist entry in the same commit. The
  gate fails on any entry that matches nothing, so no entry can outlive its
  string. Do the two `"*"` entries first. Source: the integration's
  copy-gate report (`gatefix-copy.md`, the branch ledger). Effort: days.
  *Review fix round, 2026-09-25:* the first burn-down. /methodology/'s
  pointer to /coverage/ lost its em-dash pair when final-review finding #8
  reworded it, and its leg-13 entry was deleted in the same change, leaving
  583 entries.
  **Status:** open (2026-09-25).

- **#176 The lobbying matcher reads a year, a bill number or a quantity as a
  numeric budget-line code and badges the row "PE code cited directly".**
  `src/govbudget/influence/mentions.py` adds each program's bare `pe_bli` as
  a code term (`_candidate_terms_typed`), `_build_word_boundary_re` matches
  it as a free-standing token, and `find_mentions` tags any hit
  `pe_literal`, the strongest tier. The site labels that tier "PE code cited
  directly" (`site/src/lib/evidence.ts`), and it is one of the two tiers
  that may name a company in a program's answer to "Who gets it". Nothing
  asks whether the token is a year, a bill number or a quantity. Measured
  read-only on 2026-09-25 from `data/site/data/fct_program_lobbying.parquet`
  (14,016 rows): all 1,631 `pe_literal` rows sit on 45 codes of one to four
  digits, led by 2025 (683 rows), 2026 (455), 14 (80), 4213 (54) and 22
  (51). The final integration review (finding #10) read the 2025 and 2026
  rows against the filings' own text: 638 of the 683 and 413 of the 455
  carry the code as a year ("Fiscal Year 2025", "Act of 2025"), and only 5
  of the 683 mention the Amphibious Combat Vehicle, budget line 2025, at
  all. On the integration build /company/raytheon/ carries 7 rows reading
  "Amphibious Combat Vehicle Family of Vehicles … matched on 2025 · PE code
  cited directly", /program/2025/ lists 767 mentions and opens on an Abbott
  Laboratories filing about "The Strengthening Benefit Plans Act of 2025",
  and the 14,016 program mentions /methodology/ counts, "qualifying only
  when the exact PE/BLI code appears", include every one of these rows. On
  the members of a shared code R-INT-9 now withholds them (#82); everywhere
  else they publish, as they do in production (81929a6b), so the defect
  predates the merge. How many of the 1,631 rows are real code citations is
  unmeasured. Fix: require a numeric code to appear with context that makes
  it a budget line (a PE or BLI label, or the program's own title words
  nearby), or publish bare numeric hits below `pe_literal`; then re-measure
  the 14,016 and gate 21 leg (j)'s "Who gets it" census. Source:
  `src/govbudget/influence/mentions.py`, `site/src/lib/evidence.ts`, the
  final integration review (finding #10). Effort: days.
  **Status:** open (2026-09-25; scheduled in the decisions wave).

- **#177 A deploy overwrites fixed-name `data/*.parquet` on R2 before Vercel
  serves the pages that read them.** `scripts/launch/deploy.sh` runs
  `upload_r2.sh --live` first and the Vercel deploy second, on the ground
  that "upload_r2.sh never deletes, so an early sync is safe". That holds
  for the content-addressed `pdfs/` and `workbooks/`, but `data/*.parquet`
  have fixed names, and `rclone copy --checksum` replaces a changed object
  in place (`scripts/launch/upload_r2.sh`). The integration export changed
  the columns of `data/fct_program_concentration.parquet` (#80: `hhi`,
  `top_family`, `family_count` became `hhi_all`, `hhi_high` and their
  siblings), and production's /data/ Explorer preset "Most concentrated
  programs (HHI)" queries `SELECT pe_bli, hhi, family_count, top_family …
  ORDER BY hhi DESC` (81929a6b, `site/src/components/explorer.tsx`). Checked
  by the final integration review (finding #17) on 2026-09-25: the live R2
  object is 10,895 bytes with the old columns, the local file is 17,903
  bytes with the new ones, and the old preset raises a DuckDB Binder Error
  against the new file; every other shipped parquet only gains columns or
  is unchanged. So production's preset fails from the end of the R2 step
  until Vercel serves the new pages, indefinitely if the Vercel step fails,
  and after any Vercel rollback to a pre-integration deployment
  that does not also restore the R2 object. No local copy of the old-schema
  file remains: `data/refresh/2026-09-24/rollback/site/data/` already
  carries the new columns (checked 2026-09-25), so the live R2 object is
  the only copy. Fix: before the R2 step, copy the live `data/` prefix
  aside (`rclone copy` to a dated R2 prefix) so a rollback can restore it;
  then either version the parquet keys per build, or deploy pages before
  data when a schema changes, or ship a temporary alias column. Source:
  `scripts/launch/deploy.sh`, `scripts/launch/upload_r2.sh`, the final
  integration review (finding #17). Effort: hours.
  **Status:** open (2026-09-25; the window applies to this integration's
  own deploy).

*Status markers (one ledger sweep, 2026-08-24).* Every numbered entry below now
ends with a `**Status:**` line — `CLOSED`, `PARTIAL`, `OPEN` or `UNVERIFIED` —
naming the sprint and/or commit that closed it and when, so an item's state is
readable without cross-referencing a 3,000-character sprint-table cell at the
top of this file. Two older conventions remain in place and were left
untouched: strikethrough + `**DONE <date>:**` inside the entry body (#2, #3,
#5, #6, #11, #12, #16, #17, #18, #20, #21, #23, #24, #25), and a leading `✅
**DONE/FIXED <date>**` (#27, #31, #33, #35, #37, #38, #39, #41, #44, #55).
Roughly a dozen entries carried neither and were closed only in sprint-table
prose or a blockquote — #34, #36, #45, #47–#53 and #54 all read as open bugs
until this sweep. Statuses were derived from evidence — commit messages, the
sprint rows, and the code or built artifact at HEAD — never from an entry's own
wording; where the two disagreed, the marker says so. Nothing above a
`**Status:**` line was edited: the defect descriptions are the historical
record and stay as written. Grep: `grep -n '\*\*Status: '
docs/superpowers/ROADMAP.md`.

1. **Alias backlog (5B-2/3 content):** 9 top-50 families unmatched to LDA clients
   (Booz Allen Holding, ADS Tactical, Northrop Innovation Systems, Vertex, Fluor
   Marine Propulsion, MacAndrews & Forbes, Shell E&P, Bell-Boeing JPO*, Domestic
   Awardees* — *=genuinely unmatchable). Curated client_aliases.csv additions with
   documented corporate facts.
   *Update 2026-07-02:* aliases CURATED + committed for Booz Allen, ADS Tactical,
   Vertex (V2X fka), Shell E&P — spellings verified against the live LDA API, with
   over-merge guard tests. STAGED, not yet effective: those filings were never
   returned by the original pull's query strings, so they only match at the next
   `govbudget influence pull` (+ dbt marts, mentions, export-site, dossier-citation
   check). The match_gate5a raise to 0.85 lands with that re-pull (a premature
   raise was reverted in final-stage verification — see findings). Remaining 6
   families verified as having zero 2024–2026 filings (genuinely unmatchable).

   **Status: CLOSED 2026-09-25** — ledger sweep; the work landed between
   2026-07-02 and 2026-09-01. Aliases curated in `34d65e00` (2026-07-02; the
   seed is `dbt/seeds/client_aliases.csv`); the live re-pull ran in `7d03475b`
   (2026-08-27) + `f83feca4` (2026-08-29); the aliases are effective —
   measured read-only 2026-09-25 on `lda_filings.parquet` (5,393 filings):
   Booz Allen Hamilton Holding 70, ADS Tactical 18, Vectrus 12 and Vertex
   Aerospace Services 11 filings at `match_method = 'curated_alias'`; and the
   match gate was raised to 0.85 in `bcfe9680` (2026-09-01) on a measured
   46/50 = 92%. The Shell E&P rows are inert, not wrong: the `SHELL
   EXPLORATION PRODUCTION` family ranks 6,623rd by obligation in `dim_entities`
   (2026-09-25), outside the top-100 families `influence pull` queries, so none
   of the 37 filings whose client name contains "SHELL" reaches it. The
   PARTIAL marker below predates all of this.
   *(Original marker below.)*
   **Status: PARTIAL** — swept 2026-08-24. The curation half is done and
   recorded by `2efab28` (2026-07-02); activation is still blocked on #19's
   live LDA re-pull, which has never run. Verified at HEAD:
   `src/govbudget/verify_phase5a.py:62` is still `_MATCH_THRESHOLD = 0.80` —
   the raise to 0.85 lands with the re-pull — and no commit in the history
   references drawdown Task D1 (#1 + #19 as one unit).
2. **Citation tiers deferred from 5B-1:** ~~USAspending (reproducible query
   permalink), state checkbook (SoQL URL), derived metrics (formula + input
   citations). Owner: 5B-2 (usaspending/state), 5B-3 (derived). The manifest's
   `uncited_datasets` ledger (11 datasets) is the enforcement hook — 5B-2's
   render gate must refuse to render numbers from datasets still on it.~~
   **DONE 2026-07-02:** ledger cleared to 0 — final holdouts dim_geography,
   fct_budget_to_awards, dim_lobbyists received citations (district dollars are
   clickable citations); the ledger gate is now armed at empty (any future
   uncited dataset fails loudly).

   **Status: CLOSED** — swept 2026-08-24. Fleet round; recorded by `2efab28`
   (2026-07-02), which is the commit carrying the strikethrough + "DONE
   2026-07-02" above.
3. **Page-resolution disambiguation:** ~~prefer detail-exhibit pages over summary
   pages via "Exhibit R-2"/"P-40" header anchoring → shrink ambiguous_first 73%.~~
   **DONE 2026-07-02:** exhibit-aware tie-breaking (source exhibit header, then
   project-number token; each step skipped if it would empty the candidate set);
   ambiguous_first 3,208 (73% of 4,419) → 2,239 (51%), unique 209 → 1,178.
   'unique' only when uniquely determined + word-confirmed; candidate_pages keeps
   the raw pre-tie-break count (auditable, no fabricated certainty). Rebuild
   determinism verified: delete-ambiguous + rebuild reproduced 4,419/4,419 keys
   byte-identically.

   **Status: CLOSED** — swept 2026-08-24. Fleet round; recorded by `2efab28`
   (2026-07-02).
4. **Historical J-book backfill (PB2025/PB2024)** → enables book-diff "what
   changed this cycle" (5B-3 feature 6). Schema already supports.
   *Update 2026-07-02:* PB2025 feasibility spike complete — GO recommendation
   (docs/superpowers/plans/2026-07-02-pb2025-backfill-feasibility.md).

   **Status: CLOSED** — swept 2026-08-24. Drawdown Sprint A, Task A1; `c7293e5`
   (2026-08-12). Superseded rather than built: `fct_budget_lines` carries all
   ten editions PB2017–PB2026 from Phase 5E, where this entry asked only for
   PB2025/PB2024. Closure prose is the `#4, #13, #26` blockquote near the end
   of this section — note it dates itself 2026-08-08, four days before the
   commit that recorded it.
5. **$39T CPI SATCOM subaward outlier** — ~~staging-layer sanity guard
   (max-plausible-amount flag, quarantine table).~~ **DONE 2026-07-02:**
   staging quarantines subaward outliers with `is_amount_suspect` flag.

   **Status: CLOSED** — swept 2026-08-24. Fleet round; recorded by `2efab28`
   (2026-07-02).
6. **Site-mart gaps found in 5B-1 recon:** ~~no per-family obligations-by-year
   mart (company page time series), no feed/event mart~~, dim_geography lacks
   fiscal_year/pe_bli breakdown (district drill-down) — build in 5B-2/5B-3 as
   their pages need them (YAGNI until then).
   *Correction 2026-08-07 (verified against the codebase for the backlog-drawdown
   plan; do NOT close this entry):* the two mart sub-items are **DONE** —
   `dbt/models/marts/fct_family_obligations_by_year.sql` and
   `dbt/models/marts/fct_feed_events.sql` both exist. The third clause is
   **STILL TRUE and remains OPEN**: `dim_geography` is exactly
   `[pop_state, pop_district, transaction_count, total_obligation]` — no
   `fiscal_year`, no `pe_bli`. The district fiscal_year/pe_bli breakdown this
   entry asked for has not been built.

   **Status: CLOSED — 2026-09-11 (owner decision 2026-09-05: build it).** The
   third clause is delivered, and deliberately NOT inside `dim_geography`,
   which still selects exactly `pop_state, pop_district, count(*),
   sum(obligation)`: re-graining the all-award place-of-performance headline
   would move every figure that reads it, so the breakdown is a purpose-built
   pair of models instead (precedent #37/#51 — the fix belongs in a new model,
   not a re-grained one). `dbt/models/marts/fct_district_programs_by_year.sql`
   is grain `(pop_state, pop_district, pe_bli, fiscal_year)` — 1,984 rows, 153
   districts, 203 program elements, FY2017–FY2026 — and
   `fct_district_totals_by_year.sql` is its award-distinct companion at
   `(pop_state, pop_district, fiscal_year)`, 924 rows. Both carry net AND gross
   obligations because 53 of the 924 district-year cells are net-negative, and
   the gross figure is summed at the TRANSACTION level (278 of the 924 cells
   differ from the award-level formula — the fixture now pins which one is
   published). `/district/{code}/` renders the year table off the second one,
   every figure cited through a new derived surface `district_year`;
   `assert_district_by_year_reconciles` pins both marts to their all-years
   siblings at a one-cent tolerance and, since 2026-09-11, joins FULL OUTER so
   a district that vanished from either mart is a violating row rather than an
   invisible one; gate 9 leg f pins the rendered by-year sum to the page's own
   headline with a non-vacuity floor (≥130 districts, ≥800 rows); and gate 24
   leg r recomputes a deterministic 12-cell sample from the lake — never from
   the mart under test — and checks it against both the sidecar and the
   rendered figure. FY2026 is labelled partial on the page from
   `site_meta.award_fy_range.max_partial`, derived not authored. Mart figures
   measured 2026-09-10 and re-measured unchanged 2026-09-11, read-only against
   the shipped warehouse; the page and both gate legs are proven by unit tests
   and by that recompute, and the branch's export → build → verify chain is
   what exercises them on a built site (it also re-measures the new
   `/district/*/` page-weight entry, whose ceilings are this change's one
   estimate).
   *Addendum 2026-09-25 (Task 26 fix wave): this block was moved above the
   2026-08-24 marker it supersedes, text unchanged, as the ledger sweep moved
   #29's — a reader or a tool taking the first Status line per entry read #6
   as open.*
   *(Original marker below.)*
   **Status: PARTIAL — and the entry stays OPEN** — swept 2026-08-24. The two
   mart sub-items are done
   (`dbt/models/marts/fct_family_obligations_by_year.sql` and
   `fct_feed_events.sql`, both present at HEAD). The third clause is still
   true: `dbt/models/marts/dim_geography.sql` selects exactly `pop_state,
   pop_district, count(*), sum(obligation)` — no `fiscal_year`, no `pe_bli`.
   Confirmed OPEN by `c7293e5` (2026-08-12), whose blockquote below says
   closing it "would be the false-completion this ledger keeps catching
   elsewhere".
7. **FEC → CongressionalAddDetail chain** (money in → marks → money out) —
   post-5B; the J-book XML already carries the add elements.

   **Status: CLOSED — DEFERRED AS A NON-GOAL, owner decision 2026-08-29.**
   Not deferred for cost. This entry would introduce a new CLAIM TYPE — campaign
   money in, congressional marks, money out — into a site whose entire
   credibility rests on every figure tracing to a primary budget document. An
   FEC→add inference is politically charged, and the 24-gate architecture checks
   *number ↔ citation*, which cannot police it: the three-persona review of
   2026-08-27 found six false claims live precisely because every number was
   correct and no gate checked the claim wrapped around it. One contested
   inference here would cost more credibility than the feature adds. Reopen only
   with its own spec and a distinct visual tier, the way Inferred lineage is kept
   separate from Stated. *(Original marker below.)*
   **Status: OPEN** — swept 2026-08-24. Never scoped: named out of scope at the
   top of `docs/superpowers/plans/2026-08-07-backlog-drawdown.md`, and no
   commit in the history references it. Verified at HEAD: no FEC or
   `CongressionalAdd` code under `src/govbudget/` or `dbt/models/`.
8. **Refresh automation:** monthly USAspending, quarterly LDA, annual J-book,
   biennial GAO; cron on Mac Mini + `govbudget refresh` orchestrator + drift
   alarms (golden fixtures break = schema drift detected). Post-launch.

   **Status: PARTIAL — the orchestrator ships, the scheduler is the owner's to
   load** (2026-09-18). `python -m govbudget refresh` runs the twelve-stage
   graph (preflight -> three syncs -> quarterly LDA -> golden-fixture parser
   gate -> export-facts -> build -> export-site -> site build+verify ->
   deploy.sh) with `--dry-run/--from/--until/--quarterly/--yes`; the LDA
   abort-without-overwrite guard is generalized to every sync-* stage
   (`convert.PartitionShrinkError`, 80% retention floor,
   `--allow-corpus-shrink`, Task 20a); the run record in
   `data/refresh/last_run.json` carries a cadence-age alarm, a stall alarm
   (a sync that exits 0 without advancing its dataset) and a count of
   unparseable manifest lines. Two launchd templates +
   LAUNCH.md Step 11 ship for the owner to load — no agent installs a
   scheduler, and none was installed. **Alarms are printed and recorded, never
   fatal** (ruling R-20b-6): `record["ok"]` stays true and the command exits 0,
   because a cadence alarm fires on data the upstream has not republished and
   failing a scheduled run for that trains the operator to ignore failures —
   so the operator reads `data/refresh/last_run.json` after a scheduled run,
   and nothing polls it for them. **The cadence alarm already fires today**
   (measured 2026-09-18): `contracts`, `assistance` and `subawards` were last
   ingested 2026-06-11, 99 days against a declared monthly cadence, so every
   run including `--dry-run` prints three `DRIFT ALARM:` lines. A successful
   monthly run clears the `contracts` and `assistance` lines; the `subawards`
   line keeps firing because of open item (b) below — that stage returns early
   on an FY already in the manifest, so its newest `downloaded_at` never
   moves. STILL OPEN: (a) LDA, J-book and GAO
   ingests write no `manifest.jsonl` records, so the drift report can age none
   of the three; gate 24 leg m marks the J-book and GAO cadence lines UNMETERED
   while `/methodology/` states no LDA cadence at all, so leg m never sees LDA
   and reports nothing about it; (b) `sync-subawards` still
   returns early once its FY is in the manifest, so the monthly run skips
   rather than refreshing a partial FY (now alarmed, not silent); (c) annual
   J-book / biennial GAO cadences are operator-run by design (per-service
   transport decisions; launchd cannot express biennial); (d) the entry's
   "golden fixtures break = schema drift detected" is not achievable as worded
   — the golden fixtures are committed files, so the suites test this repo's
   parsers, not the upstream. A required column vanishing, a missing
   `meta.total-pages` and a truncated archive all fail loudly; a NEWLY ADDED
   upstream column is detected by nothing. (e) The orchestrator is never
   exercised end to end by any test — every stage runs under a fake runner in
   `tests/test_refresh.py`, so the first real run is the first integration
   test. Review follow-ups landed 2026-09-18: the run record is now written
   from a `finally`, so an exec-level failure or a Ctrl-C can no longer leave
   the PREVIOUS run's `"ok": true` in `last_run.json`; the preflight probes
   carry a 60 s timeout while stages deliberately carry none (a hung stage
   holds its launchd slot — LAUNCH.md Step 11 says so); a missing lake is a
   preflight failure rather than a freshly created empty database; preflight
   CREATES a missing `logs/` (R-20b-8) while the Step 11 install snippet keeps
   its own `mkdir -p`, because launchd opens the job's log files before exec
   and preflight runs too late to help a scheduled run; `run_refresh` holds an
   exclusive `flock` on `data/refresh/.lock` so the monthly and quarterly
   labels cannot overlap, and `--dry-run` takes no lock (R-20b-7) so a plan
   stays readable mid-refresh; and the quarterly LDA stage computes `--years`
   as 2024 (`_LDA_FIRST_YEAR`, the corpus's first filing year) through the
   current calendar year, instead of inheriting the CLI's hardcoded
   `2024,2025,2026` — the end tracks the clock, the start never moves, because
   `influence pull` overwrites `lda_filings.parquet` in full and a year the
   window stopped naming would be a year deleted from the corpus.
   *Re-measured 2026-09-25 (chain C run 4; the tracked `data/manifest.jsonl`
   carries 34 download records since ruling R-C-5 adopted the 2026-09-06
   FY2026 archives):* the newest `contracts` and `assistance` downloads are
   dated 2026-09-24 (`FY2026_097_{Contracts,Assistance}_Full_20260906.zip`,
   fetched by another checkout's refresh), while the newest `subawards`
   download is still 2026-06-11 — 106 days old on 2026-09-25, as clause (b)
   predicts — and every one of the three datasets still holds fiscal-year
   archives fetched 2026-06-10 (#138). Loading the plists and running the
   first scheduled refresh — which is also the first end-to-end test, clause
   (e) — is the owner's call, after `which uv node npm rclone vercel` on the
   machine that will run it confirms `scripts/launch/refresh.sh`'s PATH line
   (LAUNCH.md Step 11).
   *Addendum 2026-09-25 (Task 26 fix wave): the 2026-08-24 marker below was
   deleted outright by `1ea5c540` (2026-09-18) when the PARTIAL marker above
   replaced it; restored verbatim here, supersede-not-delete. Its `cli.py:2092`
   line number is that day's.*
   *(Original marker below.)*
   **Status: OPEN** — swept 2026-08-24. Never scoped (out of scope in the
   drawdown plan; no commit references it). Verified at HEAD: the only
   `refresh` subcommand is `evals refresh` (`src/govbudget/cli.py:2092`); there
   is no `govbudget refresh` orchestrator and no cron under `scripts/`.
9. **Resolution-memory for review queue** (re-flagged items remember triage).

   **Status:** CLOSED 2026-09-10 — `_tally` now looks up an accepted
   `review_queue` row for the same (document, gate, pe_bli, scenario) with the
   same expected/actual and inserts the re-flagged row pre-accepted
   (`carried from #<root id>: <reason>`; the id names the human decision and a
   carried prior is copied verbatim, so chains never grow). The re-reconcile
   prune re-derives carried rows and keeps human roots. `review list` reports
   carried rows apart from open ones (`--carried` prints them with a `~#`
   prefix); `reconcile_document` returns `carried` (`failed == queued +
   carried`). No migration — `status` / `resolution` / `resolved_at` already
   existed. Carrying never sets `budget_line_details.reconciled` and still
   inserts a queue row, so `accuracy_gate`'s `silent_unreconciled` — the half
   of gate 2 that can fail — is unchanged and nothing published moves; only
   the printed `open_review` shrinks, to the true open count. Warehouse on
   2026-09-10: 927 open / 308 accepted, 35 of the open rows same-numbers
   re-flags of an accepted row on the same document; those become carried at
   their documents' next `jbooks extract` — this change backfills nothing.
   *(Original marker below.)*

   **Status: OPEN** — swept 2026-08-24. Never scoped; no commit references it.
   Verified at HEAD: `review_queue` (`migrations/001_phase1_schema.sql:84`)
   does carry `status` / `resolution` / `resolved_at`, but `_tally`
   (`src/govbudget/jbooks/reconcile.py:257`) inserts a fresh row for each new
   `check_id` and never reads a prior triage — a re-flagged item does not
   remember.
10. **SAM entity extract / Splink** entity-resolution upgrade (deferred with
    evidence since Phase 2).

    **Status: PARTIAL 2026-09-25** — ledger sweep. The spike `1d75c231`
    (2026-09-01) inverted the premise; Option A shipped in `a2a9b2f8`
    (2026-09-01: display-alias seed + gate 24 leg l); the Splink half is a
    deliberate non-goal (owner stamp recorded by Task 19a in `d799e794`,
    2026-09-12 — the marker below dates it 2026-09-10, the plan's date). The
    SAM.gov extract is **BLOCKED on an owner action**: a SAM.gov Personal API
    key (login.gov → SAM.gov → Account Details) in `GovBudget/.env` as
    `SAM_API_KEY`; the api.data.gov key is not accepted. Task 19b shipped the
    extract lane and its warehouse and reader halves offline-green
    (`4f04cec4`, `6c3cb61d`; fix round `55b1d026`, `0d0a8c2f`, `fede781f`,
    `3ca4a0c4`; all 2026-09-12) and no call has been made to api.sam.gov.
    Dated corrections to the marker below, measured 2026-09-25: the
    display-alias seed holds **17** rows (10 relabel, 7 pin — gate 24 leg l on
    chain C run 4), not "15 today", so Option B's ~40-family trigger has still
    not fired; `/companies/` has about **6** gzip bytes of headroom on the
    run-4 build (68,994 of 69,000), not ~1,800; and the 42,500 /methodology/
    gzip ceiling the marker names (not raised by that change) was raised once
    later, 42,500 → 43,000, under ruling R-C-1 at chain C run 4 (`71d3e053`,
    2026-09-25). Two latent
    seams to close before the first live run (Task 19 review, 2026-09-12):
    `src/govbudget/sam_entities.py:68,77` binds `SAM_ENTITY_API_URL` /
    `SAM_PUBLIC_ENTITY_URL` at import, so a later in-process environment change
    has no effect; and `require_preflight` (`:239`) does not re-check the
    stored `public_url` template against the constant.
    *(Earlier markers below.)*

    **Status: the Splink half CLOSED AS A DELIBERATE NON-GOAL + Option A
    (display-label correction) CLOSED — owner stamp 2026-09-10. The
    SAM-extract half is OPEN, blocked on an owner-created key.**
    The 2026-08-24 marker below is stale in BOTH its claims: two commits do
    reference this item — `1d75c231` (2026-09-01, the sizing spike,
    `docs/superpowers/reviews/10-entity-resolution-spike.md`) and `a2a9b2f8`
    (2026-09-01, `fix(#10 A)`) — and `entities.py:6` no longer says Splink is
    "deliberately deferred until a gate fails": `d799e794` replaced that line
    with the closure quoted above, which is what made the marker's second
    claim stale.

    **The spike inverted the entry's premise.** `recipient_parent_name` in
    USAspending *is* the SAM registration name, so ingesting SAM reproduces the
    defect rather than correcting it (§4). The flagship family's linkage is
    perfect — all 15 members share parent UEI `EGAVSJTA2D81` — and only the
    *string* that registration carries is wrong. This is a naming defect, not a
    resolution defect.

    **The Splink half (spike Option C) — closed, do not re-propose.** §3: the
    most permissive plausible name-similarity rule over the 2,766 families
    ≥$100M yields 103 candidate pairs worth **$30.0B**, against **$255.2B**
    (15 of the 200 published families, 9.7% of published family dollars) of
    labels decided by an argmax that beat its runner-up by under 15% — which
    Splink cannot see, because the evidence tying the flagship pair together
    is a shared child set (112 of 118 UEIs), not string similarity. A linker
    also outputs clusters, never labels. §6 records four alternative rules
    tested and rejected with measured blast radii; the cheapest-looking of
    them, "name a family by its dominant member", regresses 109,349 currently
    correct families and renames `GENERAL DYNAMICS` → `ELECTRIC BOAT
    CORPORATION`.

    **Option A — shipped and gated.** `a2a9b2f8`:
    `data-seeds/entity_display_aliases.csv` (15 rows — 9 relabel, 6 pin),
    `src/govbudget/entity_display_aliases.py`, exporter wiring at
    `export_site.py:3193` (`_entity_display_labels`) and `:8994`, 22 tests
    in `tests/test_entity_display_aliases.py`, and gate 24 leg (l)
    (`site/scripts/gates/datatruth.mjs:83,3018` +
    `site/scripts/gates/familylabel-recompute.py`), which fails the build when a
    published family's label wins its parent-registration argmax by <15% with no
    alias row. Live. *(`export_site.py` line numbers measured at `d799e794`;
    19b's own exporter inserts have moved them since — grep the symbol, not the
    line. The spike commit cited `export_site.py:2790` before Group B's inserts
    moved it.)*

    **Option B — parent-UEI clustering — deferred with a NAMED trigger.**
    §6: 322 families absorbed and $125.6B relabelled at ≥3 shared children /
    ≥50% overlap, which re-keys `family_key` → slugs → fact ids → published
    `query_body` statements, and over-merges on ownership history
    (`AMENTUM + JACOBS + AECOM + PAE` into one $40.0B cluster). Revisit **when
    the curated seed exceeds ~40 families** — it holds **15** today, so the
    trigger has not fired.

    **The SAM.gov Entity Management extract — scoped, blocked on the owner.**
    Not an entity-resolution fix (see above) and it promotes no confidence
    tier; it is an ENRICHMENT: registration status, CAGE, UEI, legal business
    name, business types, primary NAICS and expiration for the 200 published
    families' dominant registrations, published as a cited line on
    `/company/{slug}/`. Blocked on a credential only an account holder can mint:
    per https://open.gsa.gov/api/entity-api/ the Entity Management API takes a
    SAM.gov **Personal API key** (non-federal user with no role: **10
    requests/day**; with a role: 1,000/day), **not** an api.data.gov key — the
    `DATA_GOV_API_KEY` registered 2026-09-05 does not open it, and
    `https://api.sam.gov/entity-information/v3/entities` answers an empty 404
    unauthenticated. **Owner action:** sign in at login.gov → SAM.gov → Account
    Details → Public/Personal API key, then paste it into the gitignored
    `GovBudget/.env` as `SAM_API_KEY=…`. At 10 requests/day the bounded extract
    (200 UEIs, one request each) takes ~20 resumable days; with a role-holding
    key, one run.

    **What shipped 2026-09-12 (the extract lane only).** `src/govbudget/sam_entities.py`
    + `govbudget sam preflight|extract|reparse`: resumable (a stored raw body
    under `data/raw/sam/` is never re-fetched), self-capping (`--max-requests`,
    default 10 = the no-role daily limit), stopping dead on a 429 /
    `OVER_RATE_LIMIT` / `API_KEY_INVALID` rather than retrying into tomorrow's
    quota, rebuilding `data/parquet/sam/entities.parquet` even when it stops so
    a partial day is never lost, and refusing to publish the reader-facing
    `sam.gov/entity/{uei}` link until `preflight` has recorded it answering 200.
    The key is never written to a parquet, manifest, raw body or URL
    (`source_url` is the request URL with `api_key` stripped; a test asserts
    it), and `DATA_GOV_API_KEY` is never read. 16 tests, all offline
    (`httpx.MockTransport` + `tests/fixtures/sam/`); **no call has ever been
    made to api.sam.gov from this repo**, so the response shape is typed from
    https://open.gsa.gov/api/entity-api/ and `parse_entity` raises
    `SamShapeError` naming the missing JSON path rather than emitting nulls.
    Runnable with no credential today: `--dry-run` (measured 2026-09-12:
    `200 published families, 0 already stored, 200 missing; this run would
    spend 10 of 10 request(s) and 20 run(s) remain`) and `--schema-only`.

    **What shipped 2026-09-12, round 2 (the warehouse and reader halves), all
    of it true by construction at ZERO rows.** `lake.sam_entities` (dbt source)
    + `dim_entities`'s `dominant_registration_uei` and ten `sam_*` columns,
    LEFT JOINed through the `sam_entities_relation()` macro — which substitutes
    a typed zero-row relation when the parquet is absent, because DuckDB raises
    at VIEW-CREATION time on a missing `read_parquet` path (measured on duckdb
    1.5.3; the brief assumed otherwise) and `fct_influence` refs `dim_entities`,
    so an absent extract would otherwise take down the whole export. The dbt
    `unique`/`not_null` assertion on `dim_entities.family_key` is the anti-fan-out
    guard. `verify_phase2.sam_gate` (CLI leg **e4**) re-derives each published
    family's dominant registration and fails on a stale one or a nameless one;
    with no rows it passes **and prints `VACUOUS — …`** naming the un-run
    extract, because a leg that can pass by checking nothing has to say so.
    `export_site.py` mints `fact_id_derived("entity_sam", family_key,
    "registration")` (kind `derived`, URL inputs, `recorded_value` = the
    registration status) and puts the payload on `entity_details/{slug}.json`,
    never on `entities_top.json` (`/companies/` reads that file and has ~1,800
    bytes of gzip headroom); `site_meta.counts.companies_with_sam` counts the
    sidecars actually written. `SamRegistrationNote` renders the line on
    `/company/{slug}/` only when the family has a row AND its fact id is in the
    citation set — cited-or-absent, so today it renders **nothing**. The three
    "a SAM.gov entity extract this build does not have" strings are now
    data-conditional on that count (`/companies/`, both branches — at 0 they
    render the existing true sentence verbatim) or unconditionally true
    (`/companies/families/`: a registration extract would not promote a tier,
    because the registered parent name a tier reads is itself the SAM
    registration). `/methodology/` §4 states the extract's status from
    `site_meta` in one sentence — today "No SAM.gov registration record ships
    yet; that extract needs an account holder's credential" — paid for by
    trimming three redundant clauses in the same passage (−98 raw / −24 gzip,
    measured on the built page; the 42,500 ceiling was not raised), with the
    durable claim mirrored into `docs/methodology.md`.

    **What is left, and it is only the run.** No warehouse holds a SAM row and
    none can until the owner's key exists, so every surface above is in its
    zero state and every gate passes there. `cmd_build` deliberately does NOT
    bootstrap a zero-row parquet (the brief's mitigation): the dbt macro makes
    the missing-file case impossible without writing into the shared lake.

    **Owner step — the live run, once `SAM_API_KEY` is in `GovBudget/.env`:**

    ```bash
    cd GovBudget
    uv run python -m govbudget sam extract --dry-run   # free: what today's run would fetch
    uv run python -m govbudget sam preflight           # spends up to 2 requests; writes data/research/sam_entities/preflight.json
    uv run python -m govbudget sam extract             # 10/run by default; repeat daily (~20 days) until --dry-run reports complete
    uv run python -m govbudget sam reparse             # free: rebuild the parquet from data/raw/sam/
    uv run python -m govbudget build                  # REQUIRED — see below
    uv run python -m govbudget export-site
    cd site && npm run build                          # then ./scripts/launch/deploy.sh
    ```

    **The rebuild is not optional, and skipping it looks exactly like success.**
    `sam_entities_relation()` probes for the parquet at dbt COMPILE time, so a
    warehouse built while the file was absent has `dim_entities` frozen to the
    zero-row literal: the extract can land all 200 rows and every `sam_*`
    column stays NULL — no company line, no citation, `companies_with_sam` 0 —
    until `govbudget build` re-runs. `verify-phase2` leg e4 says the same in
    both of its vacuous notes. Only then do `export-site` and the site build
    have anything to publish.

    If `preflight` reports a shape other than the documented one, fix the path
    map in `parse_entity`, replace `tests/fixtures/sam/entity_lockheed.json`
    with the real (key-free) body, re-run `uv run pytest
    tests/test_sam_entities.py`, then `sam reparse` — **never re-fetch to fix a
    parse.** If it reports a non-200 `public_url_status`, fix
    `SAM_PUBLIC_ENTITY_URL` and re-run `preflight`; the extract refuses until
    it is 200. A SAM.gov role raises the limit to 1,000/day and the whole set
    lands in one run.
    *(Original marker below.)*

    **Status: OPEN** — swept 2026-08-24. Never scoped; no commit references it.
    Verified at HEAD: `src/govbudget/entities.py:6` still reads that
    probabilistic matching (Splink) is "deliberately deferred until a gate
    fails".
11. **Type oversight parquets properly:** ~~improper_payments and related oversight
    tables are all-VARCHAR from CSV ingestion, forcing CAST everywhere and inviting
    lexicographic-sort bugs (root cause of several 5B-4 SEMANTIC failures). Migrate
    to typed columns at the staging layer.~~ **DONE 2026-07-02:** loaders now write
    typed columns at ingestion (fiscal_year INTEGER, rate/amount columns DOUBLE,
    high_risk.mapped BOOLEAN); parquets retyped in place value-identically
    (fct_improper_exposure checksum unchanged); dbt try_casts dropped; schema card
    updated (trap note replaced — legacy CASTs are harmless no-ops).

    **Status: CLOSED** — swept 2026-08-24. `9931d7c` (2026-07-02), recorded by
    `2efab28` the same day.
12. **Build gate for stale/failed `site/out`:** ~~verify gates should detect that
    the SSG output is absent or from a failed build before running npm verify gates
    — currently a broken build silently causes gate false-passes against stale HTML.~~
    **DONE 2026-07-02:** gate 1 build-staleness check — postbuild marker file +
    mtime guard against data/site inputs.

    **Status: CLOSED** — swept 2026-08-24. Fleet round; recorded by `2efab28`
    (2026-07-02). Verified at HEAD: gate 1 still carries the build-staleness
    check.
13. **Mistral OCR (Document AI) as fallback extractor** for scanned/legacy J-book
    PDFs — current pipeline is XML-first and doesn't need it; revisit if pre-2015
    books (scan-only) enter scope.
    *Correction 2026-08-07 (for whoever closes this entry):* the backlog-drawdown
    plan's verification grep, `grep -rniE "ocr|mistral|document.?ai"
    src/govbudget/`, is a false-positive generator — the unanchored `ocr` matches
    So**cr**ata, producing 14 spurious hits (`src/govbudget/states/`,
    `verify_phase4.py`). Use the anchored form instead:
    `grep -rniE "\bocr\b|mistral|document.?ai" src/govbudget/ | grep -v test` —
    verified genuinely clean (0 hits) on 2026-08-07.

    **Status: CLOSED** — swept 2026-08-24. Drawdown Sprint A, Task A1;
    `c7293e5` (2026-08-12) — closed as moot, not built. The anchored grep in
    the correction above returns 0 at HEAD. The `#4, #13, #26` blockquote near
    the end of this section dates the closure 2026-08-08, four days before that
    commit.
14. **Feed title enrichment in dim_programs/exporter proper (5C):** 136 trajectory-only
    PEs currently have titles resolved at feed-export only; they need program pages and
    dim_programs entries so they appear in search and the sitemap.
    *Update 2026-07-02:* pages/search/sitemap half completed by backlog #17 (exporter
    synthesis from dim_pe_titles); dim_programs entries proper still require R-2/P-40
    detail ingestion and remain out of scope by design.

    **Status: CLOSED 2026-09-25 — the residue is #111.** Ledger sweep. The
    page/search/sitemap half closed with #17 (2026-07-02); the
    `dim_programs`-entries half is out of scope by the entry's own design,
    because the remaining workbook-only elements have no R-2/P-40 detail in
    the corpus (re-probed 2026-09-12 by Task 17a, recorded below); and every
    still-actionable residue is filed as **#111 (open)**, clauses (a)–(d),
    whose rendered-sentence half (e) Task 17c fixed (`428623ad`, 2026-09-12).
    Closed here so the open work has one home.
    *(Original marker and its two updates below.)*

    **Status: PARTIAL** — swept 2026-08-24. The page/search/sitemap half was
    closed by #17 (`2efab28`, 2026-07-02, per the update above). The
    `dim_programs`-entries half is out of scope by design pending R-2/P-40
    detail ingestion, and no later commit changes that.

    *Update 2026-09-12 (Task 17a):* the "requires R-2/P-40 detail ingestion"
    blocker was re-probed rather than re-asserted. Of the three orgs the
    2026-07-05 findings entry named as having no loaded book, **DHA has one and
    DEFW/IG do not**: the FY2026 Defense Health Program justification book is
    published on `comptroller.war.gov` (the per-section R-1/P-40/R-2 URLs all
    404; the combined `00-DHP_Vols_I_and_II_PB26.pdf` serves
    200/3,348,155 bytes — both HEAD-verified 2026-09-12, control
    `RDTE_OSD_PB_2026.pdf` 200/16,602,088 bytes) and is now registered as one
    `rdte` document via `registry.DEFENSE_HEALTH_NAMES`; the FY2026 index
    publishes only O&M exhibits for the DoD IG (`OIG_OP-5.pdf`,
    `OIG_Cyber_OP-5.pdf`), and no DEFW-specific book at all (three of DEFW's
    four pages are P-1 reconciliation/undistributed workbook rows). Those
    absences are recorded in `data/research/edition_manifest.json →
    org_absences`. **The book carries no jb-2009 payload:** acquired
    2026-09-12 (document 459, 3,348,155 bytes, `has_embedded_xml` false — the
    424-page PDF carries no attachments at all), so `jbooks extract --org DHA`
    selects nothing, DHA loaded **0 detail rows and 0 narratives**, and the
    workbook-only page count stays 73. The row stays `downloaded` as real
    provenance (a terminal status: FY2026 is 82 discovered / 82 terminal, and
    `edition_coverage_gate5e` still reads `loaded`), and DHA stays OUT of
    `ingested_service_orgs` because that set now requires loaded detail — which
    is the point: the same download would have flipped all 14 DHA pages to
    "the book is ingested, this element simply has no narrative" under the old
    `status='downloaded'` predicate (measured after the acquire: old predicate
    26 codes incl. DHA, new predicate 24). The rescrape found 38 documents /
    1 new — only the DHP volume. `PROC_SDA_PB_2026.pdf`, which a 2026-09-10
    read-only simulation of the classifier reported as newly added, is
    **commented out on the index and 404 at origin** (HEAD-verified
    2026-09-12): its `<li>` sits inside an HTML comment, so the selectolax
    parse `discover_documents` uses never sees the href (117 + 18 live PDF
    links, re-read 2026-09-12). No FY2026 SDA row was registered and nothing
    SDA-shaped was extracted. `dim_programs` entries for the remaining workbook-only
    elements stay out of scope by design.

    *Update 2026-09-12 (Task 17b):* the coverage note is no longer keyed on the
    rollup TIER but on whether a page has R-2/P-40 detail at all
    (`isWorkbookOnlyDetails`), so `0603115DHA` and `0708083D` stop asserting a
    J-book detail they do not have; `/methodology/`'s figures-only residual
    sentence now names the unloaded organizations from a build-time query
    (`getUningestedCoverageOrgs` — DHA 14, DEFW 4, IG 1 in the shipped corpus)
    instead of claiming no page blames a missing book; and gate 21 leg (o)
    fails when the rendered sentence and `site_meta.ingested_service_orgs`
    disagree in either direction — the check the 2026-07-05 fix shipped
    without. Leg (o) reads every non-decade page (no sampling): 73 render the
    note, 1,936 with detail carry none, and the negative direction is floored
    at 1,500 rather than the note population, which SHRINKS when a book lands.
15. **District choropleth + entity-graph viz (5C deferred):** interactive map of
    district spend distribution and force-directed entity graph; deferred pending
    D3/Mapbox integration decision.

    **Status: CLOSED — DEFERRED AS A NON-GOAL, owner decision 2026-08-29.**
    Measured 2026-08-29 before deciding: `fct_district_totals` covers **106 of 435
    districts** and **$5.58B** of linkable obligations. A choropleth would render a
    map roughly three-quarters blank, and **readers read blank as zero, not as
    unknown** — so the most visual page on the site would be its least honest one.
    The layman review of 2026-08-27 already named `/district/` the largest gap
    between promise and delivery ("See what a district builds" → $940.8K of DARPA
    money in CA-11); a map widens that gap rather than closing it. Blocked on
    COVERAGE, not on visualization: it becomes worth building when award linkage
    improves, and USAspending not publishing the program element on award records
    (see #30, whose crosswalk reaches 24 of 1,753 programs) is why it has not.
    *(Original marker below.)*
    **Status: OPEN** — swept 2026-08-24. Never scoped: named out of scope in
    the drawdown plan; no commit references it. Verified at HEAD: no choropleth
    or Mapbox code anywhere under `site/src`.
16. **"Why?" link phrasing consistency (5C):** ~~several detail pages mix "How is this
    calculated?" / "Source" / "Why?" for the same action — standardize to one phrase.~~
    **DONE 2026-07-02:** standardized to the explicit `why <topic>? →` convention
    across detail pages.

    **Status: CLOSED** — swept 2026-08-24. Fleet round; recorded by `2efab28`
    (2026-07-02).
17. **Program pages for trajectory-only PEs (5C):** ~~136 PEs have feed events but no
    program page; they produce dead links in the feed until pages are generated.~~
    **DONE 2026-07-02:** exporter synthesizes dim_programs-shaped rows for feed PEs
    outside dim_programs (`_trajectory_only_feed_programs`): title from dim_pe_titles,
    exhibit_family from fct_budget_lines exhibits, trajectory figures reuse the
    already-emitted derived citations; honest absences elsewhere (no FY24 J-book
    headline / details / narratives / dossier). programs.json 326→462 pages;
    program_details, search docs, sitemap, OG cards, coverage denominators
    ("N of 462") all follow from data. Feed cards regained "view program →" links
    via the existing programs.json gate. agencies.json stays dim_programs-scoped
    (derived agency-sum recompute unchanged); service-org codes (A/N/F/DHA) render
    as plain text in the program header, never a dead link. This also completes the
    page-generation half of backlog #14 (dim_programs entries themselves still
    require R-2/P-40 detail by design).

    **Status: CLOSED** — swept 2026-08-24. Fleet round; recorded by `2efab28`
    (2026-07-02).
18. **llms.txt / sitemap origin gate:** ~~a build without NEXT_PUBLIC_SITE_URL bakes
    the placeholder origin into tracked/deployed artifacts (caught once in a fleet
    straggler, 2026-07-02). Add a verify leg: production artifacts must not contain
    `govbudget-placeholder.example`.~~
    **DONE 2026-07-03:** two layers — verify-phase5b3 defaults
    NEXT_PUBLIC_SITE_URL for its wrapped npm verify (920c225), and gate 1
    now carries the requested UNCONDITIONAL placeholder scan
    (sitemap.xml/llms.txt/robots.txt/index.html must not contain the
    placeholder host, independent of the verify-time env — the env-relative
    sitemap-origin leg alone would false-pass a placeholder build verified
    without the env, since its fallback is the same placeholder).
    Pre-failure proof in reviews/5c-gates-pre-failure.txt.

    **Status: CLOSED** — swept 2026-08-24. `0cf30e5`, recorded by `746287f`
    (fix round A2, 2026-07-03).
19. **LDA re-pull to activate curated aliases (from backlog #1):** **PARTIAL
    (2026-07-04).** ✅ The first-query-wins attribution bug is FIXED + committed
    (7bb1582): best-match-tier resolution (exact_family > curated_alias >
    normalized > family_raw_name > suffix_residue > none; ties → higher
    obligation), query-order independent, 3 TDD regression tests — VECTRUS's
    'V2X' query no longer starves VERTEX AEROSPACE's curated alias.
    ⏸ DEFERRED — the live `influence pull` + dbt/mentions rebuild + export-site
    + dossier-citation check + match-gate raise to 0.85: the re-pull can change
    filing amounts, and fact identity includes amount, so it can orphan the 50
    static dossier claims that cite lobbying facts. Regenerating dossiers needs
    the Anthropic API (capped until 2026-08-01 — see #22). Rather than start a
    long live warehouse mutation that might leave dossiers broken with no repair
    path, run this as ONE unit after the cap resets: pull → ripple → dossier
    gate → (regenerate any orphaned dossiers) → measure live match rate → raise
    gate to 0.85 + boundary tests 43/50 only if the measured rate supports it.

    **Status: CLOSED 2026-09-25** — ledger sweep; both halves are done. Pull:
    `7d03475b` (2026-08-27) + `f83feca4` (2026-08-29). Threshold: raised 0.80 →
    0.85 in `bcfe9680` (2026-09-01) on a measured 46/50 = 92% (floor 43/50),
    with the boundary tests `test_pass_boundary_86_pct` (43/50) and
    `test_fail_boundary_84_pct` (42/50) in `tests/test_verify_phase5a.py`. The
    2026-08-27 marker below predates the raise. Dated figure corrections to the
    markers below, measured 2026-09-25: `lda_filings.parquet` holds **5,393**
    filings (not 5,392) and `lda_program_mentions.parquet` **14,016** rows
    (12,448 was the 2026-08-27 count); the seed the original marker cites is
    `dbt/seeds/client_aliases.csv` — `data-seeds/client_aliases.csv` does not
    exist. Not built, and not claimed: the freshness leg `bcfe9680` names as
    separate work (`src/govbudget/verify_phase5a.py:88-93` — a frozen corpus
    scores 92% forever); the LDA cadence gap it would close is #8 (a).
    *(Earlier markers below.)*
    **Status: PARTIAL — pull half CLOSED 2026-08-27, threshold half still open.**
    The re-pull ran and the premise this entry deferred on was FALSE: `fact_id_lda_filing`
    hashes `(filing_uuid, role)` only — the amount is not an input — and exactly 1 of the
    432 distinct dossier fact_ids is an `lda_filing` at all. Cost was under $1, not the
    ~$28.60 recorded (13× over; list price with the Batch discount omitted).
    **The pull was also silently broken:** `lda.senate.gov` now 301-redirects to
    `lda.gov`, httpx does not follow redirects, so every request failed into a warning
    handler and the corpus had been stale since 2026-07-03. Fixed in `7d03475`, which
    also added the empty-pull guard that did not exist — the parquet write was
    unconditional, so a pull that fetched nothing would have overwritten a 4,394-filing
    corpus with an empty one and returned normally. That is what backlog #8 was about to
    schedule. Corpus after: filings 4,394→5,392, activities 9,999→12,402, lobbyists
    14,422→18,118, mentions 10,650→12,448 across 453 programs; `dbt build` PASS=133
    ERROR=0. Still open: raising `verify_phase5a.py:62 _MATCH_THRESHOLD` from 0.80 to
    0.85 — deliberately NOT done, because the measurement to justify it has not been
    taken and raising a threshold the data does not support fails on honest input.
    *(Original marker below.)* **Status: PARTIAL** — swept 2026-08-24, and the entry's own "PARTIAL
    (2026-07-04)" still holds. The attribution half is fixed (`7bb1582`,
    recorded `599371b`, 2026-07-04). The deferred half — live `influence pull`
    → ripple → dossier gate → match-gate raise — has never run: drawdown Task
    D1 was written for it and no commit references that task. Verified at HEAD:
    `_MATCH_THRESHOLD = 0.80` (`src/govbudget/verify_phase5a.py:62`), and
    `data-seeds/client_aliases.csv` has not changed since 2026-07-02.
20. **Render-level sankey label bbox gate leg (5H judge hardening):** ~~the
    exporter TDD bbox test proves the *precomputed* layout is collision-free,
    but if the site font or node metrics ever drift from the exporter's
    assumptions, labels could re-collide at render time. Add a G9 Playwright
    leg asserting no two rendered flow-label bounding boxes intersect at 1440.~~
    **DONE 2026-07-03:** G9 leg f — getBoundingClientRect on every rendered
    label (one <text> per node group), same-river pairs, ≤1px tolerance,
    collected at initial render AND after the FY switch; zero labels found
    fails loudly. The first clean run caught a REAL shipped collision
    (b:a:CLASSIFIED|3080F × b:ba:F|3600F|05, 9.9×2.5px) — root cause was the
    exporter model under-measuring "Avenir Next" (LABEL_H 10 vs 13.09-unit
    rendered em box; several width buckets below measured advances). Fixed
    exporter-side (LABEL_H 13.2, buckets re-derived to dominate measured
    advances, GUTTER_MAX 250→270) + re-export. Pre-failure (CSS font
    injection, 166 errors) + live-catch record in
    reviews/5c-gates-pre-failure.txt.

    **Status: CLOSED** — swept 2026-08-24. `9671f42`, recorded by `746287f`
    (fix round A2, 2026-07-03).
21. **favicon.ico 404:** ~~browsers request /favicon.ico by default; the site
    ships only the Next.js app-dir icon. Add a favicon.ico to site/public/
    (or a redirect) — found as the sole console error during 5H live
    verification. Also from judge advisories: include print-CSS +
    reduced-motion captures in visual-judge evidence packs; consider pinning
    the breakdown-overlay filter box in the sticky header.~~
    **DONE 2026-07-03:** real favicon.ico (16/32/48 PNG-entry ICO, brand
    receipt mark on the OG palette; scripts/generate-favicon.mjs for
    provenance) + explicit icons metadata; breakdown-overlay filter input
    moved into the overlay's non-scrolling header (state lifted to
    BreakdownOverlay, reset on close; 4 new vitest cases); evidence-pack
    print + reduced-motion capture requirement documented in
    reviews/EVIDENCE-CONVENTIONS.md.

    **Status: CLOSED** — swept 2026-08-24. `5d06e2a`, recorded by `746287f`
    (fix round A2, 2026-07-03). Verified at HEAD: `site/public/favicon.ico`
    exists.
22. ~~**Confirm eval robustness fixes post API-cap reset:** run `verify-phase5`
    once the Anthropic cap resets — the table-equivalence groups, temperature-0
    determinism, SQL-determinism rules, and transient-error retries need one
    confirming exit-0 run.~~ **DONE 2026-07-05:** the user raised the monthly
    cap; `verify-phase5` exits 0 — gate freshness PASS, **gate eval 48/48
    accuracy + 43/43 citations PASS**, gate assembly PASS (artifact
    eval-20260706T014127Z). All robustness fixes held on a fresh live run: no
    flakes, no mid-run transport ERRORs, 100% citation resolution. The freshness
    gate additionally caught a legitimate 1-answer drift — q017
    `fct_budget_trajectory` 1982→1980, from the p1_loader junk-pe_bli cleanup
    (commit 481bba0 removed 2 bogus PEs); the analyst answered 1980 correctly and
    the stale expected was re-baselined (sanctioned mechanical fix). Still open
    as a nicety: the runner scores a transport ERROR as "correct" on
    REFUSE-expected questions — worth a distinct ERROR outcome someday (backlog).

    **Status: CLOSED** — swept 2026-08-24. `aa3c5ae` (2026-07-05). The "still
    open as a nicety" clause at the end of this entry — a distinct ERROR
    outcome for REFUSE-expected questions — was later addressed by `c97c9e8`
    ("an agent crash is not a correct refusal", 2026-08-12), which was never
    filed as its own number.
23. **Decade-parquet ↔ lake integrity leg** (Task 6 review): ~~a dedicated gate
    recomputing budget_lines_decade.parquet from the lake would close the
    residual artifact-tamper window for both parquets symmetrically.~~
    **DONE 2026-07-03:** verify-phase5e gate e (decade_parquet_gate5e) —
    ≥30 sampled decade-parquet rows; each row's grain (pe_bli, edition,
    amount_type) must sum across the whole parquet to a scenario_map
    candidate sum in the lake (reuses _lake_candidate_match, P-1R
    excluded). Main budget_lines.parquet deliberately out of scope (direct
    Postgres export, anchored by verify-phase5b1 — see gate docstring).
    Proof-can-fail recorded in reviews/5c-gates-pre-failure.txt; exhaustive
    off-gate sweep: all 32,233 grains recompute, 0 failures.

    **Status: CLOSED** — swept 2026-08-24. `2460b6d`, recorded by `f74df36`
    (fix round A1, 2026-07-03).
24. **fid_to_bl_amount overlap equality assertion** (Task 6 review): ~~5,257
    fids exist in both budget_lines and decade parquets; assert amount
    equality so a divergent decade copy can't hide behind setdefault.~~
    **DONE 2026-07-03:** _load_fid_to_bl_amount now Decimal-compares every
    overlapping fid; any divergence FAILs verify-phase5b1 gate 1 with the
    offending fids listed (first 10). Live run: 5,257 overlap, 0 divergent.

    **Status: CLOSED** — swept 2026-08-24. `07a5925`, recorded by `f74df36`
    (fix round A1, 2026-07-03).
25. **PB2024 P-1R title backfill** ~~(582 title-NULL rows; P-1 was fixed in the
    Task 5 improvements round; P-1R out of scope there).~~
    **DONE 2026-07-03:** the P-1R sheet uses the same 'Program
    Element/Budget Line Item (BLI) Title' header the P-1 fix already
    mapped, so scripts/backfill_pb2024_p1r_titles.py (wipe+reload,
    self-verifying) sufficed: 582 rows, title-NULL 582 → 0, amount drift 0,
    lake re-exported. Honest residual: PB2025 (450) and PB2026 (403) P-1R
    rows are also title-NULL for the same historical reason — reload those
    two documents with the same pattern if P-1R titles ever render.

    **Status: CLOSED** — swept 2026-08-24. `6c7cb3a`, recorded by `f74df36`
    (fix round A1, 2026-07-03). The PB2025/PB2026 P-1R residual named in the
    last sentence is still outstanding and was never given its own number.
26. **Dead-PE 0605230F request_vs_request minting** if a feed claim ever
    covers request-vs-request swings (currently scoped to request-vs-actuals
    precisely because those are 100% minted).

    **Status: CLOSED** — swept 2026-08-24. Drawdown Sprint A, Task A1;
    `c7293e5` (2026-08-12), closed as contingent-not-applicable — the feed has
    no `request_vs_request` event type for the fact to serve. The blockquote
    near the end of this section dates it 2026-08-08, four days before that
    commit.
27. ✅ **DONE 2026-08-06 — R2 sync folded into the deploy loop + a live-asset
    check that runs itself.** The deploy drill (rebuild → Vercel `--prod`)
    never re-synced `data/site/pdfs → R2`, so PDF citations for every
    post-launch phase silently degraded in production until the 2026-07-04
    catch. (a) `scripts/launch/deploy.sh` is now the only deploy path and the
    source of truth for the sequence: preflight (out/ complete, `vercel.json`
    present, rclone + PDF source present) → `upload_r2.sh --live` →
    `vercel --prod --yes --archive=tgz` from `site/out/` → live verification.
    Assets go up BEFORE pages, so no live page ever cites a binary that is not
    there yet (`upload_r2.sh` never deletes, so an early sync is always safe).
    LAUNCH.md §7d now points at the script and keeps only the *why* — the two
    load-bearing constraints (cwd `site/out/`, `--archive=tgz`) and the
    backlog-#27 history. (b) `scripts/launch/verify_live_assets.mjs` fetches the
    N most recently added **cited** `jbook_pdf` assets (newest binaries under
    `data/site/pdfs/` that a `hosted_pdf_url` actually points at — citations.json
    is ~90 MB so it is streamed, not parsed) and asserts 200/206 + non-zero body
    + `%PDF-` magic, plus `citations/citations.parquet` and the site's `/fact/`
    rewrite. **Deliberately NOT a gate in `npm run verify`**: that suite is
    hermetic and offline by design, and production CDN state cannot be true
    before the upload that creates it — a pre-deploy gate asserting it would be
    vacuous at best and green-on-last-deploy's-assets at worst. It is step 4 of
    `deploy.sh`, exits non-zero, and is runnable standalone to audit what is
    live. Proof-can-fail recorded (a real 404 for an absent sha).

    **Status: CLOSED** — swept 2026-08-24. `712485d` (2026-08-06), matching the
    in-entry marker. Verified at HEAD: `scripts/launch/deploy.sh` and
    `scripts/launch/verify_live_assets.mjs` both exist.
28. **Agency PEs with ingested decade detail but no FY2026 page (coverage
    enhancement, NOT a bug — surfaced by the 2026-07-05 audit).** A large set of
    program elements carry FY2017–2025 J-book/workbook detail in the warehouse
    but have no FY2026 `budget_lines` row, so they generate no `/program/`
    page — the decade history exists but isn't browsable (the audit estimated
    ~271 agency PEs under its criterion; a looser budget_lines-only cut is
    larger). These are legitimately absent from FY2026 (zeroed, consolidated,
    or renamed lines), so this is a decision about whether to build history-only
    pages for a PE that no longer requests money, not a data defect. Scope if
    taken: a "decade-only" page tier (or fold into the rollup tier with an
    explicit "no FY2026 request" note), gated for citation-completeness like the
    other tiers. Deferred — verify the exact eligible set and its editorial
    value before building.

    **Status: CLOSED 2026-08-31** *(date corrected 2026-09-25 from
    "2026-08-29": the four commits are dated 2026-08-31 and the ledger commit
    `8322b688` 2026-09-01. Residue: the "PB2023workbook" species named below —
    a space dropped beside an interpolation — survived on five other sites and
    was closed as #106 by Task 2: `e664dce4`, `9aee170c`, `663a759c`,
    `ad23016b`, `090d63db` + `a18111e2`, all 2026-09-11.)* Shipped `9545546`/`6b51030`/`92789cc`/`bfa575f`
    and live: **553 decade-only pages**, not the 624 measured on 08-27 — Wave 5's
    Navy ingestion gave 71 of them an FY2026 line in between, which is exactly why
    the implementer was told to re-measure. Four follow-on defects came with it and
    are fixed: `program_pages` summed two loops' INPUTS so a third loop published
    2,009 against 2,562 sidecars on disk (caught by gate 24 leg (k), the "a corpus
    count must derive from a declared source" leg added in Wave 4 — its first catch
    of something nobody anticipated); the zero-content detector read a decade of
    cited history as empty because `figures.every(v => v === 0)` is TRUE on an empty
    array; the coverage cell printed a split whose parts were not asserted to sum;
    and React dropped the space beside every interpolation so readers saw
    "PB2023workbook". `/methodology/` gzip 36,900 → 39,100, justified by the 553
    pages that moved the corpus counts the page states. *(Original markers below.)*
    **Status: APPROVED 2026-08-27, queued.** The entry asked for the eligible set
    to be verified and its editorial value decided before building; both are now
    done. **Measured population: 624 real program elements** with a decade of cited
    history and no FY2026 page (`0605230F` $20.8B 2017–2024, `1206442F` $11.4B,
    `0303140G` $9.2B among them). The entry's own "~271" is **2.3× low**, and a
    naive `budget_lines`-minus-built-pages cut returns **1,853** — 3× high, because
    **1,214 of those are synthetic `-L<n>` rollup parse artifacts** (`3010F-AF-L1`
    carries $142.6B) that must never become pages. Building against the naive cut
    would have generated 1,214 pages for parse debris. Separately verified and
    CLEARED: those artifacts hold 35.8% of `fct_budget_lines` and 20,781 of 59,179
    `fct_decade_series` rows, but **all 9 reader-facing parquets carry 0 of them**
    and `years_matrix.json` carries 0 — no published or reader-queryable figure is
    inflated. Owner decided 2026-08-27 that a program which no longer requests
    money should still have a browsable history page. *(Original marker below.)*
    **Status: OPEN** — swept 2026-08-24. Deferred by the entry itself and
    assigned to drawdown Task D5 ("decide before building"), which never
    executed; no commit in the history references #28.
29. **Program-lineage Phase 2 (coverage + depth, from 5I).** The Phase-1 lineage
    layer is small-but-bulletproof (25 stated + 3 inferred edges) because regex
    over narratives is high-precision/low-recall and stated edges are FY2026-fenced
    to the cite-shard edition. Phase 2 expands it, each piece with its own honesty
    gate: (a) **LLM extraction** over the ~1,950 prose transfers that name a move
    but no adjacent PE code → many more *stated* edges, each verified to resolve,
    gated on an extraction-precision check (uses the API); (b) **multi-edition
    citations** so the 28 pre-2026 stated edges (dropped in 5I for cite-shard
    resolvability under the binding PB2026 fence) can ship with resolving cites;
    (c) a **lineage Sankey** (reuse the `/flow/` renderer) — identities as nodes
    over time, dollar ribbons for transfers/splits/merges; (d) cross-appropriation
    (RDT&E↔Procurement) money-color lineage beyond what a stated narrative asserts.
    Two dormant 5I code notes to fold in when they become live: when `portion_amount`
    extraction lands, `has_split` (exporter `_emit_lineage`) must also flag a
    partial-transfer chain truncation so the funding line is always explainable;
    and `_load_lineage_for_export`'s `fiscal_year or 0` coercion should skip/log an
    unparseable fy rather than emit a fy:0 edge (both unreachable in Phase 1).

    **Status: CLOSED 2026-08-29 — all four parts.**
    **(a) LLM extraction** `3e465a7`/`4a8401f`/`319025a`: precision methodology
    pre-registered and committed BEFORE the first API call and unedited since.
    Pilot **19/21 = 90.5%, under the ≥95% bar — nothing published on it**; both
    failures bought generalising rules (V11: a clause calling its own move
    "one-time" is not lineage; V10: an adversarial second read quoting verbatim),
    then **32/32 on held-out pairs the rules were never tuned against**. Stated
    edges **49 → 98**, families 32 → 52, family PEs 80 → 148. **199 of 248
    proposals refused, zero fabrications** — candidates are pre-filtered to clauses
    already containing a PE token, so a model is never asked to supply an endpoint.
    Two refusals worth keeping: numeric line items permanently (pe_bli is not
    unique for them — "1350" is both *Infantry Weapons Ammunition* and *Missile
    Industrial Facilities*), and a clause naming `0604840M` where the corpus PE is
    `0604840N`, a phantom one character from a real node. **$2.60** against a
    $10–20 budget. The entry's "~1,950 prose transfers" did not reproduce: the
    extractable subset is **313 clauses**.
    **(b) multi-edition citations** `b9d0804`: the PB2026 fence was the whole
    problem — pre-2026 narratives were already in Postgres, not missing.
    **(c) lineage Sankey** `2601c43`: `/lineage/`, 32 families, every ribbon a
    constant 8.0 units because `portion_amount` is null on every row; the exporter
    RAISES if that premise breaks.
    **(d) cross-appropriation: SHIPPED NOTHING**, and that is the result — 11
    candidates, 33 verifier agents, all refuted. Co-funding is normal (Aegis BMD's
    RDT&E line RISES to $3,888.4M in FY2026 while procurement falls to $796.5M);
    procurement key renumbering fabricates a rise from zero; and the corpus already
    contradicted one edge in a cited narrative. Written up in
    `docs/superpowers/reviews/29d-cross-appropriation-negative-result.md` so the
    rule is not rebuilt. **#32(b) is absorbed here and also closed.**
    *Addendum 2026-09-25 (ledger sweep): this block was moved above the
    2026-08-27 marker it supersedes, text unchanged. Two dated notes. (c) — the
    "32 families" above is the (b)-era count; after (a) the lineage flow
    carries **52** families, 152 identities, 98 stated and 3 inferred edges
    (`data/site/json/lineage_flow.json`, chain C run 4 export, 2026-09-25), and
    (c)'s code is `a71a5b18` + `8c3888f9` (2026-08-28) — `2601c43` only
    records a gate leg's live catch in `5c-gates-pre-failure.txt`. (d) — the
    roadmap-completion branch neither committed
    nor deleted `src/govbudget/lineage/cross_appropriation.py`, the
    implementation of the refuted rule: it has never been committed on any
    branch and exists only as an untracked file in the main checkout, where
    the 2026-09-10 roadmap audit found it promising a verify-lineage leg (k)
    that does not exist (`verify_lineage.py` has legs (a)–(j)). The negative
    result stays prose-only in
    `docs/superpowers/reviews/29d-cross-appropriation-negative-result.md`;
    commit the module with its leg or delete it — the owner's checkout, the
    owner's call.*
    *(Original marker below.)*
    **Status: (b) CLOSED 2026-08-27 · (a) APPROVED, queued · (c)(d) queued.**
    **(b) shipped** (`4e6daa9`/`e85d101`/`03cf77c`/`b9d0804`): the PB2026 fence was
    the whole problem — pre-2026 narratives were already in Postgres
    `detail_narratives` (all ten editions), not missing as assumed; `export_site`
    was fencing them out of the citation layer. Split `CITED_NARRATIVE_FY` from
    `DISPLAY_NARRATIVE_FY` so evidence reaches back while program prose stays
    PB2026-fenced. Stated edges **29 → 49**, families 22 → 32, family PEs 51 → 80,
    page-anchored 13/29 → 32/49. The entry's "28 pre-2026 edges" reproduced as a
    MINT count but is only **20 distinct links** — 7 are one transfer narrated by
    several editions (an edge's `fiscal_year` is the edition asserting it, not the
    year money moved) and 1 carries two relation labels; publishing 28 would have
    double-counted. Supersession scan refused 0, and deliberately does NOT treat
    "PE still has money after the transfer year" or absence-of-later-mention as
    contradiction. verify-lineage gained legs (g) artifact-cite and (h)
    no-supersession; 8/8 PASS. **(a) LLM extraction APPROVED by the owner
    2026-08-27** (~$2 pilot, ~$10–20 full pass) — the only paid item in the
    backlog. *(Original marker below.)*
    **Status: OPEN** — swept 2026-08-24. Assigned to drawdown Task D3; never
    executed. Verified at HEAD: `src/govbudget/lineage/extract.py:5` still says
    prose transfers without an adjacent PE code "are left for the Inferred tier
    / Phase-2 LLM". The stated-edge count has moved since this entry was
    written (25 → 31 in the 5I review, then 31 → 29 by #53's retraction fix)
    but the Phase-2 scope is untouched.
30. **Program-level GAO ingestion (from PM Sprint 2 §P1-10).** The Oversight
    section on a program page currently shows only the DEPARTMENT-level GAO
    designation (`DOD — 5 high-risk areas`), now correctly labelled
    "Department-level designation (not specific to this program)" and visually
    de-emphasized so it cannot be mistaken for a program finding. What is
    missing is the program-specific tier: GAO issues real program-level work
    (the annual Weapon Systems Annual Assessment GAO-25-107569 and its
    predecessors; program-specific reports and recommendations), and on the
    F-35 in particular the absence is conspicuous. Phase: ingest GAO reports
    keyed to weapon programs, crosswalk report→pe_bli (title/PE match, gated
    like every other crosswalk on a precision check), render program-specific
    findings ABOVE the department note with the emphasis the department note
    gave up, and cite each to its report page. Until that lands, the honest
    statement on the page is exactly what it now says: no program-specific GAO
    finding for this line is in the ingested data.

    **Status: CLOSED 2026-09-12 — the "and its predecessors" half.** GAO-24-106831
    (Jun 2024) and GAO-23-106059 (Jun 2023) are ingested beside the 2025 volume:
    **65 / 69 / 65** Appendix I assessments = **199**, plus the current edition's 68
    bibliography reports (an older edition's bibliography is NOT re-read — its
    products nobody adjudicated). **111 predecessor links**: same normalized common
    name AND service family, nearest earlier edition, nothing fuzzier, so a rename
    breaks its own chain by design rather than putting GAO's words on another weapon.
    An older edition reaches a page ONLY behind a ratified current-edition anchor, and
    the matcher is fenced to the current edition (`generate_candidates(...,
    current_product=)`), so no new verdict was written: `gao-xwalk` still prints
    **74 candidates / 63 adjudicated → 62 accepted, 98.4%**, byte-identical apart from
    its new UNLINKED block. **48 pages carry 132 GAO items — 62 ratified attributions
    and 70 inherited earlier editions.** The gap is stated, not hidden: **23 programs
    GAO assessed only in an earlier edition reach no page** (31 assessment rows, listed
    by `gao-xwalk`), and the entry's own flagship is one of them — GAO-25-107569
    assesses no F-35 at all, so both older volumes' F-35 (2024 PDF p.213, 2023 p.217,
    `Lead Component: DOD`) is ingested and visible as an UNLINKED line while reaching
    no page. Closing that needs the matcher widened to older editions plus a fresh
    hand-adjudication pass — owner decision. Gate 21 leg **h8** binds each rendered
    item's edition stamp, the sentence a reader sees, its ratified anchor (same
    program, same family, strictly newer) and the inherited COUNT to the exporter's own
    `stats.inherited_items`; the service-family map is emitted into the sidecar from
    `gao_programs._SERVICE_FAMILY` rather than mirrored. **Fix round 1, 2026-09-12:**
    the heading rule had silently dropped three real assessments and swallowed GAO's
    first description sentence on three more (see the findings log); the parser now
    raises on any bannered program it fails to emit, and 199/111/23 are the
    post-fix measurements.

    **Status: CLOSED 2026-08-27.** Shipped `de19aa2`/`e642c83`/`d99d015` and live.
    One HTTP GET (GAO-25-107569), 65/65 Appendix I assessments + 68 bibliography
    reports. **62 of 63 crosswalks accepted = 98.4% precision**, every candidate
    adjudicated BY HAND against a second source — the budget line's own J-book
    narrative, not its title. The single refusal is the argument: GAO assessed
    *Small Diameter Bomb Increment II*; the matcher proposed `SDB000`, whose
    narrative opens *"GBU-39/B: Small Diameter Bomb Increment I"* — a different
    weapon, so SDB II ships **no crosswalk at all** rather than a wrong one.
    Service-rule ablation: with it 1 wrong of 63, without it 3 of 65 — and the two
    it suppresses are #55's exact species (GAO's *Air Force* "LGM-35A Sentinel"
    reaching the *Army's* "Sentinel Mods"). 48 pages gained a finding; **1,957
    correctly still state that no program-specific GAO finding is ingested**.
    `pypdf` was rejected for splitting words across line breaks — "Production Is
    sues" — on the grounds that a verbatim quote reassembled from broken words is
    not verbatim. **The entry's own flagship example did not reproduce:**
    GAO-25-107569 contains no F-35 assessment; the F-35's three reports come from
    the bibliography tier. *(Original marker below.)*
    **Status: OPEN** — swept 2026-08-24. Assigned to drawdown Task D4; never
    executed. Verified at HEAD: no GAO program-level mart under
    `dbt/models/marts/`, so the honest statement described in the last sentence
    is still the one the page makes.

31. ✅ **DONE 2026-08-04 (PM Sprint 3 Task 1) — a gate now exercises a mobile
    viewport.** The defect class: three mobile blockers — `/companies/` rendering its
    money column off-screen, `/data/` pushing its scope prose off-canvas behind
    250–400px near-empty rows, and `/families/` hiding the Source column that is the
    page's entire credibility claim — walked past a 24-gate suite untouched and were
    caught only by human-style visual judging, because every gate that drives a
    browser did so at desktop width. **Gate 3 (render-live) gained a 390×844 leg**
    (`site/scripts/gates/mobile.mjs`; standalone runner `run-mobile-leg.mjs`; sample
    pinned by 9 vitest cases) rather than a 25th gate — gate 3 already owns "does
    every page class render in a real browser" and its harness, so this is the same
    question at a second width. Two assertions: (m1) no page-level horizontal
    overflow over a 13-page sample covering every page class carrying a table or a
    wide chart, and (m2) the primary value element's box fully inside the viewport on
    the five value-bearing pages, identified by `data-*` hooks and never by text.
    (m2) is the load-bearing one: all three blockers sat inside an `overflow-x-auto`
    wrapper, so the container scrolled and (m1) alone passes on two of the three.
    Proof-can-fail reverts the three real Sprint-2 treatments in a scratch copy of
    the built stylesheet — all three reproduce, `/families/` at exactly the recorded
    +98px. **The first run against the live build found a fourth, shipping instance:
    `/district/`'s Linkable-dollars column sat 38px off the right edge at 390** (the
    Sprint 1 fact-id chip re-widened it past the Sprint 2 State-column fix); fixed by
    hiding the Programs column below `sm` with the count moved under the district
    code. Evidence: `docs/superpowers/reviews/5c-gates-pre-failure.txt`.

    **Status: CLOSED** — swept 2026-08-24. `03806e6` (2026-08-04), matching the
    in-entry marker. Verified at HEAD: `site/scripts/gates/mobile.mjs` exists
    and has since grown legs (m3), (m4) and (m5) for #40 and #65.

32. **Program-element lineage across a taxonomy renumber (from PM Sprint 3 Task 1b).**
    Task 1b withdrew 87 false "zeroed out in FY2026" feed cards, but the investigation
    surfaced a real and unmodelled phenomenon underneath them: **PB2026 renumbered
    program elements at scale, and the corpus has no way to say so.** Counting PEs in
    the PB2026 edition that carry FY2024/FY2025 money but no FY2026 figure ("retired")
    against PEs that carry FY2026 money and nothing earlier ("new"): Army 115 retired /
    33 new, Air Force 77/36, Navy 69/14, OSD 18/9, **DARPA 14/8**. DARPA is the clean
    case because it is small enough to read end to end: PB2026 retired *Defense Research
    Sciences*, *Tactical Technology*, *Sensor Technology*, *Electronics Technology* and
    10 more thematic lines, and introduced *Emerging Opportunities*, *Access and
    Awareness*, *Warfighting Performance*, *Effects*, *DARPA Advanced Technology
    Development* and 3 others — while DARPA's FY2026 total **rose to $4.92B from
    $4.15B**. Only 2 of 16 PEs carried through unchanged. **This is NOT an ingestion
    gap** — verified against the primary source, `data/raw_docs/fy2026/dod/r1_display.xlsx`
    shows the FY2026 cells for the retired lines are genuinely BLANK and the new lines
    genuinely have no FY2024/FY2025 history; the parser is reading the workbook
    correctly (an earlier "DARPA coverage artifact / parser problem" hypothesis was
    investigated and refuted). The gap is in the MODEL, not the data: nothing links a
    retired PE to its successors, so a reader who followed *Defense Research Sciences*
    for a decade hits a page that simply stops at FY2025 with no forward pointer, and
    any YoY analysis keyed on pe_bli silently drops ~$7B of continuing work. This is
    the natural next edge type for the 5I lineage layer (backlog #29): a
    `pe_remap` / `restructured_into` edge, evidence-tiered like the existing Stated and
    Inferred classes — Stated where a PB2026 R-2 narrative names the predecessor PE,
    Inferred where budget-activity + account + money conservation make a mapping likely.
    Until it exists, program pages for retired PEs should at minimum say "this program
    element does not appear in the FY2026 request" rather than ending silently — the
    honest version of the claim the withdrawn cards were trying to make. Sizing: the
    edge extraction is Phase-2 lineage work; the "does not appear in FY2026" page note
    is small and independently shippable.

    *Correction 2026-08-07 (for the planned #32a interim-note task, backlog-drawdown
    Task B2 — not yet filed as its own entry):* the task's proposed non-vacuity floor
    of 190 is wrong. 190 PEs carry FY2025 money and no FY2026 row, but only **165 of
    them have a `/program/` page** to render the note on — the other 25 have no page
    at all (that gap is backlog #28/D5 territory, not this task's). A floor of 190 can
    never pass against a 165-page eligible set. **The verified floor is 165.**

    *Correction 2026-08-26 (superseding the 2026-08-07 correction above, which
    is left standing because the reasoning it records is right and only its
    number is wrong):* **165 is not the floor either, and 190 was never the
    population this note is about.** Both figures count `pe_bli`s with FY2025
    money and no FY2026 row across ALL TEN EDITIONS — but the note is a claim
    about ONE edition (PB2026) and is rendered per PAGE, not per pe_bli. (The
    190 reproduces exactly; the 165 does not — **182** of those 190 have a
    `/program/` page at HEAD, and the 8 that do not are the known route-unsafe
    Army mis-parses `O&M` and `RDT&E` plus 6 others, not 25. So the
    "other 25 have no page" clause above is also unreproducible. Recorded, not
    quietly dropped.) Fenced
    to the PB2026 workbook rows each page actually renders, and counted per
    page: FY2025-only is **159**, and FY2024-or-FY2025 — the definition this
    entry's own headline uses, and the only one that reproduces its per-service
    figures — is **319**. That measurement is what the shipped gate uses. The
    per-service check against this entry's numbers: Air Force 77 (77), Navy 69
    (69), OSD 18 (18), DARPA 14 (14) — exact. **Army measures 113 against the
    115 filed here, and the 115 could not be reproduced.** Every variant tried
    returns 113: modal-org attribution, any-org attribution (a pe_bli counted
    under each org it has rows in), and requiring the disqualifying FY2026 row
    to carry money rather than merely exist. It is not a missing-page effect
    either — all 319 retired pe_blis have a `/program/` page, checked. So the
    entry's Army figure is two lines generous by a measurement this task could
    not recover, and **the shipped number is the measured one**: publish the
    smaller true number and label it a correction. Plus 28 across the smaller
    components (SOCOM 6, MDA 6, DISA 3, DCSA 3, DTRA 2, DEFW 2, and one each for
    DCAA, CYBER, TJS, CBDP, DHA, DLA) that the entry never enumerated.

    **Status: CLOSED 2026-08-29.** Half (a) closed 2026-08-26; half (b) was handed
    to #29 and #29 is now closed, so this entry is closed with it. Note what (b)
    actually became: #29(a)'s LLM extraction over renumber-era narratives, which
    doubled the stated tier to 98 edges. *(Original marker below.)*
    **Status: PARTIAL — half (a) CLOSED 2026-08-26, half (b) handed to #29.**

    *Correction 2026-09-05 (#32(b) residue — the note's successor sentence).*
    The (a) note's last sentence, "No ingested budget document in this corpus
    states a successor for this line", was a claim about the DOCUMENTS that
    the exporter (`has_successor`) and gate 21 leg (g) both checked against
    the lineage RAIL, and it was false on **19 of the 287 pages** that
    rendered it (measured 2026-09-05 from the shipped sidecars' own
    narratives): Navy OPN consolidation lines 2900 → LI 2361, 2176 → BLI 2136,
    2026 → LI 2981; six Air Force lines C01200/C02500/C03200/C03700/C04000/
    CFIN00 → BLI OSAEA0; FET000 → PE 0303131F; 0128B63000 → PE 0608041A
    (partial); and eight DARPA PEs whose own PB2026 narratives say, verbatim,
    "Beginning in FY 2026, efforts in this PE will be funded in PE …" (a
    `mission` narrative — on ALL EIGHT: 0601101E, 0601117E, 0602115E,
    0602303E, 0602715E, 0603286E, 0603287E, 0603760E; re-measured
    2026-09-11 over the shipped sidecars' narrative bodies, correcting this
    block's first count of four, which came from a scanner that deduped per
    code and reported only its first match) and
    "Beginning in FY 2026, this program will be funded in PE …" (an
    accomplishment/planned-program narrative, also on all eight) —
    **including 0601101E Defense Research Sciences → 0601122E Emerging
    Opportunities, the case (b) below calls unprovable.** It is stated; the
    extractor does not key it: `lineage/extract.py` `_RULES` has no "will be
    funded in" form, numeric line items are refused at V3-shape, and WSC
    codes are not PE-shaped. The smaller true claim shipped instead: the note
    now says "No successor is linked for this line: this site's
    program-lineage layer holds no keyed edge pointing forward from here" (a
    statement about this site, true by construction) and, where the page
    renders narratives, "if the J-book narrative on this page describes a
    realignment, it is quoted below in the document's own words". The sidecar
    `fy2026_absent` block gained `has_narrative`. **Gate 21 leg (l)** reads
    the sidecars' own narratives (the verbatim `detail_narratives` bodies the
    page renders), fails any note that renders the retired sentence — quoting
    the contradicting narrative — requires the narrative pointer exactly
    where there is prose to point at, checks the exporter's flag against its
    own recompute, and carries a floor of 19 such pages. Keying these as
    edges (line-item/WSC endpoints and the "will be funded in" rule) is
    backlog #105. Species: a "no document says X" sentence gated against a
    derived layer instead of the documents.

    **(a) SHIPPED.** 319 program pages carry the note, gated by **gate 21 leg
    (g)** (`site/scripts/gates/program-skeleton.mjs`) — no 25th gate; the suite
    stays at 24. The exporter emits `fy2026_absent: {last_fy}` per sidecar
    (`export_site.py::_fy2026_absent_block`) and the leg recomputes the same
    predicate independently from the sidecar's own workbook rows, so a drift
    between the two implementations fails the build. The leg runs over the
    WHOLE page universe (2,016 pages, one read pass, no sampling): every page in
    the population must carry `[data-fy2026-absent]`, **no page outside it may**,
    the note must say all four of its required sentences with the year matching
    the recomputed `last_fy`, it must never say zeroed / cancelled / terminated
    / defunded, and **it must name no other program element** — checked against
    the page universe itself, which is the mechanical guard on (b) not leaking
    into (a) as a guess. Proof-can-fail (verbatim FAIL on all 319 + PASS) is in
    `docs/superpowers/reviews/5c-gates-pre-failure.txt`. Page weight is
    untouched: the heaviest `/program/` page (`0601102A`, 142,255 gzip against a
    151,000 ceiling) is still funded in FY2026 and gets no note; the heaviest
    page that DOES get one is `0602716E` at ~81KB gzip. No ceiling was raised.

    **(b) OPEN, folded into #29.** The `pe_remap` / `restructured_into` edge
    type is unbuilt. It stays unbuilt deliberately: the corpus cannot prove
    *Defense Research Sciences* → *Emerging Opportunities*, and a named guess
    would be a fabricated citation — the defect species #53 and #69 closed. The
    note therefore states absence and its context and stops there. Successor
    extraction is lineage Phase 2 (#29(a), LLM extraction, ~$10–20 full /
    ~$2 pilot — the only real spend left in the backlog).

33. ✅ **DONE 2026-08-05 (PM Sprint 3 Task 5b) — a derived parquet older than its
    inputs understated the headline figure on 201 pages by 73%.**
    `data/parquet/entities/entity_xwalk.parquet` was built 2026-06-10 20:19; the
    FY2020–FY2026 contract partitions landed between 21:00 that night and 07:50 the
    next morning. Nobody rebuilt it. Every `/company/{slug}/` and `/companies/` row
    therefore published a `total_obligation` **labelled FY2017–FY2026 that summed only
    FY2017–FY2019** — Lockheed Martin $135.36B against a true $502.12B. The figure was
    never internally inconsistent; it was consistent with a stale input and wrong about
    the period it named, which is why 24 green gates and a 48/48 eval walked past it.
    **The rebuild alone would have been worse than the bug.** `build_entity_xwalk`
    aggregated `recipient_parent_uei` and `recipient_parent_name` with INDEPENDENT
    `max()`, so over a decade — where a recipient's registered parent legitimately
    changes — it took the uei from one transaction and the name from another and emitted
    **6,342 parent pairs that occur on no transaction anywhere**: $210B of Lockheed
    Martin into a family named `SIKORSKY SUPPORT SERVICES`, $88B of Electric Boat into
    one named `WICO`. Both defects are latent in a narrow window and only fire on a wide
    one. The parent is now chosen as a WHOLE PAIR by the obligation dollars behind it,
    under a total order (dollars, count, strings) so the build is reproducible. The
    crosswalk also now spans **contracts ∪ assistance** — the same union
    `fct_award_transactions` is, and the union every minted entity `query_body` sums —
    so `dim_entities.total_obligation` is reproducible from the query printed beside it
    (coverage 94.2% → 100.0%; 87,579 → 129,375 UEIs). **Gate 23 gained leg (d)**
    (`entitytotals-recompute.py`): d1 runs all 1,877 published `query_body` statements
    verbatim and requires each to return its own `recorded_value`; d2 finds the leading
    FY window over which the crosswalk reproduces the lake and requires it to END at the
    declared `fy_max` — the half that catches a figure wrong only about its period; d3
    fails when the parquet is older than a partition it reads. All three reproduce the
    shipped defect. d1 then caught a **second, independent** defect it was not aimed at:
    the `/feed/` new-entrant citations omitted the `obligation > 0` predicate their own
    mart carries, so 394 of 1,667 published queries returned a different number than the
    figure beside them — invisible until the rebuild populated that surface. Ranking
    moved as it should: RTX #6→#4, Raytheon #4→#10 (its UEIs resolve to RTX), Pfizer and
    Centene new to the top 200 on FY2020–21 awards the stale window could not see.
    Evidence: `docs/superpowers/reviews/5c-gates-pre-failure.txt`.

    **Status: CLOSED** — swept 2026-08-24. `8011f57` (2026-08-05), matching the
    in-entry marker. Verified at HEAD: the gate 23 leg (d) script
    `entitytotals-recompute.py` exists.

34. **Eval q022's instruction contradicts its own ground truth (found by PM Sprint 3
    Task 5b; NOT fixed there, deliberately).** q022 asks for the MDA HHI and vendor-family
    count and instructs: *"Report both values as integers, exactly as the SQL returns them
    (e.g. 2068, not 2068.0)."* That wording was written when `round(hhi, 1)` happened to
    return the integral 2068. The Task 5b crosswalk rebuild moved MDA's HHI to **2118.5**,
    so the instruction now tells the analyst to truncate a genuinely fractional value: it
    answered `2118, 3319` against an expected `2118.5, 3319` and was scored wrong. This
    is the only miss in the 47/48 run — the gate passes on it — and it is an eval-wording
    defect, not an analyst failure. It was left alone in Task 5b on purpose: rewording an
    eval question inside the same change that moves the data the question measures is the
    pattern that makes an eval untrustworthy, even when the motive is innocent. Fix
    separately: the intent is "do not add or drop decimal places", so say that rather than
    "as integers", keep the `e.g. 2068, not 2068.0` example, and re-run the live eval to
    record the corrected score.

    **Status: CLOSED** — swept 2026-08-24. **This entry carried no closure
    marker of any kind before this sweep, and read as open.** Drawdown Sprint
    A, Task A4; `c7293e5` (2026-08-12). Verified at HEAD:
    `evals/phase5_questions.yaml` q022 now reads "Report both values exactly as
    the SQL returns them — do not add or drop decimal places (e.g. 2068, not
    2068.0; 2118.5, not 2118)", with `expected_answer` (2118.5, 3319),
    `answer_sql` and `tolerance` untouched — exactly the separation this entry
    asked for.

35. ✅ **FIXED 2026-08-05 (Sprint 3 round 3).** The detail-grade tier is now
    defined by the J-book DETAIL ROWS: `getDetailGradeCount()` counts the
    `program_details` sidecars that hold at least one detail row (1,739),
    cross-checked against `dim_programs.parquet`'s published row count with a
    THROW on disagreement. The corpus statement, `/coverage/`'s lead row, the
    years-matrix note and the service-books note all read it. Two sentences
    were reworded rather than re-numbered because their count was right and
    their label was wrong (`/programs/` "the 1,741 detail-grade program
    elements" and `/methodology/` "the grid's rows ARE the N programs with
    detail-grade data" — the grid renders the whole index). datatruth leg (d)
    recomputes it the same way and now also fails when the sidecars and the
    parquet disagree. Original entry:

    **The corpus says 1,741 detail-grade programs; the detail table has 1,739
    (found by PM Sprint 3 round-1 visual judging; NOT fixed there).** `/data/`
    reports `dim_programs` at 1,739 rows while the corpus statement on the same
    page — and the `/coverage/` row, and gates 1, 20 and 21 — say 1,741 carry
    detail-grade R-2/P-40 J-book data. The page explicitly invites that
    comparison ("a row count can be compared against the right denominator"), so
    the unexplained 2-row gap undercuts its own premise. Checked: the two extra
    program elements are `0603115DHA` (Medical Development, DHA) and `0708083D`
    (Assembled Chemical Weapons Alternatives, Army). Both are in `programs.json`
    — so both get pages and both are counted in the 1,741 — and both carry
    `project_count: 0` and `narrative_count: 0`, i.e. no R-2/P-40 detail at all.
    **`dim_programs` is right and the 1,741 label is two lines generous**, which
    means the site is currently overstating its own detail-grade coverage, on the
    number the new `/coverage/` page leads with. Not fixed in the fix round for
    two reasons: re-baselining the corpus number touches gates 1, 20 and 21 plus
    the `/coverage/`, `/years/`, `/programs/` and `/data/` corpus statements, and
    the alternative (stating the difference on `/data/`) requires re-running
    `export-site` to regenerate `datasets.json`, which is not something to
    trigger under a pending deploy decision. Fix separately: decide whether the
    detail-grade tier is defined by "has a program page" or "has R-2/P-40
    detail", make every surface use that one definition, and add a gate leg that
    fails when `dim_programs` and the corpus statement disagree — the current
    suite checks rendered counts against the parquet but never the parquet
    against the corpus claim.

    **Status: CLOSED** — swept 2026-08-24. `f73b637` (2026-08-05), matching the
    in-entry marker. The figures in it have since moved and the mechanism was
    rebuilt: Sprint E (#67) and Sprint F (#45) took `dim_programs` 1,739 →
    1,749 → 1,753, and `getDetailGradeCount` (`site/src/lib/data.ts:804`) no
    longer asserts sidecar-count === dim_programs row count, because E1's
    re-grain deliberately adds synthetic rows with no R-2/P-40 exhibit behind
    them.

36. **The eval gate's 100% citation-resolution bar is flaky against a
    nondeterministic agent (found by PM Sprint 3 verification).** `verify-phase5`
    FAILED on its first run of the sprint — accuracy 47/48 (threshold 44, fine),
    but citation resolution 42/43 because q011 returned the right answer through
    literal/echo SQL, leaving `touched_tables` empty. An immediate re-run of the
    same gate, same build, same data scored 47/48 accuracy and **43/43
    citation**. The historical record shows the same question flaking twice
    before (2026-07-03, two different reasons), so this is analyst-agent
    nondeterminism, not a data or site regression. The bar is right — a citation
    that does not resolve is not a citation — but a single sampled run of an LLM
    agent gated at exactly 100% will fail intermittently for reasons unrelated to
    the build, and a release process that treats that as a blocker will either
    stall or teach operators to re-run until green, which is worse. Fix
    separately: either retry the citation-recompute step for a question whose
    answer scored correct but whose SQL was a literal echo (bounded, e.g. 2
    attempts, and record that it was retried), or make the gate report
    best-of-N with the per-attempt detail persisted. Do NOT lower the threshold.

    **Status: CLOSED** — swept 2026-08-24. **This entry carried no closure
    marker of any kind before this sweep, and read as open.** Drawdown Sprint
    A, Task A5; `71fab68` (2026-08-12). Verified at HEAD:
    `resolve_citation_with_retry` at `src/govbudget/verify_phase5.py:526`,
    bounded at `max_attempts=2`, firing only when the answer already scored
    correct and the failure is exactly the empty-`touched_tables` case, with
    `citation_retry_count` and `citation_retried` persisted to the run
    artifact. The instruction "Do NOT lower the threshold" was honoured — both
    the 100% citation bar and the 44/48 accuracy bar are unchanged.

37. ✅ **FIXED 2026-08-07 AT SOURCE — the grain is the PE, and the warehouse
    now owns the rollup.** `programs.json` held one row per PE with one `org`,
    and its `trajectory` carried that org's SHARE. For 1,738 of 1,741 programs
    the declared org is the only org, so the slice IS the program and nothing
    showed; three shared BLI codes published a part as the whole (FY24→FY26,
    USD thousands): BLI 30 "Other Major Equipment" 408,006→**435,163** /
    212,900→**232,181** (OSD + DMACT 13,012 + DTRA 12,787 + DoDEA 1,358); BLI
    20 "Vehicles" 356→**2,491** / 911→**3,141**; BLI 500 "Personnel
    Administration" 105,943→**110,388** / 79,251→**83,048**. Found by gate 23
    leg e in Sprint 3 round 3; the FY26 one had been shipping since the column
    existed.

    THE GRAIN DECISION, recorded: a row is a **PE**. pe_bli is the row
    identity, the `/program/{pe_bli}/` URL, the generateStaticParams key, the
    dead-link page set and the corpus count — one page per PE, always. The
    (PE, org) alternative multiplies the index against that URL space and
    leaves the `/programs/` row and the page it links to disagreeing by
    construction. The org grain is real and STAYS, in `fct_budget_trajectory`,
    where an agency's share is an agency-grain question.

    `fct_program_trajectory` (new dbt model, grain pe_bli) is the rollup, and
    `assert_program_trajectory_component_sum` pins every metric to the sum of
    its component rows — both directions, NULL-aware, change columns included.
    Proof-can-fail: redefine the model as the primary-org pick and it FAILs 3,
    naming BLI 30/500/20 with got/want. NOT a shipped parquet: a second public
    "trajectory" table differing on 3 of 1,741 rows would be a fresh footgun.
    The exporter reads it for `programs.json`, both sidecar tiers, search
    ranking, and the summary block's slot-2 fallback — which resolved to the
    PE's PRIMARY ORG, i.e. a component card on a program page whenever the
    decade grain was absent. Citation identity collapses to the parent at one
    component (1,738 programs keep their fact ids; no number gained a second
    receipt); the three shared BLIs mint a program-scoped derived sum whose
    inputs are every component's workbook rows, so rule 4c recomputes it.

    The site KEEPS reading years_matrix's decade cells on `/programs/` and
    `/agency/{org}/` — no longer as a workaround (the fixed trajectory agrees
    to the cent on all 1,799 FY24 and 1,671 FY26 programs where both publish)
    but because the decade cell is the same FACT the linked page cites. Same
    number from two facts still gives a reader two receipts for one figure.

    Enumerated and deliberately unchanged: the agency FY2026 sum stays the
    component grain (summing program totals there would credit OSD with
    DMACT's, DTRA's and DoDEA's money). See #45 for its coverage gap.

    **Status: CLOSED — but its remedy was partly SUPERSEDED** — swept
    2026-08-24. `03eab80`, recorded by `79ebc2f` (2026-08-07), matching the
    in-entry marker: the defect (three shared BLI codes publishing a component
    as the whole) is fixed and `fct_program_trajectory` exists. What did not
    hold is the fix's premise. Sprint F (#45, `630bb0b`, 2026-08-21) found that
    BLI 20/30/500's organizations are NOT components of one program — DLA
    "Major Equipment" and DHRA "Personnel Administration" merely reuse the code
    `500` — and un-summed them: `dbt/models/marts/fct_program_trajectory.sql`
    at HEAD explicitly does not sum across organization for those three keys.
    Read the last paragraph of this entry with that in mind: the agency FY2026
    coverage gap it hands to #45 was closed by splitting the keys, not by
    leaving them summed.

38. ✅ **DONE 2026-08-06 — the escape hatch WAS conflating two exemptions, and
    the split is the fix.** `/methodology/` wrapped its entire
    `<div class="container">` in `data-source-text="methodology"`, so the
    render-static negative-currency scan and datatruth leg j both skipped the
    single page arguing for the site's rigour. Round 3 declined the obvious fix
    (wrap ~8 paragraphs, each needing its own citation anchor for the (a0)
    constraint). **What the gate code actually said:** the marker was doing
    THREE jobs — (a0) "block-cited, so no per-figure anchor, and no
    `[data-amount]` may hide inside", (b) "these dollar strings are the
    *source's*, so do not demand `<Cite>`", and leg j "this *notation* is the
    source's, not ours". Jobs (b) and leg j are FORMATTING exemptions and are
    only earned by prose that genuinely comes from somewhere else — measured:
    dropping the skip wholesale would fail ~3,650 currency tokens under
    `narrative`/`dossier-claim`/`lineage-evidence` (real J-book prose, correctly
    exempt) and 226 leg-j hits, all under `narrative`. So a blanket "sweeps stop
    honouring it" does not hold; the narrower expression is **per-VALUE
    classification**. `scripts/gates/source-text-kinds.mjs` is now the one table
    both gates read: `narrative`/`dossier-claim`/`lineage-evidence`/
    `footnote-preview` earn both formatting exemptions (verbatim source prose);
    `headline` earns the currency one only (exporter-composed sentence — its
    *notation* is ours, so leg j sweeps it, 0 new failures); an **unclassified
    value fails render-static**, so a new marker can no longer buy silence by
    existing. `methodology` is gone as a kind: the page quoted nothing, and its
    sentinel `data-xml-path="site:methodology/prose"` was a fake anchor invented
    to satisfy (a0) — one container edit removed both, no paragraph re-wrapping,
    and `[data-amount]` is now legal on the page for the first time. Its 9
    non-figure dollar tokens (thresholds, a tolerance, GAO's $186 B, the
    $7.07B/$4.92B/$4.15B worked examples) are enumerated with reasons in
    `prose-allowlist.json`, whose `pages` field — present in the JSON since day
    one and **ignored by the gate**, matching every pattern site-wide — is now
    honoured, with dead patterns and stale (matched-nothing) entries failing the
    gate. That used-entry rule doubles as the render-static non-vacuity proof
    for `/methodology/`; leg j adds a COVERAGE guard (≥90% of the page's numeric
    leaves must be reached — a bare "≥1" would have been satisfied by the site
    chrome alone, i.e. would have passed the very defect it guards). Result:
    `/methodology/` = 47 numeric leaves swept, 9 currency tokens scanned, no
    real defect surfaced once visible (round 3 had already fixed by hand the
    three these sweeps would have caught). Proof-can-fail recorded for all four
    arms.

    **Status: CLOSED** — swept 2026-08-24. `712485d` (2026-08-06), matching the
    in-entry marker. Verified at HEAD:
    `site/scripts/gates/source-text-kinds.mjs` exists.

39. ✅ **FIXED 2026-08-13 — a published, enumerated titles-override table,
    applied at every point the exporter emits a program title.**
    `Joint Hypersonic Technology Development &Transition` (PE 0603183D8Z) was
    missing the space after its ampersand, verbatim from the source workbook.
    `data-seeds/title_overrides.csv` (`pe_bli, source_title, display_title,
    reason, verified_on`) is keyed on the SOURCE title as well as the PE, so
    an upstream workbook correction silently disarms the row instead of
    rewriting a title it no longer describes. `apply_title_override()` /
    `load_title_overrides()` route through it — the fan-out was larger than
    the plan's five named surfaces: correcting `all_prog_rows`,
    `titles_by_pe` and `bl_titles` once each (rather than patching every
    dict-literal call site) covers `programs.json`, `program_details`'
    `budget_lines` rows, `search_quick.json`, `feed.json`, `years_matrix.json`,
    the /companies/ `linked_programs` list, district/filing/flows sidecars,
    and the `breakdowns/` show-your-work labels — 8 call sites across 2
    genuinely independent raw-title reads inside `_emit_breakdowns` that the
    first pass missed and a manual post-build grep caught. `workbook-cells/`
    is deliberately EXCLUDED — it quotes the cited .xlsx cell verbatim, typo
    and all, because a citation drawer has to show what the source actually
    says. A missing seed raises `FileNotFoundError` at export time (the #55
    silent-`{}` failure mode is exactly what this refuses to repeat); an
    export-time gate re-reads the built JSON surfaces and raises if any
    listed `source_title` survived uncorrected; a row that never matched
    anything in the corpus prints (not raises — a PE can legitimately drop
    out of a future budget). The override list itself is published
    (`title_overrides.json` → `/methodology/`), so the correction is visible,
    not silent. `RDT&E`, `HM&E`, `S&T`, `D&UP` and `R&D` are unaffected
    site-wide (confirmed on the built HTML) — this was never a display-time
    regex.

    **Status: CLOSED** — swept 2026-08-24. `30dee83` (2026-08-13), matching the
    in-entry marker. Verified at HEAD: `data-seeds/title_overrides.csv` exists.

40. **The mobile navigation drawer shipped as a 32px sliver on every page —
    and no gate could see it (found by round-3 visual judging, FIXED
    2026-08-05).** The panel is `absolute left-0 top-14 w-full`, written to
    position against the sticky `<header>`; the span wrapping the trigger in
    `layout.tsx` carried `relative`, so that 32px span became the containing
    block and `w-full` resolved to 32px. All nine nav links rendered 24px wide
    at x=358 in a 390 viewport, clipped to three characters, and opening the
    menu widened the document 390 → 457px. All three judges found it
    independently; two called it the single largest defect at 390. Fixed by
    dropping one word, plus a dismiss-on-click backdrop scrim. The LESSON is
    the gate gap, not the CSS: gate 3's mobile legs (m1-m3) all measure the
    page AT REST, so a defect that only exists after a click was structurally
    invisible to the suite. Leg (m4) now opens the menu and checks it — panel
    present, ≥5 links, every link inside the viewport and ≥64px wide, no label
    clipped by its own box, no document widening — with proof-can-fail
    recorded. Any future affordance that only exists in an interaction state
    needs its own leg; "the page looks fine on load" is not coverage.

    **Status: CLOSED** — swept 2026-08-24. `7fb62fa` (2026-08-05), matching the
    "FIXED 2026-08-05" in this entry's own headline. Verified at HEAD: leg (m4)
    is present in `site/scripts/gates/mobile.mjs`, so the interaction-state
    coverage this entry's LESSON demanded actually shipped.

41. **The decade trajectory chart drew a cited figure as visually zero on all
    1,741 program pages (found by round-3 visual judging, FIXED 2026-08-05).**
    The chart was min-max autoscaled with no y-axis, so the series MINIMUM
    landed exactly on the baseline rule. On `/program/ATA000/` that is the
    FY2026 request: a cited $4.09B drawn as nothing, directly above a table
    stating $4.09B and 73% of the FY24 actual. On a site whose argument is
    that its figures are exact, a figure rendered as zero while its own table
    says otherwise is the cardinal defect. Fixed by padding the plotted domain
    below the minimum and stating the scale in words beneath the chart (no
    figures in that sentence — gate 2 requires every rendered dollar amount to
    sit inside a `<Cite>`, and the extremes are already in the cited grid
    below). ✅ **Remnant CLOSED 2026-08-07:** the x-axis labelled only the
    first and last fiscal year, at 8 viewBox units, so every dot between them
    sat at an unlabelled position — on a chart whose own caption says to read
    it for direction. It is labelled at a regular step now, with a tick under
    each label, the step derived from span × plot width against a collision
    pitch (a decade gets FY15/18/20/22/24/26; a five-year program gets every
    year; a one-year program gets one and does not divide by zero). Type 8→9
    units, `#9ca3af`→`#6b7280`. `axisLabelYears` is exported and unit-tested,
    including "no two labels closer than the pitch" across every span 4–16
    years.

    **Status: CLOSED** — swept 2026-08-24. Chart fix `2a8d56a` (2026-08-05);
    x-axis remnant `b7bc916` (2026-08-07). Verified at HEAD: `axisLabelYears`
    is exported from `site/src`.

## PM-review Sprint 3 — round-3 visual judging

First panel (3 independent opus judges, both widths, ~120 screenshots each):
**390 → 2 / 2 / 3, median 2. 1440 → 4 / 3 / 4, median 4.** The desktop bar was
met; the phone bar was not, and all three judges gated the phone score on the
same defect — the nav drawer above (#40). The five commissioned fixes
(undated coverage targets, the `/programs/` basis collision, the corpus
overstatement, `/flow/` parentage, `/company/` precedence) drew no criticism
from any judge; every 390 finding was a defect the round had not been pointed
at, which is the panel doing its job.

Second panel (3 fresh independent opus judges, after those fixes):
**390 → 3 / 4 / 3, median 3. 1440 → 4 / 3 / 3, median 3.** The phone median
moved 2 → 3; the desktop median moved 4 → 3 against a different panel. The
≥4 bar was NOT met at either width by this panel — see the third panel below,
which was run after the next round of fixes and cleared it. The nav drawer, the filing truncation and
the `/companies/` fold were all confirmed fixed — no judge on the second panel
raised any of them. What the second panel raised instead is largely SYSTEMIC
rather than defect-shaped: no layout spine (#42), no reading measure, no
desktop type scale, Fact-ID chips louder than their figures (#43), and the
budget-river Sankey unencoded beside a fully colour-encoded sibling. Those are
a design pass, not a fix round, and saying otherwise would be overstating what
this round can deliver.

Third panel (3 fresh independent opus judges, after the second round of
fixes, run against the final HEAD): **390 → 4 / 4 / 4, median 4. 1440 → 4 / 4 /
4, median 4. The ≥4 bar is MET at both widths**, unanimously and without a
split. All three cited the same load-bearing strengths — the citation drawer,
the reconciliation strips, the edition-stamped `/years/` headers, the
contractor-bridge honesty — and none raised the nav drawer, the filing
truncation, the `/methodology/` text defects, the clipped mobile tables or the
`Total` contradiction, all of which had been fixed by then.

What all three still want, and what stays open (#42, #43, plus the Sankey
labelling and the caveat-before-content ordering): one content spine and one
reading measure, the Fact-ID chip made subordinate to the figure it annotates,
budget-river label collisions resolved, and the explanatory prose demoted below
the data it qualifies on five index pages. Those are a design pass and an owner
decision, not fix-round work, and the panel scored 4 with them outstanding.

Fixed after the SECOND panel: `/company/`'s "Total" column, which summed income
and expense while `/data/` documents them as "non-additive, never summed" and
the payload flags every row `nonAdditive` — the site contradicting its own data
dictionary, and the most serious finding of either panel; three run-together
words and an outdented bullet list on `/methodology/`; the two tables that
scrolled sideways at 390 with no cue while `/flow/` and `/years/` had one; the
translucent nav panel; the program-page hero decoration overflowing a 390
viewport; and the program `h1`, which was 24px at both widths.

Fixed after the FIRST panel, from the judges' convergent list: the nav drawer and
its scrim (#40); the exporter's 120-character mid-word snippet cut on
`/filing/` and the blind ellipsis on program pages (all three judges); the
`/companies/` phone fold, which put ~24 lines of caveat prose ahead of the
first company (all three); the `/company/` awards table, the one table on the
site with no mobile treatment; three home-page feed cards that truncated to
the same string; a right-edge fade on the `/flow/` Sankeys; and the decade
chart baseline (#41).

42. **No layout spine: the content column starts at five different left edges
    (found by round-3 visual judging, panel 2 — NOT fixed).** Measured `h1`
    left offsets at 1440: 96 (`/flow/`, `/years/`), 160 (`/programs/`,
    `/companies/`), 224 (nine pages), 288 (`/`, `/filing/`), 352
    (`/methodology/`) — six distinct `max-w-*` values across nineteen route
    files, against a header whose wordmark is pinned at 96. All three judges on
    the second panel named it, two put it first on their "what would move 1440
    up" list: navigating Programs → Feed → Flow slides the page sideways each
    time, and on 12 of 14 pages the title does not align with the brand.
    Deliberately NOT fixed in the fix round, because the obvious change makes
    a second reported defect worse: the same panel measured explanatory prose
    at 136-165 characters per line on `/coverage/`, `/companies/families/`,
    `/program/` and `/`, so widening those containers to align them would
    push an already-over-long measure further. The two have to be solved
    together — pick at most two container widths (wide-for-matrix aligned to
    the header at max-w-7xl, narrow-for-prose) AND cap the reading measure at
    ~70-75 characters inside the wide one. That is a design pass across every
    route, not a fix-round edit, and it wants a gate leg that measures rendered
    characters-per-line so it cannot drift back.

    **Status: CLOSED 2026-09-25** — ledger sweep; the work landed 2026-09-01.
    One content spine and one reading measure: `f02deb0c` (`.spine` on the
    header, the footer and every route; `--measure: 54ch` on prose),
    `db065c0c` (the page-header measure) and `29ab46be` (document routes), all
    2026-09-01; the `<dd>` and marker-less-list residue in `dd86f8e7` (Task 3,
    2026-09-11). The gate shipped as `site/scripts/gates/spine.mjs` (the
    drawdown plan named it `measure.mjs`), wired into gate 3 as legs (s1)/(s2)
    and runnable alone as `node site/scripts/run-spine-leg.mjs`;
    `site/scripts/gates/__tests__/spine.test.mjs` proves it can fail. The
    `max-w-*` grep the marker below uses is no longer the proxy — leg (s1)
    measures every route's rendered left edge instead.
    *(Original marker below.)*
    **Status: OPEN** — swept 2026-08-24. Assigned to drawdown Task C1 (#42 +
    #43 together); never executed, and no commit after `b87acbf` (2026-08-07,
    which filed it) references #42. Measured at HEAD: `grep -rho
    'max-w-[a-z0-9]*' site/src/app --include=page.tsx | sort -u` still returns
    ten distinct values (`2xl 3xl 4xl 5xl 6xl 7xl full md sm xl`), so no single
    spine has been imposed and the reading measure is still uncapped.

43. **Fact-ID chips are ON by default and outweigh the figures they annotate
    (found by round-3 visual judging, panel 2 — NOT fixed, needs an owner
    decision).** All three judges on the second panel reported the same thing:
    the blue monospace hash is visually louder than the dollar value beside it,
    it wraps to a second line on wider figures (giving `/programs/` an
    alternating 63/90px row rhythm), and toggling it off "proves the underlying
    table design is much better". This is NOT a defect to fix unilaterally: the
    default was set deliberately in PM Sprint 1 §P1-1 — "the site is named
    Fiscal Receipts; its receipts are not opt-in" — and flipping it reverses a
    recorded product decision. Options for the owner: keep ON but make the chip
    quieter than its figure (smaller, lower contrast, no fill); reveal on
    hover/focus; or default OFF with the dotted underline carrying the signal.
    Whichever, the figure should be the loudest thing in its own cell.

    **Status: CLOSED 2026-08-27** — the owner decided: chips stay ON, visual weight comes down. Availability (a reader can see every figure is cited) and hierarchy (the chip must not out-shout the number) were never in conflict; turning chips off would have traded a real trust property for a styling problem styling can fix. Shipped `3e87e67`/`2fbe833`/`9289bf2`: weight 700→400, chroma 210→0, opaque blue fill removed, and a dark-mode variant where none existed. `receipts-toggle.tsx:51` untouched. Gate 6 leg (e) re-asserts the pinned floors on the same elements (underline 4.96:1, dark 7.87:1, ≥12px) so "quieter" can never mean "dimmer than AA". The panel's row-rhythm complaint was measured and found FALSE — one pixel, still alternating; that is program-title wrapping, recorded rather than counted as fixed. **[ORIGINAL MARKER, for the record: OPEN — awaiting the owner decision this entry asks for.]** — swept
    2026-08-24. Assigned to drawdown Task C0 ("the Fact-ID default is the
    owner's call"); no decision is recorded anywhere in this file or the
    history. Verified at HEAD: `site/src/components/receipts-toggle.tsx:51` is
    still `useState(true)` and
    `site/src/__tests__/receipts-default.test.tsx:114` still asserts the toggle
    is "pressed by default" — the PM Sprint 1 §P1-1 decision stands, unreversed
    and unmodified.

44. ✅ **FIXED 2026-08-07 — every feed headline figure now clicks through to
    its source.** `data-source-text="headline"` earned the currency-scan
    exemption, and its own `why` said so as a KNOWN GAP: the sentence was
    composed by the export pipeline as one string (`"… first award FY2025,
    $3.1M total"`), so its dollar tokens could not carry per-token anchors and
    were the only site-computed currency figures reaching a reader with no
    citation affordance — on the syndication surface, the most-forwarded,
    least-context view the site has. Before #38 it was invisible; #38 named it.

    **40 tokens** on the live corpus (25 `new_entrant`, 15
    `request_vs_actuals_gap`; `yoy_swing` and `concentration_shift` headlines
    print a percentage and an index, not money). **Every receipt already
    existed** — all 40 matched a fact id already on the card, so nothing was
    minted. The exporter emits `headline_segments` (text runs + `{amount,
    fact_id}`) and `<FeedHeadline>` renders the amount runs through
    `<ProseCite>`. Two invariants: the segments re-join to the flat `headline`
    exactly (it still ships in RSS/Atom/JSON and to search), and a dollar
    figure enters a headline ONLY with a receipt — where the fact does not
    resolve the money clause is dropped rather than printed uncitable.

    Gate flip: `headline` → `quotedFigures: false` (it now earns NEITHER
    formatting exemption; it stays classified because (a0) — no nested
    `[data-amount]` — is exactly what forces per-token anchors). One enabling
    change, and it is a strengthening: leg (b) accepts `[data-prose-cite]` as
    an anchor, which (a1) forces to RESOLVE, where a bare `[data-amount]` need
    carry no fact at all. New leg **(a2)** binds render to exporter both ways —
    segments re-join, every flat-headline currency token is covered by an
    amount segment (the non-vacuity arm), every amount segment resolves, and
    `/feed/` renders exactly as many headline prose cites as the sidecar
    declares. Suite stays 24 gates.

    **Status: CLOSED** — swept 2026-08-24. `03eab80` (2026-08-07), matching the
    in-entry marker. Verified at HEAD: `src/govbudget/export_site.py` emits
    `headline_segments`.

45. **The agency FY2026 sum's coverage gap (enumerated by #37, deliberately
    not closed there).** `agencies.json`'s `fy2026_total_thousands` is the
    COMPONENT grain by design — an agency total is an agency-grain question,
    and summing program totals would credit OSD with DMACT's, DTRA's and
    DoDEA's money. But it iterates `dim_programs`, which carries ONE org per
    PE, so a shared BLI's components under a different org are absent from
    that org's page entirely: DCSA is missing BLI 20's 2,230, DMACT BLI 30's
    7,258, DTRA BLI 30's 12,023, DHRA BLI 500's 3,797 — $25.3M across four
    agencies. It is not a wrong number (those pages do not list the PE either,
    so the total is consistent with what they show) but it is an
    under-statement with no note. Closing it means giving `dim_programs` a
    per-org grain — a dimension change, not an aggregate fix — and would move
    which agency page lists a shared BLI. Written down at the call site in
    `export_site.py` in the meantime.

    **Status: CLOSED** — swept 2026-08-24. **This entry carried no in-entry
    marker before this sweep; its closure was recorded only in a blockquote
    roughly 110 lines below it.** Sprint F; `630bb0b` (2026-08-21). The fix was
    not the dimension change this entry priced — the slug keys on organization
    (`{pe_bli}-{ORGANIZATION}`) instead: `dim_programs` 1,749 → 1,753,
    key-collision exclusions 11 → 4. Verified at HEAD: `is_org_split` is
    present under `src/govbudget/`.

46. **[NO ENTRY WAS EVER FILED. Ledger-gap note added 2026-08-24 — this is a
    reconstruction, not a contemporaneous record.]** The number was allocated by
    the backlog-drawdown plan
    (`docs/superpowers/plans/2026-08-07-backlog-drawdown.md`, Task A2:
    "`CURRENCY_RE` cannot see trillions (new entry — file as #46)", whose own
    file list says "Modify: `docs/superpowers/ROADMAP.md` (add #46, closed in the
    same commit)"). The work shipped; the ROADMAP edit did not, so the numbering
    has skipped 46 ever since. Per `c7293e5` (2026-08-12): the sweep was not
    blind to trillions — it fired but truncated the token ("$1.2T" reported as
    "$1.2"); the real breakage was `prose-allowlist.mjs:90` rejecting a `$T`
    entry as an illegal pattern, so a legitimate trillions figure could never be
    allowlisted. Both regexes gained `T`, pinned together by a test.

    **Status: CLOSED** — swept 2026-08-24. `c7293e5` (2026-08-12), drawdown
    Sprint A Task A2. Verified at HEAD:
    `site/scripts/gates/__tests__/currency-re.test.mjs` exists. The defect
    description above was reconstructed on 2026-08-24 from the plan and the
    commit message — no one wrote it down here at the time.

**#47–#53 (filed 2026-08-07, an independent multi-persona review): a true,
correctly-cited figure wearing a false label.** Every one of the six passes
every existing gate, because those gates check number↔citation and nothing
checks claim↔citation. Sprint A′ (`docs/superpowers/plans/
2026-08-07-sprint-a-prime-claim-citation.md`) closes all six and adds the
gate family that makes the class visible.

*Correction 2026-08-24 (found by the status sweep; the paragraph above and the
blockquote below are left as written).* **"Six" is wrong — #47 through #53
inclusive is SEVEN entries**, and all seven were filed by `0abc8c3` in one
commit, and all seven were fixed: `7f0d42a` (#47), `2d95516` (#48), `376a061` +
`a387077` (#49), `2201d6e` + `756620b` (#50), `7bebd7b` (#51), `9070d11` (#52),
`99439bd` (#53). The sprint's own process note two paragraphs down says "Every
one of the **seven** tasks", so the count is inconsistent inside this same
block. No entry was dropped or double-counted; only the word is wrong. Recorded
rather than silently rewritten, per this file's supersede-not-delete rule.

> **✅ ALL SIX CLOSED 2026-08-08** on branch `sprint-a-prime-claim-citation`
> (20 commits, HEAD `b41ddaa`). Verified at final HEAD: **24/24 gates PASS**,
> 1,551 pytest, 949 vitest, `tsc` clean, 0 eslint errors, `verify-lineage` PASS
> (6 legs), `verify-phase5b3` PASS (50/50 dossiers), eval 47/48 · citations
> 43/43 (the one miss is q022, a pre-existing eval-wording defect owned by the
> backlog-drawdown plan's Task A4, not by this sprint). Citation parity
> json↔parquet 110,875 == 110,875. **Not deployed** — deploy is the
> controller's call.
>
> **New gate legs, all attached to existing gates so the suite stays 24:**
> gate 2 leg (t) request-vs-enacted vocabulary · gate 2 leg (cc) dollar
> denominators · gate 23 leg (f) exhibit agreement · gate 23 leg (g)
> reconciliation split · gate 9 leg (e) district no-double-count ·
> `verify-lineage` leg (f) no-retraction · dbt `assert_district_totals_no_double_count`,
> `assert_district_totals_grain_unique`, `assert_program_mentions_evidence` ·
> regression tests `test_citation_parity.py`, `test_export_site_dossier_filter.py`.
>
> **What each fix cost in published numbers** — see the corrections table on
> `/methodology/`: district linkable $8.01B → $5.58B; lobbying mentions
> 34,538 → 10,447; `/programs/` counter → $228.5B of $385.3B (59.3%); stated
> lineage edges 31 → 29; FY2026 figures gained a discretionary/reconciliation
> split; the R-1 basis chip corrected on 1,077 of 1,741 programs.
>
> **Not closed by this sprint, filed as #54 and #55:** #50's label reaches
> `/program/*` only, and Lockheed still lacks the F-35 pending alias curation.
>
> **Process note for the next sprint.** Every one of the seven tasks found a
> defect in the plan's *prescribed code* — a regex matching its own prescribed
> fix, a gate letter colliding with a live leg, units off 1000×, a
> grain-mismatched fail-proof, a prescribed file needing no change, a
> misattributed page-weight regression, and a negation window that would have
> deleted a legitimate edge. The plan's *measured figures* held up every time,
> because they were reproduced against the warehouse. The code was never
> executed before being written down. Write plans accordingly.

> **Owner decision, 2026-08-07 (#49, #51, #52):** where a published figure is currently
> large and false, publish the smaller true one. District linkable dollars fall
> $8.01B → $5.58B; the lobbying mention count falls by whatever the evidence rule
> removes. These are corrections, and they ship labelled as corrections.

47. **Homepage calls the FY2026 request "enacted".** `site/src/app/page.tsx:291-292`
    reads "between FY2025 and FY2026 enacted"; `/methodology/`, `/years/` (FY26R)
    and every program page say request. The source workbook has no FY2026
    enacted column.

    **Status: CLOSED** — swept 2026-08-24. No in-entry marker before this
    sweep; closure was recorded only in the `#47–#53` blockquote above. Sprint
    A′; `7f0d42a` (2026-08-07), with gate 2 leg (t) added so the vocabulary
    cannot drift back. Verified at HEAD: `site/src/app/page.tsx:308` reads
    "between FY2025 enacted and the FY2026 request" — both labels true. (The
    line number in this entry is now stale; the text moved.)

48. **The basis chip says "P-1 TOA" on R-1 lines.** `site/src/lib/basis.ts:12`
    hardcodes one label; `programs.json.exhibit_family` is rdte=1077 /
    procurement=664, so 1,077 of 1,741 (62%) are mislabelled. The correct
    value already ships.

    **Status: CLOSED** — swept 2026-08-24. No in-entry marker before this
    sweep; closure recorded in the `#47–#53` blockquote above. Sprint A′;
    `2d95516` (2026-08-07). Verified at HEAD: `site/src/lib/basis.ts` sets
    `BASIS_LABEL.toa` to the honest both-exhibits form `"P-1/R-1 TOA"`, with
    `basisChipForExhibit` resolving rdte → "R-1 TOA" and procurement → "P-1
    TOA" wherever the call site can prove the row's exhibit.

49. **`/programs/` publishes a row counter over a 59.3%-complete dollar
    universe.** Columns sum to $228.46B against the site's own $385.3B
    FY2026 universe. Largest omissions: 9999999999 Classified $73.90B, 2013
    Virginia Class $11.08B, 1045 COLUMBIA $10.92B. The stated exclusion
    ("not covered by the R-1/P-1 rollups") is false — COLUMBIA is a P-1 line
    and its own page says so.

    **Status: CLOSED** — swept 2026-08-24. No in-entry marker before this
    sweep; closure recorded in the `#47–#53` blockquote above. Sprint A′;
    `376a061` (2026-08-07) plus `a387077` (2026-08-08). Verified at HEAD:
    `export_site.py` emits enumerated exclusions with a `key_collision` reason
    and a quantified subtotal. The coverage figure has moved on since — 58.0% →
    59.4% via #67, and the exclusion count 17 → 11 → 4 via #67 and #45.

50. **One-time reconciliation money is folded into every FY2026 "Request"
    figure.** `fy_2026_total` $385.27B = disc $296.26B + reconciliation
    $89.01B. Against `fy_2025_enacted` $321.88B the headline basis reads
    +19.7% and the discretionary basis reads −8.0%. Long Range Kill Chains
    headlines +3052.9% on $1,916k of discretionary.

    **Status: CLOSED** — swept 2026-08-24. No in-entry marker before this
    sweep; closure recorded in the `#47–#53` blockquote above. Sprint A′;
    `2201d6e` plus `756620b` (2026-08-08), gate 23 leg (g). Verified at HEAD:
    `Fy26SplitNote` is rendered from `site/src/components/program-figures.tsx`.
    Scope was `/program/*` only until #54 widened it to `/feed/`, `/years/` and
    the explorer.

51. **District totals add one award once per matched program element.**
    `fct_district_programs` joins on `award_id_piid` only, never `pe_bli`,
    and the exporter sums those rows. Published $8.0111B vs $5.5787B
    award-distinct = 43.6% inflation ($2.432B). AK-00 publishes $1.05B from
    one $209.3M award (5.0×).

    **Status: CLOSED** — swept 2026-08-24. No in-entry marker before this
    sweep; closure recorded in the `#47–#53` blockquote above. Sprint A′;
    `7bebd7b` (2026-08-08), with gate 9 leg (e) and
    `assert_district_totals_no_double_count`. Verified at HEAD:
    `dbt/models/marts/fct_district_programs.sql:20` now joins on `select
    distinct award_piid, pe_bli, ...`. Published figure fell $8.01B → $5.58B,
    labelled as a correction.

52. **"Program elements named in lobbying filings" are single-common-word
    matches.** `mentions.py` emits a row on ONE title token ≥5 chars; the
    `GENERIC_WORDS` stoplist misses BASED, SERVICES (it lists singular
    SERVICE), ACQUISITION, ACTIVITIES, CHEMICAL. Aggregates (34,538
    sitewide) carry no caveat.

    **Status: CLOSED** — swept 2026-08-24. No in-entry marker before this
    sweep; closure recorded in the `#47–#53` blockquote above. Sprint A′;
    `9070d11` (2026-08-08). Verified at HEAD:
    `src/govbudget/influence/mentions.py` now emits three evidence tiers
    (`pe_literal`, `alias`, `multi_token` requiring ≥2 distinct non-generic
    tokens) and `GENERIC_WORDS` (line 80) includes ACQUISITION, ACTIVITIES,
    BASED and CHEMICAL. Published aggregate fell 34,538 → 10,447; #55's
    alias-loader fix later took it to 10,560.

53. **A "Stated · cited" lineage edge is built from a sentence that
    retracts it.** `/program/1203154SF/` asserts realigned → 1203609SF from
    "was erroneously transferred"; both edges share one page-level
    `fact_id` `10a4acbaa3270c74`.

    **Status: CLOSED** — swept 2026-08-24. No in-entry marker before this
    sweep; closure recorded in the `#47–#53` blockquote above. Sprint A′;
    `99439bd` (2026-08-08). Verified at HEAD: `no_retraction_leg` at
    `src/govbudget/verify_lineage.py:780` is `verify-lineage` leg (f), and
    `src/govbudget/lineage/extract.py:154` implements the self-retraction test.
    Stated edges fell 31 → 29.

54. **#50's reconciliation label stops at the program page.** Sprint A′ split
    discretionary from one-time reconciliation money and labelled it on
    `/program/*` (gate 23 leg (g) enforces it there). The **combined** FY25→FY26
    percentage still renders unlabelled on `/years/`, `/feed/`, and
    `explorer.tsx`'s canned SQL — so the same +3052.9% that is now explained on
    Long Range Kill Chains' own page is still bare on three other surfaces.
    Deliberately scoped out of A′4 rather than expanded mid-task; filed so #50
    is not read as fully closed. The fix is to widen leg (g) past `/program/*`
    once those surfaces carry the split.

    **Status: CLOSED** — swept 2026-08-24. No in-entry marker before this
    sweep; closure recorded in a blockquote below. `cb7db2d`, recorded by
    `de3e65c` (both 2026-08-19) — that blockquote dates it 2026-08-14, five
    days before the commits that did the work. Verified at HEAD:
    `Fy26SplitNote` is imported by `site/src/app/feed/page.tsx` and
    `site/src/components/years-matrix.tsx`, so the split now reaches the three
    surfaces this entry named.

55. **`/company/lockheed-martin/` is honest but still incomplete.** #52 cut
    Lockheed's mention rows 1,296 → 366 by removing single-common-word matches,
    but the F-35 was absent before the fix and remains absent after: the
    matcher never had evidence for it, and removing false positives cannot
    manufacture a true one. The gap is alias curation —
    `dbt/seeds/program_aliases.csv` needs entries (F-35, JSF → ATA000, and the
    equivalents for RTX's and Boeing's flagship lines) so `evidence_kind='alias'`
    can carry programs whose titles share no two distinctive tokens with how
    lobbyists actually write them.

    *Correction 2026-08-08 (found by the post-merge code review; the first
    version of this entry had the cause wrong).* I originally wrote that
    `alias` matching zero rows was "a data-curation gap, not a code gap". It
    was a **code gap**: `mentions.py`'s `_SEED_PATH` used `parents[4]`, which
    resolves one level above the project, so `_load_aliases` hit its
    `exists()` guard and silently returned `{}` on every call — all 11
    curated aliases were dead. Harmless while `alias` was one signal among
    several; load-bearing the moment #52 made it a tier that qualifies a
    mention on its own. Fixed to `parents[3]`; `alias` now matches **53**
    rows (THAAD, Aegis, JASSM, GBI, C2BMC, SBX, MQ-9, CV-22, JADC2, C-130J,
    Iron Dome), taking the corpus from 10,447 to **10,500**.

    ✅ **CLOSED 2026-08-08.** F-35 → ATA000 and JSF → ATA000 added to the
    seed. ATA000 went **0 → 60** mention rows, Lockheed 366 → 425, the alias
    tier 53 → 113, and the corpus 10,500 → **10,560**. Lockheed's flagship
    program now appears on its own page, which was this entry's whole point.
    Equivalent aliases for RTX's and Boeing's flagship lines are the same
    shape of work and are NOT done — re-file if they matter.

    **Status: CLOSED 2026-09-25** — ledger sweep; the remainder landed
    2026-08-27. The owner ratified the thirteen flagship terms and the seed
    took them: `c6270fc9` (seed, gated by basis leg j) and `1edbfcc0` (the
    ratification), both 2026-08-27 — RATIFIED_ALIASES 42 → 53, with Patriot,
    PAC-3 and the other refusals recorded in `DROPPED_ALIASES`. What it bought,
    measured read-only 2026-09-25 over `fct_program_lobbying` (256 alias-tier
    rows corpus-wide): Boeing's clients now carry **10** alias-tier rows, all
    `F-15EX` (on `F015EX` and `0207146F`); RTX's clients carry none from the
    newly seeded terms — their only alias-tier rows are 10 `F-35` rows on
    `ATA000` (client "RAYTHEON TECHNOLOGIES CORPORATION"), from the 2026-08-12
    seed — because no RTX-client filing yields an alias-tier row from any
    newly seeded RTX term (`1edbfcc0`: nine of the eleven newly seeded terms
    match zero filings). That is a corpus limit, not a curation gap. A
    separate, live gap on `/company/rtx/` is filed as **#142**. The
    "deliberately not done" remainder below is superseded.
    *(Original marker below.)*
    **Status: CLOSED (core) with a named, deliberately-not-done remainder** —
    swept 2026-08-24. The loader bug and the F-35/JSF seed entries are
    `9aa3a80` and `c7293e5`, both 2026-08-12 — this entry's "Correction
    2026-08-08" and "CLOSED 2026-08-08" are both four days early. Verified at
    HEAD: `F-35` is present in `dbt/seeds/program_aliases.csv`. The RTX/Boeing
    remainder was investigated on 2026-08-21 (`548e1d9`) and ruled owner
    curation work rather than engineering — see the last blockquote in this
    section; the loader (this entry's actual bug) is fixed, the seed is the
    gap.

> **✅ #56–#59 CLOSED 2026-08-08** on branch `sprint-b-prime-remaining-review`.
> **#56** six fused pages de-fused (3010 $2.62B → $20.9M and five more), dbt
> `assert_program_key_unique` at `(pe_bli, amount_type)` grain — 1045 COLUMBIA
> correctly excluded as a cross-edition migration, 9999999999 excluded by name —
> plus gate 23 legs (h1–h4). **#57** DOJ/FTC bands replace "near-monopoly" from a
> single shared `hhi-band.mjs`; gate 8 leg (l) checks all 84 cards against the
> band their destination page renders — 70 diverge legitimately and now disclose
> it, 0 silent contradictions. **#58** masthead: publisher, unfunded status,
> contact and CC0 visible on `/about/` and in the footer. **#59** gate 23 leg (i):
> the reconciliation disclosure program pages already carried now renders on the
> four agency rollups that need it.
>
> **Two review claims were falsified during this sprint and are recorded rather
> than inherited.** Agency headers *do* equal the sum of their rows exactly
> (FY2024 and FY2026, every agency) — the live gap was only that program-page
> reconciliation disclosure never reached the rollups. And `1045` is COLUMBIA
> Class Submarine migrating accounts between editions, not a collision; splitting
> it would have torn one real program in two.
>
> **Two of my own figures were also wrong and were corrected by measurement.** The
> FY24 reconciliation gap is **139 programs / $7.99B**, not 142 / $11.06B — the
> larger figure came from treating two synthesized trajectory-only programs'
> `None` as `$0`. And `#56`'s first fix reported "corpus count unchanged" as a
> success when it was the symptom: keeping one program per key silently dropped
> **$5.74B**, including Tomahawk, LPD Flight II and Medium Landing Ship. Those 17
> lines totalling $5.82B are now named on `/programs/` with their own
> `key_collision` reason, and gate 23 leg (h4) makes a silent drop impossible.
>
> **Filed, not closed:** actually *splitting* the collided keys into their own
> pages is estimated at 5–9 days, dominated by `fct_decade_series` (the collision
> spans PB2024/PB2025 too, and there is no pre-PB2026 anchor to pick a primary
> account consistently). A 2–3 day middle path — split the money/title/URL layer
> and ship the new pages with an honest "no decade history yet" gap — is the
> cheaper option if Tomahawk on the site is worth more than a complete sparkline.

> **✅ #4, #13, #26 CLOSED 2026-08-08 (drawdown Sprint A, Task A1).** Verified,
> not asserted:
> **#4** superseded by Phase 5E — `fct_budget_lines` carries all ten editions
> PB2017–PB2026, where #4 asked only for PB2025/PB2024.
> **#13** moot — every ingested era embeds structured `.zzz` XML, so extraction
> is deterministic and no OCR path was needed. The **anchored** grep
> (`grep -rniE "\bocr\b|mistral|document.?ai" src/govbudget/ | grep -v test`)
> returns **0**; the drawdown plan's unanchored version returns 14 false
> positives because `ocr` matches So**cr**ata. If a future source lacks XML this
> returns as a new entry naming that source.
> **#26** contingent-not-applicable — the feed's event types are exactly
> `concentration_shift`, `new_entrant`, `request_vs_actuals_gap`, `yoy_swing`;
> no request-vs-request type exists, so the dead-PE `request_vs_request` fact
> has nothing to serve. Re-open with the event type that needs it.
>
> **#6 stays OPEN** — its two mart sub-items are done, but `dim_geography` is
> still `[pop_state, pop_district, transaction_count, total_obligation]` with no
> `fiscal_year`/`pe_bli` breakdown. Closing it would be the false-completion
> this ledger keeps catching elsewhere.

> **✅ #60–#66 CLOSED 2026-08-14 (Sprint C — usability).** None of these was a
> correctness defect; the site said nothing untrue going in. They were
> reachability and comprehension gaps.
> **#60** `/glossary/` ships — 14 terms, one shared `GLOSSARY` map, and TOA is
> finally expanded ("total obligational authority" went from **0** occurrences
> sitewide to defined-and-linked) after being stamped on ~80,000 figures.
> **#61** `/fact/{id}/` no longer 404s — the rewrite was `/fact/:id` only, and
> Vercel's edge matched it more strictly than `path-to-regexp` does locally, so
> the trailing-slash form the rest of the site trains never fired. Gate 1 leg
> (f1) pins the second rule. Config-shape only — it can only be *proved* on
> deploy, and that is stated in the leg.
> **#62** `/agency/` index — 23 agencies, every figure cited, footer-linked.
> **#63** CSV exports carry `fy2024_fact_id`, `fy2026_fact_id` and both
> permalinks; the provenance chain survives entry into a spreadsheet.
> **#64** `/years/` has a chart. It plots a **balanced panel** — the 524 of 1,741
> programs reporting in all 12 years — because a naive full-corpus sum shows
> spending sextupling FY2015→FY2026, which is corpus-ingestion coverage (35% →
> 90%), not budget movement. The chart says so in its own accessible name and
> description. A chart is a claim; that one would have been dramatic and false.
> **#65** the 768–1023px horizontal overflow is gone — `container` clamped to
> 768 at exactly the breakpoint the nav switched on. Measured +167/+101/+51px
> before, 0 after, at six widths on two pages. Gate 3 leg (m5) covers the band.
> **#66** dark mode via `prefers-color-scheme`, one token vocabulary. Gate 6 leg
> (d) re-runs axe in a real dark Playwright context — and caught a genuine
> 2.48:1 contrast failure on its first run, which was fixed rather than waived.
>
> **Also fixed, unplanned:** every `measured` string in `PAGE_WEIGHT_BUDGET` had
> gone stale — `/programs/` recorded 261,871 while shipping 277,357, telling a
> reader there was 6% headroom where there was 0.2%. All 14 refreshed, and gate 1
> now emits a near-ceiling note at 90% so the record cannot rot unnoticed again.
> Eleven pages are at or above 90% today. `/coverage/` was re-baselined
> (16,500 → 17,700 gzip) for the sitewide glossary link after drifting to **nine
> bytes** of headroom.
>
> **Two prescriptions in this sprint did not survive inspection**, continuing the
> pattern: the plan said #61 needed a resolver fix (the resolver was already
> correct — its regex ended `\/?$`), and said the review's overflow numbers
> needed confirming (they were exactly right, the first prescribed table this
> whole effort that needed no correction).

> **✅ #54 CLOSED 2026-08-14.** The entry was filed too gently. It said the
> combined FY25→FY26 percentage "renders unlabelled" on `/years/`, `/feed/` and
> the explorer. Measured: **31 of 99 `yoy_swing` feed cards** are for PEs
> carrying reconciliation money, **27 of those differ by more than 20
> percentage points** from the discretionary basis, and at least four asserted a
> direction the like-for-like basis reverses —
> `1203154SF` "increased 3053%" against **−99.2%** discretionary,
> `0603342D8Z` "increased 231%" against **−100.0%**,
> `0604028N` "increased 168%" against **−90.8%**,
> `0603183D8Z` "increased 1043%" against **−10.4%**.
> Not an unlabelled figure: a true, correctly-cited number carrying a
> directionally false claim, the same species four sprints removed elsewhere.
>
> `/feed/` cards now carry the split beneath the unchanged headline, reusing
> `Fy26SplitNote` verbatim so both surfaces say it identically. `/years/` gained
> a column-level legend shown only while `%Δ` is visible. The explorer's
> "Biggest movers" query now surfaces `discretionary_pct_change` and
> `has_reconciliation` alongside the combined rate — and an incidental
> pre-existing bug was found in the same SELECT: it referenced a column `org`
> that does not exist on `fct_budget_trajectory` (it is `organization`), so that
> canned query could never have run. Gate 23 leg (g) widened to (g4a/g4b),
> non-vacuous at ≥20 of the 31 qualifying cards.

- **#68** `test_covers_live_top50_exactly` is intermittently red in full-suite
  runs. Observed 2026-08-21: FAILED once, then PASSED twice, on an unchanged
  working tree, and PASSES in isolation. Two agents diagnosed it confidently and
  differently — E1 called it "a stale DuckDB lock from my own verification
  script", E2 called it "a pre-existing E1 gap (dossier top-50 CSV not
  regenerated)". **Neither is established.** Holding a concurrent read-only
  DuckDB connection open does NOT reproduce it, so the lock theory is not
  supported either. The test compares `top50(LIVE_DUCKDB)` against the committed
  `data-seeds/program_categories.csv`; `top50()` keys by `pe_bli`, which after
  Sprint E's `(account, pe_bli)` re-grain can have two rows per key, so a
  collision-overwrite is the plausible mechanism — but plausible is exactly what
  the other two diagnoses were. Reproduce it before fixing it. Filed rather than
  guessed at a third time.

  **Status: CLOSED 2026-09-25** — ledger sweep; the fix landed 2026-08-21.
  Reproduced read-only by the 2026-09-10 roadmap audit:
  `fct_budget_trajectory` is a dbt VIEW whose unordered output varies per
  run, so `top50()`'s pre-E3 `(pe_bli, organization)` dict key was
  last-writer-wins on a split code — 200 simulated runs produced 2 distinct
  top-50 sets (188 vs 12). Fixed by `7b576db8` (Sprint E3, the
  account-qualified join) + `07f05091` (the NULL-account fallback), both
  2026-08-21; the seed re-synced in `ff846674` (2026-08-21) and `8aa14eeb`
  (2026-08-29). `test_covers_live_top50_exactly` and `TestTop50AccountJoin`
  pass at `71d3e053` against the chain C run 4 lake (3 passed, run
  2026-09-25). The marker below ("no commit since claims a fix") was written
  after `7b576db8`'s own body had named this entry's likely root cause and
  fixed `top50()`'s key.
  *(Original marker below.)*
  **Status: OPEN — and deliberately undiagnosed** — swept 2026-08-24. Filed by
  `b34d469` (2026-08-21); no commit since claims a fix, and the entry's own
  instruction ("Reproduce it before fixing it") has not been carried out. The
  `(account, pe_bli)` re-grain it names as the plausible mechanism is Sprint E
  (`a8cc403`, 2026-08-20); Sprint F (`630bb0b`, 2026-08-21) added organization
  to the same identity, which widens rather than removes the collision surface
  this entry suspects.

> **✅ #69 CLOSED 2026-08-24 (the BUDGET-ACTIVITY shape — and the one that
> was NOT a key collision).** Filed as "two budget-line keys carry two
> distinct titles each, the same defect species as #45/#56/#67 on a third
> axis: title." **The symptom was real and the species was wrong**, and
> tracing it before designing the fix is what changed the answer.
>
> `HCMC00` published $383,072K under the title **"HC/MC-130 Post Prod"** —
> which is the **$17,986K** half of it. `JSE000` published $46,509K titled
> "Joint Simulation Environment Post Production Support" — the $28,524K
> line. The framing said each page carries "ONE line's NAME and TWO lines'
> MONEY". The name half is exactly right. **The money half is not: the sums
> are correct.** The two lines under each key differ by BUDGET ACTIVITY, not
> by program. HCMC00 is BA-05 "Modification of inservice aircraft"
> ($365,086K) plus BA-07 "Aircraft support equipment and facilities"
> ($17,986K); JSE000 is BA-01 "Combat aircraft" plus the same BA-07. Thirteen
> PB2026 keys span >1 budget activity inside one (account, organization), and
> **eleven of them carry an identical title in every activity** — F-15EX in
> BA-01/05/07 ($2,480,818K + $286,700K + $246,876K = the $3,014,394K the site
> already publishes), B-52, C-17A, F-15, KC-46A, and six RDT&E PEs. The site
> has always summed those, correctly: that sum IS the program's FY2026
> procurement. HCMC00 and JSE000 differ from their eleven siblings in exactly
> one respect — the Air Force gave the BA-07 sub-line its own label.
>
> **Two independent checks killed the title axis.** (1) In the PB2024 and
> PB2025 editions the very same HCMC00 BA-07 line is titled "HC/MC-130
> Modifications", identical to its BA-05 sibling — so a title-keyed identity
> would make the program one page in two editions and two pages in the third,
> and could not attribute the earlier editions' BA-07 money to either. (2)
> `programs_excluded.json`'s `key_collision` flag, cited in #45's close as
> corroboration that these lines were "correctly out of scope", is **computed
> from the title difference itself** (`len(_by_title) < 2: continue`), so it
> was never independent evidence — and B-52/F-15EX, structurally identical,
> appear nowhere in that file.
>
> **The cause is one line of SQL.** `dim_programs.sql`'s `matched` CTE
> resolved the page title with `max(b.title)` — a LEXICAL pick over whatever
> titles the slot carries. 'P' sorts after 'M', so "Post Prod" won HCMC00.
> The same `max()` the model's own #56 comment already describes ("purely by
> max()'s lexical accident; nothing pinned the title to the money"), one
> dimension over. Replaced with a money-anchored pick (largest fy_2026_total
> line, title-ascending tiebreak — general, no key list): **1 of 1,753 titles
> moves**, HCMC00 "HC/MC-130 Post Prod" → "HC/MC-130 Modifications".
>
> **The fix is disclosure, not separation** — splitting on title would
> fragment one program on an axis eleven siblings share. Program pages whose
> FY2026 lines carry >1 title now ship `fy26_split.lines`: every constituent
> line, its budget activity, and its own workbook fact_id, rendered as
> `Fy26LinesNote` beneath the headline (2 pages today). **No published dollar
> figure changed.**
>
> **A second, louder falsehood surfaced while tracing.** All four of these
> lines were listed in `programs_excluded.json` as "absent from the index
> because their pe_bli is already a different program's page" — $429,581K,
> which is **exactly** HCMC00's $383,072K plus JSE000's $46,509K, i.e. the two
> pages' own published totals. The site was publishing that money and
> declaring it absent, in the same build. `key_collision` exclusions 4 → **0**;
> `programs_excluded.json` 196 → 192 rows; citations 110,960 → **110,959** (the
> retired `key_collision_subtotal` derived fact). Coverage is unmoved at
> **59.4%** — the index total never contained the error.
>
> **One regression caught in the same change.** The only link to
> `programs_excluded.json` anywhere on the site lived INSIDE
> `{coverage.key_collision_count > 0 && …}`. Taking the count to zero would
> have silently unlinked the completeness manifest for the remaining 192
> excluded lines — the exact artifact gate 23 leg (h4) checks. The link is now
> unconditional.
>
> **Gate 23 leg (h) gained h5, and (h4) gained its converse — still 24
> gates.** h5a: a page whose own fy_2026_total lines carry >1 title must ship
> a complete, cited `fy26_split.lines` summing to the page total. h5b: a page's
> title must be the LARGEST of its constituents — no page named after a
> minority of its own money. h4's new leg asserts the converse of what it
> already proved: nothing declared absent from the index may in fact be
> published by it. Both fail verbatim against the pre-fix artifact
> (`docs/superpowers/reviews/5c-gates-pre-failure.txt`).
>
> **Two things found on /methodology/ while shipping the correction row.**
> The page had drifted to **SIX bytes** of gzip headroom (127,800 / 34,494
> against 128,000 / 34,500) BEFORE this row — the identical cliff /coverage/
> hit at nine bytes and /programs/ at 643, and the near-ceiling note has been
> reporting it at 99.9% without anyone re-baselining. Ceilings raised to
> 136,500 / 36,900 (~6% headroom, the /programs/ Sprint E rule), stated
> rather than quietly nudged; the correction was not written short to fit a
> budget. And the corrections section was headed "Corrections issued
> 2026-08-08" while already carrying 2026-08-21 rows — now "2026-08-08
> onward", with the intro saying later corrections are appended to the same
> table.
>
> **Filed as #69, not #68 as the brief numbered it** — #68 above is the open
> `test_covers_live_top50_exactly` flake, still open and untouched here.
>
> 24/24 gates, `pytest` 1,577 passed, vitest 1,007 passed / 60 files, `tsc`
> clean. No published dollar figure moved.

> **✅ #67 CLOSED 2026-08-21 (Sprint E — the key split).** Each (account,
> pe_bli) pair now has its own page. **10 programs worth $5.35B** that were
> correct-but-absent are on the site — `/program/3010-SCN/` renders LPD Flight
> II at $2,600,000K, `/program/3050-SCN/` Medium Landing Ship at $1,963,941K —
> and all six previously-live bare URLs resolve as disambiguation stubs.
> `/programs/` coverage 58.0% → **59.4%**; key-collision exclusions 17 → 11.
> dim_programs 1,739 → 1,749; program URLs 2,009. Gate 23 leg (h), written by
> B′1 to catch the fusion, now proves the split: no page aggregates figures
> from more than one account.
>
> **The 5–9 day estimate this was sold on rested on a premise that failed.**
> B′1 priced it as "dominated by fct_decade_series (2–4 days, high
> uncertainty)" because the collision "is not confined to PB2026" and there is
> "no dim_programs-equivalent anchor for older editions". The keys do not exist
> before PB2024 at all — era editions namespace Navy procurement as
> `1810N-NAVY-L1`, so a bare numeric key is absent by construction. Three
> editions, all anchored.
>
> **Four defects were introduced during the sprint and caught before shipping,
> every one the same shape — a layer that keyed by `pe_bli` because, before the
> split, `pe_bli` WAS the identity:**
> `fct_program_trajectory` would have re-summed the halves (E1);
> `top50()` keyed on an account that is NULL for 199 of 1,749 dim_programs
> rows, silently dropping the F-35, B-21 and F-15EX out of the dossier top-50
> (E3); the dossier and category sidecars were keyed by `pe_bli` while the page
> looks up by slug; and the decade index re-fused 1350/2101 under a bare key
> after the mart had just un-fused them.
>
> **Two scope errors were mine.** The plan said Tomahawk was "a different
> defect" — true of the page split, false of the decade fusion, which is
> identical (E2.1 corrects it). And I slug-keyed the dossier sidecars without
> updating their contents, so `parseDossier` rejected `3010-SCN.json` for
> saying `pe_bli: "3010"` and took the whole build down. That check was right;
> the file now carries an explicit `slug` and self-describes its page.
>
> **Still open, and a finding rather than a rounding error:** 11 key-collision
> exclusions remain, $0.75B. They are a DIFFERENT shape — `20`, `30`, `500`
> collide on ORGANIZATION, not account (the drawdown plan's **#45**), and
> `HCMC00`/`JSE000` on title variants. This sprint keyed on (account, pe_bli);
> closing those needs org in the grain too.

> **✅ #45 CLOSED 2026-08-21 (the ORGANIZATION shape of the same defect).**
> `20` (DCSA "Major Equipment" $2,230K / DTRA "Vehicles" $911K), `30` (OSD
> "Major Equipment, OSD" $212,900K / DTRA "Other Major Equipment" $12,023K /
> DMACT "Major Equipment" $7,258K), and `500` (DLA "Major Equipment" $79,251K
> / DHRA "Personnel Administration" $3,797K) share a BLI code across
> organizations within ONE account ('0300D' Procurement, Defense-Wide) —
> account can't disambiguate them, so the slug keys on organization instead:
> `{pe_bli}-{ORGANIZATION}` ('20-DCSA', '30-OSD', ...), reusing `_ProgramIdentity`'s
> dispatch-on-whichever-axis-differs design (`is_account_split`/`is_org_split`/
> `split_key()`) rather than inventing a parallel mechanism. dim_programs
> 1,749 → **1,753**; key-collision exclusions 11 → **4** (only `HCMC00`/
> `JSE000`'s title-variant shape remains, correctly out of scope). 24/24
> gates; gate 23 leg (h) extended to a composite (account_title,
> organization) key rather than a new letter — it now catches EITHER shape.
>
> **A 4th organization, DODEA, shares `30` historically** (FY2024/FY2025
> money, wound down before FY2026 — the identical shape to 1350/2101/
> Tomahawk on the account axis) — excluded from the page split by the same
> "no current money, no page" rule, but kept in `fct_decade_series`'s wider
> any-amount_type anchor so its historical series isn't silently fused into
> another organization's.
>
> **The most consequential finding wasn't in the file list.** `fct_program_
> trajectory` (backlog #37, PREDATING this sprint) explicitly SUMMED these
> same 3 keys' organizations into one "program" total, on the premise that
> they were legitimate multi-org components of one program. They aren't —
> DLA "Major Equipment" and DHRA "Personnel Administration" sharing `500`
> is the identical coincidental-BLI-reuse shape #56 already fixed for
> accounts, just summed instead of dropped. `programs_excluded.json`
> independently corroborated this pre-existing: all 7 org-lines were ALREADY
> listed there with reason `key_collision`, meaning the site's own coverage
> recompute had already determined none of them was honestly represented —
> including the "winning" side #37 was crediting a whole program's money to.
> Un-summed it (organization now threaded through `fct_program_trajectory`,
> both component-sum dbt tests, and every downstream citation-key builder
> that assumed "this pe_bli's only plurality is account"). Also found:
> `fct_book_diff`'s cross-edition self-join, three separate `traj_index`/
> `traj_orgs`-style caches keyed by `(pe, account)` alone (self-healing where
> `org` was already part of the same tuple, genuinely broken — silent
> collision, not a crash — where it wasn't), `_build_slug_by_pe`'s top50-style
> ranking join, and a stale-file gap: `program_details/` has no dossier-style
> prune, so `20.json`/`30.json`/`500.json` (real, fused pages before this fix)
> would ship forever once split, since nothing else in the pipeline reads them
> again to notice they're wrong.

> **#55 remainder — RTX/Boeing aliases: NOT engineering work. Investigated
> 2026-08-21 and deliberately not done.** RTX's page still matches generic
> aviation lines (Aviation Safety Technologies, Aircraft Engine Component
> Improvement) rather than Patriot or Standard Missile; Boeing matches none of
> F/A-18, KC-46, Apache or P-8. The obvious fix — seed aliases for the
> flagships — does not survive contact with the corpus. Of 31 candidate terms:
> **Patriot** matches 2 PEs, **AMRAAM** 3, **Tomahawk** 2, **F/A-18** 2,
> **KC-46** 2, **Apache** 2, **Hellfire** 3, **ESSM** 8, **RAM** 89. A filing
> that says "Patriot" does not say WHICH Patriot line, and picking one would
> be a false attribution — precisely the defect #52 removed.
>
> The six that match exactly one PE are no better on inspection: **Sentinel**
> resolves to "Sentinel Mods", which is plausibly the radar rather than the
> LGM-35A ICBM; **Harpoon** to "Harpoon Support Equipment", not the missile;
> **Stinger** to "Stinger Mods". A title match is not a correct alias.
>
> This needs someone who knows the programs to author the mappings — which is
> what "curated" in `program_aliases.csv` means. Filed as owner work, not
> deferred engineering. The loader works (#55's actual bug, fixed); the seed
> is the gap.
>
> *Superseded 2026-08-27 (noted 2026-09-25): the owner authored the mappings
> and the seed took them — `c6270fc9` + `1edbfcc0`; see #55's CLOSED
> 2026-09-25 marker for what they match today.*

## Remaining launch items

- **GitHub repo push** ✅ DONE 2026-07-02 — user-authorized; standalone history
  synced to github.com/andeslee444/govbudget via subtree split (re-sync per phase).
  *(Noted 2026-09-25: the standalone repository is now
  github.com/andeslee444/fiscalreceipts — the URL of the `govbudget` remote the
  subtree split pushes to.)*
- **R2 assets** ✅ DONE 2026-07-02 — 52 objects / 154 MiB at
  `assets.fiscalreceipts.com`; PDF panel, explorer, and downloads verified at
  full fidelity in production browser.  CORS live test 7/7 PASS.
  *(Noted 2026-09-25: those are the first upload's figures. The 2026-07-04
  re-sync moved 190 files / 1.48 GiB, `scripts/launch/deploy.sh` syncs R2
  before its Vercel deploy unless run with `--skip-r2` (its pages-only mode)
  since `712485dc` (2026-08-06), and the
  four synced directories measured 2026-09-25 hold pdfs 1.8 GB / 225 files,
  data 9.4 MB, workbooks 11 MB, citations 3.1 MB.)*
- **Domain** ✅ DONE 2026-07-02 — site LIVE at `https://fiscalreceipts.com`
  (apex A 76.76.21.21 DNS-only, www 308-redirect via Vercel API, canonicals/
  sitemap/OG on the domain, receipt moment verified in production browser).
  `govbudget.vercel.app` remains as an alias.
- **`NEXT_PUBLIC_SITE_URL`** ✅ DONE 2026-07-02 — baked into the production
  build (`https://fiscalreceipts.com`); 3,750 sitemap URLs on the domain.

## Standing constraints (unchanged, every phase)

Cited-or-absent; influence correlational never causal; no invented bidders;
derived figures labeled; supersede-not-delete; loud failures; polite scraping;
LLM only where deterministic paths fail; merge only on green gates + suite.
