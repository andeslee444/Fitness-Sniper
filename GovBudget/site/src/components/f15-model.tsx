"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Script from "next/script";
import {
  Box,
  ChevronLeft,
  ChevronRight,
  Minus,
  Plus,
  RotateCcw,
} from "lucide-react";
import styles from "./f15-model.module.css";
import { f15Illustration } from "@/lib/f15-illustration";
import { F15Schematic } from "./f15-schematic";

export type F15ModelVariant = "A" | "B" | "C" | "D" | "E" | "EX";
export type F15ModelTopic = "airframe" | "cockpit" | "sensors" | "support";
export interface F15SceneElement extends HTMLElement {
  setView?: (view: "quarter" | "side" | "top") => void;
  nudge?: (action: "left" | "right" | "in" | "out") => void;
}
export interface F15ModelProps {
  variant: F15ModelVariant;
  compareVariant?: F15ModelVariant | null;
  topic: F15ModelTopic | null;
  onTopicChange: (topic: F15ModelTopic) => void;
  onInteract?: (kind: string) => void;
  showTopicControls?: boolean;
  /** Leading year of the curated era string — the plate stamp's date. */
  yearLabel?: string;
}
const topics: { id: F15ModelTopic; label: string }[] = [
  { id: "airframe", label: "Airframe" },
  { id: "cockpit", label: "Cockpit" },
  { id: "sensors", label: "Sensors" },
  { id: "support", label: "Tooling & support" },
];
/* The plate's callout anchors, measured from the DOM as [x%, y%] of the
   1800×960 viewBox — the same contract the homepage plates carry
   (program-exhibits.ts positions). The markers are the section rail's
   other half: same 01–04, same rust when active. */
const CALLOUTS: Record<F15ModelTopic, [number, number]> = {
  airframe: [39.1, 60.4],
  cockpit: [35.8, 49.8],
  sensors: [22.1, 49.8],
  support: [28.2, 54.0],
};

