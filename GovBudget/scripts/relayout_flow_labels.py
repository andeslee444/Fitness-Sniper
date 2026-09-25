"""Re-place /flow/ node labels on the exported payload after a font change.

`data/site/json/flow_chart.json` bakes label positions computed by
`govbudget.flow_chart._place_labels` with a per-character width estimator
and a label box height that are derived from the site's sans face. When the
face changes (2026-09-12: Avenir Next system stack → vendored Source Sans 3),
the estimator and LABEL_H are re-derived in flow_chart.py and this script
re-runs ONLY the placement step over the existing nodes — the same function
the exporter calls — so the shipped payload matches the model without a full
`export-site` (which would also rewrite every other artifact in the shared
lake). Node geometry, values and fact-ids are untouched; only `lbl`/`ldr`
change. The next full export regenerates identical positions.

Run: uv run python scripts/relayout_flow_labels.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from govbudget.flow_chart import _place_labels, PAYLOAD_BUDGET_BYTES  # noqa: E402

path = ROOT / "data/site/json/flow_chart.json"
d = json.loads(path.read_text())

def relayout(nodes: list[dict], units: str) -> tuple[int, int]:
    before = sum(1 for n in nodes if n.get("lbl"))
    for n in nodes:
        n.pop("lbl", None); n.pop("ldr", None)
    _place_labels(nodes, units)
    return before, sum(1 for n in nodes if n.get("lbl"))

b0, b1 = relayout(d["budget"]["nodes"], d["budget"]["units"])
print(f"budget river: {b0} → {b1} labeled nodes of {len(d['budget']['nodes'])}")
for fy, river in d["spend"]["by_fy"].items():
    s0, s1 = relayout(river["nodes"], d["spend"]["units"])
    print(f"spend river FY{fy}: {s0} → {s1} labeled nodes of {len(river['nodes'])}")

out = json.dumps(d, sort_keys=True)  # byte-for-byte the exporter's _write_json style
size = len(out.encode("utf-8"))
assert size <= PAYLOAD_BUDGET_BYTES, f"flow_chart.json {size} > budget {PAYLOAD_BUDGET_BYTES}"
path.write_text(out)
print(f"flow_chart.json: {size} bytes (budget {PAYLOAD_BUDGET_BYTES})")
