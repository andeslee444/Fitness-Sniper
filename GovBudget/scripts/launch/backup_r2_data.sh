#!/usr/bin/env bash
# backup_r2_data.sh — copy the LIVE fixed-name R2 prefixes aside before a
# deploy overwrites them (ROADMAP backlog #177's own fix; ruling
# R-DEC-DEPLOYSAFE, the decisions wave's final review, findings #12 and #15).
#
# WHY.  upload_r2.sh runs `rclone copy --checksum`, which replaces a changed
# object in place.  pdfs/ and workbooks/ are content-addressed
# (<sha256>.<ext>), so nothing there is ever lost; data/*.parquet and
# citations/citations.parquet have fixed names, so the previous deploy's
# objects are gone the moment the sync runs.  A Vercel rollback would then
# pair the old pages with the new data for good, and no local copy of the
# live objects exists (checked 2026-09-26: the rollback directories under
# data/refresh/ hold older exports, not what R2 serves).  This script copies
# those two prefixes, server-side, to
#   <remote>:<bucket>/rollback/<tag>/data/
#   <remote>:<bucket>/rollback/<tag>/citations/
# and then checks each copy against the live prefix.
#
# deploy.sh runs it (R-DEC-DEPLOYSAFE-b): step 1 calls
#   backup_r2_data.sh --live --tag=<tag>
# before upload_r2.sh, stops the deploy (nothing uploaded, nothing deployed)
# if it fails or refuses, and prints the tag; `deploy.sh --dry-run` runs its
# dry run (no --live).  Record the printed tag in the deploy's ledger entry.
# Run it by hand only to copy the live prefixes outside a deploy:
#   ./scripts/launch/backup_r2_data.sh           # dry run: what would be copied
#   ./scripts/launch/backup_r2_data.sh --live    # copy, then check
#
# THE EXACT COMMANDS, in order (remote r2, bucket govbudget-assets; a dry
# run adds --dry-run to each copy and runs no check):
#   rclone lsf -R --files-only r2:govbudget-assets/data/            # must list objects
#   rclone lsf -R --files-only r2:govbudget-assets/citations/       # must list objects
#   rclone lsf -R --files-only r2:govbudget-assets/rollback/<tag>/  # must be empty
#   rclone copy --checksum --immutable r2:govbudget-assets/data/ r2:govbudget-assets/rollback/<tag>/data/
#   rclone check --one-way --checksum r2:govbudget-assets/data/ r2:govbudget-assets/rollback/<tag>/data/
#   rclone copy --checksum --immutable r2:govbudget-assets/citations/ r2:govbudget-assets/rollback/<tag>/citations/
#   rclone check --one-way --checksum r2:govbudget-assets/citations/ r2:govbudget-assets/rollback/<tag>/citations/
# --immutable makes rclone fail rather than overwrite a destination object
# with different content, so a second run can never replace a rollback copy
# with the objects a deploy has since uploaded; the empty-destination check
# refuses before anything is copied.
#
# RESTORE (after rolling Vercel back to the deployment that read them):
#   rclone copy --checksum r2:govbudget-assets/rollback/<tag>/data/ r2:govbudget-assets/data/
#   rclone copy --checksum r2:govbudget-assets/rollback/<tag>/citations/ r2:govbudget-assets/citations/
# Objects a later export added under data/ stay (copy never deletes); the
# pages being rolled back to never read them.
#
# NOTE.  The bucket is public through its asset domain, so the copy is
# readable at /rollback/<tag>/…; it holds only what was already public.
#
# OPTIONS
#   --live        perform the copy (default: a dry run — rclone --dry-run)
#   --tag=<tag>   the rollback/<tag>/ name (default: UTC now, e.g.
#                 2026-09-26T231500Z); letters, digits, '.', '_' and '-' only
#
# ENVIRONMENT
#   RCLONE_REMOTE (default r2) and R2_BUCKET (default govbudget-assets) — the
#   same names and defaults as upload_r2.sh.
#
# EXIT CODES
#   0  copied and checked (or the dry run completed)
#   1  rclone missing, a bad argument, an empty live prefix, a destination
#      that already holds objects, or an rclone error

set -euo pipefail

RCLONE_REMOTE="${RCLONE_REMOTE:-r2}"
R2_BUCKET="${R2_BUCKET:-govbudget-assets}"
PREFIXES=("data" "citations")

