-- link_award_keys: the AWARD each published crosswalk link names — the one
-- point where a link resolves to award_unique_key (R-DEC-LINK-2026-10-21 R4;
-- controller ruling on review 1 finding I-4, 2026-10-21, under the owner's
-- approval to withdraw "the published N0001922F0001 collision").
--
-- A PIID is unique only under its parent IDV and agency; the lake keys an
-- award by award_unique_key (contract_award_unique_key). fct_budget_to_awards
-- links an award by its PIID and records the recipient the link names, and
-- every dollar join that read the PIID alone summed EVERY award sharing it.
-- N0001922F0001 is a Lockheed Martin F-35 order (the award the ATA000 link
-- names) and an unrelated Rolls-Royce NASM maintenance order ($157.9M FY2022
-- positive obligation, all of it in IN-07); the PIID-only joins published the
-- second as F-35 money on flows/ATA000.json, /district/IN-07/ and the
-- programs.json HHI.
--
-- GRAIN: one row per published link key (award_piid, recipient_uei) — every
-- fct_budget_to_awards row, high or medium — and per award the lake carries
-- under its PIID (award_unique_key; a NULL key is one award), with n_awards
-- (how many awards the PIID is in the lake) and `named`:
--   * a PIID that is ONE award: that award, whole — every UEI on it, so a
--     novated award keeps its successor's rows — named, exactly the rows the
--     PIID-only join read (byte-identical for every such link);
--   * a PIID that is SEVERAL awards: named only on the award(s) whose
--     transactions carry the recipient the link records; a link with no
--     recipient names none of them, and contributes nothing.
-- The rule export_site._emit_flows_sidecars introduced in round 1, moved here
-- so every surface reads it from one place. A link whose PIID the lake does
-- not carry has no row (it had no transactions to join before either).
--
-- Every join from a published link to fct_award_transactions goes through
-- this model — link on (award_piid, recipient_uei) with `named`, then the
-- transactions on (award_id_piid, award_unique_key):
--   fct_district_programs, fct_district_programs_by_year,
--   fct_district_totals, fct_district_totals_by_year, fct_feed_events,
--   fct_program_concentration, assert_district_totals_no_double_count,
--   export_site (flows sidecars, district citation PIIDs, district fan-out)
--   and flow_chart (bridge families). The rows with named = false are the
--   ledger of what the rule removes: on the 2026-10-20 warehouse, the
--   Rolls-Royce award under N0001922F0001 and nothing else.
--
-- Materialized as a table (dbt_project.yml): it reads the award lake once
-- per build instead of once per mart that joins it.
with links as (
    select distinct award_piid, recipient_uei
    from {{ ref('fct_budget_to_awards') }}
),
award_recipients as (
    select distinct
        award_id_piid as award_piid,
        award_unique_key,
        recipient_uei
    from {{ ref('fct_award_transactions') }}
    where award_id_piid in (select award_piid from links)
),
piid_awards as (
    select distinct award_piid, award_unique_key
    from award_recipients
),
piid_award_counts as (
    select award_piid, count(*) as n_awards
    from piid_awards
    group by award_piid
),
-- the awards under a linked PIID whose transactions carry the link's
-- recipient (one row per link key and award: no fan-out below)
recipient_awards as (
    select distinct l.award_piid, l.recipient_uei, r.award_unique_key
    from links l
    join award_recipients r
      on r.award_piid = l.award_piid
     and r.recipient_uei = l.recipient_uei
)
select
    l.award_piid,
    l.recipient_uei,
    a.award_unique_key,
    c.n_awards,
    c.n_awards = 1 or ra.award_piid is not null as named
from links l
join piid_awards a
  on a.award_piid = l.award_piid
join piid_award_counts c
  on c.award_piid = l.award_piid
left join recipient_awards ra
  on ra.award_piid = l.award_piid
 and ra.recipient_uei = l.recipient_uei
 and ra.award_unique_key is not distinct from a.award_unique_key
