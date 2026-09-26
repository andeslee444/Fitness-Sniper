"""The tier each crosswalk link publishes under, and why (2026-09-25 rulings).

audit_link_grading grades EVERY budget_line_awards row; fct_budget_to_awards
publishes the rows it grades high or medium. Three demotions, each recorded
in `demotion_reason` while `crosswalk_confidence` keeps the loader's grade:

  * #75 (2026-09-04) — an account+tokens link graded high that no adjudication
    reviewed publishes at medium ('account_tokens_unadjudicated').
  * #107(b) (owner-delegated, 2026-09-25) — account+subagency measured 0/60 on
    program attribution, so it leaves the published tiers ('low', which the
    mart filters) unless a two-lens adjudication pinned THAT pair
    (award_verdict 'pinned', pair_reason 'pinned-here', both refuter lenses
    passed) ('account_subagency_not_pinned').
  * #110 (owner-delegated, 2026-09-25) + R-DEC-110 (2026-09-26) — an
    announcement+lexicon link graded high stays high only when a recorded
    review upholds it (a jbook_announcement_link_reviews record, of either
    record_kind, with reviewer_verdict 'link' and adversarial_verdict
    'upheld') AND no recorded reviewer rejection ('weak'/'wrong') or
    adversarial refutation targets the article its card cites (a record with
    no article_id binds to the pair). Otherwise medium, with the reason its
    records actually give: 'announcement_review_refuted',
    'announcement_reviewer_rejected', 'announcement_review_incomplete' or —
    only when no record exists at all — 'announcement_review_unrecorded'.
    An adjudication row is a recorded review too, and its grade wins as
    before.
  * R-DEC-110b (controller, 2026-09-26) — a held-out precision study's
    refutation (Postgres link_precision_samples, verdict 'refuted'), backfilled
    as record_kind 'precision_sample', is a recorded refutation of the PAIR,
    never of one article: it binds whatever article it names. A high
    announcement link the pipeline's own records keep high publishes medium
    when its pair carries one, with 'precision_sample_refuted' — the reason
    the export lane keys its precision-tally rule on, so it is used ONLY when
    the sample verdict alone moved the link; when the pipeline's records (or
    another rule) would demote the link anyway, their reason stands. A
    precision-sample record never upholds a link.
  * R-DEC-110c (controller, 2026-09-26) — "it binds to every published
    method of the pair". The grading reads a refutation per (award_piid,
    pe_bli) pair — every row of the pair, whatever row the backfill attached
    it to, whatever tier the sample drew the link from, and whatever method
    the link publishes under today: an unadjudicated link of ANY method that
    would publish high carries it down to medium. It never re-filters by
    method.

The unit tests run the committed model's SQL (and the R-DEC-110b gate's) against
a throwaway DuckDB; the build tests build the fixture lake with dbt.
"""
import os
import subprocess
from pathlib import Path

import duckdb
import pytest

from test_dbt_build import make_lake

ROOT = Path(__file__).resolve().parents[1]

AWARD_COLS = (
    "pe_bli, exhibit, fiscal_year, organization, award_piid, recipient_name,"
    " recipient_uei, matched_obligation, method, confidence, score, rationale,"
    " account"
)
ADJ_COLS = (
    "award_piid, pe_bli, adjudicated_confidence, award_verdict, pair_reason,"
    " basis, evidence, refuter_lenses_passed, method, adjudicated_at"
)
# The R-DEC-110 contract (migration 018 as enlarged in the stage-1 fix round):
# every column all-varchar, as `jbooks export-facts` writes it. `reason` is
# last so a precision_sample row can carry the tier its sample was drawn from
# (the head the backfill writes) — which the grading must never read.
REVIEW_COLS = (
    "award_piid, pe_bli, exhibit, fiscal_year, record_kind, reviewer_verdict,"
    " adversarial_verdict, article_id, cites_reviewed_article, reviewed_at,"
    " source_file, reason"
)


def _grading_sql() -> str:
    sql = (ROOT / "dbt" / "models" / "audit" / "audit_link_grading.sql").read_text()
    for src, table in {
        "{{ source('lake', 'jbook_awards') }}": "awards",
        "{{ source('lake', 'jbook_award_adjudications') }}": "adjudications",
        "{{ source('lake', 'jbook_announcement_link_reviews') }}": "reviews",
    }.items():
        sql = sql.replace(src, table)
    assert "{{" not in sql, "unsubstituted macro left in audit_link_grading.sql"
    return sql


def _grade_rows(awards, adjudications=(), reviews=()):
    """awards: (piid, pe_bli, method, confidence); every link R-1/2026/DARPA.
    adjudications: (piid, pe_bli, adjudicated_confidence, award_verdict,
    pair_reason, refuter_lenses_passed). reviews: (piid, pe_bli, exhibit,
    fiscal_year, record_kind, reviewer_verdict, adversarial_verdict,
    article_id, cites_reviewed_article, reason) — build them with rev()."""
    con = duckdb.connect()
    # all-varchar, exactly as export_facts writes every jbooks parquet
    for table, cols in (("awards", AWARD_COLS), ("adjudications", ADJ_COLS),
                        ("reviews", REVIEW_COLS)):
        defs = ", ".join(f"{c.strip()} varchar" for c in cols.split(","))
        con.execute(f"create table {table} ({defs})")
    for piid, pe, method, conf in awards:
        con.execute(
            "insert into awards values (?, 'R-1', '2026', 'DARPA', ?, 'X', 'U',"
            " '1', ?, ?, '1', 'r', '0400')",
            [pe, piid, method, conf],
        )
    for piid, pe, adj_conf, verdict, reason, lenses in adjudications:
        con.execute(
            "insert into adjudications values (?, ?, ?, ?, ?, 'narrative-grep',"
            " 'e', ?, 'hand-adjudication-v1', '2026-09-01')",
            [piid, pe, adj_conf, verdict, reason, lenses],
        )
    for row in reviews:
        con.execute(
            "insert into reviews values (?, ?, ?, ?, ?, ?, ?, ?, ?, null,"
            " 'data/research/announcements/wave4_verdicts/chunk_000_A.json', ?)",
            # a hand-written 9-tuple (no reason) reads as a NULL reason
            list(row) + [None] * (10 - len(row)),
        )
    rows = con.execute(
        "select award_piid, pe_bli, confidence, crosswalk_confidence,"
        " demotion_reason from (" + _grading_sql() + ") order by award_piid, pe_bli"
    ).fetchall()
    con.close()
    # one graded row per link — a review or adjudication join that fanned a
    # link out would publish it twice
    assert len(rows) == len(awards), rows
    return {(r[0], r[1]): r[2:] for r in rows}


