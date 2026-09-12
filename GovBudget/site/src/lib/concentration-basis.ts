/**
 * concentration-basis.ts — whether a program page PUBLISHES a contractor
 * concentration figure, and on which basis (ROADMAP #80; fix round 1,
 * 2026-09-11).
 *
 * The mart computes two bases (see ProgramHHI in lib/data.ts) and both ship:
 * in the downloadable warehouse, in citations.json, and in the description
 * on /methodology/. A PAGE publishes only one of them — the
 * high-confidence-only figures — and only where the mart's floor is cleared
 * (HIGH_ONLY_MIN_AWARDS distinct high-confidence awards across
 * HIGH_ONLY_MIN_FAMILIES contractor families holding positive dollars, with
 * positive linked dollars: 37 of 444 mart rows, measured 2026-09-11).
 *
 * Below that floor NOTHING is published — not the all-links figure in its
 * place. account+subagency is 8,833 of the 11,512 medium-confidence links,
 * and the 2026-09-04 adjudication measured that tier at 0 of 60 for program
 * attribution (ROADMAP #79): it establishes that a program exists inside an
 * account, not that this budget line paid a contractor. Substituting it
 * would widen the claim to fit a number, which is the move the owner
 * decision of 2026-08-07 ("publish the smaller true number") forbids. The
 * card states the absence instead.
 *
 * ONE basis per page: the Contractor Concentration card and the "Who gets
 * it" answer both call this, and the exporter's `_who_gets_it_fid`
 * (src/govbudget/export_site.py) mirrors the same predicate so the
 * named-primes / lobbying / honest-absence fallbacks fire exactly when the
 * award tier does not — change both together.
 *
 * Measure tokens carry the basis on purpose: gate 23 leg a2 groups every
 * [data-amount] on a page by (entity, fy, measure) and fails two distinct
 * values in one group. A high-only figure and an all-tier sibling are two
 * measures, not two bases of one measure — so if the all basis is ever
 * rendered again it arrives under "hhi"/"obligations" and cannot collide
 * with these.
 *
 * Client-safe: type-only import from lib/data (which is server-only).
 */
import type { ProgramHHI } from "@/lib/data";

export type ConcentrationBasis = "high";

/**
 * Floor for a high-only index — mirrors fct_program_concentration.sql.
 * HIGH_ONLY_MIN_FAMILIES counts families holding POSITIVE dollars
 * (`positive_family_count_high`), not merely linked ones: a family that
 * contributed nothing does not make an index a statement about a market.
 */
export const HIGH_ONLY_MIN_AWARDS = 3;
export const HIGH_ONLY_MIN_FAMILIES = 2;

export interface ConcentrationPublished {
  published: true;
  basis: ConcentrationBasis;
  hhi: number;
  hhi_fact_id: string | null;
  program_dollars: number;
  program_dollars_fact_id: string | null;
  top_family: string;
  family_count: number;
  award_count: number;
  hhiMeasure: "hhi-high";
  dollarsMeasure: "obligations-high";
}

/**
 * WHY nothing is published — ONE vocabulary, two reasons, two marker values
 * (ROADMAP #82 ruling). The site withholds a concentration figure for
 * exactly two reasons and they are not interchangeable:
 *
 *   "below-floor"  — the mart row exists and its high-confidence links do
 *                    not clear the floor (#80). CONCENTRATION_WITHHELD_REASON
 *                    states it. The Contractor Concentration card stamps it
 *                    as [data-concentration-withheld]; concentrationHeadline()
 *                    is the only producer.
 *   "shared-code"  — the mart row exists for a budget line MORE THAN ONE
 *                    program uses, and more than one of them carries linked
 *                    awards, so the figure is neither member's and the
 *                    exporter withholds the whole block from both (#70/#82).
 *                    sharedCodeWithheldReason() states it; the block never
 *                    reaches the page, so the answer strip's "none" tier is
 *                    the only surface that can say it, from the sidecar's
 *                    summary.concentration_withheld. The strip stamps it as
 *                    [data-who-withheld] and gate 21 leg n check 7 holds it
 *                    against the payload.
 */
export type ConcentrationWithheldReason = "below-floor" | "shared-code";

export interface ConcentrationWithheld {
  published: false;
  /**
   * Why nothing is published. The card stamps this as its marker value, and
   * "below-floor" is the only value this branch can carry: a shared-code
   * withholding removes the whole block upstream, so concentrationHeadline()
   * is never called for one.
   */
  withheld: Extract<ConcentrationWithheldReason, "below-floor">;
}

export type ConcentrationHeadline =
  | ConcentrationPublished
  | ConcentrationWithheld;

