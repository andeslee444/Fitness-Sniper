"""Subaward citations (ROADMAP #84): FSRS records as a first-class kind.

Links published via method='subaward+lexicon' (113 at 2026-09-10) cited
only the generic derived crosswalk row. `award_link_sources` already held the
subaward number; the subawards lake holds the subawardee and the prime
award's USAspending page. They now mint `kind='subaward'` rows.

Scope rulings pinned here:
  - official_url is the PRIME award's USAspending page: USAspending publishes
    no page for an individual subaward, and the FSRS record's own
    usaspending_permalink column points at the prime (whose Subawards tab
    lists the record). When the permalink column is blank the URL is built
    from prime_award_unique_key; when the lake has no row at all the export
    FAILS — never a fabricated URL.
  - query_body = {match_basis, subaward_number, subawardee}. No description
    (monthly re-reports carry several per record; none is THE evidence text).
  - formula (method + confidence sentence) is kept on the row: site gate 24
    leg n reads the published-tier universe from it.
  - Fact-id minting is untouched (gate 2's Cite-state contract).
  - A subaward+lexicon link with no source row, or a source row with no lake
    row, FAILS THE EXPORT (same species as the announcement raise).

The fixture link is real (checked read-only 2026-09-10): (N6833517C0392,
0605502N) is a live subaward+lexicon link whose award_link_sources row carries
source_id '000000821', and the lake's record for that pair carries exactly the
subawardee, unique key and permalink below.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from govbudget.export_site import (
    _build_budget_to_awards_citation_rows,
    _index_subaward_sources,
    _lake_parquet_dir,
    _load_subaward_lake_rows,
    _subaward_lake_keys,
    _subaward_row,
    fact_id_derived,
)
from govbudget.verify_phase5b1 import (
    _verify_subaward,
    citation_gate5b1,
    integrity_gate5b1,
)

# Citation row layout (27 columns) — mirrors export_site citations.parquet
_CIT_IDX = {
    name: i for i, name in enumerate([
        "fact_id", "kind", "units", "amount_text", "page_number",
        "x0", "x1", "top_pt", "bottom_pt", "page_width", "page_height",
        "resolution", "sheet", "cells", "amount_thousands", "sha256",
        "hosted_pdf_url", "official_url", "xml_path", "retrieved_at",
        "formula", "inputs", "query_body", "recorded_value",
        "pe_bli", "scenario", "amount_type",
    ])
}
_CIT_COL_DEFS = (
    "fact_id varchar, kind varchar, units varchar, amount_text varchar,"
    " page_number integer, x0 double, x1 double, top_pt double, bottom_pt double,"
    " page_width double, page_height double, resolution varchar,"
    " sheet varchar, cells varchar, amount_thousands double,"
    " sha256 varchar, hosted_pdf_url varchar, official_url varchar,"
    " xml_path varchar, retrieved_at varchar,"
    " formula varchar, inputs varchar, query_body varchar, recorded_value varchar,"
    " pe_bli varchar, scenario varchar, amount_type varchar"
)

_PIID = "N6833517C0392"
_PE = "0605502N"
_NUMBER = "000000821"
_KEY = "CONT_AWD_N6833517C0392_9700_-NONE-_-NONE-"
_PRIME_URL = f"https://www.usaspending.gov/award/{_KEY}/"
_SUBAWARDEE = "INTERNATIONAL COMPUTER SCIENCE INSTITUTE"
_BASIS = "subaward-description-exact"
_FORMULA = (
    f"crosswalk link: pe_bli={_PE} matched to award PIID {_PIID}"
    " via method='subaward+lexicon', confidence='medium'"
    " (dollars live at award grain in fct_award_transactions)"
)
_SUB_FID = fact_id_derived("budget_to_awards", f"{_PE}|{_PIID}", "link")
_ANN_FID = fact_id_derived("budget_to_awards", "0601101E|HR001124C0001", "link")
_ACC_FID = fact_id_derived("budget_to_awards", "0602303E|W911NF24C0002", "link")

_ARTICLE_URL = "https://www.defense.gov/News/Contracts/Contract/Article/1006508/"
_LINK_SOURCES = {
    ("HR001124C0001", "0601101E"): {
        "source_id": "1006508", "source_url": _ARTICLE_URL,
        "archive_url": None, "sha256": None, "match_basis": "exact-name",
    },
}
_SUB_SOURCES = {(_PIID, _PE): {"source_id": _NUMBER, "match_basis": _BASIS}}
_SUB_LAKE = {
    (_PIID, _NUMBER): {
        "subawardee": _SUBAWARDEE, "permalink": _PRIME_URL,
        "prime_award_unique_key": _KEY,
    },
}


def _make_b2a_duckdb(tmp_path: Path) -> Path:
    db_path = tmp_path / "govbudget.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        "CREATE TABLE fct_budget_to_awards ("
        "  pe_bli varchar, exhibit varchar, fiscal_year integer,"
        "  organization varchar, award_piid varchar, recipient_name varchar,"
        "  recipient_uei varchar, method varchar, confidence varchar,"
        "  program_title varchar"
        ")"
    )
    con.execute(
        "INSERT INTO fct_budget_to_awards VALUES "
        "('0601101E', 'R-2', 2026, 'DARPA', 'HR001124C0001', 'ACME CORP',"
        " 'UEI1', 'announcement+lexicon', 'high', 'Defense Research Sciences'),"
        f"('{_PE}', 'R-2', 2026, 'Navy', '{_PIID}', 'BETA LLC',"
        " 'UEI2', 'subaward+lexicon', 'medium', 'STTR'),"
        "('0602303E', 'R-2', 2026, 'Army', 'W911NF24C0002', 'GAMMA INC',"
        " 'UEI3', 'account+tokens', 'high', 'Army Research')"
    )
    con.close()
    return db_path


def _build(tmp_path: Path, **overrides):
    kw = dict(link_sources=_LINK_SOURCES, subaward_sources=_SUB_SOURCES,
              subaward_lake=_SUB_LAKE)
    kw.update(overrides)
    return _build_budget_to_awards_citation_rows(
        duckdb_path=_make_b2a_duckdb(tmp_path), bl_rows=[], **kw)


# ---------------------------------------------------------------------------
# _subaward_row — the 27-column row shape
# ---------------------------------------------------------------------------


def test_subaward_row_shape_and_column_positions():
    row = _subaward_row("abcd1234abcd1234", subaward_number=_NUMBER,
                        subawardee=_SUBAWARDEE, url=_PRIME_URL,
                        match_basis=_BASIS, formula=_FORMULA)
    assert len(row) == 27
    assert row[_CIT_IDX["fact_id"]] == "abcd1234abcd1234"
    assert row[_CIT_IDX["kind"]] == "subaward"
    assert row[_CIT_IDX["official_url"]] == _PRIME_URL
    assert row[_CIT_IDX["formula"]] == _FORMULA
    assert json.loads(row[_CIT_IDX["query_body"]]) == {
        "match_basis": _BASIS,
        "subaward_number": _NUMBER,
        "subawardee": _SUBAWARDEE,
    }
    # The cited fact is the LINK, not a figure: no value, no amount, no hash,
    # no page geometry, no inputs (nothing here is recomputable).
    for col in ("recorded_value", "amount_text", "amount_thousands", "sha256",
                "page_number", "inputs", "units", "retrieved_at"):
        assert row[_CIT_IDX[col]] is None, col


def test_subaward_row_query_body_is_exactly_the_three_keys():
    """No description, no prime key, no dollars — the controller's contract."""
    row = _subaward_row("abcd1234abcd1234", subaward_number=_NUMBER,
                        subawardee=_SUBAWARDEE, url=_PRIME_URL,
                        match_basis=_BASIS)
    assert sorted(json.loads(row[_CIT_IDX["query_body"]])) == [
        "match_basis", "subaward_number", "subawardee"]


