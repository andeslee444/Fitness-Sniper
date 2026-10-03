"""era_map lake reading, successor search and propose (plan Task 11; spec
§4.3, §4.6, §5.2, §5.4) on the miniature lake in era_map_fixtures."""
from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal

import pytest

from govbudget.jbooks import era_map
from govbudget.jbooks.era_map import Chain, ModernLine, search_successors
from govbudget.jbooks.p1_loader import EraKeyConflict
from jbooks.era_map_fixtures import (
    JLTV_SENTENCE,
    make_lake,
    make_raw_docs,
)

ON = date(2026, 10, 2)
JB = ("fy2026/a/Other Procurement - BA1 - Tactical & Support Vehicles__xml/"
      "U_PROCUREMENT_JB_2506261600ZZZZ_ARMY_PB_2026.xml")


@pytest.fixture(autouse=True)
def _mini_org_split(monkeypatch):
    # the miniature world splits only code '20' by organization
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"20"}))


def rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def run(tmp_path, seed=None, decided_on=ON):
    db = make_lake(tmp_path / "lake")
    raw = make_raw_docs(tmp_path)
    out = tmp_path / "research" / "era_map"
    seed = seed or tmp_path / "seeds" / "p1_era_code_decisions.csv"
    counts = era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=out,
                             seed_path=seed, decided_on=decided_on)
    return counts, out, seed


# ---------------------------------------------------------------------------
# lake reading
# ---------------------------------------------------------------------------

def test_load_era_keys_reads_code_sha_cells_and_amounts(tmp_path):
    era = {k.era_key + f"@{k.edition}": k
           for k in era_map.load_era_keys(make_lake(tmp_path))}
    assert len(era) == 15
    k = era["2035A-ARMY-L7@2022"]
    assert k.line_item_code == "5600D15603"
    assert k.filed_title == "Joint Light Tactical Vehicle"
    assert (k.organization, k.budget_activity) == ("ARMY", "01")
    assert k.source_document_sha256 == "22" * 32
    assert k.source_cells == ("O7", "Q7")
    assert k.actuals_k == Decimal("3000")
    assert k.enacted_k is None


def test_load_inputs_modern_collisions_and_pages(tmp_path):
    inputs = era_map.load_inputs(make_lake(tmp_path))
    assert inputs.collision_codes == frozenset({"3010", "20"})
    assert ("20", "0300D", "DCSA") in inputs.modern_pages
    lines = {(m.code, m.account, m.organization): m for m in inputs.modern}
    assert lines[("ATA000", "3010F", "F")].actuals_k == Decimal("250")
    assert lines[("3010", "1810N", "N")].actuals_k == Decimal("20")
    assert lines[("20", "0300D", "DCSA")].actuals_k == Decimal("45")


def test_missing_line_item_code_column_is_a_clear_precondition(tmp_path):
    db = make_lake(tmp_path, code_column=False)
    with pytest.raises(RuntimeError, match="no line_item_code column.*Tasks 7-8"):
        era_map.load_era_keys(db)


def test_blank_line_item_code_refuses(tmp_path):
    db = make_lake(tmp_path, blank_code=True)
    with pytest.raises(RuntimeError, match="blank line_item_code"):
        era_map.load_era_keys(db)


def test_a_key_printing_two_codes_raises(tmp_path):
    clash = ("P-1", "2022", "3010F", "Acct", "AF", "01", "BA", "3010F-AF-L1",
             "F-35", "fy_2022_request", "5", "22", "Exhibit P-1", "S1", "B02100")
    db = make_lake(tmp_path, extra_era=[clash])
    with pytest.raises(EraKeyConflict, match="3010F-AF-L1.*code"):
        era_map.load_era_keys(db)


# ---------------------------------------------------------------------------
# successor search (§5.4)
# ---------------------------------------------------------------------------

def chain(code, account, classes=("H",)):
    return Chain(chain_id=f"{code}|{account}|", line_item_code=code,
                 account=account, organization="", keys=((2022, "k"),),
                 classes=frozenset(classes), titles_by_edition={2022: "t"},
                 actuals_k=Decimal(0), n_keys=1, keys_sha256="")


def modern(*codes):
    return [ModernLine(edition=2026, code=c, account=a, organization="A", title="t")
            for c, a in codes]


