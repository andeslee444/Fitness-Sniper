# F-15 family funding history

The owner corrected the family header: showing the largest single F-15EX
record under the F-15 family heading misrepresents its scope. The replacement
shows funding across the identified F-15 development and procurement lines
over the full locally verified history, with explicit limits on that history.

## Delivered data and behavior

- FY2015–2024 recorded actuals: **17,043,321 USD thousands**, derived receipt
  `70e8427bdef8c6d1`. Enacted/current-year figures and requests are excluded.
- Annual history extends through FY2026. FY2026 request: **3,705,620 USD
  thousands**, derived receipt `d9aedd1cd8025592`; PE 0207171F is missing from
  the workbook subtotal and remains disclosed.
- Years are chronological columns and eight government PE/BLI identities are
  stable rows. Row labels and year headers remain visible while scrolling.
  Chart selection highlights and scrolls to its year without filtering sources.
- All 67 program/year amounts and 12 annual totals render immediately. Clicking
  an amount opens the existing accessible receipt sidebar, with program/year
  context, direct government spreadsheet links, exact source locators and
  input breakdowns. Older receipts load from the existing citation shards.
- Default cells partition all 83 source inputs, preserving all 93 source cells
  and 14 recorded zero inputs. Missing figures are distinct from zero; FY2025
  and FY2026 still disclose the missing EPAWSS development amounts.
- All 30 scenario snapshots carry 168 program cells from 207 workbook inputs.
  Multi-input cells reuse a canonical additive receipt only when its exact input
  set and value agree. Otherwise the bounded exporter publishes a derived
  receipt and breakdown. Homogeneous cells retain their exact source measure.
- Historical government codes F0150P and F015E0 remain separate rows. Workbook
  cell previews verify every code, scoped by exhibit, account and Air Force;
  changing legacy line numbers cannot establish continuity by themselves.
- Page-size limits remain unchanged; release checks audit every matrix cell,
  its annual partition, and the shipped sidecar/citation shards.
- Shared-program evidence is listed separately: 30 PB2026 programs with
  published receipts and six historical records with direct official PDFs.
  Source editions date the evidence, not yearly allocations. Shared-program
  budgets are excluded from all family totals. Historical receipt gaps and
  unresolved PDF pages remain visible; no receipt or page is invented.
- PB2017–2023 procurement rows use reviewed edition/account/organization/activity
  identities. Reused line numbers are never treated as permanent program IDs.
- Annual sums use canonical scenario columns, including each activity once.
  Base/OCO/total alternatives and request/reconciliation components are not
  added twice. Every input matches a workbook cell preview.
- A bounded export command patches the completed artifacts and preserves
  existing canonical citations. The full exporter invokes the same projection
  so a later refresh retains the feature.

## Coverage still to acquire

The available annual series begins with FY2015 actuals in PB2017. It is not
an all-time total. Earlier funding, early F-15A–D development, PE 0207130F,
personnel, operating costs and unallocated shared support are not represented.
The page states the start year beside the headline and expands its scope notes
with the receipts. Missing figures never become zeroes or substituted J-book
amounts. All figures use nominal total obligational authority, not outlays.

Earlier-source backfill is tracked in the roadmap. Official DoD budget archives
and older Air Force P-1/R-1 books are the next source acquisition work; acquisition
cost estimates and overlapping prior-years totals cannot fill annual gaps.

## Verification

- 33 Python tests cover membership, scenario selection, duplicate identities,
  missing members, cumulative-year gaps and existing citation/breakdown behavior.
- Independent exact-title SQL reproduced all 30 annual totals; all 31 derived
  sums passed the existing verifier. All 207 workbook inputs matched their cell
  previews; 5,251 overlapping existing workbook facts retained identical values.
- Repeat generation added zero citations. Thirteen artifact integrity checks
  passed across global registries, shards, previews, breakdowns and metadata.
- 80 focused frontend tests and TypeScript checks pass, covering annual
  selection, direct government links, receipt opening, family independence,
  and rejection of duplicate inputs, shifted years and request-contaminated totals.
- Desktop and 390px mobile review confirmed the full family history remains
  visible and independent of aircraft selection. A FY2015 procurement receipt
  opened its exact highlighted workbook cell. The cumulative receipt exposes
  all ten actuals years and their source chain.
- Visual review found a 32-input traversal cap falsely reporting missing sources
  on the cumulative receipt. A bounded 256-input traversal and a counted
  disclosure for lists over three documents fix the warning and keep the
  calculation visible. All 58 focused source/citation tests pass.
- All 20 official workbook URLs returned valid XLSX bytes from the official
  government host in bounded live HTTP probes.
- Release and visual verification are recorded after the production build.

## Program-by-year matrix verification

- 50 Python tests pass for source-code grouping, receipt reuse, exact scenario
  measures, historical separation and existing breakdown contracts.
- All 168 cells partition source inputs and reproduce unchanged annual totals;
  all 69 derived receipts pass independent recomputation. Existing citations
  and 5,251 overlapping workbook facts retain their published values.
- Frontend coverage verifies immediate rendering of all 67 cells, every click's
  program/year context, historical source documents, input drilldown, keyboard
  opening and focus restoration, explicit missing figures and legacy separation.
