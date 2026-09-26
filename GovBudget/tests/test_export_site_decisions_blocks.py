"""site_meta blocks the 2026-09-25 rulings move (decisions wave, export lane).

#107(b) — the `account+subagency` tier stops publishing (dbt demotes it to an
unpublished audit tier with a `demotion_reason`; Postgres keeps every row).
Its measured 0/58 must not vanish with it: `site_meta.link_precision` keeps
publishing figures ONLY for tiers the corpus publishes (`methods`, and
`unmeasured` for a published tier with no figure — gate 24 leg n), and gains
a separately labelled `withdrawn` sub-block that tallies the same verdicts
over the links the mart DEMOTED out of publication. The figure is the reason
the tier stopped publishing; dropping it would leave the demotion unexplained.

#107(b), second consequence — `link_adjudication.unpinned_tier` used to be
read from Postgres's `adjudicated_confidence` and rendered as "those links
publish at medium". After the demotion 8,389 of the 8,475 unpinned links
publish at nothing, so the tier now comes from the MART, and is stated only
while every unpinned link publishes at it.

#110 — high `announcement+lexicon` links publish at high only with a recorded
review (dbt lane; the review rows are migration 018's
`announcement_link_reviews`, exported as dbt source
`jbook_announcement_link_reviews`). `link_adjudication.high` now says how many
links published at high carry a RECORDED review of either kind, per path, so
/methodology/ can state a coverage figure instead of "60 of the 768 …".

Run against the fixture Postgres (root conftest's `pg_dsn`).
"""
from __future__ import annotations

import itertools

import duckdb
import psycopg
import pytest

from govbudget.export_site import (
    _link_adjudication_block,
    _link_precision_block,
    _published_demotions,
    _published_pair_tiers,
    _withdrawn_link_rows,
)

MARKER = "decisions-block-test"


def _mart(tmp_path, rows, *, with_reason=True) -> str:
    """A warehouse holding only fct_budget_to_awards (award_piid, pe_bli,
    method, confidence[, demotion_reason])."""
    db = tmp_path / "govbudget.duckdb"
    con = duckdb.connect(str(db))
    extra = ", demotion_reason varchar" if with_reason else ""
    con.execute(
        "create table fct_budget_to_awards (award_piid varchar, pe_bli varchar,"
        f" method varchar, confidence varchar{extra})"
    )
    for row in rows:
        ph = ", ".join("?" for _ in row)
        con.execute(f"insert into fct_budget_to_awards values ({ph})", row)
    con.close()
    return str(db)


# ═══════════════════════════════════════════════════════════════════════════
# The mart readers
# ═══════════════════════════════════════════════════════════════════════════


def test_withdrawn_links_are_the_rows_dbt_demoted_out_of_publication(tmp_path):
    db = _mart(tmp_path, [
        # demoted out of the published tiers (#107(b))
        ("W-1", "W0601101E", "account+subagency", "unpublished", "107b-audit-tier"),
        ("W-2", "W0601101E", "account+subagency", "unpublished", "107b-audit-tier"),
        # pinned-here pairs the demotion KEEPS publishing
        ("W-3", "W0601101E", "account+subagency", "high", None),
        # demoted high -> medium (#110): still published, NOT withdrawn
        ("W-4", "W0602303E", "announcement+lexicon", "medium", "110-no-recorded-review"),
        # a low row nobody demoted: never published, never withdrawn
        ("W-5", "W0602303E", "account", "low", None),
        # a demoted row whose pair still publishes on another row
        ("W-3", "W0601101E", "account+subagency", "unpublished", "107b-audit-tier"),
    ])
    rows = _withdrawn_link_rows(db)
    assert rows == [
        {"award_piid": "W-1", "pe_bli": "W0601101E", "method": "account+subagency",
         "demotion_reason": "107b-audit-tier"},
        {"award_piid": "W-2", "pe_bli": "W0601101E", "method": "account+subagency",
         "demotion_reason": "107b-audit-tier"},
    ]