def _grade(awards, adjudications=(), reviews=()):
    """_grade_rows keyed by award_piid alone (every fixture link but the
    other-PE test's has its own piid)."""
    graded = _grade_rows(awards, adjudications, reviews)
    by_piid = {piid: g for (piid, _pe), g in graded.items()}
    assert len(by_piid) == len(graded), graded
    return by_piid


# ── #107(b) ──────────────────────────────────────────────────────────────────

def test_account_subagency_leaves_the_published_tiers_unless_two_lens_pinned():
    g = _grade(
        awards=[
            ("MECH", "0601101E", "account+subagency", "medium"),
            ("POOL", "0601101E", "account+subagency", "medium"),
            ("LORELEI", "0601101E", "account+subagency", "medium"),
            ("PINNED", "0601101E", "account+subagency", "medium"),
            ("ONELENS", "0601101E", "account+subagency", "medium"),
            ("REFUTED", "0601101E", "account+subagency", "medium"),
        ],
        adjudications=[
            ("POOL", "0601101E", "medium", "darpa_unpinned", "unpinned-pool", None),
            # award pinned (to another PE, by project title) — THIS pair is in
            # the unpinned pool: the #141 shape, not a pin of this pair
            ("LORELEI", "0601101E", "medium", "pinned", "unpinned-pool", None),
            ("PINNED", "0601101E", "high", "pinned", "pinned-here", "2"),
            ("ONELENS", "0601101E", "high", "pinned", "pinned-here", "1"),
            ("REFUTED", "0601101E", "medium", "pinned", "pin-refuted", None),
        ],
    )
    demoted = ("low", "medium", "account_subagency_not_pinned")
    assert g["MECH"] == demoted
    assert g["POOL"] == demoted
    assert g["LORELEI"] == demoted
    assert g["ONELENS"] == demoted
    assert g["REFUTED"] == demoted
    # the one shape the ruling keeps
    assert g["PINNED"] == ("high", "medium", None)


def test_an_adjudicated_drop_is_not_relabelled_as_a_demotion():
    g = _grade(
        awards=[("REJ", "0601101E", "account+subagency", "medium"),
                ("LOW", "0601101E", "account+subagency", "medium")],
        adjudications=[
            ("REJ", "0601101E", "reject", "contradicted", "contradicted", None),
            ("LOW", "0601101E", "low", "not_darpa", "account-only", None),
        ],
    )
    assert g["REJ"] == ("reject", "medium", None)
    assert g["LOW"] == ("low", "medium", None)


def test_other_methods_are_untouched_by_107():
    g = _grade(awards=[("FPDS", "3010", "fpds-ap", "medium"),
                       ("ACCT", "0601101E", "account", "medium"),
                       ("SUB", "0601101E", "subaward+lexicon", "medium")])
    assert g == {k: ("medium", "medium", None) for k in ("ACCT", "FPDS", "SUB")}


# ── #75 (unchanged behaviour, now with its reason recorded) ─────────────────

def test_unadjudicated_account_tokens_high_publishes_medium_with_its_reason():
    g = _grade(
        awards=[("TOK", "0601101E", "account+tokens", "high"),
                ("TOKADJ", "0601101E", "account+tokens", "high")],
        adjudications=[("TOKADJ", "0601101E", "high", "pinned", "pinned-here", "2")],
    )
    assert g["TOK"] == ("medium", "high", "account_tokens_unadjudicated")
    assert g["TOKADJ"] == ("high", "high", None)


# ── #110 / R-DEC-110 ─────────────────────────────────────────────────────────

ANN = "announcement+lexicon"
CITED = "1001"   # the article every fixture link's card cites
OTHER = "2002"   # an article the card does not cite


def rev(piid, reviewer, adversarial, *, article=CITED, kind="verdict_pair",
        pe="0603", fy="2026", reason=None):
    """One review record of the link (piid, pe, R-1, fy). cites_reviewed_article
    is what the backfill computes from award_link_sources: whether the link's
    card cites the article this record reviewed (NULL when it names none)."""
    cites = None if article is None else ("True" if article == CITED else "False")
    return (piid, pe, "R-1", fy, kind, reviewer, adversarial, article, cites,
            reason)


def survivor(piid, **kw):
    """A wave 1-3 `surviving` entry: the reviewer's link survived the
    adversarial refuter (R-DEC-110). It names no article."""
    return rev(piid, "link", "upheld", article=None, kind="survivor_list", **kw)


HIGH = ("high", "high", None)


REASONS = {
    "refuted": "announcement_review_refuted",
    "reviewer_rejected": "announcement_reviewer_rejected",
    "incomplete": "announcement_review_incomplete",
    "unrecorded": "announcement_review_unrecorded",
    # R-DEC-110b/110c; the export lane's precision-tally rule keys on this
    # exact value
    "precision_sample": "precision_sample_refuted",
}


def sample(piid, adversarial="refuted", *, article=None, drawn=ANN, **kw):
    """R-DEC-110b/110c: a held-out precision-study verdict on the PAIR,
    backfilled as record_kind 'precision_sample' onto the link rows of the
    pair (a refutation is reviewer 'link' + adversarial 'refuted'). The
    backfill names no article: the study judges the pair on attribution, not
    one announcement. Its reason opens with the tier the sample DREW the link
    from (scripts/backfill_announcement_link_reviews.py PRECISION_REASON),
    which need not be the method the link publishes under today."""
    reason = (f"drawn from the {drawn} tier of held-out precision sample"
              f" 2026-09-04 (rubric attribution), judged {adversarial}")
    return rev(piid, "link", adversarial, article=article,
               kind="precision_sample", reason=reason, **kw)


