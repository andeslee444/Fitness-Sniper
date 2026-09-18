import shutil
import zipfile
from pathlib import Path

import duckdb


class MissingColumnsError(RuntimeError):
    pass


class PartitionShrinkError(RuntimeError):
    pass


# ── OVERWRITE-REGRESSION GUARD (ROADMAP #8) ─────────────────────────────────
# Generalized from influence/lda.py's _MIN_CORPUS_RETENTION (2026-09-01). Same
# failure, different pipeline: an upstream that answers with a truncated
# archive is not an error. convert_zip_to_parquet validates COLUMNS and then
# swaps the new partition over the old one unconditionally, so a half-sized
# FY2025 contracts archive replaces a full one, the command exits 0, and every
# downstream number silently shrinks. Nothing in dbt, export-site or the 24
# site gates can see it — the numbers stay internally consistent, they are just
# smaller than the truth. ROADMAP #8 would have run this UNATTENDED, which is
# the whole reason the guard has to exist before the scheduler does.
#
# 0.80 matches the LDA floor. A re-downloaded full-FY archive is a superset of
# the last one plus corrections; the only legitimate shrink is a deliberate
# narrowing, which is what --allow-corpus-shrink is for. The guard runs BEFORE
# the live partition is removed and BEFORE the source zip is unlinked, so a
# refused swap costs nothing but the re-run.
_MIN_PARTITION_RETENTION = 0.80


def parquet_row_count(glob_or_path: str) -> int:
    """Row count over a parquet path/glob; 0 when nothing readable is there.

    An unreadable prior partition is NOT a veto — that is exactly the state a
    crashed earlier run leaves behind, and refusing to replace it would wedge
    the pipeline on the corruption it is supposed to fix. Mirrors the same
    decision at influence/lda.py:838-840. DuckDB raises InvalidInputException
    on a junk file and IOException on a glob that matches nothing; both are
    "no readable prior rows", i.e. 0.
    """
    con = duckdb.connect()
    try:
        return con.execute(
            f"select count(*) from read_parquet('{glob_or_path}', union_by_name=true)"
        ).fetchone()[0]
    except Exception as exc:
        print(f"  WARNING: could not count rows in {glob_or_path}: {exc}")
        return 0
    finally:
        con.close()


def _prior_partition_row_count(out_dir: Path) -> int:
    """Row count of the partition already on disk at out_dir.

    A single glob read (`read_parquet('{out_dir}/*.parquet', ...)`) is the
    fast path, but it is all-or-nothing: DuckDB raises on the WHOLE read when
    even one member is unreadable. Production contracts/assistance
    partitions ARE multi-member, so a good 100-row part_000.parquet sitting
    next to one junk part_001.parquet would otherwise count as 0 via
    parquet_row_count's exception handling, and `if prior:` would skip the
    guard entirely — a 10%-truncated upstream archive overwriting a
    99%-intact FY. When the glob read fails, fall back to summing each
    member individually through parquet_row_count, which already skips (and
    prints one WARNING naming) any file it cannot read on its own — so one
    bad file costs only its own rows. A prior where EVERY member fails still
    totals 0: an unreadable prior is still not a veto (unchanged ruling,
    same as the single wholly-junk-file case parquet_row_count already
    handled).
    """
    con = duckdb.connect()
    try:
        return con.execute(
            f"select count(*) from read_parquet("
            f"'{_sql_path(out_dir)}/*.parquet', union_by_name=true)"
        ).fetchone()[0]
    except Exception:
        pass
    finally:
        con.close()
    return sum(
        parquet_row_count(str(part)) for part in sorted(out_dir.glob("*.parquet"))
    )


def _sql_path(path: Path) -> str:
    """Escape a filesystem path for interpolation into a DuckDB SQL string literal."""
    return str(path).replace("'", "''")


