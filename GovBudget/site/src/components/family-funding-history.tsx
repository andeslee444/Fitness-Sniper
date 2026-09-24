"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, FileSpreadsheet } from "lucide-react";
import { Cite } from "@/components/cite";
import { formatAmount } from "@/lib/format";
import { FAMILY_HISTORY_URL, familyHistoryInputRows, familyHistorySeries, type FamilyFundingHistoryView, type FamilyFundingPointSummary, type FamilyFundingInput } from "@/lib/family-funding-history";
import styles from "./family-funding-history.module.css";

function AnnualFigure({ point, familyId }: { point: FamilyFundingPointSummary; familyId: string }) {
  return <Cite value={point.amount_thousands} units="USD thousands" factId={point.fact_id}
    dataset="f15_funding_history" basis="toa" fy={point.fy} measure={point.measure}
    edition={point.edition} entity={`family:${familyId}`} exhibitFamily="mixed" chip={false} />;
}

/** Family scope is independent of the aircraft variant or individual record below. */
export function FamilyFundingHistory({ history, shortName }: { history: FamilyFundingHistoryView; shortName: string }) {
  const series = familyHistorySeries(history);
  const [selectedId, setSelectedId] = useState(series.at(-1)!.id);
  const selected = series.find(point => point.id === selectedId)!;
  const max = Math.max(1, ...series.map(point => point.amount_thousands));
  const total = history.cumulative;
  const [sourceRows, setSourceRows] = useState<Record<string, FamilyFundingInput[]>>({});
  const [sourceStatus, setSourceStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const needsSources = series.some(point => !point.components);
  useEffect(() => {
    if (!needsSources) return;
    const controller = new AbortController();
    fetch(FAMILY_HISTORY_URL, { signal: controller.signal })
      .then(response => {
        if (!response.ok) throw new Error("Family source file unavailable");
        return response.json() as Promise<unknown>;
      })
      .then(value => familyHistoryInputRows(value, history))
      .then(rows => {
        if (controller.signal.aborted) return;
        setSourceRows(rows);
        setSourceStatus("ready");
      })
      .catch(() => { if (!controller.signal.aborted) setSourceStatus("error"); });
    return () => controller.abort();
  }, [history, loadAttempt, needsSources]);

  function retrySources() {
    setSourceStatus("loading");
    setLoadAttempt(attempt => attempt + 1);
  }

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
          <span className={styles.chartHint}>All years and sources below</span>
        </div>
      </div>
    </div>
    <section className={styles.ledger} data-testid="family-ledger" aria-labelledby="family-history-table-heading">
      <div className={styles.tableHeading}>
        <h3 id="family-history-table-heading">Funding & sources by year</h3>
        <p>{series.length} years · {series.reduce((count, point) => count + point.component_count, 0)} source rows · Newest first</p>
      </div>
      <p className={styles.caption} id="family-history-table-description" data-basis-declared="">All identified F-15 program and activity rows in the covered workbooks. P-1/R-1 TOA · Nominal dollars, without inflation adjustment. Click an amount for its receipt.</p>
      {needsSources && sourceStatus !== "ready" && sourceStatus !== "error" && <p className={styles.coverage} role="status">Loading historical program rows… All annual totals remain available below.</p>}
      {sourceStatus === "error" && <div className={styles.coverage} role="alert">
        <p>Historical program rows could not be loaded. Annual totals and current-year sources remain available.</p>
        <button type="button" className={styles.retry} onClick={retrySources}>Retry loading source rows</button>
      </div>}
      <div className={styles.tableScroll} role="region" aria-label="Funding and source table, scroll for all years" tabIndex={0}>
        <table className={styles.table} id="family-history-receipts" aria-labelledby="family-history-table-heading" aria-describedby="family-history-table-description">
          <thead><tr><th scope="col">Fiscal year & family total</th><th scope="col">Program / budget line</th><th scope="col">Amount</th><th scope="col">Government source</th></tr></thead>
          {[...series].reverse().map(point => {
            const rows = point.components ?? sourceRows[point.id];
            const yearHeading = <th scope="rowgroup" className={styles.yearHeading} rowSpan={(rows?.length || 1) + point.missing_programs.length}>
              <span className={styles.fiscalYear}>FY{point.fy}</span>
              <span className={styles.rowMeta}>{point.measure_label}<br />PB{point.edition}</span>
              <div className={`t-figure t-figure--1 ${styles.annualTotal}`} data-history-annual={point.id}><AnnualFigure point={point} familyId={history.family_id} /></div>
              <span className={styles.rowMeta}>{point.component_count} source rows{point.coverage === "partial" ? " · Partial coverage" : ""}</span>
            </th>;
            return <tbody key={point.id} data-history-point={point.id} data-selected={selected.id === point.id}>
              {rows ? rows.map((row, index) => <tr key={row.fact_id} data-history-input={row.fact_id}>
                {index === 0 && yearHeading}
                <th scope="row" className={styles.program}>{row.program_slug ? <Link href={`/program/${row.program_slug}/`}>{row.title}</Link> : row.title}
                  <span className={styles.rowMeta}>{row.pe_bli} · {row.exhibit} · Activity {row.budget_activity}</span>
                </th>
                <td className={`t-figure t-figure--1 ${styles.amount}`}><Cite value={row.amount_thousands} units="USD thousands" factId={row.fact_id}
                  dataset={row.dataset} basis="toa" fy={point.fy} measure={row.measure} edition={point.edition}
                  entity={`family-input:${row.fact_id}`} exhibitFamily={row.exhibit.toLowerCase().startsWith("p") ? "procurement" : "rdte"} chip={false} /></td>
                <td className={styles.source}><a href={row.official_url} target="_blank" rel="noopener noreferrer" aria-label={`Open government spreadsheet for ${row.title}, FY${point.fy}, activity ${row.budget_activity}`}>
                  <FileSpreadsheet size={15} aria-hidden="true" /> Government spreadsheet <ArrowUpRight size={13} aria-hidden="true" />
                </a><span className={styles.rowMeta}>{row.sheet} · {row.cells}</span></td>
              </tr>) : <tr>{yearHeading}<td colSpan={3} className={styles.pending} data-history-pending="">{sourceStatus === "error" ? "Source rows unavailable — retry above." : `Loading ${point.component_count} source rows…`}</td></tr>}
              {point.missing_programs.map(name => <tr key={name} data-history-missing=""><td colSpan={3} className={styles.missing}>Missing workbook figure: {name}. Not included in this year’s total; missing coverage is not zero funding.</td></tr>)}
            </tbody>;
          })}
        </table>
      </div>
      <details className={styles.notes}>
        <summary>Coverage and accounting notes</summary>
        <p>{history.scope_note}</p><p>{total.scope_note}</p>{history.coverage_notes.map(note => <p key={note}>{note}</p>)}
      </details>
    </section>
  </section>;
}
