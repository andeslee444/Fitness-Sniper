import Link from "next/link";
import type { ProgramHHI } from "@/lib/data";
import { Cite } from "@/components/cite";
import { hhiBand } from "@/lib/hhi-band.mjs";
import {
  concentrationHeadline,
  awardsAcrossFamilies,
  HIGH_ONLY_MIN_AWARDS,
  HIGH_ONLY_MIN_FAMILIES,
} from "@/lib/concentration-basis";

/**
 * ProgramConcentration — HHI concentration card, TWO bases (ROADMAP #80).
 *
 * Shown only when the block is non-null. The HEADLINE basis is decided by
 * concentrationHeadline() (lib/concentration-basis.ts): high-confidence
 * links alone where the high-only index publishes, the all-tier figure
 * otherwise. Every figure is State A via a derived citation fact_id carried
 * on programs.json (dataset fct_program_concentration):
 *   - all-tier HHI / dollars → hhi_all_fact_id / program_dollars_all_fact_id
 *     (the pre-#80 fids; measures "hhi" / "obligations", unchanged)
 *   - high-only HHI / dollars → hhi_high_fact_id / program_dollars_high_fact_id
 *     (measures "hhi-high" / "obligations-high" — distinct on purpose, see
 *     the helper's doc-comment on gate 23 leg a2)
 *
 * Three shapes, one [data-concentration-secondary] line each:
 *   A basis=high  — headline high-only; second line "Including
 *                   medium-confidence links: …" with the all-tier figures
 *   B basis=all   — high links exist but sit below the floor; second line
 *                   states what they amount to and why no index is shown
 *   C basis=all   — no high link; second line says so
 *
 * Band vocabulary lives in hhi-band.mjs (backlog #57) — this is the
 * DESTINATION page a homepage/feed concentration claim links to, and
 * scripts/gates/feed.mjs leg (l) reads the ONE [data-hhi-band] below (and,
 * since #80, its data-hhi-basis) to check that claim against what this page
 * actually renders. The second line's band is plain text on purpose: a
 * second [data-hhi-band] would fail leg (l). Color stays local.
 */

interface ProgramConcentrationProps {
  hhi: ProgramHHI | null;
}

const BAND_COLOR: Record<string, string> = {
  competitive: "text-green-700",
  moderate: "text-yellow-700",
  concentrated: "text-red-700",
};

const CHIP_COLOR: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  all: "bg-yellow-100 text-yellow-800",
};

export function ProgramConcentration({ hhi }: ProgramConcentrationProps) {
  if (!hhi) return null;

  const head = concentrationHeadline(hhi);
  const band = hhiBand(head.hhi);
  const { label } = band;
  const color = BAND_COLOR[band.key];
  const allBand = hhiBand(hhi.hhi_all);

  return (
    <section
      aria-labelledby="concentration-heading"
      className="mb-8"
      data-concentration-basis={head.basis}
    >
      <h2
        id="concentration-heading"
        className="text-lg font-semibold mb-4 text-foreground"
      >
        Contractor Concentration
      </h2>

      <div className="rounded-lg border border-border bg-card p-4">
        {/* Tier chip — the headline's basis, stated where a reader sees it. */}
        <div className="mb-3 text-xs text-muted-foreground">
          Basis:{" "}
          <span
            data-concentration-tier-chip={head.basis}
            className={`inline-block px-1.5 py-0.5 rounded font-medium ${CHIP_COLOR[head.basis]}`}
            title={
              head.basis === "high"
                ? `Computed from high-confidence award links only (${awardsAcrossFamilies(head.award_count, head.family_count)}).`
                : "Computed from every published link, including medium-confidence ones — an account or agency association, not proof this line paid."
            }
          >
            {head.chip}
          </span>
        </div>

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
                title="Herfindahl-Hirschman Index: 0–10,000. <1500 competitive; 1500–2500 moderate; >2500 concentrated. Derived from positive-only contractor shares — click the value for the formula."
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
            {/* data-hhi-band: the headline's pooled all-years band, the ONE
                stable selector for scripts/gates/feed.mjs leg (l); since #80
                it also declares which basis it is. See hhi-band.mjs. */}
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
                title="Total contract obligations attributed to this program element on the basis stated above. Derived — click the value for the formula."
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

        {/* The OTHER basis — always printed, always labelled. */}
        {head.basis === "high" && (
          <p
            data-concentration-secondary="all"
            className="mt-3 text-xs text-muted-foreground"
          >
            Including medium-confidence links: HHI{" "}
            <Cite
              value={hhi.hhi_all}
              units="USD"
              dataset="fct_program_concentration"
              factId={hhi.hhi_all_fact_id}
              display={hhi.hhi_all.toFixed(0)}
              basis="usaspending"
              fy="all-years"
              measure="hhi"
            />{" "}
            ({allBand.label}), {hhi.family_count_all} contractor{" "}
            {hhi.family_count_all === 1 ? "family" : "families"} across{" "}
            {hhi.award_count_all} award{hhi.award_count_all === 1 ? "" : "s"},
            top contractor {hhi.top_family_all},{" "}
            <Cite
              value={hhi.program_dollars_all}
              units="USD"
              dataset="fct_program_concentration"
              factId={hhi.program_dollars_all_fact_id}
              basis="usaspending"
              fy="all-years"
              measure="obligations"
            />
            .
          </p>
        )}
        {head.basis === "all" && hhi.program_dollars_high !== null && (
          <p
            data-concentration-secondary="high"
            className="mt-3 text-xs text-muted-foreground"
          >
            High-confidence links alone:{" "}
            {awardsAcrossFamilies(hhi.award_count_high, hhi.family_count_high)},{" "}
            <Cite
              value={hhi.program_dollars_high}
              units="USD"
              dataset="fct_program_concentration"
              factId={hhi.program_dollars_high_fact_id}
              basis="usaspending"
              fy="all-years"
              measure="obligations-high"
            />{" "}
            — below the {HIGH_ONLY_MIN_AWARDS}-award, {HIGH_ONLY_MIN_FAMILIES}-family
            floor for a high-only index, so the figures above include
            medium-confidence links.
          </p>
        )}
        {head.basis === "all" && hhi.program_dollars_high === null && (
          <p
            data-concentration-secondary="none"
            className="mt-3 text-xs text-muted-foreground"
          >
            No high-confidence link on this line; every figure above rests on
            medium-confidence links (an account or agency association, not
            proof this line paid).
          </p>
        )}
      </div>
    </section>
  );
}
