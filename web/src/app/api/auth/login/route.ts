import { NextRequest, NextResponse } from 'next/server';
import { signIn, setAuthCookies } from '@/lib/cognito';

// Simple in-memory rate limiter for auth endpoints
const loginAttempts = new Map<string, { count: number; resetAt: number }>();
const MAX_ATTEMPTS = 5;
const WINDOW_MS = 15 * 60 * 1000; // 15 minutes

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const entry = loginAttempts.get(ip);
  if (!entry || now > entry.resetAt) {
    loginAttempts.set(ip, { count: 1, resetAt: now + WINDOW_MS });
    return false;
  }
  entry.count++;
  return entry.count > MAX_ATTEMPTS;
}

function mapCognitoError(err: unknown): { message: string; status: number } {
  if (!(err instanceof Error)) return { message: 'Authentication failed', status: 401 };

  const name = (err as { name?: string }).name || '';
  switch (name) {
    case 'NotAuthorizedException':
      return { message: 'Incorrect email or password', status: 401 };
    case 'UserNotFoundException':
      return { message: 'No account found with this email', status: 401 };
    case 'UserNotConfirmedException':
      return { message: 'Account not confirmed. Please check your email.', status: 403 };
    case 'PasswordResetRequiredException':
      return { message: 'Password reset required. Please reset your password.', status: 403 };
    case 'TooManyRequestsException':
      return { message: 'Too many attempts. Please try again later.', status: 429 };
    default:
      return { message: 'Authentication failed', status: 401 };
  }
}

export async function POST(request: NextRequest) {
  const ip = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown';
  if (isRateLimited(ip)) {
    return NextResponse.json({ error: 'Too many login attempts. Please try again later.' }, { status: 429 });
  }

  try {
    const { email, password } = await request.json();

    if (!email || !password) {
      return NextResponse.json({ error: 'Email and password required' }, { status: 400 });
    }

    const tokens = await signIn(email, password);

    const response = NextResponse.json({ success: true });
    setAuthCookies(response.cookies, tokens);
    return response;
  } catch (err) {
    const { message, status } = mapCognitoError(err);
    return NextResponse.json({ error: message }, { status });
  }
}
