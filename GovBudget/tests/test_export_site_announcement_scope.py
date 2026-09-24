"""site_meta.announcement_llm_scope — the scope of the announcement LLM-alias
pass, derived (ROADMAP findings log :118-119).

The defect this closes: /methodology/ stated "the 3,840 unmatched records that
carry about 88% of the residue by announced value; the 12,811 smaller records
carrying the remaining ~12% were not attempted" as four hand-typed literals.
They were true on 2026-09-02, they describe a residue definition whose code was
never committed, and nothing in the build could notice when they stopped being
true. Every figure in that sentence now comes from this block.

The same block carries the pass's own PRECISION pair (wave 4, 2026-09-12): the
tier-wide study (`_link_precision_block`) sampled the announcement tier on
2026-09-04, before this pass's newest links existed, so its figure says nothing
about them. A fresh two-lens sample of those links is loaded under its own
sample_id and tallied HERE, joined to the links the corpus actually publishes —
and the tier figure is pinned to the run it was drawn from so the newer,
narrower sample can never silently become "the announcement tier's precision".

Run against the fixture Postgres (root conftest's `pg_dsn`), so both the SQL
and the table's own CHECK constraints under test are the ones that run in
production.
"""
import psycopg
import pytest

from govbudget import export_site
from govbudget.export_site import _announcement_llm_scope, _link_precision_block

INSERT = (
    "insert into announcement_llm_scope (as_of, records_total,"
    " records_deterministic, records_residue, records_attempted,"
    " value_residue, value_attempted, note)"
    " values (%s,%s,%s,%s,%s,%s,%s,%s)"
)

INSERT_WITH_SAMPLE = (
    "insert into announcement_llm_scope (as_of, records_total,"
    " records_deterministic, records_residue, records_attempted,"
    " value_residue, value_attempted, note, precision_sample_id)"
    " values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
)


@pytest.fixture()
def clean(pg_dsn):
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from announcement_llm_scope")
        pg.commit()
    return pg_dsn


def test_empty_table_yields_an_empty_block(clean):
    with psycopg.connect(clean) as pg:
        assert _announcement_llm_scope(pg) == {}


def test_latest_row_wins_and_percentages_are_derived(clean):
    with psycopg.connect(clean) as pg:
        pg.execute(INSERT, ("2026-09-02", 32852, 4508, 28344, 3840,
                            3839300000000, 1954500000000, "wave 2 only"))
        pg.execute(INSERT, ("2026-09-12", 32852, 4508, 28344, 28344,
                            3839300000000, 3839300000000, "waves 2+4"))
        pg.commit()
    with psycopg.connect(clean) as pg:
        block = _announcement_llm_scope(pg)
    assert block["as_of"] == "2026-09-12"
    assert block["records_total"] == 32852
    assert block["records_deterministic"] == 4508
    assert block["records_residue"] == 28344
    assert block["records_attempted"] == 28344
    assert block["records_remaining"] == 0
    assert block["pct_value_attempted"] == 100.0
    assert block["pct_value_remaining"] == 0.0


def test_a_partial_pass_reports_the_smaller_true_number(clean):
    with psycopg.connect(clean) as pg:
        pg.execute(INSERT, ("2026-09-12", 32852, 4508, 28344, 14172,
                            4000, 3000, None))
        pg.commit()
    with psycopg.connect(clean) as pg:
        block = _announcement_llm_scope(pg)
    assert block["records_attempted"] == 14172
    assert block["records_remaining"] == 28344 - 14172
    assert block["pct_value_attempted"] == 75.0
    assert block["pct_value_remaining"] == 25.0


def test_the_table_refuses_a_pass_larger_than_the_residue(clean):
    """The write-time guard: a row claiming more records attempted than the
    residue holds is arithmetically impossible and never lands."""
    with psycopg.connect(clean) as pg:
        with pytest.raises(psycopg.errors.CheckViolation):
            pg.execute(INSERT, ("2026-09-12", 10, 2, 8, 9, 100, 50, None))


