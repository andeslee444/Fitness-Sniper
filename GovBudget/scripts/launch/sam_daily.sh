#!/usr/bin/env bash
# sam_daily.sh — the launchd entry point for `govbudget sam daily` (ROADMAP #10).
#
# THIS SCRIPT INSTALLS NOTHING. It is the thing a launchd plist points AT.
# Loading the plist is the owner's action; see docs/superpowers/LAUNCH.md
# Step 11b. An agent must never run `launchctl` or write into
# ~/Library/LaunchAgents/.
#
# launchd runs this every hour. Most ticks decide there is nothing to do and
# exit without opening the DuckDB lake; about one a day spends the SAM key's
# quota (src/govbudget/sam_daily.py says how it decides). Any flag is forwarded,
# e.g. `./scripts/launch/sam_daily.sh --check` to see what a tick would do.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# launchd hands a job a minimal PATH (/usr/bin:/bin:/usr/sbin:/sbin); uv lives
# elsewhere (refresh.sh carries the same line for the same reason).
export PATH="/opt/homebrew/bin:/usr/local/bin:${HOME}/.local/bin:${PATH}"

# Covers a hand run in a fresh clone. It cannot save a SCHEDULED run's output:
# launchd opens StandardOutPath before exec, which is why the Step 11b install
# snippet makes logs/ itself.
mkdir -p "${REPO_ROOT}/logs"

# --no-sync: an hourly job must never re-resolve or rewrite the shared .venv
# under a session that is using it. After a dependency change, `uv sync` by
# hand; until then the tick fails loudly (exit 1, and in the log).
exec uv run --no-sync python -m govbudget sam daily --notify "$@"
