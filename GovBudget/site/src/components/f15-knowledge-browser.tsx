"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Copy, Search } from "lucide-react";
import type { VariantId } from "@/lib/f15-family";
import {
  EVIDENCE_LABELS,
  PROCUREMENT_LABELS,
  type F15Knowledge,
  type KnowledgeSource,
  type ProcurementEvent,
} from "@/lib/f15-knowledge-types";
import styles from "./f15-knowledge-browser.module.css";
import { KnowledgeSources } from "./f15-knowledge-sources";
import { getF15Knowledge } from "@/lib/f15-knowledge";

const SECTIONS = [
  ["operators", "Countries & variants"],
  ["procurement", "Orders & requests"],
  ["suppliers", "Suppliers & systems"],
  ["related", "Programs & developments"],
] as const;
export type KnowledgeSection = (typeof SECTIONS)[number][0];

function EvidenceBadges({
  ids,
  sources,
}: {
  ids: string[];
  sources: KnowledgeSource[];
}) {
  const kinds = [
    ...new Set(
      sources
        .filter((source) => ids.includes(source.id))
        .map((source) => source.evidence),
    ),
  ];
  return (
    <div className={styles.badges}>
      {kinds.map((kind) => (
        <span className={styles.evidence} data-evidence={kind} key={kind}>
          {EVIDENCE_LABELS[kind]}
        </span>
      ))}
    </div>
  );
}

function RecordLinks({ slugs }: { slugs: string[] | undefined }) {
  if (!slugs?.length) return null;
  return (
    <nav className={styles.recordLinks} aria-label="Related budget records">
      {slugs.map((slug) => (
        <Link key={slug} href={`/program/${slug}/`}>
          Budget dossier · {slug}
          <ArrowUpRight size={12} />
        </Link>
      ))}
    </nav>
  );
}

function ProcurementCard({
  event,
  knowledge,
  onCopy,
}: {
  event: ProcurementEvent;
  knowledge: F15Knowledge;
  onCopy: (title: string, ids: string[]) => void;
}) {
  return (
    <article className={styles.card} data-context-id={event.id}>
      <div className={styles.cardLead}>
        <div className={styles.cardTop}>
          <span>
            {event.country} · {event.date}
          </span>
          <span className={styles.status} data-status={event.status}>
            {PROCUREMENT_LABELS[event.status]}
          </span>
        </div>
        <h3>{event.title}</h3>
      </div>
      <div className={styles.cardBody}>
        <div className={styles.figures}>
          {event.quantity != null && (
            <div>
              <strong>{event.quantity.toLocaleString("en-US")}</strong>
              <span>{event.quantityLabel}</span>
            </div>
          )}
          {event.amount && (
            <div>
              <strong>{event.amount}</strong>
              <span>{event.amountBasis}</span>
            </div>
          )}
        </div>
        <p>{event.summary}</p>
        <RecordLinks slugs={event.recordSlugs} />
        <EvidenceBadges ids={event.sourceIds} sources={knowledge.sources} />
        <KnowledgeSources ids={event.sourceIds} sources={knowledge.sources} />
        <button
          className={styles.copy}
          onClick={() => onCopy(event.title, event.sourceIds)}
        >
          <Copy size={12} />
          Copy sources
        </button>
      </div>
    </article>
  );
}

