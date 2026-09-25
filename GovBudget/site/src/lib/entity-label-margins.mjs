/**
 * entity-label-margins.mjs — the narrow-label census (ROADMAP #10 A; Task 29S).
 *
 * A published company family's label is the registered parent name of its
 * largest member, chosen by an argmax over obligations. A label that won that
 * argmax by under NEAR_TIE_MARGIN is a coin flip, and gate 24 leg l fails
 * unless data-seeds/entity_display_aliases.csv carries a reviewed row for it.
 *
 * THE DEFECT THIS MODULE CLOSES. /methodology/ stated the size of that
 * problem as a typed literal — "15 of the 200 families we publish carry a
 * label that beat its runner-up by under 15%" — and leg l read the literal
 * back against its recompute. The 2026-09-06 FY2026 refresh moved the
 * argmaxes and the top-200 membership; chain C run 3's recompute found 14,
 * and the sentence was false until someone retyped it. A literal the gate
 * checks is still a literal: it rots first and fails second.
 *
 * WHAT IS DERIVED, AND BY WHOM. One pure function counts; two callers feed it
 * their own inputs:
 *   - the page, at build, through the data reader it already uses:
 *     getEntitiesTop() rows, and as the seeded keys the rows the exporter
 *     gave a `label` (export_site.py attaches one exactly when the seed
 *     carries the family's key). entities_top.json carries no margins — the
 *     margins live in the award lake — so the page's census has
 *     closeMargin = null, and its sentence states only what the build can
 *     count: the threshold, the published families, and how many carry a
 *     seed label;
 *   - gate 24 leg l, from familylabel-recompute.py's families (DuckDB over
 *     the lake, margins included) and the seed CSV it parses itself. It
 *     enforces the rule with isNearTie(), and then requires the built page to
 *     contain EXACTLY labelCensusSentence() of its own census.
 * So a page and a gate that read different families, a seed row the exporter
 * dropped, or a threshold moved on one side only all fail the build instead
 * of shipping a sentence that used to be true.
 *
 * WHY .mjs IN src/lib: the Next page and a plain-Node gate import the literal
 * same function (the hhi-band.mjs / company-name.mjs pattern). Pure: no fs,
 * no React, no DOM.
 */

/**
 * The margin below which a label is a coin-flip win. Deliberately the number
 * the spike measured the blast radius at
 * (docs/superpowers/reviews/10-entity-resolution-spike.md §1) — lowering it to
 * make a family pass is the one edit this constant must never see.
 */
export const NEAR_TIE_MARGIN = 0.15;

/**
 * @typedef {{ family_key: string, margin?: number }} PublishedFamily
 *   A published family; `margin` = (d1 - d2) / d1 over its dominant member's
 *   parent registrations, present only where the lake was read.
 * @typedef {{ published: number, closeMargin: number | null, curated: number, thresholdPct: number }} LabelCensus
 */

/** @param {PublishedFamily} family */
const hasMargin = (family) => Number.isFinite(family?.margin);

/**
 * True when the family's label won its argmax by under NEAR_TIE_MARGIN. A
 * family whose margin was not measured is not a near-tie — it is unknown, and
 * labelMarginCensus refuses to count a list that mixes the two.
 *
 * @param {PublishedFamily} family
 */
export function isNearTie(family) {
  return hasMargin(family) && /** @type {number} */ (family.margin) < NEAR_TIE_MARGIN;
}

/**
 * @param {Iterable<PublishedFamily>} families the published families
 * @param {Iterable<string>} seededKeys the family_keys the alias seed carries a row for
 * @returns {LabelCensus}
 *   `published` — families.length; `closeMargin` — how many are near-ties, or
 *   null when no family carries a margin (the page's input); `curated` — how
 *   many published families the seed carries (a seed row for an unpublished
 *   family curates nothing); `thresholdPct` — NEAR_TIE_MARGIN as a percent.
 */
export function labelMarginCensus(families, seededKeys) {
  const list = [...families];
  const measured = list.filter(hasMargin).length;
  if (measured !== 0 && measured !== list.length) {
    throw new Error(
      `labelMarginCensus: ${measured} of ${list.length} families carry a margin — ` +
        `a near-tie count over part of the published set is not a census`,
    );
  }
  const seeded = new Set(seededKeys);
  return {
    published: list.length,
    closeMargin: measured === 0 ? null : list.filter(isNearTie).length,
    curated: list.filter((f) => seeded.has(f.family_key)).length,
    thresholdPct: Math.round(NEAR_TIE_MARGIN * 100),
  };
}

/** @param {number} n */
const count = (n) => Number(n).toLocaleString("en-US");

/**
 * The one sentence. Built from slots so the matcher below is derived from
 * the same words and cannot drift from them.
 *
 * @param {string} pct @param {string} curated @param {string} published
 */
const template = (pct, curated, published) =>
  `A label that beat its runner-up by under ${pct}% fails the build without a ` +
  `reviewed one from a curated seed; ${curated} of the ${published} families ` +
  `we publish carry one, each company page still showing its registered name.`;

/**
 * The /methodology/ sentence for a census — rendered verbatim by the page,
 * required verbatim by gate 24 leg l.
 *
 * @param {LabelCensus} census (closeMargin is not printed: the page cannot know it)
 */
export function labelCensusSentence({ published, curated, thresholdPct }) {
  return template(String(thresholdPct), count(curated), count(published));
}

/** The sentence with every figure a capture group — for the diagnostic only. */
const SENTENCE_RE = new RegExp(
  template("\u0001", "\u0002", "\u0003")
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace("\u0001", "(\\d+)")
    .replace("\u0002", "([\\d,]+)")
    .replace("\u0003", "([\\d,]+)"),
);

/**
 * Leg l's binding: the built page's text must contain exactly the sentence
 * this census renders. Returns findings (empty = bound).
 *
 * @param {string} pageText the built /methodology/ text
 * @param {LabelCensus} census the gate's own census
 * @returns {string[]}
 */
export function labelCensusFindings(pageText, census) {
  const text = String(pageText ?? "").replace(/\s+/g, " ");
  const expected = labelCensusSentence(census);
  if (text.includes(expected)) return [];
  const stated = text.match(SENTENCE_RE);
  if (!stated) {
    return [
      `the narrow-label census sentence is missing or reworded — the page must ` +
        `render labelCensusSentence() verbatim; this census renders "${expected}"`,
    ];
  }
  return [
    `states "${stated[0]}", but the census computes "${expected}" ` +
      `(${census.curated} of ${census.published} published families seeded, ` +
      `near-tie threshold ${census.thresholdPct}%)`,
  ];
}
