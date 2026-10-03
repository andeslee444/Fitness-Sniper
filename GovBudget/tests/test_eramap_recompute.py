"""site/scripts/gates/eramap-recompute.py — gate 24 leg (s)'s independent
recount of the shipped p1_era_line_map (families piece 1, Task 19 fix round 2).

The recount and write_era_map_summary count the same map two ways (DuckDB
group-bys there, Python sets here), and leg (s) requires them to agree. These
cases run the script's own queries on a fixture parquet where one printed code
spans several decisions, and check it against the summary on the same map.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import duckdb
import pytest

from govbudget.export_site import write_era_map_summary

SCRIPT = Path(__file__).resolve().parents[1] / "site" / "scripts" / "gates" / "eramap-recompute.py"
COLUMNS = ("edition integer, era_key varchar, line_item_code varchar,"
           " decision varchar, decision_id varchar, ruling varchar")
ROWS = [
    # same_program: three decisions, two printed codes (ATA000 in two accounts)
    (2017, "3010F-AF-L1", "ATA000", "same_program", "ATA000|3010F||2017-2017", "R-DEC-ERA-SAME"),
    (2017, "3020F-AF-L1", "ATA000", "same_program", "ATA000|3020F||2017-2017", "R-DEC-ERA-SAME"),
    (2017, "3010F-AF-L2", "F01500", "same_program", "F01500|3010F||2017-2017", "R-DEC-ERA-SAME"),
    # exclusions: FY2017CR placeholder in two accounts, and code 50 under two
    # exclude kinds -> four decisions, three per-decision codes, two distinct
    (2017, "2035A-A-L3", "FY2017CR", "exclude_placeholder", "FY2017CR|2035A||2017-2017", "R-DEC-ERA-EXCLUDE"),
    (2017, "3010F-AF-L60", "FY2017CR", "exclude_placeholder", "FY2017CR|3010F||2017-2017", "R-DEC-ERA-EXCLUDE"),
    (2017, "0300D-OSD-L50", "50", "exclude_reused_code", "50|0300D||2017-2017", "R-DEC-ERA-B1"),
    (2017, "0100D-DHRA-L50", "50", "exclude_route_unsafe", "50|0100D|DHRA|2017-2017", "R-DEC-ERA-B2"),
    # a NULL decision_id and a NULL code count as neither chain nor code
    (2018, "3010F-AF-L9", None, "history_only", None, "R-DEC-ERA-HISTORY"),
    (2018, "3010F-AF-L2", "F01500", "same_program", "F01500|3010F||2017-2018", "R-DEC-ERA-SAME"),
]


def _load():
    spec = importlib.util.spec_from_file_location("eramap_recompute", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _recount(mod, parquet: Path) -> dict:
    mod.PARQUET = parquet
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert mod.main() == 0
    return json.loads(out.getvalue())


@pytest.fixture()
def site(tmp_path):
    site = tmp_path / "site"
    (site / "data").mkdir(parents=True)
    (site / "json").mkdir()
    con = duckdb.connect()
    con.execute(f"create table m ({COLUMNS})")
    con.executemany("insert into m values (?,?,?,?,?,?)", ROWS)
    con.execute(f"copy m to '{(site / 'data' / 'p1_era_line_map.parquet').as_posix()}' (format parquet)")
    con.close()
    return site


def test_recounts_chains_codes_and_excluded_codes(site):
    got = _recount(_load(), site / "data" / "p1_era_line_map.parquet")
    assert got["present"] is True
    e2017 = got["editions"]["2017"]
    assert e2017["lines"] == 7
    assert e2017["by_decision"]["same_program"] == {"chains": 3, "codes": 2, "lines": 3}
    assert e2017["by_decision"]["exclude_placeholder"] == {"chains": 2, "codes": 1, "lines": 2}
    assert e2017["by_decision"]["exclude_reused_code"] == {"chains": 1, "codes": 1, "lines": 1}
    assert e2017["by_decision"]["exclude_route_unsafe"] == {"chains": 1, "codes": 1, "lines": 1}
    assert e2017["excluded_codes"] == 2
    e2018 = got["editions"]["2018"]
    assert e2018["by_decision"]["history_only"] == {"chains": 0, "codes": 0, "lines": 1}
    assert e2018["excluded_codes"] == 0


def test_reports_an_unshipped_map(tmp_path):
    assert _recount(_load(), tmp_path / "absent.parquet") == {"present": False}


def test_agrees_with_the_summary_on_the_same_map(site, tmp_path):
    """What leg (s1) compares, on a map where chains and codes differ."""
    citations = b"{}"
    (site / "json" / "citations.json").write_bytes(citations)
    (site / "json" / "budget_pdf_receipts_audit.json").write_text(json.dumps({
        "full_corpus": True, "citation_sha256": hashlib.sha256(citations).hexdigest(), "books": []}))
    db = tmp_path / "wh.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table fct_decade_series (pe_bli varchar, fy integer, edition_year integer,"
                " amount_type_kind varchar, amount_thousands double)")
    con.close()
    summary = write_era_map_summary(site_dir=site, duckdb_path=db)
    recount = _recount(_load(), site / "data" / "p1_era_line_map.parquet")
    for e in summary["editions"]:
        r = recount["editions"].get(str(e["edition"]), {"lines": 0, "by_decision": {}, "excluded_codes": 0})
        assert r["lines"] == e["lines"]
        assert r["excluded_codes"] == e["excluded_codes"]
        for d, t in e["by_decision"].items():
            want = r["by_decision"].get(d, {"chains": 0, "codes": 0, "lines": 0})
            assert want == {k: t[k] for k in ("chains", "codes", "lines")}, (e["edition"], d)
