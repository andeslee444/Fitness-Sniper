"""Reconcile F-15 workbook cells to the same-edition DoD P-1/R-1 PDF.

Only exact matches of account, line, program, fiscal column, and amount become
highlights. Parentheses around gross procurement amounts are not negatives;
the explicit minus sign on Less: Advance Procurement is retained. Printed
blanks are recorded separately for workbook zeros and never get a made-up box.
Canonical workbook citations and facts are not modified by this sidecar export.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from statistics import median
from pathlib import Path

import openpyxl
import pdfplumber

NUMBER = re.compile(r"^\(?-?\d[\d,]*(?:\.\d+)?\)?$")


def amount(text: str) -> float | None:
    if not NUMBER.fullmatch(text):
        return None
    return float(text.replace(",", "").replace("(", "").replace(")", ""))


def normalize_header(text: str) -> tuple[str, ...]:
    """Compare header words, preserving year and every scenario qualifier."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    ignore = {"amount", "quantity", "qty", "cost"}
    aliases = {"actuals": "actual", "requests": "request", "req": "request"}
    return tuple(sorted(aliases.get(w, w) for w in words if w not in ignore))


def close_line(words: list[dict], y: float) -> list[dict]:
    return sorted((w for w in words if abs(w["top"] - y) < 2), key=lambda w: w["x0"])


def pdf_header_key(header: str, *, edition: int | None, exhibit: str) -> tuple[str, ...]:
    # Reviewed PB2025 R-1 wording difference only. Both originals carry the
    # same annualized-CR footnote (Public Law 118-35); FY2024 has no full-year
    # appropriation in this edition. Do not alias these words in other books.
    if edition == 2025 and exhibit == "R-1" and normalize_header(header) == normalize_header("FY 2024 PB Request with CR Amounts*"):
        return normalize_header("FY 2024 PB Request with CR Adjustments*")
    return normalize_header(header)


def page_columns(page: dict, exhibit: str) -> list[dict]:
    """Find labeled money columns from their headers and repeated right edges."""
    words = page["words"]
    no = next((w for w in words if w["text"] == "No" and w["x0"] < 100), None)
    dollars = next((w for w in words if w["text"] == "(Dollars"), None)
    if no is None or dollars is None:
        return []
    header = [w for w in words if dollars["bottom"] < w["top"] <= no["top"] + 2]
    pairs = []
    for word in header:
        if word["text"] != "FY":
            continue
        years = [w for w in header if re.fullmatch(r"20\d\d", w["text"]) and abs(w["top"] - word["top"]) < 1 and 0 < w["x0"] - word["x1"] < 8]
        if len(years) == 1:
            pairs.append((word, years[0]))
    pairs.sort(key=lambda p: p[0]["x0"])
    if not pairs:
        return []
    first_y = min(w["top"] for w, _ in pairs)
    header = [w for w in header if w["top"] >= first_y - 1]
    centers = [(w["x0"] + y["x1"]) / 2 for w, y in pairs]
    if exhibit == "P-1":
        costs = sorted((w for w in header if w["text"].rstrip("*") == "Cost"), key=lambda w: w["x0"])
        if len(costs) != len(pairs):
            return []
        anchors = [w["x1"] for w in costs]
    else:
        anchors = [c + 25 for c in centers]
    body = [w for w in words if w["top"] > no["bottom"] and w["top"] < page["height"] - 35 and amount(w["text"]) is not None]
    edges = []
    for anchor in anchors:
        candidates = [w for w in body if abs(w["x1"] - anchor) < 30 and w["x0"] > centers[0] - 40]
        counts = Counter(round(w["x1"], 0) for w in candidates)
        edges.append(counts.most_common(1)[0][0] if counts else None)
    offsets = [edge - anchor for edge, anchor in zip(edges, anchors) if edge is not None]
    if not offsets:
        return []
    # Entire OCO/supplemental columns can be blank. Their printed header still
    # establishes the column; inherit only the page's measured alignment.
    edges = [edge if edge is not None else anchor + median(offsets) for edge, anchor in zip(edges, anchors)]
    result = []
    for i, edge in enumerate(edges):
        left = edges[i - 1] + 2 if i else pairs[0][0]["x0"] - 30
        # Headings are centered over each full quantity/cost group. Use the
        # money edge rather than the FY word center so long labels stay whole.
        label_words = [w for w in header if left <= (w["x0"] + w["x1"]) / 2 < edge + 6 and w["text"] not in {"Qty", "Cost", "Cost*", "Quantity", "S", "e", "c", "Sec", "Se", "Act"}]
        label = " ".join(w["text"] for w in sorted(label_words, key=lambda w: (round(w["top"]), w["x0"])))
        result.append({"header": label, "normalized": normalize_header(label), "edge": edge, "body_top": no["bottom"]})
    return result


