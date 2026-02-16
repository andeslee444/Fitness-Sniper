/**
 * Mariana Tek Adapter (Worker Version)
 *
 * Ported from archive/src/adapters/mariana-tek.ts with:
 * - Stealth browser launch
 * - Human-like delays between actions
 * - Screenshot capture at each step
 * - Detailed step logging for real-time UI updates
 *
 * Supports all Mariana Tek studios: Barry's, Aarmy, SLT,
 * Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre
 */

import { Page, Frame, BrowserContext } from 'playwright';
import { STUDIOS, LOCATION_IDS, type StudioConfig } from '@class-sniper/shared';
import { launchStealthBrowser } from '../stealth/browser.js';
import { humanDelay, shortDelay, humanType, humanClick } from '../stealth/human-delay.js';
import type { BookingResult, StudioCredentials, ClassInfo } from '@class-sniper/shared';

export type StepLogger = (step: string, detail: string) => void;

export class MarianaTekAdapter {
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private studio: StudioConfig;
  private credentials: StudioCredentials;
  private isAuthenticated = false;
  private log: StepLogger;
  private screenshotDir: string;

  constructor(
    studioSlug: string,
    credentials: StudioCredentials,
    opts: { log?: StepLogger; screenshotDir?: string } = {},
  ) {
    const studio = STUDIOS[studioSlug];
    if (!studio) {
      throw new Error(`Unknown studio: ${studioSlug}. Available: ${Object.keys(STUDIOS).join(', ')}`);
    }
    this.studio = studio;
    this.credentials = credentials;
    this.log = opts.log || ((step, detail) => console.log(`[${step}] ${detail}`));
    this.screenshotDir = opts.screenshotDir || '/tmp/class-sniper';
  }

  async init(): Promise<void> {
    const headless = process.env.NODE_ENV === 'production';
    const { context } = await launchStealthBrowser({ headless });
    this.context = context;
    this.page = await context.newPage();
    this.log('init', `Browser launched for ${this.studio.name} (headless: ${headless})`);
  }

  async close(): Promise<void> {
    if (this.context) {
      const browser = this.context.browser();
      await this.context.close();
      if (browser) await browser.close();
      this.context = null;
      this.page = null;
    }
  }

  async screenshot(name: string): Promise<string | null> {
    if (!this.page) return null;
    try {
      const path = `${this.screenshotDir}/${Date.now()}-${name}.png`;
      await this.page.screenshot({ path, fullPage: false });
      return path;
    } catch {
      return null;
    }
  }

  // --------------------------------------------------------
  // Authentication
  // --------------------------------------------------------

  async login(): Promise<boolean> {
    if (!this.page) throw new Error('Adapter not initialized');
    this.log('login', `Navigating to ${this.studio.loginUrl}`);

    await this.page.goto(this.studio.loginUrl);
    await this.page.waitForLoadState('networkidle');
    await humanDelay(2000, 4000);

    // Fill login form
    this.log('login', 'Filling credentials');
    const emailSelector = 'input[name="email"], [data-testid="email-input"], input[type="email"]';
    const passwordSelector = 'input[name="password"], [data-testid="password-input"], input[type="password"]';

    await humanType(this.page, emailSelector, this.credentials.email);
    await shortDelay();
    await humanType(this.page, passwordSelector, this.credentials.password);
    await shortDelay();

    await this.screenshot('login-filled');

    // Submit
    this.log('login', 'Submitting login form');
    await this.page.click('button[type="submit"], button:has-text("Log in"), button:has-text("LOG IN")');
    await this.page.waitForLoadState('networkidle');
    await humanDelay(2000, 5000);

    this.isAuthenticated = await this.checkAuthenticated();
    this.log('login', this.isAuthenticated ? 'Login successful' : 'Login failed');
    await this.screenshot('login-result');
    return this.isAuthenticated;
  }

  private async checkAuthenticated(): Promise<boolean> {
    if (!this.page) return false;
    const selectors = 'menuitem[aria-label*="avatar"], [data-testid="account-menu"], .avatar, .user-menu';
    const el = await this.page.$(selectors);
    return el !== null;
  }

  // --------------------------------------------------------
  // Schedule Navigation
  // --------------------------------------------------------

  private isDirectSPA(): boolean {
    return !this.studio.iframe || this.studio.iframe === '';
  }

  async goToSchedule(location: string): Promise<void> {
    if (!this.page) throw new Error('Adapter not initialized');

    if (this.isDirectSPA()) {
      const url = `${this.studio.scheduleUrl}?location_id=${this.studio.slug}-${location}`;
      this.log('schedule', `Navigating to direct SPA schedule: ${url}`);
      await this.page.goto(url);
      await this.page.waitForLoadState('networkidle');
      await this.page.waitForSelector('table, [class*="schedule"], [class*="class-row"]', {
        timeout: 15000,
      });
    } else {
      const locationId = LOCATION_IDS[this.studio.slug]?.[location] || location;
      const url = this.studio.scheduleUrl.replace('{location}', locationId);
      this.log('schedule', `Navigating to iframe schedule: ${url}`);
      await this.page.goto(url);
      await this.page.waitForLoadState('networkidle');
      await this.page.waitForSelector(this.studio.iframe, { timeout: 10000 });
    }

    await humanDelay(1500, 3000);
    await this.screenshot('schedule-loaded');
  }

  private async getScheduleFrame(): Promise<Frame | Page | null> {
    if (!this.page) return null;

    if (this.isDirectSPA()) {
      return this.page;
    }

    const frameElement = await this.page.$(this.studio.iframe);
    if (!frameElement) return null;
    return await frameElement.contentFrame();
  }

