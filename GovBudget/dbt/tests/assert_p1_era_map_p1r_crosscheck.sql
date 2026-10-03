-- P-1R context cross-check (families piece 1, spec §7 "P-1R rows"): every
-- era P-1R (edition, account, printed code) triple must name a code the
-- edition's P-1 prints under that account — i.e. appear in p1_era_line_map —
-- except the five PB2017 Army triples below, whose codes the PB2017 P-1 does
-- not print (measured 2026-10-02: 1,645 of the 1,650 era P-1R triples match).
-- P-1R is never counted (it is the reserve-component subset of P-1); this
-- only proves the map reads the same codes the books print.
--
--   * an exception outside the allow-list fails (always on);
--   * an allow-listed triple that stopped being an exception fails, so the
--     list stays exact (on when the lake registers the PB2017 P-1 and P-1R
--     workbooks — the real corpus);
--   * the era P-1R triple count must stay 1,650 (on when the lake registers
--     all seven era P-1R workbooks).
with docs as (
    select distinct rel_path
    from {{ source('lake', 'jbook_documents') }}
),
allow_list (edition, account, line_item_code, reason) as (
    values
        (2017, '2033A', '8190G01506', 'Precision Sniper Rifle: in the PB2017 P-1R only; the P-1 prints it from PB2020'),
        (2017, '2033A', '8635G15325', 'Handgun: in the PB2017 P-1R only; the P-1 prints it from PB2018'),
        (2017, '2035A', '4000M12800', 'WATER PURIFICATION UNIT REVERSE OSMOSIS ENHAN: in the PB2017 P-1R only; no PB2017-PB2023 P-1 prints it'),
        (2017, '2035A', '9221F00001', 'Unmanned Ground Vehicle: in the PB2017 P-1R only; no PB2017-PB2023 P-1 prints it'),
        (2017, '2035A', '9693B01001', 'DCGS-A (MIP): in the PB2017 P-1R only; no PB2017-PB2023 P-1 prints it')
),
p1r as (
    select distinct fiscal_year as edition, account, pe_bli as line_item_code
    from {{ ref('stg_budget_lines') }}
    where exhibit = 'P-1R'
      and fiscal_year between 2017 and 2023
),
map_codes as (
    select distinct edition, account, line_item_code
    from {{ ref('p1_era_line_map') }}
),
exceptions as (
    select p.edition, p.account, p.line_item_code
    from p1r p
    left join map_codes m
      on m.edition = p.edition
     and m.account = p.account
     and m.line_item_code = p.line_item_code
    where m.line_item_code is null
)

select
    'P-1R triple absent from the era map and not allow-listed' as failure,
    e.edition, e.account, e.line_item_code
from exceptions e
left join allow_list a
  on a.edition = e.edition
 and a.account = e.account
 and a.line_item_code = e.line_item_code
where a.line_item_code is null

union all

select
    'allow-listed triple is no longer an exception',
    a.edition, a.account, a.line_item_code
from allow_list a
left join exceptions e
  on e.edition = a.edition
 and e.account = a.account
 and e.line_item_code = a.line_item_code
where e.line_item_code is null
  and exists (select 1 from docs where rel_path = 'fy2017/dod/p1_display.xlsx')
  and exists (select 1 from docs where rel_path = 'fy2017/dod/p1r_display.xlsx')

union all

select
    'era P-1R triple count differs from the full corpus (1,650): ' || cast(count(*) as varchar),
    cast(null as integer), cast(null as varchar), cast(null as varchar)
from p1r
having count(*) <> 1650
   and (select count(*) from docs where rel_path in (
        'fy2017/dod/p1r_display.xlsx', 'fy2018/dod/p1r_display.xlsx',
        'fy2019/dod/p1r_display.xlsx', 'fy2020/dod/p1r_display.xlsx',
        'fy2021/dod/p1r_display.xlsx', 'fy2022/dod/p1r_display.xlsx',
        'fy2023/dod/p1r_display.xlsx')) = 7
