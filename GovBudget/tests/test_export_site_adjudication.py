"""Regression coverage for regenerated per-link review disclosures."""
import datetime as dt
import duckdb
import psycopg
import pytest
from govbudget import export_site
from govbudget.export_site import _link_adjudication_block, _published_high_links

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

    assert block["high"] == {
        "published_high": 3,
        "adjudicated_high": 1,
        "two_lens_high": 1,
        "by_path": {
            "account+subagency": {"high": 1, "adjudicated": 1, "two_lens": 1},
            "announcement+lexicon": {
                "high": 2,
                "adjudicated": 0,
                "two_lens": 0,
                "with_match_basis": 1,
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
