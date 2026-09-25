import type { GaoProgramFindings } from "./data";
export { normalizeProgramHHI } from "./concentration-evidence.mjs";

export interface GaoRatification { product_number: string; gao_program: string; slug: string; verdict: "y" | "n"; }
const gaoKey = (product: string, program: string, slug: string) => JSON.stringify([product, program, slug]);

/** Read the existing human verdicts, including quoted CSV cells and CRLF. */
export function parseGaoRatifications(csv: string): GaoRatification[] {
  const rows: string[][] = [];
  let row: string[] = [], cell = "", quoted = false;
  for (let i = 0; i < csv.length; i++) {
    const char = csv[i];
    if (char === '"') {
      if (quoted && csv[i + 1] === '"') { cell += '"'; i++; }
      else quoted = !quoted;
    } else if (!quoted && (char === "," || char === "\n")) {
      row.push(cell.trim()); cell = "";
      if (char === "\n") { if (row.some(Boolean)) rows.push(row); row = []; }
    } else cell += char;
  }
  if (quoted) throw new Error("Unclosed quoted cell in GAO ratification seed");
  row.push(cell.trim()); if (row.some(Boolean)) rows.push(row);
  const headers = rows.shift() ?? [];
  const names = ["product_number", "gao_program", "slug", "verdict"] as const;
  if (names.some(name => !headers.includes(name))) throw new Error("Missing GAO ratification seed columns");
  const decisions = new Map<string, GaoRatification>();
  for (const values of rows) {
    const item = Object.fromEntries(names.map(name => [name, values[headers.indexOf(name)] ?? ""])) as unknown as GaoRatification;
    if (!item.product_number || !item.gao_program || !item.slug || !["y", "n"].includes(item.verdict)) throw new Error("Invalid GAO ratification seed row");
    const key = gaoKey(item.product_number, item.gao_program, item.slug);
    if (decisions.has(key) && decisions.get(key)!.verdict !== item.verdict) throw new Error("Conflicting GAO ratification seed verdicts");
    decisions.set(key, item);
  }
  return [...decisions.values()];
}

export function selectRatifiedGaoFindings(bySlug: Record<string, GaoProgramFindings>, decisions: GaoRatification[]) {
  const allowed = new Set(decisions.filter(row => row.verdict === "y").map(row => gaoKey(row.product_number, row.gao_program, row.slug)));
  const selected: Record<string, GaoProgramFindings> = {};
  for (const [slug, findings] of Object.entries(bySlug)) {
    const assessments = findings.assessments.filter(row => allowed.has(gaoKey(row.product_number, row.common_name, slug)));
    const reports = findings.reports.filter(row => allowed.has(gaoKey(row.product_number, row.gao_program, slug)));
    if (assessments.length || reports.length) selected[slug] = { assessments, reports };
  }
  return selected;
}

/**
 * What a program page publishes from gao_program_findings.json (integration
 * 2026-09-25, ruling R-INT-3). The ratification guard above decides the
 * ANCHORS: an assessment a person ratified (inherited_from === null) and a
 * related report render only with a 'y' verdict for their exact (product,
 * GAO program, slug). An older WSAA edition carries no verdict of its own
 * (ROADMAP #30, gate 21 leg h8): it renders behind the ratified anchor it is
 * chained to (inherited_from + program_key), so it passes exactly when THAT
 * anchor passes the guard on the same page. The guard alone dropped all 70
 * inherited editions on the 2026-09-25 run-4 export while /methodology/
 * still printed "70 earlier editions inherited".
 */
export function selectPublishedGaoFindings(bySlug: Record<string, GaoProgramFindings>, decisions: GaoRatification[]) {
  const ratified = selectRatifiedGaoFindings(bySlug, decisions);
  const published: Record<string, GaoProgramFindings> = {};
  for (const [slug, findings] of Object.entries(bySlug)) {
    const anchors = ratified[slug]?.assessments ?? [];
    const assessments = findings.assessments.filter((row) =>
      row.inherited_from === null
        ? anchors.includes(row)
        : anchors.some(
            (anchor) =>
              anchor.product_number === row.inherited_from &&
              anchor.program_key === row.program_key,
          ),
    );
    const reports = ratified[slug]?.reports ?? [];
    if (assessments.length || reports.length) published[slug] = { assessments, reports };
  }
  return published;
}
