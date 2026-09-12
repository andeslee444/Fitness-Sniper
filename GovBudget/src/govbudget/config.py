import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_env_file(path: Path) -> None:
    """Populate os.environ from a KEY=VALUE .env file (gitignored).

    Real environment variables always win — a key already present in
    os.environ is never overridden. Blank lines and '#' comments are
    skipped; values may be wrapped in single or double quotes.
    """
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(ROOT / ".env")

DATA_DIR = Path(os.environ.get("GOVBUDGET_DATA", ROOT / "data")).resolve()


def _lake_path(base: Path, *parts: str) -> Path:
    """A path inside the shared data lake, with symlinks collapsed.

    `DATA_DIR.resolve()` is not enough in a git worktree: `data/` there is a
    REAL directory holding worktree-local files, and it is the individual lake
    entries under it (`raw_docs`, `raw`, `parquet`, `duckdb`, `site`) that are
    symlinks into the main checkout's lake. So every path built from an
    un-resolved `DATA_DIR / "raw_docs"` carries the worktree prefix, and any
    such path that gets RECORDED — `jbook_documents.file_path` is the one that
    bit, doc 459 on 2026-09-12 — names a view that disappears with the
    worktree, breaking `export_site`'s copy loop and every citation behind it.
    Resolving here makes the constant canonical, so all four `file_path`
    writers are canonical by construction rather than by remembering.

    `Path.resolve()` is a no-op for a path with no symlink component (the main
    checkout) and does not require the path to exist, so this changes nothing
    outside a worktree. `RESEARCH_DIR` and `MANIFEST_PATH` are deliberately NOT
    routed through it: they are worktree-local files by design, not lake
    entries, and resolving them would be a no-op today but a silent relocation
    the day someone symlinks them.
    """
    return base.joinpath(*parts).resolve()


RAW_DIR = _lake_path(DATA_DIR, "raw")
PARQUET_DIR = _lake_path(DATA_DIR, "parquet")
DUCKDB_PATH = _lake_path(DATA_DIR, "duckdb", "govbudget.duckdb")
MANIFEST_PATH = DATA_DIR / "manifest.jsonl"

PG_DSN = os.environ.get("GOVBUDGET_PG_DSN", "postgresql://localhost/govbudget")
RAW_DOCS_DIR = _lake_path(DATA_DIR, "raw_docs")
RESEARCH_DIR = ROOT / "data" / "research"
JBOOK_FY = 2026

# Phase 5B site export
SITE_DIR = _lake_path(DATA_DIR, "site")
# Base URL where sha-named PDFs are hosted (R2). Relative default for local dev.
PDF_BASE_URL = os.environ.get("GOVBUDGET_PDF_BASE_URL", "/pdfs")

USASPENDING_API = "https://api.usaspending.gov/api/v2"
FISCALDATA_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"

DOD_TOPTIER_CODE = "097"
FY_START = 2017
FY_END = 2026
MIN_FREE_GB = 25

# Columns that must exist in converted Parquet or the load is rejected.
REQUIRED_COLUMNS: dict[str, set[str]] = {
    "contracts": {
        "contract_transaction_unique_key",
        "action_date",
        "federal_action_obligation",
        "recipient_uei",
    },
    "assistance": {
        "assistance_transaction_unique_key",
        "action_date",
        "federal_action_obligation",
        "recipient_uei",
    },
    "subawards": {
        "prime_award_unique_key",
        "subaward_amount",
        "subaward_action_date",
    },
}
