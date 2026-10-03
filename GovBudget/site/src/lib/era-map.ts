/**
 * The era-map summary's shape and its one rendering rule (families piece 1,
 * spec 2026-10-02 §4.4, §6.4). UNIVERSAL (no server-only import), so the
 * component and its tests share it. Gate 24 leg (s) formats the same cells
 * with its OWN code, never this module, so a change here has to agree with
 * the gate to pass.
 *
 * Counts only. Dollars stay in json/era_map_summary.json: a rendered $ must
 * carry a Cite state (gate 2), and these per-decision sums have none. The
 * summary never crosses into a client component either: /downloads/ renders
 * <EraMapTable> on the server and hands DownloadCards the rendered table, so
 * the RSC payload carries the cells, not actuals_thousands (Task 19 fix
 * round 1; gate 24 leg (s) checks the built page).
 *
 * "N codes" counts printed codes (distinct line_item_code), not decisions: a
 * code can span several decisions (FY2017CR placeholders in 23 accounts of
 * PB2018; codes 30 and 500 across organizations), and the decision count
 * overstated the codes each column covers (Task 19 fix round 1).
 */
import { formatCount } from "./format";

export const ERA_DECISIONS = [
  "same_program",
  "history_only",
  "exclude_placeholder",
  "exclude_route_unsafe",
  "exclude_reused_code",
] as const;
export type EraDecision = (typeof ERA_DECISIONS)[number];

/** The decisions the "Excluded" column covers (its codes are
 *  `excluded_codes`, distinct across all three). */
export const ERA_EXCLUDED: readonly EraDecision[] = [
  "exclude_placeholder",
  "exclude_route_unsafe",
  "exclude_reused_code",
];

export interface EraMapTally {
  /** Distinct decisions (decision_id). */
  chains: number;
  /** Distinct printed codes (line_item_code): what the table renders. */
  codes: number;
  lines: number;
  actuals_thousands: number;
}

export interface EraMapEdition {
  edition: number;
  fy_actuals: number;
  lines: number;
  by_decision: Record<EraDecision, EraMapTally>;
  /** Distinct printed codes across the three exclude decisions. */
  excluded_codes: number;
  receipts: { facts: number; complete: number };
}

export interface EraMapRulingTally extends EraMapTally {
  ruling: string;
  decision: EraDecision;
}

export interface EraMapSummary {
  schema_version: 1;
  actuals_basis: string;
  receipts_basis: string;
  editions: EraMapEdition[];
  by_ruling: EraMapRulingTally[];
  totals: Record<EraDecision, EraMapTally>;
}

export const ERA_MAP_COLUMNS = [
  { key: "lines", label: "Lines" },
  { key: "same_program", label: "Same program" },
  { key: "history_only", label: "History only" },
  { key: "excluded", label: "Excluded" },
  { key: "receipts", label: "PDF receipts" },
] as const;
export type EraMapColumn = (typeof ERA_MAP_COLUMNS)[number]["key"];

const codes = (n: number): string => `${formatCount(n)} ${n === 1 ? "code" : "codes"}`;

/** One edition's cells, in column order. */
export function eraMapCells(e: EraMapEdition): { key: EraMapColumn; label: string; value: string }[] {
  const codesOf = (d: EraDecision): number => e.by_decision[d]?.codes ?? 0;
  const values: Record<EraMapColumn, string> = {
    lines: formatCount(e.lines),
    same_program: codes(codesOf("same_program")),
    history_only: codes(codesOf("history_only")),
    excluded: codes(e.excluded_codes ?? 0),
    receipts: `${formatCount(e.receipts.complete)} of ${formatCount(e.receipts.facts)}`,
  };
  return ERA_MAP_COLUMNS.map((c) => ({ key: c.key, label: c.label, value: values[c.key] }));
}