def test_withdrawn_links_are_read_from_audit_link_grading_when_it_exists(tmp_path):
    """The dbt lane's shape (2026-09-25): fct_budget_to_awards publishes only
    high/medium, and the rows graded out of publication live in
    audit_link_grading with demotion_reason 'account_subagency_not_pinned'."""
    db = tmp_path / "govbudget.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "create table fct_budget_to_awards (award_piid varchar, pe_bli varchar,"
        " method varchar, confidence varchar, demotion_reason varchar)")
    con.execute("insert into fct_budget_to_awards values"
                " ('G-3', 'G0601101E', 'account+subagency', 'high', null),"
                " ('G-4', 'G0602303E', 'announcement+lexicon', 'medium',"
                "  'announcement_review_unrecorded')")
    con.execute(
        "create table audit_link_grading (award_piid varchar, pe_bli varchar,"
        " exhibit varchar, fiscal_year integer, method varchar,"
        " confidence varchar, demotion_reason varchar)")
    con.execute("insert into audit_link_grading values"
                " ('G-1', 'G0601101E', 'R-1', 2026, 'account+subagency', 'low',"
                "  'account_subagency_not_pinned'),"
                " ('G-3', 'G0601101E', 'R-1', 2026, 'account+subagency', 'high', null),"
                " ('G-3', 'G0601101E', 'R-1', 2025, 'account+subagency', 'low',"
                "  'account_subagency_not_pinned'),"
                " ('G-4', 'G0602303E', 'R-1', 2026, 'announcement+lexicon',"
                "  'medium', 'announcement_review_unrecorded'),"
                " ('G-5', 'G0602303E', 'R-1', 2026, 'account', 'reject', null)")
    con.close()
    assert _withdrawn_link_rows(db) == [
        {"award_piid": "G-1", "pe_bli": "G0601101E", "method": "account+subagency",
         "demotion_reason": "account_subagency_not_pinned"},
    ]


def test_a_mart_without_demotion_reason_has_no_withdrawn_population(tmp_path):
    """A warehouse built before #107(b) is an expected state, not an error."""
    db = _mart(tmp_path, [("W-1", "W0601101E", "account+subagency", "medium")],
               with_reason=False)
    assert _withdrawn_link_rows(db) is None
    empty = tmp_path / "empty.duckdb"
    duckdb.connect(str(empty)).close()
    assert _withdrawn_link_rows(empty) is None


def test_published_pair_tiers_reads_the_tier_a_reader_meets(tmp_path):
    db = _mart(tmp_path, [
        ("P-1", "P0601101E", "account+subagency", "medium", None),
        ("P-1", "P0601101E", "account+subagency", "high", None),
        ("P-2", "P0601101E", "account+subagency", "unpublished", "107b"),
        ("P-3", "P0602303E", "fpds-ap", "low", None),
    ])
    assert _published_pair_tiers(db) == {("P-1", "P0601101E"): {"high", "medium"}}
    empty = tmp_path / "empty.duckdb"
    duckdb.connect(str(empty)).close()
    assert _published_pair_tiers(empty) is None


# ═══════════════════════════════════════════════════════════════════════════
# link_precision.withdrawn (#107(b))
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def precision_seeded(pg_dsn):
    runs = ("2026-09-04", "2026-09-05")
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from link_precision_samples where sample_id = any(%s)"
                   " and reason = %s", (list(runs), MARKER))
        samples = [
            # (sample_id, piid, pe_bli, method AT DRAW, verdict)
            ("2026-09-05", "D-G1", "D0601101E", "account+subagency", "refuted"),
            ("2026-09-05", "D-G2", "D0601101E", "account+subagency", "refuted"),
            ("2026-09-05", "D-G3", "D0601101E", "account+subagency", "refuted"),
            ("2026-09-04", "D-A1", "D0603286E", "announcement+lexicon", "confirmed"),
            ("2026-09-04", "D-A2", "D0603286E", "announcement+lexicon", "refuted"),
        ]
        for sid, piid, pe_bli, method, verdict in samples:
            pg.execute(
                "insert into link_precision_samples (sample_id, award_piid, pe_bli,"
                " method, rubric, verdict, reason, adjudicated_at)"
                " values (%s, %s, %s, %s, 'attribution', %s, %s,"
                " '2026-09-11 12:00:00-04'::timestamptz)",
                (sid, piid, pe_bli, method, verdict, MARKER),
            )
        pg.commit()
    yield pg_dsn
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from link_precision_samples where reason = %s", (MARKER,))
        pg.commit()


