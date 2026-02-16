'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { Badge } from '@/components/ui/badge';
import type { WorkerHeartbeat } from '@/lib/types';

export function WorkerStatus() {
  const [worker, setWorker] = useState<WorkerHeartbeat | null>(null);

  useEffect(() => {
    const supabase = createClient();

    async function fetch() {
      const { data } = await supabase
        .from('worker_heartbeats')
        .select('*')
        .order('last_heartbeat', { ascending: false })
        .limit(1)
        .single();
      setWorker(data);
    }

    fetch();

    // Subscribe to changes
    const channel = supabase
      .channel('worker-heartbeats')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'worker_heartbeats' }, () => {
        fetch();
      })
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, []);

  if (!worker) {
    return <Badge variant="outline" className="border-zinc-600 text-zinc-500">No worker</Badge>;
  }

  const isRecent = Date.now() - new Date(worker.last_heartbeat).getTime() < 60000;
  const isOnline = worker.status === 'online' && isRecent;

  return (
    <div className="flex items-center gap-2">
      <span className={`h-2 w-2 rounded-full ${isOnline ? 'bg-green-400' : 'bg-red-400'}`} />
      <span className="text-sm font-medium text-white">
        {isOnline ? 'Online' : 'Offline'}
      </span>
    </div>
  );
}
