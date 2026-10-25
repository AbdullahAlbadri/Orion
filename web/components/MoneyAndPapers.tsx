"use client";

// Payments and documents share one sidebar entry with two tabs (docs/website/app/17-payments.md, 18-documents.md).
// Payments: no provider yet (TODO(decide)), so only what is true today is shown; card details are never handled here.
// Documents: every pre-receipt version and every uploaded file, kept and never overwritten.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { CardIcon, FileIcon, SearchIcon } from "./Icons";
import { Empty, PageHead, Tabs } from "./ui";
import { api, fileObjectUrl, type DocumentItem, type OrderRow } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { COMMON, formatDate, NAV, num, t } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import { orderName } from "@/lib/orders";

const C = {
  payments: t("المدفوعات", "Payments"), documents: t("المستندات", "Documents"),
  dueNow: t("مستحق الآن", "Due now"),
  noDue: t("لا مدفوعات مستحقة.", "Nothing to pay right now."),
  // TODO(decide): payment timing; say when payment happens only once it is decided
  howPay: t("تدفع لأوريون عبر صفحة دفع آمنة. لا نرى بيانات بطاقتك ولا نحفظها.",
    "You pay Orion on a secure hosted checkout page. We never see or store your card details."),
  payLater: t("الدفع الإلكتروني قيد الإعداد. سيتواصل معك فريقنا عند جاهزية عرض السعر.",
    "Online payment is being set up. Our team will contact you when your quote is ready."),
  pay: t("ادفع", "Pay"),
  history: t("سجل المدفوعات", "Payment history"),
  noHistory: t("لا مدفوعات بعد. تظهر هنا مع إيصال لكل دفعة.", "No payments yet. Each one appears here with its receipt."),
  searchPh: t("ابحث باسم المستند أو الطلب", "Search by document or order"),
  allOrders: t("كل الطلبات", "All orders"),
  allTypes: t("كل الأنواع", "All types"),
  typeReceipt: t("ملخصات الطلب", "Order summaries"), typeUpload: t("ملفاتك المرفوعة", "Your uploaded files"),
  orion: t("مستندات من أوريون", "From Orion"), yours: t("ملفات رفعتها", "Files you uploaded"),
  summaryV: t("ملخص الطلب · النسخة {v}", "Order summary · version {v}"),
  summaryReview: t("ملخص الطلب · بانتظار مراجعتك", "Order summary · needs your review"),
  confirmed: t("مؤكد", "Confirmed"), needsReview: t("بانتظار مراجعتك", "Needs your review"),
  view: t("عرض", "View"), download: t("تنزيل", "Download"),
  noDocs: t("لا مستندات بعد", "No documents yet"),
  noDocsText: t("تظهر هنا ملخصات طلباتك وكل ملف ترفعه. تُضاف عروض الأسعار والفواتير ومستندات الشحن عند توفرها.",
    "Your order summaries and every file you upload appear here. Quotes, invoices and shipping documents are added as they exist."),
  later: t("عروض الأسعار والفواتير ومستندات الشحن تُضاف هنا تلقائيًا عند إصدارها.",
    "Quotes, invoices and shipping documents are added here automatically when they are issued."),
};

export default function MoneyAndPapers({ tab }: { tab: "payments" | "documents" }) {
  const { lang } = useLang();
  const router = useRouter();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  return (
    <>
      <PageHead title={L(NAV.payments)} />
      <div className="toolbar">
        <Tabs value={tab} onChange={(k) => router.push(`/${k}`)} options={[
          { key: "payments", label: L(C.payments) }, { key: "documents", label: L(C.documents) },
        ]} />
      </div>
      {tab === "payments" ? <Payments /> : <Documents />}
    </>
  );
}

function Payments() {
  const user = useRequireUser();
  const { lang } = useLang();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [orders, setOrders] = useState<OrderRow[] | null>(null);
  useEffect(() => { if (user) api<OrderRow[]>("/orders").then(setOrders).catch(() => setOrders([])); }, [user]);
  const due = (orders ?? []).filter((o) => o.stage === "awaiting_payment");
  return (
    <>
      <p className="note">{L(C.howPay)}</p>
      <section className="section-gap">
        <h2>{L(C.dueNow)}</h2>
        {orders === null ? <p className="muted">{L(COMMON.loading)}</p> : due.length === 0 ? <p className="muted">{L(C.noDue)}</p> : (
          <div className="attention">
            {due.map((o) => (
              <div key={o.id} className="attention-item">
                <span className="dot" aria-hidden />
                <div className="grow stack-sm"><strong>{orderName(o, lang)}</strong><span className="mono">{o.id}</span></div>
                <button type="button" className="btn btn-sm" disabled title={L(C.payLater)}>{L(C.pay)}</button>
              </div>
            ))}
            <p className="muted small">{L(C.payLater)}</p>
          </div>
        )}
      </section>
      <section className="section-gap">
        <h2>{L(C.history)}</h2>
        <Empty icon={<CardIcon />} title={L(C.noHistory)} />
      </section>
    </>
  );
}

