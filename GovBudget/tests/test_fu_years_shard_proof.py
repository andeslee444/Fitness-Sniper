"""scripts/fu/years_shard_proof.py — P2b, the /years/ shard proof (follow-ups Task 21b)."""
import copy
import json

from fu.years_shard_proof import main, run  # scripts/ is on sys.path

BUILD = "b" * 64
COLS = [{"edition": 2017, "fy": 2015, "key": "fy2015a", "kind": "actuals", "measures": ["actuals-base-oco"]},
        {"edition": 2026, "fy": 2024, "key": "fy2024a", "kind": "actuals", "measures": ["actuals"]},
        {"edition": 2026, "fy": 2026, "key": "fy2026r", "kind": "request"}]


def cell(fid, v):
    return {"fid": fid, "v": v}


def point(kind, edition, fy, fid, v):
    return {"basis": "toa", "edition": edition, "fid": fid, "fy": fy, "measure": kind, "v": v}


def v1(rows_by_org):
    return {"amount_types": ["fy_2024_actuals", "fy_2025_total", "fy_2026_total"],
            "decade_columns": COLS, "decade_default_columns": ["fy2015a", "fy2024a", "fy2026r"],
            "default_columns": ["fy_2024_actuals", "fy_2026_total"], "delta_columns": ["fy2526_change"],
            "orgs": [{"org": org, "programs": rows} for org, rows in rows_by_org.items()],
            "program_units": "USD thousands", "project_scenarios": {}, "project_units": "USD millions",
            "schema_version": 1}


R1 = {"pe_bli": "0207134F", "title": "F-15E Squadrons", "projects": [],
      "cells": {"fy2015a": cell("1000000000000001", 10.0), "fy2024a": cell("1000000000000002", 20.0),
                "fy2026r": cell("1000000000000003", 30.0)}}
P1 = {"pe_bli": "F01500", "title": "F-15", "projects": [],
      "cells": {"fy2024a": cell("2000000000000002", 5.0), "fy2026r": cell("2000000000000003", 4.0)}}
SPLIT = {"pe_bli": "20", "slug": "20-DCSA", "title": "Major Equipment", "projects": [],
         "cells": {"fy_2024_actuals": cell("3000000000000009", 2135.0)}}
SIDECARS = {
    "0207134F": {"actuals": [point("actuals", 2017, 2015, "1000000000000001", 10.0),
                             point("actuals", 2026, 2024, "1000000000000002", 20.0)],
                 "request": [point("request", 2026, 2026, "1000000000000003", 30.0)]},
    "F01500": {"actuals": [point("actuals", 2017, 2015, "2000000000000001", 498314.0),
                           point("actuals", 2026, 2024, "2000000000000002", 5.0)],
               "request": [point("request", 2026, 2026, "2000000000000003", 4.0)]},
    "20-DCSA": {"actuals": [point("actuals", 2017, 2015, "3000000000000001", 1.0),
                            point("actuals", 2026, 2024, "3000000000000002", 2135.0)]},
}


def a_payload():
    return v1({"AF": [copy.deepcopy(R1), copy.deepcopy(P1)], "DCSA": [copy.deepcopy(SPLIT)]})


def b_payload():
    p = a_payload()
    af, dcsa = p["orgs"][0]["programs"], p["orgs"][1]["programs"]
    af[1]["cells"]["fy2015a"] = cell("2000000000000001", 498314.0)          # era cell, fence lifted
    dcsa[0]["cells"]["fy2015a"] = cell("3000000000000001", 1.0)            # org-split row: era cell
    dcsa[0]["cells"]["fy2024a"] = cell("3000000000000002", 2135.0)         # org-split row: modern cell
    dcsa[0]["cells"]["fy_2025_total"] = cell("3000000000000010", 2191.0)   # org-split row: amount type
    return p


def stub_merge(core, decade, detail):
    merged = {k: v for k, v in core.items() if k not in ("build_id", "shards")}
    merged["schema_version"] = 1
    return merged


def write(root, a=None, b=None, *, ids=(BUILD, BUILD, BUILD)):
    (root / "json" / "years_matrix").mkdir(parents=True)
    (root / "json" / "program_details").mkdir()
    if a is not None:
        (root / "json" / "years_matrix.json").write_text(json.dumps(a))
    if b is not None:
        core = {**b, "schema_version": 2, "build_id": ids[0]}
        (root / "json" / "years_matrix.json").write_text(json.dumps(core))
        (root / "json" / "years_matrix" / "decade.json").write_text(json.dumps({"build_id": ids[1]}))
        (root / "json" / "years_matrix" / "detail.json").write_text(json.dumps({"build_id": ids[2]}))
    for slug, series in SIDECARS.items():
        (root / "json" / "program_details" / f"{slug}.json").write_text(json.dumps({"decade_series": series}))
    return root


