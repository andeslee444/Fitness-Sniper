-- Every era key prints exactly one budget line code, one title and one budget
-- activity, and cites one workbook (families piece 1, spec §3 and §7; the
-- loader's tripwire, EraKeyConflict, re-checked downstream of Postgres and the
-- lake export). Read from staging, not from the map: the map takes min() of
-- each, which would hide a second value.
select
    fiscal_year as edition,
    pe_bli as era_key,
    count(distinct line_item_code) as codes,
    count(*) filter (where line_item_code is null) as rows_without_code,
    count(distinct coalesce(title, '')) as titles,
    count(distinct coalesce(budget_activity, '')) as budget_activities,
    count(distinct source_document_id) as documents
from {{ ref('stg_budget_lines') }}
where exhibit = 'P-1'
  and fiscal_year between 2017 and 2023
  and regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
group by fiscal_year, pe_bli
having count(distinct line_item_code) <> 1
    or count(*) filter (where line_item_code is null) > 0
    or count(distinct coalesce(title, '')) <> 1
    or count(distinct coalesce(budget_activity, '')) <> 1
    or count(distinct source_document_id) <> 1
