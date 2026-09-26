<!-- Written 2026-09-12 from the iteration-8 copy panel: three writers (wire
desk, museum label, civic plain language) judged by a reporter, a defense
analyst and a citizen; the wire desk won 126–109–108. Log: DESIGN-CRITIC-LOG.md. -->

# VOICE — how Fiscal Receipts writes

Fiscal Receipts speaks as a research desk that has read the budget books and is
handing the reader the page. It addresses three people with one sentence: a
reporter on deadline, a defense analyst who knows what an R-1 is, and a citizen
who does not — so every sentence is plain, specific and short. It states what a
page holds, which document each figure was read from, and what is missing. It
never invites, sells, promises or explains why the reader should care.

Sentences are declarative and lead with the number when there is one. Nouns are
the site's fixed labels, not synonyms. Documents are named by exhibit (P-1, R-1,
P-40, R-2, J-book, PB2026), never gestured at as "the source". The register is a
museum label or a ledger's marginal note: cool, exact, unhurried, and willing to
print "No figure" rather than fill a gap.

Someone writing a new program page copies the slot templates in `src/lib/copy.ts`,
fills them from data (title, org, code, exhibit family, counts, edition), adds no
adjectives and no verbs of encouragement, and lets the drawing and the figure
carry the interest. Nothing in this document is hand-tuned for one program: every
rule below is a template, a token or a formatter, and the copy gate
(`site/scripts/gates/copy.mjs`, gate 27) enforces it on every built page.

## Rules

1. **Length caps by slot.** h1 ≤ 8 words; section title (h2/h3) ≤ 5 words;
   exhibit title ≤ 8 words; eyebrow ≤ 30 characters; deck ≤ 2 sentences and
   40 words; lede ≤ 3 sentences and 50 words; caption ≤ 2 sentences; empty state
   1–3 sentences and ≥ 40 characters (program-skeleton leg b); status message
   ≤ 12 words; button ≤ 4 words; link ≤ 6 words; meta title ≤ 60 characters
   before the " | Fiscal Receipts" template; meta description ≤ 155 characters.
   No sentence in any slot exceeds 22 words.
2. **One finite verb per sentence.** No independent clauses joined by ", and",
   ", but", ", so" or a semicolon. Split, or cut a clause. A verbless label
   sentence ("Six aircraft since 1972 and six Air Force P-1 and R-1 lines.") is
   allowed once per slot, as the first sentence.
3. **No triplets.** A slot never holds three consecutive sentences of ≤ 7 words,
   and never three parallel items that each begin with a verb. Two items or four.
4. **No fragment stacks.** Two consecutive sentences of ≤ 3 words fail.
5. **Declaratives only.** Headlines, section titles, ledes, decks, captions,
   eyebrows, labels and hints are declarative sentences or noun phrases; none
   begins with a base-form verb. Imperatives live only in button text and in the
   final sentence of an empty state that offers a next step.
6. **Links name destinations; buttons name actions.** A link is a noun phrase in
   sentence case with an optional trailing "→" and never begins with a verb; a
   button is verb + object with no article. The arrow never appears inside a
   heading and never anywhere but the end of a link.
7. **Number-first.** When a sentence carries a count, a year or a figure, the
   number is its first token, or its second after a single article ("The five
   largest changes…"). Counts are interpolated from data (site_meta.counts,
   array lengths, exporter meta) through `count()` / `countWord()`, never typed.
   One to nine spell out in headings, decks and ledes (`countWord`); digits with
   thousands separators everywhere else (`count`). A typed digit run in copy.ts
   that is not a PE/BLI code, an FY, a PB year or "3D" fails the gate.
