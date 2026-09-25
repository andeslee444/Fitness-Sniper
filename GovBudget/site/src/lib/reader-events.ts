import { track } from "@vercel/analytics";

export type ReaderEvent =
  | "brief_selected" | "funding_selected" | "receipt_opened"
  | "official_source_opened" | "citation_copied" | "answer_copied"
  | "view_shared" | "receipt_saved" | "receipts_exported"
  | "watch_feed_selected" | "watch_feed_copied";

export interface ReaderEventMetadata {
  program?: string;
  factId?: string;
  fiscalYear?: number;
  measure?: string;
  surface?: string;
  selection?: string;
  format?: string;
  count?: number;
}

const FIELDS = ["program", "factId", "fiscalYear", "measure", "surface", "selection", "format", "count"] as const;

/** Controlled identifiers only: never URLs, search text, notes or copied content. */
export function trackReaderEvent(name: ReaderEvent, metadata: ReaderEventMetadata = {}): void {
  const properties: Record<string, string | number> = {};
  for (const key of FIELDS) {
    const value = metadata[key];
    if (typeof value === "number" && Number.isFinite(value)) properties[key] = value;
    else if (typeof value === "string" && /^[a-zA-Z0-9_/-]{1,100}$/.test(value)) properties[key] = value;
  }
  try { track(name, properties); }
  catch { /* Measurement must never prevent a reader action. */ }
}
