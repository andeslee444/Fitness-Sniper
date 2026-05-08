'use client';

import Link from 'next/link';
import { Check, ChevronRight } from 'lucide-react';

interface SetupStepProps {
  number: number;
  label: string;
  href: string;
  done: boolean;
}

function SetupStep({ number, label, href, done }: SetupStepProps) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 rounded-xl border p-4 transition-colors hover:bg-white/[0.04] ${
        done
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : 'border-white/10 bg-white/[0.02]'
      }`}
    >
      <span
        className={`h-7 w-7 rounded-full text-sm font-bold flex items-center justify-center shrink-0 ${
          done ? 'bg-emerald-500 text-black' : 'bg-white/10 text-zinc-400'
        }`}
      >
        {done ? <Check className="h-4 w-4" /> : number}
      </span>
      <span className={done ? 'text-emerald-400' : 'text-white'}>{label}</span>
      {!done && <ChevronRight className="ml-auto h-4 w-4 text-zinc-600" />}
    </Link>
  );
}

export function EmptyStateGuide({ hasCredentials }: { hasCredentials: boolean }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center">
      <h2 className="text-lg font-semibold text-white mb-6">Get started in 3 steps</h2>
      <div className="mx-auto max-w-sm space-y-4 text-left">
        <SetupStep
          number={1}
          label="Add your studio credentials"
          href="/credentials"
          done={hasCredentials}
        />
        <SetupStep
          number={2}
          label="Browse the class schedule"
          href="/schedule"
          done={false}
        />
        <SetupStep
          number={3}
          label="Create your first snipe target"
          href="/schedule"
          done={false}
        />
      </div>
    </div>
  );
}
