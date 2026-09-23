"use client";

import {
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent,
  type ReactNode,
} from "react";
import Link from "next/link";
import {
  ArrowRight,
  Bookmark,
  Check,
  ChevronRight,
  Copy,
  FileText,
  Layers,
  Share2,
  Volume2,
  VolumeX,
  X,
  ExternalLink,
} from "lucide-react";
import { Cite, CitationPanelContext } from "@/components/cite";
import { F15Model } from "./f15-model";
import { F15Schematic } from "./f15-schematic";
import { F15Navigation, F15FamilyHeader } from "./f15-navigation";
import { SourceDocumentLinks } from "./source-document-links";
import { F15KnowledgeSection } from "./f15-knowledge-section";
import { KnowledgeSources } from "./f15-knowledge-sources";
import {
  getRecordFact,
  getFundingInputs,
  getVariantRecords,
  type F15FamilyPayload,
  type FamilyFundingFact,
  type FamilyFundingRecord,
  type F15Variant,
  type FamilySource,
} from "@/lib/f15-family";
import {
  F15_DEFAULT_VIEW,
  F15_VARIANT_IDS,
  parseFamilyView,
  readSavedFactIds,
  serializeFamilyView,
  type FamilyView,
  type F15TopicId,
  type F15VariantId,
} from "@/lib/f15-browser-state";
import { footnoteInputFromCitation, formatFootnote } from "@/lib/footnote";
import { formatAmount } from "@/lib/format";
import { ANSWER_COPY, formatAnswerBrief } from "@/lib/answer-brief";
import { trackReaderEvent, type ReaderEvent } from "@/lib/reader-events";
import styles from "./f15-family-browser.module.css";

const STORAGE_KEY = "fiscal-receipts:f15-research:v1";
const TOPICS: { id: F15TopicId; label: string }[] = [
  { id: "airframe", label: "Aircraft & configuration" },
  { id: "cockpit", label: "Cockpit & software" },
  { id: "sensors", label: "Electronic systems" },
  { id: "support", label: "Support & tooling" },
];

function figureContext(fact: FamilyFundingFact) {
  return {
    value: fact.amountThousands,
    units: fact.units,
    fy: fact.fy,
    measure: fact.measure,
    basis: fact.basis,
    entity: fact.entity ?? fact.recordSlug,
    edition: fact.edition,
  };
}

function FundingFigure({
  fact,
  chips = false,
}: {
  fact: FamilyFundingFact;
  chips?: boolean;
}) {
  return (
    <Cite
      value={fact.amountThousands}
      units={fact.units}
      dataset={fact.dataset}
      factId={fact.factId}
      basis={fact.basis}
      fy={fact.fy}
      measure={fact.measure}
      edition={fact.edition}
      entity={fact.entity ?? fact.recordSlug}
      exhibitFamily={fact.exhibit === "R-1" ? "rdte" : "procurement"}
      chip={chips}
    />
  );
}

