<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 5: Link-coverage tool, committed S0 baseline, and re-measured /methodology/ and /coverage/ weight stamps

**Spec:** §8 V9 (link coverage per page and site-wide; baseline committed at S0); overview §7 (definition (a)/(b)/(c)/(d), weakest-input rule, the two scores); §9 S0 ("`link-coverage` tool and committed baseline. Re-measure the `/methodology/` and `/coverage/` weight stamps"; "no `data/site` change"); §6.2 `/methodology/` row ("Build gate passes with the re-measured stamp and no raised ceiling"); §6.4 (the re-measured `/coverage/` headroom is one input to Task 19's choice of where the era table renders); §8 V8 (page weight: "`/methodology/` stamp re-measured at S0, no ceiling raised").

**Files:**
- Create: `src/govbudget/link_coverage.py`
- Create: `tests/test_link_coverage.py`
- Modify: `src/govbudget/cli.py`. Insert `cmd_link_coverage` after `cmd_export_budget_pdf_receipts` (currently `cli.py:2483-2485`). Insert the `link-coverage` parser after `ep.set_defaults(func=cmd_export_budget_pdf_receipts)` (currently `cli.py:3091`). Task 3 adds the `proof` CLI first, so the line numbers may shift; anchor on the quoted text.
- Create (generated): `data/research/link_coverage/baseline.json`
- Modify: `site/scripts/gates/build.mjs:641-647` (the `/methodology/` stamp comment and its `measured` string) and `:774-779` (the `/coverage/` stamp comment and its `measured` string). Comments and `measured` strings only; `maxRaw`/`maxGzip` do not change.

**Interfaces:**
- Consumes:
  - Task 1's environment: `uv run --project .` works from `GovBudget/`, `site/node_modules` is a real directory, and `data/site` is Task 1's symlink to the main lake export. Step 12 checks both and re-creates the link only if it is missing.
  - No code names from other tasks.
- Produces:
  - `govbudget.link_coverage.compute_link_coverage(site_dir: Path) -> dict` returns `{"site": {...}, "pages": {slug: {"figures","a","b","c","d","source_linked","pdf_highlighted","not_a"}}, "figures": {fid: "a"|"b"|"c"|"d"}}`.
  - `compare_to_baseline(report: dict, baseline: dict) -> list[str]` returns violations; `[]` means pass. It raises `ValueError` on a foreign or hand-edited baseline.
  - `baseline_from_report(report: dict) -> dict`, `absolute_violations(report: dict) -> list[str]`, and the constants `BASELINE_SCHEMA_VERSION = 1`, `CLASSES`, `SECTIONS`, `DEFINITION`.
  - CLI `govbudget link-coverage --site-dir DIR [--baseline FILE] [--write-baseline FILE]`. Its last line is exactly `link-coverage: PASS` or `link-coverage: FAIL`, and it exits 1 on FAIL. Without `--baseline` it applies only the baseline-free checks.
  - `data/research/link_coverage/baseline.json` (schema 1), consumed by Task 23's hard check: `uv run --project . python -m govbudget link-coverage --site-dir <S4/release data/site> --baseline data/research/link_coverage/baseline.json`.
  - Re-measured `measured` stamps for `/methodology/` and `/coverage/` in `site/scripts/gates/build.mjs`, which Task 19 budgets against.

**Baseline format (decided).** "No figure that had (a) loses it" can only be checked exactly if
the baseline holds every (a) fact ID:
- A hash of the sorted (a) list cannot test "is still a subset" once the S4 export adds about 16–21k new figures.
- Truncated prefixes can pass a figure that was actually lost.

So `figures` stores four sorted lists of 16-hex fact IDs, one per class, one ID per line
(`indent=0`), and `figures_sha256` guards against hand edits. This is the only large part of the
file: 905,978 bytes raw, about 431 KB gzip (git stores it compressed). That is in line with the
committed research files (up to 3.7 MB). One ID per line keeps the git diff per figure if the
baseline is ever re-cut. Per-page scores are not stored, because the tool recomputes them from any
site dir. Only the 125 slugs that are not fully PDF-highlighted are kept.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_link_coverage.py`:

```python
"""Link coverage (overview §7; spec §8 V9) on tiny synthetic site trees."""
import hashlib
import json
from pathlib import Path

import pytest

from govbudget import cli
from govbudget.link_coverage import (
    absolute_violations,
    baseline_from_report,
    compare_to_baseline,
    compute_link_coverage,
)

WB_BYTES = b"stand-in for a pinned comptroller workbook"
WB_SHA = hashlib.sha256(WB_BYTES).hexdigest()
XLSX_URL = "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx"
PDF_URL = "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/budget_justification/pdfs/x.pdf"


def fid(n: int) -> str:
    return f"{n:016x}"


def workbook(sha: str = WB_SHA) -> dict:
    return {"kind": "workbook", "sha256": sha, "sheet": "Exhibit P-1", "cells": "J10",
            "official_url": XLSX_URL, "inputs": None}


def derived(*inputs: str) -> dict:
    return {"kind": "derived", "inputs": json.dumps(list(inputs)),
            "formula": "sum(budget_lines.amount_thousands)", "official_url": None}


def receipt(complete: bool) -> dict:
    return {"amount_thousands": 1.0, "matched_amount_thousands": 1.0 if complete else 0.0,
            "complete": complete, "blank_zero_count": 0, "unmatched_count": 0 if complete else 1,
            "parts": []}


def write_site(root: Path, *, citations: dict, receipts: dict, pages: dict,
               audit_sha: str | None = "auto", workbook_bytes: bytes = WB_BYTES) -> Path:
    json_dir = root / "json"
    (json_dir / "program_details").mkdir(parents=True)
    (json_dir / "budget-pdf-receipts" / "v2").mkdir(parents=True)
    (root / "workbooks").mkdir()
    (root / "workbooks" / f"{WB_SHA}.xlsx").write_bytes(workbook_bytes)
    text = json.dumps(citations, sort_keys=True)
    (json_dir / "citations.json").write_text(text)
    shards: dict[str, dict] = {}
    for fact, rec in receipts.items():
        shards.setdefault(fact[:3], {})[fact] = rec
    for prefix, shard in shards.items():
        (json_dir / "budget-pdf-receipts" / "v2" / f"{prefix}.json").write_text(json.dumps(shard))
    for slug, detail in pages.items():
        (json_dir / "program_details" / f"{slug}.json").write_text(json.dumps(detail))
    if audit_sha is not None:
        sha = hashlib.sha256(text.encode()).hexdigest() if audit_sha == "auto" else audit_sha
        (json_dir / "budget_pdf_receipts_audit.json").write_text(json.dumps({"citation_sha256": sha}))
    return root


def page(*, lines=(), decade=(), cards=(), diff=None, recon=None, disc=None, split_lines=()) -> dict:
    """A program sidecar carrying only the budget-figure sections the tool reads."""
    split = None
    if recon or disc or split_lines:
        split = {"reconciliation": {"fid": recon} if recon else None,
                 "disc": {"fid": disc} if disc else None,
                 "lines": [{"fid": f} for f in split_lines] or None}
    return {
        "budget_lines": [{"fact_id": f} for f in lines],
        "decade_series": {"actuals": [{"fid": f} for f in decade]},
        "summary": {"cards": [{"fid": f} for f in cards] + [{"fid": None}]},
        "book_diff": {"fid": diff} if diff else None,
        "fy26_split": split,
        "details": [{"fact_id": fid(999)}],  # J-book detail rows are not budget figures
    }


CITATIONS = {
    fid(1): workbook(),                      # complete receipt -> a
    fid(2): workbook(),                      # partial receipt -> b
    fid(3): workbook(),                      # no receipt -> b
    fid(4): derived(fid(1)),                 # own complete receipt -> a
    fid(5): derived(fid(1), fid(2)),         # weakest input b -> b
    fid(6): derived(fid(1), fid(4)),         # all inputs a -> a
    fid(7): workbook(sha="f" * 64),          # workbook not pinned in workbooks/ -> c
    fid(9): {"kind": "jbook_pdf", "page_number": 3, "x0": 10.0, "official_url": PDF_URL},  # -> a
    fid(10): {"kind": "jbook_pdf", "page_number": None, "x0": None, "official_url": PDF_URL},  # -> c
    fid(11): derived(fid(10), fid(1)),       # weakest input c -> c
    fid(12): {"kind": "derived", "inputs": "[]", "formula": "x", "official_url": None},  # -> d
    fid(13): derived(fid(13)),               # cycle -> d
    fid(14): derived(fid(1), "https://example.gov/source"),  # URL input -> c
    fid(999): {"kind": "jbook_narrative", "page_number": None, "official_url": None},
}
RECEIPTS = {fid(1): receipt(True), fid(2): receipt(False), fid(4): receipt(True)}


def test_each_figure_takes_its_best_link_and_derived_takes_the_weakest_input(tmp_path):
    pages = {
        "AAA": page(lines=[fid(1), fid(2), None], decade=[fid(3)], cards=[fid(9)]),
        "BBB": page(decade=[fid(4)], diff=fid(5), cards=[fid(6)]),
        "CCC": page(disc=fid(7), recon=fid(8), split_lines=[fid(11), fid(12), fid(13), fid(14)]),
    }
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS, pages=pages))
    assert report["figures"] == {
        fid(1): "a", fid(2): "b", fid(3): "b", fid(4): "a", fid(5): "b", fid(6): "a",
        fid(7): "c", fid(8): "d", fid(9): "a", fid(11): "c", fid(12): "d", fid(13): "d",
        fid(14): "c", "nofid:AAA:budget_lines:2": "d",
    }
    assert fid(999) not in report["figures"]


