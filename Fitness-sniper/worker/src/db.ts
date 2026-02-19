/**
 * Database client — shared pg.Pool for all worker queries
 */

import pg from 'pg';

const { Pool } = pg;

function requireEnv(name: string): string {
  const val = process.env[name];
  if (!val) {
    console.error(`Missing required env var: ${name}`);
    process.exit(1);
  }
  return val;
}

const connectionString = requireEnv('DATABASE_URL');
const isLocalhost = connectionString.includes('localhost') || connectionString.includes('127.0.0.1');

export const pool = new Pool({
  connectionString,
  ssl: isLocalhost ? false : { rejectUnauthorized: false },
  max: 10,
});

export async function query<T extends pg.QueryResultRow = Record<string, unknown>>(
  text: string,
  params?: unknown[],
): Promise<pg.QueryResult<T>> {
  return pool.query<T>(text, params);
}
