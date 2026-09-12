"""Dump one assessment page + one index-table page per WSAA edition into
tests/fixtures/oversight/wsaa/<slug>/ so the layout tests run without the
40 MB volumes.  Reads the cached PDFs under data/raw/gao/; never fetches.

    uv run python tests/oversight/wsaa_fixture_tool.py GAO-24-106831 GAO-23-106059

The manifest pins what the parser read at dump time.  Before committing, open
assessment.txt and confirm by eye that its banner line carries the manifest's
service / type / common name and its footer the manifest's report page — that
look is what turns a parser echo into a fixture.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from govbudget import config
from govbudget.oversight import gao_programs as G

OUT = Path(__file__).resolve().parents[1] / "fixtures" / "oversight" / "wsaa"


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
        manifest = {
            "assessment_pdf_page": first.pdf_page,
            "assessment_type": first.assessment_type,
            "common_name": first.common_name,
            "description_starts": first.description[:60],
            "generated_by": "tests/oversight/wsaa_fixture_tool.py",
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
        )


if __name__ == "__main__":
    main(sys.argv[1:])
