import { NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const { rows } = await query(
      'SELECT * FROM worker_heartbeats ORDER BY last_heartbeat DESC LIMIT 1',
    );

    return NextResponse.json(rows[0] || null);
  } catch (err) {
    console.error('[worker-status] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
