import type { Citation } from "./data";
import { footnoteInputFromCitation, formatFootnote, type FootnoteFigure, type FootnoteProgram } from "./footnote";

export const ANSWER_COPY = {
  button: "Copy answer",
  copied: "Answer copied with fiscal context and receipts.",
  fallback: "Copy access is unavailable. Select and copy the text below.",
  unavailable: "The J-book passage is unavailable for this answer.",
};

export interface AnswerBriefInput {
  program: FootnoteProgram;
  factId: string;
  citation: Citation;
  figure: FootnoteFigure & { fy: number; measure: string; basis: string; edition: number };
  /** An exact source passage, kept separate from the selected funding year's figure. */
  passage?: { factId: string; citation: Citation; body: string; anchor?: string };
  permalink: string;
}

/** Verbatim excerpt, bounded at sentence/newline boundaries when possible. */
export function answerSourceExcerpt(body: string, anchor?: string): string | null {
  const text = body.trim();
  if (!text || (anchor && !text.toLowerCase().includes(anchor.toLowerCase()))) return null;
  const anchorAt = anchor ? text.toLowerCase().indexOf(anchor.toLowerCase()) : 0;
  const start = anchorAt > 0 ? Math.max(text.lastIndexOf("\n", anchorAt), text.lastIndexOf(". ", anchorAt)) + 1 : 0;
  const end = text.indexOf(". ", Math.max(start + 400, anchorAt + (anchor?.length ?? 0)));
  return text.slice(start, end >= 0 ? end + 1 : Math.min(text.length, start + 1200)).trim();
}

/** Deterministic brief: financial context and J-book context are independently cited. */
export function formatAnswerBrief(input: AnswerBriefInput): string {
  const { program, factId, citation, figure, passage, permalink } = input;
  const footnote = footnoteInputFromCitation(citation, factId, { program, figure });
  const basis = figure.basis === "toa" ? "Total obligation authority (TOA)" : figure.basis === "jbook-detail" ? "J-book detail" : figure.basis;
  const result = [
    `${program.name} (${program.code})`,
    `FY${figure.fy} ${figure.measure.replace(/-/g, " ")}: ${footnote.valueText}.`,
    `${basis} · PB${figure.edition}.`,
    "The figure applies to this budget line. It is not a component cost or an amount allocated to an illustrated variant.",
    `Funding receipt [${factId}]: ${formatFootnote(footnote)}`,
  ];
  const excerpt = passage && answerSourceExcerpt(passage.body, passage.anchor);
  if (passage && excerpt) {
    result.push(
      "J-book context (the passage has its own source edition; it does not describe each selected funding year):",
      `“${excerpt}”`,
      `Passage receipt [${passage.factId}]: ${formatFootnote(footnoteInputFromCitation(passage.citation, passage.factId, { program }))}`,
    );
  }
  result.push(`Selected view: ${permalink}`);
  return result.join("\n\n");
}
