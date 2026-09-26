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

-- recipient_basis (R-DEC-RECIPIENT, fix-round-5 ruling 2026-09-26): HOW a
-- link's recipient was decided, written by the two loaders that pick one.
-- One award can carry several recipient UEIs; the rule is (1) the UEI with
-- the largest total obligation on the award ('obligation' — also every award
-- with one UEI), (2) among a tie for that largest total, including all-$0,
-- the UEI the link's cited announcement names ('announcement_named', the
-- announcement loader only), (3) only then the lowest UEI ('uei_tiebreak').
-- scripts/load_announcement_links.py applies (1)-(3); scripts/derive_ap_links.py
-- applies (1) and (3) (an FPDS link cites no announcement).
--
-- 'pre_rule' (R-DEC-DERIVE, fix-round-6 ruling 2026-09-26): a row one of
-- those two loaders wrote BEFORE the rule — its recipient is the scan-order
-- any_value pick an earlier run stored, now a fixed value. derive_ap_links is
-- not re-run in chain G (a re-derive also changes the fpds-ap link set), so
-- the 38,964 stored fpds-ap rows keep their recipients and are recorded here
-- as 'pre_rule'. The backfill below writes it onto every existing row of the
-- two loaders' methods (derive_ap_links owns 'fpds-ap%', which it deletes
-- and rewrites; load_announcement_links owns announcement+lexicon and
-- subaward+lexicon) that carries no basis; on the production database,
-- read-only 2026-09-26, that is fpds-ap 38,964 + announcement+lexicon 1,075 +
-- subaward+lexicon 114 = 40,153 rows. The announcement loader's next run
-- (chain G: migrate -> loader) deletes and rewrites its own rows with the
-- rule's basis; the fpds-ap rows keep 'pre_rule' until a reviewed re-derive.
-- No loader writes 'pre_rule': both refuse a row whose basis is not one of
-- the rule's three (derive_ap_links.incoming_member_claims).
--
-- NULL: a row neither loader wrote — the mechanical crosswalk's account*
-- rows (jbooks/crosswalk.py picks their recipient its own way; R-DEC-RECIPIENT
-- does not govern it, so 'pre_rule' would claim a rule that never applies).
-- Added to 019 while 019 was unapplied on the production database
-- (schema_migrations stopped at 017, checked read-only 2026-09-26).
alter table budget_line_awards
    add column if not exists recipient_basis text;

alter table budget_line_awards
    drop constraint if exists budget_line_awards_recipient_basis_known;
alter table budget_line_awards
    add constraint budget_line_awards_recipient_basis_known
    check (recipient_basis is null
           or recipient_basis in ('obligation', 'announcement_named',
                                  'uei_tiebreak', 'pre_rule'));

-- the backfill: only rows with no basis, so a basis a loader recorded is never
-- overwritten and re-executing this file changes nothing further. It touches
-- recipient_basis alone (migration 020 matches rows by their created_at).
update budget_line_awards
   set recipient_basis = 'pre_rule'
 where recipient_basis is null
   and (method like 'fpds-ap%'
        or method in ('announcement+lexicon', 'subaward+lexicon'));

-- 'pre_rule' says a recipient-picking loader wrote the row; on any other
-- method it would claim a rule that never governed that recipient.
alter table budget_line_awards
    drop constraint if exists budget_line_awards_pre_rule_is_a_loaders_row;
alter table budget_line_awards
    add constraint budget_line_awards_pre_rule_is_a_loaders_row
    check (recipient_basis is distinct from 'pre_rule'
           or method like 'fpds-ap%'
           or method in ('announcement+lexicon', 'subaward+lexicon'));

comment on column budget_line_awards.recipient_basis is
  'How recipient_name/recipient_uei were decided (R-DEC-RECIPIENT): '
  '''obligation'' (the UEI with the largest total obligation), '
  '''announcement_named'' (a tie broken by the UEI the cited announcement '
  'names) or ''uei_tiebreak'' (the lowest UEI of a tie); ''pre_rule'' '
  '(R-DEC-DERIVE) on a row the announcement or FPDS loader wrote before the '
  'rule, whose recipient is the value that earlier run stored. NULL on rows '
  'neither loader wrote (the mechanical crosswalk''s account* rows).';
