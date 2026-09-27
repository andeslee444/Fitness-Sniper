"""Ruling R-DEC-DOSSIERDRIFT (controller, 2026-09-26): a dossier sentence that
contradicts its own citation never ships.

The raw dossier archives (data/research/dossiers-raw/*.json) record only the
cited fact_id for each claim — not the value the fact carried when the claim
was written — so the comparison is the ruling's fallback: parse the figure
the sentence states and hold it to the cited fact's CURRENT value, within
the rounding the sentence itself shows. Three checks, one rule:

  stated_figure       a dollar or HHI figure no stated figure of which agrees
                      with the cited fact's current value;
  concentration_band  a concentration word (low / unconcentrated /
                      moderately / highly concentrated) that contradicts the
                      2023 band of the cited HHI (govbudget.hhi_band);
  top_family          a "top / leading recipient family" claim that does not
                      name the family the cited concentration fact records.

The live shapes are the two DARPA dossiers the chain-G review found
(/program/0602025E/ and /program/0603467E/), quoted verbatim below.
"""
from __future__ import annotations

import duckdb
import pytest

from govbudget.dossiers.claim_drift import (
    ClaimDriftIndexError,
    FilerUniverse,
    LobbyingIndex,
    PageLobbying,
    PageRecipients,
    claim_contradictions,
    concentration_fact_index,
    linked_recipient_index,
    lobbying_mention_index,
    named_lobbying_filers,
    named_recipients,
    unlinked_recipients,
    unlisted_lobbying_filers,
)

HHI_UNITS = "Herfindahl-Hirschman Index"

# --- the live 0602025E / 0603467E claims (verbatim) and their cited facts ---
C_389 = (
    "Award dollars are spread across 189 recipient families, producing a low"
    " concentration score (Herfindahl-Hirschman Index of about 389), which"
    " indicates a relatively diverse contractor base overall."
)
C_RAYTHEON_468 = (
    "Across the program's award history, the leading recipient family by"
    " dollars is RAYTHEON, measured over roughly $4.68 billion in program"
    " dollars."
)
C_541 = (
    "Across the historical award family data for this program, spending is"
    " spread among roughly 160 recipient families with a concentration score"
    " (Herfindahl-Hirschman Index) of about 541, indicating a relatively"
    " unconcentrated field of recipients."
)
C_TOP_RAYTHEON = "The top recipient family across the program's award history is Raytheon."
C_358 = "Total program dollars tracked across award families amount to about $3.58 billion."

HHI_0602025E = {"units": HHI_UNITS, "recorded_value": "1284.683"}
USD_0602025E = {"units": "USD", "recorded_value": "469988662.800"}
HHI_0603467E = {"units": HHI_UNITS, "recorded_value": "4831.486"}
USD_0603467E = {"units": "USD", "recorded_value": "74376328.830"}
CONC_0602025E = {"family_key": "SYSTEM HIGH", "display_name": "SYSTEM HIGH CORPORATION",
                 "hhi": 1284.683}
CONC_0603467E = {"family_key": "GENERAL DYNAMICS", "display_name": "GENERAL DYNAMICS CORP",
                 "hhi": 4831.486}


class TestTheLiveContradictions:
    def test_0602025E_hhi_389_is_a_figure_and_a_band_contradiction(self):
        # 389 vs 1,284.683; "low concentration" vs moderate (2023 bands)
        assert claim_contradictions(C_389, HHI_0602025E, CONC_0602025E) == [
            "stated_figure", "concentration_band"]

    def test_0602025E_raytheon_468b_is_a_figure_and_a_family_contradiction(self):
        # $4.68B vs $469,988,662.80; RAYTHEON vs SYSTEM HIGH
        assert claim_contradictions(C_RAYTHEON_468, USD_0602025E, CONC_0602025E) == [
            "stated_figure", "top_family"]

    def test_0603467E_hhi_541_unconcentrated_contradicts_4831(self):
        assert claim_contradictions(C_541, HHI_0603467E, CONC_0603467E) == [
            "stated_figure", "concentration_band"]

    def test_0603467E_top_family_raytheon_contradicts_general_dynamics(self):
        assert claim_contradictions(C_TOP_RAYTHEON, HHI_0603467E, CONC_0603467E) == [
            "top_family"]

    def test_0603467E_358b_contradicts_74m(self):
        assert claim_contradictions(C_358, USD_0603467E, CONC_0603467E) == [
            "stated_figure"]


class TestTrueSentencesPass:
    """Measured phrasings from the live corpus that agree with their facts."""

    @pytest.mark.parametrize(
        "text,units,value",
        [
            ("The program's total funding is $1,997,341 thousand (about $2.0 billion)"
             " requested for FY 2026.", "USD thousands", "1997341.000"),
            ("That is a year-over-year increase of $1,055,154 thousand (about $1.1"
             " billion) from FY2025 to FY2026.", "USD thousands", "1055154.000"),
            ("That is a year-over-year increase of $2,085,072 thousand (roughly $2.09"
             " billion) from FY2025 to FY2026.", "USD thousands", "2085072.000"),
            # a signed fact stated as a magnitude
            ("That fiscal year 2026 total represents a decrease of about $32.8 million"
             " ($32,842 thousand), or roughly 2 percent, from the fiscal year 2025"
             " level.", "USD thousands", "-32842.000"),
            # several figures, one of which is the cited one
            ("COLUMBIA Class Submarine FY2024 actuals came in about $2.0 billion above"
             " the original PB2024 request (comparing the PB2024 FY2024 request of"
             " roughly $5.83 billion to the PB2026-reported FY2024 actual of roughly"
             " $7.79 billion), a gap of about 33.5 percent.", "USD thousands",
             "1955000.000"),
            ("For fiscal year 2025, the program's total was about $940.4 million"
             " ($940,431 thousand).", "USD thousands", "940431.000"),
            # no figure at all — nothing to contradict
            ("A 2025 Lockheed Martin filing referenced the FY26 National Defense"
             " Authorization Act.", "USD", "30000"),
            # a percentage is not a dollar figure
            ("That represents a 438.32% jump between fiscal years 2025 and 2026.",
             "USD thousands", "1340050.000"),
        ],
    )
    def test_agreeing_dollar_claims(self, text, units, value):
        assert claim_contradictions(text, {"units": units, "recorded_value": value}) == []

    def test_an_hhi_within_the_sentence_rounding_and_its_true_band(self):
        text = ("Award dollars are moderately concentrated (Herfindahl-Hirschman Index"
                " of about 1,285).")
        assert claim_contradictions(text, HHI_0602025E, CONC_0602025E) == []

    def test_a_rounded_hhi_is_held_to_the_rounding_it_shows(self):
        # "about 1,300" shows rounding to the hundred: 1,284.683 is within it.
        text = ("The concentration score stands at about 1,300, a moderately"
                " concentrated field.")
        assert claim_contradictions(text, HHI_0602025E, CONC_0602025E) == []

    def test_highly_concentrated_4831(self):
        text = "The field is highly concentrated (HHI of 4,831)."
        assert claim_contradictions(text, HHI_0603467E, CONC_0603467E) == []

    def test_top_family_named_by_display_name(self):
        text = "The top recipient family is General Dynamics Corp."
        assert claim_contradictions(text, HHI_0603467E, CONC_0603467E) == []

    def test_top_family_named_by_family_key_inside_a_longer_name(self):
        text = "The leading recipient family is System High Corporation."
        assert claim_contradictions(text, USD_0602025E, CONC_0602025E) == []


