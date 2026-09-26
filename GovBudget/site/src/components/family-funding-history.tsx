"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { Cite } from "@/components/cite";
import { formatAmount } from "@/lib/format";
import { familyHistorySeries, type FamilyFundingHistoryView, type FamilyFundingPointSummary } from "@/lib/family-funding-history";
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
  const tableRef = useRef<HTMLDivElement>(null);
  function selectYear(id: string) {
    setSelectedId(id);
    tableRef.current?.querySelector<HTMLElement>(`[data-history-column="${id}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
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
            onClick={() => selectYear(point.id)}>
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
        <h3 id="family-history-table-heading">Programs across the years</h3>
        <p>{history.programs.length} program rows · {series.length} fiscal years</p>
      </div>
      <p className={styles.caption} id="family-history-table-description" data-basis-declared="">P-1/R-1 TOA · Nominal dollars, without inflation adjustment. Each amount opens to its source documents and calculation.</p>
      <div className={styles.matrixKey}><span>0 = recorded zero · — = no figure in covered records</span><span>Scroll for all years →</span></div>
      <div ref={tableRef} className={`${styles.tableScroll} ${styles.matrixScroll}`} role="region" aria-label="Program funding matrix, scroll for all fiscal years" tabIndex={0}>
        <table className={`${styles.table} ${styles.matrix}`} id="family-history-receipts" aria-labelledby="family-history-table-heading" aria-describedby="family-history-table-description">
          <thead><tr><th scope="col" className={styles.matrixCorner}>Program / budget line</th>{series.map(point => <th key={point.id} scope="col" id={`history-col-${point.id}`} data-history-column={point.id} data-selected={selected.id === point.id} data-kind={point.kind}>
            <span className={styles.fiscalYear}>FY{point.fy}</span>
            <span className={styles.columnStatus} title={point.measure_label}>{point.kind === "actuals" ? "Actuals" : point.kind === "request" ? "Request" : "Current year"}</span>
            <span className={styles.columnEdition}>PB{point.edition}</span>
          </th>)}</tr></thead>
          <tbody>
            <tr className={styles.matrixTotal}><th scope="row" id="history-row-total">F-15 family total<span className={styles.rowMeta}>Covered programs</span></th>{series.map(point => <td key={point.id} headers={`history-row-total history-col-${point.id}`} data-history-annual={point.id} data-selected={selected.id === point.id}>
              <AnnualFigure point={point} familyId={history.family_id} />
              {point.coverage === "partial" && <span className={styles.partial}>Partial</span>}
            </td>)}</tr>
            {history.programs.map((program, index) => <tr key={program.id} data-history-program={program.id}>
              <th scope="row" id={`history-row-${index}`} className={styles.matrixProgram}>
                <span className={styles.programCode}>{program.exhibit === "R-1" ? "PE" : "BLI"} {program.code}</span>
                {program.program_slug ? <Link href={`/program/${program.program_slug}/`}>{program.title}</Link> : <span>{program.title}</span>}
                <span className={styles.rowMeta}>{program.exhibit === "R-1" ? "Development" : "Procurement"}{!program.program_slug ? " · Historical code" : ""}</span>
              </th>
              {series.map(point => {
                const cell = point.program_cells.find(cell => cell.program_id === program.id);
                const missing = point.missing_programs.includes(program.code);
                return <td key={point.id} headers={`history-row-${index} history-col-${point.id}`} data-history-cell={point.id} data-selected={selected.id === point.id} data-history-inputs={cell?.input_fact_ids.join(",")} className={styles.matrixCell}>
                  {cell ? <Cite value={cell.amount_thousands} units="USD thousands" factId={cell.fact_id}
                    dataset={cell.dataset} basis="toa" fy={point.fy} measure={cell.measure} edition={point.edition}
                    entity={program.id} exhibitFamily={program.exhibit === "P-1" ? "procurement" : "rdte"} chip={false}
                    title={`${program.code} · FY${point.fy} · ${point.measure_label} · $${(cell.amount_thousands * 1000).toLocaleString("en-US")} · Open source documents`}
                    className={styles.cellAmount} /> : <span className={styles.emptyCell} data-history-missing={missing ? program.code : undefined} aria-label={`${program.code}, FY${point.fy}: ${missing ? "missing workbook figure" : "no figure in covered records"}`} title="Not included in the annual total; absence is not zero funding.">{missing ? "Missing" : "—"}</span>}
                </td>;
              })}
            </tr>)}
          </tbody>
        </table>
      </div>
      <p className={styles.matrixNote}>Rows follow the government’s PE or budget-line code across editions. Historical F0150P and F015E0 remain separate. Missing EPAWSS development figures in FY2025–2026 are excluded from those totals.</p>
      <details className={styles.notes}>
        <summary>Coverage and accounting notes</summary>
        <p>{history.scope_note}</p><p>{total.scope_note}</p>{history.coverage_notes.map(note => <p key={note}>{note}</p>)}
      </details>
    </section>
  </section>;
}
