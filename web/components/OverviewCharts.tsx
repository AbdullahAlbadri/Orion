"use client";

// Small charts for the Overview, drawn in plain HTML: pieces ordered per month, how many orders sit at each step
// of the route, and how long orders have waited on each party. One series each, in the chart gold (#b88a36,
// validated on the card surface); the hovered or current bar lights up in the brand gold. Every chart has a
// hidden table with the same numbers for screen readers.
import { useState } from "react";

import type { FullStats, OrderRow } from "@/lib/api";
import { duration, num, t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { stepIndex, TRACK } from "./OrderTracker";

const C = {
  pieces: t("القطع المطلوبة شهريًا", "Pieces ordered per month"),
  piecesNone: t("تظهر بعد أول طلب مؤكد.", "Shows after your first confirmed order."),
  orders: t("طلب", "orders"),
  steps: t("أين طلباتك الآن", "Where your orders are"),
  waiting: t("وقت الانتظار لدى كل طرف", "Time waiting on each party"),
  waitingNone: t("يظهر حين تتحرك طلباتك بين المراحل.", "Shows once your orders move between steps."),
  month: t("الشهر", "Month"), step: t("المرحلة", "Step"), who: t("الطرف", "Party"), time: t("الوقت", "Time"),
};

const PARTIES: { key: "customer" | "orion" | "factory" | "shipping"; label: T }[] = [
  { key: "customer", label: t("أنت", "You") },
  { key: "orion", label: t("أوريون", "Orion") },
  { key: "factory", label: t("المصنع", "Factory") },
  { key: "shipping", label: t("الشحن", "Shipping") },
];

/** Pieces ordered in each of the last six months (by the month the order was created). */
export function PiecesChart({ list }: { list: FullStats["order_list"] }) {
  const { lang } = useLang();
  const [hover, setHover] = useState<number | null>(null);
  const now = new Date();
  const months = Array.from({ length: 6 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - 5 + i, 1);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const rows = list.filter((o) => o.created_at.slice(0, 7) === key);
    return {
      key,
      label: d.toLocaleDateString(lang === "ar" ? "ar-SA-u-ca-gregory-nu-latn" : "en-GB", { month: "short" }),
      pieces: rows.reduce((sum, o) => sum + (o.quantity ?? 0), 0),
      orders: rows.length,
    };
  });
  const max = Math.max(...months.map((m) => m.pieces), 1);
  const empty = months.every((m) => m.pieces === 0);
  const last = months.length - 1;
  return (
    <figure className="chart">
      <figcaption className="chart-title">{C.pieces[lang]}</figcaption>
      <div className="col-chart" onMouseLeave={() => setHover(null)}>
        {months.map((m, i) => {
          const on = hover === i;
          return (
            <div key={m.key} className={`col${on ? " on" : ""}${i === last ? " now" : ""}`} tabIndex={0}
              onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)}
              aria-label={`${m.label}: ${num(m.pieces)}`}>
              <div className="col-track">
                <span className="col-bar" style={{ height: `${(m.pieces / max) * 100}%` }} />
                {on && (
                  <span className="chart-tip" role="status">
                    <b>{num(m.pieces)}</b> {lang === "ar" ? "قطعة" : "pcs"} · {num(m.orders)} {C.orders[lang]}
                  </span>
                )}
              </div>
              <span className="col-label">{m.label}</span>
            </div>
          );
        })}
      </div>
      {empty && <p className="chart-note">{C.piecesNone[lang]}</p>}
      <table className="sr-only">
        <thead><tr><th>{C.month[lang]}</th><th>{C.pieces[lang]}</th></tr></thead>
        <tbody>{months.map((m) => <tr key={m.key}><td>{m.label}</td><td>{m.pieces}</td></tr>)}</tbody>
      </table>
    </figure>
  );
}

/** How many orders are at each step of the route, the steps in order along a dashed line. */
export function StepsChart({ orders }: { orders: OrderRow[] }) {
  const { lang } = useLang();
  const [hover, setHover] = useState<number | null>(null);
  const counts = TRACK.map((s, i) => ({ step: s, count: orders.filter((o) => stepIndex(o.stage) === i).length }));
  const max = Math.max(...counts.map((c) => c.count), 1);
  return (
    <figure className="chart">
      <figcaption className="chart-title">{C.steps[lang]}</figcaption>
      <div className="col-chart route" onMouseLeave={() => setHover(null)}>
        {counts.map(({ step, count }, i) => {
          const on = hover === i;
          return (
            <div key={step.key} className={`col${on ? " on" : ""}${count ? " has" : ""}`} tabIndex={0}
              onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)}
              aria-label={`${step.label[lang]}: ${num(count)}`}>
              <div className="col-track">
                {count > 0 && <span className="col-value">{num(count)}</span>}
                <span className="col-bar" style={{ height: `${(count / max) * 100}%` }} />
              </div>
              <span className="col-stop" aria-hidden />
              <span className="col-label">{step.label[lang]}</span>
            </div>
          );
        })}
      </div>
      <table className="sr-only">
        <thead><tr><th>{C.step[lang]}</th><th>{C.orders[lang]}</th></tr></thead>
        <tbody>{counts.map(({ step, count }) => <tr key={step.key}><td>{step.label[lang]}</td><td>{count}</td></tr>)}</tbody>
      </table>
    </figure>
  );
}

/** Hours orders have spent waiting on you, Orion, the factory and shipping, as labelled bars. */
export function WaitingChart({ waiting }: { waiting: FullStats["time"]["waiting_hours"] }) {
  const { lang } = useLang();
  const rows = PARTIES.map((p) => ({ ...p, hours: waiting[p.key] ?? 0 }));
  const max = Math.max(...rows.map((r) => r.hours), 1);
  const empty = rows.every((r) => r.hours === 0);
  return (
    <figure className="chart">
      <figcaption className="chart-title">{C.waiting[lang]}</figcaption>
      <div className="row-chart">
        {rows.map((r) => (
          <div key={r.key} className={`hrow${r.key === "customer" ? " you" : ""}`}>
            <span className="hrow-label">{r.label[lang]}</span>
            <span className="hrow-track"><span className="hrow-bar" style={{ width: `${(r.hours / max) * 100}%` }} /></span>
            <span className="hrow-value">{r.hours ? duration(r.hours, lang) : "—"}</span>
          </div>
        ))}
      </div>
      {empty && <p className="chart-note">{C.waitingNone[lang]}</p>}
      <table className="sr-only">
        <thead><tr><th>{C.who[lang]}</th><th>{C.time[lang]}</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.key}><td>{r.label[lang]}</td><td>{r.hours}</td></tr>)}</tbody>
      </table>
    </figure>
  );
}
