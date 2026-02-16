'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { BookingJob } from '@/lib/types';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  claimed: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  running: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  success: 'bg-green-500/10 text-green-400 border-green-500/30',
  failed: 'bg-red-500/10 text-red-400 border-red-500/30',
};

interface Props {
  jobs: Pick<BookingJob, 'id' | 'status' | 'scheduled_for' | 'target_id'>[];
}

export function ActiveJobs({ jobs: initialJobs }: Props) {
  const [jobs, setJobs] = useState(initialJobs);

  useEffect(() => {
    const supabase = createClient();

    const channel = supabase
      .channel('booking-jobs')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'booking_jobs' },
        async () => {
          const { data } = await supabase
            .from('booking_jobs')
            .select('id, status, scheduled_for, target_id')
            .in('status', ['pending', 'claimed', 'running'])
            .order('scheduled_for', { ascending: true });
          if (data) setJobs(data);
        },
      )
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, []);

  if (jobs.length === 0) return null;

  return (
    <div className="space-y-2">
      {jobs.map((job) => (
        <Card key={job.id} className="border-zinc-800 bg-zinc-950">
          <CardContent className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-mono text-zinc-400">
                {new Date(job.scheduled_for).toLocaleDateString('en-US', {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                })}
              </p>
            </div>
            <Badge variant="outline" className={STATUS_COLORS[job.status] || ''}>
              {job.status}
            </Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
