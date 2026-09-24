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
- Every year appears in a funding table with its program/activity rows, cited
  amounts, government spreadsheet links and exact worksheet/cell locators.
  Chart selection highlights a year without filtering any sources. The family
  total remains independent of aircraft and program selectors.
- Twelve preferred annual snapshots are displayed; the data export retains
  thirty scenario snapshots, 207 workbook inputs and 31 derived receipts.
- Annual totals and current-year receipt rows render immediately. Older source
  rows load automatically from a same-origin sidecar, with cached results and
  a retry state. The page keeps its existing size limits; release checks compare
  the shipped sidecar and every receipt shard with the audited source data.
- The default table contains 83 source rows across FY2015–2026, preserving
  14 genuine zero records and all 93 source cells. Missing workbook figures
  remain explicit in FY2025 and FY2026.
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
