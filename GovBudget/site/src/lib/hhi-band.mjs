/**
 * hhi-band.mjs — Herfindahl-Hirschman Index concentration bands (2023 Merger
 * Guidelines thresholds, #132).
 *
 * SINGLE SOURCE for the three-way band vocabulary rendered by:
 *   - src/components/program-concentration.tsx  (the /program/{peBli}/
 *     "Contractor Concentration" badge — the destination page a homepage/
 *     feed concentration claim links to)
 *   - src/lib/hhi-scope-note.ts                  (per-card scope note,
 *     rendered on /feed/'s hhi-unit (concentration_shift) cards by
 *     feed-card-item-shell.tsx — hhiScopeNote returns null otherwise)
 *   - src/app/methodology/page.tsx               (imports the two band
 *     constants for §4's concentration passage)
 *   - scripts/gates/feed.mjs                     (leg l: claim vs. the
 *     destination page it links to, and each card's note vs. its own
 *     printed figure; leg q: every band claim in the prose of /methodology/,
 *     /glossary/ and /feed/ vs. hhiBand itself)
 *   - scripts/gates/coverage.mjs                 (the program badge vs. the
 *     shipped hhi_high)
 *
 * ONE MIRROR outside the site: src/govbudget/hhi_band.py (repo root), the
 * Python copy the dossier exporter and gate band a dossier claim's cited HHI
 * with (R-DEC-DOSSIERDRIFT, 2026-09-26 — a claim whose concentration word is
 * not its cited HHI's band is withheld). tests/test_hhi_band_parity.py binds
 * the two: it reads HHI_MODERATE_MIN, HHI_CONCENTRATED_MIN and
 * HHI_BANDS_VINTAGE out of THIS source and runs hhiBand under node over a
 * boundary sweep against the Python answer. No site gate runs it, so after
 * changing a threshold or the vintage here run
 * `PYTHONPATH=src uv run --no-sync python -m pytest -q tests/test_hhi_band_parity.py`
 * (chain G's runbook step 13 does).
 *
 * Plain .mjs, not .ts, ON PURPOSE. scripts/gates/*.mjs run under plain Node
 * and cannot import .ts modules — see src/lib/format.ts's COMPACT_RUNGS
 * comment, which hand-mirrors a constant into feed-model.mjs for exactly
 * this reason and leans on a vitest parity sweep to catch drift between the
 * two copies. Backlog #48 hit the same failure mode from the other
 * direction: BASIS_LABEL was mirrored between src/lib/basis.ts and
 * scripts/gates/basis.mjs, and the site copy went stale while the gate copy
 * (correctly) moved on. Making the HHI band function .mjs from the start
 * means every consumer — TS pages via `import ... from "@/lib/hhi-band.mjs"`
 * (the site already does this for feed-model.mjs) and the gate script via a
 * plain relative import — share the literal same function. What is left is
 * the prose that states the bands: glossary.ts's HHI entry and the
 * program-page tooltip (program-concentration.tsx) both build their text
 * from these constants and HHI_BANDS_VINTAGE (hhi-band.test.ts and
 * program-concentration.test.tsx hold them to it). /methodology/ §4 also
 * interpolates the two thresholds into its own sentence — which, at
 * e6bc28bb, still read "1,800 or above is highly concentrated" around them;
 * feed.mjs leg (q) and src/__tests__/methodology-hhi-band-prose.test.tsx now
 * read that prose back.
 *
 * BANDS (#132, decided 2026-09-25, owner delegated to the controller's
 * recommendation). The agencies' CURRENT thresholds, as the DOJ Antitrust
 * Division states them (https://www.justice.gov/atr/herfindahl-hirschman-index,
 * updated 2024-01-17), citing U.S. DOJ & FTC, Merger Guidelines § 2.1 (2023):
 * markets "between 1,000 and 1,800 points" are moderately concentrated, and
 * markets "in excess of 1,800 points" highly concentrated. In whole points:
 *
 *   HHI <  1,000               "Unconcentrated" — this site's label; the
 *                              agencies' page names no band below 1,000
 *   1,000 <= HHI <= 1,800      moderately concentrated — "between": BOTH ends
 *   HHI >  1,800               highly concentrated — "in excess of": 1,800
 *                              itself is moderately concentrated
 *
 * Until 2026-09-25 this module carried the 2010 Horizontal Merger
 * Guidelines' bands (1,500 and 2,500) and the site called them "DOJ/FTC
 * bands" with no year, after the agencies had replaced them. Every surface
 * that names a band now names its vintage, HHI_BANDS_VINTAGE: the program
 * badge's VISIBLE vintage line (hhiBandVintageLine below, rendered by
 * program-concentration.tsx and read back by scripts/gates/coverage.mjs) and
 * its Index tooltip, the glossary entry (built from these constants), the
 * /feed/ section description and each card's scope note (hhi-scope-note.ts)
 * — the last two held by scripts/gates/feed.mjs leg (l). Measured 2026-09-25
 * on the shipped export: 3 of feed.json's 1,606 concentration_shift cards and
 * 4 of the 61 programs publishing a high-confidence band moved from
 * moderately to highly concentrated; no card or program sits between 1,000
 * and 1,500, so none moved from the lowest band to moderate.
 *
 * "UNCONCENTRATED" BELOW 1,000 (R-DEC-132b, controller, 2026-09-26, under the
 * owner's 2026-09-25 delegation). The label there was "Competitive" — an
 * editorial word about a market, which an index of award shares does not
 * establish. It is now "Unconcentrated", the agencies' historical term for
 * that range; the 2023 page names no band there, so every surface that
 * states the bands attributes the word to this site ("this site says
 * unconcentrated"), and the visible vintage line under such a badge reads
 * "Below the 2023 Merger Guidelines bands" instead of implying the 2023
 * guidelines use the word. The machine key moved with it ("competitive" →
 * "unconcentrated"): it is internal — program-concentration.tsx colours the
 * badge by it — and no export, sidecar, data-* attribute or gate reads it
 * (the DOM and the gates carry the LABEL), so renaming broke no contract.
 * Measured 2026-09-25: 1 program badge (0605502E, 389.23) and 4 feed cards
 * (0605502E FY2017–FY2020, 436.9–891.8, all in the section sidecar, none
 * statically rendered) carry it.
 *
 * HHI_CONCENTRATED_MIN KEEPS ITS NAME, NOT ITS OLD MEANING. It is the
 * highly-concentrated THRESHOLD: a band member must EXCEED it. The name
 * predates the 2023 bands (under which 1,800 is a moderate value) and is
 * kept so every importer keeps compiling; read it as "the line above which".
 * HHI_MODERATE_MIN is an inclusive floor, as its name says.
 *
 * WHOLE POINTS. The index is banded at the precision every surface prints it
 * — the badge, the feed card and its headline all print a whole number
 * (toFixed(0)), and feed leg (l) re-bands the number it reads off the card.
 * Banding the unrounded value would let an index of 1,800.4 print "1800"
 * beside "Highly Concentrated", a band whose own definition excludes 1,800,
 * and floating-point sums of squared shares can land a hair either side of
 * a boundary the arithmetic hits exactly (ten equal-share families: 1,000).
 * Measured 2026-09-25: no shipped figure sits within half a point of 1,000
 * or 1,800, so this changes no published band today. R-DEC-132b (controller,
 * 2026-09-26) ACCEPTED this rounding: the band then matches the printed
 * figure, which is the number a reader holds it against. Its consequence at
 * the edges is deliberate and pinned by hhi-band.test.ts — 999.5 prints
 * "1000" and is moderately concentrated; 1,800.4 prints "1800" and is
 * moderately concentrated, not highly.
 *
 * No editorial adjectives: an index above 1,800 is "highly concentrated",
 * never a "near-monopoly" (the site's wording before backlog #57).
 */

