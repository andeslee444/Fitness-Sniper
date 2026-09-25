from govbudget.dossiers.editorial_review import resolve_evidence, deterministic_checks


def test_locator_never_substitutes_an_unrelated_narrative():
    details = {"narratives": [{"fact_id": "other", "body": "Delivered everything."}]}
    evidence = resolve_evidence("a", details, {"a": {"kind": "workbook"}})
    assert evidence["resolution"] == "locator_only"
    assert evidence["records"] == []
    assert deterministic_checks("Delivered everything", evidence)["flags"] == ["exact_cited_record_unavailable"]


def test_missing_citation_and_recursive_inputs_are_explicit():
    assert resolve_evidence("missing", {}, {})["resolution"] == "missing_citation"
    a, b = "a" * 16, "b" * 16
    evidence = resolve_evidence(a, {}, {a: {"inputs": [b]}, b: {"inputs": [a]}})
    assert evidence["inputs"][0]["inputs"][0]["resolution"] == "cycle_or_depth_limit"


def test_spending_wording_is_flagged_against_authority_not_silently_rewritten():
    claim = "Actual amounts spent"
    evidence = resolve_evidence("a", {"budget_lines": [{"fact_id": "a", "basis": "toa", "measure": "actuals"}]}, {"a": {"kind": "workbook"}})
    checks = deterministic_checks(claim, evidence)
    assert checks["citation_resolves"]
    assert "budget_authority_as_spending_wording" in checks["flags"]
    assert claim == "Actual amounts spent"


def test_spending_wording_follows_derived_inputs_without_rewriting_the_claim():
    a, b = "a" * 16, "b" * 16
    evidence = resolve_evidence(a, {"budget_lines": [{"fact_id": b, "basis": "toa", "measure": "actuals"}]},
                                {a: {"kind": "derived", "inputs": [b]}, b: {"kind": "workbook"}})
    assert "budget_authority_as_spending_wording" in deterministic_checks("Actual amounts spent", evidence)["flags"]


def test_malformed_input_container_does_not_crash_or_invent_evidence():
    evidence = resolve_evidence("a", {}, {"a": {"inputs": "42"}})
    assert evidence["resolution"] == "locator_only"
    assert evidence["inputs"] == []
