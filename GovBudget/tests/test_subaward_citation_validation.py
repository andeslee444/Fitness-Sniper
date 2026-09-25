"""Reject fabricated amounts or mismatched prime-award context in link evidence."""
import json

import duckdb
import pytest

from govbudget.verify_phase5b1 import (
    _verify_subaward,
    citation_gate5b1,
    integrity_gate5b1,
)


def evidence(**changes):
    row = dict(
        fact_id="1234567890abcdef", kind="subaward", units=None,
        official_url="https://www.usaspending.gov/award/CONT_AWD_N0017818F3011_9700_N0017814D7650_9700/",
        query_body=json.dumps(dict(subaward_number="10977 REL 1", subawardee="VT MILCOM INC.", match_basis="subaward-description-exact")),
        formula="crosswalk link: pe_bli=0204571N matched to award PIID N0017818F3011 via method='subaward+lexicon', confidence='medium' (dollars live at award grain in fct_award_transactions)",
        recorded_value=None, amount_text=None, amount_thousands=None,
    )
    return row | changes


def validate(row):
    return _verify_subaward(tuple(row.values()), {key: i for i, key in enumerate(row)})


def test_accepts_identified_link_without_claiming_money():
    assert validate(evidence()) is None


def test_accepts_explicit_appropriation_for_shared_budget_code():
    formula = evidence()["formula"].replace("pe_bli=0204571N", "pe_bli=3050 (account 1810N)")
    assert validate(evidence(formula=formula)) is None


@pytest.mark.parametrize("url", [
    "https://usaspending.gov.attacker.example/award/CONT_AWD_N0017818F3011_9700_X_9700/",
    "https://www.usaspending.gov/",
    "https://www.usaspending.gov/award/CONT_AWD_WRONG_9700_X_9700/",
    "https://user@www.usaspending.gov/award/CONT_AWD_N0017818F3011_9700_X_9700/",
])
def test_rejects_wrong_host_resource_or_prime_award(url):
    assert validate(evidence(official_url=url))


@pytest.mark.parametrize("key", ["subaward_number", "subawardee", "match_basis"])
def test_requires_source_record_identifiers_and_matching_rule(key):
    body = json.loads(evidence()["query_body"])
    body[key] = ""
    assert validate(evidence(query_body=json.dumps(body)))


@pytest.mark.parametrize("key,value", [("recorded_value", "100"), ("amount_text", "$100"), ("amount_thousands", 0), ("units", "USD")])
def test_link_cannot_be_promoted_to_an_amount(key, value):
    assert validate(evidence(**{key: value}))


def test_cannot_upgrade_confidence_or_change_evidence_method():
    formula = evidence()["formula"]
    assert validate(evidence(formula=formula.replace("'medium'", "'high'")))
    assert validate(evidence(formula=formula.replace("'subaward+lexicon'", "'account'")))


def write_rows(tmp_path, rows):
    dest = tmp_path / "citations" / "citations.parquet"
    dest.parent.mkdir()
    with duckdb.connect() as con:
        con.execute("create table citations (" + ", ".join(key + " varchar" for key in rows[0]) + ")")
        con.executemany("insert into citations values (" + ",".join("?" for _ in rows[0]) + ")", [tuple(row.values()) for row in rows])
        con.execute("copy citations to ? (format parquet)", [str(dest)])


def test_sample_and_integrity_gates_validate_the_new_kind(tmp_path):
    write_rows(tmp_path, [evidence()])
    assert citation_gate5b1(tmp_path)["ok"]
    assert integrity_gate5b1(tmp_path)["checks"]["subaward_link_shape"]


def test_integrity_checks_invalid_rows_outside_a_small_sample(tmp_path):
    write_rows(tmp_path, [evidence(), evidence(fact_id="fedcba0987654321", recorded_value="1")])
    assert not integrity_gate5b1(tmp_path)["checks"]["subaward_link_shape"]
