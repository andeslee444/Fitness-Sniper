// DEPRECATED — Replaced by SchedulePanel (components/schedule/schedule-panel.tsx)
// and SnipeConfigSheet (components/schedule/snipe-config-sheet.tsx) in Phase 4.
// Kept for reference. Safe to delete after Phase 4 verification.
'use client';

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { ChevronLeft, ChevronRight, CalendarIcon, Loader2, SkipForward, Crosshair } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Calendar, CalendarDayButton } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { STUDIOS, STUDIO_LOCATIONS, SEAT_PREFERENCES, SPOT_PREFERENCES } from '@/lib/studios';

interface ScheduleClass {
  class_date: string;
  class_time: string;
  class_name: string | null;
  instructor: string | null;
  duration_minutes: number | null;
  available: boolean;
  spots_remaining: number | null;
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

function formatDisplayDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function parseDateStr(str: string): Date {
  const [y, m, d] = str.split('-').map(Number);
  return new Date(y, m - 1, d);
}

/** Parse "7:00 AM" or "13:30" into minutes since midnight for sorting */
function parseTimeToMinutes(time: string): number {
  const match12 = time.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
  if (match12) {
    let hours = parseInt(match12[1]);
    const minutes = parseInt(match12[2]);
    const period = match12[3].toUpperCase();
    if (period === 'PM' && hours !== 12) hours += 12;
    if (period === 'AM' && hours === 12) hours = 0;
    return hours * 60 + minutes;
  }
  const match24 = time.match(/(\d{1,2}):(\d{2})/);
  if (match24) {
    return parseInt(match24[1]) * 60 + parseInt(match24[2]);
  }
  return 0;
}

type ClassStatus = 'available' | 'full' | 'not_open';

function getClassStatus(cls: ScheduleClass, studioSlug: string): ClassStatus {
  const windowDays = STUDIOS[studioSlug]?.bookingWindowDays ?? 7;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const cutoff = new Date(today);
  cutoff.setDate(cutoff.getDate() + windowDays);
  const classDate = new Date(cls.class_date.split('T')[0] + 'T00:00:00');
  if (classDate > cutoff) return 'not_open';
  return cls.available ? 'available' : 'full';
}

// Context to pass availability data into the custom DayButton without re-mounting
const AvailabilityContext = createContext<Map<string, { total: number; available: number }>>(new Map());

/** Custom DayButton that shows heatmap colors based on availability */
function AvailabilityDayButton(props: React.ComponentProps<typeof CalendarDayButton>) {
  const monthAvail = useContext(AvailabilityContext);
  const dateStr = formatDateToStr(props.day.date);
  const avail = monthAvail.get(dateStr);
  const isSelected = props.modifiers.selected;

  const style: React.CSSProperties | undefined =
    avail && !isSelected
      ? avail.available > 0
        ? { backgroundColor: 'rgba(16, 185, 129, 0.3)', color: 'rgb(110, 231, 183)' }
        : { backgroundColor: 'rgba(239, 68, 68, 0.2)', color: 'rgb(248, 113, 113)' }
      : undefined;

  return <CalendarDayButton {...props} style={style} />;
}

export function ScheduleExplorer() {
  const [studioSlug, setStudioSlug] = useState('');
  const [locationId, setLocationId] = useState('');
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [scheduleData, setScheduleData] = useState<ScheduleResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [calendarOpen, setCalendarOpen] = useState(false);

  // Calendar heatmap state
  const [calendarMonth, setCalendarMonth] = useState<Date>(new Date());
  const [monthAvailability, setMonthAvailability] = useState<Map<string, { total: number; available: number }>>(new Map());

  // Next available state
  const [nextAvailLoading, setNextAvailLoading] = useState(false);

  // Snipe state
  const [snipingClassKey, setSnipingClassKey] = useState<string | null>(null);
  const [snipeLoading, setSnipeLoading] = useState(false);
  const [seatPref, setSeatPref] = useState('any');

  const locations = studioSlug ? STUDIO_LOCATIONS[studioSlug] || [] : [];
  const isLive = scheduleData?.source === 'scraped' || scheduleData?.source === 'live_api';

  // Sync calendarMonth when selectedDate changes month
  useEffect(() => {
    setCalendarMonth(new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1));
  }, [selectedDate]);

