/**
 * Mariana Tek API Adapter
 *
 * API-first approach: Browser only for OAuth token capture,
 * then pure REST API for class discovery and booking.
 *
 * Booking via POST /api/customer/v1/me/reservations is sub-second
 * vs multi-second browser automation.
 *
 * Supports: Barry's, Aarmy, SLT, Practice Room (iframe MT studios).
 */

import { STUDIOS, type StudioConfig } from '@fitness-sniper/shared';
import { launchStealthBrowser } from '../stealth/browser.js';
import type { BookingResult, StudioCredentials, ClassInfo } from '@fitness-sniper/shared';

export type StepLogger = (step: string, detail: string) => void;

// MT API response types
interface MTSpot {
  id: string;
  name: string;
  spot_type: { id: string; name: string; is_primary: boolean };
  x_position: number;
  y_position: number;
  is_available: boolean;
}

interface MTClass {
  id: string;
  start_datetime: string;
  end_datetime: string;
  class_type: { name: string };
  instructors: Array<{ name: string }>;
  location: { id: string; name: string };
  layout_format: string;
  available_spot_count: number;
  spot_options?: {
    primary_availability: number;
    secondary_availability: number;
    waitlist_availability: number;
    standby_availability: number;
  };
  layout?: {
    id: string;
    name: string;
    spots: MTSpot[];
  };
  booking_start_datetime: string;
}

interface MTReservation {
  id: string;
  status: string;
  spot: { id: string; name: string; spot_type: { name: string } } | null;
  reservation_type: string;
  waitlist_position: number | null;
}

// All MT iframe studios share the same OAuth client_id (Mariana Tek iframe widget)
const MT_IFRAME_CLIENT_ID = 'sbLziNCoF5HcOhkSV6zRL8O7betwd3mDDIQbWZa3';

export class InsufficientCreditsError extends Error {
  public readonly studioName: string;
  public readonly studioUrl: string;

  constructor(studioName: string, studioUrl: string, apiDetail?: string) {
    // Strip URL template placeholders like {location}
    const cleanUrl = studioUrl.replace(/\/?\{[^}]+\}/g, '');
    const msg = `Insufficient credits for ${studioName}. Please purchase more credits or renew your membership at ${cleanUrl}`;
    super(apiDetail ? `${msg} (API: ${apiDetail})` : msg);
    this.name = 'InsufficientCreditsError';
    this.studioName = studioName;
    this.studioUrl = cleanUrl;
  }
}

// Supports: Barry's, Aarmy, SLT, Practice Room (all iframe MT studios)
// Xponential brands (Rumble, CycleBar, etc.) use a different platform — see xponential.ts