  // --------------------------------------------------------
  // Class Discovery
  // --------------------------------------------------------

  async getClasses(location: string, date?: Date): Promise<ClassInfo[]> {
    if (!this.page) throw new Error('Adapter not initialized');

    await this.goToSchedule(location);
    const frame = await this.getScheduleFrame();
    if (!frame) throw new Error('Schedule frame not found');

    await frame.waitForSelector('[class*="class"], [data-testid="class-card"]', { timeout: 10000 });

    const classElements = await frame.$$('[class*="class-row"], [class*="class-card"], article');
    const classes: ClassInfo[] = [];

    for (const el of classElements) {
      const time = await el.$eval('[class*="time"]', (e: Element) => e.textContent?.trim() || '').catch(() => '');
      const className = await el.$eval('[class*="name"], [class*="title"]', (e: Element) => e.textContent?.trim() || '').catch(() => '');
      const instructor = await el.$eval('[class*="instructor"], [class*="coach"]', (e: Element) => e.textContent?.trim() || '').catch(() => '');
      const hasReserve = await el.$('button:has-text("Reserve"), a:has-text("Reserve")').catch(() => null);

      if (time && className) {
        classes.push({
          time,
          className,
          instructor,
          location,
          date: date?.toISOString().split('T')[0] || new Date().toISOString().split('T')[0],
          available: hasReserve !== null,
        });
      }
    }

    this.log('classes', `Found ${classes.length} classes, ${classes.filter((c) => c.available).length} available`);
    return classes;
  }

  // --------------------------------------------------------
  // Booking
  // --------------------------------------------------------

  async bookClass(
    location: string,
    time: string,
    preferredSpots?: string[],
  ): Promise<BookingResult> {
    if (!this.page) throw new Error('Adapter not initialized');

    // Step 1: Ensure authenticated
    if (!this.isAuthenticated) {
      this.log('book', 'Not authenticated, logging in first');
      const loggedIn = await this.login();
      if (!loggedIn) {
        return { success: false, message: 'Login failed' };
      }
    }

    // Step 2: Navigate to schedule
    this.log('book', `Opening schedule for ${this.studio.name} ${location}`);
    await this.goToSchedule(location);
    const frame = await this.getScheduleFrame();
    if (!frame) return { success: false, message: 'Schedule frame not found' };

    // Step 3: Find the target class and click Reserve
    this.log('book', `Looking for class at ${time}`);
    await humanDelay(1000, 2000);

    const classRow = await frame.$(
      `xpath=//text()[contains(., '${time}')]/ancestor::*[contains(@class, 'class') or contains(@class, 'row')]`,
    );
    if (!classRow) {
      await this.screenshot('class-not-found');
      return { success: false, message: `Class at ${time} not found in schedule` };
    }

    const reserveButton = await classRow.$('button:has-text("Reserve"), a:has-text("Reserve")');
    if (!reserveButton) {
      await this.screenshot('no-reserve-button');
      return { success: false, message: `Class at ${time} is not available for reservation` };
    }

    this.log('book', 'Clicking Reserve');
    await reserveButton.click();
    await humanDelay(1500, 3000);
    await this.screenshot('reserve-clicked');

    // Step 4: Select spot
    this.log('book', 'Waiting for spot selection');
    try {
      await frame.waitForSelector(
        'button:has-text("Available Spot"), .spot-seat-selectable, [class*="spot"][class*="selectable"]',
        { timeout: 10000 },
      );
    } catch {
      await this.screenshot('no-spot-modal');
      return { success: false, message: 'Spot selection did not appear' };
    }

    let selectedSpot: string | null = null;

    // Try preferred spots first
    if (preferredSpots && preferredSpots.length > 0) {
      for (const spotName of preferredSpots) {
        const spotEl = await frame.$(`button:has-text("${spotName}"), [aria-label*="${spotName}"]`);
        if (spotEl) {
          await spotEl.click();
          selectedSpot = spotName;
          this.log('book', `Selected preferred spot: ${spotName}`);
          break;
        }
      }
    }

    // Fallback: first available spot
    if (!selectedSpot) {
      const spotButton = await frame.$(
        'button:has-text("Available Spot"), .spot-seat-selectable:first-of-type, [class*="spot"][class*="selectable"]:first-of-type',
      );
      if (spotButton) {
        const label = await spotButton.textContent();
        await spotButton.click();
        selectedSpot = label?.trim() || 'first-available';
        this.log('book', `Selected first available spot: ${selectedSpot}`);
      }
    }

    await humanDelay(500, 1500);
    await this.screenshot('spot-selected');

    // Step 5: Confirm booking
    this.log('book', 'Confirming reservation');
    try {
      await frame.waitForSelector(
        'button:has-text("Buy & Reserve Class"), button:has-text("Confirm"), button:has-text("Complete")',
        { timeout: 5000 },
      );
      const confirmButton = await frame.$(
        'button:has-text("Buy & Reserve Class"), button:has-text("Confirm"), button:has-text("Complete")',
      );
      if (confirmButton) {
        await confirmButton.click();
        await this.page.waitForLoadState('networkidle');
        await humanDelay(2000, 4000);
        const screenshotPath = await this.screenshot('booking-confirmed');

        this.log('book', `Booking confirmed! Spot: ${selectedSpot}`);
        return {
          success: true,
          message: `Reserved ${this.studio.name} at ${time} in ${location}`,
          spot: selectedSpot || undefined,
          screenshotPath: screenshotPath || undefined,
        };
      }
    } catch {
      // fall through
    }

    await this.screenshot('booking-failed');
    return { success: false, message: 'Could not confirm reservation' };
  }
}
