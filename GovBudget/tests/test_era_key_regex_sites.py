r"""One spelling of the era-key pattern at every SQL site (ROADMAP #203;
families piece-1 follow-ups design §6.4, Task 9).

dbt's era tests and models, the exporter's runtime parity check and one unit
test each select era P-1 keys with a regex literal. They used the prefix
'^[0-9]{4}[A-Z]-[A-Z]+-L', looser than era_keys._ERA_KEY_RE: it accepts
'0300D-DEFW-L' and '0300D-DEFW-Lx'. Every site now spells the full pattern,
and the full pattern agrees with era_keys.is_era_procurement_key, whose `$`
became `\Z` (a Python `$` also matches before a trailing newline, so
'0300D-DEFW-L1\n' was an era key). The live lake has no such key: the loose
and the full pattern select the same 57,722 stg_budget_lines rows (measured
read-only 2026-10-13).
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from govbudget.jbooks.era_keys import is_era_procurement_key

ROOT = Path(__file__).resolve().parents[1]
FULL_SQL = "'^[0-9]{4}[A-Z]-[A-Z]+-L[0-9][0-9A-Za-z-]*$'"
LOOSE_SQL = "'^[0-9]{4}[A-Z]-[A-Z]+-L'"
SITES = {
    "dbt/models/marts/p1_era_line_map.sql": 2,
    "dbt/models/marts/fct_program_decade_series.sql": 1,
    "dbt/models/marts/fct_book_diff.sql": 1,
    "dbt/tests/assert_p1_era_map_one_code.sql": 1,
    "dbt/tests/assert_book_diff_no_era_procurement.sql": 1,
    "dbt/tests/assert_program_decade_native_equals_line.sql": 1,
    "dbt/tests/assert_p1_era_map_complete.sql": 1,
    "src/govbudget/export_site.py": 1,
    "tests/test_program_decade_series_sql.py": 1,
}
PROBES = [
    "3010F-AF-L1", "0300D-WHS-L46-1", "2031A-ARMY-L102",
    "0300D-DEFW-L1\n", "0300D-DEFW-L", "0300D-DEFW-Lx", "0300D-DEFW-L1 ",
    "X0300D-DEFW-L1", "0300D-defw-L1", "9999999999", "0601101E", "70", "",
]


def test_every_site_spells_the_full_pattern():
    for rel, n in SITES.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert text.count(LOOSE_SQL) == 0, f"{rel}: still spells the prefix-only era-key regex"
        assert text.count(FULL_SQL) == n, f"{rel}: expected {n} full era-key regex(es)"


def test_no_unlisted_site_spells_an_era_key_regex():
    found = set()
    for base in ("dbt/models", "dbt/tests", "src", "tests"):
        for path in (ROOT / base).rglob("*"):
            if path.suffix in (".sql", ".py") and "[0-9]{4}[A-Z]-[A-Z]+-L" in path.read_text(encoding="utf-8"):
                found.add(path.relative_to(ROOT).as_posix())
    assert found == set(SITES) | {"tests/test_era_key_regex_sites.py"}


def test_sql_and_python_agree_on_what_an_era_key_is():
    con = duckdb.connect()
    in_sql = [con.execute(f"select regexp_matches(?, {FULL_SQL})", [p]).fetchone()[0] for p in PROBES]
    assert in_sql == [is_era_procurement_key(p) for p in PROBES]
    assert in_sql == [True, True, True] + [False] * 10
