"""json/era_map_summary.json (families piece 1, spec 2026-10-02 §4.4, §6.4,
V7; Task 19): the era map counted per edition by decision, by ruling, and the
receipt completeness of each edition's cited P-1 cells, read from the receipts
audit of the SAME citations.json."""
from __future__ import annotations

import hashlib
import json

import duckdb
import pytest

from govbudget.export_site import write_era_map_summary

MAP_COLUMNS = "edition integer, era_key varchar, decision varchar, decision_id varchar, ruling varchar"
MAP_ROWS = [
    (2018, "3010F-AF-L2", "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME"),
    (2017, "3010F-AF-L1", "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME"),
    (2017, "3010F-AF-L9", "history_only", "F0150P|3010F||2017-2017", "R-DEC-ERA-HISTORY"),
    (2017, "0300D-OSD-L50", "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B1"),
    (2017, "2035A-A-L3", "exclude_placeholder", "FY2017CR|2035A||2017-2017", "R-DEC-ERA-EXCLUDE"),
]
CITATIONS = b'{"x": 1}'


def _site(tmp_path, *, rows=MAP_ROWS, full_corpus=True, citation_sha=None):
    site = tmp_path / "site"
    (site / "data").mkdir(parents=True)
    (site / "json").mkdir()
    con = duckdb.connect()
    con.execute(f"create table m ({MAP_COLUMNS})")
    con.executemany("insert into m values (?,?,?,?,?)", rows)
    con.execute(f"copy m to '{site / 'data' / 'p1_era_line_map.parquet'}' (format parquet)")
    con.close()
    (site / "json" / "citations.json").write_bytes(CITATIONS)
    (site / "json" / "budget_pdf_receipts_audit.json").write_text(json.dumps({
        "full_corpus": full_corpus,
        "citation_sha256": citation_sha or hashlib.sha256(CITATIONS).hexdigest(),
        "books": [
            {"edition": 2017, "exhibit": "P-1", "pages": 9, "facts": 6, "complete": 5},
            {"edition": 2017, "exhibit": "R-1", "pages": 9, "facts": 100, "complete": 100},
        ],
    }))
    db = tmp_path / "wh.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table fct_decade_series (pe_bli varchar, fy integer, edition_year integer,"
                " amount_type_kind varchar, amount_thousands double)")
    con.executemany("insert into fct_decade_series values (?,?,?,?,?)", [
        ("3010F-AF-L1", 2015, 2017, "actuals", 1000.0),
        ("3010F-AF-L1", 2016, 2017, "enacted", 999.0),
        ("3010F-AF-L2", 2016, 2018, "actuals", 2000.0),
        ("3010F-AF-L9", 2015, 2017, "actuals", 300.0),
        ("0300D-OSD-L50", 2015, 2017, "actuals", 50.0),
    ])
    con.close()
    return site, db


def _tally(chains, lines, actuals):
    return {"chains": chains, "lines": lines, "actuals_thousands": actuals}


ZERO = _tally(0, 0, 0.0)


def test_counts_every_edition_by_decision_and_ruling(tmp_path):
    site, db = _site(tmp_path)
    summary = write_era_map_summary(site_dir=site, duckdb_path=db)
    assert json.loads((site / "json" / "era_map_summary.json").read_text()) == summary
    assert summary["schema_version"] == 1
    assert [e["edition"] for e in summary["editions"]] == list(range(2017, 2024))
    assert summary["editions"][0] == {
        "edition": 2017, "fy_actuals": 2015, "lines": 4,
        "by_decision": {
            "same_program": _tally(1, 1, 1000.0),
            "history_only": _tally(1, 1, 300.0),
            "exclude_placeholder": _tally(1, 1, 0.0),
            "exclude_route_unsafe": ZERO,
            "exclude_reused_code": _tally(1, 1, 50.0),
        },
        "receipts": {"facts": 6, "complete": 5},
    }
    e2018 = summary["editions"][1]
    assert e2018["lines"] == 1
    assert e2018["by_decision"]["same_program"] == _tally(1, 1, 2000.0)
    assert e2018["receipts"] == {"facts": 0, "complete": 0}
    assert all(e["lines"] == 0 for e in summary["editions"][2:])
    assert summary["by_ruling"] == [
        {"ruling": "R-DEC-ERA-B1", "decision": "exclude_reused_code", **_tally(1, 1, 50.0)},
        {"ruling": "R-DEC-ERA-EXCLUDE", "decision": "exclude_placeholder", **_tally(1, 1, 0.0)},
        {"ruling": "R-DEC-ERA-HISTORY", "decision": "history_only", **_tally(1, 1, 300.0)},
        {"ruling": "R-DEC-ERA-SAME", "decision": "same_program", **_tally(1, 2, 3000.0)},
    ]
    assert summary["totals"]["same_program"] == _tally(1, 2, 3000.0)
    assert summary["totals"]["exclude_route_unsafe"] == ZERO


def test_refuses_a_stale_audit(tmp_path):
    site, db = _site(tmp_path, citation_sha="0" * 64)
    with pytest.raises(ValueError, match="not a full-corpus run"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_refuses_a_partial_audit(tmp_path):
    site, db = _site(tmp_path, full_corpus=False)
    with pytest.raises(ValueError, match="not a full-corpus run"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_refuses_an_undecided_line(tmp_path):
    rows = MAP_ROWS + [(2019, "3010F-AF-L4", "undecided", None, None)]
    site, db = _site(tmp_path, rows=rows)
    with pytest.raises(ValueError, match="never published"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_refuses_an_edition_outside_the_era(tmp_path):
    rows = MAP_ROWS + [(2024, "3010F-AF-L4", "same_program", "X|3010F||2024-2024", "R-DEC-ERA-SAME")]
    site, db = _site(tmp_path, rows=rows)
    with pytest.raises(ValueError, match="outside PB2017–PB2023"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_no_map_writes_nothing_and_removes_a_stale_summary(tmp_path):
    site = tmp_path / "site"
    (site / "json").mkdir(parents=True)
    (site / "json" / "era_map_summary.json").write_text("{}")
    assert write_era_map_summary(site_dir=site, duckdb_path=tmp_path / "absent.duckdb") is None
    assert not (site / "json" / "era_map_summary.json").exists()
