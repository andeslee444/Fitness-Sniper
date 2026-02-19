/**
 * Xponential Fitness Adapter (ClubReady backend)
 *
 * Supports: Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre
 *
 * These studios use Xponential's unified member portal (members.{brand}.com)
 * backed by a Rails/ClubReady API — NOT Mariana Tek.
 *
 * Auth: POST /api/xpass/sessions → JWT Bearer token via X-Authorization header
 * Schedule: GET /api/v2/locations/{slug}/schedule_entries (public, no auth)
 * Booking: POST /api/v2/locations/{slug}/bookings/{entry_id} (auth required)
 */

import { STUDIOS, type StudioConfig } from '@fitness-sniper/shared';
import type { BookingResult, StudioCredentials, ClassInfo } from '@fitness-sniper/shared';

export type StepLogger = (step: string, detail: string) => void;

// Xponential API response types
interface XpoScheduleEntry {
  id: string;
  type: string;
  title: string;
  description: string;
  starts_at: string;
  ends_at: string;
  capacity: number;
  free_spots: number;
  room_id: string | null;
  clubready_id: string;
  piq_id: string | null;
  instructor: { id: string; name: string } | null;
  location_id: string;
  booking_opens_at: string | null;
  booking_closes_at: string | null;
  free_cancel_until: string | null;
  has_waitlist: boolean;
  waitlist_size: number;
  booking_url: string | null;
}

interface XpoSession {
  access_token: string;
  access_token_expires_at: string;
  email: string;
  first_name: string;
  last_name: string;
  clubready_id: string;
  location_id: string;
  brand_id: number;
}

interface XpoBooking {
  id: string;
  type: string;
  status: string;
  seat_id: string | null;
  seat_label: string | null;
  waitlist_position: number | null;
  schedule_entry: XpoScheduleEntry;
}

export class InsufficientCreditsError extends Error {
  public readonly studioName: string;
  public readonly studioUrl: string;

  constructor(studioName: string, studioUrl: string, apiDetail?: string) {
    const cleanUrl = studioUrl.replace(/\/?\{[^}]+\}/g, '');
    const msg = `Insufficient credits for ${studioName}. Please purchase more credits or renew your membership at ${cleanUrl}`;
    super(apiDetail ? `${msg} (API: ${apiDetail})` : msg);
    this.name = 'InsufficientCreditsError';
    this.studioName = studioName;
    this.studioUrl = cleanUrl;
  }
}

export class XponentialAdapter {
  private studio: StudioConfig;
  private credentials: StudioCredentials;
  private accessToken: string | null = null;
  private log: StepLogger;
  private apiBase: string;

  constructor(
    studioSlug: string,
    credentials: StudioCredentials,
    opts: { log?: StepLogger } = {},
  ) {
    const studio = STUDIOS[studioSlug];
    if (!studio) {
      throw new Error(`Unknown studio: ${studioSlug}. Available: ${Object.keys(STUDIOS).join(', ')}`);
    }
    if (studio.platform !== 'xponential') {
      throw new Error(`${studioSlug} is not an Xponential studio (platform=${studio.platform})`);
    }
    this.studio = studio;
    this.credentials = credentials;
    this.log = opts.log || ((step, detail) => console.log(`[${step}] ${detail}`));
    this.apiBase = studio.membersDomain || `https://members.${studio.tenant}.com`;
  }

  // ── Initialization ─────────────────────────────────────────

  async init(): Promise<void> {
    this.log('init', `Authenticating with ${this.studio.name} via JWT...`);
    await this.authenticate();
    this.log('init', this.accessToken ? 'Authentication successful' : 'Authentication failed');
  }

  async close(): Promise<void> {
    this.accessToken = null;
  }

  // ── Authentication ─────────────────────────────────────────

  private async authenticate(): Promise<void> {
    try {
      this.log('auth', 'Logging in via /api/xpass/sessions...');

      const res = await fetch(`${this.apiBase}/api/xpass/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          email: this.credentials.email,
          password: this.credentials.password,
        }),
      });

      if (!res.ok) {
        const body = await res.text();
        this.log('auth', `Login failed (${res.status}): ${body.substring(0, 200)}`);
        return;
      }

      const session: XpoSession = await res.json();
      this.accessToken = session.access_token;
      this.log('auth', `Logged in as ${session.first_name} ${session.last_name} (${session.email})`);
    } catch (err) {
      this.log('auth', `Login error: ${err instanceof Error ? err.message : err}`);
    }
  }

  // ── API Helpers ────────────────────────────────────────────

  private authHeaders(): Record<string, string> {
    if (!this.accessToken) throw new Error('Not authenticated');
    return { 'X-Authorization': `Bearer ${this.accessToken}` };
  }

  private async apiGet<T>(path: string, auth = false): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (auth) Object.assign(headers, this.authHeaders());
    const res = await fetch(`${this.apiBase}${path}`, { headers });
    if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
    return res.json();
  }

  private async apiPost<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...this.authHeaders(),
    };
    const res = await fetch(`${this.apiBase}${path}`, {
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

  private async apiDelete(path: string): Promise<void> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...this.authHeaders(),
    };
    const res = await fetch(`${this.apiBase}${path}`, { method: 'DELETE', headers });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API DELETE ${path} returned ${res.status}: ${text.substring(0, 300)}`);
    }
  }

