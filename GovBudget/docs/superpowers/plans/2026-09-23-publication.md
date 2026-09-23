# Publication record — September 23, 2026

The user authorized committing, pushing and publishing the completed F-15 and
parallel product work. The initial source commit is monorepo `93bda149`; its
standalone publication merge `d80ea787` was pushed to Fiscal Receipts `main`.
Git-triggered Vercel builds are disabled, so that push alone did not deploy.

## Repairs found by release validation

- GAO reports and assessments are selected using the existing human-ratified
  report/program/canonical-slug decisions. Unratified editions are omitted;
  no new adjudication is inferred from a model verdict.
- Contractor concentration preserves its exact cited all-link series and
  explicitly states the high/medium-confidence, pooled-year scope. Feed cards
  without a supported canonical concentration destination are excluded from
  the server page, fetched cards and RSS/Atom together.
- Flow labels were regenerated using the current font metrics. Only label and
  leader positions changed; values, nodes, edges and citation IDs did not.
- Exact aircraft illustrations retain the existing category marker used by
  the hero gate.
- Subaward evidence is identified as a medium-confidence description match.
  The prime-award URL provides context, not a direct subaward-document link;
  it cannot imply an allocation of prime-award dollars. The citation validator
  now checks this explicit contract across every subaward citation.
- Asset upload uses nondeleting copy so remote-only source documents survive
  a publication with a smaller local asset collection.

## Validation and remaining work

The first complete site run passed 22 of 27 gates. The failed source and layout
gates above are being repaired and rerun. Focused Python validation passed 110
tests. Full `verify-phase5b1` passed: the citation sample passed 50/50, all
citation-integrity checks passed (including all 114 subaward records), and the
narrative source-page sample passed 25/25. The subaward identities were also
reconciled against the raw imported USAspending records with no recipient or
prime-award URL mismatches.

The copy/voice gate remains open across navigation, metadata, headings and
prose, including legitimate quoted government names. Its rules and thresholds
have not been disabled, widened or blanket-exempted. This is editorial debt,
separate from the source/data defects addressed for publication. Reader sessions,
production analytics arrival and human-held-out Jev evaluation remain unrun.

Final build, deployment and live verification results will be appended here.

The final functional suite passed 98 files / 1,431 tests. The source/exporter
repair also passed 50 focused Python tests, in addition to the 110 validator and
flow tests above. All 533 concentration programs retain their exact cited
series; 33 cards with ambiguous destinations are omitted consistently, leaving
1,702 published feed cards (1,563 concentration cards). Values a few machine
precision units above HHI 10,000 are preserved rather than rounded or rejected;
materially out-of-range values remain rejected. No gate ceilings were changed.

The feed and coverage gates now count the shipped feed rather than withheld
source candidates. An independent check verifies exact card membership, order
and content against canonical destination pages displaying both original
concentration citations; six regression cases passed. The Python and reader
subaward contracts also both reject monetary units on link evidence (16 focused
validator tests and all 114 exported records passed).