def test_jltv_short_form_successor_with_pdf_page(tmp_path):
    raw = make_raw_docs(tmp_path)
    got = search_successors(
        [chain("5600D15603", "2035A"), chain("F015E0", "3010F")],
        raw_docs_dir=raw, modern=modern(("5731D15610", "2035A"), ("F01500", "3010F")))
    assert list(got) == ["5600D15603|2035A|"]          # F015E0: no continuation wording
    s = got["5600D15603|2035A|"]
    assert (s["successor_code"], s["successor_account"], s["matched_form"]) == (
        "5731D15610", "2035A", "short")
    assert (s["xml"], s["line"]) == (JB, 5)                # the volume's JB beats a master MJB
    assert s["quote"] == JLTV_SENTENCE
    ev = s["successor_evidence"]
    assert ev.startswith(f"xml={JB}:5; xml_sha256=")
    assert ("pdf=fy2026/a/Other Procurement - BA1 - Tactical & Support Vehicles.pdf;"
            in ev)
    assert "pdf_page=2;" in ev and "form=short;" in ev
    assert ev.endswith(f'quote="{JLTV_SENTENCE}"')


def test_literal_form_and_only_era_only_chains(tmp_path):
    xml = tmp_path / "fy2025" / "dw" / "xml" / "U_PROCUREMENT_JB_X_DW_PB_2025.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text("<a>Line ABC123 continues under line DEF456 from FY 2024.</a>\n"
                   "<a>Line QRS789 continues under line DEF456 too.</a>\n")
    got = search_successors(
        [chain("ABC123", "0300D"), chain("QRS789", "0300D", classes=("A1",))],
        raw_docs_dir=tmp_path, modern=modern(("DEF456", "0300D")))
    assert {cid: s["successor_code"] for cid, s in got.items()} == {
        "ABC123|0300D|": "DEF456"}
    assert got["ABC123|0300D|"]["matched_form"] == "literal"
    assert "pdf=" not in got["ABC123|0300D|"]["successor_evidence"]


def test_ambiguous_or_numeric_codes_record_nothing(tmp_path):
    xml = tmp_path / "fy2026" / "n" / "xml" / "U_PROCUREMENT_JB_X_NAVY_PB_2026.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text(
        "<a>Line ABC123 is a continuation of DEF456 and GHI789.</a>\n"
        "<a>Line 1234 is a continuation of line 5678.</a>\n")
    got = search_successors(
        [chain("ABC123", "0300D"), chain("1234", "1611N")], raw_docs_dir=tmp_path,
        modern=[*modern(("DEF456", "0400D"), ("GHI789", "0500D")),
                ModernLine(2026, "5678", "1611N", "N", "t")])
    assert got == {}


def test_successor_prefers_the_chains_own_account(tmp_path):
    xml = tmp_path / "fy2026" / "n" / "xml" / "U_PROCUREMENT_JB_X_NAVY_PB_2026.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text("<a>Line ABC123 continues under DEF456 and GHI789.</a>\n")
    got = search_successors(
        [chain("ABC123", "0300D")], raw_docs_dir=tmp_path,
        modern=modern(("DEF456", "0300D"), ("GHI789", "0500D")))
    assert got["ABC123|0300D|"]["successor_code"] == "DEF456"


# ---------------------------------------------------------------------------
# propose
# ---------------------------------------------------------------------------

def test_propose_counts(tmp_path):
    counts, out, _seed = run(tmp_path)
    assert counts["era_keys"] == 15 and counts["chains"] == 11
    # Fix round 1: "50" is R1 (it has a PB2026 page), not H — it moves out
    # of h_drifting (now empty, so absent from the dict) into r_containing.
    assert counts["chain_groups"] == {
        "a1_only": 4, "cr": 1, "h_drift_free": 2,
        "r_containing": 3, "unsafe": 1}
    assert counts["key_classes"] == {"CR": 1, "UNSAFE": 1, "R3": 0, "A1": 5,
                                     "A2": 0, "R1": 2, "R2": 2, "H": 4}
    assert counts["rulings"] == {"R-DEC-ERA-SAME": 3, "R-DEC-ERA-EXCLUDE": 2,
                                 "R-DEC-ERA-HISTORY": 2}
    assert counts["review_rows"] == 4 and counts["left_ruling"] == 1
    assert counts["successors"] == {"5600D15603|2035A|": "5731D15610"}
    # "50" carries no era-side amounts (spec §5.3 example), so era_actuals_k
    # drops by the $7K it used to wrongly contribute as an H chain.
    assert counts["era_actuals_k"] == "6455"
    assert counts["collision_codes"] == ["20", "3010"]
    assert counts["org_split_codes"] == ["20"]
    # Successor-search coverage (Fix round 1, "ALSO" ruling): the two H
    # chains (JLTV $4,000K, F015E0 $620K) are both searchable (neither code
    # is digits-only); only JLTV's continuation sentence was found, so
    # "searched" ($4,620K) exceeds "successors_found" ($4,000K) — the $620K
    # gap is F015E0, searched but blank, distinguishable from "not searched".
    assert counts["successor_coverage"] == {
        "era_only_chains": 2, "era_only_actuals_k": "4620",
        "searched_chains": 2, "searched_actuals_k": "4620",
        "not_searchable_chains": 0, "not_searchable_actuals_k": "0",
        "successors_found": 1, "successors_found_actuals_k": "4000"}
    assert json.loads((out / "counts.json").read_text()) == counts


