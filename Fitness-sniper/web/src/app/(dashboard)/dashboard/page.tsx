'use client';

import Link from 'next/link';
import { Target, Clock, CheckCircle, Wifi, ArrowRight, KeyRound, Crosshair } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { WorkerStatus } from '@/components/worker-status';
import { ActiveJobs } from '@/components/active-jobs';
import { StatCardSkeleton } from '@/components/skeleton';
import { QUERY_KEYS } from '@/lib/query-keys';
import type { JobStatus } from '@/lib/types';

interface DashboardStats {
  targets: { id: string; enabled: boolean }[];
  activeJobs: { id: string; status: JobStatus; scheduled_for: string; class_datetime: string | null; target_id: string }[];
  recentHistory: { id: string; status: string }[];
}

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: QUERY_KEYS.dashboardStats,
    queryFn: async () => {
      const res = await fetch('/api/dashboard/stats');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json() as Promise<DashboardStats>;
    },
    refetchInterval: 30_000,
  });

  const enabledTargets = stats?.targets.filter((t) => t.enabled).length ?? 0;
  const totalTargets = stats?.targets.length ?? 0;
  const activeJobCount = stats?.activeJobs?.length ?? 0;
  const successfulBookings = stats?.recentHistory.filter((h) => h.status === 'booked').length ?? 0;
  const isNewUser = stats !== null && stats !== undefined && totalTargets === 0;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold sm:text-3xl">Dashboard</h1>

      {/* Onboarding for new users */}
      {isNewUser && (
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6">
          <h2 className="mb-1 text-lg font-semibold">Get started in 3 steps</h2>
          <p className="mb-6 text-sm text-zinc-400">Set up your first auto-booking in under 2 minutes.</p>
          <div className="grid gap-4 sm:grid-cols-3">
            <OnboardingStep
              step={1}
              icon={KeyRound}
              title="Save Credentials"
              desc="Add your studio login so we can book for you."
              href="/credentials"
            />
            <OnboardingStep
              step={2}
              icon={Crosshair}
              title="Add a Target"
              desc="Pick studio, day, time, and preferred spot."
              href="/targets"
            />
            <OnboardingStep
              step={3}
              icon={CheckCircle}
              title="We Handle the Rest"
              desc="Our worker books the instant classes open."
            />
          </div>
        </div>
      )}

      {/* Stats cards */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-4">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-4">
          <StatCard
            icon={Target}
            label="Active Targets"
            value={enabledTargets}
            iconColor="text-blue-400"
            iconBg="bg-blue-500/10"
          />
          <StatCard
            icon={Clock}
            label="Pending Jobs"
            value={activeJobCount}
            iconColor="text-yellow-400"
            iconBg="bg-yellow-500/10"
          />
          <StatCard
            icon={CheckCircle}
            label="Booked (30d)"
            value={successfulBookings}
            valueColor="text-emerald-400"
            iconColor="text-emerald-400"
            iconBg="bg-emerald-500/10"
          />
          <div className="flex flex-col justify-between rounded-2xl border border-white/5 bg-white/[0.02] p-6">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10">
                <Wifi className="h-4 w-4 text-purple-400" />
              </div>
              <span className="text-sm font-medium text-zinc-400">Worker</span>
            </div>
            <WorkerStatus />
          </div>
        </div>
      )}

      {/* Active jobs — self-contained, handles empty state internally */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Upcoming Jobs</h2>
          <Link href="/history" className="flex items-center gap-1 text-sm text-zinc-400 hover:text-white">
            View history <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        <ActiveJobs />
      </section>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  valueColor = 'text-white',
  iconColor,
  iconBg,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  valueColor?: string;
  iconColor: string;
  iconBg: string;
}) {
  return (
    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
      <div className="mb-3 flex items-center gap-2">
        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${iconBg}`}>
          <Icon className={`h-4 w-4 ${iconColor}`} />
        </div>
        <span className="text-sm font-medium text-zinc-400">{label}</span>
      </div>
      <p className={`text-3xl font-bold ${valueColor}`}>{value}</p>
    </div>
  );
}

function OnboardingStep({
  step,
  icon: Icon,
  title,
  desc,
  href,
}: {
  step: number;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  desc: string;
  href?: string;
}) {
  const content = (
    <div className="flex items-start gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-4 transition-colors hover:border-emerald-500/20">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
        <Icon className="h-4 w-4 text-emerald-400" />
      </div>
      <div>
        <div className="mb-0.5 flex items-center gap-2">
          <span className="text-xs font-medium text-emerald-400">Step {step}</span>
        </div>
        <p className="text-sm font-semibold text-white">{title}</p>
        <p className="mt-0.5 text-xs text-zinc-500">{desc}</p>
      </div>
    </div>
  );

  return href ? <Link href={href}>{content}</Link> : content;
}
