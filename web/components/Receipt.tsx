"use client";

// The product summary as something pleasant to read: product card, sizes, one board per section with an icon
// per line, colour swatches, a small drawing of where logos/labels go, and what is still open.
import type { ReactNode } from "react";

import type { Summary, SummaryItem } from "@/lib/api";
import { useLang, type TextKey } from "@/lib/i18n";
import { mockupFor, VIEW_H, VIEW_W, type Placement, type View } from "@/lib/mockups";
import { COLOR_SWATCHES, iconFor } from "@/lib/questions";
import { HashIcon, LightbulbIcon, PaletteIcon, ShieldIcon } from "./Icons";
import TopoTexture from "./TopoTexture";

const SECTION_TITLES: Record<string, { title: TextKey; icon: ReactNode }> = {
  design: { title: "sectionDesign", icon: <PaletteIcon /> },
  quantity: { title: "sectionQuantity", icon: <HashIcon /> },
  quality: { title: "sectionQuality", icon: <ShieldIcon /> },
};

const isPlacements = (raw: unknown): raw is Placement[] =>
  Array.isArray(raw) && raw.length > 0 && raw.every((p) => typeof p === "object" && p !== null && "view" in p);

export default function Receipt({ summary }: { summary: Summary }) {
  const { t } = useLang();
  const sizes = Object.entries(summary.sizes ?? {});
  const maxSize = Math.max(1, ...sizes.map(([, n]) => n));

  return (
    <div className="receipt-view stack">
      <div className="product-card receipt-hero">
        <div className="spread">
          <span className="label">{t("receiptTitle")}</span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="mark" src="/brand/mark-gold.png" alt="" />
        </div>
        <div>
          <div className="big">{summary.product}</div>
          <div className="label">{summary.market}</div>
        </div>
        {summary.quantity != null && (
          <div className="receipt-total"><strong>{summary.quantity}</strong> {t("totalPieces")}</div>
        )}
      </div>

      <p className="receipt-note"><LightbulbIcon width={18} height={18} /> {t("receiptNote")}</p>

      {sizes.length > 0 && (
        <div className="board board-glass cross">
          <h3 className="receipt-h"><span className="section-icon">{iconFor("size_breakdown")}</span>{t("sizesTitle")}</h3>
          <div className="size-bars" dir="ltr">
            {sizes.map(([size, n]) => (
              <div key={size} className="size-bar">
                <span className="size-name">{size}</span>
                <span className="bar"><span style={{ width: `${(n / maxSize) * 100}%` }} /></span>
                <span className="size-qty">{n}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {summary.sections.map((section) => (
        <div key={section.id} className={`board section-board section-${section.id} cross`}>
          {section.id !== "quantity" && <TopoTexture />}
          <h3 className="receipt-h">
            <span className="section-icon">{SECTION_TITLES[section.id]?.icon}</span>
            {t(SECTION_TITLES[section.id]?.title ?? "sectionDesign")}
          </h3>
          <ul className="receipt-rows">
            {section.items.map((item) => <Row key={item.id} item={item} mockup={summary.mockup} />)}
          </ul>
        </div>
      ))}

      {summary.extras.length > 0 && (
        <div className="board board-glass cross">
          <h3 className="receipt-h"><span className="section-icon">{iconFor("extra")}</span>{t("moreDetails")}</h3>
          <ul className="receipt-rows">{summary.extras.map((item) => <Row key={item.id} item={item} />)}</ul>
        </div>
      )}

      {summary.open_gaps.length > 0 && (
        <div className="board board-signal cross">
          <h3 className="receipt-h">{t("openPoints")}</h3>
          <ul className="gap-list">{summary.open_gaps.map((g) => <li key={g} dir="auto">{g}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

function Row({ item, mockup }: { item: SummaryItem; mockup?: string | null }) {
  const { t } = useLang();
  const colors = item.id === "colors" ? (Array.isArray(item.raw) ? item.raw : [item.raw]).map(String) : [];
  return (
    <li className={isPlacements(item.raw) ? "wide" : ""}>
      <span className="qicon">{iconFor(item.id)}</span>
      <div className="row-body">
        <span className="row-label" dir="auto">{item.label}</span>
        {isPlacements(item.raw) ? (
          <>
            <MockupPreview mockup={mockup} items={item.raw} />
            <span className="row-value small" dir="auto">{item.value}</span>
          </>
        ) : (
          <span className="row-value" dir="auto">
            {colors.filter((c) => COLOR_SWATCHES[c]).map((c) => (
              <span key={c} className="swatch" style={{ background: COLOR_SWATCHES[c] }} aria-hidden />
            ))}
            {item.value}
          </span>
        )}
      </div>
      {isPlacements(item.raw) && <span className="sr-only">{t("placementTitle")}</span>}
    </li>
  );
}

function MockupPreview({ mockup, items }: { mockup?: string | null; items: Placement[] }) {
  const { t } = useLang();
  const m = mockupFor(mockup);
  const views = (["front", "back"] as View[]).filter((v) => items.some((p) => p.view === v));
  return (
    <div className="mockup-previews" dir="ltr">
      {views.map((view) => (
        <figure key={view}>
          <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="mockup mini" aria-hidden>
            <path d={m.paths[view].body} className="garment" />
            {m.paths[view].details.map((d) => <path key={d} d={d} className="garment-detail" />)}
            {items.filter((p) => p.view === view).map((p, i) => {
              const w = p.width_cm / m.cmPerUnit, h = p.height_cm / m.cmPerUnit;
              return (
                <g key={i} className={`placed ${p.kind}`}>
                  <rect x={p.x * VIEW_W - w / 2} y={p.y * VIEW_H - h / 2} width={w} height={h} rx={p.kind === "label" ? 2 : 6} />
                  <text x={p.x * VIEW_W} y={p.y * VIEW_H + h / 2 + 16} className="placed-size">{p.width_cm} × {p.height_cm} cm</text>
                </g>
              );
            })}
          </svg>
          <figcaption>{t(view === "front" ? "viewFront" : "viewBack")}</figcaption>
        </figure>
      ))}
    </div>
  );
}