def program_lines(page: dict) -> list[dict]:
    words = page["words"]
    no = next((w for w in words if w["text"] == "No" and w["x0"] < 100), None)
    if no is None:
        return []
    return [w for w in words if w["text"].isdigit() and abs(w["x1"] - no["x1"]) < 15 and w["top"] > no["bottom"] and w["top"] < page["height"] - 35]


def match_cell(page: dict, row: dict, header: str, value: float, exhibit: str, edition: int | None = None) -> dict | None:
    """Return one exact printed amount, or an independently located blank zero."""
    text = page["text"]
    account = row["account"]
    if "Department of the Air Force" not in text or not re.search(rf"\b{re.escape(account)}\b", text):
        return None
    columns = [col for col in page_columns(page, exhibit) if col["normalized"] == pdf_header_key(header, edition=edition, exhibit=exhibit)]
    if len(columns) != 1:
        return None
    col = columns[0]
    lines = program_lines(page)
    candidates = [w for w in lines if int(w["text"]) == int(row["line"])]
    if len(candidates) != 1:
        return None
    line = candidates[0]
    words = page["words"]
    same = close_line(words, line["top"])
    line_text = " ".join(w["text"] for w in same)
    # P-1 omits the BLI code in the PDF; the exact title and account+line
    # identify it. R-1 prints the PE and activity, which must also agree.
    if exhibit == "R-1":
        if row["code"] not in [w["text"] for w in same] or row["title"].lower() not in line_text.lower() or row["activity"] not in [w["text"] for w in same]:
            return None
    else:
        ident = next((w for w in words if w["text"] == "Ident"), None)
        if ident is None:
            return None
        title = " ".join(w["text"] for w in same if line["x1"] < w["x0"] and w["x1"] < ident["x0"])
        if title.lower() != row["title"].lower():
            return None
        ident_tokens = [w["text"] for w in same if abs(w["x0"] - ident["x0"]) < 16]
        if row["cost_type"] in {"A", "B"} and "A" not in ident_tokens:
            return None
        if row["cost_type"] == "C" and "A" in ident_tokens:
            return None
    y = line["top"]
    next_y = min((w["top"] for w in lines if w["top"] > y + 2), default=page["height"] - 35)
    if exhibit == "P-1" and row["cost_type"] in {"B", "C"}:
        target = "Less:" if row["cost_type"] == "B" else "Advance"
        candidates = []
        for w in words:
            if w["text"] != target:
                continue
            around = " ".join(v["text"] for v in close_line(words, w["top"]))
            if row["cost_type"] == "B" and y < w["top"] < next_y and "(PY)" in around:
                candidates.append(w)
            elif row["cost_type"] == "C" and "(CY)" in around:
                if y < w["top"] < next_y:
                    candidates.append(w)
                elif 0 < y - w["top"] < 30:
                    # PB2024 puts the CY subtotal immediately BEFORE its line.
                    # The prior line must be the same named program, not an
                    # unrelated preceding aircraft's advance-procurement sum.
                    previous = max((v for v in lines if v["top"] < w["top"]), key=lambda v: v["top"], default=None)
                    if previous:
                        prior_title = " ".join(v["text"] for v in close_line(words, previous["top"]) if previous["x1"] < v["x0"] and v["x1"] < ident["x0"])
                        if row["title"].lower() == prior_title.lower():
                            candidates.append(w)
        if len(candidates) != 1:
            return None
        y = candidates[0]["top"]
    elif exhibit == "P-1" and row["cost_type"] != "A":
        return None
    amounts = [w for w in close_line(words, y) if abs(w["x1"] - col["edge"]) <= 6 and amount(w["text"]) is not None]
    if not amounts and value == 0:
        return {"blank_zero": True, "pdf_column_label": col["header"]}
    if len(amounts) != 1 or amount(amounts[0]["text"]) != value:
        return None
    return {"word": amounts[0], "page": page, "pdf_column_label": col["header"]}


