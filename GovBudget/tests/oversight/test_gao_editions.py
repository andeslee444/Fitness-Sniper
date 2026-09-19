"""WSAA predecessors (ROADMAP #30, "and its predecessors").

Three editions are ingested.  Every assessment row is stamped with its edition
and linked to the same program's assessment in the nearest EARLIER edition —
same normalized common name, same service family, nothing fuzzier.  An older
edition reaches a program page ONLY through that link, from an assessment a
person ratified in the current edition; the matcher never proposes older rows
and no new verdict is written.

The two fixture directories hold one real assessment page and one real index
page per new edition, dumped from the cached PDFs by
``tests/oversight/wsaa_fixture_tool.py`` so the layout tests do not need the
40 MB volumes.
"""
from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

import duckdb
import pytest

from govbudget.oversight import gao_programs as G
from govbudget.oversight import gao_xwalk as X

FIXTURES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "oversight" / "wsaa"
)


def _edition(product: str) -> G.Edition:
    return next(e for e in G.EDITIONS if e.product_number == product)


# ── editions ────────────────────────────────────────────────────────────────


def test_three_editions_and_the_2025_volume_is_current():
    assert [e.product_number for e in G.EDITIONS] == [
        "GAO-25-107569", "GAO-24-106831", "GAO-23-106059",
    ]
    assert [e.year for e in G.EDITIONS] == [2025, 2024, 2023]
    assert G.current_edition().product_number == "GAO-25-107569"
    e24 = _edition("GAO-24-106831")
    e23 = _edition("GAO-23-106059")
    assert e24.pdf_url == "https://www.gao.gov/assets/gao-24-106831.pdf"
    assert e23.report_url == "https://www.gao.gov/products/gao-23-106059"
    # The current edition's bibliography is the reading list; older ones
    # would add products nobody adjudicated, so they are not re-read.
    assert G.EDITIONS[0].ingest_related is True
    assert e24.ingest_related is False and e23.ingest_related is False


# ── layout tolerance ────────────────────────────────────────────────────────


def _page(product: str, *, banner: str, footer: str) -> str:
    return (
        f"{banner}\n"
        "LGM-35A Sentinel\n"
        "The Air Force's Sentinel, formerly the Ground Based Strategic "
        "Deterrent,\n"
        "is intended to replace the Minuteman III intercontinental ballistic\n"
        "missile system.\n"
        f"Source: U.S. Air Force. | {product}\n"
        "Program Performance fiscal year 2024 dollars in millions\n"
        f"{footer}"
    )


def test_banner_with_common_name_before_program_type_parses():
    page = _page(
        "GAO-24-106831",
        banner="Air Force Common Name: Sentinel Program Type: MDAP",
        footer=(
            "Page 84 U.S. Government Accountability Office GAO-24-106831 "
            "Weapon Systems Annual Assessment"
        ),
    )
    (a,) = G.parse_edition_pages([page], _edition("GAO-24-106831"))
    assert (a.service, a.assessment_type, a.common_name) == (
        "Air Force", "MDAP", "Sentinel",
    )
    assert a.report_page == 84
    assert a.product_number == "GAO-24-106831"
    assert a.edition_year == 2024
    assert a.program_key == "sentinel"
    assert a.predecessor_product == "" and a.predecessor_pdf_page == 0


def test_footer_without_the_agency_name_parses():
    page = _page(
        "GAO-23-106059",
        banner="Air Force Program Type: MDAP Common Name: Sentinel",
        footer="Page 77 GAO-23-106059 Weapon Systems Annual Assessment",
    )
    (a,) = G.parse_edition_pages([page], _edition("GAO-23-106059"))
    assert a.report_page == 77
    assert a.edition_year == 2023


