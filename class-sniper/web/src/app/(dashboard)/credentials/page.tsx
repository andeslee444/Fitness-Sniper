import { createClient } from '@/lib/supabase/server';
import { CredentialForm } from '@/components/credential-form';
import { STUDIOS } from '@/lib/studios';

export default async function CredentialsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const { data: creds } = await supabase
    .from('studio_credentials')
    .select('studio_slug')
    .eq('user_id', user!.id);

  const savedSlugs = new Set((creds || []).map((c) => c.studio_slug));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Studio Credentials</h1>
        <p className="mt-1 text-zinc-400">
          Store your login credentials for each studio. They are encrypted before being saved.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {Object.entries(STUDIOS).map(([slug, info]) => (
          <CredentialForm
            key={slug}
            studioSlug={slug}
            studioName={info.name}
            hasSaved={savedSlugs.has(slug)}
          />
        ))}
      </div>
    </div>
  );
}
