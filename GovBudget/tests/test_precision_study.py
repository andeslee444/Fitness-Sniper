"""scripts/precision_study.py — draw / load / tally (ROADMAP #72, #79).

The session-scoped `pg_dsn` fixture is never truncated between tests, so every
test uses its own sample_id and, where it needs published rows, its own
method name or piid prefix. Sample ids here are prefixed `0-` so they sort
BELOW the ISO-dated runs tests/test_export_site_link_precision.py seeds on the
same published method names: that file's per-method-LATEST assertions hold
whichever file runs first.
"""
import json

import psycopg
import pytest

from precision_study import (  # scripts/ is on sys.path via conftest
    RUBRICS,
    draw_sample,
    enrich_packets,
    load_verdicts,
    precision_by_method,
)


def test_sample_is_deterministic_and_stratified(pg_dsn):
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("""insert into budget_line_awards
            (pe_bli, exhibit, fiscal_year, organization, award_piid, method, confidence)
            select '0601101E','R-1',2026,'DARPA','P'||g, 'announcement+lexicon','high'
            from generate_series(1,80) g""")
        pg.execute("""insert into budget_line_awards
            (pe_bli, exhibit, fiscal_year, organization, award_piid, method, confidence)
            select '0601101E','R-1',2026,'DARPA','Q'||g, 'subaward+lexicon','medium'
            from generate_series(1,10) g""")
        pg.commit()
    a = draw_sample(pg_dsn, per_method=20, seed=7, rubric="attribution")
    b = draw_sample(pg_dsn, per_method=20, seed=7, rubric="attribution")
    assert a == b
    by = {}
    for r in a:
        by.setdefault(r["method"], 0)
        by[r["method"]] += 1
    assert by["announcement+lexicon"] == 20
    assert by["subaward+lexicon"] == 10   # fewer rows than per_method: take all


def test_every_packet_carries_its_rubric_and_the_question_it_asks(pg_dsn):
    """#79: adding a stratum to a draw obliges the operator to state the
    question; the packet carries it so the adjudicator answers THAT one."""
    packets = draw_sample(pg_dsn, per_method=3, seed=1, rubric="attribution",
                          methods=("announcement+lexicon",))
    assert packets, "fixture rows from the test above"
    for p in packets:
        assert p["rubric"] == "attribution"
        assert p["question"] == RUBRICS["attribution"]
        assert p["question"].startswith("Does this award execute this program element?")


def test_draw_refuses_an_unknown_rubric(pg_dsn):
    with pytest.raises(ValueError, match="rubric must be one of"):
        draw_sample(pg_dsn, per_method=3, seed=1, rubric="vibes")
    with pytest.raises(TypeError):
        draw_sample(pg_dsn, per_method=3, seed=1)  # rubric is keyword-only and required