def test_the_2025_banner_and_footer_still_parse_first():
    page = _page(
        "GAO-25-107569",
        banner="Air Force Program Type: MDAP Common Name: Sentinel",
        footer=(
            "Page 79 U.S. Govern ment Accountability Office GAO-25-107569 "
            "Weapon Systems Annual Assessment"
        ),
    )
    (a,) = G.parse_edition_pages([page], G.EDITIONS[0])
    assert (a.report_page, a.edition_year) == (79, 2025)


def test_index_header_variant_is_counted():
    page = (
        "Program name Program type\n"
        "LGM-35A Sentinel MDAP\n"
        "Hypersonic Attack Cruise Missile MTA\n"
        "Source: GAO analysis of DOD data. | GAO-23-106059\n"
    )
    assert G.index_table_program_counts([page], G.DEFAULT_LAYOUT) == 2
    assert G.index_table_program_counts(
        [page.replace("Program type", "Assessment type")]
    ) == 2


def test_banner_with_the_lead_component_order_parses():
    """The 2024/2023 typesetting, copied from GAO-24-106831 PDF p.81.

    "MDAP Lead Component: Air Force Common Name: B-52 CERP" — the assessment
    type leads and the service sits behind "Lead Component:".  Added as a
    third banner anchor; the two 2025 anchors are still tried first.
    """
    page = _page(
        "GAO-24-106831",
        banner="MDAP Lead Component: Air Force Common Name: Sentinel",
        footer=(
            "Page 84 U.S. Government Accountability Office GAO-24-106831 "
            "Weapon Systems Annual Assessment"
        ),
    )
    (a,) = G.parse_edition_pages([page], _edition("GAO-24-106831"))
    assert (a.service, a.assessment_type, a.common_name) == (
        "Air Force", "MDAP", "Sentinel",
    )
    assert (a.report_page, a.edition_year) == (84, 2024)


def test_a_dod_lead_component_parses_and_shares_the_joint_family():
    """GAO-24-106831 p.213 and GAO-23-106059 p.217 lead the F-35 with
    "Lead Component: DOD" — the label the 2025 volume writes as "Joint".
    Without DOD in the service alternation the F-35 assessment would be
    dropped silently; with it, the two volumes' F-35 rows chain to each
    other and to a 2025 "Joint" row if one ever exists."""
    page = (
        "MDAP Lead Component: DOD Common Name: F-35\n"
        "F-35 Lightning II (F-35)\n"
        "DOD is developing three fighter aircraft variants integrating "
        "stealth\n"
        "with advanced sensors, and is fielding them to the Air Force, the "
        "Navy\n"
        "and the Marine Corps as well as to international partners.\n"
        "Source: DOD. | GAO-24-106831\n"
        "Page 201 U.S. Government Accountability Office GAO-24-106831 "
        "Weapon Systems Annual Assessment"
    )
    (a,) = G.parse_edition_pages([page], _edition("GAO-24-106831"))
    assert (a.service, a.common_name, a.report_page) == ("DOD", "F-35", 201)
    assert G._family("DOD") == G._family("Joint") == "J"


def test_grouped_index_header_counts_program_rows():
    """The 2024/2023 index tables print the type once per GROUP ("MDAPs"),
    so the type column is not one token per program and the row is the
    countable unit.  Copied from GAO-24-106831 PDF p.80."""
    page = (
        "Assessment type Program name\n"
        "MDAPs B-52 Commercial Engine Replacement Program (B-52 CERP)\n"
        "LGM-35A Sentinel (Sentinel)\n"
        "MTA Programs Hypersonic Attack Cruise Missile (HACM)\n"
        "Source (previous page image): Boeing Corporation. | GAO-24-106831\n"
    )
    assert G.index_table_program_counts([page], G.DEFAULT_LAYOUT) == 3
    # …and the 2025 tables are still counted by their type column.
    assert G.index_table_program_counts(
        ["Program name Assessment type\nLGM-35A Sentinel MDAP\n"]
    ) == 1


# ── predecessor links ───────────────────────────────────────────────────────


