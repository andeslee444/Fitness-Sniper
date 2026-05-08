import { redirect } from 'next/navigation';
import { getSession } from '@/lib/cognito';
import { SchedulePageClient } from './schedule-page-client';

export default async function SchedulePage() {
  const user = await getSession();
  if (!user) {
    redirect('/login');
  }
  return <SchedulePageClient />;
}
