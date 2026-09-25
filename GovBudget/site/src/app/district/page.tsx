import type { Metadata } from "next";
import Link from "next/link";
import { getDistrictIndex, getProgramsCount } from "@/lib/data";
import { getCrosswalkCounts } from "@/lib/corpus";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { coreOgImages } from "@/lib/og";
import { exactTitle, formatAmountNoCurrency, formatCount } from "@/lib/format";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { CitationPanelProvider } from "@/components/citation-panel";
import { Cite } from "@/components/cite";
import { CoverageNote } from "@/components/coverage-note";
import { ScopeNote } from "@/components/notes";
import { DistrictTable } from "@/components/district-table";
import { FyRange } from "@/components/fy-range";

// Grouped through the shared count formatter — "17 of 1,741", never
// "17 of 1741" (fix round: the page mixed both notations against the
// "1,993"/"1,741" the corpus statement uses elsewhere).
//
// ONE declaration of what "crosswalked" counts — lib/corpus
// getCrosswalkCounts(). The number here is the district-linkable tier (a
// high-confidence link whose award records a place of performance); /flow/
// publishes the bridge tier, which is a different question, and
// /coverage/#crosswalk reconciles the two.
const _linkable = getCrosswalkCounts().find((c) => c.id === "district-linkable")!.value;
const _flowsCount = formatCount(_linkable);
const _programsCount = formatCount(getProgramsCount());
const _unlinkedCount = formatCount(getProgramsCount() - _linkable);

export const metadata: Metadata = {
  title: "Congressional Districts",
  description: `Defense spending by congressional district — programs, recipients, and awarded dollars, for the ${_flowsCount} of ${_programsCount} program elements whose awards are linked at high confidence.`,
  alternates: { canonical: `${SITE_URL}/district/` },
  openGraph: {
    title: `Congressional Districts — ${SITE_NAME}`,
    description:
      "Defense spending by congressional district — programs, recipients, and awarded dollars for the budget lines whose awards are linked at high confidence.",
    url: `${SITE_URL}/district/`,
    siteName: SITE_NAME,
    images: coreOgImages("district-index"),
  },
};

