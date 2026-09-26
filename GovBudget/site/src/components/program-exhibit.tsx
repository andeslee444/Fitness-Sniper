"use client";

import { useContext, useEffect, useRef, useState, type CSSProperties } from "react";
import Link from "next/link";
import Script from "next/script";
import { ArrowDown, ArrowRight, Box, Check, Copy, FileText, RotateCcw } from "lucide-react";
import { Cite, CitationPanelContext, type ExhibitFamily } from "@/components/cite";
import type { CitationsMap, ProgramNarrative, SummaryCard } from "@/lib/data";
import type { ProgramExhibitConfig } from "@/lib/program-exhibits";
import { PLATE_DESCS } from "@/lib/program-exhibits";
import { ANSWER_COPY, answerSourceExcerpt, formatAnswerBrief } from "@/lib/answer-brief";
import { trackReaderEvent } from "@/lib/reader-events";
import styles from "./program-exhibit.module.css";

interface Props {
  config: ProgramExhibitConfig;
  cards: SummaryCard[];
  exhibitFamily: ExhibitFamily;
  reconciliationKeys: string[];
  narratives?: ProgramNarrative[];
  citations?: CitationsMap;
}

export function ProgramExhibit({ config, cards, exhibitFamily, reconciliationKeys, narratives = [], citations = {} }: Props) {
  const available = cards.filter(c => c.key !== "change" && c.value !== null && c.fid && c.units && c.dataset && c.basis);
  const [topicIndex, setTopicIndex] = useState(0);
  const selectedTopicRef = useRef(0);
  const [yearKey, setYearKey] = useState<string>(available[available.length - 1]?.key ?? "fy2026");
  const [interactive, setInteractive] = useState(false);
  const [sceneStatus, setSceneStatus] = useState<"poster" | "loading" | "ready" | "error">("poster");
  const [blueprint, setBlueprint] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [answerCopied, setAnswerCopied] = useState(false);
  const [copyFallback, setCopyFallback] = useState("");
  const [reset, setReset] = useState(0);
  const scene = useRef<HTMLElement>(null);
  const { openPanel } = useContext(CitationPanelContext);
  const topic = config.topics[topicIndex];
  const card = available.find(c => c.key === yearKey) ?? available[available.length - 1];
  const narrative = narratives.find(item => item.fact_id === topic.factId);
  const hasAnswer = Boolean(card?.fid && citations[card.fid] && citations[topic.factId] && narrative && answerSourceExcerpt(narrative.body, topic.evidenceContains));
  const answerPilot = config.slug === "2013" || config.slug === "0602668D8Z";

  function selectTopic(index: number) {
    const changed = index !== selectedTopicRef.current;
    selectedTopicRef.current = index;
    setTopicIndex(index); setCopied(false); setCopyError(false); setAnswerCopied(false); setCopyFallback("");
    if (changed) trackReaderEvent("brief_selected", { program: config.slug, surface: "program-exhibit", selection: config.topics[index].id });
  }

  useEffect(() => {
    // Read a shared view after hydration; the server always supplies a usable poster.
    const readHash = () => {
      if (!window.location.hash.startsWith("#exhibit?")) return;
      const state = new URLSearchParams(window.location.hash.slice(9));
      const index = config.topics.findIndex(t => t.id === state.get("topic"));
      if (index >= 0) { selectedTopicRef.current = index; setTopicIndex(index); }
      const key = state.get("year");
      if (cards.some(c => c.key === key && c.key !== "change" && c.value !== null && c.fid && c.units && c.dataset && c.basis)) setYearKey(key!);
      setBlueprint(state.get("view") === "blueprint");
      document.getElementById("exhibit")?.scrollIntoView({ block: "start" });
    };
    const frame = requestAnimationFrame(readHash);
    window.addEventListener("hashchange", readHash);
    return () => { cancelAnimationFrame(frame); window.removeEventListener("hashchange", readHash); };
  }, [config, cards]);

  useEffect(() => {
    const el = scene.current;
    if (!el) return;
    const ready = () => setSceneStatus("ready");
    const fail = () => { setSceneStatus("error"); setInteractive(false); };
    const select = (event: Event) => {
      const id = (event as CustomEvent<{ topic: string }>).detail.topic;
      const index = config.topics.findIndex(t => t.id === id);
      if (index >= 0) {
        const changed = index !== selectedTopicRef.current;
        selectedTopicRef.current = index;
        setTopicIndex(index); setCopied(false); setCopyError(false); setAnswerCopied(false); setCopyFallback("");
        if (changed) trackReaderEvent("brief_selected", { program: config.slug, surface: "program-exhibit", selection: id });
      }
    };
    el.addEventListener("scene-ready", ready);
    el.addEventListener("scene-error", fail);
    el.addEventListener("topic-select", select);
    return () => { el.removeEventListener("scene-ready", ready); el.removeEventListener("scene-error", fail); el.removeEventListener("topic-select", select); };
  }, [interactive, config]);

  function selectedView() {
    const hash = new URLSearchParams({ topic: topic.id, year: yearKey, view: blueprint ? "blueprint" : "exhibit" });
    const url = `${window.location.origin}${window.location.pathname}#exhibit?${hash}`;
    return url;
  }
  async function copyView() {
    const url = selectedView();
    window.history.replaceState(null, "", url);
    try {
      await navigator.clipboard.writeText(url); setCopied(true); setCopyError(false); setCopyFallback(""); setAnswerCopied(false);
      trackReaderEvent("view_shared", { program: config.slug, surface: "program-exhibit", selection: topic.id, fiscalYear: card?.fy, measure: card?.measure });
    }
    catch { setCopyError(true); setCopyFallback(url); setAnswerCopied(false); setCopied(false); }
  }
  async function copyAnswer() {
    if (!hasAnswer || !card?.fid || !card.basis || !narrative) return;
    const text = formatAnswerBrief({
      program: { name: config.name, code: config.slug },
      factId: card.fid, citation: citations[card.fid],
      figure: { value: card.value, units: card.units, fy: card.fy, measure: card.measure, basis: card.basis, edition: card.edition, entity: config.slug },
      passage: { factId: topic.factId, citation: citations[topic.factId], body: narrative.body, anchor: topic.evidenceContains },
      permalink: selectedView(),
    });
    try {
      await navigator.clipboard.writeText(text); setAnswerCopied(true); setCopyError(false); setCopyFallback(""); setCopied(false);
      trackReaderEvent("answer_copied", { program: config.slug, factId: card.fid, fiscalYear: card.fy, measure: card.measure, surface: "program-exhibit", selection: topic.id });
    } catch { setCopyError(true); setCopyFallback(text); setAnswerCopied(false); setCopied(false); }
  }

  return (
    <section id="exhibit" className={styles.exhibit} aria-label={`${config.name} visual exhibit`} data-program-exhibit={config.slug}>
      <div className={`t-label ${styles.topline}`}><span>{config.eyebrow} / Field guide</span><Link href="/explore/">All exhibits <ArrowRight size={14} /></Link></div>
      <div className={styles.heading}><h2>{config.title}</h2><span className={`t-label ${styles.pilot}`}>Pilot exhibit</span></div>
      {config.related && <nav className={styles.fundingLines} aria-label="F-35 funding line">
        {config.related.map(r => <Link key={r.slug} href={`/program/${r.slug}/#exhibit`} aria-current={r.slug === config.slug ? "page" : undefined}>{r.label}<ArrowRight size={13}/></Link>)}
      </nav>}
      <div className={styles.stage}>
        {/* The hand-drawn plate by external <use> (never inlined — the
            homepage weight gate). The container's color sets the register:
            light ink on this dark vitrine, hatch tones for dark grounds.
            The stage keeps the viewBox's 1.875 aspect so the hotspot
            anchors (measured as % of the viewBox) land exactly. */}
        <svg viewBox="0 0 1800 960" role="img" aria-label={config.caption} className={styles.plate} data-illustration="">
          <desc>{PLATE_DESCS[config.subject]}</desc>
          <use href={`/exhibits/plates/${config.subject}.svg#${config.subject}-plate`} />
        </svg>
        {interactive && <fiscal-scene ref={scene} src={`/exhibits/${config.subject}.glb`} subject={config.subject}
          selected={topic.id} blueprint={String(blueprint)} reset={String(reset)}
          topics={JSON.stringify(config.topics.map(t => ({ id: t.id, label: t.label })))}
          aria-label={`Interactive ${config.name} model. Use arrow keys to rotate, plus or minus to zoom.`}
          className={styles.scene}/>}
        {!interactive && config.topics.map((t,i) => <button key={t.id} className={`${styles.hotspot} ${topicIndex===i ? styles.selectedHotspot : ""}`}
          style={{left:`${t.position[0]}%`,"--hotspot-y":`${t.position[1]}%`} as CSSProperties} onClick={() => selectTopic(i)}
          aria-label={`Explore ${t.label}`} aria-pressed={topicIndex===i}><span>0{i+1}</span><span className={styles.hotspotLabel}>{t.label}</span></button>)}
        <div className={styles.stageLabel}>Illustrative geometry <span>·</span> {sceneStatus === "ready" ? "Drag to rotate" : "Select a funding topic"}</div>
        <div className={styles.viewerControls}>
          {!interactive ? <button onClick={() => {setInteractive(true);setSceneStatus("loading");}}><Box size={16}/> Explore in 3D</button> : <>
            <button aria-pressed={blueprint} onClick={() => {setBlueprint(v=>!v);setCopied(false);setCopyError(false);}}>{blueprint ? "Solid view" : "Blueprint view"}</button>
            <button onClick={() => setReset(v=>v+1)} aria-label="Reset model view"><RotateCcw size={15}/></button>
            <button onClick={() => {setInteractive(false);setSceneStatus("poster");}}>Still image</button>
          </>}
        </div>
        {sceneStatus === "loading" && <span role="status" className={styles.status}>Loading interactive model…</span>}
      </div>
      {sceneStatus === "error" && <p role="status" className={styles.error}>Interactive 3D is unavailable in this browser. The illustration, explanations, and sources are available below.</p>}
      <div className={styles.topics} role="tablist" aria-label="Funding topics">
        {config.topics.map((t,i) => <button key={t.id} id={`exhibit-tab-${t.id}`} role="tab" aria-selected={topicIndex===i}
          aria-controls="exhibit-explanation" tabIndex={topicIndex===i ? 0 : -1}
          onClick={() => selectTopic(i)}
          onKeyDown={e => {
            const next = e.key === "ArrowRight" ? (i+1)%config.topics.length : e.key === "ArrowLeft" ? (i+config.topics.length-1)%config.topics.length : e.key === "Home" ? 0 : e.key === "End" ? config.topics.length-1 : -1;
            if(next<0)return;e.preventDefault();selectTopic(next);document.getElementById(`exhibit-tab-${config.topics[next].id}`)?.focus();
          }}><span>0{i+1}</span>{t.label}<ArrowRight size={15}/></button>)}
      </div>
      <div className={styles.receipt}>
        <div id="exhibit-explanation" role="tabpanel" aria-labelledby={`exhibit-tab-${topic.id}`} tabIndex={0} className={styles.explanation}>
          <span className={`t-label ${styles.overline}`}>What the program supports</span><h3>{topic.label}</h3>
          <p data-exhibit-claim={topic.factId}>{topic.text}</p>
          <button className={styles.sourceButton} onClick={() => openPanel(topic.factId)} data-exhibit-source={topic.factId}><FileText size={16}/>Read the source passage<ArrowRight size={15}/></button>
        </div>
        <div className={styles.budget}>
          <label className={`t-label ${styles.overline}`} htmlFor="exhibit-year">Program funding</label>
          <select id="exhibit-year" value={yearKey} onChange={e => {
            const selected = available.find(item => item.key === e.target.value);
            setYearKey(e.target.value);setCopied(false);setCopyError(false);setAnswerCopied(false);setCopyFallback("");
            trackReaderEvent("funding_selected", { program: config.slug, factId: selected?.fid ?? undefined, fiscalYear: selected?.fy, measure: selected?.measure, surface: "program-exhibit" });
          }}>
            {available.map(c => <option key={c.key} value={c.key}>FY{c.fy} {c.measure === "actuals" ? "Actuals" : c.measure === "enacted" ? "Enacted" : c.measure === "request" ? "Request" : "Total"}</option>)}
          </select>
          {card && <div className={`t-figure t-figure--5 ${styles.amount}`}><Cite value={card.value!} units={card.units!} dataset={card.dataset!} factId={card.fid}
            basis={card.basis!} fy={card.fy} measure={card.measure} edition={card.edition} exhibitFamily={exhibitFamily}
            reconciled={reconciliationKeys.includes(`${card.fy}|${card.measure}`)}/></div>}
          <p>Funding for this budget line. The illustration does not allocate costs to individual parts.</p>
          <a href="#figures-heading" className={styles.budgetLink}>Full budget & accounting notes <ArrowDown size={14}/></a>
        </div>
      </div>
      <footer className={styles.footer}><p>{config.caption}</p><div className={styles.copyActions}>
        {answerPilot && <button onClick={copyAnswer} disabled={!hasAnswer} title={!hasAnswer ? ANSWER_COPY.unavailable : undefined}><Copy size={14}/>{ANSWER_COPY.button}</button>}
        <button onClick={copyView}>{copied ? <Check size={14}/> : <Copy size={14}/>} {copied ? "Link copied" : "Share this view"}</button>
      </div></footer>
      {answerCopied && <p role="status" className={styles.error}>{ANSWER_COPY.copied}</p>}
      {copyError && <p role="status" className={styles.error}>{ANSWER_COPY.fallback}</p>}
      {copyFallback && <label className={styles.copyFallback}>Text to copy<textarea aria-label="Text to copy" readOnly value={copyFallback} rows={6} onFocus={event => event.target.select()} /></label>}
      <noscript><p className={styles.error}>The full program narratives and receipts follow below. Enable JavaScript to explore the interactive topics.</p></noscript>
      {interactive && <Script src="/exhibits/viewer.js" type="module" strategy="afterInteractive" onError={() => {setSceneStatus("error");setInteractive(false);}} />}
    </section>
  );
}
