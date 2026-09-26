"""site_meta.link_precision — the held-out study, tallied under the tier each
sampled link publishes under TODAY, under ONE rubric (ROADMAP #72 C1/C2/I1;
#79).

The defect these tests pin (2026-09-04): /methodology/ printed "Measured
precision of the published tiers: … fpds-ap 60/60; fpds-ap+account 34/60 …"
while `fpds-ap+account` had been WITHDRAWN, and "account+subagency 60/60"
whose 60 verdicts had answered a DIFFERENT question (did the rule fire).
Every number↔citation gate was green — the figures were true of the wrong
population and the wrong question.

Run against the fixture Postgres (root conftest's `pg_dsn`), so the SQL under
test is the SQL that runs in production, not a hand-rolled stand-in.
"""
import datetime as dt

import duckdb
import psycopg
import pytest

from govbudget import export_site
from govbudget.export_site import (
    _link_adjudication_block,
    _link_precision_block,
    _published_high_links,
)
from precision_study import precision_by_method  # scripts/ on sys.path (conftest)


@pytest.fixture()
def seeded(pg_dsn):
    """A miniature of the corpus across three study runs.

    budget_line_awards is the PUBLISHED state; link_precision_samples records
    what each link's method was when the sample was drawn, and the rubric it
    was judged under. The two disagree on purpose:

      * LPB-P1/LPB-P2 were drawn as 'fpds-ap+account' (the withdrawn high tier)
        and now publish as 'fpds-ap' medium — they must land in the fpds-ap tally;
      * LPB-P3 was drawn and still publishes as 'fpds-ap';
      * LPB-A1/LPB-A2 publish as 'announcement+lexicon' high;
      * LPB-A3 was drawn as 'announcement+lexicon' and is GONE from
        budget_line_awards — it must count toward neither number;
      * LPB-S1 was drawn as 'account+subagency' and has been demoted to
        'account'/low — unpublished, so it drops out too;
      * LPB-G1/LPB-G2 publish as 'account+subagency' medium. In the 2026-09-04
        run LPB-G1 was judged under 'rule-fired' (never published); in the
        2026-09-05 run both were judged under 'attribution';
      * LPB-U1 belongs to an older run (2026-08-01) and must never pool in.
    """
    marker = "lp-block-test"
    runs = ("2026-08-01", "2026-09-04", "2026-09-05")
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from link_precision_samples where sample_id = any(%s)", (list(runs),))
        pg.execute("delete from budget_line_awards where organization = %s", (marker,))
        rows = [
            # (piid, pe_bli, published method, published confidence)
            ("LPB-P1", "LPB0601101E", "fpds-ap", "medium"),
            ("LPB-P2", "LPB0601101E", "fpds-ap", "medium"),
            ("LPB-P3", "LPB0601101E", "fpds-ap", "medium"),
            ("LPB-A1", "LPB0603286E", "announcement+lexicon", "high"),
            ("LPB-A2", "LPB0603286E", "announcement+lexicon", "high"),
            ("LPB-S1", "LPB0604256N", "account", "low"),
            ("LPB-G1", "LPB0604256N", "account+subagency", "medium"),
            ("LPB-G2", "LPB0604256N", "account+subagency", "medium"),
            ("LPB-U1", "LPB0605502F", "fpds-ap", "medium"),
        ]
        for piid, pe_bli, method, conf in rows:
            pg.execute(
                "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
                " organization, award_piid, method, confidence)"
                " values (%s, 'R-1', 2026, %s, %s, %s, %s)",
                (pe_bli, marker, piid, method, conf),
            )
        samples = [
            # (sample_id, piid, pe_bli, method AT DRAW TIME, rubric, verdict, judged)
            ("2026-08-01", "LPB-U1", "LPB0605502F", "fpds-ap", "attribution", "refuted",
             "2026-08-01 09:00:00-04"),
            ("2026-09-04", "LPB-P1", "LPB0601101E", "fpds-ap+account", "attribution", "confirmed",
             "2026-09-04 14:58:54-04"),
            ("2026-09-04", "LPB-P2", "LPB0601101E", "fpds-ap+account", "attribution", "refuted",
             "2026-09-04 14:58:54-04"),
            ("2026-09-04", "LPB-P3", "LPB0601101E", "fpds-ap", "attribution", "confirmed",
             "2026-09-04 14:58:54-04"),
            ("2026-09-04", "LPB-A1", "LPB0603286E", "announcement+lexicon", "attribution",
             "confirmed", "2026-09-04 14:58:54-04"),
            ("2026-09-04", "LPB-A2", "LPB0603286E", "announcement+lexicon", "attribution",
             "refuted", "2026-09-04 14:58:54-04"),
            ("2026-09-04", "LPB-A3", "LPB0603286E", "announcement+lexicon", "attribution",
             "refuted", "2026-09-04 14:58:54-04"),
            ("2026-09-04", "LPB-S1", "LPB0604256N", "account+subagency", "rule-fired",
             "confirmed", "2026-09-04 14:58:54-04"),
            ("2026-09-04", "LPB-G1", "LPB0604256N", "account+subagency", "rule-fired",
             "confirmed", "2026-09-04 14:58:54-04"),
            ("2026-09-05", "LPB-G1", "LPB0604256N", "account+subagency", "attribution",
             "confirmed", "2026-09-05 11:00:00-04"),
            ("2026-09-05", "LPB-G2", "LPB0604256N", "account+subagency", "attribution",
             "refuted", "2026-09-05 11:00:00-04"),
        ]
        for sid, piid, pe_bli, method, rubric, verdict, judged in samples:
            pg.execute(
                "insert into link_precision_samples (sample_id, award_piid, pe_bli,"
                " method, rubric, verdict, reason, adjudicated_at)"
                " values (%s, %s, %s, %s, %s, %s, 'fixture', %s::timestamptz)",
                (sid, piid, pe_bli, method, rubric, verdict, judged),
            )
        pg.commit()
    yield pg_dsn
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from link_precision_samples where sample_id = any(%s)", (list(runs),))
        pg.execute("delete from budget_line_awards where organization = %s", (marker,))
        pg.commit()


