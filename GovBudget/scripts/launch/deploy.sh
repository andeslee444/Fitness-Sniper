#!/usr/bin/env bash
# deploy.sh — the ONLY deploy path for Fiscal Receipts.
#
# THIS SCRIPT IS THE SOURCE OF TRUTH.  docs/superpowers/LAUNCH.md §7d points
# here; it does not restate the commands.  If you find yourself typing
# `vercel --prod` by hand, that is the bug this script exists to fix.
#
# WHY IT EXISTS (ROADMAP backlog #27).  The deploy drill used to be "rebuild,
# then `vercel --prod`", and the R2 sync was a separate thing someone had to
# remember.  Nobody remembered it, so the PDF binaries for every post-launch
# ingestion phase were missing from the CDN and every citation panel on the new
# pages silently fell back to "open official source".  It ran that way in
# production until the 2026-07-04 catch, and no gate noticed, because no gate
# could: the property is production CDN state.  Binding the two steps into one
# command is the fix, and the post-deploy check at the end is the alarm.
#
# ORDER IS DELIBERATE: assets FIRST, pages SECOND.  upload_r2.sh never deletes,
# so syncing early is safe; deploying pages before their assets exist opens a
# window in which live pages cite binaries that are not there yet.
#
# USAGE
#   ./scripts/launch/deploy.sh                # sync R2, deploy prod, verify live
#   ./scripts/launch/deploy.sh --dry-run      # print every step, change nothing
#   ./scripts/launch/deploy.sh --skip-r2      # pages-only redeploy (no new assets)
#   ./scripts/launch/deploy.sh --no-verify    # skip the post-deploy check (discouraged)
#
# WHICH CHECKOUT IT DEPLOYS.  The one it lives in.  REPO_ROOT and SITE_OUT are
# derived from this script's own path, never from $PWD, so
#   /path/to/checkout-A/scripts/launch/deploy.sh
# deploys checkout-A's site/out/ and checkout-A's data/site/, wherever it is
# invoked from.  Running another worktree's copy deploys THAT worktree's build.
#
# PROVENANCE GUARD (preflight, also enforced under --dry-run).  Refuses unless
#   (a) site/out/.build-meta.json git_head == `git rev-parse HEAD` of this
#       checkout — the build is of the commit this checkout is at;
#   (b) `git status --porcelain --untracked-files=no -- .` (run in REPO_ROOT)
#       is empty — no staged or unstaged change to a tracked file under this
#       project.  One exemption: site/public/llms.txt, a tracked file the
#       build itself rewrites, when it is byte-identical to site/out/llms.txt
#       (see below); and
#   (c) `git ls-files --others --exclude-standard` finds no untracked,
#       non-ignored file under the BUILD INPUTS — site/src, site/scripts,
#       site/public, src, dbt, data-seeds, migrations.  A new component that
#       a committed file imports but nobody `git add`ed is compiled into
#       site/out/ yet is not in HEAD, so HEAD could not rebuild what shipped.
#       The paths are refused whole (a stray test file under site/src counts
#       too): cheaper to commit it than to prove a build never read it.
#       Ignored files (data/, tmp/, site/out/) and untracked files outside
#       those paths are fine — data/research/ in particular, where
#       verify-phase5 writes its eval runs.
# All three are printed.  To deploy, commit (or discard) the changes, rebuild
# site/out/ at that commit, and re-run.
#
# WHAT IT CANNOT CHECK.  .build-meta.json records git_head only, not whether
# the tree was clean WHEN site/out/ was built, so a build made on a dirty tree
# that was cleaned (checkout, stash) before this guard runs still passes.  The
# OK line says exactly what was checked, not that site/out/ "is a build of
# HEAD".
#
# PREREQUISITES
#   - `site/out/` built and current, at this checkout's HEAD (see above):
#       cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build
#     Vercel does NOT build this site.  See the note on --archive/cwd below.
#   - rclone configured with an `r2` remote (see upload_r2.sh --help)
#   - `vercel` CLI logged in
#
# ENVIRONMENT
#   VERCEL_PROJECT_ID / VERCEL_ORG_ID  defaulted below; `site/out/` carries no
#                                      `.vercel/` link (each build wipes it),
#                                      so the IDs go in as env vars.
#   R2_BUCKET                          passed through to upload_r2.sh
#   ASSET_BASE_URL / SITE_URL          passed through to verify_live_assets.mjs
#
# EXIT CODES
#   0  deployed and verified
#   1  a step failed (nothing further runs)
#   2  preflight failed — nothing was uploaded or deployed

