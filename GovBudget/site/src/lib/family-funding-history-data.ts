import "server-only";
import { readFileSync } from "fs";
import { join } from "path";
import { collectCitationsWithInputs } from "@/lib/data";
import { familyHistorySeries, type FamilyFundingHistoryData } from "./family-funding-history";

export function getF15FundingHistory() {
  const history = JSON.parse(readFileSync(join(process.cwd(), "..", "data/site/json/f15_funding_history.json"), "utf8")) as FamilyFundingHistoryData;
  if (history.schema_version !== 1 || history.family_id !== "f-15" || history.basis !== "toa" || history.units !== "USD thousands") {
    throw new Error("Unsupported F-15 funding history schema");
  }
  const series = familyHistorySeries(history);
  if (!series.length || new Set(series.map(point => point.fy)).size !== series.length) {
    throw new Error("Family history must have one default snapshot per fiscal year");
  }
  const factIds = [history.cumulative.fact_id, ...series.flatMap(point => [point.fact_id, ...point.components.map(row => row.fact_id)])];
  const citations = collectCitationsWithInputs(factIds);
  for (const factId of factIds) if (!citations[factId]) throw new Error(`Missing family history receipt ${factId}`);
  return { history: { ...history, points: series }, citations };
}