def test_subaward_row_keeps_an_absent_subawardee_absent():
    row = _subaward_row("abcd1234abcd1234", subaward_number=_NUMBER,
                        subawardee=None, url=_PRIME_URL, match_basis=_BASIS)
    assert json.loads(row[_CIT_IDX["query_body"]])["subawardee"] is None


# ---------------------------------------------------------------------------
# _build_budget_to_awards_citation_rows — which links flip
# ---------------------------------------------------------------------------


def test_subaward_link_gets_a_subaward_row(tmp_path):
    by_fid = {r[_CIT_IDX["fact_id"]]: r for r in _build(tmp_path)}
    sub = by_fid[_SUB_FID]
    assert sub[_CIT_IDX["kind"]] == "subaward"
    assert sub[_CIT_IDX["official_url"]] == _PRIME_URL
    body = json.loads(sub[_CIT_IDX["query_body"]])
    assert body == {"match_basis": _BASIS, "subaward_number": _NUMBER,
                    "subawardee": _SUBAWARDEE}


def test_subaward_row_carries_the_link_formula_for_gate_leg_n(tmp_path):
    """datatruth leg n reads the published-tier universe from `formula`.

    If the subaward row dropped it the site would count FIVE published
    methods, not six, and /methodology/'s subaward figure would be flagged
    as a withdrawn tier's number.
    """
    sub = next(r for r in _build(tmp_path) if r[_CIT_IDX["fact_id"]] == _SUB_FID)
    formula = sub[_CIT_IDX["formula"]]
    assert "via method='subaward+lexicon', confidence='medium'" in formula
    assert _PE in formula and _PIID in formula


