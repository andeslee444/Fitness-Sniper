-- p1_era_line_map: the reviewed bridge from PB2017–PB2023 P-1 era keys to the
-- budget line code each one prints (families piece 1, spec §4.4).
--
-- Grain: one row per era key — (edition, era_key), which implies the spec
-- key (edition, account, organization, budget_activity, era_key) because the
-- era key '{account}-{org}-L{line}' already carries account and organization
-- and every era key prints exactly one budget activity (spec §3;
-- assert_p1_era_map_one_code.sql re-checks it from staging). 6,927 keys:
-- 969 / 1,029 / 989 / 975 / 1,005 / 993 / 967 for PB2017..PB2023
-- (assert_p1_era_map_complete.sql pins them against the full corpus).
--
-- Identity never changes here: era_key stays the lake/fact identity forever
-- (no pe_bli re-keying). This model only records WHICH printed code the key
-- carries (line_item_code, column I "Line Item" of the era P-1 workbook,
-- captured by the loader since migration 021) and WHAT the owner decided
-- about that code's chain (dbt/seeds/p1_era_code_decisions.csv).
--
-- Seed join. A decision row covers the era keys printing its line_item_code
-- under its account, in editions first_edition..last_edition; its
-- organization narrows the match only when set (it is blank unless the code
-- spans organizations within an edition — '10', '15', '20', '30', '500').
-- On '10' and '15', which are not PB2026 collision codes, at most one
-- organization per edition may be same_program: the program grain keeps no
-- organization there, so two would sum into one page
-- (assert_p1_era_map_org_split.sql).
-- A key no row covers is decision='undecided' and never reaches
-- fct_program_decade_series.
--
-- program_key is the bare printed code, set only for the two decisions that
-- carry points (same_program, history_only); NULL for every exclusion and
-- for undecided keys. program_account/program_org are the seed's pins (the
-- PB2026 account/organization whose page the points join); they are set
-- only for chains on one of the 13 PB2026 collision codes
-- (assert_p1_era_map_collision_pinned.sql).
--
-- keys_sha_ok is the drift guard: the seed stores keys_sha256, the sha256 of
-- the sorted 'edition|era_key|budget_activity|filed_title' lines the owner
-- reviewed (NULL parts rendered as ''), joined by '\n' with no trailing
-- newline — exactly govbudget.jbooks.era_map.keys_sha256. This model
-- recomputes it over the keys the decision row covers TODAY: a key added,
-- dropped, retitled or moved to another budget activity since review makes
-- it false (verify-era-map leg b and `era-map check` fail on it). NULL for
-- undecided keys. tests/test_p1_era_line_map_sql.py proves the SQL and the
-- Python hash agree byte for byte.
--
-- source_document_sha256 is the era P-1 workbook's sha (the
-- data/site/workbooks/<sha>.xlsx file); source_cells lists the column-I
-- cells (the printed code) of every workbook row summed into the key, in
-- row order, comma-separated ('I35,I36' for a two-cost-type key) — derived
-- from the row numbers of the lake's recorded amount cells. verify-era-map
-- leg a re-reads those cells from the workbook.

{{ config(materialized='table') }}

with era_rows as (
    select
        fiscal_year as edition,
        account,
        organization,
        budget_activity,
        pe_bli as era_key,
        line_item_code,
        title,
        source_document_id
    from {{ ref('stg_budget_lines') }}
    where exhibit = 'P-1'
      and fiscal_year between 2017 and 2023
      and regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
),

keys as (
    select
        edition,
        account,
        organization,
        budget_activity,
        era_key,
        min(line_item_code) as line_item_code,
        min(title) as filed_title,
        min(source_document_id) as source_document_id
    from era_rows
    group by edition, account, organization, budget_activity, era_key
),

cell_rows as (
    select distinct
        cast(c.fiscal_year as integer) as edition,
        c.pe_bli as era_key,
        cast(regexp_extract(trim(u.cell), '[0-9]+$') as integer) as sheet_row
    from {{ source('lake', 'jbook_budget_lines') }} c,
         unnest(string_split(c.source_cells, ',')) as u(cell)
    where c.exhibit = 'P-1'
      and cast(c.fiscal_year as integer) between 2017 and 2023
      and regexp_matches(c.pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
      and trim(u.cell) <> ''
),

key_cells as (
    select
        edition,
        era_key,
        string_agg('I' || cast(sheet_row as varchar), ',' order by sheet_row) as source_cells
    from cell_rows
    group by edition, era_key
),

decisions as (
    select
        decision_id,
        line_item_code,
        account,
        nullif(trim(coalesce(organization, '')), '') as organization,
        cast(first_edition as integer) as first_edition,
        cast(last_edition as integer) as last_edition,
        decision,
        nullif(trim(coalesce(program_account, '')), '') as program_account,
        nullif(trim(coalesce(program_org, '')), '') as program_org,
        nullif(trim(coalesce(successor_code, '')), '') as successor_code,
        keys_sha256 as reviewed_keys_sha256,
        ruling
    from {{ ref('p1_era_code_decisions') }}
),

bound as (
    select
        k.*,
        d.decision_id,
        d.decision,
        d.program_account,
        d.program_org,
        d.successor_code,
        d.reviewed_keys_sha256,
        d.ruling
    from keys k
    left join decisions d
      on d.line_item_code = k.line_item_code
     and d.account = k.account
     and (d.organization is null or d.organization = k.organization)
     and k.edition between d.first_edition and d.last_edition
),

chain_sha as (
    select
        decision_id,
        sha256(string_agg(line, chr(10) order by line)) as keys_sha256
    from (
        select
            decision_id,
            cast(edition as varchar) || '|' || era_key || '|'
                || coalesce(budget_activity, '') || '|' || coalesce(filed_title, '') as line
        from bound
        where decision_id is not null
    )
    group by decision_id
)

select
    b.edition,
    b.account,
    b.organization,
    b.budget_activity,
    b.era_key,
    b.line_item_code,
    b.filed_title,
    case when b.decision in ('same_program', 'history_only') then b.line_item_code end as program_key,
    b.program_account,
    b.program_org,
    coalesce(b.decision, 'undecided') as decision,
    b.decision_id,
    b.ruling,
    case when b.decision_id is not null then cs.keys_sha256 = b.reviewed_keys_sha256 end as keys_sha_ok,
    b.successor_code,
    doc.sha256 as source_document_sha256,
    kc.source_cells
from bound b
left join chain_sha cs
  on cs.decision_id = b.decision_id
left join {{ source('lake', 'jbook_documents') }} doc
  on doc.id = b.source_document_id
left join key_cells kc
  on kc.edition = b.edition
 and kc.era_key = b.era_key
