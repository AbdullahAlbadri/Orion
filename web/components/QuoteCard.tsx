"use client";

// The customer's quote: prices in riyals as calculated by the API (the page never computes a price), shipping
// marked as approximate, the expected timing, and accept / decline. Payment happens later on a hosted checkout.
import { useState } from "react";

import type { CustomerQuote } from "@/lib/api";
import { formatDate, t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import { CheckIcon, TagIcon } from "./Icons";

// Also used for the agreed price on the order page (OrderSections.tsx), so both say the same thing
export const QUOTE_TEXT = {
  title: t("عرض السعر جاهز", "Your quote is ready"),
  sub: t("راجع العرض ثم أكّده للانتقال إلى الدفع.", "Review the quote, then accept it to move on to payment."),
  unit: t("سعر القطعة", "Price per piece"),
  qty: t("الكمية", "Quantity"),
  pieces: t("قطعة", "pcs"),
  products: t("إجمالي المنتجات", "Products"),
  shipping: t("الشحن (تقديري)", "Shipping (approximate)"),
  shippingLater: t("يُحدَّد لاحقًا", "To be confirmed"),
  total: t("الإجمالي", "Total"),
  sample: t("العينة (تُدفع قبل الإنتاج)", "Sample (paid before production)"),
  timing: t("المدة المتوقعة", "Expected timing"),
  production: t("التصنيع", "Production"),
  transit: t("الشحن", "Shipping"),
  arrives: t("الوصول خلال", "Arrives within"),
  days: t("يومًا تقريبًا", "days approx."),
  valid: t("العرض صالح حتى", "Valid until"),
  note: t("سعر الشحن تقديري وقد يختلف قليلًا. لن نطلب منك بيانات الدفع هنا؛ سنرسل لك رابط دفع آمنًا.",
    "The shipping price is an estimate and may change slightly. We never ask for payment details here; you'll get a secure payment link."),
  accept: t("قبول العرض", "Accept quote"),
  decline: t("رفض العرض", "Decline"),
  why: t("ما السبب؟ (اختياري) يساعدنا لنعرض عليك بديلًا مناسبًا.", "Why? (optional) It helps us offer a better alternative."),
  send: t("إرسال", "Send"),
  back: t("رجوع", "Back"),
  sar: t("ر.س", "SAR"),
};
const C = QUOTE_TEXT;

export default function QuoteCard({ quote, error, send, busy }: {
  quote: CustomerQuote; error?: string | null; send: (reply: Record<string, unknown>) => Promise<void>; busy: boolean;
}) {
  const { lang } = useLang();
  const { calendar } = useMe();
  const L = (x: T) => x[lang];
  const [declining, setDeclining] = useState(false);
  const [reason, setReason] = useState("");
  const money = (v: string) => `${Number(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${L(C.sar)}`;
  const arrival = quote.production_days != null && quote.shipping_days != null ? quote.production_days + quote.shipping_days : null;

  return (
    <section className="board board-glass stack quote-card">
      <div className="row">
        <span className="section-icon"><TagIcon /></span>
        <div>
          <h2 style={{ margin: 0 }}>{L(C.title)}</h2>
          <div className="muted small">{L(C.sub)}</div>
        </div>
      </div>

      <dl className="quote-lines">
        <div><dt>{L(C.unit)}</dt><dd dir="ltr">{money(quote.unit_price)}</dd></div>
        <div><dt>{L(C.qty)}</dt><dd>{quote.quantity.toLocaleString("en-GB")} {L(C.pieces)}</dd></div>
        <div><dt>{L(C.products)}</dt><dd dir="ltr">{money(quote.products_total)}</dd></div>
        <div><dt>{L(C.shipping)}</dt><dd dir="ltr">{quote.shipping ? money(quote.shipping) : L(C.shippingLater)}</dd></div>
        <div className="quote-total"><dt>{L(C.total)}</dt><dd dir="ltr">{money(quote.total)}</dd></div>
        {quote.sample_price && <div><dt>{L(C.sample)}</dt><dd dir="ltr">{money(quote.sample_price)}</dd></div>}
      </dl>

      {(quote.production_days != null || quote.shipping_days != null) && (
        <div className="quote-timing">
          <strong>{L(C.timing)}</strong>
          <div className="row small">
            {quote.production_days != null && <span>{L(C.production)}: {quote.production_days} {L(C.days)}</span>}
            {quote.shipping_days != null && <span>{L(C.transit)}: {quote.shipping_days} {L(C.days)}</span>}
            {arrival != null && <span className="st st-moving">{L(C.arrives)} {arrival} {L(C.days)}</span>}
          </div>
        </div>
      )}

      <div className="muted small">{L(C.valid)}: {formatDate(quote.valid_until, lang, calendar)}</div>
      <p className="note" style={{ margin: 0 }}>{L(C.note)}</p>
      {error && <p className="error">{error}</p>}

      {!declining ? (
        <div className="row">
          <button className="btn" disabled={busy} onClick={() => send({ accept: true })}>
            <CheckIcon width={18} height={18} /> {L(C.accept)}
          </button>
          <button className="btn-ghost" disabled={busy} onClick={() => setDeclining(true)}>{L(C.decline)}</button>
        </div>
      ) : (
        <form className="stack" onSubmit={(e) => { e.preventDefault(); send({ accept: false, reason: reason.trim() }); }}>
          <textarea dir="auto" value={reason} maxLength={500} placeholder={L(C.why)} onChange={(e) => setReason(e.target.value)} />
          <div className="row">
            <button className="btn" disabled={busy}>{L(C.send)}</button>
            <button type="button" className="btn-ghost" onClick={() => setDeclining(false)}>{L(C.back)}</button>
          </div>
        </form>
      )}
    </section>
  );
}
