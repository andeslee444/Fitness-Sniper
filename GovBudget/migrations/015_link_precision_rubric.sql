-- migrations/015_link_precision_rubric.sql
--
-- 015: link_precision_samples.rubric — which QUESTION a verdict answered
-- (2026-09-11, ROADMAP #79).
--
-- The 2026-09-04 held-out study (migration 011) judged four strata on program
-- ATTRIBUTION — did this award pay for this program — and one,
-- `account+subagency`, on whether the MECHANICAL rule had fired (account
-- 097-0400, sub-agency DARPA, PIID prefix HR0011): every one of its 60 reasons
-- restates the rule. `account+subagency 60/60` was printed beside the
-- attribution strata on /methodology/ as one "precision" figure until the
-- final review caught it (f96344e5, 2026-09-04), and since then the exporter
-- has told the strata apart with a hand-named set
-- (_UNRUBRICKED_PRECISION_STRATA). A hand-named set is a label the next study
-- can forget to update; a column is a property of the row.
--
-- `rubric` is what scripts/precision_study.py stamps on every verdict it loads
-- (--rubric is required) and what export_site._link_precision_block filters on:
-- only 'attribution' rows are ever published. Strata judged on anything else
-- stay listed UNMEASURED on /methodology/ until re-judged on attribution under a
-- new sample_id. Values are closed by CHECK; adding a rubric means adding it to
-- RUBRICS in the script, to this constraint, and to the sentence on the page.
--
-- Backfill: the 2026-09-04 run is stamped by its DRAW-TIME method (the study
-- table's own `method` column). Any other unstamped row fails SET NOT NULL
-- loudly — this migration knows one run and guesses for none.
alter table link_precision_samples add column if not exists rubric text;

update link_precision_samples
   set rubric = case when method = 'account+subagency' then 'rule-fired'
                     else 'attribution' end
 where rubric is null
   and sample_id = '2026-09-04';

alter table link_precision_samples alter column rubric set not null;

alter table link_precision_samples
  drop constraint if exists link_precision_samples_rubric_check;
alter table link_precision_samples
  add constraint link_precision_samples_rubric_check
  check (rubric in ('attribution', 'rule-fired'));

comment on column link_precision_samples.rubric is
  'The question this verdict answered (ROADMAP #79). attribution: does this '
  'award execute this program element. rule-fired: did the mechanical linking '
  'rule fire as recorded. Only attribution rows are published as precision.';
