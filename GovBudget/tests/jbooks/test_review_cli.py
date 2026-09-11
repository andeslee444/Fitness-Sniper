"""#9 — `govbudget review list` reports carried (pre-accepted) rows apart
from open ones, and lists them only under --carried."""
from pathlib import Path

import psycopg

from govbudget.jbooks.load_details import load_document_details
from govbudget.jbooks.reconcile import reconcile_document

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "jbooks" / "darpa_fy2026_excerpt.xml"


def test_review_list_shows_carried_rows_distinctly(monkeypatch, capsys, pg_dsn, single_failure_doc):
    from govbudget import cli, config

    monkeypatch.setattr(config, "PG_DSN", pg_dsn)
    doc_id, run1 = single_failure_doc
    reconcile_document(pg_dsn, document_id=doc_id, extraction_run_id=run1)

    cli.main(["review", "list"])
    out = capsys.readouterr().out
    open_lines = [line for line in out.splitlines() if line.startswith("#")]
    assert len(open_lines) == 1                                  # one open line, as before
    assert "gate B 0601101E/PriorYear expected=999.999 actual=280.494 ::" in open_lines[0]
    assert out.rstrip().endswith("1 open item(s), 0 carried")
    with psycopg.connect(pg_dsn) as con:
        root_id = con.execute("select id from review_queue where status='open'").fetchone()[0]

    cli.main(["review", "accept", "--id", str(root_id), "--reason", "documented delta"])
    assert capsys.readouterr().out.strip() == f"#{root_id} accepted: documented delta"

    run2 = load_document_details(pg_dsn, document_id=doc_id, xml_path=FIXTURE)
    reconcile_document(pg_dsn, document_id=doc_id, extraction_run_id=run2)

    cli.main(["review", "list"])
    out = capsys.readouterr().out
    assert out.strip() == "0 open item(s), 1 carried (review list --carried to show)"

    cli.main(["review", "list", "--carried"])
    out = capsys.readouterr().out
    carried_lines = [line for line in out.splitlines() if line.startswith("~#")]
    assert len(carried_lines) == 1
    assert "gate B 0601101E/PriorYear expected=999.999 actual=280.494" in carried_lines[0]
    assert carried_lines[0].endswith(f":: carried from #{root_id}: documented delta")
    assert out.rstrip().endswith("0 open item(s), 1 carried")