export default function DistrictIndexPage() {
  const index = getDistrictIndex();

  const totalLinkable = index.districts.reduce(
    (sum, d) => sum + d.total_linkable_dollars,
    0,
  );

  return (
    // §P2-1 page weight (Task 28b): citations resolve LAZILY through
    // cite-shards, so the provider mounts with an EMPTY embedded slice — the
    // same treatment, for the same reason, as /district/{code}/ (see its note)
    // and /programs/. The slice this page built held the grand total plus
    // every row's linkable-dollars citation: 190 derived rows, 168,934 of the
    // page's 447,757 raw bytes on chain C run 2's build. Every cited figure is
    // still a state-A <Cite>, so a click opens its citation from the shard.
    // Nothing drillable is lost: a row's inputs are that district's program
    // rows, which this page never embedded, so its input chips were already
    // plain; the grand total's citation has no fact-id inputs at all. That is
    // also why this page, unlike /district/{code}/, passes no
    // shardResolvableIds (R-28b-4): none of the 599 inputs on its 180 row
    // cards of that build is a figure it renders, so listing its own ids
    // would make no chip clickable.
    <CitationPanelProvider citations={{}}>
      <div className="spine py-8">
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: "Congressional Districts" },
          ]}
        />
        <div className="page-header mb-6">
          <h1 className="text-3xl font-bold mb-2">Congressional Districts</h1>
          <p className="text-muted-foreground mb-2">
            {index.total_districts} districts with linkable defense obligations
            — {_flowsCount} of {_programsCount} program elements have a
            follow-the-dollar view.{" "}
            <Link
              href="/coverage/#crosswalk"
              className="underline decoration-dotted hover:decoration-solid"
            >
              How the crosswalk counts differ →
            </Link>
          </p>
          {/* The coverage note, the scope note and the reconciliation
              paragraph used to sit here, between the heading and the table.
              21d moved all three directly under <DistrictTable>, which is what
              they qualify; nothing was cut, and the one reworded clause is the
              reconciliation paragraph's pointer at "the table below", which
              the move would have made false (this page's own round-1 ruling:
              named, not placed). The stat cards stay — they are data. */}
          {/* The stat row, reconciled.
              Two figures ~457× apart sat side by side with nothing relating
              them, and "all-district" read as "the 106 districts shown" when
              it means every U.S. district in the award data. The '$' was also
              missing from the middle card — on the page whose §P1-6 fix was a
              formatter. Each card now states its universe; the
              reconciliation paragraph under the table states the relationship
              in one sentence. */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 text-sm mb-2">
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="text-2xl font-bold tabular-nums">
                {index.total_districts}
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                districts with at least one crosswalked program
              </p>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              {/* §P1-6: was a hand-rolled `(total / 1e9).toFixed(1)}B` that
                  bypassed the shared ladder entirely. The no-currency
                  formatter is still the right one — a bare '$…' outside a
                  [data-amount] span is what the render-static currency gate
                  flags — so the currency sits in the label, spelled out, next
                  to the number rather than only under it.

                  FIX ROUND: the neighbouring card then read "$3.66T" while
                  this one read "USD 8.01B", so two figures meant to be
                  compared carried two currency notations. Both cards now use
                  the SAME one — the spelled-out "USD" at text-lg followed by
                  the compact magnitude — and the only visible difference left
                  between them is the cited card's underline and its chip,
                  which is a real difference (see the reconciliation line). */}
              <p className="text-2xl font-bold tabular-nums">
                <span className="text-lg align-baseline">USD </span>
                {formatAmountNoCurrency(totalLinkable, "USD")}
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                linkable to a budget program, in these{" "}
                {index.total_districts} districts <FyRange separator="· " />
              </p>
            </div>
            {index.geo_grand_total !== null && (
              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-2xl font-bold tabular-nums">
                  {/* Same notation as the middle card (see its note): "USD"
                      outside the [data-amount] span at the same size, the
                      magnitude inside it. `display` re-notates the SAME value
                      — never a different one — so `title` is passed
                      explicitly to keep the exact-dollars hover text that
                      formatAmount's default would have produced. */}
                  <span className="text-lg align-baseline">USD </span>
                  <Cite
                    value={index.geo_grand_total}
                    units="USD"
                    dataset={index.geo_grand_total_dataset}
                    factId={index.geo_grand_total_fact_id}
                    display={formatAmountNoCurrency(index.geo_grand_total, "USD")}
                    title={exactTitle(index.geo_grand_total, "USD")}
                  />
                </p>
                {/* §P1-6: this is $3.66T — a DECADE of award obligations. It
                    rendered "$3657.4B" with no period beside an "8.0B" card,
                    which reads as one year's spending. Both now carry the
                    derived range. */}
                <p className="text-muted-foreground text-xs mt-1">
                  awarded across <strong>every</strong> U.S. district, linked
                  to a program or not <FyRange separator="· " />
                </p>
              </div>
            )}
          </div>
        </div>

        {/* [data-first-data] marks the block gate 16's index-fold leg measures.
            It measures the first ROW inside it, not the block's own top: a
            table's top is its header, and a reader who can see only a header
            has not seen data. */}
        <div data-first-data>
          <DistrictTable districts={index.districts} />
        </div>

        {/* Scope note — G2 contract (data-coverage="districts") */}
        <CoverageNote id="districts" className="mt-6 mb-3" />
        {/* §P2-6: scope disclosure, not a warning. Same words, calm
            register — the amber is reserved for caution about a number. */}
        <ScopeNote className="mb-4" label="Coverage note">
          {/* The mechanism, not an organization. This said the linkage was
              a "DARPA crosswalk" until 2026-09-18, which the shipped flow
              sidecars contradict (92 Navy / 59 Air Force / 22 Army against
              14 DARPA); gate 24 leg (p3) recomputes that mix rather than
              trusting this comment. The tier is NOT described as
              hand-adjudicated: 708 of the 768 links published at high come
              from the announcement path, which carries no per-link
              adjudication (ROADMAP #109).

              WHAT THE DISJUNCTION BELOW LEAVES OUT, measured 2026-09-18 off
              site_meta.link_adjudication.high.by_path: "an announcement that
              names the program" is announcement+lexicon (708) and "an account
              plus program-specific tokens" is account+tokens (34) — 742 of the
              768 links published at high. The other 26 are adjudicator-pinned
              account matches: account (3) and account+subagency (23), both
              two-lens on every link. They are omitted deliberately — naming a
              third path here would cost more than it tells a district reader,
              and /methodology/ §4 states the full tier composition — but they
              ARE links this sentence does not describe, so if that ratio moves
              much off 742/768, re-word rather than leaving the reader with a
              disjunction that has quietly stopped covering the tier. */}
          <p>
            District data reflects only high-confidence award crosswalk
            links. A budget line earns one only where the award record says
            more than an account code: a contract announcement that names the
            program, or an account plus program-specific tokens.{" "}
            {_unlinkedCount} of {_programsCount} program elements have no
            district-level linkage. That is a limit of what the award records
            contain — one appropriation account funds dozens to hundreds of
            program elements — and not a queue position.
          </p>
        </ScopeNote>
        {index.geo_grand_total !== null && (
          <p
            data-district-reconciliation
            className="mb-4 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs leading-relaxed text-muted-foreground"
          >
            <strong className="text-foreground">
              How the every-U.S.-district total and the
              linkable-to-a-budget-program figure relate:
            </strong>{" "}
            {/* Round-1 judging: this said "right-hand" and "middle", which
                is only true at desktop — below `sm` the three cards restack
                2-then-1, putting the grand total bottom-left and the
                linkable subtotal top-right. Both pointers were wrong on the
                page's most trust-critical paragraph. Named, not placed. */}
            the{" "}
            <em className="not-italic font-medium text-foreground">
              every U.S. district
            </em>{" "}
            total is all defense award obligations recorded with a
            congressional district over the period. The{" "}
            <em className="not-italic font-medium text-foreground">
              linkable to a budget program
            </em>{" "}
            figure is the small slice of it we can tie back to a specific
            budget program through the crosswalk — {_flowsCount} of{" "}
            {_programsCount} programs — so it is a subset of the same
            universe, roughly{" "}
            {(
              (totalLinkable / (index.geo_grand_total || 1)) *
              100
            ).toFixed(2)}
            % of it, not a competing measurement of it. The gap is coverage,
            not disagreement. Only the every-U.S.-district figure is
            fact-backed
            today: the district count and the linkable subtotal are computed
            over the rows of the district table, each of which carries its own
            citation.
          </p>
        )}

        <p className="mt-4 text-xs text-muted-foreground">
          Dollars are from high-confidence USAspending award links only.
          The geography grand total aggregates USAspending award transaction
          data across all districts — click it for the formula and query.
          See{" "}
          <Link href="/methodology/" className="underline hover:text-foreground">
            methodology
          </Link>
          .
        </p>
      </div>
    </CitationPanelProvider>
  );
}
