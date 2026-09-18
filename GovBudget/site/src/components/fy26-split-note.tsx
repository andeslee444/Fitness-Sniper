import { Cite } from "@/components/cite";
import { ScopeNote } from "@/components/notes";
import type { Fy26Split } from "@/lib/data";

/**
 * Fy26SplitNote (backlog #50) — the FY2026 card's combined figure ($7.70B
 * for Long Range Kill Chains, PE 1203154SF) is disc + reconciliation with no
 * visible seam. When the split has a reconciliation component, this renders
 * beside the combined figure: a reconciliation-share chip (gate 23 leg g's
 * [data-fy26-recon-chip] marker), then a caption stating both addends —
 * each its OWN cited figure, never a re-typed number — and the
 * discretionary-basis change vs FY2025 enacted (gate leg g's
 * [data-fy26-disc-pct-change] marker), the like-for-like rate a reader can
 * actually extrapolate. The combined figure stays the headline (it is the
 * true total); this note is what turns "+3052.9%" from an unlabelled claim
 * into a labelled one — the raw change card is untouched, still rendered by
 * program-figures.tsx's sibling "change" SummaryCardCell.
 *
 * Rendered on TWO surfaces from this one component (backlog #54): beside the
 * FY2026 card on /program/{peBli}/ (program-figures.tsx) and on every
 * /feed/ yoy_swing card whose PE carries reconciliation money (BOTH /feed/
 * card trees, via feed-card-item-shell.tsx) — so the wording and the markers
 * gate 23 (scripts/gates/basis.mjs, leg g) reads cannot drift between the
 * pages. Which leg reads which, corrected 2026-09-18 against the gate:
 * g1 requires [data-fy26-recon-chip] on every /program/{peBli}/ whose sidecar
 * reports recon_share > 0; g4a requires that SAME chip on every qualifying
 * /feed/ yoy_swing card; and [data-fy26-disc-pct-change] is g2's marker,
 * required on a /program/ page that renders the combined FY25→FY26
 * percentage. No leg reads the disc-pct marker on /feed/.
 *
 * WHY THIS FILE (ROADMAP #81). Until #81 this lived in program-figures.tsx,
 * whose top-level <CoverageNote> import (→ src/lib/coverage.ts,
 * `import "server-only"`) taints every export of that module for a client
 * bundle — so the /feed/ client twin carried a hand-copied Fy26SplitNoteClient.
 * This module imports only <Cite> ("use client"), <ScopeNote> (notes.tsx, no
 * imports beyond `ReactNode`) and a type. KEEP IT THAT WAY — the client-graph
 * vitest (vitest.client-graph.config.ts) fails on the first server-only leak.
 */
export function Fy26SplitNote({ split }: { split: Fy26Split }) {
  if (!split.reconciliation) return null; // has_reconciliation implies this is set; defensive
  const sharePct = (split.recon_share * 100).toFixed(1);
  return (
    <ScopeNote label={null} className="mt-2 text-left">
      <span
        data-fy26-recon-chip=""
        className="inline-block whitespace-nowrap rounded border border-border bg-muted px-1 py-0.5 align-middle font-sans text-xs font-normal leading-none text-muted-foreground no-underline"
      >
        {sharePct}% reconciliation
      </span>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
        {split.disc && (
          <>
            <Cite
              value={split.disc.v}
              units={split.disc.units}
              dataset={split.disc.dataset}
              factId={split.disc.fid}
              basis={split.disc.basis}
              fy={split.disc.fy}
              measure={split.disc.measure}
              edition={split.disc.edition}
              chip={false}
            />
            {" discretionary + "}
          </>
        )}
        <Cite
          value={split.reconciliation.v}
          units={split.reconciliation.units}
          dataset={split.reconciliation.dataset}
          factId={split.reconciliation.fid}
          basis={split.reconciliation.basis}
          fy={split.reconciliation.fy}
          measure={split.reconciliation.measure}
          edition={split.reconciliation.edition}
          chip={false}
        />
        {" one-time reconciliation."}
        {split.disc_pct_change != null && (
          <span data-fy26-disc-pct-change="">
            {" "}
            Discretionary change vs FY2025 enacted:{" "}
            {split.disc_pct_change >= 0 ? "+" : ""}
            {split.disc_pct_change.toFixed(1)}%.
          </span>
        )}
      </p>
    </ScopeNote>
  );
}