export function F15KnowledgeBrowser({
  knowledge,
  variant,
  onCopy,
  onInteract,
  initialSection = "operators",
  onBack,
}: {
  knowledge: F15Knowledge;
  variant: VariantId;
  onCopy: (text: string, success: string) => void;
  onInteract: () => void;
  initialSection?: KnowledgeSection;
  onBack?: () => void;
}) {
  const [section, setSection] = useState<KnowledgeSection>(initialSection);
  const [query, setQuery] = useState("");
  const [governmentOnly, setGovernmentOnly] = useState(false);
  const [variantOnly, setVariantOnly] = useState(false);
  const [showUnconfirmed, setShowUnconfirmed] = useState(false);
  const [orderStatus, setOrderStatus] = useState("all");
  const [country, setCountry] = useState("all");
  const heading = useRef<HTMLHeadingElement>(null);
  const openedFromOverview = Boolean(onBack);
  useEffect(() => {
    if (openedFromOverview) {
      heading.current?.focus({ preventScroll: true });
      heading.current?.closest("section")?.scrollIntoView({ block: "start" });
    }
  }, [openedFromOverview]);
  const normalized = query.trim().toLowerCase();
  const hasRumors = knowledge.sources.some(
    (source) => source.evidence === "unconfirmed",
  );
  const sourceMatch = (sourceIds: string[]) => {
    const sources = knowledge.sources.filter((source) =>
      sourceIds.includes(source.id),
    );
    return (
      (!governmentOnly ||
        (sources.length > 0 && sources.every((source) => source.evidence === "government"))) &&
      (showUnconfirmed ||
        !sources.some((source) => source.evidence === "unconfirmed"))
    );
  };
  const textMatch = (text: string) => text.toLowerCase().includes(normalized);
  const operators = knowledge.operators.filter(
    (item) =>
      sourceMatch(item.sourceIds) &&
      textMatch(
        [item.country, ...item.variants, item.summary, item.quantityNote].join(
          " ",
        ),
      ),
  );
  const procurement = knowledge.procurement
    .filter(
      (item) =>
        sourceMatch(item.sourceIds) &&
        (country === "all" || item.country === country) &&
        (orderStatus === "all" || item.status === orderStatus) &&
        textMatch(
          [
            item.title,
            item.country,
            item.summary,
            item.quantityLabel,
            item.quantity,
            item.amount,
            item.amountBasis,
            PROCUREMENT_LABELS[item.status],
            item.date,
          ].join(" "),
        ),
    )
    .sort((a, b) => b.date.localeCompare(a.date));
  const systems = knowledge.systems.filter(
    (item) =>
      sourceMatch(item.sourceIds) &&
      (section === "suppliers"
        ? item.category === "supplier"
        : item.category !== "supplier") &&
      (!variantOnly || item.usVariants.includes(variant)) &&
      textMatch(
        [
          item.title,
          item.organization,
          ...item.variants,
          item.summary,
          ...(item.recordSlugs ?? []),
        ].join(" "),
      ),
  );
  const count =
    section === "operators"
      ? operators.length
      : section === "procurement"
        ? procurement.length
        : systems.length;
  function copySources(title: string, ids: string[]) {
    const lines = knowledge.sources
      .filter((source) => ids.includes(source.id))
      .map(
        (source) =>
          `${source.publisher}. ${source.title}. ${source.published ? `Published ${source.published}. ` : ""}${EVIDENCE_LABELS[source.evidence]}. Accessed ${source.accessed}. ${source.url}`,
      );
    onCopy(
      [title, ...lines].join("\n\n"),
      "Sources copied with publisher, date and evidence type.",
    );
    onInteract();
  }
  return (
    <section
      data-field-notes=""
      className={styles.section}
      aria-labelledby="field-notes-heading"
    >
      <header className={styles.heading}>
        <div>
          <span className={`t-label ${styles.eyebrow}`}>03 / The wider picture</span>
          <h2 id="field-notes-heading" ref={heading} tabIndex={-1}>
            The wider F-15 network.
          </h2>
        </div>
        <p>
          Who flies it. Who builds it. What was requested, ordered and
          delivered. A source beside every claim.
        </p>
      </header>
      <div className={styles.review}>
        {onBack && (
          <button className={styles.back} onClick={onBack}>
            <ArrowLeft size={14} /> Back to the overview
          </button>
        )}
        <span>Research reviewed {knowledge.reviewed}</span>
      </div>
      <div className={styles.workspace}>
        <div
          className={styles.tabs}
          role="group"
          aria-label="F-15 field notes categories"
        >
          {SECTIONS.map(([id, label]) => (
            <button
              key={id}
              aria-pressed={section === id}
              onClick={() => {
                setSection(id);
                setQuery("");
                onInteract();
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div className={styles.controls}>
          <label className={styles.search}>
            <Search size={15} />
            <span className="sr-only">Search field notes</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={`Search ${SECTIONS.find(([id]) => id === section)![1].toLowerCase()}`}
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={governmentOnly}
              onChange={(event) => setGovernmentOnly(event.target.checked)}
            />
            All sources are government records
          </label>
          {(section === "suppliers" || section === "related") && (
            <label>
              <input
                type="checkbox"
                checked={variantOnly}
                onChange={(event) => setVariantOnly(event.target.checked)}
              />
              Applies to F-15{variant}
            </label>
          )}
          {hasRumors && (
            <label>
              <input
                type="checkbox"
                checked={showUnconfirmed}
                onChange={(event) => setShowUnconfirmed(event.target.checked)}
              />
              Include unconfirmed reports
            </label>
          )}
        </div>
        {section === "operators" && (
          <p className={styles.explainer}>
            Export models have their own names and configurations. The
            quantities below describe the cited order or historical inventory;
            they are not a live count of serviceable aircraft. Proposed buyers
            are labeled separately.
          </p>
        )}
        {section === "procurement" && (
          <>
            <div className={styles.legend}>
              <span>Request = proposed funding</span>
              <span>Contract = signed scope</span>
              <span>Delivery = aircraft received</span>
            </div>
            <p className={styles.explainer}>
              Newer requests below remain separate from the stored FY2026 budget
              ledger.
            </p>
            <details className={styles.evidenceGuide}>
              <summary>Understand amount scope and overlapping records</summary>
              <p className={styles.explainer}>
                Amounts can include engines, spares, upgrades and support. These
                events overlap across an acquisition and must not be summed. A
                sale approval sets a possible package; it does not confirm an
                order. Foreign sale values alone do not establish a cost to U.S.
                taxpayers.
              </p>
            </details>
            <div className={styles.filters}>
              <label>
                Country
                <select
                  value={country}
                  onChange={(event) => setCountry(event.target.value)}
                >
                  <option value="all">All countries</option>
                  {[
                    ...new Set(
                      knowledge.procurement.map((item) => item.country),
                    ),
                  ]
                    .sort()
                    .map((name) => (
                      <option key={name}>{name}</option>
                    ))}
                </select>
              </label>
              <label>
                Acquisition stage
                <select
                  value={orderStatus}
                  onChange={(event) => setOrderStatus(event.target.value)}
                >
                  <option value="all">All stages</option>
                  {Object.entries(PROCUREMENT_LABELS).map(([id, label]) => (
                    <option key={id} value={id}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </>
        )}
        {section === "suppliers" && (
          <p className={styles.explainer}>
            A system map of the companies and public organizations behind the
            aircraft. Applicability follows the cited configuration; a supplier
            relationship does not assign a share of the program budget.
          </p>
        )}
        {section === "related" && (
          <p className={styles.explainer}>
            Modernization, sustainment and reported developments, with dates and
            evidence types. Manufacturer announcements describe what the company
            says; a demonstration or proposal does not establish fleet-wide
            installation.
          </p>
        )}
        <div className={styles.results} role="status">
          {count}{" "}
          {section === "operators"
            ? count === 1
              ? "country record"
              : "country records"
            : count === 1
              ? "source-backed entry"
              : "source-backed entries"}
          {variantOnly && (section === "suppliers" || section === "related")
            ? ` linked to F-15${variant}`
            : ""}
        </div>
        <div className={styles.grid}>
          {section === "operators" &&
            operators.map((item) => (
              <article
                className={styles.card}
                key={item.id}
                data-context-id={item.id}
              >
                <div className={styles.cardLead}>
                  <div className={styles.cardTop}>
                    <span className={styles.status}>
                      {item.status === "operator"
                        ? "Operator"
                        : item.status === "ordered"
                          ? "On order"
                          : item.status === "inactive"
                            ? "Campaign inactive · reported"
                            : item.status === "historical"
                              ? "Historical operator"
                              : "Proposed buyer"}
                    </span>
                  </div>
                  <h3>{item.country}</h3>
                  <div className={styles.variantTags}>
                    {item.variants.map((name) => (
                      <span key={name}>{name}</span>
                    ))}
                  </div>
                </div>
                <div className={styles.cardBody}>
                  <p>{item.summary}</p>
                  <div className={styles.quantityNote}>{item.quantityNote}</div>
                  <small className={styles.asOf}>
                    Source snapshot · {item.asOf}
                  </small>
                  <EvidenceBadges
                    ids={item.sourceIds}
                    sources={knowledge.sources}
                  />
                  <KnowledgeSources
                    ids={item.sourceIds}
                    sources={knowledge.sources}
                  />
                  <button
                    className={styles.copy}
                    onClick={() => copySources(item.country, item.sourceIds)}
                  >
                    <Copy size={12} />
                    Copy sources
                  </button>
                </div>
              </article>
            ))}
          {section === "procurement" &&
            procurement.map((event) => (
              <ProcurementCard
                key={event.id}
                event={event}
                knowledge={knowledge}
                onCopy={copySources}
              />
            ))}
          {(section === "suppliers" || section === "related") &&
            systems.map((item) => (
              <article
                className={styles.card}
                key={item.id}
                data-context-id={item.id}
              >
                <div className={styles.cardLead}>
                  <div className={styles.cardTop}>
                    <span>{item.organization}</span>
                    <span>{item.asOf}</span>
                  </div>
                  <h3>{item.title}</h3>
                  <div className={styles.variantTags}>
                    {item.variants.map((name) => (
                      <span key={name}>{name}</span>
                    ))}
                  </div>
                </div>
                <div className={styles.cardBody}>
                  <p>{item.summary}</p>
                  <RecordLinks slugs={item.recordSlugs} />
                  {item.companySlug && (
                    <Link
                      className={styles.company}
                      href={`/company/${item.companySlug}/`}
                    >
                      Company dossier
                      <ArrowUpRight size={12} />
                    </Link>
                  )}
                  <EvidenceBadges
                    ids={item.sourceIds}
                    sources={knowledge.sources}
                  />
                  <KnowledgeSources
                    ids={item.sourceIds}
                    sources={knowledge.sources}
                  />
                  <button
                    className={styles.copy}
                    onClick={() => copySources(item.title, item.sourceIds)}
                  >
                    <Copy size={12} />
                    Copy sources
                  </button>
                </div>
              </article>
            ))}
        </div>
        {!count && (
          <div className={styles.empty}>
            <h3>No entries match these filters.</h3>
            <p>
              Clear the search or broaden the source and variant filters to see
              the available research.
            </p>
            <button
              onClick={() => {
                setQuery("");
                setGovernmentOnly(false);
                setVariantOnly(false);
                setCountry("all");
                setOrderStatus("all");
              }}
            >
              Reset filters
            </button>
          </div>
        )}
        <details className={styles.method}>
          <summary>How to read this evidence</summary>
          <p>
            Official budgets, contract announcements and delivery releases
            establish different things. The receipt desk above preserves the
            original budget fact IDs and accounting basis. These field notes add
            attributed web research; a press release is an evidence source, not
            proof that an invoice was paid. Independent reporting is labeled,
            and unconfirmed claims are excluded by default. Missing current
            fleet counts are left unstated.
          </p>
        </details>
      </div>
    </section>
  );
}

const fullKnowledge = getF15Knowledge();
export default function LoadedF15Research(
  props: Omit<Parameters<typeof F15KnowledgeBrowser>[0], "knowledge">,
) {
  return <F15KnowledgeBrowser {...props} knowledge={fullKnowledge} />;
}
