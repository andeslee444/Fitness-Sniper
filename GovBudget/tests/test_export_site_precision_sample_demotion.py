"""R-DEC-110b (controller, 2026-09-26): a link the held-out precision study
itself refuted is demoted (dbt: demotion_reason 'precision_sample_refuted'),
and that demotion must never flatter the study's own figure.

"The precision tally keeps every sampled link in the tier it was DRAWN from
when its demotion came from its own sample verdict — the measured precision
is never flattered by the demotion." Every other link keeps the tier it
publishes under today (#140).

The failure this guards: the tally counts only links the corpus still
publishes. If the demotion ever takes a refuted sampled link out of the
published population, its 'refuted' verdict leaves numerator AND denominator
and the tier's precision goes UP because the study caught an error. A
demotion high -> medium keeps the link published under the same method, so
the tally already survives that one; these tests pin it anyway and cover the
shapes that would not.

Also: `link_adjudication.high.demoted_from_high` counts the new reason like
every other (R-DEC-110b rides on R-DEC-110's by-reason census).

Run against the fixture Postgres (root conftest's `pg_dsn`).
"""
from __future__ import annotations

import ast
import inspect

import psycopg
import pytest

from govbudget import export_site
from govbudget.export_site import (
    _link_adjudication_block,
    _link_precision_block,
    _link_precision_for_export,
)

MARKER = "precision-sample-demotion-test"
RUN = "2026-09-04"
REASON = "precision_sample_refuted"
ANN = "announcement+lexicon"
FPDS = "fpds-ap"
METHODS = {ANN, FPDS}


def _link(piid, pe, method, reason=None):
    row = {"award_piid": piid, "pe_bli": pe, "method": method}
    if reason is not None:
        row["demotion_reason"] = reason
    return row


@pytest.fixture()
def sampled(pg_dsn):
    """One run's attribution verdicts, `method` = the tier each was DRAWN from:

      PS-A1, PS-A2  announcement+lexicon  confirmed
      PS-A3         announcement+lexicon  refuted   <- the self-refuted link
      PS-F1         fpds-ap               confirmed
      PS-X1         fpds-ap+account       refuted   <- publishes today under
                                                       announcement+lexicon
                                                       (a #140 override move,
                                                       like FA880712C0012)
    """
    rows = [
        ("PS-A1", "S0603286E", ANN, "confirmed"),
        ("PS-A2", "S0603286E", ANN, "confirmed"),
        ("PS-A3", "S0603286E", ANN, "refuted"),
        ("PS-F1", "S0604000F", FPDS, "confirmed"),
        ("PS-X1", "S0605000F", "fpds-ap+account", "refuted"),
    ]
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from link_precision_samples where reason = %s", (MARKER,))
        for piid, pe, method, verdict in rows:
            pg.execute(
                "insert into link_precision_samples (sample_id, award_piid,"
                " pe_bli, method, rubric, verdict, reason, adjudicated_at)"
                " values (%s, %s, %s, %s, 'attribution', %s, %s,"
                " '2026-09-04 12:00:00-04'::timestamptz)",
                (RUN, piid, pe, method, verdict, MARKER))
        pg.commit()
    yield pg_dsn
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from link_precision_samples where reason = %s", (MARKER,))
        pg.commit()


#: The mart BEFORE any demotion: every sampled link publishes (PS-A3 at high).
BEFORE = [
    _link("PS-A1", "S0603286E", ANN),
    _link("PS-A2", "S0603286E", ANN),
    _link("PS-A3", "S0603286E", ANN),
    _link("PS-F1", "S0604000F", FPDS),
]


def _methods(block):
    return {m: (v["confirmed"], v["sampled"]) for m, v in block["methods"].items()}


def _precision(dsn, **kw):
    with psycopg.connect(dsn) as pg:
        return _link_precision_block(pg, published_methods=METHODS, **kw)


def test_the_baseline_counts_the_refuted_link_in_its_tier(sampled):
    assert _methods(_precision(sampled, published_links=BEFORE)) == {
        ANN: (2, 3), FPDS: (1, 1)}


