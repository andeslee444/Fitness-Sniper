import { F15_VARIANT_IDS } from "./f15-family";
import type { F15Knowledge } from "./f15-knowledge-types";
import {
  VARIANT_CONTEXT_SOURCES,
  VARIANT_CONTEXTS,
} from "./f15-variant-context";
import {
  OPERATORS_ORDERS_SOURCES,
  F15_OPERATORS,
  F15_PROCUREMENT,
} from "./f15-operators-orders";
import { SYSTEM_CONTEXT_SOURCES, F15_SYSTEMS } from "./f15-systems-context";

export function validateF15Knowledge(
  data: F15Knowledge,
  programSlugs?: Set<string>,
) {
  const fail = (message: string): never => {
    throw new Error(`[f15-knowledge] ${message}`);
  };
  const sourceIds = new Set(data.sources.map((source) => source.id));
  if (sourceIds.size !== data.sources.length) fail("Duplicate source identity");
  for (const source of data.sources) {
    if (!source.publisher || !source.title || !/^https:\/\//.test(source.url))
      fail(`Incomplete source ${source.id}`);
    if (
      source.accessed > data.reviewed ||
      (source.published && source.published > data.reviewed)
    )
      fail(`Future-dated source ${source.id}`);
  }
  const entries = [
    ...data.contexts,
    ...data.operators,
    ...data.procurement,
    ...data.systems,
  ];
  for (const entry of entries) {
    if ("asOf" in entry && entry.asOf > data.reviewed)
      fail("Future context snapshot");
    if (
      !entry.sourceIds.length ||
      entry.sourceIds.some((id) => !sourceIds.has(id))
    )
      fail("Unresolved claim source");
    if (
      "recordSlugs" in entry &&
      programSlugs &&
      entry.recordSlugs?.some((slug) => !programSlugs.has(slug))
    )
      fail("Unresolved related budget record");
  }
  for (const variant of F15_VARIANT_IDS) {
    for (const topic of [
      "airframe",
      "cockpit",
      "sensors",
      "support",
    ] as const) {
      const contexts = data.contexts.filter(
        (item) => item.variant === variant && item.topic === topic,
      );
      if (contexts.length !== 1 || contexts[0].text.length < 80)
        fail(`Missing substantive context ${variant}/${topic}`);
    }
  }
  if (data.contexts.length !== 24) fail("Unexpected variant/topic coverage");
  for (const event of data.procurement) {
    if (event.amount && !event.amountBasis)
      fail(`Amount has no scope: ${event.id}`);
    if (
      event.quantity != null &&
      (!Number.isFinite(event.quantity) ||
        event.quantity < 0 ||
        !event.quantityLabel)
    )
      fail(`Quantity has no scope: ${event.id}`);
    if (event.date > data.reviewed) fail(`Future event: ${event.id}`);
  }
  for (const collection of [data.operators, data.procurement, data.systems]) {
    if (new Set(collection.map((item) => item.id)).size !== collection.length)
      fail("Duplicate context identity");
  }
}

export function getF15Knowledge(programSlugs?: Set<string>): F15Knowledge {
  const data: F15Knowledge = {
    reviewed: "2026-09-09",
    sources: [
      ...VARIANT_CONTEXT_SOURCES,
      ...OPERATORS_ORDERS_SOURCES,
      ...SYSTEM_CONTEXT_SOURCES,
    ],
    contexts: VARIANT_CONTEXTS,
    operators: F15_OPERATORS,
    procurement: F15_PROCUREMENT,
    systems: F15_SYSTEMS,
  };
  validateF15Knowledge(data, programSlugs);
  return data;
}
