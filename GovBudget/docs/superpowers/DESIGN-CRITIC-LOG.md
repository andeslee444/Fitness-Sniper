# Design critic loop — homepage + F-15 program page

Started 2026-09-10. Implementer: Kimi K3 (`kimi-k3[1m]` via `kimi-fe`). Critic: a
fresh-context Claude Fable 5.1 agent that sees only four screenshots per iteration
(`/` and `/families/f-15/` at 1440 and 390) — never code, never a prior critique.
Same critic prompt every time. Target: the critic independently scores ≥ 9/10.
The critic is not told the target.

Method per iteration: capture → critic (fresh) → Kimi implements the biggest gaps →
fast gates (tokens, motion, lint) → next capture.

Screenshots and the fixed critic prompt live in the session scratchpad; only the
scores, critiques, changes and lessons are recorded here.

## Score trajectory

| Iter | Score | One-line verdict |
|---|---|---|

## Iterations

<!-- appended by the loop; one section per iteration -->

## What moved the score — and what didn't

<!-- written after the loop from the full record -->

## Run 1 — 2026-09-11 — 8 iterations, all 5.5, NOTHING CHANGED (orchestration failure)

**What happened.** Eight full iterations ran. Every critic score was 5.5. All nine
screenshot sets were byte-identical. Kimi's eight sessions each ran ~9 minutes,
invoked `frontend-design`, read 13–23 files and ran up to 18 greps auditing the gates
and tests — and made **zero** Edit or Write calls. Kimi was still in reconnaissance
("Let me check the gates I'll need to pass") when it was killed: the orchestrating
subagent's Bash had a 10-minute ceiling, the harness backgrounded the process, the
subagent ended its turn to "wait", and a workflow subagent that ends its turn is
terminated along with its children.

**Lessons.**
- Kimi K3 at `max` effort front-loads a long, careful audit before touching anything.
  CLAUDE.md already states every constraint it was grepping for. Give it a time budget
  and tell it not to re-derive the rules.
- Long-running external processes must be driven from the main session
  (`run_in_background` survives across turns there), never from a workflow subagent.
- Eight fresh-context readings of the *same* design are not wasted — they are a
  consensus critique. Tallied below.

**Consensus across 8 independent critiques of the baseline** (theme — raised in N/8):

| Theme | N/8 |
|---|---|
| Homepage abandons the field-guide language below the fold; becomes a dashboard template | 8 |
| 24-card agency grid should be a ruled typographic index | 8 |
| Badge / chip soup around citations | 8 |
| Fold has no single focus; headline undersized for 1440 | 8 |
| Mobile is squashed desktop, not its own composition | 7 |
| Stats row of big-number counters | 6 |
| Three stacked nav rails on the F-15 page before any content | 6 |
| Two lists of the same three programs ("Largest changes" + "Changes worth examining") | 6 |
| Palette split between pages (slate homepage vs paper F-15) | 5 |
| 3D render reads as a toy | 3 |

The critic scores the F-15 page alone at **7** in 5 of 8 readings. The site is graded
on its worst half.

**Baseline critic verdict (iteration 1, verbatim):** The F-15 page is a genuine
catalogue with real taste and would score 7 alone; the homepage promises that catalogue
for 700px and then becomes a dashboard template, and the mobile versions are squashed
desktop — the site's identity is decided by its worst half.

## Run 2 — Iteration 1 — homepage brought under the F-15 register

**Brief:** the four 8/8-consensus gaps, with the critic's own fixes verbatim; 30-minute
budget, "code within 8 minutes", the one permitted audit is grepping a `data-*` name
before touching its element; one authorised palette exception (lift the F-15 module's
local `--paper/--ink/…` values into `globals.css` as `--stage-*`). Scope: homepage only.

**Kimi's session:** 24 minutes. Skill×1, Read×12, Bash×27, Edit×7, Write×5. It ran
`npm run build` on its own (8,369 pages) before reporting.

### Kimi's report (verbatim)

All gates green (tokens ✓, motion ✓, lint 0 errors; build ✓, 8,369 pages). Report:

**Files changed**

