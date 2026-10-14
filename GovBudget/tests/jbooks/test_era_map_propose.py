"""era_map lake reading, successor search and propose (plan Task 11; spec
§4.3, §4.6, §5.2, §5.4) on the miniature lake in era_map_fixtures."""
from __future__ import annotations

import csv
import json
import pathlib
import subprocess
import sys
from datetime import date
from decimal import Decimal

import duckdb
import pytest

from govbudget.jbooks import era_map
from govbudget.jbooks.era_map import Chain, EraKey, ModernLine, search_successors
from govbudget.jbooks.p1_loader import EraKeyConflict
from jbooks import era_map_fixtures
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
    assert len(era) == 16
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


# ---------------------------------------------------------------------------
# _prefill (Fix round 3): hand-built era/modern, no lake — mirrors
# test_era_map.py's ek()/ml() pattern, scoped to this file per the fix's
# instructions.
# ---------------------------------------------------------------------------

def ek(edition, account, org, line, code, title, *, ba="01", act=None,
       enacted=None, request=None):
    return EraKey(
        edition=edition, account=account, organization=org, budget_activity=ba,
        era_key=f"{account}-{org}-L{line}", line_item_code=code,
        filed_title=title, actuals_k=None if act is None else Decimal(act),
        source_document_sha256="ab" * 32, source_cells=(f"O{line}",),
        enacted_k=None if enacted is None else Decimal(enacted),
        request_k=None if request is None else Decimal(request),
    )


def ml(edition, code, account, org, title, *, act=None, enacted=None):
    return ModernLine(edition=edition, code=code, account=account,
                      organization=org, title=title,
                      actuals_k=None if act is None else Decimal(act),
                      enacted_k=None if enacted is None else Decimal(enacted))


def _prefill_for(era, modern_lines, *, chain_id=None, collision_codes=frozenset(),
                  modern_pages=frozenset()):
    """Build a _Context from era/modern_lines, classify, pick one chain (by
    chain_id, or the sole chain when there is exactly one), and return
    _prefill's result for it."""
    ctx = era_map._Context(era, modern_lines)
    classes = {(k.edition, k.era_key): ctx.classify(k, collision_codes) for k in ctx.era}
    chains = era_map.build_chains(era, classes)
    if chain_id is None:
        assert len(chains) == 1, [c.chain_id for c in chains]
        ch = chains[0]
    else:
        ch = next(c for c in chains if c.chain_id == chain_id)
    keys = era_map.group_keys(era)[ch.chain_id]
    info = era_map._chain_context(ch, keys, ctx)
    org_editions = era_map._org_editions(era, ctx.split)
    return era_map._prefill(ch, keys, ctx, info, collision_codes, modern_pages, org_editions)


def test_prefill_own_account_r3_checks_every_pb2024_26_title(monkeypatch):
    # Fix round 3 (review finding, live shape 1045|1611N|): the destination
    # is the chain's OWN account — the code stayed, it did not move — but
    # PB2024 and PB2026 print DIFFERENT titles there ("OHIO Replacement
    # Submarine" then "Columbia Class Submarine"). Checking only the
    # latest title wrongly blanked a chain PB2024 itself confirms. A
    # sibling era account (1612N) makes the code span two era accounts in
    # one edition (R3) and gives the code a SECOND PB2024-26 destination
    # (1612N: Other Shipbuilding), so this chain's own-account match is
    # resolved via the >1-destination (own_hits) branch, not the
    # single-destination shortcut.
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset())
    era = [ek(2022, "1611N", "NAVY", 9, "OHSHIP", "OHIO Replacement Submarine"),
           ek(2022, "1612N", "NAVY", 3, "OHSHIP", "OHIO Replacement Submarine")]
    modern = [ml(2024, "OHSHIP", "1611N", "N", "OHIO Replacement Submarine"),
              ml(2026, "OHSHIP", "1611N", "N", "Columbia Class Submarine"),
              ml(2026, "OHSHIP", "1612N", "N", "Other Shipbuilding")]
    decision, reason, pa, po = _prefill_for(era, modern, chain_id="OHSHIP|1611N|")
    assert decision == "same_program"
    assert reason == (
        "R3: the code's own account (1611N); also printed by 1612N")
    assert (pa, po) == ("", "")


