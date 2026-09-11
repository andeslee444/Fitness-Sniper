/**
 * Unit tests for gate 14 leg cm's program-pages split (coverage.mjs) — #106.
 *
 * THE DEFECT. The leg computed rollupOnly = pages − detail − decade and then
 * asserted detail + rollupOnly + decade === pages: true by construction. Its
 * substring checks were "73" and "553", which any other number on the row
 * could satisfy. /methodology/ meanwhile rendered "553whose" and nothing
 * noticed. The check now reads the sentence a reader sees and adds it up,
 * and each bucket is read off the sidecar's own content.
 *
 * Run via `npm test` (vitest).
 */

import fs from "fs";
import os from "os";
import path from "path";
import { describe, it, expect } from "vitest";
import {
  checkProgramPagesSplit,
  classifyProgramSidecars,
  PROGRAM_PAGES_SPLIT_RE,
} from "../coverage.mjs";

const SHIPPED =
  "1,936 of 2,562 program pages carry detail-grade J-book justification; " +
  "73 carry cited FY2026 R-1/P-1 workbook figures only, and 553 are history " +
  "pages for elements the FY2026 workbooks do not list at all.";

describe("checkProgramPagesSplit", () => {
  it("accepts the shipped sentence and returns its four numbers", () => {
    const r = checkProgramPagesSplit(SHIPPED);
    expect(r.ok).toBe(true);
    expect(r.parts).toEqual({ detail: 1936, total: 2562, rollup: 73, decade: 553 });
  });

  it("fails when the parts do not sum to the total, naming the arithmetic", () => {
    const r = checkProgramPagesSplit(SHIPPED.replace("73 carry", "72 carry"));
    expect(r.ok).toBe(false);
    expect(r.why).toContain("1936 detail-grade + 72 workbook-only + 553 history = 2561");
    expect(r.why).toContain("says 2562");
    expect(r.parts.rollup).toBe(72);
  });

  it("fails when a number is glued to the word after it — the #106 species", () => {
    expect(checkProgramPagesSplit(SHIPPED.replace("553 are", "553are")).ok).toBe(false);
    expect(checkProgramPagesSplit(SHIPPED.replace("1,936 of", "1,936of")).ok).toBe(false);
  });

  it("fails when the sentence is reworded out of shape", () => {
    const r = checkProgramPagesSplit("1,936 of 2,562 program pages have detail.");
    expect(r.ok).toBe(false);
    expect(r.parts).toBeNull();
    expect(r.why).toContain("does not read");
  });

  it("collapses whitespace the way the rendered cell is read", () => {
    expect(checkProgramPagesSplit(SHIPPED.replace(/ /g, "\n  ")).ok).toBe(true);
  });

  it("the shape is loose in prose and exact on the numbers' clauses", () => {
    expect(
      PROGRAM_PAGES_SPLIT_RE.test(SHIPPED.replace("J-book justification", "anything at all")),
    ).toBe(true);
    expect(PROGRAM_PAGES_SPLIT_RE.test(SHIPPED.replace("R-1/P-1", "R1/P1"))).toBe(false);
  });
});

describe("classifyProgramSidecars", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "coverage-split-"));
  const write = (name, obj) =>
    fs.writeFileSync(path.join(dir, name), JSON.stringify(obj));
  write("detail.json", { details: [{}], budget_lines: [{}] });
  write("rollup.json", { details: [], budget_lines: [{}], tier: "rollup" });
  write("tierless-workbook.json", { details: [], budget_lines: [{}] });
  write("decade.json", { details: [], budget_lines: [], tier: "decade" });
  write("neither.json", { details: [], budget_lines: [] });
  fs.writeFileSync(path.join(dir, "broken.json"), "{ not json");

  it("reads each bucket off the sidecar's own content and names the rest", () => {
    const r = classifyProgramSidecars(dir, fs.readdirSync(dir));
    expect(r.detail).toBe(1);
    expect(r.workbookOnly).toBe(2);
    expect(r.decadeOnly).toBe(1);
    expect([...r.unclassified].sort()).toEqual(["broken.json", "neither.json"]);
  });

  it("a detail row wins over a tier marker — the predicates are ordered", () => {
    const d2 = fs.mkdtempSync(path.join(os.tmpdir(), "coverage-split-"));
    fs.writeFileSync(
      path.join(d2, "x.json"),
      JSON.stringify({ details: [{}], tier: "decade" }),
    );
    expect(classifyProgramSidecars(d2, ["x.json"])).toEqual({
      detail: 1,
      workbookOnly: 0,
      decadeOnly: 0,
      unclassified: [],
    });
  });
});
