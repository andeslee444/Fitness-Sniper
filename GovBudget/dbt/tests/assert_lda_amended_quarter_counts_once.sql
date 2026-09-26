/*
  R-DEC-AMEND (2026-09-26): an amended (registrant, client, quarter) is
  counted exactly once, from one amendment. Returns every amended quarter
  whose counted filings are not exactly one amendment — a regression that
  would count a report beside its amendment again (fails the build).
*/
select
    registrant_name,
    client_name,
    filing_year,
    filing_period,
    count(*) filter (where counted) as counted_filings,
    count(*) filter (where resolution = 'amendment_counted') as counted_amendments
from {{ ref('audit_lda_filings') }}
where resolution in ('superseded_by_amendment', 'amendment_counted',
                     'amendment_superseded')
group by all
having count(*) filter (where counted) <> 1
    or count(*) filter (where resolution = 'amendment_counted') <> 1