PUBLISHED = {
    "account",
    "account+subagency",
    "account+tokens",
    "announcement+lexicon",
    "fpds-ap",
    "subaward+lexicon",
}


def _cn(block, method):
    return (block["methods"][method]["confirmed"], block["methods"][method]["sampled"])


def test_the_hand_named_stratum_set_is_gone():
    """#79: the filter is the rubric column, not a set someone has to remember
    to edit after the next study."""
    assert not hasattr(export_site, "_UNRUBRICKED_PRECISION_STRATA")


def test_withdrawn_tier_disappears_and_its_links_land_in_the_tier_they_publish_under(seeded):
    """C1: the figure describes the tier a reader can actually meet."""
    with psycopg.connect(seeded) as pg:
        block = _link_precision_block(pg, published_methods=PUBLISHED)

    assert "fpds-ap+account" not in block["methods"]
    # LPB-P1 confirmed + LPB-P2 refuted (drawn as fpds-ap+account) + LPB-P3 confirmed.
    assert _cn(block, "fpds-ap") == (2, 3)


def test_sampled_links_the_corpus_no_longer_publishes_count_toward_neither_number(seeded):
    with psycopg.connect(seeded) as pg:
        block = _link_precision_block(pg, published_methods=PUBLISHED)

    # LPB-A1 confirmed + LPB-A2 refuted; LPB-A3 (gone) excluded.
    assert _cn(block, "announcement+lexicon") == (1, 2)
    # LPB-S1 now publishes as 'account'/low — no figure is minted for it.
    assert "account" not in block["methods"]


def test_rule_fired_verdicts_never_publish_and_the_stratum_is_named_unmeasured_until_rejudged(seeded):
    """C2 as a column: read the 2026-09-04 run alone (before the attribution
    re-study existed) — account+subagency has verdicts, but not under the
    published rubric, so it carries no figure and is named unmeasured."""
    with psycopg.connect(seeded) as pg:
        block = _link_precision_block(pg, published_methods=PUBLISHED, sample_id="2026-09-04")

    assert block["rubric"] == "attribution"
    assert "account+subagency" not in block["methods"]
    assert "account+subagency" in block["unmeasured"]


