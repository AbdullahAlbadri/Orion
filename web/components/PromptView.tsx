"use client";

import { useState } from "react";

import type { OrderView, Prompt } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { ShirtIcon } from "./Icons";
import SectionedForm from "./SectionedForm";

type Send = (reply: Record<string, unknown>) => Promise<void>;

export default function PromptView({ order, send, busy }: { order: OrderView; send: Send; busy: boolean }) {
  const { t, lang } = useLang();
  const prompt = order.prompt;

  if (order.waiting_on === "manufacturer" || !prompt) {
    return (
      <div className="card">
        <span className="pill factories">{order.status[lang]}</span>
        <h2 style={{ marginTop: 14 }}>{t("waitingTitle")}</h2>
        <p className="muted">{t("waitingText")}</p>
        {order.pre_receipt && <pre className="receipt">{order.pre_receipt}</pre>}
      </div>
    );
  }

  switch (prompt.kind) {
    case "choice":
      return <Choice prompt={prompt} send={send} busy={busy} />;
    case "form":
      return <SectionedForm key={`${prompt.step}:${prompt.questions.map((q) => q.id).join(",")}:${JSON.stringify(prompt.errors)}`} orderId={order.order_id} prompt={prompt} send={send} busy={busy} />;
    case "confirm":
      return <Confirm prompt={prompt} send={send} busy={busy} />;
  }
}

function Choice({ prompt, send, busy }: { prompt: Extract<Prompt, { kind: "choice" }>; send: Send; busy: boolean }) {
  return (
    <div className="card">
      <h2 dir="auto">{prompt.prompt}</h2>
      {prompt.error && <p className="error">{prompt.error}</p>}
      <div className="choices">
        {prompt.options.map((o) => (
          <button key={o.id} className="choice" disabled={busy} onClick={() => send({ choice: o.id })}>
            <span className="avatar"><ShirtIcon width={20} height={20} /></span>
            {o.name}
          </button>
        ))}
      </div>
    </div>
  );
}

function Confirm({ prompt, send, busy }: { prompt: Extract<Prompt, { kind: "confirm" }>; send: Send; busy: boolean }) {
  const { t } = useLang();
  const [changing, setChanging] = useState(false);
  const [changes, setChanges] = useState("");

  return (
    <div className="card stack">
      <h2>{t("summary")}</h2>
      <pre className="receipt">{prompt.pre_receipt}</pre>
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
