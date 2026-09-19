import hashlib
import io
import zipfile
from pathlib import Path

import httpx
import psycopg
import pytest
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


# ---------------------------------------------------------------------------
# The worktree-symlink regression, over ALL FOUR `file_path` writers.
#
# Doc 459 (FY2026 DHP volume, 2026-09-12) was acquired through a worktree's
# `data/raw_docs` symlink and recorded a `<worktree>/…` `file_path`. Every
# reader re-opens that string verbatim later — `export_site`'s copy loop raises
# FileNotFoundError on a missing source — so the path must name the SHARED lake,
# which outlives the worktree. Round 1 fixed three writers and found the fourth
# (`cli._service_archive_download`) still on `str(dest)`; these tests pin all
# four. A FIFTH writer is caught by the source census at the end of this module
# — these four cases cannot see a writer that does not exist yet, which is how
# the fourth one stayed invisible until a human re-grepped.
# ---------------------------------------------------------------------------


def _symlinked_lake(tmp_path: Path) -> tuple[Path, Path]:
    """(lake, view) — `view` is a worktree-style symlink pointing into `lake`."""
    lake = tmp_path / "lake"
    lake.mkdir()
    data = tmp_path / "worktree" / "data"
    data.mkdir(parents=True)
    view = data / "raw_docs"
    view.symlink_to(lake)
    return lake, view


def _assert_canonical(file_path: str, expected: Path) -> None:
    assert file_path == str(expected.resolve())
    assert "/worktree/" not in file_path
    assert Path(file_path).exists()


def test_acquire_records_the_symlink_resolved_lake_path(pg_dsn, tmp_path):
    """Writer 1/4 — `acquire.acquire_pending` (the step that wrote doc 459)."""
    lake, view = _symlinked_lake(tmp_path)

    upsert_documents(pg_dsn, [
        {"org": "DHA", "exhibit_family": "rdte", "fiscal_year": 2026,
         "title": "dhp.pdf", "source_url": "https://example.test/dhp.pdf"},
    ])

    def handler(request):
        return httpx.Response(200, content=make_pdf_bytes(False))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        n, failures = acquire_pending(
            pg_dsn, client, raw_docs_dir=view, min_free_gb=0
        )
    assert (n, failures) == (1, [])

    with psycopg.connect(pg_dsn) as con:
        (file_path,) = con.execute(
            "select file_path from jbook_documents where title = 'dhp.pdf'"
        ).fetchone()
    _assert_canonical(file_path, lake / "fy2026" / "dha" / "dhp.pdf")


def test_register_local_records_the_symlink_resolved_lake_path(pg_dsn, tmp_path):
    """Writer 2/4 — `service_fetch.register_local_documents` (`jbooks ingest-local`).

    Here the symlink is on the operator's DROP DIR, not on `raw_docs`: the row
    is registered pointing at wherever the operator dropped the file, so a drop
    dir reached through a symlink records the same doomed view.
    """
    from govbudget.jbooks.service_fetch import register_local_documents

    real_drop = tmp_path / "lake" / "drop"
    real_drop.mkdir(parents=True)
    (real_drop / "RDTE - Vol 1 - Budget Activity 1.pdf").write_bytes(
        make_pdf_bytes(False)
    )
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    view = worktree / "drop"
    view.symlink_to(real_drop)

    inserted, skipped = register_local_documents(
        pg_dsn, view, fiscal_year=2026,
        source_url="https://www.asafm.army.mil/rdte-vol1.pdf",
    )
    assert (inserted, skipped) == (1, [])

    with psycopg.connect(pg_dsn) as con:
        (file_path,) = con.execute(
            "select file_path from jbook_documents"
        ).fetchone()
    _assert_canonical(file_path, real_drop / "RDTE - Vol 1 - Budget Activity 1.pdf")


def test_service_acquire_records_the_symlink_resolved_lake_path(pg_dsn, tmp_path):
    """Writer 3/4 — `service_fetch.download_registered_playwright` (Navy route).

    The browser context is the only injected collaborator; the row lifecycle and
    the `file_path` write are the real ones.
    """
    from govbudget.jbooks.service_fetch import download_registered_playwright

    lake, view = _symlinked_lake(tmp_path)
    body = make_pdf_bytes(False)

    class _Resp:
        status = 200

        def body(self):
            return body

    class _Request:
        def get(self, url, timeout=None):
            return _Resp()

    class _Context:
        request = _Request()

    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year,"
            " title, source_url, status, acquisition) values ('N','rdte',2026,"
            " 'navy_rdte_vol1.pdf','https://www.secnav.navy.mil/x.pdf',"
            " 'registered','playwright')"
        )

    done, failures = download_registered_playwright(
        _Context(), pg_dsn, raw_docs_dir=view, fiscal_year=2026,
        min_free_gb=0, throttle_s=0, log=lambda *_: None,
    )
    assert (done, failures) == (1, [])

    with psycopg.connect(pg_dsn) as con:
        (file_path,) = con.execute(
            "select file_path from jbook_documents"
        ).fetchone()
    _assert_canonical(file_path, lake / "fy2026" / "n" / "navy_rdte_vol1.pdf")


