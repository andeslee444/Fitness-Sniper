"""json/era_map_summary.json (families piece 1, spec 2026-10-02 §4.4, §6.4,
V7; Task 19): the era map counted per edition by decision, by ruling, and the
receipt completeness of each edition's cited P-1 cells, read from the receipts
audit of the SAME citations.json."""
from __future__ import annotations

import hashlib
import json

import duckdb
import pytest

from govbudget.export_site import ERA_MAP_EXCLUDED, write_era_map_summary
from govbudget.jbooks.era_map import DECISIONS

MAP_COLUMNS = ("edition integer, era_key varchar, decision varchar, decision_id varchar,"
               " ruling varchar, line_item_code varchar")
MAP_ROWS = [
    (2018, "3010F-AF-L2", "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME", "ATA000"),
    (2017, "3010F-AF-L1", "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME", "ATA000"),
    (2017, "3010F-AF-L9", "history_only", "F0150P|3010F||2017-2017", "R-DEC-ERA-HISTORY", "F0150P"),
    (2017, "0300D-OSD-L50", "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B1", "50"),
    (2017, "2035A-A-L3", "exclude_placeholder", "FY2017CR|2035A||2017-2017", "R-DEC-ERA-EXCLUDE", "FY2017CR"),
]
#: Task 19 fix round 1: one printed code spanning several decisions. The
#: FY2017CR placeholder sits in a second account (its own decision), code 50
#: is also route-unsafe in a second organization, and ATA000 is same_program
#: in a second account. Chains overcount the codes each column covers.
SPANNING_ROWS = [
    (2017, "3010F-AF-L60", "exclude_placeholder", "FY2017CR|3010F||2017-2017", "R-DEC-ERA-EXCLUDE", "FY2017CR"),
    (2017, "0100D-DHRA-L50", "exclude_route_unsafe", "50|0100D|DHRA|2017-2017", "R-DEC-ERA-B2", "50"),
    (2017, "3020F-AF-L1", "same_program", "ATA000|3020F||2017-2017", "R-DEC-ERA-SAME", "ATA000"),
]
CITATIONS = b'{"x": 1}'


def _site(tmp_path, *, rows=MAP_ROWS, full_corpus=True, citation_sha=None):
    site = tmp_path / "site"
    (site / "data").mkdir(parents=True)
    (site / "json").mkdir()
    con = duckdb.connect()
    con.execute(f"create table m ({MAP_COLUMNS})")
    con.executemany("insert into m values (?,?,?,?,?,?)", rows)
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


def _tally(chains, lines, actuals, codes=None):
    return {"chains": chains, "codes": chains if codes is None else codes,
            "lines": lines, "actuals_thousands": actuals}


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
        "excluded_codes": 2,
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
    rows = MAP_ROWS + [(2019, "3010F-AF-L4", "undecided", None, None, "X")]
    site, db = _site(tmp_path, rows=rows)
    with pytest.raises(ValueError, match="never published"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_refuses_an_edition_outside_the_era(tmp_path):
    rows = MAP_ROWS + [(2024, "3010F-AF-L4", "same_program", "X|3010F||2024-2024", "R-DEC-ERA-SAME", "X")]
    site, db = _site(tmp_path, rows=rows)
    with pytest.raises(ValueError, match="outside PB2017–PB2023"):
        write_era_map_summary(site_dir=site, duckdb_path=db)


def test_no_map_writes_nothing_and_removes_a_stale_summary(tmp_path):
    site = tmp_path / "site"
    (site / "json").mkdir(parents=True)
    (site / "json" / "era_map_summary.json").write_text("{}")
    assert write_era_map_summary(site_dir=site, duckdb_path=tmp_path / "absent.duckdb") is None
    assert not (site / "json" / "era_map_summary.json").exists()


def test_counts_codes_not_decisions_when_a_code_spans_several(tmp_path):
    """Task 19 fix round 1: the table's "N codes" cells count printed codes.
    Chains (decisions) stay in the summary; codes are distinct line_item_code
    per decision, `excluded_codes` is distinct across the three exclude
    decisions, and totals count codes across the whole era."""
    site, db = _site(tmp_path, rows=MAP_ROWS + SPANNING_ROWS)
    e2017 = write_era_map_summary(site_dir=site, duckdb_path=db)["editions"][0]
    by = e2017["by_decision"]
    assert by["same_program"] == _tally(2, 2, 1000.0, codes=1)
    assert by["exclude_placeholder"] == _tally(2, 2, 0.0, codes=1)
    assert by["exclude_route_unsafe"] == _tally(1, 1, 0.0, codes=1)
    assert by["exclude_reused_code"] == _tally(1, 1, 50.0, codes=1)
    # four excluded decisions, three per-decision codes, two distinct codes
    assert sum(by[d]["chains"] for d in ERA_MAP_EXCLUDED) == 4
    assert sum(by[d]["codes"] for d in ERA_MAP_EXCLUDED) == 3
    assert e2017["excluded_codes"] == 2
    summary = json.loads((site / "json" / "era_map_summary.json").read_text())
    assert summary["totals"]["same_program"] == _tally(2, 3, 3000.0, codes=1)
    assert {"ruling": "R-DEC-ERA-EXCLUDE", "decision": "exclude_placeholder",
            **_tally(2, 2, 0.0, codes=1)} in summary["by_ruling"]


def test_excluded_decisions_are_decisions():
    assert set(ERA_MAP_EXCLUDED) == {d for d in DECISIONS if d.startswith("exclude_")}


def test_a_null_decision_id_or_code_is_no_chain_and_no_code(tmp_path):
    """Same NULL rule as the gate's recount (count(distinct) skips NULLs), so
    leg (s) compares like with like."""
    rows = MAP_ROWS + [(2019, "3010F-AF-L7", "history_only", None, "R-DEC-ERA-HISTORY", None)]
    site, db = _site(tmp_path, rows=rows)
    e2019 = write_era_map_summary(site_dir=site, duckdb_path=db)["editions"][2]
    assert e2019["lines"] == 1
    assert e2019["by_decision"]["history_only"] == _tally(0, 1, 0.0, codes=0)