class TestTheRuleCanFail:
    def test_a_truncated_hhi_beyond_its_own_rounding_fails(self):
        # 1,284.683 rounds to 1,285; "1,284" shows whole points and is off.
        text = "The concentration score (HHI) is 1,284."
        assert "stated_figure" in claim_contradictions(text, HHI_0602025E)

    def test_a_negated_band_word_contradicting_the_band_fails(self):
        text = "The field is not highly concentrated (HHI of 4,831)."
        assert claim_contradictions(text, HHI_0603467E, CONC_0603467E) == [
            "concentration_band"]

    def test_a_negated_band_word_agreeing_with_the_band_passes(self):
        text = "The field is not highly concentrated (HHI of about 1,285)."
        assert claim_contradictions(text, HHI_0602025E, CONC_0602025E) == []

    def test_moderately_concentrated_vs_a_highly_concentrated_index_fails(self):
        text = "Award dollars are moderately concentrated."
        assert claim_contradictions(text, HHI_0603467E) == ["concentration_band"]

    def test_the_band_comes_from_the_concentration_block_on_a_dollars_fact(self):
        # A band word on a claim citing the block's DOLLARS fact is held to the
        # block's HHI (the fact's own recorded value is dollars, not an index).
        text = "The program's award dollars are highly concentrated."
        assert claim_contradictions(text, USD_0602025E, CONC_0602025E) == [
            "concentration_band"]

    def test_a_lower_bound_qualifier(self):
        fact = {"units": "USD", "recorded_value": "2900000000"}
        assert claim_contradictions("It received more than $2 billion.", fact) == []
        assert claim_contradictions("It received under $1 billion.", fact) == [
            "stated_figure"]

    def test_a_top_family_claim_on_a_fact_that_records_no_family_is_not_checked(self):
        text = "The top recipient family is Raytheon."
        assert claim_contradictions(text, {"units": "USD", "recorded_value": None}) == []

    def test_no_fact_no_check(self):
        assert claim_contradictions(C_389, None) == []


def test_concentration_fact_index_reads_the_mart(tmp_path):
    """fid -> the family (and HHI) the concentration row that minted it
    records, for both bases, with dim_entities' display name."""
    from govbudget.export_site import fact_id_derived

    db = tmp_path / "c.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "create table fct_program_concentration (pe_bli varchar, hhi_all double,"
        " top_family_all varchar, hhi_high double, top_family_high varchar)")
    con.execute("insert into fct_program_concentration values"
                " ('0602025E', 1284.683, 'SYSTEM HIGH', null, null),"
                " ('0603467E', 4831.486, 'GENERAL DYNAMICS', 9000.0, 'RAYTHEON')")
    con.execute("create table dim_entities (family_key varchar, display_name varchar)")
    con.execute("insert into dim_entities values ('SYSTEM HIGH', 'SYSTEM HIGH CORPORATION')")
    con.close()

    idx = concentration_fact_index(db)
    all_hhi = fact_id_derived("concentration", "0602025E", "hhi")
    assert all_hhi == "b45aa52df18b0f7c"
    assert idx[all_hhi] == {"family_key": "SYSTEM HIGH",
                            "display_name": "SYSTEM HIGH CORPORATION",
                            "hhi": 1284.683}
    dollars = fact_id_derived("concentration", "0602025E", "program_dollars")
    assert idx[dollars]["family_key"] == "SYSTEM HIGH"
    # a high basis with no family records none
    assert fact_id_derived("concentration", "0602025E", "hhi_high") not in idx
    high = fact_id_derived("concentration", "0603467E", "program_dollars_high")
    assert idx[high] == {"family_key": "RAYTHEON", "display_name": None, "hhi": 9000.0}


def test_concentration_fact_index_unknown_is_empty():
    assert concentration_fact_index(None) == {}


# ---------------------------------------------------------------------------
# Round 2 (R-DEC-DOSSIERDRIFT, 2026-09-26): ANY fact kind. The ruling holds a
# stated figure to its cited fact's current value whatever the kind: a
# derived fact's recorded_value, a workbook cell's amount_thousands (read in
# the row's own units, as the site's citation card does) and a J-book PDF
# glyph's amount_text (parsed as the receipt exporter parses a printed
# amount, budget_pdf_receipts.amount). Round 1 read recorded_value only, so
# both live shapes below stayed published.
# ---------------------------------------------------------------------------

#: /program/0607210D8Z/ what_it_is[4], verbatim. Cites 6ce1109572aa7881, the
#: R-1 FY2024 actuals cell J1074 = 897,631 thousand. Its parts sum to $2,328.370
#: MILLION (the line's FY2026 total, cell P1074 = 2,328,370 thousand); the
#: sentence prints "billion", 1,000 times the cell.
C_0607210D8Z = (
    "The FY 2026 request includes $273.379 million of discretionary funding and"
    " $2,054.991 million of mandatory (reconciliation) funding, for a total of"
    " $2,328.370 billion."
)
WB_0607210D8Z_FY2024 = {"kind": "workbook", "units": "USD thousands",
                        "recorded_value": None, "amount_thousands": 897631.0,
                        "amount_text": None}
WB_0607210D8Z_FY2026 = {"kind": "workbook", "units": "USD thousands",
                        "recorded_value": None, "amount_thousands": 2328370.0,
                        "amount_text": None}
#: /program/0604250D8Z/ why_it_matters[6], verbatim. Cites ae4f1bee1cec54e4,
#: the R-1 FY2026 total cell P957 = 1,163,452 thousand; every figure in the
#: sentence is a PDI sub-total from the narrative.
C_0604250D8Z = (
    "The SCO's FY2026 Pacific Deterrence Initiative (PDI) spending under"
    " Exercises, Training, Experimentation, and Innovation includes $639.296"
    " million discretionary and $167.000 million mandatory for a total of"
    " $806.296 million — an increase of $150.786 million from FY2025 —"
    " with five new capability projects transitioning into execution in FY"
    " 2026."
)
WB_0604250D8Z = {"kind": "workbook", "units": "USD thousands",
                 "recorded_value": None, "amount_thousands": 1163452.0,
                 "amount_text": None}


