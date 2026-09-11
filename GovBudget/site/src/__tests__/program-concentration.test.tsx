/**
 * ROADMAP #80 (fix round 1, 2026-09-11) — the Contractor Concentration card
 * publishes ONE basis: high-confidence links only, or nothing.
 *
 * Both bases are computed and both ship in the downloadable mart and in
 * citations. Only the high-confidence-only figures are rendered: the
 * all-links figures are dominated by the account+subagency tier, which the
 * 2026-09-04 adjudication measured at 0 of 60 for program attribution
 * (ROADMAP #79), and "publish the smaller true number" (owner decision
 * 2026-08-07) says shrink the claim rather than substitute a wider one.
 *
 * DOM contract (read by scripts/gates/feed.mjs leg l and gate 23 leg a2):
 *   PUBLISHED (hhi_high non-null)
 *     - exactly ONE [data-hhi-band], stamped data-hhi-basis="high"
 *     - measures "hhi-high" / "obligations-high" — never "hhi"/"obligations",
 *       which would put two different figures in one (entity, fy, measure)
 *       group for leg a2 if an all-links figure ever came back
 *   WITHHELD (hhi_high null)
 *     - [data-concentration-withheld="below-floor"] and a sentence saying why
 *     - NO [data-hhi-band], NO [data-amount], NO [data-measure], no tier
 *       chip, no top family, no family count — nothing for a reader to
 *       mistake for a published figure
 */
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import { ProgramConcentration } from "@/components/program-concentration";
import {
  concentrationHeadline,
  CONCENTRATION_WITHHELD_REASON,
  WHO_GETS_IT_WITHHELD_LEAD,
} from "@/lib/concentration-basis";
import type { ProgramHHI } from "@/lib/data";

// hhi_all 2100.4 → "Moderately Concentrated" (1,500–2,500); hhi_high 9800.2 →
// "Highly Concentrated". The two bands differ on purpose: if an all-links
// figure ever leaked back onto the card, the band assertions would catch it.
const A: ProgramHHI = {
  hhi_all: 2100.4, hhi_all_fact_id: "a".repeat(16),
  program_dollars_all: 500_000_000, program_dollars_all_fact_id: "b".repeat(16),
  top_family_all: "LOCKHEED MARTIN", family_count_all: 12, award_count_all: 40,
  hhi_high: 9800.2, hhi_high_fact_id: "c".repeat(16),
  program_dollars_high: 300_000_000, program_dollars_high_fact_id: "d".repeat(16),
  top_family_high: "BOEING", family_count_high: 2, award_count_high: 5,
};
// B — high links exist but fall below the floor. The mart NULLs top_family_high
// with hhi_high (fix round 1): with no positive-dollar leader the tie-break
// picks alphabetically.
const B: ProgramHHI = {
  ...A, hhi_high: null, hhi_high_fact_id: null, top_family_high: null,
  family_count_high: 1, award_count_high: 2,
};
// C — no high link at all.
const C: ProgramHHI = {
  ...B, program_dollars_high: null, program_dollars_high_fact_id: null,
  family_count_high: 0, award_count_high: 0,
};

describe("concentrationHeadline", () => {
  it("publishes only the high basis, and only when the index publishes", () => {
    const a = concentrationHeadline(A);
    expect(a.published).toBe(true);
    if (!a.published) throw new Error("unreachable");
    expect(a.basis).toBe("high");
    expect(a.hhi).toBe(9800.2);
    expect(a.program_dollars).toBe(300_000_000);
    expect(a.top_family).toBe("BOEING");
    expect(a.hhiMeasure).toBe("hhi-high");
    expect(a.dollarsMeasure).toBe("obligations-high");
  });

  it("withholds rather than substituting the all-links figure", () => {
    for (const shape of [B, C]) {
      const h = concentrationHeadline(shape);
      expect(h.published).toBe(false);
      if (h.published) throw new Error("unreachable");
      expect(h.withheld).toBe("below-floor");
      // No path out of the withheld state carries an all-links value.
      expect(JSON.stringify(h)).not.toContain("2100.4");
      expect(JSON.stringify(h)).not.toContain("LOCKHEED");
    }
  });
});

