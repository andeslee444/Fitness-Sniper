"""Production export includes receipt refresh; fixtures never require live PDFs."""
import json
from pathlib import Path
import runpy
from unittest.mock import Mock

import pytest

from govbudget import cli, config
import govbudget.export_site as site_export
import govbudget.program_pdf_receipts as receipt_export


BASE_SUMMARY = {"datasets": 1, "citations": 2, "pdfs": 1, "workbooks": 1, "skipped_unresolved": 0, "skipped_zero_amount": 0, "dossiers": None}
RECEIPT_SUMMARY = {"complete_receipts": 10, "receipt_count": 12, "source_count": 2}


def configure_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "SITE_DIR", tmp_path / "site")
    monkeypatch.setattr(config, "DUCKDB_PATH", tmp_path / "warehouse.duckdb")


def test_full_export_cli_refreshes_sitewide_pdf_evidence_after_the_complete_bundle(monkeypatch, tmp_path, capsys):
    configure_paths(monkeypatch, tmp_path)
    events = []

    def artifacts(*args, **kwargs):
        events.append("artifacts-and-family-history")
        path = kwargs["out_dir"] / "json"
        path.mkdir(parents=True)
        (path / "citations.json").write_text(json.dumps({"completed": True}))
        (path / "f15_funding_history.json").write_text("{}")
        return BASE_SUMMARY

    def receipts(**kwargs):
        events.append("pdf-evidence")
        assert kwargs == {"site_dir": tmp_path / "site", "manifest": tmp_path / "data-seeds/budget_pdf_sources.json", "cache_dir": tmp_path / "tmp/pdfs"}
        assert json.loads((kwargs["site_dir"] / "json/citations.json").read_text()) == {"completed": True}
        assert (kwargs["site_dir"] / "json/f15_funding_history.json").exists()
        return RECEIPT_SUMMARY

    monkeypatch.setattr(site_export, "export_site", artifacts)
    monkeypatch.setattr(receipt_export, "export_program_pdf_receipts", receipts)
    cli.main(["export-site"])
    assert events == ["artifacts-and-family-history", "pdf-evidence"]
    output = capsys.readouterr().out
    assert "budget PDF receipts: 10/12 complete" in output
    assert "export-site: 1 datasets" in output


def test_failed_artifact_export_never_refreshes_receipts_from_a_stale_bundle(monkeypatch, tmp_path):
    configure_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(site_export, "export_site", Mock(side_effect=ValueError("invalid canonical facts")))
    receipts = Mock(return_value=RECEIPT_SUMMARY)
    monkeypatch.setattr(receipt_export, "export_program_pdf_receipts", receipts)
    with pytest.raises(ValueError, match="invalid canonical facts"):
        cli.main(["export-site"])
    receipts.assert_not_called()


def test_pdf_integrity_failure_fails_the_normal_export_command(monkeypatch, tmp_path, capsys):
    configure_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(site_export, "export_site", Mock(return_value=BASE_SUMMARY))
    monkeypatch.setattr(receipt_export, "export_program_pdf_receipts", Mock(side_effect=ValueError("Government PDF changed; review required")))
    with pytest.raises(ValueError, match="Government PDF changed"):
        cli.main(["export-site"])
    assert "export-site:" not in capsys.readouterr().out


def test_evidence_only_refresh_uses_sitewide_defaults_without_rebuilding_warehouse(monkeypatch, tmp_path):
    configure_paths(monkeypatch, tmp_path)
    artifacts = Mock()
    receipts = Mock(return_value=RECEIPT_SUMMARY)
    monkeypatch.setattr(site_export, "export_site", artifacts)
    monkeypatch.setattr(receipt_export, "export_program_pdf_receipts", receipts)
    cli.main(["export-budget-pdf-receipts"])
    artifacts.assert_not_called()
    receipts.assert_called_once_with(site_dir=tmp_path / "site", manifest=tmp_path / "data-seeds/budget_pdf_sources.json", cache_dir=tmp_path / "tmp/pdfs")


def test_evidence_only_refresh_accepts_explicit_fixture_bundle_and_registry(monkeypatch, tmp_path):
    receipts = Mock(return_value=RECEIPT_SUMMARY)
    monkeypatch.setattr(receipt_export, "export_program_pdf_receipts", receipts)
    cli.main(["export-budget-pdf-receipts", "--site-dir", str(tmp_path / "fixture"), "--manifest", str(tmp_path / "reviewed.json"), "--cache-dir", str(tmp_path / "cache")])
    receipts.assert_called_once_with(site_dir=tmp_path / "fixture", manifest=tmp_path / "reviewed.json", cache_dir=tmp_path / "cache")


def test_existing_script_delegates_to_the_same_sitewide_command(monkeypatch):
    command = Mock()
    monkeypatch.setattr(cli, "main", command)
    monkeypatch.setattr("sys.argv", ["export_budget_pdf_receipts.py", "--site-dir", "/tmp/fixture-site"])
    script = Path(__file__).resolve().parents[1] / "scripts/export_budget_pdf_receipts.py"
    runpy.run_path(str(script), run_name="__main__")
    command.assert_called_once_with(["export-budget-pdf-receipts", "--site-dir", "/tmp/fixture-site"])
