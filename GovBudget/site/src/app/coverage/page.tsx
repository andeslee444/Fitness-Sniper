import type { Metadata } from "next";
import Link from "next/link";

import { Breadcrumbs } from "@/components/breadcrumbs";
import { DocToc } from "@/components/doc-toc";
import { ScopeNote } from "@/components/notes";
import {
  getCoverageMap,
  CROSSWALK_LIMIT_ID,
  FILE_C_NOTE,
  MAP_REVIEWED_ON,
} from "@/lib/coverage-map";
import { getCorpusCounts, getCrosswalkCounts } from "@/lib/corpus";
import { coreOgImages } from "@/lib/og";
import { SITE_NAME, SITE_URL } from "@/lib/site";

/**
 * /coverage/ — what this site covers, what it does not, and when that changes
 * (PM-review Sprint 3 Task 6, §Coverage).
 *
 * "The honesty is right, the roadmap is missing." Every gap is already
 * disclosed at the point of use; what nobody could see was whether the site is
 * early and moving or abandoned at 1%. This page is that missing half — and
 * because it is a page ABOUT coverage, it is the one page on which a hardcoded
 * count would be self-refuting. Every figure comes from lib/coverage-map,
 * which reads the shipped sidecars; gate 14's coverage-map leg recomputes all
 * of them from those same artifacts and fails the build on a mismatch.
 *
 * REGISTER (§P2-6): this page is scope disclosure end to end, so it uses the
 * calm <ScopeNote> register throughout and never the amber caution treatment —
 * amber is reserved for "this specific number needs care".
 *
 * MOBILE: the table becomes a stack of cards below `sm` (the /data/ pattern) —
 * one DOM, restyled, so the gate hooks and header semantics are unchanged and
 * nothing scrolls off the right edge at 390px.
 *
 * TARGETS ARE UNDATED (Sprint 3 round 3, the site owner's decision). The first
 * cut published eight dates the project had never committed to. They are gone;
 * every blocker is kept verbatim, and each row now says there is no dated
 * target, names the work that is planned, and — where work is planned — says
 * plainly that it is not scheduled. A site that will not publish a figure it
 * cannot recompute should not publish a schedule it has not agreed to either.
 *
 * 2026-09-18: "the date is pending a roadmap decision" is retired from this
 * page. It promised the reader a decision was coming on seven items that were
 * filed nowhere; see COVERAGE_PROMISE_IDS in lib/coverage-map.
 */

const _rows = getCoverageMap();

export const metadata: Metadata = {
  title: "Coverage — what this site does and does not cover",
  description:
    `Coverage and the specific blocker behind it for all ${_rows.length} datasets and features on ${SITE_NAME}. ` +
    "Every figure is recomputed from the shipped data at build time, including the budget→award crosswalk gap.",
  alternates: { canonical: `${SITE_URL}/coverage/` },
  openGraph: {
    title: `Coverage — what this site does and does not cover | ${SITE_NAME}`,
    description:
      "Per-feature coverage with the specific blocker standing in the way of each — and a plain statement of the one gap that is a methodology limit rather than a backlog item.",
    url: `${SITE_URL}/coverage/`,
    siteName: SITE_NAME,
    images: coreOgImages("coverage"),
  },
};

