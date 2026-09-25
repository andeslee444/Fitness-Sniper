"""Offline tests for the deploy-path guards (integration review 2026-09-25).

1. deploy.sh provenance guard (finding #18): refuses unless
   site/out/.build-meta.json git_head == HEAD of the checkout the script lives
   in, no tracked file under that checkout is modified, and no untracked,
   non-ignored file sits under the build inputs (site/src, site/scripts,
   site/public, src, dbt, data-seeds, migrations — review round 2,
   2026-09-25); the one tracked build output (site/public/llms.txt) is exempt
   only when byte-identical to site/out/llms.txt. The OK line states exactly
   those three checks, never "a build of HEAD". Exercised with --dry-run
   --skip-r2 in a throwaway git repo, with a `vercel` stub on PATH that fails
   if it is ever invoked.

2. verify_live_assets.mjs receipt probes (finding #19): the receipt shard set
   is read before any request, and the setup errors (no shards, a part whose
   hosted_pdf_url cannot be probed) exit 2 without touching the network.

3. lighthouserc.cjs (finding #20): reports go to the local filesystem, never
   to temporary public storage.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
LAUNCH_DIR = REPO_ROOT / "scripts" / "launch"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("node") is None or shutil.which("bash") is None,
    reason="needs git, node and bash",
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


@pytest.fixture()
def checkout(tmp_path: Path):
    """A git repo whose project dir `proj/` holds a copy of deploy.sh and a site/out build."""
    repo = tmp_path / "repo"
    proj = repo / "proj"
    (proj / "scripts" / "launch").mkdir(parents=True)
    shutil.copy2(LAUNCH_DIR / "deploy.sh", proj / "scripts" / "launch" / "deploy.sh")
    (proj / "site" / "public").mkdir(parents=True)
    (proj / "site" / "public" / "llms.txt").write_text("llms v1\n")
    (proj / "README").write_text("tracked\n")
    # Mirrors GovBudget/.gitignore: data/site/ is ignored, data/research/ is
    # NOT (verify-phase5 writes its eval runs there, untracked).
    (proj / ".gitignore").write_text("site/out/\ndata/site/\n")
    (repo / "SIBLING").write_text("another project's tracked file\n")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    out = proj / "site" / "out"
    out.mkdir()
    (out / "index.html").write_text("<html></html>\n")
    (out / "vercel.json").write_text("{}\n")
    (out / "llms.txt").write_text("llms v1\n")
    (out / ".build-meta.json").write_text(json.dumps({"git_head": _git(repo, "rev-parse", "HEAD")}))

    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    vercel = stub_bin / "vercel"
    vercel.write_text("#!/bin/sh\necho 'vercel stub must never run in these tests' >&2\nexit 99\n")
    vercel.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}"}

    def run():
        # cwd is deliberately NOT the checkout: the script must locate it itself.
        return subprocess.run(
            ["bash", str(proj / "scripts" / "launch" / "deploy.sh"), "--dry-run", "--skip-r2"],
            cwd=tmp_path, env=env, capture_output=True, text=True,
        )

    return repo, proj, run


def test_clean_build_of_head_passes(checkout):
    repo, proj, run = checkout
    (proj / "untracked.txt").write_text("untracked files outside the build inputs are fine\n")
    (repo / "SIBLING").write_text("modified outside the project dir\n")
    r = run()
    assert r.returncode == 0, r.stderr
    head = _git(repo, "rev-parse", "HEAD")
    assert f"site/out built:  {head}" in r.stdout
    assert f"checkout HEAD:   {head}" in r.stdout
    assert "untracked inputs: none" in r.stdout
    # The OK line says what was checked, and only that.
    assert ("provenance:      OK — git_head matches HEAD; no tracked changes; "
            "no untracked build inputs") in r.stdout
    assert "is a build of HEAD" not in r.stdout
    assert "not checked: whether the tree was clean when site/out/ was built" in r.stdout
    assert "Dry run complete" in r.stdout


@pytest.mark.parametrize("rel", [
    "site/src/components/new-panel.tsx",   # the finding's case: imported, never git-added
    "site/scripts/gates/new-leg.mjs",
    "site/public/new-icon.svg",
    "src/govbudget/new_module.py",
    "dbt/models/marts/new_mart.sql",
    "data-seeds/new_seed.csv",
    "migrations/099_new.sql",
    "data/research/dossiers-raw/30-OSD.json",  # final check round 2: the exporter globs it
])
def test_untracked_build_input_is_refused(checkout, rel):
    """Review round 2 (2026-09-25): an untracked, non-ignored file under the
    build inputs is compiled into site/out/ but is not in HEAD — the deploy
    passed with `--untracked-files=no` and HEAD could not rebuild it."""
    repo, proj, run = checkout
    path = proj / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("new, never git-added\n")
    r = run()
    assert r.returncode == 2, r.stdout
    assert "untracked inputs: 1 path(s)" in r.stdout
    assert f"?? proj/{rel}" in r.stdout  # repo-top path, as git status prints
    assert "REFUSING TO DEPLOY: untracked files sit under the build inputs" in r.stderr
    assert "--dry-run enforces this too" in r.stderr
    assert "provenance:      OK" not in r.stdout
    assert "Dry run complete" not in r.stdout


def test_untracked_files_outside_the_build_inputs_pass(checkout):
    """data/research/eval-runs/ (verify-phase5's eval runs), tests/ and the
    project root are not build inputs; ignored files under an input path are
    not either. The rest of data/research/ IS an input (dossiers-raw)."""
    repo, proj, run = checkout
    for rel in ("data/research/eval-runs/eval-20260925T000000Z.json",
                "tests/test_new.py", "notes.txt"):
        (proj / rel).parent.mkdir(parents=True, exist_ok=True)
        (proj / rel).write_text("{}\n")
    (proj / "site" / ".gitignore").write_text("public/json/\n")
    _git(repo, "add", "proj/site/.gitignore")
    _git(repo, "commit", "-qm", "ignore generated json")
    (proj / "site" / "out" / ".build-meta.json").write_text(
        json.dumps({"git_head": _git(repo, "rev-parse", "HEAD")}))
    (proj / "site" / "public" / "json").mkdir(parents=True)
    (proj / "site" / "public" / "json" / "generated.json").write_text("{}\n")
    r = run()
    assert r.returncode == 0, r.stderr
    assert "untracked inputs: none" in r.stdout
    assert "provenance:      OK" in r.stdout


def test_build_of_another_commit_is_refused_even_in_dry_run(checkout):
    repo, proj, run = checkout
    (proj / "site" / "out" / ".build-meta.json").write_text(json.dumps({"git_head": "42eed1e4" + "0" * 32}))
    r = run()
    assert r.returncode == 2
    assert "REFUSING TO DEPLOY: site/out/ was built from 42eed1e4" in r.stderr
    assert "--dry-run enforces this too" in r.stderr
    assert "Dry run complete" not in r.stdout


@pytest.mark.parametrize("meta", [None, "{not json", json.dumps({"git_head": "unknown"}), json.dumps({})])
def test_missing_or_unusable_build_meta_is_refused(checkout, meta):
    repo, proj, run = checkout
    path = proj / "site" / "out" / ".build-meta.json"
    if meta is None:
        path.unlink()
    else:
        path.write_text(meta)
    r = run()
    assert r.returncode == 2
    assert r.stderr.startswith("ERROR:")


@pytest.mark.parametrize("staged", [False, True])
def test_tracked_modification_is_refused(checkout, staged):
    repo, proj, run = checkout
    (proj / "README").write_text("edited\n")
    if staged:
        _git(repo, "add", "proj/README")
    r = run()
    assert r.returncode == 2
    assert "proj/README" in r.stdout
    assert "REFUSING TO DEPLOY: tracked files" in r.stderr


def test_llms_txt_rewritten_by_the_build_is_exempt(checkout):
    repo, proj, run = checkout
    (proj / "site" / "public" / "llms.txt").write_text("llms v2 (new counts)\n")
    (proj / "site" / "out" / "llms.txt").write_text("llms v2 (new counts)\n")
    r = run()
    assert r.returncode == 0, r.stderr
    assert "exempt:          site/public/llms.txt" in r.stdout


@pytest.mark.parametrize("mutation", ["hand-edit", "delete"])
def test_llms_txt_not_matching_the_build_is_refused(checkout, mutation):
    repo, proj, run = checkout
    src = proj / "site" / "public" / "llms.txt"
    if mutation == "delete":
        src.unlink()
    else:
        src.write_text("edited after the build\n")
    r = run()
    assert r.returncode == 2
    assert "site/public/llms.txt" in r.stdout


def test_exemption_does_not_hide_other_changes(checkout):
    repo, proj, run = checkout
    (proj / "site" / "public" / "llms.txt").write_text("llms v2\n")
    (proj / "site" / "out" / "llms.txt").write_text("llms v2\n")
    (proj / "README").write_text("edited\n")
    r = run()
    assert r.returncode == 2
    assert "proj/README" in r.stdout


# ---------------------------------------------------------------------------
# verify_live_assets.mjs — receipt probe setup errors (no network reached)
# ---------------------------------------------------------------------------

SHA = "a" * 64


@pytest.fixture()
def asset_tree(tmp_path: Path):
    root = tmp_path / "gb"
    (root / "scripts" / "launch").mkdir(parents=True)
    shutil.copy2(LAUNCH_DIR / "verify_live_assets.mjs", root / "scripts" / "launch" / "verify_live_assets.mjs")
    (root / "data" / "site" / "pdfs").mkdir(parents=True)
    (root / "data" / "site" / "pdfs" / f"{SHA}.pdf").write_bytes(b"%PDF-1.7\n")
    (root / "data" / "site" / "json").mkdir(parents=True)
    (root / "data" / "site" / "json" / "citations.json").write_text(
        json.dumps({"x": {"hosted_pdf_url": f"/pdfs/{SHA}.pdf"}})
    )
    (root / "site" / "public").mkdir(parents=True)
    # An unroutable host: if a probe were ever sent, it would fail, not pass.
    (root / "site" / "public" / "config.json").write_text(json.dumps({"assetBaseUrl": "http://127.0.0.1:9"}))

    def run(*args: str):
        return subprocess.run(
            ["node", str(root / "scripts" / "launch" / "verify_live_assets.mjs"), "--skip-site", *args],
            capture_output=True, text=True, timeout=60,
        )

    return root, run


def test_no_receipt_shards_is_a_setup_error(asset_tree):
    root, run = asset_tree
    r = run()
    assert r.returncode == 2
    assert "no receipt shards" in r.stderr
    assert "PASS" not in r.stdout and "FAIL" not in r.stdout  # nothing was requested


def test_unprobeable_receipt_part_is_a_setup_error(asset_tree):
    root, run = asset_tree
    v2 = root / "data" / "site" / "json" / "budget-pdf-receipts" / "v2"
    v2.mkdir(parents=True)
    (v2 / "abc.json").write_text(json.dumps({"abc0000000000000": {"parts": [{"hosted_pdf_url": "https://elsewhere/x.pdf"}]}}))
    r = run()
    assert r.returncode == 2
    assert "cannot probe it" in r.stderr
    assert "PASS" not in r.stdout and "FAIL" not in r.stdout


def test_shards_without_any_book_are_a_setup_error(asset_tree):
    root, run = asset_tree
    v2 = root / "data" / "site" / "json" / "budget-pdf-receipts" / "v2"
    v2.mkdir(parents=True)
    (v2 / "000.json").write_text("{}\n")
    r = run()
    assert r.returncode == 2
    assert "name no budget book" in r.stderr


# ---------------------------------------------------------------------------
# lighthouserc.cjs
# ---------------------------------------------------------------------------


def test_lighthouse_reports_stay_on_the_local_filesystem():
    cfg = json.loads(subprocess.run(
        ["node", "-e", "process.stdout.write(JSON.stringify(require(process.argv[1]).ci.upload))",
         str(REPO_ROOT / "site" / "lighthouserc.cjs")],
        check=True, capture_output=True, text=True,
    ).stdout)
    assert cfg["target"] == "filesystem"
    # Under site/.lighthouseci/, which site/.gitignore ignores.
    assert os.path.normpath(cfg["outputDir"]).startswith(".lighthouseci" + os.sep)
