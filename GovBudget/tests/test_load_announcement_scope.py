"""scripts/load_announcement_scope.py — the write side of the derived
/methodology/ scope figures (ROADMAP findings log :118-119).

Two guards live here, and both exist because the read side cannot see what
they check:

  * `scope_row` publishes what was ADJUDICATED — the chunks that came back —
    and refuses a result file whose own record count disagrees with the
    manifest's for those chunks. A pass stopped halfway must publish the
    smaller true number, not the queued one.
  * `check_precision_sample` refuses a precision run that judges a pair this
    wave did not produce. /methodology/ says the pair measures THIS pass's
    links; export_site only names the run, so the claim is made true here.
"""
import psycopg
import pytest

from load_announcement_scope import (  # scripts/ on sys.path via tests/conftest.py
    check_precision_sample,
    new_links_published,
    scope_row,
)

MANIFEST = {
    "records_with_lake_piid": 100,
    "records_deterministic": 40,
    "records_residue": 60,
    "value_residue": 1000,
    # 12 ENTRIES / 500 handed to the earlier pass, of which 10 records / 400
    # are still in today's residue: two entries duplicate a key, and one record
    # the lexicon now matches deterministically has left the residue. Only the
    # in-residue pair may be added to wave 4's count (fix round 1, item 1).
    "earlier_pass": {"name": "wave2-llm-alias", "records": 12,
                     "distinct_records": 11, "value": 500,
                     "records_in_residue": 10, "value_in_residue": 400},
    "chunks": [
        {"file": "chunk_000_A.json", "records": 5, "announced_value": 100},
        {"file": "chunk_001_A.json", "records": 7, "announced_value": 250},
        {"file": "chunk_002_N.json", "records": 9, "announced_value": 300},
    ],
}


def test_only_the_adjudicated_chunks_count():
    row = scope_row(
        MANIFEST,
        {"chunks_attempted": ["chunk_000_A.json", "chunk_001_A.json"],
         "records_attempted": 12},
        "2026-09-19",
    )
    (as_of, total, deterministic, residue, attempted, v_residue, v_attempted,
     note, sid, new_links) = row
    assert (as_of, total, deterministic, residue) == ("2026-09-19", 100, 40, 60)
    # the earlier pass's IN-RESIDUE 10 / 400, never its 12 entries / 500
    assert attempted == 10 + 12          # earlier pass + the two chunks
    assert (v_residue, v_attempted) == (1000, 400 + 350)
    assert "2 of 3 chunks adjudicated" in note
    assert (sid, new_links) == (None, None)


def test_a_chunk_the_manifest_does_not_know_is_refused():
    with pytest.raises(SystemExit, match="chunk_404_A.json"):
        scope_row(MANIFEST,
                  {"chunks_attempted": ["chunk_404_A.json"], "records_attempted": 5},
                  "2026-09-19")


def test_a_result_file_disagreeing_with_the_manifest_is_refused():
    """The count the page publishes has two independent sources; when they
    disagree the run stops instead of picking one."""
    with pytest.raises(SystemExit, match="11775|manifest says"):
        scope_row(MANIFEST,
                  {"chunks_attempted": ["chunk_000_A.json"], "records_attempted": 11775},
                  "2026-09-19")


@pytest.fixture()
def sample(pg_dsn):
    sid = "LAS-2026-09-12"
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from link_precision_samples where sample_id = %s", (sid,))
        pg.commit()
    yield pg_dsn, sid
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from link_precision_samples where sample_id = %s", (sid,))
        pg.commit()


def _judge(pg, sid, piid, pe_bli, rubric="attribution"):
    pg.execute(
        "insert into link_precision_samples (sample_id, award_piid, pe_bli, method,"
        " rubric, verdict, adjudicated_at) values (%s,%s,%s,'announcement+lexicon',"
        " %s,'confirmed', now())", (sid, piid, pe_bli, rubric))


RESULT = {"surviving": [{"piid": "LAS-1", "pe_bli": "0603286E"},
                        {"piid": "LAS-2", "pe_bli": " 0604256N "}]}


def test_a_sample_of_this_waves_survivors_is_accepted(sample):
    dsn, sid = sample
    with psycopg.connect(dsn) as pg:
        _judge(pg, sid, "LAS-1", "0603286E")
        # the survivor list is stripped before comparison, like the packets are
        _judge(pg, sid, "LAS-2", "0604256N")
        pg.commit()
        assert check_precision_sample(pg, sid, RESULT) == 2


