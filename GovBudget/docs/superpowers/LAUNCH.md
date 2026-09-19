# Fiscal Receipts Launch Checklist

Ordered, operator-executable steps to take the site from a green local build to a
live Vercel deployment backed by Cloudflare R2 for large static assets.

Every step is idempotent — you can re-run any of them safely.

---

## Prerequisites

- Python env active (`uv run` or activated venv)
- Node 20+, npm available
- rclone installed: `brew install rclone` (needed for step 4)
- Vercel CLI installed: `npm i -g vercel`
- Accounts: Cloudflare R2, Vercel (free tier, `andes.lee444@gmail.com`)

---

## Rule — ingestion run from a git worktree must not record worktree paths (2026-09-12)

`jbook_documents.file_path` is an absolute path that later runs re-open verbatim:
`export_site`'s document-copy loop raises `FileNotFoundError` on any `status='downloaded'`
row whose file is missing, so one bad path hard-fails the export for everyone. A worktree's
`data/raw_docs` is a **symlink** into the main checkout's lake, so ingestion run from
`.claude/worktrees/<name>/GovBudget` used to record `…/.claude/worktrees/…/data/raw_docs/…`
— a path that vanishes when the worktree is removed. This happened to doc 459 (FY2026 DHP
volume) on 2026-09-12 and was repaired with a one-row `update`.

**All four** commands that write `file_path` now record `Path.resolve()` (see
`jbooks.acquire.lake_path`), and `config._lake_path` resolves the lake constants they build
from (`RAW_DOCS_DIR`, `RAW_DIR`, `PARQUET_DIR`, `DUCKDB_PATH`, `SITE_DIR`), so the fix holds at
the root as well as at each writer:

| command | writer |
|---|---|
| `jbooks acquire` | `jbooks/acquire.py` `acquire_pending` |
| `jbooks ingest-local` | `jbooks/service_fetch.py` `register_local_documents` (the operator DROP DIR, not `raw_docs`) |
| `jbooks backfill --service navy` | `jbooks/service_fetch.py` `download_registered_playwright` |
| `jbooks backfill --service {army\|af\|spaceforce} --source archive` | `cli.py` `_service_archive_download` |

