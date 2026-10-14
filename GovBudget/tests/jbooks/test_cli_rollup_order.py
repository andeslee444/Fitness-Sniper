"""cli._jbooks_load_rollups loads each edition's R-1 before its P-1 and P-1R
(families piece-1 follow-ups design §4.3, #194): the P-1 loader checks the
line it records as an R-1 restatement against the loaded R-1, so the R-1
must already be in budget_lines."""
import psycopg

from govbudget import cli, config
from govbudget.jbooks import p1_loader, rollup_loader


def test_r1_loads_before_p1_within_each_edition(pg_dsn, monkeypatch):
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        # registered P-1 first, so table order alone would load it first
        for fy, title in ((2026, "p1_display.xlsx"), (2026, "p1r_display.xlsx"),
                          (2025, "p1_display.xlsx"), (2026, "r1_display.xlsx"),
                          (2025, "r1_display.xlsx")):
            con.execute(
                "insert into jbook_documents (org, exhibit_family, fiscal_year, title,"
                " source_url, file_path, status) values ('DoD', 'rollup', %s, %s,"
                " %s, %s, 'downloaded')",
                (fy, title, f"https://example.test/fy{fy}/{title}", f"/x/fy{fy}/{title}"))
    calls = []
    monkeypatch.setattr(config, "PG_DSN", pg_dsn)
    monkeypatch.setattr(rollup_loader, "load_rollup",
                        lambda dsn, path, *, exhibit, fiscal_year, source_document_id:
                        calls.append((fiscal_year, exhibit)) or 1)
    monkeypatch.setattr(p1_loader, "load_p1_rollup",
                        lambda dsn, path, *, exhibit, fiscal_year, source_document_id:
                        calls.append((fiscal_year, exhibit)) or 1)
    loaded, failures = cli._jbooks_load_rollups()
    assert (loaded, failures) == (5, [])
    assert calls == [(2025, "R-1"), (2025, "P-1"), (2026, "R-1"), (2026, "P-1"),
                     (2026, "P-1R")]
