/**
 * Schedule Scraper — cron job that auto-scrapes class schedules
 *
 * Runs at 2 AM and 2 PM ET (+ once 30s after boot). For each studio/location
 * pair that has active snipe targets, tries the HTTP API first (fast, no browser),
 * then falls back to Playwright browser scraping if the API fails.
 *
 * Results are upserted into class_schedules; old data is cleaned up automatically.
 */

import cron from 'node-cron';
import { query } from '../db.js';
import { STUDIOS } from '@fitness-sniper/shared';
import { fetchClassesFromAPI, type ClassScheduleRow } from '../scrapers/mt-api-client.js';
import { scrapeClassesWithBrowser } from '../scrapers/mt-browser-scraper.js';
import { fetchXpoClassesFromAPI } from '../scrapers/xpo-api-client.js';
import { fetchArketaClassesFromAPI } from '../scrapers/arketa-api-client.js';

const SCRAPE_DAYS_AHEAD = 8; // Scrape 8 days into the future

interface ActivePair {
  studio_slug: string;
  location_id: string;
}

export class ScheduleScraper {
  private task: cron.ScheduledTask | null = null;
  private bootTimeout: NodeJS.Timeout | null = null;

  /**
   * Start the scraper — runs at 2 AM and 2 PM ET, plus 30s after boot
   */
  start(): void {
    // Run 30s after boot to populate initial data
    this.bootTimeout = setTimeout(() => {
      this.scrapeAll().catch((err) =>
        console.error('[schedule-scraper] Boot scrape failed:', err),
      );
    }, 30000);

    // Cron: 2 AM and 2 PM ET
    // Note: node-cron uses system timezone; worker runs in America/New_York
    this.task = cron.schedule('0 2,14 * * *', () => {
      this.scrapeAll().catch((err) =>
        console.error('[schedule-scraper] Cron scrape failed:', err),
      );
    });

    console.log('[schedule-scraper] Started (2 AM + 2 PM ET, boot in 30s)');
  }

  stop(): void {
    if (this.bootTimeout) {
      clearTimeout(this.bootTimeout);
      this.bootTimeout = null;
    }
    if (this.task) {
      this.task.stop();
      this.task = null;
    }
    console.log('[schedule-scraper] Stopped');
  }

  async scrapeAll(): Promise<void> {
    console.log(`[schedule-scraper] Starting scrape at ${new Date().toISOString()}`);

    // 1. Query distinct studio/location pairs from active targets
    const pairs = await this.getActiveStudioLocationPairs();
    if (pairs.length === 0) {
      console.log('[schedule-scraper] No active targets — skipping');
      return;
    }

    console.log(`[schedule-scraper] Found ${pairs.length} active studio/location pair(s)`);

    // 2. Build date range for scraping
    const dates = this.getDateRange(SCRAPE_DAYS_AHEAD);

    // 3. Scrape each pair
    for (const pair of pairs) {
      await this.scrapePair(pair, dates);
    }

    // 4. Cleanup old data
    await this.cleanup();

    console.log('[schedule-scraper] Scrape complete');
  }

  private async getActiveStudioLocationPairs(): Promise<ActivePair[]> {
    const { rows } = await query<ActivePair>(
      `SELECT DISTINCT studio_slug, location_id
       FROM snipe_targets
       WHERE enabled = true AND location_id != ''`,
    );
    return rows;
  }

  private getDateRange(daysAhead: number): string[] {
    const dates: string[] = [];
    const today = new Date();
    for (let i = 0; i < daysAhead; i++) {
      const d = new Date(today);
      d.setDate(d.getDate() + i);
      dates.push(d.toISOString().split('T')[0]);
    }
    return dates;
  }

