import { NextRequest, NextResponse } from 'next/server';
import { signUp, signIn, setAuthCookies } from '@/lib/cognito';
import { query } from '@/lib/db';

// Simple in-memory rate limiter for signup
const signupAttempts = new Map<string, { count: number; resetAt: number }>();
const MAX_ATTEMPTS = 3;
const WINDOW_MS = 60 * 60 * 1000; // 1 hour

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const entry = signupAttempts.get(ip);
  if (!entry || now > entry.resetAt) {
    signupAttempts.set(ip, { count: 1, resetAt: now + WINDOW_MS });
    return false;
  }
  entry.count++;
  return entry.count > MAX_ATTEMPTS;
}

function mapCognitoSignupError(err: unknown): { message: string; status: number } {
  if (!(err instanceof Error)) return { message: 'Signup failed', status: 400 };

  const name = (err as { name?: string }).name || '';
  switch (name) {
    case 'UsernameExistsException':
      return { message: 'An account with this email already exists', status: 409 };
    case 'InvalidPasswordException':
      return { message: 'Password does not meet requirements (min 8 chars, mixed case, number)', status: 400 };
    case 'InvalidParameterException':
      return { message: 'Invalid email or password format', status: 400 };
    case 'TooManyRequestsException':
      return { message: 'Too many attempts. Please try again later.', status: 429 };
    default:
      return { message: 'Signup failed', status: 400 };
  }
}

export async function POST(request: NextRequest) {
  const ip = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown';
  if (isRateLimited(ip)) {
    return NextResponse.json({ error: 'Too many signup attempts. Please try again later.' }, { status: 429 });
  }

  try {
    const { email, password } = await request.json();

    if (!email || !password) {
      return NextResponse.json({ error: 'Email and password required' }, { status: 400 });
    }

    // 1. Create Cognito user
    const { sub } = await signUp(email, password);

    // 2. Create profile in database
    await query(
      `INSERT INTO profiles (id, email, display_name) VALUES ($1, $2, $3)`,
      [sub, email, email.split('@')[0]],
    );

    // 3. Sign in to get tokens
    const tokens = await signIn(email, password);

    const response = NextResponse.json({ success: true });
    setAuthCookies(response.cookies, tokens);
    return response;
  } catch (err) {
    const { message, status } = mapCognitoSignupError(err);
    return NextResponse.json({ error: message }, { status });
  }
}
