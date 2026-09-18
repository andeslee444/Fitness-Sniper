#!/usr/bin/env bash
# refresh.sh — the launchd entry point for `govbudget refresh` (ROADMAP #8).
#
# THIS SCRIPT INSTALLS NOTHING. It is the thing a launchd plist points AT.
# Loading the plist is the owner's action; see docs/superpowers/LAUNCH.md
# Step 11. An agent must never run `launchctl` or write into
# ~/Library/LaunchAgents/.
#
# USAGE
#   ./scripts/launch/refresh.sh                 # monthly cadence
#   ./scripts/launch/refresh.sh --quarterly     # + the LDA pull
#   ./scripts/launch/refresh.sh --until build   # any `govbudget refresh` flag
#
# --yes is always passed: a scheduled job has no TTY to confirm on. --from is
# never passed here, because --from skips the preflight stage.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# launchd hands a job a minimal PATH (/usr/bin:/bin:/usr/sbin:/sbin). uv, node,
# npm, rclone and vercel all live somewhere else, and a refresh that dies on
# "vercel: command not found" three hours in is the failure mode this line
# exists to prevent.
export PATH="/opt/homebrew/bin:/usr/local/bin:${HOME}/.local/bin:${PATH}"

# This runs INSIDE the job, so it is not what makes the plist's
# StandardOutPath/StandardErrorPath work: launchd opens those before exec and
# does not create missing parents. The Step 11 install snippet's own
# `mkdir -p "$PWD/logs"` is what saves the first scheduled run's output.
# Preflight also creates the directory (ruling R-20b-8), but only once the job
# is already running; this line covers a manual
# `./scripts/launch/refresh.sh` in a fresh clone.
mkdir -p "${REPO_ROOT}/logs"
echo "── govbudget refresh $(date -u +%Y-%m-%dT%H:%M:%SZ) ──────────────────"
exec uv run python -m govbudget refresh --yes "$@"
