"use client";

/**
 * Dataset download cards — uses useAssetUrl() to resolve runtime asset base.
 *
 * Degraded mode (Phase 5C G3): on mount a HEAD probe checks
 * {assetBase}/citations/citations.parquet. When the asset bundle is not
 * attached to the deployment, an explicit banner (data-degraded="downloads")
 * renders above the cards and the cards dim with aria-disabled — no dead
 * download links pretending to work.
 *
 * TRI-PERSONA REVIEW WAVE 4, item 2 — THE INVENTORY IS THE MANIFEST NOW.
 * This file used to author its own fourteen-card list with its own
 * hand-written descriptions, beside a /data/ page that reads all sixteen from
 * data/site/json/datasets.json. The two drifted, exactly as §P1-5 predicted
 * when it moved /data/ off literals:
 *
 *   · budget_lines_decade (32,642 rows — the decade table, the most
 *     analytically distinctive thing on the site) and fct_district_totals
 *     were QUERYABLE on /data/ and absent from /downloads/. Both parquets
 *     ship; only the card was missing.
 *   · dim_entities was described as "Top-200 contractor families". The file
 *     is 114,806 rows.
 *   · jbook_details was described as having "page-level PDF citation".
 *     7,991 of its 17,007 non-zero rows (47%) resolve to no page at all —
 *     the exporter's own `resolution` column says so, and the manifest scope
 *     now says so on both pages.
 *
 * So the card list, the row counts, the descriptions and the cited badge all
 * come from the manifest the exporter computes from the emitted parquets.
 * This file authors NO dataset name, NO count and NO description.
 */

import React from "react";
import { useAssetUrl, useAssetConfigResolved } from "@/components/asset-config";

/** The dataset whose card the era-map table follows (families piece 1). */
const ERA_MAP_DATASET = "p1_era_line_map";

/** The manifest fields a card needs — mirrors lib/data DatasetManifestEntry. */
export interface DownloadDataset {
  name: string;
  row_count: number;
  scope: string;
  cited: boolean;
  caveat?: string;
}

interface DatasetCard {
  name: string;
  description: string;
  caveat?: string;
  rowCount?: number;
  parquetPath: string;
  isCited: boolean;
}

/**
 * Column and dataset names inside a card's description (`hhi_high`, the
 * `*_all` / `*_high` column suffixes, `fact_id`) are the parquet schema's own
 * identifiers, the strings a downloader types into DuckDB. They render as
 * <code>, the way this file already sets `pdfs/` and `workbooks/`, so the
 * text around them reads as prose and the names read as names.
 *
 * Integration 2026-09-25 (R-INT-7): gate 27 leg 31 ("exposed enum") fired on
 * the #80 fct_program_concentration scope, whose floor clause must name
 * `program_dollars_high` (tests/test_export_site_datasets_manifest.py). The
 * words are unchanged. Only lower-case snake_case and `*_suffix` runs are
 * wrapped; anything else stays in the copy gate's scan.
 */
const IDENTIFIER_RUN = /(\*_[a-z0-9]+|\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b)/;

export function withIdentifierCode(text: string): React.ReactNode[] {
  // split() with one capture group puts every identifier at an odd index.
  return text
    .split(IDENTIFIER_RUN)
    .map((part, i) => (i % 2 === 1 ? <code key={i}>{part}</code> : part))
    .filter((part) => part !== "");
}

/** The datasets.json "citations" entry fields the citation index card needs. */
export interface DownloadCitationsIndex {
  row_count: number;
  scope: string;
}

function buildDatasets(
  inventory: DownloadDataset[],
  uncited: Set<string>,
  citationsIndex: DownloadCitationsIndex,
): DatasetCard[] {
  const cards: DatasetCard[] = inventory.map((ds) => ({
    name: ds.name,
    description: ds.scope,
    caveat: ds.caveat,
    rowCount: ds.row_count,
    parquetPath: `/data/${ds.name}.parquet`,
    isCited: ds.cited && !uncited.has(ds.name),
  }));
  // citations.parquet is the citation INDEX, not a mart — it is not in the
  // manifest's datasets list (it is not written to data/site/data/) and is
  // listed last. Its description and count are the exporter's own
  // datasets.json "citations" entry (final review #10(c), 2026-09-27): the
  // hand-written list of kinds this card used to print named 3 of the 10
  // kinds the file holds.
  cards.push({
    name: "citations",
    description: citationsIndex.scope,
    rowCount: citationsIndex.row_count,
    parquetPath: "/citations/citations.parquet",
    isCited: true,
  });
  return cards;
}

