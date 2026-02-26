import { NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

  try {
    const [targetsRes, jobsRes, historyRes] = await Promise.all([
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
    ]);

    return NextResponse.json({
      targets: targetsRes.rows,
      activeJobs: jobsRes.rows,
      recentHistory: historyRes.rows,
    });
  } catch (err) {
    console.error('[dashboard/stats] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