def load_sources(manifest: Path, cache_dir: Path, site_dir: Path) -> dict:
    """Re-extract only reviewed pages from checksum-pinned original PDFs."""
    sources = {}
    for record in json.loads(manifest.read_text()):
        pdf = site_dir / "pdfs" / f"{record['sha256']}.pdf"
        if not pdf.exists():
            cached = cache_dir / f"{record['edition']}_{record['exhibit'].lower().replace('-', '')}.pdf"
            if cached.exists():
                if hashlib.sha256(cached.read_bytes()).hexdigest() != record["sha256"]:
                    raise ValueError(f"Source hash mismatch: {cached}")
                pdf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cached, pdf)
            else:
                import httpx
                response = httpx.get(record["url"], follow_redirects=True, timeout=90)
                response.raise_for_status()
                if hashlib.sha256(response.content).hexdigest() != record["sha256"]:
                    raise ValueError(f"Source hash changed; review needed: {record['url']}")
                pdf.parent.mkdir(parents=True, exist_ok=True)
                pdf.write_bytes(response.content)
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Source hash mismatch: {pdf}")
        pages = []
        with pdfplumber.open(pdf) as document:
            for number in record["pages"]:
                page = document.pages[number - 1]
                text = page.extract_text() or ""
                if f"FY {record['edition']} President's Budget" not in text or f"Exhibit {record['exhibit']}" not in text or "(Dollars in Thousands)" not in text:
                    raise ValueError(f"PDF identity mismatch: {pdf} page {number}")
                pages.append({"page_number": number, "width": page.width, "height": page.height, "text": text, "words": page.extract_words()})
        sources[(record["edition"], record["exhibit"])] = {**record, "pages": pages}
    return sources


def combine_receipts(receipts: list[dict], expected: float) -> dict:
    parts = [part for r in receipts for part in r["parts"]]
    matched = sum(p["amount_thousands"] for p in parts)
    unmatched = sum(r["unmatched_count"] for r in receipts)
    complete = all(r["complete"] for r in receipts) and matched == expected
    return {"amount_thousands": expected, "matched_amount_thousands": matched, "complete": complete, "blank_zero_count": sum(r["blank_zero_count"] for r in receipts), "unmatched_count": unmatched, "parts": parts}