def test_prefill_own_account_r3_mismatch_names_its_own_recorded_title(monkeypatch):
    # The sibling chain from the same world: 1612N is ALSO its own account
    # (R3, mi not None there), but its own account's recorded PB2024-26
    # title ("Other Shipbuilding") does not match this line's title at
    # all. The reason must not claim an account/organization "move" — the
    # account never changed.
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset())
    era = [ek(2022, "1611N", "NAVY", 9, "OHSHIP", "OHIO Replacement Submarine"),
           ek(2022, "1612N", "NAVY", 3, "OHSHIP", "OHIO Replacement Submarine")]
    modern = [ml(2024, "OHSHIP", "1611N", "N", "OHIO Replacement Submarine"),
              ml(2026, "OHSHIP", "1611N", "N", "Columbia Class Submarine"),
              ml(2026, "OHSHIP", "1612N", "N", "Other Shipbuilding")]
    decision, reason, pa, po = _prefill_for(era, modern, chain_id="OHSHIP|1612N|")
    assert decision == ""
    assert reason == (
        "R3: the code's own account (1612N) prints 'Other Shipbuilding',"
        " not this line's title; also printed by 1611N — confirm"
        " same_program by hand")
    assert (pa, po) == ("", "")


def test_prefill_r1_no_request_reason_differs_from_range_split():
    # Fix round 3 (owner-facing finding, live shape: the four 0350D
    # National Guard/Reserve "Miscellaneous Equipment" rows): with no
    # non-zero request in any edition (a Congress-added line, confirmed on
    # the live lake — see the report), the "range split" advice is wrong:
    # there is no year-to-year request/actuals pair to confirm either way.
    # Amounts are well above the $1M continuity floor so the check fails
    # on its ratio, not passes trivially on the floor rule.
    era = [ek(2021, "0350D", "ARMY", 5, "MISCEQ", "Miscellaneous Equipment",
              act=1, enacted=200000, request=0),
           ek(2022, "0350D", "ARMY", 5, "MISCEQ", "Miscellaneous Equipment",
              act=10000, enacted=50, request=0)]
    modern = [ml(2026, "MISCEQ", "0350D", "A", "Misc Equipment - Army National Guard")]
    decision, reason, pa, po = _prefill_for(era, modern)
    assert decision == ""
    assert reason == (
        "R1: renamed 'Miscellaneous Equipment' →"
        " 'Misc Equipment - Army National Guard'; no request in any"
        " edition (a Congress-added line), so the year-to-year continuity"
        " check cannot confirm it — decide same_program if the modern"
        " line is the same program")
    assert (pa, po) == ("", "")


def test_prefill_r1_continuity_fails_keeps_range_split_when_a_request_exists():
    # Regression: the same shape, but one edition DID carry a non-zero
    # request — the existing "range split" wording is still right, since
    # there IS year-to-year evidence and it failed.
    era = [ek(2021, "0350D", "ARMY", 5, "MISCEQ", "Miscellaneous Equipment",
              act=1, enacted=200000, request=5),
           ek(2022, "0350D", "ARMY", 5, "MISCEQ", "Miscellaneous Equipment",
              act=10000, enacted=50, request=0)]
    modern = [ml(2026, "MISCEQ", "0350D", "A", "Misc Equipment - Army National Guard")]
    decision, reason, pa, po = _prefill_for(era, modern)
    assert decision == ""
    assert reason == (
        "R1: renamed and continuity 0/1 fails — consider a range split"
        " (earlier range exclude_reused_code)")


def test_prefill_r2_ambiguous_destinations_names_each():
    # the ambiguous-destination branch: >1 destination, no collision pin,
    # and the chain's own account is not one of them.
    era = [ek(2022, "AAAA", "ORG", 1, "AMBIG", "Old Program Title")]
    modern = [ml(2026, "AMBIG", "BBBB", "B", "First Program"),
              ml(2026, "AMBIG", "CCCC", "C", "Second Program")]
    decision, reason, pa, po = _prefill_for(era, modern)
    assert decision == ""
    assert reason == (
        "R2: account/organization move to several possible destinations"
        " (BBBB: First Program; CCCC: Second Program) — decide which, if"
        " any, this line moved to")
    assert (pa, po) == ("", "")


