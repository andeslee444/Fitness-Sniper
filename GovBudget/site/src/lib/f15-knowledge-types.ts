import type { F15TopicId, VariantId } from "./f15-family";

export type KnowledgeEvidence =
  | "government"
  | "manufacturer"
  | "reporting"
  | "unconfirmed";

export interface KnowledgeSource {
  id: string;
  title: string;
  publisher: string;
  url: string;
  published: string | null;
  accessed: string;
  evidence: KnowledgeEvidence;
}

export interface VariantContext {
  variant: VariantId;
  topic: F15TopicId;
  title: string;
  text: string;
  sourceIds: string[];
}

export interface OperatorContext {
  id: string;
  country: string;
  status: "operator" | "ordered" | "proposed" | "historical" | "inactive";
  variants: string[];
  summary: string;
  /** A dated source snapshot, not an assumed current operational fleet. */
  quantityNote: string;
  asOf: string;
  sourceIds: string[];
}

export interface ProcurementEvent {
  id: string;
  title: string;
  country: string;
  date: string;
  status:
    | "request"
    | "enacted"
    | "contract"
    | "option"
    | "delivery"
    | "approval"
    | "plan";
  quantity: number | null;
  quantityLabel: string;
  amount: string | null;
  amountBasis: string | null;
  summary: string;
  sourceIds: string[];
  recordSlugs?: string[];
}

export interface SystemContext {
  id: string;
  category: "supplier" | "related" | "development";
  title: string;
  organization: string;
  variants: string[];
  /** Empty means family-wide or international context, not universal installation. */
  usVariants: VariantId[];
  summary: string;
  asOf: string;
  sourceIds: string[];
  recordSlugs?: string[];
  companySlug?: string;
}

export interface F15Knowledge {
  reviewed: string;
  sources: KnowledgeSource[];
  contexts: VariantContext[];
  operators: OperatorContext[];
  procurement: ProcurementEvent[];
  systems: SystemContext[];
}

export const EVIDENCE_LABELS: Record<KnowledgeEvidence, string> = {
  government: "Official record",
  manufacturer: "Manufacturer statement",
  reporting: "Independent reporting",
  unconfirmed: "Unconfirmed report",
};

export const PROCUREMENT_LABELS: Record<ProcurementEvent["status"], string> = {
  request: "Budget request",
  enacted: "Enacted funding",
  contract: "Contract / signed order",
  option: "Contract option",
  delivery: "Delivery reported",
  approval: "Potential sale approved",
  plan: "Announced plan",
};