/** The vintage every surface that names the bands must name with them. */
export const HHI_BANDS_VINTAGE = "2023 Merger Guidelines";

/** Where the thresholds are stated: DOJ Antitrust Division, updated 2024-01-17. */
export const HHI_BANDS_SOURCE_URL = "https://www.justice.gov/atr/herfindahl-hirschman-index";

/** Inclusive floor of "moderately concentrated". */
export const HHI_MODERATE_MIN = 1000;
/** Highly concentrated means IN EXCESS of this; 1,800 itself is moderate. */
export const HHI_CONCENTRATED_MIN = 1800;

/**
 * @typedef {{ key: "unconcentrated" | "moderate" | "concentrated", label: string }} HhiBand
 */

/**
 * @param {number} value
 * @returns {HhiBand}
 */
export function hhiBand(value) {
  // Whole points, as printed — see WHOLE POINTS above. hhi-band.test.ts
  // holds this to toFixed(0) across both boundaries.
  const points = Math.round(value);
  if (points > HHI_CONCENTRATED_MIN) {
    return { key: "concentrated", label: "Highly Concentrated" };
  }
  if (points >= HHI_MODERATE_MIN) {
    return { key: "moderate", label: "Moderately Concentrated" };
  }
  return { key: "unconcentrated", label: "Unconcentrated" };
}

/**
 * The vintage line printed, as visible text, under the program badge
 * (R-DEC-132b): "2023 Merger Guidelines bands" under a band the guidelines
 * define, "Below the 2023 Merger Guidelines bands" under Unconcentrated —
 * the guidelines name no band there, so the line places the index below
 * theirs rather than crediting them with this site's word. Banded by hhiBand
 * (whole points). scripts/gates/coverage.mjs holds the rendered line to this
 * function; hhi-scope-note.ts uses the same phrase mid-sentence.
 *
 * @param {number} value
 * @returns {string}
 */
export function hhiBandVintageLine(value) {
  return hhiBand(value).key === "unconcentrated"
    ? `Below the ${HHI_BANDS_VINTAGE} bands`
    : `${HHI_BANDS_VINTAGE} bands`;
}
