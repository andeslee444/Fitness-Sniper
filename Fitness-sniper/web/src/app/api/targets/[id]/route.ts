import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';

const ALLOWED_COLUMNS = new Set([
  'enabled', 'time', 'day_of_week', 'seat_preference', 'preferred_spots',
  'target_date', 'target_type', 'location_id', 'studio_slug', 'class_type', 'instructor',
]);

export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { id } = await params;
  const body = await request.json();

  const setClauses: string[] = [];
  const values: unknown[] = [];
  let idx = 1;

  for (const [key, value] of Object.entries(body)) {
    if (!ALLOWED_COLUMNS.has(key)) continue;
    setClauses.push(`${key} = $${idx}`);
    values.push(value);
    idx++;
  }

  if (setClauses.length === 0) {
    return NextResponse.json({ error: 'No valid fields to update' }, { status: 400 });
  }

  values.push(id, user.sub);

  const { rows } = await query(
    `UPDATE snipe_targets SET ${setClauses.join(', ')} WHERE id = $${idx} AND user_id = $${idx + 1} RETURNING *`,
    values,
  );

  if (rows.length === 0) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  return NextResponse.json(rows[0]);
}

export async function DELETE(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { id } = await params;

  const { rowCount } = await query('DELETE FROM snipe_targets WHERE id = $1 AND user_id = $2', [id, user.sub]);

  if (rowCount === 0) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  return NextResponse.json({ success: true });
}
