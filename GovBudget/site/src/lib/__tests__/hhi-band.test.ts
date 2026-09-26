/**
 * hhi-band — backlog #57. The single source for the concentration bands
 * rendered on /program/{peBli}/ (program-concentration.tsx), in
 * /methodology/ (page.tsx:22 imports both boundary constants) and on /feed/'s
 * hhi cards (lib/hhi-scope-note.ts's hhiScopeNote, via feed-card-item-shell.tsx)
 * — and read by scripts/gates/feed.mjs leg (l) and scripts/gates/coverage.mjs.
 * Pinning the boundaries here is what keeps the pages and the gates from
 * silently drifting apart the way BASIS_LABEL once did (backlog #48).
 *
 * #132 (decided 2026-09-25, owner delegated to the controller's
 * recommendation): the bands are the agencies' CURRENT thresholds, as the DOJ
 * Antitrust Division's HHI page states them (updated 2024-01-17), citing U.S.
 * DOJ & FTC, Merger Guidelines § 2.1 (2023): "between 1,000 and 1,800 points"
 * is moderately concentrated, "in excess of 1,800 points" highly
 * concentrated. Until then this module carried the 2010 Horizontal Merger
 * Guidelines' 1,500 / 2,500 and the site called them "DOJ/FTC bands" with no
 * year. Every surface that names the bands now names the vintage too.
 *
 * The GLOSSARY entry is built from this module's constants (it used to be a
 * hand copy that wrote 1,500 and 2,500 out as prose); the last describe block
 * holds it to them anyway, and to the vintage.
 *
 * The homepage was listed here until 2026-09-18; src/app/page.tsx imports
 * neither hhiBand nor either boundary constant, and never did.
 */

import { describe, it, expect } from "vitest";
import {
  hhiBand,
  hhiBandVintageLine,
  HHI_MODERATE_MIN,
  HHI_CONCENTRATED_MIN,
  HHI_BANDS_VINTAGE,
  HHI_BANDS_SOURCE_URL,
} from "../hhi-band.mjs";
import { GLOSSARY } from "../glossary";
import { formatCount } from "../format";

describe("hhiBand — the 2023 Merger Guidelines thresholds (#132)", () => {
  it("carries the agencies' current thresholds and names their vintage", () => {
    expect(HHI_MODERATE_MIN).toBe(1000);
    expect(HHI_CONCENTRATED_MIN).toBe(1800);
    expect(HHI_BANDS_VINTAGE).toBe("2023 Merger Guidelines");
    expect(HHI_BANDS_SOURCE_URL).toBe("https://www.justice.gov/atr/herfindahl-hirschman-index");
  });

  // R-DEC-132b (controller, 2026-09-26): below 1,000 the badge says
  // "Unconcentrated" — the agencies' historical term for that range; the
  // 2023 page names no band there, so the label is attributed to the site
  // wherever the bands are stated. It replaced the editorial "Competitive".
  it("labels values below 1,000 Unconcentrated", () => {
    expect(hhiBand(0).label).toBe("Unconcentrated");
    expect(hhiBand(505.5).label).toBe("Unconcentrated");
    expect(hhiBand(999).label).toBe("Unconcentrated");
    expect(hhiBand(999.49).label).toBe("Unconcentrated");
  });

  it("never renders the retired editorial label", () => {
    for (const v of [0, 389.23, 999.49, 1000, 1800, 1801, 10000]) {
      expect(hhiBand(v).label, String(v)).not.toMatch(/competitive/i);
      expect(hhiBand(v).key, String(v)).not.toMatch(/competitive/i);
    }
  });

  it("labels 1,000 through 1,800 — both ends — Moderately Concentrated", () => {
    // "between 1,000 and 1,800 points": 1,000 is in the band, and so is
    // 1,800 — only an index IN EXCESS of 1,800 is highly concentrated.
    expect(hhiBand(1000).label).toBe("Moderately Concentrated");
    expect(hhiBand(1400.4).label).toBe("Moderately Concentrated");
    expect(hhiBand(1500).label).toBe("Moderately Concentrated");
    expect(hhiBand(1800).label).toBe("Moderately Concentrated");
  });

  it("labels anything in excess of 1,800 Highly Concentrated", () => {
    expect(hhiBand(1801).label).toBe("Highly Concentrated");
    expect(hhiBand(1913.41).label).toBe("Highly Concentrated");
    // The 2010 guidelines' moderate band: now highly concentrated.
    expect(hhiBand(2000).label).toBe("Highly Concentrated");
    expect(hhiBand(2499.99).label).toBe("Highly Concentrated");
    expect(hhiBand(2500).label).toBe("Highly Concentrated");
    expect(hhiBand(9715.83).label).toBe("Highly Concentrated");
    expect(hhiBand(10000).label).toBe("Highly Concentrated");
  });

  it("bands the index at the whole-point precision every surface prints it", () => {
    // The badge, the feed card and the headline print HHI as a whole number
    // (toFixed(0)); feed leg (l) re-bands the number it reads off the card.
    // An index of 1,800.4 prints "1800", so calling it Highly Concentrated
    // would put a band beside a printed number the band's own definition
    // excludes. Ten equal-share families give exactly 1,000 on paper, and a
    // sum of floating-point squares can land a hair either side of it.
    expect(hhiBand(1800.4).label).toBe("Moderately Concentrated");
    expect(hhiBand(1800.5).label).toBe("Highly Concentrated");
    expect(hhiBand(999.5).label).toBe("Moderately Concentrated");
    expect(hhiBand(999.9999999999999).label).toBe("Moderately Concentrated");
    expect(hhiBand(1800.0000000000002).label).toBe("Moderately Concentrated");
  });

  it("agrees with the band of the number it prints, across both boundaries", () => {
    for (let v = 990; v <= 1010; v += 0.05) {
      expect(hhiBand(v).label, String(v)).toBe(hhiBand(Number(v.toFixed(0))).label);
    }
    for (let v = 1790; v <= 1810; v += 0.05) {
      expect(hhiBand(v).label, String(v)).toBe(hhiBand(Number(v.toFixed(0))).label);
    }
  });

  // The key is internal: program-concentration.tsx colours the badge by it
  // and nothing else reads it — no export, sidecar, data-* attribute or gate
  // (the gates and the DOM carry the LABEL). So R-DEC-132b renamed it with
  // the label rather than keep an editorial word in the code.
  it("carries a stable machine-readable key alongside the label", () => {
    expect(hhiBand(100).key).toBe("unconcentrated");
    expect(hhiBand(1500).key).toBe("moderate");
    expect(hhiBand(5000).key).toBe("concentrated");
  });
});

