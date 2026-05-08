import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import crypto from 'node:crypto';

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16;

function getKey(): Buffer {
  const hex = process.env.ENCRYPTION_KEY;
  if (!hex || hex.length !== 64) {
    throw new Error('ENCRYPTION_KEY must be a 64-character hex string');
  }
  return Buffer.from(hex, 'hex');
}

function encrypt(plaintext: string): { ciphertext: string; iv: string; authTag: string } {
  const key = getKey();
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv, { authTagLength: 16 });
  let encrypted = cipher.update(plaintext, 'utf8', 'base64');
  encrypted += cipher.final('base64');
  return {
    ciphertext: encrypted,
    iv: iv.toString('base64'),
    authTag: cipher.getAuthTag().toString('base64'),
  };
}

export async function POST(request: NextRequest) {
  try {
    const user = await getSession();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { studioSlug, email, password } = await request.json();

    if (!studioSlug || !email || !password) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const encEmail = encrypt(email);
    const encPassword = encrypt(password);

    await query(
      `INSERT INTO studio_credentials (user_id, studio_slug, encrypted_email, encrypted_password, iv, auth_tag, password_iv, password_auth_tag)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       ON CONFLICT (user_id, studio_slug) DO UPDATE SET
         encrypted_email = $3, encrypted_password = $4, iv = $5, auth_tag = $6,
         password_iv = $7, password_auth_tag = $8, updated_at = NOW()`,
      [user.sub, studioSlug, encEmail.ciphertext, encPassword.ciphertext,
       encEmail.iv, encEmail.authTag, encPassword.iv, encPassword.authTag],
    );

    return NextResponse.json({ success: true });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Internal error' },
      { status: 500 },
    );
  }
}

export async function DELETE(request: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const { studioSlug } = await request.json();
    await query(
      'DELETE FROM studio_credentials WHERE user_id = $1 AND studio_slug = $2',
      [user.sub, studioSlug],
    );
    return NextResponse.json({ success: true });
  } catch (err) {
    console.error('[credentials] DELETE error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
