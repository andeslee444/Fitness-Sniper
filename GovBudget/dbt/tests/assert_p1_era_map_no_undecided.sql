/*
  Families piece 1 (spec §7, §8 V3) — ERROR severity from the commit that
  closed S2 (plan Task 15). It replaces warn_p1_era_map_undecided.sql, which
  warned while the owner's review batches R-DEC-ERA-B1..B<n> were open.

  One row per era key that no owner decision covers (decision =
  'undecided'), or whose decision went stale (keys_sha_ok = false: the keys
  or titles it covers changed after review). Every PB2017-PB2023 P-1 era key
  now carries a dated decision in dbt/seeds/p1_era_code_decisions.csv, so a
  key that loses its decision (a new edition row, a seed row removed or
  re-ranged, a retitled key) fails the build instead of printing a warning.
  tests/test_p1_era_line_map_sql.py::test_no_undecided_lists_undecided_and_stale_keys
  proves the predicate returns both kinds.
*/
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