set -euo pipefail

# From the script's own location, not $PWD: this script deploys the checkout
# it lives in (see WHICH CHECKOUT IT DEPLOYS above).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SITE_OUT="${REPO_ROOT}/site/out"

# Vercel project identity.  These are project identifiers, not secrets, and
# they are already recorded in LAUNCH.md; override via env for another project.
VERCEL_PROJECT_ID="${VERCEL_PROJECT_ID:-prj_oen0seknELM3lK6UcZPS5252D7QD}"
VERCEL_ORG_ID="${VERCEL_ORG_ID:-team_b94lNMYEXzNevW7VmSNvdeYZ}"

DRY_RUN=0
SKIP_R2=0
VERIFY=1

for arg in "$@"; do
  case "$arg" in
    --dry-run)    DRY_RUN=1 ;;
    --skip-r2)    SKIP_R2=1 ;;
    --no-verify)  VERIFY=0 ;;
    --help|-h)    grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)
      echo "ERROR: unknown argument: $arg" >&2
      echo "USAGE: $0 [--dry-run] [--skip-r2] [--no-verify]" >&2
      exit 2
      ;;
  esac
done

step() {
  echo ""
  echo "═══════════════════════════════════════════════════════════════════"
  echo "  $*"
  echo "═══════════════════════════════════════════════════════════════════"
}

run() {
  echo "+ $*"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    "$@"
  fi
}

# ── Preflight ────────────────────────────────────────────────────────────────
step "0/3  preflight"

fail_preflight() { echo "ERROR: $*" >&2; exit 2; }

command -v vercel >/dev/null 2>&1 || fail_preflight "vercel CLI not found (npm i -g vercel)"
command -v node   >/dev/null 2>&1 || fail_preflight "node not found"

[[ -d "$SITE_OUT" ]] || fail_preflight \
  "site/out/ not found. Build first:
     cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build"

[[ -f "${SITE_OUT}/index.html" ]] || fail_preflight \
  "site/out/index.html missing — the export did not finish. Rebuild."

# The /fact/{id} permalink rewrite lives in site/out/vercel.json.  Deploying a
# directory without it produces a site that 404s every permalink, silently.
[[ -f "${SITE_OUT}/vercel.json" ]] || fail_preflight \
  "site/out/vercel.json missing — the /fact/ rewrite would silently die.
   Check site/scripts/prepare-assets.mjs and rebuild."

# ── Provenance guard: site/out/ is a build of THIS checkout's HEAD, clean ────
# Integration 2026-09-25 (review finding #18): the only written runbook pointed
# at another worktree's deploy.sh, which would have shipped a pre-merge build.
# The build carries its commit in .build-meta.json (write-build-meta.mjs,
# postbuild); refuse any mismatch rather than trust the operator's cwd.
command -v git >/dev/null 2>&1 || fail_preflight "git not found — cannot prove what site/out/ was built from"
BUILD_META="${SITE_OUT}/.build-meta.json"
[[ -f "$BUILD_META" ]] || fail_preflight \
  "site/out/.build-meta.json missing — cannot prove which commit site/out/ was
   built from.  Rebuild: cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build"
BUILD_HEAD="$(node -e '
  const m = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"));
  process.stdout.write(typeof m.git_head === "string" ? m.git_head : "");
' "$BUILD_META" 2>/dev/null)" || fail_preflight "site/out/.build-meta.json is not readable JSON — rebuild."
CHECKOUT_HEAD="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null)" || fail_preflight \
  "git rev-parse HEAD failed in ${REPO_ROOT} — not a git checkout?"
