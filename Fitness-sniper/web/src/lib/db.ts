/**
 * Database client — server-side only pg.Pool for Next.js API routes and Server Components
 */

import pg from 'pg';

const { Pool } = pg;

const globalForPg = globalThis as unknown as { pgPool?: pg.Pool };
const connectionString = process.env.DATABASE_URL!;
const isLocalhost = connectionString?.includes('localhost') || connectionString?.includes('127.0.0.1');

export const pool =
  globalForPg.pgPool ??
  new Pool({
    connectionString,
    ssl: isLocalhost ? false : { rejectUnauthorized: false },
    max: 10,
  });

if (process.env.NODE_ENV !== 'production') {
  globalForPg.pgPool = pool;
}

export async function query<T extends pg.QueryResultRow = Record<string, unknown>>(
  text: string,
  params?: unknown[],
): Promise<pg.QueryResult<T>> {
  return pool.query<T>(text, params);
}