def test_the_exporter_refuses_the_same_row_without_the_constraint(clean):
    """The read-time guard, which is the one that protects a database restored
    from a dump taken before 016 or migrated without it. The named constraint
    is dropped for the length of this test so the bad row can actually reach
    the exporter — a real table, not a stubbed cursor."""
    with psycopg.connect(clean) as pg:
        pg.execute("alter table announcement_llm_scope"
                   " drop constraint attempted_within_residue")
        pg.commit()
    try:
        with psycopg.connect(clean) as pg:
            pg.execute(INSERT, ("2026-09-12", 10, 2, 8, 9, 100, 50, None))
            pg.commit()
        with psycopg.connect(clean) as pg:
            with pytest.raises(ValueError, match="records_attempted"):
                _announcement_llm_scope(pg)
    finally:
        with psycopg.connect(clean) as pg:
            pg.execute("delete from announcement_llm_scope")
            pg.execute("alter table announcement_llm_scope add constraint"
                       " attempted_within_residue"
                       " check (records_attempted <= records_residue)")
            pg.commit()


# ---------------------------------------------------------------------------
# The pass's own precision pair (R-25b-1)
# ---------------------------------------------------------------------------

#: One published announcement link per sampled pair, plus the counter-examples
#: the tally must drop. (piid, pe_bli, published method, published confidence)
_LINKS = [
    ("ALS-A1", "ALS0603286E", "announcement+lexicon", "high"),
    ("ALS-A2", "ALS0603286E", "announcement+lexicon", "high"),
    ("ALS-A3", "ALS0603286E", "announcement+lexicon", "high"),
    # demoted out of the published tiers — counts toward neither number
    ("ALS-A4", "ALS0603286E", "announcement+lexicon", "low"),
    # judged, published, but under another method — not this pass's link
    ("ALS-F1", "ALS0601101E", "fpds-ap", "medium"),
]

#: (sample_id, piid, pe_bli, rubric, verdict)
_VERDICTS = [
    ("ALS-2026-09-12", "ALS-A1", "ALS0603286E", "attribution", "confirmed"),
    ("ALS-2026-09-12", "ALS-A2", "ALS0603286E", "attribution", "refuted"),
    ("ALS-2026-09-12", "ALS-A3", "ALS0603286E", "attribution", "confirmed"),
    ("ALS-2026-09-12", "ALS-A4", "ALS0603286E", "attribution", "confirmed"),
    ("ALS-2026-09-12", "ALS-F1", "ALS0601101E", "attribution", "confirmed"),
    # a rows-only audit rubric never counts as precision (migration 015)
    ("ALS-2026-09-12", "ALS-G1", "ALS0604256N", "rule-fired", "confirmed"),
    # a DIFFERENT run must not pool in
    ("ALS-2026-09-04", "ALS-A1", "ALS0603286E", "attribution", "refuted"),
    ("ALS-2026-09-04", "ALS-A2", "ALS0603286E", "attribution", "refuted"),
]


@pytest.fixture()
def sampled(clean):
    """A miniature of the wave-4 precision sample: three published links from
    the newest pass judged under its own sample_id, one demoted link, one link
    that publishes under another method, one audit-rubric verdict — and an
    EARLIER run over the same tier, which is the run the tier-wide figure is
    pinned to."""
    marker = "ann-scope-test"
    runs = sorted({v[0] for v in _VERDICTS})
    with psycopg.connect(clean) as pg:
        pg.execute("delete from link_precision_samples where sample_id = any(%s)", (runs,))
        pg.execute("delete from budget_line_awards where organization = %s", (marker,))
        for piid, pe_bli, method, conf in _LINKS:
            pg.execute(
                "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
                " organization, award_piid, method, confidence)"
                " values (%s, 'R-1', 2026, %s, %s, %s, %s)",
                (pe_bli, marker, piid, method, conf),
            )
        for sid, piid, pe_bli, rubric, verdict in _VERDICTS:
            pg.execute(
                "insert into link_precision_samples (sample_id, award_piid, pe_bli,"
                " method, rubric, verdict, reason, adjudicated_at)"
                " values (%s,%s,%s,'announcement+lexicon',%s,%s,'fixture',"
                " '2026-09-19 04:10:00-04'::timestamptz)",
                (sid, piid, pe_bli, rubric, verdict),
            )
        pg.commit()
    yield clean
    with psycopg.connect(clean) as pg:
        pg.execute("delete from link_precision_samples where sample_id = any(%s)", (runs,))
        pg.execute("delete from budget_line_awards where organization = %s", (marker,))
        pg.execute("delete from announcement_llm_scope")
        pg.commit()


