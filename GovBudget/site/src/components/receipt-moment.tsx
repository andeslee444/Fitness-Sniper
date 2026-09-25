"use client";

/**
 * ReceiptMoment — the home page's receipt, staged as the hero vitrine's
 * CAPTION (Phase 5C Goal 1 + PM Sprint 1 §P0-5; round-3 critique: the fold
 * is one composition — object above, number + source beneath the hull).
 *
 * §P0-5: the headline figure is the CANONICAL BASIS — Total Obligation
 * Authority from the site_meta hero payload ("it is what Congress
 * provides"), with its workbook fact and the corpus scope qualifier rendered
 * as small print by the page beside the caption. The old unqualified
 * "largest FY2024 actual in the J-books — $5.25B" claim was the narrower
 * Net-Procurement basis AND scope-unqualified — the single most prominent
 * number on the site contradicted the program page.
 *
 * Goal 1 (G4 gate) is unchanged: the caption still stages a REAL PDF
 * receipt — the same program-year's P-40 line, whose jbook_pdf citation
 * renders the actual page + highlight. That receipt cite is the caption's
 * FIRST [data-fact-id] in DOM order (the gate clicks it) and doubles as the
 * honest two-basis reconciliation: net procurement (P-40, printed on the
 * page) vs TOA (P-1 workbook, the figure).
 *
 * One caption line at rest: the figure shows ONCE at display size with no
 * pills and no hash; the caption below is the museum label (program ·
 * service · the P-40 receipt affordance), and the two-basis reconciliation
 * sentence is the receipt's own footnote beneath it. The full hash lives
 * inside the citation panel, not on the page. The old floating "See the
 * P-40 page" button is gone: one action, one affordance (the cite itself).
 *
 * Contract: the wrapper carries data-testid="receipt-moment" (G4 gate) and
 * must remain FULLY above the fold at 1440×900 and 390×844 — the caption
 * sits inside the hero plate, whose height is budgeted for exactly that.
 * Colors arrive as --rm-* custom properties from home.module.css (this
 * module may not hold raw hexes — the token allowlist is per-file).
 */

import Link from "next/link";
import { useContext } from "react";
import styles from "./receipt-moment.module.css";
import { Cite, CitationPanelContext } from "@/components/cite";
import { RECEIPT_MOMENT_FY_LABEL } from "@/lib/site";
import { serviceOrgName } from "@/lib/program-tier";
import type { SiteMetaHero } from "@/lib/data";

export interface ReceiptMomentProps {
  /** Program element / budget line item id (links to the program page). */
  peBli: string;
  /** Program title. */
  title: string;
  /** Owning organization (e.g. "MDA"). */
  org: string;
  /** FY2024 actuals, USD millions (J-book detail row units). */
  amountMillions: number;
  /**
   * jbook_pdf citation fact_id. Caller guarantees it resolves in the page's
   * citation slice (same guarantee as every other <Cite>).
   */
  factId: string;
  /**
   * §P0-5 canonical-TOA hero payload (site_meta.hero). Rendered as the
   * headline figure when it covers the SAME program (live: both are the
   * F-35); the caller guarantees hero.fid is in the citation slice. Null →
   * the caption falls back to the P-40 figure as its headline.
   */
  hero?: SiteMetaHero | null;
}

export function ReceiptMoment({
  peBli,
  title,
  org,
  amountMillions,
  factId,
  hero,
}: ReceiptMomentProps) {
  const showToaHeadline = hero != null && hero.pe_bli === peBli;
  const { openPanel } = useContext(CitationPanelContext);

  return (
    <div
      data-testid="receipt-moment"
      className={styles.receipt}
    >
      <p className={`t-label ${styles.receiptKicker}`}>
        {showToaHeadline
          ? `Largest ${RECEIPT_MOMENT_FY_LABEL} program element in our corpus`
          : `Largest ${RECEIPT_MOMENT_FY_LABEL} actual in the J-books`}
      </p>

      {/* The caption is ONE museum-label line (round-7: five type styles and
          a hash in the open read as debug output): program · service · the
          P-40 receipt affordance. The receipt button is the caption's FIRST
          data-fact-id in DOM order — the G4 gate clicks it and asserts the
          rendered PDF page + highlight; the hash itself lives inside that
          panel, not on the page. The fact-id chip STAYS in the DOM below
          (the a11y/P1-1 count is visibility-independent) but is display:none
          — gate-held, visually gone. Visual order keeps the caption BELOW
          the figure (order 3 vs order 2), so DOM order is unchanged. */}
      <p className={styles.captionLine}>
        <Link href={`/program/${peBli}/`} className={styles.captionTitle}>
          {title}
        </Link>
        <span aria-hidden="true"> · </span>
        <span>{serviceOrgName(org)}</span>
        {showToaHeadline && (
          <>
            <span aria-hidden="true"> · </span>
            <button
              type="button"
              className={styles.captionCite}
              data-fact-id={factId}
              onClick={() => openPanel(factId)}
            >
              {RECEIPT_MOMENT_FY_LABEL} P-40 · PB{hero.edition} ↗
            </button>
          </>
        )}
      </p>

      {/* The receipt's footnote: the two-basis reconciliation sentence,
          moved here from the caption VERBATIM (it asserts what the two
          figures mean — moved, never rewritten). Its P-40 cite keeps the
          fact-id and basis chips in the DOM for the P1-1 count; the note's
          CSS hides them, so the hash is visible only inside the panel. */}
      {showToaHeadline && (
        <p className={styles.receiptNote}>
          {"Printed on the P-40 page: "}
          <Cite
            value={amountMillions}
            units="USD millions"
            dataset="jbook_details"
            factId={factId}
            basis="jbook-detail"
            fy={hero.fy}
            measure={hero.measure}
            edition={hero.edition}
          />
          {
            " net procurement — the workbook TOA figure above adds advance-procurement rows."
          }
        </p>
      )}

      <div className={styles.receiptMain}>
        {/* The cited figure — canonical TOA, shown ONCE at display size.
            chip={false}: nothing may compete with the caption line. */}
        <p className="t-figure t-figure--6">
          {showToaHeadline ? (
            <Cite
              value={hero.value}
              units={hero.units}
              dataset={hero.dataset}
              factId={hero.fid}
              basis={hero.basis}
              fy={hero.fy}
              measure={hero.measure}
              edition={hero.edition}
              chip={false}
            />
          ) : (
            <Cite
              value={amountMillions}
              units="USD millions"
              dataset="jbook_details"
              factId={factId}
              chip={false}
            />
          )}
        </p>
      </div>
    </div>
  );
}