def test_a_sample_judging_a_pair_this_wave_never_produced_is_refused(sample):
    dsn, sid = sample
    with psycopg.connect(dsn) as pg:
        _judge(pg, sid, "LAS-1", "0603286E")
        _judge(pg, sid, "LAS-OTHER", "0605502F")
        pg.commit()
        with pytest.raises(SystemExit, match="LAS-OTHER"):
            check_precision_sample(pg, sid, RESULT)


def test_an_unjudged_sample_id_is_refused(sample):
    dsn, sid = sample
    with psycopg.connect(dsn) as pg:
        with pytest.raises(SystemExit, match="no verdict"):
            check_precision_sample(pg, sid, RESULT)


def test_an_audit_rubric_sample_is_refused(sample):
    """Only 'attribution' verdicts are ever published as precision; a run
    judged on whether the mechanical rule fired must not become one."""
    dsn, sid = sample
    with psycopg.connect(dsn) as pg:
        _judge(pg, sid, "LAS-1", "0603286E", rubric="rule-fired")
        pg.commit()
        with pytest.raises(SystemExit, match="rule-fired"):
            check_precision_sample(pg, sid, RESULT)


def test_a_manifest_without_the_in_residue_fields_is_refused():
    """The earlier pass's ENTRY count is not a subset of today's residue — it
    double-counts duplicate paragraphs and includes records the lexicon has
    since learned to match. A manifest generated before
    `mine_announcement_residue.earlier_pass_in_residue` existed carries only
    the entry count, and the loader must stop rather than publish it as a
    share OF the residue."""
    stale = {**MANIFEST,
             "earlier_pass": {"name": "wave2-llm-alias", "records": 12, "value": 500}}
    with pytest.raises(SystemExit, match="records_in_residue"):
        scope_row(stale,
                  {"chunks_attempted": ["chunk_000_A.json"], "records_attempted": 5},
                  "2026-09-19")


# ── the frame the tier-wide draw could not cover (fix round 1, item 2) ───────
#
# /methodology/ publishes the announcement tier's precision from the
# 2026-09-04 stratified draw over the tier as it stood. This pass adds links to
# that tier AFTER the draw, and the page has to say how many — derived, not
# typed. `new_links_published` is where the count comes from: pairs this wave
# produced that no earlier wave did, and that the corpus publishes today under
# announcement+lexicon.


@pytest.fixture()
def published_links(pg_dsn):
    org = "LAS-new-links"
    rows = [
        # (piid, pe_bli, method, confidence)
        ("LAS-NEW-1", "0603286E", "announcement+lexicon", "high"),
        ("LAS-OLD-1", "0603286E", "announcement+lexicon", "high"),
        ("LAS-LOW-1", "0603286E", "announcement+lexicon", "low"),
        ("LAS-SUB-1", "0603286E", "subaward+lexicon", "medium"),
    ]
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from budget_line_awards where organization = %s", (org,))
        for piid, pe, method, conf in rows:
            pg.execute(
                "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
                " organization, award_piid, method, confidence)"
                " values (%s, 'R-1', 2026, %s, %s, %s, %s)",
                (pe, org, piid, method, conf))
        pg.commit()
    yield pg_dsn
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from budget_line_awards where organization = %s", (org,))
        pg.commit()


WAVE4 = {"surviving": [
    {"piid": "LAS-NEW-1", "pe_bli": "0603286E"},   # counted
    {"piid": "LAS-OLD-1", "pe_bli": " 0603286E "},  # an earlier wave has it too
    {"piid": "LAS-LOW-1", "pe_bli": "0603286E"},   # not published
    {"piid": "LAS-SUB-1", "pe_bli": "0603286E"},   # published, other tier
    {"piid": "LAS-GONE", "pe_bli": "0603286E"},    # no row at all
]}
EARLIER = [{"surviving": [{"piid": "LAS-OLD-1", "pe_bli": "0603286E"}]}]


def test_only_this_waves_own_published_announcement_links_are_counted(published_links):
    with psycopg.connect(published_links) as pg:
        assert new_links_published(pg, WAVE4, EARLIER) == 1


def test_a_wave_that_added_no_link_of_its_own_counts_zero(published_links):
    """Every survivor is one an earlier wave already produced: the tier's draw
    predates none of them, and the page must not claim a frame gap."""
    earlier = [{"surviving": WAVE4["surviving"]}]
    with psycopg.connect(published_links) as pg:
        assert new_links_published(pg, WAVE4, earlier) == 0
