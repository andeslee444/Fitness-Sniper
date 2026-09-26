-- R-DEC-110b (controller ruling 2026-09-26, under the owner's 2026-09-25
-- delegation): "No known-refuted link at high." The held-out precision study's
-- refutations (Postgres link_precision_samples, verdict 'refuted', rubric
-- 'attribution') are recorded refutations; the backfill writes each into
-- jbook_announcement_link_reviews as record_kind 'precision_sample', on the
-- link rows the sample drew, and audit_link_grading demotes an announcement
-- link its sample refuted. Before the ruling, 10 announcement links a sample
-- refuted on attribution published high (measured read-only 2026-09-26) —
-- and nothing failed.
--
-- This gate reads the PUBLISHED mart for EVERY method, not only the
-- announcement tier the grading rule covers: a link an adjudication pinned
-- high while its held-out sample refuted it (none on 2026-09-26) is a
-- conflict between two recorded judgments that a person must rule on, so the
-- build stops rather than publishing either one silently. It reads a record on
-- the link it is attached to (award_piid, pe_bli, exhibit, fiscal_year), as
-- the grading does; the backfill decides which of a pair's rows a sample
-- speaks for (the rows of the method it drew), once.
--
-- Returned rows are the FAILURES (dbt singular test convention): one per
-- published high link carrying a precision-sample refutation.
with sample_refutations as (
    select award_piid, pe_bli, exhibit,
           cast(fiscal_year as integer) as fiscal_year,
           string_agg(distinct source_file, '; ' order by source_file)
               as refuted_in
    from {{ source('lake', 'jbook_announcement_link_reviews') }}
    where record_kind = 'precision_sample'
      and (adversarial_verdict = 'refuted'
           or reviewer_verdict in ('weak', 'wrong'))
    group by 1, 2, 3, 4
)
select
    f.award_piid,
    f.pe_bli,
    f.exhibit,
    f.fiscal_year,
    f.method,
    f.confidence_source,
    s.refuted_in
from {{ ref('fct_budget_to_awards') }} f
join sample_refutations s
  on s.award_piid = f.award_piid
 and s.pe_bli = f.pe_bli
 and s.exhibit = f.exhibit
 and s.fiscal_year = cast(f.fiscal_year as integer)
where f.confidence = 'high'
