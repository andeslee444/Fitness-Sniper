"""ROADMAP #176 — a bare number is not a budget-line citation.

`pe_literal` ("PE code cited directly" on the site) is the strongest mention
tier and one of the two that may name a company in a program's "Who gets it"
answer. Until #176 an all-digit code such as BLI 2025 matched ANY free-standing
"2025" in a filing, so years, dates, bill numbers, public-law numbers, section
numbers, aircraft designators and pieces of larger figures were published as
the program's own code cited in the filing.

Measured read-only on 2026-09-25 against data/parquet/influence/
lda_activities.parquet (12,410 activity rows, 5,029 filings): all 1,631
`pe_literal` rows sat on 45 all-digit codes, none of the 4,253 code
occurrences behind them carried a budget-line label, and a context census read
them as a year (3,099), a date (540), a bill or
resolution number (397), a public-law number (87), a section/title number
(51), a designator such as V-22 or CMS-4205-F (47), part of a larger figure
such as "2,500" (24), a Federal Register cite (2) or other non-budget text
(6). No filing in the corpus uses any budget-line vocabulary at all — zero
hits for "BLI", "program element", "PE <digit>", "line item", "budget line"
or "P-1"/"R-1" — so the rule keeps no row today; the true-positive tests
below are CONSTRUCTED to pin what the rule would accept.

Every false-positive snippet here is quoted from that parquet (the leading
comment names the filing_uuid prefix it came from).
"""
from __future__ import annotations

import pytest

from govbudget.influence.mentions import build_program_terms, find_mentions

# (pe_bli, title) exactly as dim_programs carries them (read 2026-09-25).
PROGRAMS = [
    ("2025", "Amphibious Combat Vehicle Family of Vehicles"),
    ("2026", "SPQ-9B Radar"),
    ("14", "Teleport Program"),
    ("4213", "Aircraft Support Equipment"),
    ("22", "Major Equipment, DPAA"),
    ("31", "Major Equipment, WHS"),
    ("97", "Joint Service Provider"),
    ("30", "Other Major Equipment"),
    ("20", "Vehicles"),
    ("10", "Major Equipment, TJS"),
    ("4205", "CIWS Mods"),
    ("2209", "Sidewinder"),
    ("500", "Personnel Administration"),
    ("90", "White House Communication Agency"),
    ("1045", "COLUMBIA Class Submarine"),
    ("0145", "General Purpose Bombs"),
    # Alphanumeric codes are distinctive on their own and keep the old rule.
    ("0208059JCY", "CYBERCOM Activities"),
    ("MD08", "Ground Based Midcourse"),
]


@pytest.fixture(scope="module")
def terms(tmp_path_factory):
    # An empty alias seed: these tests exercise the code tier only.
    seed = tmp_path_factory.mktemp("seed") / "program_aliases.csv"
    seed.write_text("pe_bli,alias,note\n")
    return build_program_terms(PROGRAMS, seed_path=seed)


def _rows(terms, text, uuid="u"):
    return find_mentions([{"filing_uuid": uuid, "description": text}], terms)


# Real filing text, one case per context class the 2026-09-25 census found.
FALSE_POSITIVES = [
    # year — "Fiscal Year 2025"
    ("2025", "Full-Year Continuing Appropriations and Extensions Act for Fiscal "
             "Year 2025 Various actions associated with proposed defense"),
    # year — "Act of 2025"
    ("2025", "Issues related to H.R. 4231/S. 1973 - Treat and Reduce Obesity Act "
             "of 2025; Issues related to the One Big Beautiful Bill Act"),
    # year — "FY 2026"
    ("2026", "ement issues related to the National Defense Authorization Act for "
             "FY 2026."),
    # date — "September 30, 2026" (the day matches BLI 30, the year BLI 2026)
    ("30", "consolidated appropriations for the fiscal year ending September 30, "
           "2026, and for other purposes (P.L.119-75)"),
    ("2026", "consolidated appropriations for the fiscal year ending September "
             "30, 2026, and for other purposes (P.L.119-75)"),
    # bill number — "H.R. 20"
    ("20", "Support Protecting the Right to Organize Act H.R. 20/ S. 567 Support "
           "Confirmation of Julie Sue as U.S."),
    # concurrent-resolution number — "H.Con.Res. 14"
    ("14", "Monitored S.Con.Res 7, H.Con.Res. 14 and issues related to defense "
           "spending."),
    # bill number with one of the program's own title words nearby — the
    # "title words nearby" rule would have KEPT this; it is still a bill.
    ("4213", "Homeland Security Appropriations Bills for FY 2026 (H.R. 4213); "
             "issues relating to border patrol aircraft."),
    # public-law number — "P.L. 118-31", "P.L. 115-97"
    ("31", "the National Defense Authorization Act for Fiscal Year 2024 "
           "(P.L. 118-31)."),
    ("97", "Issues related to P.L. 115-97 - Tax Cuts and Jobs Act (TCJA)/Tax "
           "Reform impleme"),
    # section / title number
    ("2209", "Issues Related to Beyond Visual Line of Sight rulemaking; Issues "
             "related to Section 2209 rulemaking"),
    ("10", "Title 10 security cooperation and foreign relations"),
    # designator — V-22 is the Osprey, not BLI 22; CMS-4205-F is a CMS rule
    ("22", "Defense funding for V-22, RQ-7 Shadow, Ship to Shore Connector, and "
           "Roboti"),
    ("4205", "Contract Year 2025 Medicare Advantage and Part D Final Rule "
             "(CMS-4205-F)"),
    # part of a larger figure — "2,500 megahertz"
    ("500", "Information Administration to identify at least 2,500 megahertz of "
            "mid-band spectrum that can be reallocated"),
    # Federal Register citation — "90 FR 8363"
    ("90", "Federal Government's Leasing and Permitting Practices for Wind "
           "Projects (90 FR 8363)"),
    # bill number — "S.1045"
    ("1045", "H.R.6086 - Aviation Funding Solvency Act S.1045/H.R.5451/H.R.5455 "
             "- Aviation Funding Stability Ac"),
]


