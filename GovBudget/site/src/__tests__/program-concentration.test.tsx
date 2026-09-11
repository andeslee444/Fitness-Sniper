/**
 * ROADMAP #80 — the Contractor Concentration card publishes both link
 * bases and headlines the high-only one where it exists.
 *
 * DOM contract (read by scripts/gates/feed.mjs leg l and gate 23 leg a2):
 *   - exactly ONE [data-hhi-band], stamped data-hhi-basis="high"|"all"
 *   - a [data-concentration-tier-chip] naming the tiers the headline rests on
 *   - the all-tier figures keep measures "hhi"/"obligations"; the high-only
 *     figures carry "hhi-high"/"obligations-high" so leg a2 never groups the
 *     two bases as one (entity, fy, measure) label
 *   - one [data-concentration-secondary] line: "all" (shape A), "high"
 *     (shape B: high links below the floor) or "none" (shape C: no high link)
 */
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import { ProgramConcentration } from "@/components/program-concentration";
import { concentrationHeadline } from "@/lib/concentration-basis";
import type { ProgramHHI } from "@/lib/data";

// hhi_all 2100.4 → "Moderately Concentrated" (1,500–2,500); hhi_high 9800.2 →
// "Highly Concentrated" — the two bands differ on purpose so the tests can
// tell the headline badge from the second line's plain-text band.
const A: ProgramHHI = {
  hhi_all: 2100.4, hhi_all_fact_id: "a".repeat(16),
  program_dollars_all: 500_000_000, program_dollars_all_fact_id: "b".repeat(16),
  top_family_all: "LOCKHEED MARTIN", family_count_all: 12, award_count_all: 40,
  hhi_high: 9800.2, hhi_high_fact_id: "c".repeat(16),
  program_dollars_high: 300_000_000, program_dollars_high_fact_id: "d".repeat(16),
  top_family_high: "BOEING", family_count_high: 2, award_count_high: 5,
};
const B: ProgramHHI = { ...A, hhi_high: null, hhi_high_fact_id: null, family_count_high: 1, award_count_high: 2 };
const C: ProgramHHI = { ...B, program_dollars_high: null, program_dollars_high_fact_id: null, top_family_high: null, family_count_high: 0, award_count_high: 0 };

describe("concentrationHeadline", () => {
  it("picks the high basis only when hhi_high publishes", () => {
    expect(concentrationHeadline(A).basis).toBe("high");
    expect(concentrationHeadline(B).basis).toBe("all");
    expect(concentrationHeadline(C).basis).toBe("all");
  });
  it("carries distinct measure tokens per basis", () => {
    expect(concentrationHeadline(A).hhiMeasure).toBe("hhi-high");
    expect(concentrationHeadline(A).dollarsMeasure).toBe("obligations-high");
    expect(concentrationHeadline(B).hhiMeasure).toBe("hhi");
    expect(concentrationHeadline(B).dollarsMeasure).toBe("obligations");
  });
  it("names the tiers honestly per shape", () => {
    expect(concentrationHeadline(A).chip).toBe("high-confidence links");
    expect(concentrationHeadline(B).chip).toBe("high- and medium-confidence links");
    expect(concentrationHeadline(C).chip).toBe("medium-confidence links only");
  });
});

describe("ProgramConcentration card", () => {
  it("renders nothing without a block", () => {
    const { container } = render(<ProgramConcentration hhi={null} />);
    expect(container.querySelector("[data-hhi-band]")).toBeNull();
  });

  it("shape A: high-only headline, one basis-stamped band, all-tier second line", () => {
    const { container } = render(<ProgramConcentration hhi={A} />);
    const bands = container.querySelectorAll("[data-hhi-band]");
    expect(bands.length).toBe(1);
    expect(bands[0].getAttribute("data-hhi-basis")).toBe("high");
    expect(bands[0].getAttribute("data-hhi-band")).toBe("Highly Concentrated");
    expect(container.querySelector("[data-concentration-tier-chip]")?.textContent).toBe("high-confidence links");
    const hhiHigh = container.querySelector('[data-amount][data-measure="hhi-high"]');
    expect(hhiHigh).toHaveAttribute("data-fact-id", "c".repeat(16));
    expect(hhiHigh?.textContent).toContain("9800");
    const hhiAll = container.querySelector('[data-amount][data-measure="hhi"]');
    expect(hhiAll).toHaveAttribute("data-fact-id", "a".repeat(16));
    expect(container.querySelector('[data-amount][data-measure="obligations-high"]')).toHaveAttribute("data-fact-id", "d".repeat(16));
    expect(container.querySelector('[data-amount][data-measure="obligations"]')).toHaveAttribute("data-fact-id", "b".repeat(16));
    const second = container.querySelector('[data-concentration-secondary="all"]');
    expect(second?.textContent).toContain("Including medium-confidence links");
    expect(second?.textContent).toContain("Moderately Concentrated");
    expect(container.textContent).toContain("BOEING");
  });

  it("shape B: all-tier headline, high links reported below the floor", () => {
    const { container } = render(<ProgramConcentration hhi={B} />);
    const bands = container.querySelectorAll("[data-hhi-band]");
    expect(bands.length).toBe(1);
    expect(bands[0].getAttribute("data-hhi-basis")).toBe("all");
    expect(container.querySelector('[data-amount][data-measure="hhi"]')?.textContent).toContain("2100");
    expect(container.querySelector('[data-amount][data-measure="hhi-high"]')).toBeNull();
    expect(container.querySelector("[data-concentration-tier-chip]")?.textContent).toBe("high- and medium-confidence links");
    const second = container.querySelector('[data-concentration-secondary="high"]');
    expect(second?.textContent).toContain("2 awards across 1 family");
    expect(second?.textContent).toContain("below the 3-award, 2-family floor");
    expect(second?.querySelector('[data-amount][data-measure="obligations-high"]')).toHaveAttribute("data-fact-id", "d".repeat(16));
  });

  it("shape C: no high link — says so, cites only all-tier figures", () => {
    const { container } = render(<ProgramConcentration hhi={C} />);
    expect(container.querySelector("[data-hhi-band]")?.getAttribute("data-hhi-basis")).toBe("all");
    expect(container.querySelector("[data-concentration-tier-chip]")?.textContent).toBe("medium-confidence links only");
    expect(container.querySelector('[data-concentration-secondary="none"]')?.textContent).toContain("No high-confidence link");
    expect(container.querySelectorAll('[data-amount][data-measure$="-high"]').length).toBe(0);
  });
});