# ONE tracked file is a build OUTPUT: prepare-assets.mjs (prebuild) rewrites
# site/public/llms.txt from the exported data on every build (its counts move
# with every refresh — see its commit history), and next build copies it into
# site/out/.  Without this exemption every data-changing refresh, including the
# unattended `govbudget refresh` deploy stage, would be refused.  It is exempt
# ONLY when the working copy is byte-identical to site/out/llms.txt, i.e. the
# modification is exactly what this build wrote and shipped; any other change
# to it (or a deletion) still refuses.
LLMS_SRC="site/public/llms.txt"
EXCLUDE=()
LLMS_NOTE=""
if ! git -C "$REPO_ROOT" diff --quiet HEAD -- "$LLMS_SRC" 2>/dev/null \
   && cmp -s "${REPO_ROOT}/${LLMS_SRC}" "${SITE_OUT}/llms.txt"; then
  EXCLUDE=(":(exclude)${LLMS_SRC}")
  LLMS_NOTE="${LLMS_SRC} differs from HEAD but is byte-identical to site/out/llms.txt (the build wrote it)"
fi
TRACKED_CHANGES="$(git -C "$REPO_ROOT" status --porcelain --untracked-files=no -- . ${EXCLUDE[@]+"${EXCLUDE[@]}"})" \
  || fail_preflight "git status failed in ${REPO_ROOT}"
# (c) Untracked, non-ignored files under the paths a build reads.  data/research/
# IS an input (the exporter globs data/research/dossiers-raw/*.json, among
# others) except data/research/eval-runs/, where verify-phase5 writes its eval
# runs — outputs of the gates, not inputs to the build.  The rest of data/ is
# ignored exports and caches.
BUILD_INPUT_PATHS=(site/src site/scripts site/public src dbt data-seeds migrations data/research ":(exclude)data/research/eval-runs")
# --full-name: paths from the repository top, as `git status` prints them above.
UNTRACKED_INPUTS="$(git -C "$REPO_ROOT" ls-files --others --exclude-standard --full-name -- "${BUILD_INPUT_PATHS[@]}")" \
  || fail_preflight "git ls-files failed in ${REPO_ROOT}"

echo "  checkout:        ${REPO_ROOT}"
echo "  site/out built:  ${BUILD_HEAD:-<none>}   (site/out/.build-meta.json git_head)"
echo "  checkout HEAD:   ${CHECKOUT_HEAD}   (git rev-parse HEAD)"
if [[ -z "$TRACKED_CHANGES" ]]; then
  echo "  tracked changes: none   (git status --porcelain --untracked-files=no -- .)"
else
  echo "  tracked changes: $(printf '%s\n' "$TRACKED_CHANGES" | wc -l | tr -d ' ') path(s)   (git status --porcelain --untracked-files=no -- .)"
  printf '%s\n' "$TRACKED_CHANGES" | sed 's/^/                     /'
fi
if [[ -n "$LLMS_NOTE" ]]; then
  echo "  exempt:          ${LLMS_NOTE}"
fi
if [[ -z "$UNTRACKED_INPUTS" ]]; then
  echo "  untracked inputs: none   (git ls-files --others --exclude-standard -- ${BUILD_INPUT_PATHS[*]})"
else
  echo "  untracked inputs: $(printf '%s\n' "$UNTRACKED_INPUTS" | wc -l | tr -d ' ') path(s)   (git ls-files --others --exclude-standard -- ${BUILD_INPUT_PATHS[*]})"
  printf '%s\n' "$UNTRACKED_INPUTS" | sed 's/^/                     ?? /'
fi

GUARD_NOTE=""
if [[ "$DRY_RUN" -eq 1 ]]; then
  GUARD_NOTE="
   (--dry-run enforces this too: a real deploy would stop here.)"
fi
if [[ "$BUILD_HEAD" != "$CHECKOUT_HEAD" ]]; then
  fail_preflight "REFUSING TO DEPLOY: site/out/ was built from ${BUILD_HEAD:-<unknown>},
   but this checkout is at ${CHECKOUT_HEAD}.  Rebuild site/out/ at HEAD
   (cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build),
   or run the deploy.sh of the checkout that built it.${GUARD_NOTE}"
fi
if [[ -n "$TRACKED_CHANGES" ]]; then
  fail_preflight "REFUSING TO DEPLOY: tracked files under ${REPO_ROOT} are modified
   (listed above), so site/out/ may not be a build of HEAD.  Commit or discard
   them, rebuild, and re-run.${GUARD_NOTE}"
