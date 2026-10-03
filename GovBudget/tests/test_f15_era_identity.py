"""V5 — F-15 family history identity, on hermetic fixtures (no lake, no data/site).

Spec 2026-10-02-era-procurement-history-design.md §8 V5, §9 S0, §6.2. The
fixtures under tests/fixtures/f15/ are captured once, at S0, by
scripts/era/capture_f15_fixtures.py and re-pinned only by the owner-approved
F-15 correction (S5, §6.5). These tests FAIL, never skip, when they are absent.

1. Golden: build_history + build_program_matrix over the captured inputs
   reproduce the pinned json/f15_funding_history.json byte for byte.
2. Fresh state: with F-15's own family_history / family_program_history
   receipts removed from the registry, and a `decade_era_map` receipt with
   identical inputs and amount injected for every multi-input matrix cell (what
   the era decade tier will mint, §6.1), the bytes are unchanged.
3. Sensitivity: a competitor whose formula IS on the matrix's reuse list,
   with identical inputs and amount, changes exactly one cell's fact ID — so
   the formula allow-list, not luck, is what keeps F-15 stable in (2).
"""
from __future__ import annotations

import functools
import gzip
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from govbudget.export_site import fact_id_derived
from govbudget.f15_funding_history import _json_bytes, build_history, build_program_matrix

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "f15"

# The sensitivity target (verified against the pinned history at S0): PB2018,
# FY2016 actuals, BLI F01500 — two era leaves (PB2018 lines 23 and 79), both
# fy_2016_base_oco, $596,932K. Its own receipt is family_program_history.
TARGET_POINT, TARGET_CELL = 2, 2
TARGET_PROGRAM = "P-1:3010F:AF:F01500"
TARGET_OWN_FID = "a0231f5a75a7ad52"
TARGET_INPUTS = ["28f53c8d681494cc", "cce72b42a96bfcb7"]
COMPETITOR_FID = "0" * 16


def _fixture_path(name: str) -> Path:
    path = FIXTURES / name
    if not path.is_file():
        pytest.fail(f"F-15 identity fixture missing: {path.relative_to(ROOT)} "
                    "(capture it with scripts/era/capture_f15_fixtures.py; spec §9 S0)", pytrace=False)
    return path


