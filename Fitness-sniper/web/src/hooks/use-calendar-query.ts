import { useQuery } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/query-keys';
import type { CalendarEvent } from '@/lib/types';

export function useCalendarQuery(weekStart: string) {
  return useQuery<CalendarEvent[]>({
    queryKey: QUERY_KEYS.calendarWeek(weekStart),
    queryFn: async () => {
      const res = await fetch(`/api/calendar?weekStart=${weekStart}`);
      if (!res.ok) {
        throw new Error(`Calendar fetch failed: ${res.status}`);
      }
      return res.json();
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
    placeholderData: [],
  });
}