function Documents() {
  const user = useRequireUser();
  const { lang } = useLang();
  const { calendar } = useMe();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [docs, setDocs] = useState<DocumentItem[] | null>(null);
  const [error, setError] = useState(false);
  const [q, setQ] = useState("");
  const [order, setOrder] = useState("");
  const [type, setType] = useState("");

  useEffect(() => { if (user) api<DocumentItem[]>("/orders/documents").then(setDocs).catch(() => setError(true)); }, [user]);

  const title = (d: DocumentItem) => d.kind === "upload" ? d.name
    : d.status === "needs_review" ? L(C.summaryReview) : L(C.summaryV).replace("{v}", num(d.version ?? 1));
  const product = (d: DocumentItem) => orderName({ title: d.kind === "pre_receipt" ? d.title : null, option: d.option }, lang);

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (docs ?? []).filter((d) => (!order || d.order_id === order) && (!type || d.kind === type)
      && (!needle || `${title(d)} ${product(d)} ${d.order_id}`.toLowerCase().includes(needle)));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs, q, order, type, lang]);

  if (!docs) return <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>;
  if (docs.length === 0) return <Empty icon={<FileIcon />} title={L(C.noDocs)} text={L(C.noDocsText)} />;

  const orders = Array.from(new Set(docs.map((d) => d.order_id)));
  const ours = shown.filter((d) => d.kind === "pre_receipt");
  const theirs = shown.filter((d) => d.kind === "upload");

  async function openFile(d: Extract<DocumentItem, { kind: "upload" }>, download: boolean) {
    const url = await fileObjectUrl(d.order_id, d.file_id);
    if (!download) { window.open(url, "_blank", "noopener"); return; }
    const a = document.createElement("a");
    a.href = url;
    a.download = d.name;
    a.click();
  }

  return (
    <>
      <div className="toolbar">
        <label className="search">
          <SearchIcon width={18} height={18} />
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={L(C.searchPh)} aria-label={L(COMMON.search)} />
        </label>
        <select value={order} onChange={(e) => setOrder(e.target.value)}>
          <option value="">{L(C.allOrders)}</option>
          {orders.map((id) => <option key={id} value={id}>{id}</option>)}
        </select>
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">{L(C.allTypes)}</option>
          <option value="pre_receipt">{L(C.typeReceipt)}</option>
          <option value="upload">{L(C.typeUpload)}</option>
        </select>
      </div>

      <section>
        <h2>{L(C.orion)}</h2>
        {ours.length === 0 ? <p className="muted">—</p> : (
          <div className="attention">
            {ours.map((d, i) => d.kind === "pre_receipt" && (
              <div key={`${d.order_id}-${d.version}-${i}`} className="link-card">
                <FileIcon />
                <div className="stack-sm grow">
                  <strong className="ellipsis">{title(d)}</strong>
                  <span className="muted small ellipsis">{product(d)} · <span className="mono">{d.order_id}</span></span>
                </div>
                <span className={`st ${d.status === "confirmed" ? "st-done" : "st-you"}`}>
                  {d.status === "confirmed" ? L(C.confirmed) : L(C.needsReview)}
                </span>
                <Link className="btn-outline" href={d.status === "needs_review" ? `/orders/${d.order_id}`
                  : `/documents/receipt?order=${encodeURIComponent(d.order_id)}&v=${d.version}`}>{L(C.view)}</Link>
              </div>
            ))}
          </div>
        )}
        <p className="muted small" style={{ marginTop: 10 }}>{L(C.later)}</p>
      </section>

      <section className="section-gap">
        <h2>{L(C.yours)}</h2>
        {theirs.length === 0 ? <p className="muted">—</p> : (
          <div className="attention">
            {theirs.map((d) => d.kind === "upload" && (
              <div key={d.file_id} className="link-card">
                <FileIcon />
                <div className="stack-sm grow">
                  <strong className="ellipsis">{d.name}</strong>
                  <span className="muted small ellipsis">{product(d)} · {formatDate(d.created_at, lang, calendar)} · {num(Math.ceil(d.size / 1024))} KB</span>
                </div>
                <button type="button" className="btn-outline" onClick={() => openFile(d, false)}>{L(C.view)}</button>
                <button type="button" className="link-btn" onClick={() => openFile(d, true)}>{L(C.download)}</button>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
