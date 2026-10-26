"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AgreedQuote, OrderUpdates } from "@/components/OrderSections";
import { JourneyTracker } from "@/components/OrderTracker";
import Planet from "@/components/Planet";
import PromptView from "@/components/PromptView";
import Receipt from "@/components/Receipt";
import { api, ApiError, type OrderView } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { productName, useLang } from "@/lib/i18n";
import { groupOf } from "@/lib/orders";

export default function OrderPage() {
  const user = useRequireUser();
  const { id } = useParams<{ id: string }>();
  const { t, lang } = useLang();
  const [order, setOrder] = useState<OrderView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => api<OrderView>(`/orders/${encodeURIComponent(id)}`).then(setOrder), [id]);

  useEffect(() => {
    if (user) load().catch(() => setError(t("error")));
  }, [user, load, t]);

  // While the factories have the turn, check for news now and then
  useEffect(() => {
    if (order?.waiting_on !== "manufacturer") return;
    const timer = setInterval(() => { if (!document.hidden) load().catch(() => {}); }, 60_000);
    return () => clearInterval(timer);
  }, [order?.waiting_on, load]);

  const send = useCallback(async (reply: Record<string, unknown>) => {
    setBusy(true);
    setError(null);
    try {
      // The language goes with every answer, so Orion's follow-up questions come in it
      const next = await api<OrderView>(`/orders/${encodeURIComponent(id)}/reply`, {
        method: "POST", body: { reply: { ...reply, lang } },
      });
      // Replies do not carry the updates list (only loading the order does): keep the one we have
      setOrder((prev) => ({ ...next, updates: next.updates ?? prev?.updates }));
    } catch (e) {
      setError(e instanceof ApiError && e.status === 409 ? null : t("error"));
      await load().catch(() => {});
    } finally {
      setBusy(false);
    }
  }, [id, load, t, lang]);

  if (!user || !order) return <p className={error ? "error" : "muted"}>{error ?? t("loading")}</p>;

  const option = order.spec?.option;
  // Once the order is placed: its updates first, then anything the customer must do now (e.g. review the
  // quote), the agreed price, and the order's details. Before that, the page is the ordering steps.
  const placed = groupOf(order.stage) !== "draft";

  return (
    <>
      <p><Link href="/orders" className="muted">← {t("myOrders")}</Link></p>
      {error && <p className="error">{error}</p>}
      <div className="order-grid">
        {placed ? (
          <div className="od-col">
            <OrderUpdates order={order} />
            {order.waiting_on === "customer" && order.prompt && <PromptView order={order} send={send} busy={busy} />}
            {order.agreed_quote && <AgreedQuote quote={order.agreed_quote} />}
            {order.summary ? <Receipt summary={order.summary} orderId={order.order_id} />
              : order.pre_receipt && <pre className="receipt">{order.pre_receipt}</pre>}
          </div>
        ) : <PromptView order={order} send={send} busy={busy} />}

        <aside className="side-panel">
          {/* the order as a paper ticket: its code, the product as a planet, and how many */}
          <article className="od-ticket">
            <div className="od-top"><b>{t("orderTitle")}</b><span dir="ltr">{order.order_id}</span></div>
            <div className="od-main">
              <Planet option={option ?? null} size={60} />
              <div className="stack-sm">
                <strong className="od-name">{productName(option, lang)}</strong>
                <span className="od-sub">{order.spec?.quantity ? `${order.spec.quantity} ${t("pieces")}` : order.status[lang]}</span>
              </div>
            </div>
            <span className="od-barcode" aria-hidden />
          </article>

          <section className="od-route">
            <div className="spread" style={{ marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>{t("journey")}</h2>
              <span className="muted small">{order.status[lang]}</span>
            </div>
            <JourneyTracker stage={order.stage} />
          </section>
        </aside>
      </div>
    </>
  );
}
