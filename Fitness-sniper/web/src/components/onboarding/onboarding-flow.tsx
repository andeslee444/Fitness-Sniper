'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { STUDIOS } from '@/lib/studios';
import type { StudioConfig } from '@fitness-sniper/shared';

// Hardcoded descriptions — STUDIOS config doesn't include user-facing descriptions
const STUDIO_DESCRIPTIONS: Record<string, string> = {
  barrys: 'High-intensity interval training',
  aarmy: 'Military-inspired group fitness',
  slt: 'Strengthen, Lengthen, Tone on the Megaformer',
  rumble: 'Boxing-inspired group fitness',
  cyclebar: 'Premium indoor cycling',
  clubpilates: 'Reformer-based Pilates',
  yogasix: 'Modern boutique yoga',
  stretchlab: 'Assisted stretching',
  purebarre: 'Barre-based total body workout',
  practiceroom: 'Multi-discipline NYC studio',
  saint: 'Private sauna and ice bath',
};

const STEPS = ['Pick Studios', 'Add Credentials', 'Browse Schedule', 'Create Snipe'];

function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {STEPS.map((label, index) => (
        <div key={index} className="flex items-center">
          <div className="flex flex-col items-center gap-1">
            <div
              className={`h-8 w-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
                index < currentStep
                  ? 'bg-emerald-500 text-black'
                  : index === currentStep
                    ? 'bg-emerald-500 text-black ring-2 ring-emerald-500/30 ring-offset-2 ring-offset-black'
                    : 'bg-zinc-800 text-zinc-500'
              }`}
            >
              {index < currentStep ? <Check className="h-4 w-4" /> : index + 1}
            </div>
            <span
              className={`text-xs font-medium ${
                index === currentStep ? 'text-emerald-400' : 'text-zinc-600'
              }`}
            >
              {label}
            </span>
          </div>
          {index < STEPS.length - 1 && (
            <div
              className={`h-0.5 w-12 mx-1 mb-5 transition-colors ${
                index < currentStep ? 'bg-emerald-500' : 'bg-zinc-800'
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// Step 1: Pick studios
function PickStudiosStep({
  selectedStudios,
  onToggle,
  onNext,
}: {
  selectedStudios: string[];
  onToggle: (slug: string) => void;
  onNext: () => void;
}) {
  const studioEntries = Object.entries(STUDIOS);

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-1">Which studios do you have memberships at?</h2>
      <p className="text-sm text-zinc-400 mb-5">Select all that apply. You can change this later.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
        {studioEntries.map(([slug, studio]) => {
          const isSelected = selectedStudios.includes(slug);
          return (
            <button
              key={slug}
              type="button"
              onClick={() => onToggle(slug)}
              className={`relative flex items-start gap-3 rounded-xl border p-4 text-left transition-all ${
                isSelected
                  ? 'border-emerald-500/50 bg-emerald-500/10'
                  : 'border-white/10 bg-white/[0.02] hover:bg-white/[0.04]'
              }`}
            >
              <div
                className={`mt-0.5 h-5 w-5 rounded-md border flex items-center justify-center shrink-0 transition-colors ${
                  isSelected ? 'border-emerald-500 bg-emerald-500' : 'border-zinc-600 bg-transparent'
                }`}
              >
                {isSelected && <Check className="h-3 w-3 text-black" />}
              </div>
              <div className="min-w-0">
                <p className={`text-sm font-medium leading-tight ${isSelected ? 'text-emerald-400' : 'text-white'}`}>
                  {studio.name}
                </p>
                <p className="text-xs text-zinc-500 mt-0.5 leading-snug">
                  {STUDIO_DESCRIPTIONS[slug] ?? ''}
                </p>
              </div>
            </button>
          );
        })}
      </div>
      <Button
        onClick={onNext}
        disabled={selectedStudios.length === 0}
        className="w-full bg-emerald-500 text-black hover:bg-emerald-400 disabled:opacity-40"
        size="lg"
      >
        Next — Add credentials
      </Button>
    </div>
  );
}

// Step 2: Add credentials
function AddCredentialsStep({
  selectedStudios,
  onNext,
  onSkip,
}: {
  selectedStudios: string[];
  onNext: () => void;
  onSkip: () => void;
}) {
  const router = useRouter();

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-1">Add your studio credentials</h2>
      <p className="text-sm text-zinc-400 mb-5">
        Fitness Sniper needs your login credentials to book classes on your behalf.
        Your credentials are encrypted with AES-256-GCM.
      </p>
      {selectedStudios.length > 0 && (
        <div className="mb-5 rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">
            Studios to add credentials for
          </p>
          <div className="space-y-2">
            {selectedStudios.map((slug) => (
              <div key={slug} className="flex items-center gap-2 text-sm text-zinc-300">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
                {STUDIOS[slug]?.name ?? slug}
              </div>
            ))}
          </div>
        </div>
      )}
      <Button
        onClick={() => router.push('/credentials')}
        className="w-full bg-emerald-500 text-black hover:bg-emerald-400 mb-3"
        size="lg"
      >
        Go to Credentials Page
      </Button>
      <Button
        onClick={onNext}
        variant="outline"
        className="w-full border-white/10 bg-transparent text-white hover:bg-white/[0.04] mb-3"
        size="lg"
      >
        I&apos;ve added my credentials — continue
      </Button>
      <button
        type="button"
        onClick={onSkip}
        className="w-full text-sm text-zinc-500 hover:text-zinc-300 transition-colors py-2"
      >
        Skip for now
      </button>
    </div>
  );
}

// Step 3: Browse schedule
function BrowseScheduleStep({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  const router = useRouter();

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-1">Browse the class schedule</h2>
      <p className="text-sm text-zinc-400 mb-5">
        The schedule browser shows upcoming classes across all your studios. Find classes you want
        to snipe and set them up for auto-booking.
      </p>
      <div className="mb-6 rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-3">
        <div className="flex items-start gap-3">
          <div className="h-6 w-6 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
            <span className="text-xs font-bold text-emerald-400">1</span>
          </div>
          <p className="text-sm text-zinc-300">Browse classes by week across all your studios</p>
        </div>
        <div className="flex items-start gap-3">
          <div className="h-6 w-6 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
            <span className="text-xs font-bold text-emerald-400">2</span>
          </div>
          <p className="text-sm text-zinc-300">Click any class to see details and availability</p>
        </div>
        <div className="flex items-start gap-3">
          <div className="h-6 w-6 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
            <span className="text-xs font-bold text-emerald-400">3</span>
          </div>
          <p className="text-sm text-zinc-300">Tap &quot;Snipe This&quot; to set up auto-booking</p>
        </div>
      </div>
      <Button
        onClick={() => router.push('/schedule')}
        className="w-full bg-emerald-500 text-black hover:bg-emerald-400 mb-3"
        size="lg"
      >
        Open Schedule Browser
      </Button>
      <Button
        onClick={onNext}
        variant="outline"
        className="w-full border-white/10 bg-transparent text-white hover:bg-white/[0.04] mb-3"
        size="lg"
      >
        I&apos;ve browsed the schedule — continue
      </Button>
      <button
        type="button"
        onClick={onSkip}
        className="w-full text-sm text-zinc-500 hover:text-zinc-300 transition-colors py-2"
      >
        Skip for now
      </button>
    </div>
  );
}

// Step 4: Create snipe
function CreateSnipeStep({ onDone }: { onDone: () => void }) {
  const router = useRouter();

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-1">Create your first snipe target</h2>
      <p className="text-sm text-zinc-400 mb-5">
        A snipe target tells Fitness Sniper which class to auto-book and when. Once created, the
        system will attempt to book the class the moment it becomes available.
      </p>
      <div className="mb-6 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
        <p className="text-sm text-emerald-400 font-medium mb-1">How it works</p>
        <p className="text-sm text-zinc-400">
          From the schedule browser, click any class and tap &quot;Snipe This.&quot; Choose recurring (same
          class every week) or one-time. Fitness Sniper handles the rest — booking exactly when the
          class opens.
        </p>
      </div>
      <Button
        onClick={() => router.push('/schedule')}
        className="w-full bg-emerald-500 text-black hover:bg-emerald-400 mb-3"
        size="lg"
      >
        Go to Schedule to Create Snipe
      </Button>
      <Button
        onClick={onDone}
        variant="outline"
        className="w-full border-white/10 bg-transparent text-white hover:bg-white/[0.04]"
        size="lg"
      >
        Done — Go to Dashboard
      </Button>
    </div>
  );
}

export function OnboardingFlow() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [selectedStudios, setSelectedStudios] = useState<string[]>([]);

  function toggleStudio(slug: string) {
    setSelectedStudios((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    );
  }

  function goNext() {
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  function goToDashboard() {
    router.push('/dashboard');
  }

  return (
    <div className="relative rounded-2xl border border-white/10 bg-white/[0.02] p-6 sm:p-8">
      {/* Skip setup link */}
      <div className="absolute top-4 right-4">
        <button
          type="button"
          onClick={goToDashboard}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          Skip setup
        </button>
      </div>

      <StepIndicator currentStep={step} />

      {step === 0 && (
        <PickStudiosStep
          selectedStudios={selectedStudios}
          onToggle={toggleStudio}
          onNext={goNext}
        />
      )}
      {step === 1 && (
        <AddCredentialsStep
          selectedStudios={selectedStudios}
          onNext={goNext}
          onSkip={goNext}
        />
      )}
      {step === 2 && (
        <BrowseScheduleStep
          onNext={goNext}
          onSkip={goNext}
        />
      )}
      {step === 3 && (
        <CreateSnipeStep
          onDone={goToDashboard}
        />
      )}
    </div>
  );
}
