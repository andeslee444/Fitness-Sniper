-- fct_program_concentration: HHI of vendor-family concentration per pe_bli,
-- published on TWO bases (ROADMAP #80, 2026-09-05):
--   *_all  — every published link (fct_budget_to_awards is high+medium by
--            construction). These are the pre-#80 columns under new names;
--            their values and their derived citation fact_ids do not move.
--   *_high — high-confidence links only. hhi_high is NULL below a floor of
--            3 linked awards across 2 contractor families (an index over one
--            or two awards is a fact about the sample, not the market);
--            program_dollars_high is NULL when the program has no high link
--            at all; the two counts are 0 in that case, never NULL.
-- The site headlines the high-only figures where they exist and prints the
-- all-tier figures on a labelled second line; the exporter mints a distinct
-- derived fact_id per basis, with a formula true of that basis.
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
    -- one row per published (pe_bli, award_piid) link; confidence is the
    -- PUBLISHED confidence (adjudication overlay + demotion applied upstream)
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
        count(distinct family_key) as family_count
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
    -- the floor: no high-only index on fewer than 3 awards or 2 families
    case
        when coalesce(max(case when basis = 'high' then award_count end), 0) >= 3
         and coalesce(max(case when basis = 'high' then family_count end), 0) >= 2
        then max(case when basis = 'high' then hhi end)
    end                                                    as hhi_high,
    max(case when basis = 'high' then top_family end)      as top_family_high,
    coalesce(max(case when basis = 'high' then family_count end), 0) as family_count_high,
    coalesce(max(case when basis = 'high' then award_count end), 0)  as award_count_high,
    max(case when basis = 'high' then program_dollars end) as program_dollars_high
from per_basis
group by pe_bli
