import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import { redirect } from 'next/navigation';
import { CredentialsPageClient } from './credentials-page-client';

export default async function CredentialsPage() {
  const user = await getSession();
  if (!user) redirect('/login');

  const { rows: creds } = await query<{ studio_slug: string }>(
    'SELECT studio_slug FROM studio_credentials WHERE user_id = $1',
    [user.sub],
  );

  const savedSlugs = creds.map((c) => c.studio_slug);

  return <CredentialsPageClient savedSlugs={savedSlugs} />;
}
