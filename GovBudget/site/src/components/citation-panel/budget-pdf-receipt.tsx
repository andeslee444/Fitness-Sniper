"use client";

import React, { createContext, useEffect, useState } from "react";
import { ExternalLink, FileText } from "lucide-react";
import { budgetPdfSourceDocuments, budgetPdfWorkbookDownloads, officialDocumentUrl } from "@/lib/source-document";
import { fetchBudgetPdfReceipt, type BudgetPdfReceipt as Receipt } from "@/lib/budget-pdf-receipts";
import { WorkbookDownload } from "@/components/workbook-download";
import { PdfView } from "./pdf-view";
import styles from "./budget-pdf-receipt.module.css";

/**
 * Where the `beside` evidence handed to <BudgetPdfReceipt> is on screen, as
 * the children see it (integration 2026-09-25, gate 4):
 *
 *  - "pending" — the receipt is still resolving, so the layout is not final.
 *    A child must not render its own copy yet: that copy would be torn down
 *    and re-parented into the collapsed details the moment a PDF receipt
 *    lands (a flash for the reader, a detached element for gate 4).
 *  - "beside"  — the receipt leads with the PDF page and renders `beside` in
 *    the open directly under it; the children sit in the collapsed details
 *    and must not render it a second time.
 *  - "inline"  — no PDF page leads (no receipt, or no verified printed
 *    amount); the children render in the open and show their own copy.
 *
 * Outside a receipt, and inside one given no `beside`, the value is always
 * "inline" — the children behave exactly as they did before this existed.
 */
export type BesideEvidencePlacement = "pending" | "beside" | "inline";
export const BesideEvidenceContext = createContext<BesideEvidencePlacement>("inline");

/**
 * The fact's PDF receipt, plus whether its lookup has SETTLED. Same contract
 * as useBudgetPdfReceipt (a changed fact never keeps the previous fact's
 * evidence while loading, one fetch per fact) — the receipt needs "still
 * resolving" told apart from "resolved to none" to place `beside` without a
 * flash. A rejected lookup settles as none: the spreadsheet evidence then
 * renders in the open, never waits forever.
 */
function useSettledReceipt(factId: string): { settled: boolean; receipt: Receipt | null } {
  const [loaded, setLoaded] = useState<{ id: string; receipt: Receipt | null } | null>(null);
  useEffect(() => {
    let cancelled = false;
    Promise.resolve(fetchBudgetPdfReceipt(factId))
      .catch(() => null)
      .then(receipt => { if (!cancelled) setLoaded({ id: factId, receipt: receipt ?? null }); });
    return () => { cancelled = true; };
  }, [factId]);
  return loaded && loaded.id === factId ? { settled: true, receipt: loaded.receipt } : { settled: false, receipt: null };
}

/**
 * PDF evidence supplements the original facts; never replaces their accounting basis.
 *
 * `beside` (optional): evidence that must stay VISIBLE when the receipt leads
 * with the PDF page, instead of folding into the collapsed "Spreadsheet
 * downloads & calculation details" with the rest of `children`. The panel
 * passes a workbook fact's cell preview (§P1-9: the drawer shows the cited
 * cells in their neighbourhood) — the spreadsheet side of the "PDF amount
 * checked against spreadsheet cell …" line it sits under. Where no PDF page
 * leads, `beside` is not rendered and the children show their own copy
 * (BesideEvidenceContext).
 */
export function BudgetPdfReceipt({ factId, children, beside }: { factId: string; children: React.ReactNode; beside?: React.ReactNode }) {
  const { settled, receipt } = useSettledReceipt(factId);
  const [selection, setSelection] = useState<{ factId: string; index: number } | null>(null);
  const selected = selection?.factId === factId ? selection.index : 0;
  // No `beside` handed in → nothing to place: the children keep their own copy.
  const placed = (placement: BesideEvidencePlacement): BesideEvidencePlacement =>
    beside === undefined ? "inline" : placement;
  if (!receipt) return <BesideEvidenceContext.Provider value={placed(settled ? "inline" : "pending")}>{children}</BesideEvidenceContext.Provider>;
  if (!receipt.parts.length) return <div className={styles.receipt}>
    {budgetPdfSourceDocuments(receipt).map(document => <a key={document.url} className={styles.source} href={document.url} target="_blank" rel="noopener noreferrer">
      <ExternalLink size={16} aria-hidden="true" />{document.label} · {document.title}<span className="sr-only"> (opens in new tab)</span>
    </a>)}
    <p className={styles.context} role="status">{receipt.blank_zero_count > 0 && receipt.unmatched_count === 0
      ? "The spreadsheet records zero. The PDF leaves these entries blank, so there is no printed number to highlight."
      : "An exact printed amount has not been verified in the matching PDF. The original spreadsheet evidence is shown below."}</p>
    <BesideEvidenceContext.Provider value="inline">{children}</BesideEvidenceContext.Provider>
  </div>;
  const part = receipt.parts[selected] ?? receipt.parts[0];
  const officialUrl = officialDocumentUrl(part);
  const headingUrl = part.identity_page_number != null && Number.isInteger(part.identity_page_number)
    && part.identity_page_number > 0 && part.identity_page_number !== part.page_number
    ? officialDocumentUrl({ ...part, page_number: part.identity_page_number }) : null;
  const download = budgetPdfWorkbookDownloads({ ...receipt, parts: [part] })[0];
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
        aria-pressed={i === selected} onClick={() => setSelection({ factId, index: i })} className={styles.part}>
        <span>{p.program}{p.line ? ` · Line ${p.line}` : ""}</span><strong>{number(p.amount_thousands)}</strong>
        {p.row_label && <small>{p.row_label}</small>}
        <small>{p.column_label} · PB{p.edition}</small>
      </button>)}
    </div>}
    <p className={styles.context}>{part.program} · {part.exhibit} · PB{part.edition}{part.row_label ? ` · ${part.row_label}` : ""}<br />{part.pdf_column_label ?? part.column_label} · Total obligational authority · USD thousands</p>
    {officialUrl && <a className={styles.source} href={officialUrl} target="_blank" rel="noopener noreferrer">
      <ExternalLink size={16} aria-hidden="true" />Open government PDF · page {part.page_number}<span className="sr-only"> (opens in new tab)</span>
    </a>}
    {headingUrl && <p className={styles.context}>
      This line continues from the program heading on another page.{" "}
      <a className={styles.headingLink} href={headingUrl} target="_blank" rel="noopener noreferrer">
        Program heading · government PDF page {part.identity_page_number}<span className="sr-only"> (opens in new tab)</span>
      </a>
    </p>}
    {download && <div className={styles.download}>
      <WorkbookDownload {...download} label="Download government spreadsheet" className={styles.source} />
      <p className={styles.context}>Complete original workbook · saves as {download.filename}.</p>
    </div>}
    <PdfView key={`${part.sha256}-${part.page_number}-${part.workbook_cell}`} citation={part} showOfficialLink={false} />
    <p className={styles.context}>PDF amount checked against spreadsheet cell {part.workbook_cell}. The highlight is an overlay; the government document is unchanged.</p>
    {beside !== undefined && <div data-testid="receipt-beside" className={styles.beside}>{beside}</div>}
    <details className={styles.details}><summary>Spreadsheet downloads &amp; calculation details</summary><div className={styles.original}>
      <BesideEvidenceContext.Provider value={placed("beside")}>{children}</BesideEvidenceContext.Provider>
    </div></details>
  </section>;
}
