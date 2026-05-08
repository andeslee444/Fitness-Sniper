import { NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

  try {
    const [targetsRes, jobsRes, historyRes, studioStatsRes] = await Promise.all([
      query('SELECT id, enabled FROM snipe_targets WHERE user_id = $1', [user.sub]),
      query(
        `SELECT id, status, scheduled_for, class_datetime, target_id FROM booking_jobs
         WHERE user_id = $1 AND status IN ('pending', 'claimed', 'running')
         ORDER BY COALESCE(class_datetime, scheduled_for) ASC`,
        [user.sub],
      ),
      query(
        `SELECT id, status FROM booking_history
         WHERE user_id = $1 AND created_at >= $2`,
        [user.sub, thirtyDaysAgo],
      ),
      query<{ studio_slug: string; booked: string; total: string }>(
        `SELECT
           studio_slug,
           COUNT(*) FILTER (WHERE status = 'booked') AS booked,
           COUNT(*) AS total
         FROM booking_history
         WHERE user_id = $1
           AND created_at >= NOW() - INTERVAL '30 days'
         GROUP BY studio_slug
         ORDER BY total DESC`,
        [user.sub],
      ),
    ]);

    return NextResponse.json({
      targets: targetsRes.rows,
      activeJobs: jobsRes.rows,
      recentHistory: historyRes.rows,
      studioStats: studioStatsRes.rows,
    });
  } catch (err) {
    console.error('[dashboard/stats] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
