-- Singular test: both by-year district models must be unique on their declared
-- grain. Returns rows that violate it (test passes when zero rows returned).
-- ROADMAP #6. The pair (pop_state, pop_district) is the grain, not pop_district
-- alone — see fct_district_totals.sql's header for the bare-'90' case.
--
-- Task 27 (2026-09-19): the programs arm gained `account`, in lockstep with
-- its all-years sibling (assert_district_programs_grain_unique). The totals
-- arm has no program element and so no account; it pads both columns with
-- NULL so the two arms union.
select 'fct_district_totals_by_year' as model,
       pop_state, pop_district, cast(null as varchar) as pe_bli,
       cast(null as varchar) as account_key, fiscal_year,
       count(*) as n
from {{ ref('fct_district_totals_by_year') }}
group by 1, 2, 3, 4, 5, 6
having count(*) > 1
union all
select 'fct_district_programs_by_year' as model,
       pop_state, pop_district, pe_bli,
       coalesce(account, '(unresolved)') as account_key, fiscal_year,
       count(*) as n
from {{ ref('fct_district_programs_by_year') }}
group by 1, 2, 3, 4, 5, 6
having count(*) > 1
