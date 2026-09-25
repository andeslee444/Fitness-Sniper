"""ROADMAP #8 — abort-without-overwrite guards on every sync-* stage.

The failure being guarded is NOT a crash. `convert_zip_to_parquet` validates
COLUMNS and then swaps the new partition over the old one unconditionally, so
an upstream that answers with a truncated archive replaces a full FY with a
half one, exits 0, and every downstream number silently shrinks. dbt,
export-site and the 24 site gates cannot see it: the numbers stay internally
consistent, they are just smaller than the truth. This is the same defect
`influence/lda.py` already guards against (_MIN_CORPUS_RETENTION, 2026-09-01);
these tests generalize it to the three USAspending datasets and Treasury MTS.

No network: every test builds its own zip / MockTransport client in tmp_path.
"""
import io
import json
import zipfile

import duckdb
import httpx
import pytest

from govbudget.convert import (
    PartitionShrinkError,
    _MIN_PARTITION_RETENTION,
    convert_zip_to_parquet,
    parquet_row_count,
)

HEADER = (
    "contract_transaction_unique_key,action_date,federal_action_obligation,"
    "recipient_uei"
)
REQUIRED = {"contract_transaction_unique_key", "action_date"}


def _rows(n, prefix="K"):
    return [f"{prefix}{i},2024-01-15,100.00,UEI{i}" for i in range(n)]


def _csv(rows):
    return HEADER + "\n" + "\n".join(rows) + "\n"


def _zip(tmp_path, name, rows, members=1):
    zip_path = tmp_path / name
    with zipfile.ZipFile(zip_path, "w") as zf:
        for i in range(members):
            zf.writestr(f"part_{i}.csv", _csv(rows))
    return zip_path


def _count(path_or_glob):
    # A dedicated connection, not duckdb.sql()'s process-global default one.
    # That default connection is shared by the whole pytest process and some
    # combination of the modules that sort before this one leaves it in an
    # aborted transaction, so every later duckdb.sql() raises
    # TransactionException. Pre-existing and not this module's to fix (it is
    # reproducible with tests/test_convert.py as the probe and none of the
    # ROADMAP #8 code loaded); production parquet_row_count() already opens its
    # own connection for the same reason, so these assertions match it.
    con = duckdb.connect()
    try:
        return con.execute(
            f"select count(*) from read_parquet('{path_or_glob}')"
        ).fetchone()[0]
    finally:
        con.close()


def _seed_partition(tmp_path, n_rows):
    """Land a real n_rows partition at parquet/contracts/fy=2024, return dirs."""
    parquet_dir = tmp_path / "parquet"
    raw_dir = tmp_path / "raw"
    convert_zip_to_parquet(
        _zip(tmp_path, "seed.zip", _rows(n_rows)),
        dataset="contracts", fiscal_year=2024,
        parquet_dir=parquet_dir, raw_dir=raw_dir, required_columns=REQUIRED,
    )
    return parquet_dir, raw_dir


# ── parquet_row_count ───────────────────────────────────────────────────────


def test_row_count_of_unreadable_parquet_is_zero_not_an_exception(tmp_path, capsys):
    junk = tmp_path / "junk.parquet"
    junk.write_bytes(b"not a parquet file")
    assert parquet_row_count(str(junk)) == 0
    assert "WARNING" in capsys.readouterr().out


def test_row_count_of_an_empty_glob_is_zero(tmp_path):
    assert parquet_row_count(f"{tmp_path}/nothing/*.parquet") == 0


# ── convert_zip_to_parquet ──────────────────────────────────────────────────


def test_convert_aborts_when_the_new_partition_shrinks(tmp_path):
    parquet_dir, raw_dir = _seed_partition(tmp_path, 100)
    shrunk = _zip(tmp_path, "shrunk.zip", _rows(50, prefix="S"))
    with pytest.raises(PartitionShrinkError) as exc:
        convert_zip_to_parquet(
            shrunk, dataset="contracts", fiscal_year=2024,
            parquet_dir=parquet_dir, raw_dir=raw_dir, required_columns=REQUIRED,
        )
    msg = str(exc.value)
    assert "50" in msg and "100" in msg
    assert "--allow-corpus-shrink" in msg


