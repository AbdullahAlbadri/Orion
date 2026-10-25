"use client";

// The brand kit on the business profile: saved logos and brand colours. Every new order offers them on its
// logo and colour questions (one tap to use, never filled in by itself), and the AI knows the colours.
import { useEffect, useRef, useState } from "react";

import { ApiError, api, brandLogoUrl, uploadBrandLogo, type BrandColor, type BrandLogo, type BusinessView } from "@/lib/api";
import { COMMON, t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { ImageIcon, PlusIcon } from "./Icons";

const ACCEPT = ".png,.jpg,.jpeg,.webp,.svg,.pdf,.ai,.eps,image/png,image/jpeg,image/webp,image/svg+xml,application/pdf";
const MAX_BYTES = 10 * 1024 * 1024;
export const MAX_LOGOS = 5;
const MAX_COLORS = 8;
const HEX = /^#[0-9A-Fa-f]{6}$/;

export const BRAND = {
  savedLogos: t("شعاراتك المحفوظة", "Your saved logos"),
  brandColors: t("ألوان علامتك", "Your brand colours"),
  use: t("استخدم", "Use"),
  added: t("أُضيف", "Added"),
  saveHint: t("احفظ شعارك وألوانك في ملف النشاط لتظهر هنا في كل طلب.",
    "Save your logo and colours in your business profile to see them here in every order."),
  openProfile: t("ملف النشاط", "Business profile"),
};

const C = {
  logos: t("الشعارات", "Logos"),
  logosHint: t("حتى 5 ملفات. الملفات المتجهة (SVG وAI وEPS وPDF) أفضل للطباعة والتطريز.",
    "Up to 5 files. Vector files (SVG, AI, EPS, PDF) print and embroider best."),
  upload: t("ارفع شعارًا", "Upload a logo"),
  uploading: t("جارٍ الرفع…", "Uploading…"),
  types: t("PNG أو JPG أو SVG أو PDF أو AI أو EPS، حتى 10 ميغابايت", "PNG, JPG, SVG, PDF, AI or EPS, up to 10 MB"),
  tooBig: t("الملف أكبر من 10 ميغابايت.", "The file is larger than 10 MB."),
  wrongType: t("نوع الملف غير مدعوم.", "This file type isn't supported."),
  full: t("وصلت إلى الحد الأقصى (5 شعارات).", "You've reached the limit (5 logos)."),
  colors: t("ألوان العلامة", "Brand colours"),
  colorsHint: t("حتى 8 ألوان. اكتب رمز HEX إن كان لديك، مثل ‎#FEB72F.", "Up to 8 colours. Type the HEX code if you have it, like #FEB72F."),
  colorName: t("اسم اللون (اختياري)", "Colour name (optional)"),
  namePh: t("مثل: الذهبي", "e.g. Gold"),
  add: t("إضافة اللون", "Add colour"),
  badHex: t("رمز HEX من 6 خانات بعد #", "A HEX code is # and 6 characters"),
  noColors: t("لا ألوان بعد.", "No colours yet."),
  removeColor: t("حذف اللون", "Remove colour"),
  removeLogo: t("حذف الشعار", "Remove logo"),
};

export function LogoThumb({ logo }: { logo: BrandLogo }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!logo.content_type.startsWith("image/")) return;
    let alive = true;
    brandLogoUrl(logo.file_id).then((u) => alive && setUrl(u)).catch(() => {});
    return () => { alive = false; };
  }, [logo.file_id, logo.content_type]);
  return url
    // eslint-disable-next-line @next/next/no-img-element
    ? <img className="thumb" src={url} alt={logo.name} />
    : <span className="thumb thumb-doc"><ImageIcon /><span>{logo.name.split(".").pop()?.toUpperCase()}</span></span>;
}

export function Swatch({ hex }: { hex: string }) {
  return <span className="swatch" style={{ background: hex }} aria-hidden="true" />;
}

/** How a brand colour is written into an answer: "Gold #FEB72F", or just the code. */
export const colorAnswer = (c: BrandColor) => (c.name ? `${c.name} ${c.hex}` : c.hex);

