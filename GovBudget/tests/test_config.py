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

    `RAW_DOCS_DIR` is the one that bit (doc 459, 2026-09-12): the four
    `jbook_documents.file_path` writers all start from it, so resolving it here
    makes them canonical by construction. Its siblings are resolved for the same
    reason and pinned here so a new `DATA_DIR / "…"` constant does not quietly
    re-open the hole.
    """
    for name in ("RAW_DIR", "PARQUET_DIR", "RAW_DOCS_DIR", "SITE_DIR", "DUCKDB_PATH"):
        p = getattr(config, name)
        assert p.is_absolute(), name
        assert p == p.resolve(), f"{name} is not symlink-resolved: {p}"
        assert "/.claude/worktrees/" not in str(p), f"{name} names a worktree view: {p}"


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
