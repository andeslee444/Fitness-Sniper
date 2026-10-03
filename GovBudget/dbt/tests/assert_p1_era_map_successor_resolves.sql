-- Every stated successor resolves (families piece 1, spec §5.4): a seed row
-- that records successor_code must also record successor_account and
-- successor_evidence, and the successor must be a P-1 budget line code
-- printed in PB2024–PB2026 under that account. The resolution leg runs only
-- when the lake registers the three modern P-1 workbooks
-- (fy2024..fy2026/dod/p1_display.xlsx — the real corpus); the shape leg
-- always runs. Known case: JLTV, 5600D15603 (2035A) -> 5731D15610 (2035A),
-- printed in PB2024, PB2025 and PB2026.
with registered as (
    select count(distinct rel_path) as n
    from {{ source('lake', 'jbook_documents') }}
    where rel_path in (
        'fy2024/dod/p1_display.xlsx', 'fy2025/dod/p1_display.xlsx',
        'fy2026/dod/p1_display.xlsx'
    )
),
modern as (
    select distinct pe_bli, account
    from {{ ref('stg_budget_lines') }}
    where exhibit = 'P-1'
      and fiscal_year between 2024 and 2026
),
successors as (
    select
        decision_id,
        nullif(trim(coalesce(successor_code, '')), '') as successor_code,
        nullif(trim(coalesce(successor_account, '')), '') as successor_account,
        nullif(trim(coalesce(successor_evidence, '')), '') as successor_evidence
    from {{ ref('p1_era_code_decisions') }}
)

select
    'successor recorded without its account or evidence' as failure,
    s.decision_id, s.successor_code, s.successor_account
from successors s
where (s.successor_code is not null
       and (s.successor_account is null or s.successor_evidence is null))
   or (s.successor_code is null
       and (s.successor_account is not null or s.successor_evidence is not null))

union all

select
    'successor absent from PB2024-PB2026 under its account',
    s.decision_id, s.successor_code, s.successor_account
from successors s
left join modern m
  on m.pe_bli = s.successor_code
 and m.account = s.successor_account
where s.successor_code is not null
  and s.successor_account is not null
  and m.pe_bli is null
  and (select n from registered) = 3
