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
  iv: string;
  auth_tag: string;
  created_at: string;
  updated_at: string;
}

export interface SnipeTarget {
  id: string;
  user_id: string;
  studio_slug: string;
  location_id: string;
  day_of_week: number; // 0-6 (Sun-Sat)
  time: string; // "6:00 AM"
  class_type: string | null;
  instructor: string | null;
  seat_preference: 'front' | 'middle' | 'back' | 'any';
  preferred_spots: string[] | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export type JobStatus = 'pending' | 'claimed' | 'running' | 'success' | 'failed' | 'cancelled';

export interface BookingJob {
  id: string;
  user_id: string;
  target_id: string;
  status: JobStatus;
  claimed_by: string | null;
  claimed_at: string | null;
  scheduled_for: string;
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
// Spot Preferences
// ============================================================

export const SPOT_PREFERENCES: Record<string, string[]> = {
  front: ['F-1', 'F-3', 'F-5', 'F-7', 'F-2', 'F-4', 'F-6', 'F-8'],
  middle: ['F-9', 'F-10', 'F-11', 'F-12', 'F-13', 'F-14', 'F-15', 'F-16'],
  back: ['T-1', 'T-3', 'T-5', 'T-7', 'T-2', 'T-4', 'T-6', 'T-8', 'T-9', 'T-10'],
  any: [],
};
