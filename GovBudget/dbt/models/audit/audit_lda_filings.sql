-- audit_lda_filings — EVERY Senate LDA filing in the lake (lda_filings), with
-- whether fct_influence counts its amounts and why. fct_influence sums exactly
-- the rows counted here; nothing is resolved anywhere else.
--
-- R-DEC-AMEND (controller ruling 2026-09-26, under the owner's 2026-09-25
-- delegation): an amendment SUPERSEDES the original report for the same
-- registrant, client and quarter (filing_year + filing_period), so the
-- quarter is counted once, from the amendment. Before this rule fct_influence
-- summed every filing and counted an amended quarter twice or more (measured
-- read-only 2026-09-26: see the decisions-lane-dbt report, fix round).
--
-- The rule reads filing_type, the only amendment field the lake carries
-- (Senate LDA codes): Q1-Q4 quarterly report, Q1Y-Q4Y the same with no
-- activity, 1T-4T termination report (1TY-4TY no activity), 1A-4A amendment
-- (1AY-4AY no activity), 1@-4@ termination amendment, RR registration, RA
-- registration amendment.
--
--   resolution
--     registration            RR / RA: a registration, not a quarterly
--                             report (the lake records no amount on any);
--                             counted as before, outside the quarter rule
--     original                a report in a quarter with no amendment —
--                             counted. Two ORIGINAL reports for one quarter
--                             (a re-filed duplicate, or a report beside a
--                             termination report) are not an amendment chain
--                             and are out of the ruling's scope: both count.
--     superseded_by_amendment a report (Q*, *T) whose quarter carries an
--                             amendment — not counted
--     amendment_counted       the one amendment the quarter is counted from
--     amendment_superseded    another amendment of the same quarter — not
--                             counted (an amendment of an amendment: the
--                             latest supersedes the earlier)
--
--   latest_determinable  (quarters with an amendment; NULL elsewhere) the
--     lake carries no posting date — influence/lda.py keeps none of the API's
--     timestamps — so "the latest amendment" can be named only when every
--     amendment of the quarter reports the same figures (then whichever is
--     latest, the counted figure is the same; the lowest filing_uuid is
--     picked so the choice is stable). When the amendments DISAGREE, the
--     latest is unknown: the quarter is counted from the amendment reporting
--     the SMALLEST total (never more than the latest amendment reports —
--     publish the smaller true number), latest_determinable is false, and
--     warn_lda_amendment_latest_undetermined prints the count in every build
--     log.
with filings as (
    select
        filing_uuid,
        url,
        client_name,
        registrant_name,
        filing_year,
        filing_period,
        filing_type,
        income_usd,
        expenses_usd,
        family_key_guess,
        match_method,
        coalesce(filing_type, '') in ('RR', 'RA') as is_registration,
        regexp_full_match(coalesce(filing_type, ''), '[1-4][A@]Y?')
            as is_amendment,
        coalesce(try_cast(nullif(trim(income_usd), '') as double), 0)
            + coalesce(try_cast(nullif(trim(expenses_usd), '') as double), 0)
            as reported_total
    from {{ source('influence', 'lda_filings') }}
),
quarters as (
    select
        registrant_name,
        client_name,
        filing_year,
        filing_period,
        count(*) filter (where is_amendment) as amendments,
        count(distinct coalesce(income_usd, '') || '|' || coalesce(expenses_usd, ''))
            filter (where is_amendment) as amended_figures
    from filings
    where not is_registration
    group by all
),
ranked as (
    select
        f.*,
        coalesce(q.amendments, 0) as amendments,
        q.amended_figures,
        row_number() over (
            partition by f.registrant_name, f.client_name, f.filing_year,
                         f.filing_period, f.is_registration
            order by f.is_amendment desc, f.reported_total asc, f.filing_uuid asc
        ) as rank_in_quarter,
        first_value(f.filing_uuid) over (
            partition by f.registrant_name, f.client_name, f.filing_year,
                         f.filing_period, f.is_registration
            order by f.is_amendment desc, f.reported_total asc, f.filing_uuid asc
        ) as quarter_first_uuid
    from filings f
    left join quarters q
      on  q.registrant_name is not distinct from f.registrant_name
      and q.client_name     is not distinct from f.client_name
      and q.filing_year     is not distinct from f.filing_year
      and q.filing_period   is not distinct from f.filing_period
      and not f.is_registration
),
resolved as (
    select
        *,
        case
            when is_registration then 'registration'
            when amendments = 0 then 'original'
            when not is_amendment then 'superseded_by_amendment'
            when rank_in_quarter = 1 then 'amendment_counted'
            else 'amendment_superseded'
        end as resolution
    from ranked
)
select
    filing_uuid,
    url,
    client_name,
    registrant_name,
    filing_year,
    filing_period,
    filing_type,
    income_usd,
    expenses_usd,
    family_key_guess,
    match_method,
    resolution,
    resolution in ('registration', 'original', 'amendment_counted') as counted,
    case
        when resolution in ('superseded_by_amendment', 'amendment_superseded')
            then quarter_first_uuid
    end as superseded_by,
    case
        when resolution in ('registration', 'original') then null
        else amended_figures = 1
    end as latest_determinable
from resolved