def _a(product, year, service, common, page):
    return G.Assessment(
        kind="assessment", product_number=product, report_title="t",
        report_url="u", source_product=product, source_pdf_url="p",
        released=f"{year}-06", service=service, assessment_type="MDAP",
        program_name=f"LGM-35A {common}", common_name=common,
        report_page=page, pdf_page=page + 10, description="d" * 130,
        edition_year=year, program_key=G.program_key(common),
        predecessor_product="", predecessor_pdf_page=0,
    )


def test_link_predecessors_chains_the_same_program_backwards():
    rows = [
        _a("GAO-25-107569", 2025, "Air Force", "Sentinel", 79),
        _a("GAO-24-106831", 2024, "Air Force", "Sentinel", 84),
        _a("GAO-23-106059", 2023, "Air Force", "Sentinel", 77),
        _a("GAO-23-106059", 2023, "Navy", "CH-53K", 60),   # 2023 only
        _a("GAO-25-107569", 2025, "Army", "Sentinel", 30),  # other service
    ]
    got = {
        (r.product_number, r.service, r.common_name): r
        for r in G.link_predecessors(rows)
    }
    s25 = got[("GAO-25-107569", "Air Force", "Sentinel")]
    s24 = got[("GAO-24-106831", "Air Force", "Sentinel")]
    s23 = got[("GAO-23-106059", "Air Force", "Sentinel")]
    assert (s25.predecessor_product, s25.predecessor_pdf_page) == (
        "GAO-24-106831", 94,
    )
    assert (s24.predecessor_product, s24.predecessor_pdf_page) == (
        "GAO-23-106059", 87,
    )
    assert s23.predecessor_product == ""
    assert got[("GAO-23-106059", "Navy", "CH-53K")].predecessor_product == ""
    # The Army "Sentinel" is a different program (ROADMAP #55's species).
    assert got[("GAO-25-107569", "Army", "Sentinel")].predecessor_product == ""


def test_link_skips_a_missing_middle_edition():
    r25, r23 = G.link_predecessors([
        _a("GAO-25-107569", 2025, "Navy", "F/A-18", 10),
        _a("GAO-23-106059", 2023, "Navy", "F/A-18", 20),
    ])
    assert r25.predecessor_product == "GAO-23-106059"
    assert r23.predecessor_product == ""


def test_a_rename_breaks_the_chain_on_purpose():
    r25, r24 = G.link_predecessors([
        _a("GAO-25-107569", 2025, "Air Force", "Sentinel", 79),
        _a("GAO-24-106831", 2024, "Air Force", "GBSD", 84),
    ])
    assert r25.predecessor_product == "" and r24.predecessor_product == ""


def test_space_force_and_air_force_are_one_family():
    r25, _ = G.link_predecessors([
        _a("GAO-25-107569", 2025, "Space Force", "NGG", 100),
        _a("GAO-23-106059", 2023, "Air Force", "NGG", 90),
    ])
    assert r25.predecessor_product == "GAO-23-106059"


def test_related_products_pass_through_unlinked():
    rel = G.parse_related_products(
        "F-35 Joint Strike Fighter: Program Continues to Encounter Production "
        "Issues and Modernization Delays. GAO-24-106909. Washington, D.C.: "
        "May 16, 2024.",
        G.EDITIONS[0],
    )
    (r,) = G.link_predecessors(rel)
    assert (r.edition_year, r.program_key, r.predecessor_product) == (
        2025, "", "",
    )


