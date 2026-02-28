'use client';

import { useState, useEffect } from 'react';
import { CredentialForm } from '@/components/credential-form';
import { STUDIOS } from '@/lib/studios';
import { ShieldCheck } from 'lucide-react';

type ValidationStatus = 'connected' | 'untested' | 'invalid' | 'checking';

export function CredentialsPageClient({ savedSlugs }: { savedSlugs: string[] }) {
  const [statuses, setStatuses] = useState<Record<string, ValidationStatus>>({});

  const savedSet = new Set(savedSlugs);
  const savedStudios = Object.entries(STUDIOS).filter(([slug]) => savedSet.has(slug));
  const unsavedStudios = Object.entries(STUDIOS).filter(([slug]) => !savedSet.has(slug));

  // Validate each saved credential on mount
  useEffect(() => {
    if (savedSlugs.length === 0) return;

    // Set all to 'checking' initially
    const initial: Record<string, ValidationStatus> = {};
    for (const slug of savedSlugs) {
      initial[slug] = 'checking';
    }
    setStatuses(initial);

    // Fire validation sequentially to avoid rate limits
    let cancelled = false;

    async function validateAll() {
      for (const slug of savedSlugs) {
        if (cancelled) break;
        try {
          const res = await fetch('/api/credentials/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ studioSlug: slug }),
          });
          if (res.ok) {
            const data = await res.json();
            if (!cancelled) {
              setStatuses((prev) => ({ ...prev, [slug]: data.status }));
            }
          } else {
            if (!cancelled) {
              setStatuses((prev) => ({ ...prev, [slug]: 'untested' }));
            }
          }
        } catch {
          if (!cancelled) {
            setStatuses((prev) => ({ ...prev, [slug]: 'untested' }));
          }
        }
      }
    }

    validateAll();
    return () => {
      cancelled = true;
    };
  }, [savedSlugs]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">Studio Credentials</h1>
        <p className="mt-1 flex items-center gap-1.5 text-sm text-zinc-400">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
          Encrypted with AES-256-GCM. Only decrypted at booking time.
        </p>
      </div>

      {/* Saved credentials */}
      {savedStudios.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wider text-zinc-500">
            Your Studios ({savedStudios.length})
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {savedStudios.map(([slug, info]) => (
              <CredentialForm
                key={slug}
                studioSlug={slug}
                studioName={info.name}
                hasSaved={true}
                validationStatus={statuses[slug]}
              />
            ))}
          </div>
        </section>
      )}

      {/* Available studios */}
      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wider text-zinc-500">
          {savedStudios.length > 0 ? 'Add a Studio' : 'Choose a Studio'}
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {unsavedStudios.map(([slug, info]) => (
            <CredentialForm
              key={slug}
              studioSlug={slug}
              studioName={info.name}
              hasSaved={false}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
