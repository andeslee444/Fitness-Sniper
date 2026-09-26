-- link table: dollars live at award grain; links graded 'low' or 'reject' stay in
-- Postgres and in audit_link_grading (every link, with its grade and why) for audit
--
-- E1 (Sprint E, ROADMAP #67): dim_programs is no longer unique on pe_bli
-- alone (a genuine account collision, 10 keys, now publishes two rows). This
-- join used to be a trivial 1:1 lookup; joining it unconstrained today
-- would fan out every award row for those pe_bli values into two
-- (duplicating awards dollars, not just the title). `programs` dedupes to
-- (at most) one row per pe_bli first.
--
-- ROADMAP #70 (2026-09-04): award-to-account attribution now EXISTS for the
-- account-split keys. budget_line_awards.account (migration 014) carries the
-- one member a link's own evidence identifies, so `programs_by_account`
-- resolves those rows to that member's title. It is a strict refinement: the
-- join is on (pe_bli, account) and dim_programs is unique on that pair, so it
-- can never fan a row out; a link with account NULL — every ordinary key, and
-- every organization-split key, which stays unlinked — matches nothing there
-- (SQL null equality) and falls back to `programs` exactly as before.
-- Hand-adjudication overlay: reviewed pairs carry an explicit adjudicated
-- confidence (see migration 010). Review coverage varies by method and is
-- measured separately; not every published pair has an individual review.
-- The published confidence is the adjudicated one when present; the mechanical
-- crosswalk tag is retained as crosswalk_confidence, never rewritten.
-- Pairs adjudicated low/reject drop out of the mart (and the site) here.
with programs as (
    select pe_bli, min(title) as title
    from {{ ref('dim_programs') }}
    group by pe_bli
),
programs_by_account as (
    -- One row per (pe_bli, account). group by rather than a bare select so a
    -- future third row under one account degrades to a deterministic title
    -- instead of fanning the award row out.
    select pe_bli, account, min(title) as title
    from {{ ref('dim_programs') }}
    where account is not null
    group by pe_bli, account
),
-- The grading — adjudication overlay, the #75 / #107(b) / #110 demotions and
-- the reason each records — lives in audit_link_grading (2026-09-25), which
-- grades EVERY crosswalk link, published or not, so a demoted or unpublished
-- link stays auditable in the warehouse. This mart publishes the rows it
-- grades high or medium, and filters on the SAME column it emits (the
-- 2026-09-04 #75 fix round 1 finding 3 invariant: the where clause must never
-- re-derive a pre-demotion grade).
linked as (
    select * from {{ ref('audit_link_grading') }}
)
select
    l.pe_bli,
    l.exhibit,
    l.fiscal_year,
    l.organization,
    l.award_piid,
    l.recipient_name,
    l.recipient_uei,
    l.method,
    l.account,
    l.confidence,
    l.crosswalk_confidence,
    l.confidence_source,
    l.award_verdict,
    l.pair_reason,
    l.adjudication_basis,
    coalesce(pa.title, p.title) as program_title,
    -- appended last (2026-09-25) so every earlier column keeps its position:
    -- NULL, or the audit_link_grading rule that moved this link down to the
    -- tier it publishes under (#75 account+tokens, #110 announcement).
    l.demotion_reason
from linked l
left join programs_by_account pa
  on pa.pe_bli = l.pe_bli and pa.account = l.account
left join programs p
  on p.pe_bli = l.pe_bli
where l.confidence in ('high', 'medium')
