/**
 * /methodology/'s precision paragraph states who counts in the held-out
 * figures (controller ruling R-DEC-LINK-2026-10-21-R2 on review 1, I-2;
 * narrowed on the round-2 review, I-1).
 *
 * "Each sampled link is counted under the tier it publishes under today …;
 * one the corpus no longer publishes is counted in neither direction" was
 * true until the 2026-10-21 line rulings. They withdrew four links the
 * precision study itself had refuted (0593|N0001917C0001 and
 * C04000|FA813423FB001 in announcement+lexicon; 0505|N0001909C0019 and
 * 0590|N0001912C2001 in fpds-ap), and those four keep counting as refuted,
 * by design: withdrawing a link must never raise the figure that caught it
 * (R-DEC-110b/110c, export_site._self_refuted_population).
 *
 * The exception is a refuted link a RULING withdrew, not every refuted link
 * that left the corpus. Round 2's "unless the study refuted it" was false
 * for three refuted announcement+lexicon links of the 2026-09-04 draw that
 * stopped publishing with no ruling (FA850419F0008|0401132F,
 * FA873018C0065|E00300, M6785417C9000|4630): they count in neither
 * direction, which tests/test_export_site_line_ruling_precision.py pins. So
 * the clause names the ruling, and this test holds it there.
 */
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import MethodologyPage from "@/app/methodology/page";

afterEach(cleanup);

describe("/methodology/ precision population", () => {
  it("says only a refuted link a ruling withdrew keeps counting after it stops publishing", () => {
    const { container } = render(<MethodologyPage />);
    const el = container.querySelector("[data-link-precision]");
    expect(el).not.toBeNull();
    const text = (el!.textContent ?? "").replace(/\s+/g, " ").trim();
    expect(text).toContain(
      "one the corpus no longer publishes is counted in neither direction, " +
        "except a refuted link a ruling withdrew:",
    );
    // The round-2 wording claimed every refuted link keeps counting.
    expect(text).not.toContain("unless the study refuted it");
  }, 30_000);
});
