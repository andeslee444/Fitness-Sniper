-- R-DEC-LINK-2026-10-21 (owner, 2026-10-21): the recurrence gate for the
-- production-on-modification-line species. Until that ruling nothing in the
-- chain compared a line's budget activity with what the award buys: the
-- loader's money-colour guard works at appropriation grain (1506N BA01
-- production and 1506N BA05 modification are one account), so the Lot 12
-- advance acquisition (N0001917C0001) and the Lot 20 long-lead
-- (N0001925C0070) published high on the F-35 modification lines 0592/0593,
-- TH-73A full-rate production on 0549, and 34 fpds-ap production, long-lead,
-- multiyear and engine buys on seven modification lines (verify.md 1.1;
-- sweep.md 2 A2). Run against the 2026-09-04 publish, this test flags all
-- five announcement links.
--
-- A FAILURE is a PUBLISHED link (fct_budget_to_awards) with no ruling in
-- dbt/seeds/link_line_rulings.csv, of method announcement+lexicon,
-- subaward+lexicon (line-specific claims) or fpds-ap (the owner withdrew
-- that species too), where
--   * the line's LATEST budget_activity_title (stg_budget_lines, newest
--     fiscal_year per (pe_bli, account)) is a modification activity, and
--   * the award's FPDS base description names end-item production or
--     long-lead — LRIP, low-rate initial production, FRP, full-rate
--     production, Lot N, long lead, advance(d) acquisition/procurement, AAC,
--     multiyear, new build, "procure(ment of) N … aircraft / air vehicles /
--     engines" — and no modification word (MOD(S), MODIFICATION, RETROFIT,
--     UPGRADE, KIT(S), ECP(S), INSTALL) once the FPDS contract-action
--     boilerplate "(THE )PURPOSE OF THIS MODIFICATION" / "THIS MODIFICATION"
--     is stripped (N0001920C0009, LRIP 15 long lead, opens with it).
--
-- The predicate is only a screen: of its 13 announcement-tier hits on the
-- 2026-10-20 warehouse, 8 are correct subsystem buys a modification line
-- makes itself (IRST, NGJ-MB, EPAWSS, AWACS FRP-C, DRAGON, GGU-25). So it
-- never withholds anything: every hit needs a recorded ruling — the owner's
-- `withdraw` (audit_link_grading grades the pair low, and the mart drops it)
-- or `allow`, or the controller's `hold` (kept as published pending an owner
-- ruling; assert_link_line_rulings_well_formed binds each to its ruler).
-- Measured read-only 2026-10-21 against the pre-ruling publish with no
-- rulings: 54 hits — 31 of the 41 withdrawn pairs, 13 allows, 10 holds.
--
-- RECALL. Its reach ends at the FPDS base description, and it MISSES 10 of
-- the 41 withdrawn pairs (same measurement; base description as this test
-- reads it, max() over the award's rows):
--   0505        N0001909C0019  fpds-ap  "F/A-18 AIRCRAFT"
--   0505        N0001914C0032  fpds-ap  "EA-18 G AIRCRAFT"
--   0505        N0001917C0003  fpds-ap  "LOT 40 F/A-18E AND EA-18G AIRCRAFT
--                                        WITH AEA KITS" (KITS excludes it)
--   0505        N0001917C0047  fpds-ap  "USN F414 ENGINES: EA-18G"
--   0590        N0001917C0081  fpds-ap  "AE1107C TURBOSHAFT ENGINES"
--   0962C50700  W31P4Q09C0002  fpds-ap  "FY09 PAC-3 MISSILE PRODUCTION BUY"
--   0962C50700  W31P4Q10C0002  fpds-ap  "PAC-3 FY10 PRODUCTIO"
--   3264AA0252  W58RGZ18F0050  fpds-ap  "AUSTRALIA DEFENSE FORCE (QAF)
--                                        QUALITY ASSURANCE TEAM REVIEW"
--   C03200      FA813423FB001  announcement+lexicon  "CONTRACTOR LOGISTICS
--   C04000      FA813423FB001  announcement+lexicon   SUPPORT FOR THE C-32/C-40
--                                                      AIRCRAFT FLEETS"
-- A ruling found those by hand. The FB001 pair is an O&M support task order,
-- not a production buy; assert_refuted_pair_siblings_ruled covers it (the
-- precision study refuted the C04000 link, and its C03200 twin cites the same
-- announcement). The others name an aircraft, an engine or a missile buy in
-- words this predicate does not list ("PRODUCTION" alone, "ENGINES", a bare
-- type designator), so a recurrence of an "ENGINE PRODUCTION" buy on a
-- modification line passes it. The predicate is NOT widened here: a broader
-- term flags subsystem buys a person must then rule on (verify.md v18 counts
-- about 14 more), and those rulings would have to be the owner's.
--
-- Returned rows are the FAILURES (dbt singular test convention), one per
-- (link, line activity, description): select distinct, because a NULL-account
-- link on a code two accounts share joins both accounts' latest rows.
with line_ba as (
    select
        pe_bli,
        account,
        budget_activity_title,
        row_number() over (
            partition by pe_bli, account order by fiscal_year desc
        ) as rn
    from {{ ref('stg_budget_lines') }}
),
published as (
    select award_piid, pe_bli, method, confidence, account
    from {{ ref('fct_budget_to_awards') }}
    where method in ('announcement+lexicon', 'subaward+lexicon', 'fpds-ap')
),
award_desc as (
    select
        award_id_piid as award_piid,
        upper(max(prime_award_base_transaction_description)) as base_desc
    from {{ source('lake', 'contracts') }}
    where award_id_piid in (select award_piid from published)
    group by 1
)
select distinct
    p.pe_bli,
    p.award_piid,
    p.method,
    p.confidence,
    b.budget_activity_title,
    d.base_desc
from published p
join line_ba b
  on b.pe_bli = p.pe_bli
 and b.rn = 1
 and (p.account is null or b.account = p.account)
join award_desc d
  on d.award_piid = p.award_piid
left join {{ ref('link_line_rulings') }} r
  on r.award_piid = p.award_piid
 and r.pe_bli = p.pe_bli
where b.budget_activity_title ilike '%modif%'
  and regexp_matches(
        d.base_desc,
        '(\bLRIP\b|LOW[- ]RATE INITIAL PRODUCTION|\bFRP\b|FULL[- ]RATE PRODUCTION'
        || '|\bLOT [0-9IVX]+\b|LONG[- ]LEAD|ADVANCED? ACQUISITION'
        || '|ADVANCED? PROCUREMENT|\bAAC\b|MULTI[- ]?YEAR|NEW[- ]BUILD'
        || '|PROCURE(MENT OF)?\s+[0-9]+\s+(\S+\s+){0,3}'
        || '(AIRCRAFT|AIR VEHICLES|ENGINES)\b)')
  and not regexp_matches(
        regexp_replace(
            d.base_desc,
            '(THE )?PURPOSE OF THIS MODIFICATION|THIS MODIFICATION', '', 'g'),
        '(\bMODS?\b|MODIFICATION|RETROFIT|UPGRADE|\bKITS?\b|\bECPS?\b|INSTALL)')
  and r.award_piid is null
