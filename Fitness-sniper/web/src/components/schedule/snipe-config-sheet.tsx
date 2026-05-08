'use client';

import { useState } from 'react';
import { Loader2, Crosshair } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { STUDIOS, SEAT_PREFERENCES, SPOT_PREFERENCES } from '@/lib/studios';
import { useSnipeMutation } from '@/hooks/use-snipe-mutation';
import type { ScheduleClass } from '@/components/schedule/schedule-panel';
import { cn } from '@/lib/utils';

interface SnipeConfigSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedClass: ScheduleClass | null;
  studioSlug: string;
  locationId: string;
}

export function SnipeConfigSheet({
  open,
  onOpenChange,
  selectedClass,
  studioSlug,
  locationId,
}: SnipeConfigSheetProps) {
  const [targetType, setTargetType] = useState<'one_time' | 'recurring'>('one_time');
  const [seatPref, setSeatPref] = useState('any');

  const { mutate, isPending } = useSnipeMutation(() => onOpenChange(false));

  if (!selectedClass) return null;

  // Derived values from selectedClass
  const classDate = selectedClass.class_date.split('T')[0];
  const [y, m, d] = classDate.split('-').map(Number);
  const dayOfWeek = new Date(y, m - 1, d).getDay();
  const dayName = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][dayOfWeek];
  const studioName = STUDIOS[studioSlug]?.name ?? studioSlug;

  function handleConfirm() {
    if (!selectedClass) return;
    mutate({
      target_type: targetType,
      studio_slug: studioSlug,
      location_id: locationId,
      time: selectedClass.class_time,
      class_type: selectedClass.class_name,
      seat_preference: seatPref,
      preferred_spots: SPOT_PREFERENCES[seatPref] || [],
      ...(targetType === 'one_time'
        ? { target_date: classDate }
        : { day_of_week: dayOfWeek }),
    });
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Create Snipe Target</SheetTitle>
          <SheetDescription>
            {selectedClass.class_name || 'Class'} at {selectedClass.class_time}
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-6 p-6">
          {/* Studio & class info (read-only summary) */}
          <div className="rounded-lg border border-white/5 bg-white/[0.02] p-4">
            <div className="text-sm font-medium text-white">{studioName}</div>
            <div className="mt-1 text-xs text-zinc-400">
              {selectedClass.class_name || 'Class'} — {selectedClass.class_time}
            </div>
            {selectedClass.instructor && (
              <div className="mt-0.5 text-xs text-zinc-500">
                with {selectedClass.instructor}
              </div>
            )}
            <div className="mt-0.5 text-xs text-zinc-500">{classDate}</div>
          </div>

          {/* Target type toggle */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-400">Snipe Type</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setTargetType('one_time')}
                className={cn(
                  'flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
                  targetType === 'one_time'
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                    : 'border-white/10 text-zinc-400 hover:bg-white/5'
                )}
              >
                One-time
                <span className="mt-0.5 block text-[10px] font-normal opacity-70">
                  Just {classDate}
                </span>
              </button>
              <button
                type="button"
                onClick={() => setTargetType('recurring')}
                className={cn(
                  'flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
                  targetType === 'recurring'
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                    : 'border-white/10 text-zinc-400 hover:bg-white/5'
                )}
              >
                Recurring
                <span className="mt-0.5 block text-[10px] font-normal opacity-70">
                  Every {dayName}
                </span>
              </button>
            </div>
          </div>

          {/* Seat preference */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-400">Seat Preference</label>
            <Select value={seatPref} onValueChange={setSeatPref}>
              <SelectTrigger className="border-white/10 bg-white/5">
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

          {/* Confirm button */}
          <Button
            onClick={handleConfirm}
            disabled={isPending}
            className="w-full bg-emerald-600 text-white hover:bg-emerald-500"
          >
            {isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Crosshair className="mr-2 h-4 w-4" />
            )}
            {isPending ? 'Creating...' : 'Confirm Snipe'}
          </Button>

          {/* Recurring explainer */}
          {targetType === 'recurring' && (
            <p className="text-[11px] leading-relaxed text-zinc-500">
              This will attempt to book {selectedClass.class_name || 'this class'} every{' '}
              {dayName} at {selectedClass.class_time}. The system will automatically
              create booking jobs each week.
            </p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
