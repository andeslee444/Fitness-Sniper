import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def script(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("jev_editorial_script_test", scripts / "review_jev_editorial.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_run_uses_exact_prepared_packet_even_if_source_changes(tmp_path, monkeypatch, script):
    cases = [{"id": "a", "state": {"claim": "Original claim"}}]
    monkeypatch.setattr(script, "prepare_batch", lambda root: cases)
    script.prepared_batch(tmp_path, root=tmp_path, run=False)
    prepared = (tmp_path / "cases.json").read_bytes()
    manifest = (tmp_path / "manifest.json").read_bytes()
    monkeypatch.setattr(script, "prepare_batch", lambda root: pytest.fail("Frozen input must not be rebuilt"))
    assert script.prepared_batch(tmp_path, root=tmp_path, run=True) == cases
    assert (tmp_path / "cases.json").read_bytes() == prepared
    assert (tmp_path / "manifest.json").read_bytes() == manifest


def test_changed_packet_and_existing_results_are_retained(tmp_path, monkeypatch, script):
    monkeypatch.setattr(script, "prepare_batch", lambda root: [{"id": "a"}])
    script.prepared_batch(tmp_path, root=tmp_path, run=False)
    with pytest.raises(ValueError, match="Existing preparation retained"):
        script.prepared_batch(tmp_path, root=tmp_path, run=False)
    (tmp_path / "cases.json").write_text(json.dumps([{"id": "changed"}]))
    with pytest.raises(ValueError, match="Prepared cases changed"):
        script.prepared_batch(tmp_path, root=tmp_path, run=True)
    (tmp_path / "results.jsonl").write_text("original result\n")
    with pytest.raises(ValueError, match="Existing results retained"):
        script.prepared_batch(tmp_path, root=tmp_path, run=True)
    assert (tmp_path / "results.jsonl").read_text() == "original result\n"
