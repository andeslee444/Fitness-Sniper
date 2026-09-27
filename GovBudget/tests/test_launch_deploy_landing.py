"""R-DEC-DEPLOYSAFE (final whole-wave review, findings #14 and #15).

1. verify_live_assets.mjs must tell whether THIS deploy landed. Before the
   ruling it passed 50/50 against the previous production: it never compared
   the live /.build-meta.json with the checkout, and it checked the
   fixed-name R2 objects only for "HTTP 200, non-empty", which the old
   objects also are. Now it fails unless
     (a) the site host's /.build-meta.json git_head equals the checkout's
         HEAD (or --expect-head), and its build equals site/out's; and
     (b) every fixed-name object upload_r2.sh copies (data/site/data/**,
         data/site/citations/**) is served with the local file's sha256.
   Exercised against a local mock server; nothing here reaches the network.

2. backup_r2_data.sh copies the live fixed-name prefixes (data/, citations/)
   aside to rollback/<tag>/ before a deploy overwrites them (#177's own fix).
   Exercised with an `rclone` stub on PATH that only records its argv.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

REPO_ROOT = Path(__file__).parent.parent
LAUNCH_DIR = REPO_ROOT / "scripts" / "launch"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("node") is None or shutil.which("bash") is None,
    reason="needs git, node and bash",
)

PDF_SHA = "a" * 64
WB_SHA = "b" * 64
OLD_HEAD = "0587f90ffcbdeec4f01270f9c070604400ae279e"  # the previous production build


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


# ---------------------------------------------------------------------------
# A mock asset + site host
# ---------------------------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self._serve(send_body=True)

    def do_HEAD(self):  # noqa: N802
        self._serve(send_body=False)

    def _serve(self, send_body: bool):
        path = unquote(urlsplit(self.path).path)
        self.server.requests.append(path)
        route = self.server.routes.get(path)
        if route is None and path.startswith("/fact/"):
            route = (200, b"<html>fact shell</html>", "text/html")
        if route is None:
            route = (404, b"", "text/plain")
        status, body, ctype = route
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def log_message(self, *args):  # keep pytest output clean
        pass


@pytest.fixture()
def mock_host():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.routes = {}
    server.requests = []
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# A checkout with a build, an export, and a mock production that serves it
# ---------------------------------------------------------------------------

DATA_FILES = {
    "data/fct_budget_to_awards.parquet": b"PAR1 new fct_budget_to_awards (demotion_reason) PAR1",
    "data/fct_program_concentration.parquet": b"PAR1 new concentration (scope) PAR1",
    "data/budget_lines.parquet": b"PAR1 unchanged budget_lines PAR1",
    "citations/citations.parquet": b"PAR1 new citations 125,349 PAR1",
}


@pytest.fixture()
def landed(tmp_path: Path, mock_host):
    """A git checkout of the verifier with a built site/out and an export,
    and a mock host serving exactly that build and that export."""
    root = tmp_path / "gb"
    (root / "scripts" / "launch").mkdir(parents=True)
    shutil.copy2(LAUNCH_DIR / "verify_live_assets.mjs", root / "scripts" / "launch" / "verify_live_assets.mjs")
    (root / ".gitignore").write_text("data/site/\nsite/out/\n")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    head = _git(root, "rev-parse", "HEAD")

    site = root / "data" / "site"
    pdf = b"%PDF-1.7\n% a cited book\n"
    (site / "pdfs").mkdir(parents=True)
    (site / "pdfs" / f"{PDF_SHA}.pdf").write_bytes(pdf)
    (site / "workbooks").mkdir()
    wb = b"PK\x03\x04 a workbook"
    (site / "workbooks" / f"{WB_SHA}.xlsx").write_bytes(wb)
    (site / "json").mkdir()
    (site / "json" / "citations.json").write_text(json.dumps({"x": {"hosted_pdf_url": f"/pdfs/{PDF_SHA}.pdf"}}))
    v2 = site / "json" / "budget-pdf-receipts" / "v2"
    v2.mkdir(parents=True)
    (v2 / "abc.json").write_text(json.dumps({"abc0000000000000": {"parts": [{
        "hosted_pdf_url": f"/pdfs/{PDF_SHA}.pdf", "workbook_sha256": WB_SHA,
        "edition": 2026, "exhibit": "R-1",
    }]}}))
    for rel, body in DATA_FILES.items():
        (site / rel).parent.mkdir(parents=True, exist_ok=True)
        (site / rel).write_bytes(body)

    meta = {"built_at": "2026-09-26T22:36:02.525Z", "built_at_ms": 1790462162526, "git_head": head}
    (root / "site" / "out").mkdir(parents=True)
    (root / "site" / "out" / ".build-meta.json").write_text(json.dumps(meta, indent=2))
    (root / "site" / "public").mkdir(parents=True)
    base = f"http://127.0.0.1:{mock_host.server_address[1]}"
    (root / "site" / "public" / "config.json").write_text(json.dumps({"assetBaseUrl": base}))

    routes = mock_host.routes
    routes[f"/pdfs/{PDF_SHA}.pdf"] = (200, pdf, "application/pdf")
    routes[f"/workbooks/{WB_SHA}.xlsx"] = (200, wb, "application/octet-stream")
    for rel, body in DATA_FILES.items():
        routes[f"/{rel}"] = (200, body, "application/octet-stream")
    routes["/.build-meta.json"] = (200, json.dumps(meta).encode(), "application/json")
    routes["/json/years_matrix.json"] = (200, b"{}", "application/json")

    def run(*args: str):
        return subprocess.run(
            ["node", str(root / "scripts" / "launch" / "verify_live_assets.mjs"), f"--site={base}", *args],
            cwd=tmp_path, capture_output=True, text=True, timeout=120,
        )

    return root, head, meta, mock_host, run


def test_a_deploy_that_landed_passes(landed):
    root, head, meta, host, run = landed
    r = run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"PASS: /.build-meta.json git_head — {head} == HEAD" in r.stdout
    assert "PASS: /.build-meta.json build — built_at 2026-09-26T22:36:02.525Z" in r.stdout
    for rel in DATA_FILES:
        assert f"PASS: {rel} — sha256 {hashlib.sha256(DATA_FILES[rel]).hexdigest()[:12]}" in r.stdout
    assert "live-asset assertions passed" in r.stdout
    # The comments the review found false are gone.
    src = (LAUNCH_DIR / "verify_live_assets.mjs").read_text()
    assert "proves the data/ and citations/ syncs landed too" not in src
    assert "proves site/out/ was the deployed directory" not in src


def test_the_previous_production_still_live_fails(landed):
    """Finding #14's case: the verifier passed 50/50 before anything was
    uploaded or deployed, because production answered every probe."""
    root, head, meta, host, run = landed
    old = {**meta, "git_head": OLD_HEAD}
    host.routes["/.build-meta.json"] = (200, json.dumps(old).encode(), "application/json")
    r = run()
    assert r.returncode == 1, r.stdout
    assert f"FAIL: /.build-meta.json git_head — live {OLD_HEAD} != HEAD {head}" in r.stdout
    assert "live-asset assertions passed" not in r.stdout


def test_a_rebuild_of_the_same_commit_that_was_not_deployed_fails(landed):
    """A data-only refresh rebuilds at the same commit: git_head alone cannot
    tell the old deployment from the new one, the build stamp can."""
    root, head, meta, host, run = landed
    older = {**meta, "built_at": "2026-09-25T01:00:00.000Z", "built_at_ms": 1790298000000}
    host.routes["/.build-meta.json"] = (200, json.dumps(older).encode(), "application/json")
    r = run()
    assert r.returncode == 1, r.stdout
    assert "FAIL: /.build-meta.json build — live built_at 2026-09-25T01:00:00.000Z" in r.stdout


@pytest.mark.parametrize("route", [
    (404, b"", "text/plain"),
    (200, b"<html>not json</html>", "text/html"),
    (200, json.dumps({"built_at": "x"}).encode(), "application/json"),
    (200, json.dumps({"git_head": 42}).encode(), "application/json"),
])
def test_an_unreadable_live_build_meta_fails_closed(landed, route):
    root, head, meta, host, run = landed
    host.routes["/.build-meta.json"] = route
    r = run()
    assert r.returncode == 1, r.stdout
    assert "FAIL: /.build-meta.json git_head" in r.stdout


@pytest.mark.parametrize("rel", ["data/fct_budget_to_awards.parquet", "citations/citations.parquet"])
def test_a_fixed_name_object_the_sync_did_not_replace_fails(landed, rel):
    """Finding #14/#15: upload_r2.sh overwrites fixed-name objects in place,
    and a 200 from the OLD object used to pass (e.g. an R2_BUCKET override
    sent the upload elsewhere)."""
    root, head, meta, host, run = landed
    old = b"PAR1 the previous deploy's object PAR1"
    host.routes[f"/{rel}"] = (200, old, "application/octet-stream")
    r = run()
    assert r.returncode == 1, r.stdout
    assert (f"FAIL: {rel} — live sha256 {hashlib.sha256(old).hexdigest()[:12]}… ({len(old)} bytes) "
            f"!= local sha256 {hashlib.sha256(DATA_FILES[rel]).hexdigest()[:12]}…") in r.stdout


def test_a_missing_fixed_name_object_fails(landed):
    root, head, meta, host, run = landed
    del host.routes["/data/fct_program_concentration.parquet"]
    r = run()
    assert r.returncode == 1, r.stdout
    assert "FAIL: data/fct_program_concentration.parquet — HTTP 404" in r.stdout


def test_skip_site_still_compares_the_fixed_name_objects(landed):
    root, head, meta, host, run = landed
    host.routes["/data/budget_lines.parquet"] = (200, b"stale", "application/octet-stream")
    r = run("--skip-site")
    assert r.returncode == 1, r.stdout
    assert "FAIL: data/budget_lines.parquet" in r.stdout
    assert "/.build-meta.json" not in host.requests


def test_expect_head_overrides_the_checkout_head(landed):
    root, head, meta, host, run = landed
    shutil.rmtree(root / ".git")
    r = run(f"--expect-head={head}")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"PASS: /.build-meta.json git_head — {head} == HEAD" in r.stdout


def test_no_head_to_compare_is_a_setup_error_before_any_request(landed):
    root, head, meta, host, run = landed
    shutil.rmtree(root / ".git")
    r = run()
    assert r.returncode == 2, r.stdout
    assert "cannot read the checkout's HEAD" in r.stderr
    assert host.requests == []


@pytest.mark.parametrize("bad", ["f70a6af5", "zz" * 20, "HEAD"])
def test_a_malformed_expect_head_is_a_setup_error(landed, bad):
    root, head, meta, host, run = landed
    r = run(f"--expect-head={bad}")
    assert r.returncode == 2, r.stdout
    assert "--expect-head" in r.stderr
    assert host.requests == []


@pytest.mark.parametrize("mutation", ["remove", "empty"])
def test_no_local_fixed_name_objects_is_a_setup_error_before_any_request(landed, mutation):
    root, head, meta, host, run = landed
    data = root / "data" / "site" / "data"
    shutil.rmtree(data)
    if mutation == "empty":
        data.mkdir()
    r = run()
    assert r.returncode == 2, r.stdout
    assert "data/site/data" in r.stderr
    assert host.requests == []


def test_a_local_build_of_another_commit_is_a_setup_error(landed):
    """site/out/ must be the build of the HEAD being checked, or the build
    stamp compared against the live one means nothing."""
    root, head, meta, host, run = landed
    (root / "site" / "out" / ".build-meta.json").write_text(json.dumps({**meta, "git_head": OLD_HEAD}))
    r = run()
    assert r.returncode == 2, r.stdout
    assert "site/out/.build-meta.json" in r.stderr
    assert host.requests == []


# ---------------------------------------------------------------------------
# backup_r2_data.sh
# ---------------------------------------------------------------------------


@pytest.fixture()
def backup(tmp_path: Path):
    root = tmp_path / "gb"
    (root / "scripts" / "launch").mkdir(parents=True)
    shutil.copy2(LAUNCH_DIR / "backup_r2_data.sh", root / "scripts" / "launch" / "backup_r2_data.sh")
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    log = tmp_path / "rclone.log"
    listing = tmp_path / "lsf-dest.out"   # what rollback/<tag>/ lists
    listing.write_text("")
    live = tmp_path / "lsf-live.out"      # what each live prefix lists
    live.write_text("fct_budget_to_awards.parquet\ncitations.parquet\n")
    rclone = stub_bin / "rclone"
    # Records each call; `lsf` prints the canned listing for its path.
    rclone.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{log}'\n"
        "if [ \"$1\" = lsf ]; then\n"
        "  case \"$*\" in\n"
        f"    */rollback/*) cat '{listing}' ;;\n"
        f"    *) cat '{live}' ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n"
    )
    rclone.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}"}
    env.pop("R2_BUCKET", None)
    env.pop("RCLONE_REMOTE", None)

    def run(*args: str, extra_env: dict | None = None):
        r = subprocess.run(
            ["bash", str(root / "scripts" / "launch" / "backup_r2_data.sh"), *args],
            cwd=tmp_path, env={**env, **(extra_env or {})}, capture_output=True, text=True, timeout=60,
        )
        calls = log.read_text().splitlines() if log.exists() else []
        return r, calls

    run.live = live
    return run, listing


def test_backup_is_a_dry_run_by_default(backup):
    run, _ = backup
    r, calls = run("--tag=2026-09-26T230000Z")
    assert r.returncode == 0, r.stderr
    copies = [c for c in calls if c.startswith("copy ")]
    assert copies == [
        "copy --dry-run --checksum --immutable r2:govbudget-assets/data/ "
        "r2:govbudget-assets/rollback/2026-09-26T230000Z/data/",
        "copy --dry-run --checksum --immutable r2:govbudget-assets/citations/ "
        "r2:govbudget-assets/rollback/2026-09-26T230000Z/citations/",
    ]
    assert not any(c.startswith("check ") for c in calls)
    assert "DRY RUN" in r.stdout


def test_backup_live_copies_then_checks_and_prints_the_restore(backup):
    run, _ = backup
    r, calls = run("--live", "--tag=2026-09-26T230000Z",
                   extra_env={"R2_BUCKET": "other-bucket", "RCLONE_REMOTE": "r2x"})
    assert r.returncode == 0, r.stderr
    assert "copy --checksum --immutable r2x:other-bucket/data/ r2x:other-bucket/rollback/2026-09-26T230000Z/data/" in calls
    assert ("check --one-way --checksum r2x:other-bucket/citations/ "
            "r2x:other-bucket/rollback/2026-09-26T230000Z/citations/") in calls
    # every copy is followed by its check
    assert calls.index(next(c for c in calls if c.startswith("check ") and "/data/" in c)) > \
        calls.index(next(c for c in calls if c.startswith("copy ") and "/data/" in c))
    assert "rclone copy --checksum r2x:other-bucket/rollback/2026-09-26T230000Z/data/ r2x:other-bucket/data/" in r.stdout


def test_backup_refuses_a_destination_that_already_holds_objects(backup):
    """A second run after the deploy would overwrite the rollback copy with
    the NEW objects; the destination must be empty."""
    run, listing = backup
    listing.write_text("fct_budget_to_awards.parquet\n")
    r, calls = run("--live", "--tag=2026-09-26T230000Z")
    assert r.returncode == 1
    assert "already holds objects" in r.stderr
    assert not any(c.startswith("copy ") for c in calls)


def test_backup_refuses_an_empty_live_prefix(backup):
    """An empty (or wrong) bucket would leave a rollback copy that restores
    nothing, and the check after it would pass trivially."""
    run, _ = backup
    run.live.write_text("")
    r, calls = run("--live", "--tag=2026-09-26T230000Z")
    assert r.returncode == 1
    assert "lists no objects" in r.stderr
    assert not any(c.startswith("copy ") for c in calls)


def test_the_commands_the_header_documents_are_the_ones_it_runs(backup):
    run, _ = backup
    r, calls = run("--live", "--tag=T1")
    assert r.returncode == 0, r.stderr
    header = (LAUNCH_DIR / "backup_r2_data.sh").read_text()
    for c in calls:
        documented = f"rclone {c}".replace("T1", "<tag>")
        assert documented in header, f"{documented!r} is run but not documented in the header"


@pytest.mark.parametrize("tag", ["../data", "a/b", "", "x y", ".."])
def test_backup_refuses_an_unsafe_tag(backup, tag):
    run, _ = backup
    r, calls = run(f"--tag={tag}")
    assert r.returncode == 1
    assert calls == []


def test_backup_default_tag_is_a_utc_timestamp(backup):
    run, _ = backup
    r, calls = run()
    assert r.returncode == 0, r.stderr
    copy = next(c for c in calls if c.startswith("copy "))
    import re
    assert re.search(r"rollback/\d{4}-\d{2}-\d{2}T\d{6}Z/data/$", copy), copy
