"""govbudget.hhi_band is a MIRROR of site/src/lib/hhi-band.mjs — held to it.

The dossier exporter and gate band a cited HHI to check a claim's
concentration word (ruling R-DEC-DOSSIERDRIFT, 2026-09-26). A Python copy of
the thresholds that drifted from the site's would let a dossier sentence
contradict the program badge rendered on the same page. Two legs:

  1. the thresholds are read out of the .mjs SOURCE and compared;
  2. where node is available, the .mjs hhiBand itself is run over a boundary
     sweep and every key compared with the Python answer (whole-point
     banding, JavaScript's round-half-up, both boundaries).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from govbudget import hhi_band

MJS = Path(__file__).resolve().parents[1] / "site" / "src" / "lib" / "hhi-band.mjs"

SWEEP = [
    0, 1, 389.23, 499.5, 998.9, 999.4, 999.49, 999.5, 999.6, 1000, 1000.4,
    1284.683, 1500, 1799.5, 1800, 1800.4, 1800.49, 1800.5, 1800.6, 1801,
    2500, 4831.486, 10000,
]


def _mjs_constant(name: str) -> int:
    m = re.search(rf"export const {name}\s*=\s*(\d+)\s*;", MJS.read_text(encoding="utf-8"))
    assert m, f"{name} not found in {MJS}"
    return int(m.group(1))


def test_the_thresholds_match_the_mjs_source():
    assert hhi_band.HHI_MODERATE_MIN == _mjs_constant("HHI_MODERATE_MIN")
    assert hhi_band.HHI_CONCENTRATED_MIN == _mjs_constant("HHI_CONCENTRATED_MIN")


def test_the_vintage_matches_the_mjs_source():
    m = re.search(r'export const HHI_BANDS_VINTAGE\s*=\s*"([^"]+)"',
                  MJS.read_text(encoding="utf-8"))
    assert m and hhi_band.HHI_BANDS_VINTAGE == m.group(1)


@pytest.mark.parametrize(
    "value,key",
    [
        (999.4, "unconcentrated"),
        # WHOLE POINTS, round half UP (JS Math.round): 999.5 prints "1000".
        (999.5, "moderate"),
        (1000, "moderate"),
        (1800, "moderate"),
        # 1,800.4 prints "1800" — moderately, not highly, concentrated.
        (1800.4, "moderate"),
        (1800.5, "concentrated"),
        (389.23, "unconcentrated"),
        (1284.683, "moderate"),
        (4831.486, "concentrated"),
    ],
)
def test_the_documented_edges(value, key):
    assert hhi_band.hhi_band_key(value) == key


def test_round_half_up_not_bankers_rounding():
    """Python's round(1000.5) is 1000 (half-to-even); JS Math.round is 1001.
    The mirror must follow JS, or an index of x.5 bands differently here."""
    assert hhi_band.hhi_points(1800.5) == 1801
    assert hhi_band.hhi_points(998.5) == 999


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_mjs_function_agrees_on_a_boundary_sweep():
    script = (
        f"import {{ hhiBand }} from {json.dumps(MJS.as_uri())};"
        f"const xs = {json.dumps(SWEEP)};"
        "process.stdout.write(JSON.stringify(xs.map((x) => hhiBand(x).key)));"
    )
    out = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True, text=True, check=True, timeout=60,
    ).stdout
    js_keys = json.loads(out)
    py_keys = [hhi_band.hhi_band_key(x) for x in SWEEP]
    assert py_keys == js_keys, list(zip(SWEEP, js_keys, py_keys))
