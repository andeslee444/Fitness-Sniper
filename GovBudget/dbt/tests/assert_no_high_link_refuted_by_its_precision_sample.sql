-- R-DEC-110b (controller ruling 2026-09-26, under the owner's 2026-09-25
-- delegation): "No known-refuted link at high." The held-out precision study's
-- refutations (Postgres link_precision_samples, verdict 'refuted', rubric
-- 'attribution') are recorded refutations; the backfill writes each into
-- jbook_announcement_link_reviews as record_kind 'precision_sample', and
-- audit_link_grading demotes an unadjudicated link its sample refuted. Before
-- the ruling, 10 announcement links a sample refuted on attribution published
-- high (measured read-only 2026-09-26) — and nothing failed.
--
-- R-DEC-110c (fix-round-3 ruling, 2026-09-26): "A precision-study refutation
-- (rubric attribution) is a verdict on the award->PE PAIR: it binds to every
-- published method of the pair." So this gate reads a refutation per PAIR
-- (award_piid, pe_bli), as the grading does: whichever row(s) of the pair the
-- backfill attached it to, whatever tier the sample drew the link from (the
-- reason's head, never read here), and whatever method the link publishes
-- under today. FA880712C0012/1203164SF — drawn from the fpds-ap+account tier on
-- 2026-09-04, published as announcement+lexicon/high since 2026-09-19 — is the
-- shape R-DEC-110b's first reading let through.
--
-- It reads the PUBLISHED mart for EVERY method: a link an adjudication pinned
-- high while its held-out sample refuted the pair (none on 2026-09-26) is a
-- conflict between two recorded judgments that a person must rule on, so the
-- build stops rather than publishing either one silently.
--
-- Returned rows are the FAILURES (dbt singular test convention): one per
-- published high link whose pair carries a precision-sample refutation.
with sample_refutations as (
    select award_piid, pe_bli,
           string_agg(distinct source_file, '; ' order by source_file)
               as refuted_in
    from {{ source('lake', 'jbook_announcement_link_reviews') }}
    where record_kind = 'precision_sample'
      and (adversarial_verdict = 'refuted'
           or reviewer_verdict in ('weak', 'wrong'))
    group by 1, 2
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
where f.confidence = 'high'
