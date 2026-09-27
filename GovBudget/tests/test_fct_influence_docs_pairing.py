"""The mart's own docs agree with the /data/ note on lobbying additivity.

This is a cross-owner binding, added by the final-fix2 suites pass on
2026-09-26.

R-DEC-LDATOTAL (final-review rulings, 2026-09-27) keeps lobbying income and
expense NON-ADDITIVE. A self-filer's reported expense can include what it paid
the outside firms whose income is also reported, so their sum can double-count.
export_site._DATASET_SCOPES["fct_influence"] is the /data/ and /downloads/
note. It says so and calls lobbying_total_usd "a plain sum" that "can
double-count". Its own test in test_export_site_datasets_manifest.py forbids
"without double-counting".

The warehouse's own docs said the opposite. schema.yml described
lobbying_total_usd as "total lobbying outlay without double-counting";
fct_influence.sql's header said that summing both gives that; and the LDA
ingester's module docstring (influence/lda.py) told a reader to "sum both
fields (never double-count ...)" for a family's yearly outlay. All three sat
beside a model whose SQL is a plain sum. Per-filing exclusivity is true (0 of
5,393 filings report both, measured 2026-09-27). It does not make a
family-year row clean: 147 of the 210 shipped rows carry both income and
expense.

This pairs all four, as test_export_site_datasets_manifest.py pairs
fct_program_concentration's floor clauses with schema.yml.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from govbudget.export_site import _DATASET_SCOPES

_MARTS = Path(__file__).resolve().parents[1] / "dbt" / "models" / "marts"

#: The clean-total readings R-DEC-LDATOTAL withdrew, wherever they are written.
_WITHDRAWN = (
    "without double-counting",
    "double-counts nothing",
    "no filing reports both",
    "never double-count",
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _column_description(model: str, column: str) -> str:
    doc = yaml.safe_load((_MARTS / "schema.yml").read_text(encoding="utf-8"))
    models = {m["name"]: m for m in doc["models"]}
    assert model in models, f"dbt/models/marts/schema.yml no longer documents {model}"
    columns = {c["name"]: c for c in models[model].get("columns", [])}
    assert column in columns, f"schema.yml documents no {model}.{column}"
    return _norm(columns[column].get("description", ""))


def _header_comment(sql: str) -> str:
    """The leading run of `--` lines, joined: the model's own prose."""
    lines: list[str] = []
    for line in sql.splitlines():
        if not line.startswith("--"):
            break
        lines.append(line[2:])
    return _norm(" ".join(lines))


def test_the_data_note_is_the_authority_this_pairs_against():
    scope = _DATASET_SCOPES["fct_influence"]
    assert "Income and expense are non-additive" in scope
    assert "lobbying_total_usd, a plain sum, can double-count" in scope


def test_schema_yml_calls_lobbying_total_usd_a_plain_sum_that_can_double_count():
    desc = _column_description("fct_influence", "lobbying_total_usd")
    for withdrawn in _WITHDRAWN:
        assert withdrawn not in desc, f"schema.yml still says {withdrawn!r}"
    assert "plain sum" in desc
    assert "not de-duplicated" in desc
    assert "can double-count" in desc
    assert "R-DEC-LDATOTAL" in desc


def test_fct_influence_sql_header_does_not_claim_a_clean_total():
    header = _header_comment((_MARTS / "fct_influence.sql").read_text(encoding="utf-8"))
    for withdrawn in _WITHDRAWN:
        assert withdrawn not in header, f"fct_influence.sql header still says {withdrawn!r}"
    assert "can double-count" in header
    assert "R-DEC-LDATOTAL" in header


def test_the_lda_ingester_docstring_does_not_prescribe_a_clean_total():
    import govbudget.influence.lda as lda

    doc = _norm(lda.__doc__ or "")
    for withdrawn in _WITHDRAWN:
        assert withdrawn not in doc, f"influence/lda.py docstring still says {withdrawn!r}"
    assert "can double-count" in doc
    assert "R-DEC-LDATOTAL" in doc
