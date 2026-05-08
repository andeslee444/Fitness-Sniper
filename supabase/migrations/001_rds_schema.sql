-- ============================================================
-- Fitness Sniper — RDS Postgres Schema
-- ============================================================
-- Migrated from Supabase. Changes:
--   - profiles keyed by cognito_sub (text) instead of auth.users FK
--   - user_id is text (Cognito sub) instead of uuid references auth.users
--   - No RLS (access control at application layer)
--   - No handle_new_user trigger (profile created by app on signup)
-- ============================================================

-- 1. Profiles (keyed by Cognito sub)
create table public.profiles (
  id text primary key,  -- Cognito sub (e.g. "us-east-2_xxx|12345")
  email text not null,
  display_name text,
  subscription_tier text not null default 'free' check (subscription_tier in ('free', 'premium')),
  created_at timestamptz not null default now()
);

-- 2. Studio Credentials (AES-256-GCM encrypted, separate IV/authTag per field)
create table public.studio_credentials (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  studio_slug text not null,
  encrypted_email text not null,
  encrypted_password text not null,
  iv text not null,
  auth_tag text not null,
  password_iv text not null,
  password_auth_tag text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, studio_slug)
);

-- 3. Snipe Targets
create table public.snipe_targets (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  studio_slug text not null,
  location_id text not null,
  target_type text not null default 'recurring' check (target_type in ('recurring', 'one_time')),
  day_of_week smallint check (day_of_week between 0 and 6),
  time text not null,
  target_date date,
  class_type text,
  instructor text,
  seat_preference text not null default 'any' check (seat_preference in ('front', 'middle', 'back', 'any')),
  preferred_spots text[],
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  -- recurring targets require day_of_week; one-time targets require target_date
  constraint chk_day_of_week check (target_type != 'recurring' or day_of_week is not null),
  constraint chk_target_date check (target_type != 'one_time' or target_date is not null)
);

-- 4. Booking Jobs (worker queue)
create table public.booking_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  target_id uuid not null references public.snipe_targets on delete cascade,
  status text not null default 'pending' check (status in ('pending', 'claimed', 'running', 'success', 'failed', 'cancelled')),
  claimed_by text,
  claimed_at timestamptz,
  scheduled_for timestamptz not null,
  result_message text,
  spot_booked text,
  screenshot_url text,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 5. Booking History
create table public.booking_history (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  job_id uuid references public.booking_jobs on delete set null,
  target_id uuid references public.snipe_targets on delete set null,
  studio_slug text not null,
  location_id text not null,
  class_time text not null,
  class_date date not null,
  status text not null check (status in ('booked', 'failed', 'cancelled')),
  spot text,
  message text,
  created_at timestamptz not null default now()
);

-- 6. Worker Heartbeats
create table public.worker_heartbeats (
  id uuid primary key default gen_random_uuid(),
  worker_id text not null unique,
  last_heartbeat timestamptz not null default now(),
  active_jobs integer not null default 0,
  status text not null default 'online' check (status in ('online', 'offline')),
  meta jsonb
);

-- ============================================================
-- Indexes
-- ============================================================

create index idx_booking_jobs_poll on public.booking_jobs (status, scheduled_for)
  where status = 'pending';

create index idx_snipe_targets_user on public.snipe_targets (user_id, enabled)
  where enabled = true;

create index idx_booking_history_user on public.booking_history (user_id, created_at desc);

create index idx_booking_jobs_target on public.booking_jobs (target_id, status);

create index idx_snipe_targets_onetime on public.snipe_targets (target_date)
  where target_type = 'one_time' and enabled = true;

-- ============================================================
-- Auto-update updated_at triggers
-- ============================================================

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger set_updated_at before update on public.studio_credentials
  for each row execute function public.set_updated_at();

create trigger set_updated_at before update on public.snipe_targets
  for each row execute function public.set_updated_at();

create trigger set_updated_at before update on public.booking_jobs
  for each row execute function public.set_updated_at();

-- ============================================================
-- Job completion → booking_history trigger
-- ============================================================

create or replace function public.on_job_completed()
returns trigger language plpgsql as $$
begin
  -- Only fire when status changes to success or failed
  if (old.status is distinct from new.status) and new.status in ('success', 'failed') then
    insert into public.booking_history (
      user_id, job_id, target_id, studio_slug, location_id,
      class_time, class_date, status, spot, message
    )
    select
      new.user_id,
      new.id,
      new.target_id,
      t.studio_slug,
      t.location_id,
      t.time,
      (new.scheduled_for at time zone 'America/New_York')::date,
      case when new.status = 'success' then 'booked' else 'failed' end,
      new.spot_booked,
      new.result_message
    from public.snipe_targets t
    where t.id = new.target_id;
  end if;
  return new;
end;
$$;

create trigger on_job_completed
  after update on public.booking_jobs
  for each row execute function public.on_job_completed();

-- ============================================================
-- RPC: Atomic job claiming (FOR UPDATE SKIP LOCKED)
-- ============================================================

create or replace function public.claim_next_job(p_worker_id text)
returns public.booking_jobs
language plpgsql
as $$
declare
  v_job public.booking_jobs;
begin
  select * into v_job
  from public.booking_jobs
  where status = 'pending'
    and scheduled_for <= now()
    and attempts < max_attempts
  order by scheduled_for asc
  limit 1
  for update skip locked;

  if v_job.id is null then
    return null;
  end if;

  update public.booking_jobs
  set status = 'claimed',
      claimed_by = p_worker_id,
      claimed_at = now(),
      attempts = attempts + 1,
      updated_at = now()
  where id = v_job.id;

  -- Return the updated row
  select * into v_job from public.booking_jobs where id = v_job.id;
  return v_job;
end;
$$;
