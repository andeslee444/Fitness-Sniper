/*
  ROADMAP #133 (2026-09-25) — WARN severity, by design: the count is the point.

  Returns one row per copy the fiscal-year move rule retired this build
  (audit_award_fy_moves). A retirement is correct and expected after a
  USAspending re-sync moves transactions between fiscal-year archives, so it
  must not fail the build — but it must never be silent either: dbt prints
  "WARN <n> warn_award_fy_moves_retired" and "Got <n> results" in the build
  log, which is the count the chain log carries. Zero on a lake the manual
  reconcile (scripts/reconcile_award_moves.py) already cleaned: PASS.
*/
{{ config(severity='warn') }}

select
    award_type,
    transaction_key,
    retired_fiscal_year,
    kept_fiscal_year,
    retired_last_modified_date,
    kept_last_modified_date,
    retired_file
from {{ ref('audit_award_fy_moves') }}
