// Order groups and "needs your attention" items, shared by Overview and Orders.
// Friendly status text always comes from the API (row.status), so every page shows the same label.
import type { OrderRow } from "./api";
import { t, type T } from "./copy";
import { productName, type Lang } from "./i18n";

/** A custom product is named by the customer's own description; others by the product type. */
export const orderName = (row: { title?: string | null; option: string | null }, lang: Lang) =>
  row.title || productName(row.option, lang);

export type Group = "draft" | "active" | "delivered" | "closed";

const CLOSED = ["cancelled", "expired", "refunded"];
const DELIVERED = ["delivered", "completed"];
export const IN_TRANSIT = ["shipped", "in_transit", "customs_paperwork"];

export function groupOf(stage: string): Group {
  if (stage === "draft" || stage === "pre_receipt_review") return "draft";
  if (DELIVERED.includes(stage)) return "delivered";
  if (CLOSED.includes(stage)) return "closed";
  return "active";
}

/** Colour of the status chip: the customer's turn, in motion, done or closed. */
export function chipTone(row: Pick<OrderRow, "stage" | "waiting_on">): "you" | "moving" | "done" | "closed" {
  if (DELIVERED.includes(row.stage)) return "done";
  if (CLOSED.includes(row.stage)) return "closed";
  return row.waiting_on === "customer" ? "you" : "moving";
}

type Action = { label: T; button: T };
// What the customer must do in each stage that waits on them
export const ACTIONS: Record<string, Action> = {
  draft: { label: t("أكمل مسودة طلبك", "Finish your draft"), button: t("أكمل", "Continue") },
  pre_receipt_review: { label: t("راجع ملخص طلبك وأكّده", "Review and confirm your summary"), button: t("راجع", "Review") },
  quote_review: { label: t("عرض السعر جاهز لتأكيده", "Your quote is ready to confirm"), button: t("راجع العرض", "Review quote") },
  awaiting_payment: { label: t("بانتظار دفعتك", "Waiting for your payment"), button: t("ادفع", "Pay") },
  sample_review: { label: t("عينتك جاهزة للمراجعة", "Your sample is ready to review"), button: t("راجع العينة", "Review sample") },
};

export function needsAction(row: OrderRow): boolean {
  return row.stage in ACTIONS;
}

export const ownerText: Record<string, T> = {
  customer: t("بانتظارك", "Waiting for you"),
  factory: t("لدى المصنع", "With the factory"),
  orion: t("لدى فريق أوريون", "With the Orion team"),
  shipping: t("مع شركة الشحن", "With the carrier"),
};
