import { createClient } from '@/lib/supabase/server';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { WorkerStatus } from '@/components/worker-status';
import { ActiveJobs } from '@/components/active-jobs';

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  // Fetch stats
  const [targetsRes, jobsRes, historyRes] = await Promise.all([
    supabase.from('snipe_targets').select('id, enabled').eq('user_id', user!.id),
    supabase
      .from('booking_jobs')
      .select('id, status, scheduled_for, target_id')
      .eq('user_id', user!.id)
      .in('status', ['pending', 'claimed', 'running'])
      .order('scheduled_for', { ascending: true }),
    supabase
      .from('booking_history')
      .select('id, status')
      .eq('user_id', user!.id)
      .gte('created_at', new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()),
  ]);

  const targets = targetsRes.data || [];
  const activeJobs = jobsRes.data || [];
  const recentHistory = historyRes.data || [];

  const enabledTargets = targets.filter((t) => t.enabled).length;
  const successfulBookings = recentHistory.filter((h) => h.status === 'booked').length;

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">Dashboard</h1>

      {/* Stats cards */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card className="border-zinc-800 bg-zinc-950">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-400">Active Targets</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-white">{enabledTargets}</p>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-950">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-400">Pending Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-white">{activeJobs.length}</p>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-950">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-400">Booked (30d)</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-400">{successfulBookings}</p>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-950">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-400">Worker</CardTitle>
          </CardHeader>
          <CardContent>
            <WorkerStatus />
          </CardContent>
        </Card>
      </div>

      {/* Active jobs */}
      {activeJobs.length > 0 && (
        <section>
          <h2 className="mb-4 text-xl font-semibold">Upcoming Jobs</h2>
          <ActiveJobs jobs={activeJobs} />
        </section>
      )}
    </div>
  );
}
