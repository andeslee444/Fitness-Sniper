import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import { CredentialForm } from '@/components/credential-form';
import { STUDIOS } from '@/lib/studios';
import { ShieldCheck } from 'lucide-react';

export default async function CredentialsPage() {
  const user = await getSession();

  const { rows: creds } = await query<{ studio_slug: string }>(
    'SELECT studio_slug FROM studio_credentials WHERE user_id = $1',
    [user!.sub],
  );

  const savedSlugs = new Set(creds.map((c) => c.studio_slug));
  const savedStudios = Object.entries(STUDIOS).filter(([slug]) => savedSlugs.has(slug));
  const unsavedStudios = Object.entries(STUDIOS).filter(([slug]) => !savedSlugs.has(slug));

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