  // Fetch schedule for the selected day
  useEffect(() => {
    if (!studioSlug) {
      setScheduleData(null);
      return;
    }

    const controller = new AbortController();
    const params = new URLSearchParams({
      studio: studioSlug,
      date: formatDateToStr(selectedDate),
    });
    if (locationId) params.set('location', locationId);

    setLoading(true);
    fetch(`/api/schedules?${params}`, { signal: controller.signal })
      .then(async (res) => {
        if (res.ok) {
          setScheduleData(await res.json());
        } else {
          setScheduleData(null);
        }
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setScheduleData(null);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [studioSlug, locationId, selectedDate]);

  // Fetch month availability for calendar heatmap (pre-loads so data is ready when calendar opens)
  useEffect(() => {
    if (!studioSlug || !locationId) {
      setMonthAvailability(new Map());
      return;
    }

    const start = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1);
    const end = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 0);

    const params = new URLSearchParams({
      studio: studioSlug,
      date: formatDateToStr(start),
      dateTo: formatDateToStr(end),
    });
    if (locationId) params.set('location', locationId);

    const controller = new AbortController();

    fetch(`/api/schedules?${params}`, { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : null))
      .then((data: ScheduleResponse | null) => {
        if (!data) return;
        const map = new Map<string, { total: number; available: number }>();
        for (const cls of data.classes) {
          // Normalize ISO "2026-02-19T05:00:00.000Z" → "2026-02-19"
          const dateKey = cls.class_date.split('T')[0];
          const existing = map.get(dateKey) || { total: 0, available: 0 };
          existing.total++;
          if (cls.available) existing.available++;
          map.set(dateKey, existing);
        }
        setMonthAvailability(map);
      })
      .catch(() => {});

    return () => controller.abort();
  }, [studioSlug, locationId, calendarMonth]);

  // Next available handler
  const handleNextAvailable = useCallback(async () => {
    if (!studioSlug) return;
    setNextAvailLoading(true);

    try {
      const startDate = new Date(selectedDate);
      startDate.setDate(startDate.getDate() + 1);
      const endDate = new Date(startDate);
      endDate.setDate(endDate.getDate() + 13);

      const params = new URLSearchParams({
        studio: studioSlug,
        date: formatDateToStr(startDate),
        dateTo: formatDateToStr(endDate),
      });
      if (locationId) params.set('location', locationId);

      const res = await fetch(`/api/schedules?${params}`);
      if (!res.ok) {
        toast.error('Failed to search for availability');
        return;
      }

      const data: ScheduleResponse = await res.json();

      const datesWithAvail = new Set<string>();
      for (const cls of data.classes) {
        if (cls.available) datesWithAvail.add(cls.class_date.split('T')[0]);
      }

      const sorted = [...datesWithAvail].sort();
      if (sorted.length > 0) {
        setSelectedDate(parseDateStr(sorted[0]));
      } else {
        toast('No availability found in the next 14 days');
      }
    } finally {
      setNextAvailLoading(false);
    }
  }, [studioSlug, locationId, selectedDate]);

  function goDay(offset: number) {
    setSelectedDate((prev) => {
      const next = new Date(prev);
      next.setDate(next.getDate() + offset);
      return next;
    });
  }

  async function handleSnipe(cls: ScheduleClass) {
    setSnipeLoading(true);
    try {
      const classDate = cls.class_date.split('T')[0];
      const res = await fetch('/api/targets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_type: 'one_time',
          studio_slug: studioSlug,
          location_id: locationId,
          target_date: classDate,
          time: cls.class_time,
          class_type: cls.class_name,
          seat_preference: seatPref,
          preferred_spots: SPOT_PREFERENCES[seatPref] || [],
        }),
      });
      const data = await res.json();
      if (res.ok) {
        toast.success(`Snipe target created for ${cls.class_name || 'class'} at ${cls.class_time}`);
        setSnipingClassKey(null);
        setSeatPref('any');
      } else {
        toast.error(data.error || 'Failed to create snipe target');
      }
    } catch {
      toast.error('Network error — try again');
    } finally {
      setSnipeLoading(false);
    }
  }

  // Sort classes by time
  const classes = [...(scheduleData?.classes ?? [])].sort(
    (a, b) => parseTimeToMinutes(a.class_time) - parseTimeToMinutes(b.class_time),
  );

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        {/* Studio */}
        <div className="w-full space-y-1.5 sm:w-56">
          <label className="text-xs font-medium text-zinc-400">Studio</label>
          <Select
            value={studioSlug}
            onValueChange={(v) => {
              setStudioSlug(v);
              setLocationId('');
              setScheduleData(null);
              setMonthAvailability(new Map());
            }}
          >
            <SelectTrigger className="border-white/10 bg-white/5">
              <SelectValue placeholder="Select studio" />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(STUDIOS).map(([slug, info]) => (
                <SelectItem key={slug} value={slug}>
                  {info.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Location dropdown or text input */}
        <div className="w-full space-y-1.5 sm:w-56">
          <label className="text-xs font-medium text-zinc-400">Location</label>
          {locations.length > 0 ? (
            <Select value={locationId} onValueChange={setLocationId}>
              <SelectTrigger className="border-white/10 bg-white/5">
                <SelectValue placeholder="Select location" />
              </SelectTrigger>
              <SelectContent>
                {locations.map((loc) => (
                  <SelectItem key={loc.id} value={loc.id}>
                    {loc.name}
                    {loc.address && ` — ${loc.address}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              value={locationId}
              onChange={(e) => setLocationId(e.target.value)}
              placeholder={
                studioSlug && STUDIOS[studioSlug]?.platform === 'xponential'
                  ? `e.g. ${STUDIOS[studioSlug]?.slug}-downtown`
                  : 'Location ID'
              }
              className="border-white/10 bg-white/5"
            />
          )}
        </div>
      </div>

      {/* Date navigation */}
      {studioSlug && (
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => goDay(-1)}
            className="h-8 w-8 text-zinc-400 hover:text-white"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className="min-w-[220px] border-white/10 bg-white/5 font-medium hover:bg-zinc-800"
              >
                <CalendarIcon className="mr-2 h-4 w-4 text-zinc-400" />
                {formatDisplayDate(selectedDate)}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto border-zinc-700 bg-zinc-950 p-0" align="center">
              <AvailabilityContext.Provider value={monthAvailability}>
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={(d) => {
                    if (d) {
                      setSelectedDate(d);
                      setCalendarOpen(false);
                    }
                  }}
                  month={calendarMonth}
                  onMonthChange={setCalendarMonth}
                  components={{ DayButton: AvailabilityDayButton }}
                />
              </AvailabilityContext.Provider>
              {/* Heatmap legend */}
              <div className="flex items-center justify-center gap-4 border-t border-zinc-800 px-3 py-2 text-[10px] text-zinc-500">
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
                  Available
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
                  Full
                </span>
              </div>
            </PopoverContent>
          </Popover>

          <Button
            variant="ghost"
            size="icon"
            onClick={() => goDay(1)}
            className="h-8 w-8 text-zinc-400 hover:text-white"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>

          {/* Next Available button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleNextAvailable}
            disabled={nextAvailLoading}
            className="border-white/10 bg-white/5 text-xs text-zinc-300 hover:bg-zinc-800 hover:text-white"
          >
            {nextAvailLoading ? (
              <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
            ) : (
              <SkipForward className="mr-1.5 h-3 w-3" />
            )}
            Next Available
          </Button>

          {loading && <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />}
          {isLive && !loading && (
            <span className="rounded bg-emerald-900/50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400">
              {scheduleData?.source === 'live_api' ? 'Live' : 'Scraped'}
            </span>
          )}
        </div>
      )}

      {/* Class list */}
      {!studioSlug && (
        <div className="rounded-lg border border-white/5 bg-white/[0.02] px-6 py-12 text-center text-sm text-zinc-500">
          Select a studio to browse schedules
        </div>
      )}

      {studioSlug && loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
        </div>
      )}

      {studioSlug && !loading && classes.length === 0 && scheduleData && (
        <div className="rounded-lg border border-white/5 bg-white/[0.02] px-6 py-12 text-center text-sm text-zinc-500">
          No classes found for this date
        </div>
      )}

      {studioSlug && !loading && classes.length > 0 && (
        <div className="space-y-2">
          {classes.map((cls, i) => {
            const status = getClassStatus(cls, studioSlug);
            const classKey = `${cls.class_time}-${cls.class_name}-${i}`;
            const canSnipe = status === 'available' || status === 'not_open';

            return (
              <div
                key={classKey}
                className="flex items-start gap-4 rounded-lg border border-white/5 bg-white/[0.02] px-4 py-3"
              >
                {/* Time */}
                <div className="w-20 shrink-0 pt-0.5 text-sm font-semibold text-white">
                  {cls.class_time}
                </div>

                {/* Details */}
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-white">
                    {cls.class_name || 'Class'}
                    {cls.instructor && (
                      <span className="font-normal text-zinc-400"> — {cls.instructor}</span>
                    )}
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 text-xs text-zinc-500">
                    {cls.duration_minutes && <span>{cls.duration_minutes} min</span>}
                  </div>
                </div>

                {/* Availability badge */}
                <div className="shrink-0">
                  {status === 'available' ? (
                    <Badge className="border-emerald-800 bg-emerald-950 text-emerald-400">
                      {cls.spots_remaining != null
                        ? `${cls.spots_remaining} spot${cls.spots_remaining !== 1 ? 's' : ''}`
                        : 'Open'}
                    </Badge>
                  ) : status === 'not_open' ? (
                    <Badge className="border-amber-800 bg-amber-950 text-amber-400">
                      Not Open
                    </Badge>
                  ) : (
                    <Badge className="border-red-800 bg-red-950 text-red-400">Full</Badge>
                  )}
                </div>

                {/* Snipe button */}
                {canSnipe && (
                  <Popover
                    open={snipingClassKey === classKey}
                    onOpenChange={(open) => {
                      setSnipingClassKey(open ? classKey : null);
                      if (!open) setSeatPref('any');
                    }}
                  >
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 shrink-0 border-emerald-700 bg-emerald-950/50 px-2.5 text-xs text-emerald-400 hover:bg-emerald-900/50 hover:text-emerald-300"
                      >
                        <Crosshair className="mr-1 h-3 w-3" />
                        Snipe
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent
                      className="w-64 border-zinc-700 bg-zinc-950 p-4"
                      align="end"
                    >
                      <div className="space-y-3">
                        <p className="text-xs text-zinc-400">
                          Create a one-time snipe for{' '}
                          <span className="font-medium text-white">
                            {cls.class_name || 'class'}
                          </span>{' '}
                          at {cls.class_time} on {cls.class_date.split('T')[0]}
                        </p>

                        <div className="space-y-1.5">
                          <label className="text-xs font-medium text-zinc-400">
                            Seat Preference
                          </label>
                          <Select value={seatPref} onValueChange={setSeatPref}>
                            <SelectTrigger className="h-8 border-white/10 bg-white/5 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {SEAT_PREFERENCES.map((s) => (
                                <SelectItem key={s.value} value={s.value}>
                                  {s.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <Button
                          size="sm"
                          className="w-full bg-emerald-600 text-white hover:bg-emerald-500"
                          disabled={snipeLoading}
                          onClick={() => handleSnipe(cls)}
                        >
                          {snipeLoading ? (
                            <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                          ) : (
                            <Crosshair className="mr-1.5 h-3 w-3" />
                          )}
                          Confirm Snipe
                        </Button>
                      </div>
                    </PopoverContent>
                  </Popover>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
