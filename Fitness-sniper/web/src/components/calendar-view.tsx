'use client';

import { useState } from 'react';
import { startOfWeek, addWeeks, subWeeks, addDays, format } from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WeekGrid } from './calendar/week-grid';
import { Skeleton } from './skeleton';
import { useCalendarQuery } from '@/hooks/use-calendar-query';

function getInitialWeekStart(): string {
  // Get today in ET to avoid UTC-midnight boundary issues
  const todayET = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  const [y, m, d] = todayET.split('-').map(Number);
  const todayLocal = new Date(y, m - 1, d);
  // weekStartsOn: 1 = Monday (not default Sunday)
  const monday = startOfWeek(todayLocal, { weekStartsOn: 1 });
  return format(monday, 'yyyy-MM-dd');
}

export function CalendarView() {
  const [weekStart, setWeekStart] = useState(getInitialWeekStart);
  const { data: events = [], isLoading } = useCalendarQuery(weekStart);

  // Parse weekStart safely to avoid UTC-midnight interpretation
  const [wy, wm, wd] = weekStart.split('-').map(Number);
  const weekStartDate = new Date(wy, wm - 1, wd);

  // Generate 7 days (Mon–Sun)
  const days = Array.from({ length: 7 }, (_, i) =>
    format(addDays(weekStartDate, i), 'yyyy-MM-dd')
  );

  const weekLabel =
    format(weekStartDate, 'MMM d') +
    ' \u2013 ' +
    format(addDays(weekStartDate, 6), 'MMM d, yyyy');

  function goToPrevWeek() {
    setWeekStart(format(subWeeks(weekStartDate, 1), 'yyyy-MM-dd'));
  }

  function goToNextWeek() {
    setWeekStart(format(addWeeks(weekStartDate, 1), 'yyyy-MM-dd'));
  }

  function goToToday() {
    setWeekStart(getInitialWeekStart());
  }

  return (
    <div className="space-y-4">
      {/* Week navigation header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">{weekLabel}</h2>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={goToPrevWeek} className="h-8 w-8">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={goToToday} className="h-8 px-3 text-xs">
            Today
          </Button>
          <Button variant="ghost" size="icon" onClick={goToNextWeek} className="h-8 w-8">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Calendar grid */}
      {isLoading ? (
        <Skeleton className="h-48 w-full rounded-xl" />
      ) : (
        <WeekGrid days={days} events={events} />
      )}
    </div>
  );
}
