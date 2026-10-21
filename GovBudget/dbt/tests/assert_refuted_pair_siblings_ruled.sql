-- R-DEC-LINK-2026-10-21 (owner, 2026-10-21; verify.md 5.4 amendment 2): a
-- refutation must not reach one twin only without a person looking at the
-- other. R-DEC-110c binds a held-out precision-study refutation to its own
-- (award_piid, pe_bli) PAIR, and that stays the rule: this test propagates
-- nothing. But the 2026-09-04 study drew (N0001917C0001, 0593) — "Ann. is
-- Lot 12 F-35 production long-lead; 0593 narrative is F-35C Modifications
-- program" — and not its twin (N0001917C0001, 0592), which cites the SAME
-- announcement (1167080) and stayed published at high; likewise
-- (FA813423FB001, C04000), refuted as an O&M support task order, and its
-- twin on C03200 (article 3348502). Both twins were wrong (verify.md 1.1 W1,
-- W6) and nothing failed.
--
-- A FAILURE is a PUBLISHED link (fct_budget_to_awards) with no ruling in
-- dbt/seeds/link_line_rulings.csv that shares its award and the article its
-- card cites with a pair a precision sample refuted (record_kind
-- 'precision_sample', as audit_link_grading reads it), on another program
-- element, and is not itself refuted (its own refutation already moves it).
-- The article a card cites is read from the announcement pipeline's own
-- review records of the pair: a record whose cites_reviewed_article is
-- 'True' names it (the backfill compared it with the link's
-- award_link_sources row). A precision_sample record names no article, so a
-- refuted pair's article comes from its pipeline records too; a pair with
-- none cited (no announcement card) has no sibling by this rule.
--
-- A ruling is either word: `withdraw` (the sibling is wrong too) or `allow`
-- (a person read it and it stands).
--
-- Returned rows are the FAILURES (dbt singular test convention): one per
-- unruled sibling link, naming every refuted pair and shared article.
with reviews as (
    select * from {{ source('lake', 'jbook_announcement_link_reviews') }}
),
cited as (
    select distinct award_piid, pe_bli, trim(article_id) as article_id
    from reviews
    where record_kind <> 'precision_sample'
      and cites_reviewed_article = 'True'
      and coalesce(trim(article_id), '') <> ''
),
refuted as (
    select award_piid, pe_bli
    from reviews
    where record_kind = 'precision_sample'
      and (adversarial_verdict = 'refuted'
           or reviewer_verdict in ('weak', 'wrong'))
    group by 1, 2
),
refuted_cited as (
    select c.award_piid, c.pe_bli, c.article_id
    from refuted r
    join cited c
      on c.award_piid = r.award_piid
     and c.pe_bli = r.pe_bli
)
select
    f.award_piid,
    f.pe_bli,
    f.method,
    f.confidence,
    string_agg(distinct rc.pe_bli, '; ' order by rc.pe_bli) as refuted_pe_blis,
    string_agg(distinct rc.article_id, '; ' order by rc.article_id)
        as shared_article_ids
from {{ ref('fct_budget_to_awards') }} f
join cited c
  on c.award_piid = f.award_piid
 and c.pe_bli = f.pe_bli
join refuted_cited rc
  on rc.award_piid = f.award_piid
 and rc.article_id = c.article_id
 and rc.pe_bli <> f.pe_bli
left join refuted self
  on self.award_piid = f.award_piid
 and self.pe_bli = f.pe_bli
left join {{ ref('link_line_rulings') }} lr
  on lr.award_piid = f.award_piid
 and lr.pe_bli = f.pe_bli
where self.award_piid is null
  and lr.award_piid is null
group by 1, 2, 3, 4