class TestAnyFactKind:
    def test_0607210D8Z_billion_total_against_the_fy2024_cell_is_withheld(self):
        assert claim_contradictions(C_0607210D8Z, WB_0607210D8Z_FY2024) == ["stated_figure"]

    def test_0607210D8Z_is_withheld_even_against_its_true_fy2026_cell(self):
        # $2,328.370 billion is 1,000x the cell; neither part is the total.
        assert claim_contradictions(C_0607210D8Z, WB_0607210D8Z_FY2026) == ["stated_figure"]

    def test_the_same_total_printed_in_millions_agrees_with_the_fy2026_cell(self):
        text = "The FY 2026 request totals $2,328.370 million."
        assert claim_contradictions(text, WB_0607210D8Z_FY2026) == []

    def test_0604250D8Z_pdi_subtotals_against_the_program_total_cell_are_withheld(self):
        assert claim_contradictions(C_0604250D8Z, WB_0604250D8Z) == ["stated_figure"]

    def test_a_true_workbook_claim_is_kept(self):
        text = ("The program's total funding is $1,997,341 thousand (about $2.0"
                " billion) requested for FY 2026.")
        fact = {"kind": "workbook", "units": "USD thousands",
                "amount_thousands": 1997341.0}
        assert claim_contradictions(text, fact) == []

    def test_a_workbook_amount_serialized_as_a_string_is_read(self):
        fact = {"kind": "workbook", "units": "USD thousands", "amount_thousands": "897631.0"}
        assert claim_contradictions("It came to about $897.6 million.", fact) == []
        assert claim_contradictions("It came to about $2.3 billion.", fact) == ["stated_figure"]

    @pytest.mark.parametrize("text,expected", [
        ("The line requests about $7.7 billion.", []),
        ("The line requests $7,712.804 million.", []),
        ("The line requests $8.1 billion.", ["stated_figure"]),
    ])
    def test_jbook_pdf_amount_text_in_millions(self, text, expected):
        # ee659a10b0133d41 (0604250D8Z): the glyph "7,712.804", USD millions
        fact = {"kind": "jbook_pdf", "units": "USD millions", "recorded_value": None,
                "amount_thousands": None, "amount_text": "7,712.804"}
        assert claim_contradictions(text, fact) == expected

    @pytest.mark.parametrize("text,expected", [
        ("A decrease of $2,647,563 thousand.", []),
        ("About $2.65 billion.", []),
        ("About $2.6 billion.", []),       # +/- $0.05B shown; 2.6476 is inside
        ("About $2.7 billion.", ["stated_figure"]),  # 2.6476 is 0.0524 away
    ])
    def test_jbook_pdf_parenthesized_thousands_glyph(self, text, expected):
        # the receipt exporter's parse drops the parentheses (sign ignored)
        fact = {"kind": "jbook_pdf", "units": "USD thousands", "amount_text": "(2,647,563)"}
        assert claim_contradictions(text, fact) == expected

    def test_an_unresolved_jbook_pdf_glyph_is_not_checked(self):
        # an 'unresolved' provenance row carries no units and no glyph
        fact = {"kind": "jbook_pdf", "units": None, "amount_text": None}
        assert claim_contradictions("It costs $1 trillion.", fact) == []

    def test_a_non_numeric_glyph_is_not_checked(self):
        fact = {"kind": "jbook_pdf", "units": "USD millions", "amount_text": "FY 2026"}
        assert claim_contradictions("It costs $1 trillion.", fact) == []

    def test_recorded_value_takes_precedence_over_a_cell(self):
        fact = {"kind": "derived", "units": "USD thousands", "recorded_value": "415751.000",
                "amount_thousands": 1.0}
        assert claim_contradictions("About $415.8 million.", fact) == []


# ---------------------------------------------------------------------------
# Round 2: recipient-list claims. A sentence naming the recipients of the
# program's awards ("Recorded recipients ... include A, B, ..." / "awards went
# to A and B" / "A is a recipient linked to this budget line") must name only
# recipients the page lists: every named recipient must be among the page's
# linked-award recipient families (the Related awards table's recipient_name,
# its family_key via entity_xwalk and dim_entities' display_name — the
# concentration mart's own family rule), compared as normalized names.
# ---------------------------------------------------------------------------

#: /program/0603467E/ players[3], verbatim. Cites 3b594c81c720df35 (program
#: dollars), which states no figure — so no round-1 check applied.
C_RECIPIENTS_0603467E = (
    "Recorded recipients of awards linked to the program include Booz Allen"
    " Hamilton, The Johns Hopkins University Applied Physics Laboratory, Leidos,"
    " Raytheon Company, Lockheed Martin Corporation, Northrop Grumman Systems"
    " Corp, SRI International, and the Massachusetts Institute of Technology."
)
#: The 17 links /program/0603467E/ publishes (read-only from the mart,
#: 2026-09-26) as (recipient_name, family_key, display_name) — 14 distinct.
LINKS_0603467E = [
    ("APPLIED PHYSICAL SCIENCES CORP", "GENERAL DYNAMICS", "GENERAL DYNAMICS CORP"),
    ("HONEYWELL INTERNATIONAL INC", "HONEYWELL INTERNATIONAL", "HONEYWELL INTERNATIONAL INC"),
    ("KBR WYLE SERVICES, LLC", "KBR WYLE SERVICES", "KBR WYLE SERVICES, LLC"),
    ("L3 TECHNOLOGIES, INC.", "L3HARRIS TECHNOLOGIES", "L3HARRIS TECHNOLOGIES, INC"),
    ("NORTHROP GRUMMAN SYSTEMS CORP", "NORTHROP GRUMMAN", "NORTHROP GRUMMAN CORPORATION"),
    ("NORTHROP GRUMMAN SYSTEMS CORPORATION", "NORTHROP GRUMMAN",
     "NORTHROP GRUMMAN CORPORATION"),
    ("PHOTONIC SYSTEMS, INC.", "PHOTONIC SYSTEMS", "PHOTONIC SYSTEMS, INC."),
    ("RAYTHEON COMPANY", "RAYTHEON", "RAYTHEON COMPANY"),
    ("RAYTHEON COMPANY", "RTX", "RTX CORP"),
    ("ROCKWELL COLLINS, INC.", "RTX", "RTX CORP"),
    ("RTX CORPORATION", "RTX", "RTX CORP"),
    ("SPATIAL INTEGRATED SYSTEMS INC", "SPATIAL INTEGRATED SYSTEMS",
     "SPATIAL INTEGRATED SYSTEMS INC"),
    ("SYSTEM HIGH CORPORATION", "SYSTEM HIGH", "SYSTEM HIGH CORPORATION"),
    ("UNIVERSITY OF SOUTHERN CALIFORNIA", "UNIVERSITY OF SOUTHERN CALIFORNIA",
     "UNIVERSITY OF SOUTHERN CALIFORNIA"),
]
#: /program/3010-SCN/'s own links (account 1611N).
LINKS_3010_SCN = [
    ("BAE SYSTEMS MARITIME SOLUTIONS SAN DIEGO INC.", "BAE SYSTEMS", "BAE SYSTEMS PLC"),
    ("HUNTINGTON INGALLS INCORPORATED", "HUNTINGTON INGALLS INDUSTRIES",
     "HUNTINGTON INGALLS INDUSTRIES, INC"),
    ("RAYTHEON COMPANY", "RAYTHEON", "RAYTHEON COMPANY"),
]


