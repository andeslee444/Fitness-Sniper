# F-15 visual consistency and source review — September 22, 2026

The F-15 family now uses one navigation, paper palette, content width, typography and aircraft drawing system across the aircraft, funding and research views. The six linked budget pages keep the same family navigation and show their government source immediately beside the program identity. This is a local implementation and verification record; no deployment was performed.

## Aircraft configurations

The initial drawing previously reused the same plate for every selection. The shared schematic now selects a single-seat canopy for A/C, a two-seat canopy for B/D/EX, and a two-seat canopy with conformal fuel tanks for E. EX has an explicit optional tank control before activating 3D. An enlarged cockpit detail identifies the seat count. A/C and B/D deliberately share schematics: internal systems differences do not justify invented external shapes. These remain simplified illustrations, not engineering drawings.

The funding thumbnail, comparison cards, Explore entry and program headers reuse this drawing system. All six aircraft also retain their existing variant-aware 3D geometry. The viewer stays optional. Its failure/reduced-motion path preserves the selected schematic and evidence access.

## Navigation and evidence

The same six family destinations remain visible across workspaces and budget pages. A single aircraft control is available in every workspace. The drawing's six-choice strip is compact on phones; chronology remains in Family history. Page hashes restore the selected workspace without a native anchor jumping past the shared header. In-content navigation transfers keyboard focus to the destination's persistent navigation link; direct navigation preserves focus.

The fixed family comparison remains independent of selected aircraft and funding record. Its five other records are available in a labeled disclosure; all citations, missing-coverage statements and accounting context remain rendered. The lead is not a family total or an allocation by aircraft.

Prominent source actions distinguish government PDFs and spreadsheets. Derived totals expose the documents and locations of their actual inputs rather than fabricating a total's own row. Workbook actions retain sheet/cell coordinates. Missing FY2026 TOA for PE 0207171F links its own J-book narrative and explicitly states that the narrative does not supply the missing figure. Receipts and fact pages use the same document actions.

The PDF viewer renders selectable text, shows the recorded evidence highlight, and provides a 200% focus action. Page or bounding-box precision is offered only when the source record contains it; unpaged narratives retain honest source-location limitations.

The field-guide paper palette also remains readable when the operating system requests dark mode. Source buttons, accounting notes, citation underlines and footer text use the matching paper/ink tokens rather than inheriting half of the dark palette. Exact reconciliation arithmetic is no longer faded below the text-contrast floor on these pages.

## Visual coverage

Reviewed at 1440×1000 and 390×844:

- Aircraft, Budget & receipts, Countries & orders, Family history, Compare aircraft, Research tray.
- Expanded Countries & variants, Orders & requests, Suppliers & systems, Programs & developments.
- Budget pages: 0207134F, 0207146F, 0207171F, F01500, F015EX, F15EWS.
- Explore family entry, populated comparison and saved-receipt states.
- Static A/B/C/D/E/EX selection, EX tank toggle, all six interactive 3D variants, and failed 3D fallback.
- Each program's direct source actions and all six receipt panels; derived inputs, workbook cells, missing-TOA narrative and a real saved PDF.

The automated 32-view desktop/mobile route check reported no horizontal overflow or browser exceptions. Additional screenshots covered Explore, populated states and model interactions. Review artifacts for this local run are under `/tmp/f15-audit/`; source placement/PDF artifacts use `/tmp/govbudget-source-*`.

## Validation and external limits

The final full functional suite passed 96 files / 1,385 tests, including the workspace-focus and program source-access corrections. Lint reported zero errors and 20 existing warnings; the final changed components and regression tests also passed targeted lint. The production export and Pagefind completed: 8,405 generated routes, 8,404 HTML files, and 4,642 indexed pages.

Build freshness/page weight, static citation/rendering, tokens, motion, typography, answer-fold and accessibility gates passed. Typography inspected 35,606 text elements across nine routes at two widths. All 17 page-weight budgets stayed within their existing ceilings; the F-15 family measured 67,161 gzip bytes against its unchanged 70,000-byte ceiling.

The final static interaction smoke verified variant and URL updates, direct government workbook actions and input locations, receipt opening, program source placement, and real Enter/Tab/Back behavior. There were no browser runtime errors. A further dark-mode pass found and repaired inherited footer and accounting-note contrast defects; all six family workspaces then passed at mobile width with no serious/critical accessibility violations or overflow. The rebuilt static family funding and F015EX pages also passed the forced-dark audit.

The expanded 24-case program audit (six records × two widths × two color schemes) found no contrast defects or document overflow. It also exposed interactive source chips inside narrative disclosure headings, interactive chart nodes inside an image role, and an unfocusable horizontally scrolling budget table. Source actions now appear inside the expanded narrative, the chart uses group semantics while retaining its keyboard links, and the budget table's scroll region has a name and keyboard focus.

After those fixes, all 24 program cases passed with zero serious/critical accessibility violations and zero document overflow. The Explore family entry also passed in dark mode at mobile width. Fresh static verification used Enter/Tab to expand an accomplishment, focus its source action and open the exact fact `0026c924483c6624`; the F15EWS budget table accepted keyboard focus and ArrowRight scrolled its columns without moving the document sideways. The final build and all seven targeted gates passed again. The source-access regression tests passed 10/10 and targeted lint was clean.

One full-suite attempt while the browser audits were running failed the existing years-matrix 50ms filter-performance assertion at 106ms (1,384 other tests passed). After the audit browsers closed, the complete suite passed 1,385/1,385 in 28.85 seconds with no code or threshold change. Final logs: `/tmp/f15-complete-build.log`, `/tmp/f15-complete-tests-uncontended.log`, `/tmp/f15-complete-static-gates.log`, `/tmp/f15-complete-browser-gates.log`. The 24-case program report is `/tmp/govbudget-program-a11y-audit.json`.

Official P-1 and R-1 workbook probes returned HTTP206 with XLSX ZIP signatures. Official Air Force PDF probes encountered TLS/gateway errors, so their live availability remains unverified. Real saved PDF rendering, a 331-span text layer, browser text selection, evidence highlighting and 200% focus were verified using an isolated local asset bridge because the production asset host blocks the local development origin. Repository asset configuration was not changed. Text selection verification used browser selection APIs rather than a physical touchscreen gesture.

The existing broader release blockers recorded in the parallel product delivery note remain separate from this UI/source pass. No trust attribution was widened and no deployment was attempted.
