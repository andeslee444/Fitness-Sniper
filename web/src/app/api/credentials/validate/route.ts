import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/cognito';
import { query } from '@/lib/db';
import crypto from 'node:crypto';
import { STUDIOS } from '@fitness-sniper/shared';

const ALGORITHM = 'aes-256-gcm';

function getKey(): Buffer {
  const hex = process.env.ENCRYPTION_KEY;
  if (!hex || hex.length !== 64) {
    throw new Error('ENCRYPTION_KEY must be a 64-character hex string');
  }
  return Buffer.from(hex, 'hex');
}

function decrypt(ciphertext: string, iv: string, authTag: string): string {
  const key = getKey();
  const decipher = crypto.createDecipheriv(
    ALGORITHM,
    key,
    Buffer.from(iv, 'base64'),
  );
  decipher.setAuthTag(Buffer.from(authTag, 'base64'));
  let decrypted = decipher.update(ciphertext, 'base64', 'utf8');
  decrypted += decipher.final('utf8');
  return decrypted;
}

async function testMarianaTekAuth(
  tenant: string,
  email: string,
  password: string,
  signal: AbortSignal,
): Promise<boolean> {
  const res = await fetch(
    `https://${tenant}.marianatek.com/api/customer/v1/auth/access-tokens`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      signal,
    },
  );
  // 200/201 = valid credentials, 4xx = invalid
  return res.ok;
}

async function testXponentialAuth(
  membersDomain: string,
  email: string,
  password: string,
  signal: AbortSignal,
): Promise<boolean> {
  const res = await fetch(`${membersDomain}/api/xpass/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
    signal,
  });
  return res.ok;
}

async function testArketaAuth(
  email: string,
  password: string,
  signal: AbortSignal,
): Promise<boolean> {
  // Arketa uses Firebase signInWithPassword
  const FIREBASE_API_KEY = 'AIzaSyCNSSHH1yTQ492d42qWOG_V_m2uQGdQF74';
  const res = await fetch(
    `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${FIREBASE_API_KEY}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        returnSecureToken: true,
      }),
      signal,
    },
  );
  if (!res.ok) return false;
  const data = await res.json();
  return !!data.idToken;
}

export async function POST(request: NextRequest) {
  try {
    const user = await getSession();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { studioSlug } = await request.json();
    if (!studioSlug) {
      return NextResponse.json({ error: 'studioSlug required' }, { status: 400 });
    }

    const studio = STUDIOS[studioSlug];
    if (!studio) {
      return NextResponse.json({ error: 'Unknown studio' }, { status: 400 });
    }

    // Fetch encrypted credentials from DB
    const { rows } = await query(
      'SELECT encrypted_email, encrypted_password, iv, auth_tag, password_iv, password_auth_tag FROM studio_credentials WHERE user_id = $1 AND studio_slug = $2',
      [user.sub, studioSlug],
    );

    if (rows.length === 0) {
      return NextResponse.json({ status: 'untested' });
    }

    // Decrypt credentials
    const row = rows[0] as {
      encrypted_email: string;
      encrypted_password: string;
      iv: string;
      auth_tag: string;
      password_iv: string;
      password_auth_tag: string;
    };
    const email = decrypt(row.encrypted_email, row.iv, row.auth_tag);
    const password = decrypt(row.encrypted_password, row.password_iv, row.password_auth_tag);

    // Create abort controller with 5s timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      let ok = false;

      switch (studio.platform) {
        case 'mariana-tek':
          ok = await testMarianaTekAuth(studio.tenant, email, password, controller.signal);
          break;
        case 'xponential':
          if (!studio.membersDomain) {
            clearTimeout(timeoutId);
            return NextResponse.json({ status: 'untested' });
          }
          ok = await testXponentialAuth(studio.membersDomain, email, password, controller.signal);
          break;
        case 'arketa':
          ok = await testArketaAuth(email, password, controller.signal);
          break;
        default:
          clearTimeout(timeoutId);
          return NextResponse.json({ status: 'untested' });
      }

      clearTimeout(timeoutId);
      return NextResponse.json({ status: ok ? 'connected' : 'invalid' });
    } catch (err) {
      clearTimeout(timeoutId);
      // Timeout or network error — return untested, not invalid
      if (err instanceof DOMException && err.name === 'AbortError') {
        return NextResponse.json({ status: 'untested' });
      }
      return NextResponse.json({ status: 'invalid' });
    }
  } catch (err) {
    console.error('[credentials/validate] Error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
