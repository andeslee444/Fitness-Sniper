-- Migration: Add one-time target support
-- Adds target_type (recurring vs one_time) and target_date columns

ALTER TABLE snipe_targets
  ADD COLUMN IF NOT EXISTS target_type text NOT NULL DEFAULT 'recurring'
    CHECK (target_type IN ('recurring', 'one_time')),
  ADD COLUMN IF NOT EXISTS target_date date;

-- one_time MUST have target_date, recurring MUST NOT
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'chk_target_date'
      AND conrelid = 'public.snipe_targets'::regclass
  ) THEN
    ALTER TABLE snipe_targets
      ADD CONSTRAINT chk_target_date CHECK (
        (target_type = 'recurring' AND target_date IS NULL)
        OR (target_type = 'one_time' AND target_date IS NOT NULL)
      );
  END IF;
END $$;

-- Make day_of_week nullable (one-time doesn't need it)
ALTER TABLE snipe_targets ALTER COLUMN day_of_week DROP NOT NULL;

-- recurring MUST have day_of_week
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'chk_day_of_week'
      AND conrelid = 'public.snipe_targets'::regclass
  ) THEN
    ALTER TABLE snipe_targets
      ADD CONSTRAINT chk_day_of_week CHECK (
        (target_type = 'recurring' AND day_of_week IS NOT NULL)
        OR (target_type = 'one_time')
      );
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_snipe_targets_onetime
  ON snipe_targets (target_date)
  WHERE target_type = 'one_time' AND enabled = true;