class TestRecipientList:
    def test_0603467E_six_of_eight_named_recipients_unlinked_is_withheld(self):
        page = PageRecipients.from_links(LINKS_0603467E)
        fact = {"kind": "derived", "units": "USD", "recorded_value": "74376328.830"}
        assert claim_contradictions(C_RECIPIENTS_0603467E, fact, None, page) == [
            "recipient_list"]
        assert unlinked_recipients(C_RECIPIENTS_0603467E, page) == [
            "Booz Allen Hamilton",
            "The Johns Hopkins University Applied Physics Laboratory",
            "Leidos",
            "Lockheed Martin Corporation",
            "SRI International",
            "the Massachusetts Institute of Technology",
        ]

    def test_the_names_are_parsed_as_the_sentence_lists_them(self):
        assert named_recipients(C_RECIPIENTS_0603467E) == [
            "Booz Allen Hamilton",
            "The Johns Hopkins University Applied Physics Laboratory",
            "Leidos",
            "Raytheon Company",
            "Lockheed Martin Corporation",
            "Northrop Grumman Systems Corp",
            "SRI International",
            "the Massachusetts Institute of Technology",
        ]

    def test_a_list_whose_names_are_all_linked_stays(self):
        page = PageRecipients.from_links(LINKS_0603467E)
        text = ("Recorded recipients of awards linked to the program include Raytheon"
                " Company, Northrop Grumman Systems Corp, System High Corporation, and"
                " the University of Southern California.")
        assert claim_contradictions(text, None, None, page) == []

    def test_names_match_at_the_family_level(self):
        page = PageRecipients.from_links(LINKS_0603467E)
        # L3Harris is L3 TECHNOLOGIES' family; Rockwell Collins a recipient_name
        text = ("Recipients of the program's linked awards include L3Harris"
                " Technologies, General Dynamics and Rockwell Collins.")
        assert unlinked_recipients(text, page) == []

    def test_awards_went_to_resolves_a_subsidiary_through_the_family_index(self):
        # 0602025E players[3]: CACI TECHNOLOGIES, LLC is not a recipient_name
        # the page lists; entity_xwalk files it under CACI INTERNATIONAL, the
        # family of the page's CACI, INC. - FEDERAL link.
        text = ("Other large awards went to SYSTEM HIGH CORPORATION (about $114.7"
                " million) and CACI TECHNOLOGIES, LLC (about $113.6 million).")
        links = [("SYSTEM HIGH CORPORATION", "SYSTEM HIGH", "SYSTEM HIGH CORPORATION"),
                 ("CACI, INC. - FEDERAL", "CACI INTERNATIONAL", "CACI INTERNATIONAL INC")]
        with_xwalk = PageRecipients.from_links(
            links, family_by_name={"CACI TECHNOLOGIES": frozenset({"CACI INTERNATIONAL"})})
        assert named_recipients(text) == ["SYSTEM HIGH CORPORATION", "CACI TECHNOLOGIES, LLC"]
        assert claim_contradictions(text, None, None, with_xwalk) == []
        without = PageRecipients.from_links(links)
        assert unlinked_recipients(text, without) == ["CACI TECHNOLOGIES, LLC"]

    def test_the_largest_award_went_to_an_unlinked_recipient(self):
        # 0602025E players[2]: no 0602025E link reaches INDYNE.
        text = ("The largest single tracked award, worth about $210.1 million, went"
                " to INDYNE, INC. (contract FA251718C8000, Alaska).")
        page = PageRecipients.from_links(
            [("SYSTEM HIGH CORPORATION", "SYSTEM HIGH", "SYSTEM HIGH CORPORATION")])
        assert unlinked_recipients(text, page) == ["INDYNE, INC."]

    def test_the_single_name_linked_recipient_form(self):
        text = ("Huntington Ingalls Incorporated is a recipient linked to this budget"
                " line through contract records.")
        assert claim_contradictions(
            text, None, None, PageRecipients.from_links(LINKS_3010_SCN)) == []
        assert claim_contradictions(
            text, None, None, PageRecipients.from_links(LINKS_0603467E)) == [
            "recipient_list"]

    def test_and_and_ampersand_inside_a_linked_name(self):
        page = PageRecipients.from_links([
            ("TEST & EVALUATION SERVICES AND TECHNOLOGIES, LLC",
             "TEST EVALUATION SERVICES AND TECHNOLOGIES",
             "TEST & EVALUATION SERVICES AND TECHNOLOGIES, LLC"),
            ("THE BOEING COMPANY", "BOEING", "THE BOEING COMPANY"),
        ])
        text = ("Recipients of linked awards include Test & Evaluation Services and"
                " Technologies, LLC and Boeing.")
        assert unlinked_recipients(text, page) == []

    def test_a_page_with_no_links_withholds_every_named_recipient(self):
        text = "Awards went to Leidos and SAIC."
        assert claim_contradictions(text, None, None, PageRecipients.from_links([])) == [
            "recipient_list"]

    def test_without_a_recipient_index_the_leg_does_not_run(self):
        assert claim_contradictions(C_RECIPIENTS_0603467E, None, None, None) == []

    def test_a_sentence_listing_no_recipients_is_not_checked(self):
        page = PageRecipients.from_links([])
        for text in (
            "Award dollars are spread across 160 recipient families.",
            "Key objectives include improved battle-space target detection.",
            "The Engineering and Manufacturing Development contract was awarded to"
            " Boeing on 24 February 2011.",
        ):
            assert claim_contradictions(text, None, None, page) == [], text


# ---------------------------------------------------------------------------
# Round 2: FAIL CLOSED. A supplied mart that cannot be read is an error, never
# an empty index — an empty index silently skips the family and recipient
# legs, and one of the chain-G contradictions (0603467E "top recipient family
# ... is Raytheon") is caught by the family leg alone.
# ---------------------------------------------------------------------------

def test_concentration_fact_index_raises_on_an_unreadable_mart(tmp_path):
    db = tmp_path / "narrow.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table fct_program_concentration (pe_bli varchar, hhi_all double)")
    con.close()
    with pytest.raises(ClaimDriftIndexError, match="fct_program_concentration"):
        concentration_fact_index(db)


def test_concentration_fact_index_raises_on_a_missing_file(tmp_path):
    with pytest.raises(ClaimDriftIndexError):
        concentration_fact_index(tmp_path / "absent.duckdb")


def test_concentration_fact_index_raises_without_dim_entities(tmp_path):
    db = tmp_path / "c.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "create table fct_program_concentration (pe_bli varchar, hhi_all double,"
        " top_family_all varchar, hhi_high double, top_family_high varchar)")
    con.close()
    with pytest.raises(ClaimDriftIndexError, match="dim_entities"):
        concentration_fact_index(db)


def _recipient_mart(db):
    """dim_programs + the three marts the recipient index reads, in the
    production 3010 shape: a shared code split by ACCOUNT, and an ordinary
    program."""
    con = duckdb.connect(str(db))
    con.execute("create table dim_programs (pe_bli varchar, account varchar,"
                " account_title varchar, org varchar, exhibit_family varchar)")
    con.executemany("insert into dim_programs values (?,?,?,?,?)", [
        ("0603467E", None, None, "DARPA", "rdte"),
        ("3010", "1611N", "Shipbuilding and Conversion, Navy", "N", "procurement"),
        ("3010", "1810N", "Other Procurement, Navy", "N", "procurement"),
    ])
    con.execute("create table fct_budget_to_awards (pe_bli varchar, account varchar,"
                " organization varchar, award_piid varchar, recipient_name varchar,"
                " recipient_uei varchar)")
    con.executemany("insert into fct_budget_to_awards values (?,?,?,?,?,?)", [
        ("0603467E", None, "DARPA", "HR1", "APPLIED PHYSICAL SCIENCES CORP", "UEI-APS"),
        ("0603467E", None, "DARPA", "HR2", "RAYTHEON COMPANY", "UEI-RAY"),
        ("3010", "1611N", "N", "N1", "HUNTINGTON INGALLS INCORPORATED", "UEI-HII"),
        ("3010", "1810N", "N", "N2", "BAE SYSTEMS MARITIME SOLUTIONS NORFOLK INC.", "UEI-BAE"),
    ])
    con.execute("create table entity_xwalk (recipient_uei varchar, recipient_name varchar,"
                " parent_name varchar, family_key varchar)")
    con.executemany("insert into entity_xwalk values (?,?,?,?)", [
        ("UEI-APS", "APPLIED PHYSICAL SCIENCES CORP", "GENERAL DYNAMICS CORPORATION",
         "GENERAL DYNAMICS"),
        ("UEI-RAY", "RAYTHEON COMPANY", "RTX CORPORATION", "RTX"),
        ("UEI-HII", "HUNTINGTON INGALLS INCORPORATED", "HUNTINGTON INGALLS INDUSTRIES INC",
         "HUNTINGTON INGALLS INDUSTRIES"),
        ("UEI-BAE", "BAE SYSTEMS MARITIME SOLUTIONS NORFOLK INC.", "BAE SYSTEMS PLC",
         "BAE SYSTEMS"),
        ("UEI-EB", "ELECTRIC BOAT CORPORATION", "GENERAL DYNAMICS CORPORATION",
         "GENERAL DYNAMICS"),
    ])
    con.execute("create table dim_entities (family_key varchar, display_name varchar)")
    con.executemany("insert into dim_entities values (?,?)", [
        ("GENERAL DYNAMICS", "GENERAL DYNAMICS CORP"), ("RTX", "RTX CORP"),
    ])
    con.close()


