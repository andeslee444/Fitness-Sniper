-- 019: budget_line_awards.superseded_* — the route an evidence-graded link
-- replaced on its key (ROADMAP #140, decided 2026-09-25 under the owner's
-- delegation: keep the override, record the route it replaced).
--
-- THE MOVE. scripts/load_announcement_links.py upserts on the table's unique
-- key (pe_bli, exhibit, fiscal_year, award_piid) with `do update set
-- method=…, confidence=…`. When an announcement or subaward link lands on a
-- key another route already holds (fpds-ap, or a mechanical account* row), the
-- older row is re-attributed in place and its method and confidence are gone.
-- On 2026-09-19 that happened to 60 rows (45 fpds-ap medium, 13 fpds-ap low,
-- 1 account low, 1 account+subagency medium — Task 25b), and no column said
-- which rows or what they had been.
--
-- THE RECORD. The loader now writes the replaced row's method and confidence
-- here, with the time of the move, and carries all four columns across its
-- own delete-and-rebuild of the partition it owns (a re-run deletes every
-- announcement/subaward row first, so without the carry the record would last
-- one run). A first insert — no other route on the key — writes NULLs.
-- method, confidence and at are all set or all NULL.
--
-- superseded_evidence is NULL on a record the loader wrote AT the move (the
-- move is its own evidence). A record written later, from other evidence,
-- cites that evidence here — migration 020 records the 60 moves of 2026-09-19
-- that way (R-DEC-140), with 'unknown' where the evidence does not name the
-- prior method or confidence.
alter table budget_line_awards
    add column if not exists superseded_method text,
    add column if not exists superseded_confidence text,
    add column if not exists superseded_at timestamptz,
    add column if not exists superseded_evidence text;

alter table budget_line_awards
    drop constraint if exists budget_line_awards_superseded_all_or_none;
alter table budget_line_awards
    add constraint budget_line_awards_superseded_all_or_none
    check (
        (superseded_method is null) = (superseded_confidence is null)
        and (superseded_method is null) = (superseded_at is null)
        and (superseded_evidence is null or superseded_method is not null)
    );

comment on column budget_line_awards.superseded_method is
  'The method of the row this link replaced on its key (ROADMAP #140), '
  '''unknown'' when the evidence for a historical move does not name it, or '
  'NULL when the key held no other route. Written by '
  'scripts/load_announcement_links.py (and migration 020 for 2026-09-19).';
comment on column budget_line_awards.superseded_evidence is
  'NULL when the loader recorded the move as it made it; otherwise the '
  'evidence a later record of the move rests on (migration 020, R-DEC-140).';
