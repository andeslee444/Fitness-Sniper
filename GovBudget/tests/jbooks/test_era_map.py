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


def test_a2_with_no_overlapping_checks_is_r1_not_a2():
    # Fix round 1 (Task 11 review, binding ruling): zero continuity checks is
    # NOT evidence of continuity. A high-jaccard rename with no checks at all
    # used to pass vacuously (total == 0 counted as "holds"); it must now
    # fall through to R1, same as any other unverified rename.
    era, modern = _renamed({2023: (None, None)}, {2026: (None, None)})
    assert set(classes(era, modern).values()) == {"R1"}


def test_modern_only_continuity_checks_do_not_count_toward_a2():
    # Fix round 1: a check between two PB2024-26 editions (y = 2024 or 2025)
    # compares the modern program against itself and is not era-side
    # evidence. Era-anchored check (2021 enacted 5000 vs 2022 actuals 5100)
    # is the only one that used to matter; old code also counted two
    # modern-only checks (2024 enacted 5000 vs 2025 actuals 5000, pass; 2025
    # enacted 4000 vs 2026 actuals 4100, pass), diluting 0/1 real failures
    # into a vacuous-looking 2/3 pass. New code must drop both and classify
    # on the one real check alone.
    era, modern = _renamed(
        {2021: (1, 6000)},
        {2022: (2000, None), 2024: (None, 5000), 2025: (5000, 4000), 2026: (4100, None)})
    assert set(classes(era, modern).values()) == {"R1"}       # 0/1 era-anchored


def test_a2_with_genuine_era_side_continuity_still_classifies_a2():
    # Fix round 1 regression guard: real era-anchored checks (y = 2017..2023)
    # are unaffected by the fix. 2021 enacted 5000 vs 2022 actuals 5100
    # (pass), 2023 enacted 7000 vs 2024 actuals 7000 (pass) -> 2/2 real
    # evidence -> A2, same as before the fix.
    era, modern = _renamed({2021: (1, 5000), 2023: (2000, 7000)},
                           {2022: (5100, None), 2024: (7000, None)})
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
