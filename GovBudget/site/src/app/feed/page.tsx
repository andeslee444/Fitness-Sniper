import { ReviewedBriefings } from "@/components/reviewed-briefings";
import { WatchFeed } from "@/components/watch-feed";
import type { Metadata } from "next";
import Link from "next/link";
import {
  getFeed,
  getEntityTopByFamilyKey,
  getProgramPeBlis,
  getSiteMeta,
} from "@/lib/data";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { coreOgImages } from "@/lib/og";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { CitationPanelProvider } from "@/components/citation-panel";
import { Reveal } from "@/components/reveal";
import { FeedCardItem } from "@/components/feed-card-item";
import { FeedSectionExpand } from "@/components/feed-section-expand";
import { feedPageAlternates, feedLinks, eventTypeFeedPaths } from "@/lib/feeds";
import {
  WHOLE_FEED_RSS,
  WHOLE_FEED_ATOM,
  feedGuid,
  feedProgramKey,
} from "@/lib/feed-model.mjs";
import type { FeedCard, FeedSidecar } from "@/lib/data";
import { formatCount } from "@/lib/format";
import { HHI_BANDS_VINTAGE, HHI_CONCENTRATED_MIN, HHI_MODERATE_MIN } from "@/lib/hhi-band.mjs";
import { PageIntro } from "@/components/page-intro";

// Event type metadata: display name, description, methodology anchor.
const EVENT_META: Record<
  string,
  { label: string; description: string; anchorId: string }
> = {
  yoy_swing: {
    label: "Year-over-Year Swings",
    description:
      "Programs with FY2025 budget ≥ $50M that changed by ≥ 50% going into FY2026. Large swings signal major policy or requirements shifts.",
    anchorId: "feed-yoy_swing",
  },
  zeroed_fy2026: {
    label: "Zeroed in FY2026",
    // Sprint 3 Task 1b: this section previously claimed a zeroing whenever a
    // program was ABSENT from the FY2026 extract — 87 cards, none of them a
    // real zero. The predicate now demands a literal zero in the workbooks,
    // which currently matches nothing, so the section renders only when a
    // genuine termination appears. The description must therefore describe
    // the evidence bar, not the old absence heuristic.
    description:
      "Programs the FY2026 budget workbooks record as literally zero after carrying FY2025 funding. Programs merely absent from the FY2026 columns are excluded — a blank cell usually means the program element was renumbered, not cancelled.",
    anchorId: "feed-zeroed_fy2026",
  },
  concentration_shift: {
    label: "Award Concentration Shifts",
    // Task 28 fix round 2: this used to say every card "falls in the DOJ/FTC
    // moderately or highly concentrated band". fct_feed_events has no HHI
    // floor — its only condition is `having sum(dollars) >= 5000000` over
    // high-confidence links' positive obligations — and 0605502E FY2017–2020
    // (HHI 437–892) render "Competitive" in chain C run 2's export. The
    // description states the mart's own universe, the band each card names
    // (hhiScopeNote), and the #70/#82 shared-code rule (_concentration_owner).
    description:
      "Programs whose high-confidence award links carry at least $5M in matched obligations (positive obligations only) in a fiscal year — one card per year, headlined by that year's Herfindahl-Hirschman Index (HHI) across contractor families, whatever its value. " +
      // R-DEC-132b: the bands' vintage and thresholds from hhi-band.mjs; the word below 1,000 is this site's. feed.mjs leg (l) reads it.
      `Each card names its band under the ${HHI_BANDS_VINTAGE}: moderately concentrated from ${formatCount(HHI_MODERATE_MIN)} to ${formatCount(HHI_CONCENTRATED_MIN)} and highly concentrated above ${formatCount(HHI_CONCENTRATED_MIN)}. Below ${formatCount(HHI_MODERATE_MIN)} the card says unconcentrated, this site's label for that range. ` +
      "On a budget line more than one program uses, only a program carrying every crosswalk link on the line, high or medium, gets a card. Each card is a one-year snapshot — it can land in a different band than the program's own pooled, all-years HHI, which that page publishes only where its high-confidence links clear the floor, and otherwise withholds.",
    anchorId: "feed-concentration_shift",
  },
  request_vs_actuals_gap: {
    label: "Largest Request-vs-Actuals Gaps",
    // Claim scoped EXACTLY to request-vs-actuals (Task 6 review advisory):
    // this section says nothing about request-vs-request changes.
    // "reported as actual total obligation authority", not "actually spent"
    // (visual-judge M6: TOA ≠ outlays).
    description:
      "The largest gaps between what a President's Budget asked for a fiscal year and what a later book reported as actual total obligation authority — the PB(N) request for FY N vs the PB(N+2) book's FY N actuals, ranked by absolute dollar gap across the loaded PB2017–PB2026 editions.",
    anchorId: "feed-request_vs_actuals_gap",
  },
  new_entrant: {
    label: "New Defense Contractors",
    description:
      "Companies or families whose first award in the DoD transaction data is FY2024 or later and whose total obligations exceed $1M. Early-stage signal of emerging vendors.",
    anchorId: "feed-new_entrant",
  },
};

