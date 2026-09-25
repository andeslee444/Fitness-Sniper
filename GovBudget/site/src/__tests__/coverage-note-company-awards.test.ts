/**
 * The "company-awards" coverage note names the tiers its tables list
 * (2026-09-25 final integration review, finding #9).
 *
 * THE DEFECT. The note rendered above Related Awards on every program page
 * with awards, and above Budget-Linked Awards on every company page, read
 * "— only high-confidence USASpending matches are included." The tables under
 * it list medium rows too: /program/3010-SCN/ one high row then five medium,
 * /company/ernst-young/ 25 rows all medium, and 9 of the 36 companies it
 * counts have no high row at all — the numerator itself counts medium-only
 * companies. Pre-existing in production (5032ff98, Phase 5C).
 *
 * WHAT THIS PINS. The note names both published tiers and never "only
 * high-confidence"; every award row the note sits above — entity_details and
 * program_details sidecars — is one of the two tiers it names (low never
 * publishes, and a third tier appearing must reword the note); and both
 * tiers are actually listed, so the note does not name a tier nothing shows.
 * Gate G2 (scripts/gates/coverage.mjs) still binds the "N of M" figures.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import { getCoverage } from "@/lib/coverage";

const JSON_DIR = path.resolve(__dirname, "..", "..", "..", "data", "site", "json");

function awardTiers(dir: string): Map<string, number> {
  const tiers = new Map<string, number>();
  for (const f of fs.readdirSync(path.join(JSON_DIR, dir))) {
    if (!f.endsWith(".json")) continue;
    const d = JSON.parse(fs.readFileSync(path.join(JSON_DIR, dir, f), "utf8")) as {
      awards?: { confidence?: string | null }[];
    };
    for (const a of d.awards ?? []) {
      const t = String(a.confidence ?? "(none)").toLowerCase();
      tiers.set(t, (tiers.get(t) ?? 0) + 1);
    }
  }
  return tiers;
}

describe("company-awards coverage note", () => {
  const note = getCoverage("company-awards").note;

  it("names both published tiers and says which is weaker", () => {
    expect(note).toContain("high- and medium-confidence USAspending matches");
    expect(note).toContain("medium is the weaker evidence");
  });

  it("never claims the tables are high-confidence only", () => {
    expect(note).not.toMatch(/only high-confidence/i);
  });

  it.each(["entity_details", "program_details"])(
    "every award row in %s is a tier the note names, and both tiers are listed",
    (dir) => {
      const tiers = awardTiers(dir);
      expect([...tiers.keys()].filter((t) => t !== "high" && t !== "medium")).toEqual([]);
      expect(tiers.get("high") ?? 0).toBeGreaterThan(0);
      expect(tiers.get("medium") ?? 0).toBeGreaterThan(0);
    },
  );
});
