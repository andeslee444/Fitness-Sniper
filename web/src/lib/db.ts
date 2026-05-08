/**
 * Database client — server-side only pg.Pool for Next.js API routes and Server Components
 */

import pg from 'pg';

const { Pool } = pg;

const globalForPg = globalThis as unknown as { pgPool?: pg.Pool };
const DEFAULT_POOL_MAX = process.env.NODE_ENV === 'production' ? 2 : 10;

function requireEnv(name: string): string {
  const val = process.env[name];
  if (!val) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return val;
}

function getPoolMax(): number {
  const raw = process.env.DATABASE_POOL_MAX;
  if (!raw) return DEFAULT_POOL_MAX;

  const parsed = Number.parseInt(raw, 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : DEFAULT_POOL_MAX;
}

export function getPool(): pg.Pool {
  if (globalForPg.pgPool) return globalForPg.pgPool;

  const connectionString = requireEnv('DATABASE_URL');
  const isLocalhost = connectionString.includes('localhost') || connectionString.includes('127.0.0.1');

  globalForPg.pgPool = new Pool({
    connectionString,
    ssl: isLocalhost ? false : { rejectUnauthorized: false },
    max: getPoolMax(),
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 10_000,
    allowExitOnIdle: true,
  });

  return globalForPg.pgPool;
}

export async function query<T extends pg.QueryResultRow = Record<string, unknown>>(
  text: string,
  params?: unknown[],
): Promise<pg.QueryResult<T>> {
  return getPool().query<T>(text, params);
}
