"""export_site._route_safe_page_fields (families piece-1 follow-ups design
§4.6, #194; owner Q1 (a), Q2, Q5): the sidecar of a page keyed by a
route-safe page key names the code its P-1 prints, the seed's exhibit
family and the restated R-1 line of its account; every other page gets
nothing."""
from govbudget.export_site import _route_safe_page_fields


def test_the_o_and_m_page_names_its_printed_code_and_the_restated_line():
    assert _route_safe_page_fields("0390DOM") == {
        "printed_code": "O&M",
        "exhibit_family": "om",
        "restated_lines": [{
            "line_item_code": "RDT&E",
            "title": "Chem Demilitarization - RDT&E",
            "program_elements": ["0708081D", "0708083D"],
        }],
    }


def test_every_other_page_gets_nothing():
    for pe in ("0708081D", "0708083D", "O&M", "RDT&E", "F015EX", "0390D"):
        assert _route_safe_page_fields(pe) == {}