def test_a_stratum_rejudged_on_attribution_in_a_later_run_replaces_only_its_own_figure(seeded):
    """#79 ruling 1: per-method latest run. The 2026-09-05 run judged ONLY
    account+subagency; it must not erase the other tiers' 2026-09-04 figures,
    and the rule-fired 2026-09-04 verdict for LPB-G1 must not pool in."""
    with psycopg.connect(seeded) as pg:
        block = _link_precision_block(pg, published_methods=PUBLISHED)

    assert block["methods"]["account+subagency"] == {
        "confirmed": 1, "sampled": 2, "sample_id": "2026-09-05", "judged": "2026-09-05",
    }
    assert block["methods"]["fpds-ap"]["sample_id"] == "2026-09-04"
    assert block["methods"]["fpds-ap"]["judged"] == "2026-09-04"
    assert "account+subagency" not in block["unmeasured"]
    assert block["sample_id"] == "2026-09-05"
    assert block["sampled_at"] == "2026-09-05"


def test_the_rubric_is_a_filter_not_a_label(seeded):
    """Asking for the audit rubric returns ONLY rows judged under it."""
    with psycopg.connect(seeded) as pg:
        audit = _link_precision_block(pg, published_methods=PUBLISHED, rubric="rule-fired")

    assert audit["rubric"] == "rule-fired"
    assert set(audit["methods"]) == {"account+subagency"}
    # LPB-G1 (published medium) counts; LPB-S1 (demoted to low) does not.
    assert _cn(audit, "account+subagency") == (1, 1)
    with psycopg.connect(seeded) as pg, pytest.raises(ValueError, match="rubric must be one of"):
        _link_precision_block(pg, published_methods=PUBLISHED, rubric="vibes")


def test_every_published_tier_is_either_measured_or_named_unmeasured(seeded):
    """The invariant gate 24 leg n enforces on the rendered page."""
    with psycopg.connect(seeded) as pg:
        block = _link_precision_block(pg, published_methods=PUBLISHED)

    assert set(block["methods"]) | set(block["unmeasured"]) == PUBLISHED
    assert not set(block["methods"]) & set(block["unmeasured"])
    # Tiers the study never drew from surface as unmeasured, not as absent.
    assert "account+tokens" in block["unmeasured"]
    assert "subaward+lexicon" in block["unmeasured"]


def test_an_older_run_never_pools_into_the_one_that_replaced_it(seeded):
    """I1: LPB-U1 (2026-08-01, fpds-ap) must not enter the fpds-ap denominator."""
    with psycopg.connect(seeded) as pg:
        block = _link_precision_block(pg, published_methods=PUBLISHED)
        older = _link_precision_block(pg, published_methods=PUBLISHED, sample_id="2026-08-01")

    assert block["methods"]["fpds-ap"]["sampled"] == 3
    assert _cn(older, "fpds-ap") == (0, 1)
    assert older["sample_id"] == "2026-08-01"


def test_no_study_yields_an_empty_block(pg_dsn):
    """The /methodology/ paragraph stays absent rather than rendering an
    empty 'measured precision' claim (gate 24 leg n's other direction)."""
    with psycopg.connect(pg_dsn) as pg:
        assert _link_precision_block(pg, sample_id="no-such-study") == {}


def test_precision_study_twin_agrees_with_the_exporter(seeded):
    """scripts/precision_study.py owns the CLI; export_site runs the same
    query — both import govbudget.link_precision since 2026-09-25, so they
    agree by construction. This stays the check that they do, under both
    rubrics and both run selections.

    Lookups, not dict equality: the session DB also holds the rows
    tests/test_precision_study.py seeds under its own method names, and the
    CLI has no published-method universe to filter them out with, so it
    legitimately returns more keys than the exporter's block.
    """
    with psycopg.connect(seeded) as pg:
        block = _link_precision_block(pg, published_methods=PUBLISHED)
        block_0904 = _link_precision_block(pg, published_methods=PUBLISHED, sample_id="2026-09-04")
        audit = _link_precision_block(pg, published_methods=PUBLISHED, rubric="rule-fired")

    cli = precision_by_method(seeded)
    for method, figures in block["methods"].items():
        assert cli[method] == (figures["confirmed"], figures["sampled"]), method
    cli_0904 = precision_by_method(seeded, sample_id="2026-09-04")
    for method, figures in block_0904["methods"].items():
        assert cli_0904[method] == (figures["confirmed"], figures["sampled"]), method
    assert precision_by_method(seeded, rubric="rule-fired")["account+subagency"] == (1, 1)
    assert set(audit["methods"]) == {"account+subagency"}