def proof(tmp_path, b, **kw):
    a_site = write(tmp_path / "a", a=a_payload())
    b_site = write(tmp_path / "b", b=b, **kw)
    return run(a_site, b_site, merge=stub_merge, max_bytes=4 * 1024 * 1024, core_gzip_max=780_074)


def test_lifted_fence_and_org_split_fix_pass_and_are_counted(tmp_path):
    report = proof(tmp_path, b_payload())
    assert report["ok"], report["violations"]
    assert report["decade_cells_added"] == {"era": 2, "modern": 1, "era_default": 2, "modern_default": 1,
                                            "era_org_split": 1, "modern_org_split": 1}
    assert report["org_split_nondecade_added"] == {"20-DCSA": ["fy_2025_total"]}
    assert report["panel"]["a"]["programs"] == 1 and report["panel"]["b"]["programs"] == 2
    assert report["panel"]["b"]["fy2024a_to_fy2026r_pct"] == round(100 * (34.0 - 25.0) / 25.0, 2)


def test_a_cell_the_sidecar_lacks_or_a_missing_cell_fails_leg_j(tmp_path):
    b = b_payload()
    b["orgs"][0]["programs"][0]["cells"]["fy2026r"] = cell("1000000000000099", 30.0)
    report = proof(tmp_path, b)
    assert any("leg j fy2026r" in v for v in report["violations"]) and report["leg_j_mismatches"] == 1
    b = b_payload()
    del b["orgs"][0]["programs"][1]["cells"]["fy2015a"]
    assert proof(tmp_path / "2", b)["leg_j_mismatches"] == 1


def test_a_changed_a_cell_and_a_stray_non_decade_cell_fail(tmp_path):
    b = b_payload()
    b["orgs"][0]["programs"][1]["cells"]["fy2024a"] = cell("2000000000000002", 6.0)
    assert any("A cell fy2024a changed" in v for v in proof(tmp_path, b)["violations"])
    b = b_payload()
    b["orgs"][0]["programs"][1]["cells"]["fy_2025_total"] = cell("2000000000000010", 1.0)
    assert "F01500: B adds non-decade cells ['fy_2025_total']" in proof(tmp_path / "2", b)["violations"]


def test_build_ids_must_agree_and_caps_hold(tmp_path):
    report = proof(tmp_path, b_payload(), ids=(BUILD, BUILD, "c" * 64))
    assert any(v.startswith("build_id differs") for v in report["violations"])
    a_site = write(tmp_path / "x" / "a", a=a_payload())
    b_site = write(tmp_path / "x" / "b", b=b_payload())
    report = run(a_site, b_site, merge=stub_merge, max_bytes=100, core_gzip_max=10)
    assert any("over the 100-byte cap" in v for v in report["violations"])
    assert any("gzip bytes, over 10" in v for v in report["violations"])


def test_the_real_split_round_trips_through_the_proof(tmp_path):
    """Task 13's split_years_matrix and merge_years_matrix, end to end: B = split(A) adds nothing."""
    from govbudget.export_site import _canonical_json_bytes, split_years_matrix

    payload = a_payload()
    a_site = write(tmp_path / "a", a=payload)
    b_site = tmp_path / "b"
    (b_site / "json" / "program_details").mkdir(parents=True)
    for rel, obj in split_years_matrix(copy.deepcopy(payload)).items():
        (b_site / "json" / rel).parent.mkdir(parents=True, exist_ok=True)
        (b_site / "json" / rel).write_bytes(_canonical_json_bytes(obj))
    for slug, series in SIDECARS.items():
        (b_site / "json" / "program_details" / f"{slug}.json").write_text(json.dumps({"decade_series": series}))
    report = run(a_site, b_site)
    # F01500's and 20-DCSA's sidecar points have no cell in A, so leg j counts them: exactly those three.
    assert report["leg_j_mismatches"] == 3, report["violations"]
    assert report["decade_cells_added"]["era"] == 0 and report["rows"] == {"a": 3, "b": 3}
    assert not [v for v in report["violations"] if "build_id" in v or "shard manifest" in v or "header" in v]


def test_cli(tmp_path, capsys):
    a_site = write(tmp_path / "a", a=a_payload())
    write(tmp_path / "b", b=b_payload())
    assert main(["--a", str(a_site), "--b", str(tmp_path / "nope")]) == 2
    assert "years-shard-proof: ERROR — " in capsys.readouterr().err
