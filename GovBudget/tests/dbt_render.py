"""Render a committed dbt model or singular test to plain DuckDB SQL.

Unit tests run the rendered SQL against a throwaway in-memory DuckDB (the
pattern tests/test_dbt_lobbyists_tiebreak.py uses for one model, made
reusable): `{{ config(...) }}` is dropped, `{{ ref('x') }}` becomes the
relation `x`, and `{{ source('a', 'b') }}` becomes `a__b` (or the name the
caller maps it to). Anything else left in braces fails loudly instead of
reaching DuckDB.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_CONFIG = re.compile(r"\{\{\s*config\([^}]*\)\s*\}\}")
_REF = re.compile(r"\{\{\s*ref\('([a-z0-9_]+)'\)\s*\}\}")
_SOURCE = re.compile(r"\{\{\s*source\('([a-z0-9_]+)',\s*'([a-z0-9_]+)'\)\s*\}\}")


def render_dbt_sql(rel_path: str, sources: dict[str, str] | None = None) -> str:
    """SQL of ROOT/rel_path with its dbt Jinja replaced by plain relation names."""
    sources = sources or {}
    sql = (ROOT / rel_path).read_text()
    sql = _CONFIG.sub("", sql)
    sql = _REF.sub(lambda m: m.group(1), sql)
    sql = _SOURCE.sub(
        lambda m: sources.get(f"{m.group(1)}.{m.group(2)}", f"{m.group(1)}__{m.group(2)}"),
        sql,
    )
    assert "{{" not in sql and "{%" not in sql, f"unrendered Jinja left in {rel_path}"
    return sql
