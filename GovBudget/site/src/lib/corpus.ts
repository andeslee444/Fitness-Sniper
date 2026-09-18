import "server-only";

/**
 * Canonical corpus statement — PM-review Sprint 2, spec §P1-5.
 *
 * The site used to state its own size four different ways: /programs/ said
 * "1,741 program elements", /years/ said "all 1,993 program pages are
 * browsable", /methodology/ said "1,741 of 1,993", and /data/ showed
 * dim_programs = 326. From outside that reads as the site disagreeing with
 * itself on the one page built to let people check its work.
 *
 * There is now ONE wording, built from ONE pair of numbers:
 *
 *   programPages — every program_details sidecar, i.e. every /program/{pe}/
 *                  page that actually gets built. Counted from the directory,
 *                  which is the artifact itself, not a claim about it.
 *   detailPages  — sidecars that actually hold R-2/P-40 J-book DETAIL rows.
 *
 * site_meta.counts.program_pages is a CROSS-CHECK, not a second source: if the
 * exporter's count disagrees with the sidecars on disk, that is a real defect
 * and this module throws rather than picking a winner.
 *
 * BACKLOG #35 (Sprint 3 round 3). detailPages used to be programs.json's
 * length, 1,741 — while /data/ published dim_programs at 1,739 rows from the
 * parquet. programs.json is the /programs/ INDEX and since backlog #17 carries
 * two trajectory-only programs with no J-book detail; dim_programs, built from
 * the detail rows, holds neither. So the corpus statement overstated the
 * detail-grade tier by two on the very number /coverage/ leads with. It is now
 * getDetailGradeCount() — the sidecars that actually carry detail rows, with
 * the parquet's own row count as the cross-check.
 *
 * The scope caveat is `site_meta.corpus_scope` — the same string the §P0-5
 * hero superlative carries, so the two cannot drift.
 */

import {
  getDatasetManifest,
  getDetailGradeCount,
  getFlowChartMeta,
  getFlowsCount,
  getFlowsOutsideBridgeCount,
  getProgramPagesCount,
  getProgramSitemapSlugs,
  getPrograms,
  getSiteMeta,
} from "./data";
import { formatCount } from "./format";

export interface Corpus {
  /** Sidecars carrying R-2/P-40 J-book detail rows (= dim_programs). */
  detailPages: number;
  /** Every browsable /program/{pe}/ page (all tiers). */
  programPages: number;
  /** The §P0-5 scope caveat, verbatim from the build. */
  scope: string;
  /** The canonical sentence — the ONLY place corpus size is worded. */
  statement: string;
}

/** Shared with the datatruth gate's leg-d regex — change both or neither. */
export function corpusStatement(
  programPages: number,
  detailPages: number,
  scope: string,
): string {
  return (
    `${formatCount(programPages)} browsable program pages; ` +
    `${formatCount(detailPages)} of them ` +
    `carry detail-grade R-2/P-40 J-book data — ${scope}.`
  );
}

