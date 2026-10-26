"use client";

// Orders (docs/website/app/11-orders.md): every order, what needs attention first, filters, search and sort.
// Totals and estimated arrival appear once quotes and shipments exist (no column until then).
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ArrowIcon, BoxIcon, PlaneIcon, SearchIcon } from "@/components/Icons";
import Planet from "@/components/Planet";
import { Empty, PageHead } from "@/components/ui";
import { api, type OrderRow } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { ago, COMMON, formatDate, NAV, t } from "@/lib/copy";
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import { ACTIONS, chipTone, groupOf, needsAction, orderName, type Group } from "@/lib/orders";

const C = {
  sub: t("كل طلباتك، وما يحتاجك في الأعلى.", "All your orders, with what needs you at the top."),
  attention: t("بحاجة لانتباهك", "Needs your attention"),
  active: t("جارية", "Active"), delivered: t("مُسلّمة", "Delivered"), closed: t("مغلقة", "Closed"), drafts: t("مسودات", "Drafts"),
  allMarkets: t("كل المجالات", "All markets"),
  searchPh: t("اسم المنتج أو رقم الطلب", "Product name or reference"),
  sortUpdated: t("الأحدث تحديثًا", "Last update"), sortCreated: t("تاريخ الإنشاء", "Date created"),
  from: t("من", "From"), to: t("إلى", "To"),
  product: t("المنتج", "Product"), reference: t("رقم الطلب", "Reference"), market: t("المجال", "Market"),
  status: t("الحالة", "Status"), updated: t("آخر تحديث", "Last update"), created: t("أُنشئ", "Created"),
  discard: t("حذف المسودة", "Discard draft"), discardSure: t("حذف هذه المسودة؟", "Discard this draft?"),
  keep: t("إبقاء", "Keep"), yes: t("حذف", "Discard"),
  none: t("لا طلبات هنا.", "No orders here."),
  noneText: t("صف ما تريد صنعه، ونتولى المصنع والشحن.", "Describe what you want to make, and we handle the factory and shipping."),
  noMatch: t("لا نتائج لهذا البحث.", "Nothing matches this search."),
  board: t("المغادرات", "Departures"),
};

type Filter = Group | "all";

