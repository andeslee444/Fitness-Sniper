/**
 * Arketa HTTP API Client
 *
 * Fetches class schedules from the public Arketa widget API:
 * GET https://app.arketa.co/api/widget/data?widgetName={name}&type=classes&start_time={unix}
 *
 * No authentication needed for schedule data.
 * Used by: Saint NYC (sauna & ice bath appointments)
 */

import type { ClassScheduleRow } from '../types';

const ARKETA_BASE = 'https://app.arketa.co';

interface ArketaLocation {
  id: string;
  name: string;
  address: string;
}

interface ArketaClass {
  id: string;
  name: string;
  class_name?: string;
  start_time: number; // Unix timestamp
  duration: number; // Minutes
  max_capacity: number;
  total_booked: number;
  experience_type: string;
  appointment_type: string | null;
  service_id: string;
  location: ArketaLocation | null;
  roomId: string;
  isBookable: boolean;
  hidden?: boolean;
  canceled?: boolean;
  deleted?: boolean;
}

interface ArketaWidgetResponse {
  data: {
    classes: ArketaClass[];
    widget?: Record<string, unknown>;
  };
}

/**
 * Convert a Unix timestamp to "H:MM AM/PM" in America/New_York timezone
 */
function formatUnixToTime12(unixTs: number): string {
  const date = new Date(unixTs * 1000);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/New_York',
  });
}

/**
 * Convert a Unix timestamp to "YYYY-MM-DD" in America/New_York timezone
 */
function formatUnixToDate(unixTs: number): string {
  const date = new Date(unixTs * 1000);
  const parts = date.toLocaleDateString('en-CA', { timeZone: 'America/New_York' }); // en-CA gives YYYY-MM-DD
  return parts;
}

/**
 * Fetch classes from the Arketa widget API.
 *
 * The API returns up to 250 classes per request from start_time onward (no end
 * param, no pagination link). To cover a full date range we paginate manually:
 * when a response returns 250 results and the last class's date is still before
 * maxDate, we advance start_time past the last result and fetch again.
 *
 * @param widgetName - Arketa widget name (e.g. "saint")
 * @param studioSlug - Internal studio slug (e.g. "saint")
 * @param locationId - Arketa location ID (e.g. "HdyzqlKBXi8OmbpxwxEB")
 * @param minDate - "YYYY-MM-DD"
 * @param maxDate - "YYYY-MM-DD"
 */
export async function fetchArketaClassesFromAPI(
  widgetName: string,
  studioSlug: string,
  locationId: string,
  minDate: string,
  maxDate: string,
): Promise<ClassScheduleRow[]> {
  const ARKETA_PAGE_LIMIT = 250;
  const MAX_PAGES = 10; // safety cap

  // Convert minDate to Unix timestamp at midnight ET
  let currentStartTime = Math.floor(new Date(`${minDate}T00:00:00-05:00`).getTime() / 1000);
  const maxDateEnd = `${maxDate}T23:59:59-05:00`;
  const maxTimestamp = Math.floor(new Date(maxDateEnd).getTime() / 1000);

  const results: ClassScheduleRow[] = [];
  const seenIds = new Set<string>();

  for (let page = 0; page < MAX_PAGES; page++) {
    const url = `${ARKETA_BASE}/api/widget/data?widgetName=${encodeURIComponent(widgetName)}&type=classes&start_time=${currentStartTime}`;

    const response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
      },
    });

    if (!response.ok) {
      throw new Error(`Arketa API returned ${response.status}: ${response.statusText}`);
    }

    const json = (await response.json()) as ArketaWidgetResponse;
    const classes = json.data?.classes || [];

    let lastTimestamp = currentStartTime;

    for (const item of classes) {
      // Track the latest timestamp for pagination
      if (item.start_time > lastTimestamp) lastTimestamp = item.start_time;

      // Deduplicate across pages (overlapping start_time boundaries)
      if (seenIds.has(item.id)) continue;
      seenIds.add(item.id);

      // Filter out internal time blocks
      if (item.appointment_type === 'time_block') continue;
      // Filter out hidden/canceled/deleted
      if (item.hidden || item.canceled || item.deleted) continue;
      // Filter by location
      if (locationId && item.location?.id !== locationId) continue;

      const classDate = formatUnixToDate(item.start_time);

      // Filter to requested date range
      if (classDate < minDate || classDate > maxDate) continue;

      const className = item.name || item.class_name || null;
      // Arketa private sessions report max_capacity=1, total_booked=1 even when bookable.
      // Trust isBookable as the source of truth — if bookable, at least 1 spot is open.
      const calcSpots = Math.max(0, item.max_capacity - item.total_booked);
      const spotsRemaining = item.isBookable ? Math.max(1, calcSpots) : calcSpots;

      results.push({
        studio_slug: studioSlug,
        location_id: locationId,
        class_date: classDate,
        class_time: formatUnixToTime12(item.start_time),
        class_name: className,
        instructor: null, // Arketa appointments don't have separate instructors
        duration_minutes: item.duration,
        available: item.isBookable,
        spots_remaining: spotsRemaining,
        booking_opens_at: null, // Arketa doesn't expose booking open times
      });
    }

    // Stop if: fewer than the limit returned (no more data), or we've passed maxDate
    if (classes.length < ARKETA_PAGE_LIMIT || lastTimestamp >= maxTimestamp) break;

    // Advance start_time past the last result for the next page
    currentStartTime = lastTimestamp + 1;
  }

  return results;
}
