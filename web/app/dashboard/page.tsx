"use client";

// Overview (docs/website/app/10-overview.md): what needs the customer, what is moving, how they are doing.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ArrowIcon, BellIcon, BuildingIcon, TruckIcon } from "@/components/Icons";
import { PageHead, ProductThumb, StatusChip } from "@/components/ui";
import {
  api, type BusinessView, type FullStats, type Notification, type OrderRow, type OrderView, type Product, type SupportRequest,
} from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { ago, COMMON, duration, NAV, num, t } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import { ACTIONS, chipTone, groupOf, IN_TRANSIT, needsAction, orderName } from "@/lib/orders";

const C = {
  attention: t("بحاجة لانتباهك", "Needs your attention"),
  teamQuestion: t("فريق أوريون ينتظر ردك", "The Orion team is waiting for your reply"),
  reply: t("رد", "Reply"),
  active: t("طلبات جارية", "Active orders"),
  inTransit: t("في الطريق", "In transit"),
  track: t("الشحنات", "Shipments"),
  stats: t("نظرة سريعة", "At a glance"),
  allStats: t("كل الإحصاءات", "All stats"),
  activeCount: t("طلبات جارية", "Active orders"),
  delivered: t("طلبات مُسلّمة", "Orders delivered"),
  avgDelivery: t("متوسط المدة من التأكيد إلى التسليم", "Average confirmation to delivery"),
  reorder: t("اطلب مرة أخرى", "Order again"),
  updates: t("آخر التحديثات", "Latest updates"),
  allUpdates: t("كل الرسائل", "All messages"),
  missing: t("{n} تفاصيل ناقصة في ملف نشاطك التجاري", "{n} details missing in your business profile"),
  missingHint: t("نحتاجها قبل أول شحنة. تستغرق دقيقة.", "We need them before your first shipment. It takes a minute."),
  complete: t("أكمل الملف", "Complete profile"),
  welcome: t("ابدأ طلبك الأول", "Start your first order"),
  welcomeText: t("ثلاث خطوات بسيطة، ونتولى الباقي.", "Three simple steps, and we handle the rest."),
  step1: t("صف منتجك وارفع شعارك أو صورك.", "Describe your product and upload your logo or pictures."),
  step2: t("راجع ملخصًا واضحًا وأكّده.", "Review a clear summary and confirm it."),
  step3: t("نتواصل مع المصانع ونرسل لك عرض السعر.", "We contact factories and send you the quote."),
  noActive: t("لا طلبات جارية الآن.", "No active orders right now."),
  updated: t("آخر تحديث", "Updated"),
};

type Data = {
  orders: OrderRow[]; business: BusinessView | null; support: SupportRequest[]; updates: Notification[];
  products: Product[]; stats: FullStats | null;
};

