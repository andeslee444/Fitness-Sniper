"""Reconcile exported PDF receipt units with canonical amounts and page evidence.

Run without --apply for a report. The six locator corrections below were
reviewed against the FY2026 Base/Total cost rows, not inferred from a scale.
Canonical figures and fact IDs never change. Unverified locations retain only
their document link. A complete before/after patch is saved before mutation.
"""
import argparse
import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import urldefrag

import duckdb
import pdfplumber

from govbudget.export_site import _emit_cite_shards, _write_json
from govbudget.jbooks.citation_units import jbook_pdf_citation_units, pdf_page_currency_units

ROOT = Path(__file__).resolve().parents[1]
# Each pair cites the first FY2026 Base/Total cost row for its own program.
# P-40 rows use Total Obligation Authority; R-2A uses the named project row.
REVIEWED = {
    "865834a6509e5506": ("0.002", 150, 175, 300, 400),
    "dc2443e23157fdef": ("0.002", 150, 175, 400, 500),
    "836d0c9bbc0ccd16": ("19.452", 240, 255, 300, 400),
    "4e60e6b6d1873135": ("19.452", 240, 255, 400, 500),
    "689b7c2f8e57e2f0": ("2.027", 240, 255, 300, 400),
    "a5b16504f30ca2e1": ("2.027", 240, 255, 400, 500),
}
LOCATION_FIELDS = ("page_number", "page_width", "page_height", "x0", "x1", "top_pt", "bottom_pt")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", default="/tmp/pdf-citation-unit-repair.json")
    args = parser.parse_args()
    site = ROOT / "data/site"
    parquet = site / "citations/citations.parquet"
    with duckdb.connect() as con:
        rows = con.execute("select distinct fact_id,amount_millions from read_parquet(?)", [str(site / "data/jbook_details.parquet")]).fetchall()
    amounts = {}
    for fid, value in rows:
        if fid in amounts and amounts[fid] != value:
            raise ValueError(f"Conflicting canonical values: {fid}")
        amounts[fid] = value
    citations = json.loads((site / "json/citations.json").read_text())
    pages, documents, patches = {}, {}, []
    def page_for(c):
        sha, number = c["sha256"], c["page_number"]
        if sha not in documents:
            documents[sha] = pdfplumber.open(site / "pdfs" / f"{sha}.pdf")
        key = (sha, number)
        if key not in pages:
            pages[key] = documents[sha].pages[number - 1]
        return pages[key]
    try:
        for fid, original in citations.items():
            if original["kind"] != "jbook_pdf" or original["resolution"] == "unresolved":
                continue
            canonical = amounts[fid]
            current = dict(original)
            if fid in REVIEWED:
                token, y0, y1, x0, x1 = REVIEWED[fid]
                if Decimal(token) != Decimal(str(canonical)):
                    raise ValueError(f"Reviewed locator's canonical value changed: {fid}")
                page = page_for(current)
                words = [w for w in page.extract_words() if w["text"] == token and y0 < w["top"] < y1 and x0 < w["x0"] < x1]
                if len(words) != 1:
                    raise ValueError(f"Reviewed locator is no longer unique: {fid}")
                word = words[0]
                current.update(amount_text=token, x0=word["x0"], x1=word["x1"], top_pt=word["top"], bottom_pt=word["bottom"], page_width=page.width, page_height=page.height, resolution="unique")
            literal = Decimal(current["amount_text"].replace(",", ""))
            source_units = None
            if literal != Decimal(str(canonical)):
                source_units = pdf_page_currency_units(page_for(current).extract_text() or "")
            try:
                current["units"] = jbook_pdf_citation_units(current["amount_text"], canonical, source_units=source_units)
            except ValueError:
                current.update({field: None for field in (*LOCATION_FIELDS, "amount_text", "units")})
                current["resolution"] = "unresolved"
                for field in ("official_url", "hosted_pdf_url"):
                    current[field] = urldefrag(current[field])[0]
            if current != original:
                delta = {key: value for key, value in current.items() if original.get(key) != value}
                patches.append({"fact_id": fid, "canonical_amount_millions": canonical, "before": {key: original.get(key) for key in delta}, "after": delta})
                citations[fid] = current
    finally:
        for document in documents.values():
            document.close()
    report = {"changed": len(patches), "thousands": sum(p["after"].get("units") == "USD thousands" for p in patches), "relocated": sum(p["fact_id"] in REVIEWED for p in patches), "unresolved": sum(p["after"].get("resolution") == "unresolved" for p in patches), "patches": patches}
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "patches"}))
    if args.apply:
        replacement = parquet.with_suffix(".repaired.parquet")
        with duckdb.connect() as con:
            con.execute("create table repaired as select * from read_parquet(?)", [str(parquet)])
            con.execute("begin transaction")
            for patch in patches:
                fields = list(patch["after"])
                con.execute("update repaired set " + ", ".join(f"{field}=?" for field in fields) + " where fact_id=?", [*(patch["after"][field] for field in fields), patch["fact_id"]])
            con.execute("commit")
            con.execute("copy repaired to ? (format parquet, compression zstd)", [str(replacement)])
        replacement.replace(parquet)
        _write_json(site / "json/citations.json", citations)
        _emit_cite_shards(json_dir=site / "json", citations_dict=citations)
        print("Updated citation Parquet, JSON, and all same-origin receipt shards; canonical amounts unchanged.")


if __name__ == "__main__":
    main()
