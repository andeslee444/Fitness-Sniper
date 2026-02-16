/**
 * Class Sniper Worker — Entry Point
 *
 * Runs on Mac Mini. Starts:
 * 1. Job Poller — polls Supabase for pending booking jobs
 * 2. Job Scheduler — creates jobs from enabled snipe targets
 * 3. Heartbeat — reports worker health to Supabase
 */

import 'dotenv/config';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { JobPoller } from './jobs/poller.js';
import { JobProcessor } from './jobs/processor.js';
import { JobScheduler } from './jobs/scheduler.js';

// ============================================================
// Config validation
// ============================================================

function requireEnv(name: string): string {
  const val = process.env[name];
  if (!val) {
    console.error(`Missing required env var: ${name}`);
    process.exit(1);
  }
  return val;
}

const SUPABASE_URL = requireEnv('SUPABASE_URL');
const SUPABASE_SERVICE_KEY = requireEnv('SUPABASE_SERVICE_KEY');
const WORKER_ID = process.env.WORKER_ID || `worker-${Date.now()}`;
const CONCURRENCY = parseInt(process.env.CONCURRENCY || '2', 10);

// ============================================================
// Initialize
// ============================================================

const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
  auth: { persistSession: false },
});

const processor = new JobProcessor(supabase, WORKER_ID);
const scheduler = new JobScheduler(supabase);

const poller = new JobPoller(supabase, {
  workerId: WORKER_ID,
  concurrencyLimit: CONCURRENCY,
  onJob: (job) => processor.process(job),
});

// ============================================================
// Heartbeat — update worker_heartbeats every 30s
// ============================================================

let heartbeatInterval: NodeJS.Timeout | null = null;

async function sendHeartbeat(): Promise<void> {
  try {
    await supabase
      .from('worker_heartbeats')
      .upsert(
        {
          worker_id: WORKER_ID,
          last_heartbeat: new Date().toISOString(),
          active_jobs: poller.activeJobCount,
          status: 'online',
          meta: {
            pid: process.pid,
            memory: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
            uptime: Math.round(process.uptime()),
          },
        },
        { onConflict: 'worker_id' },
      );
  } catch (err) {
    console.error('[heartbeat] Error:', err);
  }
}

function startHeartbeat(): void {
  sendHeartbeat();
  heartbeatInterval = setInterval(sendHeartbeat, 30000);
}

function stopHeartbeat(): void {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
}

// ============================================================
// Graceful shutdown
// ============================================================

async function shutdown(signal: string): Promise<void> {
  console.log(`\n[worker] Received ${signal}, shutting down gracefully...`);

  poller.stop();
  scheduler.stop();
  stopHeartbeat();

  // Mark worker as offline
  try {
    await supabase
      .from('worker_heartbeats')
      .update({ status: 'offline', active_jobs: 0 })
      .eq('worker_id', WORKER_ID);
  } catch {
    // Ignore — shutting down
  }

  // Wait for active jobs to finish (max 30s)
  const deadline = Date.now() + 30000;
  while (poller.activeJobCount > 0 && Date.now() < deadline) {
    console.log(`[worker] Waiting for ${poller.activeJobCount} active jobs...`);
    await new Promise((r) => setTimeout(r, 2000));
  }

  console.log('[worker] Shutdown complete');
  process.exit(0);
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

// ============================================================
// Start
// ============================================================

console.log('='.repeat(50));
console.log(`Class Sniper Worker v1.0.0`);
console.log(`Worker ID: ${WORKER_ID}`);
console.log(`Concurrency: ${CONCURRENCY}`);
console.log(`Supabase: ${SUPABASE_URL}`);
console.log('='.repeat(50));

startHeartbeat();
scheduler.start();
poller.start();
