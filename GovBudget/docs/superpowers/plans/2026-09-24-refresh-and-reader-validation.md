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
- Citation gate passed: 50/50 sampled receipts, zero divergent workbook
  overlaps, every integrity leg, and 25/25 sampled narrative locations.
  Independent district audit: 611 rows across 189 sidecars and all 11
  account-resolved destinations agree with warehouse amounts and receipt IDs.
- Publication remains pending the fresh production build, affected static
  gates, browser review, correct-remote push and live checks.
- The first built-site checks passed 13 of 15 browser-free gates. Data-truth
  stopped publication on six newly ambiguous company labels, four aliases no
  longer in the top-200 published population, and a stale methodology count.
  Labels are being reconciled against current and rollback registration/member
  evidence without changing grouping, amounts, the 15% threshold, or claiming
  new human review. Methodology now derives the 14/200 census from the warehouse;
  the independent gate continues to recompute it from the raw award lake.
- Browser review confirmed F-15 workbook receipts and account-qualified
  district navigation to Hornet. It also exposed a contradictory empty-state:
  Hornet said no company was linked despite listing five award records. The
  recipient summary now links to those records and explicitly states that no
  program-wide recipient total is available. Two focused tests passed and a
  built-page regression check covers the contradiction across program pages.
- The broad copy/voice gate still reports 22 existing findings. This is tracked
  release debt, not a fully green verification suite; no rule was weakened.
- Continued browser review found a separate shared-code defect: Hornet's
  account-qualified page still included General Purpose Bombs PDF details,
  narratives and lobbying matches. An independent source-identity audit across
  all 27 split program pages found 164 detail rows and 65 narrative rows from
  a sibling account or organization. Publication remains blocked while those
  enrichments are bound to exact account/organization identity; ambiguous
  lobbying matches must be omitted rather than assigned to both pages.
- Implemented exact member keys for detail deduplication, FY2024 source IDs,
  narrative counts, prose amount links and years-matrix projects. Narratives
  receive an account only from a unique exact document/program/organization
  match; shared-code lobbying, prime and lineage claims are omitted from member
  pages when no member identity is supplied. The new regressions and relevant
  existing suites passed 226 tests; regenerated-artifact audit remains pending.
- Company aliases are now reconciled: six measured rows, no new human-review
  pins, four inactive aliases archived in the byte-identical original seed.
  Evidence and membership changes are recorded in
  [the company-label review](../reviews/2026-09-24-entity-label-refresh.md).
- The completed member audit passes: 27 pages, 134 detail rows, 53 narratives
  and 19 headline citations agree with exact source identities. Canonical source
  facts remain intact; 164 sibling-account details and 65 sibling narratives
  are excluded from member pages. The 226 relevant Python tests pass.
- Final refreshed-data frontend run passes 105 files / 1,567 tests. It caught
  and repaired a lost concentration-scope disclosure in normalized exports;
  independent raw/normalized fixtures preserve malformed-evidence rejection.
  Registration labels and methodology explicitly distinguish reported parent
  identifiers from verified corporate ownership. Flow-empty copy no longer
  implies the absence of linked awards.
- Final citation verification passes all 13 integrity checks, 50/50 sampled
  receipts, 5,251 workbook overlaps with zero divergences, and 25/25 sampled
  narrative locations. The earlier in-progress export check was transient;
  all 20,298 lobbying receipts resolve in the completed output.

- Final release: functional source `ebbdf0d6` built successfully; full frontend
  106 files / 1,572 tests; final browser-free gates 14/15 pass, with only the
  22 existing copy findings. Focused desktop/mobile review passed. Methodology
  now states the oldest dataset refresh and distinguishes flow availability
  from linked-award evidence; visible interpolation spacing was corrected.
- Published standalone `main` merge `8cfb5720` through the normal deployment
  script. The first upload failed on a connection error; retry succeeded.
  All eight live-asset checks and 19 HTTP-200 byte-for-byte public artifact
  comparisons pass. Live PDF highlights, document-only fallback, Hornet account
  disclosure and partial-year award coverage were checked in the browser.
  See [the final publication record](2026-09-24-publication.md).
- The authorized implementation/publication work is complete. Five-reader
  sessions and human Jev evaluation remain unrun; the study kit is ready.
  Hobby custom-event reporting and existing copy-rule debt remain explicit.
