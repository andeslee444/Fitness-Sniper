/**
 * Xponential HTTP API Client
 *
 * Fetches class schedules from the public Xponential member portal API:
 * GET https://members.{brand}.com/api/v2/locations/{slug}/schedule_entries
 *
 * No authentication needed for schedule data.
 */

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

  const response = await fetch(url, {
    headers: {
      Accept: 'application/json',
      'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    },
  });

  if (!response.ok) {
    throw new Error(`Xpo API returned ${response.status}: ${response.statusText}`);
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