def demoted(reason):
    return ("medium", "high", REASONS[reason])


def test_announcement_high_needs_a_recorded_review_that_upholds_it():
    g = _grade(
        awards=[(p, "0603", ANN, "high") for p in (
            "UPHELD", "SURVIVOR", "NOREVIEW", "OTHERFY", "OTHERPE")],
        reviews=[
            rev("UPHELD", "link", "upheld"),
            # R-DEC-110: a wave 1-3 survivor-list entry IS a recorded review
            survivor("SURVIVOR"),
            # a review of a DIFFERENT link row is not a review of this one
            rev("OTHERFY", "link", "upheld", fy="2025"),
            rev("OTHERPE", "link", "upheld", pe="0604"),
        ],
    )
    assert g["UPHELD"] == HIGH
    assert g["SURVIVOR"] == HIGH
    # 'unrecorded' is said ONLY where no record of the link exists
    for piid in ("NOREVIEW", "OTHERFY", "OTHERPE"):
        assert g[piid] == demoted("unrecorded"), (piid, g[piid])


def test_a_demoted_link_carries_the_reason_its_records_give():
    """The stage-1 mislabel: a link whose recorded review REFUTED it (or came
    back incomplete) was published as 'review unrecorded'. The reason must be
    what the records say."""
    g = _grade(
        awards=[(p, "0603", ANN, "high") for p in (
            "REFUTED", "REFUTED_ELSEWHERE", "WEAK", "WRONG_ELSEWHERE",
            "INCOMPLETE", "NOTRUN", "CITED_FIRST", "REFUTED_OVER_REJECTED")],
        reviews=[
            rev("REFUTED", "link", "refuted"),
            # no uphold anywhere, and the pair was refuted on another article:
            # still a recorded refutation of this pair
            rev("REFUTED_ELSEWHERE", "link", "refuted", article=OTHER),
            # wave-4 reviewer rejections never reach the lenses: 'not_run'
            rev("WEAK", "weak", "not_run"),
            rev("WRONG_ELSEWHERE", "wrong", "not_run", article=OTHER),
            # migration 018: a lens missing/malformed and none refuting
            rev("INCOMPLETE", "link", "incomplete"),
            # a reviewer 'link' no lens answered
            rev("NOTRUN", "link", "not_run"),
            # the record on the cited article speaks first: rejected there,
            # refuted only on another article
            rev("CITED_FIRST", "weak", "not_run"),
            rev("CITED_FIRST", "link", "refuted", article=OTHER),
            # both on the cited article: the adversarial refutation is named
            rev("REFUTED_OVER_REJECTED", "wrong", "not_run"),
            rev("REFUTED_OVER_REJECTED", "link", "refuted"),
        ],
    )
    assert g["REFUTED"] == demoted("refuted")
    assert g["REFUTED_ELSEWHERE"] == demoted("refuted")
    assert g["WEAK"] == demoted("reviewer_rejected")
    assert g["WRONG_ELSEWHERE"] == demoted("reviewer_rejected")
    assert g["INCOMPLETE"] == demoted("incomplete")
    assert g["NOTRUN"] == demoted("incomplete")
    assert g["CITED_FIRST"] == demoted("reviewer_rejected")
    assert g["REFUTED_OVER_REJECTED"] == demoted("refuted")


def test_a_contrary_record_on_the_cited_article_outweighs_an_uphold():
    """R-DEC-110: high iff an upholding record exists AND no recorded reviewer
    rejection / adversarial refutation targets the article the card cites.
    A contrary record about ANOTHER article of the pair does not bind."""
    g = _grade(
        awards=[(p, "0603", ANN, "high") for p in (
            "UP_REFUTED_CITED", "UP_REJECTED_CITED", "UP_SAME_ARTICLE",
            "UP_REFUTED_OTHER", "UP_REJECTED_OTHER", "UP_INCOMPLETE_CITED",
            "SURVIVOR_REFUTED_UNNAMED", "SURVIVOR_REJECTED_OTHER")],
        reviews=[
            rev("UP_REFUTED_CITED", "link", "upheld", article=OTHER),
            rev("UP_REFUTED_CITED", "link", "refuted"),
            rev("UP_REJECTED_CITED", "link", "upheld", article=OTHER),
            rev("UP_REJECTED_CITED", "wrong", "not_run"),
            # the same article proposed twice: upheld once, rejected once
            rev("UP_SAME_ARTICLE", "link", "upheld"),
            rev("UP_SAME_ARTICLE", "weak", "not_run"),
            rev("UP_REFUTED_OTHER", "link", "upheld"),
            rev("UP_REFUTED_OTHER", "link", "refuted", article=OTHER),
            rev("UP_REJECTED_OTHER", "link", "upheld"),
            rev("UP_REJECTED_OTHER", "weak", "not_run", article=OTHER),
            # the ruling names rejections and refutations; an incomplete
            # adversarial read is neither, so an uphold elsewhere stands
            rev("UP_INCOMPLETE_CITED", "link", "upheld", article=OTHER),
            rev("UP_INCOMPLETE_CITED", "link", "incomplete"),
            # a contrary record that names no article binds to the pair
            survivor("SURVIVOR_REFUTED_UNNAMED"),
            rev("SURVIVOR_REFUTED_UNNAMED", "link", "refuted", article=None),
            survivor("SURVIVOR_REJECTED_OTHER"),
            rev("SURVIVOR_REJECTED_OTHER", "wrong", "not_run", article=OTHER),
        ],
    )
    assert g["UP_REFUTED_CITED"] == demoted("refuted")
    assert g["UP_REJECTED_CITED"] == demoted("reviewer_rejected")
    assert g["UP_SAME_ARTICLE"] == demoted("reviewer_rejected")
    assert g["UP_REFUTED_OTHER"] == HIGH
    assert g["UP_REJECTED_OTHER"] == HIGH
    assert g["UP_INCOMPLETE_CITED"] == HIGH
    assert g["SURVIVOR_REFUTED_UNNAMED"] == demoted("refuted")
    assert g["SURVIVOR_REJECTED_OTHER"] == HIGH