def test_linked_recipient_index_is_page_keyed(tmp_path):
    db = tmp_path / "r.duckdb"
    _recipient_mart(db)
    index = linked_recipient_index(db)

    darpa = index.for_page("0603467E")
    assert "GENERAL DYNAMICS" in darpa.families and "RTX" in darpa.families
    # a sibling family member the page does not list, named by its family
    assert unlinked_recipients("Awards went to General Dynamics.", darpa) == []
    # ... and by a subsidiary's own name, resolved through entity_xwalk
    assert unlinked_recipients("Awards went to Electric Boat Corporation.", darpa) == []
    assert unlinked_recipients("Awards went to Leidos.", darpa) == ["Leidos"]

    # a shared code's members are two pages with two link sets (#82)
    scn = index.for_page("3010-SCN")
    assert unlinked_recipients(
        "Huntington Ingalls Incorporated is a recipient linked to this budget line.",
        scn) == []
    assert unlinked_recipients(
        "BAE Systems Maritime Solutions Norfolk Inc. is a recipient linked to this"
        " budget line.", scn) == ["BAE Systems Maritime Solutions Norfolk Inc."]
    # a page with no links at all lists no recipients
    assert index.for_page("3010").families == frozenset()


def test_linked_recipient_index_unknown_is_none():
    assert linked_recipient_index(None) is None


def test_linked_recipient_index_raises_on_an_unreadable_mart(tmp_path):
    db = tmp_path / "r.duckdb"
    _recipient_mart(db)
    con = duckdb.connect(str(db))
    con.execute("drop table entity_xwalk")
    con.close()
    with pytest.raises(ClaimDriftIndexError, match="entity_xwalk"):
        linked_recipient_index(db)


# ---------------------------------------------------------------------------
# Round 3 (R-DEC-DOSSIERDRIFT, 2026-09-26): FISCAL-YEAR LABEL AGREEMENT,
# sub-reason `fiscal_year`. A claim that names a fiscal year for a figure
# ("FY2026", "fiscal year 2026", "FY26", or a book-relative "current year",
# "prior year", "budget year") must cite a fact whose column is that year.
# What each fact kind records:
#   workbook   amount_type ("fy_2025_enacted" -> FY2025), read by
#              export_site._amount_type_meta, the rule every workbook
#              receipt/sidecar label uses;
#   jbook_pdf  scenario (PriorYear / CurrentYear / BudgetYearOne[Base] /
#              AllPriorYears) — no column year of its own, so it is derived
#              the way the exporter labels detail columns:
#              export_site._scenario_meta(scenario, _SUMMARY_EDITION), the
#              PB2026 fence (CurrentYear = FY2025). AllPriorYears is no single
#              year and is not checked.
# The year a figure carries is the one the sentence binds to it: a leading
# frame ("For FY2026, ... $X"), a label in the same clause before it, a
# trailing "in / for / during [the] <label>" or a parenthesis right after it.
# The check applies to the figures that AGREE with the cited value (a figure
# that does not agree is the stated_figure leg's); the claim fails when every
# agreeing figure carries a year that is not the column's.
# ---------------------------------------------------------------------------

#: /program/1203154SF/ what_it_is[3], verbatim. Cites ef8d1da3e605d4f0, the
#: glyph "243.282" (USD millions) on PDF 40f1f67d… page 654 under the
#: "FY 2025" column header — J-book scenario CurrentYear. The row's FY 2026
#: Total is 1.916; the sentence gives the FY2025 amount as FY2026's.
C_1203154SF = (
    "For FY2026, the Auxiliary Payloads project is funded at about $243.3"
    " million (its Current Year amount), making it the dominant project within"
    " the program."
)
JB_1203154SF = {"kind": "jbook_pdf", "units": "USD millions", "amount_text": "243.282",
                "scenario": "CurrentYear", "amount_type": None}


def _wb(value, amount_type):
    return {"kind": "workbook", "units": "USD thousands", "amount_thousands": value,
            "amount_type": amount_type, "scenario": None}


def _jb(text, units, scenario):
    return {"kind": "jbook_pdf", "units": units, "amount_text": text,
            "scenario": scenario, "amount_type": None}


