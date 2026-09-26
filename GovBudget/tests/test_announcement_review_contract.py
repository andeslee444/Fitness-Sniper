"""The announcement-review contract, one column list across three layers
(ROADMAP #110, R-DEC-110; decisions-wave suites check, 2026-09-25).

migration 018 creates `announcement_link_reviews`; `jbooks export-facts`
writes every column but the table's own `recorded_at` to
data/parquet/jbooks/announcement_link_reviews.parquet; dbt reads that file as
source `jbook_announcement_link_reviews`. Two lanes edited the three layers
in parallel and the source's column list fell six columns behind the export
(article_source, entry_index, reason, adversarial_lenses_passed, upholds,
record_index) — a warehouse reader of the dbt docs could not learn what half
the file's columns mean. This static check fails the moment one layer adds,
drops or renames a column the others do not.
"""
import re
from pathlib import Path

import yaml

from govbudget.jbooks.export_facts import EXPORTS

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "018_announcement_link_reviews.sql"
SOURCES = ROOT / "dbt" / "models" / "sources.yml"

#: the one column the export leaves out: a run timestamp would make the
#: parquet differ run to run (export_facts.EXPORTS comment)
NOT_EXPORTED = {"recorded_at"}


def _migration_columns() -> list[str]:
    sql = MIGRATION.read_text()
    body = re.search(
        r"create table if not exists announcement_link_reviews \((.*?)\n\);",
        sql, re.S,
    ).group(1)
    cols = []
    for line in body.splitlines():
        m = re.match(r"\s{4}([a-z_]+)\s+(text|integer|boolean|date|timestamptz)\b", line)
        if m:
            cols.append(m.group(1))
    return cols


def _export_columns() -> list[str]:
    sql = EXPORTS["announcement_link_reviews"]
    select = re.search(r"select (.*?) from announcement_link_reviews", sql, re.S).group(1)
    return [c.strip() for c in select.split(",")]


def _source_columns() -> list[str]:
    doc = yaml.safe_load(SOURCES.read_text())
    for src in doc["sources"]:
        for table in src.get("tables", []):
            if table["name"] == "jbook_announcement_link_reviews":
                return [c["name"] for c in table.get("columns", [])]
    raise AssertionError("sources.yml has no jbook_announcement_link_reviews source")


def test_the_migration_parse_sees_every_column():
    cols = _migration_columns()
    assert cols[:4] == ["award_piid", "pe_bli", "exhibit", "fiscal_year"]
    assert "recorded_at" in cols
    assert len(cols) == len(set(cols)) == 18


def test_export_facts_writes_every_migration_column_but_recorded_at_in_order():
    assert _export_columns() == [
        c for c in _migration_columns() if c not in NOT_EXPORTED
    ]


def test_the_dbt_source_documents_exactly_the_exported_columns_in_order():
    assert _source_columns() == _export_columns()