def _check_columns(con: duckdb.DuckDBPyConnection, parquet_path: Path, required: set[str]) -> None:
    cols = {
        row[0]
        for row in con.execute(
            f"describe select * from read_parquet('{_sql_path(parquet_path)}')"
        ).fetchall()
    }
    missing = required - cols
    if missing:
        raise MissingColumnsError(
            f"{parquet_path.name} missing required columns: {sorted(missing)}"
        )


def convert_zip_to_parquet(
    zip_path: Path,
    *,
    dataset: str,
    fiscal_year: int,
    parquet_dir: Path,
    raw_dir: Path,
    required_columns: set[str],
    allow_shrink: bool = False,
) -> list[Path]:
    """Extract CSV members one at a time, convert to zstd Parquet, delete raws.

    Converts into a temporary `fy={year}.incoming` partition and swaps it in
    only after every member passes validation: a rejected load preserves the
    prior live partition and the source zip. A crash mid-conversion leaves the
    `.incoming` directory behind; the next run clears it, and dbt's
    `cast(fy as integer)` fails loudly if one is ever read.

    allow_shrink: permit a converted partition holding materially fewer rows
    than the one it replaces to overwrite it (ROADMAP #8). Off by default:
    the failure mode is a truncated upstream file that looks successful, so
    shrinking has to be asked for.
    """
    out_dir = parquet_dir / dataset / f"fy={fiscal_year}"
    tmp_dir = parquet_dir / dataset / f"fy={fiscal_year}.incoming"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    extract_dir = raw_dir / f"extract_{zip_path.stem}"
    extract_dir.mkdir(parents=True, exist_ok=True)

    part_names: list[str] = []
    con = duckdb.connect()
    try:
        with zipfile.ZipFile(zip_path) as zf:
            members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
            for i, member in enumerate(members):
                csv_path = Path(zf.extract(member, extract_dir))
                out_path = tmp_dir / f"part_{i:03d}.parquet"
                con.execute(
                    f"""
                    copy (select * from read_csv('{_sql_path(csv_path)}', header=true, all_varchar=true))
                    to '{_sql_path(out_path)}' (format parquet, compression zstd)
                    """
                )
                csv_path.unlink()
                _check_columns(con, out_path, required_columns)
                part_names.append(out_path.name)
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    finally:
        con.close()
        shutil.rmtree(extract_dir, ignore_errors=True)

    if out_dir.exists() and not allow_shrink:
        prior = _prior_partition_row_count(out_dir)
        if prior:
            fresh = parquet_row_count(f"{_sql_path(tmp_dir)}/*.parquet")
            floor = int(prior * _MIN_PARTITION_RETENTION)
            if fresh < floor:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise PartitionShrinkError(
                    f"{dataset} fy{fiscal_year}: the new archive converted to "
                    f"{fresh:,} rows against the {prior:,} already on disk "
                    f"({fresh / prior:.1%}), under the "
                    f"{_MIN_PARTITION_RETENTION:.0%} retention floor of "
                    f"{floor:,} rows. Refusing to overwrite a larger partition "
                    "with a smaller one — the live partition and the source "
                    "zip are untouched, so re-running costs nothing. This is "
                    "what a truncated upstream file looks like: the columns "
                    "are all there, so the column check passes it. If the "
                    "shrink is intended, re-run with --allow-corpus-shrink."
                )

    if out_dir.exists():
        shutil.rmtree(out_dir)
    tmp_dir.rename(out_dir)
    zip_path.unlink()
    return [out_dir / name for name in part_names]


def sweep_incoming_dirs(parquet_dir: Path) -> int:
    """Delete orphaned fy=*.incoming dirs left by crashed conversions.

    The sources.yml glob matches them and dbt's cast(fy as integer) then
    fails the whole build, so they must be cleared before each sync.
    """
    if not parquet_dir.exists():
        return 0
    stale = [p for p in parquet_dir.glob("*/fy=*.incoming") if p.is_dir()]
    for p in stale:
        shutil.rmtree(p)
    return len(stale)
