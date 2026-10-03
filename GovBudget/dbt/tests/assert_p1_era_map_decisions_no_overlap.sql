-- dbt/seeds/p1_era_code_decisions.csv integrity (families piece 1, spec §4.3):
-- the reviewed artifact must be well-formed and its ranges must never overlap.
--
--   * malformed row: a missing identity column; first/last edition outside
--     2017..2023 or reversed; a decision outside the five the spec defines;
--     a decision_id that is not '{code}|{account}|{org}|{first}-{last}';
--     decided_by other than 'owner'; decided_on not an ISO date; a ruling
--     that is not R-DEC-ERA-SAME / -EXCLUDE / -HISTORY / -B<n>; keys_sha256
--     not 64 lowercase hex; n_keys not a positive integer.
--   * duplicate decision_id.
--   * ranges overlap: two rows for one (code, account) whose organizations
--     can both match one key (equal, or either blank) and whose edition
--     ranges intersect — one era key would bind two decisions.
with seed as (
    select
        decision_id,
        line_item_code,
        account,
        coalesce(nullif(trim(coalesce(organization, '')), ''), '') as organization,
        cast(first_edition as varchar) as first_edition,
        cast(last_edition as varchar) as last_edition,
        try_cast(first_edition as integer) as first_ed,
        try_cast(last_edition as integer) as last_ed,
        decision,
        decided_by,
        cast(decided_on as varchar) as decided_on,
        ruling,
        keys_sha256,
        try_cast(n_keys as integer) as n_keys
    from {{ ref('p1_era_code_decisions') }}
)

select 'malformed row' as failure, decision_id, cast(null as varchar) as other_decision_id
from seed
where decision_id is null
   or line_item_code is null
   or account is null
   or first_ed is null
   or last_ed is null
   or first_ed < 2017
   or last_ed > 2023
   or first_ed > last_ed
   or decision is null
   or decision not in ('same_program', 'history_only', 'exclude_placeholder',
                       'exclude_route_unsafe', 'exclude_reused_code')
   or decision_id <> line_item_code || '|' || account || '|' || organization
                     || '|' || first_edition || '-' || last_edition
   or coalesce(decided_by, '') <> 'owner'
   or not regexp_matches(coalesce(decided_on, ''), '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
   or not regexp_matches(coalesce(ruling, ''), '^R-DEC-ERA-(SAME|EXCLUDE|HISTORY|B[0-9]+)$')
   or not regexp_matches(coalesce(keys_sha256, ''), '^[0-9a-f]{64}$')
   or n_keys is null
   or n_keys < 1

union all

select 'duplicate decision_id', decision_id, cast(null as varchar)
from seed
group by decision_id
having count(*) > 1

union all

select 'ranges overlap', a.decision_id, b.decision_id
from seed a
join seed b
  on a.line_item_code = b.line_item_code
 and a.account = b.account
 and (a.organization = b.organization or a.organization = '' or b.organization = '')
 and a.decision_id < b.decision_id
 and a.first_ed <= b.last_ed
 and b.first_ed <= a.last_ed
