/**
 * chart-figure.tsx — the site's ONE chart contract (PM Sprint 3, spec §P2-3).
 *
 * The review found three of five SVGs on the program page with neither
 * <title> nor aria-label, and no table anywhere carrying a <caption>. A
 * picture of a number is not a receipt; a picture nobody can read is not
 * even a picture. Every chart on this site therefore ships as:
 *
 *   <figure data-chart="{id}">
 *     …the svg, role="img"|"group", aria-label = the NAME,
 *        aria-describedby = the description, and a <desc> mirror…
 *     <figcaption data-chart-desc>   what it shows AND what to take from it,
 *                                    never a restatement of the title
 *     …the table view — a real <table data-chart-table> with a <caption> and
 *       [data-amount] figures carrying the site's usual citation affordance,
 *       either visible or behind a native <details>/<summary> disclosure
 *       (keyboard-reachable with no script, which a static export needs).
 *
 * The underlying data is already tabular in every case, so the table view is
 * EXPOSURE, not new data — and it is the single highest-value accessibility
 * move here: it serves screen readers, anyone who finds the visual encoding
 * hard to decode, and phones, which is where a 1000-unit-wide Sankey is
 * least readable.
 *
 * Gate 2 (render-static (ch)) pins name/desc/caption/[data-amount]
 * statically; gate 6 (charts.mjs) pins that the disclosure really takes
 * keyboard focus, really reveals a laid-out table, and does not push the
 * document sideways at 390px when every table on the page is open.
 *
 * Server component — the client charts import it too (it renders no state).
 */

import type { ReactNode } from "react";

/** The id the chart's svg points at with aria-describedby. */
export function chartDescId(id: string): string {
  return `chart-desc-${id}`;
}

export function ChartFigure({
  id,
  description,
  children,
  table,
  className = "",
  descClassName = "",
  captionPlacement = "first",
}: {
  /** Stable chart id — the [data-chart] value and the description's anchor. */
  id: string;
  /**
   * What the chart shows AND what the reader should take from it. Never a
   * restatement of the heading: the gate compares it against the svg's
   * accessible name and fails a description that merely echoes it.
   */
  description: ReactNode;
  /** The chart itself (an svg carrying aria-describedby={chartDescId(id)}). */
  children: ReactNode;
  /**
   * The table view, rendered after the chart. Omit it when the table already
   * lives inside `children` (the sparkline's legend IS its table); wrap it in
   * <ChartTableDisclosure> when it should sit behind a "View as table" toggle.
   */
  table?: ReactNode;
  className?: string;
  descClassName?: string;
  /**
   * Where the <figcaption> sits inside the <figure>. Default "first" — the
   * reader is told what the picture is for before looking at it, which is
   * the better read wherever the caption is short enough to afford it.
   *
   * "last" exists for ONE shape: a tall diagram on a narrow viewport whose
   * caption would push the picture itself below the fold. /lineage/ at 390
   * was the case that forced it — 260px of description plus a 108px legend
   * above a diagram that then started 1,049px down the page, against gate
   * 16's index-fold floor of 844 (answerfold.mjs, floor 2026-09-18). A
   * caveat that a reader has to scroll past the data to reach is the defect;
   * a caveat the reader reaches right after the data is not. Choose "last"
   * only on that evidence — a measured fold failure — never as a style
   * preference, and never to make room for a longer caption.
   */
  captionPlacement?: "first" | "last";
}) {
  // HTML's <figure> content model allows the <figcaption> only as the FIRST
  // or LAST child — those are the two legal positions, and this prop picks
  // between them. Nothing else about the caption changes with it: same text,
  // same id={chartDescId(id)}, same data-chart-desc, same classes, so gate 2
  // leg (ch) (name/desc/caption/[data-amount]) and gate 6 leg (c1) (a figure
  // must carry a description visible to sighted readers) see an identical
  // element either way. Only the order moves.
  const caption = (
    <figcaption
      id={chartDescId(id)}
      data-chart-desc=""
      className={`mb-2 text-xs leading-5 text-muted-foreground ${descClassName}`}
    >
      {description}
    </figcaption>
  );
  return (
    <figure data-chart={id} className={`m-0 ${className}`}>
      {captionPlacement === "first" ? caption : null}
      {children}
      {table}
      {captionPlacement === "last" ? caption : null}
    </figure>
  );
}

/**
 * <ChartTableDisclosure> — the "View as table" affordance. A native
 * <details>: focusable and operable with no JavaScript, which matters on a
 * statically exported site, and cheap in bytes (no extra client island).
 *
 * The inner wrapper is the SCROLL CONTAINER: a wide table scrolls inside it
 * and never widens the document (gate 3's 390px leg measures with these
 * closed; gate 6 opens them all and re-measures).
 */
export function ChartTableDisclosure({
  label = "View as table",
  children,
  className = "",
}: {
  label?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <details className={`mt-2 ${className}`}>
      <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring [&::-webkit-details-marker]:hidden">
        <span aria-hidden="true">▤</span>
        {label}
      </summary>
      {/* Round-3 judging (all three judges, 390): the SVG is ~840px inside a
          ~356px scroller, so the right-hand column is cut mid-word and the cut
          edge reads as the end of the data. The <ScrollCue> above says it
          scrolls; this says WHERE. A right-edge fade is the standard "there is
          more this way" signal, and it is decorative — pointer-events-none, so
          it never intercepts a drag on the chart underneath, and it is hidden
          at `sm` and up where the chart fits. */}
      <div className="relative mt-2 max-w-full">
        <div className="max-w-full overflow-x-auto">{children}</div>
        <div
          aria-hidden="true"
          data-chart-edge-fade
          className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-background to-transparent sm:hidden"
        />
      </div>
    </details>
  );
}
