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
 *
 * ROADMAP #82 added the SECOND withheld reason to this same vocabulary
 * (lib/concentration-basis.ts): "shared-code", where the mart's figure is
 * computed on a budget line more than one program uses and more than one of
 * them carries linked awards, so it is neither member's and the whole block
 * is withheld upstream — the card renders nothing at all there and the
 * answer strip's "none" tier is the only surface that can say why. The last
 * describe below pins that branch and its marker, [data-who-withheld].
 */
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import fs from "fs";
import path from "path";
import React from "react";
import { ProgramConcentration } from "@/components/program-concentration";
import {
  concentrationHeadline,
  CONCENTRATION_WITHHELD_REASON,
  sharedCodeWithheldReason,
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

  // R5 also ruled ONE shared string for the card and the strip. The card is
  // rendered above; the strip lives in a server component this suite cannot
  // render, so its branch is read as source: a future edit that hardcodes a
  // fresh sentence there instead of the shared constants — which is exactly
  // how both false sentences got written — fails here.
  it("the answer strip's withheld branch renders the shared strings, not its own", () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, "..", "app", "program", "[peBli]", "page.tsx"),
      "utf8",
    );
    const first = src.indexOf('data-who-tier="none"');
    const second = src.indexOf('data-who-tier="none"', first + 1);
    expect(first).toBeGreaterThan(-1);
    expect(second).toBeGreaterThan(first);
    const branch = src.slice(first, second);
    expect(branch).toContain("{WHO_GETS_IT_WITHHELD_LEAD}");
    expect(branch).toContain("{CONCENTRATION_WITHHELD_REASON}");
    expect(branch).not.toMatch(/no contractor is named/i);
    expect(branch).not.toMatch(/fewer than/i);
    // gate 21 leg (j): a non-award tier may state no dollars.
    expect(branch).not.toContain("data-amount");
    expect(branch).not.toMatch(/\$[\d{]/);
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

// ───────────────────────────────────────────────────────────────────────────
// ROADMAP #82 — the second withheld reason: a figure that is nobody's
// ───────────────────────────────────────────────────────────────────────────

describe("shared-code withholding (ROADMAP #82)", () => {
  it("states the rule, names the line, and counts nothing", () => {
    const s = sharedCodeWithheldReason("3010");
    expect(s).toContain("3010");
    // The two clauses the exporter guarantees (_concentration_withheld).
    expect(s).toMatch(/linked to this program/i);
    expect(s).toMatch(/more than one program/i);
    expect(s).toMatch(/more than one of them carries linked awards/i);
    // "two" is false on '30', which THREE programs share; a count of this
    // line's links is the sentence class #80 fix round 2 had to retract.
    expect(s).not.toMatch(/\btwo programs\b/i);
    expect(s).not.toMatch(/\bfewer than\b/i);
    expect(s).not.toMatch(/\$[\d]/);
  });

  // Task 28 fix round 2. The rule is on LINKS: the index is published only
  // when one program carries every link on the line. It is not a finding
  // that any figure mixes the programs' money, and in chain C run 2's export
  // (2026-09-19) none a page prints did: 0145-PANMC's three links are IDV
  // PIIDs whose transactions all carry obligation 0.0, so every 0145 figure
  // is 0145-APN's money, and on 3010 and 3215 every high link is one
  // member's. The fix-round-1 clause "a figure over all the line's links
  // would mix their money" was false on /program/0145-APN/ and
  // /program/0145-PANMC/, so the sentence states the rule and nothing more.
  it("states the rule on links — and claims no mixing of money", () => {
    const s = sharedCodeWithheldReason("0145");
    expect(s).toMatch(
      /; the index is published only when one program carries every link on the line\.$/,
    );
    expect(s).not.toMatch(/\bmix/i);
    expect(s).not.toMatch(/\bmoney\b/i);
    expect(s).not.toMatch(/\bfuse/i);
  });

  it("does not deny that any company is linked — award records are", () => {
    // The pre-#82 sentence on these pages was "No company is linked to this
    // line. Award records do not carry the program element, so the crosswalk
    // is silent here", rendered above a five-row Related Awards table.
    const s = sharedCodeWithheldReason("3010");
    expect(s).not.toMatch(/no company is linked/i);
    expect(s).not.toMatch(/crosswalk is silent/i);
  });

  // Same technique as the strip test above: the branch is a server component
  // this suite cannot render, so it is read as source. Slice from the SECOND
  // data-who-tier="none" (the #82 branch) to the THIRD (the plain absence).
  it("the answer strip's shared-code branch renders the shared strings and the marker", () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, "..", "app", "program", "[peBli]", "page.tsx"),
      "utf8",
    );
    const first = src.indexOf('data-who-tier="none"');
    const second = src.indexOf('data-who-tier="none"', first + 1);
    const third = src.indexOf('data-who-tier="none"', second + 1);
    expect(third).toBeGreaterThan(second);
    const branch = src.slice(second, third);
    expect(branch).toContain('data-who-withheld="shared-code"');
    expect(branch).toContain("{WHO_GETS_IT_WITHHELD_LEAD}");
    expect(branch).toContain("{sharedCodeWithheldReason(peBli)}");
    // gate 21 leg (j): a non-award tier may state no dollars and name nobody.
    expect(branch).not.toContain("data-amount");
    expect(branch).not.toContain("data-who-name");
    expect(branch).not.toMatch(/\$[\d{]/);
  });

  it("only the shared-code branch stamps the marker — leg n check 7 reads it", () => {
    // The below-floor branch (#80) is withheld too, but for the OTHER reason,
    // and ~400 pages render it with no summary.concentration_withheld behind
    // them. If it stamped the marker, gate 21 leg n check 7's
    // renderer-without-payload half would fire on every shared-code member
    // that is merely below the floor.
    const src = fs.readFileSync(
      path.resolve(__dirname, "..", "app", "program", "[peBli]", "page.tsx"),
      "utf8",
    );
    expect(src.match(/data-who-withheld=/g) ?? []).toHaveLength(1);
  });
});
