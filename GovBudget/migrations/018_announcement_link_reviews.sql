-- 018: announcement_link_reviews — the announcement path's RECORDED review
-- outcomes, one row per (crosswalk link of a reviewed pair, review record)
-- (ROADMAP #110, decided 2026-09-25 under the owner's delegation: backfill the
-- recorded review outcomes so they are gateable; stage-1 follow-up ruling
-- R-DEC-110, 2026-09-26: a wave 1-3 `surviving` entry IS a recorded review;
-- fix-round-2 ruling R-DEC-110b, 2026-09-26: the held-out precision study's
-- refutations are recorded refutations too).
--
-- THE GAP. /methodology/ says every announcement candidate "is judged by an
-- agent reviewer and challenged by an independent adversarial reviewer, and
-- only links surviving both publish". Until this table, that review wrote no
-- row anywhere in Postgres: award_pe_adjudications holds the 60 two-lens
-- adjudications of the mechanical tiers, and nothing held the announcement
-- path's. The review was recorded only in the wave files on disk.
--
-- WHAT A ROW IS. scripts/backfill_announcement_link_reviews.py writes one row
-- per review RECORD a wave file (or the precision study) holds, in one of
-- four kinds (record_kind):
--
--   verdict_pair       a wave-4 proposal (wave4_verdicts/chunk_*.json): the
--                      agent reviewer's own verdict — 'link', 'weak' or
--                      'wrong' — and, for 'link', the two adversarial refute
--                      lenses (refute_a / refute_b). A 'weak' / 'wrong'
--                      proposal never reached the lenses: adversarial_verdict
--                      'not_run'. Names the announcement it read (article_id,
--                      article_source 'verdict_file') and the paragraph
--                      (record_index).
--   survivor_list      a wave 1-3 result file's `surviving` entry {piid,
--                      pe_bli, reason}: the pair the reviewer proposed as a
--                      'link' AND the adversarial refuter did not refute
--                      (waves 1-2 carry a refutations_sample; survivors are
--                      the unrefuted). reviewer 'link', adversarial 'upheld',
--                      the entry's reason kept verbatim. The entry names no
--                      article: article_id is the id of the ONE packet that
--                      wave triaged for the pair (wave<N>_chunks/, article_
--                      source 'wave_packet') — NULL when the wave's packets
--                      for the pair name none (the wave-3 subaward packets)
--                      or more than one.
--   refutation_sample  a wave 1-2 result file's `refutations_sample` entry
--                      {piid, pe_bli, refuted: true, reason}: a proposed
--                      'link' the refuter refuted. reviewer 'link',
--                      adversarial 'refuted'; article as for survivor_list.
--                      A SAMPLE (40 per wave): the other refutations of
--                      waves 1-2 were recorded only as counts.
--   precision_sample   a held-out precision-study verdict (Postgres
--                      link_precision_samples) of verdict 'refuted' under the
--                      'attribution' rubric (R-DEC-110b): reviewer 'link'
--                      (the study judged a published link), adversarial
--                      'refuted' (its two-lens verdict). It names NO article:
--                      the study judged the (award, PE) pair, so the record
--                      binds to the pair. source_file is the sample_id,
--                      entry_index the link_precision_samples row's id (the
--                      exact join back to the verdict), and reason begins
--                      'drawn from the <method> tier of held-out precision
--                      sample <sample_id> (rubric attribution), judged
--                      refuted' — <method> is the tier the sample drew the
--                      link from — then the adjudicator's reason. It is
--                      attached ONLY to the pair's budget_line_awards rows of
--                      that method (the link the sample drew); a pair whose
--                      drawn link was since replaced by another route gets
--                      none. It is not an announcement-pipeline review: the
--                      grading reads it only as a refutation of the pair.
--
-- The granularity differs by kind and is stated, never hidden: a verdict
-- pair records both reviewers per proposal and per lens; a survivor list
-- records one pair-level outcome of both (proposed, not refuted).
--
-- THE LINK IDENTITY. No wave file names an exhibit or a fiscal year: the link
-- loader stamps them (budget_line_awards). A record of (award_piid, pe_bli) is
-- attached to EVERY budget_line_awards row of that pair (on 2026-09-26 each
-- reviewed pair held exactly one row; a precision_sample, only to the rows of
-- the method it was drawn from); (award_piid, pe_bli, exhibit,
-- fiscal_year) is budget_line_awards' own unique key, so the join is exact.
-- `cites_reviewed_article` says whether the pair's award_link_sources rows
-- cite the article this record read, so a gate can tell "the reviewers
-- upheld/rejected the evidence the card cites" from "they judged the pair on
-- another article"; NULL when the record names no article.
--
-- THE KEY. One pair can be reviewed more than once (wave 4 re-proposed pairs
-- waves 1-2 had published; some pairs were proposed from more than one
-- paragraph). A row is keyed by the file it came from, its kind, and its
-- position in that file's list (entry_index) — one wave-1 result file holds
-- both a surviving list and a refutations sample. A precision_sample is keyed
-- by its sample_id and its link_precision_samples row id.
--
-- VOCABULARY (closed by CHECK):
--   reviewer_verdict     'link' | 'weak' | 'wrong' — the agent reviewer's
--                        (always 'link' on the list kinds and precision_sample)
--   adversarial_verdict  'upheld'     every lens returned refuted=false (a
--                                     list kind: the refuter did not refute)
--                        'refuted'    at least one lens returned refuted=true
--                        'incomplete' no lens refuted, but at least one lens
--                                     is missing or not a JSON boolean — the
--                                     wave-4 collector kept it out of its
--                                     survivors (scripts/mine_announcement_residue.py),
--                                     but the GRADING reads it as neither an
--                                     uphold nor a refutation: it never binds
--                                     as a refutation of a cited article
--                                     (R-DEC-INCOMPLETE, 2026-09-26)
--                                     — a precision_sample is always
--                                     'refuted' (only refutations are
--                                     backfilled)
--                        'not_run'    no lens recorded a verdict: every
--                                     reviewer rejection, and one wave-4
--                                     'link' no lens answered
--   adversarial_lenses_passed  lenses that returned refuted=false (0-2) on a
--                        verdict pair whose lenses ran; NULL on the list kinds
--                        (their files record no per-lens outcome) and on
--                        'not_run'
--   upholds              reviewer_verdict = 'link' and adversarial_verdict =
--                        'upheld' — stored so a predicate is one column.
--
-- reviewed_at is NULL on every row the backfill writes: no wave file carries a
-- review timestamp (commit 1c30122b, 2026-09-19, only bounds the wave-4
-- files); a precision_sample's adjudicated_at stays on its
-- link_precision_samples row (join on entry_index). recorded_at is the backfill's own transaction time; `jbooks
-- export-facts` refuses to export a table recorded before the link loader's
-- last run (chain order: migrate -> loader -> backfill -> export-facts -> dbt).
--
-- export_facts exports every column but recorded_at to data/parquet/jbooks/
-- announcement_link_reviews.parquet (dbt source jbook_announcement_link_reviews).
create table if not exists announcement_link_reviews (
    award_piid                 text not null,
    pe_bli                     text not null,
    exhibit                    text not null,
    fiscal_year                integer not null,
    record_kind                text not null,
    reviewer_verdict           text not null,
    adversarial_verdict        text not null,
    adversarial_lenses_passed  integer,
    upholds                    boolean not null,
    article_id                 text,
    article_source             text,
    record_index               integer,
    entry_index                integer not null,
    cites_reviewed_article     boolean,
    reason                     text,
    reviewed_at                date,
    source_file                text not null,
    recorded_at                timestamptz not null default now(),
    primary key (award_piid, pe_bli, exhibit, fiscal_year,
                 source_file, record_kind, entry_index),
    constraint announcement_link_reviews_record_kind_check
        check (record_kind in ('verdict_pair', 'survivor_list',
                               'refutation_sample', 'precision_sample')),
    constraint announcement_link_reviews_reviewer_verdict_check
        check (reviewer_verdict in ('link', 'weak', 'wrong')),
    constraint announcement_link_reviews_adversarial_verdict_check
        check (adversarial_verdict in ('upheld', 'refuted', 'incomplete',
                                       'not_run')),
    -- a reviewer rejection never reaches the adversarial lenses
    constraint announcement_link_reviews_rejection_not_run_check
        check (reviewer_verdict = 'link' or adversarial_verdict = 'not_run'),
    -- each list kind (and a precision sample) records exactly one outcome pair
    constraint announcement_link_reviews_kind_outcome_check
        check ((record_kind <> 'survivor_list'
                or (reviewer_verdict = 'link' and adversarial_verdict = 'upheld'))
           and (record_kind not in ('refutation_sample', 'precision_sample')
                or (reviewer_verdict = 'link' and adversarial_verdict = 'refuted'))),
    -- a precision sample names no article (it binds to the pair) and states
    -- the tier it was drawn from at the head of its reason (R-DEC-110b)
    constraint announcement_link_reviews_precision_sample_check
        check (record_kind <> 'precision_sample'
            or (article_id is null
                and reason is not null
                and reason like 'drawn from the % tier of held-out precision sample % (rubric attribution), judged refuted%')),
    -- a lens count exists exactly on a verdict pair whose lenses ran
    constraint announcement_link_reviews_lenses_check
        check ((adversarial_lenses_passed is null)
                = (record_kind <> 'verdict_pair' or adversarial_verdict = 'not_run')
           and (adversarial_lenses_passed is null
                or adversarial_lenses_passed between 0 and 2)),
    constraint announcement_link_reviews_upholds_check
        check (upholds = (reviewer_verdict = 'link'
                          and adversarial_verdict = 'upheld')),
    -- an article, where it came from, and whether the card cites it: all or none
    constraint announcement_link_reviews_article_check
        check ((article_id is null) = (article_source is null)
           and (article_id is null) = (cites_reviewed_article is null)
           and (article_source is null
                or article_source in ('verdict_file', 'wave_packet'))),
    -- a verdict pair names its article and paragraph; a list entry names
    -- neither (its article is the wave's packet) and keeps the file's reason
    constraint announcement_link_reviews_kind_shape_check
        check ((record_kind = 'verdict_pair'
                and article_source = 'verdict_file'
                and record_index is not null
                and reason is null)
            or (record_kind <> 'verdict_pair'
                and (article_source is null or article_source = 'wave_packet')
                and record_index is null))
);

create index if not exists ix_announcement_link_reviews_pair
    on announcement_link_reviews (award_piid, pe_bli);

comment on table announcement_link_reviews is
  'The announcement path''s recorded review outcomes (ROADMAP #110, R-DEC-110): '
  'one row per (crosswalk link of a reviewed pair, review record) — wave-4 '
  'verdict pairs (reviewer verdict + both refute lenses, reviewer rejections '
  'with adversarial not_run), wave 1-3 survivor-list entries (link + upheld), '
  'wave 1-2 refutation-sample entries (link + refuted) and the held-out '
  'precision study''s refuted attribution verdicts (precision_sample, link + '
  'refuted, no article: binds to the pair; R-DEC-110b). A link with no '
  'pipeline row (verdict_pair / survivor_list / refutation_sample) has no '
  'recorded review.';
