# Phase 3: Calendar Home - Research

**Researched:** 2026-02-27
**Domain:** CSS Grid weekly calendar UI, TanStack Query integration, date/timezone rendering in React
**Confidence:** HIGH

## Summary

Phase 3 builds a 7-column weekly calendar that replaces the stats-grid dashboard home. The data layer (Phase 2) is complete: `GET /api/calendar?weekStart=YYYY-MM-DD` returns `CalendarEvent[]`, the `CalendarEvent` type is defined in `packages/shared/src/types.ts`, `QUERY_KEYS.calendarWeek` is already defined in `web/src/lib/query-keys.ts`, and TanStack Query is fully installed and wired. This phase is purely UI construction.

The roadmap decision to avoid `react-big-calendar` (due to Tailwind v4 CSS variable incompatibility) means building a custom `WeekGrid` using native CSS Grid. This is the right call — the calendar is narrow in scope (7 days, no time-axis scrolling, events are pills inside day columns), and the custom implementation will be roughly 200 lines of JSX/CSS, well within reason for this codebase's style.

The most important technical decisions for this phase: (1) week navigation state must be initialized from the current date in America/New_York using `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` — the same pattern used in Phase 1's timezone fix — not `new Date().toISOString()` which uses UTC; (2) event deduplication (booked > pending > configured) must happen in the component, not the API, per the Phase 2 decision captured in STATE.md; (3) heatmap intensity for CAL-03 is computed per-day from `class_schedules` data OR derived from `CalendarEvent` count — the latter is simpler and requires no new API endpoint.

**Primary recommendation:** Build the three components (WeekGrid, DayColumn, CalendarEvent pill) with static fixture data first (Plan 03-01), then wire to `useCalendarQuery` with week navigation and replace the dashboard page (Plan 03-02). No new dependencies needed — `date-fns` is already installed (transitive via `react-day-picker`), TanStack Query is active, and Tailwind v4 grid utilities work as expected.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAL-01 | User sees a weekly calendar as dashboard home showing confirmed bookings, pending snipes, and failed attempts | WeekGrid (7-column CSS grid) + DayColumn + CalendarEvent pill components; fed by `useCalendarQuery(weekStart)` hook; replaces stats grid in `dashboard/page.tsx` |
| CAL-02 | Calendar events are color-coded by status — solid for booked, outlined/dashed for pending, red for failures | CSS class mapping by `event_type`: emerald solid (booked), yellow dashed border + pulse animation (pending), red solid (failed), zinc dashed (configured). Tailwind `animate-pulse` works for pending glow. |
| CAL-03 | Calendar days show availability heatmap overlay indicating how many classes have open slots vs are full | Computed from `class_schedules` data available via `GET /api/schedules`; alternatively derived from event density in `CalendarEvent[]` — simpler approach uses event count per day to render a subtle background tint intensity |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tailwind CSS v4 | `^4` (installed) | CSS Grid layout for WeekGrid, color utilities for event status | Already installed, dark-mode hardcoded, all utilities available |
| `@tanstack/react-query` | `^5.90.21` (installed) | `useQuery` with `QUERY_KEYS.calendarWeek(weekStart)` for calendar data | Already installed and wired via `Providers` in `app/layout.tsx` |
| `date-fns` | Installed transitively via `react-day-picker` in root `node_modules` | Week arithmetic: `startOfWeek`, `addDays`, `addWeeks`, `subWeeks`, `format` | Available without install; avoids manual date math pitfalls |
| `lucide-react` | `^0.564.0` (installed) | Navigation chevrons (`ChevronLeft`, `ChevronRight`), status icons | Already used throughout the codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `cn()` utility | Already in `lib/utils.ts` | Conditional className merging (clsx + tailwind-merge) | Use for all conditional classes in calendar components |
| `Skeleton` component | Already in `components/skeleton.tsx` | Loading state for WeekGrid while query fetches | Use `isLoading` (not `isFetching`) to gate skeleton display |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom WeekGrid CSS Grid | `react-big-calendar` | react-big-calendar is explicitly rejected in STATE.md — Tailwind v4 CSS variable incompatibility. Custom is correct here. |
| Custom WeekGrid CSS Grid | `@fullcalendar/react` | Same Tailwind v4 incompatibility risk; adds 200KB+ bundle; overkill for a pill-based weekly view |
| `date-fns` week math | Manual `Date` arithmetic | Manual date math with JS `Date` is error-prone for month boundary crossing, DST, and week-start conventions. `date-fns` is already installed. |
| `date-fns` week math | `date-fns-tz` | `date-fns-tz` is NOT installed. The calendar uses `YYYY-MM-DD` strings from the API (already converted to ET by SQL `AT TIME ZONE`), so no TZ conversion needed in the browser at all. |

