-- Singular test: the by-year models must sum back to their all-years siblings,
-- to the cent. This is the property /district/{code}/ publishes — a year table
-- whose column adds up to the headline above it — and gate 9 leg f re-checks it
-- on the BUILT page. Pinning it here too means a mart-side regression fails in
-- `dbt build`, 35 minutes before the site gate would see it.
--
-- Tolerance 0.01 (one cent). The measured disagreement on 2026-09-10 was under
-- 1e-4 over 153 districts — float64 accumulation noise at $67B (TX-12), whose
-- exact magnitude changes between runs because DuckDB aggregates in parallel.
-- The tolerance is the contract; no run's residue is ever written down as one.
with totals_check as (
    select
        'fct_district_totals_by_year' as model,
        h.pop_state, h.pop_district, cast(null as varchar) as pe_bli,
        h.total_obligation as published,
        y.summed,
        h.total_obligation - y.summed as diff
    from {{ ref('fct_district_totals') }} h
    join (
        select pop_state, pop_district, sum(total_obligation) as summed
        from {{ ref('fct_district_totals_by_year') }}
        group by 1, 2
    ) y using (pop_state, pop_district)
),
programs_check as (
    select
        'fct_district_programs_by_year' as model,
        p.pop_state, p.pop_district, p.pe_bli,
        p.total_obligation as published,
        s.summed,
        p.total_obligation - s.summed as diff
    from {{ ref('fct_district_programs') }} p
    join (
        select pop_state, pop_district, pe_bli, sum(total_obligation) as summed
        from {{ ref('fct_district_programs_by_year') }}
        group by 1, 2, 3
    ) s using (pop_state, pop_district, pe_bli)
)
select * from totals_check where abs(diff) > 0.01
union all
select * from programs_check where abs(diff) > 0.01
