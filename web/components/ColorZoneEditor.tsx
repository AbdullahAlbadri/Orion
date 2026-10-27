"use client";

// Colour each part of the garment: tap a part on the drawing (or in the list), then pick its colour from the palette
// or type any HEX. Same drawing as the placement editor; the parts come from the question (config/garment_zones.py).
import { useState } from "react";

import type { Question } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { mockupFor, VIEW_H, VIEW_W, type View } from "@/lib/mockups";

type Zone = { id: string; en: string; ar: string; front: string | null; back: string | null; stroke: boolean };

const PALETTE = [
  "#111111", "#ffffff", "#8a8a8a", "#1b2a4a", "#1e5ac8", "#8cbeeb", "#1f8c8c", "#28a046", "#6e6e32", "#c9b38a",
  "#e1d2b4", "#6e4628", "#c81e28", "#6e1428", "#f096b4", "#f0821e", "#f5cd28", "#6e3296",
];
const HEX = /^#[0-9a-fA-F]{6}$/;

export default function ColorZoneEditor({ question, value, onChange }: {
  question: Question; value: Record<string, string>; onChange: (next: Record<string, string>) => void;
}) {
  const { t, lang } = useLang();
  const zones = ((question as Question & { zones?: Zone[] }).zones ?? []) as Zone[];
  const m = mockupFor(question.mockup);
  const [view, setView] = useState<View>("front");
  const [selected, setSelected] = useState<string | null>(zones[0]?.id ?? null);
  const [hex, setHex] = useState("");
  const name = (z: Zone) => (lang === "ar" ? z.ar : z.en);

  if (zones.length === 0) return null;

  const paint = (color: string) => {
    if (!selected) return;
    onChange({ ...value, [selected]: color.toLowerCase() });
  };
  const paintAll = (color: string) => onChange(Object.fromEntries(zones.map((z) => [z.id, color.toLowerCase()])));
  const clear = (id: string) => {
    const next = { ...value };
    delete next[id];
    onChange(next);
  };
  const current = selected ? value[selected] : undefined;

  return (
    <div className="zones">
      <div className="segmented" role="radiogroup" aria-label={t("view")}>
        {(["front", "back"] as View[]).map((v) => (
          <button key={v} type="button" role="radio" aria-checked={view === v} className={view === v ? "on" : ""}
            onClick={() => setView(v)}>
            {t(v === "front" ? "viewFront" : "viewBack")}
          </button>
        ))}
      </div>

      <div className="mockup-wrap" dir="ltr">
        <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="mockup" role="group" aria-label={lang === "ar" ? "ألوان القطعة" : "Garment colours"}>
          <path d={m.paths[view].body} className="garment" />
          {zones.map((z) => {
            const d = z[view];
            if (!d) return null;
            const color = value[z.id];
            const on = selected === z.id;
            return (
              <path key={z.id} d={d} className={`zone${on ? " on" : ""}${z.stroke ? " stroke" : ""}`}
                style={color ? (z.stroke ? { stroke: color } : { fill: color }) : undefined}
                tabIndex={0} role="button" aria-label={`${name(z)}${color ? ` ${color}` : ""}`} aria-pressed={on}
                onClick={() => setSelected(z.id)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(z.id); } }} />
            );
          })}
          {m.paths[view].details.map((d) => <path key={d} d={d} className="garment-detail" pointerEvents="none" />)}
        </svg>
      </div>

      <ul className="zone-list">
        {zones.map((z) => (
          <li key={z.id} className={selected === z.id ? "on" : ""}>
            <button type="button" className="zone-pick" onClick={() => setSelected(z.id)}>
              <span className="zone-chip" style={{ background: value[z.id] ?? "transparent" }} aria-hidden />
              <strong>{name(z)}</strong>
              <span className="muted small" dir="ltr">{value[z.id] ?? (lang === "ar" ? "بدون لون" : "no colour")}</span>
            </button>
            {value[z.id] && (
              <button type="button" className="icon-btn" aria-label={t("remove")} onClick={() => clear(z.id)}>×</button>
            )}
          </li>
        ))}
      </ul>

      <div className="zone-palette" role="group" aria-label={lang === "ar" ? "اختر لونًا" : "Pick a colour"}>
        {PALETTE.map((c) => (
          <button key={c} type="button" className={`zone-swatch${current === c ? " on" : ""}`} style={{ background: c }}
            aria-label={c} disabled={!selected} onClick={() => paint(c)} />
        ))}
        <label className="zone-custom">
          <input type="color" value={current ?? "#808080"} disabled={!selected} aria-label={lang === "ar" ? "لون مخصص" : "Custom colour"}
            onChange={(e) => paint(e.target.value)} />
        </label>
        <input className="zone-hex" dir="ltr" placeholder="#RRGGBB" maxLength={7} value={hex} disabled={!selected}
          onChange={(e) => { setHex(e.target.value); if (HEX.test(e.target.value)) paint(e.target.value); }} />
      </div>

      <div className="row">
        <button type="button" className="chip" disabled={!current} onClick={() => current && paintAll(current)}>
          {lang === "ar" ? "طبّق هذا اللون على كل الأجزاء" : "Use this colour for every part"}
        </button>
        {Object.keys(value).length > 0 && (
          <button type="button" className="chip" onClick={() => onChange({})}>{lang === "ar" ? "مسح الكل" : "Clear all"}</button>
        )}
      </div>
    </div>
  );
}