#: The mart after #107(b): D-G1/D-G2 demoted out, D-G4 (never sampled) still
#: published as a pinned-here high link, the announcement links published.
PUBLISHED_AFTER = [
    {"award_piid": "D-A1", "pe_bli": "D0603286E", "method": "announcement+lexicon"},
    {"award_piid": "D-A2", "pe_bli": "D0603286E", "method": "announcement+lexicon"},
    {"award_piid": "D-G4", "pe_bli": "D0601101E", "method": "account+subagency"},
]
WITHDRAWN_AFTER = [
    {"award_piid": "D-G1", "pe_bli": "D0601101E", "method": "account+subagency",
     "demotion_reason": "107b-audit-tier"},
    {"award_piid": "D-G2", "pe_bli": "D0601101E", "method": "account+subagency",
     "demotion_reason": "107b-audit-tier"},
]


def test_a_demoted_tier_keeps_its_measured_figure_under_withdrawn(precision_seeded):
    """The 0/N that caused the demotion stays in site_meta — labelled as a tier
    that no longer publishes, never inside `methods` (gate 24 leg n: a
    withdrawn tier keeps its verdicts, never a published figure)."""
    with psycopg.connect(precision_seeded) as pg:
        block = _link_precision_block(
            pg,
            published_methods={"announcement+lexicon", "account+subagency"},
            published_links=PUBLISHED_AFTER,
            withdrawn_links=WITHDRAWN_AFTER,
        )
    assert "account+subagency" not in block["methods"], (
        "none of its sampled links publishes, so it has no published figure")
    assert block["unmeasured"] == ["account+subagency"], (
        "it still publishes (the pinned-here links), unmeasured")
    assert block["withdrawn"] == {
        "account+subagency": {
            "confirmed": 0,
            "sampled": 2,          # D-G3 is in neither population: it counts nowhere
            "sample_id": "2026-09-05",
            "judged": "2026-09-11",
            "links": 2,
            "demotion_reasons": ["107b-audit-tier"],
        },
    }
    assert block["methods"]["announcement+lexicon"]["sampled"] == 2
    # The paragraph's dates stay the published figures' own.
    assert block["sample_id"] == "2026-09-04"


def test_no_withdrawn_population_means_no_withdrawn_key(precision_seeded):
    with psycopg.connect(precision_seeded) as pg:
        before = _link_precision_block(
            pg, published_methods={"announcement+lexicon", "account+subagency"},
            published_links=PUBLISHED_AFTER)
        also = _link_precision_block(
            pg, published_methods={"announcement+lexicon", "account+subagency"},
            published_links=PUBLISHED_AFTER, withdrawn_links=[])
    assert "withdrawn" not in before
    assert "withdrawn" not in also


