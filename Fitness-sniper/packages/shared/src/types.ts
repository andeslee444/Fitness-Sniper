// ============================================================
// Database Row Types (matching Supabase schema)
// ============================================================

export interface Profile {
  id: string;
  display_name: string | null;
  subscription_tier: 'free' | 'premium';
  created_at: string;
}

export interface StudioCredential {
  id: string;
  user_id: string;
  studio_slug: string;
  encrypted_email: string;
  encrypted_password: string;
  iv: string; // email IV
  auth_tag: string; // email auth tag
  password_iv: string;
  password_auth_tag: string;
  created_at: string;
  updated_at: string;
}

export type TargetType = 'recurring' | 'one_time';

export interface SnipeTarget {
  id: string;
  user_id: string;
  studio_slug: string;
  location_id: string;
  target_type: TargetType;
  day_of_week: number | null; // 0-6 (Sun-Sat), null for one-time
  time: string; // "6:00 AM"
  target_date: string | null; // "YYYY-MM-DD", null for recurring
  class_type: string | null;
  instructor: string | null;
  seat_preference: 'front' | 'middle' | 'back' | 'any';
  preferred_spots: string[] | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export type JobStatus = 'pending' | 'claimed' | 'running' | 'success' | 'failed' | 'cancelled';

/** SnipeTarget enriched with the latest booking_job status */
export interface TargetWithJob extends SnipeTarget {
  job_status: JobStatus | null;
  job_scheduled_for: string | null;
  job_class_datetime: string | null; // actual class time (for display)
  job_message: string | null;
  job_spot: string | null;
}

export interface BookingJob {
  id: string;
  user_id: string;
  target_id: string;
  status: JobStatus;
  claimed_by: string | null;
  claimed_at: string | null;
  scheduled_for: string;
  class_datetime: string | null; // actual class start time (scheduled_for = booking open time)
  result_message: string | null;
  spot_booked: string | null;
  screenshot_url: string | null;
  attempts: number;
  max_attempts: number;
  created_at: string;
  updated_at: string;
}

export interface BookingHistory {
  id: string;
  user_id: string;
  job_id: string | null;
  target_id: string | null;
  studio_slug: string;
  location_id: string;
  class_time: string;
  class_date: string;
  status: 'booked' | 'failed' | 'cancelled';
  spot: string | null;
  message: string | null;
  created_at: string;
}

export interface WorkerHeartbeat {
  id: string;
  worker_id: string;
  last_heartbeat: string;
  active_jobs: number;
  status: 'online' | 'offline';
  meta: Record<string, unknown> | null;
}

// ============================================================
// Adapter Types
// ============================================================

export interface ClassInfo {
  time: string;
  className: string;
  instructor: string;
  location: string;
  date: string;
  available: boolean;
}

export interface BookingResult {
  success: boolean;
  message: string;
  spot?: string;
  screenshotPath?: string;
}

export interface StudioCredentials {
  email: string;
  password: string;
}

// ============================================================
// Class Schedule (scraped data)
// ============================================================

export interface ClassSchedule {
  id: string;
  studio_slug: string;
  location_id: string;
  class_date: string;
  class_time: string;
  class_name: string | null;
  instructor: string | null;
  duration_minutes: number | null;
  available: boolean;
  spots_remaining: number | null;
  scraped_at: string;
}

// ============================================================
// Class Schedule Row (used by API clients and scrapers)
// ============================================================

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
  booking_opens_at: string | null; // ISO 8601 — when booking opens for this class
}

// ============================================================
// Time Parsing Utilities
// ============================================================

/**
 * Parse "H:MM AM/PM" into { hours24, minutes }.
 * Returns null if the string doesn't match.
 */
export function parseTime(time: string): { hours24: number; minutes: number } | null {
  const match = time.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
  if (!match) return null;

  let hours = parseInt(match[1], 10);
  const minutes = parseInt(match[2], 10);
  const ampm = match[3].toUpperCase();

  if (ampm === 'PM' && hours !== 12) hours += 12;
  if (ampm === 'AM' && hours === 12) hours = 0;

  return { hours24: hours, minutes };
}

/**
 * Format a Date or ISO string to "H:MM AM/PM"
 */
export function formatTime12(input: Date | string): string {
  const date = typeof input === 'string' ? new Date(input) : input;
  let hours = date.getHours();
  const minutes = date.getMinutes();
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12 || 12;
  return `${hours}:${minutes.toString().padStart(2, '0')} ${ampm}`;
}

// ============================================================
// Spot Preferences
// ============================================================

export const SPOT_PREFERENCES: Record<string, string[]> = {
  front: ['F-1', 'F-3', 'F-5', 'F-7', 'F-2', 'F-4', 'F-6', 'F-8'],
  middle: ['F-9', 'F-10', 'F-11', 'F-12', 'F-13', 'F-14', 'F-15', 'F-16'],
  back: ['T-1', 'T-3', 'T-5', 'T-7', 'T-2', 'T-4', 'T-6', 'T-8', 'T-9', 'T-10'],
  any: [],
};
