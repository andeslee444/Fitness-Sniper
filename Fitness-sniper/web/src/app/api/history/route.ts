import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';

export async function GET(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const limit = Math.min(parseInt(searchParams.get('limit') || '20', 10), 100);
  const offset = Math.max(parseInt(searchParams.get('offset') || '0', 10), 0);
  const studioFilter = searchParams.get('studio') || null;

  try {
    // Build dynamic WHERE clause with optional studio filter
    const conditions = ['user_id = $1'];
    const baseParams: unknown[] = [user.sub];
    if (studioFilter) {
      conditions.push(`studio_slug = $${baseParams.length + 1}`);
      baseParams.push(studioFilter);
    }
    const whereClause = conditions.join(' AND ');

    // Count params: user_id + optional studio filter (no limit/offset)
    const countParams = [...baseParams];

    // Data params: user_id + optional studio filter + limit + offset
    const dataParams: unknown[] = [...baseParams, limit, offset];
    const limitIndex = baseParams.length + 1;
    const offsetIndex = baseParams.length + 2;

    const [{ rows }, { rows: countRows }] = await Promise.all([
      query(
        `SELECT * FROM booking_history WHERE ${whereClause} ORDER BY created_at DESC LIMIT $${limitIndex} OFFSET $${offsetIndex}`,
        dataParams,
      ),
      query<{ total: string }>(
        `SELECT COUNT(*) as total FROM booking_history WHERE ${whereClause}`,
        countParams,
      ),
    ]);

    const total = parseInt(countRows[0]?.total || '0', 10);

    return NextResponse.json({ rows, total, limit, offset });
  } catch (err) {
    console.error('[history] GET error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
