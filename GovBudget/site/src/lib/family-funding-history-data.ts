import "server-only";
import { readFileSync } from "fs";
import { join } from "path";
import { collectCitations } from "@/lib/data";
import { familyHistorySeries, validateFamilyHistoryMatrix, type FamilyFundingHistoryData, type FamilyFundingHistoryView } from "./family-funding-history";

export function getF15FundingHistorySource(): FamilyFundingHistoryData {
  const history = JSON.parse(readFileSync(join(process.cwd(), "..", "data/site/json/f15_funding_history.json"), "utf8")) as FamilyFundingHistoryData;
  if (history.schema_version !== 1 || history.family_id !== "f-15" || history.basis !== "toa" || history.units !== "USD thousands") {
    throw new Error("Unsupported F-15 funding history schema");
  }
  validateFamilyHistoryMatrix(history);
  const series = familyHistorySeries(history);
  if (!series.length || new Set(series.map(point => point.fy)).size !== series.length) {
    throw new Error("Family history must have one default snapshot per fiscal year");
  }
  return history;
}

export function getF15FundingHistory() {
  const source = getF15FundingHistorySource();
  const series = familyHistorySeries(source);
  const latest = series.at(-1)!;
  // All amounts render immediately. Older annual and program receipts resolve
  // from existing citation shards on demand, keeping the full matrix compact.
  const factIds = [...new Set([source.cumulative.fact_id, latest.fact_id, ...latest.components.map(row => row.fact_id), ...latest.program_cells.map(cell => cell.fact_id)])];
  const citations = collectCitations(factIds);
  for (const factId of factIds) if (!citations[factId]) throw new Error(`Missing family history receipt ${factId}`);
  const history: FamilyFundingHistoryView = {
    ...source,
    points: series.map(({ components, ...point }) => ({
      ...point, component_count: components.length, input_fact_ids: components.map(row => row.fact_id),
    })),
  };
  return { history, citations };
}
