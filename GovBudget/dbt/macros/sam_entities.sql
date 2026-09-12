{#
  sam_entities_relation() — the SAM.gov registration lake, or a typed hole.

  ROADMAP #10. `dim_entities` LEFT JOINs `source('lake','sam_entities')`, whose
  parquet is written by `govbudget sam extract` behind a key only an account
  holder can mint. Today that file does not exist on any machine.

  A missing parquet is NOT a soft failure in DuckDB: `create view … from
  read_parquet('missing.parquet')` raises at VIEW-CREATION time ("IO Error: No
  files found that match the pattern"), and every mart here is a view
  (dbt_project.yml `+materialized: view`), with fct_influence refing
  dim_entities — so an absent extract would take down the whole export, not
  just one column. Measured on duckdb 1.5.3, 2026-09-12; the Task 19 brief
  assumed the opposite ("a missing parquet does not fail dbt build") and it is
  wrong.

  So the presence check happens at COMPILE time, against the same path the
  source declares (parsed out of the source's own rendered external_location,
  so the path is defined once, in sources.yml, and cannot drift):

    * file present  → the source relation; sam_* columns carry its values.
    * file absent   → a typed zero-row relation with the same column names;
                      the LEFT JOIN matches nothing and every sam_* is NULL.

  Both states are gated: verify-phase2 leg e4 prints which one this warehouse
  is in and passes in both, and tests/test_dbt_build.py builds the fixture lake
  each way.
#}
{% macro sam_entities_relation() %}
  {%- set rendered = source('lake', 'sam_entities') | string -%}
  {%- set match = modules.re.search("'([^']+)'", rendered) -%}
  {%- set path = match.group(1) if match else '' -%}
  {%- set found = 0 -%}
  {%- if execute and path -%}
    {%- set probe = run_query("select count(*) from glob('" ~ path ~ "')") -%}
    {%- set found = probe.columns[0].values()[0] -%}
  {%- endif -%}
  {%- if found > 0 -%}
{{ rendered }}
  {%- else -%}
(select
     null::varchar as sam_uei,
     null::varchar as legal_business_name,
     null::varchar as cage_code,
     null::varchar as registration_status,
     null::varchar as registration_expiration_date,
     null::varchar as business_types,
     null::varchar as primary_naics,
     null::varchar as public_url,
     null::varchar as source_url,
     null::varchar as retrieved_at,
     null::varchar as response_sha256
 where false)
  {%- endif -%}
{% endmacro %}
