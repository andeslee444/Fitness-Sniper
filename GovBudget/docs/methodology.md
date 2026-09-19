# Methodology

**Last updated:** 2026-09-01

---

## 1. What this is

GovBudget connects four things that live in separate government silos: what
agencies said money was for (budget documents), what was actually obligated and
to whom (federal and state spending records), who ultimately received it
(contractors, grantees, and their corporate parents), and what auditors said
about it (GAO findings, improper-payment estimates). Every number on this site
carries a citation to the exact source document, page, or API endpoint it came
from. If we cannot cite it, we do not publish it.

---

## 2. Where every number comes from

**Federal awards — USAspending.gov.** The official federal award database
(contracts, grants, loans, and subawards), mandated by the DATA Act. We
download bulk archive ZIP files from `files.usaspending.gov/award_data_archive/`,
convert them to compressed Parquet, and record the exact file name, URL, and
SHA-256 hash of every file. Current scope: Department of Defense agencies,
FY2017 onward. Update cadence: monthly (USAspending publishes new full-archive
files on a monthly cycle).

**DoD budget justification books ("J-books").** The detailed budget submissions
the Pentagon sends to Congress each spring, published at
`comptroller.defense.gov`. These cover every research and development program
(R-2 exhibits) and procurement budget line (P-40 exhibits) with program
narratives, project-level cost tables, and congressional justifications.

The Pentagon's budget system embeds its own database inside these PDFs: the
full structured XML that generated the PDF is attached as a file inside the PDF
itself. We extract that XML directly rather than re-reading numbers from the
printed pages. A FY2026 DARPA justification book, for example, contains a
1.5 MB XML attachment with every program element, project, cost figure, and
narrative. For the rare document that lacks an XML attachment, we use a
deterministic PDF parser as a fallback, with an accuracy gate that requires
≥98% numeric-field agreement against XML-backed ground truth before that path
is trusted.

We also download the comptroller's official R-1 and P-1 Excel rollups, which
list every program element and budget line item with FY dollar figures. The
FY2026 R-1 workbook contains 1,143 PE/BLI rows. These serve as the independent
control totals that every extracted figure is checked against. Update cadence:
annual, with each February President's Budget release.

**Improper-payment estimates — paymentaccuracy.gov.** Agencies are legally
required to estimate and report payment-error rates. The dollar exposure figure
we show per agency — the estimated improper dollar amount — is derived by
multiplying the published rate by the published outlay figure. The federal
government reported approximately $186 billion in improper payments in FY2025.
This is a derived estimate and is labeled as such. Update cadence: annual.

**GAO high-risk list — gao.gov/high-risk-list.** The GAO's biennial list of
federal programs at high risk for fraud, waste, or mismanagement. We collect
each area's title and its link in the current GAO report. Update cadence:
biennial.

**Senate lobbying disclosures — lda.senate.gov.** The Senate Lobbying
Disclosure Act database (`lda.senate.gov/api/v1`) contains filings
for 2025 and prior years, each with a permanent UUID, registrant, client
company, dollar amounts, agencies lobbied, and issue text. We link LDA client
names to our company-family database and match each filing's issue text
against our program titles for keyword co-occurrence — never a claim that the
filing names the program. A mention qualifies only when the exact PE/BLI code
appears, a curated alias appears, or at least two distinct, non-generic title
words co-occur in the same filing; each row of the `fct_program_lobbying`
dataset records which tier it qualified under (`evidence_kind`). The current
mention count is derived from that dataset on every build and published on the
live methodology page rather than restated here as a fixed number: an earlier
revision of this document said "32,780 program mentions across 245 programs",
a count produced by a since-withdrawn method that accepted a single shared
common word as a match (correction 34,538 → 10,560, recorded in the site's
corrections table). As of the 2026-08-31 build, the mart holds 14,016
evidence-tiered mention rows across 499 program elements. Lobbying income and
expenditure by year are shown alongside federal obligations received —
influence is presented side by side with outcomes, never as a causal claim.

