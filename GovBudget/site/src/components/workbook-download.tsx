"use client";

import { Download } from "lucide-react";
import { useRef, useState } from "react";
import { downloadWorkbook } from "@/lib/workbook-download";
import { useAssetUrl } from "./asset-config";

export function WorkbookDownload({ sha256, filename, label, className, onDownload }: {
  sha256: string;
  filename: string;
  label: string;
  className?: string;
  onDownload?: () => void;
}) {
  const assetUrl = useAssetUrl();
  const pending = useRef(false);
  const [status, setStatus] = useState<"idle" | "loading" | "saved" | "error">("idle");
  async function save() {
    if (pending.current) return;
    pending.current = true;
    setStatus("loading");
    try {
      await downloadWorkbook(assetUrl(`/workbooks/${sha256}.xlsx`), filename, sha256);
      setStatus("saved");
      onDownload?.();
    } catch { setStatus("error"); }
    finally { pending.current = false; }
  }
  return <>
    <button type="button" className={className} data-testid="workbook-download" data-filename={filename}
      disabled={status === "loading"} onClick={save}>
      <Download size={16} aria-hidden="true" />
      <span>{status === "loading" ? "Preparing spreadsheet…" : label}</span>
    </button>
    <span role="status" className={status === "error" ? "block mt-1 text-xs text-muted-foreground" : "sr-only"}>
      {status === "error" ? "Download unavailable. Try again, or use the government original." : status === "saved" ? `Download started: ${filename}` : ""}
    </span>
  </>;
}