class TestFiscalYearLabel:
    def test_1203154SF_fy2026_label_on_a_current_year_cell_is_withheld(self):
        assert claim_contradictions(C_1203154SF, JB_1203154SF) == ["fiscal_year"]

    def test_the_same_sentence_correctly_labelled_stays(self):
        text = C_1203154SF.replace("For FY2026,", "For FY2025,")
        assert claim_contradictions(text, JB_1203154SF) == []
        assert claim_contradictions(
            "The Auxiliary Payloads project is funded at about $243.3 million (its"
            " Current Year amount).", JB_1203154SF) == []

    def test_a_budget_year_cell_named_as_fy2026_stays(self):
        fact = dict(JB_1203154SF, scenario="BudgetYearOne")
        assert claim_contradictions(C_1203154SF.replace(" (its Current Year amount)", ""),
                                    fact) == []
        # ... and the book's "Current Year" is not its budget year
        assert claim_contradictions(
            "The project is funded at about $243.3 million (its Current Year amount).",
            fact) == ["fiscal_year"]

    @pytest.mark.parametrize("text,fact", [
        # /program/0605180N/ why_it_matters[0]: "in FY 2025" belongs to the
        # $755M figure before it; the cited $1,243,978 thousand is FY 2026's.
        ("The program's total funding grows from $755,316 thousand (about $755"
         " million) in FY 2025 to $1,243,978 thousand (about $1.24 billion)"
         " requested for FY 2026.", _wb(1243978.0, "fy_2026_total")),
        # /program/0572EP1000/ why_it_matters[3]: the cited figure is the
        # current-year one (J-book CurrentYear = FY2025 in PB2026).
        ("The FY 2026 request of about $1,084.6 million is close to the"
         " current-year level of about $1,054.3 million, a modest year-over-year"
         " rise after the higher FY 2024 spend.", _jb("1,054.260", "USD millions",
                                                      "CurrentYear")),
        # /program/0604288F/ why_it_matters[6]
        ("That same SAOC project line was funded at about $1,617.2 million in the"
         " current year (FY2025) and about $717.6 million in the prior year"
         " (FY2024), showing the program's rapid growth as development advances.",
         _jb("1,617,187", "USD thousands", "CurrentYear")),
        # /program/0604288F/ why_it_matters[5]
        ("The money flows through a single named project, the Survivable Airborne"
         " Operations Center, funded at about $1,826.3 million in the FY2026 budget"
         " year.", _jb("1,826,328", "USD thousands", "BudgetYearOne")),
        # /program/0207110F/ players[1]: "in FY2026" is the later project line's
        ("In FY2025 the program was carried under the Next Generation Air Dominance"
         " (NGAD) Platform project, funded at $2,424.208 million that year before"
         " transitioning to the named F-47 project line in FY2026.",
         _jb("2,424,208", "USD thousands", "CurrentYear")),
        # /program/0207110F/ why_it_matters[2]: "the FY2026 request" is a new clause
        ("In FY2024 the program recorded actual spending of $2,346,905 thousand"
         " (about $2.3 billion), so the FY2026 request is roughly half again as"
         " large as that recent execution level.", _wb(2346905.0, "fy_2024_actuals")),
        # /program/0195/ why_it_matters[0]
        ("The Navy requested about $1.50 billion (USD, $1,503,556 thousand) for the"
         " E-2D in Fiscal Year 2026, a large increase over the roughly $571 million"
         " actually spent in Fiscal Year 2024.", _wb(1503556.0, "fy_2026_total")),
        # /program/1206446SF/ what_it_is[4]
        ("Nearly all of the FY 2026 money flows through a single project, Resilient"
         " MW/MT - LEO (project 657LEO), funded at about $1,757.4 million for the"
         " budget year.", _jb("1,757.354", "USD millions", "BudgetYearOne")),
    ])
    def test_the_live_correctly_labelled_claims_stay(self, text, fact):
        assert claim_contradictions(text, fact) == []

    @pytest.mark.parametrize("text", [
        "For fiscal year 2026, Congress enacted about $2.51 billion.",
        "In FY26 the program was enacted at $2,511,893 thousand.",
        "The program was enacted at $2,511,893 thousand for FY 2026.",
        "The FY2026 enacted level is about $2.51 billion.",
    ])
    def test_a_workbook_cell_named_for_another_year_is_withheld(self, text):
        fact = _wb(2511893.0, "fy_2025_enacted")
        assert claim_contradictions(text, fact) == ["fiscal_year"]
        assert claim_contradictions(
            text.replace("2026", "2025").replace("FY26", "FY25"), fact) == []

    def test_a_trailing_label_binds_the_figure_before_it(self):
        fact = _jb("1,617,187", "USD thousands", "CurrentYear")
        assert claim_contradictions(
            "The line was funded at about $1,617.2 million in the prior year (FY2024).",
            fact) == ["fiscal_year"]

    def test_any_correctly_labelled_agreeing_figure_keeps_the_claim(self):
        # the same value stated twice; one statement carries the column's year
        fact = _wb(2511893.0, "fy_2025_enacted")
        assert claim_contradictions(
            "FY2025 enacted $2,511,893 thousand; the program's history shows"
            " $2,511,893 thousand in FY2026 as well.", fact) == []

    def test_a_disagreeing_figure_is_the_stated_figure_legs_not_this_one(self):
        fact = _wb(2511893.0, "fy_2025_enacted")
        assert claim_contradictions("For FY2026, about $9.9 billion.", fact) == [
            "stated_figure"]

    @pytest.mark.parametrize("text", [
        # an unlabelled figure, a year range, a year that is not a period label
        "Congress enacted about $2.51 billion.",
        "Across FY2023-FY2027, about $2.51 billion was enacted.",
        "The FY2016 SSNs received $2,511,893 thousand in the enacted budget.",
        # a figure whose only label is in another clause, after a comma
        "The line saw $2,511,893 thousand enacted, while the FY2026 request grew.",
    ])
    def test_what_binds_no_year_is_not_checked(self, text):
        assert claim_contradictions(text, _wb(2511893.0, "fy_2025_enacted")) == []

    def test_a_relative_label_on_a_workbook_cell_is_not_resolved(self):
        # /program/1000/ why_it_matters[3]: a workbook cell records its year
        # (fy_2025_enacted) but not the edition a "current year" is relative
        # to, so the relative word is not read — only explicit years are.
        text = ("The FY 2026 request of about $2,392.6 million is essentially flat"
                " against the current-year enacted level of about $2,392.2 million.")
        assert claim_contradictions(text, _wb(2392190.0, "fy_2025_enacted")) == []
        assert claim_contradictions(text, _wb(2392190.0, "fy_2024_actuals")) == []

    def test_all_prior_years_and_facts_without_a_column_are_not_checked(self):
        cumulative = _jb("7,712.804", "USD millions", "AllPriorYears")
        assert claim_contradictions(
            "In FY2026 the project had drawn about $7.71 billion.", cumulative) == []
        # a derived fact records a formula, not a column; a row read without
        # its scenario / amount_type (citations.json alone) has no year
        for fact in ({"kind": "derived", "units": "USD thousands",
                      "recorded_value": "2511893.000"},
                     {"kind": "workbook", "units": "USD thousands",
                      "amount_thousands": 2511893.0}):
            assert claim_contradictions("For FY2026, $2,511,893 thousand.", fact) == []

    def test_fact_fiscal_year(self):
        from govbudget.dossiers.claim_drift import fact_fiscal_year

        assert fact_fiscal_year(JB_1203154SF) == 2025
        assert fact_fiscal_year(_jb("1", "USD millions", "PriorYear")) == 2024
        assert fact_fiscal_year(_jb("1", "USD millions", "BudgetYearOneBase")) == 2026
        assert fact_fiscal_year(_jb("1", "USD millions", "AllPriorYears")) is None
        assert fact_fiscal_year(_wb(1.0, "fy_2018_total_pb_requests_with_cr_adj_base_oco")) == 2018
        assert fact_fiscal_year({"kind": "derived"}) is None


def test_fact_column_index_reads_the_citations_parquet(tmp_path):
    from govbudget.dossiers.claim_drift import fact_column_index

    pq = tmp_path / "citations.parquet"
    con = duckdb.connect()
    con.execute(
        "copy (select * from (values ('a', 'jbook_pdf', 'CurrentYear', null),"
        " ('b', 'workbook', null, 'fy_2025_enacted'), ('c', 'derived', null, null))"
        " t(fact_id, kind, scenario, amount_type)) to '" + str(pq) + "' (format parquet)")
    con.close()
    assert fact_column_index(pq) == {
        "a": {"scenario": "CurrentYear", "amount_type": None},
        "b": {"scenario": None, "amount_type": "fy_2025_enacted"},
    }
    assert fact_column_index(None) == {}


def test_fact_column_index_fails_closed(tmp_path):
    from govbudget.dossiers.claim_drift import fact_column_index

    with pytest.raises(ClaimDriftIndexError):
        fact_column_index(tmp_path / "absent.parquet")
    narrow = tmp_path / "narrow.parquet"
    con = duckdb.connect()
    con.execute(f"copy (select 'a' as fact_id) to '{narrow}' (format parquet)")
    con.close()
    with pytest.raises(ClaimDriftIndexError, match="scenario"):
        fact_column_index(narrow)


# ---------------------------------------------------------------------------
# R-DEC-DOSSIERLDA (final-review ruling, controller 2026-09-27): a dossier
# claim naming a lobbying registrant or client the PAGE's lobbying mentions do
# not list (after the #176 rematch removed every pe_literal row) is withheld,
# sub-reason `lobbying_mention`. Same principle as the recipient-list leg: the
# claim's own citation cannot vouch for a tie the page's records do not carry.
#
# What the leg reads:
#   - a LOBBYING claim: one citing an lda_filing fact, or one whose text uses
#     lobbying vocabulary ("lobby…", "LDA");
#   - the filers it NAMES: every Senate LDA client, registrant or (verified)
#     family name in audit_lda_filings — the whole filing universe, not only
#     fct_program_lobbying, so a filer whose every mention the rematch removed
#     is still recognised — found as a proper-noun run of the sentence;
#   - the filers the page LISTS: its fct_program_lobbying rows' client, family
#     and (through audit_lda_filings) registrant — the program_details
#     `mentions` rows; a shared code's member page lists none (R-INT-9).
# ---------------------------------------------------------------------------

