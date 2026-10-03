-- fct_program_decade_series: the edition-aware decade series at PROGRAM grain
-- (families piece 1, spec §4.5). The same CTEs as fct_decade_series, with one
-- step added: PB2017–PB2023 P-1 era rows are carried to the budget line code
-- they print, through the owner-reviewed p1_era_line_map.
--
-- Grain: (program_key, account, organization, fy, edition_year, map_basis).
-- Among the rows pages read — map_basis 'native' and 'era_line_map' — the
-- five columns without map_basis are unique: exactly fct_decade_series'
-- uniqueness key with pe_bli renamed program_key
-- (assert_program_decade_grain_unique.sql). program_key is ALWAYS the bare
-- printed code; account/organization are non-NULL only for the 13 PB2026
-- collision codes, exactly as in fct_decade_series. No suffixed key exists.
--
-- What changes against fct_decade_series, and nothing else:
--   * an era row (pe_bli '{account}-{org}-L{line}') enters ONLY when its map
--     decision is same_program or history_only. Its pe_bli becomes the map's
--     program_key, and its account/organization become the map's pinned
--     program_account/program_org — never the era row's own values — so a
--     pinned chain (e.g. '20' DSS -> DCSA) lands on the PB2026 side it was
--     decided for. Excluded and undecided era rows produce no grain at all.
--   * Same aggregation as today: era lines that share a code and a
--     map_basis in an edition (advance-procurement pairs, lines in two
--     budget activities, a non-collision code under two accounts) are summed
--     at the detail step before slug selection, exactly as modern lines that
--     share a code already are. Measured 2026-10-02: every era key of an
--     edition picks the same slug per scenario, so the program sum equals the
--     sum of the fct_decade_series era grains it absorbs
--     (assert_program_decade_conservation.sql).
--   * row_fact_id still hashes the SOURCE row's own identity (its era key,
--     its own account and organization) — the formula below is
--     fct_decade_series' byte for byte — so a single-source era grain's
--     source_fact_id is the fact ID the era row already has.
--   * map_basis is part of the grouping key, from detail through the slug
--     pick to the lake check: 'native' (no era row), 'era_line_map'
--     (same_program era keys — what the code's page reads), and
--     'era_history_only' (history_only era keys — data, no page). Rows of
--     different bases never sum into one grain. A history_only chain and a
--     same_program chain that print the same code in the same edition
--     (measured 2026-10-02: '10' in PB2018, DPAA beside TJS; '15' in
--     PB2021–PB2023, TJS Cyber beside DISA) give two rows, and the
--     era_line_map row the page reads sums only the same_program keys. A
--     native row and an era row on one five-column key would be two rows a
--     page reads: assert_program_decade_grain_unique.sql fails on that
--     (measured 2026-10-02: no era code equals an R-1 program element in any
--     edition).
--   * source_keys: the era keys summed, sorted, comma-separated; NULL for
--     native grains.
--
-- Parity: every map_basis='native' row — all editions, including the 22,008
-- PB2017–PB2023 R-1 grains — equals its fct_decade_series row column for
-- column (assert_program_decade_native_equals_line.sql). The collision
-- anchors and the candidate patterns below are copied VERBATIM from
-- fct_decade_series.sql, and the slug pick is copied with map_basis added to
-- its partition; tests/test_program_decade_series_sql.py fails if they drift
-- apart. fct_decade_series itself is not touched (F-15's builder,
-- verify-phase5e and fct_book_diff keep reading it).

{{ config(materialized='table') }}

with era_map as (
    select
        edition,
        era_key,
        program_key,
        program_account,
        program_org,
        decision
    from {{ ref('p1_era_line_map') }}
    where decision in ('same_program', 'history_only')
),

lake as (
    select
        b.exhibit,
        case when m.era_key is not null then m.program_key else b.pe_bli end as pe_bli,
        b.fiscal_year as edition_year,
        b.amount_type,
        b.amount_thousands,
        case when m.era_key is not null then m.program_account else b.account end as account,
        case when m.era_key is not null then m.program_org else b.organization end as organization,
        case m.decision
            when 'same_program' then 'era_line_map'
            when 'history_only' then 'era_history_only'
            else 'native'
        end as map_basis
    from {{ ref('stg_budget_lines') }} b
    left join era_map m
      on b.exhibit = 'P-1'
     and m.edition = b.fiscal_year
     and m.era_key = b.pe_bli
),

detail as (
    select
        case when m.era_key is not null then m.program_key else b.pe_bli end as pe_bli,
        b.fiscal_year as edition_year,
        b.amount_type,
        case when m.era_key is not null then m.program_account else b.account end as account,
        case when m.era_key is not null then m.program_org else b.organization end as organization,
        b.amount_thousands,
        substr(sha256(
            d.sha256 || '|' || b.exhibit || '|' || cast(b.fiscal_year as varchar)
            || '|' || b.account || '|' || b.organization || '|'
            || coalesce(b.budget_activity, '') || '|' || b.pe_bli || '|' || b.amount_type
        ), 1, 16) as row_fact_id,
        case when m.era_key is not null then b.pe_bli end as source_key,
        case m.decision
            when 'same_program' then 'era_line_map'
            when 'history_only' then 'era_history_only'
            else 'native'
        end as map_basis
    from {{ ref('stg_budget_lines') }} b
    left join {{ source('lake', 'jbook_documents') }} d
      on d.id = b.source_document_id
    left join era_map m
      on b.exhibit = 'P-1'
     and m.edition = b.fiscal_year
     and m.era_key = b.pe_bli
    where b.exhibit in ('R-1', 'P-1')
      and b.source_document_id is not null
      and b.pe_bli <> '9999999999'
      and (
          m.era_key is not null
          or not (b.exhibit = 'P-1' and regexp_matches(b.pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L'))
      )
),

-- Collision anchor (E2.1 correction, 2026-08-21 — see the model-level
-- comment above): >1 distinct account reporting at the SAME amount_type,
-- checked across EVERY amount_type PB2026's own workbook carries (not
-- only fy_2026_total). Independently re-derived (this mart reads
-- stg_budget_lines directly and is not downstream of dim_programs in the
-- dbt DAG).
collision_slots as (
    select pe_bli, amount_type, account
    from {{ ref('stg_budget_lines') }}
    where fiscal_year = 2026
      and title is not null
      and pe_bli <> '9999999999'
    group by pe_bli, amount_type, account
),
collision_pes as (
    select distinct pe_bli
    from (
        select pe_bli
        from collision_slots
        group by pe_bli, amount_type
        having count(distinct account) > 1
    )
),

-- ROADMAP #45 organization collision anchor — collision_pes' mirror on
-- organization instead of account (see the model-level comment above).
org_collision_slots as (
    select pe_bli, amount_type, organization
    from {{ ref('stg_budget_lines') }}
    where fiscal_year = 2026
      and title is not null
      and pe_bli <> '9999999999'
    group by pe_bli, amount_type, organization
),
org_collision_pes as (
    select distinct pe_bli
    from (
        select pe_bli
        from org_collision_slots
        group by pe_bli, amount_type
        having count(distinct organization) > 1
    )
),

editions as (
    select distinct edition_year from detail
),

-- Candidate slug patterns: a 1:1 transcription of reconcile.scenario_map
-- (PriorYear / CurrentYear / BudgetYearOne; BudgetYearOneBase is not a
-- series kind). priority = list order = the any-candidate pick order.
cand_patterns (scenario, priority, slug_template, fy_offset) as (
    values
        ('PriorYear', 1, 'fy_%d_actuals', 2),
        ('PriorYear', 2, 'fy_%d_base_oco', 2),
        ('PriorYear', 3, 'fy_%d_actual', 2),
        ('CurrentYear', 1, 'fy_%d_total', 1),
        ('CurrentYear', 2, 'fy_%d_enacted', 1),
        ('CurrentYear', 3, 'fy_%d_total_enacted', 1),
        ('CurrentYear', 4, 'fy_%d_less_supplementals_enacted', 1),
        ('CurrentYear', 5, 'fy_%d_pb_request_with_cr_amounts', 1),
        ('CurrentYear', 6, 'fy_%d_pb_request_with_cr_adjustments', 1),
        ('CurrentYear', 7, 'fy_%d_enactment', 1),
        ('CurrentYear', 8, 'fy_%d_total_enacted_base_emerg_oco', 1),
        ('CurrentYear', 9, 'fy_%d_total_pb_requests_with_cr_adj_base_oco', 1),
        ('CurrentYear', 10, 'fy_%d_total_pb_requests_with_cr_adj_base_oco_saa', 1),
        ('CurrentYear', 11, 'fy_%d_total_pb_requests_with_cr_adj_base_oco_emergency', 1),
        ('BudgetYearOne', 1, 'fy_%d_total', 0),
        ('BudgetYearOne', 2, 'fy_%d_disc_request', 0),
        ('BudgetYearOne', 3, 'fy_%d_request', 0),
        ('BudgetYearOne', 4, 'fy_%d_total_base_oco', 0)
),

candidates as (
    select
        e.edition_year,
        c.scenario,
        c.priority,
        c.fy_offset,
        printf(c.slug_template, e.edition_year - c.fy_offset) as amount_type
    from editions e
    cross join cand_patterns c
),

detail_sums as (
    select
        d.pe_bli,
        d.edition_year,
        c.scenario,
        c.priority,
        c.fy_offset,
        c.amount_type,
        case when cp.pe_bli is not null then d.account end as account,
        case when ocp.pe_bli is not null then d.organization end as organization,
        d.map_basis,
        sum(d.amount_thousands) as amount,
        count(*) as n_source_rows,
        case when count(*) = 1 then min(d.row_fact_id) end as source_fact_id,
        string_agg(distinct d.source_key, ',' order by d.source_key) as source_keys
    from detail d
    join candidates c
      on c.edition_year = d.edition_year
     and c.amount_type = d.amount_type
    left join collision_pes cp
      on cp.pe_bli = d.pe_bli
    left join org_collision_pes ocp
      on ocp.pe_bli = d.pe_bli
    group by
        d.pe_bli, d.edition_year, c.scenario, c.priority, c.fy_offset, c.amount_type,
        case when cp.pe_bli is not null then d.account end,
        case when ocp.pe_bli is not null then d.organization end,
        d.map_basis
),

-- The slug pick is fct_decade_series' with one change: map_basis joins the
-- partition, so a same_program grain and a history_only grain of one code
-- and edition each pick their own top-priority slug (every era key of an
-- edition prints the same slugs, so both pick the same one).
chosen as (
    select * from (
        select
            *,
            row_number() over (
                -- account/organization in the partition: each side of a
                -- genuine collision (account OR organization, whichever
                -- axis this pe_bli actually splits on) picks its OWN
                -- top-priority candidate slug independently. Without this,
                -- row_number() would rank every side's rows together and
                -- could arbitrarily discard one side's only row as a
                -- tie-broken rn=2 (DuckDB does not guarantee priority ties
                -- resolve by account/organization) — this pins the fix.
                partition by pe_bli, account, organization, map_basis, edition_year, scenario
                order by priority
            ) as rn
        from detail_sums
    )
    where rn = 1
),

-- Raw lake sums per candidate slug, as in fct_decade_series (no title
-- filter, every exhibit except P-1R), over the same mapped lake: an era row
-- carried by the map counts under its program_key, pinned
-- account/organization and map_basis, so a program grain is verified against
-- the lake sum of exactly the rows it absorbed.
lake_sums as (
    select
        l.pe_bli,
        l.edition_year,
        c.scenario,
        case when cp.pe_bli is not null then l.account end as account,
        case when ocp.pe_bli is not null then l.organization end as organization,
        l.map_basis,
        sum(l.amount_thousands) as lake_amount
    from lake l
    join candidates c
      on c.edition_year = l.edition_year
     and c.amount_type = l.amount_type
    left join collision_pes cp
      on cp.pe_bli = l.pe_bli
    left join org_collision_pes ocp
      on ocp.pe_bli = l.pe_bli
    where l.exhibit <> 'P-1R'
    group by l.pe_bli, l.edition_year, c.scenario, c.amount_type,
             case when cp.pe_bli is not null then l.account end,
             case when ocp.pe_bli is not null then l.organization end,
             l.map_basis
)

select
    ch.pe_bli as program_key,
    ch.edition_year - ch.fy_offset as fy,
    ch.edition_year,
    case ch.scenario
        when 'PriorYear' then 'actuals'
        when 'CurrentYear' then 'enacted'
        when 'BudgetYearOne' then 'request'
    end as amount_type_kind,
    ch.amount,
    ch.amount as amount_thousands,
    ch.scenario,
    ch.amount_type,
    ch.account,
    ch.organization,
    ch.n_source_rows,
    ch.source_fact_id,
    ch.map_basis,
    ch.source_keys
from chosen ch
where exists (
    select 1
    from lake_sums ls
    -- pe_bli compares `is not distinct from`, not `=`: a mapped era row whose
    -- p1_era_line_map.program_key is wrongly NULL (data bug, decision should
    -- never allow it) produces pe_bli = NULL here and in lake_sums alike.
    -- Plain `=` treats NULL = NULL as unknown and would silently drop that
    -- grain instead of publishing it with program_key NULL, where
    -- not_null_fct_program_decade_series_program_key catches it (fix round 1).
    where ls.pe_bli is not distinct from ch.pe_bli
      and ls.edition_year = ch.edition_year
      and ls.scenario = ch.scenario
      and ls.account is not distinct from ch.account
      and ls.organization is not distinct from ch.organization
      and ls.map_basis = ch.map_basis
      and abs(ls.lake_amount - ch.amount) <= 0.5
)
