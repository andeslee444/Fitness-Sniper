# Fiscal Receipts frontend: editorial research atlas

Status: implemented, verified, and published to fiscalreceipts.com on 2026-09-07.

## Product direction

Use calm paper-and-ink reading surfaces with precise blue evidence accents. Reserve navy blueprint stages for program illustrations and relationship views. A visitor should be able to understand a program, distinguish its fiscal measures, and open the source behind a claim without adopting an analyst persona.

The homepage provides three task entrances: understand a program, investigate changes, and find local connections. Analysts also have direct routes to cross-year comparisons and downloadable data. Navigation and global search remain available everywhere.

## Page families

| Family | Routes | Primary job |
| --- | --- | --- |
| Discovery | /, /explore/, /programs/ | Understand the scope, find a program, open a receipt |
| Program dossier | /program/[slug]/ | What, change, recipient evidence, then 13 navigable source-backed chapters |
| Organizations | /agency/, /agency/[org]/, /companies/, /company/[slug]/, /companies/families/ | Portfolio and entity identity with contract evidence separate from lobbying |
| Places | /district/, /district/[district]/ | Find documented local connections and understand the covered subset |
| Documents | /filings/, /filing/[uuid]/, /fact/ | Read a record, inspect locator and copy source citation |
| Investigation | /feed/, /years/, /flow/, /lineage/ | Find signals, compare like fiscal measures and inspect supported relationships |
| Data | /data/, /downloads/ | Query and export with grain, coverage and join context |
| Reference | /coverage/, /methodology/, /glossary/, /about/ | Resolve a trust or interpretation question without losing the research path |
| Recovery | not-found | Search again or return to the relevant index |

## Evidence contracts

- Canonical program slugs identify service/appropriation as well as PE/BLI.
- Every amount retains fiscal year, measure, accounting basis, edition and citation identity.
- Budget authority, J-book details, award obligations and lobbying amounts are distinct measures.
- An exact budget receipt does not establish a payment to a contractor. ProgramAward currently exposes recipient, PIID and confidence; per-award matching rationale/source enrichment is a future exporter task.
- Missing, unresolved, nonpublished and zero are distinct states.
- All 13 program sections, stable source/project anchors, citation actions and existing sparse-tier behavior remain.
- Site export time is distinct from each dataset's retrieval and action dates.

## Acceptance

Run TypeScript, lint, meaningful changed-component tests, static export and the existing 24-gate acceptance suite. Review home, program, citation reader, navigation/search and representative page families at desktop and mobile widths. Preserve above-fold receipt/three-answer contracts, contrast, keyboard access, reduced motion, readable line length, page-weight limits and lazy heavy visualizations. Do not publish concept images as source documents or engineering specifications.

## Concept studies

Generated with the built-in Codex image generation tool. These are illustrative mockups, not screenshots of a finished implementation. Their document tables, controls and annotations are visual explorations; implementation uses real exported evidence and supported features. The program concept's original incorrect R-1 contract label was corrected to J-book request detail.

- [Homepage](../../../art/concepts/2026-09-07/homepage.png)
- [Program dossier](../../../art/concepts/2026-09-07/program-dossier.png)
- [Receipt reader](../../../art/concepts/2026-09-07/receipt-reader.png)
- [Exact generation prompts](../../../art/concepts/2026-09-07/prompts.md)

## Implemented experience

- A shared editorial masthead, task-based navigation, mobile menu, full section directory, and structured footer connect every page family. Global search keeps its fast and deep indexes and now uses a keyboard-accessible dialog with predictable focus return.
- The homepage pairs a real program illustration with the existing above-fold source receipt and three task entrances. The visual field guide retains all three interactive pilots.
- Program pages retain the WHAT / CHANGED / WHO strip, fiscal basis labels, sparse-tier behavior and 13 original sections. New chapter navigation and source wayfinding shorten the route to evidence; category artwork occupies a separate desktop plate.
- The receipt drawer gives the source preview more space, exposes its official link and copy/share actions, and makes preview scrolling keyboard-accessible. Fact permalinks distinguish source-recorded from derived figures. A program link promises an exact fact location only when the sidecar resolves it; ambiguous identifiers lead to filtered program references.
- Program index filters and sorting survive reload and can be shared in the URL. Company search and results precede extended methodology. Company, agency, district and filing profiles have task-specific chapter links and visible interpretation context.
- Comparison, flow, lineage, signals, SQL and download pages explain their distinct measures before the workspace. Reference pages use a reading rail on desktop and a native chapter disclosure above the prose on mobile.
- Site export time is labeled separately from source dates. District table labels now describe linked award obligations across services; the old DARPA-only label contradicted the current exported data.

## Review findings and limits

Browser review covered desktop and 390px mobile home, a Virginia-class dossier, real source PDF rendering and highlight, navigation/search, shareable program filters, company directory and Boeing profile, district filtering and CT-02 detail, methodology navigation, years and flow. It caught a company-directory prose wall, which was shortened using progressive disclosure while preserving the full explanation.

The first acceptance run exposed four integration issues: the mobile menu's stable target identifier, keyboard access to the larger scrollable PDF, a borderline light-mode status-label contrast, and hidden data-dictionary discovery text. The existing category-art gate also required keeping its actual illustrations. All were fixed without relaxing assertions or ceilings. Page-weight recorded measurements were refreshed from the built HTML; numerical ceilings remain unchanged. Several existing dense routes remain close to those ceilings and should be optimized before more data or chrome is added.

This release changes presentation, navigation and explanatory labels, not warehouse facts or data coverage. PE-to-budget-receipt tracing is supported by existing citation IDs. A universal PE-to-contractor-payment trail still requires richer award-link evidence from the exporter; the UI does not present associations as proof of payment.

## Release validation

- Production static export and TypeScript passed. Full unit suite: **1,174 tests in 77 files pass**. Lint: zero errors, 17 existing warnings. Whitespace/diff checks clean.
- Final frozen-release acceptance: **24/24 gates pass** (`site/test-results/frontend-verify-release.log`), including accessibility, source click-through, persona journeys, search, performance, accounting basis and data-truth recomputation.
- Above-fold contract: all 10 sampled program pages show all three answers at desktop and 390×844; homepage receipt is fully visible. Final company-directory review puts its filter at approximately 444px desktop / 582px mobile, with no page overflow and two expected Boeing search matches.
- No warehouse or R2 source asset changed. Publishing uses `scripts/launch/deploy.sh --skip-r2`; the three existing 3D pilots remain in the static release.
- Production deployment **`dpl_AW7JRD39jVFpM72JTZYMzLUvQhDj`** is Ready and aliased to [fiscalreceipts.com](https://fiscalreceipts.com/). [Vercel deployment](https://vercel.com/andeslee444s-projects/govbudget/AW7JRD39jVFpM72JTZYMzLUvQhDj).
- All **8 live asset assertions** and **27 production HTML/status/URL comparisons** pass. The production bytes match the frozen local export across all 24 page templates, recovery, a fact rewrite and a query-bearing index URL. Real Navy P-40 PDF page 155 rendered in the live 768px receipt drawer with its source-row highlight and official URL.
- Sources remain in the shared workspace; no git commit or push was made. Concept studies and prompts are under `art/concepts/2026-09-07/`, outside the published evidence assets.
