"use client";

import { useEffect, useRef, useState } from "react";
import type { Citation } from "@/lib/data";
import { SourceDocumentLinks } from "./source-document-links";

/** Source metadata loads as this section approaches the viewport, not with the program header. */
export function ProgramSources({ entries, program }: { entries: { factId: string; citation: Citation }[]; program?: string }) {
  const root = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!root.current) return;
    if (typeof IntersectionObserver === "undefined") {
      const frame = requestAnimationFrame(() => setVisible(true));
      return () => cancelAnimationFrame(frame);
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setVisible(true); observer.disconnect(); }
    }, { rootMargin: "200px" });
    observer.observe(root.current);
    return () => observer.disconnect();
  }, []);
  const workbooks = entries.filter(entry => entry.citation.kind === "workbook");
  const details = entries.filter(entry => entry.citation.kind !== "workbook");
  return <section ref={root} aria-labelledby="primary-sources-heading" className="mt-8 pt-6 border-t border-border mb-8">
    <h2 id="primary-sources-heading" className="mb-3 text-foreground">Primary Sources</h2>
    {entries.length === 0 ? <p className="text-sm text-muted-foreground">No document-tier citations resolve on this page. Open a cited number for its calculation and input sources.</p> : <>
      <p className="mb-4 text-sm text-muted-foreground">Open any budget figure for its exact receipt. Verified line items lead with the highlighted government PDF; original spreadsheets download with their budget edition and exhibit in the filename.</p>
      {workbooks.length > 0 && <div data-testid="program-budget-sources">
        <h3 className="mb-3 text-sm font-semibold">Budget totals · TOA sources</h3>
        {workbooks.map(({ factId, citation }) => <SourceDocumentLinks key={factId} citation={citation} factId={factId} program={program} surface="program-sources" showBudgetPdf={visible} />)}
      </div>}
      {details.length > 0 && <div data-testid="program-detail-sources">
        <h3 className="mb-3 text-sm font-semibold">Detailed budget justification</h3>
        {workbooks.length > 0 && <p className="mb-4 text-sm text-muted-foreground">The related TOA spreadsheets above use a different accounting basis from R-2/P-40 detail. Their amounts are not assumed to match these detailed sources.</p>}
        {details.map(({ factId, citation }) => <SourceDocumentLinks key={factId} citation={citation} factId={factId} program={program} surface="program-sources" showBudgetPdf={visible} />)}
      </div>}
    </>}
  </section>;
}