def _row(pg, precision_sample_id):
    pg.execute(INSERT_WITH_SAMPLE,
               ("2026-09-12", 32852, 4508, 28344, 15615,
                3839296125017, 3432690768287, "fixture", precision_sample_id))
    pg.commit()


def test_precision_is_null_when_the_row_names_no_sample(sampled):
    """A pass whose links have not been sampled publishes no precision pair —
    the page then says so in words rather than borrowing another sample's."""
    with psycopg.connect(sampled) as pg:
        _row(pg, None)
    with psycopg.connect(sampled) as pg:
        assert _announcement_llm_scope(pg)["precision"] is None


def test_precision_is_null_when_the_named_sample_has_no_published_rows(sampled):
    with psycopg.connect(sampled) as pg:
        _row(pg, "ALS-no-such-run")
    with psycopg.connect(sampled) as pg:
        assert _announcement_llm_scope(pg)["precision"] is None


def test_precision_counts_only_published_announcement_links_of_that_run(sampled):
    """Three sampled links publish as announcement+lexicon (2 confirmed, 1
    refuted). The demoted link, the fpds-ap link, the audit-rubric verdict and
    the earlier run are all excluded — the same population rule the tier-wide
    block uses, applied to this pass's own sample."""
    with psycopg.connect(sampled) as pg:
        _row(pg, "ALS-2026-09-12")
    with psycopg.connect(sampled) as pg:
        precision = _announcement_llm_scope(pg)["precision"]
    assert precision == {
        "sample_id": "ALS-2026-09-12",
        "sampled_at": "2026-09-19",
        "drawn": 5,
        "sampled": 3,
        "confirmed": 2,
    }


def test_the_tier_figure_stays_pinned_to_the_run_it_was_drawn_from(sampled):
    """R-25b-1. Unpinned, `_link_precision_block` takes each method's LATEST
    run — which after a wave sample loads is the wave's own narrow sample, and
    the announcement tier would silently start publishing a figure measured on
    one wave's links. Pinned, the tier keeps the run it was drawn from."""
    published = {"announcement+lexicon", "fpds-ap"}
    with psycopg.connect(sampled) as pg:
        latest = _link_precision_block(pg, published_methods=published)
        pinned = _link_precision_block(
            pg, published_methods=published,
            pinned_samples={"announcement+lexicon": "ALS-2026-09-04"},
        )
    assert latest["methods"]["announcement+lexicon"]["sample_id"] == "ALS-2026-09-12"
    assert (latest["methods"]["announcement+lexicon"]["confirmed"],
            latest["methods"]["announcement+lexicon"]["sampled"]) == (2, 3)
    assert pinned["methods"]["announcement+lexicon"]["sample_id"] == "ALS-2026-09-04"
    assert (pinned["methods"]["announcement+lexicon"]["confirmed"],
            pinned["methods"]["announcement+lexicon"]["sampled"]) == (0, 2)
    # the pin moves ONE method; every other tier keeps its own latest run
    assert pinned["methods"]["fpds-ap"] == latest["methods"]["fpds-ap"]


def test_a_pinned_method_with_no_verdicts_in_that_run_is_unmeasured(sampled):
    """The pin never falls back to a run it was not given: a tier whose pinned
    sample judged nothing it still publishes is reported UNMEASURED, which
    /methodology/ states in prose, rather than quietly reverting to the latest
    sample."""
    published = {"announcement+lexicon", "fpds-ap"}
    with psycopg.connect(sampled) as pg:
        block = _link_precision_block(
            pg, published_methods=published,
            pinned_samples={"announcement+lexicon": "ALS-no-such-run"},
        )
    assert "announcement+lexicon" not in block["methods"]
    assert "announcement+lexicon" in block["unmeasured"]