def test_scores_count_distinct_figures_per_page_and_site(tmp_path):
    pages = {
        "AAA": page(lines=[fid(1)], cards=[fid(1)], decade=[fid(3)]),  # fid(1) shown twice
        "BBB": page(decade=[fid(4)], cards=[fid(6)]),
    }
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS, pages=pages))
    assert report["pages"]["AAA"] == {"figures": 2, "a": 1, "b": 1, "c": 0, "d": 0,
                                      "source_linked": 1.0, "pdf_highlighted": 0.5,
                                      "not_a": {fid(3): "b"}}
    assert report["pages"]["BBB"]["pdf_highlighted"] == 1.0
    site = report["site"]
    assert (site["figures"], site["a"], site["b"], site["c"], site["d"]) == (4, 3, 1, 0, 0)
    assert site["source_linked"] == 1.0 and site["pdf_highlighted"] == 0.75
    assert (site["pages"], site["pages_fully_source_linked"], site["pages_fully_pdf_highlighted"]) == (2, 2, 1)
    assert site["occurrences"]["budget_lines"] == {"a": 1, "b": 0, "c": 0, "d": 0}
    assert site["occurrences"]["summary_cards"] == {"a": 2, "b": 0, "c": 0, "d": 0}
    assert site["occurrences"]["decade_series"] == {"a": 1, "b": 1, "c": 0, "d": 0}
    assert site["receipts_match_citations"] is True and site["workbooks_pinned"] == 1
    assert (site["workbook_citations"], site["workbook_citations_pdf_highlighted"]) == (4, 1)


def test_a_workbook_that_does_not_hash_to_its_name_is_not_pinned(tmp_path):
    pages = {"AAA": page(lines=[fid(1), fid(3)])}
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS,
                                              pages=pages, workbook_bytes=b"edited copy"))
    assert report["site"]["workbooks_pinned"] == 0
    assert report["figures"] == {fid(1): "a", fid(3): "c"}  # the receipt still highlights fid(1)


def test_baseline_round_trip_passes_and_new_or_upgraded_figures_are_allowed(tmp_path):
    before = compute_link_coverage(write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                                              pages={"AAA": page(lines=[fid(1), fid(2)])}))
    baseline = json.loads(json.dumps(baseline_from_report(before)))
    assert baseline["figures"] == {"a": [fid(1)], "b": [fid(2)], "c": [], "d": []}
    assert baseline["pages_not_fully_pdf_highlighted"] == ["AAA"]
    assert compare_to_baseline(before, baseline) == []
    upgraded = dict(RECEIPTS, **{fid(2): receipt(True)})
    after = compute_link_coverage(write_site(tmp_path / "s4", citations=CITATIONS, receipts=upgraded,
                                             pages={"AAA": page(lines=[fid(1), fid(2)], decade=[fid(4)])}))
    assert compare_to_baseline(after, baseline) == []


