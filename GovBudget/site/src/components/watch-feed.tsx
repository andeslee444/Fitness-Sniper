"use client";

import { useState } from "react";
import { trackReaderEvent } from "@/lib/reader-events";

import { WATCH_COPY } from "@/lib/copy";

/** URLs come only from the server's existing feed eligibility resolver. */
export function WatchFeed({ urls, label, scope = "feed", program, compact = false }: {
  urls: { rss: string; atom: string } | null;
  label: string;
  scope?: "program" | "company" | "feed";
  program?: string;
  compact?: boolean;
}) {
  const [status, setStatus] = useState("");
  const [fallback, setFallback] = useState(false);
  if (!urls) return <p className="my-3 text-sm text-muted-foreground" data-watch-unavailable="">{WATCH_COPY.unavailable}</p>;
  const metadata = { surface: `watch_${scope}`, program };
  async function copyFeed() {
    try {
      await navigator.clipboard.writeText(urls!.rss);
      setStatus("Feed address copied."); setFallback(false);
      trackReaderEvent("watch_feed_copied", { ...metadata, format: "rss" });
    } catch {
      setStatus("Copy the feed address below."); setFallback(true);
    }
  }
  return <details data-feed-subscribe="" className={compact ? "my-2 text-sm" : "my-4 rounded-md border border-border p-4 text-sm"}>
    <summary className="cursor-pointer font-medium">{label}</summary>
    <div className="mt-3 space-y-2 text-muted-foreground">
      <p>{WATCH_COPY[scope]}</p><p>{WATCH_COPY.timing}</p><p>{WATCH_COPY.instruction}</p>
      <div className="flex flex-wrap items-center gap-4 text-foreground">
        <a href={urls.rss} className="underline" title={`${label} — RSS`} onClick={() => trackReaderEvent("watch_feed_selected", { ...metadata, format: "rss" })}>RSS</a>
        <a href={urls.atom} className="underline" title={`${label} — Atom`} onClick={() => trackReaderEvent("watch_feed_selected", { ...metadata, format: "atom" })}>Atom</a>
        <button type="button" className="rounded border border-border px-3 py-2" onClick={copyFeed}>Copy feed address</button>
      </div>
      <p role="status">{status}</p>
      {fallback && <label className="block">RSS address<input className="mt-1 block w-full rounded border border-border p-2" readOnly value={urls.rss} onFocus={event => event.currentTarget.select()} /></label>}
    </div>
  </details>;
}
