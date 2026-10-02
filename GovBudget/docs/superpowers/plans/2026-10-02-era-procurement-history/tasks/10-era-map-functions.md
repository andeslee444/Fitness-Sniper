<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 10: era_map pure functions: normalize, classify, chains, rulings

**Spec:** §5.1 (normalization; rule order CR → UNSAFE → R3 → A1 → A2 → R1 → R2 → H; org-aware
existence for the five org-split codes), §5.2 (chain identity; R-DEC-ERA-EXCLUDE precedence;
R-DEC-ERA-SAME with collision pinning and the no-page exit; R-DEC-ERA-HISTORY for drift-free
era-only chains), §4.3 (seed columns, `decision_id`, `keys_sha256`, `decided_by=owner`).

**Files:**
- Create: `src/govbudget/jbooks/era_map.py`
- Test: `tests/jbooks/test_era_map.py`

**Interfaces:** Consumes: `EraKeyConflict` (Task 6, `src/govbudget/jbooks/p1_loader.py`; imported now,
used from Task 11), `require_resolved` (`src/govbudget/jbooks/collision_keys.py:121`),
`is_era_procurement_key` (`src/govbudget/jbooks/era_keys.py:105`), `is_route_safe_pe`
(`src/govbudget/export_site.py:6751`, test parity only). / Produces: in `govbudget.jbooks.era_map`:
`CLASS_ORDER`, `ORG_SPLIT_CODES`, `RULING_SAME`, `RULING_EXCLUDE`, `RULING_HISTORY`,
`CLASS_RULINGS`, `DECISIONS`, `SEED_COLUMNS`, `REVIEW_COLUMNS`, `CHAIN_COLUMNS`, `KEY_COLUMNS`,
`ERA_ORG_TO_MODERN`, `CR_CODES`, `CLASS_RULINGS_DECIDED_ON`, `BATCH_RE`; dataclasses `EraKey`,
`ModernLine`, `Chain` (with `first_edition`/`last_edition` properties); `normalize_title(title) -> str`,
`title_jaccard(a, b) -> float`, `keys_sha256(lines) -> str`, `is_route_safe_code(code) -> bool`,
`org_split_codes(era) -> frozenset[str]`, `chain_id(code, account, organization) -> str`,
`parse_chain_id(cid) -> tuple[str, str, str]`, `classify_keys(era, modern, *, collision_codes) ->
dict[tuple[int, str], str]`, `group_keys(era) -> dict[str, list[EraKey]]`, `range_sha(keys, first,
last) -> tuple[int, str]`, `build_chains(era, classes) -> list[Chain]`, `title_drift_free(chain) ->
bool`, `collision_page(chain, modern_pages) -> tuple[str, str] | None`, `class_ruling(chain, *,
modern_pages, collision_codes) -> tuple[str, str, str, str] | None`, `seed_row(chain, *, first, last,
n_keys, keys_sha, decision, ruling, decided_on, ...) -> dict[str, str]`, `apply_class_rulings(chains,
*, modern_pages, collision_codes, decided_on) -> tuple[list[dict], list[Chain]]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/jbooks/test_era_map.py`:

