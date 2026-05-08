'use client';

import { useQuery } from '@tanstack/react-query';
import { STUDIOS } from '@/lib/studios';
import { QUERY_KEYS } from '@/lib/query-keys';

interface StudioStat {
  studio_slug: string;
  booked: string;
  total: string;
}

interface DashboardStatsResponse {
  studioStats: StudioStat[];
}

export function StudioSuccessRates() {
  const { data } = useQuery<DashboardStatsResponse>({
    queryKey: QUERY_KEYS.dashboardStats,
    queryFn: async () => {
      const res = await fetch('/api/dashboard/stats');
      if (!res.ok) throw new Error('Failed to fetch stats');
      return res.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes — stats don't need live updates
  });

  if (!data?.studioStats || data.studioStats.length === 0) return null;

  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
      <p className="mb-3 text-sm font-medium text-zinc-400">Success Rate (30 days)</p>
      <div className="space-y-2">
        {data.studioStats.map((stat) => {
          const booked = parseInt(stat.booked, 10);
          const total = parseInt(stat.total, 10);
          const pct = total > 0 ? Math.round((booked / total) * 100) : 0;
          const studioName = STUDIOS[stat.studio_slug]?.name || stat.studio_slug;
          const statColor =
            pct >= 80 ? 'text-emerald-400' : pct < 50 ? 'text-red-400' : 'text-yellow-400';

          return (
            <div key={stat.studio_slug} className="flex items-center justify-between">
              <span className="text-sm text-white">{studioName}</span>
              <span className={`text-sm ${statColor}`}>
                {booked}/{total} booked, {pct}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
