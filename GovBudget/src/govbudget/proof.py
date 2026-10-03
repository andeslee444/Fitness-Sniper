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
significant digits (relative difference at most 1e-12) OR within
_FLOAT_ABS_TOL (1e-6) absolute — the same non-determinism shows up as a
near-zero residual too, where a purely relative rule is degenerate (Fix
round 3b) — count as equivalent and are tallied apart (report["float_noise"],
each file's "float_noise"); they are never "changed". Integers and decimals
always compare exactly.

Fix round 3 (2026-10, driven by two real exports of one snapshot differing):
  - Numeric-text equivalence: when BOTH sides of a string leaf (a JSON value
    or a parquet VARCHAR cell) are numeric text — a rendering of a finite
    float: a decimal point, or an exponent with an explicit sign (Fix round
    4; see _NUMERIC_TEXT_RE) — they compare as numbers under the SAME float
    rule and, if equal, count as float noise too — not their own class.
    Any other string, including a bare integer or an unsigned-exponent
    identity code ("0050E89600", "133783872e323816"), compares exactly.
  - JSON-in-string equivalence: when BOTH sides of a string leaf parse as a
    JSON array or object (citations.parquet's `inputs`/`query_body`/
    `recorded_value` VARCHAR columns; citations.json's matching fields), the
    PARSED values are compared with these same rules, recursively; the
    verdict (noise, a trusted reorder, or a real change) is reported at the
    OUTER string leaf's pointer, never a pointer inside the decoded value.
  - Derived-hash equivalence (ruling 3): a content hash or byte count is
    equivalent when the file it describes is present in BOTH trees and
    compared equivalent or reordered in the SAME diff — never when that
    file is missing or byte-identical (Fix round 4: neither can explain a
    different hash or size of it). DERIVED_HASH_CARRIERS names the two known
    cases (json/datasets.json's per-entry `bytes`, pointed at
    `data/<file>`; json/budget_pdf_receipts_audit.json's `/citation_sha256`,
    pointed at json/citations.json) — an explicit, small mapping, not a
    generic hash-field detector. Tallied apart in report["derived_hash"].
  - Reorder classes (ruling 4): a pure permutation (multiset-equal arrays by
    canonical JSON, including an array found inside a JSON-in-string value)
    is trusted as equivalent ONLY when diff_trees() is called with
    control=True (every class is trusted, and tallied into
    report["reorder_classes"] for `--write-noise`) or with a `noise_classes`
    set a prior control run produced (`--noise-from`; only a REGISTERED
    (group, pointer) class is trusted). With neither, a reorder is reported
    as "changed", exactly as before this ruling — nothing becomes laxer by
    accident. A trusted reorder's file status is "reordered", a THIRD good
    status alongside "identical"/"equivalent" (is_equal() treats it as fine).

Fix round 3b (2026-10, controller ruling after Fix round 3's real-check run
left one difference): _FLOAT_ABS_TOL — see its own comment — closes the one
case the relative-only rule could not: a near-zero float residual compared
against an exact 0.0.

Fix round 4 (2026-10, review findings):
  - Numeric text is a finite float rendering only (above); identity codes
    never compare as numbers, and non-finite values never compare at all.
  - Derived hashes need a present, equivalent-but-not-identical referent.
  - Pairing of noisy rows/elements (_pair_noise) walks a TOTAL order, so it
    depends only on the two multisets, never on DuckDB's fetch order; a
    rejected trial pairing (or a JSON-in-string value that differs for
    real) records no reorder class (_Mode.fork/absorb).
  - `--write-noise` writes only for an EQUAL control: the file records the
    verdict, both source trees and a content hash of the classes, nothing
    time-dependent (noise_file); `--noise-from` refuses any other file
    (load_noise_classes). format_report never truncates a list silently.

Fix round 5 (2026-10, controller ruling on Task 8's judged diffs): a reorder
class's pointer generalises every 16-hex fact-ID segment to {fid} — exactly
as the report's grouping (_pattern) already prints `/{fid}/inputs` — both in
the classes a --control run records and in the lookup a --noise-from run
performs (_Mode.allow_reorder). Export nondeterminism reorders derived
citations' `inputs` and usaspending `query_body` award_ids on a DIFFERENT
random subset of fact IDs every run, so a per-fact-ID class (Fix round 3's
`/1195916d7235078e/inputs`) under-samples it: a judged diff read "changed"
on fact IDs the control merely happened not to see. The KIND of reorder is
what the control observes. No other segment is generalised — codes, slugs,
upper-case or non-16-character hex keep their literal text — and a reorder
of a different field under a fact ID (`/{fid}/tags`) is its own class. The
noise file records the rule (`pointer_generalisation`), and
load_noise_classes refuses a file without it.
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
#: "reordered" only ever gets a non-zero count under --control/--noise-from
#: (Fix round 3, ruling 4); without either flag a pure permutation is still
#: reported as "changed", exactly as before.
STATUSES = ("identical", "equivalent", "reordered", "changed", "only_a", "only_b")
CHANGES = ("added", "removed", "changed", "reordered")
FLOAT_SIGNIFICANT_DIGITS = 12
FLOAT_TYPES = frozenset({"DOUBLE", "FLOAT"})
SCRATCH_DB_PREFIX = "govbudget_proof_"
#: ruling 3 (Fix round 3): an explicit, small mapping of known content-hash /
#: byte-count fields to the file they describe. Each carrier is handled by
#: its own small resolver (_resolve_datasets_derived_hash /
#: _resolve_audit_derived_hash) rather than a generic detector.
DERIVED_HASH_CARRIERS = ("json/datasets.json", "json/budget_pdf_receipts_audit.json")
#: the referent statuses that can excuse a derived-hash difference (Fix
#: round 4): present in both trees, equivalent but NOT byte-identical.
_REFERENT_EXCUSES = frozenset({"equivalent", "reordered"})

_UTC_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00")
_UTC_FRACTION_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{1,6}\+00:00")
_FID_RE = re.compile(r"[0-9a-f]{16}")
_SCRATCH_DB_RE = re.compile(r"[a-z][a-z0-9_]{0,62}")
#: ruling 1 (Fix round 3, tightened in Fix round 4): numeric text is a
#: string — the WHOLE string, ASCII digits only — that is how a program
#: writes a FLOAT, and nothing else:
#:   - a decimal point, optionally followed by an exponent whose sign is
#:     EXPLICIT: "1234.0", "-0.25", ".5", "1.", "1.5e+300", "2.5e-3";
#:   - or digits with an exponent whose sign is EXPLICIT and no point:
#:     "1e-07", "1e+16" (how Python's repr() and JavaScript write a float
#:     with an exponent — always signed).
#: A bare integer ("4248", "0152") never matches, and neither does an
#: exponent without a sign ("1e5"): this domain's IDENTITY codes look
#: exactly like that — pe_bli values "4248", "0152" (float() reads it as
#: 152.0), "0050E89600", "2420E61000"; hex fact_ids "133783872e323816" —
#: and float() turns most E-form codes into inf, so two DIFFERENT codes
#: once compared "equal" (Fix round 4's Critical finding). An identity
#: code is never noisy; reading it as a number merges rows that are not
#: the same row (fct_program_concentration.parquet's pe_bli column, Fix
#: round 3) or hides a real change outright. A string that matches but
#: whose value is not finite ("1e+400") is not numeric text either
#: (_numeric_text). Two strings that both qualify compare as numbers with
#: the same rule as a native float (_float_close); a match is float noise,
#: never its own class. This pattern and _numeric_text also decide which
#: VARCHAR cells collapse together for row pairing (_group_cell).
_NUMERIC_TEXT_RE = re.compile(
    r"[+-]?(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][+-][0-9]+)?"  # a decimal point
    r"|[+-]?[0-9]+[eE][+-][0-9]+"                            # or a SIGNED exponent
)
_WINDOW_LOOKBACK = datetime.timedelta(hours=3)
_WINDOW_LOOKAHEAD = datetime.timedelta(hours=1)
_GROUP_MIN_FILES = 50
_SAMPLES_PER_CHANGE = 3
_SAMPLE_ROWS = 5
_MAX_VALUE_CHARS = 300
_IGNORED_NAMES = frozenset({".DS_Store"})
_RULE_KEYS = frozenset({"path", "why", "status", "pointer", "change", "required"})
_FLOAT_REL_TOL = 10.0 ** -FLOAT_SIGNIFICANT_DIGITS
#: Fix round 3b (controller ruling, 2026-10): a PURELY relative tolerance is
#: degenerate near zero — max(|x|,|y|) is tiny there too, so the tolerance
#: band shrinks right along with the gap it is supposed to absorb. Real
#: evidence: json/districts/AZ-05.json's total_obligation, -2**-27
#: (-7.450580596923828e-09, float-precision residue from the same parallel
#: double-sum non-determinism as every other float-noise case here) vs
#: 0.0 — a relative-only rule can never call that noise. Amounts in this
#: warehouse are dollars or thousands of dollars, so one millionth of a
#: unit is immaterial at that scale; the floor applies in ADDITION to (not
#: instead of) the 12-significant-digit relative rule, everywhere the float
#: rule applies (JSON floats, parquet DOUBLE/FLOAT, numeric text — ruling 1).
_FLOAT_ABS_TOL = 1e-6
_FLOAT_MARK = "\x00float"          # stands in for every float in a pairing key
_NOISE_MAX_ROWS = 1_000_000        # residual parquet rows beyond this compare exactly


class _Mode:
    """How diff_trees() treats a pure permutation (ruling 4, Fix round 3).

    control=True: every (group, pointer) permutation is trusted and tallied
    into `observed` (for --write-noise); any OTHER kind of difference still
    fails the control (diff_trees's caller reads `is_equal`). trusted, when
    not None (--noise-from), is the exact set of (group, pointer) classes a
    PRIOR control run vouched for; a permutation elsewhere is untrusted. A
    class is (group, pointer pattern): 16-hex fact-ID pointer segments read
    as {fid} (Fix round 5), so `/1195916d7235078e/inputs` and
    `/2ab45e40c656c4ef/inputs` are one class, `/{fid}/inputs`.
    Neither set (the default): nothing is trusted, same as before this
    ruling existed. Numeric-text/JSON-in-string/derived-hash equivalence
    (rulings 1-3) do not go through this gate — they apply unconditionally.
    """

    __slots__ = ("control", "trusted", "observed")

    def __init__(self, *, control: bool = False, trusted: set[tuple[str, str]] | None = None):
        if control and trusted is not None:
            raise ValueError("proof diff: --control and --noise-from are mutually exclusive")
        self.control = control
        self.trusted = trusted
        self.observed: Counter = Counter()

    def allow_reorder(self, group: str, pointer: str) -> bool:
        # Fix round 5 (controller ruling): a class is keyed by the pointer's
        # PATTERN — every 16-hex fact-ID segment becomes {fid}, exactly as the
        # report's own grouping prints it — when a control records it AND when
        # a --noise-from run looks it up. No other segment is generalised.
        key = (group, _pattern(pointer))
        if self.control:
            self.observed[key] += 1
            return True
        if self.trusted is not None and key in self.trusted:
            self.observed[key] += 1
            return True
        return False

    def fork(self) -> "_Mode":
        """A probe for one TRIAL comparison (Fix round 4): same trust, an
        empty tally. A trial that fails — a pairing candidate rejected, or a
        JSON-in-string value that differs for real — must not vouch for any
        reorder it saw on the way; only absorb() a probe whose trial
        succeeded."""
        return _Mode(control=self.control, trusted=self.trusted)

    def absorb(self, probe: "_Mode") -> None:
        self.observed.update(probe.observed)


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
    """Equal to FLOAT_SIGNIFICANT_DIGITS significant digits (relative
    difference at most 1e-12) OR within _FLOAT_ABS_TOL (1e-6) absolute —
    the floor a purely relative rule cannot provide near zero (Fix round
    3b). None and NaN match only themselves."""
    if x is None or y is None:
        return x is None and y is None
    if math.isnan(x) or math.isnan(y):
        return math.isnan(x) and math.isnan(y)
    return x == y or math.isclose(x, y, rel_tol=_FLOAT_REL_TOL, abs_tol=_FLOAT_ABS_TOL)


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


def _numeric_text(s) -> float | None:
    """float(s) if s is numeric text (see _NUMERIC_TEXT_RE) with a FINITE
    value; None for "", "1e9x", "nan", "inf", "1e+400", a bare integer, an
    unsigned-exponent code like "0050E89600" or "133783872e323816", etc."""
    if not isinstance(s, str) or not _NUMERIC_TEXT_RE.fullmatch(s):
        return None
    try:
        value = float(s)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _multiset_canon(value):
    """value with every float stripped and every list's elements sorted
    into canonical order, at any depth: two values share this form iff they
    are equal up to float noise and list reordering. Used only to GROUP
    pairing candidates (parquet row cells); `measure`/`_json_noise` still
    decide precisely whether a candidate pair is really equivalent."""
    if type(value) is float:
        return _FLOAT_MARK
    if isinstance(value, dict):
        return {k: _multiset_canon(v) for k, v in value.items()}
    if isinstance(value, list):
        return sorted((_multiset_canon(v) for v in value), key=_canon)
    return value


def _leaf_equiv(a, b, pointer: str, group: str | None, mode: "_Mode | None") -> int | None:
    """a and b are two DIFFERENT, not-both-float scalars at `pointer`.

    Returns the noise count if they are equivalent under ruling 1 (both
    strings that are numeric-text-close) or ruling 2 (both strings that
    parse as a JSON array/object, compared recursively with these same
    rules — including a trusted reorder inside, gated by `mode` exactly as
    a native list would be, keyed at THIS pointer regardless of how deep
    the real difference sits); None for a genuine difference."""
    if not (isinstance(a, str) and isinstance(b, str)):
        return None
    na, nb = _numeric_text(a), _numeric_text(b)
    if na is not None and nb is not None:
        return 1 if _float_close(na, nb) else None
    try:
        pa, pb = json.loads(a), json.loads(b)
    except ValueError:
        return None
    if not isinstance(pa, (list, dict)) or not isinstance(pb, (list, dict)):
        return None
    sub_out: list = []
    sub_noise: list = []
    probe = mode.fork() if mode is not None else None
    _json_changes(pa, pb, pointer, sub_out, sub_noise, group=group, mode=probe,
                  key_pointer=pointer)
    if sub_out:
        return None          # a real change: any reorder seen inside is not vouched for
    if mode is not None:
        mode.absorb(probe)
    return sum(sub_noise)


def _json_noise(a, b, *, group: str | None = None, mode: "_Mode | None" = None,
                key_pointer: str = "") -> int | None:
    """How many float/numeric-text/JSON-in-string leaves differ between a
    and b by noise only (rulings 1+2), or None when a and b differ in any
    other way (lists compared POSITIONALLY here — this pairs CANDIDATES
    already matched on everything else by the caller, not an independent
    reorder search; `key_pointer` is fixed by the caller for any nested
    JSON-in-string reorder-trust lookup, same convention as _json_changes)."""
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
        if type(a) is type(b) and a == b:
            return 0
        return _leaf_equiv(a, b, key_pointer, group, mode)
    total = 0
    for x, y in pairs:
        n = _json_noise(x, y, group=group, mode=mode, key_pointer=key_pointer)
        if n is None:
            return None
        total += n
    return total


def _row_noise(ra: tuple, rb: tuple, lenient: list[tuple[int, str, str]],
               group: str | None, mode: "_Mode | None") -> int | None:
    """How many columns differ between two rows by noise only, or None.

    `lenient` is [(column index, DuckDB type, pointer)] for every column
    eligible for lenient comparison: a FLOAT_TYPES column (ruling: existing
    float noise) or a VARCHAR column (ruling 1: numeric-text; ruling 2:
    JSON-in-string, recursively, with the same reorder gating as a JSON
    file — `pointer` is `/<column name>`, used for that gating)."""
    n = 0
    for i, typ, pointer in lenient:
        x, y = ra[i], rb[i]
        if typ in FLOAT_TYPES:
            if not _float_close(x, y):
                return None
            if x is not None and not math.isnan(x) and x != y:
                n += 1
            continue
        if x == y:
            continue
        if x is None or y is None:
            return None
        m = _leaf_equiv(x, y, pointer, group, mode)
        if m is None:
            return None
        n += m
    return n


def _pair_noise(xs: list, ys: list, *, group_key, order_key, measure,
                mode: "_Mode | None" = None) -> tuple[list, list, int]:
    """Pair items of xs and ys that differ only by noise.

    Items pair only inside one group_key (everything noise cannot change);
    inside a group both sides are walked in order_key order and paired when
    measure(x, y, probe) is not None. order_key must be a TOTAL order on
    distinct items (Fix round 4: callers end it with the item's full
    canonical form), so the pairing — and every count it feeds — depends
    only on the two multisets, never on the order xs and ys arrived in
    (DuckDB's `except all` fetch order is undefined). Each trial runs
    against a fork of `mode` that is absorbed only when the pair is kept:
    a rejected trial records no reorder class. Returns (unpaired xs,
    unpaired ys, number of noise values that differed)."""
    gx: dict = defaultdict(list)
    gy: dict = defaultdict(list)
    for x in xs:
        gx[group_key(x)].append(x)
    for y in ys:
        gy[group_key(y)].append(y)
    left_x, left_y, values = [], [], 0
    for key in sorted(set(gx) | set(gy)):
        la = sorted(((order_key(x), x) for x in gx.get(key, [])), key=lambda kx: kx[0])
        lb = sorted(((order_key(y), y) for y in gy.get(key, [])), key=lambda ky: ky[0])
        i = j = 0
        while i < len(la) and j < len(lb):
            probe = mode.fork() if mode is not None else None
            n = measure(la[i][1], lb[j][1], probe)
            if n is not None:
                if mode is not None:
                    mode.absorb(probe)
                values += n
                i += 1
                j += 1
            elif la[i][0] < lb[j][0]:
                left_x.append(la[i][1])
                i += 1
            else:
                left_y.append(lb[j][1])
                j += 1
        left_x.extend(x for _, x in la[i:])
        left_y.extend(y for _, y in lb[j:])
    return left_x, left_y, values


def _json_changes(a, b, pointer: str, out: list, noise: list | None = None, *,
                  group: str | None = None, mode: "_Mode | None" = None,
                  key_pointer: str | None = None) -> None:
    """Append (change, pointer, a, b) for every difference between a and b.

    Dicts recurse by key; lists compare as multisets of canonical JSON: a
    shuffled list is a pure permutation, trusted as equivalent (nothing
    appended; the caller sees it only via `mode.observed`) only when
    `mode.allow_reorder(group, key_pointer or pointer)` says so (ruling 4,
    Fix round 3) — otherwise it is one `reordered` change, exactly as
    before that ruling. An inserted element is one `added` at `<list>/[]`.
    Scalars must match in type AND value, so 1 vs 1.0 or 1 vs true is a
    change — UNLESS both are floats close to 12 significant digits, or both
    are strings that are numeric-text-close (ruling 1) or JSON-in-string
    equivalent (ruling 2, recursively, with the SAME reorder gating): any of
    those go to `noise` instead (list elements that differ only by such
    noise are paired first, via `_json_noise`).

    `key_pointer`, when given, is the pointer used for EVERY reorder-trust
    lookup in this call and its recursion, no matter how deep — set once by
    the ruling-2 JSON-in-string caller (`_leaf_equiv`) so a reorder found
    anywhere inside a decoded string value is keyed by that OUTER leaf's
    pointer, matching what the report (and a --write-noise file) show. A
    plain top-level call leaves it None, so the real, deepening `pointer` is
    used instead — unchanged from before this ruling existed."""
    if noise is None:
        noise = []
    rk = key_pointer if key_pointer is not None else pointer
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            p = f"{pointer}/{_escape(key)}"
            if key not in b:
                out.append(("removed", p, a[key], None))
            elif key not in a:
                out.append(("added", p, None, b[key]))
            else:
                _json_changes(a[key], b[key], p, out, noise, group=group, mode=mode,
                              key_pointer=key_pointer)
        return
    if isinstance(a, list) and isinstance(b, list):
        ca, cb = [_canon(x) for x in a], [_canon(x) for x in b]
        if ca == cb:
            return
        ma, mb = Counter(ca), Counter(cb)
        if ma == mb:
            if mode is not None and mode.allow_reorder(group, rk):
                return
            out.append(("reordered", pointer, None, None))
            return
        only_a = [json.loads(s) for s, n in sorted((ma - mb).items()) for _ in range(n)]
        only_b = [json.loads(s) for s, n in sorted((mb - ma).items()) for _ in range(n)]
        only_a, only_b, n_noise = _pair_noise(
            only_a, only_b,
            group_key=lambda x: _canon(_strip_floats(x)),
            order_key=lambda x: (tuple(_float_order(f) for f in _floats(x)), _canon(x)),
            measure=lambda x, y, m: _json_noise(x, y, group=group, mode=m, key_pointer=rk),
            mode=mode,
        )
        noise.append(n_noise)
        if not only_a and not only_b:
            if [_canon(_strip_floats(x)) for x in a] != [_canon(_strip_floats(x)) for x in b]:
                if mode is not None and mode.allow_reorder(group, rk):
                    return
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
    n = _leaf_equiv(a, b, rk, group, mode)
    if n is not None:
        noise.append(n)
        return
    out.append(("changed", pointer, a, b))


def _pattern(pointer: str) -> str:
    return "/".join("{fid}" if _FID_RE.fullmatch(s) else s for s in pointer.split("/"))


def _short(value) -> str | None:
    if value is None:
        return None
    s = _canon(value)
    return s if len(s) <= _MAX_VALUE_CHARS else s[:_MAX_VALUE_CHARS] + "…"


def _group_raw_changes(raw: list) -> dict | None:
    """Group raw (change, pointer, a, b) tuples into the {"changes": [...]}
    detail shape; None when raw is empty (used both by _json_detail and by
    the derived-hash post-pass, which filters a file's raw tuples and must
    regroup the remainder the SAME way, Fix round 3)."""
    if not raw:
        return None
    grouped: dict[tuple[str, str], dict] = {}
    for change, pointer, va, vb in raw:
        key = (_pattern(pointer), change)
        entry = grouped.setdefault(
            key, {"pattern": key[0], "change": change, "count": 0, "samples": []}
        )
        entry["count"] += 1
        if len(entry["samples"]) < _SAMPLES_PER_CHANGE:
            entry["samples"].append({"pointer": pointer, "a": _short(va), "b": _short(vb)})
    return {"changes": [grouped[k] for k in sorted(grouped)]}


def _json_raw_diff(pa: Path, pb: Path, wa, wb, group: str | None,
                   mode: "_Mode | None") -> tuple[list, list]:
    """(raw, noise): the UNGROUPED diff of two JSON files after masking.
    Exposed separately from _json_detail so the derived-hash post-pass
    (ruling 3) can re-examine and filter the exact tuples, then regroup the
    remainder with _group_raw_changes — the grouped/sampled "changes" shape
    _json_detail returns does not keep every instance, only a few samples."""
    a = _mask(json.loads(pa.read_text(encoding="utf-8")), wa)
    b = _mask(json.loads(pb.read_text(encoding="utf-8")), wb)
    raw: list = []
    noise: list = []
    _json_changes(a, b, "", raw, noise, group=group, mode=mode)
    return raw, noise


def _json_detail(pa: Path, pb: Path, wa, wb, group: str | None = None,
                 mode: "_Mode | None" = None) -> tuple[dict | None, int]:
    """(detail, float/numeric-text-noise values); detail is None when the
    two files hold the same JSON value after masking and after rulings 1-4
    (floats/numeric-text close to 12 significant digits, JSON-in-string
    equivalence, and — only under `mode` — a trusted reorder)."""
    raw, noise = _json_raw_diff(pa, pb, wa, wb, group, mode)
    return _group_raw_changes(raw), sum(noise)


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


def _group_cell(value):
    """A row-grouping contribution for a VARCHAR-lenient column: collapses
    the kinds of noise rulings 1-2 tolerate (so a row differing only that
    way still groups with its twin — `_row_noise` decides precisely),
    while anything else — including a value that merely LOOKS numeric,
    e.g. a sha256 that happens to be all digits — passes through unchanged,
    so a real mismatch there still splits the group; a row's OTHER,
    non-lenient columns (e.g. fact_id) still disambiguate what this alone
    cannot."""
    if isinstance(value, str):
        if _numeric_text(value) is not None:
            return "\x00num"
        try:
            parsed = json.loads(value)
        except ValueError:
            return value
        if isinstance(parsed, (list, dict)):
            return _canon(_multiset_canon(parsed))
    return value


def _noise_canon(value):
    """value with every float rounded to FLOAT_SIGNIFICANT_DIGITS
    significant digits and every list sorted into canonical order, at any
    depth: a deterministic SORT key that keeps a cell's noisy twins
    (float noise, a reordered list) next to each other. Ordering only —
    equality is always decided by `measure`."""
    if type(value) is float:
        return float(f"{value:.{FLOAT_SIGNIFICANT_DIGITS}g}")
    if isinstance(value, dict):
        return {k: _noise_canon(v) for k, v in value.items()}
    if isinstance(value, list):
        return sorted((_noise_canon(v) for v in value), key=_canon)
    return value


def _text_order(value) -> tuple:
    """Sort key for a VARCHAR-lenient cell (Fix round 4): numeric text by
    its value (like a float column), JSON-in-string by its noise-canonical
    form, anything else by itself; the raw text breaks every tie."""
    if value is None:
        return (0,)
    number = _numeric_text(value)
    if number is not None:
        return (1, _float_order(number), value)
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        parsed = None
    if isinstance(parsed, (list, dict)):
        return (2, _canon(_noise_canon(parsed)), value)
    return (3, value)


def _pair_rows(rows_a: list, rows_b: list, schema: list, group: str | None,
               mode: "_Mode | None") -> tuple[list, list, int]:
    """Pair parquet rows (each side's `except all` residue) that differ only
    by noise: DOUBLE/FLOAT columns by float noise, VARCHAR cells by
    numeric-text/JSON-in-string equivalence (rulings 1-2); every other
    column must match exactly (it is part of the group key). The order key
    covers every lenient cell — floats by value, VARCHAR by _text_order —
    and ends with the whole row's repr, a total order, so the result does
    not depend on DuckDB's fetch order (Fix round 4)."""
    cols = [name for name, _ in schema]
    types = [typ for _, typ in schema]
    floats = [i for i, typ in enumerate(types) if typ in FLOAT_TYPES]
    varchars = [i for i, typ in enumerate(types) if typ == "VARCHAR"]
    lenient = sorted(
        [(i, "DOUBLE", f"/{cols[i]}") for i in floats]
        + [(i, "VARCHAR", f"/{cols[i]}") for i in varchars]
    )
    exact = [i for i in range(len(cols)) if i not in floats and i not in varchars]

    def order_key(r) -> tuple:
        return (
            tuple(_float_order(r[i]) if typ in FLOAT_TYPES else _text_order(r[i])
                  for i, typ, _ in lenient),
            repr(r),
        )

    return _pair_noise(
        rows_a, rows_b,
        group_key=lambda r: repr([r[i] for i in exact] + [_group_cell(r[i]) for i in varchars]),
        order_key=order_key,
        measure=lambda ra, rb, m: _row_noise(ra, rb, lenient, group, m),
        mode=mode,
    )


def _parquet_detail(pa: Path, pb: Path, wa, wb, group: str | None = None,
                    mode: "_Mode | None" = None) -> tuple[dict | None, int]:
    """(detail, noise values); detail is None when the two files hold the
    same row multiset after masking: DOUBLE/FLOAT columns compared to 12
    significant digits, and — ruling 1/2, Fix round 3 — a VARCHAR column's
    cell too when both sides are numeric-text-close or JSON-in-string
    equivalent (a reorder inside gated by `mode` exactly as in a JSON
    file). Every other column compares exactly."""
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
        lenient = any(typ in FLOAT_TYPES or typ == "VARCHAR" for _, typ in schema_a)
        if lenient and only_a + only_b <= _NOISE_MAX_ROWS:
            left_a, left_b, noise = _pair_rows(
                con.execute(f"select * from ({sel_a} except all {sel_b})").fetchall(),
                con.execute(f"select * from ({sel_b} except all {sel_a})").fetchall(),
                schema_a, group, mode,
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


def _dataset_entries(doc) -> dict:
    """{file: entry} for datasets.json's list, keyed by the one field that
    never changes across equivalent exports (Fix round 3, ruling 3)."""
    if not isinstance(doc, dict):
        return {}
    return {
        d["file"]: d for d in doc.get("datasets", [])
        if isinstance(d, dict) and isinstance(d.get("file"), str)
    }


def _referent_excuses(file_status: dict[str, str], rel: str) -> bool:
    """Whether the file a derived hash/byte count describes can explain a
    difference in it (ruling 3, tightened in Fix round 4): only when the
    file exists in BOTH trees and compared equivalent-but-not-identical
    ("equivalent" — build stamps, float/numeric-text noise, JSON-in-string,
    JSON formatting — or "reordered"). A referent missing from either tree
    (no status, "only_a", "only_b") explains nothing, and a byte-IDENTICAL
    one cannot explain a different hash or size of itself — both stay
    "changed", as does a "changed" referent."""
    return file_status.get(rel) in _REFERENT_EXCUSES


def _resolve_datasets_derived_hash(raw: list, pa_doc, pb_doc,
                                   file_status: dict[str, str]) -> tuple[list, int]:
    """Drop json/datasets.json's /datasets/[] added/removed pairs whose
    entries differ ONLY in `bytes` (a derived file size) when the parquet
    they describe (data/<file>) is present in both trees and compared
    equivalent or reordered — never identical, never missing — in this SAME
    diff (ruling 3; _referent_excuses). Returns (filtered raw, values
    resolved)."""
    da, db = _dataset_entries(pa_doc), _dataset_entries(pb_doc)
    resolved_files: set[str] = set()
    for name in sorted(set(da) & set(db)):
        old, new = da[name], db[name]
        if old == new:
            continue
        diff_keys = {k for k in set(old) | set(new) if old.get(k) != new.get(k)}
        if diff_keys and diff_keys <= {"bytes"}:
            if _referent_excuses(file_status, f"data/{name}"):
                resolved_files.add(name)
    if not resolved_files:
        return raw, 0

    def _is_resolved(item: tuple) -> bool:
        change, pointer, va, vb = item
        if pointer != "/datasets/[]" or change not in ("added", "removed"):
            return False
        entry = vb if change == "added" else va
        return isinstance(entry, dict) and entry.get("file") in resolved_files

    return [item for item in raw if not _is_resolved(item)], len(resolved_files)


def _resolve_audit_derived_hash(raw: list, file_status: dict[str, str]) -> tuple[list, int]:
    """Drop json/budget_pdf_receipts_audit.json's /citation_sha256 change
    when json/citations.json is present in both trees and compared
    equivalent or reordered — never identical, never missing — in this SAME
    diff (ruling 3; _referent_excuses)."""
    if not _referent_excuses(file_status, "json/citations.json"):
        return raw, 0
    filtered = [item for item in raw
               if not (item[1] == "/citation_sha256" and item[0] == "changed")]
    return filtered, len(raw) - len(filtered)


_DERIVED_HASH_RESOLVERS = {
    "json/datasets.json": _resolve_datasets_derived_hash,
    "json/budget_pdf_receipts_audit.json": _resolve_audit_derived_hash,
}


def diff_trees(a: Path, b: Path, *, control: bool = False,
               noise_classes: "set[tuple[str, str]] | list[dict] | None" = None) -> dict:
    """Compare two data/site trees; return the report (see module docstring).

    report["counts"] has every status in STATUSES; report["files"] lists each
    file that is not byte-identical; report["groups"] tallies statuses per
    path group (a directory with 50+ files collapses to '<dir>/*<suffix>');
    report["float_noise"] = {files, values} counts the float/numeric-text
    values equal to 12 significant digits that were treated as equal (each
    file entry carries its own "float_noise"); report["derived_hash"] does
    the same for a content hash/byte count resolved via ruling 3 (each
    file's own "derived_hash" count). report["reorder_classes"] lists every
    (group, pointer pattern — fact IDs as {fid}, Fix round 5)
    pure-permutation class trusted this run, sorted, with
    counts — non-empty only with `control=True` or a `noise_classes` set
    (ruling 4); with neither, nothing is trusted and behaviour is as before
    these rulings existed. `noise_classes` also accepts the JSON list
    `load_noise_classes()` returns (each a {"path", "pointer", ...} dict)."""
    a, b = Path(a), Path(b)
    for root in (a, b):
        if not root.is_dir():
            raise NotADirectoryError(f"proof diff: {root} is not a directory")
    trusted = None
    if noise_classes is not None:
        trusted = {
            (c["path"], c["pointer"]) if isinstance(c, dict) else tuple(c)
            for c in noise_classes
        }
    mode = _Mode(control=control, trusted=trusted)
    wa, wb = _build_window(a), _build_window(b)
    files_a, files_b = set(_files(a)), set(_files(b))
    every = sorted(files_a | files_b)
    dir_counts = Counter(rel.rpartition("/")[0] for rel in every)
    counts = Counter({s: 0 for s in STATUSES})
    groups: dict[str, Counter] = {}
    files: dict[str, dict] = {}
    file_status: dict[str, str] = {}
    noise_files = noise_values = 0
    for rel in every:
        kind, group = _kind(rel), _group(rel, dir_counts)
        detail, noise, had_reorder = None, 0, False
        if rel not in files_b:
            status = "only_a"
        elif rel not in files_a:
            status = "only_b"
        elif _same_bytes(a / rel, b / rel):
            status = "identical"
        else:
            before = sum(mode.observed.values())
            if kind == "json":
                try:
                    detail, noise = _json_detail(a / rel, b / rel, wa, wb, group, mode)
                except ValueError:  # not JSON after all: compare as bytes
                    kind = "bytes"
            elif kind == "parquet":
                detail, noise = _parquet_detail(a / rel, b / rel, wa, wb, group, mode)
            if kind == "bytes":
                detail = {"sha256_a": _sha256_file(a / rel), "sha256_b": _sha256_file(b / rel)}
            had_reorder = sum(mode.observed.values()) > before
            status = "changed" if detail is not None else ("reordered" if had_reorder else "equivalent")
        file_status[rel] = status
        counts[status] += 1
        groups.setdefault(group, Counter({s: 0 for s in STATUSES}))[status] += 1
        if noise:
            noise_files += 1
            noise_values += noise
        if status != "identical":
            files[rel] = {"status": status, "kind": kind, "group": group, "detail": detail,
                          "float_noise": noise}

    # Ruling 3 (derived hashes): a second, explicit pass — the referenced
    # file's FINAL status must be known first, and the two known carriers
    # do not sort after everything they can reference (budget_pdf_receipts_
    # audit.json < citations.json alphabetically), so this cannot be folded
    # into the loop above.
    dh_files = dh_values = 0
    for rel, resolver in _DERIVED_HASH_RESOLVERS.items():
        entry = files.get(rel)
        if entry is None or entry["status"] != "changed" or entry["kind"] != "json":
            continue
        pa_path, pb_path = a / rel, b / rel
        # A throwaway Mode: this re-derives the SAME raw diff the main loop
        # already computed for `rel` (to get the ungrouped tuples, which
        # _json_detail discarded after grouping) — reusing `mode` itself
        # here would double-count any reorder this file already contributed
        # to `mode.observed`/report["reorder_classes"].
        fresh_mode = _Mode(control=mode.control, trusted=mode.trusted)
        raw, _ = _json_raw_diff(pa_path, pb_path, wa, wb, entry["group"], fresh_mode)
        if rel == "json/datasets.json":
            pa_doc = _mask(json.loads(pa_path.read_text(encoding="utf-8")), wa)
            pb_doc = _mask(json.loads(pb_path.read_text(encoding="utf-8")), wb)
            filtered, resolved = resolver(raw, pa_doc, pb_doc, file_status)
        else:
            filtered, resolved = resolver(raw, file_status)
        if not resolved:
            continue
        dh_files += 1
        dh_values += resolved
        new_detail = _group_raw_changes(filtered)
        new_status = "changed" if new_detail is not None else "equivalent"
        counts[entry["status"]] -= 1
        counts[new_status] += 1
        groups[entry["group"]][entry["status"]] -= 1
        groups[entry["group"]][new_status] += 1
        entry["status"] = new_status
        entry["detail"] = new_detail
        file_status[rel] = new_status

    reorder_classes = [
        {"path": g, "pointer": p, "count": n}
        for (g, p), n in sorted(mode.observed.items())
    ]
    return {
        "a": str(a),
        "b": str(b),
        "mode": "control" if control else ("noise-from" if trusted is not None else "plain"),
        "build_window": {
            side: (None if w is None else [w.lo.isoformat(), w.hi.isoformat()])
            for side, w in (("a", wa), ("b", wb))
        },
        "counts": dict(counts),
        "float_noise": {"files": noise_files, "values": noise_values},
        "derived_hash": {"files": dh_files, "values": dh_values},
        "reorder_classes": reorder_classes,
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


NOISE_FILE_SCHEMA = 1
#: Recorded in every noise file (Fix round 5) and required by
#: load_noise_classes: says how its class pointers are keyed.
NOISE_POINTER_GENERALISATION = "16-hex fact-ID pointer segments are {fid}"


def _classes_sha256(classes: list) -> str:
    """sha256 of the classes' canonical JSON (sorted keys, no whitespace,
    UTF-8): the noise file's timestamp-free content hash (Fix round 4)."""
    return hashlib.sha256(_canon(classes).encode("utf-8")).hexdigest()


def noise_file(report: dict) -> dict:
    """The --write-noise document for a `--control` report (Fix round 4).

    Refuses (ValueError) unless the report comes from a control run whose
    verdict is EQUAL: a control that found any non-noise difference — or
    a run that trusted nothing — vouches for no reorder class at all. The
    document records the verdict, both source trees (resolved) and a
    content hash of the classes, and nothing time-dependent, so the same
    control on the same trees writes a byte-identical file."""
    if report.get("mode") != "control":
        raise ValueError("proof diff --write-noise: only a --control report can vouch for"
                         " reorder classes")
    if not is_equal(report):
        raise ValueError("proof diff --write-noise: the control is DIFFERENT — it vouches for"
                         " no reorder class; noise file not written")
    classes = report["reorder_classes"]
    return {
        "schema_version": NOISE_FILE_SCHEMA,
        "verdict": "EQUAL",
        "a": str(Path(report["a"]).resolve()),
        "b": str(Path(report["b"]).resolve()),
        "pointer_generalisation": NOISE_POINTER_GENERALISATION,
        "classes_sha256": _classes_sha256(classes),
        "classes": classes,
    }


def write_noise_file(path: Path, report: dict) -> None:
    """Write noise_file(report) to path; raises (and writes nothing) when
    noise_file refuses."""
    doc = noise_file(report)
    Path(path).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_noise_classes(path: Path) -> list[dict]:
    """Read a --write-noise file back for --noise-from (ruling 4; Fix round
    4 format): the {"path", "pointer", "count"} reorder classes a prior
    `--control` run vouched for. Refuses a file that does not record a
    control verdict of EQUAL (including Fix round 3's bare-list format,
    which recorded no verdict at all), that does not name both source
    trees, or whose classes no longer match their recorded classes_sha256,
    or that predates Fix round 5's fact-ID generalisation (no
    `pointer_generalisation` marker, or a class pointer that still holds a
    raw 16-hex segment). `count` is provenance only — matching is by
    (path, pointer pattern) alone."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("verdict") != "EQUAL":
        raise ValueError(
            f"proof diff --noise-from: {path} does not record a control verdict of EQUAL —"
            f" only a passing `--control --write-noise` run vouches for reorder classes"
        )
    if not isinstance(data.get("a"), str) or not isinstance(data.get("b"), str):
        raise ValueError(f"proof diff --noise-from: {path} does not name both source trees"
                         f" ('a', 'b') of its control run")
    classes = data.get("classes")
    if not isinstance(classes, list):
        raise ValueError("proof diff --noise-from: 'classes' must be a JSON list of classes")
    for i, c in enumerate(classes):
        if not isinstance(c, dict) or not isinstance(c.get("path"), str) \
                or not isinstance(c.get("pointer"), str):
            raise ValueError(
                f"proof diff --noise-from: class {i} needs a string 'path' and 'pointer'"
            )
    if data.get("classes_sha256") != _classes_sha256(classes):
        raise ValueError(f"proof diff --noise-from: {path}'s classes do not match its"
                         f" classes_sha256 — edited after the control run?")
    if data.get("pointer_generalisation") != NOISE_POINTER_GENERALISATION:
        raise ValueError(
            f"proof diff --noise-from: {path} does not say its class pointers are fact-ID"
            f" generalised ({NOISE_POINTER_GENERALISATION!r}) — written before Fix round 5;"
            f" re-run the --control"
        )
    for i, c in enumerate(classes):
        if any(_FID_RE.fullmatch(seg) for seg in c["pointer"].split("/")):
            raise ValueError(
                f"proof diff --noise-from: class {i} pointer {c['pointer']!r} holds a raw"
                f" fact-ID segment — a lookup reads it as {{fid}}, so it could never match"
            )
    return classes


def _diff_items(report: dict) -> list[dict]:
    items = []
    for rel, entry in sorted(report["files"].items()):
        status = entry["status"]
        if status in ("equivalent", "reordered"):
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


_REPORT_LINES = 10
_REPORT_UNEXPECTED_LINES = 50


def _more_line(total: int, shown: int = _REPORT_LINES) -> list[str]:
    """Never truncate a list silently (Fix round 4): say how many more."""
    return [f"    +{total - shown:,} more (see --report)"] if total > shown else []


def format_report(report: dict, verdict: dict | None = None) -> list[str]:
    """Human-readable lines; the last line is the verdict."""
    c, fn, dh = report["counts"], report["float_noise"], report["derived_hash"]
    lines = [
        f"proof diff: A = {report['a']}",
        f"proof diff: B = {report['b']}",
        f"  build window A {report['build_window']['a']} · B {report['build_window']['b']}",
        f"  identical {c['identical']:,} · equivalent {c['equivalent']:,}"
        f" (build stamps, row order, JSON formatting, float/numeric-text noise or a"
        f" derived hash only) · reordered {c['reordered']:,} (control class)"
        f" · changed {c['changed']:,} · only in A {c['only_a']:,} · only in B {c['only_b']:,}",
        f"  equivalent (float noise): {fn['files']:,} file(s), {fn['values']:,} value(s)"
        f" equal to {FLOAT_SIGNIFICANT_DIGITS} significant digits",
        f"  equivalent (derived hash): {dh['files']:,} file(s), {dh['values']:,} value(s)"
        f" — a content hash or byte count of a file that compared equivalent",
    ]
    if report["reorder_classes"]:
        lines.append(f"  reordered (control class): {c['reordered']:,} file(s) across"
                     f" {len(report['reorder_classes']):,} class(es)")
        for rc in report["reorder_classes"][:_REPORT_LINES]:
            lines.append(f"    [{rc['path']}] {rc['pointer']} ×{rc['count']:,}")
        lines.extend(_more_line(len(report["reorder_classes"])))
    for group, gc in report["groups"].items():
        if not (gc["changed"] or gc["only_a"] or gc["only_b"] or gc["reordered"]):
            continue
        lines.append(f"  {group}: changed {gc['changed']:,} · reordered {gc['reordered']:,}"
                     f" · only in A {gc['only_a']:,} · only in B {gc['only_b']:,}")
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
        for (pattern, change), n in tally.most_common(_REPORT_LINES):
            lines.append(f"    {change} {pattern} ×{n:,}")
        lines.extend(_more_line(len(tally)))
    if verdict is None:
        lines.append("proof diff: EQUAL" if is_equal(report) else "proof diff: DIFFERENT")
        return lines
    for m in verdict["matched"]:
        lines.append(f"  rule {m['rule']} [{m['path']}] matched {m['count']:,}: {m['why']}")
    if verdict["unexpected"]:
        lines.append(f"  UNEXPECTED differences: {len(verdict['unexpected']):,}")
        for item in verdict["unexpected"][:_REPORT_UNEXPECTED_LINES]:
            lines.append(f"    {item['path']} {item['status']}"
                         f" {item['change'] or ''} {item['pattern'] or ''} ×{item['count']:,}".rstrip())
        lines.extend(_more_line(len(verdict["unexpected"]), _REPORT_UNEXPECTED_LINES))
    for u in verdict["unmet"]:
        lines.append(f"  UNMET required rule {u['rule']} [{u['path']}]: {u['why']}")
    lines.append("proof diff: PASS" if verdict["ok"] else "proof diff: FAIL")
    return lines


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


def snapshot(out_dir: Path, *, data_dir: Path, pg_dsn: str, scratch_db: str) -> dict:
    """Pin everything export-site reads into out_dir; return the manifest.

    Writes out_dir/{duckdb,parquet,site,raw_docs,manifest.jsonl} (APFS clones),
    out_dir/pg/<db>.dump, out_dir/snapshot.json and out_dir/env.sh, and restores
    the dump into a NEW database `scratch_db` on the same server. Refuses if
    out_dir or the scratch database already exists, out_dir resolves inside
    the lake (symlinks followed — a worktree's data/site is a symlink into
    the live lake), inside the SAM write window (:15-:20), while a writer
    holds the DuckDB file, or scratch_db is not named govbudget_proof_<name>.
    """
    # .resolve(), not .absolute(): a worktree's data/site is a symlink into
    # the live lake (Task 1), and .absolute() does not follow it — an
    # unresolved out_dir could sit textually outside data_dir while actually
    # landing inside it once the symlink is followed (2026-10 review finding).
    out_dir = Path(out_dir).resolve()
    data_dir = Path(data_dir).resolve()
    _check_sam_window("before the copy")
    if out_dir.exists():
        raise FileExistsError(f"proof snapshot: {out_dir} already exists")
    if out_dir == data_dir or data_dir in out_dir.parents:
        raise ValueError(f"proof snapshot: {out_dir} is inside the lake {data_dir}")
    if not _SCRATCH_DB_RE.fullmatch(scratch_db):
        raise ValueError(
            f"proof snapshot: scratch database name {scratch_db!r} must match"
            f" {_SCRATCH_DB_RE.pattern}"
        )
    _check_scratch_name(scratch_db)
    source_db = _resolve_dbname(pg_dsn)
    if scratch_db == source_db:
        raise ValueError("proof snapshot: the scratch database cannot be the source database")
    src_duckdb = data_dir / DUCKDB_REL
    for required in (src_duckdb, data_dir / MANIFEST_REL, *(data_dir / d for d in CLONED_DIRS)):
        if not required.exists():
            raise FileNotFoundError(f"proof snapshot: {required} is missing")
    wal = src_duckdb.with_name(src_duckdb.name + ".wal")
    if wal.exists():
        raise RuntimeError(f"proof snapshot: {wal} exists — a DuckDB write is unfinished")
    if _database_exists(pg_dsn, scratch_db):
        raise FileExistsError(
            f"proof snapshot: database {scratch_db} already exists — drop it"
            f" (dropdb) or choose another --scratch-db"
        )

    import duckdb

    # A read-only connection holds DuckDB's shared file lock for the whole
    # copy, so no writer (dbt build) can start mid-clone — and it fails here,
    # before anything is written, if a writer already holds the file.
    try:
        lock = duckdb.connect(str(src_duckdb), read_only=True)
    except duckdb.IOException as e:
        raise RuntimeError(f"proof snapshot: {src_duckdb} is being written ({e}); retry later") from e
    try:
        out_dir.mkdir(parents=True)
        (out_dir / DUCKDB_REL.parent).mkdir()
        _clone(src_duckdb, out_dir / DUCKDB_REL)
        for name in CLONED_DIRS:
            _clone(data_dir / name, out_dir / name)
        _clone(data_dir / MANIFEST_REL, out_dir / MANIFEST_REL)
    finally:
        lock.close()
    _check_sam_window(f"after the copy — delete {out_dir} and retry")

    duckdb_sha_at_copy = _sha256_file(out_dir / DUCKDB_REL)
    views = _rewrite_duckdb_views(out_dir / DUCKDB_REL, old_root=data_dir, new_root=out_dir)
    pg = _pg_snapshot(
        pg_dsn, scratch_db, out_dir / "pg",
        old_raw_docs=data_dir / "raw_docs", new_raw_docs=out_dir / "raw_docs",
        data_dir=data_dir,
    )
    env = {
        "GOVBUDGET_DATA": str(out_dir),
        "GOVBUDGET_DUCKDB": str(out_dir / DUCKDB_REL),
        "GOVBUDGET_PG_DSN": pg["scratch_dsn"],
    }
    manifest = {
        "schema_version": 1,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "out_dir": str(out_dir),
        "source": {"data_dir": str(data_dir), "pg_dsn": pg_dsn},
        "env": env,
        "duckdb": {
            "path": DUCKDB_REL.as_posix(),
            "sha256_at_copy": duckdb_sha_at_copy,
            "sha256": _sha256_file(out_dir / DUCKDB_REL),
            "views": views["views"],
            "views_rewritten": views["rewritten"],
        },
        "parquet": _parquet_digest(out_dir / "parquet"),
        "site": _tree_digest(out_dir / "site"),
        "raw_docs": _tree_digest(out_dir / "raw_docs"),
        "manifest_jsonl_sha256": _sha256_file(out_dir / MANIFEST_REL),
        "pg": pg,
    }
    (out_dir / SNAPSHOT_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / SNAPSHOT_ENV).write_text(_env_script(manifest), encoding="utf-8")
    return manifest


def _check_sam_window(stage: str) -> None:
    now = _now()
    if now.minute in SAM_WINDOW_MINUTES:
        raise RuntimeError(
            f"proof snapshot: refusing at {now:%H:%M} ({stage}) — the hourly SAM"
            " job writes data/parquet/sam at :17; run outside :15-:20"
        )


def _check_scratch_name(scratch_db: str) -> None:
    """The only database this tool may create is govbudget_proof_<name>
    (README, Global Constraints) — unconditionally, on every host.

    This used to be enforced only when the DSN's netloc looked local. That
    was unsound (2026-10 review finding): libpq lets a query parameter
    (`?host=...`) silently retarget a connection to a different server than
    the one the URI's host component names, so a DSN that merely LOOKS
    remote could defeat a host-based exemption and create an unprefixed
    database on the real server."""
    if not (
        scratch_db.startswith(SCRATCH_DB_PREFIX) and len(scratch_db) > len(SCRATCH_DB_PREFIX)
    ):
        raise ValueError(
            f"proof snapshot: a scratch database must be named"
            f" {SCRATCH_DB_PREFIX}<name>, not {scratch_db!r}"
        )


def _clone(src: Path, dst: Path) -> None:
    """APFS copy-on-write clone (macOS `cp -c`): seconds, no extra space."""
    done = subprocess.run(
        ["cp", "-c", "-R", str(src), str(dst)], capture_output=True, text=True
    )
    if done.returncode != 0:
        raise RuntimeError(
            f"proof snapshot: cp -c -R {src} {dst} failed: {done.stderr.strip()}"
            " (snapshots need APFS clones on one volume)"
        )


def _tree_digest(root: Path) -> dict:
    lines, total = [], 0
    files = _files(root)
    for rel in files:
        size = (root / rel).stat().st_size
        total += size
        lines.append(f"{rel}\t{size}\t{_sha256_file(root / rel)}\n")
    return {
        "files": len(files),
        "bytes": total,
        "sha256": hashlib.sha256("".join(lines).encode("utf-8")).hexdigest(),
    }


def _parquet_digest(root: Path) -> dict:
    import duckdb

    con = duckdb.connect()
    try:
        out = {}
        for rel in _files(root):
            path = root / rel
            rows = None
            if rel.endswith(".parquet"):
                rows = con.execute(
                    "select sum(num_rows) from parquet_file_metadata(?)", [str(path)]
                ).fetchone()[0]
            out[rel] = {
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
                "rows": int(rows) if rows is not None else None,
            }
        return out
    finally:
        con.close()


def _rewrite_duckdb_views(db_path: Path, *, old_root: Path, new_root: Path) -> dict:
    """Repoint every view that embeds old_root at new_root, in the copy only.

    DuckDB binds a view when it is created, so new_root's parquet must
    already exist (snapshot() clones it first). Raises if any view still names
    old_root afterwards."""
    import duckdb

    old, new = str(old_root) + "/", str(new_root) + "/"
    con = duckdb.connect(str(db_path))
    try:
        views = con.execute(
            "select view_name, sql from duckdb_views()"
            " where not internal and database_name = current_database()"
            " order by view_name"
        ).fetchall()
        rewritten = 0
        for name, sql in views:
            if old not in sql:
                continue
            if not sql.startswith("CREATE VIEW "):
                raise RuntimeError(f"proof snapshot: unexpected DDL for view {name}: {sql[:80]!r}")
            con.execute("CREATE OR REPLACE VIEW " + sql[len("CREATE VIEW "):].replace(old, new))
            rewritten += 1
        left = con.execute(
            "select view_name from duckdb_views()"
            " where not internal and database_name = current_database()"
            " and contains(sql, ?)",
            [old],
        ).fetchall()
        if left:
            raise RuntimeError(f"proof snapshot: views still read {old}: {sorted(r[0] for r in left)}")
        con.execute("checkpoint")
    finally:
        con.close()
    return {"views": len(views), "rewritten": rewritten}


def _pg_bin(name: str) -> str:
    env_dir = os.environ.get("GOVBUDGET_PG_BIN")
    if env_dir:
        cand = Path(env_dir) / name
        if cand.is_file():
            return str(cand)
        raise FileNotFoundError(f"proof snapshot: {cand} not found (GOVBUDGET_PG_BIN)")
    found = shutil.which(name)
    if found:
        return found
    cand = DEFAULT_PG_BIN / name
    if cand.is_file():
        return str(cand)
    raise FileNotFoundError(
        f"proof snapshot: {name} not found — set GOVBUDGET_PG_BIN to the Postgres bin directory"
    )


def _resolve_dbname(pg_dsn: str) -> str:
    """The database pg_dsn actually targets, after every libpq override.

    A query parameter (`?dbname=...`) wins over the URI path's database
    component — verified against a running server (2026-10 review finding)
    — so the target must never be read with urlsplit(pg_dsn).path: that
    silently disagrees with where the connection actually lands."""
    import psycopg

    dbname = psycopg.conninfo.conninfo_to_dict(pg_dsn).get("dbname")
    if not dbname:
        raise ValueError(f"proof snapshot: {pg_dsn!r} names no database")
    return dbname


def _with_database(dsn: str, database: str) -> str:
    """dsn, retargeted at `database` — even when a libpq query parameter
    (`?dbname=...`) would otherwise win over a bare URI-path replacement
    (2026-10 review finding: a naive urlsplit/urlunsplit path swap does not
    survive such a query parameter, so pg_restore could land on whatever the
    query named instead of the scratch database)."""
    import psycopg

    return psycopg.conninfo.make_conninfo(dsn, dbname=database)


def _assert_current_database(con, expected: str) -> None:
    """Defense in depth against a libpq override silently retargeting a
    connection (2026-10 review finding): refuse before touching anything if
    the live connection did not land on the database we meant to touch."""
    got = con.execute("select current_database()").fetchone()[0]
    if got != expected:
        raise RuntimeError(
            f"proof snapshot: connected to database {got!r}, expected"
            f" {expected!r} — refusing to touch it"
        )


def _assert_connected_to(dsn: str, expected: str) -> None:
    import psycopg

    with psycopg.connect(dsn) as con:
        _assert_current_database(con, expected)


def _database_exists(pg_dsn: str, name: str) -> bool:
    import psycopg

    with psycopg.connect(_with_database(pg_dsn, "postgres"), autocommit=True) as admin:
        return admin.execute(
            "select 1 from pg_database where datname = %s", (name,)
        ).fetchone() is not None


def _run(cmd: list[str]) -> str:
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"proof snapshot: {' '.join(cmd[:2])} failed: {done.stderr.strip()}")
    return done.stdout


def _pg_snapshot(
    pg_dsn: str, scratch_db: str, dump_dir: Path, *,
    old_raw_docs: Path, new_raw_docs: Path, data_dir: Path,
) -> dict:
    import psycopg
    from psycopg import sql

    source_db = _resolve_dbname(pg_dsn)
    scratch_dsn = _with_database(pg_dsn, scratch_db)
    dump_dir.mkdir()
    dump = dump_dir / f"{source_db}.dump"
    _run([_pg_bin("pg_dump"), "--format=custom", "--no-owner", "--no-privileges",
          f"--file={dump}", pg_dsn])
    with psycopg.connect(_with_database(pg_dsn, "postgres"), autocommit=True) as admin:
        admin.execute(sql.SQL("create database {}").format(sql.Identifier(scratch_db)))
    # Defense in depth before the destructive pg_restore: a libpq override
    # buried in pg_dsn could otherwise make scratch_dsn resolve somewhere
    # other than the database just created (2026-10 review finding).
    _assert_connected_to(scratch_dsn, scratch_db)
    _run([_pg_bin("pg_restore"), "--no-owner", "--no-privileges", "--exit-on-error",
          f"--dbname={scratch_dsn}", str(dump)])

    tables: dict[str, dict] = {}
    rewrites: dict[str, int] = {}
    with psycopg.connect(scratch_dsn) as con:
        _assert_current_database(con, scratch_db)
        # Pin the row-to-text rendering so the digests compare across sessions.
        con.execute("set time zone 'UTC'")
        con.execute("set datestyle = 'ISO, YMD'")
        con.execute("set extra_float_digits = 1")
        names = [r[0] for r in con.execute(
            "select table_name from information_schema.tables"
            " where table_schema = 'public' and table_type = 'BASE TABLE'"
            " order by table_name"
        ).fetchall()]
        for name in names:
            rows, digest = con.execute(sql.SQL(
                "select count(*), md5(coalesce(string_agg(h, '' order by h), ''))"
                " from (select md5(t::text) as h from {} t) s"
            ).format(sql.Identifier("public", name))).fetchone()
            tables[name] = {"rows": int(rows), "md5": digest}
        # Digests above describe the dump as taken. Only now repoint the
        # document paths at the cloned raw_docs, so export-site run against
        # this database never opens a live-lake file.
        if con.execute("select to_regclass('public.jbook_documents')").fetchone()[0]:
            old, new = str(old_raw_docs) + "/", str(new_raw_docs) + "/"
            cur = con.execute(
                "update jbook_documents set file_path = %s || substr(file_path, length(%s) + 1)"
                " where left(file_path, length(%s)) = %s",
                (new, old, old, old),
            )
            rewrites["jbook_documents.file_path"] = cur.rowcount
            live = str(data_dir) + "/"
            left = con.execute(
                "select count(*) from jbook_documents where left(file_path, length(%s)) = %s",
                (live, live),
            ).fetchone()[0]
            if left:
                raise RuntimeError(
                    f"proof snapshot: {left} jbook_documents.file_path row(s) still under {live}"
                )
        con.commit()
    return {
        "source_db": source_db,
        "scratch_db": scratch_db,
        "scratch_dsn": scratch_dsn,
        "dump": f"pg/{dump.name}",
        "dump_sha256": _sha256_file(dump),
        "pg_dump_version": _run([_pg_bin("pg_dump"), "--version"]).strip(),
        "tables": tables,
        "rewrites": rewrites,
    }


def _env_script(manifest: dict) -> str:
    env = manifest["env"]
    return (
        f"# Written by `govbudget proof snapshot` at {manifest['created_at']}.\n"
        "# Usage: source env.sh [RUN_DIR]\n"
        "#   no argument: point export-site/dbt/verify-* at this snapshot itself;\n"
        "#   RUN_DIR:     a `cp -c -R` clone of this snapshot to export into.\n"
        f'_proof_dir="${{1:-{env["GOVBUDGET_DATA"]}}}"\n'
        'export GOVBUDGET_DATA="$_proof_dir"\n'
        'export GOVBUDGET_DUCKDB="$_proof_dir/duckdb/govbudget.duckdb"\n'
        f"export GOVBUDGET_PG_DSN={shlex.quote(env['GOVBUDGET_PG_DSN'])}\n"
        "unset _proof_dir\n"
    )
