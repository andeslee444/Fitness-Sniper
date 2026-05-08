/**
 * MindBody Adapter
 * Works for: Dogpound and any other MindBody-powered studio
 * 
 * MindBody uses two booking systems:
 * 1. Classic ASP: clients.mindbodyonline.com/ASP/su1.asp?studioid=XXXXX
 * 2. Modern Cart: cart.mindbodyonline.com/sites/XXXXX (Healcode widget)
 * 
 * This adapter supports the modern Cart system (used by Dogpound and most current studios).
 * 
 * Booking flow:
 * 1. Load schedule via Healcode widget (or direct cart URL)
 * 2. Add class to cart: cart.mindbodyonline.com/sites/{siteId}/cart/add_booking
 * 3. Login/authenticate via cart.mindbodyonline.com/sites/{siteId}/client
 * 4. Complete checkout
 * 
 * Created: 2026-02-13
 */

import { chromium, Browser, Page, BrowserContext } from 'playwright';

export interface MindBodyStudio {
  name: string;
  siteId: number;           // MindBody numeric site ID (from cart URL)
  widgetId?: string;         // Healcode widget ID (optional, for schedule scraping)
  siteMboId?: number;        // Alternate MBO ID (from widget params)
  locations?: Record<string, number>;  // location name → mbo_location_id
}

export interface MindBodyClassInfo {
  id: string;               // mbo_id from add_booking URL
  name: string;
  instructor: string;
  date: string;             // "Sat. Feb 14, 2026"
  time: string;             // "10:00 AM - 11:00 AM"
  locationId: number;
  available: boolean;
  addToCartUrl?: string;    // Full add_booking URL
}

export interface MindBodyCredentials {
  email: string;
  password: string;
}

export interface MindBodyBookingResult {
  success: boolean;
  classInfo: MindBodyClassInfo;
  message: string;
  confirmationId?: string;
}

// Studio configurations
export const MINDBODY_STUDIOS: Record<string, MindBodyStudio> = {
  dogpound_nyc: {
    name: 'Dogpound NYC',
    siteId: 57707,
    widgetId: '6b1820348c92',
    locations: {
      'nyc': 1,
    }
  },
  dogpound_la: {
    name: 'Dogpound LA',
    siteId: 57707,  // Same site, different location
    widgetId: '9a201004eb07',
    locations: {
      'la': 2,
    }
  },
};

export class MindBodyAdapter {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private studio: MindBodyStudio;
  private credentials: MindBodyCredentials;
  private isAuthenticated: boolean = false;

  // Base URLs
  private readonly CART_BASE: string;
  private readonly WIDGET_BASE = 'https://widgets.healcode.com/widgets/schedules';
  private readonly SCHEDULE_PRINT_URL: string;

  constructor(studioKey: string, credentials: MindBodyCredentials) {
    const studio = MINDBODY_STUDIOS[studioKey];
    if (!studio) {
      throw new Error(`Unknown studio: ${studioKey}. Available: ${Object.keys(MINDBODY_STUDIOS).join(', ')}`);
    }
    this.studio = studio;
    this.credentials = credentials;
    this.CART_BASE = `https://cart.mindbodyonline.com/sites/${studio.siteId}`;
    this.SCHEDULE_PRINT_URL = studio.widgetId 
      ? `${this.WIDGET_BASE}/${studio.widgetId}/print`
      : '';
  }

