"use client";

// The parts of a placed order's page, top to bottom: its updates (newest first, on a route line), the price
// the customer agreed to (a paper ticket; prices come from the API, the page never computes one), then the
// order's details (the receipt, rendered by the page).
import type { CustomerQuote, Notification, OrderView } from "@/lib/api";
import { ago, formatDate, t } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import { BellIcon } from "./Icons";
import { QUOTE_TEXT as Q } from "./QuoteCard";

const C = {
  updates: t("آخر التحديثات", "Latest updates"),
  none: t("لا تحديثات بعد. سنخبرك هنا وفي رسائلك عند كل خطوة.", "No updates yet. We'll tell you here and in your messages at every step."),
  agreed: t("السعر المتفق عليه", "Agreed price"),
  acceptedOn: t("وافقت عليه في", "Accepted on"),
};

export function OrderUpdates({ order }: { order: OrderView }) {
  const { lang } = useLang();
  const items: Notification[] = order.updates ?? [];
  return (
    <section className="od-updates" aria-labelledby="od-updates">
      <div className="spread">
        <h2 id="od-updates" className="ov-h"><span className="ov-pulse" aria-hidden /> {C.updates[lang]}</h2>
        <span className="flap dep-status">{order.status[lang]}</span>
      </div>
      {items.length === 0 ? <p className="muted" style={{ margin: 0 }}>{C.none[lang]}</p> : (
        <ol className="od-timeline">
          {items.map((n, i) => (
            <li key={n.id} className={i === 0 ? "latest" : undefined}>
              <span className="od-dot" aria-hidden>{i === 0 && <BellIcon width={14} height={14} />}</span>
              <div className="stack-sm grow">
                <strong>{lang === "ar" ? n.title_ar : n.title_en}</strong>
                {(lang === "ar" ? n.body_ar : n.body_en) && <span className="muted small">{lang === "ar" ? n.body_ar : n.body_en}</span>}
              </div>
              <span className="muted small od-when">{ago(n.created_at, lang)}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export function AgreedQuote({ quote }: { quote: CustomerQuote & { accepted_at: string } }) {
  const { lang } = useLang();
  const { calendar } = useMe();
  const money = (v: string) => `${Number(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${Q.sar[lang]}`;
  return (
    <article className="od-price" aria-labelledby="od-price">
      <div className="ov-doc-top"><b id="od-price">{C.agreed[lang]}</b>
        <span>{C.acceptedOn[lang]} {formatDate(quote.accepted_at, lang, calendar)}</span></div>
      <dl className="ov-doc-rows">
        <div><dt>{Q.unit[lang]}</dt><i aria-hidden /><dd dir="ltr">{money(quote.unit_price)}</dd></div>
        <div><dt>{Q.qty[lang]}</dt><i aria-hidden /><dd>{quote.quantity.toLocaleString("en-GB")} {Q.pieces[lang]}</dd></div>
        <div><dt>{Q.products[lang]}</dt><i aria-hidden /><dd dir="ltr">{money(quote.products_total)}</dd></div>
        <div><dt>{Q.shipping[lang]}</dt><i aria-hidden /><dd dir="ltr">{quote.shipping ? money(quote.shipping) : Q.shippingLater[lang]}</dd></div>
        {quote.sample_price && <div><dt>{Q.sample[lang]}</dt><i aria-hidden /><dd dir="ltr">{money(quote.sample_price)}</dd></div>}
        <div className="od-total"><dt>{Q.total[lang]}</dt><i aria-hidden /><dd dir="ltr">{money(quote.total)}</dd></div>
      </dl>
      {(quote.production_days != null || quote.shipping_days != null) && (
        <p className="od-timing">
          {quote.production_days != null && <span>{Q.production[lang]}: {quote.production_days} {Q.days[lang]}</span>}
          {quote.shipping_days != null && <span>{Q.transit[lang]}: {quote.shipping_days} {Q.days[lang]}</span>}
        </p>
      )}
    </article>
  );
}
