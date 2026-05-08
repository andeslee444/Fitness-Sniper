-- Migration 007: Add class_name to booking_history for enriched display
--
-- Purpose: Users need to see what class was booked/failed, not just location IDs.
-- The class name is stored in class_schedules at booking time and should be
-- captured in booking_history for historical display.
--
-- Changes:
-- 1. Add class_name column to booking_history
-- 2. Update on_job_completed trigger to populate class_name via scalar subquery
--    (scalar subquery avoids duplicate inserts when class_schedules has multiple
--    rows for the same timeslot)

-- 1. Add class_name column
ALTER TABLE booking_history ADD COLUMN IF NOT EXISTS class_name text;

-- 2. Update the on_job_completed trigger to populate class_name
CREATE OR REPLACE FUNCTION public.on_job_completed()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (old.status IS DISTINCT FROM new.status) AND new.status IN ('success', 'failed') THEN
    INSERT INTO public.booking_history (
      user_id, job_id, target_id, studio_slug, location_id,
      class_time, class_date, status, spot, message, class_name
    )
    SELECT
      new.user_id, new.id, new.target_id,
      t.studio_slug, t.location_id, t.time,
      (COALESCE(new.class_datetime, new.scheduled_for) AT TIME ZONE 'America/New_York')::date,
      CASE WHEN new.status = 'success' THEN 'booked' ELSE 'failed' END,
      new.spot_booked, new.result_message,
      (
        SELECT cs.class_name FROM public.class_schedules cs
        WHERE cs.studio_slug = t.studio_slug
          AND cs.location_id = t.location_id
          AND cs.class_date = (COALESCE(new.class_datetime, new.scheduled_for) AT TIME ZONE 'America/New_York')::date
          AND cs.class_time = t.time
        LIMIT 1
      )
    FROM public.snipe_targets t
    WHERE t.id = new.target_id;
  END IF;
  RETURN new;
END;
$$;
