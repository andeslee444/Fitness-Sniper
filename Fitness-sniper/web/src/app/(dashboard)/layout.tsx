import { redirect } from 'next/navigation';
import { getSession } from '@/lib/cognito';
import { NavBar } from '@/components/nav-bar';
import { WorkerOfflineBanner } from '@/components/worker-offline-banner';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await getSession();

  if (!user) {
    redirect('/login');
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <NavBar userEmail={user.email || ''} />
      <WorkerOfflineBanner />
      <main className="mx-auto max-w-6xl px-4 py-6 pb-24 sm:px-6 sm:py-8 sm:pb-8">{children}</main>
    </div>
  );
}
