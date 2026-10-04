/**
 * /data/ Explorer preset "Rows per President's Budget edition" on
 * budget_lines_decade (families piece 1 final review T3). It counted
 * COUNT(DISTINCT pe_bli) AS program_elements, but since the era tier a
 * PB2017–PB2023 P-1 row's pe_bli is an era key (one per edition's display
 * line), not a program element: on the S5 export PB2017 reads 1,662, 744 of
 * them era keys. The column is named for what it counts; the query and its
 * results are unchanged.
 */
import { describe, it, expect } from "vitest";
import { cannedQueriesFor } from "@/components/explorer";

describe("Explorer — budget_lines_decade presets", () => {
  const presets = cannedQueriesFor("budget_lines_decade");
  const sql = (label: string): string =>
    presets.find((q) => q.label === label)!.sql.replace(/\s+/g, " ");

  it("names the distinct-pe_bli count for what it is", () => {
    const q = sql("Rows per President's Budget edition");
    expect(q).toContain("COUNT(DISTINCT pe_bli) AS pe_bli_keys");
    expect(q).not.toMatch(/program_elements/);
  });
});