def test_enrich_attaches_program_evidence_and_says_when_the_lake_is_absent(pg_dsn, tmp_path):
    """The attribution question cannot be answered from the packet the 2026-09-04
    draw wrote (method/piid/pe/recipient/rationale); it needs the program's
    title, mission narrative and project titles, and the award's lake row.
    On the fixture DB there is no parquet lake, and the packet must SAY so
    rather than carry an empty award silently."""
    with psycopg.connect(pg_dsn, autocommit=True) as pg:
        doc_id = pg.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year, title,"
            " source_url, sha256, status) values ('DARPA', 'rdte', 2026, 'enrich-doc',"
            " 'https://example.test/enrich-015.pdf', 'enrich015', 'downloaded')"
            " returning id").fetchone()[0]
        run_id = pg.execute(
            "insert into extraction_runs (document_id, tier, tool_versions, status)"
            " values (%s, 1, '{}', 'finished') returning id", (doc_id,)).fetchone()[0]
        pg.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " budget_activity, line_number, pe_bli, title, amount_type, amount_thousands,"
            " source_document_id) values ('R-1', 2026, '0400D', 'DARPA', '02', '9',"
            " 'ENR0602E', 'Enrichment Technology', 'fy_2026_request', 1, %s)", (doc_id,))
        pg.execute(
            "insert into detail_narratives (extraction_run_id, document_id, pe_bli, kind,"
            " title, body, xml_path, superseded) values"
            " (%s, %s, 'ENR0602E', 'mission', 'Enrichment Technology',"
            "  'The Enrichment Technology PE develops terahertz devices.', 'PE[1]', false),"
            " (%s, %s, 'ENR0602E', 'accomplishment_planned_program', 'Terahertz Electronics',"
            "  'body', 'PE[1]/P[1]', false),"
            " (%s, %s, 'ENR0602E', 'accomplishment_planned_program', 'Old Project',"
            "  'body', 'PE[1]/P[2]', true)",
            (run_id, doc_id, run_id, doc_id, run_id, doc_id))
    lexicon = tmp_path / "lexicon.jsonl"
    lexicon.write_text(
        json.dumps({"pe_bli": "ENR0602E", "name": "THz Electronics", "ownership": "own",
                    "kind": "program", "doc_id": "1", "quote": "THz"}) + "\n"
        + json.dumps({"pe_bli": "ENR0602E", "name": "Not Ours", "ownership": "mentioned",
                      "kind": "program", "doc_id": "1", "quote": "x"}) + "\n")
    packets = [{"method": "account+subagency", "rubric": "attribution",
                "question": RUBRICS["attribution"], "piid": "HR0011ENRICH",
                "pe_bli": "ENR0602E", "recipient": "X", "rationale": "account 097-0400"}]
    out = enrich_packets(packets, pg_dsn,
                         contracts_glob=str(tmp_path / "nope" / "fy=*" / "*.parquet"),
                         lexicon_path=lexicon)
    prog = out[0]["program"]
    assert prog["title"] == "Enrichment Technology"
    assert "terahertz" in prog["mission"].lower()
    assert prog["projects"] == [{"number": None, "title": "Terahertz Electronics"}]
    assert prog["lexicon_own"] == ["THz Electronics"]
    assert "lake" in out[0]["award"] and "no contracts parquet" in out[0]["award"]["lake"]


def test_precision_counts_only_confirmed(pg_dsn):
    # P1..P3 are published announcement+lexicon links seeded by the first test
    # (budget_line_awards P1..P80). The tally JOINS the sample to
    # budget_line_awards and counts under the method the link publishes under
    # today, so those published rows are what makes these rows countable.
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("""insert into link_precision_samples
            (sample_id, award_piid, pe_bli, method, rubric, verdict, reason)
            values ('0-s1','P1','0601101E','announcement+lexicon','attribution','confirmed','ok'),
                   ('0-s1','P2','0601101E','announcement+lexicon','attribution','refuted','platform mention'),
                   ('0-s1','P3','0601101E','announcement+lexicon','attribution',null,null)""")
        pg.commit()
    got = precision_by_method(pg_dsn, sample_id="0-s1")
    assert got["announcement+lexicon"] == (1, 2)  # unjudged rows excluded


def test_a_sampled_link_the_corpus_no_longer_publishes_is_not_counted(pg_dsn):
    """ROADMAP #72 final review C1: a sampled link since deleted (or demoted
    below medium) is evidence about no published tier, in either direction."""
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("""insert into budget_line_awards
            (pe_bli, exhibit, fiscal_year, organization, award_piid, method, confidence)
            values ('0601101E','R-1',2026,'DARPA','WITHDRAWN-KEPT','announcement+lexicon','high'),
                   ('0601101E','R-1',2026,'DARPA','WITHDRAWN-LOW','announcement+lexicon','low')""")
        pg.execute("""insert into link_precision_samples
            (sample_id, award_piid, pe_bli, method, rubric, verdict, reason)
            values ('0-s-withdrawn','WITHDRAWN-KEPT','0601101E','announcement+lexicon','attribution','confirmed','ok'),
                   ('0-s-withdrawn','WITHDRAWN-LOW','0601101E','announcement+lexicon','attribution','refuted','demoted'),
                   ('0-s-withdrawn','WITHDRAWN-GONE','0601101E','announcement+lexicon','attribution','refuted','deleted')""")
        pg.commit()
    assert precision_by_method(pg_dsn, sample_id="0-s-withdrawn") == {
        "announcement+lexicon": (1, 1)
    }


