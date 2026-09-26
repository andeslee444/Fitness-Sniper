"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight } from "lucide-react";
import { PROGRAM_SECTIONS, type ProgramSectionId } from "./program-section";
import styles from "./program-wayfinding.module.css";

const CHAPTER_LABELS: Record<ProgramSectionId, string> = {
  "answer-strip": "Overview",
  figures: "Budget figures",
  trajectory: "Budget history",
  lineage: "Program lineage",
  description: "Purpose",
  justification: "Justification",
  "line-items": "Line items",
  "follow-dollar": "Follow the dollar",
  awards: "Related awards",
  lobbying: "Lobbying",
  oversight: "Oversight",
  dossier: "Research dossier",
  sources: "Primary sources",
};

const SHORTCUTS: { id: ProgramSectionId; label: string }[] = [
  { id: "answer-strip", label: "Overview" },
  { id: "figures", label: "Budget & history" },
  { id: "justification", label: "Program detail" },
  { id: "awards", label: "Contracts & influence" },
  { id: "oversight", label: "Oversight" },
  { id: "sources", label: "Sources" },
];

/** Navigation follows the existing evidence sections; it asserts no financial join. */
export function ProgramWayfinding({ code, isProcurement }: {
  code: string;
  isProcurement: boolean;
}) {
  const [active, setActive] = useState<ProgramSectionId>("answer-strip");
  const disclosure = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting);
      if (!visible.length) return;
      visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      const section = visible[0].target.getAttribute("data-section") as ProgramSectionId;
      setActive(section);
    }, { rootMargin: "-120px 0px -65% 0px", threshold: 0 });
    for (const id of PROGRAM_SECTIONS) {
      const section = document.getElementById(`program-${id}`);
      if (section) observer.observe(section);
    }
    return () => observer.disconnect();
  }, []);

  function selectChapter(id: ProgramSectionId) {
    setActive(id);
    if (disclosure.current) disclosure.current.open = false;
    document.getElementById(`program-${id}`)?.focus({ preventScroll: true });
  }

  return (
    <nav className={styles.wayfinding} aria-label="Program chapters" data-program-wayfinding>
      <div className={styles.shortcutRow}>
        <span className={styles.identity}>{isProcurement ? "BLI" : "PE"} <code>{code}</code></span>
        <div className={styles.shortcuts}>
          {SHORTCUTS.map(({ id, label }) => (
            <a key={id} href={`#program-${id}`} onClick={() => selectChapter(id)}>
              {label}
            </a>
          ))}
        </div>
        <details ref={disclosure} className={styles.chapters} onKeyDown={(event) => {
          if (event.key === "Escape" && disclosure.current?.open) {
            event.preventDefault();
            disclosure.current.open = false;
            disclosure.current.querySelector("summary")?.focus();
          }
        }}>
          <summary>
            <span className={styles.desktopLabel}>All chapters</span>
            <span className={styles.mobileLabel}>{CHAPTER_LABELS[active]}</span>
            <span aria-hidden="true">⌄</span>
          </summary>
          <ol>
            {PROGRAM_SECTIONS.map((id, index) => (
              <li key={id}>
                <a href={`#program-${id}`} onClick={() => selectChapter(id)} aria-current={active === id ? "location" : undefined}>
                  <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                  {CHAPTER_LABELS[id]}
                </a>
              </li>
            ))}
          </ol>
        </details>
      </div>
    </nav>
  );
}

/** A reading guide, not a claim that budget dollars have reached a contractor. */
export function ProgramEvidencePath() {
  return (
    <aside className={styles.evidencePath} aria-label="How to trace this program">
      <p className="t-label">Follow the evidence</p>
      <ol>
        <li><a href="#program-description">Understand the program</a></li>
        <li><ArrowRight size="1em" aria-hidden className={styles.pathArrow} /><a href="#program-figures">Choose a budget figure</a></li>
        <li><ArrowRight size="1em" aria-hidden className={styles.pathArrow} /><a href="#program-sources">Open its source receipt</a></li>
      </ol>
      <span>A cited figure opens to its source, fiscal context and a shareable footnote.</span>
    </aside>
  );
}
