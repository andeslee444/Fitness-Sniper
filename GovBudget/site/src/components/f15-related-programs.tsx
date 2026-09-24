"use client";

import { useContext, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, FileText } from "lucide-react";
import { CitationPanelContext } from "@/components/cite";
import type { F15RelatedProgram } from "@/lib/f15-related-programs";
import styles from "./family-funding-history.module.css";

/** Shared-program evidence is contextual; it never contributes to annual sums. */
export function F15RelatedPrograms({ programs }: { programs: F15RelatedProgram[] }) {
  const [expanded, setExpanded] = useState(false);
  const { openPanel } = useContext(CitationPanelContext);
  const publishedCount = programs.filter(program => program.factId).length;
  return <section className={styles.related} aria-labelledby="f15-shared-heading" data-family-shared-programs="">
    <div className={styles.tableHeading}>
      <h3 id="f15-shared-heading">Shared programs with F-15 work</h3>
      <p>{publishedCount} cited programs · {programs.length - publishedCount} historical records</p>
    </div>
    <p className={styles.caption} id="f15-shared-description">These programs also support other aircraft. Their budgets are excluded from the family totals because no F-15 share is established. Source editions date the evidence; they do not establish funding in every year.</p>
    <button type="button" className={styles.retry} aria-expanded={expanded} aria-controls="f15-shared-sources" onClick={() => setExpanded(value => !value)}>
      {expanded ? "Hide shared-program sources" : "View all shared-program sources"}
    </button>
    <div id="f15-shared-sources">
      {expanded && <div className={styles.tableScroll} role="region" aria-label="Shared program evidence table" tabIndex={0}>
        <table className={`${styles.table} ${styles.sharedTable}`} aria-labelledby="f15-shared-heading" aria-describedby="f15-shared-description">
          <thead><tr><th scope="col">Source edition</th><th scope="col">Program / budget line</th><th scope="col">Documented F-15 work</th><th scope="col">Government source</th></tr></thead>
          <tbody>{programs.map(program => <tr key={`${program.sourceEdition}-${program.identifier}`} data-shared-program={program.identifier} data-source-edition={program.sourceEdition}>
            <td><strong>PB{program.sourceEdition}</strong><span className={styles.rowMeta}>{program.factId ? "Published receipt" : "Historical evidence"}</span></td>
            <th scope="row" className={styles.program}>{program.slug ? <Link href={`/program/${program.slug}/`}>{program.title}</Link> : program.title}<span className={styles.rowMeta}>{program.identifier}</span></th>
            <td className={styles.association}><p>{program.association}</p><blockquote data-source-text="narrative">“{program.excerpt}”</blockquote></td>
            <td className={styles.source}>
              <a href={program.officialUrl} target="_blank" rel="noopener noreferrer" aria-label={`Open government PDF for ${program.title}, PB${program.sourceEdition}`}><FileText size={15} aria-hidden="true" /> Government PDF <ArrowUpRight size={13} aria-hidden="true" /></a>
              <span className={styles.rowMeta}>{program.pageNumber ? `PDF page ${program.pageNumber}` : "PDF page not mapped"} · {program.locator}</span>
              {program.factId ? <button type="button" className={styles.receiptLink} data-source-fact={program.factId} aria-label={`Open source receipt for ${program.title}, PB${program.sourceEdition}`} onClick={() => openPanel(program.factId!)}>Source receipt ↗</button> : <span className={styles.rowMeta}>Source PDF available; receipt not yet published.</span>}
            </td>
          </tr>)}</tbody>
        </table>
      </div>}
    </div>
  </section>;
}
