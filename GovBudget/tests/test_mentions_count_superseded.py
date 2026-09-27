"""/methodology/ §2: "Program mentions still count superseded reports." — held true.

Final review finding #5 (2026-09-27). R-DEC-AMEND makes an amendment replace
its original in fct_influence (the yearly lobbying dollars and the filing
counts beside them): that mart sums only ``audit_lda_filings`` rows with
``counted``. fct_program_lobbying — the mention count the same paragraph
opens with, and every company page's "LDA Filing Mentions (N)" — has no such
filter, so a superseded original (or a superseded amendment) still
contributes its mention rows. The page and docs/methodology.md now scope the
amendment sentence to "those yearly figures" and say the mentions still count
superseded reports. This file fails if either side of that changes:

  * the mention mart gains a ``counted`` filter (the sentence would then be
    false — rewrite it), or
  * the dollar mart loses its filter (the scoped sentence would be false).

Measured 2026-09-27 on the chain-G lake: 801 of 12,571 mention rows come from
68 filings with counted = false. Read-only: models are read as text, the lake
is opened ``read_only=True``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "dbt" / "models" / "marts"
LAKE = Path(os.environ.get("GOVBUDGET_DUCKDB", ROOT / "data" / "duckdb" / "govbudget.duckdb"))


def _sql(name: str) -> str:
    text = (MARTS / f"{name}.sql").read_text(encoding="utf-8")
    return "\n".join(line.split("--", 1)[0] for line in text.splitlines())


def test_the_dollar_mart_counts_only_counted_filings():
    sql = _sql("fct_influence")
    assert "audit_lda_filings" in sql
    assert re.search(r"\bwhere\s+counted\b", sql), "fct_influence lost its `where counted`"


def test_the_mention_mart_applies_no_supersession_rule():
    sql = _sql("fct_program_lobbying")
    assert "audit_lda_filings" not in sql
    assert not re.search(r"\bcounted\b", sql), (
        "fct_program_lobbying now filters on `counted` — /methodology/ §2 and "
        "docs/methodology.md say mentions still count superseded reports; rewrite them"
    )


def test_superseded_reports_do_contribute_mentions():
    if not LAKE.exists():
        pytest.skip("no warehouse")
    try:
        con = duckdb.connect(str(LAKE), read_only=True)
    except duckdb.IOException as e:
        pytest.skip(f"warehouse locked: {e}")
    try:
        tables = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
        if not {"fct_program_lobbying", "audit_lda_filings"} <= tables:
            pytest.skip("warehouse lacks the mention or audit mart")
        n = con.execute(
            "select count(*) from fct_program_lobbying p"
            " join audit_lda_filings a using (filing_uuid) where not a.counted"
        ).fetchone()[0]
    finally:
        con.close()
    assert n > 0, "no mention row comes from a superseded report — the sentence is vacuous; drop it"
