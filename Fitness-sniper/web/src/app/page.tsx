import Link from 'next/link';
import { Target, Zap, Bell, ShieldCheck, Clock, Crosshair } from 'lucide-react';

const STUDIO_NAMES = [
  "Barry's Bootcamp",
  'Aarmy',
  'SLT',
  'Rumble Boxing',
  'CycleBar',
  'Club Pilates',
  'YogaSix',
  'Pure Barre',
  'StretchLab',
  'Practice Room',
];

const STEPS = [
  {
    icon: Target,
    title: 'Set Your Targets',
    desc: 'Pick your studio, location, day, time, and preferred spot. Set it once for recurring classes or pick a specific date.',
  },
  {
    icon: Zap,
    title: 'We Book Instantly',
    desc: 'Our worker monitors the schedule and books the moment your class opens — faster than any human.',
  },
  {
    icon: Bell,
    title: 'Get Confirmed',
    desc: 'Receive an email confirmation with your booked spot. Check your dashboard for full history.',
  },
];

const FEATURES = [
  {
    icon: Crosshair,
    title: 'Spot Selection',
    desc: 'Choose front row, back treads, or a specific spot number.',
  },
  {
    icon: ShieldCheck,
    title: 'Encrypted Credentials',
    desc: 'AES-256-GCM encryption. Credentials are only decrypted at booking time.',
  },
  {
    icon: Clock,
    title: 'Recurring & One-Time',
    desc: 'Set weekly recurring targets or book a specific date.',
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500 text-sm font-black text-black">FS</span>
          <span className="text-lg font-bold">Fitness Sniper</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="rounded-lg px-4 py-2 text-sm font-medium text-zinc-400 transition hover:text-white">
            Log In
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-black transition hover:bg-emerald-400"
          >
            Get Started
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* Gradient background */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute left-1/2 top-0 h-[600px] w-[900px] -translate-x-1/2 rounded-full bg-emerald-500/8 blur-3xl" />
          <div className="absolute left-1/4 top-32 h-[400px] w-[400px] rounded-full bg-emerald-600/5 blur-3xl" />
        </div>

        <div className="mx-auto max-w-4xl px-6 pb-24 pt-24 text-center sm:pt-32">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-1.5 text-sm text-emerald-400">
            <Zap className="h-3.5 w-3.5" />
            Never miss a class again
          </div>
          <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-6xl lg:text-7xl">
            Auto-book fitness classes{' '}
            <span className="text-emerald-400">before they fill up</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-zinc-400 sm:text-xl">
            Fitness Sniper monitors schedules and books your spot the instant classes open.
            Set your preferences once — we handle the rest.
          </p>
          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/signup"
              className="w-full rounded-xl bg-emerald-500 px-8 py-3.5 text-center font-semibold text-black transition hover:bg-emerald-400 sm:w-auto"
            >
              Start Booking Free
            </Link>
            <Link
              href="/login"
              className="w-full rounded-xl border border-white/10 px-8 py-3.5 text-center font-semibold transition hover:bg-white/5 sm:w-auto"
            >
              Log In
            </Link>
          </div>
        </div>
      </section>

      {/* Studio logos strip */}
      <section className="border-y border-white/5 bg-white/[0.02] py-10">
        <div className="mx-auto max-w-6xl px-6">
          <p className="mb-6 text-center text-xs font-medium uppercase tracking-widest text-zinc-500">
            Works with your favorite studios
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
            {STUDIO_NAMES.map((name) => (
              <span key={name} className="text-sm font-medium text-zinc-400">
                {name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <h2 className="mb-4 text-center text-sm font-medium uppercase tracking-widest text-emerald-400">
          How it works
        </h2>
        <p className="mx-auto mb-16 max-w-xl text-center text-3xl font-bold sm:text-4xl">
          Three steps to never miss a class
        </p>
        <div className="grid gap-8 sm:grid-cols-3">
          {STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={step.title} className="relative rounded-2xl border border-white/5 bg-white/[0.02] p-8">
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10">
                    <Icon className="h-5 w-5 text-emerald-400" />
                  </div>
                  <span className="text-sm font-bold text-zinc-500">Step {i + 1}</span>
                </div>
                <h3 className="mb-2 text-lg font-semibold">{step.title}</h3>
                <p className="text-sm leading-relaxed text-zinc-400">{step.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-white/5 bg-white/[0.02] py-24">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="mb-16 text-center text-3xl font-bold sm:text-4xl">Built for serious class-goers</h2>
          <div className="grid gap-8 sm:grid-cols-3">
            {FEATURES.map((feat) => {
              const Icon = feat.icon;
              return (
                <div key={feat.title} className="text-center">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5">
                    <Icon className="h-6 w-6 text-emerald-400" />
                  </div>
                  <h3 className="mb-2 font-semibold">{feat.title}</h3>
                  <p className="text-sm text-zinc-400">{feat.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-6 py-24 text-center">
        <h2 className="text-3xl font-bold sm:text-4xl">Ready to stop refreshing?</h2>
        <p className="mx-auto mt-4 max-w-lg text-zinc-400">
          Set up your targets in under 2 minutes. Your next class is already waiting.
        </p>
        <Link
          href="/signup"
          className="mt-8 inline-block rounded-xl bg-emerald-500 px-8 py-3.5 font-semibold text-black transition hover:bg-emerald-400"
        >
          Get Started Free
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8">
        <div className="mx-auto max-w-6xl px-6 text-center text-sm text-zinc-600">
          Fitness Sniper
        </div>
      </footer>
    </div>
  );
}
