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