// Order in which event types are displayed on the page.
// §P0-5: budget-figure superlative sections carry the corpus scope
// qualifier ONCE in the section header (not per card). Award-derived
// sections (concentration, new entrants) rank a different universe.
const SCOPED_EVENT_TYPES = new Set([
  "yoy_swing",
  "zeroed_fy2026",
  "request_vs_actuals_gap",
]);

const EVENT_ORDER: FeedCard["event_type"][] = [
  "yoy_swing",
  "zeroed_fy2026",
  "request_vs_actuals_gap",
  "concentration_shift",
  "new_entrant",
];

const EVENT_LABELS: Record<string, string> = Object.fromEntries(
  Object.entries(EVENT_META).map(([k, v]) => [k, v.label]),
);

export const metadata: Metadata = {
  title: "Anomaly Feed",
  description:
    "Automated signals from the defense budget: year-over-year swings, zeroed programs, award concentration shifts, and new contractors.",
  alternates: {
    canonical: `${SITE_URL}/feed/`,
    // §P1-8: autodiscovery for the whole feed AND for each event type this
    // page renders a section for — the feeds scripts/generate-feeds.mjs
    // wrote, resolved through the same membership rules.
    types: feedPageAlternates(EVENT_LABELS),
  },
  openGraph: {
    title: `Anomaly Feed — ${SITE_NAME}`,
    description:
      "Automated signals from the defense budget: year-over-year swings, zeroed programs, award concentration shifts, and new contractors.",
    url: `${SITE_URL}/feed/`,
    siteName: SITE_NAME,
    images: coreOgImages("feed"),
  },
};

/**
 * The subscribe affordance. Small by design — it sits beside a heading, not
 * as a banner — but present on the whole feed and on every section, because
 * §P1-8's point is that a reader on this beat wants the section, not the
 * firehose.
 */
function SubscribeLinks({
  paths,
  label,
  className,
}: {
  paths: { rss: string; atom: string };
  label: string;
  className?: string;
}) {
  return <div className={className}><WatchFeed urls={feedLinks(paths)} label={label} compact /></div>;
}

function groupByEventType(cards: FeedCard[]): Map<string, FeedCard[]> {
  const map = new Map<string, FeedCard[]>();
  for (const card of cards) {
    if (!map.has(card.event_type)) {
      map.set(card.event_type, []);
    }
    map.get(card.event_type)!.push(card);
  }
  return map;
}

/**
 * The /feed/ digest cap comes from feed.json's `section_cap` — owned by the
 * exporter (_FEED_SECTION_CAP in export_site.py, ROADMAP #88) because the
 * per-section sidecars json/feed-sections/{event_type}.json carry exactly
 * the cards past it. No fallback: a feed.json without it predates #88 and
 * its sidecars do not exist, so "Show all" would 404 on every section.
 * (Historical: this was `const FEED_SECTION_CAP = 75` here, 2026-09-02.)
 */
