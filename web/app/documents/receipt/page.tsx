"use client";

// One confirmed order summary, rebuilt from that frozen version, to read or print ("Save as PDF").
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { PrinterIcon } from "@/components/Icons";
import Receipt from "@/components/Receipt";
import { PageHead } from "@/components/ui";
import { api, type Summary } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { COMMON, NAV, num, t } from "@/lib/copy";
import { useLang } from "@/lib/i18n";

const C = {
  title: t("ملخص الطلب · النسخة {v}", "Order summary · version {v}"),
  print: t("طباعة أو حفظ PDF", "Print or save as PDF"),
  order: t("الطلب", "Order"),
};

function ReceiptView() {
  const user = useRequireUser();
  const params = useSearchParams();
  const { lang } = useLang();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const order = params.get("order") ?? "";
  const version = params.get("v");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!user || !order) return;
    const v = version ? `&version=${encodeURIComponent(version)}` : "";
    api<Summary>(`/orders/${encodeURIComponent(order)}/receipt?lang=${lang}${v}`).then(setSummary).catch(() => setError(true));
  }, [user, order, version, lang]);

  if (!user || !summary) return <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>;
  return (
    <>
      <p className="no-print"><Link href="/documents" className="muted">← {L(NAV.payments)}</Link></p>
      <PageHead title={L(C.title).replace("{v}", num(Number(version ?? 1)))}
        sub={`${L(C.order)} ${order}`}
        actions={<button type="button" className="btn-ghost no-print" onClick={() => window.print()}>
          <PrinterIcon width={18} height={18} /> {L(C.print)}</button>} />
      <Receipt summary={summary} orderId={order} />
    </>
  );
}

export default function ReceiptPage() {
  return <Suspense><ReceiptView /></Suspense>;
}
