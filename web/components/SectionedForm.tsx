"use client";

// The product details form, split into Design / Quantity / Quality tabs. Answers are kept across tabs and
// sent together; the API validates and sends errors back, and we jump to the first tab with an error.
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { ApiError, askAboutSection, type Prompt, type Question, type Section } from "@/lib/api";
import { useLang, type TextKey } from "@/lib/i18n";
import {
  ArrowIcon, CheckIcon, HashIcon, ImageIcon, LayersIcon, ListIcon, NeedleIcon, PaletteIcon, PlusIcon, RulerIcon, ScaleIcon,
  SendIcon, ShieldIcon, ShirtIcon, SparkleIcon, StepsIcon, TagIcon, TargetIcon,
} from "./Icons";
import type { Placement } from "@/lib/mockups";
import { choiceLabel, costTier, errorText, iconFor, questionHint, questionText } from "@/lib/questions";
import PlacementEditor from "./PlacementEditor";
import TopoTexture from "./TopoTexture";
import SizeTable, { initialSizes, sizesToAnswer, type SizeRow } from "./SizeTable";

type FormPrompt = Extract<Prompt, { kind: "form" }>;
type Send = (reply: Record<string, unknown>) => Promise<void>;

const SECTIONS: { id: Section; title: TextKey; hint: TextKey; icon: ReactNode }[] = [
  { id: "design", title: "sectionDesign", hint: "sectionDesignHint", icon: <PaletteIcon /> },
  { id: "quantity", title: "sectionQuantity", hint: "sectionQuantityHint", icon: <HashIcon /> },
  { id: "quality", title: "sectionQuality", hint: "sectionQualityHint", icon: <ShieldIcon /> },
];


// Choice questions: tapped options plus an optional "Other" text
type ChoiceState = { picked: string[]; other: string; otherOn: boolean };

function initialChoice(q: Question, value: unknown): ChoiceState {
  const list = Array.isArray(value) ? value.map(String) : value == null || value === "" ? [] : [String(value)];
  const others = list.filter((v) => !q.choices.includes(v));
  return { picked: list.filter((v) => q.choices.includes(v)), other: others.join(", "), otherOn: others.length > 0 };
}

function choiceAnswer(q: Question, s: ChoiceState): string | string[] {
  const other = s.otherOn ? s.other.trim() : "";
  if (q.multiple) return [...s.picked, ...(other ? [other] : [])];
  return other || s.picked[0] || "";
}