def test_losing_a_receipt_or_unpublishing_an_a_figure_is_a_violation(tmp_path):
    before = compute_link_coverage(write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                                              pages={"AAA": page(lines=[fid(1)], decade=[fid(4)])}))
    baseline = baseline_from_report(before)
    degraded = dict(RECEIPTS, **{fid(1): receipt(False)})
    after = compute_link_coverage(write_site(tmp_path / "s4", citations=CITATIONS, receipts=degraded,
                                             pages={"AAA": page(lines=[fid(1)])}))
    assert compare_to_baseline(after, baseline) == [
        f"lost PDF receipt: {fid(1)} was (a) in the baseline, now (b)",
        f"lost PDF receipt: {fid(4)} was (a) in the baseline, no longer published",
    ]


def test_unlinked_budget_figures_fail_without_a_baseline(tmp_path):
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS,
                                              pages={"CCC": page(lines=[fid(1)], disc=fid(7), recon=fid(8))}))
    assert absolute_violations(report) == [
        f"not source-linked: {fid(7)} is (c) on /program/CCC/",
        f"not source-linked: {fid(8)} is (d) on /program/CCC/",
        "site source-linked share 0.333333 < 1.0: 2 of 3 budget figures are (c) or (d)",
    ]


def test_a_receipt_store_built_for_other_citations_is_a_violation(tmp_path):
    stale = compute_link_coverage(write_site(tmp_path / "stale", citations=CITATIONS, receipts=RECEIPTS,
                                             pages={"AAA": page(lines=[fid(1)])}, audit_sha="0" * 64))
    assert stale["site"]["receipts_match_citations"] is False
    assert absolute_violations(stale) == [
        "receipt store is stale: json/budget_pdf_receipts_audit.json was built for a "
        "different citations.json (re-run export-budget-pdf-receipts)"
    ]
    unaudited = compute_link_coverage(write_site(tmp_path / "none", citations=CITATIONS, receipts=RECEIPTS,
                                                 pages={"AAA": page(lines=[fid(1)])}, audit_sha=None))
    assert unaudited["site"]["receipts_match_citations"] is None
    assert absolute_violations(unaudited) == []


def test_a_hand_edited_or_foreign_baseline_is_refused(tmp_path):
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS,
                                              pages={"AAA": page(lines=[fid(1), fid(4)])}))
    baseline = baseline_from_report(report)
    baseline["figures"]["a"].remove(fid(4))
    with pytest.raises(ValueError, match="figures_sha256"):
        compare_to_baseline(report, baseline)
    with pytest.raises(ValueError, match="schema"):
        compare_to_baseline(report, {**baseline_from_report(report), "schema_version": 2})


def test_a_site_dir_without_program_sidecars_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="program sidecars"):
        compute_link_coverage(tmp_path)


def test_cli_writes_a_baseline_then_passes_and_fails_against_it(tmp_path, capsys):
    s0 = write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                    pages={"AAA": page(lines=[fid(1), fid(2)])})
    target = tmp_path / "research" / "baseline.json"
    cli.main(["link-coverage", "--site-dir", str(s0), "--write-baseline", str(target)])
    out = capsys.readouterr().out
    assert "link-coverage: 2 budget figures on 1 program pages: a 1 · b 1 · c 0 · d 0;" in out
    assert out.rstrip().endswith("link-coverage: PASS")
    text = target.read_text()
    assert f'"{fid(1)}"' in text.splitlines()  # one fact ID per line: per-figure git diffs
    cli.main(["link-coverage", "--site-dir", str(s0), "--baseline", str(target)])
    assert capsys.readouterr().out.rstrip().endswith("link-coverage: PASS")

    s4 = write_site(tmp_path / "s4", citations=CITATIONS, receipts=dict(RECEIPTS, **{fid(1): receipt(False)}),
                    pages={"AAA": page(lines=[fid(1), fid(2)])})
    with pytest.raises(SystemExit) as exc:
        cli.main(["link-coverage", "--site-dir", str(s4), "--baseline", str(target)])
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert f"  - lost PDF receipt: {fid(1)} was (a) in the baseline, now (b)" in out
    assert out.rstrip().endswith("link-coverage: FAIL")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget`):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_link_coverage.py -q
```

Expected: collection error, nothing runs:

```
E   ModuleNotFoundError: No module named 'govbudget.link_coverage'
ERROR tests/test_link_coverage.py
1 error in 0.0Xs
```

- [ ] **Step 3: Write the module**

Create `src/govbudget/link_coverage.py`:

