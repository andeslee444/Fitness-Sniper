-- 016: announcement_llm_scope — what the announcement LLM-alias pass covered
-- (2026-09-19, ROADMAP findings log :118-119).
--
-- /methodology/ has disclosed the scope of this pass since 2026-09-02 as four
-- hand-typed literals ("3,840 … about 88% … 12,811 … ~12%"). They described a
-- residue whose selection code was never committed, and no gate could notice
-- when they stopped being true. This table is where the figures now come from:
-- one row per pass, written by scripts/load_announcement_scope.py from
-- data/research/announcements/residue_manifest.json + wave4_result.json, read
-- by export_site._announcement_llm_scope into site_meta.
--
-- Rows are kept, never updated in place (supersede-not-delete): the exporter
-- reads the latest as_of, and the older rows are the record of what the page
-- said before.
--
-- The cross-column CHECKs are NAMED so a test can drop one and prove the
-- exporter's own read-time guard still fires
-- (tests/test_export_site_announcement_scope.py).
create table if not exists announcement_llm_scope (
    as_of                  date primary key,
    -- archived announcement records that join the award lake
    records_total          bigint not null check (records_total >= 0),
    -- … of those, matched by deterministic owned-name matching
    records_deterministic  bigint not null check (records_deterministic >= 0),
    -- … of those, with no deterministic match (the residue)
    records_residue        bigint not null check (records_residue >= 0),
    -- … of the residue, put through an LLM-assisted alias pass
    records_attempted      bigint not null check (records_attempted >= 0),
    -- announced value (USD, amounts[0] of each record) of the residue …
    value_residue          numeric not null check (value_residue >= 0),
    -- … and of the part attempted
    value_attempted        numeric not null check (value_attempted >= 0),
    -- link_precision_samples.sample_id of the held-out sample drawn from the
    -- links this pass's newest wave produced, or NULL while that wave's links
    -- carry no measurement of their own. The tier-wide study
    -- (_link_precision_block) sampled the announcement tier on 2026-09-04,
    -- before those links existed, so its figure says nothing about them;
    -- naming the run here is what lets /methodology/ state a precision pair
    -- for THIS pass — "x of N", derived — instead of borrowing the tier's.
    precision_sample_id    text,
    note                   text,
    constraint attempted_within_residue
        check (records_attempted <= records_residue),
    constraint value_attempted_within_residue
        check (value_attempted <= value_residue),
    constraint residue_partitions_total
        check (records_deterministic + records_residue = records_total)
);

comment on table announcement_llm_scope is
  'One row per announcement LLM-alias pass: what it covered, of what residue, '
  'and which held-out sample measured its newest links. /methodology/ states '
  'every one of those figures through site_meta.announcement_llm_scope '
  '(export_site._announcement_llm_scope); gate 24 leg q recomputes them '
  'against the rendered paragraph.';
