'use client';

import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Trash2, Calendar, MapPin, Clock, Armchair, CheckCircle, XCircle, Loader2, Timer } from 'lucide-react';
import { STUDIOS, STUDIO_LOCATIONS, DAY_ABBR, SEAT_PREFERENCES } from '@/lib/studios';
import type { TargetWithJob, JobStatus } from '@/lib/types';

function formatTargetDate(dateVal: string | Date): string {
  const date = typeof dateVal === 'string'
    ? new Date(dateVal + 'T00:00:00')
    : new Date(dateVal);
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

const JOB_STATUS_CONFIG: Record<string, { label: string; style: string; icon: React.ComponentType<{ className?: string }> }> = {
  pending: { label: 'Queued', style: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30', icon: Timer },
  claimed: { label: 'Claimed', style: 'bg-blue-500/10 text-blue-400 border-blue-500/30', icon: Loader2 },
  running: { label: 'Booking...', style: 'bg-purple-500/10 text-purple-400 border-purple-500/30', icon: Loader2 },
  success: { label: 'Booked', style: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30', icon: CheckCircle },
  failed: { label: 'Failed', style: 'bg-red-500/10 text-red-400 border-red-500/30', icon: XCircle },
};

export function TargetsList({ targets }: { targets: TargetWithJob[] }) {
  const router = useRouter();

  async function toggleTarget(id: string, enabled: boolean) {
    try {
      const res = await fetch(`/api/targets/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (!res.ok) throw new Error('Failed to update target');
      router.refresh();
    } catch {
      toast.error('Failed to update target');
    }
  }

  async function deleteTarget(id: string, name: string) {
    if (!confirm(`Delete this ${name} target? This cannot be undone.`)) return;
    try {
      const res = await fetch(`/api/targets/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete target');
      toast.success('Target deleted');
      router.refresh();
    } catch {
      toast.error('Failed to delete target');
    }
  }

  if (targets.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center">
        <p className="text-zinc-500">No targets yet. Add one to start auto-booking.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {targets.map((target) => {
        const studio = STUDIOS[target.studio_slug];
        const location = STUDIO_LOCATIONS[target.studio_slug]?.find(
          (l) => l.id === target.location_id,
        );
        const seatLabel = SEAT_PREFERENCES.find((s) => s.value === target.seat_preference)?.label;

        const scheduleLabel =
          target.target_type === 'one_time' && target.target_date
            ? formatTargetDate(target.target_date)
            : DAY_ABBR[target.day_of_week ?? 0];

        const jobConfig = target.job_status ? JOB_STATUS_CONFIG[target.job_status] : null;
        const JobIcon = jobConfig?.icon;

        return (
          <div
            key={target.id}
            className={`rounded-xl border bg-white/[0.02] p-4 transition-colors ${
              target.enabled ? 'border-white/5' : 'border-white/5 opacity-50'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <Switch
                  checked={target.enabled}
                  onCheckedChange={(checked) => toggleTarget(target.id, checked)}
                  className="mt-0.5"
                />
                <div className="min-w-0 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-white">{studio?.name || target.studio_slug}</span>
                    {target.target_type === 'one_time' && (
                      <Badge variant="outline" className="border-blue-500/30 text-xs text-blue-400">
                        One-time
                      </Badge>
                    )}
                    {jobConfig && (
                      <Badge variant="outline" className={`text-xs ${jobConfig.style}`}>
                        {JobIcon && <JobIcon className={`mr-1 h-3 w-3 ${target.job_status === 'running' || target.job_status === 'claimed' ? 'animate-spin' : ''}`} />}
                        {jobConfig.label}
                        {target.job_status === 'success' && target.job_spot && ` · Spot ${target.job_spot}`}
                      </Badge>
                    )}
                    {!target.job_status && target.enabled && (
                      <Badge variant="outline" className="border-zinc-700 text-xs text-zinc-500">
                        Waiting
                      </Badge>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-400">
                    {(location?.name || target.location_id) && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {location?.name || target.location_id}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {scheduleLabel}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {target.time || 'Any time'}
                    </span>
                    {seatLabel && seatLabel !== 'Any Available' && (
                      <span className="flex items-center gap-1">
                        <Armchair className="h-3 w-3" />
                        {seatLabel}
                      </span>
                    )}
                  </div>
                  {target.job_status === 'failed' && target.job_message && (
                    <p className="text-xs text-red-400/70">{target.job_message}</p>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => deleteTarget(target.id, studio?.name || target.studio_slug)}
                className="h-8 w-8 shrink-0 p-0 text-zinc-500 hover:text-red-400"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
