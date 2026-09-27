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
# THE ROLLBACK COPY COMES FIRST (ROADMAP #177; rulings R-DEC-DEPLOYSAFE and
# R-DEC-DEPLOYSAFE-b).  "Never deletes" is not "never overwrites": the
# fixed-name objects under data/ and citations/ are replaced in place, so the
# previous deploy's copies are gone the moment the sync runs, and a Vercel
# rollback would pair the old pages with the new data.  So step 1 runs
#   backup_r2_data.sh --live --tag=<tag>
# BEFORE upload_r2.sh: it copies the live data/ and citations/ server-side to
# rollback/<tag>/ in the same bucket, checks each copy, and prints the restore
# commands.  If it fails or refuses, this script stops with nothing uploaded
# and nothing deployed.  The tag (UTC time, e.g. 2026-09-27T011500Z) is
# printed in the preflight summary and after the copy; record it in the
# deploy's ledger entry.  If a later step fails, the tag is printed again: a
# re-run makes a NEW copy of whatever R2 serves then, which after this run's
# R2 step is this run's upload, so the first run's tag is the one that holds
# the previous production's objects.  Every run that makes the copy leaves
# one rollback/<tag>/ in the bucket (--skip-r2 makes none); nothing prunes them.
#
# USAGE
#   ./scripts/launch/deploy.sh                # copy live R2 data aside, sync R2,
#                                             # deploy prod, verify live
#   ./scripts/launch/deploy.sh --dry-run      # print every step, change nothing;
#                                             # runs backup_r2_data.sh's own dry
#                                             # run (reads the bucket's listings,
#                                             # copies nothing)
#   ./scripts/launch/deploy.sh --skip-r2      # pages-only redeploy (no new assets;
#                                             # no rollback copy: nothing in R2
#                                             # is overwritten)
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
#   - scripts/launch/backup_r2_data.sh present (unless --skip-r2)
#   - `vercel` CLI logged in
#
# ENVIRONMENT
#   VERCEL_PROJECT_ID / VERCEL_ORG_ID  defaulted below; `site/out/` carries no
#                                      `.vercel/` link (each build wipes it),
#                                      so the IDs go in as env vars.
#   R2_BUCKET / RCLONE_REMOTE          passed through to backup_r2_data.sh and
#                                      upload_r2.sh (same defaults, govbudget-assets
#                                      and r2), so the copy is of the bucket the
#                                      upload writes
#   ASSET_BASE_URL / SITE_URL          passed through to verify_live_assets.mjs
#
# EXIT CODES
#   0  deployed and verified
#   1  a step failed (nothing further runs); a failed or refused rollback
#      copy stops the run before anything is uploaded or deployed
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

# The rollback copy (step 1a).  backup_r2_data.sh reads RCLONE_REMOTE and
# R2_BUCKET with these same defaults (as does upload_r2.sh); they are
# resolved here only to PRINT where the copy goes.  The tag is fixed once per
# run, so the line printed in preflight names the copy the step makes.
BACKUP_SH="${REPO_ROOT}/scripts/launch/backup_r2_data.sh"
ROLLBACK_TAG="$(date -u +%Y-%m-%dT%H%M%SZ)"
ROLLBACK_DEST="${RCLONE_REMOTE:-r2}:${R2_BUCKET:-govbudget-assets}/rollback/${ROLLBACK_TAG}"
BACKUP_DONE=0

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

