'use client';

import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { STUDIOS, STUDIO_LOCATIONS, DAY_ABBR, SEAT_PREFERENCES } from '@/lib/studios';
import type { SnipeTarget } from '@/lib/types';

export function TargetsList({ targets }: { targets: SnipeTarget[] }) {
  const router = useRouter();

  async function toggleTarget(id: string, enabled: boolean) {
    const supabase = createClient();
    await supabase.from('snipe_targets').update({ enabled }).eq('id', id);
    router.refresh();
  }

  async function deleteTarget(id: string) {
    const supabase = createClient();
    await supabase.from('snipe_targets').delete().eq('id', id);
    router.refresh();
  }

  if (targets.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-700 p-12 text-center">
        <p className="text-zinc-400">No targets yet. Add one to start auto-booking.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {targets.map((target) => {
        const studio = STUDIOS[target.studio_slug];
        const location = STUDIO_LOCATIONS[target.studio_slug]?.find(
          (l) => l.id === target.location_id,
        );
        const seatLabel = SEAT_PREFERENCES.find((s) => s.value === target.seat_preference)?.label;

        return (
          <Card key={target.id} className="border-zinc-800 bg-zinc-950">
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex items-center gap-4">
                <Switch
                  checked={target.enabled}
                  onCheckedChange={(checked) => toggleTarget(target.id, checked)}
                />
                <div>
                  <p className="font-semibold text-white">
                    {studio?.name || target.studio_slug}{' '}
                    <span className="text-zinc-400">{location?.name || target.location_id}</span>
                  </p>
                  <p className="text-sm text-zinc-500">
                    {DAY_ABBR[target.day_of_week]} @ {target.time}
                    {seatLabel && <span className="ml-2">· {seatLabel}</span>}
                    {target.preferred_spots && target.preferred_spots.length > 0 && (
                      <span className="ml-2">· Spots: {target.preferred_spots.join(', ')}</span>
                    )}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={target.enabled ? 'default' : 'outline'} className={target.enabled ? 'bg-green-500/10 text-green-400 border-green-500/30' : 'border-zinc-700 text-zinc-500'}>
                  {target.enabled ? 'Active' : 'Paused'}
                </Badge>
                <Button variant="ghost" size="sm" onClick={() => deleteTarget(target.id)} className="text-zinc-500 hover:text-red-400">
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