def test_prefill_r2_zero_destinations_names_the_gap():
    # Fix round 3: a code that exists in modern but has no title on
    # record anywhere must not be told it has "several possible
    # destinations" — there are none.
    era = [ek(2022, "AAAA", "ORG", 1, "NOTITLE", "Old Program Title")]
    modern = [ModernLine(edition=2026, code="NOTITLE", account="BBBB",
                         organization="B", title=None)]
    decision, reason, pa, po = _prefill_for(era, modern)
    assert decision == ""
    assert reason == (
        "R2: account/organization move, but no PB2024-26 line for this"
        " code has a title on record — decide which program this line"
        " belongs to")


def test_prefill_r2_collision_pin_missing_from_destinations_names_the_pin():
    # Fix round 3: a defensive case ("neither occurs live" per the review
    # finding) — a collision page is on record for the chain's own
    # account, but no P-1 line backs it, while the code genuinely exists
    # elsewhere in modern. The message must name the actual gap (the pin),
    # not the unrelated destination that does have a title.
    era = [ek(2022, "AAAA", "ORG", 1, "PINCODE", "Old Title")]
    modern = [ml(2026, "PINCODE", "ZZZZ", "Z", "Unrelated Program")]
    modern_pages = frozenset({("PINCODE", "AAAA", "B")})
    decision, reason, pa, po = _prefill_for(
        era, modern, collision_codes=frozenset({"PINCODE"}), modern_pages=modern_pages)
    assert decision == ""
    assert reason == (
        "R2: the collision pin AAAA has no PB2024-26 title on record —"
        " decide which program this line belongs to")
    assert (pa, po) == ("AAAA", "B")


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
    # Fix round 2 adds one more R2 chain (MVTRUE|3021F|, a genuine move with
    # a matching destination title) to exercise the Jaccard gate end to end.
    assert counts["era_keys"] == 16 and counts["chains"] == 12
    # Fix round 1: "50" is R1 (it has a PB2026 page), not H — it moves out
    # of h_drifting (now empty, so absent from the dict) into r_containing.
    assert counts["chain_groups"] == {
        "a1_only": 4, "cr": 1, "h_drift_free": 2,
        "r_containing": 4, "unsafe": 1}
    assert counts["key_classes"] == {"CR": 1, "UNSAFE": 1, "R3": 0, "A1": 5,
                                     "A2": 0, "R1": 2, "R2": 3, "H": 4}
    assert counts["rulings"] == {"R-DEC-ERA-SAME": 3, "R-DEC-ERA-EXCLUDE": 2,
                                 "R-DEC-ERA-HISTORY": 2}
    assert counts["review_rows"] == 5 and counts["left_ruling"] == 1
    assert counts["successors"] == {"5600D15603|2035A|": "5731D15610"}
    # "50" carries no era-side amounts (spec §5.3 example), so era_actuals_k
    # drops by the $7K it used to wrongly contribute as an H chain; MVTRUE
    # (Fix round 2) adds $80K.
    assert counts["era_actuals_k"] == "6535"
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
    # MVTRUE ($80K, Fix round 2) sorts between OHIO ($500K) and DSS ($40K).
    assert [r["chain_id"] for r in review] == [
        "1045|1612N|", "MVTRUE|3021F|", "20|0300D|DSS", "20|0300D|DHRA", "50|0300D|"]
    ohio, mvtrue, dss, dhra, fifty = review
    # Fix round 2 (binding ruling, the "0182" shape): OHIO's only PB2026
    # destination (1611N) prints a DIFFERENT program ("Columbia Class
    # Submarine", title Jaccard < 0.5 against "OHIO Replacement Submarine")
    # — same_program must not be guessed from an account move alone.
    assert (ohio["proposed_decision"], ohio["program_account"]) == ("", "")
    assert ohio["accounts"] == "era=1612N; modern=1611N"
    assert ohio["reason"] == (
        "R2: account/organization move, but the code is 'Columbia Class"
        " Submarine' in 1611N; decide same_program only if this line"
        " moved there")
    assert ohio["modern_title"] == "1611N: Columbia Class Submarine"
    # Fix round 2: a genuine move (same title in the destination, 3022F)
    # still clears the Jaccard gate and keeps same_program; modern_title
    # shows "<account>: <title>" for a move, per the binding ruling.
    assert (mvtrue["proposed_decision"], mvtrue["program_account"]) == ("same_program", "")
    assert mvtrue["modern_title"] == "3022F: Space Launch Range System"
    assert (dss["proposed_decision"], dss["program_account"], dss["program_org"]) == (
        "same_program", "0300D", "DCSA")
    # Fix round 2: DSS's modern_title now lists EVERY PB2026 destination of
    # code "20" (not just the DCSA page its pin resolved to).
    assert dss["modern_title"] == (
        "0300D/DCSA: Major Equipment; 0300D/DHRA: Personnel Administration;"
        " 0300D/DTRA: Vehicles")
    # A1 on a collision code with no PB2026 page: data only, pinned to its line
    assert (dhra["proposed_decision"], dhra["program_account"], dhra["program_org"]) == (
        "history_only", "0300D", "DHRA")
    # DHRA is A1 alone (not a move) — modern_title keeps today's plain format.
    assert dhra["modern_title"] == "Personnel Administration"
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
    assert len(keys) == 16 and tuple(keys[0]) == era_map.KEY_COLUMNS
    k = next(r for r in keys if r["era_key"] == "2035A-ARMY-L7" and r["edition"] == "2022")
    assert (k["line_number"], k["class"], k["chain_id"], k["source_rows"],
            k["source_cells"]) == ("7", "H", "5600D15603|2035A|", "7", "O7,Q7")
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert len(chains) == 12
    assert chains["20|0300D|DHRA"]["left_ruling_reason"] == (
        "collision code without a matching PB2026 page")
    assert chains["5600D15603|2035A|"]["successor_evidence"].startswith(f"xml={JB}:5;")
    assert chains["FY2017CR|2031A|"]["ruling"] == "R-DEC-ERA-EXCLUDE"
    assert chains["50|0300D|"]["ruling"] == ""
    # Fix round 2: chains.csv's modern_title shows every PB2026 destination
    # for a move (classes containing R2 or R3), not just the chain's own.
    assert chains["1045|1612N|"]["modern_title"] == "1611N: Columbia Class Submarine"
    assert chains["MVTRUE|3021F|"]["modern_title"] == "3022F: Space Launch Range System"


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


