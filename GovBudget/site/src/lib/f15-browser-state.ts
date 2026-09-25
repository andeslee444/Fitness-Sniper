/** Small, validated URL/storage contract for the family browser. */
export const F15_VARIANT_IDS = ["A", "B", "C", "D", "E", "EX"] as const;
export type F15VariantId = (typeof F15_VARIANT_IDS)[number];
export type F15Purpose = "develop" | "buy" | "upgrade";
export type F15TopicId = "airframe" | "cockpit" | "sensors" | "support";
export interface FamilyView {
  variant: F15VariantId;
  purpose: F15Purpose;
  record: string;
  fy: number;
  compare: F15VariantId | null;
  topic: F15TopicId;
}
export const F15_DEFAULT_VIEW: FamilyView = {
  variant: "EX",
  purpose: "buy",
  record: "F015EX",
  fy: 2026,
  compare: null,
  topic: "airframe",
};
const PURPOSES = ["develop", "buy", "upgrade"];
const TOPICS = ["airframe", "cockpit", "sensors", "support"];
const RECORDS = [
  "0207134F",
  "0207146F",
  "0207171F",
  "F01500",
  "F015EX",
  "F15EWS",
];
export function isF15Variant(value: unknown): value is F15VariantId {
  return (
    typeof value === "string" &&
    (F15_VARIANT_IDS as readonly string[]).includes(value)
  );
}
export function parseFamilyView(search: string, years: number[]): FamilyView {
  const query = new URLSearchParams(search);
  const variant = query.get("variant");
  const compare = query.get("compare");
  const purpose = query.get("purpose");
  const topic = query.get("topic");
  const record = query.get("record");
  const fy = Number(query.get("fy"));
  const selected = isF15Variant(variant) ? variant : F15_DEFAULT_VIEW.variant;
  return {
    variant: selected,
    compare: isF15Variant(compare) && compare !== selected ? compare : null,
    purpose: PURPOSES.includes(purpose ?? "")
      ? (purpose as F15Purpose)
      : F15_DEFAULT_VIEW.purpose,
    record: RECORDS.includes(record ?? "") ? record! : F15_DEFAULT_VIEW.record,
    fy: years.includes(fy) ? fy : (years.length ? Math.max(...years) : F15_DEFAULT_VIEW.fy),
    topic: TOPICS.includes(topic ?? "")
      ? (topic as F15TopicId)
      : F15_DEFAULT_VIEW.topic,
  };
}
export function serializeFamilyView(view: FamilyView): string {
  const query = new URLSearchParams({
    variant: view.variant,
    purpose: view.purpose,
    record: view.record,
    fy: String(view.fy),
    topic: view.topic,
  });
  if (view.compare && view.compare !== view.variant)
    query.set("compare", view.compare);
  return query.toString();
}
export function readSavedFactIds(
  raw: string | null,
  allowed: Set<string>,
): string[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return [
      ...new Set(
        parsed.filter(
          (id): id is string => typeof id === "string" && allowed.has(id),
        ),
      ),
    ].slice(0, 12);
  } catch {
    return [];
  }
}