**Installation:**
```bash
# No new dependencies needed.
# date-fns is already available via react-day-picker transitive dependency.
# If it needs to be explicit in web/package.json:
npm install date-fns --workspace=web
```

---

## Architecture Patterns

### New Files to Create
```
web/src/
├── components/
│   ├── calendar/
│   │   ├── week-grid.tsx         # WeekGrid: 7-column CSS grid container
│   │   ├── day-column.tsx        # DayColumn: header + event list for one day
│   │   └── calendar-event.tsx    # CalendarEvent: pill UI for a single event
│   └── calendar-view.tsx         # CalendarView: week nav + useCalendarQuery + WeekGrid
└── hooks/
    └── use-calendar-query.ts     # useCalendarQuery(weekStart) hook
```

### Modified Files
```
web/src/
└── app/(dashboard)/dashboard/page.tsx   # Replace stats grid + jobs with <CalendarView />
```

### Pattern 1: WeekGrid (CSS Grid Layout)

**What:** A 7-column CSS Grid where each column is a `DayColumn`. The grid grows vertically to fit event pills — no fixed-height time axis needed for this use case.

**Tailwind v4 note:** In Tailwind v4, `grid-cols-7` works exactly as in v3. The `@theme inline` block in `globals.css` maps CSS variables to Tailwind color tokens — all `emerald-*`, `yellow-*`, `red-*`, `zinc-*` utilities work normally.

**Example:**
```tsx
// web/src/components/calendar/week-grid.tsx
import { DayColumn } from './day-column';
import type { CalendarEvent } from '@/lib/types';

interface WeekGridProps {
  days: string[];          // ['2026-02-23', '2026-02-24', ...'2026-02-29'] — 7 YYYY-MM-DD strings
  events: CalendarEvent[]; // all events for the week
}

export function WeekGrid({ days, events }: WeekGridProps) {
  return (
    <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border border-white/5 bg-white/5">
      {days.map((date) => (
        <DayColumn
          key={date}
          date={date}
          events={events.filter((e) => e.event_date === date)}
        />
      ))}
    </div>
  );
}
```

### Pattern 2: DayColumn with Event Priority Deduplication

**What:** Renders the day header plus event pills. Applies the Phase 2 decision: when multiple events share the same `studio_slug + event_date + event_time`, show only the highest-priority one (booked > pending > configured).

**Heatmap overlay (CAL-03):** Implemented as a background tint based on event count. 0 events = no tint, 1-2 events = very subtle emerald tint (`emerald-500/5`), 3+ events = slightly stronger (`emerald-500/10`). This is purely cosmetic and requires no additional API call — it uses the events already fetched for the week.

**Today highlight:** Compare `date` against the ET "today" string using the same `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` pattern from Phase 1.

