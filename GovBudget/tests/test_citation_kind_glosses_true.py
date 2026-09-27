"""Every citation-kind gloss is true of every row of its kind in the shipped
citations.parquet (final integration pass, 2026-09-27).

Final-review finding #10(c): the /downloads/ citations card said
"(jbook_pdf + workbook + lda_filing)" while citations.parquet holds 10 kinds.
The exporter now writes a datasets.json "citations" entry whose scope glosses
each kind (export_site._CITATION_KIND_GLOSSES), and the /downloads/ card and
JSON-LD render that scope (site/src/__tests__/downloads-citations-index.test.tsx).
A gloss is a claim about EVERY row of its kind, so each one is held to the file:

- "derived" said "a computed figure with its formula and inputs". On the
  chain-G file (measured 2026-09-27) 2,499 of its 38,993 rows record no figure
  (2,497 crosswalk-link citations record the link's confidence tier, "high"
  or "medium"; 2 SAM.gov citations a registration status, "Active"), and
  9,218 carry no inputs ("[]"). Every derived row does carry a formula and a
  recorded value.
- The column each other gloss implies is present on every row of its kind:
  a workbook cell names its sheet, a J-book narrative passage its xml_path,
  a USAspending query its query_body.

Skipped where the shipped file is absent (a fresh checkout); the fixture tests
in test_export_site_datasets_manifest.py pin the scope sentence's shape.
"""

from pathlib import Path

import pytest

from govbudget.export_site import _CITATION_KIND_GLOSSES

ROOT = Path(__file__).resolve().parents[1]
CITATIONS = ROOT / "data" / "site" / "citations" / "citations.parquet"


@pytest.fixture(scope="module")
def con():
    if not CITATIONS.exists():
        pytest.skip(f"{CITATIONS} not present (run export-site)")
    import duckdb

    c = duckdb.connect()
    c.execute(f"create view cit as select * from read_parquet('{CITATIONS}')")
    yield c
    c.close()


def _count(con, kind: str, where: str) -> int:
    return con.execute(
        f"select count(*) from cit where kind = ? and ({where})", [kind]
    ).fetchone()[0]


def test_every_shipped_kind_is_glossed(con):
    kinds = {k for (k,) in con.execute("select distinct kind from cit").fetchall()}
    assert kinds <= set(_CITATION_KIND_GLOSSES), kinds - set(_CITATION_KIND_GLOSSES)


def test_the_derived_gloss_claims_only_what_every_derived_row_carries(con):
    gloss = _CITATION_KIND_GLOSSES["derived"]
    assert _count(con, "derived", "true") > 0
    # What every derived row does carry: a formula and a recorded value.
    assert _count(con, "derived", "coalesce(formula, '') = ''") == 0
    assert _count(con, "derived", "coalesce(recorded_value, '') = ''") == 0
    assert "formula" in gloss and "value" in gloss, gloss
    # "figure" is a number: only if every derived row records one.
    non_numeric = _count(con, "derived", "try_cast(recorded_value as double) is null")
    if non_numeric:
        assert "figure" not in gloss, (
            f"{non_numeric} derived rows record no figure (a link tier, a"
            f" registration status), yet the gloss reads {gloss!r}")
    # "inputs" only if every derived row lists at least one.
    no_inputs = _count(con, "derived", "coalesce(inputs, '') in ('', '[]')")
    if no_inputs:
        assert "input" not in gloss, (
            f"{no_inputs} derived rows carry no inputs, yet the gloss reads {gloss!r}")


@pytest.mark.parametrize(
    "kind, column",
    [("workbook", "sheet"), ("jbook_narrative", "xml_path"), ("usaspending", "query_body")],
)
def test_the_column_a_gloss_implies_is_on_every_row(con, kind, column):
    assert _count(con, kind, "true") > 0
    assert _count(con, kind, f"coalesce({column}, '') = ''") == 0


def test_the_jbook_pdf_gloss_is_true_of_every_jbook_pdf_row(con):
    """"a figure printed in a J-book PDF" was false for 4 of the 9,879 rows
    (chain G, measured 2026-09-27): resolution 'unresolved', no amount_text,
    no page_number (e.g. 90fab19bdc91648a, 0208088F). export_site keeps such a
    row as the document receipt alone when it cannot prove the matched
    numeral's units (4a, "Retain the document receipt without presenting an
    unproven numeral ... as money"). Final-review finding #10 follow-up."""
    gloss = _CITATION_KIND_GLOSSES["jbook_pdf"]
    assert _count(con, "jbook_pdf", "true") > 0
    # Every row cites a J-book PDF: its SHA-256 and the hosted copy.
    assert _count(con, "jbook_pdf", "coalesce(sha256, '') = ''") == 0
    assert _count(con, "jbook_pdf", "coalesce(hosted_pdf_url, '') = ''") == 0
    # A row with no printed figure (no amount_text or no page) is exactly an
    # unresolved row, and every other row carries both.
    no_figure = "coalesce(amount_text, '') = '' or page_number is null"
    assert _count(con, "jbook_pdf", f"({no_figure}) and coalesce(resolution, '') <> 'unresolved'") == 0
    assert _count(con, "jbook_pdf", f"resolution = 'unresolved' and not ({no_figure})") == 0
    if _count(con, "jbook_pdf", no_figure):
        assert "unresolved" in gloss and "the PDF alone" in gloss, (
            f"{_count(con, 'jbook_pdf', no_figure)} jbook_pdf rows cite no printed"
            f" figure (unresolved), yet the gloss reads {gloss!r}")


def test_the_jbook_pdf_gloss_covers_the_exporters_unresolved_path():
    """Not skipped on a fresh checkout: the exporter mints unresolved
    jbook_pdf rows by construction (units unproven -> amount_text and
    page_number None), so the gloss must cover them whatever the current
    file holds."""
    src = (ROOT / "src" / "govbudget" / "export_site.py").read_text(encoding="utf-8")
    assert 'resolution = "unresolved"' in src
    assert "citation_units = amount_text = page_number = None" in src
    gloss = _CITATION_KIND_GLOSSES["jbook_pdf"]
    assert gloss.startswith("a figure printed in a J-book PDF"), gloss
    assert "unresolved" in gloss and "the PDF alone" in gloss, gloss