def test_propose_seed_rows(tmp_path):
    _counts, _out, seed = run(tmp_path)
    got = {r["decision_id"]: r for r in rows(seed)}
    assert list(got) == sorted(got)
    assert set(got) == {
        "3010|1611N||2023-2023", "5600D15603|2035A||2022-2023",
        "ATA000|3010F||2022-2023", "F015E0|3010F||2022-2023",
        "FY2017CR|2031A||2022-2022", "O&M|0390D||2023-2023",
        "20|0300D|DTRA|2022-2022"}
    assert (got["3010|1611N||2023-2023"]["program_account"],
            got["3010|1611N||2023-2023"]["program_org"]) == ("1611N", "N")
    assert got["20|0300D|DTRA|2022-2022"]["program_org"] == "DTRA"
    jltv = got["5600D15603|2035A||2022-2023"]
    assert (jltv["decision"], jltv["ruling"], jltv["successor_code"],
            jltv["successor_account"]) == (
        "history_only", "R-DEC-ERA-HISTORY", "5731D15610", "2035A")
    assert got["F015E0|3010F||2022-2023"]["successor_code"] == ""
    ata = got["ATA000|3010F||2022-2023"]
    assert ata["modern_title"] == "F-35"
    assert ata["evidence"] == "title_jaccard=1.00; continuity=1/1; actuals_k=300"
    assert {r["decided_by"] for r in got.values()} == {"owner"}
    assert {r["decided_on"] for r in got.values()} == {"2026-10-02"}


def test_propose_review_rows_sorted_by_dollars(tmp_path):
    _counts, out, _seed = run(tmp_path)
    review = rows(out / "review.csv")
    assert tuple(review[0]) == era_map.REVIEW_COLUMNS
    # "50" now carries $0 era-side (Fix round 1), so it sorts last, after DHRA's $5K.
    assert [r["chain_id"] for r in review] == [
        "1045|1612N|", "20|0300D|DSS", "20|0300D|DHRA", "50|0300D|"]
    ohio, dss, dhra, fifty = review
    assert (ohio["proposed_decision"], ohio["program_account"]) == ("same_program", "")
    assert ohio["accounts"] == "era=1612N; modern=1611N"
    assert (dss["proposed_decision"], dss["program_account"], dss["program_org"]) == (
        "same_program", "0300D", "DCSA")
    # A1 on a collision code with no PB2026 page: data only, pinned to its line
    assert (dhra["proposed_decision"], dhra["program_account"], dhra["program_org"]) == (
        "history_only", "0300D", "DHRA")
    # Fix round 1 (binding ruling): "50" is R1 with zero era-anchored
    # continuity checks (no era-side amounts at all) — the pre-fill must not
    # guess same_program from an absence of evidence. Blank decision, and a
    # reason naming the exact gap instead of a false "continuity holds".
    assert (fifty["proposed_decision"], fifty["program_account"],
            fifty["program_org"]) == ("", "", "")
    assert fifty["reason"] == (
        "R1: no era-side continuity evidence (title Jaccard 0.00); possible"
        " reused code — decide same_program, a range split, or"
        " exclude_reused_code")
    assert fifty["titles_by_edition"] == (
        "2022: Indian Financing Act; 2023: Indian Incentive Program")
    assert {r["decision"] for r in review} == {""}
    assert all(len(r["keys_sha256"]) == 64 for r in review)


def test_propose_keys_and_chains_csv(tmp_path):
    _counts, out, _seed = run(tmp_path)
    keys = rows(out / "keys.csv")
    assert len(keys) == 15 and tuple(keys[0]) == era_map.KEY_COLUMNS
    k = next(r for r in keys if r["era_key"] == "2035A-ARMY-L7" and r["edition"] == "2022")
    assert (k["line_number"], k["class"], k["chain_id"], k["source_rows"],
            k["source_cells"]) == ("7", "H", "5600D15603|2035A|", "7", "O7,Q7")
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert len(chains) == 11
    assert chains["20|0300D|DHRA"]["left_ruling_reason"] == (
        "collision code without a matching PB2026 page")
    assert chains["5600D15603|2035A|"]["successor_evidence"].startswith(f"xml={JB}:5;")
    assert chains["FY2017CR|2031A|"]["ruling"] == "R-DEC-ERA-EXCLUDE"
    assert chains["50|0300D|"]["ruling"] == ""