# ---------------------------------------------------------------------------
# ROADMAP #198 (follow-ups spec 2026-10-04 §6.2, §4.5, Q25)
# ---------------------------------------------------------------------------

def test_era_map_does_not_import_the_workbook_loader():
    code = ("import sys, govbudget.jbooks.era_map as m;"
            " print('govbudget.jbooks.p1_loader' in sys.modules, m.EraKeyConflict.__module__)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True).stdout.split()
    assert out == ["False", "govbudget.jbooks.era_keys"]


def test_p1_loader_re_exports_the_era_keys_conflict():
    from govbudget.jbooks import era_keys, p1_loader

    assert p1_loader.EraKeyConflict is era_keys.EraKeyConflict is EraKeyConflict


# The live PB2021 shape (code 15: DISA's page, TJS's line), moved into this
# world's PB2022: both organizations print 15 under one title in the era
# edition and in PB2026, so both chains are A1 and class-ruled same_program.
CLASH_15 = [
    ("P-1", "2022", "0300D", "Acct", "DISA", "01", "BA", "0300D-DISA-L30", "Major Equipment",
     "fy_2020_actuals", "70", "22", "Exhibit P-1", "O30", "15"),
    ("P-1", "2022", "0300D", "Acct", "TJS", "01", "BA", "0300D-TJS-L31", "Major Equipment",
     "fy_2020_actuals", "9", "22", "Exhibit P-1", "O31", "15"),
    ("P-1", "2026", "0300D", "Acct", "DISA", "01", "BA", "15", "Major Equipment",
     "fy_2024_actuals", "80", "26", "Exhibit P-1", "O9", "15"),
    ("P-1", "2026", "0300D", "Acct", "TJS", "01", "BA", "15", "Major Equipment",
     "fy_2024_actuals", "10", "26", "Exhibit P-1", "O10", "15"),
]


def test_propose_sends_two_organizations_on_one_page_to_review(tmp_path, monkeypatch):
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"15", "20"}))
    db = make_lake(tmp_path / "lake", extra_era=CLASH_15)
    con = duckdb.connect(str(db))
    con.execute("insert into dim_programs values ('15', '0300D', 'DISA')")   # page 15 is DISA's
    con.close()
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=make_raw_docs(tmp_path), out_dir=out,
                    seed_path=seed, decided_on=ON)
    assert not [r for r in rows(seed) if r["line_item_code"] == "15"]
    review = {r["chain_id"]: r for r in rows(out / "review.csv")}
    for cid in ("15|0300D|DISA", "15|0300D|TJS"):
        assert review[cid]["proposed_decision"] == ""
        assert review[cid]["reason"] == (
            "A1: 15|0300D|DISA|2022-2022: same_program collides with 15|0300D|TJS|2022-2022"
            " — page 15 would sum DISA and TJS in PB2022; decide history_only for the"
            " organization whose page it is not")
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert chains["15|0300D|TJS"]["left_ruling_reason"] == (
        "one organization per page grain (rule 4(b))")


