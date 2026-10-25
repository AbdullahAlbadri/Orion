"use client";

// Typical measurements in cm for the product's sizes (from the size question's size_chart).
import type { SizeChartData } from "@/lib/api";
import { useLang } from "@/lib/i18n";

const TITLE = { ar: "جدول المقاسات (سم)", en: "Size chart (cm)" };
const SIZE = { ar: "المقاس", en: "Size" };

export default function SizeChart({ chart }: { chart: SizeChartData }) {
  const { lang } = useLang();
  return (
    <div className="size-chart">
      <strong>{TITLE[lang]}</strong>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>{SIZE[lang]}</th>{chart.measures.map((m) => <th key={m.id}>{m[lang]}</th>)}</tr>
          </thead>
          <tbody>
            {Object.entries(chart.sizes).map(([size, values]) => (
              <tr key={size}><th dir="ltr">{size}</th>{values.map((v, i) => <td key={i} dir="ltr">{v}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="hint" style={{ margin: 0 }}>{chart.note[lang]}</p>
    </div>
  );
}
