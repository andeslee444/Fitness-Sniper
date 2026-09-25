import type { ReactNode } from "react";
import Link from "next/link";
import { Cite } from "@/components/cite";
import { FeedMagnitudeLine } from "@/components/feed-magnitude";
import { Fy26SplitNote } from "@/components/fy26-split-note";
import { hhiScopeNote } from "@/lib/hhi-scope-note";
import { feedProgramKey } from "@/lib/feed-model.mjs";
import type { FeedCard } from "@/lib/data";

/**
 * <FeedCardItemShell> — THE /feed/ card markup, rendered by both trees
 * (ROADMAP #81):
 *
 *   - <FeedCardItem>       (feed-card-item.tsx, SERVER tree — feed/page.tsx)
 *   - <FeedCardItemClient> (feed-card-item-client.tsx, "use client" — the
 *                           section-expand path, feed-section-expand.tsx)
 *
 * Until #81 the two were hand-copied twins pinned only by a byte-identical
 * parity test. Now there is one shell and ONE slot:
 *
 *   headline — the rendered headline runs. The server tree passes
 *              <FeedHeadline> (feedHeadlineSegments() → lib/data.ts, which
 *              can fall back to getPrograms() on disk); the client tree
 *              passes its fs-free twin. This is the ONE piece the two trees
 *              legitimately compute differently.
 *
 * Everything else is computed HERE from `card`, once: the §57 scope note
 * (lib/hhi-scope-note.ts) and the #54 FY2026 split note
 * (components/fy26-split-note.tsx — the same component /program/*\/ renders).
 *
 * CLIENT-SAFE BY CONSTRUCTION: this module is imported from a "use client"
 * module, so nothing it imports may reach a `import "server-only"` module.
 * Its imports are <Cite> ("use client"), <FeedMagnitudeLine> (type-only
 * import of lib/data), <Fy26SplitNote> (Cite + ScopeNote + a type),
 * hhiScopeNote (lib/hhi-scope-note.ts — hhi-band.mjs + a type),
 * feedProgramKey (lib/feed-model.mjs — pure, imports nothing) and
 * next/link. vitest.client-graph.config.ts runs the client twin against the
 * REAL server-only package and fails on the first leak.
 *
 * feed-card-item-parity.test.tsx still diffs the two trees' HTML;
 * feed-card-item-shell.test.tsx pins that both trees call THIS component and
 * that its markers are authored nowhere else.
 */
export interface FeedCardItemShellProps {
  card: FeedCard;
  /**
   * /company/{slug}/ slug when the card's family_key has a page in the
   * top-200 entity index; null otherwise. new_entrant cards without a page
   * carry data-no-company-page on the wrapper (G1 link-graph contract).
   */
  companySlug: string | null;
  /**
   * Whether the page the card addresses was built: its feedProgramKey (the
   * key in program_url, else pe_bli — lib/feed-model.mjs) names a
   * program_details sidecar, the listing generateStaticParams builds
   * /program/{key}/ from. The server tree's /feed/ page tests that listing
   * (getProgramPeBlis); the client tree reads the section sidecar's
   * has_program_page, which the exporter resolves the same way
   * (_feed_program_key) and gate 8 leg (p) holds to this answer. Cards on
   * codes no program page covers keep the code text but get no "view
   * program" link (G1 dead-link contract).
   */
  hasProgramPage: boolean;
  /** Rendered inside the [data-source-text="headline"] <p>. See doc above. */
  headline: ReactNode;
}

