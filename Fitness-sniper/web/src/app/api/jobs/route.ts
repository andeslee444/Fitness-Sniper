import { NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { rows } = await query(
    `SELECT id, status, scheduled_for, target_id FROM booking_jobs
     WHERE user_id = $1 AND status IN ('pending', 'claimed', 'running')
     ORDER BY scheduled_for ASC`,
    [user.sub],
  );

  return NextResponse.json(rows);
}
