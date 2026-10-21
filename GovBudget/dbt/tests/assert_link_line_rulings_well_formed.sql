-- dbt/seeds/link_line_rulings.csv integrity (R-DEC-LINK-2026-10-21 and
-- R-DEC-LINK-2026-10-21-B, owner 2026-10-21). The seed is a ledger of rulings on crosswalk pairs:
-- audit_link_grading withdraws a pair on `withdraw`, and the recurrence gates
-- (assert_no_production_award_on_modification_line,
-- assert_refuted_pair_siblings_ruled) accept a pair carrying any ruling. A
-- malformed row would do either silently, so the build stops on:
--
--   * a missing award_piid or pe_bli;
--   * a ruling value outside the three below, or a row whose ruler and
--     ruling id are not that value's own:
--       withdraw  the owner's ruling: grades the pair low (not published);
--                 ruled_by 'owner', ruling_id 'R-DEC-LINK-2026-10-21' or
--                 'R-DEC-LINK-2026-10-21-B' (the owner's second ruling the
--                 same day, "proceed with recommendations": it withdrew the
--                 10 F03500 production-support pairs the controller had
--                 recorded as holds, and is kept apart because the first
--                 approval did not cover them);
--       allow     the owner's ruling: the pair stands as published;
--                 ruled_by 'owner', ruling_id 'R-DEC-LINK-2026-10-21' (the
--                 B ruling allowed nothing);
--       hold      recorded, kept as published, pending an owner ruling
--                 (controller, 2026-10-21: the owner never ruled on it, so
--                 the ledger must not say they did); grades nothing;
--                 ruled_by 'controller', ruling_id
--                 'R-DEC-LINK-2026-10-21-HOLD'. No seed row is a hold
--                 since the B ruling; the value stays valid for the next
--                 flagged pair no owner has ruled on;
--   * a blank species or evidence (a ruling says what it is and why);
--   * ruled_on not an ISO date;
--   * a pair ruled twice (two rows for one (award_piid, pe_bli)) — every row
--     of the pair is returned.
--
-- When the owner rules on a held pair, its row flips to `withdraw` or
-- `allow` under the owner's ruler and that ruling's own id, as the B ruling
-- did; it is never pre-empted here, and a new ruling id is added above only
-- with the ruling it names.
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
        (coalesce(ruling, '') = 'withdraw'
         and coalesce(ruled_by, '') = 'owner'
         and coalesce(ruling_id, '') in ('R-DEC-LINK-2026-10-21',
                                         'R-DEC-LINK-2026-10-21-B'))
     or (coalesce(ruling, '') = 'allow'
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