def test_archive_acquire_records_the_symlink_resolved_lake_path(
    pg_dsn, tmp_path, monkeypatch
):
    """Writer 4/4 — `cli._service_archive_download` (`backfill --source archive`).

    The route ROADMAP #111 prescribes for the WAF-blocked services, and the one
    the round-1 fix missed: 17 rows already carry `acquisition='archive'`. Only
    the Wayback fetch is injected; `config.RAW_DOCS_DIR` is pointed at a
    worktree-style symlink, exactly as it is in a real worktree run.
    """
    from govbudget import cli, config
    from govbudget.jbooks import archive_fetch

    lake, view = _symlinked_lake(tmp_path)
    monkeypatch.setattr(config, "RAW_DOCS_DIR", view)
    monkeypatch.setattr(config, "PG_DSN", pg_dsn)
    monkeypatch.setattr(archive_fetch, "build_client",
                        lambda **kw: httpx.Client())

    body = make_pdf_bytes(False)

    def fake_download(client, original_url, dest, **kw):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(body)
        return archive_fetch.DownloadResult(
            original_url=original_url, wayback_url="https://web.archive.org/x",
            snapshot_timestamp="20260101000000",
            sha256=hashlib.sha256(body).hexdigest(), bytes=len(body),
        )

    monkeypatch.setattr(archive_fetch, "download_via_archive", fake_download)

    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year,"
            " title, source_url, status, acquisition) values ('A','rdte',2026,"
            " 'army_rdte_vol1.pdf','https://www.asafm.army.mil/x.pdf',"
            " 'registered','archive')"
        )

    done, gaps = cli._service_archive_download("army", 2026)
    assert (done, gaps) == (1, [])

    with psycopg.connect(pg_dsn) as con:
        (file_path,) = con.execute(
            "select file_path from jbook_documents"
        ).fetchone()
    _assert_canonical(file_path, lake / "fy2026" / "a" / "army_rdte_vol1.pdf")


# ---------------------------------------------------------------------------
# The same rule at the ROOT: the config constants every writer starts from.
# ---------------------------------------------------------------------------


def test_config_lake_path_collapses_a_symlinked_lake_dir(tmp_path):
    """`config._lake_path` resolves the per-entry symlink a worktree installs."""
    from govbudget.config import _lake_path

    lake = tmp_path / "lake" / "raw_docs"
    lake.mkdir(parents=True)
    data = tmp_path / "worktree" / "data"
    data.mkdir(parents=True)
    (data / "raw_docs").symlink_to(lake)

    assert _lake_path(data, "raw_docs") == lake.resolve()
    # and it keeps carrying through to the paths writers actually build
    assert _lake_path(data, "raw_docs", "fy2026", "dha", "dhp.pdf") == (
        lake / "fy2026" / "dha" / "dhp.pdf"
    )


@pytest.mark.parametrize("parts", [("raw_docs",), ("raw_docs", "fy2026", "x.pdf")])
def test_config_lake_path_is_a_noop_without_a_symlink(tmp_path, parts):
    """The main checkout: no symlink, nothing moves — including for a path that
    does not exist yet, which is every `dest` before its download."""
    data = (tmp_path / "data").resolve()
    (data / "raw_docs").mkdir(parents=True)
    from govbudget.config import _lake_path

    assert _lake_path(data, *parts) == data.joinpath(*parts)


# ---------------------------------------------------------------------------
# The census the docs already claimed (Task 17c rider).
#
# LAUNCH.md, the block comment above and tests/test_config.py all promised
# that a FIFTH `file_path` writer would show up as a red test. Nothing
# checked that: the four tests above pin the four writers that EXIST, and a
# fifth one added tomorrow passes all of them by being invisible. Round 2's
# fourth writer was found by a human grepping `file_path`, which is exactly
# the detection this replaces.
#
# This parses the package's own source for SQL that writes `file_path` and
# asserts the writer set is the four known ones — so the docs' claim is a
# test, not a hope. Method and its limits, stated rather than assumed:
#
#   1. every statement in this codebase is ONE string literal (adjacent
#      literals are joined by the parser before the AST sees them), so the
#      literal boundary is the statement boundary; SQL assembled at runtime
#      from fragments would escape the census, and there is none today;
#   2. `writes_file_path` inspects only the FIRST `insert into … (cols)` and
#      the first `update … set …` in a literal — both regexes `search` once.
#      One of EACH kind is inspected, though, and the insert check falls
#      through to the update check: a literal whose first statement is an
#      innocent insert and whose second is `update … set file_path = …` IS
#      caught. What escapes is a writer that repeats a kind already matched —
#      a second insert after an insert, a second update after an update. That
#      shape does not exist today (limit 1 is why), and a multi-statement
#      literal is the thing to look at by hand if this census ever disagrees
#      with a grep. The test below plants both shapes.
# ---------------------------------------------------------------------------

