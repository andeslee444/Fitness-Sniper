import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import { z } from 'zod';
import { STUDIOS, parseTime } from '@fitness-sniper/shared';

const TIME_REGEX = /^\d{1,2}:\d{2}\s?(AM|PM)$/i;

// Time is optional for Arketa studios (user picks a day, worker snipes any slot)
const timeField = z.string().regex(TIME_REGEX, 'Time must be like "6:00 AM"').nullable().optional();

const targetSchema = z.discriminatedUnion('target_type', [
  z.object({
    target_type: z.literal('recurring'),
    studio_slug: z.string().refine((s) => s in STUDIOS, 'Unknown studio'),
    location_id: z.string().default(''),
    day_of_week: z.number().int().min(0).max(6),
    time: timeField,
    seat_preference: z.enum(['front', 'middle', 'back', 'any']).default('any'),
    preferred_spots: z.array(z.string()).default([]),
    target_date: z.null().optional(),
    class_type: z.string().nullable().optional(),
  }),
  z.object({
    target_type: z.literal('one_time'),
    studio_slug: z.string().refine((s) => s in STUDIOS, 'Unknown studio'),
    location_id: z.string().default(''),
    day_of_week: z.null().optional(),
    time: timeField,
    seat_preference: z.enum(['front', 'middle', 'back', 'any']).default('any'),
    preferred_spots: z.array(z.string()).default([]),
    target_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be YYYY-MM-DD'),
    class_type: z.string().nullable().optional(),
  }),
]).refine((data) => {
  // Non-Arketa studios still require a time
  const studio = STUDIOS[data.studio_slug];
  if (studio?.platform !== 'arketa' && !data.time) {
    return false;
  }
  return true;
}, { message: 'Time is required for this studio' });

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const { rows } = await query(
      'SELECT * FROM snipe_targets WHERE user_id = $1 ORDER BY created_at DESC',
      [user.sub],
    );
    return NextResponse.json(rows);
  } catch (err) {
    console.error('[targets] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const body = await request.json();

    // Zod validation
    const parsed = targetSchema.safeParse(body);
    if (!parsed.success) {
      const firstError = parsed.error.issues[0]?.message || 'Invalid input';
      return NextResponse.json({ error: firstError }, { status: 400 });
    }

    const data = parsed.data;

    // One-time: reject past dates
    if (data.target_type === 'one_time') {
      const dateObj = new Date(data.target_date + 'T00:00:00');
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (dateObj < today) {
        return NextResponse.json({ error: 'target_date cannot be in the past' }, { status: 400 });
      }
    }

    // Check that credentials exist for this studio before allowing target creation
    const { rows: creds } = await query(
      'SELECT id FROM studio_credentials WHERE user_id = $1 AND studio_slug = $2',
      [user.sub, data.studio_slug],
    );
    if (creds.length === 0) {
      return NextResponse.json(
        { error: `Save your ${STUDIOS[data.studio_slug]?.name || data.studio_slug} credentials first` },
        { status: 400 },
      );
    }

    const { rows } = await query(
      `INSERT INTO snipe_targets (user_id, studio_slug, location_id, target_type, day_of_week, time, target_date, seat_preference, preferred_spots, class_type, enabled)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, true)
       RETURNING *`,
      [
        user.sub,
        data.studio_slug,
        data.location_id,
        data.target_type,
        data.target_type === 'recurring' ? data.day_of_week : null,
        data.time || null,
        data.target_type === 'one_time' ? data.target_date : null,
        data.seat_preference,
        data.preferred_spots,
        data.class_type || null,
      ],
    );

    const target = rows[0];

    // Immediately create a booking job if within the booking window
    // (skip Arketa — the SlotWatcher handles job creation for those)
    const studioForJob = STUDIOS[data.studio_slug];
    try {
      const classDate = data.time ? getClassDate(data, data.time) : null;
      if (classDate && classDate > new Date() && studioForJob?.platform !== 'arketa') {
        const windowDays = studioForJob?.bookingWindowDays ?? 7;

        // Compute scheduled_for: classDate minus booking window
        // If already past, execute immediately (set to now)
        const now = new Date();
        let scheduledFor = new Date(classDate);
        scheduledFor.setDate(scheduledFor.getDate() - windowDays);
        if (scheduledFor < now) {
          scheduledFor = now;
        }

        await query(
          `INSERT INTO booking_jobs (user_id, target_id, status, scheduled_for, class_datetime)
           VALUES ($1, $2, 'pending', $3, $4)`,
          [user.sub, target.id, scheduledFor.toISOString(), classDate.toISOString()],
        );
      }
    } catch {
      // Non-critical — scheduler will pick it up on next scan
    }

    return NextResponse.json(target, { status: 201 });
  } catch (err) {
    console.error('[targets] POST error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

function getClassDate(
  data: { target_type: string; target_date?: string | null; day_of_week?: number | null },
  time: string,
): Date | null {
  const parsed = parseTime(time);
  const hours = parsed?.hours24 ?? 0;
  const minutes = parsed?.minutes ?? 0;

  if (data.target_type === 'one_time' && data.target_date) {
    const [year, month, day] = data.target_date.split('-').map(Number);
    return new Date(year, month - 1, day, hours, minutes, 0, 0);
  }

  if (data.target_type === 'recurring' && data.day_of_week != null) {
    const etTodayStr = new Date().toLocaleDateString('en-CA', {
      timeZone: 'America/New_York',
    });
    const [year, month, day] = etTodayStr.split('-').map(Number);
    const target = new Date(year, month - 1, day, hours, minutes, 0, 0);
    const etDayOfWeek = new Date(etTodayStr + 'T12:00:00').getDay();
    const daysUntil = (data.day_of_week - etDayOfWeek + 7) % 7;
    target.setDate(target.getDate() + daysUntil);
    if (daysUntil === 0) {
      const etNowStr = new Date().toLocaleTimeString('en-US', {
        timeZone: 'America/New_York',
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
      });
      const [etHour, etMin] = etNowStr.split(':').map(Number);
      if (etHour > hours || (etHour === hours && etMin >= minutes)) {
        target.setDate(target.getDate() + 7);
      }
    }
    return target;
  }

  return null;
}
