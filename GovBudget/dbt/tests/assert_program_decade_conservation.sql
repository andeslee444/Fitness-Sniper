-- Conservation (families piece 1, spec §4.5 and V3): for every edition and
-- slug, the program grains that carry era rows (map_basis era_line_map /
-- era_history_only) hold exactly the dollars and the source rows of the
-- fct_decade_series era grains whose keys the map carries (decision
-- same_program or history_only) — no era key dropped, double-counted, or
-- withheld by the lake-verifiability filter, and nothing excluded or
-- undecided leaking in. Per (edition_year, amount_type_kind, amount_type).
-- Amounts are whole thousands (see assert_program_decade_native_equals_line),
-- so the 0.5 tolerance only absorbs representation, never a real dollar.
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
)

select
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
