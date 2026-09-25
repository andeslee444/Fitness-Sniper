# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GovBudget powers **Fiscal Receipts** (fiscalreceipts.com) — a government spending-intelligence platform. It ingests federal data (USAspending award archives, Treasury MTS, DoD J-book budget PDFs, Senate LDA lobbying filings, GAO oversight reports), builds an evidence-tiered warehouse, and exports a fully static Next.js site where every figure carries a citation back to its source document.

**This directory is NOT its own git repository.** The repo root is one level up (`Cursor-Projects/`, `origin` → Fitness-Sniper). The standalone GitHub repo (github.com/andeslee444/fiscalreceipts, remote name `govbudget`) is produced with `git subtree split --prefix=GovBudget` run from the monorepo toplevel — never from inside `GovBudget/`. Commit with `--author="Andes Lee <andes.lee444@gmail.com>"`.

**Source of truth for project state:** `docs/superpowers/ROADMAP.md` — phase ledger, findings log, improvement backlog. Every phase loop ends by updating it. Backlog entries are never reworded when fixed; grep `**Status:**` to see what's actually open. `docs/superpowers/LAUNCH.md` covers launch/deploy operations.

## Commands

Python is managed with uv (Python ≥3.12, `.venv` present). The CLI has no installed entry point — invoke as a module.

```bash
uv run pytest                          # all Python tests
uv run pytest tests/test_convert.py    # one file
uv run pytest tests/lineage -k stated  # subset by dir/keyword

uv run python -m govbudget <command>   # the CLI (see below)
uv run python -m govbudget build       # dbt build (wraps dbt with project/profiles dirs)

# Site (from site/)
npm run dev          # Next.js dev server
npm run build        # SSG build → site/out (pre: assets/OG/feeds; post: build meta + pagefind)
npm run test         # vitest
npm run lint         # eslint
npm run verify       # the site gate registry — run before any deploy

# Deploy — the ONLY deploy path (R2 assets first, then Vercel, then live verification)
./scripts/launch/deploy.sh             # requires site/out built with NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com
./scripts/launch/deploy.sh --dry-run
```

**Critical deploy rule:** after any ingestion that adds PDFs/assets, the deploy must re-sync R2 (`deploy.sh` does this; `upload_r2.sh --live` is the underlying step). Skipping it silently degrades every citation panel on new pages to "open official source" — this happened in production and no gate can catch it because the property is CDN state.

### CLI subcommands (`python -m govbudget ...`)

Ingestion: `sync-archive` (USAspending zips → parquet), `sync-subawards`, `sync-fiscaldata` (Treasury MTS), `jbooks <action>` (scrape/backfill/acquire/extract/export-facts/crosswalk/provenance-pages/narrative-provenance/ingest-local), `oversight`, `states`, `influence pull|restamp|rematch`, `entity-graph`, `lineage`.

Warehouse/ops: `build` (dbt), `migrate` (Postgres migrations from `migrations/`), `review` (reconciliation queue), `export-site` (typed site artifacts + citations → `data/site/`).

Analysis: `analyst` (text-to-SQL agent), `dossiers fetch|submit|collect|gate` (Anthropic Batch API; needs `ANTHROPIC_API_KEY`), `evals refresh|check` (exit 1 if expected answers are stale).

Gates: `verify-phase1` … `verify-phase5` (plus `verify-phase5a/5b1/5b3/5e`, `verify-lineage`). **These are the acceptance gates for each phase — a phase is not done until its verify CLI passes.** `verify-lineage` (5 legs) is wired into `verify-phase5` assembly.

## Architecture

Two data stores with different jobs:

- **DuckDB + dbt** (`dbt/`, `data/duckdb/govbudget.duckdb`) — the analytics lake. Raw archives land as parquet under `data/parquet/`; `dbt build` (dbt-duckdb) constructs the star schema in `dbt/models/staging` → `dbt/models/marts`. Path overridable via `GOVBUDGET_DUCKDB`.
- **PostgreSQL** (`migrations/*.sql`, DSN via `GOVBUDGET_PG_DSN`, default `postgresql://localhost/govbudget`) — curated J-book facts, narratives, provenance pages, program lineage, adjudications. Schema evolves only through numbered migrations applied by `migrate`.

Pipeline flow, end to end:

```
sync-* / jbooks / oversight / states / influence     (raw → data/raw, data/parquet, Postgres)
  → build (dbt star schema in DuckDB)
  → entity-graph / lineage / crosswalk               (derived layers)
  → export-site                                      (typed artifacts + citations → data/site/)
  → site: npm run build                              (SSG reads data/site → site/out)
  → scripts/launch/deploy.sh                         (R2 assets → Vercel → live check)
```

The site (`site/`, Next.js 16 + React 19 + Tailwind v4) is fully static — no server. Client-side querying uses DuckDB-WASM against the shipped parquet warehouse; PDF citations render via PDF.js from R2-hosted binaries; search is MiniSearch + pagefind. Python and TypeScript deliberately mirror each other in several places (e.g. FY-range labels in `export_site.py` vs `site/src/lib/fy-range.ts`; evidence tiers vs `site/src/lib/evidence.ts`) — when you change one side, find and change the mirror, and expect a gate in `site/scripts/gates/` to enforce the pairing.

`src/govbudget/config.py` loads a gitignored `.env` at the GovBudget root (real env vars always win). Key vars: `GOVBUDGET_DATA`, `GOVBUDGET_DUCKDB`, `GOVBUDGET_PG_DSN`, `GOVBUDGET_PDF_BASE_URL`, `ANTHROPIC_API_KEY`.

## Key Principles

- **Every number must trace to a citation.** The whole product is provenance. New figures need a citation/basis chip; the verify CLIs and site gates check number↔citation binding, but prose claims around a true cited number are the known blind spot — read narratives as assertions, not decoration.
- **Publish the smaller true number** (owner decision 2026-08-07): when a headline conflicts with evidence, shrink the claim and label it a correction — never widen the claim to fit the number.
- **Gates over vibes.** Fixes land with a gate or eval that would have caught the bug. The site gate registry lives in `site/scripts/verify.mjs` + `site/scripts/gates/`; Python-side gates are the `verify-*` CLI legs.
- **Service J-books** (Army/AF/Space Force) are WAF-blocked at origin — backfill uses `--source archive` (Internet Archive mirror) or the manual `ingest-local` drop-dir path with an operator-supplied `--source-url`.