# A step that fails AFTER the rollback copy names the copy again: a re-run
# copies whatever R2 serves then — this run's upload, if its R2 step ran — so
# this run's tag is the one that holds the previous production's objects.
on_exit() {
  local rc=$?
  if [[ "$rc" -ne 0 && "$BACKUP_DONE" -eq 1 ]]; then
    {
      echo ""
      echo "NOTE: the deploy stopped (exit ${rc}) after its rollback copy was made."
      echo "  ${ROLLBACK_DEST}/ holds what R2 served before this run (data/, citations/)."
      echo "  Record the rollback tag ${ROLLBACK_TAG}.  A re-run copies what R2 serves"
      echo "  THEN under a new tag; once this run's R2 step has run, that is this run's"
      echo "  upload, not the previous production.  Restore commands: printed above by"
      echo "  backup_r2_data.sh (rclone copy --checksum ${ROLLBACK_DEST}/<prefix>/ …)."
    } >&2
  fi
}
trap on_exit EXIT

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
  # R-DEC-DEPLOYSAFE-b: the rollback copy cannot be skipped silently.
  [[ -f "$BACKUP_SH" ]] || fail_preflight \
    "scripts/launch/backup_r2_data.sh not found — without it the live data/ and
     citations/ objects would be overwritten with no rollback copy (ROADMAP #177).
     Restore the script; --skip-r2 is the only deploy that needs no copy."
fi

FILE_COUNT="$(find "$SITE_OUT" -type f | wc -l | tr -d ' ')"
echo "  site/out/:       ${FILE_COUNT} files"
echo "  vercel project:  ${VERCEL_PROJECT_ID}"
if [[ "$SKIP_R2" -eq 1 ]]; then
  echo "  R2 sync:         SKIPPED (--skip-r2)"
  echo "  rollback copy:   SKIPPED (--skip-r2: no R2 object is overwritten)"
else
  PDF_COUNT="$(find "${REPO_ROOT}/data/site/pdfs" -name '*.pdf' | wc -l | tr -d ' ')"
  echo "  R2 pdfs:         ${PDF_COUNT} binaries to sync"
  echo "  rollback tag:    ${ROLLBACK_TAG}   (live data/ and citations/ → ${ROLLBACK_DEST}/)"
fi
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo ""
  echo "  DRY RUN — the steps below are printed, not executed, except"
  echo "  backup_r2_data.sh's own dry run (it lists the bucket and copies nothing)."
fi

# ── 1. R2: (a) rollback copy, then (b) sync ──────────────────────────────────
# (a) R-DEC-DEPLOYSAFE-b.  The fixed-name objects under data/ and citations/
# are overwritten in place by (b), so the live ones are copied aside FIRST, and
# a failed or refused copy stops the deploy before anything is uploaded.  A
# dry run runs the backup's own dry run (no --live): it lists the live
# prefixes and the destination and runs `rclone copy --dry-run`, so it shows
# what would be copied and stops wherever a real run would, writing nothing.
# (b) Assets before pages: upload_r2.sh never deletes, so an early sync is
# safe, while deploying first would publish pages citing binaries that do not
# exist.
if [[ "$SKIP_R2" -eq 0 ]]; then
  step "1/3  R2: (a) copy the live data/ + citations/ aside, (b) sync assets"
  echo "  (a) rollback copy → ${ROLLBACK_DEST}/"
  BACKUP_ARGS=("--tag=${ROLLBACK_TAG}")
  if [[ "$DRY_RUN" -eq 0 ]]; then
    BACKUP_ARGS=(--live "${BACKUP_ARGS[@]}")
    echo "+ ${BACKUP_SH} ${BACKUP_ARGS[*]}"
  else
    echo "+ ${BACKUP_SH} ${BACKUP_ARGS[*]}   (its dry run; a real deploy runs backup_r2_data.sh --live --tag=<its own tag>)"
  fi
  if ! bash "$BACKUP_SH" "${BACKUP_ARGS[@]}"; then
    DRY_NOTE=""
    if [[ "$DRY_RUN" -eq 1 ]]; then
      DRY_NOTE="
   (--dry-run ran the backup's own dry run: a real deploy would stop here.)"
    fi
    echo "ERROR: REFUSING TO CONTINUE: the rollback copy of the live data/ and citations/
   (${ROLLBACK_DEST}/, tag ${ROLLBACK_TAG}) failed or was refused — see
   backup_r2_data.sh's message above.  Without it the upload would overwrite
   those objects with no copy (ROADMAP #177).  Nothing was uploaded or deployed.
   Fix the cause and re-run (a re-run picks a new tag).${DRY_NOTE}" >&2
    exit 1
  fi
  if [[ "$DRY_RUN" -eq 0 ]]; then
    BACKUP_DONE=1
    echo "  Rollback copy made and checked: ${ROLLBACK_DEST}/"
    echo "  Record the rollback tag ${ROLLBACK_TAG} in the deploy's ledger entry."
  fi
  echo "  (b) sync pdfs, data, workbooks, citations"
  run "${REPO_ROOT}/scripts/launch/upload_r2.sh" --live
else
  step "1/3  R2 sync SKIPPED (--skip-r2); rollback copy SKIPPED (--skip-r2: nothing is overwritten)"
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
  echo "Dry run complete — nothing was copied, uploaded or deployed."
else
  if [[ "$SKIP_R2" -eq 0 ]]; then
    DONE_R2="live data/ + citations/ copied to ${ROLLBACK_DEST}/ (rollback tag ${ROLLBACK_TAG}), assets synced"
  else
    DONE_R2="R2 sync and rollback copy skipped (--skip-r2)"
  fi
  if [[ "$VERIFY" -eq 1 ]]; then
    DONE_CHECK="live assets verified"
  else
    DONE_CHECK="live check SKIPPED (--no-verify)"
  fi
  echo "Deploy complete: ${DONE_R2}, site/out/ live, ${DONE_CHECK}."
fi