```python
"""Era map pure functions (families piece 1, spec §4.3, §5.1, §5.2).

Synthetic inputs only: no lake, no DuckDB, no Postgres.
"""
from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

import pytest

from govbudget.jbooks import era_map
from govbudget.jbooks.era_map import (
    CLASS_ORDER,
    DECISIONS,
    RULING_EXCLUDE,
    RULING_HISTORY,
    RULING_SAME,
    SEED_COLUMNS,
    EraKey,
    ModernLine,
    apply_class_rulings,
    build_chains,
    classify_keys,
    keys_sha256,
    normalize_title,
    org_split_codes,
)

D = Decimal


def ek(edition, account, org, line, code, title, *, ba="01", act=None,
       enacted=None):
    return EraKey(
        edition=edition, account=account, organization=org, budget_activity=ba,
        era_key=f"{account}-{org}-L{line}", line_item_code=code,
        filed_title=title, actuals_k=None if act is None else D(act),
        source_document_sha256="ab" * 32, source_cells=(f"O{line}",),
        enacted_k=None if enacted is None else D(enacted),
    )


def ml(edition, code, account, org, title, *, act=None, enacted=None):
    return ModernLine(edition=edition, code=code, account=account,
                      organization=org, title=title,
                      actuals_k=None if act is None else D(act),
                      enacted_k=None if enacted is None else D(enacted))


NONE = frozenset()


# ---------------------------------------------------------------------------
# vocabulary
# ---------------------------------------------------------------------------

def test_vocabulary_is_the_contract():
    assert CLASS_ORDER == ("CR", "UNSAFE", "R3", "A1", "A2", "R1", "R2", "H")
    assert era_map.ORG_SPLIT_CODES == frozenset({"10", "15", "20", "30", "500"})
    assert (RULING_SAME, RULING_EXCLUDE, RULING_HISTORY) == (
        "R-DEC-ERA-SAME", "R-DEC-ERA-EXCLUDE", "R-DEC-ERA-HISTORY")
    assert DECISIONS == ("same_program", "history_only", "exclude_placeholder",
                         "exclude_route_unsafe", "exclude_reused_code")
    assert SEED_COLUMNS == (
        "decision_id", "line_item_code", "account", "organization",
        "first_edition", "last_edition", "decision", "program_account",
        "program_org", "successor_code", "successor_account",
        "successor_evidence", "n_keys", "keys_sha256", "titles_seen",
        "modern_title", "proposed_rule", "evidence", "decided_on",
        "decided_by", "ruling", "note")


# ---------------------------------------------------------------------------
# normalize_title / title_jaccard / keys_sha256
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, want", [
    ("Joint Light Tactical Vehicle", "joint light tactical vehicle"),
    ("JOINT LIGHT TACTICAL VEHICLE", "joint light tactical vehicle"),
    ("F-35A (MYP)", "f 35a"),
    ("Virginia Class Submarine (AP-CY)", "virginia class submarine"),
    ("C-130J (AP)", "c 130j"),
    ("GPS III Space Segment (SPACE)", "gps iii space segment"),
    ("Mine-Resistant/Ambush-Protected", "mine resistant ambush protected"),
    ("  Items  Less Than $5 Million ", "items less than 5 million"),
    ("Aircraft (MIP) (MULTIYEAR)", "aircraft"),
    (None, ""),
])
def test_normalize_title(raw, want):
    assert normalize_title(raw) == want


def test_title_jaccard():
    assert era_map.title_jaccard("Ohio Replacement", "OHIO REPLACEMENT (AP)") == 1.0
    assert era_map.title_jaccard("Major Equipment, TJS", "Major Equipment") == 2 / 3
    assert era_map.title_jaccard("LX(R)", "LPD Flight II") == 0.0
    assert era_map.title_jaccard(None, "anything") == 0.0


def test_keys_sha256_is_order_free_and_blank_safe():
    lines = [(2018, "2035A-ARMY-L7", "01", "JLTV"), (2017, "2035A-ARMY-L9", None, None)]
    want = hashlib.sha256(
        b"2017|2035A-ARMY-L9||\n2018|2035A-ARMY-L7|01|JLTV").hexdigest()
    assert keys_sha256(lines) == want
    assert keys_sha256(list(reversed(lines))) == want
    changed = [(2018, "2035A-ARMY-L7", "01", "JLTV2"), lines[1]]
    assert keys_sha256(changed) != want


@pytest.mark.parametrize("code", ["O&M", "RDT&E", "A/B", "A?B", "A%B", "A#B",
                                  "A B", "D15610", "FY2017CR", "0145"])
def test_route_safety_mirrors_the_exporter(code):
    from govbudget.export_site import is_route_safe_pe

    assert era_map.is_route_safe_code(code) is is_route_safe_pe(code)


# ---------------------------------------------------------------------------
# org split
# ---------------------------------------------------------------------------

def test_org_split_codes_needs_two_orgs_in_one_edition_account():
    era = [
        ek(2017, "0300D", "DSS", 20, "20", "Major Equipment"),
        ek(2017, "0300D", "DTRA", 21, "20", "Vehicles"),
        ek(2017, "0300D", "TJS", 10, "10", "Major Equipment, TJS"),
        ek(2018, "0300D", "DPAA", 11, "10", "Major Equipment, DPAA"),
        # same code, two orgs, but different accounts: not org-split
        ek(2017, "2031A", "ARMY", 1, "X1", "A"),
        ek(2017, "0300D", "OSD", 1, "X1", "A"),
    ]
    assert org_split_codes(era) == frozenset({"20"})


# ---------------------------------------------------------------------------
# classify_keys — §5.1 rules and their order
# ---------------------------------------------------------------------------

def classes(era, modern, collision=NONE):
    return classify_keys(era, modern, collision_codes=collision)


def test_cr_placeholder_is_cr_not_h():
    k = ek(2017, "2031A", "ARMY", 99, "FY2017CR", "FY 2017 CR Adjustment")
    assert classes([k], []) == {(2017, k.era_key): "CR"}


def test_route_unsafe_code_is_unsafe_even_when_modern_prints_it():
    k = ek(2019, "0390D", "CBDP", 2, "O&M", "Operation & Maintenance")
    modern = [ml(2024, "O&M", "0390D", "CBDP", "Operation & Maintenance")]
    assert classes([k], modern) == {(2019, k.era_key): "UNSAFE"}


def test_r3_beats_a1_when_code_spans_accounts_in_the_edition():
    a = ek(2019, "3020F", "AF", 5, "SPC001", "Space Item")
    b = ek(2019, "3021F", "AF", 6, "SPC001", "Space Item")
    modern = [ml(2024, "SPC001", "3020F", "F", "Space Item")]
    got = classes([a, b], modern)
    assert got[(2019, a.era_key)] == "R3"       # (code, account) exists → R3
    assert got[(2019, b.era_key)] == "R2"       # 3021F absent → R2


def test_collision_code_spanning_accounts_is_not_r3():
    a = ek(2019, "1611N", "NAVY", 5, "3010", "LPD Flight II")
    b = ek(2019, "1810N", "NAVY", 9, "3010", "Shipboard Tactical Communications")
    modern = [ml(2026, "3010", "1611N", "N", "LPD Flight II"),
              ml(2026, "3010", "1810N", "N", "Shipboard Tactical Communications")]
    got = classes([a, b], modern, frozenset({"3010"}))
    assert got == {(2019, a.era_key): "A1", (2019, b.era_key): "A1"}


def test_a1_matches_after_normalization():
    k = ek(2020, "2035A", "ARMY", 7, "D15610", "JOINT LIGHT TACTICAL VEHICLE (MYP)")
    modern = [ml(2026, "D15610", "2035A", "A", "Joint Light Tactical Vehicle")]
    assert classes([k], modern) == {(2020, k.era_key): "A1"}


def _renamed(edition_amounts, modern_amounts):
    """One era key per edition titled 'Combat Rescue Helicopter Program',
    modern title 'Combat Rescue Helicopter' (Jaccard 3/4)."""
    era = [ek(y, "3010F", "AF", 20, "HH0600", "Combat Rescue Helicopter Program",
              act=a, enacted=e) for y, (a, e) in edition_amounts.items()]
    modern = [ml(y, "HH0600", "3010F", "F", "Combat Rescue Helicopter", act=a,
                 enacted=e) for y, (a, e) in modern_amounts.items()]
    return era, modern


def test_a2_needs_two_thirds_of_continuity_checks():
    # checks: 2021 enacted 5000 vs 2022 actuals 5100 (pass),
    #         2022 enacted 6000 vs 2023 actuals 2000 (fail: > 2x),
    #         2023 enacted 7000 vs 2024 actuals 7000 (pass) → 2/3
    era, modern = _renamed({2021: (1, 5000), 2022: (5100, 6000), 2023: (2000, 7000)},
                           {2024: (7000, None)})
    got = classes(era, modern)
    assert set(got.values()) == {"A2"}


def test_a2_fails_continuity_becomes_r1():
    # 2021→2022 fail, 2022→2023 fail, 2023→2024 pass → 1/3
    era, modern = _renamed({2021: (1, 5000), 2022: (1000, 6000), 2023: (2000, 7000)},
                           {2024: (7000, None)})
    assert set(classes(era, modern).values()) == {"R1"}


def test_a2_with_no_overlapping_checks_passes():
    era, modern = _renamed({2023: (None, None)}, {2026: (None, None)})
    assert set(classes(era, modern).values()) == {"A2"}


def test_sign_flip_fails_a_check_and_small_amounts_pass():
    # 2022→2023: 5000 vs -5000 sign flip (fail); 2021→2022: both < $1M (pass)
    era, modern = _renamed({2021: (1, 900), 2022: (-400, 5000), 2023: (-5000, None)},
                           {2026: (None, None)})
    assert set(classes(era, modern).values()) == {"R1"}       # 1/2 < 2/3


def test_low_jaccard_is_r1():
    k = ek(2018, "1611N", "NAVY", 4, "3010", "LX(R)")
    modern = [ml(2026, "3010", "1611N", "N", "LPD Flight II")]
    assert classes([k], modern) == {(2018, k.era_key): "R1"}


def test_r2_code_only_under_another_account():
    k = ek(2018, "1612N", "NAVY", 3, "1045", "OHIO Replacement Submarine")
    modern = [ml(2026, "1045", "1611N", "N", "Columbia Class Submarine")]
    assert classes([k], modern) == {(2018, k.era_key): "R2"}


def test_h_code_absent_from_modern():
    k = ek(2017, "3010F", "AF", 3, "F015E0", "F-15e")
    assert classes([k], [ml(2026, "F01500", "3010F", "F", "F-15")]) == {
        (2017, k.era_key): "H"}


def test_org_split_codes_compare_organization():
    dss = ek(2018, "0300D", "DSS", 20, "20", "Major Equipment")
    dtra = ek(2018, "0300D", "DTRA", 21, "20", "Vehicles")
    modern = [ml(2026, "20", "0300D", "DCSA", "Major Equipment"),
              ml(2026, "20", "0300D", "DTRA", "Vehicles")]
    got = classes([dss, dtra], modern, frozenset({"20"}))
    # DSS's title equals DCSA's, but the org differs: an org rename is R2
    assert got == {(2018, dss.era_key): "R2", (2018, dtra.era_key): "A1"}


def test_org_split_maps_service_org_names():
    army = ek(2019, "2035A", "ARMY", 1, "ZX0001", "Widget")
    defw = ek(2019, "2035A", "DEFW", 2, "ZX0001", "Widget")
    modern = [ml(2025, "ZX0001", "2035A", "A", "Widget")]
    got = classes([army, defw], modern)
    assert got == {(2019, army.era_key): "A1", (2019, defw.era_key): "R2"}


# ---------------------------------------------------------------------------
# build_chains
# ---------------------------------------------------------------------------

def test_build_chains_identity_keys_titles_dollars_and_sha():
    era = [
        ek(2018, "0300D", "DSS", 20, "20", "Major Equipment", act=100),
        ek(2017, "0300D", "DSS", 20, "20", "Major Equipment", act=50),
        ek(2017, "0300D", "DTRA", 21, "20", "Vehicles"),
        ek(2017, "1506N", "NAVY", 1, "0145", "Widget", act=7),
        ek(2017, "1506N", "NAVY", 2, "0145", "Widget (AP)", act=3),
    ]
    cls = {(k.edition, k.era_key): "A1" for k in era}
    cls[(2017, "0300D-DTRA-L21")] = "R2"
    chains = {c.chain_id: c for c in build_chains(era, cls)}
    assert sorted(chains) == ["0145|1506N|", "20|0300D|DSS", "20|0300D|DTRA"]
    dss = chains["20|0300D|DSS"]
    assert dss.keys == ((2017, "0300D-DSS-L20"), (2018, "0300D-DSS-L20"))
    assert (dss.first_edition, dss.last_edition, dss.n_keys) == (2017, 2018, 2)
    assert dss.actuals_k == D(150)
    assert dss.classes == frozenset({"A1"})
    assert dss.keys_sha256 == keys_sha256(
        [(2017, "0300D-DSS-L20", "01", "Major Equipment"),
         (2018, "0300D-DSS-L20", "01", "Major Equipment")])
    navy = chains["0145|1506N|"]
    assert navy.titles_by_edition == {2017: "Widget | Widget (AP)"}
    assert navy.actuals_k == D(10)
    assert chains["20|0300D|DTRA"].actuals_k == D(0)


def test_build_chains_raises_on_unclassified_key():
    with pytest.raises(KeyError):
        build_chains([ek(2017, "3010F", "AF", 1, "ATA000", "F-35")], {})


def test_title_drift_free():
    def chain(titles):
        era = [ek(2017 + i, "3010F", "AF", 1, "Q1", t) for i, t in enumerate(titles)]
        return build_chains(era, {(k.edition, k.era_key): "H" for k in era})[0]
    assert era_map.title_drift_free(chain(["F-15", "F-15 ", "f-15"]))
    assert not era_map.title_drift_free(chain(["F-15", "F-15E"]))


# ---------------------------------------------------------------------------
# apply_class_rulings — §5.2
# ---------------------------------------------------------------------------

PAGES = frozenset({
    ("3010", "1611N", "N"), ("3010", "1810N", "N"),
    ("20", "0300D", "DCSA"), ("20", "0300D", "DTRA"),
    ("30", "0300D", "OSD"), ("30", "0300D", "DTRA"), ("30", "0300D", "DMACT"),
})
COLLISION = frozenset({"3010", "20", "30"})
ON = date(2026, 10, 2)


def rule(era, cls):
    chains = build_chains(era, {(k.edition, k.era_key): c
                                for k, c in zip(era, cls)})
    rows, left = apply_class_rulings(chains, modern_pages=PAGES,
                                     collision_codes=COLLISION, decided_on=ON)
    return {r["decision_id"]: r for r in rows}, [c.chain_id for c in left]


def test_same_program_for_a1_only_chain():
    era = [ek(2017, "3010F", "AF", 1, "ATA000", "F-35", act=10),
           ek(2018, "3010F", "AF", 1, "ATA000", "F-35", act=20)]
    rows, left = rule(era, ["A1", "A1"])
    assert left == []
    row = rows["ATA000|3010F||2017-2018"]
    assert set(row) == set(SEED_COLUMNS)
    assert row["decision"] == "same_program" and row["ruling"] == RULING_SAME
    assert (row["program_account"], row["program_org"]) == ("", "")
    assert (row["first_edition"], row["last_edition"], row["n_keys"]) == ("2017", "2018", "2")
    assert row["decided_on"] == "2026-10-02" and row["decided_by"] == "owner"
    assert row["proposed_rule"] == "A1"
    assert row["titles_seen"] == "2017: F-35; 2018: F-35"
    assert row["evidence"] == "actuals_k=30"
    assert row["keys_sha256"] == keys_sha256(
        [(2017, "3010F-AF-L1", "01", "F-35"), (2018, "3010F-AF-L1", "01", "F-35")])


def test_collision_account_chain_is_pinned_to_its_page():
    rows, left = rule([ek(2019, "1611N", "NAVY", 5, "3010", "LPD Flight II")], ["A1"])
    assert left == []
    row = rows["3010|1611N||2019-2019"]
    assert (row["program_account"], row["program_org"]) == ("1611N", "N")


def test_collision_org_chain_is_pinned_to_its_org_page():
    era = [ek(2019, "0300D", "DTRA", 21, "20", "Vehicles"),
           ek(2019, "0300D", "DCSA", 20, "20", "Major Equipment")]
    rows, left = rule(era, ["A1", "A1"])
    assert left == []
    assert (rows["20|0300D|DTRA|2019-2019"]["program_org"],
            rows["20|0300D|DCSA|2019-2019"]["program_org"]) == ("DTRA", "DCSA")
    assert rows["20|0300D|DTRA|2019-2019"]["program_account"] == "0300D"


def test_collision_chain_without_a_page_leaves_the_ruling():
    era = [ek(2019, "0300D", "DODEA", 31, "30",
              "Automation/Educational Support & Logistics"),
           ek(2019, "0300D", "OSD", 30, "30", "Major Equipment, OSD")]
    rows, left = rule(era, ["A1", "A1"])
    assert left == ["30|0300D|DODEA"]
    assert list(rows) == ["30|0300D|OSD|2019-2019"]


def test_exclude_takes_precedence_over_history():
    # a CR chain is era-only and drift-free: HISTORY would match, EXCLUDE wins
    rows, left = rule([ek(2017, "2031A", "ARMY", 99, "FY2017CR", "CR Adj"),
                       ek(2018, "2031A", "ARMY", 98, "FY2017CR", "CR Adj")], ["CR", "CR"])
    assert left == []
    row = rows["FY2017CR|2031A||2017-2018"]
    assert (row["decision"], row["ruling"]) == ("exclude_placeholder", RULING_EXCLUDE)


def test_unsafe_chain_is_excluded_route_unsafe():
    rows, _ = rule([ek(2019, "0390D", "CBDP", 2, "O&M", "Operation & Maintenance")],
                   ["UNSAFE"])
    assert rows["O&M|0390D||2019-2019"]["decision"] == "exclude_route_unsafe"


def test_history_only_drift_free_vs_drifting():
    free = [ek(2017, "3010F", "AF", 3, "F0150P", "F-15"),
            ek(2018, "3010F", "AF", 3, "F0150P", "F-15 ")]
    rows, left = rule(free, ["H", "H"])
    assert rows["F0150P|3010F||2017-2018"]["decision"] == "history_only"
    assert rows["F0150P|3010F||2017-2018"]["ruling"] == RULING_HISTORY
    drifting = [ek(2017, "0300D", "DTRA", 50, "50", "Indian Financing Act"),
                ek(2019, "0300D", "DTRA", 50, "50", "DTRA Cyber Activities")]
    rows, left = rule(drifting, ["H", "H"])
    assert rows == {} and left == ["50|0300D|"]


def test_mixed_and_review_classes_are_left():
    for cls in (["A1", "A2"], ["A1", "R3"], ["R1", "R1"], ["R2", "R2"], ["A2", "A2"]):
        era = [ek(2017, "1611N", "NAVY", 4, "2086", "Ship X"),
               ek(2018, "1611N", "NAVY", 4, "2086", "Ship X")]
        rows, left = rule(era, cls)
        assert rows == {} and left == ["2086|1611N|"], cls
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run --project . pytest tests/jbooks/test_era_map.py -q`

