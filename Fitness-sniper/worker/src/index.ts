/**
 * Fitness Sniper Worker — Entry Point
 *
 * Runs on Mac Mini. Starts:
 * 1. Job Poller — polls for pending booking jobs
 * 2. Job Scheduler — creates jobs from enabled snipe targets
 * 3. Heartbeat — reports worker health to database
 */

import 'dotenv/config';
import { JobPoller } from './jobs/poller.js';
import { JobProcessor } from './jobs/processor.js';
import { JobScheduler } from './jobs/scheduler.js';
import { ScheduleScraper } from './jobs/schedule-scraper.js';
import { SlotWatcher } from './jobs/slot-watcher.js';
import { pool, query } from './db.js';

// ============================================================
// Config
// ============================================================

const WORKER_ID = process.env.WORKER_ID || `worker-${Date.now()}`;
const CONCURRENCY = parseInt(process.env.CONCURRENCY || '2', 10);

// ============================================================
// Initialize
// ============================================================

const processor = new JobProcessor(WORKER_ID);
const scheduler = new JobScheduler();
const scheduleScraper = new ScheduleScraper();
const slotWatcher = new SlotWatcher();

const poller = new JobPoller({
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
    await query(
      `INSERT INTO worker_heartbeats (worker_id, last_heartbeat, active_jobs, status, meta)
       VALUES ($1, NOW(), $2, 'online', $3)
       ON CONFLICT (worker_id) DO UPDATE SET
         last_heartbeat = NOW(),
         active_jobs = $2,
         status = 'online',
         meta = $3`,
      [
        WORKER_ID,
        poller.activeJobCount,
        JSON.stringify({
          pid: process.pid,
          memory: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
          uptime: Math.round(process.uptime()),
        }),
      ],
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
  scheduleScraper.stop();
  slotWatcher.stop();
  stopHeartbeat();

  // Mark worker as offline
  try {
    await query(
      `UPDATE worker_heartbeats SET status = 'offline', active_jobs = 0 WHERE worker_id = $1`,
      [WORKER_ID],
    );
  } catch {
    // Ignore — shutting down
  }

  // Wait for active jobs to finish (max 30s)
  const deadline = Date.now() + 30000;
  while (poller.activeJobCount > 0 && Date.now() < deadline) {
    console.log(`[worker] Waiting for ${poller.activeJobCount} active jobs...`);
    await new Promise((r) => setTimeout(r, 2000));
  }

  // Close database pool
  try {
    await pool.end();
  } catch {
    // Ignore — shutting down
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
console.log(`Fitness Sniper Worker v1.0.0`);
console.log(`Worker ID: ${WORKER_ID}`);
console.log(`Concurrency: ${CONCURRENCY}`);
console.log('='.repeat(50));

startHeartbeat();
scheduler.start();
scheduleScraper.start();
slotWatcher.start();
poller.start();
