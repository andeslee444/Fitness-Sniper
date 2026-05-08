import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { refreshSession } from '@/lib/cognito';

export async function POST() {
  try {
    const cookieStore = await cookies();
    const refreshToken = cookieStore.get('cognito_refresh_token')?.value;
    const idToken = cookieStore.get('cognito_id_token')?.value;

    if (!refreshToken || !idToken) {
      return NextResponse.json({ error: 'No refresh token' }, { status: 401 });
    }

    // Decode email from ID token JWT payload — no network call needed
    const email: string = JSON.parse(
      Buffer.from(idToken.split('.')[1], 'base64url').toString(),
    ).email;

    const tokens = await refreshSession(refreshToken, email);

    if (!tokens) {
      return NextResponse.json({ error: 'Session expired' }, { status: 401 });
    }

    const cookieOptions = {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict' as const,
      path: '/',
      maxAge: 60 * 60 * 24 * 30, // 30 days
    };

    const response = NextResponse.json({ success: true });
    response.cookies.set('cognito_access_token', tokens.accessToken, cookieOptions);
    response.cookies.set('cognito_id_token', tokens.idToken, cookieOptions);
    // NOTE: Do NOT set cognito_refresh_token — REFRESH_TOKEN_AUTH does not return a new one

    return response;
  } catch (err) {
    console.error('[auth/refresh] Error:', err);
    return NextResponse.json({ error: 'Session expired' }, { status: 401 });
  }
}
