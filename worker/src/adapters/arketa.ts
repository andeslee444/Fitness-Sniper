/**
 * Arketa Adapter (Firebase/Firestore backend)
 *
 * Supports: Saint NYC (private sauna & ice bath)
 *
 * Auth: Firebase REST API (signInWithPassword)
 * Schedule: Public widget API (no auth needed)
 * Booking: POST https://app.arketa.co/api/app/checkout?classId={id} (auth required)
 *
 * Arketa uses Firebase for authentication and Firestore for data.
 * The booking endpoint needs the Firebase ID token as a Bearer token.
 */

import { STUDIOS, type StudioConfig } from '@fitness-sniper/shared';
import { fetchArketaClassesFromAPI } from '../scrapers/arketa-api-client.js';
import type { BookingResult, StudioCredentials } from '@fitness-sniper/shared';

export type StepLogger = (step: string, detail: string) => void;

// Firebase Web API key for Arketa (sutra-prod project)
// This is a public client-side key, not a secret
const FIREBASE_API_KEY = 'AIzaSyCNSSHH1yTQ492d42qWOG_V_m2uQGdQF74';

interface FirebaseAuthResponse {
  idToken: string;
  email: string;
  refreshToken: string;
  expiresIn: string;
  localId: string;
  registered?: boolean;
}

interface FirebaseAuthError {
  error: {
    code: number;
    message: string;
    errors: Array<{ message: string; domain: string; reason: string }>;
  };
}

interface ArketaCheckoutResponse {
  success: boolean;
  message?: string | { raw?: { message?: string } };
  reservationId?: string;
  clientSecret?: string;
  error?: string;
}

export class ArketaAdapter {
  private studio: StudioConfig;
  private credentials: StudioCredentials;
  private idToken: string | null = null;
  private firebaseUid: string | null = null;
  private log: StepLogger;

  constructor(
    studioSlug: string,
    credentials: StudioCredentials,
    opts: { log?: StepLogger } = {},
  ) {
    const studio = STUDIOS[studioSlug];
    if (!studio) {
      throw new Error(`Unknown studio: ${studioSlug}. Available: ${Object.keys(STUDIOS).join(', ')}`);
    }
    if (studio.platform !== 'arketa') {
      throw new Error(`${studioSlug} is not an Arketa studio (platform=${studio.platform})`);
    }
    this.studio = studio;
    this.credentials = credentials;
    this.log = opts.log || ((step, detail) => console.log(`[${step}] ${detail}`));
  }

  // ── Initialization ─────────────────────────────────────────

  async init(): Promise<void> {
    this.log('init', `Authenticating with ${this.studio.name} via Firebase...`);
    await this.authenticate();
    this.log('init', this.idToken ? 'Authentication successful' : 'Authentication failed');
  }

  async close(): Promise<void> {
    this.idToken = null;
    this.firebaseUid = null;
  }

  // ── Authentication ─────────────────────────────────────────

