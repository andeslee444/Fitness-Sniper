import type { Metadata } from "next";
import Link from "next/link";
import { getDistrictIndex, getProgramsCount } from "@/lib/data";
import { crosswalkValue } from "@/lib/corpus";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { coreOgImages } from "@/lib/og";
import { exactTitle, formatAmountNoCurrency, formatCount } from "@/lib/format";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageIntro } from "@/components/page-intro";
import { CitationPanelProvider } from "@/components/citation-panel";
import { Cite } from "@/components/cite";
import { CoverageNote } from "@/components/coverage-note";
import { ScopeNote } from "@/components/notes";
import { DistrictTable } from "@/components/district-table";
import { FyRange } from "@/components/fy-range";
import styles from "./district-directory.module.css";

// Grouped through the shared count formatter — "17 of 1,741", never
// "17 of 1741" (fix round: the page mixed both notations against the
// "1,993"/"1,741" the corpus statement uses elsewhere).
//
// ONE declaration of what "crosswalked" counts — lib/corpus
// getCrosswalkCounts(), read through its own accessor (Task 26: this was a
// local `find(...)!.value`, which threw a TypeError on a typo where the
// accessor throws a named error). The number here is the district-linkable
// tier (a high-confidence award obligating money at a recorded place of
// performance — one flows sidecar, and one program page drawing it, each);
// /flow/ publishes the bridge tier, which is a different question, and
// /coverage/#crosswalk reconciles the two.
const _linkable = crosswalkValue("district-linkable");
const _flowsCount = formatCount(_linkable);
const _programsCount = formatCount(getProgramsCount());
const _unlinkedCount = formatCount(getProgramsCount() - _linkable);

