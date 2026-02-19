/**
 * Slot Watcher — polls Arketa API for newly-added class slots
 *
 * Saint NYC adds sauna/ice bath slots manually at unpredictable times.
 * This watcher polls every 60s, diffs against known classes, and creates
 * booking_jobs with scheduled_for=NOW() for instant pickup by the existing
 * poller/processor pipeline.
 */

import { query } from '../db.js';
import { STUDIOS, parseTime } from '@fitness-sniper/shared';
import { fetchArketaSlots, type ArketaSlot } from './arketa-slot-source.js';

const DEFAULT_POLL_INTERVAL_MS = 60_000; // 60 seconds
const TARGET_REFRESH_INTERVAL_MS = 5 * 60_000; // 5 minutes
const CLEANUP_INTERVAL_MS = 60 * 60_000; // 1 hour

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
  widgetName: string;
  locationId: string;
}

export class SlotWatcher {
  private pollInterval: NodeJS.Timeout | null = null;
  private targetRefreshInterval: NodeJS.Timeout | null = null;
  private cleanupInterval: NodeJS.Timeout | null = null;
  private running = false;

  /** Set of known Arketa class IDs — used for delta detection */
  private knownClassIds = new Set<string>();

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

    // Seed known class IDs from first fetch (no new-class detection on boot)
    await this.seedKnownClasses();

    // Start poll loop
    this.pollInterval = setInterval(() => this.poll(), this.pollIntervalMs);

    // Refresh targets every 5 min
    this.targetRefreshInterval = setInterval(
      () => this.refreshTargets(),
      TARGET_REFRESH_INTERVAL_MS,
    );

    // Cleanup old IDs every hour
    this.cleanupInterval = setInterval(() => this.cleanupKnownIds(), CLEANUP_INTERVAL_MS);

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
   * Seed known class IDs from the first API fetch — prevents restart flood.
   */
  private async seedKnownClasses(): Promise<void> {
    let totalSeeded = 0;

    for (const ws of this.watchedStudios) {
      try {
        const slots = await fetchArketaSlots(ws.widgetName, ws.locationId);
        for (const slot of slots) {
          this.knownClassIds.add(slot.arketaId);
        }
        totalSeeded += slots.length;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[slot-watcher] Seed failed for ${ws.studioSlug}: ${msg}`);
      }
    }

    console.log(`[slot-watcher] Seeded ${totalSeeded} known classes (${this.knownClassIds.size} unique IDs)`);
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
    const slots = await fetchArketaSlots(ws.widgetName, ws.locationId);

    // Diff: find new classes not in known set
    const newSlots: ArketaSlot[] = [];
    for (const slot of slots) {
      if (!this.knownClassIds.has(slot.arketaId)) {
        newSlots.push(slot);
      }
    }

    // Add ALL fetched IDs to known set (including existing ones — idempotent)
    for (const slot of slots) {
      this.knownClassIds.add(slot.arketaId);
    }

    if (newSlots.length === 0) {
      // Quiet log — don't spam on every tick
      return;
    }

    console.log(`[slot-watcher] Found ${newSlots.length} NEW class(es) for ${ws.studioSlug}`);

    // Upsert new classes into class_schedules
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
        if (!studio?.widgetName) continue;

        watched.push({
          studioSlug: t.studio_slug,
          widgetName: studio.widgetName,
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
      // Get day of week in ET
      const slotDate = new Date(slot.startTime * 1000);
      const etDateStr = slotDate.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
      const etDow = new Date(
        slotDate.toLocaleString('en-US', { timeZone: 'America/New_York' }),
      ).getDay();

      for (const target of relevantTargets) {
        if (!this.isTargetMatch(target, slot, etDow, etDateStr)) continue;

        // Dedup check: skip if booking_jobs already has a row for this (target_id, class_date)
        const { rows: existingJobs } = await query(
          `SELECT id FROM booking_jobs
           WHERE target_id = $1
             AND (
               (class_datetime >= $2 AND class_datetime <= $3)
               OR (class_datetime IS NULL AND scheduled_for >= $2 AND scheduled_for <= $3)
             )
             AND status IN ('pending', 'claimed', 'running', 'success')`,
          [target.id, `${etDateStr}T00:00:00Z`, `${etDateStr}T23:59:59Z`],
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
            `[slot-watcher] Match: target ${target.id} → created job for ${slot.name} on ${etDateStr} ${slot.classTime}`,
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

    // one_time: match target_date
    if (target.target_type === 'one_time' && target.target_date) {
      return target.target_date === slotDateStr;
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
      const calcSpots = Math.max(0, slot.maxCapacity - slot.totalBooked);
      const spotsRemaining = slot.isBookable ? Math.max(1, calcSpots) : calcSpots;
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
            slot.name,
            null, // instructor
            slot.duration,
            slot.isBookable,
            spotsRemaining,
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
   * Prune known IDs for classes that have already passed (prevents unbounded growth).
   * Since we don't store timestamps per ID, we re-fetch and rebuild the set.
   */
  private async cleanupKnownIds(): Promise<void> {
    if (this.watchedStudios.length === 0) return;

    const freshIds = new Set<string>();
    for (const ws of this.watchedStudios) {
      try {
        const slots = await fetchArketaSlots(ws.widgetName, ws.locationId);
        for (const slot of slots) {
          freshIds.add(slot.arketaId);
        }
      } catch {
        // On error, keep existing IDs for this studio to avoid false positives
        return;
      }
    }

    const oldSize = this.knownClassIds.size;
    this.knownClassIds = freshIds;
    const pruned = oldSize - freshIds.size;
    if (pruned > 0) {
      console.log(`[slot-watcher] Cleanup: pruned ${pruned} expired IDs (${freshIds.size} remaining)`);
    }
  }
}