def test_an_incomplete_record_is_neither_an_uphold_nor_a_refutation():
    """R-DEC-INCOMPLETE (controller ruling 2026-09-26): one rule everywhere —
    an 'incomplete' adversarial record (a lens missing or malformed, none
    refuting) neither upholds nor refutes. Alone it demotes with
    'announcement_review_incomplete'; it never binds as a refutation of the
    article the card cites, whichever article it names — so it can neither
    demote an upheld link nor be reported as a refutation."""
    g = _grade(
        awards=[(p, "0603", ANN, "high") for p in (
            "INC_CITED", "INC_UNNAMED", "INC_MANY", "INC_SAME_ARTICLE_AS_UPHOLD",
            "INC_UNNAMED_BESIDE_SURVIVOR", "INC_CITED_REFUTED_OTHER")],
        reviews=[
            rev("INC_CITED", "link", "incomplete"),
            rev("INC_UNNAMED", "link", "incomplete", article=None),
            rev("INC_MANY", "link", "incomplete"),
            rev("INC_MANY", "link", "incomplete", article=OTHER),
            rev("INC_MANY", "link", "incomplete", article=None),
            # upheld and incomplete on the very article the card cites
            rev("INC_SAME_ARTICLE_AS_UPHOLD", "link", "upheld"),
            rev("INC_SAME_ARTICLE_AS_UPHOLD", "link", "incomplete"),
            # an incomplete read naming no article binds to the pair — and
            # still is not a refutation
            survivor("INC_UNNAMED_BESIDE_SURVIVOR"),
            rev("INC_UNNAMED_BESIDE_SURVIVOR", "link", "incomplete", article=None),
            # no uphold: the reason is the refutation the records hold (on
            # another article), never the incomplete read on the cited one
            rev("INC_CITED_REFUTED_OTHER", "link", "incomplete"),
            rev("INC_CITED_REFUTED_OTHER", "link", "refuted", article=OTHER),
        ],
    )
    for piid in ("INC_CITED", "INC_UNNAMED", "INC_MANY"):
        assert g[piid] == demoted("incomplete"), (piid, g[piid])
    assert g["INC_SAME_ARTICLE_AS_UPHOLD"] == HIGH
    assert g["INC_UNNAMED_BESIDE_SURVIVOR"] == HIGH
    assert g["INC_CITED_REFUTED_OTHER"] == demoted("refuted")


def test_a_refutation_sample_entry_is_read_like_any_refutation():
    # migration 018's third kind: a wave 1-2 refutations_sample entry (link +
    # refuted), its article the wave's packet — binding only on the cited one
    g = _grade(
        awards=[("RS_CITED", "0603", ANN, "high"), ("RS_OTHER", "0603", ANN, "high"),
                ("RS_ONLY", "0603", ANN, "high")],
        reviews=[survivor("RS_CITED"),
                 rev("RS_CITED", "link", "refuted", kind="refutation_sample"),
                 survivor("RS_OTHER"),
                 rev("RS_OTHER", "link", "refuted", article=OTHER,
                     kind="refutation_sample"),
                 rev("RS_ONLY", "link", "refuted", article=None,
                     kind="refutation_sample")],
    )
    assert g["RS_CITED"] == demoted("refuted")
    assert g["RS_OTHER"] == HIGH
    assert g["RS_ONLY"] == demoted("refuted")


def test_an_empty_article_id_binds_like_a_missing_one():
    # all-varchar parquet: a record that names no article may arrive as ''
    g = _grade(
        awards=[("E", "0603", ANN, "high")],
        reviews=[survivor("E"),
                 ("E", "0603", "R-1", "2026", "verdict_pair", "wrong",
                  "not_run", "", None)],
    )
    assert g["E"] == demoted("reviewer_rejected")


def test_a_record_whose_article_match_is_unknown_binds():
    # an article_id with no cites_reviewed_article verdict: whether it is the
    # cited article is unknown, so the contrary record is read against the
    # card (never the wider claim)
    g = _grade(
        awards=[("U", "0603", ANN, "high")],
        reviews=[survivor("U"),
                 ("U", "0603", "R-1", "2026", "verdict_pair", "link",
                  "refuted", OTHER, None)],
    )
    assert g["U"] == demoted("refuted")


def test_an_adjudicated_announcement_link_keeps_its_adjudicated_grade():
    g = _grade(
        awards=[("ADJ", "0603", ANN, "high"), ("ADJLOW", "0603", ANN, "high")],
        adjudications=[("ADJ", "0603", "high", "pinned", "pinned-here", "2"),
                       ("ADJLOW", "0603", "low", "pinned", "pinned-elsewhere:0604", None)],
        # a contrary record does not override the adjudication either
        reviews=[rev("ADJ", "link", "refuted")],
    )
    assert g["ADJ"] == ("high", "high", None)
    assert g["ADJLOW"] == ("low", "high", None)


def test_a_medium_announcement_link_is_not_touched():
    assert _grade(awards=[("M", "0603", ANN, "medium")],
                  reviews=[rev("M", "link", "refuted")]) == {
        "M": ("medium", "medium", None)
    }


def test_the_grading_never_fans_a_link_out():
    # one link, four review records for it: still one graded row (_grade
    # asserts one row per link)
    graded = _grade(
        awards=[("L", "0603", ANN, "high")],
        reviews=[rev("L", "link", "upheld"),
                 rev("L", "link", "upheld"),
                 survivor("L"),
                 rev("L", "wrong", "not_run", article=OTHER)],
    )
    assert graded == {"L": HIGH}