def test_demoting_a_refuted_sampled_link_to_medium_does_not_change_its_tier(sampled):
    """The shape dbt ships (R-DEC-110b): PS-A3 falls high -> medium and keeps
    publishing under the same method. Its tier still reads 2 of 3."""
    before = _precision(sampled, published_links=BEFORE)
    after = _precision(
        sampled, published_links=BEFORE,
        demoted_links=[_link("PS-A3", "S0603286E", ANN, REASON)])
    assert _methods(after) == _methods(before) == {ANN: (2, 3), FPDS: (1, 1)}
    assert "withdrawn" not in after


def test_a_demotion_out_of_publication_still_counts_the_link_where_it_was_drawn(sampled):
    """The shape that WOULD flatter: the demotion takes PS-A3 out of the
    published population (it lands in the withdrawn rows). Counted by
    "publishes today" alone, the tier would read 2 of 2 — 100% because the
    study caught an error. It must still read 2 of 3, and a self-refuted link
    is not a withdrawn TIER: no `withdrawn` figure is invented for it."""
    before = _precision(sampled, published_links=BEFORE)
    after = _precision(
        sampled,
        published_links=[r for r in BEFORE if r["award_piid"] != "PS-A3"],
        withdrawn_links=[_link("PS-A3", "S0603286E", ANN, REASON)])
    assert _methods(after) == _methods(before) == {ANN: (2, 3), FPDS: (1, 1)}
    assert "withdrawn" not in after


def test_a_withdrawn_tier_keeps_its_own_figure_beside_a_self_refuted_link(sampled):
    """Only the self-refuted row leaves the withdrawn population: a tier dbt
    demoted out of publication for another reason keeps its `withdrawn`
    figure exactly as before (#107(b))."""
    withdrawn_tier = _link("PS-F1", "S0604000F", FPDS, "account_subagency_not_pinned")
    block = _precision(
        sampled,
        published_links=[_link("PS-A1", "S0603286E", ANN),
                         _link("PS-A2", "S0603286E", ANN)],
        withdrawn_links=[withdrawn_tier,
                         _link("PS-A3", "S0603286E", ANN, REASON)])
    assert _methods(block) == {ANN: (2, 3)}
    assert block["withdrawn"] == {
        FPDS: {"confirmed": 1, "sampled": 1, "sample_id": RUN,
               "judged": "2026-09-04", "links": 1,
               "demotion_reasons": ["account_subagency_not_pinned"]},
    }


def test_other_demotion_reasons_keep_the_tier_the_link_publishes_under_today(sampled):
    """The drawn-tier rule is R-DEC-110b's, for a demotion its OWN sample
    verdict caused. PS-X1 was drawn under fpds-ap+account and publishes today
    under announcement+lexicon (#140): demoted for a pipeline review, it
    counts where it publishes, as every link did before the ruling."""
    published = BEFORE + [_link("PS-X1", "S0605000F", ANN)]
    before = _precision(sampled, published_links=published)
    after = _precision(
        sampled, published_links=published,
        demoted_links=[_link("PS-X1", "S0605000F", ANN,
                             "announcement_review_refuted")])
    assert _methods(after) == _methods(before) == {ANN: (2, 4), FPDS: (1, 1)}


def test_a_self_refuted_link_whose_drawn_tier_differs_is_not_moved_and_is_named(
        sampled, capsys):
    """PS-X1 is the one shape where "the tier it was DRAWN from"
    (fpds-ap+account) is not the tier its verdict counts in (announcement+
    lexicon, where #140 counts a moved link). Moving it at its demotion would
    drop a 'refuted' verdict from the announcement figure — 2 of 4 would
    become 2 of 3, the flattering R-DEC-110b forbids — so it stays where it
    counted, and the export log names the pair and both tiers for a ruling."""
    published = BEFORE + [_link("PS-X1", "S0605000F", ANN)]
    before = _precision(sampled, published_links=published)
    capsys.readouterr()
    after = _precision(
        sampled, published_links=published,
        demoted_links=[_link("PS-X1", "S0605000F", ANN, REASON)])
    assert _methods(after) == _methods(before) == {ANN: (2, 4), FPDS: (1, 1)}
    out = capsys.readouterr().out
    assert "WARNING" in out
    assert "PS-X1/S0605000F" in out
    assert "fpds-ap+account" in out and ANN in out


