-- Conservation (families piece 1, spec §4.5 and V3): for every edition and
-- slug, the program grains that carry era rows (map_basis era_line_map /
-- era_history_only) hold exactly the dollars and the source rows of the
-- fct_decade_series era grains whose keys the map carries (decision
-- same_program or history_only) — no era key dropped, double-counted, or
-- withheld by the lake-verifiability filter, and nothing excluded or
-- undecided leaking in. Per (edition_year, amount_type_kind, amount_type).
-- Amounts are whole thousands (see assert_program_decade_native_equals_line),
-- so the 0.5 tolerance only absorbs representation, never a real dollar.
--
-- Two legs (fix round 1): the dollar/row-count leg below sums
-- era_line_map and era_history_only TOGETHER, so relabelling one as the
-- other leaves its sums untouched and would pass silently. The second leg
-- re-reads every grain's own source_keys against p1_era_line_map.decision
-- and fails when a grain's recorded map_basis disagrees with what its
-- summed keys were actually decided — the check a relabelled grain cannot
-- pass. Columns amount_type_kind/amount_type are reused on that leg to carry
-- the disagreeing grain's map_basis and era_key; line_amount, program_amount,
-- line_rows and program_rows are not meaningful there and are NULL.
with carried as (
    select edition, era_key
    from {{ ref('p1_era_line_map') }}
    where decision in ('same_program', 'history_only')
),
line as (
    select
        f.edition_year,
        f.amount_type_kind,
        f.amount_type,
        sum(f.amount) as amount,
        sum(f.n_source_rows) as n_source_rows
    from {{ ref('fct_decade_series') }} f
    join carried k
      on k.era_key = f.pe_bli
     and k.edition = f.edition_year
    group by f.edition_year, f.amount_type_kind, f.amount_type
),
program as (
    select
        edition_year,
        amount_type_kind,
        amount_type,
        sum(amount) as amount,
        sum(n_source_rows) as n_source_rows
    from {{ ref('fct_program_decade_series') }}
    where map_basis in ('era_line_map', 'era_history_only')
    group by edition_year, amount_type_kind, amount_type
),

-- Every era key summed into an era grain (source_keys, comma-split), paired
-- with the map_basis its grain was recorded under.
basis_keys as (
    select p.edition_year, p.map_basis, u.k as era_key
    from {{ ref('fct_program_decade_series') }} p,
         unnest(string_split(p.source_keys, ',')) as u(k)
    where p.map_basis in ('era_line_map', 'era_history_only')
)

select
    'era grain does not conserve the fct_decade_series era grains it carries' as failure,
    coalesce(l.edition_year, p.edition_year) as edition_year,
    coalesce(l.amount_type_kind, p.amount_type_kind) as amount_type_kind,
    coalesce(l.amount_type, p.amount_type) as amount_type,
    l.amount as line_amount,
    p.amount as program_amount,
    l.n_source_rows as line_rows,
    p.n_source_rows as program_rows
from line l
full outer join program p
  on p.edition_year = l.edition_year
 and p.amount_type_kind = l.amount_type_kind
 and p.amount_type = l.amount_type
where l.amount is null
   or p.amount is null
   or abs(l.amount - p.amount) > 0.5
   or l.n_source_rows <> p.n_source_rows

union all

select
    'grain map_basis disagrees with the decision of a summed source key' as failure,
    bk.edition_year,
    bk.map_basis as amount_type_kind,
    bk.era_key as amount_type,
    cast(null as double) as line_amount,
    cast(null as double) as program_amount,
    cast(null as bigint) as line_rows,
    cast(null as bigint) as program_rows
from basis_keys bk
left join {{ ref('p1_era_line_map') }} m
  on m.era_key = bk.era_key
 and m.edition = bk.edition_year
where (bk.map_basis = 'era_line_map' and coalesce(m.decision, '') <> 'same_program')
   or (bk.map_basis = 'era_history_only' and coalesce(m.decision, '') <> 'history_only')
