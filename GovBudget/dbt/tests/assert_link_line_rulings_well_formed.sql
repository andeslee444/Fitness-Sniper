-- dbt/seeds/link_line_rulings.csv integrity (R-DEC-LINK-2026-10-21, owner
-- 2026-10-21). The seed is a ledger of a person's rulings on crosswalk pairs:
-- audit_link_grading withdraws a pair on `withdraw`, and the recurrence gates
-- (assert_no_production_award_on_modification_line,
-- assert_refuted_pair_siblings_ruled) accept a pair carrying any ruling. A
-- malformed row would do either silently, so the build stops on:
--
--   * a missing award_piid or pe_bli;
--   * a ruling outside 'withdraw' / 'allow';
--   * a blank species or evidence (a ruling says what it is and why);
--   * ruled_on not an ISO date; ruled_by other than 'owner' (the only ruler
--     the seed has: R-DEC-LINK-2026-10-21); a blank ruling_id;
--   * a pair ruled twice (two rows for one (award_piid, pe_bli)) — every row
--     of the pair is returned.
--
-- Returned rows are the FAILURES (dbt singular test convention).
with seed as (
    select
        *,
        count(*) over (partition by award_piid, pe_bli) as n_rulings
    from {{ ref('link_line_rulings') }}
)
select award_piid, pe_bli, ruling, ruled_on, ruled_by, ruling_id
from seed
where coalesce(trim(award_piid), '') = ''
   or coalesce(trim(pe_bli), '') = ''
   or coalesce(ruling, '') not in ('withdraw', 'allow')
   or coalesce(trim(species), '') = ''
   or coalesce(trim(evidence), '') = ''
   or try_strptime(coalesce(cast(ruled_on as varchar), ''), '%Y-%m-%d') is null
   or coalesce(ruled_by, '') <> 'owner'
   or coalesce(trim(ruling_id), '') = ''
   or n_rulings > 1