def test_the_announcement_tier_is_pinned_at_the_export_call_site():
    """The pin is policy, not a default: it lives in one named constant the
    exporter passes, so removing it is a visible edit and this test fails."""
    assert export_site._PINNED_PRECISION_SAMPLES["announcement+lexicon"] == "2026-09-04"


# ---------------------------------------------------------------------------
# Fix round 1: the draw size, the frame the tier draw could not cover, and the
# pin bound at the CALL SITE rather than at the constant
# ---------------------------------------------------------------------------


def test_precision_states_the_draw_it_came_from_not_only_what_publishes(sampled):
    """The published pair counts judged links the corpus STILL publishes, so
    the denominator is smaller than the draw. `drawn` is the draw: five
    attribution verdicts were judged under this run, three of them on links
    that publish today. Without it the page can say "48 of the 55" and never
    show the reader the five links that left."""
    with psycopg.connect(sampled) as pg:
        _row(pg, "ALS-2026-09-12")
    with psycopg.connect(sampled) as pg:
        precision = _announcement_llm_scope(pg)["precision"]
    assert (precision["drawn"], precision["sampled"], precision["confirmed"]) == (5, 3, 2)


def test_the_audit_rubric_verdict_is_not_part_of_the_draw(sampled):
    """`drawn` counts the run's ATTRIBUTION verdicts — the question the
    published pair answers. The fixture's one `rule-fired` row answers another
    one and is in neither number."""
    with psycopg.connect(sampled) as pg:
        _row(pg, "ALS-2026-09-12")
        n = pg.execute(
            "select count(*) from link_precision_samples where sample_id = %s",
            ("ALS-2026-09-12",)).fetchone()[0]
    assert n == 6                       # 5 attribution + 1 rule-fired
    with psycopg.connect(sampled) as pg:
        assert _announcement_llm_scope(pg)["precision"]["drawn"] == 5


def test_links_new_this_pass_is_published_when_the_row_carries_it(clean):
    """The tier-wide precision draw (2026-09-04) predates the links this pass
    added to the tier; the page states how many, so a reader can see the frame.
    NULL on a row written before migration 017, and the page then says
    nothing."""
    with psycopg.connect(clean) as pg:
        pg.execute(INSERT, ("2026-09-11", 32852, 4508, 28344, 3840,
                            3839300000000, 1954500000000, "before 017"))
        pg.commit()
    with psycopg.connect(clean) as pg:
        assert _announcement_llm_scope(pg)["links_new_this_pass"] is None
    with psycopg.connect(clean) as pg:
        pg.execute(INSERT + " ", ("2026-09-12", 32852, 4508, 28344, 15604,
                                  3839296125017, 3422307000911, "with 017"))
        pg.execute("update announcement_llm_scope set links_new_this_pass = 367"
                   " where as_of = '2026-09-12'")
        pg.commit()
    with psycopg.connect(clean) as pg:
        assert _announcement_llm_scope(pg)["links_new_this_pass"] == 367


class _RecordingPg:
    """A `pg` that answers nothing and remembers every query's parameters —
    enough to prove which RUN the exporter asked the precision tally for."""

    def __init__(self):
        self.params = []

    def execute(self, sql, params=None):
        self.params.append(params)
        return self

    def fetchall(self):
        return []

    def fetchone(self):
        return None


def test_the_export_call_site_asks_for_the_pinned_run(clean):
    """R-25b-1, bound where it can break. The pin is not a default inside
    `_link_precision_block`: the EXPORT CALL SITE passes it, and deleting that
    kwarg would silently republish the announcement tier's figure from the
    wave-4 sample — a narrower population under the tier's name. The test used
    to assert the constant's value, which that edit leaves untouched. This one
    runs the function the exporter calls and watches the run it asks Postgres
    for."""
    recorder = _RecordingPg()
    export_site._link_precision_for_export(
        recorder, published_methods={"announcement+lexicon"})
    asked = [p.get("sample_id") for p in recorder.params if isinstance(p, dict)]
    assert export_site._PINNED_PRECISION_SAMPLES["announcement+lexicon"] in asked, (
        "the exporter never asked for the pinned run — "
        f"runs asked for: {asked}")
