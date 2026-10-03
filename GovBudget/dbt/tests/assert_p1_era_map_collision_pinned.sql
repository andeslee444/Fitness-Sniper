-- Every carried era key on a PB2026 collision code is pinned to ONE side of
-- the collision (families piece 1, spec §4.3, §4.5 and §7).
--
-- fct_program_decade_series splits a collision code's grain by account (10
-- codes) or organization ('20', '30', '500') exactly like fct_decade_series,
-- and for an era row it takes the seed's program_account / program_org, never
-- the era row's own values. So for every key whose decision carries points:
--   * on an account-collision code, program_account must be set — and, for
--     same_program, be an account PB2026 reports under that code (the page
--     the points join); a history_only pin only has to be set;
--   * on an organization-collision code, the same for program_org;
--   * on any other code, both pins must be blank (they would be ignored).
-- The two anchors below are fct_decade_series.sql's collision_pes /
-- org_collision_pes, re-derived from staging (this test checks the map
-- independently of the mart).
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
),
pb2026_accounts as (
    select distinct pe_bli, account from collision_slots
),
pb2026_orgs as (
    select distinct pe_bli, organization from org_collision_slots
),
carried as (
    select edition, era_key, line_item_code, decision, program_account, program_org
    from {{ ref('p1_era_line_map') }}
    where decision in ('same_program', 'history_only')
)

select
    'account-collision code without a usable account pin' as failure,
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
join collision_pes cp
  on cp.pe_bli = c.line_item_code
left join pb2026_accounts a
  on a.pe_bli = c.line_item_code
 and a.account = c.program_account
where c.program_account is null
   or (c.decision = 'same_program' and a.pe_bli is null)

union all

select
    'organization-collision code without a usable organization pin',
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
join org_collision_pes ocp
  on ocp.pe_bli = c.line_item_code
left join pb2026_orgs o
  on o.pe_bli = c.line_item_code
 and o.organization = c.program_org
where c.program_org is null
   or (c.decision = 'same_program' and o.pe_bli is null)

union all

select
    'pin on a code that is not a PB2026 collision code',
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
left join collision_pes cp
  on cp.pe_bli = c.line_item_code
left join org_collision_pes ocp
  on ocp.pe_bli = c.line_item_code
where cp.pe_bli is null
  and ocp.pe_bli is null
  and (c.program_account is not null or c.program_org is not null)
