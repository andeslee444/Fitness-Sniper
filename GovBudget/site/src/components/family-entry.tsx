import Link from "next/link";
import { ArrowRight, Layers3 } from "lucide-react";
import { getF15FamilyData } from "@/lib/f15-family-data";
import { getRecordFact, type VariantId } from "@/lib/f15-family";
import { citationSourceSlice } from "@/lib/source-document";
import { F15Navigation, F15FamilyHeader } from "./f15-navigation";
import { F15Schematic } from "./f15-schematic";
import { SourceDocumentLinks } from "./source-document-links";
import styles from "./family-entry.module.css";

// These are curated budget-record entry points, not a prefix match or a claim
// that a shared program's spending belongs exclusively to the selected variant.
const F15_ENTRY_VARIANTS: Record<string, VariantId> = {
  "0207134F": "E",
  "0207146F": "EX",
  "0207171F": "EX",
  F01500: "E",
  F015EX: "EX",
  F15EWS: "E",
};

export function F15ProgramIllustration({ programSlug }: { programSlug: string }) {
  const variant = F15_ENTRY_VARIANTS[programSlug];
  return variant ? <F15Schematic variant={variant} /> : null;
}

export function isF15Program(slug: string) { return Boolean(F15_ENTRY_VARIANTS[slug]); }

export function F15ProgramNavigation({ programSlug }: { programSlug: string }) {
  const variant = F15_ENTRY_VARIANTS[programSlug];
  if (!variant) return null;
  const record = getF15FamilyData().records.find(item => item.slug === programSlug)!;
  const base = `/families/f-15/?variant=${variant}&purpose=${record.purpose}&record=${programSlug}`;
  return <div className={styles.familyNavigation}>
    <F15FamilyHeader recordPage />
    <F15Navigation active="funding" base={base} />
  </div>;
}

/** Preserve the reader's budget-record identity when entering a family view. */
export function ProgramFamilyEntry({ programSlug }: { programSlug: string }) {
  const variant = F15_ENTRY_VARIANTS[programSlug];
  if (!variant) return null;
  const record = getF15FamilyData().records.find((item) => item.slug === programSlug);
  if (!record?.variantIds.includes(variant)) return null;
  const href = `/families/f-15/?variant=${variant}&purpose=${record.purpose}&record=${programSlug}`;

  return (
    <aside className={styles.compact} aria-label="Explore the aircraft family" data-family-entry={programSlug}>
      <Layers3 size={23} strokeWidth={1.4} aria-hidden="true" />
      <div>
        <p className={styles.compactTitle}>This record is part of the F-15 family.</p>
        <p className={styles.compactDescription}>Inspect aircraft variants alongside their development, procurement, and upgrade records.</p>
      </div>
      <Link href={href} className={styles.compactLink}>Open the family browser <ArrowRight size={17} aria-hidden="true" /></Link>
    </aside>
  );
}

/** Keep each record's exact government source beside its program identity. */
export function F15ProgramSources({ programSlug }: { programSlug: string }) {
  const variant = F15_ENTRY_VARIANTS[programSlug];
  if (!variant) return null;
  const family = getF15FamilyData();
  const record = family.records.find((item) => item.slug === programSlug);
  if (!record?.variantIds.includes(variant)) return null;
  const sourceYear = Math.max(...family.years);
  const fact = getRecordFact(record, sourceYear);
  // The absent TOA record can still point to its own narrative document.
  // It must not borrow another program's amount or substitute a J-book zero.
  const sourceFactId = fact?.factId ?? record.narratives.find(item => family.citations[item.factId]?.official_url)?.factId;
  if (!sourceFactId) return null;
  const sourceCitations = citationSourceSlice(sourceFactId, family.citations);
  return <div data-program-sources={programSlug}>
    {!fact && <p className={styles.compactDescription}>J-book narrative source. This does not supply the missing FY{sourceYear} TOA figure.</p>}
    <SourceDocumentLinks citation={sourceCitations[sourceFactId]} citations={sourceCitations} factId={sourceFactId} program={programSlug} surface="f15-program" />
  </div>;
}

/** A poster-sized entry into the family browser; no 3D loads on the index. */
export function F15FamilyFeature() {
  return (
    <section className={styles.feature} aria-labelledby="f15-family-heading" data-family-feature="f-15">
      <div className={styles.featureCopy}>
        <p className={`t-label ${styles.eyebrow}`}>The family register · Air</p>
        <h2 id="f15-family-heading">One family. <br />Many chapters.</h2>
        <p className={styles.description}>Meet the F-15 family. Move between aircraft variants, inspect the model, and follow the separate records for development, procurement, and upgrades.</p>
        <Link href="/families/f-15/" className={styles.featureLink}>Explore the F-15 family <ArrowRight size={18} aria-hidden="true" /></Link>
        <p className={styles.featureNote}>Every linked budget record keeps its own fiscal context and source receipts.</p>
      </div>
      <div className={styles.plate} aria-label="F-15 family preview">
        <div className={styles.plateHeader}><span>F-15 / Aircraft family</span><span aria-hidden="true">01</span></div>
        <F15Schematic variant="EX" className={styles.schematic} />
        <div className={styles.variantPreview} aria-label="Aircraft variants in this family">
          {["A", "B", "C", "D", "E", "EX"].map((variant) => <span key={variant}>F-15{variant}</span>)}
        </div>
        <p className={styles.plateNote}>Conceptual silhouette · Explore the models and evidence</p>
      </div>
    </section>
  );
}