- `src/app/globals.css` — added `--stage-paper/sheet/ink/muted-ink/rule/accent/muted`, values lifted verbatim from `f15-family-browser.module.css` (the authorized exception). Gap 1's palette unification.
- `src/app/home.module.css` — rewritten: `.home` re-points semantic tokens to the `--stage-*` set (same mechanism as F-15's `.family`); hero headline to `clamp(3rem, 8.4vw, 7.75rem)` with the plate bleeding to the right viewport edge via spine-math padding (no `vw`, no scrollbar drift); search is a single underlined field; persona row is one ruled line of three serif links; stats are one mono line; `.ledger`/`.agencyIndex` are hairline-ruled with delta bars and right-aligned tabular figures; mobile collapses the index to 6 rows + "All 24 agencies". Gaps 1, 2, 4.
- `src/app/page.tsx` — restructured to hero → persona ruled line → receipt band → ink band → stats line → ruled movers ledger (inline delta bars scaled to the max swing, reconciliation pill → italic qualifier, `data-mover-recon`/`disc-down` kept) → ruled 3-column agency index → ruled feed rows; all ↗ arrows removed except one `→` on "Browse all programs"; every gate-held attribute preserved (`data-stat` links, `data-mover-row`, `data-mobile-pair-*`, `data-primary-value`, `data-source-text`, `data-xml-path`, `data-agency-code`, `persona-row` testid). Gaps 1–4.
- `src/components/receipt-moment.tsx` + `.module.css` — card chrome (border, accent spine, shadow, filled button) replaced by the ruled sheet band; figure at display size (`clamp(2.75rem, 6vw, 4.75rem)`); P-40 action is a quiet outlined control; DOM order and `data-testid="receipt-moment"` untouched so the G4 first-cite contract holds. Gaps 2, 3.
- `scripts/gates/token-allowlist.json` — removed the two stale entries (`#395667`, `#10202b05`) whose values no longer exist.

**Gap not fully closed:** Gap 3 at the chip level — `cite.tsx` is untouched by design: the Fact-ID/basis chips were already inline mono text, and the soup came from card chrome, which is gone. Two deliberate deviations: "Changes worth examining" was *not* merged into the movers ledger — they are different datasets (event-ordered signals vs. |delta| ranking; the three-program overlap is coincidental, and merging would fabricate sameness), so both were unboxed instead; and on mobile the ledger ID stays an inline muted prefix rather than a true sub-line, because the mobile gate's `data-mobile-pair` label/value contract constrains that row's structure.

### Verified independently

- files changed: `globals.css` (+7 `--stage-*` tokens), `home.module.css` (35 uses of
  `var(--stage-*)`), `page.tsx`, `receipt-moment.tsx` + `.module.css`,
  `token-allowlist.json` (−2 stale entries)
- tokens gate PASS · motion gate PASS · lint clean
- `/` and `/families/f-15/` both HTTP 200 on the dev server
- homepage screenshot changed vs baseline: yes · F-15 screenshot: unchanged (in scope)
- second Kimi run needed: no

**Two deliberate deviations Kimi argued for, both defensible:** it refused to merge
"Changes worth examining" into the movers ledger because they are different datasets
(event-ordered signals vs |delta| ranking — "merging would fabricate sameness"), and it
kept the mobile ledger ID inline rather than as a sub-line because the mobile gate's
`data-mobile-pair` contract constrains that row. Both are the anti-proactiveness rule
working as intended: it stopped and explained rather than improvising.

**Seams visible to me before the critic:** "your" orphaned on its own line in the 4-line
headline at 1440; the inline delta "bars" in the ledger read as tiny +/− glyphs, not bars;
the dark band still has three identical illustration cards.

### Critic — Run 2 / Iteration 1

## 1. Aesthetic

This is reaching for the **editorial data atlas**: the numbered-plate discipline of a museum catalogue raisonné or a Jane's reference volume ("AIRCRAFT / 001", "FAMILY REGISTER 001", "01 / SEA"), set on Monocle-warm cream paper with a transitional display serif, and punctuated by low-poly pale-mint models sitting in navy blueprint vitrines — Apple-keynote product reveal crossed with a naval architect's lines drawing. Type-wise it's the Pudding / NYT Graphics civic-journalism register (serif display, sans body, mono for identifiers). The intended feeling is *reverence made accountable*: public money rendered as a tangible object you can rotate, with a receipt underneath.

## 2. Studio execution

The best studio would keep exactly three things — the cream/ink/navy palette, the mint models, the serif — and rebuild everything around **one object, one receipt** per viewport.

**Homepage.** The fold would be a single composition: the Virginia-class submarine full-bleed across all 1440px, the headline "See what your tax dollars build." set in two lines over its upper-left, and directly beneath the hull, as the vitrine's caption, the receipt: *$10.7B — printed on P-40, PB2026, page N*. The search field is the only other element. That's the whole proposition in one glance: object → number → source. Everything currently between the hero and the field-guide band (the three-column "Understand / Find / Investigate" row, the standalone $10.7B stat block with its pills and button) would be gone, absorbed into that caption. Below the fold: four movements, not nine — the field guide (models breathing at full width, not boxed in three identical frames), one ledger of FY25→26 changes, the agency index as a real table, footer. The "Changes worth examining" list would not exist as a second section because it's the same three programs as the ledger above it.

**Program page.** The studio would treat the F-15 family as a *timeline*, because it is one: A (1972) → EX (2021). The variant selector becomes a horizontal chronology with delivery years, left-aligned, replacing the six evenly-justified tabs. The aircraft is named once at the top ("F-15 / The Eagle family.") and once as the wordmark inside the vitrine; the third repetition as an H2 is deleted. Sub-sections (configuration / cockpit / electronics / support) become a left rail beside the prose, so the reader hits content 300px sooner. And the budget ledger for the selected variant would be visible on this page beneath the aircraft prose — a "model program page" that ends after one paragraph and a "Next →" is not a model, it's a cover.

**Mobile.** Would be its own composition: the model is the brand, so the submarine leads the mobile homepage full-bleed, headline beneath it; the variant picker on F-15 is a chronology scroller with a visible peek and edge fade; sub-sections collapse to a single dropdown rather than a 2×2 chevron grid.

**Between the pages.** Same header on both. Right now the homepage has a five-item nav plus "Fact IDs"; the program page has "Explore ⌄" alone — they read as two products.

## 3. Gaps

1. **Homepage has no single idea above the fold.** (home-1440, y 0–1200.) Headline, vitrine, three-column feature row, and $10.7B stat block all compete; the vitrine's bottom edge (~y 800) collides with the feature row's top with no breathing room. Fix: full-bleed submarine hero with headline over it; the $10.7B becomes the vitrine's caption line; delete the three-column row.

2. **The F-15 page announces the aircraft three times in one viewport.** (f15-1440: "F-15 The Eagle family." ~y 200; "F-15EX" wordmark ~y 580; "F-15EX Eagle II" H2 ~y 1120.) Fix: cut the H2; let "2021 · FIRST AIR FORCE DELIVERY" lead straight into the description.

3. **Three stacked navigation layers before content.** (f15-1440: variant row y 310–380, section tabs y 400–440, sub-section tabs y 990–1045.) Fix: variants → timeline; sub-sections → left rail beside the prose.

4. **Mobile homepage drops the hero illustration entirely.** (home-390: first model appears at ~y 1100 of 5343.) The strongest asset vanishes at the width most readers arrive on. Fix: submarine full-bleed at the top.

5. **The program page is thin.** (f15-1440, y 1050–1450.) One paragraph, two accordions, then "Next." The receipts are behind a tab. Fix: a five-line ledger preview for the selected variant on this page.

6. **Headline rag.** (home-1440 hero.) "See what / your / tax dollars / build." strands "your" alone. Fix: explicit two-line break "See what your / tax dollars build." at a slightly smaller size.

7. **Duplicate sections.** (home-1440: "Largest FY25→26 changes" y ~2050–2650 and "Changes worth examining" y ~3550–3850 list the same three programs — Long Range Kill Chains, GBSD EMD, LRS-B.) Fix: one ledger; "worth examining" becomes an annotation on rows, not a second list.

8. **Citation badge soup.** (home-1440, $10.7B block y ~940–1200.) Dotted underline + `#0208475b` + two pills + a second hash + two more pills + a floating right button. On mobile these wrap into four lines of chips. Fix: one chip: "P-40 · PB2026 · p. N"; hashes live inside the citation panel.

9. **The "− +" delta glyphs.** (home-1440 ledger right column; on home-390 they stack as separate lines above the amount.) They read as buttons. Fix: signed figure in tabular numerals, increases in the rust accent.

10. **Variant tabs justified across the full width with "swipe to switch" on desktop.** (f15-1440 y 320–380.) 200px gaps between six small labels; the hint is for touch. Fix: left-aligned chronology, hint only on touch.

11. **Mobile tab overflow with no affordance.** (f15-390: variants show C/D/E/EX with A/B hidden at y ~430; section tabs truncate to "F" at y ~490.) Fix: peek + edge fade, or a dropdown.

12. **"Sound off" and "Share view" collide on mobile.** (f15-390 y ~360 — zero gap between the two.) Fix: 24px gap or stack.

13. **Orphan accent color.** The rust appears exactly once (F-15EX underline). Fix: make rust the sitewide "this is a source" color — citation chips, ledger deltas, "view →" links — or remove it.

14. **Mono is used for everything.** Eyebrows, PE IDs, breadcrumbs, stat strip, panel labels, disclosure labels ("Budget connection"). It no longer signals "identifier." Fix: mono for PE numbers, hashes, and doc/page citations only; eyebrows go to small-cap sans.

15. **Agency index alignment.** (home-1440 "Browse by agency" y ~2780–3450.) Multi-line names ("Defense Counterintelligence and Security Agency") wrap to three lines while their count/amount sits on line one; the three columns have no shared baseline. Fix: a single-column table, tabular figures right-aligned, sorted by FY24 TOA.

16. **Serif-to-sans tone drop under both headlines.** The deck "Explore the aircraft. Understand what gets funded…" (f15-1440 y ~270) is body-size sans directly beneath a 96px serif. Fix: deck in the serif at ~22px, ink at 70%.

17. **Two affordances for one action in the vitrine.** (f15-1440: "Activate to rotate and inspect" mono at bottom-left; "Inspect in 3D | Drag · rotate · explore" bordered button bottom-right.) Fix: one.

18. **Orphan disclaimer band.** (home-1440 y ~3900.) "All figures are cited…" floats as its own section between the last list and the footer. Fold into the footer.

19. **Header inconsistency between the two pages** — see above. Fix: one header.

## 4. AI tells

- Three-column feature row ("Understand a program | Find local connections | Investigate a change").
- Three identical illustrated cards (01/Sea, 02/Air, 03/Cyber) with image + title + tag list.
- Stats strip with big numbers ("1,938 program elements · 130,347 source citations · 200 contractor families · 24 defense agencies").
- Big hero number with badge soup ($10.7B).
- The same section template stamped six times: MONO EYEBROW → serif headline → sans subhead → "→" link at right.
- Arrow links everywhere: "Browse all programs →", "View all →", "view →" ×3, "budget & receipts →".
- Four-column feature list with trailing "›" chevrons (f15 sub-tabs).
- Three separate numbering conceits on two pages ("01 / SEA", "AIRCRAFT / 001", "FAMILY REGISTER 001") — the brutalist-editorial register tic, over-applied.
- Headline-left / illustration-right hero composition — the SaaS template with a nicer frame.
- Disclosure-triangle accordions ("▸ Sources & dates", "▸ Budget connection").
- "Inspect in 3D | Drag · rotate · explore" tooltip-as-button.
- Three-column link footer.

Credit where load-bearing: no gradient blobs, no rounded shadow cards, no hover-lift affordances, square corners throughout, and the model-on-blueprint illustration system is a genuine, ownable idea — it is what keeps this from being forgettable.

## 5. Score

A real identity (the vitrines, the paper, the serif) sitting on top of stock section-stacking. The homepage is a sequence of templates; the program page names its subject three times, stacks three nav layers, then runs out of content; mobile loses the one thing worth looking at. Good professional work would fix the rag and the collisions; this has structural composition problems on both pages.

SCORE: 6/10

## Run 2 — Iteration 2 — the fold as one composition; F-15 to one nav layer

**Brief:** the critic's studio-execution vision verbatim as the target ("one object, one
receipt per viewport"); 12 numbered gaps in priority order; the note that executing fixes
literally capped at 6 and this pass changes structure, not polish.

**Kimi's session:** 51 minutes. Skill×1, Read×20, Bash×42, Edit×21, Write×1.

### Kimi's report (verbatim)

All checks done. The 2 failures are the same funding-workspace absence-rendering tests that fail identically before and after my edits — my F-15 changes are inspect-workspace only (rail, h3, hint class); those tests exercise `chooseRecord`/`selectYear` in the untouched funding workspace, and all F-15/browser files are untracked branch work-in-progress. Home tests (hero, ledger-flips) pass.

---

**Files changed**

- `src/app/page.tsx` — hero rebuilt as one full-bleed composition: submarine plate across the viewport, two-line serif headline over its upper-left, search the only control, receipt docked beneath the hull, persona row as one line of serif links (#1, #2); "Browse all programs →" and the plate's "01 / SEA" label deleted (tells); field-guide section lost its eyebrow and its cards unboxed with a full-width lead exhibit (tells); "Changes worth examining" section deleted — its signals merged into the one FY25→26 ledger as rust-ruled mono annotations on matching rows (extra signals append as rows; all `data-source-text`/`data-xml-path` preserved) (#6); delta bars replaced by signed tabular figures, rust for increases / ink for decreases (#5, #11).
- `src/app/home.module.css` — plate palette lifted into named `--plate-*` props from hexes already allowlisted in this file (no new values); stage/stageInner full-bleed hero with the inset vitrine hairline kept; `--cite-decoration` re-pointed to `--plate-ink` inside the desktop dock only (higher contrast, never lowered); mobile order: plate → headline → search → receipt (#4); persona/personaLine, signalTag, moverUp/moverDown, scopeNote, viewLink styles; three removed hexes reported to the allowlist (#1–#6, #11, #12).
- `src/components/receipt-moment.tsx` — the element IS the vitrine caption now (`data-testid="receipt-moment"` kept; measured fully above fold at 1440×900 → bottom 658, and 390×844 → bottom 770); P-40 jbook_pdf cite remains the first `[data-fact-id]` in DOM order (G4 click leg intact); figure carries `chip={false}`, the fact-id hash element kept in DOM but `display:none`, leaving exactly one visible chip — "P-40 detail · PB2026"; floating "See the P-40 page" button deleted: one action, one affordance (#1, #3).
- `src/components/receipt-moment.module.css` — rewritten as the caption register (kicker/figure/title/printed-line), colors only via `--rm-*` aliases piped from home.module.css (zero raw values; the allowlist is per-file) (#1, #3, #12).
- `src/components/f15-family-browser.tsx` — third naming deleted (variantIdentity `<h3>`; "2021 · FIRST AIR FORCE DELIVERY" leads the description) (#7); "Aircraft / 001" eyebrow deleted (numbering conceit; "Family register 001" is the one kept); variant buttons carry their delivery/first-flight year parsed from the curated `era` strings — no new data (#8); "swipe to switch" hint now `.railHint`, shown only on `pointer: coarse` (#8).
- `src/components/f15-family-browser.module.css` — appended (so it wins the cascade): chronology rail — left-aligned, hairline axis with tick marks, mono years, rust active tick (#8); topic stepper re-placed as a left rail beside the prose via grid, DOM and `data-*` untouched (#9); era eyebrow to small-cap sans (#12); mobile: 24px between Sound/Share, right-edge mask fade + peek on the variant tray and section nav (#10).
- `scripts/gates/token-allowlist.json` — three entries deleted (`#3a5665`, `#a7c8d7`, `#bcdae7` from home.module.css) as the gate itself demands.

**Verification** — tokens gate: pass; motion gate: pass; lint: 0 errors; vitest: 1324 passed, 2 failed (pre-existing, funding-workspace absence rendering — see above); screenshots reviewed at 390/1440 on both pages after scroll-through; fold contract measured numerically at both gate viewports.

**Not closed**

- #11 partially: rust now means "source/signal" on ledger increases, signal rules, view links, and F-15 active states — but citation chips on the navy plate deliberately stay plate-ink (rust `#8a3e24` on `#0a161f` fails contrast), and chips site-wide were beyond scope.
- #12 partially: small-cap sans eyebrows only where I touched (home hero, receipt kicker, F-15 era line); the site-wide mono sweep (stat strip, breadcrumbs, panel labels) was beyond the time budget.
- The F-15 vitrine still has two affordances ("Activate to rotate" + "Inspect in 3D") and the disclosure-triangle accordions remain — both are citation-panel wiring I judged too risky to alter inside the budget.
- Full `npm run verify` not run (needs a production build and binds port 4173; a dev server belonging to another session is live on 3015, which I used for screenshots).

### Verified independently

- tokens gate PASS · motion gate PASS · both pages HTTP 200
- vitest: 1324 passed, 2 failed — both in `f15-family-browser.test.tsx`, funding-workspace
  absence rendering. That test file and both F-15 browser source files are `??` untracked
  (in-flight branch work predating this loop); Kimi's F-15 edits were inspect-workspace
  only. Accepted as pre-existing.
- both screenshots changed vs iteration 1
- Kimi again refused two things inside the budget — the vitrine's double affordance and
  the disclosure accordions — as "citation-panel wiring I judged too risky." Correct call.

**Seams visible to me before the critic:** the `$10.7B` receipt figure is dark ink on the
dark plate and reads as nearly invisible — the single most important number on the page;
the submarine now appears twice (hero, then again full-width in the field-guide band);
the persona row is a thin cream strip pinched between two dark zones; the F-15 variant
rail still spans the full width with wide gaps rather than sitting compact-left.

### Critic — Run 2 / Iteration 2

**1. AESTHETIC**

This is reaching for the printed civic ledger crossed with the museum exhibition catalogue: warm cream stock, a navy "plate" with a cyan blueprint grid, letterspaced small-cap eyebrows in tan, a transitional serif for display, mono for every figure with a dotted leader under each dollar amount, a single vermilion for deltas. The reference points are Bloomberg Businessweek's "how it works" spreads, The Pudding's evidentiary tone, a Pentagram-designed institutional catalogue, and the register/breadcrumb language of a technical manual ("AIR / UNITED STATES AIR FORCE / FAMILY REGISTER 001"). It wants the reader to feel that public money is physical and auditable: here is the object you bought, here is the receipt.

**2. STUDIO EXECUTION**

The best studio would recognise that the F-15 page's *plate* (navy panel, mono corner captions, title top-left, disclaimer as a caption bar) is the real design system and that the homepage hero is a leftover SaaS template. They would make the homepage a *cover* built from the same plate: one object, one number, type held in a hard left column that never touches the render, the $10.7B set as the second-largest thing on the page and its dotted leader running physically to the citation chip. The submarine would appear once.

The illustrations would be the product. A "visual field guide" earns its name with drawn plates, not clay block-outs: side elevation or isometric line art, numbered callouts (01 cockpit & software, 02 electronic systems, 03 support & tooling) keyed to the section list beside it, so the sidebar and the picture are one instrument. The variant strip would be a real proportional timeline or a plain register, never an evenly spaced rule with years pretending to be an axis.

Type would drop to two families plus mono-for-figures: the serif stays; the rounded humanist sans (it reads as Avenir) is replaced by a grotesk with no smile, because a ledger should not be friendly. The page rhythm would be one alternation of cream and navy per page, not five stripes in the first 1,100px and then 3,000px of cream. Every column would share a single right edge; every ledger row the same height; every rule in a three-column table aligned across columns.

Mobile would be composed from the number down: eyebrow, number, headline, then the plate; ledger rows with the name left and the figure right on the first line; agency rows the same. The F-15 mobile page would keep its sidebar as a scrolling register, not a 2×2 grid of chevrons.

**3. GAPS**

1. **Hero is broken, home 1440.** The headline "tax dollars build." sits on top of the submarine's sail and masts; below, "$10.7B" renders as near-black mono on navy (it is legible only as a ghost) and the inline figure after "Printed on the P-40 page:" is an empty underlined blank. The most important number on the site is invisible on the most important screen. Fix: hard 40/60 column split with the render clipped to the right column (or pushed to 30% opacity behind), number set in cream/tan mono at 64px, citation value populated. Nothing else moves the design as far.

2. **The submarine appears twice, home 1440 and 390.** Hero object, then the same asset full-bleed 500px later as the first gallery item, then a third time on mobile. Fix: hero is a typographic cover with the number, gallery holds all three objects; or hero holds the sub and the gallery starts with the F-35.

3. **Illustration quality, both pages.** The F-15EX render (F-15 page plate) is a wedge fuselage with paper-plane wings and oversized fins; the "Cyber Security Research" tile (home gallery, right card) is generic server boxes on a slab; the submarine is a clay tube. For a field guide, these are the content. Fix: line-art technical plates with callouts keyed to the section nav; if 3D must stay, higher fidelity and a flat cel-shaded look that matches the blueprint grid.

4. **Fake timeline, F-15 1440 under "Selected aircraft".** Six variants evenly spaced along a rule with tick marks and years; 1972→1973 gets the same gap as 1988→2021. Fix: proportional spacing with the 33-year gap visible (that gap is the story), or remove the rule and ticks and present a plain register.

5. **Name repetition, F-15 1440.** Within 450px: "F-15" (H1), "F-15EX Eagle II" (selected variant), "F-15EX / EAGLE II" (plate corner), "F-15EX" at 90px (plate title). Fix: drop the mono corner label; keep the plate title as the variant and the H1 as the family.

6. **Ledger inconsistency, home "Largest FY25→26 changes".** Three of five rows carry a red-ruled mono "increased N%" story line; two do not; row heights vary accordingly; two paragraphs of caveat ("Programs with the biggest…", "Scope: …") precede the first figure, then a third caveat follows the list. Fix: one-line intro; scope into the existing footnote; story lines on every row or on none.

7. **Agency grid rules misalign, home 1440 "Browse by agency".** Names wrap to 1, 2, or 3 lines ("Defense Advanced Research Projects Agency" vs "Defense Threat Reduction Agency"), so the horizontal rules across the three columns drift out of register from the second row down. Fix: shared row height per triple, or a single-column table with name | programs | FY24 $ right-aligned; drop the 24 repetitions of "FY24".

8. **Palette strays.** Blue outlined "Fact IDs" button in the home nav is the only saturated blue on the page; the "$10.7B" on home 390 is link-blue; the home footer is cool grey while the F-15 footer is cream. Fix: vermilion is the one accent; footer cream everywhere.

9. **Mobile ledger loses its anchor, home 390.** "+$7.45B" is demoted to the third line at body size under the italic descriptor. Fix: name left, figure right on line one, descriptor beneath.

10. **Mobile hero becomes a banner, home 390.** The plate shrinks to a 260px image strip, then the type restarts on cream; it reads as a stock 3D banner. Fix: keep the plate frame with corner captions, or lead with eyebrow + number + headline and put the object below as a captioned plate.

11. **Ragged right edges, home 1440 hero.** Headline ends ~640px, subhead ~567px, search rule ~512px; three right edges in one column. The hero also has a 10px inset bezel border that no other panel on either page has.

12. **F-15 body, 1440.** The middle column's eyebrow/summary starts higher than the right column's H2 "Aircraft & configuration", so two text blocks compete for first read; "Sources & dates" is sans while "Budget connection" is mono directly below it; ~120px of dead cream between the "Next" link and the footer. On 390 the H2 arrives *after* the summary, role/crew, and source link, inverting the hierarchy.

13. **Stats strip wraps badly, home 390.** "24" orphaned at the end of line two, "defense agencies" alone on line three.

14. **Fold strip, home both widths.** "Understand a program / Find local connections / Investigate a change" is three serif labels with no affordance, no destination hint, no relationship to what follows; on 390 they become three ruled rows that look like a collapsed accordion.

**4. AI TELLS**

- Hero-illustration-with-tagline: "See what your tax dollars build." beside a clay 3D object on a grid is the 2023 Stripe/Linear/Spline template, verbatim.
- Clay isometric renders on a cyan grid, three times over. The single most recognisable generated-look of the moment.
- Triplet copy cadence: "Understand the program. Follow the evidence. Open the receipt." and the three-verb fold strip "Understand / Find / Investigate" (the three-pillar feature row, just without boxes).
- Stats row: "1,938 program elements · 130,347 source citations · 200 contractor families · 24 defense agencies". Setting it in mono mutes it; it is still the stats row.
- Three-column grid of agencies with a hover-ready row treatment.
- Four-column SaaS footer with bold group headings (Explore / Investigate / Verify & reuse).
- Caveat soup standing in for badge soup: five disclaimers on the homepage ("Conceptual illustrations…", "Scope: …", "Coverage varies…", "Trajectory figures are derived…", "Correlation is shown, not causation"), plus the disclaimer bar under the F-15 plate. Rigor is the brand, but this reads as a template that appends a caveat to every block.
- Gradient-fade selected-state bar under F-15EX.
- "A different way into the budget." as a section head: generic marketing subhead language.

**5. SCORE**

The seeds of a memorable design are present and load-bearing: the mono ledger with right-aligned vermilion deltas and dotted leaders, the register breadcrumb, the dual-scale "F-15 The Eagle family." headline, the plate with corner captions, the "Next, follow the public money" pagination. Those are the parts I would keep in a monograph. Around them sits a broken hero (invisible headline number, type-on-render collision), a duplicated asset, block-out illustrations carrying a "visual field guide" they cannot support, a fake axis, misregistered grids, palette strays, and a mobile ledger that demotes its own numbers. The seams are not cosmetic; they are structural on the hero and on the illustration layer the whole premise rests on.

SCORE: 5.5/10

### Diagnosis of the regression (6 → 5.5)

Measured on the live page: the `$10.7B` cite-figure computes to `color: rgb(32,46,40)` —
the site's dark ink — on the navy plate. `.cite-figure` carries `text-foreground`; Kimi
re-pointed `--cite-decoration` (the underline) inside the dock but never the text colour
itself. The critic's "empty underlined blank" after "Printed on the P-40 page:" is that
same figure, present in the DOM and invisible. The headline's right edge at ~640px runs
through the submarine's sail and masts. Both are execution bugs on the correct structural
idea. The critic was explicit: "Nothing else moves the design as far."

**A methodological note.** Iteration 1's critic called the model-on-blueprint illustration
system "a genuine, ownable idea — it is what keeps this from being forgettable." Iteration
2's critic called the same assets "clay isometric renders on a cyan grid — the single most
recognisable generated-look of the moment" and demanded line-art technical plates. Same
assets, opposite readings. Fresh-context critics carry real variance on subjective calls;
some of the 0.5 swing is critic, not design. The hero regression, however, is objective.

**A ceiling to name.** The iteration-2 critic's gap #3 is illustration *quality* — "these
are the content" of a visual field guide. That is an asset problem, not a CSS problem;
Kimi cannot fix it. If a fresh critic keeps grading the 3D models as block-outs, 9/10 may
be unreachable without new illustration.

## Constraint change (owner, 2026-09-11): new illustration is in scope

> "use new illustration! you are not restrained to what is on the page, only what the data
> in the codebase holds and to make the website goal easy for reporters, defense analysts,
> and normal people to understand."

**What this unlocked.** The "illustration ceiling" flagged after iteration 2 did not
exist. Inventory of what the repo already held, none of it in the default view:

- `art/exhibits/f15-family-line-plate-v1.png` — graphite technical line engraving, front
  elevation, generated by Codex imagegen 2026-09-09. Exactly the "line-art technical
  plate" the iteration-2 critic demanded. Wired only into the *funding* workspace.
- `art/exhibits/f15-editorial-illustration-v1.png` — three-quarter overhead, graphite and
  sage, engraved surface detail, warm paper. Catalogue-raisonné quality. Same workspace.
- The default F-15 view — what every critic saw — renders `geometry.mjs`, a procedural
  three.js schematic. That is the "paper-plane wings" every critic named.
- Blender 5.2.1 LTS is installed; `.blend` sources for all three homepage exhibits exist;
  `scripts/exhibits/blender_sources.py` already sets camera, lighting and a drafting grid.

**New assets produced** (`scripts/exhibits/blender_lineart.py`, ~2–10 s per render):
same GLB geometry, same orthographic camera so `program-exhibits.ts` pin positions stay
valid, rendered as Freestyle silhouette + crease + border lines instead of lit clay.

| Asset | Register | Bytes |
|---|---|---|
| `virginia-line.webp`, `f35-line.webp`, `cyber-line.webp` | graphite on cream paper | 30–50 KB |
| `virginia-blueprint.webp`, `f35-blueprint.webp`, `cyber-blueprint.webp` | pale drafting lines on navy | 37–59 KB |

Geometry unchanged; `public/exhibits/README.md` disclaimers still hold. One gotcha
recorded for reuse: Blender's default **AgX** view transform tone-maps a paper world down
to grey — `view_transform = 'Standard'` is required for a line plate to render as paper
and graphite.

**Design implication.** The callout data the critic wanted ("numbered callouts keyed to
the section list, so the sidebar and the picture are one instrument") already exists:
every topic in `program-exhibits.ts` carries a `position: [x%, y%]` on the plate.

**Owner correction (same day):** "Don't need to use blender or 3d, requirements are
beautiful graphics that match the vibe of what fiscalreceipts.com is trying to achieve."
The Freestyle plates are clay geometry in a different coat — cleaner than the posters,
not beautiful. Removed from `site/public/`; `art/exhibits/*-line.png`,
`*-blueprint.png` and `scripts/exhibits/blender_lineart.py` retained but unused.

**New approach: hand-drawn vector plates.** SVG, `viewBox 0 0 1800 960`, every stroke and
fill `currentColor` or `none` — no literal colour, so one asset renders as graphite on
paper *and* as pale lines on the navy plate, and passes the tokens gate by construction.
Tone by hatching and opacity only. The two Codex-imagegen F-15 plates are the explicit
bar; the illustrator must Read them first. Mandatory write→render→look→revise loop
(≥3 passes) against both registers. Spike on the submarine first; scale to a judge panel
across all three subjects only if the spike holds up beside the F-15 plates.

### Illustration spike — Virginia-class shipyard plate (hand-drawn SVG)

One illustrator (Fable 5.1), five write→render→look→revise loops, 20 minutes. Result:
14.8 KB SVG, zero literal colours, reads correctly on cream and on navy from the same
file. The boat is unmistakably a Virginia — blunt sonar-sphere bow with contour hatching,
sail a third back with the raked leading edge and aft fillet, bow planes on the hull,
module seams, long taper to a ring-airfoil pump-jet shroud, cruciform stern with hinge
lines. Goliath gantry, keel blocks, drydock floor, and the next hull behind as three
separated modules on blocks — so all three funding topics have something real to point at.

Loop 1 caught a real defect worth recording: a `<g id="sail">` and a `<defs>` path shared
an id, so `<use>` resolved to itself and the sail had no outline; anchor circles were
inheriting the group stroke. Both lessons are now in every illustrator's brief.

Illustrator's own verdict, verbatim: "It would sit beside the editorial plate as a
plainer, more diagrammatic sibling rather than an equal." Fair. The hatching is ruled
rather than hand-varied, the gantry is an emblem, the surface articulation is sparse.
Anchors: construction [53.3, 66.9], future [56.2, 48.8], shipyard [44.7, 19.4].

**Verdict: SVG is a viable path.** Scaled to a judge panel — three angles per subject
(technical / editorial-engraving / cutaway for the sub; planform / three-quarter /
flightline for the F-35; isometric lab / network-engraving / three-benches for cyber),
each blind to the others, a fresh judge per subject ranking against the F-15 plates,
then one refinement pass on each winner grafting from the runners-up.

## Run 2 — Iteration 3 — hero repair (execution, not structure)

**Brief:** the ten gaps from the iteration-2 critique in priority order, led by the three
measured hero defects; Kimi required to *prove* Gap 1(a) with `getComputedStyle` readings
and contrast ratios, not assert it. No new structure.

**Kimi's session:** ~40 minutes. Skill×1, Read×16, Bash×36, Edit×23, Write×2.

### Kimi's report (verbatim)

Mobile ledger confirmed: figure right on line one, descriptor beneath. All verification done. 

---

**Report**

**Files changed (gap per line):**
- `src/app/page.tsx` — persona strip → one prose line inside the hero copy (Gap 10); gallery drops the submarine, F-35 leads (Gap 2); signal tag inline at the row's right, uniform ledger rows (Gap 5); scope caveat moved verbatim into the single ledger footnote (Gaps 5, 9); agency grid → single-column table, "FY24" once in the head (Gap 6); H1 re-broken to three lines (Gap 1b/1c).
- `src/app/home.module.css` — `--foreground: var(--plate-ink)` + cite re-points inside the ≥768px dock (Gap 1a); 40/60 airlock, render clipped to the right 60% at `object-position: 66%` (Gap 1b); one 30rem measure for the whole column (Gap 1c); 10px bezel removed; rust `--cite-decoration` register on `.home` and cream footer via `body:has(.home)` (Gap 7); mobile hero = copy → receipt → object plate, ledger title|figure line one, stats wrap as whole units (Gap 8).
- `src/components/receipt-moment.module.css` — display figure to `clamp(2.5rem, 4.5vw, 4rem)` (Gap 1a).
- `src/components/f15-family-browser.tsx` — rail margins proportional to year deltas (5px/yr; C/D adjacent, EX stands 165px apart) (Gap 3).
- `src/components/f15-family-browser.module.css` — rail left-held, `width: fit-content` so the axis ends at the 2021 tick, buttons no longer grow (Gap 3); plate corner label suppressed structurally (Gap 4).
- `src/components/site-header.module.css` — Fact IDs toggle restyled to quiet register chrome (unlayered rules outrank the blue utilities; F-15's own override still wins there) (Gap 7).
- `scripts/gates/token-allowlist.json` — `#8db7c433` entry deleted with the bezel.

**Gates:** tokens **pass**, motion **pass**, lint **0 errors** (17 pre-existing warnings in untouched files).

**Gap 1(a), measured live at 1440×900 (playwright, `getComputedStyle`):**
- Display `$10.7B` (64px): color **rgb(214, 237, 245)** on plate rgb(10, 22, 31) → **15.07:1** (floor 3:1) — was rgb(32, 46, 40), invisible.
- Inline `$10.7B` (12.48px, printed-on line): color **rgb(214, 237, 245)** → **15.07:1** (floor 4.5:1).
- DOM order unchanged (printed-line cite still first `[data-fact-id]`); fold contract re-measured: receipt-moment bottom 749px @1440×900, 638px @390×844 — above both folds.

**Not closed:** nothing in the ten gaps — the hero scope qualifier, stats coverage line, gallery illustration note, and trust/correlation line each remain exactly once (moved or kept, never rewritten, per the prose constraint); full `npm run verify` was not run per the brief's instructions — the three commanded checks plus the Gap 1(a) numeric proof are what was asked.

### Verified independently

- tokens gate PASS · motion gate PASS · both pages HTTP 200
- **My own playwright measurement, not Kimi's:** both `$10.7B` figures compute to
  `rgb(214, 237, 245)` on `rgb(10, 22, 31)` → **15.07:1**. Matches Kimi's report exactly.
  Iteration 2 measured `rgb(32, 46, 40)` — invisible.
- Hero zoom confirms: type column hard-stopped at 40%, render clipped to the right 60%,
  headline on three lines with no orphan, one measure for the column, bezel gone.
- No stray dev server; only the pre-existing :3015.

### Critic — Run 2 / Iteration 3

**1. AESTHETIC**

It is reaching for investigative data journalism dressed as a naturalist's field guide: cream stock, ink-navy plates, a Garamond-class display serif, a typewriter mono for identifiers, and monochrome low-poly 3D "specimens." Reference points are ProPublica/The Pudding rigor crossed with the object-fetish of a Teenage Engineering product page and the hangar viewer of an Ace Combat codex. It wants the reader to feel that a $10.7B line item is a physical object you can pick up, rotate, and read the receipt on.

**2. STUDIO EXECUTION**

Home: one subject per screen. The studio hero is the submarine and the number as a single composed receipt — render full-bleed, "$10.7B" set in the display serif with lining figures sitting against the hull, one caption line ("Virginia Class Submarine · Navy · P-40, PB2026"), one search field. Everything the current hero stacks (eyebrow, three-link sentence, four chips, two-line scope note) drops below the fold. "A different way in" becomes a shelf of three or four specimens at ~360px, not two 470px full-bleed plates; the page returns to cream by 1,400px instead of 2,200. The changes table gets bars scaled to the delta and nothing else; the agency list runs two columns of twelve with a faint proportional bar so $109.3B and $715.5M are comparable at a glance.

F-15: the atlas is the hero, and the six-variant timeline is drawn along the atlas's bottom edge as a scrubber — it is a model selector, so it lives on the model. One band replaces five. Title is "F-15" alone at display size with "THE EAGLE FAMILY · UNITED STATES AIR FORCE · REGISTER 001" as one mono eyebrow. Below: two columns, not three — a spec sheet (role, crew, seats, first delivery, source) and one narrative under one heading. One accent (rust) owns every active state; mint is reserved for models; the home renders are re-lit in the same mint-on-navy material as the atlas so both pages come out of one hangar.

Mobile as its own composition: the timeline becomes a stepper ("F-15EX · 6 of 6", prev/next), tabs become a full-width segmented list, renders get art-directed square crops instead of the desktop frame shrunk to a postage stamp inside a tall navy box, and every heading precedes its content.

Relationship between pages: same nav, same accent, same model material, same rule discipline. Right now home has six nav items plus a "Fact IDs" pill; F-15 has one item. They read as two products.

**3. GAPS** (biggest first)

1. **The hero has no subject.** Home 1440, above the fold. Six elements compete in the left column: eyebrow, headline (with "build." orphaned on line three), one-liner, search, the three-link sentence, and the $10.7B block carrying four chips and two lines of scope text. The submarine on the right and the Virginia-class figure on the left are the same subject and never touch. Fix: headline + search only; make submarine + $10.7B one full-width receipt band beneath, figure in the serif at headline size, chips dissolved into a plain caption. Reset the rag to two lines: "See what your tax / dollars build."

2. **Five bands of chrome before the first image.** F-15 1440: breadcrumb bar, title/subtitle/actions, "Selected aircraft" timeline, tabs, "CONFIGURATION ATLAS" header — ~470px of controls separated by identical hairlines and identical ~40px gaps, so nothing groups with anything. Fix: timeline into the atlas's bottom edge; tabs beneath the atlas; breadcrumb folded into the eyebrow; the atlas header row becomes a corner stamp. Tighten title-to-timeline to ~16px so the family name owns the scrubber.

3. **Redundant prose in a three-column layout.** F-15 1440, below the atlas. Column two ("A two-seat Eagle with digital flight controls, cockpit displays and updated avionics") and column three ("combines a two-seat airframe with digital flight controls and updated mission systems") are the same sentence. The heading "Aircraft & configuration" appears in the rail and atop column three but never over the content as a whole. Fix: one heading spanning columns two and three; column two becomes a spec sheet (ROLE, CREW, SEATS, FIRST DELIVERY, SOURCE); column three the single narrative. Delete the summary paragraph.

4. **Mobile is a squashed desktop with defects.** Home 390, changes table: italic tags clip mid-word ("discretionary dow"), mono bar labels clip ("...EMD increase"). F-15 390, timeline strip: scrolled to the end with "5E" bleeding at the left edge, no scroll cue, and the active underline fades to transparent on the right — reads as a rendering error. Tabs cut off "Family history" with no overflow cue. F-15 390, content: the "Aircraft & configuration" heading arrives after its own summary, ROLE/CREW block, and source link. Home 390, dark section: the F-35 and server renders are small objects floating in tall navy boxes. Fix: two-line rows with real ellipsis; stepper for the timeline; segmented list for tabs; DOM reorder so the heading leads; square art-directed crops.

5. **A 2,200px dark slab.** Home 1440, hero through "Cyber Security Research." Hero navy and section navy are the same value with no seam, so the fold is a wall, then two 470px plates with 100px paddings. The stack of white sheets behind the F-35 reads as a clipping artifact at that scale. Fix: return to cream after the hero; run the specimens as a shelf; make the paper stack legible (a J-book with a spine) or drop it.

6. **Mini-bars that carry nothing.** Home 1440, changes table, between the row and the delta: a 2px red tick plus a mono sentence repeating the row name ("Long Range Kill Chains increased 3053% FY25→26"). Each row carries five type treatments (mono ID, bold name, sans agency, italic tags, mono label, mono delta). Fix: a bar scaled to the dollar delta, the % folded into the tags line, two treatments per row.

7. **Underlined-number noise.** Home 1440, "Browse by agency," FY24 column: 24 underlined mono numbers form a dotted right edge; mixed $B/$M magnitudes without a bar are incomparable; 24 single-column rows is 1,200px of list. Fix: two columns of twelve, no underlines (the row is the link), tabular figures in one unit or with a faint proportional bar.

8. **The accent has no owner.** Rust on the F-15EX tick and "2021"; dark green on the rail's active item; red ticks in the changes table; mint on the atlas model; navy underlines on home links. Fix: rust for every selected/active state, green removed, mint only on models.

9. **Two giant serif labels in one viewport.** F-15 1440: "F-15" at ~120px and "F-15EX" at ~70px in mint 350px below it. Fix: in-panel label becomes a mono plate stamp ("F-15EX · EAGLE II · 2021") bottom-left, replacing "Activate to rotate and inspect  02 SEATS," which currently jams an instruction and a spec onto one baseline.

10. **Fine detail.** "Sources & dates" (sans) and "Budget connection" (mono) are adjacent disclosure rows in two typefaces (F-15, column three). "$10.7B" appears twice within 40px (display, then inline underlined in the caption). "Sound off / Share view" float 500px right of a subtitle they don't relate to; they belong in the atlas. "Open the visual field guide" sits 1,000px from the heading it serves. The 390 footer forces three link columns into ~110px each.

**4. AI TELLS**

- ⌘K search pill plus a second pill ("Fact IDs") in the nav.
- Badge soup in the hero: 2013 / Navy / P-40 detail / PB2026.
- The stats strip ("1,938 program elements · 130,347 source citations · …") — quiet, but it is the stats row.
- Four-column SaaS footer: brand blurb + Explore / Investigate / Verify & reuse.
- Left rail with right-chevrons on every item; on mobile a 2×2 grid of chevron cells — the settings-list default used as tabs.
- Default `<details>` triangles with a count badge.
- Hairline-as-spacing: roughly fourteen full-width 1px rules on the F-15 page; every gap is the same gap.
- Middot chains as metadata everywhere: "Drag · rotate · explore," "2021 · FIRST AIR FORCE DELIVERY," "Aircraft & engines · Ground & training support · …," the italic row tags.
- Monospace applied to anything that smells like "data," including prose bar labels and UI instructions — a technical costume rather than a type system.
- Accidental gradient on the mobile timeline underline.
- Hero = eyebrow / headline / one-liner / search / illustration-right — the docs-site template; the bespoke render is the only thing keeping it out of the bin.

What it avoids, and this is load-bearing: no card grid, no three-up feature row, no hover chrome, no rounded-everything, no stock illustration. The renders, the variant timeline, and the "Next, follow the public money" band are not things I have seen a thousand times.

**5. SCORE**

The ambition and the assets are 8-level; the composition and the mobile are 5-level. A hero that does not choose a subject, five bands of chrome before the model, the same sentence in two columns, real defects at 390 (clipped text, a cut-off scroller, a heading after its content), and two pages that share neither a nav nor an accent. That is more than visible seams.

SCORE: 6/10

### Reading across four critiques (baseline consensus + iterations 1–3)

Score trajectory: 5.5 → 6 → 5.5 → 6. Three iterations of real, independently verified
change have moved the score half a point. That is the finding.

**The critic's *prescription* for the hero has changed every time.** Iteration 1 wanted
headline 120px+, plate full-bleed right, search demoted. Iteration 2 wanted a hard 40/60
split with the number in cream mono at 64px — Kimi built exactly that. Iteration 3 now
says "the hero has no subject" and wants headline + search only, with submarine + number
as a separate full-width band, figure in the *serif*. Each fresh critic redesigns the fold
from scratch; chasing the latest prescription is a random walk.

**The illustration verdict flipped again.** Iteration 2: "clay isometric renders on a cyan
grid — the single most recognisable generated-look of the moment." Iteration 3: "the
bespoke render is the only thing keeping it out of the bin… not things I have seen a
thousand times." Same pixels.

**What is stable across all four** — and therefore what iteration 4 should be driven by,
not the latest critic's specific fix:

| Principle | Raised in |
|---|---|
| Too many elements compete; one subject per screen | 4/4 |
| Badge / chip soup around the receipt (still 4 chips: 2013 / Navy / P-40 detail / PB2026) | 4/4 |
| Stats strip is still the stats row however it is set | 4/4 |
| F-15: too many bands of chrome before the first content (now "five") | 4/4 |
| Mobile is a squashed desktop, now with real defects (clipped text, cut-off scroller, heading after its content) | 4/4 |
| Mono used as a costume for anything that "smells like data" — reserve it for identifiers | 3/4 |
| One accent with one owner; rust / green / red / mint / navy all claiming "active" | 3/4 |
| The two pages share neither nav nor accent — "they read as two products" | 3/4 |
| Hairline-as-spacing: ~14 full-width rules on F-15, every gap the same gap | 2/4 |
| The same sentence rendered twice in adjacent F-15 columns | 1/4 (new, real) |

**Lesson for maximising the score:** execute the *principles* that every critic names,
with fewer and larger moves, rather than the *prescriptions* that each critic invents.
Verified execution earns ~+0.5 when a structural move lands; a broken bold move costs it
back. Nothing so far has been big enough to clear 6, and the critic said why: "The
ambition and the assets are 8-level; the composition and the mobile are 5-level."

### Illustration panel — results

14 agents (8 illustrators, 3 judges, 3 refiners), 76 minutes. One refiner (F-35) was
killed by a session usage limit mid-loop and resumed afterwards.

| Subject | Winner | Judge score | Runners-up | Judge's one line |
|---|---|---|---|---|
| Virginia | **B — editorial engraving** (Goliath gantry hoisting a hull ring, boat sunk in drydock, next hull queued in sections) | 7.5 | C cutaway 6 · A spike 5 | "The only candidate with a point of view about how a Virginia is actually built." |
| F-35 | **C — flightline elevation** (canopy up, boarding stand, tow tractor, power cart) | 7 | A planform 6 · B three-quarter 5 | "The only candidate that reads as a maintenance scene rather than a diagram." |
| Cyber | **B — network engraving** (hardened core, broken periphery, lens detail cutting a node open, three specimens on a bench) | 7.3 | C three benches 5.8 · A isometric lab 5 | "The only candidate whose hairline-to-heavy ladder and hatch-as-volume belong in the same register as the F-15 line plate." |

The F-15 reference plates were calibrated at 8.5–9. Every judge said the winner would sit
beside them *after* the named fixes; the refiners then did those fixes.

**Two findings from the panel.**
- My spike scored **5** against B's 7.5 — "an infographic pictogram next to the F-15
  plates." One iterated attempt converges on the safe drawing; the panel's diversity was
  in the *angle* (engraving vs cutaway vs technical), and the angle with a point of view
  won all three times. The runners-up still contributed: the judges named what to graft.
- The three-quarter F-35 (the angle closest to the editorial reference) scored lowest
  (5) — vector perspective fought the illustrator. Profile and plan views are the honest
  vector idiom; the panel found that empirically rather than by my assuming it.

**Integration decided by a measurement, not a preference.** The homepage weight gate is
at 1,389,228 / 88,022 against a ceiling of 1,475,000 / 95,000 — 86 KB raw headroom.
Inlining three plates (~370 KB raw) would fail it by 4×. External `<use
href="/exhibits/plates/x.svg#x-plate">` inherits `currentColor` from the host, keeps
~100 bytes of DOM per plate, and is verified in both registers with the external
`<style>` block applying. Anchors measured from the DOM, not from illustrator reports.

### Judge variance — the finding that matters most for the method

Resuming the panel to re-run one interrupted refiner re-ran the judges instead (their
prompts were unchanged, but the harness replays agents, not results, when an upstream
value differs — and fresh judges are not deterministic). **Identical candidates, different
winners for two of three subjects:**

| Subject | Run 1 judge | Run 2 judge |
|---|---|---|
| Virginia | B 7.5 · C 6 · A 5 | B 7 · A 6 · C 5.5 — same winner |
| F-35 | **C flightline 7** · A 6 · B 5 | **A planform 7** · C 5.5 · B 4 — inverted |
| Cyber | **B network 7.3** · C 5.8 · A 5 | **C benches 7** · A 6.5 · B 6 — inverted |

Not a reorder among near-ties — the run-1 winner dropped 1.5 points on re-judging in both
cases. This is the same phenomenon as the page critic's flip on the clay renders, now
measured directly. **A single judge is not a measurement.** The design-critic loop's
scores carry the same variance; a ±0.5 swing is inside the noise.

Both sets of winners were then refined, so two good plates now exist for the F-35 and
for cyber. Resolution: three judges per subject with deliberately different lenses
(studio craft / newspaper graphics editor / defense analyst), each judging both
finalists in both registers against the owner's audience statement. Majority wins.
Kimi's iteration 4 continues against the run-1 set in `public/`; the page structure is
plate-agnostic, so a swap afterwards touches only file contents and the anchor table.

### Majority vote — resolved

Three judges per subject, deliberately different lenses, both finalists in both registers,
judged against the owner's audience statement.

**F-35 — planform, 3–0, every margin "clear".** All three found the flightline's *aircraft*
not credibly an F-35: "the canopy is a giant blade dominating the composition, the wing
reads as a ledge," "a rounded chin scoop instead of a DSI side inlet, an F-22-length
nose." The planform "draws the right airplane with authority." The lay-reader story of
canopy-up-and-ladder was acknowledged by all three and outweighed by identification.

**Cyber — three benches, 2–1.** The craft judge picked the network engraving clearly (real
weight ladder, hatching as volume, tighter composition; "the one that would hang beside
the F-15 line plate"). The editor and the analyst picked the benches, and the analyst's
reason is the one that binds on this site: on the network plate "a callout would land on
a metaphor ('hardened core'), which an analyst will read as an unsupported assertion,"
whereas the benches "draw things a cyber R&D program actually pays for" — callouts land
on nameable equipment. The editor: the network "shouts 'cyber' at thumbnail size, and
that is exactly the cliché a field guide should avoid."

**Lesson:** the craft-only judge and the audience judges disagreed on the abstract subject
and agreed on the concrete one. When the drawing is of a real object, craft and legibility
point the same way; when it is of an idea, they can diverge, and the audience wins.

## Run 2 — Iteration 4 — plates in, principles applied

**Brief:** principles, not prescriptions — the ten things all four critiques agreed on —
plus the plate integration spec (external `<use>`, measured anchors, the F-15 editorial
illustration as default plate). Two facts that freed Kimi: `persona-row` is not
gate-held; `data-stat` only requires linked elements, not a strip. Mobile deferred.

**Kimi's session:** 48 minutes, Read×19, Bash×41, Edit×31, Write×4 — then
`429 · account suspended due to insufficient balance`. No report. The Moonshot balance
ran out mid-pass.

### What Kimi finished (verified)
- Homepage: hero as one composition (three-line headline, blueprint submarine in the navy
  vitrine, `$10.7B` with ONE caption line); persona row deleted; chips dissolved; stats
  folded into a footer sentence with the four `data-stat` links; field-guide band on
  paper with all three SVG plates via `<use>`, each with numbered callouts at the
  measured anchors and the key beside it; ledger with signed rust deltas; agency index as
  a single-column table with "FY24" once.
- F-15: breadcrumb folded into the eyebrow; full site header restored (focused mode
  removed); editorial illustration wired into `f15-model.tsx` as the default plate with
  the 3D scene as the one bordered opt-in; `f15-model.module.css` rewritten for the paper
  register; the new `plateBlock` JSX written with a comment stating its intent.

### What the cutoff left broken, and what I (Claude) completed by hand
Kimi wrote the plate-block JSX at 18:33 and died before the CSS. On the live page: the
F-15 plate rendered **twice** (new block above the timeline, stale one below the tabs),
`.plateActions` had no styles so Sound/Share collapsed onto each other, and the old
`.modelCell { background: #0a1b23 }` painted navy gutters around an illustration meant
for paper. I removed the stale `<F15Model>`, made `.modelCell` transparent (the
instrument's own `[data-active]` rule darkens it only while 3D is live), and wrote
`.plateBlock` / `.plateActions` / `.plateBlock + .rail` to the intent in Kimi's own JSX
comment — ~40 lines. One allowlist entry retired with the hex.

### Plates swapped to the vote winners after Kimi finished
`f35.svg` → planform, `cyber.svg` → three benches; nine `position` values updated in
`program-exhibits.ts` from DOM measurement. `pin-layout` 3/3, `program-exhibit` 6/6.

### One test changed, deliberately
`site-header.test.tsx` asserted the focused-family behaviour that hid the Fact IDs
toggle behind the sections menu on `/families/…` — the exact thing four critics called
"two products." Rewritten to the new contract (toggle directly reachable, still in the
menu, open/close/focus-return unchanged), with the reason in a comment. The two
funding-workspace failures in Astra's untracked `f15-family-browser.test.tsx` remain
pre-existing.

- tokens PASS · motion PASS · lint 0 errors · both pages 200

### Critic B — Run 2 / Iteration 4

## 1. Aesthetic

This is reaching for the **civic-archive editorial** register: warm paper ground, an old-style serif for display, monospace for identifiers, hairline rules, and white-on-navy engineering linework — the visual grammar of a Haynes manual crossed with the FT's visual-journalism desk and the Stripe Press / *Works in Progress* school of "serious things, beautifully typeset." The "field guide" framing (numbered plates, callouts 01/02/03, captions under each figure) borrows from Audubon and Jane's. It wants the reader to feel they are standing in a well-kept records room where every dollar has a drawer: calm, documented, trustworthy — the opposite of a dashboard.

## 2. Studio execution

A top studio handed this brief would make three decisions this design has not made.

**One language for objects.** The homepage promises blueprints; the program page delivers a glossy camo 3D render. The studio would pick linework everywhere (ghosted technical views with dimension lines and numbered callouts), so the F-15 page reads as plate 02 of the same book the homepage opened. The callouts on the drawing would *be* the section nav — click "03" on the tail and you land in Electronic systems.

**The number lives on the drawing.** In the home hero, the submarine would be drawn to scale with a dimension line across the hull reading `$10.7B`, set in the serif with tabular lining figures, the citation reduced to one quiet line ("Virginia-class · P-40, PB2026 ↗") with the hash ID behind the click. Text and image become one figure instead of two columns that happen to share a background. The F-15 hero would do the same: "F-15 — The Eagle family" with the family's FY2026 request as a cited figure in the first screen, because on a site called Fiscal Receipts a program page whose first 900px contain zero dollars is a broken promise.

**Tables are ledgers, not spreadsheets.** The agency list at 1440 would be a 720px measure with numbers right beside names (or proportional bars that make the Navy/Army/Air Force parity visible at a glance), truncated to eight with "All 24 →" — exactly what the mobile version already does. The changes table would be one label, one bar, one delta per row.

The mobile versions would be their own compositions: hero = number plus a cropped hull bleeding off the right edge; variant timeline as a vertical stepper (1972 → 2021, showing the 33-year gap before EX as real space); eyebrow reduced to 11px tracked small caps on one line; content heading first, always.

The rhythm down the homepage would be strictly numbered: 01 / SEA (the hero), 02 / AIR, 03 / CYBER — the hero currently is plate 01 but is never labeled as such, so the sequence starts at 02 and the reader never learns why.

## 3. Gaps

1. **The two pages don't belong to the same book.** *F-15 1440, hero image panel.* Photoreal render with "Sound off" / "Share view" / "Inspect in 3D" is an immersive-product-page template dropped into an editorial field guide. The caption beneath it literally says "Simplified illustration" under a photograph-grade render. Fix: linework F-15 in the same stroke weight and callout system as the home F-35 plate; kill "Sound off."

2. **The home hero is two unrelated columns and the number looks like terminal output.** *Home 1440, dark band.* Headline top-left, `$10.7B` in bold slashed-zero monospace bottom-left, submarine floating center-right; below the figure a raw `#d9dcdc48 P-40 detail` chip and a 30-word reconciliation note. Fix: number in serif tabular figures as a dimension annotation on the drawing; one-line citation; hash behind the click.

3. **Mobile home hero has ~300px of empty black.** *Home 390, dark band below the citation.* The illustration container reserves space and shows nothing. This is the first screen on a phone. Fix: crop the hull to bleed off-edge, or collapse the block.

4. **Program page buries the money.** *F-15 1440, everything above the tab bar.* No figure, no citation. Fix: family funding headline in the hero with a citation chip.

5. **Reading order in the F-15 body is backwards.** *F-15 1440, three-column region below the tabs.* The h3 "Aircraft & configuration" sits in the right column *after* an eyebrow-and-paragraph in the middle column that says the same thing ("two-seat… digital flight controls… avionics" twice). On mobile the heading lands mid-flow, after ROLE/CREW. Fix: one content column, heading first, merged paragraph, Role/Crew/First-delivery as a spec block under the heading.

6. **Agency table is a 1000px eye-trek.** *Home 1440, "Browse by agency."* 24 full-width rows, numbers at the far right edge, no leaders, no bars, mono abbreviation chips after every name. Fix: narrow measure or proportional bars; truncate to 8 + "All 24" as mobile does.

7. **Changes table has two labels per row and clips on mobile.** *Home 1440 and 390, "Largest FY25→26 changes."* Each row carries mono ID + bold name + agency + italic reconciliation note + a monospace sentence ("Long Range Kill Chains increased 3053% FY25→26") + delta. On 390 the sentence is cut off mid-word. Fix: name, one bar, delta; reconciliation as a footnote glyph.

8. **Variant timeline is neither even nor proportional.** *F-15 1440, row below the caption.* Gaps between A/B/C/D/E/EX vary by content width; 1 year and 33 years look alike. On 390 the scroller shows a clipped "5E" fragment with no edge mask, and the tab row hides "Family history" with no affordance. Fix: proportional axis on desktop; vertical stepper or scroll-snap with fade masks on mobile.

9. **Mobile F-15 top is cramped and colliding.** *F-15 390, y≈360–390.* "CONFIGURATION ATLAS" overhangs "Share view"; the eyebrow wraps to two lines of oversized tracked mono caps. Fix: drop the label to a caption, eyebrow to 11px.

10. **Fine detail.** "Inspect in 3D" overlaps the nose cone (*F-15 1440, bottom-right of image*). "▸ Budget connection" is in mono while "▸ Sources & dates" is in sans, one rule apart. The F-35 plate has a loose curved line trailing off the right wing to nowhere. The 01/02/03 callout list is stranded top-right with a void beneath it (*Home 1440, AIR and CYBER sections*). The eyebrow on F-15 is as large as body text — it shouts.

## 4. AI tells

- "Explore the aircraft. Understand what gets funded. Follow every budget figure to its source." — the three-verb tagline template.
- Big-stat-with-eyebrow in the hero. Cited, but still the pattern.
- Chevron side-nav (four items with `>`), "Inspect in 3D," "Sound off" — the interactive-showcase kit.
- Badge soup: mono abbreviation chips on all 24 agency rows; a raw hash chip in the hero.
- A screen-reader sentence apparently leaking into the layout in the changes table.
- Hairline-divider list as the universal container.

To its credit: no card grids, no gradient blobs, no rounded boxes, no icon feature rows, no hover glow. The restraint is real, and it is why this scores above 5.

## 5. Score

The homepage has genuine typographic intent and a memorable idea; the program page abandons the system, and mobile has three outright layout defects (empty hero, clipped text, label collision). Good professional work with very visible seams.

SCORE: 6/10

### Critic C — Run 2 / Iteration 4

I have the four screenshots and nothing else is needed.

## 1. Aesthetic

This is reaching for the "civic ledger as editorial object": cream paper stock, a transitional display serif for headlines, monospace for identifiers and dollar figures, hairline rules, and blueprint-style line drawings. The reference points are The Pudding and Bloomberg Graphics on the data side, Stripe Press / Works in Progress on the typographic side, and Eyewitness / Haynes cutaway manuals for the "visual field guide" conceit. It wants the reader to feel that a government budget can be handled like a receipt — every number a line item, every line item traceable — and that the tracing is a pleasure rather than a chore.

## 2. Studio execution

The best studio would first commit to one drawing language and never break it. The home page's submarine, F-35 and cyber lab are all one hand — thin blueprint lines with numbered callouts. The studio version of the F-15 page would be drawn in that same hand, as a cutaway with callouts 01–04 that are literally the section nav (Aircraft & configuration, Cockpit & software, Electronic systems, Support & tooling). The illustration would be the table of contents. That single move makes the "field guide" promise true instead of decorative.

On the home hero the studio would pick one lead. Right now the headline ("See what your tax dollars build.") and the receipt ("$10.7B") are both trying to be it, in two different display voices. The studio would let the number lead — it is the product — set it in the display serif with tabular figures at the same size as the headline, and typeset the citation beneath it as an actual receipt: labeled rows (PROGRAM / FY / SOURCE / PAGE / LINE), not a run-on string mixing prose with a hash. The submarine would either bleed right on purpose with the drydock crane fully resolved, or be fitted; it would not be cut mid-structure at the right edge.

The rhythm down the home page would be tighter: hero, one field-guide illustration (not two stacked at ~700px each), the changes ledger, then an agency ledger of eight rows with a link, then footer. Roughly 3,000px, not 4,700. Each section would earn its space by density, not height.

Type scale would be pulled in. Eyebrows in mono at 10–11px with 0.12em tracking, not the 16px wide-set line that currently competes with the F-15 title. The display serif tightened at large sizes. One accent (the rust) used only for the active state and the link underline — which it mostly is, good.

Mobile would be its own composition: the hero becomes number-first with the illustration removed or used as a faint background wash; the changes ledger restacks to delta-first cards; the variant strip becomes a stepped list; the section nav becomes a single column with the active item pinned. Nothing clipped, nothing colliding.

## 3. Gaps, biggest first

**1. The model program page breaks the site's visual language.** F-15 desktop, hero region (y≈280–720): a photoreal 3D render on a cream box, sitting directly under a caption that says "Simplified illustration." The home page promised blueprint line art; the program page delivers a stock-looking render. This is the single decision that most flattens the site — it makes the program page feel like a different product. Fix: redraw the F-15 in the blueprint hand as a cutaway with callouts that map 1:1 to the left section nav. If 3D is non-negotiable, render it as a line-shaded/wireframe pass on the same paper, and delete "Sound off."

**2. The F-15 body is composed backwards.** Desktop, y≈925–1240: three columns — nav left, lede + specs middle, H2 "Aircraft & configuration" + body right. The heading sits to the right of the content it heads; the middle and right paragraphs say the same thing twice ("two-seat… digital flight controls… updated avionics" / "two-seat airframe with digital flight controls and updated mission systems"). On mobile (y≈990–1400) the order becomes lede → specs → source link → heading → body: the heading arrives after the section. Fix: one reading column. Heading, lede, a two-row spec table, body, disclosures. Left nav becomes a sticky rail. Delete one of the two paragraphs.

**3. Mobile home hero has a void.** 390 home, y≈205–330 (displayed; ~430–690 actual): after the citation line there is roughly a full viewport of empty dark navy where the submarine should be. Nothing renders. Fix: either ship the illustration at mobile (cropped to the hull, as a wash) or collapse the container.

**4. Mobile changes ledger clips.** 390 home, "Largest FY25→26 changes" rows: "discretionary do" and "Long Range Kill Chains increased 3053% FY25→26" run off the right edge and are truncated. Fix: restack per row — delta first line in mono, name second, agency + note third — and drop the mono sentence at mobile (it duplicates the row anyway; see gap 9).

**5. Mobile F-15 hero: three collisions in 300px.** (a) Eyebrow breaks "UNITED / STATES AIR FORCE". (b) "CONFIGURATION ATLAS" sits on a different baseline jammed against "Share view." (c) The variant strip shows a clipped fragment "5E" at the left edge with a gradient underline fading right. Fix: eyebrow becomes "FIELD GUIDE · AIR · USAF" at mobile; overlays stack into one mono line under the image; the variant strip becomes a snap-scroll with the active item centered and a leading fade, or a stepped vertical list.

**6. Home hero: two leads, two voices, one crop.** 1440 home, y≈50–300: serif headline top-left, mono slab "$10.7B" bottom-left, illustration cropped at the right edge mid-crane. The eye goes headline → number → illustration and never settles. The citation line under the number mixes prose, a program name, a FY, a hash, and a caveat sentence in one run. Fix: number leads (display serif, tabular); citation set as labeled receipt rows; illustration either fully resolved within the frame or deliberately bleeding with the crane cropped at a clean structural line.

**7. The field-guide numbering has a hole.** 1440 home, y≈410 and y≈690: "02 / AIR" and "03 / CYBER" with no visible "01." If the submarine is 01, it isn't labeled. Fix: label the hero "01 / SEA" in the same mono, or renumber.

**8. A 24-row table on a landing page.** 1440 home, y≈1250–1770: "Browse by agency" runs the full 24 rows, about a quarter of the page. The mobile version already truncates to 6 + "All 24 agencies →" — that is the correct design; desktop should match. Fix: 8 rows + link, or a two-column ledger.

**9. The changes ledger says everything twice.** 1440 home, y≈1060–1160: each row carries mono ID, bold name, agency, italic note, then a mono sentence ("Long Range Kill Chains increased 3053% FY25→26") that restates the row, then the delta. Fix: drop the sentence. Delta becomes the anchor with a small inline bar; the italic note becomes the only explanatory text.

**10. Type detail on the F-15 title.** 1440 F-15, y≈130–200: "F-15" is set in a heavy display weight and "The Eagle family." in a lighter weight on the same baseline; the contrast reads as two fonts rather than one family. The eyebrow above it is set too large and too wide and competes. Fix: eyebrow at ~11px; either one weight for the whole title line, or set "F-15" in the mono slab used for "$10.7B" so program pages tie back to the receipt voice on home.

**11. Overlay chrome on the F-15 image is three type voices.** 1440 F-15, y≈300: "Sound off / Share view" in sans with icons at left, "CONFIGURATION ATLAS" in mono caps at right, "Inspect in 3D" in a bordered button bottom-right. Fix: one mono voice for all overlays; remove "Sound off" unless sound is actually a feature people want on a budget site.

**12. The model page is thin.** 1440 F-15: tab bar ends at y≈875, body starts at y≈925, body ends at y≈1335, footer at y≈1410. The page is a hero plus one short module with dead space on both sides. For a page meant to model every program page, it does not yet show a single dollar figure. Fix: pull the lead receipt from "Budget & receipts" onto the Aircraft tab as a teaser — one cited number, in the receipt format from the home hero — so the program page delivers the product above the fold.

## 4. AI tells

- Photoreal 3D render on a flat cream background with "Inspect in 3D" cube button and "Sound off / Share view" — this is generic 3D-viewer chrome, and it is the most machine-looking thing on either page.
- Three-sentence triad copy: "Explore the aircraft. Understand what gets funded. Follow every budget figure to its source." and the headline "A different way into the budget." Both are template cadence.
- Three-column footer (Explore / Investigate / Verify & reuse) — default.
- Chevron ">" list links in the section nav, and the 2×2 chevron grid on mobile — default component behavior.
- The big-number hero stat. There is only one, and it is cited, which mitigates it, but the pattern is the pattern.
- Rust underline as the single accent — fine in itself but it is the accent every cream/serif site picks.

To its credit: no card grids, no gradients, no uniform border-radius, no hover-affordance rows, no badge soup. The ledgers and hairlines are honest. The home page has a genuine point of view; the program page dilutes it.

## 5. Score

The home page at desktop is a real 7 — a voice, a conceit, a typographic system, visible seams. But the brief says the F-15 page is the model for every program page, and that page breaks the visual language, composes its body in the wrong order, and shows no money. Mobile has outright defects: a blank hero void, clipped ledger rows, a clipped variant strip, colliding overlays. A studio would not ship any of those four. Taken as a whole, this is competent work with a point of view, undercut by its most important page and by a mobile pass that reads as untested.

SCORE: 5.5/10

### Critic A — Run 2 / Iteration 4

**1. AESTHETIC**

This is reaching for the civic field guide: warm paper, an old-style serif for display, monospace for anything that is an ID or a figure, hairline rules, and technical line drawings in the lineage of the Haynes manual and the USAF technical order, filtered through the Stripe Press / Works in Progress / Pudding school of data journalism that wants to look like a printed book. It wants the reader to feel that the federal budget is a physical thing made of parts, and that every part comes with a receipt you can hold up to the light. An auditor's Audubon.

**2. STUDIO EXECUTION**

A studio at this level would make three decisions this design has not made.

One drawing system. The homepage speaks in white ink-line elevations and isometrics; the F-15 page speaks in a photoreal gray 3D render sitting in a cream that is not quite the page's cream. The studio version commits to the line drawing, because it is the only ownable asset here, and the F-15 hero becomes a large orthographic view or a numbered exploded plate whose callouts are the budget lines. Same projection everywhere: right now the submarine is a side elevation, the F-35 a top-down orthographic, the cyber scene an isometric. Three plates, three projections.

The number lives on the drawing. On the homepage the $10.7B and the submarine are the same fact separated by 300px of dark. A studio runs a leader from the hull to the figure, sets the figure in the same serif as the headline rather than a heavier competing mono, and cuts the caption to one line. The hash and "workbook TOA" go behind the click.

The program page has one reading column. A sticky left rail carrying the variant timeline and section list; one column of prose; a specification block (Role / Crew / First delivery / Source) set as a plate caption directly under the image, the way a field guide does it. The current rail + lede + main-column trio says the same paragraph twice.

Rhythm: hero, thesis, plate, plate, ranked list, index. The plates stay the loudest thing on the page; the tables get shorter and quieter (eight agencies with inline proportion bars, then a link). Mobile is art-directed rather than reflowed: submarine cropped to the bow, F-15 cropped to the cockpit, the timeline turned vertical, the tables turned into stacked entries where the delta is the only large element. The nav is set in the same voice as the page instead of a SaaS bar with a ⌘K pill and a "Fact IDs" pill.

**3. GAPS**, ordered by leverage

1. **Two visual languages and no bridge.** Homepage: line drawings. F-15 page hero: a photoreal render whose caption reads "Simplified illustration" under something that looks like a photograph. The page meant to be the model for every program page does not look like the homepage that introduces it. Fix: line-draw the F-15. Also the seam: the render's background is a lighter, pinker cream than the page, producing a visible rectangle from the "Sound off" row down to the hairline above the disclaimer. Match it or ship the image transparent.

2. **F-15 body: three columns doing one job.** Below the tab bar, the left rail says "Aircraft & configuration," the right column's H2 says "Aircraft & configuration," and the middle column's lede ("A two-seat Eagle with digital flight controls…") paraphrases the right column's first two sentences. The right column's H2 is optically heavier than the middle column's eyebrow, so the eye lands right while reading order says middle. There is also a ~50px dead band with a stray hairline between the tabs and the content. Fix: rail + one column; Role / Crew / First delivery become a spec table under the image caption; delete the middle column.

3. **Mobile is a squashed desktop, and it breaks in three places.** Home 390: below the $10.7B caption there is roughly 250px of empty black where the submarine should be. F-15 390: the variant timeline is clipped, leaving a stranded "5E" fragment at the left edge, "F-15EX" alone mid-screen, and a rust gradient fading to nothing; "CONFIGURATION ATLAS" collides with "Share view" on the same row; "Multirole-capable fighter" hyphen-breaks. Home 390: the "Largest changes" mono formula lines run off the right edge. Fix: crop the heroes; timeline becomes a vertical list with the active variant marked; drop the formula line below 768 entirely; move the atlas label under the image.

4. **Chrome on the F-15 hero.** Four UI elements sit on the render: "Sound off," "Share view," "CONFIGURATION ATLAS," and a bordered "Inspect in 3D" button with a cube icon. An editorial page wearing a dashboard's controls. "Sound off" on a static image is a mystery. Fix: one text link, "Inspect in 3D ↗," in the caption line, at caption size.

5. **Homepage hero has four competing claims.** Headline top-left, drawing right, heavy mono figure bottom-left, and a two-line caption in five type styles (bold sans name, mono year, sans, underlined link, mono hash). The eye goes drawing → figure → headline. It should go headline → drawing-plus-figure as a single unit. Fix per section 2.

6. **Section numbering starts at 02.** Homepage body: "02 / AIR," then "03 / CYBER." No 01. If the submarine is 01, label it in the hero. Otherwise this reads as a bug, because it is one.

7. **Callout keys are 400px from their callouts.** Both homepage plates: numbered circles on the drawing at left; the key ("01 Aircraft & engines…") floats top-right, aligned to the section label rather than the drawing. Fix: leader lines, or set the key in a row beneath the drawing, or put the labels on the drawing itself.

8. **Two tables back-to-back kill the lower half.** "Largest FY25→26 changes": each row carries an ID, name, agency, italic caveat, a mono formula sentence that restates the name and the delta, and the delta. The formula is noise; +$7.45B is the story. "Browse by agency": 24 rows on the homepage, underlined dollar figures (underlined numerals in a tabular column hurt legibility), and single-letter mono abbreviations "N," "F," "A" beside Navy / Air Force / Army that read as stray characters. Fix: five rows with the delta large and the caveat as a footnote mark; eight agencies with inline bars, abbreviations removed.

9. **Fine detail.** F-15 left rail: chevrons hug each label and land at four different x-positions; right-align or drop them. F-15 right column: "▸ Sources & dates" is sans, "▸ Budget connection" is mono, siblings in two faces. F-15 tab bar: primary tabs at one weight, "Compare aircraft / Research tray" at another, two nav systems on one rule. The eyebrow "VISUAL FIELD GUIDE · AIR · UNITED STATES AIR FORCE" wraps to two tracked lines on mobile; shorten it below 768. "F-15" at ~80px beside "The Eagle family." at ~40px on one baseline is neither a stacked title nor a single one; pick.

**4. AI TELLS**

The large one: this recipe (old-style serif display, tracked mono eyebrows, warm cream, terracotta accent, hairlines, "01 / 02 / 03" keys) is the 2025–26 anti-default default, what a model produces when told "editorial, not SaaS." Avoiding cards is not the same as having a voice. The drawings are the voice; the type system around them is off the shelf.

Specific tells:
- Three-beat imperative tagline: "Explore the aircraft. Understand what gets funded. Follow every budget figure to its source."
- Stats-in-a-sentence footer: "Built from **1,938** program elements and **130,347** source citations across **200** contractor families and **24** agencies." A stats row with the boxes removed.
- Three-column footer link grid (Explore / Investigate / Verify & reuse).
- Bordered icon button and icon-label pairs on the hero image.
- Chevron on every sidebar item.
- The same cadence five times down the homepage: tracked mono eyebrow → serif H2 → sans dek → content.
- Headline-left / illustration-right hero split.
- "→" glyphs inside headings.
- A SaaS nav (⌘K search pill, "Fact IDs" pill, sans links) bolted onto an editorial page.

**5. SCORE**

Desktop pages are a 6: real illustrative assets, a proportional timeline that is a good idea, a "Next, follow the public money" hand-off that is a genuinely editorial move, undercut by two visual languages and a redundant body. Mobile pages are a 4.5: not squashed, broken. The palette-by-formula costs the remaining half point.

SCORE: 5.5/10

### Iteration 4 — three-critic result: 6 · 5.5 · 5.5 → **median 5.5**

First iteration scored by three fresh critics instead of one. All three split the
verdict the same way: **desktop ~6–7** ("the home page at desktop is a real 7," "desktop
pages are a 6"), **mobile ~4.5** ("not squashed, broken"). The site is graded on both.

**What all three agreed on** (3/3 unless noted):

| Finding | Notes |
|---|---|
| The F-15 editorial render now breaks the visual language | The homepage went to blueprint linework this pass; the one photographic-grade image on the model page reads as "a different product." Two of three call it the single highest-leverage gap. "The drawings are the voice." Fix: draw the F-15 in the same hand, callouts = section nav. |
| Mobile has outright defects | Hero void (diagnosed: dark ink on navy — `.stageImageWrap` flips `color` to the paper register at ≤767px but `.stage` still paints navy), ledger rows clipped mid-word, variant strip stranding a "5E" fragment, "CONFIGURATION ATLAS" colliding with "Share view." |
| F-15 body composed backwards, same paragraph twice | Principle 6 from the brief — Kimi's balance ran out before it. |
| Hero: the number should lead, in the serif, with one caption line | The `$10.7B` "looks like terminal output"; the citation "mixes prose, a program name, a FY, a hash, and a caveat in one run." |
| Numbering starts at 02 | The hero is plate 01 and never says so. "Reads as a bug, because it is one." |
| Ledger says everything twice; agency table too long on desktop | The mono annotation restates the row; mobile's 6-rows-plus-link is the right design, desktop should match. |
| F-15 hero chrome is dashboard, not editorial | "Sound off" on a static image "is a mystery." One text link, in the caption. |
| F-15 page shows no dollar figure above the fold (2/3) | "On a site called Fiscal Receipts a program page whose first 900px contain zero dollars is a broken promise." |

**The critique that cuts deepest** (critic A): the type recipe itself — old-style serif,
tracked mono eyebrows, cream, terracotta, hairlines, 01/02/03 keys — "is the 2025–26
anti-default default, what a model produces when told 'editorial, not SaaS.' Avoiding
cards is not the same as having a voice. The drawings are the voice; the type system
around them is off the shelf."

**Score movement:** with single critics the trajectory read 5.5 → 6 → 5.5 → 6. The
three-critic median for the biggest pass of the loop is 5.5. Given ±1.5 of measured
single-judge variance, none of the earlier moves was resolvable from the score; the
consensus *findings* were.

**Post-critique fix (Claude, one line):** `.stageImageWrap` at ≤767px now sets
`background: var(--stage-paper)` alongside the existing `color: var(--stage-ink)`. The
mobile hero renders headline → number → caption → the shipyard plate on paper. Tokens
gate passes. This is the third time this session a plate or figure has been rendered in
the wrong ink for its ground (iteration 2's `$10.7B`, iteration 4's F-15 gutters, this);
a gate that samples computed `color` vs `background-color` contrast on every
`[data-testid=receipt-moment]` figure and every plate `<svg>` at both 1440 and 390 would
have caught all three before a critic did.

## What moved the score — and what didn't (through iteration 4)

**Trajectory:** baseline 5.5 (×8 consensus) → 6 → 5.5 → 6 → **5.5 (3-critic median)**.

**What the score is measuring.** Single-judge variance on identical inputs measured at
±1.5 points; the loop's earlier ±0.5 moves were inside the noise. The stable signal has
never been the number — it is what every critic names independently.

**What earned credit every time it landed:**
- Verified structural moves (palette unification, the one-composition hero, the drawn
  plates). Critic A on iteration 4: "the drawings are the voice."
- Restraint. All three iteration-4 critics credited the absence of cards, gradients,
  radius, hover chrome as load-bearing.
- Kimi refusing to fabricate: not merging two datasets, not rewriting cited prose,
  stopping at constraints. Nothing it declined to do ever cost a point.

**What cost points:**
- Bold moves with a broken execution detail (iteration 2's invisible number: 6 → 5.5).
  The fix was two CSS properties; the cost was a full half-point and a wasted cycle.
- Executing a critic's *prescription* literally (iteration 1) — capped at 6 because the
  structure underneath was unchanged.
- Mobile treated as reflow. Named in 4/4 baseline critiques and 3/3 at iteration 4; the
  three iteration-4 critics put desktop at 6–7 and mobile at 4.5, and grade the whole.
- The one non-drawn asset. Once the homepage went to linework, the imagegen F-15 — the
  best single image in the repo — became the outlier every critic named first.

**What the method got right:** consensus extraction across independent critics; the
judge panel for plates (spike 5 → panel winner 7.5); three-lens majority votes; making
Kimi prove fixes numerically; hand-completing only to Kimi's own written intent.

**What the method got wrong:** single critics for four iterations; an orchestrator
harness that killed Kimi mid-reconnaissance; a `$(cat)` that mangled dollar signs; not
budgeting Kimi's time; not noticing the Moonshot balance; a resume that re-ran judges.

**Where the ceiling is now.** Critic A: the type recipe itself is "the 2025–26
anti-default default … the type system around [the drawings] is off the shelf." The
remaining distance to 9 is not fixes — it is (1) one drawing language on both pages,
(2) mobile as its own composition, (3) a type system with a voice of its own. The first
two are executable in this loop. The third is a design decision the loop was not scoped
to make.

## Run 2 — Iteration 5 — mobile as its own composition

**Brief:** mobile only. The eleven defects all three iteration-4 critics named, each with
the critic's own fix; the principle "art-directed, not reflowed"; a section telling Kimi
what was completed by hand during its balance cutoff so it would not undo it; and a
geometric verification clause — every element in `main` at 390×844 must satisfy
`scrollWidth ≤ clientWidth` and `right ≤ 390`, overflow count reported, must be zero.

**Kimi's session:** 42 minutes (Moonshot refilled). Skill×1, Read×18, Bash×36, Edit×13,
Write×2.

### Kimi's report (verbatim)

Both desktops are pixel-consistent with the pre-pass references — no regression. All verification done.

## Report

**Files changed (one line each):**
- `src/app/page.tsx` — hero plate now renders twice from the same `<use>`: `meet` for desktop, `xMinYMid slice` crop for ≤767, exactly one visible per width — **#12**.
- `src/app/home.module.css` — hero crop rules (`aspect-ratio: 4/3`, bow-held slice); ledger restacks delta-first (mono 1.375rem line one, name line two, agency+italic note line three, `nowrap` removed from `.reconNote`, `.signalTag` gone below 768, `data-mobile-pair` contract kept); callout key sits compact directly beneath the plate, leaders off — **#1, #2, #12**.
- `src/app/editorial.css` — footer links two columns at ≤639 (not three at ~110px); corpus-sentence links become `inline-block` so clauses wrap whole, "24" never orphans — **#3, #4**.
- `src/components/f15-family-browser.tsx` — eyebrow gets one-line `FIELD GUIDE · AIR · USAF` spans for ≤760; rail inline margin becomes `--variant-gap/--variant-step` CSS vars (same 5px/year desktop axis); brief restructured heading-first in DOM with era+source as mobile spec cells — **#5, #7, #8**.
- `src/components/f15-family-browser.module.css` — round-6 block: stepped variant list (stair indent + 3px/year vertical gap = 99px of real space before the EX, active in rust); section tabs wrap to two lines (snap-scroll was vetoed by the overflow proof — its children are offscreen by construction); topic nav single column, active rust, chevrons gone; 2×2 spec block, `hyphens: manual` on values; sound/share become the quiet line off the plate — **#5, #6, #7, #8, #9, #10, #11**.
- `src/components/f15-model.module.css` — at ≤600, `:not([data-active])` stage becomes the one mono line under the image (`F-15EX · EAGLE II · 2021 · Inspect in 3D`), corner stamp removed, illustration `cover`-cropped to cockpit/forward fuselage at `74% 42%` — **#6, #13**.

**Overflow measurement at 390×844 (playwright, every element inside `main`, `scrollWidth ≤ clientWidth+1` and `rect.right ≤ 390`): 0 elements on `/`, 0 on `/families/f-15/`.** (Exclusions, principled: `.sr-only` clipped to 1px by design; SVG descendants clipped by their `<svg>` viewport — the svg roots themselves measured.) Initial run caught 5 real items — the section-nav scroll strip — fixed by the wrap; first run also used the wrong F-15 route (`/companies/families/`), corrected to `/families/f-15/`.

Gates: tokens **pass**, motion **pass**, lint **pass** (0 errors). Desktop 1440 screenshots: both pages unchanged.

**Not closed:** defect **#14's optional half** (desktop agency index to 8 rows) — out of time; mobile stays the approved 6+link. Also: 2 pre-existing `f15-family-browser.test.tsx` failures in the funding absence state (`Budget source trail` region renders when a record exists but the year lacks a fact) — that `aria-label` structure predates this pass (verified in the pre-edit file), it's in the funding workspace I didn't touch, and changing region semantics to satisfy it is a data-meaning call, not mobile art direction. Helper artifacts left untracked for the human commit decision: `measure-390.mjs`, `shots-1440.mjs`, `shots-r6/`.

### Verified independently
- tokens PASS · motion PASS
- **My own playwright overflow measurement at 390×844, both pages: 0 overflowing
  elements, `document.scrollWidth = 390`.** Matches Kimi's report.
- Kimi's judgment call worth recording: it vetoed the critics' snap-scroll suggestion
  for the section tabs because "its children are offscreen by construction" — it would
  pass visually and fail the overflow proof — and wrapped them instead. The measurement
  clause shaped the design decision, not just the report.
- Kimi left three helper artifacts (`measure-390.mjs`, `shots-1440.mjs`, `shots-r6/`) in
  `site/` "for the human commit decision"; moved to scratch.

**F-15 at 390 now:** one-line eyebrow, stacked title, illustration cropped to the cockpit,
one mono line under the plate, the variant list as a vertical stair with the 33-year gap
as real space and EX in rust, tabs wrapping not truncating, single-column section nav,
heading before its content. Nothing clips.

### Critic A — Run 2 / Iteration 5

## 1. Aesthetic

This is reaching for the civic-reference-volume: the FT Visual desk crossed with a Haynes workshop manual and the NASA Graphics Standards reissue — cream stock, ink serif display, monospace for anything that is a *receipt*, and blueprint linework that says "we drew this from the P-40 page, not from a stock library." It wants the reader to feel the weight of a well-bound government atlas that dares you to check its footnotes: authority through restraint, evidence as decoration. The tabs, sidebar chevrons and ⌘K pill borrow from Linear/Vercel-era docs chrome to say "this is also a tool."

## 2. Studio execution

A top studio handed this brief would make one decision first and let everything hang off it: **the drawing is the product.** Every program gets the same hand — same stroke weight, same cream, same 3/4 orthographic view — and the budget figures sit *on* the drawing as callouts with leader lines, the way a DK cross-section labels a turbine. The homepage hero would not be tagline-left / illustration-right; it would be the Virginia-class submarine bled across the full width, anchored to the bottom edge of the hero, with "$10.7B" set as the one label on it and "Printed on the P-40 page" as the caption underneath — the receipt is the headline, no tagline needed. Down the page, the AIR and CYBER drawings would be numbered 01–03 as a single running system that starts in the hero (SEA), with the callout list living on the drawing rather than stranded in a half-empty right column.

The program page would open with the same linework F-15, not a photoreal render, and the 3D model would be the *destination* of "Inspect in 3D," never the hero. Below the fold, the section title would come first, then a two-column body (spec sheet left, narrative right) on one shared baseline. Type would be two families, not three doing four jobs: serif for display and narrative, mono for anything citeable (codes, hashes, figures, years) — sans retired entirely, or vice versa. Mobile would be its own composition: a one-screen hero (number + tight crop of the drawing), a horizontal scroll strip for tabs with actions folded into overflow, and the family timeline as a plain two-column list (year | variant) with no stagger.

## 3. Gaps

**1. Two illustration languages on the two pages that define the system.** Homepage: blueprint linework (submarine, F-35, server room). F-15 page hero region: a photoreal 3D game-asset render on cream, captioned "Simplified illustration." This is the single largest gap; it makes the model page look like a Sketchfab embed dropped into a book. Fix: redraw the F-15EX in the homepage's stroke and viewpoint. Keep the render behind "Inspect in 3D."

**2. Homepage hero is four corners and a dead middle** (1440, dark band, y≈50–740). Headline top-left, submarine mid-right cropped at the viewport edge, "$10.7B" bottom-left, ~250px of empty navy between headline and number. Fix: one lockup — bleed the drawing full-width and bottom-anchored, set the number as a label on it, drop the tagline or shrink it to a kicker.

**3. F-15 body reading order is inverted** (1440, below tabs, y≈930–1250). Column 2 carries the summary paragraph, ROLE/CREW and source link; column 3 carries the section *title* "Aircraft & configuration" and the narrative. The eye lands on body copy, then finds the heading to its right. Fix: title spans above; then two columns. Also "▸ Budget connection" is set in mono while "▸ Sources & dates" directly above is sans — visible seam.

**4. Mobile is a squashed desktop, both pages.**
- Home 390 hero runs ~2.5 screens; the submarine sits below the number at reduced scale, floating in dark space, then the ghosted carrier bleeds up behind the "A different way into the budget" heading (y≈1050–1200 at 390). Fix: one-screen hero, tight crop; kill the ghost image on mobile.
- F-15 390 timeline: the desktop's proportional horizontal axis has been rotated into a staggered-indent list with a ~100px void between F-15E (1988) and F-15EX (2021). It reads as a rendering bug. Fix: year | variant two-column list, no indentation, no proportional gaps.
- F-15 390 tabs wrap to two lines and the second line mixes "Family history" with "Compare aircraft" and "Research tray." Fix: horizontal scroll strip; actions into an overflow menu.
- F-15 390 hero image crop lops off the tail and both wingtips; it is a random rectangle, not a composed crop. Fix: art-direct a mobile crop (nose-to-canopy, or the whole silhouette small).

**5. The numbering starts at 02.** Homepage shows "02 / AIR" and "03 / CYBER"; the hero submarine is never labeled "01 / SEA." Either label it or drop the system. And the callout list ("01 Aircraft & engines…") sits at the top of the right column with ~400px of dead column beneath while the numbered circles on the drawing are 500px away. Fix: labels on the drawing with leader lines, or list beneath the caption.

**6. "Largest FY25→26 changes" rows are three text layers plus a truncated sentence** (1440, y≈1240–1400). Bold name, italic reconciliation note, then a middle column repeating "Long Range Kill Chains increased 3053% FY25→26" that truncates on row 2 ("…increased 106% …"). Fix: one line per row — name, agency, % as a secondary tabular figure, $ as anchor; move the reconciliation note to the expand.

**7. Fine type detail.** The "$10.7B" dotted citation underline at display size reads as broken (dots under part of the numeral). The metadata line under it runs six data types (name, year, agency, page, hash, note) as one paragraph — set it as label/value pairs. "F-15" display is a green-black that does not match the ink of the nav or the body. Three button styles on one page: the ⌘K pill, the "Fact IDs" outline, the rectangular "Inspect in 3D" with icon.

**8. The F-15 page is 65% chrome.** Eyebrow, H1, sub, hero, caption, timeline, tabs, sidebar — then one short section and a "next" link, and the page ends at 1500px. For the model program page, the money content is a tab away. Fix: bring one budget figure with its citation into the first screen, on the drawing.

## 4. AI tells

- **Hero-illustration-with-tagline template** on the homepage. The illustration is bespoke, the layout is not; "See what your tax dollars build." is a placeholder sentence.
- **Docs-app chrome** lifted wholesale: ⌘K search pill, "More ▾", tab row with right-aligned utility actions, chevron sidebar, "▸" disclosure rows, oversized "Next →" footer link.
- **Photoreal 3D asset + "Inspect in 3D" cube-icon button + "Sound off" toggle** reads as a feature checklist rather than an editorial decision.
- **Monospace-as-credibility** is overused: eyebrows, hashes, years, "CONFIGURATION ATLAS," table values, one disclosure label. It is justified for citeable figures, not for every caption.
- **Numbered eyebrow sections ("02 / AIR")** and **numbered hairline lists (01/02/03)** are Awwwards furniture.

Credit where it is load-bearing: no card grids, no three-up feature row, no gradient, no stats-row-of-big-numbers, no badge soup, no rounded-everything, and the tables are honest hairline tables. The restraint is real and is what keeps this above a 5.

## 5. Score

The concept — receipts as design, drawings as navigation — is genuinely memorable, and the homepage linework sections are the best thing here. But the page nominated as the template for every program page breaks the visual language with a render, inverts reading order in its body, and buries the money; and both mobile compositions are literal translations that expose the desktop scaffolding. Good instincts, structural seams.

SCORE: 6/10

### Critic B — Run 2 / Iteration 5

**1. AESTHETIC**

This is reaching for the naturalist's field guide crossed with a government ledger: cream stock, a bookish display serif, wide-tracked mono for plate numbers and IDs, hairline rules, a single rust ink, and blueprint-grade line drawings of hardware. The reference points are Stripe Press book sites and The Pudding's editorial data pieces on the type side, Jane's Fighting Ships / Haynes cutaway plates on the illustration side, and the mono-labelled evidence chips of a GAO report reset by someone who has read Bringhurst. It wants the reader to feel two things at once: that a budget can be *seen* like a machine, and that every figure on the page is a receipt they could take to court.

**2. STUDIO EXECUTION**

A top studio would start by choosing one illustration language and refusing the other. Right now the homepage is a line-drawn blueprint and the program page (the declared model for every program page) is a photoreal 3D render on a cream backdrop with drop shadow. Those are two products. The studio version draws the F-15EX the way the submarine and the F-35 are drawn, in the same line weight, with the same numbered callouts, and the "Inspect in 3D" affordance lives inside the plate as a plate-number footnote, not a button on the jet's nose.

The homepage would open on paper, not on a dark band. The dark hero is a SaaS landing convention grafted onto a paper product; no other page in the set uses it. The studio version begins with the submarine plate full-bleed as Plate 01, dock waterline as the horizontal datum, headline set in the left margin on that datum, and "$10.7B" treated as the plate's caption figure, not as a second headline competing with the first. Down the page, the rhythm becomes plate / legend / ledger, repeating, each plate numbered 01, 02, 03 consecutively, each legend sitting *on* the drawing with leader lines (the F-35 plate already has 01/02/03 callouts drawn on the equipment; the legend is 500px away in a separate column, so the pairing is lost). The tables would never span 1,250px with three columns; the ledger would either sit in a reading measure or earn its width with a sparkline per row.

The program page would be about the money. The model page, as shipped, is a hero plus one paragraph, stated twice in two columns, behind three stacked navigation layers (variant timeline, page tabs, section sidebar). The studio version puts the F-15EX procurement line and its receipt directly under the aircraft, on this page, with the prose as a marginal note beside the figure. One nav layer. One column of prose. The sidebar becomes a sticky TOC only when the page is long enough to need one; this one is a single screen.

Type: the studio version would use two families, not three. The invisible grotesque used for nav, body and table labels adds nothing; body would go into the serif's text cut, with mono for data. The display serif would be one weight; the current "F-15" is set in a much heavier cut than anything else on the site and reads as a fourth family.

Mobile would be its own composition: hero in one viewport; a mobile-specific crop or a side-profile silhouette for the jet (the three-view is the field-guide convention anyway); the variant timeline as a vertical rule with year ticks where a 33-year gap is a compressed break, not blank space; tabs as a horizontal scroll strip with actions elsewhere.

**3. GAPS** (ordered by how far each would move the work)

1. **Two illustration languages across the two pages.** Homepage plates are line art; the F-15 hero (desktop, y≈285–700) is a rendered product shot on a card with an inset border, a cream backdrop that does not match the page cream, and four UI chips in four corners ("Sound off", "Share view", "CONFIGURATION ATLAS", "Inspect in 3D"). The page the brief says is the model contradicts the site's own drawing system. Fix: draw the F-15 family in the blueprint idiom with numbered callouts; kill the card border and the backdrop mismatch; collapse the four chips to one caption line and one action.

2. **The model program page is thin and says everything twice.** F-15 desktop, y≈925–1250: the sidebar heading "Aircraft & configuration", the right-column h3 "Aircraft & configuration", and two paragraphs that restate the same fact ("A two-seat Eagle with digital flight controls, cockpit displays and updated avionics" vs "combines a two-seat airframe with digital flight controls and updated mission systems"). Three nav layers (timeline y≈760, tabs y≈850, sidebar y≈945) wrap one screen of content. Fix: one column of prose, spec (ROLE / CREW / FIRST DELIVERY) as a sidenote, budget line and receipt on this page beneath the aircraft, sidebar removed until a page is long enough to justify it.

3. **Homepage hero is three floating objects in a dark box.** Desktop y≈50–730: headline top-left, drawing mid-right with dead navy above the crane, stat bottom-left. The drawing stops arbitrarily rather than bleeding; the eye goes to the drawing, then to the mono "$10.7B" (which is optically heavier than the headline), and reaches the headline last. Mobile: the same band runs ~820px tall on a 390 screen, two full viewports of navy for one line, one number and a cropped, hairline-thin sub whose left dock is chopped. Fix: drop the dark band, treat the sub as Plate 01 on paper with headline on the waterline datum; on mobile, hero within one viewport, sub recomposed tight.

4. **The variant timeline is neither proportional nor even.** Desktop y≈760–810: A→B (1 year) gets ~165px, C→D (0 years) gets ~160px, E→EX (33 years) gets ~355px; a minimum slot width swamps the proportion, so the spacing reads as arbitrary. Mobile y≈625–950: the same data becomes a staircase of progressively indented rows with a ~100px void before F-15EX. The indent implies hierarchy (children), the void looks like missing content. Fix: pick proportional or even and commit; on mobile, a vertical rule with year ticks and an explicit compressed break ("33 yr") for the gap.

5. **The agency table spans empty width.** Home desktop y≈1290–1770: three columns across 1,250px, ~900px of nothing per row, 24 rows of it, mono values underlined so they read as broken links. Fix: reading-measure width, or add a column that earns the space (FY22–26 sparkline, share-of-total bar); remove underlines and use row hover or colour.

6. **"Largest FY25→26 changes" restates itself in the middle column.** Home desktop y≈1055–1160: column 2 ("Long Range Kill Chains increased 3053% FY25→26") repeats column 1's name; row 2 truncates with "…"; "3053%" has no thousands separator; the italic reconciliation note is too light at that size. Fix: kill column 2, set "+$7.45B · +3,053%" together on the right, tabular.

7. **Plate numbering starts at 02.** Home desktop y≈408 "02 / AIR", y≈688 "03 / CYBER". The hero submarine is presumably 01 / SEA but is never labelled. Fix: label it, or renumber.

8. **The ghost F-35 is an artifact.** Home desktop, the faded second aircraft bleeding off the right edge behind the main plate (y≈430–600) reads as an unfinished layer. On mobile it sits *behind the section heading*: "A different way into the budget." at 390 has a line-drawn jet nose poking through the text. Fix: remove it, or make it a deliberate registration ghost with a plate-note.

9. **Mobile tabs wrap and mix actions in.** F-15 390, y≈975–1020: "Aircraft | Budget & receipts | Countries & orders" then a second line "Family history | Compare aircraft | Research tray", so page tabs and tools share a line. Fix: horizontal-scroll strip for tabs; actions to an overflow.

10. **Mobile hero crop on F-15.** 390, y≈285–460: nose and half a wing, both tails chopped, image rectangle visible against page cream; "Sound off" / "Share view" controls land *below* the caption (y≈585), separated from the image they act on. Fix: a mobile crop or side profile; controls attached to the plate.

11. **Type hierarchy at the top of the F-15 page.** "F-15" (y≈120–200) is a heavier cut than every other serif on the site, set at ~2:1 to "The Eagle family." on a shared baseline; it reads as a different family. The tracked-mono eyebrow above it is ~18px and competes with the nav. Fix: one display weight; eyebrow down to 12–13px.

12. **Hairline soup.** Both pages separate every section, every row, every tab, every disclosure with a full-bleed rule; F-15 desktop has a tab underline at y≈875 and a second full rule at y≈925, 50px apart, with nothing between. Fix: rules reserved for tables; sections separated by space and scale.

13. **Three type families.** The grotesque used for nav, body and table labels has no character and dilutes the serif/mono pairing. Fix: body in the serif's text cut, mono for data, sans gone.

**4. AI TELLS**

- The triple-imperative tagline: "Explore the aircraft. Understand what gets funded. Follow every budget figure to its source." (F-15 both widths). Also "A different way into the budget." as a section head.
- Dark hero band + headline-left + illustration-right + big stat: the hero-with-illustration template, dressed in mono.
- Four-corner overlay chips on a hero image; outlined "Inspect in 3D" button with a cube icon.
- Chevrons on every sidebar item (F-15 desktop sidebar) as per-item affordance.
- Numbered 01/02/03 feature list beside an image, twice in a row on the homepage.
- "Search ⌘K" pill in the nav; "Fact IDs" as a top-level nav button (jargon).
- Disclosure rows with a count badge ("▸ Sources & dates 2"), one in sans and the next ("Budget connection") in mono.
- Footer with bolded inline stats ("1,938 program elements and 130,347 source citations across 200 contractor families and 24 agencies") plus the three-column link footer (Explore / Investigate / Verify & reuse).
- Uniform hairline dividers as the only separator vocabulary.

Avoided, to its credit and load-bearing for the score: no card grids, no gradients, no radius soup, no badge soup, no three-column feature row.

**5. SCORE**

There is a genuine point of view here, the F-35 plate is the best thing on either page, and the palette and mono discipline are real. But the two pages disagree about what the drawings are, the model program page is thin and triple-navigated with duplicated prose, the homepage hero is a floating-objects composition, the tables waste their width, and mobile is a squashed desktop with three visible defects (staircase timeline, wrapping tabs, ghost artifact behind a heading). Good professional work with seams you can see from across the room.

SCORE: 6/10

### Critic C — Run 2 / Iteration 5

## 1. Aesthetic

This is reaching for the *technical standards manual* tradition — Order's reissued NASA/EPA manuals, Jane's cutaways, Haynes exploded views — crossed with contemporary editorial data journalism (The Pudding, FT Visual, Bloomberg's diagram features), with the "receipt" conceit carried by a dot-matrix monospace for figures. Cream paper, ink linework, one rust accent, a bookish serif for headlines. It wants the reader to feel that a $10.7B line item is a physical object you can pick up, turn over, and read the label on — calm, authoritative, inspectable.

## 2. Studio execution

An Order- or Fathom-level version of this brief would make one decision the current site refuses to make: the drawn object *is* the interface. The exploded line drawing with numbered callouts on the homepage (02 / AIR) would be the program-page hero, and the callout numbers would be the section nav — 01 Aircraft & configuration, 02 Cockpit & software, 03 Electronic systems, 04 Support & tooling — leader lines running from the airframe to the rail. The photoreal render would not exist, or would live behind a secondary control.

The homepage hero would be entry 01 / SEA of the same series, not a separate composition. Headline, drawing, and figure would sit on one grid: the drydock baseline aligned to the number's cap height, the callout list beside it as on the entries below. Every figure frame down the page would be the same width and height, so the whitespace between drawing and list is identical each time and the page acquires a metronomic rhythm.

Type would use two voices, not three: serif for titles and running heads, mono strictly for figures, IDs, and captions. Tracking on eyebrows would be tight enough to read at speed. The provenance line under the hero number would be one line with a page reference and an arrow; the hash would live in the citation panel.

On mobile the studio version would be a different composition, not a squashed one: a nose-forward art-directed crop of the aircraft, a variant list with a right-aligned year gutter, tabs in a horizontal scroll strip with utilities moved to an overflow, and drawings redrawn or cropped to portrait so nothing leaks out of its frame.

## 3. Gaps

**1. The two pages speak different visual languages — and the model page is the one that breaks the system.** Homepage: ink linework on cream, exploded view with numbered callouts, and the explicit promise "Each illustration opens into explanations with receipts." Program page: a grey photoreal 3D render on a beige slab with an "Inspect in 3D" button (f15-1440, y≈285–705). The promise is broken the moment you click through. Fix: the program hero becomes the drawn, numbered exploded view; callout numbers map 1:1 to the left rail. Demote the render to a secondary mode. If the render must be primary, then the homepage must use renders too — not both.

**2. Homepage hero is three things in three corners.** (home-1440, y≈60–720.) Headline top-left, submarine floating mid-right in thin light lines on near-black, number bottom-left. Nothing shares a baseline. The drawing carries no "01 / SEA" label, so the series below starts at 02 — a numbering system that visibly skips its first entry. On mobile (home-390, y≈470–850) the drawing sits at the bottom of a tall dark band with a void above it; it reads as leftover. Fix: label it 01 / SEA, give it the same callout list as 02 and 03, align the dock baseline to the number's cap height. Mobile: crop to the hull only, full-width, directly beneath the headline.

**3. Actual collision on mobile.** (home-390, y≈980–1280 real.) The ghosted second-aircraft layer behind the F-35 exploded view overflows its container upward and runs lines through "Explore the systems, research, and support a program funds" and across the rust "Open the visual field guide" link. Same layer bleeds under the right-hand callout list on desktop (home-1440, x≈1030–1440, y≈1050–1300). Fix: clip the figure to its frame; delete the ghost layer — it adds nothing the exploded view doesn't.

**4. The variant timeline is neither a timeline nor a control.** Desktop (f15-1440, y≈750–810): A→B is one year and gets ~160px; C→D is zero years and gets ~160px; E→EX is 33 years and gets ~360px. The spacing reads as jitter, not data. Mobile (f15-390, y≈610–950): it becomes a staircase — each row indented further than the last, with a ~120px void before F-15EX. It looks broken. Fix: choose. A true proportional timeline with a visible year axis and ticks so the gaps read as meaning, or an evenly segmented control. Mobile: plain list, no indent, year right-aligned.

**5. The model program page ends after one paragraph.** (f15-1440, y≈930–1250.) Below the hero: a 55px dead band under the tab bar, then a lede that says "two-seat Eagle with digital flight controls, cockpit displays and updated avionics," then a paragraph that says "two-seat airframe with digital flight controls and updated mission systems." Then the footer. The page that is supposed to set the standard is mostly chrome. Fix: kill the lede; move ROLE / CREW / FIRST DELIVERY into a spec strip directly under the hero plate; let the section paragraph carry the two disclosures; close the dead band.

**6. Three text columns with no shared edge.** (f15-1440, y≈930–1250.) Left rail starts at y≈930, middle eyebrow at y≈962, right heading at y≈970. "Read the aircraft source" sits at y≈1105 against nothing. Fix: one hairline across all three columns at the top; heading and eyebrow on the same baseline; or collapse middle and right into one column.

**7. Two display voices fighting on one baseline.** "F-15" in the dot-matrix mono is optically heavier than "The Eagle family." in the serif at the same size (f15-1440, y≈130–200). The eye stops on the mono and reads the serif as a subtitle, though they are one sentence. Worse, the same mono is "$10.7B" on the homepage — so the face now means both *figure* and *designation*, which dilutes the receipt conceit. Fix: title in serif; mono reserved for numbers, IDs, and captions.

**8. Eyebrows tracked too wide, set too light.** "VISUAL FIELD GUIDE · AIR · UNITED STATES AIR FORCE" (f15-1440, y≈95) is ~50 characters of all-caps mono at roughly 0.2em tracking in mid-grey on cream. Slow to read and low contrast. Mobile already shortens it to "FIELD GUIDE · AIR · USAF" — desktop should match. "CONFIGURATION ATLAS" in the hero corner (y≈300) is an orphan; delete it or make it the plate caption.

**9. Provenance line under the hero number reads as debug output.** (home-1440, y≈640–700.) "Virginia Class Submarine 2013 Navy · Printed on the P-40 page: $10.7B #d9dcdc48 P-40 detail · P82026 net procurement — the workbook TOA figure above adds advance-procurement rows." Five type styles, three lines, a hash in the open. This is the most important number on the site. Fix: one line — "Virginia-class submarine · Navy · FY2024 P-40, p. N ↗" — and the ID goes in the panel.

**10. "Largest FY25→26 changes" rows carry four type styles plus a redundant middle column.** (home-1440, y≈2440–2720.) Mono ID, bold name, regular agency, italic note, then a right-aligned mono sentence that repeats the name ("Long Range Kill Chains increased 305% FY25→26"), then the delta. Fix: drop the sentence or reduce it to "+305%"; name in one weight, note in one grey line beneath.

**11. Twenty-four agency rows on the homepage.** (home-1440, y≈3020–4120.) A quarter of the page is a table that belongs on /agency/. Mobile already does it right — six rows and "All 24 agencies →". Desktop should do the same.

**12. Mobile F-15 hero crop is object-fit:center, not art direction.** (f15-390, y≈290–560.) Left wing and one tail cut off; "Sound off / Share view" exiled below the disclaimer paragraph, separated from the image they control. Fix: a deliberate nose-forward crop; controls overlaid in the plate or directly under its caption.

**13. Mobile tab bar wraps into two rows and mixes nav with utilities.** (f15-390, y≈1180–1230.) "Family history | Compare aircraft | Research tray" is a second row of three unrelated things. Fix: horizontal scroll strip for the four tabs; Compare and Research tray into an overflow.

**14. Homepage vertical rhythm drifts.** Hero → section: ~90px. F-35 caption → 03 / CYBER: ~60px. Cyber caption → "Largest": ~100px. → "Browse": ~110px. Figure widths differ (F-35 ~800px, cyber lab ~600px) against a fixed right column, so the gutter between drawing and list is different each time. Fix: fixed figure frame; list top-aligned to the frame.

**15. Fine detail.** "Fact IDs" as a header-level button exposes an internal concept. "Sound off" on a budget document promises audio, which is a gimmick on this page. The "F-15" mono title and the "$10.7B" underline-dot treatment are the two moments where the receipt idea actually lands — that treatment should be used on every figure, consistently, or not at all.

## 4. AI tells

- The photoreal aircraft render on a beige slab with a cube-icon "Inspect in 3D" button is the generic 3D-product-hero template. It is the single most machine-looking element on either page and it sits on the page meant to be the model.
- Eyebrow → big serif headline → subtitle of three short imperative sentences ("Explore the aircraft. Understand what gets funded. Follow every budget figure to its source.") is the AI copy-and-layout tricolon.
- Identical "01 / 02 / 03" three-item callout lists, twice in a row, each with exactly three items.
- Wide-tracked all-caps mono eyebrows on every section.
- The oversized serif "Next, follow the public money → F-15EX budget & receipts" footer CTA is the docs-site "next page" pattern.
- Chevron-right on every left-rail item; ▸ disclosure rows with count badges ("Sources & dates 2").
- A stat tile of one ("$10.7B" with an eyebrow).

To its credit: no card grids, no gradient blobs, no icon rows, no uniform border-radius soup, tables built on hairlines rather than cards, one accent color used with restraint. It avoids most of the thousand-times patterns — which is why it is not scoring lower.

## 5. Score

The desktop homepage has a real idea and is close to good professional work. The program page — the one that is supposed to be the template — abandons the idea for a stock-looking render, ships a broken timeline and a body that ends after one paragraph, and the mobile versions have a genuine collision bug and a staircase that reads as unfinished. Considered intent, unresolved system.

SCORE: 5.5/10

### Iteration 5 — three-critic result: 6 · 6 · 5.5 → **median 6** (confounded)

**All three critics were scoring a regression.** Kimi's mobile pass rendered the hero
plate twice ("`meet` for desktop, `xMinYMid slice` for ≤767, exactly one visible per
width") and hid each with a single-class `display: none`. Line 50 of `home.module.css` —
`.stageImageWrap svg { display: block }`, a descendant selector at (0,1,1) — outranked
both. Both copies rendered at every width; the second overflowed the hero into the field
guide. All three critics named it ("ghost F-35 behind the section heading", "ghosted
second-aircraft layer overflows upward", "the ghost F-35 is an artifact"). Kimi's overflow
proof was horizontal-only (`scrollWidth`, `right ≤ 390`) and could not see a vertical
bleed. Fixed by matching the specificity; verified one copy per width at 1440 and 390.

**A gate lesson, the fourth of its kind this session:** the proof Kimi was asked for
constrained what it checked. Every verification clause so far has been a floor
(contrast ≥ N, overflow = 0, gate passes); none has been "nothing renders outside its
section." A per-section `getBoundingClientRect` containment check would have caught
this and the iteration-2 collision both.

**Consensus across the three (3/3 unless noted):**

| Finding | Status |
|---|---|
| F-15 photographic render breaks the drawn language | plate panel in progress |
| Ghost / duplicate hero copy | **fixed** |
| F-15 body: heading after content, same paragraph twice | still open — two iterations, never reached |
| Mobile tabs wrap into two rows mixing nav with utilities | open |
| Mobile F-15 crop is `object-fit: center`, not art-directed | open |
| Numbering starts at 02 | open |
| Ledger's middle mono sentence restates the row | open |
| 24 agency rows on desktop; mobile's 6+link is right | open |
| Provenance line under `$10.7B` "reads as debug output" (2/3) | open |
| The mono "F-15" title dilutes the receipt conceit — mono should mean *figure* (2/3) | open |

**The mobile timeline is a critic-variance casualty.** Iteration-4 critics asked for "the
33-year gap as real space." Kimi built a vertical stair with a 99px gap before the EX.
Iteration-5 critics: "reads as a rendering bug," "looks like missing content." Kimi did
exactly what was asked. Critic B's synthesis is the way out: "a vertical rule with year
ticks and an explicit compressed break ('33 yr')" — the gap as a *labelled* break, not
empty space. Prescriptions flip; label the data and the flip stops mattering.

### F-15 plate panel — result

Three angles drawn (front elevation, planform, hangar-floor side elevation), then three
judges with different lenses picked among the three SVGs **and the existing imagegen
line plate** as a fourth candidate. Two harness failures on the way — every agent hit the
Claude session limit at once, then the refiner lost its connection — each resumed.

**Planform, 3–0, every margin "clear."** The existing raster got zero votes: "a different
book entirely — photographic tone, gradients, no navy, no currentColor." The front
elevation "collapses the airframe into a cross and cannot show tandem seating"; the side
elevation "leaves the top half of the plate as empty hangar." The planform "uses the F-35
plate's grammar verbatim, and the two silhouettes do the differentiating, which is exactly
how a series of plates should work."

Refined once against the judges' fixes (wing sweep, CFT bulge, intake boxes, stabilator
tip, fin caps, tandem-seat legibility). Staged as `public/exhibits/plates/f15.svg`,
287 KB, root id `f15-plate`, no `<style>`, no `<text>`, four anchors measured from the
DOM: configuration [39.1, 60.4] · cockpit [35.8, 49.8] · electronics [22.1, 49.8] ·
support [28.2, 54.0]. The illustrator's own remaining caveat: at a 200px thumbnail the
twin fins read as two short dashes; the tell survives at ~450px.

**Method note:** putting the existing raster on the ballot was the honest move — it
could have won, and then no one would have redrawn. It lost 3–0 on the same-book
criterion, which is the criterion six page critics had just written.

## Run 2 — Iteration 6 — the F-15 in the same book; the last six-of-six items

**Brief:** the drawn F-15 planform as the page's plate with callouts 01–04 that ARE the
section nav; the F-15 body (heading first, duplicate deleted, spec block); `01 / SEA`;
the ledger's redundant sentence; desktop agency index to 8 + link; the `$10.7B`
provenance to one line; mobile tabs separated from utilities; the timeline gap as a
labelled `33 yr` break; mono for figures only. Verification: per-section containment
at both widths (0 escapes) and one plate copy per width — the two properties the last two
passes each shipped a defect against.

**Kimi's session:** 60 minutes. Skill×1, Read×14, Bash×48, Edit×43, Write×2.

### Kimi's report (verbatim)

All eight items are in. Report:

**Files changed (one line each)**

- `src/components/f15-model.tsx` — **#1**: drawn planform replaces the editorial `.webp` as the default plate (two `<use>` renders — `meet` ≥768 / `xMinYMid slice` ≤767), `CONFIGURATION ATLAS` deleted, `01 / AIR` stamp top-left, four numbered callout markers with staggered leaders wired to `onTopicChange`/`aria-pressed` (anchors per the measured table).
- `src/components/f15-model.module.css` — **#1**: `.poster .plateFull` / `.poster .plateCrop` hide rules out-specificity `.poster svg`; full copy in an aspect-correct 15/8 wrapper so `%`-anchored markers land on the drawing under `meet`; crop copy `inset:0` letting the svg's own `slice` clip (nothing escapes); marker/leader styles, active = rust; `img`/`cornerStamp` rules deleted.
- `src/components/f15-family-browser.tsx` — **#1/#2/#7/#8**: sound toggle gated behind `[data-active]`; eyebrow one string (`Field guide · Air · USAF`); middle-column lede deleted, spec block (Role / Crew / First Air Force delivery / Source) directly under the heading; labelled 33-yr gap break in the rail (railItem wrapper + keyboard-focus fix); tabs wrapped into page-tabs vs utility rows.
- `src/components/f15-family-browser.module.css` — **#1/#2/#7/#8**: share top-right, sound only when live; dead band closed (`inspection` padding 0, brief border/margin gone); one-column brief, 4-cell spec row ≥761; eyebrow tracking 0.08em; disclosure summaries one typeface; stair indent dropped, `gapBreak` rule/ticks/mono label; tab rows at ≤760.
- `src/app/page.tsx` — **#3/#4/#5**: hero `01 / SEA` stamp; signal annotation dropped at every width, `+$7.45B · +3,053%` together on the right (tabular, `toLocaleString` thousands separator); agency rows 8 at ≥768 / 6 on phones.
- `src/app/home.module.css` — **#3/#4/#5**: `heroStamp` (plate register on navy, stage register on paper), `moverPct`, `signalTag` rules deleted, "All 24 agencies →" visible at all widths.
- `src/components/receipt-moment.tsx` — **#6**: caption = `Virginia Class Submarine · Navy · FY2024 P-40 · PB2026 ↗` (the receipt button is the first `data-fact-id`, opens the panel); the workbook-TOA sentence moved **verbatim** to the receipt's footnote; fact-id/basis chips stay in the DOM.
- `src/components/receipt-moment.module.css` — **#6**: `captionCite`/`receiptNote` styles (chips `display:none`, gate is visibility-independent); old inline-chip rules deleted.
- `scripts/gates/token-allowlist.json` — stale `#92b0b5` entry removed (its rule died with `cornerStamp`), as the constraints require.

**Gates:** tokens `true` · motion `true` · `npm run lint` 0 errors (18 warnings, all pre-existing — none in my diffs except none).

**Measurements (reported, not asserted):**
- **(a) Containment: 0 escapes** on `/` and `/families/f-15/` at both 1440×900 and 390×844. Methodology note: raw run counted 5, all `<use>` elements — drawing bounding-rect geometry, not paint; computed `overflow: hidden` verified on every plate svg, so svg-internal nodes are excluded and the svg elements themselves are checked and contained. This is exactly the ghost-plate class of bug the check exists for, at the HTML layer where it lives.
- **(b) One plate per width:** hero — full `display:block`/crop `none` at 1440, crop `block`/full `none` at 390. F-15 — identical pattern per width. Field-guide plates are single renders, each visible.

**Judgment calls (not silent):** #6 — the footnote keeps its P-40 cite (the figure) inside the moved sentence; stripping it would rewrite a cited sentence and remove the gate-held chip DOM, and "delete duplicates" loses to "never rewrite what a number means." The caption line itself carries no figure and no hash. #8 — the h1 was already the display serif at one weight (`--font-editorial` 400; the register fonts only reach the funding workspace), so the actionable work was the eyebrow and taking the "Budget connection" summary off mono.

### Verified independently
- tokens PASS · motion PASS · lint 0 errors
- vitest: 1323 passed, 3 failed — the two pre-existing funding-workspace failures, plus
  `doc-toc.test.tsx` (a resize test; passes 3/3 in isolation twice; pre-existing `M` file;
  flakes under the full parallel run). None are Kimi's.
- **One plate per width, by rect:** F-15 full 806×430 / crop 0×0 at 1440; full 0×0 /
  crop 354×240 at 390. Hero identical pattern. My first check read `getComputedStyle().display`
  on the `<svg>` and reported both `block` — wrong instrument: Kimi hides the *wrapper*,
  and a child's computed display is its own value. Rect is the honest measurement.
- **Containment:** my first pass counted 18 escapes on the F-15 page, all "Official
  record" source blocks extending below their section. All were descendants of a closed
  `<details>` — Chromium keeps layout boxes for them but does not paint them
  (`elementFromPoint` hits the next element). Not a defect; Kimi's check excluded them
  correctly. Real escapes: 0.

**Two of Kimi's judgment calls, both correct and both stated rather than hidden:** the
`$10.7B` footnote keeps its P-40 cite inside the moved sentence because stripping it would
rewrite a cited sentence and remove gate-held chip DOM — "delete duplicates loses to never
rewrite what a number means." And the `F-15` h1 was already the display serif; the mono
I described in the brief only reaches the funding workspace. It fixed what was actually
there.

### Critic B — Run 2 / Iteration 6

**1. AESTHETIC**

This is reaching for the annotated technical manual as editorial object: Dorling Kindersley cutaway spreads and Haynes-manual exploded views, set with the typographic apparatus of a modern data desk (FT Graphics, The Pudding) and the "receipt" conceit carried by monospaced numerals. Cream stock, near-black ink, one rust accent, transitional serif for display, mono for codes and money. It wants the reader to feel they are holding an authoritative placard from an aviation museum that happens to have the Treasury printout stapled to the back — calm, exact, sourced.

**2. STUDIO EXECUTION**

A top studio handed this brief would treat the line drawings as the entire identity and build both pages as one continuous system around them.

Homepage: the hero would be a single locked composition, not a headline in one corner, a stat in the other, and a drawing floating in between. The submarine would bleed off the band's edge or span its full width; the $10.7B would be set as the caption of the drawing, part of the sentence ("the largest line this year is this boat"), not a KPI module. The three field-guide sections would vary in scale — one full-bleed, one inline at half-width, one cropped detail — so the page has a rhythm instead of the same template three times. The numbered legend would sit against the drawing it annotates, connected by leader lines or proximity, not exiled 800px to the right behind hairline rules. The "biggest changes" and "browse by agency" tables would share one grid, one measure, one numeral treatment, and the methodology prose would be footnotes, not ledes.

Program page: the variant timeline would be the spine — full-width, genuinely proportional, so the 33-year gap between F-15E and F-15EX reads at a glance and the active variant drives the drawing above it. There would be one navigation layer, not four. The fold would show money, because that is the product's promise. Mobile would be composed fresh: the drawing re-cropped for portrait, the timeline a compact strip, tabs that scroll rather than wrap, no sidebar ghost.

**3. GAPS**

**Gap 1 — the desktop hero is three orphans in a dark box.** Home 1440, y 30–370. Headline top-left, ~300px of empty navy, then the "LARGEST FY2024…" eyebrow, "$10.7B", and a two-line caveat pinned to the bottom-left. The submarine sits centered-right with dead space on all four sides. The eye goes to the headline, then falls into the void, then hunts. Fix: make the number the drawing's caption (right column, under the hull, one line: "$10.7B · Virginia-class · FY2024 P-40"), let the drydock gantry run to the band's right edge, and shrink the band so headline and drawing share a vertical center. Kill the caveat line here; it belongs in the citation panel.

**Gap 2 — program page chrome outweighs content.** F-15 1440, y 830–1280. Tabs row, then a utilities row (Compare aircraft / Research tray), then a four-item chevron sidebar, then two collapsibles — four affordance layers around a 90-word paragraph and four facts. Above the fold the page shows zero dollars on a site whose subhead says "Follow every budget figure to its source." Fix: put the first procurement figure directly under the drawing as its caption (mirroring the home hero). Collapse the sidebar into in-page section headings with a sticky mini-index. Keep tabs; drop the utilities row into the tab bar's right edge as icons only.

**Gap 3 — the variant timeline is misaligned and encodes nothing.** F-15 1440, y 750–810. The rule runs from x 96 to x 1180 while the caption rule above and tab rule below run to x 1344 — a 164px short stop visible at a glance. Spacing is neither even nor proportional: F-15C and F-15D are both 1979 yet sit at different x. Fix: pick one encoding. Proportional is the story (A–E are a cluster; EX is a 33-year outlier), so share a tick for C/D and let the E→EX run be long. Extend to the content edge.

**Gap 4 — the mobile timeline looks like a rendering bug.** F-15 390, y 620–990. Six stacked rows with unexplained blank gaps between B/C and D/E, then a 1px vertical tick with a floating "33 yr" label before EX. Only one gap is annotated; the others are silent whitespace. Fix: either label every gap over five years in the same way, or drop the proportional idea on mobile and use a dense six-row list with the year column doing the work.

**Gap 5 — mobile is a reflowed desktop, not a composition.** F-15 390: tabs wrap to two lines ("Family history" alone on line two, y 1035); the sidebar becomes a four-item menu stacked above the content it points at (y 1140–1280), so the reader scrolls past a table of contents to reach one paragraph. Home 390: the dark hero band is gone entirely (the desktop's one strong identity move), and the submarine is cropped at the right edge with the drydock gantry sliced off (y 195–320). Fix: horizontal-scroll tab strip; delete the sidebar on mobile in favor of inline section headings; keep the dark band; supply a portrait crop of the submarine (hull only) or rotate the composition.

**Gap 6 — three identical field-guide modules.** Home 1440, y 480–1100. "02 / AIR" and "03 / CYBER" use the exact template: label, drawing left, numbered list right with hairline rules, caption below. The right-hand lists (01 Aircraft & engines…) are ~800px from the tiny callout circles on the F-35 they reference; the 01/02/03 markers on the drawing are roughly 14px and nearly invisible. Fix: legend goes under the drawing beside the caption, markers go to 22px with rust fill on all (not just one as on the F-15), and the second drawing should be a different scale from the first.

**Gap 7 — rust is doing three jobs.** Across both pages: links ("Open the visual field guide", "All 24 agencies →"), active state (F-15EX, "Aircraft & configuration"), and data (+$7.45B · +3,053%). The delta column on Home 1440 y 1240–1360 reads as a column of links. Fix: rust for interactive and active only; data figures in ink with a direction glyph.

**Gap 8 — the changes table has a 700px gutter per row.** Home 1440, y 1240–1360. PE code, bold name, agency, italic reconciliation note on the left; figures hard-right. The eye has to travel the full measure five times. The 60-word methodology paragraph above it ("when the list is all increases, that is the result, not a filter") is apologia in the lede slot while a footnote already exists below. Fix: narrow the table to ~880px or dot-lead; move the paragraph into the existing footnote.

**Gap 9 — fine type.** F-15 1440 y 130–190: "F-15" at ~96px and "The Eagle family." at ~44px share a baseline; the size jump with no weight or style change reads as a subtitle squeezed onto the wrong line. Either one size, or stack with the family name as a true deck. Mono eyebrows use two different tracking values ("FIELD GUIDE · AIR · USAF" wider than "01 / AIR"). Agency table: single-letter mono abbreviations "N", "F", "A" after Navy/Air Force/Army are noise; underlined mono dollar figures look like spreadsheet hyperlinks. "Inspect in 3D" is a boxed button, "Share view" is a bare icon link — two affordance styles 350px apart in the same region.

**Gap 10 — the model program page ends in a void.** F-15 1440, y 1360–1440: ~100px of nothing between the "Next" row and the footer. For the page every other program page will copy, it feels unfinished rather than restrained.

**4. AI TELLS**

- Big-number hero stat with tracked-caps eyebrow ("LARGEST FY2024 PROGRAM ELEMENT IN OUR CORPUS" → "$10.7B"). The pattern is a KPI card wearing a serif.
- Mono tracked-caps eyebrows on everything: "01 / SEA", "02 / AIR", "ROLE / CREW / FIRST AIR FORCE DELIVERY / SOURCE", "AGENCY / PROGRAMS / FY24". This is the default "editorial" register of generated sites in 2026 and it is everywhere here.
- Numbered feature list (01 / 02 / 03) with hairline dividers, repeated three times.
- Chevron on every sidebar item.
- ⌘K search pill plus an outlined "Fact IDs" button — stock SaaS nav.
- "▶ Sources & dates 2" collapsible rows.
- Bold inline stats in the footer blurb ("1,938 program elements and 130,347 source citations across 200 contractor families and 24 agencies") — the stats row in prose form.
- Three-column footer link block (Explore / Investigate / Verify & reuse).
- Headline-plus-subtitle-on-one-line ("F-15 The Eagle family.").
- Mixed border radii: search pill fully rounded, "Fact IDs" and "Inspect in 3D" at ~4px.

What it avoids, to its credit: no card grid, no gradient blobs, no hover affordances, no hero illustration-with-tagline template — the drawings are real work and the paper/ink/rust palette is a genuine choice. That is why this is not a 5.

**5. SCORE**

A distinctive idea with an asset worth building around, executed with visible seams: the hero does not compose, the program page buries the product's promise under navigation, the timeline is misaligned and mis-encoded, and mobile is a reflow with one section that looks broken. The mono-eyebrow register and the tripled feature-list module cost it further. Good professional work that has not yet been edited.

SCORE: 6/10

### Critic A — Run 2 / Iteration 6

## 1. Aesthetic

This is reaching for the annotated technical plate: Jane's and Haynes cutaway manuals, patent drawings, DK cross-sections, filtered through the current editorial-data house style (The Pudding, Bloomberg Graphics, Stripe Press) — cream paper, black ink, a bookish transitional serif for the voice, wide-tracked mono for the apparatus, one rust accent for "you are here." The receipt metaphor is carried by the mono dollar figures. It wants the reader to feel that public spending has been catalogued like a museum collection: sober, physical, verifiable, worth lingering over.

## 2. Studio execution

A top studio would commit to the paper. The dark hero band is the only reversed element on the site, and it costs the one thing the brand has — the drawings. White hairlines on black at that scale lose the drydock entirely; the same submarine in black ink on cream, run edge to edge with the headline set into it, would be the cover of the book this site wants to be. The "$10.7B" would sit directly under the headline as a deck, not stranded 220px below it.

They would build one plate system and use it on both pages: number and title top-left, drawing filling the frame, key/legend as a caption strip along the bottom (museum-label logic), corner registration marks on every plate or none. The homepage would then read as a contact sheet of three plates — 01 SEA, 02 AIR, 03 CYBER — dense, rhythmic, each one a door into a program page whose plate is visibly the same object at larger scale. Right now the homepage plates and the F-15 plate are two different systems.

On the program page they would collapse the three stacked navigation strata (tab strip → sidebar → repeated h2) into one, run the variant timeline to the margin, and use the empty right third of the plate for the thing that belongs there — the variant timeline or the callout key — rather than two floating utilities.

Mobile would be its own composition: drawing first at full bleed with a mobile-specific crop, headline over it, stat as caption; tabs as a scrolling strip; sidebar folded into in-place accordions. The vertical timeline with the "33 yr" gap on the F-15 mobile page is already the right instinct — the studio version would apply that instinct everywhere.

## 3. Gaps

**1. Homepage hero is unresolved (home-1440, top 740px).** Headline top-left, stat bottom-left, ~220px of dead black between them, drawing floating at 55% width in the right half with no relationship to the text column. The drawing is under-scaled and low-contrast; the "LARGEST FY2024 PROGRAM ELEMENT IN OUR CORPUS" eyebrow is ~10px on black and effectively invisible. Fix: drop the dark band, run the submarine in ink on cream across the full width, lock the stat under the headline as a deck. If you keep dark, thicken the linework and scale the drawing to fill the right column edge to edge.

**2. Two plate systems (home 02/AIR and 03/CYBER vs f15-1440 plate).** Home plates put the drawing centered in the left 65% and the three-item key right-aligned 400px away with nothing between; the plate title ("F-35 aircraft procurement") arrives *below* the image while the number sits above. The F-15 plate is a framed object with corner marks, a grid, corner controls, and the title bottom-left. Fix: one frame, title top-left, key bottom as a caption strip, corner marks on all or none (the cyber plate and the hero submarine have none; the F-35 and F-15 plates do).

**3. F-15 plate: empty right third and a timeline that doesn't reach the grid (f15-1440, y≈285–810).** The drawing occupies x≈375–1015 of a 96–1344 frame; the right side holds only "Share view" and "Inspect in 3D," whose right edges don't even align with each other. Below it, the variant timeline stops at x≈1180 while the tab row beneath runs to 1344 — a 164px misalignment visible at a glance. Fix: span the timeline to the margin (or right-align F-15EX to it), and move the timeline or the callout key into the plate's right column.

**4. Three navigation layers before content (f15-1440 y≈830–1010; f15-390 y≈1000–1290).** "Aircraft" tab → "Aircraft & configuration ›" sidebar → "Aircraft & configuration" heading. On mobile this becomes timeline + wrapped tabs + Compare/Tray row + a full-width sidebar list — roughly 1,000px of navigation between the plate and the first sentence. Fix: kill the repeated h2 or the sidebar; on mobile, make sections in-place accordions.

**5. Mobile home hero crop (home-390, y≈390–650).** The drydock is clipped at the right edge — the crane tower is cut mid-structure, and it reads as accidental, not as bleed. Fix: a mobile art-direction crop, or scale-to-fit with the headline stacked over it.

**6. Tab strip wraps on mobile (f15-390, y≈1000–1050).** "Family history" orphans to a second line with the active underline on line one. Fix: horizontal scroll strip with edge fade.

**7. Timeline spacing is categorical on desktop and proportional on mobile.** Desktop ticks are equally spaced; mobile spacing reflects years (A/B tight, B→C wide, only the 33-year gap labeled), so the unlabeled gaps look like padding errors. Pick one; if proportional, annotate every gap.

**8. Fine detail.**
- Home section heads ("A different way…", "Largest FY25→26 changes", "Browse by agency") are all the same ~30px; the scale has one step between hero and everything else. Add a deck size or shrink these.
- "$10.7B" in heavy mono at display size reads as a terminal, not a receipt; tracking is too tight for that weight. Try the serif with tabular figures, or a lighter mono weight with +2% tracking.
- Changes table rows carry five typographic voices (mono ID, bold sans, regular sans, italic sans, rust mono). Cut to three; the italic descriptors belong in a tooltip or mono small caps.
- Agency table codes "N," "F," "A" beside Navy / Air Force / Army are cryptic where "DARPA" and "SOCOM" are not.
- Disclosure triangles ("▶ Sources & dates 2") are raw `<details>` defaults.
- "Share view" on mobile is an orphan line between the caption and the timeline.
- "Fact IDs" in the nav is an internal tool leaking into the public header.

## 4. AI tells

- Hero big-number stat ("$10.7B") — the stats-row pattern, even if singular and justified by the product.
- Rule-of-three keys beside every plate (01/02/03 × three plates) — a feature list in a legend's clothing.
- Two pill buttons in the nav (Search ⌘K + Fact IDs); four icon+label utilities on one program page (Share, Inspect in 3D, Compare, Research tray).
- Per-item chevrons on every sidebar link.
- Default disclosure triangles.
- The cyber plate's magnifying-glass zoom callout and generic server-rack-plus-desks isometric — the one drawing that looks like stock.
- Three-column footer link grid.

What it avoids matters: no card grids, no gradients, no radius soup, no hero illustration-with-tagline template in the strict sense, and the drawings are original. That restraint is why this scores above competent.

## 5. Score

The F-15 page top — eyebrow, the "F-15 / The Eagle family." lockup, the framed plate, the mobile timeline with its gap annotation — is a distinctive, real system and sits near a 7.5. The homepage undoes it: an unresolved hero, a tonal split that hides the signature asset, a second plate system, and a clipped mobile hero a studio would never ship. Averaged honestly, this is good work with structural seams still showing.

SCORE: 6/10

### Critic C — Run 2 / Iteration 6

**1. AESTHETIC**

This is reaching for the technical-editorial register: patent-drawing and 1970s systems-manual line art (the plan-view F-35, the elevation of the submarine in its gantry) laid onto cream stock with rust ink and monospaced figures — the "receipt" conceit made literal. The nearest references are *Works in Progress* / Stripe Press book design, Businessweek's Turley-era data pages, and the Eyewitness/field-guide tradition of numbered callouts. It wants the reader to feel that the Pentagon is a machine you can open and inspect, and that every figure on the page is sworn to a document.

**2. STUDIO EXECUTION**

A top studio handed this brief would do the following differently, concretely:

- **One composition, not three objects.** The home hero would make the submarine drawing the subject and hang the $10.7B off it as a callout — a leader line from the hull to the figure — instead of parking the headline top-left, the stat bottom-left, the drawing right, and a floating "01 / SEA" at top-centre. The drawing would set the scale for the type, not the other way around.
- **One drawing language.** Submarine = side elevation at hairline weight; F-35 = plan view at medium weight; cyber = stocky isometric with a different callout scale; F-15 = plan view, rotated, at an even lighter weight than the F-35. A studio would pick one projection family and one line weight and commission the cyber scene in it, because right now the cyber illustration is the one piece that reads as clip-art.
- **A stable index.** "01 / SEA, 02 / AIR, 03 / CYBER" on the home page; "01 / AIR" on the F-15 page. The chapter numbers would be a real system across the site, not local ordinals.
- **Two type families that fit, not three that don't.** The mono is a generic Courier-like at a heavier colour than the serif; the labels ("LARGEST FY2024 PROGRAM ELEMENT…", "FIELD GUIDE · AIR · USAF") are set at two different sizes and trackings on the two pages. A studio would use a mono with matched x-height (Berkeley/GT America/Söhne Mono class), one label style, and would tighten the display serif at 64px+ — "See what your tax dollars build." is sitting at body tracking.
- **The program page fold contains a fact.** The drawing, the four spec cells and the lede paragraph would share the first screen. Today the first sentence of substance on the model program page is at y≈1030 on a 1531px page, under two tiers of navigation.
- **A timeline that is a timeline.** The variant strip would be proportional to years, full-width to the grid, active state as a position on the axis — which, notably, the mobile version already does (the "33 yr" bracket) and the desktop doesn't.
- **Mobile as its own composition.** Keep the dark band (it is the identity), crop the submarine on purpose (a detail of the hull) rather than clipping it, scroll the tabs horizontally, collapse the section rail into an "on this page" control, and stop turning the changes table into a stack of big numbers.

**3. GAPS** (largest first)

1. **The model program page is chrome around one paragraph.** F-15 1440: drawing (280–715), caveat, variant strip, tab bar, left rail, spec row — and the actual content is a single 5-line paragraph plus two collapsed disclosures, then a giant "F-15EX budget & receipts →" and the footer. This is the template for every program page, and it has more navigation surface (4 tabs + Compare + Research tray + 4 rail items = 10 nav affordances) than content. Fix: pull the spec row and lede up beside the drawing; kill one navigation tier (the rail's four items can be in-page anchors under the h2); do not ship a tab whose content is one paragraph.

2. **Home hero is unresolved.** Home 1440, y 40–740: headline top-left, 130px dead zone, stat block bottom-left, drawing right, "01 / SEA" floating above the band's centre and attached to nothing. Fix: leader the $10.7B to the hull; move "01 / SEA" to the drawing's lower-left corner exactly as "F-15EX · EAGLE II · 2021" is placed on the program page (which is the correct pattern — use it here); compress the band so the type and drawing share a scale.

3. **Mobile home throws away the identity.** Home 390, top: the hero is cream, not dark, and the submarine is clipped mid-hull at the right edge — it reads as a layout accident, not a crop. Fix: keep the dark band; crop to a chosen detail with the same corner registration dots the F-15 uses.

4. **Callout lists are orphaned from their drawings.** Home 1440, the "01 Aircraft & engines / 02 / 03" lists sit at x≈1040–1344 while the F-35 ends at x≈1000; the callout discs on the wing are ~12px and 500px away from the list they index. Same for the cyber block. Fix: leader lines, or a legend directly under the drawing beside the caption — the caption is already in the right place and the list should join it.

5. **Illustration inconsistency** (detailed above). Specific: the cyber isometric at 390 wide (home 390, y≈1290–1560) collapses to an unreadable grey mass with numbered dots floating in it; the F-15 at 390 loses its callouts entirely. Fix: one projection family, one weight, and mobile-specific crops rather than scaling down the full scene.

6. **Desktop variant strip is a tab bar wearing a timeline's clothes.** F-15 1440, y≈750–810: 1972→1973 (1 yr) gets the same gap as 1988→2021 (33 yr); the strip ends at x≈1180 while the grid runs to 1344, leaving a dangling gap on the right. Mobile gets it right. Port the mobile logic back.

7. **Tab bar wraps on mobile.** F-15 390, y≈1000–1045: "Family history" drops to its own line under the underline rule, and "Compare aircraft / Research tray" become a third row. Then four rail rows before any content. Fix: horizontal scroll for tabs; rail becomes a select or a sticky mini-TOC.

8. **Two affordance styles in one region.** F-15 1440: "Share view" (icon + text, no border, top-right of drawing) versus "Inspect in 3D" (bordered button, bottom-right). On mobile "Share view" is stranded as a lone link under the caveat paragraph (F-15 390, y≈600). Fix: one toolbar row under the drawing carrying both.

9. **Leftover guides in the F-15 drawing.** Three faint vertical lines at x≈548, 777, 1005 cut through the aircraft and mean nothing. Either label them as station lines or remove them.

10. **Caveats compete with captions.** "Printed on the P-40 page…", "Simplified illustration. A/C and B/D share schematics…", the six-line hedging paragraph under "Largest FY25→26 changes" — all set in the same grey sans at the same size as descriptive captions. Establish a footnote register (smaller, symbol-led, indented) so honesty doesn't read as body copy.

11. **Changes table overloaded.** Home 1440, y≈1240–1360: each row carries a mono ID, bold name, agency, italic reconciliation note, and two mono deltas at the right edge. On mobile (home 390, y≈1980–2400) the deltas become 22px mono headlines above each name. Fix: proportional bar for the dollar delta, the percentage as a secondary figure, the italic note demoted to a footnote mark.

12. **Header doesn't carry the voice.** Both pages: sans wordmark with a receipt glyph, small sans nav, a pill search and a bordered "Fact IDs" button — generic app chrome above an editorial page. Set the wordmark in the serif and drop one of the two right-side controls.

13. **Type detail.** Display serif at default tracking (home headline, "F-15"); mono labels at two sizes/trackings between pages; mono chips under $10.7B ("FY2024 P-40 · PB2026 ↗") in a different chip style from the agency abbreviations ("N", "OSD", "DARPA") in the table below. Pick one label spec and one chip spec.

**4. AI TELLS**

- Three-beat imperative taglines: "Explore the aircraft. Understand what gets funded. Follow every budget figure to its source." and the marketing h2 "A different way into the budget." — this is model prose.
- Big-number-with-eyebrow stat block ("LARGEST FY2024… / $10.7B"), and the footer paragraph with bolded counts ("1,938 … 130,347 … 200 … 24") — a stats row hidden in a sentence.
- Exactly three numbered items beside every illustration, every time.
- The mobile changes table degrading into a stack of giant mono numbers.
- The generic isometric server/desks scene.
- Default details/summary triangles ("▶ Sources & dates 2", "▶ Budget connection") and default chevrons on every rail item.
- Hairline rules under every list item, table row and rail item — the everything-is-a-row pattern.
- The oversized "Next, follow the public money →" hand-off link.

It avoids card grids, gradients, rounded-everything, hover-card affordances and badge soup, and the palette is disciplined — which is why this scores above the midpoint despite the tells above.

**5. SCORE**

There is a real point of view here — the cream/rust/mono receipt register and bespoke line art are choices most sites never make, and the mobile timeline bracket shows someone thought. But the model program page is a shell, the hero is three things in three corners, the illustrations speak three dialects, mobile drops the brand on the home page and wraps the tabs on the program page, and the copy carries the machine's cadence. Good professional work with structural seams still showing.

SCORE: 6/10

### Iteration 6 — three-critic result: 6 · 6 · 6 → **median 6** (unanimous, clean)

The first round with no confound and no disagreement. All three at exactly 6.

**The gap that was #1 in nine of nine critiques is closed and no critic mentions it.**
Not one of the three names the F-15's illustration as a gap. Critic A: "The F-15 page
top — eyebrow, the lockup, the framed plate, the mobile timeline with its gap annotation
— is a distinctive, real system and sits near a 7.5." Six iterations ago every critic
scored the F-15 page as the 7 and the homepage as the drag. **The two pages have swapped
places.** The homepage hero is now the #1 gap in 3/3.

**What the three name now (3/3 unless noted):**

| Gap | Where it points |
|---|---|
| Homepage hero: "three orphans in a dark box" — headline, stat, drawing sharing no relationship | design: leader the `$10.7B` to the hull; number as the drawing's caption; two of three say drop the dark band and run the submarine in ink on cream |
| Program page is "chrome around one paragraph" — 10 nav affordances, no dollar figure above the fold | **content**: the page needs money in the first screen; that is a data decision |
| Desktop variant strip stops 164px short of the grid; categorical spacing while mobile is proportional | execution: port the mobile logic back |
| Callout keys 400–800px from their drawings; markers ~12–14px | design: legend under the drawing beside the caption |
| Mobile tabs wrap; mobile home hero is cream not navy and clips the hull | execution |
| Two plate frame systems — homepage plates vs the F-15 plate differ on corner marks and title position (2/3) | design |
| The cyber isometric "is the one piece that reads as clip-art"; three projections, three weights (1/3, C) | illustration |
| The copy is "model prose" — "Explore the aircraft. Understand what gets funded. Follow every…", "A different way into the budget." (3/3 as an AI tell) | **copy** |
| Mono eyebrows at two sizes/trackings between pages; `$10.7B` "reads as a terminal"; three type families | **type system** |
| The header is "generic app chrome above an editorial page" (1/3) | identity |

**Reading the trajectory with the noise removed.** Single-critic scores through
iteration 3 swung inside ±1.5 of measured variance. Three-critic medians: 5.5 → 6 → 6,
with the middle one confounded by a ghost render. The site has moved from a page-critic
5.5 to a unanimous, clean 6 while absorbing: a palette unification, a one-composition
hero, four hand-drawn plates replacing clay renders, a mobile pass that measures zero
overflow, a full-nav header on both pages, and every six-of-six item closed. Each closed
gap revealed the next tier. That is the shape of the curve: **execution moves the
findings, not the number, because the number is anchored by the weakest remaining
part, and the weakest remaining parts are now content, copy, and type identity.**

**What a 9 would need, in the critics' own terms:** (1) a hero that composes the
drawing and the number as one object; (2) money on the model program page's first screen;
(3) copy that isn't a tricolon; (4) a mono that matches the serif's x-height and one label
spec across the site; (5) one projection family across all four plates. (1) and (5) are
executable in this loop. (2) is a data decision. (3) is editorial. (4) is the type system.
Three of five are outside what a design-execution loop can decide.

## First full `npm run verify` of the loop — 20 pass, 5 fail

Every critic through six iterations scored dev-server screenshots. The 25-gate suite had
not run against a build since the plates landed. It caught six things the critics
structurally cannot see:

| Gate | Finding | Whose |
|---|---|---|
| 24 datatruth | `/methodology/` cites "24 site verification gates"; the registry has 25 | **mine** — I added gate 25; the site's own provenance discipline caught it. Meta corrected to the derived count. |
| 2 render-static | 18 chart-contract violations: every plate is `svg[role="img"]`, which the gate treats as a chart needing a `<desc>` + table view | Kimi's markup is correct a11y; the gate had no category for a drawn plate. **Gate patched:** `[data-illustration]` keeps name + `<desc>`, waives the table view (a plate encodes no figures; a table for it would be fabricated). Kimi adds the attribute and the `<desc>`. |
| 6 a11y | 7 dark-mode contrast failures, all in the footer: `#fafafa` on cream, 1.09:1 | Kimi — iteration 3's forced-cream footer never set its own dark-mode ink |
| 6 a11y leg (e) | Fact-ID chip (12px, 3.21:1) larger and less legible than its figure (11.52px) in the receipt footnote | Kimi — iteration 6 moved the sentence and shrank the figure under its chip. ROADMAP #43's contract, held by the gate. |
| 3 render-live | footnote runs 101 chars/line against the 80-char spine ceiling | Kimi |
| 1 build | `/companies/` +65 B and `/coverage/` +90 B over their weight ceilings — pages the loop never touched | Kimi — iteration 4 put the four-`data-stat` corpus sentence into `layout.tsx`, so every page carries it; linkgraph only needs it on home |
| 1 build | sitemap origin mismatch | **mine** — built with the production `NEXT_PUBLIC_SITE_URL` but verified without it. (Corrected in iteration 7: the gate's placeholder scan is *unconditional*, so a placeholder build can never pass; build AND verify must both carry `NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com`.) |
| 3 render-live | no `button[aria-controls="mobile-nav-panel"]` at 390 | pre-existing; no diff on those lines |
| 1 build | 4 stale ledger entries (under ceiling, headroom overstated) | re-measure after the compliance pass |

**The lesson, plainly:** a screenshot critic and a contract gate see different halves of
the same page. Six iterations of critic-scored work accumulated a dark-mode footer at
1.09:1, a chip outranking its figure, a 101-character line and two pages over their
weight ceiling — none visible in a 1440×900 light-mode PNG. The fast-gate set each
iteration ran (tokens, motion, lint) is source-scan only. `npm run verify` needs a build
and ~10 minutes; it should have run at least every other iteration.

## Run 2 — Iteration 7 — the compliance pass (gates, not critics)

No critic this iteration. The brief was exactly the four verify findings that were Kimi's
(`scratchpad/r2-brief-7.md`): `data-illustration` + `<desc>` on every plate svg; the
footer's dark-mode ink; the footnote chip/figure hierarchy and its measure; the corpus
sentence back to the homepage only. ~30-minute budget, "do not touch anything a critic
said."

### Kimi's report (verbatim)

> All four items closed and gate-verified.
> - `src/app/page.tsx` — #1: `data-illustration` + `<desc>` on both hero plate svgs and the field-guide gallery svg (descs via `PLATE_DESCS`, crop gets its own bow-section sentence).
> - `src/lib/program-exhibits.ts` — #1: added exported `PLATE_DESCS` — one sentence per subject, the single desc source for gallery + program exhibit.
> - `src/components/program-exhibit.tsx` — #1: exhibit plate svg gets `data-illustration` + `<desc>{PLATE_DESCS[config.subject]}</desc>`.
> - `src/components/f15-model.tsx` — #1: both F-15 plate svgs get `data-illustration` + `<desc>` (full planform; nose-and-cockpit crop).
> - `src/app/home.module.css` — #2: the forced-cream footer rule now also pins `--foreground: var(--stage-ink)` and `--muted-foreground: var(--stage-muted-ink)` in the same declaration block; #3: the ≥768 `.receiptDock` block adds `--muted-foreground: var(--plate-soft)`.
> - `src/components/receipt-moment.module.css` — #3: `.receiptNote` font-size `.72rem`→`.75rem` (figure 12px, no longer below its 12px chip); #4: `max-width: 34rem`→`var(--measure)` (54ch — 60ch measured out marginal at ~84 cpl, so the existing token it is).
> - `src/app/layout.tsx` — #5: corpus sentence replaced with `<FooterCorpus counts={counts} />`.
> - `src/components/footer-corpus.tsx` (new) — #5: client component, `usePathname()` check (the SiteHeader mechanism), renders the sentence verbatim only on `/`.
>
> **#2 — footer, forced dark on the forced cream (was 1.09:1 / 2.91:1):** `.site-footer-corpus` 5.00:1; the four `a[data-stat] > strong` 12.44:1 each; `.site-footer-bottom > span` 5.00:1; `time` 5.00:1.
> **#3 — footnote pair on the navy plate:** figure 12px, 15.07:1; chip 12px, 10.85:1 (was 3.21:1).
> **#4 — footnote measure:** 74 chars/line (was 101).
>
> Gate outputs: tokens true · motion true · lint 0 errors · render-static true · build false only on the four placeholder-origin lines and one stale f15 ledger note — no page over its ceiling · spine PASS (228 prose blocks, none past 80 cpl) · linkgraph true · a11y true.
> Not closed: 2 pre-existing `f15-family-browser.test.tsx` failures (funding-absence region), a file this pass never touched.

### Verified independently (production build, `NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com`)

| Claim | Instrument | Result |
|---|---|---|
| Plate svgs carry `role="img"` + `data-illustration` + `aria-label` + non-empty `<desc>` | regex over `out/index.html` and `out/families/f-15/index.html`, every `<svg>` containing `/exhibits/plates/` | 6/6 (hero ×2, gallery f35 + cyber, F-15 ×2); descs 88–133 chars ✓ |
| Footer dark-mode ink | playwright, `colorScheme: "dark"` and `"light"`, computed colour vs first opaque ancestor background, WCAG ratio | dark = light: corpus 5.00:1, four `strong` 12.44:1, bottom span 5.00:1, `time` 5.00:1 ✓ — the forced-cream rule now decides both halves of the pair |
| Footnote figure ≥ chip; chip ≥ 4.5:1 | same, on `.receiptNote` | figure 12px @ 15.07:1, chip 12px @ 10.85:1 on navy (1440); 12.44:1 / 5.00:1 on paper (390) ✓ |
| Footnote measure | note width 376px at 12px | ≈63 cpl ✓ (Kimi's 74 was the widest line; the spine gate passes either way) |
| Corpus sentence home-only | `grep -l site-footer-corpus` over `out/` | only `out/index.html`; four `data-stat` links present there ✓ |

**Two defects Kimi's pass introduced that no gate can see — found by looking at the drawings, not the code.** Kimi wrote the `<desc>` sentences from the exhibit `caption` strings, and two of those captions were themselves stale from the clay-render era:

- `f35`: desc + caption said "symbolic support and software tiles" — the live run-2 plate is a planform on a hangar floor with a tow tractor, a boarding ladder and work stand, a ground power cart on a cable, and an equipment box aft. No tiles.
- `cyber`: desc + caption said "conceptual diagram of connected devices" — the live plate is three isometric lab benches: instruments and a whiteboard, a desk with monitor beside a server rack, an open shielded enclosure under a magnifier.

Both `caption`s render *visibly* under the plates and double as the svg `aria-label`, so the page was describing drawings that were no longer on it. Corrected in `program-exhibits.ts` to what is drawn (illustration disclaimers, not cited prose — the "never rewrite" rule is about numbers and their sentences). Rule for next time: **a `<desc>` is written from the image, never from a string about the image.** Kimi can read PNGs; the brief should have pointed it at the plate renders.

### The rest of the verify run — what was mine, what was Astra's

- **Stale ledger entries** re-measured with the gate's own `zlib` level 9 on the production build; `measured` fields refreshed for `/families/f-15/` (677,253 / 68,720 — 1,280 gzip bytes left), `/companies/families/` (227,031 / 26,796), `/data/` (96,469 / 13,991), `/methodology/` (150,448 / 42,234). **No ceiling raised.** Only the f-15 entry actually fired the 2× rule; the other three were refreshed while there.
- **The origin contradiction** resolved by reading the gate rather than guessing: the sitemap-origin leg compares against the verify-time env (default placeholder), and the placeholder scan is *unconditional*. So a placeholder build can never pass, and a production build verified without the env fails the sitemap leg. Both runs in the earlier table were env mistakes, one each. The only consistent invocation is `NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com` on **both** `npm run build` and `npm run verify` — which is also what `deploy.sh` requires.
- **`mobile nav: no button[aria-controls="mobile-nav-panel"]`** was labelled "pre-existing" for two iterations on the strength of "no diff on those lines." Actually reading it: Astra's untracked `site-header.tsx` sets `aria-controls` only while its Radix dialog is open — correct ARIA (the portalled panel is not in the DOM while closed; a reference to a nonexistent id is the defect) and pinned by Astra's own `site-header.test.tsx`. The gate's *finder* was written against the old static `mobile-nav.tsx`, so the leg returned before measuring anything — a vacuous FAIL that was hiding a real measurement. `mobile.mjs` now finds the trigger by its accessible name, opens it, then asserts `aria-controls === "mobile-nav-panel"` on the open trigger. First real result on this branch: **17 links in a 390px panel, all on screen, none clipped.**
- **The two `f15-family-browser.test.tsx` failures** (Kimi, twice: "pre-existing, funding workspace, not mine" — true) are Astra's test against Astra's component: the test holds that no region named "Budget source trail" exists when the selected year has no cited figure. The `<section>` wrapped both branches. A `<section>` is a `region` only while it has an accessible name, so the name is now conditional on `fact` — no layout change, and semantically right: a coverage note is not a trail. 45/45 in the file; **1,326/1,326 site-wide.**
- Lint: the one loop-caused warning (`ArrowLeft` imported after iteration 6 removed the rail chevrons) dropped. The other 17 are pre-existing in gate scripts and an unrelated test.
- Noted, not fixed (Astra's in-flight CSS): `.fundingAbsence` and `.fundingChartFrame` carry `grid-column`/`grid-row` placements as if they were siblings of `.receiptPaper` in the `.fundingSheet` grid, but the TSX nests both inside it (`display: block`), so those placements are inert and the chart renders inside the paper column. Whoever finishes the funding workspace should decide which of the two the design is.

### Iteration 7 — result

`NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build && … npm run verify` on the
exact working tree: **25/25 gates PASS**, `npm run test` 1,326/1,326, `npm run lint` 0
errors (17 pre-existing warnings, none in loop-touched files). Screenshots in
`scratchpad/shots/r2-7/`. Nothing committed — the tree is the user's to commit, as author
Andes Lee.

**What the compliance pass cost against the critic score: nothing, by design.** It touched
no composition. The state going into iteration 8 is the unanimous-6 tree of iteration 6
with its gate debt paid, plus honest captions under two plates.

### Going into iteration 8 — what a 9 needs, sorted by who decides

The six critics of iterations 5–6 agree on the residual gaps. Three are executable; three
are decisions this loop cannot make on its own.

*Executable (Kimi, one brief):*
1. Hero composition — the headline, the receipt and the plate still read as three orphans;
   2 of 3 critics say drop the dark band and set the hero on paper like everything below it.
2. F-15 variant timeline misaligned with the grid (164px short of the right edge).
3. Callout keys live beside the plate; critics want them under the drawing, tight to it.
4. Two plate frame systems (homepage stamp+caption vs F-15 stamp+variant line+caption).
5. Mobile tabs wrap to two rows; a scroll strip with a peek was the ask.

*Decisions (owner):*
- **Content** — the program page has no money above the fold; the critics call it thin. The
  fix is which figure leads, which is a claim about what the page is for.
- **Copy** — "model prose" on both pages; the critics can tell. Rewriting cited sentences is
  forbidden to Kimi (rightly); new uncited copy is an editorial call.
- **Type** — the display serif / dot-matrix mono pair is "an anti-default default." A new
  face is an identity decision, not a fix.

## Run 2 — Iteration 8 — content, copy and type as SYSTEMS

The owner opened the three decisions with one constraint: "all 3 can be changed but
needs to be scalable and reproducible across other content and programs on
fiscalreceipts.com." So iteration 8 is not a rewrite of two pages. Each decision became a
rule, a token set, or a template that every program page and family page inherits, with a
gate that would catch a regression. The dark band: 2 of 3 critics said drop it; it goes.

### The design phase — a 23-agent workflow, three tracks, judge panels

Three read-only maps first (type, content, copy inventory), then per track: independent
proposals from different angles → independent judges → synthesis. Scores are summed over
judges; disqualifications override the tally.

| Track | Proposals | Judges | Result |
|---|---|---|---|
| Type | 3 (paper of record · engineering document · the receipt itself) | type director · perf engineer · analyst reader | All three converged on the Adobe **Source** superfamily (Source Serif 4 + Source Code Pro — one designer lineage, x-heights 475/478/478: the critics' "mono that matches the serif"). Split only on the sans: **Title Block** (Source Sans 3) 113 · Public Record (Public Sans) 112 · Source Receipt (no sans) 107. Two judges grafted "money in the serif, never the mono" (`--font-figure`). |
| Content | 2 (inherit the AnswerStrip · the Family Receipt) | provenance auditor · reporter on a phone | **The Family Receipt** 64–52. Violations fixed in synthesis: a kicker that omitted "cited"; a fallback that would rank `enacted` against `total`; ledger rows without a visible fid; the 100%-reconciliation composition of the $3.01B must be declared. |
| Copy | voice doc, then 3 sets (wire desk · museum label · civic plain language) | reporter · analyst · citizen | **Wire desk** 126 · civic 108 · museum 109 — the shortest true sentence, the document and the year doing the talking. |

**What the maps found that changed the briefs.** The site-wide type was literally system
stacks: the display serif was Iowan Old Style *Bold* on a Mac (500 snaps to 700),
Palatino on Windows, Georgia on Android — "anti-default default" was exact. Astra had
vendored Source Serif 4 + IBM Plex for the F-15 page alone (two products, again). The
vendored subsets carry no italic and no `→`; the `/flow/` Sankey labels are laid out in
Python with a per-character estimator derived from Avenir Next; F015EX's FY2026 request is
100% reconciliation-bill money; the copy inventory found 287 uncited strings, FOUR parallel
vocabularies for the same 13 program sections, THREE label sets for the same four F-15
topics, and no central home for any of it.

### What landed before Kimi's passes (mine)

- **Type declaration site** (`globals.css`): four `@font-face` (Source Serif 4 Roman +
  Italic 400, Source Sans 3, Source Code Pro — 193,060 B, vendored under
  `public/fonts/<family>/v<N>/` with PROVENANCE.md, SHA-256, the fontTools metadata and the
  served `unicode-range`); metric-matched `local()` fallbacks generated from the font
  tables by `scripts/fonts/fallback-metrics.py` (size-adjust + ascent/descent overrides so
  the swap does not move the LCP heading); faces → roles (`--font-figure` = serif,
  `--font-label` = sans, `--font-id` = mono); the size ladder (`--text-*`, `--fig-1..7`);
  trackings; composite `--type-*`; base heading/prose rules; the ONE label / figure /
  identifier spec (`.t-label`, `.t-figure--N`, `.t-id`) and `[data-plate-mark]`. The F-15
  module's seven `@font-face` deleted, its `--register-*` aliased for the fold; the
  `f15-register` and dead Barlow directories retired; preloads + immutable header.
- **Mirror rule honoured:** `flow_chart.py`'s estimator re-derived for Source Sans 3 in
  Chromium (every bucket ≥3% over the measured glyph; `LABEL_H` 13.2 → 14.3 because the
  em box is 1.424em), and the shipped `flow_chart.json` re-placed with the exporter's own
  `_place_labels` (`scripts/relayout_flow_labels.py`) — only `lbl`/`ldr` changed,
  byte-identical otherwise. A full `export-site` was not run: the other active session
  had already exported at 23:16 with a changed `hhi` schema, and a re-export from this
  checkout would have clobbered it (the shared-lake hazard, both directions).
- **Gates:** 25 tokens gained check 6 (the ladder — 338 sizes/trackings off it today,
  frozen shrink-only by `TYPE_ALLOWLIST_EMIT=1` after the fold) and check 7 (declaration
  site complete and alone: no `--register-*`, no `--font-editorial` consumer); **26 type**
  (rendered: faces loaded, no Google Fonts request, every label/figure/heading on spec,
  12px floor, weights, money never in the mono, `font-mono` ratchet); **27 copy** (VOICE.md
  as ~22 regex legs over the built text, cited/data text out of scope by attribute; the
  program meta-title shape); answerfold's **family-fold** leg; program-skeleton **leg (o)**
  (recomputes the family lead from the sidecars and holds every attribute, the kicker's
  counts, the ledger order, the program-page tile identity); basis indexes `/families/*/`;
  a11y samples the F-15 page; build.mjs **fonts leg** (every `url(/fonts/…)` exists and
  matches its PROVENANCE hash, no dead asset, immutable header, both preloads); lighthouse
  audits `/families/f-15/` and `/programs/`.
- **The rule:** `src/lib/family-lead.ts` (pure), proven on F-15 / Virginia-class /
  Tomahawk / AMRAAM from the real sidecars (`family-lead.test.ts`, 8 tests).
- **The voice:** `docs/superpowers/VOICE.md` (28 rules, slot patterns, fixed sentences,
  label vocabulary) and `src/lib/copy.ts` (formatters, lockups, empty-state grammar,
  `FIXED`, `ANSWER_LABELS`, `SECTION_LABELS`, nav, every slot string for home / F-15 /
  program template / chrome). Owner override recorded: "Missing coverage is not zero
  spending." is doctrine and stays.
- Kimi's standing CLAUDE.md gained the type system, so every future pass knows the
  vocabulary without a brief.

Three Kimi passes follow: 8a type adoption, 8b content + composition (family receipt,
program-hero figure, hero-as-plate-01 on paper, one plate frame, callout keys under the
drawings, timeline to the grid edge, mobile tab strip), 8c copy wiring. Then the full
registry and the three-critic panel.

### Pass 8a — type adoption (Kimi, 2h35m)

Brief: `scratchpad/r2-brief-8a.md` — "the gate output IS your worklist." Kimi worked the
tokens gate from 349 errors to **0** (338 ladder violations, 9 `--font-editorial`
consumers, the F-15 register, the raw `monospace` shorthand), file by file, then built and
ran gate 26 against the built site: **0 errors** on 9 routes × 2 viewports, 35,208 text
elements — every label 12px/500/uppercase in the sans, every standalone figure in the serif
at a ladder step with tabular figures, every identifier in the mono, nothing under 12px
outside plate marks, no italic but the serif's, no request to Google Fonts. 1,335/1,335
tests; lint 0 errors. ~70 files. The one test that pinned a removed heading utility moved
to the new contract with a comment.

Two judgement calls it made, both right: the amber/blue caution and link chips stayed
`font-mono text-xs` rather than `t-id` because `.t-id`'s unlayered colour would have
beaten the colour utilities the brief said to keep; and dark-plate identifiers took
`font: var(--type-id)` in-module for the same reason. One it got wrong, mine to undo: it
added a **mono preload** because gate 26 leg (0) required all three faces *loaded* and on
`/flow/` at 390 no identifier paints. The spec said the mono is CSS-discovered; the gate
now asks the browser to `load()` each face from the origin instead of requiring it on the
critical path, and the preload is gone. `font-mono` ratchet frozen at 539
(`type-allowlist-ratchet.json`); `type-allowlist.json` needed **zero** entries.

**The shared lake moved under the branch — twice.** Another session's export rewrote
`programs.json` (23:16, then 03:37) with a two-tier concentration schema
(`hhi_all`/`hhi_high`, `program_dollars_all_fact_id`) that this branch's `data.ts`,
`ProgramConcentration` and `WhoGetsItBody` do not read; the DuckDB mart
`fct_program_concentration` no longer has the columns this checkout's exporter selects.
Kimi's build crashed on `/program/18/` (`hhi.hhi.toFixed`) and it added a one-line shape
guard (`typeof hhi.hhi !== "number"` → render nothing) — honest (nothing invented, the
section is absent), but the concentration section and the award-tier "Who gets it" are
now dark on every program page until that session's `data.ts` lands on this branch. Not
this loop's defect; not fixable from here without merging their in-flight work. Flagged.

### First full registry on the 8a state — 27 gates, 12 fail, in three piles

| Pile | Gates | What |
|---|---|---|
| **Expected — closed by 8b/8c** | 16 answerfold (family fold), 21 leg (o), 23 e1 (`/families/f-15/` must say "P-1/R-1 TOA" — the ledger caption), 27 copy | The gates written for the passes that have not run yet. Each fails exactly as designed. |
| **The type system's own consequences — mine, fixed** | 1 build, 3 render-live (spine), 6 a11y, 22 flowdown | (a) Four pages crossed their weight ceilings by 265–370 gzip — the uniform per-page cost of two font preloads (markup + RSC payload), the spec class names and attributes, and one inline arrow icon; re-baselined at the ~6% convention with the reason written in the ledger. (b) The spine leg measured **1.32 rendered characters per ch** in Source Sans 3 (87 cpl at my first guess of 66ch); `--measure` is 60ch, and the globals.css comment now records that the ratio is the font's. (c) One dark-mode contrast node: the dossier chip went grey on light blue because `.t-id`'s unlayered colour beat `text-blue-700` — the three specs moved into `@layer components`, where a deliberate utility wins. (d) `/flow/` labels overlapped by 1.1 px: the label box measures **14.73** viewBox units *in situ* on the shipped page, not the 14.00 an isolated Chromium page gave — `LABEL_H` is 15.0, labels re-placed, and the comment says: measure on the built page, never in isolation. Widths dominated comfortably (worst rendered/estimated 0.87). |
| **The shared lake — another session's in-flight work** | 8 feed leg l, 14 coverage leg cv, 24 datatruth leg e | (a) Feed cards link to program pages that no longer render a concentration figure (the `hhi_all/hhi_high` schema; see 8a). (b) A downloaded, unparsed DHA FY2026 volume the methodology coverage prose does not mention (their roadmap #14). (c) `site_meta.json`'s gate count was reset to 24 by their export a second time, and its dbt-assertion count (115) no longer matches the manifest they rebuilt (100). For (c) the site now derives both counts from *this checkout's* artifacts at build time (`getSiteMeta`), by the exporter's own rule — a shared lake cannot desync the page from the registry again. (a) and (b) wait for their branch. |

Gate 7 (lighthouse, now including `/families/f-15/` and `/programs/`) **passed** with the
webfonts — CLS on the LCP heading held by the generated metric overrides. Gate 26 passed.

Re-run of the six gates touched after the fixes (fresh production build): build ✓
(four ledgers re-baselined, company heaviest re-measured), render-live ✓ (spine clean at
60ch), a11y ✓, flowdown ✓, datatruth ✓, type ✓. The tree now fails only the gates written
for 8b/8c and the two the lake owns. **Waiting on a Moonshot refill for 8b.**

