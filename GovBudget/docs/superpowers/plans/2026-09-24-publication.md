# Publication record — September 24, 2026

Authorized by the user's request to plan and proceed, following the existing
commit, push and publish authorization. The refreshed release is published and
production verification passed; the source and deployment are recorded below.

## Changes

- Refreshed the September 6 FY2026 DoD contract and assistance archives. Contract
  action coverage reaches September 4; assistance reaches August 30. Subawards
  remain June 11, and FY2026 remains a partial reporting year.
- Added bounded, deterministic crosswalk safeguards. A live FY2026 DARPA dry-run
  examined 39,192 candidates without writing; stronger links and stored human
  reviews were retained. Attribution precision uses the actual published pairs.
- Reconciled 81 proven cross-year transaction revisions with rollback records.
- Corrected shared-code attribution on district destinations and all 27 split
  program pages. Removed 164 sibling-account detail rows and 65 narrative rows
  from member pages. Supporting documents, prose amounts, headline receipts and
  project rows retain the exact account/organization identity.
- Withheld unassignable shared-code lobbying, prime and lineage claims; empty
  states explain the attribution limit. Pages with award records but no overall
  recipient total link to those records instead of claiming no company is linked.
- Reconciled six company labels from registration evidence; preserved the old
  seed and four inactive aliases in history without new human-review pins.
  Methodology derives its current 14/200 close-label census from the warehouse.
  The company page and feed verifier preserve the same exact reviewed label.
- Restored concentration scope in validated normalized exports. Both export
  shapes require matching values, units and supported confidence-scope evidence.
- Clarified that registration grouping does not verify corporate ownership,
  a missing flow view does not mean no award is linked, and dataset refresh
  dates differ within the combined USAspending collection.

## Validation

- Full dbt: 136 passes, one existing subaward warning, no errors or skips.
- Full frontend: 106 files / 1,572 tests passed, including concentration-scope
  and curated feed-label regressions. The final methodology wording pass was
  checked by the production build, TypeScript, static gates and browser review.
- Account-specific enrichment regression and adjacent suites: 226 tests passed.
- Independent final member audit: 27 pages, 134 detail rows, 53 narratives and 19
  headline citations checked against exact source identities, with zero errors.
- Independent PDF audit: 9,879 receipts, 21,975 canonical identities, 58 source
  hashes and 2,266 pages. All 1,421 unit repairs, six corrected locators and four
  document-only fallbacks survived regeneration, with no canonical budget amount
  or fact-identity changes.

- Final browser-free gates: 14 of 15 passed. Build, static rendering, feeds,
  districts, filings, share images, animation markers, link graph, coverage,
  motion, program skeleton, accounting basis, data truth and tokens all pass.
  The copy gate retains 22 known rule-level findings; its rules are unchanged.
- Final citation verification: 50/50 sampled receipts, 5,251 workbook overlaps
  with no divergence, all 13 integrity checks and 25/25 sampled narrative
  locations. The latter is a sample, not complete narrative-location coverage.
- Desktop review: Hornet account identity and five-award summary; concentration
  scope; reviewed company labels and ownership caveat; methodology disclosures;
  F-15E workbook receipt with Exhibit R-1 cell P676 and 233,018 USD thousands.
  Mobile Hornet review at 390 × 844 found no horizontal page overflow and the
  summary link reached its five award rows.

## Remaining product work

The five-reader pilot is ready but all sessions remain unrun; no recruitment
messages were sent. Production page-view reporting works. The two controlled
custom-event sends received HTTP 200, but the active Hobby plan does not provide
custom-event reporting. No subscription, privacy or account changes were made.
The reader pilot can run without paid analytics.

No program spending-change briefing was created: archive revisions and backfills
support a coverage update, not a comparable change in program spending. Existing
copy/voice-rule findings remain open; this release must not be described as a
fully green gate suite. Browser checks are focused user-flow reviews, not a rerun
of all browser-automation gates.


## Production result

Functional monorepo source: `ebbdf0d6f203f76b0b6f281351be74a570578a13`.
Standalone subtree: `e8cc4162094b632325a9de91b4053388e0707b77`, merged and
pushed to Fiscal Receipts `main` as
`8cfb5720b7b662379dfee6825fbfc3e885a491a9`. The final production build completed
at 06:49 UTC with 8,405 routes and 4,642 indexed search pages. Git-triggered
builds remain disabled; a source push alone did not publish this release.

`scripts/launch/deploy.sh` completed nondeleting R2 upload, production deployment
and all eight live-asset assertions. The first page-upload attempt hit a
connection error; the normal deployment script succeeded on retry with the
same reviewed output. Production deployment:
[govbudget-qtjjkhy79](https://govbudget-qtjjkhy79-andeslee444s-projects.vercel.app),
aliased to [Fiscal Receipts](https://fiscalreceipts.com).

Independent verification completed by 07:05 UTC: all **19 public responses**
returned HTTP 200 and matched local artifact bytes. These include the F-15
family and program pages, methodology, MA-06, both account-qualified code-0145
programs, Raytheon's company page and feed, coverage, signals, flow JSON, four
receipt shards, the F-15 detail sidecar, and the R2 citations and budget-to-awards
Parquets. Python's default HTTP client was rejected on the two R2 URLs; normal
curl requests returned the exact artifacts, and the complete 19-target check
was rerun successfully using curl. The public citations Parquet is 3,286,731
bytes, SHA-256
`211d17b0b8476036bf9ce4bc22d6fe25ec2b0e6fd7f4e38dfeb478f3f17c6a2f`.

Live browser review confirmed Hornet's five linked awards and account-qualified
lobbying disclosure, the September 4 partial-year award window, and both PDF
receipt states. F-15 receipt `f6d6db240d3be8ba` renders page 20 with **78,345 USD
thousands (= $78.3M)** and the matching highlighted source amount. Receipt
`90fab19bdc91648a` shows the unresolved-location notice and direct government
PDF action without claiming a page, highlight or printed amount. Exact public
bytes plus these focused browser checks establish the release's reviewed
scope; they do not claim a new exhaustive visual review of every route.

This publication record and its roadmap follow-up are documentation-only;
the deployed functional source remains the commit identified above.