@functools.lru_cache(maxsize=1)
def _inputs() -> dict:
    with gzip.open(_fixture_path("builder_inputs.json.gz"), "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _pinned_bytes() -> bytes:
    return _fixture_path("history.json").read_bytes()


def _payload():
    """build_history over the captured rows: (payload, workbook leaf ids)."""
    inputs = _inputs()
    payload, _, workbook_rows, _ = build_history(
        inputs["source_rows"], inputs["series"], retrieved_at=inputs["retrieved_at"],
        current_fact_ids=set(inputs["current_fact_ids"]))
    return payload, set(workbook_rows)


def _matrix_bytes(payload, registry) -> tuple[bytes, dict, dict]:
    out, additions, breakdowns = build_program_matrix(
        payload, _inputs()["previews"], existing_citations=registry, retrieved_at=_inputs()["retrieved_at"])
    return _json_bytes(out), additions, breakdowns


def _own_receipt_ids(history: dict) -> set[str]:
    """Every receipt F-15's own builder mints: annual, cumulative, multi-input cells."""
    ids = {history["cumulative"]["fact_id"]}
    for point in history["points"]:
        ids.add(fact_id_derived("family_history", f"f-15|{point['edition']}|{point['fy']}", point["kind"]))
        for cell in point["program_cells"]:
            if len(cell["input_fact_ids"]) > 1:
                ids.add(fact_id_derived("family_program_history",
                                        f"{cell['program_id']}|{point['edition']}|{point['fy']}", point["kind"]))
    return ids


def _fresh_registry(history: dict) -> dict:
    own = _own_receipt_ids(history)
    registry = _inputs()["registry"]
    # The captured subset holds the 30 annual receipts and the 27 era
    # multi-input cell receipts (the cumulative's inputs are annual ids, not
    # workbook leaves, so it is not in the subset).
    assert len(own & set(registry)) == 57
    return {fid: citation for fid, citation in registry.items() if fid not in own}


def _diff(a, b, at=()):
    """Every leaf path at which two JSON values differ, as (path, a, b)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for key in sorted(set(a) | set(b)) for d in _diff(a.get(key), b.get(key), (*at, key))]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for index, (x, y) in enumerate(zip(a, b)) for d in _diff(x, y, (*at, index))]
    return [] if a == b else [(at, a, b)]


def test_pin_matches_committed_history():
    data = _pinned_bytes()
    pin = _fixture_path("history.sha256").read_text().strip()
    assert len(pin) == 64 and pin == hashlib.sha256(data).hexdigest()
    assert _inputs()["captured_from"]["history_sha256"] == pin


def test_golden_rebuild_from_fixtures_is_byte_identical():
    payload, leaves = _payload()
    assert len(leaves) == 207 and len(payload["points"]) == 30
    assert set(_inputs()["previews"]) == leaves
    data, _, _ = _matrix_bytes(payload, _inputs()["registry"])
    assert data == _pinned_bytes()


def test_fresh_state_with_decade_era_map_receipts_keeps_every_byte():
    history = json.loads(_pinned_bytes())
    registry = _fresh_registry(history)
    injected = 0
    era_cells = 0
    for point in history["points"]:
        components = {row["fact_id"]: row for row in point["components"]}
        for cell in point["program_cells"]:
            ids = sorted(cell["input_fact_ids"])
            if len(ids) < 2:
                continue
            amount_types = {components[fid]["amount_type"] for fid in ids}
            assert len(amount_types) == 1, cell["fact_id"]
            amount_type = amount_types.pop()
            code = cell["program_id"].rsplit(":", 1)[1]
            amount = sum((Decimal(str(components[fid]["amount_thousands"])) for fid in ids), Decimal(0))
            # §6.1: surface "decade_era_map", key "{program_key}|{account}|{organization}|{edition}"
            # (blank account/organization for a non-collision code), inputs sorted by fact ID.
            fid = fact_id_derived("decade_era_map", f"{code}|||{point['edition']}", amount_type)
            registry[fid] = dict(
                kind="derived", units="USD thousands", recorded_value=f"{amount:.3f}",
                formula=(f"sum(budget_lines.amount_thousands where era_line_map='{code}' "
                         f"and amount_type={amount_type} and edition={point['edition']})"),
                inputs=json.dumps(ids), retrieved_at="2026-10-02T00:00:00+00:00")
            injected += 1
            era_cells += all(components[f]["pe_bli"].startswith("3010F-AF-L") for f in ids)
    assert (injected, era_cells) == (38, 27)
    payload, _ = _payload()
    data, _, _ = _matrix_bytes(payload, registry)
    assert data == _pinned_bytes()


def test_allowed_formula_competitor_changes_exactly_one_cell():
    history = json.loads(_pinned_bytes())
    point = history["points"][TARGET_POINT]
    cell = point["program_cells"][TARGET_CELL]
    assert (point["edition"], point["fy"], point["kind"]) == (2018, 2016, "actuals")
    assert (cell["program_id"], cell["fact_id"], sorted(cell["input_fact_ids"])) == (TARGET_PROGRAM, TARGET_OWN_FID, TARGET_INPUTS)
    assert TARGET_OWN_FID == fact_id_derived("family_program_history", f"{TARGET_PROGRAM}|2018|2016", "actuals")
    competitor = dict(
        kind="derived", units="USD thousands", recorded_value="596932.000",
        formula="sum(budget_lines.amount_thousands where amount_type=fy_2016_base_oco and edition=2018)",
        inputs=json.dumps(TARGET_INPUTS), retrieved_at="2026-10-02T00:00:00+00:00")
    payload, _ = _payload()

    # Fresh state: nothing outranks the allowed competitor, so it takes the cell.
    data, additions, breakdowns = _matrix_bytes(payload, {**_fresh_registry(history), COMPETITOR_FID: competitor})
    changed = json.loads(data)
    assert _diff(history, changed) == [
        (("points", TARGET_POINT, "program_cells", TARGET_CELL, "fact_id"), TARGET_OWN_FID, COMPETITOR_FID)]
    assert additions[COMPETITOR_FID] == competitor and TARGET_OWN_FID not in additions
    assert COMPETITOR_FID in breakdowns and TARGET_OWN_FID not in breakdowns

    # Today's registry: F-15's own receipt (allowed index 0) outranks it.
    data, _, _ = _matrix_bytes(payload, {**_inputs()["registry"], COMPETITOR_FID: competitor})
    assert data == _pinned_bytes()
