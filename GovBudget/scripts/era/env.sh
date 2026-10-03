# Families piece 1 (era procurement history): the shell environment every task
# in the plan starts from. SOURCE it (bash or zsh) from the worktree's
# GovBudget/ directory:
#
#     source scripts/era/env.sh
#
# Points reads at the LIVE lake and the live Postgres (the plan writes to them
# only in its named tasks) and points tests at the throwaway cluster on
# 127.0.0.1:55432 — never at the real server. For a pinned proof snapshot,
# source <snapshot>/env.sh [RUN_DIR] instead (written by `govbudget proof
# snapshot`). config.py builds every lake path from GOVBUDGET_DATA and ignores
# GOVBUDGET_DUCKDB; dbt and `govbudget build` read GOVBUDGET_DUCKDB, so both
# are set, consistently.
_era_common="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
if [ -z "$_era_common" ]; then
  echo "scripts/era/env.sh: source me from inside the GovBudget checkout" >&2
  return 1
fi
_era_main="$(dirname "$_era_common")/GovBudget"   # the main checkout owns the lake
export GOVBUDGET_DATA="$_era_main/data"
export GOVBUDGET_DUCKDB="$GOVBUDGET_DATA/duckdb/govbudget.duckdb"
export GOVBUDGET_PG_DSN="postgresql://localhost/govbudget"
export GOVBUDGET_TEST_PG_DSN="postgresql://127.0.0.1:55432/postgres"
export GOVBUDGET_PG_BIN="${GOVBUDGET_PG_BIN:-/opt/homebrew/opt/postgresql@17/bin}"
export GOVBUDGET_PROOFS="$_era_main/.proofs"
unset _era_common _era_main