export const metadata: Metadata = {
  title: "Congressional Districts",
  // Task 26: "whose awards are linked at high confidence" named the wrong
  // set — ~100 more elements carry high-confidence links whose awards record
  // no place of performance; this count is the ones with a view.
  description: `Defense spending by congressional district — programs, recipients, and awarded dollars, for the ${_flowsCount} of ${_programsCount} program elements with a follow-the-dollar view.`,
  alternates: { canonical: `${SITE_URL}/district/` },
  openGraph: {
    title: `Congressional Districts — ${SITE_NAME}`,
    description:
      "Defense spending by congressional district — programs, recipients, and awarded dollars for the budget lines with a follow-the-dollar view.",
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
        {/* 2026-09-25 integration: the editorial redesign's masthead
            (eyebrow, title, description, actions, the #district-directory
            anchor) over this branch's lede and stat cards. The lede keeps
            its reviewed count ("have a follow-the-dollar view", Task 26) —
            the redesign's "have documented budget-to-award links" named the
            wrong set (~100 more elements carry high-confidence links whose
            awards record no place of performance). */}
        {/* Below `sm` the masthead is tightened and the stat tiles become one
            ledger (district-directory.module.css), so the first district row
            is inside the 390x844 fold (gate 16, index-fold leg). Every
            sentence and figure stays where it was. */}
        <PageIntro eyebrow="Local connections" title="Follow the evidence to your district."
          className={styles.intro}
          description="Find the programs connected to a place through documented defense contract awards."
          actions={<><a href="#district-directory">Find a district</a><Link href="/coverage/#crosswalk">How programs connect to awards</Link></>}>
          <h2 className="sr-only">Congressional Districts</h2>
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
              they qualify. Their wording has changed since, separately:
              a1e8dc86 rewrote the scope note, b41561c7 the reconciliation
              lead-in (whose pointer at "the table below" the move would have
              made false — this page's own round-1 ruling: named, not placed),
              and Task 26 the scope note's mechanism sentence. The stat cards
              stay — they are data. */}
          {/* The stat row, reconciled.
              Two figures ~457× apart sat side by side with nothing relating
              them, and "all-district" read as "the 106 districts shown" when
              it means every U.S. district in the award data. The '$' was also
              missing from the middle card — on the page whose §P1-6 fix was a
              formatter. Each card now states its universe; the
              reconciliation paragraph under the table states the relationship
              in one sentence. */}
          <div className={`grid grid-cols-2 gap-4 sm:grid-cols-3 text-sm mb-2 ${styles.stats}`}>
            <div className={`rounded-lg border border-border bg-card p-4 ${styles.tile}`}>
              <p className={`t-figure t-figure--5 ${styles.tileFigure}`}>
                {index.total_districts}
              </p>
              <p className={`text-muted-foreground text-xs mt-1 ${styles.tileLabel}`}>
                districts with at least one crosswalked program
              </p>
            </div>
            <div className={`rounded-lg border border-border bg-card p-4 ${styles.tile}`}>
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
              <p className={`t-figure t-figure--5 ${styles.tileFigure}`}>
                <span data-figure-suffix className="align-baseline">USD </span>
                {formatAmountNoCurrency(totalLinkable, "USD")}
              </p>
              <p className={`text-muted-foreground text-xs mt-1 ${styles.tileLabel}`}>
                linkable to a budget program, in these{" "}
                {index.total_districts} districts <FyRange separator="· " />
              </p>
            </div>
            {index.geo_grand_total !== null && (
              <div className={`rounded-lg border border-border bg-card p-4 ${styles.tile}`}>
                <p className={`t-figure t-figure--5 ${styles.tileFigure}`}>
                  {/* Same notation as the middle card (see its note): "USD"
                      outside the [data-amount] span at the same size, the
                      magnitude inside it. `display` re-notates the SAME value
                      — never a different one — so `title` is passed
                      explicitly to keep the exact-dollars hover text that
                      formatAmount's default would have produced. */}
                  <span data-figure-suffix className="align-baseline">USD </span>
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
                <p className={`text-muted-foreground text-xs mt-1 ${styles.tileLabel}`}>
                  awarded across <strong>every</strong> U.S. district, linked
                  to a program or not <FyRange separator="· " />
                </p>
              </div>
            )}
          </div>
        </PageIntro>

        {/* [data-first-data] marks the block gate 16's index-fold leg measures.
            It measures the first ROW inside it, not the block's own top: a
            table's top is its header, and a reader who can see only a header
            has not seen data. #district-directory is the masthead's jump
            target. */}
        <div id="district-directory" data-first-data className="scroll-mt-24">
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
              14 DARPA that day; 139 / 88 / 56 against 14 on run 4); gate 24
              leg (p3) recomputes that mix rather than trusting this comment.

              Task 26 (final review): the next sentence was a disjunction — "a
              contract announcement that names the program, or an account plus
              program-specific tokens" — that stopped covering the tier it
              described: on run 4 it left out the 25 adjudicator-pinned
              account (3) and account+subagency (22) links of the 1,133
              published at high, and "names the program" claims more than
              /methodology/ §4 does for an announcement link whose match basis
              went unrecorded (326 of 1,074). It now says what every high link
              shares — more than an account code ties it — and points at §4
              for what that evidence is, so no tier change can quietly falsify
              an enumeration here.

              The complement is the pages with NO VIEW (programs.json rows −
              district-linkable, which gate 24 leg (p2) admits). It said "no
              district-level linkage", which is 3 fewer on run 4: 356010,
              845550 and 9140MA7804 have district rows but no positive linked
              obligation at any of them, so they appear on district pages yet
              draw no view (the exporter writes a sidecar only for a positive
              one).
              Integration 2026-09-25 (R-INT-7): the reason sat between two
              em dashes (gate 27 leg 13, VOICE.md rule 14). It is now its own
              sentence after the claim it supports, 4 characters shorter, so
              the 390px fold (gate 16) cannot lose a line to it. */}
          <p>
            District data reflects only high-confidence award crosswalk
            links. A budget line earns one only where more than an account
            code ties the award to it;{" "}
            <Link
              href="/methodology/#crosswalk-confidence"
              className="underline hover:text-foreground"
            >
              methodology §4
            </Link>{" "}
            says what does. {_unlinkedCount} of {_programsCount} program
            elements have no follow-the-dollar view. That is a limit of what
            the award records contain, not a queue position. One appropriation
            account funds dozens to hundreds of program elements.
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
            {/* Fix-wave round 2 (B1): the sentence below tied the linkable
                subtotal to "— {_flowsCount} of {_programsCount} programs —",
                the programs with a view. The subtotal sums the district
                table's rows, which span 317 programs on run 4: 356010, 845550
                and 9140MA7804 carry only zero or negative obligations there
                and draw no view. The count went (the lede above states the
                view ratio) rather than a second, undeclared one arriving. */}
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
            budget program through the crosswalk, so it is a subset of the
            same universe, roughly{" "}
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
