import { afterEach, describe, expect, it, vi } from "vitest";
afterEach(() => { vi.unstubAllGlobals(); vi.resetModules(); });
describe("PDF receipt shard loading", () => {
  it("loads versioned three-character shards and shares a request for facts in the same shard", async () => {
    const receipt = { parts: [], complete: false };
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ a123456789abcdef: receipt, a12fedcba9876543: receipt }) });
    vi.stubGlobal("fetch", fetch);
    const { fetchBudgetPdfReceipt } = await import("@/lib/budget-pdf-receipts");
    const results = await Promise.all([fetchBudgetPdfReceipt("a123456789abcdef"), fetchBudgetPdfReceipt("a12fedcba9876543")]);
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledWith("/json/budget-pdf-receipts/v2/a12.json");
    expect(results).toEqual([receipt, receipt]);
  });
  it("retries unavailable shards and rejects a payload without receipt parts", async () => {
    const fetch = vi.fn().mockResolvedValueOnce({ ok: false }).mockResolvedValueOnce({ ok: true, json: async () => ({ a123456789abcdef: { kind: "workbook" } }) });
    vi.stubGlobal("fetch", fetch);
    const { fetchBudgetPdfReceipt } = await import("@/lib/budget-pdf-receipts");
    expect(await fetchBudgetPdfReceipt("a123456789abcdef")).toBeNull();
    expect(await fetchBudgetPdfReceipt("a123456789abcdef")).toBeNull();
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(await fetchBudgetPdfReceipt("invalid")).toBeNull();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
