/**
 * hhi-scope-note — backlog #57's per-card "one year, not the pooled figure"
 * disclosure, moved out of components/feed-headline.tsx by ROADMAP #81 so
 * the /feed/ client tree can call the SAME function instead of a hand-copied
 * twin. The cases below are the ones feed-headline.test.tsx carried until
 * #81 — including #80 fix round 2's "does not promise the destination
 * publishes a pooled figure" — unchanged.
 */

import { describe, it, expect } from "vitest";

import { hhiScopeNote } from "@/lib/hhi-scope-note";
import type { FeedCard } from "@/lib/data";

function card(over: Partial<FeedCard> = {}): FeedCard {
  return {
    event_type: "new_entrant",
    family_key: "ACME CORP",
    figure_fact_id: "f".repeat(16),
    figure_units: "dollars",
    figure_value: 3_100_000,
    fiscal_year: 2025,
    headline: "ACME CORP new defense contractor (first award FY2025, $3.1M total)",
    headline_segments: [
      { text: "ACME CORP new defense contractor (first award FY2025, " },
      { amount: "$3.1M", fact_id: "f".repeat(16) },
      { text: " total)" },
    ],
    organization: null,
    pe_bli: null,
    program_url: null,
    title: null,
    why_url: "/methodology/#feed-new_entrant",
    basis: null,
    fy: null,
    measure: null,
    edition: null,
    magnitude: null,
    ...over,
  };
}

describe("hhiScopeNote", () => {
  it("returns null for a non-hhi card", () => {
    expect(hhiScopeNote(card())).toBeNull();
  });

  it("returns null when the hhi card carries no figure_value", () => {
    expect(
      hhiScopeNote(
        card({ event_type: "concentration_shift", figure_units: "hhi", figure_value: null }),
      ),
    ).toBeNull();
  });

  // backlog #57: the destination /program/0601101E/ page renders a pooled
  // all-years HHI of 505.5 ("Unconcentrated" since R-DEC-132b; "Competitive"
  // then) for the same program — a
  // DIFFERENT measure this note exists to disclose, not to match.
  it("names the standard band and the fiscal year, and discloses the pooled figure can differ", () => {
    const note = hhiScopeNote(
      card({
        event_type: "concentration_shift",
        figure_units: "hhi",
        figure_value: 8662.294,
        fiscal_year: 2020,
        pe_bli: "0601101E",
        program_url: "/program/0601101E/",
      }),
    );
    expect(note).not.toBeNull();
    expect(note!.band).toBe("Highly Concentrated");
    expect(note!.text).toContain("FY2020");
    expect(note!.text).toContain("Highly Concentrated");
    expect(note!.text.toLowerCase()).toContain("pooled");
    expect(note!.text.toLowerCase()).toContain("differ");
  });

  it("uses the standard vocabulary, not an editorial adjective, below the highly-concentrated floor", () => {
    // The old two-way split called ANYTHING under 2500 "a high supplier-
    // concentration score" — false for a genuinely unconcentrated value.
    const note = hhiScopeNote(
      card({
        event_type: "concentration_shift",
        figure_units: "hhi",
        figure_value: 800,
        fiscal_year: 2022,
      }),
    );
    expect(note!.band).toBe("Unconcentrated");
    expect(note!.text).not.toMatch(/near-monopoly/i);
    expect(note!.text).not.toMatch(/high supplier-concentration/i);
    expect(note!.text).not.toMatch(/competitive/i);
  });

  // R-DEC-132b (controller, 2026-09-26): "Unconcentrated" is this site's word
  // for the range below 1,000 — the 2023 guidelines name no band there — so
  // the note says the figure sits BELOW their bands instead of implying the
  // guidelines call it that. Same phrase as the program badge's visible
  // vintage line (hhiBandVintageLine), still naming the vintage feed leg (l)
  // requires.
  it("places an unconcentrated year below the 2023 bands, not inside them", () => {
    const note = hhiScopeNote(
      card({ event_type: "concentration_shift", figure_units: "hhi", figure_value: 891.8, fiscal_year: 2020 }),
    )!;
    expect(note.text).toContain("Unconcentrated in FY2020 (below the 2023 Merger Guidelines bands)");
    const high = hhiScopeNote(
      card({ event_type: "concentration_shift", figure_units: "hhi", figure_value: 4401, fiscal_year: 2020 }),
    )!;
    expect(high.text).toContain("Highly Concentrated in FY2020 (2023 Merger Guidelines bands)");
  });

  // ROADMAP #80 fix round 2 (2026-09-11), finding 8 — ruling R8. The note
  // used to end "the program's pooled, all-years HHI can differ; see the
  // program page", written when the destination always had one. After the
  // high-only floor, 444 - 37 = 407 of the 444 mart rows publish no pooled
  // index at all, so that instruction sent most readers to a page that
  // states an absence. The note must say the figure may not be there —
  // while keeping the "pooled"/"differ" tokens scripts/gates/feed.mjs leg
  // (l) matches on. This assertion fails if either half is dropped.
  it("does not promise the destination publishes a pooled figure", () => {
    const note = hhiScopeNote(
      card({
        event_type: "concentration_shift",
        figure_units: "hhi",
        figure_value: 8662.294,
        fiscal_year: 2020,
        pe_bli: "0601101E",
        program_url: "/program/0601101E/",
      }),
    );
    expect(note!.text).toMatch(/not be published/i);
    expect(note!.text.toLowerCase()).toContain("pooled");
    expect(note!.text.toLowerCase()).toContain("differ");
  });

  // #132 (decided 2026-09-25): the note names the band's vintage, because a
  // band without a year is exactly what let the site call the 2010 bands
  // "DOJ/FTC bands" after the agencies had replaced them.
  it("names the vintage of the bands it applies", () => {
    const note = hhiScopeNote(
      card({
        event_type: "concentration_shift",
        figure_units: "hhi",
        figure_value: 8662.294,
        fiscal_year: 2020,
      }),
    );
    expect(note!.text).toContain("2023 Merger Guidelines");
    expect(note!.text).not.toMatch(/DOJ\/FTC|Horizontal Merger/);
  });

  // #132 measured 2026-09-25 on the shipped export: three concentration_shift
  // cards sit between 1,800 and 2,500 — 0605625A FY2021 (2,000.0) and FY2022
  // (2,060.3), 0602715E FY2019 (2,148.7). Moderately concentrated under the
  // retired 2010 bands, highly concentrated under 2023's.
  it("calls a year above 1,800 highly concentrated, and 1,800 itself moderate", () => {
    const at = (figure_value: number) =>
      hhiScopeNote(
        card({ event_type: "concentration_shift", figure_units: "hhi", figure_value, fiscal_year: 2021 }),
      )!;
    expect(at(2000).band).toBe("Highly Concentrated");
    expect(at(2000).text).toContain("Highly Concentrated in FY2021");
    expect(at(1800).band).toBe("Moderately Concentrated");
    expect(at(1000).band).toBe("Moderately Concentrated");
    expect(at(999).band).toBe("Unconcentrated");
  });

  it("falls back to 'that year' when fiscal_year is absent", () => {
    const note = hhiScopeNote(
      card({
        event_type: "concentration_shift",
        figure_units: "hhi",
        figure_value: 3000,
        fiscal_year: null,
      }),
    );
    expect(note!.text).toContain("that year");
  });
});
