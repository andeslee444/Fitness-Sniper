/**
 * gate-report.mjs — the lines `npm run verify` prints for one gate (ROADMAP
 * #201). It showed the first three notes and the warnings; every other note
 * was invisible (gate 21 leg p's among them). Now the summary says how many
 * notes it left out, and VERIFY_NOTES=all prints them.
 */
import { describe, expect, it } from "vitest";
import { gateReportLines } from "../gate-report.mjs";

const notes = (n) => Array.from({ length: n }, (_, i) => `note ${i + 1}`);

describe("gateReportLines", () => {
  it("prints up to three notes on the summary line and nothing else", () => {
    expect(gateReportLines(9, "x", { pass: true, notes: notes(3), errors: [] })).toEqual([
      "gate 9 x: note 1; note 2; note 3 → PASS"]);
  });

  it("says how many notes it left out", () => {
    expect(gateReportLines(9, "x", { pass: true, notes: notes(5), errors: [] }, { allNotes: false })).toEqual([
      "gate 9 x: note 1; note 2; note 3; +2 more notes (VERIFY_NOTES=all prints them) → PASS"]);
    expect(gateReportLines(9, "x", { pass: true, notes: notes(4), errors: [] }, { allNotes: false })[0])
      .toContain("; +1 more note (VERIFY_NOTES=all prints them) → PASS");
  });

  it("still surfaces a warning wherever it sits", () => {
    const result = { pass: true, notes: [...notes(4), "page weight near-ceiling: /x/"], errors: [] };
    expect(gateReportLines(1, "build", result, { allNotes: false })).toEqual([
      "gate 1 build: note 1; note 2; note 3; +2 more notes (VERIFY_NOTES=all prints them) → PASS",
      "  ⚠ page weight near-ceiling: /x/"]);
  });

  it("prints every note with VERIFY_NOTES=all", () => {
    const result = { pass: false, notes: [...notes(4), "page weight near-ceiling: /x/"], errors: ["e1"] };
    expect(gateReportLines(21, "program-skeleton", result, { allNotes: true })).toEqual([
      "gate 21 program-skeleton: note 1; note 2; note 3; +2 more notes; ERRORS: e1 → FAIL",
      "  · note 4",
      "  ⚠ page weight near-ceiling: /x/",
      "  ✗ e1"]);
  });

  it("reads VERIFY_NOTES from the environment by default", () => {
    const before = process.env.VERIFY_NOTES;
    process.env.VERIFY_NOTES = "all";
    try {
      expect(gateReportLines(9, "x", { pass: true, notes: notes(4), errors: [] })).toEqual([
        "gate 9 x: note 1; note 2; note 3; +1 more note → PASS", "  · note 4"]);
    } finally {
      if (before === undefined) delete process.env.VERIFY_NOTES;
      else process.env.VERIFY_NOTES = before;
    }
  });
});