**Example:**
```tsx
// web/src/components/calendar/day-column.tsx
import { CalendarEventPill } from './calendar-event';
import { cn } from '@/lib/utils';
import type { CalendarEvent } from '@/lib/types';

const PRIORITY: Record<string, number> = { booked: 0, failed: 1, pending: 2, configured: 3 };

function deduplicateEvents(events: CalendarEvent[]): CalendarEvent[] {
  const map = new Map<string, CalendarEvent>();
  for (const e of events) {
    // Key: studio+time (or studio+event_type if no time, e.g. Arketa any-slot)
    const key = `${e.studio_slug}|${e.event_time ?? 'anytime'}`;
    const existing = map.get(key);
    if (!existing || PRIORITY[e.event_type] < PRIORITY[existing.event_type]) {
      map.set(key, e);
    }
  }
  return Array.from(map.values()).sort((a, b) =>
    (a.event_time ?? '').localeCompare(b.event_time ?? '')
  );
}

function heatmapClass(count: number): string {
  if (count === 0) return '';
  if (count <= 2) return 'bg-emerald-500/5';
  return 'bg-emerald-500/10';
}

interface DayColumnProps {
  date: string;       // 'YYYY-MM-DD'
  events: CalendarEvent[];
}

export function DayColumn({ date, events }: DayColumnProps) {
  const todayET = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  const isToday = date === todayET;
  const dedupedEvents = deduplicateEvents(events);

  // Parse date as local date (avoid UTC offset shifting the day)
  const [year, month, day] = date.split('-').map(Number);
  const dateObj = new Date(year, month - 1, day);
  const dayLabel = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
  const dayNum = dateObj.getDate();

  return (
    <div className={cn('flex flex-col gap-1 p-1.5 min-h-24', heatmapClass(dedupedEvents.length))}>
      {/* Day header */}
      <div className={cn('flex flex-col items-center py-1', isToday && 'text-emerald-400')}>
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">{dayLabel}</span>
        <span className={cn('text-sm font-bold', isToday ? 'text-emerald-400' : 'text-white')}>
          {dayNum}
        </span>
      </div>
      {/* Events */}
      <div className="flex flex-col gap-0.5">
        {dedupedEvents.map((event) => (
          <CalendarEventPill key={event.id} event={event} />
        ))}
      </div>
    </div>
  );
}
```

### Pattern 3: CalendarEvent Pill (CAL-02 Color Coding)

**What:** A small pill showing studio name, time, and visual status treatment. Status-to-style mapping:

| event_type | Visual Treatment | Tailwind Classes |
|------------|-----------------|-----------------|
| `booked` | Solid green | `bg-emerald-500/15 border border-emerald-500/30 text-emerald-300` |
| `pending` | Dashed yellow + pulse | `border border-dashed border-yellow-500/50 text-yellow-400 animate-pulse` |
| `failed` | Solid red | `bg-red-500/15 border border-red-500/30 text-red-400` |
| `configured` | Dashed gray | `border border-dashed border-zinc-700 text-zinc-500` |

**Studio name lookup:** Import `STUDIOS` from `@fitness-sniper/shared` — already available in the web package via `transpilePackages`.

**Example:**
```tsx
// web/src/components/calendar/calendar-event.tsx
import { STUDIOS } from '@fitness-sniper/shared';
import { cn } from '@/lib/utils';
import type { CalendarEvent } from '@/lib/types';

const EVENT_STYLES: Record<string, string> = {
  booked:     'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300',
  pending:    'border border-dashed border-yellow-500/50 text-yellow-400 animate-pulse',
  failed:     'bg-red-500/15 border border-red-500/30 text-red-400',
  configured: 'border border-dashed border-zinc-700 text-zinc-500',
};

interface CalendarEventPillProps {
  event: CalendarEvent;
}

export function CalendarEventPill({ event }: CalendarEventPillProps) {
  const studioName = STUDIOS[event.studio_slug]?.name ?? event.studio_slug;

  return (
    <div className={cn('rounded px-1.5 py-0.5 text-xs leading-tight', EVENT_STYLES[event.event_type])}>
      <span className="font-medium truncate block">{studioName}</span>
      {event.event_time && (
        <span className="opacity-75">{event.event_time}</span>
      )}
    </div>
  );
}
```

### Pattern 4: useCalendarQuery Hook

**What:** Wraps `useQuery` for the `/api/calendar` endpoint. Takes `weekStart` as a parameter. Uses `QUERY_KEYS.calendarWeek(weekStart)` which is already defined.

