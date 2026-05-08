'use client';

import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { QUERY_KEYS } from '@/lib/query-keys';
import type { WorkerHeartbeat } from '@/lib/types';

const OFFLINE_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes

export function WorkerOfflineBanner() {
  const { data: worker, dataUpdatedAt, isLoading } = useQuery<WorkerHeartbeat | null>({
    queryKey: QUERY_KEYS.workerStatus,
    queryFn: async () => {
      const res = await fetch('/api/worker-status');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json() as Promise<WorkerHeartbeat | null>;
    },
    refetchInterval: 30_000,
  });

  // Avoid flash on initial load — never renders on server so no SSR hydration mismatch
  if (isLoading) return null;

  const isOffline =
    !worker ||
    dataUpdatedAt - new Date(worker.last_heartbeat).getTime() > OFFLINE_THRESHOLD_MS;

  if (!isOffline) return null;

  return (
    <div className="flex items-center justify-center gap-2 border-b border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm text-red-400">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>
        Worker offline — automatic booking is paused.{' '}
        <span className="text-red-300">Start the worker daemon on your Mac Mini.</span>
      </span>
    </div>
  );
}
