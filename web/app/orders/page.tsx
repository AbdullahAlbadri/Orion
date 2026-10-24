"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { BoxIcon, ChatIcon, FactoryIcon, PlusIcon, ShirtIcon } from "@/components/Icons";
import ProgressRing from "@/components/ProgressRing";
import { api, type OrderRow } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { productName, useLang, type TextKey } from "@/lib/i18n";
import { bucket, journeyPercent, type Bucket } from "@/lib/journey";

const PILL: Record<Bucket, TextKey> = { you: "waitingForYou", factories: "withFactories", done: "stepDelivered" };

export default function Dashboard() {
  const user = useRequireUser();
  const { t, lang } = useLang();
  const [orders, setOrders] = useState<OrderRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) api<OrderRow[]>("/orders").then(setOrders).catch(() => setError(t("error")));
  }, [user, t]);

  if (!user || orders === null) return <p className={error ? "error" : "muted"}>{error ?? t("loading")}</p>;

  const counts = { active: 0, you: 0, factories: 0 };
  for (const o of orders) {
    const b = bucket(o.stage);
    if (b !== "done") counts.active += 1;
    if (b === "you") counts.you += 1;
    if (b === "factories") counts.factories += 1;
  }
  const latest = orders[0];
  const date = (iso: string) =>
    new Date(iso).toLocaleDateString(lang === "ar" ? "ar-SA" : "en-GB", { day: "numeric", month: "long" });

  return (
    <>
      <div className="section-title" style={{ marginTop: 8 }}><h2>{t("overview")}</h2></div>

      <div className="overview">
        {latest ? (
          <Link href={`/orders/${latest.id}`} className="product-card">
            <div className="spread">
              <span className="label">{t("latestOrder")}</span>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img className="mark" src="/brand/mark-gold.png" alt="" />
            </div>
            <div>
              <div className="big">{productName(latest.option, lang)}</div>
              <div className="label">{latest.quantity ? `${latest.quantity} ${t("pieces")}` : t("stepDescribe")}</div>
            </div>
            <div className="spread">
              <span className={`pill ${bucket(latest.stage)}`}>{t(PILL[bucket(latest.stage)])}</span>
              <span className="label">{date(latest.updated_at)}</span>
            </div>
          </Link>
        ) : (
          <Link href="/orders/new" className="product-card">
            <span className="label">{t("newOrder")}</span>
            <div className="big">{t("startHint")}</div>
            <span className="btn btn-sm" style={{ alignSelf: "flex-start" }}><PlusIcon width={18} height={18} /> {t("newOrder")}</span>
          </Link>
        )}

        <div className="card spread" style={{ alignItems: "center", justifyContent: "space-around" }}>
          <ProgressRing percent={latest ? journeyPercent(latest.stage) : 0} label={t("progress")} />
          <div className="stack" style={{ gap: 4 }}>
            <span className="muted small">{t("journey")}</span>
            <strong style={{ fontSize: 18 }}>{latest ? productName(latest.option, lang) : "—"}</strong>
          </div>
        </div>
      </div>

      <div className="grid-stats" style={{ marginTop: 16 }}>
        <Stat icon={<BoxIcon />} label={t("activeOrders")} value={counts.active} />
        <Stat icon={<ChatIcon />} label={t("waitingForYou")} value={counts.you} />
        <Stat icon={<FactoryIcon />} label={t("withFactories")} value={counts.factories} />
      </div>

      <div className="section-title" id="list"><h2>{t("myOrders")}</h2></div>
      <div className="card" style={{ padding: 10 }}>
        {orders.length === 0 ? (
          <p className="muted" style={{ padding: 14, margin: 0 }}>{t("noOrders")}</p>
        ) : (
          <div className="list">
            {orders.map((o) => (
              <Link key={o.id} href={`/orders/${o.id}`} className="list-row">
                <span className="avatar"><ShirtIcon /></span>
                <span className="cell-value">{productName(o.option, lang)}</span>
                <span className="hide-sm"><div className="cell-label">{t("date")}</div><div className="cell-value">{date(o.created_at)}</div></span>
                <span className="hide-sm"><div className="cell-label">{t("quantity")}</div><div className="cell-value">{o.quantity ?? "—"}</div></span>
                <span className="hide-sm"><span className={`pill ${bucket(o.stage)}`}>{t(PILL[bucket(o.stage)])}</span></span>
                <span className="btn-outline">{t("open")}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="card stat">
      <span className="icon">{icon}</span>
      <span className="muted">{label}</span>
      <span className="value">{value}</span>
    </div>
  );
}
