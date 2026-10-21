-- R-DEC-LINK-2026-10-21 (owner, 2026-10-21): a `withdraw` ruling in
-- dbt/seeds/link_line_rulings.csv grades its (award_piid, pe_bli) pair low
-- in audit_link_grading, ahead of every other rule — the adjudication
-- overlay included. A pair a hand adjudication PINNED HERE (award_verdict
-- 'pinned', pair_reason 'pinned-here': the adjudicator tied this award to
-- this very program element) is the one judgment the ruling must never
-- override silently: two recorded judgments disagree, and a person rules on
-- which stands. The build stops instead.
--
-- Returned rows are the FAILURES (dbt singular test convention): one per
-- withdraw ruling whose pair carries a pinned-here adjudication, whatever
-- its refuter-lens count.
select
    r.award_piid,
    r.pe_bli,
    r.ruling_id,
    a.award_verdict,
    a.pair_reason,
    a.refuter_lenses_passed
from {{ ref('link_line_rulings') }} r
join {{ source('lake', 'jbook_award_adjudications') }} a
  on a.award_piid = r.award_piid
 and a.pe_bli = r.pe_bli
where r.ruling = 'withdraw'
  and a.award_verdict = 'pinned'
  and a.pair_reason = 'pinned-here'