def test_the_tier_a_link_publishes_under_today_owns_its_verdict(pg_dsn):
    """The `fpds-ap+account` shape: a link drawn under a withdrawn tier is
    counted under the tier that absorbed it, not the dead one."""
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("""insert into budget_line_awards
            (pe_bli, exhibit, fiscal_year, organization, award_piid, method, confidence)
            values ('0601101E','R-1',2026,'DARPA','MOVED-1','fpds-ap','medium'),
                   ('0601101E','R-1',2026,'DARPA','MOVED-2','fpds-ap','medium')""")
        pg.execute("""insert into link_precision_samples
            (sample_id, award_piid, pe_bli, method, rubric, verdict, reason)
            values ('0-s-moved','MOVED-1','0601101E','fpds-ap+account','attribution','confirmed','ok'),
                   ('0-s-moved','MOVED-2','0601101E','fpds-ap+account','attribution','refuted','sibling line')""")
        pg.commit()
    got = precision_by_method(pg_dsn, sample_id="0-s-moved")
    assert "fpds-ap+account" not in got
    assert got == {"fpds-ap": (1, 2)}


def test_rule_fired_verdicts_are_excluded_from_the_published_tally(pg_dsn):
    """#79: the filter is the rubric, not a method name. A rule-fired verdict
    on ANY method is not evidence of program attribution."""
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("""insert into budget_line_awards
            (pe_bli, exhibit, fiscal_year, organization, award_piid, method, confidence)
            values ('0601101E','R-1',2026,'DARPA','RF-1','rf-test','medium'),
                   ('0601101E','R-1',2026,'DARPA','RF-2','rf-test','medium')""")
        pg.execute("""insert into link_precision_samples
            (sample_id, award_piid, pe_bli, method, rubric, verdict, reason)
            values ('0-s-rf','RF-1','0601101E','rf-test','rule-fired','confirmed','rule fired'),
                   ('0-s-rf','RF-2','0601101E','rf-test','rule-fired','confirmed','rule fired')""")
        pg.commit()
    assert precision_by_method(pg_dsn, sample_id="0-s-rf") == {}
    assert precision_by_method(pg_dsn, sample_id="0-s-rf", rubric="rule-fired") == {"rf-test": (2, 2)}
    with pytest.raises(ValueError, match="rubric must be one of"):
        precision_by_method(pg_dsn, sample_id="0-s-rf", rubric="vibes")


def test_a_stratum_rejudged_in_a_later_run_replaces_only_its_own_figure(pg_dsn):
    """#79 ruling 1: per-method latest run. Run A judged two methods; run B
    (later) re-judged one of them. B's figure replaces A's for that method;
    the other method keeps A's figure; nothing pools."""
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("""insert into budget_line_awards
            (pe_bli, exhibit, fiscal_year, organization, award_piid, method, confidence)
            values ('0601101E','R-1',2026,'DARPA','LR-A1','lr-alpha','medium'),
                   ('0601101E','R-1',2026,'DARPA','LR-A2','lr-alpha','medium'),
                   ('0601101E','R-1',2026,'DARPA','LR-B1','lr-beta','medium'),
                   ('0601101E','R-1',2026,'DARPA','LR-B2','lr-beta','medium'),
                   ('0601101E','R-1',2026,'DARPA','LR-B3','lr-beta','medium')""")
        pg.execute("""insert into link_precision_samples
            (sample_id, award_piid, pe_bli, method, rubric, verdict, reason)
            values ('0-lr-2026-01-01','LR-A1','0601101E','lr-alpha','attribution','confirmed','a'),
                   ('0-lr-2026-01-01','LR-A2','0601101E','lr-alpha','attribution','confirmed','a'),
                   ('0-lr-2026-01-01','LR-B1','0601101E','lr-beta','attribution','confirmed','b'),
                   ('0-lr-2026-01-01','LR-B2','0601101E','lr-beta','attribution','refuted','b'),
                   ('0-lr-2026-02-01','LR-B2','0601101E','lr-beta','attribution','refuted','b again'),
                   ('0-lr-2026-02-01','LR-B3','0601101E','lr-beta','attribution','refuted','b again')""")
        pg.commit()
    # No sample_id: every method takes its own latest run. lr-alpha only
    # exists in the January run; lr-beta's February run replaces January's.
    got = precision_by_method(pg_dsn)
    assert got["lr-alpha"] == (2, 2)
    assert got["lr-beta"] == (0, 2)      # NOT (1, 4): January's lr-beta rows did not pool in
    # Explicit sample_id restricts to that run only.
    assert precision_by_method(pg_dsn, sample_id="0-lr-2026-01-01")["lr-beta"] == (1, 2)