def test_propose_never_silently_overturns_a_seeded_class_decision(tmp_path):
    _c, out, seed = run(tmp_path)
    seeded = rows(seed)
    ata = next(r for r in seeded if r["line_item_code"] == "ATA000")
    ata.update(decision="history_only", ruling="R-DEC-ERA-HISTORY")   # as an earlier lake ruled it
    era_map.write_seed(seed, seeded)
    db = tmp_path / "lake" / "duckdb" / "govbudget.duckdb"
    era_map.propose(duckdb_path=db, raw_docs_dir=tmp_path / "raw_docs", out_dir=out,
                    seed_path=seed, decided_on=ON)
    assert not [r for r in rows(seed) if r["line_item_code"] == "ATA000"]   # Q25
    held = {r["chain_id"]: r for r in rows(out / "review.csv")}["ATA000|3010F|"]
    assert held["proposed_decision"] == "same_program"
    assert held["reason"] == (
        "A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded"
        " history_only (R-DEC-ERA-HISTORY, 2026-10-02) — confirm or keep the seeded"
        " decision; no silent overturn")
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert chains["ATA000|3010F|"]["left_ruling_reason"] == (
        "class result differs from the seeded decision")
    undecided = era_map.check(duckdb_path=db, seed_path=seed)["undecided"]
    assert "ATA000|3010F|" in [u["chain_id"] for u in undecided]


def test_propose_writes_nothing_when_a_later_output_fails(tmp_path, monkeypatch):
    _c, out, seed = run(tmp_path)
    era_map.write_seed(seed, [r for r in rows(seed) if r["line_item_code"] != "ATA000"])
    before = {p.name: p.read_bytes() for p in [seed, *sorted(out.iterdir())]}

    def boom(code):
        raise RuntimeError("counts.json failed")

    monkeypatch.setattr(era_map, "is_successor_searchable", boom)   # read only for counts.json
    with pytest.raises(RuntimeError, match="counts.json failed"):
        era_map.propose(duckdb_path=tmp_path / "lake" / "duckdb" / "govbudget.duckdb",
                        raw_docs_dir=tmp_path / "raw_docs", out_dir=out, seed_path=seed,
                        decided_on=ON)
    assert {p.name: p.read_bytes() for p in [seed, *sorted(out.iterdir())]} == before


