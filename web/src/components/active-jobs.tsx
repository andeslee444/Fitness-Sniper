'use client';

import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { QUERY_KEYS } from '@/lib/query-keys';
import type { BookingJob } from '@/lib/types';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  claimed: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  running: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  success: 'bg-green-500/10 text-green-400 border-green-500/30',
  failed: 'bg-red-500/10 text-red-400 border-red-500/30',
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'Queued',
  claimed: 'Claimed',
  running: 'Booking...',
  success: 'Booked',
  failed: 'Failed',
};

export function ActiveJobs() {
  const { data: jobs = [] } = useQuery<Pick<BookingJob, 'id' | 'status' | 'scheduled_for' | 'class_datetime' | 'target_id'>[]>({
    queryKey: QUERY_KEYS.jobs,
    queryFn: async () => {
      const res = await fetch('/api/jobs');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    refetchInterval: 15_000,
  });

  if (jobs.length === 0) return null;

  return (
    <div className="space-y-2">
      {jobs.map((job) => (
        <div key={job.id} className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
          <div className="flex items-center gap-3">
            <div className={`h-2 w-2 rounded-full ${
              job.status === 'running' ? 'animate-pulse bg-purple-400' :
              job.status === 'claimed' ? 'bg-blue-400' :
              'bg-yellow-400'
            }`} />
            <div>
              <p className="text-sm font-medium text-white">
                {new Date(job.class_datetime || job.scheduled_for).toLocaleDateString('en-US', {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                })}{' '}
                <span className="text-zinc-400">
                  @ {new Date(job.class_datetime || job.scheduled_for).toLocaleTimeString('en-US', {
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </span>
              </p>
            </div>
          </div>
          <Badge variant="outline" className={STATUS_COLORS[job.status] || ''}>
            {STATUS_LABELS[job.status] || job.status}
          </Badge>
        </div>
      ))}
    </div>
  );
}
