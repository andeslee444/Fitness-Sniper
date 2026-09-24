-- No SHARED budget-line code may carry an account-NULL HIGH link beside an
-- account-resolved one. Returns the offending keys (test passes when zero rows
-- returned). Zero rows on the corpus as of 2026-09-19.
--
-- WHAT THIS GUARDS, AND HOW IT NARROWED.
--
-- 2026-09-04 (ROADMAP #70 fix round 1, finding 4). fct_district_programs was
-- grained on (pop_state, pop_district, pe_bli) and joined the HIGH-confidence
-- rows of fct_budget_to_awards. Since #70 those rows resolve program_title per
-- (pe_bli, account), so one of the codes two Navy programs share could present
-- TWO titles for one pe_bli. The model grouped on the pe_bli and took min() of
-- the label columns — chosen deliberately over grouping BY the title, which
-- would have split one district-program into two rows and broken the model's
-- own declared grain. The cost of that choice was that if both members of a
-- shared code ever carried high links, the district card would sum BOTH
-- programs' money and file it under whichever title sorts first: the #56
-- fusion shape, in a figure a reader is likely to quote, with every
-- number<->citation gate still green because each underlying link is
-- individually true. So this test returned any shared code with two account
-- keys, and its header said: "If this fires, the fix is NOT to relax the test:
-- it is to give fct_district_programs an account-qualified grain (and the
-- district sidecars slug-addressed program links to match)."
--
-- 2026-09-19, part 1: IT FIRED. Task 25b's wave-4 announcement load added five
-- high links on '0145' under 1506N ("F/A-18E/F (Fighter) Hornet") beside the
-- three it already carried under 1508N ("General Purpose Bombs"), and
-- `govbudget build` went red on `('0145', 2, '1506N', '1508N', 8)`. The fusion
-- was still LATENT — all three 1508N awards had zero place-of-performance
-- rows, so no reader had yet met a fused figure — which is exactly what this
-- assertion exists to buy: notice on the precondition, not on the symptom.
--
-- 2026-09-19, part 2: Task 27 took the prescription. fct_district_programs and
-- fct_district_programs_by_year now group on `account`, so two
-- ACCOUNT-RESOLVED members of one code are two rows, each under its own title,
-- each addressed to its own member page by split key. That configuration is no
-- longer a fusion and no longer returned here.
--
-- WHAT REMAINS GUARDED. An account grain cannot separate what carries no
-- account. NULL IS A MEMBER, NOT AN ABSENCE (2026-09-04 final review, finding
-- I7): an account-NULL high link names BOTH members of a shared code — an
-- overlay-raised `account+subagency` high row is exactly that — so one sitting
-- beside an account-resolved high link on the same pe_bli puts an unknown
-- member's dollars on the page in a row the exporter can only address to the
-- disambiguation stub, immediately beside a sibling row filed under a named
-- member. That is the shape this test now returns. `count(distinct account)`
-- ignores NULLs on its own, so the '(unresolved)' sentinel is what makes the
-- NULL side countable at all.
--
-- NOT COVERED, DELIBERATELY: the 3 ORGANIZATION-split codes ('20', '30',
-- '500'), whose members share one account ('0300D') and so are not selected by
-- the `count(distinct account) > 1` definition of "shared" below. An account
-- can never name one of their members, and both link loaders exclude them
-- (ROADMAP #70/#83), so they carry no crosswalk links at all today; the
-- exporter keeps them on the stub via _ProgramIdentity.is_account_split.
with shared as (
    -- the codes whose members an ACCOUNT can tell apart
    select pe_bli
    from {{ ref('dim_programs') }}
    group by pe_bli
    having count(distinct account) > 1
),
keyed as (
    select
        b.pe_bli,
        coalesce(b.account, '(unresolved)') as account_key
    from {{ ref('fct_budget_to_awards') }} b
    join shared s on b.pe_bli = s.pe_bli
    where b.confidence = 'high'
)
select
    pe_bli,
    count(distinct account_key)                            as n_accounts,
    count(*) filter (where account_key = '(unresolved)')   as n_unresolved_links,
    count(*) filter (where account_key <> '(unresolved)')  as n_resolved_links,
    count(*)                                               as n_high_links
from keyed
group by pe_bli
having count(*) filter (where account_key = '(unresolved)') > 0
   and count(*) filter (where account_key <> '(unresolved)') > 0