@pytest.fixture()
def seeded_wave(seeded):
    """`seeded` plus a NEWER announcement+lexicon run under the id the real
    wave-4 sample carries (2026-09-12): both published announcement links
    re-judged, both confirmed. Unpinned, "latest run" makes it the tier's
    figure (2/2); the export pins the tier to 2026-09-04 (1/2 — LPB-A3 no
    longer publishes)."""
    with psycopg.connect(seeded) as pg:
        for piid in ("LPB-A1", "LPB-A2"):
            pg.execute(
                "insert into link_precision_samples (sample_id, award_piid, pe_bli,"
                " method, rubric, verdict, reason, adjudicated_at)"
                " values ('2026-09-12', %s, 'LPB0603286E', 'announcement+lexicon',"
                " 'attribution', 'confirmed', 'fixture',"
                " '2026-09-19 04:10:00-04'::timestamptz)",
                (piid,),
            )
        pg.commit()
    yield seeded
    with psycopg.connect(seeded) as pg:
        pg.execute("delete from link_precision_samples where sample_id = '2026-09-12'"
                   " and award_piid like 'LPB-%'")
        pg.commit()


def test_the_cli_twin_carries_the_exporters_pin(seeded_wave):
    """Task 26 (confirmed finding): the CLI twin never got the 2026-09-19 pin,
    so an operator reading `report` saw the one-wave sample as the tier's
    figure while the page published the pinned run. The pin is now ONE
    constant, and the twin applies it the way the export call site does."""
    import precision_study

    assert precision_study.PINNED_SAMPLES is export_site._PINNED_PRECISION_SAMPLES
    with psycopg.connect(seeded_wave) as pg:
        exported = export_site._link_precision_for_export(pg, PUBLISHED)
    cli = precision_by_method(seeded_wave, pinned_samples=precision_study.PINNED_SAMPLES)
    for method, figures in exported["methods"].items():
        assert cli[method] == (figures["confirmed"], figures["sampled"]), method
    assert exported["methods"]["announcement+lexicon"]["sample_id"] == "2026-09-04"
    assert cli["announcement+lexicon"] == (1, 2)
    # The pin is what makes them agree: unpinned, the twin reads the newer run.
    assert precision_by_method(seeded_wave)["announcement+lexicon"] == (2, 2)


def test_report_prints_the_pinned_figure_and_tags_the_newer_run(
    seeded_wave, monkeypatch, capsys,
):
    """`report` under rubric=attribution prints the PUBLISHED figure for a
    pinned tier (its pinned run), and the newer run on its own line tagged
    NOT PUBLISHED — never the newer run as the tier's figure."""
    import precision_study

    monkeypatch.setattr(precision_study, "DSN", seeded_wave)
    precision_study.main(["report"])
    out = capsys.readouterr().out
    attribution = out.split("## rubric=attribution")[1].split("## rubric=")[0]
    lines = [ln for ln in attribution.splitlines() if "announcement+lexicon" in ln]
    published = [ln for ln in lines if "NOT PUBLISHED" not in ln]
    newer = [ln for ln in lines if "NOT PUBLISHED" in ln]
    assert len(published) == 1, lines
    assert "1/2" in published[0] and "2026-09-04" in published[0], published
    assert len(newer) == 1, lines
    assert "2/2" in newer[0] and "2026-09-12" in newer[0], newer


# ═══════════════════════════════════════════════════════════════════════════
# site_meta.link_adjudication — per-award hand-adjudication COVERAGE (#109)
# ═══════════════════════════════════════════════════════════════════════════
#
# The defect these pin (measured 2026-09-11, Task 6b): /methodology/ opened
# "As of September 2026, every published link was individually
# hand-adjudicated … every proposed program-level link was then challenged by
# two independent adversarial reviewers — a link is published as high only if
# neither could refute it." Of 12,595 links the crosswalk grades high or
# medium, 9,587 carry an award_pe_adjudications row at all; 8,474 of those
# adjudications say `darpa_unpinned`; and 60 rows in the whole table carry
# refuter_lenses_passed = 2 — 57 of them on a link the crosswalk grades high
# or medium. Every number on the page was derived and true; this sentence was
# neither.
#
# The block is a WHOLE-TABLE aggregate, so unlike `seeded` above its fixture
# cannot scope itself with an organization marker — it owns both tables for
# the duration of the test. tests/ files run one at a time and every other
# file that seeds budget_line_awards inserts its rows inside its own tests
# (test_precision_study.py, test_derive_ap_links_run_order.py), so the
# truncation cannot pull a row out from under a test that is still running.


