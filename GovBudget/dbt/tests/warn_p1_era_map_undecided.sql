/*
  Families piece 1 (spec §7) — WARN severity while the S2 review batches are
  open, by design: the count is the point.

  One row per era key that no owner decision covers yet (decision =
  'undecided'), or whose decision went stale (keys_sha_ok = false: the keys
  or titles it covers changed after review). Neither kind ever reaches
  fct_program_decade_series — an undecided key carries no program_key, and
  a stale one is re-reviewed — but they must never be silent: dbt prints
  "WARN <n> warn_p1_era_map_undecided" and "Got <n> results" in the build
  log. Task 15's closing commit deletes this file and adds
  assert_p1_era_map_no_undecided.sql with the same predicate at error
  severity; verify-era-map leg b is strict from S4.
*/
{{ config(severity='warn') }}

select
    edition,
    era_key,
    line_item_code,
    account,
    organization,
    filed_title,
    decision,
    decision_id,
    keys_sha_ok
from {{ ref('p1_era_line_map') }}
where decision = 'undecided'
   or keys_sha_ok = false