**State checkbooks — California and Connecticut (pilot).** California's Open
Fi$Cal and Connecticut's OpenCheckbook publish transaction-level government
spending. We aggregate by department, spending category, and fiscal year, and
use Census Bureau population estimates (NST-EST series) for per-capita
comparisons. The category mappings that bridge both states' classification
systems are published alongside the data.

---

## 3. How we verify

**Reconciliation.** Every figure extracted from a J-book clears two arithmetic
checks. Check A: project-level amounts within an exhibit must sum to the
program-element total in that same exhibit (tolerance: ±$0.001M). Check B:
that program-element total must match the corresponding row in the official R-1
or P-1 Excel rollup for the same program, appropriation, and fiscal year.
Failures do not get published — they go to a human review queue. No
unreconciled figure is served without a visible flag.

**Zero-absent rule.** When a program has no funding for a given fiscal year,
the official rollup workbook simply omits the row (an absent row means zero).
Our reconciliation code recognizes this so zero-funded programs are not
incorrectly flagged as failures.

**Coverage gate.** At least 99% of R-1 program elements must have either
extracted detail or an explicit gap record. Silent holes — program elements
with no record of any kind — are a build failure.

**Provenance spot-check.** Each build randomly samples 50 served facts and
mechanically verifies that the cited source document exists on disk, its
SHA-256 matches the download manifest, and the XML element path resolves to a
real node in that document. A number whose citation chain breaks does not
render.

