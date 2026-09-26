-- audit_link_grading — EVERY budget->award crosswalk link (every
-- budget_line_awards row, published or not) with the tier it publishes under
-- and, where a rule moved it, why. fct_budget_to_awards publishes exactly the
-- rows graded high or medium here; nothing is graded anywhere else.
--
--   crosswalk_confidence  the loader's grade, never rewritten
--   confidence            the published grade: the adjudication overlay
--                         (migration 010) over the loader's grade, then the
--                         demotions below. 'low' and 'reject' do not publish.
--   confidence_source     'adjudicated' when an award_pe_adjudications row
--                         reviewed this pair, else 'mechanical'
--   demotion_reason       NULL unless a rule below moved the grade:
--
--   account_tokens_unadjudicated   (#75 addendum ruling 3, 2026-09-04) an
--       account+tokens link graded high that no adjudication reviewed
--       publishes at medium — token overlap alone is not evidence-graded.
--   account_subagency_not_pinned   (#107(b), owner-delegated 2026-09-25) the
--       account+subagency tier measured 0 of 60 on program attribution
--       (sample 2026-09-05, judged 2026-09-11), so it leaves the published
--       tiers — graded 'low', which the mart filters; Postgres keeps every row
--       — EXCEPT a pair a two-lens adjudication pinned: award_verdict
--       'pinned', pair_reason 'pinned-here', both refuter lenses passed.
--       Measured read-only 2026-09-25: 22 of the 8,855 published
--       account+subagency rows are that shape (all published high); the other
--       8,833 are 'darpa_unpinned'/'unpinned-pool' (8,389), 'pinned' awards
--       whose pin is on another PE and whose pair sits in the unpinned pool
--       (279 — the LORELEI shape #141 is for), 'pin-refuted' (1) or carry no
--       adjudication at all (164). None of those pins THIS pair.
--   announcement_review_* / announcement_reviewer_rejected (#110,
--       owner-delegated 2026-09-25; R-DEC-110, controller 2026-09-26) an
--       unadjudicated announcement+lexicon link graded high stays high only
--       when BOTH hold for its jbook_announcement_link_reviews records (the
--       records of THIS link: award_piid, pe_bli, exhibit, fiscal_year):
--         (a) a record upholds it — reviewer 'link' AND adversarial 'upheld',
--             of any record_kind: a wave-4 'verdict_pair' or a wave 1-3
--             'survivor_list' entry (R-DEC-110: a surviving entry records the
--             reviewer's link and its survival of the refuter; a wave 1-2
--             'refutation_sample' entry is always link + refuted), and
--         (b) no record with reviewer 'weak'/'wrong' or adversarial 'refuted'
--             targets the article the link's card cites: a record binds when
--             cites_reviewed_article = 'True' (the backfill's comparison of the
--             record's article_id with the link's award_link_sources article),
--             when that comparison is missing, or when the record names no
--             article_id at all (it then binds to the pair). Measured on the
--             R-DEC-110 backfill shape 2026-09-26, every binding contrary
--             record names the cited article itself (18 links, each a wave 1-2
--             survivor a wave-4 reviewer rejected or refuted on the same
--             article). A contrary record about ANOTHER
--             article of the pair does
--             not bind; an 'incomplete' adversarial read is neither a
--             rejection nor a refutation, so it never binds (R-DEC-INCOMPLETE:
--             it is not an uphold either — alone it demotes with
--             announcement_review_incomplete).
--       "Record" means a jbook_announcement_link_reviews row and nothing
--       else: the announcement pipeline's own wave 1-4 reviews. The held-out
--       precision study (Postgres link_precision_samples) is NOT a grading
--       input — it is the independent measurement of the published tier, and
--       grading on it would bias the precision figure it publishes. So a link
--       can publish high while a precision sample refuted it: measured
--       read-only 2026-09-26, 10 of the 15 announcement links the 2026-09-04
--       and 2026-09-12 samples refuted (rubric 'attribution') publish high,
--       both on the deployed mart and in chain order; the other 5 are no
--       longer budget_line_awards rows. No sentence may say that no high link
--       carries a recorded refutation without naming this scope.
--       Otherwise the link publishes at medium with the reason its records
--       give, first match wins:
--         announcement_review_refuted     a binding record was refuted, or —
--                                         with no upholding record — any
--                                         record of the link was refuted
--         announcement_reviewer_rejected  the same, for a reviewer 'weak' /
--                                         'wrong'
--         announcement_review_incomplete  records exist, none upholds, none
--                                         refutes or rejects (adversarial
--                                         'incomplete', or a 'link' no lens
--                                         answered: 'not_run')
--         announcement_review_unrecorded  no record of the link at all
--       An adjudication row is itself a recorded review, so an adjudicated
--       link keeps its adjudicated grade and this rule does not apply to it.
--
-- Demotions only ever move a link DOWN (high → medium, or out of the
-- published tiers); a grade the adjudication overlay already set to low or
-- reject stays that grade with no demotion_reason (the adjudication is the
-- reason, recorded in award_verdict / pair_reason).
with adjudications as (
    select award_piid, pe_bli, adjudicated_confidence, award_verdict,
           pair_reason, basis as adjudication_basis,
           try_cast(refuter_lenses_passed as integer) as refuter_lenses_passed
    from {{ source('lake', 'jbook_award_adjudications') }}
),
-- One row per reviewed link, so several review records (a pair two waves
-- both reviewed, or proposed from several articles) can never fan a link out.
review_records as (
    select
        *,
        reviewer_verdict in ('weak', 'wrong') as rejects,
        adversarial_verdict = 'refuted' as refutes,
        -- does this record speak about the article the link's card cites?
        -- A record naming no article (NULL, or '' in the all-varchar parquet)
        -- binds to the pair; so does one whose article match is unknown
        -- (cites_reviewed_article NULL) — read against the card, never wider.
        case
            when coalesce(trim(article_id), '') = '' then true
            else coalesce(cites_reviewed_article, 'True') = 'True'
        end as binds
    from {{ source('lake', 'jbook_announcement_link_reviews') }}
),
reviews as (
    select
        award_piid,
        pe_bli,
        exhibit,
        cast(fiscal_year as integer) as fiscal_year,
        bool_or(reviewer_verdict = 'link' and adversarial_verdict = 'upheld')
            as upheld,
        bool_or(refutes and binds) as cited_refuted,
        bool_or(rejects and binds) as cited_rejected,
        bool_or(refutes) as any_refuted,
        bool_or(rejects) as any_rejected
    from review_records
    group by 1, 2, 3, 4
),
overlaid as (
    select
        a.pe_bli,
        a.exhibit,
        cast(a.fiscal_year as integer) as fiscal_year,
        a.organization,
        a.award_piid,
        a.recipient_name,
        a.recipient_uei,
        a.method,
        a.account,
        a.confidence as crosswalk_confidence,
        coalesce(adj.adjudicated_confidence, a.confidence) as overlay_confidence,
        adj.award_piid is not null as adjudicated,
        coalesce(
            adj.award_verdict = 'pinned'
            and adj.pair_reason = 'pinned-here'
            and adj.refuter_lenses_passed = 2,
            false
        ) as two_lens_pinned,
        r.award_piid is not null as review_recorded,
        coalesce(r.upheld, false) as review_upheld,
        coalesce(r.cited_refuted, false) as review_cited_refuted,
        coalesce(r.cited_rejected, false) as review_cited_rejected,
        coalesce(r.any_refuted, false) as review_any_refuted,
        coalesce(r.any_rejected, false) as review_any_rejected,
        adj.award_verdict,
        adj.pair_reason,
        adj.adjudication_basis
    from {{ source('lake', 'jbook_awards') }} a
    left join adjudications adj
      on adj.award_piid = a.award_piid and adj.pe_bli = a.pe_bli
    left join reviews r
      on r.award_piid = a.award_piid
     and r.pe_bli = a.pe_bli
     and r.exhibit = a.exhibit
     and r.fiscal_year = cast(a.fiscal_year as integer)
),
reasoned as (
    select
        *,
        case
            when overlay_confidence not in ('high', 'medium') then null
            when method = 'account+subagency' and not two_lens_pinned
                then 'account_subagency_not_pinned'
            when not adjudicated
             and method = 'account+tokens'
             and crosswalk_confidence = 'high'
                then 'account_tokens_unadjudicated'
            when not adjudicated
             and method = 'announcement+lexicon'
             and overlay_confidence = 'high'
             and (not review_upheld
                  or review_cited_refuted
                  or review_cited_rejected)
                then case
                    when review_cited_refuted then 'announcement_review_refuted'
                    when review_cited_rejected then 'announcement_reviewer_rejected'
                    when review_any_refuted then 'announcement_review_refuted'
                    when review_any_rejected then 'announcement_reviewer_rejected'
                    when review_recorded then 'announcement_review_incomplete'
                    else 'announcement_review_unrecorded'
                end
        end as demotion_reason
    from overlaid
)
select
    pe_bli,
    exhibit,
    fiscal_year,
    organization,
    award_piid,
    recipient_name,
    recipient_uei,
    method,
    account,
    case demotion_reason
        when 'account_subagency_not_pinned' then 'low'
        when 'account_tokens_unadjudicated' then 'medium'
        when 'announcement_review_refuted' then 'medium'
        when 'announcement_reviewer_rejected' then 'medium'
        when 'announcement_review_incomplete' then 'medium'
        when 'announcement_review_unrecorded' then 'medium'
        else overlay_confidence
    end as confidence,
    crosswalk_confidence,
    case when adjudicated then 'adjudicated' else 'mechanical' end
        as confidence_source,
    demotion_reason,
    award_verdict,
    pair_reason,
    adjudication_basis
from reasoned
