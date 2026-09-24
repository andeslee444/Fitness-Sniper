"use client";

import React, { useEffect, useState } from "react";
import { ExternalLink, FileText } from "lucide-react";
import { fetchBudgetPdfReceipt, type BudgetPdfReceipt as Receipt } from "@/lib/budget-pdf-receipts";
import { PdfView } from "./pdf-view";
import styles from "./budget-pdf-receipt.module.css";

/** PDF evidence supplements the original facts; never replaces their accounting basis. */
export function BudgetPdfReceipt({ factId, children }: { factId: string; children: React.ReactNode }) {
  const [loaded, setLoaded] = useState<{ id: string; receipt: Receipt | null } | null>(null);
  const [selected, setSelected] = useState(0);
  useEffect(() => {
    let cancelled = false;
    fetchBudgetPdfReceipt(factId).then(receipt => {
      if (!cancelled) { setLoaded({ id: factId, receipt }); setSelected(0); }
    });
    return () => { cancelled = true; };
  }, [factId]);
  const receipt = loaded?.id === factId ? loaded.receipt : null;
  if (!receipt) return <>{children}</>;
  if (!receipt.parts.length) return <div className={styles.receipt}>
    <p className={styles.context} role="status">{receipt.blank_zero_count > 0 && receipt.unmatched_count === 0
      ? "The spreadsheet records zero. The PDF leaves these entries blank, so there is no printed number to highlight."
      : "An exact printed amount has not been verified in the matching PDF. The original spreadsheet evidence is shown below."}</p>
    {children}
  </div>;
  const part = receipt.parts[selected] ?? receipt.parts[0];
  const number = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 3 });
  return <section data-testid="budget-pdf-receipt" className={styles.receipt}>
    <div className={styles.heading}><FileText size={18} aria-hidden="true" /><h3>Budget document receipt</h3></div>
    <p className={styles.status} data-testid="pdf-workbook-match">
      {receipt.complete ? "Matches the published spreadsheet" : "Partially matched to the published spreadsheet"}
    </p>
    {receipt.parts.length > 1 && <p className={styles.context}>
      {receipt.parts.length} printed amounts {receipt.complete ? "sum" : "contribute"} to {number(receipt.amount_thousands)} USD thousands.
      Each contributing amount is shown on its original PDF page.
    </p>}
    {receipt.blank_zero_count > 0 && <p className={styles.context}>
      {receipt.blank_zero_count} spreadsheet {receipt.blank_zero_count === 1 ? "entry is" : "entries are"} zero with no printed number in the PDF. No highlight is claimed for those entries.
    </p>}
    {receipt.unmatched_count > 0 && <p role="status" className={styles.context}>Some entries do not have a verified PDF amount. Their spreadsheet receipts remain available below.</p>}
    {receipt.parts.length > 1 && <div className={styles.parts} role="group" aria-label="Contributing PDF amounts">
      {receipt.parts.map((p, i) => <button type="button" key={`${p.sha256}-${p.workbook_cell}-${i}`}
        aria-pressed={i === selected} onClick={() => setSelected(i)} className={styles.part}>
        <span>{p.program} · Line {p.line}</span><strong>{number(p.amount_thousands)}</strong>
        {p.row_label && <small>{p.row_label}</small>}
        <small>{p.column_label} · PB{p.edition}</small>
      </button>)}
    </div>}
    <p className={styles.context}>{part.program} · {part.exhibit} · PB{part.edition}{part.row_label ? ` · ${part.row_label}` : ""}<br />{part.pdf_column_label ?? part.column_label} · Total obligational authority · USD thousands</p>
    <a className={styles.source} href={`${part.official_url?.split("#")[0]}#page=${part.page_number}`} target="_blank" rel="noopener noreferrer">
      <ExternalLink size={16} aria-hidden="true" />Open government PDF · page {part.page_number}<span className="sr-only"> (opens in new tab)</span>
    </a>
    <PdfView key={`${part.sha256}-${part.page_number}-${part.workbook_cell}`} citation={part} showOfficialLink={false} />
    <p className={styles.context}>PDF amount checked against spreadsheet cell {part.workbook_cell}. The highlight is an overlay; the government document is unchanged.</p>
    <details className={styles.details}><summary>Spreadsheet downloads &amp; calculation details</summary><div className={styles.original}>{children}</div></details>
  </section>;
}
