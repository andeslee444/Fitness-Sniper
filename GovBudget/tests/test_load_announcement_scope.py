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

from load_announcement_scope import check_precision_sample, scope_row  # scripts/ (conftest)

MANIFEST = {
    "records_with_lake_piid": 100,
    "records_deterministic": 40,
    "records_residue": 60,
    "value_residue": 1000,
    "earlier_pass": {"name": "wave2-llm-alias", "records": 10, "value": 400},
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
    as_of, total, deterministic, residue, attempted, v_residue, v_attempted, note, sid = row
    assert (as_of, total, deterministic, residue) == ("2026-09-19", 100, 40, 60)
    assert attempted == 10 + 12          # earlier pass + the two chunks
    assert (v_residue, v_attempted) == (1000, 400 + 350)
    assert "2 of 3 chunks adjudicated" in note
    assert sid is None


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
