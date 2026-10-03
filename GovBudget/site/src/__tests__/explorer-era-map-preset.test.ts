/**
 * /data/ Explorer presets for p1_era_line_map (families piece 1, Task 19).
 * The map carries decisions, not money: the presets count chains (distinct
 * decision_id) and lines, and list the owner review batches by ruling id.
 * tests/test_explorer_era_map_preset.py runs both against a fixture parquet.
 */
import { describe, it, expect } from "vitest";
import { cannedQueriesFor } from "@/components/explorer";

describe("Explorer — p1_era_line_map presets", () => {
  const presets = cannedQueriesFor("p1_era_line_map");
  const sql = (label: string): string =>
    presets.find((q) => q.label === label)!.sql.replace(/\s+/g, " ");

  it("offers the two presets, in order", () => {
    expect(presets.map((q) => q.label)).toEqual([
      "Decisions by edition",
      "Lines decided in owner review batches",
    ]);
  });

  it("counts chains as distinct decisions and lines as rows, per edition and decision", () => {
    expect(sql("Decisions by edition")).toMatch(/COUNT\(DISTINCT decision_id\) AS chains/);
    expect(sql("Decisions by edition")).toMatch(/COUNT\(\*\) AS lines/);
    expect(sql("Decisions by edition")).toMatch(/GROUP BY edition, decision ORDER BY edition, decision/);
  });

  it("selects the owner review batches by their ruling id", () => {
    expect(sql("Lines decided in owner review batches")).toContain("WHERE ruling LIKE 'R-DEC-ERA-B%'");
  });

  it("reads the map parquet and no amount column", () => {
    for (const q of presets) {
      expect(q.sql).toContain("FROM 'p1_era_line_map.parquet'");
      expect(q.sql).not.toMatch(/amount/i);
    }
  });
});
