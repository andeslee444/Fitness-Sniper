import { createClient } from '@/lib/supabase/server';
import { TargetsList } from '@/components/targets-list';
import { AddTargetDialog } from '@/components/add-target-dialog';

export default async function TargetsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const { data: targets } = await supabase
    .from('snipe_targets')
    .select('*')
    .eq('user_id', user!.id)
    .order('created_at', { ascending: false });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Snipe Targets</h1>
        <AddTargetDialog />
      </div>
      <TargetsList targets={targets || []} />
    </div>
  );
}