export function getCorpus(): Corpus {
  const meta = getSiteMeta();
  const programPages = getProgramPagesCount();
  const detailPages = getDetailGradeCount();

  const declared = meta.counts.program_pages;
  if (declared !== undefined && declared !== programPages) {
    throw new Error(
      `[govbudget/corpus] site_meta.counts.program_pages=${declared} but ` +
        `${programPages} program_details sidecars exist on disk. The export is ` +
        `inconsistent with its own output — re-run "uv run python -m govbudget export-site".`,
    );
  }
  if (!(programPages > 0) || !(detailPages > 0)) {
    throw new Error(
      `[govbudget/corpus] degenerate corpus (${programPages} pages, ${detailPages} detail-grade) — ` +
        `sidecars missing; re-run "uv run python -m govbudget export-site".`,
    );
  }
  if (detailPages > programPages) {
    throw new Error(
      `[govbudget/corpus] detail-grade (${detailPages}) exceeds total program pages (${programPages}) — ` +
        `the detail tier is a SUBSET of the page universe by definition.`,
    );
  }

  const scope = meta.corpus_scope;
  if (!scope) {
    throw new Error(
      `[govbudget/corpus] site_meta.json has no corpus_scope — re-run ` +
        `"uv run python -m govbudget export-site" (PM Sprint 2 §P1-5 added it).`,
    );
  }

  return {
    detailPages,
    programPages,
    scope,
    statement: corpusStatement(programPages, detailPages, scope),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// The corpus-count registry — tri-persona review Wave 4, item 4
// ─────────────────────────────────────────────────────────────────────────────
//
// The site states its own size FIVE ways and every one of them is right for
// its own denominator (as measured 2026-08-29; the registry below is the
// live value):
//
//   2,016  every indexable /program/ URL declared in sitemap.xml
//   2,005  program_details sidecars — the browsable page universe
//   1,755  programs.json rows — the FY2026 budget index on /programs/
//   1,753  dim_programs.parquet rows
//   1,743  sidecars carrying at least one R-2/P-40 detail row
//
// The corpus statement above already pins two of them on four pages. Nothing
// pinned the other three, nothing said what each counts, and a reader who
// compared /programs/ ("1,755 program elements") against sitemap.xml (2,016)
// or /data/ (dim_programs 1,753) had no way to tell an inconsistency from a
// different question.
//
// So: ONE declaration of all five, each DERIVED from the artifact that defines
// it, each carrying the sentence that says what one unit is. /coverage/
// renders the list; gate 24 leg k recomputes all five independently and
// requires every corpus-shaped number rendered on the singleton pages to be
// one of them. A hard-coded 1,750 fails — that is the leg's whole point, and
// it is the generalisation of the `measured:` annotation and the stale
// docstring this project has been bitten by twice already.

export interface CorpusCount {
  /** Stable id — the gate's own key, and the row's DOM hook. */
  id: string;
  value: number;
  /** Where the number is published. */
  where: string;
  /** What ONE unit of this count is. */
  counts: string;
}

let _corpusCounts: CorpusCount[] | null = null;

/**
 * Every corpus count the site publishes, largest first, each derived.
 *
 * Order is deliberate: the list reads as a set of nested universes, so the
 * differences between adjacent rows are the interesting part.
 */
export function getCorpusCounts(): CorpusCount[] {
  if (_corpusCounts) return _corpusCounts;
  const dimPrograms = getDatasetManifest().datasets.find(
    (d) => d.name === "dim_programs",
  );
  if (!dimPrograms) {
    throw new Error(
      "[govbudget/corpus] datasets.json has no dim_programs entry — the " +
        "corpus reconciliation cannot state what /data/ publishes. Re-run " +
        '"uv run python -m govbudget export-site".',
    );
  }
  _corpusCounts = [
    {
      id: "sitemap-urls",
      value: getProgramSitemapSlugs().length,
      where: "sitemap.xml",
      counts:
        "Indexable /program/ URLs — every page below, plus a stub per " +
        "budget-line key two programs share.",
    },
    {
      id: "program-pages",
      value: getProgramPagesCount(),
      where: "the corpus line",
      // ROADMAP #28 widened what this counts and made the sentence more
      // nearly true at the same time. Before the decade tier it read "every
      // element the workbooks name in any loaded edition", while the page
      // universe was in fact FY2026-only — 1,287 elements named by an
      // earlier edition had no page. 553 of those have one now: the ones
      // whose history is CITED (a positive fct_decade_series grain). The
      // rest are era P-1 display line numbers, which are workbook rows
      // rather than program identities, and reserve-component P-1R rows,
      // whose money is already inside the P-1 line. The sentence names the
      // two universes it unions instead of claiming all of them.
      counts:
        "Browsable program pages, all tiers: elements the FY2026 workbooks " +
        "list, plus elements only earlier editions list.",
    },
    {
      id: "index-rows",
      value: getPrograms().length,
      where: "Programs, Years, home",
      counts:
        "Rows of the FY2026 index — element \u00d7 appropriation account in " +
        "PB2026. An older-edition-only page is not a row.",
    },
    {
      id: "dim-programs-rows",
      value: dimPrograms.row_count,
      where: "dim_programs, on Data",
      counts:
        "Detail-grade elements, plus a synthetic row per shared-key " +
        "account with no exhibit behind it.",
    },
    {
      id: "detail-pages",
      value: getDetailGradeCount(),
      where: "the corpus line, and the row above",
      counts:
        "Pages carrying R-2/P-40 project detail. The rest carry cited " +
        "R-1/P-1 rollup figures only.",
    },
  ];

  // A count out of order means one of the derivations has changed shape (a
  // subset overtaking its superset), which is a defect, not a rendering
  // choice — and the table's whole claim is that these are nested.
  for (let i = 1; i < _corpusCounts.length; i++) {
    const prev = _corpusCounts[i - 1];
    const cur = _corpusCounts[i];
    if (!(cur.value <= prev.value)) {
      throw new Error(
        `[govbudget/corpus] ${cur.id} (${cur.value}) exceeds ${prev.id} ` +
          `(${prev.value}). These counts are nested universes by ` +
          `construction; one of the derivations no longer counts what its ` +
          `description says.`,
      );
    }
  }
  return _corpusCounts;
}

// ─────────────────────────────────────────────────────────────────────────────
// The crosswalk-count registry — PM-S3 leftover (ROADMAP.md:34)
// ─────────────────────────────────────────────────────────────────────────────
//
// The site publishes "crosswalked" TWICE, with different denominators and
// different questions behind them, and until now nothing said so:
//
//   link-universe                 program elements with at least one published
//                                 budget→award link, at any tier
//   bridged-request               of those, the ones that also carry FY2026
//                                 request dollars (the /flow/ bridge)
//   high-confidence-links         of those, the ones with a high-confidence link
//   district-linkable             elements with a follow-the-dollar view (a
//                                 high-confidence link whose award records a
//                                 place of performance)
//   district-linkable-unbridged   of those, the ones NOT in the bridged set
//
// The last row is the point. The two published ratios are not nested: a reader
// who saw "384 of 444" on /flow/ and "200 of 1,938" on /district/ had no way
// to tell an inconsistency from a different question. /coverage/#crosswalk
// renders the list; gate 24 leg (p) recomputes all five from the shipped
// artifacts and rejects any crosswalk-shaped ratio, on the pages that publish
// one, which is not a declared value.
//
// EVERY VALUE IS READ, NEVER RE-DERIVED. The first three come straight off
// flow_chart.json's own bridge band (the exporter publishes them); the last
// two come off the shipped sidecar directory and that same band. Nothing here
// recomputes a figure the export already states — which is also why the
// link-LEVEL census (how many graded links each evidence path publishes) is
// NOT duplicated here: site_meta.link_adjudication carries it, /methodology/
// renders it, and gate 24 leg (o) binds it slot for slot.
//
// NOT memoized, deliberately: getCorpusCounts() above caches in a module local
// and is therefore untestable across fixtures. The expensive read
// (flow_chart.json) is memoized in lib/data instead.

export interface CrosswalkCount {
  /** Stable id — the gate's key and the row's DOM hook. */
  id: string;
  value: number;
  /** Where the number is published. */
  where: string;
  /** What ONE unit of this count is. */
  counts: string;
}

export const CROSSWALK_COUNT_IDS = [
  "link-universe",
  "bridged-request",
  "high-confidence-links",
  "district-linkable",
  "district-linkable-unbridged",
] as const;

export function getCrosswalkCounts(): CrosswalkCount[] {
  const b = getFlowChartMeta().bridge;
  const rows: CrosswalkCount[] = [
    {
      id: "link-universe",
      value: b.universePeCount,
      where: "the /flow/ bridge, and Coverage",
      counts:
        "Program elements with a published budget→award link, at any tier.",
    },
    {
      id: "bridged-request",
      value: b.crosswalkedPeCount,
      where: "the /flow/ bridge band",
      counts:
        "Of those, the ones also carrying FY2026 request dollars — all the river can draw.",
    },
    {
      id: "high-confidence-links",
      value: b.highConfidencePeCount,
      where: "the /flow/ bridge note",
      counts:
        "Of the bridged, the ones with a high-confidence link.",
    },
    {
      id: "district-linkable",
      value: getFlowsCount(),
      where: "Districts, Coverage, and program pages",
      counts:
        "Elements with a follow-the-dollar view: a high-confidence link naming a place of performance.",
    },
    {
      id: "district-linkable-unbridged",
      value: getFlowsOutsideBridgeCount(),
      where: "this list",
      counts:
        "Of those, the ones with no FY2026 request dollars — why the two ratios differ.",
    },
  ];
  const by = (id: string) => rows.find((r) => r.id === id)!;
  // Only the containments that are true BY CONSTRUCTION are asserted.
  // district-linkable vs high-confidence-links is deliberately NOT one of
  // them: the two tiers differ in both directions (place of performance vs
  // FY2026 request dollars), and the unbridged sidecars prove it.
  const nested: [string, string][] = [
    ["bridged-request", "link-universe"],
    ["high-confidence-links", "bridged-request"],
    ["district-linkable", "link-universe"],
    ["district-linkable-unbridged", "district-linkable"],
  ];
  for (const [inner, outer] of nested) {
    if (by(inner).value > by(outer).value) {
      throw new Error(
        `[govbudget/corpus] ${inner} (${by(inner).value}) exceeds ${outer} ` +
          `(${by(outer).value}). ${inner} is a subset of ${outer} by ` +
          `construction; one of the derivations no longer counts what its ` +
          `description says.`,
      );
    }
  }
  return rows;
}