@pytest.mark.parametrize("code,text", FALSE_POSITIVES)
def test_a_bare_number_in_filing_text_is_not_the_program_code(terms, code, text):
    got = [r for r in _rows(terms, text) if r["pe_bli"] == code]
    assert not any(r["evidence_kind"] == "pe_literal" for r in got), got
    # None of these snippets carries two of the program's title words, so the
    # row must disappear entirely — not merely be relabelled.
    assert got == []


def test_a_real_program_mention_beside_a_year_keeps_its_word_tier(terms):
    """filing 96ae87f5…: names "USMC Amphibious Combat Vehicles (ACV)" in words
    and the FY2025 appropriations act by year. Before #176 this row was
    `pe_literal` on "2025"; the program really is mentioned, so the row stays,
    under the tier its evidence supports (title words), not the code tier."""
    text = (
        "Combat Mission Systems; Paladin PIM; Bradley Fighting Vehicle; M88 "
        "Recovery Vehicle; USMC Amphibious Combat Vehicles (ACV); Army Combat "
        "Vehicles; Department of Defense Appropriations Act of 2025 (HR XXXX/S "
        "XXXX); provisions"
    )
    got = [r for r in _rows(terms, text) if r["pe_bli"] == "2025"]
    assert len(got) == 1
    assert got[0]["evidence_kind"] == "multi_token"
    assert "Amphibious" in got[0]["matched_term"].split("|")


# CONSTRUCTED — the corpus holds no budget-line vocabulary (see module doc).
TRUE_POSITIVES = [
    ("2025", "Navy procurement, BLI 2025, Amphibious Combat Vehicle"),
    ("2025", "Funding for bli #2025 in the FY27 request"),
    ("2025", "BLI No. 2025 (Amphibious Combat Vehicle)"),
    ("1045", "Support P-1 line 1045 funding"),
    ("1045", "budget line item 1045"),
    ("1045", "Program Element 1045"),
    ("0145", "Line item 0145, General Purpose Bombs"),
    ("30", "PE 30 in the Defense-Wide request"),
]


@pytest.mark.parametrize("code,text", TRUE_POSITIVES)
def test_a_numeric_code_named_as_a_budget_line_is_cited_directly(terms, code, text):
    got = [r for r in _rows(terms, text) if r["pe_bli"] == code]
    assert len(got) == 1, got
    assert got[0]["evidence_kind"] == "pe_literal"
    assert got[0]["matched_term"] == code


@pytest.mark.parametrize("text", [
    # The label must NAME this number: a label elsewhere in the text does not.
    "BLI funding discussed; Appropriations Act of 2025",
    # A label followed by a LARGER figure is not this code.
    "BLI 2,025 units",
    "BLI 20251",
    "BLI 2025.5",
    # A label that is only the tail of a longer word is not a label.
    "TYPE 2025 compliance",
])
def test_the_label_must_name_this_exact_number(terms, text):
    assert not any(
        r["evidence_kind"] == "pe_literal" and r["pe_bli"] == "2025"
        for r in _rows(terms, text)
    )


def test_alphanumeric_codes_keep_the_plain_code_rule(terms):
    """A code with letters (0208059JCY, MD08) cannot be a year, a bill or a
    quantity, so it still qualifies on its own — no label needed."""
    got = {r["pe_bli"]: r for r in _rows(terms, "Funding for 0208059JCY and MD08.")}
    assert got["0208059JCY"]["evidence_kind"] == "pe_literal"
    assert got["MD08"]["evidence_kind"] == "pe_literal"