def test_announcement_and_mechanical_links_are_untouched(tmp_path):
    by_fid = {r[_CIT_IDX["fact_id"]]: r for r in _build(tmp_path)}
    assert by_fid[_ANN_FID][_CIT_IDX["kind"]] == "announcement"
    assert by_fid[_ACC_FID][_CIT_IDX["kind"]] == "derived"
    assert by_fid[_ACC_FID][_CIT_IDX["recorded_value"]] == "high"


def test_fact_ids_are_the_derived_ids_the_program_pages_already_reference(tmp_path):
    """Gate 2's Cite-state contract: set equality against fact_id_derived."""
    rows = _build(tmp_path)
    assert {r[_CIT_IDX["fact_id"]] for r in rows} == {_ANN_FID, _SUB_FID, _ACC_FID}
    sub = next(r for r in rows if r[_CIT_IDX["kind"]] == "subaward")
    assert sub[_CIT_IDX["fact_id"]] == fact_id_derived(
        "budget_to_awards", f"{_PE}|{_PIID}", "link")


def test_subaward_link_without_a_source_row_fails_the_export(tmp_path):
    with pytest.raises(RuntimeError) as exc:
        _build(tmp_path, subaward_sources={})
    msg = str(exc.value)
    assert "1 'subaward+lexicon' link" in msg
    assert "load_announcement_links.py" in msg


def test_subaward_link_with_no_source_map_at_all_fails_the_export(tmp_path):
    with pytest.raises(RuntimeError):
        _build(tmp_path, subaward_sources=None, subaward_lake=None)


def test_subaward_link_whose_record_is_not_in_the_lake_fails_the_export(tmp_path):
    """A source row alone is not a citation: the lake supplies the URL."""
    with pytest.raises(RuntimeError) as exc:
        _build(tmp_path, subaward_lake={})
    msg = str(exc.value)
    assert _NUMBER in msg
    assert "sync-subawards" in msg


def test_lake_row_without_any_url_fails_the_export(tmp_path):
    """No permalink and no prime key → nothing honest to cite."""
    with pytest.raises(RuntimeError):
        _build(tmp_path, subaward_lake={(_PIID, _NUMBER): {
            "subawardee": _SUBAWARDEE, "permalink": None,
            "prime_award_unique_key": None}})


def test_a_mart_with_no_subaward_links_needs_no_subaward_sources(tmp_path):
    db_path = tmp_path / "no_sub.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        "CREATE TABLE fct_budget_to_awards ("
        "  pe_bli varchar, exhibit varchar, fiscal_year integer,"
        "  organization varchar, award_piid varchar, recipient_name varchar,"
        "  recipient_uei varchar, method varchar, confidence varchar,"
        "  program_title varchar)"
    )
    con.execute(
        "INSERT INTO fct_budget_to_awards VALUES "
        "('0602303E', 'R-2', 2026, 'Army', 'W911NF24C0002', 'GAMMA INC',"
        " 'UEI3', 'account+tokens', 'high', 'Army Research')"
    )
    con.close()
    rows = _build_budget_to_awards_citation_rows(
        duckdb_path=db_path, bl_rows=[], link_sources={})
    assert [r[_CIT_IDX["kind"]] for r in rows] == ["derived"]