def test_load_verdicts_requires_and_records_the_rubric(pg_dsn, tmp_path):
    method = "load-verdicts-test"
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("""insert into budget_line_awards
            (pe_bli, exhibit, fiscal_year, organization, award_piid, method, confidence)
            values ('0601101E','R-1',2026,'DARPA','L1',%s,'medium'),
                   ('0601101E','R-1',2026,'DARPA','L2',%s,'medium')
            on conflict do nothing""", (method, method))
        pg.commit()
    verdicts_path = tmp_path / "verdicts.json"
    verdicts_path.write_text(json.dumps([
        {"piid": "L1", "pe_bli": "0601101E", "method": method,
         "verdict": "confirmed", "reason": "ok"},
        {"piid": "L2", "pe_bli": "0601101E", "method": method,
         "verdict": "refuted", "reason": "platform mention"},
    ]))
    with pytest.raises(TypeError):
        load_verdicts(pg_dsn, "0-study-x", verdicts_path)          # rubric is required
    with pytest.raises(ValueError, match="rubric must be one of"):
        load_verdicts(pg_dsn, "0-study-x", verdicts_path, rubric="vibes")

    assert load_verdicts(pg_dsn, "0-study-x", verdicts_path, rubric="attribution") == 2
    assert precision_by_method(pg_dsn, sample_id="0-study-x")[method] == (1, 2)
    with psycopg.connect(pg_dsn) as pg:
        rubrics = pg.execute(
            "select distinct rubric from link_precision_samples"
            " where sample_id = '0-study-x'"
        ).fetchall()
    assert rubrics == [("attribution",)]

    # Re-running load with a corrected verdict for the same (sample_id,
    # award_piid, pe_bli) upserts in place rather than duplicating the row.
    verdicts_path.write_text(json.dumps([
        {"piid": "L1", "pe_bli": "0601101E", "method": method,
         "verdict": "confirmed", "reason": "ok"},
        {"piid": "L2", "pe_bli": "0601101E", "method": method,
         "verdict": "confirmed", "reason": "re-reviewed: platform mention was wrong"},
    ]))
    assert load_verdicts(pg_dsn, "0-study-x", verdicts_path, rubric="attribution") == 2
    assert precision_by_method(pg_dsn, sample_id="0-study-x")[method] == (2, 2)


def test_load_rejects_a_verdict_that_is_neither_confirmed_nor_refuted(pg_dsn, tmp_path):
    verdicts_path = tmp_path / "bad.json"
    verdicts_path.write_text(json.dumps([
        {"piid": "BAD-1", "pe_bli": "0601101E", "method": "bad-test",
         "verdict": "maybe", "reason": "unsure"},
    ]))
    with pytest.raises(ValueError, match=r"verdict must be confirmed\|refuted"):
        load_verdicts(pg_dsn, "0-study-bad", verdicts_path, rubric="attribution")


def test_load_refuses_to_mix_rubrics_inside_one_run(pg_dsn, tmp_path):
    """A re-judgement under another question is a NEW sample_id. Overwriting
    the rule-fired rows with attribution verdicts would destroy the audit
    record the 2026-09-04 review kept on purpose."""
    verdicts_path = tmp_path / "v.json"
    verdicts_path.write_text(json.dumps([
        {"piid": "MIX-1", "pe_bli": "0601101E", "method": "mix-test",
         "verdict": "confirmed", "reason": "rule fired"},
    ]))
    assert load_verdicts(pg_dsn, "0-study-mix", verdicts_path, rubric="rule-fired") == 1
    with pytest.raises(ValueError, match="already holds 1 verdict"):
        load_verdicts(pg_dsn, "0-study-mix", verdicts_path, rubric="attribution")
    # A verdict row that names a rubric other than the one being loaded is
    # refused before anything is written.
    verdicts_path.write_text(json.dumps([
        {"piid": "MIX-2", "pe_bli": "0601101E", "method": "mix-test",
         "rubric": "attribution", "verdict": "confirmed", "reason": "x"},
    ]))
    with pytest.raises(ValueError, match="says rubric 'attribution'"):
        load_verdicts(pg_dsn, "0-study-mix-2", verdicts_path, rubric="rule-fired")
