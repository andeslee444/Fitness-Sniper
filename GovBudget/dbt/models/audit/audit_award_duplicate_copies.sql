{{ config(materialized='table') }}
-- audit_award_duplicate_copies — every copy of every transaction key that
-- appears more than once in ONE award archive (contracts or assistance), and
-- what the fiscal-year move rule does with it (ROADMAP #133, owner-delegated
-- ruling 2026-09-25).
--
-- Why a key appears twice. A USAspending source correction can move a
-- transaction into another fiscal year's archive: the refreshed archive then
-- carries the key once in its new year while an older archive still carries
-- the pre-correction copy. On 2026-09-24 a re-sync of FY2026 did exactly that
-- to 81 rows (74 contract, 7 assistance) and scripts/reconcile_award_moves.py
-- retired the old copies by rewriting the parquet, report first.
--
-- The rule is that script's acceptance rule, applied at build time so a fresh
-- sync rebuilds without the manual step:
--
--   * EXACTLY TWO copies, in two DIFFERENT fiscal-year archives, both with a
--     parseable last_modified_date and the two dates DIFFERENT → the strictly
--     newer copy is kept ('keep') and the other is retired ('retire').
--     stg_contracts / stg_assistance / stg_flow_contracts drop the retired copy
--     through audit_award_fy_moves (one row per move, both sides named).
--   * anything else → 'ambiguous', with the reason. NOTHING is retired, so
--     unique_fct_award_transactions_transaction_key fails exactly as it did
--     before this model existed, and assert_award_duplicates_unambiguous names
--     every copy and why. The guard is never weakened.
--
-- The script names a refreshed fiscal year and requires the refreshed copy to
-- be the newer; here no year is privileged — whichever copy the source revised
-- later wins, which is the same outcome on every move the script accepts.
--
-- Per archive, as in the script: a key present once in contracts and once in
-- assistance is not a move and is left to the unique test.
--
-- Materialized as a TABLE: finding duplicates is one aggregate over ~41.5M
-- contract keys, which every query through the staging views would otherwise
-- repeat. The table is rebuilt by every `dbt build`, which every sync is
-- followed by; assert_award_fy_moves_applied fails if it has gone stale
-- against the lake (a listed move whose copies are no longer as recorded).
with contract_dup_keys as (
    select contract_transaction_unique_key as k
    from {{ source('lake', 'contracts') }}
    where contract_transaction_unique_key is not null
    group by 1
    having count(*) > 1
),
assistance_dup_keys as (
    select assistance_transaction_unique_key as k
    from {{ source('lake', 'assistance') }}
    where assistance_transaction_unique_key is not null
    group by 1
    having count(*) > 1
),
copies as (
    select
        'contract' as award_type,
        c.contract_transaction_unique_key as transaction_key,
        cast(c.fy as integer) as fiscal_year,
        c.last_modified_date,
        try_cast(c.last_modified_date as timestamptz) as modified_at,
        c.filename as source_file
    from {{ source('lake', 'contracts') }} c
    where c.contract_transaction_unique_key in (select k from contract_dup_keys)
    union all
    select
        'assistance' as award_type,
        a.assistance_transaction_unique_key as transaction_key,
        cast(a.fy as integer) as fiscal_year,
        a.last_modified_date,
        try_cast(a.last_modified_date as timestamptz) as modified_at,
        a.filename as source_file
    from {{ source('lake', 'assistance') }} a
    where a.assistance_transaction_unique_key in (select k from assistance_dup_keys)
),
per_key as (
    select
        award_type,
        transaction_key,
        count(*) as copies,
        count(distinct fiscal_year) as fiscal_years,
        count(modified_at) as dated_copies,
        count(distinct modified_at) as distinct_dates
    from copies
    group by 1, 2
),
classified as (
    select
        c.*,
        k.copies,
        k.fiscal_years,
        case
            when k.copies <> 2 then 'more than two copies'
            when k.fiscal_years <> 2 then 'both copies sit in one fiscal year'
            when k.dated_copies <> 2 then 'a copy has no parseable last_modified_date'
            when k.distinct_dates <> 2 then 'both copies carry the same last_modified_date'
        end as ambiguity
    from copies c
    join per_key k
      on k.award_type = c.award_type and k.transaction_key = c.transaction_key
)
select
    award_type,
    transaction_key,
    fiscal_year,
    last_modified_date,
    modified_at,
    source_file,
    copies,
    fiscal_years,
    case
        when ambiguity is not null then 'ambiguous'
        -- two dated copies with different dates: the newer is unique
        when modified_at = max(modified_at) over (
            partition by award_type, transaction_key
        ) then 'keep'
        else 'retire'
    end as resolution,
    ambiguity
from classified
