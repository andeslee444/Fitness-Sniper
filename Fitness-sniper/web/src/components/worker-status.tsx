'use client';

import { useEffect, useState } from 'react';
import type { WorkerHeartbeat } from '@/lib/types';

export function WorkerStatus() {
  const [worker, setWorker] = useState<WorkerHeartbeat | null>(null);

  useEffect(() => {
    async function fetchStatus() {
      const res = await fetch('/api/worker-status');
      if (res.ok) {
        const data = await res.json();
        setWorker(data);
      }
    }

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!worker) {
    return (
      <div className="flex items-center gap-2">
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-600" />
        <span className="text-lg font-bold text-zinc-500">Offline</span>
      </div>
    );
  }

  const isRecent = Date.now() - new Date(worker.last_heartbeat).getTime() < 60000;
  const isOnline = worker.status === 'online' && isRecent;

  return (
    <div className="flex items-center gap-2">
      <span className={`h-2.5 w-2.5 rounded-full ${isOnline ? 'animate-pulse bg-emerald-400' : 'bg-red-400'}`} />
      <span className={`text-lg font-bold ${isOnline ? 'text-emerald-400' : 'text-red-400'}`}>
        {isOnline ? 'Online' : 'Offline'}
      </span>
    </div>
  );
}
