-- fct_program_decade_series grain (families piece 1, spec §4.5). Two legs:
--
--   * duplicate grain: (program_key, account, organization, fy,
--     edition_year, map_basis) is unique. Era lines sharing a code, or two
--     era chains pinned to the same side of a collision, must SUM into one
--     row per map_basis, never publish two.
--   * two rows a page reads share one grain: among the rows pages read
--     (map_basis 'native' and 'era_line_map'), the five columns without
--     map_basis — fct_decade_series' own uniqueness key with pe_bli renamed
--     — are unique. An 'era_history_only' row may share its five columns
--     with an 'era_line_map' row (a history-only chain printing the same
--     code in the same edition as a same_program chain: '10' in PB2018 and
--     '15' in PB2021–PB2023, if review decides them that way). A native row
--     and an era_line_map row may not (measured 2026-10-02: no era code
--     equals an R-1 program element in any edition).
select
    'duplicate grain' as failure,
    program_key,
    account,
    organization,
    fy,
    edition_year,
    map_basis,
    count(*) as n
from {{ ref('fct_program_decade_series') }}
group by program_key, account, organization, fy, edition_year, map_basis
having count(*) > 1

union all

select
    'two rows a page reads share one grain',
    program_key,
    account,
    organization,
    fy,
    edition_year,
    string_agg(map_basis, ',' order by map_basis),
    count(*)
from {{ ref('fct_program_decade_series') }}
where map_basis in ('native', 'era_line_map')
group by program_key, account, organization, fy, edition_year
having count(*) > 1
