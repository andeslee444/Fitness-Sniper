-- Column order is load-bearing: fct_award_transactions UNION ALLs this model
-- positionally with its sibling staging model. Keep both lists identical.
-- New columns (recon §D, added 2026-06-12):
--   col 17: usaspending_permalink  — raw permalink from USAspending bulk download
--   col 18: award_unique_key       — alias of assistance_award_unique_key (assistance)
--                                    or contract_award_unique_key (contracts)
select
    assistance_transaction_unique_key as transaction_key,
    'assistance' as award_type,
    try_cast(action_date as date) as action_date,
    cast(fy as integer) as fiscal_year,
    try_cast(federal_action_obligation as double) as obligation,
    nullif(recipient_uei, '') as recipient_uei,
    upper(recipient_name) as recipient_name,
    nullif(recipient_parent_uei, '') as recipient_parent_uei,
    upper(recipient_parent_name) as recipient_parent_name,
    awarding_agency_name,
    awarding_sub_agency_name,
    cast(null as varchar) as naics_code,
    cast(null as varchar) as product_or_service_code,
    -- Assistance archives carry the state NAME (contracts carry the 2-letter
    -- code); Phase 1 normalizes pop_state to one vocabulary.
    primary_place_of_performance_state_name as pop_state,
    prime_award_transaction_place_of_performance_cd_current as pop_district,
    -- award_id_piid: null-cast in assistance; real column in contracts (SAME position both files)
    cast(null as varchar) as award_id_piid,
    -- usaspending_permalink: real column in assistance; null-cast in contracts (SAME position both files)
    usaspending_permalink,
    -- award_unique_key: assistance_award_unique_key here; contract_award_unique_key in sibling (SAME position both files)
    assistance_award_unique_key as award_unique_key
from {{ source('lake', 'assistance') }} src
-- ROADMAP #133 (2026-09-25): a assistance whose key sits in two fiscal-year
-- archives is kept ONCE — its strictly newer copy — when
-- audit_award_duplicate_copies proves the move (exactly two copies, two
-- different fiscal years, two different last_modified_dates); the retired copy
-- is listed in audit_award_fy_moves and dropped by the clause below (empty
-- when this build retired none — see macros/award_fy_moves.sql). Every other
-- duplicate passes through untouched and fails
-- unique_fct_award_transactions_transaction_key.
-- depends_on: {{ ref('audit_award_fy_moves') }}
{{ award_fy_move_filter('assistance', 'assistance_transaction_unique_key', 'src') }}