def test_write_csv_replaces_the_file_whole_or_not_at_all(tmp_path, monkeypatch):
    path = tmp_path / "x.csv"
    era_map.write_csv(path, ("a",), [{"a": "1"}])

    def fail(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(era_map.os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        era_map.write_csv(path, ("a",), [{"a": "2"}])
    assert path.read_text() == "a\n1\n"
    assert [p.name for p in tmp_path.iterdir()] == ["x.csv"]


def test_a_literal_form_in_a_later_file_beats_an_earlier_short_form(tmp_path):
    short = tmp_path / "fy2026" / "a" / "xml" / "U_PROCUREMENT_JB_X_ARMY_PB_2026.xml"
    literal = tmp_path / "fy2025" / "a" / "xml" / "U_PROCUREMENT_JB_X_ARMY_PB_2025.xml"
    for p in (short, literal):
        p.parent.mkdir(parents=True)
    short.write_text("<a>Budget line D15610 is a continuation of budget line D15603.</a>\n")
    literal.write_text("<a>Line 5600D15603 continues under 5731D15610 from FY 2021.</a>\n")
    got = search_successors([chain("5600D15603", "2035A")], raw_docs_dir=tmp_path,
                            modern=modern(("5731D15610", "2035A")))
    s = got["5600D15603|2035A|"]
    assert (s["successor_code"], s["matched_form"], s["xml"]) == (
        "5731D15610", "literal", "fy2025/a/xml/U_PROCUREMENT_JB_X_ARMY_PB_2025.xml")


def test_a_double_quote_in_the_successor_sentence_is_escaped(tmp_path):
    xml = tmp_path / "fy2026" / "dw" / "xml" / "U_PROCUREMENT_JB_X_DW_PB_2026.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text('<a>Line ABC123 continues under the "DEF456" line from FY 2024.</a>\n')
    got = search_successors([chain("ABC123", "0300D")], raw_docs_dir=tmp_path,
                            modern=modern(("DEF456", "0300D")))
    s = got["ABC123|0300D|"]
    assert s["quote"] == 'Line ABC123 continues under the "DEF456" line from FY 2024.'
    assert s["successor_evidence"].endswith(
        'quote="Line ABC123 continues under the \\"DEF456\\" line from FY 2024."')


def test_prefill_own_account_with_no_other_account_says_so(monkeypatch):
    # The live GPS03C|3022F| shape: R3 because the era edition printed the
    # code in two accounts, but PB2024-26 print it in its own account only.
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset())
    era = [ek(2022, "3022F", "AF", 9, "GPS03C", "GPS III Space Segment"),
           ek(2022, "3021F", "AF", 3, "GPS03C", "GPS III Space Segment")]
    modern_lines = [ml(2026, "GPS03C", "3022F", "F", "GPS III Space Segment")]
    decision, reason, pa, po = _prefill_for(era, modern_lines, chain_id="GPS03C|3022F|")
    assert decision == "same_program"
    assert reason == "R3: the code's own account (3022F); no other PB2024-26 account prints it"
    assert (pa, po) == ("", "")


# ---------------------------------------------------------------------------
# Task 4a fix round 1: the overturn hold persists in review.csv (Q25 is
# fail-closed), a rule-4(b) clash beside an owner row, a pins-only overturn,
# and the five outputs staged before any is replaced
# ---------------------------------------------------------------------------

DECIDED = date(2026, 10, 5)
HELD_ATA = ("A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded"
            " history_only (R-DEC-ERA-HISTORY, 2026-10-02) — confirm or keep the seeded"
            " decision; no silent overturn")


def _db(tmp_path):
    return tmp_path / "lake" / "duckdb" / "govbudget.duckdb"


def _propose_again(tmp_path, out, seed, db=None):
    return era_map.propose(duckdb_path=db or _db(tmp_path), raw_docs_dir=tmp_path / "raw_docs",
                           out_dir=out, seed_path=seed, decided_on=ON)


def _files(seed, out):
    return {p.name: p.read_bytes() for p in [seed, *sorted(out.iterdir())]}


def _seed_ata_as(seed, decision, ruling):
    seeded = rows(seed)
    next(r for r in seeded if r["line_item_code"] == "ATA000").update(
        decision=decision, ruling=ruling)
    era_map.write_seed(seed, seeded)


def _assert_ata_held(tmp_path, out, seed, reason=HELD_ATA):
    assert not [r for r in rows(seed) if r["line_item_code"] == "ATA000"]
    held = {r["chain_id"]: r for r in rows(out / "review.csv")}["ATA000|3010F|"]
    assert held["reason"] == reason
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert chains["ATA000|3010F|"]["left_ruling_reason"] == (
        "class result differs from the seeded decision")
    assert chains["ATA000|3010F|"]["ruling"] == ""
    undecided = era_map.check(duckdb_path=_db(tmp_path), seed_path=seed)["undecided"]
    assert "ATA000|3010F|" in [u["chain_id"] for u in undecided]
    return held


def test_a_held_overturn_stays_held_until_the_owner_ratifies(tmp_path):
    # Review finding 1: the hold fired once, while the seed still held the old
    # class row; the same call removed that row, so a second plain `propose`
    # class-ruled the chain with the new result and `era-map check` passed.
    _c, out, seed = run(tmp_path)
    _seed_ata_as(seed, "history_only", "R-DEC-ERA-HISTORY")
    _propose_again(tmp_path, out, seed)
    first = _files(seed, out)
    _assert_ata_held(tmp_path, out, seed)
    for _ in range(3):
        _propose_again(tmp_path, out, seed)
        held = _assert_ata_held(tmp_path, out, seed)
        assert held["proposed_decision"] == "same_program"
        assert _files(seed, out) == first          # byte-stable, nothing drifts


def test_a_ratified_owner_row_releases_the_hold(tmp_path):
    _c, out, seed = run(tmp_path)
    _seed_ata_as(seed, "history_only", "R-DEC-ERA-HISTORY")
    _propose_again(tmp_path, out, seed)
    _propose_again(tmp_path, out, seed)            # still held: no owner action yet
    _assert_ata_held(tmp_path, out, seed)
    review = rows(out / "review.csv")
    next(r for r in review if r["chain_id"] == "ATA000|3010F|")["decision"] = "history_only"
    era_map.write_csv(out / "review.csv", era_map.REVIEW_COLUMNS, review)
    assert era_map.ratify(review_csv=out / "review.csv", seed_path=seed, batch="B1",
                          decided_on=DECIDED, duckdb_path=_db(tmp_path)) == 1
    _propose_again(tmp_path, out, seed)
    ata = [r for r in rows(seed) if r["line_item_code"] == "ATA000"]
    assert [(r["decision"], r["ruling"], r["decided_on"]) for r in ata] == [
        ("history_only", "R-DEC-ERA-B1", "2026-10-05")]
    assert "ATA000|3010F|" not in {r["chain_id"] for r in rows(out / "review.csv")}
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert (chains["ATA000|3010F|"]["ruling"], chains["ATA000|3010F|"]["left_ruling_reason"]) == (
        "owner-batch", "")
    undecided = era_map.check(duckdb_path=_db(tmp_path), seed_path=seed)["undecided"]
    assert "ATA000|3010F|" not in [u["chain_id"] for u in undecided]
    again = _files(seed, out)
    _propose_again(tmp_path, out, seed)
    assert _files(seed, out) == again


def test_a_held_overturn_follows_a_class_result_that_changes_again(tmp_path, monkeypatch):
    _c, out, seed = run(tmp_path)
    _seed_ata_as(seed, "exclude_reused_code", "R-DEC-ERA-EXCLUDE")
    _propose_again(tmp_path, out, seed)
    _assert_ata_held(tmp_path, out, seed, reason=(
        "A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded"
        " exclude_reused_code (R-DEC-ERA-EXCLUDE, 2026-10-02) — confirm or keep the seeded"
        " decision; no silent overturn"))
    # the lake moves on: PB2026 no longer prints ATA000, so the chain is era-only
    # and the class ruling is history_only
    monkeypatch.setattr(era_map_fixtures, "MODERN",
                        [m for m in era_map_fixtures.MODERN if m[0] != "ATA000"])
    db2 = era_map_fixtures.make_lake(tmp_path / "lake2")
    _propose_again(tmp_path, out, seed, db=db2)
    assert not [r for r in rows(seed) if r["line_item_code"] == "ATA000"]
    held = {r["chain_id"]: r for r in rows(out / "review.csv")}["ATA000|3010F|"]
    assert held["proposed_decision"] == "history_only"
    assert held["reason"] == (
        "H: class result history_only (R-DEC-ERA-HISTORY) differs from the seeded"
        " exclude_reused_code (R-DEC-ERA-EXCLUDE, 2026-10-02) — confirm or keep the seeded"
        " decision; no silent overturn")
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert chains["ATA000|3010F|"]["left_ruling_reason"] == (
        "class result differs from the seeded decision")
    undecided = era_map.check(duckdb_path=db2, seed_path=seed)["undecided"]
    assert "ATA000|3010F|" in [u["chain_id"] for u in undecided]


def test_a_pins_only_difference_is_an_overturn_and_stays_held(tmp_path):
    _c, out, seed = run(tmp_path)
    seeded = rows(seed)
    dtra = next(r for r in seeded if r["decision_id"] == "20|0300D|DTRA|2022-2022")
    assert (dtra["decision"], dtra["program_org"]) == ("same_program", "DTRA")
    dtra["program_org"] = "DCSA"                   # same decision and ruling, other page
    era_map.write_seed(seed, seeded)
    for _ in range(2):
        _propose_again(tmp_path, out, seed)
        assert "20|0300D|DTRA|2022-2022" not in {r["decision_id"] for r in rows(seed)}
        held = {r["chain_id"]: r for r in rows(out / "review.csv")}["20|0300D|DTRA"]
        assert (held["proposed_decision"], held["program_account"], held["program_org"]) == (
            "same_program", "0300D", "DTRA")
        assert held["reason"] == (
            "A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded"
            " same_program (R-DEC-ERA-SAME, 2026-10-02) — confirm or keep the seeded"
            " decision; no silent overturn")
        chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
        assert chains["20|0300D|DTRA"]["left_ruling_reason"] == (
            "class result differs from the seeded decision")


def test_a_clash_with_an_owner_ratified_row_holds_only_the_class_ruled_side(
        tmp_path, monkeypatch):
    # The live DISA/TJS shape on code 15: the owner already ratified TJS
    # same_program; the class ruling would put DISA on the same page.
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"15", "20"}))
    db = make_lake(tmp_path / "lake", extra_era=CLASH_15)
    con = duckdb.connect(str(db))
    con.execute("insert into dim_programs values ('15', '0300D', 'DISA')")
    con.close()
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    owner = {c: "" for c in era_map.SEED_COLUMNS}
    owner.update({"decision_id": "15|0300D|TJS|2022-2022", "line_item_code": "15",
                  "account": "0300D", "organization": "TJS", "first_edition": "2022",
                  "last_edition": "2022", "decision": "same_program", "n_keys": "1",
                  "keys_sha256": "x" * 64, "decided_on": "2026-10-05",
                  "decided_by": "owner", "ruling": "R-DEC-ERA-B1"})
    era_map.write_seed(seed, [owner])
    for _ in range(2):
        era_map.propose(duckdb_path=db, raw_docs_dir=make_raw_docs(tmp_path), out_dir=out,
                        seed_path=seed, decided_on=ON)
        assert next(r for r in rows(seed) if r["ruling"] == "R-DEC-ERA-B1") == owner
        assert not [r for r in rows(seed) if r["organization"] == "DISA"]
        review = {r["chain_id"]: r for r in rows(out / "review.csv")}
        assert "15|0300D|TJS" not in review
        assert review["15|0300D|DISA"]["proposed_decision"] == ""
        assert review["15|0300D|DISA"]["reason"] == (
            "A1: 15|0300D|TJS|2022-2022: same_program collides with 15|0300D|DISA|2022-2022"
            " — page 15 would sum TJS and DISA in PB2022; decide history_only for the"
            " organization whose page it is not")
        chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
        assert chains["15|0300D|TJS"]["ruling"] == "owner-batch"
        assert chains["15|0300D|DISA"]["left_ruling_reason"] == (
            "one organization per page grain (rule 4(b))")


