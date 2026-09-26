import { describe, it, expect } from "vitest";
import {
  evidenceKindLabel,
  evidenceKindTitle,
  evidenceKindLongExplanation,
} from "@/lib/evidence";

describe("evidenceKindLabel (#52) — no row renders without saying its tier", () => {
  it("labels the three qualifying tiers distinctly", () => {
    expect(evidenceKindLabel("pe_literal")).toBe("PE/BLI code cited directly");
    expect(evidenceKindLabel("alias")).toBe("matched a known alias");
    expect(evidenceKindLabel("multi_token")).toBe("matched 2+ title words");
  });

  it("never crashes on missing/unknown data — falls back to a labelled unknown", () => {
    expect(evidenceKindLabel(null)).toBe("unclassified match");
    expect(evidenceKindLabel(undefined)).toBe("unclassified match");
    expect(evidenceKindLabel("something_new")).toBe("unclassified match");
  });
});

describe("evidenceKindTitle (#52) — short per-row hover form", () => {
  // Regression: a verbose per-row title attribute (the original
  // implementation) was gate 1's page-weight ceiling failure on the
  // heaviest /filing/ page — 131 mention rows x ~180 bytes of repeated
  // title text = 23.7KB, more than the entire ceiling overage. The title
  // is now capped intentionally short since it repeats once per row.
  it("gives a distinct, non-empty, but SHORT rationale per tier", () => {
    const kinds = ["pe_literal", "alias", "multi_token"] as const;
    const titles = kinds.map((k) => evidenceKindTitle(k));
    for (const t of titles) {
      expect(t.length).toBeGreaterThan(10);
      expect(t.length).toBeLessThan(70);
    }
    expect(new Set(titles).size).toBe(titles.length);
  });

  it("never crashes on missing/unknown data", () => {
    expect(evidenceKindTitle(null)).toBe("Evidence tier not recorded.");
    expect(evidenceKindTitle(undefined)).toBe("Evidence tier not recorded.");
  });
});

describe("evidenceKindLongExplanation (#52) — full rationale, for one-time use only", () => {
  it("gives a distinct, non-empty rationale per tier", () => {
    const kinds = ["pe_literal", "alias", "multi_token"] as const;
    const explanations = kinds.map((k) => evidenceKindLongExplanation(k));
    for (const e of explanations) expect(e.length).toBeGreaterThan(20);
    expect(new Set(explanations).size).toBe(explanations.length);
  });

  it("multi_token's rationale states the >=2-word rule (the actual #52 fix)", () => {
    expect(evidenceKindLongExplanation("multi_token")).toMatch(
      /two distinct/i,
    );
  });
});

/**
 * ROADMAP #176 site mirror (decisions wave fix round, 2026-09-26). The
 * matcher (src/govbudget/influence/mentions.py, _build_code_re) now counts an
 * ALL-DIGIT code only where a budget-line label names it ("BLI 2025",
 * "PE 0145", "line item 14"): measured 2026-09-25, all 1,631 `pe_literal` rows
 * sat on bare numbers — years, dates, bill and public-law numbers — and none
 * carried such a label. A code with letters (0604122D8Z, MD08) keeps the plain
 * whole-word rule. The three strings a reader can meet say that rule, and the
 * badge names both kinds of code the tier can carry (a program element or a
 * budget line), not only "PE".
 */
describe("pe_literal states the #176 matcher rule", () => {
  it("the badge names both code kinds the tier carries", () => {
    expect(evidenceKindLabel("pe_literal")).toMatch(/^PE\/BLI code/);
  });

  it("the hover title says an all-digit code needs a budget-line label", () => {
    const t = evidenceKindTitle("pe_literal");
    expect(t).toBe("PE/BLI code in the filing; all-digit codes need a budget-line label.");
    expect(t.length).toBeLessThan(70);
  });

  it("the full rationale states both halves of the rule, with an example", () => {
    const e = evidenceKindLongExplanation("pe_literal");
    expect(e).toMatch(/letters/i);
    expect(e).toMatch(/budget-line label/i);
    expect(e).toContain("BLI 2025");
    expect(e).not.toMatch(/contains this exact program element \/ budget line code\.$/);
  });
});
