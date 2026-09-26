import Link from "next/link";
import type { ProgramHHI } from "@/lib/data";
import { Cite } from "@/components/cite";
import { ScopeNote } from "@/components/notes";
import {
  hhiBand,
  hhiBandVintageLine,
  HHI_MODERATE_MIN,
  HHI_CONCENTRATED_MIN,
  HHI_BANDS_VINTAGE,
} from "@/lib/hhi-band.mjs";
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
 *     with one visible [data-hhi-band-vintage] line naming the bands'
 *     vintage (R-DEC-132b),
 *     plus State-A citations on the index and the obligations
 *     (hhi_high_fact_id / program_dollars_high_fact_id, dataset
 *     fct_program_concentration, measures "hhi-high"/"obligations-high" —
 *     distinct tokens so gate 23 leg a2 can never group a high-only figure
 *     with an all-tier one).
 *   WITHHELD — [data-concentration-withheld="below-floor"], one sentence,
 *     and NOTHING else: no band (so no vintage line), no [data-amount], no [data-measure], no
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

/**
 * The Index tooltip's bands, built from the constants hhiBand applies (Task
 * 26: the hand-typed "1500–2500 moderate; >2500 concentrated" called an index
 * of exactly 2,500 moderate while the badge beside it said Highly
 * Concentrated). Since #132 (decided 2026-09-25) the constants are the 2023
 * Merger Guidelines': 1,000 through 1,800 moderately concentrated, only an
 * index ABOVE 1,800 highly concentrated — and the tooltip names that
 * vintage. The DOJ page names no band below 1,000; "unconcentrated" is this
 * site's word there (R-DEC-132b; "competitive" until 2026-09-26), and the
 * sentence says so.
 */
const fmtBand = (n: number) => n.toLocaleString("en-US");
const HHI_TOOLTIP =
  "Herfindahl-Hirschman Index: 0–10,000. " +
  `${HHI_BANDS_VINTAGE} bands: ${fmtBand(HHI_MODERATE_MIN)} to ${fmtBand(HHI_CONCENTRATED_MIN)} moderately concentrated; ` +
  `above ${fmtBand(HHI_CONCENTRATED_MIN)} highly concentrated; ` +
  `below ${fmtBand(HHI_MODERATE_MIN)} this site says unconcentrated. ` +
  "Computed from high-confidence award links only, on positive-only " +
  "contractor shares — click the value for the formula.";

const BAND_COLOR: Record<string, string> = {
  unconcentrated: "text-green-700",
  moderate: "text-yellow-700",
  concentrated: "text-red-700",
};

function ConcentrationSection({ children }: { children: React.ReactNode }) {
  return (
    <section aria-labelledby="concentration-heading" className="mb-8">
      <h2
        id="concentration-heading"
        className="mb-4 text-foreground"
      >
        Contractor concentration
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
            {CONCENTRATION_WITHHELD_REASON} An index below that floor is a
            fact about the sample, not about the market. Whatever further
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
                title={HHI_TOOLTIP}
              >
                ⓘ
              </span>
            </div>
            <div className={`t-figure t-figure--4 ${color}`}>
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
            {/* R-DEC-132b: the bands' vintage as VISIBLE text under the band
                — the ⓘ title above carries it too, but a hover title cannot
                reach a reader on a phone. hhiBandVintageLine: "2023 Merger
                Guidelines bands", or "Below the 2023 Merger Guidelines
                bands" under Unconcentrated. scripts/gates/coverage.mjs reads
                it back. */}
            <div className="text-xs text-muted-foreground" data-hhi-band-vintage="">
              {hhiBandVintageLine(head.hhi)}
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
            <div className="t-figure t-figure--4 text-foreground">
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
            <div className="t-figure t-figure--4">
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

        {/* The positive/net sentence is the f15-family-browser card's
            disclosure, carried onto the high basis (integration 2026-09-25):
            both halves are what the two cited formulas say —
            hhi_high "obligation > 0 (positive-only shares …)",
            program_dollars_high "(net of deobligations)". */}
        <p className="mt-3 text-xs text-muted-foreground">
          High-confidence award links only, pooled across ingested years. The
          index uses positive obligations; program obligations are net of
          deobligations. The figures over every published
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
