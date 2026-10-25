"use client";

// Order tracker for the Overview: the order's steps in a row, done steps checked, the current step's icon
// animated (each in its own way: the factory smokes, the gear turns, the truck drives). Several orders in
// progress: chips switch between them. Still when the customer prefers reduced motion.
import Link from "next/link";
import { useState, type ReactNode } from "react";

import type { OrderRow } from "@/lib/api";
import { t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { ACTIONS, chipTone, needsAction, orderName, ownerText } from "@/lib/orders";
import { CardIcon, CheckIcon, FactoryIcon, GearIcon, ListIcon, NeedleIcon, TagIcon, TruckIcon, BoxIcon } from "./Icons";
import { ProductThumb, StatusChip } from "./ui";

type Step = { key: string; label: T; icon: ReactNode; anim: string; stages: string[] };

export const TRACK: Step[] = [
  { key: "prep", label: t("تجهيز الطلب", "Preparing"), icon: <ListIcon />, anim: "write", stages: ["draft", "pre_receipt_review"] },
  { key: "factory", label: t("مع المصانع", "With factories"), icon: <FactoryIcon />, anim: "smoke",
    stages: ["spec_frozen", "sourcing", "clarifying"] },
  { key: "quote", label: t("عرض السعر", "Quote"), icon: <TagIcon />, anim: "swing", stages: ["quote_received", "quote_review"] },
  { key: "pay", label: t("الدفع", "Payment"), icon: <CardIcon />, anim: "bob", stages: ["awaiting_payment"] },
  { key: "sample", label: t("العينة", "Sample"), icon: <NeedleIcon />, anim: "stitch",
    stages: ["sample_requested", "sample_in_transit", "sample_review"] },
  { key: "make", label: t("التصنيع", "Production"), icon: <GearIcon />, anim: "spin", stages: ["in_production", "quality_check"] },
  { key: "ship", label: t("الشحن", "Shipping"), icon: <TruckIcon />, anim: "drive", stages: ["shipped", "in_transit", "customs_paperwork"] },
  { key: "done", label: t("التسليم", "Delivered"), icon: <BoxIcon />, anim: "pop", stages: ["delivered", "completed"] },
];

export function stepIndex(stage: string): number {
  const i = TRACK.findIndex((s) => s.stages.includes(stage));
  return i === -1 ? 0 : i;
}

const C = {
  title: t("متابعة الطلب", "Order tracking"),
  now: t("المرحلة الحالية", "Current step"),
  open: t("فتح الطلب", "Open order"),
};

export default function OrderTracker({ orders }: { orders: OrderRow[] }) {
  const { lang } = useLang();
  const L = (x: T) => x[lang];
  const [selected, setSelected] = useState(orders[0]?.id);
  const order = orders.find((o) => o.id === selected) ?? orders[0];
  if (!order) return null;
  const current = stepIndex(order.stage);
  const fill = current / (TRACK.length - 1);   // 0-1: how far the gold line reaches

  return (
    <section className="board board-ink tracker" aria-labelledby="tracker-title">
      <div className="spread">
        <h2 id="tracker-title" style={{ margin: 0 }}>{L(C.title)}</h2>
        {orders.length > 1 && (
          <div className="tracker-chips" role="tablist">
            {orders.slice(0, 5).map((o) => (
              <button key={o.id} type="button" role="tab" aria-selected={o.id === order.id}
                className={o.id === order.id ? "on" : ""} onClick={() => setSelected(o.id)}>
                {orderName(o, lang)}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="tracker-order">
        <ProductThumb option={order.option} size={52} />
        <div className="stack-sm grow">
          <strong className="ellipsis">{orderName(order, lang)}</strong>
          <span className="row small">
            <StatusChip status={order.status} tone={chipTone(order)} />
            {order.waiting_on && <span className="muted">{L(ownerText[order.waiting_on])}</span>}
          </span>
        </div>
        {needsAction(order)
          ? <Link href={`/orders/${order.id}`} className="btn btn-sm">{L(ACTIONS[order.stage].button)}</Link>
          : <Link href={`/orders/${order.id}`} className="btn-outline">{L(C.open)}</Link>}
      </div>

      <ol className="tracker-steps" style={{ ["--fill" as string]: fill }} key={order.id}>
        {TRACK.map((s, i) => {
          const state = i < current ? "done" : i === current ? "now" : "next";
          return (
            <li key={s.key} className={`tracker-step ${state}`} style={{ ["--i" as string]: i }}
              aria-current={state === "now" ? "step" : undefined}>
              <span className={`tracker-icon anim-${s.anim}`}>
                {state === "done" ? <CheckIcon /> : s.icon}
                {state === "now" && s.anim === "smoke" && <><i className="puff p1" /><i className="puff p2" /></>}
              </span>
              <span className="tracker-label">{L(s.label)}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