def test_the_withdrawn_tally_honours_the_pin(precision_seeded):
    """A pinned tier's withdrawn figure comes from its pinned run, or none."""
    withdrawn = [{"award_piid": "D-A2", "pe_bli": "D0603286E",
                  "method": "announcement+lexicon", "demotion_reason": "x"}]
    published = [PUBLISHED_AFTER[0], PUBLISHED_AFTER[2]]
    methods = {"announcement+lexicon", "account+subagency"}
    with psycopg.connect(precision_seeded) as pg:
        unpinned = _link_precision_block(
            pg, published_methods=methods, published_links=published,
            withdrawn_links=withdrawn)
        pinned_elsewhere = _link_precision_block(
            pg, published_methods=methods, published_links=published,
            withdrawn_links=withdrawn,
            pinned_samples={"announcement+lexicon": "2026-09-05"})
    got = unpinned["withdrawn"]["announcement+lexicon"]
    assert (got["confirmed"], got["sampled"], got["sample_id"]) == (0, 1, "2026-09-04")
    # The pinned run judged no announcement link: no figure under any key.
    assert "announcement+lexicon" not in pinned_elsewhere.get("withdrawn", {})
    assert "announcement+lexicon" not in pinned_elsewhere.get("methods", {})


# ═══════════════════════════════════════════════════════════════════════════
# link_adjudication: unpinned tier from the MART (#107(b)); review coverage of
# the High tier (#110)
# ═══════════════════════════════════════════════════════════════════════════

#: A stand-in for migration 018's table, used only if the fixture Postgres
#: somehow lacks it (the root conftest migrates from migrations/*.sql, so the
#: migration's own table — with its CHECKs — is the one these tests write).
_REVIEW_DDL = """
create table if not exists announcement_link_reviews (
    award_piid text not null, pe_bli text not null, exhibit text not null,
    fiscal_year integer not null, record_kind text not null,
    reviewer_verdict text not null, adversarial_verdict text not null,
    adversarial_lenses_passed integer, upholds boolean not null,
    article_id text, article_source text, record_index integer,
    entry_index integer not null, cites_reviewed_article boolean, reason text,
    reviewed_at date, source_file text not null,
    recorded_at timestamptz not null default now())
"""

_ENTRY = itertools.count()


def _review(pg, piid, pe, *, kind, adv="upheld", reviewer="link", idx=0,
            lenses=2, article="art-1", source="wave4_verdicts/x.json"):
    """One review record shaped as migration 018 (R-DEC-110) requires: a
    wave-4 verdict pair names its article and paragraph and, when its lenses
    ran, their count; a wave 1-3 list entry names neither and keeps a
    reason."""
    pair = kind == "verdict_pair"
    pg.execute(
        "insert into announcement_link_reviews (award_piid, pe_bli, exhibit,"
        " fiscal_year, record_kind, reviewer_verdict, adversarial_verdict,"
        " adversarial_lenses_passed, upholds, article_id, article_source,"
        " record_index, entry_index, cites_reviewed_article, reason,"
        " reviewed_at, source_file)"
        " values (%s, %s, 'R-1', 2026, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
        " %s, %s, null, %s)",
        (piid, pe, kind, reviewer, adv,
         lenses if pair and adv != "not_run" else None,
         reviewer == "link" and adv == "upheld",
         article if pair else None, "verdict_file" if pair else None,
         idx if pair else None, next(_ENTRY), True if pair else None,
         None if pair else "survived the refuter", source))


