import { createClient } from '@/lib/supabase/server';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { STUDIOS } from '@/lib/studios';

const STATUS_STYLES: Record<string, string> = {
  booked: 'bg-green-500/10 text-green-400 border-green-500/30',
  failed: 'bg-red-500/10 text-red-400 border-red-500/30',
  cancelled: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/30',
};

export default async function HistoryPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const { data: history } = await supabase
    .from('booking_history')
    .select('*')
    .eq('user_id', user!.id)
    .order('created_at', { ascending: false })
    .limit(50);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Booking History</h1>

      {!history || history.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-700 p-12 text-center">
          <p className="text-zinc-400">No bookings yet. Once the worker books a class, it will appear here.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {history.map((entry) => {
            const studio = STUDIOS[entry.studio_slug];
            return (
              <Card key={entry.id} className="border-zinc-800 bg-zinc-950">
                <CardContent className="flex items-center justify-between py-4">
                  <div>
                    <p className="font-semibold text-white">
                      {studio?.name || entry.studio_slug}{' '}
                      <span className="text-zinc-400">{entry.location_id}</span>
                    </p>
                    <p className="text-sm text-zinc-500">
                      {new Date(entry.class_date).toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                      })}{' '}
                      @ {entry.class_time}
                      {entry.spot && <span className="ml-2">· Spot {entry.spot}</span>}
                    </p>
                    {entry.message && (
                      <p className="mt-1 text-xs text-zinc-600">{entry.message}</p>
                    )}
                  </div>
                  <Badge variant="outline" className={STATUS_STYLES[entry.status] || ''}>
                    {entry.status}
                  </Badge>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
