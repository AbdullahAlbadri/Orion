"use client";

// The product summary as something pleasant to read: product card, sizes, one board per section with an icon
// per line, colour swatches, a small drawing of where logos/labels go, and what is still open.
import { useEffect, useState, type ReactNode } from "react";

import { fileObjectUrl, type Summary, type SummaryItem, type UploadedFile } from "@/lib/api";
import { useLang, type TextKey } from "@/lib/i18n";
import { mockupFor, VIEW_H, VIEW_W, type Placement, type View } from "@/lib/mockups";
import { COLOR_SWATCHES, iconFor } from "@/lib/questions";
import { HashIcon, LightbulbIcon, PaletteIcon, ShieldIcon } from "./Icons";
import { FileThumb } from "./FileUpload";
import TopoTexture from "./TopoTexture";

const SECTION_TITLES: Record<string, { title: TextKey; icon: ReactNode }> = {
  design: { title: "sectionDesign", icon: <PaletteIcon /> },
  quantity: { title: "sectionQuantity", icon: <HashIcon /> },
  quality: { title: "sectionQuality", icon: <ShieldIcon /> },
};

const isFiles = (raw: unknown): raw is UploadedFile[] =>
  Array.isArray(raw) && raw.length > 0 && raw.every((f) => typeof f === "object" && f !== null && "file_id" in f);

const isZoneColors = (raw: unknown): raw is Record<string, string> =>
  typeof raw === "object" && raw !== null && !Array.isArray(raw) && Object.keys(raw).length > 0
  && Object.values(raw).every((v) => typeof v === "string" && /^#[0-9a-f]{6}$/i.test(v));

const isPlacements = (raw: unknown): raw is Placement[] =>
  Array.isArray(raw) && raw.length > 0 && raw.every((p) => typeof p === "object" && p !== null && "view" in p);

export default function Receipt({ summary, orderId }: { summary: Summary; orderId: string }) {
  const { t } = useLang();
  // The customer's logo, drawn on the garment previews
  const logoFile = summary.sections.flatMap((s) => s.items).filter((i) => isFiles(i.raw))
    .flatMap((i) => i.raw as UploadedFile[]).find((f) => f.content_type.startsWith("image/"));
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!logoFile) return;
    let alive = true;
    fileObjectUrl(orderId, logoFile.file_id).then((u) => alive && setLogoUrl(u)).catch(() => {});
    return () => { alive = false; };
  }, [orderId, logoFile?.file_id]);   // eslint-disable-line react-hooks/exhaustive-deps
  const sizes = Object.entries(summary.sizes ?? {});
  const maxSize = Math.max(1, ...sizes.map(([, n]) => n));

  return (
    <div className="receipt-view stack">
      <div className="product-card receipt-hero">
        <span className="label">{t("receiptTitle")}</span>
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
            {section.items.map((item) => <Row key={item.id} item={item} mockup={summary.mockup} orderId={orderId} logoUrl={logoUrl} />)}
          </ul>
        </div>
      ))}

      {summary.extras.length > 0 && (
        <div className="board board-glass cross">
          <h3 className="receipt-h"><span className="section-icon">{iconFor("extra")}</span>{t("moreDetails")}</h3>
          <ul className="receipt-rows">{summary.extras.map((item) => <Row key={item.id} item={item} orderId={orderId} />)}</ul>
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

function Row({ item, mockup, orderId, logoUrl }: {
  item: SummaryItem; mockup?: string | null; orderId: string; logoUrl?: string | null;
}) {
  const { t } = useLang();
  const colors = item.id === "colors" ? (Array.isArray(item.raw) ? item.raw : [item.raw]).map(String) : [];
  return (
    <li className={isPlacements(item.raw) || isFiles(item.raw) ? "wide" : ""}>
      <span className="qicon">{iconFor(item.id)}</span>
      <div className="row-body">
        <span className="row-label" dir="auto">{item.label}</span>
        {isPlacements(item.raw) ? (
          <>
            <MockupPreview mockup={mockup} items={item.raw} logoUrl={logoUrl} />
            <span className="row-value small" dir="auto">{item.value}</span>
          </>
        ) : isZoneColors(item.raw) ? (
          <span className="row-value zone-summary">
            {Object.entries(item.raw).map(([zone, hex]) => (
              <span key={zone} className="zone-summary-item">
                <span className="swatch" style={{ background: hex }} aria-hidden />
                <span dir="auto">{zone.replace(/_/g, " ")}</span>
                <span className="muted small" dir="ltr">{hex}</span>
              </span>
            ))}
          </span>
        ) : isFiles(item.raw) ? (
          <span className="row-value">
            {item.raw.map((f) => <span key={f.file_id} className="row">
              <FileThumb orderId={orderId} file={f} /> <span dir="auto">{f.name}</span></span>)}
          </span>
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

function MockupPreview({ mockup, items, logoUrl }: { mockup?: string | null; items: Placement[]; logoUrl?: string | null }) {
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
                  {p.kind === "color" && <rect x={p.x * VIEW_W - w / 2} y={p.y * VIEW_H - h / 2} width={w} height={h} rx={3} fill={p.color} />}
                  {p.kind === "logo" && logoUrl && (
                    <image href={logoUrl} x={p.x * VIEW_W - w / 2 + 2} y={p.y * VIEW_H - h / 2 + 2} width={Math.max(0, w - 4)}
                      height={Math.max(0, h - 4)} preserveAspectRatio="xMidYMid meet" />
                  )}
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