  private async authenticate(): Promise<void> {
    try {
      this.log('auth', 'Logging in via Firebase signInWithPassword...');

      const res = await fetch(
        `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${FIREBASE_API_KEY}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: this.credentials.email,
            password: this.credentials.password,
            returnSecureToken: true,
          }),
        },
      );

      if (!res.ok) {
        const errorBody = (await res.json()) as FirebaseAuthError;
        const errorMsg = errorBody.error?.message || `HTTP ${res.status}`;
        this.log('auth', `Firebase login failed: ${errorMsg}`);
        return;
      }

      const data = (await res.json()) as FirebaseAuthResponse;
      this.idToken = data.idToken;
      this.firebaseUid = data.localId;
      this.log('auth', `Logged in as ${data.email} (uid: ${data.localId})`);
    } catch (err) {
      this.log('auth', `Login error: ${err instanceof Error ? err.message : err}`);
    }
  }

  // ── Booking ────────────────────────────────────────────────

  async bookClass(
    locationId: string,
    time: string,
    _preferredSpots?: string[],
    classDate?: Date,
  ): Promise<BookingResult> {
    if (!this.idToken) {
      return { success: false, message: 'Not authenticated' };
    }

    try {
      // Step 1: Find matching session from schedule
      this.log('book', `Searching for session at ${time} in ${locationId}${classDate ? ` on ${classDate.toISOString().split('T')[0]}` : ''}`);

      const partnerId = this.studio.partnerId || '';
      const serviceId = this.studio.serviceId || '';
      // Use classDate if provided, otherwise search from today
      const searchDate = classDate || new Date();
      const dateStr = searchDate.toISOString().split('T')[0];
      // Search a week out from the target date to find the occurrence
      const weekOut = new Date(searchDate);
      weekOut.setDate(weekOut.getDate() + 7);
      const weekOutStr = weekOut.toISOString().split('T')[0];

      const classes = await fetchArketaClassesFromAPI(
        partnerId,
        serviceId,
        this.studio.slug,
        locationId,
        dateStr,
        weekOutStr,
      );

      const matchingClass = classes.find((c) => {
        const classTime = c.class_time.replace(/\s+/g, ' ').trim();
        const targetTime = time.replace(/\s+/g, ' ').trim();
        return classTime === targetTime;
      });

      if (!matchingClass) {
        return { success: false, message: `No session found at ${time} in ${locationId}` };
      }

      if (!matchingClass.available) {
        return { success: false, message: `Session at ${time} is full (0 spots remaining)` };
      }

      this.log('book', `Found: ${matchingClass.class_name} on ${matchingClass.class_date} (${matchingClass.spots_remaining} spots)`);

      // Step 2: Book via Arketa API
      // The booking endpoint uses the class/session ID from the widget data
      // We need to refetch the raw data to get the Arketa class ID
      const rawWidgetName = this.studio.widgetName || this.studio.tenant;
      const rawClasses = await this.fetchRawClasses(rawWidgetName, dateStr);
      const rawMatch = rawClasses.find((c) => {
        if (c.appointment_type === 'time_block') return false;
        if (c.hidden || c.canceled || c.deleted) return false;
        if (c.location?.id !== locationId) return false;
        const classDate = this.formatUnixToDate(c.start_time);
        const classTime = this.formatUnixToTime12(c.start_time);
        return classDate === matchingClass.class_date &&
          classTime.replace(/\s+/g, ' ').trim() === time.replace(/\s+/g, ' ').trim();
      });

      if (!rawMatch) {
        return { success: false, message: `Could not find raw session data for ${time}` };
      }

      this.log('book', `Booking session ${rawMatch.id} (${rawMatch.name})...`);

      // Arketa checkout endpoint: POST /api/app/checkout?classId={id}
      // Body contains the class data + booking metadata
      const checkoutBody = {
        ...rawMatch,
        bookingType: 'class',
        collection: 'classes',
        bookingLocation: 'widget',
        bookingWidget: this.studio.widgetName || this.studio.tenant,
      };

      const bookingRes = await fetch(
        `https://app.arketa.co/api/app/checkout?classId=${encodeURIComponent(rawMatch.id)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${this.idToken}`,
          },
          body: JSON.stringify(checkoutBody),
        },
      );

      if (!bookingRes.ok) {
        const errorText = await bookingRes.text();
        this.log('book', `Checkout API returned ${bookingRes.status}: ${errorText.substring(0, 300)}`);
        return { success: false, message: `Booking failed (${bookingRes.status}): ${errorText.substring(0, 200)}` };
      }

      const bookingData = (await bookingRes.json()) as ArketaCheckoutResponse;
      this.log('book', `Checkout response: ${JSON.stringify(bookingData).substring(0, 300)}`);

      if (!bookingData.success) {
        const errMsg = typeof bookingData.message === 'string'
          ? bookingData.message
          : bookingData.message?.raw?.message || 'Unknown checkout error';
        return { success: false, message: `Checkout failed: ${errMsg}` };
      }

      return {
        success: true,
        message: `Reserved ${this.studio.name} at ${time} — ${matchingClass.class_name || 'Session'}`,
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.log('book', `Booking failed: ${message}`);
      return { success: false, message };
    }
  }

  // ── Raw API Access ─────────────────────────────────────────

  private async fetchRawClasses(widgetName: string, minDate: string): Promise<RawArketaClass[]> {
    const minDateObj = new Date(`${minDate}T00:00:00-05:00`);
    const startTime = Math.floor(minDateObj.getTime() / 1000);
    const url = `https://app.arketa.co/api/widget/data?widgetName=${encodeURIComponent(widgetName)}&type=classes&start_time=${startTime}`;

    const res = await fetch(url, {
      headers: {
        Accept: 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
      },
    });

    if (!res.ok) throw new Error(`Arketa raw API returned ${res.status}`);
    const json = await res.json();
    return json.data?.classes || [];
  }

  private formatUnixToTime12(unixTs: number): string {
    const date = new Date(unixTs * 1000);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone: 'America/New_York',
    });
  }

  private formatUnixToDate(unixTs: number): string {
    const date = new Date(unixTs * 1000);
    return date.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  }

  // ── Utility ────────────────────────────────────────────────

  async screenshot(_name: string): Promise<string | null> {
    return null; // API-only adapter, no browser
  }
}

// Raw Arketa class shape from the widget API
interface RawArketaClass {
  id: string;
  name: string;
  class_name?: string;
  start_time: number;
  duration: number;
  max_capacity: number;
  total_booked: number;
  experience_type: string;
  appointment_type: string | null;
  service_id: string;
  location: { id: string; name: string } | null;
  roomId: string;
  isBookable: boolean;
  hidden?: boolean;
  canceled?: boolean;
  deleted?: boolean;
}
