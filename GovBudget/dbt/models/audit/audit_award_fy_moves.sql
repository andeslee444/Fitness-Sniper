-- audit_award_fy_moves — one row per transaction the fiscal-year move rule
-- resolved (ROADMAP #133): the copy the build KEEPS and the copy it RETIRES,
-- each with its fiscal-year archive, its source revision time and the part
-- file it sits in. The staging models drop exactly the retired side of these
-- rows and nothing else; see audit_award_duplicate_copies for the rule and for
-- the ambiguous duplicates, which are never listed here and fail the build.
--
-- Empty on a lake the manual reconcile (scripts/reconcile_award_moves.py) has
-- already cleaned — the 81 rows of 2026-09-24 are gone from the parquet, so
-- there is nothing left to retire. warn_award_fy_moves_retired prints this
-- model's row count in every `dbt build` log where it is not zero.
select
    r.award_type,
    r.transaction_key,
    k.fiscal_year as kept_fiscal_year,
    k.last_modified_date as kept_last_modified_date,
    k.source_file as kept_file,
    r.fiscal_year as retired_fiscal_year,
    r.last_modified_date as retired_last_modified_date,
    r.source_file as retired_file
from {{ ref('audit_award_duplicate_copies') }} r
join {{ ref('audit_award_duplicate_copies') }} k
  on k.award_type = r.award_type
 and k.transaction_key = r.transaction_key
 and k.resolution = 'keep'
where r.resolution = 'retire'
