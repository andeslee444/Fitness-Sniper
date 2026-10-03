-- A code that spans organizations within one edition is decided per
-- organization (families piece 1, spec §4.3 and §7: today '10', '15', '20',
-- '30', '500'). Two legs:
--
--   * one decision covers several organizations: a decision covers keys of
--     more than one organization in the same edition — a row left
--     `organization` blank for an organization-spanning code.
--   * two organizations would sum into one page: on a code that is NOT a
--     PB2026 collision code, fct_program_decade_series keeps neither account
--     nor organization in the grain, so every same_program key printing the
--     code in an edition sums into the code's ONE page. Keys of two
--     organizations there would put one organization's dollars on the
--     other's page, so at most one organization per (edition, code) may be
--     same_program; the others are history_only or excluded. Today this is
--     '10' (PB2018: TJS beside DPAA) and '15' (PB2021–PB2023: DISA beside
--     TJS Cyber). Collision codes are exempt: their grain splits by the
--     pinned account or organization (assert_p1_era_map_collision_pinned.sql).
--     The two anchors are fct_decade_series.sql's collision_pes /
--     org_collision_pes, re-derived from staging exactly as
--     assert_p1_era_map_collision_pinned.sql does.
with collision_slots as (
    select pe_bli, amount_type, account
    from {{ ref('stg_budget_lines') }}
    where fiscal_year = 2026
      and title is not null
      and pe_bli <> '9999999999'
    group by pe_bli, amount_type, account
),
collision_pes as (
    select distinct pe_bli
    from (
        select pe_bli
        from collision_slots
        group by pe_bli, amount_type
        having count(distinct account) > 1
    )
),
org_collision_slots as (
    select pe_bli, amount_type, organization
    from {{ ref('stg_budget_lines') }}
    where fiscal_year = 2026
      and title is not null
      and pe_bli <> '9999999999'
    group by pe_bli, amount_type, organization
),
org_collision_pes as (
    select distinct pe_bli
    from (
        select pe_bli
        from org_collision_slots
        group by pe_bli, amount_type
        having count(distinct organization) > 1
    )
)

select
    'one decision covers several organizations' as failure,
    decision_id as subject,
    edition,
    count(distinct organization) as organizations,
    string_agg(distinct organization, ',' order by organization) as organizations_seen
from {{ ref('p1_era_line_map') }}
where decision_id is not null
group by decision_id, edition
having count(distinct organization) > 1

union all

select
    'two organizations would sum into one page',
    m.line_item_code,
    m.edition,
    count(distinct m.organization),
    string_agg(distinct m.organization, ',' order by m.organization)
from {{ ref('p1_era_line_map') }} m
left join collision_pes cp
  on cp.pe_bli = m.line_item_code
left join org_collision_pes ocp
  on ocp.pe_bli = m.line_item_code
where m.decision = 'same_program'
  and cp.pe_bli is null
  and ocp.pe_bli is null
group by m.line_item_code, m.edition
having count(distinct m.organization) > 1
