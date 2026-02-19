import { redirect } from 'next/navigation';
import { getSession } from '@/lib/cognito';
import { ScheduleExplorer } from './schedule-explorer';

export default async function SchedulePage() {
  const user = await getSession();

  if (!user) {
    redirect('/login');
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">Schedule Explorer</h1>
        <p className="mt-1 text-sm text-zinc-400">Browse class schedules and availability</p>
      </div>
      <ScheduleExplorer />
    </div>
  );
}
