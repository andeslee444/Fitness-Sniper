/**
 * Which program page draws each follow-the-dollar sidecar — and, for a page
 * that draws none, which reason it may truthfully give (Task 26, from the
 * final review's one Critical).
 *
 * Pure: data.ts feeds it the shipped artifacts, the tests feed it fixtures.
 *
 * WHY THIS EXISTS. The exporter writes flows/{pe_bli}.json per BARE code
 * (export_site._emit_flows_sidecars): a high-confidence award with a positive
 * obligation at a recorded place of performance. For every code that names
 * one program the page slug IS that code, so the page finds its sidecar by
 * name. For a code two programs share, the sidecar is named for neither page
 * ('0145', beside /program/0145-APN/ and /program/0145-PANMC/), so until this
 * module no page drew it — and those member pages said their awards "haven't
 * been crosswalked at high confidence" while listing high-confidence awards,
 * and /coverage/ counted the sidecar as a program with a view.
 *
 * WHOSE IT IS comes from the member-grain district mart (fct_district_programs,
 * Task 27: one row per (district, pe_bli, account), addressed by split_key):
 * if every district row on the code carries ONE member's split_key, every
 * high-confidence award on the code that records a place of performance is
 * that member's link, so the sidecar — which draws only such awards — is that
 * member's view. Measured on the run-4 export (2026-09-25): all four shared
 * codes with a sidecar (0145, 2292, 3010, 3215) resolve to one member each,
 * and each sidecar's awards are a subset of that member's own high-confidence
 * links. A code whose rows name two members, or whose rows name no member (an
 * organization split keeps split_key === pe_bli), is owned by nobody; lib/corpus
 * then refuses to build, because the count every page prints as "programs
 * [with] a follow-the-dollar view" would overstate the pages that draw one.
 */

/** The two things about a programs.json row this rule reads. */
export interface FlowOwnerProgram {
  slug: string;
  pe_bli: string;
}

/**
 * sidecar name (bare pe_bli) → the slug of the one program page that draws it.
 * A sidecar absent from the map is drawn by no page.
 */
export function flowSidecarOwners({
  sidecars,
  programs,
  districtMemberKeys,
}: {
  /** flows/*.json basenames. */
  sidecars: Iterable<string>;
  programs: readonly FlowOwnerProgram[];
  /** bare pe_bli → every split_key its district-mart rows carry. */
  districtMemberKeys: ReadonlyMap<string, ReadonlySet<string>>;
}): Map<string, string> {
  const slugsByCode = new Map<string, string[]>();
  for (const p of programs) {
    const list = slugsByCode.get(p.pe_bli) ?? [];
    list.push(p.slug);
    slugsByCode.set(p.pe_bli, list);
  }
  const owners = new Map<string, string>();
  for (const code of sidecars) {
    const slugs = slugsByCode.get(code) ?? [];
    const keys = districtMemberKeys.get(code);
    if (!keys || keys.size !== 1) continue;
    const [key] = keys;
    // One program on the code: its page is named for the code.
    // Several: the one member the mart files every district row under —
    // never the bare code itself, which is an organization split's
    // unresolved address and the disambiguation stub's URL.
    if (slugs.length === 1 ? key === code && slugs[0] === code : key !== code && slugs.includes(key)) {
      owners.set(code, key);
    }
  }
  return owners;
}

/**
 * Why a program page that draws no follow-the-dollar view draws none. Each
 * reason is true of every page it is given to, provided the page is not a
 * sidecar's owner (flowSidecarOwners) — which lib/corpus guarantees by
 * refusing to build while any sidecar has no owner:
 *
 *   "no-high-link"           none of the page's own links is high-confidence.
 *   "no-place-of-performance" it has high-confidence links, and none of them
 *                            is an award with a positive obligation at a
 *                            recorded place of performance — the exporter's
 *                            condition for a sidecar. (Its code has no
 *                            sidecar; or the code is shared and the mart
 *                            files every district row under a sibling, so
 *                            this member's links record no district at all.)
 */
export type FlowAbsence = "no-high-link" | "no-place-of-performance";

export function flowAbsenceReason(
  awards: readonly { confidence: string }[],
): FlowAbsence {
  return awards.some((a) => a.confidence === "high")
    ? "no-place-of-performance"
    : "no-high-link";
}