def test_predecessor_chain_and_unlinked_report_over_dict_rows():
    rows = [asdict(r) for r in G.link_predecessors([
        _a("GAO-25-107569", 2025, "Air Force", "Sentinel", 79),
        _a("GAO-24-106831", 2024, "Air Force", "Sentinel", 84),
        _a("GAO-23-106059", 2023, "Air Force", "Sentinel", 77),
        _a("GAO-23-106059", 2023, "Navy", "CH-53K", 60),
    ])]
    head = next(r for r in rows if r["product_number"] == "GAO-25-107569")
    chain = G.predecessor_chain(head, rows)
    assert [c["product_number"] for c in chain] == [
        "GAO-24-106831", "GAO-23-106059",
    ]
    gap = G.unlinked_older_assessments(rows, "GAO-25-107569")
    assert [(g["product_number"], g["common_name"]) for g in gap] == [
        ("GAO-23-106059", "CH-53K"),
    ]
    assert G.unlinked_older_programs(rows, "GAO-25-107569") == 1


def test_unlinked_programs_counts_a_program_once_across_two_editions():
    """The number /methodology/ states is programs, not rows.

    GAO assessed the F-35 in both older volumes and neither reaches a page;
    that is ONE program the current edition does not carry, and two rows.
    """
    rows = [asdict(r) for r in G.link_predecessors([
        _a("GAO-24-106831", 2024, "DOD", "F-35", 213),
        _a("GAO-23-106059", 2023, "DOD", "F-35", 217),
        _a("GAO-25-107569", 2025, "Air Force", "Sentinel", 79),
    ])]
    assert len(G.unlinked_older_assessments(rows, "GAO-25-107569")) == 2
    assert G.unlinked_older_programs(rows, "GAO-25-107569") == 1


# ── the matcher's scope ─────────────────────────────────────────────────────


def test_generate_candidates_matches_only_the_current_edition():
    programs = [{"slug": "0101125F", "org": "F", "title": "LGM-35A Sentinel"}]
    rows = [
        dict(kind="assessment", product_number=p, common_name="Sentinel",
             program_name="LGM-35A Sentinel", service="Air Force")
        for p in ("GAO-25-107569", "GAO-24-106831")
    ]
    both = X.generate_candidates(rows, programs)
    assert sorted(c.product_number for c in both) == [
        "GAO-24-106831", "GAO-25-107569",
    ]
    only = X.generate_candidates(
        rows, programs, current_product="GAO-25-107569"
    )
    assert [c.product_number for c in only] == ["GAO-25-107569"]


def test_generate_candidates_still_proposes_bibliography_reports():
    """A related product is not an edition; the filter must not swallow it.

    22 of the 63 ratified rows are bibliography reports (GAO-24-106909,
    GAO-23-106047, GAO-22-105128, GAO-22-104530, GAO-24-106639).  If the
    edition filter reached them, every one would go STALE.
    """
    programs = [{"slug": "ATA000", "org": "F", "title": "F-35"}]
    rows = [dict(kind="related_product", product_number="GAO-24-106909",
                 common_name="", program_name="F-35 Joint Strike Fighter",
                 service="")]
    got = X.generate_candidates(
        rows, programs, current_product="GAO-25-107569"
    )
    assert [(c.product_number, c.slug) for c in got] == [
        ("GAO-24-106909", "ATA000"),
    ]


# ── cached fixture pages, one per new edition ───────────────────────────────


@pytest.mark.parametrize("slug", ["gao-24-106831", "gao-23-106059"])
def test_cached_fixture_pages_parse_with_the_edition_layout(slug):
    d = FIXTURES / slug
    manifest = json.loads((d / "manifest.json").read_text())
    edition = _edition(manifest["product_number"])
    (a,) = G.parse_edition_pages([(d / "assessment.txt").read_text()], edition)
    assert a.common_name == manifest["common_name"]
    assert a.service == manifest["service"]
    assert a.assessment_type == manifest["assessment_type"]
    assert a.report_page == manifest["report_page"]
    assert a.pdf_page == 1
    assert a.edition_year == edition.year
    assert a.description.startswith(manifest["description_starts"])
    assert a.description.endswith(".")
    assert not G.DESC_RESIDUE_RE.search(a.description)
    index = (d / "index.txt").read_text()
    assert manifest["index_count_on_page"] > 0
    assert G.index_table_program_counts([index], edition.layout) == (
        manifest["index_count_on_page"]
    )


