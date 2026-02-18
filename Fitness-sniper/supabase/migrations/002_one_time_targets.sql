-- Migration: Add one-time target support
-- Adds target_type (recurring vs one_time) and target_date columns

ALTER TABLE snipe_targets
  ADD COLUMN target_type text NOT NULL DEFAULT 'recurring'
    CHECK (target_type IN ('recurring', 'one_time')),
  ADD COLUMN target_date date;

-- one_time MUST have target_date, recurring MUST NOT
ALTER TABLE snipe_targets
  ADD CONSTRAINT chk_target_date CHECK (
    (target_type = 'recurring' AND target_date IS NULL)
    OR (target_type = 'one_time' AND target_date IS NOT NULL)
  );

-- Make day_of_week nullable (one-time doesn't need it)
ALTER TABLE snipe_targets ALTER COLUMN day_of_week DROP NOT NULL;

-- recurring MUST have day_of_week
ALTER TABLE snipe_targets
  ADD CONSTRAINT chk_day_of_week CHECK (
    (target_type = 'recurring' AND day_of_week IS NOT NULL)
    OR (target_type = 'one_time')
  );

CREATE INDEX idx_snipe_targets_onetime
  ON snipe_targets (target_date)
  WHERE target_type = 'one_time' AND enabled = true;
