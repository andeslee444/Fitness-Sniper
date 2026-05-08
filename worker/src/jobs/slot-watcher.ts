/**
 * Slot Watcher — polls Arketa appointments API for newly-available time slots.
 *
 * Saint NYC uses Arketa's "privates/appointments" system. Slots are added
 * manually at unpredictable times. This watcher polls every 60s, diffs
 * against known slots, and creates booking_jobs with scheduled_for=NOW()
 * for instant pickup by the existing poller/processor pipeline.
 *
 * Unlike the old classes-based watcher, this uses the real Cloud Run API:
 *   GET {base}/{partnerId}/services/{serviceId}/availableTimes?date=...
 */

import { query } from '../db.js';
import {
  addDaysToDateString,
  dateStringInTimeZone,
  dayOfWeekForDateString,
  parseTime,
  STUDIOS,
} from '@fitness-sniper/shared';
import {
  fetchArketaAvailableTimes,
  type ArketaSlot,
} from './arketa-slot-source.js';

const DEFAULT_POLL_INTERVAL_MS = 60_000; // 60 seconds
const TARGET_REFRESH_INTERVAL_MS = 5 * 60_000; // 5 minutes
const CLEANUP_INTERVAL_MS = 60 * 60_000; // 1 hour
const MAX_DAYS_AHEAD = 21; // Check up to 21 days ahead (matches Arketa bookNotBefore policy)

interface SnipeTarget {
  id: string;
  user_id: string;
  target_type: 'recurring' | 'one_time';
  day_of_week: number | null;
  time: string | null; // null = any time (Arketa auto-snipe)
  target_date: string | null;
  studio_slug: string;
  location_id: string;
}

interface WatchedStudio {
  studioSlug: string;
  partnerId: string;
  serviceId: string;
  locationId: string;
}

export class SlotWatcher {
  private pollInterval: NodeJS.Timeout | null = null;
  private targetRefreshInterval: NodeJS.Timeout | null = null;
  private cleanupInterval: NodeJS.Timeout | null = null;
  private running = false;

  /** Set of known slot keys — used for delta detection */
  private knownSlotKeys = new Set<string>();

  /** Cached snipe targets for Arketa studios */
  private targets: SnipeTarget[] = [];

  /** Arketa studio/location pairs to watch (derived from targets) */
  private watchedStudios: WatchedStudio[] = [];

  private pollIntervalMs: number;

  constructor() {
    this.pollIntervalMs = parseInt(
      process.env.SLOT_WATCHER_INTERVAL_MS || String(DEFAULT_POLL_INTERVAL_MS),
      10,
    );
  }

  async start(): Promise<void> {
    this.running = true;

    // Load targets first to know which studios to watch
    await this.refreshTargets();

    if (this.watchedStudios.length === 0) {
      console.log('[slot-watcher] No Arketa targets found — will check again in 5 min');
    }

    // Seed known slot keys from first fetch (no new-slot detection on boot)
    await this.seedKnownSlots();

    // Start poll loop
    this.pollInterval = setInterval(() => this.poll(), this.pollIntervalMs);

    // Refresh targets every 5 min
    this.targetRefreshInterval = setInterval(
      () => this.refreshTargets(),
      TARGET_REFRESH_INTERVAL_MS,
    );

    // Cleanup old keys every hour
    this.cleanupInterval = setInterval(() => this.cleanupKnownKeys(), CLEANUP_INTERVAL_MS);

    console.log(
      `[slot-watcher] Started (poll every ${this.pollIntervalMs / 1000}s, ${this.watchedStudios.length} studio(s))`,
    );
  }

  stop(): void {
    this.running = false;
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    if (this.targetRefreshInterval) {
      clearInterval(this.targetRefreshInterval);
      this.targetRefreshInterval = null;
    }
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    console.log('[slot-watcher] Stopped');
  }

  /**
   * Determine which dates to check based on active targets.
   * - one_time targets → check the specific target_date
   * - recurring targets → check the next N occurrences of that day_of_week
   */
  private getDatesToCheck(studioSlug: string, locationId: string): string[] {
    const dates = new Set<string>();
    const now = new Date();
    const today = dateStringInTimeZone(now);

    const relevantTargets = this.targets.filter(
      (t) => t.studio_slug === studioSlug && t.location_id === locationId,
    );

    for (const target of relevantTargets) {
      if (target.target_type === 'one_time' && target.target_date) {
        // Only check if in the future (Postgres may return Date objects)
        const raw = target.target_date as string | Date;
        const dateStr = typeof raw === 'object' && raw instanceof Date
          ? raw.toISOString().split('T')[0]
          : String(raw).split('T')[0];
        if (dateStr >= today) {
          dates.add(dateStr);
        }
      } else if (target.target_type === 'recurring' && target.day_of_week !== null) {
        // Find next occurrences of this day_of_week within MAX_DAYS_AHEAD
        for (let d = 0; d < MAX_DAYS_AHEAD; d++) {
          const dateStr = addDaysToDateString(today, d);
          const dow = dayOfWeekForDateString(dateStr);
          if (dow === target.day_of_week) {
            dates.add(dateStr);
          }
        }
      }
    }

    return [...dates].sort();
  }

