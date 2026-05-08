import { CalendarEventPill } from './calendar-event';
import { cn } from '@/lib/utils';
import type { CalendarEvent, CalendarEventType } from '@/lib/types';

const PRIORITY: Record<CalendarEventType, number> = {
  booked: 0,
  failed: 1,
  pending: 2,
  configured: 3,
};

function deduplicateEvents(events: CalendarEvent[]): CalendarEvent[] {
  const map = new Map<string, CalendarEvent>();

  for (const event of events) {
    const key = `${event.studio_slug}|${event.event_time ?? 'anytime'}`;
    const existing = map.get(key);
    if (!existing || PRIORITY[event.event_type] < PRIORITY[existing.event_type]) {
      map.set(key, event);
    }
  }

  return Array.from(map.values()).sort((a, b) => {
    if (a.event_time === null && b.event_time === null) return 0;
    if (a.event_time === null) return 1;
    if (b.event_time === null) return -1;
    return a.event_time.localeCompare(b.event_time);
  });
}

function heatmapClass(count: number): string {
  if (count === 0) return '';
  if (count <= 2) return 'bg-emerald-500/5';
  return 'bg-emerald-500/10';
}

interface DayColumnProps {
  date: string; // 'YYYY-MM-DD'
  events: CalendarEvent[];
}

export function DayColumn({ date, events }: DayColumnProps) {
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  const isToday = date === today;

  // Safe date parsing — avoid new Date(string) which parses as UTC
  const [year, month, day] = date.split('-').map(Number);
  const dateObj = new Date(year, month - 1, day);

  const weekdayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
  const dayNumber = dateObj.getDate();

  const dedupedEvents = deduplicateEvents(events);

  return (
    <div
      className={cn(
        'flex flex-col gap-1 p-1.5 min-h-24',
        heatmapClass(dedupedEvents.length),
      )}
    >
      <div className="flex flex-col items-center mb-1">
        <span
          className={cn(
            'text-xs font-medium uppercase tracking-wide',
            isToday ? 'text-emerald-400' : 'text-zinc-400',
          )}
        >
          {weekdayName}
        </span>
        <span
          className={cn(
            'text-sm font-semibold',
            isToday ? 'text-emerald-300' : 'text-zinc-200',
          )}
        >
          {dayNumber}
        </span>
      </div>

      <div className="flex flex-col gap-0.5">
        {dedupedEvents.map((event) => (
          <CalendarEventPill key={event.id} event={event} />
        ))}
      </div>
    </div>
  );
}