export default function Overview() {
  const user = useRequireUser();
  const { lang } = useLang();
  const { me } = useMe();
  const router = useRouter();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    const soft = <X,>(p: Promise<X>, fallback: X) => p.catch(() => fallback);
    const [orders, business, support, notes, products, stats] = await Promise.all([
      api<OrderRow[]>("/orders"),
      soft(api<BusinessView>("/business"), null),
      soft(api<SupportRequest[]>("/support"), []),
      soft(api<{ items: Notification[] }>("/notifications"), { items: [] }),
      soft(api<Product[]>("/products"), []),
      soft(api<FullStats>("/orders/stats"), null),
    ]);
    setData({ orders, business, support, updates: notes.items.slice(0, 3), products, stats });
  }, []);

  useEffect(() => {
    if (!user) return;
    load().catch(() => setError(true));
    const timer = setInterval(() => { if (!document.hidden) load().catch(() => {}); }, 60_000);
    return () => clearInterval(timer);
  }, [user, load]);

  if (!user || !data) return <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>;

  const { orders, business, support, updates, products, stats } = data;
  const attention = orders.filter(needsAction);
  const waitingTeam = support.filter((s) => s.status === "waiting_customer");
  const active = orders.filter((o) => groupOf(o.stage) === "active");
  const moving = active.filter((o) => IN_TRANSIT.includes(o.stage));
  const delivered = orders.filter((o) => groupOf(o.stage) === "delivered").length;
  const missing = business ? business.completeness.total - business.completeness.done : 0;
  const isNew = orders.length === 0;

  async function reorder(productId: string) {
    setBusy(productId);
    try {
      const order = await api<OrderView>(`/products/${encodeURIComponent(productId)}/reorder`, { method: "POST" });
      router.push(`/orders/${order.order_id}`);
    } catch {
      setError(true);
      setBusy(null);
    }
  }

  return (
    <>
      <PageHead title={`${L(NAV.hello)}${me?.name ? ` ${me.name}` : ""}`} />

      {(attention.length > 0 || waitingTeam.length > 0) && (
        <section aria-labelledby="attention">
          <h2 id="attention">{L(C.attention)}</h2>
          <div className="attention">
            {attention.map((o) => (
              <div key={o.id} className="attention-item">
                <span className="dot" aria-hidden />
                <ProductThumb option={o.option} size={40} />
                <div className="grow stack-sm">
                  <strong className="ellipsis">{L(ACTIONS[o.stage].label)}</strong>
                  <span className="muted small ellipsis">{orderName(o, lang)}</span>
                </div>
                <Link href={`/orders/${o.id}`} className="btn btn-sm">{L(ACTIONS[o.stage].button)}</Link>
              </div>
            ))}
            {waitingTeam.map((s) => (
              <div key={s.id} className="attention-item">
                <span className="dot" aria-hidden />
                <div className="grow stack-sm">
                  <strong>{L(C.teamQuestion)}</strong>
                  <span className="muted small ellipsis">#{s.ref} · {s.last_message}</span>
                </div>
                <Link href={`/help?request=${s.id}`} className="btn btn-sm">{L(C.reply)}</Link>
              </div>
            ))}
          </div>
        </section>
      )}

      {isNew ? (
        <section className="board board-ink cross welcome-card section-gap">
          <div className="stack">
            <h2 style={{ margin: 0, fontSize: 26 }}>{L(C.welcome)}</h2>
            <p className="muted" style={{ margin: 0 }}>{L(C.welcomeText)}</p>
            <Link href="/orders/new" className="btn" style={{ alignSelf: "flex-start" }}>{L(C.welcome)}</Link>
          </div>
          <ol className="welcome-steps">
            {[C.step1, C.step2, C.step3].map((s, i) => <li key={i}><span className="n">{i + 1}</span><span>{L(s)}</span></li>)}
          </ol>
        </section>
      ) : (
        <section className="section-gap">
          <div className="section-title"><h2>{L(C.active)}</h2><Link href="/orders" className="small">{L(NAV.orders)}</Link></div>
          {active.length === 0 ? <p className="muted">{L(C.noActive)}</p> : (
            <div className="order-cards">
              {active.slice(0, 6).map((o) => (
                <Link key={o.id} href={`/orders/${o.id}`} className="order-card">
                  <div className="top">
                    <ProductThumb option={o.option} size={48} />
                    <div className="stack-sm">
                      <strong className="ellipsis">{orderName(o, lang)}</strong>
                      <span className="muted small">{o.quantity ? `${num(o.quantity)} ${L(COMMON.pieces)}` : ""}</span>
                    </div>
                  </div>
                  <div className="spread">
                    <StatusChip status={o.status} tone={chipTone(o)} />
                    <span className="muted small">{L(C.updated)} {ago(o.updated_at, lang)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}

      {moving.length > 0 && (
        <section className="section-gap">
          <div className="section-title"><h2>{L(C.inTransit)}</h2><Link href="/shipments" className="small">{L(C.track)}</Link></div>
          <div className="attention">
            {moving.map((o) => (
              <Link key={o.id} href="/shipments" className="link-card">
                <TruckIcon /><span className="grow">{orderName(o, lang)}</span><StatusChip status={o.status} tone={chipTone(o)} />
              </Link>
            ))}
          </div>
        </section>
      )}

      {!isNew && (
        <section className="section-gap">
          <div className="section-title"><h2>{L(C.stats)}</h2><Link href="/stats" className="small">{L(C.allStats)}</Link></div>
          <div className="tiles">
            <div className="tile"><span className="label">{L(C.activeCount)}</span><span className="value">{num(active.length)}</span></div>
            <div className="tile"><span className="label">{L(C.delivered)}</span><span className="value">{num(delivered)}</span></div>
            {stats?.time.order_to_delivery_hours != null && (
              <div className="tile"><span className="label">{L(C.avgDelivery)}</span>
                <span className="value">{duration(stats.time.order_to_delivery_hours, lang)}</span></div>
            )}
          </div>
        </section>
      )}

      {products.length > 0 && (
        <section className="section-gap">
          <div className="section-title"><h2>{L(C.reorder)}</h2><Link href="/products" className="small">{L(NAV.products)}</Link></div>
          <div className="card-grid">
            {products.slice(0, 3).map((p) => (
              <div key={p.id} className="link-card">
                <ProductThumb option={p.option} picture={p.picture} size={52} />
                <div className="stack-sm grow">
                  <Link href={`/products/${p.id}`} className="ellipsis" style={{ color: "var(--text)", fontWeight: 600 }}>{orderName(p, lang)}</Link>
                  <span className="muted small">{p.last_quantity ? `${num(p.last_quantity)} ${L(COMMON.pieces)}` : ""}</span>
                </div>
                <button type="button" className="btn-outline" disabled={busy === p.id} onClick={() => reorder(p.id)}>{L(COMMON.reorder)}</button>
              </div>
            ))}
          </div>
        </section>
      )}

      {updates.length > 0 && (
        <section className="section-gap">
          <div className="section-title"><h2>{L(C.updates)}</h2><Link href="/messages" className="small">{L(C.allUpdates)}</Link></div>
          <div className="attention">
            {updates.map((n) => (
              <Link key={n.id} href={n.href || "/messages"} className="link-card">
                <BellIcon />
                <div className="stack-sm grow">
                  <strong className="ellipsis">{lang === "ar" ? n.title_ar : n.title_en}</strong>
                  {(lang === "ar" ? n.body_ar : n.body_en) && <span className="muted small ellipsis">{lang === "ar" ? n.body_ar : n.body_en}</span>}
                </div>
                <span className="muted small">{ago(n.created_at, lang)}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {missing > 0 && (
        <section className="section-gap">
          <Link href="/business" className="link-card" style={{ borderColor: "rgba(254,183,47,.35)" }}>
            <BuildingIcon />
            <div className="stack-sm grow">
              <strong>{L(C.missing).replace("{n}", num(missing))}</strong>
              <span className="muted small">{L(C.missingHint)}</span>
            </div>
            <span className="btn-outline">{L(C.complete)} <ArrowIcon className="flip-forward" width={14} height={14} /></span>
          </Link>
        </section>
      )}

    </>
  );
}
