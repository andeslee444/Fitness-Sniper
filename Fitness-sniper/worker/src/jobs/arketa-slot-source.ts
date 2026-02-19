/**
 * Arketa Slot Source — raw API fetch for the SlotWatcher
 *
 * Returns Arketa classes with their original `id` field so the watcher can
 * track which classes are new (delta detection). The shared
 * `fetchArketaClassesFromAPI` strips the Arketa ID, so we need this
 * dedicated fetcher.
 */

const ARKETA_BASE = 'https://app.arketa.co';
const ARKETA_PAGE_LIMIT = 250;
const MAX_PAGES = 10;

export interface ArketaSlot {
  arketaId: string;
  name: string;
  startTime: number; // Unix timestamp
  duration: number; // Minutes
  maxCapacity: number;
  totalBooked: number;
  isBookable: boolean;
  locationId: string;
  classDate: string; // "YYYY-MM-DD" in ET
  classTime: string; // "H:MM AM/PM" in ET
}

interface ArketaClass {
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
  location: { id: string; name: string; address: string } | null;
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

function formatUnixToTime12(unixTs: number): string {
  const date = new Date(unixTs * 1000);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/New_York',
  });
}

function formatUnixToDate(unixTs: number): string {
  const date = new Date(unixTs * 1000);
  return date.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
}

/**
 * Fetch all current Arketa classes for a widget + location, returning raw slot
 * data with Arketa IDs for delta detection.
 *
 * Fetches from now through ~30 days ahead with manual pagination.
 */
export async function fetchArketaSlots(
  widgetName: string,
  locationId: string,
): Promise<ArketaSlot[]> {
  const now = Math.floor(Date.now() / 1000);
  let currentStartTime = now;

  const results: ArketaSlot[] = [];
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
      if (item.start_time > lastTimestamp) lastTimestamp = item.start_time;

      if (seenIds.has(item.id)) continue;
      seenIds.add(item.id);

      // Filter out internal time blocks, hidden, canceled, deleted
      if (item.appointment_type === 'time_block') continue;
      if (item.hidden || item.canceled || item.deleted) continue;

      // Filter by location
      if (locationId && item.location?.id !== locationId) continue;

      results.push({
        arketaId: item.id,
        name: item.name || item.class_name || 'Unknown',
        startTime: item.start_time,
        duration: item.duration,
        maxCapacity: item.max_capacity,
        totalBooked: item.total_booked,
        isBookable: item.isBookable,
        locationId: item.location?.id || locationId,
        classDate: formatUnixToDate(item.start_time),
        classTime: formatUnixToTime12(item.start_time),
      });
    }

    if (classes.length < ARKETA_PAGE_LIMIT) break;
    currentStartTime = lastTimestamp + 1;
  }

  return results;
}