# ---------------------------------------------------------------------------
# _index_subaward_sources — the loader's indexing step (no Postgres needed)
# ---------------------------------------------------------------------------


def test_index_subaward_sources_keys_by_piid_and_pe():
    out = _index_subaward_sources([(_PIID, _PE, _NUMBER, _BASIS)])
    assert out == {(_PIID, _PE): {"source_id": _NUMBER, "match_basis": _BASIS}}


def test_subaward_lake_keys_strip_the_number_the_other_two_uses_strip(tmp_path):
    """A padded source_id must not become a bogus 'not in the lake' failure.

    The missing-row check and the mint branch both look the record up under
    str(source_id).strip(). The §4d3 call site must FETCH under that same key,
    or a padded source_id in Postgres would pull the lake under the padded key,
    find nothing, and fail the export for a record the lake really holds.
    """
    padded_sources = {
        (_PIID, _PE): {"source_id": f"  {_NUMBER}\t", "match_basis": _BASIS},
    }
    assert _subaward_lake_keys(padded_sources) == {(_PIID, _NUMBER)}

    # …and the key the builder then uses is the same one, so the row mints
    # (the lake fixture is keyed by the stripped number) with a clean number.
    sub = next(r for r in _build(tmp_path, subaward_sources=padded_sources)
               if r[_CIT_IDX["fact_id"]] == _SUB_FID)
    assert json.loads(sub[_CIT_IDX["query_body"]])["subaward_number"] == _NUMBER


def test_index_subaward_sources_raises_on_two_records_for_one_link():
    """A kind='subaward' citation names ONE record; never a silent pick."""
    with pytest.raises(RuntimeError) as exc:
        _index_subaward_sources([(_PIID, _PE, _NUMBER, _BASIS),
                                 (_PIID, _PE, "999999999", _BASIS)])
    assert _NUMBER in str(exc.value) and "999999999" in str(exc.value)


# ---------------------------------------------------------------------------
# _load_subaward_lake_rows — reading data/parquet/subawards
# ---------------------------------------------------------------------------

_LAKE_COLS = (
    "prime_award_unique_key varchar, subaward_number varchar,"
    " subawardee_name varchar, subaward_description varchar,"
    " usaspending_permalink varchar, subaward_action_date varchar,"
    " subaward_sam_report_last_modified_date varchar"
)


def _write_lake(tmp_path: Path) -> Path:
    """A two-file lake in the live layout: {root}/duckdb/x.duckdb next to
    {root}/parquet/subawards/fy=YYYY/part_000.parquet.

    The fy=2023 file is ASSISTANCE-shaped (prime_award_fain, no
    prime_award_piid column) — the real lake's part_001 files are — so a read
    that projects prime_award_piid without union_by_name fails on it. It sorts
    FIRST in the glob, so the failure cannot hide behind file order.
    """
    lake = tmp_path / "parquet" / "subawards"
    (lake / "fy=2024").mkdir(parents=True)
    (lake / "fy=2023").mkdir(parents=True)
    con = duckdb.connect()
    con.execute(f"create table c (prime_award_piid varchar, {_LAKE_COLS})")
    con.execute(
        "insert into c values "
        f"('{_PIID}', '{_KEY}', '{_NUMBER}', 'OLD NAME', 'old desc', '{_PRIME_URL}',"
        " '2019-02-01', '2019-03-01'),"
        f"('{_PIID}', '{_KEY}', '{_NUMBER}', '{_SUBAWARDEE}', 'new desc',"
        f" '{_PRIME_URL}', '2020-06-15', '2020-07-01'),"
        f"('{_PIID}', '{_KEY}', 'OTHER-SUB', 'SOMEONE ELSE', 'x', '{_PRIME_URL}',"
        " '2020-06-15', '2020-07-01'),"
        "('W900KK20C0001', 'CONT_AWD_W900KK20C0001_9700_-NONE-_-NONE-', 'NOURL',"
        " 'BLANK PERMALINK CO', 'y', '', '2021-01-01', '2021-02-01')"
    )
    p = str(lake / "fy=2024" / "part_000.parquet").replace("'", "''")
    con.execute(f"copy c to '{p}' (format parquet)")
    con.execute(f"create table a (prime_award_fain varchar, {_LAKE_COLS})")
    con.execute(
        "insert into a values ('FAIN1', 'ASST_NON_FAIN1_9700', 'G-1', 'GRANTEE',"
        " 'z', 'https://www.usaspending.gov/award/ASST_NON_FAIN1_9700/',"
        " '2022-01-01', '2022-02-01')"
    )
    p = str(lake / "fy=2023" / "part_000.parquet").replace("'", "''")
    con.execute(f"copy a to '{p}' (format parquet)")
    con.close()
    (tmp_path / "duckdb").mkdir()
    return tmp_path / "duckdb" / "govbudget.duckdb"


