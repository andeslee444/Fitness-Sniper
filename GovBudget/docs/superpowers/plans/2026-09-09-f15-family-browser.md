# F-15 family browser

Branch: `codex/f15-family-browser`  
Route: `/families/f-15/`  
Scope: a complete, source-backed aircraft family experience. Production deployment is not part of this branch implementation.

## Experience

The family register combines the Public Record and Industrial Almanac reading surfaces with a dark Polar Instrument model stage. A/B/C/D/E/EX live in a single swipeable and keyboard-accessible selector. Selecting a model topic updates its explanation and the corresponding budget record. Variant and comparison changes preserve the camera.

The model is original procedural Three.js geometry, loaded only after activation. It supports pointer rotation, keyboard rotation/zoom, camera presets, blueprint mode, aligned comparison overlays, and an optional sourced EX conformal-tank configuration. Single-seat A/C and two-seat B/D share simplified schematics. Geometry does not claim engineering accuracy or allocate costs. Three matching posters are generated reproducibly by `scripts/exhibits/f15-family-posters.mjs`. Rendering is event-driven, with no idle animation loop, and a context-loss fallback retains the evidence interface.

The funding workspace names the actual records (aircraft and support, fleet software, electronic protection, and other verified records), grouped as procurement or research and development. A single clickable annual chart selects the year and updates its receipt. It replaces the ambiguous Develop/Buy/Upgrade controls and competing year dropdown. Figures use existing Cite and receipt-reader components, including derived totals and their workbook inputs. Detailed annual rows, source context, and the exporter’s cited change calculation preserve fiscal status and accounting basis. Comparison repeats shared records with explicit labels rather than summing them twice.

The research tray saves validated fact IDs locally, supports removal and reload, and copies citations with record, fiscal status, TOA/PB basis, source locators and input fact links. Clipboard or storage restrictions have usable fallbacks. Optional synthesized interface sounds are off by default. URL state preserves variant, purpose, exact canonical record, year, topic and comparison. Camera angle itself is maintained in the active view but is not serialized into the share URL.

Discovery comes from Explore, all six linked program dossiers, the sitemap and Pagefind. Existing dossier award and district connections remain available through the complete record link.

## Data contract

| Record | Funding category | Mapping |
|---|---|---|
| `0207134F` | Research & development | Shared C/D/E/EX software and integration |
| `0207146F` | Research & development | Dedicated EX development |
| `0207171F` | Research & development | Related EPAWSS system development for E/EX; no variant allocation |
| `F01500` | Modification procurement | Shared C/D/E modifications and tooling |
| `F015EX` | Aircraft procurement | EX aircraft, modifications and support; broader than aircraft purchases alone |
| `F15EWS` | Modification procurement | E EPAWSS installation and support; not assigned to EX |

- Historical A/B have no separately mapped budget record, rather than a zero budget.
- Every displayed amount retains source units, fact ID, fiscal year, status, dataset, accounting basis, edition and record identity.
- Default fiscal figures use the exporter’s preferred summary fact ID, including its exact status and workbook column. Change endpoints use the same source facts.
- Canonical figures and underlying workbook rows are separate collections. Discretionary/reconciliation splits are labeled alternative views, not additions to totals.
- Variant source descriptions and milestones cite official Air Force history. Curated budget associations and topic passages are validated against the actual narrative fact IDs and text during loading.
- The family layer is distinct from the existing budget-lineage graph.

## Verification

Implemented regression coverage for monetary identities, source inputs, shared mappings, empty years, historical absence, status alignment, URL validation, keyboard selection, model-topic-to-record navigation, comparison and research export/storage behavior. The final suite passes **1,215 tests across 80 files**. Targeted ESLint and full TypeScript checks pass. The fresh production build generated **8,369 routes**, with **4,641 pages** in the Pagefind index.

All **24 acceptance gates** are verified against that final output. The full `npm run verify` invocation passed gates 2–24 but retained a gate-1 failure because the existing companies-page weight measurement understated its current size. Its recorded measurement was refreshed to 695,161 raw / 68,768 gzip bytes, retaining the existing 710,000 / 69,000 ceilings; gate 1 then passed independently against the same fresh output. This is a combined verification result, not a claim that the original full-run command exited successfully. A new family-page guard records 644,603 raw / 60,577 gzip bytes against 725,000 / 70,000 ceilings. Logs: `/tmp/f15-verified-tests.log`, `/tmp/f15-verified-build.log`, `/tmp/f15-verified-gates.log`, and `/tmp/f15-final-build-gate.log`.

