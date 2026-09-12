"""Dump one assessment page + one index-table page + the heading-rule pages
per WSAA edition into tests/fixtures/oversight/wsaa/<slug>/ so the layout
tests run without the 40 MB volumes.  Reads the cached PDFs under
data/raw/gao/; never fetches.

    uv run python tests/oversight/wsaa_fixture_tool.py GAO-24-106831 GAO-23-106059

The manifest pins what the parser read at dump time.  Before committing, open
assessment.txt and confirm by eye that its banner line carries the manifest's
service / type / common name and its footer the manifest's report page — that
look is what turns a parser echo into a fixture.

``HEADING_CASES`` names the pages whose heading GAO typesets in a way the
common-name rule got wrong (measured 2026-09-12): three the contiguous rule
dropped outright and three where it swallowed GAO's first description line.
Those pages are dumped verbatim and located by the BANNER (never by the
heading rule under test), and ``test_gao_editions.py`` carries the expected
heading and description head read by eye off the page — a parser echo would
pin the defect instead of the fix.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from govbudget import config
from govbudget.oversight import gao_programs as G

OUT = Path(__file__).resolve().parents[1] / "fixtures" / "oversight" / "wsaa"

# product -> the banner common names whose heading the rule must get right.
HEADING_CASES = {
    "GAO-24-106831": (
        "MK 54 MOD 2 (ALWT)",      # dropped: name not contiguous in the heading
        "DDG 51 Flight III",       # over-consumed: heading swallowed a sentence
        "Resilient MW/MT MEO",     # over-consumed: heading swallowed a sentence
    ),
    "GAO-23-106059": (
        "MK 54 MOD 2 (ALWT)",      # dropped
        "B-52 CERP RVP",           # dropped: name spans two heading lines
        "DDG 51 Flight III",       # over-consumed
    ),
}


def _banner_pages(pages: list[str], edition: G.Edition) -> dict[str, int]:
    """PDF page (1-based) of each banner common name, by normalized key.

    Located by ``Layout.banner`` alone so a fixture for a page the heading
    rule DROPS can still be dumped.
    """
    found: dict[str, int] = {}
    for i, raw in enumerate(pages):
        if not raw:
            continue
        b = edition.layout.banner(raw)
        if b is None or edition.layout.pageno(raw) is None:
            continue
        key = G._key(G._clean(b.group("common")))
        found.setdefault(key, i + 1)
    return found


def main(products: list[str]) -> None:
    for product in products:
        edition = next(e for e in G.EDITIONS if e.product_number == product)
        pdf = config.RAW_DIR / "gao" / f"{edition.slug}.pdf"
        pages = G.extract_pdf_pages(pdf)
        parsed = G.parse_edition_pages(pages, edition)
        if not parsed:
            sys.exit(f"{product}: parsed 0 assessments; fix the layout first")
        first = parsed[0]
        index_pages = [
            i for i, raw in enumerate(pages)
            if edition.layout.index_header(raw) is not None
        ]
        if not index_pages:
            sys.exit(f"{product}: no index-table page found")
        idx = index_pages[0]
        d = OUT / edition.slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "assessment.txt").write_text(pages[first.pdf_page - 1])
        (d / "index.txt").write_text(pages[idx])
        banner_pages = _banner_pages(pages, edition)
        headings = []
        for common in HEADING_CASES.get(product, ()):
            key = G._key(common)
            if key not in banner_pages:
                sys.exit(f"{product}: no banner page for {common!r}")
            page_no = banner_pages[key]
            name = f"heading-{key}.txt"
            (d / name).write_text(pages[page_no - 1])
            headings.append(
                {"common_name": common, "file": name, "pdf_page": page_no}
            )
        manifest = {
            "assessment_pdf_page": first.pdf_page,
            "assessment_type": first.assessment_type,
            "common_name": first.common_name,
            "description_starts": first.description[:60],
            "generated_by": "tests/oversight/wsaa_fixture_tool.py",
            "heading_cases": headings,
            "index_count_on_page": G.index_table_program_counts(
                [pages[idx]], edition.layout
            ),
            "index_pdf_page": idx + 1,
            "product_number": product,
            "report_page": first.report_page,
            "service": first.service,
        }
        (d / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        print(
            f"{product}: {d} <- pdf p.{first.pdf_page} ({first.common_name}) "
            f"+ index p.{idx + 1} ({manifest['index_count_on_page']} programs)"
            + "".join(f" + heading p.{h['pdf_page']}" for h in headings)
        )


if __name__ == "__main__":
    main(sys.argv[1:])
