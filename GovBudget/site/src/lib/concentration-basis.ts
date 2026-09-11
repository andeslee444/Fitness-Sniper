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

export interface ConcentrationWithheld {
  published: false;
  /** Why nothing is published. The card stamps this as its marker value. */
  withheld: "below-floor";
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
 */
export const CONCENTRATION_WITHHELD_REASON =
  `Fewer than ${HIGH_ONLY_MIN_AWARDS} high-confidence award links across ` +
  `${HIGH_ONLY_MIN_FAMILIES} contractor families with positive obligations ` +
  `are published for this line, so no concentration index is published for ` +
  `it either.`;