# ── R-DEC-110b: the held-out precision study's refutations ──────────────────

def test_a_precision_sample_refutation_demotes_a_link_its_pipeline_upholds():
    """R-DEC-110b: 'No known-refuted link at high.' A precision-sample
    refutation binds to the pair, whatever article it names, so a link the
    pipeline's records keep high publishes medium, and the reason says the
    sample moved it. R-DEC-110c: it binds the PAIR — a record found on
    another row of the pair (another edition) binds this row too."""
    g = _grade(
        awards=[(p, "0603", ANN, "high") for p in (
            "PS_SURVIVOR", "PS_VERDICT", "PS_NAMES_OTHER", "PS_NAMES_CITED",
            "PS_REFUTED_OTHER_TOO", "PS_OTHER_ROW", "PS_TWO_STUDIES",
            "CONTROL")],
        reviews=[
            survivor("PS_SURVIVOR"), sample("PS_SURVIVOR"),
            rev("PS_VERDICT", "link", "upheld"), sample("PS_VERDICT"),
            # the study judges the PAIR on attribution: an article it names
            # does not narrow it (unlike a pipeline record on another article)
            survivor("PS_NAMES_OTHER"), sample("PS_NAMES_OTHER", article=OTHER),
            survivor("PS_NAMES_CITED"), sample("PS_NAMES_CITED", article=CITED),
            # the pipeline keeps it high (a refutation of ANOTHER article does
            # not bind); the sample alone moves it
            rev("PS_REFUTED_OTHER_TOO", "link", "upheld"),
            rev("PS_REFUTED_OTHER_TOO", "link", "refuted", article=OTHER),
            sample("PS_REFUTED_OTHER_TOO"),
            # attached to ANOTHER row of the pair only: R-DEC-110c binds the
            # pair, so this link is refuted too (before 110c it stayed high)
            survivor("PS_OTHER_ROW"), sample("PS_OTHER_ROW", fy="2025"),
            # two studies refuted it: one graded row, one reason
            survivor("PS_TWO_STUDIES"), sample("PS_TWO_STUDIES"),
            sample("PS_TWO_STUDIES"),
            survivor("CONTROL"),
        ],
    )
    for piid in ("PS_SURVIVOR", "PS_VERDICT", "PS_NAMES_OTHER", "PS_NAMES_CITED",
                 "PS_REFUTED_OTHER_TOO", "PS_OTHER_ROW", "PS_TWO_STUDIES"):
        assert g[piid] == demoted("precision_sample"), (piid, g[piid])
    assert g["CONTROL"] == HIGH


def test_the_pipeline_reason_stands_when_its_records_alone_demote_the_link():
    """'precision_sample_refuted' means the sample verdict ALONE moved the link
    (the export keeps such a link in the tier it was tallied in immediately
    before the demotion, so the measured precision is never flattered by
    it). A link the pipeline's own records demote anyway keeps the
    pipeline's true reason — counting it as sample-demoted would move a link
    the sample did not move."""
    g = _grade(
        awards=[(p, "0603", ANN, "high") for p in (
            "CITED_REFUTED", "CITED_REJECTED", "ONLY_SAMPLE", "INCOMPLETE",
            "REFUTED_ELSEWHERE", "REJECTED_ELSEWHERE", "NOTRUN")],
        reviews=[
            rev("CITED_REFUTED", "link", "upheld", article=OTHER),
            rev("CITED_REFUTED", "link", "refuted"), sample("CITED_REFUTED"),
            survivor("CITED_REJECTED"), rev("CITED_REJECTED", "weak", "not_run"),
            sample("CITED_REJECTED"),
            # no pipeline record at all: the pipeline would demote it as
            # unrecorded; a precision sample is not a pipeline review
            sample("ONLY_SAMPLE"),
            rev("INCOMPLETE", "link", "incomplete"), sample("INCOMPLETE"),
            rev("REFUTED_ELSEWHERE", "link", "refuted", article=OTHER),
            sample("REFUTED_ELSEWHERE"),
            rev("REJECTED_ELSEWHERE", "wrong", "not_run", article=OTHER),
            sample("REJECTED_ELSEWHERE"),
            rev("NOTRUN", "link", "not_run"), sample("NOTRUN"),
        ],
    )
    assert g["CITED_REFUTED"] == demoted("refuted")
    assert g["CITED_REJECTED"] == demoted("reviewer_rejected")
    assert g["ONLY_SAMPLE"] == demoted("unrecorded")
    assert g["INCOMPLETE"] == demoted("incomplete")
    assert g["REFUTED_ELSEWHERE"] == demoted("refuted")
    assert g["REJECTED_ELSEWHERE"] == demoted("reviewer_rejected")
    assert g["NOTRUN"] == demoted("incomplete")


def test_a_precision_sample_record_never_upholds_a_link():
    """The study measures the published tier; its verdicts are never the
    uphold a link needs (R-DEC-110b admits its refutations only). Should a
    non-refuting precision_sample row ever reach the table (the source test
    refuses it first), the grading still does not read it as an uphold, and
    it is not a pipeline review record either."""
    g = _grade(
        awards=[(p, "0603", ANN, "high") for p in (
            "CONFIRMED_ONLY", "CONFIRMED_BESIDE_REFUTED", "CONFIRMED_BESIDE_SURVIVOR")],
        reviews=[
            sample("CONFIRMED_ONLY", "upheld"),
            sample("CONFIRMED_BESIDE_REFUTED", "upheld"),
            rev("CONFIRMED_BESIDE_REFUTED", "link", "refuted", article=OTHER),
            sample("CONFIRMED_BESIDE_SURVIVOR", "upheld"),
            survivor("CONFIRMED_BESIDE_SURVIVOR"),
        ],
    )
    assert g["CONFIRMED_ONLY"] == demoted("unrecorded")
    assert g["CONFIRMED_BESIDE_REFUTED"] == demoted("refuted")
    assert g["CONFIRMED_BESIDE_SURVIVOR"] == HIGH


