import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { parse } from "node-html-parser";
import { FamilyFundingHistory } from "@/components/family-funding-history";
import { getF15FundingHistory, getF15FundingHistorySource } from "@/lib/family-funding-history-data";
import { getCitations } from "@/lib/data";
import { checkFamilyHistory, checkFamilyHistoryAssets } from "../../scripts/gates/family-history.mjs";

describe("family funding release gate", () => {
  const view = getF15FundingHistory();
  const history = getF15FundingHistorySource();
  const citations = getCitations();
  const html = renderToStaticMarkup(<FamilyFundingHistory history={view.history} shortName="F-15" />);
  const check = (h = history, markup = html) => checkFamilyHistory(parse(markup), h, citations, new Set(Object.keys(view.citations)));

  it("accepts the published actuals chain and direct source links", () => {
    expect(check()).toEqual([]);
  });

  it("requires matching historical data and on-demand receipt shards", () => {
    expect(checkFamilyHistoryAssets(history, citations, history, citations)).toEqual([]);
    expect(checkFamilyHistoryAssets(history, citations, null, citations)).toContain("shipped family history differs from the audited export");
    const id = history.points[0].components[0].fact_id;
    const incomplete = { ...citations };
    delete incomplete[id];
    expect(checkFamilyHistoryAssets(history, citations, history, incomplete)).toContain(`receipt ${id} is missing or changed in built citation shards`);
  });

  it("rejects adding a request to cumulative actuals or duplicating a source row", () => {
    const contaminated = structuredClone(history);
    const request = contaminated.points.at(-1)!;
    contaminated.cumulative.point_ids.push(request.id);
    contaminated.cumulative.amount_thousands += request.amount_thousands;
    expect(check(contaminated)).toContain("cumulative actuals do not add up");
    const duplicate = structuredClone(history);
    duplicate.points[0].components.push(duplicate.points[0].components[0]);
    expect(check(duplicate).some((error: string) => error.includes("repeats a source receipt"))).toBe(true);
  });

  it("rejects an old single-record headline and missing government links", () => {
    expect(check(history, html.replace(history.cumulative.fact_id, "4a9ae7cc78dcf0ba"))).toContain("headline is not the exported family actuals total");
    const doc = parse(html);
    const first = doc.querySelector('[data-history-input] a[target="_blank"]')!;
    first.setAttribute("href", "/program/F015EX/");
    expect(check(history, doc.toString()).some((error: string) => error.includes("no direct government spreadsheet link"))).toBe(true);
  });

  it("rejects balanced changes to source amounts even when the yearly sum is unchanged", () => {
    const altered = structuredClone(history);
    altered.points[0].components[0].amount_thousands += 1;
    altered.points[0].components[1].amount_thousands -= 1;
    expect(check(altered).filter((error: string) => error.includes("amount or locator differs from its receipt"))).toHaveLength(2);
  });

  it("rejects a mislabeled year or a source from another fiscal year", () => {
    expect(check(history, html.replace('data-history-year="2015"', 'data-history-year="2014"')).some((error: string) => error.includes("chart year/status differs"))).toBe(true);
    const altered = structuredClone(history);
    altered.points[0].components[0].amount_type = "fy_2014_actuals";
    expect(check(altered).some((error: string) => error.includes("belongs to another fiscal year"))).toBe(true);
  });
});