```python
"""Link coverage of published budget figures (overview §7; spec §8 V9).

Every budget figure on a program page gets its best link class:

  a  PDF-highlighted: a v2 budget PDF receipt with ``complete: true`` (page and
     glyph box in the government PDF), or a ``jbook_pdf`` citation that carries a
     page number and a box.
  b  a workbook cell in a sha-pinned copy of the official workbook: a
     ``workbook`` citation whose ``sha256`` names a file in ``<site>/workbooks/``
     that really hashes to that name, with a sheet and cells.
  c  an official URL only.
  d  nothing: no citation, no fact ID, or no usable inputs.

A ``derived`` figure without its own complete receipt takes the weakest class
among its inputs (a > b > c > d); a derived figure WITH a complete receipt is
(a), which by construction (``budget_pdf_receipts.combine_receipts``) means
every input is (a). Two scores, per program page and site-wide, over distinct
fact IDs: source-linked = (a + b) / n, PDF-highlighted = a / n.

Budget figures are the money figures a program sidecar renders from the
comptroller P-1/R-1/P-1R family: ``budget_lines[].fact_id``,
``decade_series[*][].fid``, ``summary.cards[].fid``, ``book_diff.fid``,
``fy26_split.reconciliation.fid``, ``fy26_split.disc.fid`` and
``fy26_split.lines[].fid``. J-book detail and narrative rows are not budget
figures (overview §7, gap C).

The committed baseline (``data/research/link_coverage/baseline.json``) stores
every figure's class as sorted fact-ID lists, so "no figure that had (a) loses
it" is checked exactly, figure by figure, not through a hash or a count.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

CLASSES = ("a", "b", "c", "d")
_RANK = {cls: rank for rank, cls in enumerate(CLASSES)}
_FID = re.compile(r"[0-9a-f]{16}")
BASELINE_SCHEMA_VERSION = 1
SECTIONS = (
    "budget_lines",
    "decade_series",
    "summary_cards",
    "book_diff",
    "fy26_reconciliation",
    "fy26_disc",
    "fy26_lines",
)
DEFINITION = (
    "Per budget figure on a program page: a = complete PDF receipt (page + highlighted "
    "location), b = workbook cell in a sha-pinned workbook, c = official URL only, "
    "d = nothing; derived figures take the weakest class among their inputs. "
    "source_linked = (a+b)/n, pdf_highlighted = a/n, over distinct fact IDs."
)


def _page_figures(detail: dict) -> list[tuple[str, object]]:
    """(section, fact id) for every budget figure one program sidecar renders."""
    out: list[tuple[str, object]] = []
    for row in detail.get("budget_lines") or []:
        out.append(("budget_lines", row.get("fact_id")))
    for points in (detail.get("decade_series") or {}).values():
        for point in points or []:
            out.append(("decade_series", point.get("fid")))
    for card in (detail.get("summary") or {}).get("cards") or []:
        if card.get("fid"):
            out.append(("summary_cards", card["fid"]))
    diff = detail.get("book_diff")
    for entry in diff if isinstance(diff, list) else [diff]:
        if isinstance(entry, dict) and entry.get("fid"):
            out.append(("book_diff", entry["fid"]))
    split = detail.get("fy26_split")
    if isinstance(split, dict):
        for key, section in (("reconciliation", "fy26_reconciliation"), ("disc", "fy26_disc")):
            if isinstance(split.get(key), dict) and split[key].get("fid"):
                out.append((section, split[key]["fid"]))
        for line in split.get("lines") or []:
            if isinstance(line, dict) and line.get("fid"):
                out.append(("fy26_lines", line["fid"]))
    return out


def _has_url(citation: dict, *keys: str) -> bool:
    return any(str(citation.get(key) or "").startswith(("http://", "https://", "/pdfs/")) for key in keys)


class _Classifier:
    def __init__(self, citations: dict, receipts: dict, pinned_workbooks: set[str]):
        self.citations = citations
        self.receipts = receipts
        self.pinned = pinned_workbooks
        self.memo: dict[str, str] = {}

    def classify(self, fid: str, active: frozenset[str] = frozenset()) -> str:
        if fid in active:
            return "d"  # a derivation cycle links to nothing
        if fid in self.memo:
            return self.memo[fid]
        citation = self.citations.get(fid)
        receipt = self.receipts.get(fid)
        if citation is None:
            out = "d"
        elif isinstance(receipt, dict) and receipt.get("complete") is True:
            out = "a"
        elif citation.get("kind") == "derived":
            out = self._derived(fid, citation, active)
        else:
            out = self._leaf(citation)
        self.memo[fid] = out
        return out

    def _leaf(self, citation: dict) -> str:
        kind = citation.get("kind")
        if kind == "workbook":
            if citation.get("sha256") in self.pinned and citation.get("sheet") and citation.get("cells"):
                return "b"
            return "c" if _has_url(citation, "official_url") else "d"
        if kind == "jbook_pdf" and citation.get("page_number") is not None and citation.get("x0") is not None:
            return "a"
        return "c" if _has_url(citation, "official_url", "hosted_pdf_url") else "d"

    def _derived(self, fid: str, citation: dict, active: frozenset[str]) -> str:
        try:
            inputs = json.loads(citation.get("inputs") or "[]")
        except ValueError:
            return "d"
        if not isinstance(inputs, list) or not inputs:
            return "d"
        classes = []
        for item in inputs:
            if isinstance(item, str) and _FID.fullmatch(item):
                classes.append(self.classify(item, active | {fid}))
            elif isinstance(item, str) and item.startswith(("http://", "https://")):
                classes.append("c")
            else:
                classes.append("d")
        return max(classes, key=_RANK.__getitem__)


def _scores(classes: dict[str, str]) -> dict:
    counts = Counter(classes.values())
    n = len(classes)
    out = {"figures": n, **{cls: counts.get(cls, 0) for cls in CLASSES}}
    out["source_linked"] = round((out["a"] + out["b"]) / n, 6) if n else None
    out["pdf_highlighted"] = round(out["a"] / n, 6) if n else None
    return out


def compute_link_coverage(site_dir: Path) -> dict:
    """Classify every budget figure on every program page of an exported site dir.

    Returns {"site": {...}, "pages": {slug: {...}}, "figures": {fid: "a"|"b"|"c"|"d"}}.
    Raises FileNotFoundError when the site dir has no program sidecars or no citations.
    """
    site_dir = Path(site_dir)
    json_dir = site_dir / "json"
    detail_paths = sorted((json_dir / "program_details").glob("*.json"))
    if not detail_paths:
        raise FileNotFoundError(f"no program sidecars under {json_dir / 'program_details'}")
    citations_bytes = (json_dir / "citations.json").read_bytes()
    citations = json.loads(citations_bytes)
    citations_sha256 = hashlib.sha256(citations_bytes).hexdigest()
    receipts: dict = {}
    for shard in sorted((json_dir / "budget-pdf-receipts" / "v2").glob("*.json")):
        receipts.update(json.loads(shard.read_text()))
    pinned = {
        path.stem
        for path in (site_dir / "workbooks").glob("*.xlsx")
        if hashlib.sha256(path.read_bytes()).hexdigest() == path.stem
    }
    classify = _Classifier(citations, receipts, pinned).classify

    figures: dict[str, str] = {}
    pages: dict[str, dict] = {}
    occurrences = {section: dict.fromkeys(CLASSES, 0) for section in SECTIONS}
    for path in detail_paths:
        slug = path.stem
        page: dict[str, str] = {}
        for index, (section, fid) in enumerate(_page_figures(json.loads(path.read_text()))):
            if isinstance(fid, str) and _FID.fullmatch(fid):
                key, cls = fid, classify(fid)
            else:
                key, cls = f"nofid:{slug}:{section}:{index}", "d"
            occurrences[section][cls] += 1
            page[key] = cls
            figures[key] = cls
        pages[slug] = _scores(page) | {"not_a": {fid: cls for fid, cls in sorted(page.items()) if cls != "a"}}

    audit_path = json_dir / "budget_pdf_receipts_audit.json"
    receipts_match = None
    if audit_path.exists():
        receipts_match = json.loads(audit_path.read_text()).get("citation_sha256") == citations_sha256
    meta_path = json_dir / "site_meta.json"
    built_at = json.loads(meta_path.read_text()).get("built_at") if meta_path.exists() else None

    site = _scores(figures)
    site.update({
        "pages": len(pages),
        "pages_with_figures": sum(1 for p in pages.values() if p["figures"]),
        "pages_fully_source_linked": sum(1 for p in pages.values() if p["figures"] and p["c"] + p["d"] == 0),
        "pages_fully_pdf_highlighted": sum(1 for p in pages.values() if p["figures"] and p["a"] == p["figures"]),
        "occurrences": occurrences,
        "citations": len(citations),
        "workbook_citations": sum(1 for c in citations.values() if c.get("kind") == "workbook"),
        "workbook_citations_pdf_highlighted": sum(
            1 for f, c in citations.items()
            if c.get("kind") == "workbook" and (receipts.get(f) or {}).get("complete") is True
        ),
        "citations_sha256": citations_sha256,
        "receipts": len(receipts),
        "receipts_match_citations": receipts_match,
        "workbooks_pinned": len(pinned),
        "export_built_at": built_at,
    })
    return {"site": site, "pages": pages, "figures": dict(sorted(figures.items()))}


def _figures_digest(figures: dict[str, str]) -> str:
    text = "".join(f"{fid} {cls}\n" for fid, cls in sorted(figures.items()))
    return hashlib.sha256(text.encode()).hexdigest()


def baseline_from_report(report: dict) -> dict:
    """The committed-baseline form of a report: every figure's class, exactly."""
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "definition": DEFINITION,
        "site": report["site"],
        "pages_not_fully_pdf_highlighted": sorted(
            slug for slug, page in report["pages"].items() if page["a"] != page["figures"]
        ),
        "figures": {cls: sorted(f for f, c in report["figures"].items() if c == cls) for cls in CLASSES},
        "figures_sha256": _figures_digest(report["figures"]),
    }


def absolute_violations(report: dict) -> list[str]:
    """Checks that need no baseline: every budget figure is (a) or (b); receipts match citations."""
    out = []
    for slug, page in sorted(report["pages"].items()):
        for fid, cls in page["not_a"].items():
            if cls in ("c", "d"):
                out.append(f"not source-linked: {fid} is ({cls}) on /program/{slug}/")
    site = report["site"]
    unlinked = site["figures"] - site["a"] - site["b"]
    if unlinked > 0:
        out.append(
            f"site source-linked share {site['source_linked']} < 1.0: "
            f"{unlinked} of {site['figures']} budget figures are (c) or (d)"
        )
    if site.get("receipts_match_citations") is False:
        out.append(
            "receipt store is stale: json/budget_pdf_receipts_audit.json was built for a "
            "different citations.json (re-run export-budget-pdf-receipts)"
        )
    return out


def compare_to_baseline(report: dict, baseline: dict) -> list[str]:
    """Violations of V9 against a committed baseline; [] means the check passes.

    Raises ValueError when the baseline is not schema 1 or its figure lists do not
    reproduce its figures_sha256 (a hand-edited or truncated file).
    """
    if baseline.get("schema_version") != BASELINE_SCHEMA_VERSION:
        raise ValueError(f"unsupported link-coverage baseline schema: {baseline.get('schema_version')!r}")
    recorded = {fid: cls for cls in CLASSES for fid in baseline["figures"].get(cls, [])}
    if _figures_digest(recorded) != baseline.get("figures_sha256"):
        raise ValueError("link-coverage baseline figures do not match its figures_sha256")
    violations = []
    now = report["figures"]
    for fid in baseline["figures"]["a"]:
        cls = now.get(fid)
        if cls != "a":
            state = "no longer published" if cls is None else f"now ({cls})"
            violations.append(f"lost PDF receipt: {fid} was (a) in the baseline, {state}")
    violations.extend(absolute_violations(report))
    return violations
```

