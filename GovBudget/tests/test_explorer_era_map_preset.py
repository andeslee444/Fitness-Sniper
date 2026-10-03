"""The /data/ Explorer's p1_era_line_map presets, run for real (families piece 1, Task 19).

The SQL lives in site/src/components/explorer.tsx and runs in the reader's
browser on DuckDB-WASM. This lifts it out of the component and runs it with
DuckDB on a fixture parquet shaped like the shipped map (spec §4.4 columns),
so it needs no export. The shape is pinned in
site/src/__tests__/explorer-era-map-preset.test.ts.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPLORER = ROOT / "site" / "src" / "components" / "explorer.tsx"
CASE = 'case "p1_era_line_map":'
MAP_DDL = (
    "create table m ("
    " edition integer, account varchar, organization varchar,"
    " budget_activity varchar, era_key varchar, line_item_code varchar,"
    " filed_title varchar, program_key varchar, program_account varchar,"
    " program_org varchar, decision varchar, decision_id varchar,"
    " ruling varchar, keys_sha_ok boolean, successor_code varchar,"
    " source_document_sha256 varchar, source_cells varchar)"
)
ROWS = [
    (2017, "3010F", "AF", "01", "3010F-AF-L1", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2021", "R-DEC-ERA-SAME", True, None, "sha17", "J8"),
    (2017, "3010F", "AF", "01", "3010F-AF-L2", "ATA000", "F-35 AP", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2021", "R-DEC-ERA-SAME", True, None, "sha17", "J9"),
    (2017, "1611N", "N", "02", "1611N-N-L4", "1045", "OHIO REPLACEMENT", "1045", "1611N", None,
     "same_program", "1045|1611N||2017-2020", "R-DEC-ERA-B1", True, None, "sha17", "J30"),
    (2018, "1611N", "N", "02", "1611N-N-L4", "1045", "OHIO REPLACEMENT", "1045", "1611N", None,
     "same_program", "1045|1611N||2017-2020", "R-DEC-ERA-B1", True, None, "sha18", "J31"),
    (2018, "0300D", "OSD", "01", "0300D-OSD-L50", "50", "INDIAN FINANCING ACT", None, None, None,
     "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B2", True, None, "sha18", "J60"),
]


def _presets() -> dict[str, str]:
    src = EXPLORER.read_text(encoding="utf-8")
    start = src.index(CASE)
    block = src[start:src.index("case ", start + len(CASE))]
    return {m.group(1): m.group(2).strip()
            for m in re.finditer(r'label: "([^"]+)",\s*sql: t\(`(.*?)`\)', block, re.S)}


@pytest.fixture()
def run(tmp_path):
    pq = tmp_path / "p1_era_line_map.parquet"
    con = duckdb.connect()
    con.execute(MAP_DDL)
    con.executemany("insert into m values (" + ",".join("?" * 17) + ")", ROWS)
    con.execute(f"copy m to '{pq.as_posix()}' (format parquet)")

    def _run(label: str):
        # The browser registers each dataset under its file name; here the
        # quoted name resolves against the fixture file instead.
        sql = _presets()[label].replace("'p1_era_line_map.parquet'", f"'{pq.as_posix()}'")
        cur = con.execute(sql)
        return [d[0] for d in cur.description], cur.fetchall()

    yield _run
    con.close()


def test_the_two_presets_exist_in_order():
    assert list(_presets()) == ["Decisions by edition", "Lines decided in owner review batches"]


def test_decisions_by_edition_counts_chains_and_lines(run):
    cols, rows = run("Decisions by edition")
    assert cols == ["edition", "decision", "chains", "lines"]
    assert rows == [
        (2017, "same_program", 2, 3),
        (2018, "exclude_reused_code", 1, 1),
        (2018, "same_program", 1, 1),
    ]


def test_owner_batches_list_only_batch_rulings(run):
    cols, rows = run("Lines decided in owner review batches")
    assert cols == ["edition", "era_key", "line_item_code", "filed_title", "program_key", "decision", "ruling"]
    assert [(r[0], r[1], r[6]) for r in rows] == [
        (2017, "1611N-N-L4", "R-DEC-ERA-B1"),
        (2018, "1611N-N-L4", "R-DEC-ERA-B1"),
        (2018, "0300D-OSD-L50", "R-DEC-ERA-B2"),
    ]
