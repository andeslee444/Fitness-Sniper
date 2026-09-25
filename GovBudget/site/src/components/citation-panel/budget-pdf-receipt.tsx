"use client";

import React, { useState } from "react";
import { ExternalLink, FileText } from "lucide-react";
import { budgetPdfSourceDocuments, budgetPdfWorkbookDownloads, officialDocumentUrl } from "@/lib/source-document";
import { useBudgetPdfReceipt } from "@/components/use-budget-pdf-receipt";
import { WorkbookDownload } from "@/components/workbook-download";
import { PdfView } from "./pdf-view";
import styles from "./budget-pdf-receipt.module.css";

/** PDF evidence supplements the original facts; never replaces their accounting basis. */
export function BudgetPdfReceipt({ factId, children }: { factId: string; children: React.ReactNode }) {
  const receipt = useBudgetPdfReceipt(factId);
  const [selection, setSelection] = useState<{ factId: string; index: number } | null>(null);
  const selected = selection?.factId === factId ? selection.index : 0;
  if (!receipt) return <>{children}</>;
  if (!receipt.parts.length) return <div className={styles.receipt}>
    {budgetPdfSourceDocuments(receipt).map(document => <a key={document.url} className={styles.source} href={document.url} target="_blank" rel="noopener noreferrer">
      <ExternalLink size={16} aria-hidden="true" />{document.label} · {document.title}<span className="sr-only"> (opens in new tab)</span>
    </a>)}
    <p className={styles.context} role="status">{receipt.blank_zero_count > 0 && receipt.unmatched_count === 0
      ? "The spreadsheet records zero. The PDF leaves these entries blank, so there is no printed number to highlight."
      : "An exact printed amount has not been verified in the matching PDF. The original spreadsheet evidence is shown below."}</p>
    {children}
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
    <details className={styles.details}><summary>Spreadsheet downloads &amp; calculation details</summary><div className={styles.original}>{children}</div></details>
  </section>;
}
