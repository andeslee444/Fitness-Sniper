-- ============================================================
-- Class Schedules — scraped from Mariana Tek studios
-- ============================================================

CREATE TABLE class_schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  studio_slug text NOT NULL,
  location_id text NOT NULL,
  class_date date NOT NULL,
  class_time text NOT NULL,              -- "6:00 AM" format
  class_name text,
  instructor text,
  duration_minutes integer,
  available boolean NOT NULL DEFAULT true,
  spots_remaining integer,
  scraped_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (studio_slug, location_id, class_date, class_time, class_name)
);

CREATE INDEX idx_class_schedules_lookup
  ON class_schedules (studio_slug, location_id, class_date);

CREATE INDEX idx_class_schedules_date
  ON class_schedules (class_date);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON class_schedules
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- Scrape Runs — audit log of each scrape attempt
-- ============================================================

CREATE TABLE scrape_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  studio_slug text NOT NULL,
  location_id text NOT NULL,
  method text NOT NULL CHECK (method IN ('http_api', 'browser')),
  status text NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
  classes_found integer NOT NULL DEFAULT 0,
  days_scraped integer NOT NULL DEFAULT 0,
  error_message text,
  duration_ms integer,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_scrape_runs_lookup
  ON scrape_runs (studio_slug, location_id, created_at DESC);