Browser review covers desktop and 390px layouts, model activation and real dragging, keyboard/presets, camera persistence, overlays, blueprint/CFT configuration, real workbook receipt drilldown, research save/copy, source-list expansion and WebGL context-loss/retry. Local model checks confirmed no idle rendering. The final static preview also verified 3D activation and the cockpit hotspot opening its exact software-development source passage, with no console output or horizontal overflow. The preview is served at `http://127.0.0.1:4175/families/f-15/#inspect`. Existing earlier uncommitted work in this checkout is preserved; no commit, remote push or production release is made by this feature task.

## Public research expansion

The follow-up replaces the budget-dependent inspection placeholder with **24 substantive aircraft explanations**: all six U.S. variants across configuration, cockpit/software, electronic systems and support. Aircraft context and budget connections are separate, with their own citations. Selecting a variant defaults to a supported funding purpose; variant-only URLs do the same. The topic's funding link selects its actual canonical record before scrolling.

The new research desk contains **8 country records, 16 procurement milestones and 14 supplier/system/program cards**, backed by 58 source entries. It covers the seven operator countries, export variant names, and Indonesia's campaign reported inactive in February 2026. The older Indonesian approval and MoU remain historical milestones, not current orders. The January 2026 Korean upgrade award is also distinct from its earlier possible-sale approval.

Government records, manufacturer statements and independent reporting carry different labels and publication/access dates. Singapore's reported fleet size is explicitly distinguished from official disclosures. Unconfirmed material has a separate evidence type and is hidden by default; no rumor is invented to fill the category. Country quantities are dated acquisition or inventory snapshots, never an assumed current count of serviceable aircraft.

The procurement desk distinguishes budget requests, contracts, options, approvals, plans and deliveries. Amounts retain package scope: FY2026's rounded $3.1 billion department briefing is not substituted for the exact stored F015EX TOA; FY2027's P-40 request is a newer external source. A contract ceiling, initial obligation and payment are different measures. Foreign sale values alone do not establish a cost to U.S. taxpayers. No aircraft unit costs or supplier allocations are inferred.

Search and category, country, acquisition-stage, government-source and U.S.-variant filters help readers select useful detail. Every card has its source drawer and citation-copy action. The complete research module loads on approach or explicit activation, while the initial page carries the 24 inspection explanations. This preserves existing payload and HTML size ceilings. The additional research is a curated, dated source layer; it does not change the canonical warehouse export, budget facts, or source-receipt identities.

Validation: **1,244 tests across 82 files pass**, with targeted ESLint and TypeScript checks. Browser review verified all 24 contexts, all categories and filters, citation copying, source drawers, and correct topic-to-record navigation at 1440px and 390px. Contract-ID search also includes identifiers carried in a figure's accounting basis. No horizontal overflow. Settled desktop accessibility scans across all four research categories have zero violations or incomplete checks; mobile has zero violations, with its remaining contrast checks manually reviewed.

The final production build and full `npm run verify` invocation pass **24/24 acceptance gates**, exit 0. The family HTML measures 665,992 raw / 67,152 gzip bytes within the unchanged 725,000 / 70,000 ceilings. Final static-preview inspection verifies the revised Indonesia status and searching `FA8634-26-C-B002` at desktop and 390px widths. Console output contains only the expected local-preview notice that Vercel Analytics is unavailable outside Vercel. Final logs: `/tmp/f15-context-verified-tests.log`, `/tmp/f15-context-verified-build.log`, and `/tmp/f15-context-verified-gates.log`. The existing preview tab was queued to navigate to the refreshed research view; the preview server remains at port 4175.

## Follow-on boundaries

Exact per-aircraft 3D assets, interactive foreign/export models, component-specific cost allocations, and family-wide local-impact maps require further source/asset work. The current site exposes the six-variant U.S. model register, the six verified budget records and the broader international research desk without inferring those additions.

## UX refinement in progress