Expected: collection error, ending
```
E   ImportError: cannot import name 'era_map' from 'govbudget.jbooks' (.../src/govbudget/jbooks/__init__.py)
1 error in 0.1s
```

- [ ] **Step 3: Create the module**

Create `src/govbudget/jbooks/era_map.py` with exactly this content (the full import block is
added now; `csv`, `json`, `Path`, `require_resolved`, `is_era_procurement_key` and
`EraKeyConflict` are used by the code Task 11 appends):

```python
"""Era (PB2017–PB2023) P-1 lines → dated program decisions (families piece 1).

Spec: docs/superpowers/specs/2026-10-02-era-procurement-history-design.md
§4.3 (the seed), §4.6 (research outputs), §5 (classes, rulings, review,
successors).

An era P-1 key ('{account}-{org}-L{line}', jbooks/era_keys.py) is ONE display
line inside ONE edition's workbook; line numbers are not identities across
editions. Column I of the same workbook row prints the budget line code
("Line Item"), which the loader keeps as budget_lines.line_item_code
(migration 021). This module never re-keys pe_bli. It records which program,
if any, each era line's PRINTED code belongs to, as decisions the owner made:

  * classify_keys   — one class per era key, first matching rule wins, in
                      CLASS_ORDER (§5.1).
  * build_chains    — keys grouped by (code, account), split by organization
                      for the codes that span organizations within one
                      edition's account (ORG_SPLIT_CODES).
  * apply_class_rulings — the three owner-approved class rulings (§5.2);
                      every other chain goes to individual review (§5.3).
  * search_successors — book-stated continuations for era-only codes (§5.4).
  * propose / ratify / check — the file-level workflow behind the
                      `govbudget era-map` CLI.

Drift guard: every decision row carries keys_sha256 over the sorted lines
'{edition}|{era_key}|{budget_activity}|{filed_title}' (blank for a missing
value), joined with '\\n', no trailing newline, sha256 hex of the UTF-8
bytes. DuckDB mirror for dbt: sha256(string_agg(line, chr(10) order by line)).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from govbudget.jbooks.collision_keys import require_resolved
from govbudget.jbooks.era_keys import is_era_procurement_key
from govbudget.jbooks.p1_loader import EraKeyConflict

# ---------------------------------------------------------------------------
# Vocabulary (binding: the seed, the dbt map and verify-era-map read these)
# ---------------------------------------------------------------------------

CLASS_ORDER = ("CR", "UNSAFE", "R3", "A1", "A2", "R1", "R2", "H")
ORG_SPLIT_CODES = frozenset({"10", "15", "20", "30", "500"})
RULING_SAME = "R-DEC-ERA-SAME"
RULING_EXCLUDE = "R-DEC-ERA-EXCLUDE"
RULING_HISTORY = "R-DEC-ERA-HISTORY"
CLASS_RULINGS = (RULING_SAME, RULING_EXCLUDE, RULING_HISTORY)
DECISIONS = (
    "same_program", "history_only", "exclude_placeholder",
    "exclude_route_unsafe", "exclude_reused_code",
)
SEED_COLUMNS = (
    "decision_id", "line_item_code", "account", "organization",
    "first_edition", "last_edition", "decision", "program_account",
    "program_org", "successor_code", "successor_account", "successor_evidence",
    "n_keys", "keys_sha256", "titles_seen", "modern_title", "proposed_rule",
    "evidence", "decided_on", "decided_by", "ruling", "note",
)
REVIEW_COLUMNS = (
    "chain_id", "first_edition", "last_edition", "titles_by_edition",
    "modern_title", "accounts", "continuity", "actuals_k",
    "proposed_decision", "reason", "program_account", "program_org",
    "successor_code", "keys_sha256", "decision", "note",
)
CHAIN_COLUMNS = (
    "chain_id", "line_item_code", "account", "organization", "first_edition",
    "last_edition", "classes", "n_keys", "keys_sha256", "actuals_k",
    "titles_by_edition", "modern_title", "title_jaccard", "continuity",
    "ruling", "decision", "left_ruling_reason", "successor_code",
    "successor_account", "successor_evidence",
)
KEY_COLUMNS = (
    "edition", "era_key", "account", "organization", "budget_activity",
    "line_number", "line_item_code", "filed_title", "chain_id", "class",
    "title_jaccard", "continuity", "actuals_k", "enacted_k",
    "source_document_sha256", "source_rows", "source_cells",
)

ERA_EDITIONS = tuple(range(2017, 2024))
MODERN_EDITIONS = (2024, 2025, 2026)
CR_CODES = frozenset({"FY2017CR", "FY2018CR"})
# Era workbooks spell the service organizations out; PB2024+ abbreviates them.
# The Defense-Wide agency codes are printed identically in both eras.
ERA_ORG_TO_MODERN = {"ARMY": "A", "NAVY": "N", "AF": "F"}
JACCARD_MIN = 0.5
# Both sides of a continuity check below $1M (amounts are $K) carry no signal.
CONTINUITY_FLOOR_K = Decimal(1000)
# The approval date of the three class rulings (spec status line, 2026-10-02).
CLASS_RULINGS_DECIDED_ON = date(2026, 10, 2)
BATCH_RE = re.compile(r"^B[1-9][0-9]*$")
CHAIN_TITLE_SEP = " | "

_TITLE_MARKERS = re.compile(r"\((?:myp|mip|space|multiyear|ap|ap-cy)\)")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# export_site.is_route_safe_pe's character set (a page slug must survive a URL).
_ROUTE_UNSAFE_CHARS = frozenset("&#/?%")


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EraKey:
    """One era P-1 key in one edition: the lake's (edition, era_key) grain."""

    edition: int
    account: str
    organization: str
    budget_activity: str | None
    era_key: str
    line_item_code: str
    filed_title: str | None
    actuals_k: Decimal | None          # fct_decade_series FY(N-2) actuals
    source_document_sha256: str
    source_cells: tuple[str, ...]
    enacted_k: Decimal | None = None   # fct_decade_series FY(N-1) enacted


@dataclass(frozen=True)
class ModernLine:
    """One PB2024–26 P-1 line identity: (edition, code, account, org, title).

    actuals_k / enacted_k are the decade-series grain of the code's page
    identity in that edition (the code alone, or code+account / code+org for
    the PB2026 collision codes) — the same values a modern page shows."""

    edition: int
    code: str
    account: str
    organization: str
    title: str | None
    actuals_k: Decimal | None = None
    enacted_k: Decimal | None = None


@dataclass(frozen=True)
class Chain:
    chain_id: str                      # '{code}|{account}|{org}' (org '' unless org-split)
    line_item_code: str
    account: str
    organization: str
    keys: tuple[tuple[int, str], ...]  # (edition, era_key), sorted
    classes: frozenset[str]
    titles_by_edition: dict[int, str]  # edition -> its filed titles, ' | '-joined
    actuals_k: Decimal
    n_keys: int
    keys_sha256: str

    @property
    def first_edition(self) -> int:
        return self.keys[0][0]

    @property
    def last_edition(self) -> int:
        return self.keys[-1][0]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def normalize_title(title: str | None) -> str:
    """Casefold, drop the (MYP)/(MIP)/(SPACE)/(MULTIYEAR)/(AP)/(AP-CY)
    markers, collapse every run of punctuation/whitespace to one space."""
    t = (title or "").casefold()
    t = _TITLE_MARKERS.sub("", t)
    return " ".join(_NON_ALNUM.sub(" ", t).split())


def title_jaccard(a: str | None, b: str | None) -> float:
    """Token-set Jaccard of the two normalized titles; 0.0 if either is empty."""
    sa, sb = set(normalize_title(a).split()), set(normalize_title(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def keys_sha256(lines: Iterable[tuple[int, str, str | None, str | None]]) -> str:
    """The drift guard over (edition, era_key, budget_activity, filed_title)."""
    rendered = sorted(
        f"{edition}|{era_key}|{ba or ''}|{title or ''}"
        for edition, era_key, ba, title in lines
    )
    return hashlib.sha256("\n".join(rendered).encode("utf-8")).hexdigest()


def is_route_safe_code(code: str) -> bool:
    return not (set(code) & _ROUTE_UNSAFE_CHARS or any(c.isspace() for c in code))


def org_split_codes(era: Iterable[EraKey]) -> frozenset[str]:
    """Codes printed by more than one organization inside one edition's account."""
    orgs: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    for k in era:
        orgs[(k.edition, k.account, k.line_item_code)].add(k.organization)
    return frozenset(code for (_e, _a, code), o in orgs.items() if len(o) > 1)


def chain_id(code: str, account: str, organization: str) -> str:
    return f"{code}|{account}|{organization}"


def parse_chain_id(cid: str) -> tuple[str, str, str]:
    parts = cid.split("|")
    if len(parts) != 3 or not parts[0] or not parts[1]:
        raise ValueError(f"malformed chain_id {cid!r} (want 'code|account|org')")
    return parts[0], parts[1], parts[2]


def _chain_org(code: str, organization: str, split: frozenset[str]) -> str:
    return organization if code in split else ""


def _modern_org(organization: str) -> str:
    return ERA_ORG_TO_MODERN.get(organization, organization)


def _fmt_k(value: Decimal | None) -> str:
    if value is None:
        return ""
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


# ---------------------------------------------------------------------------
# Classification (§5.1)
# ---------------------------------------------------------------------------


@dataclass
class _ModernIdent:
    titles: set[str] = field(default_factory=set)
    norm_titles: set[str] = field(default_factory=set)
    editions: set[int] = field(default_factory=set)
    amounts: dict[tuple[int, str], Decimal] = field(default_factory=dict)
    latest_title: tuple[int, str] | None = None


class _Context:
    """Everything classification and review context derive from (era, modern)."""

    def __init__(self, era: Sequence[EraKey], modern: Sequence[ModernLine]):
        self.era = list(era)
        self.split = org_split_codes(self.era)
        self.idx: dict[tuple[str, str, str], _ModernIdent] = {}
        self.modern_codes: set[str] = set()
        self.modern_accounts: dict[str, set[str]] = defaultdict(set)
        self.line_idents: set[tuple[str, str, str]] = set()
        for m in sorted(modern, key=lambda m: (m.edition, m.code, m.account,
                                               m.organization, m.title or "")):
            self.modern_codes.add(m.code)
            self.modern_accounts[m.code].add(m.account)
            self.line_idents.add((m.code, m.account, m.organization))
            ident = (m.code, m.account,
                     m.organization if m.code in self.split else "")
            mi = self.idx.setdefault(ident, _ModernIdent())
            mi.editions.add(m.edition)
            if m.title is not None:
                mi.titles.add(m.title)
                mi.norm_titles.add(normalize_title(m.title))
                if mi.latest_title is None or m.edition >= mi.latest_title[0]:
                    mi.latest_title = (m.edition, m.title)
            for kind, value in (("actuals", m.actuals_k), ("enacted", m.enacted_k)):
                if value is not None:
                    mi.amounts.setdefault((m.edition, kind), value)
        self.accounts_in_edition: dict[tuple[int, str], set[str]] = defaultdict(set)
        self.era_by_ident: dict[tuple[str, str, str], list[EraKey]] = defaultdict(list)
        for k in self.era:
            self.accounts_in_edition[(k.edition, k.line_item_code)].add(k.account)
            self.era_by_ident[self.ident(k)].append(k)
        self._continuity: dict[tuple[str, str, str], tuple[int, int]] = {}

    def ident(self, k: EraKey) -> tuple[str, str, str]:
        code = k.line_item_code
        return (code, k.account,
                _modern_org(k.organization) if code in self.split else "")

    def continuity(self, ident: tuple[str, str, str]) -> tuple[int, int]:
        """(passed, total) checks: edition y's FY(y-1) enacted vs edition y+1's
        FY(y-1) actuals, y = 2017..2025, on the ident's era sum + modern grain.
        A check passes when both are under $1M, or they share a sign and the
        smaller is at least half the larger (within 2x)."""
        if ident in self._continuity:
            return self._continuity[ident]
        series: dict[tuple[int, str], Decimal] = {}
        for k in self.era_by_ident.get(ident, ()):
            for kind, value in (("actuals", k.actuals_k), ("enacted", k.enacted_k)):
                if value is not None:
                    series[(k.edition, kind)] = series.get((k.edition, kind), Decimal(0)) + value
        mi = self.idx.get(ident)
        if mi is not None:
            series.update(mi.amounts)
        passed = total = 0
        for y in range(ERA_EDITIONS[0], MODERN_EDITIONS[-1]):
            enacted, actuals = series.get((y, "enacted")), series.get((y + 1, "actuals"))
            if enacted is None or actuals is None:
                continue
            total += 1
            hi = max(abs(enacted), abs(actuals))
            if hi < CONTINUITY_FLOOR_K:
                passed += 1
            elif min(abs(enacted), abs(actuals)) * 2 >= hi and (enacted >= 0) == (actuals >= 0):
                passed += 1
        self._continuity[ident] = (passed, total)
        return passed, total

    def best_jaccard(self, k: EraKey) -> float | None:
        mi = self.idx.get(self.ident(k))
        if mi is None:
            return None
        return max((title_jaccard(k.filed_title, t) for t in mi.titles), default=0.0)

    def classify(self, k: EraKey, collision_codes: frozenset[str]) -> str:
        code = k.line_item_code
        if code in CR_CODES:
            return "CR"
        if not is_route_safe_code(code):
            return "UNSAFE"
        mi = self.idx.get(self.ident(k))
        if mi is not None:
            if (len(self.accounts_in_edition[(k.edition, code)]) > 1
                    and code not in collision_codes):
                return "R3"
            if normalize_title(k.filed_title) in mi.norm_titles:
                return "A1"
            passed, total = self.continuity(self.ident(k))
            if (self.best_jaccard(k) or 0.0) >= JACCARD_MIN and (
                    total == 0 or passed * 3 >= total * 2):
                return "A2"
            return "R1"
        if code in self.modern_codes:
            return "R2"
        return "H"


def classify_keys(
    era: Sequence[EraKey], modern: Sequence[ModernLine], *,
    collision_codes: frozenset[str],
) -> dict[tuple[int, str], str]:
    """{(edition, era_key): class} under CLASS_ORDER (§5.1; first match wins):

    CR      code is a FY2017CR/FY2018CR continuing-resolution placeholder;
    UNSAFE  code is not route-safe ('O&M', 'RDT&E' in 0390D);
    R3      (code, account[, org]) exists in PB2024–26, the code spans accounts
            inside this era edition, and it is not a PB2026 collision code;
    A1      (code, account[, org]) exists in PB2024–26 and the normalized
            title equals one of its normalized modern titles;
    A2      it exists, best title Jaccard ≥ 0.5, and at least 2/3 of the
            continuity checks pass (no checks counts as passing);
    R1      it exists (title drift beyond A2);
    R2      the code exists in PB2024–26 only under another account/org;
    H       the code is absent from PB2024–26.

    [, org] applies to org-split codes only (organization compared after
    ERA_ORG_TO_MODERN)."""
    ctx = _Context(era, modern)
    return {(k.edition, k.era_key): ctx.classify(k, collision_codes) for k in ctx.era}


# ---------------------------------------------------------------------------
# Chains (§5.2)
# ---------------------------------------------------------------------------


def group_keys(era: Sequence[EraKey]) -> dict[str, list[EraKey]]:
    """{chain_id: [EraKey, ...] sorted by (edition, era_key)}."""
    split = org_split_codes(era)
    groups: dict[str, list[EraKey]] = defaultdict(list)
    for k in era:
        groups[chain_id(k.line_item_code, k.account,
                        _chain_org(k.line_item_code, k.organization, split))].append(k)
    for keys in groups.values():
        keys.sort(key=lambda k: (k.edition, k.era_key))
    return dict(groups)


def range_sha(keys: Sequence[EraKey], first: int, last: int) -> tuple[int, str]:
    """(n_keys, keys_sha256) of the keys whose edition is in [first, last]."""
    inside = [k for k in keys if first <= k.edition <= last]
    return len(inside), keys_sha256(
        (k.edition, k.era_key, k.budget_activity, k.filed_title) for k in inside
    )


def build_chains(
    era: Sequence[EraKey], classes: Mapping[tuple[int, str], str],
) -> list[Chain]:
    """One Chain per (code, account[, org]); sorted by chain_id. Raises
    KeyError if a key has no class."""
    chains = []
    for cid, keys in group_keys(era).items():
        code, account, org = parse_chain_id(cid)
        titles: dict[int, set[str]] = defaultdict(set)
        for k in keys:
            titles[k.edition].add(k.filed_title or "")
        n_keys, sha = range_sha(keys, keys[0].edition, keys[-1].edition)
        chains.append(Chain(
            chain_id=cid, line_item_code=code, account=account, organization=org,
            keys=tuple((k.edition, k.era_key) for k in keys),
            classes=frozenset(classes[(k.edition, k.era_key)] for k in keys),
            titles_by_edition={e: CHAIN_TITLE_SEP.join(sorted(t))
                               for e, t in sorted(titles.items())},
            actuals_k=sum((k.actuals_k or Decimal(0) for k in keys), Decimal(0)),
            n_keys=n_keys, keys_sha256=sha,
        ))
    return sorted(chains, key=lambda c: c.chain_id)


def title_drift_free(chain: Chain) -> bool:
    """True when every filed title of the chain normalizes to one string."""
    return len({
        normalize_title(t)
        for v in chain.titles_by_edition.values()
        for t in v.split(CHAIN_TITLE_SEP)
    }) == 1


def collision_page(
    chain: Chain, modern_pages: frozenset[tuple[str, str, str]],
) -> tuple[str, str] | None:
    """The ONE PB2026 page (account, org) a collision-code chain joins: same
    code and account, and — for an org-split chain — the same organization.
    None when no page (or more than one) matches."""
    org = _modern_org(chain.organization)
    hits = sorted(
        (a, o) for (c, a, o) in modern_pages
        if c == chain.line_item_code and a == chain.account
        and (not chain.organization or o == org)
    )
    return hits[0] if len(hits) == 1 else None


def class_ruling(
    chain: Chain, *, modern_pages: frozenset[tuple[str, str, str]],
    collision_codes: frozenset[str],
) -> tuple[str, str, str, str] | None:
    """(ruling, decision, program_account, program_org), or None when the
    chain needs an individual decision. R-DEC-ERA-EXCLUDE takes precedence."""
    if "CR" in chain.classes:
        return (RULING_EXCLUDE, "exclude_placeholder", "", "")
    if "UNSAFE" in chain.classes:
        return (RULING_EXCLUDE, "exclude_route_unsafe", "", "")
    if chain.classes == frozenset({"A1"}):
        if chain.line_item_code in collision_codes:
            page = collision_page(chain, modern_pages)
            if page is None:
                return None
            return (RULING_SAME, "same_program", page[0], page[1])
        return (RULING_SAME, "same_program", "", "")
    if chain.classes == frozenset({"H"}) and title_drift_free(chain):
        return (RULING_HISTORY, "history_only", "", "")
    return None


def _proposed_rule(classes: Iterable[str]) -> str:
    present = set(classes)
    return "+".join(c for c in CLASS_ORDER if c in present)


def _titles_seen(chain: Chain, first: int, last: int) -> str:
    return "; ".join(f"{e}: {t}" for e, t in sorted(chain.titles_by_edition.items())
                     if first <= e <= last)


def seed_row(
    chain: Chain, *, first: int, last: int, n_keys: int, keys_sha: str,
    decision: str, ruling: str, decided_on: date, program_account: str = "",
    program_org: str = "", successor: Mapping[str, str] | None = None,
    modern_title: str = "", evidence: str = "", note: str = "",
) -> dict[str, str]:
    successor = successor or {}
    return {
        "decision_id": f"{chain.chain_id}|{first}-{last}",
        "line_item_code": chain.line_item_code,
        "account": chain.account,
        "organization": chain.organization,
        "first_edition": str(first),
        "last_edition": str(last),
        "decision": decision,
        "program_account": program_account,
        "program_org": program_org,
        "successor_code": successor.get("successor_code", ""),
        "successor_account": successor.get("successor_account", ""),
        "successor_evidence": successor.get("successor_evidence", ""),
        "n_keys": str(n_keys),
        "keys_sha256": keys_sha,
        "titles_seen": _titles_seen(chain, first, last),
        "modern_title": modern_title,
        "proposed_rule": _proposed_rule(chain.classes),
        "evidence": evidence or f"actuals_k={_fmt_k(chain.actuals_k)}",
        "decided_on": decided_on.isoformat(),
        "decided_by": "owner",
        "ruling": ruling,
        "note": note,
    }


def apply_class_rulings(
    chains: Sequence[Chain], *, modern_pages: frozenset[tuple[str, str, str]],
    collision_codes: frozenset[str], decided_on: date,
) -> tuple[list[dict], list[Chain]]:
    """(seed rows for the class-ruled chains, chains left for review)."""
    rows, left = [], []
    for ch in chains:
        rule = class_ruling(ch, modern_pages=modern_pages,
                            collision_codes=collision_codes)
        if rule is None:
            left.append(ch)
            continue
        ruling, decision, pa, po = rule
        rows.append(seed_row(
            ch, first=ch.first_edition, last=ch.last_edition, n_keys=ch.n_keys,
            keys_sha=ch.keys_sha256, decision=decision, ruling=ruling,
            decided_on=decided_on, program_account=pa, program_org=po,
        ))
    return rows, left
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run --project . pytest tests/jbooks/test_era_map.py -q`

Expected: `49 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/jbooks/era_map.py GovBudget/tests/jbooks/test_era_map.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era-map): era P-1 key classes, chains and the three class rulings (families piece 1, spec §5.1-5.2)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
