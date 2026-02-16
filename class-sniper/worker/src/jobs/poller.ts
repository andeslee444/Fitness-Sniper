/**
 * Job Poller — polls Supabase for claimable booking jobs
 *
 * Uses claim_next_job() RPC for atomic claiming with FOR UPDATE SKIP LOCKED.
 * Exponential backoff on empty polls: 5s → 10s → 30s → 60s, reset on job found.
 */

import { SupabaseClient } from '@supabase/supabase-js';
import type { BookingJob } from '@class-sniper/shared';

export interface PollerOptions {
  workerId: string;
  concurrencyLimit?: number;
  onJob: (job: BookingJob) => Promise<void>;
}

export class JobPoller {
  private supabase: SupabaseClient;
  private workerId: string;
  private concurrencyLimit: number;
  private onJob: (job: BookingJob) => Promise<void>;
  private activeJobs = 0;
  private running = false;
  private backoffMs = 5000;

  private static readonly MIN_POLL = 5000;
  private static readonly BACKOFF_STEPS = [5000, 10000, 30000, 60000];

  constructor(supabase: SupabaseClient, opts: PollerOptions) {
    this.supabase = supabase;
    this.workerId = opts.workerId;
    this.concurrencyLimit = opts.concurrencyLimit ?? 2;
    this.onJob = opts.onJob;
  }

  get activeJobCount(): number {
    return this.activeJobs;
  }

  start(): void {
    if (this.running) return;
    this.running = true;
    console.log(`[poller] Started (worker=${this.workerId}, concurrency=${this.concurrencyLimit})`);
    this.poll();
  }

  stop(): void {
    this.running = false;
    console.log('[poller] Stopped');
  }

  private async poll(): Promise<void> {
    while (this.running) {
      if (this.activeJobs >= this.concurrencyLimit) {
        await this.sleep(JobPoller.MIN_POLL);
        continue;
      }

      try {
        const job = await this.claimJob();

        if (job) {
          this.backoffMs = JobPoller.MIN_POLL; // reset backoff
          this.activeJobs++;
          console.log(`[poller] Claimed job ${job.id} (active: ${this.activeJobs})`);

          // Process in background — don't await
          this.processJob(job);
        } else {
          this.increaseBackoff();
          await this.sleep(this.backoffMs);
        }
      } catch (err) {
        console.error('[poller] Error:', err);
        await this.sleep(this.backoffMs);
      }
    }
  }

  private async claimJob(): Promise<BookingJob | null> {
    const { data, error } = await this.supabase.rpc('claim_next_job', {
      p_worker_id: this.workerId,
    });

    if (error) {
      console.error('[poller] claim_next_job error:', error.message);
      return null;
    }

    return data as BookingJob | null;
  }

  private async processJob(job: BookingJob): Promise<void> {
    try {
      await this.onJob(job);
    } catch (err) {
      console.error(`[poller] Job ${job.id} uncaught error:`, err);
    } finally {
      this.activeJobs--;
    }
  }

  private increaseBackoff(): void {
    const idx = JobPoller.BACKOFF_STEPS.indexOf(this.backoffMs);
    if (idx < JobPoller.BACKOFF_STEPS.length - 1) {
      this.backoffMs = JobPoller.BACKOFF_STEPS[idx + 1];
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