LIVE=0
TAG="$(date -u +%Y-%m-%dT%H%M%SZ)"
for arg in "$@"; do
  case "$arg" in
    --live) LIVE=1 ;;
    --tag=*) TAG="${arg#--tag=}" ;;
    --help|-h) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)
      echo "ERROR: unknown argument: $arg" >&2
      echo "USAGE: $0 [--live] [--tag=<tag>]" >&2
      exit 1
      ;;
  esac
done

if [[ ! "$TAG" =~ ^[A-Za-z0-9._-]+$ || "$TAG" == "." || "$TAG" == ".." ]]; then
  echo "ERROR: --tag must be letters, digits, '.', '_' or '-' (got '${TAG}')" >&2
  exit 1
fi

if ! command -v rclone &>/dev/null; then
  echo "ERROR: rclone not found (brew install rclone; see upload_r2.sh --help)." >&2
  exit 1
fi

BUCKET_ROOT="${RCLONE_REMOTE}:${R2_BUCKET}"
DEST_ROOT="${BUCKET_ROOT}/rollback/${TAG}"

DRY_FLAG=()
if [[ "$LIVE" -eq 0 ]]; then
  DRY_FLAG=(--dry-run)
  echo "═══════════════════════════════════════════════════════════════════"
  echo "  DRY RUN — nothing will be copied.  Pass --live to copy."
  echo "═══════════════════════════════════════════════════════════════════"
fi
echo ""
echo "Live:     ${BUCKET_ROOT}/{$(IFS=,; echo "${PREFIXES[*]}")}/"
echo "Aside:    ${DEST_ROOT}/"
echo "Tag:      ${TAG}"
echo ""

# Lists a prefix's objects (stdout only: rclone's notices on stderr are not
# objects).  A prefix that does not exist yet lists as empty (rclone reports
# "directory not found"); any other error fails closed.
list_objects() {
  local out err errf rc=0
  errf="$(mktemp)"
  out="$(rclone lsf -R --files-only "$1" 2>"$errf")" || rc=$?
  err="$(cat "$errf")"
  rm -f "$errf"
  if [[ "$rc" -ne 0 ]]; then
    if [[ "${err}${out}" == *"directory not found"* ]]; then
      return 0
    fi
    echo "ERROR: rclone lsf $1 failed (exit ${rc}): ${err}${out}" >&2
    exit 1
  fi
  printf '%s' "$out"
}

# 1. Every live prefix holds objects: copying an empty (or wrong) bucket
#    would leave a rollback copy that restores nothing.
declare -a COUNTS=()
for prefix in "${PREFIXES[@]}"; do
  listing="$(list_objects "${BUCKET_ROOT}/${prefix}/")"
  n="$(printf '%s' "$listing" | grep -c . || true)"
  if [[ "$n" -eq 0 ]]; then
    echo "ERROR: ${BUCKET_ROOT}/${prefix}/ lists no objects — wrong remote or bucket?" >&2
    exit 1
  fi
  COUNTS+=("$n")
done

# 2. The destination is empty: a rollback copy is never overwritten.
existing="$(list_objects "${DEST_ROOT}/")"
if [[ -n "$existing" ]]; then
  echo "ERROR: ${DEST_ROOT}/ already holds objects — pick another --tag;" >&2
  echo "       a rollback copy is never overwritten." >&2
  exit 1
fi

# 3. Copy each prefix aside, server-side; then check the copy (live runs).
for i in "${!PREFIXES[@]}"; do
  prefix="${PREFIXES[$i]}"
  src="${BUCKET_ROOT}/${prefix}/"
  dst="${DEST_ROOT}/${prefix}/"
  echo "  COPY  ${src} → ${dst}  (${COUNTS[$i]} object(s))"
  rclone copy ${DRY_FLAG[@]+"${DRY_FLAG[@]}"} --checksum --immutable "$src" "$dst"
  if [[ "$LIVE" -eq 1 ]]; then
    echo "  CHECK ${dst} holds every object of ${src}"
    rclone check --one-way --checksum "$src" "$dst"
  fi
done

echo ""
if [[ "$LIVE" -eq 0 ]]; then
  echo "Dry run complete.  Re-run with --live (and the same --tag=${TAG} if you want this name)."
else
  echo "Rollback copy complete and checked: ${DEST_ROOT}/"
fi
echo ""
echo "To restore after a Vercel rollback:"
for prefix in "${PREFIXES[@]}"; do
  echo "  rclone copy --checksum ${DEST_ROOT}/${prefix}/ ${BUCKET_ROOT}/${prefix}/"
done
