# Technology Stack

**Analysis Date:** 2026-02-26

## Languages

**Primary:**
- TypeScript 5.x - All source code across worker, web, and shared packages
- SQL - PostgreSQL migrations in `supabase/migrations/`

**Secondary:**
- CSS - Tailwind v4 utility classes in web components

## Runtime

**Environment:**
- Node.js v24.13.0 (detected at analysis time)

**Package Manager:**
- npm 11.6.2
- Lockfile: `package-lock.json` (present, committed)
- Workspaces: npm workspaces monorepo (`worker`, `web`, `packages/shared`)

## Frameworks

**Core (Frontend):**
- Next.js 16.1.6 (`web/`) - App Router, server components, API routes
- React 19.2.3 - UI rendering

**Core (Worker):**
- No framework - plain Node.js daemon with `node-cron` scheduling

**Build/Dev:**
- tsx 4.19.2 - Worker dev runner (`npm run worker` → `tsx src/index.ts`)
- TypeScript compiler (`tsc`) - Worker production build to `worker/dist/`
- Next.js build - Web production build to `web/.next/`

**Linting:**
- ESLint 9 with flat config (`web/eslint.config.mjs`) - Web only; worker has no ESLint

**CSS:**
- Tailwind v4 (`tailwindcss ^4`) via `@tailwindcss/postcss` plugin
- `postcss.config.mjs` at `web/postcss.config.mjs`

## Key Dependencies

**Critical (Worker):**
- `playwright ^1.50.0` - Browser automation for MT browser fallback auth
- `playwright-extra ^4.3.6` - Playwright wrapper with plugin support
- `puppeteer-extra-plugin-stealth ^2.11.2` - Anti-bot-detection fingerprinting
- `pg ^8.13.1` - Direct PostgreSQL client (no ORM)
- `node-cron ^3.0.3` - Cron-based job scheduling (scheduler runs every 15 min)
- `resend ^4.1.2` - Transactional email (booking confirmations)
- `dotenv ^16.4.7` - Environment variable loading

**Critical (Web):**
- `next 16.1.6` - App Router framework
- `react 19.2.3` / `react-dom 19.2.3` - UI
- `@aws-sdk/client-cognito-identity-provider ^3.750.0` - AWS Cognito auth
- `pg ^8.13.1` - Direct PostgreSQL pool (same as worker)
- `zod ^4.3.6` - Schema validation (note: v4 API, breaking changes from v3)
- `react-hook-form ^7.71.1` - Form state management
- `@hookform/resolvers ^5.2.2` - Zod integration for react-hook-form

**UI Components (Web):**
- `radix-ui ^1.4.3` - Unified Radix package (NOT individual `@radix-ui/react-*` packages)
- `lucide-react ^0.564.0` - Icon library
- `class-variance-authority ^0.7.1` - Component variant utilities (shadcn/ui)
- `clsx ^2.1.1` - Conditional class names
- `tailwind-merge ^3.4.1` - Tailwind class deduplication
- `sonner ^2.0.7` - Toast notifications
- `next-themes ^0.4.6` - Dark mode support (hardcoded dark mode only)
- `react-day-picker ^9.6.4` - Date picker component
- `shadcn ^3.8.4` (devDep) - shadcn/ui component generator

**Shared Package:**
- `@fitness-sniper/shared *` - Internal workspace package, consumed as raw TypeScript (no build step)
- Next.js transpiles it via `transpilePackages: ['@fitness-sniper/shared']` in `web/next.config.ts`
- Worker resolves via workspace symlink

## Configuration

**TypeScript (Worker):**
- `tsconfig.json` (root, worker-targeted): `target: ES2022`, `module: NodeNext`, `moduleResolution: NodeNext`
- **Critical**: All worker imports require `.js` extensions due to `moduleResolution: NodeNext`
- Compiles to `worker/dist/`

**TypeScript (Web):**
- `web/tsconfig.json`: `module: esnext`, `moduleResolution: bundler`, `jsx: react-jsx`
- Path alias: `@/*` → `./src/*`
- `noEmit: true` (Next.js handles compilation)

**Build (Web):**
- `web/next.config.ts` - Minimal; sets `transpilePackages`
- `web/postcss.config.mjs` - Tailwind v4 via `@tailwindcss/postcss`
- `web/components.json` - shadcn/ui configuration

**Deployment:**
- `vercel.json` - Vercel deployment config
  - `installCommand`: `rm -rf node_modules package-lock.json && npm install`
  - `buildCommand`: `cd web && next build`
  - `outputDirectory`: `web/.next`
  - `framework`: `nextjs`

**Environment:**
- Worker: `worker/.env` (loaded via `dotenv/config` in `worker/src/index.ts`)
- Web: `web/.env.local` (Next.js convention)
- Required vars listed in INTEGRATIONS.md

## Platform Requirements

**Development:**
- Node.js 24+ recommended (v24.13.0 used)
- npm 11+ (workspaces support)
- PostgreSQL instance accessible via `DATABASE_URL`

**Production (Worker):**
- Mac Mini daemon (`tsx src/index.ts` or `node dist/index.js`)
- Chromium installed (Playwright downloads it)
- Always-on process; uses `SIGINT`/`SIGTERM` for graceful shutdown

**Production (Web):**
- Vercel (configured via `vercel.json`)
- Deployment triggers: git push, Vercel auto-deploy

---

*Stack analysis: 2026-02-26*
