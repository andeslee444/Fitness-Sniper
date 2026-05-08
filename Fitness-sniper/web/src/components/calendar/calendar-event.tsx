import { STUDIOS } from '@/lib/studios';
import { cn } from '@/lib/utils';
import type { CalendarEvent, CalendarEventType } from '@/lib/types';

const EVENT_STYLES: Record<CalendarEventType, string> = {
  booked: 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300',
  pending: 'border border-dashed border-yellow-500/50 text-yellow-400 animate-pulse',
  failed: 'bg-red-500/15 border border-red-500/30 text-red-400',
  configured: 'border border-dashed border-zinc-700 text-zinc-500',
};

interface CalendarEventPillProps {
  event: CalendarEvent;
}

export function CalendarEventPill({ event }: CalendarEventPillProps) {
  const studioName = STUDIOS[event.studio_slug]?.name ?? event.studio_slug;
  const styles = EVENT_STYLES[event.event_type];

  return (
    <div className={cn('rounded px-1.5 py-0.5 text-xs leading-tight', styles)}>
      <span className="truncate block">{studioName}</span>
      {event.event_time !== null && (
        <span className="opacity-75">{event.event_time}</span>
      )}
    </div>
  );
}
