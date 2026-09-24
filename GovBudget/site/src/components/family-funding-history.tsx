"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, FileSpreadsheet } from "lucide-react";
import { Cite } from "@/components/cite";
import { formatAmount } from "@/lib/format";
import { familyHistorySeries, type FamilyFundingHistoryData, type FamilyFundingPoint } from "@/lib/family-funding-history";
import styles from "./family-funding-history.module.css";

function AnnualFigure({ point, familyId }: { point: FamilyFundingPoint; familyId: string }) {
  return <Cite value={point.amount_thousands} units="USD thousands" factId={point.fact_id}
    dataset="f15_funding_history" basis="toa" fy={point.fy} measure={point.measure}
    edition={point.edition} entity={`family:${familyId}`} exhibitFamily="mixed" chip={false} />;
}

/** Family scope is independent of the aircraft variant or individual record below. */
export function FamilyFundingHistory({ history, shortName }: { history: FamilyFundingHistoryData; shortName: string }) {
  const series = familyHistorySeries(history);
  const [selectedId, setSelectedId] = useState(series.at(-1)!.id);
  const selected = series.find(point => point.id === selectedId)!;
  const max = Math.max(1, ...series.map(point => point.amount_thousands));
  const total = history.cumulative;

  return <section className={styles.overview} aria-label={`${shortName} family funding history`} data-family-history={history.family_id}>
    <div className={styles.summary} data-testid="family-receipt" data-family-cumulative={total.fact_id}>
      <div className={styles.total}>
        <h2 className={styles.heading}>{shortName} family funding</h2>
        <p className={styles.caption} data-testid="family-receipt-kicker">Recorded actuals · FY{total.start_fy}–{total.end_fy}</p>
        <div className={`t-figure t-figure--4 ${styles.figure}`} data-testid="family-receipt-figure">
          <Cite value={total.amount_thousands} units="USD thousands" factId={total.fact_id}
            dataset="f15_funding_history" basis="toa" fy={`${total.start_fy}-${total.end_fy}`}
            measure={total.measure} entity={`family:${history.family_id}`} exhibitFamily="mixed" chip={false} />
        </div>
        <p className={styles.scope}>Development, aircraft purchases, upgrades and support across the identified F-15 budget lines.</p>
        <p className={styles.coverage} data-history-coverage="">Coverage starts in FY{history.start_fy}; earlier funding is not included. Newer enacted funding and requests are shown separately.</p>
      </div>
      <div className={styles.timeline}>
        <div className={styles.selected} aria-live="polite" aria-atomic="true">
          <p className={styles.caption}>FY{selected.fy} · {selected.measure_label}{selected.coverage === "partial" ? " · Partial coverage" : ""}</p>
          <div className="t-figure t-figure--2" data-history-selected={selected.id}><AnnualFigure point={selected} familyId={history.family_id} /></div>
        </div>
        <div className={styles.bars} role="group" aria-label="Funding by fiscal year">
          {series.map(point => <button key={point.id} type="button" className={styles.year}
            aria-label={`FY${point.fy} ${point.measure_label}, ${formatAmount(point.amount_thousands, "USD thousands")}${point.coverage === "partial" ? ", partial coverage" : ""}`}
            aria-pressed={selected.id === point.id} aria-controls="family-history-receipts"
            data-history-year={point.fy} data-history-fact={point.fact_id} data-kind={point.kind}
            onClick={() => setSelectedId(point.id)}>
            <span className={styles.track} aria-hidden="true"><span className={styles.bar} style={{ height: `${Math.max(1, point.amount_thousands / max * 100)}%` }} /></span>
            <span className={styles.yearLabel}>{String(point.fy).slice(-2)}</span>
          </button>)}
        </div>
        <div className={styles.legend} aria-label="Chart legend">
          <span data-kind="actuals">Actuals</span><span data-kind="enacted">Enacted</span><span data-kind="request">Request</span>
          <span className={styles.chartHint}>Select a year for receipts</span>
        </div>
      </div>
    </div>
    <details className={styles.ledger} data-testid="family-ledger" id="family-history-receipts">
      <summary>FY{selected.fy} · {selected.components.length} source rows · View funding & receipts</summary>
      <p className={styles.caption} data-basis-declared="">P-1/R-1 TOA · PB{selected.edition} · {selected.measure_label} · Nominal dollars, without inflation adjustment.</p>
      <p className={styles.scope}>{history.scope_note}</p>
      {selected.missing_programs.length > 0 && <p className={styles.coverage} data-history-missing="">Missing from this year’s total: {selected.missing_programs.join(", ")}. Missing coverage is not zero funding.</p>}
      <dl className={styles.rows}>
        {selected.components.map(row => <div className={styles.row} key={row.fact_id} data-history-input={row.fact_id}>
          <dt>{row.program_slug ? <Link href={`/program/${row.program_slug}/`}>{row.title}</Link> : row.title}
            <span className={styles.rowMeta}>{row.pe_bli} · {row.exhibit} · Activity {row.budget_activity}</span>
          </dt>
          <dd className="t-figure t-figure--1"><Cite value={row.amount_thousands} units="USD thousands" factId={row.fact_id}
            dataset={row.dataset} basis="toa" fy={selected.fy} measure={row.measure} edition={selected.edition}
            entity={`family-input:${row.fact_id}`} exhibitFamily={row.exhibit.toLowerCase().startsWith("p") ? "procurement" : "rdte"} chip={false} /></dd>
          <dd className={styles.source}><a href={row.official_url} target="_blank" rel="noopener noreferrer" aria-label={`Open government spreadsheet for ${row.title}, FY${selected.fy}, activity ${row.budget_activity}`}>
            <FileSpreadsheet size={15} aria-hidden="true" /> Government spreadsheet <ArrowUpRight size={13} aria-hidden="true" />
          </a><span>{row.sheet} · {row.cells}</span></dd>
        </div>)}
      </dl>
      <div className={styles.notes}><p>{total.scope_note}</p>{history.coverage_notes.map(note => <p key={note}>{note}</p>)}</div>
    </details>
  </section>;
}
