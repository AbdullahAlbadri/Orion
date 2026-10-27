"use client";

import { useState } from "react";

import type { OrderView, Prompt } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { ArrowIcon, ShirtIcon } from "./Icons";
import Planet from "./Planet";
import QuoteCard from "./QuoteCard";
import Receipt from "./Receipt";
import SectionedForm from "./SectionedForm";

type Send = (reply: Record<string, unknown>) => Promise<void>;

export default function PromptView({ order, send, busy }: { order: OrderView; send: Send; busy: boolean }) {
  const { t, lang } = useLang();
  const prompt = order.prompt;

  if (order.waiting_on === "manufacturer" || !prompt) {
    const paying = order.waiting_on === "payment";
    return (
      <div className="card">
        <span className="pill factories">{order.status[lang]}</span>
        <h2 style={{ marginTop: 14 }}>{t(paying ? "paymentTitle" : "waitingTitle")}</h2>
        <p className="muted">{t(paying ? "paymentText" : "waitingText")}</p>
        {order.summary ? <div style={{ marginTop: 16 }}><Receipt summary={order.summary} orderId={order.order_id} /></div>
          : order.pre_receipt && <pre className="receipt">{order.pre_receipt}</pre>}
      </div>
    );
  }

  switch (prompt.kind) {
    case "choice":
      return <Choice prompt={prompt} send={send} busy={busy} />;
    case "form":
      return <SectionedForm key={`${prompt.step}:${prompt.questions.map((q) => q.id).join(",")}:${JSON.stringify(prompt.errors)}`} orderId={order.order_id} prompt={prompt} send={send} busy={busy} />;
    case "reorder":
      return <ReorderChoice prompt={prompt} send={send} busy={busy} orderId={order.order_id} />;
    case "confirm":
      return <Confirm prompt={prompt} send={send} busy={busy} orderId={order.order_id} />;
    case "quote":
      return <QuoteCard quote={prompt.quote} error={prompt.error} send={send} busy={busy} />;
    case "chat":
      return <LegacyMessage prompt={prompt} send={send} busy={busy} />;
    default:
      // Never show a blank page: something unexpected from the API
      return <div className="card"><p className="error">{t("error")}</p></div>;
  }
}

/** An order paused by an older version that asked one free-text question. Answering it moves the
    order on to the new question cards. */
function LegacyMessage({ prompt, send, busy }: { prompt: Extract<Prompt, { kind: "chat" }>; send: Send; busy: boolean }) {
  const { t } = useLang();
  const [text, setText] = useState("");
  return (
    <form className="card stack" onSubmit={(e) => { e.preventDefault(); if (text.trim()) send({ message: text.trim() }); }}>
      <div className="bubble orion" dir="auto">{prompt.message}</div>
      <textarea dir="auto" value={text} placeholder={t("typeMessage")} onChange={(e) => setText(e.target.value)} disabled={busy} />
      <button className="btn" disabled={busy || !text.trim()} style={{ alignSelf: "flex-start" }}>{busy ? t("thinking") : t("send")}</button>
    </form>
  );
}