export class MarianaTekAdapter {
  private studio: StudioConfig;
  private credentials: StudioCredentials;
  private accessToken: string | null = null;
  private log: StepLogger;
  private apiBase: string;
  private iframeBase: string;

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
    this.apiBase = `https://${studio.tenant}.marianatek.com`;
    this.iframeBase = `https://${studio.tenant}.marianaiframes.com`;
  }

  // ── Initialization: OAuth token capture ──────────────────────

  async init(): Promise<void> {
    this.log('init', `Authenticating with ${this.studio.name} via OAuth PKCE...`);
    await this.authenticate();
    this.log('init', this.accessToken ? 'Authentication successful' : 'Authentication failed');
  }

  async close(): Promise<void> {
    this.accessToken = null;
  }

  // ── Authentication ───────────────────────────────────────────

  private async authenticate(): Promise<void> {
    // Try HTTP-only OAuth PKCE first (no browser needed)
    const token = await this.loginViaOAuthHTTP();
    if (token) { this.accessToken = token; return; }

    // Fallback: browser-based OAuth
    this.log('auth', 'HTTP OAuth failed, falling back to browser');
    const browserToken = await this.loginViaBrowser();
    if (browserToken) {
      this.accessToken = browserToken;
    }
  }

  /**
   * OAuth PKCE login for iframe studios (Barry's, Aarmy, SLT, Practice Room).
   * Pure HTTP — no browser needed.
   */
  private async loginViaOAuthHTTP(): Promise<string | null> {
    try {
      this.log('auth', 'Attempting OAuth HTTP login...');

      const clientId = MT_IFRAME_CLIENT_ID;

      // Generate PKCE code verifier and challenge
      const { codeVerifier, codeChallenge } = await this.generatePKCE();
      const state = Buffer.from(JSON.stringify({ action: 'redirect' })).toString('base64url');
      const nonce = crypto.randomUUID();

      const authorizeParams = new URLSearchParams({
        client_id: clientId,
        response_type: 'code',
        redirect_uri: `${this.iframeBase}/iframe/callback/`,
        scope: 'read:account',
        code_challenge: codeChallenge,
        code_challenge_method: 'S256',
        state,
        nonce,
      });

      const loginPageUrl = `${this.apiBase}/auth/login/?next=/o/authorize/%3F${encodeURIComponent(authorizeParams.toString())}`;
      const loginPageRes = await fetch(loginPageUrl, { redirect: 'manual' });
      const loginPageHtml = await loginPageRes.text();

      // Extract CSRF token
      const csrfMatch = loginPageHtml.match(/name="csrfmiddlewaretoken" value="([^"]+)"/);
      if (!csrfMatch) {
        this.log('auth', 'Could not find CSRF token');
        return null;
      }
      const csrfToken = csrfMatch[1];

      // Get session cookie
      const setCookies = loginPageRes.headers.getSetCookie?.() || [];
      const cookies = setCookies.map(c => c.split(';')[0]).join('; ');

      // Step 2: POST login
      const loginRes = await fetch(`${this.apiBase}/auth/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Cookie': cookies,
          'Referer': loginPageUrl,
        },
        body: new URLSearchParams({
          csrfmiddlewaretoken: csrfToken,
          username: this.credentials.email,
          password: this.credentials.password,
          next: `/o/authorize/?${authorizeParams.toString()}`,
        }),
        redirect: 'manual',
      });

      // Step 3: Follow redirects to get auth code
      let redirectUrl = loginRes.headers.get('location');
      const loginCookies = [
        cookies,
        ...(loginRes.headers.getSetCookie?.() || []).map(c => c.split(';')[0]),
      ].join('; ');

      if (!redirectUrl) {
        this.log('auth', `Login POST returned ${loginRes.status}, no redirect`);
        return null;
      }

      // Follow redirect chain
      let currentUrl = redirectUrl.startsWith('/') ? `${this.apiBase}${redirectUrl}` : redirectUrl;
      let authCode: string | null = null;

      for (let i = 0; i < 5; i++) {
        const res = await fetch(currentUrl, {
          headers: { Cookie: loginCookies },
          redirect: 'manual',
        });

        const nextUrl = res.headers.get('location');
        if (nextUrl?.includes('code=')) {
          const u = new URL(nextUrl.startsWith('/') ? `${this.iframeBase}${nextUrl}` : nextUrl);
          authCode = u.searchParams.get('code');
          break;
        }
        if (!nextUrl) break;
        currentUrl = nextUrl.startsWith('/') ? `${this.apiBase}${nextUrl}` : nextUrl;
      }

      if (!authCode) {
        this.log('auth', 'Could not capture auth code from redirects');
        return null;
      }

      // Step 4: Exchange code for token
      const tokenRes = await fetch(`${this.apiBase}/o/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'authorization_code',
          client_id: clientId,
          code: authCode,
          redirect_uri: `${this.iframeBase}/iframe/callback/`,
          code_verifier: codeVerifier,
        }),
      });

      const tokenData = await tokenRes.json();
      if (tokenData.access_token) {
        this.log('auth', 'HTTP-only login successful!');
        return tokenData.access_token;
      }

      this.log('auth', `Token exchange failed: ${JSON.stringify(tokenData)}`);
      return null;
    } catch (err) {
      this.log('auth', `HTTP login error: ${err instanceof Error ? err.message : err}`);
      return null;
    }
  }

  /**
   * Browser-based OAuth as fallback.
   * Launches stealth browser, logs in, captures access token.
   */
  private async loginViaBrowser(): Promise<string | null> {
    this.log('auth', 'Starting browser-based OAuth...');
    const headless = process.env.NODE_ENV === 'production';
    const { context } = await launchStealthBrowser({ headless });

    try {
      const page = await context.newPage();
      let capturedToken: string | null = null;

      // Listen for token response
      page.on('response', async (res) => {
        if (res.url().includes('/o/token')) {
          try {
            const body = await res.json();
            if (body.access_token) capturedToken = body.access_token;
          } catch { /* not json */ }
        }
      });

      // Navigate to iframe schedule to trigger login
      await page.goto(`${this.iframeBase}/iframe/schedule/daily/`);
      await page.waitForLoadState('networkidle');
      await sleep(2000);

      // Click Log In
      const loginBtn = page.locator('button:has-text("Log In"), a:has-text("Log In")');
      if (await loginBtn.first().isVisible({ timeout: 5000 }).catch(() => false)) {
        await loginBtn.first().click();
        await sleep(3000);
      }

      // Fill credentials if on login page
      if (page.url().includes('/auth/login')) {
        await page.locator('#id_username').fill(this.credentials.email);
        await page.locator('#id_password').fill(this.credentials.password);
        await page.click('button[type="submit"]');
        await page.waitForLoadState('networkidle');
        await sleep(5000);
      }

      this.log('auth', capturedToken ? 'Browser OAuth successful' : 'Browser OAuth failed');
      return capturedToken;
    } finally {
      const browser = context.browser();
      await context.close();
      if (browser) await browser.close();
    }
  }

  private async generatePKCE(): Promise<{ codeVerifier: string; codeChallenge: string }> {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    const codeVerifier = Buffer.from(array).toString('base64url');
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(codeVerifier));
    const codeChallenge = Buffer.from(hash).toString('base64url');
    return { codeVerifier, codeChallenge };
  }

  // ── API Helpers ──────────────────────────────────────────────

  private authHeaders(): Record<string, string> {
    if (!this.accessToken) throw new Error('Not authenticated');
    return { Authorization: `Bearer ${this.accessToken}` };
  }

  private async apiGet<T>(path: string, auth = false): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (auth) Object.assign(headers, this.authHeaders());
    const res = await fetch(`${this.apiBase}/api/customer/v1${path}`, { headers });
    if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
    return res.json();
  }

  private async apiPost<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...this.authHeaders(),
    };
    const res = await fetch(`${this.apiBase}/api/customer/v1${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      const errorText = text.substring(0, 500).toLowerCase();
      if (
        res.status === 402 ||
        errorText.includes('credit') ||
        errorText.includes('payment') ||
        errorText.includes('balance') ||
        errorText.includes('membership') ||
        errorText.includes('package') ||
        errorText.includes('plan') ||
        errorText.includes('purchase') ||
        errorText.includes('insufficient')
      ) {
        throw new InsufficientCreditsError(this.studio.name, this.studio.scheduleUrl, text.substring(0, 300));
      }
      throw new Error(`API POST ${path} returned ${res.status}: ${text.substring(0, 300)}`);
    }
    return res.json();
  }

  // ── Class Discovery (Public API) ─────────────────────────────

  async getClasses(locationApiId: string, date?: Date): Promise<ClassInfo[]> {
    const d = date || new Date();
    const dateStr = d.toISOString().split('T')[0];
    const nextDay = new Date(d);
    nextDay.setDate(nextDay.getDate() + 1);

    const data = await this.apiGet<{ results: MTClass[] }>(
      `/classes?min_start_date=${dateStr}&max_start_date=${nextDay.toISOString().split('T')[0]}&page_size=500&location=${locationApiId}`,
    );

    return data.results.map((c) => ({
      time: new Date(c.start_datetime).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
        timeZone: 'America/New_York',
      }),
      className: c.class_type?.name || 'Unknown',
      instructor: c.instructors?.[0]?.name || '',
      location: c.location?.name || locationApiId,
      date: dateStr,
      available: c.available_spot_count > 0,
      // Extended info
      classId: c.id,
      spotsAvailable: c.available_spot_count,
      layoutFormat: c.layout_format,
      bookingStartDatetime: c.booking_start_datetime,
    }));
  }

  /**
   * Get full class detail including spot layout.
   */
  async getClassDetail(classId: string): Promise<MTClass> {
    return this.apiGet<MTClass>(`/classes/${classId}`);
  }

  // ── Booking (Authenticated API) ──────────────────────────────

  async bookClass(
    location: string,
    time: string,
    preferredSpots?: string[],
  ): Promise<BookingResult> {
    if (!this.accessToken) {
      return { success: false, message: 'Not authenticated' };
    }

    try {
      // Step 1: Find matching class via API
      this.log('book', `Searching for class at ${time} in ${location}`);

      // We need the MT location API ID. Try the location directly.
      // The scheduler should pass the MT location ID.
      const classes = await this.getClasses(location);
      const matchingClass = classes.find((c: any) => {
        // Match by time (fuzzy — compare hours and minutes)
        const classTime = c.time.replace(/\s+/g, ' ').trim();
        const targetTime = time.replace(/\s+/g, ' ').trim();
        return classTime === targetTime;
      }) as any;

      if (!matchingClass) {
        return { success: false, message: `No class found at ${time} in ${location}` };
      }

      if (!matchingClass.available) {
        return { success: false, message: `Class at ${time} is full` };
      }

      this.log('book', `Found class ${matchingClass.classId}: ${matchingClass.className} (${matchingClass.spotsAvailable} spots)`);

      // Step 2: Get class detail with spot layout
      const detail = await this.getClassDetail(matchingClass.classId);
      const spots = detail.layout?.spots || [];
      const availableSpots = spots.filter((s) => s.is_available);

      this.log('book', `Layout: ${detail.layout?.name}, ${availableSpots.length} spots available`);

      // Step 3: Pick a spot
      let targetSpot: MTSpot | undefined;

      if (preferredSpots && preferredSpots.length > 0) {
        for (const name of preferredSpots) {
          targetSpot = availableSpots.find((s) => s.name === name);
          if (targetSpot) {
            this.log('book', `Found preferred spot: ${name} (id=${targetSpot.id})`);
            break;
          }
        }
      }

      if (!targetSpot && availableSpots.length > 0) {
        targetSpot = availableSpots[0];
        this.log('book', `Using first available spot: ${targetSpot.name} (id=${targetSpot.id})`);
      }

      // Step 4: Check payment options
      const paymentOpts = await this.apiGet<{
        user_payment_options: Array<{ id: string; name: string; type: string }>;
      }>(`/classes/${matchingClass.classId}/payment_options`, true);

      if (paymentOpts.user_payment_options.length === 0) {
        const cleanUrl = this.studio.scheduleUrl.replace(/\/?\{[^}]+\}/g, '');
        return {
          success: false,
          message: `Insufficient credits for ${this.studio.name}. Please purchase more credits or renew your membership at ${cleanUrl}`,
        };
      }

      // Step 5: Create reservation
      this.log('book', `Booking class ${matchingClass.classId}, spot ${targetSpot?.name || 'any'}...`);

      const reservationBody: Record<string, unknown> = {
        class_session: matchingClass.classId,
        reservation_type: 'standard',
      };

      if (targetSpot && detail.layout_format === 'pick-a-spot') {
        reservationBody.spot = parseInt(targetSpot.id, 10);
      }

      const reservation = await this.apiPost<MTReservation>('/me/reservations', reservationBody);

      this.log('book', `Reservation created: ${reservation.id}, status: ${reservation.status}`);

      return {
        success: true,
        message: `Reserved ${this.studio.name} at ${time} — ${matchingClass.className}`,
        spot: reservation.spot?.name || targetSpot?.name || undefined,
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.log('book', `Booking failed: ${message}`);

      // Surface credit/payment errors clearly
      if (err instanceof InsufficientCreditsError) {
        return { success: false, message: err.message };
      }

      // If it's a waitlist scenario, try waitlist
      if (message.includes('full') || message.includes('sold out')) {
        return await this.joinWaitlist(location, time);
      }

      return { success: false, message };
    }
  }

  /**
   * Join waitlist for a full class.
   */
  private async joinWaitlist(location: string, time: string): Promise<BookingResult> {
    try {
      this.log('book', 'Class full — attempting waitlist...');
      const classes = await this.getClasses(location);
      const match = classes.find((c: any) => c.time === time) as any;
      if (!match) return { success: false, message: 'Class not found for waitlist' };

      const reservation = await this.apiPost<MTReservation>('/me/reservations', {
        class_session: match.classId,
        reservation_type: 'waitlist',
      });

      return {
        success: true,
        message: `Joined waitlist (position ${reservation.waitlist_position || '?'}) for ${this.studio.name} at ${time}`,
      };
    } catch (err) {
      return { success: false, message: `Waitlist failed: ${err instanceof Error ? err.message : err}` };
    }
  }

  // ── Utility ──────────────────────────────────────────────────

  /** No-op — included for API compatibility with browser-based adapter */
  async screenshot(_name: string): Promise<string | null> {
    return null;
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