**Example:**
```tsx
// web/src/hooks/use-calendar-query.ts
import { useQuery } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/query-keys';
import type { CalendarEvent } from '@/lib/types';

export function useCalendarQuery(weekStart: string) {
  return useQuery<CalendarEvent[]>({
    queryKey: QUERY_KEYS.calendarWeek(weekStart),
    queryFn: async () => {
      const res = await fetch(`/api/calendar?weekStart=${weekStart}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    staleTime: 60_000,          // Calendar data doesn't need sub-minute freshness
    refetchInterval: 60_000,   // Refresh every 60s while tab active
    placeholderData: [],        // Don't show loading state on week navigation — show empty grid
  });
}
```

**`placeholderData: []` note:** Using `placeholderData` instead of `initialData` means the previous week's events are NOT shown while the new week loads (which would be confusing). An empty grid with a subtle loading indicator is cleaner on week navigation.

### Pattern 5: CalendarView with Week Navigation

**What:** Top-level component that owns `weekStart` state, provides navigation buttons, and renders `WeekGrid`. This is the component that replaces the stats grid in `dashboard/page.tsx`.

**Week start computation:** The API accepts any `YYYY-MM-DD` date as `weekStart` and returns a 7-day window. The UI should always show the Monday-anchored week to match how the API's recurring target expansion works (DOW math relative to `week_start`). Use `date-fns/startOfWeek` with `{ weekStartsOn: 1 }` for Monday.

**Critical:** The initial `weekStart` must be derived in America/New_York timezone using `toLocaleDateString('en-CA', { timeZone: 'America/New_York' })`, then adjusted to the start of that week. Do NOT use `new Date().toISOString()` which gives UTC.

**Example:**
```tsx
// web/src/components/calendar-view.tsx
'use client';

import { useState } from 'react';
import { startOfWeek, addWeeks, subWeeks, addDays, format } from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WeekGrid } from './calendar/week-grid';
import { Skeleton } from './skeleton';
import { useCalendarQuery } from '@/hooks/use-calendar-query';

function getInitialWeekStart(): string {
  // Today in America/New_York
  const todayET = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  const [y, m, d] = todayET.split('-').map(Number);
  const todayLocal = new Date(y, m - 1, d);
  // Monday of current week
  const monday = startOfWeek(todayLocal, { weekStartsOn: 1 });
  return format(monday, 'yyyy-MM-dd');
}