  async init(): Promise<void> {
    this.browser = await chromium.launch({ headless: false });
    this.context = await this.browser.newContext({
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    });
    this.page = await this.context.newPage();
  }

  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.context = null;
      this.page = null;
    }
  }

  /**
   * Login via the MindBody cart client page
   */
  async login(): Promise<boolean> {
    if (!this.page) throw new Error('Adapter not initialized');

    const loginUrl = `${this.CART_BASE}/client?theme=none&widget_type=schedule`;
    await this.page.goto(loginUrl);
    await this.page.waitForLoadState('networkidle');

    // MindBody login form - look for email/password fields
    try {
      // Wait for login form to appear
      await this.page.waitForSelector('input[type="email"], input[name="email"], #email', { timeout: 10000 });
      
      // Fill credentials
      const emailInput = await this.page.$('input[type="email"], input[name="email"], #email');
      if (emailInput) {
        await emailInput.fill(this.credentials.email);
      }

      const passwordInput = await this.page.$('input[type="password"], input[name="password"], #password');
      if (passwordInput) {
        await passwordInput.fill(this.credentials.password);
      }

      // Click login/sign-in button
      const loginButton = await this.page.$(
        'button[type="submit"], input[type="submit"], button:has-text("Sign In"), button:has-text("Log In")'
      );
      if (loginButton) {
        await loginButton.click();
      }

      // Wait for post-login state
      await this.page.waitForLoadState('networkidle');
      
      // Check for success indicators
      const errorElement = await this.page.$('.error, .alert-danger, [class*="error"]');
      if (errorElement) {
        const errorText = await errorElement.textContent();
        console.error('Login error:', errorText);
        return false;
      }

      this.isAuthenticated = true;
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  }

  /**
   * Get available classes from the schedule
   * Uses the Healcode widget print view for reliable HTML parsing
   */
  async getClasses(): Promise<MindBodyClassInfo[]> {
    if (!this.page) throw new Error('Adapter not initialized');

    const classes: MindBodyClassInfo[] = [];

    if (this.SCHEDULE_PRINT_URL) {
      // Use the print view - cleaner HTML, easier to parse
      await this.page.goto(this.SCHEDULE_PRINT_URL);
      await this.page.waitForLoadState('networkidle');

      // Parse the schedule table
      const rows = await this.page.$$('tr');
      let currentDate = '';

      for (const row of rows) {
        const dateCell = await row.$('td.hc_date, th.hc_date, .healcode-date');
        if (dateCell) {
          currentDate = (await dateCell.textContent())?.trim() || currentDate;
          continue;
        }

        const timeCell = await row.$('td:first-child');
        const nameCell = await row.$('td:nth-child(2)');
        const instructorCell = await row.$('td:nth-child(3), td:last-child');

        if (timeCell && nameCell) {
          const time = (await timeCell.textContent())?.trim() || '';
          const name = (await nameCell.textContent())?.trim() || '';
          const instructor = instructorCell ? (await instructorCell.textContent())?.trim() || '' : '';

          if (time && name) {
            classes.push({
              id: '', // Will be populated from full widget view
              name,
              instructor,
              date: currentDate,
              time,
              locationId: 1,
              available: true,
            });
          }
        }
      }
    }

    // If we need booking URLs, load the full widget
    if (this.studio.widgetId) {
      const widgetUrl = `${this.WIDGET_BASE}/${this.studio.widgetId}`;
      await this.page.goto(widgetUrl);
      await this.page.waitForLoadState('networkidle');

      // Extract add_booking links
      const bookingLinks = await this.page.$$('a[href*="add_booking"]');
      
      for (const link of bookingLinks) {
        const href = await link.getAttribute('href');
        if (!href) continue;

        // Parse URL params
        const url = new URL(href, 'https://cart.mindbodyonline.com');
        const mboId = url.searchParams.get('item[mbo_id]') || '';
        const itemName = url.searchParams.get('item[name]') || '';
        const itemInfo = url.searchParams.get('item[info]') || '';
        const locationId = parseInt(url.searchParams.get('item[mbo_location_id]') || '1');

        // Match with existing class or create new entry
        const existingClass = classes.find(c => 
          c.name === itemName || c.time.includes(itemInfo.split(' ')[0])
        );

        if (existingClass) {
          existingClass.id = mboId;
          existingClass.addToCartUrl = href;
          existingClass.locationId = locationId;
        } else {
          classes.push({
            id: mboId,
            name: itemName,
            instructor: '',
            date: itemInfo,
            time: '',
            locationId,
            available: true,
            addToCartUrl: href,
          });
        }
      }
    }

    return classes;
  }

  /**
   * Book a specific class by adding to cart and checking out
   */
  async bookClass(classInfo: MindBodyClassInfo): Promise<MindBodyBookingResult> {
    if (!this.page) throw new Error('Adapter not initialized');

    // Ensure we're logged in
    if (!this.isAuthenticated) {
      const loggedIn = await this.login();
      if (!loggedIn) {
        return {
          success: false,
          classInfo,
          message: 'Login failed - cannot book class',
        };
      }
    }

    try {
      // Step 1: Add class to cart
      const addToCartUrl = classInfo.addToCartUrl || 
        `${this.CART_BASE}/cart/add_booking?item[type]=Class&item[mbo_id]=${classInfo.id}&item[mbo_location_id]=${classInfo.locationId}&item[name]=${encodeURIComponent(classInfo.name)}&theme=none&widget_type=schedule`;

      await this.page.goto(addToCartUrl);
      await this.page.waitForLoadState('networkidle');

      // Step 2: Check if we need to log in (cart may redirect to login)
      const loginForm = await this.page.$('input[type="email"], input[name="email"]');
      if (loginForm) {
        await this.login();
        // Retry adding to cart
        await this.page.goto(addToCartUrl);
        await this.page.waitForLoadState('networkidle');
      }

      // Step 3: Complete checkout
      const checkoutButton = await this.page.$(
        'button:has-text("Complete"), button:has-text("Book"), button:has-text("Confirm"), button:has-text("Purchase"), input[type="submit"]'
      );

      if (checkoutButton) {
        await checkoutButton.click();
        await this.page.waitForLoadState('networkidle');

        // Check for success
        const successIndicator = await this.page.$(
          '.success, .confirmation, [class*="success"], :has-text("confirmed"), :has-text("booked")'
        );

        if (successIndicator) {
          const confirmationText = await successIndicator.textContent();
          return {
            success: true,
            classInfo,
            message: `Successfully booked ${classInfo.name}`,
            confirmationId: confirmationText?.match(/\d{6,}/)?.[0],
          };
        }
      }

      // Check for errors
      const errorElement = await this.page.$('.error, .alert-danger, [class*="error"]');
      if (errorElement) {
        const errorText = await errorElement.textContent();
        return {
          success: false,
          classInfo,
          message: `Booking error: ${errorText?.trim()}`,
        };
      }

      return {
        success: false,
        classInfo,
        message: 'Could not complete booking - checkout button not found or confirmation not detected',
      };
    } catch (error) {
      return {
        success: false,
        classInfo,
        message: `Booking failed: ${error}`,
      };
    }
  }

  /**
   * Snipe a class - wait for it to become available and book immediately
   * Useful for classes that open at midnight or when spots open up
   */
  async snipeClass(
    className: string,
    targetTime: string,
    options: {
      pollIntervalMs?: number;
      maxAttempts?: number;
      bookingOpensAt?: Date;
    } = {}
  ): Promise<MindBodyBookingResult> {
    const {
      pollIntervalMs = 5000,
      maxAttempts = 360, // 30 min at 5s intervals
      bookingOpensAt,
    } = options;

    // If we know when booking opens, wait until then
    if (bookingOpensAt) {
      const waitMs = bookingOpensAt.getTime() - Date.now();
      if (waitMs > 0) {
        console.log(`Waiting ${Math.round(waitMs / 1000)}s until booking opens...`);
        // Start polling 2 seconds before
        await new Promise(resolve => setTimeout(resolve, Math.max(0, waitMs - 2000)));
      }
    }

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      console.log(`Snipe attempt ${attempt + 1}/${maxAttempts}...`);
      
      const classes = await this.getClasses();
      const targetClass = classes.find(c => {
        const nameMatch = c.name.toLowerCase().includes(className.toLowerCase());
        const timeMatch = !targetTime || c.time.includes(targetTime);
        return nameMatch && timeMatch && c.available && c.addToCartUrl;
      });

      if (targetClass) {
        console.log(`Found target class: ${targetClass.name} at ${targetClass.time}`);
        return await this.bookClass(targetClass);
      }

      if (attempt < maxAttempts - 1) {
        await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
      }
    }

    return {
      success: false,
      classInfo: {
        id: '',
        name: className,
        instructor: '',
        date: '',
        time: targetTime,
        locationId: 1,
        available: false,
      },
      message: `Class "${className}" at ${targetTime} not found after ${maxAttempts} attempts`,
    };
  }
}

