-- 020: record the 60 route moves of the 2026-09-19 announcement load
-- (ROADMAP #140; stage-1 follow-up ruling R-DEC-140, 2026-09-26: "before the
-- loader next runs, record the 60 historical moves from the best evidence
-- available; where a prior route cannot be recovered, record it as unknown
-- with the aggregate breakdown cited").
--
-- THE MOVES. scripts/load_announcement_links.py, run 2026-09-19
-- 04:10:37.770102-04 (the created_at of every row that load inserted), upserted
-- 60 announcement links onto keys another route held and overwrote those rows
-- in place (Task 25b report). Their prior rows exist nowhere (no Postgres
-- copy; the 2026-09-24 rollback parquet postdates the load). What survives:
--
--   * each moved row's created_at — the upsert keeps it. 58 carry
--     2026-09-04 18:28:01.819115-04: the one transaction that wrote EVERY
--     stored fpds-ap row (38,964, measured 2026-09-25) and no row of another
--     method (39,022 rows carry that time: those 38,964 and these 58). Their
--     route was fpds-ap. 2 carry a 2026-06-10 time of the DARPA mechanical
--     crosswalk run, whose transactions wrote account / account+subagency /
--     account+tokens rows only.
--   * the aggregate: the load moved fpds-ap medium 1,910 -> 1,865 (45), low
--     37,112 -> 37,099 (13), account low 114,638 -> 114,637 (1),
--     account+subagency medium 9,337 -> 9,336 (1) (Task 25b report).
--   * 6 of the 58 pairs sit in the 2026-09-04 precision sample
--     (link_precision_samples) under an fpds-ap stratum — drawn from published
--     links that afternoon, before the 18:28 transaction: it corroborates the
--     route, not the confidence the 18:28 transaction gave.
--   * data/research/adjudication_pairs.json (commit b2923030, 2026-09-01)
--     records both DARPA pairs published at medium on 2026-09-01; which one
--     was account/low by 2026-09-19 is recorded nowhere.
--
-- So: 58 keys record superseded_method 'fpds-ap' with confidence 'unknown';
-- 2 record 'unknown' / 'unknown'. superseded_at is the load's own transaction
-- time; superseded_evidence cites the above per key. Nothing is re-derived: a
-- route recomputed today would be a reconstruction, not a record.
--
-- WHY A MIGRATION. The evidence is each row's created_at, and the loader's
-- next run deletes and re-inserts every row it owns (new created_at), erasing
-- it. Migrations run first (chain: migrate -> loader -> backfill ->
-- export-facts -> dbt), and the loader refuses to write while any migration
-- is unapplied (load_announcement_links.require_migrations). A key is
-- recorded only if its row still carries the created_at the evidence rests on
-- and has no record yet. The migration then REFUSES to finish when:
--   (a) any of the 60 keys is held by an announcement+lexicon /
--       subaward+lexicon row that carries no record and whose created_at no
--       longer matches the evidence — a loader run WITHOUT the migration
--       guard (the pre-wave loader) rebuilt it and erased the evidence; this
--       leg does not depend on (b), so a rebuild that erased every
--       2026-09-19 transaction time is refused too (fix round 2, 2026-09-26);
--   (b) the 2026-09-19 load is still the table's latest (rows carrying its
--       transaction time exist) and fewer than all 60 keys carry a record.
-- On a database where none of the 60 keys is held by those two methods (a
-- fresh or test database, or a key another route holds again) it matches
-- nothing and does nothing.
drop table if exists pg_temp.r140_moves;
create temp table r140_moves (
    pe_bli      text not null,
    exhibit     text not null,
    fiscal_year integer not null,
    award_piid  text not null,
    created_at  timestamptz not null,
    method      text not null,
    confidence  text not null,
    ev          text not null
) on commit drop;

