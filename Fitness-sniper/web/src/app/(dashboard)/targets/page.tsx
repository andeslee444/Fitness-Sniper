import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import { AddTargetDialog } from '@/components/add-target-dialog';
import { TargetsTabs } from './targets-tabs';
import type { SnipeTarget } from '@/lib/types';

export default async function TargetsPage() {
  const user = await getSession();

  const { rows: targets } = await query<SnipeTarget>(
    'SELECT * FROM snipe_targets WHERE user_id = $1 ORDER BY created_at DESC',
    [user!.sub],
  );

  const allTargets = targets || [];
  const recurring = allTargets.filter((t) => t.target_type === 'recurring');
  const oneTime = allTargets.filter((t) => t.target_type === 'one_time');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">Snipe Targets</h1>
          <p className="mt-1 text-sm text-zinc-400">{allTargets.length} target{allTargets.length !== 1 ? 's' : ''} configured</p>
        </div>
        <AddTargetDialog />
      </div>
      <TargetsTabs recurring={recurring} oneTime={oneTime} />
    </div>
  );
}