  private async scrapePair(pair: ActivePair, dates: string[]): Promise<void> {
    const { studio_slug, location_id } = pair;
    const studio = STUDIOS[studio_slug];
    if (!studio) {
      console.warn(`[schedule-scraper] Unknown studio: ${studio_slug}`);
      return;
    }

    const startTime = Date.now();
    let method: 'http_api' | 'browser' = 'http_api';
    let classes: ClassScheduleRow[] = [];
    let errorMessage: string | null = null;

    // Dispatch to the right scraper based on platform
    if (studio.platform === 'xponential') {
      classes = await this.scrapeXponential(studio_slug, location_id, dates, studio.membersDomain);
      if (classes.length === 0) errorMessage = 'Xponential API returned no classes';
    } else if (studio.platform === 'arketa') {
      classes = await this.scrapeArketa(studio_slug, location_id, dates, studio.partnerId || '', studio.serviceId || '');
      if (classes.length === 0) errorMessage = 'Arketa API returned no classes';
    } else {
      // Mariana Tek: try HTTP API first with retry, then browser fallback
      const result = await this.scrapeMarianaTek(studio_slug, location_id, dates, studio.tenant, studio.region);
      classes = result.classes;
      method = result.method;
      errorMessage = result.errorMessage;
    }

    const durationMs = Date.now() - startTime;
    const uniqueDates = new Set(classes.map((c) => c.class_date));

    // Upsert classes into database
    if (classes.length > 0) {
      await this.upsertClasses(classes);
    }

    // Log scrape run
    const status = errorMessage ? 'failed' : classes.length > 0 ? 'success' : 'partial';
    await this.logScrapeRun({
      studio_slug,
      location_id,
      method,
      status,
      classes_found: classes.length,
      days_scraped: uniqueDates.size,
      error_message: errorMessage,
      duration_ms: durationMs,
    });
  }

