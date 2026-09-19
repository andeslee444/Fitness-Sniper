-- fct_district_programs_by_year: high-confidence dollar grain per
-- (pop_state, pop_district, pe_bli, account, fiscal_year) — the fiscal_year
-- breakdown ROADMAP #6's third clause asked for, at the member grain Task 27
-- gave its all-years sibling.
--
-- Identical join, predicate and label-aggregation to fct_district_programs
-- (that model's header explains why `account` joined the grain on 2026-09-19
-- and why the two LABEL columns are min()-aggregated). The two models MUST
-- move in lockstep: assert_district_by_year_reconciles joins them on this
-- grain, so a column added to one and not the other turns every row of that
-- test into a vanished-row violation. fiscal_year is the AWARD ACTION year
-- from fct_award_transactions, never fct_budget_to_awards.fiscal_year (which
-- is the J-book edition the link came from).
--
-- NOT summable at district grain, for the same reason its all-years sibling is
-- not: an award matched to N program elements appears N times with the same
-- dollars. Use fct_district_totals_by_year for any district-level year figure.
--
-- Measured read-only against the shipped warehouse 2026-09-19: 3,290 rows,
-- 189 districts, 317 pe_bli, FY2017-FY2026; summing total_obligation over a
-- (district, pe_bli, account) key's years reproduces fct_district_programs to
-- under 1e-4 (float accumulation noise — pinned by tolerance in
-- assert_district_by_year_reconciles, never by a value).
select
    t.pop_state,
    t.pop_district,
    b.pe_bli,
    b.account,
    t.fiscal_year,
    min(b.program_title)                         as program_title,
    min(b.organization)                          as organization,
    count(distinct t.transaction_key)            as transaction_count,
    count(distinct t.award_id_piid)              as award_count,
    count(distinct t.recipient_uei)              as recipient_count,
    sum(coalesce(t.obligation, 0))               as total_obligation,
    sum(greatest(coalesce(t.obligation, 0), 0))  as positive_obligation
from {{ ref('fct_award_transactions') }} t
join (
    select distinct award_piid, pe_bli, account, program_title, organization
    from {{ ref('fct_budget_to_awards') }}
    where confidence = 'high'
) b on t.award_id_piid = b.award_piid
where t.pop_district is not null
group by 1, 2, 3, 4, 5
