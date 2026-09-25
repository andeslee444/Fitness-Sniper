import type { Citation, CitationsMap } from "./data";
import { parseDerivedInputs } from "./citations";
import { documentTitleFromUrl } from "./footnote";
import type { BudgetPdfReceipt } from "./budget-pdf-receipts";

export interface SourceDocument {
  url: string;
  title: string;
  host: string;
  label: string;
  kind: "pdf" | "workbook" | "document";
  locators: string[];
  workbook?: { sha256: string; filename: string };
}

/** One opening receipt per original budget document; all figure receipts remain addressable. */
export function programSourceEntries(citations: CitationsMap): { factId: string; citation: Citation }[] {
  const documents = new Map<string, { factId: string; citation: Citation }>();
  for (const [factId, citation] of Object.entries(citations)) {
    if (citation.kind !== "workbook" && citation.kind !== "jbook_pdf" && citation.kind !== "jbook_narrative") continue;
    const url = officialDocumentUrl(citation);
    if (!url) continue;
    const key = `${citation.kind === "workbook" ? "workbook" : "pdf"}:${url.split("#")[0]}`;
    const existing = documents.get(key);
    // Prefer a verified numeric receipt over a narrative/document-only locator.
    const verified = citation.kind === "jbook_pdf" && citation.resolution !== "unresolved";
    const existingVerified = existing?.citation.kind === "jbook_pdf" && existing.citation.resolution !== "unresolved";
    if (!existing || (verified && !existingVerified)) documents.set(key, { factId, citation });
  }
  return [...documents.values()];
}

/** Verified pages lead; a matching book alone does not establish a highlight. */
export function budgetPdfSourceDocuments(receipt: BudgetPdfReceipt): SourceDocument[] {
  const documents = new Map<string, SourceDocument>();
  const representedBooks = new Set<string>();
  for (const part of receipt.parts) {
    const url = officialDocumentUrl(part);
    if (!url) continue;
    const base = url.split("#")[0];
    representedBooks.add(base);
    const locator = `PDF page ${part.page_number}${part.line ? ` · Line ${part.line}` : ""}${part.row_label ? ` · ${part.row_label}` : ""} · ${part.pdf_column_label ?? part.column_label}`;
    const existing = documents.get(url);
    if (existing) { if (!existing.locators.includes(locator)) existing.locators.push(locator); continue; }
    documents.set(url, {
      url, host: new URL(url).hostname, kind: "pdf",
      title: `PB${part.edition} DoD ${part.exhibit}`,
      label: `Open government PDF · page ${part.page_number}`,
      locators: [locator],
    });
  }
  for (const book of receipt.source_documents ?? []) {
    const url = officialDocumentUrl({ official_url: book.official_url, page_number: null });
    if (!url || representedBooks.has(url.split("#")[0]) || documents.has(url)) continue;
    documents.set(url, {
      url, host: new URL(url).hostname, kind: "pdf", title: `PB${book.edition} DoD ${book.exhibit}`,
      label: "Open government PDF", locators: [],
    });
  }
  return [...documents.values()];
}

/** The download retains the original workbook identity, not a program alias. */
export function budgetPdfWorkbookDownloads(receipt: BudgetPdfReceipt): { sha256: string; filename: string }[] {
  const downloads = new Map<string, { sha256: string; filename: string }>();
  for (const part of receipt.parts) {
    if (!part.workbook_sha256 || !/^[a-f0-9]{64}$/i.test(part.workbook_sha256)) continue;
    downloads.set(part.workbook_sha256, {
      sha256: part.workbook_sha256,
      filename: workbookDownloadName(part.workbook_url ?? null, part.workbook_sha256),
    });
  }
  return [...downloads.values()];
}

/** Names describe the whole original workbook, not the clicked program/year. */
export function workbookDownloadName(officialUrl: string | null, sha256: string): string {
  let parsed: URL | undefined;
  try { if (officialUrl) parsed = new URL(officialUrl); } catch { /* use the saved-file identity below */ }
  const basename = parsed?.pathname.split("/").pop() ?? "";
  const edition = parsed?.pathname.match(/\/fy(\d{4})\//i)?.[1];
  const comptroller = parsed && /^comptroller\.(?:war|defense)\.gov$/i.test(parsed.hostname);
  const exhibits: Record<string, string> = {
    "p1_display.xlsx": "P-1_Procurement",
    "p1r_display.xlsx": "P-1R_Procurement",
    "r1_display.xlsx": "R-1_Research-Development-Test-Evaluation",
  };
  if (comptroller && edition && exhibits[basename.toLowerCase()]) {
    return `PB${edition}_DoD_${exhibits[basename.toLowerCase()]}.xlsx`;
  }
  // Unknown publishers never acquire a guessed DoD, service or budget edition.
  const sourceName = basename.replace(/\.xlsx$/i, "").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 90) || "Budget-spreadsheet";
  const identity = /^[a-f0-9]{64}$/i.test(sha256) ? sha256.slice(0, 8) : "saved-copy";
  return `${sourceName}_${identity}.xlsx`;
}

/** Enough for multi-year receipts while bounding standalone graph downloads. */
export const SOURCE_INPUT_LIMIT = 256;

/** Resolve input facts once, including nested totals; loaded facts never fetch. */
export async function resolveSourceCitationInputs(
  citation: Citation,
  lookup: (id: string) => Citation | undefined,
  fetchCitation: (id: string) => Promise<Citation | null>,
  cancelled: () => boolean = () => false,
): Promise<{ values: CitationsMap; incomplete: boolean }> {
  const values: CitationsMap = {};
  const visited = new Set<string>();
  const pending: Citation[] = [citation];
  let incomplete = false;
  while (pending.length && !cancelled()) {
    const row = pending.pop()!;
    if (row.kind !== "derived") continue;
    for (const input of parseDerivedInputs(row.inputs)) {
      if (!input.isFactId || visited.has(input.value)) continue;
      if (visited.size >= SOURCE_INPUT_LIMIT) { incomplete = true; continue; }
      visited.add(input.value);
      let source = lookup(input.value);
      if (!source) {
        try { source = await fetchCitation(input.value) ?? undefined; }
        catch { incomplete = true; }
      }
      if (cancelled()) return { values, incomplete };
      if (!source) { incomplete = true; continue; }
      values[input.value] = source;
      if (source.kind === "derived") pending.push(source);
    }
  }
  return { values, incomplete };
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
      kind, label: `${kind === "workbook" ? "Download" : "Open"} ${government ? "government" : "source"} ${format}${kind === "pdf" && row.page_number ? ` · page ${row.page_number}` : ""}`,
      locators: locator ? [locator] : [],
      ...(row.kind === "workbook" ? { workbook: { sha256: row.sha256, filename: workbookDownloadName(row.official_url, row.sha256) } } : {}),
    });
  }
  visit(citation);
  return [...documents.values()];
}
