"""Pinned proof snapshots, and a masked, parquet-aware diff of two data/site trees.

Families piece 1 (docs/superpowers/specs/2026-10-02-era-procurement-history-design.md
§8, "Proofs run on pinned snapshots, never on the live lake").

What `govbudget export-site` reads — and so what `snapshot()` pins (traced in
export_site.py, cli.py and config.py on 2026-10-02):

  Under GOVBUDGET_DATA (config.DATA_DIR, config.py:29). Every lake constant is
  built from it — SITE_DIR, DUCKDB_PATH, PARQUET_DIR, RAW_DOCS_DIR, RAW_DIR and
  MANIFEST_PATH (config.py:56-67) — so one variable moves them all.
    duckdb/govbudget.duckdb  config.DUCKDB_PATH. dbt materializes most marts as
                             VIEWS whose SQL embeds the ABSOLUTE
                             read_parquet('<DATA_DIR>/parquet/...') path of the
                             lake it was built against (18 of 37 views on
                             2026-10-02). A byte copy alone would still read the
                             live lake, so snapshot() repoints those views at the
                             copy. config ignores GOVBUDGET_DUCKDB; only dbt
                             (dbt/profiles.yml) and `govbudget build`
                             (cli.py cmd_build) read it.
    parquet/                 config.PARQUET_DIR. The exporter also reads staged
                             parquets BESIDE the DuckDB file
                             (export_site._stage_parquet_path/_lake_parquet_dir:
                             <duckdb dir>/../parquet/<stage>/...).
    manifest.jsonl           config.MANIFEST_PATH (site_meta source freshness).
    site/                    config.SITE_DIR, the output tree. Existing pdfs/ and
                             workbooks/ are kept when their sha256 matches;
                             program_pdf_receipts downloads a PDF only when
                             site/pdfs/<sha>.pdf is missing.
    raw_docs/                NOT read through config.RAW_DOCS_DIR: the document
                             loop (export_site.py, "3. Documents") stats and copies
                             jbook_documents.file_path, an ABSOLUTE path stored in
                             Postgres. snapshot() clones raw_docs and points the
                             scratch database's file_path rows at the clone.
  Postgres: config.PG_DSN (GOVBUDGET_PG_DSN).
  Repo-relative, pinned by the commit being run, not by the snapshot:
    data/research/ (config.RESEARCH_DIR = ROOT/data/research, config.py:63),
    data-seeds/, dbt/seeds/state_category_map.csv, the build_checks inputs
    (dbt/target/manifest.json, site/scripts/verify.mjs,
    evals/phase5_questions.yaml), and the program_pdf_receipts page cache
    ROOT/tmp/pdfs (derived from sha-pinned PDFs; a cold cache costs time only).

Running export-site against a snapshot (each export gets its own clone, so a
second export never starts from the first one's output):

    SNAP=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/<name>
    cp -c -R "$SNAP" "$SNAP-A"           # APFS clone: seconds, no extra space
    source "$SNAP/env.sh" "$SNAP-A"      # GOVBUDGET_DATA/_DUCKDB -> $SNAP-A, PG -> scratch db
    uv run --project . python -m govbudget export-site     # from the code checkout's GovBudget/
    uv run --project . python -m govbudget proof diff "$SNAP/site" "$SNAP-A/site"

The clone's DuckDB views keep reading $SNAP/parquet and its documents resolve to
$SNAP/raw_docs; both are read-only and pinned. Never run a snapshot or an export
between :15 and :20 past the hour (the hourly SAM job writes data/parquet/sam
at :17); snapshot() refuses to.

diff_trees() compares two data/site trees: JSON structurally, parquet as row
multisets, everything else by bytes. It masks build timestamps only — values of
`built_at`/`retrieved_at` that are UTC instants inside the tree's own build
window, and `measured_on` equal to the build day — never `retrieved_at` as a
key, because source retrieval stamps are evidence (spec §10 expects specific
`retrieved_at` changes).

Float noise: dbt marts built from parallel double sums (dim_geography,
fct_district_totals, fct_program_concentration) differ in the last bits
between two identical queries (4589898661.9800005 vs 4589898661.98), so
DOUBLE/FLOAT parquet values and JSON floats equal to FLOAT_SIGNIFICANT_DIGITS
significant digits (relative difference at most 1e-12) count as equivalent and
are tallied apart (report["float_noise"], each file's "float_noise"); they are
never "changed". Integers, decimals and strings always compare exactly.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SNAPSHOT_MANIFEST = "snapshot.json"
SNAPSHOT_ENV = "env.sh"
DUCKDB_REL = Path("duckdb") / "govbudget.duckdb"
MANIFEST_REL = "manifest.jsonl"
CLONED_DIRS = ("parquet", "site", "raw_docs")
SAM_WINDOW_MINUTES = range(15, 21)
DEFAULT_PG_BIN = Path("/opt/homebrew/opt/postgresql@17/bin")

BUILD_TS = "<build-timestamp>"
BUILD_DATE = "<build-date>"
STAMP_KEYS = frozenset({"built_at", "retrieved_at"})
DATE_KEYS = frozenset({"measured_on"})
STATUSES = ("identical", "equivalent", "changed", "only_a", "only_b")
CHANGES = ("added", "removed", "changed", "reordered")
FLOAT_SIGNIFICANT_DIGITS = 12
FLOAT_TYPES = frozenset({"DOUBLE", "FLOAT"})
SCRATCH_DB_PREFIX = "govbudget_proof_"

_UTC_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00")
_UTC_FRACTION_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{1,6}\+00:00")
_FID_RE = re.compile(r"[0-9a-f]{16}")
_SCRATCH_DB_RE = re.compile(r"[a-z][a-z0-9_]{0,62}")
_WINDOW_LOOKBACK = datetime.timedelta(hours=3)
_WINDOW_LOOKAHEAD = datetime.timedelta(hours=1)
_GROUP_MIN_FILES = 50
_SAMPLES_PER_CHANGE = 3
_SAMPLE_ROWS = 5
_MAX_VALUE_CHARS = 300
_IGNORED_NAMES = frozenset({".DS_Store"})
_RULE_KEYS = frozenset({"path", "why", "status", "pointer", "change", "required"})
_FLOAT_REL_TOL = 10.0 ** -FLOAT_SIGNIFICANT_DIGITS
_FLOAT_MARK = "\x00float"          # stands in for every float in a pairing key
_NOISE_MAX_ROWS = 1_000_000        # residual parquet rows beyond this compare exactly
_LOCAL_HOSTS = frozenset({"", "localhost", "127.0.0.1", "::1"})


def _now() -> datetime.datetime:
    """Local wall clock; tests monkeypatch this."""
    return datetime.datetime.now()


# ---------------------------------------------------------------------------
# shared
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _same_bytes(pa: Path, pb: Path) -> bool:
    if pa.stat().st_size != pb.stat().st_size:
        return False
    with open(pa, "rb") as fa, open(pb, "rb") as fb:
        while True:
            ca, cb = fa.read(1 << 20), fb.read(1 << 20)
            if ca != cb:
                return False
            if not ca:
                return True


def _files(root: Path) -> list[str]:
    """Sorted POSIX relpaths of every regular file under root.

    Raises on a symlink: a link inside a pinned tree could point back at the
    live lake."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in [*dirnames, *filenames]:
            if (Path(dirpath) / name).is_symlink():
                raise RuntimeError(f"proof: symlink inside a pinned tree: {Path(dirpath) / name}")
        for name in filenames:
            if name in _IGNORED_NAMES:
                continue
            out.append((Path(dirpath) / name).relative_to(root).as_posix())
    return sorted(out)


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Window:
    lo: datetime.datetime
    hi: datetime.datetime
    day: str