8. **No dollar figure in uncited copy.** A dollar amount is always a <Cite> inside
   [data-amount]. Copy refers to it as "the figure" or by its measure ("the
   FY2026 request"); "$" never appears in copy.ts.
9. **Name the document.** A lede, deck, caption, empty state, note or link that
   says "source", "document", "record", "book", "row", "filing" or "narrative"
   names the specific one in the same sentence — P-1, R-1, P-1R, P-40, R-2,
   J-book, PB{yyyy}, USAspending, Senate LDA filing, GAO high-risk list, SAM.gov,
   FPDS, defense.gov announcement, or an editorial source's own short title
   ("F-15 Eagle fact sheet"). Headlines, tabs and buttons are exempt.
10. **Fiscal years** are "FY2026" in sentences and "FY26" only in table headers,
    chips and TRAJECTORY_FY_LABEL ("FY25→26"); editions are "PB2026"; ranges use
    an en dash ("FY2017–FY2026"). Never "fiscal 2026", "'26", "the 2026 budget"
    or a bare year for a fiscal year.
11. **Money verbs.** A budget figure (TOA, P-40, R-2) is "requested", "enacted",
    "reported as actuals" or "funded" — never "spent", "paid", "cost", "priced"
    or "bought". USAspending figures are "obligations" or "awards", never
    "spending". The one "spending" in a budget context is the fixed sentence
    "Missing coverage is not zero spending." — the site's coverage doctrine,
    held by tests and by the program-skeleton gate. It is not paraphrased.
12. **Second person** ("you", "your") appears only in status messages, the coach
    mark and the research tray; never in an h1, h2, eyebrow, lede, deck, caption
    or meta field.
13. **First person** ("we", "our", "us") appears only in the fixed phrases "in our
    corpus" and "the FY2026 J-books we ingested", and in body prose on
    /methodology/, /coverage/ and /about/.
14. **Em dash:** at most one per sentence, never sentence-final, never as a list
    separator. Label segments join with " · "; eyebrows join with " / "; a reason
    follows a colon.
15. **Ampersand:** " & " only in labels, tabs, table headers, nav items and
    section titles of ≤ 4 words; sentences use "and". Unspaced acronyms (RDT&E,
    O&M, R&D, T&E) are fine anywhere. No serial comma.
16. **Sentence case** for every authored heading, label, tab, button, table
    header and nav item; capitals only for proper nouns, acronyms and document
    names (the citation-kind labels "Budget Justification PDF", "Budget Workbook",
    "Derived Figure" are document names).
17. **Terminal punctuation:** a full-sentence h1 ends with a period; a noun-phrase
    heading, label, tab, link or button has none; ledes, decks, captions, notes
    and empty states end with periods. No question marks in headings, no
    exclamation marks anywhere, no ellipses in copy.
18. **Fixed nouns are never paraphrased:** a number is a "figure"; the citation
    panel is the "receipt"; a PE/BLI is a "line" ("program element" / "budget
    line" in full); an aircraft type is a "variant"; a USAspending row is an
    "award"; an LDA record is a "filing"; "family" is always qualified (corporate,
    aircraft, exhibit, contractor, program, lineage). "stat", "data point",
    "metric", "insight", "number" (in prose) and "model" (for a variant) fail.
19. **Empty states follow one grammar:** "No {noun} for {scope}. {Named document}
    carries no {row|entry|narrative} for {peBliLabel}.[ Missing coverage is not
    zero spending.]" The identifier lockup is the subject of the second sentence.
    Never a dash, "N/A", "none", "no data" or a blank cell as a value.
20. **Disclaimers are single fixed sentences** reused verbatim from `FIXED` in
    copy.ts, one per meaning: illustration, allocation, basis, funding authority,
    correlation, missing coverage, every-figure, site export. A second wording of
    any of them fails.
21. **Superlatives carry their scope** in the same sentence: "largest", "biggest",
    "first", "only", "every", "all" must be followed by "in our corpus", "in the
    J-books", "among the {n} …", "FY{yyyy}" or an explicit denominator. "All"
    before an interpolated count ("All 24 agencies") is scoped.
22. **Interface verbs:** figures and receipts "open"; controls are "selected"; a
    source is "read"; a model "rotates". Nothing is "clicked", "tapped", "hit" or
    "explored".
23. **One formatter each** for plurals, counts and lockups: count(n, noun),
    countWord(n), callout(i) ("01" … "10"), stamp(n, domain) ("01 / Sea"),
    eyebrow(group, item), peBliLabel(kind, code), fyLabel(fy), pbLabel(edition),
    orgLabel(org, form), exhibitFamilyPlain(family), citationKindLabel(kind),
    measureHeading(fy, measure). "(s)" plurals fail.
24. **Every reusable slot reads from `src/lib/copy.ts`** or the SECTION_LABELS
    map keyed by PROGRAM_SECTIONS. A JSX string literal of more than three words
    inside an h1/h2/h3, lede, deck, eyebrow, caption, empty state, link or button
    fails the copy gate. Cited sentences (topics[].text, scope notes, absence
    notes, the receipt-moment reconciliation sentence, the [data-stat] corpus
    sentence, the WHO lobbying template, what-it-is tails, ServiceBooksNote,
    reconciliation badges, coverage.ts notes, VARIANTS editorial prose) stay
    beside their data and are read-only to copy.ts.
25. **One vocabulary per surface:** header and footer both render SITE_NAVIGATION;
    the 13 program sections read one label map {chapter, heading, short}; the
    F-15 topics read f15-family-data TOPICS[].label; record titles read
    RECORD_CONFIG.purposeLabel; feed event types read the exported EVENT_LABEL;
    measure words read one map. "Read source passage", "Share view", "Official
    document", "Inspect in 3D", "Field guide", "Follow the dollar" are the only
    spellings of those things.
26. **A rewrite ships with its regex** (copy.mjs) and moves every test or gate
    that held the old string in the same commit.
27. **Plate accessible names** are "{exhibit.name} plate[, {crop}]"; an svg
    <desc> says only what is drawn (gate 2 contract) and never a figure.
28. **Meta titles** are "{title} ({PE|BLI} {code}) · {orgShort}". When that
    exceeds 60 characters (365 of 1,938 titles today; longest title 99 chars),
    the title is cut at a word boundary with "…" and the lockup is never cut.

## Slot patterns

| slot | pattern | example |
|---|---|---|
| home h1 | `{count} {corpus noun}, each with its source.` — count from site_meta.counts as the [data-stat] link | 1,938 defense budget lines, each with its source. |
| program h1 + identity line | `{title as printed}` / `{orgLong} · {peBliLabel} · {exhibitFamilyLabel}` | Virginia Class Submarine / Navy · BLI 2013 · Procurement |
| family h1 | `{Designation} {qualified family noun}` | F-15 aircraft family |
| masthead eyebrow | `{Group} / {Item}` — exactly two segments, ≤ 30 chars | Field guide / Air |
| plate stamp | `stamp(n, domain)` → `{NN} / {Domain}` | 01 / Sea |
| callout label | `callout(i) + ' ' + topic.label` | 02 Ground & training support |
| section title | noun phrase ≤ 5 words, count interpolated | Largest FY2025–FY2026 changes |
| section lede | number-first statement of what is listed and how ordered; what the figures are and which document | 24 agencies, ranked by the number of programs each has in our corpus. The FY2024 column sums each program's R-2/P-40 actuals. |
| deck | `{count} {things} {scope}[, {rule}]. {Where each figure opens, naming the document}.` | Six aircraft since 1972 and six Air Force P-1 and R-1 lines for development, procurement and modification, not allocated by variant. Each figure opens to the P-1 or R-1 row it was read from. |
| exhibit title | `{orgShort} {exhibitFamilyPlain}, {peBliLabel}` | Navy procurement, BLI 2013 |
| exhibit caption | `{what is drawn}. ` + FIXED.illustration | A Virginia-class submarine in a drydock under a gantry crane. Numbered callouts are funding topics from the program's J-book narrative, not components or prices. |
| exhibit funding note | `The figure is this line's {TOA ∣ J-book detail} figure for {fyLabel}, read from the {P-1 ∣ R-1 ∣ R-2/P-40} of {pbLabel}.` — from card.basis, never hard-coded | The figure is this line's TOA figure for FY2026, read from the P-1 of PB2026. |
| receipt line | `{title} · {orgShort} · {fyLabel} {Exhibit} · {pbLabel} ↗` | Virginia Class Submarine · Navy · FY2024 P-40 · PB2026 ↗ |
| empty state | `No {noun} for {scope}. {Named document} carries no {row∣entry∣narrative} for {peBliLabel}.[ FIXED.missingCoverage]` | No FY2026 line items for this program element. The FY2026 R-1 and P-1 workbooks carry no row for BLI 2013. Missing coverage is not zero spending. |
| absence note (other basis) | `No {basis} figure for {fyLabel}. {Other place} carries a separate {other basis} figure. The bases are not interchangeable.` | No TOA workbook figure for FY2026. The program dossier carries a separate J-book detail figure. The bases are not interchangeable. |
| coverage line | `{n} of {d} {things} {verb phrase}.` — pair gate-held (coverage G2) | 412 of 1,938 program elements carry at least one matched award. |
| wayfinding link | `{Destination} →` ≤ 6 words | All 24 agencies → |
| related-line link | `{title} · {peBliLabel} →` | F-15EX · BLI F015EX → |
| editorial source link | `{source.shortTitle} →` — shortTitle is a field on EDITORIAL_SOURCES | F-15 Eagle fact sheet → |
| button | `{Verb} {object}` ≤ 4 words | Open budget receipt |
| status | `{Noun} {past-tense verb} {where}.` ≤ 12 words | Receipt saved on this device. |
| meta title | `{title} ({peBliLabel}) · {orgShort}` (rule 28) | Virginia Class Submarine (BLI 2013) · Navy |
| meta description | `{title} ({code}), {orgShort}. {exporter basisTail}[{tierTail}]` + FIXED.everyFigure | see §3 |
| table header | `{Noun}[ / {noun}]` ≤ 3 words; FY26 allowed | Year / status |
| tab | noun phrase ≤ 3 words | Budget & receipts |
| disclosure summary | `{Noun phrase}[ {count}]` | Sources & mapping evidence |
| control hint | two declaratives, one verb each | Drag or arrow keys rotate the model. +/− zooms. |
| coach mark | what the underline does; what the toggle does | A dotted underline marks a figure that opens to its source. The Fact IDs toggle shows or hides the id chips. |
| footer export | fixed | Site export September 12, 2026. Source dates vary by dataset. |

## Fixed sentences (`FIXED` in copy.ts — verbatim, one per meaning)

- illustration: "Numbered callouts are funding topics from the program's J-book narrative, not components or prices."
- allocation: "Shared records are not allocated by variant."
- basis: "Reported totals and any discretionary/reconciliation splits are alternative views of the same line; do not add them together." (cited, gate-held wording — the one semicolon rule 2 allows)
- fundingAuthority: "Funding authority, not payments or aircraft unit prices."
- correlation: "Correlation is shown, not causation."
- missingCoverage: "Missing coverage is not zero spending." (the doctrine sentence, rule 11)
- everyFigure: "Every figure links to the document it is printed in."
- siteExport(date): "Site export {date}. Source dates vary by dataset."

## Label vocabulary (changes from the previous draft in bold)

- answer labels: What it is · What changed · Who gets it
- measures: Actuals · Enacted · Request · Total · Change · Base Request; chips lower case (discretionary request, reconciliation request, supplemental, base request, all prior years, enacted (request column), enacted (book total), actuals (base + OCO), request (base + OCO total)); headings `FY{yyyy} request | enacted | actuals`
- basis chips: P-1 TOA · R-1 TOA · P-1/R-1 TOA · P-40 detail
- identifiers: PE {code} · BLI {code} · Organization code {org} (tooltip)
- exhibit family badge: RDT&E · Procurement · O&M · MILPERS · Budget; plain form (sentences, exhibit titles): research and development · procurement · operations and maintenance · military personnel · budget
- org: short = Army · Navy · Air Force · {code}; long = AGENCY_NAMES[code] (agency-names.ts) — **one pair, no third map**
- citation kinds: Budget Justification PDF · Budget Workbook · LDA Lobbying Filing · Derived Figure · USAspending Query · State Open Data Query · State Source File · J-book Narrative · DoD Contract Announcement
- feed event labels: **EVENT_LABEL exported from feed-model.mjs** (yoy_swing → Year-over-year swings; zeroed_fy2026 → Zeroed in FY2026; concentration_shift → Award concentration shifts; new_entrant → New defense contractors; request_vs_actuals_gap → Request-vs-actuals gaps)
- reconciliation badges: Reconciled · Partial Reconciliation · No detail to reconcile · Summary figures (R-1/P-1)
- tier tails: Summary figures only · History only
- confidence: High · Medium · Low (never published); High confidence (registry fact) · Medium confidence (name inference)
- nav groups (header = footer): **Budget** · Investigate · Places & agencies · Data & methods
- nav links: **Field guide** · Programs · Budget over time · Companies · Signals · **Follow the dollar** · Program lineage · Lobbying filings · Corporate families · Districts · Agencies · Data explorer · Downloads · Coverage · Methodology · Glossary · About
- primary bar: **Field guide** · Programs · Companies · Districts · Signals
- section labels (chapter = heading): Overview · Budget figures · Budget history · Program lineage · Purpose · Justification · Line items · Follow the dollar · Related awards · Lobbying · Oversight · Research dossier · Primary sources; shortcuts: Overview · Budget & history · Program detail · Contracts & influence · Oversight · Sources
- F-15 topics (one set): Aircraft & retrofits · Software & integration · Electronic warfare · Tooling & support
- F-15 records (RECORD_CONFIG.purposeLabel): Software, integration & testing · F-15EX development · EPAWSS development · Fleet modifications & tooling · Aircraft, modifications & support · F-15E EPAWSS installation
- F-15 categories: Aircraft procurement · Research & development · Modification procurement
- F-15 tabs: Aircraft · Budget & receipts · Countries & orders · **F-15 history**
- actions: Open budget receipt · Read source passage · Share view · Save receipt / Saved to research · Copy all citations · Inspect in 3D · Solid view / Blueprint view / Still image
- absence values: No figure · Not covered
- plate stamps: {NN} / {Domain}; callouts: {NN}

## Examples (corrected where the earlier draft broke its own rules)

| before | after | why |
|---|---|---|
| Explore the aircraft. Understand what gets funded. Follow every budget figure to its source. | Six aircraft since 1972 and six Air Force P-1 and R-1 lines for development, procurement and modification, not allocated by variant. Each figure opens to the P-1 or R-1 row it was read from. | rules 3, 5, 7, 9; the earlier example said "budget records" without naming a document |
| A different way into the budget. | What three budget lines fund | banned subhead; countWord(EXHIBIT_PILOTS.length) |
| Select the work. Choose a year. Open the original source. | Each figure is one record's TOA (total obligation authority) for one fiscal year, read from that edition's P-1 or R-1 workbook. | rules 3, 4; one gloss, once |
| Programs with the biggest funding swings … — click a figure … | The five largest changes between FY2025 enacted and the FY2026 request, in dollars. Increases and decreases rank together without a direction filter. Each delta's citation shows the derived formula and both workbook inputs. | rules 1, 14, 21, 22; the earlier example joined two clauses with ", so" |
| 24 organizations … FY2024 is a derived sum; its citation lists the rows added. | 24 agencies, ranked by the number of programs each has in our corpus. The FY2024 column sums each program's R-2/P-40 actuals. Its citation lists the J-book rows added. | the earlier example used a semicolon (rule 2) |
| See what your tax dollars build. | 1,938 defense budget lines, each with its source. | rules 5, 12; count from site_meta.counts.programs |

## Conflicts resolved (owner-visible)

1. The vocabulary fixed "Explore" as a nav group and primary item; the ban wins: "Budget" / "Field guide".
2. "Visual field guide" and "Field guide" were two spellings; "Field guide" everywhere (the /explore/ h1 adopts it in the same commit).
3. "Family history" fails the bare-family regex; the tab is "F-15 history".
4. Rule 7 now allows one article before the number; the movers example is split on ", so"; the agencies example loses its semicolon; the family deck names P-1/R-1.
5. "Missing coverage is not zero spending." stays where tests hold it; retirement is its own commit.
6. Exhibit `name` reads the programs.json title ("F-35", "F-35 C2D2"); the assembled exhibit title carries the org/family/code the old descriptive names did.
7. Editorial source links render `source.shortTitle →` (a new field beside `title` in EDITORIAL_SOURCES) rather than the full title (7 tokens, and a news headline carries a verb) or a generic "Aircraft source →" (unnamed).
8. `exhibitFamilyPlain` is `answerFamilyPlain()` with " & " → " and " — no third map.
