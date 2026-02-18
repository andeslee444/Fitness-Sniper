import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import { STUDIO_TIMES } from '@/lib/studios';

interface ScheduleRow {
  id: string;
  class_date: string;
  class_time: string;
  class_name: string | null;
  instructor: string | null;
  duration_minutes: number | null;
  available: boolean;
  spots_remaining: number | null;
  scraped_at: string;
}

export async function GET(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { searchParams } = request.nextUrl;
  const studio = searchParams.get('studio');
  const location = searchParams.get('location');
  const date = searchParams.get('date'); // "YYYY-MM-DD"
  const dayOfWeek = searchParams.get('dayOfWeek'); // "0"-"6"

  if (!studio) {
    return NextResponse.json({ error: 'studio parameter required' }, { status: 400 });
  }

  // Build query conditions
  const conditions: string[] = ['studio_slug = $1'];
  const params: unknown[] = [studio];
  let paramIdx = 2;

  if (location) {
    conditions.push(`location_id = $${paramIdx}`);
    params.push(location);
    paramIdx++;
  }

  if (date) {
    // Specific date
    conditions.push(`class_date = $${paramIdx}`);
    params.push(date);
    paramIdx++;
  } else if (dayOfWeek !== null && dayOfWeek !== undefined) {
    // Filter by day of week — get upcoming classes matching this day
    conditions.push(`EXTRACT(DOW FROM class_date) = $${paramIdx}`);
    params.push(parseInt(dayOfWeek));
    paramIdx++;
    // Only show future dates
    conditions.push('class_date >= CURRENT_DATE');
  } else {
    // Default: future classes
    conditions.push('class_date >= CURRENT_DATE');
  }

  const { rows } = await query<ScheduleRow>(
    `SELECT id, class_date, class_time, class_name, instructor,
            duration_minutes, available, spots_remaining, scraped_at
     FROM class_schedules
     WHERE ${conditions.join(' AND ')}
     ORDER BY class_date, class_time
     LIMIT 200`,
    params,
  );

  // If we have scraped data, return it
  if (rows.length > 0) {
    // Deduplicate times (same time can appear across multiple dates)
    const uniqueTimes = [...new Set(rows.map((r) => r.class_time))];
    return NextResponse.json({
      source: 'scraped' as const,
      times: uniqueTimes,
      classes: rows,
    });
  }

  // Fall back to hardcoded times
  const hardcodedTimes = STUDIO_TIMES[studio] || [];
  return NextResponse.json({
    source: 'hardcoded' as const,
    times: hardcodedTimes,
    classes: [],
  });
}
