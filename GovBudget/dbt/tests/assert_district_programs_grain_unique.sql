-- Singular test: fct_district_programs must be unique on
-- (pop_state, pop_district, pe_bli, account) — the member grain Task 27 gave
-- the model (2026-09-19). Returns rows that violate uniqueness (test passes
-- when zero rows returned).
--
-- pop_state is part of the key, as it is in assert_district_totals_grain_unique
-- and assert_district_by_year_grain_unique: pop_district alone is not globally
-- unique, because a bare '90' MULTI-STATE/unknown-state code appears against
-- more than one raw pop_state label (see fct_district_totals.sql's header).
--
-- account is NULL for every code that names ONE program, and `group by` would
-- keep those rows in one group per key anyway — but the '(unresolved)'
-- sentinel is the same shape the sibling guard uses, and it keeps the
-- violating row legible when the NULL side is the duplicated one.
select pop_state, pop_district, pe_bli,
       coalesce(account, '(unresolved)') as account_key,
       count(*)
from {{ ref('fct_district_programs') }}
group by 1, 2, 3, 4
having count(*) > 1
