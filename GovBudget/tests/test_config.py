from govbudget import config


def test_paths_and_constants():
    assert config.DATA_DIR.name == "data"
    # `.resolve()`d, not just joined: in a git worktree `data/parquet` is a
    # symlink into the main checkout's lake, and a path that names the worktree
    # view dies with the worktree. Outside a worktree the two are the same path.
    assert config.PARQUET_DIR == (config.DATA_DIR / "parquet").resolve()
    assert config.DOD_TOPTIER_CODE == "097"
    assert config.FY_START == 2017
    assert "contracts" in config.REQUIRED_COLUMNS
    assert config.DATA_DIR.is_absolute()


def test_lake_dirs_are_symlink_resolved():
    """Every lake entry a writer builds paths from is canonical at the root.

    `RAW_DOCS_DIR` is the one that bit (doc 459, 2026-09-12): THREE of the four
    `jbook_documents.file_path` writers start from it, so resolving it here
    makes those three canonical by construction. The fourth,
    `service_fetch.register_local_documents`, starts from the operator's drop
    dir — an argument, not a constant — which is why `lake_path` stays at each
    writer as well. Its siblings are resolved for the same reason.

    This case names the five lake constants explicitly, so dropping one from
    `_lake_path` is a red test that says WHICH. The generic sweep below is the
    other half: it catches a NEW `DATA_DIR / "…"` constant nobody listed here.
    """
    for name in ("RAW_DIR", "PARQUET_DIR", "RAW_DOCS_DIR", "SITE_DIR", "DUCKDB_PATH"):
        p = getattr(config, name)
        assert p.is_absolute(), name
        assert p == p.resolve(), f"{name} is not symlink-resolved: {p}"
        assert "/.claude/worktrees/" not in str(p), f"{name} names a worktree view: {p}"


def test_every_data_dir_path_constant_is_resolved():
    """No unlisted lake constant, present or future.

    LAUNCH.md claims a new `DATA_DIR / "…"` constant that skips `_lake_path`
    is caught automatically. Before this case nothing swept: the test above
    checks the five constants someone remembered to name, which is the same
    shape of hole as the `file_path` writer census (round 2 found the fourth
    writer by hand). This walks `dir(config)` instead, so a constant added
    tomorrow is inside the check the day it is added.

    `p == p.resolve()` is the whole assertion, and it has teeth exactly where
    the defect lives — inside a git worktree, where the lake entries under
    `data/` are symlinks into the main checkout. `MANIFEST_PATH` and
    `RESEARCH_DIR` are deliberately worktree-LOCAL (see `config._lake_path`)
    and pass because they are real files there, not symlinks; if either is
    ever symlinked into the lake, this case fails and that is the intended
    conversation, not a false alarm.

    The sweep is over EVERY `Path` constant, not only those under `DATA_DIR`:
    in a worktree a resolved lake constant points into the MAIN checkout, so
    `DATA_DIR in p.parents` is false for exactly the five constants this
    exists to protect. Filtering on it would have made the case vacuous in
    the one environment where it bites — the same shape as the defect.
    """
    from pathlib import Path

    from govbudget import config

    checked = []
    for name in dir(config):
        if name.startswith("__"):
            continue
        value = getattr(config, name)
        if not isinstance(value, Path):
            continue
        checked.append(name)
        assert value.is_absolute(), f"{name} is not absolute: {value}"
        assert value == value.resolve(), (
            f"config.{name} = {value} is not symlink-resolved. Build it with"
            " config._lake_path(DATA_DIR, ...) if it names a lake entry; if it"
            " is deliberately worktree-local, it must still be a real path"
        )
    # Non-vacuity: the constants this exists to protect must be in the sweep,
    # and so must the two deliberate worktree-local ones.
    assert {"RAW_DIR", "PARQUET_DIR", "RAW_DOCS_DIR", "SITE_DIR", "DUCKDB_PATH",
            "MANIFEST_PATH", "RESEARCH_DIR", "DATA_DIR"} <= set(checked), checked


def test_site_constants():
    from govbudget import config

    assert config.SITE_DIR == (config.DATA_DIR / "site").resolve()
    assert config.PDF_BASE_URL  # non-empty; env-overridable


def test_research_dir_defined_and_absolute():
    from govbudget import config
    from pathlib import Path

    assert hasattr(config, "RESEARCH_DIR"), "RESEARCH_DIR must be defined in config"
    assert Path(config.RESEARCH_DIR).is_absolute(), "RESEARCH_DIR must be an absolute path"
    # Must end with data/research (ROOT-relative, not DATA_DIR-relative)
    rdir = str(config.RESEARCH_DIR)
    assert rdir.endswith("data/research") or rdir.endswith("data\\research"), \
        f"RESEARCH_DIR should be ROOT/data/research, got: {rdir}"


def test_load_env_file(tmp_path, monkeypatch):
    from govbudget.config import _load_env_file

    env = tmp_path / ".env"
    env.write_text(
        "# comment line\n"
        "\n"
        "ANTHROPIC_API_KEY=sk-ant-test-123\n"
        'QUOTED_VALUE="hello world"\n'
        "ALREADY_SET=from-file\n"
        "not a valid line\n"
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("QUOTED_VALUE", raising=False)
    monkeypatch.setenv("ALREADY_SET", "from-environment")

    _load_env_file(env)

    import os

    assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-test-123"
    assert os.environ["QUOTED_VALUE"] == "hello world"
    # real environment always wins — never overridden by the file
    assert os.environ["ALREADY_SET"] == "from-environment"


def test_load_env_file_missing_is_noop(tmp_path):
    from govbudget.config import _load_env_file

    _load_env_file(tmp_path / "does-not-exist.env")  # must not raise
