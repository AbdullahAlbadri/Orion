// Where an order is on its way to the customer, for the tracker and progress ring.
import type { TextKey } from "./i18n";

export type JourneyStep = { key: TextKey; stages: string[] };

export const JOURNEY: JourneyStep[] = [
  { key: "stepDescribe", stages: ["draft"] },
  { key: "stepReview", stages: ["pre_receipt_review"] },
  { key: "stepFactories", stages: ["spec_frozen", "sourcing", "clarifying"] },
  { key: "stepQuote", stages: ["quote_received", "quote_review", "awaiting_payment"] },
  { key: "stepProduction", stages: ["sample_requested", "sample_in_transit", "sample_review", "in_production", "quality_check"] },
  { key: "stepShipping", stages: ["shipped", "in_transit", "customs_paperwork"] },
  { key: "stepDelivered", stages: ["delivered", "completed"] },
];

export function journeyIndex(stage: string): number {
  const i = JOURNEY.findIndex((s) => s.stages.includes(stage));
  return i === -1 ? 0 : i;
}

/** 0-100: share of the journey completed (the current step counts as half done). */
export function journeyPercent(stage: string): number {
  return Math.round(((journeyIndex(stage) + 0.5) / JOURNEY.length) * 100);
}

export type Bucket = "you" | "factories" | "done";

export function bucket(stage: string): Bucket {
  if (["draft", "pre_receipt_review"].includes(stage)) return "you";
  if (["delivered", "completed", "cancelled", "expired", "refunded"].includes(stage)) return "done";
  return "factories";
}
