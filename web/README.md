# Fitness Sniper Web

Next.js dashboard and API routes for Fitness Sniper.

## Responsibilities

- Cognito signup, login, logout, and session refresh.
- Authenticated dashboard shell.
- Credential save and validation.
- Snipe target CRUD.
- Schedule browsing with DB-first and live API fallback.
- Calendar, history, worker status, and success-rate views.

## Development

Run from the repository app root:

```bash
npm run web:dev
```

Build:

```bash
npm run web:build
```

Lint:

```bash
npm run lint --workspace=web
```

## Environment

Create `web/.env.local` from `web/.env.local.example`.

```text
DATABASE_URL=
DATABASE_POOL_MAX=2
ENCRYPTION_KEY=
AWS_REGION=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
COGNITO_USER_POOL_ID=
COGNITO_CLIENT_ID=
COGNITO_CLIENT_SECRET=
```

The web app uses direct PostgreSQL access through `pg` and AWS Cognito for auth. It does not use Supabase Auth or Supabase browser/server clients.
`DATABASE_POOL_MAX` is optional and defaults to `2` in production. AWS credentials are required in Vercel for Cognito admin signup confirmation.