def test_abort_leaves_the_prior_partition_and_the_source_zip_intact(tmp_path):
    parquet_dir, raw_dir = _seed_partition(tmp_path, 100)
    shrunk = _zip(tmp_path, "shrunk.zip", _rows(50, prefix="S"))
    with pytest.raises(PartitionShrinkError):
        convert_zip_to_parquet(
            shrunk, dataset="contracts", fiscal_year=2024,
            parquet_dir=parquet_dir, raw_dir=raw_dir, required_columns=REQUIRED,
        )
    live = parquet_dir / "contracts" / "fy=2024"
    assert _count(f"{live}/*.parquet") == 100, "the prior partition must survive"
    assert shrunk.exists(), "the source zip must survive so the run is re-runnable"
    assert not (parquet_dir / "contracts" / "fy=2024.incoming").exists()


def test_allow_shrink_flag_permits_the_overwrite(tmp_path):
    parquet_dir, raw_dir = _seed_partition(tmp_path, 100)
    convert_zip_to_parquet(
        _zip(tmp_path, "shrunk.zip", _rows(50, prefix="S")),
        dataset="contracts", fiscal_year=2024,
        parquet_dir=parquet_dir, raw_dir=raw_dir, required_columns=REQUIRED,
        allow_shrink=True,
    )
    assert _count(f"{parquet_dir}/contracts/fy=2024/*.parquet") == 50


def test_growth_and_a_shrink_inside_the_floor_are_allowed(tmp_path):
    parquet_dir, raw_dir = _seed_partition(tmp_path, 100)
    # 90 rows = 90% retention, above the 80% floor.
    convert_zip_to_parquet(
        _zip(tmp_path, "ok.zip", _rows(90, prefix="A")),
        dataset="contracts", fiscal_year=2024,
        parquet_dir=parquet_dir, raw_dir=raw_dir, required_columns=REQUIRED,
    )
    convert_zip_to_parquet(
        _zip(tmp_path, "grow.zip", _rows(500, prefix="B")),
        dataset="contracts", fiscal_year=2024,
        parquet_dir=parquet_dir, raw_dir=raw_dir, required_columns=REQUIRED,
    )
    assert _count(f"{parquet_dir}/contracts/fy=2024/*.parquet") == 500


def test_an_empty_archive_is_a_shrink_not_a_success(tmp_path):
    """Zero CSV members => zero rows => the guard, not a silent wipe."""
    parquet_dir, raw_dir = _seed_partition(tmp_path, 100)
    empty = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty, "w") as zf:
        zf.writestr("readme.txt", "no csv members here")
    with pytest.raises(PartitionShrinkError):
        convert_zip_to_parquet(
            empty, dataset="contracts", fiscal_year=2024,
            parquet_dir=parquet_dir, raw_dir=raw_dir, required_columns=REQUIRED,
        )
    assert _count(f"{parquet_dir}/contracts/fy=2024/*.parquet") == 100


def test_floor_is_the_documented_eighty_percent():
    assert _MIN_PARTITION_RETENTION == 0.80


def test_unreadable_prior_partition_does_not_block_the_replacement(tmp_path):
    parquet_dir = tmp_path / "parquet"
    live = parquet_dir / "contracts" / "fy=2024"
    live.mkdir(parents=True)
    (live / "corrupt.parquet").write_bytes(b"junk")
    convert_zip_to_parquet(
        _zip(tmp_path, "fresh.zip", _rows(3)),
        dataset="contracts", fiscal_year=2024,
        parquet_dir=parquet_dir, raw_dir=tmp_path / "raw",
        required_columns=REQUIRED,
    )
    assert not (live / "corrupt.parquet").exists()


# ── prior-partition counting must tolerate a partially-corrupt directory ────
# (Fix round 1, item 1). Production contracts/assistance partitions ARE
# multi-member: a single glob read over `*.parquet` is all-or-nothing, so one
# junk member sitting next to a good 100-row part must not zero out the whole
# prior count and let `if prior:` skip the guard.


def test_partial_corruption_in_the_prior_partition_does_not_bypass_the_guard(tmp_path):
    """Proof-it-can-fail: one good 100-row part + one junk part must still
    total 100, so a 50-row (shrunk) fresh partition still trips the guard."""
    parquet_dir, raw_dir = _seed_partition(tmp_path, 100)
    live = parquet_dir / "contracts" / "fy=2024"
    (live / "part_999_junk.parquet").write_bytes(b"not a parquet file")
    shrunk = _zip(tmp_path, "shrunk.zip", _rows(50, prefix="S"))
    with pytest.raises(PartitionShrinkError) as exc:
        convert_zip_to_parquet(
            shrunk, dataset="contracts", fiscal_year=2024,
            parquet_dir=parquet_dir, raw_dir=raw_dir, required_columns=REQUIRED,
        )
    msg = str(exc.value)
    assert "50" in msg and "100" in msg
    # the good member and the junk member both survive the abort
    assert _count(f"{live}/part_000.parquet") == 100
    assert (live / "part_999_junk.parquet").exists()