@pytest.fixture()
def adjudicated(pg_dsn):
    """Three published links (2 adjudicated, 1 of those unpinned, 1 link on a
    method with no adjudication at all) plus one UNPUBLISHED link that carries
    an adjudication — it must count toward neither number."""
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from award_pe_adjudications")
        pg.execute("delete from budget_line_awards")
        rows = [
            ("LAB-1", "LAB0601101E", "account+subagency", "medium"),
            ("LAB-2", "LAB0601101E", "account+subagency", "medium"),
            ("LAB-3", "LAB0602303E", "fpds-ap", "medium"),
            ("LAB-4", "LAB0602303E", "account", "low"),  # not published
        ]
        for piid, pe_bli, method, conf in rows:
            pg.execute(
                "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
                " organization, award_piid, method, confidence)"
                " values (%s, 'R-1', 2026, 'lab-block-test', %s, %s, %s)",
                (pe_bli, piid, method, conf),
            )
        adjs = [
            # (piid, pe_bli, adjudicated_confidence, verdict, pair_reason, judged)
            ("LAB-1", "LAB0601101E", "medium", "darpa_unpinned", "unpinned-pool",
             "2026-09-01 12:00:00-04"),
            ("LAB-2", "LAB0601101E", "high", "pinned", "pinned-here",
             "2026-08-30 12:00:00-04"),
            ("LAB-4", "LAB0602303E", "medium", "darpa_unpinned", "unpinned-pool",
             "2026-09-30 12:00:00-04"),
        ]
        for piid, pe_bli, conf, verdict, reason, judged in adjs:
            pg.execute(
                "insert into award_pe_adjudications (award_piid, pe_bli,"
                " adjudicated_confidence, award_verdict, pair_reason, adjudicated_at)"
                " values (%s, %s, %s, %s, %s, %s::timestamptz)",
                (piid, pe_bli, conf, verdict, reason, judged),
            )
        pg.commit()
    yield pg_dsn
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from award_pe_adjudications")
        pg.execute("delete from budget_line_awards where organization = 'lab-block-test'")
        pg.commit()


def test_the_adjudication_block_counts_coverage_not_intent(adjudicated):
    """Every figure /methodology/ prints about hand adjudication, derived.

    `as_of` is the latest adjudication the block COUNTS (2026-09-01 here) —
    LAB-4's later 2026-09-30 row is on an unpublished link and must not date
    a claim about published ones. `measured_on` is a DIFFERENT fact: the
    export run's own date, passed in by the caller.
    """
    with psycopg.connect(adjudicated) as pg:
        block = _link_adjudication_block(pg, measured_on="2026-09-11")

    assert block == {
        "measured_on": "2026-09-11",
        "as_of": "2026-09-01",
        "published": 3,
        "adjudicated": 2,
        "unpinned": 1,
        "unpinned_tier": "medium",
        "by_method": {
            "account+subagency": {"published": 2, "adjudicated": 2},
            "fpds-ap": {"published": 1, "adjudicated": 0},
        },
        "unadjudicated_methods": ["fpds-ap"],
    }


def test_the_census_date_is_the_export_run_not_the_last_adjudication(adjudicated):
    """Fix round 1, C1. The counts are taken at export time; `as_of` dates the
    last adjudication. Welding the two made the rendered sentence false under
    its own date — on 2026-09-01 the live corpus held 9,864 published links,
    not the 12,595 the sentence counted. The two dates are now separate
    fields, and `measured_on` defaults to TODAY rather than to `as_of` when a
    caller does not supply the run's date."""
    with psycopg.connect(adjudicated) as pg:
        stamped = _link_adjudication_block(pg, measured_on="2026-12-25")
        defaulted = _link_adjudication_block(pg)

    assert stamped["measured_on"] == "2026-12-25"
    assert stamped["as_of"] == "2026-09-01"
    assert defaulted["measured_on"] == dt.datetime.now(dt.UTC).date().isoformat()
    assert defaulted["measured_on"] != defaulted["as_of"]


def test_the_block_publishes_no_list_nothing_reads(adjudicated):
    """M5. `adjudicated_methods` was produced, typed in data.ts and consumed
    by neither the page nor a gate leg. A field nothing reads is a field
    nothing checks."""
    with psycopg.connect(adjudicated) as pg:
        block = _link_adjudication_block(pg, measured_on="2026-09-11")

    assert "adjudicated_methods" not in block