def test_lake_parquet_dir_resolves_the_live_layout(tmp_path):
    db = _write_lake(tmp_path)
    assert _lake_parquet_dir(db, "subawards") == tmp_path / "parquet" / "subawards"
    assert _lake_parquet_dir(db, "nope") is None


def test_load_subaward_lake_rows_reads_a_mixed_schema_lake_by_name(tmp_path):
    db = _write_lake(tmp_path)
    out = _load_subaward_lake_rows(db, {(_PIID, _NUMBER)})
    assert out == {(_PIID, _NUMBER): {
        "subawardee": _SUBAWARDEE,          # the LATEST report wins
        "permalink": _PRIME_URL,
        "prime_award_unique_key": _KEY,
    }}


def test_load_subaward_lake_rows_builds_the_prime_url_from_the_key_when_blank(tmp_path):
    db = _write_lake(tmp_path)
    out = _load_subaward_lake_rows(db, {("W900KK20C0001", "NOURL")})
    assert out[("W900KK20C0001", "NOURL")]["permalink"] == (
        "https://www.usaspending.gov/award/CONT_AWD_W900KK20C0001_9700_-NONE-_-NONE-/")


def test_load_subaward_lake_rows_returns_only_requested_keys(tmp_path):
    db = _write_lake(tmp_path)
    assert _load_subaward_lake_rows(db, {(_PIID, "NOT-THERE")}) == {}
    assert _load_subaward_lake_rows(db, set()) == {}


def test_load_subaward_lake_rows_without_a_lake_is_empty_not_an_error(tmp_path):
    (tmp_path / "duckdb").mkdir()
    assert _load_subaward_lake_rows(
        tmp_path / "duckdb" / "x.duckdb", {(_PIID, _NUMBER)}) == {}


# ---------------------------------------------------------------------------
# verify_phase5b1 — the new kind must be verifiable, not "unknown"
# ---------------------------------------------------------------------------


def _good_row(**over) -> tuple:
    kw = dict(subaward_number=_NUMBER, subawardee=_SUBAWARDEE, url=_PRIME_URL,
              match_basis=_BASIS, formula=_FORMULA)
    kw.update(over)
    return _subaward_row("abcd1234abcd1234", **kw)


def test_verify_subaward_accepts_a_well_formed_row():
    assert _verify_subaward(_good_row(), _CIT_IDX) is None


def test_verify_subaward_accepts_a_null_subawardee():
    """Absence is honest; the card says 'not recorded'."""
    assert _verify_subaward(_good_row(subawardee=None), _CIT_IDX) is None


@pytest.mark.parametrize("bad_url", [
    "https://evil.example.com/?ref=usaspending.gov/award/X/",
    "https://www.usaspending.gov/search/?hash=abc",
    "https://www.usaspending.gov/award/CONT_AWD_X_9700/extra",
    "http://www.usaspending.gov/award/CONT_AWD_X_9700/",
    "https://usaspending.gov/award/CONT_AWD_X_9700/",
    "https://www.usaspending.gov/award/cont_awd_x_9700/",
    "https://www.usaspending.gov/award//",
])
def test_verify_subaward_rejects_urls_a_substring_check_would_accept(bad_url):
    """Proof-it-can-fail: the anchored pattern, not `'usaspending.gov' in url`."""
    reason = _verify_subaward(_good_row(url=bad_url), _CIT_IDX)
    assert reason is not None and "official_url" in reason


def test_verify_subaward_fails_without_a_subaward_number():
    row = list(_good_row())
    row[_CIT_IDX["query_body"]] = json.dumps(
        {"match_basis": _BASIS, "subaward_number": "", "subawardee": _SUBAWARDEE})
    reason = _verify_subaward(tuple(row), _CIT_IDX)
    assert reason is not None and "subaward_number" in reason