fi
if [[ -n "$UNTRACKED_INPUTS" ]]; then
  fail_preflight "REFUSING TO DEPLOY: untracked files sit under the build inputs
   (${BUILD_INPUT_PATHS[*]}; listed above).  The build or the
   export may have read them and HEAD does not contain them, so HEAD may not
   rebuild what would ship.  git add and commit them (or delete them, or
   ignore them if they are not inputs), rebuild, and re-run.${GUARD_NOTE}"
fi
echo "  provenance:      OK — git_head matches HEAD; no tracked changes; no untracked build inputs"
echo "                   (not checked: whether the tree was clean when site/out/ was built —"
echo "                   .build-meta.json records git_head only)"

if [[ "$SKIP_R2" -eq 0 ]]; then
  command -v rclone >/dev/null 2>&1 || fail_preflight \
    "rclone not found (brew install rclone). Pass --skip-r2 only if you are
     certain no asset changed since the last deploy."
  [[ -d "${REPO_ROOT}/data/site/pdfs" ]] || fail_preflight \
    "data/site/pdfs/ not found — run \`govbudget export-site\` first."
fi

FILE_COUNT="$(find "$SITE_OUT" -type f | wc -l | tr -d ' ')"
echo "  site/out/:       ${FILE_COUNT} files"
echo "  vercel project:  ${VERCEL_PROJECT_ID}"
if [[ "$SKIP_R2" -eq 1 ]]; then
  echo "  R2 sync:         SKIPPED (--skip-r2)"
else
  PDF_COUNT="$(find "${REPO_ROOT}/data/site/pdfs" -name '*.pdf' | wc -l | tr -d ' ')"
  echo "  R2 pdfs:         ${PDF_COUNT} binaries to sync"
fi
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo ""
  echo "  DRY RUN — the steps below are printed, not executed."
fi

# ── 1. R2 sync ───────────────────────────────────────────────────────────────
# Assets before pages: upload_r2.sh never deletes, so an early sync is safe,
# while deploying first would publish pages citing binaries that do not exist.
if [[ "$SKIP_R2" -eq 0 ]]; then
  step "1/3  sync assets to R2 (pdfs, data, workbooks, citations)"
  run "${REPO_ROOT}/scripts/launch/upload_r2.sh" --live
else
  step "1/3  R2 sync SKIPPED (--skip-r2)"
fi

# ── 2. Vercel ────────────────────────────────────────────────────────────────
# Both the working directory and the flag are load-bearing:
#
#   cwd = site/out/, never site/.  Vercel does not build this site in the
#   cloud; it serves the prebuilt static export.  From site/ it would run
#   `npm run build`, whose prebuild reads data/site/json/site_meta.json — a
#   path outside site/ that is never uploaded — and die with
#   "FATAL: data/site/json/site_meta.json not found."
#
#   --archive=tgz.  The default per-file upload sends a JSON manifest of every
#   file; at ~89.5k files that exceeds Vercel's 10 MB request limit and fails
#   with "Request body too large" BEFORE anything uploads.  Required since
#   2026-08-05 (the same deploy succeeded on the manifest path 15 h earlier,
#   so the limit tightened server-side).  Retrying, upgrading the CLI, and
#   .vercelignore all do not help.
step "2/3  deploy site/out/ to Vercel production"
echo "+ cd ${SITE_OUT} && VERCEL_PROJECT_ID=… VERCEL_ORG_ID=… vercel --prod --yes --archive=tgz"
if [[ "$DRY_RUN" -eq 0 ]]; then
  (
    cd "$SITE_OUT"
    VERCEL_PROJECT_ID="$VERCEL_PROJECT_ID" \
    VERCEL_ORG_ID="$VERCEL_ORG_ID" \
      vercel --prod --yes --archive=tgz
  )
fi

# ── 3. Post-deploy verification ──────────────────────────────────────────────
# The alarm for the defect this script exists to prevent.  A missing-from-CDN
# PDF now fails HERE instead of failing a reader six weeks later.
if [[ "$VERIFY" -eq 1 ]]; then
  step "3/3  verify live assets (the backlog-#27 alarm)"
  run node "${REPO_ROOT}/scripts/launch/verify_live_assets.mjs"
else
  step "3/3  post-deploy verification SKIPPED (--no-verify)"
  echo "  Run it manually: node scripts/launch/verify_live_assets.mjs"
fi

echo ""
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run complete — nothing was uploaded or deployed."
else
  echo "Deploy complete: assets synced, site/out/ live, live assets verified."
fi
