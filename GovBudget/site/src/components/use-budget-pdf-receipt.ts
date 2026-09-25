"use client";

import { useEffect, useState } from "react";
import { fetchBudgetPdfReceipt, type BudgetPdfReceipt } from "@/lib/budget-pdf-receipts";

/** A changed fact never keeps the previous fact's evidence during loading. */
export function useBudgetPdfReceipt(factId: string | null | undefined): BudgetPdfReceipt | null {
  const [loaded, setLoaded] = useState<{ id: string; receipt: BudgetPdfReceipt | null } | null>(null);
  useEffect(() => {
    if (!factId) return;
    let cancelled = false;
    fetchBudgetPdfReceipt(factId).then(receipt => {
      if (!cancelled) setLoaded({ id: factId, receipt });
    });
    return () => { cancelled = true; };
  }, [factId]);
  return loaded && loaded.id === factId ? loaded.receipt : null;
}