export function FeedCardItemShell({
  card,
  companySlug,
  hasProgramPage,
  headline,
}: FeedCardItemShellProps) {
  const isConcentration = card.event_type === "concentration_shift";
  const isNewEntrant = card.event_type === "new_entrant";
  const isRvaGap = card.event_type === "request_vs_actuals_gap";
  // §57: null for non-hhi cards — see lib/hhi-scope-note.ts's doc-comment.
  const hhiScope = hhiScopeNote(card);

  // Basis threading (PM Sprint 1): budget-figure cards carry
  // basis/fy/measure/edition from the sidecar; award-derived cards
  // (basis null) render without attrs or chip.
  const basisProps = card.basis
    ? {
        basis: card.basis,
        fy: card.fy ?? undefined,
        measure: card.measure ?? undefined,
        edition: card.edition ?? undefined,
        entity: card.pe_bli ?? undefined,
      }
    : {};

  return (
    // PM Sprint 3 round-1 judging: this row kept its desktop two-column shape
    // at 390. The figure column is `shrink-0` and carries the percentage, the
    // fact-id chip, the basis chip and "why flagged?" — roughly 260px of it —
    // which left the headline about 110px and wrapped it one or two words per
    // line ("Strategic / Sub & / Weapons / System / Support / increased ...").
    // Nothing was clipped, so no gate saw it; the page was simply unreadable.
    //
    // It stacks below `sm` and keeps the desktop row above it.
    <div
      data-feed-card=""
      className="flex flex-col gap-2 px-5 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-4 hover:bg-muted/60 transition-colors"
      {...(isNewEntrant && !companySlug ? { "data-no-company-page": "" } : {})}
    >
      <div data-mobile-pair-label="" className="min-w-0 sm:flex-1">
        {/* data-source-text="headline": prose COMPOSED by the export pipeline.
            Since backlog #44 it earns neither formatting exemption
            (source-text-kinds.mjs): the notation is ours and so are the dollar
            tokens, which now carry their own fact ids through <ProseCite>.
            What the marker still does is (a0) — no [data-amount] may nest
            inside it — which is what forces those per-token anchors.
            data-xml-path is the block-level anchor (a0) requires. */}
        {/* Headline leads with the program title when the programs index has
            one (feedHeadlineSegments); the raw PE/BLI code is demoted to the
            metadata line below. */}
        <p
          className="text-sm font-medium leading-snug"
          data-source-text="headline"
          data-xml-path={`site:feed/${card.event_type}/${card.pe_bli ?? card.family_key ?? "unknown"}`}
        >{headline}</p>
        {/* §57: this card's figure is one fiscal year's HHI, not the
            program's pooled all-years figure — see hhi-band.mjs and
            lib/hhi-scope-note.ts's doc-comment. Read by
            scripts/gates/feed.mjs leg (l). */}
        {hhiScope && (
          <p
            data-hhi-scope-note=""
            data-hhi-band={hhiScope.band}
            className="mt-0.5 text-xs text-muted-foreground"
          >
            {hhiScope.text}
          </p>
        )}
        {/* §P1-8: the dollars the headline's percentage is a percentage OF.
            Kept OUTSIDE the [data-source-text] headline — computed figures
            may not nest inside source text (render-static leg a0). */}
        <FeedMagnitudeLine card={card} />
        {/* backlog #54: this card's pct_change headline is computed on the
            COMBINED FY2026 figure (discretionary + one-time reconciliation
            money) — the same defect #50 fixed on /program/*\/. Renders the
            identical <Fy26SplitNote> /program/*\/ uses (same component, same
            [data-fy26-recon-chip]/[data-fy26-disc-pct-change] markers gate 23
            leg g reads off this page) rather than a second,
            differently-worded disclosure. Null for every card except a
            yoy_swing whose PE carries reconciliation money — the combined
            headline is never deleted, only accompanied. */}
        {card.fy26_split?.has_reconciliation && (
          <Fy26SplitNote split={card.fy26_split} />
        )}
        {card.pe_bli && (
          <div className="mt-1 flex items-center gap-2">
            {/* The page the card addresses (feedProgramKey): its pe_bli,
                except on a card addressed to ONE member of a shared code
                (Task 28a), which prints that member's key (2292-WPN) — both
                2292 members carry one title, so the bare code named neither.
                The event's identities (data-xml-path above, the guid, the
                basis entity) stay on the bare pe_bli. */}
            <span className="font-mono text-xs text-muted-foreground">
              {feedProgramKey(card)}
            </span>
            {card.program_url && hasProgramPage && (
              <Link
                href={card.program_url}
                className="text-xs text-primary underline decoration-dotted hover:decoration-solid"
              >
                view program &rarr;
              </Link>
            )}
          </div>
        )}
        {card.family_key && !card.pe_bli && (
          <p className="mt-1 text-xs font-mono">
            {companySlug ? (
              <Link
                href={`/company/${companySlug}/`}
                className="text-primary underline decoration-dotted hover:decoration-solid"
              >
                {card.family_key}
              </Link>
            ) : (
              <span className="text-muted-foreground">{card.family_key}</span>
            )}
          </p>
        )}
      </div>
      <div
        data-mobile-pair-value=""
        className="flex shrink-0 flex-wrap items-baseline gap-x-2 gap-y-1 sm:block sm:text-right"
      >
        {card.figure_value !== null && (
          <span
            data-primary-value="feed-figure"
            className="text-sm font-mono font-semibold"
          >
            {isConcentration || card.figure_units === "hhi" ? (
              <Cite
                value={card.figure_value}
                units="USD"
                dataset="fct_feed_events"
                factId={card.figure_fact_id}
                {...basisProps}
                display={`HHI ${card.figure_value.toFixed(0)}`}
              />
            ) : isNewEntrant || card.figure_units === "dollars" ? (
              <Cite
                value={card.figure_value}
                units="USD"
                dataset="fct_feed_events"
                factId={card.figure_fact_id}
                {...basisProps}
              />
            ) : isRvaGap ? (
              // Signed gap in USD thousands, cited via the minted book_diff
              // derived fact (breakdown reachable from the citation panel).
              <Cite
                value={card.figure_value}
                units="USD thousands"
                dataset="fct_book_diff"
                factId={card.figure_fact_id}
                {...basisProps}
              />
            ) : card.figure_units === "pct_change" ? (
              <Cite
                value={card.figure_value}
                units="USD"
                dataset="fct_budget_trajectory"
                factId={card.figure_fact_id}
                display={`${card.figure_value >= 0 ? "+" : ""}${card.figure_value.toFixed(0)}%`}
                {...basisProps}
              />
            ) : (
              <Cite
                value={card.figure_value}
                units="USD thousands"
                dataset="fct_budget_trajectory"
                factId={card.figure_fact_id}
                {...basisProps}
              />
            )}
          </span>
        )}
        <div className="sm:mt-1">
          {/* Slightly larger + higher-contrast than muted-foreground
              (visual-judge nit: "why?" was easy to miss). href keeps the
              /methodology/#feed-{type} anchor the feed gate greps for. */}
          <Link
            href={card.why_url}
            className="text-[13px] text-foreground/70 underline decoration-dotted hover:text-foreground hover:decoration-solid"
            title="Why am I seeing this?"
          >
            why flagged?
          </Link>
        </div>
      </div>
    </div>
  );
}
