"""Python mirror of site/src/lib/hhi-band.mjs (2023 Merger Guidelines bands).

The site's single source for the three-way HHI band vocabulary is
site/src/lib/hhi-band.mjs (#132, R-DEC-132b). Python needed the same bands
once the dossier exporter and gate began checking a dossier claim's
concentration word against the band of the HHI it cites (ruling
R-DEC-DOSSIERDRIFT, 2026-09-26). No Python copy existed, so this is the
smallest faithful mirror: the two thresholds and the band function, banded in
WHOLE POINTS exactly as the .mjs does (JavaScript's Math.round, which rounds
a half up — floor(x + 0.5) — not Python's round-half-to-even).

    HHI <  1,000               unconcentrated (this site's label)
    1,000 <= HHI <= 1,800      moderate       ("between": both ends)
    HHI >  1,800               concentrated   ("in excess of")

tests/test_hhi_band_parity.py holds this file to the .mjs: it reads both
thresholds out of the .mjs source and, where node is available, runs the
.mjs hhiBand over a boundary sweep and compares every key.
"""
from __future__ import annotations

import math

HHI_BANDS_VINTAGE = "2023 Merger Guidelines"

#: Inclusive floor of "moderately concentrated".
HHI_MODERATE_MIN = 1000
#: Highly concentrated means IN EXCESS of this; 1,800 itself is moderate.
HHI_CONCENTRATED_MIN = 1800


def hhi_points(value: float) -> int:
    """Whole points as the site prints them (JavaScript Math.round)."""
    return math.floor(value + 0.5)


def hhi_band_key(value: float) -> str:
    """'unconcentrated' | 'moderate' | 'concentrated' — hhiBand(value).key."""
    points = hhi_points(value)
    if points > HHI_CONCENTRATED_MIN:
        return "concentrated"
    if points >= HHI_MODERATE_MIN:
        return "moderate"
    return "unconcentrated"
