import io
import zipfile
from pathlib import Path

import httpx
import psycopg
from pypdf import PdfWriter

from govbudget.jbooks.acquire import acquire_pending
from govbudget.jbooks.registry import upsert_documents

XML = b'<?xml version="1.0"?><root/>'


def make_pdf_bytes(with_attachment: bool) -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    if with_attachment:
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w") as z:
            z.writestr("book.xml", XML)
        w.add_attachment("book.zzz", zbuf.getvalue())
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def test_acquire_downloads_detects_xml_and_updates_rows(pg_dsn, tmp_path):
    upsert_documents(pg_dsn, [
        {"org": "DARPA", "exhibit_family": "rdte", "fiscal_year": 2026,
         "title": "darpa.pdf", "source_url": "https://example.test/darpa.pdf"},
        {"org": "NOXML", "exhibit_family": "rdte", "fiscal_year": 2026,
         "title": "noxml.pdf", "source_url": "https://example.test/noxml.pdf"},
        {"org": "DoD", "exhibit_family": "rollup", "fiscal_year": 2026,
         "title": "r1_display.xlsx", "source_url": "https://example.test/r1_display.xlsx"},
    ])
    payloads = {
        "/darpa.pdf": make_pdf_bytes(True),
        "/noxml.pdf": make_pdf_bytes(False),
        "/r1_display.xlsx": b"PK\x03\x04fakexlsx",
    }

    def handler(request):
        return httpx.Response(200, content=payloads[request.url.path])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        n, failures = acquire_pending(pg_dsn, client, raw_docs_dir=tmp_path, min_free_gb=0)
    assert n == 3
    assert failures == []
    with psycopg.connect(pg_dsn) as con:
        rows = {
            r[0]: r for r in con.execute(
                "select title, status, has_embedded_xml, file_path, sha256 from jbook_documents"
            )
        }
    assert rows["darpa.pdf"][1] == "downloaded" and rows["darpa.pdf"][2] is True
    assert rows["noxml.pdf"][2] is False
    assert rows["r1_display.xlsx"][2] is None  # xlsx: attachment check not applicable
    assert (tmp_path / "fy2026" / "darpa" / "darpa.pdf").exists()
    assert (tmp_path / "fy2026" / "darpa" / "xml" / "book.xml").exists()

    # second run: nothing pending
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        n2, f2 = acquire_pending(pg_dsn, client, raw_docs_dir=tmp_path, min_free_gb=0)
    assert (n2, f2) == (0, [])


def test_acquire_continues_past_corrupt_pdf_and_marks_failed(pg_dsn, tmp_path):
    upsert_documents(pg_dsn, [
        {"org": "BAD", "exhibit_family": "rdte", "fiscal_year": 2026,
         "title": "bad.pdf", "source_url": "https://example.test/bad.pdf"},
        {"org": "GOOD", "exhibit_family": "rdte", "fiscal_year": 2026,
         "title": "good.pdf", "source_url": "https://example.test/good.pdf"},
    ])
    payloads = {
        "/bad.pdf": b"%PDF-1.4 this is not really a pdf",
        "/good.pdf": make_pdf_bytes(True),
    }

    def handler(request):
        return httpx.Response(200, content=payloads[request.url.path])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        n, failures = acquire_pending(pg_dsn, client, raw_docs_dir=tmp_path, min_free_gb=0)
    assert n == 1
    assert len(failures) == 1 and failures[0][1] == "bad.pdf"
    with psycopg.connect(pg_dsn) as con:
        statuses = dict(con.execute("select title, status from jbook_documents"))
    assert statuses == {"bad.pdf": "failed", "good.pdf": "downloaded"}

    # re-run: failed doc is NOT retried (no infinite re-download loop)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        n2, f2 = acquire_pending(pg_dsn, client, raw_docs_dir=tmp_path, min_free_gb=0)
    assert (n2, f2) == (0, [])


def test_acquire_records_the_symlink_resolved_lake_path(pg_dsn, tmp_path):
    """A worktree's `data/raw_docs` is a symlink into the shared lake.

    Regression for doc 459 (FY2026 DHP volume, 2026-09-12): acquiring through
    that symlink recorded a `<worktree>/…` `file_path` that every reader —
    `export_site`'s copy loop raises FileNotFoundError on a missing source —
    would follow into a directory that disappears when the worktree is removed.
    `file_path` must name the resolved target, like every other row.
    """
    lake = tmp_path / "lake"
    lake.mkdir()
    view = tmp_path / "worktree" / "data"
    view.mkdir(parents=True)
    (view / "raw_docs").symlink_to(lake)          # the worktree's view of the lake

    upsert_documents(pg_dsn, [
        {"org": "DHA", "exhibit_family": "rdte", "fiscal_year": 2026,
         "title": "dhp.pdf", "source_url": "https://example.test/dhp.pdf"},
    ])

    def handler(request):
        return httpx.Response(200, content=make_pdf_bytes(False))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        n, failures = acquire_pending(
            pg_dsn, client, raw_docs_dir=view / "raw_docs", min_free_gb=0
        )
    assert (n, failures) == (1, [])

    with psycopg.connect(pg_dsn) as con:
        (file_path,) = con.execute(
            "select file_path from jbook_documents where title = 'dhp.pdf'"
        ).fetchone()
    expected = lake / "fy2026" / "dha" / "dhp.pdf"
    assert file_path == str(expected.resolve())
    assert "/worktree/" not in file_path
    assert Path(file_path).exists()
