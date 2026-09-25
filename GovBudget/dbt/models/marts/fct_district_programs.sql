-- fct_district_programs: high-confidence dollar grain per
-- (pop_state, pop_district, pe_bli, account) — the MEMBER grain.
-- Only confidence='high' awards are used to avoid the 14.7x multi-count fanout
-- seen with medium-confidence rows (recon §B). Measured read-only against the
-- shipped warehouse 2026-09-19: 608 rows, 317 pe_bli, 189 districts.
-- Breadth grain (all-confidence, mapped_via_account flag, NO dollar column) is
-- deferred — the join cost was acceptable but adds complexity; note that a second
-- model fct_district_programs_breadth could be added cheaply using the same joins
-- without the dollar column if needed by Task 5.
--
-- ROADMAP #70 (2026-09-04): grouped by (pop_state, pop_district, pe_bli) only,
-- with the two LABEL columns aggregated, because grouping BY the title would
-- have split one district-program into two rows and broken the model's own
-- declared grain.
--
-- TASK 27 (2026-09-19): the grain now carries `account`, so that split is the
-- point rather than the hazard. fct_budget_to_awards resolves program_title per
-- (pe_bli, account) for the codes two programs share; on 2026-09-19 the
-- wave-4 announcement load added '0145' high-confidence links under 1506N
-- ("F/A-18E/F (Fighter) Hornet" x5) beside the three 1508N ("General Purpose
-- Bombs") links an earlier announcement wave (wave 1) had already given it,
-- and assert_district_programs_single_member_high_links fired as designed.
-- Grouping on the account keeps each member's dollars under its own name
-- instead of summing both under min(program_title) — ROADMAP #56's fusion
-- shape. `account` is NULL for every code that names ONE program (597 of the
-- 608 rows measured read-only 2026-09-19), so those rows are byte-identical to
-- the pre-Task-27 model. On a SHARED code, a NULL account beside an
-- account-resolved high link is what the (narrowed) singular test guards; a
-- shared code whose high links are ALL account-NULL passes it, and the
-- exporter addresses that row to the disambiguation stub under a
-- both-members label.
-- The label columns stay min()-aggregated: within one (pe_bli, account) the
-- high links carry one title and one organization (measured read-only
-- 2026-09-25: at most 1 of each over all 416 (pe_bli, account) pairs with a
-- high link), so min() returns that value. No test asserts it: a pair that
-- ever carried two organization labels would make the `select distinct`
-- below emit two rows per award, and sum(t.obligation) would count that
-- award's transactions twice.
select
    t.pop_state,
    t.pop_district,
    b.pe_bli,
    b.account,
    min(b.program_title)               as program_title,
    min(b.organization)                as organization,
    count(distinct t.transaction_key)  as transaction_count,
    count(distinct t.award_id_piid)    as award_count,
    count(distinct t.recipient_uei)    as recipient_count,
    sum(t.obligation)                  as total_obligation
from {{ ref('fct_award_transactions') }} t
join (
    select distinct award_piid, pe_bli, account, program_title, organization
    from {{ ref('fct_budget_to_awards') }}
    where confidence = 'high'
) b on t.award_id_piid = b.award_piid
where t.pop_district is not null
group by 1, 2, 3, 4
