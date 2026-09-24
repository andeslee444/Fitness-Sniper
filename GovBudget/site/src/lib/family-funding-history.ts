/** Exported family totals retain the exact workbook rows behind each year. */
export interface FamilyFundingInput {
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

/** One published snapshot per year. Requests never fill a gap in actuals. */
export function familyHistorySeries(history: FamilyFundingHistoryData): FamilyFundingPoint[] {
  return history.default_point_ids.map(id => {
    const point = history.points.find(point => point.id === id);
    if (!point) throw new Error(`Family history has no point ${id}`);
    return point;
  }).sort((a, b) => a.fy - b.fy);
}
