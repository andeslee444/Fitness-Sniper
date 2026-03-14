import { redirect } from 'next/navigation';
import { getSession } from '@/lib/cognito';
import { OnboardingFlow } from '@/components/onboarding/onboarding-flow';

export default async function OnboardingPage() {
  const user = await getSession();
  if (!user) redirect('/login');

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
        <div className="mb-8 text-center">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500 text-sm font-black text-black">
            FS
          </span>
          <h1 className="mt-4 text-2xl font-bold">Welcome to Fitness Sniper</h1>
          <p className="mt-2 text-zinc-400">
            Let&apos;s get you set up to auto-book your favorite classes.
          </p>
        </div>
        <OnboardingFlow />
      </div>
    </div>
  );
}
