"""The link and scope loaders write to the database the exporter reads.

export_site reads Postgres through `config.PG_DSN`, which honours
GOVBUDGET_PG_DSN (and the gitignored .env). Four operator scripts hard-coded
`postgresql://localhost/govbudget` instead, so with the variable set a loader
wrote its rows into one database while the page was exported from another
(Task 26 fix wave). Each import runs in a subprocess so the variable reaches
the module's import-time constant without reloading `govbudget.config` in
this process.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = "postgresql://localhost/govbudget_dsn_probe"


@pytest.mark.parametrize("module", [
    "load_announcement_scope",
    "load_announcement_links",
    "derive_ap_links",
    "load_award_adjudications",
])
def test_the_loader_writes_where_the_exporter_reads(module):
    code = (
        "import sys; sys.path.insert(0, 'scripts'); "
        f"import {module} as m; from govbudget import config; "
        "print(m.DSN); print(config.PG_DSN)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT, env={**os.environ, "GOVBUDGET_PG_DSN": PROBE},
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert out[-2:] == [PROBE, PROBE], out
