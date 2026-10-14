-- Every carried era key on a PB2026 collision code is pinned to ONE side of
-- the collision (families piece 1, spec §4.3, §4.5 and §7; plan binding
-- decision 5: the seed sets BOTH pins — ROADMAP #203, follow-ups Task 9).
--
-- fct_program_decade_series splits a collision code's grain by account (10
-- codes) or organization ('20', '30', '500') exactly like fct_decade_series,
-- and for an era row it takes the seed's program_account / program_org, never
-- the era row's own values. So for every key whose decision carries points:
--   * on an account- or organization-collision code, program_account AND
--     program_org must both be set — and, for same_program, name a line
--     PB2026 prints under that code (the page the points join; the same test
--     `era-map ratify` applies before a batch is written); a history_only
--     pair only has to be set;
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
pb2026_lines as (
    select distinct pe_bli, account, organization
    from {{ ref('stg_budget_lines') }}
    where fiscal_year = 2026
      and title is not null
      and pe_bli <> '9999999999'
),
carried as (
    select edition, era_key, line_item_code, decision, program_account, program_org
    from {{ ref('p1_era_line_map') }}
    where decision in ('same_program', 'history_only')
)

select
    'account-collision code without a usable pin pair' as failure,
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
join collision_pes cp
  on cp.pe_bli = c.line_item_code
left join pb2026_lines l
  on l.pe_bli = c.line_item_code
 and l.account = c.program_account
 and l.organization = c.program_org
where c.program_account is null
   or c.program_org is null
   or (c.decision = 'same_program' and l.pe_bli is null)

union all

select
    'organization-collision code without a usable pin pair',
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
join org_collision_pes ocp
  on ocp.pe_bli = c.line_item_code
left join pb2026_lines l
  on l.pe_bli = c.line_item_code
 and l.account = c.program_account
 and l.organization = c.program_org
where c.program_account is null
   or c.program_org is null
   or (c.decision = 'same_program' and l.pe_bli is null)

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
