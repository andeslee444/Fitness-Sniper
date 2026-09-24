# Company label review after the September award refresh

Measured on 2026-09-24 from the refreshed contracts and assistance award lake and
`entity_xwalk`. The existing 15% parent-registration margin rule is unchanged.
Six newly flagged published keys need measured labels; four historical alias
keys remain in the warehouse but fall below the top 200 published families.

This is an award-registration review, not a corporate ownership determination.
No new `pin` row is authored: that evidence kind asserts a human review. The six
new `measured` rows report what the lake contains and qualify uncertain family
scope. Registered names, warehouse keys, membership, dollars and fact identifiers
remain unchanged. Existing rows retain their original measurement dates.

## New measured labels

Amounts are net obligations over the available fiscal years. The label-selection
margin is `(winning pair dollars - runner-up pair dollars) / winning pair dollars`
on the family's largest recipient. Pairs include both parent UEI and parent name.

| Warehouse key | Measured display label | Family amount | Margin | Evidence and limits |
| --- | --- | ---: | ---: | --- |
| BROWN ROOT INDUSTRIAL SERVICES HOLDINGS | KBR Wyle Services LLC | $3.597288B | 2.0269% | All net obligations belong to three KBR Wyle Services recipient UEIs; a fourth Brown & Root member has zero net obligations. The dominant KBR Wyle UEI holds 99.7523%. Its winning Brown & Root parent registration occurs in FY2024–FY2025; FY2026 uses KBR Wyle and KBR Inc. registrations. This names the recipients without asserting an owner. |
| TRANSDIGM GROUP | TransDigm Group registrations | $3.388163B | 2.3699% | All 51 members select the exact parent name TRANSDIGM GROUP INCORPORATED, across three parent UEIs. The dominant Armtec recipient's two leading pairs have the same name and different identifiers ($380.791M and $371.767M). The qualified label describes shared registrations, not independently verified ownership. |
| RAYTHEON | Raytheon Company registrations | $32.250080B | 4.4189% | 66 recipient UEIs; 95.7686% of net obligations have recipient names beginning RAYTHEON COMPANY. Other members include historical Nightwing registrations. The dominant recipient selects Raytheon Company ($3.333034B) over RTX Corp ($3.185749B). This remains a separate registration family from RTX; the label is not an ownership claim. |
| CONSIGLIO NAZIONALE DELLE RICERCHE | Marinette Marine Corporation and other recipients | $3.059770B | 8.9291% | Marinette Marine holds 99.9802% ($3.059165B), but the remaining $605,043.72 includes a municipality and healthcare recipient alongside Fincantieri Marine Group. All six members select parent UEI JJMDKZCTCDD8; this does not establish a shared corporate owner. The qualified label preserves that distinction instead of presenting the whole amount as a research council's work. |
| SERCO | Serco Inc. registrations | $5.952086B | 9.1351% | Exactly two Serco Inc recipient UEIs. The dominant $5.634034B UEI moved from SERCO GROUP into SERCO, while nine recipients remain in the separate old family. The historical whole-group review is not transferred to this narrower grouping. |
| VERITAS CAPITAL FUND MANAGEMENT | Veritas Capital registrations | $4.273255B | 11.7684% | All 18 members select the exact Veritas parent name across three parent UEIs. Peraton-named recipients hold 91.8877%, while other businesses account for the rest. The shared-registration label avoids presenting this mixed family as Peraton alone or asserting current portfolio ownership. |

Full pair amounts, parent identifiers, fiscal-year observations and limits are
recorded in each active seed note. The bounded local evidence export is
`data/refresh/2026-09-24/entity-label-evidence.json`; it includes all current
members of these six families, dominant-member registrations by fiscal year,
and each old alias family's recipient-UEI mapping before and after refresh.

## Historical rows retained without speculative migration

The exact original 15-row seed is preserved at
`data-seeds/history/entity_display_aliases.2026-09-01.csv`. It is historical
evidence, not an additional active alias input.

| Inactive alias key | Current rank / amount | UEI comparison with the rollback crosswalk |
| --- | --- | --- |
| ROCKWELL COLLINS AUSTRALIA | 561 / $626.683M | Three of the former 15 members moved to RTX, including XSV6AZJ6SDJ7, the former $18.934B dominant Raytheon recipient (now $21.181B). The other 12 remain. None moved to RAYTHEON. The old label therefore cannot be transferred to RAYTHEON on name similarity. |
| L3 TECHNOLOGIES | 201 / $1.972060B | All 26 former members remain under the same key. It fell outside the publication cutoff; no replacement family is inferred. |
| SERCO GROUP | 297 / $1.371078B | Only DKJ1R5ABCN48 moved to SERCO. Nine members remain under SERCO GROUP. A whole-group alias cannot migrate to the two-member SERCO family. |
| APM TERMINALS PACIFIC | 226 / $1.811737B | U.S. Marine Management (ULJ3VFQNYKQ4) remains; Farrell Lines (YZ7JDRJMLJH8, now $687.013M) moved to the separate A.P. Moller foundation key. No whole-family alias migration is justified. |

## Reproduction

Read the live `entity_xwalk` and the pre-refresh snapshot at
`data/refresh/2026-09-24/rollback/parquet/entities/entity_xwalk.parquet`, joining
on exact `recipient_uei`. Never match family names to infer identity. Rank
`dim_entities` by `total_obligation desc` to reproduce publication positions.

For each selected dominant recipient, group the union of contract and assistance
Parquet rows by `nullif(recipient_parent_uei, '')` and
`nullif(recipient_parent_name, '')`, summing
`try_cast(federal_action_obligation as double)`. Exclude a pair only when both
fields are null. Order by summed obligations descending, transaction count
descending, parent name nulls last, then parent UEI nulls last. Group additionally
by `action_date_fiscal_year` for the registration history. This matches the
independent `site/scripts/gates/familylabel-recompute.py` rule; the seed is not an
input to those measurements.