  private async scrapeXponential(
    studioSlug: string,
    locationSlug: string,
    dates: string[],
    membersDomain?: string,
  ): Promise<ClassScheduleRow[]> {
    const domain = membersDomain || `https://members.${studioSlug}.com`;
    const maxRetries = 2;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        if (attempt > 0) {
          const delay = 1000 * Math.pow(2, attempt - 1);
          console.log(`[schedule-scraper] Retrying Xpo API for ${studioSlug}/${locationSlug} (attempt ${attempt + 1}) after ${delay}ms`);
          await new Promise((r) => setTimeout(r, delay));
        } else {
          console.log(`[schedule-scraper] Trying Xpo API for ${studioSlug}/${locationSlug}`);
        }
        const classes = await fetchXpoClassesFromAPI(
          domain,
          studioSlug,
          locationSlug,
          dates[0],
          dates[dates.length - 1],
        );
        console.log(`[schedule-scraper] Xpo API returned ${classes.length} classes`);
        return classes;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        if (attempt < maxRetries) {
          console.warn(`[schedule-scraper] Xpo API attempt ${attempt + 1} failed: ${msg}`);
          continue;
        }
        console.error(`[schedule-scraper] Xpo API failed after ${maxRetries + 1} attempts: ${msg}`);
      }
    }
    return [];
  }

  private async scrapeArketa(
    studioSlug: string,
    locationId: string,
    dates: string[],
    partnerId: string,
    serviceId: string,
  ): Promise<ClassScheduleRow[]> {
    const maxRetries = 2;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        if (attempt > 0) {
          const delay = 1000 * Math.pow(2, attempt - 1);
          console.log(`[schedule-scraper] Retrying Arketa API for ${studioSlug}/${locationId} (attempt ${attempt + 1}) after ${delay}ms`);
          await new Promise((r) => setTimeout(r, delay));
        } else {
          console.log(`[schedule-scraper] Trying Arketa API for ${studioSlug}/${locationId}`);
        }
        const classes = await fetchArketaClassesFromAPI(
          partnerId,
          serviceId,
          studioSlug,
          locationId,
          dates[0],
          dates[dates.length - 1],
        );
        console.log(`[schedule-scraper] Arketa API returned ${classes.length} classes`);
        return classes;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        if (attempt < maxRetries) {
          console.warn(`[schedule-scraper] Arketa API attempt ${attempt + 1} failed: ${msg}`);
          continue;
        }
        console.error(`[schedule-scraper] Arketa API failed after ${maxRetries + 1} attempts: ${msg}`);
      }
    }
    return [];
  }

  private async scrapeMarianaTek(
    studioSlug: string,
    locationId: string,
    dates: string[],
    tenant: string,
    region?: string,
  ): Promise<{ classes: ClassScheduleRow[]; method: 'http_api' | 'browser'; errorMessage: string | null }> {
    let method: 'http_api' | 'browser' = 'http_api';
    let classes: ClassScheduleRow[] = [];
    let errorMessage: string | null = null;

    const maxRetries = 2;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        if (attempt > 0) {
          const delay = 1000 * Math.pow(2, attempt - 1);
          console.log(`[schedule-scraper] Retrying HTTP API for ${studioSlug}/${locationId} (attempt ${attempt + 1}) after ${delay}ms`);
          await new Promise((r) => setTimeout(r, delay));
        } else {
          console.log(`[schedule-scraper] Trying HTTP API for ${studioSlug}/${locationId}`);
        }
        classes = await fetchClassesFromAPI(
          tenant,
          studioSlug,
          locationId,
          dates[0],
          dates[dates.length - 1],
          region,
        );
        console.log(`[schedule-scraper] HTTP API returned ${classes.length} classes`);
        break;
      } catch (apiErr) {
        const apiMsg = apiErr instanceof Error ? apiErr.message : String(apiErr);
        if (attempt < maxRetries) {
          console.warn(`[schedule-scraper] HTTP API attempt ${attempt + 1} failed for ${studioSlug}/${locationId}: ${apiMsg}`);
          continue;
        }
        console.warn(`[schedule-scraper] HTTP API failed after ${maxRetries + 1} attempts for ${studioSlug}/${locationId}: ${apiMsg}`);

        // Fall back to browser scraping
        method = 'browser';
        try {
          console.log(`[schedule-scraper] Falling back to browser for ${studioSlug}/${locationId}`);
          classes = await scrapeClassesWithBrowser(studioSlug, locationId, dates);
          console.log(`[schedule-scraper] Browser returned ${classes.length} classes`);
        } catch (browserErr) {
          errorMessage = browserErr instanceof Error ? browserErr.message : String(browserErr);
          console.error(`[schedule-scraper] Browser also failed for ${studioSlug}/${locationId}: ${errorMessage}`);
        }
      }
    }

    return { classes, method, errorMessage };
  }

  private async upsertClasses(classes: ClassScheduleRow[]): Promise<void> {
    // Batch upsert using individual INSERT ... ON CONFLICT statements
    for (const c of classes) {
      try {
        await query(
          `INSERT INTO class_schedules
             (studio_slug, location_id, class_date, class_time, class_name,
              instructor, duration_minutes, available, spots_remaining, scraped_at, booking_opens_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), $10)
           ON CONFLICT (studio_slug, location_id, class_date, class_time, class_name)
           DO UPDATE SET
             instructor = EXCLUDED.instructor,
             duration_minutes = EXCLUDED.duration_minutes,
             available = EXCLUDED.available,
             spots_remaining = EXCLUDED.spots_remaining,
             scraped_at = NOW(),
             booking_opens_at = COALESCE(EXCLUDED.booking_opens_at, class_schedules.booking_opens_at)`,
          [
            c.studio_slug,
            c.location_id,
            c.class_date,
            c.class_time,
            c.class_name,
            c.instructor,
            c.duration_minutes,
            c.available,
            c.spots_remaining,
            c.booking_opens_at,
          ],
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[schedule-scraper] Upsert failed for ${c.class_date} ${c.class_time}:`, msg);
      }
    }
  }

  private async logScrapeRun(run: {
    studio_slug: string;
    location_id: string;
    method: string;
    status: string;
    classes_found: number;
    days_scraped: number;
    error_message: string | null;
    duration_ms: number;
  }): Promise<void> {
    try {
      await query(
        `INSERT INTO scrape_runs
           (studio_slug, location_id, method, status, classes_found, days_scraped, error_message, duration_ms)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
        [
          run.studio_slug,
          run.location_id,
          run.method,
          run.status,
          run.classes_found,
          run.days_scraped,
          run.error_message,
          run.duration_ms,
        ],
      );
    } catch (err) {
      console.error('[schedule-scraper] Failed to log scrape run:', err);
    }
  }

  /**
   * Cleanup: remove class schedules older than 2 days
   */
  private async cleanup(): Promise<void> {
    try {
      const { rowCount } = await query(
        `DELETE FROM class_schedules WHERE class_date < CURRENT_DATE - 2`,
      );
      if (rowCount && rowCount > 0) {
        console.log(`[schedule-scraper] Cleaned up ${rowCount} old schedule row(s)`);
      }
    } catch (err) {
      console.error('[schedule-scraper] Cleanup failed:', err);
    }
  }
}