describe("ProgramConcentration card", () => {
  it("renders nothing without a block", () => {
    const { container } = render(<ProgramConcentration hhi={null} />);
    expect(container.querySelector("[data-hhi-band]")).toBeNull();
    expect(container.querySelector("[data-concentration-withheld]")).toBeNull();
    expect(container.textContent).toBe("");
  });

  it("published: one basis-stamped band, high-only measures, no second line", () => {
    const { container } = render(<ProgramConcentration hhi={A} />);
    const bands = container.querySelectorAll("[data-hhi-band]");
    expect(bands.length).toBe(1);
    expect(bands[0].getAttribute("data-hhi-basis")).toBe("high");
    expect(bands[0].getAttribute("data-hhi-band")).toBe("Highly Concentrated");
    const hhiHigh = container.querySelector('[data-amount][data-measure="hhi-high"]');
    expect(hhiHigh).toHaveAttribute("data-fact-id", "c".repeat(16));
    expect(hhiHigh?.textContent).toContain("9800");
    expect(
      container.querySelector('[data-amount][data-measure="obligations-high"]'),
    ).toHaveAttribute("data-fact-id", "d".repeat(16));
    expect(container.textContent).toContain("BOEING");
    expect(container.querySelector("[data-concentration-withheld]")).toBeNull();
  });

  it("withheld: the reason, the marker, and not one figure", () => {
    for (const [name, shape] of [["below floor", B], ["no high link", C]] as const) {
      const { container } = render(<ProgramConcentration hhi={shape} />);
      const note = container.querySelector('[data-concentration-withheld="below-floor"]');
      expect(note, name).not.toBeNull();
      expect(note?.textContent, name).toMatch(/high-confidence/i);
      expect(note?.textContent, name).toMatch(/no concentration (index|figure)/i);
      expect(container.querySelectorAll("[data-hhi-band]").length, name).toBe(0);
      expect(container.querySelectorAll("[data-amount]").length, name).toBe(0);
      expect(container.querySelectorAll("[data-measure]").length, name).toBe(0);
      expect(container.querySelector("[data-concentration-tier-chip]"), name).toBeNull();
      // The all-links top family and counts must not appear anywhere.
      expect(container.textContent, name).not.toContain("LOCKHEED");
      expect(container.textContent, name).not.toContain("2100");
      expect(container.textContent, name).not.toContain("Moderately Concentrated");
    }
  });

  it("never renders an all-links figure or a second line, on any shape", () => {
    for (const shape of [A, B, C]) {
      const { container } = render(<ProgramConcentration hhi={shape} />);
      expect(container.querySelector('[data-measure="hhi"]')).toBeNull();
      expect(container.querySelector('[data-measure="obligations"]')).toBeNull();
      expect(container.querySelector("[data-concentration-secondary]")).toBeNull();
      expect(container.querySelector("[data-concentration-tier-chip]")).toBeNull();
      expect(container.textContent).not.toContain("Including medium-confidence links");
      expect(container.textContent).not.toContain(
        "an account or agency association",
      );
    }
  });
});

/**
 * ROADMAP #80 fix round 2 (2026-09-11), findings 1 and 3 — ruling R5.
 *
 * The withheld sentences must state the RULE, never a fact about this line
 * that may be false. Measured on the live lake at the post-fix floor: 282
 * programs carry at least one high-confidence link and 37 clear the floor,
 * so 245 pages withhold WITH high-confidence links on the page — 44 of them
 * publish 3 or more, and 245 name high-confidence contractors in their own
 * Related Awards table lower down. "Fewer than 3 high-confidence award
 * links … are published for this line" was false on those 44; "No
 * contractor is named for this line at high confidence" was false on all
 * 245. The floor also has a third clause (positive net linked dollars) the
 * old sentence never mentioned — 356010's high links net −$2,328,281.
 *
 * These assertions are the gate on that class of sentence: they fail if
 * either string goes back to counting this line's links or to asserting
 * that nobody is named.
 */
describe("the withheld sentences state the floor, not a count about this line", () => {
  it("the shared reason names all three clauses of the floor", () => {
    expect(CONCENTRATION_WITHHELD_REASON).toContain("do not clear the floor");
    expect(CONCENTRATION_WITHHELD_REASON).toContain("3 awards");
    expect(CONCENTRATION_WITHHELD_REASON).toContain("2 contractor families");
    expect(CONCENTRATION_WITHHELD_REASON).toContain("positive obligations");
    expect(CONCENTRATION_WITHHELD_REASON).toContain("positive net linked dollars");
  });

  it("the shared reason claims no count and no absence of names", () => {
    expect(CONCENTRATION_WITHHELD_REASON).not.toMatch(/fewer than/i);
    expect(CONCENTRATION_WITHHELD_REASON).not.toMatch(/no contractor is named/i);
    expect(CONCENTRATION_WITHHELD_REASON).not.toMatch(/no .{0,20}link/i);
  });

  it("the answer-strip lead withholds a leader, it does not deny the names", () => {
    expect(WHO_GETS_IT_WITHHELD_LEAD).not.toMatch(/no contractor is named/i);
    expect(WHO_GETS_IT_WITHHELD_LEAD).not.toMatch(/fewer than/i);
    expect(WHO_GETS_IT_WITHHELD_LEAD).toMatch(/leader/i);
  });

  it("the card renders the rule, on both withheld shapes", () => {
    for (const [name, shape] of [["below floor", B], ["no high link", C]] as const) {
      const { container } = render(<ProgramConcentration hhi={shape} />);
      const note = container.querySelector('[data-concentration-withheld="below-floor"]');
      expect(note?.textContent, name).toContain(CONCENTRATION_WITHHELD_REASON);
      expect(note?.textContent, name).not.toMatch(/fewer than/i);
    }
  });
});
