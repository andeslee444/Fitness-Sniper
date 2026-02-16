'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { STUDIOS, STUDIO_LOCATIONS, STUDIO_TIMES, SEAT_PREFERENCES, SPOT_PREFERENCES } from '@/lib/studios';

const DAYS = [
  { value: '0', label: 'Sunday' },
  { value: '1', label: 'Monday' },
  { value: '2', label: 'Tuesday' },
  { value: '3', label: 'Wednesday' },
  { value: '4', label: 'Thursday' },
  { value: '5', label: 'Friday' },
  { value: '6', label: 'Saturday' },
];

export function AddTargetDialog() {
  const [open, setOpen] = useState(false);
  const [studioSlug, setStudioSlug] = useState('');
  const [locationId, setLocationId] = useState('');
  const [dayOfWeek, setDayOfWeek] = useState('');
  const [time, setTime] = useState('');
  const [seatPref, setSeatPref] = useState('any');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const locations = studioSlug ? STUDIO_LOCATIONS[studioSlug] || [] : [];
  const times = studioSlug ? STUDIO_TIMES[studioSlug] || [] : [];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();

    await supabase.from('snipe_targets').insert({
      user_id: user!.id,
      studio_slug: studioSlug,
      location_id: locationId,
      day_of_week: parseInt(dayOfWeek),
      time,
      seat_preference: seatPref,
      preferred_spots: SPOT_PREFERENCES[seatPref] || [],
      enabled: true,
    });

    setLoading(false);
    setOpen(false);
    // Reset form
    setStudioSlug('');
    setLocationId('');
    setDayOfWeek('');
    setTime('');
    setSeatPref('any');
    router.refresh();
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Add Target</Button>
      </DialogTrigger>
      <DialogContent className="border-zinc-800 bg-zinc-950 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-white">New Snipe Target</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Studio */}
          <div className="space-y-2">
            <Label>Studio</Label>
            <Select value={studioSlug} onValueChange={(v) => { setStudioSlug(v); setLocationId(''); setTime(''); }}>
              <SelectTrigger className="border-zinc-700 bg-zinc-900"><SelectValue placeholder="Select studio" /></SelectTrigger>
              <SelectContent>
                {Object.entries(STUDIOS).map(([slug, info]) => (
                  <SelectItem key={slug} value={slug}>{info.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Location */}
          {locations.length > 0 && (
            <div className="space-y-2">
              <Label>Location</Label>
              <Select value={locationId} onValueChange={setLocationId}>
                <SelectTrigger className="border-zinc-700 bg-zinc-900"><SelectValue placeholder="Select location" /></SelectTrigger>
                <SelectContent>
                  {locations.map((loc) => (
                    <SelectItem key={loc.id} value={loc.id}>{loc.name}{loc.address && ` — ${loc.address}`}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Location ID input for studios without pre-set locations */}
          {studioSlug && locations.length === 0 && (
            <div className="space-y-2">
              <Label>Location ID</Label>
              <Input
                value={locationId}
                onChange={(e) => setLocationId(e.target.value)}
                placeholder="e.g. downtown"
                className="border-zinc-700 bg-zinc-900"
              />
            </div>
          )}

          {/* Day of Week */}
          <div className="space-y-2">
            <Label>Day</Label>
            <Select value={dayOfWeek} onValueChange={setDayOfWeek}>
              <SelectTrigger className="border-zinc-700 bg-zinc-900"><SelectValue placeholder="Select day" /></SelectTrigger>
              <SelectContent>
                {DAYS.map((d) => (
                  <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Time */}
          <div className="space-y-2">
            <Label>Time</Label>
            {times.length > 0 ? (
              <Select value={time} onValueChange={setTime}>
                <SelectTrigger className="border-zinc-700 bg-zinc-900"><SelectValue placeholder="Select time" /></SelectTrigger>
                <SelectContent>
                  {times.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input
                value={time}
                onChange={(e) => setTime(e.target.value)}
                placeholder="e.g. 6:00 AM"
                className="border-zinc-700 bg-zinc-900"
              />
            )}
          </div>

          {/* Seat Preference */}
          <div className="space-y-2">
            <Label>Seat Preference</Label>
            <Select value={seatPref} onValueChange={setSeatPref}>
              <SelectTrigger className="border-zinc-700 bg-zinc-900"><SelectValue /></SelectTrigger>
              <SelectContent>
                {SEAT_PREFERENCES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button type="submit" disabled={loading || !studioSlug || !dayOfWeek || !time} className="w-full">
            {loading ? 'Adding...' : 'Add Target'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