# ── the heading rule, on the six pages that caught it out ───────────────────
#
# Measured 2026-09-12 over the cached volumes: the contiguous-substring rule
# DROPPED three real assessments (the banner's common name is not a contiguous
# run inside GAO's typeset heading) and OVER-CONSUMED three others (the rule
# kept reading until it found the name inside GAO's first description line, so
# program_name carried a sentence and the quote began mid-sentence).
#
# Every expected value below was read by eye off the committed fixture page,
# never echoed from the parser — an echo would have pinned the defect.
HEADING_EXPECTED = {
    ("gao-24-106831", "MK 54 MOD 2 (ALWT)"): (
        "MK 54 MOD 2 Advanced Lightweight Torpedo (ALWT)",
        "The Navy's MK 54 MOD 2 program is developing an advanced lightweight",
    ),
    ("gao-24-106831", "DDG 51 Flight III"): (
        "DDG 51 Arleigh Burke Class Destroyer, Flight III (DDG 51)",
        "The Navy's DDG 51 Flight III destroyer is planned to be a "
        "multimission ship",
    ),
    ("gao-24-106831", "Resilient MW/MT MEO"): (
        "Resilient Missile Warning (MW)/Missile Tracking (MT) Medium Earth "
        "Orbit (MEO) - Epoch 1",
        "Resilient MW/MT MEO is a new effort by the Space Force's Space "
        "Systems Command (SSC)",
    ),
    ("gao-23-106059", "MK 54 MOD 2 (ALWT)"): (
        "MK 54 MOD 2 Advanced Lightweight Torpedo (ALWT)",
        "The Navy's MK 54 MOD 2 program is developing an advanced lightweight",
    ),
    ("gao-23-106059", "B-52 CERP RVP"): (
        "B-52 Commercial Engine Replacement Program (CERP) Rapid Virtual "
        "Prototype (RVP)",
        "The CERP RVP effort is expected to deliver a virtual system prototype",
    ),
    ("gao-23-106059", "DDG 51 Flight III"): (
        "DDG 51 Arleigh Burke Class Destroyer, Flight III",
        "The Navy's DDG 51 Flight III destroyer is planned to be a "
        "multimission ship",
    ),
}


@pytest.mark.parametrize("slug,common", sorted(HEADING_EXPECTED))
def test_the_heading_stops_where_gao_stops_it(slug, common):
    d = FIXTURES / slug
    manifest = json.loads((d / "manifest.json").read_text())
    case = next(
        c for c in manifest["heading_cases"] if c["common_name"] == common
    )
    edition = _edition(manifest["product_number"])
    want_name, want_desc = HEADING_EXPECTED[(slug, common)]
    (a,) = G.parse_edition_pages([(d / case["file"]).read_text()], edition)
    assert a.common_name == common
    assert a.program_name == want_name
    assert a.description.startswith(want_desc)
    assert not G.heading_defect(a)


def test_a_banner_page_that_parses_no_assessment_raises():
    """The silent drop is the failure this module is built to refuse.

    A page GAO banners as an Appendix I program and the parser emits nothing
    for is a missed program, not noise: the index-row count is an upper bound
    and cannot see it, so the banner set is diffed against the emitted set and
    the difference is raised.
    """
    page = (
        "MDAP Lead Component: Navy Common Name: MK 54 MOD 2 (ALWT)\n"
        "MK 54 MOD 2 Advanced Lightweight Torpedo (ALWT)\n"
        "Too short to be GAO's paragraph.\n"
        "Page 175 GAO-24-106831 Weapon Systems Annual Assessment"
    )
    with pytest.raises(RuntimeError, match="MK 54 MOD 2"):
        G.parse_edition_pages([page], _edition("GAO-24-106831"))