- [ ] **Step 4: Run the tests: the module tests pass, the CLI test still fails**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_link_coverage.py -q
```

Expected: `1 failed, 9 passed`. The failure is in
`test_cli_writes_a_baseline_then_passes_and_fails_against_it`, with captured stderr ending in:

```
govbudget: error: argument cmd: invalid choice: 'link-coverage' (choose from ...)
FAILED tests/test_link_coverage.py::test_cli_writes_a_baseline_then_passes_and_fails_against_it
1 failed, 9 passed
```

- [ ] **Step 5: Add the CLI command and parser**

In `src/govbudget/cli.py`, edit 1 is currently at `:2483-2488`. Before:

```python
def cmd_export_budget_pdf_receipts(args) -> None:
    """Refresh PDF-first evidence for an already completed site artifact bundle."""
    _export_budget_pdf_evidence(site_dir=args.site_dir, manifest=args.manifest, cache_dir=args.cache_dir)


def cmd_verify_phase5b2(args) -> None:
```

After:

```python
def cmd_export_budget_pdf_receipts(args) -> None:
    """Refresh PDF-first evidence for an already completed site artifact bundle."""
    _export_budget_pdf_evidence(site_dir=args.site_dir, manifest=args.manifest, cache_dir=args.cache_dir)


def cmd_link_coverage(args) -> None:
    """Overview §7 / spec V9: link class of every budget figure on the program pages."""
    import json

    from govbudget.link_coverage import (
        absolute_violations,
        baseline_from_report,
        compare_to_baseline,
        compute_link_coverage,
    )

    def pct(share):
        return "n/a" if share is None else f"{100 * share:.2f}%"

    report = compute_link_coverage(args.site_dir)
    site = report["site"]
    print(
        f"link-coverage: {site['figures']:,} budget figures on {site['pages']:,} program pages:"
        f" a {site['a']:,} · b {site['b']:,} · c {site['c']:,} · d {site['d']:,};"
        f" source-linked {pct(site['source_linked'])},"
        f" PDF-highlighted {pct(site['pdf_highlighted'])};"
        f" {site['pages_fully_pdf_highlighted']:,} of {site['pages']:,} pages fully PDF-highlighted"
    )
    if args.write_baseline is not None:
        args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(baseline_from_report(report), indent=0, sort_keys=True) + "\n"
        args.write_baseline.write_text(text)
        print(f"link-coverage: baseline -> {args.write_baseline} ({len(text.encode()):,} bytes)")
    if args.baseline is not None:
        baseline = json.loads(args.baseline.read_text())
        violations = compare_to_baseline(report, baseline)
        print(f"link-coverage: compared against {args.baseline} ({len(baseline['figures']['a']):,} baseline (a) figures)")
    else:
        violations = absolute_violations(report)
    for line in violations[:50]:
        print(f"  - {line}")
    if len(violations) > 50:
        print(f"  ... and {len(violations) - 50:,} more")
    print(f"link-coverage: {len(violations):,} violation(s)")
    if violations:
        print("link-coverage: FAIL")
        sys.exit(1)
    print("link-coverage: PASS")


