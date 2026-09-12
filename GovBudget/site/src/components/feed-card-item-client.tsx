"use client";

/**
 * <FeedCardItemClient> — the CLIENT-tree /feed/ card, for the section-expand
 * feature (Task 6, #73; feed-section-expand.tsx).
 *
 * Since ROADMAP #81 this is NOT a twin of <FeedCardItem>: both render the
 * same <FeedCardItemShell> (feed-card-item-shell.tsx), which calls
 * hhiScopeNote (lib/hhi-scope-note.ts) and renders <Fy26SplitNote>
 * (fy26-split-note.tsx) itself. The hand-copied hhiScopeNoteClient and
 * Fy26SplitNoteClient this file used to define are gone.
 *
 * WHAT IS STILL REIMPLEMENTED HERE, AND WHY. The headline. <FeedHeadline>
 * (feed-headline.tsx) calls feedHeadlineSegments() from src/lib/data.ts,
 * which is `import "server-only"` (it reads the exported JSON sidecars off
 * disk with `fs`) — Next throws when that reaches a client bundle. So this
 * file carries feedHeadlineSegmentsClient(), which reproduces data.ts's
 * feedDisplayHeadline() swap of a code-led headline's leading pe_bli run for
 * card.title, using ONLY card.title — it deliberately leaves out
 * feedDisplayHeadline()'s further fallback to getPrograms() (disk I/O) for
 * the case where card.title itself is absent: that path needs `fs`, cannot
 * run in the browser, and is unreachable for the current corpus (the
 * exporter has resolved and led with the title for every card since #44; the
 * 6 cards whose headline still starts with their own code, all pe_bli
 * "LRASM0", carry card.title === card.pe_bli === "LRASM0", the
 * reconstruction's own no-op case, verified against the live corpus
 * 2026-09-04).
 *
 * NOT COVERED (2026-09-04 batch review 1.5): a future export shipping a
 * code-led headline with NO card.title at all would render the raw code here
 * and a getPrograms()-resolved title on the server. The parity test's
 * code-led fixtures all carry a title, and its title-less fixtures are
 * company cards with pe_bli === null, so neither reaches this case — a
 * fixture that did would FAIL by construction. The guard is upstream: the
 * exporter resolves a title for every card, and gate 23's feed legs check
 * the rendered headline against the card it came from.
 *
 * PARITY CONTRACT. For the same (card, companySlug, hasProgramPage) triple
 * this renders IDENTICAL HTML to <FeedCardItem> — by construction for
 * everything but the headline, and end-to-end by
 * __tests__/feed-card-item-parity.test.tsx. __tests__/feed-card-item-shell.
 * test.tsx pins the construction; __tests__/client-graph/ runs this module
 * against the REAL server-only package.
 */

import { ProseCite } from "@/components/prose-cite";
import { FeedCardItemShell } from "@/components/feed-card-item-shell";
import type { FeedCard, FeedHeadlineSegment } from "@/lib/data";

// ── feedHeadlineSegments twin (see doc comment above) ───────────────────────

/**
 * Client-safe display headline — reproduces data.ts's feedDisplayHeadline()
 * for the dominant branch only: card.title swapped in for a leading pe_bli
 * code. No getPrograms() fallback (see file doc comment for why that's
 * left out, not just deferred).
 */
function feedDisplayHeadlineClient(card: FeedCard): string {
  if (!card.pe_bli || !card.headline.startsWith(card.pe_bli)) {
    return card.headline;
  }
  if (!card.title || card.title === card.pe_bli) return card.headline;
  return `${card.title}${card.headline.slice(card.pe_bli.length)}`;
}

function feedHeadlineSegmentsClient(card: FeedCard): FeedHeadlineSegment[] {
  const segments = card.headline_segments;
  if (!segments || segments.length === 0) {
    return [{ text: feedDisplayHeadlineClient(card) }];
  }
  const display = feedDisplayHeadlineClient(card);
  if (display === card.headline) return segments;
  // The swap only ever rewrites the leading run; splice it back in place
  // (identical to feedHeadlineSegments in lib/data.ts).
  const [first, ...rest] = segments;
  if (first.text === undefined) return segments;
  const swapped = display.slice(
    0,
    display.length - (card.headline.length - first.text.length),
  );
  return [{ text: swapped }, ...rest];
}

function FeedHeadlineClient({ card }: { card: FeedCard }) {
  const segments = feedHeadlineSegmentsClient(card);
  return (
    <>
      {segments.map((seg, i) =>
        seg.text !== undefined ? (
          <span key={i}>{seg.text}</span>
        ) : (
          <ProseCite key={i} factId={seg.fact_id}>
            {seg.amount}
          </ProseCite>
        ),
      )}
    </>
  );
}

// ── FeedCardItemClient — the shell, with the client-safe headline ───────────

export function FeedCardItemClient({
  card,
  companySlug,
  hasProgramPage,
}: {
  card: FeedCard;
  companySlug: string | null;
  hasProgramPage: boolean;
}) {
  return (
    <FeedCardItemShell
      card={card}
      companySlug={companySlug}
      hasProgramPage={hasProgramPage}
      headline={<FeedHeadlineClient card={card} />}
    />
  );
}