The follow-up separates Aircraft, Budget & receipts, Countries & orders, Family history, Compare, and the Research tray into focused workspaces. Hash navigation preserves variant, funding record, year and topic; modified links retain native browser behavior. The aircraft view retains the full swipeable variant selector and a larger, better-lit model. Other views use a compact variant selector. Research opens with a sourced overview and explicit category entry points.

The Source data disclosure now clearly denotes the underlying fiscal records, separate from the one year-selection chart. The selected-year statement precedes the annual context on desktop and mobile. The funding chart uses a shared zero-based scale with labelled units, distinct fiscal statuses, source-linked amounts, and only one year selector. A missing year remains absent rather than being drawn as zero. The official workbook reference is resolved from the selected fact or its same-year component rows for derived totals. The program route and canonical receipt remain separate, direct destinations.

Fresh screenshot-only Astra critiques guide the design pass. Every review uses the same prompt and only the current screenshot in a fresh context. After the built-in worker quota was reached, reviews continued in separate ephemeral, read-only local Astra sessions in an empty directory. The requested visual bar has not been met; design iteration and independent critique are continuing. The final design and its acceptance evidence will replace this interim note.

The latest full functional baseline passes 1,326 tests across 85 files. Iteration 61 passes 140 focused family-browser, funding-input, family-data and footnote tests, plus TypeScript. Copied citations preserve the declared request, enacted or actuals status in every export format. Iteration 61 passes 27 targeted funding accessibility checks at 1440, 768 and 390 pixels with Fact IDs on and off. Source buttons preserve exact values, cells and focus return; headings explicitly say budget request, enacted funding or reported actuals. Source Serif 4, IBM Plex Sans and IBM Plex Mono are served locally under SIL OFL 1.1; the seven files total 244,040 bytes, with licenses and provenance in `site/public/fonts/f15-register/`.

The source receipt includes only complete, reconciled input sets. FY2024 selects its two inputs; FY2025 has no complete additive set and therefore no breakdown. The selected total uses the exact parent fact and is outside the additive input region. Monetary labels and source controls open the exact citation. Chart bars share a zero baseline and physical width; missing coverage is never zero. The comparison uses its actual source years and appears only for the matching selected fact.

Citation-reader focus restoration is covered by nine regression tests and twelve desktop/mobile browser paths, including drilldown and Back. Mobile workspace navigation reveals focused tabs without moving the page vertically. A/B variants retain aircraft-selector recovery in their funding empty state. All six workspaces remain navigable with preserved URL state. The long-series development chart passes the mobile overflow regression at both ends of its scroll range. The interactive model remains in Aircraft. An exploratory generated family illustration is archived with its original, compressed asset and exact generation prompts in `art/exhibits/f15-family-line-plate-v1.md`; it is not currently displayed in the funding view.

The latest interim export generated 8,369 routes and indexed 4,641 pages. Its family HTML measures 678,097 raw / 68,630 gzip bytes against the unchanged 725,000 / 70,000 ceilings. The earlier baseline verification passed 22/24 gates; only source edits newer than the build marker and two raw motion-duration literals failed. The literals have been replaced by existing motion tokens. Rendering, source interactions, accessibility, Lighthouse and data-truth gates passed. These interim results are not final acceptance: a fresh export, all gates, and browser review must follow visual acceptance.

The FY2026 F015EX receipt now exposes only the three exact inputs named by its canonical derived fact `4a9ae7cc78dcf0ba`: `03407158217dec76` (combat aircraft), `5768200ce4fbc494` (modification of in-service aircraft), and `819f32a0ad3fb66e` (aircraft support equipment and facilities). Labels were checked against the official FY2026 P-1 workbook, SHA-256 `4d965906ad91aa8b7d6d5f891a0717ac25ace6c18f3d50df07ebde611774a9c0`, sheet Exhibit P-1, cells W847, W875, and W923/W932. The support fact already aggregates two source rows. Alternative reconciliation-request facts are not added again. The resolver requires complete, unique, compatible inputs whose values reconcile exactly; malformed or partial inputs do not produce a breakdown. These budget activities do not establish per-aircraft prices, parts allocations, or supplier payments.

Final visual acceptance, a fresh export, the full acceptance registry and final static browser review remain pending. These checks do not claim completion or publication.
