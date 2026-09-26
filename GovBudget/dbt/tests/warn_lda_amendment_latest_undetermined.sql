/*
  R-DEC-AMEND (2026-09-26) — WARN severity, by design: the count is the point.

  One row per (registrant, client, quarter) whose amendments DISAGREE on the
  figures they report. The lake carries no posting date, so the latest
  amendment cannot be named; audit_lda_filings counts the quarter from the
  amendment reporting the smallest total (never more than the latest one
  reports). That must never be silent: dbt prints
  "WARN <n> warn_lda_amendment_latest_undetermined" and "Got <n> results" in
  the build log. Keeping the LDA API's posting timestamp in
  influence/lda.py's trimmed filing would make "latest" exact and this 0.
*/
{{ config(severity='warn') }}

select
    registrant_name,
    client_name,
    filing_year,
    filing_period,
    count(*) filter (where resolution in ('amendment_counted',
                                          'amendment_superseded')) as amendments,
    max(filing_uuid) filter (where resolution = 'amendment_counted')
        as counted_filing_uuid,
    max(match_method) as match_method,
    max(family_key_guess) as family_key_guess
from {{ ref('audit_lda_filings') }}
where latest_determinable = false
group by all
