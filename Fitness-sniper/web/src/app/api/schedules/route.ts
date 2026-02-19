import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import { STUDIOS, fetchClassesFromAPI, fetchXpoClassesFromAPI, fetchArketaClassesFromAPI } from '@fitness-sniper/shared';
import type { ClassScheduleRow } from '@fitness-sniper/shared';

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

// 5-minute in-memory cache to avoid repeated API calls
const apiCache = new Map<string, { data: ClassScheduleRow[]; expires: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

/**
 * Compute the next occurrence of a given day-of-week (0=Sun..6=Sat)
 * as "YYYY-MM-DD". Returns today if today matches.
 */
function nextOccurrence(dayOfWeek: number): string {
  const now = new Date();
  const today = now.getDay();
  const diff = (dayOfWeek - today + 7) % 7;
  const target = new Date(now);
  target.setDate(target.getDate() + diff);
  return target.toISOString().split('T')[0];
}

export async function GET(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { searchParams } = request.nextUrl;
  const studio = searchParams.get('studio');
  const location = searchParams.get('location');
  const date = searchParams.get('date'); // "YYYY-MM-DD"
  const dateTo = searchParams.get('dateTo'); // optional end date for range queries
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

  if (date && dateTo) {
    // Date range
    conditions.push(`class_date >= $${paramIdx}`);
    params.push(date);
    paramIdx++;
    conditions.push(`class_date <= $${paramIdx}`);
    params.push(dateTo);
    paramIdx++;
  } else if (date) {
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

  // Try DB first — table may not exist yet
  // For range queries (dateTo), skip DB early-return: scraped data is often
  // incomplete (only covers the scrape window), so we always prefer the live API
  // which handles date ranges natively. DB rows are kept as fallback.
  let dbFallbackRows: ScheduleRow[] = [];
  try {
    const { rows } = await query<ScheduleRow>(
      `SELECT id, class_date, class_time, class_name, instructor,
              duration_minutes, available, spots_remaining, scraped_at
       FROM class_schedules
       WHERE ${conditions.join(' AND ')}
       ORDER BY class_date, class_time
       LIMIT ${dateTo ? 1000 : 200}`,
      params,
    );

    if (rows.length > 0) {
      if (!dateTo) {
        // Single-date query: DB data is sufficient
        const uniqueTimes = [...new Set(rows.map((r) => r.class_time))];
        return NextResponse.json({
          source: 'scraped' as const,
          times: uniqueTimes,
          classes: rows,
        });
      }
      // Range query: save as fallback, continue to live API
      dbFallbackRows = rows;
    }
  } catch {
    // DB table may not exist — fall through to live API
  }

  // --- Try live API (always for range queries, fallback for single-date) ---

  if (!location) {
    // Can't call API without a location — return DB data if we have any
    if (dbFallbackRows.length > 0) {
      const uniqueTimes = [...new Set(dbFallbackRows.map((r) => r.class_time))];
      return NextResponse.json({ source: 'scraped' as const, times: uniqueTimes, classes: dbFallbackRows });
    }
    return NextResponse.json({ source: 'empty' as const, times: [], classes: [] });
  }

  const studioConfig = STUDIOS[studio];
  if (!studioConfig) {
    return NextResponse.json({ source: 'empty' as const, times: [], classes: [] });
  }

  // Resolve a concrete date for the API call
  const targetDate = date || (dayOfWeek !== null && dayOfWeek !== undefined
    ? nextOccurrence(parseInt(dayOfWeek))
    : null);

  if (!targetDate) {
    return NextResponse.json({ source: 'empty' as const, times: [], classes: [] });
  }

  const endDate = dateTo || targetDate;

  // Check in-memory cache
  const cacheKey = `${studio}:${location}:${targetDate}:${endDate}`;
  const cached = apiCache.get(cacheKey);
  if (cached && cached.expires > Date.now()) {
    const classes = cached.data;
    const uniqueTimes = [...new Set(classes.map((c) => c.class_time))];
    return NextResponse.json({
      source: 'live_api' as const,
      times: uniqueTimes,
      classes: classes.map((c) => ({
        class_date: c.class_date,
        class_time: c.class_time,
        class_name: c.class_name,
        instructor: c.instructor,
        duration_minutes: c.duration_minutes,
        available: c.available,
        spots_remaining: c.spots_remaining,
      })),
    });
  }

  try {
    let liveClasses: ClassScheduleRow[];

    if (studioConfig.platform === 'xponential') {
      const domain = studioConfig.membersDomain || `https://members.${studio}.com`;
      liveClasses = await fetchXpoClassesFromAPI(domain, studio, location, targetDate, endDate);
    } else if (studioConfig.platform === 'arketa') {
      const widgetName = studioConfig.widgetName || studioConfig.tenant;
      liveClasses = await fetchArketaClassesFromAPI(widgetName, studio, location, targetDate, endDate);
    } else {
      // Mariana Tek
      liveClasses = await fetchClassesFromAPI(studioConfig.tenant, studio, location, targetDate, endDate);
    }

    // For range queries: merge DB scraped data with live API data.
    // Live APIs often only return future classes, while DB has historical scraped data.
    // Live data takes priority for dates it covers; DB fills gaps for dates it doesn't.
    let classes = liveClasses;
    if (dateTo && dbFallbackRows.length > 0) {
      const liveDateKeys = new Set(liveClasses.map((c) => c.class_date));
      const dbOnly = dbFallbackRows
        .filter((r) => {
          const dateKey = typeof r.class_date === 'string' && r.class_date.includes('T')
            ? r.class_date.split('T')[0]
            : String(r.class_date);
          return !liveDateKeys.has(dateKey);
        })
        .map((r) => ({
          studio_slug: studio,
          location_id: location,
          class_date: typeof r.class_date === 'string' && r.class_date.includes('T')
            ? r.class_date.split('T')[0]
            : String(r.class_date),
          class_time: r.class_time,
          class_name: r.class_name,
          instructor: r.instructor,
          duration_minutes: r.duration_minutes,
          available: r.available,
          spots_remaining: r.spots_remaining,
        }));
      classes = [...liveClasses, ...dbOnly];
    }

    // Cache the results
    apiCache.set(cacheKey, { data: classes, expires: Date.now() + CACHE_TTL });

    // Fire-and-forget: cache to DB for future requests
    if (liveClasses.length > 0) {
      cacheToDb(liveClasses).catch((err) =>
        console.error('[schedules] DB cache failed:', err),
      );
    }

    const uniqueTimes = [...new Set(classes.map((c) => c.class_time))];
    return NextResponse.json({
      source: 'live_api' as const,
      times: uniqueTimes,
      classes: classes.map((c) => ({
        class_date: c.class_date,
        class_time: c.class_time,
        class_name: c.class_name,
        instructor: c.instructor,
        duration_minutes: c.duration_minutes,
        available: c.available,
        spots_remaining: c.spots_remaining,
      })),
    });
  } catch (err) {
    console.error('[schedules] Live API fallback failed:', err);
    // Return DB data if available
    if (dbFallbackRows.length > 0) {
      const uniqueTimes = [...new Set(dbFallbackRows.map((r) => r.class_time))];
      return NextResponse.json({
        source: 'scraped' as const,
        times: uniqueTimes,
        classes: dbFallbackRows,
      });
    }
    return NextResponse.json({ source: 'empty' as const, times: [], classes: [] });
  }
}

/**
 * Fire-and-forget: upsert live API results into class_schedules
 * so subsequent requests hit the DB path.
 */
async function cacheToDb(classes: ClassScheduleRow[]): Promise<void> {
  for (const c of classes) {
    try {
      await query(
        `INSERT INTO class_schedules
           (studio_slug, location_id, class_date, class_time, class_name,
            instructor, duration_minutes, available, spots_remaining, scraped_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
         ON CONFLICT (studio_slug, location_id, class_date, class_time, class_name)
         DO UPDATE SET
           instructor = EXCLUDED.instructor,
           duration_minutes = EXCLUDED.duration_minutes,
           available = EXCLUDED.available,
           spots_remaining = EXCLUDED.spots_remaining,
           scraped_at = NOW()`,
        [
          c.studio_slug,
          c.location_id,
          c.class_date,
          c.class_time,
          c.class_name,
          c.instructor,
          c.duration_minutes,
          c.available,
          c.spots_remaining,
        ],
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`[schedules] Upsert failed for ${c.class_date} ${c.class_time}:`, msg);
    }
  }
}
