-- No district total may exceed the sum of its DISTINCT awards.
-- fct_district_programs is per (district, pe_bli, account); one award matched
-- to N program elements produces N rows carrying the same dollars, so any sum
-- over that model double-counts. This asserts the headline model does not
-- (#51). The account joined that grain in Task 27 (2026-09-19) and can only
-- widen the fan-out, never narrow it: it splits a shared code's row in two
-- without changing which awards each side counts.
-- R-DEC-LINK-2026-10-21 R4: an award is the one a link NAMES
-- (link_award_keys), never every award sharing its PIID — the truth is
-- counted on the same awards the model counts.
with truth as (
    select t.pop_district, t.award_id_piid, sum(t.obligation) as obl
    from {{ ref('fct_award_transactions') }} t
    join (
        select distinct b.award_piid, k.award_unique_key
        from {{ ref('fct_budget_to_awards') }} b
        join {{ ref('link_award_keys') }} k
          on k.award_piid = b.award_piid
         and k.recipient_uei is not distinct from b.recipient_uei
         and k.named
        where b.confidence = 'high'
    ) b on t.award_id_piid = b.award_piid
       and t.award_unique_key is not distinct from b.award_unique_key
    where t.pop_district is not null
    group by 1, 2
),
distinct_by_district as (
    select pop_district, sum(obl) as distinct_obl from truth group by 1
)
select
    h.pop_district,
    h.total_obligation as published,
    d.distinct_obl     as distinct_awards,
    h.total_obligation - d.distinct_obl as overstatement
from {{ ref('fct_district_totals') }} h
join distinct_by_district d using (pop_district)
where h.total_obligation > d.distinct_obl + 0.01
