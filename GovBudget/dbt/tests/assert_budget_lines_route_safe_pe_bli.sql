-- No budget_lines row is keyed by a code a web address cannot carry
-- (families piece-1 follow-ups design §4.4, #194). A program page is a static
-- route keyed by pe_bli, so '&', '#', '/', '?', '%' or whitespace in one is a
-- page that cannot exist or a total that counts an unpublished line. Until
-- the #194 write (scripts/era/s194_chem_demil.py --apply) 16 PB2024-PB2025
-- rows held 0390D's printed codes 'O&M' and 'RDT&E'; the loader now keys O&M
-- by its route-safe page key (dbt/seeds/p1_route_safe_codes.csv) and keeps
-- the RDT&E restatement out, and raises on any other such code.
select
    'route-unsafe pe_bli in budget_lines' as failure,
    exhibit,
    fiscal_year,
    account,
    pe_bli,
    count(*) as n_rows
from {{ ref('stg_budget_lines') }}
where regexp_matches(pe_bli, '[&#/?%[:space:]]')
group by exhibit, fiscal_year, account, pe_bli
