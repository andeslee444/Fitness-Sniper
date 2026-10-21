/**
 * /methodology/'s precision paragraph states who counts in the held-out
 * figures (controller ruling R-DEC-LINK-2026-10-21-R2 on review 1, I-2).
 *
 * "Each sampled link is counted under the tier it publishes under today …;
 * one the corpus no longer publishes is counted in neither direction" was
 * true until the 2026-10-21 line rulings. They withdrew four links the
 * precision study itself had refuted (0593|N0001917C0001 and
 * C04000|FA813423FB001 in announcement+lexicon; 0505|N0001909C0019 and
 * 0590|N0001912C2001 in fpds-ap), and those four keep counting as refuted,
 * by design: withdrawing a link must never raise the figure that caught it
 * (R-DEC-110b/110c, export_site._self_refuted_population). So the clause
 * names its exception, in the shortest true wording, and this test holds it
 * there.
 */
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import MethodologyPage from "@/app/methodology/page";

afterEach(cleanup);

describe("/methodology/ precision population", () => {
  it("says a link the study refuted keeps counting after it stops publishing", () => {
    const { container } = render(<MethodologyPage />);
    const el = container.querySelector("[data-link-precision]");
    expect(el).not.toBeNull();
    const text = (el!.textContent ?? "").replace(/\s+/g, " ").trim();
    expect(text).toContain(
      "one the corpus no longer publishes is counted in neither direction " +
        "unless the study refuted it:",
    );
  }, 30_000);
});
