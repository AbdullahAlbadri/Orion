"use client";

// Messages and updates (docs/website/app/19-messages.md): one inbox for order updates and team replies.
// Replies to the team happen in the Help request thread; the order assistant stays on the order page.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { BellIcon, MailIcon } from "@/components/Icons";
import { Empty, PageHead, Tabs } from "@/components/ui";
import { api, type Notification, type OrderRow } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { ago, COMMON, formatDate, NAV, t } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import { orderName } from "@/lib/orders";

const C = {
  sub: t("كل ما يخبرك به أوريون، لكل طلباتك.", "Everything Orion tells you, across all your orders."),
  unread: t("غير مقروءة", "Unread"), updates: t("تحديثات الطلبات", "Order updates"), team: t("الفريق", "Team"),
  markAll: t("تعليم الكل كمقروء", "Mark all as read"),
  none: t("لا رسائل بعد", "No messages yet"),
  noneText: t("تصلك هنا تحديثات طلباتك وردود فريقنا.", "Updates on your orders and replies from our team arrive here."),
  pick: t("اختر رسالة لعرضها.", "Pick a message to read it."),
  general: t("عام", "General"),
  openOrder: t("فتح الطلب", "Open the order"),
  replyHelp: t("الرد على الفريق", "Reply to the team"),
  emailed: t("أُرسلت بالبريد أيضًا", "Also sent by email"),
};

type Filter = "all" | "unread" | "status" | "team";

export default function MessagesPage() {
  const user = useRequireUser();
  const { lang } = useLang();
  const { calendar, refreshUnread } = useMe();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [items, setItems] = useState<Notification[] | null>(null);
  const [orders, setOrders] = useState<Record<string, OrderRow>>({});
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    const load = () => Promise.all([
      api<{ items: Notification[] }>("/notifications"),
      api<OrderRow[]>("/orders").catch(() => [] as OrderRow[]),
    ]).then(([n, o]) => {
      setItems(n.items);
      setOrders(Object.fromEntries(o.map((r) => [r.id, r])));
    });
    load().catch(() => setError(true));
    const timer = setInterval(() => { if (!document.hidden) load().catch(() => {}); }, 60_000);
    return () => clearInterval(timer);
  }, [user]);

  const shown = useMemo(() => (items ?? []).filter((n) =>
    filter === "all" || (filter === "unread" ? !n.read_at : n.kind === filter)), [items, filter]);
  const groups = useMemo(() => {
    const map = new Map<string, Notification[]>();
    for (const n of shown) {
      const key = n.order_id ?? "";
      map.set(key, [...(map.get(key) ?? []), n]);
    }
    return Array.from(map.entries());
  }, [shown]);

  if (!user || !items) return <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>;

  const current = items.find((n) => n.id === selected) ?? null;
  const groupName = (orderId: string) => {
    if (!orderId) return L(C.general);
    const row = orders[orderId];
    return row ? `${orderName(row, lang)} · ${orderId}` : orderId;
  };

  async function select(n: Notification) {
    setSelected(n.id);
    if (!n.read_at) {
      setItems((list) => (list ?? []).map((x) => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x)));
      await api("/notifications/read", { method: "POST", body: { ids: [n.id] } }).catch(() => {});
      refreshUnread().catch(() => {});
    }
  }
  async function markAll() {
    await api("/notifications/read", { method: "POST", body: {} }).catch(() => {});
    setItems((list) => (list ?? []).map((x) => ({ ...x, read_at: x.read_at ?? new Date().toISOString() })));
    refreshUnread().catch(() => {});
  }

  const unreadCount = items.filter((n) => !n.read_at).length;
  return (
    <>
      <PageHead title={L(NAV.messages)} sub={L(C.sub)}
        actions={unreadCount > 0 ? <button type="button" className="btn-ghost btn-sm" onClick={markAll}>{L(C.markAll)}</button> : undefined} />
      {items.length === 0 ? <Empty icon={<BellIcon />} title={L(C.none)} text={L(C.noneText)} /> : (
        <>
          <div className="toolbar">
            <Tabs<Filter> value={filter} onChange={setFilter} options={[
              { key: "all", label: L(COMMON.all) }, { key: "unread", label: L(C.unread), count: unreadCount },
              { key: "status", label: L(C.updates) }, { key: "team", label: L(C.team) },
            ]} />
          </div>
          <div className="two-pane">
            <div className="pane-list">
              {groups.map(([orderId, list]) => (
                <div key={orderId || "general"}>
                  <div className="pane-group">{groupName(orderId)}</div>
                  {list.map((n) => (
                    <button key={n.id} type="button" onClick={() => select(n)}
                      className={`pane-item${n.read_at ? "" : " unread"}${selected === n.id ? " on" : ""}`}>
                      <span className="title">{lang === "ar" ? n.title_ar : n.title_en}</span>
                      <span className="muted small">{ago(n.created_at, lang)}</span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
            <div className="board board-glass">
              {!current ? <p className="muted" style={{ margin: 0 }}>{L(C.pick)}</p> : (
                <div className="stack">
                  <div>
                    <h2 style={{ margin: 0 }}>{lang === "ar" ? current.title_ar : current.title_en}</h2>
                    <span className="muted small">{formatDate(current.created_at, lang, calendar, true)}</span>
                    {current.emailed && <span className="muted small"> · <MailIcon width={14} height={14} /> {L(C.emailed)}</span>}
                  </div>
                  {(lang === "ar" ? current.body_ar : current.body_en) && (
                    <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{lang === "ar" ? current.body_ar : current.body_en}</p>
                  )}
                  <div className="row">
                    {current.kind === "team" && current.href && <Link href={current.href} className="btn btn-sm">{L(C.replyHelp)}</Link>}
                    {current.order_id && <Link href={`/orders/${current.order_id}`} className="btn-outline">{L(C.openOrder)}</Link>}
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
