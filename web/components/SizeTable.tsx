"use client";

import { useLang } from "@/lib/i18n";

export type SizeRow = { size: string; qty: string };

export function initialSizes(value: unknown): SizeRow[] {
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, number>).map(([size, qty]) => ({ size, qty: String(qty) }));
  }
  return ["S", "M", "L", "XL"].map((size) => ({ size, qty: "" }));
}

/** {S: 20, M: 50} from the rows; empty or zero rows are dropped (the API validates the rest). */
export function sizesToAnswer(rows: SizeRow[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const r of rows) {
    const qty = Number(r.qty);
    if (r.size.trim() && qty > 0) out[r.size.trim().toUpperCase()] = Math.floor(qty);
  }
  return out;
}

export default function SizeTable({ rows, onChange }: { rows: SizeRow[]; onChange: (rows: SizeRow[]) => void }) {
  const { t } = useLang();
  const total = Object.values(sizesToAnswer(rows)).reduce((a, b) => a + b, 0);
  const set = (i: number, patch: Partial<SizeRow>) => onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  return (
    <div>
      <div className="sizes">
        <span className="head">{t("size")}</span>
        <span className="head">{t("qty")}</span>
        <span />
        {rows.map((r, i) => (
          <div key={i} style={{ display: "contents" }}>
            <input dir="ltr" value={r.size} onChange={(e) => set(i, { size: e.target.value })} aria-label={t("size")} />
            <input dir="ltr" inputMode="numeric" value={r.qty}
              onChange={(e) => set(i, { qty: e.target.value.replace(/\D/g, "") })} aria-label={t("qty")} />
            <button type="button" className="icon-btn" aria-label="remove" onClick={() => onChange(rows.filter((_, j) => j !== i))}>×</button>
          </div>
        ))}
      </div>
      <div className="spread" style={{ marginTop: 10 }}>
        <button type="button" className="btn-ghost btn-sm" onClick={() => onChange([...rows, { size: "", qty: "" }])}>+ {t("addSize")}</button>
        <strong>{t("total")}: {total}</strong>
      </div>
    </div>
  );
}
