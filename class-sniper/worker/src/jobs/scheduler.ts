/**
 * Job Scheduler — creates booking_jobs from snipe_targets
 *
 * Runs on cron (every 15 min): scans all enabled targets, calculates
 * next class date, and creates a pending job if within the booking window
 * and no existing job already covers it.
 */

import { SupabaseClient } from '@supabase/supabase-js';
import cron from 'node-cron';

const BOOKING_WINDOW_DAYS = 7;

export class JobScheduler {
  private supabase: SupabaseClient;
  private task: cron.ScheduledTask | null = null;

  constructor(supabase: SupabaseClient) {
    this.supabase = supabase;
  }

  /**
   * Start the scheduler — runs every 15 minutes
   */
  start(): void {
    // Run immediately on start
    this.scan();
    // Then every 15 minutes
    this.task = cron.schedule('*/15 * * * *', () => this.scan());
    console.log('[scheduler] Started (every 15 min)');
  }

  stop(): void {
    if (this.task) {
      this.task.stop();
      this.task = null;
    }
    console.log('[scheduler] Stopped');
  }

  async scan(): Promise<void> {
    console.log(`[scheduler] Scanning targets at ${new Date().toISOString()}`);

    // Fetch all enabled targets
    const { data: targets, error } = await this.supabase
      .from('snipe_targets')
      .select('*')
      .eq('enabled', true);

    if (error || !targets) {
      console.error('[scheduler] Error fetching targets:', error?.message);
      return;
    }

    console.log(`[scheduler] Found ${targets.length} enabled targets`);

    for (const target of targets) {
      try {
        await this.processTarget(target);
      } catch (err) {
        console.error(`[scheduler] Error processing target ${target.id}:`, err);
      }
    }
  }

  private async processTarget(target: {
    id: string;
    user_id: string;
    day_of_week: number;
    time: string;
    studio_slug: string;
    location_id: string;
  }): Promise<void> {
    const nextClass = getNextClassDate(target.day_of_week, target.time);

    if (!isInBookingWindow(nextClass, BOOKING_WINDOW_DAYS)) {
      return; // Not yet in booking window
    }

    // Check if a job already exists for this target + date
    const classDateStr = nextClass.toISOString().split('T')[0];
    const { data: existingJobs } = await this.supabase
      .from('booking_jobs')
      .select('id, status')
      .eq('target_id', target.id)
      .gte('scheduled_for', `${classDateStr}T00:00:00Z`)
      .lte('scheduled_for', `${classDateStr}T23:59:59Z`)
      .in('status', ['pending', 'claimed', 'running', 'success']);

    if (existingJobs && existingJobs.length > 0) {
      return; // Job already exists
    }

    // Create new booking job
    const { error } = await this.supabase.from('booking_jobs').insert({
      user_id: target.user_id,
      target_id: target.id,
      status: 'pending',
      scheduled_for: nextClass.toISOString(),
    });

    if (error) {
      console.error(`[scheduler] Failed to create job for target ${target.id}:`, error.message);
    } else {
      console.log(
        `[scheduler] Created job: ${target.studio_slug} ${target.location_id} ${target.time} on ${classDateStr}`,
      );
    }
  }
}

// ============================================================
// Date Utilities (ported from archive/src/auto-sniper.ts)
// ============================================================

export function getNextClassDate(dayOfWeek: number, time: string): Date {
  const now = new Date();
  const [timePart, ampm] = time.split(' ');
  let [hours, minutes] = timePart.split(':').map(Number);

  if (ampm?.toUpperCase() === 'PM' && hours !== 12) hours += 12;
  if (ampm?.toUpperCase() === 'AM' && hours === 12) hours = 0;

  const target = new Date(now);
  target.setHours(hours, minutes || 0, 0, 0);

  const daysUntil = (dayOfWeek - now.getDay() + 7) % 7;
  target.setDate(target.getDate() + daysUntil);

  if (daysUntil === 0 && target <= now) {
    target.setDate(target.getDate() + 7);
  }

  return target;
}

export function isInBookingWindow(classDate: Date, windowDays: number): boolean {
  const now = new Date();
  const windowEnd = new Date(now);
  windowEnd.setDate(windowEnd.getDate() + windowDays);

  return classDate >= now && classDate <= windowEnd;
}
