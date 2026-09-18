import "server-only";

/**
 * coverage-map.ts — the /coverage/ manifest (PM Sprint 3 Task 6, §Coverage).
 *
 * "The honesty is right, the roadmap is missing." Every coverage gap on this
 * site is disclosed at the point of use — and a visitor still cannot tell
 * "early, moving fast" from "abandoned at 1%". This module is the answer:
 * for each surface, what it covers TODAY, the SPECIFIC thing standing in the
 * way, and a DATED target (or an honest statement of why there is no date).
 *
 * THE ONE RULE. Every number here is read from a shipped artifact — §P1-5,
 * and on this page of all pages it is not negotiable. A hardcoded count on the
 * page that publishes the site's coverage would be self-refuting the first
 * time the corpus moved. So: `covered` strings are assembled from the data.ts
 * / feeds.ts loaders, `numerator` and `denominator` carry the same values as
 * machine-readable attributes, and gate 14's coverage-map leg recomputes all
 * of them from the sidecars and the built HTML.
 *
 * Numbers that cannot be derived at export time are OMITTED rather than
 * authored — the precedent /methodology/ §3 already set for the pytest and
 * vitest totals. One is omitted here for the same reason and named in the
 * page's own "what is not on this page" note: the share of award dollars whose
 * recipient resolves to a corporate family (the entity crosswalk's own
 * coverage). It is a warehouse query, not a sidecar, so the page does not
 * state it rather than shipping a literal that would rot.
 *
 * BLOCKERS AND TARGETS ARE PROSE, and prose is authored — that is the point of
 * them. What the gate enforces is that they EXIST, that a dated target names a
 * month and a year, and that an undated one says so in as many words.
 *
 * TARGET POLICY (Sprint 3 round 3 — the site owner's decision). The first cut
 * of this page shipped eight dated targets that nobody outside the build had
 * committed to. The owner reviewed them and decided the page ships with the
 * targets UNDATED: publishing a date the project has not agreed to is the same
 * class of defect as publishing a figure it cannot recompute, and this is the
 * page least able to afford either. So every row now states that there is no
 * dated target AND names the work that is planned and what would move it —
 * "planned and not scheduled", never "undated because nobody knows".
 * (2026-09-18: "undated pending a roadmap decision" is retired — it promised a
 * decision on work that was filed nowhere and, for lineage, on a pass that had
 * already run. See COVERAGE_PROMISE_IDS below.)
 * The BLOCKERS are untouched: they are the page's value, and none was dropped.
 * A dated target remains legal in this vocabulary (targetKind "dated"); adding
 * one back is a deliberate act that has to name a month and a year.
 */

import {
  getCompaniesCount,
  getCompaniesWithAwardsCount,
  getDecadeEditions,
  getDetailGradeCount,
  getDistrictsCount,
  getDossierCount,
  getFilingsCount,
  getFlowChartMeta,
  getLineagePrograms,
  getPagesWithoutDetail,
  getProgramPagesCount,
  getProgramsCount,
  getSiteMeta,
} from "@/lib/data";
import { getCrosswalkCounts } from "@/lib/corpus";
import { getFeedInventory } from "@/lib/feeds";
import { formatCount } from "@/lib/format";

/** Rows, in the order the page renders them. */
export const COVERAGE_MAP_IDS = [
  "program-pages",
  "editions",
  "dossiers",
  "lineage",
  "flows",
  "bridge",
  "company-awards",
  "awards-window",
  "districts",
  "state-ca",
  "feeds",
  "filings",
] as const;

export type CoverageMapId = (typeof COVERAGE_MAP_IDS)[number];

/**
 * The row whose blocker IS the methodology limit — the crosswalk gap. Named
 * so the page, the tests and the gate all point at the same row rather than
 * three copies of the string "bridge".
 */
export const CROSSWALK_LIMIT_ID: CoverageMapId = "bridge";

