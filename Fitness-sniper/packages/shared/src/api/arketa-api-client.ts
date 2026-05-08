/**
 * Arketa HTTP API Client
 *
 * Fetches appointment schedules from the real Arketa Cloud Run API:
 *   GET {base}/{partnerId}/services/{serviceId}/availableDays
 *   GET {base}/{partnerId}/services/{serviceId}/availableTimes
 *
 * No authentication needed for schedule data.
 * Used by: Saint NYC (sauna & ice bath appointments)
 */

import type { ClassScheduleRow } from '../types';

const ARKETA_WIDGET_API = 'https://widget-api-tkaeguucxq-uc.a.run.app';
const TIMEZONE = 'America/New_York';
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36';

interface AvailableDayEntry {
  date: string; // "2026-02-26T00:00:00-05:00"
  isAvailable: boolean;
}

interface StartTimeEntry {
  label: string;
  dateString: string; // ISO "2026-02-26T22:15:00.000Z"
  serviceId: string;
  roomId: string;
  locationId: string;
}

interface AvailableTimesResponse {
  slots: {
    type: string;
    startTimes: StartTimeEntry[];
    roomId: string;
    roomName: string;
  }[];
  durationInMinutes: number;
}

/**
 * Convert an ISO datetime string to "H:MM AM/PM" in America/New_York timezone
 */
function formatISOToTime12(isoStr: string): string {
  return new Date(isoStr).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: TIMEZONE,
  });
}

/**
 * Convert an ISO datetime string to "YYYY-MM-DD" in America/New_York timezone
 */
function formatISOToDate(isoStr: string): string {
  return new Date(isoStr).toLocaleDateString('en-CA', { timeZone: TIMEZONE });
}

/**
 * Get all unique months (YYYY-MM) that span [startDate, endDate].
 * Returns array of { start: "YYYY-MM-01", end: "YYYY-MM-last_day" }.
 */
function getMonthRanges(startDate: string, endDate: string): { start: string; end: string }[] {
  const ranges: { start: string; end: string }[] = [];
  const [startY, startM] = startDate.split('-').map(Number);
  const [endY, endM] = endDate.split('-').map(Number);

  let y = startY;
  let m = startM;

  while (y < endY || (y === endY && m <= endM)) {
    const monthStart = `${y}-${String(m).padStart(2, '0')}-01`;
    const lastDay = new Date(y, m, 0).getDate(); // day 0 of next month = last day of this month
    const monthEnd = `${y}-${String(m).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;

    // Clamp to requested range
    const rangeStart = monthStart < startDate ? startDate : monthStart;
    const rangeEnd = monthEnd > endDate ? endDate : monthEnd;

    ranges.push({ start: rangeStart, end: rangeEnd });

    m++;
    if (m > 12) {
      m = 1;
      y++;
    }
  }

  return ranges;
}

/**
 * Fetch available days for a single month range.
 */
async function fetchAvailableDays(
  partnerId: string,
  serviceId: string,
  locationId: string,
  startDate: string,
  endDate: string,
): Promise<AvailableDayEntry[]> {
  const params = new URLSearchParams({
    instructorId: '',
    locationId,
    roomId: 'any',
    startDate,
    endDate,
    timezone: TIMEZONE,
  });

  const url = `${ARKETA_WIDGET_API}/${partnerId}/services/${serviceId}/availableDays?${params}`;
  const res = await fetch(url, { headers: { Accept: 'application/json', 'User-Agent': UA } });

  if (!res.ok) {
    throw new Error(`Arketa availableDays ${res.status}`);
  }

  return (await res.json()) as AvailableDayEntry[];
}

/**
 * Fetch available time slots for a single date.
 */
async function fetchAvailableTimes(
  partnerId: string,
  serviceId: string,
  locationId: string,
  date: string,
): Promise<StartTimeEntry[]> {
  const params = new URLSearchParams({
    instructorId: '',
    locationId,
    roomId: 'any',
    date,
    timezone: TIMEZONE,
  });

  const url = `${ARKETA_WIDGET_API}/${partnerId}/services/${serviceId}/availableTimes?${params}`;
  const res = await fetch(url, { headers: { Accept: 'application/json', 'User-Agent': UA } });

  if (!res.ok) {
    throw new Error(`Arketa availableTimes ${res.status}`);
  }

  const json = (await res.json()) as AvailableTimesResponse;
  const entries: StartTimeEntry[] = [];
  for (const group of json.slots || []) {
    entries.push(...(group.startTimes || []));
  }
  return entries;
}

/**
 * Fetch classes from the Arketa appointments API.
 *
 * 1. Calls availableDays per month to find which days have slots
 * 2. Calls availableTimes for each available day
 * 3. Transforms to ClassScheduleRow[]
 *
 * @param partnerId - Arketa partner ID
 * @param serviceId - Arketa service/offering ID
 * @param studioSlug - Internal studio slug (e.g. "saint")
 * @param locationId - Arketa location ID
 * @param minDate - "YYYY-MM-DD"
 * @param maxDate - "YYYY-MM-DD"
 */
export async function fetchArketaClassesFromAPI(
  partnerId: string,
  serviceId: string,
  studioSlug: string,
  locationId: string,
  minDate: string,
  maxDate: string,
): Promise<ClassScheduleRow[]> {
  // 1. Get available days across all months in range
  const monthRanges = getMonthRanges(minDate, maxDate);
  const availableDates: string[] = [];

  for (const range of monthRanges) {
    try {
      const days = await fetchAvailableDays(partnerId, serviceId, locationId, range.start, range.end);
      for (const day of days) {
        if (day.isAvailable) {
          // Extract YYYY-MM-DD from the date string like "2026-02-26T00:00:00-05:00"
          const dateStr = day.date.split('T')[0];
          if (dateStr >= minDate && dateStr <= maxDate) {
            availableDates.push(dateStr);
          }
        }
      }
    } catch (err) {
      console.error(`[arketa] Failed to fetch availableDays for ${range.start}-${range.end}: ${err}`);
    }
  }

  // 2. Fetch time slots for each available day
  const results: ClassScheduleRow[] = [];

  for (const date of availableDates) {
    try {
      const times = await fetchAvailableTimes(partnerId, serviceId, locationId, date);
      for (const slot of times) {
        const classDate = formatISOToDate(slot.dateString);
        results.push({
          studio_slug: studioSlug,
          location_id: locationId,
          class_date: classDate,
          class_time: formatISOToTime12(slot.dateString),
          class_name: 'PERSONAL SAUNA & ICE BATH',
          instructor: null,
          duration_minutes: 60,
          available: true, // These slots are available — that's why the API returns them
          spots_remaining: 1, // Private sessions have 1 spot
          booking_opens_at: null,
        });
      }
    } catch (err) {
      console.error(`[arketa] Failed to fetch availableTimes for ${date}: ${err}`);
    }
  }

  return results;
}