@pytest.fixture()
def reviewed(pg_dsn):
    """Six links the crosswalk grades high/medium:
      R-1  account+subagency  adjudicated darpa_unpinned  (the mart demotes it)
      R-2  account+subagency  adjudicated darpa_unpinned  (the mart publishes it medium)
      R-3  account+subagency  adjudicated pinned, two lenses (published high)
      R-4  announcement+lexicon  one recorded review, upheld   (published high)
      R-5  announcement+lexicon  two review rows, one refuted, one upheld (high)
      R-6  announcement+lexicon  no recorded review         (dbt: medium)
    """
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from award_pe_adjudications")
        pg.execute("delete from award_link_sources")
        pg.execute("delete from budget_line_awards")
        pg.execute(_REVIEW_DDL)
        pg.execute("delete from announcement_link_reviews")
        for piid, pe, method, conf in (
            ("R-1", "R0601101E", "account+subagency", "medium"),
            ("R-2", "R0601101E", "account+subagency", "medium"),
            ("R-3", "R0601101E", "account+subagency", "medium"),
            ("R-4", "R0602303E", "announcement+lexicon", "high"),
            ("R-5", "R0602303E", "announcement+lexicon", "high"),
            ("R-6", "R0602303E", "announcement+lexicon", "high"),
        ):
            pg.execute(
                "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
                " organization, award_piid, method, confidence)"
                " values (%s, 'R-1', 2026, %s, %s, %s, %s)",
                (pe, MARKER, piid, method, conf))
        for piid, conf, verdict, reason, lenses in (
            ("R-1", "medium", "darpa_unpinned", "unpinned-pool", None),
            ("R-2", "medium", "darpa_unpinned", "unpinned-pool", None),
            ("R-3", "high", "pinned", "pinned-here", 2),
        ):
            pg.execute(
                "insert into award_pe_adjudications (award_piid, pe_bli,"
                " adjudicated_confidence, award_verdict, pair_reason,"
                " refuter_lenses_passed, adjudicated_at)"
                " values (%s, 'R0601101E', %s, %s, %s, %s,"
                " '2026-09-01 12:00:00-04'::timestamptz)",
                (piid, conf, verdict, reason, lenses))
        for piid, adv, lenses, idx in (
            ("R-4", "upheld", 2, 0),
            ("R-5", "refuted", 1, 0),
            ("R-5", "upheld", 2, 1),
        ):
            _review(pg, piid, "R0602303E", kind="verdict_pair", adv=adv,
                    lenses=lenses, idx=idx)
        pg.commit()
    yield pg_dsn
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from announcement_link_reviews")
        pg.execute("delete from award_pe_adjudications")
        pg.execute("delete from budget_line_awards where organization = %s", (MARKER,))
        pg.commit()


#: The mart after both rulings: R-1 demoted out, R-6 demoted high -> medium.
TIERS_AFTER = {
    ("R-2", "R0601101E"): {"medium"},
    ("R-3", "R0601101E"): {"high"},
    ("R-4", "R0602303E"): {"high"},
    ("R-5", "R0602303E"): {"high"},
    ("R-6", "R0602303E"): {"medium"},
}
HIGH_AFTER = [
    ("R-3", "R0601101E", "account+subagency"),
    ("R-4", "R0602303E", "announcement+lexicon"),
    ("R-5", "R0602303E", "announcement+lexicon"),
]


def test_the_unpinned_tier_comes_from_the_mart_not_postgres(reviewed):
    """Postgres says both unpinned links carry adjudicated_confidence medium;
    the mart publishes only one of them. "those links publish at medium" would
    be false of R-1, so the tier is withheld and the split is published."""
    with psycopg.connect(reviewed) as pg:
        block = _link_adjudication_block(
            pg, high_links=HIGH_AFTER, measured_on="2026-09-25",
            published_tiers=TIERS_AFTER)
    assert block["unpinned"] == 2
    assert block["unpinned_published"] == 1
    assert block["unpinned_published_tier"] == "medium"
    assert block["unpinned_tier"] is None, (
        "a tier is stated for 'those links' only while all of them publish at it")


def test_the_unpinned_tier_is_stated_when_every_unpinned_link_publishes_at_it(reviewed):
    tiers = dict(TIERS_AFTER)
    tiers[("R-1", "R0601101E")] = {"medium"}
    with psycopg.connect(reviewed) as pg:
        block = _link_adjudication_block(
            pg, high_links=HIGH_AFTER, measured_on="2026-09-25",
            published_tiers=tiers)
    assert block["unpinned_published"] == 2
    assert block["unpinned_tier"] == "medium"


def test_without_the_mart_the_block_keeps_its_old_shape(reviewed):
    """Fixture callers that pass no mart tiers get the pre-2026-09-25 block."""
    with psycopg.connect(reviewed) as pg:
        block = _link_adjudication_block(pg, measured_on="2026-09-25")
    assert block["unpinned_tier"] == "medium"
    assert "unpinned_published" not in block


