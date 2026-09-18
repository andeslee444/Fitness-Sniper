import datetime as dt
import hashlib
import json
from pathlib import Path

import duckdb
import httpx

from govbudget.convert import (
    _MIN_PARTITION_RETENTION,
    PartitionShrinkError,
    _sql_path,
    parquet_row_count,
)
from govbudget.manifest import ManifestRecord, append_record


def fetch_all_pages(client: httpx.Client, path: str, params: dict) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        r = client.get(path, params={**params, "page[number]": str(page), "page[size]": "10000"})
        r.raise_for_status()
        body = r.json()
        rows.extend(body["data"])
        total_pages = body.get("meta", {}).get("total-pages")
        if total_pages is None:
            raise ValueError(
                f"Unexpected FiscalData response — no meta.total-pages: {body!r}"
            )
        if page >= int(total_pages):
            return rows
        page += 1


def sync_mts_outlays(
    client: httpx.Client, *, parquet_dir: Path, raw_dir: Path,
    manifest_path: Path, fy_start: int, allow_shrink: bool = False,
) -> Path:
    """Treasury MTS table 5 -> one parquet. Returns the written path.

    allow_shrink: permit a pull holding materially fewer rows than the file it
    replaces to overwrite it (ROADMAP #8). Off by default — see the guard block
    in convert.py. There is no `.incoming` partition convention here, so the
    fresh file is written to a `.parquet.incoming` sibling and swapped only once
    the guard passes; the raw JSONL is kept until the swap succeeds so a refused
    pull is inspectable. dbt reads this directory as `*.parquet`
    (dbt/models/sources.yml:17), which does not match `.parquet.incoming`, so a
    crashed run's leftover sibling is invisible to the build.
    """
    path = "/v1/accounting/mts/mts_table_5"
    rows = fetch_all_pages(client, path, {"filter": f"record_fiscal_year:gte:{fy_start}"})
    raw_dir.mkdir(parents=True, exist_ok=True)
    jsonl = raw_dir / "mts_table_5.jsonl"
    with open(jsonl, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    out_dir = parquet_dir / "mts_outlays"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "mts_table_5.parquet"
    incoming_path = out_dir / "mts_table_5.parquet.incoming"
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            copy (select * from read_json_auto('{_sql_path(jsonl)}', format='newline_delimited'))
            to '{_sql_path(incoming_path)}' (format parquet, compression zstd)
            """
        )
    finally:
        con.close()

    if out_path.exists() and not allow_shrink:
        prior = parquet_row_count(_sql_path(out_path))
        if prior:
            fresh = parquet_row_count(_sql_path(incoming_path))
            floor = int(prior * _MIN_PARTITION_RETENTION)
            if fresh < floor:
                incoming_path.unlink(missing_ok=True)
                raise PartitionShrinkError(
                    f"mts_outlays: the pull returned {fresh:,} rows against the "
                    f"{prior:,} already on disk ({fresh / prior:.1%}), under the "
                    f"{_MIN_PARTITION_RETENTION:.0%} retention floor of "
                    f"{floor:,} rows. Refusing to overwrite a larger file with "
                    f"a smaller one — the prior parquet is untouched; the "
                    f"refused pull's {jsonl} is kept for inspection. If the "
                    "shrink is intended, re-run with --allow-corpus-shrink."
                )

    incoming_path.replace(out_path)
    jsonl.unlink()
    append_record(manifest_path, ManifestRecord(
        dataset="mts_outlays", fiscal_year=None,
        file_name=out_path.name,
        source_url=str(client.base_url).rstrip("/") + path,
        sha256=hashlib.sha256(out_path.read_bytes()).hexdigest(),
        bytes=out_path.stat().st_size,
        downloaded_at=dt.datetime.now(dt.UTC).isoformat(),
    ))
    return out_path
