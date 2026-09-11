-- fct_district_totals_by_year: the district HEADLINE grain, per fiscal year.
-- One row per (pop_state, pop_district, fiscal_year); dollars counted once per
-- award PER YEAR.
--
-- ROADMAP #6 (third clause, 2026-09-10). The entry asked dim_geography for a
-- fiscal_year/pe_bli breakdown. It does not get one: dim_geography is the
-- all-award place-of-performance headline and re-graining it would move every
-- figure that reads it (precedent #37/#51 — the fix belongs in a purpose-built
-- model, not a re-grained one). This is the award-distinct half; its
-- per-(district, program, year) sibling is fct_district_programs_by_year.
--
-- SUMMABILITY, stated because the two columns behave differently:
--   total_obligation  IS summable across years — the sum over a district's
--     rows equals fct_district_totals.total_obligation (agreement measured
--     2026-09-10 at under 1e-4 over 153 districts; the exact residue is
--     float64 accumulation noise at $67B and varies run to run, so it is
--     pinned by assert_district_by_year_reconciles at a 0.01 tolerance, never
--     at a value).
--   award_count is NOT. An award with transactions in two fiscal years is
--     counted in both, so the per-year counts OVERCOUNT when added (MO-01:
--     district award_count 24, by-year counts sum to 134). Never publish a
--     summed by-year award count.
--
-- positive_obligation is the GROSS figure — the same dollars before
-- deobligations are netted out (sum of positive transactions). 53 of the 924
-- district-year cells are net-negative; a page that renders only the net
-- number publishes an unexplained negative. The net figure stays the
-- headline ("publish the smaller true number"); the gross sits beside it.
with linked as (
    select
        t.pop_state,
        t.pop_district,
        t.fiscal_year,
        t.award_id_piid,
        sum(coalesce(t.obligation, 0))               as obligation,
        sum(greatest(coalesce(t.obligation, 0), 0))  as positive_obligation
    from {{ ref('fct_award_transactions') }} t
    join (
        select distinct award_piid
        from {{ ref('fct_budget_to_awards') }}
        where confidence = 'high'
    ) b on t.award_id_piid = b.award_piid
    where t.pop_district is not null
    group by 1, 2, 3, 4
)
select
    pop_state,
    pop_district,
    fiscal_year,
    count(distinct award_id_piid) as award_count,
    sum(obligation)               as total_obligation,
    sum(positive_obligation)      as positive_obligation
from linked
group by 1, 2, 3
