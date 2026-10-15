"""A synthetic PB2026 book set for the #195 tests (Tasks 23a, 23b, 23c, 24).

Org 'A' RDT&E, fiscal year 2026: volume BA1 is the downloaded book every
narrative is attached to (its master XML holds all six narratives); BA2, BA3
and BA4 are superseded volumes of the same book set; an org 'N' book is
outside the set. Each narrative and where its words are printed:

  N1 0605001TST  BA1 p1 prints only the opening; BA2 p2 prints it whole
                 -> stored on BA1 p1 by the pre-#195 builder; relocated to BA2 p2
  N2 0605002TST  BA3 p1-p2 prints it whole across the page break
                 -> stored unresolved; located on BA3 p1
  N3 0605003TST  printed nowhere -> stays unresolved
  N4 0605004TST  BA1 p2 prints it whole -> kept
  N5 0605005TST  BA1 p3 prints only the opening; nothing prints the closing
                 -> stays on BA1 p3 (opening_only)
  N6 0605006TST  only the org 'N' book prints it -> stays unresolved
  BA4 prints none of them and is never cited.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import psycopg

from pdf_factory import make_pdf

R2 = "Exhibit R-2, RDT&E Budget Item Justification"

BODIES = {
    "N1": ("0605001TST", "The Alpha program fields a new radar for the fleet. It replaces three"
                         " legacy sets and the work continues through the final test event in FY 2027."),
    "N2": ("0605002TST", "The Bravo effort builds a test range for hypersonic flight trials. Funding"
                         " in FY 2026 completes the range control center and the first two telemetry sites."),
    "N3": ("0605003TST", "The Charlie study is described in a classified annex that is not part of"
                         " this book and no page prints its text at all anywhere in any volume."),
    "N4": ("0605004TST", "The Delta line buys spares for the training fleet. The quantity rises in FY"
                         " 2026 because two squadrons convert to the new aircraft type."),
    "N5": ("0605005TST", "The Echo program upgrades the cockpit displays on the trainer. Work in FY"
                         " 2026 integrates the software and starts the qualification test series."),
    "N6": ("0605006TST", "The Foxtrot program buys night vision sets for the reserve units. The FY"
                         " 2026 request completes the second lot and closes out the contract."),
}

PAGES = {
    "BA1": [
        [R2, "PE 0605001TST / ALPHA",
         "The Alpha program fields a new radar for the fleet. It replaces", "three legacy sets."],
        [R2, "PE 0605004TST / DELTA",
         "The Delta line buys spares for the training fleet. The quantity rises",
         "in FY 2026 because two squadrons convert to the new aircraft type."],
        [R2, "PE 0605005TST / ECHO",
         "The Echo program upgrades the cockpit displays on the trainer. Work in FY",
         "2026 integrates the software."],
    ],
    "BA2": [
        [R2, "PE 0605009TST / OTHER", "Unrelated text on the first page of the second volume."],
        [R2, "PE 0605001TST / ALPHA",
         "The Alpha program fields a new radar for the fleet. It replaces",
         "three legacy sets and the work continues through the final test", "event in FY 2027."],
    ],
    "BA3": [
        [R2, "PE 0605002TST / BRAVO",
         "The Bravo effort builds a test range for hypersonic flight trials.", "Funding in FY 2026"],
        ["completes the range control center and the first two", "telemetry sites."],
    ],
    "BA4": [[R2, "PE 0605008TST / GOLF", "Nothing here is cited by any narrative."]],
    "NAVY": [
        [R2, "PE 0605006TST / FOXTROT",
         "The Foxtrot program buys night vision sets for the reserve units. The FY",
         "2026 request completes the second lot and closes out the contract."],
    ],
}

# (org, status, title) per volume; BA1 is the attached, downloaded book.
VOLUMES = {
    "BA1": ("A", "downloaded", "Book BA1"),
    "BA2": ("A", "superseded", "Book BA2"),
    "BA3": ("A", "superseded", "Book BA3"),
    "BA4": ("A", "superseded", "Book BA4"),
    "NAVY": ("N", "downloaded", "Navy book"),
}


def xml_path(key: str) -> str:
    return f"ProgramElement[{list(BODIES).index(key)}]/Narrative[0]"


def seed_book_set(pg_dsn: str, tmp_path: Path) -> dict:
    """Write the five PDFs, register them, attach the six narratives to BA1.

    Returns {"sha": {volume: sha256}, "doc": {volume: id}, "path": {volume: Path}}.
    Volume n (1-based, in VOLUMES order) was downloaded 2026-07-0n.
    """
    out = {"sha": {}, "doc": {}, "path": {}}
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        for n, (vol, (org, status, title)) in enumerate(VOLUMES.items(), start=1):
            path = tmp_path / f"{vol}.pdf"
            make_pdf(path, PAGES[vol])
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            doc_id = con.execute(
                "insert into jbook_documents (org, exhibit_family, fiscal_year, title,"
                " source_url, file_path, sha256, bytes, downloaded_at, has_embedded_xml,"
                " status) values (%s, 'rdte', 2026, %s, %s, %s, %s, %s, %s, true, %s)"
                " returning id",
                (org, title, f"https://example.mil/{vol}.pdf", str(path), sha,
                 path.stat().st_size, f"2026-07-0{n}T00:00:00+00:00", status),
            ).fetchone()[0]
            out["sha"][vol], out["doc"][vol], out["path"][vol] = sha, doc_id, path
        run_id = con.execute(
            "insert into extraction_runs (document_id, tier, tool_versions)"
            " values (%s, 1, '{}') returning id", (out["doc"]["BA1"],)).fetchone()[0]
        for key, (pe_bli, body) in BODIES.items():
            con.execute(
                "insert into detail_narratives (extraction_run_id, document_id, pe_bli,"
                " kind, title, body, xml_path) values (%s, %s, %s, 'mission', %s, %s, %s)",
                (run_id, out["doc"]["BA1"], pe_bli, key, body, xml_path(key)),
            )
    return out


def seed_pre_195_rows(pg_dsn: str, book: dict) -> None:
    """The rows the pre-#195 builder stored: each narrative resolved against
    BA1 alone by its opening (find_narrative_page, the old single-volume rule)."""
    from govbudget.jbooks.provenance_pages import find_narrative_page

    with psycopg.connect(pg_dsn, autocommit=True) as con:
        for key, (pe_bli, body) in BODIES.items():
            hit = find_narrative_page(book["path"]["BA1"], pe_bli=pe_bli, body=body,
                                      exhibit_family="rdte")
            con.execute(
                "insert into provenance_pages (target_kind, document_sha256, pe_bli,"
                " narrative_kind, xml_path, amount_text, page_number, x0, x1, top_pt,"
                " bottom_pt, page_width, page_height, resolution, candidate_pages)"
                " values ('narrative', %s, %s, 'mission', %s, %s, %s, %s, %s, %s, %s,"
                " %s, %s, %s, %s)",
                (book["sha"]["BA1"], pe_bli, xml_path(key), hit["search_text"],
                 hit["page_number"], hit["x0"], hit["x1"], hit["top_pt"],
                 hit["bottom_pt"], hit["page_width"], hit["page_height"],
                 hit["resolution"], hit["candidate_pages"]),
            )
