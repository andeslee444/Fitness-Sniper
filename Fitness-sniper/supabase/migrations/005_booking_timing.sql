-- Migration 005: Fix booking pipeline timing
--
-- Problems solved:
-- 1. scheduled_for was set to class start time, but claim_next_job gates on
--    scheduled_for <= now(), so jobs sat idle for up to 7 days.
-- 2. No way to pass the actual class date through the pipeline to adapters.
-- 3. Stale job recovery referenced non-existent column "worker_id".
--
-- After this migration:
-- - scheduled_for = when to execute (booking open time)
-- - class_datetime = actual class start time
-- - booking_opens_at = per-class booking window from API data

-- 1a. booking_opens_at on class_schedules (when booking opens per class)
ALTER TABLE class_schedules ADD COLUMN IF NOT EXISTS booking_opens_at timestamptz;

-- 1b. class_datetime on booking_jobs (actual class start time)
ALTER TABLE booking_jobs ADD COLUMN IF NOT EXISTS class_datetime timestamptz;

-- 1c. Backfill existing jobs: scheduled_for currently = class time, so copy it
UPDATE booking_jobs
SET class_datetime = scheduled_for
WHERE class_datetime IS NULL
  AND status IN ('pending', 'claimed', 'running');

-- 1d. Update trigger to use class_datetime for booking_history class_date
CREATE OR REPLACE FUNCTION public.on_job_completed()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (old.status IS DISTINCT FROM new.status) AND new.status IN ('success', 'failed') THEN
    INSERT INTO public.booking_history (
      user_id, job_id, target_id, studio_slug, location_id,
      class_time, class_date, status, spot, message
    )
    SELECT
      new.user_id, new.id, new.target_id,
      t.studio_slug, t.location_id, t.time,
      (COALESCE(new.class_datetime, new.scheduled_for) AT TIME ZONE 'America/New_York')::date,
      CASE WHEN new.status = 'success' THEN 'booked' ELSE 'failed' END,
      new.spot_booked, new.result_message
    FROM public.snipe_targets t
    WHERE t.id = new.target_id;
  END IF;
  RETURN new;
END;
$$;

-- 1e. Index for scheduler booking_opens_at lookups
CREATE INDEX IF NOT EXISTS idx_class_schedules_booking_opens
  ON class_schedules (studio_slug, location_id, class_date, class_time)
  WHERE booking_opens_at IS NOT NULL;
