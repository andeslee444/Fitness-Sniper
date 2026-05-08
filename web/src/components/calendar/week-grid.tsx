import { DayColumn } from './day-column';
import type { CalendarEvent } from '@/lib/types';

interface WeekGridProps {
  days: string[]; // 7 'YYYY-MM-DD' strings
  events: CalendarEvent[];
}

export function WeekGrid({ days, events }: WeekGridProps) {
  return (
    <div className="overflow-x-auto">
      <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border border-white/5 bg-white/5 min-w-[560px]">
        {days.map((date) => (
          <DayColumn
            key={date}
            date={date}
            events={events.filter((e) => e.event_date === date)}
          />
        ))}
      </div>
    </div>
  );
}