The archive route was missed by the first fix and caught on re-review; it is the prescribed
route for the WAF-blocked services (ROADMAP #111), and 31 rows already carry
`acquisition='archive'` — 17 of them `status='downloaded'` (Army 10, Air Force 7), the rest
superseded (measured 2026-09-12). Each writer has its own symlink regression test in
`tests/jbooks/test_acquire.py`, and — since 2026-09-12 — that module's
`test_file_path_writer_census_matches_the_four_tested_writers` parses `src/govbudget/**/*.py`
for SQL that writes `file_path` and fails unless the writer set is exactly these four, so a
**fifth** writer is a red test, not a dead citation. (Before that census the four cases pinned
the four writers that existed and were blind to a new one — which is how the archive route
stayed missing until a human re-grepped.) A new `DATA_DIR / "…"` lake constant that skips
`_lake_path` is caught by `tests/test_config.py::test_lake_dirs_are_symlink_resolved` (the five
named constants) and by `::test_every_data_dir_path_constant_is_resolved`, which sweeps every
`Path` constant in `config`, including ones added later. **Both of those cases only bite when
the suite runs INSIDE a worktree**, where `data/`'s entries are symlinks into the main lake: in
the main checkout every lake entry is a real directory, so `p == p.resolve()` holds for an
unrouted constant exactly as it does for a routed one and the sweep passes vacuously. Run them
from the worktree (`uv run --no-sync python -m pytest tests/test_config.py` there) before
trusting the claim after touching `config`. (`_lake_path` itself is proven anywhere, by
`tests/jbooks/test_acquire.py::test_config_lake_path_collapses_a_symlinked_lake_dir`, which
builds its own symlink under `tmp_path`; what needs the worktree is the claim about the
CONSTANTS.)

After ANY ingestion from a worktree, confirm nothing slipped through:

```bash
psql "$GOVBUDGET_PG_DSN" -c \
  "select id, file_path from jbook_documents where file_path like '%/.claude/worktrees/%';"
# expect 0 rows
```

---

## Step 0 — Loader order (run BEFORE export-site, whenever links are rebuilt)

The budget→award link loaders share one table (`budget_line_awards`) and one
unique key `(pe_bli, exhibit, fiscal_year, award_piid)`. Each writes only its
own rows: the mechanical crosswalk has no delete at all, it upserts under a
method guard (`on conflict … do update … where method in ('account',
'account+subagency','account+tokens')`), while the FPDS and announcement/
subaward loaders delete their own method's rows before reinserting. Either
way, the order they run in decides which evidence a shared key ends up
carrying. **The canonical order is:**

```
govbudget jbooks crosswalk --org DARPA --dry-run   # plan first: pairs per edition FY, nothing written
govbudget jbooks crosswalk --org DARPA             # mechanical account* rows; window = each line's own edition FY. Add --yes once the plan is read — DARPA projects 761,029 pairs, above the 500,000 abort threshold
uv run python scripts/derive_ap_links.py        # FPDS acquisition-program tags
uv run python scripts/load_announcement_links.py  # defense.gov + FSRS subawards
govbudget jbooks export-facts        # Postgres -> parquet
govbudget build                      # dbt: parquet -> the mart
govbudget export-site                # mart -> data/site/
```

**Award window (#78, 2026-09-05).** With no flags, `jbooks crosswalk` matches
each budget line only against awards whose *federal* fiscal year equals that
line's own PB-edition `fiscal_year` — resolved per line, so a PB2017 line sees
FY2017 awards and a PB2026 line sees FY2026 awards. `--fy-start N --fy-end M`
(always together; one bound alone exits 2) pins one explicit window for every
line. `--all-years` is the opt-in to the old unbounded behaviour — that shape
is what produced the 2026-09-04 +2,214,705-row DARPA run (177 line-editions ×
13,216 awards). **Every** run is planned before it writes, `--all-years` or
not, and **refuses to write above 500,000 planned pairs unless `--yes`**: the
default window is not a small window, it is a smaller one. Measured read-only
2026-09-05, DARPA plans 761,029 pairs under the default against 124,502
mechanical DARPA rows in the table today, so a full DARPA re-run needs `--yes`
either way (every DARPA line carries account 0400, so each edition's 17–24
lines each match that FY's whole 097-0400 population — the account method's own
shape, #85's question, not the window's). Run `--dry-run` before any write; it
plans under whichever window you gave, prints the pairs per organization and
edition FY, and writes nothing.

**Determinism (#85, 2026-09-05).** Two `jbooks crosswalk` runs over the same
lake and the same `budget_lines` write byte-identical mechanical rows. The
run reads ONE canonical title per (pe_bli, exhibit, fiscal_year, account)
key within the organization — the latest document's row, then the lowest
budget activity, then the first title (`CANONICAL_LINE_SQL`; three live keys
carry two titles: HCMC00 and JSE000 on 3010F, SFV000 on 3022F, all org F) —
and grades each award from ALL of its transactions in the window, never from
whichever one was scanned first: an award carries a sub-agency if ANY of its
transactions was awarded under it (the rationale says "on k of n
transaction(s)"), token overlap is taken over the union of its distinct
transaction and base descriptions, the recipient is the latest transaction's,
and the account obligation is an exact decimal sum. Before this,
`any_value()` picked a different transaction on consecutive identical runs
for about 6,000 of the 13,216 `097-0400` awards (three read-only runs,
2026-09-10) — the ±346 medium / +119 high flip #85 recorded. After ANY
re-run, prove it on the real table: run the crosswalk twice and both of these
must print the same thing each time —

    select method, confidence, count(*) from budget_line_awards
     where method in ('account','account+subagency','account+tokens')
     group by 1,2 order by 1,2;
    select count(*), md5(string_agg(
             pe_bli||'|'||exhibit||'|'||fiscal_year||'|'||award_piid||'|'||method
             ||'|'||confidence||'|'||coalesce(score::text,'~')||'|'||coalesce(rationale,'~')
             ||'|'||coalesce(recipient_name,'~')||'|'||coalesce(recipient_uei,'~')
             ||'|'||coalesce(matched_obligation::text,'~'),
             E'\n' order by pe_bli, exhibit, fiscal_year, award_piid))
      from budget_line_awards
     where method in ('account','account+subagency','account+tokens');

Baseline before any re-run (2026-09-10): 124,502 rows, md5
`3e8f7459808e9b4d9bb906096abaa79a` (account/low 114,638 ·
account+subagency/medium 9,337 · account+tokens/high 527). A changed md5
between two consecutive runs with no lake or `budget_lines` change is a bug,
not drift.

Weakest evidence first, strongest last: each stage may upgrade the key, none
may demote it. Two guards make that true regardless of who actually ran last,
so a mistaken order degrades nothing silently:

- `jbooks/crosswalk.py` restricts its upsert to
  `method in ('account', 'account+subagency', 'account+tokens')`;
- `scripts/derive_ap_links.py` restricts its upsert to
  `method not in ('announcement+lexicon', 'subaward+lexicon')`
  (added 2026-09-04 — without it, running the deriver after the announcement
  loader rewrote an `announcement+lexicon`/high row to `fpds-ap`/medium and
  orphaned its `award_link_sources` row, losing the article from the citation
  panel with every gate still green).

`scripts/load_announcement_links.py` is not a third guard — it is the reason to
be careful with that loader's ARGUMENTS. It deletes and rebuilds its WHOLE
partition (`announcement+lexicon` + `subaward+lexicon` links and their
`award_link_sources` rows) from the wave result files on its command line, so
pass every wave file on every run: a subset unpublishes the rest, with every
gate green (ROADMAP #87). The loader prints `replacing N stored … with M`
before it commits — read that line.

After ANY of these run, `export-facts` → `build` → `export-site` must run too,
or the mart and Postgres disagree and `export_site` fails loudly on the
announcement-source check.

---

## Step 1 — Export site artifacts

Regenerates `data/site/` from the DuckDB warehouse.  Must run before build so
the static JSON sidecars and parquet files are current.

```bash
govbudget export-site
```

Verify: `data/site/manifest.json` `built_at` timestamp is fresh.

---

## Step 2 — Build with NEXT_PUBLIC_SITE_URL

Set the Vercel deployment URL as the sitemap origin **before** building.  While
the custom domain is tabled, use the Vercel preview URL assigned to the project
(e.g. `https://govbudget-xyz.vercel.app`).

```bash
# Substitute your actual *.vercel.app URL:
export NEXT_PUBLIC_SITE_URL=https://govbudget-xyz.vercel.app

cd site
npm run build   # runs prebuild → next build → postbuild (pagefind)
cd ..
```

`site/out/` will contain the full static export (~1.0 GB, ~49 k files).

**Vercel free-tier limits:**
- Deployment source upload: 100 MB compressed — `site/out/` at ~1.0 GB raw
  exceeds this.
- **Mitigation:** the large binary assets (pdfs/, data/, workbooks/, citations/)
  are served from R2, not Vercel.  Vercel only serves the HTML/JS/CSS bundle
  plus small JSON sidecars.  Keep `site/out/` lean by ensuring the `public/`
  folder does not include the R2 asset directories.
- If the Vercel upload still exceeds limits, use `.vercelignore` to exclude
  `out/pdfs/`, `out/data/`, `out/workbooks/`, `out/citations/` (these folders
  should not be in `public/` in the first place — they live in `data/site/` and
  are served from R2 via `assetBaseUrl`).

Gate check (run after build):

```bash
cd site && npm run verify && cd ..
```

---

## Step 3 — Run verify-phase5b1 (citations gate)

Confirms citations.parquet is consistent with the warehouse before uploading
anything to R2.

```bash
govbudget verify-phase5b1
```

Expected: `verify-phase5b1: PASS`

---

## Step 4 — Upload assets to R2 ✅ DONE 2026-07-02 · RE-SYNCED 2026-07-04

52 objects / 154 MiB uploaded to `govbudget-assets` bucket.
Custom domain `assets.fiscalreceipts.com` live and Active.

> **RE-SYNC 2026-07-04 (Phase 5G):** `upload_r2.sh --live` moved 190 files /
> 1.48 GiB. The deploy drill rebuilds `site/out` + pushes to Vercel but does NOT
> re-sync `data/site/pdfs → R2`, so every post-launch phase (5E decade editions,
> 5F/5H, 5G Navy) had shipped citation metadata while the PDF binaries were
> missing from the CDN — the panel degraded to "open official source". **Run
> `R2_BUCKET=govbudget-assets ./scripts/launch/upload_r2.sh --live` after any
> ingestion phase, before/with the Vercel deploy.** (Backlog #27 folds this into
> the deploy sequence + adds a live-PDF-fetch gate.)

### 4a. Configure rclone (one-time)

```bash
brew install rclone
rclone config
# → New remote → name "r2"
# → Provider: S3 Compatible (Cloudflare R2)
# → access_key_id: <R2 API token key ID>
# → secret_access_key: <R2 API token secret>
# → endpoint: https://<ACCOUNT_ID>.r2.cloudflarestorage.com
# → Leave region blank
# → No ACL needed
```

> **Lesson (2026-07-02):** R2 scoped tokens must include `Object Read & Write`
> AND `Bucket Read & Write` permissions — the `HeadBucket` call rclone makes
> during `lsd` is blocked by object-only tokens, causing spurious "bucket not
> found → CreateBucket" attempts.  Add `no_check_bucket = true` to the rclone
> remote config to skip the check entirely.  Also: R2 API tokens take ~1 min to
> activate after creation.

### 4b. Apply the CORS policy (one-time)

Edit `scripts/launch/cors-policy.json`: replace `REPLACE_WITH_SITE_URL` with
your actual `NEXT_PUBLIC_SITE_URL` value, then apply:

```bash
# Using wrangler (requires an Admin API token — scoped tokens lack PutBucketCors):
wrangler r2 bucket cors put $R2_BUCKET \
  --rules scripts/launch/cors-policy.json

# Least-privilege path: Cloudflare dashboard
# R2 → your bucket → Settings → CORS → Add policy → paste the JSON
```

Policy summary:
- AllowedMethods: GET, HEAD, OPTIONS
- AllowedHeaders: range, origin, content-type, accept
- ExposeHeaders: content-range, accept-ranges, content-length
- MaxAgeSeconds: 3600

> **Lesson (2026-07-02):** `PutBucketCors` requires an Admin-level API token.
> Scoped R2 tokens are insufficient; the dashboard paste is the least-privilege
> path.

### 4c. Dry-run sync

```bash
R2_BUCKET=govbudget-assets ./scripts/launch/upload_r2.sh
```

Review the output — rclone will print what would be transferred without moving
any files.

### 4d. Live upload

```bash
R2_BUCKET=govbudget-assets ./scripts/launch/upload_r2.sh --live
```

> On a normal deploy you do **not** run this by hand — `scripts/launch/deploy.sh`
> runs it as step 1 (see §7d).  Run it standalone only when syncing assets
> without shipping pages.

Uploads four directories from `data/site/` to R2:

| Local | R2 path | Size |
|---|---|---|
| `data/site/pdfs/` | `/pdfs/` | ~149 MB |
| `data/site/data/` | `/data/` | ~3.2 MB |
| `data/site/workbooks/` | `/workbooks/` | ~1.2 MB |
| `data/site/citations/` | `/citations/` | ~1 MB |

### 4e. Connect custom domain (one-time)

> **Lesson (2026-07-02):** A custom domain on R2 is NOT just a CNAME.  You must
> go to R2 → your bucket → Settings → Custom Domains → Connect Domain, enter the
> subdomain, and let Cloudflare add the CNAME automatically.  Manually adding a
> CNAME at the DNS level without the Connect Domain step returns Cloudflare error
> 1014 ("CNAME cross-user banned") until the bucket binding is active.  The
> binding initializes for a few minutes after connection — expect 1014 responses
> until it turns Active.

---

## Step 5 — Rewrite config.json ✅ DONE 2026-07-02

`assetBaseUrl` set to `https://assets.fiscalreceipts.com` in both
`site/public/config.json` and `site/out/config.json`.

```bash
node scripts/launch/rewrite-config.mjs https://assets.fiscalreceipts.com
```

Verify output: the script prints before/after for each target file.

---

## Step 6 — CORS live test ✅ DONE 2026-07-02

All 7 assertions PASS (exit 0) against the live endpoint:

```
R2_HOST=https://assets.fiscalreceipts.com \
SITE_URL=https://govbudget.vercel.app \
  ./scripts/launch/cors_live_test.sh
```

```
── 1. OPTIONS preflight ──────────────────────────────────────────────────
  PASS: status 204
  PASS: Access-Control-Allow-Origin echoes SITE_URL: https://govbudget.vercel.app
  PASS: Access-Control-Allow-Headers contains 'range': range

── 2. Ranged GET ─────────────────────────────────────────────────────────
  PASS: status 206 Partial Content
  PASS: Access-Control-Allow-Origin echoes SITE_URL: https://govbudget.vercel.app
  PASS: Content-Range: bytes 0-1023/3175571
  PASS: Accept-Ranges declared in Access-Control-Expose-Headers: content-range,accept-ranges,content-length

All CORS assertions passed.
```

> **Script bug fixed (2026-07-02):** `set -euo pipefail` + the `grep` pipeline
> inside `header_value()` exited with code 1 when R2 omits a standalone
> `Accept-Ranges` header (it lists it in `Access-Control-Expose-Headers`
> instead).  The grep failure propagated through the command substitution and
> aborted the script silently before any leg-2 assertions printed.  Fix: added
> `|| true` to the `grep` and `awk` pipelines in `header_value()`/`status_code()`
> so a no-match grep returns 0; updated the Accept-Ranges assertion to accept
> the expose-headers declaration as equivalent.

Without env vars the script prints the full manual checklist and exits 0
(`SKIPPED`).

---

## Step 7 — Vercel project setup

### 7a. Connect project

```bash
vercel link
# → Set up and deploy → Y
# → Which scope: andes.lee444@gmail.com
# → Found existing project? No → Create new project
# → Project name: govbudget (or govbudget-site)
```

### 7b. Configure Root Directory

In the Vercel dashboard → Project Settings → General:

- **Root Directory:** `GovBudget/site`
  (Vercel builds from here; `next.config.ts` is at this level)
- **Framework:** Next.js (auto-detected)
- **Build Command:** (leave default — `npm run build`)
- **Output Directory:** `out`

### 7c. Set environment variables

```bash
vercel env add NEXT_PUBLIC_SITE_URL production
# value: https://govbudget-xyz.vercel.app
```

Add the same for `preview` and `development` environments as needed.

### 7d. Deploy

**One command.  Do not run `vercel` by hand.**

```bash
# build first — Vercel does NOT build this site
cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build && cd ..

./scripts/launch/deploy.sh
```

`scripts/launch/deploy.sh` **is the source of truth for the deploy sequence**;
this section explains *why* it does what it does and does not restate the
commands.  Read the script (or `--help`) for flags.  It runs, in order:

1. **preflight** — `site/out/` present and complete, `vercel.json` present,
   rclone and the PDF source directory present;
2. **`upload_r2.sh --live`** — sync `pdfs/ data/ workbooks/ citations/` to R2;
3. **`vercel --prod --yes --archive=tgz` from `site/out/`**;
4. **`verify_live_assets.mjs`** — fetches recently-added `jbook_pdf` assets
   from the CDN and fails the deploy if they are not there.

> **Why steps 2 and 4 exist (ROADMAP backlog #27).**  The R2 sync used to be a
> separate thing someone had to remember after every ingestion phase.  Nobody
> remembered, so the new PDF binaries were missing from the CDN and every
> citation panel on the new pages silently fell back to "open official source".
> It shipped that way for every post-launch phase until the 2026-07-04 catch,
> and no gate noticed — no gate *could*, because the property is production CDN
> state, which does not exist before a deploy.  Binding the sync to the deploy
> is the fix; step 4 is the alarm.  Assets go up **before** pages, so no live
> page ever cites a binary that is not there yet (`upload_r2.sh` never deletes,
> so an early sync is always safe).

**Both the directory and the flag in step 3 are load-bearing.  Do not simplify
this to `vercel --prod` from `site/`.**

- **Run it from `site/out/`, never `site/`.**  Vercel does *not* build this site
  in the cloud — it serves the prebuilt static export.  Deploying from `site/`
  makes Vercel run `npm run build`, whose `prebuild` step
  (`prepare-assets.mjs`) reads `data/site/json/site_meta.json` — a path outside
  `site/` that is never uploaded.  It fails with:
  `❌  FATAL: data/site/json/site_meta.json not found.`
  A correct deploy logs `Extracted <N> deployment files` where N equals
  `find site/out -type f | wc -l`, then `Build Completed in /vercel/output`
  in ~30s with no `npm install`.
- **`--archive=tgz` is required.**  The default per-file upload sends a JSON
  manifest of every file; at ~89.5 k files that exceeds Vercel's request limit
  and fails with `Request body too large. Limit: 10mb` *before* anything
  uploads.  `--archive=tgz` sends one tarball and has no such limit.  This
  became necessary on **2026-08-05**: the identical 89,494-file deploy
  succeeded 15 h earlier on the manifest path, so the limit tightened
  server-side rather than the site outgrowing it.  Retrying, upgrading the CLI
  (54.12.2 → 58.5.1 was tried), or adding `.vercelignore` do **not** help.
- `site/out/` has no `.vercel/` link (it is wiped by each build), so the project
  and org IDs go in as env vars.  `deploy.sh` carries them as defaults
  (`VERCEL_PROJECT_ID` / `VERCEL_ORG_ID` override them).

Do **not** try to shrink `site/out/` by excluding `json/`, `json-lite/`,
`duckdb/`, or `og/` — despite their size these are served from Vercel, not R2
(no R2 host appears in the built chunks).  R2 serves only `pdfs/`, `data/`,
`workbooks/`, and `citations/`, none of which are in `site/out/`.

**Post-deploy verification is step 4 of `deploy.sh`, not a checklist.**  It runs
`scripts/launch/verify_live_assets.mjs`, which asserts:

- the N most recently added `jbook_pdf` assets return 200/206 from
  `assets.fiscalreceipts.com` with a non-zero body starting `%PDF-`;
- `citations/citations.parquet` is reachable (proves the `data/` + `citations/`
  syncs landed);
- `https://fiscalreceipts.com/fact/<id>` resolves — the `/fact/` rewrite comes
  from `site/out/vercel.json` and silently dies if the wrong directory was
  deployed.

It exits non-zero on any failure and can be run on its own at any time to audit
what is live:

```bash
node scripts/launch/verify_live_assets.mjs            # newest 5 cited PDFs
node scripts/launch/verify_live_assets.mjs --count=20
node scripts/launch/verify_live_assets.mjs --sha=<sha256>   # one specific asset
```

It is deliberately **not** a gate in `npm run verify`: that suite is hermetic
and offline, and CDN state cannot be asserted before the upload that creates
it.  See the header of `verify_live_assets.mjs` for the full reasoning.

---

## Step 8 — Smoke checks

After deployment, verify the following manually:

### 8a. Citation panel — PDF from R2

1. Open a program page, e.g. `/program/0400D/`
2. Click any cited figure (blue badge)
3. The PDF.js panel should open and scroll to the highlighted excerpt
4. Network tab: PDF request goes to `pub-<hash>.r2.dev` (not Vercel)
5. No CORS errors in the browser console

### 8b. Explorer query (DuckDB-WASM)

1. Navigate to `/data/`
2. Run a simple query: `SELECT count(*) FROM dim_entities`
3. Result should appear within 2–3 seconds (first load fetches WASM)
4. Run a query referencing a Parquet file:
   `SELECT * FROM 'citations/citations.parquet' LIMIT 5`
5. Expect rows returned — this proves R2 CORS is working for data files

### 8c. Downloads page

1. Navigate to `/downloads/`
2. Verify all download cards show data-driven counts (no hardcoded "44,754")
3. Click "citations.parquet" download link — URL should be
   `/citations/citations.parquet` (not `/data/citations.parquet`)
4. Confirm the file downloads from R2

---

## Step 9 — Unblock the API-key pair

Two commands require `ANTHROPIC_API_KEY` to run live.  Without it both
commands report `BLOCKED` (not `FAIL`) and exit with code 2.

```bash
export ANTHROPIC_API_KEY=sk-ant-...

# Submit the dossier batch (cost-capped ≤ $50):
govbudget dossiers submit

# Run the full verify-phase5 gate suite (NL eval ≥ 90%):
govbudget verify-phase5
```

Expected terminal state after both complete:
- `verify-phase5: PASS` (or `exit 2` if all gates pass but dossier batch is
  still running — run `govbudget dossiers collect` after the batch ends and
  re-run `verify-phase5`)
- `dossier_gate: PASS`

---

## Service J-books (Phase 5G) — Navy automated, Army/AF manual

Beyond the defense-wide comptroller books, the site ingests the military
services' own R&D and procurement justification books. Access differs per
service (probe evidence: `docs/superpowers/reviews/5g-probe/PROBE-REPORT.md`):

| Service | Path | Why |
|---|---|---|
| **Navy** | automated (`jbooks backfill --service navy`) | reachable via headless Chromium; the `/fmc` bot-WAF does not block a real browser |
| **Army** | **manual** (`jbooks ingest-local --service army`) | Akamai edge WAF returns **403 to headless Chromium** at every entry point — a finding, not a challenge. No stealth/evasion transport is built or permitted. |
| **Air Force** | **manual** (`jbooks ingest-local --service af`) | CAC-gated; no anonymous automated fetch |

### Navy — automated backfill

```bash
govbudget jbooks backfill --fiscal-year 2026 --service navy
```

This Playwright-fetches the FY2026 Navy index
(`https://www.secnav.navy.mil/fmc/fmb/Documents/26pres/`), builds a download
plan, and:

- classifies each PDF via the Navy appropriation-code allowlist (`NAVY_NAMES`
  in `registry.py`): 5 RDTEN + 12 procurement books → `(family, org='N')`;
- **de-duplicates the RDTE BA-splits** — the five `RDTEN_BA*_Book.pdf` files
  each embed the SAME full 252-PE master book, so only the lowest-BA volume
  (`RDTEN_BA1-3_Book.pdf`) registers; the other four are recorded in the
  edition manifest under `services.navy_2026.exclusions`
  (rule `rdte-ba-split-duplicate`);
- excludes the 19 non-justification volumes (O&M / MilPers / MilCon / BRAC /
  working-capital / overview), rule `non-justification-appropriation`;
- registers each keeper with `acquisition='playwright'`, downloads through the
  browser context (sha256 + size verified, 2–4 s throttle, **resume-safe** —
  a re-run skips books already `downloaded`), then runs the standard
  extract → reconcile scoped to org `N`.

### Army / Air Force — manual drop-dir

A human with normal browser (or CAC) access downloads the service's R&D and
procurement justification PDFs to a directory, then:

```bash
govbudget jbooks ingest-local \
  --service army --fiscal-year 2026 \
  --source-url "https://www.asafm.army.mil/Budget-Materials/Budget2026/" \
  /path/to/army-drop-dir
```

Every classifiable PDF in the directory is registered with
`acquisition='manual'` and the operator-supplied `--source-url` (recorded on
each document for provenance; a per-file `#<basename>` fragment keeps rows
distinct under one URL). PDFs the classifier cannot place are **reported, not
registered** — the operator sees exactly what was skipped. `--service`,
`--source-url`, and the directory argument are all required.

> Army routes here because its Akamai policy blocks even a real headless
> browser. Do **not** attempt a stealth transport (undetected-chromedriver,
> real-Chrome CDP attach, residential egress) without an explicit human
> decision — a WAF that blocks a normal browser is a finding, not a challenge.

---

## Step 10 — Domain cutover (TABLED)

Domain selection is tabled.  Current shortlist: `outlays.us`,
`fiscalreceipts.com`.

When a domain is chosen:

1. Add it to Vercel: Project Settings → Domains → Add
2. Update DNS at registrar (CNAME → `cname.vercel-dns.com`)
3. Wait for SSL provisioning (usually < 5 min)
4. Re-run step 5 with the custom domain as `assetBaseUrl` if the R2 bucket
   is also being served via a custom subdomain
5. Re-run step 4b (CORS policy) with the new origin
6. Re-run step 7c to update `NEXT_PUBLIC_SITE_URL`
7. Redeploy: `./scripts/launch/deploy.sh` (never bare `vercel --prod` — it
   skips the R2 asset sync)
8. Re-run step 6 (CORS live test) with the new domain

---

## Step 11 — Scheduled refresh (ROADMAP #8)

`govbudget refresh` is the monthly DATA refresh as one command — not the whole
drill: the Step 0 link loaders, `migrate`, `oversight`, `states`,
`entity-graph`, `lineage`, `dossiers` and the J-book/GAO ingests all stay
operator-run. Known limitations below covers two of those: the Step 0 link
loaders (second bullet) and the J-book/GAO ingests (third bullet). `dossiers`
has its own procedure, Step 9 above. `migrate`, `oversight`, `states`,
`entity-graph` and `lineage` are operator commands with no step of their own in
this document — CLAUDE.md lists them. Step 0 is exclusively the budget→award
link-loader order, not a catch-all reference for the rest. What it does run,
in order: preflight -> the three
USAspending/Treasury syncs -> (quarterly) the LDA pull -> the
golden-fixture parser gate -> `jbooks export-facts` -> `build` ->
`export-site` -> `npm run build` -> `npm run verify` ->
`scripts/launch/deploy.sh`. It stops at the first failure and tells you the
`--from` flag that resumes there.

```bash
# See the plan without running any of it.
uv run python -m govbudget refresh --dry-run --yes

# The monthly run, interactively (it will ask you to type 'yes').
uv run python -m govbudget refresh

# The quarterly run adds the LDA pull.
uv run python -m govbudget refresh --quarterly

# Resume a run that died in dbt; stop before the deploy.
uv run python -m govbudget refresh --from build --until site-verify --yes
```

Stage names, in order: `preflight`, `sync-archive`, `sync-subawards`,
`sync-fiscaldata`, `influence-pull`, `fixtures`, `export-facts`, `build`,
`export-site`, `site-build`, `site-verify`, `deploy`.

**What the preflight checks:** >=25 GB free at `data/raw`, Postgres answering on
`GOVBUDGET_PG_DSN`, a DuckDB lake that EXISTS at `GOVBUDGET_DUCKDB` and whose
write lock is free (nothing else holding it), an rclone remote named `r2`, and
`vercel whoami` succeeding. It also CREATES `logs/` when it is missing (ruling
R-20b-8) — gitignored, so a fresh clone has none, and a hand-typed run has no
reason to fail over a directory the process can make for itself. Every failure
is reported at once, and nothing runs until they are all clear. The
rclone/vercel checks are skipped when `--until` stops the run before `deploy`.
**`--from` skips preflight entirely** (it is a stage, and `--from` slices the
graph), so a resume trades the early warning for the resume — which is why
`refresh.sh` never passes `--from`.

One of those checks exists because its failure mode is silent rather than loud:
the lake is checked for EXISTENCE before the lock, because `duckdb.connect` on
a path that does not exist CREATES an empty database, so a mistyped
`GOVBUDGET_DATA` would otherwise pass preflight green and fail in dbt half an
hour later. The `logs/` mkdir is the opposite case — it fixes what it finds,
and it cannot help a SCHEDULED run: launchd opens
`StandardOutPath`/`StandardErrorPath` **before** exec and does not create
missing parents, so by the time preflight runs, a scheduled job with no `logs/`
has already lost its output. That is what the install snippet's own
`mkdir -p "$PWD/logs"` below is for; preflight's mkdir does not replace it.

**Timeouts: the probes have one, the stages do not.** `rclone listremotes` and
`vercel whoami` get 60 s each; a probe that does not answer is an ordinary
preflight failure naming that probe — and a hung `vercel whoami` is reported as
a hang whose answer is unknown, not as a logged-out CLI with `vercel login` as
the remedy. Stages get no timeout at all, because `dbt build` and
`npm run build` routinely run 30+ minutes and a full
`sync-archive` sweep runs hours — any limit small enough to catch a wedged
stage would kill healthy ones. The cost is real and worth knowing: a stage that
hangs holds its launchd slot forever, and launchd starts no second instance of
a label whose previous instance is still alive, so the monthly job simply stops
happening. If a scheduled run's log goes quiet, check for a live process before
assuming the schedule is fine.

**Only one refresh runs at a time.** `run_refresh` builds the stage plan and
runs the confirmation prompt first, and takes an exclusive `flock` on
`data/refresh/.lock` only once that plan is confirmed — a bad
`--from`/`--until` or a declined confirmation never reaches the lock at all. A
second invocation that DOES reach it exits non-zero immediately and names the
lock. `--dry-run` is the exception
(ruling R-20b-7): it runs no stage and writes no record, so it takes no lock at
all and the plan stays readable while a real refresh is running. This is not
hypothetical — the monthly and quarterly jobs are different launchd labels, so
launchd's
same-label suppression does not keep them apart, and in Jan/Apr/Jul/Oct they
fire 24 hours apart. The lock is released when the process exits, crash
included, so there is no stale lock to clear by hand.

**A non-zero exit from any stage is fatal for the run**, and `sync-archive` is
the stage where that matters most. `cmd_sync_archive` iterates (type x FY) and
does NOT stop at the first bad year: it catches the exception, prints
`contracts fy2019: FAILED (PartitionShrinkError: ...)`, CONTINUES to the next
FY, and exits 1 at the end with a summary line naming every failed pair. So the
orchestrator's "stage failed" is the whole sweep's verdict, not one year's —
read the printed `FAILED` lines and the summary to learn which FY refused, then
decide per FY whether the shrink is real before re-running that FY by hand with
`--allow-corpus-shrink`.

**The drift record** lands in `data/refresh/last_run.json` (gitignored) and
carries three alarms, each also printed to stderr as `DRIFT ALARM: ...`:

1. **Cadence age.** Every dataset in `data/manifest.jsonl` is aged against the
   cadence its source publishes on (`export_site._DECLARED_CADENCE`). A dataset
   past its window is named. **As of 2026-09-18 this alarm already fires on
   every run, `--dry-run` included:** `contracts`, `assistance` and `subawards`
   were last ingested 2026-06-11 — 99 days — against a monthly claim. That is a
   true statement about the lake, not a bug. `contracts` and `assistance`
   clear on the first monthly run that ingests a newly published archive; an
   un-republished upstream leaves the cadence alarm standing (with a stall
   alarm beside it) — `sync_archive` skips on `has_file(...)` and appends no
   manifest record when it skips, so a "successful" (exit 0) monthly run does
   not by itself move `newest_downloaded_at`. `subawards` cannot clear at all
   on the current `FY_END` — the stage returns early on an FY already in the
   manifest (first Known limitation below), so its cadence alarm stands beside
   its stall alarm until `FY_END` moves.
2. **Stall.** A sync stage that exits 0 without advancing its dataset's newest
   `downloaded_at` is named as skipped, not refreshed. `ingest_advanced` in the
   record says per dataset whether it actually moved.
3. **Unparseable manifest lines.** A line that is not JSON, or carries no
   dataset/timestamp, is counted rather than skipped in silence
   (`unparseable_lines` in the record): a dropped line makes its dataset vanish
   from the report, and the stall check would then describe a record that
   exists as absent. Gate 24 leg m treats one such line in the same file as
   fatal; this alarm is deliberately laxer — a partial final line is ordinary
   crash residue and must not stop a refresh — but it is never silent.

**An alarm never fails the run** (ruling R-20b-6). `record["ok"]` stays true and
the command still exits 0: a cadence alarm fires on data the *upstream* has not
republished, and failing a scheduled run for that would train the operator to
ignore the failure. Alarms are printed and recorded, nothing more — so after a
scheduled run the operator reads `data/refresh/last_run.json` (or
`logs/refresh-*.err.log`). Nothing polls either file for you. That record is
the last INVOCATION's outcome, not the last successful one: every path that
leaves `run_refresh` once the lock is held writes it — a preflight failure, a
stage failure, an unreadable manifest and a Ctrl-C mid-stage all included —
each with `"ok": false` and an `error` saying which. The plan and the
confirmation prompt run BEFORE the lock, so a bad `--from`/`--until`, a
declined confirmation and a no-TTY run without `--yes` are a run that never
started and write nothing at all, the same as a refused second instance — none
of them may overwrite the record of a run that actually happened.

**What the `fixtures` stage is, and is not.** It runs `tests/influence`,
`tests/jbooks`, `tests/oversight` and `tests/states` after the pulls and before
anything derived is rebuilt, so a broken parser stops the run instead of
propagating into the mart, the site and the CDN. It is **not** an upstream-shape
alarm: those suites read *committed* fixtures under `tests/fixtures/`, so a
changed upstream cannot break them. What does fire on a changed upstream is
already in the syncs — a missing required column raises `MissingColumnsError`, a
missing `meta.total-pages` raises `ValueError`, and a truncated archive raises
`PartitionShrinkError`. A **newly added** upstream column is detected by nothing;
that gap is open under ROADMAP #8. (The suites build their Postgres state in the
throwaway databases `govbudget_test` / `govbudget_test_root`, with one
exception: `tests/jbooks/test_era_keys.py` opens a connection to the real
`GOVBUDGET_PG_DSN` warehouse and only reads from it — SELECTs for its
keyspace-collision guard; `psycopg.connect(config.PG_DSN)` at
`test_era_keys.py:84` sets no read-only mode — and skips when that database is
unavailable.)

**Known limitations — read these before trusting a green run:**

- `sync-subawards` returns early once `data/manifest.jsonl` already holds that
  dataset + FY, so after the first successful pull for an FY the stage prints
  `skipped` every month. The stall alarm above is what says so out loud.
- The refresh does NOT run the budget->award link loaders (Step 0). New awards
  from a sync therefore carry no new links until an operator runs Step 0 and
  re-runs `export-facts` -> `build` -> `export-site`.
- Annual J-book and biennial GAO ingestion are NOT scheduled. `jbooks backfill`
  needs per-service transport decisions (`--source archive` for Army/AF/Space
  Force, an operator `--source-url` for `ingest-local`) that cannot be made
  unattended, and launchd cannot express a biennial cadence. Run those by hand
  — and note that nothing alarms when they go stale: they write no
  `manifest.jsonl` record, so the cadence alarm above cannot see them (next
  bullet).
- LDA, J-book and GAO ingests write no `manifest.jsonl` records, so the drift
  report can age none of the three. What gate 24 leg m says about them differs:
  it marks the J-book and GAO cadence lines UNMETERED (the `unmetered` markers
  on `/methodology/`), while the LDA section states no cadence at all, so leg m
  never sees LDA and never marks it anything. Open under ROADMAP #8.
- The quarterly stage explicitly passes `--years` computed as 2024 through the
  current calendar year (comma-joined, e.g. `2024,2025,2026,2027` in 2027)
  rather than inheriting the CLI's hardcoded `--years 2024,2025,2026` default,
  which a loaded job would still be using in 2027. The window grows at
  the end and never at the start: `influence pull` overwrites
  `lda_filings.parquet` in full, so a year the window stopped naming would be a
  year deleted from the corpus and from the citations that rest on it
  (`_LDA_FIRST_YEAR` in `src/govbudget/refresh.py` says so). A pull that needs
  years before 2024 is a by-hand `govbudget influence pull --years ...`.
- A crash between the MTS `COPY` and its swap leaves
  `data/parquet/mts_outlays/mts_table_5.parquet.incoming` on disk. dbt's source
  glob for that directory is `*.parquet` (`dbt/models/sources.yml:17`), which
  does not match it, so the leftover is invisible to the build and the next
  `sync-fiscaldata` overwrites it. There is no sweeper for it —
  `convert.sweep_incoming_dirs` only clears `fy=*.incoming` *directories*.
- The preflight's Postgres check connects to `GOVBUDGET_PG_DSN`. The `fixtures`
  stage creates its throwaway databases through `GOVBUDGET_TEST_PG_DSN`
  (default `postgresql://localhost/postgres`), which preflight does not check —
  same server in the normal setup, but not the same DSN.

### Loading the scheduler — the owner does this, never an agent

Two launchd templates ship under `scripts/launch/`. They are templates: nothing
in this repo installs, loads, or enables a scheduler.

```bash
cd /path/to/GovBudget
mkdir -p ~/Library/LaunchAgents
# launchd opens the job's log files BEFORE exec and will not create this
# directory, so the first scheduled run loses its output without it.
mkdir -p "$PWD/logs"

for cadence in monthly quarterly; do
  sed "s|__REPO_ROOT__|$PWD|g" \
    "scripts/launch/com.fiscalreceipts.refresh.${cadence}.plist.template" \
    > "$HOME/Library/LaunchAgents/com.fiscalreceipts.refresh.${cadence}.plist"
  plutil -lint "$HOME/Library/LaunchAgents/com.fiscalreceipts.refresh.${cadence}.plist"
  launchctl bootstrap "gui/$(id -u)" \
    "$HOME/Library/LaunchAgents/com.fiscalreceipts.refresh.${cadence}.plist"
done

launchctl list | grep fiscalreceipts        # confirm both are loaded
```

Monthly fires on the 5th at 03:00; quarterly on the 6th of Jan/Apr/Jul/Oct at
03:00 — so in those four months the pipeline runs twice, on the 5th and again
on the 6th. Logs land in `logs/refresh-*.log` (gitignored) — true once the
`mkdir -p "$PWD/logs"` above has been run, which is why it is in the snippet.
launchd opens those files before exec, so preflight's own mkdir runs far too
late to save a scheduled run's first output. To stop one:

```bash
launchctl bootout "gui/$(id -u)/com.fiscalreceipts.refresh.monthly"
```

The Mac Mini must be awake at 03:00 for these to fire (`pmset repeat wakeorpoweron
MTWRFSU 02:55:00`, or accept that a sleeping machine runs the job at next wake).

---

## Backups

### Raw announcements corpus

```bash
./scripts/launch/backup_raw_announcements.sh
```

Backs up the git-ignored `data/raw/announcements/` corpus (2,786 HTML + 2 auxiliary files, ~307 MB) to R2 under `research/announcements-raw/` with manifest presence verification.

---

## Quick reference — all commands

```bash
# 0. Links (Step 0) — plan, then write; read the plan before any six-figure write
govbudget jbooks crosswalk --org DARPA --dry-run
govbudget jbooks crosswalk --org DARPA            # add --yes once the plan is read

# 1. Export
govbudget export-site

# 2. Build
NEXT_PUBLIC_SITE_URL=https://govbudget-xyz.vercel.app \
  bash -c 'cd site && npm run build'

# 3. Gate
govbudget verify-phase5b1

# 4. Upload (dry-run first)
./scripts/launch/upload_r2.sh
./scripts/launch/upload_r2.sh --live

# 5. Rewrite config
node scripts/launch/rewrite-config.mjs https://pub-<hash>.r2.dev

# 6. CORS test
R2_HOST=https://pub-<hash>.r2.dev \
SITE_URL=https://govbudget-xyz.vercel.app \
  ./scripts/launch/cors_live_test.sh

# 7. Deploy — the ONLY deploy path (R2 assets, then Vercel, then live check)
./scripts/launch/deploy.sh

# 9. Unblock
export ANTHROPIC_API_KEY=sk-ant-...
govbudget dossiers submit
govbudget verify-phase5

# 10. Scheduled refresh (ROADMAP #8)
uv run python -m govbudget refresh --dry-run --yes    # plan only
uv run python -m govbudget refresh --quarterly        # full quarterly run
```