export default function OrdersPage() {
  const user = useRequireUser();
  const { lang } = useLang();
  const { calendar } = useMe();
  const router = useRouter();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [orders, setOrders] = useState<OrderRow[] | null>(null);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");
  const [market, setMarket] = useState("");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<"updated" | "created">("updated");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    const load = () => api<OrderRow[]>("/orders").then(setOrders);
    load().catch(() => setError(true));
    const timer = setInterval(() => { if (!document.hidden) load().catch(() => {}); }, 60_000);
    return () => clearInterval(timer);
  }, [user]);

  const marketName = (id: string | null) => {
    const m = HOME.markets.items.find((x) => x.id === id);
    return m ? m.name[lang] : "—";
  };

  const counts = useMemo(() => {
    const c: Record<Filter, number> = { active: 0, delivered: 0, closed: 0, draft: 0, all: orders?.length ?? 0 };
    for (const o of orders ?? []) c[groupOf(o.stage)] += 1;
    return c;
  }, [orders]);

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (orders ?? [])
      .filter((o) => filter === "all" || groupOf(o.stage) === filter)
      .filter((o) => !market || o.market === market)
      .filter((o) => !from || o.created_at.slice(0, 10) >= from)
      .filter((o) => !to || o.created_at.slice(0, 10) <= to)
      .filter((o) => !needle || o.id.toLowerCase().includes(needle) || orderName(o, "ar").toLowerCase().includes(needle)
        || orderName(o, "en").toLowerCase().includes(needle))
      .sort((a, b) => (sort === "updated" ? b.updated_at.localeCompare(a.updated_at) : b.created_at.localeCompare(a.created_at)));
  }, [orders, filter, market, q, sort, from, to]);

  if (!user || !orders) return <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>;

  const attention = orders.filter(needsAction);
  const markets = Array.from(new Set(orders.map((o) => o.market).filter(Boolean))) as string[];

  async function discard(id: string) {
    try {
      await api(`/orders/${encodeURIComponent(id)}/discard`, { method: "POST" });
      setOrders((list) => (list ?? []).filter((o) => o.id !== id));
    } catch {
      setError(true);
    }
    setConfirming(null);
  }

  return (
    <>
      <PageHead title={L(NAV.orders)} sub={L(C.sub)} />

      {orders.length === 0 ? (
        <Empty icon={<BoxIcon />} title={L(C.none)} text={L(C.noneText)}
          action={<Link href="/orders/new" className="btn">{L(COMMON.startFirst)}</Link>} />
      ) : (
        <>
          {attention.length > 0 && (
            <section style={{ marginBottom: 24 }}>
              <h2>{L(C.attention)}</h2>
              <div className="attention">
                {attention.map((o) => (
                  <div key={o.id} className="attention-item">
                    <Planet option={o.option} size={36} />
                    <div className="grow stack-sm">
                      <strong className="ellipsis">{L(ACTIONS[o.stage].label)}</strong>
                      <span className="muted small ellipsis">{orderName(o, lang)} · <span className="mono">{o.id}</span></span>
                    </div>
                    <Link href={`/orders/${o.id}`} className="btn btn-sm">{L(ACTIONS[o.stage].button)}</Link>
                  </div>
                ))}
              </div>
            </section>
          )}

          <div className="dep-board">
            <div className="dep-head">
              <span className="dep-title"><PlaneIcon className="flip-forward" width={24} height={24} /> {L(C.board)}</span>
              <span className="dep-route" dir="ltr">CN → KSA</span>
            </div>
            {/* the filters live on the board: status as flap tiles, then search, dates and order */}
            <div className="dep-filters">
              <div className="dep-tabs" role="tablist" aria-label={L(C.status)}>
                {([["active", C.active], ["delivered", C.delivered], ["closed", C.closed], ["draft", C.drafts],
                  ["all", COMMON.all]] as const).map(([key, label]) => (
                  <button key={key} type="button" role="tab" aria-selected={filter === key}
                    className={`flap dep-tab${filter === key ? " on" : ""}`} onClick={() => setFilter(key)}>
                    {L(label)} <b>{counts[key]}</b>
                  </button>
                ))}
              </div>
              <div className="dep-tools">
                <label className="dep-search">
                  <SearchIcon width={16} height={16} />
                  <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={L(C.searchPh)} aria-label={L(COMMON.search)} />
                </label>
                {markets.length > 1 && (
                  <select value={market} onChange={(e) => setMarket(e.target.value)} aria-label={L(C.market)}>
                    <option value="">{L(C.allMarkets)}</option>
                    {markets.map((m) => <option key={m} value={m}>{marketName(m)}</option>)}
                  </select>
                )}
                <label className="dep-date">{L(C.from)} <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
                <label className="dep-date">{L(C.to)} <input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></label>
                <select value={sort} onChange={(e) => setSort(e.target.value as "updated" | "created")} aria-label="sort">
                  <option value="updated">{L(C.sortUpdated)}</option>
                  <option value="created">{L(C.sortCreated)}</option>
                </select>
              </div>
            </div>
            {shown.length === 0 ? <p className="muted dep-empty">{L(C.noMatch)}</p> : (<>
              <div className="dep-cols" aria-hidden>
                <span>{L(C.reference)}</span><span>{L(C.product)}</span><span>{L(C.updated)}</span><span>{L(C.status)}</span><span /><span />
              </div>
              {shown.map((o, i) => {
                const group = groupOf(o.stage);
                const tone = chipTone(o);
                return (
                  <div key={o.id} className="dep-row" style={{ ["--i" as string]: i }} onClick={() => router.push(`/orders/${o.id}`)}>
                    <span className="flap dep-code">{o.id}</span>
                    <span className="dep-product">
                      <Planet option={o.option} size={38} />
                      <span className="stack-sm"><strong className="ellipsis">{orderName(o, lang)}</strong><small>{marketName(o.market)}</small></span>
                    </span>
                    <span className="dep-place" title={formatDate(o.updated_at, lang, calendar, true)}>{ago(o.updated_at, lang)}</span>
                    <span className={`flap dep-status ${tone}`}>{tone === "you" && <i className="dep-blink" />}{o.status[lang]}</span>
                    <span className="dep-actions" onClick={(e) => e.stopPropagation()}>
                      {group === "draft" && o.stage === "draft" && (confirming === o.id ? (
                        <>
                          <span className="muted small">{L(C.discardSure)}</span>
                          <button type="button" className="btn btn-sm" onClick={() => discard(o.id)}>{L(C.yes)}</button>
                          <button type="button" className="btn-ghost btn-sm" onClick={() => setConfirming(null)}>{L(C.keep)}</button>
                        </>
                      ) : (
                        <button type="button" className="link-btn" onClick={() => setConfirming(o.id)}>{L(C.discard)}</button>
                      ))}
                      {group === "delivered" && o.product_id && (
                        <Link href={`/products/${o.product_id}`} className="btn-outline">{L(COMMON.reorder)}</Link>
                      )}
                      <Link href={`/orders/${o.id}`} className="btn-outline">
                        {group === "draft" ? L(COMMON.continueDraft) : L(COMMON.open)}
                      </Link>
                    </span>
                    <ArrowIcon className="dep-more flip-forward" width={18} height={18} />
                  </div>
                );
              })}
            </>)}
          </div>
        </>
      )}
    </>
  );
}
