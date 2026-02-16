// Database row types matching Supabase schema

export interface Profile {
  id: string;
  display_name: string | null;
  subscription_tier: 'free' | 'premium';
  created_at: string;
}

export interface SnipeTarget {
  id: string;
  user_id: string;
  studio_slug: string;
  location_id: string;
  day_of_week: number;
  time: string;
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
