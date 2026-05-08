import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { signOut, clearAuthCookies } from '@/lib/cognito';

export async function POST() {
  try {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get('cognito_access_token')?.value;

    if (accessToken) {
      await signOut(accessToken);
    }

    const response = NextResponse.json({ success: true });
    clearAuthCookies(response.cookies);
    return response;
  } catch (err) {
    console.error('[auth/logout] POST error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
