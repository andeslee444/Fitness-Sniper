'use client';

import { useState, useEffect, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { HistorySkeleton } from '@/components/skeleton';
import { STUDIOS } from '@/lib/studios';
import { AlertCircle, CheckCircle, XCircle, MinusCircle } from 'lucide-react';
import { translateJobMessage } from '@/components/job-status-timeline';

const STATUS_CONFIG: Record<string, { style: string; icon: React.ComponentType<{ className?: string }> }> = {
  booked: { style: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30', icon: CheckCircle },
  failed: { style: 'bg-red-500/10 text-red-400 border-red-500/30', icon: XCircle },
  cancelled: { style: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/30', icon: MinusCircle },
};

interface HistoryEntry {
  id: string;
  studio_slug: string;
  location_id: string;
  class_date: string;
  class_time: string;
  status: string;
  spot: string | null;
  message: string | null;
  class_name: string | null;
}

const PAGE_SIZE = 20;

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [studioFilter, setStudioFilter] = useState<string>('all');

  const fetchHistory = useCallback(async (offset: number, append: boolean) => {
    const setter = append ? setLoadingMore : setLoading;
    setter(true);
    try {
      const url = `/api/history?limit=${PAGE_SIZE}&offset=${offset}${studioFilter !== 'all' ? `&studio=${studioFilter}` : ''}`;
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      setHistory((prev) => (append ? [...prev, ...data.rows] : data.rows));
      setTotal(data.total);
    } finally {
      setter(false);
    }
  }, [studioFilter]);

  // Initial load
  useEffect(() => {
    fetchHistory(0, false);
  }, [fetchHistory]);

  // Reset pagination when studio filter changes
  useEffect(() => {
    fetchHistory(0, false);
    // fetchHistory is in the dep array, which already includes studioFilter
    // This effect fires on mount (covered above) and whenever studioFilter changes
  }, [studioFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const hasMore = history.length < total;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">Booking History</h1>
          {!loading && total > 0 && (
            <p className="mt-1 text-sm text-zinc-400">{total} booking{total !== 1 ? 's' : ''} total</p>
          )}
        </div>

        {/* Studio filter */}
        <Select value={studioFilter} onValueChange={setStudioFilter}>
          <SelectTrigger className="w-44 border-white/10 bg-white/[0.02] text-sm text-zinc-300 focus:ring-0">
            <SelectValue placeholder="All Studios" />
          </SelectTrigger>
          <SelectContent className="border-white/10 bg-zinc-900 text-zinc-300">
            <SelectItem value="all">All Studios</SelectItem>
            {Object.entries(STUDIOS).map(([slug, config]) => (
              <SelectItem key={slug} value={slug}>
                {config.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <HistorySkeleton />
      ) : history.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center">
          <p className="text-zinc-500">
            {studioFilter !== 'all'
              ? `No bookings found for ${STUDIOS[studioFilter]?.name ?? studioFilter}.`
              : 'No bookings yet. Once the worker books a class, it will appear here.'}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {history.map((entry) => {
            const studio = STUDIOS[entry.studio_slug];
            const config = STATUS_CONFIG[entry.status] || STATUS_CONFIG.cancelled;
            const StatusIcon = config.icon;

            // Use T00:00:00 suffix to prevent UTC shift for YYYY-MM-DD strings
            const formattedDate = new Date(entry.class_date + 'T00:00:00').toLocaleDateString('en-US', {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
            });

            return (
              <div key={entry.id} className="flex items-start justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
                <div className="flex items-start gap-3">
                  <StatusIcon className={`mt-0.5 h-4 w-4 shrink-0 ${
                    entry.status === 'booked' ? 'text-emerald-400' :
                    entry.status === 'failed' ? 'text-red-400' : 'text-zinc-500'
                  }`} />
                  <div className="min-w-0">
                    {/* Primary line: class name (or studio name as fallback) */}
                    <p className="font-medium text-white">
                      {entry.class_name || studio?.name || entry.studio_slug}
                    </p>
                    {/* Secondary line: studio + date/time */}
                    <p className="text-sm text-zinc-400">
                      {studio?.name || entry.studio_slug}
                      {' · '}
                      {formattedDate} @ {entry.class_time}
                      {entry.spot && <span className="ml-2 text-emerald-400">· Spot {entry.spot}</span>}
                    </p>
                    {/* Prominent failure message */}
                    {entry.status === 'failed' && entry.message && (
                      <p className="mt-1 flex items-center gap-1 text-sm text-red-400">
                        <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                        {translateJobMessage(entry.message)}
                      </p>
                    )}
                    {/* Non-failed message (spot confirmation etc.) */}
                    {entry.status !== 'failed' && entry.message && (
                      <p className="mt-0.5 text-xs text-zinc-500">{entry.message}</p>
                    )}
                  </div>
                </div>
                <Badge variant="outline" className={`shrink-0 ${config.style}`}>
                  {entry.status}
                </Badge>
              </div>
            );
          })}

          {hasMore && (
            <div className="pt-4 text-center">
              <Button
                variant="outline"
                onClick={() => fetchHistory(history.length, true)}
                disabled={loadingMore}
                className="border-white/10 text-zinc-400 hover:text-white"
              >
                {loadingMore ? 'Loading...' : `Load More (${history.length} of ${total})`}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
