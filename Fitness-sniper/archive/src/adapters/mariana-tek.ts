/**
 * Mariana Tek Unified Adapter
 * Works for: Barry's, Aarmy, and any other Mariana Tek-powered studio
 * 
 * Created: 2026-02-13
 */

import { chromium, Browser, Page, Frame } from 'playwright';

export interface Studio {
  name: string;
  slug: string;
  scheduleUrl: string;
  loginUrl: string;
  iframe: string;  // iframe selector (varies by studio)
}

export interface ClassInfo {
  time: string;
  className: string;
  instructor: string;
  location: string;
  date: string;
  available: boolean;
}

export interface Credentials {
  email: string;
  password: string;
}

// Studio configurations
export const STUDIOS: Record<string, Studio> = {
  barrys: {
    name: "Barry's Bootcamp",
    slug: 'barrys',
    scheduleUrl: 'https://www.barrys.com/schedule/{location}',
    loginUrl: 'https://barrysbootcamp.marianatek.com/auth/login/',
    iframe: 'iframe.visible'
  },
  aarmy: {
    name: 'Aarmy',
    slug: 'aarmy',
    scheduleUrl: 'https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily',
    loginUrl: 'https://aarmy.marianatek.com/auth/login/',
    iframe: 'iframe'
  },
  slt: {
    name: 'SLT',
    slug: 'slt',
    scheduleUrl: 'https://www.sltnyc.com/book-a-class/',
    loginUrl: 'https://slt.marianatek.com/auth/login/',
    iframe: 'iframe'  // Uses marianaiframes.com embeds
  },
  // Xponential Fitness brands (all use Mariana Tek member portals)
  rumble: {
    name: 'Rumble Boxing',
    slug: 'rumble',
    scheduleUrl: 'https://members.rumbleboxinggym.com/schedule/daily',
    loginUrl: 'https://members.rumbleboxinggym.com/auth/login',
    iframe: ''  // Direct SPA, no iframe
  },
  cyclebar: {
    name: 'CycleBar',
    slug: 'cyclebar',
    scheduleUrl: 'https://members.cyclebar.com/schedule/daily',
    loginUrl: 'https://members.cyclebar.com/auth/login',
    iframe: ''  // Direct SPA, no iframe
  },
  clubpilates: {
    name: 'Club Pilates',
    slug: 'clubpilates',
    scheduleUrl: 'https://members.clubpilates.com/schedule/daily',
    loginUrl: 'https://members.clubpilates.com/auth/login',
    iframe: ''  // Direct SPA, no iframe
  },
  yogasix: {
    name: 'YogaSix',
    slug: 'yogasix',
    scheduleUrl: 'https://members.yogasix.com/schedule/daily',
    loginUrl: 'https://members.yogasix.com/auth/login',
    iframe: ''  // Direct SPA, no iframe
  },
  stretchlab: {
    name: 'StretchLab',
    slug: 'stretchlab',
    scheduleUrl: 'https://members.stretchlab.com/schedule/daily',
    loginUrl: 'https://members.stretchlab.com/auth/login',
    iframe: ''  // Direct SPA, no iframe
  },
  purebarre: {
    name: 'Pure Barre',
    slug: 'purebarre',
    scheduleUrl: 'https://members.purebarre.com/schedule/daily',
    loginUrl: 'https://members.purebarre.com/auth/login',
    iframe: ''  // Direct SPA, no iframe
  },
};

// Location IDs for each studio
export const LOCATIONS: Record<string, Record<string, string>> = {
  barrys: {
    'noho': 'noho',
    'chelsea': 'chelsea',
    'tribeca': 'tribeca',
    'brooklyn-heights': 'brooklyn-heights',
    'east-64th': 'east-64th',
    'east-86th': 'east-86th',
    'lic': 'long-island-city',
    'park-ave-south': 'park-ave-south'
  },
  aarmy: {
    'chelsea': 'Chelsea (A23)',
    'noho': 'NoHo'
  },
  slt: {
    'ues': 'Upper East Side',
    'uws': 'Upper West Side',
    'nomad': 'NoMad',
    'soho': 'SoHo',
    'fidi': 'FiDi',
    'brooklyn': 'Brooklyn',
    'hoboken': 'Hoboken',
  }
};

export class MarianaTekAdapter {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private studio: Studio;
  private credentials: Credentials;
  private isAuthenticated: boolean = false;

  constructor(studioSlug: string, credentials: Credentials) {
    const studio = STUDIOS[studioSlug];
    if (!studio) {
      throw new Error(`Unknown studio: ${studioSlug}. Available: ${Object.keys(STUDIOS).join(', ')}`);
    }
    this.studio = studio;
    this.credentials = credentials;
  }

