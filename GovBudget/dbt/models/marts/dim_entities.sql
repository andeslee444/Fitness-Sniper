-- One row per company family.
--
-- ROADMAP #10 adds the SAM.gov registration of the family's DOMINANT member —
-- the same rn=1 row `display_name` is taken from, so the sam_* columns describe
-- the registration the page's own heading is built on. LEFT JOINed, so a
-- partial extract publishes what it has and nulls the rest; the join is 1:1 by
-- construction (entities.parquet is written unique on sam_uei by
-- sam_entities.write_entities_parquet), and schema.yml's unique test on
-- family_key is the assertion that says so.
--
-- ENRICHMENT, NEVER A TIER INPUT. `worst_confidence` is computed above the
-- join and cannot see it: recipient_parent_name in USAspending IS the SAM
-- registration name, so re-reading it from SAM returns the same string
-- (docs/superpowers/reviews/10-entity-resolution-spike.md §4).
--
-- The relation on the right of the join comes from sam_entities_relation(),
-- which substitutes a typed zero-row relation when the extract has never run —
-- see that macro for why an absent parquet would otherwise kill the mart.
--
-- rk (rank, ties kept) vs rn (row_number, ties broken arbitrarily): the SAM
-- join key is taken over the TIED top set with max(), so it does not depend on
-- which tied member a query plan happens to number 1 — sam_entities.
-- dominant_parent_ueis() re-derives it identically and verify-phase2 leg e4
-- compares the two. display_name keeps rn, unchanged: no published family's
-- label moves.
with ranked as (
    select *,
           row_number() over (partition by family_key order by total_obligation desc nulls last) as rn,
           rank() over (partition by family_key order by total_obligation desc nulls last) as rk
    from {{ ref('entity_xwalk') }}
),
base as (
    select
        family_key,
        max(coalesce(parent_name, recipient_name)) filter (where rn = 1) as display_name,
        max(coalesce(parent_uei, recipient_uei)) filter (where rk = 1) as dominant_registration_uei,
        count(*) as uei_count,
        sum(total_obligation) as total_obligation,
        min(confidence) as worst_confidence
    from ranked
    group by family_key
),
sam as (
    select * from {{ sam_entities_relation() }}
)
select
    b.family_key,
    b.display_name,
    b.uei_count,
    b.total_obligation,
    b.worst_confidence,
    b.dominant_registration_uei,
    s.sam_uei,
    s.legal_business_name          as sam_legal_business_name,
    s.cage_code                    as sam_cage_code,
    s.registration_status          as sam_registration_status,
    s.registration_expiration_date as sam_registration_expiration_date,
    s.business_types               as sam_business_types,
    s.primary_naics                as sam_primary_naics,
    s.public_url                   as sam_public_url,
    s.source_url                   as sam_source_url,
    s.retrieved_at                 as sam_retrieved_at
from base b
left join sam s
  on s.sam_uei = b.dominant_registration_uei