/**
 * The rows whose target names work this project intends to do — as opposed to
 * a methodology limit (bridge, flows, company-awards) or a source limit
 * (program-pages, awards-window).
 *
 * 2026-09-18. All seven used to end "pending a roadmap decision". Nothing was
 * pending: the 2026-09-05 audit found no numbered entry, spec or commit behind
 * any of them, and the lineage row described a pass that had already run and
 * closed (#29(a), 2026-08-26). "Pending a decision" promises a decision is
 * coming; "not scheduled" is what was true.
 *
 * The ROADMAP number is deliberately NOT rendered: ROADMAP.md is not a
 * published document, and a reference the reader cannot open is the same
 * defect one layer down. For a maintainer looking for the paperwork, the
 * 2026-09-05 audit routes four of these to numbered backlog entries — grep
 * ROADMAP.md for the SUBJECT PHRASE, never a number: "PB2015 and PB2016
 * editions" (editions), "Dossier expansion beyond the top 50" (dossiers),
 * "Lineage title-only endpoints" (lineage), "GAO protest-docket enrichment"
 * (feeds). districts, state-ca and filings are routed to no entry at all,
 * which is exactly what their rows say.
 */
export const COVERAGE_PROMISE_IDS: readonly CoverageMapId[] = [
  "editions",
  "dossiers",
  "lineage",
  "districts",
  "state-ca",
  "feeds",
  "filings",
];

/**
 * The File C negative result, published. Spike:
 * docs/superpowers/reviews/filec-program-activity-spike.md (2026-09-01),
 * whose §Implications asks this page to say File C was "examined and ruled
 * out rather than staying silent on it".
 *
 * File C ("Account Breakdown by Award") nominally carries a program activity
 * per (TAS × award) — the one official path that could have closed the
 * budget→award gap. The spike tested it and it cannot. Every clause below is
 * the spike's own measurement, in its own scope:
 *
 *   - finding #1: OMB's authoritative program-activity domain for the DoD
 *     RDT&E accounts it checked (097-0400, 057-3600, at FY25P12) "contains
 *     only budget-activity lines … plus junk codes", and "Program elements
 *     are not in the valid domain", so "PE-level File C reporting is
 *     impossible by construction". Hence "budget activities and junk codes,
 *     never program elements" — the junk half is not dropped. Fix round 1
 *     (review Important #1, 2026-09-18): the rendered link label now names
 *     those two accounts explicitly. The page's own crosswalk universe is
 *     wider — it includes procurement books — and the linked file is OMB's
 *     whole-government domain list, so the old "for these accounts" had no
 *     antecedent that actually bounded the claim to what was checked.
 *   - finding #2, measured over the sample and NOT over the corpus: "81% of
 *     absolute obligated flow ($501M of $617M) sits under junk or absent
 *     labels", where the sample is a "Stratified sample of 44 published links
 *     (19 high / 25 medium; 41 distinct awards)" and its 1,090 File C rows.
 *     The rendered sentence keeps "absolute" and gives the sample its own
 *     antecedent — "this site's own published crosswalk links (19 high / 25
 *     medium)" — so "44-link sample" is never read as "the corpus". It states
 *     no dollar figure (none is derivable here).
 *   - findings #3/#4 and §Implications: the field "contradicts ground truth
 *     on awards we can independently verify", and cannot serve "as a join
 *     key, … as corroborating evidence, [or] as a veto on suspect links".
 *
 * The spike itself has no published home (no route renders docs/, and the
 * repository is not public), so the link is its public primary evidence: OMB's
 * domain list. That file is 63,635,154 bytes (HTTP 200, text/csv, re-checked
 * 2026-09-18) and the link text says "64 MB CSV" — a link that silently
 * starts a 64 MB download is a hostile citation.
 */
export const FILE_C_NOTE = {
  lead:
    "A published negative result, not a silence: File C nominally names a " +
    "program activity for each award, but ",
  linkHref: "https://files.usaspending.gov/reference_data/program_activity.csv",
  linkLabel:
    "OMB’s own domain list for the DoD RDT&E accounts checked, 097-0400 " +
    "and 057-3600 (a 64 MB CSV)",
  tail:
    " carries only budget activities and junk codes, never program elements, " +
    "so program-element grain is impossible by construction. In a 44-link " +
    "sample of this site's own published crosswalk links (19 high / 25 " +
    "medium), 81% of absolute obligated flow sat under junk or absent " +
    "labels, and it contradicts ground truth on awards verified " +
    "independently. It cannot join, corroborate, or veto.",
} as const;

