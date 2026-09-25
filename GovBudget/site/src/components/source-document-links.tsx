"use client";

import { ExternalLink, ScanLine } from "lucide-react";
import { useContext, useEffect, useState } from "react";
import type { Citation, CitationsMap } from "@/lib/data";
import { budgetPdfSourceDocuments, citationSourceDocuments, resolveSourceCitationInputs } from "@/lib/source-document";
import { pagedAmountCitation } from "@/lib/citations";
import { trackReaderEvent } from "@/lib/reader-events";
import { resolveCitationFromShards } from "@/lib/cite-shards";
import { CopyButton } from "./copy-button";
import { WorkbookDownload } from "./workbook-download";
import { CitationPanelContext } from "./cite";
import { useBudgetPdfReceipt } from "./use-budget-pdf-receipt";
import styles from "./source-document-links.module.css";

const EMPTY_CITATIONS: CitationsMap = {};

export function SourceDocumentLinks({ citation, citations = EMPTY_CITATIONS, className = "", factId, program, surface = "source-document", compact = false, resolveInputs = false, showBudgetPdf = true }: {
  citation: Citation;
  citations?: CitationsMap | ((id: string) => Citation | undefined);
  className?: string;
  factId?: string;
  program?: string;
  surface?: string;
  compact?: boolean;
  /** Standalone receipts may have only the total's citation embedded. */
  resolveInputs?: boolean;
  /** The receipt already displays PDF evidence above its original-source disclosure. */
  showBudgetPdf?: boolean;
}) {
  const { openPanel } = useContext(CitationPanelContext);
  const receipt = useBudgetPdfReceipt(showBudgetPdf && (citation.kind === "workbook" || citation.kind === "derived") ? factId : null);
  const [resolved, setResolved] = useState<{ root: Citation; values: CitationsMap; incomplete: boolean } | null>(null);
  useEffect(() => {
    if (!resolveInputs || citation.kind !== "derived") return;
    let cancelled = false;
    const lookup = typeof citations === "function" ? citations : (id: string) => citations[id];
    resolveSourceCitationInputs(citation, lookup, resolveCitationFromShards, () => cancelled)
      .then(result => { if (!cancelled) setResolved({ root: citation, ...result }); });
    return () => { cancelled = true; };
  }, [citation, citations, resolveInputs]);
  const current = resolved?.root === citation ? resolved : null;
  const originals = citationSourceDocuments(citation, id => (typeof citations === "function" ? citations(id) : citations[id]) ?? current?.values[id]);
  const pdfDocuments = receipt ? budgetPdfSourceDocuments(receipt) : [];
  const pdfUrls = new Set(pdfDocuments.map(document => document.url));
  const documents = [...pdfDocuments, ...originals.filter(document => !pdfUrls.has(document.url))];
  if (!documents.length && !current?.incomplete) return null;
  const canHighlight = factId && showBudgetPdf && (Boolean(receipt?.parts.length) || (citation.kind === "jbook_pdf" && Boolean(pagedAmountCitation(citation))));
  const hasPdf = documents.some(document => document.kind === "pdf");
  const documentRows = documents.map(document => <div key={document.url} className={styles.document}>
      {document.workbook && <WorkbookDownload {...document.workbook} label={document.label} className={hasPdf ? styles.secondaryAction : styles.action}
        onDownload={() => trackReaderEvent("official_source_opened", { program, factId, surface, format: "xlsx" })} />}
      <a href={document.url} target="_blank" rel="noopener noreferrer" data-testid="official-source" className={document.workbook ? styles.original : canHighlight ? styles.secondaryAction : styles.action}
        onClick={() => trackReaderEvent("official_source_opened", { program, factId, surface })}>
        <ExternalLink size={16} aria-hidden="true" />
        <span>{document.workbook ? /\.(gov|mil)$/i.test(document.host) ? "Government original" : "Source original" : document.label}</span><span className="sr-only"> (opens in new tab)</span>
      </a>
      {!compact && <p className={styles.context}>{document.title} · {document.host}</p>}
      {document.locators.length > 0 && <p className={styles.locators}>
        {document.locators.join("; ")}
        {document.kind === "workbook" && <> <CopyButton text={document.locators.join("; ")} label="Copy sheet and cell locations" /></>}
      </p>}
      {document.workbook && !compact && <p className={styles.context}>Complete workbook · unchanged saved copy. Saves as <span>{document.workbook.filename}</span>.</p>}
    </div>);
  const allWorkbooks = documents.every(document => document.kind === "workbook");
  const allGovernment = documents.every(document => /\.(gov|mil)$/i.test(document.host));
  const groupLabel = `${documents.length} ${allGovernment ? "government " : "source "}${allWorkbooks ? "spreadsheets" : "documents"}`;
  // Keep the first PDF and first workbook immediately available even for multi-year totals.
  const visibleIndexes = new Set([0, documents.findIndex(document => document.kind === "workbook")]);
  const remainingRows = documentRows.filter((_, index) => !visibleIndexes.has(index));
  return <div className={`${styles.documents} ${compact ? styles.compact : ""} ${className}`} data-testid="source-documents">
    {canHighlight && <button type="button" className={styles.action} onClick={() => openPanel(factId)}>
      <ScanLine size={16} aria-hidden="true" />View highlighted line item
    </button>}
    {receipt && receipt.parts.length === 0 && pdfDocuments.length > 0 && <p className={styles.context}>Matching budget document. An exact printed amount has not been verified; the spreadsheet receipt remains available.</p>}
    {citation.kind === "derived" && <p className={styles.context}>Source documents for the calculation’s inputs</p>}
    {documents.length > 3 && hasPdf ? <>
      {documentRows.filter((_, index) => visibleIndexes.has(index))}
      <details className={styles.disclosure}><summary>View all {groupLabel}</summary><div className={styles.expandedDocuments}>{remainingRows}</div></details>
    </> : documents.length > 3 ? <details className={styles.disclosure}>
        <summary>View {groupLabel}</summary>
        <div className={styles.expandedDocuments}>{documentRows}</div>
      </details> : documentRows}
    {current?.incomplete && <p className={styles.context}>Some source locations could not be loaded here. Inspect the calculation’s input receipts for the remaining sources.</p>}
  </div>;
}
