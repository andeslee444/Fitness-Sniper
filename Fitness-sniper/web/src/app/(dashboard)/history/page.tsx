'use client';

import { useState, useEffect, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { HistorySkeleton } from '@/components/skeleton';
import { STUDIOS } from '@/lib/studios';
import { CheckCircle, XCircle, MinusCircle } from 'lucide-react';

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
}

const PAGE_SIZE = 20;

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const fetchHistory = useCallback(async (offset: number, append: boolean) => {
    const setter = append ? setLoadingMore : setLoading;
    setter(true);
    try {
      const res = await fetch(`/api/history?limit=${PAGE_SIZE}&offset=${offset}`);
      if (!res.ok) return;
      const data = await res.json();
      setHistory((prev) => (append ? [...prev, ...data.rows] : data.rows));
      setTotal(data.total);
    } finally {
      setter(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory(0, false);
  }, [fetchHistory]);

  const hasMore = history.length < total;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">Booking History</h1>
        {!loading && total > 0 && (
          <p className="mt-1 text-sm text-zinc-400">{total} booking{total !== 1 ? 's' : ''} total</p>
        )}
      </div>

      {loading ? (
        <HistorySkeleton />
      ) : history.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center">
          <p className="text-zinc-500">No bookings yet. Once the worker books a class, it will appear here.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {history.map((entry) => {
            const studio = STUDIOS[entry.studio_slug];
            const config = STATUS_CONFIG[entry.status] || STATUS_CONFIG.cancelled;
            const StatusIcon = config.icon;
            return (
              <div key={entry.id} className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
                <div className="flex items-center gap-3">
                  <StatusIcon className={`h-4 w-4 shrink-0 ${
                    entry.status === 'booked' ? 'text-emerald-400' :
                    entry.status === 'failed' ? 'text-red-400' : 'text-zinc-500'
                  }`} />
                  <div className="min-w-0">
                    <p className="font-medium text-white">
                      {studio?.name || entry.studio_slug}{' '}
                      <span className="text-zinc-500">{entry.location_id}</span>
                    </p>
                    <p className="text-sm text-zinc-400">
                      {new Date(entry.class_date).toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                      })}{' '}
                      @ {entry.class_time}
                      {entry.spot && <span className="ml-2 text-emerald-400">· Spot {entry.spot}</span>}
                    </p>
                    {entry.message && (
                      <p className="mt-0.5 text-xs text-zinc-600">{entry.message}</p>
                    )}
                  </div>
                </div>
                <Badge variant="outline" className={config.style}>
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
