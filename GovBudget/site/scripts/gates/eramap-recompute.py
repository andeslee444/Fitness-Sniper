#!/usr/bin/env python3
"""eramap-recompute.py — gate 24 leg (s) truth helper (families piece 1).

Recounts, from data/site/data/p1_era_line_map.parquet itself (never from
era_map_summary.json, the artifact under test), each era edition's line count
and, per decision, its chains (distinct decision_id) and lines.

Output (stdout, JSON):
  {"present": true, "editions": {"2017": {"lines": 969,
     "by_decision": {"same_program": {"chains": 690, "lines": 701}, ...}}, ...}}
  {"present": false} when the parquet is not shipped.
"""

import json
import sys
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[3]
PARQUET = REPO / "data" / "site" / "data" / "p1_era_line_map.parquet"


def main() -> int:
    if not PARQUET.is_file():
        print(json.dumps({"present": False}))
        return 0
    con = duckdb.connect()
    try:
        rows = con.execute(
            "select edition, decision, count(*), count(distinct decision_id)"
            " from read_parquet(?) group by edition, decision"
            " order by edition, decision",
            [PARQUET.as_posix()],
        ).fetchall()
    finally:
        con.close()
    editions: dict[str, dict] = {}
    for edition, decision, lines, chains in rows:
        e = editions.setdefault(str(edition), {"lines": 0, "by_decision": {}})
        e["lines"] += int(lines)
        e["by_decision"][decision] = {"chains": int(chains), "lines": int(lines)}
    print(json.dumps({"present": True, "editions": editions}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