#: (client_name, registrant_name, family_key) — the audit_lda_filings rows the
#: live claims touch, measured read-only 2026-09-27.
FILINGS = [
    ("FEDEX CORPORATION", "FEDEX CORPORATION", "FEDEX"),
    ("GENERAL DYNAMICS CORP", "GENERAL DYNAMICS CORP", "GENERAL DYNAMICS"),
    ("GENERAL DYNAMICS CORPORATION", "MELTSNER STRATEGIES, LLC", "GENERAL DYNAMICS"),
    ("HUNTINGTON INGALLS INDUSTRIES INCORPORATED",
     "HUNTINGTON INGALLS INDUSTRIES INCORPORATED", "HUNTINGTON INGALLS INDUSTRIES"),
    ("LOCKHEED MARTIN CORPORATION", "ETHERTON AND ASSOCIATES, INC.", "LOCKHEED MARTIN"),
    ("BOEING COMPANY", "BOEING COMPANY", "BOEING"),
    ("RTX CORPORATION AND AFFILIATES", "RTX CORPORATION AND AFFILIATES", "RTX"),
    ("GENERAL DYNAMICS INFORMATION TECHNOLOGY", "GDIT", "GENERAL DYNAMICS"),
    ("AEROSPACE", "AEROSPACE", None),
]
UNIVERSE = FilerUniverse.from_filings(FILINGS)

#: each page's fct_program_lobbying rows as (client_name, family_key,
#: registrant_name), read-only 2026-09-27 (program_details mentions)
MENTIONS_1045 = [
    ("GENERAL DYNAMICS CORP", "GENERAL DYNAMICS", "GENERAL DYNAMICS CORP"),
    ("GENERAL DYNAMICS CORPORATION", "GENERAL DYNAMICS", "MELTSNER STRATEGIES, LLC"),
    ("HUNTINGTON INGALLS INDUSTRIES INCORPORATED", "HUNTINGTON INGALLS INDUSTRIES",
     "HUNTINGTON INGALLS INDUSTRIES INCORPORATED"),
]
MENTIONS_0605 = [("FEDEX CORPORATION", "FEDEX", "FEDEX CORPORATION")]
MENTIONS_0607210D8Z = [
    ("BOEING COMPANY", "BOEING", "BOEING COMPANY"),
    ("RTX CORPORATION AND AFFILIATES", "RTX", "RTX CORPORATION AND AFFILIATES"),
    ("SCIENCE APPLICATIONS INTERNATIONAL CORPORATION", "SCIENCE APPLICATIONS INTERNATIONAL",
     "SCIENCE APPLICATIONS INTERNATIONAL CORPORATION"),
]
MENTIONS_2001 = [MENTIONS_1045[2]]

#: an lda_filing citation row (citations.json shape: no value, no units)
LDA_FACT = {"kind": "lda_filing", "units": None, "recorded_value": None}
#: a filing-level lda_filing row (the filing's reported amount)
LDA_AMOUNT_FACT = {"kind": "lda_filing", "units": "USD", "recorded_value": "37500"}

#: /program/2004/ (CVN-81) players[1], verbatim; cites 0823104dbb624904 (a
#: FedEx mention of 821800). The #176 rematch left 2004 no mention at all.
C_2004_FEDEX = (
    "Additional FedEx Corporation filings in 2024 referenced legislative"
    " monitoring of Open Skies Agreements and general trade issues including"
    " customs modernization."
)
#: /program/1045/ players[5], verbatim; cites 019440805ba04bc0 (a FedEx
#: mention of 0208085JCY). 1045 lists General Dynamics and Huntington Ingalls.
C_1045_FEDEX = (
    "A FedEx Corporation filing matched the term '1045' while describing lobbying"
    " on aviation security and safety issues — a coincidental keyword match"
    " unrelated to the submarine program (2026 filing)."
)
#: /program/1045/ players[0] and players[2], verbatim — filers 1045 lists.
C_1045_GD = (
    "Lobbying filings from General Dynamics Corporation reported lobbying for full"
    " funding of the Virginia Class and Columbia Class submarine programs and"
    " funding for the submarine industrial base (2026 filing)."
)
C_1045_HII = (
    "Huntington Ingalls Industries Incorporated filings referenced the COLUMBIA"
    " Class submarine among a list of Navy shipbuilding programs (2026 filing)."
)
#: /program/0605/ players[0], verbatim — FedEx IS on 0605's mention list.
C_0605_FEDEX = (
    "Lobbying filings referenced this program: FedEx Corporation reported lobbying"
    " activity in a 2026 filing that mentioned repair and parts legislation,"
    " including the REPAIR Act."
)
#: /program/0607210D8Z/ players[0], verbatim; cites 0010cfea95c30893, a
#: Lockheed Martin filing (57a5f526…) that mentions no program at all. The
#: page lists Boeing, RTX and SAIC — never Lockheed Martin, before or after
#: the rematch. The rule is the page's list, not the rematch's history.
C_0607210D8Z_LOCKHEED = (
    "A 2025 Lockheed Martin filing referenced the FY26 National Defense"
    " Authorization Act and issues relating to acquisition and the industrial base."
)


def _page(mentions):
    return PageLobbying.from_mentions(mentions, UNIVERSE)


