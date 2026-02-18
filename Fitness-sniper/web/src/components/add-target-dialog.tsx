'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { CalendarIcon, Loader2, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
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
import { STUDIOS, STUDIO_LOCATIONS, SEAT_PREFERENCES, SPOT_PREFERENCES } from '@/lib/studios';
import type { StudioConfig } from '@/lib/studios';
import type { TargetType } from '@/lib/types';

const DAYS = [
  { value: '0', label: 'Sunday' },
  { value: '1', label: 'Monday' },
  { value: '2', label: 'Tuesday' },
  { value: '3', label: 'Wednesday' },
  { value: '4', label: 'Thursday' },
  { value: '5', label: 'Friday' },
  { value: '6', label: 'Saturday' },
];

interface ScheduleClass {
  class_time: string;
  class_name: string | null;
  instructor: string | null;
}

interface ScheduleResponse {
  source: 'scraped' | 'live_api' | 'empty';
  times: string[];
  classes: ScheduleClass[];
}

function formatDateToStr(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function AddTargetDialog() {
  const [open, setOpen] = useState(false);
  const [targetType, setTargetType] = useState<TargetType>('recurring');
  const [studioSlug, setStudioSlug] = useState('');
  const [locationId, setLocationId] = useState('');
  const [dayOfWeek, setDayOfWeek] = useState('');
  const [targetDate, setTargetDate] = useState<Date | undefined>();
  const [time, setTime] = useState('');
  const [seatPref, setSeatPref] = useState('any');
  const [loading, setLoading] = useState(false);
  const [timesLoading, setTimesLoading] = useState(false);
  const [scheduleData, setScheduleData] = useState<ScheduleResponse | null>(null);
  const router = useRouter();

  const locations = studioSlug ? STUDIO_LOCATIONS[studioSlug] || [] : [];

  // Determine available times from API response
  const times = scheduleData?.times ?? [];
  const isLive = scheduleData?.source === 'scraped' || scheduleData?.source === 'live_api';

  // Build a map from time → class detail string for display
  const timeDisplayMap = new Map<string, string>();
  if (isLive && scheduleData?.classes) {
    // Deduplicate: for the same time, pick the first class entry
    for (const cls of scheduleData.classes) {
      if (!timeDisplayMap.has(cls.class_time)) {
        const parts = [cls.class_time];
        const detail = [cls.class_name, cls.instructor].filter(Boolean).join(' - ');
        if (detail) parts.push(detail);
        timeDisplayMap.set(cls.class_time, parts.join(' — '));
      }
    }
  }

  // Fetch class schedules when studio/location/day/date changes
  useEffect(() => {
    setTime('');

    if (!studioSlug) {
      setScheduleData(null);
      return;
    }

    const controller = new AbortController();

    const params = new URLSearchParams({ studio: studioSlug });
    if (locationId) params.set('location', locationId);

    if (targetType === 'one_time' && targetDate) {
      params.set('date', formatDateToStr(targetDate));
    } else if (targetType === 'recurring' && dayOfWeek !== '') {
      params.set('dayOfWeek', dayOfWeek);
    }

    setTimesLoading(true);
    fetch(`/api/schedules?${params}`, { signal: controller.signal })
      .then(async (res) => {
        if (res.ok) {
          const data: ScheduleResponse = await res.json();
          setScheduleData(data);
        } else {
          setScheduleData(null);
        }
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setScheduleData(null);
      })
      .finally(() => setTimesLoading(false));

    return () => controller.abort();
  }, [studioSlug, locationId, targetType, dayOfWeek, targetDate]);

  const isValid = studioSlug && time && (
    targetType === 'recurring' ? dayOfWeek !== '' : targetDate !== undefined
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch('/api/targets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          studio_slug: studioSlug,
          location_id: locationId,
          target_type: targetType,
          day_of_week: targetType === 'recurring' ? parseInt(dayOfWeek) : null,
          target_date: targetType === 'one_time' && targetDate ? formatDateToStr(targetDate) : null,
          time,
          seat_preference: seatPref,
          preferred_spots: SPOT_PREFERENCES[seatPref] || [],
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Failed to create target');
      }

      toast.success('Target added');
      setOpen(false);
      resetForm();
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create target');
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setTargetType('recurring');
    setStudioSlug('');
    setLocationId('');
    setDayOfWeek('');
    setTargetDate(undefined);
    setTime('');
    setSeatPref('any');
    setScheduleData(null);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-emerald-500 text-black hover:bg-emerald-400">
          <Plus className="mr-1.5 h-4 w-4" />
          Add Target
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto border-white/10 bg-zinc-950 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-white">New Snipe Target</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Target Type Toggle */}
          <div className="flex rounded-lg border border-zinc-700 p-1">
            <button
              type="button"
              onClick={() => setTargetType('recurring')}
              className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                targetType === 'recurring'
                  ? 'bg-white/10 text-white'
                  : 'text-zinc-400 hover:text-zinc-300'
              }`}
            >
              Recurring
            </button>
            <button
              type="button"
              onClick={() => setTargetType('one_time')}
              className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                targetType === 'one_time'
                  ? 'bg-white/10 text-white'
                  : 'text-zinc-400 hover:text-zinc-300'
              }`}
            >
              One-Time
            </button>
          </div>

          {/* Studio */}
          <div className="space-y-2">
            <Label>Studio</Label>
            <Select value={studioSlug} onValueChange={(v) => { setStudioSlug(v); setLocationId(''); setTime(''); }}>
              <SelectTrigger className="border-white/10 bg-white/5"><SelectValue placeholder="Select studio" /></SelectTrigger>
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
                <SelectTrigger className="border-white/10 bg-white/5"><SelectValue placeholder="Select location" /></SelectTrigger>
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
                placeholder={
                  STUDIOS[studioSlug]?.platform === 'xponential'
                    ? `e.g. ${STUDIOS[studioSlug]?.slug}-downtown`
                    : 'e.g. chelsea'
                }
                className="border-white/10 bg-white/5"
              />
              {STUDIOS[studioSlug]?.platform === 'xponential' && (
                <p className="text-xs text-zinc-500">
                  Format: {STUDIOS[studioSlug]?.slug}-location-name
                </p>
              )}
            </div>
          )}

          {/* Day of Week (recurring only) */}
          {targetType === 'recurring' && (
            <div className="space-y-2">
              <Label>Day</Label>
              <Select value={dayOfWeek} onValueChange={setDayOfWeek}>
                <SelectTrigger className="border-white/10 bg-white/5"><SelectValue placeholder="Select day" /></SelectTrigger>
                <SelectContent>
                  {DAYS.map((d) => (
                    <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Date picker (one-time only) */}
          {targetType === 'one_time' && (
            <div className="space-y-2">
              <Label>Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full justify-start border-white/10 bg-white/5 text-left font-normal hover:bg-zinc-800"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4 text-zinc-400" />
                    {targetDate
                      ? targetDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
                      : <span className="text-zinc-400">Pick a date</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto border-zinc-700 bg-zinc-950 p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={targetDate}
                    onSelect={setTargetDate}
                    disabled={{ before: new Date() }}
                    defaultMonth={targetDate || new Date()}
                  />
                </PopoverContent>
              </Popover>
            </div>
          )}

          {/* Time */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label>Time</Label>
              {timesLoading && <Loader2 className="h-3 w-3 animate-spin text-zinc-400" />}
              {isLive && !timesLoading && (
                <span className="rounded bg-emerald-900/50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400">
                  Live
                </span>
              )}
            </div>
            {times.length > 0 ? (
              <Select value={time} onValueChange={setTime}>
                <SelectTrigger className="border-white/10 bg-white/5"><SelectValue placeholder="Select time" /></SelectTrigger>
                <SelectContent>
                  {times.map((t) => (
                    <SelectItem key={t} value={t}>
                      {timeDisplayMap.get(t) || t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input
                value={time}
                onChange={(e) => setTime(e.target.value)}
                placeholder="e.g. 6:00 AM"
                className="border-white/10 bg-white/5"
              />
            )}
          </div>

          {/* Seat Preference */}
          <div className="space-y-2">
            <Label>Seat Preference</Label>
            <Select value={seatPref} onValueChange={setSeatPref}>
              <SelectTrigger className="border-white/10 bg-white/5"><SelectValue /></SelectTrigger>
              <SelectContent>
                {SEAT_PREFERENCES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button type="submit" disabled={loading || !isValid} className="w-full bg-emerald-500 text-black hover:bg-emerald-400 disabled:opacity-50">
            {loading ? 'Adding...' : 'Add Target'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
