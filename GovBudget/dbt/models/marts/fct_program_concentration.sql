-- fct_program_concentration: HHI of vendor-family concentration per pe_bli,
-- published on TWO bases (ROADMAP #80, 2026-09-05):
--   *_all  — every published link (fct_budget_to_awards is high+medium by
--            construction). These are the pre-#80 columns under new names;
--            their values and their derived citation fact_ids do not move.
--   *_high — high-confidence links only. hhi_high AND top_family_high are
--            NULL below a floor of 3 linked awards across 2 contractor
--            families HOLDING POSITIVE DOLLARS, with positive net program
--            dollars (an index over one or two awards is a fact about the
--            sample, not the market — and an index over zero dollars is not
--            a fact about anything: 13 programs' high links summed to $0 and
--            published hhi_high = 0.0 "Competitive" with a top contractor
--            picked alphabetically, 7 more published 10,000 over a single
--            positive-dollar family while the card said "2-4 families",
--            2026-09-11 review of #80). positive_family_count_high is
--            published so the floor is auditable from the mart itself;
--            program_dollars_high stays the TRUE sum (it may be <= 0) and is
--            NULL only when the program has no high link at all; the three
--            counts are 0 in that case, never NULL.
-- The site headlines the high-only figures where they publish and states the
-- absence where they do not; the *_all columns are not rendered (the
-- account+subagency tier that dominates them measured 0/60 for program
-- attribution, ROADMAP #79) but ship in the download and on /methodology/.
-- The exporter mints a distinct derived fact_id per basis, with a formula
-- true of that basis.
-- Award dollars enter ONCE per award (not per transaction) to avoid double-count.
-- HHI uses positive-obligation share only to keep HHI ∈ [0, 10000].
-- positive-only shares: families with net deobligations keep full positive share (documented bias).
with award_dollars as (
    -- sum obligation at award grain across all transactions (positive-only for share)
    select
        award_id_piid,
        sum(obligation) as award_obligation,
        sum(case when obligation > 0 then obligation else 0 end) as pos_obligation
    from {{ ref('fct_award_transactions') }}
    where award_id_piid is not null
    group by award_id_piid
),
links as (
    -- one row per published (pe_bli, award_piid) link — true of the corpus
    -- (measured read-only 2026-09-25: 12,601 mart rows, 12,601 distinct
    -- pairs), but NOT asserted: budget_line_awards is unique on (pe_bli,
    -- exhibit, fiscal_year, award_piid), so a second edition-year row for one
    -- pair (a multi-edition crosswalk run, ROADMAP #78) would add that award's
    -- dollars twice to the family and program sums (and so to the HHI) below;
    -- the distinct counts (award_count, family_count, positive_family_count)
    -- would not show it. Confidence is the PUBLISHED confidence (adjudication
    -- overlay + demotion applied upstream).
    select
        l.pe_bli,
        l.award_piid,
        l.confidence,
        coalesce(a.award_obligation, 0) as award_obligation,
        coalesce(a.pos_obligation, 0) as pos_obligation,
        coalesce(x.family_key, l.recipient_uei, upper(l.recipient_name)) as family_key
    from {{ ref('fct_budget_to_awards') }} l
    left join award_dollars a
        on a.award_id_piid = l.award_piid
    left join {{ ref('entity_xwalk') }} x
        on x.recipient_uei = l.recipient_uei
),
based as (
    -- the two bases as one long table; every aggregate below is per basis
    select 'all' as basis, * from links
    union all
    select 'high' as basis, * from links where confidence = 'high'
),
program_totals as (
    select
        basis,
        pe_bli,
        -- distinct AWARDS, not link rows: the mart's grain key is
        -- (pe_bli, exhibit, fiscal_year, award_piid), and "3 linked awards"
        -- is the floor's sentence. Identical today (the link table's
        -- (pe_bli, award_piid) is unique over 12,280 rows, 2026-09-10).
        count(distinct award_piid) as award_count,
        sum(award_obligation) as program_dollars,
        sum(pos_obligation) as pos_program_dollars
    from based
    group by basis, pe_bli
),
family_totals as (
    select
        basis,
        pe_bli,
        family_key,
        sum(award_obligation) as family_dollars,
        sum(pos_obligation) as family_pos_dollars
    from based
    group by basis, pe_bli, family_key
),
family_shares as (
    select
        ft.basis,
        ft.pe_bli,
        ft.family_key,
        ft.family_pos_dollars,
        case
            when pt.pos_program_dollars > 0 and ft.family_pos_dollars > 0
            then 100.0 * ft.family_pos_dollars / pt.pos_program_dollars
            else 0
        end as share_pct
    from family_totals ft
    join program_totals pt
      on pt.basis = ft.basis and pt.pe_bli = ft.pe_bli
),
hhi_calc as (
    select
        basis,
        pe_bli,
        sum(share_pct * share_pct) as hhi,
        count(distinct family_key) as family_count,
        -- families that actually hold positive dollars. family_count counts
        -- every LINKED family, including those whose share_pct fell into the
        -- `else 0` branch above; a floor over that count is satisfiable by a
        -- family that contributed nothing, which is how 7 programs published
        -- a 10,000 index next to "2 contractor families" (#80 fix round 1).
        count(distinct case when share_pct > 0 then family_key end)
            as positive_family_count
    from family_shares
    group by basis, pe_bli
),
top_family as (
    -- family_key tie-break makes the pick deterministic run to run
    select distinct on (basis, pe_bli)
        basis,
        pe_bli,
        family_key as top_family
    from family_shares
    order by basis, pe_bli, family_pos_dollars desc, family_key
),
per_basis as (
    select
        h.basis,
        h.pe_bli,
        h.hhi,
        h.family_count,
        h.positive_family_count,
        t.top_family,
        pt.award_count,
        pt.program_dollars
    from hhi_calc h
    join program_totals pt
      on pt.basis = h.basis and pt.pe_bli = h.pe_bli
    left join top_family t
      on t.basis = h.basis and t.pe_bli = h.pe_bli
)
select
    pe_bli,
    max(case when basis = 'all' then hhi end)             as hhi_all,
    max(case when basis = 'all' then top_family end)      as top_family_all,
    max(case when basis = 'all' then family_count end)    as family_count_all,
    max(case when basis = 'all' then award_count end)     as award_count_all,
    max(case when basis = 'all' then program_dollars end) as program_dollars_all,
    -- THE FLOOR (#80 fix round 1, 2026-09-11). A high-only index publishes
    -- only over >= 3 distinct awards, >= 2 families holding POSITIVE dollars,
    -- and positive net program dollars. top_family_high is withheld with it:
    -- with every family at zero positive dollars the `distinct on` tie-break
    -- picks the alphabetically first family, which is not a leader.
    -- 37 of 444 programs clear this (2026-09-11, live lake); the 57 that
    -- cleared the award/family-count-only floor included 13 whose high links
    -- summed to zero or negative dollars and 7 with a single positive family.
    case
        when coalesce(max(case when basis = 'high' then award_count end), 0) >= 3
         and coalesce(max(case when basis = 'high' then positive_family_count end), 0) >= 2
         and coalesce(max(case when basis = 'high' then program_dollars end), 0) > 0
        then max(case when basis = 'high' then hhi end)
    end                                                    as hhi_high,
    case
        when coalesce(max(case when basis = 'high' then award_count end), 0) >= 3
         and coalesce(max(case when basis = 'high' then positive_family_count end), 0) >= 2
         and coalesce(max(case when basis = 'high' then program_dollars end), 0) > 0
        then max(case when basis = 'high' then top_family end)
    end                                                    as top_family_high,
    coalesce(max(case when basis = 'high' then family_count end), 0) as family_count_high,
    coalesce(max(case when basis = 'high' then positive_family_count end), 0)
        as positive_family_count_high,
    coalesce(max(case when basis = 'high' then award_count end), 0)  as award_count_high,
    max(case when basis = 'high' then program_dollars end) as program_dollars_high
from per_basis
group by pe_bli
