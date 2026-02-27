'use client';

import { CalendarView } from '@/components/calendar-view';
import { WorkerStatus } from '@/components/worker-status';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold sm:text-3xl">Your Week</h1>
        <WorkerStatus />
      </div>
      <CalendarView />
    </div>
  );
}
