-- ROADMAP #133 (2026-09-25): every move audit_award_fy_moves lists reached the
-- warehouse exactly as listed — the kept copy present ONCE, in its fiscal
-- year, and the retired copy absent. audit_award_duplicate_copies is a table
-- (built once per `dbt build`) while the staging models are views over the
-- live parquet, so this is also the staleness check: a lake rewritten after
-- the build (a re-sync, a manual reconcile) can leave a listed move that no
-- longer matches the files, and the next `dbt test` says so here instead of a
-- key silently vanishing or doubling. Returns the offending moves.
with seen as (
    select award_type, transaction_key, fiscal_year, count(*) as n
    from {{ ref('fct_award_transactions') }}
    where transaction_key in (
        select transaction_key from {{ ref('audit_award_fy_moves') }}
    )
    group by 1, 2, 3
)
select
    m.award_type,
    m.transaction_key,
    m.kept_fiscal_year,
    m.retired_fiscal_year,
    s.fiscal_year as warehouse_fiscal_year,
    s.n as warehouse_rows
from {{ ref('audit_award_fy_moves') }} m
left join seen s
  on s.award_type = m.award_type
 and s.transaction_key = m.transaction_key
where s.transaction_key is null
   or s.fiscal_year <> m.kept_fiscal_year
   or s.n <> 1
