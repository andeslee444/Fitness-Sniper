# Fitness Sniper

Auto-book competitive fitness classes as soon as booking opens or a slot appears.

Fitness Sniper is a private TypeScript monorepo with a Next.js dashboard, a PostgreSQL-backed booking worker, and shared studio/API logic.

## What It Does

- Stores encrypted per-studio credentials.
- Lets users create recurring and one-time snipe targets.
- Browses live and cached class schedules.
- Creates booking jobs at each studio's booking-open time.
- Books through platform-specific adapters.
- Tracks worker health, booking history, and per-studio success rates.
- Sends success/failure email notifications through Resend.

## Supported Platforms

- Mariana Tek: Barry's Bootcamp, Aarmy, SLT, Practice Room.
- Xponential/ClubReady: Rumble Boxing, CycleBar, Club Pilates, YogaSix, StretchLab, Pure Barre.
- Arketa: Saint NYC.

## Architecture

```text
.
├── web/                 # Next.js App Router dashboard and API routes
├── worker/              # Always-on booking daemon
├── packages/shared/     # Shared types, studio registry, and API clients
├── supabase/migrations/ # PostgreSQL schema migrations
├── archive/             # Legacy reference code only, not deployed
└── screenshots/         # UI verification screenshots
```

## Setup

```bash
npm install
```

Create environment files from the examples:

```bash
cp web/.env.local.example web/.env.local
cp worker/.env.example worker/.env
```

Required web variables:

```text
DATABASE_URL=
ENCRYPTION_KEY=
AWS_REGION=
COGNITO_USER_POOL_ID=
COGNITO_CLIENT_ID=
COGNITO_CLIENT_SECRET=
```

Required worker variables:

```text
DATABASE_URL=
ENCRYPTION_KEY=
RESEND_API_KEY=
WORKER_ID=
```

`ENCRYPTION_KEY` must be the same 64-character hex key for web and worker.

## Development

```bash
npm run web:dev
npm run worker
```

Build commands:

```bash
npm run web:build
npm run worker:build
npm run build
```

Lint:

```bash
npm run lint
```

There is currently no automated test framework configured.

## Database

The active schema is PostgreSQL with Cognito user IDs:

- `supabase/migrations/001_rds_schema.sql`
- `supabase/migrations/002_one_time_targets.sql`
- `supabase/migrations/003_class_schedules.sql`
- `supabase/migrations/004_credential_separate_iv.sql`
- `supabase/migrations/005_booking_timing.sql`
- `supabase/migrations/006_optional_time_arketa.sql`
- `supabase/migrations/007_history_class_name.sql`

Supabase Auth and Supabase client helpers are legacy and should not be reintroduced.

## Consolidation Note

`Fitness-sniper` is the active app. The old `class-sniper` tree was an earlier name/copy and should stay deleted. Archive files are retained only for historical selector and flow reference.
