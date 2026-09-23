import { describe, expect, it } from "vitest";
import { getF15FamilyData } from "@/lib/f15-family-data";
import { getFundingInputs, getRecordFact, type FamilyFundingFact } from "@/lib/f15-family";
import type { CitationsMap } from "@/lib/data";

const family = getF15FamilyData();
const original = family.records.find((record) => record.slug === "F015EX")!;
const inputIds = ["03407158217dec76", "5768200ce4fbc494", "819f32a0ad3fb66e"];

function fixture() {
  const record = structuredClone(original);
  const fact = getRecordFact(record, 2026)!;
  const citations: CitationsMap = structuredClone(family.citations);
  const citation = citations[fact.factId];
  if (citation.kind !== "derived") throw new Error("Expected a canonical additive receipt");
  return { record, fact, citations, citation };
}

describe("F-15 canonical receipt inputs", () => {
  it("uses only the three declared FY2026 inputs and ignores same-year alternative measures", () => {
    const { record, fact, citations } = fixture();
    const inputs = getFundingInputs(record, fact, citations);
    expect(inputs.map((input) => input.factId)).toEqual(inputIds);
    expect(inputs.map((input) => input.amountThousands)).toEqual([2_480_818, 286_700, 246_876]);
    expect(inputs.reduce((sum, input) => sum + input.amountThousands, 0)).toBe(3_014_394);
    const alternativeRows = record.componentRows.filter((input) => input.fy === 2026 && !inputIds.includes(input.factId));
    expect(alternativeRows).toHaveLength(3);
    expect(alternativeRows.every((input) => input.measure === "reconciliation-request")).toBe(true);
    expect(alternativeRows.reduce((sum, input) => sum + input.amountThousands, 0)).toBe(fact.amountThousands);
    expect(inputs.every((input) => input.measure === "request")).toBe(true);
    expect(inputs.some((input) => input.factId === fact.factId)).toBe(false);
  });

  it("uses a historical receipt's own inputs and omits a direct workbook total", () => {
    const { record, citations } = fixture();
    expect(getFundingInputs(record, getRecordFact(record, 2024), citations).map((input) => input.factId)).toEqual(["c05ad3ce0481b0ef", "97884d9ae98e9e06"]);
    expect(getFundingInputs(record, getRecordFact(record, 2025), citations)).toEqual([]);
    expect(getFundingInputs(record, null, citations)).toEqual([]);
  });

  it.each([
    ["invalid JSON", "not-json"],
    ["object", JSON.stringify({ inputs: inputIds })],
    ["scalar", JSON.stringify(inputIds[0])],
    ["empty list", "[]"],
    ["one input", JSON.stringify([inputIds[0]])],
    ["mixed types", JSON.stringify([inputIds[0], null, 12])],
    ["duplicate identities", JSON.stringify([inputIds[0], inputIds[0], inputIds[1]])],
    ["missing member", JSON.stringify([inputIds[0], inputIds[1], "0000000000000000"])],
    ["partial total", JSON.stringify(inputIds.slice(0, 2))],
  ])("refuses %s instead of displaying a partial breakdown", (_, malformed) => {
    const { record, fact, citations, citation } = fixture();
    citation.inputs = malformed;
    expect(getFundingInputs(record, fact, citations)).toEqual([]);
  });

  it.each([
    ["year", { fy: 2025 }],
    ["units", { units: "USD" }],
    ["basis", { basis: "jbook-detail" }],
    ["budget edition", { edition: 2025 }],
    ["funding measure", { measure: "reconciliation-request" }],
    ["nonfinite amount", { amountThousands: Number.NaN }],
    ["infinite amount", { amountThousands: Number.POSITIVE_INFINITY }],
    ["sum mismatch", { amountThousands: 2_480_819 }],
  ])("refuses a mismatched %s on any declared component", (_, patch) => {
    const { record, fact, citations } = fixture();
    record.componentRows = record.componentRows.map((row) => row.factId === inputIds[0] ? { ...row, ...patch } as FamilyFundingFact : row);
    expect(getFundingInputs(record, fact, citations)).toEqual([]);
  });

  it("requires every input row and its citation to be unique and present", () => {
    for (const change of ["missing row", "missing citation", "duplicate row"] as const) {
      const { record, fact, citations } = fixture();
      if (change === "missing row") record.componentRows = record.componentRows.filter((row) => row.factId !== inputIds[1]);
      if (change === "missing citation") delete citations[inputIds[1]];
      if (change === "duplicate row") record.componentRows.push({ ...record.componentRows.find((row) => row.factId === inputIds[1])! });
      expect(getFundingInputs(record, fact, citations), change).toEqual([]);
    }
  });

  it("requires an explicitly additive canonical citation", () => {
    const { record, fact, citations, citation } = fixture();
    citation.formula = "difference(previous_year,current_year)";
    expect(getFundingInputs(record, fact, citations)).toEqual([]);
    delete citations[fact.factId];
    expect(getFundingInputs(record, fact, citations)).toEqual([]);
  });

  it.each([8, 9])("accepts at most eight otherwise valid additive inputs (count %i)", (count) => {
    const { record, fact, citations, citation } = fixture();
    const template = record.componentRows.find((row) => row.factId === inputIds[0])!;
    record.componentRows = Array.from({ length: count }, (_, index) => ({ ...template, factId: (index + 1).toString(16).padStart(16, "0"), amountThousands: 100 }));
    fact.amountThousands = count * 100;
    citation.recorded_value = String(fact.amountThousands);
    citation.inputs = JSON.stringify(record.componentRows.map((row) => row.factId));
    const sourceCitation = citations[inputIds[0]];
    if (sourceCitation.kind !== "workbook") throw new Error("Expected a workbook input");
    for (const row of record.componentRows) citations[row.factId] = { ...sourceCitation, amount_thousands: row.amountThousands };
    expect(getFundingInputs(record, fact, citations)).toHaveLength(count === 8 ? 8 : 0);
  });
});