/** "dated" → target names a month and a year. "none" → and says why not. */
export type CoverageTargetKind = "dated" | "none";

export interface CoverageMapRow {
  id: CoverageMapId;
  /** What the row is about, in the reader's words. */
  label: string;
  /** The surface this row describes. */
  href: string;
  /** Machine-readable ratio, or null where the row is not a ratio. */
  numerator: number | null;
  denominator: number | null;
  /** The rendered coverage sentence — every figure interpolated. */
  covered: string;
  /** Which shipped artifact those figures were read from. */
  derivation: string;
  /** The specific thing in the way. Never "not done yet". */
  blocker: string;
  targetKind: CoverageTargetKind;
  /** A dated target, or the reason there is not one. */
  target: string;
}

/**
 * The date this map's PROSE was last reviewed — rendered so a stale page is
 * visible. (Was TARGETS_SET_ON; the targets are undated now, but the review
 * date is exactly the thing a reader needs to judge whether the map is
 * current.)
 *
 * Every FIGURE on the page is recomputed at build time and cannot go stale.
 * The prose — blockers, targets, the reasons a row has no date — is written
 * by hand and can. Those are different guarantees and the page now says so,
 * because on 2026-08-27 this constant read 2026-08-05 while the detail-grade
 * row's blocker was being rewritten: the date understated one row and
 * overstated the other eleven at the same time.
 *
 * 2026-09-18 (fix round 1) re-read: the seven COVERAGE_PROMISE_IDS target
 * sentences against ROADMAP.md; the bridge row's blocker and its FILE_C_NOTE
 * against the spike; and the awards-window and company-awards targets, the
 * two rows trimmed to fund that round's additions under R-22a-1's net-zero
 * budget. It did not re-read every row on the page — a row outside that list
 * can still be stale under this date.
 */
export const MAP_REVIEWED_ON = "2026-09-18";

