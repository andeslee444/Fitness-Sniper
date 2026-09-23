"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import type { VariantId } from "@/lib/f15-family";
import type { KnowledgeSection } from "./f15-knowledge-browser";
import styles from "./f15-knowledge-browser.module.css";

const Research = dynamic(() => import("./f15-knowledge-browser"), {
  ssr: false,
  loading: () => (
    <section data-field-notes="" className={styles.section} aria-busy="true">
      <h2>The wider F-15 network.</h2>
      <p role="status">Loading countries, orders and supplier research…</p>
    </section>
  ),
});

// Small, cited entry points keep the full research dataset out of the initial
// page payload. The expanded workspace remains one deliberate click away.
export function F15KnowledgeSection(props: {
  variant: VariantId;
  onCopy: (text: string, success: string) => void;
  onInteract: () => void;
}) {
  const [section, setSection] = useState<KnowledgeSection | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const hasOpened = useRef(false);
  useEffect(() => {
    if (section === null && hasOpened.current) {
      heading.current?.focus({ preventScroll: true });
      heading.current?.closest("section")?.scrollIntoView({ block: "start" });
    }
  }, [section]);
  function open(section: KnowledgeSection) {
    hasOpened.current = true;
    setSection(section);
    props.onInteract();
  }
  if (section) {
    return (
      <Research
        {...props}
        initialSection={section}
        onBack={() => setSection(null)}
      />
    );
  }
  return (
    <section
      data-field-notes=""
      className={`${styles.section} ${styles.networkOverview}`}
      aria-labelledby="field-notes-heading"
    >
      <header className={styles.heading}>
        <div>
          <span className={styles.eyebrow}>Beyond the U.S. budget</span>
          <h2 id="field-notes-heading" ref={heading} tabIndex={-1}>
            The wider F-15 network.
          </h2>
        </div>
        <p>
          Follow the aircraft into other countries, signed orders and the
          companies behind its systems.
        </p>
      </header>
      <div className={styles.preview}>
        <div className={styles.previewItem}>
          <span className={styles.previewLabel}>Who flies it</span>
          <h3>One family. Seven countries.</h3>
          <p className={styles.countryList}>
            United States · Japan · Israel · Saudi Arabia · Singapore · South
            Korea · Qatar
          </p>
          <a
            className={styles.previewSource}
            href="https://www.boeing.com/features/2026/02/built-to-adapt-the-f-15s-transformation-and-global-impact"
            target="_blank"
            rel="noopener noreferrer"
          >
            Boeing · February 2026 <ArrowUpRight size={12} />
          </a>
          <button onClick={() => open("operators")}>
            Explore countries & variants <ArrowRight size={16} />
          </button>
        </div>
        <div className={styles.previewItem}>
          <span className={styles.previewLabel}>What is being requested</span>
          <h3>24 more F-15EX aircraft.</h3>
          <p>
            The FY2027 U.S. budget request includes 24 aircraft and associated
            support. A request is a proposal, not a signed order.
          </p>
          <a
            className={styles.previewSource}
            href="https://www.af.mil/Portals/1/documents/Secretariat%20of%20the%20AF/SAF-FM/Budget%20-%202027/Budget%20docs/FY27%20Air%20Force%20Aircraft%20Procurement%20Volume%20I.pdf?ver=4kiKWbFkcqsD4dDrO7-P4g%3D%3D"
            target="_blank"
            rel="noopener noreferrer"
          >
            Air Force P-40 · April 2026 <ArrowUpRight size={12} />
          </a>
          <button onClick={() => open("procurement")}>
            Examine orders & requests <ArrowRight size={16} />
          </button>
        </div>
        <div className={styles.previewItem}>
          <span className={styles.previewLabel}>Who builds the systems</span>
          <h3>Engines, radar, protection.</h3>
          <p>
            GE supplies the EX’s F110 engines. Raytheon’s APG-82 radar is one
            part of a wider network of suppliers and upgrades.
          </p>
          <div className={styles.previewSources}>
            <a
              className={styles.previewSource}
              href="https://www.af.mil/News/Features/Article/2827633/us-air-force-awards-f-15ex-engine-contract/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Air Force · 2021 <ArrowUpRight size={12} />
            </a>
            <a
              className={styles.previewSource}
              href="https://www.rtx.com/raytheon/what-we-do/air/apg82v1"
              target="_blank"
              rel="noopener noreferrer"
            >
              RTX · system profile <ArrowUpRight size={12} />
            </a>
          </div>
          <button onClick={() => open("suppliers")}>
            Explore suppliers & systems <ArrowRight size={16} />
          </button>
        </div>
      </div>
      <div className={styles.previewFooter}>
        <span>
          Dated evidence, with original sources. Reviewed September 9, 2026.
        </span>
        <button onClick={() => open("related")}>
          Related programs & developments <ArrowRight size={14} />
        </button>
      </div>
    </section>
  );
}
