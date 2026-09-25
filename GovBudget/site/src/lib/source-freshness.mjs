/**
 * source-freshness.mjs — the /methodology/ fetch-date clause (ROADMAP #8;
 * Task 29 fix round 1).
 *
 * THE DEFECT THIS MODULE CLOSES. The USAspending card ended "Source cadence:
 * monthly — this corpus was fetched 2026-06-11." The date is the exporter's
 * group as-of: the OLDEST of the three award datasets' newest downloads. Once
 * the 2026-09-06 FY2026 contract and assistance archives (fetched 2026-09-24)
 * were adopted, that date belonged to the subawards alone, and the sentence
 * gave it to the whole corpus. Gate 24 leg m stayed green: it checked the
 * date, which was right, and not whose date it was.
 *
 * So the clause names the part the date belongs to — the group's
 * `stalest_dataset`, derived by export_site._source_freshness_block() from
 * data/manifest.jsonl — and the rendered span carries that name in
 * STALEST_ATTR, which leg m reads back against the manifest itself.
 *
 * WHY .mjs IN src/lib: the Next page and the plain-Node gate's unit test
 * import the same function and the same attribute name (the
 * entity-label-margins.mjs pattern). Pure: no fs, no React, no DOM.
 */

/** The attribute on the rendered clause naming the dataset its date is for. */
export const STALEST_ATTR = "data-source-stalest";

/**
 * The clause after "Source cadence: <word>". "Last refreshed" is the
 * dataset's NEWEST download (a dataset is fetched in several files, one per
 * fiscal year); "least recently refreshed" means no other dataset in the group
 * has an older newest download. It describes FETCH ACTIVITY, not data age: an
 * older fiscal-year file of a more recently refreshed dataset can predate the
 * date shown (2026-09-25 ruling — FY2017–FY2019 archives were fetched
 * 2026-06-10, the subaward file 2026-06-11).
 *
 * @param {{ stalest_dataset: string, as_of: string }} group
 *   site_meta.source_freshness.groups[name]
 * @returns {string}
 */
export function stalestPartClause({ stalest_dataset, as_of }) {
  return ` — its least recently refreshed dataset (${stalest_dataset}) was last fetched ${as_of}.`;
}