function FundingSourceRows({ inputs }: { inputs: FamilyFundingFact[] }) {
  return (
    <section
      className={styles.receiptInputs}
      aria-label="Included in this total"
      data-input-count={inputs.length}
    >
      <h4>{inputs[0]?.status === "Request" ? "Inside this request" : "Inside this funding record"}</h4>
      <ul>
        {inputs.map((input, index) => {
          const label = RECEIPT_INPUT_LABELS[input.factId];
          return (
            <li key={input.factId} data-input-index={index}>
              <div className={styles.receiptInputLabel}>
                <span>{label?.title ?? input.label ?? "Source row"}</span>
                <small className="sr-only">{label?.detail ?? input.source.locator}</small>
              </div>
              <FundingFigure fact={input} />
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function SourceLink({
  source,
  label = "Source document",
}: {
  source: FamilySource | undefined;
  label?: string;
}) {
  if (!source) return null;
  return (
    <a
      href={source.officialUrl ?? source.receiptUrl}
      className={styles.sourceLink}
      onClick={() => { if (source.officialUrl) trackReaderEvent("official_source_opened", { program: "f-15", factId: source.factId, surface: "f15" }); }}
      target="_blank"
      rel="noreferrer"
    >
      {source.officialUrl ? label : "Inspect source record"}
      <ExternalLink size={11} />
    </a>
  );
}

const RECORD_GUIDES: Record<string, { title: string; description: string }> = {
  F015EX: {
    title: "Aircraft & support",
    description: "Purchase aircraft, modifications and supporting equipment.",
  },
  "0207146F": {
    title: "F-15EX development",
    description: "Test and integrate capabilities for the Eagle II.",
  },
  "0207134F": {
    title: "Fleet software",
    description: "Develop and integrate systems across the F-15 fleet.",
  },
  "0207171F": {
    title: "Electronic protection",
    description: "Develop the EPAWSS threat warning and countermeasure system.",
  },
  F01500: {
    title: "Aircraft modifications",
    description: "Improve existing aircraft and their supporting equipment.",
  },
  F15EWS: {
    title: "F-15E protection kits",
    description: "Purchase and install EPAWSS on the Strike Eagle.",
  },
};
const FUNDING_CATEGORIES = {
  buy: "Aircraft procurement",
  develop: "Research & development",
  upgrade: "Modification procurement",
};

// Exact P-1 FY2026 workbook classifications; these labels do not infer a
// parts allocation, unit price, or a classification for another year's rows.
const RECEIPT_INPUT_LABELS: Record<
  string,
  { title: string; detail: string; shortTitle: string }
> = {
  "03407158217dec76": {
    title: "Combat aircraft",
    shortTitle: "Aircraft",
    detail: "Tactical forces · Activity 01",
  },
  "5768200ce4fbc494": {
    title: "Aircraft modifications",
    shortTitle: "Modifications",
    detail: "In-service aircraft · Activity 05",
  },
  "819f32a0ad3fb66e": {
    title: "Support & facilities",
    shortTitle: "Support",
    detail: "Support equipment and facilities · Activity 07",
  },
};

function FundingAircraftSelect({
  variant,
  variants,
  onChange,
  compact = false,
}: {
  variant: F15VariantId;
  variants: F15Variant[];
  onChange: (variant: F15VariantId) => void;
  compact?: boolean;
}) {
  return (
    <label className={styles.fundingVariant}>
      <span>Aircraft</span>
      <select
        aria-label="Selected aircraft"
        value={variant}
        onChange={(event) => onChange(event.target.value as F15VariantId)}
      >
        {variants.map((item) => (
          <option value={item.id} key={item.id}>
            {item.name}{compact ? "" : ` · ${item.nickname}`}
          </option>
        ))}
      </select>
    </label>
  );
}

function BudgetTimeline({
  record,
  year,
  years,
  onYear,
  comparisonYears,
}: {
  record: FamilyFundingRecord;
  year: number;
  years: number[];
  onYear: (year: number) => void;
  comparisonYears?: [number, number];
}) {
  const yearRail = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const rail = yearRail.current;
    if (!rail) return;
    const alignSelectedYear = () => {
      const selected = rail.querySelector<HTMLButtonElement>(
        '[aria-pressed="true"]',
      );
      if (!selected || !rail.clientWidth) return;
      rail.scrollLeft +=
        selected.getBoundingClientRect().left -
        rail.getBoundingClientRect().left -
        (rail.clientWidth - selected.clientWidth) / 2;
    };
    alignSelectedYear();
    const observer =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(alignSelectedYear)
        : null;
    observer?.observe(rail);
    return () => observer?.disconnect();
  }, [year, record.slug]);
  const coveredYears = [
    ...record.facts.map((item) => item.fy),
    Math.max(...years),
    year,
  ];
  const firstYear = Math.min(...coveredYears);
  const lastYear = Math.max(...coveredYears);
  const series = Array.from(
    { length: lastYear - firstYear + 1 },
    (_, index) => {
      const fy = firstYear + index;
      return { fy, fact: getRecordFact(record, fy) };
    },
  );
  const maximum = Math.max(
    ...series.map(({ fact }) => Math.abs(fact?.amountThousands ?? 0)),
    1,
  );
  const unit = maximum >= 1_000_000 ? 1_000_000 : 1_000;
  const roughStep = maximum / unit / 4;
  const magnitude = 10 ** Math.floor(Math.log10(roughStep));
  const step =
    ([1, 2, 2.5, 5, 10].find((n) => n * magnitude >= roughStep) ?? 10) *
    magnitude;
  const top = maximum / unit;
  const ceiling = top * unit;
  const ticks = Array.from(
    { length: Math.floor(top / step) + 1 },
    (_, i) => i * step,
  );
  return (
    <figure className={styles.fundingPlot}>
      <figcaption>
        <div>
          <strong>Annual funding</strong>
          <span>Select a fiscal year</span>
        </div>
        <span>USD {unit === 1_000_000 ? "billions" : "millions"}</span>
      </figcaption>
      <div className={styles.plotSurface}>
        <div className={styles.plotScale} aria-hidden="true">
          {ticks.map((tick) => (
            <span
              key={tick}
              style={{ "--tick-position": 1 - tick / top } as CSSProperties}
            >
              <i>{Number(tick.toPrecision(3))}</i>
            </span>
          ))}
        </div>
        <div
          ref={yearRail}
          className={styles.plotColumns}
          role="group"
          aria-label="Fiscal year"
        >
          {series.map(({ fy, fact: item }) => (
            <div
              key={fy}
              className={styles.plotYear}
              data-selected={year === fy}
              data-year={fy}
              data-status={item?.status.toLowerCase()}
              data-comparison-year={comparisonYears?.includes(fy) ?? false}
              data-comparison-from={comparisonYears?.[0] === fy}
              style={
                {
                  "--bar-fraction":
                    Math.abs(item?.amountThousands ?? 0) / ceiling,
                } as CSSProperties
              }
            >
              <div className={styles.plotValue}>
                {item ? <FundingFigure fact={item} /> : "No figure"}
              </div>
              <button
                type="button"
                aria-pressed={year === fy}
                aria-label={`Select FY${fy}${item ? `, ${item.status}, ${formatAmount(item.amountThousands, item.units)}` : ", no figure in this collection"}`}
                data-chart-fact-id={item?.factId}
                onClick={() => onYear(fy)}
              >
                <span className={styles.plotTrack}>
                  {item && (
                    <span
                      className={styles.plotBar}
                      data-budget-bar
                      data-status={item.status.toLowerCase()}
                      style={{
                        height: `${(Math.abs(item.amountThousands) / ceiling) * 100}%`,
                      }}
                    />
                  )}
                </span>
                <span className={styles.plotYearLabel}><span className="sr-only">FY</span>{fy}</span>
                <span className={styles.plotStatus}>
                  {item?.status ?? "Not covered"}
                </span>
              </button>
            </div>
          ))}
        </div>
      </div>
    </figure>
  );
}

function CompareCard({
  variant,
  family,
  view,
}: {
  variant: F15Variant;
  family: F15FamilyPayload;
  view: FamilyView;
}) {
  const records = getVariantRecords(family, variant.id, view.purpose);
  return (
    <article className={styles.compareCard}>
      <span className={`t-label ${styles.eyebrow}`}>{variant.role}</span>
      <h3>{variant.name}</h3>
      <F15Schematic variant={variant.id} className={styles.compareSchematic} />
      <p>{variant.description}</p>
      <dl className={styles.metadata}>
        <div>
          <dt className="t-label">Crew</dt>
          <dd>{variant.crew}</dd>
        </div>
        <div>
          <dt className="t-label">Context</dt>
          <dd>{variant.era}</dd>
        </div>
      </dl>
      <ul>
        {variant.changes.map((change) => (
          <li key={change}>{change}</li>
        ))}
      </ul>
      <SourceLink
        source={family.sources.find((s) => variant.sourceIds.includes(s.id))}
        label="Variant evidence"
      />
      <div className={styles.compareRecords}>
        <span className={`t-label ${styles.eyebrow}`}>
          {FUNDING_CATEGORIES[view.purpose]} · FY{view.fy} · Separate records
        </span>
        {records.length ? (
          records.map((record) => {
            const fact = getRecordFact(record, view.fy);
            const shared =
              variant.recordLinks.find((l) => l.slug === record.slug)?.scope ===
              "shared";
            return (
              <div key={record.slug} className={styles.compareRecord}>
                <div>
                  <Link href={`/program/${record.slug}/`}>{record.title}</Link>
                  <small>
                    {record.identifierKind} {record.slug}
                    {shared ? " · Shared across variants" : ""}
                  </small>
                </div>
                <div>
                  {fact ? (
                    <>
                      <FundingFigure fact={fact} />
                      <small>
                        {fact.status} · {fact.exhibit} TOA
                      </small>
                    </>
                  ) : (
                    <small>No record for this year</small>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <p>
            No separately mapped{" "}
            {FUNDING_CATEGORIES[view.purpose].toLowerCase()} record in this
            collection.
          </p>
        )}
      </div>
    </article>
  );
}

const WORKSPACES = [
  "inspect",
  "funding",
  "field-notes",
  "history",
  "compare",
  "research",
] as const;
type Workspace = (typeof WORKSPACES)[number];
function readWorkspace(): Workspace {
  const hash = window.location.hash.slice(1);
  return WORKSPACES.includes(hash as Workspace)
    ? (hash as Workspace)
    : "inspect";
}

export function F15FamilyBrowser({ family, fundingLead }: { family: F15FamilyPayload; fundingLead?: ReactNode }) {
  const [workspace, setWorkspace] = useState<Workspace>("inspect");
  const workspaceNav = useRef<HTMLElement>(null);
  useEffect(() => {
    const restore = () => { setWorkspace(readWorkspace()); requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: "auto" })); };
    const frame = requestAnimationFrame(() => setWorkspace(readWorkspace()));
    window.addEventListener("hashchange", restore);
    window.addEventListener("popstate", restore);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("hashchange", restore);
      window.removeEventListener("popstate", restore);
    };
  }, []);
  function openWorkspace(next: Workspace, focusNavigation = false) {
    if (next !== workspace) trackReaderEvent("brief_selected", { program: "f-15", surface: "family", selection: next });
    setWorkspace(next);
    window.history.pushState(
      null,
      "",
      `${window.location.pathname}${window.location.search}#${next}`,
    );
    requestAnimationFrame(() => {
      // In-content links disappear with their workspace. Keep keyboard focus
      // on the visible destination instead of leaving the next Tab at the footer.
      if (focusNavigation) {
        workspaceNav.current?.querySelector<HTMLAnchorElement>(`a[href="#${next}"]`)?.focus({ preventScroll: true });
      }
      window.scrollTo({ top: 0, behavior: "auto" });
    });
  }

  function followWorkspace(
    event: MouseEvent<HTMLAnchorElement>,
    next: Workspace,
    beforeNavigate?: () => void,
  ) {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    event.preventDefault();
    beforeNavigate?.();
    openWorkspace(next, !workspaceNav.current?.contains(event.currentTarget));
  }

  const [view, setView] = useState<FamilyView>({
    ...F15_DEFAULT_VIEW,
    fy: Math.max(...family.years),
  });
  const [sound, setSound] = useState(false);
  const [saved, setSaved] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [showSource, setShowSource] = useState(false);
  const [showExplanation, setShowExplanation] = useState(false);
  const [copyFallback, setCopyFallback] = useState("");
  const audio = useRef<AudioContext | null>(null);
  const rail = useRef<HTMLDivElement>(null);
  const railGesture = useRef<{ x: number; y: number } | null>(null);
  const suppressClick = useRef(false);
  const { openPanel } = useContext(CitationPanelContext);
  const variant = family.variants.find((v) => v.id === view.variant)!;
  const records = getVariantRecords(family, view.variant, view.purpose);
  const record =
    records.find((r) => r.slug === view.record) ?? records[0] ?? null;
  const fact = record ? getRecordFact(record, view.fy) : null;
  const narrativeSource = record?.narratives.find(item => family.citations[item.factId]?.official_url);
  const receiptInputs = record
    ? getFundingInputs(record, fact, family.citations)
    : [];
  const comparison =
    record?.change &&
    record.change.fy === view.fy &&
    fact?.factId === record.change.toFactId
      ? record.change
      : null;
  const comparisonFrom = comparison
    ? record?.facts.find((item) => item.factId === comparison.fromFactId)
    : null;
  const documentSource =
    fact?.source.kind === "derived"
      ? record?.componentRows.find(
          (row) => row.fy === view.fy && row.source.officialUrl,
        )?.source
      : fact?.source;
  const compareVariant =
    family.variants.find((v) => v.id === view.compare) ?? null;
  const topic = family.topics.find(
    (t) => t.id === view.topic && t.variantIds.includes(view.variant),
  );
  const topicLabel = TOPICS.find((item) => item.id === view.topic)!.label;
  const context = family.knowledge.contexts.find(
    (item) => item.variant === view.variant && item.topic === view.topic,
  )!;
  const mappedRecords = getVariantRecords(family, view.variant);
  const selectedLink = variant.recordLinks.find(
    (link) => link.slug === record?.slug,
  );
  const allFacts = family.records.flatMap((r) => [
    ...r.facts,
    ...r.componentRows,
    ...(r.change ? [r.change] : []),
  ]);
  const savedFacts = saved
    .map((id) => allFacts.find((f) => f.factId === id))
    .filter((f): f is FamilyFundingFact => Boolean(f));

  useEffect(() => {
    const restore = () => {
      const restored = parseFamilyView(window.location.search, family.years);
      const available = getVariantRecords(family, restored.variant);
      if (
        !new URLSearchParams(window.location.search).has("purpose") &&
        available.length &&
        !available.some((item) => item.purpose === restored.purpose)
      ) {
        restored.purpose = available[0].purpose;
        restored.record = available[0].slug;
      }
      setView(restored);
      try {
        setSaved(
          readSavedFactIds(
            localStorage.getItem(STORAGE_KEY),
            new Set(
              family.records.flatMap((r) =>
                [
                  ...r.facts,
                  ...r.componentRows,
                  ...(r.change ? [r.change] : []),
                ].map((f) => f.factId),
              ),
            ),
          ),
        );
      } catch {
        /* Private browsing can disable storage. */
      }
    };
    const frame = requestAnimationFrame(restore);
    window.addEventListener("popstate", restore);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("popstate", restore);
      void audio.current?.close();
    };
  }, [family]);

  useEffect(() => {
    const container = rail.current;
    if (!container) return;
    const align = () => {
      const button = container.querySelector<HTMLButtonElement>(
        '[aria-pressed="true"]',
      );
      if (!button) return;
      // Scroll only the strip; scrollIntoView would also move the reader's page.
      const left = button.offsetLeft - container.offsetLeft;
      container.scrollLeft = Math.max(
        0,
        left - (container.clientWidth - button.clientWidth) / 2,
      );
    };
    align();
    const observer =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(align) : null;
    observer?.observe(container);
    return () => observer?.disconnect();
  }, [view.variant]);

  const tick = useCallback(
    (kind: "select" | "receipt" = "select", force = false) => {
      if (!sound && !force) return;
      try {
        audio.current ??= new AudioContext();
        const context = audio.current;
        if (context.state === "suspended")
          void context.resume().catch(() => {});
        const oscillator = context.createOscillator(),
          gain = context.createGain(),
          now = context.currentTime;
        oscillator.type = kind === "receipt" ? "sine" : "triangle";
        oscillator.frequency.setValueAtTime(
          kind === "receipt" ? 340 : 620,
          now,
        );
        oscillator.frequency.exponentialRampToValueAtTime(150, now + 0.035);
        gain.gain.setValueAtTime(0.025, now);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.045);
        oscillator.connect(gain);
        gain.connect(context.destination);
        oscillator.start(now);
        oscillator.stop(now + 0.05);
      } catch {
        setSound(false);
        setMessage(
          "Sound is unavailable in this browser. All controls remain available.",
        );
      }
    },
    [sound],
  );

  function changeView(patch: Partial<FamilyView>) {
    const next = { ...view, ...patch };
    if (next.compare === next.variant) next.compare = null;
    const linked = getVariantRecords(family, next.variant, next.purpose);
    if (!linked.some((item) => item.slug === next.record))
      next.record = linked[0]?.slug ?? "";
    const selectedRecord = linked.find((item) => item.slug === next.record);
    const selectedFact = selectedRecord ? getRecordFact(selectedRecord, next.fy) : null;
    if (next.record !== view.record || next.fy !== view.fy || next.variant !== view.variant || next.topic !== view.topic) {
      trackReaderEvent("funding_selected", { program: next.record, factId: selectedFact?.factId, fiscalYear: next.fy, measure: selectedFact?.measure, surface: "f15", selection: next.topic });
    }
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}?${serializeFamilyView(next)}${window.location.hash}`,
    );
    setView(next);
    setShowSource(false);
    setShowExplanation(false);
    setMessage("");
    tick();
  }

  function selectVariant(id: F15VariantId) {
    const available = getVariantRecords(family, id);
    const purpose = available.some((item) => item.purpose === view.purpose)
      ? view.purpose
      : (available[0]?.purpose ?? view.purpose);
    changeView({ variant: id, purpose });
  }
  function selectTopic(id: F15TopicId) {
    const selected = family.topics.find(
      (item) => item.id === id && item.variantIds.includes(view.variant),
    );
    const linked = selected?.recordSlugs
      .map((slug) => mappedRecords.find((item) => item.slug === slug))
      .find(Boolean);
    changeView({
      topic: id,
      ...(linked ? { record: linked.slug, purpose: linked.purpose } : {}),
    });
  }
  function openReceipt(target: FamilyFundingFact) {
    tick("receipt");
    openPanel(target.factId, figureContext(target));
  }
  function saveFact(target: FamilyFundingFact) {
    if (saved.includes(target.factId)) {
      setMessage("This receipt is already in your research tray.");
      return;
    }
    if (saved.length >= 12) {
      setMessage("Your tray holds 12 receipts. Remove one to save another.");
      return;
    }
    const next = [...saved, target.factId];
    setSaved(next);
    trackReaderEvent("receipt_saved", { program: target.recordSlug, factId: target.factId, fiscalYear: target.fy, measure: target.measure, surface: "f15", count: next.length });
    tick();
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setMessage("Receipt saved to your research tray on this device.");
    } catch {
      setMessage(
        "Receipt saved for this visit. This browser has disabled local storage.",
      );
    }
  }
  function removeFact(id: string) {
    const next = saved.filter((f) => f !== id);
    setSaved(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* In-memory tray still works. */
    }
  }
  async function copy(text: string, success: string, event?: ReaderEvent) {
    try {
      await navigator.clipboard.writeText(text);
      setMessage(success);
      setCopyFallback("");
      if (event) trackReaderEvent(event, { program: record?.slug, factId: fact?.factId, fiscalYear: fact?.fy, measure: fact?.measure, surface: "f15", ...(event === "receipts_exported" ? { count: savedFacts.length } : {}) });
    } catch {
      setCopyFallback(text);
      setMessage("Copy access is unavailable. Select and copy the text below.");
    }
  }
  function share() {
    void copy(
      `${window.location.origin}${window.location.pathname}?${serializeFamilyView({ ...view, record: record?.slug ?? "" })}#${workspace}`,
      "Link copied with your variant, funding record, year, topic, and comparison.",
      "view_shared",
    );
  }
  function copyAnswer() {
    if (!record || !fact || !family.citations[fact.factId]) return;
    const narrative = record.narratives.find((item) => family.citations[item.factId] && item.body.trim());
    const text = formatAnswerBrief({
      program: { name: record.title, code: record.slug },
      factId: fact.factId,
      citation: family.citations[fact.factId],
      figure: figureContext(fact),
      passage: narrative ? { factId: narrative.factId, citation: family.citations[narrative.factId], body: narrative.body } : undefined,
      permalink: `${window.location.origin}${window.location.pathname}?${serializeFamilyView({ ...view, record: record.slug })}#funding`,
    });
    void copy(text, ANSWER_COPY.copied, "answer_copied");
  }
  function exportResearch() {
    const notes = savedFacts
      .map((item) => {
        const parent = family.records.find((r) => r.slug === item.recordSlug)!;
        const citation = family.citations[item.factId];
        return `${item.exhibit} TOA · PB${item.edition} · ${item.status}\n${formatFootnote(footnoteInputFromCitation(citation, item.factId, { program: { name: parent.title, code: parent.slug }, figure: figureContext(item) }))}`;
      })
      .join("\n\n");
    void copy(
      notes,
      "Research citations copied with fiscal and source context.",
      "receipts_exported",
    );
  }

  return (
    <div
      className={styles.family}
      data-stage
      data-family-browser="f-15"
      data-workspace={workspace}
      data-pagefind-body
    >
      <div className={`spine ${styles.shell}`}>
        <F15FamilyHeader>
          <FundingAircraftSelect variant={view.variant} variants={family.variants} onChange={selectVariant} />
          <button className={styles.navShare} onClick={share}><Share2 size={14} /> Share view</button>
        </F15FamilyHeader>
        {fundingLead}
        <F15Navigation active={workspace} saved={saved.length} navRef={workspaceNav} onNavigate={followWorkspace} />
        <div className={styles.unifiedBar}>
          {/* The plate: title-to-plate gap ~16px so the family name owns
              the scrubber. The variant timeline is the model's selector,
              so it lives ON the model — a scrubber along the plate's
              bottom edge. Sound and share belong to the plate, not to a
              floating actions row 500px from the subtitle. */}
          <div hidden={workspace !== "inspect"} className={styles.plateBlock}>
            <div
              ref={rail}
              className={styles.rail}
              role="group"
              aria-label="Aircraft variant"
              onPointerDown={(event) => {
                railGesture.current = { x: event.clientX, y: event.clientY };
                suppressClick.current = false;
              }}
              onPointerCancel={() => {
                railGesture.current = null;
              }}
              onPointerUp={(event) => {
                const start = railGesture.current;
                railGesture.current = null;
                if (!start) return;
                const dx = event.clientX - start.x,
                  dy = event.clientY - start.y;
                if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.4) {
                  suppressClick.current = true;
                  const i = F15_VARIANT_IDS.indexOf(view.variant);
                  selectVariant(
                    F15_VARIANT_IDS[
                      Math.min(5, Math.max(0, i + (dx < 0 ? 1 : -1)))
                    ],
                  );
                }
              }}
            >
              {family.variants.map((item, i) => {
                return (
                <span key={item.id} className={styles.railItem}>
                <button
                  type="button"
                  className={styles.variantButton}
                  aria-label={`${item.name} ${item.nickname}`}
                  aria-pressed={view.variant === item.id}
                  onClick={() => {
                    if (suppressClick.current) {
                      suppressClick.current = false;
                      return;
                    }
                    selectVariant(item.id);
                  }}
                  onKeyDown={(event) => {
                    const index =
                      event.key === "ArrowRight"
                        ? (i + 1) % 6
                        : event.key === "ArrowLeft"
                          ? (i + 5) % 6
                          : event.key === "Home"
                            ? 0
                            : event.key === "End"
                              ? 5
                              : -1;
                    if (index >= 0) {
                      event.preventDefault();
                      selectVariant(F15_VARIANT_IDS[index]);
                      rail.current?.children[index]
                        ?.querySelector("button")
                        ?.focus();
                    }
                  }}
                >
                  <span>{item.name}</span>
                  <small>{item.nickname}</small>
                  {/* Dates identify the variant; the history view explains the chronology. */}
                  <span className={styles.variantYear}>
                    {item.era.match(/^\d{4}/)?.[0]}
                  </span>
                </button>
                </span>
                );
              })}
            </div>
            <div className={styles.modelCell}>
              <F15Model
                variant={view.variant}
                compareVariant={view.compare}
                topic={view.topic}
                showTopicControls={false}
                onTopicChange={selectTopic}
                onInteract={() => tick()}
                yearLabel={variant.era.match(/^\d{4}/)?.[0]}
              />
              <div className={styles.plateActions}>
                {/* "Sound off" exists only while the 3D scene is active —
                    on a static drawing it promises audio (six critics).
                    Hidden by CSS unless the instrument is [data-active]. */}
                <button
                  className={styles.soundToggle}
                  onClick={() => {
                    const next = !sound;
                    setSound(next);
                    if (next) tick("select", true);
                  }}
                  aria-pressed={sound}
                >
                  {sound ? <Volume2 size={14} /> : <VolumeX size={14} />}
                  Sound {sound ? "on" : "off"}
                </button>

              </div>
            </div>

          </div>

        </div>

        <section
          data-workspace-section="inspect"
          hidden={workspace !== "inspect"}
          className={styles.inspection}
          aria-label="Aircraft inspection"
        >
          <h2 className="sr-only">Aircraft inspection</h2>
          <div className={styles.inspectGrid}>
            {/* The plate itself now renders once, above the timeline (the
                plateBlock). This grid keeps only the topic rail and the
                prose. — removed the stale second <F15Model> that Kimi's
                iteration-4 pass was cut off before deleting. */}
            <div
              className={styles.topicBar}
              role="group"
              aria-label="Inspection topics"
            >
              {TOPICS.map((item, i) => (
                <button
                  key={item.id}
                  className={styles.topicButton}
                  aria-pressed={view.topic === item.id}
                  onClick={() => selectTopic(item.id)}
                >
                  <span>0{i + 1}</span>
                  {item.label}
                  <ChevronRight size={13} />
                </button>
              ))}
            </div>
            <section className={styles.brief} aria-label="Selected variant">
              {/* Heading first, then ONE column (six of six critics): the
                  spec block directly under the heading, then the cited
                  narrative, then the disclosures. The middle-column lede is
                  deleted — it paraphrased the cited narrative beside it;
                  the cited one stays. DOM order = reading order. */}
              <h4 className={styles.topicHeading}>{topicLabel}</h4>
              <dl className={styles.metadata}>
                <div>
                  <dt className="t-label">Role</dt>
                  <dd>{variant.role}</dd>
                </div>
                <div>
                  <dt className="t-label">Crew</dt>
                  <dd>{variant.crew}</dd>
                </div>
                <div>
                  <dt className="t-label">{variant.era.replace(/^\d{4}\s*·\s*/, "")}</dt>
                  <dd>{variant.era.match(/^\d{4}/)?.[0]}</dd>
                </div>
                <div>
                  <dt className="t-label">Source</dt>
                  <dd>
                    <SourceLink
                      source={family.sources.find((s) =>
                        variant.sourceIds.includes(s.id),
                      )}
                      label="Read the aircraft source"
                    />
                  </dd>
                </div>
              </dl>
              <div className={styles.briefTopic} data-family-topic={view.topic}>
                <p>{context.text}</p>
                <KnowledgeSources
                  ids={context.sourceIds}
                  sources={family.knowledge.sources}
                  compact
                />
                {topic && (
                  <details className={styles.topicFunding}>
                    <summary>Budget connection</summary>
                    <p>{topic.text}</p>
                    <button
                      className={styles.sourceLink}
                      onClick={() => {
                        tick("receipt");
                        openPanel(topic.factId);
                      }}
                    >
                      Read source passage
                      <FileText size={12} />
                    </button>
                    <a
                      href="#funding"
                      onClick={(event) =>
                        followWorkspace(event, "funding", () =>
                          selectTopic(view.topic),
                        )
                      }
                    >
                      Follow its funding record
                      <ArrowRight size={13} />
                    </a>
                  </details>
                )}
                {!topic && (
                  <a
                    href="#field-notes"
                    onClick={(event) => followWorkspace(event, "field-notes")}
                  >
                    Explore orders, operators & systems
                    <ArrowRight size={13} />
                  </a>
                )}
              </div>
            </section>
          </div>{" "}
          <a
            href="#funding"
            className={styles.nextChapter}
            onClick={(event) => followWorkspace(event, "funding")}
          >
            <span>Next, follow the public money</span>
            <strong>
              {variant.name} budget & receipts <ArrowRight size={22} />
            </strong>
          </a>
        </section>

        <section
          data-workspace-section="funding"
          hidden={workspace !== "funding"}
          className={styles.section}
          aria-labelledby="funding-heading"
        >
          <div className={styles.sectionHeading}>
            <div>
              <h2 id="funding-heading">Budget & receipts.</h2>
            </div>
            <p>Select the work. Choose a year. Open the original source.</p>
          </div>
          {record ? (
            <div className={styles.fundingGrid}>
              <article
                className={styles.fundingSheet}
                aria-label="Selected funding record"
                data-has-figure={Boolean(fact)}
              >
                <div className={styles.fundingSpread}>
                  <header className={styles.aircraftPlate} data-prose>
                    <span className={styles.plateRunningHead}>
                      United States Air Force
                    </span>
                    <h2 className={styles.plateTitle}>{variant.name}<span>Budget & receipts</span></h2>
                    <p className={styles.plateSummary}>Aircraft, software, testing and upgrades have separate budgets. Choose a record to see what it funds.</p>
                    <span className={styles.plateNickname}>{variant.nickname}</span>
                    <a
                      className={styles.plateAircraft}
                      href="#inspect"
                      onClick={(event) => followWorkspace(event, "inspect")}
                    >
                      <div className={styles.plateIllustration}>
                        <F15Schematic variant={view.variant} />
                      </div>
                      <span>
                        Inspect aircraft{" "}
                        <ArrowRight size={16} aria-hidden="true" />
                      </span>
                      <small>Selected aircraft configuration</small>
                    </a>
                  </header>
                  <div className={styles.fundingDocument}>
                    <div
                      className={styles.fundingContext}
                      role="group"
                      aria-label="Aircraft and funding record"
                    >
                      <div className={styles.recordControl}>
                        <label htmlFor="family-funding-record">
                          Funding record
                        </label>
                        <select
                          id="family-funding-record"
                          aria-label="Funding record"
                          value={record.slug}
                          onChange={(event) => {
                            const selected = mappedRecords.find(
                              (item) => item.slug === event.target.value,
                            );
                            if (selected)
                              changeView({
                                record: selected.slug,
                                purpose: selected.purpose,
                              });
                          }}
                        >
                          {(["buy", "upgrade", "develop"] as const)
                            .filter((purpose) =>
                              mappedRecords.some(
                                (item) => item.purpose === purpose,
                              ),
                            )
                            .map((purpose) => (
                              <optgroup
                                key={purpose}
                                label={FUNDING_CATEGORIES[purpose]}
                              >
                                {mappedRecords
                                  .filter((item) => item.purpose === purpose)
                                  .map((item) => (
                                    <option value={item.slug} key={item.slug}>
                                      {RECORD_GUIDES[item.slug]?.title ??
                                        item.title}
                                    </option>
                                  ))}
                              </optgroup>
                            ))}
                        </select>
                      </div>

                    </div>

                    {/* A <section> is a landmark region only while it has an
                        accessible name. "Budget source trail" is true only when a
                        cited figure exists for the selected year; the coverage
                        note for a missing year is a container, not a trail —
                        f15-family-browser.test.tsx holds the region absent then. */}
                    <section
                      className={styles.receiptPaper}
                      aria-label={fact ? "Budget source trail" : undefined}
                    >
                      {fact ? (
                        <>
                        <header className={styles.receiptDocumentLine}>
                          <p title={documentSource?.title ?? fact.source.title}>
                            {fact.exhibit}
                            {" · "}
                            {(documentSource?.title ?? fact.source.title)
                              .replace(
                                /^FY\d{4} Department of Defense Budget: /,
                                "",
                              )
                              .replace(/\s+\([RP]-1\)$/, "")}
                          </p>
                          <Link
                            className={styles.recordLink}
                            href={`/program/${record.slug}/`}
                          >
                            {record.identifierKind === "BLI"
                              ? "Budget line"
                              : "Program element"}{" "}
                            {record.slug}
                          </Link>
                        </header>
                        <div className={styles.receiptHeadline}>
                          <SourceDocumentLinks citation={family.citations[fact.factId]} citations={family.citations} factId={fact.factId} program={record.slug} surface="f15" compact />
                          <div
                            className={`${styles.statementTotal} ${styles.receiptTotal}`}
                          >
                            <h3
                              aria-live="polite"
                              aria-atomic="true"
                            >{`FY${view.fy} ${fact.status === "Request" ? "budget request" : fact.status === "Enacted" ? "enacted funding" : fact.status === "Actuals" ? "reported actuals" : `${fact.status.toLowerCase()} funding`}`}</h3>
                            <p className={`t-figure t-figure--7 ${styles.statementAmount}`}>
                              <FundingFigure fact={fact} />
                            </p>
                            <span className="sr-only">
                              {fact.status === "Request"
                                ? "Total requested"
                                : fact.status === "Enacted"
                                  ? "Total enacted"
                                  : "Reported total"}
                            </span>
                          </div>
                          {comparison && comparisonFrom && (
                            <div className={styles.statementComparison}>
                              <h3>
                                <FundingFigure fact={comparison} />{" "}
                                <span>
                                  {comparison.amountThousands > 0
                                    ? "more than"
                                    : "change from"}{" "}
                                  FY{comparisonFrom.fy} {comparisonFrom.status.toLowerCase()}
                                </span>
                              </h3>
                              <p className="sr-only">
                                FY{fact.fy} {fact.status.toLowerCase()} compared
                                with FY{comparisonFrom.fy}{" "}
                                {comparisonFrom.status.toLowerCase()} funding.
                              </p>
                            </div>
                          )}
                        <footer className={styles.receiptFooter}>
                          <div>
                            <h3 className="sr-only">{`FY${view.fy} ${fact.status.toLowerCase()} — ${receiptInputs.length > 0 ? "source rows" : "source record"}`}</h3>
                            <p className={styles.statementBasis}>
                              Total obligation authority · Source edition:
                              President’s Budget {fact.edition}.
                            </p>

                          </div>
                          <div className={styles.officialReceiptActions}>
                            <button
                              className={styles.statementReceipt}
                              onClick={() => openReceipt(fact)}
                            >
                              <FileText size={16} /> Open budget receipt
                            </button>
                            <div>
                              <button className={styles.saveReceipt} onClick={copyAnswer}>
                                <Copy size={14} /> {ANSWER_COPY.button}
                              </button>
                              <button
                                className={styles.saveReceipt}
                                onClick={() => saveFact(fact)}
                              >
                                {saved.includes(fact.factId) ? (
                                  <Check size={14} />
                                ) : (
                                  <Bookmark size={14} />
                                )}
                                {saved.includes(fact.factId)
                                  ? "Saved to research"
                                  : "Save receipt"}
                              </button>
                            </div>
                          </div>
                        </footer>
                        <p className={styles.receiptAccounting}>
                          Funding authority, not payments or aircraft unit prices.
                        </p>
                        </div>
                        </>
                      ) : (
                      <div className={styles.fundingAbsence}>
                        <span>Coverage note</span>
                        <h3>No matching TOA figure for FY{view.fy}.</h3>
                        {narrativeSource && <>
                          <p>Read this record’s J-book narrative. It does not supply the missing FY{view.fy} TOA figure.</p>
                          <SourceDocumentLinks citation={family.citations[narrativeSource.factId]} citations={family.citations} factId={narrativeSource.factId} program={record.slug} surface="f15" compact />
                        </>}
                        <p>
                          {record.absenceNotes.find((n) => n.fy === view.fy)
                            ?.text ??
                            "This collection has no cited figure for this year. Missing coverage is not zero spending."}
                        </p>
                        <Link
                          className={styles.recordLink}
                          href={`/program/${record.slug}/`}
                        >
                          {record.identifierKind === "BLI"
                            ? "Budget line"
                            : "Program element"}{" "}
                          {record.slug}
                        </Link>
                      </div>
                      )}
                  <div className={styles.fundingChartFrame}>
                    <BudgetTimeline
                      record={record}
                      year={view.fy}
                      years={family.years}
                      comparisonYears={
                        fact && comparison && comparisonFrom
                          ? [comparisonFrom.fy, fact.fy]
                          : undefined
                      }
                      onYear={(fy) => changeView({ fy })}
                    />
                    <p className={styles.chartReadingNote}>
                      {fact
                        ? "Actuals report past budget authority. Enacted funding is approved; requests are proposals."
                        : "Missing coverage is not zero spending. Select an available year to inspect its source."}
                    </p>
                  </div>
                      {fact && (
                        <>
                        <div className={styles.recordIntroduction} data-prose>
                          <h3>What this funds</h3>
                          <p className={styles.recordScope}>
                            {record.slug === "F015EX"
                              ? "New aircraft, in-service modifications, support equipment and facilities."
                              : record.scopeNote.replace(
                                  /\bBLI\b/g,
                                  "budget line",
                                )}
                          </p>
                          {selectedLink?.scope === "shared" && (
                            <p className={styles.recordShared}>
                              {selectedLink.note}
                            </p>
                          )}
                        </div>
                        {receiptInputs.length > 0 ? (
                          <FundingSourceRows inputs={receiptInputs} />
                        ) : (
                          <p className={styles.directSourceLocation}>
                            {fact.source.locator}
                          </p>
                        )}
                        </>
                      )}
                    </section>
                  </div>
                </div>
                <div className={styles.receiptBody}>
                  {showExplanation && record.narratives.length > 0 && (
                    <div id="family-narrative" className={styles.narrative}>
                      <h4>{record.narratives[0].title}</h4>
                      <p
                        data-source-text="narrative"
                        data-cite-fact-id={record.narratives[0].factId}
                      >
                        {record.narratives[0].body}
                      </p>
                      <button
                        className={styles.sourceLink}
                        onClick={() => openPanel(record.narratives[0].factId)}
                      >
                        Read source passage
                        <ArrowRight size={12} />
                      </button>
                    </div>
                  )}
                  <details className={styles.yearRows}>
                    <summary>
                      <span>
                        Source data{" "}
                        <small>All fiscal years and funding measures</small>
                      </span>
                      <span aria-hidden="true">
                        {record.facts.length} records <ChevronRight size={16} />
                      </span>
                    </summary>
                    {fact && (
                      <div className={styles.receiptSourceDetails}>
                        <span>
                          FY{fact.fy} {fact.status.toLowerCase()} · {fact.source.kind === "derived"
                            ? "Calculated from cited source rows"
                            : "Traced to its source location"}
                        </span>
                        <SourceLink source={documentSource ?? fact.source} label="Official document" />
                      </div>
                    )}
                    {record.slug === "F015EX" && (
                      <p className={styles.fundingDefinitions}>
                        {record.scopeNote.replace(/\bBLI\b/g, "budget line")}
                      </p>
                    )}
                    <p className={styles.fundingDefinitions}>
                      Research & development funds design, software and testing.
                      Procurement funds aircraft, equipment and modifications to
                      the existing fleet. Each record keeps its own scope;
                      shared records do not allocate a cost to each variant.
                    </p>
                    <div className={styles.actions} style={{ marginTop: 16 }}>
                      <button
                        className={styles.action}
                        onClick={() => {
                          setShowSource(!showSource);
                          tick("receipt");
                        }}
                        aria-expanded={showSource}
                        aria-controls="family-source-preview"
                        disabled={!fact}
                      >
                        <Layers size={14} />
                        {showSource
                          ? "Hide source context"
                          : "Inspect source context"}
                      </button>
                      {record.narratives.length > 0 && (
                        <button
                          className={styles.action}
                          onClick={() => setShowExplanation(!showExplanation)}
                          aria-expanded={showExplanation}
                          aria-controls="family-narrative"
                        >
                          Read the budget explanation
                          <ChevronRight size={13} />
                        </button>
                      )}
                    </div>
                    {showSource && fact && (
                      <div
                        id="family-source-preview"
                        className={styles.sourcePreview}
                      >
                        <h4>{fact.source.title}</h4>
                        <p>
                          {fact.source.locator ??
                            "Open the receipt to inspect its source inputs."}
                        </p>
                        <p>
                          Recorded units: {fact.units}.{" "}
                          {fact.source.retrievedAt
                            ? `Source retrieved ${fact.source.retrievedAt.slice(0, 10)}.`
                            : ""}
                        </p>
                        <SourceLink
                          source={fact.source}
                          label="Open official document"
                        />
                      </div>
                    )}

                    <nav className={styles.trail} aria-label="Evidence trail">
                      <a
                        href="#inspect"
                        onClick={(event) => followWorkspace(event, "inspect")}
                      >
                        {variant.name}
                      </a>
                      <ChevronRight />
                      <span>
                        {record.identifierKind} {record.slug}
                      </span>
                      <ChevronRight />
                      <span>FY{view.fy}</span>
                      {fact && (
                        <>
                          <ChevronRight />
                          <button onClick={() => openReceipt(fact)}>
                            Source #{fact.publicId}
                          </button>
                        </>
                      )}
                    </nav>

                    <div className={styles.tableWrap}>
                      <table className={styles.table}>
                        <caption className="sr-only">
                          Cited fiscal figures for {record.title}; fiscal status
                          is shown for every row.
                        </caption>
                        <thead>
                          <tr>
                            <th className="t-label">Year / status</th>
                            <th className="t-label">Basis</th>
                            <th className="t-label">Cited amount</th>
                          </tr>
                        </thead>
                        <tbody>
                          {record.facts.map((item) => (
                            <tr key={item.factId}>
                              <td>
                                FY{item.fy} · {item.status}
                              </td>
                              <td>
                                {item.exhibit} TOA · PB{item.edition}
                              </td>
                              <td>
                                <FundingFigure fact={item} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className={styles.scope}>
                      Reported totals and any discretionary/reconciliation
                      splits are alternative views of the same line; do not add
                      them together.
                    </p>
                    {record.componentRows.filter((item) => item.fy === view.fy)
                      .length > 0 && (
                      <details className={styles.notes}>
                        <summary>Underlying FY{view.fy} workbook rows</summary>
                        <p>
                          These are the source rows behind the record, not
                          additional funding.
                        </p>
                        <div className={styles.tableWrap}>
                          <table className={styles.table}>
                            <thead>
                              <tr>
                                <th className="t-label">Source row / status</th>
                                <th className="t-label">Cited amount</th>
                              </tr>
                            </thead>
                            <tbody>
                              {record.componentRows
                                .filter((item) => item.fy === view.fy)
                                .map((item) => (
                                  <tr key={item.factId}>
                                    <td>
                                      {item.label ?? item.source.locator}
                                      <small className={`t-label ${styles.eyebrow}`}>
                                        {item.status}
                                      </small>
                                    </td>
                                    <td>
                                      <FundingFigure fact={item} />
                                    </td>
                                  </tr>
                                ))}
                            </tbody>
                          </table>
                        </div>
                      </details>
                    )}
                  </details>
                </div>
              </article>
            </div>
          ) : (
            <div className={styles.empty}>
              <h3>
                {mappedRecords.length
                  ? `${variant.name}: follow its development and upgrades.`
                  : `${variant.name}: an earlier chapter of the Eagle.`}
              </h3>
              <p>{variant.coverageNote}</p>
              <div className={styles.actions}>
                <a
                  className={styles.action}
                  href="#field-notes"
                  onClick={(event) => followWorkspace(event, "field-notes")}
                >
                  Country histories, orders & suppliers
                  <ArrowRight size={13} />
                </a>
                {mappedRecords.length ? (
                  <button
                    className={styles.action}
                    onClick={() =>
                      changeView({ purpose: mappedRecords[0].purpose })
                    }
                  >
                    See available funding records
                    <ArrowRight size={13} />
                  </button>
                ) : (
                  <button
                    className={styles.action}
                    onClick={() =>
                      changeView({ variant: "EX", purpose: "buy" })
                    }
                  >
                    Explore F-15EX funding
                    <ArrowRight size={13} />
                  </button>
                )}
              </div>
            </div>
          )}
        </section>

        <div hidden={workspace !== "field-notes"}>
          <F15KnowledgeSection
            variant={view.variant}
            onCopy={(text, success) => {
              void copy(text, success);
            }}
            onInteract={() => tick()}
          />
        </div>

        <section
          data-workspace-section="history"
          hidden={workspace !== "history"}
          className={styles.section}
          aria-labelledby="history-heading"
        >
          <div className={styles.sectionHeading}>
            <div>
              <span className={`t-label ${styles.eyebrow}`}>A short history</span>
              <h2 id="history-heading">
                Five moments in the Eagle’s evolution.
              </h2>
            </div>
            <p>
              From the first flight to a new generation. Select a milestone to
              inspect its aircraft.
            </p>
          </div>
          <div className={styles.history}>
            {family.milestones.map((milestone) => (
              <div key={`${milestone.year}-${milestone.label}`}>
                <span className={styles.eyebrow}>{milestone.year}</span>
                <h3>{milestone.label}</h3>
                <div className={styles.historyButtons}>
                  {milestone.variantIds.map((id) => (
                    <button
                      key={id}
                      aria-pressed={view.variant === id}
                      onClick={() => selectVariant(id)}
                    >
                      F-15{id}
                    </button>
                  ))}
                </div>
                <p>
                  <SourceLink
                    source={family.sources.find(
                      (s) => s.id === milestone.sourceId,
                    )}
                    label="Milestone source"
                  />
                </p>
              </div>
            ))}
          </div>
          <details className={styles.notes}>
            <summary>How aircraft families relate to program elements</summary>
            <p>
              A family is a browsing group. Aircraft variants, modifications,
              and budget records have a many-to-many relationship. A single PE
              or BLI can support several variants, and one aircraft can receive
              development, procurement, and upgrade funding from different
              records.
            </p>
            <p>
              {family.coverageNote} The source-backed mappings here are curated;
              similar names alone do not establish a relationship.
            </p>
          </details>
        </section>

        <div
          className={styles.utilityGrid}
          hidden={workspace !== "compare" && workspace !== "research"}
          data-expanded={Boolean(compareVariant) || savedFacts.length > 0}
        >
          <section
            data-workspace-section="compare"
            hidden={workspace !== "compare"}
            className={styles.section}
            aria-labelledby="compare-heading"
          >
            <div className={styles.sectionHeading}>
              <div>
                <h2 id="compare-heading">Compare aircraft</h2>
              </div>
              <label className={styles.yearControl}>
                Compare {variant.name} with
                <select
                  className={styles.compareSelect}
                  value={view.compare ?? ""}
                  onChange={(event) =>
                    changeView({
                      compare: (event.target.value as F15VariantId) || null,
                    })
                  }
                >
                  <option value="">Choose a variant</option>
                  {family.variants
                    .filter((v) => v.id !== view.variant)
                    .map((v) => (
                      <option value={v.id} key={v.id}>
                        {v.name}
                      </option>
                    ))}
                </select>
              </label>
            </div>
            {compareVariant ? (
              <>
                <div className={styles.compareGrid}>
                  <CompareCard variant={variant} family={family} view={view} />
                  <CompareCard
                    variant={compareVariant}
                    family={family}
                    view={view}
                  />
                </div>
                <p className={styles.scope} style={{ marginTop: 14 }}>
                  Comparison uses FY{view.fy} and the selected record’s
                  category: {FUNDING_CATEGORIES[view.purpose].toLowerCase()}. A
                  shared record appearing in both columns is the same funding,
                  counted once. The model uses an aligned overlay; public
                  schematics do not capture every internal difference.
                </p>
                <a
                  href="#inspect"
                  onClick={(event) => followWorkspace(event, "inspect")}
                  className={styles.sourceLink}
                  style={{ marginTop: 12 }}
                >
                  Inspect the aligned models
                  <ArrowRight size={12} />
                </a>
              </>
            ) : (
              <div className={styles.comparePrompt}>
                <p>
                  Compare missions, equipment and funding side by side. Add a
                  second aircraft to the model as an aligned outline.
                </p>
                <button
                  className={styles.action}
                  style={{ marginTop: 16 }}
                  onClick={() =>
                    changeView({ compare: view.variant === "E" ? "EX" : "E" })
                  }
                >
                  Compare with {view.variant === "E" ? "F-15EX" : "F-15E"}
                  <ArrowRight size={13} />
                </button>
              </div>
            )}
          </section>

          <section
            data-workspace-section="research"
            hidden={workspace !== "research"}
            className={styles.section}
            aria-labelledby="research-heading"
          >
            <div className={styles.research} data-empty={!savedFacts.length}>
              <div className={styles.researchHeader}>
                <div>
                  <h2
                    id="research-heading"
                    style={{ marginTop: 7 }}
                  >
                    Your research tray
                  </h2>
                </div>
                <button
                  className={styles.action}
                  onClick={exportResearch}
                  disabled={!savedFacts.length}
                >
                  <Copy size={14} />
                  Copy all citations
                </button>
              </div>
              {savedFacts.length > 0 && (
                <p>
                  Saved on this device. Each citation keeps its fiscal context,
                  source locator and fact link.
                </p>
              )}
              {savedFacts.length ? (
                <div className={styles.savedList}>
                  {savedFacts.map((item) => (
                    <article className={styles.savedItem} key={item.factId}>
                      <div>
                        <strong>
                          {
                            family.records.find(
                              (r) => r.slug === item.recordSlug,
                            )?.title
                          }
                        </strong>
                        <small>
                          {item.recordSlug} · FY{item.fy} · {item.status} ·{" "}
                          {item.exhibit} TOA · #{item.publicId}
                        </small>
                      </div>
                      <div className={styles.actions}>
                        <FundingFigure fact={item} />
                        <button
                          className={styles.action}
                          onClick={() => openReceipt(item)}
                          aria-label={`Open saved receipt ${item.publicId}`}
                        >
                          <FileText size={14} />
                        </button>
                        <button
                          className={styles.action}
                          onClick={() => removeFact(item.factId)}
                          aria-label={`Remove saved receipt ${item.publicId}`}
                        >
                          <X size={14} />
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <p>
                  Save a budget receipt to collect its figure, fiscal context
                  and source here.
                </p>
              )}
            </div>
            <details className={styles.notes}>
              <summary>Aircraft references & mapping evidence</summary>
              <div className={styles.sources}>
                {family.sources.map((source) => (
                  <a
                    key={source.id}
                    href={source.officialUrl ?? source.receiptUrl}
                    onClick={() => { if (source.officialUrl) trackReaderEvent("official_source_opened", { program: "f-15", factId: source.factId, surface: "f15" }); }}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <FileText
                      size={16}
                      style={{ flexShrink: 0, marginTop: 2 }}
                    />
                    <span>
                      {source.title}
                      <small>{source.locator ?? source.kind}</small>
                    </span>
                    <ExternalLink
                      size={12}
                      style={{ flexShrink: 0, marginLeft: "auto" }}
                    />
                  </a>
                ))}
              </div>
            </details>
          </section>
        </div>
        <div
          className={styles.status}
          role="status"
          aria-live="polite"
          aria-label="Research feedback"
        >
          {message}
        </div>
        {copyFallback && (
          <label className={styles.scope}>
            Copy this text
            <textarea
              readOnly
              value={copyFallback}
              rows={5}
              style={{
                display: "block",
                width: "100%",
                padding: 12,
                border: "1px solid var(--rule)",
                marginTop: 8,
              }}
              onFocus={(event) => event.target.select()}
            />
          </label>
        )}
        <noscript>
          <p className={styles.scope}>
            The default F-15EX funding record and source links are available
            here. Enable JavaScript to switch variants and use the model.{" "}
            <Link href="/program/F015EX/">
              Open the complete F-15EX dossier.
            </Link>
          </p>
        </noscript>
      </div>
    </div>
  );
}