def test_a_precision_sample_does_not_regrade_other_tiers():
    """An adjudicated link keeps its adjudicated grade, whatever its method (a
    conflict with a refuting sample is left to
    assert_no_high_link_refuted_by_its_precision_sample, which stops the
    build), and a medium link stays medium with no demotion_reason: a
    refutation only ever moves a link that would publish HIGH."""
    g = _grade(
        awards=[("ADJ", "0603", ANN, "high"), ("MED", "0603", ANN, "medium"),
                ("FPDS", "0603", "fpds-ap", "medium"),
                ("TOKADJ", "0603", "account+tokens", "high")],
        adjudications=[("ADJ", "0603", "high", "pinned", "pinned-here", "2"),
                       ("TOKADJ", "0603", "high", "pinned", "pinned-here", "2")],
        reviews=[sample("ADJ"), sample("MED"), sample("FPDS"), sample("TOKADJ")],
    )
    assert g["ADJ"] == ("high", "high", None)
    assert g["MED"] == ("medium", "medium", None)
    assert g["FPDS"] == ("medium", "medium", None)
    assert g["TOKADJ"] == ("high", "high", None)


# ── R-DEC-110c: the refutation binds the PAIR, under every method ───────────

def test_a_pair_refutation_binds_whatever_tier_the_sample_drew_the_link_from():
    """R-DEC-110c (controller, 2026-09-26): 'A precision-study refutation
    (rubric attribution) is a verdict on the award->PE PAIR: it binds to every
    published method of the pair (FA880712C0012/1203164SF demotes as the
    11th).' That pair's shape: the 2026-09-04 sample drew it from the
    fpds-ap+account tier (withdrawn that day), and today it publishes as
    announcement+lexicon/high, upheld by its pipeline. The record's reason
    names the drawn tier; the grading must not compare it with the method the
    link publishes under — the link demotes whatever tier it was drawn from."""
    g = _grade(
        awards=[(p, "0603", ANN, "high") for p in (
            "DRAWN_FPDS_ACCOUNT", "DRAWN_SUBAWARD", "DRAWN_SUBAGENCY",
            "DRAWN_AS_TODAY", "CONTROL")],
        reviews=[
            survivor("DRAWN_FPDS_ACCOUNT"),
            sample("DRAWN_FPDS_ACCOUNT", drawn="fpds-ap+account"),
            rev("DRAWN_SUBAWARD", "link", "upheld"),
            sample("DRAWN_SUBAWARD", drawn="subaward+lexicon"),
            survivor("DRAWN_SUBAGENCY"),
            sample("DRAWN_SUBAGENCY", drawn="account+subagency"),
            survivor("DRAWN_AS_TODAY"), sample("DRAWN_AS_TODAY", drawn=ANN),
            survivor("CONTROL"),
        ],
    )
    for piid in ("DRAWN_FPDS_ACCOUNT", "DRAWN_SUBAWARD", "DRAWN_SUBAGENCY",
                 "DRAWN_AS_TODAY"):
        assert g[piid] == demoted("precision_sample"), (piid, g[piid])
    assert g["CONTROL"] == HIGH


def test_the_other_pe_of_a_refuted_award_is_not_refuted():
    """The pair is (award_piid, pe_bli): the refutation of an award's link to
    one PE says nothing about its link to another PE."""
    sql_rows = _grade_rows(
        awards=[("AWD", "0603", ANN, "high"), ("AWD", "0604", ANN, "high"),
                ("OTHER_AWD", "0603", ANN, "high")],
        reviews=[survivor("AWD"), survivor("AWD", pe="0604"),
                 survivor("OTHER_AWD"), sample("AWD", drawn="fpds-ap+account")],
    )
    assert sql_rows == {
        ("AWD", "0603"): demoted("precision_sample"),
        ("AWD", "0604"): HIGH,
        ("OTHER_AWD", "0603"): HIGH,
    }, sql_rows


def test_a_pair_refutation_demotes_a_mechanical_high_link_of_any_method():
    """R-DEC-110c on the mart side: the refutation binds on whatever method
    the pair publishes under, so the grading must not re-filter by method.
    Today only announcement+lexicon links publish high without an
    adjudication (every other unadjudicated high is moved by another rule or
    never graded high by its loader), but a loader that grades another method
    high must not carry a refuted pair past the grading: the link publishes
    medium with 'precision_sample_refuted'. A rule that moves the link anyway
    keeps its own reason (account+tokens, account+subagency), a medium link
    stays medium, and an adjudicated link keeps its adjudicated grade (the
    gate stops the build on that conflict)."""
    g = _grade(
        awards=[("SUB_HIGH", "0603", "subaward+lexicon", "high"),
                ("FPDS_HIGH", "0603", "fpds-ap", "high"),
                ("ACCOUNT_HIGH", "0603", "account", "high"),
                ("TOKENS_HIGH", "0603", "account+tokens", "high"),
                ("SUBAGENCY_HIGH", "0603", "account+subagency", "high"),
                ("FPDS_MEDIUM", "0603", "fpds-ap", "medium"),
                ("SUB_HIGH_UNSAMPLED", "0603", "subaward+lexicon", "high"),
                ("ADJ_FPDS_HIGH", "0603", "fpds-ap", "high")],
        adjudications=[("ADJ_FPDS_HIGH", "0603", "high", "pinned", "pinned-here", "2")],
        reviews=[sample("SUB_HIGH", drawn="subaward+lexicon"),
                 sample("FPDS_HIGH", drawn="fpds-ap+account"),
                 sample("ACCOUNT_HIGH", drawn="announcement+lexicon"),
                 sample("TOKENS_HIGH", drawn="account+tokens"),
                 sample("SUBAGENCY_HIGH", drawn="account+subagency"),
                 sample("FPDS_MEDIUM", drawn="fpds-ap+account"),
                 sample("ADJ_FPDS_HIGH", drawn="fpds-ap")],
    )
    for piid in ("SUB_HIGH", "FPDS_HIGH", "ACCOUNT_HIGH"):
        assert g[piid] == demoted("precision_sample"), (piid, g[piid])
    assert g["TOKENS_HIGH"] == ("medium", "high", "account_tokens_unadjudicated")
    assert g["SUBAGENCY_HIGH"] == ("low", "high", "account_subagency_not_pinned")
    assert g["FPDS_MEDIUM"] == ("medium", "medium", None)
    assert g["SUB_HIGH_UNSAMPLED"] == HIGH
    assert g["ADJ_FPDS_HIGH"] == HIGH