export default function BrandKit({ view, onSaved }: { view: BusinessView; onSaved: (v: BusinessView) => void }) {
  const { lang } = useLang();
  const L = (x: T) => x[lang];
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [over, setOver] = useState(false);
  const [hex, setHex] = useState("#FEB72F");
  const [name, setName] = useState("");
  const [colorError, setColorError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const colors = view.profile.brand_colors ?? [];
  const logos = view.logos ?? [];

  async function upload(list: FileList | null) {
    if (!list?.length) return;
    setBusy(true); setError(null);
    for (const file of Array.from(list).slice(0, MAX_LOGOS - logos.length)) {
      if (file.size > MAX_BYTES) { setError(L(C.tooBig)); continue; }
      try {
        onSaved(await uploadBrandLogo(file));
      } catch (e) {
        const status = e instanceof ApiError ? e.status : 0;
        setError(status === 415 ? L(C.wrongType) : status === 413 ? L(C.tooBig) : status === 409 ? L(C.full) : L(COMMON.error));
      }
    }
    setBusy(false);
    if (input.current) input.current.value = "";
  }

  async function removeLogo(id: string) {
    try { onSaved(await api<BusinessView>(`/business/logos/${encodeURIComponent(id)}`, { method: "DELETE" })); }
    catch { setError(L(COMMON.error)); }
  }

  async function saveColors(next: BrandColor[]) {
    setColorError(null);
    try {
      onSaved(await api<BusinessView>("/business", { method: "PUT", body: { brand_colors: next } }));
      setSaved(true); setTimeout(() => setSaved(false), 2000);
      return true;
    } catch { setColorError(L(COMMON.error)); return false; }
  }

  async function addColor(e: React.FormEvent) {
    e.preventDefault();
    const code = (hex.startsWith("#") ? hex : `#${hex}`).trim().toUpperCase();
    if (!HEX.test(code)) { setColorError(L(C.badHex)); return; }
    if (await saveColors([...colors.filter((c) => c.hex !== code), { hex: code, name: name.trim() || null }])) setName("");
  }

  return (
    <div className="brand-kit">
      <div className="stack-sm">
        <strong>{L(C.logos)}</strong>
        <span className="muted small">{L(C.logosHint)}</span>
        {logos.length > 0 && (
          <ul className="file-list">
            {logos.map((l) => (
              <li key={l.file_id}>
                <LogoThumb logo={l} />
                <span className="file-name" dir="auto">{l.name}</span>
                <button type="button" className="icon-btn" aria-label={L(C.removeLogo)} onClick={() => removeLogo(l.file_id)}>×</button>
              </li>
            ))}
          </ul>
        )}
        {logos.length < MAX_LOGOS && (
          <div className={`dropzone${over ? " over" : ""}`} role="button" tabIndex={0}
            onClick={() => input.current?.click()}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.current?.click(); } }}
            onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); upload(e.dataTransfer.files); }}>
            <span className="dropzone-icon"><PlusIcon /></span>
            <strong>{busy ? L(C.uploading) : L(C.upload)}</strong>
            <span className="muted small">{L(C.types)}</span>
            <input ref={input} type="file" accept={ACCEPT} multiple hidden onChange={(e) => upload(e.target.files)} />
          </div>
        )}
        {error && <p className="error small">{error}</p>}
      </div>

      <div className="stack-sm">
        <strong>{L(C.colors)}</strong>
        <span className="muted small">{L(C.colorsHint)}</span>
        {colors.length === 0 ? <span className="muted small">{L(C.noColors)}</span> : (
          <div className="chips">
            {colors.map((c) => (
              <span key={c.hex} className="chip color-chip">
                <Swatch hex={c.hex} />
                {c.name && <span dir="auto">{c.name}</span>}
                <span className="hex" dir="ltr">{c.hex}</span>
                <button type="button" className="icon-btn" aria-label={`${L(C.removeColor)} ${c.hex}`}
                  onClick={() => saveColors(colors.filter((x) => x.hex !== c.hex))}>×</button>
              </span>
            ))}
          </div>
        )}
        {colors.length < MAX_COLORS && (
          <form className="color-add" onSubmit={addColor}>
            <input type="color" aria-label={L(C.colors)} value={HEX.test(hex) ? hex : "#000000"}
              onChange={(e) => setHex(e.target.value.toUpperCase())} />
            <input className="hex-input" dir="ltr" value={hex} maxLength={7} aria-label="HEX"
              onChange={(e) => setHex(e.target.value)} />
            <input dir="auto" value={name} maxLength={40} placeholder={L(C.namePh)} aria-label={L(C.colorName)}
              onChange={(e) => setName(e.target.value)} />
            <button className="btn btn-sm"><PlusIcon width={16} height={16} /> {L(C.add)}</button>
          </form>
        )}
        {saved && <span className="saved-note">{L(COMMON.saved)}</span>}
        {colorError && <span className="error small">{colorError}</span>}
      </div>
    </div>
  );
}