export function F15Model({
  variant,
  compareVariant = null,
  topic,
  onTopicChange,
  onInteract,
  showTopicControls = true,
  yearLabel,
}: F15ModelProps) {
  const [active, setActive] = useState(false);
  const [status, setStatus] = useState<
    "poster" | "loading" | "ready" | "error"
  >("poster");
  const [blueprint, setBlueprint] = useState(true);
  const [conformal, setConformal] = useState(false);
  const scene = useRef<F15SceneElement | null>(null);
  const callbacks = useRef({ onTopicChange, onInteract });
  useEffect(() => {
    callbacks.current = { onTopicChange, onInteract };
  }, [onTopicChange, onInteract]);

  const handleReady = useCallback(() => setStatus("ready"), []);
  const handleError = useCallback(() => {
    setStatus("error");
    setActive(false);
  }, []);
  const handleTopic = useCallback((event: Event) => {
    const id = (event as CustomEvent<{ topic: F15ModelTopic }>).detail?.topic;
    if (topics.some((t) => t.id === id)) callbacks.current.onTopicChange(id);
  }, []);
  const handleInteract = useCallback((event: Event) => {
    callbacks.current.onInteract?.(
      (event as CustomEvent<{ kind: string }>).detail?.kind ?? "model",
    );
  }, []);
  // Callback ref installs listeners during commit, before a cached custom element
  // can finish connecting. This also handles navigating back to the family page.
  const attachScene = useCallback(
    (element: F15SceneElement | null) => {
      if (scene.current) {
        scene.current.removeEventListener("model-ready", handleReady);
        scene.current.removeEventListener("model-error", handleError);
        scene.current.removeEventListener("topic-select", handleTopic);
        scene.current.removeEventListener("model-interact", handleInteract);
      }
      scene.current = element;
      if (!element) return;
      element.addEventListener("model-ready", handleReady);
      element.addEventListener("model-error", handleError);
      element.addEventListener("topic-select", handleTopic);
      element.addEventListener("model-interact", handleInteract);
      if (element.getAttribute("data-ready") === "true") handleReady();
      if (element.getAttribute("data-error") === "true") handleError();
    },
    [handleReady, handleError, handleTopic, handleInteract],
  );

  function activate() {
    setActive(true);
    setStatus("loading");
    onInteract?.("activate");
  }
  function setView(view: "quarter" | "side" | "top") {
    scene.current?.setView?.(view);
  }
  const compare =
    compareVariant && compareVariant !== variant ? compareVariant : null;
  const drawing = f15Illustration(variant, conformal);
  const nickname =
    variant === "EX"
      ? "EAGLE II"
      : variant === "E"
        ? "STRIKE EAGLE"
        : "EAGLE";

  return (
    <section
      className={styles.instrument}
      aria-label={`F-15${variant} interactive illustration`}
      data-f15-model-stage
      data-variant={variant}
      data-active={active || undefined}
    >
      <div className={styles.stage}>
        <div
          className={`${styles.poster} ${status === "ready" ? styles.posterHidden : ""}`}
          aria-hidden={status === "ready"}
        >
          {/* The default plate is the drawn planform on the hangar floor —
              the SAME object the homepage plates are: external <use>,
              container color = ink, mono corner stamp, numbered callouts,
              caption beneath. The editorial .webp leaves the default view;
              the three.js scene loads only on "Inspect in 3D".
              Two renders, exactly one visible per width (the homepage
              hero's wiring): `meet` at ≥768, `xMin…slice` at ≤767 holding
              the nose and cockpit. The full copy sits in an aspect-correct
              15/8 wrapper so the callout markers (anchored in viewBox
              percent) land on the drawing whatever the stage's aspect; the
              crop copy is inset:0 and lets the svg's own slice do the
              cropping, so no descendant rect ever escapes its container. */}
          <div className={styles.plateFull}>
            <span className={styles.plateCorner} aria-hidden="true" data-plate-mark>
              01 / Air
            </span>
            <svg
              viewBox="0 0 1800 960"
              role="img"
              aria-label={drawing.description}
              preserveAspectRatio="xMidYMid meet"
              data-illustration=""
            >
              <desc>
                Overhead planform view of an F-15 fighter jet parked on a
                hangar floor, with ground support equipment positioned around
                the aircraft.
              </desc>
              <use href={drawing.href} />
            </svg>
            {topics.map((item, index) => (
              <button
                key={item.id}
                type="button"
                className={styles.plateMarker}
                data-marker={index}
                style={{
                  left: `${CALLOUTS[item.id][0]}%`,
                  top: `${CALLOUTS[item.id][1]}%`,
                }}
                aria-pressed={topic === item.id}
                aria-label={`${item.label} — section 0${index + 1}`}
                tabIndex={status === "ready" ? -1 : 0}
                onClick={() => onTopicChange(item.id)}
              >
                <span className={styles.markerLeader} aria-hidden="true" />
                <span className={styles.markerNum} aria-hidden="true" data-plate-mark>
                  0{index + 1}
                </span>
              </button>
            ))}
          </div>
          <div className={styles.plateCrop} aria-hidden="true">
            <svg
              viewBox="0 0 1800 960"
              role="img"
              aria-label={`${drawing.description}, nose and cockpit section`}
              preserveAspectRatio="xMinYMid slice"
              data-illustration=""
            >
              <desc>
                A cropped view of the same F-15 planform plate, holding the
                aircraft&apos;s nose and cockpit.
              </desc>
              <use href={drawing.href} />
            </svg>
          </div>
        </div>
        {active ? (
          <f15-family-scene
            ref={attachScene}
            variant={variant}
            compare={compare ?? ""}
            selected={topic ?? ""}
            blueprint={String(blueprint)}
            conformal={String(conformal)}
            className={styles.scene}
          />
        ) : (
          /* The 3D affordance is the ONE bordered control on the plate. */
          <button type="button" className={styles.activate} onClick={activate}>
            <Box size={17} strokeWidth={1.5} />
            <span>
              {status === "error" ? "Retry interactive model" : "Inspect in 3D"}
            </span>
          </button>
        )}
        {status === "loading" && (
          <div className={styles.loading} role="status">
            <span className={styles.loadingDot} />
            Preparing model
          </div>
        )}
        {compare && status === "ready" && (
          <div className={styles.compareLegend}>
            <span>
              <i /> F-15{variant}
            </span>
            <span>
              <i /> F-15{compare} overlay
            </span>
          </div>
        )}
        {/* The bottom-left instruction/spec jam becomes the mono plate
            stamp: variant · nickname · year (identifiers — mono's job).
            While the model is live the same corner carries the control
            hint, in sans (mono is for identifiers, not instructions). */}
        <span className={styles.plateStamp} data-plate-mark data-live={status === "ready" || undefined}>
          {status === "ready"
            ? "Drag to rotate · arrows & +/− on keyboard"
            : `F-15${variant} · ${nickname}${yearLabel ? ` · ${yearLabel}` : ""}`}
        </span>
      </div>
      <div className={styles.configuration} aria-live="polite">
        <F15Schematic variant={variant} conformal={conformal} cockpit />
        <p><strong>F-15{variant} · {drawing.seats === 1 ? "One seat" : "Two seats"}</strong>
          <span>{drawing.tanks ? "Conformal fuel tanks shown." : variant === "EX" ? "Two-seat airframe; operable by one pilot." : "Cockpit detail of the selected aircraft."}</span>
        </p>
        {variant === "EX" && <button type="button" aria-pressed={conformal} onClick={() => {
          setConformal(value => !value); onInteract?.("configuration");
        }}>Conformal tanks {conformal ? "on" : "off"}</button>}
      </div>
      {status === "ready" && (
        <div className={styles.toolbar}>
          <div
            className={styles.viewButtons}
            role="group"
            aria-label="Model camera"
          >
            <button
              type="button"
              disabled={status !== "ready"}
              onClick={() => setView("quarter")}
            >
              ¾ view
            </button>
            <button
              type="button"
              disabled={status !== "ready"}
              onClick={() => setView("side")}
            >
              Side
            </button>
            <button
              type="button"
              disabled={status !== "ready"}
              onClick={() => setView("top")}
            >
              Top
            </button>
          </div>
          <div className={styles.utilities}>
            <button
              type="button"
              disabled={status !== "ready"}
              aria-pressed={blueprint}
              onClick={() => {
                setBlueprint((v) => !v);
                onInteract?.("view");
              }}
            >
              Blueprint
            </button>
            <button
              type="button"
              disabled={status !== "ready"}
              aria-label="Rotate model left"
              onClick={() => scene.current?.nudge?.("left")}
            >
              <ChevronLeft size={15} />
            </button>
            <button
              type="button"
              disabled={status !== "ready"}
              aria-label="Rotate model right"
              onClick={() => scene.current?.nudge?.("right")}
            >
              <ChevronRight size={15} />
            </button>
            <button
              type="button"
              disabled={status !== "ready"}
              aria-label="Zoom model out"
              onClick={() => scene.current?.nudge?.("out")}
            >
              <Minus size={15} />
            </button>
            <button
              type="button"
              disabled={status !== "ready"}
              aria-label="Zoom model in"
              onClick={() => scene.current?.nudge?.("in")}
            >
              <Plus size={15} />
            </button>
            <button
              type="button"
              disabled={status !== "ready"}
              aria-label="Reset model view"
              onClick={() => setView("quarter")}
            >
              <RotateCcw size={14} />
            </button>
          </div>
        </div>
      )}
      {showTopicControls && (
        <div
          className={styles.topicKeys}
          role="group"
          aria-label="Inspect model topics"
        >
          {topics.map((item, index) => (
            <button
              type="button"
              key={item.id}
              aria-pressed={topic === item.id}
              onClick={() => onTopicChange(item.id)}
            >
              <span>0{index + 1}</span>
              {item.label}
            </button>
          ))}
        </div>
      )}
      <p className={styles.caption}>
        Simplified illustration. A/C and B/D share schematics; exact equipment
        varies.{" "}
        {variant === "E"
          ? "E shown with conformal tanks. "
          : variant === "EX" && conformal
            ? "EX shown in a CFT-equipped configuration. "
            : ""}
        Support is a conceptual link; the model does not assign costs to parts.
      </p>
      {status === "error" && (
        <p className={styles.error} role="status">
          3D is unavailable in this browser. The illustration, topic buttons,
          and program evidence remain available.
        </p>
      )}
      {active && (
        <Script
          src="/exhibits/f15-family/viewer.js"
          type="module"
          strategy="afterInteractive"
          onError={handleError}
        />
      )}
    </section>
  );
}