export function CalendarView() {
  const [weekStart, setWeekStart] = useState(getInitialWeekStart);

  const { data: events = [], isLoading } = useCalendarQuery(weekStart);

  // Generate array of 7 YYYY-MM-DD strings for the week
  const [y, m, d] = weekStart.split('-').map(Number);
  const weekStartDate = new Date(y, m - 1, d);
  const days = Array.from({ length: 7 }, (_, i) =>
    format(addDays(weekStartDate, i), 'yyyy-MM-dd')
  );

  function goToPrevWeek() {
    const prev = subWeeks(weekStartDate, 1);
    setWeekStart(format(prev, 'yyyy-MM-dd'));
  }

  function goToNextWeek() {
    const next = addWeeks(weekStartDate, 1);
    setWeekStart(format(next, 'yyyy-MM-dd'));
  }

  const weekLabel = `${format(weekStartDate, 'MMM d')} – ${format(addDays(weekStartDate, 6), 'MMM d, yyyy')}`;

  return (
    <div className="space-y-4">
      {/* Week navigation header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">{weekLabel}</h2>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={goToPrevWeek} className="h-8 w-8">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={goToNextWeek} className="h-8 w-8">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Calendar grid */}
      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <WeekGrid days={days} events={events} />
      )}
    </div>
  );
}
```

### Pattern 6: Dashboard Page Replacement

**What:** Replace the existing stats grid + `ActiveJobs` section in `dashboard/page.tsx` with `<CalendarView />` as the primary element. The stats cards and `WorkerStatus` can be retained above or removed — the roadmap says "7-column weekly calendar (not the old stats grid) as the primary content element". Interpreted as: calendar is primary, stats are secondary or removed.

**Decision for planner:** Either (A) remove stats completely and show only calendar, or (B) keep a compact stats bar above the calendar. Given the phase goal is to make the calendar the *primary content element*, (A) is cleaner and matches the success criterion "not the old stats grid". The `ActiveJobs` component shows the same data the calendar shows (pending/running jobs), making it redundant once the calendar is live.

**New dashboard/page.tsx structure:**
```tsx
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold sm:text-3xl">Your Week</h1>
        <WorkerStatus />   {/* compact inline — or remove per planner decision */}
      </div>
      <CalendarView />
    </div>
  );
}
```

### Anti-Patterns to Avoid

- **Parsing `event_date` as UTC:** `new Date('2026-02-27')` treats the string as UTC midnight, causing it to display as Feb 26 in ET (UTC-5). Always split the string: `const [y, m, d] = date.split('-').map(Number); new Date(y, m - 1, d)` to get local midnight.
- **Using `isFetching` to show skeleton on week navigation:** `isFetching` becomes `true` on every background refetch. Use `isLoading` (no cache yet) for the initial skeleton. On week navigation, `placeholderData: []` ensures the old data clears immediately and the grid shows empty (not skeleton).
- **Module-level `new Date()` for week initialization:** `new Date()` at module load is UTC-based. Always compute "today in ET" lazily inside the component or inside `useState(() => getInitialWeekStart())`.
- **CSS Grid with `grid-cols-7` on mobile without horizontal scroll:** 7 columns is too narrow on phones < 375px. Add `overflow-x-auto` on the grid container and `min-w-[480px]` on the inner grid to enable horizontal scrolling on very small screens.
- **`animate-pulse` on the entire `DayColumn`:** The pulse animation should only be on pending event pills, not the whole column. Applying it to the wrong element causes the day header to pulse too.
- **Deduplicate after rendering:** Apply the booked > pending > configured deduplication logic before rendering, not as a display toggle. Rendering all events and hiding duplicates via CSS creates accessibility issues.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Week arithmetic (prev/next, day array generation) | Manual `Date` subtraction with `getTime()` | `date-fns`: `startOfWeek`, `addWeeks`, `subWeeks`, `addDays`, `format` | Month/year boundary cases, leap years, DST transitions — all handled by date-fns |
| Query caching + background refresh | `useState` + `setInterval` fetch | `useCalendarQuery` hook with TanStack Query | Already decided in Phase 2; deduplication, stale-while-revalidate, tab-visibility pause built in |
| Status-to-color mapping | Long switch/if chain inline in JSX | `EVENT_STYLES` lookup object | Easier to extend, consistent with codebase pattern (see `STATUS_COLORS` in `active-jobs.tsx`) |
| Studio name display | Inline string manipulation | `STUDIOS[slug]?.name` from `@fitness-sniper/shared` | Single source of truth for studio names; already imported elsewhere in web |

**Key insight:** The calendar's complexity is almost entirely in layout (CSS Grid) and data transformation (deduplication, grouping by date). Both are straightforward with the tools already available — no new libraries are needed.

---

## Common Pitfalls

### Pitfall 1: YYYY-MM-DD Date Parsed as UTC
**What goes wrong:** `new Date('2026-02-27')` returns `2026-02-26T19:00:00` in ET (UTC-5), so the date renders as Feb 26 instead of Feb 27.
**Why it happens:** ISO date strings without a time component are treated as UTC midnight by the JS spec.
**How to avoid:** Always split the string manually: `const [y, m, d] = date.split('-').map(Number); const localDate = new Date(y, m - 1, d);` This gives local midnight (no TZ shift).
**Warning signs:** Calendar days are off by one for users in negative UTC offsets (all US timezones).

### Pitfall 2: `startOfWeek` Defaulting to Sunday
**What goes wrong:** `startOfWeek(date)` returns Sunday (day 0) by default. The API's recurring target expansion uses Monday as the reference week start (SQL `EXTRACT(DOW ...)`). Misalignment means Sunday targets could appear in the wrong column.
**Why it happens:** `date-fns` follows locale conventions — US locale is Sunday-start. The API SQL uses Monday-based math.
**How to avoid:** Always pass `{ weekStartsOn: 1 }` to `startOfWeek` in the CalendarView. The days array starts on Monday, column indices 0-6 = Mon-Sun, which aligns with the SQL formula.
**Warning signs:** Sunday events appear in the first column instead of the last; recurring targets on Sunday show up in Monday's column.

### Pitfall 3: Double Events for Booked Classes
**What goes wrong:** A class that was successfully booked appears twice in the same day column — once as `type: 'configured'` (the snipe target) and once as `type: 'booked'` (the booking history record).
**Why it happens:** The Phase 2 decision was to return all rows from the API and let Phase 3 handle deduplication. The `DayColumn` must apply the priority filter: when two events share the same `studio_slug + event_time`, show only the highest-priority one.
**How to avoid:** The `deduplicateEvents()` function in `DayColumn` uses `PRIORITY = { booked: 0, failed: 1, pending: 2, configured: 3 }` and keeps only the lowest-priority-number event per `studio_slug|event_time` key.
**Warning signs:** Users see two event pills for classes they've already booked.

### Pitfall 4: Week Navigation Causes Loading Flash
**What goes wrong:** When the user clicks prev/next week, the calendar briefly shows a skeleton (or empty state) while the new data loads, even if the response is fast.
**Why it happens:** TanStack Query `isLoading` is `true` when there is no cached data for the new week. If `data` is `undefined`, a skeleton renders.
**How to avoid:** Set `placeholderData: []` (or `keepPreviousData: true` in v4 API — in v5 it's `placeholderData: (prev) => prev ?? []`). With `placeholderData: []`, the grid renders empty but visible immediately, and events populate within 100-200ms without a skeleton flash.
**Warning signs:** Skeleton flashes every time the user navigates weeks.

### Pitfall 5: `animate-pulse` Breaking Layout
**What goes wrong:** Tailwind's `animate-pulse` applies `opacity: 0.5` cyclically. When applied to a container element, it pulses child text too, making time labels nearly invisible during the pulse.
**Why it happens:** `animate-pulse` is applied to the event pill container, which includes both the studio name and time.
**How to avoid:** Only apply `animate-pulse` to pending events. The pulse is intentional for pending (communicating uncertainty) but should not affect the text legibility — consider applying it only to a border or background pseudo-element via a parent class. Alternatively, use a subtle `opacity-50`-to-`opacity-100` on just the border.
**Warning signs:** Pending event text is invisible or hard to read during the animation.

### Pitfall 6: Mobile Layout with 7 Columns
**What goes wrong:** 7 equal columns on a 375px phone gives each column ~53px — enough for the day number but too narrow for event pill text.
**Why it happens:** CSS Grid divides available width equally across 7 columns. Event pill text gets truncated or wraps awkwardly.
**How to avoid:** Add `overflow-x-auto` to the outer wrapper and `min-w-[560px]` to the grid container. This enables horizontal scrolling on small screens. Alternatively, on mobile, collapse the view to show only Mon-Wed and Thu-Sun in two rows — but this adds complexity. The overflow-x-auto approach is simpler and sufficient.
**Warning signs:** Text truncation in event pills on mobile.

---

## Code Examples

Verified patterns from codebase analysis:

### ET "Today" Computation (from Phase 1 pattern in scheduler.ts)
```typescript
// Consistent with Phase 1 decision in STATE.md
// "Use toLocaleDateString('en-CA', { timeZone: 'America/New_York' })"
const todayET = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
// Returns 'YYYY-MM-DD' format — safe for direct string comparison with event_date
```

### Safe YYYY-MM-DD to Local Date Conversion
```typescript
// DO THIS — avoids UTC offset shift
const [year, month, day] = '2026-02-27'.split('-').map(Number);
const localDate = new Date(year, month - 1, day); // local midnight

