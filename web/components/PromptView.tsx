"use client";

import { useState } from "react";

import type { OrderView, Prompt, Question } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { ShirtIcon } from "./Icons";
import SizeTable, { initialSizes, sizesToAnswer, type SizeRow } from "./SizeTable";

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
      return <Form prompt={prompt} send={send} busy={busy} />;
    case "chat":
      return <Chat order={order} send={send} busy={busy} />;
    case "confirm":
      return <Confirm prompt={prompt} send={send} busy={busy} />;
  }
}

function Choice({ prompt, send, busy }: { prompt: Extract<Prompt, { kind: "choice" }>; send: Send; busy: boolean }) {
  return (
    <div className="card">
      <h2>{prompt.prompt}</h2>
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

function Form({ prompt, send, busy }: { prompt: Extract<Prompt, { kind: "form" }>; send: Send; busy: boolean }) {
  const { t } = useLang();
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(prompt.questions.filter((q) => q.type !== "size_table")
      .map((q) => [q.id, prompt.values[q.id] == null ? "" : String(prompt.values[q.id])])));
  const [sizes, setSizes] = useState<Record<string, SizeRow[]>>(() =>
    Object.fromEntries(prompt.questions.filter((q) => q.type === "size_table").map((q) => [q.id, initialSizes(prompt.values[q.id])])));

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const answers: Record<string, unknown> = { ...values };
    for (const [id, rows] of Object.entries(sizes)) answers[id] = sizesToAnswer(rows);
    send({ answers });
  }

  const field = (q: Question) => {
    if (q.type === "size_table") {
      return <SizeTable rows={sizes[q.id]} onChange={(rows) => setSizes({ ...sizes, [q.id]: rows })} />;
    }
    const common = {
      id: q.id, value: values[q.id] ?? "", required: q.required,
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setValues({ ...values, [q.id]: e.target.value }),
    };
    if (q.type === "choice") {
      return (
        <select {...common}>
          <option value="" />
          {q.choices.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      );
    }
    if (q.type === "number") return <input {...common} inputMode="decimal" dir="ltr" />;
    return <input {...common} dir="auto" placeholder={q.type === "file" ? "https://…" : undefined} />;
  };

  return (
    <form className="card stack" onSubmit={submit}>
      <h2>{prompt.prompt}</h2>
      {prompt.questions.map((q) => (
        <div key={q.id}>
          <label htmlFor={q.id}>{q.prompt}{!q.required && <span className="muted"> ({t("optional")})</span>}</label>
          {field(q)}
          {q.hint && <div className="hint">{q.hint}</div>}
          {prompt.errors[q.id] && <div className="field-error">{prompt.errors[q.id]}</div>}
        </div>
      ))}
      <button className="btn" disabled={busy}>{busy ? t("thinking") : t("submit")}</button>
    </form>
  );
}

function Chat({ order, send, busy }: { order: OrderView; send: Send; busy: boolean }) {
  const { t } = useLang();
  const [text, setText] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    const message = text;
    setText("");
    await send({ message });
  }

  return (
    <div className="card">
      <div className="chat">
        {order.messages.map((m, i) => <div key={i} className={`bubble ${m.role}`} dir="auto">{m.content}</div>)}
        {busy && <div className="thinking">{t("thinking")}</div>}
      </div>
      <form className="composer" onSubmit={submit}>
        <textarea dir="auto" value={text} placeholder={t("typeMessage")} onChange={(e) => setText(e.target.value)}
          disabled={busy}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} />
        <button className="btn" disabled={busy || !text.trim()}>{t("send")}</button>
      </form>
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