def test_a_method_with_no_adjudication_is_named_rather_than_left_silent(adjudicated):
    """The half of #109 the old sentence erased: three evidence paths carry
    ZERO adjudication rows. A method absent from `by_method` would read as a
    method that passed."""
    with psycopg.connect(adjudicated) as pg:
        block = _link_adjudication_block(pg)

    assert set(block["by_method"]) == {"account+subagency", "fpds-ap"}
    assert block["adjudicated"] < block["published"]
    assert block["unadjudicated_methods"] == ["fpds-ap"]


def test_no_adjudications_yields_an_empty_block(adjudicated):
    """A fixture warehouse renders NOTHING for this sentence — never a stale
    claim about an adjudication that has not happened."""
    with psycopg.connect(adjudicated) as pg:
        pg.execute("delete from award_pe_adjudications")
        pg.commit()
        assert _link_adjudication_block(pg) == {}


def test_the_unpinned_tier_is_none_when_the_pool_does_not_publish_at_one_tier(adjudicated):
    """The page says "those links publish at medium" only while every unpinned
    published link carries that one grade — a mixed pool prints no tier rather
    than the majority's."""
    with psycopg.connect(adjudicated) as pg:
        pg.execute(
            "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
            " organization, award_piid, method, confidence)"
            " values ('LAB0601101E', 'R-1', 2026, 'lab-block-test', 'LAB-5',"
            " 'account+subagency', 'high')"
        )
        pg.execute(
            "insert into award_pe_adjudications (award_piid, pe_bli,"
            " adjudicated_confidence, award_verdict, pair_reason, adjudicated_at)"
            " values ('LAB-5', 'LAB0601101E', 'high', 'darpa_unpinned',"
            " 'unpinned-pool', '2026-09-01 12:00:00-04'::timestamptz)"
        )
        pg.commit()
        block = _link_adjudication_block(pg)

    assert block["unpinned"] == 2
    assert block["unpinned_tier"] is None


# ═══════════════════════════════════════════════════════════════════════════
# site_meta.link_adjudication.high — the High tier's own census (#109, fix
# round 1 R-6c-4)
# ═══════════════════════════════════════════════════════════════════════════
#
# THE DEFECT THESE PIN. Four surfaces graded the High tier "verified
# adversarially" / "verified by two independent adversarial reviewers"
# (methodology page.tsx ×2, docs/methodology.md, lib/coverage-map.ts — the
# last of which coverage.mjs's leg cm[bridge] MANDATED). Measured 2026-09-11
# over the MART: 768 links publish at high, 60 carry a per-award adjudication
# (all 60 at refuter_lenses_passed = 2), and 708 `announcement+lexicon` links
# carry none at all — a match basis is recorded on 384 of those 708.
#
# THE SECOND DEFECT, which these tests exist to make unrepeatable: the high
# tier CANNOT be re-derived from budget_line_awards. dbt demotes an
# unadjudicated `account+tokens` high row to medium (#75 addendum,
# 2026-09-04) and Postgres has no column for it, so
# `coalesce(adjudicated_confidence, confidence) = 'high'` counts 881 links
# where the site publishes 768. `high_links` is therefore an INPUT, read from
# the mart by _published_high_links; the block only asks Postgres what
# evidence those pairs carry.


@pytest.fixture()
def high_tier(adjudicated):
    """Adds the evidence rows the high census reads: LAB-2 is the adjudicated,
    two-lens high link; LAB-6 is an announcement link with a recorded match
    basis and LAB-7 an announcement link without one, neither adjudicated."""
    with psycopg.connect(adjudicated) as pg:
        pg.execute(
            "update award_pe_adjudications set refuter_lenses_passed = 2"
            " where award_piid = 'LAB-2'"
        )
        for piid, basis in (("LAB-6", "exact-name"), ("LAB-7", None)):
            pg.execute(
                "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
                " organization, award_piid, method, confidence)"
                " values ('LAB0602303E', 'R-1', 2026, 'lab-block-test', %s,"
                " 'announcement+lexicon', 'high')",
                (piid,),
            )
            pg.execute(
                "insert into award_link_sources (award_piid, pe_bli,"
                " source_kind, source_id, match_basis)"
                " values (%s, 'LAB0602303E', 'announcement', %s, %s)",
                (piid, f"src-{piid}", basis),
            )
        pg.commit()
    yield adjudicated
    with psycopg.connect(adjudicated) as pg:
        pg.execute("delete from award_link_sources")
        pg.commit()