export function DownloadCards({
  builtAt,
  inventory,
  citationsIndex,
  workbookCount,
  uncitedDatasets = [],
  eraMapTable = null,
}: {
  builtAt: string;
  /**
   * The shipped-parquet manifest (data/site/json/datasets.json), passed
   * through from the server page. THE card list — see the file header.
   */
  inventory: DownloadDataset[];
  /**
   * datasets.json's "citations" entry (lib/data citationsIndexOf): the
   * citation index card's description and row count.
   */
  citationsIndex: DownloadCitationsIndex;
  /**
   * site_meta.datasets row counts — accepted and NOT read since the citation
   * index card reads its own entry (final review #10(c)).
   */
  datasets?: Record<string, number>;
  /**
   * site_meta.pdf_count — accepted and NOT rendered (fix-wave round 2): it
   * counts the documents the export run copied (204 on run 4), not the
   * pdfs/ directory that ships (225). Render it again once the exporter
   * prunes or counts the directory (#164).
   */
  pdfCount?: number;
  /** Number of workbook files in the bundle (from site_meta.workbook_count). */
  workbookCount?: number;
  /**
   * The manifest's uncited_datasets ledger (from site_meta.uncited_datasets).
   * Dataset cards show the "cited" badge IFF they are off this ledger — the
   * badge flips automatically when a dataset gains a citation tier.
   */
  uncitedDatasets?: string[];
  /**
   * The era-map table (families piece 1), ALREADY RENDERED by the server
   * page (<EraMapTable summary>). When present it renders as the full-width
   * grid item directly after the p1_era_line_map card, which then spans both
   * columns too (spec §6.4 owner decision). Never the summary itself: this
   * is a client component, so every prop is serialised into the page's RSC
   * payload, and the summary carries uncited actuals_thousands sums (Task 19
   * fix round 1).
   */
  eraMapTable?: React.ReactNode;
}) {
  const assetUrl = useAssetUrl();
  const assetConfigResolved = useAssetConfigResolved();
  const DATASETS = buildDatasets(
    inventory,
    new Set(uncitedDatasets),
    citationsIndex,
  );

  // Asset-bundle reachability: null = probing, true = reachable, false = not.
  //
  // WAIT FOR THE RUNTIME BASE (Wave 4). `ssrBase` now seeds the first paint
  // with the production asset host, so probing before /config.json resolves
  // would fire at prod R2 from 127.0.0.1 — CORS-blocked — and flash the
  // "not attached to this deployment" banner on every local page load. The
  // probe runs once, against the base the reader's browser will actually use.
  const [assetsAvailable, setAssetsAvailable] = React.useState<boolean | null>(
    null,
  );
  React.useEffect(() => {
    if (!assetConfigResolved) return;
    let cancelled = false;
    fetch(assetUrl("/citations/citations.parquet"), { method: "HEAD" })
      .then((r) => {
        if (!cancelled) setAssetsAvailable(r.ok);
      })
      .catch(() => {
        if (!cancelled) setAssetsAvailable(false);
      });
    return () => {
      cancelled = true;
    };
  }, [assetUrl, assetConfigResolved]);
  const degraded = assetsAvailable === false;

  const builtDate = builtAt
    ? new Date(builtAt).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "unknown";

  return (
    <div>
      {degraded && (
        <div
          data-degraded="downloads"
          role="alert"
          className="mb-6 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200"
        >
          Download files are not attached to this deployment yet — they ship
          from object storage. Checksums and schemas below still describe the
          bundle.
        </div>
      )}

      <p className="text-sm text-muted-foreground mb-6">
        Bundle built: <time dateTime={builtAt}>{builtDate}</time>. Files are
        in Apache Parquet format, readable with DuckDB, pandas, R
        arrow/duckdb, or any Parquet-compatible tool. Each file includes the
        same provenance metadata that backs on-screen figures.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {DATASETS.map((ds) => (
          <React.Fragment key={ds.name}>
          <div
            data-dataset-card={ds.name}
            {...(degraded ? { "aria-disabled": true } : {})}
            className={[
              "rounded-lg border border-border bg-card p-4 flex flex-col gap-2",
              // The full-width era table follows this card; spanning it too
              // keeps the grid from leaving the cell beside it empty.
              ds.name === ERA_MAP_DATASET && eraMapTable ? "sm:col-span-2" : "",
              degraded ? "opacity-50" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <div className="flex items-start justify-between gap-2">
              {/* A level-2 heading per card (Task 19 fix round 1): the era
                  table's h3 nests under p1_era_line_map's, and the cards
                  after it stay its siblings in the page outline. role, not
                  <h2>, so the global h2 type style does not apply. */}
              <span role="heading" aria-level={2} className="text-sm font-medium text-foreground">
                {ds.name}
              </span>
              {ds.rowCount !== undefined && (
                <span className="t-figure t-figure--3 ml-auto shrink-0 text-muted-foreground">
                  {ds.rowCount.toLocaleString("en-US")} rows
                </span>
              )}
              {ds.isCited && (
                <span className="shrink-0 text-xs rounded bg-emerald-100 text-emerald-800 px-1.5 py-0.5">
                  cited
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground leading-5">
              {withIdentifierCode(ds.description)}
            </p>
            {ds.caveat && (
              <p
                data-dataset-caveat={ds.name}
                className="text-xs text-muted-foreground leading-5 border-l-2 border-amber-500/50 pl-2"
              >
                {/* Fix round 5 (2026-09-26): the R-DEC-130c concentration
                    caveat names the mart's columns (member_keys_with_links,
                    links_outside_member_keys); as plain text gate 27 leg 31
                    read them as exposed enums. Same treatment as the
                    description, words unchanged. */}
                {withIdentifierCode(ds.caveat)}
              </p>
            )}
            <a
              href={assetUrl(ds.parquetPath)}
              {...(degraded ? { "aria-disabled": true, tabIndex: -1 } : {})}
              className={[
                "mt-auto inline-flex items-center gap-1 text-xs text-primary hover:underline",
                degraded ? "pointer-events-none" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              download
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              {ds.name}.parquet
            </a>
          </div>
          {ds.name === ERA_MAP_DATASET && eraMapTable}
          </React.Fragment>
        ))}
      </div>

      <div className="mt-8 rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
        {/* Level 2 like the card names (Task 19 fix round 1), so this box
            is not read as part of the last card's section. */}
        <p role="heading" aria-level={2} className="font-medium text-foreground mb-2">
          Additional assets (not in table above)
        </p>
        {/* citations.parquet used to be listed here too, under a heading
            that says "not in table above" while it had a card of its own.
            One place now: the card. */}
        {/* Task 26 (polish 18): this typed "(~149 MB total)" — the
            2026-07-02 bundle; data/site/pdfs/ held 1.8 GB on 2026-09-25 — and
            fell back to literal counts (34, 3) when the export carried none.
            A size the export does not publish is dropped (the smaller true
            claim), and a missing count renders no number rather than an old
            one. */}
        <ul className="list-disc list-inside space-y-1 text-xs">
          {/* Fix-wave round 2 (B4): no count either. pdf_count (204 on run
              4) is the documents the export run copied; the pdfs/ directory
              the R2 sync ships held 225 (#164, an exporter fix). */}
          <li>
            <code>pdfs/</code> — SHA-named J-book PDFs
          </li>
          <li>
            <code>workbooks/</code> —{" "}
            {workbookCount !== undefined ? `${workbookCount} ` : ""}R-1/P-1
            Excel rollup files
          </li>
        </ul>
      </div>
    </div>
  );
}
