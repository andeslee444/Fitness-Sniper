/**
 * Mariana Tek HTTP API Client
 *
 * Calls the public Customer API at https://{tenant}.marianatek.com/api/customer/v1/classes
 * to fetch class schedules without needing a browser.
 *
 * The API returns a standard REST pagination format (count/next/results)
 * with inline relationships (location, instructors, class_type).
 */

import { formatTime12 } from '../types';
import type { ClassScheduleRow } from '../types';
import { STUDIO_LOCATIONS } from '../studios';

interface MTInstructor {
  id: string;
  name: string;
  bio: string | null;
}

interface MTClassType {
  id: string;
  name: string;
  duration: number;
  description: string;
}

interface MTLocation {
  id: string;
  name: string;
  city: string;
}

interface MTClassResult {
  id: string;
  name: string;
  start_date: string; // "YYYY-MM-DD"
  start_time: string; // "HH:MM:SS"
  start_datetime: string; // ISO 8601 UTC
  is_cancelled: boolean;
  available_spot_count: number;
  capacity: number;
  class_type: MTClassType | null;
  instructors: MTInstructor[];
  location: MTLocation;
}

interface MTApiResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: MTClassResult[];
}

/**
 * Convert "HH:MM:SS" (24h) to "H:MM AM/PM" format
 */
function formatTime24to12(time24: string): string {
  const [hStr, mStr] = time24.split(':');
  let hours = parseInt(hStr, 10);
  const minutes = mStr;
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12 || 12;
  return `${hours}:${minutes} ${ampm}`;
}

/**
 * Fetch classes from the Mariana Tek Customer API for a given tenant and date range.
 *
 * Optionally filters by location name (matched against STUDIO_LOCATIONS config).
 * Throws on non-200 responses (caller should catch and fall back).
 */
export async function fetchClassesFromAPI(
  tenant: string,
  studioSlug: string,
  locationId: string,
  minDate: string, // "YYYY-MM-DD"
  maxDate: string, // "YYYY-MM-DD"
): Promise<ClassScheduleRow[]> {
  const allClasses: ClassScheduleRow[] = [];

  // Resolve location name for filtering from our config
  const locationConfig = STUDIO_LOCATIONS[studioSlug]?.find((l) => l.id === locationId);
  const locationName = locationConfig?.name; // e.g. "NoHo", "Chelsea"

  let url: string | null =
    `https://${tenant}.marianatek.com/api/customer/v1/classes?min_start_date=${minDate}&max_start_date=${maxDate}&page_size=100`;

  while (url) {
    const response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
      },
    });

    if (!response.ok) {
      throw new Error(`MT API returned ${response.status}: ${response.statusText}`);
    }

    const json = (await response.json()) as MTApiResponse;

    for (const item of json.results) {
      if (item.is_cancelled) continue;

      // Filter by location name if we have one
      if (locationName && item.location.name !== locationName) continue;

      const instructorName = item.instructors.length > 0
        ? item.instructors[0].name
        : null;

      const className = item.name || item.class_type?.name || null;
      const duration = item.class_type?.duration || null;

      allClasses.push({
        studio_slug: studioSlug,
        location_id: locationId,
        class_date: item.start_date,
        class_time: formatTime24to12(item.start_time),
        class_name: className,
        instructor: instructorName,
        duration_minutes: duration,
        available: item.available_spot_count > 0,
        spots_remaining: item.available_spot_count,
      });
    }

    // Follow pagination
    url = json.next || null;
  }

  return allClasses;
}
