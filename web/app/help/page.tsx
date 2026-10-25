"use client";

// Help and support (docs/website/app/21-help.md): reach a person, with the order's context attached.
// People answer every request; no AI replies here, and price or change questions get no promise (rule 1).
// TODO(decide): WhatsApp/email contact and support hours; attachments on requests.
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { HelpIcon, SendIcon } from "@/components/Icons";
import { PageHead } from "@/components/ui";
import { api, ApiError, type OrderRow, type SupportRequest, type SupportTopic } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { ago, COMMON, NAV, num, t, type T } from "@/lib/copy";
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";
import { orderName } from "@/lib/orders";

const TOPICS: Record<SupportTopic, T> = {
  order: t("سؤال عن طلب", "A question about an order"),
  change: t("تعديل أو إلغاء", "A change or cancellation"),
  price: t("سؤال عن السعر أو العرض", "A price or quote question"),
  delivery: t("مشكلة في التوصيل أو البضاعة", "A delivery or goods problem"),
  account: t("الحساب", "My account"),
  other: t("أخرى", "Something else"),
};
const STATUS: Record<SupportRequest["status"], T> = {
  open: t("مفتوح · لدى فريقنا", "Open · with our team"),
  waiting_customer: t("بانتظار ردك", "Waiting for you"),
  resolved: t("تم الحل", "Resolved"),
};
const C = {
  sub: t("يرد عليك شخص من فريقنا، ومعه تفاصيل طلبك.", "A person from our team replies, with your order's details already attached."),
  newTitle: t("طلب جديد", "New request"),
  topic: t("الموضوع", "Topic"), order: t("الطلب", "Order"), noOrder: t("لا يتعلق بطلب", "Not about an order"),
  body: t("صف ما تحتاجه", "Describe what you need"),
  bodyPh: t("اكتب بالتفصيل، وسنرد هنا وفي صفحة الرسائل.", "Give us the details; we'll reply here and in Messages."),
  priceNote: t("أسئلة السعر والتعديل يراجعها فريقنا مباشرة. لا نعِد بشيء قبل المراجعة.",
    "Price and change questions go straight to our team for review. Nothing is promised before that."),
  send: t("إرسال", "Send"),
  sent: t("وصلنا طلبك رقم {ref}. سيرد فريقنا هنا.", "We got your request #{ref}. Our team will reply here."),
  mine: t("طلباتي", "My requests"),
  none: t("لا طلبات بعد.", "No requests yet."),
  reply: t("ردك", "Your reply"), you: t("أنت", "You"), team: t("فريق أوريون", "Orion team"),
  quick: t("أجوبة سريعة", "Quick answers"),
  tooMany: t("أرسلت طلبات كثيرة. حاول بعد قليل.", "You've sent a lot of requests. Please try again a bit later."),
};

