import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';

export async function GET(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const limit = Math.min(parseInt(searchParams.get('limit') || '20', 10), 100);
  const offset = Math.max(parseInt(searchParams.get('offset') || '0', 10), 0);

  try {
    const [{ rows }, { rows: countRows }] = await Promise.all([
      query(
        'SELECT * FROM booking_history WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3',
        [user.sub, limit, offset],
      ),
      query<{ total: string }>(
        'SELECT COUNT(*) as total FROM booking_history WHERE user_id = $1',
        [user.sub],
      ),
    ]);

    const total = parseInt(countRows[0]?.total || '0', 10);

    return NextResponse.json({ rows, total, limit, offset });
  } catch (err) {
    console.error('[history] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
