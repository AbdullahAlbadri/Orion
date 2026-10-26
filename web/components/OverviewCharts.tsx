"use client";

// The small chart on the Overview's numbers board: pieces ordered in each of the last six months, drawn in plain
// HTML. One series in the chart gold (#b88a36, validated on the board surface); the hovered month lights up in
// the brand gold and shows its numbers. A hidden table carries the same numbers for screen readers.
import { useState } from "react";

import type { FullStats } from "@/lib/api";
import { num, t } from "@/lib/copy";
import { useLang } from "@/lib/i18n";

const C = {
  pieces: t("القطع المطلوبة شهريًا", "Pieces ordered per month"),
  piecesNone: t("تظهر بعد أول طلب مؤكد.", "Shows after your first confirmed order."),
  orders: t("طلب", "orders"),
  pcs: t("قطعة", "pcs"),
  month: t("الشهر", "Month"),
};

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
  return (
    <figure className="chart">
      <figcaption className="chart-title">{C.pieces[lang]}</figcaption>
      <div className="col-chart" onMouseLeave={() => setHover(null)}>
        {months.map((m, i) => {
          const on = hover === i;
          return (
            <div key={m.key} className={`col${on ? " on" : ""}`} tabIndex={0}
              onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)}
              aria-label={`${m.label}: ${num(m.pieces)}`}>
              <div className="col-track">
                <span className="col-bar" style={{ height: `${(m.pieces / max) * 100}%` }} />
                {on && (
                  <span className="chart-tip" role="status">
                    <b>{num(m.pieces)}</b> {C.pcs[lang]} · {num(m.orders)} {C.orders[lang]}
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
