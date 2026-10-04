"""scripts/era/fact_stability.py — V6 of the S4 A/B proof (Task 21, spec §8, §10)."""
import json

import duckdb
import pytest

from era.fact_stability import (  # scripts/ is on sys.path via conftest
    F15_A1_LEAVES,
    compare_citations,
    compare_decade_rows,
    f15_a1_leaves,
    main,
)

WB = dict(kind="workbook", units="USD thousands", amount_thousands=10.0, sha256="a" * 64, sheet="Exhibit P-1",
          cells="J10", official_url="https://comptroller.war.gov/p1.xlsx",
          retrieved_at="2026-07-03T07:44:15.975561-04:00", pe_bli="F01500")
DV = dict(kind="derived", units="USD thousands", recorded_value="10.000", formula="sum(budget_lines.amount_thousands)",
          inputs='["w1"]', retrieved_at="2026-10-02T01:26:11.150859+00:00", pe_bli=None)
LEAF_A = {**WB, "pe_bli": None, "retrieved_at": "2026-07-03 07:44:15.975561-04:00"}
LEAF_B = {**WB, "pe_bli": "F01500", "retrieved_at": "2026-07-03T07:44:15.975561-04:00"}
LEAVES = {"f1": "F01500"}


def a_side():
    return {"w1": dict(WB), "d1": dict(DV), "f1": dict(LEAF_A)}


def b_side():
    return {"w1": dict(WB), "d1": {**DV, "retrieved_at": "2026-10-09T03:00:00+00:00"}, "f1": dict(LEAF_B), "n1": dict(WB)}


def test_b_may_restamp_run_times_and_the_f15_leaves_and_add_facts():
    report = compare_citations(a_side(), b_side(), LEAVES, expected_f15=1)
    assert report["ok"], report
    assert (report["new_in_b"], report["f15_restamped"]) == (1, 1)


@pytest.mark.parametrize("fid, field, value", [
    ("w1", "retrieved_at", "2026-07-04T00:00:00-04:00"),
    ("w1", "amount_thousands", 11.0),
    ("w1", "pe_bli", None),
    ("d1", "inputs", '["w1", "w2"]'),
    ("d1", "recorded_value", "11.000"),
    ("f1", "cells", "J11"),
])
def test_any_other_field_change_fails(fid, field, value):
    b = b_side()
    b[fid][field] = value
    report = compare_citations(a_side(), b, LEAVES, expected_f15=1)
    assert not report["ok"]
    assert any(c["fact_id"] == fid and c["field"] == field for c in report["changed"])


def test_a_fact_missing_from_b_fails():
    b = b_side()
    del b["w1"]
    report = compare_citations(a_side(), b, LEAVES, expected_f15=1)
    assert not report["ok"] and report["missing"] == ["w1"]


def test_an_f15_leaf_the_decade_tier_did_not_mint_fails():
    b = b_side()
    b["f1"] = dict(LEAF_A)
    report = compare_citations(a_side(), b, LEAVES, expected_f15=1)
    assert not report["ok"] and report["f15_restamped"] == 0


def test_the_restamp_must_cover_exactly_the_expected_leaves():
    assert F15_A1_LEAVES == 72
    assert not compare_citations(a_side(), b_side(), LEAVES)["ok"]


def test_f15_leaves_are_era_keys_on_a1_code_rows_only():
    history = {"programs": [{"id": "P1", "code": "F01500"}, {"id": "P2", "code": "F0150P"}, {"id": "P3", "code": "F015EX"}],
               "points": [{"components": [
                   {"pe_bli": "3010F-AF-L21", "program_id": "P1", "fact_id": "a"},
                   {"pe_bli": "3010F-AF-L69", "program_id": "P2", "fact_id": "b"},
                   {"pe_bli": "F015EX", "program_id": "P3", "fact_id": "c"},
                   {"pe_bli": "3010F-AF-L5", "program_id": "P3", "fact_id": "d"}]}]}
    assert f15_a1_leaves(history) == {"a": "F01500", "d": "F015EX"}


def parquet(path, rows, amount_type="double"):
    con = duckdb.connect()
    con.execute(f"create table t (fact_id varchar, pe_bli varchar, amount_thousands {amount_type})")
    con.executemany("insert into t values (?, ?, ?)", rows)
    con.execute(f"copy t to '{path}' (format parquet)")
    con.close()


def test_every_decade_row_of_a_ships_unchanged_in_b(tmp_path):
    a, b, bad, retyped = (tmp_path / f"{n}.parquet" for n in ("a", "b", "bad", "retyped"))
    parquet(a, [("f1", "3010F-AF-L21", 10.0), ("f2", "0207134F", 5.0)])
    parquet(b, [("f2", "0207134F", 5.0), ("f3", "3010F-AF-L4", 1.0), ("f1", "3010F-AF-L21", 10.0)])
    parquet(bad, [("f1", "3010F-AF-L21", 10.5), ("f2", "0207134F", 5.0)])
    parquet(retyped, [("f1", "3010F-AF-L21", 10.0), ("f2", "0207134F", 5.0)], amount_type="decimal(18,3)")
    assert compare_decade_rows(a, b)["ok"]
    report = compare_decade_rows(a, bad)
    assert not report["ok"] and report["lost_fact_ids"] == ["f1"]
    assert not compare_decade_rows(a, retyped)["schema_equal"]