def test_heading_defect_catches_a_swallowed_first_description_line():
    """The head of the quote, guarded the way DESC_RESIDUE_RE guards its tail.

    Both shapes the over-consuming rule produced: a program_name carrying a
    sentence, and a description that starts mid-sentence.
    """
    good = replace(
        _a("GAO-24-106831", 2024, "Navy", "DDG 51 Flight III", 163),
        program_name="DDG 51 Arleigh Burke Class Destroyer, Flight III",
        description=(
            "The Navy's DDG 51 Flight III destroyer is planned to be a "
            "multimission ship designed to operate against air, surface, and "
            "underwater threats."
        ),
    )
    assert G.heading_defect(good) == ""
    prose = replace(
        good,
        program_name=(
            "DDG 51 Arleigh Burke Class Destroyer, Flight III (DDG 51) The "
            "Navy's DDG 51 Flight III destroyer is planned to be a "
            "multimission ship"
        ),
    )
    assert "sentence" in G.heading_defect(prose)
    fragment = replace(good, description="designed to operate against air.")
    assert "mid-sentence" in G.heading_defect(fragment)


# ── the exporter inherits older editions under the ratified anchor ──────────


def _write_parquet(path: Path, col_defs: str, rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.execute(f"create table _t ({col_defs})")
        con.executemany(
            "insert into _t values (" + ",".join("?" for _ in rows[0]) + ")",
            rows,
        )
        con.execute(
            f"copy _t to '{str(path).replace(chr(39), chr(39) * 2)}' "
            "(format parquet, compression zstd)"
        )
    finally:
        con.close()


def _row(product, year, service, common, page, pred, pred_page):
    return (
        "assessment", product, f"WSAA {year}",
        f"https://www.gao.gov/products/{product.lower()}", product,
        f"https://www.gao.gov/assets/{product.lower()}.pdf", f"{year}-06",
        service, "MDAP", f"LGM-35A {common}", common, page, page + 10,
        "The Air Force's Sentinel is intended to replace Minuteman III. " * 3,
        year, G.program_key(common), pred, pred_page,
    )


def test_exporter_inherits_older_editions_under_the_ratified_anchor(tmp_path):
    from govbudget.export_site import _emit_gao_program_findings_sidecar

    _write_parquet(
        tmp_path / "parquet" / "oversight" / "gao_program_assessments.parquet",
        G._COLUMNS,
        [
            _row("GAO-25-107569", 2025, "Air Force", "Sentinel", 79,
                 "GAO-24-106831", 94),
            _row("GAO-24-106831", 2024, "Air Force", "Sentinel", 84,
                 "GAO-23-106059", 87),
            _row("GAO-23-106059", 2023, "Air Force", "Sentinel", 77, "", 0),
            _row("GAO-23-106059", 2023, "Navy", "CH-53K", 60, "", 0),
        ],
    )
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "product_number,gao_program,slug,verdict,org,corpus_title,"
        "matched_on,curator_notes\n"
        "GAO-25-107569,Sentinel,0101125F,y,F,LGM-35A Sentinel,Sentinel,"
        "narrative names Sentinel\n"
    )
    json_dir = tmp_path / "json"
    json_dir.mkdir()
    _emit_gao_program_findings_sidecar(
        json_dir=json_dir, duckdb_path=tmp_path / "x.duckdb", seed_path=seed,
    )
    obj = json.loads((json_dir / "gao_program_findings.json").read_text())
    items = obj["by_slug"]["0101125F"]["assessments"]
    assert [
        (i["product_number"], i["edition_year"], i["inherited_from"])
        for i in items
    ] == [
        ("GAO-25-107569", 2025, None),
        ("GAO-24-106831", 2024, "GAO-25-107569"),
        ("GAO-23-106059", 2023, "GAO-25-107569"),
    ]
    assert all(i["program_key"] == "sentinel" for i in items)
    assert items[1]["report_page"] == 84 and items[1]["pdf_page"] == 94
    assert "CH-53K" not in json.dumps(obj)  # no chain reaches it: no page
    assert obj["stats"]["editions_ingested"] == 3
    assert obj["stats"]["inherited_items"] == 2
    assert obj["stats"]["rendered_items"] == 3
    assert obj["stats"]["assessments_ingested"] == 4
    # CH-53K: assessed in 2023 only, so no chain reaches it (the gap ¶2 states).
    assert obj["stats"]["unlinked_older_programs"] == 1
    assert [e["edition_year"] for e in obj["source"]] == [2023, 2024, 2025]
    assert obj["source"][2]["report_title"] == "WSAA 2025"
    # Gate 21 leg h8 reads this map instead of keeping its own copy of it.
    assert obj["service_families"] == G._SERVICE_FAMILY
    assert obj["service_families"]["DOD"] == obj["service_families"]["Joint"]