def export_budget_pdf_receipts(*, site_dir: Path, manifest: Path, cache_dir: Path) -> dict:
    history = json.loads((site_dir / "json/f15_funding_history.json").read_text())
    citations = json.loads((site_dir / "json/citations.json").read_text())
    sources = load_sources(manifest, cache_dir, site_dir)
    workbooks = {}
    receipts = {}
    unmatched = []
    for point in history["points"]:
        for component in point["components"]:
            fact = component["fact_id"]
            if fact in receipts:
                continue
            citation = citations[fact]
            sha = citation["sha256"]
            if sha not in workbooks:
                path = site_dir / "workbooks" / f"{sha}.xlsx"
                if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                    raise ValueError(f"Workbook hash mismatch: {path}")
                workbooks[sha] = openpyxl.load_workbook(path, data_only=True)
            sheet = workbooks[sha][component["sheet"]]
            source = sources[(point["edition"], component["exhibit"])]
            parts = []
            blanks = 0
            missing = 0
            workbook_total = 0
            for cell in component["cells"].split(","):
                address = sheet[cell]
                row = address.row
                value = float(address.value or 0)
                workbook_total += value
                metadata = {"account": str(sheet[f"A{row}"].value), "activity": str(sheet[f"D{row}"].value), "line": str(sheet[f"F{row}"].value).strip(), "code": str(sheet[f"I{row}" if component["exhibit"] == "P-1" else f"G{row}"].value), "title": str(sheet[f"J{row}" if component["exhibit"] == "P-1" else f"H{row}"].value), "cost_type": str(sheet[f"K{row}"].value)}
                if metadata["account"] != component["account"] or metadata["code"] != component["program_id"].split(":")[-1] or metadata["activity"] != component["budget_activity"] or metadata["title"].lower() != component["title"].lower():
                    raise ValueError(f"Workbook program identity mismatch: {fact}/{cell}")
                header = str(sheet.cell(2, address.column).value)
                matches = [match for page in source["pages"] if (match := match_cell(page, metadata, header, value, component["exhibit"], point["edition"])) is not None]
                if len(matches) != 1:
                    missing += 1
                    unmatched.append({"fact_id": fact, "edition": point["edition"], "exhibit": component["exhibit"], "cell": cell, "value": value, "header": header, **metadata, "matches": len(matches)})
                    continue
                match = matches[0]
                if match.get("blank_zero"):
                    blanks += 1
                    continue
                word, page = match["word"], match["page"]
                parts.append({"amount_thousands": value, "program": metadata["title"], "line": metadata["line"], "workbook_cell": cell, "column_label": " ".join(header.split()), "pdf_column_label": match["pdf_column_label"], "edition": point["edition"], "exhibit": component["exhibit"], "sha256": source["sha256"], "hosted_pdf_url": f"/pdfs/{source['sha256']}.pdf", "page_width": page["width"], "page_height": page["height"], "page_number": page["page_number"], "x0": word["x0"], "x1": word["x1"], "top_pt": word["top"], "bottom_pt": word["bottom"], "resolution": "unique", "amount_text": word["text"], "units": "USD thousands", "official_url": source["url"]})
                if component["exhibit"] == "P-1":
                    parts[-1]["row_label"] = str(sheet[f"L{row}"].value)
            expected = component["amount_thousands"]
            if workbook_total != expected:
                raise ValueError(f"Canonical workbook amount mismatch: {fact}")
            matched = sum(p["amount_thousands"] for p in parts)
            receipts[fact] = {"amount_thousands": expected, "matched_amount_thousands": matched, "complete": missing == 0 and matched == expected, "blank_zero_count": blanks, "unmatched_count": missing, "parts": parts}
    leaf_count = len(receipts)
    for point in history["points"]:
        for cell in point["program_cells"]:
            if cell["fact_id"] not in receipts:
                receipts[cell["fact_id"]] = combine_receipts([receipts[fid] for fid in cell["input_fact_ids"]], cell["amount_thousands"])
        receipts[point["fact_id"]] = combine_receipts([receipts[c["fact_id"]] for c in point["components"]], point["amount_thousands"])
    cumulative = history["cumulative"]
    inputs = json.loads(citations[cumulative["fact_id"]]["inputs"])
    receipts[cumulative["fact_id"]] = combine_receipts([receipts[fid] for fid in inputs], cumulative["amount_thousands"])
    shards = defaultdict(dict)
    for fact, receipt in receipts.items():
        shards[fact[:2]][fact] = receipt
    out = site_dir / "json/budget-pdf-receipts"
    out.mkdir(parents=True, exist_ok=True)
    for i in range(256):
        (out / f"{i:02x}.json").write_text(json.dumps(shards[f"{i:02x}"], separators=(",", ":"), sort_keys=True) + "\n")
    default_cells = [cell for p in history["points"] if p["id"] in history["default_point_ids"] for cell in p["program_cells"]]
    report = {"source_count": len(sources), "leaf_count": leaf_count, "receipt_count": len(receipts), "default_cells": len(default_cells), "default_complete": sum(receipts[c["fact_id"]]["complete"] for c in default_cells), "complete_receipts": sum(r["complete"] for r in receipts.values()), "unmatched_cells": unmatched}
    (site_dir / "json/budget_pdf_receipts_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
