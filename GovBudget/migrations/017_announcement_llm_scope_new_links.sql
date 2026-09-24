-- 017: announcement_llm_scope.links_new_this_pass — how many of the links the
-- announcement tier publishes today came from THIS pass (2026-09-19, fix round
-- 1, item 2).
--
-- THE DEFECT. /methodology/ publishes the announcement tier's precision from
-- the 2026-09-04 stratified draw (56 of 60, pinned by
-- export_site._PINNED_PRECISION_SAMPLES). That draw was made over the tier as
-- it stood: 708 links. After this pass loaded, the tier holds 1,075, and 367
-- of them post-date the draw — a third of the tier the figure describes was
-- never eligible for it. Every number on the page was true; the SAMPLING FRAME
-- was disclosed only in docs/methodology.md. This column is where the page
-- gets the count, so the disclosure is derived and gate 24 leg q binds it.
--
-- Counted at write time by scripts/load_announcement_scope.py: pairs in the
-- wave's `surviving` list that no earlier wave's list holds, and that the
-- corpus publishes today under `announcement+lexicon` at high or medium. NULL
-- on a row written before this column existed, and the page then renders no
-- frame sentence rather than a count it cannot derive.
--
-- ON 016's COMMENT, which is wrong and cannot be edited (a migration file is
-- never amended once applied): 016 says "Rows are kept, never updated in place
-- (supersede-not-delete)". The loader upserts ON CONFLICT (as_of), so a re-run
-- on the same date REPLACES that day's row. What is true is the weaker claim:
-- one row per as_of, and rows from earlier dates are kept as the record of
-- what the page said before.
alter table announcement_llm_scope
    add column if not exists links_new_this_pass bigint
        check (links_new_this_pass >= 0);

comment on column announcement_llm_scope.links_new_this_pass is
  'Links the corpus publishes under announcement+lexicon that only this pass '
  'produced (its surviving pairs minus every earlier wave''s). /methodology/ '
  'states it beside the tier-wide precision figure, whose draw predates them.';
