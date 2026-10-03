-- 021: the budget line code printed in each P-1/P-1R source row
-- (families piece 1, spec docs/superpowers/specs/2026-10-02-era-procurement-history-design.md §4.1).
--
-- PB2017-PB2023 P-1 rows key pe_bli by the era display line
-- ('{account}-{org}-L{line}', era_keys.py) and the loader used to drop the
-- printed code (column I, 'Line Item'). This column keeps it, source-stated
-- and never mapped. Modern P-1 rows and every P-1R row already key pe_bli by
-- the printed code, so the backfill below is exact for them; era P-1 rows
-- are filled by the S1 re-run (scripts/era/s1_reload_era_p1.py --apply).
-- R-1 rows stay NULL (a program element, not a budget line code).
alter table budget_lines add column line_item_code text;
comment on column budget_lines.line_item_code is
  'Budget line code printed in the source P-1/P-1R row (era "Line Item", modern "Budget Line Item"); source-stated, never mapped';
update budget_lines set line_item_code = pe_bli
 where exhibit in ('P-1','P-1R') and pe_bli !~ '^\d{4}[A-Z]-[A-Z]+-L';