def test_the_rule_honours_the_pin(sampled):
    """The export pins announcement+lexicon to its 2026-09-04 run; the
    self-refuted link stays in that pinned figure too."""
    with psycopg.connect(sampled) as pg:
        block = _link_precision_block(
            pg, published_methods=METHODS,
            published_links=[r for r in BEFORE if r["award_piid"] != "PS-A3"],
            withdrawn_links=[_link("PS-A3", "S0603286E", ANN, REASON)],
            pinned_samples={ANN: RUN})
    assert _methods(block) == {ANN: (2, 3), FPDS: (1, 1)}


def test_the_export_twin_threads_the_demotions(sampled):
    """`_link_precision_for_export` is what the export calls: it must pass
    the demotions through to the block."""
    with psycopg.connect(sampled) as pg:
        block = _link_precision_for_export(
            pg, METHODS,
            published_links=[r for r in BEFORE if r["award_piid"] != "PS-A3"],
            withdrawn_links=[_link("PS-A3", "S0603286E", ANN, REASON)],
            demoted_links=[])
    assert _methods(block)[ANN] == (2, 3)


def test_the_export_call_site_passes_the_marts_demotions():
    """Bound where it can break (the R-25b-1 lesson: a kwarg deleted from the
    call site leaves every unit test green). The export's own call of
    `_link_precision_for_export` must pass `demoted_links`."""
    tree = ast.parse(inspect.getsource(export_site.export_site))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "_link_precision_for_export"
    ]
    assert len(calls) == 1
    kwargs = {kw.arg: kw.value for kw in calls[0].keywords}
    assert "demoted_links" in kwargs
    assert getattr(kwargs["demoted_links"], "id", None) == "demoted_links"


# ═══════════════════════════════════════════════════════════════════════════
# link_adjudication.high.demoted_from_high counts the new reason
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def one_high_link(pg_dsn):
    """One adjudicated high link so `_link_adjudication_block` has a census."""
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from award_pe_adjudications")
        pg.execute("delete from award_link_sources")
        pg.execute("delete from budget_line_awards")
        pg.execute(
            "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
            " organization, award_piid, method, confidence)"
            " values ('S0601101E', 'R-1', 2026, %s, 'PS-H1', 'account', 'high')",
            (MARKER,))
        pg.execute(
            "insert into award_pe_adjudications (award_piid, pe_bli,"
            " adjudicated_confidence, award_verdict, pair_reason,"
            " refuter_lenses_passed, adjudicated_at) values ('PS-H1',"
            " 'S0601101E', 'high', 'pinned', 'pinned-here', 2,"
            " '2026-09-01 12:00:00-04'::timestamptz)")
        pg.commit()
    yield pg_dsn
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from award_pe_adjudications")
        pg.execute("delete from budget_line_awards where organization = %s", (MARKER,))
        pg.commit()


def test_demoted_from_high_counts_the_precision_sample_reason(one_high_link):
    demoted = [
        _link("PS-A3", "S0603286E", ANN, REASON),
        _link("PS-A4", "S0603286E", ANN, REASON),
        _link("PS-A5", "S0603286E", ANN, "announcement_reviewer_rejected"),
    ]
    with psycopg.connect(one_high_link) as pg:
        block = _link_adjudication_block(
            pg, high_links=[("PS-H1", "S0601101E", "account")],
            measured_on="2026-09-26", demoted_links=demoted)
    assert block["high"]["demoted_from_high"] == {
        "links": 3,
        "by_reason": {"announcement_reviewer_rejected": 1, REASON: 2},
        "by_path": {ANN: {"announcement_reviewer_rejected": 1, REASON: 2}},
    }
