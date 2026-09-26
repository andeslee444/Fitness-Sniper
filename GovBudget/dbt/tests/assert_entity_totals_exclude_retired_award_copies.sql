{#
  ROADMAP #133 (owner-delegated ruling 2026-09-25) — dbt checker, decisions
  fix round 2 (2026-09-26); header brought up to date for R-DEC-133b (fix
  round 3, 2026-09-26).

  The fiscal-year move rule is applied twice. dbt staging (stg_contracts /
  stg_assistance) drops the copy audit_award_fy_moves retires, so
  fct_award_transactions counts a moved transaction once. `govbudget
  entity-graph` does not read the staging models — it runs BEFORE `dbt build`
  in the chain — so since R-DEC-133b it reads the contracts/assistance archive
  globs through src/govbudget/award_moves.py (register_award_rows: the same
  rule, re-implemented in Python; entity_graph._TX_SQL sums its `_awards`
  view), and an ambiguous duplicate stops it as it stops dbt. dim_entities
  publishes entity_xwalk.total_obligation beside a citation whose query sums
  fct_award_transactions, so the two applications must agree on every
  recipient a retired copy belongs to.

  This test is the build-time cross-check that they do. It returns every
  recipient UEI a retired copy belongs to whose entity_xwalk total differs
  from the warehouse's (fct_award_transactions) total by more than a cent —
  the build stops here, at the first step that can see both, instead of at
  the site's recompute gates. It fails when entity_xwalk still counts a
  retired copy: entity-graph regressed to a raw read, award_moves.py and
  audit_award_duplicate_copies.sql disagree on which copy is newer, or
  entity_xwalk.parquet was written before the re-sync that moved the key. The
  fix is upstream of dbt: re-run `govbudget entity-graph` on the current lake,
  then build again; if it still fails, compare audit_award_fy_moves with
  award_moves.find_moves() on the same archives. A UEI entity_xwalk does not
  carry has no entity total to be wrong, and is not this test's business.

  Same compile-time probe as macros/award_fy_moves.sql: on a lake where this
  build retired nothing (today's, and every lake the manual reconcile
  cleaned) there is no copy to trace, and the test compiles to an empty
  select that never reads the award archives. A scoped build that selects
  entity_xwalk but never built the move list (e.g. `--select +dim_entities`
  on a fresh warehouse) has no move to check against either; in a full
  build the move list is always built before this test runs.
#}
-- depends_on: {{ ref('audit_award_fy_moves') }}
-- depends_on: {{ ref('fct_award_transactions') }}
-- depends_on: {{ ref('entity_xwalk') }}
{%- set moves = ref('audit_award_fy_moves') -%}
{%- set retired = 1 -%}
{%- if execute -%}
  {%- set built = adapter.get_relation(
        database=moves.database, schema=moves.schema, identifier=moves.identifier) -%}
  {%- if built is none -%}
    {%- set retired = 0 -%}
  {%- else -%}
    {%- set probe = run_query("select count(*) from " ~ moves) -%}
    {%- set retired = probe.columns[0].values()[0] -%}
  {%- endif -%}
{%- endif %}
{% if retired > 0 -%}
with retired_copies as (
    select nullif(c.recipient_uei, '') as recipient_uei
    from {{ source('lake', 'contracts') }} c
    join {{ moves }} m
      on m.award_type = 'contract'
     and m.transaction_key = c.contract_transaction_unique_key
     and m.retired_fiscal_year = cast(c.fy as integer)
     and m.retired_last_modified_date = c.last_modified_date
    union all
    select nullif(a.recipient_uei, '') as recipient_uei
    from {{ source('lake', 'assistance') }} a
    join {{ moves }} m
      on m.award_type = 'assistance'
     and m.transaction_key = a.assistance_transaction_unique_key
     and m.retired_fiscal_year = cast(a.fy as integer)
     and m.retired_last_modified_date = a.last_modified_date
),
touched as (
    select distinct recipient_uei
    from retired_copies
    where recipient_uei is not null
),
warehouse as (
    select recipient_uei, sum(obligation) as warehouse_total
    from {{ ref('fct_award_transactions') }}
    where recipient_uei in (select recipient_uei from touched)
    group by 1
)
select
    x.recipient_uei,
    x.family_key,
    x.total_obligation as entity_graph_total,
    coalesce(w.warehouse_total, 0) as warehouse_total
from touched t
join {{ ref('entity_xwalk') }} x on x.recipient_uei = t.recipient_uei
left join warehouse w on w.recipient_uei = t.recipient_uei
where abs(coalesce(x.total_obligation, 0) - coalesce(w.warehouse_total, 0)) > 0.01
{%- else -%}
-- ROADMAP #133: this build retired no award copy, so no entity total can
-- count one.
select
    cast(null as varchar) as recipient_uei,
    cast(null as varchar) as family_key,
    cast(null as double) as entity_graph_total,
    cast(null as double) as warehouse_total
where false
{%- endif %}
