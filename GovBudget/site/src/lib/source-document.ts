import type { Citation, CitationsMap } from "./data";
import { parseDerivedInputs } from "./citations";
import { documentTitleFromUrl } from "./footnote";

export interface SourceDocument {
  url: string;
  title: string;
  host: string;
  label: string;
  kind: "pdf" | "workbook" | "document";
  locators: string[];
}

/** Small serializable source closure for a single selected receipt. */
export function citationSourceSlice(factId: string, citations: CitationsMap): CitationsMap {
  const slice: CitationsMap = {};
  function visit(id: string) {
    if (slice[id] || !citations[id]) return;
    const citation = citations[id];
    slice[id] = citation;
    if (citation.kind === "derived") for (const input of parseDerivedInputs(citation.inputs)) {
      if (input.isFactId) visit(input.value);
    }
  }
  visit(factId);
  return slice;
}

/** Only a recorded PDF page creates a page target. Spreadsheet fragments are not portable. */
export function officialDocumentUrl(citation: Pick<Citation, "official_url" | "page_number">): string | null {
  if (!citation.official_url) return null;
  try {
    const url = new URL(citation.official_url);
    if (url.protocol !== "https:" && url.protocol !== "http:") return null;
    if (/\.pdf$/i.test(url.pathname) && Number.isInteger(citation.page_number) && citation.page_number! > 0) {
      const fragment = new URLSearchParams(url.hash.slice(1));
      fragment.set("page", String(citation.page_number));
      url.hash = fragment.toString();
    }
    return url.href;
  } catch { return null; }
}

/** Derived totals link to their inputs' documents; they never acquire a fictitious source row. */
export function citationSourceDocuments(citation: Citation, citations: CitationsMap | ((id: string) => Citation | undefined) = {}): SourceDocument[] {
  const lookup = typeof citations === "function" ? citations : (id: string) => citations[id];
  const documents = new Map<string, SourceDocument>();
  const visited = new Set<string>();
  function visit(row: Citation) {
    // The subaward card labels its prime-award context link explicitly.
    // It must not appear here as a direct source-document action.
    if (row.kind === "subaward") return;
    if (row.kind === "derived") {
      for (const input of parseDerivedInputs(row.inputs)) {
        if (!input.isFactId || visited.has(input.value)) continue;
        visited.add(input.value);
        const source = lookup(input.value);
        if (source) visit(source);
      }
      if (!row.official_url) return;
    }
    const url = officialDocumentUrl(row);
    if (!url) return;
    const parsed = new URL(url);
    const government = /\.(gov|mil)$/i.test(parsed.hostname);
    const kind = row.kind === "workbook" ? "workbook" : /\.pdf$/i.test(parsed.pathname) ? "pdf" : "document";
    const locator = kind === "workbook" ? [row.sheet, row.cells].filter(Boolean).join(" · ")
      : row.page_number != null ? `PDF page ${row.page_number}` : null;
    const existing = documents.get(url);
    if (existing) {
      if (locator && !existing.locators.includes(locator)) existing.locators.push(locator);
      return;
    }
    const format = kind === "workbook" ? "spreadsheet" : kind === "pdf" ? "PDF" : "document";
    documents.set(url, {
      url, host: parsed.hostname,
      title: documentTitleFromUrl(row.official_url, row.kind) ?? "Source document",
      kind, label: `Open ${government ? "government" : "source"} ${format}${kind === "pdf" && row.page_number ? ` · page ${row.page_number}` : ""}`,
      locators: locator ? [locator] : [],
    });
  }
  visit(citation);
  return [...documents.values()];
}
