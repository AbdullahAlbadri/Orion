"use client";

// My Products (docs/website/app/15-my-products.md): what the customer has made, to reorder without the questions.
// A product is saved when its first order's summary is confirmed.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { SearchIcon, ShirtIcon } from "@/components/Icons";
import { Empty, PageHead, ProductThumb, StatusChip, Tabs } from "@/components/ui";
import { api, type Product } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { COMMON, formatDate, NAV, num, t } from "@/lib/copy";
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import { chipTone, orderName } from "@/lib/orders";

const C = {
  sub: t("منتجاتك المحفوظة. أعد طلبها دون إعادة الأسئلة.", "Your saved products. Reorder them without answering the questions again."),
  current: t("الحالية", "Current"), archived: t("المؤرشفة", "Archived"),
  none: t("لا منتجات محفوظة بعد", "No saved products yet"),
  noneText: t("يُحفظ المنتج هنا عندما تؤكد ملخص أول طلب له.", "A product is saved here when you confirm the summary of its first order."),
  noArchived: t("لا منتجات مؤرشفة.", "No archived products."),
  lastOrdered: t("آخر طلب", "Last ordered"), lastQty: t("آخر كمية", "Last quantity"), orders: t("الطلبات", "Orders"),
  searchPh: t("ابحث باسم المنتج", "Search by product name"),
  allMarkets: t("كل المجالات", "All markets"),
};

export default function ProductsPage() {
  const user = useRequireUser();
  const { lang } = useLang();
  const { calendar } = useMe();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [tab, setTab] = useState<"current" | "archived">("current");
  const [products, setProducts] = useState<Product[] | null>(null);
  const [error, setError] = useState(false);
  const [q, setQ] = useState("");
  const [market, setMarket] = useState("");

  useEffect(() => {
    if (!user) return;
    setProducts(null);
    api<Product[]>(`/products${tab === "archived" ? "?archived=true" : ""}`).then(setProducts).catch(() => setError(true));
  }, [user, tab]);

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (products ?? []).filter((p) => (!market || p.market === market)
      && (!needle || orderName(p, "ar").toLowerCase().includes(needle) || orderName(p, "en").toLowerCase().includes(needle)));
  }, [products, q, market]);

  const markets = Array.from(new Set((products ?? []).map((p) => p.market)));

  return (
    <>
      <PageHead title={L(NAV.products)} sub={L(C.sub)} />
      <div className="toolbar">
        <Tabs value={tab} onChange={setTab} options={[{ key: "current", label: L(C.current) }, { key: "archived", label: L(C.archived) }]} />
        <label className="search">
          <SearchIcon width={18} height={18} />
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={L(C.searchPh)} aria-label={L(COMMON.search)} />
        </label>
        {markets.length > 1 && (
          <select value={market} onChange={(e) => setMarket(e.target.value)}>
            <option value="">{L(C.allMarkets)}</option>
            {markets.map((m) => <option key={m} value={m}>{HOME.markets.items.find((x) => x.id === m)?.name[lang] ?? m}</option>)}
          </select>
        )}
      </div>

      {!user || !products ? <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>
        : products.length === 0 ? (
          tab === "current"
            ? <Empty icon={<ShirtIcon />} title={L(C.none)} text={L(C.noneText)}
                action={<Link href="/orders/new" className="btn">{L(COMMON.startFirst)}</Link>} />
            : <p className="muted">{L(C.noArchived)}</p>
        ) : (
          <div className="card-grid">
            {shown.map((p) => (
              <Link key={p.id} href={`/products/${p.id}`} className="order-card">
                <div className="top">
                  <ProductThumb option={p.option} picture={p.picture} size={64} />
                  <div className="stack-sm">
                    <strong className="ellipsis">{orderName(p, lang)}</strong>
                    <span className="muted small">{HOME.markets.items.find((x) => x.id === p.market)?.name[lang]}</span>
                  </div>
                </div>
                <div className="spread small">
                  <span><span className="muted">{L(C.lastOrdered)}: </span>{formatDate(p.last_ordered_at, lang, calendar)}</span>
                  <span><span className="muted">{L(C.orders)}: </span>{num(p.orders)}</span>
                </div>
                <div className="spread small">
                  <span><span className="muted">{L(C.lastQty)}: </span>{p.last_quantity ? num(p.last_quantity) : "—"}</span>
                  <StatusChip status={p.status} tone={chipTone({ stage: p.latest_stage, waiting_on: null })} />
                </div>
              </Link>
            ))}
          </div>
        )}
    </>
  );
}
