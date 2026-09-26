-- dim_lobbyists: one row per unique lobbyist name, with filing count and
-- revolving_door flag derived from covered_position disclosure.
--
-- revolving_door = true when covered_position is non-empty and not 'N/A'
-- (statutory disclosure of prior executive/legislative branch position).
-- This flag mirrors the public LDA disclosure; no additional inference.
with lobbyists as (
    select
        name,
        covered_position,
        count(*) as filing_appearances
    from {{ source('influence', 'lda_lobbyists') }}
    where name is not null
      and name <> ''
    group by name, covered_position
),
aggregated as (
    select
        name,
        -- A disclosed covered_position wins over an empty/N/A one, then the
        -- position disclosed on the most filings, then — the tiebreak —
        -- the position text itself (NULL last). The order must be TOTAL:
        -- without the last key two positions tied on the first two came back
        -- in whatever order the sort emitted them, and chain F2 (2026-09-25)
        -- measured 14 lobbyist fact ids changing between two rebuilds of one
        -- lake (the exporter mints the fact id from the filing that discloses
        -- THIS position, so a /fact/ link could break between deploys).
        -- tests/test_dbt_lobbyists_tiebreak.py pins it.
        first_value(covered_position) over (
            partition by name
            order by
                case when covered_position is not null
                          and covered_position <> ''
                          and upper(covered_position) <> 'N/A'
                     then 0 else 1 end,
                filing_appearances desc,
                covered_position asc nulls last
        ) as covered_position,
        sum(filing_appearances) as filings_count
    from lobbyists
    group by name, covered_position, filing_appearances
)
select
    name,
    max(covered_position)   as covered_position,
    sum(filings_count)      as filings_count,
    -- revolving_door: disclosed prior government service position
    bool_or(
        covered_position is not null
        and covered_position <> ''
        and upper(covered_position) <> 'N/A'
    )                       as revolving_door
from aggregated
group by name
