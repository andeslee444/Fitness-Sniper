/**
 * Gate 13 leg (k) — every citation source link this site serves resolves
 * (ROADMAP #191: both SAM registration facts linked to sam.gov/entity/<UEI>,
 * SAM.gov's 404 page, and no gate read citation inputs at all).
 *
 * Run via `npm test` (vitest).
 */
import { describe, it, expect } from "vitest";
import { citationInputFindings } from "../linkgraph.mjs";

const UEI = "ZFN2JJXBLZT3";
const RECEIPT = `https://fiscalreceipts.com/json/sam/${UEI}.json`;
const samRow = (inputs) => ({
  kind: "derived",
  formula: `SAM.gov Entity Management registration for UEI ${UEI}, family lockheed: ...`,
  inputs: JSON.stringify(inputs),
});

describe("citationInputFindings (leg k)", () => {
  it("passes a SAM fact that cites its built receipt", () => {
    const r = citationInputFindings({
      shardRows: { a: samRow([RECEIPT]) },
      builtPaths: new Set([`/json/sam/${UEI}.json`]),
      receiptUeis: new Set([UEI]),
    });
    expect(r.errors).toEqual([]);
    expect(r.samFacts).toBe(1);
  });

  it("fails the sam.gov entity route — the live bug", () => {
    const r = citationInputFindings({
      shardRows: { a: samRow([`https://sam.gov/entity/${UEI}`]) },
      builtPaths: new Set(),
      receiptUeis: new Set(),
    });
    expect(r.errors.join("\n")).toMatch(/404 page/);
    expect(r.errors.join("\n")).toMatch(/must cite exactly its receipt/);
  });

  it("fails a same-origin input that was not built", () => {
    const r = citationInputFindings({
      shardRows: { a: samRow([RECEIPT]) },
      builtPaths: new Set(),
      receiptUeis: new Set(),
    });
    expect(r.errors.join("\n")).toMatch(/was not built/);
    expect(r.errors.join("\n")).toMatch(/cited but missing/);
  });

  it("ignores external inputs and fact-id inputs", () => {
    const r = citationInputFindings({
      shardRows: {
        b: { kind: "derived", formula: "sum(...)", inputs: JSON.stringify(["4eb7fe9bd4fa4af5"]) },
        c: { kind: "derived", formula: "x", inputs: JSON.stringify(["https://lda.gov/filings/1"]) },
      },
      builtPaths: new Set(),
      receiptUeis: new Set(),
    });
    expect(r.errors).toEqual([]);
    expect(r.urlInputs).toBe(1);
    expect(r.testedInputs).toBe(0);   // cross-origin: counted, not opened
  });
});