insert into r140_moves values
    ('0603286E', 'R-1', 2026, 'HR001116C0110', timestamptz '2026-06-10 19:00:22.083813-04', 'unknown', 'unknown', 'mechanical_split'),
    ('0603766E', 'R-1', 2026, 'HR001114C0054', timestamptz '2026-06-10 19:00:26.365822-04', 'unknown', 'unknown', 'mechanical_split'),
    ('0101328F', 'R-1', 2026, 'FA821920C0001', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('0102110F', 'R-1', 2026, 'FA873918C5030', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('0204229N', 'R-1', 2026, 'N0001919C0083', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('0204460M', 'R-1', 2026, 'M6785415C0230', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('0207325F', 'R-1', 2026, 'FA868218C0009', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('0576', 'P-1', 2026, 'N0001919F0046', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('0576', 'P-1', 2026, 'N0001920C0002', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('0603892C', 'R-1', 2026, 'HQ027610C0001', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('0604307N', 'R-1', 2026, 'N0002413C5116', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn_sampled'),
    ('0648CC0007', 'P-1', 2026, 'W31P4Q13C0129', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1203164SF', 'R-1', 2026, 'FA880712C0012', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn_sampled'),
    ('1206432SF', 'R-1', 2026, 'FA880819C0004', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1206855SF', 'R-1', 2026, 'FA880820C0047', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003014C0100', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003015C0100', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003016C0100', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003017C0008', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003017C0100', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003018C0100', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003019C0100', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003020C0100', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003021C0008', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1250', 'P-1', 2026, 'N0003023C6008', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('1338C70000', 'P-1', 2026, 'W31P4Q11C0242', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2013', 'P-1', 2026, 'N0002409C4137', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2013', 'P-1', 2026, 'N0002412C2115', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn_sampled'),
    ('2013', 'P-1', 2026, 'N0002415C4103', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn_sampled'),
    ('2013', 'P-1', 2026, 'N0002417C2100', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2013', 'P-1', 2026, 'N0002420C2120', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2013', 'P-1', 2026, 'N0002421C4106', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2013', 'P-1', 2026, 'N0002424C2110', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2073GZ0410', 'P-1', 2026, 'W56HZV17C0001', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2122', 'P-1', 2026, 'N0002410C2310', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2122', 'P-1', 2026, 'N0002418C2305', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn_sampled'),
    ('2122', 'P-1', 2026, 'N0002418C2307', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2122', 'P-1', 2026, 'N0002418C2312', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2122', 'P-1', 2026, 'N0002418C2313', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2127', 'P-1', 2026, 'N0002411C2300', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2127', 'P-1', 2026, 'N0002417C2301', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2127', 'P-1', 2026, 'N0002418C2300', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2127', 'P-1', 2026, 'N6278619F0055', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2128', 'P-1', 2026, 'N0002420C2300', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2606', 'P-1', 2026, 'N0002412C5231', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2606', 'P-1', 2026, 'N0002413C5212', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2606', 'P-1', 2026, 'N0002420C5203', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('2944G80819', 'P-1', 2026, 'W56HZV23C0024', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('3225', 'P-1', 2026, 'N0002411C6404', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('353620', 'P-1', 2026, 'FA821317F1001', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('4655', 'P-1', 2026, 'M6785419C0043', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('6005C64400', 'P-1', 2026, 'W31P4Q16C0102', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('8260C53101', 'P-1', 2026, 'W31P4Q17C0006', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('8260C53101', 'P-1', 2026, 'W31P4Q23F0003', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('8540C29600', 'P-1', 2026, 'W31P4Q23C0052', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('NSSL00', 'P-1', 2026, 'FA881118C0003', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('NSSL00', 'P-1', 2026, 'FA881119C0002', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('SDB002', 'P-1', 2026, 'FA867220C0005', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn'),
    ('SDB002', 'P-1', 2026, 'FA867221C0005', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn_sampled'),
    ('SDB002', 'P-1', 2026, 'FA867225CB001', timestamptz '2026-09-04 18:28:01.819115-04', 'fpds-ap', 'unknown', 'fpds_ap_txn');

drop table if exists pg_temp.r140_evidence;
create temp table r140_evidence (ev text primary key, evidence text not null)
    on commit drop;
insert into r140_evidence values
    ('fpds_ap_txn',
     'R-DEC-140 (recorded from evidence 2026-09-26, not at the move): the'
     || ' replaced row was created 2026-09-04 18:28:01.819115-04 by the one'
     || ' transaction that wrote every stored fpds-ap row and no row of another'
     || ' method, so its route was fpds-ap. Its confidence was not recorded per'
     || ' key: the 58 fpds-ap rows the 2026-09-19 load took were 45 medium and'
     || ' 13 low (Task 25b report: fpds-ap medium 1,910 -> 1,865, low 37,112 ->'
     || ' 37,099). Moved by the load of 2026-09-19 04:10:37.770102-04.'),
    ('fpds_ap_txn_sampled',
     'R-DEC-140 (recorded from evidence 2026-09-26, not at the move): the'
     || ' replaced row was created 2026-09-04 18:28:01.819115-04 by the one'
     || ' transaction that wrote every stored fpds-ap row and no row of another'
     || ' method, so its route was fpds-ap; the 2026-09-04 precision sample'
     || ' (drawn from published links before that transaction) also holds this'
     || ' pair under an fpds-ap stratum. Its confidence was not recorded per'
     || ' key: the 58 fpds-ap rows the 2026-09-19 load took were 45 medium and'
     || ' 13 low (Task 25b report: fpds-ap medium 1,910 -> 1,865, low 37,112 ->'
     || ' 37,099). Moved by the load of 2026-09-19 04:10:37.770102-04.'),
    ('mechanical_split',
     'R-DEC-140 (recorded from evidence 2026-09-26, not at the move): the'
     || ' replaced row was created 2026-06-10 by the DARPA mechanical crosswalk'
     || ' (its transactions wrote account / account+subagency / account+tokens'
     || ' rows only). Which one it was is not recorded per key: of the two'
     || ' mechanical rows the 2026-09-19 load took (HR001116C0110/0603286E and'
     || ' HR001114C0054/0603766E) one was account/low and one'
     || ' account+subagency/medium (Task 25b report: account low 114,638 ->'
     || ' 114,637, account+subagency medium 9,337 -> 9,336);'
     || ' data/research/adjudication_pairs.json (commit b2923030) records both'
     || ' pairs published at medium on 2026-09-01. Moved by the load of'
     || ' 2026-09-19 04:10:37.770102-04.');

update budget_line_awards b
   set superseded_method = v.method,
       superseded_confidence = v.confidence,
       superseded_at = timestamptz '2026-09-19 04:10:37.770102-04',
       superseded_evidence = e.evidence
  from r140_moves v
  join r140_evidence e on e.ev = v.ev
 where b.pe_bli = v.pe_bli and b.exhibit = v.exhibit
   and b.fiscal_year = v.fiscal_year and b.award_piid = v.award_piid
   and b.created_at = v.created_at
   and b.method in ('announcement+lexicon', 'subaward+lexicon')
   and b.superseded_method is null;

do $$
declare
    n_load integer;
    n_recorded integer;
    n_erased integer;
begin
    -- (b) the 2026-09-19 load still in place: all 60 must carry a record.
    select count(*) into n_load from budget_line_awards
     where created_at = timestamptz '2026-09-19 04:10:37.770102-04'
       and method in ('announcement+lexicon', 'subaward+lexicon');
    if n_load > 0 then
        select count(*) into n_recorded
          from budget_line_awards b
          join r140_moves v
            on b.pe_bli = v.pe_bli and b.exhibit = v.exhibit
           and b.fiscal_year = v.fiscal_year and b.award_piid = v.award_piid
         where b.superseded_method is not null;
        if n_recorded <> 60 then
            raise exception '020 (R-DEC-140): the 2026-09-19 load is still in place (% row(s) carry its transaction time) but % of the 60 moves it made carry a record: a key whose created_at no longer matches has lost its evidence. Nothing recorded; investigate before the loader runs.', n_load, n_recorded;
        end if;
    end if;
    -- (a) evidence erased before this migration ran: a loader-owned row of a
    -- moved key with no record and another created_at. Checked WHATEVER
    -- n_load is — an unguarded rebuild leaves no 2026-09-19 row behind, and
    -- a database like that must not pass as a fresh one (migrate tracks by
    -- file name: a silent no-op would mark 020 applied for good).
    select count(*) into n_erased
      from budget_line_awards b
      join r140_moves v
        on b.pe_bli = v.pe_bli and b.exhibit = v.exhibit
       and b.fiscal_year = v.fiscal_year and b.award_piid = v.award_piid
     where b.method in ('announcement+lexicon', 'subaward+lexicon')
       and b.superseded_method is null
       and b.created_at <> v.created_at;
    if n_erased > 0 then
        raise exception '020 (R-DEC-140): % of the 60 moved key(s) are held by an announcement/subaward row that carries no record and whose created_at no longer matches the evidence: a loader run without the migration guard rebuilt them and erased the evidence this migration records from. Nothing recorded; restore budget_line_awards from the pre-chain backup before migrating.', n_erased;
    end if;
end $$;
