{#
  award_fy_move_filter(award_type, key_column, src_alias) — the WHERE clause
  that drops the copies the fiscal-year move rule retired (ROADMAP #133,
  owner-delegated ruling 2026-09-25), or nothing when this build retired none.

  audit_award_duplicate_copies decides which copy of a moved transaction is
  retired; audit_award_fy_moves lists each retired copy (key, fiscal-year
  archive, last_modified_date). The staging views over the award archives
  (stg_contracts, stg_assistance, stg_flow_contracts) and the flow
  conservation assertion drop exactly those copies through this clause.

  WHY IT IS DECIDED AT BUILD TIME. The exclusion needs each row's key and
  source revision time, so an unconditional anti-join makes every query over
  the award lake read two wide varchar columns it otherwise never touches —
  measured read-only 2026-09-25 on the real lake: a full aggregate over
  fct_award_transactions 0.26 s → 1.4–2.3 s, fct_program_concentration
  1.3 s → 4.1–4.5 s. On a lake with nothing to retire (every lake the manual
  reconcile cleaned, including today's) that cost buys nothing, so the probe
  below reads the move list when the model is built — after the move list
  itself, which the staging models depend on — and emits the clause only when
  there is a copy of this award type to drop. The same pattern as
  sam_entities_relation(): a compile-time probe, the relation decides.

  Staleness is loud, not silent: the move list is a table rebuilt by every
  `dbt build`, the views read the live parquet, and a lake that gains a
  duplicate after the build fails unique_fct_award_transactions_transaction_key
  on the next `dbt test` exactly as before; assert_award_fy_moves_applied
  fails if a listed move no longer matches the warehouse.
#}
{% macro award_fy_move_filter(award_type, key_column, src_alias='src') %}
  {%- set moves = ref('audit_award_fy_moves') -%}
  {%- set retired = 1 -%}
  {%- if execute -%}
    {%- set probe = run_query(
        "select count(*) from " ~ moves ~ " where award_type = '" ~ award_type ~ "'"
    ) -%}
    {%- set retired = probe.columns[0].values()[0] -%}
  {%- endif -%}
  {%- if retired > 0 -%}
where not exists (
    select 1
    from {{ moves }} m
    where m.award_type = '{{ award_type }}'
      and m.transaction_key = {{ src_alias }}.{{ key_column }}
      and m.retired_fiscal_year = cast({{ src_alias }}.fy as integer)
      and m.retired_last_modified_date = {{ src_alias }}.last_modified_date
)
  {%- else -%}
-- ROADMAP #133: audit_award_fy_moves retired no {{ award_type }} copy in this
-- build, so no row is dropped here.
  {%- endif -%}
{% endmacro %}
