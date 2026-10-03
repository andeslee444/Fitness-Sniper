/**
 * The era-map decision table on /downloads/ (families piece 1, spec
 * 2026-10-02 §6.4), directly under the p1_era_line_map download card:
 * DownloadCards renders it inside its card grid as the item right after that
 * card, spanning both columns from `sm` up (`sm:col-span-2`); gate 24 leg (s)
 * checks that position.
 *
 * Placed here by the owner's decision (spec §6.4 correction): as built it
 * weighed +2,393 gzip on /coverage/ (292 left) and +3,647 on /data/ (2,083
 * left after the inventory hoist), and no ceiling is raised; /downloads/
 * carries no page-weight ceiling (+2,354 gzip here, measured with the table
 * below the card grid; gate 1 has no /downloads/ entry, so no step re-weighs
 * it). Counts only: dollars stay in
 * json/era_map_summary.json (see lib/era-map). Below `sm` each row becomes a
 * card (the /data/ treatment) with its field labels; the gate hooks
 * ([data-era-edition], [data-era-cell], [data-era-value]) are what gate 24
 * leg (s) reads.
 */
import { ERA_MAP_COLUMNS, eraMapCells, type EraMapSummary } from "@/lib/era-map";

export function EraMapTable({ summary }: { summary: EraMapSummary }) {
  return (
    <section id="era-map" aria-labelledby="era-map-heading" className="sm:col-span-2">
      <h2 id="era-map-heading" className="mb-3">
        Procurement lines before PB2024
      </h2>
      <p className="mb-4 max-w-2xl text-sm leading-7 text-muted-foreground">
        Each PB2017–PB2023 P-1 line reaches a program page only through a dated
        decision on the budget line code it printed, published in the
        p1_era_line_map dataset above. For each edition the table counts the
        lines, the codes each decision covers and the era figures cited on the
        site that carry a complete PDF receipt.
      </p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table data-era-map className="min-w-full text-sm">
          <caption className="sr-only">
            Era P-1 lines, codes per decision and complete PDF receipts, by
            President&apos;s Budget edition.
          </caption>
          <thead className="hidden sm:table-header-group">
            <tr className="border-b border-border bg-muted/50">
              <th scope="col" className="px-4 py-2 text-left font-semibold text-muted-foreground">
                Edition
              </th>
              {ERA_MAP_COLUMNS.map((c) => (
                <th key={c.key} scope="col" className="px-4 py-2 text-right font-semibold text-muted-foreground">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {summary.editions.map((e) => (
              <tr
                key={e.edition}
                data-era-edition={e.edition}
                className="block border-b border-border py-3 last:border-0 sm:table-row sm:py-0"
              >
                <th scope="row" className="block px-4 text-left font-medium text-foreground sm:table-cell sm:py-2">
                  {`PB${e.edition}`}
                </th>
                {eraMapCells(e).map((c) => (
                  <td
                    key={c.key}
                    data-era-cell={c.key}
                    className="block px-4 pt-1 tabular-nums text-muted-foreground sm:table-cell sm:py-2 sm:text-right"
                  >
                    <span className="t-label mb-0.5 block sm:hidden">{c.label}</span>
                    <span data-era-value>{c.value}</span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
