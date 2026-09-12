/**
 * hhiScopeNote — the "this is one year, not the program's pooled figure"
 * disclosure for an hhi-unit feed card (backlog #57).
 *
 * WHY THIS EXISTS. concentration_shift cards headline a SINGLE (pe_bli,
 * fiscal_year)'s HHI over high-confidence award transactions for that year
 * alone (dbt fct_feed_events). The /program/{peBli}/ page a card links to
 * renders a DIFFERENT figure: fct_program_concentration's HHI pooled across
 * every year, over high-confidence links alone — and only where the program
 * clears the floor: 3 high-confidence awards across 2 contractor families
 * holding positive obligations, with positive net linked dollars. Below it
 * the page publishes no pooled index at all and says so (ROADMAP #80,
 * 2026-09-11: 444 - 37 = 407 of the 444 mart rows, the measured 37 living
 * in _MIN_HIGH_ONLY_ROWS in src/govbudget/verify_phase3.py and mirrored in
 * lib/concentration-basis.ts), so a card can legitimately land on a page
 * with no band to compare against; scripts/gates/feed.mjs leg (l) treats
 * that as a destination state, not a missing badge, and floors the
 * population it can still reconcile. Where both exist, both are real,
 * correctly
 * computed numbers — they are just not the same measure, and a single
 * concentrated year can sit next to a competitive pooled figure (or the
 * reverse) with no error anywhere. Without this note, a reader who reads
 * "HHI=8662 (2020)" glossed with a concentration adjective, then clicks
 * through and finds the page calling the SAME program "Competitive," has no
 * way to tell that apart from the site contradicting itself.
 *
 * AND THE DESTINATION MAY PUBLISH NOTHING (#80 fix round 2, 2026-09-11,
 * finding 8). The note used to promise the pooled figure outright ("see the
 * program page"), written when the card always found one there; 407 of 444
 * program pages now publish no pooled index at all, so a reader following
 * the instruction meets the withheld sentence instead. It says "or not be
 * published" — and keeps the "pooled"/"differ" tokens scripts/gates/feed.mjs
 * leg (l) matches on to accept a disclosed band divergence.
 *
 * WHY THIS FILE (ROADMAP #81). Until #81 this lived in
 * components/feed-headline.tsx, whose VALUE import of feedHeadlineSegments()
 * from src/lib/data.ts (`import "server-only"`) taints every export of that
 * module for a client bundle — so the /feed/ section-expand client twin
 * carried a hand-copied hhiScopeNoteClient. This module imports ONLY
 * hhi-band.mjs and a type, so <FeedCardItemShell> (feed-card-item-shell.tsx)
 * calls it from both the server and the client tree. KEEP IT THAT WAY: no
 * value import from "@/lib/data" or any other server-only module — the
 * client-graph vitest (vitest.client-graph.config.ts) fails on the first one.
 *
 * Returns null for non-hhi cards. Text and band both derive from the SAME
 * shared hhiBand() the destination page's own badge uses (hhi-band.mjs) —
 * see that file's doc-comment for why it is .mjs, not .ts. Rendered on every
 * /feed/ card as the [data-hhi-scope-note] <p> that scripts/gates/feed.mjs
 * leg (l) reads.
 */

import { hhiBand } from "@/lib/hhi-band.mjs";
import type { FeedCard } from "@/lib/data";

export function hhiScopeNote(
  card: FeedCard,
): { band: string; text: string } | null {
  if (card.figure_units !== "hhi" || card.figure_value === null) return null;
  const band = hhiBand(card.figure_value);
  const yearText = card.fiscal_year ? `FY${card.fiscal_year}` : "that year";
  return {
    band: band.label,
    text:
      `${band.label} in ${yearText} — the program's pooled, all-years HHI ` +
      `can differ, or not be published; see the program page.`,
  };
}
