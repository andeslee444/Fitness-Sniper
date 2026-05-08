-- Make `time` nullable for Arketa studios (e.g. Saint NYC) where users
-- want to snipe any available slot on a given day without picking a time.
ALTER TABLE public.snipe_targets ALTER COLUMN time DROP NOT NULL;
