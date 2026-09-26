/**
 * R-DEC-132b (controller, 2026-09-26) — the /feed/ "Award Concentration
 * Shifts" section description names the bands, so it names their vintage.
 *
 * The stage-1 checker found it still reading "Each card names its DOJ/FTC
 * band: competitive, moderately concentrated or highly concentrated." after
 * #132 moved every other surface to the 2023 Merger Guidelines: no year, and
 * "competitive" presented as an agency band. The sentence is now built from
 * hhi-band.mjs's constants (never a hand copy of 1,000 / 1,800), uses the
 * badge's own word below 1,000 ("unconcentrated") and says that word is this
 * site's. scripts/gates/feed.mjs leg (l) reads the same paragraph off the
 * built page (hhiSectionDescriptionFinding).
 */
import React from "react";
import { afterEach, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import FeedPage from "@/app/feed/page";
import { HHI_BANDS_VINTAGE, HHI_CONCENTRATED_MIN, HHI_MODERATE_MIN } from "@/lib/hhi-band.mjs";
import { formatCount } from "@/lib/format";

afterEach(() => cleanup());

it("the concentration section's description names the 2023 bands and whose word the low band is", () => {
  const { container } = render(<FeedPage />);
  const section = container.querySelector("#feed-concentration_shift");
  expect(section, "no concentration_shift section rendered").not.toBeNull();
  const description = section!.querySelector("div > p")!.textContent ?? "";
  expect(description).toContain(
    `Each card names its band under the ${HHI_BANDS_VINTAGE}: moderately concentrated from ` +
      `${formatCount(HHI_MODERATE_MIN)} to ${formatCount(HHI_CONCENTRATED_MIN)} and highly concentrated ` +
      `above ${formatCount(HHI_CONCENTRATED_MIN)}.`,
  );
  expect(description).toContain(
    `Below ${formatCount(HHI_MODERATE_MIN)} the card says unconcentrated, this site's label for that range.`,
  );
  expect(description).not.toMatch(/DOJ\/FTC/);
  expect(description).not.toMatch(/competitive/i);
});