  // ── Class Discovery (Public API) ───────────────────────────

  /**
   * Get classes for a location.
   * Location slug format: {brand_slug}-{location_name} (e.g. 'cyclebar-hoboken')
   */
  async getClasses(locationSlug: string, date?: Date): Promise<ClassInfo[]> {
    const d = date || new Date();
    const dateStr = d.toISOString().split('T')[0];
    const nextDay = new Date(d);
    nextDay.setDate(nextDay.getDate() + 1);

    const data = await this.apiGet<{ schedule_entries: XpoScheduleEntry[] }>(
      `/api/v2/locations/${locationSlug}/schedule_entries?start_date=${dateStr}&end_date=${nextDay.toISOString().split('T')[0]}`,
    );

    return (data.schedule_entries || []).map((e) => ({
      time: new Date(e.starts_at).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
        timeZone: 'America/New_York',
      }),
      className: e.title || 'Unknown',
      instructor: e.instructor?.name || '',
      location: e.location_id || locationSlug,
      date: dateStr,
      available: e.free_spots > 0,
      // Extended info
      entryId: e.id,
      freeSpots: e.free_spots,
      capacity: e.capacity,
      hasWaitlist: e.has_waitlist,
      waitlistSize: e.waitlist_size,
      bookingOpensAt: e.booking_opens_at,
    }));
  }

  // ── Booking (Authenticated API) ────────────────────────────

  async bookClass(
    locationSlug: string,
    time: string,
    preferredSpots?: string[],
  ): Promise<BookingResult> {
    if (!this.accessToken) {
      return { success: false, message: 'Not authenticated' };
    }

    try {
      // Step 1: Find matching class
      this.log('book', `Searching for class at ${time} in ${locationSlug}`);
      const classes = await this.getClasses(locationSlug);
      const matchingClass = classes.find((c) => {
        const classTime = c.time.replace(/\s+/g, ' ').trim();
        const targetTime = time.replace(/\s+/g, ' ').trim();
        return classTime === targetTime;
      }) as any;

      if (!matchingClass) {
        return { success: false, message: `No class found at ${time} in ${locationSlug}` };
      }

      if (!matchingClass.available) {
        if (matchingClass.hasWaitlist) {
          return await this.joinWaitlist(locationSlug, matchingClass.entryId, matchingClass.className, time);
        }
        return { success: false, message: `Class at ${time} is full (no waitlist)` };
      }

      this.log('book', `Found: ${matchingClass.className} (${matchingClass.freeSpots} spots)`);

      // Step 2: Book the class
      const bookingBody: Record<string, unknown> = { waitlist: false };
      if (preferredSpots && preferredSpots.length > 0) {
        bookingBody.seat_id = preferredSpots[0];
      }

      const booking = await this.apiPost<XpoBooking>(
        `/api/v2/locations/${locationSlug}/bookings/${matchingClass.entryId}`,
        bookingBody,
      );

      this.log('book', `Booked! Status: ${booking.status}, seat: ${booking.seat_label || 'any'}`);

      return {
        success: true,
        message: `Reserved ${this.studio.name} at ${time} — ${matchingClass.className}`,
        spot: booking.seat_label || undefined,
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.log('book', `Booking failed: ${message}`);

      // Surface credit/payment errors clearly
      if (err instanceof InsufficientCreditsError) {
        return { success: false, message: err.message };
      }

      return { success: false, message };
    }
  }

  private async joinWaitlist(
    locationSlug: string,
    entryId: string,
    className: string,
    time: string,
  ): Promise<BookingResult> {
    try {
      this.log('book', 'Class full — joining waitlist...');
      const booking = await this.apiPost<XpoBooking>(
        `/api/v2/locations/${locationSlug}/bookings/${entryId}`,
        { waitlist: true },
      );

      return {
        success: true,
        message: `Joined waitlist (position ${booking.waitlist_position || '?'}) for ${this.studio.name} at ${time} — ${className}`,
      };
    } catch (err) {
      return { success: false, message: `Waitlist failed: ${err instanceof Error ? err.message : err}` };
    }
  }

  // ── Utility ────────────────────────────────────────────────

  async screenshot(_name: string): Promise<string | null> {
    return null;
  }
}
