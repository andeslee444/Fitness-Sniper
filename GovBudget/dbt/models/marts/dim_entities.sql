-- One row per company family.
--
-- ROADMAP #10 adds the SAM.gov registration of the family's DOMINANT member,
-- joined on `dominant_registration_uei` below: `max(...) filter (rk = 1)`, the
-- highest REGISTRATION UEI (coalesce(parent_uei, recipient_uei)) among the
-- TIED top members — not the highest recipient_uei, which on a tie across two
-- different parents is a different member. That is NOT always the rn=1 row
-- `display_name` is taken from. The two name the same member wherever the top
-- member is unique — every published family today — but on an exact tie they
-- can differ, so nothing rendered may say this registration is the one the
-- page's heading was read from. sam-registration.tsx and the citation formula
-- in export_site.py state the tie-break instead of that identity.
--
-- LEFT JOINed, so a partial extract publishes what it has and nulls the rest;
-- the join is 1:1 by construction (entities.parquet is written unique on
-- sam_uei by sam_entities.write_entities_parquet), and schema.yml's unique
-- test on family_key is the assertion that says so.
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
-- rk (rank, ties kept) vs rn (row_number, one member): the SAM join key is
-- taken over the TIED top set with max(), so it does not depend on which tied
-- member rn numbers 1 — sam_entities.dominant_parent_ueis() re-derives it
-- identically and verify-phase2 leg e4 compares the two. rn's order is TOTAL
-- (R-DEC-ENTITYTIE, 2026-09-26): obligation desc, then the registration UEI
-- ASCENDING, then recipient_uei (unique and not null in entity_xwalk). Until
-- then it stopped at the obligation, and 13 tied families' display_name
-- changed between reads of one unchanged warehouse (none published).
-- On a tie across registrations the name is therefore read from the LOWEST
-- registration and the SAM record from the HIGHEST: there the two differ by
-- rule, and (header, first paragraph) nothing rendered may say they are one
-- member.
-- tests/test_dbt_entity_display_tiebreak.py holds the order.
with ranked as (
    select *,
           row_number() over (
               partition by family_key
               order by total_obligation desc nulls last,
                        coalesce(parent_uei, recipient_uei) asc nulls last,
                        recipient_uei asc nulls last
           ) as rn,
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
        -- The WORST member's tier. Not min(confidence): as text 'high' sorts
        -- before 'medium', so min() returned the BEST tier and graded a family
        -- high when any one member was (29 families, NAN on /companies/;
        -- integration final check, 2026-09-25). Ranked instead; an unknown
        -- tier maps to NULL and fails accepted_values in schema.yml.
        case max(case confidence when 'high' then 1 when 'medium' then 2 end)
            when 1 then 'high' when 2 then 'medium' end as worst_confidence
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
