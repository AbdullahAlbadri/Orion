"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, type OrderRow, type OrderView } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

export default function OrdersPage() {
  const user = useRequireUser();
  const { t, lang } = useLang();
  const router = useRouter();
  const [orders, setOrders] = useState<OrderRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) api<OrderRow[]>("/orders").then(setOrders).catch(() => setError(t("error")));
  }, [user, t]);

  async function newOrder() {
    setBusy(true);
    try {
      const order = await api<OrderView>("/orders", { method: "POST" });
      router.push(`/orders/${order.order_id}`);
    } catch {
      setError(t("error"));
      setBusy(false);
    }
  }

  if (!user) return <p className="muted">{t("loading")}</p>;
  const date = (iso: string) => new Date(iso).toLocaleDateString(lang === "ar" ? "ar-SA" : "en-GB");

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>{t("myOrders")}</h1>
        <button className="btn" onClick={newOrder} disabled={busy}>{t("newOrder")}</button>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="card">
        {orders === null ? (
          <p className="muted">{t("loading")}</p>
        ) : orders.length === 0 ? (
          <p className="muted">{t("noOrders")}</p>
        ) : (
          <ul className="orders">
            {orders.map((o) => (
              <li key={o.id}>
                <Link href={`/orders/${o.id}`}>
                  {o.option ?? t("orderTitle")}{o.quantity ? ` · ${o.quantity} ${t("pieces")}` : ""}
                </Link>
                <span className="muted">{date(o.updated_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