// DON'T do this — parsed as UTC, shifts to previous day in ET
const wrongDate = new Date('2026-02-27'); // = 2026-02-26T19:00:00 ET
```

### Fixture Data for Plan 03-01 (static testing)
```typescript
// Static fixture for Plan 03-01 (before API wiring in 03-02)
const FIXTURE_EVENTS: CalendarEvent[] = [
  {
    id: '1',
    event_date: '2026-02-23', // Monday
    event_time: '6:00 AM',
    studio_slug: 'barrys',
    event_type: 'booked',
    source: 'history',
    meta: { spot: 'T-3', message: null },
  },
  {
    id: '2',
    event_date: '2026-02-25', // Wednesday
    event_time: '7:00 AM',
    studio_slug: 'slt',
    event_type: 'pending',
    source: 'job',
    meta: { job_status: 'pending', scheduled_for: '2026-02-25T12:00:00Z' },
  },
  {
    id: '3',
    event_date: '2026-02-27', // Friday
    event_time: '8:00 AM',
    studio_slug: 'aarmy',
    event_type: 'failed',
    source: 'history',
    meta: { message: 'Class was full' },
  },
  {
    id: '4',
    event_date: '2026-02-28', // Saturday
    event_time: '9:00 AM',
    studio_slug: 'barrys',
    event_type: 'configured',
    source: 'target',
    meta: { target_type: 'recurring', day_of_week: 6 },
  },
];
```

### Query Key Already Defined
```typescript
// Already in web/src/lib/query-keys.ts — no changes needed
calendarWeek: (weekStart: string) => ['calendar', weekStart] as const,
```

### TanStack Query `placeholderData` Pattern (v5)
```typescript
// v5 API — keepPreviousData replaced with placeholderData
const { data: events = [], isLoading } = useQuery({
  queryKey: QUERY_KEYS.calendarWeek(weekStart),
  queryFn: ...,
  placeholderData: (previousData) => previousData ?? [],
});
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `react-big-calendar` with CSS variable themes | Custom CSS Grid WeekGrid | Phase 3 plan decision (STATE.md) | Eliminates Tailwind v4 CSS variable conflict; smaller bundle; full visual control |
| `keepPreviousData: true` (TanStack Query v4) | `placeholderData: (prev) => prev ?? []` (v5) | TanStack Query v5 | Prevents empty flash on query key change (week navigation) |
| Date parsing via `new Date(isoString)` | Split `YYYY-MM-DD` strings for local date construction | Phase 1 pattern (INFRA-03) | Correct dates in all US timezones |

