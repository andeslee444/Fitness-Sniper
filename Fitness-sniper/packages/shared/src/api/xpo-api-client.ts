/**
 * Xponential HTTP API Client
 *
 * Fetches class schedules from the public Xponential member portal API:
 * GET https://members.{brand}.com/api/v2/locations/{slug}/schedule_entries
 *
 * No authentication needed for schedule data.
 */

import https from 'node:https';
import { formatTime12 } from '../types';
import type { ClassScheduleRow } from '../types';

interface XpoScheduleEntry {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string;
  capacity: number;
  free_spots: number;
  instructor: { id: string; name: string } | null;
  has_waitlist: boolean;
  waitlist_size: number;
  booking_opens_at: string | null;
  booking_closes_at: string | null;
}

interface XpoScheduleResponse {
  schedule_entries: XpoScheduleEntry[];
}

// Cloudflare WAF-protected domains that block requests based on TLS fingerprinting.
// These need browser-like cipher suites to avoid 403 blocks.
const CF_WAF_DOMAINS = new Set(['members.purebarre.com']);

// Browser-like TLS cipher suites that pass Cloudflare's fingerprint check
const BROWSER_CIPHERS = [
  'TLS_AES_128_GCM_SHA256',
  'TLS_AES_256_GCM_SHA384',
  'TLS_CHACHA20_POLY1305_SHA256',
  'ECDHE-ECDSA-AES128-GCM-SHA256',
  'ECDHE-RSA-AES128-GCM-SHA256',
].join(':');

const REQUEST_HEADERS = {
  'Accept': 'application/json',
  'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
};

/**
 * HTTPS request with custom TLS ciphers to bypass Cloudflare WAF fingerprinting.
 * Used for domains (like members.purebarre.com) that block standard Node.js TLS.
 */
function fetchWithTLSCiphers(url: string): Promise<{ ok: boolean; status: number; json: () => Promise<XpoScheduleResponse> }> {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const req = https.request(
      {
        hostname: parsed.hostname,
        port: 443,
        path: parsed.pathname + parsed.search,
        method: 'GET',
        headers: {
          ...REQUEST_HEADERS,
          'Accept-Encoding': 'identity',
        },
        ciphers: BROWSER_CIPHERS,
      },
      (res) => {
        let body = '';
        res.on('data', (chunk) => (body += chunk));
        res.on('end', () => {
          const status = res.statusCode || 0;
          resolve({
            ok: status >= 200 && status < 300,
            status,
            json: () => Promise.resolve(JSON.parse(body)),
          });
        });
      },
    );
    req.on('error', reject);
    req.end();
  });
}

/**
 * Fetch classes from the Xponential member portal API.
 *
 * @param membersDomain - e.g. "https://members.cyclebar.com"
 * @param studioSlug - e.g. "cyclebar"
 * @param locationSlug - e.g. "cyclebar-hoboken"
 * @param minDate - "YYYY-MM-DD"
 * @param maxDate - "YYYY-MM-DD"
 */
export async function fetchXpoClassesFromAPI(
  membersDomain: string,
  studioSlug: string,
  locationSlug: string,
  minDate: string,
  maxDate: string,
): Promise<ClassScheduleRow[]> {
  const url = `${membersDomain}/api/v2/locations/${locationSlug}/schedule_entries?start_date=${minDate}&end_date=${maxDate}`;

  // Use custom TLS ciphers for Cloudflare WAF-protected domains
  const hostname = new URL(membersDomain).hostname;
  const response = CF_WAF_DOMAINS.has(hostname)
    ? await fetchWithTLSCiphers(url)
    : await fetch(url, { headers: REQUEST_HEADERS });

  if (!response.ok) {
    throw new Error(`Xpo API returned ${response.status}`);
  }

  const json = (await response.json()) as XpoScheduleResponse;
  const entries = json.schedule_entries || [];

  return entries.map((entry) => {
    const startDate = new Date(entry.starts_at);
    const endDate = new Date(entry.ends_at);
    const durationMinutes = Math.round((endDate.getTime() - startDate.getTime()) / 60000);

    return {
      studio_slug: studioSlug,
      location_id: locationSlug,
      class_date: entry.starts_at.split('T')[0],
      class_time: formatTime12(entry.starts_at),
      class_name: entry.title || null,
      instructor: entry.instructor?.name || null,
      duration_minutes: durationMinutes,
      available: entry.free_spots > 0,
      spots_remaining: entry.free_spots,
    };
  });
}