  /**
   * Seed known slot keys from the first API fetch — prevents restart flood.
   */
  private async seedKnownSlots(): Promise<void> {
    let totalSeeded = 0;

    for (const ws of this.watchedStudios) {
      try {
        const dates = this.getDatesToCheck(ws.studioSlug, ws.locationId);
        for (const date of dates) {
          const slots = await fetchArketaAvailableTimes(
            ws.partnerId,
            ws.serviceId,
            ws.locationId,
            date,
          );
          for (const slot of slots) {
            this.knownSlotKeys.add(slot.slotKey);
          }
          totalSeeded += slots.length;
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[slot-watcher] Seed failed for ${ws.studioSlug}: ${msg}`);
      }
    }

    console.log(
      `[slot-watcher] Seeded ${totalSeeded} known slots (${this.knownSlotKeys.size} unique keys)`,
    );
  }

  /**
   * One poll tick — fetch, diff, match, create jobs.
   */
  private async poll(): Promise<void> {
    if (!this.running) return;

    for (const ws of this.watchedStudios) {
      try {
        await this.pollStudio(ws);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[slot-watcher] Poll error for ${ws.studioSlug}: ${msg}`);
      }
    }
  }

  private async pollStudio(ws: WatchedStudio): Promise<void> {
    const dates = this.getDatesToCheck(ws.studioSlug, ws.locationId);
    if (dates.length === 0) return;

    const allSlots: ArketaSlot[] = [];
    for (const date of dates) {
      const slots = await fetchArketaAvailableTimes(
        ws.partnerId,
        ws.serviceId,
        ws.locationId,
        date,
      );
      allSlots.push(...slots);
    }

    // Diff: find new slots not in known set
    const newSlots: ArketaSlot[] = [];
    for (const slot of allSlots) {
      if (!this.knownSlotKeys.has(slot.slotKey)) {
        newSlots.push(slot);
      }
    }

    // Add ALL fetched slot keys to known set
    for (const slot of allSlots) {
      this.knownSlotKeys.add(slot.slotKey);
    }

    if (newSlots.length === 0) return;

    console.log(`[slot-watcher] Found ${newSlots.length} NEW slot(s) for ${ws.studioSlug}`);

    // Upsert new slots into class_schedules
    await this.upsertClasses(ws.studioSlug, ws.locationId, newSlots);

    // Match against targets and create jobs
    await this.matchAndCreateJobs(ws.studioSlug, ws.locationId, newSlots);
  }

