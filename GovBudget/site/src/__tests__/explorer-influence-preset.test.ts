/**
 * /data/ Explorer — the "Lobbying totals by family + year" preset
 * (R-DEC-EXPLORER, final-review rulings 2026-09-27; final review finding #9).
 *
 * THE DEFECT. fct_influence is one row per (family, filing year), so the
 * preset's `COUNT(*) AS filing_count` grouped by family and year was 1 on
 * every row, beside a real `filings_count` of 59 / 65 / 33 (Lockheed Martin
 * 2024 / 2025 / 2026) that /company/lockheed-martin/ renders. And under a
 * title promising lobbying totals it selected no lobbying dollars at all —
 * only SUM(family_obligations_usd), the family's all-years obligation total
 * repeated on each year row ($532B for Lockheed in every year).
 *
 * WHAT THIS PINS (the SQL's shape; tests/test_explorer_influence_preset.py
 * runs it against the shipped parquet with DuckDB):
 *  - the filing count is the sum of the mart's own filings_count;
 *  - lobbying income and lobbying expense are both selected;
 *  - no obligations column (a lifetime figure beside a year is not a
 *    per-year figure), and no COUNT(*);
 *  - income and expense are never added together, and the mart's
 *    lobbying_total_usd is not selected. R-DEC-LDATOTAL (final-review rulings,
 *    2026-09-27): lobbying income and expense stay NON-ADDITIVE on the site —
 *    a self-filer's reported expense can include what it paid the outside
 *    firms whose income is also reported, so a sum can double-count. That is
 *    the company page's reviewed decision (it suppresses its Total column;
 *    ROADMAP: "the most serious finding of either panel"), and the ruling
 *    keeps this preset "without a total (as built)". The ruling, not any
 *    dataset note's wording, is the authority: the /data/ note this header
 *    used to quote ("alternative disclosures — non-additive, never summed")
 *    was rewritten in the same round.
 */
import fs from "fs";
import path from "path";
import { describe, it, expect } from "vitest";
import { cannedQueriesFor } from "@/components/explorer";

describe("Explorer — fct_influence preset", () => {
  const presets = cannedQueriesFor("fct_influence");
  const preset = presets.find((q) => q.label === "Lobbying totals by family + year");

  it("keeps its label", () => {
    expect(preset).toBeDefined();
  });

  const sql = () => preset!.sql.replace(/\s+/g, " ");

  it("counts filings as the sum of the mart's filings_count, never COUNT(*)", () => {
    expect(sql()).toMatch(/SUM\(filings_count\) AS filings\b/);
    expect(sql()).not.toMatch(/COUNT\(\*\)/i);
  });

  it("selects lobbying income and lobbying expense", () => {
    expect(sql()).toMatch(/SUM\(lobbying_income_usd\) AS income_usd\b/);
    expect(sql()).toMatch(/SUM\(lobbying_expense_usd\) AS expense_usd\b/);
  });

  it("carries no obligations figure and never adds income to expense", () => {
    expect(sql()).not.toMatch(/obligations/i);
    expect(sql()).not.toMatch(/lobbying_total_usd/);
    expect(sql()).not.toMatch(/income_usd\s*\+|\+\s*\w*expense_usd/);
  });

  it("orders deterministically (the grain is family × year)", () => {
    expect(sql()).toMatch(/ORDER BY filings DESC, family_key, filing_year DESC/);
  });

  it("the preset's source comment cites R-DEC-LDATOTAL, not the rewritten /data/ note", () => {
    // The comment is the preset's only stated reason for having no total; it
    // must rest on the ruling that decides it, never on a note another change
    // can rewrite out from under it.
    const src = fs.readFileSync(
      path.resolve(__dirname, "..", "components", "explorer.tsx"),
      "utf8",
    );
    const at = src.indexOf('case "fct_influence":');
    expect(at).toBeGreaterThan(-1);
    const block = src.slice(at, src.indexOf("case ", at + 1));
    expect(block).toContain("R-DEC-LDATOTAL");
    expect(block).not.toMatch(/alternative disclosures/);
    expect(block).not.toMatch(/never summed/);
    expect(block).not.toMatch(/final review #8\b/);
  });
});
