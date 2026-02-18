-- ============================================================
-- Fitness Sniper — Initial Schema
-- ============================================================

-- 1. Profiles (extends auth.users)
create table public.profiles (
  id uuid primary key references auth.users on delete cascade,
  display_name text,
  subscription_tier text not null default 'free' check (subscription_tier in ('free', 'premium')),
  created_at timestamptz not null default now()
);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1)));
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 2. Studio Credentials (AES-256-GCM encrypted)
create table public.studio_credentials (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users on delete cascade,
  studio_slug text not null,
  encrypted_email text not null,
  encrypted_password text not null,
  iv text not null,
  auth_tag text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, studio_slug)
);

-- 3. Snipe Targets
create table public.snipe_targets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users on delete cascade,
  studio_slug text not null,
  location_id text not null,
  day_of_week smallint not null check (day_of_week between 0 and 6),
  time text not null,
  class_type text,
  instructor text,
  seat_preference text not null default 'any' check (seat_preference in ('front', 'middle', 'back', 'any')),
  preferred_spots text[],
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 4. Booking Jobs (worker queue)
create table public.booking_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users on delete cascade,
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
  user_id uuid not null references auth.users on delete cascade,
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
returns trigger language plpgsql security definer set search_path = '' as $$
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
security definer
set search_path = ''
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

-- ============================================================
-- Row Level Security
-- ============================================================

alter table public.profiles enable row level security;
alter table public.studio_credentials enable row level security;
alter table public.snipe_targets enable row level security;
alter table public.booking_jobs enable row level security;
alter table public.booking_history enable row level security;
alter table public.worker_heartbeats enable row level security;

-- Profiles: users can read/update their own
create policy "Users can view own profile"
  on public.profiles for select using (auth.uid() = id);
create policy "Users can update own profile"
  on public.profiles for update using (auth.uid() = id);

-- Studio credentials: users manage their own
create policy "Users can view own credentials"
  on public.studio_credentials for select using (auth.uid() = user_id);
create policy "Users can insert own credentials"
  on public.studio_credentials for insert with check (auth.uid() = user_id);
create policy "Users can update own credentials"
  on public.studio_credentials for update using (auth.uid() = user_id);
create policy "Users can delete own credentials"
  on public.studio_credentials for delete using (auth.uid() = user_id);

-- Snipe targets: users manage their own
create policy "Users can view own targets"
  on public.snipe_targets for select using (auth.uid() = user_id);
create policy "Users can insert own targets"
  on public.snipe_targets for insert with check (auth.uid() = user_id);
create policy "Users can update own targets"
  on public.snipe_targets for update using (auth.uid() = user_id);
create policy "Users can delete own targets"
  on public.snipe_targets for delete using (auth.uid() = user_id);

-- Booking jobs: users can view their own; worker uses service key (bypasses RLS)
create policy "Users can view own jobs"
  on public.booking_jobs for select using (auth.uid() = user_id);
create policy "Users can cancel own jobs"
  on public.booking_jobs for update using (auth.uid() = user_id)
  with check (status = 'cancelled');

-- Booking history: users can view their own
create policy "Users can view own history"
  on public.booking_history for select using (auth.uid() = user_id);

-- Worker heartbeats: public read for dashboard status display
create policy "Anyone can view worker status"
  on public.worker_heartbeats for select using (true);
