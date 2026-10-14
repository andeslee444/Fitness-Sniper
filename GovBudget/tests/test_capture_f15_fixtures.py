"""scripts/era/capture_f15_fixtures.py hardening (ROADMAP #201; follow-ups Task 20).

The capture's self-check rebuilt the history from its in-memory rows, not
from the fixture it then wrote, and it wrote its three files one by one, in
place. Now the bytes it writes are gzip round-tripped and rebuilt exactly as
tests/test_f15_era_identity.py rebuilds them, and the three files land
through temporary files, only after every check passed.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

import era.capture_f15_fixtures as capture  # scripts/ is on sys.path via conftest
from govbudget.f15_funding_history import _json_bytes

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "f15"


def _committed_inputs() -> dict:
    return json.loads(gzip.decompress((FIXTURES / "builder_inputs.json.gz").read_bytes()))


def test_round_trip_check_returns_the_bytes_it_proved():
    fixture = _committed_inputs()
    gz = gzip.compress(_json_bytes(fixture), mtime=0)
    assert capture.round_trip_check(fixture, capture.rebuild_from_fixture_bytes(gz)) == gz


def test_round_trip_check_refuses_a_history_the_written_fixture_does_not_rebuild():
    with pytest.raises(SystemExit, match="round-tripped fixture does not rebuild the shipped history"):
        capture.round_trip_check(_committed_inputs(), b"{}\n")


def test_the_check_rebuilds_from_the_written_bytes_not_the_in_memory_rows(monkeypatch):
    fixture = _committed_inputs()
    seen = []
    real = capture.build_history

    def spy(source_rows, series, **kwargs):
        seen.append(source_rows)
        return real(source_rows, series, **kwargs)

    monkeypatch.setattr(capture, "build_history", spy)
    gz = gzip.compress(_json_bytes(fixture), mtime=0)
    capture.round_trip_check(fixture, capture.rebuild_from_fixture_bytes(gz))
    assert seen and all(rows is not fixture["source_rows"] and rows == fixture["source_rows"]
                        for rows in seen)


FILES = {"history.json": b"{}\n", "history.sha256": b"0" * 64 + b"\n", "builder_inputs.json.gz": b"gz"}


def test_write_fixtures_replaces_all_three_files_and_leaves_no_temporaries(tmp_path):
    capture.write_fixtures(tmp_path, FILES)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == FILES


def test_write_fixtures_changes_nothing_when_a_write_fails(tmp_path, monkeypatch):
    old = {"history.json": b"old\n", "history.sha256": b"1" * 64 + b"\n", "builder_inputs.json.gz": b"old-gz"}
    for name, data in old.items():
        (tmp_path / name).write_bytes(data)
    real = Path.write_bytes

    def flaky(self, data):
        if "builder_inputs" in self.name:
            raise OSError("disk full")
        return real(self, data)

    monkeypatch.setattr(Path, "write_bytes", flaky)
    with pytest.raises(OSError, match="disk full"):
        capture.write_fixtures(tmp_path, FILES)
    monkeypatch.undo()
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == old