**Deprecated/outdated:**
- `keepPreviousData` option: Removed in TanStack Query v5, replaced by `placeholderData`.
- `react-day-picker` v8 API: Project uses v9 (`react-day-picker@^9.6.4`). The `ui/calendar.tsx` component uses v9 API (`DayPicker`, `getDefaultClassNames`, `DayButton`). Not directly relevant to WeekGrid, but note when checking the installed version.

---

## Open Questions

1. **Should the stats grid (active targets, pending jobs, booked count, worker status) be removed or retained above the calendar?**
   - What we know: The success criterion says "7-column weekly calendar (not the old stats grid) as the primary content element." The `ActiveJobs` component shows redundant data once the calendar shows pending events.
   - What's unclear: Whether the user wants zero stats or a compact bar above the calendar.
   - Recommendation: Remove the stats grid and `ActiveJobs` section entirely. Keep only a compact `WorkerStatus` inline in the page header. The calendar shows all the same information more usefully. The planner should make this call explicitly.

2. **What is the "today" column highlight behavior?**
   - What we know: The `isToday` check uses ET date string comparison, which is correct per INFRA-03 pattern.
   - What's unclear: Whether "today" gets a special background highlight in addition to the emerald header text.
   - Recommendation: A subtle `bg-white/[0.02]` background on the today column header area (same as other cards in this app) is sufficient. Avoid a full column highlight that competes with event colors.

