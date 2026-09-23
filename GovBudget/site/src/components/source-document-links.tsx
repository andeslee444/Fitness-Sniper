"use client";

import { ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";
import type { Citation, CitationsMap } from "@/lib/data";
import { citationSourceDocuments } from "@/lib/source-document";
import { trackReaderEvent } from "@/lib/reader-events";
import { parseDerivedInputs } from "@/lib/citations";
import { resolveCitationFromShards } from "@/lib/cite-shards";
import { CopyButton } from "./copy-button";
import styles from "./source-document-links.module.css";

const EMPTY_CITATIONS: CitationsMap = {};

export function SourceDocumentLinks({ citation, citations = EMPTY_CITATIONS, className = "", factId, program, surface = "source-document", compact = false, resolveInputs = false }: {
  citation: Citation;
  citations?: CitationsMap | ((id: string) => Citation | undefined);
  className?: string;
  factId?: string;
  program?: string;
  surface?: string;
  compact?: boolean;
  /** Standalone receipts may have only the total's citation embedded. */
  resolveInputs?: boolean;
}) {
  const [resolved, setResolved] = useState<{ root: Citation; values: CitationsMap; incomplete: boolean } | null>(null);
  useEffect(() => {
    if (!resolveInputs || citation.kind !== "derived") return;
    let cancelled = false;
    const lookup = typeof citations === "function" ? citations : (id: string) => citations[id];
    const values: CitationsMap = {};
    const visited = new Set<string>();
    let incomplete = false;
    async function visit(row: Citation): Promise<void> {
      if (row.kind !== "derived") return;
      for (const input of parseDerivedInputs(row.inputs)) {
        if (!input.isFactId || visited.has(input.value)) continue;
        // A source action must not download an unbounded graph for a large rollup.
        if (visited.size >= 32) { incomplete = true; continue; }
        visited.add(input.value);
        const source = lookup(input.value) ?? await resolveCitationFromShards(input.value);
        if (cancelled) return;
        if (!source) { incomplete = true; continue; }
        values[input.value] = source;
        await visit(source);
      }
    }
    visit(citation).then(() => { if (!cancelled) setResolved({ root: citation, values, incomplete }); });
    return () => { cancelled = true; };
  }, [citation, citations, resolveInputs]);
  const current = resolved?.root === citation ? resolved : null;
  const documents = citationSourceDocuments(citation, id => (typeof citations === "function" ? citations(id) : citations[id]) ?? current?.values[id]);
  if (!documents.length && !current?.incomplete) return null;
  return <div className={`${styles.documents} ${compact ? styles.compact : ""} ${className}`} data-testid="source-documents">
    {citation.kind === "derived" && <p className={styles.context}>Source documents for the calculation’s inputs</p>}
    {documents.map(document => <div key={document.url} className={styles.document}>
      <a href={document.url} target="_blank" rel="noopener noreferrer" data-testid="official-source" className={styles.action}
        onClick={() => trackReaderEvent("official_source_opened", { program, factId, surface })}>
        <ExternalLink size={16} aria-hidden="true" />
        <span>{document.label}</span><span className="sr-only"> (opens in new tab)</span>
      </a>
      {!compact && <p className={styles.context}>{document.title} · {document.host}</p>}
      {document.locators.length > 0 && <p className={styles.locators}>
        {document.locators.join("; ")}
        {document.kind === "workbook" && <> <CopyButton text={document.locators.join("; ")} label="Copy sheet and cell locations" /></>}
      </p>}
      {document.kind === "workbook" && !compact && <p className={styles.context}>Open the file, then use the sheet and cell locations above. The link opens the whole spreadsheet.</p>}
    </div>)}
    {current?.incomplete && <p className={styles.context}>Some source locations could not be loaded here. Inspect the calculation’s input receipts for the remaining sources.</p>}
  </div>;
}
