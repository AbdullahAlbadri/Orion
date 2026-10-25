"use client";

import { useState } from "react";

import type { OrderView, Prompt } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { ShirtIcon } from "./Icons";
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

function Choice({ prompt, send, busy }: { prompt: Extract<Prompt, { kind: "choice" }>; send: Send; busy: boolean }) {
  const { lang } = useLang();
  return (
    <div className="card">
      <h2 dir="auto">{lang === "ar" && prompt.prompt_ar ? prompt.prompt_ar : prompt.prompt}</h2>
      {prompt.error && <p className="error">{prompt.error}</p>}
      <div className="choices">
        {prompt.options.map((o) => (
          <button key={o.id} className="choice" disabled={busy} onClick={() => send({ choice: o.id })}>
            <span className="avatar"><ShirtIcon width={20} height={20} /></span>
            {lang === "ar" && o.name_ar ? o.name_ar : o.name}
          </button>
        ))}
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
