import Link from "next/link";
import type { ProgramHHI } from "@/lib/data";
import { Cite } from "@/components/cite";
import { ScopeNote } from "@/components/notes";
import { hhiBand } from "@/lib/hhi-band.mjs";
import {
  concentrationHeadline,
  CONCENTRATION_WITHHELD_REASON,
} from "@/lib/concentration-basis";

/**
 * ProgramConcentration — HHI concentration card (ROADMAP #80; fix round 1,
 * 2026-09-11).
 *
 * Shown only when the block is non-null (a #70 shared-code withholding
 * removes the block upstream and this renders nothing at all). The mart
 * computes TWO bases and both ship in the download and in citations; this
 * card renders ONE — the high-confidence-only figures — and only where
 * concentrationHeadline() says they publish. Where they do not, the card
 * states the absence and prints no figure: the all-links figures rest
 * mostly on the account+subagency tier, measured 0 of 60 for program
 * attribution (ROADMAP #79), so substituting them would widen the claim to
 * fit a number. See lib/concentration-basis.ts for the whole argument.
 *
 * Two states, and the gates read both:
 *   PUBLISHED — exactly one [data-hhi-band] stamped data-hhi-basis="high",
 *     plus State-A citations on the index and the obligations
 *     (hhi_high_fact_id / program_dollars_high_fact_id, dataset
 *     fct_program_concentration, measures "hhi-high"/"obligations-high" —
 *     distinct tokens so gate 23 leg a2 can never group a high-only figure
 *     with an all-tier one).
 *   WITHHELD — [data-concentration-withheld="below-floor"], one sentence,
 *     and NOTHING else: no band, no [data-amount], no [data-measure], no
 *     tier chip, no top contractor, no family count. A reader must not be
 *     able to mistake an absence for a small number.
 *
 * Band vocabulary lives in hhi-band.mjs (backlog #57) — this is the
 * DESTINATION page a homepage/feed concentration claim links to, and
 * scripts/gates/feed.mjs leg (l) reads either the ONE [data-hhi-band] (with
 * its basis stamp) or the withheld marker to check that claim against what
 * this page actually renders. Color stays local.
 */

interface ProgramConcentrationProps {
  hhi: ProgramHHI | null;
}

const BAND_COLOR: Record<string, string> = {
  competitive: "text-green-700",
  moderate: "text-yellow-700",
  concentrated: "text-red-700",
};

function ConcentrationSection({ children }: { children: React.ReactNode }) {
  return (
    <section aria-labelledby="concentration-heading" className="mb-8">
      <h2
        id="concentration-heading"
        className="text-lg font-semibold mb-4 text-foreground"
      >
        Contractor Concentration
      </h2>
      {children}
    </section>
  );
}

export function ProgramConcentration({ hhi }: ProgramConcentrationProps) {
  if (!hhi) return null;

  const head = concentrationHeadline(hhi);

  if (!head.published) {
    return (
      <ConcentrationSection>
        <ScopeNote label={null}>
          <p
            data-concentration-withheld={head.withheld}
            className="text-xs leading-relaxed text-muted-foreground"
          >
            <strong className="text-foreground">
              No concentration index is published for this line.
            </strong>{" "}
            {CONCENTRATION_WITHHELD_REASON} An index over one or two awards is
            a fact about the sample, not about the market. Whatever further
            links this line carries are medium-confidence, and what each
            medium evidence path does and does not establish is set out in
            the{" "}
            <Link
              href="/methodology/#crosswalk-confidence"
              className="underline decoration-dotted hover:text-foreground"
            >
              methodology
            </Link>
            . Both bases are in the{" "}
            <Link
              href="/downloads/"
              className="underline decoration-dotted hover:text-foreground"
            >
              downloadable warehouse
            </Link>
            .
          </p>
        </ScopeNote>
      </ConcentrationSection>
    );
  }

  const band = hhiBand(head.hhi);
  const { label } = band;
  const color = BAND_COLOR[band.key];

  return (
    <ConcentrationSection>
      <div
        className="rounded-lg border border-border bg-card p-4"
        data-concentration-basis={head.basis}
      >
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {/* HHI — derived citation (display override: index, not dollars) */}
          <div>
            <div className="text-xs text-muted-foreground mb-1">
              {/* Tri-persona Wave 3, Task 3: "HHI" is stamped here, on every
                  concentration_shift feed card, and in the anomaly headline
                  that used to open the home page — and was expanded only
                  inside /glossary/, which was linked twice per page and both
                  times from the footer. The hover title stays (it carries the
                  bands); the term now reaches its own definition in a click,
                  which a hover title cannot do on a phone. */}
              <Link
                href="/glossary/#hhi"
                data-glossary-term="hhi"
                className="underline decoration-dotted underline-offset-2 hover:text-foreground"
              >
                HHI
              </Link>{" "}
              Index
              <span
                className="ml-1 text-muted-foreground/60 cursor-help"
                title="Herfindahl-Hirschman Index: 0–10,000. <1500 competitive; 1500–2500 moderate; >2500 concentrated. Computed from high-confidence award links only, on positive-only contractor shares — click the value for the formula."
              >
                ⓘ
              </span>
            </div>
            <div className={`text-xl font-bold ${color}`}>
              <Cite
                value={head.hhi}
                units="USD"
                dataset="fct_program_concentration"
                factId={head.hhi_fact_id}
                display={head.hhi.toFixed(0)}
                // Non-budget figure (gate 23 a1): source-family basis token,
                // honest multi-year fy token — no basis chip (usaspending is
                // not a chip-vocabulary basis).
                basis="usaspending"
                fy="all-years"
                measure={head.hhiMeasure}
              />
            </div>
            {/* data-hhi-band: the pooled all-years band, the ONE stable
                selector for scripts/gates/feed.mjs leg (l); it also declares
                which basis it is. See hhi-band.mjs. */}
            <div
              className={`text-xs font-medium ${color}`}
              data-hhi-band={label}
              data-hhi-basis={head.basis}
            >
              {label}
            </div>
          </div>

          {/* Top family */}
          <div>
            <div className="text-xs text-muted-foreground mb-1">Top Contractor</div>
            <div className="text-sm font-medium text-foreground">
              {head.top_family}
            </div>
          </div>

          {/* Family count */}
          <div>
            <div className="text-xs text-muted-foreground mb-1">
              Contractor Families
            </div>
            <div className="text-xl font-bold text-foreground">
              {head.family_count}
            </div>
          </div>

          {/* Program dollars — derived citation */}
          <div>
            <div className="text-xs text-muted-foreground mb-1">
              Program Obligations
              <span
                className="ml-1 text-muted-foreground/60 cursor-help"
                title="Contract obligations attributed to this program element through high-confidence award links. Derived — click the value for the formula."
              >
                ⓘ
              </span>
            </div>
            <div className="text-xl font-bold">
              <Cite
                value={head.program_dollars}
                units="USD"
                dataset="fct_program_concentration"
                factId={head.program_dollars_fact_id}
                basis="usaspending"
                fy="all-years"
                measure={head.dollarsMeasure}
              />
            </div>
          </div>
        </div>

        <p className="mt-3 text-xs text-muted-foreground">
          High-confidence award links only. The figures over every published
          link, including medium-confidence ones, are in the{" "}
          <Link
            href="/downloads/"
            className="underline decoration-dotted hover:text-foreground"
          >
            downloadable warehouse
          </Link>
          , not on this page —{" "}
          <Link
            href="/methodology/#crosswalk-confidence"
            className="underline decoration-dotted hover:text-foreground"
          >
            why
          </Link>
          .
        </p>
      </div>
    </ConcentrationSection>
  );
}
