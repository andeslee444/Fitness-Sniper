/** Exported family totals retain the exact workbook rows behind each year. */
export interface FamilyFundingInput {
  program_id: string;
  fact_id: string;
  dataset: string;
  pe_bli: string;
  program_slug: string | null;
  title: string;
  exhibit: string;
  account: string;
  organization: string;
  budget_activity: string;
  amount_type: string;
  measure: string;
  amount_thousands: number;
  official_url: string;
  sheet: string;
  cells: string;
}

/** Durable government codes, scoped to their exhibit, account and service. */
export interface FamilyFundingProgram {
  id: string;
  code: string;
  title: string;
  program_slug: string | null;
  exhibit: string;
  account: string;
  organization: string;
  /** A budget book's own sentence about this line, quoted verbatim ([brackets] gloss it); always paired with note_fact_id. */
  note?: string;
  /** The jbook_narrative receipt for `note`: the page that prints the sentence. */
  note_fact_id?: string;
}

export interface FamilyFundingCell {
  program_id: string;
  amount_thousands: number;
  fact_id: string;
  measure: string;
  dataset: string;
  input_fact_ids: string[];
}

export interface FamilyFundingPoint {
  id: string;
  fy: number;
  edition: number;
  kind: "actuals" | "enacted" | "request";
  measure: string;
  measure_label: string;
  amount_thousands: number;
  fact_id: string;
  coverage: "covered-records" | "partial";
  missing_programs: string[];
  components: FamilyFundingInput[];
  program_cells: FamilyFundingCell[];
}

export interface FamilyFundingHistoryData {
  schema_version: 1;
  family_id: string;
  units: "USD thousands";
  basis: "toa";
  start_fy: number;
  end_fy: number;
  scope_note: string;
  coverage_notes: string[];
  default_point_ids: string[];
  points: FamilyFundingPoint[];
  programs: FamilyFundingProgram[];
  cumulative: {
    start_fy: number;
    end_fy: number;
    kind: "actuals";
    measure: string;
    amount_thousands: number;
    fact_id: string;
    point_ids: string[];
    scope_note: string;
  };
}

/** The complete matrix renders immediately; receipts resolve on demand. */
export type FamilyFundingPointSummary = Omit<FamilyFundingPoint, "components"> & {
  component_count: number;
  components?: FamilyFundingInput[];
};

export type FamilyFundingHistoryView = Omit<FamilyFundingHistoryData, "points"> & {
  points: FamilyFundingPointSummary[];
};

export const FAMILY_HISTORY_URL = "/json/f15_funding_history.json";

/** One published snapshot per year. Requests never fill a gap in actuals. */
export function familyHistorySeries<T extends { id: string; fy: number }>(history: { default_point_ids: string[]; points: T[] }): T[] {
  return history.default_point_ids.map(id => {
    const point = history.points.find(point => point.id === id);
    if (!point) throw new Error(`Family history has no point ${id}`);
    return point;
  }).sort((a, b) => a.fy - b.fy);
}

/** A late fetch must describe the same published figures as the loaded page. */
export function familyHistoryInputRows(value: unknown, history: FamilyFundingHistoryView): Record<string, FamilyFundingInput[]> {
  if (!value || typeof value !== "object") throw new Error("Invalid family history response");
  const full = value as FamilyFundingHistoryData;
  validateFamilyHistoryMatrix(full);
  if (JSON.stringify(full.programs) !== JSON.stringify(history.programs)) throw new Error("Family history programs do not match this page");
  if (full.schema_version !== history.schema_version || full.family_id !== history.family_id || full.basis !== history.basis || full.units !== history.units || !Array.isArray(full.points)) {
    throw new Error("Unsupported family history response");
  }
  const rows: Record<string, FamilyFundingInput[]> = {};
  for (const summary of history.points) {
    const matches = full.points.filter(point => point.id === summary.id);
    const point = matches[0];
    if (JSON.stringify(point?.program_cells) !== JSON.stringify(summary.program_cells)) throw new Error("Family history cells do not match this page");
    const expectedInputs = summary.program_cells.flatMap(cell => cell.input_fact_ids).sort().join(",");
    if (matches.length !== 1 || point.fact_id !== summary.fact_id || point.fy !== summary.fy || point.edition !== summary.edition || point.kind !== summary.kind || point.measure !== summary.measure || point.amount_thousands !== summary.amount_thousands || !Array.isArray(point.components) || point.components.length !== summary.component_count || point.components.map(row => row.fact_id).sort().join(",") !== expectedInputs) {
      throw new Error("Family history response does not match this page");
    }
    const ids = new Set<string>();
    let amount = 0;
    for (const row of point.components) {
      if (!/^[0-9a-f]{16}$/.test(row.fact_id) || ids.has(row.fact_id) || !Number.isFinite(row.amount_thousands) || typeof row.title !== "string" || typeof row.sheet !== "string" || typeof row.cells !== "string" || typeof row.exhibit !== "string" || typeof row.measure !== "string" || !row.amount_type?.startsWith(`fy_${summary.fy}_`) || !["budget_lines", "budget_lines_decade"].includes(row.dataset) || !/^https:\/\/[^/]+\.(?:mil|gov)\//.test(row.official_url)) {
        throw new Error("Invalid family history source row");
      }
      ids.add(row.fact_id);
      amount += row.amount_thousands;
    }
    if (Math.abs(amount - point.amount_thousands) > 0.000001) throw new Error("Family history source rows disagree with total");
    rows[summary.id] = point.components;
  }
  return rows;
}

/** A displayed cell partitions the annual inputs, never inventing an allocation. */
export function validateFamilyHistoryMatrix(history: FamilyFundingHistoryData): void {
  if (!Array.isArray(history.programs) || !Array.isArray(history.points)) throw new Error("Missing family funding matrix");
  const programs = new Map(history.programs.map(program => [program.id, program]));
  if (programs.size !== history.programs.length) throw new Error("Duplicate family program identity");
  for (const program of history.programs) {
    const hasNote = program.note !== undefined, hasReceipt = program.note_fact_id !== undefined;
    if (hasNote !== hasReceipt || (hasNote && (!program.note!.trim() || !/^[0-9a-f]{16}$/.test(program.note_fact_id!)))) {
      throw new Error(`Invalid family program note: ${program.code}`);
    }
  }
  for (const point of history.points) {
    const inputs = new Map(point.components.map(row => [row.fact_id, row]));
    const seen = new Set<string>();
    const groups = new Set<string>();
    let total = 0;
    if (!Array.isArray(point.program_cells)) throw new Error("Missing family funding cells");
    for (const cell of point.program_cells) {
      if (!programs.has(cell.program_id) || groups.has(cell.program_id) || !cell.input_fact_ids.length || !Number.isFinite(cell.amount_thousands)) throw new Error("Invalid family funding cell");
      groups.add(cell.program_id);
      let amount = 0;
      for (const id of cell.input_fact_ids) {
        const input = inputs.get(id);
        if (!input || seen.has(id) || input.program_id !== cell.program_id) throw new Error("Family cell inputs disagree with program identity");
        seen.add(id);
        amount += input.amount_thousands;
      }
      if (Math.abs(amount - cell.amount_thousands) > 0.000001) throw new Error("Family cell inputs disagree with total");
      total += cell.amount_thousands;
    }
    if (seen.size !== point.components.length || Math.abs(total - point.amount_thousands) > 0.000001) throw new Error("Family cells do not partition the annual total");
  }
}