// ============================================================
// Classic ASP Adapter (fallback for older MindBody studios)
// ============================================================

export class MindBodyClassicAdapter {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private studioId: number;
  private credentials: MindBodyCredentials;

  private readonly BASE_URL: string;

  constructor(studioId: number, credentials: MindBodyCredentials) {
    this.studioId = studioId;
    this.credentials = credentials;
    this.BASE_URL = `https://clients.mindbodyonline.com/ASP/su1.asp?studioid=${studioId}`;
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
   * Login via the classic MindBody client portal
   */
  async login(): Promise<boolean> {
    if (!this.page) throw new Error('Adapter not initialized');

    await this.page.goto(this.BASE_URL);
    await this.page.waitForLoadState('networkidle');

    try {
      // Classic ASP login form
      await this.page.fill('#su1UserName', this.credentials.email);
      await this.page.fill('#su1Password', this.credentials.password);
      await this.page.click('#btnSu1Login');
      await this.page.waitForLoadState('networkidle');

      // Check if login succeeded by looking for schedule tab
      const scheduleTab = await this.page.$('#tabA7');
      return scheduleTab !== null;
    } catch (error) {
      console.error('Classic login failed:', error);
      return false;
    }
  }

  /**
   * Navigate to class schedule and book
   */
  async bookClass(classId: string): Promise<boolean> {
    if (!this.page) throw new Error('Adapter not initialized');

    try {
      // Click schedule tab
      await this.page.click('#tabA7');
      await this.page.waitForLoadState('networkidle');

      // Find and click the sign-up button for the target class
      const signUpButton = await this.page.$(`input[name*="${classId}"], a[href*="${classId}"]`);
      if (!signUpButton) {
        console.error('Class not found in schedule');
        return false;
      }

      await signUpButton.click();
      await this.page.waitForLoadState('networkidle');

      // Confirm enrollment
      const confirmButton = await this.page.$('#SubmitEnroll2');
      if (confirmButton) {
        await confirmButton.click();
        await this.page.waitForLoadState('networkidle');
        return true;
      }

      return false;
    } catch (error) {
      console.error('Classic booking failed:', error);
      return false;
    }
  }
}