def test_the_high_census_counts_recorded_reviews_of_either_kind(reviewed):
    with psycopg.connect(reviewed) as pg:
        block = _link_adjudication_block(
            pg, high_links=HIGH_AFTER, measured_on="2026-09-25",
            published_tiers=TIERS_AFTER)
    high = block["high"]
    # The existing census is unchanged in meaning.
    assert high["published_high"] == 3
    assert high["adjudicated_high"] == 1
    assert high["two_lens_high"] == 1
    # New: every link published at high, and what recorded review it carries.
    assert high["reviewed_high"] == 3
    assert high["by_path"]["account+subagency"]["reviewed"] == 1
    assert high["by_path"]["announcement+lexicon"] == {
        "high": 2, "adjudicated": 0, "two_lens": 0,
        "reviewed": 2,                  # adjudication OR announcement review
        "announcement_reviewed": 2,     # has >= 1 recorded review row
        "announcement_upheld": 2,       # >= 1 row: reviewer 'link' + adversarial 'upheld'
        "reviewed_by_kind": {"adjudication": 0, "verdict_pair": 2,
                             "survivor_list": 0},
    }
    assert high["review_as_of"] is None, "wave-4 rows carry no review date"


def test_an_unreviewed_high_link_is_counted_as_unreviewed(reviewed):
    """If the mart ever published an announcement link at high with no review
    row (the dbt rule regressed), the census says so rather than assuming it."""
    high = HIGH_AFTER + [("R-6", "R0602303E", "announcement+lexicon")]
    with psycopg.connect(reviewed) as pg:
        block = _link_adjudication_block(pg, high_links=high,
                                         measured_on="2026-09-25")
    assert block["high"]["published_high"] == 4
    assert block["high"]["reviewed_high"] == 3
    assert block["high"]["by_path"]["announcement+lexicon"]["announcement_reviewed"] == 2


def test_a_postgres_without_the_review_table_publishes_the_old_census(pg_dsn):
    """Before migration 018 the review keys are absent, not zero: "no table"
    is not "no review"."""
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("delete from award_pe_adjudications")
        pg.execute("delete from budget_line_awards")
        pg.execute(
            "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
            " organization, award_piid, method, confidence)"
            " values ('N0601101E', 'R-1', 2026, %s, 'N-1', 'account', 'high')",
            (MARKER,))
        pg.execute(
            "insert into award_pe_adjudications (award_piid, pe_bli,"
            " adjudicated_confidence, award_verdict, pair_reason,"
            " refuter_lenses_passed, adjudicated_at) values ('N-1', 'N0601101E',"
            " 'high', 'pinned', 'pinned-here', 2, now())")
        pg.execute(_REVIEW_DDL)
        pg.execute("savepoint s")
        pg.execute("alter table announcement_link_reviews rename to _alr_hidden")
        try:
            block = _link_adjudication_block(
                pg, high_links=[("N-1", "N0601101E", "account")],
                measured_on="2026-09-25")
        finally:
            pg.execute("rollback to savepoint s")
        pg.rollback()
    assert "reviewed_high" not in block["high"]
    assert "reviewed" not in block["high"]["by_path"]["account"]


# ═══════════════════════════════════════════════════════════════════════════
# R-DEC-110 (controller, 2026-09-26): the high census splits recorded review
# by record_kind, and says how many high links were demoted, and why
# ═══════════════════════════════════════════════════════════════════════════


def _add_announcement_links(pg, *piids):
    for piid in piids:
        pg.execute(
            "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
            " organization, award_piid, method, confidence)"
            " values ('R0602303E', 'R-1', 2026, %s, %s,"
            " 'announcement+lexicon', 'high')", (MARKER, piid))


