/**
 * Barry's Bootcamp adapter
 * 
 * Barry's uses a custom booking system at https://www.barrys.com/book/
 * Classes open 7 days in advance at varying times depending on location.
 */

import { chromium, Browser, Page, BrowserContext } from 'playwright';
import {
  StudioAdapter,
  StudioCredentials,
  ClassPreferences,
  ClassInfo,
  BookingResult,
} from './base.js';

export class BarrysAdapter implements StudioAdapter {
  name = "Barry's Bootcamp";
  
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private loggedIn = false;
  
  private readonly BASE_URL = 'https://www.barrys.com';
  private readonly BOOK_URL = 'https://www.barrys.com/book/';
  private readonly LOGIN_URL = 'https://www.barrys.com/login/';
  
  /**
   * Initialize browser
   */
  private async initBrowser(): Promise<void> {
    if (this.browser) return;
    
    this.browser = await chromium.launch({
      headless: false, // Set to true for production
      slowMo: 100, // Slow down for debugging
    });
    
    this.context = await this.browser.newContext({
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
      viewport: { width: 1280, height: 800 },
    });
    
    this.page = await this.context.newPage();
  }
  
  /**
   * Login to Barry's
   */
  async login(credentials: StudioCredentials): Promise<boolean> {
    await this.initBrowser();
    if (!this.page) throw new Error('Browser not initialized');
    
    try {
      console.log('🔐 Logging into Barry\'s...');
      
      // Navigate to login page
      await this.page.goto(this.LOGIN_URL, { waitUntil: 'networkidle' });
      
      // Wait for login form
      await this.page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 10000 });
      
      // Fill in credentials
      await this.page.fill('input[type="email"], input[name="email"]', credentials.email);
      await this.page.fill('input[type="password"], input[name="password"]', credentials.password);
      
      // Click login button
      await this.page.click('button[type="submit"]');
      
      // Wait for navigation/login to complete
      await this.page.waitForNavigation({ timeout: 15000 }).catch(() => {});
      
      // Check if login was successful (look for user menu or book button)
      const loggedInIndicator = await this.page.$('[data-testid="user-menu"], .user-menu, .account-menu');
      
      if (loggedInIndicator) {
        console.log('✅ Successfully logged in to Barry\'s');
        this.loggedIn = true;
        return true;
      }
      
      // Check for error message
      const errorMessage = await this.page.$('.error-message, .login-error');
      if (errorMessage) {
        const errorText = await errorMessage.textContent();
        console.error('❌ Login failed:', errorText);
        return false;
      }
      