def test_a_prior_partition_with_every_member_unreadable_still_skips_the_guard(tmp_path, capsys):
    """All-junk prior: the per-file fallback sums to 0, same ruling as a
    single wholly-unreadable prior — the swap proceeds, with a WARNING per
    skipped file."""
    parquet_dir = tmp_path / "parquet"
    live = parquet_dir / "contracts" / "fy=2024"
    live.mkdir(parents=True)
    (live / "part_000.parquet").write_bytes(b"junk one")
    (live / "part_001.parquet").write_bytes(b"junk two")
    convert_zip_to_parquet(
        _zip(tmp_path, "fresh.zip", _rows(3)),
        dataset="contracts", fiscal_year=2024,
        parquet_dir=parquet_dir, raw_dir=tmp_path / "raw",
        required_columns=REQUIRED,
    )
    assert _count(f"{parquet_dir}/contracts/fy=2024/*.parquet") == 3
    assert capsys.readouterr().out.count("WARNING") >= 2


def test_prior_partition_row_count_fallback_sums_only_the_readable_members(tmp_path):
    """The fallback helper itself: two readable members (40 + 15 rows) plus
    one junk member sums to 55, not 0 — the junk member costs only its own
    rows."""
    from govbudget.convert import _prior_partition_row_count

    live = tmp_path / "fy=2024"
    live.mkdir(parents=True)
    con = duckdb.connect()
    try:
        con.execute(
            f"copy (select * from range(40)) to '{live}/part_000.parquet' (format parquet)"
        )
        con.execute(
            f"copy (select * from range(15)) to '{live}/part_001.parquet' (format parquet)"
        )
    finally:
        con.close()
    (live / "part_002_junk.parquet").write_bytes(b"not a parquet file")
    assert _prior_partition_row_count(live) == 55


# ── sync_archive (the guard reached through the real download path) ─────────

AGENCIES = {
    "agencies": {
        "cfo_agencies": [{"toptier_agency_id": 126, "toptier_code": "097", "name": "DoD"}],
        "other_agencies": [],
    }
}


