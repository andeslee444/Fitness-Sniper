-- p1_era_line_map covers every era key and nothing else (families piece 1,
-- spec §4.4, V3 "coverage ≠ 6,927").
--
-- Relational legs (always on): every PB2017–PB2023 P-1 era key in staging is
-- in the map and every map key is in staging; every map row carries its
-- workbook sha and its column-I cells.
--
-- Full-corpus legs (on only when the lake registers all seven era P-1
-- workbooks, fy2017..fy2023/dod/p1_display.xlsx — the real corpus; the
-- tests/test_dbt_build.py fixture lake registers none, so a committed seed
-- written against the real corpus cannot fail the fixture build):
--   * per-edition key counts equal the measured corpus: 969 / 1,029 / 989 /
--     975 / 1,005 / 993 / 967 = 6,927 (measured 2026-10-02 from
--     data/parquet/jbooks/budget_lines.parquet, exhibit P-1, era-key pe_bli);
--   * every seed decision covers exactly the n_keys keys it was reviewed
--     over — a decision that binds no key (a typo, a stale range) or binds a
--     different number of keys fails here.
with registered as (
    select count(distinct rel_path) as n
    from {{ source('lake', 'jbook_documents') }}
    where rel_path in (
        'fy2017/dod/p1_display.xlsx', 'fy2018/dod/p1_display.xlsx',
        'fy2019/dod/p1_display.xlsx', 'fy2020/dod/p1_display.xlsx',
        'fy2021/dod/p1_display.xlsx', 'fy2022/dod/p1_display.xlsx',
        'fy2023/dod/p1_display.xlsx'
    )
),

expected (edition, n_keys) as (
    values (2017, 969), (2018, 1029), (2019, 989), (2020, 975),
           (2021, 1005), (2022, 993), (2023, 967)
),

actual as (
    select edition, count(*) as n_keys
    from {{ ref('p1_era_line_map') }}
    group by edition
),

lake_keys as (
    select distinct fiscal_year as edition, pe_bli as era_key
    from {{ ref('stg_budget_lines') }}
    where exhibit = 'P-1'
      and fiscal_year between 2017 and 2023
      and regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
),

map_keys as (
    select edition, era_key, source_document_sha256, source_cells
    from {{ ref('p1_era_line_map') }}
),

seed_bound as (
    select
        s.decision_id,
        try_cast(s.n_keys as integer) as n_keys,
        count(m.era_key) as bound_keys
    from {{ ref('p1_era_code_decisions') }} s
    left join {{ ref('p1_era_line_map') }} m
      on m.decision_id = s.decision_id
    group by s.decision_id, try_cast(s.n_keys as integer)
)

select
    'edition key count differs from the full corpus' as failure,
    cast(e.edition as varchar) as subject,
    cast(e.n_keys as varchar) as expected,
    cast(coalesce(a.n_keys, 0) as varchar) as actual
from expected e
left join actual a
  on a.edition = e.edition
where (select n from registered) = 7
  and coalesce(a.n_keys, 0) <> e.n_keys

union all

select
    'lake era key missing from the map',
    cast(l.edition as varchar) || '/' || l.era_key,
    null,
    null
from lake_keys l
left join map_keys m
  on m.edition = l.edition
 and m.era_key = l.era_key
where m.era_key is null

union all

select
    'map key not in the lake',
    cast(m.edition as varchar) || '/' || m.era_key,
    null,
    null
from map_keys m
left join lake_keys l
  on l.edition = m.edition
 and l.era_key = m.era_key
where l.era_key is null

union all

select
    'map key without its workbook sha or cells',
    cast(m.edition as varchar) || '/' || m.era_key,
    null,
    coalesce(m.source_document_sha256, '<null sha>') || ' ' || coalesce(m.source_cells, '<null cells>')
from map_keys m
where m.source_document_sha256 is null
   or m.source_cells is null

union all

select
    'decision covers a different number of keys than were reviewed',
    b.decision_id,
    cast(b.n_keys as varchar),
    cast(b.bound_keys as varchar)
from seed_bound b
where (select n from registered) = 7
  and b.bound_keys is distinct from b.n_keys
