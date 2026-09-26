/**
 * The company page's "matched on" term chips carry the identifier spec
 * `t-id`, not the `font-mono` utility (chain G step 12, 2026-09-26).
 *
 * Gate 26 leg (h) counts `font-mono` in the sampled built pages and may only
 * fall (type-allowlist-ratchet.json, frozen at 539). BUILD 1 at a5148814
 * counted 543: the #176 rematch changed Lockheed Martin's lobbying mentions
 * ("Electronic"×2 and "Warfare"×2 in, "2025"×2 out), and every matched term
 * printed as a `font-mono` chip — 91 chips, 182 occurrences with the RSC
 * payload, on /company/lockheed-martin/, a sampled route. New code writes
 * t-id, never font-mono; the chip now does, so its count no longer moves with
 * the data. The face, size, weight and line height are what they were (t-id is
 * the mono face at 12px/400 on a 1rem line, as text-xs + font-mono computed),
 * and `text-primary` still wins over t-id's muted ink (utilities layer).
 *
 * The page renders against the export on disk, so the terms are whatever
 * Lockheed's mentions match today; the assertions hold for any of them.
 */
import { describe, it, expect, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import React from "react";

vi.mock("@/components/citation-panel", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/citation-panel")>()),
  CitationPanelProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const norm = (s: string | null | undefined) => (s ?? "").replace(/\s+/g, " ").trim();

async function renderCompany(slug: string) {
  cleanup();
  const CompanyPage = (await import("@/app/company/[slug]/page")).default;
  const el = await CompanyPage({ params: Promise.resolve({ slug }) });
  return render(el as React.ReactElement).container;
}

describe('company page — "matched on" term chips use the identifier spec (gate 26 ratchet)', () => {
  it("every matched-term chip on /company/lockheed-martin/ is a t-id chip and none is font-mono", async () => {
    const root = await renderCompany("lockheed-martin");
    const groups = [...root.querySelectorAll("[data-matched-terms]")];
    // Lockheed is gate 26's sampled company route; a page with no matched
    // terms would make this test vacuous.
    expect(groups.length, "lockheed-martin renders matched-term rows").toBeGreaterThan(0);

    for (const g of groups) {
      const chips = [...g.querySelectorAll(":scope > span")];
      expect(chips.length).toBeGreaterThan(0);
      for (const chip of chips) {
        expect(chip.classList.contains("t-id"), `chip "${chip.textContent}" carries t-id`).toBe(true);
        // the chip keeps its look: primary ink on a primary tint
        expect(chip.classList.contains("text-primary")).toBe(true);
        expect(chip.classList.contains("bg-primary/10")).toBe(true);
      }
      // nothing in the "matched on" group counts toward the font-mono ratchet
      expect(g.querySelector(".font-mono")).toBeNull();
      expect(g.classList.contains("font-mono")).toBe(false);
      // the words are unchanged: "matched on A, B"
      expect(norm(g.textContent)).toBe(`matched on ${chips.map((c) => norm(c.textContent)).join(", ")}`);
    }
  }, 60000);
});