def cmd_verify_phase5b2(args) -> None:
```

Edit 2 is currently at `:3090-3093`. Before:

```python
    ep.add_argument("--cache-dir", type=Path, default=config.ROOT / "tmp" / "pdfs")
    ep.set_defaults(func=cmd_export_budget_pdf_receipts)

    v5b1 = sub.add_parser("verify-phase5b1", help="phase 5B-1 acceptance gates (citation export)")
```

After:

```python
    ep.add_argument("--cache-dir", type=Path, default=config.ROOT / "tmp" / "pdfs")
    ep.set_defaults(func=cmd_export_budget_pdf_receipts)

    lc = sub.add_parser(
        "link-coverage",
        help="overview §7 / spec V9: classify every program-page budget figure"
             " (a PDF-highlighted, b workbook cell, c URL only, d nothing)",
    )
    lc.add_argument("--site-dir", type=Path, required=True, dest="site_dir",
                    help="an exported site dir (data/site or a snapshot's copy)")
    lc.add_argument("--baseline", type=Path, default=None,
                    help="committed baseline JSON; fail if any (a) figure lost (a)")
    lc.add_argument("--write-baseline", type=Path, default=None, dest="write_baseline",
                    help="write this site's report as a baseline JSON to FILE")
    lc.set_defaults(func=cmd_link_coverage)

    v5b1 = sub.add_parser("verify-phase5b1", help="phase 5B-1 acceptance gates (citation export)")
```

(`sys` and `Path` are already imported at `cli.py:3-4`. Keep `json` as a local import, like the
module's other commands do.)

- [ ] **Step 6: Run the tests to verify they pass, plus the neighbouring CLI tests**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_link_coverage.py tests/test_budget_pdf_export_workflow.py -q
uv run --project . python -m govbudget link-coverage --help
```

Expected: `16 passed` (10 new + 6 existing). The help output lists `--site-dir SITE_DIR`,
`--baseline BASELINE` and `--write-baseline WRITE_BASELINE`.

