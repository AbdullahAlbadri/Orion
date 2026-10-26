"use client";

// Small charts for the numbers board on the Overview, one under each number, drawn in plain HTML: bars for the
// last six months, a factory per factory contacted, the share of orders where a mistake was stopped, and what
// the time saved is made of. One series each in the chart gold (#b88a36, validated on the board surface); the
// hovered bar lights up in the brand gold. Each chart carries a label or hidden table with its numbers.
import { useState } from "react";

import type { FullStats } from "@/lib/api";
import { duration, num, t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { FactoryIcon } from "./Icons";

const C = {
  month: t("الشهر", "Month"),
  ofOrders: t("في {a} من {b} طلبات", "In {a} of {b} orders"),
  more: t("+{n}", "+{n}"),
  specs: t("كتابة المواصفات", "Writing specs"),
  factories: t("التواصل مع المصانع", "Contacting factories"),
  messages: t("الرسائل", "Messages"),
};

export type Month = { key: string; label: string; orders: number; pieces: number };

/** The last six months, oldest first, with the orders and pieces created in each. */
export function lastMonths(list: FullStats["order_list"], lang: "ar" | "en"): Month[] {
  const now = new Date();
  return Array.from({ length: 6 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - 5 + i, 1);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const rows = list.filter((o) => o.created_at.slice(0, 7) === key);
    return {
      key,
      label: d.toLocaleDateString(lang === "ar" ? "ar-SA-u-ca-gregory-nu-latn" : "en-GB", { month: "short" }),
      orders: rows.length,
      pieces: rows.reduce((sum, o) => sum + (o.quantity ?? 0), 0),
    };
  });
}

/** Six small bars, one per month; hovering one shows its value. Only the first and last months are labelled. */
export function MonthBars({ months, pick, unit, title }: {
  months: Month[]; pick: (m: Month) => number; unit: string; title: string;
}) {
  const { lang } = useLang();
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...months.map(pick), 1);
  return (
    <figure className="mini">
      <div className="mini-bars" onMouseLeave={() => setHover(null)}>
        {months.map((m, i) => (
          <span key={m.key} className={`mini-col${hover === i ? " on" : ""}`} tabIndex={0}
            onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)}
            aria-label={`${m.label}: ${num(pick(m))} ${unit}`}>
            <span className="mini-bar" style={{ height: `${(pick(m) / max) * 100}%` }} />
            {hover === i && <span className="chart-tip" role="status"><b>{num(pick(m))}</b> {unit} · {m.label}</span>}
          </span>
        ))}
      </div>
      <figcaption className="mini-axis"><span>{months[0].label}</span><span>{months[months.length - 1].label}</span></figcaption>
      <table className="sr-only">
        <thead><tr><th>{C.month[lang]}</th><th>{title}</th></tr></thead>
        <tbody>{months.map((m) => <tr key={m.key}><td>{m.label}</td><td>{pick(m)}</td></tr>)}</tbody>
      </table>
    </figure>
  );
}

/** One small factory per factory contacted, up to twelve, then "+n". */
export function FactoryDots({ count }: { count: number }) {
  const { lang } = useLang();
  const shown = Math.min(count, 12);
  return (
    <div className="mini-dots" aria-hidden>
      {Array.from({ length: shown }, (_, i) => <FactoryIcon key={i} width={16} height={16} style={{ ["--i" as string]: i }} />)}
      {count > shown && <span className="mini-more">{C.more[lang].replace("{n}", num(count - shown))}</span>}
      {count === 0 && <span className="mini-empty" />}
    </div>
  );
}

/** The share of orders where a factory reply was stopped for differing from the order. */
export function ShareBar({ part, total }: { part: number; total: number }) {
  const { lang } = useLang();
  return (
    <div className="mini-share">
      <span className="mini-track"><span className="mini-fill" style={{ width: total ? `${(part / total) * 100}%` : 0 }} /></span>
      {total > 0 && <span className="mini-note">{C.ofOrders[lang].replace("{a}", num(part)).replace("{b}", num(total))}</span>}
    </div>
  );
}

/** What the time saved is made of: specs written, factories contacted and messages, at the server's hour rates. */
export function TimeParts({ stats }: { stats: FullStats }) {
  const { lang } = useLang();
  const b = stats.time_saved_basis;
  const parts: { label: T; hours: number }[] = [
    { label: C.specs, hours: stats.orders_submitted * b.per_spec },
    { label: C.factories, hours: stats.factories_contacted * b.per_factory },
    { label: C.messages, hours: stats.messages_handled * b.per_message },
  ];
  const max = Math.max(...parts.map((p) => p.hours), 1);
  return (
    <div className="mini-rows">
      {parts.map((p) => (
        <div key={p.label.en} className="mini-row">
          <span className="mini-row-label">{p.label[lang]}</span>
          <span className="mini-track"><span className="mini-fill" style={{ width: `${(p.hours / max) * 100}%` }} /></span>
          <span className="mini-row-value">{p.hours ? duration(p.hours, lang) : "—"}</span>
        </div>
      ))}
    </div>
  );
}
