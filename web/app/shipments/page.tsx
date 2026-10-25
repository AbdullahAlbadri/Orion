"use client";

// Shipments (docs/website/app/14-shipments.md). Orders appear here once they ship. Carrier, tracking number
// and the carrier's estimate arrive with the tracking provider (TODO(decide): provider); nothing is promised.
import Link from "next/link";
import { useEffect, useState } from "react";

import { TruckIcon } from "@/components/Icons";
import { Empty, PageHead, ProductThumb, StatusChip, Tabs } from "@/components/ui";
import { api, type OrderRow } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { ago, COMMON, NAV, t } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { chipTone, IN_TRANSIT, orderName } from "@/lib/orders";

const C = {
  sub: t("كل ما هو في الطريق إليك.", "Everything on its way to you."),
  inTransit: t("في الطريق", "In transit"), delivered: t("مُسلّمة", "Delivered"),
  none: t("لا شحنات بعد", "No shipments yet"),
  noneText: t("تظهر طلباتك هنا عند شحنها من المصنع، مع حالة الشحنة وآخر تحديث.",
    "Your orders appear here once they ship from the factory, with the shipment status and latest update."),
  tracking: t("رقم التتبع وشركة الشحن يظهران هنا عند ربط مزود التتبع. أي تاريخ وصول يكون تقديرًا من شركة الشحن.",
    "The tracking number and carrier appear here once tracking is connected. Any arrival date is the carrier's estimate."),
  address: t("عنوان التسليم", "Delivery address"),
  addressNote: t("تغيير عنوان شحنة جارية يحتاج تأكيد فريقنا.", "Changing the address of a live shipment needs our team's confirmation."),
  problem: t("أبلغ عن مشكلة", "Report a problem"),
  updated: t("آخر تحديث", "Last update"),
};

type Tab = "transit" | "delivered" | "all";

export default function ShipmentsPage() {
  const user = useRequireUser();
  const { lang } = useLang();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [orders, setOrders] = useState<OrderRow[] | null>(null);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState<Tab>("transit");

  useEffect(() => {
    if (user) api<OrderRow[]>("/orders").then(setOrders).catch(() => setError(true));
  }, [user]);

  if (!user || !orders) return <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>;

  const transit = orders.filter((o) => IN_TRANSIT.includes(o.stage));
  const delivered = orders.filter((o) => ["delivered", "completed"].includes(o.stage));
  const shown = tab === "transit" ? transit : tab === "delivered" ? delivered : [...transit, ...delivered];

  return (
    <>
      <PageHead title={L(NAV.shipments)} sub={L(C.sub)} />
      <div className="toolbar">
        <Tabs<Tab> value={tab} onChange={setTab} options={[
          { key: "transit", label: L(C.inTransit), count: transit.length },
          { key: "delivered", label: L(C.delivered), count: delivered.length },
          { key: "all", label: L(COMMON.all), count: transit.length + delivered.length },
        ]} />
      </div>
      {shown.length === 0 ? (
        <Empty icon={<TruckIcon />} title={L(C.none)} text={L(C.noneText)} />
      ) : (
        <div className="attention">
          {shown.map((o) => (
            <div key={o.id} className="link-card">
              <ProductThumb option={o.option} size={48} />
              <div className="stack-sm grow">
                <Link href={`/orders/${o.id}`} style={{ color: "var(--text)", fontWeight: 600 }}>{orderName(o, lang)}</Link>
                <span className="mono">{o.id}</span>
              </div>
              <StatusChip status={o.status} tone={chipTone(o)} />
              <span className="muted small hide-phone">{L(C.updated)} {ago(o.updated_at, lang)}</span>
              <Link href={`/help?order=${o.id}&topic=delivery`} className="link-btn">{L(C.problem)}</Link>
            </div>
          ))}
        </div>
      )}
      <p className="note section-gap">{L(C.tracking)} {L(C.addressNote)}</p>
    </>
  );
}