export function concentrationHeadline(h: ProgramHHI): ConcentrationHeadline {
  if (
    h.hhi_high !== null &&
    h.program_dollars_high !== null &&
    h.top_family_high !== null
  ) {
    return {
      published: true,
      basis: "high",
      hhi: h.hhi_high,
      hhi_fact_id: h.hhi_high_fact_id,
      program_dollars: h.program_dollars_high,
      program_dollars_fact_id: h.program_dollars_high_fact_id,
      top_family: h.top_family_high,
      family_count: h.family_count_high,
      award_count: h.award_count_high,
      hhiMeasure: "hhi-high",
      dollarsMeasure: "obligations-high",
    };
  }
  return { published: false, withheld: "below-floor" };
}

/**
 * The one-sentence reason a card, or an answer strip, gives for publishing
 * no concentration figure. Stated once so the two surfaces cannot drift,
 * and carrying no figure about this program — the counts that would say how
 * far below the floor it sits are not cited, so they are not printed.
 *
 * IT STATES THE RULE, NOT A FACT ABOUT THIS LINE (fix round 2, 2026-09-11,
 * ruling R5). The first draft said "Fewer than 3 high-confidence award
 * links … are published for this line", which is false on the 44 withheld
 * pages that publish 3 or more — a reader counting the high-badged rows in
 * the Related Awards table directly above reads a contradiction — and it
 * stated two of the floor's three clauses, so it named the wrong reason on
 * a line withheld for netting non-positive dollars (356010: −$2,328,281
 * across 17 high links). The rule below is true on every withheld page by
 * construction, because it is the mart's floor
 * (dbt/models/marts/fct_program_concentration.sql) and nothing else.
 */
export const CONCENTRATION_WITHHELD_REASON =
  `This line's high-confidence links do not clear the floor for a published ` +
  `concentration index — at least ${HIGH_ONLY_MIN_AWARDS} awards across ` +
  `${HIGH_ONLY_MIN_FAMILIES} contractor families holding positive ` +
  `obligations, with positive net linked dollars.`;

/**
 * What the "Who gets it" answer strip leads with when the index is withheld
 * (site/src/app/program/[peBli]/page.tsx, the data-who-tier="none" branch
 * that a program WITH a concentration block falls through to).
 *
 * The strip's own #80 first draft said "No contractor is named for this
 * line at high confidence", which is false on all 245 withheld-with-links
 * pages: they name high-confidence contractors, with a "high" confidence
 * badge, in their own Related Awards table further down the same page
 * (/program/2915/ names 14 contractor families across 18 high-confidence
 * links). What is absent is a PUBLISHED LEADER: top_family_high is withheld
 * with the index on EVERY below-floor row — the mart repeats the hhi_high
 * WHEN clause verbatim for it (dbt/models/marts/fct_program_concentration.sql,
 * the two CASE expressions at :156-167) — which also removes the alphabetical
 * tie-break pick a zero-positive-dollar program would otherwise name as a
 * leader. It is not only those programs: a row that fails one of the other
 * two clauses can hold a genuine positive-dollar leader and still publish
 * none (0603882C clears the award count with 4 high awards and $7.45B, and
 * is withheld on the one positive-dollar family — measured read-only,
 * #80 fix round 3, 2026-09-11). Say that, then the rule above.
 */
export const WHO_GETS_IT_WITHHELD_LEAD =
  `No single contractor is published as this line's leader.`;

/**
 * The "shared-code" reason, the second half of the withheld vocabulary above
 * (ROADMAP #82). Lives here, beside CONCENTRATION_WITHHELD_REASON, because
 * R5 ruled one home for what the site says about a withheld concentration
 * figure — the two false sentences #80 had to retract were both written
 * inline in the surface that rendered them.
 *
 * EVERY CLAUSE IS TRUE BY CONSTRUCTION on every page that renders it. The
 * exporter sets summary.concentration_withheld (src/govbudget/export_site.py,
 * _concentration_withheld) only when ALL of these hold:
 *   - fct_program_concentration has a row for this bare pe_bli;
 *   - dim_programs publishes more than one program under it (ident.is_split);
 *   - more than one of those members carries at least one published
 *     crosswalk link, which is why the mart's figure — computed on the bare
 *     line — is neither member's to claim and is withheld from both;
 *   - THIS member is one of the linked ones, so this page renders its own
 *     Related Awards table below.
 * Nothing here counts this line's links or names a number: no dollars, no
 * award count, no leader — gate 21 leg (j) allows a non-award tier none of
 * those, and #80 fix round 2 showed that a count is exactly what goes false.
 * "More than one", never "two": '30' is shared by THREE programs.
 */
export function sharedCodeWithheldReason(peBli: string): string {
  return (
    `Award records are linked to this program — see Related Awards below — ` +
    `but no concentration index is published for it: the crosswalk computes ` +
    `concentration on budget line ${peBli}, which more than one program ` +
    `uses, and more than one of them carries linked awards, so the figure ` +
    `would mix their money.`
  );
}
