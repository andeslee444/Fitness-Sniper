import "server-only";

/**
 * Coverage manifest — Phase 5C.
 *
 * Declarative table of what each surface covers and what it omits.
 * Counts come from the same data sidecars the pages use (loaded via data.ts
 * helpers). Numbers are interpolated at build time — never hardcoded in JSX.
 *
 * Used by <CoverageNote id> and by the G2 gate (coverage.mjs).
 *
 * Fix round: counts are grouped through lib/format formatCount ("1,741", not
 * "1741") — the same notation /programs/, /district/ and the corpus statement
 * use. coverage.mjs mirrors the grouping in its expected patterns; it still
 * recomputes every number from the sidecars and still requires an exact
 * string match, so the gate is unchanged in strength.
 */

import { formatCount } from "@/lib/format";
import type { FlowAbsence } from "@/lib/flow-owner";
import { getAwardFyRange } from "@/lib/fy-range";
// crosswalkValue is the registry's OWN accessor (lib/corpus): it throws
// through the registry's invariants rather than falling back to a literal, and
// it is the single read every page goes through, so a coverage note cannot
// silently state a count the rest of the site has moved past.
import { crosswalkValue } from "@/lib/corpus";
import {
  getDetailGradeCount,
  getProgramsCount,
  getPagesWithoutDetail,
  getProgramPagesCount,
  getDossierCount,
  getCompaniesCount,
  getCompaniesWithAwardsCount,
  getDistrictsCount,
  getFlowChartMeta,
} from "@/lib/data";

export const COVERAGE_IDS = [
  "follow-the-dollar",
  "dossiers",
  "company-awards",
  "districts",
  "state-ca",
  "fy2026-partial",
  "years-matrix",
  "service-books",
  "flow-bridge",
] as const;

export type CoverageId = (typeof COVERAGE_IDS)[number];

export interface Coverage {
  id: CoverageId;
  numerator: number | null;
  denominator: number | null;
  note: string; // full rendered sentence, numbers interpolated
  /**
   * Empty-state variant for surfaces that are ABSENT on a given page
   * (e.g. a program page with no flow sidecar / no dossier). Numbers are
   * interpolated here too so the G2 number check holds no matter which
   * variant a representative page renders. Null where an empty state
   * cannot occur (the surface always renders).
   */
  emptyNote: string | null;
  anchor: string; // /methodology/#coverage-<id>
  /**
   * Visible link label for <CoverageNote>. States WHAT is being explained
   * (e.g. "why coverage is partial? →") so users know what they're clicking
   * before they arrive at the methodology anchor. Consistent convention:
   * "why <topic>? →"
   */
  linkText: string;
}

/**
 * `absence` picks follow-the-dollar's empty-state reason (lib/flow-owner
 * flowAbsenceReason, derived per page from its own links); every other id
 * ignores it. The default is the reason that held on every page before
 * Task 26 split it — "no-high-link".
 */
