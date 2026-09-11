/**
 * concentration-basis.ts — which link basis a program page HEADLINES for
 * its contractor-concentration figures (ROADMAP #80, 2026-09-05).
 *
 * The mart publishes two bases (see ProgramHHI in lib/data.ts). "Publish
 * the smaller true number": the high-confidence-only figures are the
 * headline wherever they exist, and the all-tier figures are printed on a
 * labelled second line. Where the high-only index does not publish (fewer
 * than HIGH_ONLY_MIN_AWARDS high awards across HIGH_ONLY_MIN_FAMILIES
 * families — 387 of 444 mart rows at the 2026-09-10 measurement), the
 * all-tier figures are the headline and the chip says which tiers they
 * rest on.
 *
 * ONE basis per page: the Contractor Concentration card and the "Who gets
 * it" answer both call this. The exporter's `_who_gets_it_fid`
 * (src/govbudget/export_site.py) mirrors the `basis` decision so the
 * named-primes / uncrosswalked fallbacks fire exactly when the award tier
 * does not render — change both together.
 *
 * Measure tokens differ per basis on purpose: gate 23 leg a2 groups every
 * [data-amount] on a page by (entity, fy, measure) and fails two distinct
 * values in one group. A high-only figure and its all-tier sibling are two
 * measures, not two bases of one measure.
 *
 * Client-safe: type-only import from lib/data (which is server-only).
 */
import type { ProgramHHI } from "@/lib/data";

export type ConcentrationBasis = "high" | "all";

/** Floor for a high-only index — mirrors fct_program_concentration.sql. */
export const HIGH_ONLY_MIN_AWARDS = 3;
export const HIGH_ONLY_MIN_FAMILIES = 2;

export interface ConcentrationHeadline {
  basis: ConcentrationBasis;
  hhi: number;
  hhi_fact_id: string | null;
  program_dollars: number;
  program_dollars_fact_id: string | null;
  top_family: string;
  family_count: number;
  award_count: number;
  hhiMeasure: "hhi-high" | "hhi";
  dollarsMeasure: "obligations-high" | "obligations";
  /** Tier chip text — names exactly the link tiers the headline rests on. */
  chip: string;
}

export function concentrationHeadline(h: ProgramHHI): ConcentrationHeadline {
  if (
    h.hhi_high !== null &&
    h.program_dollars_high !== null &&
    h.top_family_high !== null
  ) {
    return {
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
      chip: "high-confidence links",
    };
  }
  return {
    basis: "all",
    hhi: h.hhi_all,
    hhi_fact_id: h.hhi_all_fact_id,
    program_dollars: h.program_dollars_all,
    program_dollars_fact_id: h.program_dollars_all_fact_id,
    top_family: h.top_family_all,
    family_count: h.family_count_all,
    award_count: h.award_count_all,
    hhiMeasure: "hhi",
    dollarsMeasure: "obligations",
    chip:
      h.award_count_high === 0
        ? "medium-confidence links only"
        : "high- and medium-confidence links",
  };
}

/** "3 awards across 2 families" — shared by the card and the answer strip. */
export function awardsAcrossFamilies(awards: number, families: number): string {
  return `${awards} award${awards === 1 ? "" : "s"} across ${families} ${families === 1 ? "family" : "families"}`;
}
