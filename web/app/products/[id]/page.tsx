"use client";

// One product (docs/website/app/15-my-products.md): its confirmed specification, files, notes, order history,
// reorder and archive. Reorder pre-fills every answer; the customer can change any of them (a changed order is
// a new version) and confirms a new summary. TODO(decide): which steps a reorder may skip.
// Landed cost and the margin calculator wait for payments (no cost data exists yet).
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FileThumb } from "@/components/FileUpload";
import { ArchiveIcon, ReplayIcon } from "@/components/Icons";
import Receipt from "@/components/Receipt";
import { PageHead, ProductThumb, StatusChip } from "@/components/ui";
import { api, type OrderView, type ProductDetail } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { COMMON, formatDate, NAV, num, t } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import { chipTone, orderName } from "@/lib/orders";

const C = {
  reorder: t("أعد الطلب", "Reorder"),
  reorderNote: t("نبدأ طلبًا جديدًا بنفس الإجابات والملفات. تختار الكمية وتعدّل ما تريد، ثم تؤكد ملخصًا جديدًا.",
    "We start a new order with the same answers and files. You pick the quantity, change anything you like, then confirm a new summary."),
  archive: t("أرشفة", "Archive"), unarchive: t("إلغاء الأرشفة", "Unarchive"),
  spec: t("المواصفات المؤكدة", "Confirmed specification"),
  files: t("الصور والملفات", "Pictures and files"),
  notes: t("ملاحظاتك", "Your notes"),
  notesPh: t("ملاحظات لنفسك عن هذا المنتج (لا يراها المصنع)", "Notes for yourself about this product (the factory doesn't see them)"),
  history: t("سجل الطلبات", "Order history"),
  date: t("التاريخ", "Date"), qty: t("الكمية", "Quantity"), status: t("الحالة", "Status"),
  version: t("نسخ الملخص", "Summary versions"), checks: t("فروقات اكتشفناها", "Differences caught"),
  delivered: t("التسليم", "Delivered"),
  margin: t("حاسبة الربح", "Margin calculator"),
  marginLater: t("تظهر بعد أول طلب مُسلّم بتكلفة نهائية: تُدخل سعر البيع ونحسب ربحك لكل قطعة.",
    "Appears after your first delivered order with a final cost: enter your selling price and we work out your margin per piece."),
};

export default function ProductPage() {
  const user = useRequireUser();
  const { id } = useParams<{ id: string }>();
  const { lang } = useLang();
  const { calendar } = useMe();
  const router = useRouter();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [p, setP] = useState<ProductDetail | null>(null);
  const [error, setError] = useState(false);
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    api<ProductDetail>(`/products/${encodeURIComponent(id)}?lang=${lang}`).then((d) => { setP(d); setNotes(d.notes ?? ""); })
      .catch(() => setError(true));
  }, [user, id, lang]);

  if (!user || !p) return <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>;

  async function reorder() {
    setBusy(true);
    try {
      const order = await api<OrderView>(`/products/${encodeURIComponent(id)}/reorder`, { method: "POST" });
      router.push(`/orders/${order.order_id}`);
    } catch {
      setError(true);
      setBusy(false);
    }
  }
  async function save(fields: { notes?: string; archived?: boolean }) {
    await api(`/products/${encodeURIComponent(id)}`, { method: "PUT", body: fields });
    if (fields.archived !== undefined) setP({ ...p!, archived_at: fields.archived ? new Date().toISOString() : null });
    if (fields.notes !== undefined) { setSaved(true); setTimeout(() => setSaved(false), 2000); }
  }

  return (
    <>
      <p><Link href="/products" className="muted">← {L(NAV.products)}</Link></p>
      <div className="row" style={{ gap: 16, alignItems: "center" }}>
        <ProductThumb option={p.option} picture={p.picture} size={72} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <PageHead title={orderName(p, lang)} actions={<>
            <button type="button" className="btn" onClick={reorder} disabled={busy}><ReplayIcon width={18} height={18} /> {L(C.reorder)}</button>
            <button type="button" className="btn-ghost" onClick={() => save({ archived: !p.archived_at })}>
              <ArchiveIcon width={18} height={18} /> {p.archived_at ? L(C.unarchive) : L(C.archive)}
            </button>
          </>} />
        </div>
      </div>
      <p className="note">{L(C.reorderNote)}</p>

      <section className="section-gap">
        <h2>{L(C.history)}</h2>
        <table className="table">
          <thead><tr><th>{L(C.date)}</th><th>{L(C.qty)}</th><th>{L(C.status)}</th><th>{L(C.version)}</th><th>{L(C.checks)}</th><th>{L(C.delivered)}</th></tr></thead>
          <tbody>
            {p.history.map((h) => (
              <tr key={h.id} className="click" onClick={() => router.push(`/orders/${h.id}`)}>
                <td data-label={L(C.date)}>{formatDate(h.created_at, lang, calendar)}</td>
                <td data-label={L(C.qty)}>{h.quantity ? num(h.quantity) : "—"}</td>
                <td data-label={L(C.status)}><StatusChip status={h.status} tone={chipTone({ stage: h.stage, waiting_on: null })} /></td>
                <td data-label={L(C.version)}>{num(h.revisions + 1)}</td>
                <td data-label={L(C.checks)}>{num(h.mismatches_caught)}</td>
                <td data-label={L(C.delivered)}>{formatDate(h.delivered_at, lang, calendar)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="section-gap">
        <h2>{L(C.notes)}</h2>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={L(C.notesPh)} maxLength={2000} />
        <div className="form-actions">
          <button type="button" className="btn btn-sm" onClick={() => save({ notes })}>{L(COMMON.save)}</button>
          {saved && <span className="saved-note">{L(COMMON.saved)}</span>}
        </div>
      </section>

      {p.files.length > 0 && (
        <section className="section-gap">
          <h2>{L(C.files)}</h2>
          <div className="row">
            {p.files.filter((f, i, all) => all.findIndex((x) => x.name === f.name) === i).map((f) => (
              <FileThumb key={f.id} orderId={f.order_id} file={{ file_id: f.id, name: f.name, content_type: f.content_type }} />
            ))}
          </div>
        </section>
      )}

      {p.summary && (
        <section className="section-gap">
          <h2>{L(C.spec)}</h2>
          <Receipt summary={p.summary} orderId={p.latest_order_id} />
        </section>
      )}

      <section className="section-gap">
        <h2>{L(C.margin)}</h2>
        <p className="note">{L(C.marginLater)}</p>
      </section>
    </>
  );
}