def test_reviewed_high_is_split_by_the_kind_of_record_that_upholds_it(reviewed):
    """Each high link counts ONCE, under its strongest recorded review: a
    two-lens adjudication, else a wave-4 verdict pair (the reviewer's verdict
    AND both adversarial lenses on that proposal), else a wave 1-3 survivor
    list entry (the reviewer's 'link' and survival of the refuter, recorded
    per pair). The split sums to reviewed_high, so /methodology/ can state it
    (R-DEC-110: "the granularity is disclosed, not hidden")."""
    with psycopg.connect(reviewed) as pg:
        _add_announcement_links(pg, "R-7", "R-8")
        # R-7: upheld by a survivor list alone
        _review(pg, "R-7", "R0602303E", kind="survivor_list",
                source="wave1_result.json")
        # R-8: a survivor list AND a wave-4 verdict pair -> verdict_pair
        _review(pg, "R-8", "R0602303E", kind="survivor_list",
                source="wave2_result.json")
        _review(pg, "R-8", "R0602303E", kind="verdict_pair", idx=3)
        pg.commit()
        high_links = HIGH_AFTER + [("R-7", "R0602303E", "announcement+lexicon"),
                                   ("R-8", "R0602303E", "announcement+lexicon")]
        block = _link_adjudication_block(
            pg, high_links=high_links, measured_on="2026-09-26")
    high = block["high"]
    assert high["published_high"] == 5
    assert high["reviewed_high"] == 5
    assert high["reviewed_by_kind"] == {
        "adjudication": 1, "verdict_pair": 3, "survivor_list": 1}
    assert sum(high["reviewed_by_kind"].values()) == high["reviewed_high"]
    ann = high["by_path"]["announcement+lexicon"]
    assert ann["reviewed_by_kind"] == {
        "adjudication": 0, "verdict_pair": 3, "survivor_list": 1}
    assert high["by_path"]["account+subagency"]["reviewed_by_kind"] == {
        "adjudication": 1, "verdict_pair": 0, "survivor_list": 0}


def test_a_high_link_whose_records_do_not_uphold_it_is_its_own_bucket(reviewed):
    """If the mart ever published at high a link whose only records reject
    it (the dbt rule regressed), the split says so under `not_upheld`
    instead of filing it under a kind that did not uphold it."""
    with psycopg.connect(reviewed) as pg:
        _add_announcement_links(pg, "R-9")
        _review(pg, "R-9", "R0602303E", kind="verdict_pair", reviewer="weak",
                adv="not_run")
        pg.commit()
        block = _link_adjudication_block(
            pg, high_links=HIGH_AFTER + [("R-9", "R0602303E", "announcement+lexicon")],
            measured_on="2026-09-26")
    by_kind = block["high"]["reviewed_by_kind"]
    assert by_kind["not_upheld"] == 1
    assert sum(by_kind.values()) == block["high"]["reviewed_high"] == 4


def test_no_record_kind_column_means_no_kind_split(reviewed):
    """Before the R-DEC-110 migration the table has no record_kind: the split
    is ABSENT, not guessed from the file names."""
    with psycopg.connect(reviewed) as pg:
        pg.execute("savepoint s")
        pg.execute("alter table announcement_link_reviews drop column record_kind")
        try:
            block = _link_adjudication_block(
                pg, high_links=HIGH_AFTER, measured_on="2026-09-26")
        finally:
            pg.execute("rollback to savepoint s")
        pg.rollback()
    assert block["high"]["reviewed_high"] == 3
    assert "reviewed_by_kind" not in block["high"]
    assert "reviewed_by_kind" not in block["high"]["by_path"]["announcement+lexicon"]


