"""R-DEC-DEPLOYSAFE-b (final-review rulings, 2026-09-27): deploy.sh makes the
rollback copy itself.

backup_r2_data.sh (R-DEC-DEPLOYSAFE, #177's own fix) copies the live
fixed-name R2 prefixes (data/, citations/) aside to rollback/<tag>/ before an
upload overwrites them. Until this ruling it was a manual step that deploy.sh
neither called nor checked for, so skipping it left every check green while
the previous deploy's objects were overwritten with no copy (the final
review's check round, deploy.sh finding). Now deploy.sh:

  - runs `backup_r2_data.sh --live --tag=<tag>` before `upload_r2.sh --live`;
  - refuses to continue (nothing uploaded, nothing deployed) if it fails;
  - prints the tag, and names it again if a later step fails;
  - under --dry-run runs the backup's own dry run (it lists the live
    prefixes and copies nothing) and uploads and deploys nothing;
  - under --skip-r2 makes no copy: no R2 object is overwritten.

Exercised in a throwaway git checkout with stubs on PATH (`rclone`,
`vercel`) and in the checkout (`upload_r2.sh`, `verify_live_assets.mjs`),
all appending to one call log, so the ORDER of the steps is asserted.
Nothing here reaches the network.
"""
from __future__ import annotations

import json
import os
import re
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

TAG_RE = re.compile(r"rollback tag:\s+(\d{4}-\d{2}-\d{2}T\d{6}Z)\b")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


@pytest.fixture()
def deploy(tmp_path: Path):
    """A clean checkout at HEAD with a build of HEAD, the real deploy.sh and
    backup_r2_data.sh, and recording stubs for everything that would touch
    R2, Vercel or the network."""
    repo = tmp_path / "repo"
    proj = repo / "proj"
    launch = proj / "scripts" / "launch"
    launch.mkdir(parents=True)
    shutil.copy2(LAUNCH_DIR / "deploy.sh", launch / "deploy.sh")
    shutil.copy2(LAUNCH_DIR / "backup_r2_data.sh", launch / "backup_r2_data.sh")
    log = tmp_path / "calls.log"
    upload = launch / "upload_r2.sh"
    upload.write_text(
        "#!/bin/sh\n"
        "printf 'upload_r2 %s bucket=%s\\n' \"$*\" \"${R2_BUCKET:-}\" >> \"$CALL_LOG\"\n"
        "exit \"${UPLOAD_EXIT:-0}\"\n"
    )
    upload.chmod(0o755)
    (launch / "verify_live_assets.mjs").write_text(
        "import fs from 'fs';\n"
        "fs.appendFileSync(process.env.CALL_LOG, 'verify ' + process.argv.slice(2).join(' ') + '\\n');\n"
    )
    (proj / "site" / "public").mkdir(parents=True)
    (proj / "site" / "public" / "llms.txt").write_text("llms v1\n")
    (proj / ".gitignore").write_text("site/out/\ndata/site/\n")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    out = proj / "site" / "out"
    out.mkdir()
    (out / "index.html").write_text("<html></html>\n")
    (out / "vercel.json").write_text("{}\n")
    (out / "llms.txt").write_text("llms v1\n")
    (out / ".build-meta.json").write_text(json.dumps({"git_head": _git(repo, "rev-parse", "HEAD")}))
    (proj / "data" / "site" / "pdfs").mkdir(parents=True)
    (proj / "data" / "site" / "pdfs" / f"{'a' * 64}.pdf").write_bytes(b"%PDF-1.7\n")

    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    dest_listing = tmp_path / "lsf-dest.out"  # what rollback/<tag>/ lists
    dest_listing.write_text("")
    live_listing = tmp_path / "lsf-live.out"  # what each live prefix lists
    live_listing.write_text("fct_budget_to_awards.parquet\ncitations.parquet\n")
    rclone = stub_bin / "rclone"
    # Records each call; `lsf` prints the canned listing for its path;
    # RCLONE_FAIL=<subcommand> makes that subcommand exit 1.
    rclone.write_text(
        "#!/bin/sh\n"
        "printf 'rclone %s\\n' \"$*\" >> \"$CALL_LOG\"\n"
        "if [ -n \"$RCLONE_FAIL\" ] && [ \"$1\" = \"$RCLONE_FAIL\" ]; then\n"
        "  echo \"rclone stub: $1 failed\" >&2; exit 1\n"
        "fi\n"
        "if [ \"$1\" = lsf ]; then\n"
        "  case \"$*\" in\n"
        f"    */rollback/*) cat '{dest_listing}' ;;\n"
        f"    *) cat '{live_listing}' ;;\n"
        "  esac\n"
        "fi\n"
        "exit 0\n"
    )
    rclone.chmod(0o755)
    vercel = stub_bin / "vercel"
    vercel.write_text(
        "#!/bin/sh\n"
        "printf 'vercel %s\\n' \"$*\" >> \"$CALL_LOG\"\n"
        "exit 0\n"
    )
    vercel.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}", "CALL_LOG": str(log)}
    for var in ("R2_BUCKET", "RCLONE_REMOTE", "RCLONE_FAIL", "UPLOAD_EXIT"):
        env.pop(var, None)

    def run(*args: str, extra_env: dict | None = None):
        r = subprocess.run(
            ["bash", str(launch / "deploy.sh"), *args],
            cwd=tmp_path, env={**env, **(extra_env or {})}, capture_output=True, text=True, timeout=120,
        )
        calls = log.read_text().splitlines() if log.exists() else []
        return r, calls

    run.live_listing = live_listing
    run.dest_listing = dest_listing
    run.launch = launch
    return run