def test_verify_subaward_fails_on_a_basis_the_loader_never_emits():
    reason = _verify_subaward(_good_row(match_basis="llm-description"), _CIT_IDX)
    assert reason is not None and "match_basis" in reason
    reason = _verify_subaward(_good_row(match_basis=None), _CIT_IDX)
    assert reason is not None and "match_basis" in reason


def test_verify_subaward_fails_when_the_formula_drops_the_method():
    """Leg n's universe is read from this token; losing it is a site failure."""
    reason = _verify_subaward(_good_row(formula=None), _CIT_IDX)
    assert reason is not None and "formula" in reason
    reason = _verify_subaward(
        _good_row(formula="crosswalk link: something else entirely"), _CIT_IDX)
    assert reason is not None and "subaward+lexicon" in reason


def test_verify_subaward_fails_on_malformed_or_non_object_bodies():
    for body in (None, "", "{not json", "[]", "42"):
        row = list(_good_row())
        row[_CIT_IDX["query_body"]] = body
        assert _verify_subaward(tuple(row), _CIT_IDX) is not None, body


@pytest.mark.parametrize("col,value", [
    ("recorded_value", "medium"), ("sha256", "ab" * 32),
    ("amount_text", "$1"), ("amount_thousands", 1.0),
])
def test_verify_subaward_fails_when_a_figure_field_is_populated(col, value):
    """Docstring rule and code agree (the #87 lesson): every figure field."""
    row = list(_good_row())
    row[_CIT_IDX[col]] = value
    reason = _verify_subaward(tuple(row), _CIT_IDX)
    assert reason is not None and col in reason


def _write_parquet(path: Path, col_defs: str, rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.execute(f"create table _t ({col_defs})")
        placeholders = ", ".join("?" for _ in rows[0])
        con.executemany(f"insert into _t values ({placeholders})", rows)
        con.execute(
            f"copy _t to '{str(path).replace(chr(39), chr(39) * 2)}'"
            " (format parquet, compression zstd)")
    finally:
        con.close()


def _write_site(tmp_path: Path, rows: list[tuple]) -> Path:
    """citations.parquet + manifest.json — all gate 1 and the distinctness
    check need (re-proved 2026-09-10 with an announcement analog: gate 1
    sampled the rows, integrity flagged the duplicate fact_id)."""
    site = tmp_path / "site"
    _write_parquet(site / "citations" / "citations.parquet", _CIT_COL_DEFS, rows)
    (site / "manifest.json").write_text(json.dumps({
        "built_at": "2026-09-10T00:00:00+00:00", "datasets": {},
        "citations": {"subaward": len(rows)}, "skipped_unresolved": 0,
        "skipped_zero_amount": 0, "uncited_datasets": [],
        "pdf_base_url": "/pdfs", "schema_version": 1}))
    return site


def test_citation_gate_dispatches_the_subaward_kind(tmp_path):
    """Gate 1 must verify the kind, not report 'unknown citation kind'."""
    result = citation_gate5b1(_write_site(tmp_path, [_good_row()]))
    assert result["ok"] is True, result["failures"]
    assert result["sampled"] == 1


def test_citation_gate_fails_a_subaward_row_with_a_bad_url(tmp_path):
    """Proof-it-can-fail through the dispatcher, not only the leg function."""
    result = citation_gate5b1(_write_site(
        tmp_path, [_good_row(url="https://www.usaspending.gov/search/?hash=x")]))
    assert result["ok"] is False
    assert any(reason.startswith("subaward: official_url")
               for _fid, reason in result["failures"]), result["failures"]
    assert not any("unknown citation kind" in reason
                   for _fid, reason in result["failures"])


def test_integrity_gate_distinctness_covers_the_subaward_kind(tmp_path):
    """Proof-it-can-fail: a duplicated subaward fact_id trips the gate."""
    result = integrity_gate5b1(_write_site(tmp_path, [_good_row(), _good_row()]))
    assert result["checks"].get("citation_distinctness") is False
    assert any("kind='subaward'" in f and "citation_distinctness" in f
               for f in result["failures"]), result["failures"]
