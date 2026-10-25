"use client";

// Business details and address forms, used by the Business profile page and the /start onboarding.
// The server validates again; these checks only help the customer fix things early.
import { useState } from "react";

import { api, ApiError, type Address, type AddressInput, type BusinessProfile, type BusinessView } from "@/lib/api";
import { COMMON, t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";

export const BUSINESS_TYPES: Record<string, T> = {
  online_store: t("متجر إلكتروني", "Online store"), shop: t("محل تجاري", "Shop"), food: t("مقهى أو مطعم", "Café or restaurant"),
  brand: t("علامة تجارية", "Brand"), company: t("شركة", "Company"), other: t("أخرى", "Other"),
};
export const PLATFORMS: Record<string, T> = {
  salla: t("سلة", "Salla"), zid: t("زد", "Zid"), shopify: t("شوبيفاي", "Shopify"), instagram: t("إنستغرام", "Instagram"),
  other: t("أخرى", "Other"), none: t("لا يوجد متجر", "No store"),
};

const C = {
  name: t("اسم النشاط", "Business name"),
  type: t("نوع النشاط", "Business type"),
  platform: t("منصة المتجر", "Store platform"),
  url: t("رابط المتجر", "Store link"),
  urlHint: t("يبدأ بـ https://", "Starts with https://"),
  description: t("ماذا تبيع؟", "What do you sell?"),
  descriptionHint: t("سطر أو سطران. يقرؤه المساعد قبل كل طلب ليقترح ما يناسبك.",
    "One or two lines. The assistant reads it before each order to suggest what fits you."),
  pick: t("اختر", "Choose"),
  label: t("اسم العنوان", "Address name"), labelPh: t("مثل: المستودع", "e.g. Warehouse"),
  contact: t("اسم المستلم", "Receiver's name"), phone: t("رقم الجوال", "Mobile number"),
  city: t("المدينة", "City"), district: t("الحي", "District"), street: t("الشارع", "Street"),
  building: t("رقم المبنى", "Building number"), postal: t("الرمز البريدي", "Postal code"),
  notes: t("ملاحظات التوصيل", "Delivery notes"),
  makeDefault: t("العنوان الافتراضي", "Default address"),
  badPhone: t("أدخل رقمًا صحيحًا، مثل ‎+966 5x xxx xxxx", "Enter a valid number, like +966 5x xxx xxxx"),
  badPostal: t("الرمز البريدي 5 أرقام", "Postal codes have 5 digits"),
  badUrl: t("الرابط يبدأ بـ https://", "The link starts with https://"),
  required: t("مطلوب", "Required"),
};

const PHONE = /^\+?[0-9][0-9 \-]{6,18}$/;

export function BusinessDetailsForm({ profile, onSaved, submitLabel }: {
  profile: BusinessProfile; onSaved: (v: BusinessView) => void; submitLabel?: string;
}) {
  const { lang } = useLang();
  const L = (x: T) => x[lang];
  const [f, setF] = useState({
    name: profile.name ?? "", business_type: profile.business_type ?? "", store_platform: profile.store_platform ?? "",
    store_url: profile.store_url ?? "", description: profile.description ?? "",
  });
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const badUrl = f.store_url && !/^https?:\/\/\S+$/.test(f.store_url);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (badUrl) return;
    setBusy(true); setError(null);
    try {
      const body = { ...f, business_type: f.business_type || null, store_platform: f.store_platform || null, store_url: f.store_url || null };
      onSaved(await api<BusinessView>("/business", { method: "PUT", body }));
      setSaved(true); setTimeout(() => setSaved(false), 2000);
    } catch { setError(L(COMMON.error)); } finally { setBusy(false); }
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <div className="field"><label htmlFor="b-name">{L(C.name)}</label>
        <input id="b-name" value={f.name} maxLength={120} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
      <div className="field"><label htmlFor="b-type">{L(C.type)}</label>
        <select id="b-type" value={f.business_type} onChange={(e) => setF({ ...f, business_type: e.target.value })}>
          <option value="">{L(C.pick)}</option>
          {Object.entries(BUSINESS_TYPES).map(([k, v]) => <option key={k} value={k}>{L(v)}</option>)}
        </select></div>
      <div className="field"><label htmlFor="b-platform">{L(C.platform)}</label>
        <select id="b-platform" value={f.store_platform} onChange={(e) => setF({ ...f, store_platform: e.target.value })}>
          <option value="">{L(C.pick)}</option>
          {Object.entries(PLATFORMS).map(([k, v]) => <option key={k} value={k}>{L(v)}</option>)}
        </select></div>
      <div className="field"><label htmlFor="b-url">{L(C.url)} <span className="muted small">({L(COMMON.optional)})</span></label>
        <input id="b-url" dir="ltr" type="url" value={f.store_url} maxLength={300} placeholder="https://"
          onChange={(e) => setF({ ...f, store_url: e.target.value })} aria-invalid={!!badUrl} />
        {badUrl && <div className="field-error">{L(C.badUrl)}</div>}</div>
      <div className="field full"><label htmlFor="b-desc">{L(C.description)}</label>
        <textarea id="b-desc" value={f.description} maxLength={600} onChange={(e) => setF({ ...f, description: e.target.value })} />
        <div className="hint">{L(C.descriptionHint)}</div></div>
      <div className="form-actions full">
        <button className="btn" disabled={busy}>{submitLabel ?? L(COMMON.save)}</button>
        {saved && <span className="saved-note">{L(COMMON.saved)}</span>}
        {error && <span className="error">{error}</span>}
      </div>
    </form>
  );
}