class TestLobbyingMention:
    def test_2004_fedex_key_player_claim_is_withheld(self):
        page = _page([])  # 2004: no mention after the rematch
        assert claim_contradictions(C_2004_FEDEX, LDA_FACT, None, None, page) == [
            "lobbying_mention"]
        assert unlisted_lobbying_filers(C_2004_FEDEX, LDA_FACT, page) == ["FedEx Corporation"]

    def test_1045_fedex_matched_term_claim_is_withheld(self):
        page = _page(MENTIONS_1045)
        assert claim_contradictions(C_1045_FEDEX, LDA_FACT, None, None, page) == [
            "lobbying_mention"]
        assert unlisted_lobbying_filers(C_1045_FEDEX, LDA_FACT, page) == ["FedEx Corporation"]

    def test_a_claim_whose_named_filer_still_has_mentions_stays(self):
        assert claim_contradictions(
            C_1045_GD, LDA_AMOUNT_FACT, None, None, _page(MENTIONS_1045)) == []
        assert claim_contradictions(
            C_1045_HII, LDA_FACT, None, None, _page(MENTIONS_1045)) == []
        assert claim_contradictions(
            C_0605_FEDEX, LDA_FACT, None, None, _page(MENTIONS_0605)) == []

    def test_the_same_claim_is_held_to_its_own_page(self):
        # FedEx is listed on 0605 and not on 1045 or 2004
        assert claim_contradictions(C_0605_FEDEX, LDA_FACT, None, None,
                                    _page(MENTIONS_1045)) == ["lobbying_mention"]
        assert claim_contradictions(C_1045_HII, LDA_FACT, None, None,
                                    _page(MENTIONS_0605)) == ["lobbying_mention"]

    def test_0607210D8Z_lockheed_claim_names_a_filer_the_page_never_lists(self):
        page = _page(MENTIONS_0607210D8Z)
        fact = {"kind": "lda_filing", "units": "USD", "recorded_value": "30000"}
        assert claim_contradictions(C_0607210D8Z_LOCKHEED, fact, None, None, page) == [
            "lobbying_mention"]
        assert unlisted_lobbying_filers(C_0607210D8Z_LOCKHEED, fact, page) == [
            "Lockheed Martin"]

    def test_the_named_filers_are_read_as_the_sentence_prints_them(self):
        assert named_lobbying_filers(C_1045_GD, UNIVERSE) == [
            "General Dynamics Corporation"]
        assert named_lobbying_filers(C_1045_HII, UNIVERSE) == [
            "Huntington Ingalls Industries Incorporated"]
        assert named_lobbying_filers(C_2004_FEDEX, UNIVERSE) == ["FedEx Corporation"]
        # the longest filer name wins over a name it contains
        assert named_lobbying_filers(
            "General Dynamics Information Technology lobbied on it.", UNIVERSE) == [
            "General Dynamics Information Technology"]
        # a possessive is the name's
        assert named_lobbying_filers("FedEx's 2024 lobbying filings.", UNIVERSE) == [
            "FedEx's"]

    def test_a_registrant_is_listed_through_the_pages_own_filings(self):
        text = "Meltsner Strategies lobbied on the program for its client."
        assert claim_contradictions(text, None, None, None, _page(MENTIONS_1045)) == []
        assert claim_contradictions(text, None, None, None, _page(MENTIONS_2001)) == [
            "lobbying_mention"]

    def test_names_match_at_the_family_level(self):
        # GDIT is a GENERAL DYNAMICS client name; 1045 lists that family
        text = "General Dynamics Information Technology lobbied on the program."
        assert claim_contradictions(text, None, None, None, _page(MENTIONS_1045)) == []
        assert claim_contradictions(text, None, None, None, _page(MENTIONS_0605)) == [
            "lobbying_mention"]

    def test_lobbying_vocabulary_without_an_lda_citation_is_checked(self):
        text = "Lockheed Martin lobbied on the program in 2025."
        assert claim_contradictions(text, None, None, None, _page(MENTIONS_1045)) == [
            "lobbying_mention"]

    def test_a_claim_that_is_not_about_lobbying_is_not_this_legs(self):
        page = _page([])
        for text, fact in (
            ("Lockheed Martin Corporation is a recipient linked to this budget line.",
             {"kind": "derived", "units": "USD", "recorded_value": "1.0"}),
            ("The EMD contract was awarded to Boeing on 24 February 2011.", None),
        ):
            assert claim_contradictions(text, fact, None, None, page) == [], text

    def test_a_common_word_is_not_a_filer_name(self):
        page = _page([])
        for text in (
            "Lobbying filings addressed the aerospace industrial base.",
            "Aerospace lobbying rose in 2025 across the industrial base.",
            "LDA filings referenced the program 12 times.",
        ):
            assert named_lobbying_filers(text, UNIVERSE) == [], text
            assert claim_contradictions(text, LDA_FACT, None, None, page) == [], text

    def test_a_lobbying_claim_naming_no_filer_is_not_checked(self):
        text = ("Lobbying mentions show only that a filing referenced program-related"
                " terms, not that any spending decision resulted.")
        assert claim_contradictions(text, LDA_FACT, None, None, _page([])) == []

    def test_without_a_lobbying_index_the_leg_does_not_run(self):
        assert claim_contradictions(C_2004_FEDEX, LDA_FACT, None, None, None) == []
        assert claim_contradictions(C_2004_FEDEX, LDA_FACT) == []


def _lobbying_mart(db):
    """dim_programs + the two relations the lobbying index reads: an ordinary
    program with mentions, one whose mentions the rematch removed, and a
    shared code (3010, split by ACCOUNT) whose bare-code rows R-INT-9 withholds
    from both member pages."""
    con = duckdb.connect(str(db))
    con.execute("create table dim_programs (pe_bli varchar, account varchar,"
                " account_title varchar, org varchar, exhibit_family varchar)")
    con.executemany("insert into dim_programs values (?,?,?,?,?)", [
        ("1045", None, None, "N", "procurement"),
        ("2004", None, None, "N", "procurement"),
        ("3010", "1611N", "Shipbuilding and Conversion, Navy", "N", "procurement"),
        ("3010", "1810N", "Other Procurement, Navy", "N", "procurement"),
    ])
    con.execute("create table audit_lda_filings (filing_uuid varchar, client_name varchar,"
                " registrant_name varchar, family_key_guess varchar, match_method varchar)")
    con.executemany("insert into audit_lda_filings values (?,?,?,?,?)", [
        ("f-gd", "GENERAL DYNAMICS CORPORATION", "MELTSNER STRATEGIES, LLC",
         "GENERAL DYNAMICS", "exact_family"),
        ("f-fedex", "FEDEX CORPORATION", "FEDEX CORPORATION", "FEDEX", "exact_family"),
        ("f-hii", "HUNTINGTON INGALLS INDUSTRIES INCORPORATED",
         "HUNTINGTON INGALLS INDUSTRIES INCORPORATED", "HUNTINGTON INGALLS INDUSTRIES",
         "exact_family"),
        # an unverified guess is no family link (fct_program_lobbying's rule)
        ("f-x", "ACME WIDGETS LLC", "ACME WIDGETS LLC", "LOCKHEED MARTIN", "none"),
    ])
    con.execute("create table fct_program_lobbying (filing_uuid varchar, pe_bli varchar,"
                " client_name varchar, family_key varchar)")
    con.executemany("insert into fct_program_lobbying values (?,?,?,?)", [
        ("f-gd", "1045", "GENERAL DYNAMICS CORPORATION", "GENERAL DYNAMICS"),
        ("f-fedex", "0605", "FEDEX CORPORATION", "FEDEX"),
        ("f-hii", "3010", "HUNTINGTON INGALLS INDUSTRIES INCORPORATED",
         "HUNTINGTON INGALLS INDUSTRIES"),
    ])
    con.close()


def test_lobbying_mention_index_is_page_keyed(tmp_path):
    db = tmp_path / "l.duckdb"
    _lobbying_mart(db)
    index = lobbying_mention_index(db)
    assert isinstance(index, LobbyingIndex)

    gd = "General Dynamics Corporation lobbied for submarine funding."
    fedex = "A FedEx Corporation filing matched the term '1045' in its lobbying."
    assert claim_contradictions(gd, None, None, None, index.for_page("1045")) == []
    # the registrant of the page's own filing
    assert unlisted_lobbying_filers(
        "Meltsner Strategies lobbied on it.", None, index.for_page("1045")) == []
    # FedEx: in the filing universe, listed on 0605 only
    assert unlisted_lobbying_filers(fedex, None, index.for_page("1045")) == [
        "FedEx Corporation"]
    assert unlisted_lobbying_filers(fedex, None, index.for_page("2004")) == [
        "FedEx Corporation"]
    assert unlisted_lobbying_filers(fedex, None, index.for_page("0605")) == []
    # R-INT-9: a shared code's bare-code rows are on no member page
    hii = "Huntington Ingalls Industries lobbied on the program."
    for member in ("3010-SCN", "3010-OPN", "3010"):
        assert unlisted_lobbying_filers(hii, None, index.for_page(member)) == [
            "Huntington Ingalls Industries"], member
    # a 'none' match is no family link: ACME is a filer, LOCKHEED MARTIN not
    # made one by an unverified guess
    assert named_lobbying_filers("Acme Widgets lobbied.", index.universe) == [
        "Acme Widgets"]
    assert named_lobbying_filers("Lockheed Martin lobbied.", index.universe) == []


def test_lobbying_mention_index_unknown_is_none():
    assert lobbying_mention_index(None) is None


def test_lobbying_mention_index_raises_on_an_unreadable_mart(tmp_path):
    db = tmp_path / "l.duckdb"
    _lobbying_mart(db)
    con = duckdb.connect(str(db))
    con.execute("drop table audit_lda_filings")
    con.close()
    with pytest.raises(ClaimDriftIndexError, match="audit_lda_filings"):
        lobbying_mention_index(db)
    with pytest.raises(ClaimDriftIndexError):
        lobbying_mention_index(tmp_path / "absent.duckdb")