      // Assume success if we navigated away from login
      if (!this.page.url().includes('login')) {
        console.log('✅ Successfully logged in to Barry\'s');
        this.loggedIn = true;
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('❌ Login error:', error);
      return false;
    }
  }
  
  /**
   * Search for classes matching preferences
   */
  async searchClasses(preferences: ClassPreferences): Promise<ClassInfo[]> {
    await this.initBrowser();
    if (!this.page) throw new Error('Browser not initialized');
    
    const classes: ClassInfo[] = [];
    
    try {
      console.log('🔍 Searching for classes...');
      
      // Navigate to booking page
      await this.page.goto(this.BOOK_URL, { waitUntil: 'networkidle' });
      
      // Wait for class schedule to load
      await this.page.waitForSelector('.class-card, .schedule-item, [data-class-id]', { timeout: 15000 });
      
      // Filter by location if possible
      for (const location of preferences.locations) {
        console.log(`📍 Searching location: ${location}`);
        
        // Try to select location from dropdown/filter
        const locationSelector = await this.page.$('.location-filter, [data-location-filter]');
        if (locationSelector) {
          await locationSelector.click();
          await this.page.click(`text="${location}"`).catch(() => {
            console.log(`⚠️ Could not select location: ${location}`);
          });
          await this.page.waitForTimeout(1000); // Wait for filter to apply
        }
        
        // Parse class cards
        const classElements = await this.page.$$('.class-card, .schedule-item, [data-class-id]');
        
        for (const element of classElements) {
          try {
            const classInfo = await this.parseClassElement(element, location);
            if (classInfo && this.matchesPreferences(classInfo, preferences)) {
              classes.push(classInfo);
            }
          } catch (e) {
            // Skip unparseable elements
          }
        }
      }
      
      console.log(`📋 Found ${classes.length} matching classes`);
      return classes;
      
    } catch (error) {
      console.error('❌ Search error:', error);
      return classes;
    }
  }
  
  /**
   * Parse a class element into ClassInfo
   */
  private async parseClassElement(element: any, location: string): Promise<ClassInfo | null> {
    try {
      const id = await element.getAttribute('data-class-id') || 
                 await element.getAttribute('id') || 
                 `barry-${Date.now()}-${Math.random()}`;
      
      // Extract class details - these selectors are approximate and need testing
      const timeText = await element.$eval('.class-time, .time, [data-time]', (el: any) => el.textContent).catch(() => '');
      const dateText = await element.$eval('.class-date, .date, [data-date]', (el: any) => el.textContent).catch(() => '');
      const instructorText = await element.$eval('.instructor, .trainer, [data-instructor]', (el: any) => el.textContent).catch(() => '');
      const classNameText = await element.$eval('.class-name, .title, [data-class-name]', (el: any) => el.textContent).catch(() => 'Barry\'s Class');
      const spotsText = await element.$eval('.spots, .availability, [data-spots]', (el: any) => el.textContent).catch(() => '');
      
      // Parse spots available
      let spotsAvailable = 0;
      const spotsMatch = spotsText.match(/(\d+)/);
      if (spotsMatch) {
        spotsAvailable = parseInt(spotsMatch[1], 10);
      }
      
      // Check if bookable or waitlist
      const bookButton = await element.$('.book-btn, [data-book], button:has-text("Book")');
      const waitlistButton = await element.$('.waitlist-btn, [data-waitlist], button:has-text("Waitlist")');
      
      return {
        id,
        studio: "Barry's",
        location,
        date: this.parseDate(dateText),
        time: this.parseTime(timeText),
        instructor: instructorText.trim(),
        className: classNameText.trim(),
        spotsAvailable,
        isBookable: !!bookButton,
        isWaitlist: !!waitlistButton,
      };
    } catch (error) {
      return null;
    }
  }
  
  /**
   * Parse date string to YYYY-MM-DD
   */
  private parseDate(dateText: string): string {
    // Try to parse common date formats
    const now = new Date();
    const dateMatch = dateText.match(/(\w+)\s+(\d+)/);
    
    if (dateMatch) {
      const months: Record<string, number> = {
        jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
        jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11
      };
      const monthStr = dateMatch[1].toLowerCase().slice(0, 3);
      const day = parseInt(dateMatch[2], 10);
      
      if (months[monthStr] !== undefined) {
        const date = new Date(now.getFullYear(), months[monthStr], day);
        return date.toISOString().split('T')[0];
      }
    }
    
    // Default to today
    return now.toISOString().split('T')[0];
  }
  
  /**
   * Parse time string to HH:MM
   */
  private parseTime(timeText: string): string {
    const match = timeText.match(/(\d{1,2}):?(\d{2})?\s*(am|pm)?/i);
    if (match) {
      let hour = parseInt(match[1], 10);
      const minute = match[2] ? parseInt(match[2], 10) : 0;
      const period = match[3]?.toLowerCase();
      
      if (period === 'pm' && hour < 12) hour += 12;
      if (period === 'am' && hour === 12) hour = 0;
      
      return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
    }
    return '00:00';
  }
  
  /**
   * Check if class matches user preferences
   */
  private matchesPreferences(classInfo: ClassInfo, preferences: ClassPreferences): boolean {
    // Check location
    if (!preferences.locations.some(loc => 
      classInfo.location.toLowerCase().includes(loc.toLowerCase())
    )) {
      return false;
    }
    
    // Check instructor
    if (preferences.instructors && preferences.instructors.length > 0) {
      if (!preferences.instructors.some(inst => 
        classInfo.instructor.toLowerCase().includes(inst.toLowerCase())
      )) {
        return false;
      }
    }
    
    // Check time (simplified - would need more logic for full implementation)
    const classHour = parseInt(classInfo.time.split(':')[0], 10);
    const date = new Date(classInfo.date);
    const isWeekend = date.getDay() === 0 || date.getDay() === 6;
    
    const timeRanges = isWeekend ? preferences.times.weekends : preferences.times.weekdays;
    
    if (timeRanges && timeRanges.length > 0) {
      const inRange = timeRanges.some(range => {
        const [start, end] = range.split('-').map(t => parseInt(t.split(':')[0], 10));
        return classHour >= start && classHour < end;
      });
      if (!inRange) return false;
    }
    
    return true;
  }
  
  /**
   * Book a specific class
   */
  async bookClass(classInfo: ClassInfo): Promise<BookingResult> {
    if (!this.page) throw new Error('Browser not initialized');
    
    try {
      console.log(`🎯 Attempting to book: ${classInfo.className} at ${classInfo.time}`);
      
      // Navigate to booking page if not already there
      if (!this.page.url().includes('book')) {
        await this.page.goto(this.BOOK_URL, { waitUntil: 'networkidle' });
      }
      
      // Find the specific class
      const classElement = await this.page.$(`[data-class-id="${classInfo.id}"]`);
      
      if (!classElement) {
        // Try to find by other attributes
        console.log('⚠️ Could not find class by ID, searching by details...');
      }
      
      // Click book button
      const bookButton = classElement 
        ? await classElement.$('.book-btn, [data-book], button:has-text("Book")')
        : await this.page.$(`button:has-text("Book"):near(:text("${classInfo.time}"))`);
      
      if (!bookButton) {
        return {
          success: false,
          classInfo,
          error: 'Book button not found',
        };
      }
      
      await bookButton.click();
      
      // Wait for confirmation dialog or page
      await this.page.waitForTimeout(2000);
      
      // Look for confirmation button if there's a modal
      const confirmButton = await this.page.$('button:has-text("Confirm"), button:has-text("Complete"), .confirm-booking');
      if (confirmButton) {
        await confirmButton.click();
        await this.page.waitForTimeout(2000);
      }
      
      // Check for success message
      const successIndicator = await this.page.$('.booking-success, .confirmation, :text("confirmed"), :text("booked")');
      
      if (successIndicator) {
        // Try to get confirmation ID
        const confirmationText = await this.page.$eval('.confirmation-id, .booking-id', (el: any) => el.textContent).catch(() => '');
        const confirmationId = confirmationText.match(/[A-Z0-9]{6,}/)?.[0];
        
        console.log(`✅ Successfully booked! Confirmation: ${confirmationId || 'N/A'}`);
        
        return {
          success: true,
          classInfo,
          confirmationId,
        };
      }
      
      // Check for error
      const errorIndicator = await this.page.$('.error, .booking-error, :text("failed"), :text("unavailable")');
      if (errorIndicator) {
        const errorText = await errorIndicator.textContent();
        return {
          success: false,
          classInfo,
          error: errorText || 'Booking failed',
        };
      }
      
      return {
        success: false,
        classInfo,
        error: 'Could not confirm booking status',
      };
      
    } catch (error) {
      console.error('❌ Booking error:', error);
      return {
        success: false,
        classInfo,
        error: String(error),
      };
    }
  }
  
  /**
   * Check if logged in
   */
  async isLoggedIn(): Promise<boolean> {
    return this.loggedIn;
  }
  
  /**
   * Close browser
   */
  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.context = null;
      this.page = null;
      this.loggedIn = false;
    }
  }
}