def _tag(stdout: str) -> str:
    m = TAG_RE.search(stdout)
    assert m, f"deploy.sh printed no rollback tag:\n{stdout}"
    return m.group(1)


def _kinds(calls: list[str]) -> list[str]:
    """The call log as step kinds, in order: rclone subcommand, or the stub name."""
    out = []
    for c in calls:
        word, _, rest = c.partition(" ")
        out.append(f"rclone {rest.split(' ', 1)[0]}" if word == "rclone" else word)
    return out


def test_a_deploy_copies_the_live_prefixes_aside_before_the_upload(deploy):
    r, calls = deploy()
    assert r.returncode == 0, r.stdout + r.stderr
    tag = _tag(r.stdout)
    # The rollback copy, in full, then the upload, then Vercel, then the check.
    assert _kinds(calls) == [
        "rclone lsf", "rclone lsf", "rclone lsf",
        "rclone copy", "rclone check", "rclone copy", "rclone check",
        "upload_r2", "vercel", "verify",
    ], calls
    assert (f"rclone copy --checksum --immutable r2:govbudget-assets/data/ "
            f"r2:govbudget-assets/rollback/{tag}/data/") in calls
    assert (f"rclone copy --checksum --immutable r2:govbudget-assets/citations/ "
            f"r2:govbudget-assets/rollback/{tag}/citations/") in calls
    assert not any("--dry-run" in c for c in calls)
    assert "upload_r2 --live bucket=" in calls
    # The tag is printed with where the copy went, for the ledger.
    assert f"r2:govbudget-assets/rollback/{tag}/" in r.stdout
    assert f"Record the rollback tag {tag}" in r.stdout
    assert "Deploy complete" in r.stdout


def test_the_copy_goes_to_the_bucket_the_upload_writes(deploy):
    """R2_BUCKET / RCLONE_REMOTE reach the backup as they reach upload_r2.sh:
    a copy of another bucket would restore nothing."""
    r, calls = deploy(extra_env={"R2_BUCKET": "other-bucket", "RCLONE_REMOTE": "r2x"})
    assert r.returncode == 0, r.stdout + r.stderr
    tag = _tag(r.stdout)
    assert (f"rclone copy --checksum --immutable r2x:other-bucket/data/ "
            f"r2x:other-bucket/rollback/{tag}/data/") in calls
    assert "upload_r2 --live bucket=other-bucket" in calls
    assert f"r2x:other-bucket/rollback/{tag}/" in r.stdout


@pytest.mark.parametrize("failure", ["copy", "check", "lsf"])
def test_a_failed_copy_stops_the_deploy_before_anything_is_uploaded(deploy, failure):
    r, calls = deploy(extra_env={"RCLONE_FAIL": failure})
    assert r.returncode == 1, r.stdout + r.stderr
    kinds = _kinds(calls)
    assert "upload_r2" not in kinds and "vercel" not in kinds and "verify" not in kinds, calls
    assert "REFUSING TO CONTINUE: the rollback copy" in r.stderr
    assert "Nothing was uploaded or deployed" in r.stderr
    assert _tag(r.stdout) in r.stderr
    assert "Deploy complete" not in r.stdout


@pytest.mark.parametrize("setup", ["empty_live_prefix", "destination_taken"])
def test_a_refused_copy_stops_the_deploy_before_anything_is_uploaded(deploy, setup):
    """The backup's own refusals (an empty live prefix: wrong bucket; a
    destination that already holds objects) stop the deploy too."""
    if setup == "empty_live_prefix":
        deploy.live_listing.write_text("")
    else:
        deploy.dest_listing.write_text("fct_budget_to_awards.parquet\n")
    r, calls = deploy()
    assert r.returncode == 1, r.stdout + r.stderr
    kinds = _kinds(calls)
    assert "rclone copy" not in kinds, calls
    assert "upload_r2" not in kinds and "vercel" not in kinds and "verify" not in kinds, calls
    assert "REFUSING TO CONTINUE: the rollback copy" in r.stderr


