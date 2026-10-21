-- dbt/seeds/link_line_rulings.csv integrity (R-DEC-LINK-2026-10-21, owner
-- 2026-10-21). The seed is a ledger of rulings on crosswalk pairs:
-- audit_link_grading withdraws a pair on `withdraw`, and the recurrence gates
-- (assert_no_production_award_on_modification_line,
-- assert_refuted_pair_siblings_ruled) accept a pair carrying any ruling. A
-- malformed row would do either silently, so the build stops on:
--
--   * a missing award_piid or pe_bli;
--   * a ruling value outside the three below, or a row whose ruler and
--     ruling id are not that value's own:
--       withdraw  the owner's ruling: grades the pair low (not published);
--                 ruled_by 'owner', ruling_id 'R-DEC-LINK-2026-10-21';
--       allow     the owner's ruling: the pair stands as published;
--                 ruled_by 'owner', ruling_id 'R-DEC-LINK-2026-10-21';
--       hold      recorded, kept as published, pending an owner ruling
--                 (controller, 2026-10-21: the owner never ruled on it, so
--                 the ledger must not say they did); grades nothing;
--                 ruled_by 'controller', ruling_id
--                 'R-DEC-LINK-2026-10-21-HOLD';
--   * a blank species or evidence (a ruling says what it is and why);
--   * ruled_on not an ISO date;
--   * a pair ruled twice (two rows for one (award_piid, pe_bli)) — every row
--     of the pair is returned.
--
-- When the owner rules on a held pair, its row flips to `withdraw` or
-- `allow` under the owner's ruler and id; it is never pre-empted here.
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
   or not (
        (coalesce(ruling, '') in ('withdraw', 'allow')
         and coalesce(ruled_by, '') = 'owner'
         and coalesce(ruling_id, '') = 'R-DEC-LINK-2026-10-21')
     or (coalesce(ruling, '') = 'hold'
         and coalesce(ruled_by, '') = 'controller'
         and coalesce(ruling_id, '') = 'R-DEC-LINK-2026-10-21-HOLD')
   )
   or coalesce(trim(species), '') = ''
   or coalesce(trim(evidence), '') = ''
   or try_strptime(coalesce(cast(ruled_on as varchar), ''), '%Y-%m-%d') is null
   or n_rulings > 1
