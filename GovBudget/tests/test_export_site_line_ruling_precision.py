"""R-DEC-LINK-2026-10-21 and R-DEC-LINK-2026-10-21-B (owner, 2026-10-21) on
the export's held-out link precision tally.

A `withdraw` ruling in dbt/seeds/link_line_rulings.csv grades a pair 'low'
with demotion_reason 'line_activity_mismatch' (or 'precision_sample_refuted'
where a precision sample refuted the pair), so the pair leaves the mart and
lands in `_withdrawn_link_rows`. Two rules decide what the tally does with it:

  * a pair the study itself REFUTED stays in the tally, in the tier it was
    tallied in (R-DEC-110b/110c, `_self_refuted_population`): withdrawing it
    must never raise the figure that caught it — 57/61 for
    announcement+lexicon stays 57/61;
  * any other line-ruled pair follows the population rule /methodology/
    states: "one the corpus no longer publishes is counted in neither
    direction, except a refuted link a ruling withdrew" (the exception is
    the rule above; controller ruling R-DEC-LINK-2026-10-21-R2, narrowed on
    the round-2 review, I-1: a refuted link that left the corpus WITHOUT a
    ruling counts in neither direction, as three of the 2026-09-04
    announcement draw do; the last test pins it). Two of the first ruling's
    34 withdrawn fpds-ap pairs carry a 'confirmed' verdict (F03500|N0001917C0020,
    link_precision_samples id 75; 3264AA0252|W58RGZ18F0050, id 120), so the
    fpds-ap figure loses them: 89/114 -> 87/112, the smaller true number
    (controller ruling R-DEC-LINK-2026-10-21-R1: option B confirmed). One of
    the B ruling's 10 F03500 production-support pairs does too
    (F03500|N0001916C0004, id 74), so it loses that one as well: 87/112 ->
    86/111 (controller ruling R-DEC-LINK-2026-10-21-B-C1; measured read-only
    2026-10-21). The same order's ATA000 link (id 73) and the other two
    sampled B-ruling orders' links on 0147 and ATA000 (ids 72, 96) still
    publish, so their confirmations still count.

And a per-pair ruling is not a withdrawn TIER. The `withdrawn` sub-block
exists so the measurement that caused a tier's withdrawal survives it
(#107(b): account+subagency, 0 of 58); /methodology/ renders every entry as
"its N links were withdrawn from publication". Fed the line-ruled rows, the
unchanged exporter would have minted "fpds-ap: confirmed 2 of 2; its 32
links were withdrawn" on the first ruling's 41 pairs, and "confirmed 3 of 3;
its 42 links were withdrawn" on all 51 (measured 2026-10-21) — a figure that
did not cause the withdrawal, stated as if it had. Line-ruled rows never
enter it.

Run against the fixture Postgres (root conftest's `pg_dsn`).
"""
from __future__ import annotations

import psycopg
import pytest

from govbudget.export_site import _link_precision_block

MARKER = "line-ruling-precision-test"
RUN = "2026-09-04"
ANN = "announcement+lexicon"
FPDS = "fpds-ap"
SUB = "subaward+lexicon"
METHODS = {ANN, FPDS, SUB}
LINE = "line_activity_mismatch"
SAMPLE = "precision_sample_refuted"


def _link(piid, pe, method, reason=None):
    row = {"award_piid": piid, "pe_bli": pe, "method": method}
    if reason is not None:
        row["demotion_reason"] = reason
    return row