def test_exporter_refuses_a_census_that_does_not_add_up(tmp_path):
    """/methodology/ prints the split; the exporter is what makes it true.

    The sentence is "N pages carry {rendered_items} GAO items — {accepted}
    ratified attributions and {inherited_items} earlier editions inherited
    from them", every number derived from this sidecar's stats. Its arithmetic
    is an ASSUMPTION about the emit loop: one parquet row per ratified
    (product, program) pair, and nothing else rendered. Here a verdict-"y"
    pairing names a program the parquet has no row for, so it renders nothing
    and 3 != 2 + 2 — the state in which that sentence would decompose 3 items
    into 4. Stop the export rather than publish the subtraction.
    """
    from govbudget.export_site import _emit_gao_program_findings_sidecar

    _write_parquet(
        tmp_path / "parquet" / "oversight" / "gao_program_assessments.parquet",
        G._COLUMNS,
        [
            _row("GAO-25-107569", 2025, "Air Force", "Sentinel", 79,
                 "GAO-24-106831", 94),
            _row("GAO-24-106831", 2024, "Air Force", "Sentinel", 84,
                 "GAO-23-106059", 87),
            _row("GAO-23-106059", 2023, "Air Force", "Sentinel", 77, "", 0),
        ],
    )
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "product_number,gao_program,slug,verdict,org,corpus_title,"
        "matched_on,curator_notes\n"
        "GAO-25-107569,Sentinel,0101125F,y,F,LGM-35A Sentinel,Sentinel,ok\n"
        "GAO-25-107569,Ghost Program,0101125F,y,F,LGM-35A Sentinel,Ghost,"
        "ratified against a row this edition does not carry\n"
    )
    json_dir = tmp_path / "json"
    json_dir.mkdir()
    with pytest.raises(RuntimeError, match="rendered_items"):
        _emit_gao_program_findings_sidecar(
            json_dir=json_dir, duckdb_path=tmp_path / "x.duckdb",
            seed_path=seed,
        )


def test_exporter_refuses_a_parquet_without_the_edition_stamp(tmp_path):
    from govbudget.export_site import _emit_gao_program_findings_sidecar

    old_cols = G._COLUMNS.split(", edition_year")[0]
    _write_parquet(
        tmp_path / "parquet" / "oversight" / "gao_program_assessments.parquet",
        old_cols,
        [_row("GAO-25-107569", 2025, "Air Force", "Sentinel", 79, "", 0)[:14]],
    )
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "product_number,gao_program,slug,verdict,org,corpus_title,"
        "matched_on,curator_notes\n"
        "GAO-25-107569,Sentinel,0101125F,y,F,LGM-35A Sentinel,Sentinel,ok\n"
    )
    json_dir = tmp_path / "json"
    json_dir.mkdir()
    with pytest.raises(RuntimeError, match="edition_year"):
        _emit_gao_program_findings_sidecar(
            json_dir=json_dir, duckdb_path=tmp_path / "x.duckdb",
            seed_path=seed,
        )