function Help() {
  const user = useRequireUser();
  const params = useSearchParams();
  const router = useRouter();
  const { lang } = useLang();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [requests, setRequests] = useState<SupportRequest[] | null>(null);
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [open, setOpen] = useState<SupportRequest | null>(null);
  const [topic, setTopic] = useState<SupportTopic>((params.get("topic") as SupportTopic) || "order");
  const [order, setOrder] = useState(params.get("order") ?? "");
  const [body, setBody] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selectedId = params.get("request");

  const load = useCallback(async () => setRequests(await api<SupportRequest[]>("/support")), []);
  useEffect(() => {
    if (!user) return;
    load().catch(() => setError(L(COMMON.error)));
    api<OrderRow[]>("/orders").then(setOrders).catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, load]);
  useEffect(() => {
    if (!user || !selectedId) { setOpen(null); return; }
    api<SupportRequest>(`/support/${encodeURIComponent(selectedId)}`).then(setOpen).catch(() => setOpen(null));
  }, [user, selectedId]);

  const fail = (e: unknown) => setError(e instanceof ApiError && e.status === 429 ? L(C.tooMany) : L(COMMON.error));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true); setError(null);
    try {
      const r = await api<SupportRequest>("/support", { method: "POST", body: { topic, order_id: order || null, body } });
      setBody("");
      setNotice(L(C.sent).replace("{ref}", num(r.ref)));
      await load();
      router.replace(`/help?request=${r.id}`);
    } catch (err) { fail(err); } finally { setBusy(false); }
  }
  async function sendReply(e: React.FormEvent) {
    e.preventDefault();
    if (!open || !reply.trim()) return;
    setBusy(true); setError(null);
    try {
      setOpen(await api<SupportRequest>(`/support/${encodeURIComponent(open.id)}/messages`, { method: "POST", body: { body: reply } }));
      setReply("");
      await load();
    } catch (err) { fail(err); } finally { setBusy(false); }
  }

  if (!user) return null;
  return (
    <>
      <PageHead title={L(NAV.help)} sub={L(C.sub)} />
      {error && <p className="error">{error}</p>}
      {notice && <p className="saved-note">{notice}</p>}
      <div className="two-pane">
        <div className="stack">
          <form className="board board-glass stack" onSubmit={submit}>
            <h2 style={{ margin: 0 }}>{L(C.newTitle)}</h2>
            <div className="field">
              <label htmlFor="topic">{L(C.topic)}</label>
              <select id="topic" value={topic} onChange={(e) => setTopic(e.target.value as SupportTopic)}>
                {(Object.keys(TOPICS) as SupportTopic[]).map((k) => <option key={k} value={k}>{L(TOPICS[k])}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="order">{L(C.order)}</label>
              <select id="order" value={order} onChange={(e) => setOrder(e.target.value)}>
                <option value="">{L(C.noOrder)}</option>
                {orders.map((o) => <option key={o.id} value={o.id}>{orderName(o, lang)} · {o.id}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="body">{L(C.body)}</label>
              <textarea id="body" value={body} onChange={(e) => setBody(e.target.value)} placeholder={L(C.bodyPh)} maxLength={4000} required />
            </div>
            {(topic === "price" || topic === "change") && <p className="note" style={{ margin: 0 }}>{L(C.priceNote)}</p>}
            <button className="btn" disabled={busy || !body.trim()}><SendIcon width={18} height={18} /> {L(C.send)}</button>
          </form>

          <section>
            <h2>{L(C.mine)}</h2>
            {requests === null ? <p className="muted">{L(COMMON.loading)}</p> : requests.length === 0 ? <p className="muted">{L(C.none)}</p> : (
              <div className="pane-list">
                {requests.map((r) => (
                  <button key={r.id} type="button" className={`pane-item${selectedId === r.id ? " on" : ""}`}
                    onClick={() => router.replace(`/help?request=${r.id}`)}>
                    <span className="title">#{r.ref} · {L(TOPICS[r.topic])}</span>
                    <span className="muted small ellipsis">{r.last_author === "team" ? `${L(C.team)}: ` : ""}{r.last_message}</span>
                    <span className="row small"><span className={`st ${r.status === "waiting_customer" ? "st-you" : r.status === "resolved" ? "st-done" : "st-moving"}`}>
                      {L(STATUS[r.status])}</span><span className="muted">{ago(r.updated_at, lang)}</span></span>
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>

        <div className="stack">
          {open ? (
            <div className="board board-glass stack">
              <div className="spread">
                <h2 style={{ margin: 0 }}>#{open.ref} · {L(TOPICS[open.topic])}</h2>
                <span className={`st ${open.status === "waiting_customer" ? "st-you" : open.status === "resolved" ? "st-done" : "st-moving"}`}>{L(STATUS[open.status])}</span>
              </div>
              <div className="thread">
                {(open.messages ?? []).map((m, i) => (
                  <div key={i} className={`msg ${m.author}`}>
                    {m.body}
                    <span className="meta">{m.author === "team" ? L(C.team) : L(C.you)} · {ago(m.created_at, lang)}</span>
                  </div>
                ))}
              </div>
              <form className="composer" onSubmit={sendReply}>
                <textarea value={reply} onChange={(e) => setReply(e.target.value)} placeholder={L(C.reply)} maxLength={4000} aria-label={L(C.reply)} />
                <button className="btn" disabled={busy || !reply.trim()} aria-label={L(C.send)}><SendIcon width={18} height={18} /></button>
              </form>
            </div>
          ) : (
            <div className="board board-glass stack">
              <h2 style={{ margin: 0 }}><HelpIcon /> {L(C.quick)}</h2>
              <div className="faq">
                {HOME.faq.groups.flatMap((g) => g.items).map((f) => (
                  <details key={f.id} className="board board-glass" style={{ padding: 14 }}>
                    <summary>{L(f.q)}</summary>
                    <p className="muted" style={{ margin: "8px 0 0" }}>{L(f.a)}</p>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function HelpPage() {
  return <Suspense><Help /></Suspense>;
}
