# Refresh and reader validation

Authorized 2026-09-24: plan and proceed with the next trust/product workstreams.

## Outcome

Complete a bounded, reproducible award-refresh cycle while checking whether
the shipped reader actions reach production analytics. Preserve fiscal year,
accounting basis, confidence, receipt identity and reviewed source corrections.
Human comprehension remains a separate five-reader pilot, never inferred from
automated clicks or aggregate analytics.

## Work and ownership

1. **Refresh safeguards — implementation agent.** Bound the mechanical
   crosswalk by fiscal year; reject incomplete/reversed ranges; preview and
   cap writes; make full assignments stable under repeated/shuffled inputs.
   Preserve stronger evidence. Verify with real scratch-database tests before
   applying to the curated store. Roadmap #78/#85.
2. **Attribution reconciliation — main agent.** Inspect actual schema and
   review records against shipped precision metadata. Add an explicit rubric
   migration and one shared tally contract; preserve existing verdicts and
   distinguish attribution from mechanical-rule review. No new adjudications
   or invented human sign-offs. Roadmap #79.
3. **Bounded refresh — main agent after safeguards.** Discover available
   FY2026 DoD contract/assistance archives, compare their identities with the
   manifest, stage changed data with rollback snapshots, validate counts,
   keys, amounts and action-date coverage, then rebuild dependent outputs.
   Review diffs before promoting. Keep PDF receipt repairs reproducible through
   regeneration. Record unavailable sources instead of advancing freshness.
   Roadmap #8.
4. **Production measurement — main agent in parallel.** Inspect Vercel
   project analytics availability, trigger a bounded set of real reader actions,
   verify transport and dashboard receipt when access permits, and distinguish
   those checks from organic reader activity. Preserve the controlled-property
   privacy contract. Do not purchase a plan or change account access.
   Roadmap #90.
5. **Reader and return-visit handoff.** Keep the existing five-reader task and
   success rubric, provide a ready session/result sheet, and document any human
   recruitment or account-access dependency. Derive a reviewed change briefing
   only if the refresh produces a defensible, comparable change. No invented
   changes, user-study results, scheduled monitoring or external outreach.
   Roadmap #89–91.

## Verification and publication

- Unit/integration checks must exercise wrong years, row-cap rejection,
  deterministic classifications, rubric separation and artifact parity.
- Live probes establish source availability and analytics behavior; test
  success alone does not establish fresh data or dashboard arrival.
- Before publication, preserve a rollback snapshot, verify source → curated
  store → export consistency, build with the production origin, and run affected
  gates. Existing copy/voice debt stays visible; thresholds are not loosened.
- Use the established subtree/Git and `scripts/launch/deploy.sh` publication
  path for completed reader-facing changes, then check the public output.

## Execution record

- Baseline: deployed code `e742f3e8`; documentation through `883c6323`.
  Published award actions stop at 2026-04-23; source archives were downloaded
  June 11. Crosswalk source still lacks bounded defaults and stable assignments.
- Safeguards delegated; attribution and analytics investigation started.

- Reused and reconciled existing branch implementations, rather than repeating
  reviews already stored in the database. Restored migrations 015–017 and kept
  the tier-wide announcement sample distinct from the wave-only sample.
- Crosswalk: 42 focused tests passed; live DARPA FY2026 dry-run projected
  39,192 links without writing. Stronger links and human judgments remain intact.
- Archive conversion: restored corpus-shrink guards; 35 focused tests passed.
  Both FY2026 archives staged and independently reviewed. Contracts: 2,897,468
  unique rows through September 4. Assistance: 19,981 through August 30. Source
  partitions, manifest, warehouse, site artifacts and curated database backed up.
- Six previously reviewed PDF highlights rechecked against exact source hashes,
  canonical values and unique page glyphs, then persisted atomically with a
  before/after report. No canonical amounts or fact identities changed.
- Precision: one shared query, deduplicated sample pairs and actual mart
  membership. The old account/subagency tally included two rows excluded by
  adjudication; those no longer count as published evidence. Focused combined
  Python suite: 92 passed, including new population and staged-refresh cases.
- Reader measurement: page-view reporting and two actual HTTP-200 event sends
  verified. Hobby-plan custom-event reporting is unavailable; no account changes.
  Five-reader kit remains ready, with all human sessions explicitly not run.
- Editorial review: archive differences mix new reporting, revisions and longer
  coverage, so no unsupported program-change story was added.

- First dbt pass stopped publication on two real failures: 81 source-corrected
  transactions duplicated across fiscal-year snapshots, and one district
  program code shared by two appropriation accounts. Gates are unchanged.
  Added conservative source-revision reconciliation (three regression tests)
  and account-qualified district identity. Final dbt: 136 passed, one existing
  subaward warning, zero errors or skips. All 81 cross-year duplicates were
  proven newer source revisions; original files and row-level reports retained.

- Full export completed: 16 datasets, 135,164 citations, 204 PDFs and 30
  workbooks. Metadata keys and budget fact identities/amounts were preserved.
  The 47 skipped additive breakdowns are explicitly nonadditive district
  deduplications; their receipts retain the award-distinct formula.
- Independent PDF audit: all 9,879 PDF receipts match Parquet/JSON/shards;
  21,975 canonical identities, 58 document hashes, 2,266 source pages and all
  six reviewed locators checked. All 1,421 thousands-scale corrections and
  four strict document-only fallbacks survive regeneration. Five coordinate
  fields differ only by numeric roundtrip rounding below 0.000000001 point;
  source-glyph verification remains independently required.
- Full frontend suite: 104 files / 1,535 tests passed. Final district regression
  and shared export fixtures: 44 passed, including same-code, same-district
  programs in different accounts. TypeScript passed.
- Flow payload exceeded its 614,400-byte cap by 262 bytes after refresh.
  Flow-only compact serialization reduces it to 553,197 bytes with exact parsed
  equality; no members, values, citations or thresholds changed. Seventeen
  focused flow tests passed.
- Publication remains pending the citation gate, fresh production build,
  affected static gates, browser review, correct-remote push and live checks.