def _gate_sql() -> str:
    sql = (ROOT / "dbt" / "tests"
           / "assert_no_high_link_refuted_by_its_precision_sample.sql").read_text()
    for src, table in {
        "{{ ref('fct_budget_to_awards') }}": "published",
        "{{ source('lake', 'jbook_announcement_link_reviews') }}": "reviews",
    }.items():
        sql = sql.replace(src, table)
    assert "{{" not in sql, "unsubstituted macro left in the gate"
    return sql


def test_the_gate_fails_on_any_published_high_link_its_precision_sample_refuted():
    """The gate that would have caught the 10 known-refuted high links
    (R-DEC-110b), read against the published mart for EVERY method — a link an
    adjudication pinned high while its held-out sample refuted it is a
    conflict for a person to rule on, so the build stops instead of
    publishing it. It reads a refutation per PAIR, as the grading does
    (R-DEC-110c): a record on another row of the pair, or drawn from another
    tier than the link publishes under, still binds; a record of the same
    award on another PE does not."""
    con = duckdb.connect()
    con.execute(
        "create table published (award_piid varchar, pe_bli varchar,"
        " exhibit varchar, fiscal_year integer, method varchar,"
        " confidence varchar, confidence_source varchar, demotion_reason varchar)")
    con.executemany("insert into published values (?, ?, 'R-1', 2026, ?, ?, ?, ?)", [
        ("HIGH_REFUTED", "0603", ANN, "high", "mechanical", None),
        ("ADJ_REFUTED", "0603", "account+tokens", "high", "adjudicated", None),
        ("DEMOTED", "0603", ANN, "medium", "mechanical", "precision_sample_refuted"),
        ("HIGH_CONFIRMED", "0603", ANN, "high", "mechanical", None),
        ("HIGH_PIPELINE_REFUTED_OTHER", "0603", ANN, "high", "mechanical", None),
        ("HIGH_SAMPLE_ON_OTHER_ROW", "0603", ANN, "high", "mechanical", None),
        ("HIGH_DRAWN_ELSEWHERE", "0603", ANN, "high", "mechanical", None),
        ("SUB_HIGH_REFUTED", "0603", "subaward+lexicon", "high", "mechanical", None),
        ("HIGH_OTHER_PE_REFUTED", "0603", ANN, "high", "mechanical", None),
    ])
    defs = ", ".join(f"{c.strip()} varchar" for c in REVIEW_COLS.split(","))
    con.execute(f"create table reviews ({defs})")
    for row in (sample("HIGH_REFUTED"), sample("ADJ_REFUTED"),
                sample("HIGH_SAMPLE_ON_OTHER_ROW", fy="2025"),
                sample("HIGH_DRAWN_ELSEWHERE", drawn="fpds-ap+account"),
                sample("SUB_HIGH_REFUTED", drawn="subaward+lexicon"),
                sample("HIGH_OTHER_PE_REFUTED", pe="0604"),
                sample("DEMOTED"), sample("HIGH_CONFIRMED", "upheld"),
                rev("HIGH_PIPELINE_REFUTED_OTHER", "link", "refuted", article=OTHER)):
        con.execute("insert into reviews values (?, ?, ?, ?, ?, ?, ?, ?, ?, null,"
                    " 'link_precision_samples', ?)", list(row))
    failures = sorted(r[0] for r in con.execute(
        "select award_piid from (" + _gate_sql() + ")").fetchall())
    con.close()
    assert failures == ["ADJ_REFUTED", "HIGH_DRAWN_ELSEWHERE", "HIGH_REFUTED",
                        "HIGH_SAMPLE_ON_OTHER_ROW", "SUB_HIGH_REFUTED"], failures


# ── the fixture lake, built with dbt ────────────────────────────────────────

def _build(data_dir: Path, *select: str):
    (data_dir / "duckdb").mkdir(exist_ok=True)
    db = data_dir / "duckdb" / "test.duckdb"
    env = {**os.environ, "GOVBUDGET_DATA": str(data_dir), "GOVBUDGET_DUCKDB": str(db)}
    cmd = ["uv", "run", "dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"]
    if select:
        cmd += ["--select", *select]
    return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True), db


