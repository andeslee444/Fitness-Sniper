import datetime as dt
from pathlib import Path

import httpx
import psycopg

from govbudget.download import download_file, ensure_free_space
from govbudget.jbooks.attachments import extract_jbook_xml


def lake_path(dest: Path) -> str:
    """The string to record in `jbook_documents.file_path`, symlinks resolved.

    Every reader (`export_site`'s document copy loop, `verify`, `provenance_pages`)
    re-opens this string verbatim on some future machine-state, so it has to name
    the file in the SHARED lake, not in whatever view of it this process happened
    to walk. Git worktrees are the live hazard: `<worktree>/data/raw_docs` is a
    symlink into the main checkout's lake, so an un-resolved `str(dest)` records a
    path that vanishes the moment the worktree is removed (this happened to doc 459
    on 2026-09-12 — FY2026 DHP volume, repaired by hand). `Path.resolve()` collapses
    the symlink to the canonical lake path every other row already uses.

    `config._lake_path` now resolves `RAW_DOCS_DIR` itself, so a `dest` built
    from the config constant is already canonical and this call is a no-op.
    It stays at every writer because `raw_docs_dir` is an INJECTED parameter on
    three of the four (tests, `ingest-local`'s operator drop dir, and any future
    caller passing its own root) — the constant being canonical does not make an
    arbitrary argument canonical. All four writers route through here:
    `acquire.acquire_pending`, `service_fetch.register_local_documents`,
    `service_fetch.download_registered_playwright`, and
    `cli._service_archive_download`.
    """
    return str(dest.resolve())


def acquire_pending(
    dsn: str, client: httpx.Client, *, raw_docs_dir: Path, min_free_gb: float
) -> tuple[int, list[tuple[int, str, str]]]:
    """Download every 'registered' document, detect embedded XML, update rows.

    PDFs and XLSX are KEPT on disk — they are the provenance source.
    Per-document failures don't stop the sweep: the row is marked 'failed'
    (so re-runs skip it until re-registered) and reported in the second
    return value as (doc_id, title, error). Returns (downloaded_count, failures).
    """
    with psycopg.connect(dsn) as con:
        pending = con.execute(
            "select id, org, fiscal_year, title, source_url from jbook_documents "
            "where status = 'registered' order by id"
        ).fetchall()
    done = 0
    failures: list[tuple[int, str, str]] = []
    for doc_id, org, fy, title, url in pending:
        dest = raw_docs_dir / f"fy{fy}" / org.lower() / title
        try:
            ensure_free_space(dest.parent, min_free_gb)
            sha, n = download_file(client, url, dest)
            has_xml: bool | None = None
            if title.lower().endswith(".pdf"):
                xmls = extract_jbook_xml(dest, dest.parent / "xml")
                has_xml = bool(xmls)
        except Exception as e:
            failures.append((doc_id, title, f"{type(e).__name__}: {e}"))
            with psycopg.connect(dsn) as con:
                con.execute(
                    "update jbook_documents set status='failed' where id=%s", (doc_id,)
                )
            continue
        with psycopg.connect(dsn) as con:
            con.execute(
                "update jbook_documents set status='downloaded', file_path=%s, sha256=%s, "
                "bytes=%s, downloaded_at=%s, has_embedded_xml=%s where id=%s",
                (lake_path(dest), sha, n, dt.datetime.now(dt.UTC), has_xml, doc_id),
            )
        done += 1
    return done, failures
