/**
 * Arketa Slot Source — fetches available appointment slots from the real
 * Arketa Cloud Run API.
 *
 * Saint NYC uses Arketa's "privates/appointments" system (NOT the widget
 * classes API). The real endpoints are:
 *
 *   GET {BASE}/{partnerId}/services/{serviceId}/availableDays
 *       ?locationId=&roomId=any&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&timezone=
 *       (start/end must be in the same calendar month)
 *
 *   GET {BASE}/{partnerId}/services/{serviceId}/availableTimes
 *       ?locationId=&roomId=any&date=YYYY-MM-DD&timezone=
 *
 * No auth required — these are public widget endpoints.
 */

const ARKETA_WIDGET_API = 'https://widget-api-tkaeguucxq-uc.a.run.app';
const TIMEZONE = 'America/New_York';
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36';

// ── Types ────────────────────────────────────────────────────────────

export interface ArketaSlot {
  /** Composite key for delta detection: "dateString|roomId" */
  slotKey: string;
  /** Human-readable time label from API (e.g. "5:15PM") */
  label: string;
  /** ISO datetime from API (e.g. "2026-02-26T22:15:00.000Z") */
  dateString: string;
  serviceId: string;
  roomId: string;
  locationId: string;
  /** Date in ET: "YYYY-MM-DD" */
  classDate: string;
  /** Time in ET: "H:MM AM/PM" */
  classTime: string;
  /** Unix timestamp (seconds) */
  startTime: number;
}

interface AvailableDayEntry {
  date: string; // "2026-02-26T00:00:00-05:00"
  isAvailable: boolean;
}

interface StartTimeEntry {
  label: string;
  dateString: string;
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

// ── Helpers ──────────────────────────────────────────────────────────

function formatISOToDateET(isoStr: string): string {
  return new Date(isoStr).toLocaleDateString('en-CA', { timeZone: TIMEZONE });
}

function formatISOToTime12ET(isoStr: string): string {
  return new Date(isoStr).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: TIMEZONE,
  });
}

// ── API Functions ────────────────────────────────────────────────────

/**
 * Fetch which days have availability in a date range (must be same month).
 */
export async function fetchArketaAvailableDays(
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
    throw new Error(`Arketa availableDays ${res.status}: ${await res.text().then((t) => t.substring(0, 200))}`);
  }

  return (await res.json()) as AvailableDayEntry[];
}

/**
 * Fetch available time slots for a specific date.
 */
export async function fetchArketaAvailableTimes(
  partnerId: string,
  serviceId: string,
  locationId: string,
  date: string,
): Promise<ArketaSlot[]> {
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
    throw new Error(`Arketa availableTimes ${res.status}: ${await res.text().then((t) => t.substring(0, 200))}`);
  }

  const json = (await res.json()) as AvailableTimesResponse;
  const slots: ArketaSlot[] = [];

  for (const group of json.slots || []) {
    for (const st of group.startTimes || []) {
      slots.push({
        slotKey: `${st.dateString}|${st.roomId}`,
        label: st.label,
        dateString: st.dateString,
        serviceId: st.serviceId,
        roomId: st.roomId,
        locationId: st.locationId,
        classDate: formatISOToDateET(st.dateString),
        classTime: formatISOToTime12ET(st.dateString),
        startTime: Math.floor(new Date(st.dateString).getTime() / 1000),
      });
    }
  }

  return slots;
}

/**
 * Fetch all available slots across a set of dates.
 * Used by the SlotWatcher to check multiple dates in one call.
 */
export async function fetchArketaSlotsForDates(
  partnerId: string,
  serviceId: string,
  locationId: string,
  dates: string[],
): Promise<ArketaSlot[]> {
  const all: ArketaSlot[] = [];
  for (const date of dates) {
    const slots = await fetchArketaAvailableTimes(partnerId, serviceId, locationId, date);
    all.push(...slots);
  }
  return all;
}