3. **How does CAL-03 heatmap interact with the availability data in `class_schedules`?**
   - What we know: `class_schedules` has `available` and `spots_remaining` fields. `GET /api/schedules` exists. The calendar query does NOT join `class_schedules`.
   - What's unclear: Whether CAL-03 requires actual availability data from `class_schedules`, or if event density is an acceptable proxy.
   - Recommendation: Use event count as the heatmap proxy for Phase 3. A day with 3+ events gets a slightly stronger emerald tint than a day with 1 event. This satisfies the spirit of CAL-03 ("a busy day looks visually denser than an empty one") without a second API call. If richer availability data is needed, it can be added in Phase 4 when the schedule browser is built.

4. **Mobile: scrollable 7-column grid or alternative view?**
   - What we know: The dashboard layout uses `max-w-6xl` container. The calendar max content width is ~1200px. On mobile (375px), 7 columns is impractical.
   - What's unclear: Whether a horizontal scroll or a 3+4 row split is preferred.
   - Recommendation: Horizontal scroll with `overflow-x-auto` and `min-w-[560px]` on the grid. Simplest implementation, maintains the 7-column mental model. The planner should confirm.

---

## Validation Architecture

The `workflow.nyquist_validation` field is not present in `.planning/config.json` (only `research`, `plan_check`, and `verifier` flags exist). No formal test framework is configured for this project (confirmed in CLAUDE.md: "No test framework is configured. There are no automated tests."). Skipping this section.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `web/src/app/(dashboard)/dashboard/page.tsx`, `components/active-jobs.tsx`, `components/skeleton.tsx`, `components/worker-status.tsx`, `components/nav-bar.tsx`, `components/ui/calendar.tsx`, `app/globals.css`, `lib/query-keys.ts`, `lib/types.ts`, `lib/utils.ts`, `packages/shared/src/types.ts`, `packages/shared/src/studios.ts`, `web/package.json`
- Phase 2 outputs: `02-02-SUMMARY.md`, `web/src/app/api/calendar/route.ts` (actual built code, not plan)
- `.planning/STATE.md` — locked decisions: no react-big-calendar, no optimistic updates, custom WeekGrid ~200 lines CSS grid, dedup logic in UI not API
- `.planning/ROADMAP.md` — Phase 3 success criteria (7 columns, ET timezone, color coding, heatmap, week navigation)

### Secondary (MEDIUM confidence)
- `date-fns` availability: confirmed in root `node_modules/date-fns` (installed transitively via `react-day-picker@^9.6.4`). Not listed in `web/package.json` — transitive only.
- Tailwind v4 grid utilities: `grid-cols-7`, `gap-px`, `overflow-x-auto` — verified as working in v4 via `globals.css` inspection (same utility API as v3 for grid/flex). CSS variable incompatibility is with third-party calendar libraries, not with native Tailwind utilities.
- TanStack Query v5 `placeholderData` — replaces v4's `keepPreviousData`. Confirmed from Phase 2 research (HIGH confidence on v5 API).

### Tertiary (LOW confidence — flagged for validation)
- `animate-pulse` on dashed borders: Tailwind's `animate-pulse` uses `opacity` keyframes, which affect the entire element including border. The visual result with `border-dashed` needs manual testing — the border may not pulse visibly if `opacity` modulation is too subtle on a transparent background. May need `@keyframes` override if insufficient.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed; no new deps needed
- Architecture: HIGH — component structure follows established codebase patterns; data contract is Phase 2's built/verified API
- Date handling: HIGH — pattern directly verified from Phase 1's INFRA-03 implementation in codebase
- Heatmap (CAL-03): MEDIUM — event-count proxy approach is an interpretation of the requirement; actual slot data from `class_schedules` would be more accurate but adds complexity
- Mobile layout: MEDIUM — overflow-x-auto approach is standard but specific pixel breakpoints need testing

**Research date:** 2026-02-27
**Valid until:** 2026-03-28 (30 days — stable stack, no fast-moving dependencies)