def site(root, citations, history, rows):
    (root / "json").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "json" / "citations.json").write_text(json.dumps(citations))
    (root / "json" / "f15_funding_history.json").write_text(json.dumps(history))
    parquet(root / "data" / "budget_lines_decade.parquet", rows)
    return root


def test_cli_reads_two_site_trees(tmp_path):
    history = {"programs": [{"id": "P1", "code": "F01500"}],
               "points": [{"components": [{"pe_bli": "3010F-AF-L21", "program_id": "P1", "fact_id": "f1"}]}]}
    rows = [("f1", "3010F-AF-L21", 10.0)]
    a = site(tmp_path / "a", a_side(), history, rows)
    b = site(tmp_path / "b", b_side(), history, rows + [("n1", "F01500", 10.0)])
    assert main(["--a", str(a), "--b", str(b), "--expected-f15", "1", "--report", str(tmp_path / "r.json")]) == 0
    assert json.loads((tmp_path / "r.json").read_text())["citations"]["new_in_b"] == 1
    assert main(["--a", str(b), "--b", str(a), "--expected-f15", "1"]) == 1


# Task 21 fix: two exports of ONE code and ONE snapshot (B vs B2) differ in 130
# citation fields by export noise alone; V6 judges them with proof diff's rules.
INPUTS_CLASS = {"path": "json/citations.json", "pointer": "/{fid}/inputs", "count": 1}


DFID = "0123456789abcdef"  # reorder classes key real 16-hex fact IDs as {fid}


def reordered():
    a, b = a_side(), b_side()
    a[DFID] = {**DV, "inputs": '["w1", "w2"]'}
    b[DFID] = {**DV, "inputs": '["w2", "w1"]'}
    return a, b


def test_a_reorder_reads_changed_unless_a_control_vouched_for_its_class():
    a, b = reordered()
    report = compare_citations(a, b, LEAVES, expected_f15=1)
    assert not report["ok"] and [c["field"] for c in report["changed"]] == ["inputs"]
    other = {"path": "json/citations.json", "pointer": "/{fid}/query_body"}
    assert not compare_citations(a, b, LEAVES, expected_f15=1, noise_classes=[other])["ok"]
    report = compare_citations(a, b, LEAVES, expected_f15=1, noise_classes=[INPUTS_CLASS])
    assert report["ok"], report
    assert report["noise_equivalent"] == {"inputs": 1}
    assert report["reorder_classes_trusted"] == [{"path": "json/citations.json", "pointer": "/{fid}/inputs", "count": 1}]


def test_a_vouched_class_never_excuses_a_changed_input_set():
    a, b = reordered()
    b[DFID]["inputs"] = '["w2", "w3"]'
    assert not compare_citations(a, b, LEAVES, expected_f15=1, noise_classes=[INPUTS_CLASS])["ok"]


def test_numeric_text_equal_to_12_significant_digits_is_noise():
    a, b = a_side(), b_side()
    a["d1"]["recorded_value"], b["d1"]["recorded_value"] = "3872766113006.810", "3872766113006.812"
    report = compare_citations(a, b, LEAVES, expected_f15=1)
    assert report["ok"] and report["noise_equivalent"] == {"recorded_value": 1}
    b["d1"]["recorded_value"] = "3872766200000.000"
    assert not compare_citations(a, b, LEAVES, expected_f15=1)["ok"]


def test_cli_reads_a_noise_file(tmp_path):
    from govbudget.proof import NOISE_FILE_SCHEMA, NOISE_POINTER_GENERALISATION, _classes_sha256

    history = {"programs": [{"id": "P1", "code": "F01500"}],
               "points": [{"components": [{"pe_bli": "3010F-AF-L21", "program_id": "P1", "fact_id": "f1"}]}]}
    rows = [("f1", "3010F-AF-L21", 10.0)]
    ca, cb = reordered()
    a = site(tmp_path / "a", ca, history, rows)
    b = site(tmp_path / "b", cb, history, rows)
    classes = [INPUTS_CLASS]
    noise = tmp_path / "noise.json"
    noise.write_text(json.dumps({"schema_version": NOISE_FILE_SCHEMA, "verdict": "EQUAL", "a": "B", "b": "B2",
                                 "pointer_generalisation": NOISE_POINTER_GENERALISATION,
                                 "classes_sha256": _classes_sha256(classes), "classes": classes}))
    args = ["--a", str(a), "--b", str(b), "--expected-f15", "1"]
    assert main(args) == 1
    assert main(args + ["--noise-from", str(noise)]) == 0