export default function SectionedForm({ orderId, prompt: raw, send, busy }: {
  orderId: string; prompt: FormPrompt; send: Send; busy: boolean;
}) {
  const { t, lang } = useLang();
  // An older API sends questions without a section: treat those as design
  const prompt = useMemo(
    () => ({ ...raw, questions: raw.questions.map((q) => ({ ...q, section: q.section ?? "design" })) }),
    [raw],
  );
  const sections = SECTIONS.filter((s) => prompt.questions.some((q) => q.section === s.id));

  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(prompt.questions.filter((q) => q.type !== "size_table" && q.type !== "choice")
      .map((q) => [q.id, prompt.values[q.id] == null ? "" : String(prompt.values[q.id])])));
  const [choices, setChoices] = useState<Record<string, ChoiceState>>(() =>
    Object.fromEntries(prompt.questions.filter((q) => q.type === "choice")
      .map((q) => [q.id, initialChoice(q, prompt.values[q.id])])));
  const [placements, setPlacements] = useState<Record<string, Placement[]>>(() =>
    Object.fromEntries(prompt.questions.filter((q) => q.type === "placement")
      .map((q) => [q.id, Array.isArray(prompt.values[q.id]) ? (prompt.values[q.id] as Placement[]) : []])));
  const [sizes, setSizes] = useState<Record<string, SizeRow[]>>(() =>
    Object.fromEntries(prompt.questions.filter((q) => q.type === "size_table")
      .map((q) => [q.id, initialSizes(prompt.values[q.id])])));
  // Start on the first tab with a server error, else the first tab
  const [active, setActive] = useState(() => {
    const i = sections.findIndex((s) => prompt.questions.some((q) => q.section === s.id && prompt.errors[q.id]));
    return Math.max(0, i);
  });

  const answers = useMemo(() => {
    const out: Record<string, unknown> = { ...values };
    for (const [id, rows] of Object.entries(sizes)) out[id] = sizesToAnswer(rows);
    for (const q of prompt.questions) if (q.type === "choice") out[q.id] = choiceAnswer(q, choices[q.id]);
    for (const [id, items] of Object.entries(placements)) out[id] = items;
    return out;
  }, [values, sizes, choices, placements, prompt.questions]);

  const isAnswered = (q: Question) => {
    if (q.type === "size_table") return Object.keys(sizesToAnswer(sizes[q.id] ?? [])).length > 0;
    if (q.type === "placement") return (placements[q.id] ?? []).length > 0;
    if (q.type === "choice") return choiceAnswer(q, choices[q.id]).length > 0;
    return Boolean(values[q.id]?.trim());
  };

  function pick(q: Question, option: string) {
    const s = choices[q.id];
    const picked = q.multiple
      ? (s.picked.includes(option) ? s.picked.filter((p) => p !== option) : [...s.picked, option])
      : (s.picked[0] === option ? [] : [option]);
    // Single choice: an option replaces "Other"
    setChoices({ ...choices, [q.id]: { ...s, picked, otherOn: q.multiple ? s.otherOn : false } });
  }

  function toggleOther(q: Question) {
    const s = choices[q.id];
    setChoices({ ...choices, [q.id]: { ...s, otherOn: !s.otherOn, picked: q.multiple ? s.picked : [] } });
  }
  const progress = (section: Section) => {
    const required = prompt.questions.filter((q) => q.section === section && q.required);
    return { done: required.filter(isAnswered).length, total: required.length };
  };

  // "steps": one section at a time; "all": every section on one page. Remembered on this device.
  const [mode, setModeState] = useState<"steps" | "all">("steps");
  useEffect(() => {
    try {
      if (localStorage.getItem("orion-form-mode") === "all") setModeState("all");
    } catch { /* storage blocked */ }
  }, []);
  const setMode = (m: "steps" | "all") => {
    setModeState(m);
    try { localStorage.setItem("orion-form-mode", m); } catch { /* ignore */ }
  };

  const last = mode === "all" || active === sections.length - 1;
  const shown = mode === "all" ? sections : [sections[active]];

  function onTab(i: number) {
    setActive(i);
    if (mode === "all") document.getElementById(`section-${sections[i].id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const renderQuestion = (q: Question) => (
    <QuestionCard key={q.id} q={q} error={prompt.errors[q.id]}>
      {q.type === "size_table" ? (
        <SizeTable rows={sizes[q.id]} onChange={(rows) => setSizes({ ...sizes, [q.id]: rows })} />
      ) : q.type === "placement" ? (
        <PlacementEditor mockup={q.mockup} value={placements[q.id]}
          onChange={(items) => setPlacements((prev) => ({ ...prev, [q.id]: items }))} />
      ) : q.type === "choice" ? (
        <>
          <div className="chips" role={q.multiple ? "group" : "radiogroup"} aria-label={questionText(q, lang)}>
            {q.choices.map((c) => {
              const on = choices[q.id].picked.includes(c);
              return (
                <button key={c} type="button" role={q.multiple ? "checkbox" : "radio"} aria-checked={on}
                  className={`chip${on ? " selected" : ""}`} dir="auto" onClick={() => pick(q, c)}>
                  {q.multiple && on && <CheckIcon width={14} height={14} />}{choiceLabel(q, c, lang)}
                  {costTier(q, c) > 0 && <span className="cost" title={t("costHint")}>{"$".repeat(costTier(q, c))}</span>}
                </button>
              );
            })}
            {q.allow_other && (
              <button type="button" role={q.multiple ? "checkbox" : "radio"} aria-checked={choices[q.id].otherOn}
                className={`chip chip-other${choices[q.id].otherOn ? " selected" : ""}`} onClick={() => toggleOther(q)}>
                <PlusIcon width={14} height={14} /> {t("other")}
              </button>
            )}
          </div>
          {q.multiple && <div className="hint">{t("pickSeveral")}</div>}
          {choices[q.id].otherOn && (
            <input id={q.id} dir="auto" autoFocus value={choices[q.id].other} placeholder={t("otherPlaceholder")}
              onChange={(e) => setChoices({ ...choices, [q.id]: { ...choices[q.id], other: e.target.value } })} />
          )}
        </>
      ) : (
        <input id={q.id} value={values[q.id] ?? ""} dir={q.type === "number" ? "ltr" : "auto"}
          inputMode={q.type === "number" ? "decimal" : undefined}
          placeholder={q.type === "file" ? "https://…" : undefined}
          onChange={(e) => setValues({ ...values, [q.id]: e.target.value })} />
      )}
    </QuestionCard>
  );

  return (
    <form className="stack form-boards" onSubmit={(e) => { e.preventDefault(); if (last) send({ answers }); else setActive(active + 1); }}>
      <div className="board board-glass stack">
      <div className="spread">
        <h2 style={{ margin: 0 }} dir="auto">{lang === "ar" && prompt.prompt_ar ? prompt.prompt_ar : prompt.prompt}</h2>
        <div className="segmented" role="radiogroup" aria-label={t("viewMode")}>
          <button type="button" role="radio" aria-checked={mode === "steps"} className={mode === "steps" ? "on" : ""}
            onClick={() => setMode("steps")}>
            <StepsIcon width={16} height={16} /> {t("viewSteps")}
          </button>
          <button type="button" role="radio" aria-checked={mode === "all"} className={mode === "all" ? "on" : ""}
            onClick={() => setMode("all")}>
            <ListIcon width={16} height={16} /> {t("viewAll")}
          </button>
        </div>
      </div>

      <div className="tabs" role="tablist">
        {sections.map((s, i) => {
          const p = progress(s.id);
          const complete = p.total > 0 && p.done === p.total;
          const hasError = prompt.questions.some((q) => q.section === s.id && prompt.errors[q.id]);
          const selected = mode === "steps" && i === active;
          return (
            <button key={s.id} type="button" role="tab" aria-selected={selected}
              className={`tab${selected ? " active" : ""}${hasError ? " has-error" : ""}`} onClick={() => onTab(i)}>
              <span className="tab-icon">{complete ? <CheckIcon /> : s.icon}</span>
              <span className="tab-text">
                <strong>{t(s.title)}</strong>
                <span className="small">{p.total ? `${p.done}/${p.total}` : t(s.hint)}</span>
              </span>
            </button>
          );
        })}
      </div>
      </div>

      {shown.map((s) => (
        <section key={s.id} id={`section-${s.id}`} className={`form-section board section-board section-${s.id} cross`}>
          {s.id !== "quantity" && <TopoTexture />}
          <div className="section-head">
            <div className="row">
              <span className="section-icon">{s.icon}</span>
              <div>
                <strong>{t(s.title)}</strong>
                <div className="muted small">{t(s.hint)}</div>
              </div>
            </div>
            <AskOrion key={s.id} orderId={orderId} section={s.id} answers={answers} />
          </div>
          {prompt.questions.some((q) => q.section === s.id && q.cost_tiers?.some((tier) => tier > 0)) && (
            <div className="hint cost-note">{t("costNote")}</div>
          )}
          <div className="qgrid">{prompt.questions.filter((q) => q.section === s.id).map(renderQuestion)}</div>
        </section>
      ))}

      <div className="spread form-nav">
        {mode === "steps" && active > 0 ? (
          <button type="button" className="btn-ghost" onClick={() => setActive(active - 1)}>
            <ArrowIcon className="flip-back" width={18} height={18} /> {t("previous")}
          </button>
        ) : <span />}
        <button className="btn" disabled={busy}>
          {busy ? t("thinking") : last ? t("submit") : t("next")}
          {!busy && <ArrowIcon className="flip-forward" width={18} height={18} />}
        </button>
      </div>
    </form>
  );
}

function QuestionCard({ q, error, children }: { q: Question; error?: string; children: ReactNode }) {
  const { t, lang } = useLang();
  const hint = questionHint(q, lang);
  const wide = q.type === "size_table" || q.type === "choice" || q.type === "placement";
  return (
    <div className={`qcard${wide ? " wide" : ""}${error ? " has-error" : ""}`}>
      <div className="qhead">
        <span className="qicon">{iconFor(q.id)}</span>
        <label htmlFor={q.id} dir="auto">
          {questionText(q, lang)}
          {!q.required && <span className="muted small"> ({t("optional")})</span>}
        </label>
      </div>
      {children}
      {hint && <div className="hint" dir="auto">{hint}</div>}
      {error && <div className="field-error" dir="auto">{errorText(error, lang)}</div>}
    </div>
  );
}

function AskOrion({ orderId, section, answers }: { orderId: string; section: Section; answers: Record<string, unknown> }) {
  const { t, lang } = useLang();
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [thread, setThread] = useState<{ q: string; a: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(text: string) {
    setBusy(true);
    setError(null);
    try {
      const a = await askAboutSection(orderId, section, text, answers, lang);
      setThread((th) => [...th, { q: text || t("askExplain"), a }]);
      setQuestion("");
    } catch (e) {
      setError(e instanceof ApiError && e.status === 429 ? t("askTooMany") : t("error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ask">
      <button type="button" className={`ask-btn${open ? " open" : ""}`} onClick={() => setOpen(!open)} aria-expanded={open}>
        <SparkleIcon width={18} height={18} /> {t("askOrion")}
      </button>
      {open && (
        <div className="ask-panel">
          {thread.map((m, i) => (
            <div key={i} className="stack" style={{ gap: 6 }}>
              <div className="bubble customer" dir="auto">{m.q}</div>
              <div className="bubble orion" dir="auto">{m.a}</div>
            </div>
          ))}
          {busy && <div className="thinking">{t("thinking")}</div>}
          {error && <p className="error small">{error}</p>}
          {thread.length === 0 && !busy && (
            <button type="button" className="chip" onClick={() => ask("")}>
              <SparkleIcon width={14} height={14} /> {t("askExplain")}
            </button>
          )}
          <div className="composer">
            <input value={question} dir="auto" placeholder={t("askPlaceholder")} disabled={busy}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); if (question.trim()) ask(question.trim()); } }} />
            <button type="button" className="btn btn-icon" aria-label={t("send")} disabled={busy || !question.trim()}
              onClick={() => ask(question.trim())}>
              <SendIcon width={18} height={18} />
            </button>
          </div>
          <div className="muted small">{t("askNote")}</div>
        </div>
      )}
    </div>
  );
}
