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
--
-- FULL OUTER, not inner (rider to ROADMAP #6, 2026-09-11): an inner join sees
-- only districts present on BOTH sides, so a district that vanished from either
-- model — the failure mode a by-year table most plausibly suffers — would be
-- invisible to it, and its NULL diff would additionally be filtered away by
-- `abs(NULL) > 0.01`. Coalescing both sides to 0 turns a vanished district into
-- a violating row. Keys are compared with IS NOT DISTINCT FROM so a NULL
-- pop_state matches itself rather than splitting one district into two rows.
--
-- Task 27 (2026-09-19): the programs arm joins on `account` as well, because
-- both district-program models now carry it in their grain. IS NOT DISTINCT
-- FROM is load-bearing there, not a nicety: account is NULL for every code
-- that names one program (597 of the 608 all-years rows, measured read-only
-- 2026-09-19), so an equality join would drop almost the whole model out of
-- this check and then report every dropped row as a vanished one.
--
-- WHAT THE FIXTURE TEST DOES NOT COVER: tests/test_dbt_build.py builds a
-- one-district fixture lake, so it exercises the agreement arm of this test but
-- never the vanished-district arm — nothing in that fixture can drop a district
-- from one model and not the other. The vanished arm is guarded by this SQL
-- running in every real `dbt build`, not by a Python test.
with totals_check as (
    select
        'fct_district_totals_by_year' as model,
        coalesce(h.pop_state, y.pop_state)        as pop_state,
        coalesce(h.pop_district, y.pop_district)  as pop_district,
        cast(null as varchar)                     as pe_bli,
        cast(null as varchar)                     as account,
        coalesce(h.total_obligation, 0)           as published,
        coalesce(y.summed, 0)                     as summed,
        coalesce(h.total_obligation, 0) - coalesce(y.summed, 0) as diff
    from {{ ref('fct_district_totals') }} h
    full outer join (
        select pop_state, pop_district, sum(total_obligation) as summed
        from {{ ref('fct_district_totals_by_year') }}
        group by 1, 2
    ) y
      on h.pop_state is not distinct from y.pop_state
     and h.pop_district is not distinct from y.pop_district
),
programs_check as (
    select
        'fct_district_programs_by_year' as model,
        coalesce(p.pop_state, s.pop_state)        as pop_state,
        coalesce(p.pop_district, s.pop_district)  as pop_district,
        coalesce(p.pe_bli, s.pe_bli)              as pe_bli,
        coalesce(p.account, s.account)            as account,
        coalesce(p.total_obligation, 0)           as published,
        coalesce(s.summed, 0)                     as summed,
        coalesce(p.total_obligation, 0) - coalesce(s.summed, 0) as diff
    from {{ ref('fct_district_programs') }} p
    full outer join (
        select pop_state, pop_district, pe_bli, account,
               sum(total_obligation) as summed
        from {{ ref('fct_district_programs_by_year') }}
        group by 1, 2, 3, 4
    ) s
      on p.pop_state is not distinct from s.pop_state
     and p.pop_district is not distinct from s.pop_district
     and p.pe_bli is not distinct from s.pe_bli
     and p.account is not distinct from s.account
)
select * from totals_check where abs(diff) > 0.01
union all
select * from programs_check where abs(diff) > 0.01
