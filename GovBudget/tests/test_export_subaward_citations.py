"""Subaward identities must come from the exact raw record, without attributed money."""
import json

import duckdb
import pytest

from govbudget.export_site import (
    _build_budget_to_awards_citation_rows, _enrich_subaward_link_sources,
    _subaward_row, fact_id_derived,
)

PIID = "N0017818F3011"
KEY = f"CONT_AWD_{PIID}_9700_N0017814D7650_9700"
SOURCES = {(PIID, "0204571N"): {"source_kind": "subaward", "source_id": "10977 REL 1", "match_basis": "subaward-description-exact"}}


def lake(tmp_path, rows):
    path = tmp_path / "subawards.parquet"
    with duckdb.connect() as con:
        con.execute("create table subs (prime_award_piid varchar, subaward_number varchar, prime_award_unique_key varchar, subawardee_name varchar, subaward_description varchar)")
        con.executemany("insert into subs values (?, ?, ?, ?, ?)", rows)
        con.execute("copy subs to ? (format parquet)", [str(path)])
    return str(path)


def test_enrichment_requires_both_prime_and_subaward_identity(tmp_path):
    path = lake(tmp_path, [
        (PIID, "10977 REL 1", KEY, "VT MILCOM INC.", "Matching source description"),
        ("WRONG", "10977 REL 1", "CONT_AWD_WRONG_9700", "Wrong recipient", "Another source"),
        (PIID, "OTHER", KEY, "Wrong subaward", "Another source"),
    ])
    result = _enrich_subaward_link_sources(SOURCES, path)
    assert result[(PIID, "0204571N")]["source_url"] == f"https://www.usaspending.gov/award/{KEY}/"
    assert result[(PIID, "0204571N")]["subawardee"] == "VT MILCOM INC."
    assert "source_url" not in SOURCES[(PIID, "0204571N")]


@pytest.mark.parametrize("rows", [
    [(PIID, "OTHER", KEY, "VT MILCOM INC.", "Description")],
    [(PIID, "10977 REL 1", KEY, "VT MILCOM INC.", "")],
    [(PIID, "10977 REL 1", KEY, "", "Description")],
    [(PIID, "10977 REL 1", "CONT_AWD_WRONG_9700", "VT MILCOM INC.", "Description")],
    [(PIID, "10977 REL 1", KEY, "Recipient A", "Description"), (PIID, "10977 REL 1", KEY, "Recipient B", "Description")],
])
def test_missing_or_ambiguous_raw_evidence_blocks_export(tmp_path, rows):
    with pytest.raises(RuntimeError, match="Subaward evidence"):
        _enrich_subaward_link_sources(SOURCES, lake(tmp_path, rows))


def test_subaward_row_has_stable_link_id_and_no_amount():
    fid = fact_id_derived("budget_to_awards", f"0204571N|{PIID}", "link")
    row = _subaward_row(fid, number="10977 REL 1", recipient="VT MILCOM INC.", url=f"https://www.usaspending.gov/award/{KEY}/", formula="recorded link method")
    assert len(row) == 27
    assert row[0] == fid and row[1] == "subaward"
    assert row[2] is None and row[3] is None and row[14] is None and row[23] is None
    assert json.loads(row[22]) == {"match_basis": "subaward-description-exact", "subaward_number": "10977 REL 1", "subawardee": "VT MILCOM INC."}


def test_missing_subaward_source_never_falls_back_to_generic_derived_evidence(tmp_path):
    db = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("create table fct_budget_to_awards as select '0204571N' as pe_bli, 'N0017818F3011' as award_piid, 'Navy' as organization, 'subaward+lexicon' as method, 'medium' as confidence, NULL as account")
    with pytest.raises(RuntimeError, match="lacks verified medium-confidence source identity"):
        _build_budget_to_awards_citation_rows(duckdb_path=db, bl_rows=[], link_sources={})
