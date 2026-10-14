"""ROADMAP #204 (families piece-1 follow-ups spec 2026-10-04 §6.7): the era
fences are required arguments, and the /lineage/ flow asserts that no era
grain supplies its money column."""
from __future__ import annotations

import inspect

import pytest

from govbudget import export_site as es
from govbudget.lineage.flow import AMOUNT_FY, AMOUNT_MEASURE, build_lineage_flow

ERA = "e0a0000000000001"
NATIVE = "f0a0000000000002"


@pytest.mark.parametrize("name", ["_emit_lineage", "_emit_json_sidecars", "_write_all_sidecars"])
def test_era_grain_fids_is_a_required_keyword_only_argument(name):
    param = inspect.signature(getattr(es, name)).parameters["era_grain_fids"]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    assert param.default is inspect.Parameter.empty, f"{name} still defaults era_grain_fids"


def test_years_matrix_no_longer_takes_the_era_fence():
    # Task 13 lifted the /years/ fence; a stale parameter would read as a fence.
    assert "era_grain_fids" not in inspect.signature(es._emit_years_matrix).parameters


def _flow(fid: str) -> dict:
    return build_lineage_flow(
        edges=[], families={"PRED": 1}, titles_by_pe={"PRED": "Predecessor"},
        page_pes={"PRED"},
        decade_series_by_pe={"PRED": {"request": [{
            "fy": AMOUNT_FY, "v": 5.0, "fid": fid, "edition": 2026, "basis": "toa",
            "measure": AMOUNT_MEASURE}]}},
        cited_fact_ids={fid},
    )


def test_the_lineage_flow_accepts_a_native_amount():
    es._assert_lineage_flow_has_no_era_amount(_flow(NATIVE), frozenset({ERA}))


def test_the_lineage_flow_refuses_an_era_amount():
    with pytest.raises(RuntimeError, match=r"1 FY2026 amount\(s\) chosen from an era grain"):
        es._assert_lineage_flow_has_no_era_amount(_flow(ERA), frozenset({ERA}))