def _archive_client(n_rows, file_name):
    """MockTransport client serving list_agencies, list_monthly_files, the zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("part_0.csv", _csv(_rows(n_rows)))
    zip_bytes = buf.getvalue()

    def handler(request):
        p = request.url.path
        if p.endswith("/bulk_download/list_agencies/"):
            return httpx.Response(200, json=AGENCIES)
        if p.endswith("/bulk_download/list_monthly_files/"):
            return httpx.Response(200, json={"monthly_files": [{
                "file_name": file_name,
                "url": f"https://api.usaspending.gov/fake/{file_name}",
                "updated_date": "2026-06-07",
            }]})
        if p.endswith(".zip"):
            return httpx.Response(200, content=zip_bytes)
        return httpx.Response(404)

    return httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://api.usaspending.gov/api/v2",
    )


def _sync_archive(tmp_path, n_rows, file_name, **kw):
    from govbudget.usaspending.archive_sync import sync_archive

    with _archive_client(n_rows, file_name) as client:
        return sync_archive(
            client, type_="contracts", fiscal_year=2024,
            parquet_dir=tmp_path / "parquet", raw_dir=tmp_path / "raw",
            manifest_path=tmp_path / "manifest.jsonl",
            required_columns=REQUIRED, min_free_gb=0, **kw
        )


def test_sync_archive_threads_the_guard_and_records_nothing_on_abort(tmp_path):
    from govbudget.manifest import load_records

    assert _sync_archive(tmp_path, 100, "FY2024_097_Contracts_Full_v1.zip") == "loaded"
    live = tmp_path / "parquet" / "contracts" / "fy=2024"
    assert _count(f"{live}/*.parquet") == 100

    with pytest.raises(PartitionShrinkError):
        _sync_archive(tmp_path, 10, "FY2024_097_Contracts_Full_v2.zip")
    assert _count(f"{live}/*.parquet") == 100
    assert len(load_records(tmp_path / "manifest.jsonl")) == 1, \
        "no manifest record for an archive that was never swapped in"

    assert _sync_archive(
        tmp_path, 10, "FY2024_097_Contracts_Full_v2.zip", allow_shrink=True
    ) == "loaded"
    assert _count(f"{live}/*.parquet") == 10
    assert len(load_records(tmp_path / "manifest.jsonl")) == 2


# ── sync_mts_outlays ────────────────────────────────────────────────────────


def _mts_client(n_rows):
    def handler(request):
        return httpx.Response(200, json={
            "data": [
                {"record_fiscal_year": "2024", "record_date": "2024-01-31",
                 "classification_desc": f"row {i}",
                 "current_month_gross_outly_amt": "1.0"}
                for i in range(n_rows)
            ],
            "meta": {"total-pages": 1},
        })
    return httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://example.invalid",
    )


def _sync_mts(tmp_path, n_rows, **kw):
    from govbudget.fiscaldata import sync_mts_outlays

    with _mts_client(n_rows) as client:
        return sync_mts_outlays(
            client,
            parquet_dir=tmp_path / "parquet", raw_dir=tmp_path / "raw",
            manifest_path=tmp_path / "manifest.jsonl", fy_start=2017, **kw
        )


def test_mts_sync_aborts_when_the_row_count_shrinks(tmp_path):
    out = _sync_mts(tmp_path, 100)
    assert _count(out) == 100
    with pytest.raises(PartitionShrinkError) as exc:
        _sync_mts(tmp_path, 10)
    assert "--allow-corpus-shrink" in str(exc.value)
    # The prior file survives untouched, no manifest record was appended for
    # the refused pull, and the incoming sibling is cleaned up.
    assert _count(out) == 100
    records = [
        json.loads(line)
        for line in (tmp_path / "manifest.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert not (out.parent / "mts_table_5.parquet.incoming").exists()
    # The raw JSONL is kept so a refused pull is inspectable.
    assert (tmp_path / "raw" / "mts_table_5.jsonl").exists()


def test_mts_sync_allows_the_shrink_with_the_flag(tmp_path):
    out = _sync_mts(tmp_path, 100)
    _sync_mts(tmp_path, 10, allow_shrink=True)
    assert _count(out) == 10
    assert not (tmp_path / "raw" / "mts_table_5.jsonl").exists()


# ── CLI surface ─────────────────────────────────────────────────────────────
#
# The parametrized tests below patch cmd_sync_subawards / cmd_sync_fiscaldata
# WHOLESALE, so deleting `allow_shrink=getattr(...)` from cli.py:84 or :101
# would leave this whole file green. The next two tests patch the UNDERLYING
# function each command calls instead (mirroring
# tests/test_archive_sync.py:90-113's `fake_sync` on `sync_archive_cmd`), so
# the actual kwarg-threading at those two call sites is what's under test.


def test_cmd_sync_subawards_threads_allow_shrink_to_convert_zip_to_parquet(tmp_path, monkeypatch):
    """cli.py:84 — the getattr(args, "allow_corpus_shrink", False) kwarg on
    the convert_zip_to_parquet call inside cmd_sync_subawards."""
    import contextlib

    from govbudget import cli, config
    from govbudget import convert as convert_mod
    from govbudget import download as download_mod
    from govbudget.usaspending import subawards as subawards_mod

    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "PARQUET_DIR", tmp_path / "parquet")
    monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "manifest.jsonl")
    monkeypatch.setattr(config, "MIN_FREE_GB", 0)
    monkeypatch.setattr(cli, "_usaspending_client", lambda: contextlib.nullcontext(object()))
    monkeypatch.setattr(
        subawards_mod, "request_subaward_download",
        lambda client, *, fiscal_year: {"file_name": f"subawards_fy{fiscal_year}.zip"},
    )
    monkeypatch.setattr(
        subawards_mod, "poll_until_ready",
        lambda client, file_name, **kw: f"https://example.invalid/{file_name}",
    )
    monkeypatch.setattr(
        download_mod, "download_file",
        lambda client, url, dest, **kw: ("deadbeef", 0),
    )

    seen = []

    def fake_convert(zip_path, *, dataset, fiscal_year, parquet_dir, raw_dir,
                      required_columns, allow_shrink=False):
        seen.append(allow_shrink)
        out_dir = parquet_dir / dataset / f"fy={fiscal_year}"
        out_dir.mkdir(parents=True, exist_ok=True)
        return [out_dir / "part_000.parquet"]

    monkeypatch.setattr(convert_mod, "convert_zip_to_parquet", fake_convert)

    cli.cmd_sync_subawards(type("A", (), {"fy": 2025, "allow_corpus_shrink": True})())
    cli.cmd_sync_subawards(type("A", (), {"fy": 2026, "allow_corpus_shrink": False})())
    assert seen == [True, False]


def test_cmd_sync_fiscaldata_threads_allow_shrink_to_sync_mts_outlays(tmp_path, monkeypatch):
    """cli.py:101 — the getattr(args, "allow_corpus_shrink", False) kwarg on
    the sync_mts_outlays call inside cmd_sync_fiscaldata."""
    from govbudget import cli, config
    from govbudget import fiscaldata as fiscaldata_mod

    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "PARQUET_DIR", tmp_path / "parquet")
    monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "manifest.jsonl")

    seen = []

    def fake_sync(client, *, parquet_dir, raw_dir, manifest_path, fy_start, allow_shrink=False):
        seen.append(allow_shrink)
        return parquet_dir / "mts_outlays" / "mts_table_5.parquet"

    monkeypatch.setattr(fiscaldata_mod, "sync_mts_outlays", fake_sync)

    cli.cmd_sync_fiscaldata(type("A", (), {"allow_corpus_shrink": True})())
    cli.cmd_sync_fiscaldata(type("A", (), {"allow_corpus_shrink": False})())
    assert seen == [True, False]


def test_dbt_source_glob_does_not_match_the_mts_incoming_sibling():
    """Pins the 'invisible to dbt' property the report claims: dbt's source
    for mts_outlays globs the file name read here out of
    dbt/models/sources.yml's own `external_location` (not a hard-coded
    copy of it), and that glob does not match a crashed run's leftover
    mts_table_5.parquet.incoming sibling."""
    import fnmatch
    import re
    from pathlib import Path

    import yaml

    sources = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "dbt" / "models" / "sources.yml")
        .read_text())
    (loc,) = [
        t["meta"]["external_location"]
        for src in sources["sources"] for t in src["tables"]
        if t["name"] == "mts_outlays"
    ]
    # "read_parquet('{{ env_var(…) }}/parquet/mts_outlays/<GLOB>')" -> <GLOB>
    m = re.search(r"/mts_outlays/([^'/]+)'\)", loc)
    assert m, loc
    name_glob = m.group(1)
    assert fnmatch.fnmatch("mts_table_5.parquet", name_glob)
    assert not fnmatch.fnmatch("mts_table_5.parquet.incoming", name_glob)


@pytest.mark.parametrize(
    "argv",
    [
        ["sync-archive"],
        ["sync-subawards", "--fy", "2025"],
        ["sync-fiscaldata"],
    ],
)
def test_every_sync_command_accepts_allow_corpus_shrink(argv, monkeypatch):
    """One spelling across every sync command — same as `influence pull`."""
    from govbudget import cli

    seen = {}
    for name in ("cmd_sync_archive", "cmd_sync_subawards", "cmd_sync_fiscaldata"):
        monkeypatch.setattr(cli, name, lambda a: seen.update(vars(a)), raising=True)
    cli.main(argv + ["--allow-corpus-shrink"])
    assert seen["allow_corpus_shrink"] is True


@pytest.mark.parametrize(
    "cmd", ["sync-archive", "sync-subawards", "sync-fiscaldata"]
)
def test_the_flag_renders_in_help(cmd, capsys):
    """argparse %-expands help strings, so the floor's percent sign must be
    doubled. With a bare `80%)` every one of these three --help calls dies with
    `ValueError: unsupported format character ')'` — the flag is unusable and
    nothing else in this file notices, because argparse only expands help at
    format time."""
    from govbudget import cli

    with pytest.raises(SystemExit) as exc:
        cli.main([cmd, "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--allow-corpus-shrink" in out
    assert "floor 80%" in out


@pytest.mark.parametrize(
    "argv",
    [
        ["sync-archive"],
        ["sync-subawards", "--fy", "2025"],
        ["sync-fiscaldata"],
    ],
)
def test_the_flag_is_off_unless_asked_for(argv, monkeypatch):
    from govbudget import cli

    seen = {}
    for name in ("cmd_sync_archive", "cmd_sync_subawards", "cmd_sync_fiscaldata"):
        monkeypatch.setattr(cli, name, lambda a: seen.update(vars(a)), raising=True)
    cli.main(argv)
    assert seen["allow_corpus_shrink"] is False
