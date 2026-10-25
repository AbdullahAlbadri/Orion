"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { JourneyTracker } from "@/components/OrderTracker";
import PromptView from "@/components/PromptView";
import TopoTexture from "@/components/TopoTexture";
import { api, ApiError, type OrderView } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { productName, useLang } from "@/lib/i18n";

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
      setOrder(await api<OrderView>(`/orders/${encodeURIComponent(id)}/reply`, {
        method: "POST", body: { reply: { ...reply, lang } },
      }));
    } catch (e) {
      setError(e instanceof ApiError && e.status === 409 ? null : t("error"));
      await load().catch(() => {});
    } finally {
      setBusy(false);
    }
  }, [id, load, t, lang]);

  if (!user || !order) return <p className={error ? "error" : "muted"}>{error ?? t("loading")}</p>;

  const option = order.spec?.option;

  return (
    <>
      <p><Link href="/orders" className="muted">← {t("myOrders")}</Link></p>
      {error && <p className="error">{error}</p>}
      <div className="order-grid">
        <PromptView order={order} send={send} busy={busy} />

        <aside className="side-panel">
          <div className="product-card" style={{ minHeight: 180 }}>
            <div className="spread">
              <span className="label">{t("orderTitle")}</span>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img className="mark" src="/brand/mark-gold.png" alt="" />
            </div>
            <div>
              <div className="big">{productName(option, lang)}</div>
              <div className="label">{order.spec?.quantity ? `${order.spec.quantity} ${t("pieces")}` : order.status[lang]}</div>
            </div>
            <span className="label" dir="ltr" style={{ alignSelf: "flex-end" }}>{order.order_id}</span>
          </div>

          <div className="board board-ink cross">
            <TopoTexture />
            <div className="spread" style={{ marginBottom: 14 }}>
              <h2 style={{ margin: 0 }}>{t("journey")}</h2>
              <span className="muted small">{order.status[lang]}</span>
            </div>
            <JourneyTracker stage={order.stage} />
          </div>
        </aside>
      </div>
    </>
  );
}