def test_propose_stages_every_output_before_replacing_any(tmp_path, monkeypatch):
    # Review finding M2: the five os.replace calls run back to back, after all
    # five temporary files are written.
    _c, out, seed = run(tmp_path)
    era_map.write_seed(seed, [r for r in rows(seed) if r["line_item_code"] != "ATA000"])
    staged = []
    real = era_map.os.replace

    def spy(src, dst):
        if not staged:
            staged.extend(sorted(p.name for d in (seed.parent, out)
                                 for p in d.iterdir() if p.name.endswith(".tmp")))
        return real(src, dst)

    monkeypatch.setattr(era_map.os, "replace", spy)
    _propose_again(tmp_path, out, seed)
    assert staged == sorted([".chains.csv.tmp", ".counts.json.tmp", ".keys.csv.tmp",
                             ".p1_era_code_decisions.csv.tmp", ".review.csv.tmp"])
    assert not [p for d in (seed.parent, out) for p in d.iterdir() if p.name.endswith(".tmp")]


def test_propose_replaces_nothing_when_a_temporary_file_cannot_be_written(
        tmp_path, monkeypatch):
    _c, out, seed = run(tmp_path)
    era_map.write_seed(seed, [r for r in rows(seed) if r["line_item_code"] != "ATA000"])
    before = _files(seed, out)
    real = pathlib.Path.write_text

    def flaky(self, *args, **kwargs):
        if self.name == ".keys.csv.tmp":           # the fourth of the five
            raise OSError("disk full")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", flaky)
    with pytest.raises(OSError, match="disk full"):
        _propose_again(tmp_path, out, seed)
    monkeypatch.undo()
    assert _files(seed, out) == before
    assert not [p for d in (seed.parent, out) for p in d.iterdir() if p.name.endswith(".tmp")]
