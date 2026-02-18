/**
 * Cognito Auth — helper functions for AWS Cognito authentication
 */

import {
  CognitoIdentityProviderClient,
  InitiateAuthCommand,
  SignUpCommand,
  AdminConfirmSignUpCommand,
  GlobalSignOutCommand,
  GetUserCommand,
} from '@aws-sdk/client-cognito-identity-provider';
import crypto from 'node:crypto';
import { cookies } from 'next/headers';

const client = new CognitoIdentityProviderClient({
  region: process.env.AWS_REGION || 'us-east-2',
});

const CLIENT_ID = process.env.COGNITO_CLIENT_ID!;
const CLIENT_SECRET = process.env.COGNITO_CLIENT_SECRET;
const USER_POOL_ID = process.env.COGNITO_USER_POOL_ID!;

function computeSecretHash(username: string): string | undefined {
  if (!CLIENT_SECRET) return undefined;
  return crypto
    .createHmac('sha256', CLIENT_SECRET)
    .update(username + CLIENT_ID)
    .digest('base64');
}

export async function signUp(email: string, password: string): Promise<{ sub: string }> {
  const secretHash = computeSecretHash(email);

  const command = new SignUpCommand({
    ClientId: CLIENT_ID,
    Username: email,
    Password: password,
    ...(secretHash && { SecretHash: secretHash }),
    UserAttributes: [
      { Name: 'email', Value: email },
      { Name: 'phone_number', Value: '+10000000000' },
    ],
  });

  const response = await client.send(command);

  // Auto-confirm the user (skips email verification)
  await client.send(
    new AdminConfirmSignUpCommand({
      UserPoolId: USER_POOL_ID,
      Username: email,
    }),
  );

  return { sub: response.UserSub! };
}

export async function signIn(
  email: string,
  password: string,
): Promise<{ accessToken: string; idToken: string; refreshToken: string; sub: string }> {
  const secretHash = computeSecretHash(email);

  const command = new InitiateAuthCommand({
    AuthFlow: 'USER_PASSWORD_AUTH',
    ClientId: CLIENT_ID,
    AuthParameters: {
      USERNAME: email,
      PASSWORD: password,
      ...(secretHash && { SECRET_HASH: secretHash }),
    },
  });

  const response = await client.send(command);
  const result = response.AuthenticationResult!;

  // Decode ID token to get sub
  const payload = JSON.parse(
    Buffer.from(result.IdToken!.split('.')[1], 'base64url').toString(),
  );

  return {
    accessToken: result.AccessToken!,
    idToken: result.IdToken!,
    refreshToken: result.RefreshToken!,
    sub: payload.sub,
  };
}

export async function signOut(accessToken: string): Promise<void> {
  try {
    await client.send(new GlobalSignOutCommand({ AccessToken: accessToken }));
  } catch {
    // Ignore errors — token might already be invalid
  }
}

export interface CognitoUser {
  sub: string;
  email: string;
}

export async function getSession(): Promise<CognitoUser | null> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('cognito_access_token')?.value;
  const idToken = cookieStore.get('cognito_id_token')?.value;

  if (!accessToken || !idToken) return null;

  try {
    // Validate access token by calling GetUser
    const response = await client.send(new GetUserCommand({ AccessToken: accessToken }));
    const email =
      response.UserAttributes?.find((a) => a.Name === 'email')?.Value || '';

    return { sub: response.Username!, email };
  } catch {
    return null;
  }
}

export function setAuthCookies(
  responseCookies: {
    set: (name: string, value: string, options?: Record<string, unknown>) => void;
  },
  tokens: { accessToken: string; idToken: string; refreshToken: string },
): void {
  const cookieOptions = {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict' as const,
    path: '/',
    maxAge: 60 * 60 * 24 * 30, // 30 days
  };

  responseCookies.set('cognito_access_token', tokens.accessToken, cookieOptions);
  responseCookies.set('cognito_id_token', tokens.idToken, cookieOptions);
  responseCookies.set('cognito_refresh_token', tokens.refreshToken, cookieOptions);
}

export function clearAuthCookies(
  responseCookies: {
    set: (name: string, value: string, options?: Record<string, unknown>) => void;
  },
): void {
  const options = { path: '/', maxAge: 0 };
  responseCookies.set('cognito_access_token', '', options);
  responseCookies.set('cognito_id_token', '', options);
  responseCookies.set('cognito_refresh_token', '', options);
}
