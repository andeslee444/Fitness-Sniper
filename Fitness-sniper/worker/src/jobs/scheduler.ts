/**
 * Job Scheduler — creates booking_jobs from snipe_targets
 *
 * Runs on cron (every 15 min): scans all enabled targets, calculates
 * next class date, and creates a pending job if within the booking window
 * and no existing job already covers it.
 */

import { query } from '../db.js';
import { parseTime, STUDIOS } from '@fitness-sniper/shared';
import cron from 'node-cron';

const DEFAULT_BOOKING_WINDOW_DAYS = 7;

interface TargetRow {
  id: string;
  user_id: string;
  target_type: 'recurring' | 'one_time';
  day_of_week: number | null;
  time: string | null;
  target_date: string | null;
  studio_slug: string;
  location_id: string;
}

export class JobScheduler {
  private task: cron.ScheduledTask | null = null;

  private staleTask: cron.ScheduledTask | null = null;

  /**
   * Start the scheduler — runs every 15 minutes
   */
  start(): void {
    // Run immediately on start
    this.scan();
    // Then every 15 minutes
    this.task = cron.schedule('*/15 * * * *', () => this.scan());

    // Stale job recovery — every 5 minutes
    this.staleTask = cron.schedule('*/5 * * * *', () => this.recoverStaleJobs());
    console.log('[scheduler] Started (every 15 min + stale recovery every 5 min)');
  }

  stop(): void {
    if (this.task) {
      this.task.stop();
      this.task = null;
    }
    if (this.staleTask) {
      this.staleTask.stop();
      this.staleTask = null;
    }
    console.log('[scheduler] Stopped');
  }

  async scan(): Promise<void> {
    console.log(`[scheduler] Scanning targets at ${new Date().toISOString()}`);

    // Fetch all enabled targets
    const { rows: targets } = await query<TargetRow>(
      'SELECT * FROM snipe_targets WHERE enabled = true',
    );

    console.log(`[scheduler] Found ${targets.length} enabled targets`);

    for (const target of targets) {
      try {
        await this.processTarget(target);
      } catch (err) {
        console.error(`[scheduler] Error processing target ${target.id}:`, err);
      }
    }

    // Auto-disable completed one-time targets
    await this.disableCompletedOneTimeTargets();
  }