/**
 * R-DEC-132b (controller, 2026-09-26): the vintage is VISIBLE text beside the
 * program badge, not only the Index tooltip's hover title (which a phone
 * cannot reach). hhiBandVintageLine is that text — one function for the badge
 * (program-concentration.tsx) and for the gate that reads it back
 * (scripts/gates/coverage.mjs). The guidelines name no band below 1,000, so an
 * Unconcentrated badge says it sits BELOW their bands rather than implying
 * the 2023 guidelines use the word.
 */
describe("hhiBandVintageLine — the badge's visible vintage", () => {
  it("names the 2023 Merger Guidelines under a band they define", () => {
    expect(hhiBandVintageLine(1000)).toBe(`${HHI_BANDS_VINTAGE} bands`);
    expect(hhiBandVintageLine(1800)).toBe("2023 Merger Guidelines bands");
    expect(hhiBandVintageLine(2444.43)).toBe("2023 Merger Guidelines bands");
  });

  it("says an Unconcentrated index sits below those bands", () => {
    expect(hhiBandVintageLine(389.23)).toBe("Below the 2023 Merger Guidelines bands");
    expect(hhiBandVintageLine(999.49)).toBe("Below the 2023 Merger Guidelines bands");
  });

  it("follows the whole-point banding hhiBand applies", () => {
    for (const v of [999.4, 999.5, 1800.4, 1800.5]) {
      const below = hhiBand(v).key === "unconcentrated";
      expect(hhiBandVintageLine(v).startsWith("Below"), String(v)).toBe(below);
    }
  });
});

describe("the glossary's statement of the bands", () => {
  const hhi = GLOSSARY.find((e) => e.id === "hhi");
  const definition = hhi?.definition ?? "";

  it("states the boundaries this module defines, and their vintage", () => {
    expect(hhi, "GLOSSARY has no 'hhi' entry").toBeDefined();
    expect(definition).toContain(formatCount(HHI_MODERATE_MIN));
    expect(definition).toContain(formatCount(HHI_CONCENTRATED_MIN));
    expect(definition).toContain(HHI_BANDS_VINTAGE);
    // The boundary words hhiBand applies: 1,800 is moderate, so the high band
    // starts "above" it, never "at" it.
    expect(definition).toContain(`above ${formatCount(HHI_CONCENTRATED_MIN)}`);
    expect(definition).not.toMatch(/1,800 or (above|more)/);
  });

  it("no longer states the retired 2010 bands, or calls them the DOJ/FTC bands without a year", () => {
    expect(definition).not.toMatch(/1,500|2,500/);
    expect(definition).not.toMatch(/Horizontal Merger Guidelines/);
  });

  // R-DEC-132b: the range below 1,000 carries the badge's own word, and the
  // sentence attributes it to this site, not to the agencies.
  it("calls the range below 1,000 unconcentrated, as this site's label", () => {
    expect(definition).toContain(`This site calls an HHI below ${formatCount(HHI_MODERATE_MIN)} unconcentrated.`);
    expect(definition).not.toMatch(/competitive/i);
  });
});
