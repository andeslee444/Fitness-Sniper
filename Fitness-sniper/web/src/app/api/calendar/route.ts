import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import type { CalendarEvent } from '@fitness-sniper/shared';

const WEEK_START_REGEX = /^\d{4}-\d{2}-\d{2}$/;

const CALENDAR_SQL = `
WITH week_bounds AS (
  SELECT
    $2::date AS week_start,
    $2::date + INTERVAL '7 days' AS week_end
)

-- Branch 1: booking_history (booked/failed events)
SELECT
  bh.id::text AS id,
  bh.class_date::text AS event_date,
  bh.class_time AS event_time,
  bh.studio_slug,
  CASE bh.status WHEN 'booked' THEN 'booked' ELSE 'failed' END AS event_type,
  'history' AS source,
  jsonb_build_object('spot', bh.spot, 'message', bh.message) AS meta
FROM booking_history bh, week_bounds wb
WHERE bh.user_id = $1
  AND bh.class_date >= wb.week_start
  AND bh.class_date < wb.week_end

UNION ALL

-- Branch 2: booking_jobs (pending/claimed/running events)
SELECT
  bj.id::text AS id,
  (COALESCE(bj.class_datetime, bj.scheduled_for) AT TIME ZONE 'America/New_York')::date::text AS event_date,
  to_char(COALESCE(bj.class_datetime, bj.scheduled_for) AT TIME ZONE 'America/New_York', 'FMHH12:MI AM') AS event_time,
  t.studio_slug,
  'pending' AS event_type,
  'job' AS source,
  jsonb_build_object(
    'scheduled_for', bj.scheduled_for,
    'class_datetime', bj.class_datetime,
    'job_status', bj.status
  ) AS meta
FROM booking_jobs bj
LEFT JOIN snipe_targets t ON t.id = bj.target_id,
week_bounds wb
WHERE bj.user_id = $1
  AND bj.status IN ('pending', 'claimed', 'running')
  AND (COALESCE(bj.class_datetime, bj.scheduled_for) AT TIME ZONE 'America/New_York')::date >= wb.week_start
  AND (COALESCE(bj.class_datetime, bj.scheduled_for) AT TIME ZONE 'America/New_York')::date < wb.week_end

UNION ALL

-- Branch 3: snipe_targets recurring (expand day_of_week to dates in the 7-day window)
SELECT
  st.id::text AS id,
  (
    wb.week_start
    + ((st.day_of_week - EXTRACT(DOW FROM wb.week_start)::int + 7) % 7) * INTERVAL '1 day'
  )::date::text AS event_date,
  st.time AS event_time,
  st.studio_slug,
  'configured' AS event_type,
  'target' AS source,
  jsonb_build_object('target_type', 'recurring', 'day_of_week', st.day_of_week) AS meta
FROM snipe_targets st, week_bounds wb
WHERE st.user_id = $1
  AND st.enabled = true
  AND st.target_type = 'recurring'
  AND st.day_of_week IS NOT NULL

UNION ALL

-- Branch 4: snipe_targets one_time (filter by target_date in window)
SELECT
  st.id::text AS id,
  st.target_date::text AS event_date,
  st.time AS event_time,
  st.studio_slug,
  'configured' AS event_type,
  'target' AS source,
  jsonb_build_object('target_type', 'one_time') AS meta
FROM snipe_targets st, week_bounds wb
WHERE st.user_id = $1
  AND st.enabled = true
  AND st.target_type = 'one_time'
  AND st.target_date >= wb.week_start
  AND st.target_date < wb.week_end

ORDER BY event_date, event_time NULLS LAST
`;

export async function GET(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const weekStart = searchParams.get('weekStart');

  if (!weekStart || !WEEK_START_REGEX.test(weekStart)) {
    return NextResponse.json(
      { error: 'weekStart query parameter is required (YYYY-MM-DD)' },
      { status: 400 },
    );
  }

  try {
    const { rows } = await query<CalendarEvent>(CALENDAR_SQL, [user.sub, weekStart]);
    return NextResponse.json(rows);
  } catch (err) {
    console.error('[calendar] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
