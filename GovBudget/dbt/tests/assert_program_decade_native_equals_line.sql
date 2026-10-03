-- Native parity (families piece 1, spec §4.5): every fct_program_decade_series
-- row that involves no era row (map_basis = 'native') equals its
-- fct_decade_series row column for column, in EVERY edition — PB2024–PB2026
-- R-1 and P-1, and the 22,008 PB2017–PB2023 R-1 grains (measured
-- 2026-10-02: 38,398 native grains in all). The book-diff join and the
-- exporter's derived-ID mirror depend on it.
--
-- Checked both ways: a fct_decade_series grain that is not an era key must
-- appear in the program table as a native row, and a native program row
-- must have a fct_decade_series twin. Amounts compare exactly: every lake
-- amount is a whole number of thousands (measured 2026-10-02: 0 of 159,494
-- budget_lines rows carry a fraction), so both double sums are exact.
with line as (
    select *
    from {{ ref('fct_decade_series') }}
    where not regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
),
native as (
    select *
    from {{ ref('fct_program_decade_series') }}
    where map_basis = 'native'
)

select
    'fct_decade_series grain missing from the program table' as failure,
    l.pe_bli as program_key, l.account, l.organization, l.fy, l.edition_year
from line l
left join native n
  on n.program_key = l.pe_bli
 and n.account is not distinct from l.account
 and n.organization is not distinct from l.organization
 and n.fy = l.fy
 and n.edition_year = l.edition_year
where n.program_key is null

union all

select
    'native program row without a fct_decade_series twin',
    n.program_key, n.account, n.organization, n.fy, n.edition_year
from native n
left join line l
  on l.pe_bli = n.program_key
 and l.account is not distinct from n.account
 and l.organization is not distinct from n.organization
 and l.fy = n.fy
 and l.edition_year = n.edition_year
where l.pe_bli is null

union all

select
    'native program row differs from fct_decade_series',
    n.program_key, n.account, n.organization, n.fy, n.edition_year
from native n
join line l
  on l.pe_bli = n.program_key
 and l.account is not distinct from n.account
 and l.organization is not distinct from n.organization
 and l.fy = n.fy
 and l.edition_year = n.edition_year
where l.amount_type_kind is distinct from n.amount_type_kind
   or l.amount is distinct from n.amount
   or l.amount_thousands is distinct from n.amount_thousands
   or l.scenario is distinct from n.scenario
   or l.amount_type is distinct from n.amount_type
   or l.n_source_rows is distinct from n.n_source_rows
   or l.source_fact_id is distinct from n.source_fact_id
   or n.source_keys is not null
