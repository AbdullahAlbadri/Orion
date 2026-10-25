"use client";

// Place logos and labels on a garment drawing: drag to move, drag the corner to resize, or type exact cm.
// Positions are stored as fractions of the drawing and sizes in cm (see lib/mockups.ts).
import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

import { useLang } from "@/lib/i18n";
import { mockupFor, VIEW_H, VIEW_W, type Placement, type PlacementKind, type View } from "@/lib/mockups";
import { suggestSize } from "@/lib/sizing";
import { PlusIcon, SparkleIcon } from "./Icons";

const MAX_ITEMS = 10;
const MIN_CM = 1;

type Drag = { index: number; mode: "move" | "resize"; startX: number; startY: number; start: Placement };

export default function PlacementEditor({ mockup, value, onChange, logoUrl, logoAspect, method }: {
  mockup?: string | null; value: Placement[]; onChange: (items: Placement[]) => void;
  logoUrl?: string | null;       // the uploaded logo, drawn inside logo boxes
  logoAspect?: number | null;    // its width / height, to keep it undistorted
  method?: string;               // decoration method chosen in the form (embroidery, screen print...)
}) {
  const { t, lang } = useLang();
  const m = mockupFor(mockup);
  const svg = useRef<SVGSVGElement>(null);
  const [view, setView] = useState<View>("front");
  const [selected, setSelected] = useState<number | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);

  const units = (cm: number) => cm / m.cmPerUnit;
  const toCm = (u: number) => Math.round(u * m.cmPerUnit * 10) / 10;

  function clamp(item: Placement): Placement {
    const w = Math.min(units(item.width_cm), VIEW_W), h = Math.min(units(item.height_cm), VIEW_H);
    const cx = Math.min(Math.max(item.x * VIEW_W, w / 2), VIEW_W - w / 2);
    const cy = Math.min(Math.max(item.y * VIEW_H, h / 2), VIEW_H - h / 2);
    return { ...item, x: cx / VIEW_W, y: cy / VIEW_H, width_cm: toCm(w), height_cm: toCm(h) };
  }

  const update = (i: number, item: Placement) => onChange(value.map((v, j) => (j === i ? clamp(item) : v)));

  function add(item: Placement) {
    if (value.length >= MAX_ITEMS) return;
    if (item.kind === "logo" && logoAspect) item = { ...item, height_cm: Math.round((item.width_cm / logoAspect) * 2) / 2 };
    setView(item.view);
    onChange([...value, clamp(item)]);
    setSelected(value.length);
  }

  function point(e: PointerEvent) {
    const ctm = svg.current?.getScreenCTM();
    if (!svg.current || !ctm) return { x: 0, y: 0 };
    const pt = svg.current.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const r = pt.matrixTransform(ctm.inverse());
    return { x: r.x, y: r.y };
  }

  function startDrag(e: PointerEvent, index: number, mode: Drag["mode"]) {
    e.stopPropagation();
    (e.target as Element).setPointerCapture(e.pointerId);
    const { x, y } = point(e);
    setSelected(index);
    setDrag({ index, mode, startX: x, startY: y, start: value[index] });
  }

  function onMove(e: PointerEvent) {
    if (!drag) return;
    const { x, y } = point(e);
    const dx = x - drag.startX, dy = y - drag.startY;
    const s = drag.start;
    if (drag.mode === "move") {
      update(drag.index, { ...s, x: s.x + dx / VIEW_W, y: s.y + dy / VIEW_H });
    } else {
      // Resize from the bottom-right corner, top-left stays put
      const w0 = units(s.width_cm), h0 = units(s.height_cm);
      const left = s.x * VIEW_W - w0 / 2, top = s.y * VIEW_H - h0 / 2;
      const w = Math.max(units(MIN_CM), w0 + dx), h = Math.max(units(MIN_CM), h0 + dy);
      update(drag.index, { ...s, x: (left + w / 2) / VIEW_W, y: (top + h / 2) / VIEW_H, width_cm: toCm(w), height_cm: toCm(h) });
    }
  }

  function onKey(e: KeyboardEvent, i: number) {
    const step = 4, item = value[i];
    const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key];
    if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      onChange(value.filter((_, j) => j !== i));
      setSelected(null);
    }
    if (!d) return;
    e.preventDefault();
    if (e.shiftKey) {
      update(i, { ...item, width_cm: Math.max(MIN_CM, item.width_cm + d[0] * m.cmPerUnit), height_cm: Math.max(MIN_CM, item.height_cm + d[1] * m.cmPerUnit) });
    } else {
      update(i, { ...item, x: item.x + d[0] / VIEW_W, y: item.y + d[1] / VIEW_H });
    }
  }

  const describe = (pl: Placement) => {
    const wearerLeft = pl.view === "front" ? pl.x > 0.56 : pl.x < 0.44;
    const wearerRight = pl.view === "front" ? pl.x < 0.44 : pl.x > 0.56;
    const side = wearerLeft ? t("posLeft") : wearerRight ? t("posRight") : t("posCentre");
    const area = pl.y < 0.2 ? t("posNeck") : pl.y < 0.42 ? t("posChest") : pl.y < 0.65 ? t("posMiddle") : t("posLower");
    return `${side} · ${area}`;
  };

  return (
    <div className="placement">
      <div className="spread">
        <div className="segmented" role="radiogroup" aria-label={t("view")}>
          {(["front", "back"] as View[]).map((v) => (
            <button key={v} type="button" role="radio" aria-checked={view === v} className={view === v ? "on" : ""}
              onClick={() => { setView(v); setSelected(null); }}>
              {t(v === "front" ? "viewFront" : "viewBack")}
            </button>
          ))}
        </div>
        <div className="row">
          {(["logo", "label"] as PlacementKind[]).map((kind) => (
            <button key={kind} type="button" className="chip" disabled={value.length >= MAX_ITEMS}
              onClick={() => add({ kind, view, x: 0.5, y: kind === "logo" ? 0.35 : 0.12,
                width_cm: kind === "logo" ? 10 : 5, height_cm: kind === "logo" ? 8 : 2.5 })}>
              <PlusIcon width={14} height={14} /> {t(kind === "logo" ? "addLogo" : "addLabel")}
            </button>
          ))}
        </div>
      </div>

      <div className="chips">
        {m.presets.map((pr) => (
          <button key={pr.key} type="button" className="chip" disabled={value.length >= MAX_ITEMS} onClick={() => add(pr.placement)}>
            {pr[lang]}
          </button>
        ))}
      </div>

      <div className="mockup-wrap" dir="ltr">
        <svg ref={svg} viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="mockup" onPointerMove={onMove}
          onPointerUp={() => setDrag(null)} onPointerCancel={() => setDrag(null)} onPointerDown={() => setSelected(null)}
          role="application" aria-label={t("placementHelp")}>
          <path d={m.paths[view].body} className="garment" />
          {m.paths[view].details.map((d) => <path key={d} d={d} className="garment-detail" />)}
          {value.map((pl, i) => {
            if (pl.view !== view) return null;
            const w = units(pl.width_cm), h = units(pl.height_cm);
            const x = pl.x * VIEW_W - w / 2, y = pl.y * VIEW_H - h / 2;
            const active = selected === i;
            return (
              <g key={i} className={`placed ${pl.kind}${active ? " active" : ""}`}>
                {pl.kind === "logo" && logoUrl && (
                  <image href={logoUrl} x={x + 2} y={y + 2} width={Math.max(0, w - 4)} height={Math.max(0, h - 4)}
                    preserveAspectRatio="xMidYMid meet" className="placed-logo" />
                )}
                <rect x={x} y={y} width={w} height={h} rx={pl.kind === "label" ? 2 : 6} tabIndex={0}
                  aria-label={`${t(pl.kind === "logo" ? "logoTag" : "labelTag")} ${pl.width_cm} × ${pl.height_cm} cm`}
                  onPointerDown={(e) => startDrag(e, i, "move")} onKeyDown={(e) => onKey(e, i)} onFocus={() => setSelected(i)} />
                <text x={x + w / 2} y={y + h / 2} className="placed-text">
                  {w > 34 && h > 14 && !(pl.kind === "logo" && logoUrl) ? t(pl.kind === "logo" ? "logoTag" : "labelTag") : ""}
                </text>
                <text x={x + w / 2} y={y + h + 14} className="placed-size">{pl.width_cm} × {pl.height_cm} cm</text>
                {active && (
                  <rect x={x + w - 7} y={y + h - 7} width={14} height={14} rx={3} className="handle"
                    onPointerDown={(e) => startDrag(e, i, "resize")} />
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {value.length === 0 ? (
        <p className="muted small">{t("placementEmpty")}</p>
      ) : (
        <ul className="placed-list">
          {value.map((pl, i) => (
            <li key={i} className={selected === i ? "active" : ""} onClick={() => { setView(pl.view); setSelected(i); }}>
              <span className={`pill ${pl.kind === "logo" ? "you" : "factories"}`}>{t(pl.kind === "logo" ? "logoTag" : "labelTag")}</span>
              <span className="muted small">{t(pl.view === "front" ? "viewFront" : "viewBack")} · {describe(pl)}</span>
              <span className="cm-inputs" dir="ltr">
                <input type="number" min={MIN_CM} max={60} step={0.5} value={pl.width_cm} aria-label={t("widthCm")}
                  onChange={(e) => update(i, { ...pl, width_cm: Math.max(MIN_CM, Number(e.target.value) || MIN_CM) })} />
                ×
                <input type="number" min={MIN_CM} max={60} step={0.5} value={pl.height_cm} aria-label={t("heightCm")}
                  onChange={(e) => update(i, { ...pl, height_cm: Math.max(MIN_CM, Number(e.target.value) || MIN_CM) })} />
                cm
              </span>
              <button type="button" className="icon-btn" aria-label={t("remove")}
                onClick={(e) => { e.stopPropagation(); onChange(value.filter((_, j) => j !== i)); setSelected(null); }}>×</button>
              <SizeHint item={pl} method={method} aspect={logoAspect} onApply={(w, h) => update(i, { ...pl, width_cm: w, height_cm: h })} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** "Orion suggests": the producible size closest to the customer's. Applied only when they tap it. */
function SizeHint({ item, method, aspect, onApply }: {
  item: Placement; method?: string; aspect?: number | null; onApply: (w: number, h: number) => void;
}) {
  const { t } = useLang();
  const s = suggestSize(item, method, aspect);
  if (!s) return null;
  const why = s.reason === "aspect" ? t("sizeWhyAspect")
    : s.reason === "too_big" ? t("sizeWhyBig").replace("{max}", String(s.limits.maxW))
    : t("sizeWhySmall").replace("{min}", String(s.limits.minW));
  return (
    <div className="size-hint" onClick={(e) => e.stopPropagation()}>
      <SparkleIcon width={16} height={16} />
      <span>
        <strong>{t("sizeSuggest")} <span dir="ltr">{s.width_cm} × {s.height_cm} cm</span></strong>
        <span className="muted small"> · {why}</span>
      </span>
      <button type="button" className="chip" onClick={() => onApply(s.width_cm, s.height_cm)}>{t("apply")}</button>
    </div>
  );
}