#: What _published_high_links returns for the fixture: the MART's high tier.
#: LAB-1 is adjudicated MEDIUM and LAB-3 is an unadjudicated fpds-ap medium —
#: neither publishes at high, so neither appears.
FIXTURE_HIGH_LINKS = [
    ("LAB-2", "LAB0601101E", "account+subagency"),
    ("LAB-6", "LAB0602303E", "announcement+lexicon"),
    ("LAB-7", "LAB0602303E", "announcement+lexicon"),
]


def test_the_high_census_splits_adjudicated_evidence_from_the_rest(high_tier):
    """The sentence /methodology/ renders for the High tier, derived: how many
    of the links published at high carry a hand adjudication, how many of
    those survived both adversarial lenses, and what the rest carry instead."""
    with psycopg.connect(high_tier) as pg:
        block = _link_adjudication_block(
            pg, high_links=FIXTURE_HIGH_LINKS, measured_on="2026-09-11"
        )

    # `reviewed` / `reviewed_high` / `review_as_of` (ROADMAP #110, decided
    # 2026-09-25) are present because migration 018's announcement_link_reviews
    # exists and holds no row for these links: the announcement links carry
    # no RECORDED review, the adjudicated one does. `reviewed_by_kind`
    # (R-DEC-110, 2026-09-26) is present because the table carries
    # record_kind: the one reviewed link is the adjudicated one.
    assert block["high"] == {
        "published_high": 3,
        "adjudicated_high": 1,
        "two_lens_high": 1,
        "reviewed_high": 1,
        "review_as_of": None,
        "reviewed_by_kind": {"adjudication": 1, "verdict_pair": 0,
                             "survivor_list": 0},
        "by_path": {
            "account+subagency": {"high": 1, "adjudicated": 1, "two_lens": 1,
                                  "reviewed": 1,
                                  "reviewed_by_kind": {"adjudication": 1,
                                                       "verdict_pair": 0,
                                                       "survivor_list": 0}},
            "announcement+lexicon": {
                "high": 2,
                "adjudicated": 0,
                "two_lens": 0,
                "with_match_basis": 1,
                "reviewed": 0,
                "reviewed_by_kind": {"adjudication": 0, "verdict_pair": 0,
                                     "survivor_list": 0},
            },
        },
    }


def test_an_adjudication_without_two_lenses_is_not_counted_as_one(high_tier):
    """`two_lens` is the claim "two independent adversarial reviewers", and it
    is a STRICTLY smaller population than `adjudicated`: 10,031 of the 10,091
    rows in the live table leave refuter_lenses_passed NULL. A block that
    conflated them would let the page say "all 60 survived two reviewers" of a
    tier where one did not."""
    with psycopg.connect(high_tier) as pg:
        pg.execute(
            "update award_pe_adjudications set refuter_lenses_passed = null"
            " where award_piid = 'LAB-2'"
        )
        pg.commit()
        block = _link_adjudication_block(
            pg, high_links=FIXTURE_HIGH_LINKS, measured_on="2026-09-11"
        )

    assert block["high"]["adjudicated_high"] == 1
    assert block["high"]["two_lens_high"] == 0
    assert block["high"]["by_path"]["account+subagency"]["two_lens"] == 0


def test_a_path_that_records_no_sources_states_no_basis_figure(high_tier):
    """`with_match_basis` distinguishes "recorded, and it is none" from "this
    path records no source rows at all". The account family carries neither
    an announcement nor a basis, so the key is absent rather than 0."""
    with psycopg.connect(high_tier) as pg:
        block = _link_adjudication_block(
            pg, high_links=FIXTURE_HIGH_LINKS, measured_on="2026-09-11"
        )

    assert "with_match_basis" not in block["high"]["by_path"]["account+subagency"]
    assert block["high"]["by_path"]["announcement+lexicon"]["with_match_basis"] == 1

    with psycopg.connect(high_tier) as pg:
        pg.execute("update award_link_sources set match_basis = null")
        pg.commit()
        stripped = _link_adjudication_block(
            pg, high_links=FIXTURE_HIGH_LINKS, measured_on="2026-09-11"
        )
    assert stripped["high"]["by_path"]["announcement+lexicon"]["with_match_basis"] == 0


