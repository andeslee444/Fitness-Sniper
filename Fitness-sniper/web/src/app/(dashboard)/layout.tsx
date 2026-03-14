import { redirect } from 'next/navigation';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import { NavBar } from '@/components/nav-bar';
import { WorkerOfflineBanner } from '@/components/worker-offline-banner';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await getSession();

  if (!user) {
    redirect('/login');
  }

  // New-user detection: redirect to onboarding if no credentials and no targets.
  // /onboarding is outside the (dashboard) route group — this layout does NOT run for it,
  // so there is no redirect loop.
  const [{ rows: credRows }, { rows: targetRows }] = await Promise.all([
    query<{ exists: boolean }>(
      'SELECT EXISTS(SELECT 1 FROM studio_credentials WHERE user_id = $1) as exists',
      [user.sub]
    ),
    query<{ exists: boolean }>(
      'SELECT EXISTS(SELECT 1 FROM snipe_targets WHERE user_id = $1) as exists',
      [user.sub]
    ),
  ]);

  const isNewUser = !credRows[0]?.exists && !targetRows[0]?.exists;
  if (isNewUser) redirect('/onboarding');

  return (
    <div className="min-h-screen bg-black text-white">
      <NavBar userEmail={user.email || ''} />
      <WorkerOfflineBanner />
      <main className="mx-auto max-w-6xl px-4 py-6 pb-24 sm:px-6 sm:py-8 sm:pb-8">{children}</main>
    </div>
  );
}
