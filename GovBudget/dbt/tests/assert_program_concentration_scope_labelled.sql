-- ROADMAP #130 (owner-delegated 2026-09-25): every fct_program_concentration
-- row states its scope, and the label agrees with itself — 'code' exactly when
-- two or more programs share the budget-line code, member counts present and
-- in range. One pass over the view (each test on it re-evaluates the pooled
-- award join, ~2 minutes on the 2026-09-25 lake), instead of four not_null
-- tests and an accepted_values test. Returns the offending rows.
select
    pe_bli,
    scope,
    member_programs,
    member_keys_with_links,
    links_outside_member_keys
from {{ ref('fct_program_concentration') }}
where scope is null
   or scope not in ('program', 'code')
   or member_programs is null
   or member_keys_with_links is null
   or links_outside_member_keys is null
   or (scope = 'code') <> (member_programs > 1)
   or member_keys_with_links > member_programs
   or member_keys_with_links < 0
   or links_outside_member_keys < 0
