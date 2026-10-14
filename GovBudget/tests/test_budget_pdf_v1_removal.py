"""ROADMAP #196 (families piece-1 follow-ups, design §5.7; owner sign-off
2026-10-04): the v1 F-15-only receipt writer, its unread PDF seed and the 256
two-hex shards it left are gone. program_pdf_receipts writes
json/budget-pdf-receipts/v2/, which is all the site reads
(site/src/lib/budget-pdf-receipts.ts), and now also clears the v1 shards an
older export left beside it, so the site build cannot ship them.
"""
from __future__ import annotations

import ast
from pathlib import Path

import govbudget.budget_pdf_receipts as receipts_v1
from govbudget.program_pdf_receipts import export_program_pdf_receipts, remove_v1_receipt_shards

ROOT = Path(__file__).resolve().parents[1]


def test_the_v1_writer_and_the_helpers_only_it_used_are_gone():
    for name in ("export_budget_pdf_receipts", "load_sources", "tight_glyph_geometry"):
        assert not hasattr(receipts_v1, name), name


def test_the_matcher_module_imports_nothing_it_does_not_use():
    tree = ast.parse(Path(receipts_v1.__file__).read_text(encoding="utf-8"))
    imported = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update({(a.asname or a.name).split(".")[0]: node.lineno for a in node.names})
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imported.update({a.asname or a.name: node.lineno for a in node.names})
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert sorted(set(imported) - used) == []


def test_the_unread_f15_pdf_seed_is_gone():
    assert not (ROOT / "data-seeds" / "f15_budget_pdf_sources.json").exists()
    assert (ROOT / "data-seeds" / "budget_pdf_sources.json").exists()


def test_the_export_removes_v1_shards_and_keeps_v2(tmp_path):
    site = tmp_path / "site"
    receipts = site / "json" / "budget-pdf-receipts"
    (receipts / "v2").mkdir(parents=True)
    for name in ("00.json", "a7.json", "ff.json"):
        (receipts / name).write_text("{}\n")
    (receipts / "README.txt").write_text("kept\n")
    (receipts / "v2" / "000.json").write_text('{"stale": {}}\n')
    (site / "json" / "citations.json").write_text("{}")
    manifest = tmp_path / "sources.json"
    manifest.write_text("[]")
    report = export_program_pdf_receipts(site_dir=site, manifest=manifest, cache_dir=tmp_path / "cache")
    assert sorted(p.name for p in receipts.iterdir()) == ["README.txt", "v2"]
    assert len(list((receipts / "v2").glob("*.json"))) == 4096
    assert (receipts / "v2" / "000.json").read_text() == "{}\n"
    assert report["receipt_count"] == 0


def test_remove_v1_receipt_shards_takes_only_two_hex_digit_files(tmp_path):
    assert remove_v1_receipt_shards(tmp_path / "absent") == 0
    (tmp_path / "v2").mkdir()
    (tmp_path / "v2" / "0f.json").write_text("{}")
    for name in ("0f.json", "10.json", "abc.json", "1g.json"):
        (tmp_path / name).write_text("{}")
    assert remove_v1_receipt_shards(tmp_path) == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == ["1g.json", "abc.json", "v2"]
    assert (tmp_path / "v2" / "0f.json").exists()
