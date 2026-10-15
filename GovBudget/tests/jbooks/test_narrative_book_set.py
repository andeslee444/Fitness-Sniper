"""#195: a narrative is cited to the volume of its book set that prints it
(families piece-1 follow-ups design §5.6; Task 23a)."""
from __future__ import annotations

from pathlib import Path

import psycopg

from govbudget.jbooks.provenance_pages import (
    NARRATIVE_CLOSING_SPAN_PAGES,
    NARRATIVE_CLOSING_WORDS,
    RELOCATION_COLUMNS,
    _page_texts,
    book_set,
    build_narrative_provenance,
    narrative_closing,
    narrative_located_at,
    narrative_printed_at,
    page_texts_parallel,
    plan_narrative_relocations,
)
from jbooks.narrative_volumes import seed_book_set, seed_pre_195_rows

ROW_STATE = ("select id, page_number, x0, resolution, candidate_pages,"
             " printed_document_sha256 from provenance_pages order by id")


def _plan(pg_dsn, **kwargs):
    with psycopg.connect(pg_dsn) as con:
        return plan_narrative_relocations(con, log=lambda *_: None, **kwargs)


def test_closing_is_the_last_twelve_words_whitespace_normalized():
    assert (NARRATIVE_CLOSING_WORDS, NARRATIVE_CLOSING_SPAN_PAGES) == (12, 3)
    body = " ".join(f"w{i}" for i in range(1, 31))
    assert narrative_closing(body) == " ".join(f"w{i}" for i in range(19, 31))
    assert narrative_closing("a\n b\t c") == "a b c"
    assert narrative_closing("   ") == ""


def test_printed_at_needs_the_opening_on_the_page_and_the_closing_within_three_pages():
    pages = ["intro OPEN words here", "middle", "more CLOSE", "late END"]
    assert narrative_printed_at(pages, 0, "OPEN words", "more CLOSE")
    assert narrative_printed_at(pages, 0, "OPEN words", "here middle more")  # across page breaks
    assert not narrative_printed_at(pages, 0, "OPEN words", "late END")      # fourth page
    assert not narrative_printed_at(pages, 1, "OPEN words", "more CLOSE")    # opening elsewhere
    assert not narrative_printed_at(pages, 7, "OPEN words", "more CLOSE")    # no such page
    assert not narrative_printed_at(pages, 0, "", "more CLOSE")


def test_located_at_also_needs_the_anchor_on_the_opening_page():
    pages = ["PE 0605001TST intro OPEN words", "more CLOSE"]
    assert narrative_located_at(pages, 0, "OPEN words", "more CLOSE", "0605001TST")
    assert not narrative_located_at(pages, 0, "OPEN words", "more CLOSE", "0605002TST")
    assert not narrative_located_at(pages, 0, "OPEN words", "more CLOSE", None)


def test_book_set_is_edition_org_and_family_attached_volume_first(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    with psycopg.connect(pg_dsn) as con:
        vols = book_set(con, book["doc"]["BA1"])
        from_ba3 = [v.title for v in book_set(con, book["doc"]["BA3"])]
    assert [v.title for v in vols] == ["Book BA1", "Book BA2", "Book BA3", "Book BA4"]
    assert [v.status for v in vols] == ["downloaded", "superseded", "superseded", "superseded"]
    assert (vols[0].sha256, vols[0].document_id) == (book["sha"]["BA1"], book["doc"]["BA1"])
    assert from_ba3 == ["Book BA3", "Book BA1", "Book BA2", "Book BA4"]


def test_page_texts_parallel_matches_the_serial_text_pass(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    paths = [str(book["path"][v]) for v in ("BA1", "BA2", "BA3")]
    assert page_texts_parallel(paths, workers=2) == {p: _page_texts(Path(p)) for p in paths}
    assert page_texts_parallel([]) == {}


def test_plan_relocates_locates_keeps_and_counts(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    plan = _plan(pg_dsn)
    assert plan["counts"] == {"rows": 6, "kept": 1, "located": 1, "relocated": 1,
                              "opening_only": 1, "unresolved": 2}
    by_pe = {ch["fact_key"][1]: ch for ch in plan["changes"]}
    assert sorted(by_pe) == ["0605001TST", "0605002TST"]
    n1, n2 = by_pe["0605001TST"], by_pe["0605002TST"]
    assert n1["kind"] == "relocated" and n1["before"]["page_number"] == 1
    assert (n1["after"]["page_number"], n1["after"]["printed_document_sha256"]) == (2, book["sha"]["BA2"])
    assert (n1["after"]["resolution"], n1["after"]["candidate_pages"]) == ("unique", 1)
    assert n2["kind"] == "located" and n2["before"]["page_number"] is None
    assert (n2["after"]["page_number"], n2["after"]["printed_document_sha256"]) == (1, book["sha"]["BA3"])
    assert all(ch["fact_key"][0] == book["sha"]["BA1"] for ch in plan["changes"])
    assert all(set(ch["after"]) == set(RELOCATION_COLUMNS) for ch in plan["changes"])
    assert {s: (v["status"], v["rows"]) for s, v in plan["printed_volumes"].items()} == {
        book["sha"]["BA2"]: ("superseded", 1), book["sha"]["BA3"]: ("superseded", 1)}


def test_plan_reads_only_and_scopes_by_edition(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    with psycopg.connect(pg_dsn) as con:
        before = con.execute(ROW_STATE).fetchall()
    assert _plan(pg_dsn, fiscal_years=[2026])["counts"]["rows"] == 6
    assert _plan(pg_dsn, fiscal_years=[2025])["counts"]["rows"] == 0
    assert _plan(pg_dsn, printed_column=False)["counts"]["located"] == 1
    with psycopg.connect(pg_dsn) as con:
        assert con.execute(ROW_STATE).fetchall() == before


def test_a_relocated_row_is_kept_by_the_next_plan(pg_dsn, tmp_path):
    """The plan is a fixed point: once its rows are written (Task 23c owns the
    transactional write; a plain update stands in here), it plans nothing."""
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        for ch in _plan(pg_dsn)["changes"]:
            cols = list(ch["after"])
            con.execute(f"update provenance_pages set {', '.join(f'{c} = %s' for c in cols)}"
                        " where id = %s", [ch["after"][c] for c in cols] + [ch["id"]])
    again = _plan(pg_dsn)
    assert again["changes"] == []
    assert again["counts"] == {"rows": 6, "kept": 3, "located": 0, "relocated": 0,
                               "opening_only": 1, "unresolved": 2}


def test_new_rows_record_the_printing_volume(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    assert build_narrative_provenance(pg_dsn) == 6
    with psycopg.connect(pg_dsn) as con:
        rows = {pe: (page, res, printed) for pe, page, res, printed in con.execute(
            "select pe_bli, page_number, resolution, printed_document_sha256"
            " from provenance_pages where target_kind = 'narrative'").fetchall()}
    assert rows == {
        "0605001TST": (2, "unique", book["sha"]["BA2"]),
        "0605002TST": (1, "unique", book["sha"]["BA3"]),
        "0605003TST": (None, "unresolved", None),
        "0605004TST": (2, "unique", None),
        "0605005TST": (3, "unique", None),   # opening only: the pre-#195 rule decides
        "0605006TST": (None, "unresolved", None),
    }
    assert build_narrative_provenance(pg_dsn) == 0
    assert _plan(pg_dsn)["changes"] == []
