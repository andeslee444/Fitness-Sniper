"use client";
import { ArrowUpRight } from "lucide-react";
import {
  EVIDENCE_LABELS,
  type KnowledgeSource,
} from "@/lib/f15-knowledge-types";
import styles from "./f15-knowledge-browser.module.css";

export function KnowledgeSources({
  ids,
  sources,
  compact = false,
}: {
  ids: string[];
  sources: KnowledgeSource[];
  compact?: boolean;
}) {
  const selected = ids.flatMap((id) =>
    sources.filter((source) => source.id === id),
  );
  if (!selected.length) return null;
  return (
    <details className={`${styles.sources} ${compact ? styles.compact : ""}`}>
      <summary>
        Sources & dates <span>{selected.length}</span>
      </summary>
      {selected.map((source) => (
        <div key={source.id} className={styles.source}>
          <span className={styles.evidence} data-evidence={source.evidence}>
            {EVIDENCE_LABELS[source.evidence]}
          </span>
          <a href={source.url} target="_blank" rel="noreferrer">
            {source.title}
            <ArrowUpRight size={12} />
          </a>
          <small>
            {source.publisher} ·{" "}
            {source.published
              ? `Published ${source.published}`
              : "Publication date not stated"}{" "}
            · Accessed {source.accessed}
          </small>
        </div>
      ))}
    </details>
  );
}