function feedSectionCap(feed: FeedSidecar): number {
  const cap = feed.section_cap;
  if (typeof cap !== "number" || !Number.isInteger(cap) || cap <= 0) {
    throw new Error(
      "feed.json carries no positive-integer section_cap — the export predates " +
        "ROADMAP #88 (per-event-type feed-sections/ sidecars). Re-run " +
        "`uv run python -m govbudget export-site` before building.",
    );
  }
  return cap;
}

export default function FeedPage() {
  const feed = getFeed();
  const { cards, total, scope_qualifier } = feed;
  const FEED_SECTION_CAP = feedSectionCap(feed);
  // Backlog #49: the section scope note below used to hand-type its own
  // parenthetical, which had drifted false ("appropriations not covered by
  // the R-1/P-1 rollups" — COLUMBIA is a P-1 line and still absent). Reads
  // site_meta's corpus_scope now — the bare tail, not the full hero-style
  // scope_qualifier sentence above (which reads as a superlative caption,
  // not a "ranked across" clause) — so it cannot drift from the homepage,
  // /programs/, /years/, /methodology/ and /data/ wording again.
  const corpusScope = getSiteMeta().corpus_scope;
  const grouped = groupByEventType(cards);

  // family_key → company slug lookup (SSG) from the same top-200 entity
  // index the companies page uses. Families outside the top 200 have no
  // company page — their cards get data-no-company-page instead of a link.
  const entityByFamilyKey = getEntityTopByFamilyKey();

  // pe_blis that actually have a /program/{pe_bli}/ page — the page universe
  // is EVERY program_details sidecar (Phase 5F §2a: full + rollup tiers),
  // the same set generateStaticParams enumerates. Feed events may reference
  // pe_blis outside even that (trajectory-mart extras, dead decade-diff PEs);
  // linking those would 404 in the static export (G1 dead-link contract).
  // A card is looked up by the page it ADDRESSES (feedProgramKey) — its
  // pe_bli, except a concentration_shift card on one member of a shared code,
  // whose program_url names the member's page (Task 28a).
  const programPeBlis = new Set(getProgramPeBlis());

  return (
    // §P2-1 page weight: citations resolve LAZILY through cite-shards
    // (/json/cite-shards/{fact_id[:2]}.json), so the provider mounts with an
    // EMPTY embedded slice — the same treatment /programs/, /years/ and
    // /flow/ already use for the same reason, and /feed/ was the last index
    // page without it. Its 535-fact slice was 1.08 MB of a 1.72 MB document
    // (63% of it) purely to save one fetch on the first citation click — on
    // the SYNDICATION surface, the one page most likely to be opened once
    // from a link and never navigated. Clicking a figure still opens its
    // citation; the panel resolves the fact's shard first and shows the
    // declared loading/degraded states while it does.
    <CitationPanelProvider citations={{}}>
      <div className="spine py-8">
        <Breadcrumbs
          items={[{ label: "Home", href: "/" }, { label: "Anomaly Feed" }]}
        />
        <PageIntro eyebrow="Research tools / Discover" title="Changes & signals"
          description={<p>Find budget shifts and contracting patterns worth investigating. Start with a signal, inspect the program, and follow its figures to the source.</p>}
          actions={<><Link href="/years/">Compare the budget years →</Link><Link href="/methodology/#feed">How signals are selected →</Link></>}>
          <p className="text-sm text-muted-foreground">
            {formatCount(total)}{" "}automated signals across{" "}
            {formatCount(grouped.size)}{" "}event types.
            Every item states the dollars it is about, not just a percentage.
            Figures carry citations. An underlined value opens to its source.
            &ldquo;Why flagged?&rdquo; links explain each signal type and its
            threshold.
          </p>
          <div className="mt-2">
            <SubscribeLinks
              paths={{ rss: WHOLE_FEED_RSS, atom: WHOLE_FEED_ATOM }}
              label="Whole anomaly feed"
            />
            <span className="ml-2 text-xs text-muted-foreground">
              Items are dated to the corpus build — the budget books carry no
              per-event timestamp.
            </span>
          </div>
        </PageIntro>

        <ReviewedBriefings />

        <nav aria-label="Signal types" className="mb-8 flex flex-wrap gap-2">
          {EVENT_ORDER.filter((etype) => (grouped.get(etype)?.length ?? 0) > 0).map((etype) => (
            <a key={etype} href={`#${EVENT_META[etype].anchorId}`} className="inline-flex min-h-11 items-center gap-2 border border-border bg-card px-3 py-2 text-sm text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2">
              {EVENT_META[etype].label}
              <span className="t-id">{formatCount(grouped.get(etype)!.length)}</span>
            </a>
          ))}
        </nav>

        <div className="space-y-10">
          {EVENT_ORDER.map((etype) => {
            const meta = EVENT_META[etype];
            const all_section_cards = grouped.get(etype) ?? [];
            if (all_section_cards.length === 0) return null;
            // Page cap (2026-09-02): the crosswalk expansions grew the feed
            // from 160 to 700+ cards and the page to 6.8MB raw. The page is a
            // digest: the top section_cap cards per section (cards arrive
            // ranked by magnitude from the exporter); the full set stays in
            // feed.json and the RSS/Atom feeds linked in each section header.
            const section_cards = all_section_cards.slice(0, FEED_SECTION_CAP);
            const truncated = all_section_cards.length - section_cards.length;

            return (
              // scroll-mt-16 clears the sticky header when navigating to the
              // #feed-{type} anchors directly (site-wide anchored-section
              // pattern — methodology/home sections use the same value).
              <section key={etype} id={meta.anchorId} className="scroll-mt-16">
                <div className="mb-3">
                  <h2>
                    {meta.label}{" "}
                    <span className="ml-1 text-sm text-muted-foreground font-normal">
                      ({truncated > 0 ? `${formatCount(section_cards.length)} of ${formatCount(all_section_cards.length)}` : formatCount(section_cards.length)})
                    </span>
                  </h2>
                  {/* backlog #38: this carried data-source-text="methodology"
                      + a sentinel data-xml-path. The description is OUR prose
                      stating the selection thresholds ($50M, $5M, $1M), quoted
                      from nothing, so it takes no source-text exemption. The
                      three thresholds are enumerated in
                      scripts/gates/prose-allowlist.json, scoped to this page
                      and /methodology/. */}
                  <p className="text-sm text-muted-foreground mt-1">
                    {meta.description}
                  </p>
                  {SCOPED_EVENT_TYPES.has(etype) && scope_qualifier && corpusScope && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Scope: ranked across the R&D and procurement program
                      elements in our corpus ({corpusScope}).
                    </p>
                  )}
                  <div className="mt-1">
                    <SubscribeLinks
                      paths={eventTypeFeedPaths(etype)}
                      label={meta.label}
                    />
                  </div>
                </div>
                {/* Card list — staggered once-reveal on scroll (Task 11);
                    the Reveal wrapper divs are the divide-y children. */}
                <div className="divide-y divide-border rounded-lg border border-border overflow-hidden bg-card">
                  {section_cards.map((card, i) => (
                    <Reveal
                      key={feedGuid(card)}
                      index={i}
                    >
                      <FeedCardItem
                        card={card}
                        companySlug={
                          card.family_key
                            ? (entityByFamilyKey.get(card.family_key)?.slug ??
                              null)
                            : null
                        }
                        hasProgramPage={programPeBlis.has(
                          feedProgramKey(card) ?? "",
                        )}
                      />
                    </Reveal>
                  ))}
                </div>
                {truncated > 0 && (
                  <FeedSectionExpand
                    eventType={etype}
                    shown={section_cards.length}
                    total={all_section_cards.length}
                  />
                )}
              </section>
            );
          })}
        </div>

        <p className="mt-8 text-xs text-muted-foreground">
          Signals computed from FY2026 budget justification books, USAspending
          award data, and LDA lobbying disclosures. Thresholds and methodology:
          see{" "}
          <Link href="/methodology/#feed" className="underline hover:text-foreground">
            /methodology/#feed
          </Link>
          .
        </p>
      </div>
    </CitationPanelProvider>
  );
}