/** The first two steps: the market, as rows of the departures board, then the product, as planets to tap. */
function Choice({ prompt, send, busy }: { prompt: Extract<Prompt, { kind: "choice" }>; send: Send; busy: boolean }) {
  const { lang } = useLang();
  const name = (o: { name: string; name_ar?: string | null }) => (lang === "ar" && o.name_ar ? o.name_ar : o.name);
  return (
    <div className="pick">
      <h2 className="pick-title" dir="auto">{lang === "ar" && prompt.prompt_ar ? prompt.prompt_ar : prompt.prompt}</h2>
      {prompt.error && <p className="error">{prompt.error}</p>}
      {prompt.step === "pick_option" ? (
        <div className="pick-planets">
          {prompt.options.map((o, i) => (
            <button key={o.id} type="button" className="pick-planet" style={{ ["--i" as string]: i }} disabled={busy}
              onClick={() => send({ choice: o.id })}>
              <Planet option={o.id} size={84} />
              <span className="pick-name">{name(o)}</span>
            </button>
          ))}
        </div>
      ) : (
        <div className="dep-board">
          {prompt.options.map((o, i) => (
            <button key={o.id} type="button" className="dep-row pick-row" style={{ ["--i" as string]: i }} disabled={busy}
              onClick={() => send({ choice: o.id })}>
              <span className="flap dep-code">MKT-{String(i + 1).padStart(2, "0")}</span>
              <span className="dep-product"><span className="pick-icon"><ShirtIcon width={20} height={20} /></span>
                <strong>{name(o)}</strong></span>
              <ArrowIcon className="dep-more flip-forward" width={18} height={18} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** A reorder: the earlier details as a summary, and three ways on. Nothing is asked again unless the customer wants to. */
function ReorderChoice({ prompt, send, busy, orderId }: {
  prompt: Extract<Prompt, { kind: "reorder" }>; send: Send; busy: boolean; orderId: string;
}) {
  const { lang } = useLang();
  const L = (ar: string, en: string) => (lang === "ar" ? ar : en);
  return (
    <div className="stack">
      <div>
        <h2 dir="auto" style={{ marginBottom: 4 }}>{lang === "ar" && prompt.prompt_ar ? prompt.prompt_ar : prompt.prompt}</h2>
        <p className="muted" style={{ margin: 0 }}>
          {L("نفس التفاصيل والملفات من طلبك السابق. اختر كيف تكمل:", "The same details and files as your earlier order. Choose how to continue:")}
        </p>
      </div>
      <Receipt summary={prompt.summary} orderId={orderId} />
      <div className="row">
        <button className="btn" disabled={busy} onClick={() => send({ mode: "same" })}>
          {busy ? "…" : L(`اطلب نفس الكمية${prompt.quantity ? ` (${prompt.quantity})` : ""}`, `Order the same${prompt.quantity ? ` (${prompt.quantity})` : ""}`)}
        </button>
        {prompt.can_change_quantity && (
          <button className="btn-ghost" disabled={busy} onClick={() => send({ mode: "quantity" })}>
            {L("غيّر الكمية فقط", "Change the quantity only")}
          </button>
        )}
        <button className="btn-ghost" disabled={busy} onClick={() => send({ mode: "edit" })}>
          {L("عدّل التفاصيل", "Edit the details")}
        </button>
      </div>
    </div>
  );
}

function Confirm({ prompt, send, busy, orderId }: {
  prompt: Extract<Prompt, { kind: "confirm" }>; send: Send; busy: boolean; orderId: string;
}) {
  const { t } = useLang();
  const [changing, setChanging] = useState(false);
  const [changes, setChanges] = useState("");

  return (
    <div className="stack">
      {prompt.summary ? <Receipt summary={prompt.summary} orderId={orderId} /> : <pre className="receipt">{prompt.pre_receipt}</pre>}
      {prompt.error && <p className="error">{prompt.error}</p>}
      {!changing ? (
        <div className="row">
          <button className="btn" disabled={busy} onClick={() => send({ confirm: true })}>{busy ? t("thinking") : t("confirm")}</button>
          <button className="btn-ghost" disabled={busy} onClick={() => setChanging(true)}>{t("requestChanges")}</button>
        </div>
      ) : (
        <form className="stack" onSubmit={(e) => { e.preventDefault(); send({ confirm: false, changes }); }}>
          <textarea dir="auto" value={changes} placeholder={t("changesPlaceholder")} onChange={(e) => setChanges(e.target.value)} required />
          <div className="row">
            <button className="btn" disabled={busy || !changes.trim()}>{busy ? t("thinking") : t("sendChanges")}</button>
            <button type="button" className="btn-ghost" onClick={() => setChanging(false)}>{t("back")}</button>
          </div>
        </form>
      )}
    </div>
  );
}