def _build_window(tree: Path) -> _Window | None:
    """The span of the export run that produced `tree`, or None.

    Anchored on manifest.json's `built_at`; widened to every UTC instant with
    a fractional second among citations.parquet's retrieved_at values within
    3 h before / 1 h after it (derived rows carry their tier's own now()).
    Source stamps cannot fall inside: a snapshot pins them before the run
    starts, and SAM's are second-precision."""
    manifest = tree / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        obj = json.loads(manifest.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    anchor_s = obj.get("built_at") if isinstance(obj, dict) else None
    if not isinstance(anchor_s, str) or not _UTC_TS_RE.fullmatch(anchor_s):
        return None
    anchor = datetime.datetime.fromisoformat(anchor_s)
    lo, hi = anchor - _WINDOW_LOOKBACK, anchor + _WINDOW_LOOKAHEAD
    stamps = [anchor]
    cit = tree / "citations" / "citations.parquet"
    if cit.is_file():
        import duckdb

        con = duckdb.connect()
        try:
            cols = {r[0] for r in con.execute(
                "describe select * from read_parquet(?)", [str(cit)]).fetchall()}
            if "retrieved_at" in cols:
                for (v,) in con.execute(
                    "select distinct retrieved_at from read_parquet(?)"
                    " where retrieved_at is not null", [str(cit)],
                ).fetchall():
                    if isinstance(v, str) and _UTC_FRACTION_RE.fullmatch(v):
                        d = datetime.datetime.fromisoformat(v)
                        if lo <= d <= hi:
                            stamps.append(d)
        finally:
            con.close()
    return _Window(min(stamps), max(stamps), anchor_s[:10])


def _is_build_stamp(value, window: _Window | None) -> bool:
    if window is None or not isinstance(value, str) or not _UTC_TS_RE.fullmatch(value):
        return False
    return window.lo <= datetime.datetime.fromisoformat(value) <= window.hi


def _mask(obj, window: _Window | None):
    """Mask build stamps in place; return obj."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in STAMP_KEYS and _is_build_stamp(value, window):
                obj[key] = BUILD_TS
            elif key in DATE_KEYS and window is not None and value == window.day:
                obj[key] = BUILD_DATE
            else:
                _mask(value, window)
    elif isinstance(obj, list):
        for value in obj:
            _mask(value, window)
    return obj


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _escape(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def _float_close(x, y) -> bool:
    """Equal to FLOAT_SIGNIFICANT_DIGITS significant digits: the relative
    difference is at most 1e-12. None and NaN match only themselves."""
    if x is None or y is None:
        return x is None and y is None
    if math.isnan(x) or math.isnan(y):
        return math.isnan(x) and math.isnan(y)
    return x == y or math.isclose(x, y, rel_tol=_FLOAT_REL_TOL, abs_tol=0.0)


def _float_order(x) -> tuple:
    """Sort key for a float column or leaf that keeps noisy twins together."""
    if x is None:
        return (0,)
    if math.isnan(x):
        return (2,)
    return (1, float(f"{x:.{FLOAT_SIGNIFICANT_DIGITS}g}"), x)


def _strip_floats(value):
    """value with every float replaced by one marker: what float noise cannot change."""
    if type(value) is float:
        return _FLOAT_MARK
    if isinstance(value, dict):
        return {k: _strip_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_floats(v) for v in value]
    return value


def _floats(value) -> list:
    """Every float in value, in canonical (sorted-key) order."""
    if type(value) is float:
        return [value]
    if isinstance(value, dict):
        return [f for k in sorted(value) for f in _floats(value[k])]
    if isinstance(value, list):
        return [f for v in value for f in _floats(v)]
    return []


def _json_noise(a, b) -> int | None:
    """How many float leaves differ between a and b by float noise only, or
    None when a and b differ in any other way (lists in order here)."""
    if type(a) is float and type(b) is float:
        if a == b:
            return 0
        return 1 if _float_close(a, b) else None
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return None
        pairs = [(a[k], b[k]) for k in a]
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return None
        pairs = list(zip(a, b))
    else:
        return 0 if (type(a) is type(b) and a == b) else None
    total = 0
    for x, y in pairs:
        n = _json_noise(x, y)
        if n is None:
            return None
        total += n
    return total


def _row_noise(ra: tuple, rb: tuple, floats: list[int]) -> int | None:
    """How many float columns differ between two rows by noise only, or None."""
    n = 0
    for i in floats:
        x, y = ra[i], rb[i]
        if not _float_close(x, y):
            return None
        if x is not None and not math.isnan(x) and x != y:
            n += 1
    return n


def _pair_noise(xs: list, ys: list, *, group_key, order_key, measure) -> tuple[list, list, int]:
    """Pair items of xs and ys that differ only by float noise.

    Items pair only inside one group_key (everything except the floats, which
    must be equal exactly); inside a group both sides are walked in order_key
    order and paired when measure() is not None. Returns (unpaired xs,
    unpaired ys, number of float values that differed)."""
    gx: dict = defaultdict(list)
    gy: dict = defaultdict(list)
    for x in xs:
        gx[group_key(x)].append(x)
    for y in ys:
        gy[group_key(y)].append(y)
    left_x, left_y, values = [], [], 0
    for key in sorted(set(gx) | set(gy)):
        la = sorted(gx.get(key, []), key=order_key)
        lb = sorted(gy.get(key, []), key=order_key)
        i = j = 0
        while i < len(la) and j < len(lb):
            n = measure(la[i], lb[j])
            if n is not None:
                values += n
                i += 1
                j += 1
            elif order_key(la[i]) < order_key(lb[j]):
                left_x.append(la[i])
                i += 1
            else:
                left_y.append(lb[j])
                j += 1
        left_x.extend(la[i:])
        left_y.extend(lb[j:])
    return left_x, left_y, values


def _json_changes(a, b, pointer: str, out: list, noise: list | None = None) -> None:
    """Append (change, pointer, a, b) for every difference between a and b.

    Dicts recurse by key; lists compare as multisets of canonical JSON (a
    shuffled list is one `reordered` change; an inserted element is one
    `added` at `<list>/[]`); scalars must match in type AND value, so 1 vs
    1.0 or 1 vs true is a change. Two floats equal to 12 significant digits
    are not a change: their count goes to `noise` instead (list elements that
    differ only by such floats are paired first)."""
    if noise is None:
        noise = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            p = f"{pointer}/{_escape(key)}"
            if key not in b:
                out.append(("removed", p, a[key], None))
            elif key not in a:
                out.append(("added", p, None, b[key]))
            else:
                _json_changes(a[key], b[key], p, out, noise)
        return
    if isinstance(a, list) and isinstance(b, list):
        ca, cb = [_canon(x) for x in a], [_canon(x) for x in b]
        if ca == cb:
            return
        ma, mb = Counter(ca), Counter(cb)
        if ma == mb:
            out.append(("reordered", pointer, None, None))
            return
        only_a = [json.loads(s) for s, n in sorted((ma - mb).items()) for _ in range(n)]
        only_b = [json.loads(s) for s, n in sorted((mb - ma).items()) for _ in range(n)]
        only_a, only_b, n_noise = _pair_noise(
            only_a, only_b,
            group_key=lambda x: _canon(_strip_floats(x)),
            order_key=lambda x: tuple(_float_order(f) for f in _floats(x)),
            measure=_json_noise,
        )
        noise.append(n_noise)
        if not only_a and not only_b:
            if [_canon(_strip_floats(x)) for x in a] != [_canon(_strip_floats(x)) for x in b]:
                out.append(("reordered", pointer, None, None))
            return
        out.extend(("removed", pointer + "/[]", x, None) for x in sorted(only_a, key=_canon))
        out.extend(("added", pointer + "/[]", None, y) for y in sorted(only_b, key=_canon))
        return
    if type(a) is type(b) and a == b:
        return
    if type(a) is float and type(b) is float and _float_close(a, b):
        noise.append(1)
        return
    out.append(("changed", pointer, a, b))


def _pattern(pointer: str) -> str:
    return "/".join("{fid}" if _FID_RE.fullmatch(s) else s for s in pointer.split("/"))


def _short(value) -> str | None:
    if value is None:
        return None
    s = _canon(value)
    return s if len(s) <= _MAX_VALUE_CHARS else s[:_MAX_VALUE_CHARS] + "…"


def _json_detail(pa: Path, pb: Path, wa, wb) -> tuple[dict | None, int]:
    """(detail, float-noise values); detail is None when the two files hold
    the same JSON value after masking, floats compared to 12 significant digits."""
    a = _mask(json.loads(pa.read_text(encoding="utf-8")), wa)
    b = _mask(json.loads(pb.read_text(encoding="utf-8")), wb)
    raw: list = []
    noise: list = []
    _json_changes(a, b, "", raw, noise)
    if not raw:
        return None, sum(noise)
    grouped: dict[tuple[str, str], dict] = {}
    for change, pointer, va, vb in raw:
        key = (_pattern(pointer), change)
        entry = grouped.setdefault(
            key, {"pattern": key[0], "change": change, "count": 0, "samples": []}
        )
        entry["count"] += 1
        if len(entry["samples"]) < _SAMPLES_PER_CHANGE:
            entry["samples"].append({"pointer": pointer, "a": _short(va), "b": _short(vb)})
    return {"changes": [grouped[k] for k in sorted(grouped)]}, sum(noise)


def _sql_path(path: Path) -> str:
    return "read_parquet('" + str(path).replace("'", "''") + "')"


def _masked_select(con, path: Path, schema: list, window, tag: str) -> str:
    src = _sql_path(path)
    exprs = []
    for i, (name, typ) in enumerate(schema):
        q = '"' + name.replace('"', '""') + '"'
        if name in STAMP_KEYS and typ == "VARCHAR" and window is not None:
            masked = [
                v for (v,) in con.execute(
                    f"select distinct {q} from {src} where {q} is not null").fetchall()
                if _is_build_stamp(v, window)
            ]
            if masked:
                table = f"mask_{tag}_{i}"
                con.execute(f"create temp table {table} (v varchar)")
                con.executemany(f"insert into {table} values (?)", [(v,) for v in masked])
                exprs.append(
                    f"case when {q} in (select v from {table}) then '{BUILD_TS}'"
                    f" else {q} end as {q}"
                )
                continue
        exprs.append(q)
    return f"select {', '.join(exprs)} from {src}"


def _jsonable(cols: list[str], row: tuple) -> dict:
    return json.loads(json.dumps(dict(zip(cols, row)), default=str))


def _jsonable_rows(cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [_jsonable(cols, row) for row in cursor.fetchall()]


def _parquet_detail(pa: Path, pb: Path, wa, wb) -> tuple[dict | None, int]:
    """(detail, float-noise values); detail is None when the two files hold the
    same row multiset after masking, DOUBLE/FLOAT columns compared to 12
    significant digits (every other column exactly)."""
    import duckdb

    con = duckdb.connect()
    try:
        schema_a = [[r[0], r[1]] for r in con.execute(f"describe select * from {_sql_path(pa)}").fetchall()]
        schema_b = [[r[0], r[1]] for r in con.execute(f"describe select * from {_sql_path(pb)}").fetchall()]
        rows_a = con.execute(f"select count(*) from {_sql_path(pa)}").fetchone()[0]
        rows_b = con.execute(f"select count(*) from {_sql_path(pb)}").fetchone()[0]
        if schema_a != schema_b:
            return {"schema_a": schema_a, "schema_b": schema_b, "rows_a": rows_a,
                    "rows_b": rows_b, "only_a": None, "only_b": None,
                    "sample_only_a": [], "sample_only_b": []}, 0
        sel_a = _masked_select(con, pa, schema_a, wa, "a")
        sel_b = _masked_select(con, pb, schema_b, wb, "b")
        only_a = con.execute(f"select count(*) from ({sel_a} except all {sel_b})").fetchone()[0]
        only_b = con.execute(f"select count(*) from ({sel_b} except all {sel_a})").fetchone()[0]
        if only_a == 0 and only_b == 0:
            return None, 0
        cols = [name for name, _ in schema_a]
        floats = [i for i, (_, typ) in enumerate(schema_a) if typ in FLOAT_TYPES]
        if floats and only_a + only_b <= _NOISE_MAX_ROWS:
            exact = [i for i in range(len(cols)) if i not in floats]
            left_a, left_b, noise = _pair_noise(
                con.execute(f"select * from ({sel_a} except all {sel_b})").fetchall(),
                con.execute(f"select * from ({sel_b} except all {sel_a})").fetchall(),
                group_key=lambda r: repr([r[i] for i in exact]),
                order_key=lambda r: tuple(_float_order(r[i]) for i in floats),
                measure=lambda ra, rb: _row_noise(ra, rb, floats),
            )
            if not left_a and not left_b:
                return None, noise
            return {
                "schema_a": schema_a, "schema_b": schema_b, "rows_a": rows_a, "rows_b": rows_b,
                "only_a": len(left_a), "only_b": len(left_b),
                "sample_only_a": [_jsonable(cols, r) for r in left_a[:_SAMPLE_ROWS]],
                "sample_only_b": [_jsonable(cols, r) for r in left_b[:_SAMPLE_ROWS]],
            }, noise
        return {
            "schema_a": schema_a, "schema_b": schema_b, "rows_a": rows_a, "rows_b": rows_b,
            "only_a": only_a, "only_b": only_b,
            "sample_only_a": _jsonable_rows(con.execute(
                f"select * from ({sel_a} except all {sel_b}) limit {_SAMPLE_ROWS}")),
            "sample_only_b": _jsonable_rows(con.execute(
                f"select * from ({sel_b} except all {sel_a}) limit {_SAMPLE_ROWS}")),
        }, 0
    finally:
        con.close()


def _kind(rel: str) -> str:
    if rel.endswith(".json"):
        return "json"
    if rel.endswith(".parquet"):
        return "parquet"
    return "bytes"


def _group(rel: str, dir_counts: Counter) -> str:
    parent, _, name = rel.rpartition("/")
    if parent and dir_counts[parent] >= _GROUP_MIN_FILES:
        return f"{parent}/*{Path(name).suffix}"
    return rel


def diff_trees(a: Path, b: Path) -> dict:
    """Compare two data/site trees; return the report (see module docstring).

    report["counts"] has every status in STATUSES; report["files"] lists each
    file that is not byte-identical; report["groups"] tallies statuses per
    path group (a directory with 50+ files collapses to '<dir>/*<suffix>');
    report["float_noise"] = {files, values} counts the float values equal to
    12 significant digits that were treated as equal (each file entry carries
    its own "float_noise")."""
    a, b = Path(a), Path(b)
    for root in (a, b):
        if not root.is_dir():
            raise NotADirectoryError(f"proof diff: {root} is not a directory")
    wa, wb = _build_window(a), _build_window(b)
    files_a, files_b = set(_files(a)), set(_files(b))
    every = sorted(files_a | files_b)
    dir_counts = Counter(rel.rpartition("/")[0] for rel in every)
    counts = Counter({s: 0 for s in STATUSES})
    groups: dict[str, Counter] = {}
    files: dict[str, dict] = {}
    noise_files = noise_values = 0
    for rel in every:
        kind, group = _kind(rel), _group(rel, dir_counts)
        detail, noise = None, 0
        if rel not in files_b:
            status = "only_a"
        elif rel not in files_a:
            status = "only_b"
        elif _same_bytes(a / rel, b / rel):
            status = "identical"
        else:
            if kind == "json":
                try:
                    detail, noise = _json_detail(a / rel, b / rel, wa, wb)
                except ValueError:  # not JSON after all: compare as bytes
                    kind = "bytes"
            elif kind == "parquet":
                detail, noise = _parquet_detail(a / rel, b / rel, wa, wb)
            if kind == "bytes":
                detail = {"sha256_a": _sha256_file(a / rel), "sha256_b": _sha256_file(b / rel)}
            status = "changed" if detail is not None else "equivalent"
        counts[status] += 1
        groups.setdefault(group, Counter({s: 0 for s in STATUSES}))[status] += 1
        if noise:
            noise_files += 1
            noise_values += noise
        if status != "identical":
            files[rel] = {"status": status, "kind": kind, "group": group, "detail": detail,
                          "float_noise": noise}
    return {
        "a": str(a),
        "b": str(b),
        "build_window": {
            side: (None if w is None else [w.lo.isoformat(), w.hi.isoformat()])
            for side, w in (("a", wa), ("b", wb))
        },
        "counts": dict(counts),
        "float_noise": {"files": noise_files, "values": noise_values},
        "groups": {g: dict(c) for g, c in sorted(groups.items())},
        "files": files,
    }


def is_equal(report: dict) -> bool:
    c = report["counts"]
    return c["changed"] == 0 and c["only_a"] == 0 and c["only_b"] == 0


# ---------------------------------------------------------------------------
# expectations (--expect)
# ---------------------------------------------------------------------------


def _glob(pattern: str, text: str) -> bool:
    """`*` matches any run of characters (including '/'); nothing else is special."""
    rx = "".join(".*" if c == "*" else re.escape(c) for c in pattern)
    return re.fullmatch(rx, text, re.DOTALL) is not None


def load_expectations(path: Path) -> list[dict]:
    """Read and validate an --expect file: a JSON list of rules.

    Rule keys: path (required glob over the tree-relative path), why
    (required, non-empty: the allowed-change description), status (list of
    'equivalent'-free statuses: changed/only_a/only_b), pointer (glob over a
    JSON change pattern such as '/{fid}/retrieved_at' or '/decade_series/[]'),
    change (list of added/removed/changed/reordered), required (bool: the
    rule must match at least one difference)."""
    rules = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rules, list):
        raise ValueError("proof diff --expect: the file must hold a JSON list of rules")
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f"proof diff --expect: rule {i} is not an object")
        unknown = set(rule) - _RULE_KEYS
        if unknown:
            raise ValueError(f"proof diff --expect: rule {i} has unknown keys {sorted(unknown)}")
        if not isinstance(rule.get("path"), str) or not rule["path"]:
            raise ValueError(f"proof diff --expect: rule {i} needs a 'path' glob")
        if not isinstance(rule.get("why"), str) or not rule["why"].strip():
            raise ValueError(f"proof diff --expect: rule {i} needs a non-empty 'why'")
        if "status" in rule and not set(rule["status"]) <= {"changed", "only_a", "only_b"}:
            raise ValueError(f"proof diff --expect: rule {i} has a bad 'status' {rule['status']}")
        if "change" in rule and not set(rule["change"]) <= set(CHANGES):
            raise ValueError(f"proof diff --expect: rule {i} has a bad 'change' {rule['change']}")
        if "pointer" in rule and not isinstance(rule["pointer"], str):
            raise ValueError(f"proof diff --expect: rule {i} 'pointer' must be a string")
        if "required" in rule and not isinstance(rule["required"], bool):
            raise ValueError(f"proof diff --expect: rule {i} 'required' must be true/false")
    return rules


def _diff_items(report: dict) -> list[dict]:
    items = []
    for rel, entry in sorted(report["files"].items()):
        status = entry["status"]
        if status == "equivalent":
            continue
        if status == "changed" and entry["kind"] == "json":
            for ch in entry["detail"]["changes"]:
                items.append({"path": rel, "status": status, "pattern": ch["pattern"],
                              "change": ch["change"], "count": ch["count"]})
        else:
            items.append({"path": rel, "status": status, "pattern": None,
                          "change": None, "count": 1})
    return items


def _rule_matches(rule: dict, item: dict) -> bool:
    if not _glob(rule["path"], item["path"]):
        return False
    if "status" in rule and item["status"] not in rule["status"]:
        return False
    if "pointer" in rule and (item["pattern"] is None or not _glob(rule["pointer"], item["pattern"])):
        return False
    if "change" in rule and item["change"] not in rule["change"]:
        return False
    return True


def check_expectations(report: dict, rules: list[dict]) -> dict:
    """Every difference must match a rule; every `required` rule must match."""
    matched = [0] * len(rules)
    unexpected = []
    for item in _diff_items(report):
        hit = False
        for i, rule in enumerate(rules):
            if _rule_matches(rule, item):
                matched[i] += item["count"]
                hit = True
        if not hit:
            unexpected.append(item)
    unmet = [{"rule": i, "path": r["path"], "why": r["why"]}
             for i, r in enumerate(rules) if r.get("required") and matched[i] == 0]
    return {
        "ok": not unexpected and not unmet,
        "unexpected": unexpected,
        "unmet": unmet,
        "matched": [{"rule": i, "path": r["path"], "why": r["why"], "count": matched[i]}
                    for i, r in enumerate(rules)],
    }


def format_report(report: dict, verdict: dict | None = None) -> list[str]:
    """Human-readable lines; the last line is the verdict."""
    c, fn = report["counts"], report["float_noise"]
    lines = [
        f"proof diff: A = {report['a']}",
        f"proof diff: B = {report['b']}",
        f"  build window A {report['build_window']['a']} · B {report['build_window']['b']}",
        f"  identical {c['identical']:,} · equivalent {c['equivalent']:,}"
        f" (build stamps, row order, JSON formatting or float noise only) · changed {c['changed']:,}"
        f" · only in A {c['only_a']:,} · only in B {c['only_b']:,}",
        f"  equivalent (float noise): {fn['files']:,} file(s), {fn['values']:,} value(s)"
        f" equal to {FLOAT_SIGNIFICANT_DIGITS} significant digits",
    ]
    for group, gc in report["groups"].items():
        if not (gc["changed"] or gc["only_a"] or gc["only_b"]):
            continue
        lines.append(f"  {group}: changed {gc['changed']:,} · only in A {gc['only_a']:,}"
                     f" · only in B {gc['only_b']:,}")
        tally: Counter = Counter()
        for entry in report["files"].values():
            if entry["group"] != group or entry["status"] != "changed":
                continue
            if entry["kind"] == "json":
                for ch in entry["detail"]["changes"]:
                    tally[(ch["pattern"], ch["change"])] += ch["count"]
            elif entry["kind"] == "parquet":
                d = entry["detail"]
                tally[(f"rows {d['rows_a']:,} -> {d['rows_b']:,}; only in A {d['only_a']}"
                       f", only in B {d['only_b']}", "parquet")] += 1
            else:
                tally[("bytes differ", "bytes")] += 1
        for (pattern, change), n in tally.most_common(10):
            lines.append(f"    {change} {pattern} ×{n:,}")
    if verdict is None:
        lines.append("proof diff: EQUAL" if is_equal(report) else "proof diff: DIFFERENT")
        return lines
    for m in verdict["matched"]:
        lines.append(f"  rule {m['rule']} [{m['path']}] matched {m['count']:,}: {m['why']}")
    if verdict["unexpected"]:
        lines.append(f"  UNEXPECTED differences: {len(verdict['unexpected']):,}")
        for item in verdict["unexpected"][:50]:
            lines.append(f"    {item['path']} {item['status']}"
                         f" {item['change'] or ''} {item['pattern'] or ''} ×{item['count']:,}".rstrip())
    for u in verdict["unmet"]:
        lines.append(f"  UNMET required rule {u['rule']} [{u['path']}]: {u['why']}")
    lines.append("proof diff: PASS" if verdict["ok"] else "proof diff: FAIL")
    return lines
