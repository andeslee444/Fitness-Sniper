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
-- never withholds anything: every hit needs a person's ruling, `withdraw`
-- (audit_link_grading grades the pair low, and the mart drops it) or
-- `allow`. Its recall is limited to the base description: "WITH AEA KITS"
-- (N0001917C0003) is excluded by KITS, and "PRODUCTION READY TEST ASSET"
-- (W58RGZ24C0021) or "PAC-3 MISSILE PRODUCTION" name no listed term — a
-- ruling found those by hand.
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
