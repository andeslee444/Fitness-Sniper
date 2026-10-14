"""site/scripts/gates/yearsmatrix-recompute.py — the era join gate 20 leg g
reads (ROADMAP #193, families piece-1 follow-ups design §3.6).

Since the /years/ era fence lifted, a PB2017–PB2023 procurement cell's lake
rows carry an era key ('0300D-DCSA-L5'), not the row's code. The helper hands
the gate, per decade fact, the p1_era_line_map row of every era-keyed lake row
(by edition = fiscal_year and era_key = pe_bli), so the gate can prove the
cell reaches its program only through a reviewed same_program decision. Run
against a fixture data directory, never data/site.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

HELPER = (
    Path(__file__).resolve().parents[1]
    / "site" / "scripts" / "gates" / "yearsmatrix-recompute.py"
)


def _fixture(data_dir: Path) -> None:
    con = duckdb.connect()
    d = str(data_dir).replace("'", "''")
    con.execute(
        "copy (select 'p' as pe_bli, 'A' as organization, 'fy_2024_actuals' as"
        " amount_type, 'Line' as title, 1.0 as amount_thousands)"
        f" to '{d}/budget_lines.parquet' (format parquet)"
    )
    con.execute(
        "copy (select 'p' as pe_bli, 'P1' as project_number, 'PriorYear' as"
        f" scenario, 1.0 as amount_millions) to '{d}/jbook_details.parquet'"
        " (format parquet)"
    )
    con.execute(
        "copy (select * from (values"
        " ('aaaa000000000001', 2019, '0300D-DCSA-L5', 1057.0, 'sha_p1_19'),"
        " ('aaaa000000000002', 2019, '0300D-DCAA-L1', 25.0, 'sha_p1_19'),"
        " ('aaaa000000000003', 2026, '20', 2135.0, 'sha_p1_26'),"
        " ('aaaa000000000004', 2018, '0300D-DCSA-L5', 1000.0, 'sha_p1_18')"
        ") t(fact_id, fiscal_year, pe_bli, amount_thousands, document_sha256))"
        f" to '{d}/budget_lines_decade.parquet' (format parquet)"
    )
    con.execute(
        "copy (select * from (values"
        " (2019, '0300D-DCSA-L5', '20', 'same_program', '0300D', 'DCSA'),"
        " (2019, '0300D-DCAA-L1', '20', 'history_only', '0300D', 'DCAA')"
        ") t(edition, era_key, program_key, decision, program_account, program_org))"
        f" to '{d}/p1_era_line_map.parquet' (format parquet)"
    )
    con.close()


def _run(tmp_path: Path, fids: list[str]) -> dict:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _fixture(data_dir)
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"decade_fids": fids}))
    res = subprocess.run(
        [sys.executable, str(HELPER), str(request), str(data_dir)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(res.stdout)["decade"]


def test_an_era_row_carries_its_map_row(tmp_path):
    out = _run(tmp_path, ["aaaa000000000001", "aaaa000000000002"])
    assert out["aaaa000000000001"] == {
        "v": 1057.0, "n": 1, "fys": [2019], "pes": ["0300D-DCSA-L5"],
        "shas": ["sha_p1_19"],
        "era": [{
            "era_key": "0300D-DCSA-L5", "program_key": "20",
            "decision": "same_program", "program_account": "0300D",
            "program_org": "DCSA",
        }],
    }
    assert out["aaaa000000000002"]["era"][0]["decision"] == "history_only"


def test_a_native_row_carries_no_era_entry(tmp_path):
    out = _run(tmp_path, ["aaaa000000000003"])
    assert out["aaaa000000000003"]["pes"] == ["20"]
    assert out["aaaa000000000003"]["era"] == []


def test_an_era_row_the_map_does_not_name_is_listed_with_nulls(tmp_path):
    """The map has no PB2018 row for the key: the gate must see that, not
    an empty list it would read as a native row."""
    out = _run(tmp_path, ["aaaa000000000004"])
    assert out["aaaa000000000004"]["era"] == [{
        "era_key": "0300D-DCSA-L5", "program_key": None, "decision": None,
        "program_account": None, "program_org": None,
    }]


def test_an_unknown_fact_is_null(tmp_path):
    assert _run(tmp_path, ["ffff000000000000"]) == {"ffff000000000000": None}
