/**
 * Mariana Tek HTTP API Client
 *
 * Calls the public Customer API at https://{tenant}.marianatek.com/api/customer/v1/classes
 * to fetch class schedules without needing a browser. Falls back to browser scraping
 * if the API requires auth or returns errors.
 */

export interface ClassScheduleRow {
  studio_slug: string;
  location_id: string;
  class_date: string; // "YYYY-MM-DD"
  class_time: string; // "6:00 AM" format
  class_name: string | null;
  instructor: string | null;
  duration_minutes: number | null;
  available: boolean;
  spots_remaining: number | null;
}

interface MTClassAttributes {
  name: string;
  start_datetime: string; // ISO 8601
  end_datetime: string;
  is_cancelled: boolean;
  remaining_capacity: number | null;
  class_type?: string;
}

interface MTRelationshipData {
  id: string;
  type: string;
}

interface MTClassRelationships {
  class_type?: { data: MTRelationshipData | null };
  instructors?: { data: MTRelationshipData[] };
  location?: { data: MTRelationshipData | null };
}

interface MTIncludedItem {
  id: string;
  type: string;
  attributes: {
    name?: string;
    first_name?: string;
    last_name?: string;
  };
}

interface MTClassItem {
  id: string;
  type: string;
  attributes: MTClassAttributes;
  relationships?: MTClassRelationships;
}

interface MTApiResponse {
  data: MTClassItem[];
  included?: MTIncludedItem[];
  links?: {
    next?: string | null;
  };
  meta?: {
    pagination?: {
      count: number;
      pages: number;
    };
  };
}

import { formatTime12 } from '@fitness-sniper/shared';

/**
 * Normalize an ISO datetime to "H:MM AM/PM" format matching snipe_targets.time
 */
function formatTime(isoDatetime: string): string {
  return formatTime12(isoDatetime);
}

/**
 * Extract date portion from ISO datetime as "YYYY-MM-DD"
 */
function formatDate(isoDatetime: string): string {
  return isoDatetime.split('T')[0];
}

/**
 * Calculate duration in minutes between two ISO datetimes
 */
function calcDuration(start: string, end: string): number {
  return Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60000);
}

/**
 * Resolve an included resource name by ID and type
 */
function resolveIncluded(
  included: MTIncludedItem[] | undefined,
  id: string,
  type: string,
): MTIncludedItem | undefined {
  return included?.find((item) => item.id === id && item.type === type);
}

/**
 * Fetch classes from the Mariana Tek Customer API for a given tenant and date range.
 * Throws on non-200 responses (caller should catch and fall back to browser).
 */
export async function fetchClassesFromAPI(
  tenant: string,
  studioSlug: string,
  locationId: string,
  minDate: string, // "YYYY-MM-DD"
  maxDate: string, // "YYYY-MM-DD"
): Promise<ClassScheduleRow[]> {
  const allClasses: ClassScheduleRow[] = [];
  let url: string | null =
    `https://${tenant}.marianatek.com/api/customer/v1/classes?min_date=${minDate}&max_date=${maxDate}&page_size=100`;

  while (url) {
    const response = await fetch(url, {
      headers: {
        Accept: 'application/vnd.api+json',
        'User-Agent':
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
      },
    });

    if (!response.ok) {
      throw new Error(`MT API returned ${response.status}: ${response.statusText}`);
    }

    const json = (await response.json()) as MTApiResponse;
    const included = json.included;

    for (const item of json.data) {
      const attrs = item.attributes;
      if (attrs.is_cancelled) continue;

      // Resolve instructor name from included
      let instructorName: string | null = null;
      const instructorRels = item.relationships?.instructors?.data;
      if (instructorRels && instructorRels.length > 0) {
        const instructorItem = resolveIncluded(included, instructorRels[0].id, instructorRels[0].type);
        if (instructorItem?.attributes) {
          const { first_name, last_name, name } = instructorItem.attributes;
          instructorName = name || [first_name, last_name].filter(Boolean).join(' ') || null;
        }
      }

      // Resolve class type name from included
      let className: string | null = attrs.name || null;
      const classTypeRel = item.relationships?.class_type?.data;
      if (!className && classTypeRel) {
        const classTypeItem = resolveIncluded(included, classTypeRel.id, classTypeRel.type);
        className = classTypeItem?.attributes?.name || null;
      }

      allClasses.push({
        studio_slug: studioSlug,
        location_id: locationId,
        class_date: formatDate(attrs.start_datetime),
        class_time: formatTime(attrs.start_datetime),
        class_name: className,
        instructor: instructorName,
        duration_minutes: calcDuration(attrs.start_datetime, attrs.end_datetime),
        available: attrs.remaining_capacity === null || attrs.remaining_capacity > 0,
        spots_remaining: attrs.remaining_capacity,
      });
    }

    // Follow pagination
    url = json.links?.next || null;
  }

  return allClasses;
}
