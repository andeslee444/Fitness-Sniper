"""#86: `jbooks crosswalk` reports written vs guard-skipped links.

The old single count added 1 for every candidate row, including the ones the
upsert's method guard refused to touch (an evidence-graded row already on the
key), so the printed "links" overstated what the run wrote.

DB-free: migrate, plan_crosswalk_org and crosswalk_org are monkeypatched (the
pattern tests/jbooks/test_cli_service.py::_wire_service_backfill uses).
cmd_jbooks imports the crosswalk module at call time, so patching the module
attributes is enough. The DB-backed CLI tests in test_crosswalk.py cover the
plan/abort path; this one isolates the two printed counts.
"""
import argparse

import govbudget.jbooks.db
from govbudget import cli, config
from govbudget.jbooks import crosswalk as crosswalk_module
from govbudget.jbooks.crosswalk import CrosswalkResult, LinePlan


def test_crosswalk_cli_prints_written_and_skipped_separately(monkeypatch, capsys):
    monkeypatch.setattr(govbudget.jbooks.db, "migrate", lambda *a, **kw: [])
    # Defence in depth (same reason as test_crosswalk.py::_wire_crosswalk_cli):
    # the plan/write path is monkeypatched out, so nothing here should reach
    # Postgres — but if a patch point ever drifts, the CLI must fail on a DSN
    # that cannot exist rather than write to the live database.
    monkeypatch.setattr(config, "PG_DSN", "postgresql://localhost/govbudget_no_such_db")
    calls: list[str] = []

    def fake_plan(dsn, **kw):
        # Five projected pairs: well under ALL_YEARS_ABORT_ROWS, so the run
        # proceeds without --yes and the write path's print is what we read.
        return [LinePlan("0601101E", "R-1", 2026, "0400", "097-0400", 2026, 2026, 5)]

    def fake_crosswalk_org(dsn, **kw):
        calls.append(kw["organization"])
        return CrosswalkResult(written=3, skipped=2)

    monkeypatch.setattr(crosswalk_module, "plan_crosswalk_org", fake_plan)
    monkeypatch.setattr(crosswalk_module, "crosswalk_org", fake_crosswalk_org)
    cli.cmd_jbooks(argparse.Namespace(
        action="crosswalk", org="DARPA", fy_start=None, fy_end=None))
    out = capsys.readouterr().out
    assert calls == ["DARPA"]
    assert ("crosswalk DARPA: 3 links written, 2 skipped"
            " (evidence-graded rows kept)") in out
    assert "crosswalk total: 3 written, 2 skipped" in out