export function getCoverageMap(): CoverageMapRow[] {
  const programs = getProgramsCount();
  const pages = getProgramPagesCount();
  // Backlog #35: the detail-grade tier is the sidecars that carry J-book
  // detail rows (= dim_programs), NOT programs.json's length — the index also
  // lists trajectory-only lines. This page LEADS with this number, so it is
  // the worst possible place for the site to be two generous about itself.
  const detailGrade = getDetailGradeCount();
  // ROADMAP #28: the non-detail remainder is TWO claims now, not one. A page
  // with FY2026 workbook rows and no R-2/P-40 detail is a different statement
  // from a page whose element the FY2026 workbooks do not list at all, and
  // `pages − detailGrade` — which used to be exactly the first — would have
  // made the sentence below false for 553 pages the day the decade tier
  // shipped. Both halves are derived from the sidecars' own content, and the
  // three-way reconciliation is asserted so a page that fits NEITHER sentence
  // fails the build instead of being quietly absorbed into one of them.
  const remainder = getPagesWithoutDetail();
  const rollups = remainder.workbookOnly;
  const decadeOnly = remainder.decadeOnly;
  if (remainder.unclassified.length > 0) {
    throw new Error(
      `[govbudget/coverage-map] ${remainder.unclassified.length} program page(s) ` +
        `carry neither R-2/P-40 detail, nor FY2026 workbook rows, nor the ` +
        `decade tier's marker: ${remainder.unclassified.slice(0, 5).join(", ")}. ` +
        `Neither sentence below describes them, and this row would under-report ` +
        `the corpus rather than say so.`,
    );
  }
  if (rollups + decadeOnly !== pages - detailGrade) {
    throw new Error(
      `[govbudget/coverage-map] ${pages} pages − ${detailGrade} detail-grade ` +
        `leaves ${pages - detailGrade}, but the sidecars partition into ` +
        `${rollups} workbook-only + ${decadeOnly} decade-only. The two counts ` +
        `must exhaust the remainder or this row describes fewer pages than exist.`,
    );
  }
  const editions = getDecadeEditions();
  const budgetFy = getFlowChartMeta().budgetFy;
  // ONE declaration of what "crosswalked" counts — lib/corpus
  // getCrosswalkCounts, which reads flow_chart.json's own bridge band and the
  // shipped sidecar directory. The `flows` and `bridge` rows below state two
  // DIFFERENT ratios out of the same registry, and /coverage/#crosswalk
  // renders the list that says how they differ. Gate 24 leg (p) binds all of
  // it. `pctNotCrosswalked` still comes off the meta: it is a share of
  // dollars, not a count of program elements.
  const crosswalk = getCrosswalkCounts();
  const crosswalkValue = (id: string) =>
    crosswalk.find((c) => c.id === id)!.value;
  const pctNotCrosswalked = getFlowChartMeta().bridge.pctNotCrosswalked;
  const linkable = crosswalkValue("district-linkable");
  const bridged = crosswalkValue("bridged-request");
  const universe = crosswalkValue("link-universe");
  const highConfidence = crosswalkValue("high-confidence-links");
  const awardWindow = getSiteMeta().award_fy_range;
  const feeds = getFeedInventory();

  const rows: CoverageMapRow[] = [
    {
      id: "program-pages",
      label: "Program pages",
      href: "/programs/",
      numerator: detailGrade,
      denominator: pages,
      // #106: gate 14 leg cm parses this sentence back (coverage.mjs
      // PROGRAM_PAGES_SPLIT_RE: "A of B program pages carry detail-grade …;
      // C carry cited FYxxxx R-1/P-1 workbook figures only, and D are
      // history pages") and asserts A + C + D = B as rendered. Reword the
      // two together.
      covered:
        `${formatCount(detailGrade)} of ${formatCount(pages)} program pages carry ` +
        `detail-grade J-book justification; ${formatCount(rollups)} carry cited ` +
        `FY2026 R-1/P-1 workbook figures only, and ${formatCount(decadeOnly)} are ` +
        `history pages for elements the FY2026 workbooks do not list at all.`,
      derivation:
        "program_details sidecars holding at least one J-book detail row, over every sidecar this build shipped; the two remainders are the sidecars' own tier field.",
      // CORRECTED TWICE, and the second correction is the one that matters.
      //
      // 2026-08-27: the text said the missing justification "does not exist
      // publicly" and that this was "a limit of what the Department
      // publishes, not of what we have loaded". Both false — 25 FY2026
      // volumes were downloaded here and unparsed, including SCN_Book.pdf,
      // the Navy shipbuilding volume carrying Virginia, COLUMBIA and DDG-51.
      // That correction replaced the denial with a backlog confession.
      //
      // 2026-08-29 (Wave 5): the backlog is gone, so the confession is now
      // the false sentence. Every FY2026 justification volume in this repo
      // is parsed — 81 of 81 files, 20 of which are duplicate covers of a
      // book already loaded (the services print one master XML under several
      // budget-activity covers; verified byte-identical, and verified to
      // carry no fact identity their parsed twin lacks). Virginia, COLUMBIA
      // and DDG-51 have R-2/P-40 detail on this build. The excluded list
      // fell from 192 lines and $156.5B to 29 lines and $85.2B, of which
      // $73.9B is Classified Programs.
      //
      // What remains genuinely is not published: the classified aggregate,
      // and a short tail of lines whose money is real but whose
      // justification is filed elsewhere or not at all.
      //
      // Deliberately no hard-coded dollar or volume counts below: this file
      // has no derived source for them, and a stale literal here would be
      // the same defect one layer down. Gate 14 leg (cv) recomputes the
      // disk↔lake reconciliation and fails the build if this row's claim
      // points the other way — in EITHER direction, which is exactly what
      // forced this second correction: with the volumes parsed, leg cv fails
      // on any sentence still claiming an unparsed backlog.
      // ROADMAP #28 split this sentence in two. It used to describe the
      // whole non-detail remainder as "rollup lines carrying cited R-1/P-1
      // workbook figures without R-2/P-40 detail" — false, from the day the
      // decade tier shipped, for every page whose element has no FY2026
      // workbook line at all. The reason those pages carry no justification
      // is not that the volume is missing; it is that the FY2026 books do
      // not list the element.
      blocker:
        `${formatCount(rollups)} of the remaining pages are rollup lines carrying ` +
        "cited FY2026 R-1/P-1 workbook figures without R-2/P-40 detail. Classified " +
        "Programs — much the largest single line, and most of the money — " +
        "genuinely publish no justification, and no ingestion run will ever " +
        "change that. The rest is a short tail of lines whose money is real " +
        "and whose justification is not filed as an R-2 or P-40 exhibit of " +
        `its own. The other ${formatCount(decadeOnly)} are history pages: the ` +
        "FY2026 books carry no line for those elements, so there is no FY2026 " +
        "justification for them to be missing, and what those pages publish is " +
        "the cited record from the President's Budget editions that do carry " +
        "them. No FY2026 " +
        "justification volume this project holds is still waiting to be read: " +
        "the Navy procurement books, Virginia and COLUMBIA class submarines " +
        "and DDG-51 among them, were the last of them and are loaded.",
      targetKind: "none",
      target:
        "No dated target, because there is no longer an ingestion step to " +
        "date. What is left is source material the Department does not " +
        "publish in this form, which is a different thing from work this " +
        "project has not done — and the distinction is checked on every " +
        "build against the files actually on disk, in both directions.",
    },
    {
      id: "editions",
      label: "President's Budget editions",
      href: "/years/",
      numerator: editions.length,
      denominator: null,
      covered:
        `${formatCount(editions.length)} editions loaded — ` +
        `PB${editions[0]}–PB${editions[editions.length - 1]}. Actuals for ` +
        "fiscal year N are read from the PB(N+2) book, and every column on the " +
        "decade matrix states its edition.",
      derivation:
        "distinct edition stamps on years_matrix.json's decade columns — the same columns /years/ renders.",
      blocker:
        "Each earlier edition is manual work rather than a rerun: the older " +
        "books publish consolidated volumes under unstable file naming, so " +
        "every edition needs its own evidence-keyed volume classification " +
        "before its lines can be trusted next to the modern ones. Two editions " +
        "were nearly published with the wrong volumes before that rule existed.",
      targetKind: "none",
      target:
        // "queued" was the word that had to go with the date: nothing queues
        // these two anywhere (#96 — the only commit that has ever touched the
        // string PB2015 is the one that published this page).
        "No dated target, and not scheduled — PB2015 and PB2016 are the two " +
        "editions that would come next. An edition ships only once its " +
        "volumes are evidence-keyed — never on a filename pattern — so a date " +
        "could only follow that work.",
    },
    {
      id: "dossiers",
      label: "Research dossiers",
      href: "/programs/",
      numerator: getDossierCount(),
      denominator: programs,
      covered: `${formatCount(getDossierCount())} of ${formatCount(programs)} programs have a research dossier.`,
      derivation: "dossier sidecars over programs.json rows.",
      blocker:
        "Dossiers are generated in metered batches under a per-run cost cap, " +
        "and every claim in one must resolve to a citation before it is " +
        "first published — a freshly generated dossier with even one " +
        "unresolvable citation is rejected outright, not published with a " +
        "caveat. If an upstream data correction later invalidates a citation " +
        "in an already-published dossier, that individual claim is dropped " +
        "and the removal is disclosed on the page (#52) rather than pulling " +
        "the whole dossier. Throughput is bounded by that budget and that " +
        "gate, not by the availability of source material.",
      targetKind: "none",
      target:
        // The old sentence said the next batches were "queued". They are not
        // queued anywhere (#95); the ORDER is the only thing that exists, and
        // it exists in code — dossiers/research.py sorts the candidate rows by
        // fct_budget_trajectory.fy2026_total descending before the cap.
        "No dated target, and not scheduled — the order is fixed even though " +
        "the schedule is not: whenever a next batch runs it is taken in order " +
        "of FY2026 requested dollars, largest lines first.",
    },
    {
      id: "lineage",
      label: "Program lineage",
      href: "/programs/",
      numerator: getLineagePrograms(),
      denominator: programs,
      covered:
        `${formatCount(getLineagePrograms())} of ${formatCount(programs)} programs ` +
        "carry a lineage rail — where the money went when a program element was " +
        "renumbered, realigned or transferred.",
      derivation:
        "program_details sidecars carrying a non-empty lineage rail, over programs.json rows.",
      // Tri-persona review Wave 4, item 5. This used to say an edge is
      // asserted "only where a justification narrative names BOTH endpoints
      // in a sentence we can quote back". Measured against
      // data/parquet/jbooks/program_lineage.parquet: of 49 stated edges, 16
      // quote a sentence naming both ends and 33 (67%) quote a sentence
      // naming ONE — the other end being the program element whose own
      // narrative the sentence came from. The edges are sound and the
      // extractor's rules are deliberate (lineage/extract.py: a both-named
      // clause pairs the two NAMED PEs; a single-direction clause pairs the
      // named PE with `this`). The RULE AS WRITTEN was simply not the rule
      // enforced, and it is the rule a reader uses to judge the tier.
      blocker:
        "An edge is asserted only where a justification narrative names the " +
        "other end explicitly, next to a transfer verb: “realigned to PE " +
        "0604818A” is usable, “realigned to another program element” is not, " +
        "and most renumberings are written the second way. Usually the " +
        "sentence names one end and the book it appears in supplies the " +
        "other; where one names both, those two are paired instead. " +
        "Candidate edges found by maturation patterns are shown dashed and " +
        "are never cited.",
      targetKind: "none",
      target:
        // STALE as well as over-promising. The extraction pass over clauses
        // already carrying a PE token ran and closed as #29(a) (2026-08-26,
        // 313 clauses). What is left is the ~4,400 verb-only clauses that
        // §6.2 of specs/2026-08-31-lineage-llm-extraction-precision.md:194-201
        // declares need "a separate matcher with a separate precision
        // measurement" — its dominant error being a SYSTEM name confidently
        // resolved to a BUDGET LINE.
        //
        // Fix round 1 (Minor #3, 2026-09-18): "Anything it found" pointed
        // past "a different matcher" to "an effort" two nouns back. Named
        // the matcher explicitly instead.
        "No dated target, and not scheduled — the pass over clauses that " +
        "already name a program element has run; what is left are clauses " +
        "naming only a system or an effort, which need a different matcher " +
        "and their own precision study. Anything such a matcher found would " +
        "stay in the candidate tier until a quotable sentence names the " +
        "other end.",
    },
    {
      id: "flows",
      label: "Follow-the-dollar",
      href: "/flow/",
      numerator: linkable,
      denominator: programs,
      covered: `${formatCount(linkable)} of ${formatCount(programs)} programs have a follow-the-dollar view.`,
      derivation: "flow sidecars over programs.json rows.",
      // Trimmed 2026-09-12 to pay for the crosswalk-count list this page now
      // publishes (#crosswalk): that list states what one unit of this count
      // is, so the blocker no longer has to. Ceilings unchanged.
      blocker:
        "The budget→award crosswalk, one row below: a program earns this " +
        "view only where its awards tie to it by more than an account code, " +
        "and almost none do.",
      targetKind: "none",
      target:
        "No dated target — this number moves when the crosswalk moves, which " +
        "is a methodology limit rather than a queue.",
    },
    {
      id: "bridge",
      label: "Budget→award crosswalk",
      href: "/flow/#bridge",
      numerator: bridged,
      denominator: universe,
      covered:
        `${formatCount(bridged)} of ` +
        `${formatCount(universe)} crosswalked program elements ` +
        `carry FY${budgetFy} request dollars ` +
        `(${formatCount(highConfidence)} at high confidence) — ` +
        `${pctNotCrosswalked}% of the FY${budgetFy} request is not bridged to an award.`,
      derivation:
        "the bridge band of flow_chart.json: crosswalked and universe PE counts, and the unbridged share of the request.",
      blocker:
        "Account codes are too coarse to attribute awards to program elements. " +
        "An award record carries a Treasury account and an appropriation; one " +
        "appropriation account funds dozens to hundreds of program elements, " +
        // ROADMAP #109 (2026-09-11): this said "Every published link was
        // hand-adjudicated". Measured against award_pe_adjudications, 9,587 of
        // the 12,595 links the crosswalk grades high or medium carry an
        // adjudication row at all and three published evidence paths carry
        // none — the same universal /methodology/ opened its crosswalk section
        // with, in a second place. The count is NOT restated here: /coverage/
        // has no derived figure for it, and a typed one is what this branch
        // keeps removing. "Most" is true of both the crosswalk table (76%) and
        // the mart a reader meets (76%).
        //
        // Fix round 1 (R-6c-4): the tier sentence said "high means … verified
        // by two independent adversarial reviewers", and coverage.mjs's leg
        // cm[bridge] MANDATED the word. Measured over the mart the same day,
        // 768 links publish at high and 60 of them carry a per-award
        // adjudication — the adversarial step is real, and it covers 60 of
        // 768, not the tier. The claim is now bounded to the links that
        // carry one; the gate mandates the bounded wording instead.
        "and nothing else on the record narrows it. Most published links were " +
        "hand-adjudicated (September 2026) — /methodology/ states how many, " +
        "and which evidence paths carry no per-link adjudication at all: high " +
        "means the contract and the program's own J-book pages name the same " +
        "program, and where a per-award adjudication exists it was challenged " +
        "by two independent adversarial reviewers; medium " +
        "means only that the award drew on the same account and agency. " +
        "Where evidence pinned an award " +
        "to a different organization's program, the link was removed — a " +
        // The File C negative result (spike 2026-09-01), stated where the
        // limit is stated. Short on purpose: this blocker renders TWICE (the
        // map row and /coverage/#crosswalk), so every character here costs
        // two, and the paragraph the page puts directly under it — FILE_C_NOTE
        // — carries the measurement and the public evidence link.
        "guess wearing a citation is worse than an honest absence. File C, " +
        "the last untested official path, was examined and ruled out in " +
        "September 2026.",
      targetKind: "none",
      target:
        // Trimmed 2026-09-18 to pay for the File C sentences on this page.
        // What went was "Until then the unbridged share is stated outright, so
        // nobody has to reverse-engineer it from what the chart omits" — a
        // claim this page makes twice over already: the row's own `covered`
        // cell states the unbridged share as a percentage, and the paragraph
        // immediately above this one in /coverage/#crosswalk says the site
        // "publish[es] the size of the remainder rather than leaving it to be
        // inferred from an empty chart". This target renders TWICE, so the
        // duplicate cost double. No claim was dropped, only restated once.
        "No dated target, because this is a methodology limit and not a backlog " +
        "item. It closes if a source begins publishing the program element on " +
        "the award record.",
    },
    {
      id: "company-awards",
      label: "Company award linkage",
      href: "/companies/",
      numerator: getCompaniesWithAwardsCount(),
      denominator: getCompaniesCount(),
      covered:
        `${formatCount(getCompaniesWithAwardsCount())} of ` +
        `${formatCount(getCompaniesCount())} profiled companies show at least ` +
        "one award linked to a named budget line.",
      derivation:
        "entity_details sidecars carrying a non-empty awards array, over entities_top.json rows.",
      blocker:
        "The same crosswalk limit, seen from the company side. Each profiled " +
        "company's obligations total is complete over the award window; what is " +
        "partial is the link from those obligations to a named budget line.",
      targetKind: "none",
      target:
        // Fix round 1 (funds Important #1 and Minors #2/#3 under R-22a-1):
        // "rather than per program element" restated the bridge row's own
        // framing, one row up on this same page. Kept "counted per company"
        // — that half is not said anywhere else.
        "No dated target — this is the crosswalk limit above, counted per " +
        "company.",
    },
    {
      id: "awards-window",
      label: "Award obligations window",
      href: "/companies/",
      numerator: null,
      denominator: null,
      covered:
        `${awardWindow?.label ?? "not stated"} contract and assistance ` +
        `obligations${awardWindow?.latest_action_date ? `, through ${awardWindow.latest_action_date}` : ""}` +
        `${awardWindow?.max_partial ? `. FY${awardWindow.fy_max} is a partial year` : ""}.`,
      derivation:
        "site_meta.award_fy_range, computed from the award transaction lake at export time.",
      blocker:
        "The newest fiscal year is always incomplete: USAspending publishes on " +
        "a rolling basis and the federal year does not close until 30 " +
        "September. Years before the window's start sit outside the transaction " +
        "archive we ingest.",
      targetKind: "none",
      target:
        // Fix round 1 (funds Important #1 and Minors #2/#3 under R-22a-1): "The
        // newest fiscal year stops moving once the federal year has closed
        // and USAspending has finished publishing against it" restated the
        // blocker immediately above, in the same words — "the newest fiscal
        // year is always incomplete: USAspending publishes on a rolling
        // basis and the federal year does not close until 30 September."
        "No dated target, and none would mean anything here: this window is " +
        "refreshed on every ingestion run rather than on a schedule.",
    },
    {
      id: "districts",
      label: "Congressional districts",
      href: "/district/",
      numerator: getDistrictsCount(),
      denominator: 435,
      covered: `${formatCount(getDistrictsCount())} of ${formatCount(435)} congressional districts have linked defense dollars.`,
      derivation: "districts/index.json rows over the 435 seats of the House.",
      blocker:
        "A district appears only where an award's place of performance resolves " +
        "to a numbered district. A large share of defense obligations is " +
        "recorded against statewide or undistricted codes (00, 90, 98, 99), and " +
        "those cannot be split across a state's seats without inventing a " +
        "distribution nobody could check.",
      targetKind: "none",
      target:
        "No dated target, and not scheduled — the planned fix is scoped: " +
        "publish the statewide residual as its own row per state, so the " +
        "dollars that cannot be districted are visible instead of missing.",
    },
    {
      id: "state-ca",
      label: "State spending",
      href: "/data/",
      numerator: null,
      denominator: null,
      covered: "California only, FY2025 only.",
      derivation:
        "the scope of the fct_state_per_capita dataset shipped on /data/.",
      blocker:
        "CA Open Fi$Cal publishes on a lag and restates prior years in place, " +
        "so each earlier year needs its own reconciliation against the restated " +
        "totals before it can sit beside a federal figure. Every other state is " +
        "a separate portal with its own schema — there is no shared source.",
      targetKind: "none",
      target:
        // Filed nowhere: the backlog's California entry (#93) is the 376-page
        // ACFR table parse, a different document species from the Open Fi$Cal
        // FY2023/FY2024 ingest this row is about.
        "No dated target, and not scheduled — California FY2023 and FY2024 " +
        "are the planned next step. No second state is queued behind them, " +
        "and none will be announced before its portal is ingested.",
    },
    {
      id: "feeds",
      label: "Syndication feeds",
      href: "/feed/",
      numerator: feeds.programFeeds + feeds.companyFeeds,
      denominator: null,
      covered:
        `${formatCount(feeds.items)} items across ` +
        `${formatCount(feeds.eventTypes)} event types, plus ` +
        `${formatCount(feeds.programFeeds)} program and ` +
        `${formatCount(feeds.companyFeeds)} company watch feeds.`,
      derivation:
        "feed.json's cards, and the RSS files under public/feeds/ that this build wrote.",
      blocker:
        "A watch feed is written only where the program or company actually has " +
        "events; the rest would be permanently empty subscriptions advertised " +
        "as live ones. So feed coverage is event coverage, and a new event type " +
        "cannot ship until its threshold is published and gated.",
      targetKind: "none",
      target:
        "No dated target, and not scheduled — two further event types are " +
        "planned, protest outcomes and GAO high-risk transitions, each with " +
        "its threshold published before its first card.",
    },
    {
      id: "filings",
      label: "Lobbying filings",
      href: "/filings/",
      numerator: getFilingsCount(),
      denominator: null,
      covered: `${formatCount(getFilingsCount())} Senate LDA filings indexed, with program mentions extracted.`,
      derivation: "filings_index.json's total.",
      blocker:
        "Filings are matched to programs by name and alias, and LDA activity " +
        "descriptions usually name a platform or a service rather than a budget " +
        "line. A mention is published only where a tracked alias matches; a " +
        "description naming only “the Navy” produces none, which is " +
        "the honest result rather than a miss.",
      targetKind: "none",
      target:
        // Filed nowhere: the backlog's alias entry (#100) is the defence.gov
        // announcement corpus, not this LDA alias table.
        "No dated target, and not scheduled — extending alias coverage across " +
        "the whole detail-grade corpus is planned, with each new alias " +
        "recorded in the alias table rather than inferred at match time.",
    },
  ];

  return rows;
}
