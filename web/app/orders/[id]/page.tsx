"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import PromptView from "@/components/PromptView";
import { api, ApiError, type OrderView } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

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
      setOrder(await api<OrderView>(`/orders/${encodeURIComponent(id)}/reply`, { method: "POST", body: { reply } }));
    } catch (e) {
      setError(e instanceof ApiError && e.status === 409 ? null : t("error"));
      await load().catch(() => {});
    } finally {
      setBusy(false);
    }
  }, [id, load, t]);

  if (!user || !order) return <p className="muted">{error ?? t("loading")}</p>;

  return (
    <>
      <p><Link href="/orders">← {t("myOrders")}</Link></p>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
        <h1 style={{ margin: 0 }}>{t("orderTitle")}</h1>
        <span className="badge">{order.status[lang]}</span>
      </div>
      {error && <p className="error">{error}</p>}
      <PromptView order={order} send={send} busy={busy} />
    </>
  );
}
