# Reviewed award coverage update — 2026-09-24

Status: published and production-verified. See the [publication record](2026-09-24-publication.md) for the exact source, deployment and live checks.

## What the source update establishes

The September 6 USAspending releases expand the FY2026 DoD award-transaction
collection. Contract actions extend from April 23 to September 4; assistance
actions extend from April 10 to August 30. FY2026 remains partial.

| Source | Previous rows | Reviewed replacement rows | Newly appearing transaction keys | Retired keys | Shared keys with changed amount/date |
|---|---:|---:|---:|---:|---:|
| Contracts | 1,203,294 | 2,897,468 | 1,696,812 | 2,638 | 462 |
| Assistance | 10,005 | 19,981 | 9,994 | 18 | 58 |

Both replacements have unique transaction keys, no missing keys, no invalid
action dates or amounts, and no actions outside federal FY2026. Neither
regresses date coverage or breaches the 80% row-retention safeguard. Removed
and revised records are reported rather than silently treated as additions.

Primary sources:
[DoD FY2026 contracts archive](https://files.usaspending.gov/award_data_archive/FY2026_097_Contracts_Full_20260906.zip)
and [DoD FY2026 assistance archive](https://files.usaspending.gov/award_data_archive/FY2026_097_Assistance_Full_20260906.zip).
Archive hashes, download times and sizes are retained in the ingestion manifest.
Local review evidence and rollback snapshots are under
`data/refresh/2026-09-24/` (not committed public artifacts).

## Editorial decision

This supports a **coverage update**, not a budget-increase story. The new archive
includes previously unreported actions before the old cutoff, corrections and
retirements. Comparing its cumulative obligation total with the old incomplete
snapshot would mix reporting coverage with real activity. Neither total measures
cash paid, and neither establishes an aircraft-program allocation.

Do not add a program change briefing based solely on this archive difference.
Keep the existing reviewed budget briefings and their unchanged, cited fiscal
comparisons. A future program-change briefing needs a comparable fiscal basis,
program-specific evidence and before/after receipts.

## Cross-year corrections found by the full rebuild

The global uniqueness gate found 81 duplicated transaction identities after the
bounded refresh: 74 contracts and seven assistance actions also remained in
older FY2018–FY2025 snapshots. Each has exactly one FY2026 replacement with a
strictly later source `last_modified_date`. These are source-corrected action
dates, sometimes with revised obligations, not two separate transactions.

The reconciliation tool retains the newer FY2026 row and retires only its
proven older version. It refuses ambiguous counts, missing/tied revision dates,
or files changed after review; prepares every replacement before promoting any;
and retains the original files and row-level before/after report. The untouched
raw source snapshot remains available in the original rollback set. Historical
coverage otherwise remains at the earlier download date.

The district gate separately found that code `0145` now connects to high-tier
links under two appropriation accounts. A bare code cannot identify the funded
program. District rows, destinations and receipts must retain the account to
separate Hornet work from General Purpose Bombs.

## Regeneration checks

The final warehouse build passed 136 checks with one existing subaward warning
and no errors or skips. Budget fact values and identities did not change.
Regenerated metadata keeps separate dataset freshness: only FY2026 contracts
and assistance were refreshed. Subawards remain at June 11, and the combined
USAspending freshness label correctly retains that older date.

All previously reviewed PDF receipt repairs survive regeneration. District
receipts and destinations now retain appropriation-account identity, including
a regression where two programs share one code in the same district.