**Per-build automated checks.** A Python test suite and a browser test suite
both run green before any build ships, alongside the site verification gates
and the dbt data-model assertions. The counts of gates, assertions, and
evaluation questions are derived on every build from the artifacts that
define them — dbt's compiled manifest, the `verify.mjs` gate registry, and
the eval set with the gate's own threshold constant — and published in §3 of
the live methodology page; this document does not pin them (an earlier
revision's "197 test functions, 21 dbt assertions, 45 eval pairs, ≥41
correct" had all drifted). As of the 2026-08-31 build: 24 site verification
gates, 99 dbt data-model assertions, and a 48-question analyst-agent
evaluation set requiring at least 44 correct answers and 100% citation
resolution before shipping.

---

## 4. How confident to be

**Company families — registry fact vs. name inference.** When we say a company
received a total figure across its subsidiaries, we rely on one of two methods.
*High confidence* (registry fact): the subsidiaries share one registered parent
UEI in SAM.gov, so the *grouping* is a registry fact rather than a guess.
*Medium confidence* (name inference): slightly different legal-name variants
normalize to the same string (e.g., "THE BOEING COMPANY" and "BOEING COMPANY,
THE (INC)"). Both tiers appear on screen; the method is always disclosed.

**The tier grades the grouping, never the name.** A family's label is the
registered parent name of whichever member holds the most money — an argmax
that knows nothing about how close the runner-up was, or about which
registration the registrant still uses. 15 of the 200 families we publish carry
a label that beat its runner-up by under 15%. The largest is a family that is
97% Raytheon Company obligations and was titled "ROCKWELL COLLINS AUSTRALIA PTY
LIMITED": a common registered parent name, recorded in SAM.gov, at high
confidence, and wrong — RTX had already reverted that registration. Every
family inside that margin now carries a reviewed label from a hand-curated seed
(`data-seeds/entity_display_aliases.csv`), each row recording whether it
corrects the name or merely pins the argmax winner, and the build fails if a
new one appears unreviewed. The registered name stays visible on every company
page beneath the heading, because that is the string USAspending answers to.

**What a SAM.gov extract can and cannot do.** The registered parent name a
confidence tier reads is *itself* the SAM.gov registration, so fetching it back
from SAM returns the same string and upgrades nothing. Where a build has fetched
a family's SAM record — status, CAGE code, legal business name, business types,
primary NAICS and expiry — that company's page shows it with its own citation;
where it has not, the page shows no line rather than a guess. (ROADMAP #10.)

**Budget-to-contract links.** Connecting a budget program element to the
contracts that funded it is an inference, not a direct database join. As of
2026-09-11, 9,587 of the 12,595 links the crosswalk grades high or medium
carry a per-award hand adjudication — the most recent made on 2026-09-01 —
recording which program elements, if any, the award's own contract record
supports. 8,474 of those found work that could not be pinned to any one
program element; those links publish at medium.
The announcement+lexicon, fpds-ap and subaward+lexicon paths carry no per-link
adjudication — their precision is sampled instead (below). The page renders
every one of those figures from `site_meta.link_adjudication` and gate 24 leg
o fails a build whose sentence states a number the block does not hold.
(The two dates are two facts and the page states both: the census is the
export run's, the adjudication the last one made. They were welded until
2026-09-11 — "as of 2026-09-01, 9,587 of 12,595" is a ratio that never held,
because 2,731 of those links were created on 2026-09-04, after the last
adjudication, which is exactly why they carry none; on 2026-09-01 the ratio
was 9,587 of 9,864. The sentence this replaced said "every published link was
individually hand-adjudicated … a link publishes as high only if neither
[adversarial reviewer] could refute it", which the census does not support —
60 rows in the whole adjudication table record both lenses, 57 of them on a
link the crosswalk grades high or medium. Backlog #109 carries the remaining
five-path evidence pass.) *High*: affirmative
program-level evidence — the contract names a program the budget line's own
J-book pages also name. 60 of the 768 links published at high carry a
per-award hand adjudication, all 60 challenged by two independent
adversarial reviewers; the other 708 rest on the announcement+lexicon path.
(Measured 2026-09-11 over the MART — the tier a reader meets, not
`budget_line_awards`: dbt demotes an unadjudicated `account+tokens` high row
to medium and Postgres has no column for it, so re-deriving the tier there
counts 881 links where the site publishes 768. Of the 708, a match basis is
recorded on 384 — `site_meta.link_adjudication.high.by_path` carries the
figure and gate 24 leg o binds every number the sentence states, plus the
rule that each path publishing at high with no adjudication is NAMED. This
replaced "adversarially verified", which was true of 60 of 768.)
*Medium*: most such links are
account-based — the award drew from the same appropriation account as the
program, usually under the same sub-agency — an association, not evidence
this specific program paid for the contract. A held-out sample of account /
sub-agency links, judged on program attribution, confirmed 0 of 60
(2026-09-11). Where the evidence is
instead an FPDS acquisition-program tag or a subaward description (both below),
the program is established but which of its budget lines paid is not.
*Low*: only the account matches — never published. The earlier
automated high tier (account match plus keyword overlap) measured 9.1%
precise under this adjudication (37 of 408 confirmed) and was corrected on
2026-09-01; superseded links are retained in the correction record.

A second evidence path covers major acquisition programs. Some DoD contract
records carry an FPDS "Program, System, or Equipment" tag naming the
acquisition program (F-35, Virginia class, Sentinel). We hand-mapped every
such program (746 in our corpus; 449 mappable) to its J-book budget lines,
each mapping challenged by a two-reviewer adversarial process, then
linked a tagged award to a specific line only when the award's own funding
accounts match that line's appropriation. FPDS-tagged awards publish at
*medium* — the tag plus a verified program mapping establish the program,
and the award's funding accounts confirm the money color, but which of a
program's several lines (production vs. modification vs. research) paid is
not provable from account data alone. A held-out study measured the earlier
"unique line" *high* tier at 34 of 60 and it was withdrawn on 2026-09-04.
Tagged awards whose funding is entirely outside the program's J-book
accounts (e.g. O&M sustainment) are not linked. The FPDS tag is DoD-entered
and sparse (well under 1% of awards, concentrated in the largest programs),
so absence of a link never means absence of spending.

A third evidence path reads the Department of Defense's own daily contract
announcements (defense.gov, archived with snapshot timestamps and SHA-256
hashes): each announcement names the contract number and describes the work,
often by program. Where an announcement's program name is one a program
element's J-book narrative itself owns (a lexicon entry carrying the verbatim
narrative quote), the pair is a candidate; every candidate is judged by an
agent reviewer and challenged by an independent adversarial reviewer, and only
links surviving both publish — at *high*: the announcement establishes the
contract, and the program is identified by its name as written, by a
normalized designator, by an alias an adversarial reviewer checked, or —
rarely — by the announcement's own description of the work. Where the
adjudication packet recorded which of those applied, the link's citation card
states it; where it did not, the card says the basis was not recorded rather
than asserting one. Announcement links
additionally require the award's funding accounts to match the line's
appropriation; awards funded only from operations and maintenance money are
not linked to research or procurement lines. Platform-support mentions,
generic services, and weak generic names are rejected by design. Each link
cites its announcement (article id, date, URL).

Scope of the announcement path, stated plainly: deterministic name matching
covered every archived announcement record that joins the award lake; the rest
— the residue — went to an LLM-assisted alias pass that decodes designators and
aliases (PATRIOT backronyms → PAC-3, Global Hawk → RQ-4B). /methodology/ states
the counts, the share of the residue by announced value the pass has covered,
and the held-out precision of its most recent round; every one of those figures
is derived from `site_meta.announcement_llm_scope` (written by
`scripts/load_announcement_scope.py` from the wave manifests and the pass's own
precision sample, recomputed against the rendered page by gate 24 leg q), never
typed here or there. That round's precision is measured on ITS links alone: the
tier-wide study further down sampled the announcement tier on 2026-09-04,
before those links existed, and stays pinned to that draw. Correction,
2026-09-19: until this date the page carried four literals from 2026-09-02
instead — "3,840 … about 88% … 12,811 … ~12%" — describing a residue whose
selection code was never committed and which no later reconstruction
reproduces; they are why the figures are derived now. An unrecorded basis is
not evidence the announcement named the program outright.

Where the only evidence is a subaward: FSRS subaward reports describe the
work a subcontractor performs under a prime contract, and when that
description names a program the PE's own narrative owns, the prime is linked
at *medium* — the evidence is one hop removed, so it never publishes as high
and its rationale names the subaward it rests on.

**Measured precision of the published tiers.** A held-out stratified sample of
published links is re-adjudicated by a two-reviewer process, and
/methodology/ prints the confirmed/judged figure per tier from
`site_meta.link_precision` (the exporter derives it; no figure on that page is
typed by hand). Every published figure answers ONE question — the study's
*rubric*, recorded on every verdict row (`link_precision_samples.rubric`,
migration 015): **program attribution** — does this award execute this program
element? — judged from what the award records buying (its own description, its
FPDS acquisition-program tag, the DoD announcement, or the subaward that names
the work) against the work the program owns — its narrative, its project
titles, or the program its tag names — not from whether the linking rule
fired. The page names that question beside the figures, and gate 24 leg n
fails a build whose figures carry any other rubric or whose paragraph omits
it. Each sampled link is counted under the tier it publishes under TODAY, not
the tier it carried when it was drawn —
`fpds-ap+account` was withdrawn hours after the 2026-09-04 draw and its links
moved into the `fpds-ap` medium tier, so counting by the drawn method printed a
figure for a tier no reader can meet. A sampled link the corpus no
longer publishes counts in neither direction. A study run may re-judge one
stratum only: each tier's figure comes from the latest run that judged that
tier, a re-measurement replaces the number it corrects and never pools with it,
and the page states every study date it draws on.

Tiers with no published figure are NAMED on the page rather than left silent.
The page's sentence, mirrored: "No precision figure is published for the
remaining tiers a reader can meet — account, account+tokens. Those rest on an
appropriation-account match, narrowed by a hand adjudication of the award or by
keyword overlap; how often that association names the right program has not
been independently measured for these tiers." Both halves — the tier list and the
narrowing each tier adds — are derived from the same `unmeasured` array, so a
tier that gains a figure stops being described as unmeasured in the same build.
The `account` narrowing says "a hand adjudication of the award", not "that
pinned the pair" (its earlier wording): measured 2026-09-11, all 442 published
`account` rows publish because of an adjudication, but 426 of them carry
`darpa_unpinned` / `unpinned-pool` with an empty basis — the adjudication
explicitly did NOT pin the pair; only 16 are `pinned`. The account/sub-agency
tier's first sample (2026-09-04) was judged only on whether the mechanical rule
had fired — the appropriation account, the sub-agency, the contract-number
prefix — and not on whether the award paid for this program; those 60 verdicts
are stored under the `rule-fired` rubric for audit and excluded from every
published figure by the rubric filter, not by a hand-named list. A fresh
60-link sample (drawn as `2026-09-05`, seed 20260905, with the award's
description and the program's narrative, project titles and lexicon names in
each packet) was judged on program attribution by two independent adversarial
lenses per packet — an attribution judge and a skeptical refuter, arbiter on
disagreement, default refuted (120 judgements, 0 disagreements) — and
**0 of 60** is the figure the page prints. Under that rubric a link confirms
only when the award's own record names work the program element's narrative or
project titles own; no sampled link cleared it — several awards name a
different DARPA effort outright, and what the reviewers found in common
between award and line was the linking rule itself (the appropriation account,
the DARPA sub-agency, the HR0011 contract-number prefix).

**Derived figures are labeled derived.** Any figure computed from published
rates or published subtotals — rather than directly reported in a source
document — is labeled as derived wherever it appears.

**Contractor concentration is computed on two bases and published on one.**
Both bases — high-confidence links alone, and every published link — are
computed from the same crosswalk and ship in the downloadable warehouse with
derived citations, but a program page publishes only the high-confidence-only
figures, and only over at least three such awards across two or more contractor
families holding positive obligations with positive net linked dollars; below
that floor it states the absence rather than substituting the wider figure.

---

## 5. Known limitations

**FY attribution is approximate.** Contracts execute across multiple fiscal
years; our current method assigns links based on which fiscal years' award
transactions share the same federal account code. A multi-year contract may be
partially attributed to a budget line it does not fully correspond to.

**Losing bidders are not in federal data.** FPDS records how many offers were
received for a competed contract but does not name unsuccessful bidders. We
show offer counts and competition type; we do not name losing bidders.

**Company family grouping by name inference can err.** Acquired, divested, or
renamed subsidiaries may be grouped incorrectly. Method and confidence are
always exposed. Corrections create superseding records; the original is
retained, not deleted.

**Improper-payment dollar figures are derived.** They are computed from
OMB-published rates times published outlays and carry the same uncertainty as
the underlying rate estimates.

**State comparables depend on category mappings.** Mapping two states'
accounting codes to shared categories involves judgment. We publish the mapping
tables; treat cross-state comparisons as directional.

**Classified programs are absent.** DoD classified budget lines are not in
public J-books or USAspending. Our figures do not cover classified spending.

**Data-as-of dates vary by source.** USAspending updates monthly; GAO
high-risk is biennial; J-books are annual. Every table shows a "data as of"
date. Numbers on the same page may reflect different time periods.

---

## 6. Corrections

If you find a number that appears wrong, send us the citation that contradicts
it and we will investigate. We follow a supersede-not-delete policy: a
corrected record is marked superseded and a new record takes its place. The old
record is retained and accessible. Permalinks continue to resolve permanently;
they show the current best value alongside the correction history if one exists.

---

## 7. Cite us / bulk data

When citing a specific figure, include the source citation displayed alongside
it: document title, fiscal year, page or XML element path, and the date we
retrieved the file. USAspending-derived figures cite the archive file name and
SHA-256 hash; J-book figures cite the PDF title, page number, and XML element
path.

Bulk data exports (Parquet files with data dictionaries) are available for
researchers and include the same provenance metadata that backs every on-screen
figure. Contact us for access or consult the project repository for the export
schema.
