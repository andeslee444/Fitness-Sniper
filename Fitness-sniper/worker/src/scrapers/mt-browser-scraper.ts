/**
 * Mariana Tek Browser Scraper (Fallback)
 *
 * Launches a stealth Playwright browser, navigates to the studio's schedule page,
 * and extracts class cards from the DOM. Used when the HTTP API is unavailable
 * or requires authentication.
 */

import { Page, Frame, BrowserContext } from 'playwright';
import { STUDIOS, LOCATION_IDS, type StudioConfig } from '@fitness-sniper/shared';
import { launchStealthBrowser } from '../stealth/browser.js';
import { humanDelay, shortDelay } from '../stealth/human-delay.js';
import type { ClassScheduleRow } from './mt-api-client.js';

/**
 * Scrape class schedules for a studio/location over a date range using the browser.
 */
export async function scrapeClassesWithBrowser(
  studioSlug: string,
  locationId: string,
  dates: string[], // ["YYYY-MM-DD", ...]
): Promise<ClassScheduleRow[]> {
  const studio = STUDIOS[studioSlug];
  if (!studio) throw new Error(`Unknown studio: ${studioSlug}`);

  const { context } = await launchStealthBrowser({ headless: true });
  const page = await context.newPage();
  const allClasses: ClassScheduleRow[] = [];

  try {
    // Navigate to schedule
    await navigateToSchedule(page, studio, locationId);

    // Get the content frame (iframe or page itself)
    const frame = await getScheduleFrame(page, studio);
    if (!frame) throw new Error('Schedule frame not found');

    // For each date, navigate and scrape
    for (const dateStr of dates) {
      try {
        const classes = await scrapeDate(frame, page, studio, studioSlug, locationId, dateStr);
        allClasses.push(...classes);
        await humanDelay(1500, 3000);
      } catch (err) {
        console.warn(`[browser-scraper] Failed to scrape ${studioSlug}/${locationId} on ${dateStr}:`, err);
      }
    }
  } finally {
    const browser = context.browser();
    await context.close();
    if (browser) await browser.close();
  }

  return allClasses;
}

async function navigateToSchedule(
  page: Page,
  studio: StudioConfig,
  locationId: string,
): Promise<void> {
  const isDirectSPA = !studio.iframe || studio.iframe === '';

  if (isDirectSPA) {
    const url = `${studio.scheduleUrl}?location_id=${studio.slug}-${locationId}`;
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('table, [class*="schedule"], [class*="class-row"]', {
      timeout: 15000,
    });
  } else {
    const mtLocationId = LOCATION_IDS[studio.slug]?.[locationId] || locationId;
    const url = studio.scheduleUrl.replace('{location}', mtLocationId);
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector(studio.iframe, { timeout: 10000 });
  }

  await humanDelay(1500, 3000);
}

async function getScheduleFrame(
  page: Page,
  studio: StudioConfig,
): Promise<Frame | Page | null> {
  if (!studio.iframe || studio.iframe === '') return page;
  const frameElement = await page.$(studio.iframe);
  if (!frameElement) return null;
  return await frameElement.contentFrame();
}

async function scrapeDate(
  frame: Frame | Page,
  page: Page,
  studio: StudioConfig,
  studioSlug: string,
  locationId: string,
  dateStr: string,
): Promise<ClassScheduleRow[]> {
  // Try to navigate to the specific date using date picker/navigation buttons
  // MT schedules usually have date navigation arrows or a date selector
  const dateObj = new Date(dateStr + 'T12:00:00');
  const monthDay = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  // Try clicking date navigation buttons to reach the target date
  // This is best-effort — the schedule might already show the right date
  try {
    // Look for a date button/link matching the date
    const dateButton = await frame.$(
      `button:has-text("${monthDay}"), a:has-text("${monthDay}"), [aria-label*="${monthDay}"]`,
    );
    if (dateButton) {
      await dateButton.click();
      await shortDelay(1000, 2000);
      await frame.waitForSelector('[class*="class"], [data-testid="class-card"]', {
        timeout: 10000,
      });
    }
  } catch {
    // Date navigation failed, try with what's currently showing
  }

  // Wait for class cards to appear
  try {
    await frame.waitForSelector('[class*="class"], [data-testid="class-card"]', {
      timeout: 10000,
    });
  } catch {
    return []; // No classes found for this date
  }

  // Extract class info from DOM
  const classElements = await frame.$$('[class*="class-row"], [class*="class-card"], article');
  const classes: ClassScheduleRow[] = [];

  for (const el of classElements) {
    const time = await el
      .$eval('[class*="time"]', (e: Element) => e.textContent?.trim() || '')
      .catch(() => '');
    const className = await el
      .$eval(
        '[class*="name"], [class*="title"]',
        (e: Element) => e.textContent?.trim() || '',
      )
      .catch(() => '');
    const instructor = await el
      .$eval(
        '[class*="instructor"], [class*="coach"]',
        (e: Element) => e.textContent?.trim() || '',
      )
      .catch(() => '');
    const hasReserve = await el
      .$('button:has-text("Reserve"), a:has-text("Reserve")')
      .catch(() => null);

    if (time) {
      classes.push({
        studio_slug: studioSlug,
        location_id: locationId,
        class_date: dateStr,
        class_time: normalizeTime(time),
        class_name: className || null,
        instructor: instructor || null,
        duration_minutes: null, // Can't reliably extract from DOM
        available: hasReserve !== null,
        spots_remaining: null,
        booking_opens_at: null, // Browser scraper can't extract this
      });
    }
  }

  return classes;
}

/**
 * Normalize time strings to "H:MM AM/PM" format.
 * Handles various formats: "6:00am", "6:00 AM", "06:00 AM", "6:00 a.m."
 */
function normalizeTime(raw: string): string {
  const cleaned = raw.replace(/\./g, '').replace(/\s+/g, ' ').trim().toUpperCase();
  const match = cleaned.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/);
  if (!match) return raw.trim();

  const hours = parseInt(match[1], 10);
  const minutes = match[2];
  const ampm = match[3];
  return `${hours}:${minutes} ${ampm}`;
}