export default function CoveragePage() {
  const rows = getCoverageMap();
  const crosswalk = rows.find((r) => r.id === CROSSWALK_LIMIT_ID)!;
  const counts = getCorpusCounts();
  const crosswalkCounts = getCrosswalkCounts();
  const dated = rows.filter((r) => r.targetKind === "dated").length;

  return (
    <div className="spine py-8">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Coverage" }]} />

      {/* <h1> FIRST — gate 2 (nk) pins that no scope block precedes it. */}
      <h1 className="mb-3 text-3xl font-bold">Coverage</h1>
      <div className="doc-layout">
        <div data-doc-prose>
          {/* Trimmed 2026-09-18 to pay for the File C sentences below. What
              went: "— including, in plain words, why no row here carries a
              date", a promise the paragraph under the table keeps in the same
              breath as it explains the policy. 21d's move is untouched; this
              is the lede's own redundancy, and shortening it can only help
              the index-fold leg. */}
          <p className="leading-7 text-muted-foreground">
            What this site covers, what it does not, and what would have to change
            for that to move. Each row gives the coverage this build actually
            shipped, the specific thing standing in the way, and where the work
            stands.
          </p>

          {/* The "recomputed at build time" panel used to sit here, and the
              dated-target paragraph sat under the "Feature by feature"
              heading. Both qualify the map table, so 21d moved both directly
              under it; nothing was cut or reworded. The lede above and the
              <h2> stay — they introduce the table rather than qualifying it.
              Byte note: this is a move, not an addition, on a page whose
              ceiling had ~430 gzip of headroom then (its gzip ceiling was
              raised once later, under R-D-2 in chain D). */}

          {/* ── The map ─────────────────────────────────────────────────────── */}
          {/* [data-first-data] marks the block gate 16's index-fold leg
              measures. It measures the first ROW inside it, not the block's
              own top: a table's top is its header, and a reader who can see
              only a header has not seen data. */}
          <section
            data-first-data
            className="mt-10"
            aria-labelledby="map-heading"
          >
            <h2 id="map-heading" className="mb-3 text-xl font-semibold">
              Feature by feature
            </h2>
            {/* MOBILE: below `sm` each row becomes a card (the /data/ treatment),
                so the Blocker and Target columns — the whole point of the page —
                stay on screen at 390px instead of scrolling off behind the
                container. Same <table>, restyled; roles are declared where the
                display override would otherwise drop them. */}
            <div className="overflow-x-auto rounded-lg border border-border">
              <table
                data-coverage-map
                className="min-w-full text-sm"
              >
                <caption className="sr-only">
                  Coverage, blocker and target for each dataset and feature on{" "}
                  {SITE_NAME}.
                </caption>
                <thead className="hidden sm:table-header-group">
                  <tr className="border-b border-border bg-muted/50">
                    <th scope="col" className="px-4 py-2 text-left font-semibold text-muted-foreground">
                      Feature
                    </th>
                    <th scope="col" className="px-4 py-2 text-left font-semibold text-muted-foreground">
                      Coverage today
                    </th>
                    <th scope="col" className="px-4 py-2 text-left font-semibold text-muted-foreground">
                      What is in the way
                    </th>
                    <th scope="col" className="px-4 py-2 text-left font-semibold text-muted-foreground">
                      Target
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr
                      key={r.id}
                      data-coverage-row={r.id}
                      data-covered-n={r.numerator ?? undefined}
                      data-covered-d={r.denominator ?? undefined}
                      role="row"
                      className="block border-b border-border py-4 last:border-0 sm:table-row sm:py-0"
                    >
                      <th
                        scope="row"
                        className="block px-4 py-0 text-left align-top text-base font-semibold text-foreground sm:table-cell sm:py-3 sm:text-sm sm:whitespace-nowrap"
                      >
                        <Link href={r.href} className="underline decoration-dotted hover:text-primary">
                          {r.label}
                        </Link>
                      </th>
                      <td
                        role="cell"
                        data-primary-value="covered"
                        className="block px-4 pt-1 align-top sm:table-cell sm:py-3"
                      >
                        <span className="text-foreground">{r.covered}</span>
                        <span className="mt-1 block text-xs text-muted-foreground">
                          Derived from {r.derivation}
                        </span>
                      </td>
                      <td
                        role="cell"
                        data-coverage-blocker
                        className="block px-4 pt-2 align-top text-muted-foreground sm:table-cell sm:py-3"
                      >
                        <span className="mb-0.5 block text-[11px] font-semibold uppercase tracking-widest text-foreground/60 sm:hidden">
                          In the way
                        </span>
                        {r.blocker}
                      </td>
                      <td
                        role="cell"
                        data-coverage-target
                        data-target-kind={r.targetKind}
                        className="block px-4 pt-2 align-top text-muted-foreground sm:table-cell sm:py-3"
                      >
                        <span className="mb-0.5 block text-[11px] font-semibold uppercase tracking-widest text-foreground/60 sm:hidden">
                          Target
                        </span>
                        {r.target}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <p className="mt-4 text-sm text-muted-foreground">
            {dated === 0
              ? "No row on this page carries a dated target, and that is a decision rather than an omission: a site that will not publish a figure it cannot recompute should not publish a schedule it has not committed to. Each row instead names either the planned work, saying plainly that it is not scheduled, or the limit of the sources behind the gap. When a date is agreed it is added here — and a date that slips is moved here, not deleted."
              : `${dated} of the ${rows.length} rows carry a dated target; the rest say why they do not, and a date that slips is moved here rather than deleted.`}{" "}
            Every figure above is recomputed at build time. The wording around
            them — blockers, targets, the reasons a row carries no date — is
            written by hand and was last reviewed on{" "}
            <time dateTime={MAP_REVIEWED_ON}>{MAP_REVIEWED_ON}</time>.
          </p>

          <ScopeNote className="mt-6" label={null}>
            {/* Task 26: this said "Every number on this page", and the File C
                note below renders a dated one-off spike sample (44 links,
                81%) that nothing recomputes. Scoped to what the gate does
                recompute — 4 characters shorter. */}
            <h2 className="mb-2 text-lg font-semibold text-foreground">
              Every coverage figure is recomputed at build time
            </h2>
            {/* Trimmed 2026-09-18 to pay for the File C sentences below. What
                went: "Nothing here is typed by hand." (the <h2> directly above
                says it) and "The derivation for each row is printed beside
                it." (every row visibly prints "Derived from …"). Both were
                restatements of things already on the page; no claim was
                dropped. */}
            {/* Chain-D fix round 1 (R-D-2b) took §22a's third trim here —
                "— the same files the pages themselves render from —" — on the
                grounds that the <h2> above already said where the figures come
                from. It does not: it claims RECOMPUTATION, not provenance, and
                with the clause gone nothing on the page said the coverage
                figures and the rest of the site read the SAME files. Fix round
                2 restores that identity one word shorter than the original
                ("themselves" went; 39 rendered characters, +88 raw and 14-20
                gzip, measured). The warrant is coverage-map.ts's
                own header: every `covered` string is assembled from the
                data.ts / feeds.ts loaders the pages themselves render from. */}
            <p className="text-sm leading-7">
              Each coverage figure is read from the data files this build
              shipped — the same files the pages render from — and a
              build-time gate recomputes all{" "}
              {rows.length} rows independently and fails the build if any rendered
              figure disagrees with its source. A coverage page carrying a
              stale literal would refute its own argument, so this one is not
              allowed to carry any.
            </p>
            {/* Same 2026-09-18 trim: "— and an unverifiable number on this
                page would be worse than a missing one" was the paragraph
                above's "A coverage page carrying a stale literal would refute
                its own argument" in other words, two sentences apart. */}
            <p className="mt-3 text-sm leading-7">
              One figure is deliberately <em>absent</em> for the same reason: the
              share of award dollars whose recipient resolves to a corporate family.
              That is a warehouse query rather than a shipped file, so it cannot be
              recomputed at build time.
            </p>
          </ScopeNote>

          {/* ── How the corpus is counted (tri-persona Wave 4, item 4) ──────────
              Five true numbers, five denominators, and until now nothing that
              said so. Each row is derived from the artifact that defines it
              (lib/corpus getCorpusCounts; see the five-way list below); this
              page never states a count it did not recompute. Gate 24 leg k
              recomputes all five from the shipped artifacts and rejects any
              corpus-shaped number on
              the singleton pages that is not one of them. */}
          <section className="mt-12" aria-labelledby="counts-heading" id="corpus-counts">
            <h2 id="counts-heading" className="mb-3 text-xl font-semibold">
              How the corpus is counted
            </h2>
            <p className="mb-4 text-sm leading-7 text-muted-foreground">
              Five nested questions; the differences are the point.
            </p>
            {/* A LIST, AND EVERY SHARED CLASS ON THE <ul>. The table form of this
                block cost 10,794 raw bytes and put the page 288 gzip over its
                ceiling; per-row class strings then cost another 841 raw, because
                the RSC payload carries each one a second time. Nothing was
                trimmed from the disclosure — all five counts and all five
                explanations are here; the markup around them is.
                data-measure="prose-box": five sentences in a padded, marker-less
                box take the reading measure (globals.css, the note-register
                rule) — 132 characters per line without it, and gate 3 leg (s2)
                now measures marker-less items (#42 residue). */}
            <ul
              data-corpus-counts
              data-measure="prose-box"
              className="divide-y divide-border rounded-lg border border-border text-sm text-muted-foreground [&>li]:px-4 [&>li]:py-3 [&_strong]:tabular-nums [&_strong]:text-foreground"
            >
              {counts.map((c) => (
                <li key={c.id} data-corpus-count={c.id}>
                  <strong data-corpus-value>
                    {c.value.toLocaleString("en-US")}
                  </strong>{" "}
                  on {c.where}. {c.counts}
                </li>
              ))}
            </ul>
          </section>

          {/* ── The crosswalk: a methodology limit, not a backlog item ───────── */}
          <section className="mt-12" aria-labelledby="crosswalk-heading" id="crosswalk">
            <h2 id="crosswalk-heading" className="mb-3 text-xl font-semibold">
              The budget→award crosswalk is a methodology limit, not a backlog item
            </h2>
            {/* Trimmed 2026-09-18 to pay for the File C note below. What went:
                "and what kind of gap it is matters: not work we have not got
                to, but a limit of what the source records contain" — the <h2>
                directly above it says exactly that, and so does the target
                paragraph further down. */}
            {/* DEDUPE 2026-09-18 (chain-D fix round 1, R-D-2a). The bridge
                row's blocker and target rendered TWICE on this page — once in
                the map table's cells above and again here, verbatim — and a
                page that states one thing twice is a page that will eventually
                state it two ways (§P0-2). The long form stays in the TABLE
                CELL, because that is where gate 14 leg cm reads it:
                coverage.mjs finds the row by [data-coverage-row="bridge"],
                then pins its
                four phrases (account-code coarseness, hand adjudication, the
                adversarial step, and that step BOUND to the links carrying a
                per-award adjudication) inside [data-coverage-blocker], with
                MIN_BLOCKER_CHARS/MIN_TARGET_CHARS floors on the same cells.
                This section points at it instead. Not one word of either
                string changed — lib/coverage-map is untouched — and
                [data-coverage-crosswalk] below still restates the figure the
                leg compares. Measured on the built page: −2,424 raw. Gzip
                barely moves (−46), because the second copy compressed to a
                back-reference; raw is what a duplicate paragraph really
                costs. */}
            <p className="leading-7 text-muted-foreground">
              This is the site&apos;s largest gap; the crosswalk row of the
              table above states what is in the way, and why no target is
              dated.
            </p>
            {/* The File C negative result (spike 2026-09-01,
                docs/superpowers/reviews/filec-program-activity-spike.md). Its
                §Implications asks this page to say File C was examined and
                ruled out rather than staying silent on it. The link is OMB's
                domain list — the public evidence behind finding #1 — because
                the write-up itself is not a published page; the label says
                "64 MB CSV" because that is what the reader is about to get.
                It sits BELOW [data-first-data] (the map table), so it costs
                gate 16's index-fold leg nothing. */}
            <p className="mt-3 leading-7 text-muted-foreground">
              {FILE_C_NOTE.lead}
              <a
                href={FILE_C_NOTE.linkHref}
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-foreground"
              >
                {FILE_C_NOTE.linkLabel}
              </a>
              {FILE_C_NOTE.tail}
            </p>
            <p className="mt-3 leading-7 text-muted-foreground">
              So the honest boundary is this: we assert a budget→award link only
              where the record supports one, and we publish the size of the
              remainder rather than leaving it to be inferred from an empty chart.{" "}
              <Link href="/flow/#bridge" className="underline hover:text-foreground">
                The bridge
              </Link>{" "}
              states that remainder as a share of the request; in this build:{" "}
              {/* Same string as the row above, from the same source — the gate
                  compares the two, because a page that states one number twice is
                  a page that will eventually state it two ways (§P0-2). */}
              <span data-coverage-crosswalk>{crosswalk.covered}</span>
            </p>
            {/* PM-S3 leftover: "crosswalked" is published with two
                denominators — the bridge's and the district view's — and both
                are true. They are not nested, so each is stated with what one
                unit of it is. Same list form, same classes and same
                data-measure as #corpus-counts above (the 10.8KB table lesson,
                and the repeated attribute string costs almost nothing gzipped). */}
            <p className="mt-3 leading-7 text-muted-foreground">
              &ldquo;Crosswalked&rdquo; is published with two denominators, and
              they are not nested — so each is stated with what one unit of it
              is:
            </p>
            <ul
              data-crosswalk-counts
              data-measure="prose-box"
              className="mt-3 divide-y divide-border rounded-lg border border-border text-sm text-muted-foreground [&>li]:px-4 [&>li]:py-3 [&_strong]:tabular-nums [&_strong]:text-foreground"
            >
              {crosswalkCounts.map((c) => (
                <li key={c.id} data-crosswalk-count={c.id}>
                  {/* ONE text child after the <strong>, not four: React emits a
                      <!-- --> separator between adjacent text nodes, and the RSC
                      payload carries each child again. On a near-ceiling page
                      that framing costs ~300 raw bytes for no reader. */}
                  <strong data-crosswalk-value>
                    {c.value.toLocaleString("en-US")}
                  </strong>
                  {` on ${c.where}. ${c.counts}`}
                </li>
              ))}
            </ul>
          </section>

          {/* ── What this page is not ────────────────────────────────────────── */}
          <section className="mt-12" aria-labelledby="not-heading">
            <h2 id="not-heading" className="mb-3 text-xl font-semibold">
              Where coverage is stated elsewhere
            </h2>
            <p className="leading-7 text-muted-foreground">
              Every one of these gaps is also disclosed where a reader meets it: on
              the page, beside the figure, with a link to the reasoning. This page
              collects them so the shape of the whole is visible at once. For the
              definitions behind the numbers — confidence tiers, the supersede
              policy, and the nine named limitations — see the{" "}
              <Link href="/methodology/" className="underline hover:text-foreground">
                methodology
              </Link>
              . For the datasets themselves, with row counts read from the shipped
              parquet files, see{" "}
              <Link href="/data/" className="underline hover:text-foreground">
                the data explorer
              </Link>
              .
            </p>
          </section>
        </div>
        <DocToc />
      </div>
    </div>
  );
}