  private async processTarget(target: TargetRow): Promise<void> {
    const studioConfig = STUDIOS[target.studio_slug];
    if (!studioConfig) {
      console.warn(`[scheduler] Unknown studio '${target.studio_slug}' in target ${target.id} — skipping`);
      return;
    }

    // Arketa studios are handled by the SlotWatcher (unpredictable slot drops)
    if (studioConfig.platform === 'arketa') return;

    // Non-Arketa targets always require a time
    if (!target.time) return;

    let classDate: Date;

    if (target.target_type === 'one_time') {
      if (!target.target_date) return;

      classDate = parseTargetDate(target.target_date, target.time);

      // If the date has already passed, disable the target
      if (classDate < new Date()) {
        await query(
          'UPDATE snipe_targets SET enabled = false, updated_at = NOW() WHERE id = $1',
          [target.id],
        );
        console.log(`[scheduler] Auto-disabled past one-time target ${target.id}`);
        return;
      }
    } else {
      // Recurring
      if (target.day_of_week === null) return;
      classDate = getNextClassDate(target.day_of_week, target.time);
    }

    // Only create jobs for future classes
    if (classDate <= new Date()) return;

    const windowDays = studioConfig?.bookingWindowDays ?? DEFAULT_BOOKING_WINDOW_DAYS;

    // Check if a job already exists for this target + class date
    // Use class_datetime (not scheduled_for) for dedup since scheduled_for is now booking open time
    const classDateStr = classDate.toISOString().split('T')[0];
    const { rows: existingJobs } = await query(
      `SELECT id, status FROM booking_jobs
       WHERE target_id = $1
         AND (
           (class_datetime >= $2 AND class_datetime <= $3)
           OR (class_datetime IS NULL AND scheduled_for >= $2 AND scheduled_for <= $3)
         )
         AND status IN ('pending', 'claimed', 'running', 'success')`,
      [target.id, `${classDateStr}T00:00:00Z`, `${classDateStr}T23:59:59Z`],
    );

    if (existingJobs.length > 0) {
      return; // Job already exists
    }

    // Look up booking_opens_at from scraped schedule data
    let scheduledFor: Date;
    try {
      const { rows: scheduleRows } = await query<{ booking_opens_at: string }>(
        `SELECT booking_opens_at FROM class_schedules
         WHERE studio_slug = $1 AND location_id = $2
           AND class_date = $3 AND class_time = $4
           AND booking_opens_at IS NOT NULL
         LIMIT 1`,
        [target.studio_slug, target.location_id, classDateStr, target.time],
      );

      if (scheduleRows.length > 0 && scheduleRows[0].booking_opens_at) {
        scheduledFor = new Date(scheduleRows[0].booking_opens_at);
        console.log(`[scheduler] Using booking_opens_at for ${target.studio_slug}: ${scheduledFor.toISOString()}`);
      } else {
        // Fallback: classDate minus bookingWindowDays
        scheduledFor = new Date(classDate);
        scheduledFor.setDate(scheduledFor.getDate() - windowDays);
        console.log(`[scheduler] Fallback scheduled_for (class - ${windowDays}d): ${scheduledFor.toISOString()}`);
      }
    } catch {
      scheduledFor = new Date(classDate);
      scheduledFor.setDate(scheduledFor.getDate() - windowDays);
    }

    // If scheduled_for is in the past, set to now (execute immediately)
    const now = new Date();
    if (scheduledFor < now) {
      scheduledFor = now;
    }

    // Create new booking job with both scheduled_for (booking open time) and class_datetime
    try {
      await query(
        `INSERT INTO booking_jobs (user_id, target_id, status, scheduled_for, class_datetime)
         VALUES ($1, $2, 'pending', $3, $4)`,
        [target.user_id, target.id, scheduledFor.toISOString(), classDate.toISOString()],
      );
      console.log(
        `[scheduler] Created job: ${target.studio_slug} ${target.location_id} ${target.time} on ${classDateStr} (execute at ${scheduledFor.toISOString()})`,
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error(`[scheduler] Failed to create job for target ${target.id}:`, message);
    }
  }

  /**
   * Recover stale jobs — reset jobs stuck in 'claimed' for >30 min or 'running' for >60 min
   */
  private async recoverStaleJobs(): Promise<void> {
    try {
      const { rowCount } = await query(
        `UPDATE booking_jobs
         SET status = 'pending', claimed_at = NULL, claimed_by = NULL, attempts = COALESCE(attempts, 0) + 1, updated_at = NOW()
         WHERE (
           (status = 'claimed' AND claimed_at < NOW() - INTERVAL '30 minutes')
           OR
           (status = 'running' AND updated_at < NOW() - INTERVAL '60 minutes')
         )
         AND COALESCE(attempts, 0) < 3`,
      );
      if (rowCount && rowCount > 0) {
        console.log(`[scheduler] Recovered ${rowCount} stale job(s)`);
      }
    } catch (err) {
      console.error('[scheduler] Stale job recovery failed:', err);
    }
  }

  /**
   * Auto-disable one-time targets that have a terminal job (success or failed)
   */
  private async disableCompletedOneTimeTargets(): Promise<void> {
    const { rowCount } = await query(
      `UPDATE snipe_targets st
       SET enabled = false, updated_at = NOW()
       WHERE st.target_type = 'one_time'
         AND st.enabled = true
         AND EXISTS (
           SELECT 1 FROM booking_jobs bj
           WHERE bj.target_id = st.id
             AND bj.status IN ('success', 'failed')
         )`,
    );
    if (rowCount && rowCount > 0) {
      console.log(`[scheduler] Auto-disabled ${rowCount} completed one-time target(s)`);
    }
  }
}

// ============================================================
// Date Utilities (ported from archive/src/auto-sniper.ts)
// ============================================================

export function getNextClassDate(dayOfWeek: number, time: string): Date {
  const parsed = parseTime(time);
  const hours = parsed?.hours24 ?? 0;
  const minutes = parsed?.minutes ?? 0;

  // Get today's date in America/New_York (not server local time)
  const etTodayStr = new Date().toLocaleDateString('en-CA', {
    timeZone: 'America/New_York',
  }); // "YYYY-MM-DD"
  const [year, month, day] = etTodayStr.split('-').map(Number);

  // Build date at class time using explicit year/month/day
  const target = new Date(year, month - 1, day, hours, minutes, 0, 0);

  // Get day of week from the ET date string (noon avoids DST edge case)
  const etDayOfWeek = new Date(etTodayStr + 'T12:00:00').getDay();

  const daysUntil = (dayOfWeek - etDayOfWeek + 7) % 7;
  target.setDate(target.getDate() + daysUntil);

  // If same day and time has already passed in ET, push to next week
  if (daysUntil === 0) {
    const etNowStr = new Date().toLocaleTimeString('en-US', {
      timeZone: 'America/New_York',
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
    });
    const [etHour, etMin] = etNowStr.split(':').map(Number);
    if (etHour > hours || (etHour === hours && etMin >= minutes)) {
      target.setDate(target.getDate() + 7);
    }
  }

  return target;
}

/**
 * Parse a target_date ("YYYY-MM-DD") + time ("6:00 AM") into a Date
 */
export function parseTargetDate(dateStr: string | Date, time: string): Date {
  // Postgres may return a Date object instead of a string
  const str = dateStr instanceof Date ? dateStr.toISOString().split('T')[0] : dateStr;
  const [year, month, day] = str.split('-').map(Number);
  const parsed = parseTime(time);
  const hours = parsed?.hours24 ?? 0;
  const minutes = parsed?.minutes ?? 0;

  return new Date(year, month - 1, day, hours, minutes, 0, 0);
}

export function isInBookingWindow(classDate: Date, windowDays: number): boolean {
  const etTodayStr = new Date().toLocaleDateString('en-CA', {
    timeZone: 'America/New_York',
  });
  const [year, month, day] = etTodayStr.split('-').map(Number);
  const now = new Date(year, month - 1, day, 0, 0, 0, 0);
  const windowEnd = new Date(now);
  windowEnd.setDate(windowEnd.getDate() + windowDays);

  return classDate >= now && classDate <= windowEnd;
}
