# Fitness Sniper - Product Requirements Document

## Summary

Fitness Sniper is a private web app and worker system that auto-books competitive fitness classes as soon as booking opens or a slot becomes available. The product is built for users who already know which studios, locations, days, and class times they want, and need the system to execute faster and more reliably than manual refreshing.

The active product name is **Fitness Sniper**. "Class Sniper" is retired legacy naming and should remain only in historical archive material when needed for context.

## Core Problem

High-demand boutique fitness classes often fill within seconds of release. Users need to monitor schedules, remember each studio's booking window, select spots, and act immediately. Fitness Sniper centralizes targets and credentials, monitors class schedules, and attempts booking at the correct moment.

## Current Product

Fitness Sniper is an npm workspaces monorepo with three runtime areas:

- `web/` - Next.js App Router dashboard for signup/login, credentials, targets, schedules, history, and worker status.
- `worker/` - Always-on Node/Playwright daemon that schedules jobs, scrapes schedules, watches dynamic slots, books classes, and sends email notifications.
- `packages/shared/` - Shared studio registry, types, time helpers, and API clients used by both web and worker.

The canonical app directory is this folder. The separate `class-sniper/` tree is obsolete and should not be restored.

## Users

Primary user:

- A regular boutique fitness customer who wants recurring or one-time class bookings at specific NYC-area studios and locations.

Operational user:

- The project owner/operator running the worker on a trusted Mac Mini and deploying the dashboard to Vercel.

## Supported Studios And Platforms

Fitness Sniper routes each studio through a platform-specific adapter:

- Mariana Tek: Barry's Bootcamp, Aarmy, SLT, Practice Room.
- Xponential/ClubReady: Rumble Boxing, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre.
- Arketa: Saint NYC.

Each platform has different authentication, schedule, and booking APIs. Adapters should remain platform-specific unless a real shared abstraction emerges.

## Required Capabilities

### Authentication

- Users sign up and log in with AWS Cognito.
- The web app stores `cognito_access_token`, `cognito_id_token`, and `cognito_refresh_token` as httpOnly cookies.
- Protected pages and API routes require a valid Cognito session.
- Supabase Auth is not part of the active architecture.

### Credentials

- Users save studio credentials per studio.
- Credentials are encrypted with AES-256-GCM before storage.
- Web and worker must share the same `ENCRYPTION_KEY`.
- Credentials are decrypted only in the worker at booking time or in web validation endpoints.
- Plaintext credential config files must not be tracked.

### Snipe Targets

- Users can create recurring targets by day of week and time.
- Users can create one-time targets by exact date and time.
- Arketa targets may omit time to snipe any available slot on a selected day.
- Targets can include seat/spot preferences.
- Non-Arketa targets require a time.
- Target creation requires saved credentials for that studio.

### Schedule Browser

- Users can browse schedules by studio, location, and date.
- The schedule API should prefer fresh database data and fall back to live studio APIs.
- Schedule results should be normalized for UI display.
- Users can create one-time snipe targets directly from schedule rows.

### Booking Jobs

- The worker creates `booking_jobs` from enabled targets.
- `scheduled_for` is the booking attempt time, usually the class booking open time.
- `class_datetime` is the actual class start time.
- Jobs are claimed atomically through the PostgreSQL `claim_next_job(worker_id)` function.
- Failed jobs retry up to their configured max attempts.
- Terminal jobs write booking history through database triggers.

### Worker Operations

- The worker sends heartbeats to `worker_heartbeats`.
- The scheduler recovers stale `claimed` and `running` jobs.
- The schedule scraper populates `class_schedules` for active targets.
- Arketa/Saint NYC is handled by `SlotWatcher`, not the normal scheduler, because slots can appear unpredictably.

### Notifications And History

- Booking success and failure should be visible in history.
- Successful and failed attempts should generate email notifications through Resend when a user email is available.
- Dashboard views should show calendar events, active target status, worker status, and per-studio success rates.

## Data Model

Canonical tables:

- `profiles`
- `studio_credentials`
- `snipe_targets`
- `booking_jobs`
- `booking_history`
- `worker_heartbeats`
- `class_schedules`
- `scrape_runs`

Canonical schema source:

- `supabase/migrations/001_rds_schema.sql`
- Follow-on migrations `002` through `007`

The old Supabase Auth schema is removed from active migrations. Access control is enforced at the application layer with Cognito user IDs.

## Non-Goals

- No public marketplace or multi-tenant commercial rollout yet.
- No native mobile app.
- No generic browser automation framework for every studio.
- No Supabase Auth dependency.
- No plaintext local credential config.
- No automated test suite is currently configured.

## Deployment Model

- Web: Vercel, using `web/.next` output and environment variables from Vercel.
- Worker: trusted always-on machine, currently intended for a Mac Mini.
- Database: PostgreSQL reachable by both web and worker via `DATABASE_URL`.
- Email: Resend.
- Browser automation: Playwright/Chromium for Mariana Tek fallback paths.

## Consolidation Decisions

- `Fitness-sniper/` is the authoritative app folder in this checkout.
- `class-sniper/` is obsolete and should remain deleted from the repository.
- Active package names use `fitness-sniper` and `@fitness-sniper/*`.
- Active docs should say Fitness Sniper.
- Historical archive material may mention Class Sniper only where it is clearly legacy reference content.
- Legacy config files that held or encouraged plaintext credentials have been removed from `archive/config/`.

## Acceptance Criteria

- The repo has one active app implementation.
- No tracked plaintext credentials remain in active or legacy config files.
- Build and lint commands run from the app root.
- Supabase client/auth helpers are not reintroduced.
- The worker still compiles with NodeNext `.js` import extensions.
- The web app still uses Cognito and direct `pg` database access.