def test_no_mart_means_no_high_sentence_rather_than_a_wrong_universe(high_tier):
    """_published_high_links returns None on a warehouse with no mart. The
    block then omits `high` entirely and the page renders no High-tier census
    — never one counted against budget_line_awards, which does not know which
    links dbt demoted."""
    with psycopg.connect(high_tier) as pg:
        assert "high" not in _link_adjudication_block(pg, high_links=None)
        assert "high" not in _link_adjudication_block(pg, high_links=[])


# ═══════════════════════════════════════════════════════════════════════════
# _published_high_links — the MART query itself (#109, fix round 2 R-6c-7)
# ═══════════════════════════════════════════════════════════════════════════
#
# THE DEFECT THESE PIN. This function decides the UNIVERSE the High-tier
# census is measured over, and until 2026-09-11 nothing exercised its query
# or its fallback: `git grep _published_high_links` found it only in comments,
# and the block's own tests passed `high_links=None`/`[]` by hand. It also
# swallowed EVERY exception into the same `None` the missing-mart case
# returns — so a renamed column, a type change or a transient read failure at
# export time would have deleted the whole High-tier grading from a published
# /methodology/ with every gate green, which is the vacuity shape M4 closed
# one sub-block over. The catch is now narrowed to the missing relation and
# gate 24 leg o fails a block that grades links and exports no `high`.


def _mart_duckdb(tmp_path, rows, *, method_column="method") -> str:
    """A warehouse holding nothing but fct_budget_to_awards."""
    db = tmp_path / "govbudget.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "create table fct_budget_to_awards ("
        f" award_piid varchar, pe_bli varchar, {method_column} varchar,"
        "  confidence varchar)"
    )
    for row in rows:
        con.execute("insert into fct_budget_to_awards values (?, ?, ?, ?)", row)
    con.close()
    return str(db)


def test_published_high_links_reads_the_marts_high_tier_and_nothing_else(tmp_path):
    """The mart's `confidence` is the authority: an `account+tokens` row the
    crosswalk graded high but no one adjudicated arrives here already DEMOTED
    to medium (#75 addendum ruling 3), and must not appear. Re-deriving the
    tier in Postgres as coalesce(adjudicated_confidence, confidence) counts
    those 113 rows and reports 881 links where the site publishes 768."""
    db = _mart_duckdb(
        tmp_path,
        [
            ("HL-1", "HL0601101E", "account+subagency", "high"),
            ("HL-2", "HL0601101E", "account+tokens", "medium"),  # dbt demoted it
            ("HL-3", "HL0602303E", "announcement+lexicon", "high"),
            ("HL-3", "HL0602303E", "announcement+lexicon", "high"),  # distinct
            (None, "HL0602303E", "account", "high"),
            ("HL-4", None, "account", "high"),
            ("HL-5", "HL0602303E", None, "high"),
            ("HL-6", "HL0604256N", "fpds-ap", "low"),
        ],
    )

    assert sorted(_published_high_links(db)) == [
        ("HL-1", "HL0601101E", "account+subagency"),
        ("HL-3", "HL0602303E", "announcement+lexicon"),
    ]


def test_a_warehouse_with_no_mart_states_no_high_census_at_all(tmp_path):
    """`None`, not an empty list and not a guess — the caller then omits the
    `high` sub-block entirely (pinned by
    test_no_mart_means_no_high_sentence_rather_than_a_wrong_universe) rather
    than publishing a census measured against the wrong universe."""
    db = tmp_path / "govbudget.duckdb"
    duckdb.connect(str(db)).close()

    assert _published_high_links(db) is None


def test_a_broken_mart_raises_instead_of_deleting_the_high_census(tmp_path):
    """The narrowed catch. A mart whose `method` column was renamed is NOT a
    warehouse without a mart: the first silently publishes a /methodology/
    with no High-tier grading at all, which no number can disagree with. Only
    CatalogException (no such relation) may degrade to `None`."""
    db = _mart_duckdb(
        tmp_path,
        [("HL-1", "HL0601101E", "account+subagency", "high")],
        method_column="linking_method",
    )

    with pytest.raises(duckdb.BinderException):
        _published_high_links(db)