- [ ] **Step 7: Commit the tool**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/link_coverage.py GovBudget/tests/test_link_coverage.py GovBudget/src/govbudget/cli.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(link-coverage): classify every program-page budget figure a/b/c/d and check a committed baseline (spec V9, overview §7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `3 files changed` on branch `families-2026-10-02`.

- [ ] **Step 8: Confirm the live export is the production export before cutting the baseline**

The baseline must describe what production serves at S0. Run from
`/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget`:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
shasum -a 256 /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/citations.json
curl -s https://fiscalreceipts.com/llms.txt | grep -o '[0-9,]* source citations'
grep -o '[0-9,]* source citations' site/public/llms.txt
```

Expected (measured 2026-10-02 against the export built `2026-10-02T01:30:21Z`):

```
60e7589539c2bd20e542b04e3a1c263aa1fb84fc138e53fb915777480ed35488  /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/citations.json
125,409 source citations
125,409 source citations
```

If the production count and the committed count differ, the local export is not what production
serves: stop and ask the owner. If only the sha differs and both counts still read 125,409,
someone re-exported the same corpus. Continue, but Steps 9–10 must then show
`receipts_match_citations` = True, and the commit in Step 11 records the numbers the tool prints in
place of the expected ones below.

- [ ] **Step 9: Write the baseline from the live export**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python -m govbudget link-coverage \
  --site-dir /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site \
  --write-baseline data/research/link_coverage/baseline.json
```

Expected (about 2 s, read-only on the export):

```
link-coverage: 45,151 budget figures on 2,562 program pages: a 44,747 · b 404 · c 0 · d 0; source-linked 100.00%, PDF-highlighted 99.11%; 2,437 of 2,562 pages fully PDF-highlighted
link-coverage: baseline -> data/research/link_coverage/baseline.json (905,978 bytes)
link-coverage: 0 violation(s)
link-coverage: PASS
```

- [ ] **Step 10: Check the baseline against itself and reconcile it with overview §7**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python -m govbudget link-coverage \
  --site-dir /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site \
  --baseline data/research/link_coverage/baseline.json
uv run --project . python -c "
import json
b = json.load(open('data/research/link_coverage/baseline.json'))
s = b['site']; occ = s['occurrences']
five = [k for k in occ if k not in ('fy26_disc', 'fy26_lines')]
print(sum(sum(occ[k].values()) for k in five), sum(occ[k]['a'] for k in five),
      sum(sum(v.values()) for v in occ.values()), len(b['pages_not_fully_pdf_highlighted']),
      s['workbook_citations'], s['workbook_citations_pdf_highlighted'], s['workbooks_pinned'],
      s['receipts_match_citations'], b['figures_sha256'][:16])
"
shasum -a 256 /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/citations.json
git -C .. status --short GovBudget/data/research
```

Expected:

```
link-coverage: 45,151 budget figures on 2,562 program pages: a 44,747 · b 404 · c 0 · d 0; source-linked 100.00%, PDF-highlighted 99.11%; 2,437 of 2,562 pages fully PDF-highlighted
link-coverage: compared against data/research/link_coverage/baseline.json (44,747 baseline (a) figures)
link-coverage: 0 violation(s)
link-coverage: PASS
55749 55328 57391 125 42153 41772 30 True b1358f0979feb1d5
60e7589539c2bd20e542b04e3a1c263aa1fb84fc138e53fb915777480ed35488  /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/citations.json
?? GovBudget/data/research/link_coverage/
```

Reading the second line of numbers:
- `55749 55328`: the research pass's appearance counts (five sections), reproduced exactly.
- `57391`: all seven sections.
- `125`: pages not fully PDF-highlighted (2,562 − 2,437).
- `42153 41772`: workbook citations and how many have a complete receipt. These are overview §7's numbers.
- `30`: workbooks, all hashing to their names.

The citations sha is unchanged, which shows the tool wrote nothing into `data/site`. That is the
S0 criterion "no `data/site` change".

- [ ] **Step 11: Commit the baseline**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/data/research/link_coverage/baseline.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(research): link-coverage S0 baseline — 45,151 program-page budget figures (44,747 a, 404 b, 0 c/d), 2,437 of 2,562 pages fully PDF-highlighted" -m "Export built 2026-10-02T01:30:21Z, citations.json sha256 60e75895…, 125,409 citations (= production llms.txt). Reproduces overview §7: 55,749 appearances / 55,328 (a) in the five sections the research pass read; 42,153 workbook citations / 41,772 with complete receipts. figures_sha256 b1358f0979feb1d5…. Spec §8 V9; the hard check runs at S6 (Task 23)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `1 file changed, 45356 insertions(+)` (one line per fact ID plus the summary keys).

- [ ] **Step 12: Check the build prerequisites (node_modules, data/site link, same export)**

Task 1 installed `site/node_modules` (`npm ci`) and created the `data/site` symlink into the main
lake. This step checks both, and that the link shows the export the baseline was computed from.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
test -d site/node_modules && ! test -L site/node_modules && echo "node_modules: real directory"
ls -ld data/site
git check-ignore -v data/site
shasum -a 256 data/site/json/citations.json
```

Expected:

```
node_modules: real directory
lrwxr-xr-x  1 andeslee  staff  ...  data/site -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site
/Users/andeslee/Documents/Cursor-Projects/.git/info/exclude:26:GovBudget/data/site	data/site
60e7589539c2bd20e542b04e3a1c263aa1fb84fc138e53fb915777480ed35488  data/site/json/citations.json
```

If `node_modules` is missing, run `cd site && npm ci && cd ..`. Do not symlink it: Turbopack
rejects a symlinked `node_modules`.

If `data/site` is missing (Task 1's link was removed), re-create it the way Task 1 does. Git must
keep ignoring it. `.gitignore`'s `data/site/` is a directory pattern, and it does not match a
symlink. The shared exclude file already lists `GovBudget/data/site` at line 26 (measured
2026-10-02), so the second command normally appends nothing:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
test -L data/site || ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site data/site
git check-ignore -q data/site || echo 'GovBudget/data/site' >> "$(git rev-parse --path-format=absolute --git-common-dir)/info/exclude"
git check-ignore -v data/site
git -C .. status --short GovBudget/data
```

Expected: `/Users/andeslee/Documents/Cursor-Projects/.git/info/exclude:26:GovBudget/data/site	data/site`.
The `git status` line prints nothing. Then re-run the first block of this step.

- [ ] **Step 13: Fresh production-origin build of the S0 tree**

A fresh build of this branch is the measurement source, because `site/out` in the main checkout is
stale and comes from a dirty tree. The env var is required: a placeholder-origin build weighs
differently.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site || exit 1
NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > "${TMPDIR:-/tmp}/task5-build.log" 2>&1; echo "exit=$?"
grep -E "Generating static pages using [0-9]+ workers \([0-9]+/[0-9]+\) in|Indexed [0-9]+ pages|Finished in" "${TMPDIR:-/tmp}/task5-build.log"
cat out/.build-meta.json
git -C ../.. status --short GovBudget/site
```

Expected (a few minutes; the 2026-10-02 deploy build of the same export generated 8,407 static
pages):

```
exit=0
✓ Generating static pages using 11 workers (8407/8407) in 2X.Xs
  Indexed 4125 pages
Finished in X.XXX seconds
{
  "built_at": "2026-10-0…Z",
  ...
  "git_head": "<full sha of the Step 11 commit>",
  ...
}
```

The `git status` line prints nothing: `out/` is ignored, and `public/llms.txt` is regenerated with
the same 125,409. If `llms.txt` shows as modified, the export differs from the committed one. Stop:
the stamps would measure a different page.

- [ ] **Step 14: Measure both pages with gate 1's own `weigh()`, and cross-check production**

The measurement script below extracts `weigh()` from `scripts/gates/build.mjs:889-892`
(raw bytes + `zlib.gzipSync(buf, { level: 9 })`) and runs that exact function, so the numbers are
the gate's numbers. It reads the paths and ceilings from the exported `PAGE_WEIGHT_BUDGET`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site || exit 1
node --input-type=module -e '
import fs from "fs"; import path from "path"; import zlib from "zlib";
import { PAGE_WEIGHT_BUDGET } from "./scripts/gates/build.mjs";
const src = fs.readFileSync("scripts/gates/build.mjs", "utf8");
const body = /\nfunction weigh\(absPath\) \{[\s\S]*?\n\}\n/.exec(src)[0];
const weigh = new Function("fs", "zlib", `${body}\nreturn weigh;`)(fs, zlib);
const meta = JSON.parse(fs.readFileSync("out/.build-meta.json", "utf8"));
for (const label of ["/methodology/", "/coverage/"]) {
  const e = PAGE_WEIGHT_BUDGET.find((x) => x.label === label);
  const { raw, gzip } = weigh(path.resolve("out", e.file));
  console.log(JSON.stringify({ label, raw, gzip, rawLeft: e.maxRaw - raw, gzipLeft: e.maxGzip - gzip,
    stamp: e.measured, git_head: meta.git_head.slice(0, 8), built_at: meta.built_at.replace(/\.\d+Z$/, "Z") }));
}'
for p in methodology coverage; do curl -s "https://fiscalreceipts.com/$p/" | node -e 'const z=require("zlib");const c=[];process.stdin.on("data",d=>c.push(d)).on("end",()=>{const b=Buffer.concat(c);console.log(process.argv[1],b.length,z.gzipSync(b,{level:9}).length)})' "$p"; done
```

Expected. The first two lines come from the build. Production (last two lines, measured
2026-10-02) serves the same sources and export.

```
{"label":"/methodology/","raw":161166,"gzip":45270,"rawLeft":834,"gzipLeft":130,"stamp":"160,836 / 45,147","git_head":"<8 hex>","built_at":"2026-10-0…Z"}
{"label":"/coverage/","raw":86203,"gzip":20458,"rawLeft":16797,"gzipLeft":292,"stamp":"85,710 / 20,288","git_head":"<8 hex>","built_at":"2026-10-0…Z"}
methodology 161166 45270
coverage 86203 20458
```

A fresh build can differ from production by a few gzip bytes, because Next writes a new build ID
each time. Use the printed build numbers. If either build number differs from production by more
than 500 raw or 50 gzip bytes, stop: the worktree's site sources or export differ from production.
Do not stamp a page production does not serve.

- [ ] **Step 15: Re-stamp `/methodology/` and `/coverage/` (comments and `measured` strings only)**

Use the values Step 14 printed:
- `<git_head>` and `<built_at>` are the `git_head` and `built_at` fields.
- The `X / Y` numbers are `raw` / `gzip`.
- The "left" numbers are `rawLeft` / `gzipLeft`.

Below, the expected values are filled in. Edit `site/scripts/gates/build.mjs`.

Edit 1 is at `:641-647`. Before:

```js
  // RE-MEASURED 2026-09-26 (decisions chain G, BUILD 1 of 0176fa6e, built
  // 2026-09-26T16:51:29Z; gate 1's own weigh()): 156,560 / 43,901 ->
  // 160,836 / 45,147. CEILINGS UNCHANGED; 1,164 raw / 253 gzip left. The
  // drift leg fired at 5.9x (+1,246 gzip over the integration stamp, on the
  // decisions branch with chain G's lake and export). The next paragraph
  // here needs a trim first, not a raise.
  { label: "/methodology/", file: "methodology/index.html", maxRaw: 162_000, maxGzip: 45_400, measured: "160,836 / 45,147" },
```

After:

```js
  // RE-MEASURED 2026-09-26 (decisions chain G, BUILD 1 of 0176fa6e, built
  // 2026-09-26T16:51:29Z; gate 1's own weigh()): 156,560 / 43,901 ->
  // 160,836 / 45,147. CEILINGS UNCHANGED; 1,164 raw / 253 gzip left. The
  // drift leg fired at 5.9x (+1,246 gzip over the integration stamp, on the
  // decisions branch with chain G's lake and export). The next paragraph
  // here needs a trim first, not a raise.
  // RE-MEASURED 2026-10-02 (families piece 1 S0, build of <git_head>, built
  // <built_at>, on the 2026-10-02T01:30:21Z export of 125,409 citations;
  // gate 1's own weigh()): 160,836 / 45,147 -> 161,166 / 45,270. CEILINGS
  // UNCHANGED; 834 raw / 130 gzip left (the old stamp claimed 253).
  // Production served 161,166 / 45,270 the same day. Piece 1 replaces one
  // sentence here at equal length and adds a link (spec §6.4); its era table
  // renders wherever it fits without a ceiling raise, decided in Task 19.
  { label: "/methodology/", file: "methodology/index.html", maxRaw: 162_000, maxGzip: 45_400, measured: "161,166 / 45,270" },
```

Edit 2 is at `:774-779`. Before:

```js
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 99,824 / 20,450 -> 85,710 / 20,288. CEILINGS UNCHANGED; 17,290
  // raw / 462 gzip left. The gate-fix wave moved this table's per-row utility
  // classes into a page-local CSS module (coverage.module.css).
  { label: "/coverage/", file: "coverage/index.html", maxRaw: 103_000, maxGzip: 20_750, measured: "85,710 / 20,288" },
```

After:

```js
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 99,824 / 20,450 -> 85,710 / 20,288. CEILINGS UNCHANGED; 17,290
  // raw / 462 gzip left. The gate-fix wave moved this table's per-row utility
  // classes into a page-local CSS module (coverage.module.css).
  // RE-MEASURED 2026-10-02 (families piece 1 S0, build of <git_head>, built
  // <built_at>, on the 2026-10-02T01:30:21Z export of 125,409 citations;
  // gate 1's own weigh()): 85,710 / 20,288 -> 86,203 / 20,458. CEILINGS
  // UNCHANGED; 16,797 raw / 292 gzip left (the old stamp claimed 462).
  // Production served 86,203 / 20,458 the same day. Piece 1's per-edition era
  // table (spec §6.4) renders on whichever page fits it without a ceiling
  // raise; Task 19 measures the candidate pages and decides.
  { label: "/coverage/", file: "coverage/index.html", maxRaw: 103_000, maxGzip: 20_750, measured: "86,203 / 20,458" },
```

In each "production served" sentence, keep the production numbers Step 14 printed, even when the
build numbers differ by a few bytes.

- [ ] **Step 16: Verify the page-weight leg and that only comments and stamps changed**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site || exit 1
node --input-type=module -e '
import { checkPageWeight, PAGE_WEIGHT_BUDGET } from "./scripts/gates/build.mjs";
const { errors, notes } = checkPageWeight();
console.log(JSON.stringify({ errors: errors.filter((e) => /\/(methodology|coverage)\//.test(e)) }));
for (const note of notes) for (const m of note.matchAll(/\/(?:methodology|coverage)\/ [\d.]+% \([^)]*\)/g)) console.log(m[0]);
for (const e of PAGE_WEIGHT_BUDGET) if (/^\/(methodology|coverage)\/$/.test(e.label)) console.log(e.label, e.maxRaw, e.maxGzip, e.measured);
'
git -C ../.. diff -U0 -- GovBudget/site/scripts/gates/build.mjs | grep '^[-+]' | grep -v '^+++\|^---' | grep -v '^[-+] *//'
```

Expected. There are no ceiling or drift errors for the two pages, and the ceilings are unchanged.
The only non-comment diff lines are the two `measured` strings.

```
{"errors":[]}
/methodology/ 99.7% (45,270/45,400 gzip, 130 bytes left)
/coverage/ 98.6% (20,458/20,750 gzip, 292 bytes left)
/methodology/ 162000 45400 161,166 / 45,270
/coverage/ 103000 20750 86,203 / 20,458
-  { label: "/methodology/", file: "methodology/index.html", maxRaw: 162_000, maxGzip: 45_400, measured: "160,836 / 45,147" },
+  { label: "/methodology/", file: "methodology/index.html", maxRaw: 162_000, maxGzip: 45_400, measured: "161,166 / 45,270" },
-  { label: "/coverage/", file: "coverage/index.html", maxRaw: 103_000, maxGzip: 20_750, measured: "85,710 / 20,288" },
+  { label: "/coverage/", file: "coverage/index.html", maxRaw: 103_000, maxGzip: 20_750, measured: "86,203 / 20,458" },
```

The drift leg (`build.mjs` ~:983-997) now compares the stamp with itself. Before this step it was
4 gzip bytes from firing on `/methodology/`: 253 recorded against 130 real, and it fires at
more than 2×.

- [ ] **Step 17: Commit the stamps**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/site/scripts/gates/build.mjs && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(site): re-measure /methodology/ and /coverage/ page-weight stamps at families S0 — ceilings unchanged" -m "Gate 1's own weigh() on a fresh production-origin build of the S0 tree (export 2026-10-02T01:30:21Z, 125,409 citations): /methodology/ 160,836 / 45,147 -> 161,166 / 45,270 (834 raw / 130 gzip left of 162,000 / 45,400); /coverage/ 85,710 / 20,288 -> 86,203 / 20,458 (16,797 raw / 292 gzip left of 103,000 / 20,750). Production weighs the same. Spec §6.2, §6.4, V8: /coverage/ has 292 gzip bytes left, not the 462 spec §6.4 quotes; piece 1's era table renders wherever it fits without a ceiling raise (Task 19 decides)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `1 file changed, 16 insertions(+), 2 deletions(-)`. If Step 14 printed different build
numbers, put those numbers in this message as well.