export function getCoverage(
  id: CoverageId,
  absence: FlowAbsence = "no-high-link",
): Coverage {
  switch (id) {
    case "follow-the-dollar": {
      // ONE declaration of what "crosswalked" counts (lib/corpus
      // getCrosswalkCounts) — /flow/ publishes a different, equally true
      // ratio, and gate 24 leg (p) is what keeps the two from drifting into
      // an apparent contradiction again. The registry refuses to build unless
      // one program page draws each sidecar, so "N programs" is pages.
      const linkable = crosswalkValue("district-linkable");
      const num = formatCount(linkable);
      const den = formatCount(getProgramsCount());
      // Task 26: a page with high-confidence links whose awards record no
      // positive obligation at a place of performance has been crosswalked
      // at high confidence — 102 such pages on the run-4 export said it had
      // not. Each page now gets the reason that is true of it.
      // Integration 2026-09-25 (R-INT-7): "at a place" tripped gate 27 leg
      // 11 (the "one place / a place" pattern); "at any place" is the same
      // negated claim.
      const why =
        absence === "no-place-of-performance"
          ? "none of this program's high-confidence awards records a positive obligation at any place of performance"
          : "this program's awards haven't been crosswalked at high confidence";
      return {
        id,
        numerator: linkable,
        denominator: getProgramsCount(),
        note: `Follow-the-dollar covers ${num} of ${den} programs — only high-confidence budget→award links are shown.`,
        emptyNote: `No follow-the-dollar view — ${why} (flows cover ${num} of ${den} programs).`,
        anchor: "/methodology/#coverage-follow-the-dollar",
        linkText: "why coverage is partial? →",
      };
    }
    case "dossiers": {
      const num = formatCount(getDossierCount());
      const den = formatCount(getProgramsCount());
      return {
        id,
        numerator: getDossierCount(),
        denominator: getProgramsCount(),
        note: `Research dossiers exist for ${num} of ${den} programs — the ${num} largest fully J-book-detailed programs by FY2026 request.`,
        emptyNote: `No research dossier for this program — dossiers cover ${num} of ${den} programs, the largest fully J-book-detailed lines by FY2026 requested dollars.`,
        anchor: "/methodology/#coverage-dossiers",
        linkText: "why no dossier here? →",
      };
    }
    case "company-awards": {
      const num = getCompaniesWithAwardsCount();
      const den = getCompaniesCount();
      return {
        id,
        numerator: num,
        denominator: den,
        note: `Award linkage is shown for ${formatCount(num)} of ${formatCount(den)} profiled companies — only high-confidence USASpending matches are included.`,
        emptyNote: null,
        anchor: "/methodology/#coverage-company-awards",
        linkText: "why partial award coverage? →",
      };
    }
    case "districts": {
      const num = getDistrictsCount();
      const den = 435;
      return {
        id,
        numerator: num,
        denominator: den,
        note: `${formatCount(num)} of ${formatCount(den)} congressional districts have high-confidence linked defense dollars.`,
        emptyNote: null,
        anchor: "/methodology/#coverage-districts",
        linkText: "why not all districts? →",
      };
    }
    case "state-ca": {
      return {
        id,
        numerator: null,
        denominator: null,
        note: "California data covers FY2025 only — CA Open Fi$Cal updates on a lag; prior years not yet ingested.",
        emptyNote: null,
        anchor: "/methodology/#coverage-state-ca",
        linkText: "why FY2025 only? →",
      };
    }
    case "fy2026-partial": {
      // Fix-wave round 2 (B3): this ended "…and the fiscal year does not
      // close until September 30" — a claim about the calendar, false from
      // 2026-10-01 while this corpus stays a part-year one — on ~2,587 pages.
      // It now states where the corpus's data ends
      // (site_meta.award_fy_range.latest_action_date, via lib/fy-range, the
      // same source /district/ and the <FyRange> tooltip read), and drops the
      // clause rather than guess when the export carries no date.
      const through = getAwardFyRange()?.latestActionDate ?? null;
      return {
        id,
        numerator: null,
        denominator: null,
        note:
          "FY2026 award data is a partial year — USAspending reports awards on a rolling basis" +
          (through ? `, and this corpus runs through ${through}.` : "."),
        emptyNote: null,
        anchor: "/methodology/#coverage-fy2026-partial",
        linkText: "why partial FY2026 data? →",
      };
    }
    case "years-matrix": {
      const num = getProgramsCount();
      const den = getProgramPagesCount();
      return {
        id,
        numerator: num,
        denominator: den,
        // Phase 5E: the 5D "prior-edition backfill is on the roadmap" promise
        // is delivered — ten editions loaded, columns edition-honest. The
        // second sentence is the G2 gate's interpolated-number contract.
        // Backlog #35: this used to call all `num` rows "detail-grade", which
        // is two more than actually carry J-book detail — the same
        // overstatement the corpus statement was making. The matrix's row
        // count and the detail-grade tier are different quantities, so the
        // note now states both instead of conflating them.
        note:
          `Columns are edition-honest: actuals for FY N come from the PB(N+2) President's Budget book, and every column states its edition — ten editions (PB2017–PB2026) are loaded. ` +
          `The matrix covers the ${formatCount(num)} program elements in the FY2026 budget index, ${formatCount(getDetailGradeCount())} of which carry detail-grade R-2/P-40 data; all ${formatCount(den)} program pages are browsable.`,
        emptyNote: null,
        anchor: "/methodology/#coverage-editions",
        linkText: "why these editions? →",
      };
    }
    case "service-books": {
      // Backlog #35: the tier this note is ABOUT is the detail-grade one, so
      // it counts the sidecars that carry J-book detail rows — not the
      // /programs/ index, which also holds trajectory-only lines.
      const num = getDetailGradeCount();
      const den = getProgramPagesCount();
      // ROADMAP #28. This sentence used to call the whole remainder "the
      // small remainder [which] carries cited R-1/P-1 workbook figures for
      // lines that publish no matching R-2/P-40 narrative". Both halves
      // stopped being true when the decade tier shipped: the remainder is no
      // longer small, and 553 of it carries no FY2026 workbook figure at all
      // — those elements are not in the FY2026 books, so "publishes no
      // matching narrative" describes the wrong absence. Both counts derived
      // (getPagesWithoutDetail), so neither can rot into a literal.
      const remainder = getPagesWithoutDetail();
      return {
        id,
        numerator: num,
        denominator: den,
        note: `Detailed J-book justification is ingested for ${formatCount(num)} of ${formatCount(den)} program pages — the FY2026 Navy, Army, and Air Force / Space Force books are all in. ${formatCount(remainder.workbookOnly)} pages carry cited FY2026 R-1/P-1 workbook figures for lines that publish no matching R-2/P-40 narrative (classified, SBIR, or spectrum lines); another ${formatCount(remainder.decadeOnly)} are history pages whose program element the FY2026 workbooks do not list at all, cited to the President's Budget editions that do carry it.`,
        emptyNote: null,
        anchor: "/methodology/#coverage-service-books",
        linkText: "why summary figures only? →",
      };
    }
    case "flow-bridge": {
      // /flow/ bridge honesty (Phase 5H). Numbers come from the flow_chart
      // export; the G2 gate recomputes both counts AND the percentage from
      // the payload, and the G9 leg-e contract requires the rendered note to
      // state the not-yet-crosswalked gap.
      const b = getFlowChartMeta().bridge;
      // Same registry as follow-the-dollar above: the two ratios this module
      // publishes are DIFFERENT questions, and they now come from one place
      // that says so. pctNotCrosswalked stays on the meta — it is a share of
      // dollars, not a count of program elements.
      const bridged = crosswalkValue("bridged-request");
      const universe = crosswalkValue("link-universe");
      return {
        id,
        numerator: bridged,
        denominator: universe,
        note:
          `Budget→contractor links are drawn for ${formatCount(bridged)} of ${formatCount(universe)} crosswalked PEs — ` +
          `${b.pctNotCrosswalked}% of the FY2026 request is not yet crosswalked: an honest gap, not an absence of contractors.`,
        emptyNote: null,
        // Anchor id is "coverage-flowdown" (the section covers the whole
        // /flow/ surface, not just the bridge) — the G2 gate carries an
        // explicit override for this id.
        anchor: "/methodology/#coverage-flowdown",
        linkText: "why is so little bridged? →",
      };
    }
  }
}