#: The mart's demotions after R-DEC-110: (award_piid, pe_bli, method, reason).
DEMOTED_AFTER = [
    {"award_piid": "R-6", "pe_bli": "R0602303E", "method": "announcement+lexicon",
     "demotion_reason": "announcement_review_unrecorded"},
    {"award_piid": "R-10", "pe_bli": "R0602303E", "method": "announcement+lexicon",
     "demotion_reason": "announcement_review_refuted"},
    {"award_piid": "R-11", "pe_bli": "R0602303E", "method": "announcement+lexicon",
     "demotion_reason": "announcement_reviewer_rejected"},
    {"award_piid": "R-12", "pe_bli": "R0602303E", "method": "announcement+lexicon",
     "demotion_reason": "announcement_review_unrecorded"},
    {"award_piid": "T-1", "pe_bli": "R0601101E", "method": "account+tokens",
     "demotion_reason": "account_tokens_unadjudicated"},
    # demoted on one row, still high on another: it is in published_high
    {"award_piid": "R-4", "pe_bli": "R0602303E", "method": "announcement+lexicon",
     "demotion_reason": "announcement_review_unrecorded"},
]


def test_the_high_census_counts_the_links_demoted_from_high_by_reason(reviewed):
    """R-DEC-110 asks for a TRUE demotion_reason per demoted link; the census
    publishes their counts, read from the mart, so /methodology/ can say how
    many high links fell to medium and why — never "unreviewed" for a link
    whose record refuted it."""
    with psycopg.connect(reviewed) as pg:
        block = _link_adjudication_block(
            pg, high_links=HIGH_AFTER, measured_on="2026-09-26",
            demoted_links=DEMOTED_AFTER)
    demoted = block["high"]["demoted_from_high"]
    assert demoted == {
        "links": 5,
        "by_reason": {
            "account_tokens_unadjudicated": 1,
            "announcement_review_refuted": 1,
            "announcement_review_unrecorded": 2,
            "announcement_reviewer_rejected": 1,
        },
        "by_path": {
            "account+tokens": {"account_tokens_unadjudicated": 1},
            "announcement+lexicon": {
                "announcement_review_refuted": 1,
                "announcement_review_unrecorded": 2,
                "announcement_reviewer_rejected": 1,
            },
        },
    }
    # The high census itself is untouched by the demotion block.
    assert block["high"]["published_high"] == 3


def test_no_demotion_population_means_no_demotion_key(reviewed):
    with psycopg.connect(reviewed) as pg:
        block = _link_adjudication_block(
            pg, high_links=HIGH_AFTER, measured_on="2026-09-26")
    assert "demoted_from_high" not in block["high"]


def test_published_demotions_are_the_marts_medium_rows_with_a_reason(tmp_path):
    db = _mart(tmp_path, [
        ("D-1", "P0602303E", "announcement+lexicon", "medium",
         "announcement_review_unrecorded"),
        ("D-2", "P0602303E", "announcement+lexicon", "medium",
         "announcement_review_refuted"),
        ("D-2", "P0602303E", "announcement+lexicon", "medium",
         "announcement_review_refuted"),          # a second row, same link
        ("D-3", "P0601101E", "account+tokens", "medium",
         "account_tokens_unadjudicated"),
        ("D-4", "P0602303E", "announcement+lexicon", "high", None),
        ("D-5", "P0602303E", "fpds-ap", "medium", None),
    ])
    assert _published_demotions(db) == [
        {"award_piid": "D-1", "pe_bli": "P0602303E",
         "method": "announcement+lexicon",
         "demotion_reason": "announcement_review_unrecorded"},
        {"award_piid": "D-2", "pe_bli": "P0602303E",
         "method": "announcement+lexicon",
         "demotion_reason": "announcement_review_refuted"},
        {"award_piid": "D-3", "pe_bli": "P0601101E", "method": "account+tokens",
         "demotion_reason": "account_tokens_unadjudicated"},
    ]


def test_published_demotions_are_none_before_the_mart_records_reasons(tmp_path):
    db = _mart(tmp_path, [("D-1", "P0602303E", "announcement+lexicon", "medium")],
               with_reason=False)
    assert _published_demotions(db) is None
    empty = tmp_path / "empty.duckdb"
    duckdb.connect(str(empty)).close()
    assert _published_demotions(empty) is None