def test_the_fixture_lake_publishes_each_tier_as_graded(tmp_path):
    make_lake(tmp_path)
    result, db = _build(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    con = duckdb.connect(str(db), read_only=True)
    try:
        published = dict(con.sql(
            "select award_piid, confidence || '|' || coalesce(demotion_reason, '')"
            " from fct_budget_to_awards"
            " where award_piid like 'HR0011%' or award_piid like 'ANN%'"
        ).fetchall())
        assert published == {
            "HR001124C0001": "high|",
            "HR001124C0002": "medium|account_tokens_unadjudicated",
            # #107(b): the two-lens pinned account+subagency pair publishes…
            "HR001125C0010": "high|",
            # #110 / R-DEC-110: upheld by a survivor-list record (a reviewer
            # rejection of ANOTHER article does not bind) / refuted on the
            # article its card cites
            "ANN0001": "high|",
            "ANN0002": "medium|announcement_review_refuted",
        }, published
        # …the unpinned one does not publish, and the audit model says why
        assert con.sql(
            "select confidence, crosswalk_confidence, demotion_reason"
            " from audit_link_grading where award_piid = 'HR001125C0011'"
        ).fetchone() == ("low", "medium", "account_subagency_not_pinned")
        # #130 on the built mart: the shared '3010' code (one fpds-ap link on
        # each member) is labelled code-level, an ordinary code is not
        scope = dict(con.sql(
            "select pe_bli, scope || '|' || member_programs || '|'"
            " || member_keys_with_links || '|' || links_outside_member_keys"
            " from fct_program_concentration"
        ).fetchall())
        assert scope == {"0601101E": "program|1|1|0", "3010": "code|2|2|0"}, scope
    finally:
        con.close()


def test_a_missing_review_parquet_fails_the_build_instead_of_demoting_silently(tmp_path):
    """A lake whose export-facts predates the review backfill must not
    quietly publish every announcement link at medium: the build stops."""
    make_lake(tmp_path)
    (tmp_path / "parquet/jbooks/announcement_link_reviews.parquet").unlink()
    result, _db = _build(tmp_path)
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    assert "announcement_link_reviews.parquet" in out, out


def _add_review_rows(data_dir: Path, *values_sql: str):
    """Append rows to the fixture lake's announcement_link_reviews.parquet, in
    the all-varchar shape export-facts writes (make_lake's column order)."""
    path = data_dir / "parquet/jbooks/announcement_link_reviews.parquet"
    con = duckdb.connect()
    try:
        con.execute(f"create table t as select * from read_parquet('{path}')")
        for values in values_sql:
            con.execute(f"insert into t values {values}")
        con.execute(f"copy t to '{path}' (format parquet)")
    finally:
        con.close()


# R-DEC-110b: a precision-study refutation of ANN0001's pair, as the backfill
# records it — reviewer 'link', adversarial 'refuted', no article (the study
# judges the pair), no lens count, no paragraph.
_ANN0001_SAMPLE_REFUTED = (
    "('ANN0001','0601101E','R-1','2026','precision_sample','link','refuted',"
    " null,'False',null,null,null,null,"
    " 'link_precision_samples:2026-09-12')"
)


def test_the_fixture_lake_demotes_a_high_link_its_precision_sample_refuted(tmp_path):
    """R-DEC-110b end to end: the source contract accepts record_kind
    'precision_sample', ANN0001 (upheld by its survivor-list record) publishes
    medium with 'precision_sample_refuted', and the whole build — including
    assert_no_high_link_refuted_by_its_precision_sample — passes."""
    make_lake(tmp_path)
    _add_review_rows(tmp_path, _ANN0001_SAMPLE_REFUTED)
    result, db = _build(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    con = duckdb.connect(str(db), read_only=True)
    try:
        published = dict(con.sql(
            "select award_piid, confidence || '|' || coalesce(demotion_reason, '')"
            " from fct_budget_to_awards where award_piid like 'ANN%'"
        ).fetchall())
        assert published == {
            "ANN0001": "medium|precision_sample_refuted",
            # the pipeline's own refutation of the cited article still names it
            "ANN0002": "medium|announcement_review_refuted",
        }, published
        # crosswalk_confidence keeps the loader's grade
        assert con.sql(
            "select crosswalk_confidence from audit_link_grading"
            " where award_piid = 'ANN0001'").fetchone() == ("high",)
    finally:
        con.close()


def test_a_precision_sample_row_that_is_not_a_refutation_fails_the_build(tmp_path):
    """R-DEC-110b admits the study's REFUTATIONS only. A precision_sample row
    carrying any other adversarial verdict (a confirmation backfilled by
    mistake) is a contract drift: the source test stops the build instead of
    the grading silently ignoring it."""
    make_lake(tmp_path)
    _add_review_rows(
        tmp_path,
        "('ANN0001','0601101E','R-1','2026','precision_sample','link','upheld',"
        " null,'True',null,null,null,null,'link_precision_samples:2026-09-12')",
    )
    result, _db = _build(tmp_path, "source:lake.jbook_announcement_link_reviews")
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    # failed BY the contract test (not merely mentioned beside another error)
    assert "Failure in test precision_sample_rows_are_refutations" in out, out


def test_the_fixture_lake_demotes_a_pair_refuted_under_another_tier(tmp_path):
    """R-DEC-110c end to end, in the export's own column shape (the `reason`
    column carries the drawn tier, as the backfill writes it): ANN0001
    publishes as announcement+lexicon/high and its pipeline upholds it; the
    held-out sample drew the pair from the fpds-ap+account tier and refuted
    it on attribution — FA880712C0012/1203164SF's shape. The link publishes
    medium with 'precision_sample_refuted', and the whole build, gate
    included, passes."""
    make_lake(tmp_path)
    path = tmp_path / "parquet/jbooks/announcement_link_reviews.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            f"create table t as select *, null::varchar as reason"
            f" from read_parquet('{path}')")
        con.execute(
            "insert into t by name select 'ANN0001' as award_piid,"
            " '0601101E' as pe_bli, 'R-1' as exhibit, '2026' as fiscal_year,"
            " 'precision_sample' as record_kind, 'link' as reviewer_verdict,"
            " 'refuted' as adversarial_verdict,"
            " 'drawn from the fpds-ap+account tier of held-out precision sample"
            " 2026-09-04 (rubric attribution), judged refuted: 3620 holds two"
            " mapped lines' as reason,"
            " '2026-09-04' as source_file")
        con.execute(f"copy t to '{path}' (format parquet)")
    finally:
        con.close()
    result, db = _build(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS assert_no_high_link_refuted_by_its_precision_sample" in result.stdout
    con = duckdb.connect(str(db), read_only=True)
    try:
        published = dict(con.sql(
            "select award_piid, method || '|' || confidence || '|'"
            " || coalesce(demotion_reason, '')"
            " from fct_budget_to_awards where award_piid like 'ANN%'"
        ).fetchall())
        assert published == {
            "ANN0001": "announcement+lexicon|medium|precision_sample_refuted",
            "ANN0002": "announcement+lexicon|medium|announcement_review_refuted",
        }, published
    finally:
        con.close()
