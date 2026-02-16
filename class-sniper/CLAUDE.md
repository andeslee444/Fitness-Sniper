# CLAUDE.md

## Project Overview

Class Sniper auto-books competitive fitness classes (Barry's, Aarmy, SLT, Xponential brands) before they fill up. The system uses a Supabase backend, Mac Mini worker with stealth Playwright, and Next.js dashboard.

## Architecture

```
class-sniper/
├── archive/          # Legacy code (reference only)
├── worker/           # Mac Mini worker (Playwright + job queue)
├── web/              # Next.js 15 frontend (dashboard)
├── supabase/         # Database migrations
├── packages/shared/  # Shared types and studio config
└── package.json      # npm workspaces root
```

### Worker (`worker/`)
- **Stealth browser** (`stealth/browser.ts`) — Playwright with anti-detection
- **Human delays** (`stealth/human-delay.ts`) — Randomized timing between actions
- **Mariana Tek adapter** (`adapters/mariana-tek.ts`) — Booking for all MT studios
- **Job poller** (`jobs/poller.ts`) — Polls Supabase for pending jobs via `claim_next_job()` RPC
- **Job processor** (`jobs/processor.ts`) — Decrypts creds, launches browser, executes booking
- **Job scheduler** (`jobs/scheduler.ts`) — Creates jobs from enabled targets (every 15 min)
- **Credentials** (`crypto/credentials.ts`) — AES-256-GCM encrypt/decrypt
- **Email** (`notifications/email.ts`) — Booking notifications via Resend

### Frontend (`web/`)
- Next.js 15 App Router + Tailwind + shadcn/ui
- Supabase Auth (email/password)
- Pages: `/dashboard`, `/targets`, `/history`, `/credentials`
- Realtime subscriptions for job status updates

### Database (`supabase/migrations/`)
- Tables: `profiles`, `studio_credentials`, `snipe_targets`, `booking_jobs`, `booking_history`, `worker_heartbeats`
- RPC: `claim_next_job(worker_id)` — atomic job claiming with `FOR UPDATE SKIP LOCKED`
- RLS: All user tables scoped to `auth.uid() = user_id`

## Commands

```bash
# Root
npm install                    # Install all workspaces

# Worker
npm run worker                 # Start worker (dev)
npm run worker:build           # Build worker

# Frontend
npm run web:dev                # Next.js dev server
npm run web:build              # Build frontend
```

## Supported Studios

All Mariana Tek: Barry's, Aarmy, SLT, Rumble, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre.
Studio configs in `packages/shared/src/studios.ts`.

## Booking Flow

1. User creates snipe target (studio, location, day, time, seat preference)
2. Scheduler creates `booking_jobs` row when class enters 7-day booking window
3. Worker polls for pending jobs via `claim_next_job()` RPC
4. Worker decrypts credentials, launches stealth browser, navigates to schedule
5. Finds class → clicks Reserve → selects preferred spot → confirms booking
6. Updates job status → trigger inserts into `booking_history` → sends email

## Environment Variables

### Worker
`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ENCRYPTION_KEY` (32-byte hex), `RESEND_API_KEY`, `WORKER_ID`

### Frontend
`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `ENCRYPTION_KEY`

## Key Challenges

- **Selectors are fragile** — Studio sites change DOM. Check `archive/exploration/SUMMARY.md`.
- **Iframe embedding** — Barry's, SLT, Aarmy embed schedules in iframes. Xponential brands use direct SPAs.
- **Rate limiting** — Human-like delays (3-8s between actions, 50-150ms per keystroke).
- **Credentials** — Encrypted with AES-256-GCM, stored in Supabase, decrypted only by worker at booking time.