#: (module path relative to the package, function) for every site that writes
#: jbook_documents.file_path, each with its own symlink regression test above.
FILE_PATH_WRITERS = {
    ("cli.py", "_service_archive_download"),
    ("jbooks/acquire.py", "acquire_pending"),
    ("jbooks/service_fetch.py", "register_local_documents"),
    ("jbooks/service_fetch.py", "download_registered_playwright"),
}


def _file_path_writer_census(src_root: Path | None = None) -> set[tuple[str, str]]:
    """{(module, function)} for every SQL literal that writes file_path.

    `src_root` defaults to the installed package and is injectable so the
    control test below can run this SAME function over a synthetic tree — a
    census proven on a copy of its own logic proves nothing.
    """
    import ast
    import re

    if src_root is None:
        import govbudget

        src_root = Path(govbudget.__file__).resolve().parent
    insert_re = re.compile(r"insert\s+into\s+(\w+)\s*\(([^)]*)\)")
    # The SET clause only: "update scrape_runs set note=%s where file_path is
    # null" names file_path in its WHERE and writes nothing.
    update_re = re.compile(r"update\s+(\w+)\s+set\b(.*?)(?:\swhere\s|$)")

    def writes_file_path(sql: str) -> bool:
        low = " ".join(sql.lower().split())
        if "file_path" not in low:
            return False
        m = insert_re.search(low)
        if m and "file_path" in m.group(2):
            return True
        m = update_re.search(low)
        return bool(m and "file_path" in m.group(2))

    found: set[tuple[str, str]] = set()
    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text())
        funcs = [
            (n.lineno, n.end_lineno or n.lineno, n.name)
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if not writes_file_path(node.value):
                continue
            enclosing = sorted(
                (f for f in funcs if f[0] <= node.lineno <= f[1]),
                key=lambda f: f[1] - f[0],
            )
            found.add((
                str(path.relative_to(src_root)),
                enclosing[0][2] if enclosing else "<module>",
            ))
    return found


def test_file_path_writer_census_matches_the_four_tested_writers():
    """A fifth writer is a red test here, not a dead citation later."""
    assert _file_path_writer_census() == FILE_PATH_WRITERS, (
        "the set of source sites that write file_path changed. Every writer must"
        " route its path through jbooks.acquire.lake_path and gain a symlink"
        " regression test in this module; then add it to FILE_PATH_WRITERS and"
        " to the command table in docs/superpowers/LAUNCH.md"
    )


def test_the_census_sees_a_fifth_writer_in_either_sql_shape(tmp_path):
    """The control, through the census itself.

    A census that matched FILE_PATH_WRITERS because it finds NOTHING would
    pass just as quietly. Both write shapes (update … set, insert … (cols))
    are planted in a synthetic package, along with two decoys that name
    file_path without writing it — a SELECT and an unrelated table's update.
    """
    pkg = tmp_path / "pkg"
    (pkg / "jbooks").mkdir(parents=True)
    (pkg / "cli.py").write_text(
        "def sneaky_update(con, dest, doc_id):\n"
        "    con.execute(\n"
        '        "update jbook_documents set status=\'downloaded\', file_path=%s,"\n'
        '        " sha256=%s where id=%s",\n'
        "        (str(dest), None, doc_id),\n"
        "    )\n"
    )
    (pkg / "jbooks" / "loader.py").write_text(
        "def sneaky_insert(con, p):\n"
        "    con.execute(\n"
        '        "insert into jbook_documents (org, file_path, status)"\n'
        '        " values (%s,%s,\'registered\')",\n'
        "        ('X', str(p)),\n"
        "    )\n"
        "\n"
        "def reader(con):\n"
        '    return con.execute("select id, file_path from jbook_documents").fetchall()\n'
        "\n"
        "def other_table(con, p):\n"
        '    con.execute("update scrape_runs set note=%s where file_path is null", (p,))\n'
    )

    assert _file_path_writer_census(pkg) == {
        ("cli.py", "sneaky_update"),
        ("jbooks/loader.py", "sneaky_insert"),
    }


def test_the_census_blind_spot_is_a_repeat_of_the_same_statement_kind(tmp_path):
    """Limit 2, stated exactly: which multi-statement literal escapes.

    The comment above used to say a literal whose SECOND statement is the
    writer is invisible. It is not: `writes_file_path` searches once for an
    insert and, failing that, once for an update, so a mixed literal is still
    caught. Only a repeat of a kind already matched hides. Both are planted
    here so the stated limit is a test rather than a reading of the regexes.
    """
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "mixed.py").write_text(
        "def caught(con, p, doc_id):\n"
        "    con.execute(\n"
        '        "insert into scrape_runs (note) values (%s);"\n'
        '        " update jbook_documents set file_path=%s where id=%s",\n'
        "        ('x', str(p), doc_id),\n"
        "    )\n"
    )
    (pkg / "repeat.py").write_text(
        "def hidden(con, p):\n"
        "    con.execute(\n"
        '        "insert into scrape_runs (note) values (%s);"\n'
        '        " insert into jbook_documents (org, file_path) values (%s,%s)",\n'
        "        ('x', 'X', str(p)),\n"
        "    )\n"
    )

    assert _file_path_writer_census(pkg) == {("mixed.py", "caught")}
