"use client";

/**
 * <FeedSectionExpand> — /feed/ client-side "show all" (Task 6, #73; payload
 * moved to per-event-type sidecars in ROADMAP #88).
 *
 * MIRRORS ProgramAwards.handleExpand (program-awards.tsx): client component,
 * useState, plain same-origin fetch, an error state. On click it fetches
 * /json/feed-sections/{eventType}.json — the exporter's per-section sidecar
 * (copied into public/json/ by prepare-assets.mjs 5h) carrying ONLY the
 * cards past the digest cap — and renders them with the client-safe
 * <FeedCardItemClient> twin (feed-card-item-client.tsx).
 *
 * #88: this used to fetch the whole feed.json (881,872 bytes on the
 * 2026-09-04 export) and filter by event_type in the browser, so expanding
 * the 24 hidden yoy_swing cards downloaded a file it discarded 97% of. The
 * yoy_swing sidecar is 23,927 bytes. (concentration_shift's is 712,645 —
 * that section IS most of the feed, so its saving is ~19% raw / ~28%
 * gzipped, not a tenth.)
 *
 * companySlug / hasProgramPage arrive PRE-RESOLVED on each sidecar card
 * (company_slug, has_program_page) from the same entities_top /
 * program_details lookups feed/page.tsx applies to the visible cards, so
 * the per-section lookup props the #73 design carried are gone.
 *
 * The collapsed (initial, pre-hydration) render keeps
 * `[data-feed-truncation-note]` on the note — gate 23 leg g4
 * (scripts/gates/basis.mjs runFeedFy26SplitLeg) reads that attribute
 * against the STATIC HTML to excuse a qualifying yoy_swing card below the
 * cap — and now also carries data-feed-event-type / data-feed-shown /
 * data-feed-total, which gate 8 leg (o) (scripts/gates/feed.mjs
 * runSectionSidecarLeg) reads to assert the SHIPPED sidecar carries
 * exactly total − shown cards of this event type. Client-side expansion is
 * invisible to gates that only read out/feed/index.html; the sidecar
 * contract is how they see it.
 */

import { useState } from "react";
import type { FeedSectionCard, FeedSectionSidecar } from "@/lib/data";
import { FeedCardItemClient } from "@/components/feed-card-item-client";
import { formatCount } from "@/lib/format";

interface FeedSectionExpandProps {
  /** feed.json card.event_type this section renders — one of feed/page.tsx's EVENT_ORDER literals. */
  eventType: string;
  /** Cards already rendered statically (feed.json section_cap, today 75). */
  shown: number;
  /** Total cards in this section (all_section_cards.length). */
  total: number;
}

export function FeedSectionExpand({ eventType, shown, total }: FeedSectionExpandProps) {
  const [expanded, setExpanded] = useState(false);
  const [extraCards, setExtraCards] = useState<FeedSectionCard[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExpand() {
    if (extraCards) {
      setExpanded(true);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // eventType is a server-chosen EVENT_ORDER literal, never reader
      // input; the exporter refuses to write a sidecar whose name is not
      // [a-z0-9_]+, so this names a shipped file or 404s loudly below.
      // Gate 13 leg (i) recognises this directory-templated shape and
      // asserts out/json/feed-sections/ shipped; gate 8 leg (o) asserts the
      // per-section file matches the rendered section.
      const resp = await fetch(`/json/feed-sections/${eventType}.json`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: FeedSectionSidecar = await resp.json();
      if (!Array.isArray(data.cards)) throw new Error("sidecar has no cards array");
      // The sidecar was cut at ITS cap (data.shown). Cut LOWER than this
      // page's `shown` (a file behind a newer page after a partial deploy),
      // its first (shown − data.shown) cards are already on screen — drop
      // them so nothing renders twice. Cut HIGHER, nothing here can fill the
      // gap; the footer below states how many are actually on screen.
      const overlap =
        typeof data.shown === "number" && data.shown < shown ? shown - data.shown : 0;
      setExtraCards(data.cards.slice(overlap));
      setExpanded(true);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  if (expanded && extraCards) {
    return (
      <>
        <div className="divide-y divide-border rounded-b-lg border border-t-0 border-border overflow-hidden bg-card">
          {extraCards.map((card, i) => (
            <FeedCardItemClient
              key={`${card.event_type}-${card.pe_bli ?? card.family_key ?? i}-${i}`}
              card={card}
              companySlug={card.company_slug ?? null}
              hasProgramPage={card.has_program_page === true}
            />
          ))}
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {/* The sidecar can lag the built page after a partial deploy — so
              assert only what is actually ON SCREEN, never "all".

              M8 (2026-09-04 final review): the first `shown` cards are
              rendered SERVER-side and stay on screen regardless of what the
              fetch returned, so what is on screen is exactly
              `shown + extraCards.length` — never the fetched count alone. */}
          {(() => {
            const onScreen = shown + extraCards.length;
            return onScreen !== total
              ? `Showing ${formatCount(onScreen)} of ${formatCount(total)} cards in this section.`
              : `Showing all ${formatCount(total)} cards in this section.`;
          })()}
        </p>
      </>
    );
  }

  return (
    <div>
      <p
        className="mt-2 text-xs text-muted-foreground"
        data-feed-truncation-note=""
        data-feed-event-type={eventType}
        data-feed-shown={shown}
        data-feed-total={total}
      >
        Showing the {formatCount(shown)} largest of {formatCount(total)}{" "}
        cards in this section; the full set is in the RSS/Atom feeds above
        and in feed.json.
      </p>
      <div className="mt-2">
        {error && (
          <p className="text-xs text-red-600 mb-2">Failed to load: {error}</p>
        )}
        <button
          onClick={handleExpand}
          disabled={loading}
          className="text-sm text-primary hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Loading…" : `Show all ${formatCount(total)}`}
        </button>
      </div>
    </div>
  );
}