@pytest.fixture()
def sampled(pg_dsn):
    """One run's attribution verdicts (method = the tier each was drawn from):

      LR-A1, LR-A2  announcement+lexicon  confirmed
      LR-A3         announcement+lexicon  refuted    <- withdrawn by a ruling
      LR-F1, LR-F2  fpds-ap               confirmed  <- LR-F2 withdrawn
      LR-F3         fpds-ap+account       refuted    <- publishes under fpds-ap;
                                                        withdrawn by a ruling
      LR-S1         subaward+lexicon      confirmed
      LR-X1         account+subagency     refuted    <- the #107(b) tier
    """
    rows = [
        ("LR-A1", "0592", ANN, "confirmed"),
        ("LR-A2", "0592", ANN, "confirmed"),
        ("LR-A3", "0593", ANN, "refuted"),
        ("LR-F1", "F03500", FPDS, "confirmed"),
        ("LR-F2", "F03500", FPDS, "confirmed"),
        ("LR-F3", "0505", "fpds-ap+account", "refuted"),
        ("LR-S1", "0601", SUB, "confirmed"),
        ("LR-X1", "0602", "account+subagency", "refuted"),
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


#: The mart BEFORE the rulings: every sampled link but the #107(b) one
#: publishes (LR-F3 under fpds-ap, where #140 moved it).
BEFORE = [
    _link("LR-A1", "0592", ANN), _link("LR-A2", "0592", ANN),
    _link("LR-A3", "0593", ANN),
    _link("LR-F1", "F03500", FPDS), _link("LR-F2", "F03500", FPDS),
    _link("LR-F3", "0505", FPDS),
    _link("LR-S1", "0601", SUB),
]
#: The #107(b) tier's own withdrawn row, as the export reads it today.
SUBAGENCY = _link("LR-X1", "0602", "account+subagency",
                  "account_subagency_not_pinned")
#: The rulings' rows, as `_withdrawn_link_rows` reads them after the build:
#: graded low, published nowhere.
RULED = [
    _link("LR-A3", "0593", ANN, SAMPLE),     # refuted: keeps the sample reason
    _link("LR-F2", "F03500", FPDS, LINE),    # confirmed, ruled withdrawn
    _link("LR-F3", "0505", FPDS, SAMPLE),    # refuted under another draw tier
    _link("LR-U1", "0549", ANN, LINE),       # never sampled
]
WITHDRAWN = {(r["award_piid"], r["pe_bli"]) for r in RULED}
AFTER = [r for r in BEFORE if (r["award_piid"], r["pe_bli"]) not in WITHDRAWN]


def _figures(block):
    return {m: (v["confirmed"], v["sampled"]) for m, v in block["methods"].items()}


def _precision(dsn, **kw):
    with psycopg.connect(dsn) as pg:
        return _link_precision_block(pg, published_methods=METHODS, **kw)


def test_the_baseline(sampled):
    block = _precision(sampled, published_links=BEFORE, withdrawn_links=[SUBAGENCY])
    assert _figures(block) == {ANN: (2, 3), FPDS: (2, 3), SUB: (1, 1)}
    assert set(block["withdrawn"]) == {"account+subagency"}


def test_a_line_ruling_never_mints_a_withdrawn_figure(sampled):
    """LR-F2 was confirmed and is now withdrawn by a ruling. The unchanged
    exporter put it in `withdrawn` as an fpds-ap figure ("confirmed 1 of 1;
    its 1 link was withdrawn") — a per-pair ruling stated as a tier's
    measured withdrawal. Only the #107(b) tier's figure stays there."""
    block = _precision(sampled, published_links=AFTER,
                       withdrawn_links=[SUBAGENCY, *RULED])
    assert set(block["withdrawn"]) == {"account+subagency"}, block["withdrawn"]
    assert block["withdrawn"]["account+subagency"]["links"] == 1


def test_a_refuted_pair_stays_and_a_confirmed_one_leaves(sampled):
    """The refuted pairs (LR-A3; LR-F3, drawn under fpds-ap+account and
    tallied under fpds-ap) keep their 'refuted' verdicts where they were
    tallied — the withdrawal never raises a figure. The confirmed LR-F2 no
    longer publishes, so it counts in neither direction: fpds-ap 2/3 -> 1/2.
    Announcement and subaward figures are unchanged."""
    block = _precision(sampled, published_links=AFTER,
                       withdrawn_links=[SUBAGENCY, *RULED])
    assert _figures(block) == {ANN: (2, 3), FPDS: (1, 2), SUB: (1, 1)}


def test_with_no_withdrawn_tier_the_block_carries_no_withdrawn_key(sampled):
    block = _precision(sampled, published_links=AFTER, withdrawn_links=RULED)
    assert "withdrawn" not in block
    assert _figures(block) == {ANN: (2, 3), FPDS: (1, 2), SUB: (1, 1)}


@pytest.fixture()
def left_the_corpus(sampled):
    """`sampled` plus LR-A4, an announcement+lexicon link the same run
    refuted. The `sampled` teardown removes it with the rest (same MARKER)."""
    with psycopg.connect(sampled) as pg:
        pg.execute(
            "insert into link_precision_samples (sample_id, award_piid,"
            " pe_bli, method, rubric, verdict, reason, adjudicated_at)"
            " values (%s, 'LR-A4', '0594', %s, 'attribution', 'refuted', %s,"
            " '2026-09-04 12:00:00-04'::timestamptz)",
            (RUN, ANN, MARKER))
        pg.commit()
    return sampled


def test_a_refuted_link_that_left_the_corpus_without_a_ruling_counts_nowhere(
        left_the_corpus):
    """The exception /methodology/ names is a refuted link a RULING withdrew
    (", except a refuted link a ruling withdrew"), not every refuted link the
    corpus stopped publishing. Three refuted announcement+lexicon links of the
    2026-09-04 draw (FA850419F0008|0401132F, FA873018C0065|E00300,
    M6785417C9000|4630) left the lake with no ruling and no demotion_reason,
    so the export sees them in neither population: they count in neither
    direction, and the tally reproduces the published 57/61 only that way
    (round-2 review, I-1, measured read-only 2026-10-21).

    LR-A4 is that shape: refuted, then gone from both the published and the
    withdrawn rows. While it publishes, its refutation counts (2/4); gone, it
    counts in neither direction (2/3) and mints no `withdrawn` figure; withdrawn
    by a ruling (graded low as 'precision_sample_refuted'), it keeps counting
    (2/4)."""
    lr_a4 = _link("LR-A4", "0594", ANN)
    published = _precision(left_the_corpus, published_links=[*AFTER, lr_a4],
                           withdrawn_links=[SUBAGENCY, *RULED])
    assert _figures(published)[ANN] == (2, 4)

    gone = _precision(left_the_corpus, published_links=AFTER,
                      withdrawn_links=[SUBAGENCY, *RULED])
    assert _figures(gone) == {ANN: (2, 3), FPDS: (1, 2), SUB: (1, 1)}
    assert set(gone["withdrawn"]) == {"account+subagency"}

    ruled = _precision(
        left_the_corpus, published_links=AFTER,
        withdrawn_links=[SUBAGENCY, *RULED, _link("LR-A4", "0594", ANN, SAMPLE)])
    assert _figures(ruled) == {ANN: (2, 4), FPDS: (1, 2), SUB: (1, 1)}
    assert set(ruled["withdrawn"]) == {"account+subagency"}