  async init(): Promise<void> {
    this.browser = await chromium.launch({ headless: false });
    this.page = await this.browser.newPage();
  }

  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
    }
  }

  /**
   * Login to Mariana Tek
   * Selectors are consistent across all Mariana Tek implementations
   */
  async login(): Promise<boolean> {
    if (!this.page) throw new Error('Adapter not initialized');
    
    // Navigate to login URL
    await this.page.goto(this.studio.loginUrl);
    await this.page.waitForLoadState('networkidle');
    
    // Fill login form - consistent selectors across all Mariana Tek
    await this.page.fill('input[name="email"], [data-testid="email-input"], input[type="email"]', this.credentials.email);
    await this.page.fill('input[name="password"], [data-testid="password-input"], input[type="password"]', this.credentials.password);
    
    // Click login button
    await this.page.click('button[type="submit"], button:has-text("Log in"), button:has-text("LOG IN")');
    
    // Wait for redirect after login
    await this.page.waitForLoadState('networkidle');
    
    // Check if login was successful
    this.isAuthenticated = await this.checkAuthenticated();
    return this.isAuthenticated;
  }

  /**
   * Check if currently authenticated
   */
  async checkAuthenticated(): Promise<boolean> {
    if (!this.page) return false;
    
    // Look for avatar or account menu - indicates logged in
    const avatarSelector = 'menuitem[aria-label*="avatar"], [data-testid="account-menu"], .avatar, .user-menu';
    const avatar = await this.page.$(avatarSelector);
    return avatar !== null;
  }

  /**
   * Check if this studio uses direct SPA (no iframe) - Xponential brands
   */
  private isDirectSPA(): boolean {
    return !this.studio.iframe || this.studio.iframe === '';
  }

  /**
   * Navigate to schedule for a specific location
   * Xponential brands: direct SPA with location_id param
   * Barry's/SLT: iframe-based schedule
   */
  async goToSchedule(location: string): Promise<void> {
    if (!this.page) throw new Error('Adapter not initialized');
    
    if (this.isDirectSPA()) {
      // Xponential brands: direct member portal with location_id
      const url = `${this.studio.scheduleUrl}?location_id=${this.studio.slug}-${location}`;
      await this.page.goto(url);
      await this.page.waitForLoadState('networkidle');
      // Wait for schedule table to render (React SPA)
      await this.page.waitForSelector('table, [class*="schedule"], [class*="class-row"]', { timeout: 15000 });
    } else {
      // iframe-based studios (Barry's, SLT, Aarmy)
      const url = this.studio.scheduleUrl.replace('{location}', location);
      await this.page.goto(url);
      await this.page.waitForLoadState('networkidle');
      await this.page.waitForSelector(this.studio.iframe, { timeout: 10000 });
    }
  }

  /**
   * Get the content frame for class interactions
   * Returns iframe frame for Barry's/SLT, or the page itself for Xponential SPAs
   */
  async getScheduleFrame(): Promise<Frame | Page | null> {
    if (!this.page) return null;
    
    if (this.isDirectSPA()) {
      // For direct SPAs, the page IS the frame
      return this.page;
    }
    
    // iframe-based studios
    const frameElement = await this.page.$(this.studio.iframe);
    if (!frameElement) return null;
    
    const frame = await frameElement.contentFrame();
    return frame;
  }

  /**
   * Get available classes from schedule
   */
  async getClasses(location: string, date?: Date): Promise<ClassInfo[]> {
    if (!this.page) throw new Error('Adapter not initialized');
    
    await this.goToSchedule(location);
    const frame = await this.getScheduleFrame();
    if (!frame) throw new Error('Schedule iframe not found');
    
    // Wait for classes to load
    await frame.waitForSelector('[class*="class"], [data-testid="class-card"]', { timeout: 10000 });
    
    // Extract class information
    const classes: ClassInfo[] = [];
    
    // Get all class rows/cards
    const classElements = await frame.$$('[class*="class-row"], [class*="class-card"], article');
    
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
          available: hasReserve !== null
        });
      }
    }
    
    return classes;
  }

  /**
   * Reserve a specific class
   */
  async reserveClass(location: string, time: string): Promise<{ success: boolean; message: string }> {
    if (!this.page) throw new Error('Adapter not initialized');
    if (!this.isAuthenticated) {
      const loggedIn = await this.login();
      if (!loggedIn) {
        return { success: false, message: 'Login failed' };
      }
    }
    
    await this.goToSchedule(location);
    const frame = await this.getScheduleFrame();
    if (!frame) return { success: false, message: 'Schedule iframe not found' };
    
    // Find the class by time and click Reserve
    const timeSelector = `text="${time}"`;
    const classRow = await frame.$(`xpath=//text()[contains(., '${time}')]/ancestor::*[contains(@class, 'class') or contains(@class, 'row')]`);
    
    if (!classRow) {
      return { success: false, message: `Class at ${time} not found` };
    }
    
    const reserveButton = await classRow.$('button:has-text("Reserve"), a:has-text("Reserve")');
    if (!reserveButton) {
      return { success: false, message: `Class at ${time} is not available for reservation` };
    }
    
    await reserveButton.click();
    
    // Wait for spot/seat selection modal
    // Xponential uses .spot-seat-selectable, Barry's/SLT use "Available Spot" buttons
    await frame.waitForSelector('button:has-text("Available Spot"), .spot-seat-selectable, [class*="spot"][class*="selectable"]', { timeout: 10000 });
    
    // Select first available spot
    const spotButton = await frame.$('button:has-text("Available Spot"), .spot-seat-selectable:first-of-type, [class*="spot"][class*="selectable"]:first-of-type');
    if (spotButton) {
      await spotButton.click();
    }
    
    // Confirm reservation
    await frame.waitForSelector('button:has-text("Confirm"), button:has-text("Complete")', { timeout: 5000 });
    const confirmButton = await frame.$('button:has-text("Confirm"), button:has-text("Complete")');
    if (confirmButton) {
      await confirmButton.click();
      await frame.waitForLoadState('networkidle');
      return { success: true, message: `Successfully reserved class at ${time}` };
    }
    
    return { success: false, message: 'Could not confirm reservation' };
  }
}

// Example usage — credentials from env vars
export async function testBarrysLogin() {
  const adapter = new MarianaTekAdapter('barrys', {
    email: process.env.BARRYS_EMAIL || '',
    password: process.env.BARRYS_PASSWORD || '',
  });

  await adapter.init();
  const loggedIn = await adapter.login();
  console.log('Barry\'s login:', loggedIn ? 'SUCCESS' : 'FAILED');

  if (loggedIn) {
    const classes = await adapter.getClasses('noho');
    console.log('Available classes:', classes.filter(c => c.available));
  }

  await adapter.close();
}