def test_a_step_that_fails_after_the_copy_names_the_rollback_tag(deploy):
    """If the upload (or Vercel) fails after the copy, the tag that holds the
    objects R2 served BEFORE this run is printed again: a re-run copies what R2
    serves then, which may already be this run's upload."""
    r, calls = deploy(extra_env={"UPLOAD_EXIT": "1"})
    assert r.returncode == 1, r.stdout + r.stderr
    tag = _tag(r.stdout)
    kinds = _kinds(calls)
    assert kinds.index("upload_r2") > kinds.index("rclone check")
    assert "vercel" not in kinds and "verify" not in kinds
    assert f"r2:govbudget-assets/rollback/{tag}/" in r.stderr
    assert "holds what R2 served before this run" in r.stderr


def test_a_dry_run_runs_the_backups_own_dry_run_and_changes_nothing(deploy):
    r, calls = deploy("--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    tag = _tag(r.stdout)
    kinds = _kinds(calls)
    # Listings and `copy --dry-run` only: no real copy, no check, no upload,
    # no Vercel, no live check.
    assert kinds == ["rclone lsf", "rclone lsf", "rclone lsf", "rclone copy", "rclone copy"], calls
    assert all("--dry-run" in c for c in calls if c.startswith("rclone copy")), calls
    assert (f"rclone copy --dry-run --checksum --immutable r2:govbudget-assets/data/ "
            f"r2:govbudget-assets/rollback/{tag}/data/") in calls
    # What it would back up, and what a real deploy runs.
    assert "COPY  r2:govbudget-assets/data/" in r.stdout
    assert "backup_r2_data.sh --live" in r.stdout
    assert "Dry run complete" in r.stdout


def test_a_dry_run_stops_where_a_real_deploy_would(deploy):
    deploy.live_listing.write_text("")
    r, calls = deploy("--dry-run")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "REFUSING TO CONTINUE: the rollback copy" in r.stderr
    assert "a real deploy would stop here" in r.stderr
    assert "Dry run complete" not in r.stdout


def test_skip_r2_makes_no_copy_because_it_overwrites_nothing(deploy):
    r, calls = deploy("--skip-r2")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not any(c.startswith("rclone ") for c in calls), calls
    assert _kinds(calls) == ["vercel", "verify"], calls
    assert "rollback copy SKIPPED (--skip-r2" in r.stdout


def test_a_missing_backup_script_fails_preflight_before_anything_runs(deploy):
    """Committed without the script (so the provenance guard is clean and the
    build is of HEAD): preflight still refuses, before any rclone call."""
    proj = deploy.launch.parent.parent
    repo = proj.parent
    _git(repo, "rm", "-q", "proj/scripts/launch/backup_r2_data.sh")
    _git(repo, "commit", "-qm", "drop the backup script")
    (proj / "site" / "out" / ".build-meta.json").write_text(
        json.dumps({"git_head": _git(repo, "rev-parse", "HEAD")}))
    r, calls = deploy()
    assert r.returncode == 2, r.stdout + r.stderr
    assert "provenance:      OK" in r.stdout  # the guard passed; this check refused
    assert "backup_r2_data.sh not found" in r.stderr
    assert calls == []


def test_a_deleted_backup_script_is_refused_by_the_provenance_guard_too(deploy):
    """Deleted but not committed: a tracked change, refused before the R2
    checks are reached."""
    (deploy.launch / "backup_r2_data.sh").unlink()
    r, calls = deploy()
    assert r.returncode == 2, r.stdout + r.stderr
    assert "REFUSING TO DEPLOY: tracked files" in r.stderr
    assert calls == []


def test_the_headers_say_deploy_sh_makes_the_copy():
    """The backup header said "deploy.sh does not call it"; both headers now
    say what deploy.sh does."""
    backup = (LAUNCH_DIR / "backup_r2_data.sh").read_text()
    assert "deploy.sh does not call it" not in backup
    assert "deploy.sh runs it" in backup
    header = "\n".join(
        line for line in (LAUNCH_DIR / "deploy.sh").read_text().splitlines() if line.startswith("#")
    )
    assert "backup_r2_data.sh --live" in header
    assert "R-DEC-DEPLOYSAFE-b" in header