  /**
   * Refresh snipe targets from DB — picks up new/toggled targets.
   */
  private async refreshTargets(): Promise<void> {
    try {
      const { rows } = await query<SnipeTarget>(
        `SELECT id, user_id, target_type, day_of_week, time, target_date, studio_slug, location_id
         FROM snipe_targets
         WHERE enabled = true`,
      );

      // Filter to Arketa-platform studios only
      this.targets = rows.filter((t) => {
        const studio = STUDIOS[t.studio_slug];
        return studio?.platform === 'arketa';
      });

      // Derive watched studios from targets
      const pairSet = new Set<string>();
      const watched: WatchedStudio[] = [];

      for (const t of this.targets) {
        const key = `${t.studio_slug}:${t.location_id}`;
        if (pairSet.has(key)) continue;
        pairSet.add(key);

        const studio = STUDIOS[t.studio_slug];
        if (!studio?.partnerId || !studio?.serviceId) continue;

        watched.push({
          studioSlug: t.studio_slug,
          partnerId: studio.partnerId,
          serviceId: studio.serviceId,
          locationId: t.location_id,
        });
      }

      this.watchedStudios = watched;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`[slot-watcher] Failed to refresh targets: ${msg}`);
    }
  }

  /**
   * Match new slots against cached targets and create booking_jobs.
   */
  private async matchAndCreateJobs(
    studioSlug: string,
    locationId: string,
    newSlots: ArketaSlot[],
  ): Promise<void> {
    // Filter targets for this studio + location
    const relevantTargets = this.targets.filter(
      (t) => t.studio_slug === studioSlug && t.location_id === locationId,
    );

    if (relevantTargets.length === 0) return;

    for (const slot of newSlots) {
      const etDow = dayOfWeekForDateString(slot.classDate);

      for (const target of relevantTargets) {
        if (!this.isTargetMatch(target, slot, etDow, slot.classDate)) continue;

        // Dedup check: skip if booking_jobs already has a row for this (target_id, class_date)
        const { rows: existingJobs } = await query(
          `SELECT id FROM booking_jobs
           WHERE target_id = $1
             AND (
               (class_datetime >= $2 AND class_datetime <= $3)
               OR (class_datetime IS NULL AND scheduled_for >= $2 AND scheduled_for <= $3)
             )
             AND status IN ('pending', 'claimed', 'running', 'success')`,
          [target.id, `${slot.classDate}T00:00:00Z`, `${slot.classDate}T23:59:59Z`],
        );

        if (existingJobs.length > 0) continue;

        // Create booking job with scheduled_for = NOW() for immediate pickup
        const classDatetime = new Date(slot.startTime * 1000).toISOString();
        try {
          await query(
            `INSERT INTO booking_jobs (user_id, target_id, status, scheduled_for, class_datetime)
             VALUES ($1, $2, 'pending', NOW(), $3)`,
            [target.user_id, target.id, classDatetime],
          );
          console.log(
            `[slot-watcher] Match: target ${target.id} → created job for ${slot.classDate} ${slot.classTime}`,
          );
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          console.error(`[slot-watcher] Failed to create job for target ${target.id}: ${msg}`);
        }
      }
    }
  }

  /**
   * Check if a target matches a slot by type (recurring vs one_time) and optionally time.
   * When target.time is null, matches ANY slot on the matching day (Arketa auto-snipe).
   */
  private isTargetMatch(
    target: SnipeTarget,
    slot: ArketaSlot,
    slotDayOfWeek: number,
    slotDateStr: string,
  ): boolean {
    // If target has a specific time, compare it
    if (target.time) {
      const targetParsed = parseTime(target.time);
      const slotParsed = parseTime(slot.classTime);

      if (!targetParsed || !slotParsed) return false;
      if (targetParsed.hours24 !== slotParsed.hours24 || targetParsed.minutes !== slotParsed.minutes) {
        return false;
      }
    }
    // If target.time is null → match any time on the matching day

    if (target.target_type === 'recurring') {
      return target.day_of_week === slotDayOfWeek;
    }

    // one_time: match target_date (Postgres may return Date objects)
    if (target.target_type === 'one_time' && target.target_date) {
      const raw = target.target_date as string | Date;
      const targetDateStr = typeof raw === 'object' && raw instanceof Date
        ? raw.toISOString().split('T')[0]
        : String(raw).split('T')[0];
      return targetDateStr === slotDateStr;
    }

    return false;
  }

  /**
   * Upsert new slots into class_schedules (mirrors ScheduleScraper pattern).
   */
  private async upsertClasses(
    studioSlug: string,
    locationId: string,
    slots: ArketaSlot[],
  ): Promise<void> {
    for (const slot of slots) {
      try {
        await query(
          `INSERT INTO class_schedules
             (studio_slug, location_id, class_date, class_time, class_name,
              instructor, duration_minutes, available, spots_remaining, scraped_at, booking_opens_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), $10)
           ON CONFLICT (studio_slug, location_id, class_date, class_time, class_name)
           DO UPDATE SET
             duration_minutes = EXCLUDED.duration_minutes,
             available = EXCLUDED.available,
             spots_remaining = EXCLUDED.spots_remaining,
             scraped_at = NOW()`,
          [
            studioSlug,
            locationId,
            slot.classDate,
            slot.classTime,
            'PERSONAL SAUNA & ICE BATH',
            null, // instructor
            60, // duration
            true, // available (these are open slots from the API)
            1, // spots_remaining (private sessions = 1 spot)
            null, // booking_opens_at
          ],
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[slot-watcher] Upsert failed for ${slot.classDate} ${slot.classTime}: ${msg}`);
      }
    }
  }

  /**
   * Prune known keys — rebuild from fresh API data to remove expired slots.
   */
  private async cleanupKnownKeys(): Promise<void> {
    if (this.watchedStudios.length === 0) return;

    const freshKeys = new Set<string>();
    for (const ws of this.watchedStudios) {
      try {
        const dates = this.getDatesToCheck(ws.studioSlug, ws.locationId);
        for (const date of dates) {
          const slots = await fetchArketaAvailableTimes(
            ws.partnerId,
            ws.serviceId,
            ws.locationId,
            date,
          );
          for (const slot of slots) {
            freshKeys.add(slot.slotKey);
          }
        }
      } catch {
        // On error, keep existing keys to avoid false positives
        return;
      }
    }

    const oldSize = this.knownSlotKeys.size;
    this.knownSlotKeys = freshKeys;
    const pruned = oldSize - freshKeys.size;
    if (pruned > 0) {
      console.log(`[slot-watcher] Cleanup: pruned ${pruned} expired keys (${freshKeys.size} remaining)`);
    }
  }
}