def test_propose_is_byte_stable_and_keeps_class_ruling_dates(tmp_path):
    _c, out, seed = run(tmp_path)
    first = {p.name: p.read_bytes() for p in [seed, *sorted(out.iterdir())]}
    era_map.propose(duckdb_path=tmp_path / "lake" / "duckdb" / "govbudget.duckdb",
                    raw_docs_dir=tmp_path / "raw_docs", out_dir=out, seed_path=seed,
                    decided_on=date(2027, 1, 1))
    second = {p.name: p.read_bytes() for p in [seed, *sorted(out.iterdir())]}
    assert first == second


def test_propose_keeps_owner_batch_rows_and_skips_their_chains(tmp_path):
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    owner = {c: "" for c in era_map.SEED_COLUMNS}
    owner.update({"decision_id": "50|0300D||2022-2023", "line_item_code": "50",
                  "account": "0300D", "first_edition": "2022", "last_edition": "2023",
                  "decision": "exclude_reused_code", "n_keys": "2",
                  "keys_sha256": "x" * 64, "decided_on": "2026-10-05",
                  "decided_by": "owner", "ruling": "R-DEC-ERA-B1"})
    era_map.write_seed(seed, [owner])
    counts, out, _ = run(tmp_path, seed=seed)
    assert counts["owner_batch_chains"] == 1
    assert "50|0300D|" not in {r["chain_id"] for r in rows(out / "review.csv")}
    assert next(r for r in rows(seed) if r["ruling"] == "R-DEC-ERA-B1") == owner


def test_propose_prefills_history_only_on_another_organizations_page(
        tmp_path, monkeypatch):
    # PB2022 prints `10` for TJS (the page's organization) and DPAA, and `20`
    # for DTRA (page 20-DTRA) and DLA, whose title matches DTRA's page:
    # same_program would put DPAA's / DLA's dollars on the other's page.
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"10", "20"}))
    db = make_lake(tmp_path / "lake", org_clash=True)
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    counts = era_map.propose(duckdb_path=db, raw_docs_dir=make_raw_docs(tmp_path),
                             out_dir=out, seed_path=seed, decided_on=ON)
    assert counts["org_split_codes"] == ["10", "20"]
    assert counts["collision_codes"] == ["20", "3010"]
    review = {r["chain_id"]: r for r in rows(out / "review.csv")}
    dpaa, dla, dss = review["10|0300D|DPAA"], review["20|0300D|DLA"], review["20|0300D|DSS"]
    assert (dpaa["proposed_decision"], dpaa["program_account"], dpaa["program_org"],
            dpaa["reason"]) == (
        "history_only", "", "", "R2: code also printed by TJS in PB2022; page 10 is TJS's")
    # a collision code pins the chain's own identity, apart from page 20-DTRA
    assert (dla["proposed_decision"], dla["program_account"], dla["program_org"],
            dla["reason"]) == (
        "history_only", "0300D", "DLA",
        "R2: code also printed by DTRA in PB2022; page 20-DTRA (title match) is DTRA's")
    # DSS -> DCSA: page 20-DCSA has no era keys beside DSS's, an organization rename
    assert (dss["proposed_decision"], dss["program_org"]) == ("same_program", "DCSA")
    seeded = {r["decision_id"]: r for r in rows(seed)}
    assert (seeded["10|0300D|TJS|2022-2023"]["ruling"],
            seeded["10|0300D|TJS|2022-2023"]["program_org"]) == ("R-DEC-ERA-SAME", "")


def test_propose_refuses_to_overwrite_unratified_decisions(tmp_path):
    _c, out, seed = run(tmp_path)
    review = rows(out / "review.csv")
    review[0]["decision"] = "same_program"
    era_map.write_csv(out / "review.csv", era_map.REVIEW_COLUMNS, review)
    before = (seed.read_bytes(), (out / "review.csv").read_bytes())
    with pytest.raises(RuntimeError, match="not ratified yet.*1045"):
        era_map.propose(duckdb_path=tmp_path / "lake" / "duckdb" / "govbudget.duckdb",
                        raw_docs_dir=tmp_path / "raw_docs", out_dir=out,
                        seed_path=seed, decided_on=ON)
    assert (seed.read_bytes(), (out / "review.csv").read_bytes()) == before


def test_propose_refuses_a_changed_org_split(tmp_path, monkeypatch):
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"10", "20"}))
    with pytest.raises(RuntimeError, match="org-split codes changed"):
        run(tmp_path)
