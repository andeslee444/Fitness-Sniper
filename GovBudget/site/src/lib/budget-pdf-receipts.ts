import type { PdfPageCitation } from "./citations";

export interface BudgetPdfPart extends PdfPageCitation {
  amount_thousands: number;
  program: string;
  line: string;
  row_label?: string;
  workbook_cell: string;
  column_label: string;
  pdf_column_label?: string;
  edition: number;
  exhibit: string;
  sha256: string;
}
export interface BudgetPdfReceipt {
  amount_thousands: number;
  matched_amount_thousands: number;
  complete: boolean;
  blank_zero_count: number;
  unmatched_count: number;
  parts: BudgetPdfPart[];
}
const cache = new Map<string, Promise<Record<string, BudgetPdfReceipt> | null>>();
export async function fetchBudgetPdfReceipt(factId: string): Promise<BudgetPdfReceipt | null> {
  if (!/^[a-f0-9]{16}$/.test(factId)) return null;
  const prefix = factId.slice(0, 2);
  let pending = cache.get(prefix);
  if (!pending) {
    pending = fetch(`/json/budget-pdf-receipts/${prefix}.json`)
      .then(r => { if (!r.ok) throw new Error("PDF evidence unavailable"); return r.json(); })
      .catch(() => { cache.delete(prefix); return null; });
    cache.set(prefix, pending);
  }
  return (await pending)?.[factId] ?? null;
}
