import React from "react";
import { createHash, webcrypto } from "node:crypto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { downloadWorkbook } from "@/lib/workbook-download";
import { WorkbookDownload } from "@/components/workbook-download";
import { AssetConfigProvider } from "@/components/asset-config";

const bytes = new TextEncoder().encode("unchanged official workbook bytes");
const sha256 = createHash("sha256").update(bytes).digest("hex");
const filename = "PB2026_DoD_P-1_Procurement.xlsx";
const createObjectURL = vi.fn(() => "blob:verified-workbook");
const revokeObjectURL = vi.fn();
const clicks: { href: string; filename: string }[] = [];

beforeEach(() => {
  clicks.length = 0;
  vi.stubGlobal("crypto", webcrypto);
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, arrayBuffer: async () => bytes.buffer })));
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    clicks.push({ href: this.href, filename: this.download });
  });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); vi.clearAllMocks(); vi.useRealTimers(); });

describe("named government workbook downloads", () => {
  it("checks source bytes and saves a Blob using the descriptive filename", async () => {
    vi.useFakeTimers();
    await downloadWorkbook("https://assets.fiscalreceipts.com/workbooks/source.xlsx", filename, sha256);
    expect(fetch).toHaveBeenCalledWith("https://assets.fiscalreceipts.com/workbooks/source.xlsx");
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(clicks).toEqual([{ href: "blob:verified-workbook", filename }]);
    expect(document.querySelector('a[download]')).toBeNull();
    expect(revokeObjectURL).not.toHaveBeenCalled();
    vi.advanceTimersByTime(60_000);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:verified-workbook");
  });

  it("does not save bytes that differ from the cited source", async () => {
    await expect(downloadWorkbook("/file.xlsx", filename, "0".repeat(64))).rejects.toThrow("did not match");
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(clicks).toEqual([]);
  });

  it("rejects missing source identities and failed asset requests", async () => {
    await expect(downloadWorkbook("/file.xlsx", filename, "missing")).rejects.toThrow("identity");
    expect(fetch).not.toHaveBeenCalled();
    vi.mocked(fetch).mockResolvedValueOnce({ ok: false, status: 404 } as Response);
    await expect(downloadWorkbook("/file.xlsx", filename, sha256)).rejects.toThrow("404");
    expect(clicks).toEqual([]);
  });

  it("runs from a download button and reports its filename only after success", async () => {
    const onDownload = vi.fn();
    render(<AssetConfigProvider initialBase="https://assets.fiscalreceipts.com"><WorkbookDownload sha256={sha256} filename={filename} label="Download government spreadsheet" onDownload={onDownload} /></AssetConfigProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Download government spreadsheet" }));
    expect(screen.getByRole("button", { name: "Preparing spreadsheet…" })).toBeDisabled();
    await waitFor(() => expect(onDownload).toHaveBeenCalledOnce());
    expect(fetch).toHaveBeenCalledWith(`https://assets.fiscalreceipts.com/workbooks/${sha256}.xlsx`);
    expect(screen.getByRole("status")).toHaveTextContent(`Download started: ${filename}`);
    expect(clicks).toEqual([{ href: "blob:verified-workbook", filename }]);
  });

  it("reports failures with retry and original-source guidance", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("offline"));
    const onDownload = vi.fn();
    render(<WorkbookDownload sha256={sha256} filename={filename} label="Download government spreadsheet" onDownload={onDownload} />);
    fireEvent.click(screen.getByRole("button"));
    expect(await screen.findByText(/Download unavailable/)).toBeVisible();
    expect(screen.getByRole("button")).toBeEnabled();
    expect(onDownload).not.toHaveBeenCalled();
    expect(clicks).toEqual([]);
  });
});