const EMPTY: AddressInput = { label: "", contact_name: "", phone: "", city: "", district: "", street: "", building: "",
  postal_code: "", notes: "", is_default: false };

export function AddressForm({ address, onSaved, onCancel, submitLabel }: {
  address?: Address | null; onSaved: (v: BusinessView) => void; onCancel?: () => void; submitLabel?: string;
}) {
  const { lang } = useLang();
  const L = (x: T) => x[lang];
  const [f, setF] = useState<AddressInput>(address ? { ...EMPTY, ...address } : EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);
  const errors = {
    contact_name: !f.contact_name.trim() ? L(C.required) : null,
    phone: !PHONE.test(f.phone.trim()) ? L(C.badPhone) : null,
    city: !f.city.trim() ? L(C.required) : null,
    street: !f.street.trim() ? L(C.required) : null,
    postal_code: f.postal_code && !/^\d{5}(-?\d{4})?$/.test(f.postal_code) ? L(C.badPostal) : null,
  };
  const invalid = Object.values(errors).some(Boolean);
  const set = (k: keyof AddressInput) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (invalid) return;
    setBusy(true); setError(null);
    const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, typeof v === "string" ? v.trim() || null : v]));
    try {
      const path = address ? `/business/addresses/${encodeURIComponent(address.id)}` : "/business/addresses";
      onSaved(await api<BusinessView>(path, { method: address ? "PUT" : "POST", body }));
    } catch (err) {
      setError(err instanceof ApiError && err.status === 422 ? L(C.badPhone) : L(COMMON.error));
    } finally { setBusy(false); }
  }

  const field = (k: keyof typeof errors | "label" | "district" | "building", label: T, opts: { ltr?: boolean; optional?: boolean; ph?: T } = {}) => (
    <div className="field">
      <label htmlFor={`a-${k}`}>{L(label)}{opts.optional && <span className="muted small"> ({L(COMMON.optional)})</span>}</label>
      <input id={`a-${k}`} dir={opts.ltr ? "ltr" : undefined} value={(f[k] as string) ?? ""} onChange={set(k)}
        placeholder={opts.ph ? L(opts.ph) : undefined} aria-invalid={touched && !!(errors as Record<string, string | null>)[k]} />
      {touched && (errors as Record<string, string | null>)[k] && <div className="field-error">{(errors as Record<string, string | null>)[k]}</div>}
    </div>
  );

  return (
    <form className="form-grid" onSubmit={submit} noValidate>
      {field("label", C.label, { optional: true, ph: C.labelPh })}
      {field("contact_name", C.contact)}
      {field("phone", C.phone, { ltr: true })}
      {field("city", C.city)}
      {field("district", C.district, { optional: true })}
      {field("street", C.street)}
      {field("building", C.building, { optional: true })}
      {field("postal_code", C.postal, { ltr: true, optional: true })}
      <div className="field full"><label htmlFor="a-notes">{L(C.notes)} <span className="muted small">({L(COMMON.optional)})</span></label>
        <textarea id="a-notes" value={f.notes ?? ""} maxLength={300} onChange={set("notes")} style={{ minHeight: 70 }} /></div>
      <label className="check-row full">
        <input type="checkbox" checked={!!f.is_default} onChange={(e) => setF({ ...f, is_default: e.target.checked })} /> {L(C.makeDefault)}
      </label>
      <div className="form-actions full">
        <button className="btn" disabled={busy}>{submitLabel ?? L(COMMON.save)}</button>
        {onCancel && <button type="button" className="btn-ghost" onClick={onCancel}>{L(COMMON.cancel)}</button>}
        {error && <span className="error">{error}</span>}
      </div>
    </form>
  );
}
